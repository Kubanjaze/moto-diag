"""Phase 373 (F188) — warranty work on the invoice.

A claim records which of its work order's lines it covers (`shop warranty
claim cover`); the invoice leaves them off what the customer owes and prices
them for the claim, so the amount claimed is derived in integer cents, never
typed. The tax on covered work is keyed on who owes the repair, from the
jurisdiction's rule (`tax_warranty_rules`). A claim denied or paid short is
settled by the shop (`claim settle`). The claim is exported as owed by its
provider. Every test runs on a scratch database on a fixed clock.

The work order in most tests, worked by hand at 10000 cents an hour in
Massachusetts (parts taxable at 6.25%, labour not):
- 2.0 h of labour (20000); part row 1, 2 x 4000 (8000); part row 2, 1 x 2500.
- The claim covers 1.5 h (15000) and both of part row 1 (8000): 23000.
- The customer owes 0.5 h (5000) and part row 2 (2500): 7500, tax 156
  (2500 x 6.25% = 156.25), total 7656.
- Owed by someone else, the claim carries the parts' tax: 8000 x 6.25% =
  500, claimed 23500. Under a maker's warranty or the shop's own contract it
  carries none: 23000.
"""

from __future__ import annotations

import csv
import json
from datetime import date, datetime, timezone

import pytest

from support.frozen_clock import frozen_datetime
from support.phase274 import new_db, ok, refused, seed_bike, seed_customer, seed_shop, sql

DAY = "2026-10-15"
NOON = datetime(2026, 10, 15, 16, 0, tzinfo=timezone.utc)
RATE = "10000"


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    from motodiag.accounting import tax
    from motodiag.inventory import warranty_claims
    from motodiag.shop import invoicing

    monkeypatch.setattr(tax, "today", lambda: date.fromisoformat(DAY))
    frozen = frozen_datetime(NOON)
    monkeypatch.setattr(invoicing, "datetime", frozen)
    monkeypatch.setattr(warranty_claims, "datetime", frozen)


@pytest.fixture
def db(tmp_path):
    path = new_db(tmp_path)
    shop = seed_shop(path, "Harbor Moto")
    seed_customer(path, shop, "Dana Rider", "dana@example.com")
    seed_bike(path, "Honda", "CBR600RR", 2005, mileage=31200)
    ok(path, "shop", "tax", "jurisdiction", "set", "--shop", shop, "--code", "US-MA")
    return path


def _customer(db) -> int:
    return sql(db, "SELECT id FROM customers WHERE name = 'Dana Rider'")[0][0]


def _work_order(db, hours=2.0, parts=((4000, 2), (2500, 1)), bike=1) -> tuple[int, list[int]]:
    sql(db, "INSERT INTO work_orders (shop_id, vehicle_id, customer_id, title, status, "
            "actual_hours, opened_at, completed_at) VALUES (1, ?, ?, 'Brakes', "
            "'completed', ?, '2026-10-15T13:00:00', '2026-10-15T15:00:00')",
        (bike, _customer(db), hours))
    wo = sql(db, "SELECT MAX(id) FROM work_orders")[0][0]
    rows = []
    for i, (cents, qty) in enumerate(parts):
        sql(db, "INSERT INTO parts (slug, brand, description, category, make, "
                "model_pattern, typical_cost_cents) VALUES (?, 'Honda', ?, 'brakes', "
                "'Honda', '%', ?)", (f"p{wo}-{i}", f"Part {i + 1}", cents))
        part = sql(db, "SELECT MAX(id) FROM parts")[0][0]
        sql(db, "INSERT INTO work_order_parts (work_order_id, part_id, quantity, status) "
                "VALUES (?, ?, ?, 'installed')", (wo, part, qty))
        rows.append(sql(db, "SELECT MAX(id) FROM work_order_parts")[0][0])
    return wo, rows


def _warranty(db, payer="other", provider="Honda Protection Plan", bike=1) -> int:
    args = ["shop", "warranty", "add", "--bike", bike, "--coverage", "extended",
            "--start", "2024-03-01", "--end", "2027-02-28", "--mileage-limit", "40000"]
    if provider:
        args += ["--provider", provider]
    if payer:
        args += ["--payer", payer]
    ok(db, *args)
    return sql(db, "SELECT MAX(id) FROM warranties")[0][0]


def _claim(db, warranty, wo) -> int:
    ok(db, "shop", "warranty", "claim", "open", "--warranty", warranty, "--wo", wo,
       "--description", "Front brake pulls left")
    return sql(db, "SELECT MAX(id) FROM warranty_claims")[0][0]


