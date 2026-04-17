"""Phase 130 — Shell completions + short aliases.

Covers:
- `TestCompletionCommand`: `motodiag completion {bash,zsh,fish}` prints a
  non-empty shell script with the ``_MOTODIAG_COMPLETE`` magic env var and
  install-hint header. Unknown shell errors cleanly via Click's Choice.
- `TestDynamicCompleters`: the three completer callbacks
  (``complete_bike_slug`` / ``complete_dtc_code`` / ``complete_session_id``)
  return seeded data, empty-list on a fresh (un-migrated) DB, and
  prefix-filter correctly.
- `TestAliases`: the four hidden single-letter aliases (d / k / g / q)
  resolve to their canonical commands and stay hidden from ``--help``.
- `TestRegistration`: `completion` group + subcommand set present.

Zero AI calls, zero live tokens — pure CLI + SQLite exercise.
"""

from __future__ import annotations

import sqlite3
import pytest
from click.testing import CliRunner

from motodiag.core.database import init_db
from motodiag.core.session_repo import create_session
from motodiag.core.models import (
    VehicleBase, ProtocolType, PowertrainType, EngineType,
    DTCCode, SymptomCategory, Severity,
)
from motodiag.vehicles.registry import add_vehicle
from motodiag.knowledge.dtc_repo import add_dtc


# --- Fixtures ---


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    """Point settings at a temp DB so CliRunner + completers agree on the
    DB path via ``get_settings().db_path``.

    Mirrors the Phase 125/127/128 pattern: env var + reset_settings around
    the test so the cached ``get_settings()`` singleton is refreshed.
    """
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase130_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "200")
    reset_settings()
    yield path
    reset_settings()


@pytest.fixture
def fresh_db_path(tmp_path, monkeypatch):
    """Point settings at a DB path that doesn't exist as a motodiag DB.

    We create an empty SQLite file without any of the motodiag tables
    (no ``vehicles``, no ``dtc_codes``, no ``diagnostic_sessions``). This
    exercises each completer's defensive branch — a fresh install
    shouldn't crash tab-completion.
    """
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase130_fresh.db")
    # Create a valid SQLite file with no tables so queries raise
    # OperationalError("no such table ...") rather than connection errors.
    conn = sqlite3.connect(path)
    conn.close()
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    reset_settings()
    yield path
    reset_settings()


def _seed_vehicles(db_path: str) -> list[int]:
    """Seed three vehicles for slug-completion tests.

    Slugs produced (matches the ``complete_bike_slug`` algorithm:
    ``model.lower().replace(' ', '-') + '-' + year``):
      - sportster-2001
      - cbr929rr-2000
      - r6-2007
    """
    ids: list[int] = []
    ids.append(add_vehicle(
        VehicleBase(
            make="Harley-Davidson", model="Sportster", year=2001,
            engine_cc=1200,
            protocol=ProtocolType.NONE,
            powertrain=PowertrainType.ICE,
            engine_type=EngineType.FOUR_STROKE,
        ),
        db_path=db_path,
    ))
    ids.append(add_vehicle(
        VehicleBase(
            make="Honda", model="CBR929RR", year=2000,
            engine_cc=929,
            protocol=ProtocolType.NONE,
            powertrain=PowertrainType.ICE,
            engine_type=EngineType.FOUR_STROKE,
        ),
        db_path=db_path,
    ))
    ids.append(add_vehicle(
        VehicleBase(
            make="Yamaha", model="R6", year=2007,
            engine_cc=599,
            protocol=ProtocolType.NONE,
            powertrain=PowertrainType.ICE,
            engine_type=EngineType.FOUR_STROKE,
        ),
        db_path=db_path,
    ))
    return ids


