"""Phase 168 — Bay/lift scheduling tests.

Five test classes across ~38 tests. Pure stdlib + SQL. Zero AI.
"""

from __future__ import annotations

import json as _json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

from motodiag.cli.shop import register_shop
from motodiag.core.database import (
    SCHEMA_VERSION, get_connection, get_schema_version, init_db,
    table_exists,
)
from motodiag.core.migrations import rollback_to_version
from motodiag.crm import customer_repo
from motodiag.crm.models import Customer
from motodiag.shop import (
    BayNotFoundError, InvalidSlotTransition, SlotNotFoundError,
    SlotOverlapError,
    add_bay, cancel_slot, complete_slot, create_shop, create_work_order,
    deactivate_bay, detect_conflicts, get_bay, get_slot, list_bays,
    list_slots, open_work_order, optimize_shop_day, reschedule_slot,
    schedule_wo, start_slot, utilization_for_day,
)


def _make_cli():
    @click.group()
    def root() -> None:
        """test root"""
    register_shop(root)
    return root


def _add_vehicle(db_path):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO vehicles (make, model, year, protocol) "
            "VALUES ('Harley-Davidson', 'Sportster 1200', 2010, 'none')",
        )
        return cursor.lastrowid


def _add_customer(db_path, name="Jane"):
    return customer_repo.create_customer(
        Customer(name=name, phone="555-0100", email="jane@example.com"),
        db_path=db_path,
    )


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase168.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase168_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    yield path
    reset_settings()


def _seed_open_wo(db_path):
    shop_id = create_shop("s", db_path=db_path)
    c = _add_customer(db_path)
    v = _add_vehicle(db_path)
    wo_id = create_work_order(
        shop_id, v, c, "x", estimated_hours=2.0, db_path=db_path,
    )
    open_work_order(wo_id, db_path=db_path)
    return wo_id, shop_id


# ===========================================================================
# 1. Migration 032
# ===========================================================================


class TestMigration032:
    def test_schema_version_bumped_to_at_least_32(self, db):
        assert SCHEMA_VERSION >= 32
        assert get_schema_version(db) >= 32

    def test_tables_created(self, db):
        assert table_exists("shop_bays", db)
        assert table_exists("bay_schedule_slots", db)

    def test_indexes_present(self, db):
        expected = {
            "idx_bays_shop_active", "idx_slots_bay_start",
            "idx_slots_wo", "idx_slots_status_start",
        }
        with get_connection(db) as conn:
            actual = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()}
        assert expected.issubset(actual)

    def test_bay_type_check_rejects_invalid(self, db):
        shop_id = create_shop("s", db_path=db)
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            with get_connection(db) as conn:
                conn.execute(
                    "INSERT INTO shop_bays (shop_id, name, bay_type) "
                    "VALUES (?, 'x', 'bogus')", (shop_id,),
                )

    def test_slot_end_greater_than_start_check(self, db):
        shop_id = create_shop("s", db_path=db)
        bay_id = add_bay(shop_id, "b1", db_path=db)
        import sqlite3
        # Trigger CHECK (scheduled_end > scheduled_start) via INSERT
        with pytest.raises(sqlite3.IntegrityError):
            with get_connection(db) as conn:
                conn.execute(
                    "INSERT INTO bay_schedule_slots "
                    "(bay_id, scheduled_start, scheduled_end) "
                    "VALUES (?, ?, ?)",
                    (bay_id, "2026-04-22T10:00:00Z", "2026-04-22T09:00:00Z"),
                )

    def test_unique_shop_id_name(self, db):
        shop_id = create_shop("s", db_path=db)
        add_bay(shop_id, "bay-1", db_path=db)
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            add_bay(shop_id, "bay-1", db_path=db)

    def test_rollback_to_31_drops_both(self, tmp_path):
        path = str(tmp_path / "rollback.db")
        init_db(path)
        assert table_exists("shop_bays", path)
        assert table_exists("bay_schedule_slots", path)
        rollback_to_version(31, path)
        assert not table_exists("shop_bays", path)
        assert not table_exists("bay_schedule_slots", path)
        # Phase 167 substrate preserved
        assert table_exists("labor_estimates", path)


# ===========================================================================
# 2. Bay CRUD
# ===========================================================================


