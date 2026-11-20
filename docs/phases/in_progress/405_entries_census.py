"""Phase 405: what the approved exact diffs committed so far hold.

Reads every `docs/phases/completed/*_dryrun_diff.md`, takes the exact diff
after its marker comment, and prints, per file and in total: the tables it
lists, their empty `added`, `removed` and `changed` dicts, any `<clock>`
inside a changed field's `[before, after]` list, and the schema's three
lists. Read-only.

    python3 docs/phases/in_progress/405_entries_census.py
"""
from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[3]
BLOCK = re.compile(r"<!-- the exact diff[^>]*-->\s*```json\n(.*?)\n```", re.S)
CLOCK = "<clock>"


def census(diff: dict) -> dict[str, object]:
    rows = diff.get("rows", {})
    empty = sum(1 for t in rows.values() for k in ("added", "removed", "changed")
                if t.get(k) == {})
    clock_pairs = sum(1 for t in rows.values() for r in t.get("changed", {}).values()
                      for v in r.values() if isinstance(v, list) and CLOCK in v)
    sch = diff.get("schema", {})
    return {"tables": len(rows), "empty dicts": empty, "clock in a changed pair": clock_pairs,
            "schema": {k: sch.get(k, []) for k in ("added", "removed", "changed")}}


def main() -> int:
    files = sorted((ROOT / "docs" / "phases" / "completed").glob("*_dryrun_diff.md"))
    with_block = with_tables = with_empty = pairs = 0
    for p in files:
        found = BLOCK.search(p.read_text(encoding="utf-8"))
        if not found:
            print(f"{p.name}: no exact diff block")
            continue
        c = census(json.loads(found.group(1)))
        with_block += 1
        if c["tables"]:
            with_tables += 1
            with_empty += bool(c["empty dicts"])
        pairs += int(c["clock in a changed pair"])  # type: ignore[call-overload]
        print(f"{p.name}: {json.dumps(c, sort_keys=True)}")
    print(f"{len(files)} files, {with_block} with an exact diff; {with_tables} list a table, "
          f"{with_empty} of them with an empty dict; <clock> inside a changed pair: {pairs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
