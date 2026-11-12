"""Phase 372 — a shop's card payments over HTTP.

Five routes in front of Phase 273's functions. Each is driven through
``TestClient(create_app(...))`` on a scratch database, with Stripe
answered from ``tests/fixtures/phase273/`` by the SDK's own http_client.
No test reads the live database and none reaches the network.
"""

from __future__ import annotations

import pytest
from support import phase303 as h
from support.phase273 import STRIPE_ENV, answer, seed_account, seed_invoice, seed_reader
from support.stripe_fixtures import (
    INVOICE_SESSION,
    LIVE_KEY_PLANTED,
    READER,
    SHOP_ACCOUNT,
    TERMINAL_PI,
    TEST_KEY,
    event,
    stripe_settings,
)

from motodiag.billing.webhook_handlers import dispatch_event
from motodiag.cli.payments import PAID_BY_EVENT
from motodiag.core.config import reset_settings
from motodiag.shop import seed_first_owner

CHECKOUT = ("POST", r"/v1/checkout/sessions", "checkout_session_invoice")
CREATE = ("POST", r"/v2/core/accounts", "v2_account_created")
LINK = ("POST", r"/v2/core/account_links", "v2_account_link")
READ_ACTIVE = ("GET", rf"/v2/core/accounts/{SHOP_ACCOUNT}", "v2_account_active")
TERMINAL = [
    ("POST", r"/v1/payment_intents", "payment_intent_card_present"),
    ("POST", rf"/v1/terminal/readers/{READER}/process_payment_intent", "reader_processing"),
    ("POST", rf"/v1/test_helpers/terminal/readers/{READER}/present_payment_method",
     "reader_presented"),
]
LINK_URL = "https://connect.stripe.com/d/setup/fixture_link_not_real"


class Shop:
    """A shop with a sent invoice of 250.00 USD, its owner, a service
    writer and a tech (all on the shop tier), a member of another shop,
    and an individual-tier caller. Each caller holds an API key."""

    def __init__(self, db: str) -> None:
        self.db = db
        self.ids = seed_invoice(db)
        self.shop_id = self.ids["shop_id"]
        self.invoice_id = self.ids["invoice_id"]
        self.other = seed_invoice(db, shop_name="Another Shop")
        self.users: dict[str, int] = {}
        self.keys: dict[str, str] = {}
        for name, tier in (("owner", "shop"), ("writer", "shop"), ("tech", "shop"),
                           ("stranger", "shop"), ("solo", "individual")):
            # Only the writer logs in (the audit test); a password hash is slow.
            uid = h.make_user(db, name, h.PASSWORD if name == "writer" else None)
            h.make_sub(db, uid, tier)
            self.users[name] = uid
            self.keys[name] = h.make_key(db, uid)
        seed_first_owner(self.shop_id, self.users["owner"], db_path=db)
        h.add_member(db, self.shop_id, self.users["writer"], "service_writer")
        h.add_member(db, self.shop_id, self.users["tech"], "tech")
        seed_first_owner(self.other["shop_id"], self.users["stranger"], db_path=db)
        self.c = h.client(db)

    def hdr(self, who: str) -> dict:
        return {"X-API-Key": self.keys[who]}

    def account(self, who: str = "owner", **params):
        return self.c.get(f"/v1/shop/{self.shop_id}/payments/account",
                          params=params, headers=self.hdr(who))

    def connect(self, who: str = "owner", body: dict | None = None):
        if body is None:
            body = {"contact_email": "owner@example.com", "country": "US", "currency": "USD"}
        return self.c.post(f"/v1/shop/{self.shop_id}/payments/connect",
                           json=body, headers=self.hdr(who))

    def start(self, channel: str, who: str = "owner", invoice_id: int | None = None):
        inv = self.invoice_id if invoice_id is None else invoice_id
        return self.c.post(f"/v1/shop/{self.shop_id}/invoices/{inv}/payments/{channel}",
                           headers=self.hdr(who))

    def payments(self, who: str = "owner", invoice_id: int | None = None):
        inv = self.invoice_id if invoice_id is None else invoice_id
        return self.c.get(f"/v1/shop/{self.shop_id}/invoices/{inv}/payments",
                          headers=self.hdr(who))

    def rows(self) -> list:
        return h.sql(self.db, "SELECT channel, status, started_by_user_id, "
                              "terminal_reader_id, invoice_id FROM invoice_payments ORDER BY id")

    def invoice_status(self) -> str:
        return h.sql(self.db, "SELECT status FROM invoices WHERE id = ?",
                     (self.invoice_id,))[0][0]


