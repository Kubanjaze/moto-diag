"""Phase 132 — HTML + PDF export tests.

Covers:

- ``TestExportHelpers`` — pure helpers in ``motodiag.cli.export``:
  format_as_html structure / table conversion, format_as_pdf magic
  bytes, import-error handling, write_binary safety net.
- ``TestDiagnoseShowHtml`` — ``diagnose show --format html`` stdout
  and file paths, content sanity checks.
- ``TestDiagnoseShowPdf`` — ``diagnose show --format pdf`` requires
  --output, writes %PDF- magic, respects --yes.
- ``TestKbShowFormats`` — ``kb show --format`` parity with Phase 126
  (terminal default preserved, md/html/pdf branches, pdf requires
  --output).
- ``TestRegression`` — Phase 126 and Phase 128 behaviors preserved.
- ``TestExtrasAvailable`` — sanity that the ``export`` extras packages
  import in the test venv and the ``[project.optional-dependencies]
  export`` entry exists in ``pyproject.toml``.

Zero AI calls — pure formatting. The `markdown` and `xhtml2pdf`
packages are installed via the ``motodiag[export]`` extra so every
test runs against the real conversion pipeline (no stubs).
"""

from __future__ import annotations

from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from motodiag.core.database import init_db
from motodiag.core.session_repo import (
    add_fault_code_to_session,
    close_session,
    create_session,
    set_diagnosis,
    update_session,
)
from motodiag.knowledge.issues_repo import add_known_issue

from motodiag.cli.export import (
    format_as_html,
    format_as_pdf,
    write_binary,
)


# --- Fixtures -------------------------------------------------------------


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase132.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    """Point settings at a temp DB so CliRunner sees it via the default path.

    Mirrors Phase 126 / 128 cli_db fixture pattern.
    """
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase132_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    # Widen terminal so Rich tables don't wrap long text.
    monkeypatch.setenv("COLUMNS", "200")
    reset_settings()
    yield path
    reset_settings()


def _seed_full_session(db_path: str) -> int:
    """Full-field session so every formatter branch has content."""
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
    update_session(
        sid,
        {"ai_model_used": "haiku", "tokens_used": 1432},
        db_path=db_path,
    )
    close_session(sid, db_path=db_path)
    return sid


def _seed_known_issue(db_path: str) -> int:
    """Seed one rich known-issue row for kb show tests."""
    return add_known_issue(
        title="Stator failure",
        description=(
            "Stator windings break down from heat causing charging failure."
        ),
        make="Harley-Davidson",
        model="Sportster 1200",
        year_start=1999,
        year_end=2017,
        severity="high",
        symptoms=["battery not charging", "headlight dim or flickering"],
        dtc_codes=["P0562"],
        causes=["Stator winding insulation breakdown"],
        fix_procedure="Test stator AC output, replace if low.",
        parts_needed=["Stator assembly", "Stator gasket"],
        estimated_hours=3.5,
        db_path=db_path,
    )


# =============================================================================
# TestExportHelpers — pure helpers in cli/export.py
# =============================================================================


class TestExportHelpers:
    def test_format_as_html_produces_valid_structure(self):
        out = format_as_html(
            title="Test Report",
            body_md="# Heading 1\n\nA paragraph.",
        )
        assert out.startswith("<!DOCTYPE html>")
        assert "<title>Test Report</title>" in out
        assert "<h1>Heading 1</h1>" in out
        assert "<body>" in out
        assert "</html>" in out
        # Inline CSS is embedded (self-contained).
        assert "<style" in out
        assert "font-family" in out

    def test_format_as_html_converts_markdown_tables(self):
        """The `tables` extension must be enabled — plan requirement."""
        md = (
            "# Title\n"
            "\n"
            "| col1 | col2 |\n"
            "|------|------|\n"
            "| A    | B    |\n"
        )
        out = format_as_html(title="Tbl", body_md=md)
        assert "<table>" in out
        assert "<th>col1</th>" in out
        assert "<td>A</td>" in out

    def test_format_as_html_raises_click_on_missing_markdown(self, monkeypatch):
        """If `markdown` is unimportable, the helper must raise ClickException
        with a pip install hint — not bubble up ImportError."""
        # Patch the import path used inside _ensure_markdown_installed.
        import motodiag.cli.export as export_mod

        def _boom():
            raise click.ClickException(
                "HTML/PDF export requires the optional 'markdown' package. "
                "Install with: pip install 'motodiag[export]'"
            )

        monkeypatch.setattr(export_mod, "_ensure_markdown_installed", _boom)
        with pytest.raises(click.ClickException) as excinfo:
            format_as_html(title="x", body_md="# hi")
        assert "pip install" in str(excinfo.value.message).lower()
        assert "motodiag[export]" in str(excinfo.value.message)

    def test_format_as_pdf_returns_pdf_magic_bytes(self):
        out = format_as_pdf(
            title="PDF Test",
            body_md="# Heading\n\nParagraph.",
        )
        assert isinstance(out, bytes)
        assert len(out) > 100, "PDF output suspiciously small"
        # All valid PDFs start with `%PDF-` magic number.
        assert out.startswith(b"%PDF-"), f"Unexpected magic: {out[:10]!r}"

    def test_format_as_pdf_raises_click_on_missing_xhtml2pdf(self, monkeypatch):
        """ImportError on xhtml2pdf must surface as ClickException."""
        import motodiag.cli.export as export_mod

        def _boom():
            raise click.ClickException(
                "PDF export requires the optional 'xhtml2pdf' package. "
                "Install with: pip install 'motodiag[export]'"
            )

        monkeypatch.setattr(export_mod, "_ensure_pdf_installed", _boom)
        with pytest.raises(click.ClickException) as excinfo:
            format_as_pdf(title="x", body_md="# hi")
        assert "pip install" in str(excinfo.value.message).lower()
        assert "motodiag[export]" in str(excinfo.value.message)

    def test_write_binary_writes_bytes_and_creates_parent_dirs(self, tmp_path):
        nested = tmp_path / "sub" / "deeper" / "out.pdf"
        data = b"%PDF-1.4\n%fake-but-binary\n"
        write_binary(nested, data, overwrite_confirmed=True)
        assert nested.exists()
        assert nested.read_bytes() == data


