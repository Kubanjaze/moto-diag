"""Phase 273 — 176's subscription billing against Stripe's current API (F187).

Each class is one of F187's defects:
- the user reaches the Subscription through ``subscription_data.metadata``;
- the billing period is read from the subscription's items;
- no tier or status is invented;
- events in any order end in Stripe's state, because the handler re-reads;
- a handler that could not read Stripe is retried, not recorded.
Plus the tier's payments (``invoice.paid`` / ``.payment_failed``).
"""

from __future__ import annotations

import copy

import pytest
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.api.routes.billing import get_provider
from motodiag.billing.providers import (
    BillingProviderError, FakeBillingProvider, StripeBillingProvider,
)
from motodiag.billing.subscription_repo import get_subscription_by_stripe_id
from motodiag.billing.webhook_handlers import dispatch_event
from motodiag.core.database import get_connection
from support.phase273 import answer, cli, new_db, sql
from support.stripe_fixtures import (
    body, event, stripe_settings, TEST_KEY, TEST_SECRET,
)

SUB = "sub_test_fixture273"


@pytest.fixture
def db(tmp_path):
    return new_db(tmp_path)


@pytest.fixture
def user(db):
    with get_connection(db) as conn:
        return conn.execute("INSERT INTO users (username) VALUES ('rider')").lastrowid


def _stripe_says(user_id, **changes) -> dict:
    sub = body("subscription_active")
    sub["metadata"]["user_id"] = str(user_id)
    sub.update(changes)
    return sub


def _sub_event(event_type, event_id, payload_status="active", user_id=None):
    """What the event carries. The handler must not trust its status."""
    obj = {"id": SUB, "object": "subscription", "status": payload_status,
           "customer": "cus_test_fixture273", "metadata": {}}
    if user_id is not None:
        obj["metadata"] = {"user_id": str(user_id), "tier": "shop"}
    return event(event_type, obj, event_id=event_id)


def _stored(db):
    row = get_subscription_by_stripe_id(SUB, db_path=db)
    return None if row is None else {k: row[k] for k in (
        "tier", "status", "stripe_price_id", "current_period_start",
        "current_period_end", "cancel_at_period_end", "canceled_at")}


class TestTheUserReachesTheSubscription:
    def test_checkout_puts_user_and_tier_in_subscription_data(self, monkeypatch):
        http = answer(monkeypatch, [("POST", r"/v1/checkout/sessions",
                                     "checkout_session_subscription")])
        provider = StripeBillingProvider(TEST_KEY, TEST_SECRET, settings=stripe_settings())
        result = provider.create_checkout_session(
            user_id=7, email="r@example.com", tier="shop",
            success_url="http://localhost/ok", cancel_url="http://localhost/no")
        p = http.requests[0].params
        assert p["subscription_data[metadata][user_id]"] == "7"
        assert p["subscription_data[metadata][tier]"] == "shop"
        assert p["metadata[user_id]"] == "7"
        assert p["line_items[0][price]"] == "price_test_shop"
        assert http.requests[0].headers["Stripe-Version"] == "2026-09-30.endive"
        assert result.checkout_url.startswith("https://checkout.stripe.com/")

    def test_a_first_event_finds_the_user_through_stripes_metadata(self, db, user):
        provider = FakeBillingProvider({SUB: _stripe_says(user)})
        res = dispatch_event(_sub_event("customer.subscription.created", "evt_1"),
                             db_path=db, provider=provider, settings=stripe_settings())
        assert res.error is None, res.error
        row = get_subscription_by_stripe_id(SUB, db_path=db)
        assert row["user_id"] == user and row["tier"] == "shop"

    def test_checkout_url_survives_a_narrow_terminal(self, db, monkeypatch, user):
        """Bug fix #1: 176's command printed the URL through rich, which
        wrapped Stripe's ~600-character Checkout URL at 80 columns."""
        session = body("checkout_session_subscription")
        session["url"] = "https://checkout.stripe.com/c/pay/cs_test_" + "x" * 560
        answer(monkeypatch, [("POST", r"/v1/checkout/sessions", (200, session))])
        out = cli(db, "subscription", "checkout-url", "--user", user, "--tier", "shop",
                  columns=80)
        assert out.exit_code == 0, out.output
        assert session["url"] in out.output.splitlines()

    def test_checkout_url_says_the_prices_are_placeholders(self, db, monkeypatch, user):
        answer(monkeypatch, [("POST", r"/v1/checkout/sessions",
                              "checkout_session_subscription")])
        out = cli(db, "subscription", "checkout-url", "--user", user, "--tier", "shop")
        assert out.exit_code == 0, out.output
        assert "test placeholders" in out.output


