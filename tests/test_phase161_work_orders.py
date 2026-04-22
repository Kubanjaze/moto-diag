"""Phase 161 — Work order system tests.

Four test classes across ~45 tests:

- :class:`TestMigration026` (5) — schema-version bump to >=26,
  `work_orders` table + 4 indexes present, status CHECK enforced,
  priority CHECK enforced (1-5), rollback drops table cleanly.
- :class:`TestWorkOrderRepo` (18) — CRUD roundtrip, missing-FK pre-checks
  (shop/customer/vehicle), intake-mismatch rejection, priority
  validation, hours validation, list filter composition, all 7
  lifecycle transitions (open / start / pause / resume / complete /
  cancel / reopen), invalid transitions raise, reopen clears terminal
  fields, update whitelist cannot mutate status.
- :class:`TestIntakeLinkage` (8) — 1:N intake→WOs, intake delete sets
  intake_visit_id=NULL on surviving WOs, shop delete cascades WOs,
  customer/vehicle RESTRICT when WOs exist, auto-fill from --intake CLI.
- :class:`TestWorkOrderCLI` (14) — create happy/mutex/missing-intake,
  list with filters + JSON, show + JSON, update --set, start/pause/resume/
  complete lifecycle CLI round-trip, cancel with --yes, reopen with --yes,
  assign/unassign, invalid transition surfaces clean error.

All tests are SW + SQL only. Zero AI calls, zero network, zero live
tokens.
"""

from __future__ import annotations

import json as _json

import click
import pytest
from click.testing import CliRunner

from motodiag.cli.shop import register_shop
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
from motodiag.crm import customer_repo
from motodiag.crm.models import Customer
from motodiag.shop import (
    InvalidWorkOrderTransition,
    WORK_ORDER_STATUSES,
    WorkOrderFKError,
    WorkOrderNotFoundError,
    assign_mechanic,
    cancel_intake,
    cancel_work_order,
    close_intake,
    complete_work_order,
    count_work_orders,
    create_intake,
    create_shop,
    create_work_order,
    delete_shop,
    get_intake,
    get_work_order,
    list_work_orders,
    open_work_order,
    pause_work,
    reopen_work_order,
    require_work_order,
    resume_work,
    start_work,
    unassign_mechanic,
    update_work_order,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_cli():
    @click.group()
    def root() -> None:
        """test root"""

    register_shop(root)
    return root


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase161.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase161_cli.db")
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
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO vehicles (make, model, year, protocol) "
            "VALUES (?, ?, ?, 'none')",
            (make, model, year),
        )
        return cursor.lastrowid


def _add_customer(
    db_path: str, name: str = "Jane Doe",
    phone: str = "555-0100", email: str = "jane@example.com",
) -> int:
    customer = Customer(name=name, phone=phone, email=email)
    return customer_repo.create_customer(customer, db_path=db_path)


def _setup_triple(db_path: str) -> tuple[int, int, int]:
    shop_id = create_shop("s", db_path=db_path)
    customer_id = _add_customer(db_path)
    vehicle_id = _add_vehicle(db_path)
    return shop_id, customer_id, vehicle_id


# ===========================================================================
# 1. Migration 026
# ===========================================================================


