"""Phase 126 — Diagnostic Report Output (export to file) tests.

Covers:
- `TestFormatters`: pure formatter functions for txt / json / md
  (full session, minimal session, missing fields, JSON round-trip,
  format_version tag, markdown headings, no Rich markup in txt).
- `TestDiagnoseShowExport`: CLI options wire through (`--format`, `--output`,
  `--yes`); stdout paths for txt/json/md; file-write paths; missing session;
  overwrite confirmation.
- `TestFileWriteErrors`: directory-as-output, parent-dir auto-creation, and
  permission-style errors surfaced as ClickException.
- `TestRegression`: default terminal rendering unchanged (Phase 123 regression)
  and the new options don't perturb the existing show path.

Zero AI calls — pure formatting, so no mocking of `_default_diagnose_fn`.
"""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from motodiag.core.database import init_db
from motodiag.core.session_repo import (
    create_session, set_diagnosis, close_session, add_fault_code_to_session,
    get_session,
)

from motodiag.cli.diagnose import (
    _format_session_text,
    _format_session_json,
    _format_session_md,
    _write_report_to_file,
    _REPORT_FORMAT_VERSION,
)


# --- Fixtures ---


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase126.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(db, monkeypatch):
    """Point settings at the temp DB; reset config cache after."""
    from motodiag.core.config import reset_settings
    monkeypatch.setenv("MOTODIAG_DB_PATH", db)
    reset_settings()
    yield db
    reset_settings()


def _seed_full_session(db_path: str) -> int:
    """Create, diagnose, add fault code, and close a session.

    Returns the session ID. The session has all fields populated so
    formatters can exercise every branch.
    """
    sid = create_session(
        vehicle_make="Harley-Davidson",
        vehicle_model="Sportster 1200",
        vehicle_year=2001,
        symptoms=["won't start when cold", "cranks slow"],
        db_path=db_path,
    )
    add_fault_code_to_session(sid, "P0300", db_path=db_path)
    set_diagnosis(
        session_id=sid,
        diagnosis="Stator failure — voltage drops under load.",
        confidence=0.87,
        severity="high",
        repair_steps=[
            "Check stator continuity (service manual §7-3)",
            "Replace stator if reading below 0.2 ohm",
        ],
        db_path=db_path,
    )
    # set ai_model_used + tokens_used via raw UPDATE — the repo's
    # update_session only allows the allow-list we want to exercise.
    from motodiag.core.session_repo import update_session
    update_session(
        sid,
        {"ai_model_used": "haiku", "tokens_used": 1432},
        db_path=db_path,
    )
    close_session(sid, db_path=db_path)
    return sid


def _seed_minimal_session(db_path: str) -> int:
    """Session with no diagnosis and no fault codes. Status stays 'open'."""
    return create_session(
        vehicle_make="Honda",
        vehicle_model="CBR929RR",
        vehicle_year=2000,
        symptoms=[],
        db_path=db_path,
    )


# =============================================================================
# TestFormatters — pure dict → str
# =============================================================================


