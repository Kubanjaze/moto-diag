#!/usr/bin/env python3
"""The ONE implementation of the ROADMAP 120-word count.

The method is specified in words in the workspace `CLAUDE.md` rule "ROADMAP
rows are an index, not the record". That rule is the specification and must
stay readable without running anything; this file is the only place the
specification is executed.

Why one implementation. The cap was argued about twice rather than applied —
at 115 / 126 and again at 117 / 122 — because three different methods were
in use at once, and nobody had written down which was meant. The third was
inside the verify block itself: `awk '{print "tokens:", NF-1}'` over the
whole row, pipes and title included, which is the method that would have
passed a 122-word row.

The method:
  1. The BODY CELL only — the fourth pipe-delimited cell. Not the phase
     number, the title, the status glyph, and not the pipes.
  2. Whitespace-split, nothing stripped first. `**CLOSED` is one word.
     Stripping `**` before splitting merges tokens and changes the answer,
     which caused one of the two disputes.
  3. A markdown link is ONE word, however long its text or URL.

Usage:
    roadmap_words.py <phase>            # count, exit 0
    roadmap_words.py <phase> --check    # exit 1 if over the cap
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

CAP = 120
_LINK = re.compile(r"\[[^\]]*\]\([^)]*\)")


def body_cell(line: str) -> str:
    """The fourth pipe-delimited cell of a ROADMAP row."""
    cells = line.rstrip("\n").split("|")
    if len(cells) < 5:
        raise ValueError(f"not a 4-column ROADMAP row: {line[:60]!r}")
    return cells[4]


def count(cell: str) -> int:
    """Words, by the specified method. A markdown link collapses to one."""
    return len(_LINK.sub("LINK", cell).split())


def row_for(phase: str, roadmap: pathlib.Path) -> str:
    prefix = f"| {phase} |"
    for line in roadmap.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            return line
    raise LookupError(f"no ROADMAP row for phase {phase!r}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("phase")
    ap.add_argument("--roadmap", default="docs/ROADMAP.md")
    ap.add_argument("--check", action="store_true",
                    help=f"exit 1 if the body cell exceeds {CAP} words")
    a = ap.parse_args(argv)
    try:
        n = count(body_cell(row_for(a.phase, pathlib.Path(a.roadmap))))
    except (LookupError, ValueError) as e:
        print(f"roadmap_words: {e}", file=sys.stderr)
        return 2
    if a.check and n > CAP:
        print(f"roadmap_words: phase {a.phase} body cell is {n} words, "
              f"cap is {CAP} (over by {n - CAP})", file=sys.stderr)
        return 1
    print(n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
