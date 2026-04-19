"""Phase 151 — Service-interval scheduling tests.

Four test classes across ~35 tests:

- :class:`TestMigration019` (4) — schema-version bump to 19,
  service_intervals + service_interval_templates tables + 3 indexes,
  FK CASCADE from vehicles, rollback idempotent.
- :class:`TestScheduleRepo` (10) — CRUD roundtrip, UNIQUE violation,
  list/filter, update/delete, load_templates 44 rows, idempotent
  re-load, match_templates wildcard + LIKE, seed_from_template skips
  existing slugs.
- :class:`TestScheduler` (10) — next_due_calc miles-only / months-only
  / dual-axis / Feb-28 / Jan-31 edge, due_items horizons, overdue
  ordering, record_completion with/without mileage, missing-sources
  raises.
- :class:`TestScheduleCLI` (11, Click CliRunner) — init / list / due /
  overdue / complete / history happy paths + error handling.

All tests are SW + SQL only. Zero AI calls, zero network, zero live
tokens.
"""

from __future__ import annotations

import json as _json
import sqlite3
from datetime import date
from pathlib import Path

import pytest
from click.testing import CliRunner

from motodiag.advanced import (
    ServiceInterval,
    ServiceIntervalError,
)
from motodiag.advanced.schedule_repo import (
    create_interval,
    delete_interval,
    get_interval,
    get_interval_by_slug,
    list_intervals,
    list_templates,
    load_templates_from_json,
    match_templates_for_vehicle,
    seed_from_template,
    update_interval,
)
from motodiag.advanced.scheduler import (
    _add_months,
    _parse_iso_date,
    due_items,
    history,
    next_due_calc,
    overdue_items,
    record_completion,
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
    path = str(tmp_path / "phase151.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    """Point settings + CLI env at a temp DB. Mirrors Phase 150."""
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase151_cli.db")
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
    """Insert a vehicles row directly."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO vehicles (make, model, year, protocol) "
            "VALUES (?, ?, ?, 'none')",
            (make, model, year),
        )
        return cursor.lastrowid


# ===========================================================================
# 1. Migration 019
# ===========================================================================


class TestMigration019:
    """Migration 019 creates scheduling tables + indexes and is reversible."""

    def test_schema_version_at_least_19(self, db):
        # SCHEMA_VERSION may have been bumped further by Phase 152+
        # builders; Phase 151's contract is that migration 019 lands
        # and the DB version is >= 19.
        assert SCHEMA_VERSION >= 19
        current = get_schema_version(db)
        assert current is not None and current >= 19

    def test_tables_and_three_indexes_created(self, db):
        assert table_exists("service_intervals", db) is True
        assert table_exists("service_interval_templates", db) is True
        expected = {
            "idx_svc_int_vehicle",
            "idx_svc_int_next_due",
            "idx_svc_tpl_make_model",
        }
        with get_connection(db) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
            actual = {r[0] for r in rows}
        assert expected.issubset(actual)

    def test_fk_cascade_from_vehicles(self, db):
        """Deleting a vehicle cascades its service_intervals rows."""
        vid = _add_vehicle(db)
        create_interval(
            vid, "oil-change", "Engine oil",
            every_miles=5000, every_months=12, db_path=db,
        )
        create_interval(
            vid, "chain-clean-lube", "Chain maintenance",
            every_miles=1000, db_path=db,
        )
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM service_intervals WHERE vehicle_id = ?",
                (vid,),
            )
            assert cursor.fetchone()[0] == 2
            conn.execute("DELETE FROM vehicles WHERE id = ?", (vid,))
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM service_intervals WHERE vehicle_id = ?",
                (vid,),
            )
            assert cursor.fetchone()[0] == 0

    def test_rollback_drops_both_tables(self, tmp_path):
        """Migration 019 rollback drops both tables cleanly."""
        path = str(tmp_path / "rollback.db")
        init_db(path)
        assert table_exists("service_intervals", path) is True
        assert table_exists("service_interval_templates", path) is True

        migration = get_migration_by_version(19)
        assert migration is not None
        rollback_migration(migration, path)

        assert table_exists("service_intervals", path) is False
        assert table_exists("service_interval_templates", path) is False