class TestThePeriodComesFromTheItems:
    def test_period_start_and_end_are_stored(self, db, user):
        provider = FakeBillingProvider({SUB: _stripe_says(user)})
        dispatch_event(_sub_event("customer.subscription.created", "evt_1"),
                       db_path=db, provider=provider, settings=stripe_settings())
        s = _stored(db)
        assert s["current_period_start"] == "2026-10-06T12:00:00+00:00"
        assert s["current_period_end"] == "2026-11-06T12:00:00+00:00"
        assert s["stripe_price_id"] == "price_test_shop"


class TestNothingIsInvented:
    def test_no_tier_metadata_reads_the_tier_from_the_price(self, db, user):
        sub = _stripe_says(user)
        sub["metadata"] = {"user_id": str(user)}
        sub["items"]["data"][0]["price"]["id"] = "price_test_company"
        dispatch_event(_sub_event("customer.subscription.created", "evt_1"), db_path=db,
                       provider=FakeBillingProvider({SUB: sub}), settings=stripe_settings())
        assert _stored(db)["tier"] == "company"

    def test_neither_tier_nor_known_price_writes_nothing_and_says_why(self, db, user):
        sub = _stripe_says(user)
        sub["metadata"] = {"user_id": str(user)}
        sub["items"]["data"][0]["price"]["id"] = "price_unknown"
        res = dispatch_event(_sub_event("customer.subscription.created", "evt_1"),
                             db_path=db, provider=FakeBillingProvider({SUB: sub}),
                             settings=stripe_settings())
        assert "none of the three configured tier prices" in res.error
        assert _stored(db) is None

    def test_no_status_writes_nothing(self, db, user):
        sub = _stripe_says(user)
        sub["status"] = None
        res = dispatch_event(_sub_event("customer.subscription.created", "evt_1"),
                             db_path=db, provider=FakeBillingProvider({SUB: sub}),
                             settings=stripe_settings())
        assert "has no status" in res.error
        assert _stored(db) is None

    def test_an_unknown_user_writes_nothing(self, db):
        sub = body("subscription_active")
        sub["metadata"] = {}
        res = dispatch_event(_sub_event("customer.subscription.created", "evt_1"),
                             db_path=db, provider=FakeBillingProvider({SUB: sub}),
                             settings=stripe_settings())
        assert "no user_id" in res.error
        assert _stored(db) is None


