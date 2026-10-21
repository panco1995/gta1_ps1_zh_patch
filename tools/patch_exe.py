#!/usr/bin/env python3
"""Patch the US EXE so Simplified Chinese uses font/glyphs.bin.

The US build leaves the wide-character path switched off, and the glyph
source behind it is the BIOS Shift-JIS font. This turns the path on, points
the kanji cache at a VRAM strip of our own, and replaces the BIOS lookup
with a binary search of the glyphs appended to the executable.

ASCII inside a wide string is normally rewritten to Shift-JIS for the BIOS
font. Those codes overlap the hanzi we store as Unicode, so the patch skips
that rewrite and looks every character up by its Unicode scalar.
"""

import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "extract" / "SLUS_001.06"
GLYPHS = ROOT / "font" / "glyphs.bin"
ZH = ROOT / "text" / "zh_cn.tsv"
OUT = ROOT / "build" / "SLUS_001.06"

BASE = 0x80010000
HEADER = 0x800
LOAD_SIZE_OFF = 0x1C
GATE_OFF = 0xA5F8
CAVE = 0x8012F8D4
GLYPH_VA = 0x80130000
LOOKUP_FN = 0x8012C708
LOADER_AT = 0x800E4F3C
LOADER_RESUME = 0x800E4F8C
REMAP_BRANCH = 0x800E545C
FONT_PATH = ROOT / "font" / "NotoSansCJKsc-Regular-subset.otf"
# Beside the 320-wide framebuffers. 160 slots of 4 VRAM pixels fit in
# 384..1024, and y=256 stays out of a buffer that only occupies x=0..320.
VRAM_X = 384
VRAM_Y = 256

REG = {
    "zero": 0, "at": 1, "v0": 2, "v1": 3, "a0": 4, "a1": 5, "a2": 6, "a3": 7,
    "t0": 8, "t1": 9, "t2": 10, "t3": 11, "t4": 12, "t5": 13, "t6": 14, "t7": 15,
    "gp": 28, "ra": 31,
}


def file_off(va: int) -> int:
    return va - BASE + HEADER


def split_addr(addr: int) -> tuple[int, int]:
    lo = addr & 0xFFFF
    hi = (addr >> 16) & 0xFFFF
    if lo >= 0x8000:
        hi = (hi + 1) & 0xFFFF
        lo -= 0x10000
    return hi, lo


def i_type(op: int, rs: str, rt: str, imm: int) -> int:
    return (op << 26) | (REG[rs] << 21) | (REG[rt] << 16) | (imm & 0xFFFF)


def r_type(rs: str, rt: str, rd: str, shamt: int, funct: int) -> int:
    return (REG[rs] << 21) | (REG[rt] << 16) | (REG[rd] << 11) | (shamt << 6) | funct


def lui(rt: str, imm: int) -> int:
    return i_type(0x0F, "zero", rt, imm)


def addiu(rt: str, rs: str, imm: int) -> int:
    return i_type(0x09, rs, rt, imm)


def lw(rt: str, imm: int, rs: str) -> int:
    return i_type(0x23, rs, rt, imm)


def lhu(rt: str, imm: int, rs: str) -> int:
    return i_type(0x25, rs, rt, imm)


def sw(rt: str, imm: int, rs: str) -> int:
    return i_type(0x2B, rs, rt, imm)


def beq(rs: str, rt: str, words: int) -> int:
    return i_type(0x04, rs, rt, words)


def j(target: int) -> int:
    return (0x02 << 26) | ((target >> 2) & 0x3FFFFFF)


def jr(rs: str) -> int:
    return r_type(rs, "zero", "zero", 0, 8)


def nop() -> int:
    return 0


def addu(rd: str, rs: str, rt: str) -> int:
    return r_type(rs, rt, rd, 0, 0x21)


def sltu(rd: str, rs: str, rt: str) -> int:
    return r_type(rs, rt, rd, 0, 0x2B)


def sll(rd: str, rt: str, shamt: int) -> int:
    return r_type("zero", rt, rd, shamt, 0)


