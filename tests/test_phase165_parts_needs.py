"""Phase 165 — Parts needs aggregation tests.

Five test classes across ~38 tests:

- :class:`TestMigration029` (5) — schema + 3 tables + 3 indexes + CHECK.
- :class:`TestPartsNeedsCRUD` (12) — add/remove/update/cancel + cost recompute
  routes through Phase 161 update_work_order whitelist (NEVER raw SQL).
- :class:`TestPartsLifecycle` (5) — guarded transitions + Phase 164 contract.
- :class:`TestRequisitions` (8) — build/get/list + immutability + scope validation.
- :class:`TestPartsNeedsCLI` (8) — 8 subcommand round-trips.

All tests pure stdlib + SQL. Zero AI, zero tokens.
"""

from __future__ import annotations

import json as _json
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
    InvalidPartNeedTransition, PartNotInCatalogError,
    Requisition, WorkOrderPartNotFoundError,
    add_part_to_work_order, build_requisition, cancel_part_need,
    create_intake, create_shop, create_work_order, get_requisition,
    get_work_order, list_parts_for_shop_open_wos, list_parts_for_wo,
    list_requisitions, mark_part_ordered, mark_part_received,
    open_work_order, remove_part_from_work_order,
    update_part_cost_override, update_part_quantity,
)


def _make_cli():
    @click.group()
    def root() -> None:
        """test root"""
    register_shop(root)
    return root


def _add_vehicle(db_path, make="Harley-Davidson", model="Sportster 1200", year=2010):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO vehicles (make, model, year, protocol) "
            "VALUES (?, ?, ?, 'none')",
            (make, model, year),
        )
        return cursor.lastrowid


def _add_customer(db_path, name="Jane Doe"):
    return customer_repo.create_customer(
        Customer(name=name, phone="555-0100", email="jane@example.com"),
        db_path=db_path,
    )


def _add_part(db_path, slug="brake-pad-ebc-fa416hh", oem="HD-44209-08", typical_cents=1995):
    """Insert a Phase 153 catalog part directly. Returns part_id."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO parts (slug, oem_part_number, brand, description,
               category, make, model_pattern, typical_cost_cents, verified_by)
               VALUES (?, ?, 'EBC', 'sintered brake pad', 'brakes',
                       'harley-davidson', 'Sportster%', ?, 'test')""",
            (slug, oem, typical_cents),
        )
        return cursor.lastrowid


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase165.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase165_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    yield path
    reset_settings()


def _seed_full(db_path):
    """Seed shop+customer+vehicle+WO+part. Returns (wo_id, part_id, shop_id)."""
    shop_id = create_shop("s", db_path=db_path)
    c = _add_customer(db_path)
    v = _add_vehicle(db_path)
    wo_id = create_work_order(shop_id, v, c, "x", db_path=db_path)
    open_work_order(wo_id, db_path=db_path)
    part_id = _add_part(db_path)
    return wo_id, part_id, shop_id


# ===========================================================================
# 1. Migration 029
# ===========================================================================


class TestMigration029:
    def test_schema_version_bumped_to_at_least_29(self, db):
        assert SCHEMA_VERSION >= 29
        assert get_schema_version(db) >= 29

    def test_three_tables_created(self, db):
        assert table_exists("work_order_parts", db)
        assert table_exists("parts_requisitions", db)
        assert table_exists("parts_requisition_items", db)

    def test_indexes_present(self, db):
        expected = {"idx_wop_wo_status", "idx_wop_part",
                    "idx_parts_req_shop_date"}
        with get_connection(db) as conn:
            actual = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()}
        assert expected.issubset(actual)

    def test_quantity_check_rejects_zero(self, db):
        wo_id, part_id, _ = _seed_full(db)
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            with get_connection(db) as conn:
                conn.execute(
                    "INSERT INTO work_order_parts "
                    "(work_order_id, part_id, quantity) VALUES (?, ?, 0)",
                    (wo_id, part_id),
                )

    def test_rollback_to_28_drops_tables(self, tmp_path):
        path = str(tmp_path / "rollback.db")
        init_db(path)
        assert table_exists("work_order_parts", path)
        rollback_to_version(28, path)
        assert not table_exists("work_order_parts", path)
        assert not table_exists("parts_requisitions", path)
        assert not table_exists("parts_requisition_items", path)
        # Phase 160-164 substrate preserved
        assert table_exists("shops", path)
        assert table_exists("work_orders", path)


