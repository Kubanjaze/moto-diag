"""Phase 129 — Rich terminal UI polish: theme module tests.

Covers:
- ``TestConsole`` — ``get_console`` singleton + ``reset_console``
  helper; respects ``NO_COLOR`` and ``COLUMNS`` env vars.
- ``TestColorMaps`` — severity / status / tier dicts and the
  parallel ``*_style`` / ``format_*`` helpers.
- ``TestIcons`` — five icon constants exported and non-empty.
- ``TestStatusSpinner`` — ``theme.status()`` returns a usable
  context manager that doesn't crash in non-TTY mode.
- ``TestIntegration`` — smoke test across the migrated CLI
  modules (``diagnose quick`` mocked, ``kb list`` empty-filter,
  ``code --help``, ``intake quota``, ``tier``) to prove the
  ``Console`` swap didn't break existing renderers.

All tests are DB-only. Zero AI calls — ``diagnose quick`` is
mocked via ``_default_diagnose_fn``.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from click.testing import CliRunner
from rich.console import Console

from motodiag.cli import theme
from motodiag.cli.theme import (
    ICON_FAIL,
    ICON_INFO,
    ICON_LOADING,
    ICON_OK,
    ICON_WARN,
    SEVERITY_COLORS,
    STATUS_COLORS,
    TIER_COLORS,
    format_severity,
    format_status,
    format_tier,
    get_console,
    reset_console,
    severity_style,
    status_style,
    tier_style,
)
from motodiag.core.database import init_db


# --- Fixtures ---------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_console_around_every_test():
    """Guarantee a clean Console singleton on every test boundary.

    Several tests mutate ``NO_COLOR`` / ``COLUMNS`` via
    ``monkeypatch.setenv``. Without this autouse reset the singleton
    constructed in one test would bleed into the next. Parallel to
    how ``reset_settings()`` is called in other phase test modules.
    """
    reset_console()
    yield
    reset_console()


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    """Point settings at a temp DB and reset both singletons.

    Mirrors the Phase 128 ``cli_db`` fixture but adds a
    ``reset_console()`` teardown so any ``NO_COLOR`` / ``COLUMNS``
    mutation inside a test doesn't leak into the next one.
    """
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase129_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    # Widen the virtual terminal so Rich tables do not wrap across
    # multiple lines and break substring assertions.
    monkeypatch.setenv("COLUMNS", "200")
    reset_settings()
    reset_console()
    yield path
    reset_settings()
    reset_console()


# =============================================================================
# TestConsole — singleton, env-var respect
# =============================================================================


class TestConsole:
    def test_singleton_returns_same_instance(self, monkeypatch):
        """Two calls to ``get_console()`` return the same object."""
        # Clear env influences so construction is deterministic.
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("COLUMNS", raising=False)
        reset_console()

        c1 = get_console()
        c2 = get_console()
        assert c1 is c2, "get_console must return a singleton"
        assert isinstance(c1, Console)

    def test_reset_console_clears_singleton(self, monkeypatch):
        """After ``reset_console()`` the next call builds a fresh Console."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("COLUMNS", raising=False)
        reset_console()

        first = get_console()
        reset_console()
        second = get_console()
        assert first is not second, (
            "reset_console() should force a new Console on the next call"
        )

    def test_no_color_env_disables_color(self, monkeypatch):
        """``NO_COLOR=1`` → ``Console.no_color is True`` (per the spec)."""
        monkeypatch.setenv("NO_COLOR", "1")
        reset_console()
        c = get_console()
        assert c.no_color is True

    def test_columns_env_sets_width(self, monkeypatch):
        """``COLUMNS=200`` → Console ``width`` matches that value."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("COLUMNS", "200")
        reset_console()
        c = get_console()
        # Rich exposes the configured width directly on the Console.
        assert c.width == 200

    def test_default_construction_no_env(self, monkeypatch):
        """No env vars → Console constructs without raising.

        ``no_color`` defaults to False (Rich's own default when we
        don't pass ``no_color=True``). The width falls back to Rich's
        auto-detection so we only assert the type.
        """
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("COLUMNS", raising=False)
        reset_console()
        c = get_console()
        assert isinstance(c, Console)
        # no_color was never set → Rich default is False.
        assert c.no_color is False


# =============================================================================
# TestColorMaps — severity / status / tier style + format helpers
# =============================================================================


class TestColorMaps:
    def test_severity_map_has_all_expected_keys(self):
        """All documented severity levels plus None fallback present."""
        for key in ("critical", "high", "medium", "low", "info"):
            assert key in SEVERITY_COLORS, (
                f"severity '{key}' missing from SEVERITY_COLORS"
            )
        assert None in SEVERITY_COLORS, (
            "None fallback missing from SEVERITY_COLORS"
        )
        # Concrete style values per the plan.
        assert SEVERITY_COLORS["critical"] == "red"
        assert SEVERITY_COLORS["high"] == "orange1"
        assert SEVERITY_COLORS["medium"] == "yellow"
        assert SEVERITY_COLORS["low"] == "green"
        assert SEVERITY_COLORS["info"] == "cyan"
        assert SEVERITY_COLORS[None] == "dim"

    def test_unknown_severity_falls_back_to_dim(self):
        """``severity_style`` on an unknown value returns ``"dim"``.

        The CLI must never crash on an unexpected knowledge-base
        severity string — mechanics may load third-party JSON with
        non-standard levels.
        """
        assert severity_style("bananas") == "dim"
        assert severity_style("") == "dim"
        assert severity_style(None) == "dim"
        # severity_style is case-insensitive
        assert severity_style("CRITICAL") == "red"

    def test_status_map_and_helper(self):
        """status map exposes open/diagnosed/closed/cancelled + fallback."""
        for key in ("open", "diagnosed", "closed", "cancelled"):
            assert key in STATUS_COLORS
        assert STATUS_COLORS["open"] == "yellow"
        assert STATUS_COLORS["closed"] == "green"
        assert status_style("open") == "yellow"
        assert status_style("unknown_status") == "dim"
        assert status_style(None) == "dim"

    def test_tier_map_and_helper(self):
        """tier map exposes individual/shop/company + fallback."""
        assert TIER_COLORS["individual"] == "cyan"
        assert TIER_COLORS["shop"] == "yellow"
        assert TIER_COLORS["company"] == "magenta"
        assert tier_style("individual") == "cyan"
        assert tier_style("shop") == "yellow"
        assert tier_style("company") == "magenta"
        assert tier_style("nonexistent") == "dim"
        assert tier_style(None) == "dim"

    def test_format_severity_markup_string(self):
        """``format_severity('critical')`` returns exactly ``"[red]critical[/red]"``."""
        assert format_severity("critical") == "[red]critical[/red]"
        assert format_severity("high") == "[orange1]high[/orange1]"
        assert format_severity("low") == "[green]low[/green]"
        # Unknown → dim placeholder, original text preserved.
        assert format_severity("bogus") == "[dim]bogus[/dim]"
        # None → dim with "-" placeholder
        assert format_severity(None) == "[dim]-[/dim]"

    def test_format_status_and_tier_parallel(self):
        """``format_status`` / ``format_tier`` follow the same markup shape."""
        assert format_status("open") == "[yellow]open[/yellow]"
        assert format_status("closed") == "[green]closed[/green]"
        assert format_status(None) == "[dim]-[/dim]"
        assert format_tier("individual") == "[cyan]individual[/cyan]"
        assert format_tier("shop") == "[yellow]shop[/yellow]"
        assert format_tier("company") == "[magenta]company[/magenta]"
        assert format_tier(None) == "[dim]-[/dim]"


# =============================================================================
# TestIcons — unicode glyph constants
# =============================================================================


class TestIcons:
    def test_all_five_icons_non_empty_strings(self):
        """Every icon is a non-empty string — no accidental ``None``/``""``."""
        for icon in (ICON_OK, ICON_WARN, ICON_FAIL, ICON_INFO, ICON_LOADING):
            assert isinstance(icon, str)
            assert len(icon) > 0, (
                f"icon {icon!r} is empty — theme.py icon constants must be "
                "non-empty strings"
            )

    def test_icons_are_importable_individually(self):
        """The five icons are importable by name from ``theme`` — protects
        against an accidental rename or removal of any one of them."""
        # Re-import via the module to confirm the attribute paths.
        assert theme.ICON_OK == ICON_OK
        assert theme.ICON_WARN == ICON_WARN
        assert theme.ICON_FAIL == ICON_FAIL
        assert theme.ICON_INFO == ICON_INFO
        assert theme.ICON_LOADING == ICON_LOADING


# =============================================================================
# TestStatusSpinner — spinner context manager
# =============================================================================


class TestStatusSpinner:
    def test_status_returns_context_manager(self):
        """``theme.status(msg)`` returns a Rich ``Status`` — a context manager."""
        ctx = theme.status("Analyzing symptoms...")
        # Rich's Status exposes __enter__/__exit__ for the ``with`` protocol.
        assert hasattr(ctx, "__enter__")
        assert hasattr(ctx, "__exit__")
        # Clean up — call the exit explicitly since we didn't enter it.
        # (Status.__init__ doesn't start the live display, so no teardown needed.)

    def test_status_usable_as_context_manager_in_non_tty(self):
        """Using ``theme.status`` as a ``with`` block doesn't raise in non-TTY mode.

        CliRunner tests execute under a non-TTY stream. Rich
        auto-detects this and suppresses the spinner animation so the
        block is a safe no-op. We assert the block enters/exits
        without crashing rather than asserting any output — there
        simply isn't any to check.
        """
        # Force a fresh Console without any env that would change behavior.
        reset_console()
        with theme.status("working..."):
            # Minimal work — proves the block body runs.
            _ = 1 + 1
        # If we got here without exception, the context manager works.


# =============================================================================
# TestIntegration — existing CLI commands still render after the migration
# =============================================================================


class TestIntegration:
    """Smoke tests that prove swapping ``Console()`` for ``get_console()``
    did not break any existing CLI renderer. Each test invokes one of
    the migrated commands through CliRunner and asserts ``exit_code == 0``.

    These are NOT exhaustive behavior tests — those live in the
    per-phase suites (Phase 123 diagnose, Phase 124 code, Phase 128 kb,
    etc). This is a regression guard specifically for the Phase 129
    migration.
    """

    def test_diagnose_quick_renders(self, cli_db):
        """``diagnose quick`` with a mocked AI call still renders correctly."""
        from motodiag.cli.main import cli
        from motodiag.core.models import VehicleBase, ProtocolType
        from motodiag.vehicles.registry import add_vehicle
        from tests.test_phase123_diagnose import (  # type: ignore[import-not-found]
            make_diagnose_fn,
            make_response,
        )

        # Seed a vehicle so the command has something to resolve.
        add_vehicle(
            VehicleBase(
                make="Harley-Davidson",
                model="Sportster 1200",
                year=2001,
                engine_cc=1200,
                protocol=ProtocolType.J1850,
            ),
            db_path=cli_db,
        )

        fn = make_diagnose_fn(make_response(confidence=0.88))
        with patch("motodiag.cli.diagnose._default_diagnose_fn", fn):
            runner = CliRunner()
            r = runner.invoke(
                cli,
                [
                    "diagnose", "quick",
                    "--vehicle-id", "1",
                    "--symptoms", "won't start",
                ],
            )
            assert r.exit_code == 0, (
                f"diagnose quick returned {r.exit_code}: {r.output}"
            )
            # Proof-of-rendering: the session acknowledgement surfaces.
            assert "Session #" in r.output

    def test_kb_list_empty_filter_message(self, cli_db):
        """``kb list`` with no seeds prints the empty-knowledge-base message."""
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["kb", "list"])
        assert r.exit_code == 0, r.output
        # With no seed data, the empty-state message should mention the
        # knowledge base (exact wording is Phase 128 — "No known issues
        # in the knowledge base yet.").
        assert "knowledge base" in r.output.lower()

    def test_code_help_renders(self, cli_db):
        """``code --help`` renders without crashing."""
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["code", "--help"])
        assert r.exit_code == 0, r.output
        # The help text should include one of the flag names.
        assert "--explain" in r.output

    def test_intake_quota_renders(self, cli_db):
        """``intake quota`` prints tier/quota info without crashing."""
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["intake", "quota"])
        assert r.exit_code == 0, r.output
        # Must mention the tier name somewhere in the output.
        assert "tier" in r.output.lower()

    def test_tier_command_renders(self, cli_db):
        """``tier`` prints the tier panel + limits + features tables."""
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["tier"])
        assert r.exit_code == 0, r.output
        # The panel title includes the word "tier" regardless of
        # current-tier value.
        assert "tier" in r.output.lower()
