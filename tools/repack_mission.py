#!/usr/bin/env python3
"""Rebuild MISSION.VSR so the English slots carry UTF-8 Simplified Chinese.

The game's text walker (0x8010a5b0) reads one string as a byte-aligned
bitstream that starts after an 8-byte head and stops at a decoded NUL.
That head is the tail of the previous string, which is why a slot's own
bytes often stop mid-word: the rest, including the NUL, sits in the next
record's head. This writer keeps that layout, swaps in a new English
Huffman tree, and leaves the other five languages untouched.
"""

import csv
import heapq
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VSR = ROOT / "extract" / "MISSION.VSR"
ZH = ROOT / "text" / "zh_cn.tsv"
OUT = ROOT / "build" / "MISSION.VSR"

# English text bins, then the English Huffman table. Language order in each
# city group is EN, FR, DE, IT, ES, JP, so bin 12 is the table English uses.
EN_TEXT = [0, 6, 19, 26, 33, 40, 47, 54]
EN_HUFF = 12
MISSION = {19, 26, 33, 40, 47, 54}
DIR_START = 136
DIR_STRIDE = 40


class Node:
    _seq = 0

    def __init__(self, weight, char=None, left=None, right=None):
        self.w = weight
        self.ch = char
        self.l = left
        self.r = right
        Node._seq += 1
        self.seq = Node._seq

    def __lt__(self, other):
        return (self.w, self.seq) < (other.w, other.seq)


def build_tree(freq: dict[int, int]) -> Node:
    heap = [Node(w, ch) for ch, w in freq.items()]
    heapq.heapify(heap)
    if len(heap) == 1:
        only = heap.pop()
        heapq.heappush(heap, Node(only.w, None, only, Node(0, 0)))
    while len(heap) > 1:
        a = heapq.heappop(heap)
        b = heapq.heappop(heap)
        heapq.heappush(heap, Node(a.w + b.w, None, a, b))
    return heap[0]


def pack_tree(root: Node) -> list[int]:
    """u16 nodes in the shape 0x8010a5b0 walks.

    Children of a node are adjacent. Bit 0 selects the left one. The low two
    bits of an internal node are leaf flags: bit 1 for the bit-0 child, bit 0
    for the bit-1 child. A leaf's low byte is the symbol.
    """
    slots: list[int] = []

    def alloc() -> int:
        slots.append(0)
        return len(slots) - 1

    def fill(node: Node, index: int) -> None:
        if node.ch is not None:
            slots[index] = node.ch & 0xFF
            return
        left = alloc()
        right = alloc()
        delta = left - index
        if not 0 < delta <= 0x3FFF:
            raise SystemExit(f"tree delta {delta} does not fit in 14 bits")
        flags = 0
        if node.l.ch is not None:
            flags |= 2
        if node.r.ch is not None:
            flags |= 1
        slots[index] = (delta << 2) | flags
        fill(node.l, left)
        fill(node.r, right)

    fill(root, alloc())
    return slots


def codes_of(node: Node, prefix: str = "") -> dict[int, str]:
    if node.ch is not None:
        return {node.ch: prefix or "0"}
    out = codes_of(node.l, prefix + "0")
    out.update(codes_of(node.r, prefix + "1"))
    return out


def encode_bytes(data: bytes, codes: dict[int, str]) -> bytes:
    bits = "".join(codes[b] for b in data)
    if len(bits) % 8:
        bits += "0" * (8 - len(bits) % 8)
    return bytes(int(bits[i : i + 8], 2) for i in range(0, len(bits), 8))


def tree_blob(slots: list[int]) -> bytes:
    # The loader treats the first u16 as the start index and copies the rest.
    table = b"".join(struct.pack("<H", w) for w in slots)
    body = struct.pack("<H", 0) + table
    return struct.pack("<I", len(body)) + body


def load_tree(blob: bytes) -> tuple[bytes, int]:
    size = struct.unpack_from("<I", blob)[0]
    body = blob[4 : 4 + size]
    root = struct.unpack_from("<H", body)[0]
    return body[2:], root


