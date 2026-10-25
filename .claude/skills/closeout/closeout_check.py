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
                         "passed-test count, and no failure")
    else:
        _, problem = regression_record(log_txt, phase)
        if problem:
            fails.append(f"A5 {problem}")

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
#: in backticks, and a backticked command that runs pytest. F206 (Phase 383):
#: the whole shape, so the failures, errors and exit code are read too.
PREFIX = "Regression of record:"
FAILED_PREFIX = "Regression run FAILED (not of record):"
SKIP_PREFIX = "Skipped in the regression of record:"
_REGRESSION = re.compile(r"Regression of record:\s*(\d[\d,]*) passed, (\d+) failed, (\d+) skipped, "
                         r"(\d+) errors? at `([0-9a-f]{7,40})` \(.*?`([^`]*\bpytest\b[^`]*)`, "
                         r"exit (\d+)\)")
_SKIP = re.compile(r"Skipped in the regression of record: \[(\d+)\] ([^\s:]+):\d+: (.+?)\s*$")
#: pytest's -rA summary line for a skip, grouped: "SKIPPED [1] tests/x.py:79: reason".
_PYTEST_SKIP = re.compile(r"^SKIPPED \[(\d+)\] ([^\s:]+:\d+): (.*)$", re.M)
_SUMMARY = re.compile(r"^=+ .*(passed|failed|error|no tests ran).* =+$", re.M)

#: F206, the operator's 1C: a skip in the regression of record is allowed only
#: when its test file and its reason are pinned here. Adding to it is the
#: operator's call; `test_phase383_regression_outcome.py` holds it to equality.
EXPECTED_SKIPS = frozenset({
    ("tests/test_phase244H_test_db_isolation.py", "no production database on this machine"),
    # Phase 388, the operator: "Mac runs it (Recommended)". The Linux fence's
    # boundary test, on the Mac, where 257's sandbox test is its twin.
    ("tests/test_phase388_fence_boundary.py",
     "macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py"),
})

#: Phase 389, the operator, 2026-10-25: "Sandbox counts (Recommended)" — the
#: tests that cannot run inside the fleet's fence skip there with a reason
#: naming it, "and the machine-shaped skips are accepted only for runs made
#: in the sandbox". So these count only on a line `regression.sh` printed
#: inside the fence, which carries FENCE_MARK; the Mac keeps EXPECTED_SKIPS
#: alone. Measured in the fence at `c7f61bc` (389_step0.md, S0-5) and
#: re-measured after the skips above were given their reasons.
#: `test_phase389_fence_regression.py` holds it to equality.
FENCE_MARK = "(run inside the fleet's fence)"
FENCE_ROOT = pathlib.Path("/fleet/moto-diag")
FENCE_EXPECTED_SKIPS = frozenset({
    ("tests/test_phase191b_ffmpeg.py", "real ffmpeg binary or fixture mp4 not available"),
    ("tests/test_phase204_gate10.py", "inside the fleet's fence: no ffmpeg on the home desktop"),
    ("tests/test_phase209_packaging.py", "inside the fleet's fence: no network to build a wheel"),
    ("tests/test_phase257_orchestrator_guards.py",
     "inside the fleet's fence: no Subconscious login there (K42)"),
    ("tests/test_phase257_orchestrator_guards.py", "inside the fleet's fence: osacompile is macOS-only"),
    ("tests/test_phase257_sandbox_boundary.py", "sandbox-exec is macOS-only; the orchestrator runs only there"),
    ("tests/test_phase257_source_checks.py", "needs the on-disk library"),
    ("tests/test_phase257_source_checks.py",
     "acquired/Yamaha/library_om_contents_pdf_10_5YR-F8199-15_02.pdf is not in this machine's library"),
    ("tests/test_phase257_source_checks.py",
     "acquired/KTM/24_3214961_en_OM.pdf is not in this machine's library"),
    ("tests/test_phase257_source_checks.py", "the KTM manual is not in this machine's library"),
    ("tests/test_phase257_manual_route_excerpts.py", "needs the on-disk library"),
    ("tests/test_phase388_fence_boundary.py",
     "inside the fleet's fence: its boundary is proven from the host, not from inside"),
})


def in_fleet_fence(root: pathlib.Path | None = None) -> bool:
    """A run inside the fleet's fence: the clone is at /fleet/moto-diag and the
    run directory /fleet/run exists (`fence.sh`); no machine of the
    operator's has either."""
    root = root or pathlib.Path(__file__).resolve().parents[3]
    return root.resolve() == FENCE_ROOT and pathlib.Path("/fleet/run").is_dir()


#: The closed logs whose regression line records a skip with no line naming
#: it, measured 2026-10-19 over every completed log: 382, before 1C. Pinned,
#: with the same equality control as A5_COMMAND_EXEMPT.
A5_UNNAMED_SKIP_EXEMPT = frozenset({"382"})

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