def _generate(db, wo) -> int:
    out = ok(db, "shop", "invoice", "generate", wo, "--hourly-rate", RATE)
    return sql(db, "SELECT MAX(id) FROM invoices")[0][0]


def _invoice(db, invoice_id) -> dict:
    row = sql(db, "SELECT subtotal, tax_amount, total, status FROM invoices WHERE id = ?",
              (invoice_id,))[0]
    lines = sql(db, "SELECT item_type, quantity, line_total FROM invoice_line_items "
                    "WHERE invoice_id = ? ORDER BY sort_order, id", (invoice_id,))
    cents = lambda d: int(round(d * 100))  # noqa: E731  the REAL columns, read in cents
    return {"subtotal": cents(row[0]), "tax": cents(row[1]), "total": cents(row[2]),
            "status": row[3], "lines": [(t, q, cents(c)) for t, q, c in lines]}


def _claim_row(db, claim) -> dict:
    keys = ("status", "invoice_id", "covered_cents", "tax_cents", "amount_claimed_cents",
            "amount_approved_cents", "settlement", "shortfall_cents", "shortfall_invoice_id")
    return dict(zip(keys, sql(db, f"SELECT {', '.join(keys)} FROM warranty_claims "
                                  "WHERE id = ?", (claim,))[0]))


def _covered_job(db, payer="other"):
    """The work order of the module docstring, its claim covering 1.5 h and
    part row 1, and the invoice."""
    wo, wops = _work_order(db)
    claim = _claim(db, _warranty(db, payer), wo)
    ok(db, "shop", "warranty", "claim", "cover", claim, "--labour-hours", "1.5",
       "--part", wops[0])
    return wo, wops, claim, _generate(db, wo)


# --- Migration 081 ---


class TestMigration081:
    def test_the_tables_columns_and_massachusetts_rules(self, db):
        from motodiag.core.migrations import get_current_version

        assert get_current_version(db) >= 81
        rules = sql(db, "SELECT payer, taxed_on_claim, basis, provenance, valid_until, "
                        "source_url FROM tax_warranty_rules r JOIN tax_jurisdictions j "
                        "ON j.id = r.jurisdiction_id WHERE j.code = 'US-MA' ORDER BY payer")
        assert [r[:5] for r in rules] == [
            ("maker_with_bike", 0, "stated", "regulation", "2027-10-06"),
            ("other", 1, "reading", "regulation", "2027-10-06"),
            ("shop_contract", 0, "stated", "regulation", "2027-10-06"),
        ]
        assert all(r[5].startswith("https://www.mass.gov/") for r in rules)
        notes = sql(db, "SELECT notes FROM tax_warranty_rules")
        assert all("confirmed by the shop's accountant" in n for (n,) in notes)

    def test_the_rollback_takes_them_away_and_keeps_existing_rows(self, db):
        from motodiag.core.migrations import apply_pending_migrations, rollback_to_version

        wo, _ = _work_order(db)
        warranty = _warranty(db, payer=None)
        _claim(db, warranty, wo)
        before = sql(db, "SELECT id, warranty_id, work_order_id, status FROM warranty_claims")
        rollback_to_version(80, db)
        tables = {r[0] for r in sql(db, "SELECT name FROM sqlite_master WHERE type='table'")}
        assert not {"warranty_claim_lines", "tax_warranty_rules",
                    "accounting_export_claims"} & tables
        assert "repair_payer" not in [r[1] for r in sql(db, "PRAGMA table_info(warranties)")]
        assert sql(db, "SELECT id, warranty_id, work_order_id, status "
                       "FROM warranty_claims") == before
        assert 81 in apply_pending_migrations(db)

    @pytest.mark.parametrize("query", [
        "UPDATE warranties SET repair_payer = 'the customer'",
        "INSERT INTO warranty_claim_lines (claim_id, line_type, quantity) "
        "VALUES (1, 'parts', 1)",
        "INSERT INTO warranty_claim_lines (claim_id, line_type, quantity) "
        "VALUES (1, 'labor', 0)",
        "INSERT INTO warranty_claim_lines (claim_id, line_type, quantity, amount_cents) "
        "VALUES (1, 'labor', 1, -1)",
        "UPDATE warranty_claims SET settlement = 'waived'",
    ])
    def test_the_checks_refuse_what_cannot_be(self, db, query):
        import sqlite3

        wo, _ = _work_order(db)
        _claim(db, _warranty(db), wo)
        with pytest.raises(sqlite3.IntegrityError):
            sql(db, query)


# --- Who owes the repair ---


