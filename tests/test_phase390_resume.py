"""Phase 390 — a stage killed at any point resumes on the next start (F219).

What must hold (the 390 prompt; v1.0 sections 2, 3 and 5): for every kill
point in `390_step0.md`'s tables, the stage, killed there, is resumed by a
new dispatcher's `recover()` before its first cycle, from its run directory
and journal: finished model calls are replayed and not made again, the cut
call goes on with `--resume` and the session its transcript names, a
model-free run is started again on the same commit, and each commit, push
and GitHub write is made exactly once. The issue reaches the stage's next
label with no hand on it.

The kill is a `BaseException` raised by a stand-in at the kill point: no
stage catches it, as nothing in the process runs when systemd kills it
(Step 0, S0-1). "After" kills let the call happen first: the write is on
GitHub and the journal does not know. git is real (389's origin); `gh`, the
fence, the Engineer's session and the model-free run are stand-ins.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "fleet"
sys.path.insert(0, str(SKILL))
sys.path.insert(0, str(ROOT / "tests"))

import dispatcher as D  # noqa: E402
import engineer as E  # noqa: E402
import journal as J  # noqa: E402
import rank_call  # noqa: E402
from test_phase388_dispatcher import LIMITED, USAGE_LIMITED, Clock, claude_json  # noqa: E402
from test_phase389_dispatcher import ASSESS, BRANCH, LINE, PHASE, PLAN, TERMS  # noqa: E402
from test_phase389_dispatcher import TITLE, TRIAL, FakeEngineer, GitHub  # noqa: E402
from test_phase389_fleet_git import git, make_origin  # noqa: E402
from test_phase389_red_team import FINDING, TABLE  # noqa: E402

N = 31
CUT = "sess-cut"
SCOUT = (claude_json(TERMS, model=rank_call.HAIKU), claude_json(ASSESS, model=rank_call.HAIKU))
V1 = claude_json({"implementation_md": PLAN})
APPROVE = claude_json({"verdict": "approve", "items": [], "reason": "ok"})
XO_BACK = claude_json({"verdict": "back-to-captain", "items": ["Name the file."],
                       "reason": "One defect."})
BACK = claude_json({"verdict": "back", "findings": [FINDING], "refuter_pass": TABLE},
                   model=rank_call.OPUS)
CLEAR = claude_json({"verdict": "clear", "findings": [], "refuter_pass": TABLE},
                    model=rank_call.OPUS)
MERGE = claude_json({"decision": "merge", "lines": ["It adds row 385.", "Green.", "Merge."]})
DIGEST = claude_json({"summary": "A quiet day."}, model=rank_call.HAIKU)


class Killed(BaseException):
    """systemd's kill: no `except` in a stage catches it."""


class Hub(GitHub):
    """389's stand-in, with a pull request's comments readable."""

    def gh(self, cmd):
        if cmd[1:3] == ["pr", "view"] and cmd[cmd.index("--json") + 1] == "comments":
            pr = next(p for p in self.prs.values() if p["number"] == int(cmd[3]))
            return subprocess.CompletedProcess(
                cmd, 0, json.dumps({"comments": [{"body": b} for b in pr["comments"]]}), "")
        return super().gh(cmd)


def transcript(cmd: list[str], session: str = CUT) -> None:
    """What a killed `claude` leaves: its transcript, named by its session."""
    run = pathlib.Path(cmd[cmd.index("--run") + 1])
    p = run / "claude" / "projects" / "-fleet-moto-diag" / f"{session}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('{"type":"user"}\n')


class Kill:
    """The host, with at most one kill point armed: the `nth` call `match`
    accepts dies before it runs, or once it has run (`after`)."""

    def __init__(self, host: Hub):
        self.host, self.point = host, None

    def at(self, match, *, after: bool = False, nth: int = 1, cut: bool = False) -> None:
        self.point = [match, after, nth, cut]

    def __call__(self, cmd, **kw):
        cmd = list(cmd)
        p = self.point
        if p and p[0](cmd):
            p[2] -= 1
            if p[2] == 0:
                self.point = None
                if p[3]:
                    transcript(cmd)
                if p[1]:
                    self.host(cmd, **kw)
                raise Killed(" ".join(cmd[:4]))
        return self.host(cmd, **kw)


def model(c):
    return c[0].endswith("fence.sh") and "claude" in c


