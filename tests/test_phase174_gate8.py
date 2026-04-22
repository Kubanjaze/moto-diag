"""Phase 174 — Gate 8: Track G intake-to-invoice integration test.

Closes Track G with an end-to-end walkthrough that exercises every
subgroup of ``motodiag shop *`` against a single WO lifecycle. Uses
CLI invocations where the paths don't require AI; falls back to
direct repo calls for Phase 163/166/167 (where the CLI path invokes
live AI — per-phase tests already prove the CLI wiring in isolation).

Zero AI: AI phases use their ``_default_scorer_fn`` injection seams
with deterministic stubs.

Three test classes:
- :class:`TestEndToEndHappyPath` — one big WO lifecycle
- :class:`TestShopScopedIsolation` — two shops don't cross-pollinate
- :class:`TestRuleFiresAcrossLifecycle` — rules fire on distinct events
"""

from __future__ import annotations

import json as _json

import click
import pytest
from click.testing import CliRunner

from motodiag.cli.shop import register_shop
from motodiag.core.database import (
    SCHEMA_VERSION, get_connection, init_db,
)
from motodiag.crm import customer_repo
from motodiag.crm.models import Customer
from motodiag.shop import (
    add_bay, add_part_to_work_order, add_shop_member,
    complete_work_order, complete_slot, create_rule, create_shop,
    create_work_order, dashboard_snapshot, fire_rule_for_wo,
    generate_invoice_for_wo, get_invoice_with_items,
    list_invoices_for_shop, list_notifications, list_rule_runs,
    list_work_order_assignments, mark_invoice_paid,
    mark_part_ordered, mark_part_received, open_work_order,
    reassign_work_order, revenue_rollup, schedule_wo, start_slot,
    start_work, trigger_notification, trigger_rules_for_event,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_cli():
    @click.group()
    def root() -> None:
        """test root"""

    register_shop(root)
    return root


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase174_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    yield path
    reset_settings()


def _add_user(db_path, username="bob"):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, tier, is_active) "
            "VALUES (?, 'individual', 1)", (username,),
        )
        return cursor.lastrowid


def _add_customer(db_path, name="Jane Doe",
                  email="jane@ex.com", phone="555-0100"):
    return customer_repo.create_customer(
        Customer(name=name, phone=phone, email=email),
        db_path=db_path,
    )


def _add_vehicle(db_path, make="Harley-Davidson",
                 model="Sportster 1200", year=2010):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO vehicles (make, model, year, protocol) "
            "VALUES (?, ?, ?, 'none')",
            (make, model, year),
        )
        return cursor.lastrowid