class TestThePayer:
    def test_add_records_it_and_update_changes_it(self, db):
        warranty = _warranty(db, payer=None, provider=None)
        assert "not recorded" in ok(db, "shop", "warranty", "list", "--bike", "1")
        ok(db, "shop", "warranty", "update", warranty, "--payer", "maker_with_bike",
           "--provider", "Honda")
        assert sql(db, "SELECT repair_payer, provider FROM warranties") == [
            ("maker_with_bike", "Honda")]
        assert "maker_with_bike" in ok(db, "shop", "warranty", "list", "--bike", "1")

    def test_update_refuses_nothing_and_an_unknown_warranty(self, db):
        warranty = _warranty(db)
        refused(db, "shop", "warranty", "update", warranty)
        refused(db, "shop", "warranty", "update", "99", "--payer", "other")
        refused(db, "shop", "warranty", "update", warranty, "--payer", "the customer")


# --- Covering lines ---


class TestCover:
    def test_cover_records_the_lines_and_covering_again_replaces_them(self, db):
        wo, wops = _work_order(db)
        claim = _claim(db, _warranty(db), wo)
        out = ok(db, "shop", "warranty", "claim", "cover", claim, "--labour-hours", "1.5",
                 "--part", wops[0])
        assert "labour 1.50 h" in out and "2 x Honda Part 1" in out
        ok(db, "shop", "warranty", "claim", "cover", claim, "--part", f"{wops[0]}=1")
        assert sql(db, "SELECT line_type, work_order_part_id, quantity, amount_cents "
                       "FROM warranty_claim_lines") == [("parts", wops[0], 1.0, None)]

    def test_none_records_that_it_covers_nothing(self, db):
        wo, _ = _work_order(db)
        claim = _claim(db, _warranty(db, payer=None, provider=None), wo)
        ok(db, "shop", "warranty", "claim", "cover", claim, "--none")
        assert sql(db, "SELECT coverage_recorded_at IS NOT NULL FROM warranty_claims") == [(1,)]
        assert sql(db, "SELECT COUNT(*) FROM warranty_claim_lines") == [(0,)]

    @pytest.mark.parametrize("args, why", [
        ((), "say which lines"),
        (("--none", "--labour-hours", "1"), "not both"),
        (("--labour-hours", "2.5"), "at most 2 h"),
        (("--part", "99"), "not on work order"),
        (("--part", "1=3"), "can cover 1 to 2"),
        (("--part", "1", "--part", "1"), "given twice"),
        (("--part", "one"), "ROW or ROW=QTY"),
    ])
    def test_what_the_order_does_not_hold_is_refused(self, db, args, why):
        wo, _ = _work_order(db)
        claim = _claim(db, _warranty(db), wo)
        assert why in refused(db, "shop", "warranty", "claim", "cover", claim, *args)
        assert sql(db, "SELECT COUNT(*) FROM warranty_claim_lines") == [(0,)]

    def test_two_claims_cannot_cover_more_than_the_order(self, db):
        wo, wops = _work_order(db)
        warranty = _warranty(db)
        first, second = _claim(db, warranty, wo), _claim(db, warranty, wo)
        ok(db, "shop", "warranty", "claim", "cover", first, "--labour-hours", "1.5",
           "--part", f"{wops[0]}=1")
        assert "at most 0.5 h" in refused(db, "shop", "warranty", "claim", "cover", second,
                                          "--labour-hours", "1")
        assert "can cover 1 to 1" in refused(db, "shop", "warranty", "claim", "cover",
                                             second, "--part", f"{wops[0]}=2")

    @pytest.mark.parametrize("missing, why", [("payer", "who owes the repair"),
                                              ("provider", "who gives it")])
    def test_the_payer_and_provider_must_be_on_record(self, db, missing, why):
        wo, wops = _work_order(db)
        warranty = _warranty(db, payer=None if missing == "payer" else "other",
                             provider=None if missing == "provider" else "HPP")
        claim = _claim(db, warranty, wo)
        out = refused(db, "shop", "warranty", "claim", "cover", claim, "--part", wops[0])
        assert why in out and f"shop warranty update {warranty}" in out

    def test_only_a_draft_on_a_work_order_not_invoiced_can_change(self, db):
        wo, wops, claim, invoice = _covered_job(db)
        out = refused(db, "shop", "warranty", "claim", "cover", claim, "--none")
        assert "already invoiced" in out and f"invoice void {invoice}" in out
        ok(db, "shop", "warranty", "claim", "status", claim, "--to", "submitted")
        assert "only a draft" in refused(db, "shop", "warranty", "claim", "cover", claim,
                                         "--none")
        ok(db, "shop", "warranty", "claim", "open", "--warranty", "1",
           "--description", "no work order")
        assert "no work order" in refused(db, "shop", "warranty", "claim", "cover",
                                          claim + 1, "--labour-hours", "1")

    def test_the_typed_amount_is_gone(self, db):
        wo, _ = _work_order(db)
        refused(db, "shop", "warranty", "claim", "open", "--warranty", _warranty(db),
                "--wo", wo, "--description", "x", "--claimed-cents", "41400")