def comment(prefix):
    return lambda c: c[:3] == ["gh", "issue", "comment"] and \
        c[c.index("--body") + 1].startswith(prefix)


def label(name):
    return lambda c: c[:3] == ["gh", "issue", "edit"] and "--add-label" in c and name in c


def pr_comment(c):
    return c[:3] == ["gh", "pr", "comment"]


def push(c):
    return c[0] == "git" and "push" in c


@dataclasses.dataclass
class World:
    tmp: pathlib.Path
    origin: pathlib.Path
    clock: Clock
    host: Hub
    kill: Kill
    engineer: FakeEngineer
    checks: list
    lines: list
    fleet: D.Fleet = None
    check_kill: object = None     # (full, after) for the next model-free run
    check_fail: bool = False      # the next full model-free run fails (F220: lost to load)
    session_kill: bool = False    # the next Engineer session dies, its transcript written

    def make(self) -> D.Fleet:
        def check(clone, commit, *, full, command=None):
            self.checks.append((commit, full, command))
            if self.check_kill is not None and self.check_kill == (full, command is not None):
                self.check_kill = None
                raise Killed("the model-free run")
            if full and self.check_fail:
                self.check_fail = False
                return D.Check(False, commit, None, "subprocess timed out after 60 seconds")
            return D.Check(True, commit, LINE if full else None,
                           "F9 lint: clean" if command else "")

        def popen(cmd, stdout, stderr, **kw):
            if self.session_kill:
                self.session_kill = False
                transcript(cmd)
                raise Killed("the Engineer's session")
            self.sessions.append(cmd[cmd.index("--") + 1:])
            return self.engineer(cmd, stdout, stderr, **kw)

        self.fleet = D.Fleet(
            state=self.tmp / "state", token="sk-ant-oat01-test-token", host=self.kill,
            fence=self.tmp / "fence.sh", workspace_docs=self.tmp / "wsd",
            repo_url=str(self.origin), now=self.clock, out=self.lines.append,
            identity_file=self.tmp / "no-identity.env", popen=popen, check=check,
            sleep=lambda s: None, venv=self.tmp / "no-venv", mobile=self.tmp / "no-mobile")
        return self.fleet

    sessions: list = dataclasses.field(default_factory=list)


@pytest.fixture(autouse=True)
def ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("FLEET_LEDGER", str(tmp_path / "calls.jsonl"))


@pytest.fixture
def w(tmp_path, monkeypatch) -> World:
    origin = make_origin(tmp_path)
    road = origin / "docs" / "ROADMAP.md"
    road.write_text(road.read_text().rstrip("\n") + f"\n| {PHASE} | The trial | 🚧 | x |\n")
    git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qam", "row 902", cwd=origin)
    clock = Clock()
    host = Hub(clock, tmp_path / "fence.sh")
    world = World(tmp_path, origin, clock, host, Kill(host), FakeEngineer(), [], [])
    world.make().save({"last_digest": "2026-10-21"})
    monkeypatch.setattr(D.engineer, "verify", lambda *a, **k: [])
    host.issue(N, TITLE, TRIAL, {"mission": clock.t})
    return world


# ------------------------------------------------------------------ driving
def advance(w: World, *replies: str) -> None:
    w.clock.t += dt.timedelta(minutes=5)
    w.host.replies = list(replies)
    w.fleet.cycle()
    assert w.host.replies == [], f"replies left unused: {len(w.host.replies)}"


def killed(w: World, *replies: str) -> None:
    w.clock.t += dt.timedelta(minutes=5)
    w.host.replies = list(replies)
    with pytest.raises(Killed):
        w.fleet.cycle()
    w.fleet.journal = None


def restart(w: World, *replies: str) -> list[str]:
    """A new process over the same state directory: `recover()` first."""
    w.clock.t += dt.timedelta(minutes=1)
    w.host.replies = list(replies)
    w.make()
    said = w.fleet.recover()
    assert w.host.replies == [], f"replies left unused: {len(w.host.replies)}"
    return said


def labels(w: World) -> list[str]:
    return sorted(w.host.issues[N]["labels"])


def said(w: World, prefix: str) -> int:
    return sum(b.lstrip().startswith(prefix) for b in w.host.comments(N))


def calls(w: World) -> list[list[str]]:
    return w.host.model_calls()


