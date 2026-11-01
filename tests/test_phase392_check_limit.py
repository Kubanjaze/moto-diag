"""Phase 392 — F225: a model-free run past its time limit stops its stage
the usual way.

Before, `check_run` let `subprocess.TimeoutExpired` out of the stage: the
cycle ended the journal "failed" and the next cycle began the same stage
again from nothing, saying nothing on the issue (#28, 2026-10-26). Now the
run's whole process group is killed and a failed `Check` names the limit;
the Engineer's stage stops once, said on the issue, its run held, and the
next cycle does not start it again. The limit is the operator's (K51):
5400 s. The known-bad case is a planted command that outlives the limit.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import time

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "fleet"))
sys.path.insert(0, str(ROOT / "tests"))
import dispatcher as D  # noqa: E402
import journal as J  # noqa: E402
from test_phase389_dispatcher import go_to_approved, labels, step, world  # noqa: E402,F401


def test_the_limit_is_the_operators():
    assert D.CHECK_TIMEOUT_S == 5400


def planted(tmp_path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    """A fence that outlives any limit, and leaves a grandchild behind."""
    pidfile = tmp_path / "child.pid"
    f = tmp_path / "fence.sh"
    f.write_text("#!/bin/bash\nwhile [ \"$1\" != --run ]; do shift; done\n"
                 f"mkdir -p \"$2/tmp/pytest-of-fleet\"\necho started\n"
                 f"sleep 300 & echo $! > {pidfile}\nwait\n")
    f.chmod(0o755)
    return f, pidfile


def alive(pid: int) -> bool:
    """Whether `pid` has not ended; a zombie has ended and waits only to be
    reaped. `ps` answers on Linux and on macOS, which has no /proc: there
    the old answer, read from /proc, was "ended" for every pid (F241)."""
    r = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True)
    state = r.stdout.strip()
    if (r.returncode, bool(state)) not in ((0, True), (1, False)):
        raise AssertionError(f"ps gave no answer for pid {pid}: exit {r.returncode}, "
                             f"{r.stdout!r} {r.stderr!r}")
    return bool(state) and not state.startswith("Z")


def test_alive_answers_on_this_system():
    assert alive(os.getpid())
    child = subprocess.Popen(["/bin/sh", "-c", "exit 0"])
    for _ in range(100):                 # exited and not reaped: a zombie
        r = subprocess.run(["ps", "-o", "stat=", "-p", str(child.pid)],
                           capture_output=True, text=True)
        if r.stdout.strip().startswith("Z"):
            break
        time.sleep(0.05)
    else:
        pytest.fail(f"the child never showed as a zombie: {r.stdout!r}")
    assert not alive(child.pid)
    child.wait()
    assert not alive(child.pid)


#: The planted command's windows, each double the last (F241). The first is
#: the old one second, which a busy Mac's full run could not start a shell
#: in; the test takes the first window in which the command reached its child.
WINDOWS = (1, 2, 4, 8, 16, 32)


def test_run_group_kills_the_whole_group_and_says_what_it_printed(tmp_path):
    for window in WINDOWS:
        here = tmp_path / f"window{window}"
        here.mkdir()
        fence, pidfile = planted(here)
        t = time.monotonic()
        with pytest.raises(subprocess.TimeoutExpired) as e:
            D.run_group([str(fence), "--run", str(here / "r")], timeout=window, text=True)
        assert time.monotonic() - t < window + 29
        if pidfile.is_file() and pidfile.read_text().endswith("\n"):
            break
    else:
        pytest.fail(f"in windows of {WINDOWS} s the planted command never reached its child")
    # The pid file is written after `echo started`: it was printed, so it is kept.
    assert "started" in e.value.stdout
    pid = int(pidfile.read_text())
    for _ in range(50):
        if not alive(pid):
            break
        time.sleep(0.1)
    assert not alive(pid), "the planted command's child outlived the kill"


def test_run_group_passes_a_run_that_ends(tmp_path):
    r = D.run_group(["/bin/sh", "-c", "echo hi; echo err >&2; exit 3"], timeout=120, text=True)
    assert (r.returncode, r.stdout, r.stderr) == (3, "hi\n", "err\n")


def test_the_engineers_over_limit_run_stops_once_and_is_not_started_again(world, monkeypatch):
    """The known-bad case through a stage: before this phase the
    TimeoutExpired left `engineer_finish` and the cycle (F225)."""
    fleet, host, clock, origin, engineer, checks, lines = world
    fence, _ = planted(pathlib.Path(fleet.state_dir).parent)
    monkeypatch.setattr(D, "CHECK_TIMEOUT_S", 1)
    go_to_approved(world)
    fleet.fence = fence                  # the model calls before it are the stand-in's
    fleet.check = fleet.check_run        # the real model-free run, past its limit
    step(clock, fleet, host)
    assert "needs-admiral" in labels(host)
    said = host.comments(31)[-1]
    assert "passed its time limit of 1 s" in said and "take `needs-admiral` off" in said
    (run,) = [p for p in fleet.runs.iterdir() if p.name.endswith("_engineer_902")]
    j = J.Journal.load(run)
    assert j.data["outcome"] == "checks failed" and J.held(run) is not None
    check = next(p for p in fleet.runs.iterdir() if p.name.endswith("_check"))
    assert "time limit" in (check / "run" / "check.txt").read_text()
    n, runs = len(host.comments(31)), engineer.runs
    step(clock, fleet, host)
    assert len(host.comments(31)) == n and engineer.runs == runs, "it started again"
    assert not any("cycle failed" in ln for ln in lines)