# ===========================================================================
# 2. CRUD + cost recompute
# ===========================================================================


class TestPartsNeedsCRUD:
    def test_add_part_creates_row(self, db):
        wo_id, part_id, _ = _seed_full(db)
        wop_id = add_part_to_work_order(
            wo_id, part_id, quantity=2, db_path=db,
        )
        assert wop_id > 0
        rows = list_parts_for_wo(wo_id, db_path=db)
        assert len(rows) == 1
        assert rows[0]["quantity"] == 2

    def test_add_part_recomputes_wo_cost(self, db):
        wo_id, part_id, _ = _seed_full(db)  # part typical_cost_cents=1995
        add_part_to_work_order(wo_id, part_id, quantity=2, db_path=db)
        row = get_work_order(wo_id, db_path=db)
        # 2 * 1995 = 3990
        assert row["estimated_parts_cost_cents"] == 3990

    def test_add_part_with_override_uses_override_cost(self, db):
        wo_id, part_id, _ = _seed_full(db)
        add_part_to_work_order(
            wo_id, part_id, quantity=1, unit_cost_override=5000, db_path=db,
        )
        row = get_work_order(wo_id, db_path=db)
        assert row["estimated_parts_cost_cents"] == 5000

    def test_add_part_unknown_part_raises(self, db):
        wo_id, _, _ = _seed_full(db)
        with pytest.raises(PartNotInCatalogError):
            add_part_to_work_order(wo_id, 999, db_path=db)

    def test_add_part_zero_qty_raises(self, db):
        wo_id, part_id, _ = _seed_full(db)
        with pytest.raises(ValueError):
            add_part_to_work_order(wo_id, part_id, quantity=0, db_path=db)

    def test_add_part_negative_override_raises(self, db):
        wo_id, part_id, _ = _seed_full(db)
        with pytest.raises(ValueError):
            add_part_to_work_order(
                wo_id, part_id, unit_cost_override=-1, db_path=db,
            )

    def test_remove_part_decrements_cost(self, db):
        wo_id, part_id, _ = _seed_full(db)
        wop_id = add_part_to_work_order(
            wo_id, part_id, quantity=2, db_path=db,
        )
        remove_part_from_work_order(wop_id, db_path=db)
        row = get_work_order(wo_id, db_path=db)
        assert row["estimated_parts_cost_cents"] == 0

    def test_update_part_quantity_recomputes_cost(self, db):
        wo_id, part_id, _ = _seed_full(db)
        wop_id = add_part_to_work_order(wo_id, part_id, quantity=1, db_path=db)
        update_part_quantity(wop_id, 5, db_path=db)
        row = get_work_order(wo_id, db_path=db)
        assert row["estimated_parts_cost_cents"] == 5 * 1995

    def test_update_cost_override_to_none_reverts_to_catalog(self, db):
        wo_id, part_id, _ = _seed_full(db)
        wop_id = add_part_to_work_order(
            wo_id, part_id, quantity=1, unit_cost_override=10000, db_path=db,
        )
        # Now clear the override
        update_part_cost_override(wop_id, None, db_path=db)
        row = get_work_order(wo_id, db_path=db)
        assert row["estimated_parts_cost_cents"] == 1995

    def test_cancel_part_drops_from_sum(self, db):
        wo_id, part_id, _ = _seed_full(db)
        wop_id = add_part_to_work_order(wo_id, part_id, quantity=2, db_path=db)
        cancel_part_need(wop_id, reason="customer-changed-mind", db_path=db)
        row = get_work_order(wo_id, db_path=db)
        assert row["estimated_parts_cost_cents"] == 0

    def test_recompute_routes_through_update_work_order(self, db):
        """Critical: cost recompute must call update_work_order, NOT raw SQL.

        Patch update_work_order at the parts_needs import site; verify
        it's called when add_part runs.
        """
        wo_id, part_id, _ = _seed_full(db)
        with patch(
            "motodiag.shop.parts_needs.update_work_order",
        ) as mock_upd:
            add_part_to_work_order(
                wo_id, part_id, quantity=2, db_path=db,
            )
        # Should have been called once with estimated_parts_cost_cents in updates
        assert mock_upd.called
        call_kwargs = mock_upd.call_args.kwargs
        call_args = mock_upd.call_args.args
        if call_kwargs:
            updates = call_kwargs.get("updates") or (
                call_args[1] if len(call_args) > 1 else {}
            )
        else:
            # Positional call
            updates = call_args[1] if len(call_args) > 1 else {}
        assert "estimated_parts_cost_cents" in updates

    def test_remove_unknown_wop_id_raises(self, db):
        with pytest.raises(WorkOrderPartNotFoundError):
            remove_part_from_work_order(999, db_path=db)


