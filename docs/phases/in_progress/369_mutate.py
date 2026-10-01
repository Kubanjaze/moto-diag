"""Phase 369's mutations: each undoes one thing the phase adds, and the
tests named beside it must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/369_mutate.py`
(moved to completed/ at close-out). 361's form: each mutation replaces one
exact string (which must occur once), runs its tests with `-B` after
clearing `__pycache__`, and restores the file whatever happens. Prints one
line per mutation and exits 1 if any stayed green.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
TESTS = ["tests/test_phase369_worker_loss.py"]
PUSH = ".claude/skills/closeout/_pre_push_guard.py"
EDIT = ".claude/skills/closeout/_edit_guard.py"
CHECK = "tests/support/alarm_left_armed.py"
LOSS = "tests/support/worker_loss.py"
CONFTEST = "tests/conftest.py"

MUTATIONS = [
    ("G1 the push guard cancels inside its try (the code before 369)", PUSH,
     "        fails = wholetree_gate(command, repo)\n"
     "    except Exception as e:                         # fails closed: only a push is blocked\n"
     "        fails = [f\"the whole-tree check could not run ({e!r}); the push is blocked\"]\n"
     "    finally:\n"
     "        signal.alarm(0)    # F183: an armed alarm outlives main() and os._exit()s a later test\n",
     "        fails = wholetree_gate(command, repo)\n"
     "        signal.alarm(0)\n"
     "    except Exception as e:                         # fails closed: only a push is blocked\n"
     "        fails = [f\"the whole-tree check could not run ({e!r}); the push is blocked\"]\n",
     TESTS),
    ("G2 the edit guard cancels after its try (the code before 369)", EDIT,
     "    finally:\n        signal.alarm(0)                    # F183: never left armed past main()\n",
     "    signal.alarm(0)\n", TESTS),
    ("C1 the teardown check never fails", CHECK,
     "        if left:\n", "        if False:\n", TESTS),
    ("C2 the teardown check runs before the real teardown", CHECK,
     "@pytest.hookimpl(wrapper=True)       # after the test's own teardown, never before it\n"
     "def pytest_runtest_teardown(item: pytest.Item):\n"
     "    try:\n        return (yield)\n    finally:\n",
     "def pytest_runtest_teardown(item: pytest.Item):\n"
     "    if True:\n        pass\n    if True:\n", TESTS),
    ("L1 a lost worker is not reported", LOSS,
     "    if not error or not folder:\n        return\n",
     "    return\n", TESTS),
    ("L2 the exit status is not read", LOSS,
     "            returncode = popen.wait(timeout=10)\n",
     "            returncode = None\n", TESTS),
    ("L3 no signal is registered", LOSS,
     "        faulthandler.register(getattr(signal, name), file=f, all_threads=True, chain=True)\n",
     "        pass\n", TESTS),
    ("L4 the last test is not recorded", LOSS,
     "        _last.write_text(f\"pid {os.getpid()}\\nstarted {nodeid}\\n\")\n",
     "        pass\n", TESTS),
    ("W1 the suite does not load the plugins", CONFTEST,
     "pytest_plugins = [\"support.worker_loss\", \"support.alarm_left_armed\"]\n",
     "pytest_plugins = []\n", TESTS),
]


def run_tests(tests: list[str]) -> int:
    for base in (ROOT / "src", ROOT / "tests", ROOT / ".claude"):
        for cache in base.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)
    return subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", *tests],
        cwd=ROOT, capture_output=True, text=True,
    ).returncode


def main(argv: list[str]) -> int:
    chosen = [m for m in MUTATIONS if not argv or m[0].startswith(argv[0])]
    every = sorted({t for m in chosen for t in m[4]})
    assert run_tests(every) == 0, "the tests are not green before mutating"
    survivors = []
    for name, rel, old, new, tests in chosen:
        path = ROOT / rel
        original = path.read_text()
        assert original.count(old) == 1, f"{name}: the text occurs {original.count(old)} times"
        try:
            path.write_text(original.replace(old, new))
            code = run_tests(tests)
        finally:
            path.write_text(original)
        verdict = "red" if code != 0 else "GREEN (survived)"
        print(f"{name}: {verdict}", flush=True)
        if code == 0:
            survivors.append(name)
    assert run_tests(every) == 0, "the tests are not green after restoring"
    print(f"{len(chosen) - len(survivors)}/{len(chosen)} red")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
