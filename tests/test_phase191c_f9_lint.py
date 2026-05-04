"""Phase 191C — unit tests for ``scripts/check_f9_patterns.py``.

Three test classes mirroring the script's checks:
  - TestCheckModelIds: subspecies (ii) — model-ID literals in test files
  - TestCheckDeployPathInitDb: subspecies (iv) — serve commands missing init_db
  - TestRunAllChecks + TestMainCli: orchestration + CLI entry point

Pattern doc: ``docs/patterns/f9-mock-vs-runtime-drift.md``.
Plan: ``docs/phases/in_progress/191C_implementation.md``.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------
# Module loader: scripts/ is not a Python package, so we load the module
# via importlib.util to avoid sys.path munging or adding an __init__.py
# ---------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_f9_patterns.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location(
        "check_f9_patterns", SCRIPT_PATH
    )
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"Could not load {SCRIPT_PATH}")
    mod = importlib.util.module_from_spec(spec)
    # Register in sys.modules BEFORE exec_module so @dataclass can
    # resolve cls.__module__ via sys.modules.get(...).__dict__ lookup.
    # Without this, dataclasses raises:
    #   AttributeError: 'NoneType' object has no attribute '__dict__'
    # Phase 191C fix-cycle (Commit 2 self-test) — Python 3.13 dataclass
    # internals require the module to be importable by name during
    # decoration.
    sys.modules["check_f9_patterns"] = mod
    spec.loader.exec_module(mod)
    return mod


_check_f9 = _load_script_module()
F9Finding = _check_f9.F9Finding
check_model_ids = _check_f9.check_model_ids
check_deploy_path_init_db = _check_f9.check_deploy_path_init_db
run_all_checks = _check_f9.run_all_checks


# ---------------------------------------------------------------------
# Source-of-truth literal references for assertions in this file.
#
# This test file is itself under tests/, so any literal model ID we
# write here would trigger the no-hardcoded-model-ids rule. Wrap them
# in KNOWN_BOGUS_IDS / KNOWN_GOOD_MODEL_IDS sets so the rule's
# exempt-container check passes — the same exemption pattern the rule
# enforces for production test files.
#
# Phase 191C Commit 2 self-test discipline: the lint script must not
# complain about its own test file's legitimate references. If the
# rule changes its exempt list, this set's name has to track.
# ---------------------------------------------------------------------

KNOWN_BOGUS_IDS = {
    "claude-sonnet-4-5-20241022",  # the architect-gate Step 7 bogus ID
}

KNOWN_GOOD_MODEL_IDS = {
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
    "claude-opus-4-7",
}


# ---------------------------------------------------------------------
# Class 1 — TestCheckModelIds (subspecies ii)
# ---------------------------------------------------------------------


class TestCheckModelIds:
    """Positive, negative, and exemption guards for ``check_model_ids``."""

    def test_clean_main_has_zero_findings(self):
        """Anti-regression for Phase 191B C2 fix-cycle-4 model-string scrub.

        Running ``check_model_ids`` against THIS repo's ``tests/`` directory
        must return zero findings — every model ID should already live in
        an exempt source-of-truth container (``KNOWN_GOOD_MODEL_IDS`` etc.).
        If this test fails, a new hardcoded literal slipped in and needs to
        be moved into a set OR the file needs a documented file-level
        ``# f9-allow-model-ids: <reason>`` opt-out (20-char reason floor).

        Un-xfailed at Commit 5b (2026-05-04) after 5a's clean-baseline scrub
        landed 0 findings on master.
        """
        findings = check_model_ids([REPO_ROOT / "tests"])
        assert findings == [], (
            f"Expected zero findings against clean main, got "
            f"{len(findings)}:\n"
            + "\n".join(f.format() for f in findings)
        )

    def test_finds_hardcoded_bogus_id_in_test_file(self, tmp_path: Path):
        """Synthetic test file with an unexempt bogus literal → 1 finding."""
        bogus = next(iter(KNOWN_BOGUS_IDS))
        test_file = tmp_path / "test_synthetic.py"
        test_file.write_text(
            f'def test_bad():\n'
            f'    assert _resolve_model("sonnet") == "{bogus}"\n',
            encoding="utf-8",
        )
        findings = check_model_ids([tmp_path])
        assert len(findings) == 1
        f = findings[0]
        assert f.file == test_file
        assert f.line == 2
        assert f.rule == "model-ids"
        assert any(b in f.message for b in KNOWN_BOGUS_IDS)
        assert any(b in f.snippet for b in KNOWN_BOGUS_IDS)

    def test_exempts_known_good_ids_set(self, tmp_path: Path):
        """Literals inside ``KNOWN_GOOD_MODEL_IDS = {...}`` must not fire."""
        test_file = tmp_path / "test_synthetic.py"
        test_file.write_text(
            'KNOWN_GOOD_MODEL_IDS = {\n'
            '    "claude-sonnet-4-6",\n'
            '    "claude-opus-4-7",\n'
            '}\n',
            encoding="utf-8",
        )
        findings = check_model_ids([tmp_path])
        assert findings == []

    def test_exempts_known_bogus_ids_set(self, tmp_path: Path):
        """The anti-regression pin literal inside ``KNOWN_BOGUS_IDS`` must
        not trigger — that is the Phase 191B C2 architect-gate-step-7 guard
        and removing it would defeat the whole point."""
        test_file = tmp_path / "test_synthetic.py"
        test_file.write_text(
            'KNOWN_BOGUS_IDS = {\n'
            '    "claude-sonnet-4-5-20241022",\n'
            '}\n',
            encoding="utf-8",
        )
        findings = check_model_ids([tmp_path])
        assert findings == []

    def test_exempts_model_aliases_dict(self, tmp_path: Path):
        """``MODEL_ALIASES = {...}`` is a valid container per plan v1.0.1."""
        test_file = tmp_path / "test_synthetic.py"
        test_file.write_text(
            'MODEL_ALIASES = {\n'
            '    "sonnet": "claude-sonnet-4-6",\n'
            '    "haiku": "claude-haiku-4-5-20251001",\n'
            '}\n',
            encoding="utf-8",
        )
        findings = check_model_ids([tmp_path])
        assert findings == []

    def test_exempts_model_pricing_dict(self, tmp_path: Path):
        """``MODEL_PRICING = {...}`` keys legitimately contain literal IDs."""
        test_file = tmp_path / "test_synthetic.py"
        test_file.write_text(
            'MODEL_PRICING = {\n'
            '    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},\n'
            '    "claude-haiku-4-5-20251001": {"input": 0.8, "output": 4.0},\n'
            '}\n',
            encoding="utf-8",
        )
        findings = check_model_ids([tmp_path])
        assert findings == []

    def test_string_outside_exempt_assignment_is_flagged(
        self, tmp_path: Path
    ):
        """Literal in a function body (no exempt assignment) IS flagged."""
        test_file = tmp_path / "test_synthetic.py"
        test_file.write_text(
            'def test_inline():\n'
            '    model = "claude-haiku-4-5-20251001"\n'
            '    assert model.startswith("claude")\n',
            encoding="utf-8",
        )
        findings = check_model_ids([tmp_path])
        assert len(findings) == 1
        assert findings[0].rule == "model-ids"

    def test_substring_inside_docstring_not_flagged(self, tmp_path: Path):
        """Docstring sentences mentioning a model ID as part of prose
        should NOT trigger because :func:`re.fullmatch` only matches
        exact-string literals, not substrings of larger strings."""
        test_file = tmp_path / "test_synthetic.py"
        test_file.write_text(
            '"""This module tests the claude-sonnet-4-6 model integration\n'
            'against various input shapes; it does not assert on literal IDs.\n'
            '"""\n'
            'def test_noop():\n'
            '    pass\n',
            encoding="utf-8",
        )
        findings = check_model_ids([tmp_path])
        assert findings == []


