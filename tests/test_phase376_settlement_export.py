"""Phase 376 (F190) — warranty claim settlements in the accounting export.

Row 373 exports a claim as owed by its provider. When the claim is denied
or paid short, `shop warranty claim settle` bills the customer for the
shortfall or records that the shop absorbs it; 376 books each settlement
against the claim's receivable, in both files (the operator's choice 1A):

- QuickBooks: a journal `<claim number>-CR` crediting the provider's A/R
  for the shortfall, against the income and tax the shortfall invoice
  re-bills (billed; the shortfall invoice's own journal follows) or the
  absorbed account (absorbed);
- Xero: a credit note `<claim number>-CR` to the provider in a file of its
  own, tax-inclusive (5A); a billed shortfall invoice in the invoices file.

The job is Phase 373's, worked at 10000 cents an hour in Massachusetts
(parts taxable at 6.25%, labour not): 2.0 h (20000), part row 1 2 x 4000,
part row 2 1 x 2500. The claim covers 1.5 h (15000) and part row 1 (8000),
tax 500 (owed by someone else's plan): **claimed 23500**. The customer's
invoice: 5000 + 2500, tax 156, 7656.

Approved at 20000, the shortfall is 3500: the shortfall invoice is pre-tax
23000 x 3500 / 23500 = 3426 (2234 labour + 1192 parts), customer tax 75,
total 3501; the claim's tax inside the shortfall is 74; D11's cent is +1.

Every test runs in New York on a fixed clock (Phase 370's frozen clock):
2026-10-15 12:00 EDT, or 2026-10-31 21:00 EDT (2026-11-01 01:00 UTC).
"""

from __future__ import annotations

import csv
import hashlib
import sqlite3
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from support.frozen_clock import frozen_datetime, set_zone
from support.phase274 import new_db, ok, refused, seed_bike, seed_customer, seed_shop, sql

ZONE = "America/New_York"
DAY = "2026-10-15"
NOON = datetime(2026, 10, 15, 16, 0, tzinfo=timezone.utc)          # 12:00 EDT
MONTH_END = datetime(2026, 11, 1, 1, 0, tzinfo=timezone.utc)       # 2026-10-31 21:00 EDT
RATE = "10000"
AR = "Accounts Receivable (A/R)"
PLAN = "Honda Protection Plan"

# The files `shop accounting export` wrote for this job with no settlement,
# measured on master at 23ff246, before Phase 376 (the phase log has the
# run): D4, an export with no settlements writes what it wrote before.
BEFORE_376_SHA256 = {
    "quickbooks-online": "81c1918fbcaa29b3f8c39cb987fdd97fcdd6601b246278107233719857bc63a3",
    "xero": "432cd338cf33123797e2b31c09d0f9ad8c7bacdeab794ec2151739a7a6bcd614",
}


@pytest.fixture
def clock(monkeypatch):
    """Freeze invoicing's and settling's clock, and the tax day, in New York;
    ``clock(instant)`` moves them. TZ is restored afterwards."""
    from motodiag.accounting import tax
    from motodiag.inventory import warranty_claims
    from motodiag.shop import invoicing

    set_zone(ZONE)

    def at(instant: datetime) -> None:
        frozen = frozen_datetime(instant)
        monkeypatch.setattr(invoicing, "datetime", frozen)
        monkeypatch.setattr(warranty_claims, "datetime", frozen)
        day = instant.astimezone().date()
        monkeypatch.setattr(tax, "today", lambda: day)

    at(NOON)
    yield at
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


# --- The job, as Phase 373's tests build it ---


def _work_order(db, parts=((4000, 2), (2500, 1))) -> tuple[int, list[int]]:
    customer = sql(db, "SELECT id FROM customers WHERE name = 'Dana Rider'")[0][0]
    sql(db, "INSERT INTO work_orders (shop_id, vehicle_id, customer_id, title, status, "
            "actual_hours, opened_at, completed_at) VALUES (1, 1, ?, 'Brakes', "
            "'completed', 2.0, '2026-10-15T13:00:00', '2026-10-15T15:00:00')", (customer,))
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