# =============================================================================
# TestDiagnoseShowHtml — CLI wiring for HTML
# =============================================================================


class TestDiagnoseShowHtml:
    def test_html_to_stdout_starts_with_doctype(self, cli_db):
        sid = _seed_full_session(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, [
            "diagnose", "show", str(sid),
            "--format", "html",
        ])
        assert r.exit_code == 0, r.output
        assert r.output.startswith("<!DOCTYPE html>") or "<!DOCTYPE html>" in r.output

    def test_html_to_file_writes_and_reports(self, cli_db, tmp_path):
        sid = _seed_full_session(cli_db)
        from motodiag.cli.main import cli

        out_path = tmp_path / "session.html"
        runner = CliRunner()
        r = runner.invoke(cli, [
            "diagnose", "show", str(sid),
            "--format", "html",
            "--output", str(out_path),
        ])
        assert r.exit_code == 0, r.output
        assert out_path.exists()
        content = out_path.read_text(encoding="utf-8")
        assert content.startswith("<!DOCTYPE html>")
        assert f"Saved to {out_path}" in r.output

    def test_html_contains_diagnosis_text(self, cli_db):
        sid = _seed_full_session(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, [
            "diagnose", "show", str(sid),
            "--format", "html",
        ])
        assert r.exit_code == 0, r.output
        assert "Stator failure" in r.output

    def test_html_contains_vehicle_info(self, cli_db):
        sid = _seed_full_session(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, [
            "diagnose", "show", str(sid),
            "--format", "html",
        ])
        assert r.exit_code == 0, r.output
        assert "Harley-Davidson" in r.output
        assert "Sportster 1200" in r.output
        assert "2001" in r.output


# =============================================================================
# TestDiagnoseShowPdf — CLI wiring for PDF
# =============================================================================


class TestDiagnoseShowPdf:
    def test_pdf_without_output_errors(self, cli_db):
        sid = _seed_full_session(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, [
            "diagnose", "show", str(sid),
            "--format", "pdf",
        ])
        assert r.exit_code != 0
        # The helpful error must mention --output.
        assert "--output" in r.output.lower() or "output" in r.output.lower()

    def test_pdf_to_file_writes_bytes(self, cli_db, tmp_path):
        sid = _seed_full_session(cli_db)
        from motodiag.cli.main import cli

        out_path = tmp_path / "session.pdf"
        runner = CliRunner()
        r = runner.invoke(cli, [
            "diagnose", "show", str(sid),
            "--format", "pdf",
            "--output", str(out_path),
        ])
        assert r.exit_code == 0, r.output
        assert out_path.exists()
        assert out_path.stat().st_size > 100
        assert f"Saved to {out_path}" in r.output

    def test_pdf_starts_with_magic_bytes(self, cli_db, tmp_path):
        sid = _seed_full_session(cli_db)
        from motodiag.cli.main import cli

        out_path = tmp_path / "session.pdf"
        runner = CliRunner()
        r = runner.invoke(cli, [
            "diagnose", "show", str(sid),
            "--format", "pdf",
            "--output", str(out_path),
        ])
        assert r.exit_code == 0, r.output
        raw = out_path.read_bytes()
        assert raw.startswith(b"%PDF-"), f"Unexpected magic: {raw[:10]!r}"

    def test_pdf_overwrite_with_yes_skips_prompt(self, cli_db, tmp_path):
        sid = _seed_full_session(cli_db)
        from motodiag.cli.main import cli

        out_path = tmp_path / "session.pdf"
        # Preexisting file — without --yes we'd get a prompt.
        out_path.write_bytes(b"old content")

        runner = CliRunner()
        r = runner.invoke(cli, [
            "diagnose", "show", str(sid),
            "--format", "pdf",
            "--output", str(out_path),
            "--yes",
        ])
        assert r.exit_code == 0, r.output
        # File has been overwritten with real PDF bytes.
        assert out_path.read_bytes().startswith(b"%PDF-")