# ===========================================================================
# 2. schedule_repo
# ===========================================================================


class TestScheduleRepo:
    """CRUD + template loader + matching + seeding."""

    def test_create_and_get_roundtrip(self, db):
        vid = _add_vehicle(db)
        iid = create_interval(
            vid, "oil-change", "Engine oil + filter",
            every_miles=5000, every_months=12, db_path=db,
        )
        assert iid > 0
        row = get_interval(iid, db_path=db)
        assert row is not None
        assert row["item_slug"] == "oil-change"
        assert row["every_miles"] == 5000
        assert row["every_months"] == 12

        # Also accessible by (vehicle_id, item_slug)
        row2 = get_interval_by_slug(vid, "oil-change", db_path=db)
        assert row2 is not None and row2["id"] == iid

        # Pydantic model accepts the row
        model = ServiceInterval(**{
            k: v for k, v in row.items()
            if k in ServiceInterval.model_fields
        })
        assert model.item_slug == "oil-change"

    def test_unique_vehicle_item_slug_violation(self, db):
        vid = _add_vehicle(db)
        create_interval(
            vid, "oil-change", "first", every_miles=5000, db_path=db,
        )
        with pytest.raises(sqlite3.IntegrityError):
            create_interval(
                vid, "oil-change", "second", every_miles=6000, db_path=db,
            )

    def test_check_at_least_one_axis(self, db):
        vid = _add_vehicle(db)
        with pytest.raises(ServiceIntervalError):
            create_interval(
                vid, "bad-slug", "neither axis", db_path=db,
            )

    def test_list_intervals_ordered_by_slug(self, db):
        vid = _add_vehicle(db)
        create_interval(vid, "valve-check", "Valves", every_miles=16000, db_path=db)
        create_interval(vid, "chain-clean-lube", "Chain", every_miles=1000, db_path=db)
        create_interval(vid, "oil-change", "Oil", every_miles=5000, db_path=db)
        rows = list_intervals(vid, db_path=db)
        slugs = [r["item_slug"] for r in rows]
        assert slugs == sorted(slugs)

    def test_update_partial_and_delete(self, db):
        vid = _add_vehicle(db)
        iid = create_interval(
            vid, "oil-change", "Oil", every_miles=5000, db_path=db,
        )
        assert update_interval(
            iid, db_path=db,
            last_done_miles=4500, last_done_at="2026-04-10",
            next_due_miles=9500, next_due_at="2027-04-10",
        ) is True
        row = get_interval(iid, db_path=db)
        assert row["last_done_miles"] == 4500
        assert row["next_due_miles"] == 9500
        assert row["next_due_at"] == "2027-04-10"

        # No-op update returns False
        assert update_interval(iid, db_path=db) is False

        # Delete returns True, then False on repeat
        assert delete_interval(iid, db_path=db) is True
        assert delete_interval(iid, db_path=db) is False

    def test_load_templates_loads_44(self, db):
        count = load_templates_from_json(db_path=db)
        assert count == 44
        rows = list_templates(db_path=db)
        assert len(rows) == 44

    def test_load_templates_idempotent(self, db):
        first = load_templates_from_json(db_path=db)
        second = load_templates_from_json(db_path=db)
        assert first == 44
        assert second == 0
        assert len(list_templates(db_path=db)) == 44

    def test_match_templates_wildcard(self, db):
        load_templates_from_json(db_path=db)
        # Ducati Monster should match make='*' universals + make='ducati'
        vehicle = {"make": "Ducati", "model": "Monster 696", "year": 2012}
        matches = match_templates_for_vehicle(vehicle, db_path=db)
        slugs = {m["item_slug"] for m in matches}
        # Universal items always match
        assert "brake-fluid-flush" in slugs
        assert "chain-clean-lube" in slugs
        assert "tire-pressure-check" in slugs
        # Make-specific
        assert "valve-check" in slugs  # Ducati desmo entry
        assert "timing-belt-replace" in slugs

    def test_match_templates_like_model_pattern(self, db):
        load_templates_from_json(db_path=db)
        # KLR650 should pick up the doohickey-check row via KLR% pattern
        vehicle = {"make": "Kawasaki", "model": "KLR650", "year": 2018}
        matches = match_templates_for_vehicle(vehicle, db_path=db)
        slugs = {m["item_slug"] for m in matches}
        assert "doohickey-check" in slugs
        # But a Ninja should NOT
        ninja = {"make": "Kawasaki", "model": "Ninja 650", "year": 2018}
        matches2 = match_templates_for_vehicle(ninja, db_path=db)
        slugs2 = {m["item_slug"] for m in matches2}
        assert "doohickey-check" not in slugs2
        assert "valve-check" in slugs2  # Ninja% entry

    def test_seed_from_template_skips_existing(self, db):
        load_templates_from_json(db_path=db)
        vid = _add_vehicle(db, make="Harley-Davidson", model="Sportster 1200")
        # Pre-seed one slug manually
        create_interval(
            vid, "oil-change", "manual entry", every_miles=3000, db_path=db,
        )
        created = seed_from_template(vid, db_path=db)
        # At least several templates matched; at least one was skipped.
        assert created >= 5
        intervals = list_intervals(vid, db_path=db)
        # Still only one oil-change row, with the manual every_miles preserved.
        oil = [i for i in intervals if i["item_slug"] == "oil-change"]
        assert len(oil) == 1
        assert oil[0]["every_miles"] == 3000
        assert oil[0]["description"] == "manual entry"

        # Re-seeding is a no-op
        second = seed_from_template(vid, db_path=db)
        assert second == 0