def _job(db, payer="other", labour_only=False) -> tuple[int, int]:
    """The covered job, invoiced: returns (claim, invoice)."""
    wo, wops = _work_order(db)
    ok(db, "shop", "warranty", "add", "--bike", 1, "--coverage", "extended",
       "--start", "2024-03-01", "--end", "2027-02-28", "--mileage-limit", "40000",
       "--provider", PLAN, "--payer", payer)
    warranty = sql(db, "SELECT MAX(id) FROM warranties")[0][0]
    ok(db, "shop", "warranty", "claim", "open", "--warranty", warranty, "--wo", wo,
       "--description", "Front brake pulls left")
    claim = sql(db, "SELECT MAX(id) FROM warranty_claims")[0][0]
    cover = ["--labour-hours", "1.5"] + ([] if labour_only else ["--part", wops[0]])
    ok(db, "shop", "warranty", "claim", "cover", claim, *cover)
    ok(db, "shop", "invoice", "generate", wo, "--hourly-rate", RATE)
    return claim, sql(db, "SELECT MAX(id) FROM invoices")[0][0]


def _settle(db, claim, to, how, approved=None):
    ok(db, "shop", "warranty", "claim", "status", claim, "--to", "submitted")
    args = ["--approved-cents", approved] if approved is not None else []
    ok(db, "shop", "warranty", "claim", "status", claim, "--to", to, *args)
    return ok(db, "shop", "warranty", "claim", "settle", claim,
              "--bill-customer" if how == "billed" else "--absorb")


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


def _export(db, tmp_path, target, start=DAY, end=DAY, name=None):
    path = tmp_path / (name or f"{target}.csv")
    out = ok(db, "shop", "accounting", "export", "--shop", "1", "--target", target,
             "--from", start, "--to", end, "--out", path)
    return out, path


def _cents(text: str) -> int:
    if not text:
        return 0
    sign = -1 if text.startswith("-") else 1
    whole, _, frac = text.lstrip("-").partition(".")
    return sign * (int(whole) * 100 + int((frac + "00")[:2]))


def _qbo_ledger(rows) -> dict[tuple[str, str], int]:
    """Net debit per (account, name) over the whole file."""
    ledger: dict[tuple[str, str], int] = defaultdict(int)
    for r in rows:
        ledger[(r["Account Name"], r["Name"])] += _cents(r["Debits"]) - _cents(r["Credits"])
    return {k: v for k, v in ledger.items() if v}


def _qbo_journals_balance(rows) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for r in rows:
        totals[r["Journal No."]] += _cents(r["Debits"]) - _cents(r["Credits"])
    return dict(totals)


def _numbers(db, claim) -> tuple[str, str]:
    claim_invoice = sql(db, "SELECT i.invoice_number FROM invoices i JOIN warranty_claims c "
                            "ON c.invoice_id = i.id WHERE c.id = ?", (claim,))[0][0]
    return f"{claim_invoice}-W{claim}", f"{claim_invoice}-W{claim}-CR"


def _shortfall_number(db) -> str:
    return sql(db, "SELECT invoice_number FROM invoices WHERE shortfall_claim_id "
                   "IS NOT NULL")[0][0]


# --- What each settlement books, in QuickBooks: the worked example ---

PAID_IN_FULL = {
    # the customer's invoice and the claim, before any settlement
    (AR, "Dana Rider"): 7656, (AR, PLAN): 23500,
    ("Labor Income", ""): -20000, ("Parts Sales", ""): -10500,
    ("Sales Tax Payable", ""): -656,
}


