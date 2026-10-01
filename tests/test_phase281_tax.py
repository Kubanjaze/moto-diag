"""Phase 281, row 288: sales tax by jurisdiction, and the invoices that use it (F184).

Every rate and rule is stored with its effective date, valid-until date and
source; Massachusetts ships from the Department of Revenue's text; any other
shop enters its own. An invoice takes its tax only from the record, on the
taxable lines only, is refused without it, and records what it used. The
clock is fixed per test (`on_day`), so no test depends on today's date.
"""

from __future__ import annotations

import pytest

from support.phase281 import new_db, ok, on_day, refused, seed_bike, seed_customer, \
    seed_shop, sql

MA_DAY = "2026-10-01"


@pytest.fixture
def db(tmp_path):
    path = new_db(tmp_path)
    seed_shop(path, "Reyes Moto")                           # shop 1
    seed_customer(path, 1, "Dana Reyes")                     # customer 1
    seed_bike(path)                                          # bike 1
    return path


def _completed_wo(db, parts_cents=(), hours=2.0) -> int:
    sql(db, "INSERT INTO work_orders (shop_id, vehicle_id, customer_id, title, status, "
            "actual_hours) VALUES (1, 1, 1, 'Valve check', 'completed', ?)", (hours,))
    wo = sql(db, "SELECT MAX(id) FROM work_orders")[0][0]
    for i, cents in enumerate(parts_cents):
        sql(db, "INSERT INTO parts (slug, brand, description, category, make, "
                "model_pattern, typical_cost_cents) VALUES (?, 'OEM', 'Gasket', 'engine', "
                "'Honda', '%', ?)", (f"p{wo}-{i}", cents))
        part = sql(db, "SELECT MAX(id) FROM parts")[0][0]
        sql(db, "INSERT INTO work_order_parts (work_order_id, part_id, quantity, status) "
                "VALUES (?, ?, 1, 'installed')", (wo, part))
    return wo


def _in_ma(db):
    ok(db, "shop", "tax", "jurisdiction", "set", "--shop", "1", "--code", "US-MA")


def _invoice(db):
    return sql(db, "SELECT subtotal, tax_amount, total, currency, tax_rate, tax_source, "
                   "tax_recheck_by, taxed_line_types, fx_rate FROM invoices "
                   "ORDER BY id DESC LIMIT 1")[0]


def _own_rule(db, line_type, taxable=True, until="2027-12-31"):
    ok(db, "shop", "tax", "rule", "set", "--shop", "1", "--line-type", line_type,
       "--taxable" if taxable else "--not-taxable", "--effective", "2026-01-01",
       "--valid-until", until, "--source-title", "The shop's accountant, letter of 2026-09-01",
       "--checked-on", "2026-09-01")


