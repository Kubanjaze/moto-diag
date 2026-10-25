"""Phase 389 — the dispatcher runs the four new ranks, label to label.

What must hold (the 389 prompt and v1.0's label table): one stage per
application of a label, each move made by script from a checked result;
pushes only through the gate, in the trial's name (the operator's login)
when the issue carries the trial marker, and never for any other issue
until the fleet has its own account; the Engineer's stops, the Red Team's
three rounds and the Captain's revision; the Fable gate.

git is real (an origin built from 387's good tree, with row 902 🚧 and no
documents yet); `gh`, the fence's model calls, the Engineer's session and
the model-free run are stand-ins on one clock.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "fleet"
FIX = SKILL / "fixtures"
sys.path.insert(0, str(SKILL))

import dispatcher as D  # noqa: E402
import fleet_git  # noqa: E402
import rank_call  # noqa: E402
from plan_check import GOOD  # noqa: E402
from test_phase388_dispatcher import T0, Clock, Host, claude_json  # noqa: E402
from test_phase389_fleet_git import git, make_origin  # noqa: E402
from test_phase389_red_team import FINDING, TABLE  # noqa: E402

PHASE = "902"
TITLE = f"Phase {PHASE}: the trial"
BRANCH = f"phase-{PHASE}-the-trial"
TRIAL = f"Add row 385.\n\n{fleet_git.TRIAL_MARKER}"
PLAN = (GOOD / "docs/phases/in_progress/900_implementation.md").read_text()
LINE = ("Regression of record: 1234 passed, 0 failed, 0 skipped, 0 errors at `ccccccc` "
        "(12 min 0 s wall, `python -m pytest -n auto --dist load`, exit 0)")
TERMS = json.loads((FIX / "scout" / "terms_good.json").read_text())
ASSESS = json.loads((FIX / "scout" / "assess_good.json").read_text())
USAGE_FABLE_FULL = (FIX / "dispatcher" / "usage_fable_at_ceiling.txt").read_text()


class GitHub(Host):
    """388's stand-in, with pull requests and issue titles."""

    def __init__(self, clock, fence):
        super().__init__(clock, fence)
        self.prs: dict[str, dict] = {}

    def gh(self, cmd):
        ok = lambda out="": subprocess.CompletedProcess(cmd, 0, out, "")  # noqa: E731
        if cmd[1] == "pr":
            if cmd[2] == "list":
                b = cmd[cmd.index("--head") + 1]
                return ok(json.dumps([{"number": p["number"], "url": p["url"]}
                                      for p in [self.prs.get(b)] if p]))
            if cmd[2] == "create":
                b, n = cmd[cmd.index("--head") + 1], 100 + len(self.prs)
                self.prs[b] = {"number": n, "url": f"https://github.com/pr/{n}",
                               "body": cmd[cmd.index("--body") + 1], "comments": []}
                return ok()
            pr = next(p for p in self.prs.values() if p["number"] == int(cmd[3]))
            if cmd[2] == "comment":
                pr["comments"].append(cmd[cmd.index("--body") + 1])
                return ok()
            return ok(pr["body"])                               # pr view --jq .body
        if cmd[1:3] == ["issue", "view"] and cmd[cmd.index("--json") + 1] == "title":
            return ok(json.dumps({"title": self.issues[int(cmd[3])]["title"]}))
        return super().gh(cmd)


class FakeEngineer:
    """The Engineer's session as a Popen: it commits in its clone, writes its
    result, and exits."""

    def __init__(self, result: dict | None = None, rc: int = 0):
        self.result = result or {"outcome": "pr-ready", "summary": "Row 385 added.",
                                 "regression_line": LINE}
        self.rc, self.runs = rc, 0

    def __call__(self, cmd, stdout, stderr, **kw):
        self.runs += 1
        clone = pathlib.Path(cmd[cmd.index("--clone") + 1])
        run = pathlib.Path(cmd[cmd.index("--run") + 1])
        log = clone / "docs" / "phases" / "in_progress" / f"{PHASE}_phase_log.md"
        log.write_text(f"# {PHASE} log\n\nRound {self.runs}.\n\nNo refute pass ran.\n")
        if self.runs == 1:
            roadmap = clone / "docs" / "ROADMAP.md"
            roadmap.write_text(roadmap.read_text().rstrip("\n")
                               + "\n| 385 | The push token's own write | 🔲 | Not started. |\n")
        git("add", "-A", cwd=clone)
        git("commit", "-qm", f"round {self.runs}", cwd=clone)
        (run / "engineer.json").write_text(json.dumps(self.result))
        stdout.write(json.dumps({"is_error": False, "result": "done"}))
        stdout.flush()
        rc = self.rc
        return type("Proc", (), {"poll": lambda s: rc, "returncode": rc,
                                 "terminate": lambda s: None})()


