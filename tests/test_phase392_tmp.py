"""Phase 392 — F226: a finished stage's temporary files are deleted.

The operator's K45: "go with your pick, delete each run's temp files". The
disk image is not sparse since 2026-10-26, so a trim gives Windows nothing;
pytest's temporary folders (about 9 GB a full run, measured in 392's Step
0) are what fills it. What must hold: a run's `run/tmp` goes when its stage
ends; a held, a paused and an unfinished run keep theirs until they end;
`tests/support/worker_loss.py`'s folders survive every deletion; a check
run's go when it has written its result; the reclaim line says when nothing
came back to Windows.
"""
from __future__ import annotations

import datetime as dt
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "fleet"))
sys.path.insert(0, str(ROOT / "tests"))
import dispatcher as D  # noqa: E402
import journal as J  # noqa: E402
from test_phase389_fleet_git import git  # noqa: E402

T0 = dt.datetime(2026, 10, 27, 12, 0).astimezone()
LOSS = "motodiag_worker_loss_x1y2"


def litter(run: pathlib.Path) -> None:
    """What a fenced run leaves: pytest's folders, a stray file, the worker-loss folder."""
    tmp = run / "run" / "tmp"
    (tmp / "pytest-of-fleet" / "pytest-0" / "t0").mkdir(parents=True)
    (tmp / "pytest-of-fleet" / "pytest-0" / "t0" / "big.db").write_bytes(b"x" * 4096)
    (tmp / "stray.txt").write_text("x")
    (tmp / LOSS).mkdir()
    (tmp / LOSS / "gw0.last").write_text("pid 7\nstarted tests/test_x.py::t\n")


def left(run: pathlib.Path) -> list[str]:
    tmp = run / "run" / "tmp"
    return sorted(p.name for p in tmp.iterdir()) if tmp.is_dir() else []


@pytest.fixture
def fleet(tmp_path):
    return D.Fleet(state=tmp_path / "state", token="", now=lambda: T0, out=lambda s: None,
                   identity_file=tmp_path / "none.env", venv=tmp_path / "nv",
                   mobile=tmp_path / "nm")


def stage(fleet, name: str) -> J.Journal:
    run = fleet.new_run(name, {"stage": "xo", "issue": 1, "phase": "900"})
    litter(run)
    return J.Journal.load(run)


class TestTheDeletion:
    def test_clean_tmp_keeps_only_the_worker_loss_folders(self, tmp_path):
        run = tmp_path / "r"
        litter(run)
        assert D.clean_tmp(run) == [LOSS]
        assert left(run) == [LOSS]
        assert (run / "run" / "tmp" / LOSS / "gw0.last").read_text().startswith("pid 7")

    def test_a_run_with_no_tmp_is_nothing_to_do(self, tmp_path):
        assert D.clean_tmp(tmp_path / "none") == []

    def test_a_stage_that_ends_loses_its_tmp(self, fleet):
        j = stage(fleet, "xo_900")
        fleet.journal = j
        fleet.finish("verdict applied")
        assert left(j.run) == [LOSS]


class TestWhatKeepsItsFiles:
    """The known-bad cases: each run that must keep its files, kept."""

    def test_a_paused_stage_keeps_its_tmp(self, fleet):
        j = stage(fleet, "xo_900")
        fleet.journal = j
        fleet.finish("rate-limited")
        assert "pytest-of-fleet" in left(j.run) and J.Journal.load(j.run).unfinished

    def test_a_held_stage_keeps_its_tmp_until_released(self, fleet):
        j = stage(fleet, "engineer_900")
        J.hold(j.run, {"issue": 1, "phase": "900", "rnd": 0, "commit": "c"})
        fleet.journal = j
        fleet.finish("checks failed")
        assert "pytest-of-fleet" in left(j.run)
        fleet.prune_runs(set())
        assert "pytest-of-fleet" in left(j.run), "prune cleaned a held run"

    def test_an_unfinished_stage_keeps_its_tmp_through_prune(self, fleet):
        j = stage(fleet, "captain_900")                        # never ended: a restart cut it
        fleet.prune_runs(set())
        assert "pytest-of-fleet" in left(j.run)

    def test_the_paused_run_prune_is_told_to_keep_keeps_its_tmp(self, fleet):
        j = stage(fleet, "xo_900")
        j.end("rate-limited", T0)                              # as a stale record might say
        fleet.prune_runs({str(j.run)})
        assert "pytest-of-fleet" in left(j.run)


class TestPrune:
    def test_an_ended_run_and_a_finished_check_run_are_cleaned(self, fleet):
        j = stage(fleet, "xo_900")
        j.end("verdict applied", T0)
        check = fleet.new_run("check")
        litter(check)
        (check / "run" / "check.txt").write_text("PASSED")
        cut = fleet.new_run("check")                          # a check a restart cut off
        litter(cut)
        fleet.prune_runs(set())
        assert left(j.run) == [LOSS] and left(check) == [LOSS]
        assert "pytest-of-fleet" in left(cut)


class TestTheCheckRun:
    @pytest.fixture
    def repo(self, tmp_path):
        r = tmp_path / "repo"
        r.mkdir()
        git("init", "-q", "-b", "master", cwd=r)
        (r / "a").write_text("a")
        git("add", "-A", cwd=r)
        git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qm", "a", cwd=r)
        return r

    def fake_fence(self, tmp_path, body: str) -> pathlib.Path:
        f = tmp_path / "fence.sh"
        f.write_text("#!/bin/bash\nwhile [ \"$1\" != --run ]; do shift; done; RUN=$2\n"
                     f"mkdir -p \"$RUN/tmp/pytest-of-fleet\" \"$RUN/tmp/{LOSS}\"\n{body}\n")
        f.chmod(0o755)
        return f

    def test_a_check_run_cleans_its_tmp_after_writing_its_result(self, fleet, tmp_path, repo):
        fleet.fence = self.fake_fence(tmp_path, "echo all fine")
        head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True,
                              text=True).stdout.strip()
        c = fleet.check_run(repo, head, full=False)
        run = next(p for p in fleet.runs.iterdir() if p.name.endswith("_check"))
        assert c.ok and (run / "run" / "check.txt").read_text().strip() == "all fine"
        assert left(run) == [LOSS]


class TestTheReclaimLine:
    @pytest.mark.parametrize("before,after,trimmed,said", [
        (428.4, 428.4, "/: 28.3 GiB trimmed", True),
        (428.4, 428.45, "/: 1 GiB trimmed", True),
        (428.4, 440.0, "/: 12 GiB trimmed", False),
        (428.4, 428.4, "failed (exit 1): no", False),
        (428.4, 428.4, "not set up", False),
        (None, 428.4, "/: 1 GiB trimmed", False),
    ])
    def test_nothing_came_back_is_said_only_when_so(self, before, after, trimmed, said):
        got = D.nothing_back("C:", before, after, trimmed)
        assert ("nothing came back to Windows" in got) is said

    def test_never_said_of_ubuntu(self):
        assert D.nothing_back("Ubuntu", 900.0, 900.0, "/: 1 GiB trimmed") == ""