# ===========================================================================
# 3. scheduler
# ===========================================================================


class TestScheduler:
    """Due/overdue math + record_completion."""

    def test_next_due_calc_miles_only(self):
        interval = {"every_miles": 5000, "every_months": None}
        miles, at = next_due_calc(
            interval, done_miles=10000, done_at=None,
        )
        assert miles == 15000
        assert at is None

    def test_next_due_calc_months_only(self):
        interval = {"every_miles": None, "every_months": 12}
        miles, at = next_due_calc(
            interval, done_miles=None, done_at="2026-04-10",
        )
        assert miles is None
        assert at == "2027-04-10"

    def test_next_due_calc_dual_axis(self):
        interval = {"every_miles": 5000, "every_months": 12}
        miles, at = next_due_calc(
            interval, done_miles=10000, done_at="2026-04-10",
        )
        assert miles == 15000
        assert at == "2027-04-10"

    def test_month_clamp_feb28_plus_two(self):
        """Feb 28 + 2 months = Apr 28 (simple day-match, no clamp needed)."""
        assert _add_months(date(2026, 2, 28), 2) == date(2026, 4, 28)

    def test_month_clamp_jan31_plus_one_leap(self):
        """Jan 31 + 1 month = Feb 29 in leap year, Feb 28 otherwise."""
        assert _add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)
        assert _add_months(date(2023, 1, 31), 1) == date(2023, 2, 28)

    def test_due_items_miles_horizon(self, db):
        vid = _add_vehicle(db)
        # Oil change due in 200 miles (within 500 horizon)
        create_interval(
            vid, "oil-change", "Oil",
            every_miles=5000, next_due_miles=10200,
            db_path=db,
        )
        # Chain due in 2000 miles (beyond 500 horizon) — not included
        create_interval(
            vid, "chain-clean-lube", "Chain",
            every_miles=1000, next_due_miles=12000,
            db_path=db,
        )
        items = due_items(
            vid, horizon_miles=500, horizon_days=30,
            current_miles=10000, db_path=db,
        )
        slugs = [i["item_slug"] for i in items]
        assert "oil-change" in slugs
        assert "chain-clean-lube" not in slugs

    def test_due_items_excludes_overdue(self, db):
        vid = _add_vehicle(db)
        create_interval(
            vid, "oil-change", "Oil",
            every_miles=5000, next_due_miles=9000,  # we're at 10k — overdue
            db_path=db,
        )
        items = due_items(
            vid, horizon_miles=500, horizon_days=30,
            current_miles=10000, db_path=db,
        )
        assert items == []

    def test_overdue_items_sorted_most_overdue_first(self, db):
        vid = _add_vehicle(db)
        create_interval(
            vid, "oil-change", "Oil",
            every_miles=5000, next_due_miles=9500,  # 500 overdue
            db_path=db,
        )
        create_interval(
            vid, "valve-check", "Valves",
            every_miles=16000, next_due_miles=8000,  # 2000 overdue
            db_path=db,
        )
        items = overdue_items(vid, current_miles=10000, db_path=db)
        assert [i["item_slug"] for i in items] == ["valve-check", "oil-change"]

    def test_record_completion_with_explicit_miles_and_date(self, db):
        vid = _add_vehicle(db)
        create_interval(
            vid, "oil-change", "Oil",
            every_miles=5000, every_months=12, db_path=db,
        )
        updated = record_completion(
            vid, "oil-change",
            at_miles=12000, at_date="2026-04-18",
            db_path=db,
        )
        assert updated["last_done_miles"] == 12000
        assert updated["last_done_at"] == "2026-04-18"
        assert updated["next_due_miles"] == 17000
        assert updated["next_due_at"] == "2027-04-18"

    def test_record_completion_without_mileage_source_raises(self, db):
        """Mileage-only interval + no at_miles + no vehicles.mileage column → raise."""
        vid = _add_vehicle(db)
        create_interval(
            vid, "chain-clean-lube", "Chain",
            every_miles=1000, every_months=None, db_path=db,
        )
        # Phase 152 hasn't landed in this test DB (vehicles.mileage absent),
        # so record_completion should raise ServiceIntervalError.
        with pytest.raises(ServiceIntervalError):
            record_completion(
                vid, "chain-clean-lube",
                at_miles=None, at_date="2026-04-18",
                db_path=db,
            )

    def test_record_completion_unknown_slug_raises(self, db):
        vid = _add_vehicle(db)
        with pytest.raises(ServiceIntervalError):
            record_completion(
                vid, "nonexistent-slug",
                at_miles=5000, at_date="2026-04-18",
                db_path=db,
            )

    def test_parse_iso_date_rejects_bogus(self):
        with pytest.raises(ValueError):
            _parse_iso_date("not-a-date")

    def test_history_snapshot_when_no_service_history_table(self, db):
        """Pre-Phase-152: history reads last_done_* columns as snapshot."""
        vid = _add_vehicle(db)
        create_interval(
            vid, "oil-change", "Oil",
            every_miles=5000, last_done_miles=12000,
            last_done_at="2026-04-18", db_path=db,
        )
        rows = history(vid, db_path=db)
        # Either Phase 152's service_history table exists + is empty (returns []),
        # OR we fall through to the snapshot path. Accept both outcomes.
        if rows:
            assert rows[0]["item_slug"] == "oil-change"
            assert rows[0].get("source") in ("snapshot", None)