def commits(w: World, subject: str) -> int:
    log = subprocess.run(["git", "-C", str(w.origin), "log", "--format=%s", BRANCH],
                         capture_output=True, text=True).stdout.splitlines()
    return log.count(subject)


def no_unfinished(w: World) -> None:
    assert J.unfinished(w.fleet.runs) == [], "a journal left open"


def to_step0(w):
    advance(w, *SCOUT)


def to_review(w):
    to_step0(w)
    advance(w, V1)


def to_approved(w):
    to_review(w)
    advance(w, APPROVE)


def to_pr(w):
    to_approved(w)
    advance(w)


# ------------------------------------------------------- the Science Officer
STEP0 = f"Phase {PHASE} Step 0: the Science Officer's report"


def test_scout_cut_in_its_second_model_call(w):
    w.kill.at(model, nth=2, cut=True)
    killed(w, SCOUT[0])
    said_lines = restart(w, SCOUT[1])
    assert len(calls(w)) == 2, "the finished first call was made again"
    assert calls(w)[-1][:3] == ["claude", "--resume", CUT]
    assert labels(w) == ["mission", "step0:done"] and commits(w, STEP0) == 1
    assert said(w, D.SCOUT_M) == 1 and said(w, D.STARTED_M) == 1
    assert any(s.startswith("resume scout") for s in said_lines)
    no_unfinished(w)


def test_scout_cut_before_its_first_answer_runs_fresh_in_the_same_run(w):
    w.kill.at(model)
    killed(w)
    runs = sorted(p.name for p in w.fleet.runs.iterdir())
    restart(w, *SCOUT)
    assert calls(w)[0][:2] == ["claude", "-p"], "no transcript, yet --resume"
    assert sorted(p.name for p in w.fleet.runs.iterdir())[:len(runs)] == runs
    assert labels(w) == ["mission", "step0:done"] and commits(w, STEP0) == 1


def test_scout_cut_in_the_push_gates_model_free_run(w):
    w.check_kill = (False, False)
    killed(w, *SCOUT)
    restart(w)
    assert len(calls(w)) == 2 and labels(w) == ["mission", "step0:done"]
    assert commits(w, STEP0) == 1


def test_scout_cut_after_its_push(w):
    w.kill.at(push, after=True)
    killed(w, *SCOUT)
    restart(w)
    assert commits(w, STEP0) == 1, "a second Step 0 (Step 0, S0-2)"
    assert labels(w) == ["mission", "step0:done"] and said(w, D.SCOUT_M) == 1


def test_scout_cut_after_its_marker(w):
    w.kill.at(comment(D.SCOUT_M), after=True)
    killed(w, *SCOUT)
    restart(w)
    assert said(w, D.SCOUT_M) == 1 and labels(w) == ["mission", "step0:done"]
    no_unfinished(w)


# ------------------------------------------------------------- the Captain
V1_SUBJECT = f"Phase {PHASE} v1.0: the plan"


def test_captain_cut_in_its_model_call(w):
    to_step0(w)
    w.kill.at(model, cut=True)
    killed(w)
    restart(w, V1)
    assert calls(w)[-1][:3] == ["claude", "--resume", CUT]
    assert labels(w) == ["mission", "plan:needs-review"] and commits(w, V1_SUBJECT) == 1


def test_captain_cut_after_its_push(w):
    to_step0(w)
    w.kill.at(push, after=True)
    killed(w, V1)
    restart(w)
    assert commits(w, V1_SUBJECT) == 1 and said(w, D.CAPTAIN_M) == 1
    assert labels(w) == ["mission", "plan:needs-review"]


def test_captain_cut_after_its_marker_then_the_xo_is_due(w):
    to_step0(w)
    w.kill.at(comment(D.CAPTAIN_M), after=True)
    killed(w, V1)
    restart(w)
    assert labels(w) == ["mission", "plan:needs-review"] and said(w, D.CAPTAIN_M) == 1
    advance(w, APPROVE)
    assert labels(w) == ["mission", "plan:approved"]


def test_captains_revision_cut_between_taking_the_label_off_and_putting_it_back(w):
    to_review(w)
    advance(w, XO_BACK)
    remove = lambda c: c[:3] == ["gh", "issue", "edit"] and "--remove-label" in c \
        and D.REVIEW in c  # noqa: E731
    w.kill.at(remove, after=True)
    killed(w, claude_json({"implementation_md": PLAN + "\nRevised.\n"}))
    assert D.REVIEW not in labels(w)
    restart(w)
    assert D.REVIEW in labels(w) and said(w, f"{D.CAPTAIN_M} revision") == 1
    advance(w, APPROVE)
    assert labels(w) == ["mission", "plan:approved"]