@pytest.fixture
def shop(tmp_path, monkeypatch):
    db = h.new_db(tmp_path, monkeypatch)
    for k, v in STRIPE_ENV.items():
        monkeypatch.setenv(k, v)
    reset_settings()
    yield Shop(db)
    reset_settings()


@pytest.fixture
def ready(shop):
    """The shop's account is active."""
    seed_account(shop.db, shop.shop_id)
    return shop


def _every_route(s: Shop) -> list:
    base = f"/v1/shop/{s.shop_id}"
    inv = f"{base}/invoices/{s.invoice_id}/payments"
    return [("GET", f"{base}/payments/account", None),
            ("POST", f"{base}/payments/connect", {"contact_email": "a@b.co"}),
            ("POST", f"{inv}/checkout", None),
            ("POST", f"{inv}/terminal", None),
            ("GET", inv, None)]


class TestWhoMay:
    def test_no_credential_is_401_everywhere(self, ready, monkeypatch):
        http = answer(monkeypatch, [])
        for method, path, body in _every_route(ready):
            r = ready.c.request(method, path, json=body)
            assert r.status_code == 401, (path, r.text)
        assert http.requests == []

    def test_an_individual_tier_caller_is_402_everywhere(self, ready, monkeypatch):
        http = answer(monkeypatch, [])
        for method, path, body in _every_route(ready):
            r = ready.c.request(method, path, json=body, headers=ready.hdr("solo"))
            assert r.status_code == 402, (path, r.text)
        assert http.requests == []

    def test_a_member_of_another_shop_is_403_everywhere(self, ready, monkeypatch):
        http = answer(monkeypatch, [])
        for method, path, body in _every_route(ready):
            r = ready.c.request(method, path, json=body, headers=ready.hdr("stranger"))
            assert r.status_code == 403, (path, r.text)
        assert http.requests == []
        assert ready.rows() == []

    def test_a_tech_may_not_start_list_or_connect(self, ready, monkeypatch):
        http = answer(monkeypatch, [])
        assert ready.start("checkout", "tech").status_code == 403
        assert ready.start("terminal", "tech").status_code == 403
        assert ready.payments("tech").status_code == 403
        assert ready.connect("tech").status_code == 403
        assert http.requests == [] and ready.rows() == []

    def test_a_tech_may_read_the_account(self, ready):
        """The exclusion's control: membership alone reads the account."""
        r = ready.account("tech")
        assert r.status_code == 200, r.text
        assert r.json()["stripe_account_id"] == SHOP_ACCOUNT

    def test_a_service_writer_may_start_but_not_connect(self, ready, monkeypatch):
        answer(monkeypatch, [CHECKOUT])
        assert ready.start("checkout", "writer").status_code == 201
        assert ready.connect("writer").status_code == 403
        assert ready.payments("writer").status_code == 200

    def test_the_owner_may_do_all_of_it(self, ready, monkeypatch):
        seed_reader(ready.db, ready.shop_id)
        answer(monkeypatch, [CHECKOUT, *TERMINAL, LINK])
        assert ready.start("checkout").status_code == 201
        assert ready.start("terminal").status_code == 201
        assert ready.payments().status_code == 200
        assert ready.account().status_code == 200
        assert ready.connect().status_code == 200


class TestTheInvoiceMustBeTheShops:
    @pytest.mark.parametrize("call", ["checkout", "terminal", "list"])
    def test_an_invoice_at_another_shop_is_404(self, ready, monkeypatch, call):
        seed_account(ready.db, ready.other["shop_id"], account="acct_1OtherShop")
        seed_reader(ready.db, ready.shop_id)
        http = answer(monkeypatch, [])
        other = ready.other["invoice_id"]
        r = (ready.payments(invoice_id=other) if call == "list"
             else ready.start(call, invoice_id=other))
        assert r.status_code == 404, r.text
        assert r.json()["type"].endswith("/invoice-not-found")
        assert http.requests == [] and ready.rows() == []

    def test_an_invoice_that_does_not_exist_is_404(self, ready, monkeypatch):
        http = answer(monkeypatch, [])
        r = ready.start("checkout", invoice_id=999999)
        assert r.status_code == 404
        # The route's own answer, not the 404 of a path nobody serves.
        assert r.json()["type"].endswith("/invoice-not-found")
        assert http.requests == [] and ready.rows() == []


