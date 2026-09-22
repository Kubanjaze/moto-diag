#!/usr/bin/env python3
"""Closeout's artefact assertions. ONE implementation, two callers.

`tests/test_phase255D_closeout_contract.py` calls this, and so does
`_pre_push_guard.py`. They share the function deliberately: a guard that
reimplemented the checks could pass while the test failed, and the push
would sail through the thing meant to stop it.

**What this asserts, and what it refuses to assert.** It checks the
ARTEFACTS a close-out is defined to produce — seven file facts, each one
something a skipped close-out leaves undone. It does NOT assert "closeout
ran", because that is unfalsifiable from inside a repository, and a check
that cannot fail is the defect this phase exists to stop shipping.

Each assertion has a stable id (A1..A7) so a failure names itself and the
known-bad fixture can require that each one fires.
"""
from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from roadmap_words import CAP, body_cell, count  # noqa: E402

#: A short commit hash, as the logs write them.
_HASH = re.compile(r"\b[0-9a-f]{7,40}\b")
#: A collected/passed test count, e.g. "8,091 passed" or "8091 passed".
_COUNT = re.compile(r"\b\d[\d,]{2,}\s+passed\b", re.I)


def _read(p: pathlib.Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def check(repo: pathlib.Path, phase: str) -> list[str]:
    """Return a list of failure strings. Empty means closeout is complete."""
    repo = pathlib.Path(repo)
    done = repo / "docs" / "phases" / "completed"
    prog = repo / "docs" / "phases" / "in_progress"
    impl = done / f"{phase}_implementation.md"
    log = done / f"{phase}_phase_log.md"
    fails: list[str] = []

    # A1 — both docs in completed/, neither left in in_progress/
    stray = sorted(p.name for p in prog.glob(f"{phase}_*.md")) if prog.is_dir() else []
    missing = [p.name for p in (impl, log) if not p.is_file()]
    if stray or missing:
        fails.append(
            f"A1 documents not moved to completed/: "
            f"missing={missing or 'none'} still-in-progress={stray or 'none'}")

    log_txt, impl_txt = _read(log), _read(impl)

    # A2 — the phase log's status line reads Complete
    m = re.search(r"^\*\*Status:\*\*\s*(.+)$", log_txt, re.M)
    if not m or "complete" not in m.group(1).lower():
        fails.append(f"A2 phase log Status line is not Complete: "
                     f"{(m.group(1).strip() if m else 'absent')!r}")

    # A3 — the implementation doc has a Deviations section
    if not re.search(r"^#{1,3}\s.*deviation", impl_txt, re.M | re.I):
        fails.append("A3 implementation doc has no Deviations section")

    # A4 — bug fixes are a contiguous register from #1, each naming its commit
    #
    # Heading detection is LINE-anchored on purpose. The first cut of this
    # used one `re.findall` with `re.S`, so the non-greedy `.*?` before
    # "Bug fix #" ran across newlines and matched a later heading's number
    # from an earlier heading's line — reporting #5 twice against a log whose
    # headings are a clean #1..#7. The check was wrong, not the log. A
    # DOTALL `.*?` spanning a line boundary is the same defect that ate a
    # guard in Phase 255B; it is not allowed to detect headings here.
    lines = log_txt.splitlines()
    heads = [i for i, ln in enumerate(lines) if re.match(r"^#{1,3}\s", ln)]
    entries = []
    for pos, i in enumerate(heads):
        m = re.match(r"^#{1,3}\s.*?Bug fix #(\d+)\b", lines[i], re.I)
        if not m:
            continue
        end = heads[pos + 1] if pos + 1 < len(heads) else len(lines)
        entries.append((m.group(1), "\n".join(lines[i + 1:end])))
    if entries:
        nums = [int(n) for n, _ in entries]
        expected = list(range(1, max(nums) + 1))
        if sorted(nums) != expected:
            fails.append(f"A4 bug-fix numbering is not contiguous from #1: "
                         f"found {sorted(nums)}, expected {expected}")
        no_commit = [n for n, body in entries
                     if not re.search(r"\*\*Commit\.?\*\*", body, re.I)]
        if no_commit:
            fails.append(f"A4 bug-fix entries with no Commit line: "
                         f"{sorted(int(n) for n in no_commit)}")
    # No bug fixes at all is legitimate — a phase may have found none.

    # A5 — a regression line carrying BOTH a commit hash and a count
    reg = [ln for ln in log_txt.splitlines() if re.search(r"regression", ln, re.I)]
    if not any(_HASH.search(ln) and _COUNT.search(ln) for ln in reg):
        fails.append("A5 no regression line carrying both a commit hash and a "
                     f"passed-test count (found {len(reg)} regression line(s))")

    # A6 — a ROADMAP row exists and its body cell is within the cap
    roadmap = repo / "docs" / "ROADMAP.md"
    row = next((ln for ln in _read(roadmap).splitlines()
                if ln.startswith(f"| {phase} |")), None)
    if row is None:
        fails.append(f"A6 no ROADMAP row for phase {phase}")
    else:
        try:
            n = count(body_cell(row))
            if n > CAP:
                fails.append(f"A6 ROADMAP body cell is {n} words, cap {CAP} "
                             f"(over by {n - CAP})")
        except ValueError as e:
            fails.append(f"A6 ROADMAP row is malformed: {e}")

    # A7 — implementation.md carries a row, and its header names the phase
    hist = _read(repo / "implementation.md")
    if not any(ln.startswith(f"| **{phase}** |") for ln in hist.splitlines()):
        fails.append(f"A7 implementation.md has no history row for {phase}")
    else:
        ver = next((ln for ln in hist.splitlines()
                    if ln.startswith("**Version:**")), "")
        if phase not in ver:
            fails.append("A7 implementation.md version header does not name "
                         f"phase {phase}: {ver[:80]!r}")
    return fails


ASSERTION_IDS = ("A1", "A2", "A3", "A4", "A5", "A6", "A7")


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: closeout_check.py <repo> <phase>", file=sys.stderr)
        return 2
    fails = check(pathlib.Path(sys.argv[1]), sys.argv[2])
    for f in fails:
        print(f)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