# --- The invoice ---


class TestTheInvoice:
    def test_a_claim_with_no_coverage_recorded_stops_the_invoice(self, db):
        wo, _ = _work_order(db)
        claim = _claim(db, _warranty(db), wo)
        out = refused(db, "shop", "invoice", "generate", wo, "--hourly-rate", RATE)
        assert f"shop warranty claim cover {claim}" in out
        assert sql(db, "SELECT COUNT(*) FROM invoices") == [(0,)]

    def test_covered_lines_are_off_the_invoice_and_priced_for_the_claim(self, db):
        wo, wops, claim, invoice = _covered_job(db)
        assert _invoice(db, invoice) == {
            "subtotal": 7500, "tax": 156, "total": 7656, "status": "sent",
            "lines": [("labor", 0.5, 5000), ("parts", 1.0, 2500)]}
        assert _claim_row(db, claim) == {
            "status": "draft", "invoice_id": invoice, "covered_cents": 23000,
            "tax_cents": 500, "amount_claimed_cents": 23500, "amount_approved_cents": None,
            "settlement": None, "shortfall_cents": None, "shortfall_invoice_id": None}
        assert sql(db, "SELECT line_type, amount_cents FROM warranty_claim_lines "
                       "ORDER BY id") == [("labor", 15000), ("parts", 8000)]
        # the customer and the claim together are the work order: 20000 + 10500
        assert 7500 + 23000 == 30500
        notes = sql(db, "SELECT notes FROM invoices WHERE id = ?", (invoice,))[0][0]
        assert f"Warranty claim #{claim} covers: labour 1.50 h; 2 x Honda Part 1" in notes

    @pytest.mark.parametrize("payer, tax", [("other", 500), ("maker_with_bike", 0),
                                            ("shop_contract", 0)])
    def test_the_claims_tax_follows_who_owes_the_repair(self, db, payer, tax):
        _, _, claim, invoice = _covered_job(db, payer)
        row = _claim_row(db, claim)
        assert (row["tax_cents"], row["amount_claimed_cents"]) == (tax, 23000 + tax)
        assert _invoice(db, invoice)["total"] == 7656  # the customer's side never moves
        source = sql(db, "SELECT tax_source FROM warranty_claims")[0][0]
        assert {"other": "79-19", "maker_with_bike": "03-8",
                "shop_contract": "64H.1.1"}[payer] in source

    def test_with_no_rule_for_the_payer_the_invoice_is_refused(self, db):
        sql(db, "DELETE FROM tax_warranty_rules WHERE payer = 'other'")
        wo, wops = _work_order(db)
        claim = _claim(db, _warranty(db), wo)
        ok(db, "shop", "warranty", "claim", "cover", claim, "--part", wops[0])
        out = refused(db, "shop", "invoice", "generate", wo, "--hourly-rate", RATE)
        assert "shop tax warranty-rule set --shop 1 --payer other" in out
        assert sql(db, "SELECT COUNT(*) FROM invoices") == [(0,)]

    def test_a_shops_own_rule_is_used(self, db):
        ok(db, "shop", "tax", "warranty-rule", "set", "--shop", "1", "--payer", "other",
           "--not-on-claim", "--effective", "2026-01-01", "--valid-until", "2027-12-31",
           "--source-title", "The shop's accountant, letter of 2026-10-01",
           "--checked-on", "2026-10-01")
        _, _, claim, _ = _covered_job(db)
        assert _claim_row(db, claim)["tax_cents"] == 0
        assert "accountant" in sql(db, "SELECT tax_source FROM warranty_claims")[0][0]

    def test_a_denied_claim_is_left_out(self, db):
        wo, wops = _work_order(db)
        claim = _claim(db, _warranty(db), wo)
        ok(db, "shop", "warranty", "claim", "cover", claim, "--part", wops[0])
        ok(db, "shop", "warranty", "claim", "status", claim, "--to", "submitted")
        ok(db, "shop", "warranty", "claim", "status", claim, "--to", "denied")
        invoice = _generate(db, wo)
        assert _invoice(db, invoice)["total"] == 20000 + 10500 + 656  # 10500 x 6.25%
        assert _claim_row(db, claim)["invoice_id"] is None

    def test_everything_covered_leaves_the_customer_nothing_to_pay(self, db):
        wo, wops = _work_order(db, parts=((4000, 2),))
        claim = _claim(db, _warranty(db), wo)
        ok(db, "shop", "warranty", "claim", "cover", claim, "--labour-hours", "2",
           "--part", wops[0])
        invoice = _generate(db, wo)
        assert _invoice(db, invoice) == {"subtotal": 0, "tax": 0, "total": 0,
                                         "status": "paid", "lines": []}
        assert _claim_row(db, claim)["amount_claimed_cents"] == 28500

    def test_a_covered_part_not_received_stops_the_invoice(self, db):
        wo, wops = _work_order(db)
        claim = _claim(db, _warranty(db), wo)
        ok(db, "shop", "warranty", "claim", "cover", claim, "--part", wops[1])
        sql(db, "UPDATE work_order_parts SET status = 'ordered' WHERE id = ?", (wops[1],))
        assert "not received or installed" in refused(db, "shop", "invoice", "generate",
                                                      wo, "--hourly-rate", RATE)

    def test_the_api_route_obeys_the_claim(self, db, monkeypatch):
        """No request model changes: the route reads the claim from the database."""
        from fastapi.testclient import TestClient

        from motodiag.api import create_app
        from motodiag.auth.api_key_repo import create_api_key
        from motodiag.core.config import reset_settings
        from motodiag.shop import seed_first_owner

        monkeypatch.setenv("MOTODIAG_DB_PATH", db)
        monkeypatch.setenv("MOTODIAG_RATE_LIMIT_SHOP_PER_MINUTE", "9999")
        reset_settings()
        user = sql(db, "INSERT INTO users (username, email, tier, is_active) "
                       "VALUES ('o', 'o@ex.com', 'shop', 1) RETURNING id")[0][0]
        sql(db, "INSERT INTO subscriptions (user_id, tier, status, current_period_end) "
                "VALUES (?, 'shop', 'active', datetime('now', '+30 days'))", (user,))
        _, key = create_api_key(user, db_path=db)
        seed_first_owner(1, user, db_path=db)
        client = TestClient(create_app(db_path_override=db), raise_server_exceptions=False)
        wo, wops = _work_order(db)
        claim = _claim(db, _warranty(db), wo)
        body = {"work_order_id": wo, "labor_hourly_rate_cents": int(RATE)}
        r = client.post("/v1/shop/1/invoices/generate", headers={"X-API-Key": key}, json=body)
        assert r.status_code == 422 and f"claim cover {claim}" in r.text, r.text
        ok(db, "shop", "warranty", "claim", "cover", claim, "--labour-hours", "1.5",
           "--part", wops[0])
        r = client.post("/v1/shop/1/invoices/generate", headers={"X-API-Key": key}, json=body)
        assert r.status_code == 201, r.text
        assert (r.json()["total_cents"], r.json()["tax_cents"]) == (7656, 156)
        reset_settings()