class TestQuickBooks:
    def _file(self, db, tmp_path, to, how, approved=None):
        claim, _ = _job(db)
        _settle(db, claim, to, how, approved)
        _map(db)
        out, path = _export(db, tmp_path, "quickbooks-online")
        return claim, out, _read(path)

    def test_part_approval_billed(self, db, tmp_path):
        claim, out, rows = self._file(db, tmp_path, "approved", "billed", 20000)
        _, credit = _numbers(db, claim)
        assert [(r["Account Name"], r["Debits"], r["Credits"], r["Name"])
                for r in rows if r["Journal No."] == credit] == [
            ("Labor Income", "22.34", "", ""), ("Parts Sales", "11.92", "", ""),
            ("Sales Tax Payable", "0.74", "", ""), (AR, "", "35.00", PLAN)]
        assert [(r["Account Name"], r["Debits"], r["Credits"], r["Name"])
                for r in rows if r["Journal No."] == _shortfall_number(db)] == [
            (AR, "35.01", "", "Dana Rider"), ("Labor Income", "", "22.34", ""),
            ("Parts Sales", "", "11.92", ""), ("Sales Tax Payable", "", "0.75", "")]
        # revenue as paid in full; tax payable moves by D11's cent
        assert _qbo_ledger(rows) == {**PAID_IN_FULL, (AR, PLAN): 20000,
                                     (AR, "Dana Rider"): 7656 + 3501,
                                     ("Sales Tax Payable", ""): -657}
        assert set(_qbo_journals_balance(rows).values()) == {0}

    def test_part_approval_absorbed(self, db, tmp_path):
        claim, out, rows = self._file(db, tmp_path, "approved", "absorbed", 20000)
        _, credit = _numbers(db, claim)
        assert [(r["Account Name"], r["Debits"], r["Credits"], r["Name"])
                for r in rows if r["Journal No."] == credit] == [
            ("Warranty Write-offs", "35.00", "", ""), (AR, "", "35.00", PLAN)]
        assert _qbo_ledger(rows) == {**PAID_IN_FULL, (AR, PLAN): 20000,
                                     ("Warranty Write-offs", ""): 3500}
        assert set(_qbo_journals_balance(rows).values()) == {0}

    def test_denial_billed(self, db, tmp_path):
        _, _, rows = self._file(db, tmp_path, "denied", "billed")
        assert _qbo_ledger(rows) == {
            **{k: v for k, v in PAID_IN_FULL.items() if k != (AR, PLAN)},
            (AR, "Dana Rider"): 7656 + 23500}
        assert set(_qbo_journals_balance(rows).values()) == {0}

    def test_denial_absorbed(self, db, tmp_path):
        _, _, rows = self._file(db, tmp_path, "denied", "absorbed")
        assert _qbo_ledger(rows) == {
            **{k: v for k, v in PAID_IN_FULL.items() if k != (AR, PLAN)},
            ("Warranty Write-offs", ""): 23500}
        assert set(_qbo_journals_balance(rows).values()) == {0}

    def test_the_cli_says_what_the_file_holds_and_how_to_apply_the_credit(
            self, db, tmp_path):
        _, out, rows = self._file(db, tmp_path, "approved", "billed", 20000)
        text = " ".join(out.split())
        assert "Wrote 2 invoice(s) and 1 warranty claim(s) owed by their providers, " \
               "and 1 warranty claim settlement(s):" in text
        assert f"quickbooks-online.csv: journal entries, {len(rows)} row(s)" in text
        assert "Receive payment" in text and "the -CR journal under Credits" in text


# --- In Xero ---


def _xero_by_number(rows, amount_column="UnitAmount"):
    by: dict[str, list[tuple]] = defaultdict(list)
    for r in rows:
        by[r["InvoiceNumber"]].append((r["ContactName"], r["AccountCode"], r[amount_column],
                                       r.get("TaxAmount", "")))
    return dict(by)