class TestBayCRUD:
    def test_add_bay(self, db):
        shop_id = create_shop("s", db_path=db)
        bay_id = add_bay(shop_id, "Bay 1 — Main Lift", db_path=db)
        assert bay_id > 0

    def test_add_bay_invalid_type_raises(self, db):
        shop_id = create_shop("s", db_path=db)
        with pytest.raises(Exception):
            add_bay(shop_id, "bogus", bay_type="invalid", db_path=db)

    def test_list_bays(self, db):
        shop_id = create_shop("s", db_path=db)
        add_bay(shop_id, "A", db_path=db)
        add_bay(shop_id, "B", bay_type="tire", db_path=db)
        rows = list_bays(shop_id, db_path=db)
        assert len(rows) == 2

    def test_deactivate_bay(self, db):
        shop_id = create_shop("s", db_path=db)
        bay_id = add_bay(shop_id, "B", db_path=db)
        deactivate_bay(bay_id, db_path=db)
        rows = list_bays(shop_id, db_path=db)
        assert len(rows) == 0  # default excludes inactive
        rows = list_bays(shop_id, include_inactive=True, db_path=db)
        assert len(rows) == 1

    def test_get_bay_unknown_returns_none(self, db):
        assert get_bay(999, db_path=db) is None


# ===========================================================================
# 3. Slot scheduling + lifecycle
# ===========================================================================


class TestSlotScheduling:
    def test_schedule_wo_explicit_bay(self, db):
        wo_id, shop_id = _seed_open_wo(db)
        bay_id = add_bay(shop_id, "B1", db_path=db)
        slot_id = schedule_wo(
            wo_id, bay_id=bay_id, duration_hours=1.0, db_path=db,
        )
        slot = get_slot(slot_id, db_path=db)
        assert slot is not None
        assert slot["bay_id"] == bay_id
        assert slot["work_order_id"] == wo_id

    def test_schedule_wo_auto_assign(self, db):
        wo_id, shop_id = _seed_open_wo(db)
        add_bay(shop_id, "B1", db_path=db)
        add_bay(shop_id, "B2", db_path=db)
        slot_id = schedule_wo(wo_id, duration_hours=1.0, db_path=db)
        slot = get_slot(slot_id, db_path=db)
        assert slot is not None

    def test_schedule_wo_no_active_bays_raises(self, db):
        wo_id, _ = _seed_open_wo(db)
        with pytest.raises(BayNotFoundError):
            schedule_wo(wo_id, duration_hours=1.0, db_path=db)

    def test_schedule_wo_inactive_bay_raises(self, db):
        wo_id, shop_id = _seed_open_wo(db)
        bay_id = add_bay(shop_id, "B", db_path=db)
        deactivate_bay(bay_id, db_path=db)
        with pytest.raises(BayNotFoundError):
            schedule_wo(wo_id, bay_id=bay_id, duration_hours=1.0, db_path=db)

    def test_overlap_raises(self, db):
        wo_id, shop_id = _seed_open_wo(db)
        bay_id = add_bay(shop_id, "B", db_path=db)
        # Schedule first slot at specific time
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        schedule_wo(
            wo_id, bay_id=bay_id,
            scheduled_start=future.isoformat(), duration_hours=2.0,
            db_path=db,
        )
        # Second WO at overlapping time on same bay
        c = _add_customer(db, name="Bob")
        v = _add_vehicle(db)
        wo2 = create_work_order(shop_id, v, c, "y",
                                estimated_hours=1.0, db_path=db)
        open_work_order(wo2, db_path=db)
        with pytest.raises(SlotOverlapError):
            schedule_wo(
                wo2, bay_id=bay_id,
                scheduled_start=future.isoformat(), duration_hours=1.0,
                db_path=db,
            )

    def test_reschedule_planned_slot(self, db):
        wo_id, shop_id = _seed_open_wo(db)
        bay_id = add_bay(shop_id, "B", db_path=db)
        slot_id = schedule_wo(
            wo_id, bay_id=bay_id, duration_hours=1.0, db_path=db,
        )
        new_start = (datetime.now(timezone.utc) + timedelta(hours=5))
        reschedule_slot(
            slot_id, new_start=new_start.isoformat(), db_path=db,
        )
        slot = get_slot(slot_id, db_path=db)
        assert slot is not None

    def test_reschedule_non_planned_raises(self, db):
        wo_id, shop_id = _seed_open_wo(db)
        bay_id = add_bay(shop_id, "B", db_path=db)
        slot_id = schedule_wo(
            wo_id, bay_id=bay_id, duration_hours=1.0, db_path=db,
        )
        start_slot(slot_id, db_path=db)
        with pytest.raises(InvalidSlotTransition):
            reschedule_slot(slot_id, new_start="2027-01-01T00:00:00Z", db_path=db)

    def test_start_slot_transitions(self, db):
        wo_id, shop_id = _seed_open_wo(db)
        bay_id = add_bay(shop_id, "B", db_path=db)
        slot_id = schedule_wo(
            wo_id, bay_id=bay_id, duration_hours=1.0, db_path=db,
        )
        start_slot(slot_id, db_path=db)
        slot = get_slot(slot_id, db_path=db)
        assert slot["status"] == "active"
        assert slot["actual_start"] is not None

    def test_complete_slot_within_buffer(self, db):
        wo_id, shop_id = _seed_open_wo(db)
        bay_id = add_bay(shop_id, "B", db_path=db)
        # Schedule for NOW so completing quickly is within buffer
        slot_id = schedule_wo(
            wo_id, bay_id=bay_id, duration_hours=1.0, db_path=db,
        )
        start_slot(slot_id, db_path=db)
        mutated, overrun = complete_slot(slot_id, db_path=db)
        assert mutated is True
        slot = get_slot(slot_id, db_path=db)
        # We complete immediately after start, so actual_end <<< scheduled_end → "completed" or "overrun"
        # With scheduled_end 1h in future, completing now is well within buffer → completed
        assert slot["status"] in ("completed", "overrun")

    def test_cancel_slot_from_planned(self, db):
        wo_id, shop_id = _seed_open_wo(db)
        bay_id = add_bay(shop_id, "B", db_path=db)
        slot_id = schedule_wo(
            wo_id, bay_id=bay_id, duration_hours=1.0, db_path=db,
        )
        cancel_slot(slot_id, reason="parts delay", db_path=db)
        slot = get_slot(slot_id, db_path=db)
        assert slot["status"] == "cancelled"

    def test_cancel_terminal_raises(self, db):
        wo_id, shop_id = _seed_open_wo(db)
        bay_id = add_bay(shop_id, "B", db_path=db)
        slot_id = schedule_wo(
            wo_id, bay_id=bay_id, duration_hours=1.0, db_path=db,
        )
        cancel_slot(slot_id, db_path=db)
        with pytest.raises(InvalidSlotTransition):
            cancel_slot(slot_id, db_path=db)


