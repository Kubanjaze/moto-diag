"""Phase 371, Logic item 4 — the daily limit check and its notice (K65 (2)).

Each of the four lines at, above and below its number; once ever for the
two shop-count lines, once per UTC day for the other two, across a
restart (the rows in ``stripe_feed_notices``); the guide's page in every
notice; the fake sender's events equal to the rows; the ``NullSender``
path. Scratch databases only.
"""

from __future__ import annotations

import logging

import pytest
from support.phase273 import new_db, sql
from support.stripe_fixtures import FROZEN_AT, stripe_settings

from motodiag.core.database import get_connection
from motodiag.core.timestamps import utc_day
from motodiag.payments import event_feed as feed
from motodiag.telemetry.sender import NullSender

DAY = 86400


class FakeSender:
    enabled = True
    environment = "test"
    server_name = "bench"

    def __init__(self):
        self.events: list[dict] = []

    def capture(self, event):
        self.events.append(event)
        return True


@pytest.fixture
def db(tmp_path):
    return new_db(tmp_path)


def _shops(db, n):
    with get_connection(db) as conn:
        for i in range(n):
            shop = conn.execute("INSERT INTO shops (name) VALUES (?)", (f"S{i}",)).lastrowid
            conn.execute(
                "INSERT INTO shop_payment_accounts (shop_id, stripe_account_id, "
                "dashboard, fees_collector, losses_collector, country, currency) "
                "VALUES (?, ?, 'full', 'stripe', 'stripe', 'us', 'usd')",
                (shop, f"acct_s{i}"))


def _check(db, sender, *, at=FROZEN_AT, lag=0.0, refusals=0):
    day = feed.DayStats(utc_day(at), max_lag_s=lag, refusals=refusals)
    return feed.limit_check(stripe_settings(), db, day, sender, lambda: float(at))


def _rows(db):
    return [dict(r) for r in sql(db, "SELECT * FROM stripe_feed_notices ORDER BY id")]


class TestShopCounts:
    def test_49_shops_send_nothing(self, db):
        _shops(db, 49)
        assert _check(db, FakeSender()) == []

    def test_50_shops_send_the_plan_notice_once_ever(self, db):
        _shops(db, 50)
        s = FakeSender()
        assert _check(db, s) == ["shops_plan"]
        assert _check(db, s, at=FROZEN_AT + DAY) == []
        assert [r["line"] for r in _rows(db)] == ["shops_plan"]

    def test_100_shops_send_the_upgrade_notice_once(self, db):
        _shops(db, 100)
        s = FakeSender()
        assert _check(db, s) == ["shops_plan", "shops_upgrade"]
        assert _check(db, FakeSender(), at=FROZEN_AT + 2 * DAY) == []

    def test_live_shops_do_not_count_under_a_test_key(self, db):
        _shops(db, 50)
        sql(db, "UPDATE shop_payment_accounts SET livemode = 1 WHERE stripe_account_id = 'acct_s0'")
        assert _check(db, FakeSender()) == []


class TestLateness:
    @pytest.mark.parametrize("lag,sent", [(119, []), (120, []), (121, ["news_late"])])
    def test_more_than_2_minutes_late_sends(self, db, lag, sent):
        assert _check(db, FakeSender(), lag=lag) == sent

    def test_once_a_day(self, db):
        assert _check(db, FakeSender(), lag=200) == ["news_late"]
        assert _check(db, FakeSender(), at=FROZEN_AT + 60, lag=300) == []
        assert _check(db, FakeSender(), at=FROZEN_AT + DAY, lag=300) == ["news_late"]


class TestRefusals:
    def test_a_refusal_sends_once_a_day_and_again_the_next(self, db):
        assert _check(db, FakeSender(), refusals=1) == ["stripe_refused"]
        assert _check(db, FakeSender(), at=FROZEN_AT + 60, refusals=3) == []
        assert _check(db, FakeSender(), at=FROZEN_AT + DAY, refusals=1) == ["stripe_refused"]

    def test_no_refusal_sends_nothing(self, db):
        assert _check(db, FakeSender(), refusals=0) == []


class TestTheNotice:
    def test_every_notice_names_the_guide_and_the_sender_holds_the_rows(self, db):
        _shops(db, 100)
        s = FakeSender()
        sent = _check(db, s, lag=500, refusals=2)
        assert sent == ["shops_plan", "shops_upgrade", "news_late", "stripe_refused"]
        rows = _rows(db)
        assert [r["detail"] for r in rows] == [e["message"]["formatted"] for e in s.events]
        assert all("docs/guide/payments.md" in r["detail"] for r in rows)
        assert all(e["level"] == "warning" for e in s.events)
        assert all(r["delivered"] == 1 for r in rows)
        assert rows[0]["sent_at"].startswith(utc_day(FROZEN_AT))

    def test_the_plan_text(self, db):
        _shops(db, 50)
        _check(db, FakeSender())
        assert _rows(db)[0]["detail"] == (
            "Payments feed: 50 shops are connected; time to start planning the "
            "upgrade. See docs/guide/payments.md, 'When it is time to upgrade'.")

    def test_with_no_dsn_the_row_is_written_undelivered_and_logged(self, db, caplog):
        with caplog.at_level(logging.WARNING, logger="motodiag.payments.feed"):
            assert _check(db, NullSender(), refusals=1) == ["stripe_refused"]
        assert _rows(db)[0]["delivered"] == 0
        assert "Stripe refused or rate-limited 1 asks" in caplog.text


class TestStoredTimesCompareParsed:
    """core/timestamps.py's rule: a stored time is compared parsed, never
    as text. Each planted row's text says the other thing."""

    def _plant(self, db, sent_at):
        with get_connection(db) as conn:
            conn.execute("INSERT INTO stripe_feed_notices (line, sent_at, detail, "
                         "delivered) VALUES ('stripe_refused', ?, 'x', 1)", (sent_at,))

    def test_a_notice_at_an_offset_counts_on_its_utc_day(self, db):
        # 20:00 at -05:00 on the day before is 01:00 UTC on FROZEN_AT's day.
        prev = utc_day(FROZEN_AT - DAY)
        self._plant(db, f"{prev}T20:00:00.000-05:00")
        assert feed.already_sent(db, "stripe_refused", utc_day(FROZEN_AT + 3600))
        assert not feed.already_sent(db, "stripe_refused", prev)

    def test_a_notice_in_sqlites_shape_is_inside_the_window(self, db):
        day = utc_day(FROZEN_AT)
        self._plant(db, f"{day} 12:00:00")
        assert len(feed.notices_since(db, f"{day}T11:00:00.000+00:00")) == 1
        assert feed.notices_since(db, f"{day}T13:00:00.000+00:00") == []


class TestTheJobsDay:
    def test_the_check_runs_at_start_and_on_a_new_days_first_round(self, db, monkeypatch):
        calls: list[str] = []
        monkeypatch.setattr(feed, "limit_check",
                            lambda s, d, day, sender, clock: calls.append(day.day) or [])
        monkeypatch.setattr(feed, "poll_once", lambda *a: [])
        now = [float(FROZEN_AT)]
        waits: list[float] = []

        def sleep(s):
            waits.append(s)
            now[0] += DAY / 2

        feed.run_forever(stripe_settings(), db, clock=lambda: now[0], sleep=sleep,
                         stop=lambda: len(waits) >= 4, sender=FakeSender())
        d0 = utc_day(FROZEN_AT)
        assert calls[0] == d0
        assert len(calls) == 3  # start, then the first round of each new day