class TestMassachusetts:
    def test_parts_are_taxed_at_6_25_and_labour_and_diagnostic_are_not(self, db, monkeypatch):
        on_day(monkeypatch, MA_DAY)
        _in_ma(db)
        wo = _completed_wo(db, parts_cents=(4000, 6000))
        out = ok(db, "shop", "invoice", "generate", wo, "--hourly-rate", "10000",
                 "--diagnostic-fee", "5000")
        subtotal, tax, total, currency, rate, source, recheck, taxed, fx = _invoice(db)
        assert subtotal == 350.0          # 200 labour + 100 parts + 50 diagnostic
        assert tax == 6.25                # 6.25% of the 100 of parts only
        assert total == 356.25
        assert (currency, rate, taxed, fx) == ("USD", 0.0625, "parts", None)
        assert recheck == "2027-09-30"
        assert "mass.gov/guides/sales-and-use-tax" in source and "(regulation)" in source
        assert "Rate must be re-checked by 2027-09-30" in out
        assert "6.25% on parts" in out

    def test_a_half_cent_rounds_up(self, db, monkeypatch):
        on_day(monkeypatch, MA_DAY)
        _in_ma(db)
        wo = _completed_wo(db, parts_cents=(1000, 1000, 400, 8,))   # 24.08 of parts
        ok(db, "shop", "invoice", "generate", wo, "--hourly-rate", "10000")
        assert _invoice(db)[1] == 1.51    # 6.25% of 24.08 = 1.505

    def test_shop_supplies_are_refused_until_the_shop_records_a_rule(self, db, monkeypatch):
        on_day(monkeypatch, MA_DAY)
        _in_ma(db)
        wo = _completed_wo(db, parts_cents=(4000,))
        out = refused(db, "shop", "invoice", "generate", wo, "--hourly-rate", "10000",
                      "--supplies-flat", "1500")
        assert "no US-MA rule on record for whether shop supplies is taxable" in out
        assert "shop tax rule set --shop 1 --line-type misc" in out
        assert sql(db, "SELECT COUNT(*) FROM invoices")[0][0] == 0, "nothing written"
        _own_rule(db, "misc", taxable=True)
        ok(db, "shop", "invoice", "generate", wo, "--hourly-rate", "10000",
           "--supplies-flat", "1500")
        subtotal, tax, _, _, _, _, recheck, taxed, _ = _invoice(db)
        assert taxed == "parts,misc"
        assert tax == 3.44                # 6.25% of (40 + 15) = 3.4375
        assert recheck == "2027-09-30"    # the earliest validity among what was used

    def test_status_prints_every_item_with_its_recheck_date_and_basis(self, db, monkeypatch):
        on_day(monkeypatch, MA_DAY)
        _in_ma(db)
        out = ok(db, "shop", "tax", "status", "--shop", "1")
        assert "US-MA (Massachusetts)" in out
        assert "Rate: 6.25%, must be re-checked by 2027-09-30" in out
        assert "Parts: taxable, must be re-checked by 2027-09-30" in out
        assert "Labour: not taxable" in out
        diagnostic = next(l for l in out.splitlines() if l.startswith("Diagnostic fee"))
        assert "a reading of 830 CMR 64H.1.1(2)(a)1" in diagnostic
        assert "a reading of the source" in diagnostic
        assert "Shop supplies: no rule on record" in out
        assert "FAILS" not in out


class TestValidity:
    def test_after_its_validity_the_rate_fails_and_invoices_are_refused(self, db, monkeypatch):
        on_day(monkeypatch, "2027-10-01")
        _in_ma(db)
        out = refused(db, "shop", "tax", "status", "--shop", "1")
        assert "FAILS: the US-MA rate was valid until 2027-09-30 and must be re-checked" in out
        wo = _completed_wo(db, parts_cents=(4000,))
        out = refused(db, "shop", "invoice", "generate", wo, "--hourly-rate", "10000")
        assert "valid until 2027-09-30" in out
        assert sql(db, "SELECT COUNT(*) FROM invoices")[0][0] == 0

    def test_the_last_valid_day_still_invoices(self, db, monkeypatch):
        on_day(monkeypatch, "2027-09-30")
        _in_ma(db)
        ok(db, "shop", "invoice", "generate", _completed_wo(db, (4000,)), "--hourly-rate", "100")

    def test_confirm_records_a_new_check_and_moves_validity_12_months(self, db, monkeypatch):
        on_day(monkeypatch, "2027-10-01")
        _in_ma(db)
        out = ok(db, "shop", "tax", "confirm", "--jurisdiction", "US-MA",
                 "--checked-on", "2027-09-20",
                 "--source-url", "https://www.mass.gov/guides/sales-and-use-tax")
        assert "must be re-checked by 2028-09-20" in out
        assert "3 rules" in out
        ok(db, "shop", "tax", "status", "--shop", "1")
        assert sql(db, "SELECT COUNT(*) FROM tax_rates WHERE provenance = 'regulation'")[0][0] == 2
        diag = sql(db, "SELECT basis, valid_until FROM tax_line_rules WHERE line_type = "
                       "'diagnostic' ORDER BY id DESC LIMIT 1")[0]
        assert diag == ("reading", "2028-09-20"), "a reading stays a reading"

    def test_a_shop_with_no_jurisdiction_is_refused_and_fails_status(self, db, monkeypatch):
        on_day(monkeypatch, MA_DAY)
        out = refused(db, "shop", "invoice", "generate", _completed_wo(db), "--hourly-rate", "1")
        assert "shop 1 has no tax jurisdiction" in out
        assert "shop tax jurisdiction set --shop 1" in out
        assert "FAILS: no tax jurisdiction" in refused(db, "shop", "tax", "status", "--shop", "1")