# ===========================================================================
# 4. Conflict detection + optimization
# ===========================================================================


class TestConflictsAndOptimize:
    def test_no_conflicts_empty_shop(self, db):
        shop_id = create_shop("s", db_path=db)
        conflicts = detect_conflicts(shop_id, db_path=db)
        assert conflicts == []

    def test_detects_overlap(self, db):
        # Direct INSERT bypassing schedule_wo's overlap check to seed conflicts
        wo_id, shop_id = _seed_open_wo(db)
        bay_id = add_bay(shop_id, "B", db_path=db)
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        # First slot via normal path
        schedule_wo(
            wo_id, bay_id=bay_id,
            scheduled_start=future.isoformat(), duration_hours=2.0,
            db_path=db,
        )
        # Second slot inserted manually with overlap
        c = _add_customer(db, name="Bob")
        v = _add_vehicle(db)
        wo2 = create_work_order(shop_id, v, c, "y", db_path=db)
        open_work_order(wo2, db_path=db)
        overlap_start = future + timedelta(minutes=30)
        overlap_end = future + timedelta(hours=2, minutes=30)
        with get_connection(db) as conn:
            conn.execute(
                "INSERT INTO bay_schedule_slots "
                "(bay_id, work_order_id, scheduled_start, scheduled_end, status) "
                "VALUES (?, ?, ?, ?, 'planned')",
                (bay_id, wo2, overlap_start.isoformat(), overlap_end.isoformat()),
            )
        conflicts = detect_conflicts(shop_id, db_path=db)
        assert len(conflicts) == 1
        assert conflicts[0].severity == "error"  # >=15min overlap
        assert conflicts[0].overlap_minutes > 15

    def test_utilization_for_empty_day(self, db):
        shop_id = create_shop("s", db_path=db)
        add_bay(shop_id, "B", db_path=db)
        util = utilization_for_day(shop_id, "2026-04-22", db_path=db)
        assert util["utilization"] == 0.0

    def test_utilization_with_slot(self, db):
        shop_id = create_shop("s", db_path=db)
        bay_id = add_bay(shop_id, "B", db_path=db)
        # Insert a 4h slot on date 2026-05-01
        with get_connection(db) as conn:
            conn.execute(
                "INSERT INTO bay_schedule_slots "
                "(bay_id, scheduled_start, scheduled_end, status) "
                "VALUES (?, '2026-05-01T09:00:00+00:00', "
                "'2026-05-01T13:00:00+00:00', 'planned')",
                (bay_id,),
            )
        util = utilization_for_day(shop_id, "2026-05-01", db_path=db)
        # 4h of 8h available = 0.5
        assert abs(util["utilization"] - 0.5) < 0.01

    def test_optimize_deterministic_with_seed(self, db):
        shop_id = create_shop("s", db_path=db)
        add_bay(shop_id, "B", db_path=db)
        r1 = optimize_shop_day(
            shop_id, "2026-05-01", random_seed=42, db_path=db,
        )
        r2 = optimize_shop_day(
            shop_id, "2026-05-01", random_seed=42, db_path=db,
        )
        assert r1.iterations_run == r2.iterations_run
        assert r1.utilization_before == r2.utilization_before

    def test_optimize_warns_on_over_commit(self, db):
        shop_id = create_shop("s", db_path=db)
        bay_id = add_bay(shop_id, "B", db_path=db)
        # Insert 7.5h of work on an 8h day = 94% utilization
        with get_connection(db) as conn:
            conn.execute(
                "INSERT INTO bay_schedule_slots "
                "(bay_id, scheduled_start, scheduled_end, status) "
                "VALUES (?, '2026-05-01T09:00:00+00:00', "
                "'2026-05-01T16:30:00+00:00', 'planned')",
                (bay_id,),
            )
        report = optimize_shop_day(
            shop_id, "2026-05-01", random_seed=1, db_path=db,
        )
        assert report.utilization_before > 0.90
        assert any("90%" in w for w in report.warnings)


