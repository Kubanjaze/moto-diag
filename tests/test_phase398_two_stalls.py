"""Phase 398 — the two stalls at the Red Team's clear (F251, F252).

(a) F251: A5 reads the regression of record only from a line that begins
with "Regression of record:". Replayed on the two refused logs, kept byte
for byte as fixtures (`git show 9555925:…345_phase_log.md`,
`git show 41370d2:…343_phase_log.md`).

(b) F252: a refused record push holds the cleared table with
`needs-hands`; taking `needs-hands` off pushes the same table on the branch
as it then stands and sets `review:clear`, with no new round; a second
refusal holds again; the hold outlives a restart and `prune_runs`.
Replayed with the real stop text of issues #45 and #50 planted as the
gate's G6 on the record push, through 390's world (real git, stand-in gh,
fence and model-free runs).
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLOSEOUT = ROOT / ".claude" / "skills" / "closeout"
FLEET = ROOT / ".claude" / "skills" / "fleet"
sys.path.insert(0, str(CLOSEOUT))
sys.path.insert(0, str(FLEET))
sys.path.insert(0, str(ROOT / "tests"))

import closeout_check as C  # noqa: E402
import dispatcher as D  # noqa: E402
import journal as J  # noqa: E402
from test_phase389_dispatcher import BRANCH, PHASE  # noqa: E402
from test_phase389_fleet_git import git  # noqa: E402
from test_phase390_resume import (  # noqa: E402
    CLEAR,
    N,
    advance,
    calls,
    commits,
    killed,
    labels,
    ledger,
    push,
    restart,
    said,
    to_pr,
    w,
)

assert w and ledger  # the fixtures, imported for their names

F251 = CLOSEOUT / "fixtures" / "f251"
STOPS = json.loads((FLEET / "fixtures" / "f252" / "stops.json").read_text(encoding="utf-8"))
COMMAND = "python -m pytest -n auto --dist load --cov=motodiag"
RECORD = f"Phase {PHASE}: the Red Team's refuter pass, round 1"
HOLD = f"{D.MARKER} needs-hands rank=red-team"
LOG = f"docs/phases/in_progress/{PHASE}_phase_log.md"


# ----------------------------------------------------------------- (a) F251
def _refused(phase: str, commit: str) -> str:
    return (F251 / f"{phase}_phase_log_at_{commit}.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("phase, commit, count, at", [
    ("345", "9555925", "12186", "c2b0767"),
    ("343", "41370d2", "12292", "ca580f6")])
def test_a5_reads_the_record_in_the_refused_log(phase, commit, count, at):
    """Red on the old A5: the table row's quote was read, and did not parse."""
    text = _refused(phase, commit)
    quotes = [ln for ln in text.splitlines() if C.PREFIX in ln and not ln.startswith(C.PREFIX)]
    assert quotes and all(q.startswith("|") for q in quotes), "the fixture lost its table row"
    assert C.regression_record(text, phase) == ((count, at, COMMAND), None)


@pytest.mark.parametrize("phase, commit", [("345", "9555925"), ("343", "41370d2")])
def test_a_refused_log_without_its_record_still_fails(phase, commit):
    """Known-bad: the real lines removed, the quote left. A5 must not take it."""
    lines = [ln for ln in _refused(phase, commit).splitlines()
             if not ln.startswith((C.PREFIX, C.SKIP_PREFIX))]
    record, why = C.regression_record("\n".join(lines), phase)
    assert record is None and "no regression line that parses" in why


def test_a_table_row_alone_is_not_a_record():
    """Known-bad: a row quoting a whole line, which the old A5 passed."""
    text = (F251 / "a5_bad_table_row_only.md").read_text(encoding="utf-8")
    assert [ln for ln in text.splitlines() if C.PREFIX in ln][0].startswith("| ")
    record, why = C.regression_record(text, "ZZZ")
    assert record is None and "no regression line that parses" in why


def test_a5_still_reads_every_part_of_the_line_it_takes():
    """The line A5 now takes is held to the same shape and outcome."""
    good = ("Regression of record: 10 passed, 0 failed, 0 skipped, 0 errors at `abcdef1` "
            "(1 min 0 s wall, `python -m pytest -n auto --dist load`, exit 0)")
    assert C.regression_record(good)[0] == ("10", "abcdef1", "python -m pytest -n auto --dist load")
    for bad in (good.replace("0 failed", "1 failed"), good.replace("exit 0", "exit 1"),
                good.replace("0 skipped", "1 skipped"), good.replace("`python -m pytest", "`make"),
                "  " + good, "> " + good):
        assert C.regression_record(bad)[0] is None, bad