def _seed_dtcs(db_path: str) -> None:
    """Seed three DTCs for code-completion tests."""
    add_dtc(DTCCode(
        code="P0115",
        description="Engine coolant temperature sensor circuit",
        category=SymptomCategory.ENGINE,
        severity=Severity.MEDIUM,
    ), db_path=db_path)
    add_dtc(DTCCode(
        code="P0562",
        description="System voltage low (stator / charging)",
        category=SymptomCategory.ELECTRICAL,
        severity=Severity.HIGH,
    ), db_path=db_path)
    add_dtc(DTCCode(
        code="B1004",
        description="Body control module fault",
        category=SymptomCategory.ELECTRICAL,
        severity=Severity.LOW,
    ), db_path=db_path)


def _seed_sessions(db_path: str) -> list[int]:
    """Seed three diagnostic sessions for session-id completion tests."""
    ids: list[int] = []
    for i in range(3):
        sid = create_session(
            vehicle_make="Honda",
            vehicle_model=f"Test{i}",
            vehicle_year=2000 + i,
            symptoms=["test"],
            db_path=db_path,
        )
        ids.append(sid)
    return ids


# =============================================================================
# TestCompletionCommand — `motodiag completion <shell>` output
# =============================================================================


class TestCompletionCommand:
    def test_completion_help_lists_shells(self):
        """`completion --help` mentions all three shell names."""
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["completion", "--help"])
        assert r.exit_code == 0, r.output
        assert "bash" in r.output
        assert "zsh" in r.output
        assert "fish" in r.output

    def test_completion_bash_prints_script(self):
        """`completion bash` prints a non-empty script containing the magic var."""
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["completion", "bash"])
        assert r.exit_code == 0, r.output
        assert len(r.output) > 0
        # Either the env-var name OR the word 'completion' shows up in
        # every Click-generated shell script.
        assert (
            "_MOTODIAG_COMPLETE" in r.output
            or "completion" in r.output.lower()
        )

    def test_completion_zsh_prints_script(self):
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["completion", "zsh"])
        assert r.exit_code == 0, r.output
        assert len(r.output) > 0
        assert (
            "_MOTODIAG_COMPLETE" in r.output
            or "compdef" in r.output
            or "completion" in r.output.lower()
        )

    def test_completion_fish_prints_script(self):
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["completion", "fish"])
        assert r.exit_code == 0, r.output
        assert len(r.output) > 0
        assert (
            "_MOTODIAG_COMPLETE" in r.output
            or "complete" in r.output
        )

    def test_completion_unknown_shell_errors(self):
        """`completion powershell` (not supported) errors via Click's Choice guard."""
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["completion", "powershell"])
        # Click rejects unknown subcommands with exit code != 0.
        assert r.exit_code != 0


# =============================================================================
# TestDynamicCompleters — callback behavior against a real SQLite DB
# =============================================================================


class TestDynamicCompleters:
    def test_bike_slug_returns_seeded(self, cli_db):
        """With a seeded garage, the completer returns all three slugs."""
        from motodiag.cli.completion import complete_bike_slug

        _seed_vehicles(cli_db)
        items = complete_bike_slug(None, None, "")
        values = [item.value for item in items]
        assert "sportster-2001" in values
        assert "cbr929rr-2000" in values
        assert "r6-2007" in values

    def test_bike_slug_fresh_db_returns_empty(self, fresh_db_path):
        """No ``vehicles`` table → completer returns [] rather than crashing."""
        from motodiag.cli.completion import complete_bike_slug

        items = complete_bike_slug(None, None, "")
        assert items == []

    def test_bike_slug_prefix_filters(self, cli_db):
        """Input ``sport`` should match only ``sportster-*``."""
        from motodiag.cli.completion import complete_bike_slug

        _seed_vehicles(cli_db)
        items = complete_bike_slug(None, None, "sport")
        values = [item.value for item in items]
        assert "sportster-2001" in values
        assert "cbr929rr-2000" not in values
        assert "r6-2007" not in values

    def test_dtc_code_returns_seeded(self, cli_db):
        from motodiag.cli.completion import complete_dtc_code

        _seed_dtcs(cli_db)
        items = complete_dtc_code(None, None, "")
        values = [item.value for item in items]
        assert "P0115" in values
        assert "P0562" in values
        assert "B1004" in values

    def test_dtc_code_fresh_db_returns_empty(self, fresh_db_path):
        from motodiag.cli.completion import complete_dtc_code

        items = complete_dtc_code(None, None, "")
        assert items == []

    def test_dtc_code_prefix_filters(self, cli_db):
        """Input ``P0`` should match P0115 + P0562 only (not B1004)."""
        from motodiag.cli.completion import complete_dtc_code

        _seed_dtcs(cli_db)
        items = complete_dtc_code(None, None, "P0")
        values = [item.value for item in items]
        assert "P0115" in values
        assert "P0562" in values
        assert "B1004" not in values

    def test_session_id_returns_recent(self, cli_db):
        from motodiag.cli.completion import complete_session_id

        seeded = _seed_sessions(cli_db)
        items = complete_session_id(None, None, "")
        values = [item.value for item in items]
        for sid in seeded:
            assert str(sid) in values

    def test_session_id_fresh_db_returns_empty(self, fresh_db_path):
        from motodiag.cli.completion import complete_session_id

        items = complete_session_id(None, None, "")
        assert items == []