def regression_record(log_txt: str, phase: str | None = None
                      ) -> tuple[tuple[str, str, str] | None, str | None]:
    """((count, hash, command), None) for a passing regression of record, or
    (None, why not).

    The regression line is the LAST line carrying "Regression of record:".
    A re-run supersedes the run before it (358 recorded two), so the first
    line is the one run the close-out no longer rests on (Phase 359, bug
    fix #1). F206 (Phase 383, the operator's 1C): it must record 0 failed,
    0 errors and exit 0, and the lines right below it must name every skip
    by its file and reason, each one in EXPECTED_SKIPS.
    """
    lines = log_txt.splitlines()
    at = [i for i, ln in enumerate(lines) if PREFIX in ln]
    m = _REGRESSION.search(lines[at[-1]]) if at else None
    if m is None:
        return None, ("no regression line that parses as regression.sh prints it: "
                      "'Regression of record: N passed, F failed, S skipped, E errors at "
                      "`HASH` (…, `… pytest …`, exit RC)'")
    count, failed, skipped, errors, commit, command, rc = m.groups()
    allowed = EXPECTED_SKIPS | (FENCE_EXPECTED_SKIPS if FENCE_MARK in lines[at[-1]] else frozenset())
    if (failed, errors, rc) != ("0", "0", "0"):
        return None, (f"the regression of record did not pass: {failed} failed, "
                      f"{errors} errors, exit {rc}")
    named, problems = 0, []
    for ln in lines[at[-1] + 1:]:
        if SKIP_PREFIX not in ln:
            break
        s = _SKIP.search(ln)
        if s is None:
            problems.append(f"a skip line that does not parse: {ln.strip()[:120]!r}")
            continue
        named += int(s.group(1))
        if (s.group(2), s.group(3)) not in allowed:
            problems.append(f"an unexpected skip: {s.group(2)}: {s.group(3)!r}")
    unnamed_ok = named == 0 and phase in A5_UNNAMED_SKIP_EXEMPT
    if named != int(skipped) and not unnamed_ok:
        problems.append(f"the line records {skipped} skipped and the lines below it name "
                        f"{named}")
    if problems:
        return None, "; ".join(problems)
    return (count, commit, command), None


def regression_line(log_txt: str, phase: str | None = None) -> tuple[str, str, str] | None:
    """(count, hash, command) from a passing regression of record, or None."""
    return regression_record(log_txt, phase)[0]


def format_regression(log_text: str, commit: str, wall_s: int, command: str, rc: int,
                      fence: bool = False) -> str:
    """The lines `regression.sh` prints, from the pytest log of its run.

    One writer beside its reader, so the two cannot drift (F206, Phase 383).
    The prefix "Regression of record:" is printed only for a run that exits
    0 with 0 failed and 0 errors. Each skip in pytest's -rA summary follows
    on its own line, with its count, file and reason. A run inside the
    fleet's fence ends its line with FENCE_MARK (Phase 389).
    """
    summaries = [m.group(0) for m in _SUMMARY.finditer(log_text)]
    summary = summaries[-1] if summaries else ""

    def n(word: str) -> int:
        hit = re.search(rf"(\d+) {word}\b", summary)
        return int(hit.group(1)) if hit else 0

    p, f, s, e = n("passed"), n("failed"), n("skipped"), n("errors?")
    prefix = PREFIX if (rc, f, e) == (0, 0, 0) else FAILED_PREFIX
    out = [f"{prefix} {p} passed, {f} failed, {s} skipped, {e} errors at `{commit}` "
           f"({wall_s // 60} min {wall_s % 60} s wall, `{command}`, exit {rc})"
           + (f" {FENCE_MARK}" if fence else "")]
    out += [f"{SKIP_PREFIX} [{k}] {where}: {why}"
            for k, where, why in _PYTEST_SKIP.findall(log_text)]
    return "\n".join(out)


def legacy_regression_line(log_txt: str) -> bool:
    """The pre-358 A5: a line saying "regression" with a hash and a count,
    and (F206) recording no failure or error."""
    return any(_HASH.search(ln) and _COUNT.search(ln)
               and not re.search(r"\b[1-9][\d,]* (?:failed|errors?)\b", ln)
               for ln in log_txt.splitlines() if re.search(r"regression", ln, re.I))


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
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "refute"))
    import refute_check
    if refute_check.find_block(log_txt):
        rounds = phase not in refute_check.OLD_FORMAT
        return [f"refuter checklist: {f}"
                for f in refute_check.check(log_txt, require_rounds=rounds)]
    if _NO_REFUTE.search(log_txt):
        return []
    return ["the log mentions refute but has no '## Refuter pass' checklist, and no "
            "line saying 'No refute pass ran'"]


ASSERTION_IDS = ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8")


def main() -> int:
    if len(sys.argv) == 7 and sys.argv[1] == "--format-regression":
        _, _, log, commit, wall, command, rc = sys.argv
        print(format_regression(_read(pathlib.Path(log)), commit, int(wall), command, int(rc),
                                fence=in_fleet_fence()))
        return 0
    if len(sys.argv) < 3:
        print("usage: closeout_check.py <repo> <phase>\n"
              "       closeout_check.py --format-regression <pytest log> <commit> "
              "<wall s> <command> <rc>", file=sys.stderr)
        return 2
    fails = check(pathlib.Path(sys.argv[1]), sys.argv[2])
    for f in fails:
        print(f)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
