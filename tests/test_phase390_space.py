"""Phase 390 — free space is part of the method, phase to phase (F221).

The operator, 2026-10-25: "it's just something that needs to be done
frequently to free up the claimed space, now it just needs to be written
into the method itself. as a part of the overall process phase to phase".
What must hold:
- the dispatcher reclaims (`fstrim`, through its one sudoers line) on a
  timer, at each merge and at each close-out, and logs the free space on C:
  and in Ubuntu before and after;
- no new model stage or model-free run starts below a floor on either disk:
  it reclaims first, and if still below, it holds the label, comments why
  and adds `needs-hands`; the operator taking `needs-hands` off lets the
  stage it held run (the Engineer's model-free run on the same commit);
- the service is given both disks and the command; nothing else is.

The disks are a stand-in reading (`Disk`), planted low where a test says;
`fstrim` is answered by the stand-in, never run. The rest is the 390 resume
tests' world: real git, `gh` and the fence stood in.
"""
from __future__ import annotations

import datetime as dt
import pathlib
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))

from test_phase388_dispatcher import iso  # noqa: E402
from test_phase389_dispatcher import BRANCH, PHASE  # noqa: E402
from test_phase389_fleet_git import git  # noqa: E402
from test_phase390_resume import (BACK, DIGEST, N, D, J, World, advance, calls,  # noqa: E402,F401
                                  labels, ledger, said, to_approved, to_pr, w)

TRIMMED = "/: 12 GiB (12884901888 bytes) trimmed\n"


class Disk:
    """Free space in GB by disk name; `when` drops C: to a reading once its
    predicate first holds (mid-stage), `trim_frees` is what fstrim gives back."""

    def __init__(self):
        self.free = {"C:": 200.0, "Ubuntu": 900.0}
        self.unreadable: set[str] = set()
        self.when = None
        self.trim_frees, self.trim_rc, self.trims = 0.0, 0, 0

    def __call__(self, path: pathlib.Path):
        if self.when and self.when[0]():
            self.free["C:"], self.when = self.when[1], None
        if path.name in self.unreadable:
            raise OSError(f"no disk at {path}")
        return (0, 0, int(self.free[path.name] * 1e9))

    def trim(self) -> subprocess.CompletedProcess:
        self.trims += 1
        self.free["C:"] += self.trim_frees
        return subprocess.CompletedProcess(D.FSTRIM, self.trim_rc, TRIMMED, "")


@pytest.fixture
def s(w, monkeypatch) -> World:
    """The world with both disks watched, as `main` sets the service up."""
    disk = Disk()
    plain = World.make

    def make(self):
        f = plain(self)
        f.disks = {name: self.tmp / name for name in ("C:", "Ubuntu")}
        f.trim, f.disk_usage = list(D.FSTRIM), disk
        inner = f.host
        f.host = lambda cmd, **kw: disk.trim() if list(cmd) == D.FSTRIM else inner(cmd, **kw)
        return f

    monkeypatch.setattr(World, "make", make)
    w.disk = disk
    w.make()
    state = w.fleet.load()
    state["last_reclaim"] = iso(w.clock())          # the timer not due: each test sets its own
    w.fleet.save(state)
    return w


def low(w: World, gb: float = 10.0) -> None:
    w.disk.free["C:"] = gb


def logged(w: World, text: str) -> bool:
    return any(text in ln for ln in w.lines)


def holds(w: World) -> list[str]:
    return [b for b in w.host.comments(N) if b.lstrip().startswith(D.SPACE_M)]


# ------------------------------------------------------------- a new stage
def test_a_planted_low_reading_stops_a_new_stage(s):
    to_approved(s)
    low(s)
    advance(s)
    assert s.sessions == [], "the Engineer started below the floor"
    assert labels(s) == ["mission", "needs-hands", "plan:approved"], "the label moved"
    (hold,) = holds(s)
    assert "C: has 10.0 GB free (floor 50 GB)" in hold and "take `needs-hands` off" in hold
    assert s.disk.trims == 1, "no reclaim before the hold"
    assert logged(s, "reclaim (below the floor): C: 10.0 -> 10.0 GB free; Ubuntu 900.0 -> 900.0")
    n = len(s.host.comments(N))
    advance(s)                                           # the operator has not answered
    assert len(s.host.comments(N)) == n and s.sessions == []


def test_taking_needs_hands_off_starts_the_stage_it_held(s):
    to_approved(s)
    low(s)
    advance(s)
    low(s, 200.0)
    s.host.issues[N]["labels"].remove("needs-hands")     # the operator's hand
    advance(s)
    assert len(s.sessions) == 1 and labels(s) == ["mission", "review:open"]