class TestOrderDoesNotMatter:
    def _deliver(self, db, events, truth):
        provider = FakeBillingProvider({SUB: truth})
        for e in events:
            dispatch_event(e, db_path=db, provider=provider, settings=stripe_settings())
        return _stored(db)

    def test_the_payload_status_is_not_trusted(self, db, user):
        stored = self._deliver(db, [_sub_event("customer.subscription.created", "evt_1",
                                               payload_status="active")],
                               _stripe_says(user, status="past_due"))
        assert stored["status"] == "past_due"

    def test_a_late_updated_does_not_revive_a_cancelled_subscription(self, tmp_path, user):
        canceled = _stripe_says(user, status="canceled", canceled_at=1791300000)
        results = []
        for name, order in (("a", ["created", "deleted", "updated"]),
                            ("b", ["created", "updated", "deleted"]),
                            ("c", ["deleted", "updated", "created"])):
            d = new_db(tmp_path, f"{name}.db")
            with get_connection(d) as conn:
                conn.execute("INSERT INTO users (id, username) VALUES (?, 'rider')", (user,))
            evts = [_sub_event(f"customer.subscription.{t}", f"evt_{t}",
                               payload_status="active") for t in order]
            results.append(self._deliver(d, evts, canceled))
        assert results[0] == results[1] == results[2]
        assert results[0]["status"] == "canceled"
        assert results[0]["canceled_at"] == "2026-10-06T15:20:00+00:00"

    def test_a_replay_runs_nothing(self, db, user):
        provider = FakeBillingProvider({SUB: _stripe_says(user)})
        evt = _sub_event("customer.subscription.created", "evt_1")
        first = dispatch_event(evt, db_path=db, provider=provider, settings=stripe_settings())
        provider.subscriptions[SUB] = _stripe_says(user, status="past_due")
        second = dispatch_event(evt, db_path=db, provider=provider, settings=stripe_settings())
        assert (first.processed, second.processed) == (True, False)
        assert _stored(db)["status"] == "active"


class TestRetriedWhenStripeCannotBeRead:
    def test_the_event_is_not_recorded_so_a_redelivery_is_applied(self, db, user):
        provider = FakeBillingProvider()  # Stripe has nothing to say yet
        evt = _sub_event("customer.subscription.created", "evt_1")
        first = dispatch_event(evt, db_path=db, provider=provider, settings=stripe_settings())
        assert first.retry and not first.processed
        assert sql(db, "SELECT COUNT(*) FROM stripe_webhook_events")[0][0] == 0
        provider.subscriptions[SUB] = _stripe_says(user)
        second = dispatch_event(evt, db_path=db, provider=provider, settings=stripe_settings())
        assert second.processed and second.error is None
        assert _stored(db)["status"] == "active"

    def test_the_route_answers_503(self, db, user):
        app = create_app(db_path_override=db)
        app.dependency_overrides[get_provider] = lambda: FakeBillingProvider()
        client = TestClient(app, raise_server_exceptions=False)
        import json
        r = client.post("/v1/billing/webhooks/stripe",
                        content=json.dumps(_sub_event("customer.subscription.created",
                                                      "evt_1")).encode(),
                        headers={"Stripe-Signature": FakeBillingProvider.FAKE_SIGNATURE})
        assert r.status_code == 503

    def test_stripe_down_through_the_real_provider_is_retried(self, db, monkeypatch, user):
        answer(monkeypatch, [("GET", rf"/v1/subscriptions/{SUB}", (500, {
            "error": {"type": "api_error", "message": "down"}}))])
        provider = StripeBillingProvider(TEST_KEY, TEST_SECRET, settings=stripe_settings())
        res = dispatch_event(_sub_event("customer.subscription.created", "evt_1"),
                             db_path=db, provider=provider, settings=stripe_settings())
        assert res.retry

    def test_the_real_provider_reads_the_subscription(self, db, monkeypatch, user):
        sub = _stripe_says(user)
        http = answer(monkeypatch, [("GET", rf"/v1/subscriptions/{SUB}", (200, sub))])
        provider = StripeBillingProvider(TEST_KEY, TEST_SECRET, settings=stripe_settings())
        res = dispatch_event(_sub_event("customer.subscription.updated", "evt_1"),
                             db_path=db, provider=provider, settings=stripe_settings())
        assert res.error is None, res.error
        assert _stored(db)["tier"] == "shop"
        assert http.requests[0].headers["Stripe-Version"] == "2026-09-30.endive"


