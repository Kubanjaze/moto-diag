"""Phase 371, Logic item 2 — the payments feed asks Stripe for its news.

Stripe answers through :class:`FixtureHTTP`, each ask a ``(status, body)``
tuple whose body is an events-list page built from Stripe's documented
list shape (docs.stripe.com/api/events/list) in ``support/phase371.py``.
Every database is a scratch one; nothing reaches the network.
"""

from __future__ import annotations

import logging

import pytest
from support.phase273 import answer, new_db, seed_account, seed_invoice, sql
from support.phase371 import (
    ask,
    busy,
    started_payment,
    succeeded,
)
from support.stripe_fixtures import (
    FROZEN_AT,
    SHOP_ACCOUNT,
    TEST_KEY,
    stripe_settings,
)

from motodiag.billing import webhook_handlers
from motodiag.billing.webhook_handlers import HANDLERS, WebhookDispatchResult
from motodiag.payments import event_feed as feed

NOW = FROZEN_AT + 10


def clock() -> float:
    return float(NOW)


@pytest.fixture
def db(tmp_path):
    return new_db(tmp_path)


def _types(params: dict) -> list[str]:
    return [params[f"types[{i}]"] for i in range(len(feed.FEED_TYPES))
            if f"types[{i}]" in params]


def _cursor(db, account):
    rows = sql(db, "SELECT * FROM stripe_event_cursors WHERE account = ?", (account,))
    return dict(rows[0]) if rows else None


def _set_place(db, account, created):
    feed.write_cursor(db, account, last_created=created, last_event_id=None,
                      polled_at=feed.stamp(NOW), last_error=None, livemode=0)


class TestTheTypes:
    def test_the_feed_asks_for_exactly_the_handlers_types(self):
        assert feed.FEED_TYPES == tuple(HANDLERS.keys())
        assert len(feed.FEED_TYPES) == 8

    def test_control_a_planted_ninth_type_turns_the_equality_red(self, monkeypatch):
        monkeypatch.setitem(HANDLERS, "planted.ninth", HANDLERS["invoice.paid"])
        assert feed.FEED_TYPES != tuple(HANDLERS.keys())


class TestAccounts:
    def test_platform_then_the_shops_of_the_keys_mode_by_shop(self, db):
        a = seed_invoice(db)
        b = seed_invoice(db, shop_name="Second")
        c = seed_invoice(db, shop_name="Live one")
        seed_account(db, b["shop_id"], account="acct_second")
        seed_account(db, a["shop_id"], account="acct_first")
        seed_account(db, c["shop_id"], account="acct_live")
        sql(db, "UPDATE shop_payment_accounts SET livemode = 1 "
                "WHERE stripe_account_id = 'acct_live'")
        s = stripe_settings()
        assert feed.accounts(s, db) == ["platform", "acct_first", "acct_second"]
        live = stripe_settings(stripe_api_key="sk_live_" + "planted371")
        assert feed.accounts(live, db) == ["platform", "acct_live"]


class TestTheAsks:
    def test_one_round_asks_the_platform_then_the_shop(self, db, monkeypatch):
        ids = seed_invoice(db)
        seed_account(db, ids["shop_id"])
        _set_place(db, "platform", FROZEN_AT - 1000)
        _set_place(db, SHOP_ACCOUNT, FROZEN_AT - 2000)
        http = answer(monkeypatch, [ask(), ask()])
        results = feed.poll_once(stripe_settings(), db, clock)
        assert [r.account for r in results] == ["platform", SHOP_ACCOUNT]
        plat, shop = http.requests
        assert (plat.method, plat.path) == ("GET", "/v1/events")
        assert plat.params["created[gte]"] == str(FROZEN_AT - 1000 - 300)
        assert shop.params["created[gte]"] == str(FROZEN_AT - 2000 - 300)
        assert _types(plat.params) == list(feed.FEED_TYPES)
        assert _types(shop.params) == list(feed.FEED_TYPES)
        assert plat.params["limit"] == "100"
        assert "Stripe-Account" not in plat.headers
        assert shop.headers["Stripe-Account"] == SHOP_ACCOUNT

    def test_with_no_place_the_first_ask_is_the_overlap_before_now(self, db, monkeypatch):
        http = answer(monkeypatch, [ask()])
        feed.poll_once(stripe_settings(), db, clock)
        assert http.requests[0].params["created[gte]"] == str(NOW - 300)
        assert _cursor(db, "platform")["last_created"] == NOW

    def test_two_pages_are_followed_with_starting_after(self, db, monkeypatch):
        first = [succeeded(9, 9, event_id=f"evt_p1_{i}") for i in range(2)]
        for e in first:
            e["type"] = "invoice.payment_failed"
            e["data"]["object"] = {"id": "in_x", "object": "invoice"}
        http = answer(monkeypatch, [ask(first, has_more=True), ask()])
        feed.poll_once(stripe_settings(), db, clock)
        assert "starting_after" not in http.requests[0].params
        assert http.requests[1].params["starting_after"] == "evt_p1_1"
        assert http.requests[1].params["created[gte]"] == http.requests[0].params["created[gte]"]