@pytest.fixture(autouse=True)
def ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("FLEET_LEDGER", str(tmp_path / "calls.jsonl"))


@pytest.fixture
def world(tmp_path, monkeypatch):
    origin = make_origin(tmp_path)
    road = origin / "docs" / "ROADMAP.md"
    road.write_text(road.read_text().rstrip("\n") + f"\n| {PHASE} | The trial | 🚧 | x |\n")
    git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qam", "row 902", cwd=origin)
    clock = Clock()
    host = GitHub(clock, tmp_path / "fence.sh")
    checks: list[tuple] = []

    def check(clone, commit, *, full, command=None):
        checks.append((commit, full, command))
        return D.Check(True, commit, LINE if full else None, "F9 lint: clean" if command else "")

    engineer = FakeEngineer()
    lines: list[str] = []
    fleet = D.Fleet(state=tmp_path / "state", token="sk-ant-oat01-test-token", host=host,
                    fence=tmp_path / "fence.sh", workspace_docs=tmp_path / "wsd",
                    repo_url=str(origin), now=clock, out=lines.append,
                    identity_file=tmp_path / "no-identity.env", popen=engineer, check=check,
                    sleep=lambda s: None, venv=tmp_path / "no-venv", mobile=tmp_path / "no-mobile")
    fleet.save({"last_digest": "2026-10-21"})
    monkeypatch.setattr(D.engineer, "verify", lambda *a, **k: [])
    return fleet, host, clock, origin, engineer, checks, lines


def step(clock, fleet, host, *replies):
    clock.t += dt.timedelta(minutes=5)
    host.replies = list(replies)
    fleet.cycle()
    assert host.replies == [], f"replies left unused: {len(host.replies)}"


def labels(host, n=31):
    return sorted(host.issues[n]["labels"])


def on_origin(origin, ref):
    return subprocess.run(["git", "-C", str(origin), "rev-parse", "--verify", "-q", ref],
                          capture_output=True, text=True).returncode == 0