# --------------------------------------------------- the Executive Officer
def test_xo_cut_in_its_model_call(w):
    to_review(w)
    w.kill.at(model, cut=True)
    killed(w)
    restart(w, APPROVE)
    assert calls(w)[-1][:3] == ["claude", "--resume", CUT]
    assert labels(w) == ["mission", "plan:approved"] and said(w, "<!-- xo-verdict:") == 1


def test_xo_cut_after_its_verdict_before_its_label(w):
    to_review(w)
    w.kill.at(comment("<!-- xo-verdict:"), after=True)
    killed(w, APPROVE)
    n = len(calls(w))
    restart(w)
    assert len(calls(w)) == n, "the XO reviewed again"
    assert labels(w) == ["mission", "plan:approved"] and said(w, "<!-- xo-verdict:") == 1


# ------------------------------------------------ the Chief Engineer (F219)
def test_engineer_cut_between_its_started_marker_and_build_open(w):
    to_approved(w)
    w.kill.at(comment(D.ENGINEER_M), after=True)
    killed(w)
    restart(w)
    assert labels(w) == ["mission", "review:open"] and said(w, f"{D.ENGINEER_M} started") == 1


def test_engineer_cut_in_its_session_goes_on_with_continue(w):
    to_approved(w)
    w.session_kill = True
    killed(w)
    restart(w)
    (cmd,) = w.sessions
    assert cmd[:4] == ["claude", "--resume", CUT, "-p"] and cmd[4] == E.CONTINUE
    assert labels(w) == ["mission", "review:open"] and BRANCH in w.host.prs


def test_engineer_cut_in_its_model_free_run_f219(w):
    """F219's own case: the session done, `engineer.json` written, the full
    run killed. Resumed: no session, the run again on the same commit."""
    to_approved(w)
    w.check_kill = (True, False)
    killed(w)
    full = [c for c in w.checks if c[1]]
    restart(w)
    assert len(w.sessions) == 1, "the finished session ran again"
    again = [c for c in w.checks if c[1]]
    assert len(again) == len(full) + 1 and again[-1][0] == full[-1][0], "not the same commit"
    assert labels(w) == ["mission", "review:open"] and BRANCH in w.host.prs


def test_engineer_cut_after_its_session_ended_before_the_journal_knew(w):
    """The session wrote its final JSON, and the kill fell before the
    journal recorded it: `session.json` says it ended; it is not run again."""
    to_approved(w)
    w.check_kill = (True, False)
    killed(w)
    (j,) = J.unfinished(w.fleet.runs)
    j.data["calls"][0].update(done=False)
    j.data["checks"].clear()
    j.save()
    (j.run / "run" / "session.json").write_text(json.dumps({"type": "result", "is_error": False,
                                                           "result": "done"}))
    restart(w)
    assert len(w.sessions) == 1, "a session that had ended ran again"
    assert labels(w) == ["mission", "review:open"]


def test_engineer_cut_after_its_push_before_the_pr(w):
    to_approved(w)
    w.kill.at(push, after=True)
    killed(w)
    full = len([c for c in w.checks if c[1]])
    restart(w)
    assert len([c for c in w.checks if c[1]]) == full, "the finished model-free run ran again"
    assert len(w.sessions) == 1 and BRANCH in w.host.prs
    assert labels(w) == ["mission", "review:open"]


def test_engineer_cut_after_opening_the_pr(w):
    to_approved(w)
    w.kill.at(lambda c: c[:3] == ["gh", "pr", "create"], after=True)
    killed(w)
    restart(w)
    assert len(w.host.prs) == 1 and w.host.prs[BRANCH]["comments"] == []
    assert said(w, f"{D.ENGINEER_M} pr-ready") == 1 and labels(w) == ["mission", "review:open"]


def test_engineer_cut_after_pr_ready_before_its_label(w):
    to_approved(w)
    w.kill.at(comment(f"{D.ENGINEER_M} pr-ready"), after=True)
    killed(w)
    restart(w)
    assert said(w, f"{D.ENGINEER_M} pr-ready") == 1 and labels(w) == ["mission", "review:open"]


