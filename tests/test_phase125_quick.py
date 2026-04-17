"""Phase 125 — Quick Diagnosis Mode: bike slug + top-level shortcut.

Covers:
- `_parse_slug` splitting rules (year / no year / out-of-range / no hyphen)
- `_resolve_bike_slug` match priorities (exact model, exact make, partial,
  year filter, case-insensitive, ambiguity ordering, None on miss)
- `diagnose quick --bike SLUG`: happy path, unknown slug, both IDs, neither
- `motodiag quick "<symptoms>"` top-level shortcut: positional symptoms,
  flags pass-through, missing symptom
- Regression: existing `diagnose quick --vehicle-id N` still works

Zero live API tokens: all AI calls mocked via
`patch("motodiag.cli.diagnose._default_diagnose_fn", fn)`.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from motodiag.core.database import init_db
from motodiag.core.models import VehicleBase, ProtocolType
from motodiag.core.session_repo import list_sessions
from motodiag.vehicles.registry import add_vehicle

from motodiag.cli.diagnose import (
    _parse_slug,
    _resolve_bike_slug,
    SLUG_YEAR_MIN,
    SLUG_YEAR_MAX,
)

# Reuse the Phase 123 helpers so mocked responses match the existing shape.
from tests.test_phase123_diagnose import (  # type: ignore[import-not-found]
    make_diagnose_fn,
    make_response,
)


# --- Fixtures ---


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase125.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(db, monkeypatch):
    """Mirrors Phase 123 fixture: point settings at the temp DB."""
    from motodiag.core.config import reset_settings
    monkeypatch.setenv("MOTODIAG_DB_PATH", db)
    reset_settings()
    yield db
    reset_settings()


def _seed_sportster(db_path: str) -> int:
    return add_vehicle(VehicleBase(
        make="Harley-Davidson", model="Sportster 1200", year=2001,
        engine_cc=1200, protocol=ProtocolType.J1850,
    ), db_path=db_path)


def _seed_cbr(db_path: str) -> int:
    return add_vehicle(VehicleBase(
        make="Honda", model="CBR929RR", year=2000,
        engine_cc=929, protocol=ProtocolType.K_LINE,
    ), db_path=db_path)


# --- _parse_slug ---


class TestParseSlug:
    def test_slug_with_year(self):
        assert _parse_slug("sportster-2001") == ("sportster", 2001)

    def test_slug_with_model_year(self):
        assert _parse_slug("cbr929-2000") == ("cbr929", 2000)

    def test_slug_no_hyphen(self):
        assert _parse_slug("sportster") == ("sportster", None)

    def test_slug_case_insensitive(self):
        assert _parse_slug("SPORTSTER-2001") == ("sportster", 2001)

    def test_slug_out_of_range_year_treated_as_stem(self):
        # 9999 is outside [1980, 2035] — not a year
        stem, year = _parse_slug("foo-9999")
        assert year is None
        assert "foo-9999" == stem

    def test_slug_empty(self):
        assert _parse_slug("") == ("", None)

    def test_slug_whitespace_trimmed(self):
        assert _parse_slug("  sportster-2001  ") == ("sportster", 2001)

    def test_slug_year_boundary_min(self):
        assert _parse_slug(f"foo-{SLUG_YEAR_MIN}") == ("foo", SLUG_YEAR_MIN)

    def test_slug_year_boundary_max(self):
        assert _parse_slug(f"foo-{SLUG_YEAR_MAX}") == ("foo", SLUG_YEAR_MAX)


# --- _resolve_bike_slug ---


class TestResolveBikeSlug:
    def test_exact_model_match_with_year(self, db):
        _seed_sportster(db)
        row = _resolve_bike_slug("sportster 1200-2001", db_path=db)
        # "sportster 1200" is the exact model (case-insensitive)
        assert row is not None
        assert row["model"] == "Sportster 1200"
        assert row["year"] == 2001

    def test_partial_model_match_with_year(self, db):
        _seed_sportster(db)
        row = _resolve_bike_slug("sportster-2001", db_path=db)
        assert row is not None
        assert row["make"] == "Harley-Davidson"
        assert row["year"] == 2001

    def test_cbr_partial_model_match(self, db):
        _seed_cbr(db)
        row = _resolve_bike_slug("cbr929-2000", db_path=db)
        assert row is not None
        assert row["model"] == "CBR929RR"

    def test_make_match_when_model_doesnt_match(self, db):
        _seed_sportster(db)
        _seed_cbr(db)
        # "honda" matches Honda make
        row = _resolve_bike_slug("honda", db_path=db)
        assert row is not None
        assert row["make"] == "Honda"

    def test_harley_partial_make(self, db):
        _seed_sportster(db)
        # "harley" matches "Harley-Davidson" via LIKE
        row = _resolve_bike_slug("harley", db_path=db)
        assert row is not None
        assert "Harley" in row["make"]

    def test_no_match_returns_none(self, db):
        _seed_sportster(db)
        assert _resolve_bike_slug("notabike-9999", db_path=db) is None

    def test_slug_without_year_matches_by_model(self, db):
        _seed_sportster(db)
        row = _resolve_bike_slug("sportster", db_path=db)
        assert row is not None
        assert row["model"] == "Sportster 1200"

    def test_case_insensitive(self, db):
        _seed_sportster(db)
        row = _resolve_bike_slug("SPORTSTER-2001", db_path=db)
        assert row is not None
        assert row["model"] == "Sportster 1200"

    def test_year_filter_excludes_wrong_year(self, db):
        _seed_sportster(db)  # year=2001
        # Ask for 2005 — no match even though model matches
        assert _resolve_bike_slug("sportster-2005", db_path=db) is None

    def test_ambiguous_returns_first_by_created_at(self, db):
        # Two Harley rows — oldest by created_at should win.
        vid1 = _seed_sportster(db)
        add_vehicle(VehicleBase(
            make="Harley-Davidson", model="Dyna", year=2005,
            engine_cc=1450, protocol=ProtocolType.J1850,
        ), db_path=db)
        row = _resolve_bike_slug("harley", db_path=db)
        assert row is not None
        assert row["id"] == vid1  # the first-inserted row

    def test_empty_slug_returns_none(self, db):
        assert _resolve_bike_slug("", db_path=db) is None


# --- CLI: diagnose quick --bike SLUG ---


class TestDiagnoseQuickBikeSlug:
    def test_happy_path_bike_slug(self, cli_db):
        _seed_sportster(cli_db)
        from motodiag.cli.main import cli
        fn = make_diagnose_fn(make_response(confidence=0.88))
        with patch("motodiag.cli.diagnose._default_diagnose_fn", fn):
            runner = CliRunner()
            r = runner.invoke(cli, [
                "diagnose", "quick",
                "--bike", "sportster-2001",
                "--symptoms", "won't start",
            ])
        assert r.exit_code == 0, r.output
        assert "Session #" in r.output
        assert "Stator failure" in r.output

    def test_unknown_slug_errors(self, cli_db):
        _seed_sportster(cli_db)
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, [
            "diagnose", "quick",
            "--bike", "notabike-9999",
            "--symptoms", "x",
        ])
        assert r.exit_code != 0
        assert "no bike matches" in r.output.lower()
        # Garage hint should list seeded vehicle
        assert "Sportster 1200" in r.output or "Harley" in r.output

    def test_unknown_slug_empty_garage(self, cli_db):
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, [
            "diagnose", "quick",
            "--bike", "sportster-2001",
            "--symptoms", "x",
        ])
        assert r.exit_code != 0
        assert "no bike matches" in r.output.lower()
        assert "empty" in r.output.lower() or "add a bike" in r.output.lower()

    def test_both_bike_and_vehicle_id_prefers_id(self, cli_db):
        vid = _seed_sportster(cli_db)
        _seed_cbr(cli_db)
        from motodiag.cli.main import cli
        captured = {}
        base = make_diagnose_fn(make_response(confidence=0.9))

        def spy(**kwargs):
            captured.update(kwargs)
            return base(**kwargs)

        with patch("motodiag.cli.diagnose._default_diagnose_fn", spy):
            runner = CliRunner()
            r = runner.invoke(cli, [
                "diagnose", "quick",
                "--vehicle-id", str(vid),
                "--bike", "cbr929-2000",
                "--symptoms", "x",
            ])
        assert r.exit_code == 0, r.output
        # Warning should mention the conflict
        assert "--vehicle-id" in r.output or "vehicle-id" in r.output.lower()
        # Sportster (from --vehicle-id) won, not CBR (from --bike)
        assert captured.get("make") == "Harley-Davidson"

    def test_neither_bike_nor_vehicle_id_errors(self, cli_db):
        _seed_sportster(cli_db)
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, [
            "diagnose", "quick",
            "--symptoms", "x",
        ])
        assert r.exit_code != 0
        assert (
            "--vehicle-id" in r.output
            or "--bike" in r.output
            or "specify" in r.output.lower()
        )


# --- CLI: top-level motodiag quick ---


class TestTopLevelQuick:
    def test_top_level_quick_with_bike(self, cli_db):
        _seed_sportster(cli_db)
        from motodiag.cli.main import cli
        fn = make_diagnose_fn(make_response(confidence=0.9))
        with patch("motodiag.cli.diagnose._default_diagnose_fn", fn):
            runner = CliRunner()
            r = runner.invoke(cli, [
                "quick",
                "won't start when cold",
                "--bike", "sportster-2001",
            ])
        assert r.exit_code == 0, r.output
        assert "Session #" in r.output
        assert "Stator failure" in r.output

    def test_top_level_quick_with_vehicle_id(self, cli_db):
        vid = _seed_sportster(cli_db)
        from motodiag.cli.main import cli
        fn = make_diagnose_fn(make_response(confidence=0.9))
        with patch("motodiag.cli.diagnose._default_diagnose_fn", fn):
            runner = CliRunner()
            r = runner.invoke(cli, [
                "quick",
                "starts then dies",
                "--vehicle-id", str(vid),
            ])
        assert r.exit_code == 0, r.output
        assert "Session #" in r.output

    def test_top_level_quick_missing_symptoms(self, cli_db):
        _seed_sportster(cli_db)
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["quick", "--bike", "sportster-2001"])
        assert r.exit_code != 0
        # Click reports missing positional argument
        assert "missing" in r.output.lower() or "symptoms" in r.output.lower()

    def test_top_level_quick_description_passthrough(self, cli_db):
        _seed_sportster(cli_db)
        from motodiag.cli.main import cli
        captured = {}
        base = make_diagnose_fn(make_response(confidence=0.9))

        def spy(**kwargs):
            captured.update(kwargs)
            return base(**kwargs)

        with patch("motodiag.cli.diagnose._default_diagnose_fn", spy):
            runner = CliRunner()
            r = runner.invoke(cli, [
                "quick", "won't start",
                "--bike", "sportster-2001",
                "--description", "Only when cold; cranks slow.",
            ])
        assert r.exit_code == 0, r.output
        assert captured.get("description") == "Only when cold; cranks slow."

    def test_top_level_quick_unknown_slug(self, cli_db):
        _seed_sportster(cli_db)
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, [
            "quick", "stalls",
            "--bike", "notabike-9999",
        ])
        assert r.exit_code != 0
        assert "no bike matches" in r.output.lower()

    def test_top_level_quick_sonnet_on_individual_hard(self, cli_db, monkeypatch):
        monkeypatch.setenv("MOTODIAG_PAYWALL_MODE", "hard")
        monkeypatch.setenv("MOTODIAG_SUBSCRIPTION_TIER", "individual")
        _seed_sportster(cli_db)
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, [
            "quick", "x",
            "--bike", "sportster-2001",
            "--model", "sonnet",
        ])
        assert r.exit_code != 0
        assert "shop tier" in r.output.lower() or "individual" in r.output.lower()


# --- Regression: existing diagnose quick --vehicle-id still works ---


class TestRegression:
    def test_existing_vehicle_id_path_unchanged(self, cli_db):
        vid = _seed_cbr(cli_db)
        from motodiag.cli.main import cli
        fn = make_diagnose_fn(make_response(confidence=0.88))
        with patch("motodiag.cli.diagnose._default_diagnose_fn", fn):
            runner = CliRunner()
            r = runner.invoke(cli, [
                "diagnose", "quick",
                "--vehicle-id", str(vid),
                "--symptoms", "won't start, battery weak",
            ])
        assert r.exit_code == 0, r.output
        assert "Session #" in r.output
        assert "Stator failure" in r.output
        # And the session actually persists
        sessions = list_sessions(db_path=cli_db)
        assert len(sessions) == 1
        assert sessions[0]["status"] == "closed"

    def test_top_level_quick_command_registered(self):
        from motodiag.cli.main import cli
        assert "quick" in cli.commands

    def test_diagnose_group_still_has_quick(self):
        from motodiag.cli.main import cli
        diagnose_group = cli.commands["diagnose"]
        assert "quick" in diagnose_group.commands
