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

import datetime as dt
import pathlib
import re
import subprocess
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


def _git_root(path: pathlib.Path) -> pathlib.Path | None:
    r = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True)
    return pathlib.Path(r.stdout.strip()) if r.returncode == 0 else None


#: How far a heading may run ahead of the commit that recorded it. Headings
#: are written to the minute and committed a moment later; anything beyond
#: this is a time the entry could not have been written at.
TIME_TOLERANCE = dt.timedelta(minutes=5)
_HEAD_TIME = re.compile(r"^#{1,3}\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\b")


def recorded_at(log: pathlib.Path, heading: str) -> dt.datetime | None:
    """Author time of the first commit that wrote this exact heading line.

    None when no commit holds it yet — an uncommitted entry, whose recording
    time is "now". Searched in both `completed/` and `in_progress/`, because
    a phase log is written in one and moved to the other.
    """
    root = _git_root(log.parent)
    if root is None:
        return None
    rel = log.resolve().relative_to(root.resolve())
    paths = {str(rel), str(rel).replace("/completed/", "/in_progress/")}
    r = subprocess.run(
        ["git", "-C", str(root), "log", "--reverse", "--format=%ad",
         "--date=format:%Y-%m-%d %H:%M", "-S", heading, "--", *sorted(paths)],
        capture_output=True, text=True)
    first = r.stdout.splitlines()[:1]
    return dt.datetime.strptime(first[0], "%Y-%m-%d %H:%M") if first else None


def dated_after_recording(log: pathlib.Path, heading: str,
                          now: dt.datetime | None = None) -> str | None:
    """A heading dated later than the commit that wrote it cannot be true.

    The rule is deliberately NOT "heading matches the fix commit". Measured
    over 255C and 255D, a heading records when the ENTRY was written — often
    in a close-out batch an hour after the fix — so that rule failed 11 of
    13 honest entries. What no honest entry does is carry a time later than
    the commit that recorded it: 255C #7 (18:05, written at 16:25), 255D #5
    and #6 (21:40/21:55, written at 20:17/20:18), and the invented 22:40 and
    22:55 of fixes #7/#8 (written at 20:39). This rule catches exactly those.
    """
    m = _HEAD_TIME.match(heading)
    if not m:
        return None
    stated = dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M")
    at = recorded_at(log, heading) or (now or dt.datetime.now())
    if stated > at + TIME_TOLERANCE:
        return f"heading {m.group(1)} is after it was recorded ({at:%Y-%m-%d %H:%M})"
    return None


def unresolved_commits(repo: pathlib.Path, line: str) -> list[str] | None:
    """The hashes on a `**Commit.**` line that do not name a real commit.

    Returns None when the line names no hash at all — `This one.`, `See the
    close-out commit` — which is a non-answer, not a citation. A trailing
    `(name)` after a hash means the commit is in the sibling repository
    `name` beside this one (`e536740` (workspace-docs)); a sibling that is
    not checked out cannot be resolved, and that is reported, not skipped.

    Resolution is `git cat-file -e <hash>^{commit}` — the only test of
    "names its commit" that a fabricated hash cannot pass.
    """
    hashes = list(re.finditer(r"`([0-9a-f]{7,40})`(?:\s*\(([\w.-]+)\))?", line))
    if not hashes:
        return None
    root = _git_root(repo)
    bad = []
    for m in hashes:
        h, sibling = m.group(1), m.group(2)
        where = (root.parent / sibling) if (root and sibling) else root
        ok = where is not None and where.is_dir() and subprocess.run(
            ["git", "-C", str(where), "cat-file", "-e", f"{h}^{{commit}}"],
            capture_output=True).returncode == 0
        if not ok:
            bad.append(f"{h}" + (f" ({sibling})" if sibling else ""))
    return bad


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
        entries.append((m.group(1), "\n".join(lines[i + 1:end]), lines[i]))
    if entries:
        nums = [int(n) for n, _, _ in entries]
        expected = list(range(1, max(nums) + 1))
        if sorted(nums) != expected:
            fails.append(f"A4 bug-fix numbering is not contiguous from #1: "
                         f"found {sorted(nums)}, expected {expected}")
        # A Commit line must NAME a commit, and the commit must exist. The
        # first cut only looked for the words `**Commit.**`, so `This one.`
        # and `See the close-out commit for this fix.` both passed — 255C #7
        # and 255D #5/#6 shipped that way. A check that passes on a
        # non-answer is the defect this folder exists to stop shipping.
        no_commit, non_answer, unresolved = [], [], []
        late = []
        for n, body, head in entries:
            why = dated_after_recording(log, head)
            if why:
                late.append(f"#{n} {why}")
            m = re.search(r"^\*\*Commit\.?\*\*(.*)$", body, re.I | re.M)
            if not m:
                no_commit.append(int(n))
                continue
            bad = unresolved_commits(repo, m.group(1))
            if bad is None:
                non_answer.append(f"#{n} {m.group(1).strip()!r}")
            elif bad:
                unresolved.append(f"#{n} {', '.join(bad)}")
        if no_commit:
            fails.append(f"A4 bug-fix entries with no Commit line: "
                         f"{sorted(no_commit)}")
        if non_answer:
            fails.append("A4 bug-fix Commit lines that name no `backticked` commit hash: "
                         + "; ".join(non_answer))
        if unresolved:
            fails.append("A4 bug-fix commits that do not resolve "
                         "(git cat-file -e): " + "; ".join(unresolved))
        if late:
            fails.append("A4 bug-fix headings dated after the commit that "
                         "recorded them: " + "; ".join(late))
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
    rows = [ln for ln in hist.splitlines() if ln.startswith("| **")]
    if not any(ln.startswith(f"| **{phase}** |") for ln in rows):
        fails.append(f"A7 implementation.md has no history row for {phase}")
    else:
        # The version header names the phase that closed MOST RECENTLY, so
        # it can only ever name one. Asserting it for every phase made A7
        # unpassable for all but the newest — it broke the moment the next
        # phase landed, which is how this was found: the test pinned 255C,
        # 255D closed, and 255C's A7 started failing on a document that was
        # correct. **An assertion that only the newest artefact can satisfy
        # is not a property of a closed phase.**
        newest = rows[0].split("|")[1].strip().strip("*")
        if phase == newest:
            ver = next((ln for ln in hist.splitlines()
                        if ln.startswith("**Version:**")), "")
            if phase not in ver:
                fails.append("A7 implementation.md version header does not "
                             f"name the newest phase {phase}: {ver[:80]!r}")
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