class TestThePayment:
    def test_an_event_without_account_pays_the_invoice(self, db, monkeypatch):
        ids = started_payment(db, monkeypatch)
        evt = succeeded(1, ids["invoice_id"])
        assert "account" not in evt
        answer(monkeypatch, [ask(), ask([evt])])
        results = feed.poll_once(stripe_settings(), db, clock)
        assert (results[1].seen, results[1].handled) == (1, 1)
        assert results[1].lag_s == pytest.approx(10)
        inv = sql(db, "SELECT status FROM invoices WHERE id = ?", (ids["invoice_id"],))[0]
        assert inv["status"] == "paid"
        cur = _cursor(db, SHOP_ACCOUNT)
        assert (cur["last_created"], cur["last_error"]) == (NOW, None)

    def test_control_without_the_shops_id_written_in_the_payment_is_rejected(
            self, db, monkeypatch):
        ids = started_payment(db, monkeypatch)
        evt = succeeded(1, ids["invoice_id"])
        webhook_handlers.dispatch_event(evt, db_path=db, settings=stripe_settings())
        inv = sql(db, "SELECT status FROM invoices WHERE id = ?", (ids["invoice_id"],))[0]
        assert inv["status"] == "sent"

    def test_the_repeat_next_round_is_acknowledged_and_changes_nothing(
            self, db, monkeypatch):
        ids = started_payment(db, monkeypatch)
        evt = succeeded(1, ids["invoice_id"])
        answer(monkeypatch, [ask(), ask([evt]), ask(), ask([dict(evt)])])
        feed.poll_once(stripe_settings(), db, clock)
        before = sql(db, "SELECT * FROM invoice_payments")
        results = feed.poll_once(stripe_settings(), db, clock)
        assert (results[1].seen, results[1].handled) == (1, 0)
        assert [dict(r) for r in sql(db, "SELECT * FROM invoice_payments")] == [
            dict(r) for r in before]

    def test_the_restore_asks_again_and_nothing_is_paid_twice(self, db, monkeypatch):
        ids = started_payment(db, monkeypatch)
        evt = succeeded(1, ids["invoice_id"])
        http = answer(monkeypatch, [ask(), ask([evt]), ask(), ask([dict(evt)])])
        feed.poll_once(stripe_settings(), db, clock)
        _set_place(db, SHOP_ACCOUNT, FROZEN_AT - 3600)  # the backup's place
        feed.poll_once(stripe_settings(), db, clock)
        assert http.requests[3].params["created[gte]"] == str(FROZEN_AT - 3600 - 300)
        assert sql(db, "SELECT status FROM invoices WHERE id = ?",
                   (ids["invoice_id"],))[0]["status"] == "paid"
        assert len(sql(db, "SELECT * FROM invoice_payments")) == 1
        assert _cursor(db, SHOP_ACCOUNT)["last_created"] == FROZEN_AT

    def test_an_older_event_never_moves_the_place_back(self, db, monkeypatch):
        _set_place(db, "platform", FROZEN_AT)
        old = succeeded(9, 9, event_id="evt_old", created=FROZEN_AT - 100)
        answer(monkeypatch, [ask([old])])
        feed.poll_once(stripe_settings(), db, clock)
        assert _cursor(db, "platform")["last_created"] == FROZEN_AT