def test_mission_to_merge_needs_review(world):
    fleet, host, clock, origin, engineer, checks, lines = world
    master = git("rev-parse", "master", cwd=origin).stdout
    host.issue(31, TITLE, TRIAL, {"mission": T0})

    # the Science Officer
    step(clock, fleet, host, claude_json(TERMS, model=rank_call.HAIKU),
         claude_json(ASSESS, model=rank_call.HAIKU))
    assert labels(host) == ["mission", "step0:done"]
    assert on_origin(origin, f"refs/heads/{BRANCH}")
    files = git("ls-tree", "-r", "--name-only", BRANCH, cwd=origin).stdout.split()
    assert f"docs/phases/in_progress/{PHASE}_step0.md" in files
    assert "docs/prompts/902_the_trial.txt" in files
    author = git("log", "-1", "--format=%an <%ae>", BRANCH, cwd=origin).stdout.strip()
    assert author == "MotoDiag fleet (scout) <fleet@motodiag.invalid>"
    assert "Co-Authored-By: Claude Haiku 5.5" in git("log", "-1", "--format=%B", BRANCH, cwd=origin).stdout

    # the Captain
    step(clock, fleet, host, claude_json({"implementation_md": PLAN}))
    assert labels(host) == ["mission", "plan:needs-review"]
    assert git("log", "-1", "--format=%s", BRANCH, cwd=origin).stdout.strip() == f"Phase {PHASE} v1.0: the plan"

    # the XO (387's, unchanged)
    step(clock, fleet, host, claude_json({"verdict": "approve", "items": [], "reason": "ok"}))
    assert labels(host) == ["mission", "plan:approved"]

    # the Engineer
    step(clock, fleet, host)
    assert labels(host) == ["mission", "review:open"] and engineer.runs == 1
    pr = host.prs[BRANCH]
    assert "Mission: #31" in pr["body"] and LINE in pr["body"]
    assert any(full for _, full, cmd in checks if cmd is None), "no model-free full run"
    roadmap = git("show", f"{BRANCH}:docs/ROADMAP.md", cwd=origin).stdout
    assert "| 385 | The push token's own write | 🔲 |" in roadmap

    # the Red Team, round 1: back
    step(clock, fleet, host, claude_json({"verdict": "back", "findings": [FINDING],
                                          "refuter_pass": TABLE}, model=rank_call.OPUS))
    assert labels(host) == ["build:open", "mission"]
    assert "Red Team, round 1: back" in pr["comments"][-1] and "F213" in pr["comments"][-1]

    # the Engineer, fix round 1
    step(clock, fleet, host)
    assert labels(host) == ["mission", "review:open"] and engineer.runs == 2
    assert "fix round 1" in pr["comments"][-1]

    # the Red Team, round 2: clear, its table committed into the log
    step(clock, fleet, host, claude_json({"verdict": "clear", "findings": [],
                                          "refuter_pass": TABLE}, model=rank_call.OPUS))
    assert labels(host) == ["mission", "review:clear"]
    log = git("show", f"{BRANCH}:docs/phases/in_progress/{PHASE}_phase_log.md", cwd=origin).stdout
    assert "## Refuter pass" in log and "No refute pass ran." not in log

    # the Captain's recommendation
    step(clock, fleet, host, claude_json({"decision": "merge",
                                          "lines": ["It adds row 385.", "All checks green.",
                                                    "Merge."]}))
    assert labels(host) == ["merge:needs-review", "mission"]
    assert "The Captain's recommendation: merge" in pr["comments"][-1]

    # nothing more until the operator merges; master never moved
    step(clock, fleet, host)
    assert git("rev-parse", "master", cwd=origin).stdout == master
    assert host.fenced and all(kw["pass_fds"] == (3,) and kw["env"].keys() == {"PATH"}
                               for _, kw in host.fenced), "a fenced call without the token pipe"


def test_master_is_never_pushed(world):
    fleet, host, clock, origin, *_ = world
    before = git("rev-parse", "master", cwd=origin).stdout
    host.issue(31, TITLE, TRIAL, {"mission": T0})
    step(clock, fleet, host, claude_json(TERMS, model=rank_call.HAIKU),
         claude_json(ASSESS, model=rank_call.HAIKU))
    assert git("rev-parse", "master", cwd=origin).stdout == before


def test_without_the_account_a_real_mission_needs_hands_and_nothing_is_pushed(world):
    fleet, host, clock, origin, *_ = world
    host.issue(31, TITLE, "A real mission, not planted.", {"mission": T0})
    step(clock, fleet, host)
    assert labels(host) == ["mission", "needs-hands"]
    assert "389_operator_steps.md" in host.comments(31)[-1]
    assert host.model_calls() == [] and not on_origin(origin, f"refs/heads/{BRANCH}")
    step(clock, fleet, host)                    # left alone while needs-hands is on
    assert len(host.comments(31)) == 1


def test_the_captain_revises_after_the_xo_sends_it_back(world):
    fleet, host, clock, *_ = world
    host.issue(31, TITLE, TRIAL, {"mission": T0})
    step(clock, fleet, host, claude_json(TERMS, model=rank_call.HAIKU),
         claude_json(ASSESS, model=rank_call.HAIKU))
    step(clock, fleet, host, claude_json({"implementation_md": PLAN}))
    step(clock, fleet, host, claude_json({"verdict": "back-to-captain",
                                          "items": ["Say which file holds the row."],
                                          "reason": "One defect."}))
    assert labels(host) == ["mission", "plan:needs-review"]
    step(clock, fleet, host, claude_json({"implementation_md": PLAN + "\nRevised.\n"}))
    revision = host.model_calls()[-1][2]
    assert "- Say which file holds the row." in revision
    assert host.comments(31)[-1].startswith(f"{D.CAPTAIN_M} revision round=1")
    step(clock, fleet, host, claude_json({"verdict": "approve", "items": [], "reason": "ok"}))
    assert labels(host) == ["mission", "plan:approved"]


