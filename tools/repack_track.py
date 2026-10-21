#!/usr/bin/env python3
"""Repack Track 01 so the patched EXE and MISSION.VSR fit.

Both files are larger than their original extents, and the next file starts
on the following sector. This rebuilds the data track in the same order,
updates the root directory, and writes a Mode 2 Form 1 EDC/ECC for every
sector whose bytes changed. Audio tracks are separate files and stay put.
"""

import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "Grand Theft Auto (USA)" / "Grand Theft Auto (USA) (Track 01).bin"
SLUS = ROOT / "build" / "SLUS_001.06"
MISSION = ROOT / "build" / "MISSION.VSR"
OUT = ROOT / "build" / "Grand Theft Auto (USA) (Track 01).bin"
CUE = ROOT / "build" / "Grand Theft Auto (zh).cue"
AUDIO = ROOT / "Grand Theft Auto (USA)"

SEC = 2352
USER = 2048
USER_AT = 24
REPLACEMENTS = {
    b"SLUS_001.06": SLUS,
    b"MISSION.VSR": MISSION,
}
TAIL_SECTORS = 150
DATA_SUB = bytes.fromhex("0000080000000800")
TAIL_SUB = bytes.fromhex("0000200000002000")
SYNC = bytes.fromhex("00ffffffffff00")  # placeholder, real sync below
SYNC = bytes.fromhex("00ffffffffffffffffffff00")

F_LUT = [0] * 256
B_LUT = [0] * 256
for _i in range(256):
    _j = ((_i << 1) ^ (0x11D if _i & 0x80 else 0)) & 0xFF
    F_LUT[_i] = _j
    B_LUT[_i ^ _j] = _i

EDC_LUT = [0] * 256
for _i in range(256):
    _edc = _i
    for _ in range(8):
        _edc = (_edc >> 1) ^ (0xD8018001 if _edc & 1 else 0)
    EDC_LUT[_i] = _edc


def user_of(image: bytes, sector: int) -> bytes:
    off = sector * SEC + USER_AT
    return image[off : off + USER]


def edc(buf: bytes) -> int:
    crc = 0
    for byte in buf:
        crc = (crc >> 8) ^ EDC_LUT[(crc ^ byte) & 0xFF]
    return crc


def ecc_compute(src: bytes, major_count: int, minor_count: int, major_mult: int, minor_inc: int) -> bytes:
    size = major_count * minor_count
    dest = bytearray(major_count * 2)
    for major in range(major_count):
        index = (major >> 1) * major_mult + (major & 1)
        ecc_a = 0
        ecc_b = 0
        for _minor in range(minor_count):
            temp = src[index]
            index += minor_inc
            if index >= size:
                index -= size
            ecc_a ^= temp
            ecc_b ^= temp
            ecc_a = F_LUT[ecc_a]
        ecc_a = B_LUT[F_LUT[ecc_a] ^ ecc_b]
        dest[major] = ecc_a
        dest[major + major_count] = (ecc_a ^ ecc_b) & 0xFF
    return bytes(dest)