# ---------------------------------------------------------------------
# Class 2 — TestCheckDeployPathInitDb (subspecies iv)
# ---------------------------------------------------------------------


class TestCheckDeployPathInitDb:
    """Positive, exemption, and opt-out guards for the deploy-path check."""

    def test_clean_main_has_zero_findings(self):
        """Phase 191B fix-cycle-1 added init_db to ``serve.py``; this is
        the regression guard ensuring no new long-running CLI entry slips
        in without it."""
        findings = check_deploy_path_init_db(
            REPO_ROOT / "src" / "motodiag" / "cli"
        )
        assert findings == [], (
            f"Expected zero findings against clean main, got "
            f"{len(findings)}:\n"
            + "\n".join(f.format() for f in findings)
        )

    def test_finds_uvicorn_run_without_init_db(self, tmp_path: Path):
        """Click-decorated function calling ``uvicorn.run`` w/o init_db."""
        cli_file = tmp_path / "broken_cmd.py"
        cli_file.write_text(
            'import click\n'
            'import uvicorn\n'
            '\n'
            '@click.group()\n'
            'def cli_group():\n'
            '    pass\n'
            '\n'
            '@cli_group.command("serve")\n'
            'def serve_cmd():\n'
            '    uvicorn.run("app:create", factory=True)\n',
            encoding="utf-8",
        )
        findings = check_deploy_path_init_db(tmp_path)
        assert len(findings) == 1
        f = findings[0]
        assert f.file == cli_file
        assert f.rule == "deploy-path-init-db"
        assert "serve_cmd" in f.message
        assert "uvicorn.run" in f.snippet

    def test_exempts_when_init_db_called_first(self, tmp_path: Path):
        """``init_db(...)`` precedes ``uvicorn.run(...)`` → no finding."""
        cli_file = tmp_path / "good_cmd.py"
        cli_file.write_text(
            'import click\n'
            'import uvicorn\n'
            'from motodiag.core.database import init_db\n'
            '\n'
            '@click.group()\n'
            'def cli_group():\n'
            '    pass\n'
            '\n'
            '@cli_group.command("serve")\n'
            'def serve_cmd():\n'
            '    init_db("/tmp/db.sqlite", apply_migrations=True)\n'
            '    uvicorn.run("app:create", factory=True)\n',
            encoding="utf-8",
        )
        findings = check_deploy_path_init_db(tmp_path)
        assert findings == []

    def test_exempts_via_f9_noqa_comment(self, tmp_path: Path):
        """Explicit ``# f9-noqa: deploy-path-init-db <reason>`` opts out
        WHEN reason is >= MIN_OPTOUT_REASON_CHARS chars long. Phase
        191C Commit 5a refinement enforces a length floor so opt-outs
        teach (rather than drive-by-allow). Drive-by short reasons get
        treated as no opt-out + a malformed-optout finding gets
        emitted (covered in test_rejects_too_short_reason below)."""
        cli_file = tmp_path / "noqa_cmd.py"
        cli_file.write_text(
            'import click\n'
            'import uvicorn\n'
            '\n'
            '@click.group()\n'
            'def cli_group():\n'
            '    pass\n'
            '\n'
            '@cli_group.command("test-only-serve")\n'
            'def test_only_serve_cmd():\n'
            '    uvicorn.run("app:create", factory=True)  '
            '# f9-noqa: deploy-path-init-db tests-only CLI; never serves '
            'real traffic, init_db handled by test fixture\n',
            encoding="utf-8",
        )
        findings = check_deploy_path_init_db(tmp_path)
        assert findings == []

    def test_non_click_function_not_scanned(self, tmp_path: Path):
        """Plain functions (no ``@*.command(...)`` decorator) are out of
        scope — the rule targets CLI entries specifically because those are
        the deploy-paths that get wired into production launch scripts."""
        cli_file = tmp_path / "plain_func.py"
        cli_file.write_text(
            'import uvicorn\n'
            '\n'
            'def helper_serve():\n'
            '    uvicorn.run("app:create", factory=True)\n',
            encoding="utf-8",
        )
        findings = check_deploy_path_init_db(tmp_path)
        assert findings == []


