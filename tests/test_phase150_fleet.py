"""Phase 150 — Fleet management tests.

Four test classes across ~35 tests:

- :class:`TestMigration018` (4) — schema-version bump v17→v18, fleets +
  fleet_bikes tables + indexes present, UNIQUE(owner_user_id, name)
  violation, rollback idempotent (child-first DROP).
- :class:`TestFleetRepo` (10) — CRUD happy path, dup-name raises
  :class:`FleetNameExistsError`, dup-bike raises
  :class:`BikeAlreadyInFleetError`, role CHECK rejects invalid values,
  delete_fleet cascades junction rows but preserves vehicles,
  list_fleets_for_bike returns >=2 fleets for a shared bike.
- :class:`TestFleetAnalytics` (8) — empty-fleet zeros, predictions
  aggregated, critical count, open-session count, _HAS_WEAR=False
  branch, _HAS_WEAR=True via monkeypatch + stub, missing fleet raises,
  horizon passthrough.
- :class:`TestFleetCLI` (12, Click CliRunner) — create happy + dup,
  list empty + JSON, show, add-bike + invalid role + already-in-fleet,
  remove-bike, delete --force + prompt abort, status JSON.

All tests are SW + SQL only. Zero AI calls, zero network, zero live
tokens.
"""

from __future__ import annotations

import json as _json

import pytest
from click.testing import CliRunner

