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
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    stat = pathlib.Path(f"/proc/{pid}/stat")
    return stat.exists() and stat.read_text().rsplit(")", 1)[1].split()[0] != "Z"


def test_run_group_kills_the_whole_group_and_says_what_it_printed(tmp_path):
    fence, pidfile = planted(tmp_path)
    t = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired) as e:
        D.run_group([str(fence), "--run", str(tmp_path / "r")], timeout=1, text=True)
    assert time.monotonic() - t < 30
    assert "started" in e.value.stdout
    pid = int(pidfile.read_text())
    for _ in range(50):
        if not alive(pid):
            break
        time.sleep(0.1)
    assert not alive(pid), "the planted command's child outlived the kill"


def test_run_group_passes_a_run_that_ends(tmp_path):
    r = D.run_group(["/bin/sh", "-c", "echo hi; echo err >&2; exit 3"], timeout=10, text=True)
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
