"""Phase 390 — a real dispatcher process, killed half way, and restarted (F219).

F219's own words: "A test kills a stage half way and restarts the
dispatcher." A dispatcher process (`tests/support/fleet_kill_driver.py`, on
389's stand-ins, its GitHub kept on disk) is SIGKILLed, with its whole
process group, while its Science Officer's first model call is running,
which is what systemd's control-group kill does. A second process then runs
the search on start: the stage is resumed with `--resume` and the session
its transcript names, in the same run directory, and reaches `step0:done`.
"""
from __future__ import annotations

import json
import os
import pathlib
import signal
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "fleet"))

import journal as J  # noqa: E402
from test_phase389_dispatcher import PHASE, TITLE, TRIAL  # noqa: E402
from test_phase389_fleet_git import git, make_origin  # noqa: E402
from test_phase390_resume import CUT  # noqa: E402

DRIVER = ROOT / "tests" / "support" / "fleet_kill_driver.py"


def test_a_killed_process_resumes_its_stage_in_the_next(tmp_path):
    origin = make_origin(tmp_path)
    road = origin / "docs" / "ROADMAP.md"
    road.write_text(road.read_text().rstrip("\n") + f"\n| {PHASE} | The trial | 🚧 | x |\n")
    git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qam", "row 902", cwd=origin)
    issue = {"title": TITLE, "body": TRIAL, "comments": [], "labels": ["mission"],
             "events": [{"label": "mission", "at": "2026-10-25T12:00:00Z"}]}
    (tmp_path / "github.json").write_text(json.dumps({"31": issue}))
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "state.json").write_text(json.dumps({"last_digest": "2999-01-01"}))
    env = {**os.environ, "FLEET_LEDGER": str(tmp_path / "calls.jsonl")}

    first = subprocess.Popen([sys.executable, str(DRIVER), "first", str(tmp_path)], env=env,
                             start_new_session=True, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
    deadline = time.monotonic() + 120
    while not (tmp_path / "hanging").exists():
        assert first.poll() is None, first.stdout.read().decode()
        assert time.monotonic() < deadline, "the first process never reached its model call"
        time.sleep(0.2)
    os.killpg(first.pid, signal.SIGKILL)
    assert first.wait(30) == -signal.SIGKILL

    (j,) = J.unfinished(tmp_path / "state" / "runs")
    assert j.record["stage"] == "scout" and j.data["calls"][0]["done"] is False
    labels = json.loads((tmp_path / "github.json").read_text())["31"]["labels"]
    assert labels == ["mission"]

    second = subprocess.run([sys.executable, str(DRIVER), "second", str(tmp_path)], env=env,
                            capture_output=True, text=True, timeout=300)
    assert second.returncode == 0, second.stdout + second.stderr
    assert (f"resume scout from {j.run.name} (issue 31), after started, clone, session {CUT}"
            in second.stdout), second.stdout

    calls = [json.loads(ln) for ln in (tmp_path / "model_calls.jsonl").read_text().splitlines()]
    assert calls[1] == ["claude", "--resume", CUT], calls
    gh = json.loads((tmp_path / "github.json").read_text())["31"]
    assert sorted(gh["labels"]) == ["mission", "step0:done"]
    assert sum(c["body"].startswith("<!-- fleet-scout:") for c in gh["comments"]) == 1
    assert not J.Journal.load(j.run).unfinished
    assert sorted(p.name for p in (tmp_path / "state" / "runs").glob("*_scout_*")) == [j.run.name]
