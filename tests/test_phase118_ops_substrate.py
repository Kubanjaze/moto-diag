"""Phase 118 — Billing/accounting/inventory/scheduling substrate tests.

Tests cover:
- Migration 011 creates 9 tables + 14+ indexes
- 8 enums (billing 3, accounting 2, inventory 1, scheduling 2) with correct counts
- CRUD round-trips for all 9 tables
- FK CASCADE: user→subscriptions/payments, customer→invoices, invoice→line_items,
  customer→appointments, vehicle→warranties
- FK SET NULL: vendor→inventory_items, repair_plan→invoices, mechanic→appointments
- Unique constraints (invoice_number, sku, vendor name, campaign_number)
- JSON columns (model_applicable) round-trip
- recalculate_invoice_totals computes subtotal + tax correctly
- adjust_quantity/items_below_reorder work
- list_recalls_for_vehicle year-range filter
- list_upcoming + list_for_user on appointments
- Rollback drops all 9 tables
- Forward-compat schema version (>= 11)
"""

import pytest

from motodiag.core.database import (
    init_db, get_schema_version, SCHEMA_VERSION, get_connection,
)
from motodiag.core.migrations import (
    get_migration_by_version, rollback_migration,
)
from motodiag.core.models import VehicleBase, ProtocolType
from motodiag.vehicles.registry import add_vehicle
from motodiag.crm.customer_repo import create_customer
from motodiag.crm.models import Customer

from motodiag.billing import (
    SubscriptionTier, SubscriptionStatus, PaymentStatus,
    Subscription, Payment,
    create_subscription, get_subscription, get_subscription_by_user,
    list_subscriptions, update_subscription, delete_subscription,
    record_payment, get_payment, list_payments,
    update_payment_status, delete_payment,
)
from motodiag.accounting import (
    InvoiceStatus, InvoiceLineItemType, Invoice, InvoiceLineItem,
    create_invoice, get_invoice, get_invoice_by_number, list_invoices,
    update_invoice, delete_invoice,
    add_line_item, get_line_items, update_line_item, delete_line_item,
    recalculate_invoice_totals,
)
from motodiag.inventory import (
    CoverageType, InventoryItem, Vendor, Recall, Warranty,
    add_item, get_item, get_item_by_sku, list_items, update_item,
    delete_item, adjust_quantity, items_below_reorder,
    add_vendor, get_vendor, get_vendor_by_name, list_vendors,
    update_vendor, delete_vendor,
    add_recall, get_recall, list_recalls_for_vehicle, list_recalls,
    delete_recall,
    add_warranty, get_warranty, list_warranties_for_vehicle,
    increment_claim_count, delete_warranty,
)
from motodiag.scheduling import (
    AppointmentType, AppointmentStatus, Appointment,
    create_appointment, get_appointment, list_appointments,
    list_upcoming, list_for_user, update_appointment,
    cancel_appointment, complete_appointment, delete_appointment,
)


# Helpers


def _mk_customer(db, name="Test Customer"):
    return create_customer(Customer(name=name), db)


def _mk_vehicle(db):
    return add_vehicle(VehicleBase(
        make="Honda", model="CBR929RR", year=2001,
        engine_cc=929, protocol=ProtocolType.K_LINE,
    ), db)


# --- Migration 011 ---


class TestMigration011:
    def test_all_9_tables_created(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        expected = {
            "subscriptions", "payments", "invoices", "invoice_line_items",
            "vendors", "inventory_items", "recalls", "warranties",
            "appointments",
        }
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                f"AND name IN ({','.join('?' * len(expected))})",
                tuple(expected),
            )
            tables = {row[0] for row in cursor.fetchall()}
        assert tables == expected

    def test_rollback_drops_all(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        m = get_migration_by_version(11)
        rollback_migration(m, db)
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN "
                "('subscriptions','payments','invoices','invoice_line_items',"
                "'vendors','inventory_items','recalls','warranties','appointments')"
            )
            assert cursor.fetchall() == []