def test_a_reclaim_that_frees_enough_lets_the_stage_start(s):
    to_approved(s)
    low(s)
    s.disk.trim_frees = 100.0
    advance(s)
    assert sum("reclaim (below the floor)" in ln for ln in s.lines) == 1
    assert len(s.sessions) == 1 and "needs-hands" not in labels(s)
    assert holds(s) == []


def test_ubuntu_below_its_floor_holds_too(s):
    to_approved(s)
    s.disk.free["Ubuntu"] = 20.0
    advance(s)
    assert s.sessions == [] and "Ubuntu has 20.0 GB free (floor 50 GB)" in holds(s)[0]


def test_a_disk_that_cannot_be_read_holds_the_stage(s):
    to_approved(s)
    s.disk.unreadable.add("Ubuntu")
    advance(s)
    assert s.sessions == [] and "needs-hands" in labels(s)
    assert "Ubuntu cannot be read" in holds(s)[0]


def test_a_failed_trim_is_said_and_the_stage_still_held(s):
    s.disk.trim_rc = 1
    to_approved(s)
    low(s)
    advance(s)
    assert logged(s, "fstrim: failed (exit 1)") and "needs-hands" in labels(s)


# ------------------------------------------------ a model-free run mid-stage
def engineer_held(s):
    to_approved(s)
    s.disk.when = (lambda: len(s.sessions) == 1, 10.0)
    advance(s)
    (held,) = J.held_runs(s.fleet.runs, N)
    return held


def test_below_the_floor_before_the_engineers_model_free_run_holds_the_run(s):
    held = engineer_held(s)
    assert len(s.sessions) == 1 and not [c for c in s.checks if c[1]], "the full run started"
    assert J.held(held)["why"] == "space"
    assert labels(s) == ["build:open", "mission", "needs-hands"] and BRANCH not in s.host.prs
    commit = J.held(held)["commit"]
    low(s, 200.0)
    s.host.issues[N]["labels"].remove("needs-hands")
    advance(s)
    assert [c[:2] for c in s.checks if c[1]] == [(commit, True)], "not the same commit"
    assert len(s.sessions) == 1, "the Engineer ran again"
    assert labels(s) == ["mission", "review:open"] and J.held_runs(s.fleet.runs, N) == []


def test_a_recheck_below_the_floor_again_keeps_its_run_held(s):
    held = engineer_held(s)
    low(s, 200.0)
    s.host.issues[N]["labels"].remove("needs-hands")
    s.disk.when = (lambda: any(s.fleet.runs.glob("*_recheck_*")), 10.0)
    advance(s)
    assert J.held_runs(s.fleet.runs, N) == [held] and J.held(held)["why"] == "space"
    assert "needs-hands" in labels(s) and BRANCH not in s.host.prs


def test_a_space_hold_answered_some_other_way_is_not_due(s):
    """A recheck that stopped (or a hand) has spoken since the hold: the
    held run does not run again every cycle."""
    held = engineer_held(s)
    s.host.issues[N]["labels"].remove("needs-hands")
    s.clock.t += dt.timedelta(minutes=1)
    s.host.issues[N]["comments"].append({"body": f"{D.MARKER} stopped rank=engineer -->\nx",
                                         "createdAt": iso(s.clock())})
    assert s.fleet.held_for(N) is None and J.held(held) is not None


def test_the_red_teams_f9_run_below_the_floor_is_held_then_due_again(s):
    to_pr(s)
    s.disk.when = (lambda: any(s.fleet.runs.glob("*_red_team_*")), 10.0)
    advance(s)
    assert labels(s) == ["mission", "needs-hands", "review:open"] and said(s, D.RED_M) == 0
    assert "no model-free run" in holds(s)[-1]
    low(s, 200.0)
    s.host.issues[N]["labels"].remove("needs-hands")
    advance(s, BACK)
    assert labels(s) == ["build:open", "mission"] and said(s, D.RED_M) == 1


def test_the_digest_below_the_floor_waits_for_space(s):
    s.host.issues.clear()
    s.fleet.save({**s.fleet.load(), "last_digest": "2026-10-20"})
    low(s)
    advance(s)
    assert s.fleet.load()["last_digest"] == "2026-10-20" and calls(s) == []
    assert logged(s, "digest: held, no new stage: free space is below the floor")
    low(s, 200.0)
    advance(s, DIGEST)
    assert s.fleet.load()["last_digest"] == "2026-10-21"


