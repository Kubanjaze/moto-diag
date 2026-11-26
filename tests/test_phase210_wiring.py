"""Phase 210: ``motodiag launch check`` is reachable, and its documents say so.

The command is on the real root CLI; ``main.py`` carries its import and its
registration once each; the module imports no web framework at the CLI's
start (293's bug fix #3); and the launch checklist names the command.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

from click.testing import CliRunner

from motodiag.cli.main import cli

REPO = Path(__file__).resolve().parent.parent
MAIN = REPO / "src" / "motodiag" / "cli" / "main.py"
LAUNCH_CLI = REPO / "src" / "motodiag" / "cli" / "launch.py"
CHECK = REPO / "src" / "motodiag" / "launch" / "check.py"
CHECKLIST = REPO / "docs" / "launch-checklist.md"
NOT_INSTALLED = ("fastapi", "uvicorn", "starlette")


def test_launch_is_on_the_root_with_check():
    assert "launch" in cli.commands
    assert "check" in cli.commands["launch"].commands


def test_launch_help_lists_check():
    out = CliRunner().invoke(cli, ["launch", "--help"])
    assert out.exit_code == 0, out.output
    assert "check" in out.output


def test_main_carries_the_import_and_the_call_once_each():
    text = MAIN.read_text(encoding="utf-8")
    assert text.count("from motodiag.cli.launch import register_launch") == 1
    assert text.count("register_launch(cli)") == 1


def _module_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_no_web_framework_at_module_level():
    for path in (LAUNCH_CLI, CHECK):
        imported = _module_level_imports(path)
        assert not {n for n in imported if n.split(".")[0] in NOT_INSTALLED}, path
        assert "motodiag.api" not in {".".join(n.split(".")[:2]) for n in imported}, path


def test_launch_help_starts_without_the_server_libraries(tmp_path):
    """As 293's test does for ``--version``: the web framework cannot be
    imported, and ``motodiag launch --help`` still runs."""
    code = "\n".join((
        "import sys",
        f"for name in {NOT_INSTALLED!r}:",
        "    sys.modules[name] = None",
        "from motodiag.cli.main import cli",
        "cli(['launch', '--help'], prog_name='motodiag')",
    ))
    env = {**os.environ, "MOTODIAG_DB_PATH": str(tmp_path / "plain.db")}
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                          timeout=120, env=env)
    assert proc.returncode == 0, proc.stderr[-1500:]
    assert "check" in proc.stdout


def test_the_checklist_names_the_command_and_is_no_longer_unstarted():
    text = CHECKLIST.read_text(encoding="utf-8")
    assert "motodiag launch check" in text
    assert "still deliberately unstarted" not in text
    assert "ALL GOOD" in text and "SOMETHING IS OFF" in text


def test_no_phase210_test_reads_git_diff_or_a_master_ref():
    for path in sorted((REPO / "tests").glob("test_phase210_*.py")):
        text = path.read_text(encoding="utf-8")
        for word in ("git" + " diff", "origin/" + "master", "'" + "master" + "'"):
            assert word not in text, f"{path.name} reads {word!r}"