class TestVoidAndRegenerate:
    def test_void_and_regenerate_are_unchanged_and_price_the_claim_again(self, db):
        wo, _, claim, invoice = _covered_job(db)
        first = _invoice(db, invoice)
        ok(db, "shop", "invoice", "void", invoice, "--reason", "typo")
        again = _generate(db, wo)
        assert again != invoice
        assert _invoice(db, again) == first
        assert _claim_row(db, claim)["invoice_id"] == again
        assert _claim_row(db, claim)["amount_claimed_cents"] == 23500

    def test_a_claim_past_draft_is_not_priced_differently(self, db):
        wo, _, claim, invoice = _covered_job(db)
        ok(db, "shop", "warranty", "claim", "status", claim, "--to", "submitted")
        ok(db, "shop", "invoice", "void", invoice)
        out = refused(db, "shop", "invoice", "generate", wo, "--hourly-rate", "11000")
        # 1.5 h x 11000 = 16500, + 8000 parts + 500 tax = 25000
        assert "is submitted at 23500 cents" in out and "price it at 25000 cents" in out
        _generate(db, wo)  # the same rate prices it the same

    def test_a_second_invoice_is_still_refused(self, db):
        wo, _, _, invoice = _covered_job(db)
        assert f"invoice id={invoice} already exists" in refused(
            db, "shop", "invoice", "generate", wo, "--hourly-rate", RATE)


# --- The decision and the settlement ---


def _decided(db, to, approved=None):
    wo, wops, claim, invoice = _covered_job(db)
    ok(db, "shop", "warranty", "claim", "status", claim, "--to", "submitted")
    args = ["--approved-cents", approved] if approved is not None else []
    ok(db, "shop", "warranty", "claim", "status", claim, "--to", to, *args)
    return wo, claim, invoice