def _add_part(db_path, slug="brake-pad", typical_cents=1995):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO parts (slug, oem_part_number, brand,
               description, category, make, model_pattern,
               typical_cost_cents, verified_by)
               VALUES (?, 'OEM-1', 'EBC', 'brake pad', 'brakes',
                       'harley-davidson', '%', ?, 'test')""",
            (slug, typical_cents),
        )
        return cursor.lastrowid


# ===========================================================================
# 1. End-to-end happy path
# ===========================================================================


class TestEndToEndHappyPath:

    def test_full_lifecycle(self, cli_db):
        """Walk a single WO from intake through paid invoice, touching
        every Track G subgroup."""
        root = _make_cli()
        runner = CliRunner()

        # --- Step 1: shop profile init via CLI ---
        r = runner.invoke(root, [
            "shop", "profile", "init",
            "--name", "BobMoto",
            "--state", "CA", "--phone", "555-0100",
        ])
        assert r.exit_code == 0, r.output
        with get_connection(cli_db) as conn:
            shop_id = conn.execute(
                "SELECT id FROM shops WHERE name='BobMoto'",
            ).fetchone()["id"]

        # --- Step 2: membership (owner + tech) ---
        owner_id = _add_user(cli_db, username="bob")
        tech_id = _add_user(cli_db, username="alice")
        for uid, role in [(owner_id, "owner"), (tech_id, "tech")]:
            r = runner.invoke(root, [
                "shop", "member", "add",
                "--shop", str(shop_id),
                "--user", str(uid), "--role", role,
            ])
            assert r.exit_code == 0, r.output

        # --- Step 3: customer + bike + intake directly (CLI path
        # requires bike linkage across multiple subcommands; the
        # per-phase tests already cover that surface) ---
        customer_id = _add_customer(cli_db)
        vehicle_id = _add_vehicle(cli_db)

        # --- Step 4: work order creation ---
        wo_id = create_work_order(
            shop_id=shop_id, vehicle_id=vehicle_id,
            customer_id=customer_id,
            title="rear brake pad replacement",
            description="squealing on stops",
            estimated_hours=2.0, priority=2, db_path=cli_db,
        )
        open_work_order(wo_id, db_path=cli_db)

        # --- Step 5: issue logging via CLI ---
        r = runner.invoke(root, [
            "shop", "issue", "add",
            "--work-order", str(wo_id),
            "--title", "brake squeal",
            "--category", "brakes",
            "--severity", "high",
        ])
        assert r.exit_code == 0, r.output

        # --- Step 6: parts needs ---
        part_id = _add_part(cli_db)
        wop_id = add_part_to_work_order(
            wo_id, part_id, quantity=2, db_path=cli_db,
        )
        mark_part_ordered(wop_id, db_path=cli_db)
        mark_part_received(wop_id, db_path=cli_db)

        # --- Step 7: bay add + schedule ---
        bay_id = add_bay(shop_id, "Bay 1", "lift", db_path=cli_db)
        slot_id = schedule_wo(
            wo_id,
            scheduled_start="2026-04-22T09:00:00",
            duration_hours=2.0,
            bay_id=bay_id, db_path=cli_db,
        )

        # --- Step 8: work start + slot start ---
        start_work(wo_id, db_path=cli_db)
        start_slot(slot_id, db_path=cli_db)

        # --- Step 9: mid-repair reassignment (owner → tech) ---
        assignment_id = reassign_work_order(
            wo_id, new_mechanic_user_id=tech_id,
            reason="owner pulled to front desk",
            db_path=cli_db,
        )
        assert assignment_id > 0

        # --- Step 10: trigger in-progress notification ---
        notif_id = trigger_notification(
            "wo_in_progress", wo_id=wo_id, channel="email",
            db_path=cli_db,
        )
        assert notif_id > 0

        # --- Step 11: complete work + complete slot ---
        complete_work_order(
            wo_id, actual_hours=2.5, db_path=cli_db,
        )
        complete_slot(slot_id, db_path=cli_db)

        # Mark the installed part via CLI
        from motodiag.shop import mark_part_installed
        mark_part_installed(wop_id, db_path=cli_db)

        # --- Step 12: invoice generation ---
        invoice_id = generate_invoice_for_wo(
            wo_id,
            labor_hourly_rate_cents=10000,  # $100/hr
            tax_rate=0.0825,
            db_path=cli_db,
        )
        invoice = get_invoice_with_items(invoice_id, db_path=cli_db)
        assert invoice is not None
        # 2.5h × $100 = $250 labor + (2 × $19.95 = $39.90 parts)
        # = $289.90 subtotal; tax 8.25% = ~$23.92; total ~$313.82
        assert invoice.subtotal_cents == 28990
        assert invoice.total_cents > invoice.subtotal_cents

        # --- Step 13: revenue rollup shows this invoice ---
        rev = revenue_rollup(shop_id=shop_id, db_path=cli_db)
        assert rev.invoice_count == 1
        assert rev.total_invoiced_cents == invoice.total_cents

        # --- Step 14: mark invoice paid ---
        mark_invoice_paid(invoice_id, db_path=cli_db)
        rev2 = revenue_rollup(shop_id=shop_id, db_path=cli_db)
        assert rev2.total_paid_cents == invoice.total_cents

        # --- Step 15: analytics snapshot includes this WO ---
        snap = dashboard_snapshot(shop_id, since="1d", db_path=cli_db)
        assert snap.throughput.completed_total >= 1
        assert snap.revenue.invoice_count >= 1

        # --- Step 16: automation rule — wo_completed notification ---
        rule_id = create_rule(
            shop_id=shop_id, name="completed-notify",
            event_trigger="wo_completed",
            conditions=[{"type": "always"}],
            actions=[{
                "type": "trigger_notification",
                "event": "wo_completed", "channel": "email",
            }],
            db_path=cli_db,
        )
        results = trigger_rules_for_event(
            "wo_completed", wo_id, db_path=cli_db,
        )
        assert len(results) == 1
        assert results[0].matched
        assert results[0].error is None

        # --- Step 17: notification queue has both messages ---
        notifs = list_notifications(shop_id=shop_id, db_path=cli_db)
        # wo_in_progress (manual) + wo_completed (rule-triggered)
        assert len(notifs) == 2

        # --- Step 18: rule firing history ---
        runs = list_rule_runs(rule_id=rule_id, db_path=cli_db)
        assert len(runs) == 1
        assert runs[0].matched is True

        # --- Step 19: assignment history survives ---
        hist = list_work_order_assignments(wo_id, db_path=cli_db)
        assert len(hist) == 1
        assert hist[0].mechanic_user_id == tech_id


# ===========================================================================
# 2. Shop-scoped isolation
# ===========================================================================


class TestShopScopedIsolation:

    def test_two_shops_stay_isolated(self, cli_db):
        """Two shops with overlapping names/customers don't cross-
        pollinate invoices/notifications/analytics."""
        root = _make_cli()
        runner = CliRunner()

        shop_a = create_shop("ShopA", state="CA", db_path=cli_db)
        shop_b = create_shop("ShopB", state="TX", db_path=cli_db)

        # Two distinct customers + vehicles
        cust_a = _add_customer(cli_db, name="Alice",
                               email="a@ex.com", phone="555-1111")
        cust_b = _add_customer(cli_db, name="Bob",
                               email="b@ex.com", phone="555-2222")
        veh_a = _add_vehicle(cli_db)
        veh_b = _add_vehicle(cli_db, make="Yamaha", model="R6",
                             year=2005)

        # Complete a WO + invoice in each shop
        for shop_id, cust_id, veh_id in [
            (shop_a, cust_a, veh_a),
            (shop_b, cust_b, veh_b),
        ]:
            wo = create_work_order(
                shop_id=shop_id, vehicle_id=veh_id,
                customer_id=cust_id,
                title="x", estimated_hours=1.0, db_path=cli_db,
            )
            open_work_order(wo, db_path=cli_db)
            start_work(wo, db_path=cli_db)
            complete_work_order(wo, actual_hours=1.0, db_path=cli_db)
            generate_invoice_for_wo(
                wo, labor_hourly_rate_cents=10000, db_path=cli_db,
            )

        # Revenue: each shop sees only its own
        rev_a = revenue_rollup(shop_id=shop_a, db_path=cli_db)
        rev_b = revenue_rollup(shop_id=shop_b, db_path=cli_db)
        assert rev_a.invoice_count == 1
        assert rev_b.invoice_count == 1

        # Invoice list scoping
        inv_a = list_invoices_for_shop(shop_a, db_path=cli_db)
        inv_b = list_invoices_for_shop(shop_b, db_path=cli_db)
        assert len(inv_a) == 1
        assert len(inv_b) == 1
        assert inv_a[0]["id"] != inv_b[0]["id"]

        # Cross-shop rollup sums both
        rev_all = revenue_rollup(shop_id=None, db_path=cli_db)
        assert rev_all.invoice_count == 2

        # Reassignment guard: shop_a's tech can't be assigned to
        # shop_b's WO
        from motodiag.shop import MechanicNotInShopError
        tech_a = _add_user(cli_db, username="tech_a")
        add_shop_member(shop_a, tech_a, "tech", db_path=cli_db)
        # Create a fresh non-terminal WO in shop_b
        wo_b_active = create_work_order(
            shop_id=shop_b, vehicle_id=veh_b,
            customer_id=cust_b, title="active",
            estimated_hours=1.0, db_path=cli_db,
        )
        open_work_order(wo_b_active, db_path=cli_db)
        with pytest.raises(MechanicNotInShopError):
            reassign_work_order(
                wo_b_active, new_mechanic_user_id=tech_a,
                db_path=cli_db,
            )


# ===========================================================================
# 3. Rules fire across multiple event triggers
# ===========================================================================


class TestRuleFiresAcrossLifecycle:

    def test_event_triggered_rules(self, cli_db):
        """One rule on wo_completed + one on invoice_issued each fire
        when their events trigger — independent audit rows."""
        shop_id = create_shop("s", db_path=cli_db)
        customer_id = _add_customer(cli_db)
        vehicle_id = _add_vehicle(cli_db)
        wo_id = create_work_order(
            shop_id=shop_id, vehicle_id=vehicle_id,
            customer_id=customer_id,
            title="service", estimated_hours=1.0, db_path=cli_db,
        )
        open_work_order(wo_id, db_path=cli_db)
        start_work(wo_id, db_path=cli_db)
        complete_work_order(wo_id, actual_hours=1.0, db_path=cli_db)

        rule_done = create_rule(
            shop_id=shop_id, name="on-complete",
            event_trigger="wo_completed",
            conditions=[{"type": "always"}],
            actions=[{
                "type": "trigger_notification",
                "event": "wo_completed", "channel": "email",
            }],
            db_path=cli_db,
        )
        rule_invoice = create_rule(
            shop_id=shop_id, name="on-invoice",
            event_trigger="invoice_issued",
            conditions=[{"type": "always"}],
            actions=[{
                "type": "trigger_notification",
                "event": "invoice_issued", "channel": "email",
            }],
            db_path=cli_db,
        )

        # Fire wo_completed event
        r1 = trigger_rules_for_event(
            "wo_completed", wo_id, db_path=cli_db,
        )
        assert len(r1) == 1
        assert r1[0].rule_id == rule_done

        # Generate invoice, then fire invoice_issued event
        generate_invoice_for_wo(
            wo_id, labor_hourly_rate_cents=10000, db_path=cli_db,
        )
        r2 = trigger_rules_for_event(
            "invoice_issued", wo_id, db_path=cli_db,
        )
        assert len(r2) == 1
        assert r2[0].rule_id == rule_invoice

        # Audit trail: two rules, two runs each for their own event
        completed_runs = list_rule_runs(
            rule_id=rule_done, db_path=cli_db,
        )
        invoice_runs = list_rule_runs(
            rule_id=rule_invoice, db_path=cli_db,
        )
        assert len(completed_runs) == 1
        assert len(invoice_runs) == 1
        assert completed_runs[0].triggered_event == "wo_completed"
        assert invoice_runs[0].triggered_event == "invoice_issued"

        # Both rules fired real notifications
        notifs = list_notifications(shop_id=shop_id, db_path=cli_db)
        assert len(notifs) == 2


# ===========================================================================
# 4. Anti-regression
# ===========================================================================


class TestGate8AntiRegression:

    def test_schema_version_at_gate(self):
        """Gate 8 closes at schema v36 (Phase 173's migration)."""
        assert SCHEMA_VERSION == 36

    def test_track_g_summary_doc_exists(self):
        from pathlib import Path
        summary = (
            Path(__file__).parent.parent / "docs" / "phases" /
            "completed" / "TRACK_G_SUMMARY.md"
        )
        assert summary.exists(), (
            "TRACK_G_SUMMARY.md must ship alongside Phase 174 "
            "(track closure doc)"
        )