class TestXero:
    def _files(self, db, tmp_path, to, how, approved=None):
        claim, _ = _job(db)
        _settle(db, claim, to, how, approved)
        _map(db)
        out, path = _export(db, tmp_path, "xero")
        notes = path.with_name("xero_credit_notes.csv")
        return claim, out, _read(path), _read(notes)

    def test_part_approval_billed(self, db, tmp_path):
        claim, out, invoices, notes = self._files(db, tmp_path, "approved", "billed", 20000)
        own, credit = _numbers(db, claim)
        assert _xero_by_number(notes) == {credit: [
            (PLAN, "200", "-22.34", ""), (PLAN, "210", "-12.66", "")]}
        assert {r["Reference"] for r in notes} == {own}
        assert {r["InvoiceDate"] for r in notes} == {"10/15/2026"}
        assert _xero_by_number(invoices)[_shortfall_number(db)] == [
            ("Dana Rider", "200", "22.34", "0.00"), ("Dana Rider", "210", "11.92", "0.75")]
        # balance: the credit note is the shortfall; the shortfall invoice is its total
        assert sum(_cents(r["UnitAmount"]) for r in notes) == -3500
        billed = [r for r in invoices if r["InvoiceNumber"] == _shortfall_number(db)]
        assert sum(_cents(r["UnitAmount"]) + _cents(r["TaxAmount"]) for r in billed) == 3501
        assert "Credit note " + credit + ": credits 35.00; Xero should show tax of 0.74" \
            in " ".join(out.split())

    def test_part_approval_absorbed(self, db, tmp_path):
        claim, out, invoices, notes = self._files(db, tmp_path, "approved", "absorbed",
                                                  20000)
        _, credit = _numbers(db, claim)
        assert _xero_by_number(notes) == {credit: [(PLAN, "690", "-35.00", "")]}
        assert [r["TaxType"] for r in notes] == ["Tax Exempt"]
        assert "Xero should show tax of 0.00 (absorbed" in " ".join(out.split())

    def test_denial_billed_counts_no_revenue_twice(self, db, tmp_path):
        claim, _, invoices, notes = self._files(db, tmp_path, "denied", "billed")
        own, credit = _numbers(db, claim)
        assert _xero_by_number(notes) == {credit: [
            (PLAN, "200", "-150.00", ""), (PLAN, "210", "-85.00", "")]}
        # per account: what the invoices file books, less what the credit note
        # takes back (its tax inside: 0 on labour, 500 on parts) = paid in full
        income = defaultdict(int)
        for r in invoices:
            income[r["AccountCode"]] += round(_cents(r["UnitAmount"]) * float(r["Quantity"]))
        income["200"] += -15000
        income["210"] += -8000
        assert dict(income) == {"200": 20000, "210": 10500}

    def test_denial_absorbed(self, db, tmp_path):
        claim, _, invoices, notes = self._files(db, tmp_path, "denied", "absorbed")
        _, credit = _numbers(db, claim)
        assert _xero_by_number(notes) == {credit: [(PLAN, "690", "-235.00", "")]}
        assert _shortfall_number_absent(db)

    def test_the_credit_note_columns_are_the_pages(self, db, tmp_path):
        from motodiag.accounting.export import XERO_CREDIT_NOTE_COLUMNS

        self._files(db, tmp_path, "denied", "absorbed")
        header = (tmp_path / "xero_credit_notes.csv").read_text().splitlines()[0]
        assert header.split(",") == list(XERO_CREDIT_NOTE_COLUMNS)
        assert "TaxAmount" not in header  # 5A: tax-inclusive, no tax amount


def _shortfall_number_absent(db) -> bool:
    return sql(db, "SELECT COUNT(*) FROM invoices WHERE shortfall_claim_id "
                   "IS NOT NULL") == [(0,)]


# --- Which export carries a settlement ---