class TestMigration026:

    def test_schema_version_bumped_to_at_least_26(self, db):
        assert SCHEMA_VERSION >= 26
        assert get_schema_version(db) >= 26

    def test_work_orders_table_created(self, db):
        assert table_exists("work_orders", db) is True

    def test_indexes_present(self, db):
        expected = {
            "idx_wo_shop_status",
            "idx_wo_vehicle",
            "idx_wo_customer",
            "idx_wo_intake_visit",
        }
        with get_connection(db) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
            actual = {r[0] for r in rows}
        assert expected.issubset(actual)

    def test_status_check_and_priority_check_enforced(self, db):
        shop_id, c, v = _setup_triple(db)
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            with get_connection(db) as conn:
                conn.execute(
                    "INSERT INTO work_orders "
                    "(shop_id, vehicle_id, customer_id, title, status) "
                    "VALUES (?, ?, ?, ?, 'bogus')",
                    (shop_id, v, c, "bad status"),
                )
        with pytest.raises(sqlite3.IntegrityError):
            with get_connection(db) as conn:
                conn.execute(
                    "INSERT INTO work_orders "
                    "(shop_id, vehicle_id, customer_id, title, priority) "
                    "VALUES (?, ?, ?, ?, 9)",
                    (shop_id, v, c, "bad priority"),
                )

    def test_rollback_drops_work_orders_table(self, tmp_path):
        """work_orders rolls back cleanly; Phase 160 tables preserved.

        Forward-compat: when later migrations (Phase 162+ issues, etc.)
        add FKs into work_orders, those must be rolled back first.
        Use rollback_to_version(target=25) to peel everything above 25
        in reverse-version order — that drops migration 026 (Phase 161)
        plus any later migrations that reference work_orders.
        """
        from motodiag.core.migrations import rollback_to_version

        path = str(tmp_path / "rollback.db")
        init_db(path)
        assert table_exists("work_orders", path) is True
        rollback_to_version(25, path)
        assert table_exists("work_orders", path) is False
        # Phase 160 tables should still exist.
        assert table_exists("shops", path) is True
        assert table_exists("intake_visits", path) is True


# ===========================================================================
# 2. work_order_repo CRUD + lifecycle
# ===========================================================================


