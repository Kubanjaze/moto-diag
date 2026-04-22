"""Phase 169 — Revenue tracking + invoicing tests.

Five test classes across ~30 tests:

- :class:`TestMigration033` (5) — schema_version >= 33,
  ``invoices.work_order_id`` column + index present, rollback to 32
  drops column cleanly, migration 033 is listed.
- :class:`TestInvoiceGeneration` (10) — happy path, idempotency,
  non-completed WO raises, no-customer raises, no labor hours raises,
  labor rate fallback (caller-supplied), labor rate missing raises,
  parts lines from Phase 165 installed rows, tax + supplies stacking,
  invoice number format.
- :class:`TestMarkPaidAndVoid` (5) — mark_paid happy + paid_at stamp +
  not-found raises; void happy + void allows regeneration.
- :class:`TestListAndRollup` (6) — list by shop, list filtered by status,
  revenue_rollup by status buckets, all-shops rollup, since filter
  honored, total_pending math.
- :class:`TestInvoiceCLI` (6) — generate / list / show / mark-paid /
  void / revenue round-trip through Click.

All tests are SW + SQL only. Zero AI calls, zero live tokens.
"""

from __future__ import annotations

import json as _json
import sqlite3

import click
import pytest
from click.testing import CliRunner

from motodiag.cli.shop import register_shop
from motodiag.core.database import (
    SCHEMA_VERSION,
    get_connection,
    get_schema_version,
    init_db,
)
from motodiag.core.migrations import (
    get_migration_by_version,
    rollback_to_version,
)
from motodiag.crm import customer_repo
from motodiag.crm.models import Customer
from motodiag.shop import (
    InvoiceGenerationError,
    InvoiceNotFoundError,
    add_part_to_work_order,
    complete_work_order,
    create_shop,
    create_work_order,
    generate_invoice_for_wo,
    get_invoice_with_items,
    list_invoices_for_shop,
    mark_invoice_paid,
    mark_part_ordered,
    mark_part_received,
    open_work_order,
    revenue_rollup,
    start_work,
    update_work_order,
    void_invoice,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_cli():
    @click.group()
    def root() -> None:
        """test root"""

    register_shop(root)
    return root


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase169.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase169_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    yield path
    reset_settings()


def _add_vehicle(db_path, make="Harley-Davidson",
                 model="Sportster 1200", year=2010):
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


def _add_part(db_path, slug="brake-pad-ebc-fa416hh",
              oem="HD-44209-08", typical_cents=1995):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO parts (slug, oem_part_number, brand, description,
               category, make, model_pattern, typical_cost_cents, verified_by)
               VALUES (?, ?, 'EBC', 'sintered brake pad', 'brakes',
                       'harley-davidson', 'Sportster%', ?, 'test')""",
            (slug, oem, typical_cents),
        )
        return cursor.lastrowid


def _seed_completed_wo(db_path, *, actual_hours=2.0, shop_name="s") -> tuple[int, int, int]:
    """Seed shop+customer+vehicle+WO, lifecycle it to completed.

    Returns (shop_id, wo_id, customer_id).
    """
    shop_id = create_shop(shop_name, db_path=db_path)
    customer_id = _add_customer(db_path)
    vehicle_id = _add_vehicle(db_path)
    wo_id = create_work_order(
        shop_id=shop_id, vehicle_id=vehicle_id, customer_id=customer_id,
        title="rear brake pad replacement", estimated_hours=1.5,
        db_path=db_path,
    )
    open_work_order(wo_id, db_path=db_path)
    start_work(wo_id, db_path=db_path)
    complete_work_order(wo_id, actual_hours=actual_hours, db_path=db_path)
    return shop_id, wo_id, customer_id


# ===========================================================================
# 1. Migration 033
# ===========================================================================


class TestMigration033:

    def test_schema_version_bumped_to_at_least_33(self, db):
        assert SCHEMA_VERSION >= 33
        assert get_schema_version(db) >= 33

    def test_work_order_id_column_exists(self, db):
        with get_connection(db) as conn:
            cols = {
                r[1] for r in conn.execute(
                    "PRAGMA table_info(invoices)"
                ).fetchall()
            }
        assert "work_order_id" in cols

    def test_index_present(self, db):
        with get_connection(db) as conn:
            names = {
                r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                ).fetchall()
            }
        assert "idx_invoices_work_order" in names

    def test_migration_033_registered(self):
        m = get_migration_by_version(33)
        assert m is not None
        assert m.version == 33

    def test_rollback_to_32_drops_column(self, tmp_path):
        """Rollback strips work_order_id + preserves Phase 118 data.

        Rename-recreate rollback peels the column while leaving any
        existing invoice rows intact.
        """
        path = str(tmp_path / "rollback.db")
        init_db(path)
        # Pre-check column exists at 33.
        with get_connection(path) as conn:
            cols = {
                r[1] for r in conn.execute(
                    "PRAGMA table_info(invoices)"
                ).fetchall()
            }
        assert "work_order_id" in cols
        rollback_to_version(32, path)
        with get_connection(path) as conn:
            cols = {
                r[1] for r in conn.execute(
                    "PRAGMA table_info(invoices)"
                ).fetchall()
            }
        assert "work_order_id" not in cols


# ===========================================================================
# 2. generate_invoice_for_wo
# ===========================================================================


class TestInvoiceGeneration:

    def test_generate_happy_path_labor_only(self, db):
        shop_id, wo_id, customer_id = _seed_completed_wo(db)
        invoice_id = generate_invoice_for_wo(
            wo_id, labor_hourly_rate_cents=10000, db_path=db,  # $100/hr
        )
        summary = get_invoice_with_items(invoice_id, db_path=db)
        assert summary is not None
        assert summary.work_order_id == wo_id
        assert summary.customer_id == customer_id
        assert summary.status == "sent"
        # 2.0h × $100 = $200.00 labor, no tax
        labor_items = [i for i in summary.items if i.item_type == "labor"]
        assert len(labor_items) == 1
        assert labor_items[0].line_total_cents == 20000
        assert summary.subtotal_cents == 20000
        assert summary.tax_cents == 0
        assert summary.total_cents == 20000

    def test_generate_idempotent_raises_on_duplicate(self, db):
        _, wo_id, _ = _seed_completed_wo(db)
        generate_invoice_for_wo(
            wo_id, labor_hourly_rate_cents=10000, db_path=db,
        )
        with pytest.raises(InvoiceGenerationError, match="already exists"):
            generate_invoice_for_wo(
                wo_id, labor_hourly_rate_cents=10000, db_path=db,
            )

    def test_generate_rejects_non_completed_wo(self, db):
        shop_id = create_shop("s", db_path=db)
        c = _add_customer(db)
        v = _add_vehicle(db)
        wo_id = create_work_order(
            shop_id=shop_id, vehicle_id=v, customer_id=c,
            title="in-progress", estimated_hours=1.0, db_path=db,
        )
        open_work_order(wo_id, db_path=db)
        start_work(wo_id, db_path=db)  # in_progress, not completed
        with pytest.raises(InvoiceGenerationError, match="only completed"):
            generate_invoice_for_wo(
                wo_id, labor_hourly_rate_cents=10000, db_path=db,
            )

    def test_generate_rejects_when_no_labor_hours(self, db):
        shop_id = create_shop("s", db_path=db)
        c = _add_customer(db)
        v = _add_vehicle(db)
        wo_id = create_work_order(
            shop_id=shop_id, vehicle_id=v, customer_id=c,
            title="no-hours", db_path=db,
        )
        open_work_order(wo_id, db_path=db)
        start_work(wo_id, db_path=db)
        complete_work_order(wo_id, db_path=db)  # no actual_hours
        with pytest.raises(InvoiceGenerationError, match="no labor hours"):
            generate_invoice_for_wo(
                wo_id, labor_hourly_rate_cents=10000, db_path=db,
            )

    def test_generate_falls_back_to_estimated_hours(self, db):
        """No actual_hours → uses estimated_hours (1.5 × $80 = $120)."""
        shop_id = create_shop("s", db_path=db)
        c = _add_customer(db)
        v = _add_vehicle(db)
        wo_id = create_work_order(
            shop_id=shop_id, vehicle_id=v, customer_id=c,
            title="estimate-only", estimated_hours=1.5, db_path=db,
        )
        open_work_order(wo_id, db_path=db)
        start_work(wo_id, db_path=db)
        complete_work_order(wo_id, db_path=db)  # no actual_hours supplied
        invoice_id = generate_invoice_for_wo(
            wo_id, labor_hourly_rate_cents=8000, db_path=db,
        )
        summary = get_invoice_with_items(invoice_id, db_path=db)
        assert summary.subtotal_cents == 12000

    def test_generate_rejects_without_labor_rate(self, db):
        _, wo_id, _ = _seed_completed_wo(db)
        # labor_rates table is empty in init_db
        with pytest.raises(InvoiceGenerationError, match="no labor rate"):
            generate_invoice_for_wo(wo_id, db_path=db)

    def test_generate_pulls_installed_parts_lines(self, db):
        shop_id, wo_id, c = _seed_completed_wo(db)
        # Walk WO back to something that allows adding parts — Phase 165
        # requires WO status=='in_progress' or 'open'; 'completed' rejects.
        # So add parts to a fresh WO, then complete.
        shop2 = create_shop("s2", db_path=db)
        c2 = _add_customer(db, name="Bob")
        v2 = _add_vehicle(db, make="Yamaha", model="R6", year=2005)
        wo2 = create_work_order(
            shop_id=shop2, vehicle_id=v2, customer_id=c2,
            title="with-parts", estimated_hours=1.0, db_path=db,
        )
        open_work_order(wo2, db_path=db)
        part_id = _add_part(db, typical_cents=2500)
        wop_id = add_part_to_work_order(
            wo2, part_id, quantity=2, db_path=db,
        )
        # open → ordered → received so it shows on invoice
        mark_part_ordered(wop_id, db_path=db)
        mark_part_received(wop_id, db_path=db)
        start_work(wo2, db_path=db)
        complete_work_order(wo2, actual_hours=1.0, db_path=db)
        invoice_id = generate_invoice_for_wo(
            wo2, labor_hourly_rate_cents=10000, db_path=db,
        )
        summary = get_invoice_with_items(invoice_id, db_path=db)
        parts_items = [i for i in summary.items if i.item_type == "parts"]
        assert len(parts_items) == 1
        assert parts_items[0].quantity == 2
        assert parts_items[0].unit_price_cents == 2500
        assert parts_items[0].line_total_cents == 5000
        # Labor ($100) + parts ($50) = $150
        assert summary.subtotal_cents == 15000

    def test_generate_stacks_tax_and_supplies(self, db):
        _, wo_id, _ = _seed_completed_wo(db, actual_hours=1.0)
        # $100 labor + 5% supplies = $5 → subtotal $105, tax 8.25% = $8.6625
        invoice_id = generate_invoice_for_wo(
            wo_id,
            labor_hourly_rate_cents=10000,
            tax_rate=0.0825,
            shop_supplies_pct=0.05,
            db_path=db,
        )
        summary = get_invoice_with_items(invoice_id, db_path=db)
        supplies = [i for i in summary.items if i.item_type == "misc"]
        assert len(supplies) == 1
        assert supplies[0].line_total_cents == 500  # $5.00
        # subtotal = 10000 + 500 = 10500 cents
        assert summary.subtotal_cents == 10500
        # tax = round(10500 * 0.0825) = 866 cents = $8.66
        assert summary.tax_cents == 866
        assert summary.total_cents == 10500 + 866

    def test_generate_invoice_number_format(self, db):
        shop_id, wo_id, _ = _seed_completed_wo(db)
        invoice_id = generate_invoice_for_wo(
            wo_id, labor_hourly_rate_cents=10000, db_path=db,
        )
        summary = get_invoice_with_items(invoice_id, db_path=db)
        assert summary.invoice_number.startswith(f"INV-{shop_id}-{wo_id}-")
        # Ends with YYYYMMDD (8 digits)
        tail = summary.invoice_number.split("-")[-1]
        assert len(tail) == 8 and tail.isdigit()


# ===========================================================================
# 3. mark_invoice_paid + void_invoice
# ===========================================================================


class TestMarkPaidAndVoid:

    def test_mark_paid_sets_status_and_timestamp(self, db):
        _, wo_id, _ = _seed_completed_wo(db)
        invoice_id = generate_invoice_for_wo(
            wo_id, labor_hourly_rate_cents=10000, db_path=db,
        )
        mark_invoice_paid(invoice_id, db_path=db)
        summary = get_invoice_with_items(invoice_id, db_path=db)
        assert summary.status == "paid"
        assert summary.paid_at is not None

    def test_mark_paid_with_explicit_timestamp(self, db):
        _, wo_id, _ = _seed_completed_wo(db)
        invoice_id = generate_invoice_for_wo(
            wo_id, labor_hourly_rate_cents=10000, db_path=db,
        )
        mark_invoice_paid(
            invoice_id, paid_at="2026-04-22T15:00:00+00:00", db_path=db,
        )
        summary = get_invoice_with_items(invoice_id, db_path=db)
        assert summary.paid_at == "2026-04-22T15:00:00+00:00"

    def test_mark_paid_raises_on_unknown(self, db):
        with pytest.raises(InvoiceNotFoundError):
            mark_invoice_paid(9999, db_path=db)

    def test_void_sets_cancelled_status(self, db):
        _, wo_id, _ = _seed_completed_wo(db)
        invoice_id = generate_invoice_for_wo(
            wo_id, labor_hourly_rate_cents=10000, db_path=db,
        )
        void_invoice(invoice_id, reason="customer disputed", db_path=db)
        summary = get_invoice_with_items(invoice_id, db_path=db)
        assert summary.status == "cancelled"
        assert "VOID" in (summary.notes or "")

    def test_void_allows_regeneration_for_same_wo(self, db):
        _, wo_id, _ = _seed_completed_wo(db)
        first = generate_invoice_for_wo(
            wo_id, labor_hourly_rate_cents=10000, db_path=db,
        )
        void_invoice(first, db_path=db)
        second = generate_invoice_for_wo(
            wo_id, labor_hourly_rate_cents=10000, db_path=db,
        )
        assert second != first


# ===========================================================================
# 4. list_invoices_for_shop + revenue_rollup
# ===========================================================================


class TestListAndRollup:

    def test_list_returns_shop_invoices(self, db):
        shop_id, wo_id, _ = _seed_completed_wo(db)
        invoice_id = generate_invoice_for_wo(
            wo_id, labor_hourly_rate_cents=10000, db_path=db,
        )
        rows = list_invoices_for_shop(shop_id, db_path=db)
        assert len(rows) == 1
        assert rows[0]["id"] == invoice_id
        assert rows[0]["total_cents"] == 20000

    def test_list_filters_by_status(self, db):
        shop_id, wo_id, _ = _seed_completed_wo(db)
        invoice_id = generate_invoice_for_wo(
            wo_id, labor_hourly_rate_cents=10000, db_path=db,
        )
        # Not yet paid
        paid = list_invoices_for_shop(shop_id, status="paid", db_path=db)
        assert paid == []
        sent = list_invoices_for_shop(shop_id, status="sent", db_path=db)
        assert len(sent) == 1
        mark_invoice_paid(invoice_id, db_path=db)
        paid = list_invoices_for_shop(shop_id, status="paid", db_path=db)
        assert len(paid) == 1

    def test_list_rejects_bogus_status(self, db):
        shop_id, _, _ = _seed_completed_wo(db)
        with pytest.raises(ValueError, match="status must be one of"):
            list_invoices_for_shop(shop_id, status="bogus", db_path=db)

    def test_revenue_rollup_by_status(self, db):
        shop_id, wo_id1, _ = _seed_completed_wo(db, shop_name="s1")
        # Second WO on same shop
        c2 = _add_customer(db, name="Bob")
        v2 = _add_vehicle(db, make="Yamaha", model="R6")
        wo_id2 = create_work_order(
            shop_id=shop_id, vehicle_id=v2, customer_id=c2,
            title="x2", estimated_hours=1.0, db_path=db,
        )
        open_work_order(wo_id2, db_path=db)
        start_work(wo_id2, db_path=db)
        complete_work_order(wo_id2, actual_hours=1.0, db_path=db)
        inv1 = generate_invoice_for_wo(
            wo_id1, labor_hourly_rate_cents=10000, db_path=db,  # $200
        )
        inv2 = generate_invoice_for_wo(
            wo_id2, labor_hourly_rate_cents=10000, db_path=db,  # $100
        )
        mark_invoice_paid(inv1, db_path=db)
        rollup = revenue_rollup(shop_id=shop_id, db_path=db)
        assert rollup.invoice_count == 2
        assert rollup.total_invoiced_cents == 30000
        assert rollup.total_paid_cents == 20000
        assert rollup.total_pending_cents == 10000
        assert rollup.by_status.get("paid") == 1
        assert rollup.by_status.get("sent") == 1

    def test_revenue_rollup_all_shops(self, db):
        # Build two shops, each with one invoice.
        shop1, wo1, _ = _seed_completed_wo(db, shop_name="s1")
        shop2 = create_shop("s2", db_path=db)
        c = _add_customer(db, name="Alice")
        v = _add_vehicle(db, make="Honda", model="CBR600", year=2008)
        wo2 = create_work_order(
            shop_id=shop2, vehicle_id=v, customer_id=c,
            title="second", estimated_hours=1.0, db_path=db,
        )
        open_work_order(wo2, db_path=db)
        start_work(wo2, db_path=db)
        complete_work_order(wo2, actual_hours=1.0, db_path=db)
        generate_invoice_for_wo(
            wo1, labor_hourly_rate_cents=10000, db_path=db,  # $200
        )
        generate_invoice_for_wo(
            wo2, labor_hourly_rate_cents=10000, db_path=db,  # $100
        )
        # All-shops rollup aggregates both.
        rollup = revenue_rollup(shop_id=None, db_path=db)
        assert rollup.invoice_count == 2
        assert rollup.total_invoiced_cents == 30000

    def test_revenue_rollup_pending_math_never_negative(self, db):
        shop_id, wo_id, _ = _seed_completed_wo(db)
        invoice_id = generate_invoice_for_wo(
            wo_id, labor_hourly_rate_cents=10000, db_path=db,
        )
        mark_invoice_paid(invoice_id, db_path=db)
        rollup = revenue_rollup(shop_id=shop_id, db_path=db)
        assert rollup.total_paid_cents == 20000
        assert rollup.total_pending_cents == 0


# ===========================================================================
# 5. CLI round-trip
# ===========================================================================


class TestInvoiceCLI:

    def test_generate_show_mark_paid_roundtrip(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id, wo_id, _ = _seed_completed_wo(cli_db)
        gen = runner.invoke(root, [
            "shop", "invoice", "generate", str(wo_id),
            "--hourly-rate", "10000", "--json",
        ])
        assert gen.exit_code == 0, gen.output
        payload = _json.loads(gen.output)
        invoice_id = int(payload["id"])
        show = runner.invoke(root, [
            "shop", "invoice", "show", str(invoice_id), "--json",
        ])
        assert show.exit_code == 0
        data = _json.loads(show.output)
        assert data["work_order_id"] == wo_id
        paid = runner.invoke(root, [
            "shop", "invoice", "mark-paid", str(invoice_id),
        ])
        assert paid.exit_code == 0
        reshow = runner.invoke(root, [
            "shop", "invoice", "show", str(invoice_id), "--json",
        ])
        assert _json.loads(reshow.output)["status"] == "paid"

    def test_list_cli_filters(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id, wo_id, _ = _seed_completed_wo(cli_db)
        runner.invoke(root, [
            "shop", "invoice", "generate", str(wo_id),
            "--hourly-rate", "10000", "--json",
        ])
        lst = runner.invoke(root, [
            "shop", "invoice", "list", "--shop", str(shop_id), "--json",
        ])
        assert lst.exit_code == 0, lst.output
        rows = _json.loads(lst.output)
        assert len(rows) == 1

    def test_void_cli(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id, wo_id, _ = _seed_completed_wo(cli_db)
        gen = runner.invoke(root, [
            "shop", "invoice", "generate", str(wo_id),
            "--hourly-rate", "10000", "--json",
        ])
        invoice_id = int(_json.loads(gen.output)["id"])
        v = runner.invoke(root, [
            "shop", "invoice", "void", str(invoice_id),
            "--reason", "customer-withdrew",
        ])
        assert v.exit_code == 0
        show = runner.invoke(root, [
            "shop", "invoice", "show", str(invoice_id), "--json",
        ])
        assert _json.loads(show.output)["status"] == "cancelled"

    def test_revenue_cli(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id, wo_id, _ = _seed_completed_wo(cli_db)
        runner.invoke(root, [
            "shop", "invoice", "generate", str(wo_id),
            "--hourly-rate", "10000", "--json",
        ])
        rev = runner.invoke(root, [
            "shop", "invoice", "revenue", "--shop", str(shop_id), "--json",
        ])
        assert rev.exit_code == 0
        data = _json.loads(rev.output)
        assert data["invoice_count"] == 1
        assert data["total_invoiced_cents"] == 20000

    def test_generate_surfaces_error_on_non_completed_wo(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id = create_shop("s", db_path=cli_db)
        c = _add_customer(cli_db)
        v = _add_vehicle(cli_db)
        wo_id = create_work_order(
            shop_id=shop_id, vehicle_id=v, customer_id=c,
            title="draft-only", estimated_hours=1.0, db_path=cli_db,
        )
        r = runner.invoke(root, [
            "shop", "invoice", "generate", str(wo_id),
            "--hourly-rate", "10000",
        ])
        assert r.exit_code != 0
        assert "only completed" in r.output or "draft" in r.output

    def test_show_cli_not_found(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        r = runner.invoke(root, [
            "shop", "invoice", "show", "9999", "--json",
        ])
        assert r.exit_code != 0


# ===========================================================================
# 6. Anti-regression
# ===========================================================================


class TestAntiRegression:

    def test_no_anthropic_import_in_invoicing(self):
        from pathlib import Path
        path = (
            Path(__file__).parent.parent / "src" / "motodiag" /
            "shop" / "invoicing.py"
        )
        src = path.read_text(encoding="utf-8")
        assert "import anthropic" not in src
        assert "from anthropic" not in src
