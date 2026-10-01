"""Phase 369 — F183: the xdist worker lost with no traceback.

The cause: the push guard's ``main()`` left a 345 s SIGALRM armed when the
whole-tree gate raised, and its handler calls ``os._exit(2)``. A test that
ran ``main()`` inside a worker lost that worker 345 s later, in whatever
test it had reached.

What this holds:

* neither guard leaves its alarm armed, whatever escapes ``main()``;
* ``support.alarm_left_armed`` fails a test that leaves SIGALRM armed, and a
  later test in the same worker survives;
* ``support.worker_loss`` names how a lost worker ended (exit status or
  signal), the test it last started, and a catchable signal it received.
  A fatal signal's dump is not planted here: on macOS each one writes a
  crash report to ~/Library/Logs/DiagnosticReports, the place F183 was
  read from. Phase 369's log records it proven once by hand;
* the suite's conftest loads both.

The planted runs are nested pytest processes in ``tmp_path`` with their own
ini file, so the repository's configuration and conftest stay out of them.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import signal
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"
CLOSEOUT = ROOT / ".claude" / "skills" / "closeout"
sys.path.insert(0, str(CLOSEOUT))

import _edit_guard as edit_guard  # noqa: E402
import _pre_push_guard as push_guard  # noqa: E402


class _Stdin:
    def __init__(self, text: str):
        self._text = text

    def read(self, *_):
        return self._text


def _alarm_left() -> float:
    """Seconds left on the real-time timer; cancels it, so no test is harmed."""
    left, _ = signal.setitimer(signal.ITIMER_REAL, 0)
    return left


class TestTheGuardsCancelTheirAlarm:
    def test_the_push_guard_cancels_when_the_whole_tree_gate_raises(self, monkeypatch, capsys):
        import roadmap_check
        monkeypatch.setattr(roadmap_check, "check_tree", lambda *a, **k: [])

        def boom(*a, **k):
            raise RuntimeError("planted")
        monkeypatch.setattr(push_guard, "wholetree_gate", boom)
        monkeypatch.setattr(sys, "stdin", _Stdin(json.dumps({"tool_input": {"command": "git push"}})))
        assert push_guard.main() == 2                       # still fails closed
        assert _alarm_left() == 0, "the push guard left its alarm armed (F183)"

    def test_the_edit_guard_cancels_when_its_check_is_interrupted(self, monkeypatch):
        def interrupted(*a, **k):
            raise KeyboardInterrupt                         # not an Exception: escapes main()
        monkeypatch.setattr(edit_guard, "check", interrupted)
        monkeypatch.setattr(sys, "stdin", _Stdin(json.dumps(
            {"tool_input": {"command": "sed -i s/a/b/ x"}, "cwd": str(ROOT)})))
        with pytest.raises(KeyboardInterrupt):
            edit_guard.main()
        assert _alarm_left() == 0, "the edit guard left its alarm armed (F183)"


def _nested(tmp_path: pathlib.Path, body: str, workers: int) -> str:
    """Run a planted test file under its own xdist pytest, with both plugins."""
    (tmp_path / "pytest.ini").write_text("[pytest]\n")
    (tmp_path / "test_planted.py").write_text(body)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PYTEST_", "PYTHONPATH"))}
    env["PYTHONPATH"] = str(TESTS)
    p = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-p", "support.worker_loss",
         "-p", "support.alarm_left_armed", "-v", "-n", str(workers), "test_planted.py"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=180)
    return p.stdout + p.stderr


class TestTheAlarmCheck:
    def test_a_test_that_leaves_an_alarm_fails_and_the_next_one_survives(self, tmp_path):
        out = _nested(tmp_path, (
            "import signal, time\n"
            "def test_arms_an_alarm():\n"
            "    signal.alarm(2)\n"
            "def test_runs_after_it():\n"
            "    time.sleep(4)\n"), workers=1)
        assert re.search(r"ERROR test_planted.py::test_arms_an_alarm", out), out
        assert "left SIGALRM armed" in out, out
        assert re.search(r"PASSED test_planted.py::test_runs_after_it", out), out
        assert "node down" not in out, out


class TestALostWorkerExplainsItself:
    PLANTED = (
        "import os, signal, time\n"
        "def test_exits():\n"
        "    os._exit(2)\n"
        "def test_killed():\n"
        "    os.kill(os.getpid(), signal.SIGKILL)\n"
        "def test_terminated():\n"
        "    os.kill(os.getpid(), signal.SIGTERM)\n"
        "    time.sleep(5)\n"
        "def test_fine():\n"
        "    pass\n")

    @pytest.fixture(scope="class")
    def blocks(self, tmp_path_factory) -> dict[str, list[str]]:
        """Each lost worker's report, keyed by the test it last started."""
        out = _nested(tmp_path_factory.mktemp("lost"), self.PLANTED, workers=2)
        lines = [ln for ln in out.splitlines() if ln.startswith("worker-loss: ")]
        found: dict[str, list[str]] = {}
        for i, ln in enumerate(lines):
            if re.match(r"worker-loss: gw\d+ pid \d+: ", ln):
                block = [ln]
                for nxt in lines[i + 1:]:
                    if re.match(r"worker-loss: gw\d+ pid ", nxt):
                        break
                    block.append(nxt)
                started = re.search(r"started test_planted.py::(\w+)", block[1])
                found[started.group(1) if started else "?"] = block
        assert set(found) == {"test_exits", "test_killed", "test_terminated"}, out
        return found

    def test_an_exit_is_named_with_its_status(self, blocks):
        assert "exited with status 2 (no signal)" in blocks["test_exits"][0]
        assert any("no catchable signal received" in ln for ln in blocks["test_exits"])

    def test_an_uncatchable_kill_is_named(self, blocks):
        assert "killed by signal SIGKILL (9)" in blocks["test_killed"][0]

    def test_a_catchable_signal_leaves_its_traceback(self, blocks):
        b = blocks["test_terminated"]
        assert "killed by signal SIGTERM (15)" in b[0]
        i = b.index("worker-loss: SIGTERM received:")
        assert "test_terminated" in "\n".join(b[i:]), b

    def test_the_pid_is_the_workers_own(self, blocks):
        for b in blocks.values():
            pid = re.search(r"pid (\d+):", b[0]).group(1)
            assert b[1].startswith(f"worker-loss: pid {pid};"), b


class TestTheWiring:
    def test_the_suite_loads_both_plugins(self, request):
        pm = request.config.pluginmanager
        assert pm.get_plugin("support.worker_loss") is not None
        assert pm.get_plugin("support.alarm_left_armed") is not None