class TestWhichExport:
    def test_settled_at_21_00_edt_on_the_months_last_day_is_that_months(
            self, db, tmp_path, clock):
        claim, _ = _job(db)
        _map(db)
        _export(db, tmp_path, "quickbooks-online", name="claim.csv")
        clock(MONTH_END)
        _settle(db, claim, "approved", "billed", 20000)
        settled_at = sql(db, "SELECT settled_at FROM warranty_claims WHERE id = ?",
                         (claim,))[0][0]
        assert settled_at.startswith("2026-11-01T01:00:00")  # stored UTC
        november = refused(db, "shop", "accounting", "export", "--shop", "1", "--target",
                           "quickbooks-online", "--from", "2026-11-01", "--to",
                           "2026-11-30", "--out", tmp_path / "nov.csv")
        assert "no invoices to export" in november
        out, path = _export(db, tmp_path, "quickbooks-online", "2026-10-01", "2026-10-31",
                            name="oct.csv")
        rows = _read(path)
        _, credit = _numbers(db, claim)
        assert {r["Journal Date"] for r in rows if r["Journal No."] == credit} == {
            "10/31/2026"}
        # F194: the shortfall invoice is numbered with the shop's day, not UTC's
        assert _shortfall_number(db) == f"INV-1-1-20261031-S{claim}"

    def test_once_per_target(self, db, tmp_path):
        claim, _ = _job(db)
        _settle(db, claim, "approved", "absorbed", 20000)
        _map(db)
        _export(db, tmp_path, "quickbooks-online", name="first.csv")
        again = refused(db, "shop", "accounting", "export", "--shop", "1", "--target",
                        "quickbooks-online", "--from", DAY, "--to", DAY, "--out",
                        tmp_path / "second.csv")
        assert "were exported before" in again
        out, path = _export(db, tmp_path, "xero")
        assert _read(path.with_name("xero_credit_notes.csv"))
        assert sql(db, "SELECT e.target FROM accounting_export_settlements s JOIN "
                       "accounting_exports e ON e.id = s.export_id ORDER BY e.id") == [
            ("quickbooks_online",), ("xero",)]

    def test_a_range_with_settlements_and_no_invoices_exports(self, db, tmp_path,
                                                              clock):
        claim, _ = _job(db)
        _map(db)
        _export(db, tmp_path, "quickbooks-online", name="q-claim.csv")
        _export(db, tmp_path, "xero", name="x-claim.csv")
        clock(datetime(2026, 10, 20, 16, 0, tzinfo=timezone.utc))
        _settle(db, claim, "denied", "absorbed")
        out, path = _export(db, tmp_path, "quickbooks-online", "2026-10-20", "2026-10-20")
        _, credit = _numbers(db, claim)
        assert {r["Journal No."] for r in _read(path)} == {credit}
        assert "Wrote 0 invoice(s), and 1 warranty claim settlement(s)" in " ".join(
            out.split())
        out, path = _export(db, tmp_path, "xero", "2026-10-20", "2026-10-20")
        assert not path.exists()  # no invoice rows: only the credit notes file
        assert _read(path.with_name("xero_credit_notes.csv"))
        assert sql(db, "SELECT invoice_count, settlement_count FROM accounting_exports "
                       "ORDER BY id DESC LIMIT 2") == [(0, 1), (0, 1)]

    def test_a_settlement_whose_claim_was_never_exported_is_refused(self, db, tmp_path,
                                                                    clock):
        claim, _ = _job(db)
        clock(datetime(2026, 10, 20, 16, 0, tzinfo=timezone.utc))
        _settle(db, claim, "denied", "absorbed")
        _map(db)
        out = refused(db, "shop", "accounting", "export", "--shop", "1", "--target",
                      "xero", "--from", "2026-10-20", "--to", "2026-10-20", "--out",
                      tmp_path / "x.csv")
        own, _ = _numbers(db, claim)
        assert (f"the claim was never exported to xero; export its invoice "
                f"{own.rsplit('-W', 1)[0]} first (issued 2026-10-15)") in " ".join(out.split())
        assert not list(tmp_path.glob("x*.csv"))

    def test_an_export_with_no_settlements_writes_what_it_wrote_before(self, db,
                                                                       tmp_path):
        _job(db)
        _map(db, absorbed=False)
        for target, digest in BEFORE_376_SHA256.items():
            out, path = _export(db, tmp_path, target)
            assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, target
            assert "settlement" not in out
            assert not path.with_name(f"{path.stem}_credit_notes.csv").exists()


# --- Refusals, and the tax readings ---


