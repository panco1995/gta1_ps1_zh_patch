#!/usr/bin/env python3
"""Rasterize the Simplified Chinese mission charset into 16x16 4bpp pages.

The US disc font (GAMEFONT page 0) is a Latin metallic face. Japanese wide
glyphs are drawn from a separate atlas the US image does not ship, and neither
Huffman alphabet can name 1500+ hanzi. These pages are the glyph art for that
atlas: 256 glyphs per 256x256 4bpp texture, low nibble first, index 0 blank.

This does not inject the pages into the game yet.

glyphs.bin is the form the in-game kanji cache wants. 0x800e51bc reads
16 little-endian rows per character. Records are sorted by Unicode scalar
so a hook can binary-search them:

    u32 count
    repeated: u16 codepoint, u16 zero, 32-byte bitmap
"""

import csv
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "text" / "zh_cn.tsv"
OUT = ROOT / "font"
FONT_PATH = OUT / "NotoSansCJKsc-Regular-subset.otf"
CELL = 16
PAGE = 16  # cells per side; 256 glyphs, one PS1 4bpp texture page
GLYPHS_PER_PAGE = PAGE * PAGE


def charset() -> list[str]:
    counts: Counter[str] = Counter()
    for row in csv.DictReader(SRC.open(encoding="utf-8"), delimiter="\t"):
        counts.update(ch for ch in row["zh"] if not ch.isspace())
    return [ch for ch, _ in counts.most_common()]


def draw_cell(font: ImageFont.FreeTypeFont, ch: str) -> Image.Image:
    img = Image.new("L", (CELL, CELL), 0)
    pen = ImageDraw.Draw(img)
    box = pen.textbbox((0, 0), ch, font=font)
    width = box[2] - box[0]
    height = box[3] - box[1]
    x = (CELL - width) // 2 - box[0]
    y = (CELL - height) // 2 - box[1]
    pen.text((x, y), ch, fill=255, font=font)
    return img.point(lambda p: 255 if p > 80 else 0)


def pack_row(cell: Image.Image, y: int) -> int:
    """One 16-pixel row as the kanji rasterizer reads it.

    0x800e51bc consumes 16 little-endian u16s. The low byte is the left
    eight pixels and bit 7 of each byte is the leftmost pixel of that half.
    """
    pix = cell.tobytes()
    row = 0
    for x in range(16):
        if not pix[y * CELL + x]:
            continue
        if x < 8:
            row |= 1 << (7 - x)
        else:
            row |= 1 << (15 - (x - 8))
    return row


def pack_bitmap(cell: Image.Image) -> bytes:
    return b"".join(pack_row(cell, y).to_bytes(2, "little") for y in range(CELL))


def pack_4bpp(cells: list[Image.Image]) -> bytes:
    raw = bytearray(GLYPHS_PER_PAGE * CELL * CELL // 2)
    for index, cell in enumerate(cells):
        col = index % PAGE
        row = index // PAGE
        pix = cell.tobytes()
        for y in range(CELL):
            for x in range(0, CELL, 2):
                left = 15 if pix[y * CELL + x] else 0
                right = 15 if pix[y * CELL + x + 1] else 0
                # Same order as GAMEFONT page 0: low nibble is the left pixel.
                byte = left | (right << 4)
                atlas_x = col * CELL + x
                atlas_y = row * CELL + y
                raw[(atlas_y * PAGE * CELL + atlas_x) // 2] = byte
    return bytes(raw)


def main() -> None:
    chars = charset()
    font = ImageFont.truetype(FONT_PATH, 14)
    OUT.mkdir(parents=True, exist_ok=True)
    # Slot 0 is the blank cell. Glyphs follow, most-used first.
    slots = [""] + chars
    pages = (len(slots) + GLYPHS_PER_PAGE - 1) // GLYPHS_PER_PAGE
    blank = Image.new("L", (CELL, CELL), 0)
    missing = []
    bitmaps: dict[str, bytes] = {}
    with (OUT / "charset.tsv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(["index", "char", "page", "x", "y"])
        for page in range(pages):
            cells = []
            preview = Image.new("L", (PAGE * CELL, PAGE * CELL), 0)
            for local in range(GLYPHS_PER_PAGE):
                index = page * GLYPHS_PER_PAGE + local
                ch = slots[index] if index < len(slots) else ""
                cell = blank if not ch else draw_cell(font, ch)
                if ch and cell.getbbox() is None:
                    missing.append(ch)
                if ch:
                    bitmaps[ch] = pack_bitmap(cell)
                cells.append(cell)
                col = local % PAGE
                row = local // PAGE
                preview.paste(cell, (col * CELL, row * CELL))
                if ch:
                    writer.writerow([index, ch, page, col * CELL, row * CELL])
            (OUT / f"page_{page:02d}.4bpp").write_bytes(pack_4bpp(cells))
            preview.save(OUT / f"page_{page:02d}.png")
    ordered = sorted(bitmaps, key=ord)
    blob = bytearray(len(ordered).to_bytes(4, "little"))
    for ch in ordered:
        blob += ord(ch).to_bytes(2, "little")
        blob += b"\x00\x00"
        blob += bitmaps[ch]
    (OUT / "glyphs.bin").write_bytes(blob)
    print(f"chars {len(chars)} slots {len(slots)} pages {pages} missing {len(missing)}")
    print(f"glyphs.bin {len(blob)} bytes, {len(ordered)} records")
    if missing:
        raise SystemExit("font has no glyph for " + "".join(missing[:40]))


if __name__ == "__main__":
    main()
