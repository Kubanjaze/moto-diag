#!/usr/bin/env python3
"""Finding's assertions. ONE implementation, shared by the test and any caller.

**The evidence this folder exists for is F135.** Phase 255C's plan stated a
finding was "filed on the general-applicability ticket". It was not — the
claim was written and the entry never created. It was caught at close-out
only because someone went looking for the ticket the plan cited.

So the second assertion below is the one that matters: **every F-number a
phase document cites must resolve to an entry that exists.** A document
saying a thing was filed is not the filing.

Two assertions, stable ids:

  B1  the header's "highest assigned is FNNN" matches the highest entry
      actually present in the file.
  B2  every F-number cited in a completed phase document resolves to an
      entry that exists.
"""
from __future__ import annotations

import pathlib
import re
import sys

_ENTRY = re.compile(r"^#{2,3}\s*(F(\d+))\b", re.M)
_HEADER = re.compile(r"highest assigned is \*\*F(\d+)\*\*", re.I)
_CITE = re.compile(r"\bF(\d{2,4})\b")


def entries(followups: pathlib.Path) -> set[int]:
    """Every F-number that has a real entry heading in the file."""
    try:
        txt = followups.read_text(encoding="utf-8")
    except OSError:
        return set()
    return {int(n) for _, n in _ENTRY.findall(txt)}


#: F-numbers are ONE global sequence across both repositories, so a citation
#: resolves against the UNION of both files. Checking only this repo's file
#: reports every mobile finding as dangling — 98 of them, on the first run,
#: which is the same under-scoped-denominator error this project has made
#: repeatedly. Verify the denominator before weakening the assertion.
SIBLING_FOLLOWUPS = "../moto-diag-mobile/docs/FOLLOWUPS.md"

#: Tokens shaped like an F-number that are NOT findings, each named.
#:
#: In THIS corpus that is not a theoretical concern: `F650`, `F700` and
#: `F750` are BMW motorcycles and `F401` is a flake8 code in a `# noqa:`
#: comment. A bare `F` plus digits is a model designation here at least as
#: often as a finding — the same vocabulary collision that has produced a
#: defect in nearly every phase this month.
#:
#: **An earlier cut excluded these by a CEILING** — ignore anything above the
#: highest assigned number — and the known-bad fixture caught why that is
#: wrong: a phase citing `F139` when the file stops at `F138` is *exactly*
#: F135's shape, and the ceiling silently skipped it. The rule that removes
#: the false positives also removed the one true positive it exists to find.
#: Named exclusions instead: they cannot hide a citation one past the end.
NOT_FINDINGS = {
    401: "flake8's 'imported but unused', in a `# noqa: F401` comment",
    650: "BMW F650GS — a motorcycle",
    700: "BMW F700GS — a motorcycle",
    750: "BMW F750GS — a motorcycle",
    800: "BMW F800GS — a motorcycle",
    850: "BMW F850GS — a motorcycle",
    900: "BMW F900GS — a motorcycle",
    8199: "Yamaha owner's-manual publication numbers, 'BRG-F8199-11' "
          "(Phase 257's citations) — a document number",
}

#: Citations that are known not to resolve, each with its reason. Anything
#: NOT in this set fails the check — 244U's orphan pin in the same spirit:
#: the literal records the debt, and the debt may only shrink.
KNOWN_DANGLING = {
    31: "Phase 192 proposed 'file F31 as small cross-cutting error-state "
        "policy'. The proposal was written; the entry never was.",
    32: "Phase 192, same sentence, same outcome.",
    35: "Phase 192B. Proposed and never filed.",
    48: "Not a finding at all — `F48` is a PHASE, and the citations are "
        "`F48_implementation.md` and `F48_phase_log.md` referring to "
        "themselves.",
}

def check(repo: pathlib.Path, followups: str = "docs/FOLLOWUPS.md",
          phase_docs: str = "docs/phases/completed",
          sibling: str | None = SIBLING_FOLLOWUPS) -> list[str]:
    repo = pathlib.Path(repo)
    f = repo / followups
    present = entries(f)
    if sibling:
        present |= entries(repo / sibling)
    fails: list[str] = []

    try:
        txt = f.read_text(encoding="utf-8")
    except OSError:
        return [f"B1 cannot read {followups}"]

    # B1 — the header claim matches the file's contents
    m = _HEADER.search(txt)
    if not m:
        fails.append("B1 no 'highest assigned is **FNNN**' line in the header")
    elif present:
        claimed, actual = int(m.group(1)), max(present)
        if claimed != actual:
            fails.append(f"B1 header claims highest assigned is F{claimed}, "
                         f"but the highest entry present is F{actual}")

    # B2 — every cited F-number resolves. THIS is the F135 check.
    d = repo / phase_docs
    if d.is_dir():
        dangling: dict[int, list[str]] = {}
        for doc in sorted(d.glob("*.md")):
            body = doc.read_text(encoding="utf-8", errors="replace")
            for n in {int(x) for x in _CITE.findall(body)}:
                if (n in present or n in KNOWN_DANGLING or n in NOT_FINDINGS
                        or (n, doc.name) in DESCRIBED_NOT_CITED):
                    continue
                dangling.setdefault(n, []).append(doc.name)
        if dangling:
            shown = ", ".join(
                f"F{n} (cited by {', '.join(sorted(set(v))[:2])})"
                for n, v in sorted(dangling.items())[:8])
            fails.append(
                f"B2 {len(dangling)} F-number(s) cited by a phase document "
                f"have no entry: {shown}")
    return fails


#: (number, document) pairs where a phase document DESCRIBES an F-number
#: rather than citing one.
#:
#: Found by running `verify_phase.sh` against Phase 255D itself, which is how
#: this check's own blind spot surfaced: **prose ABOUT an identifier is
#: indistinguishable from a citation OF it.** 255D's documents explain the
#: `finding` known-bad fixture, and that fixture uses fabricated numbers.
#:
#: **The first attempt pinned the numbers globally and broke the control** —
#: F139 is the fixture's deliberate one-past-the-end case, so a global pin
#: made the fixture pass and the assertion meaningless. Exactly the shape of
#: the ceiling bug it was fixing. The pin is scoped to the DOCUMENT instead,
#: so the fixture still catches F139 where it matters.
DESCRIBED_NOT_CITED = {
    (138, "255D_implementation.md"), (138, "255D_phase_log.md"),
    (139, "255D_phase_log.md"), (139, "255D_implementation.md"),
    (140, "255D_implementation.md"), (140, "255D_phase_log.md"),
}


ASSERTION_IDS = ("B1", "B2")


def main() -> int:
    repo = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    fails = check(repo)
    for x in fails:
        print(x)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
