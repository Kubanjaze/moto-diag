#!/usr/bin/env python3
"""Refute's checklist assertions. A REPORT check, and it says so.

`refute` is judgement work: whether a claim survives contact with the
documents cannot be asserted by a script. What CAN be asserted is that the
pass **emitted its checklist**, and that every row in it carries the two
things that make a human spot-check cheap — **a verbatim quote and a
document plus page.**

**The ceiling, stated rather than implied.** A complete block is consistent
with a lazy pass. Nothing here proves the PDF was opened. What it does buy
is that a reader can take any row and check it against the source **in one
step**, because the quote and the page are right there. A checklist without
them moves the work of verification back onto the reader, which is where it
was before the folder existed.

Assertions:

  C1  the block is present, with its header row
  C2  every claim row states a verdict of kept or killed
  C3  every claim row carries a verbatim quote, in quotation marks
  C4  every claim row cites a document AND a page
"""
from __future__ import annotations

import pathlib
import re
import sys

HEADER = "## Refuter pass"
#: A row: | claim | kept/killed | "quote" | document p.N |
_ROW = re.compile(r"^\|(?P<claim>[^|]+)\|(?P<verdict>[^|]+)\|"
                  r"(?P<quote>[^|]+)\|(?P<source>[^|]+)\|\s*$")
_VERDICT = re.compile(r"\b(kept|killed)\b", re.I)
_QUOTED = re.compile(r"[\"“”']\s*\S")
_PAGE = re.compile(r"\bp{1,2}\.?\s*\d+|\bpage\s*\d+", re.I)


def check(text: str) -> list[str]:
    fails: list[str] = []
    if HEADER not in text:
        return [f"C1 no '{HEADER}' block in the phase log"]

    block = text.split(HEADER, 1)[1]
    block = block.split("\n## ", 1)[0]
    rows = []
    for line in block.splitlines():
        m = _ROW.match(line)
        if not m:
            continue
        cells = {k: v.strip() for k, v in m.groupdict().items()}
        if set(cells["claim"]) <= set("-: ") or not cells["claim"]:
            continue                                   # separator / header
        if cells["claim"].lower() in ("claim",):
            continue
        rows.append(cells)

    if not rows:
        fails.append("C1 the block has a header but no claim rows")
        return fails

    for i, r in enumerate(rows, 1):
        if not _VERDICT.search(r["verdict"]):
            fails.append(f"C2 row {i} ({r['claim'][:34]!r}) has no "
                         f"kept/killed verdict: {r['verdict']!r}")
        if not _QUOTED.search(r["quote"]):
            fails.append(f"C3 row {i} ({r['claim'][:34]!r}) carries no "
                         "verbatim quote in quotation marks")
        if not _PAGE.search(r["source"]):
            fails.append(f"C4 row {i} ({r['claim'][:34]!r}) cites no page: "
                         f"{r['source'][:40]!r}")
    return fails


ASSERTION_IDS = ("C1", "C2", "C3", "C4")


def main() -> int:
    p = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if p is None:
        print("usage: refute_check.py <phase_log.md>", file=sys.stderr)
        return 2
    fails = check(p.read_text(encoding="utf-8", errors="replace"))
    for f in fails:
        print(f)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