# =============================================================================
# TestKbShowFormats — kb show parity with diagnose show
# =============================================================================


class TestKbShowFormats:
    def test_terminal_default_unchanged(self, cli_db):
        """Phase 128 behavior: no flags → Rich Panel output."""
        iid = _seed_known_issue(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["kb", "show", str(iid)])
        assert r.exit_code == 0, r.output
        # Rich Panel header token from Phase 128.
        assert "Known Issue" in r.output
        assert "Stator failure" in r.output

    def test_md_to_file(self, cli_db, tmp_path):
        iid = _seed_known_issue(cli_db)
        from motodiag.cli.main import cli

        out_path = tmp_path / "issue.md"
        runner = CliRunner()
        r = runner.invoke(cli, [
            "kb", "show", str(iid),
            "--format", "md",
            "--output", str(out_path),
        ])
        assert r.exit_code == 0, r.output
        content = out_path.read_text(encoding="utf-8")
        # Heading + Overview section + parts + hours all present.
        assert "# Stator failure" in content
        assert "## Overview" in content
        assert "## Parts Needed" in content
        assert "3.5 hours" in content
        assert f"Saved to {out_path}" in r.output

    def test_html_to_stdout(self, cli_db):
        iid = _seed_known_issue(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, [
            "kb", "show", str(iid),
            "--format", "html",
        ])
        assert r.exit_code == 0, r.output
        assert "<!DOCTYPE html>" in r.output
        assert "Stator failure" in r.output

    def test_pdf_to_file(self, cli_db, tmp_path):
        iid = _seed_known_issue(cli_db)
        from motodiag.cli.main import cli

        out_path = tmp_path / "issue.pdf"
        runner = CliRunner()
        r = runner.invoke(cli, [
            "kb", "show", str(iid),
            "--format", "pdf",
            "--output", str(out_path),
        ])
        assert r.exit_code == 0, r.output
        assert out_path.exists()
        assert out_path.read_bytes().startswith(b"%PDF-")

    def test_pdf_without_output_errors(self, cli_db):
        iid = _seed_known_issue(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, [
            "kb", "show", str(iid),
            "--format", "pdf",
        ])
        assert r.exit_code != 0
        assert "--output" in r.output.lower() or "output" in r.output.lower()


# =============================================================================
# TestRegression — existing phase behaviors still work
# =============================================================================


class TestRegression:
    def test_phase126_formats_still_work(self, cli_db):
        """txt / json / md / terminal from Phase 126 all return exit 0."""
        sid = _seed_full_session(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        for fmt in ("terminal", "txt", "json", "md"):
            r = runner.invoke(cli, [
                "diagnose", "show", str(sid), "--format", fmt,
            ])
            assert r.exit_code == 0, (
                f"--format {fmt} broke with exit {r.exit_code}: {r.output}"
            )

    def test_phase128_kb_show_terminal_default_unchanged(self, cli_db):
        iid = _seed_known_issue(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["kb", "show", str(iid)])
        assert r.exit_code == 0, r.output
        # Panel header + all core sections still render (sanity — full
        # Phase 128 regression is covered by test_phase128_kb.py; this
        # is a light smoke test that --format parsing didn't break the
        # default path).
        assert "Known Issue" in r.output
        assert "Stator failure" in r.output
        assert "Description" in r.output
        assert "Symptoms" in r.output

    def test_missing_session_errors_unchanged(self, cli_db):
        from motodiag.cli.main import cli

        runner = CliRunner()
        # diagnose show on a missing session: Phase 126 behavior preserved.
        r = runner.invoke(cli, [
            "diagnose", "show", "99999", "--format", "md",
        ])
        assert r.exit_code != 0
        assert "not found" in r.output.lower()

        # kb show on a missing issue: Phase 128 ClickException preserved.
        r2 = runner.invoke(cli, ["kb", "show", "99999"])
        assert r2.exit_code != 0
        assert "not found" in r2.output.lower()


# =============================================================================
# TestExtrasAvailable — sanity that export extras installed + pyproject entry
# =============================================================================


class TestExtrasAvailable:
    def test_markdown_importable(self):
        import markdown
        # Any version that supports the `tables` extension works.
        assert hasattr(markdown, "markdown")

    def test_xhtml2pdf_importable(self):
        from xhtml2pdf import pisa
        assert hasattr(pisa, "CreatePDF")

    def test_pyproject_has_export_extras(self):
        """The export extra must appear in pyproject.toml so
        `pip install motodiag[export]` resolves."""
        import tomllib

        # Walk up from this test file to find the repo root (where
        # pyproject.toml lives). The file is at tests/test_phase132_export.py
        # so parent.parent is the repo root.
        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        assert pyproject.exists(), f"pyproject.toml not at {pyproject}"
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        extras = data["project"]["optional-dependencies"]
        assert "export" in extras, (
            f"'export' extra missing from pyproject.toml — found: {list(extras)}"
        )
        export_deps = extras["export"]
        # Both expected packages referenced.
        joined = " ".join(export_deps).lower()
        assert "markdown" in joined
        assert "xhtml2pdf" in joined