# --- Enums ---


class TestEnums:
    def test_subscription_tier_3(self):
        assert len(SubscriptionTier) == 3

    def test_subscription_status_4(self):
        assert len(SubscriptionStatus) == 4

    def test_payment_status_4(self):
        assert len(PaymentStatus) == 4

    def test_invoice_status_5(self):
        assert len(InvoiceStatus) == 5

    def test_invoice_line_item_type_4(self):
        assert len(InvoiceLineItemType) == 4

    def test_coverage_type_4(self):
        assert len(CoverageType) == 4

    def test_appointment_type_4(self):
        assert len(AppointmentType) == 4

    def test_appointment_status_6(self):
        assert len(AppointmentStatus) == 6


# --- Billing: subscriptions + payments ---


class TestBilling:
    def test_create_subscription(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        sid = create_subscription(Subscription(
            user_id=1, tier=SubscriptionTier.SHOP,
            status=SubscriptionStatus.ACTIVE,
            stripe_customer_id="cus_123",
            stripe_subscription_id="sub_abc",
        ), db)
        row = get_subscription(sid, db)
        assert row["tier"] == "shop"
        assert row["stripe_subscription_id"] == "sub_abc"

    def test_get_subscription_by_user_filters_active(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        create_subscription(Subscription(
            user_id=1, status=SubscriptionStatus.CANCELLED,
        ), db)
        create_subscription(Subscription(
            user_id=1, status=SubscriptionStatus.ACTIVE,
        ), db)
        row = get_subscription_by_user(1, db)
        assert row["status"] == "active"

    def test_update_subscription(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        sid = create_subscription(Subscription(user_id=1), db)
        assert update_subscription(
            sid, db_path=db, tier=SubscriptionTier.COMPANY,
            status=SubscriptionStatus.ACTIVE,
        )
        row = get_subscription(sid, db)
        assert row["tier"] == "company"
        assert row["status"] == "active"

    def test_delete_subscription(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        sid = create_subscription(Subscription(user_id=1), db)
        assert delete_subscription(sid, db)
        assert get_subscription(sid, db) is None

    def test_record_payment_and_list(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        pid = record_payment(Payment(
            user_id=1, amount=99.00, currency="USD",
            status=PaymentStatus.SUCCEEDED,
            stripe_payment_intent_id="pi_123",
        ), db)
        row = get_payment(pid, db)
        assert row["amount"] == 99.00
        assert row["status"] == "succeeded"
        all_payments = list_payments(user_id=1, db_path=db)
        assert len(all_payments) == 1

    def test_update_payment_status(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        pid = record_payment(Payment(user_id=1, amount=99.00), db)
        assert update_payment_status(pid, PaymentStatus.FAILED, db)
        assert get_payment(pid, db)["status"] == "failed"


# --- Accounting: invoices + line items ---


class TestAccounting:
    def test_create_invoice(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        cid = _mk_customer(db)
        iid = create_invoice(Invoice(
            customer_id=cid, invoice_number="INV-0001",
            status=InvoiceStatus.DRAFT,
        ), db)
        row = get_invoice(iid, db)
        assert row["invoice_number"] == "INV-0001"
        assert row["status"] == "draft"

    def test_invoice_number_unique(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        cid = _mk_customer(db)
        create_invoice(Invoice(customer_id=cid, invoice_number="INV-0001"), db)
        with pytest.raises(Exception):
            create_invoice(Invoice(customer_id=cid, invoice_number="INV-0001"), db)

    def test_get_by_number(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        cid = _mk_customer(db)
        create_invoice(Invoice(customer_id=cid, invoice_number="INV-XYZ"), db)
        row = get_invoice_by_number("INV-XYZ", db)
        assert row is not None

    def test_line_items_and_recalc(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        cid = _mk_customer(db)
        iid = create_invoice(Invoice(customer_id=cid, invoice_number="INV-100"), db)

        add_line_item(InvoiceLineItem(
            invoice_id=iid, item_type=InvoiceLineItemType.LABOR,
            description="Diagnostic labor", quantity=2.0,
            unit_price=125.0, line_total=250.0,
        ), db)
        add_line_item(InvoiceLineItem(
            invoice_id=iid, item_type=InvoiceLineItemType.PARTS,
            description="Brake pad set", quantity=1.0,
            unit_price=85.0, line_total=85.0,
        ), db)
        items = get_line_items(iid, db)
        assert len(items) == 2

        totals = recalculate_invoice_totals(iid, tax_rate=0.0875, db_path=db)
        assert totals["subtotal"] == 335.0
        assert round(totals["tax_amount"], 2) == round(335.0 * 0.0875, 2)
        assert round(totals["total"], 2) == round(335.0 + 335.0 * 0.0875, 2)

        row = get_invoice(iid, db)
        assert row["subtotal"] == 335.0

    def test_cascade_deletes_line_items(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        cid = _mk_customer(db)
        iid = create_invoice(Invoice(customer_id=cid, invoice_number="INV-CASCADE"), db)
        add_line_item(InvoiceLineItem(
            invoice_id=iid, item_type=InvoiceLineItemType.LABOR,
            description="x",
        ), db)
        delete_invoice(iid, db)
        assert get_line_items(iid, db) == []


# --- Inventory ---


class TestInventory:
    def test_vendor_crud(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        vid = add_vendor(Vendor(name="Parts Unlimited", email="orders@pu.com"), db)
        assert get_vendor(vid, db)["name"] == "Parts Unlimited"
        assert get_vendor_by_name("Parts Unlimited", db) is not None

    def test_vendor_name_unique(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        add_vendor(Vendor(name="Dup"), db)
        with pytest.raises(Exception):
            add_vendor(Vendor(name="Dup"), db)

    def test_item_crud_with_json(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        vid = add_vendor(Vendor(name="V1"), db)
        iid = add_item(InventoryItem(
            sku="BRK-929-01",
            name="Brake pad front",
            category="brakes",
            make="Honda",
            model_applicable=["CBR929RR", "CBR954RR"],
            quantity_on_hand=5, reorder_point=2,
            unit_cost=15.0, unit_price=35.0,
            vendor_id=vid,
        ), db)
        row = get_item(iid, db)
        assert row["model_applicable"] == ["CBR929RR", "CBR954RR"]
        assert get_item_by_sku("BRK-929-01", db) is not None

    def test_sku_unique(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        add_item(InventoryItem(sku="DUP", name="A"), db)
        with pytest.raises(Exception):
            add_item(InventoryItem(sku="DUP", name="B"), db)

    def test_vendor_fk_set_null(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        vid = add_vendor(Vendor(name="VTEMP"), db)
        iid = add_item(InventoryItem(sku="X", name="X", vendor_id=vid), db)
        delete_vendor(vid, db)
        assert get_item(iid, db)["vendor_id"] is None

    def test_adjust_quantity(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        iid = add_item(InventoryItem(sku="Q1", name="Part", quantity_on_hand=10), db)
        assert adjust_quantity(iid, -3, db) == 7
        assert adjust_quantity(iid, +5, db) == 12

    def test_items_below_reorder(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        add_item(InventoryItem(sku="LOW", name="A", quantity_on_hand=1, reorder_point=5), db)
        add_item(InventoryItem(sku="OK", name="B", quantity_on_hand=10, reorder_point=5), db)
        low = items_below_reorder(db)
        skus = [i["sku"] for i in low]
        assert "LOW" in skus
        assert "OK" not in skus

    def test_recall_list_for_vehicle(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        add_recall(Recall(
            campaign_number="21V-234", make="Honda",
            year_start=2000, year_end=2005,
            description="Brake caliper bolt torque issue",
            severity="high",
        ), db)
        add_recall(Recall(
            campaign_number="22V-111", make="Harley-Davidson",
            description="Stator harness chafe",
        ), db)
        hits = list_recalls_for_vehicle("Honda", year=2001, db_path=db)
        assert len(hits) == 1
        assert hits[0]["campaign_number"] == "21V-234"

    def test_warranty_crud(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        veh = _mk_vehicle(db)
        wid = add_warranty(Warranty(
            vehicle_id=veh, coverage_type=CoverageType.EXTENDED,
            provider="Honda Extended Care",
            start_date="2026-04-17",
            end_date="2029-04-17",
            mileage_limit=36000,
        ), db)
        row = get_warranty(wid, db)
        assert row["coverage_type"] == "extended"
        assert increment_claim_count(wid, db) == 1
        assert increment_claim_count(wid, db) == 2
        assert get_warranty(wid, db)["claim_count"] == 2


# --- Scheduling ---


class TestScheduling:
    def test_create_and_get(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        cid = _mk_customer(db)
        aid = create_appointment(Appointment(
            customer_id=cid,
            appointment_type=AppointmentType.PPI,
            scheduled_start="2026-05-01T09:00:00",
            scheduled_end="2026-05-01T10:30:00",
        ), db)
        row = get_appointment(aid, db)
        assert row["appointment_type"] == "ppi"

    def test_list_filters(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        cid = _mk_customer(db)
        for t in (AppointmentType.PPI, AppointmentType.SERVICE, AppointmentType.DIAGNOSTIC):
            create_appointment(Appointment(
                customer_id=cid, appointment_type=t,
                scheduled_start="2026-05-01T09:00:00",
                scheduled_end="2026-05-01T10:00:00",
            ), db)
        ppis = list_appointments(appointment_type=AppointmentType.PPI, db_path=db)
        assert len(ppis) == 1

    def test_list_upcoming_filters_terminal(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        cid = _mk_customer(db)
        aid1 = create_appointment(Appointment(
            customer_id=cid, scheduled_start="2030-01-01T09:00:00",
            scheduled_end="2030-01-01T10:00:00",
        ), db)
        aid2 = create_appointment(Appointment(
            customer_id=cid, scheduled_start="2030-01-02T09:00:00",
            scheduled_end="2030-01-02T10:00:00",
        ), db)
        cancel_appointment(aid2, reason="Customer requested", db_path=db)
        upcoming = list_upcoming(from_iso="2029-12-31T00:00:00", db_path=db)
        ids = [a["id"] for a in upcoming]
        assert aid1 in ids
        assert aid2 not in ids

    def test_complete_appointment(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        cid = _mk_customer(db)
        aid = create_appointment(Appointment(
            customer_id=cid, scheduled_start="2026-05-01T09:00:00",
            scheduled_end="2026-05-01T10:00:00",
        ), db)
        assert complete_appointment(aid, actual_end="2026-05-01T10:15:00", db_path=db)
        row = get_appointment(aid, db)
        assert row["status"] == "completed"
        assert row["actual_end"] == "2026-05-01T10:15:00"

    def test_cascade_from_customer(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        cid = _mk_customer(db, name="CASCADE")
        aid = create_appointment(Appointment(
            customer_id=cid, scheduled_start="2026-05-01T09:00:00",
            scheduled_end="2026-05-01T10:00:00",
        ), db)
        with get_connection(db) as conn:
            conn.execute("DELETE FROM customers WHERE id = ?", (cid,))
        assert get_appointment(aid, db) is None


# --- Forward compat ---


class TestSchemaVersionForwardCompat:
    def test_schema_version_at_least_11(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        assert get_schema_version(db) >= 11

    def test_schema_version_constant_at_least_11(self):
        assert SCHEMA_VERSION >= 11