class TestFormatters:
    def test_text_full_session_contains_all_sections(self, db):
        sid = _seed_full_session(db)
        s = get_session(sid, db_path=db)
        out = _format_session_text(s)

        # Structural headings
        assert f"Session #{sid}" in out
        assert "Vehicle" in out
        assert "Symptoms" in out
        assert "Fault codes" in out
        assert "Diagnosis" in out
        assert "Repair steps" in out
        assert "Metadata" in out
        # Content
        assert "Harley-Davidson" in out
        assert "Sportster 1200" in out
        assert "won't start" in out
        assert "P0300" in out
        assert "Stator failure" in out
        assert "0.87" in out
        assert "high" in out
        assert "haiku" in out
        assert "1432" in out

    def test_text_has_no_rich_markup(self, db):
        sid = _seed_full_session(db)
        s = get_session(sid, db_path=db)
        out = _format_session_text(s)

        # No Rich-style tags like [bold], [red], [/green], etc.
        # Common markup tokens that would appear if we accidentally leaked
        # Rich markup into the text formatter.
        forbidden_markers = [
            "[bold]", "[/bold]", "[red]", "[/red]", "[green]", "[/green]",
            "[cyan]", "[/cyan]", "[yellow]", "[/yellow]", "[dim]", "[/dim]",
        ]
        for token in forbidden_markers:
            assert token not in out, f"Rich markup {token!r} leaked into text output"

    def test_text_minimal_session_no_crash(self, db):
        sid = _seed_minimal_session(db)
        s = get_session(sid, db_path=db)
        out = _format_session_text(s)
        # Missing fields rendered as '-' or '(none)'; text formatter must not
        # raise on None confidence / empty repair_steps / empty fault_codes.
        assert f"Session #{sid}" in out
        assert "(none)" in out  # diagnosis falls back to "(none)"
        # Confidence / severity rendered as dash when None
        assert "Confidence: -" in out
        assert "Severity: -" in out

    def test_json_full_session_round_trips(self, db):
        sid = _seed_full_session(db)
        s = get_session(sid, db_path=db)
        out = _format_session_json(s)

        parsed = json.loads(out)
        # format_version tag present
        assert parsed["format_version"] == _REPORT_FORMAT_VERSION
        # All session fields preserved
        assert parsed["id"] == sid
        assert parsed["vehicle_make"] == "Harley-Davidson"
        assert parsed["vehicle_model"] == "Sportster 1200"
        assert parsed["vehicle_year"] == 2001
        assert parsed["status"] == "closed"
        assert parsed["symptoms"] == ["won't start when cold", "cranks slow"]
        assert parsed["fault_codes"] == ["P0300"]
        assert parsed["diagnosis"].startswith("Stator failure")
        assert parsed["confidence"] == 0.87
        assert parsed["severity"] == "high"
        assert parsed["ai_model_used"] == "haiku"
        assert parsed["tokens_used"] == 1432
        assert parsed["repair_steps"] == [
            "Check stator continuity (service manual §7-3)",
            "Replace stator if reading below 0.2 ohm",
        ]

    def test_json_format_version_first_key(self, db):
        """format_version should be the first key in the JSON output so
        consumers can reject unknown versions without parsing the whole doc."""
        sid = _seed_full_session(db)
        s = get_session(sid, db_path=db)
        out = _format_session_json(s)
        # First non-whitespace after '{' must be "format_version"
        stripped = out.lstrip()
        assert stripped.startswith("{")
        # The opening line should contain format_version before any other field
        first_line_with_key = out.split("\n")[1]  # line after the '{'
        assert "format_version" in first_line_with_key

    def test_json_minimal_session_round_trips(self, db):
        sid = _seed_minimal_session(db)
        s = get_session(sid, db_path=db)
        out = _format_session_json(s)
        parsed = json.loads(out)
        assert parsed["format_version"] == _REPORT_FORMAT_VERSION
        assert parsed["id"] == sid
        assert parsed["status"] == "open"
        assert parsed["symptoms"] == []
        assert parsed["fault_codes"] == []
        # Empty repair_steps defaulted by session_repo._row_to_dict
        assert parsed["repair_steps"] == []
        assert parsed["diagnosis"] is None
        assert parsed["confidence"] is None

    def test_md_full_session_has_gfm_headings(self, db):
        sid = _seed_full_session(db)
        s = get_session(sid, db_path=db)
        out = _format_session_md(s)

        # Required GFM headings per plan spec
        assert f"# Session #{sid}" in out
        assert "## Vehicle" in out
        assert "## Diagnosis" in out
        assert "## Repair Steps" in out
        # Metadata table present
        assert "| Confidence | Severity | AI model | Tokens |" in out
        assert "|---|---|---|---|" in out
        assert "| 0.87 | high | haiku | 1432 |" in out
        # Repair steps numbered
        assert "1. Check stator continuity" in out
        assert "2. Replace stator" in out

    def test_md_minimal_session_no_crash(self, db):
        sid = _seed_minimal_session(db)
        s = get_session(sid, db_path=db)
        out = _format_session_md(s)
        assert f"# Session #{sid}" in out
        assert "## Vehicle" in out
        # Missing data rendered as italic "none" markers
        assert "_none recorded_" in out or "_(none)_" in out
        # Metadata table still rendered with dashes
        assert "| - | - | - | - |" in out

    def test_formatters_handle_missing_repair_steps_field(self):
        """Defensive: formatters must not crash if `repair_steps` is absent
        entirely (e.g., raw dict not from session_repo)."""
        bare = {
            "id": 99,
            "status": "open",
            "vehicle_make": "Yamaha",
            "vehicle_model": "R6",
            "vehicle_year": 2006,
            "symptoms": [],
            "fault_codes": [],
            "diagnosis": None,
            "confidence": None,
            "severity": None,
            "created_at": "2026-04-17T10:00:00",
        }
        # None of these should raise.
        assert "Session #99" in _format_session_text(bare)
        assert "Session #99" in _format_session_md(bare)
        parsed = json.loads(_format_session_json(bare))
        assert parsed["id"] == 99

    def test_text_wraps_long_lines(self):
        """Long diagnosis text should be wrapped at ~80 cols."""
        long_diag = "A" * 200  # 200 chars of "A"
        session = {
            "id": 1, "status": "closed",
            "vehicle_make": "Kawasaki", "vehicle_model": "ZX6R", "vehicle_year": 2005,
            "symptoms": [], "fault_codes": [],
            "diagnosis": long_diag,
            "confidence": 0.5, "severity": "low",
            "repair_steps": [],
            "created_at": "2026-04-17T10:00:00",
        }
        out = _format_session_text(session)
        # No single line should exceed 85 cols (leave slack for bullet prefix).
        for line in out.split("\n"):
            assert len(line) <= 85, f"Line too long ({len(line)}): {line!r}"