def bcd(number: int) -> int:
    return ((number // 10) << 4) | (number % 10)


def header(lba: int) -> bytes:
    tick = lba + 150
    frame = tick % 75
    tick //= 75
    second = tick % 60
    minute = tick // 60
    return bytes((bcd(minute), bcd(second), bcd(frame), 0x02))


def form1(lba: int, sub: bytes, payload: bytes) -> bytes:
    if len(payload) != USER or len(sub) != 8:
        raise SystemExit("a Form 1 sector needs 8 subheader bytes and 2048 data bytes")
    sector = bytearray(SEC)
    sector[:12] = SYNC
    sector[12:16] = header(lba)
    sector[16:24] = sub
    sector[24:2072] = payload
    struct.pack_into("<I", sector, 2072, edc(sector[16:2072]))
    saved = bytes(sector[12:16])
    sector[12:16] = b"\x00\x00\x00\x00"
    # Q parity covers the P parity, so P has to be stored before Q is built.
    sector[2076:2248] = ecc_compute(sector[12:], 86, 24, 2, 86)
    sector[2248:2352] = ecc_compute(sector[12:], 52, 43, 86, 88)
    sector[12:16] = saved
    return bytes(sector)


def directory(image: bytes) -> tuple[int, bytearray, list[tuple[int, bytes, int, int]]]:
    pvd = user_of(image, 16)
    extent = struct.unpack_from("<I", pvd, 158)[0]
    length = struct.unpack_from("<I", pvd, 166)[0]
    blob = bytearray(user_of(image, extent)[:length])
    files = []
    pos = 0
    while pos + 33 < len(blob):
        rec = blob[pos]
        if rec == 0:
            break
        name_len = blob[pos + 32]
        raw = bytes(blob[pos + 33 : pos + 33 + name_len])
        name = raw.split(b";", 1)[0]
        file_extent = struct.unpack_from("<I", blob, pos + 2)[0]
        size = struct.unpack_from("<I", blob, pos + 10)[0]
        if name not in (b"\x00", b"\x01"):
            files.append((pos, name, file_extent, size))
        pos += rec
    return extent, blob, files


def read_file(image: bytes, extent: int, size: int) -> bytes:
    out = bytearray()
    left = size
    sector = extent
    while left:
        take = min(USER, left)
        out += user_of(image, sector)[:take]
        left -= take
        sector += 1
    return bytes(out)


def put_both(buf: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<I", buf, offset, value)
    struct.pack_into(">I", buf, offset + 4, value)


def main() -> None:
    image = SRC.read_bytes()
    if len(image) % SEC:
        raise SystemExit("track 01 is not a whole number of sectors")
    root_sector, records, files = directory(image)
    if root_sector != 22:
        raise SystemExit(f"root directory is at sector {root_sector}, expected 22")
    files.sort(key=lambda item: item[2])
    if files[0][2] != 23:
        raise SystemExit("the first file does not start at sector 23")

    payloads = []
    for pos, name, extent, size in files:
        if name in REPLACEMENTS:
            data = REPLACEMENTS[name].read_bytes()
            print(f"{name.decode():16} {size:8} -> {len(data):8}")
        else:
            data = read_file(image, extent, size)
        payloads.append((pos, name, data))

    cursor = 23
    placed = []
    for pos, name, data in payloads:
        placed.append((pos, name, cursor, data))
        cursor += (len(data) + USER - 1) // USER
    tail_at = cursor
    total = tail_at + TAIL_SECTORS
    print(f"sectors {len(image)//SEC} -> {total}")

    for pos, name, extent, data in placed:
        put_both(records, pos + 2, extent)
        put_both(records, pos + 10, len(data))
    if len(records) > USER:
        raise SystemExit("root directory no longer fits in one sector")
    records.extend(b"\x00" * (USER - len(records)))

    pvd = bytearray(user_of(image, 16))
    old_volume = struct.unpack_from("<I", pvd, 80)[0]
    put_both(pvd, 80, old_volume + (total - len(image) // SEC))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("wb") as handle:
        for sector in range(16):
            handle.write(image[sector * SEC : (sector + 1) * SEC])
        handle.write(form1(16, image[16 * SEC + 16 : 16 * SEC + 24], bytes(pvd)))
        for sector in range(17, 22):
            handle.write(image[sector * SEC : (sector + 1) * SEC])
        handle.write(form1(22, image[22 * SEC + 16 : 22 * SEC + 24], bytes(records)))
        for _pos, _name, extent, data in placed:
            offset = 0
            sector = extent
            while offset < len(data):
                chunk = data[offset : offset + USER]
                if len(chunk) < USER:
                    chunk += b"\x00" * (USER - len(chunk))
                handle.write(form1(sector, DATA_SUB, chunk))
                offset += USER
                sector += 1
        empty = b"\x00" * USER
        for sector in range(tail_at, total):
            handle.write(form1(sector, TAIL_SUB, empty))

    # The directory we just wrote must point at the bytes we just wrote.
    written = OUT.read_bytes()
    for name, source in REPLACEMENTS.items():
        match = [item for item in placed if item[1] == name]
        if len(match) != 1:
            raise SystemExit(f"{name!r} was not in the directory")
        _pos, _name, extent, data = match[0]
        if read_file(written, extent, len(data)) != source.read_bytes():
            raise SystemExit(f"{name.decode()} did not round-trip")
    # One rewritten sector must satisfy the same EDC the originals do.
    sample = written[24 * SEC : 25 * SEC]
    if struct.unpack_from("<I", sample, 2072)[0] != edc(sample[16:2072]):
        raise SystemExit("EDC mismatch on the first file sector")
    saved = bytearray(sample)
    saved[12:16] = b"\x00\x00\x00\x00"
    body = bytes(saved[12:2076])
    if ecc_compute(body, 86, 24, 2, 86) != sample[2076:2248]:
        raise SystemExit("ECC mismatch on the first file sector")
    print(f"wrote {OUT} ({len(written)} bytes)")

    lines = [
        'FILE "Grand Theft Auto (USA) (Track 01).bin" BINARY',
        "  TRACK 01 MODE2/2352",
        "    INDEX 01 00:00:00",
    ]
    for number in range(2, 12):
        filename = f"Grand Theft Auto (USA) (Track {number:02d}).bin"
        lines.append(f'FILE "../Grand Theft Auto (USA)/{filename}" BINARY')
        lines.append(f"  TRACK {number:02d} AUDIO")
        lines.append("    INDEX 00 00:00:00")
        lines.append("    INDEX 01 00:02:00" if number == 2 else "    INDEX 01 00:01:00")
    CUE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {CUE}")


if __name__ == "__main__":
    main()