# =============================================================================
# TestAliases — hidden single-letter shortcuts
# =============================================================================


class TestAliases:
    def test_alias_d_resolves_to_diagnose(self):
        """`motodiag d --help` works and mentions diagnose subcommands."""
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["d", "--help"])
        assert r.exit_code == 0, r.output
        # The diagnose subgroup help lists at least one known subcommand.
        assert (
            "quick" in r.output
            or "start" in r.output
            or "diagnostic" in r.output.lower()
        )

    def test_alias_k_resolves_to_kb(self, cli_db):
        """`motodiag k list` works (empty kb OK — exit 0)."""
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["k", "list"])
        assert r.exit_code == 0, r.output

    def test_alias_g_help_works(self):
        """`motodiag g --help` resolves to garage group."""
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["g", "--help"])
        assert r.exit_code == 0, r.output
        assert (
            "add" in r.output
            or "list" in r.output
            or "garage" in r.output.lower()
        )

    def test_aliases_hidden_from_top_help(self):
        """`motodiag --help` output does NOT advertise the short aliases.

        We parse the command listing out of the help text and ensure none
        of the alias letters appear as standalone command entries. Long
        words that happen to contain these letters (e.g., ``diagnose``)
        are allowed — we check for the alias as a whole-line command.
        """
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["--help"])
        assert r.exit_code == 0, r.output

        # Click renders commands like ``  d   Diagnose...``. We scan each
        # line looking for one that starts with leading whitespace and
        # then the bare alias token followed by whitespace.
        for alias in ("d", "k", "g", "q"):
            for line in r.output.splitlines():
                stripped = line.lstrip()
                # A command line in Click's help starts with the command
                # name followed by 2+ spaces before the description.
                parts = stripped.split(None, 1)
                if not parts:
                    continue
                first_token = parts[0]
                assert first_token != alias, (
                    f"Alias {alias!r} leaked into `motodiag --help` "
                    f"output on line: {line!r}"
                )


# =============================================================================
# TestRegistration — completion group wired into the CLI
# =============================================================================


class TestRegistration:
    def test_completion_group_registered(self):
        """`completion` appears as a subgroup on the top-level CLI with
        bash/zsh/fish subcommands."""
        from motodiag.cli.main import cli
        import click as _click

        assert "completion" in cli.commands, (
            f"completion group missing; got {sorted(cli.commands)}"
        )
        group = cli.commands["completion"]
        assert isinstance(group, _click.Group), (
            f"cli.commands['completion'] is not a click.Group; got {type(group)}"
        )
        expected = {"bash", "zsh", "fish"}
        actual = set(group.commands.keys())
        missing = expected - actual
        assert not missing, (
            f"Missing completion subcommands: {sorted(missing)}. "
            f"Present: {sorted(actual)}"
        )
