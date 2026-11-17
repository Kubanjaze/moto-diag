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

  C5  every row carries the column, and no round is above 3, unless the
      operator granted it (Phase 403, K88): round 3 + k names the phase's
      k-th grant after its number, `4 K89 · factual · fixed`
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
#: The block is the HEADING, on a line of its own. A sentence that names the
#: block in backticks is not the block (Phase 358 bug fix #2: 358's own log
#: described A8 as needing "the `## Refuter pass` block", and a substring
#: match read that as an empty block).
_HEADING = re.compile(r"^## Refuter pass[ \t]*$", re.M)


def find_block(text: str) -> re.Match | None:
    return _HEADING.search(text)
#: A row: | claim | kept/killed | "quote" | document p.N | round · kind · outcome |
_ROW = re.compile(r"^\|(?P<claim>[^|]+)\|(?P<verdict>[^|]+)\|"
                  r"(?P<quote>[^|]+)\|(?P<source>[^|]+)\|(?:(?P<rko>[^|]*)\|)?\s*$")
#: Since Phase 403 (K88) a round past the third names the operator's grant
#: after its number: `4 K89 · factual · fixed`.
_RKO = re.compile(r"^\s*(?P<round>\d+)(?:\s+(?P<grant>K\d+))?\s*[·/]\s*"
                  r"(?P<kind>none|wording|factual|citation)\s*[·/]\s*"
                  r"(?P<outcome>kept|fixed|deleted|open)(?:\s+(?P<finding>F\d{2,4}))?\s*$", re.I)
MAX_ROUNDS = 3
#: A grant (Phase 403, the operator's K88: "One written grant = one extra
#: round"): a `docs/decisions.md` row whose Covers cell is exactly this, for
#: one phase. Found by lookup, never by reading the row's words.
GRANT_COVERS = re.compile(r"^grant=review-round subject=(\d{2,3}[A-Z]?)$")
_GRANT_ROW = re.compile(r"^\| (K\d+) \|.*\| grant=review-round subject=(\d{2,3}[A-Z]?) \|\s*$",
                        re.M)


def grants(decisions_text: str, phase: str) -> list[str]:
    """The K-ids that grant `phase` one more review round each, in the
    file's order: round 3 + k is granted by the k-th."""
    return [kid for kid, p in _GRANT_ROW.findall(decisions_text or "") if p == phase]
#: The checklists written before the fifth column, measured 2026-09-27: every
#: closed log with a `## Refuter pass` block. Pinned; the test recomputes it.
OLD_FORMAT = frozenset({"257", "260", "261", "262", "264", "353", "354"})
_VERDICT = re.compile(r"\b(kept|killed)\b", re.I)
_QUOTED = re.compile(r"[\"“”']\s*\S")
_PAGE = re.compile(r"\bp{1,2}\.?\s*\d+|\bpage\s*\d+", re.I)


def check(text: str, require_rounds: bool = True, grants: tuple[str, ...] | list[str] = ()
          ) -> list[str]:
    """`require_rounds=False` only for a phase in OLD_FORMAT. `grants`: the
    phase's grants (`grants()`), which allow its rounds past the third."""
    fails: list[str] = []
    head = find_block(text)
    if head is None:
        return [f"C1 no '{HEADER}' block in the phase log"]

    block = text[head.end():]
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
        fails += _rounds(rows, [g.upper() for g in grants])
    return fails


def _rounds(rows: list[dict], grants: list[str]) -> list[str]:
    fails, findings = [], set()
    for i, r in enumerate(rows, 1):
        name = repr(r["claim"][:34])
        m = _RKO.match(r["rko"])
        if not m:
            fails.append(f"C5 row {i} ({name}) has no 'round · kind · outcome' cell "
                         f"that parses: {r['rko']!r}")
            continue
        rnd, kind, outcome, finding = int(m["round"]), m["kind"].lower(), \
            m["outcome"].lower(), m["finding"]
        grant = m["grant"].upper() if m["grant"] else None
        k = rnd - MAX_ROUNDS
        if k > 0 and (k > len(grants) or grant != grants[k - 1]):
            fails.append(f"C5 row {i} ({name}) is round {rnd}; at most {MAX_ROUNDS} "
                         f"refute rounds, and one more for each grant the operator wrote: "
                         f"round {rnd} must name grant {k} "
                         f"({grants[k - 1] if k <= len(grants) else 'there is none'}), "
                         f"and it names {grant or 'none'}")
        if k <= 0 and grant:
            fails.append(f"C5 row {i} ({name}) names a grant, {grant}, on round {rnd}: only "
                         f"a round past {MAX_ROUNDS} is granted")
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
    decisions = pathlib.Path("docs") / "decisions.md"
    granted = grants(decisions.read_text(encoding="utf-8"), phase.group(1)) \
        if phase and decisions.is_file() else []
    fails = check(p.read_text(encoding="utf-8", errors="replace"),
                  require_rounds=not (phase and phase.group(1) in OLD_FORMAT), grants=granted)
    for f in fails:
        print(f)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
