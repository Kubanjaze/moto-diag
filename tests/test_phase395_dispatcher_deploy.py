"""Phase 395 — the dispatcher hands the operator the database step, and resumes.

The prompt: "On a believed deploy, the dispatcher pushes the branch, holds
the run (held.json, why: deploy), posts one comment on the mission issue
and adds needs-hands", and "When I take needs-hands off, the dispatcher
checks that live equals the approved diff (verify-live). It then gives the
Engineer a close-out round in the same clone ... then pr-ready as today."

On 390's harness (real git, a stand-in GitHub, the Engineer's session and
the model-free run stood in). `verify-live` is stood in too: the real one
is `tests/test_phase395_through_fleet.py`'s and the trial's.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "fleet"
FIX = SKILL / "fixtures" / "deploy"
sys.path.insert(0, str(SKILL))
sys.path.insert(0, str(ROOT / "tests"))

import captain  # noqa: E402
import dispatcher as D  # noqa: E402
import journal as J  # noqa: E402
import xo  # noqa: E402
from test_phase389_dispatcher import BRANCH, LINE, PHASE  # noqa: E402
from test_phase390_resume import (  # noqa: E402
    Killed,
    N,
    advance,
    killed,
    labels,
    ledger,
    restart,
    to_approved,
    w,
)

assert w and ledger  # the fixtures, imported for their names

RESULT = {**json.loads((FIX / "deploy_result.json").read_text()), "regression_line": LINE}
LIVE_CHANGE = RESULT["live_change"]


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


class DeployEngineer:
    """The Engineer's sessions: the first builds and ends `deploy`; the
    close-out round quotes the answer and ends `pr-ready`. `extra` is what
    the close-out round also writes (a known-bad case)."""

    def __init__(self):
        self.runs, self.extra = 0, {}

    def __call__(self, cmd, stdout, stderr, **kw):
        self.runs += 1
        clone = pathlib.Path(cmd[cmd.index("--clone") + 1])
        run = pathlib.Path(cmd[cmd.index("--run") + 1])
        inp = clone / "docs" / "phases" / "in_progress"
        inp.mkdir(parents=True, exist_ok=True)
        log = inp / f"{PHASE}_phase_log.md"
        if self.runs == 1:
            (inp / f"{PHASE}_deploy_scope.json").write_text(json.dumps(
                {"tables": {"schema_version": {"added": 1}},
                 "schema": {"added": ["table trial_empty"]}}))
            log.write_text(f"# {PHASE} log\n\n{LINE}\n\nNo refute pass ran.\n")
            result = RESULT
        else:
            log.write_text(log.read_text() + "\n## The operator's answer\n\n> yes\n")
            for rel, text in self.extra.items():
                (clone / rel).parent.mkdir(parents=True, exist_ok=True)
                (clone / rel).write_text(text)
            result = {"outcome": "pr-ready", "summary": "Closed out.", "regression_line": LINE}
        git(clone, "add", "-A")
        git(clone, "-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qm",
            f"session {self.runs}")
        (run / "engineer.json").write_text(json.dumps(result))
        stdout.write(json.dumps({"is_error": False, "result": "done"}))
        stdout.flush()
        return type("Proc", (), {"poll": lambda s: 0, "returncode": 0,
                                 "terminate": lambda s: None})()


class Live:
    """`verify-live`, stood in: what it says, and every call."""

    def __init__(self):
        self.rc, self.text, self.calls = 0, "  equals the approved exact diff: yes\n", []

    def __call__(self, clone, phase):
        self.calls.append((clone, phase))
        return self.rc, self.text


@pytest.fixture
def d(w, tmp_path, monkeypatch):
    live = Live()
    monkeypatch.setattr(D, "verify_live_here", live)
    monkeypatch.setattr(D.through_fleet, "deploy_root", lambda: tmp_path / "deploy")
    monkeypatch.setattr(D.engineer, "verify_deploy", lambda *a, **k: [])
    w.engineer = DeployEngineer()
    w.make()
    w.live = live
    return w


def to_deploy(w) -> pathlib.Path:
    to_approved(w)
    advance(w)
    (held,) = J.held_runs(w.fleet.runs, N)
    return held


def operator_block(w, extra: dict[str, str] | None = None) -> str:
    """What the operator's paste leaves: a deploy checkout of the pushed
    commit with the step's commits; then `needs-hands` off."""
    co = w.tmp / "deploy" / PHASE
    git(w.tmp, "clone", "-q", str(w.origin), str(co))
    git(co, "checkout", "-q", BRANCH)
    inp = co / "docs" / "phases" / "in_progress"
    (inp / f"{PHASE}_dryrun_diff.md").write_text("# dry run\n")
    (inp / f"{PHASE}_deploy_answer.md").write_text("# answer\n\n> yes\n")
    for rel, text in (extra or {}).items():
        (co / rel).parent.mkdir(parents=True, exist_ok=True)
        (co / rel).write_text(text)
    git(co, "add", "-A")
    git(co, "-c", "user.name=o", "-c", "user.email=o@o", "commit", "-qm", "the dry run, and yes")
    (inp / f"{PHASE}_live_diff.md").write_text("# live\n")
    git(co, "add", "-A")
    git(co, "-c", "user.name=o", "-c", "user.email=o@o", "commit", "-qm", "the live diff")
    w.host.issues[N]["labels"].remove("needs-hands")
    return git(co, "rev-parse", "HEAD")


