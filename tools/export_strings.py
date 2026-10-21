#!/usr/bin/env python3
"""Export PS1 MISSION.VSR string slots joined to the PC English FXT reference.

The PS1 blobs are still Huffman-compressed. This table is the translation
worksheet: one row per mission string id, with the PC English line as the
source text. `zh` is left empty. A row is flagged when the same id does not
share one compressed payload across cities.
"""

import csv
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VSR = ROOT / "extract" / "MISSION.VSR"
FXT = ROOT / "ref" / "ENGLISH.FXT.txt"
OUT = ROOT / "text" / "zh_todo.tsv"

# English text bin, group name. UI bins use a local 0..n index.
GROUPS = [
    (0, "NON_INT", True),
    (6, "FRONTEND", True),
    (19, "Easy Liberty City", False),
    (26, "Medium Liberty City", False),
    (33, "San Andreas medium", False),
    (40, "San Andreas hard", False),
    (47, "Vice City 1", False),
    (54, "Vice City 2", False),
]


def bins_of(data: bytes) -> list[bytes]:
    atad = data.find(b"ATAD")
    if atad < 0:
        raise SystemExit("ATAD chunk not found")
    size = struct.unpack_from("<I", data, atad + 4)[0]
    end = atad + 8 + size
    i = atad + 8
    out = []
    while i + 8 <= end:
        sz = struct.unpack_from("<I", data, i + 4)[0]
        out.append(data[i + 8 : i + 8 + sz])
        i += 8 + sz
    return out


def string_chunks(blob: bytes) -> dict[int, bytes]:
    if len(blob) < 8:
        return {}
    size = struct.unpack_from("<I", blob)[0]
    if not (8 < size < len(blob)) or size % 4:
        return {}
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
    base = size
    out = {}
    for n, (sid, off) in enumerate(pairs):
        nxt = pairs[n + 1][1] if n + 1 < len(pairs) else len(blob) - base
        if off <= nxt <= len(blob) - base:
            out[sid] = blob[base + off : base + nxt]
    return out


def load_fxt(path: Path) -> dict[str, str]:
    text = path.read_bytes().decode("latin1")
    out = {}
    for line in text.split("\n"):
        line = line.rstrip("\r")
        if not (line.startswith("[") and "]" in line):
            continue
        key, body = line[1:].split("]", 1)
        if body.endswith(" "):
            body = body[:-1]
        out.setdefault(key, body)
    return out


def payload_tail(blob: bytes) -> bytes:
    # The first 8 bytes change per file even when the text is the same.
    # The bytes after that are the stable compressed payload.
    return blob[8:] if len(blob) > 8 else blob


def main() -> None:
    blobs = bins_of(VSR.read_bytes())
    fxt = load_fxt(FXT)

    mission: dict[int, dict[str, bytes]] = {}
    ui: list[tuple[str, int, bytes]] = []
    for bin_i, name, is_ui in GROUPS:
        for sid, raw in string_chunks(blobs[bin_i]).items():
            if is_ui:
                ui.append((name, sid, raw))
            else:
                mission.setdefault(sid, {})[name] = raw

    OUT.parent.mkdir(parents=True, exist_ok=True)
    n_flagged = 0
    n_with_en = 0
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["id", "english", "zh", "groups", "payload_hex", "payload_note"])
        for sid in sorted(mission):
            slots = mission[sid]
            tails = {name: payload_tail(blob) for name, blob in slots.items()}
            unique = {tail.hex() for tail in tails.values()}
            if len(unique) == 1:
                payload = next(iter(unique))
                note = ""
            else:
                payload = " | ".join(f"{name}:{tails[name].hex()}" for name in slots)
                note = "payload differs by city"
                n_flagged += 1
            english = fxt.get(str(sid), "")
            if english:
                n_with_en += 1
            w.writerow([sid, english, "", ",".join(slots), payload, note])
        for name, sid, raw in ui:
            w.writerow(
                [
                    f"{name}:{sid}",
                    "",
                    "",
                    name,
                    payload_tail(raw).hex(),
                    "ui index, not an FXT id",
                ]
            )
    print(
        f"wrote {OUT} mission={len(mission)} with_english={n_with_en} "
        f"flagged={n_flagged} ui={len(ui)}"
    )


if __name__ == "__main__":
    main()
