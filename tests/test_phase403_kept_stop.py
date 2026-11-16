"""Phase 403 (a) — a stop keeps its work (F266, F231, K84).

What must hold (the 403 prompt, (a)): a stop whose clone holds commits that
GitHub's branch does not keeps its run (a new hold reason, `stopped`), so
the next round starts from those commits; the commits go through the push
gate to `phase-<N>-stopped-<run>`, never the phase branch, every check
holding but the model-free run; the stop note names the commits and says
where they are; commits pushed by hand meanwhile are not a refusal.

372's three stops are replayed from `tests/fixtures/phase403/stops_372.json`:
each one's kind, its stop note's words, GitHub's branch then and the
commits only its clone had (by subject, from git; the first two runs were
pruned before this phase, the third's folder was copied). Through 390's
world: real git, a stand-in GitHub, the session stood in by one that makes
those commits and stops as the real one did.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "fleet"
FIX = ROOT / "tests" / "fixtures" / "phase403"
sys.path.insert(0, str(SKILL))
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "closeout"))
sys.path.insert(0, str(ROOT / "tests"))

import _edit_guard  # noqa: E402
import dispatcher as D  # noqa: E402
import fleet_git  # noqa: E402
import journal as J  # noqa: E402
from test_phase389_dispatcher import BRANCH, PHASE, FakeEngineer  # noqa: E402
from test_phase389_fleet_git import git  # noqa: E402
from test_phase390_resume import N, advance, labels, ledger, restart, to_approved, w  # noqa: E402

assert w and ledger  # the fixtures, imported for their names

STOPS = json.loads((FIX / "stops_372.json").read_text(encoding="utf-8"))
ANSWERS = [c for c in json.loads((FIX / "issue59_stops_and_answers.json").read_text(
    encoding="utf-8")) if c["author"]["login"] == fleet_git.OPERATOR_LOGIN]
HOOK = "PreToolUse:Bash hook error:"


def out(*args, cwd) -> str:
    return git(*args, cwd=cwd).stdout.strip()


def guard_refusal() -> str:
    """The edit guard's refusal of 372's `> $b.inner`, as the hook prints it."""
    why = _edit_guard.check("cat /fleet/run/a > $b.inner", "/fleet/moto-diag")
    assert why, "the edit guard let a variable's redirect through"
    return f"[${{CLAUDE_PROJECT_DIR}}/.claude/skills/closeout/edit_guard.sh]: edit guard: blocked — {why}"


class Stopping:
    """The stopped session: the fixture's commits, by subject, then its stop.
    `commits=False`: it stops having committed nothing. Later sessions are
    `then`'s. Each session's clone history is kept in `seen`."""

    def __init__(self, stop: dict, then=None, commits: bool = True):
        self.stop, self.commits, self.then = stop, commits, then or FakeEngineer()
        self.runs, self.seen, self.heads = 0, [], []

    def __call__(self, cmd, stdout, stderr, **kw):
        self.runs += 1
        clone = pathlib.Path(cmd[cmd.index("--clone") + 1])
        run = pathlib.Path(cmd[cmd.index("--run") + 1])
        self.seen.append(out("log", "--format=%s", cwd=clone).splitlines())
        self.heads.append(out("rev-parse", "HEAD", cwd=clone))
        if self.runs > 1:
            return self.then(cmd, stdout, stderr, **kw)
        for k, c in enumerate(self.stop["commits"] if self.commits else []):
            (clone / "docs" / f"stopped_{k}.md").write_text(c["subject"] + "\n")
            git("add", "-A", cwd=clone)
            git("commit", "-qm", c["subject"], cwd=clone)
        if self.stop["kind"] == "guard-blocked-twice":
            t = run / "claude" / "projects" / "-fleet-moto-diag" / "sess-stop.jsonl"
            t.parent.mkdir(parents=True, exist_ok=True)
            part = {"type": "tool_result", "is_error": True,
                    "content": f"{HOOK} {guard_refusal()}"}
            t.write_text("".join(json.dumps({"message": {"content": [part]}}) + "\n"
                                 for _ in range(2)))
        else:
            (run / "engineer.json").write_text(json.dumps(
                {"outcome": "stop", "kind": self.stop["kind"], "question": self.stop["stop_text"]
                 .split(f"({self.stop['kind']}). ", 1)[-1]}))
        stdout.write(json.dumps({"is_error": False, "result": "stopped"}))
        stdout.flush()
        return type("Proc", (), {"poll": lambda s: 0, "returncode": 0,
                                 "terminate": lambda s: None})()


def stop_at(w, stop: dict, **kw) -> Stopping:
    """The build stops as `stop` did, from `plan:approved`."""
    w.engineer = Stopping(stop, **kw)
    to_approved(w)
    w.engineer.before = out("rev-parse", BRANCH, cwd=w.origin)
    advance(w)
    return w.engineer


def side(w) -> str:
    (run,) = [p for p in J.held_runs(w.fleet.runs, N)]
    return fleet_git.side_branch(PHASE, run.name)


def answer(w, text: str, login: str = fleet_git.OPERATOR_LOGIN) -> None:
    """A comment on the issue by `login`, then `needs-admiral` taken off."""
    w.clock.t += D.dt.timedelta(minutes=1)
    w.host.commenter, was = login, w.host.commenter
    w.host.gh(["gh", "issue", "comment", str(N), "--body", text])
    w.host.commenter = was
    if "needs-admiral" in w.host.issues[N]["labels"]:
        w.host.issues[N]["labels"].remove("needs-admiral")


@pytest.mark.parametrize("k", range(3), ids=[s["run"] for s in STOPS])
def test_372s_stop_keeps_its_commits_on_a_side_branch(w, k):
    """Red on the old code: nothing held, nothing pushed, the commits only in
    the run's clone (F266's three rescues)."""
    stop = STOPS[k]
    before = stop_at(w, stop).before
    (run,) = J.held_runs(w.fleet.runs, N)
    info = J.held(run)
    assert info["why"] == "stopped" and info["kind"] == stop["kind"]
    head = out("rev-parse", "HEAD", cwd=run / "clone")
    assert info["commit"] == head
    assert out("rev-parse", BRANCH, cwd=w.origin) == before, "the phase branch moved"
    sb = fleet_git.side_branch(PHASE, run.name)
    assert out("rev-parse", sb, cwd=w.origin) == head, "the side branch is not on GitHub"
    subjects = out("log", "--format=%s", f"{before}..{sb}", cwd=w.origin).splitlines()
    assert subjects == [c["subject"] for c in reversed(stop["commits"])]
    note = w.host.comments(N)[-1]
    assert note.startswith(f"{D.MARKER} needs-admiral rank=engineer stop={stop['kind']}")
    for c in out("log", "--format=%H %s", f"{before}..{sb}", cwd=w.origin).splitlines():
        sha, subject = c.split(" ", 1)
        assert f"`{sha[:12]}` {subject}" in note
    assert f"side branch `{sb}`, not on the phase branch `{BRANCH}`" in note
    assert "the next round starts from these commits" in note
    assert "needs-admiral" in labels(w)


def test_the_guard_stop_is_the_real_refusal():
    """The second stop's note, as GitHub keeps it, is cut at 200 characters:
    it is the start of what the edit guard says today about `> $b.inner`."""
    said = STOPS[1]["stop_text"].split("a guard blocked the same thing twice: ", 1)[1]
    now = guard_refusal()
    for part in ("edit_guard.sh]: edit guard: blocked — the edit guard cannot tell where the "
                 "redirect `>` `$b.", "writes (a variable, substitution, glob or unknown dire"):
        assert part in said and part in now, part


@pytest.mark.parametrize("k", range(3), ids=[s["run"] for s in STOPS])
def test_the_next_round_starts_from_the_kept_commits(w, k):
    """The operator's answer (372's own, for this stop) and the label off:
    the Engineer's next session has the stopped commits in its clone, and
    the hold is let go."""
    eng = stop_at(w, STOPS[k])
    held = J.held_runs(w.fleet.runs, N)[0]
    answer(w, ANSWERS[k]["body"])
    advance(w)
    assert eng.runs == 2
    for c in STOPS[k]["commits"]:
        assert c["subject"] in eng.seen[1]
    assert J.held(held) is None, "the hold outlived the round it was for"
    assert labels(w) == ["mission", "review:open"] and BRANCH in w.host.prs
    pushed = out("log", "--format=%s", BRANCH, cwd=w.origin).splitlines()
    for c in STOPS[k]["commits"]:
        assert c["subject"] in pushed, "the kept commits did not reach the phase branch"


def test_commits_pushed_by_hand_on_top_are_not_a_refusal(w):
    """As on 2026-11-14: the operator pushed the kept commits to the phase
    branch by hand (a fast-forward). GitHub's branch is then an ancestor of
    the kept run's head, so the round starts from the kept run."""
    eng = stop_at(w, STOPS[2])
    held = J.held_runs(w.fleet.runs, N)[0]
    head = J.held(held)["commit"]
    git("push", "-q", str(w.origin), f"{head}:refs/heads/{BRANCH}", cwd=held / "clone")
    answer(w, ANSWERS[2]["body"])
    advance(w)
    assert all(c["subject"] in eng.seen[1] for c in STOPS[2]["commits"])
    assert any("the Engineer starts from the held run" in ln for ln in w.lines)
    assert out("rev-parse", BRANCH, cwd=w.origin) != head, "nothing went on top of the kept run"


