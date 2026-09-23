#!/usr/bin/env python3
"""Census — every (make, model) in the junction that resolves `unknown`.

No model, no sampling, no search: a rule applied to the whole junction.
That is how the figures of record were produced (F139), and the reason
this step is a script — a model counting spellings is how 427 appeared
where ~600 was true.

Usage:  census.py [DB] [--make MAKE] [--json]
"""
from __future__ import annotations

import collections
import json
import pathlib
import sqlite3
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from motodiag.knowledge.transmission import resolve_transmission  # noqa: E402


def census(db: pathlib.Path, make: str | None = None) -> dict[str, list[dict]]:
    """{make: [{"model", "rows"}]} for every unknown pair, rows descending."""
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        pairs = c.execute("SELECT make, model, count(*) FROM known_issue_models "
                          "GROUP BY make, model").fetchall()
    finally:
        c.close()
    out: dict[str, list[dict]] = collections.defaultdict(list)
    for mk, md, n in pairs:
        if make and mk != make:
            continue
        if resolve_transmission(mk, md).provenance == "unknown":
            out[mk].append({"model": md, "rows": n})
    return {mk: sorted(v, key=lambda e: (-e["rows"], e["model"]))
            for mk, v in sorted(out.items(), key=lambda kv: (-len(kv[1]), kv[0]))}


def main(argv: list[str]) -> int:
    db = pathlib.Path(next((a for a in argv if not a.startswith("--") and
                            argv[argv.index(a) - 1] != "--make"), REPO / "data" / "motodiag.db"))
    make = argv[argv.index("--make") + 1] if "--make" in argv else None
    result = census(db, make)
    if "--json" in argv:
        print(json.dumps(result, indent=1))
    else:
        for mk, entries in result.items():
            print(f"{mk:20s} {len(entries):4d} spellings  {sum(e['rows'] for e in entries):5d} junction rows")
        print(f"{'TOTAL':20s} {sum(len(v) for v in result.values()):4d} spellings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