# =============================================================================
# TestDiagnoseShowExport — CLI wiring
# =============================================================================


class TestDiagnoseShowExport:
    def test_format_txt_to_stdout(self, cli_db):
        sid = _seed_full_session(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, [
            "diagnose", "show", str(sid),
            "--format", "txt",
        ])
        assert r.exit_code == 0, r.output
        assert f"Session #{sid}" in r.output
        assert "Stator failure" in r.output
        # Plain text — no Rich panel border characters
        assert "╭" not in r.output and "╮" not in r.output

    def test_format_json_to_stdout(self, cli_db):
        sid = _seed_full_session(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, [
            "diagnose", "show", str(sid),
            "--format", "json",
        ])
        assert r.exit_code == 0, r.output
        parsed = json.loads(r.output)
        assert parsed["format_version"] == _REPORT_FORMAT_VERSION
        assert parsed["id"] == sid
        assert parsed["vehicle_make"] == "Harley-Davidson"

    def test_format_md_to_file(self, cli_db, tmp_path):
        sid = _seed_full_session(cli_db)
        from motodiag.cli.main import cli

        out_path = tmp_path / "report.md"
        runner = CliRunner()
        r = runner.invoke(cli, [
            "diagnose", "show", str(sid),
            "--format", "md",
            "--output", str(out_path),
        ])
        assert r.exit_code == 0, r.output
        assert out_path.exists()
        content = out_path.read_text(encoding="utf-8")
        assert f"# Session #{sid}" in content
        assert "## Repair Steps" in content
        # Confirmation message
        assert f"Saved to {out_path}" in r.output

    def test_format_txt_to_file(self, cli_db, tmp_path):
        sid = _seed_full_session(cli_db)
        from motodiag.cli.main import cli

        out_path = tmp_path / "report.txt"
        runner = CliRunner()
        r = runner.invoke(cli, [
            "diagnose", "show", str(sid),
            "--format", "txt",
            "--output", str(out_path),
        ])
        assert r.exit_code == 0, r.output
        assert out_path.exists()
        content = out_path.read_text(encoding="utf-8")
        assert f"Session #{sid}" in content
        assert "Stator failure" in content

    def test_missing_session_errors_cleanly(self, cli_db):
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, [
            "diagnose", "show", "99999",
            "--format", "json",
        ])
        assert r.exit_code != 0
        assert "not found" in r.output.lower()

    def test_overwrite_confirmation_declined(self, cli_db, tmp_path):
        """Without --yes, re-writing an existing file prompts and aborts on 'n'."""
        sid = _seed_full_session(cli_db)
        from motodiag.cli.main import cli

        out_path = tmp_path / "report.json"
        out_path.write_text("preexisting content", encoding="utf-8")

        runner = CliRunner()
        r = runner.invoke(
            cli,
            [
                "diagnose", "show", str(sid),
                "--format", "json",
                "--output", str(out_path),
            ],
            input="n\n",
        )
        assert r.exit_code != 0
        # File should be unchanged
        assert out_path.read_text(encoding="utf-8") == "preexisting content"

    def test_overwrite_with_yes_flag_skips_prompt(self, cli_db, tmp_path):
        sid = _seed_full_session(cli_db)
        from motodiag.cli.main import cli

        out_path = tmp_path / "report.json"
        out_path.write_text("preexisting content", encoding="utf-8")

        runner = CliRunner()
        r = runner.invoke(cli, [
            "diagnose", "show", str(sid),
            "--format", "json",
            "--output", str(out_path),
            "--yes",
        ])
        assert r.exit_code == 0, r.output
        content = out_path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert parsed["id"] == sid


