"""Phase 355 — the regression of record runs in parallel under pytest-xdist.

What this file holds in place:

- pytest-xdist is a declared dev dependency, and `addopts` carries no `-n`.
  Seven test files spawn pytest. If `addopts` carried a worker count, each
  spawned run would start its own worker pool inside a worker.
- Every spawned pytest says how it runs: `-p no:xdist`, or an explicit
  `-n`. Nothing is inherited. The scanner parses; a flag written in a
  comment does not count.
- The canonical command is the one stated in the closeout skill, in
  CLAUDE.md and in `regression.sh`, the script that runs it.
- A failing test is reported by a parallel run: the planted-failure proof,
  kept as a test so it cannot quietly stop being true.
"""

from __future__ import annotations

import ast
import os
import pathlib
import subprocess
import sys
import textwrap
import tomllib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
TESTS_DIR = ROOT / "tests"
CLOSEOUT = ROOT / ".claude" / "skills" / "closeout"
CANONICAL = "python -m pytest -n auto --dist load"


def spawned_pytest_without_a_mode(directory: pathlib.Path) -> list[str]:
    """Every `[..., "-m", "pytest", ...]` list in test_*.py that neither
    disables xdist nor sets its own worker count, as "file:line"."""
    offenders: list[str] = []
    for path in sorted(directory.glob("test_*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.List, ast.Tuple)):
                continue
            words = [e.value for e in node.elts
                     if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            spawns = any(a == "-m" and b == "pytest" for a, b in zip(words, words[1:]))
            if not spawns:
                continue
            if "no:xdist" in words or any(w in ("-n", "--numprocesses") for w in words):
                continue
            offenders.append(f"{path.name}:{node.lineno}")
    return offenders


class TestTheWorkerCountIsNeverInherited:
    def test_xdist_is_a_dev_dependency(self):
        cfg = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        dev = cfg["project"]["optional-dependencies"]["dev"]
        assert any(d.startswith("pytest-xdist") for d in dev), dev

    def test_addopts_carries_no_worker_count(self):
        cfg = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        opts = cfg["tool"]["pytest"]["ini_options"]["addopts"].split()
        assert not {"-n", "--numprocesses", "--dist"} & set(opts), opts
        assert not any(o.startswith(("-n", "--numprocesses=", "--dist=")) for o in opts), opts

    def test_every_spawned_pytest_states_its_mode(self):
        assert spawned_pytest_without_a_mode(TESTS_DIR) == []

    def test_the_scan_sees_the_spawns_it_passes(self):
        """Positive control: the real tree has spawns, and the scanner sees them."""
        seen = 0
        for path in TESTS_DIR.glob("test_*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, (ast.List, ast.Tuple)):
                    words = [e.value for e in node.elts if isinstance(e, ast.Constant)]
                    if "pytest" in words and "no:xdist" in words:
                        seen += 1
        # 147 x2, 159 x2, 205, 240, 250, 258 and 255B's collection count.
        # This file's planted-failure run sets -n 2 instead, so it is not here.
        assert seen >= 9, seen


class TestTheScannerCanFail:
    """Known-bad controls, written to a tmp dir the scanner then reads."""

    def _scan(self, tmp_path, body: str) -> list[str]:
        (tmp_path / "test_planted.py").write_text(textwrap.dedent(body), encoding="utf-8")
        return spawned_pytest_without_a_mode(tmp_path)

    def test_a_spawn_with_no_mode_is_caught(self, tmp_path):
        assert self._scan(tmp_path, """
            import subprocess, sys
            subprocess.run([sys.executable, "-m", "pytest", "x.py", "-q"])
        """) == ["test_planted.py:3"]

    def test_the_flag_in_a_comment_does_not_count(self, tmp_path):
        assert self._scan(tmp_path, """
            import subprocess, sys
            subprocess.run([sys.executable, "-m", "pytest", "x.py"])  # "-p", "no:xdist"
        """) == ["test_planted.py:3"]

    def test_an_opt_out_passes(self, tmp_path):
        assert self._scan(tmp_path, """
            import subprocess, sys
            subprocess.run([sys.executable, "-m", "pytest", "x.py", "-p", "no:xdist"])
        """) == []

    def test_an_explicit_worker_count_passes(self, tmp_path):
        assert self._scan(tmp_path, """
            import subprocess, sys
            subprocess.run([sys.executable, "-m", "pytest", "-n", "2", "x.py"])
        """) == []


class TestTheCanonicalCommandIsStated:
    def test_the_script_runs_it(self):
        script = CLOSEOUT / "regression.sh"
        text = script.read_text(encoding="utf-8")
        assert os.access(script, os.X_OK)
        assert 'ARGS="-n auto --dist load"' in text
        assert 'ARGS="-p no:xdist"' in text          # the --serial fallback

    def test_the_skill_states_it_at_step_1(self):
        skill = (CLOSEOUT / "SKILL.md").read_text(encoding="utf-8")
        step1 = skill.split("\n1. ", 1)[1].split("\n2. ", 1)[0]
        assert CANONICAL in step1 and "regression.sh" in step1
        assert "--serial" in step1

    def test_claude_md_states_it(self):
        text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        assert CANONICAL in text and "regression.sh --serial" in text

    def test_verify_phase_runs_its_tests_in_parallel(self):
        text = (CLOSEOUT / "verify_phase.sh").read_text(encoding="utf-8")
        assert '-m pytest -n auto --dist load -k "$PHASE"' in text


class TestAParallelRunReportsAFailure:
    """The planted-failure proof. A nested pool of two workers, deliberately:
    this is the one spawned run whose point is to run in parallel."""

    def test_the_planted_failure_is_reported(self, tmp_path):
        (tmp_path / "test_planted.py").write_text(textwrap.dedent("""
            def test_passes():
                assert True

            def test_planted_failure():
                assert 1 == 2, "planted by Phase 355"
        """), encoding="utf-8")
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "-n", "2", "--dist", "load",
             "-p", "no:cacheprovider", "-rA", "test_planted.py"],
            cwd=tmp_path, capture_output=True, text=True, timeout=300,
        )
        assert r.returncode == 1, r.stdout[-2000:]
        assert "2 workers" in r.stdout, r.stdout[-2000:]
        assert "FAILED test_planted.py::test_planted_failure" in r.stdout
        assert "PASSED test_planted.py::test_passes" in r.stdout
        assert "1 failed, 1 passed" in r.stdout
