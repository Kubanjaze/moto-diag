"""Phase 375 — warranty deductibles.

A warranty plan may charge the customer a deductible for each covered
repair, as LR 79-19's plan did ($25.00). The operator's choices (1A, 2A,
3A, 4A):

- the deductible is recorded on the warranty (`warranty add/update
  --deductible-cents`) and applied once per claim with covered lines, capped
  at the claim's covered work;
- it is split over the claim's covered lines by amount; the customer's
  invoice charges it by covered kind, taxed on its taxable share by the
  jurisdiction's reading (`tax_deductible_rules`); the claim is the covered
  work less it, and its tax is the tax on all the covered work less the
  deductible's, so together they are the tax on the whole parts charge;
- both export files carry it as ordinary lines, and a settlement bills
  only what the customer has not been charged.

The worked example is Phase 373's case, all covered: 1.5 h at 10000 cents
an hour (15000) and part row 1, 2 x 4000 (8000), in Massachusetts (parts
taxed at 6.25 %, labour not), owed by someone else's plan. With a 2500
deductible: labour 1630 + parts 870 to the customer, tax 54, 2554; the
claim 13370 + 7130, tax 500 - 54 = 446, claimed 20946. Together 23500.

Every test runs in New York on a fixed clock (Phase 370's frozen clock),
2026-10-15 12:00 EDT.
"""

from __future__ import annotations

import csv
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pytest

from support.frozen_clock import frozen_datetime, set_zone
from support.phase274 import new_db, ok, refused, seed_bike, seed_customer, seed_shop, sql

ZONE = "America/New_York"
DAY = "2026-10-15"
NOON = datetime(2026, 10, 15, 16, 0, tzinfo=timezone.utc)          # 12:00 EDT
RATE = "10000"
AR = "Accounts Receivable (A/R)"
PLAN = "Honda Protection Plan"
DEDUCTIBLE = 2500


@pytest.fixture
def clock(monkeypatch):
    """Freeze invoicing's and settling's clock, and the tax day, in New York."""
    from motodiag.accounting import tax
    from motodiag.inventory import warranty_claims
    from motodiag.shop import invoicing

    set_zone(ZONE)
    frozen = frozen_datetime(NOON)
    monkeypatch.setattr(invoicing, "datetime", frozen)
    monkeypatch.setattr(warranty_claims, "datetime", frozen)
    monkeypatch.setattr(tax, "today", lambda: NOON.astimezone().date())
    yield
    monkeypatch.undo()
    set_zone(None)


@pytest.fixture
def db(clock, tmp_path):
    path = new_db(tmp_path)
    shop = seed_shop(path, "Harbor Moto")
    seed_customer(path, shop, "Dana Rider", "dana@example.com")
    seed_bike(path, "Honda", "CBR600RR", 2005, mileage=31200)
    ok(path, "shop", "tax", "jurisdiction", "set", "--shop", shop, "--code", "US-MA")
    return path


# --- The job ---


def _work_order(db, hours=1.5, parts=((4000, 2),)) -> tuple[int, list[int]]:
    customer = sql(db, "SELECT id FROM customers WHERE name = 'Dana Rider'")[0][0]
    sql(db, "INSERT INTO work_orders (shop_id, vehicle_id, customer_id, title, status, "
            "actual_hours, opened_at, completed_at) VALUES (1, 1, ?, 'Brakes', "
            "'completed', ?, '2026-10-15T13:00:00', '2026-10-15T15:00:00')",
        (customer, hours))
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


def _warranty(db, payer="other", deductible=DEDUCTIBLE) -> int:
    args = ["shop", "warranty", "add", "--bike", 1, "--coverage", "extended",
            "--start", "2024-03-01", "--end", "2027-02-28", "--mileage-limit", "40000",
            "--provider", PLAN, "--payer", payer]
    if deductible is not None:
        args += ["--deductible-cents", deductible]
    ok(db, *args)
    return sql(db, "SELECT MAX(id) FROM warranties")[0][0]