def test_a_deploy_is_pushed_held_and_handed_to_the_operator(d):
    held = to_deploy(d)
    head = git(held / "clone", "rev-parse", "HEAD")
    assert J.held(held) == {"issue": N, "phase": PHASE, "rnd": 0, "commit": head, "why": "deploy"}
    assert labels(d) == ["build:open", "mission", "needs-hands"]
    assert git(d.origin, "rev-parse", BRANCH) == head, "the branch was not pushed"
    assert BRANCH not in d.host.prs, "a pull request opened before the database step"
    said = d.host.comments(N)[-1]
    assert said.startswith(f"{D.DEPLOY_M} phase={PHASE} commit={head}")
    assert "**Which computer:** the home desktop. **Which window:** the Ubuntu terminal." in said
    assert LIVE_CHANGE in said and "table trial_empty" in said
    assert f'"$PY" "$STEP" {PHASE} {BRANCH} {head} </dev/null || exit 1' in said
    assert f"gh issue edit {N} -R Kubanjaze/moto-diag --remove-label needs-hands" in said
    block = said.split("```bash", 1)[1].split("```", 1)[0]
    assert block.rstrip().splitlines()[-2] == 'echo "ALL GOOD"'
    assert "SOMETHING IS OFF" in block
    for internal in ("K58", "F232", "Q1", "verify-live", "deploy:"):
        assert internal not in said, f"an internal label in the operator's comment: {internal}"
    n = len(d.host.comments(N))
    advance(d)                                     # the operator has not pasted yet
    assert len(d.host.comments(N)) == n and d.engineer.runs == 1 and d.live.calls == []


def test_the_resume_closes_out_in_the_same_clone_and_opens_the_pr(d):
    held = to_deploy(d)
    applied = operator_block(d)
    advance(d)
    assert labels(d) == ["mission", "review:open"] and BRANCH in d.host.prs
    assert d.engineer.runs == 2 and d.live.calls == [(held / "clone", PHASE)]
    assert "The database step is done" in d.session_briefs[-1]
    assert git(d.origin, "merge-base", "--is-ancestor", applied, BRANCH) == ""
    files = git(d.origin, "ls-tree", "-r", "--name-only", BRANCH).split()
    for kind in ("dryrun_diff", "deploy_answer", "live_diff"):
        assert f"docs/phases/in_progress/{PHASE}_{kind}.md" in files
    assert J.held_runs(d.fleet.runs, N) == [] and (held / "run" / "engineer.deploy.json").is_file()


