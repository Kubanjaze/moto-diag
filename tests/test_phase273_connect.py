"""Phase 273 — Connect: a shop's own Stripe account (the operator's 1A).

Reached by ``motodiag shop payments connect`` and ``status``. Stripe
answers from fixtures through the SDK's own http_client; no network.
"""

from __future__ import annotations

import pytest

from motodiag.payments import connect
from support.phase273 import STRIPE_ENV, answer, cli, new_db, seed_invoice, sql
from support.stripe_fixtures import SHOP_ACCOUNT, TEST_KEY, stripe_settings

CREATE = ("POST", r"/v2/core/accounts", "v2_account_created")
LINK = ("POST", r"/v2/core/account_links", "v2_account_link")
READ_ACTIVE = ("GET", rf"/v2/core/accounts/{SHOP_ACCOUNT}", "v2_account_active")


@pytest.fixture
def db(tmp_path):
    return new_db(tmp_path)


def _connect(db, monkeypatch, *extra):
    ids = seed_invoice(db)
    http = answer(monkeypatch, [CREATE, LINK, *extra])
    out = cli(db, "shop", "payments", "connect", "--shop", ids["shop_id"],
              "--email", "owner@example.com", "--country", "US", "--currency", "USD")
    return ids, http, out


class TestConnect:
    def test_creates_the_account_with_the_operators_configuration(self, db, monkeypatch):
        ids, http, out = _connect(db, monkeypatch)
        assert out.exit_code == 0, out.output
        sent = http.requests[0].params
        assert sent["dashboard"] == "full"
        assert sent["defaults"]["responsibilities"] == {
            "fees_collector": "stripe", "losses_collector": "stripe"}
        assert sent["configuration"]["merchant"]["capabilities"]["card_payments"] == {
            "requested": True}
        assert sent["identity"] == {"country": "us"}
        assert sent["defaults"]["currency"] == "usd"
        row = sql(db, "SELECT * FROM shop_payment_accounts WHERE shop_id = ?",
                  (ids["shop_id"],))[0]
        assert row["stripe_account_id"] == SHOP_ACCOUNT
        assert row["card_payments_status"] == "restricted"
        assert row["requirements_due"] == 2  # eventually_due is not counted
        assert "Created Stripe account" in out.output

    def test_prints_the_onboarding_link_with_stripes_warning(self, db, monkeypatch):
        _, http, out = _connect(db, monkeypatch)
        assert "https://connect.stripe.com/d/setup/fixture_link_not_real" in out.output
        assert "never by email or text" in out.output
        link = http.requests[1].params
        assert link["account"] == SHOP_ACCOUNT
        assert link["use_case"]["type"] == "account_onboarding"
        assert "configurations" not in link["use_case"]["account_onboarding"]

    def test_every_request_sends_the_pinned_version(self, db, monkeypatch):
        _, http, _ = _connect(db, monkeypatch)
        assert {r.headers["Stripe-Version"] for r in http.requests} == {
            "2026-09-30.endive"}

    def test_a_second_connect_reuses_the_account(self, db, monkeypatch):
        ids, _, _ = _connect(db, monkeypatch)
        http = answer(monkeypatch, [LINK])
        out = cli(db, "shop", "payments", "connect", "--shop", ids["shop_id"])
        assert out.exit_code == 0, out.output
        assert "Using Stripe account" in out.output
        assert [r.path for r in http.requests] == ["/v2/core/account_links"]

    def test_country_and_currency_come_from_the_tax_jurisdiction(self, db, monkeypatch):
        from support.tax_on_record import record_tax
        ids = seed_invoice(db)
        record_tax(db, ids["shop_id"])  # ZZ-T, USD
        http = answer(monkeypatch, [CREATE, LINK])
        out = cli(db, "shop", "payments", "connect", "--shop", ids["shop_id"],
                  "--email", "owner@example.com")
        assert out.exit_code == 0, out.output
        assert http.requests[0].params["identity"] == {"country": "zz"}

    def test_no_jurisdiction_and_no_country_is_refused_before_stripe(self, db, monkeypatch):
        ids = seed_invoice(db)
        http = answer(monkeypatch, [])
        out = cli(db, "shop", "payments", "connect", "--shop", ids["shop_id"],
                  "--email", "owner@example.com")
        assert out.exit_code == 1
        assert "--country" in out.output
        assert http.requests == []


class TestStatus:
    def test_status_reads_stripe_and_stores_active(self, db, monkeypatch):
        ids, _, _ = _connect(db, monkeypatch)
        answer(monkeypatch, [READ_ACTIVE])
        out = cli(db, "shop", "payments", "status", "--shop", ids["shop_id"])
        assert out.exit_code == 0, out.output
        assert "Card payments: active" in out.output
        assert connect.get_shop_account(ids["shop_id"], db_path=db).can_take_payments

    def test_status_exits_1_while_card_payments_is_not_active(self, db, monkeypatch):
        ids, _, _ = _connect(db, monkeypatch)
        answer(monkeypatch, [("GET", rf"/v2/core/accounts/{SHOP_ACCOUNT}",
                              "v2_account_created")])
        out = cli(db, "shop", "payments", "status", "--shop", ids["shop_id"])
        assert out.exit_code == 1
        assert "Card payments: restricted" in out.output

    def test_stripe_down_names_stripe_and_shows_what_is_stored(self, db, monkeypatch):
        ids, _, _ = _connect(db, monkeypatch)
        http = answer(monkeypatch, [("GET", r"/v2/core/accounts/.*", (500, {
            "error": {"type": "api_error", "message": "Something went wrong"}}))])
        out = cli(db, "shop", "payments", "status", "--shop", ids["shop_id"])
        assert out.exit_code == 1
        assert "Stripe returned an error" in out.output
        assert len(http.requests) == 1
        assert "Stored, read" in out.output and "restricted" in out.output

    def test_a_payment_is_refused_until_card_payments_is_active(self, db, monkeypatch):
        ids, _, _ = _connect(db, monkeypatch)
        http = answer(monkeypatch, [])
        out = cli(db, "shop", "invoice", "pay-link", ids["invoice_id"])
        assert out.exit_code == 1
        assert "cannot take card payments yet" in out.output
        assert http.requests == []
        assert sql(db, "SELECT COUNT(*) FROM invoice_payments")[0][0] == 0


class TestNotConfigured:
    def test_the_fake_provider_refuses_rather_than_pretending(self, db):
        ids = seed_invoice(db)
        out = cli(db, "shop", "payments", "connect", "--shop", ids["shop_id"],
                  "--email", "o@example.com", "--country", "US", "--currency", "USD",
                  env={"MOTODIAG_BILLING_PROVIDER": "fake"})
        assert out.exit_code == 1
        assert "Stripe is not configured" in out.output
        assert sql(db, "SELECT COUNT(*) FROM shop_payment_accounts")[0][0] == 0

    def test_settings_helper_is_test_mode(self):
        assert stripe_settings().stripe_api_key == TEST_KEY
        assert STRIPE_ENV["MOTODIAG_STRIPE_API_KEY"] == TEST_KEY