def _covered(db, payer="other", deductible=DEDUCTIBLE, hours=1.5,
             parts=((4000, 2),), invoice=True, extra=()) -> tuple[int, int, int]:
    """The covered job: 1.5 h and part row 1 on a claim. Returns (wo, claim,
    invoice or None)."""
    wo, wops = _work_order(db, hours, parts)
    warranty = _warranty(db, payer, deductible)
    ok(db, "shop", "warranty", "claim", "open", "--warranty", warranty, "--wo", wo,
       "--description", "Front brake pulls left")
    claim = sql(db, "SELECT MAX(id) FROM warranty_claims")[0][0]
    ok(db, "shop", "warranty", "claim", "cover", claim, "--labour-hours", "1.5",
       "--part", wops[0])
    if not invoice:
        return wo, claim, None
    ok(db, "shop", "invoice", "generate", wo, "--hourly-rate", RATE, *extra)
    return wo, claim, sql(db, "SELECT MAX(id) FROM invoices")[0][0]


def _claim(db, claim) -> dict:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        return dict(conn.execute("SELECT * FROM warranty_claims WHERE id = ?",
                                 (claim,)).fetchone())
    finally:
        conn.close()


def _cents(dollars) -> int:
    return int(round(float(dollars or 0) * 100))


def _invoice(db, invoice) -> tuple[int, int, int, list[tuple[str, str, int]]]:
    """(subtotal, tax, total, [(type, description, line total)]) in cents."""
    subtotal, tax, total = sql(db, "SELECT subtotal, tax_amount, total FROM invoices "
                                   "WHERE id = ?", (invoice,))[0]
    lines = [(t, d, _cents(v)) for t, d, v in sql(
        db, "SELECT item_type, description, line_total FROM invoice_line_items "
            "WHERE invoice_id = ? ORDER BY sort_order, id", (invoice,))]
    return _cents(subtotal), _cents(tax), _cents(total), lines


def _claim_lines(db, claim) -> list[tuple[str, int, int]]:
    return sql(db, "SELECT line_type, amount_cents, deductible_cents FROM "
                   "warranty_claim_lines WHERE claim_id = ? ORDER BY id", (claim,))


def _flat(text: str) -> str:
    return " ".join(text.split())


# --- The export ---


def _map(db, absorbed=True):
    for kind, account in (("receivable", AR), ("labor", "Labor Income"),
                          ("parts", "Parts Sales"), ("tax", "Sales Tax Payable"),
                          ("absorbed", "Warranty Write-offs")):
        if kind != "absorbed" or absorbed:
            ok(db, "shop", "accounting", "map", "set", "--shop", "1", "--target",
               "quickbooks-online", "--kind", kind, "--account", account)
    for kind, code, tax_type in (("labor", "200", "Tax Exempt"),
                                 ("parts", "210", "Tax on Sales (6.25%)"),
                                 ("absorbed", "690", "Tax Exempt")):
        if kind != "absorbed" or absorbed:
            ok(db, "shop", "accounting", "map", "set", "--shop", "1", "--target", "xero",
               "--kind", kind, "--account", code, "--tax-type", tax_type)


