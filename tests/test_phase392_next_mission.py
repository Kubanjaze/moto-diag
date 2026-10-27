"""Phase 392 — the next mission comes from the plan.

The operator's K48 (the "Next, in order" list, read exactly) and K49 ("The
fleet opens a one-row PR (the 🚧 row and the issue) and I merge it by
hand; the fleet never pushes to master"). On 389's walk-through, with the
fleet's own account: the plan's next phase gets its issue and a one-row
pull request once; merging it starts the Science Officer; an entry that
needs the operator is asked once, in plain English, and waits for the
label; a builder's phase is waited for; a list that does not read exactly
starts nothing. The `row` rank's push gate allows the phase's status and
nothing else. A `next` stage killed after its issue resumes on restart.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "fleet"))
sys.path.insert(0, str(ROOT / "tests"))
import dispatcher as D  # noqa: E402
import fleet_git  # noqa: E402
import journal as J  # noqa: E402
import plan_order  # noqa: E402
import rank_call  # noqa: E402
from test_phase388_dispatcher import claude_json  # noqa: E402
from test_phase389_dispatcher import ASSESS, TERMS, GitHub, step, world  # noqa: E402,F401
from test_phase389_fleet_git import git  # noqa: E402

FLEET = "kubanjazefleet"
TOKEN = "ghp_" + "b" * 36
TITLE = "Phase 901: The shop's first screen"
WORK = "phase-901-the-shop-s-first-screen"

PLAN = """# Fixture plan of record

## Next, in order

As of 2026-10-05, K91.

| # | phase | kind | built by | needs the operator | entry |
|---|---|---|---|---|---|
| 1 | 901 | shop | fleet | {need} | Wave 1, item 1 · K91 |

## Changes to the order

- **2026-10-05: the shop's first screen goes first.** The operator's decision is K91, for 901.

## Wave 1: the first shop

1. **901, the shop's first screen.**
"""


class Hub(GitHub):
    """389's stand-in, which can also open an issue: in the fleet's name."""

    def gh(self, cmd):
        if cmd[1:3] == ["issue", "create"]:
            n = max([*self.issues, 40]) + 1
            self.issue(n, cmd[cmd.index("--title") + 1], cmd[cmd.index("--body") + 1],
                       {cmd[cmd.index("--label") + 1]: self.clock()})
            self.issues[n]["author"] = FLEET
            return subprocess.CompletedProcess(cmd, 0, f"https://github.com/{D.REPO}/issues/{n}\n",
                                               "")
        if cmd[1:3] == ["pr", "view"] and "comments" in cmd:
            return subprocess.CompletedProcess(cmd, 0, json.dumps({"comments": []}), "")
        return super().gh(cmd)


@pytest.fixture
def next_world(world, tmp_path):
    fleet, host, clock, origin, *_ = world
    host.__class__ = Hub
    host.commenter = FLEET
    ident = tmp_path / "fleet-github.env"
    ident.write_text(f"FLEET_GITHUB_USER={FLEET}\nFLEET_GITHUB_TOKEN={TOKEN}\n")
    ident.chmod(0o600)
    fleet.identity_file = ident
    set_plan(origin, "nothing")
    return world


def set_plan(origin: pathlib.Path, need: str) -> None:
    (origin / plan_order.PLAN).write_text(PLAN.replace("{need}", need))
    git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qam", "the plan", cwd=origin)


def the_issue(host) -> tuple[int, dict]:
    (n, i), = [(n, i) for n, i in host.issues.items() if i["title"] == TITLE]
    return n, i


def merge_row(origin: pathlib.Path) -> None:
    """The operator's one click: the row's PR merged into master."""
    git("-c", "user.name=t", "-c", "user.email=t@l", "merge", "-q", "--no-ff", "-m", "merge",
        D.row_branch("901"), cwd=origin)


class TestTheNextMission:
    def test_its_issue_and_one_row_pr_then_the_merge_starts_step_0(self, next_world):
        fleet, host, clock, origin, *_ = next_world
        step(clock, fleet, host)
        n, issue = the_issue(host)
        assert issue["labels"] == ["mission"] and issue["author"] == FLEET
        assert f"`{WORK}`" in issue["body"] and "'Next, in order' #1" in issue["body"]
        assert "K91" in issue["body"]
        pr = host.prs[D.row_branch("901")]
        assert "Merging this starts Phase 901" in pr["body"]
        assert "echo ALL GOOD || echo SOMETHING IS OFF" in pr["body"]
        assert f"-R {D.REPO}" in pr["body"]
        diff = git_out(origin, "diff", "master", D.row_branch("901"))
        assert [ln for ln in diff.splitlines() if ln[:1] in "+-" and ln[:3] not in ("+++", "---")
                ] == ["-| 901 | The shop's first screen | 🔲 | The first-shop phase 900 unblocks. |",
                      "+| 901 | The shop's first screen | 🚧 | The first-shop phase 900 unblocks. |"]
        assert host.comments(n)[-1].startswith(f"{D.NEXT_M} row-pr")
        step(clock, fleet, host)                                     # nothing new to do
        assert len(host.prs) == 1 and len([i for i in host.issues.values()
                                           if i["title"] == TITLE]) == 1
        merge_row(origin)
        step(clock, fleet, host, claude_json(TERMS, model=rank_call.HAIKU),
             claude_json(ASSESS, model=rank_call.HAIKU))            # the Science Officer
        assert "step0:done" in host.issues[n]["labels"]
        assert on(origin, f"refs/heads/{WORK}")

    def test_master_is_never_pushed_by_it(self, next_world):
        fleet, host, clock, origin, *_ = next_world
        before = git_out(origin, "rev-parse", "master")
        step(clock, fleet, host)
        assert git_out(origin, "rev-parse", "master") == before

    def test_an_entry_that_needs_the_operator_is_asked_once_and_waits(self, next_world):
        fleet, host, clock, origin, *_ = next_world
        set_plan(origin, "an outside account: the shop's payments account, which the operator "
                         "opens")
        step(clock, fleet, host)
        n, issue = the_issue(host)
        assert "needs-hands" in issue["labels"] and not host.prs
        asked = host.comments(n)[-1]
        assert asked.startswith(f"{D.NEXT_M} asked need=needs-hands")
        assert "the shop's payments account, which the operator opens" in asked
        assert "take the `needs-hands` label off" in asked
        step(clock, fleet, host)
        assert not host.prs and len(host.comments(n)) == 1           # the ask, once
        issue["labels"].remove("needs-hands")                        # the operator has done it
        step(clock, fleet, host)
        assert D.row_branch("901") in host.prs
        assert sum(c.startswith(f"{D.NEXT_M} asked") for c in host.comments(n)) == 1

    def test_a_fork_is_asked_with_needs_admiral(self, next_world):
        fleet, host, clock, origin, *_ = next_world
        set_plan(origin, "a fork: two ways to reach the payments service")
        step(clock, fleet, host)
        _, issue = the_issue(host)
        assert "needs-admiral" in issue["labels"]

    def test_a_builders_phase_is_waited_for(self, next_world):
        fleet, host, clock, origin, engineer, checks, lines = next_world
        (origin / plan_order.PLAN).write_text(PLAN.replace("{need}", "nothing")
                                              .replace("| shop | fleet |", "| shop | builder |"))
        git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qam", "builder", cwd=origin)
        step(clock, fleet, host)
        step(clock, fleet, host)
        assert not [i for i in host.issues.values() if i["title"] == TITLE] and not host.prs
        assert sum("phase 901 is a builder's" in ln for ln in lines) == 1

    def test_a_list_that_does_not_read_exactly_starts_nothing(self, next_world):
        fleet, host, clock, origin, engineer, checks, lines = next_world
        set_plan(origin, "a favour")
        step(clock, fleet, host)
        assert not [i for i in host.issues.values() if i["title"] == TITLE]
        assert any("cannot be read exactly on master" in ln for ln in lines)

    def test_without_the_fleets_account_nothing_is_opened(self, next_world, tmp_path):
        fleet, host, clock, *_ = next_world
        fleet.identity_file = tmp_path / "none.env"
        step(clock, fleet, host)
        assert not [i for i in host.issues.values() if i["title"] == TITLE]


class Killed(BaseException):
    """A kill: nothing in the stage catches it, so its journal stays open."""


def test_next_cut_after_its_issue_resumes_with_no_second_issue(next_world):
    """The kill point (`fixtures/resume/kill_points.json`): cut after the
    issue, before the row's pull request; the search on start resumes it."""
    fleet, host, clock, origin, *_ = next_world
    real = fleet.stage_clone

    def killed(*a, **k):
        raise Killed
    fleet.stage_clone = killed
    clock.t += D.dt.timedelta(minutes=5)
    with pytest.raises(Killed):
        fleet.cycle()
    assert len([i for i in host.issues.values() if i["title"] == TITLE]) == 1
    (j,) = J.unfinished(fleet.runs)
    assert j.record["stage"] == "next" and j.done("issue")
    fleet.stage_clone = real
    fleet.recover()
    assert len([i for i in host.issues.values() if i["title"] == TITLE]) == 1
    assert D.row_branch("901") in host.prs and not J.unfinished(fleet.runs)