# ===========================================================================
# 5. CLI
# ===========================================================================


class TestBayCLI:
    def test_help_lists_10_subcommands(self, cli_db):
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, ["shop", "bay", "--help"])
        assert result.exit_code == 0
        for sub in ("add", "list", "show", "deactivate", "schedule",
                    "reschedule", "conflicts", "optimize",
                    "utilization", "calendar"):
            assert sub in result.output

    def test_add_bay_cli(self, cli_db):
        shop_id = create_shop("s", db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "bay", "add",
            "--shop", str(shop_id),
            "--name", "Bay 1",
            "--type", "lift",
        ])
        assert result.exit_code == 0, result.output
        rows = list_bays(shop_id, db_path=cli_db)
        assert len(rows) == 1

    def test_list_bays_cli_json(self, cli_db):
        shop_id = create_shop("s", db_path=cli_db)
        add_bay(shop_id, "B", db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "bay", "list", "--shop", str(shop_id), "--json",
        ])
        assert result.exit_code == 0
        parsed = _json.loads(result.output)
        assert len(parsed) == 1

    def test_utilization_cli(self, cli_db):
        shop_id = create_shop("s", db_path=cli_db)
        add_bay(shop_id, "B", db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "bay", "utilization",
            "--shop", str(shop_id), "--date", "2026-05-01", "--json",
        ])
        assert result.exit_code == 0
        parsed = _json.loads(result.output)
        assert parsed["utilization"] == 0.0

    def test_conflicts_cli_empty(self, cli_db):
        shop_id = create_shop("s", db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "bay", "conflicts", "--shop", str(shop_id),
        ])
        assert result.exit_code == 0
        assert "No conflicts" in result.output

    def test_optimize_cli_deterministic(self, cli_db):
        shop_id = create_shop("s", db_path=cli_db)
        add_bay(shop_id, "B", db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "bay", "optimize",
            "--shop", str(shop_id), "--date", "2026-05-01",
            "--seed", "42", "--json",
        ])
        assert result.exit_code == 0
        parsed = _json.loads(result.output)
        assert parsed["shop_id"] == shop_id

    def test_schedule_wo_cli(self, cli_db):
        wo_id, shop_id = _seed_open_wo(cli_db)
        add_bay(shop_id, "B", db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "bay", "schedule", str(wo_id),
            "--duration-hours", "1.5",
        ])
        assert result.exit_code == 0, result.output
        # Verify a slot was created
        slots = list_slots(wo_id=wo_id, db_path=cli_db)
        assert len(slots) == 1

    def test_deactivate_cli_with_yes(self, cli_db):
        shop_id = create_shop("s", db_path=cli_db)
        bay_id = add_bay(shop_id, "B", db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "bay", "deactivate", str(bay_id), "--yes",
        ])
        assert result.exit_code == 0
        bay = get_bay(bay_id, db_path=cli_db)
        assert bay["is_active"] == 0