def test_engineers_fix_round_cut_after_its_pr_comment(w):
    to_pr(w)
    advance(w, BACK)
    w.kill.at(pr_comment, after=True)
    killed(w)
    restart(w)
    fix = [b for b in w.host.prs[BRANCH]["comments"] if "fix round 1" in b]
    assert len(fix) == 1 and labels(w) == ["mission", "review:open"]


def test_engineers_escalation_cut_between_its_comment_and_its_label(w):
    to_approved(w)
    w.engineer.result = {"outcome": "stop", "kind": "fork", "question": "🔲 or 🚧?"}
    w.kill.at(comment(f"{D.MARKER} needs-admiral"), after=True)
    killed(w)
    restart(w)
    assert "needs-admiral" in labels(w) and said(w, f"{D.MARKER} needs-admiral") == 1
    assert len(w.sessions) == 1
    no_unfinished(w)


# ------------------------------------------------------------- the Red Team
def test_red_team_cut_in_its_f9_run(w):
    to_pr(w)
    w.check_kill = (False, True)
    killed(w)
    restart(w, BACK)
    assert labels(w) == ["build:open", "mission"] and said(w, D.RED_M) == 1


def test_red_team_cut_in_its_model_call(w):
    to_pr(w)
    w.kill.at(model, cut=True)
    killed(w)
    restart(w, BACK)
    assert calls(w)[-1][:3] == ["claude", "--resume", CUT]
    assert labels(w) == ["build:open", "mission"]


def test_red_team_cut_after_its_pr_comment(w):
    to_pr(w)
    w.kill.at(pr_comment, after=True)
    killed(w, BACK)
    restart(w)
    assert len(w.host.prs[BRANCH]["comments"]) == 1, "a second round-1 comment on the PR"
    assert said(w, f"{D.RED_M} verdict=back round=1") == 1
    assert labels(w) == ["build:open", "mission"]


def test_red_team_cut_after_its_verdict_before_its_label(w):
    to_pr(w)
    w.kill.at(comment(D.RED_M), after=True)
    killed(w, BACK)
    restart(w)
    assert said(w, D.RED_M) == 1 and labels(w) == ["build:open", "mission"]
    advance(w)                                                      # the fix round follows
    assert labels(w) == ["mission", "review:open"]


def test_red_team_clear_cut_after_its_push_before_review_clear(w):
    to_pr(w)
    w.kill.at(push, after=True)
    killed(w, CLEAR)
    restart(w)
    subject = f"Phase {PHASE}: the Red Team's refuter pass, round 1"
    assert commits(w, subject) == 1 and labels(w) == ["mission", "review:clear"]


# ------------------------------------------- the Captain's recommendation
def to_clear(w):
    to_pr(w)
    advance(w, CLEAR)


def test_recommendation_cut_in_its_model_call(w):
    to_clear(w)
    w.kill.at(model, cut=True)
    killed(w)
    restart(w, MERGE)
    assert calls(w)[-1][:3] == ["claude", "--resume", CUT]
    assert labels(w) == ["merge:needs-review", "mission"]


def test_recommendation_cut_after_its_pr_comment(w):
    to_clear(w)
    w.kill.at(pr_comment, after=True)
    killed(w, MERGE)
    restart(w)
    recs = [b for b in w.host.prs[BRANCH]["comments"] if "recommendation" in b]
    assert len(recs) == 1 and labels(w) == ["merge:needs-review", "mission"]


def test_recommendation_cut_after_its_marker(w):
    to_clear(w)
    w.kill.at(comment(f"{D.CAPTAIN_M} recommendation"), after=True)
    killed(w, MERGE)
    restart(w)
    assert said(w, f"{D.CAPTAIN_M} recommendation") == 1
    assert labels(w) == ["merge:needs-review", "mission"]


# ------------------------------------------------------------- the digest
def test_digest_cut_in_its_model_call(w):
    w.host.issues.clear()
    w.fleet.save({"last_digest": "2026-10-20"})
    w.kill.at(model, cut=True)
    killed(w)
    assert w.fleet.load()["last_digest"] == "2026-10-20"
    restart(w, DIGEST)
    assert calls(w)[-1][:3] == ["claude", "--resume", CUT]
    assert w.fleet.load()["last_digest"] == "2026-10-21"
    no_unfinished(w)