class TestCheckout:
    def test_returns_the_session_url_and_leaves_the_invoice_unpaid(self, ready, monkeypatch):
        http = answer(monkeypatch, [CHECKOUT])
        r = ready.start("checkout", "writer")
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["checkout_url"] == INVOICE_SESSION["url"]
        assert body["paid_when"] == PAID_BY_EVENT
        assert (body["amount_cents"], body["currency"], body["channel"]) == (
            25000, "usd", "checkout")
        assert body["invoice_number"].startswith("INV-273-")
        assert ready.rows() == [("checkout", "started", ready.users["writer"], None,
                                 ready.invoice_id)]
        assert ready.invoice_status() == "sent"
        assert http.requests[0].headers["Stripe-Account"] == SHOP_ACCOUNT


class TestTerminal:
    def test_sends_the_intent_to_the_reader(self, ready, monkeypatch):
        seed_reader(ready.db, ready.shop_id)
        answer(monkeypatch, TERMINAL)
        r = ready.start("terminal")
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["payment_intent_id"] == TERMINAL_PI
        assert body["reader_action_status"]
        assert body["paid_when"] == PAID_BY_EVENT
        assert ready.rows() == [("terminal", "started", ready.users["owner"], READER,
                                 ready.invoice_id)]
        assert ready.invoice_status() == "sent"

    def test_no_reader_is_409_naming_the_setup_command(self, ready, monkeypatch):
        http = answer(monkeypatch, [])
        r = ready.start("terminal")
        assert r.status_code == 409, r.text
        assert r.json()["type"].endswith("/payment-refused")
        assert "motodiag shop terminal setup" in r.json()["detail"]
        assert http.requests == [] and ready.rows() == []


class TestConnect:
    def test_creates_once_and_links_twice(self, shop, monkeypatch):
        http = answer(monkeypatch, [CREATE, LINK])
        r = shop.connect()
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["created"] is True
        assert body["onboarding_url"] == LINK_URL
        assert body["stripe_account_id"] == SHOP_ACCOUNT
        assert body["card_payments_status"] == "restricted"
        assert body["expires_at"]
        assert [q.path for q in http.requests] == ["/v2/core/accounts",
                                                    "/v2/core/account_links"]
        stored = h.sql(shop.db, "SELECT created_by_user_id FROM shop_payment_accounts "
                                "WHERE shop_id = ?", (shop.shop_id,))
        assert stored == [(shop.users["owner"],)]

        http = answer(monkeypatch, [LINK])
        r = shop.connect(body={})
        assert r.status_code == 200, r.text
        assert r.json()["created"] is False
        assert r.json()["onboarding_url"] == LINK_URL
        assert [q.path for q in http.requests] == ["/v2/core/account_links"]

    def test_no_email_the_first_time_is_409(self, shop, monkeypatch):
        http = answer(monkeypatch, [])
        r = shop.connect(body={"country": "US", "currency": "USD"})
        assert r.status_code == 409, r.text
        assert r.json()["type"].endswith("/payment-refused")
        assert "contact email" in r.json()["detail"]
        assert http.requests == []


class TestTheAccount:
    def test_no_account_is_404(self, shop, monkeypatch):
        http = answer(monkeypatch, [])
        r = shop.account()
        assert r.status_code == 404
        assert "no Stripe account yet" in r.text
        assert http.requests == []

    def test_the_stored_reading_without_refresh(self, shop, monkeypatch):
        seed_account(shop.db, shop.shop_id, status="restricted")
        http = answer(monkeypatch, [])
        r = shop.account()
        assert r.status_code == 200, r.text
        assert r.json() == {
            "stripe_account_id": SHOP_ACCOUNT, "card_payments_status": "restricted",
            "requirements_due": 0, "status_checked_at": "2026-10-06T12:00:00.000+00:00",
            "livemode": False, "can_take_payments": False,
        }
        assert http.requests == []

    def test_refresh_asks_stripe_once_and_stores_its_answer(self, shop, monkeypatch):
        seed_account(shop.db, shop.shop_id, status="restricted")
        http = answer(monkeypatch, [READ_ACTIVE])
        r = shop.account(refresh="true")
        assert r.status_code == 200, r.text
        assert r.json()["card_payments_status"] == "active"
        assert r.json()["can_take_payments"] is True
        assert len(http.requests) == 1
        stored = h.sql(shop.db, "SELECT card_payments_status FROM shop_payment_accounts")
        assert stored == [("active",)]