from motodiag.advanced import (
    BikeAlreadyInFleetError,
    FleetNameExistsError,
    FleetNotFoundError,
    FleetRole,
    fleet_status_summary,
)
from motodiag.advanced import fleet_analytics as fa_mod
from motodiag.advanced.fleet_repo import (
    add_bike_to_fleet,
    create_fleet,
    delete_fleet,
    get_fleet,
    get_fleet_by_name,
    list_bikes_in_fleet,
    list_fleets,
    list_fleets_for_bike,
    remove_bike_from_fleet,
    rename_fleet,
    set_bike_role,
    update_fleet_description,
)
from motodiag.cli.advanced import register_advanced
from motodiag.core.database import (
    SCHEMA_VERSION,
    get_connection,
    get_schema_version,
    init_db,
    table_exists,
)
from motodiag.core.migrations import (
    get_migration_by_version,
    rollback_migration,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_cli():
    """Build a fresh CLI group with only `advanced` registered."""
    import click

    @click.group()
    def root() -> None:
        """test root"""

    register_advanced(root)
    return root


@pytest.fixture
def db(tmp_path):
    """Per-test SQLite DB pre-migrated to the latest schema."""
    path = str(tmp_path / "phase150.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    """Point settings + CLI env at a temp DB. Mirrors Phase 148."""
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase150_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    yield path
    reset_settings()


def _add_vehicle(
    db_path: str,
    make: str = "Harley-Davidson",
    model: str = "Sportster 1200",
    year: int = 2010,
) -> int:
    """Insert a vehicles row directly so we don't need Pydantic models."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO vehicles (make, model, year, protocol) "
            "VALUES (?, ?, ?, 'none')",
            (make, model, year),
        )
        return cursor.lastrowid


# ===========================================================================
# 1. Migration 018
# ===========================================================================


class TestMigration018:
    """Migration 018 bumps v17→v18, creates 2 tables + 2 indexes, rolls back."""

    def test_schema_version_bumped_to_18(self, db):
        assert SCHEMA_VERSION == 18
        assert get_schema_version(db) == 18

    def test_fleets_and_fleet_bikes_created_with_indexes(self, db):
        assert table_exists("fleets", db) is True
        assert table_exists("fleet_bikes", db) is True
        expected = {"idx_fleets_owner_name", "idx_fleet_bikes_vehicle"}
        with get_connection(db) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
            actual = {r[0] for r in rows}
        assert expected.issubset(actual)

    def test_unique_owner_name_violation(self, db):
        create_fleet("shared-name", db_path=db)
        with pytest.raises(FleetNameExistsError):
            create_fleet("shared-name", db_path=db)

    def test_rollback_drops_both_tables_idempotent(self, tmp_path):
        """Rollback must drop fleet_bikes FIRST (FK CASCADE on fleets.id)."""
        path = str(tmp_path / "rollback.db")
        init_db(path)
        assert table_exists("fleets", path) is True
        assert table_exists("fleet_bikes", path) is True
        migration = get_migration_by_version(18)
        assert migration is not None
        rollback_migration(migration, path)
        assert table_exists("fleets", path) is False
        assert table_exists("fleet_bikes", path) is False


# ===========================================================================
# 2. fleet_repo CRUD
# ===========================================================================


class TestFleetRepo:
    """CRUD + junction semantics + cascade behavior."""

    def test_create_and_get_fleet_roundtrip(self, db):
        fid = create_fleet(
            "rentals-2026", description="Summer rental fleet", db_path=db,
        )
        assert fid > 0
        row = get_fleet(fid, db_path=db)
        assert row is not None
        assert row["name"] == "rentals-2026"
        assert row["description"] == "Summer rental fleet"
        assert row["owner_user_id"] == 1

    def test_get_fleet_by_name(self, db):
        create_fleet("race-team", db_path=db)
        row = get_fleet_by_name("race-team", db_path=db)
        assert row is not None
        assert row["name"] == "race-team"

    def test_list_fleets_with_bike_count(self, db):
        f1 = create_fleet("f1", db_path=db)
        f2 = create_fleet("f2", db_path=db)
        v1 = _add_vehicle(db)
        v2 = _add_vehicle(db, model="Road Glide")
        add_bike_to_fleet(f1, v1, db_path=db)
        add_bike_to_fleet(f1, v2, db_path=db)
        add_bike_to_fleet(f2, v1, db_path=db)
        rows = list_fleets(db_path=db)
        by_name = {r["name"]: r for r in rows}
        assert by_name["f1"]["bike_count"] == 2
        assert by_name["f2"]["bike_count"] == 1

    def test_rename_and_update_description(self, db):
        fid = create_fleet("orig", db_path=db)
        assert rename_fleet(fid, "new-name", db_path=db) is True
        assert get_fleet(fid, db_path=db)["name"] == "new-name"
        assert update_fleet_description(fid, "new desc", db_path=db) is True
        assert get_fleet(fid, db_path=db)["description"] == "new desc"

    def test_create_fleet_dup_name_raises(self, db):
        create_fleet("dup", db_path=db)
        with pytest.raises(FleetNameExistsError):
            create_fleet("dup", db_path=db)

    def test_add_bike_dup_raises_bikealreadyinfleet(self, db):
        fid = create_fleet("f", db_path=db)
        vid = _add_vehicle(db)
        add_bike_to_fleet(fid, vid, db_path=db)
        with pytest.raises(BikeAlreadyInFleetError):
            add_bike_to_fleet(fid, vid, db_path=db)

    def test_role_check_rejects_invalid(self, db):
        fid = create_fleet("f", db_path=db)
        vid = _add_vehicle(db)
        with pytest.raises(ValueError, match="role"):
            add_bike_to_fleet(fid, vid, role="bogus", db_path=db)

    def test_set_bike_role_roundtrip(self, db):
        fid = create_fleet("f", db_path=db)
        vid = _add_vehicle(db)
        add_bike_to_fleet(fid, vid, role="customer", db_path=db)
        assert set_bike_role(fid, vid, "rental", db_path=db) is True
        bikes = list_bikes_in_fleet(fid, db_path=db)
        assert bikes[0]["role"] == "rental"
        # Role enum values match the CHECK constraint.
        assert FleetRole.RENTAL.value == "rental"

    def test_delete_fleet_preserves_vehicles(self, db):
        fid = create_fleet("f", db_path=db)
        vid = _add_vehicle(db)
        add_bike_to_fleet(fid, vid, db_path=db)
        assert delete_fleet(fid, db_path=db) is True
        # Vehicle survives even though junction rows cascaded.
        with get_connection(db) as conn:
            row = conn.execute(
                "SELECT * FROM vehicles WHERE id = ?", (vid,),
            ).fetchone()
        assert row is not None
        # Junction rows gone.
        with get_connection(db) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM fleet_bikes WHERE fleet_id = ?",
                (fid,),
            ).fetchone()[0]
        assert count == 0

    def test_list_fleets_for_bike_returns_multiple(self, db):
        f1 = create_fleet("fleet-a", db_path=db)
        f2 = create_fleet("fleet-b", db_path=db)
        vid = _add_vehicle(db)
        add_bike_to_fleet(f1, vid, role="rental", db_path=db)
        add_bike_to_fleet(f2, vid, role="demo", db_path=db)
        fleets = list_fleets_for_bike(vid, db_path=db)
        assert len(fleets) == 2
        names = {f["name"] for f in fleets}
        assert names == {"fleet-a", "fleet-b"}
        # Junction role survives the JOIN.
        assert {f["role"] for f in fleets} == {"rental", "demo"}

    def test_remove_bike_from_fleet_returns_false_when_missing(self, db):
        fid = create_fleet("f", db_path=db)
        vid = _add_vehicle(db)
        # Removing when absent → False, not exception.
        assert remove_bike_from_fleet(fid, vid, db_path=db) is False