class TestRefusalsAndTax:
    def test_an_absorbed_settlement_needs_the_absorbed_account(self, db, tmp_path):
        claim, _ = _job(db)
        _settle(db, claim, "denied", "absorbed")
        _map(db, absorbed=False)
        for target in ("quickbooks-online", "xero"):
            out = refused(db, "shop", "accounting", "export", "--shop", "1", "--target",
                          target, "--from", DAY, "--to", DAY, "--out",
                          tmp_path / f"{target}.csv")
            assert "--kind absorbed --account NAME" in " ".join(out.split()), target
            assert not list(tmp_path.glob(f"{target}*.csv"))

    def test_a_shortfall_invoice_out_of_step_with_its_claim_is_refused(self, db, tmp_path):
        """The claim's tax inside the shortfall is the shortfall less the shortfall
        invoice's lines; a line raised by a cent leaves it at -1, and both files
        refuse rather than book a credit that does not balance."""
        claim, _ = _job(db)
        _settle(db, claim, "approved", "billed", 23400)  # shortfall 100: pre-tax 98, tax 2
        sql(db, "UPDATE invoice_line_items SET line_total = line_total + 0.03 WHERE "
                "id = (SELECT MIN(id) FROM invoice_line_items WHERE invoice_id = "
                "(SELECT shortfall_invoice_id FROM warranty_claims WHERE id = ?))", (claim,))
        _map(db)
        for target in ("quickbooks-online", "xero"):
            out = refused(db, "shop", "accounting", "export", "--shop", "1", "--target",
                          target, "--from", DAY, "--to", DAY, "--out",
                          tmp_path / f"{target}.csv")
            assert f"claim #{claim}'s settlement does not balance" in out, target
            assert not list(tmp_path.glob(f"{target}*.csv"))

    def test_an_absorbed_taxed_claim_needs_a_reading_on_record(self, db, tmp_path):
        claim, _ = _job(db)
        _settle(db, claim, "denied", "absorbed")
        _map(db)
        sql(db, "DELETE FROM tax_settlement_rules")
        out = refused(db, "shop", "accounting", "export", "--shop", "1", "--target",
                      "quickbooks-online", "--from", DAY, "--to", DAY, "--out",
                      tmp_path / "q.csv")
        assert "motodiag shop tax settlement-rule set --shop 1" in " ".join(out.split())
        ok(db, "shop", "tax", "settlement-rule", "set", "--shop", "1", "--effective",
           "2026-01-01", "--valid-until", "2027-01-01", "--source-title",
           "the shop's accountant", "--checked-on", DAY, "--reading")
        out, _ = _export(db, tmp_path, "quickbooks-online")
        assert "the 5.00 of tax charged on the claim stays owed (the shop's accountant" \
            in " ".join(out.split())

    def test_the_massachusetts_reading_is_named(self, db, tmp_path):
        claim, _ = _job(db)
        _settle(db, claim, "approved", "absorbed", 20000)
        _map(db)
        out, _ = _export(db, tmp_path, "quickbooks-online")
        assert "stays owed (Massachusetts DOR, TIR 00-3" in " ".join(out.split())
        assert "F195" not in out

    def test_an_untaxed_absorbed_claim_with_parts_names_f195(self, db, tmp_path):
        claim, _ = _job(db, payer="maker_with_bike")
        assert sql(db, "SELECT tax_cents FROM warranty_claims WHERE id = ?",
                   (claim,)) == [(0,)]
        _settle(db, claim, "denied", "absorbed")
        _map(db)
        out, _ = _export(db, tmp_path, "quickbooks-online")
        assert "tax on the parts' cost may be due (finding F195)" in " ".join(out.split())

    def test_a_labour_only_absorbed_claim_does_not(self, db, tmp_path):
        claim, _ = _job(db, payer="maker_with_bike", labour_only=True)
        _settle(db, claim, "denied", "absorbed")
        _map(db)
        out, _ = _export(db, tmp_path, "quickbooks-online")
        assert "F195" not in out

    def test_status_and_confirm_carry_the_settlement_rule(self, db, monkeypatch):
        from motodiag.accounting import tax

        text = " ".join(ok(db, "shop", "tax", "status", "--shop", "1").split())
        assert ("A warranty shortfall the shop absorbs: the tax charged on the claim "
                "stays owed, must be re-checked by 2027-10-07") in text
        monkeypatch.setattr(tax, "today", lambda: date(2027, 10, 8))
        sql(db, "UPDATE tax_rates SET valid_until = '2028-12-31'")
        sql(db, "UPDATE tax_line_rules SET valid_until = '2028-12-31'")
        sql(db, "UPDATE tax_warranty_rules SET valid_until = '2028-12-31'")
        out = refused(db, "shop", "tax", "status", "--shop", "1")
        assert "a warranty shortfall the shop absorbs was valid until 2027-10-07" in " ".join(
            out.split())
        out = ok(db, "shop", "tax", "confirm", "--jurisdiction", "US-MA", "--checked-on",
                 "2027-10-08", "--source-url", "https://www.mass.gov/")
        assert "1 settlement rule(s)" in out
        ok(db, "shop", "tax", "status", "--shop", "1")