class TestTheTiersPayments:
    def _invoice_event(self, etype, event_id, *, paid, invoice_id="in_1"):
        return event(etype, {
            "id": invoice_id, "object": "invoice", "currency": "usd",
            "amount_due": 4900, "amount_paid": 4900 if paid else 0,
            "livemode": False,
            "parent": {"type": "subscription_details",
                       "subscription_details": {"subscription": SUB}},
            "lines": {"data": [{"period": {"start": 1791288000, "end": 1793966400}}]},
        }, event_id=event_id)

    def _subscribed(self, db, user):
        dispatch_event(_sub_event("customer.subscription.created", "evt_sub"),
                       db_path=db, provider=FakeBillingProvider({SUB: _stripe_says(user)}),
                       settings=stripe_settings())

    def test_paid_is_recorded_in_cents_once(self, db, user):
        self._subscribed(db, user)
        evt = self._invoice_event("invoice.paid", "evt_paid", paid=True)
        for _ in range(2):
            dispatch_event(evt, db_path=db, settings=stripe_settings())
        rows = sql(db, "SELECT status, amount_paid_cents, currency, period_end "
                       "FROM subscription_payments")
        assert [tuple(r) for r in rows] == [
            ("paid", 4900, "usd", "2026-11-06T12:00:00+00:00")]

    def test_a_late_failure_never_overwrites_a_payment(self, db, user):
        self._subscribed(db, user)
        dispatch_event(self._invoice_event("invoice.paid", "evt_paid", paid=True),
                       db_path=db, settings=stripe_settings())
        dispatch_event(self._invoice_event("invoice.payment_failed", "evt_fail", paid=False),
                       db_path=db, settings=stripe_settings())
        row = sql(db, "SELECT status, amount_paid_cents FROM subscription_payments")[0]
        assert tuple(row) == ("paid", 4900)

    def test_an_invoice_before_its_subscription_reads_the_subscription(self, db, user):
        """Bug fix #2: in the smoke run `invoice.paid` came before
        `customer.subscription.created`; the 503 waited for a redelivery
        `stripe listen` never makes. The handler now reads the subscription
        from Stripe itself."""
        provider = FakeBillingProvider({SUB: _stripe_says(user)})
        res = dispatch_event(self._invoice_event("invoice.paid", "evt_paid", paid=True),
                             db_path=db, provider=provider, settings=stripe_settings())
        assert res.error is None and not res.retry, res.error
        assert _stored(db)["status"] == "active"
        rows = sql(db, "SELECT status, amount_paid_cents FROM subscription_payments")
        assert [tuple(r) for r in rows] == [("paid", 4900)]
        # The subscription event that follows changes nothing it should not.
        dispatch_event(_sub_event("customer.subscription.created", "evt_sub"),
                       db_path=db, provider=provider, settings=stripe_settings())
        assert sql(db, "SELECT COUNT(*) FROM subscriptions WHERE stripe_subscription_id = ?",
                   (SUB,))[0][0] == 1

    def test_an_invoice_before_its_subscription_with_stripe_down_is_retried(self, db, user):
        res = dispatch_event(self._invoice_event("invoice.paid", "evt_paid", paid=True),
                             db_path=db, provider=FakeBillingProvider(),
                             settings=stripe_settings())
        assert res.retry
        assert sql(db, "SELECT COUNT(*) FROM subscription_payments")[0][0] == 0


class TestSync:
    def test_sync_stores_what_stripe_says(self, db, monkeypatch, user):
        provider = FakeBillingProvider({SUB: _stripe_says(user)})
        dispatch_event(_sub_event("customer.subscription.created", "evt_1"),
                       db_path=db, provider=provider, settings=stripe_settings())
        answer(monkeypatch, [("GET", rf"/v1/subscriptions/{SUB}",
                              (200, _stripe_says(user, cancel_at_period_end=True)))])
        out = cli(db, "subscription", "sync", "--user", user)
        assert out.exit_code == 0, out.output
        assert _stored(db)["cancel_at_period_end"] == 1


class TestTheFakeProvider:
    def test_an_unknown_subscription_raises_as_stripe_would(self):
        with pytest.raises(BillingProviderError):
            FakeBillingProvider().retrieve_subscription("sub_nope")

    def test_it_returns_what_it_was_given(self):
        sub = {"id": "sub_x", "status": "active"}
        assert FakeBillingProvider({"sub_x": copy.deepcopy(sub)}).retrieve_subscription(
            "sub_x") == sub