# ------------------------------- a model-free run lost to load (F220, #14)
def held_stop(w):
    to_approved(w)
    w.check_fail = True
    advance(w)
    (held,) = J.held_runs(w.fleet.runs, N)
    return held


def test_a_stop_whose_only_failure_is_the_model_free_run_is_held(w):
    held = held_stop(w)
    info = J.held(held)
    head = subprocess.run(["git", "-C", str(held / "clone"), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    assert info == {"issue": N, "phase": PHASE, "rnd": 0, "commit": head}
    assert "needs-admiral" in labels(w) and "take `needs-admiral` off" in w.host.comments(N)[-1]
    assert BRANCH not in w.host.prs
    n = len(w.host.comments(N))
    advance(w)                                           # the operator has not answered
    assert len(w.host.comments(N)) == n and J.held_runs(w.fleet.runs, N) == [held]


def test_taking_needs_admiral_off_runs_it_again_on_the_same_commit(w):
    held = held_stop(w)
    commit = J.held(held)["commit"]
    w.host.issues[N]["labels"].remove("needs-admiral")      # the operator's hand
    n = len(w.checks)
    advance(w)
    assert [c[:2] for c in w.checks[n:] if c[1]] == [(commit, True)]
    assert len(w.sessions) == 1, "the Engineer ran again"
    assert BRANCH in w.host.prs and labels(w) == ["mission", "review:open"]
    assert J.held_runs(w.fleet.runs, N) == [] and held.is_dir()
    advance(w, BACK)                                        # the Red Team, its next round
    assert said(w, f"{D.RED_M} verdict=back round=1") == 1


def test_a_failure_beyond_the_model_free_run_is_not_held(w, monkeypatch):
    to_approved(w)
    monkeypatch.setattr(D.engineer, "verify", lambda *a, **k: ["close-out: A6 the row is long"])
    w.check_fail = True
    advance(w)
    assert J.held_runs(w.fleet.runs, N) == []
    assert "take `needs-admiral` off" not in w.host.comments(N)[-1]
    w.host.issues[N]["labels"].remove("needs-admiral")
    n = len(w.host.comments(N))
    advance(w)
    assert len(w.host.comments(N)) == n and BRANCH not in w.host.prs


def test_the_recheck_failing_again_holds_again(w):
    held = held_stop(w)
    w.host.issues[N]["labels"].remove("needs-admiral")
    w.check_fail = True
    advance(w)
    assert "needs-admiral" in labels(w) and J.held_runs(w.fleet.runs, N) == [held]


def test_the_recheck_cut_in_its_model_free_run(w):
    held = held_stop(w)
    w.host.issues[N]["labels"].remove("needs-admiral")
    w.check_kill = (True, False)
    killed(w)
    said_lines = restart(w)
    assert said_lines[0].startswith("resume recheck")
    assert labels(w) == ["mission", "review:open"] and J.held_runs(w.fleet.runs, N) == []
    assert held.is_dir()


def test_prune_keeps_a_held_run(w, monkeypatch):
    held = held_stop(w)
    monkeypatch.setattr(D, "KEEP_RUNS", 0)
    w.fleet.prune_runs(set())
    assert held.is_dir()


# -------------------------------------------------- the pause (389's resume)
def test_a_pause_is_kept_until_its_resumed_stage_ends(w):
    """389 removed `paused` before running the resumed stage: a kill then
    lost it (Step 0, S0-2)."""
    to_review(w)
    w.host.usage_after = USAGE_LIMITED
    advance(w, LIMITED)
    paused = w.fleet.load()["paused"]
    w.clock.t = D._time(paused["until"]) + dt.timedelta(minutes=1)
    w.kill.at(model)
    killed(w)
    assert w.fleet.load()["paused"]["run"] == paused["run"], "the pause was lost"
    said_lines = restart(w)
    assert any(s.startswith("leave xo") for s in said_lines)
    advance(w, APPROVE, DIGEST)                 # the reset's day has its digest due too
    assert [c[:3] for c in calls(w) if "--resume" in c] == [["claude", "--resume",
                                                             "sess-limited-1"]]
    assert "plan:approved" in labels(w) or "review:open" in labels(w)
    assert "paused" not in w.fleet.load()
    assert len(list(w.fleet.runs.glob("*_xo_*"))) == 1, "a second XO run"