class TestAnotherJurisdiction:
    def test_a_shop_enters_its_own_rate_and_rules_with_their_sources(self, db, monkeypatch):
        on_day(monkeypatch, MA_DAY)
        ok(db, "shop", "tax", "jurisdiction", "add", "--code", "US-NH", "--name",
           "New Hampshire", "--currency", "usd")
        ok(db, "shop", "tax", "jurisdiction", "set", "--shop", "1", "--code", "us-nh")
        out = ok(db, "shop", "tax", "rate", "set", "--shop", "1", "--rate", "0",
                 "--effective", "2026-01-01", "--valid-until", "2026-12-31",
                 "--source-title", "NH Department of Revenue Administration",
                 "--checked-on", "2026-09-15")
        assert "0% (stored as 0)" in out
        for line_type in ("labor", "parts"):
            _own_rule(db, line_type, taxable=False, until="2026-12-31")
        ok(db, "shop", "invoice", "generate", _completed_wo(db, (4000,)), "--hourly-rate", "100")
        _, tax, _, currency, rate, source, recheck, taxed, _ = _invoice(db)
        assert (tax, currency, rate, taxed, recheck) == (0.0, "USD", 0.0, "none", "2026-12-31")
        assert "NH Department of Revenue Administration" in source and "(shop)" in source

    def test_every_field_is_required(self, db):
        ok(db, "shop", "tax", "jurisdiction", "set", "--shop", "1", "--code", "US-MA")
        out = refused(db, "shop", "tax", "rate", "set", "--shop", "1", "--rate", "5",
                      "--effective", "2026-01-01", "--source-title", "x",
                      "--checked-on", "2026-01-01")
        assert "--valid-until" in out
        out = refused(db, "shop", "tax", "rate", "set", "--shop", "1", "--rate", "5",
                      "--effective", "2026-02-01", "--valid-until", "2026-01-01",
                      "--source-title", "x", "--checked-on", "2026-01-01")
        assert "is before the effective date" in out
        assert "a currency is three letters" in refused(
            db, "shop", "tax", "jurisdiction", "add", "--code", "CA-ON", "--name", "Ontario",
            "--currency", "dollars")

    def test_the_shops_own_rate_is_used_over_the_regulation(self, db, monkeypatch):
        on_day(monkeypatch, MA_DAY)
        _in_ma(db)
        ok(db, "shop", "tax", "rate", "set", "--shop", "1", "--rate", "7", "--effective",
           "2026-01-01", "--valid-until", "2026-12-31", "--source-title", "Shop override",
           "--checked-on", "2026-09-30")
        ok(db, "shop", "invoice", "generate", _completed_wo(db, (10000,)), "--hourly-rate", "1")
        _, tax, _, _, rate, source, recheck, _, _ = _invoice(db)
        assert (tax, rate, recheck) == (7.0, 0.07, "2026-12-31")
        assert "Shop override" in source

    def test_the_invoice_is_in_the_jurisdictions_currency(self, db, monkeypatch):
        on_day(monkeypatch, MA_DAY)
        ok(db, "shop", "tax", "jurisdiction", "add", "--code", "CA-ON", "--name", "Ontario",
           "--currency", "CAD")
        ok(db, "shop", "tax", "jurisdiction", "set", "--shop", "1", "--code", "CA-ON")
        ok(db, "shop", "tax", "rate", "set", "--shop", "1", "--rate", "13", "--effective",
           "2026-01-01", "--valid-until", "2026-12-31", "--source-title", "HST",
           "--checked-on", "2026-09-30")
        _own_rule(db, "labor", taxable=True, until="2026-12-31")
        ok(db, "shop", "invoice", "generate", _completed_wo(db), "--hourly-rate", "10000")
        assert _invoice(db)[3] == "CAD"