# --- The record ---


class TestTheRecord:
    def test_each_file_is_recorded_with_its_hash(self, db, tmp_path):
        claim, _ = _job(db)
        _settle(db, claim, "approved", "billed", 20000)
        _map(db)
        _, path = _export(db, tmp_path, "xero")
        notes = path.with_name("xero_credit_notes.csv")
        recorded = sql(db, "SELECT holds, file_name, file_sha256, row_count FROM "
                           "accounting_export_files ORDER BY holds")
        assert recorded == [
            ("credit_notes", str(notes), hashlib.sha256(notes.read_bytes()).hexdigest(), 2),
            ("invoices", str(path), hashlib.sha256(path.read_bytes()).hexdigest(),
             len(_read(path)))]
        assert sql(db, "SELECT file_name, invoice_count, settlement_count FROM "
                       "accounting_exports") == [(str(path), 2, 1)]
        from motodiag.accounting.export import list_exports

        [export] = list_exports(1, db_path=db)
        assert [f["file_name"] for f in export["files"]] == [str(path), str(notes)]
        assert "Settlements" in ok(db, "shop", "accounting", "exports", "--shop", "1")

    def test_f194_an_evening_invoice_carries_the_shops_day(self, db, clock):
        clock(MONTH_END)
        _job(db)
        assert sql(db, "SELECT invoice_number FROM invoices") == [("INV-1-1-20261031",)]


# --- Migration 083 ---