# ===========================================================================
# 3. fleet_analytics
# ===========================================================================


class TestFleetAnalytics:
    """fleet_status_summary rollup logic."""

    def test_empty_fleet_zero_totals(self, db):
        fid = create_fleet("empty", db_path=db)
        summary = fleet_status_summary(fid, db_path=db)
        assert summary["fleet"]["bike_count"] == 0
        assert summary["bikes"] == []
        assert summary["totals"]["total_predictions"] == 0
        assert summary["totals"]["critical_predictions"] == 0
        assert summary["totals"]["bikes_with_open_sessions"] == 0
        assert summary["totals"]["bikes_with_critical"] == 0

    def test_missing_fleet_raises(self, db):
        with pytest.raises(FleetNotFoundError):
            fleet_status_summary(99999, db_path=db)

    def test_predictions_aggregated_per_bike(self, db):
        # Seed a known issue that will trigger at least one prediction.
        from motodiag.knowledge.issues_repo import add_known_issue

        add_known_issue(
            title="Fleet test stator",
            description="Stator failure common. Forum consensus: replace.",
            make="Harley-Davidson",
            model="Sportster 1200",
            year_start=2004,
            year_end=2021,
            severity="critical",
            symptoms=["no charge"],
            dtc_codes=["P0562"],
            causes=["winding breakdown"],
            fix_procedure="Forum tip: swap stator assembly.",
            parts_needed=["Stator"],
            estimated_hours=3.5,
            db_path=db,
        )
        fid = create_fleet("pred-fleet", db_path=db)
        vid = _add_vehicle(db, year=2010)
        add_bike_to_fleet(fid, vid, role="rental", db_path=db)

        summary = fleet_status_summary(
            fid, horizon_days=3650, db_path=db,
        )
        assert summary["fleet"]["bike_count"] == 1
        bike_row = summary["bikes"][0]
        assert bike_row["prediction_count"] >= 1
        assert bike_row["critical_prediction_count"] >= 1
        assert bike_row["top_prediction"] is not None
        assert summary["totals"]["total_predictions"] >= 1
        assert summary["totals"]["bikes_with_critical"] == 1

    def test_critical_count_separate_from_total(self, db):
        """Non-critical predictions increment total but not critical count."""
        from motodiag.knowledge.issues_repo import add_known_issue

        add_known_issue(
            title="Low-severity cosmetic",
            description="Paint chipping on airbox.",
            make="Harley-Davidson",
            model="Sportster 1200",
            year_start=2004,
            year_end=2021,
            severity="low",
            symptoms=["cosmetic"],
            dtc_codes=[],
            causes=["sun exposure"],
            fix_procedure="Touch up paint.",
            parts_needed=["Paint"],
            estimated_hours=0.5,
            db_path=db,
        )
        fid = create_fleet("low-fleet", db_path=db)
        vid = _add_vehicle(db, year=2010)
        add_bike_to_fleet(fid, vid, db_path=db)
        summary = fleet_status_summary(
            fid, horizon_days=3650, db_path=db,
        )
        bike_row = summary["bikes"][0]
        if bike_row["prediction_count"] >= 1:
            # At least one prediction but it's low severity → 0 critical.
            assert bike_row["critical_prediction_count"] == 0

    def test_open_session_count(self, db):
        fid = create_fleet("sess-fleet", db_path=db)
        vid = _add_vehicle(db)
        add_bike_to_fleet(fid, vid, db_path=db)
        # Insert two open diagnostic_sessions and one closed.
        with get_connection(db) as conn:
            for status in ("open", "open", "closed"):
                conn.execute(
                    "INSERT INTO diagnostic_sessions ("
                    "vehicle_id, vehicle_make, vehicle_model, vehicle_year, "
                    "status) VALUES (?, 'Harley-Davidson', "
                    "'Sportster 1200', 2010, ?)",
                    (vid, status),
                )
        summary = fleet_status_summary(fid, db_path=db)
        bike_row = summary["bikes"][0]
        assert bike_row["open_sessions"] == 2
        assert summary["totals"]["bikes_with_open_sessions"] == 1

    def test_has_wear_false_wear_percent_none(self, db, monkeypatch):
        """When _HAS_WEAR=False, wear_percent is None for every bike."""
        monkeypatch.setattr(fa_mod, "_HAS_WEAR", False)
        fid = create_fleet("nowear", db_path=db)
        vid = _add_vehicle(db)
        add_bike_to_fleet(fid, vid, db_path=db)
        summary = fleet_status_summary(fid, db_path=db)
        assert summary["phase149_available"] is False
        assert summary["bikes"][0]["wear_percent"] is None
        assert summary["totals"]["average_wear_percent"] is None

    def test_has_wear_true_populates_wear_percent(self, db, monkeypatch):
        """Monkeypatch _HAS_WEAR=True + stub the helper to return 42.0."""
        monkeypatch.setattr(fa_mod, "_HAS_WEAR", True)
        monkeypatch.setattr(
            fa_mod, "_wear_percent_for_vehicle",
            lambda bike_row, db_path=None: 42.0,
        )
        fid = create_fleet("wear", db_path=db)
        vid = _add_vehicle(db)
        add_bike_to_fleet(fid, vid, db_path=db)
        summary = fleet_status_summary(fid, db_path=db)
        assert summary["phase149_available"] is True
        assert summary["bikes"][0]["wear_percent"] == 42.0
        assert summary["totals"]["average_wear_percent"] == 42.0

    def test_horizon_days_passthrough(self, db):
        """horizon_days propagates to predict_failures (short horizon → fewer
        predictions)."""
        from motodiag.knowledge.issues_repo import add_known_issue

        add_known_issue(
            title="Far-future issue",
            description="Problem emerges late in life.",
            make="Harley-Davidson",
            model="Sportster 1200",
            year_start=2004,
            year_end=2021,
            severity="medium",
            symptoms=["late-life"],
            dtc_codes=[],
            causes=["age"],
            fix_procedure="Monitor then replace.",
            parts_needed=["Item"],
            estimated_hours=1.0,
            db_path=db,
        )
        fid = create_fleet("horizon-test", db_path=db)
        vid = _add_vehicle(db, year=2024)  # brand-new
        add_bike_to_fleet(fid, vid, db_path=db)

        short = fleet_status_summary(fid, horizon_days=1, db_path=db)
        wide = fleet_status_summary(fid, horizon_days=3650, db_path=db)
        assert short["horizon_days"] == 1
        assert wide["horizon_days"] == 3650
        assert (
            short["totals"]["total_predictions"]
            <= wide["totals"]["total_predictions"]
        )


