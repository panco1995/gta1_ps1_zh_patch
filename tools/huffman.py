#!/usr/bin/env python3
"""Decode English MISSION.VSR string payloads.

Each string blob starts with an 8-byte chain header taken from the previous
record. The bytes after that are an MSB-first prefix code. Codes were recovered
from the shared damage-message plaintext and then extended from the other
mission lines.
"""

from __future__ import annotations

CODES: dict[str, tuple[int, int]] = {
    ' ': (3, 0),
    '!': (6, 58),
    '$': (12, 1749),
    "'": (6, 62),
    ',': (7, 106),
    '-': (10, 153),
    '.': (6, 37),
    '0': (7, 62),
    '1': (7, 63),
    '2': (7, 55),
    '3': (7, 47),
    '4': (8, 214),
    '5': (8, 155),
    '6': (8, 187),
    '7': (8, 244),
    '8': (9, 112),
    '9': (9, 372),
    ':': (11, 304),
    '?': (9, 304),
    'A': (8, 92),
    'B': (8, 215),
    'C': (8, 108),
    'D': (8, 156),
    'E': (7, 92),
    'F': (9, 219),
    'G': (8, 93),
    'H': (8, 153),
    'I': (7, 45),
    'J': (10, 227),
    'K': (10, 226),
    'L': (8, 157),
    'M': (8, 240),
    'N': (8, 57),
    'O': (7, 79),
    'P': (9, 305),
    'Q': (14, 2442),
    'R': (8, 154),
    'S': (7, 121),
    'T': (7, 44),
    'U': (9, 77),
    'V': (9, 490),
    'W': (8, 241),
    'X': (13, 1220),
    'Y': (8, 39),
    'Z': (11, 875),
    'a': (4, 12),
    'b': (6, 59),
    'c': (6, 26),
    'd': (6, 8),
    'e': (4, 4),
    'f': (7, 18),
    'g': (6, 47),
    'h': (5, 14),
    'i': (5, 6),
    'j': (9, 491),
    'k': (7, 29),
    'l': (5, 27),
    'm': (6, 30),
    'n': (5, 5),
    'o': (4, 8),
    'p': (6, 63),
    'q': (11, 1495),
    'r': (5, 12),
    's': (5, 10),
    't': (4, 10),
    'u': (5, 28),
    'v': (7, 123),
    'w': (6, 52),
    'x': (10, 436),
    'y': (6, 15),
    'z': (12, 1748)
}


def decode(payload: bytes) -> tuple[str, int]:
    """Return decoded text and the number of bits consumed."""
    bylen: dict[int, dict[int, str]] = {}
    for ch, (ln, val) in CODES.items():
        bylen.setdefault(ln, {})[val] = ch
    mx = max(bylen)
    out: list[str] = []
    pos = 0
    nbits = len(payload) * 8
    while pos < nbits:
        acc = 0
        found: tuple[str, int] | None = None
        for ln in range(1, mx + 1):
            if pos + ln > nbits:
                break
            acc = (acc << 1) | ((payload[(pos + ln - 1) >> 3] >> (7 - ((pos + ln - 1) & 7))) & 1)
            ch = bylen.get(ln, {}).get(acc)
            if ch:
                found = (ch, ln)
                break
        if found is None:
            break
        out.append(found[0])
        pos += found[1]
    return "".join(out), pos