def srl(rd: str, rt: str, shamt: int) -> int:
    return r_type("zero", rt, rd, shamt, 2)


def move(rd: str, rs: str) -> int:
    return r_type(rs, "zero", rd, 0, 0x25)


def words(*ops: int) -> bytes:
    return b"".join(struct.pack("<I", op) for op in ops)


def pack_bitmap(cell: Image.Image) -> bytes:
    pix = cell.tobytes()
    out = bytearray()
    for y in range(16):
        row = 0
        for x in range(16):
            if not pix[y * 16 + x]:
                continue
            if x < 8:
                row |= 1 << (7 - x)
            else:
                row |= 1 << (15 - (x - 8))
        out += struct.pack("<H", row)
    return bytes(out)


def draw_char(font: ImageFont.FreeTypeFont, char: str) -> bytes:
    img = Image.new("L", (16, 16), 0)
    pen = ImageDraw.Draw(img)
    box = pen.textbbox((0, 0), char, font=font)
    x = (16 - (box[2] - box[0])) // 2 - box[0]
    y = (16 - (box[3] - box[1])) // 2 - box[1]
    pen.text((x, y), char, fill=255, font=font)
    img = img.point(lambda p: 255 if p > 80 else 0)
    return pack_bitmap(img)


def load_glyphs() -> dict[int, bytes]:
    blob = GLYPHS.read_bytes()
    count = struct.unpack_from("<I", blob)[0]
    out = {}
    pos = 4
    for _ in range(count):
        code, _zero = struct.unpack_from("<HH", blob, pos)
        bitmap = blob[pos + 4 : pos + 36]
        if len(bitmap) != 32 or code in out:
            raise SystemExit(f"bad glyph record at {pos}")
        out[code] = bitmap
        pos += 36
    if pos != len(blob):
        raise SystemExit("glyphs.bin has trailing bytes")
    return out


def ascii_in_wide_strings() -> set[str]:
    import csv

    need = set()
    for row in csv.DictReader(ZH.open(encoding="utf-8"), delimiter="\t"):
        text = row["zh"]
        if any(ord(ch) > 127 for ch in text):
            need.update(ch for ch in text if ord(ch) < 128)
    return need


def lookup_code(code_va: int, glyph_va: int, blank_va: int) -> bytes:
    ghi, glo = split_addr(glyph_va)
    bhi, blo = split_addr(blank_va)
    # Offsets are in instructions from the branch to the target, counting
    # from the delay slot. miss is 20 words ahead, hit is 9, go_lo is 4.
    return words(
        lui("t0", ghi),
        addiu("t0", "t0", glo),
        lw("t1", 0, "t0"),
        addiu("t0", "t0", 4),
        move("t2", "zero"),
        move("t3", "t1"),
        beq("t2", "t3", 20),
        nop(),
        addu("t4", "t2", "t3"),
        srl("t4", "t4", 1),
        sll("t5", "t4", 5),
        sll("t6", "t4", 2),
        addu("t5", "t5", "t6"),
        addu("t5", "t5", "t0"),
        lhu("t6", 0, "t5"),
        beq("t6", "a0", 9),
        nop(),
        sltu("t7", "t6", "a0"),
        beq("t7", "zero", 4),
        nop(),
        addiu("t2", "t4", 1),
        j(code_va + 0x18),
        nop(),
        j(code_va + 0x18),
        move("t3", "t4"),
        jr("ra"),
        addiu("v0", "t5", 4),
        lui("v0", bhi),
        jr("ra"),
        addiu("v0", "v0", blo),
    )