def test_a_phase_branch_moved_past_the_kept_run_is_started_from_and_said(w):
    """GitHub's branch moved on by hand past the kept commits, or beside
    them: not an ancestor, so the round starts from GitHub's branch, and the
    log says so."""
    eng = stop_at(w, STOPS[0])
    work = w.tmp / "hand"
    git("clone", "-q", "--branch", BRANCH, str(w.origin), str(work), cwd=w.tmp)
    (work / "docs" / "by_hand.md").write_text("The operator's own commit.\n")
    git("add", "-A", cwd=work)
    git("-c", "user.name=op", "-c", "user.email=op@l", "commit", "-qm", "by hand", cwd=work)
    git("push", "-q", "origin", BRANCH, cwd=work)
    answer(w, ANSWERS[0]["body"])
    advance(w)
    assert "by hand" in eng.seen[1]
    assert not any(c["subject"] in eng.seen[1] for c in STOPS[0]["commits"])
    assert any("it is not an ancestor of the held run" in ln for ln in w.lines)


def test_a_stop_with_no_new_commits_holds_nothing(w):
    """Known-bad: a stop before any commit holds no run and pushes nothing."""
    stop_at(w, STOPS[0], commits=False)
    assert J.held_runs(w.fleet.runs, N) == []
    assert not out("branch", "--list", f"phase-{PHASE}-stopped-*", cwd=w.origin)
    note = w.host.comments(N)[-1]
    assert note.startswith(f"{D.MARKER} needs-admiral rank=engineer stop=")
    assert "What the stopped session committed" not in note