# =============================================================================
# TestFileWriteErrors — edge paths for _write_report_to_file
# =============================================================================


class TestFileWriteErrors:
    def test_directory_as_output_errors(self, cli_db, tmp_path):
        """Pointing --output at an existing directory is a ClickException."""
        sid = _seed_full_session(cli_db)
        from motodiag.cli.main import cli

        # Click's Path(dir_okay=False) rejects dirs first, producing a nonzero
        # exit code. Either that guard or our own isdir check catches it.
        runner = CliRunner()
        r = runner.invoke(cli, [
            "diagnose", "show", str(sid),
            "--format", "json",
            "--output", str(tmp_path),  # tmp_path is a directory
        ])
        assert r.exit_code != 0
        assert (
            "directory" in r.output.lower()
            or "is a dir" in r.output.lower()
        )

    def test_parent_directory_auto_created(self, cli_db, tmp_path):
        """--output /some/new/nested/path.md creates the parent dirs."""
        sid = _seed_full_session(cli_db)
        from motodiag.cli.main import cli

        out_path = tmp_path / "reports" / "2026" / "april" / "session.md"
        assert not out_path.parent.exists()

        runner = CliRunner()
        r = runner.invoke(cli, [
            "diagnose", "show", str(sid),
            "--format", "md",
            "--output", str(out_path),
        ])
        assert r.exit_code == 0, r.output
        assert out_path.exists()
        assert out_path.parent.is_dir()

    def test_permission_error_surfaced(self, cli_db, tmp_path):
        """PermissionError on open() surfaces as ClickException with clear msg."""
        sid = _seed_full_session(cli_db)
        from motodiag.cli.main import cli

        # Simulate a PermissionError on open() — portable across Win/*nix
        # because we don't rely on real filesystem permissions (which are
        # fiddly on Windows running as admin).
        import builtins
        real_open = builtins.open
        out_path = tmp_path / "locked.txt"
        target = str(out_path)

        def raising_open(path, mode="r", *args, **kwargs):
            # Only intercept writes to the single target path; all other opens
            # (SQLite uses C-level open anyway, but pytest logs etc. must pass).
            if "w" in mode and str(path) == target:
                raise PermissionError(f"simulated: {path}")
            return real_open(path, mode, *args, **kwargs)

        runner = CliRunner()
        with patch("builtins.open", side_effect=raising_open):
            r = runner.invoke(cli, [
                "diagnose", "show", str(sid),
                "--format", "txt",
                "--output", str(out_path),
            ])
        assert r.exit_code != 0
        assert "permission denied" in r.output.lower()


# =============================================================================
# TestRegression — existing Phase 123 behavior must be intact
# =============================================================================


class TestRegression:
    def test_default_show_is_terminal_rendering(self, cli_db):
        """`diagnose show N` with no flags must produce the Rich Panel output
        exactly as in Phase 123."""
        sid = _seed_full_session(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["diagnose", "show", str(sid)])
        assert r.exit_code == 0, r.output
        # Rich Panels draw box-drawing chars; CliRunner captures them.
        # Session header phrasing matches Phase 123.
        assert f"Session #{sid}" in r.output
        assert "status:" in r.output
        assert "Vehicle:" in r.output
        assert "Stator failure" in r.output

    def test_terminal_format_with_output_warns_and_still_renders(self, cli_db, tmp_path):
        """--format terminal --output PATH should warn + keep terminal behavior,
        NOT write the file."""
        sid = _seed_full_session(cli_db)
        from motodiag.cli.main import cli

        out_path = tmp_path / "wont_be_written.txt"
        runner = CliRunner()
        r = runner.invoke(cli, [
            "diagnose", "show", str(sid),
            "--format", "terminal",
            "--output", str(out_path),
        ])
        assert r.exit_code == 0, r.output
        # Warning surfaced (exact text may vary by terminal width; just look
        # for a substring).
        assert "ignored" in r.output.lower() or "terminal" in r.output.lower()
        # And no file written.
        assert not out_path.exists()