def main() -> None:
    exe = bytearray(EXE.read_bytes())
    if exe[:8] != b"PS-X EXE":
        raise SystemExit("not a PS-X EXE")
    load_size = struct.unpack_from("<I", exe, LOAD_SIZE_OFF)[0]
    if load_size != 0x120000 or len(exe) != HEADER + load_size:
        raise SystemExit(f"unexpected EXE size {len(exe):#x} load {load_size:#x}")
    if exe[GATE_OFF : GATE_OFF + 4] != b"\x01\x00\x00\x00":
        raise SystemExit("wide-char gate is not the US default")
    if struct.unpack_from("<I", exe, file_off(LOADER_AT))[0] >> 26 != 0x0F:
        raise SystemExit("kanji loader entry does not look like the US build")

    glyphs = load_glyphs()
    import csv

    missing = sorted({ch for row in csv.DictReader(ZH.open(encoding="utf-8"), delimiter="\t") for ch in row["zh"] if ord(ch) > 127 and ord(ch) not in glyphs})
    if missing:
        raise SystemExit("glyphs.bin is missing " + "".join(missing[:20]))
    font = ImageFont.truetype(FONT_PATH, 14)
    added = 0
    for char in sorted(ascii_in_wide_strings()):
        if ord(char) in glyphs:
            continue
        glyphs[ord(char)] = b"\x00" * 32 if char == " " else draw_char(font, char)
        added += 1
    # 0x800e545c is `beqz v0, +4`, taken only for codepoints above 0xFF.
    # An unconditional branch leaves ASCII as itself instead of Shift-JIS.
    branch = struct.unpack_from("<I", exe, file_off(REMAP_BRANCH))[0]
    if branch != beq("v0", "zero", 4):
        raise SystemExit(f"remap branch is {branch:#x}, not the US instruction")
    struct.pack_into("<I", exe, file_off(REMAP_BRANCH), beq("zero", "zero", 4))

    ordered = sorted(glyphs)
    blob = bytearray(struct.pack("<I", len(ordered)))
    for code in ordered:
        blob += struct.pack("<HH", code, 0)
        blob += glyphs[code]
    pad = (-len(blob)) % 2048
    image_extra = bytes(blob) + b"\x00" * pad

    cave = file_off(CAVE)
    struct_va = CAVE
    blank_va = CAVE + 0x48
    code_va = CAVE + 0x68
    if code_va + 0x78 > GLYPH_VA:
        raise SystemExit("lookup stub does not fit in the cave")
    struct_bytes = bytearray(0x48)
    struct.pack_into("<H", struct_bytes, 0x1C, VRAM_X)
    struct.pack_into("<H", struct_bytes, 0x1E, VRAM_Y)
    exe[cave : cave + 0x48] = struct_bytes
    exe[cave + 0x48 : cave + 0x68] = b"\x00" * 32
    code = lookup_code(code_va, GLYPH_VA, blank_va)
    if len(code) != 0x78:
        raise SystemExit(f"lookup stub is {len(code)} bytes, expected 120")
    exe[cave + 0x68 : cave + 0x68 + len(code)] = code

    exe[file_off(LOOKUP_FN) : file_off(LOOKUP_FN) + 8] = words(j(code_va), nop())
    loader = words(
        lui("t0", split_addr(struct_va)[0]),
        addiu("t0", "t0", split_addr(struct_va)[1]),
        sw("t0", 0x660, "gp"),
        sw("t0", 0x664, "gp"),
        j(LOADER_RESUME),
        nop(),
    )
    span = file_off(LOADER_RESUME) - file_off(LOADER_AT)
    exe[file_off(LOADER_AT) : file_off(LOADER_RESUME)] = loader + words(*([nop()] * ((span - len(loader)) // 4)))
    exe[GATE_OFF : GATE_OFF + 4] = b"\x00\x00\x00\x00"

    exe.extend(image_extra)
    struct.pack_into("<I", exe, LOAD_SIZE_OFF, len(exe) - HEADER)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(exe)

    from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN

    md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 + CS_MODE_LITTLE_ENDIAN)
    print("lookup:")
    for insn in md.disasm(code, code_va):
        print(f"  {insn.address:08x}: {insn.mnemonic:8} {insn.op_str}")
    print(f"added ascii {added} glyphs {len(ordered)} appended {len(image_extra)}")
    print(f"wrote {OUT} ({len(exe)} bytes)")


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(0)