# ===========================================================================
# 3. Lifecycle transitions
# ===========================================================================


class TestPartsLifecycle:
    def test_open_to_ordered(self, db):
        wo_id, part_id, _ = _seed_full(db)
        wop_id = add_part_to_work_order(wo_id, part_id, db_path=db)
        mark_part_ordered(wop_id, db_path=db)
        rows = list_parts_for_wo(wo_id, db_path=db)
        assert rows[0]["status"] == "ordered"
        assert rows[0]["ordered_at"] is not None

    def test_ordered_to_received(self, db):
        wo_id, part_id, _ = _seed_full(db)
        wop_id = add_part_to_work_order(wo_id, part_id, db_path=db)
        mark_part_ordered(wop_id, db_path=db)
        mark_part_received(wop_id, db_path=db)
        rows = list_parts_for_wo(wo_id, db_path=db)
        assert rows[0]["status"] == "received"
        assert rows[0]["received_at"] is not None

    def test_open_to_received_invalid(self, db):
        wo_id, part_id, _ = _seed_full(db)
        wop_id = add_part_to_work_order(wo_id, part_id, db_path=db)
        with pytest.raises(InvalidPartNeedTransition):
            mark_part_received(wop_id, db_path=db)

    def test_cancel_terminal_status_raises(self, db):
        wo_id, part_id, _ = _seed_full(db)
        wop_id = add_part_to_work_order(wo_id, part_id, db_path=db)
        cancel_part_need(wop_id, db_path=db)
        with pytest.raises(InvalidPartNeedTransition):
            cancel_part_need(wop_id, db_path=db)

    def test_phase164_soft_guard_contract(self, db):
        """Phase 164's _parts_available_for calls list_parts_for_wo."""
        from motodiag.shop.triage_queue import _parts_available_for
        wo_id, part_id, _ = _seed_full(db)
        # No parts → ready
        ready, missing = _parts_available_for(
            wo_id, assumed_available=True, db_path=db,
        )
        assert ready is True
        # Add an open part → not ready
        add_part_to_work_order(wo_id, part_id, db_path=db)
        ready, missing = _parts_available_for(
            wo_id, assumed_available=True, db_path=db,
        )
        assert ready is False
        assert len(missing) == 1


# ===========================================================================
# 4. Requisitions
# ===========================================================================