def test_the_known_bad_resume_with_live_not_equal_goes_to_the_operator(d):
    case = json.loads((FIX / "known_bad" / "resume_live_not_equal.json").read_text())
    held = to_deploy(d)
    operator_block(d)
    d.live.rc, d.live.text = case["exit"], case["printed"]
    advance(d)
    assert "needs-admiral" in labels(d) and BRANCH not in d.host.prs
    assert case["refusal"] in d.host.comments(N)[-1]
    assert d.engineer.runs == 1, "the close-out ran on a live database that is not the approved one"
    assert J.held(held)["why"] == "deploy", "the hold was let go"


def test_after_live_is_put_right_the_close_out_runs_from_the_same_hold(d):
    held = to_deploy(d)
    operator_block(d)
    d.live.rc = 3
    advance(d)
    d.host.issues[N]["labels"].remove("needs-admiral")
    d.live.rc = 0
    advance(d)
    assert labels(d) == ["mission", "review:open"] and J.held_runs(d.fleet.runs, N) == []
    assert held.is_dir()


def test_a_checkout_that_changes_more_than_the_step_files_stops(d):
    to_deploy(d)
    operator_block(d, extra={"src/motodiag/core/trial.py": "X = 1\n"})
    advance(d)
    assert "it may add only" in d.host.comments(N)[-1]
    assert d.engineer.runs == 1 and d.live.calls == [] and BRANCH not in d.host.prs


def test_no_checkout_means_the_block_has_not_run(d):
    to_deploy(d)
    d.host.issues[N]["labels"].remove("needs-hands")
    advance(d)
    assert "has not run on this computer" in d.host.comments(N)[-1]
    assert d.engineer.runs == 1


def test_the_known_bad_code_change_after_the_apply_is_refused(d):
    case = json.loads((FIX / "known_bad" / "code_after_apply.json").read_text())
    to_deploy(d)
    operator_block(d)
    d.engineer.extra = case["write"]
    advance(d)
    assert "needs-admiral" in labels(d) and BRANCH not in d.host.prs
    assert case["refusal"] in d.host.comments(N)[-1]


def test_deployed_cut_in_its_close_out_session(d):
    to_deploy(d)
    operator_block(d)
    d.session_kill = True
    killed(d)
    said = restart(d)
    assert said[0].startswith("resume deployed")
    assert labels(d) == ["mission", "review:open"] and BRANCH in d.host.prs


def test_a_deploy_whose_model_free_run_fails_is_held_for_a_recheck_that_hands_over_again(d):
    to_approved(d)
    d.check_fail = True
    advance(d)
    (held,) = J.held_runs(d.fleet.runs, N)
    assert "why" not in J.held(held) and "needs-admiral" in labels(d)
    d.host.issues[N]["labels"].remove("needs-admiral")
    advance(d)
    assert J.held(held)["why"] == "deploy" and "needs-hands" in labels(d)
    assert d.host.comments(N)[-1].startswith(D.DEPLOY_M)


def test_a_session_killed_before_it_can_hand_over_says_nothing_to_the_operator(d):
    """The control for the kill-point test: Killed is not swallowed."""
    to_approved(d)
    d.session_kill = True
    with pytest.raises(Killed):
        d.fleet.cycle()
    assert not any(c.startswith(D.DEPLOY_M) for c in d.host.comments(N))


def test_the_quartermaster_hands_q1_verify_live_outside_the_fence(d, monkeypatch):
    held = to_deploy(d)
    operator_block(d)
    advance(d)
    seen = {}

    def scope(clone, phase, base="master", live_check=None):
        seen["said"] = live_check() if live_check else None
        return D.quartermaster.Finding("Q1", False, "recorded")
    monkeypatch.setattr(D.quartermaster, "scope", scope)
    d.fleet.stage_quartermaster(N, PHASE, d.host.issues[N]["body"], BRANCH)
    assert seen["said"] == (0, d.live.text) and d.live.calls[-1][1] == PHASE
    assert held.is_dir()


# -------------------------------------------------------------- the planners
def test_the_planners_put_a_named_migration_in_scope():
    for brief in (captain.BRIEF, xo.BRIEF):
        flat = " ".join(brief.split())
        assert "## The database step" in flat
        assert "changes or deletes existing live rows" in flat and "rule-1 stop" in flat