class TestSettle:
    def test_approval_above_the_claim_is_refused(self, db):
        _, _, claim, _ = _covered_job(db)
        ok(db, "shop", "warranty", "claim", "status", claim, "--to", "submitted")
        assert "claims 23500 cents" in refused(db, "shop", "warranty", "claim", "status",
                                               claim, "--to", "approved",
                                               "--approved-cents", "23501")

    def test_a_denied_claim_billed_to_the_customer(self, db):
        wo, claim, invoice = _decided(db, "denied")
        out = ok(db, "shop", "warranty", "claim", "settle", claim, "--bill-customer")
        row = _claim_row(db, claim)
        assert (row["settlement"], row["shortfall_cents"]) == ("bill_customer", 23500)
        shortfall = row["shortfall_invoice_id"]
        assert f"invoice id={shortfall}" in out
        assert _invoice(db, shortfall) == {
            "subtotal": 23000, "tax": 500, "total": 23500, "status": "sent",
            "lines": [("labor", 1.0, 15000), ("parts", 1.0, 8000)]}
        number, owner, linked = sql(db, "SELECT invoice_number, customer_id, "
                                        "shortfall_claim_id FROM invoices WHERE id = ?",
                                    (shortfall,))[0]
        assert number == f"INV-1-{wo}-20261015-S{claim}"
        assert (owner, linked) == (_customer(db), claim)
        assert _invoice(db, invoice)["total"] == 7656  # the first invoice is untouched

    def test_a_part_approval_bills_the_customer_in_proportion(self, db):
        """Shortfall 3500 of 23500: pre-tax 23000 x 3500 / 23500 = 3425.53 -> 3426,
        split 15000:8000 by largest remainder -> 2234 + 1192; the customer's tax
        1192 x 6.25% = 74.5 -> 75."""
        _, claim, _ = _decided(db, "approved", 20000)
        ok(db, "shop", "warranty", "claim", "settle", claim, "--bill-customer")
        row = _claim_row(db, claim)
        assert row["shortfall_cents"] == 3500
        assert _invoice(db, row["shortfall_invoice_id"]) == {
            "subtotal": 3426, "tax": 75, "total": 3501, "status": "sent",
            "lines": [("labor", 1.0, 2234), ("parts", 1.0, 1192)]}

    def test_the_shop_absorbs_it(self, db):
        _, claim, _ = _decided(db, "approved", 20000)
        ok(db, "shop", "warranty", "claim", "status", claim, "--to", "paid")
        ok(db, "shop", "warranty", "claim", "settle", claim, "--absorb")
        row = _claim_row(db, claim)
        assert (row["settlement"], row["shortfall_cents"], row["shortfall_invoice_id"]) == (
            "absorb", 3500, None)
        assert sql(db, "SELECT COUNT(*) FROM invoices") == [(1,)]
        assert "Shortfall: $35.00, absorbed by the shop" in ok(
            db, "shop", "warranty", "claim", "packet", claim)

    def test_a_settled_claim_does_not_settle_again(self, db):
        _, claim, _ = _decided(db, "denied")
        ok(db, "shop", "warranty", "claim", "settle", claim, "--absorb")
        assert "was settled" in refused(db, "shop", "warranty", "claim", "settle", claim,
                                        "--bill-customer")
        assert sql(db, "SELECT COUNT(*) FROM invoices") == [(1,)]

    @pytest.mark.parametrize("to, approved, why", [
        ("submitted", None, "settle it once it is denied"),
        ("approved", None, "has no approved amount"),
        ("approved", 23500, "nothing to settle"),
    ])
    def test_what_there_is_nothing_to_settle_is_refused(self, db, to, approved, why):
        _, _, claim, _ = _covered_job(db)
        if to != "submitted":
            ok(db, "shop", "warranty", "claim", "status", claim, "--to", "submitted")
        args = ["--approved-cents", approved] if approved is not None else []
        ok(db, "shop", "warranty", "claim", "status", claim, "--to", to, *args)
        assert why in refused(db, "shop", "warranty", "claim", "settle", claim, "--absorb")

    def test_a_claim_never_invoiced_or_with_its_invoice_void_is_refused(self, db):
        wo, wops = _work_order(db)
        claim = _claim(db, _warranty(db), wo)
        ok(db, "shop", "warranty", "claim", "status", claim, "--to", "submitted")
        ok(db, "shop", "warranty", "claim", "status", claim, "--to", "denied")
        assert "never invoiced" in refused(db, "shop", "warranty", "claim", "settle",
                                           claim, "--absorb")
        _, other, invoice = _decided(db, "denied")
        ok(db, "shop", "invoice", "void", invoice)
        assert "invoice is void" in refused(db, "shop", "warranty", "claim", "settle",
                                            other, "--bill-customer")
        assert "choose --bill-customer or --absorb" in refused(
            db, "shop", "warranty", "claim", "settle", other)

    def test_after_a_settlement_regenerating_does_not_bill_the_covered_lines_again(self, db):
        wo, claim, invoice = _decided(db, "denied")
        ok(db, "shop", "warranty", "claim", "settle", claim, "--bill-customer")
        ok(db, "shop", "invoice", "void", invoice)
        again = _generate(db, wo)
        assert _invoice(db, again)["total"] == 7656
        assert _claim_row(db, claim)["invoice_id"] == again

    def test_only_settle_writes_a_second_invoice(self, db):
        wo, claim, invoice = _decided(db, "denied")
        ok(db, "shop", "warranty", "claim", "settle", claim, "--bill-customer")
        assert "already exists" in refused(db, "shop", "invoice", "generate", wo,
                                           "--hourly-rate", RATE)
        assert sql(db, "SELECT COUNT(*) FROM invoices WHERE work_order_id = ?",
                   (wo,)) == [(2,)]