class TestMigration083:
    def test_only_the_two_rebuilt_tables_change_and_no_row_moves(self, tmp_path):
        from motodiag.core.migrations import (
            apply_migration, get_migration_by_version, rollback_to_version,
        )

        path = new_db(tmp_path, "m083.db")
        rollback_to_version(82, path)
        shop = seed_shop(path, "Harbor Moto")
        customer = seed_customer(path, shop, "Dana Rider")
        seed_bike(path)
        sql(path, "INSERT INTO work_orders (shop_id, vehicle_id, customer_id, title) "
                  "VALUES (1, 1, ?, 'job')", (customer,))
        sql(path, "INSERT INTO invoices (customer_id, invoice_number, total, "
                  "work_order_id) VALUES (?, 'INV-PLANT', 12.5, 1)", (customer,))
        sql(path, "INSERT INTO warranties (vehicle_id, coverage_type, start_date, "
                  "end_date) VALUES (1, 'extended', '2024-01-01', '2027-01-01')")
        sql(path, "INSERT INTO warranty_claims (warranty_id, work_order_id, description, "
                  "opened_at) VALUES (1, 1, 'x', '2026-09-01T12:00:00.000+00:00')")
        sql(path, "INSERT INTO accounting_accounts (shop_id, target, kind, account) "
                  "VALUES (1, 'xero', 'labor', '200')")
        sql(path, "INSERT INTO accounting_exports (shop_id, target, period_from, "
                  "period_to, file_name, file_sha256, invoice_count, exported_at) "
                  "VALUES (1, 'xero', '2026-09-01', '2026-09-30', 'x.csv', 'abc', 1, 'now')")
        sql(path, "INSERT INTO accounting_export_invoices VALUES (1, 1)")
        sql(path, "INSERT INTO accounting_export_claims VALUES (1, 1)")
        tables = ("accounting_accounts", "accounting_exports",
                  "accounting_export_invoices", "accounting_export_claims")
        rows = {t: sql(path, f"SELECT * FROM {t} ORDER BY rowid") for t in tables}
        schema = lambda: {name: text for name, text in sql(  # noqa: E731
            path, "SELECT name, sql FROM sqlite_master")}
        before = schema()

        # 083 alone: what a later migration adds is not 083's change (Phase 375).
        apply_migration(get_migration_by_version(83), path)
        after = schema()
        rebuilt = {"accounting_accounts", "accounting_exports"}
        new = {"accounting_export_files", "accounting_export_settlements",
               "idx_accounting_export_settlements_claim", "tax_settlement_rules",
               "idx_tax_settlement_rules_jurisdiction",
               "sqlite_autoindex_accounting_export_files_1",
               "sqlite_autoindex_accounting_export_settlements_1"}
        assert {k for k in before if before[k] != after.get(k)} == rebuilt
        assert set(after) - set(before) == new
        assert "'absorbed'" in after["accounting_accounts"]
        assert "settlement_count" in after["accounting_exports"]
        for t in tables:
            got = sql(path, f"SELECT * FROM {t} ORDER BY rowid")
            assert [r[:len(b)] for r, b in zip(got, rows[t])] == rows[t], t
        assert sql(path, "SELECT settlement_count FROM accounting_exports") == [(0,)]
        assert sql(path, "PRAGMA foreign_key_check") == []
        assert sql(path, "SELECT absorbed_tax, basis, provenance, valid_until FROM "
                         "tax_settlement_rules") == [
            ("stays_owed", "reading", "regulation", "2027-10-07")]
        # the children's foreign keys still reach the rebuilt parent: with the
        # pragma on (as the app's connection sets it), deleting it cascades
        from motodiag.core.database import get_connection

        with get_connection(path) as conn:
            conn.execute("DELETE FROM accounting_exports")
        assert sql(path, "SELECT COUNT(*) FROM accounting_export_invoices") == [(0,)]
        assert sql(path, "SELECT COUNT(*) FROM accounting_export_claims") == [(0,)]

    def test_the_new_checks(self, tmp_path):
        path = new_db(tmp_path, "c083.db")
        seed_shop(path, "S")
        with pytest.raises(sqlite3.IntegrityError):
            sql(path, "INSERT INTO accounting_exports (shop_id, target, period_from, "
                      "period_to, file_name, file_sha256, invoice_count, exported_at, "
                      "settlement_count) VALUES (1, 'xero', 'a', 'b', 'x', 'h', 0, 'n', 0)")
        sql(path, "INSERT INTO accounting_exports (shop_id, target, period_from, "
                  "period_to, file_name, file_sha256, invoice_count, exported_at, "
                  "settlement_count) VALUES (1, 'xero', 'a', 'b', 'x', 'h', 0, 'n', 1)")
        sql(path, "INSERT INTO accounting_accounts (shop_id, target, kind, account) "
                  "VALUES (1, 'xero', 'absorbed', '690')")
        with pytest.raises(sqlite3.IntegrityError):
            sql(path, "INSERT INTO tax_settlement_rules (jurisdiction_id, settlement, "
                      "absorbed_tax, basis, effective_from, valid_until, source_title, "
                      "checked_on, provenance) SELECT id, 'absorb', 'reversed', 'reading', "
                      "'2026-01-01', '2027-01-01', 's', '2026-01-01', 'regulation' "
                      "FROM tax_jurisdictions WHERE code = 'US-MA'")

    def test_the_rollback(self, tmp_path):
        from motodiag.core.migrations import rollback_to_version

        path = new_db(tmp_path, "r083.db")
        seed_shop(path, "S")
        sql(path, "INSERT INTO accounting_accounts (shop_id, target, kind, account) "
                  "VALUES (1, 'xero', 'labor', '200'), (1, 'xero', 'absorbed', '690')")
        rollback_to_version(82, path)
        assert sql(path, "SELECT kind FROM accounting_accounts") == [("labor",)]
        assert sql(path, "SELECT name FROM sqlite_master WHERE name IN "
                         "('tax_settlement_rules', 'accounting_export_files', "
                         "'accounting_export_settlements')") == []
        assert sql(path, "PRAGMA foreign_key_check") == []