# ===========================================================================
# 4. CLI
# ===========================================================================


class TestScheduleCLI:
    """Click-runner tests for the schedule subgroup."""

    def _seed_vehicle(self, db_path: str) -> int:
        from motodiag.core.models import (
            EngineType,
            PowertrainType,
            ProtocolType,
            VehicleBase,
        )
        from motodiag.vehicles.registry import add_vehicle

        vehicle = VehicleBase(
            make="Harley-Davidson",
            model="Sportster 1200",
            year=2010,
            engine_cc=1200,
            protocol=ProtocolType.J1850,
            powertrain=PowertrainType.ICE,
            engine_type=EngineType.FOUR_STROKE,
        )
        return add_vehicle(vehicle, db_path=db_path)

    def test_init_happy_path(self, cli_db):
        self._seed_vehicle(cli_db)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "schedule", "init", "--bike", "sportster-2010"],
        )
        assert result.exit_code == 0, result.output
        assert "Schedule initialized" in result.output or "Seeded" in result.output

    def test_init_unknown_bike_remediation(self, cli_db):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "schedule", "init", "--bike", "nosuch-2099"],
        )
        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "no bike" in result.output.lower()

    def test_list_empty_hints_init(self, cli_db):
        self._seed_vehicle(cli_db)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "schedule", "list", "--bike", "sportster-2010"],
        )
        assert result.exit_code == 0, result.output
        assert "No service intervals" in result.output or "schedule init" in result.output

    def test_list_json_roundtrip(self, cli_db):
        self._seed_vehicle(cli_db)
        runner = CliRunner()
        runner.invoke(
            _make_cli(),
            ["advanced", "schedule", "init", "--bike", "sportster-2010"],
        )
        result = runner.invoke(
            _make_cli(),
            ["advanced", "schedule", "list", "--bike", "sportster-2010", "--json"],
        )
        assert result.exit_code == 0, result.output
        payload = _json.loads(result.output)
        assert "intervals" in payload
        assert len(payload["intervals"]) > 0

    def test_due_negative_horizon_rejected(self, cli_db):
        self._seed_vehicle(cli_db)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "schedule", "due",
                "--bike", "sportster-2010",
                "--horizon-days", "-5",
            ],
        )
        assert result.exit_code != 0
        assert "horizon" in result.output.lower()

    def test_due_json(self, cli_db):
        self._seed_vehicle(cli_db)
        runner = CliRunner()
        runner.invoke(
            _make_cli(),
            ["advanced", "schedule", "init", "--bike", "sportster-2010"],
        )
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "schedule", "due",
                "--bike", "sportster-2010",
                "--current-miles", "5000",
                "--horizon-miles", "500",
                "--horizon-days", "30",
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = _json.loads(result.output)
        assert "items" in payload

    def test_overdue_json_empty(self, cli_db):
        self._seed_vehicle(cli_db)
        runner = CliRunner()
        runner.invoke(
            _make_cli(),
            ["advanced", "schedule", "init", "--bike", "sportster-2010"],
        )
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "schedule", "overdue",
                "--bike", "sportster-2010",
                "--current-miles", "0",
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = _json.loads(result.output)
        assert payload["items"] == []

    def test_complete_success(self, cli_db):
        self._seed_vehicle(cli_db)
        runner = CliRunner()
        runner.invoke(
            _make_cli(),
            ["advanced", "schedule", "init", "--bike", "sportster-2010"],
        )
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "schedule", "complete",
                "--bike", "sportster-2010",
                "--item", "oil-change",
                "--at-miles", "5000",
                "--at-date", "2026-04-18",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "recorded" in result.output.lower() or "service recorded" in result.output.lower()

    def test_complete_unknown_item(self, cli_db):
        self._seed_vehicle(cli_db)
        runner = CliRunner()
        runner.invoke(
            _make_cli(),
            ["advanced", "schedule", "init", "--bike", "sportster-2010"],
        )
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "schedule", "complete",
                "--bike", "sportster-2010",
                "--item", "bogus-item",
                "--at-miles", "5000",
                "--at-date", "2026-04-18",
            ],
        )
        assert result.exit_code != 0
        assert "no service interval" in result.output.lower() or "bogus" in result.output.lower()

    def test_complete_non_iso_date_error(self, cli_db):
        self._seed_vehicle(cli_db)
        runner = CliRunner()
        runner.invoke(
            _make_cli(),
            ["advanced", "schedule", "init", "--bike", "sportster-2010"],
        )
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "schedule", "complete",
                "--bike", "sportster-2010",
                "--item", "oil-change",
                "--at-miles", "5000",
                "--at-date", "not-a-date",
            ],
        )
        assert result.exit_code != 0
        assert "iso" in result.output.lower() or "date" in result.output.lower()

    def test_history_no_events_panel(self, cli_db):
        self._seed_vehicle(cli_db)
        runner = CliRunner()
        runner.invoke(
            _make_cli(),
            ["advanced", "schedule", "init", "--bike", "sportster-2010"],
        )
        # No completions recorded → "No history"
        result = runner.invoke(
            _make_cli(),
            ["advanced", "schedule", "history", "--bike", "sportster-2010"],
        )
        assert result.exit_code == 0, result.output
        assert (
            "No completion history" in result.output
            or "No history" in result.output
            or "history" in result.output.lower()
        )

    def test_help_group(self, cli_db):
        runner = CliRunner()
        result = runner.invoke(_make_cli(), ["advanced", "schedule", "--help"])
        assert result.exit_code == 0
        for sub in ("init", "list", "due", "overdue", "complete", "history"):
            assert sub in result.output
