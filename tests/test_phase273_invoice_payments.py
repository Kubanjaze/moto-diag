"""Phase 273 — a shop invoice paid through Stripe, online or at the reader.

The invoice becomes paid only when Stripe's verified
``payment_intent.succeeded`` reaches the webhook: from the shop's own
account, for a payment this app started, for the exact amount. Every
event is signed at test time with a test-only secret on a frozen clock.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.api.deps import get_settings as api_settings
from motodiag.billing.webhook_handlers import dispatch_event
from motodiag.payments import invoice_payments as ip
from motodiag.shop.invoicing import _cents_to_dollars, _dollars_to_cents
from support.phase273 import (
    answer, cli, new_db, seed_account, seed_invoice, seed_reader, sql,
)
from support.stripe_fixtures import (
    FROZEN_AT, INVOICE_SESSION, LOCATION, READER, SHOP_ACCOUNT, TERMINAL_PI, event,
    freeze_webhook_clock, load, signed, stripe_settings,
)

CHECKOUT = ("POST", r"/v1/checkout/sessions", "checkout_session_invoice")
# As long as the Checkout URLs Stripe returned in the smoke run (~600 chars).
LONG_URL = "https://checkout.stripe.com/c/pay/cs_test_" + "a1B2" * 20 + "#fid" + "x%2F" * 130


@pytest.fixture
def db(tmp_path):
    return new_db(tmp_path)


@pytest.fixture
def ready(db):
    """A sent invoice of 250.00 USD at a shop whose account is active."""
    ids = seed_invoice(db)
    seed_account(db, ids["shop_id"])
    return ids


def _start(db, monkeypatch, invoice_id):
    http = answer(monkeypatch, [CHECKOUT])
    out = cli(db, "shop", "invoice", "pay-link", invoice_id)
    assert out.exit_code == 0, out.output
    return http, out


def _succeeded(payment_id, invoice_id, *, event_id="evt_pi_ok", amount=25000,
               currency="usd", account=SHOP_ACCOUNT, pi_id="pi_test_1"):
    return event("payment_intent.succeeded", {
        "id": pi_id, "object": "payment_intent", "amount": amount,
        "amount_received": amount, "currency": currency, "status": "succeeded",
        "metadata": {"motodiag_payment_id": str(payment_id),
                     "motodiag_invoice_id": str(invoice_id)},
    }, event_id=event_id, account=account)


def _failed(payment_id, invoice_id, *, event_id="evt_pi_fail", pi_id="pi_test_1"):
    return event("payment_intent.payment_failed", {
        "id": pi_id, "object": "payment_intent", "amount": 25000,
        "amount_received": 0, "currency": "usd", "status": "requires_payment_method",
        "last_payment_error": {"message": "Your card was declined."},
        "metadata": {"motodiag_payment_id": str(payment_id),
                     "motodiag_invoice_id": str(invoice_id)},
    }, event_id=event_id, account=SHOP_ACCOUNT)


def _invoice(db, invoice_id):
    return sql(db, "SELECT status, paid_at FROM invoices WHERE id = ?", (invoice_id,))[0]


def _payment(db, payment_id=1):
    return sql(db, "SELECT * FROM invoice_payments WHERE id = ?", (payment_id,))[0]


def _state(db):
    """Everything a payment event can change."""
    return (
        [tuple(r) for r in sql(db, "SELECT id, status, paid_at FROM invoices ORDER BY id")],
        [tuple(r) for r in sql(db, "SELECT id, status, outcome, outcome_reason, "
                                   "payment_intent_id, refunded_cents, failure_message "
                                   "FROM invoice_payments ORDER BY id")],
    )


class TestMoney:
    def test_every_cent_survives_the_real_column(self):
        """The invoice's total is REAL dollars (118); the payment reads it
        back as cents. Exact for every cent to 10,000.00 and at the edges."""
        for cents in range(0, 1_000_001):
            assert _dollars_to_cents(_cents_to_dollars(cents)) == cents
        for cents in (10**9 - 1, 10**10 + 7, 10**11 - 1, 10**11):
            assert _dollars_to_cents(_cents_to_dollars(cents)) == cents

    def test_the_amount_charged_is_the_invoice_total_in_cents(self, db, monkeypatch, ready):
        http, _ = _start(db, monkeypatch, ready["invoice_id"])
        line = http.requests[0].params
        assert line["line_items[0][price_data][unit_amount]"] == "25000"
        assert line["line_items[0][price_data][currency]"] == "usd"
        assert _payment(db)["amount_cents"] == 25000


class TestStartingIsNotPaying:
    def test_pay_link_prints_the_url_and_leaves_the_invoice_unpaid(self, db, monkeypatch, ready):
        http, out = _start(db, monkeypatch, ready["invoice_id"])
        assert INVOICE_SESSION["url"] in out.output.splitlines()
        assert "is not paid yet" in out.output
        assert _invoice(db, ready["invoice_id"])["status"] == "sent"
        p = _payment(db)
        assert (p["status"], p["outcome"], p["channel"]) == ("started", None, "checkout")
        assert p["checkout_session_id"] == INVOICE_SESSION["id"]

    def test_the_link_survives_a_narrow_terminal(self, db, monkeypatch, ready):
        """Bug fix #1: Stripe's Checkout URLs run to ~600 characters; printed
        through rich at 80 columns they wrapped, and a copied link broke."""
        session = load("checkout_session_invoice")["body"]
        session["url"] = LONG_URL
        answer(monkeypatch, [("POST", r"/v1/checkout/sessions", (200, session))])
        out = cli(db, "shop", "invoice", "pay-link", ready["invoice_id"], columns=80)
        assert out.exit_code == 0, out.output
        assert LONG_URL in out.output.splitlines()

    def test_the_session_is_created_on_the_shops_account(self, db, monkeypatch, ready):
        http, _ = _start(db, monkeypatch, ready["invoice_id"])
        req = http.requests[0]
        assert req.headers["Stripe-Account"] == SHOP_ACCOUNT
        assert req.headers["Idempotency-Key"] == "motodiag-invoice-payment-1"
        assert req.params["mode"] == "payment"
        assert req.params["payment_intent_data[metadata][motodiag_payment_id]"] == "1"
        assert req.params["payment_intent_data[metadata][motodiag_invoice_id]"] == str(
            ready["invoice_id"])
        assert "payment_method_types[0]" not in req.params  # removed in endive

    @pytest.mark.parametrize("status", ["draft", "paid", "cancelled"])
    def test_only_a_sent_or_overdue_invoice_can_be_paid(self, db, monkeypatch, status):
        ids = seed_invoice(db, status=status)
        seed_account(db, ids["shop_id"])
        http = answer(monkeypatch, [])
        out = cli(db, "shop", "invoice", "pay-link", ids["invoice_id"])
        assert out.exit_code == 1
        assert f"is {status}" in out.output
        assert http.requests == []

    def test_a_rejected_request_leaves_no_payment_row(self, db, monkeypatch, ready):
        answer(monkeypatch, [("POST", r"/v1/checkout/sessions", "error_rejected")])
        out = cli(db, "shop", "invoice", "pay-link", ready["invoice_id"])
        assert out.exit_code == 1
        assert "Stripe rejected the request" in out.output
        assert sql(db, "SELECT COUNT(*) FROM invoice_payments")[0][0] == 0


class TestTheVerifiedEvent:
    def test_succeeded_pays_the_invoice(self, db, monkeypatch, ready):
        _start(db, monkeypatch, ready["invoice_id"])
        res = dispatch_event(_succeeded(1, ready["invoice_id"]), db_path=db,
                             settings=stripe_settings())
        assert res.processed and res.error is None
        assert _invoice(db, ready["invoice_id"])["status"] == "paid"
        p = _payment(db)
        assert (p["status"], p["outcome"], p["payment_intent_id"]) == (
            "succeeded", "paid_invoice", "pi_test_1")

    def test_from_another_account_is_rejected(self, db, monkeypatch, ready):
        _start(db, monkeypatch, ready["invoice_id"])
        res = dispatch_event(_succeeded(1, ready["invoice_id"], account="acct_other"),
                             db_path=db, settings=stripe_settings())
        assert "PaymentEventRejected" in res.error
        assert _invoice(db, ready["invoice_id"])["status"] == "sent"
        assert _payment(db)["status"] == "started"

    def test_from_the_platform_account_is_rejected(self, db, monkeypatch, ready):
        _start(db, monkeypatch, ready["invoice_id"])
        evt = _succeeded(1, ready["invoice_id"])
        del evt["account"]
        res = dispatch_event(evt, db_path=db, settings=stripe_settings())
        assert "the platform account" in res.error
        assert _invoice(db, ready["invoice_id"])["status"] == "sent"

    def test_a_short_amount_is_rejected_and_says_refund(self, db, monkeypatch, ready):
        _start(db, monkeypatch, ready["invoice_id"])
        dispatch_event(_succeeded(1, ready["invoice_id"], amount=24999), db_path=db,
                       settings=stripe_settings())
        assert _invoice(db, ready["invoice_id"])["status"] == "sent"
        p = _payment(db)
        assert p["outcome"] == "rejected" and "Refund in Stripe" in p["outcome_reason"]

    def test_another_currency_is_rejected(self, db, monkeypatch, ready):
        _start(db, monkeypatch, ready["invoice_id"])
        dispatch_event(_succeeded(1, ready["invoice_id"], currency="cad"), db_path=db,
                       settings=stripe_settings())
        assert _invoice(db, ready["invoice_id"])["status"] == "sent"
        assert _payment(db)["outcome"] == "rejected"

    def test_paid_by_hand_first_is_reported_as_paid_twice(self, db, monkeypatch, ready):
        _start(db, monkeypatch, ready["invoice_id"])
        sql(db, "UPDATE invoices SET status = 'paid', paid_at = 'cash' WHERE id = ?",
            (ready["invoice_id"],))
        dispatch_event(_succeeded(1, ready["invoice_id"]), db_path=db,
                       settings=stripe_settings())
        assert _invoice(db, ready["invoice_id"])["paid_at"] == "cash"
        p = _payment(db)
        assert p["outcome"] == "paid_twice" and "refund one" in p["outcome_reason"]

    def test_cancelled_while_paying_is_rejected(self, db, monkeypatch, ready):
        _start(db, monkeypatch, ready["invoice_id"])
        sql(db, "UPDATE invoices SET status = 'cancelled' WHERE id = ?",
            (ready["invoice_id"],))
        dispatch_event(_succeeded(1, ready["invoice_id"]), db_path=db,
                       settings=stripe_settings())
        assert _invoice(db, ready["invoice_id"])["status"] == "cancelled"
        assert _payment(db)["outcome"] == "rejected"

    def test_not_ours_changes_nothing(self, db, monkeypatch, ready):
        _start(db, monkeypatch, ready["invoice_id"])
        before = _state(db)
        evt = _succeeded(1, ready["invoice_id"])
        evt["data"]["object"]["metadata"] = {}
        res = dispatch_event(evt, db_path=db, settings=stripe_settings())
        assert res.processed and res.error is None
        assert _state(db) == before

    def test_a_refund_is_recorded_and_the_invoice_stays_paid(self, db, monkeypatch, ready):
        _start(db, monkeypatch, ready["invoice_id"])
        dispatch_event(_succeeded(1, ready["invoice_id"]), db_path=db,
                       settings=stripe_settings())
        refund = event("charge.refunded", {
            "id": "ch_1", "object": "charge", "payment_intent": "pi_test_1",
            "amount": 25000, "amount_refunded": 5000}, event_id="evt_ref",
            account=SHOP_ACCOUNT)
        dispatch_event(refund, db_path=db, settings=stripe_settings())
        assert _payment(db)["refunded_cents"] == 5000
        assert _invoice(db, ready["invoice_id"])["status"] == "paid"
        out = cli(db, "shop", "invoice", "payments", ready["invoice_id"])
        assert "50.00 USD" in out.output and "paid_invoice" in out.output


    def test_an_older_refund_event_arriving_late_does_not_lower_it(self, db, monkeypatch, ready):
        _start(db, monkeypatch, ready["invoice_id"])
        dispatch_event(_succeeded(1, ready["invoice_id"]), db_path=db,
                       settings=stripe_settings())
        for evt_id, refunded in (("evt_ref_2", 8000), ("evt_ref_1", 5000)):
            dispatch_event(event("charge.refunded", {
                "id": "ch_1", "object": "charge", "payment_intent": "pi_test_1",
                "amount": 25000, "amount_refunded": refunded}, event_id=evt_id,
                account=SHOP_ACCOUNT), db_path=db, settings=stripe_settings())
        assert _payment(db)["refunded_cents"] == 8000


class TestTwiceAndOutOfOrder:
    """Stripe may deliver an event twice, two events for one payment, and
    in any order. The database must end the same."""

    def _run(self, db, monkeypatch, ready, events):
        _start(db, monkeypatch, ready["invoice_id"])
        for e in events:
            dispatch_event(e, db_path=db, settings=stripe_settings())
        return _state(db)

    def test_the_same_event_twice(self, tmp_path, monkeypatch):
        dbs = [new_db(tmp_path, f"t{i}.db") for i in range(2)]
        states = []
        for d, n in zip(dbs, (1, 2)):
            ids = seed_invoice(d)
            seed_account(d, ids["shop_id"])
            evt = _succeeded(1, ids["invoice_id"])
            states.append(self._run(d, monkeypatch, ids, [evt] * n))
        assert states[0] == states[1]

    def test_two_success_events_for_one_payment(self, db, monkeypatch, ready):
        once = self._run(db, monkeypatch, ready, [_succeeded(1, ready["invoice_id"])])
        dispatch_event(_succeeded(1, ready["invoice_id"], event_id="evt_pi_ok_2"),
                       db_path=db, settings=stripe_settings())
        assert _state(db) == once

    @pytest.mark.parametrize("order", ["fail_then_ok", "ok_then_fail"])
    def test_a_failure_and_a_success_in_either_order(self, tmp_path, monkeypatch, order):
        d = new_db(tmp_path, f"{order}.db")
        ids = seed_invoice(d)
        seed_account(d, ids["shop_id"])
        fail, ok = _failed(1, ids["invoice_id"]), _succeeded(1, ids["invoice_id"])
        events = [fail, ok] if order == "fail_then_ok" else [ok, fail]
        self._run(d, monkeypatch, ids, events)
        assert _invoice(d, ids["invoice_id"])["status"] == "paid"
        p = _payment(d)
        assert (p["status"], p["outcome"]) == ("succeeded", "paid_invoice")

    def test_a_failure_alone_records_the_reason(self, db, monkeypatch, ready):
        self._run(db, monkeypatch, ready, [_failed(1, ready["invoice_id"])])
        p = _payment(db)
        assert (p["status"], p["failure_message"]) == ("failed", "Your card was declined.")
        assert _invoice(db, ready["invoice_id"])["status"] == "sent"


class TestTheWebhookRoute:
    """End to end through ``/v1/billing/webhooks/stripe`` with Stripe's
    signature checked by the SDK, the provider set to ``stripe``."""

    def _client(self, db):
        app = create_app(db_path_override=db)
        app.dependency_overrides[api_settings] = lambda: stripe_settings(db_path=db)
        return TestClient(app, raise_server_exceptions=False)

    def test_a_signed_event_pays_the_invoice(self, db, monkeypatch, ready):
        _start(db, monkeypatch, ready["invoice_id"])
        freeze_webhook_clock(monkeypatch)
        payload, sig = signed(_succeeded(1, ready["invoice_id"]))
        r = self._client(db).post("/v1/billing/webhooks/stripe", content=payload,
                                  headers={"Stripe-Signature": sig})
        assert r.status_code == 200, r.text
        assert _invoice(db, ready["invoice_id"])["status"] == "paid"
        row = sql(db, "SELECT account, livemode FROM stripe_webhook_events")[0]
        assert (row["account"], row["livemode"]) == (SHOP_ACCOUNT, 0)

    def test_a_signature_301_seconds_old_is_refused(self, db, monkeypatch, ready):
        _start(db, monkeypatch, ready["invoice_id"])
        freeze_webhook_clock(monkeypatch)
        payload, sig = signed(_succeeded(1, ready["invoice_id"]),
                              timestamp=FROZEN_AT - 301)
        r = self._client(db).post("/v1/billing/webhooks/stripe", content=payload,
                                  headers={"Stripe-Signature": sig})
        assert r.status_code == 400
        assert _invoice(db, ready["invoice_id"])["status"] == "sent"

    def test_a_signature_299_seconds_old_is_accepted(self, db, monkeypatch, ready):
        """The control for the test above: the clock, not the secret, refused it."""
        _start(db, monkeypatch, ready["invoice_id"])
        freeze_webhook_clock(monkeypatch)
        payload, sig = signed(_succeeded(1, ready["invoice_id"]),
                              timestamp=FROZEN_AT - 299)
        r = self._client(db).post("/v1/billing/webhooks/stripe", content=payload,
                                  headers={"Stripe-Signature": sig})
        assert r.status_code == 200, r.text

    def test_another_secret_is_refused(self, db, monkeypatch, ready):
        _start(db, monkeypatch, ready["invoice_id"])
        freeze_webhook_clock(monkeypatch)
        payload, sig = signed(_succeeded(1, ready["invoice_id"]),
                              secret="whsec_" + "some0other0secret")
        r = self._client(db).post("/v1/billing/webhooks/stripe", content=payload,
                                  headers={"Stripe-Signature": sig})
        assert r.status_code == 400
        assert sql(db, "SELECT COUNT(*) FROM stripe_webhook_events")[0][0] == 0

    def test_a_live_event_is_refused_outside_prod(self, db, monkeypatch, ready):
        _start(db, monkeypatch, ready["invoice_id"])
        freeze_webhook_clock(monkeypatch)
        evt = _succeeded(1, ready["invoice_id"])
        evt["livemode"] = True
        payload, sig = signed(evt)
        r = self._client(db).post("/v1/billing/webhooks/stripe", content=payload,
                                  headers={"Stripe-Signature": sig})
        assert r.status_code == 400
        assert "row 371" in r.text
        assert _invoice(db, ready["invoice_id"])["status"] == "sent"
        assert sql(db, "SELECT COUNT(*) FROM stripe_webhook_events")[0][0] == 0


class TestTerminal:
    def test_setup_registers_the_simulated_reader_on_the_shops_account(self, db, monkeypatch, ready):
        http = answer(monkeypatch, [
            ("POST", r"/v1/terminal/locations", "terminal_location"),
            ("POST", r"/v1/terminal/readers", "terminal_reader"),
        ])
        out = cli(db, "shop", "terminal", "setup", "--shop", ready["shop_id"], "--simulated")
        assert out.exit_code == 0, out.output
        loc, reader = http.requests
        assert loc.headers["Stripe-Account"] == SHOP_ACCOUNT
        assert loc.params["address[state]"] == "MA"
        assert reader.params["registration_code"] == "simulated-wpe"
        assert reader.params["location"] == LOCATION
        row = sql(db, "SELECT stripe_reader_id, simulated FROM terminal_readers")[0]
        assert tuple(row) == (READER, 1)

    def test_setup_without_an_address_is_refused_before_stripe(self, db, monkeypatch):
        ids = seed_invoice(db, address=False)
        seed_account(db, ids["shop_id"])
        http = answer(monkeypatch, [])
        out = cli(db, "shop", "terminal", "setup", "--shop", ids["shop_id"], "--simulated")
        assert out.exit_code == 1
        assert "line1" in out.output
        assert http.requests == []

    def test_pay_sends_a_card_present_intent_and_presents_the_test_card(self, db, monkeypatch, ready):
        seed_reader(db, ready["shop_id"])
        http = answer(monkeypatch, [
            ("POST", r"/v1/payment_intents", "payment_intent_card_present"),
            ("POST", rf"/v1/terminal/readers/{READER}/process_payment_intent",
             "reader_processing"),
            ("POST", rf"/v1/test_helpers/terminal/readers/{READER}/present_payment_method",
             "reader_presented"),
        ])
        out = cli(db, "shop", "terminal", "pay", ready["invoice_id"])
        assert out.exit_code == 0, out.output
        pi, process, present = http.requests
        assert pi.params["allowed_payment_method_types[0]"] == "card_present"
        assert pi.params["amount"] == "25000"
        assert pi.params["capture_method"] == "automatic"
        assert pi.params["metadata[motodiag_payment_id]"] == "1"
        assert {r.headers["Stripe-Account"] for r in http.requests} == {SHOP_ACCOUNT}
        assert process.params["payment_intent"] == TERMINAL_PI
        assert "is not paid yet" in out.output
        assert _invoice(db, ready["invoice_id"])["status"] == "sent"

    def test_the_readers_success_event_pays_the_invoice(self, db, monkeypatch, ready):
        seed_reader(db, ready["shop_id"])
        answer(monkeypatch, [
            ("POST", r"/v1/payment_intents", "payment_intent_card_present"),
            ("POST", r".*/process_payment_intent", "reader_processing"),
            ("POST", r".*/present_payment_method", "reader_presented"),
        ])
        cli(db, "shop", "terminal", "pay", ready["invoice_id"])
        dispatch_event(_succeeded(1, ready["invoice_id"],
                                  pi_id=TERMINAL_PI),
                       db_path=db, settings=stripe_settings())
        assert _invoice(db, ready["invoice_id"])["status"] == "paid"
        assert _payment(db)["channel"] == "terminal"

    def test_another_intent_for_the_same_payment_is_rejected(self, db, monkeypatch, ready):
        seed_reader(db, ready["shop_id"])
        answer(monkeypatch, [
            ("POST", r"/v1/payment_intents", "payment_intent_card_present"),
            ("POST", r".*/process_payment_intent", "reader_processing"),
            ("POST", r".*/present_payment_method", "reader_presented"),
        ])
        cli(db, "shop", "terminal", "pay", ready["invoice_id"])
        res = dispatch_event(_succeeded(1, ready["invoice_id"], pi_id="pi_other"),
                             db_path=db, settings=stripe_settings())
        assert "PaymentEventRejected" in res.error
        assert _invoice(db, ready["invoice_id"])["status"] == "sent"

    def test_pay_without_a_reader_is_refused(self, db, monkeypatch, ready):
        http = answer(monkeypatch, [])
        out = cli(db, "shop", "terminal", "pay", ready["invoice_id"])
        assert out.exit_code == 1
        assert "shop terminal setup" in out.output
        assert http.requests == []
