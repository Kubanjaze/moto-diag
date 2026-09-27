#!/usr/bin/env python3
"""Closeout's artefact assertions. ONE implementation, two callers.

`tests/test_phase255D_closeout_contract.py` calls this, and so does
`_pre_push_guard.py`. They share the function deliberately: a guard that
reimplemented the checks could pass while the test failed, and the push
would sail through the thing meant to stop it.

**What this asserts, and what it refuses to assert.** It checks the
ARTEFACTS a close-out is defined to produce — eight file facts, each one
something a skipped close-out leaves undone. It does NOT assert "closeout
ran", because that is unfalsifiable from inside a repository, and a check
that cannot fail is the defect this phase exists to stop shipping.

Each assertion has a stable id (A1..A8) so a failure names itself and the
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


_ROW_DATE = re.compile(r"\*\*(\d{4}-\d{2}-\d{2})\*\*")


def row_committed_at(hist: pathlib.Path, phase: str) -> float:
    """Epoch of the first commit that added this phase's history row.

    Searched on the row's `| **phase** |` prefix, not the whole line, so an
    edit to the notes later does not move it. A row no commit holds yet is
    later than any committed one, as `recorded_at` treats a heading.
    """
    root = _git_root(hist.parent)
    if root is not None:
        rel = hist.resolve().relative_to(root.resolve())
        r = subprocess.run(
            ["git", "-C", str(root), "log", "--reverse", "--format=%at",
             "-S", f"| **{phase}** |", "--", str(rel)],
            capture_output=True, text=True)
        first = r.stdout.split()[:1]
        if first:
            return float(first[0])
    return float("inf")


def newest_phase(hist: pathlib.Path, rows: list[str]) -> str:
    """The phase whose history row carries the latest Date.

    NOT the first row: the table is not in date order, and taking `rows[0]`
    made the version-header half of A7 fire only for 244M, its first bold
    row (F148). Same-day rows (257 and 257B both closed 2026-09-24) are
    ordered by when each row was committed, then by table position.
    """
    dated = []
    for ln in rows:
        cells = ln.split("|")
        m = _ROW_DATE.search(cells[3]) if len(cells) > 3 else None
        if m:
            dated.append((m.group(1), cells[1].strip().strip("*")))
    if not dated:
        return ""
    latest = max(d for d, _ in dated)
    tied = [(i, p) for i, (d, p) in enumerate(dated) if d == latest]
    return max(tied, key=lambda ip: (row_committed_at(hist, ip[1]), ip[0]))[1]


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

    # A5 — the regression line parses to count + hash + command (K6, Phase
    # 358); the ten phases closed before that carry the older, looser line.
    if phase in A5_COMMAND_EXEMPT:
        if not legacy_regression_line(log_txt):
            fails.append("A5 no regression line carrying both a commit hash and a "
                         "passed-test count")
    elif not regression_line(log_txt):
        fails.append("A5 no regression line that parses as regression.sh prints it: "
                     "'Regression of record: N passed … at `HASH` (…, `… pytest …`, …)'")

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
        newest = newest_phase(repo / "implementation.md", rows)
        if phase == newest:
            ver = next((ln for ln in hist.splitlines()
                        if ln.startswith("**Version:**")), "")
            if phase not in ver:
                fails.append("A7 implementation.md version header does not "
                             f"name the newest phase {phase}: {ver[:80]!r}")

    # A8 — a log that mentions refute carries the checklist, or says in one
    # line that no refute pass ran (K7, Phase 358)
    if phase not in A8_REFUTE_EXEMPT:
        fails += [f"A8 {f}" for f in refute_record(log_txt, phase)]
    return fails


#: K6. `regression.sh` prints: "Regression of record: 9507 passed, 0 failed,
#: 0 skipped, 0 errors at `5750985` (11 min 15 s wall, `python -m pytest -n
#: auto --dist load`, exit 0)". A5 requires that shape: the count, the hash
#: in backticks, and a backticked command that runs pytest.
_REGRESSION = re.compile(r"Regression of record:\s*(\d[\d,]*) passed\b.*?\bat `([0-9a-f]{7,40})`"
                         r".*?`([^`]*\bpytest\b[^`]*)`")

#: The phases whose close-out passed the old A5 (a hash and a count on a line
#: saying "regression") with no command on it, measured 2026-09-27 over all
#: 312 completed logs. Pinned; `test_phase358_closeout_k6_k7.py` recomputes
#: the set and requires equality, so it can neither grow nor quietly shrink.
A5_COMMAND_EXEMPT = frozenset({"255B", "255C", "255D", "257B", "257", "258", "259", "260",
                               "353", "354"})

#: K7. The closed logs that mention refute and carry neither the checklist nor
#: a one-line "no refute pass ran", measured 2026-09-27 over all 312. Pinned,
#: with the same equality control.
A8_REFUTE_EXEMPT = frozenset({
    "212", "213", "214", "215", "216", "217", "225B", "225", "226", "227", "228", "229",
    "230", "231", "232", "233", "234", "235", "236", "237", "238", "239", "242", "243",
    "244G", "244M", "244", "245", "246", "247", "248", "249", "254", "255B", "255D",
    "255", "256", "257B", "258", "259"})

_MENTION = re.compile(r"refut", re.I)
_NO_REFUTE = re.compile(r"^\s*(?:[-*]\s+)?\**no refute pass ran\b", re.I | re.M)


def regression_line(log_txt: str) -> tuple[str, str, str] | None:
    """(count, hash, command) from the log's regression line, or None."""
    m = _REGRESSION.search(log_txt)
    return m.groups() if m else None


def legacy_regression_line(log_txt: str) -> bool:
    """The pre-358 A5: a line saying "regression" with a hash and a count."""
    return any(_HASH.search(ln) and _COUNT.search(ln) for ln in log_txt.splitlines()
               if re.search(r"regression", ln, re.I))


def refute_record(log_txt: str, phase: str | None = None) -> list[str]:
    """Why a log that mentions refute does not record it; [] when it does.

    The operator's words, applied literally: "a log mentioning refute
    without a refute checklist fails." The one way out is a line saying no
    refute pass ran, so the honest sentence naming what is absent passes.
    A checklist must pass refute_check, including the round column (K9)
    unless the phase is one of refute_check.OLD_FORMAT.
    """
    if not _MENTION.search(log_txt):
        return []
    if "## Refuter pass" in log_txt:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "refute"))
        import refute_check
        rounds = phase not in refute_check.OLD_FORMAT
        return [f"refuter checklist: {f}"
                for f in refute_check.check(log_txt, require_rounds=rounds)]
    if _NO_REFUTE.search(log_txt):
        return []
    return ["the log mentions refute but has no '## Refuter pass' checklist, and no "
            "line saying 'No refute pass ran'"]


ASSERTION_IDS = ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8")


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