def test_the_pinned_exemptions_still_hold_by_equality():
    """358's and 383's controls, recomputed with the new A5."""
    done = ROOT / "docs" / "phases" / "completed"
    logs = {p.name.split("_")[0]: p.read_text(encoding="utf-8")
            for p in done.glob("*_phase_log.md")}
    old_rule = {p for p, t in logs.items()
                if C.legacy_regression_line(t) and not C.regression_line(t, p)}
    assert old_rule == C.A5_COMMAND_EXEMPT and len(C.A5_COMMAND_EXEMPT) == 10
    unnamed = {p for p, t in logs.items() if p not in C.A5_COMMAND_EXEMPT
               and C.PREFIX in t and C.regression_line(t) is None}
    assert unnamed == C.A5_UNNAMED_SKIP_EXEMPT == {"382"}
    assert [p for p, t in logs.items() if p not in C.A5_COMMAND_EXEMPT and C.PREFIX in t
            and C.regression_line(t, p) is None] == []


# ----------------------------------------------------------------- (b) F252
def _reason(issue: int) -> str:
    """The gate's words in the real stop: "G6 … did not pass a model-free run: …"."""
    return STOPS[str(issue)]["body"].split("the push gate refused: ", 1)[1]


def refuse(w, issue: int, times: int = 1) -> None:
    """The record push's fast run fails as #`issue`'s did, so the real gate
    refuses it with G6, `times` times; every other run as before."""
    left, base = [times], w.fleet.check
    why = _reason(issue).split("did not pass a model-free run: ", 1)[1]

    def check(clone, commit, *, full, command=None):
        subject = subprocess.run(["git", "-C", str(clone), "log", "-1", "--format=%s", commit],
                                 capture_output=True, text=True).stdout.strip()
        if not full and command is None and subject == RECORD and left[0] > 0:
            left[0] -= 1
            w.checks.append((commit, full, command))
            return D.Check(False, commit, None, why)
        return base(clone, commit, full=full, command=command)
    w.fleet.check = check


def by_hand(w, change) -> str:
    """The operator's commit on the branch, pushed to origin: `change(clone)`."""
    work = w.tmp / "hand"
    git("clone", "-q", "--branch", BRANCH, str(w.origin), str(work), cwd=w.tmp)
    change(work)
    git("add", "-A", cwd=work)
    git("-c", "user.name=op", "-c", "user.email=op@l", "commit", "-qm", "by hand", cwd=work)
    git("push", "-q", "origin", BRANCH, cwd=work)
    return git("rev-parse", "HEAD", cwd=work).stdout.strip()


def fix_branch(w) -> str:
    """The operator's fix: any commit on the branch."""
    return by_hand(w, lambda c: (c / "docs" / "hand_fix.md").write_text("The operator's fix.\n"))


def plant(w, body: str) -> None:
    """A comment on the issue, as `gh issue comment` makes one."""
    w.host.gh(["gh", "issue", "comment", str(N), "--body", body])


def on_branch(w, rel: str) -> str:
    return git("show", f"{BRANCH}:{rel}", cwd=w.origin).stdout


def held(w) -> pathlib.Path:
    (run,) = J.held_runs(w.fleet.runs, N)
    return run


def hands_off(w) -> None:
    w.host.issues[N]["labels"].remove("needs-hands")


@pytest.mark.parametrize("issue", [45, 50])
def test_a_refused_record_push_holds_the_table_with_needs_hands(w, issue):
    """Red on the old code: it said "could not finish, label unchanged" and
    nothing was held or due."""
    to_pr(w)
    refuse(w, issue)
    advance(w, CLEAR)
    assert labels(w) == ["mission", "needs-hands", "review:open"]
    stop = w.host.comments(N)[-1]
    assert stop.startswith(HOLD) and "the push gate refused: G6 " in stop
    assert _reason(issue).split("did not pass a model-free run: ", 1)[1] in stop
    assert "take `needs-hands` off" in stop and "no new Red Team round" in stop
    info = J.held(held(w))
    assert info["why"] == "record" and info["rnd"] == 1 and info["branch"] == BRANCH
    assert "## Refuter pass" in info["table"]
    assert commits(w, RECORD) == 0, "the refused commit reached the branch"
    n = len(w.host.comments(N))
    advance(w)                                    # left alone while needs-hands is on
    assert len(w.host.comments(N)) == n and labels(w) == ["mission", "needs-hands", "review:open"]


