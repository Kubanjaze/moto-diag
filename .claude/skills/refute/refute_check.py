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

and, since Phase 358 (K9, the operator's three-round rule), over a fifth
column `round · kind · outcome` — `2 · factual · fixed`, `3 · wording ·
open F163`, `1 · none · kept`:

  C5  every row carries the column, and no round is above 3
  C6  no factual or citation defect is still open: the row does not ship
  C7  open wording defects all cite one and the same F-number (the one
      finding they go to; finding_check B2 resolves it)

The seven checklists written before the column existed are a pinned
exemption from it (`OLD_FORMAT`), with an equality control in
`tests/test_phase358_refute_rounds.py`. What no check can see, and the
skill states as text: that a fix deleted a sentence rather than rewrote
it, and that rounds 2+ refuted the diff and its neighbours, not the row.
"""
from __future__ import annotations

import pathlib
import re
import sys

HEADER = "## Refuter pass"
#: A row: | claim | kept/killed | "quote" | document p.N | round · kind · outcome |
_ROW = re.compile(r"^\|(?P<claim>[^|]+)\|(?P<verdict>[^|]+)\|"
                  r"(?P<quote>[^|]+)\|(?P<source>[^|]+)\|(?:(?P<rko>[^|]*)\|)?\s*$")
_RKO = re.compile(r"^\s*(\d+)\s*[·/]\s*(none|wording|factual|citation)\s*[·/]\s*"
                  r"(kept|fixed|deleted|open)(?:\s+(F\d{2,4}))?\s*$", re.I)
MAX_ROUNDS = 3
#: The checklists written before the fifth column, measured 2026-09-27: every
#: closed log with a `## Refuter pass` block. Pinned; the test recomputes it.
OLD_FORMAT = frozenset({"257", "260", "261", "262", "264", "353", "354"})
_VERDICT = re.compile(r"\b(kept|killed)\b", re.I)
_QUOTED = re.compile(r"[\"“”']\s*\S")
_PAGE = re.compile(r"\bp{1,2}\.?\s*\d+|\bpage\s*\d+", re.I)


def check(text: str, require_rounds: bool = True) -> list[str]:
    """`require_rounds=False` only for a phase in OLD_FORMAT."""
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
        cells = {k: (v or "").strip() for k, v in m.groupdict().items()}
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
    if require_rounds:
        fails += _rounds(rows)
    return fails


def _rounds(rows: list[dict]) -> list[str]:
    fails, findings = [], set()
    for i, r in enumerate(rows, 1):
        name = repr(r["claim"][:34])
        m = _RKO.match(r["rko"])
        if not m:
            fails.append(f"C5 row {i} ({name}) has no 'round · kind · outcome' cell "
                         f"that parses: {r['rko']!r}")
            continue
        rnd, kind, outcome, finding = int(m.group(1)), m.group(2).lower(), \
            m.group(3).lower(), m.group(4)
        if rnd > MAX_ROUNDS:
            fails.append(f"C5 row {i} ({name}) is round {rnd}; at most {MAX_ROUNDS} "
                         "refute rounds")
        if outcome == "open" and kind in ("factual", "citation"):
            fails.append(f"C6 row {i} ({name}) has an open {kind} defect: the row "
                         "does not ship")
        if outcome == "open" and kind == "wording":
            if finding is None:
                fails.append(f"C7 row {i} ({name}) leaves a wording defect open with "
                             "no finding")
            else:
                findings.add(finding.upper())
    if len(findings) > 1:
        fails.append(f"C7 open wording defects go to ONE finding, not {sorted(findings)}")
    return fails


ASSERTION_IDS = ("C1", "C2", "C3", "C4", "C5", "C6", "C7")


def main() -> int:
    p = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if p is None:
        print("usage: refute_check.py <phase_log.md>", file=sys.stderr)
        return 2
    phase = re.match(r"(\d+[A-Z]?)_", p.name)
    fails = check(p.read_text(encoding="utf-8", errors="replace"),
                  require_rounds=not (phase and phase.group(1) in OLD_FORMAT))
    for f in fails:
        print(f)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