# --- The packet ---


class TestThePacket:
    def test_before_the_invoice_it_says_the_lines_are_priced_then(self, db):
        wo, wops = _work_order(db)
        claim = _claim(db, _warranty(db), wo)
        ok(db, "shop", "warranty", "claim", "cover", claim, "--part", wops[0])
        text = ok(db, "shop", "warranty", "claim", "packet", claim)
        assert "- 2 x Honda Part 1: priced when the invoice is generated" in text
        assert "Amount claimed: not recorded" in text

    def test_after_it_the_packet_lists_the_lines_and_the_amount(self, db):
        _, _, claim, _ = _covered_job(db)
        text = ok(db, "shop", "warranty", "claim", "packet", claim)
        for expected in ("Repair owed by: someone else's plan or contract",
                         "- labour 1.50 h: $150.00", "- 2 x Honda Part 1: $80.00",
                         "Covered work: $230.00", "Tax on the claim: $5.00 (",
                         "Amount claimed: $235.00"):
            assert expected in text, expected


# --- The export ---


def _map_accounts(db):
    for kind, account in (("receivable", "Accounts Receivable (A/R)"),
                          ("labor", "Labor Income"), ("parts", "Parts Sales"),
                          ("tax", "Sales Tax Payable")):
        ok(db, "shop", "accounting", "map", "set", "--shop", "1", "--target",
           "quickbooks-online", "--kind", kind, "--account", account)
    for kind, code, tax_type in (("labor", "200", "Tax Exempt"),
                                 ("parts", "210", "Tax on Sales (6.25%)")):
        ok(db, "shop", "accounting", "map", "set", "--shop", "1", "--target", "xero",
           "--kind", kind, "--account", code, "--tax-type", tax_type)


def _export(db, tmp_path, target, name=None):
    path = tmp_path / (name or f"{target}.csv")
    out = ok(db, "shop", "accounting", "export", "--shop", "1", "--target", target,
             "--from", DAY, "--to", DAY, "--out", path)
    with path.open(newline="", encoding="utf-8") as f:
        return out, list(csv.DictReader(f))