class TestRequisitions:
    def test_build_empty_returns_id_with_zero_counts(self, db):
        shop_id = create_shop("s", db_path=db)
        req_id = build_requisition(shop_id, db_path=db)
        req = get_requisition(req_id, db_path=db)
        assert req is not None
        assert req.total_distinct_parts == 0
        assert req.items == []

    def test_build_aggregates_across_wos(self, db):
        shop_id = create_shop("s", db_path=db)
        c = _add_customer(db)
        v = _add_vehicle(db)
        wo1 = create_work_order(shop_id, v, c, "a", db_path=db)
        wo2 = create_work_order(shop_id, v, c, "b", db_path=db)
        open_work_order(wo1, db_path=db)
        open_work_order(wo2, db_path=db)
        part_id = _add_part(db)
        add_part_to_work_order(wo1, part_id, quantity=2, db_path=db)
        add_part_to_work_order(wo2, part_id, quantity=3, db_path=db)
        req_id = build_requisition(shop_id, db_path=db)
        req = get_requisition(req_id, db_path=db)
        assert req.total_distinct_parts == 1
        assert req.total_quantity == 5
        assert sorted(req.items[0].wo_ids) == sorted([wo1, wo2])

    def test_build_with_wo_ids_validates_shop(self, db):
        shop_a = create_shop("a", db_path=db)
        shop_b = create_shop("b", db_path=db)
        c = _add_customer(db)
        v = _add_vehicle(db)
        wo_a = create_work_order(shop_a, v, c, "a", db_path=db)
        # Try to scope shop_b's requisition to shop_a's WO
        with pytest.raises(ValueError, match="shop_id"):
            build_requisition(shop_b, wo_ids=[wo_a], db_path=db)

    def test_build_with_unknown_wo_ids_raises(self, db):
        shop_id = create_shop("s", db_path=db)
        with pytest.raises(ValueError, match="not found"):
            build_requisition(shop_id, wo_ids=[9999], db_path=db)

    def test_immutable_after_build(self, db):
        wo_id, part_id, shop_id = _seed_full(db)
        add_part_to_work_order(wo_id, part_id, quantity=2, db_path=db)
        req_id = build_requisition(shop_id, db_path=db)
        # Now edit work_order_parts
        wop_rows = list_parts_for_wo(wo_id, db_path=db)
        update_part_quantity(wop_rows[0]["id"], 100, db_path=db)
        # Snapshot unchanged
        req = get_requisition(req_id, db_path=db)
        assert req.items[0].total_quantity == 2

    def test_get_requisition_unknown_returns_none(self, db):
        assert get_requisition(999, db_path=db) is None

    def test_list_requisitions_filters_by_shop(self, db):
        s1 = create_shop("s1", db_path=db)
        s2 = create_shop("s2", db_path=db)
        build_requisition(s1, db_path=db)
        build_requisition(s2, db_path=db)
        rows = list_requisitions(shop_id=s1, db_path=db)
        assert len(rows) == 1
        assert rows[0]["shop_id"] == s1

    def test_consolidated_excludes_terminal_part_status(self, db):
        wo_id, part_id, shop_id = _seed_full(db)
        wop_id = add_part_to_work_order(wo_id, part_id, db_path=db)
        cancel_part_need(wop_id, db_path=db)
        # Cancelled line excluded from aggregation
        consolidated = list_parts_for_shop_open_wos(shop_id, db_path=db)
        assert consolidated == []


# ===========================================================================
# 5. CLI
# ===========================================================================


class TestPartsNeedsCLI:
    def test_help_lists_subcommands(self, cli_db):
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, ["shop", "parts-needs", "--help"])
        assert result.exit_code == 0
        for sub in ("add", "list", "consolidate", "mark-ordered",
                    "mark-received", "requisition"):
            assert sub in result.output

    def test_requisition_help_lists_3(self, cli_db):
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(
            root, ["shop", "parts-needs", "requisition", "--help"],
        )
        assert result.exit_code == 0
        for sub in ("create", "list", "show"):
            assert sub in result.output

    def test_add_cli(self, cli_db):
        wo_id, part_id, _ = _seed_full(cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "parts-needs", "add", str(wo_id),
            "--part-id", str(part_id),
            "--qty", "3",
        ])
        assert result.exit_code == 0, result.output

    def test_list_wo_json(self, cli_db):
        wo_id, part_id, _ = _seed_full(cli_db)
        add_part_to_work_order(wo_id, part_id, quantity=2, db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "parts-needs", "list", "--wo", str(wo_id), "--json",
        ])
        assert result.exit_code == 0
        parsed = _json.loads(result.output)
        assert len(parsed) == 1

    def test_list_mutex_error(self, cli_db):
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "parts-needs", "list",
            "--wo", "1", "--shop", "1",
        ])
        assert result.exit_code != 0
        assert "exactly one" in result.output.lower()

    def test_consolidate_cli(self, cli_db):
        wo_id, part_id, shop_id = _seed_full(cli_db)
        add_part_to_work_order(wo_id, part_id, quantity=2, db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "parts-needs", "consolidate",
            "--shop", str(shop_id), "--json",
        ])
        assert result.exit_code == 0
        parsed = _json.loads(result.output)
        assert len(parsed) == 1
        assert parsed[0]["total_quantity"] == 2

    def test_requisition_create_cli(self, cli_db):
        wo_id, part_id, shop_id = _seed_full(cli_db)
        add_part_to_work_order(wo_id, part_id, quantity=2, db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "parts-needs", "requisition", "create",
            "--shop", str(shop_id), "--json",
        ])
        assert result.exit_code == 0, result.output
        parsed = _json.loads(result.output)
        assert parsed["total_distinct_parts"] == 1

    def test_requisition_show_unknown(self, cli_db):
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "parts-needs", "requisition", "show", "999",
        ])
        assert result.exit_code != 0
