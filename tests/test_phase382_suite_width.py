"""Phase 382, bug fixes #1 and #2: the suite's result does not depend on the terminal.

The push guard's hook inherited the operator's terminal width through
COLUMNS, and at 38 columns two CLI tests failed on wrapped text (#1). Pinning
COLUMNS=80 then broke 44 gate tests (#2): a Rich Console reads COLUMNS when
it is built, so the CLI's module-level consoles kept 80 and ignored the 240
the gate tests set. The conftest now removes COLUMNS. The first test spawns
pytest on a wrapped test at 38 columns; the second checks that a console
built at import still follows a COLUMNS set later.
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


def test_a_console_built_at_import_follows_a_width_set_later(tmp_path):
    probe = tmp_path / "test_probe.py"
    probe.write_text(
        "from rich.console import Console\n"
        "console = Console()\n"
        "def test_probe(monkeypatch):\n"
        "    monkeypatch.setenv('COLUMNS', '240')\n"
        "    assert console.width == 240\n")
    # The suite's conftest, loaded as a plugin, before the probe is imported.
    env = dict(os.environ, COLUMNS="38", PYTHONPATH=str(REPO / "tests"))
    run = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:xdist", "-p", "no:cacheprovider",
         "-p", "conftest", str(probe)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300,
    )
    assert run.returncode == 0, run.stdout[-2000:]