class TestTheExport:
    def test_quickbooks_has_the_claim_as_owed_by_the_provider(self, db, tmp_path):
        _, _, claim, invoice = _covered_job(db)
        _map_accounts(db)
        out, rows = _export(db, tmp_path, "quickbooks-online")
        assert "Wrote 1 invoice(s) and 1 warranty claim(s)" in out
        number = sql(db, "SELECT invoice_number FROM invoices WHERE id = ?", (invoice,))[0][0]
        claim_rows = [(r["Account Name"], r["Debits"], r["Credits"], r["Name"])
                      for r in rows if r["Journal No."] == f"{number}-W{claim}"]
        assert claim_rows == [
            ("Accounts Receivable (A/R)", "235.00", "", "Honda Protection Plan"),
            ("Labor Income", "", "150.00", ""), ("Parts Sales", "", "80.00", ""),
            ("Sales Tax Payable", "", "5.00", "")]
        customer_rows = [(r["Account Name"], r["Debits"], r["Credits"])
                         for r in rows if r["Journal No."] == number]
        assert customer_rows == [("Accounts Receivable (A/R)", "76.56", ""),
                                 ("Labor Income", "", "50.00"), ("Parts Sales", "", "25.00"),
                                 ("Sales Tax Payable", "", "1.56")]
        assert sql(db, "SELECT claim_id FROM accounting_export_claims") == [(claim,)]

    def test_xero_has_the_claim_as_an_invoice_to_the_provider(self, db, tmp_path):
        _, _, claim, invoice = _covered_job(db)
        _map_accounts(db)
        _, rows = _export(db, tmp_path, "xero")
        number = sql(db, "SELECT invoice_number FROM invoices WHERE id = ?", (invoice,))[0][0]
        got = [(r["ContactName"], r["Quantity"], r["UnitAmount"], r["AccountCode"],
                r["TaxAmount"]) for r in rows if r["InvoiceNumber"] == f"{number}-W{claim}"]
        assert got == [("Honda Protection Plan", "1", "150.00", "200", "0.00"),
                       ("Honda Protection Plan", "1", "80.00", "210", "5.00")]

    def test_an_invoice_with_nothing_owed_writes_only_the_claim(self, db, tmp_path):
        wo, wops = _work_order(db, parts=((4000, 2),))
        claim = _claim(db, _warranty(db), wo)
        ok(db, "shop", "warranty", "claim", "cover", claim, "--labour-hours", "2",
           "--part", wops[0])
        invoice = _generate(db, wo)
        _map_accounts(db)
        number = sql(db, "SELECT invoice_number FROM invoices WHERE id = ?", (invoice,))[0][0]
        for target in ("quickbooks-online", "xero"):
            _, rows = _export(db, tmp_path, target)
            key = "Journal No." if target == "quickbooks-online" else "InvoiceNumber"
            assert {r[key] for r in rows} == {f"{number}-W{claim}"}

    def test_a_shortfall_invoice_is_exported_with_its_settlement(self, db, tmp_path):
        """Inverted by Phase 376 (F190): until then the shortfall invoice was
        left out and named; now it is exported after its settlement's credit."""
        _, claim, invoice = _decided(db, "denied")
        ok(db, "shop", "warranty", "claim", "settle", claim, "--bill-customer")
        _map_accounts(db)
        out, rows = _export(db, tmp_path, "quickbooks-online")
        shortfall = sql(db, "SELECT invoice_number FROM invoices WHERE shortfall_claim_id "
                            "IS NOT NULL")[0][0]
        number = sql(db, "SELECT invoice_number FROM invoices WHERE id = ?", (invoice,))[0][0]
        journals = list(dict.fromkeys(r["Journal No."] for r in rows))
        assert journals == [number, f"{number}-W{claim}", f"{number}-W{claim}-CR", shortfall]
        assert "not in the export yet" not in out
        assert "Wrote 2 invoice(s)" in out and "1 warranty claim settlement(s)" in out

    def test_a_claim_with_no_provider_is_refused(self, db, tmp_path):
        _covered_job(db)
        sql(db, "UPDATE warranties SET provider = NULL")
        _map_accounts(db)
        out = refused(db, "shop", "accounting", "export", "--shop", "1", "--target",
                      "xero", "--from", DAY, "--to", DAY, "--out", tmp_path / "x.csv")
        assert "shop warranty update 1 --provider NAME" in out
        assert not (tmp_path / "x.csv").exists()


# --- The tax commands ---


class TestTheTaxCommands:
    def test_status_lists_the_warranty_rules(self, db):
        status = json.loads(ok(db, "shop", "tax", "status", "--shop", "1", "--json"))
        assert {p: r["value"] for p, r in status["warranty_rules"].items()} == {
            "maker_with_bike": 0.0, "other": 1.0, "shop_contract": 0.0}
        text = ok(db, "shop", "tax", "status", "--shop", "1")
        assert "Warranty work owed by someone else's plan or contract: taxed on the claim" \
            in text
        assert "a reading of the source" in text

    def test_after_its_validity_a_warranty_rule_fails_status_and_confirm_renews_it(
            self, db, monkeypatch):
        from motodiag.accounting import tax

        monkeypatch.setattr(tax, "today", lambda: date(2027, 10, 7))
        sql(db, "UPDATE tax_rates SET valid_until = '2028-12-31'")
        sql(db, "UPDATE tax_line_rules SET valid_until = '2028-12-31'")
        out = refused(db, "shop", "tax", "status", "--shop", "1")
        assert "warranty work owed by someone else's plan or contract was valid until " \
               "2027-10-06" in " ".join(out.split())
        out = ok(db, "shop", "tax", "confirm", "--jurisdiction", "US-MA", "--checked-on",
                 "2027-10-07", "--source-url", "https://www.mass.gov/")
        assert "3 warranty rules" in out
        ok(db, "shop", "tax", "status", "--shop", "1")
        assert sql(db, "SELECT COUNT(*), MAX(valid_until) FROM tax_warranty_rules") == [
            (6, "2028-10-07")]