class TestThePlace:
    def test_a_place_40_days_old_is_asked_at_30_days_and_says_so(self, db, monkeypatch):
        _set_place(db, "platform", NOW - 40 * 86400)
        http = answer(monkeypatch, [ask()])
        results = feed.poll_once(stripe_settings(), db, clock)
        assert http.requests[0].params["created[gte]"] == str(NOW - 30 * 86400)
        cur = _cursor(db, "platform")
        assert "30 days" in cur["last_error"]
        assert results[0].error_kind == "gap"

    def test_a_retry_leaves_the_place_where_it_was(self, db, monkeypatch):
        _set_place(db, "platform", FROZEN_AT - 1000)
        evt = succeeded(9, 9, event_id="evt_retry")

        def retry(event, **kw):
            return WebhookDispatchResult(True, False, event["id"], event["type"],
                                         error="BillingProviderError: x", retry=True)

        monkeypatch.setattr(feed, "dispatch_event", retry)
        answer(monkeypatch, [ask([evt])])
        results = feed.poll_once(stripe_settings(), db, clock)
        assert _cursor(db, "platform")["last_created"] == FROZEN_AT - 1000
        assert results[0].error_kind == "retry"

    def test_control_a_clean_dispatch_moves_the_place(self, db, monkeypatch):
        _set_place(db, "platform", FROZEN_AT - 1000)
        evt = succeeded(9, 9, event_id="evt_clean")
        answer(monkeypatch, [ask([evt])])
        feed.poll_once(stripe_settings(), db, clock)
        cur = _cursor(db, "platform")
        assert (cur["last_created"], cur["last_event_id"]) == (FROZEN_AT, "evt_clean")

    def test_a_live_event_under_dev_is_recorded_and_the_round_finishes(
            self, db, monkeypatch):
        ids = seed_invoice(db)
        seed_account(db, ids["shop_id"])
        live = succeeded(9, 9, event_id="evt_live", livemode=True)
        answer(monkeypatch, [ask([live]), ask()])
        results = feed.poll_once(stripe_settings(), db, clock)
        assert [r.account for r in results] == ["platform", SHOP_ACCOUNT]
        assert results[0].error_kind == "live_event"
        assert "evt_live" in _cursor(db, "platform")["last_error"]
        assert sql(db, "SELECT count(*) FROM stripe_webhook_events")[0][0] == 0

    def test_one_accounts_refusal_does_not_stop_the_others(self, db, monkeypatch):
        from support.phase371 import refused
        ids = seed_invoice(db)
        seed_account(db, ids["shop_id"])
        answer(monkeypatch, [refused(), ask()])
        results = feed.poll_once(stripe_settings(), db, clock)
        assert [r.error_kind for r in results] == ["refused", None]
        assert "Stripe refused the key" in _cursor(db, "platform")["last_error"]
        assert _cursor(db, SHOP_ACCOUNT)["last_error"] is None


class TestTheWait:
    def _run(self, db, monkeypatch, expected, rounds):
        answer(monkeypatch, expected)
        waits: list[float] = []
        feed.run_forever(stripe_settings(), db, clock=clock, sleep=waits.append,
                         stop=lambda: len(waits) >= rounds,
                         sender=_NoSender())
        return waits

    def test_busy_doubles_the_wait_and_a_clean_round_restores_it(self, db, monkeypatch):
        waits = self._run(db, monkeypatch, [busy(), busy(), ask()], 3)
        assert waits == [40, 80, 20]

    def test_the_wait_stops_at_300_seconds(self, db, monkeypatch):
        waits = self._run(db, monkeypatch, [busy()] * 6, 6)
        assert waits == [40, 80, 160, 300, 300, 300]

    def test_a_round_that_raises_is_logged_and_the_loop_goes_on(
            self, db, monkeypatch, caplog):
        calls = []

        def broken(*a, **k):
            calls.append(1)
            raise RuntimeError("planted")

        monkeypatch.setattr(feed, "poll_once", broken)
        waits: list[float] = []
        with caplog.at_level(logging.ERROR, logger="motodiag.payments.feed"):
            feed.run_forever(stripe_settings(), db, clock=clock, sleep=waits.append,
                             stop=lambda: len(waits) >= 2, sender=_NoSender())
        assert len(calls) == 2 and waits == [20, 20]
        assert "the round failed" in caplog.text


class _NoSender:
    enabled = False
    environment = "test"
    server_name = "bench"

    def capture(self, event):
        return False


class TestNoKeyInTheLog:
    def test_no_key_appears_in_any_record(self, db, monkeypatch, caplog):
        ids = started_payment(db, monkeypatch)
        answer(monkeypatch, [ask(), ask([succeeded(1, ids["invoice_id"])])])
        with caplog.at_level(logging.DEBUG):
            feed.poll_once(stripe_settings(), db, clock)
        assert caplog.records
        assert TEST_KEY not in caplog.text
        assert "evt_feed_ok" in caplog.text

    def test_control_a_logged_key_is_seen(self, caplog):
        with caplog.at_level(logging.INFO):
            logging.getLogger("motodiag.payments.feed").info("key %s", TEST_KEY)
        assert TEST_KEY in caplog.text
