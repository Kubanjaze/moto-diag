"""Phase 382, bug fix #1: the suite's result does not depend on the terminal.

The push guard's hook inherited the operator's terminal width through
COLUMNS, and at 38 columns two CLI tests failed on wrapped text. The conftest
now pins COLUMNS. This spawns pytest on one of those tests with a narrow
COLUMNS; without the pin it fails.
"""

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WRAPPED = ("tests/test_f86_recall_honesty.py::TestARecallThatDoesNotExist::"
           "test_a_real_duplicate_is_still_idempotent")


def test_a_narrow_terminal_does_not_change_the_result():
    env = dict(os.environ, COLUMNS="38")
    run = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:xdist", "-p", "no:cacheprovider", WRAPPED],
        cwd=REPO, env=env, capture_output=True, text=True, timeout=300,
    )
    assert run.returncode == 0, run.stdout[-2000:]