class TestWorkOrderRepo:

    def test_create_and_get_roundtrip_with_denorm(self, db):
        shop_id, c, v = _setup_triple(db)
        wo_id = create_work_order(
            shop_id=shop_id, vehicle_id=v, customer_id=c,
            title="rear brake pad replacement",
            description="squealing on stops",
            priority=2, estimated_hours=1.5,
            db_path=db,
        )
        row = get_work_order(wo_id, db_path=db)
        assert row is not None
        assert row["status"] == "draft"
        assert row["title"] == "rear brake pad replacement"
        assert row["priority"] == 2
        assert row["estimated_hours"] == 1.5
        assert row["shop_name"] == "s"
        assert row["customer_name"] == "Jane Doe"
        assert row["vehicle_make"] == "Harley-Davidson"

    def test_create_missing_shop_raises(self, db):
        c = _add_customer(db)
        v = _add_vehicle(db)
        with pytest.raises(ValueError, match="shop"):
            create_work_order(
                shop_id=999, vehicle_id=v, customer_id=c,
                title="x", db_path=db,
            )

    def test_create_missing_customer_raises(self, db):
        shop_id = create_shop("s", db_path=db)
        v = _add_vehicle(db)
        with pytest.raises(ValueError, match="customer"):
            create_work_order(
                shop_id=shop_id, vehicle_id=v, customer_id=999,
                title="x", db_path=db,
            )

    def test_create_missing_vehicle_raises(self, db):
        shop_id = create_shop("s", db_path=db)
        c = _add_customer(db)
        with pytest.raises(ValueError, match="vehicle"):
            create_work_order(
                shop_id=shop_id, vehicle_id=999, customer_id=c,
                title="x", db_path=db,
            )

    def test_create_rejects_empty_title(self, db):
        shop_id, c, v = _setup_triple(db)
        with pytest.raises(ValueError, match="title"):
            create_work_order(
                shop_id=shop_id, vehicle_id=v, customer_id=c,
                title="   ", db_path=db,
            )

    def test_create_intake_mismatch_rejects(self, db):
        shop_id, c, v = _setup_triple(db)
        v2 = _add_vehicle(db, model="Road Glide")  # different bike
        intake_id = create_intake(shop_id, c, v, db_path=db)
        # vehicle_id doesn't match the intake's bike → must raise.
        with pytest.raises(ValueError, match="vehicle_id"):
            create_work_order(
                shop_id=shop_id, vehicle_id=v2, customer_id=c,
                title="x", intake_visit_id=intake_id, db_path=db,
            )

    def test_priority_validation(self, db):
        shop_id, c, v = _setup_triple(db)
        with pytest.raises(ValueError):
            create_work_order(
                shop_id=shop_id, vehicle_id=v, customer_id=c,
                title="x", priority=0, db_path=db,
            )
        with pytest.raises(ValueError):
            create_work_order(
                shop_id=shop_id, vehicle_id=v, customer_id=c,
                title="x", priority=6, db_path=db,
            )

    def test_hours_validation(self, db):
        shop_id, c, v = _setup_triple(db)
        with pytest.raises(ValueError):
            create_work_order(
                shop_id=shop_id, vehicle_id=v, customer_id=c,
                title="x", estimated_hours=-0.5, db_path=db,
            )

    def test_lifecycle_happy_path_open_start_complete(self, db):
        shop_id, c, v = _setup_triple(db)
        wo_id = create_work_order(
            shop_id=shop_id, vehicle_id=v, customer_id=c,
            title="oil change", db_path=db,
        )
        assert open_work_order(wo_id, db_path=db) is True
        row = get_work_order(wo_id, db_path=db)
        assert row["status"] == "open"
        assert row["opened_at"] is not None

        assert start_work(wo_id, db_path=db) is True
        row = get_work_order(wo_id, db_path=db)
        assert row["status"] == "in_progress"
        assert row["started_at"] is not None

        assert complete_work_order(
            wo_id, actual_hours=0.75, db_path=db,
        ) is True
        row = get_work_order(wo_id, db_path=db)
        assert row["status"] == "completed"
        assert row["completed_at"] is not None
        assert row["closed_at"] is not None
        assert row["actual_hours"] == 0.75

    def test_pause_and_resume(self, db):
        shop_id, c, v = _setup_triple(db)
        wo_id = create_work_order(
            shop_id=shop_id, vehicle_id=v, customer_id=c,
            title="x", db_path=db,
        )
        open_work_order(wo_id, db_path=db)
        start_work(wo_id, db_path=db)
        pause_work(wo_id, reason="parts on order", db_path=db)
        row = get_work_order(wo_id, db_path=db)
        assert row["status"] == "on_hold"
        assert row["on_hold_reason"] == "parts on order"

        resume_work(wo_id, db_path=db)
        row = get_work_order(wo_id, db_path=db)
        assert row["status"] == "in_progress"
        assert row["on_hold_reason"] is None

    def test_resume_from_open_raises_clear_error(self, db):
        shop_id, c, v = _setup_triple(db)
        wo_id = create_work_order(
            shop_id=shop_id, vehicle_id=v, customer_id=c,
            title="x", db_path=db,
        )
        open_work_order(wo_id, db_path=db)
        with pytest.raises(InvalidWorkOrderTransition, match="on_hold"):
            resume_work(wo_id, db_path=db)

    def test_cancel_from_draft_allowed(self, db):
        shop_id, c, v = _setup_triple(db)
        wo_id = create_work_order(
            shop_id=shop_id, vehicle_id=v, customer_id=c,
            title="x", db_path=db,
        )
        cancel_work_order(wo_id, reason="customer-withdrew", db_path=db)
        row = get_work_order(wo_id, db_path=db)
        assert row["status"] == "cancelled"
        assert row["cancellation_reason"] == "customer-withdrew"
        assert row["closed_at"] is not None

    def test_invalid_transition_draft_to_completed_raises(self, db):
        shop_id, c, v = _setup_triple(db)
        wo_id = create_work_order(
            shop_id=shop_id, vehicle_id=v, customer_id=c,
            title="x", db_path=db,
        )
        with pytest.raises(InvalidWorkOrderTransition):
            complete_work_order(wo_id, db_path=db)

    def test_invalid_transition_completed_to_in_progress_raises(self, db):
        shop_id, c, v = _setup_triple(db)
        wo_id = create_work_order(
            shop_id=shop_id, vehicle_id=v, customer_id=c,
            title="x", db_path=db,
        )
        open_work_order(wo_id, db_path=db)
        start_work(wo_id, db_path=db)
        complete_work_order(wo_id, db_path=db)
        with pytest.raises(InvalidWorkOrderTransition):
            start_work(wo_id, db_path=db)

    def test_reopen_clears_terminal_fields(self, db):
        shop_id, c, v = _setup_triple(db)
        wo_id = create_work_order(
            shop_id=shop_id, vehicle_id=v, customer_id=c,
            title="x", db_path=db,
        )
        open_work_order(wo_id, db_path=db)
        start_work(wo_id, db_path=db)
        complete_work_order(wo_id, db_path=db)
        reopen_work_order(wo_id, db_path=db)
        row = get_work_order(wo_id, db_path=db)
        assert row["status"] == "open"
        assert row["completed_at"] is None
        assert row["closed_at"] is None
        assert row["cancellation_reason"] is None
        assert row["on_hold_reason"] is None

    def test_update_whitelist_cannot_mutate_status(self, db):
        shop_id, c, v = _setup_triple(db)
        wo_id = create_work_order(
            shop_id=shop_id, vehicle_id=v, customer_id=c,
            title="orig", db_path=db,
        )
        update_work_order(
            wo_id, {
                "title": "new", "priority": 1,
                "status": "completed",         # must be ignored
                "completed_at": "2099-01-01",  # must be ignored
                "evil_field": "x",             # must be ignored
            },
            db_path=db,
        )
        row = get_work_order(wo_id, db_path=db)
        assert row["title"] == "new"
        assert row["priority"] == 1
        assert row["status"] == "draft"     # still draft
        assert row["completed_at"] is None

    def test_list_filters_compose(self, db):
        s1 = create_shop("s1", db_path=db)
        s2 = create_shop("s2", db_path=db)
        c = _add_customer(db)
        v = _add_vehicle(db)
        wo1 = create_work_order(s1, v, c, "a", db_path=db)
        wo2 = create_work_order(s2, v, c, "b", priority=1, db_path=db)
        open_work_order(wo2, db_path=db)
        # Default (exclude terminal) — both should come back.
        rows = list_work_orders(db_path=db)
        assert {r["id"] for r in rows} == {wo1, wo2}
        # By shop.
        rows = list_work_orders(shop_id=s1, db_path=db)
        assert {r["id"] for r in rows} == {wo1}
        # By priority.
        rows = list_work_orders(priority=1, db_path=db)
        assert {r["id"] for r in rows} == {wo2}
        # By status explicit.
        rows = list_work_orders(status="draft", db_path=db)
        assert {r["id"] for r in rows} == {wo1}

    def test_list_excludes_terminal_by_default(self, db):
        shop_id, c, v = _setup_triple(db)
        wo1 = create_work_order(shop_id, v, c, "a", db_path=db)
        wo2 = create_work_order(shop_id, v, c, "b", db_path=db)
        cancel_work_order(wo1, db_path=db)
        rows = list_work_orders(db_path=db)
        assert {r["id"] for r in rows} == {wo2}
        rows_all = list_work_orders(include_terminal=True, db_path=db)
        assert {r["id"] for r in rows_all} == {wo1, wo2}

    def test_assign_and_unassign_mechanic(self, db):
        shop_id, c, v = _setup_triple(db)
        wo_id = create_work_order(shop_id, v, c, "x", db_path=db)
        # Use seeded system user id=1 (created by Phase 112 migration 005).
        assign_mechanic(wo_id, 1, db_path=db)
        row = get_work_order(wo_id, db_path=db)
        assert row["assigned_mechanic_user_id"] == 1
        unassign_mechanic(wo_id, db_path=db)
        row = get_work_order(wo_id, db_path=db)
        assert row["assigned_mechanic_user_id"] is None

    def test_require_work_order_raises_on_missing(self, db):
        with pytest.raises(WorkOrderNotFoundError):
            require_work_order(999, db_path=db)

    def test_count_work_orders_filter_composition(self, db):
        s1 = create_shop("s1", db_path=db)
        s2 = create_shop("s2", db_path=db)
        c = _add_customer(db)
        v = _add_vehicle(db)
        create_work_order(s1, v, c, "a", db_path=db)
        create_work_order(s1, v, c, "b", db_path=db)
        create_work_order(s2, v, c, "c", db_path=db)
        assert count_work_orders(db_path=db) == 3
        assert count_work_orders(shop_id=s1, db_path=db) == 2
        assert count_work_orders(shop_id=s1, status="draft", db_path=db) == 2
        assert count_work_orders(shop_id=s1, status="completed", db_path=db) == 0