# ---------------------------------------------------------------------
# Class 3 — TestRunAllChecks + TestMainCli (orchestration + CLI)
# ---------------------------------------------------------------------


class TestRunAllChecks:
    """Aggregator + CLI entry point integration tests."""

    def test_run_all_checks_aggregates_findings(self, tmp_path: Path):
        """Synthetic tree with one violation per check → 2 findings total.

        The model-id violation lives in a non-exempt module-level assignment
        (``BOGUS = "..."``) so exactly one literal triggers; the deploy-path
        violation is an unwired ``serve_cmd`` calling ``uvicorn.run`` without
        ``init_db``. Aggregator should return both.
        """
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_bad.py").write_text(
            'BOGUS = "claude-sonnet-4-5-20241022"\n'
            'def test_bad():\n'
            '    assert BOGUS\n',
            encoding="utf-8",
        )
        cli_dir = tmp_path / "src" / "motodiag" / "cli"
        cli_dir.mkdir(parents=True)
        (cli_dir / "serve.py").write_text(
            'import click\n'
            'import uvicorn\n'
            '\n'
            '@click.group()\n'
            'def cli_group():\n'
            '    pass\n'
            '\n'
            '@cli_group.command("serve")\n'
            'def serve_cmd():\n'
            '    uvicorn.run("app", factory=True)\n',
            encoding="utf-8",
        )
        findings = run_all_checks(tmp_path)
        assert len(findings) == 2, (
            f"Expected 2 findings (1 model-id + 1 deploy-path), got "
            f"{len(findings)}:\n"
            + "\n".join(f.format() for f in findings)
        )
        rules = {f.rule for f in findings}
        assert rules == {"model-ids", "deploy-path-init-db"}


