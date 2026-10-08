"""Phase 380 (F129, the operator's 1A): give every seed entry a frozen key.

Run once from the repository root:
`.venv/bin/python docs/phases/in_progress/380_add_keys.py`. Committed in the
phase folder because its output ships (K24).

A key is the first make's slug and the title's slug (ASCII, lowercase,
hyphens, at most 60 characters at a word break), made unique with `-2`,
`-3` … in file and entry order. Once written it is never regenerated: a
later title, make or model edit leaves it alone, which is the point.

69 of the 110 files are hand-formatted (arrays on one line) and one is
compact (an object per line), so a file is never re-serialised. The key goes
in right after each object's opening `{`, before its `"title"` (the first
key of every entry), in the file's own style: on its own line at the title's
indent, or inline without spaces in the compact file. Each file is checked:
- it parses to the old data with each entry's key added;
- deleting the inserted text gives back the original bytes exactly.

Nothing is written until every file passes, so a failure leaves no file
half-done (the first run wrote 27 files before stopping on the compact one).

A file that already has keys is refused, so a second run cannot rewrite
them.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[3]
SEED = ROOT / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"
OBJECT_TITLE = re.compile(r'\{(?P<ws>\s*)"title"\s*:')


def slug(text: str, limit: int = 60) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    words = re.findall(r"[a-z0-9]+", ascii_text.lower())
    out = ""
    for w in words:
        nxt = f"{out}-{w}" if out else w
        if len(nxt) > limit:
            break
        out = nxt
    return out or "row"


def base_key(entry: dict) -> str:
    first_make = (entry.get("make") or "general").split(",")[0]
    return f"{slug(first_make, 24)}-{slug(entry['title'])}"


def main() -> int:
    files = sorted(SEED.glob("known_issues_*.json"))
    taken: set[str] = set()
    plan: list[tuple[pathlib.Path, str, list[dict], list[str]]] = []
    for path in files:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if any("key" in e for e in data):
            print(f"REFUSED: {path.name} already has keys; they are frozen")
            return 1
        keys = []
        for entry in data:
            key, n = base_key(entry), 2
            while key in taken:
                key, n = f"{base_key(entry)}-{n}", n + 1
            taken.add(key)
            keys.append(key)
        plan.append((path, raw, data, keys))

    written: list[tuple[pathlib.Path, str]] = []
    for path, raw, data, keys in plan:
        matches = list(OBJECT_TITLE.finditer(raw))
        assert len(matches) == len(data), f"{path.name}: {len(matches)} objects, {len(data)} entries"
        out, inserted, last = [], [], 0
        for m, key in zip(matches, keys):
            ws = m.group("ws")
            text = (f'"key": {json.dumps(key)},{ws}' if "\n" in ws
                    else f'"key":{json.dumps(key)},')
            cut = m.start() + 1 + len(ws)
            out.append(raw[last:cut])
            out.append(text)
            inserted.append(text)
            last = cut
        out.append(raw[last:])
        new = "".join(out)
        assert json.loads(new) == [{"key": k, **e} for k, e in zip(keys, data)], (
            f"{path.name}: the data changed beyond the keys")
        restored = new
        for text in inserted:
            restored = restored.replace(text, "", 1)
        assert restored == raw, f"{path.name}: more than the keys changed"
        written.append((path, new))
    for path, new in written:
        path.write_text(new, encoding="utf-8")
    print(f"keyed {sum(len(d) for _, _, d, _ in plan)} entries in {len(written)} files; "
          f"{len(taken)} distinct keys")
    return 0


if __name__ == "__main__":
    sys.exit(main())