class TestNotPayable:
    def test_a_paid_invoice_is_409_not_400(self, ready, monkeypatch):
        h.sql(ready.db, "UPDATE invoices SET status = 'paid' WHERE id = ?",
              (ready.invoice_id,))
        http = answer(monkeypatch, [])
        r = ready.start("checkout")
        assert r.status_code == 409, r.text
        assert r.json()["type"].endswith("/payment-refused")
        assert "is paid" in r.json()["detail"]
        assert http.requests == [] and ready.rows() == []

    def test_an_account_not_yet_active_is_409_naming_the_status_command(
            self, shop, monkeypatch):
        seed_account(shop.db, shop.shop_id, status="restricted")
        answer(monkeypatch, [])
        r = shop.start("checkout")
        assert r.status_code == 409, r.text
        assert "motodiag shop payments status" in r.json()["detail"]


class TestNotConfigured:
    def test_no_key_is_503_naming_the_setting(self, ready, monkeypatch):
        monkeypatch.setenv("MOTODIAG_STRIPE_API_KEY", "")
        reset_settings()
        r = ready.start("checkout")
        assert r.status_code == 503, r.text
        assert r.json()["type"].endswith("/payments-not-configured")
        assert "MOTODIAG_STRIPE_API_KEY" in r.json()["detail"]
        assert ready.rows() == []

    def test_a_live_key_outside_prod_is_503_and_shows_no_key(self, ready, monkeypatch):
        monkeypatch.setenv("MOTODIAG_STRIPE_API_KEY", LIVE_KEY_PLANTED)
        monkeypatch.setenv("MOTODIAG_ENV", "dev")
        reset_settings()
        r = ready.start("checkout")
        assert r.status_code == 503, r.text
        assert r.json()["type"].endswith("/payments-not-configured")
        assert "'dev'" in r.json()["detail"]
        assert LIVE_KEY_PLANTED[8:] not in r.text and "sk_live" not in r.text
        assert ready.rows() == []


class TestStripeDown:
    def test_unreachable_is_503_naming_stripe_and_no_key(self, ready, monkeypatch):
        import stripe

        from motodiag.payments import stripe_api

        class Down(stripe.HTTPClient):
            name = "down"

            def request(self, *a, **k):
                raise stripe.APIConnectionError(f"could not connect with {TEST_KEY}")

            def close(self):
                pass

        monkeypatch.setattr(stripe_api, "_test_http_client", Down())
        r = ready.start("checkout")
        assert r.status_code == 503, r.text
        assert r.json()["type"].endswith("/stripe-unavailable")
        assert r.json()["detail"].startswith("Stripe could not be reached")
        assert TEST_KEY[8:] not in r.text
        assert ready.rows() == []  # the started row is forgotten


class TestThePaymentsList:
    def test_the_outcome_reaches_the_list_and_the_invoice_is_paid(self, ready, monkeypatch):
        answer(monkeypatch, [CHECKOUT])
        payment_id = ready.start("checkout").json()["payment_id"]
        before = ready.payments().json()
        assert before["total"] == 1
        assert before["items"][0]["status"] == "started"
        dispatch_event(event("payment_intent.succeeded", {
            "id": "pi_test_1", "object": "payment_intent", "amount": 25000,
            "amount_received": 25000, "currency": "usd", "status": "succeeded",
            "metadata": {"motodiag_payment_id": str(payment_id),
                         "motodiag_invoice_id": str(ready.invoice_id)},
        }, event_id="evt_372_ok", account=SHOP_ACCOUNT), db_path=ready.db,
            settings=stripe_settings())
        after = ready.payments().json()
        item = after["items"][0]
        assert (item["status"], item["outcome"]) == ("succeeded", "paid_invoice")
        assert item["started_by_user_id"] == ready.users["owner"]
        assert set(item) == {
            "id", "channel", "amount_cents", "currency", "status", "outcome",
            "outcome_reason", "failure_message", "refunded_cents", "started_at",
            "settled_at", "started_by_user_id"}
        assert ready.invoice_status() == "paid"


class TestTheAuditTrail:
    def test_a_session_callers_start_is_audited_with_its_path(self, ready, monkeypatch):
        answer(monkeypatch, [CHECKOUT])
        token = h.login(ready.c, "writer")
        path = f"/v1/shop/{ready.shop_id}/invoices/{ready.invoice_id}/payments/checkout"
        r = ready.c.post(path, headers=h.auth(token))
        assert r.status_code == 201, r.text
        rows = h.sql(ready.db, "SELECT path, status, actor_user_id FROM audit_events "
                               "WHERE path = ?", (path,))
        assert rows == [(path, 201, ready.users["writer"])]