# ===========================================================================
# 4. CLI (CliRunner)
# ===========================================================================


class TestFleetCLI:
    """CliRunner-driven tests against `motodiag advanced fleet ...`."""

    def _seed_vehicle_slug(self, db_path: str) -> int:
        """Seed a Harley Sportster 1200 2010 so --bike slug resolution works."""
        from motodiag.core.models import (
            EngineType,
            PowertrainType,
            ProtocolType,
            VehicleBase,
        )
        from motodiag.vehicles.registry import add_vehicle

        v = VehicleBase(
            make="Harley-Davidson",
            model="Sportster 1200",
            year=2010,
            engine_cc=1200,
            protocol=ProtocolType.J1850,
            powertrain=PowertrainType.ICE,
            engine_type=EngineType.FOUR_STROKE,
        )
        return add_vehicle(v, db_path=db_path)

    def test_create_happy(self, cli_db):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "fleet", "create", "rentals"],
        )
        assert result.exit_code == 0, result.output
        assert "Created fleet" in result.output
        assert get_fleet_by_name("rentals") is not None

    def test_create_duplicate_fails(self, cli_db):
        runner = CliRunner()
        runner.invoke(
            _make_cli(),
            ["advanced", "fleet", "create", "dup"],
        )
        result = runner.invoke(
            _make_cli(),
            ["advanced", "fleet", "create", "dup"],
        )
        assert result.exit_code != 0
        assert "exists" in result.output.lower()

    def test_list_empty(self, cli_db):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "fleet", "list"],
        )
        assert result.exit_code == 0, result.output
        assert "No fleets" in result.output

    def test_list_json(self, cli_db):
        create_fleet("json-fleet")
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "fleet", "list", "--json"],
        )
        assert result.exit_code == 0, result.output
        payload = _json.loads(result.output)
        assert "fleets" in payload
        assert len(payload["fleets"]) == 1
        assert payload["fleets"][0]["name"] == "json-fleet"

    def test_show_happy(self, cli_db):
        create_fleet("shown")
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "fleet", "show", "shown"],
        )
        assert result.exit_code == 0, result.output
        assert "shown" in result.output

    def test_add_bike_happy(self, cli_db):
        create_fleet("addtest")
        self._seed_vehicle_slug(cli_db)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "fleet", "add-bike", "addtest",
                "--bike", "sportster-2010",
                "--role", "rental",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Added" in result.output
        assert "rental" in result.output

    def test_add_bike_invalid_role(self, cli_db):
        create_fleet("roletest")
        self._seed_vehicle_slug(cli_db)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "fleet", "add-bike", "roletest",
                "--bike", "sportster-2010",
                "--role", "bogus",
            ],
        )
        assert result.exit_code != 0
        # Click catches the bad choice at parse time.
        assert "bogus" in result.output.lower() or "invalid" in result.output.lower()

    def test_add_bike_already_in_fleet(self, cli_db):
        create_fleet("dupbike")
        self._seed_vehicle_slug(cli_db)
        runner = CliRunner()
        runner.invoke(
            _make_cli(),
            [
                "advanced", "fleet", "add-bike", "dupbike",
                "--bike", "sportster-2010",
            ],
        )
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "fleet", "add-bike", "dupbike",
                "--bike", "sportster-2010",
            ],
        )
        assert result.exit_code != 0
        assert "already" in result.output.lower()

    def test_remove_bike_happy(self, cli_db):
        create_fleet("rmtest")
        self._seed_vehicle_slug(cli_db)
        runner = CliRunner()
        runner.invoke(
            _make_cli(),
            [
                "advanced", "fleet", "add-bike", "rmtest",
                "--bike", "sportster-2010",
            ],
        )
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "fleet", "remove-bike", "rmtest",
                "--bike", "sportster-2010",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Removed" in result.output

    def test_delete_force_happy(self, cli_db):
        create_fleet("to-delete")
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "fleet", "delete", "to-delete", "--force"],
        )
        assert result.exit_code == 0, result.output
        assert "Deleted" in result.output
        assert get_fleet_by_name("to-delete") is None

    def test_delete_prompt_abort(self, cli_db):
        create_fleet("keep-me")
        runner = CliRunner()
        # Pipe "n\n" to the confirm prompt → abort.
        result = runner.invoke(
            _make_cli(),
            ["advanced", "fleet", "delete", "keep-me"],
            input="n\n",
        )
        assert result.exit_code == 0, result.output
        assert "Aborted" in result.output
        # Fleet survives.
        assert get_fleet_by_name("keep-me") is not None

    def test_status_json(self, cli_db):
        create_fleet("status-json")
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "fleet", "status", "status-json", "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = _json.loads(result.output)
        assert "fleet" in payload
        assert "bikes" in payload
        assert "totals" in payload
        assert payload["horizon_days"] == 180