class TestInvoiceCurrency:
    def test_another_currency_needs_the_shops_own_rate_not_the_ecbs(self, db, monkeypatch):
        on_day(monkeypatch, MA_DAY)
        _in_ma(db)
        sql(db, "INSERT INTO exchange_rates (base, quote, rate, rate_date, valid_until, "
                "source, source_url) VALUES ('EUR', 'CAD', '1.6105', '2026-09-30', "
                "'2026-10-05', 'ecb', 'x'), ('EUR', 'USD', '1.1355', '2026-09-30', "
                "'2026-10-05', 'ecb', 'x')")
        wo = _completed_wo(db, (10000,))
        out = refused(db, "shop", "invoice", "generate", wo, "--hourly-rate", "10000",
                      "--currency", "CAD")
        assert "no rate of the shop's own converts USD to CAD" in out
        assert "ECB reference rates are not used on invoices" in out
        assert sql(db, "SELECT COUNT(*) FROM invoices")[0][0] == 0
        ok(db, "shop", "currency", "set", "--shop", "1", "--from", "USD", "--to", "CAD",
           "--rate", "1.40", "--rate-date", "2026-09-30", "--valid-until", "2026-10-07",
           "--source", "Eastern Bank quote")
        out = ok(db, "shop", "invoice", "generate", wo, "--hourly-rate", "10000",
                 "--currency", "CAD")
        subtotal, tax, total, currency, _, _, _, taxed, fx = _invoice(db)
        assert (currency, fx) == ("CAD", "1.40")
        assert subtotal == 420.0          # (200 labour + 100 parts) x 1.40
        assert tax == 8.75                # 6.25% of the 140 of parts
        assert "Converted from USD at 1.40, dated 2026-09-30; the shop's own rate: " \
               "Eastern Bank quote" in out


class TestTheApi:
    @pytest.fixture
    def api(self, tmp_path, monkeypatch):
        from fastapi.testclient import TestClient

        from motodiag.api import create_app
        from motodiag.auth.api_key_repo import create_api_key
        from motodiag.core.config import reset_settings
        from motodiag.shop import seed_first_owner

        path = new_db(tmp_path, "api.db")
        monkeypatch.setenv("MOTODIAG_DB_PATH", path)
        monkeypatch.setenv("MOTODIAG_RATE_LIMIT_SHOP_PER_MINUTE", "9999")
        reset_settings()
        user = sql(path, "INSERT INTO users (username, email, tier, is_active) "
                         "VALUES ('o', 'o@ex.com', 'shop', 1) RETURNING id")[0][0]
        sql(path, "INSERT INTO subscriptions (user_id, tier, status, current_period_end) "
                  "VALUES (?, 'shop', 'active', datetime('now', '+30 days'))", (user,))
        _, key = create_api_key(user, db_path=path)
        seed_shop(path, "Api Shop")
        seed_first_owner(1, user, db_path=path)
        seed_customer(path, 1, "Dana Reyes")
        seed_bike(path)
        client = TestClient(create_app(db_path_override=path), raise_server_exceptions=False)
        yield path, client, {"X-API-Key": key}
        reset_settings()

    def test_the_request_has_no_tax_rate(self):
        from motodiag.api import create_app
        schema = create_app().openapi()["components"]["schemas"]["InvoiceGenerateRequest"]
        assert "tax_rate" not in schema["properties"]

    def test_no_tax_on_record_is_409_and_writes_nothing(self, api, monkeypatch):
        path, client, h = api
        on_day(monkeypatch, MA_DAY)
        wo = _completed_wo(path, (4000,))
        r = client.post("/v1/shop/1/invoices/generate", headers=h,
                        json={"work_order_id": wo, "labor_hourly_rate_cents": 10000})
        assert r.status_code == 409, r.text
        assert "no tax jurisdiction" in r.text
        assert sql(path, "SELECT COUNT(*) FROM invoices")[0][0] == 0

    def test_with_massachusetts_on_record_the_route_taxes_parts(self, api, monkeypatch):
        path, client, h = api
        on_day(monkeypatch, MA_DAY)
        ok(path, "shop", "tax", "jurisdiction", "set", "--shop", "1", "--code", "US-MA")
        wo = _completed_wo(path, (4000,))
        r = client.post("/v1/shop/1/invoices/generate", headers=h,
                        json={"work_order_id": wo, "labor_hourly_rate_cents": 10000,
                              "tax_rate": 0.5})
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["tax_cents"] == 250   # 6.25% of 40.00; a sent tax_rate is ignored
        assert body["tax_rate"] == 0.0625
        assert body["tax_recheck_by"] == "2027-09-30"
