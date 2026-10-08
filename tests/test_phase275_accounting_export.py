"""Phase 275 — rows 277 and 278: the QuickBooks Online and Xero export files.

Driven through `motodiag shop accounting …`. The column lists are pinned
against the vendor pages as quoted in the phase folder's
`275_format_sources.md`; neither file has been tried in a real QuickBooks
or Xero company.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from pathlib import Path

import pytest

from motodiag.accounting import export as acct_export
from motodiag.core.timestamps import local_day
from support.phase275 import new_db, ok, refused, seed_booking_shop, sql
from support.tax_on_record import record_tax

REPO = Path(__file__).resolve().parent.parent


def _sources_text() -> str:
    found = sorted(REPO.glob("docs/phases/*/275_format_sources.md"))
    assert len(found) == 1, found
    return found[0].read_text()


def _seed_invoice(db_path, s, number, issued, lines, tax_cents, status="sent",
                  customer=None, shop=None, total_cents=None, currency="USD"):
    """An invoice on its own work order; ``lines`` are (kind, description, qty, unit_cents)."""
    customer = customer or s["dana"]
    bike = s["bike1"] if customer == s["dana"] else s["bike2"]
    sql(db_path, "INSERT INTO work_orders (shop_id, vehicle_id, customer_id, title, status) "
                 "VALUES (?, ?, ?, 'Job', 'completed')", (shop or s["shop"], bike, customer))
    wo = sql(db_path, "SELECT MAX(id) FROM work_orders")[0][0]
    line_cents = [round(q * u) for _, _, q, u in lines]
    subtotal = sum(line_cents)
    total = subtotal + tax_cents if total_cents is None else total_cents
    sql(db_path, "INSERT INTO invoices (customer_id, invoice_number, status, subtotal, "
                 "tax_amount, total, currency, issued_at, work_order_id) "
                 "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (customer, number, status, subtotal / 100, tax_cents / 100, total / 100,
         currency, issued, wo))
    inv = sql(db_path, "SELECT MAX(id) FROM invoices")[0][0]
    for i, ((kind, desc, qty, unit), cents) in enumerate(zip(lines, line_cents)):
        sql(db_path, "INSERT INTO invoice_line_items (invoice_id, item_type, description, "
                     "quantity, unit_price, line_total, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (inv, kind, desc, qty, unit / 100, cents / 100, i))
    return inv


def _map_qbo(db_path, shop, kinds=("receivable", "labor", "parts", "diagnostic", "misc", "tax")):
    names = {"receivable": "Accounts Receivable (A/R)", "labor": "Labor Income",
             "parts": "Parts Sales", "diagnostic": "Diagnostic Income",
             "misc": "Shop Supplies Income", "tax": "Sales Tax Payable"}
    for kind in kinds:
        ok(db_path, "shop", "accounting", "map", "set", "--shop", shop, "--target",
           "quickbooks-online", "--kind", kind, "--account", names[kind])


def _map_xero(db_path, shop, tax_type="Tax on Sales (6.25%)",
              kinds=("labor", "parts", "diagnostic", "misc")):
    codes = {"labor": "200", "parts": "210", "diagnostic": "220", "misc": "230"}
    for kind in kinds:
        ok(db_path, "shop", "accounting", "map", "set", "--shop", shop, "--target", "xero",
           "--kind", kind, "--account", codes[kind], "--tax-type", tax_type)


def _export(db_path, s, target, out, *extra, frm="2026-09-01", to="2026-09-30"):
    return ok(db_path, "shop", "accounting", "export", "--shop", s["shop"], "--target",
              target, "--from", frm, "--to", to, "--out", str(out), *extra)


def _read(out) -> list[dict]:
    raw = Path(out).read_bytes().decode("utf-8")
    return list(csv.DictReader(io.StringIO(raw)))


def _header(out) -> list[str]:
    return Path(out).read_text().splitlines()[0].split(",")


@pytest.fixture
def db(tmp_path):
    path = new_db(tmp_path)
    return path, seed_booking_shop(path)


@pytest.fixture
def september(db):
    """Two September invoices: one with every line kind and tax, one untaxed."""
    path, s = db
    a = _seed_invoice(path, s, "INV-1-0001", "2026-09-10T15:00:00+00:00", [
        ("labor", "Labor — 2.50h × $120.00/h", 2.5, 12000),
        ("parts", "NGK spark plug", 2, 899),
        ("diagnostic", "Diagnostic fee", 1, 5000),
        ("misc", "Shop supplies", 1, 1600),
    ], tax_cents=2256)
    b = _seed_invoice(path, s, "INV-1-0002", "2026-09-20T09:00:00+00:00", [
        ("labor", "Labor — 1.00h × $120.00/h", 1, 12000),
    ], tax_cents=0, customer=s["sam"])
    return path, s, a, b


class TestTheColumns:
    def test_quickbooks_columns_are_the_ones_intuits_page_names(self):
        text = _sources_text()
        section = text.split("## QuickBooks Online: \"Import journal entries\"")[1].split("## ")[0]
        for column in acct_export.QBO_JOURNAL_COLUMNS:
            assert f'"{column}"' in section or f"{column} column" in section, column
        assert acct_export.QBO_JOURNAL_COLUMNS == (
            "Journal No.", "Journal Date", "Account Name", "Debits", "Credits",
            "Journal/Description", "Name")

    def test_xero_columns_are_the_pages_names_plus_two_flagged(self):
        text = _sources_text()
        para = text.split("**The column names the page itself gives**")[1].split("\n\n")[0]
        given = set(re.findall(r"`([A-Za-z]+)`", para.split("`POAddress`")[0]))
        assert given == set(acct_export.XERO_COLUMNS_FROM_PAGE)
        assert set(acct_export.XERO_COLUMNS) == (
            set(acct_export.XERO_COLUMNS_FROM_PAGE) | set(acct_export.XERO_COLUMNS_NOT_ON_PAGE))
        assert acct_export.XERO_COLUMNS_NOT_ON_PAGE == ("Description", "Quantity")
        assert "`Description`\nand `Quantity` do **not** appear on the page" in para


class TestQuickBooksOnline:
    def test_each_invoice_is_one_balanced_journal_entry(self, september, tmp_path):
        path, s, _, _ = september
        _map_qbo(path, s["shop"])
        out = tmp_path / "qbo.csv"
        printed = _export(path, s, "quickbooks-online", out)
        assert _header(out) == list(acct_export.QBO_JOURNAL_COLUMNS)
        rows = _read(out)
        entries: dict[str, list[dict]] = {}
        for r in rows:
            entries.setdefault(r["Journal No."], []).append(r)
        assert list(entries) == ["INV-1-0001", "INV-1-0002"]

        def cents(v):
            return round(float(v) * 100) if v else 0
        for number, lines in entries.items():
            assert sum(cents(r["Debits"]) for r in lines) == sum(
                cents(r["Credits"]) for r in lines), number
        first = entries["INV-1-0001"]
        assert [(r["Account Name"], r["Debits"], r["Credits"], r["Name"]) for r in first] == [
            ("Accounts Receivable (A/R)", "406.54", "", "Dana Reyes"),
            ("Labor Income", "", "300.00", ""),
            ("Parts Sales", "", "17.98", ""),
            ("Diagnostic Income", "", "50.00", ""),
            ("Shop Supplies Income", "", "16.00", ""),
            ("Sales Tax Payable", "", "22.56", ""),
        ]
        assert {r["Journal Date"] for r in first} == {"09/10/2026"}
        assert [r["Account Name"] for r in entries["INV-1-0002"]] == [
            "Accounts Receivable (A/R)", "Labor Income"]
        assert "Wrote 2 invoice(s), 8 row(s)" in printed

    def test_the_command_says_plainly_these_are_journal_entries(self, september, tmp_path):
        path, s, _, _ = september
        _map_qbo(path, s["shop"])
        printed = _export(path, s, "quickbooks-online", tmp_path / "qbo.csv")
        assert ("These are journal entries, not invoices: they carry no line items, "
                "and they do not reach QuickBooks' sales-tax reports.") in printed
        _map_xero(path, s["shop"])
        xero_printed = _export(path, s, "xero", tmp_path / "xero.csv")
        assert "journal entries" not in xero_printed

    def test_a_missing_account_is_named_and_nothing_is_written(self, september, tmp_path):
        path, s, _, _ = september
        _map_qbo(path, s["shop"], kinds=("receivable", "labor", "parts", "misc"))
        out = tmp_path / "qbo.csv"
        printed = refused(path, "shop", "accounting", "export", "--shop", s["shop"],
                          "--target", "quickbooks-online", "--from", "2026-09-01",
                          "--to", "2026-09-30", "--out", str(out))
        assert "no quickbooks-online account is mapped for diagnostic, sales tax" in printed
        assert "--kind diagnostic" in printed
        assert not out.exists()
        assert sql(path, "SELECT COUNT(*) FROM accounting_exports") == [(0,)]

    def test_an_invoice_that_does_not_balance_is_refused(self, db, tmp_path):
        path, s = db
        _seed_invoice(path, s, "INV-BAD", "2026-09-10T15:00:00+00:00",
                      [("labor", "Labor", 1, 10000)], tax_cents=500, total_cents=10400)
        _map_qbo(path, s["shop"])
        printed = refused(path, "shop", "accounting", "export", "--shop", s["shop"],
                          "--target", "quickbooks-online", "--from", "2026-09-01",
                          "--to", "2026-09-30", "--out", str(tmp_path / "q.csv"))
        assert "INV-BAD does not balance: its lines and tax come to 105.00" in printed

    def test_an_invoice_made_by_the_invoice_command_exports(self, db, tmp_path):
        path, s = db
        sql(path, "INSERT INTO work_orders (shop_id, vehicle_id, customer_id, title, "
                  "status, actual_hours) VALUES (?, ?, ?, 'Carb clean', 'completed', 1.5)",
            (s["shop"], s["bike1"], s["dana"]))
        # Phase 281: 6.25% on every line is the shop's rate on record.
        record_tax(path, s["shop"], rate=0.0625)
        ok(path, "shop", "invoice", "generate", "1",
           "--hourly-rate", "11000", "--diagnostic-fee", "4500", "--supplies-pct", "0.05")
        # F196: the shop's day of the invoice's own stamp, never the UTC clock's
        # day, which is tomorrow on a US evening.
        today = local_day(sql(path, "SELECT issued_at FROM invoices")[0][0])
        _map_qbo(path, s["shop"], kinds=("receivable", "labor", "diagnostic", "misc", "tax"))
        out = tmp_path / "gen.csv"
        _export(path, s, "quickbooks-online", out, frm=today, to=today)
        rows = _read(out)
        debits = sum(round(float(r["Debits"]) * 100) for r in rows if r["Debits"])
        credits = sum(round(float(r["Credits"]) * 100) for r in rows if r["Credits"])
        total = round(sql(path, "SELECT total FROM invoices")[0][0] * 100)
        assert debits == credits == total


class TestWhichInvoices:
    def test_cancelled_other_shops_and_out_of_range_invoices_are_left_out(self, september, tmp_path):
        path, s, _, _ = september
        _seed_invoice(path, s, "INV-VOID", "2026-09-11T10:00:00+00:00",
                      [("labor", "Labor", 1, 10000)], tax_cents=0, status="cancelled")
        _seed_invoice(path, s, "INV-OCT", "2026-10-01T10:00:00+00:00",
                      [("labor", "Labor", 1, 10000)], tax_cents=0)
        other = sql(path, "INSERT INTO shops (name) VALUES ('Other Shop') RETURNING id")[0][0]
        _seed_invoice(path, s, "INV-OTHER", "2026-09-12T10:00:00+00:00",
                      [("labor", "Labor", 1, 10000)], tax_cents=0, shop=other)
        _map_qbo(path, s["shop"])
        out = tmp_path / "q.csv"
        _export(path, s, "quickbooks-online", out)
        assert sorted({r["Journal No."] for r in _read(out)}) == ["INV-1-0001", "INV-1-0002"]

    def test_an_invoice_is_not_exported_twice_by_accident(self, september, tmp_path):
        path, s, _, _ = september
        _map_qbo(path, s["shop"])
        _export(path, s, "quickbooks-online", tmp_path / "first.csv")
        _seed_invoice(path, s, "INV-1-0003", "2026-09-25T10:00:00+00:00",
                      [("labor", "Labor", 1, 10000)], tax_cents=0)
        printed = _export(path, s, "quickbooks-online", tmp_path / "second.csv")
        assert {r["Journal No."] for r in _read(tmp_path / "second.csv")} == {"INV-1-0003"}
        assert "Left out, already exported: INV-1-0001, INV-1-0002." in printed
        again = _export(path, s, "quickbooks-online", tmp_path / "third.csv",
                        "--include-exported")
        assert "Wrote 3 invoice(s)" in again
        nothing = refused(path, "shop", "accounting", "export", "--shop", s["shop"],
                          "--target", "quickbooks-online", "--from", "2026-09-01",
                          "--to", "2026-09-30", "--out", str(tmp_path / "fourth.csv"))
        assert "3 were exported before" in nothing
        # another target has its own record
        _map_xero(path, s["shop"])
        assert "Wrote 3 invoice(s)" in _export(path, s, "xero", tmp_path / "x.csv")

    def test_each_export_is_recorded_with_its_files_hash(self, september, tmp_path):
        path, s, a, b = september
        _map_qbo(path, s["shop"])
        out = tmp_path / "q.csv"
        _export(path, s, "quickbooks-online", out)
        digest = hashlib.sha256(out.read_bytes()).hexdigest()
        assert sql(path, "SELECT target, period_from, period_to, file_sha256, invoice_count "
                         "FROM accounting_exports") == [
            ("quickbooks_online", "2026-09-01", "2026-09-30", digest, 2)]
        assert sql(path, "SELECT invoice_id FROM accounting_export_invoices "
                         "ORDER BY invoice_id") == [(a,), (b,)]
        assert "quickbooks-online" in ok(path, "shop", "accounting", "exports",
                                         "--shop", s["shop"])

    def test_an_existing_file_is_not_overwritten(self, september, tmp_path):
        path, s, _, _ = september
        _map_qbo(path, s["shop"])
        out = tmp_path / "mine.csv"
        out.write_text("keep")
        assert "already exists" in refused(
            path, "shop", "accounting", "export", "--shop", s["shop"], "--target",
            "quickbooks-online", "--from", "2026-09-01", "--to", "2026-09-30",
            "--out", str(out))
        assert out.read_text() == "keep"


class TestXero:
    def test_one_row_per_line_tax_exclusive_with_the_invoices_tax(self, september, tmp_path):
        path, s, _, _ = september
        _map_xero(path, s["shop"])
        out = tmp_path / "xero.csv"
        printed = _export(path, s, "xero", out)
        assert _header(out) == list(acct_export.XERO_COLUMNS)
        rows = _read(out)
        first = [r for r in rows if r["InvoiceNumber"] == "INV-1-0001"]
        assert [(r["Description"], r["Quantity"], r["UnitAmount"], r["AccountCode"])
                for r in first] == [
            ("Labor — 2.50h × $120.00/h", "2.5", "120.00", "200"),
            ("NGK spark plug", "2", "8.99", "210"),
            ("Diagnostic fee", "1", "50.00", "220"),
            ("Shop supplies", "1", "16.00", "230"),
        ]
        assert sum(round(float(r["TaxAmount"]) * 100) for r in first) == 2256
        assert {r["TaxType"] for r in first} == {"Tax on Sales (6.25%)"}
        assert {(r["ContactName"], r["EmailAddress"], r["InvoiceDate"], r["DueDate"],
                 r["Currency"]) for r in first} == {
            ("Dana Reyes", "dana@example.com", "09/10/2026", "", "USD")}
        assert "Prices are tax exclusive" in printed

    def test_a_recorded_due_date_and_currency_are_written(self, db, tmp_path):
        path, s = db
        inv = _seed_invoice(path, s, "INV-EUR", "2026-09-10T15:00:00+00:00",
                            [("labor", "Labor", 1, 10000)], tax_cents=0, currency="EUR")
        sql(path, "UPDATE invoices SET due_at = '2026-10-10T00:00:00+00:00' WHERE id = ?", (inv,))
        _map_xero(path, s["shop"], kinds=("labor",))
        out = tmp_path / "x.csv"
        _export(path, s, "xero", out)
        (row,) = _read(out)
        assert (row["DueDate"], row["Currency"]) == ("10/10/2026", "EUR")

    def test_a_kind_mapped_without_a_tax_rate_is_refused(self, september, tmp_path):
        path, s, _, _ = september
        _map_xero(path, s["shop"])
        ok(path, "shop", "accounting", "map", "set", "--shop", s["shop"], "--target", "xero",
           "--kind", "parts", "--account", "210")
        printed = refused(path, "shop", "accounting", "export", "--shop", s["shop"],
                          "--target", "xero", "--from", "2026-09-01", "--to", "2026-09-30",
                          "--out", str(tmp_path / "x.csv"))
        assert "none is set for parts" in printed

    def test_the_mapping_is_listed_and_can_be_changed(self, db):
        path, s = db
        _map_xero(path, s["shop"], kinds=("labor",))
        ok(path, "shop", "accounting", "map", "set", "--shop", s["shop"], "--target", "xero",
           "--kind", "labor", "--account", "201", "--tax-type", "Tax Exempt")
        assert sql(path, "SELECT target, kind, account, tax_type FROM accounting_accounts") == [
            ("xero", "labor", "201", "Tax Exempt")]
        listed = ok(path, "shop", "accounting", "map", "list", "--shop", s["shop"])
        assert "labour" in listed and "201" in listed and "Tax Exempt" in listed


class TestSpreadingTheTax:
    @pytest.mark.parametrize("lines, tax, expected", [
        ([100, 100, 100], 100, [33, 33, 34]),
        ([30000, 1798, 5000, 1600], 2256, [1762, 105, 293, 96]),
        ([500], 31, [31]),
        ([0, 0], 7, [0, 7]),
    ])
    def test_the_shares_sum_to_the_invoices_tax(self, lines, tax, expected):
        shares = acct_export.spread_tax(lines, tax)
        assert shares == expected
        assert sum(shares) == tax