class TestTheRowRanksGate:
    @pytest.fixture
    def repo(self, tmp_path):
        r = tmp_path / "r"
        r.mkdir()
        git("init", "-q", "-b", "master", cwd=r)
        (r / "docs").mkdir()
        (r / "docs" / "ROADMAP.md").write_text("| 900 | a | 🚧 | x |\n| 901 | b | 🔲 | y |\n")
        (r / "other.md").write_text("x\n")
        git("add", "-A", cwd=r)
        git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qm", "a", cwd=r)
        return r

    def gate(self, repo, edit):
        base = git_out(repo, "rev-parse", "HEAD")
        edit(repo)
        git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qam", "b", cwd=repo)
        return [f for f in fleet_git.gate(repo, rank="row", phase="901", branch="phase-901-row",
                                          base=base, tested=lambda c: (True, ""), mobile=None)
                if f.startswith("G3")]

    def test_its_own_status_passes(self, repo):
        assert self.gate(repo, lambda r: D.mark_row_active(r, "901")) == []

    def test_another_phases_row_is_refused(self, repo):
        fails = self.gate(repo, lambda r: (r / "docs" / "ROADMAP.md").write_text(
            "| 900 | a | ✅ | x |\n| 901 | b | 🔲 | y |\n"))
        assert fails == ["G3 the row may change only phase 901's row, not '| 900 | a | 🚧 | x |'"]

    def test_more_than_the_status_is_refused(self, repo):
        fails = self.gate(repo, lambda r: (r / "docs" / "ROADMAP.md").write_text(
            "| 900 | a | 🚧 | x |\n| 901 | b | 🚧 | y, and more |\n"))
        assert fails == ["G3 the row may change only phase 901's status, to 🚧"]

    def test_a_second_file_is_refused(self, repo):
        def edit(r):
            D.mark_row_active(r, "901")
            (r / "other.md").write_text("changed\n")
        assert self.gate(repo, edit) == ["G3 the row may not change other.md"]


def git_out(repo: pathlib.Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          check=True).stdout.strip()


def on(repo: pathlib.Path, ref: str) -> bool:
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "-q", ref],
                          capture_output=True).returncode == 0