def decode_until_nul(table: bytes, root: int, payload: bytes, limit: int = 800) -> tuple[bytes, int]:
    mask = 0
    byte = 0
    pos = 0
    out = bytearray()
    while len(out) < limit:
        index = root
        for _ in range(100000):
            if mask == 0:
                if pos >= len(payload):
                    raise ValueError("bitstream ended before NUL")
                byte = payload[pos]
                pos += 1
                mask = 0x80
            off = index * 2
            if off + 1 >= len(table):
                raise ValueError(f"node {index} is outside the table")
            entry = struct.unpack_from("<H", table, off)[0]
            bit = 1 if (byte & mask) else 0
            new = index + (entry >> 2) + bit
            flag = entry & (1 if bit else 2)
            mask >>= 1
            if flag:
                if new * 2 >= len(table):
                    raise ValueError(f"leaf {new} is outside the table")
                out.append(table[new * 2])
                break
            index = new
        else:
            raise ValueError("Huffman walk did not reach a leaf")
        if out[-1] == 0:
            return bytes(out[:-1]), pos
    raise ValueError("string longer than the decoder limit")


def pairs_of(blob: bytes) -> tuple[int, list[tuple[int, int]], bytes, bytes]:
    size = struct.unpack_from("<I", blob)[0]
    words = struct.unpack_from("<" + "I" * (size // 4), blob)
    pairs = []
    prev = -1
    idx = 1
    while idx + 1 < len(words):
        sid, off = words[idx], words[idx + 1]
        if off < prev or off > len(blob):
            break
        prev = off
        pairs.append((sid, off))
        idx += 2
    if 8 + 8 * len(pairs) != size:
        raise SystemExit(f"index size {size} does not match {len(pairs)} strings")
    gap = blob[size - 4 : size]
    return size, pairs, gap, blob[size:]


def decode_bin(blob: bytes, table: bytes, root: int) -> list[tuple[int, bytes]]:
    _size, pairs, _gap, stream = pairs_of(blob)
    out = []
    for i, (sid, off) in enumerate(pairs):
        start = off + 8
        if i + 1 < len(pairs):
            window = stream[start : pairs[i + 1][1] + 8]
        else:
            window = stream[start:]
        text, _pos = decode_until_nul(table, root, window)
        out.append((sid, text))
    return out


def rebuild_stream(blob: bytes, texts: dict[int, bytes], codes: dict[int, str]) -> bytes:
    size, pairs, gap, stream = pairs_of(blob)
    head0 = stream[:8]
    payloads = []
    tails = []
    for sid, _off in pairs:
        raw = encode_bytes(texts[sid] + b"\x00", codes)
        if len(raw) < 8:
            raw += b"\x00" * (8 - len(raw))
        payloads.append(raw[:-8])
        tails.append(raw[-8:])
    out = bytearray(head0)
    offsets = [0]
    for i, payload in enumerate(payloads):
        out += payload
        if i + 1 < len(payloads):
            offsets.append(len(out))
        out += tails[i]
    rebuilt = bytearray(struct.pack("<I", size))
    for (sid, _off), offset in zip(pairs, offsets):
        rebuilt += struct.pack("<II", sid, offset)
    rebuilt += gap
    rebuilt += out
    return bytes(rebuilt)


def walk_chunks(data: bytes) -> tuple[int, list[tuple[bytes, bytes]]]:
    atad = data.find(b"ATAD")
    if atad < 0:
        raise SystemExit("ATAD chunk not found")
    size = struct.unpack_from("<I", data, atad + 4)[0]
    end = atad + 8 + size
    i = atad + 8
    chunks = []
    while i + 8 <= end:
        tag = data[i : i + 4]
        sz = struct.unpack_from("<I", data, i + 4)[0]
        chunks.append((tag, data[i + 8 : i + 8 + sz]))
        i += 8 + sz
    if i != end or len(chunks) != 60:
        raise SystemExit(f"chunk walk ended at {i} of {end} with {len(chunks)} bins")
    return atad, chunks


def write_vsr(original: bytes, chunks: list[tuple[bytes, bytes]]) -> bytes:
    atad, old = walk_chunks(original)
    if len(old) != len(chunks):
        raise SystemExit("chunk count changed")
    body = bytearray()
    offsets = []
    pos = atad + 8
    for (tag, _old), (_tag, payload) in zip(old, chunks):
        offsets.append(pos)
        body += tag + struct.pack("<I", len(payload)) + payload
        pos += 8 + len(payload)
    out = bytearray(original[: atad + 8]) + body
    atad_size = len(body)
    struct.pack_into("<I", out, atad + 4, atad_size)
    struct.pack_into("<I", out, 4, len(out) - 8)
    struct.pack_into("<I", out, 0x14, atad_size)
    for i, ((tag, payload), offset) in enumerate(zip(chunks, offsets)):
        ent = DIR_START + i * DIR_STRIDE
        struct.pack_into("<I", out, ent, offset)
        struct.pack_into("<I", out, ent + 4, len(payload))
    return bytes(out)


def load_zh() -> dict[int, bytes]:
    out = {}
    for row in csv.DictReader(ZH.open(encoding="utf-8"), delimiter="\t"):
        text = row["zh"].replace("\r", "").replace("\n", "")
        if not text:
            raise SystemExit(f"id {row['id']} has an empty translation")
        out[int(row["id"])] = text.encode("utf-8")
    return out


def main() -> None:
    original = VSR.read_bytes()
    _atad, chunks = walk_chunks(original)
    table, root = load_tree(chunks[EN_HUFF][1])
    decoded = {i: decode_bin(chunks[i][1], table, root) for i in EN_TEXT}

    # The layout has to round-trip before any translation is substituted.
    freq: dict[int, int] = {}
    for rows in decoded.values():
        for _sid, text in rows:
            for b in text + b"\x00":
                freq[b] = freq.get(b, 0) + 1
    trial_root = build_tree(freq)
    trial_slots = pack_tree(trial_root)
    trial_codes = codes_of(trial_root)
    trial_tree = load_tree(tree_blob(trial_slots))
    for index, rows in decoded.items():
        blob = rebuild_stream(chunks[index][1], {sid: text for sid, text in rows}, trial_codes)
        again = decode_bin(blob, *trial_tree)
        if again != rows:
            raise SystemExit(f"English round-trip failed on bin {index}")
    print("english round-trip ok")

    zh = load_zh()
    mission_ids = {sid for i in MISSION for sid, _ in decoded[i]}
    missing = sorted(mission_ids - zh.keys())
    extra = sorted(set(zh) - mission_ids)
    if missing or extra:
        raise SystemExit(f"translation ids missing {missing[:8]} extra {extra[:8]}")

    texts: dict[int, dict[int, bytes]] = {}
    used: dict[int, int] = {}
    for index, rows in decoded.items():
        texts[index] = {}
        for sid, text in rows:
            if index in MISSION:
                texts[index][sid] = zh[sid]
            else:
                texts[index][sid] = text
            for b in texts[index][sid] + b"\x00":
                used[b] = used.get(b, 0) + 1
    tree = build_tree(used)
    slots = pack_tree(tree)
    codes = codes_of(tree)
    huff = tree_blob(slots)
    print(f"huffman symbols {len(used)} nodes {len(slots)} table {len(huff)} bytes")

    new_chunks = list(chunks)
    for index in EN_TEXT:
        blob = rebuild_stream(chunks[index][1], texts[index], codes)
        got = decode_bin(blob, *load_tree(huff))
        want = [(sid, texts[index][sid]) for sid, _ in decoded[index]]
        if got != want:
            raise SystemExit(f"rebuild decode mismatch on bin {index}")
        old_len = len(chunks[index][1])
        if len(blob) < old_len:
            blob += b"\x00" * (old_len - len(blob))
        new_chunks[index] = (chunks[index][0], blob)
        print(f"bin {index:2} {old_len:6} -> {len(blob):6}")
    old_huff = len(chunks[EN_HUFF][1])
    huff_out = huff + b"\x00" * max(0, old_huff - len(huff))
    new_chunks[EN_HUFF] = (chunks[EN_HUFF][0], huff_out)
    print(f"bin {EN_HUFF:2} {old_huff:6} -> {len(huff_out):6}")

    # Confirm the bytes the game will walk, including a padded bin.
    for index in EN_TEXT:
        got = decode_bin(new_chunks[index][1], *load_tree(huff_out))
        want = [(sid, texts[index][sid]) for sid, _ in decoded[index]]
        if got != want:
            raise SystemExit(f"padded bin {index} does not decode")

    out = write_vsr(original, new_chunks)
    check_atad, check_chunks = walk_chunks(out)
    if [c[1] for c in check_chunks] != [c[1] for c in new_chunks]:
        raise SystemExit("rewritten container does not parse back")
    if struct.unpack_from("<I", out, 4)[0] != len(out) - 8:
        raise SystemExit("3RSV size was not updated")
    if struct.unpack_from("<I", out, check_atad + 4)[0] != struct.unpack_from("<I", out, 0x14)[0]:
        raise SystemExit("ATAD size copies disagree")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(out)
    print(f"wrote {OUT} ({len(out)} bytes, was {len(original)})")


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        sys.exit(str(exc))