def _read(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _export(db, tmp_path, target, name=None) -> Path:
    path = tmp_path / (name or f"{target}.csv")
    ok(db, "shop", "accounting", "export", "--shop", "1", "--target", target,
       "--from", DAY, "--to", DAY, "--out", path)
    return path


def _money(text: str) -> int:
    if not text:
        return 0
    sign = -1 if text.startswith("-") else 1
    whole, _, frac = text.lstrip("-").partition(".")
    return sign * (int(whole) * 100 + int((frac + "00")[:2]))


def _journals(rows) -> dict[str, list[tuple[str, int, str]]]:
    """Each journal's rows as (account, net debit, name)."""
    out: dict[str, list[tuple[str, int, str]]] = defaultdict(list)
    for r in rows:
        out[r["Journal No."]].append(
            (r["Account Name"], _money(r["Debits"]) - _money(r["Credits"]), r["Name"]))
    return dict(out)


def _ledger(rows) -> dict[str, int]:
    """Net debit per account over the whole file."""
    ledger: dict[str, int] = defaultdict(int)
    for r in rows:
        ledger[r["Account Name"]] += _money(r["Debits"]) - _money(r["Credits"])
    return {k: v for k, v in ledger.items() if v}


def _numbers(db, claim) -> tuple[str, str]:
    number = sql(db, "SELECT i.invoice_number FROM invoices i JOIN warranty_claims c "
                     "ON c.invoice_id = i.id WHERE c.id = ?", (claim,))[0][0]
    return number, f"{number}-W{claim}"


# ---------------------------------------------------------------------------


class TestTheWorkedExample:
    """373's case with a 2500 deductible, under each payer."""

    def test_someone_elses_plan(self, db):
        _, claim, invoice = _covered(db, "other")
        assert _invoice(db, invoice) == (2500, 54, 2554, [
            ("labor", "Warranty deductible, claim #1: labour", 1630),
            ("parts", "Warranty deductible, claim #1: parts", 870),
        ])
        assert _claim_lines(db, claim) == [("labor", 13370, 1630), ("parts", 7130, 870)]
        c = _claim(db, claim)
        assert (c["covered_cents"], c["tax_cents"], c["amount_claimed_cents"]) == (
            20500, 446, 20946)
        assert (c["deductible_cents"], c["deductible_tax_cents"]) == (2500, 54)
        assert "79-19" in c["deductible_tax_source"]
        # together: the repair's price and the tax on the entire parts charge (79-19)
        assert 2554 + c["amount_claimed_cents"] == 23500
        assert 54 + c["tax_cents"] == 500

    @pytest.mark.parametrize("payer, source", [("maker_with_bike", "03-8"),
                                               ("shop_contract", "64H.1.1")])
    def test_a_makers_warranty_and_the_shops_contract(self, db, payer, source):
        _, claim, invoice = _covered(db, payer)
        assert _invoice(db, invoice)[:3] == (2500, 54, 2554)
        c = _claim(db, claim)
        assert (c["covered_cents"], c["tax_cents"], c["amount_claimed_cents"]) == (
            20500, 0, 20500)
        assert c["deductible_tax_cents"] == 54
        assert source in c["deductible_tax_source"]

    def test_no_deductible_invoices_as_before_and_needs_no_rule(self, db):
        sql(db, "DELETE FROM tax_deductible_rules")
        _, claim, invoice = _covered(db, "other", deductible=0)
        assert _invoice(db, invoice) == (0, 0, 0, [])
        assert _claim_lines(db, claim) == [("labor", 15000, 0), ("parts", 8000, 0)]
        c = _claim(db, claim)
        assert (c["covered_cents"], c["tax_cents"], c["amount_claimed_cents"],
                c["deductible_cents"], c["deductible_tax_source"]) == (
            23000, 500, 23500, 0, None)

    def test_the_customers_own_lines_keep_their_supplies_and_the_deductible_does_not(
            self, db):
        """376's job: 2.0 h and part rows 1 (2 x 4000) and 2 (1 x 2500); the
        claim covers 1.5 h and row 1. The customer owes 0.5 h (5000) and row 2
        (2500); 10 % supplies fall on those 7500 only (750), not on the
        deductible."""
        ok(db, "shop", "tax", "rule", "set", "--shop", 1, "--line-type", "misc",
           "--not-taxable", "--effective", "2026-01-01", "--valid-until", "2027-01-01",
           "--source-title", "The shop's own rule, for this test", "--checked-on",
           "2026-10-01")
        _, claim, invoice = _covered(db, hours=2.0, parts=((4000, 2), (2500, 1)),
                                     extra=("--supplies-pct", "0.1"))
        subtotal, tax, total, lines = _invoice(db, invoice)
        assert [(t, c) for t, _, c in lines] == [
            ("labor", 5000), ("parts", 2500), ("misc", 750), ("labor", 1630),
            ("parts", 870)]
        assert subtotal == 10750
        assert _claim(db, claim)["amount_claimed_cents"] == 20946

    def test_more_than_the_covered_work_is_capped_and_the_claim_asks_for_nothing(
            self, db, tmp_path):
        _, claim, invoice = _covered(db, deductible=30000)
        assert _invoice(db, invoice) == (23000, 500, 23500, [
            ("labor", "Warranty deductible, claim #1: labour", 15000),
            ("parts", "Warranty deductible, claim #1: parts", 8000),
        ])
        c = _claim(db, claim)
        assert (c["deductible_cents"], c["covered_cents"], c["tax_cents"],
                c["amount_claimed_cents"]) == (23000, 0, 0, 0)
        notes = sql(db, "SELECT notes FROM invoices WHERE id = ?", (invoice,))[0][0]
        assert "(capped at the covered work)" in notes
        packet = ok(db, "shop", "warranty", "claim", "packet", claim)
        assert "the claim asks for nothing" in packet
        _map(db, absorbed=False)
        number, claim_number = _numbers(db, claim)
        journals = _journals(_read(_export(db, tmp_path, "quickbooks-online")))
        assert set(journals) == {number}


class TestRefusals:
    def test_covering_needs_the_deductible_on_record(self, db):
        wo, wops = _work_order(db)
        warranty = _warranty(db, deductible=None)
        ok(db, "shop", "warranty", "claim", "open", "--warranty", warranty, "--wo", wo,
           "--description", "Front brake pulls left")
        out = refused(db, "shop", "warranty", "claim", "cover", 1, "--labour-hours", "1.5")
        assert (f"record it with `motodiag shop warranty update {warranty} "
                f"--deductible-cents N` (0 for none)") in _flat(out)
        assert sql(db, "SELECT COUNT(*) FROM warranty_claim_lines") == [(0,)]
        ok(db, "shop", "warranty", "claim", "cover", 1, "--none")

    def test_a_claim_covered_before_the_deductible_was_recorded_refuses_the_invoice(
            self, db):
        """A claim covered before migration 084 has a warranty with no deductible
        on record; the invoice names the command, and writes nothing."""
        wo, _, _ = _covered(db, invoice=False)
        sql(db, "UPDATE warranties SET deductible_cents = NULL")
        out = refused(db, "shop", "invoice", "generate", wo, "--hourly-rate", RATE)
        assert ("warranty claim #1's warranty does not record its deductible; record it "
                "with `motodiag shop warranty update 1 --deductible-cents N` (0 for "
                "none)") in _flat(out)
        assert sql(db, "SELECT COUNT(*) FROM invoices") == [(0,)]

    def test_a_deductible_with_no_reading_on_record_refuses_the_invoice(self, db):
        sql(db, "DELETE FROM tax_deductible_rules WHERE payer = 'other'")
        wo, _, _ = _covered(db, invoice=False)
        out = refused(db, "shop", "invoice", "generate", wo, "--hourly-rate", RATE)
        assert ("no US-MA rule on record for the tax on a deductible under someone "
                "else's plan or contract (record the shop's reading with `motodiag shop "
                "tax deductible-rule set --shop 1 --payer other`)") in _flat(out)
        assert sql(db, "SELECT COUNT(*) FROM invoices") == [(0,)]

    def test_a_reading_past_its_validity_refuses_the_invoice(self, db):
        sql(db, "UPDATE tax_deductible_rules SET valid_until = '2026-09-30'")
        wo, _, _ = _covered(db, invoice=False)
        out = refused(db, "shop", "invoice", "generate", wo, "--hourly-rate", RATE)
        assert "was valid until 2026-09-30 and must be re-checked" in _flat(out)

    def test_the_shops_own_reading_is_used(self, db):
        sql(db, "DELETE FROM tax_deductible_rules")
        ok(db, "shop", "tax", "deductible-rule", "set", "--shop", 1, "--payer", "other",
           "--effective", "2026-01-01", "--valid-until", "2027-01-01",
           "--source-title", "Our accountant's letter", "--checked-on", "2026-10-01",
           "--reading")
        _, claim, invoice = _covered(db)
        assert _invoice(db, invoice)[:3] == (2500, 54, 2554)
        assert "Our accountant's letter" in _claim(db, claim)["deductible_tax_source"]


class TestRegenerating:
    def test_a_regenerated_invoice_keeps_its_deductible(self, db):
        wo, claim, invoice = _covered(db)
        first = _invoice(db, invoice)
        ok(db, "shop", "invoice", "void", invoice)
        ok(db, "shop", "invoice", "generate", wo, "--hourly-rate", RATE)
        again = sql(db, "SELECT MAX(id) FROM invoices")[0][0]
        assert _invoice(db, again) == first
        assert _claim(db, claim)["amount_claimed_cents"] == 20946

    def test_a_changed_deductible_cannot_move_a_submitted_claim(self, db):
        wo, claim, invoice = _covered(db)
        ok(db, "shop", "warranty", "claim", "status", claim, "--to", "submitted")
        ok(db, "shop", "invoice", "void", invoice)
        ok(db, "shop", "warranty", "update", 1, "--deductible-cents", "5000")
        out = refused(db, "shop", "invoice", "generate", wo, "--hourly-rate", RATE)
        assert "is submitted at 20946 cents" in _flat(out)


class TestTheExport:
    def test_quickbooks_books_the_deductible_to_the_customer_and_the_rest_to_the_plan(
            self, db, tmp_path):
        _, claim, _ = _covered(db)
        _map(db, absorbed=False)
        number, claim_number = _numbers(db, claim)
        journals = _journals(_read(_export(db, tmp_path, "quickbooks-online")))
        assert journals[number] == [(AR, 2554, "Dana Rider"), ("Labor Income", -1630, ""),
                                    ("Parts Sales", -870, ""),
                                    ("Sales Tax Payable", -54, "")]
        assert journals[claim_number] == [(AR, 20946, PLAN), ("Labor Income", -13370, ""),
                                          ("Parts Sales", -7130, ""),
                                          ("Sales Tax Payable", -446, "")]
        for rows in journals.values():
            assert sum(amount for _, amount, _ in rows) == 0

    def test_income_and_tax_are_the_same_as_with_no_deductible(self, db, tmp_path):
        _covered(db)
        _map(db, absorbed=False)
        with_deductible = _ledger(_read(_export(db, tmp_path, "quickbooks-online")))

        other = new_db(tmp_path, "none.db")
        shop = seed_shop(other, "Harbor Moto")
        seed_customer(other, shop, "Dana Rider", "dana@example.com")
        seed_bike(other, "Honda", "CBR600RR", 2005, mileage=31200)
        ok(other, "shop", "tax", "jurisdiction", "set", "--shop", shop, "--code", "US-MA")
        _covered(other, deductible=0)
        _map(other, absorbed=False)
        without = _ledger(_read(_export(other, tmp_path, "quickbooks-online", "n.csv")))

        assert with_deductible == without == {
            AR: 23500, "Labor Income": -15000, "Parts Sales": -8000,
            "Sales Tax Payable": -500}

    def test_xero_carries_the_deductible_on_the_customers_invoice(self, db, tmp_path):
        _, claim, _ = _covered(db)
        _map(db, absorbed=False)
        number, claim_number = _numbers(db, claim)
        rows = _read(_export(db, tmp_path, "xero"))
        got = [(r["InvoiceNumber"], r["ContactName"], _money(r["UnitAmount"]),
                _money(r["TaxAmount"])) for r in rows]
        assert got == [(number, "Dana Rider", 1630, 0), (number, "Dana Rider", 870, 54),
                       (claim_number, PLAN, 13370, 0), (claim_number, PLAN, 7130, 446)]


class TestSettlements:
    """4A: a settlement bills only what the customer has not been charged."""

    def _settle(self, db, claim, to, how, approved=None):
        ok(db, "shop", "warranty", "claim", "status", claim, "--to", "submitted")
        args = ["--approved-cents", approved] if approved is not None else []
        ok(db, "shop", "warranty", "claim", "status", claim, "--to", to, *args)
        ok(db, "shop", "warranty", "claim", "settle", claim,
           "--bill-customer" if how == "billed" else "--absorb")

    def _customer_total(self, db) -> int:
        return sum(_cents(t) for (t,) in sql(
            db, "SELECT total FROM invoices WHERE status != 'cancelled'"))

    @pytest.mark.parametrize("to, approved, shortfall, lines, tax", [
        ("denied", None, 20946, [13370, 7130], 446),
        ("approved", 18000, 2946, [1880, 1003], 63),
    ])
    def test_the_shortfall_invoice_bills_only_the_claimed_work(
            self, db, to, approved, shortfall, lines, tax):
        _, claim, _ = _covered(db)
        self._settle(db, claim, to, "billed", approved)
        c = _claim(db, claim)
        assert c["shortfall_cents"] == shortfall
        sub, got_tax, total, got_lines = _invoice(db, c["shortfall_invoice_id"])
        assert [cents for _, _, cents in got_lines] == lines
        assert (sub + got_tax, got_tax) == (shortfall, tax)

    @pytest.mark.parametrize("to, approved", [("denied", None), ("approved", 18000)])
    @pytest.mark.parametrize("how", ["billed", "absorbed"])
    def test_the_customer_never_pays_the_deductible_twice(self, db, to, approved, how):
        _, claim, _ = _covered(db)
        self._settle(db, claim, to, how, approved)
        paid_by_customer = self._customer_total(db)
        # the repair with no warranty is 23500; D11's rounding cent at most
        assert paid_by_customer <= 23500 + 1
        if how == "billed" and to == "denied":
            assert paid_by_customer == 23500
        if how == "absorbed":
            assert paid_by_customer == 2554

    @pytest.mark.parametrize("to, approved, credit, shortfall_rows", [
        ("denied", None, [("Labor Income", 13370), ("Parts Sales", 7130),
                          ("Sales Tax Payable", 446), (AR, -20946)], 20946),
        ("approved", 18000, [("Labor Income", 1880), ("Parts Sales", 1003),
                             ("Sales Tax Payable", 63), (AR, -2946)], 2946),
    ])
    def test_quickbooks_billed(self, db, tmp_path, to, approved, credit, shortfall_rows):
        _, claim, _ = _covered(db)
        self._settle(db, claim, to, "billed", approved)
        _map(db, absorbed=False)
        _, claim_number = _numbers(db, claim)
        journals = _journals(_read(_export(db, tmp_path, "quickbooks-online")))
        assert [(a, v) for a, v, _ in journals[f"{claim_number}-CR"]] == credit
        shortfall_number = sql(db, "SELECT invoice_number FROM invoices WHERE "
                                   "shortfall_claim_id IS NOT NULL")[0][0]
        assert journals[shortfall_number][0] == (AR, shortfall_rows, "Dana Rider")
        for rows in journals.values():
            assert sum(amount for _, amount, _ in rows) == 0

    @pytest.mark.parametrize("to, approved, shortfall", [("denied", None, 20946),
                                                         ("approved", 18000, 2946)])
    def test_quickbooks_absorbed(self, db, tmp_path, to, approved, shortfall):
        _, claim, _ = _covered(db)
        self._settle(db, claim, to, "absorbed", approved)
        _map(db)
        _, claim_number = _numbers(db, claim)
        journals = _journals(_read(_export(db, tmp_path, "quickbooks-online")))
        assert [(a, v) for a, v, _ in journals[f"{claim_number}-CR"]] == [
            ("Warranty Write-offs", shortfall), (AR, -shortfall)]

    @pytest.mark.parametrize("to, approved, how, amounts", [
        ("denied", None, "billed", [-13370, -7576]),
        ("approved", 18000, "billed", [-1880, -1066]),
        ("denied", None, "absorbed", [-20946]),
        ("approved", 18000, "absorbed", [-2946]),
    ])
    def test_xero_credit_notes(self, db, tmp_path, to, approved, how, amounts):
        _, claim, _ = _covered(db)
        self._settle(db, claim, to, how, approved)
        _map(db)
        out = _export(db, tmp_path, "xero")
        notes = _read(out.with_name(f"{out.stem}_credit_notes{out.suffix}"))
        assert [_money(r["UnitAmount"]) for r in notes] == amounts


class TestWhatTheShopSees:
    def test_warranty_add_update_and_list(self, db):
        out = ok(db, "shop", "warranty", "add", "--bike", 1, "--coverage", "extended",
                 "--provider", PLAN)
        assert "Recorded warranty #1" in out
        listed = _flat(ok(db, "shop", "warranty", "list", "--bike", 1))
        assert "not recorded" in listed
        out = ok(db, "shop", "warranty", "update", 1, "--deductible-cents", "2500")
        assert "deductible of $25.00 on each covered repair" in _flat(out)
        assert "$25.00" in ok(db, "shop", "warranty", "list", "--bike", 1)
        assert sql(db, "SELECT deductible_cents FROM warranties") == [(2500,)]
        refused(db, "shop", "warranty", "update", 1, "--deductible-cents", "-1")

    def test_the_packet_before_and_after_the_invoice(self, db):
        wo, claim, _ = _covered(db, invoice=False)
        before = ok(db, "shop", "warranty", "claim", "packet", claim)
        assert "  Deductible: $25.00 per covered repair" in before
        assert "  Deductible: applied when the invoice is generated" in before
        ok(db, "shop", "invoice", "generate", wo, "--hourly-rate", RATE)
        after = ok(db, "shop", "warranty", "claim", "packet", claim)
        assert ("    - labour 1.50 h: $133.70 (the deductible's share, $16.30, charged "
                "to the customer)") in after
        assert "  Covered work: $230.00" in after
        assert ("  Deductible (charged to the customer): $25.00, tax on it $0.54 "
                "(Massachusetts DOR, Letter Rulings 79-19 and 85-8") in after
        assert "  Claimed work: $205.00" in after
        assert "  Tax on the claim: $4.46" in after
        assert "  Amount claimed: $209.46" in after

    def test_claim_show(self, db):
        _, claim, _ = _covered(db)
        out = ok(db, "shop", "warranty", "claim", "show", claim)
        assert "deductible_cents: 2500" in out
        assert "deductible_tax_cents: 54" in out


class TestTheReadings:
    def test_the_three_massachusetts_readings_and_what_they_leave_open(self, db):
        rows = dict(sql(db, "SELECT payer, notes FROM tax_deductible_rules"))
        assert set(rows) == {"other", "maker_with_bike", "shop_contract"}
        assert sql(db, "SELECT DISTINCT deductible_tax, basis, provenance, valid_until "
                       "FROM tax_deductible_rules") == [
            ("taxable_share", "reading", "regulation", "2027-10-07")]
        for notes in rows.values():
            assert "confirmed by the shop's accountant" in notes
        assert "no additional consideration from the retail customer" in rows[
            "maker_with_bike"]
        assert '"separate charge"' in rows["shop_contract"]
        assert "LR 80-17" in rows["shop_contract"]
        assert "deduct their cost from gross sales" in rows["shop_contract"]
        assert "none names a deductible" in rows["other"]

    def test_status_lists_them(self, db):
        out = _flat(ok(db, "shop", "tax", "status", "--shop", 1))
        assert ("A deductible under someone else's plan or contract: its taxable share "
                "is taxed to the customer, must be re-checked by 2027-10-07.") in out

    def test_status_names_a_payer_with_no_reading(self, db):
        sql(db, "DELETE FROM tax_deductible_rules WHERE payer = 'shop_contract'")
        out = _flat(ok(db, "shop", "tax", "status", "--shop", 1))
        assert ("A deductible under a service contract this shop sold: no rule on "
                "record; an invoice charging one is refused until one is recorded.") in out

    def test_confirm_carries_them_forward_with_their_notes(self, db):
        out = _flat(ok(db, "shop", "tax", "confirm", "--jurisdiction", "US-MA",
                       "--checked-on", "2027-09-01", "--source-url", "https://example.org"))
        assert "3 deductible rule(s)" in out
        rows = sql(db, "SELECT payer, valid_until, notes FROM tax_deductible_rules "
                       "WHERE checked_on = '2027-09-01'")
        assert len(rows) == 3
        for _, until, notes in rows:
            assert until == "2028-09-01"
            assert "re-checked at https://example.org" in notes
            assert "confirmed by the shop's accountant" in notes


class TestMigration084:
    def test_only_new_columns_and_the_new_table_and_no_row_moves(self, tmp_path):
        from motodiag.core.migrations import (
            apply_migration, get_migration_by_version, rollback_to_version,
        )

        path = new_db(tmp_path, "m084.db")
        rollback_to_version(83, path)
        shop = seed_shop(path, "Harbor Moto")
        customer = seed_customer(path, shop, "Dana Rider")
        seed_bike(path)
        sql(path, "INSERT INTO work_orders (shop_id, vehicle_id, customer_id, title) "
                  "VALUES (1, 1, ?, 'job')", (customer,))
        sql(path, "INSERT INTO warranties (vehicle_id, coverage_type, repair_payer) "
                  "VALUES (1, 'extended', 'other')")
        sql(path, "INSERT INTO warranty_claims (warranty_id, work_order_id, description, "
                  "opened_at) VALUES (1, 1, 'x', '2026-09-01T12:00:00.000+00:00')")
        sql(path, "INSERT INTO warranty_claim_lines (claim_id, line_type, quantity, "
                  "description) VALUES (1, 'labor', 1.5, 'labour 1.50 h')")
        tables = ("warranties", "warranty_claims", "warranty_claim_lines")
        rows = {t: sql(path, f"SELECT * FROM {t} ORDER BY rowid") for t in tables}
        schema = lambda: {name: text for name, text in sql(  # noqa: E731
            path, "SELECT name, sql FROM sqlite_master")}
        before = schema()

        apply_migration(get_migration_by_version(84), path)
        after = schema()
        assert {k for k in before if before[k] != after.get(k)} == set(tables)
        assert set(after) - set(before) == {"tax_deductible_rules",
                                            "idx_tax_deductible_rules_jurisdiction"}
        for t in tables:
            got = sql(path, f"SELECT * FROM {t} ORDER BY rowid")
            assert [r[:len(b)] for r, b in zip(got, rows[t])] == rows[t], t
            assert all(r[len(rows[t][0]):] == (None,) * (len(r) - len(rows[t][0]))
                       for r in got), t
        assert sql(path, "SELECT COUNT(*) FROM tax_deductible_rules") == [(3,)]
        assert sql(path, "PRAGMA foreign_key_check") == []

        rollback_to_version(83, path)
        assert schema() == before
        for t in tables:
            assert sql(path, f"SELECT * FROM {t} ORDER BY rowid") == rows[t]

    def test_the_new_checks(self, tmp_path):
        path = new_db(tmp_path, "c084.db")
        seed_bike(path)
        with pytest.raises(sqlite3.IntegrityError):
            sql(path, "INSERT INTO warranties (vehicle_id, coverage_type, "
                      "deductible_cents) VALUES (1, 'extended', -1)")
        with pytest.raises(sqlite3.IntegrityError):
            sql(path, "INSERT INTO tax_deductible_rules (jurisdiction_id, payer, "
                      "deductible_tax, basis, effective_from, valid_until, source_title, "
                      "checked_on, provenance) VALUES (1, 'other', 'untaxed', 'reading', "
                      "'2026-01-01', '2027-01-01', 'x', '2026-01-01', 'regulation')")