# ===========================================================================
# 3. Intake linkage + FK semantics
# ===========================================================================


class TestIntakeLinkage:

    def test_one_intake_many_work_orders(self, db):
        shop_id, c, v = _setup_triple(db)
        intake_id = create_intake(shop_id, c, v, db_path=db)
        wo1 = create_work_order(
            shop_id, v, c, "brakes",
            intake_visit_id=intake_id, db_path=db,
        )
        wo2 = create_work_order(
            shop_id, v, c, "oil leak",
            intake_visit_id=intake_id, db_path=db,
        )
        wo3 = create_work_order(
            shop_id, v, c, "new tires",
            intake_visit_id=intake_id, db_path=db,
        )
        rows = list_work_orders(intake_visit_id=intake_id, db_path=db)
        assert {r["id"] for r in rows} == {wo1, wo2, wo3}

    def test_intake_delete_orphans_work_orders_with_null(self, db):
        shop_id, c, v = _setup_triple(db)
        intake_id = create_intake(shop_id, c, v, db_path=db)
        wo_id = create_work_order(
            shop_id, v, c, "x",
            intake_visit_id=intake_id, db_path=db,
        )
        # Delete the intake directly (ON DELETE SET NULL on intake_visit_id).
        with get_connection(db) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                "DELETE FROM intake_visits WHERE id = ?", (intake_id,),
            )
        row = get_work_order(wo_id, db_path=db)
        assert row is not None  # WO survived
        assert row["intake_visit_id"] is None
        assert row["status"] == "draft"

    def test_shop_delete_cascades_work_orders(self, db):
        shop_id, c, v = _setup_triple(db)
        wo_id = create_work_order(shop_id, v, c, "x", db_path=db)
        delete_shop(shop_id, db_path=db)
        assert get_work_order(wo_id, db_path=db) is None

    def test_customer_delete_restricts_when_wo_exists(self, db):
        shop_id, c, v = _setup_triple(db)
        create_work_order(shop_id, v, c, "x", db_path=db)
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            with get_connection(db) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute(
                    "DELETE FROM customers WHERE id = ?", (c,),
                )

    def test_vehicle_delete_restricts_when_wo_exists(self, db):
        shop_id, c, v = _setup_triple(db)
        create_work_order(shop_id, v, c, "x", db_path=db)
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            with get_connection(db) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute(
                    "DELETE FROM vehicles WHERE id = ?", (v,),
                )

    def test_cli_create_from_intake_autofills(self, cli_db):
        shop_id, c, v = _setup_triple(cli_db)
        intake_id = create_intake(shop_id, c, v, db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(
            root, [
                "shop", "work-order", "create",
                "--intake", str(intake_id),
                "--title", "quick oil change",
                "--priority", "3",
            ],
        )
        assert result.exit_code == 0, result.output
        rows = list_work_orders(db_path=cli_db)
        assert len(rows) == 1
        assert rows[0]["intake_visit_id"] == intake_id
        assert rows[0]["shop_id"] == shop_id
        assert rows[0]["vehicle_id"] == v
        assert rows[0]["customer_id"] == c

    def test_cli_create_intake_and_direct_args_mutex(self, cli_db):
        shop_id, c, v = _setup_triple(cli_db)
        intake_id = create_intake(shop_id, c, v, db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(
            root, [
                "shop", "work-order", "create",
                "--intake", str(intake_id),
                "--shop", "s",
                "--title", "x",
            ],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output

    def test_cli_create_without_intake_requires_all_three(self, cli_db):
        _setup_triple(cli_db)
        runner = CliRunner()
        root = _make_cli()
        # Missing --customer and --bike.
        result = runner.invoke(
            root, [
                "shop", "work-order", "create",
                "--shop", "s",
                "--title", "x",
            ],
        )
        assert result.exit_code != 0
        assert "all of --shop, --customer, --bike" in result.output


# ===========================================================================
# 4. CLI work-order subgroup
# ===========================================================================


class TestWorkOrderCLI:

    def _setup(self, cli_db):
        return _setup_triple(cli_db)

    def test_create_direct_args_happy(self, cli_db):
        shop_id, c, v = self._setup(cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(
            root, [
                "shop", "work-order", "create",
                "--shop", str(shop_id),
                "--customer", str(c),
                "--bike", str(v),
                "--title", "valve adjust",
                "--priority", "2",
                "--estimated-hours", "3.0",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Created work order" in result.output
        rows = list_work_orders(db_path=cli_db)
        assert len(rows) == 1
        assert rows[0]["priority"] == 2

    def test_list_default_excludes_terminal(self, cli_db):
        shop_id, c, v = self._setup(cli_db)
        wo1 = create_work_order(shop_id, v, c, "a", db_path=cli_db)
        wo2 = create_work_order(shop_id, v, c, "b", db_path=cli_db)
        cancel_work_order(wo1, db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        # Use --json to get a precise id set; the table output contains
        # many loose "1"/"2" substrings (mileage, phone, year) that make
        # str(id) substring checks unreliable.
        result = runner.invoke(
            root, ["shop", "work-order", "list", "--json"],
        )
        assert result.exit_code == 0, result.output
        parsed = _json.loads(result.output)
        ids = {r["id"] for r in parsed}
        assert wo2 in ids
        assert wo1 not in ids

    def test_list_status_all_includes_terminal(self, cli_db):
        shop_id, c, v = self._setup(cli_db)
        wo1 = create_work_order(shop_id, v, c, "a", db_path=cli_db)
        wo2 = create_work_order(shop_id, v, c, "b", db_path=cli_db)
        cancel_work_order(wo1, db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(
            root, ["shop", "work-order", "list", "--status", "all", "--json"],
        )
        assert result.exit_code == 0, result.output
        parsed = _json.loads(result.output)
        assert {r["id"] for r in parsed} == {wo1, wo2}

    def test_show_renders_panel(self, cli_db):
        shop_id, c, v = self._setup(cli_db)
        wo_id = create_work_order(
            shop_id, v, c, "clutch cable", db_path=cli_db,
        )
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(
            root, ["shop", "work-order", "show", str(wo_id)],
        )
        assert result.exit_code == 0, result.output
        assert f"WO id={wo_id}" in result.output
        assert "clutch cable" in result.output

    def test_show_json(self, cli_db):
        shop_id, c, v = self._setup(cli_db)
        wo_id = create_work_order(shop_id, v, c, "x", db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(
            root, ["shop", "work-order", "show", str(wo_id), "--json"],
        )
        assert result.exit_code == 0, result.output
        parsed = _json.loads(result.output)
        assert parsed["id"] == wo_id

    def test_update_set_title_and_priority(self, cli_db):
        shop_id, c, v = self._setup(cli_db)
        wo_id = create_work_order(shop_id, v, c, "old", db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(
            root, [
                "shop", "work-order", "update", str(wo_id),
                "--set", "title=new",
                "--set", "priority=1",
            ],
        )
        assert result.exit_code == 0, result.output
        row = get_work_order(wo_id, db_path=cli_db)
        assert row["title"] == "new"
        assert row["priority"] == 1

    def test_start_from_draft_autoopens_then_in_progress(self, cli_db):
        shop_id, c, v = self._setup(cli_db)
        wo_id = create_work_order(shop_id, v, c, "x", db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(
            root, ["shop", "work-order", "start", str(wo_id)],
        )
        assert result.exit_code == 0, result.output
        row = get_work_order(wo_id, db_path=cli_db)
        assert row["status"] == "in_progress"
        assert row["opened_at"] is not None
        assert row["started_at"] is not None

    def test_pause_and_resume_cycle(self, cli_db):
        shop_id, c, v = self._setup(cli_db)
        wo_id = create_work_order(shop_id, v, c, "x", db_path=cli_db)
        open_work_order(wo_id, db_path=cli_db)
        start_work(wo_id, db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(
            root, [
                "shop", "work-order", "pause", str(wo_id),
                "--reason", "parts on order",
            ],
        )
        assert result.exit_code == 0, result.output
        row = get_work_order(wo_id, db_path=cli_db)
        assert row["status"] == "on_hold"
        assert row["on_hold_reason"] == "parts on order"

        result = runner.invoke(
            root, ["shop", "work-order", "resume", str(wo_id)],
        )
        assert result.exit_code == 0, result.output
        row = get_work_order(wo_id, db_path=cli_db)
        assert row["status"] == "in_progress"

    def test_complete_with_actual_hours(self, cli_db):
        shop_id, c, v = self._setup(cli_db)
        wo_id = create_work_order(shop_id, v, c, "x", db_path=cli_db)
        open_work_order(wo_id, db_path=cli_db)
        start_work(wo_id, db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(
            root, [
                "shop", "work-order", "complete", str(wo_id),
                "--actual-hours", "2.25",
            ],
        )
        assert result.exit_code == 0, result.output
        row = get_work_order(wo_id, db_path=cli_db)
        assert row["status"] == "completed"
        assert row["actual_hours"] == 2.25

    def test_cancel_with_yes_flag(self, cli_db):
        shop_id, c, v = self._setup(cli_db)
        wo_id = create_work_order(shop_id, v, c, "x", db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(
            root, [
                "shop", "work-order", "cancel", str(wo_id),
                "--yes", "--reason", "customer-withdrew",
            ],
        )
        assert result.exit_code == 0, result.output
        row = get_work_order(wo_id, db_path=cli_db)
        assert row["status"] == "cancelled"

    def test_reopen_cancelled(self, cli_db):
        shop_id, c, v = self._setup(cli_db)
        wo_id = create_work_order(shop_id, v, c, "x", db_path=cli_db)
        cancel_work_order(wo_id, db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(
            root, [
                "shop", "work-order", "reopen", str(wo_id), "--yes",
            ],
        )
        assert result.exit_code == 0, result.output
        row = get_work_order(wo_id, db_path=cli_db)
        assert row["status"] == "open"

    def test_assign_and_unassign_cli(self, cli_db):
        shop_id, c, v = self._setup(cli_db)
        wo_id = create_work_order(shop_id, v, c, "x", db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(
            root, [
                "shop", "work-order", "assign", str(wo_id),
                "--mechanic", "1",
            ],
        )
        assert result.exit_code == 0, result.output
        row = get_work_order(wo_id, db_path=cli_db)
        assert row["assigned_mechanic_user_id"] == 1

        result = runner.invoke(
            root, ["shop", "work-order", "unassign", str(wo_id)],
        )
        assert result.exit_code == 0, result.output
        row = get_work_order(wo_id, db_path=cli_db)
        assert row["assigned_mechanic_user_id"] is None

    def test_invalid_transition_surfaces_clean_error(self, cli_db):
        shop_id, c, v = self._setup(cli_db)
        wo_id = create_work_order(shop_id, v, c, "x", db_path=cli_db)
        # draft → complete is not allowed.
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(
            root, ["shop", "work-order", "complete", str(wo_id)],
        )
        assert result.exit_code != 0
        assert "cannot transition" in result.output
