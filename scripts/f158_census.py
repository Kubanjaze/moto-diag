#!/usr/bin/env python3
"""F158 census: build references in text a user can see (Phase 358, K4).

F158: rows carried "Phase N", "Track X", finding numbers and "this phase"
into descriptions a mechanic reads. Two census scripts gave two answers on
one database (68 hits with three patterns, 79 with four), and the guard F158
proposed was never written. This is the one census; the ratchet in
`tests/test_phase358_f158_ratchet.py` uses it.

Every text column of every table, four patterns. Taken from Phase 262's
`f158.py` (kept verbatim in `358_step0.md`, sha256 2e034109…).

    python scripts/f158_census.py DB           the count, by table and pattern
    python scripts/f158_census.py DB --plant   the control: a copy of DB with
                                               "Phase 999" in one known_issues
                                               row must show exactly that hit

Never point it at data/motodiag.db from a test. The deploy script runs it on
a dry-run copy, and the ratchet on a database it builds.
"""
from __future__ import annotations

import collections
import pathlib
import re
import shutil
import sqlite3
import sys

PATTERNS = {
    "Phase N": re.compile(r"\bPhase \d+"),
    "Track X": re.compile(r"\bTrack [A-Z]\b"),
    "F-number": re.compile(r"\bF\d{2,3}\b"),
    "this phase": re.compile(r"this phase", re.I),
}
#: Tables a mechanic walks through; they must carry no build reference.
WORKFLOW_TABLES = ("workflow_templates", "checklist_items")
#: Phase 359. BMW's F-series model names match the F-number pattern. An
#: F-number hit is a model name, not a finding, when its token is one of
#: these and its row's `make` column names BMW; any other F-number stays a
#: reference.
BMW_F_MODELS = frozenset({"F650", "F700", "F750", "F800", "F850", "F900"})
#: User and operational data: reported, never rewritten by a content phase.
OPERATIONAL_TABLES = ("shops", "customer_notifications")

Hit = tuple[str, str, int, str, str]            # table, column, rowid, pattern, text


def census(db: str | pathlib.Path) -> list[Hit]:
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    hits: list[Hit] = []
    try:
        tables = [r[0] for r in c.execute(
            "select name from sqlite_master where type='table' and name not like 'sqlite_%'")]
        for t in tables:
            cols = [r[1] for r in c.execute(f'pragma table_info("{t}")')
                    if (r[2] or "").upper() in ("TEXT", "") or "CHAR" in (r[2] or "").upper()]
            for col in cols:
                for rowid, v in c.execute(f'select rowid, "{col}" from "{t}" where "{col}" is not null'):
                    if isinstance(v, str):
                        for name, p in PATTERNS.items():
                            hits += [(t, col, rowid, name, m.group()) for m in p.finditer(v)]
    finally:
        c.close()
    return hits


def build_references(db: str | pathlib.Path) -> list[Hit]:
    """The census minus its two exclusions: BMW model names, and rows in
    operational tables. What is left is a build reference in content."""
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        def is_bmw_model(t: str, rowid: int, token: str) -> bool:
            if token not in BMW_F_MODELS:
                return False
            if "make" not in {r[1] for r in c.execute(f'pragma table_info("{t}")')}:
                return False
            make = c.execute(f'select make from "{t}" where rowid = ?', (rowid,)).fetchone()[0]
            return "BMW" in (make or "")
        return [h for h in census(db) if h[0] not in OPERATIONAL_TABLES
                and not (h[3] == "F-number" and is_bmw_model(h[0], h[2], h[4]))]
    finally:
        c.close()


def ratchet(hits: list[Hit], ceiling: int) -> list[str]:
    """Why the count breaks the ratchet; [] when it holds. The count may only
    fall, and when it falls the ceiling must follow it down."""
    fails = []
    wf = [h for h in hits if h[0] in WORKFLOW_TABLES]
    if wf:
        fails.append(f"{len(wf)} build reference(s) in workflow rows: {wf[:5]}")
    if len(hits) > ceiling:
        fails.append(f"{len(hits)} hits, above the ceiling of {ceiling}: a new build "
                     "reference reached text a user sees")
    elif len(hits) < ceiling:
        fails.append(f"{len(hits)} hits, below the ceiling of {ceiling}: lower "
                     f"F158_CEILING to {len(hits)} so it cannot rise again")
    return fails


def report(hits: list[Hit]) -> str:
    rows = len({(t, r) for t, _, r, _, _ in hits})
    lines = [f"total hits {len(hits)} in {rows} rows"]
    for k, v in sorted(collections.Counter((t, c, n) for t, c, _, n, _ in hits).items()):
        lines.append(f"  {k} {v}")
    return "\n".join(lines)


def plant_control(db: str) -> bool:
    cp = pathlib.Path(db).with_suffix(".plant.db")
    shutil.copy(db, cp)
    try:
        c = sqlite3.connect(cp)
        rid = c.execute("select min(rowid) from known_issues").fetchone()[0]
        c.execute("update known_issues set description = description || ' Phase 999' where rowid=?",
                  (rid,))
        c.commit()
        c.close()
        extra = [h for h in census(cp) if h not in census(db)]
        return len(extra) == 1 and extra[0][4] == "Phase 999"
    finally:
        cp.unlink(missing_ok=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    if "--plant" in sys.argv:
        ok = plant_control(sys.argv[1])
        print("plant control:", "found exactly the planted hit" if ok else "FAILED")
        raise SystemExit(0 if ok else 1)
    print(report(census(sys.argv[1])))
    refs = build_references(sys.argv[1])
    print(f"build references after the exclusions (BMW model names, operational rows): {len(refs)}")
    for h in refs:
        print("  ", h)