def test_a_kept_run_outlives_a_restart_and_is_never_pruned(w):
    stop_at(w, STOPS[2])
    (run,) = J.held_runs(w.fleet.runs, N)
    restart(w)
    for k in range(D.KEEP_RUNS + 3):
        w.clock.t += D.dt.timedelta(minutes=1)
        w.fleet.new_run(f"filler{k}")
    w.fleet.prune_runs(set())
    assert run.is_dir() and J.held(run)["why"] == "stopped"
    assert (run / "clone" / ".git").is_dir()


def test_no_pull_request_is_ever_opened_from_the_side_branch(w):
    stop_at(w, STOPS[0])
    assert w.host.prs == {}
    sb = side(w)
    assert w.fleet.branch_for(PHASE, "")[0] == BRANCH, "the side branch counted as the phase's"
    assert sb.startswith(f"phase-{PHASE}-stopped-")


# ------------------------------------------------------- the gate's side mode
def _clone_with_commit(w, path: str, text: str) -> tuple[pathlib.Path, str]:
    c = w.tmp / f"gate-{len(list(w.tmp.iterdir()))}"
    git("clone", "-q", "--branch", "master", str(w.origin), str(c), cwd=w.tmp)
    base = out("rev-parse", "HEAD", cwd=c)
    (c / path).parent.mkdir(parents=True, exist_ok=True)
    (c / path).write_text(text)
    git("add", "-A", cwd=c)
    git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qm", "x", cwd=c)
    return c, base


def _never(commit):
    raise AssertionError("the side mode asked for a model-free run")


def test_the_side_mode_skips_only_the_model_free_run(w):
    c, base = _clone_with_commit(w, "docs/kept.md", "kept\n")
    ok = fleet_git.gate(c, rank="engineer", phase=PHASE, branch=f"phase-{PHASE}-stopped-r1",
                        base=base, tested=_never, mobile=None, side=True)
    assert ok == []
    named = fleet_git.gate(c, rank="engineer", phase=PHASE, branch=BRANCH, base=base,
                           tested=lambda h: (True, ""), mobile=None, side=True)
    assert any(f.startswith("G1 ") for f in named), "the side mode pushed to the phase branch"
    plain = fleet_git.gate(c, rank="engineer", phase=PHASE, branch=f"phase-{PHASE}-stopped-r1",
                           base=base, tested=lambda h: (False, "red"), mobile=None)
    assert any(f.startswith("G6 ") for f in plain), "G6 skipped outside the side mode"


@pytest.mark.parametrize("path, text, check", [
    (".claude/skills/fleet/dispatcher.py", "x = 1\n", "G3 "),
    ("docs/token.md", "sk-ant-oat01-" + "A" * 80 + "\n", "G4 "),
])
def test_the_side_mode_keeps_the_gates_other_checks(w, path, text, check):
    c, base = _clone_with_commit(w, path, text)
    fails = fleet_git.gate(c, rank="engineer", phase=PHASE, branch=f"phase-{PHASE}-stopped-r1",
                           base=base, tested=_never, mobile=None, side=True)
    assert any(f.startswith(check) for f in fails), fails


def test_the_side_mode_still_asks_for_a_fast_forward(w):
    c, _ = _clone_with_commit(w, "docs/kept.md", "kept\n")
    beside, _ = _clone_with_commit(w, "docs/beside.md", "beside\n")
    other = out("rev-parse", "HEAD", cwd=beside)
    subprocess.run(["git", "-C", str(c), "fetch", "-q", str(beside), "HEAD"], check=True)
    fails = fleet_git.gate(c, rank="engineer", phase=PHASE, branch=f"phase-{PHASE}-stopped-r1",
                           base=other, tested=_never, mobile=None, side=True)
    assert fails and fails[0].startswith("G2 ")