class TestMainCli:
    """End-to-end CLI invocation via subprocess, using ``sys.executable``."""

    def test_main_cli_clean_exits_zero(self):
        """Run the script's ``--all`` mode against THIS repo → exit 0.

        Un-xfailed at Commit 5b (2026-05-04) alongside the sibling
        ``TestCheckModelIds.test_clean_main_has_zero_findings``.
        """
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--all",
                "--repo-root",
                str(REPO_ROOT),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Expected clean exit (0), got {result.returncode}.\n"
            f"stderr:\n{result.stderr}"
        )

    def test_main_cli_findings_exit_one(self, tmp_path: Path):
        """Synthetic temp dir with a violation → exit 1."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_bad.py").write_text(
            'BOGUS = "claude-sonnet-4-5-20241022"\n'
            'def test_x():\n'
            '    assert BOGUS\n',
            encoding="utf-8",
        )
        # Use --check-model-ids to avoid needing the cli/ tree
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--check-model-ids",
                "--repo-root",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1, (
            f"Expected exit 1 on findings, got {result.returncode}.\n"
            f"stderr:\n{result.stderr}"
        )
        assert "model-ids" in result.stderr
        assert any(b in result.stderr for b in KNOWN_BOGUS_IDS)


# ---------------------------------------------------------------------
# Sanity guard: the script file itself is present and importable.
# ---------------------------------------------------------------------


def test_script_path_exists():
    """Without the script in place, every other test in this module is
    moot. Pin the file's existence as a top-level sanity check."""
    assert SCRIPT_PATH.exists(), (
        f"Expected lint script at {SCRIPT_PATH}; not found. "
        f"Phase 191C Commit 2 should have created it."
    )


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