def test_needs_hands_off_after_a_fix_pushes_the_same_table_with_no_new_round(w):
    to_pr(w)
    refuse(w, 50)
    advance(w, CLEAR)
    run = held(w)
    table = J.held(run)["table"]
    fixed = fix_branch(w)
    models, verdicts = len(calls(w)), said(w, D.RED_M)
    hands_off(w)
    advance(w)                                    # no replies: no model is called
    assert labels(w) == ["mission", "review:clear"]
    assert len(calls(w)) == models and said(w, D.RED_M) == verdicts == 1
    assert commits(w, RECORD) == 1
    assert table.strip() in on_branch(w, LOG)
    assert git("merge-base", "--is-ancestor", fixed, BRANCH, cwd=w.origin).returncode == 0
    assert J.held(run) is None and J.held_runs(w.fleet.runs, N) == []


def test_a_second_refusal_holds_again(w):
    to_pr(w)
    refuse(w, 45, times=2)
    advance(w, CLEAR)
    run = held(w)
    hands_off(w)
    advance(w)
    assert labels(w) == ["mission", "needs-hands", "review:open"]
    assert said(w, HOLD) == 2 and held(w) == run
    assert commits(w, RECORD) == 0 and said(w, D.RED_M) == 1
    hands_off(w)
    advance(w)                                    # the gate passes now
    assert labels(w) == ["mission", "review:clear"] and commits(w, RECORD) == 1
    assert said(w, D.RED_M) == 1


def test_a_held_table_outlives_a_restart_and_is_never_pruned(w):
    to_pr(w)
    refuse(w, 45)
    advance(w, CLEAR)
    run = held(w)
    restart(w)
    for k in range(D.KEEP_RUNS + 3):
        w.clock.t += D.dt.timedelta(minutes=1)
        w.fleet.new_run(f"filler{k}")
    w.fleet.prune_runs(set())
    assert run.is_dir() and J.held(run)["why"] == "record"
    assert len(list(w.fleet.runs.iterdir())) == D.KEEP_RUNS + 1
    hands_off(w)
    advance(w)
    assert labels(w) == ["mission", "review:clear"] and commits(w, RECORD) == 1


def test_the_kept_table_already_on_the_branch_is_not_pushed_again(w):
    """The operator pushed the table by hand, as on #45 and #50: nothing to
    commit, and `review:clear` is set."""
    to_pr(w)
    refuse(w, 45)
    advance(w, CLEAR)
    table = J.held(held(w))["table"]
    by_hand(w, lambda c: D.red_team.record_in_log(c, PHASE, table))
    hands_off(w)
    advance(w)
    assert labels(w) == ["mission", "review:clear"] and commits(w, RECORD) == 0


def test_a_record_hold_is_not_the_engineers(w):
    """The Engineer's `held_for` reads only its own holds."""
    to_pr(w)
    refuse(w, 45)
    advance(w, CLEAR)
    assert J.held(held(w))["why"] == "record"
    plant(w, f"{D.MARKER} needs-admiral rank=engineer -->\n**planted**")
    assert w.fleet.held_for(N) is None


def test_a_later_verdict_or_stop_ends_the_holds_due(w):
    """A fresh round's verdict, or a stop after the hold, is newer than the
    hold: the kept table is not pushed every cycle after it."""
    to_pr(w)
    refuse(w, 45)
    advance(w, CLEAR)
    hands_off(w)
    assert w.fleet.held_record(N) == held(w)
    plant(w, f"{D.MARKER} stopped rank=red-team -->\nplanted: a stop after the hold")
    assert w.fleet.held_record(N) is None
    plant(w, f"{HOLD} -->\nplanted: held again")
    assert w.fleet.held_record(N) == held(w)
    plant(w, f"{D.RED_M} verdict=back round=2 -->\nplanted: a later verdict")
    assert w.fleet.held_record(N) is None


def test_a_later_clear_releases_an_older_kept_table(w):
    """The clear of a later round pushes its own table, and the kept one is
    released: it is never pushed over the newer one."""
    to_pr(w)
    refuse(w, 45)
    advance(w, CLEAR)
    run = held(w)
    hands_off(w)
    plant(w, f"{D.MARKER} stopped rank=red-team -->\nplanted: the re-push stopped")
    w.clock.t += D.dt.timedelta(minutes=1)
    w.host.issues[N]["labels"].remove("review:open")
    w.host.label(N, "review:open")                # the operator: a fresh round
    advance(w, CLEAR)
    assert labels(w) == ["mission", "review:clear"] and J.held(run) is None
    assert commits(w, f"Phase {PHASE}: the Red Team's refuter pass, round 2") == 1


def test_red_record_cut_after_its_push_before_review_clear(w):
    """The kill point (390's contract): cut after the kept table's push."""
    to_pr(w)
    refuse(w, 45)
    advance(w, CLEAR)
    hands_off(w)
    w.kill.at(push, after=True)
    killed(w)
    said_ = restart(w)
    assert said_[0].startswith("resume red_record")
    assert labels(w) == ["mission", "review:clear"] and commits(w, RECORD) == 1