# ------------------------------------------------------- phase to phase
def test_reclaim_on_the_timer(s):
    s.host.issues.clear()
    state = s.fleet.load()
    state.pop("last_reclaim")
    s.fleet.save(state)
    advance(s)
    assert s.disk.trims == 1 and logged(s, "reclaim (the 3-hour timer): C: 200.0 -> 200.0 GB free")
    advance(s)
    assert s.disk.trims == 1, "the timer ran again after five minutes"
    s.clock.t += dt.timedelta(hours=D.RECLAIM_HOURS)
    advance(s)
    assert s.disk.trims == 2


def test_reclaim_at_a_merge(s):
    s.host.issues.clear()
    advance(s)
    assert PHASE in s.fleet.load()["active"]
    road = s.origin / "docs" / "ROADMAP.md"
    text = road.read_text()
    road.write_text(text.replace(f"| {PHASE} | The trial | 🚧 |", f"| {PHASE} | The trial | ✅ |"))
    git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qam", "merged", cwd=s.origin)
    advance(s)
    assert logged(s, f"reclaim (phase {PHASE} merged)") and s.disk.trims == 1
    assert PHASE not in s.fleet.load()["active"]
    advance(s)
    assert s.disk.trims == 1, "one merge, reclaimed twice"


def test_the_close_out_reclaims_and_the_pr_carries_the_line(s):
    to_pr(s)
    body = s.host.prs[BRANCH]["body"]
    assert "Free space after the close-out's reclaim:" in body
    assert "C: 200.0 -> 200.0 GB free; Ubuntu 900.0 -> 900.0 GB free; fstrim: /: 12 GiB" in body
    assert logged(s, f"reclaim (phase {PHASE}'s close-out)")


def test_without_disks_nothing_is_read_or_trimmed(w):
    """The control: a Fleet `main` did not set up (every older test's) reads
    no disk and runs no fstrim, and its stages run as before."""
    def boom(path):
        raise AssertionError(f"read {path}")
    w.fleet.disk_usage = boom
    to_pr(w)
    assert labels(w) == ["mission", "review:open"]
    assert "Free space after" not in w.host.prs[BRANCH]["body"]
    assert not any("reclaim (" in ln for ln in w.lines)


# ------------------------------------------------------------- the wiring
def test_the_service_watches_both_disks_and_trims(tmp_path, monkeypatch):
    seen = []

    class Stub:
        def __init__(self, **kw):
            seen.append(kw)

        def recover(self, **kw):
            return []

        def cycle(self):
            pass

        def reclaim(self, why, **kw):
            seen.append(("reclaim", why, kw))
            return "C: 1.0 -> 2.0 GB free; fstrim: ok"

    monkeypatch.setattr(D, "Fleet", Stub)
    monkeypatch.setattr(D, "STATE", tmp_path)
    monkeypatch.setattr(D, "load_token", lambda path: "sk-ant-oat01-test-token")
    assert D.main(["once"]) == 0
    assert seen[0]["disks"] == D.DISKS and seen[0]["trim"] == D.FSTRIM
    assert D.main(["reclaim"]) == 0
    assert seen[1]["disks"] == D.DISKS and seen[1]["trim"] == D.FSTRIM
    assert seen[2] == ("reclaim", "by hand", {"record": False}), "the CLI wrote the state"


def test_the_disks_are_c_through_wsl_and_ubuntus_root():
    assert D.DISKS == {"C:": pathlib.Path("/mnt/c"), "Ubuntu": pathlib.Path("/")}
    assert set(D.SPACE_FLOOR_GB) == set(D.DISKS)


def test_the_sudoers_rule_allows_exactly_the_one_command():
    text = (ROOT / "ops" / "desktop" / "install_fstrim_sudoers.sh").read_text()
    rules = [ln for ln in text.splitlines() if "NOPASSWD" in ln]
    assert rules == ["lilcu ALL=(root) NOPASSWD: " + " ".join(D.FSTRIM[2:])]
    assert D.FSTRIM[:2] == ["sudo", "-n"], "sudo would wait for a password"


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is the desktop's")
def test_a_model_in_the_fence_cannot_use_sudo():
    """bubblewrap sets no_new_privs, so the one sudoers line is the
    dispatcher's, never a model's."""
    r = subprocess.run(["bwrap", "--dev-bind", "/", "/", "grep", "NoNewPrivs", "/proc/self/status"],
                       capture_output=True, text=True)
    assert r.stdout.split() == ["NoNewPrivs:", "1"]


def test_the_handoff_step_names_the_reclaim_line():
    skill = (ROOT / ".claude" / "skills" / "closeout" / "SKILL.md").read_text()
    step = skill[skill.index("9. **Handoff**"):skill.index("10. **Merge.**")]
    assert "dispatcher.py reclaim" in step and "free space" in step