def go_to_approved(world):
    fleet, host, clock, *_ = world
    host.issue(31, TITLE, TRIAL, {"mission": T0})
    step(clock, fleet, host, claude_json(TERMS, model=rank_call.HAIKU),
         claude_json(ASSESS, model=rank_call.HAIKU))
    step(clock, fleet, host, claude_json({"implementation_md": PLAN}))
    step(clock, fleet, host, claude_json({"verdict": "approve", "items": [], "reason": "ok"}))


def test_an_engineer_stop_goes_to_the_admiral_with_its_question(world):
    fleet, host, clock, origin, engineer, *_ = world
    go_to_approved(world)
    engineer.result = {"outcome": "stop", "kind": "fork",
                       "question": "Should row 385 say 🔲 or 🚧?"}
    step(clock, fleet, host)
    assert "needs-admiral" in labels(host) and "🔲 or 🚧" in host.comments(31)[-1]
    assert BRANCH not in host.prs


def test_a_watcher_reason_goes_to_the_admiral(world, monkeypatch):
    fleet, host, clock, *_ = world
    go_to_approved(world)
    monkeypatch.setattr(D.engineer, "watch", lambda *a: "third-bug-fix: the log reached #3")
    step(clock, fleet, host)
    assert "needs-admiral" in labels(host) and "third-bug-fix" in host.comments(31)[-1]


def test_failed_checks_after_pr_ready_go_to_the_admiral(world, monkeypatch):
    fleet, host, clock, *_ = world
    go_to_approved(world)
    monkeypatch.setattr(D.engineer, "verify", lambda *a, **k: ["close-out: A6 the row is too long"])
    step(clock, fleet, host)
    assert "needs-admiral" in labels(host) and "A6" in host.comments(31)[-1]
    assert BRANCH not in host.prs


def test_a_failed_model_free_run_goes_to_the_admiral(world):
    fleet, host, clock, *_ = world
    go_to_approved(world)
    fleet.check = lambda clone, commit, *, full, command=None: D.Check(
        not full, commit, "Regression run FAILED (not of record): 1 failed", "1 failed")
    step(clock, fleet, host)
    assert "needs-admiral" in labels(host) and "did not pass" in host.comments(31)[-1]


def test_three_red_team_rounds_then_the_admiral(world):
    fleet, host, clock, *_ = world
    go_to_approved(world)
    step(clock, fleet, host)                                      # the PR
    back = claude_json({"verdict": "back", "findings": [FINDING], "refuter_pass": TABLE},
                       model=rank_call.OPUS)
    for rnd in (1, 2):
        step(clock, fleet, host, back)
        assert "build:open" in labels(host), rnd
        step(clock, fleet, host)                                  # the fix round
    step(clock, fleet, host, back)
    assert "needs-admiral" in labels(host) and "round 3 of 3" in host.comments(31)[-1]


def test_a_new_fable_stage_over_fables_ceiling_never_starts(world):
    fleet, host, clock, *_ = world
    host.issue(31, TITLE, TRIAL, {"mission": T0})
    step(clock, fleet, host, claude_json(TERMS, model=rank_call.HAIKU),
         claude_json(ASSESS, model=rank_call.HAIKU))
    host.usage_text = USAGE_FABLE_FULL
    calls = len(host.model_calls())
    step(clock, fleet, host)
    assert len(host.model_calls()) == calls
    assert labels(host) == ["mission", "step0:done"], "the label moved"
    assert "no new Fable stage" in host.comments(31)[-1]
    step(clock, fleet, host)                         # a stop is not retried unasked
    assert len(host.model_calls()) == calls


def test_a_closed_phase_gets_no_stage(world):
    fleet, host, clock, *_ = world
    host.issue(9, "Phase 898: a closed phase", TRIAL, {"mission": T0, "plan:approved": T0})
    step(clock, fleet, host)
    assert host.model_calls() == [] and host.comments(9) == []
