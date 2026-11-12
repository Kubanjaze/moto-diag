"""Phase 371, Logic item 3 — the alarm's check-in to a Sentry job monitor.

The URL from the documentation's example DSN; the body's schedule and
margin; the key once, in the URL (Phase 371B, F273: Sentry refuses it sent
twice); the answers; check-ins at 300-second steps under
an injected clock and none without a DSN; no key in a log line. A fake
transport takes every post: nothing reaches the network.
"""

from __future__ import annotations

import json
import logging

import pytest
from support.phase273 import answer, new_db
from support.phase371 import DSN_TEXT, PLANTED_DSN_KEY, ask
from support.stripe_fixtures import FROZEN_AT, stripe_settings

from motodiag.payments import event_feed as feed
from motodiag.telemetry import monitor
from motodiag.telemetry.dsn import parse_dsn

DOC_DSN = "https://examplePublicKey@o0.ingest.sentry.io/0"


class FakeTransport:
    def __init__(self, answer=(202, "Accepted", {}), raises=None):
        self.answer, self.raises = answer, raises
        self.posts: list[tuple[str, dict, dict]] = []

    def __call__(self, url, headers, body):
        self.posts.append((url, headers, json.loads(body)))
        if self.raises:
            raise self.raises
        return self.answer


def test_the_url_from_the_documentations_dsn():
    assert monitor.checkin_url(parse_dsn(DOC_DSN), "motodiag-payments-feed") == (
        "https://o0.ingest.sentry.io/api/0/cron/motodiag-payments-feed/examplePublicKey/")


def test_the_post_carries_the_key_once_and_the_schedule():
    t = FakeTransport()
    assert monitor.checkin(parse_dsn(DOC_DSN), "motodiag-payments-feed", t,
                           interval_minutes=5) is True
    url, headers, body = t.posts[0]
    assert url.endswith("/cron/motodiag-payments-feed/examplePublicKey/")
    assert headers == {"Content-Type": "application/json"}
    assert body["status"] == "ok"
    cfg = body["monitor_config"]
    assert cfg["schedule"] == {"type": "interval", "value": 5, "unit": "minute"}
    assert cfg["checkin_margin"] == 10
    assert cfg["timezone"] == "UTC"


def test_a_401_returns_false_and_is_logged_naming_it(caplog):
    t = FakeTransport(answer=(401, "Unauthorized", {}))
    with caplog.at_level(logging.WARNING, logger="motodiag.telemetry.monitor"):
        assert monitor.checkin(parse_dsn(DSN_TEXT), "s", t, interval_minutes=5) is False
    assert "401" in caplog.text and "o0.ingest.sentry.io" in caplog.text
    assert PLANTED_DSN_KEY not in caplog.text


def test_an_oserror_returns_false_and_raises_nothing(caplog):
    t = FakeTransport(raises=ConnectionRefusedError("refused"))
    with caplog.at_level(logging.WARNING, logger="motodiag.telemetry.monitor"):
        assert monitor.checkin(parse_dsn(DSN_TEXT), "s", t, interval_minutes=5) is False
    assert "ConnectionRefusedError" in caplog.text
    assert PLANTED_DSN_KEY not in caplog.text


def test_control_a_logged_url_shows_the_key(caplog):
    url = monitor.checkin_url(parse_dsn(DSN_TEXT), "s")
    with caplog.at_level(logging.WARNING, logger="motodiag.telemetry.monitor"):
        logging.getLogger("motodiag.telemetry.monitor").warning("posting %s", url)
    assert PLANTED_DSN_KEY in caplog.text


class _NoSender:
    enabled = False
    environment = "test"
    server_name = "bench"

    def capture(self, event):
        return False


@pytest.mark.parametrize("dsn,expected", [(DSN_TEXT, [0, 300, 600]), ("", [])])
def test_run_forever_checks_in_at_300_second_steps(tmp_path, monkeypatch, dsn, expected):
    db = new_db(tmp_path)
    rounds = 31  # 20 seconds apart: 0 .. 600
    answer(monkeypatch, [ask()] * rounds)
    now = [float(FROZEN_AT)]
    waits: list[float] = []
    t = FakeTransport()
    times: list[float] = []

    def transport(url, headers, body):
        times.append(now[0] - FROZEN_AT)
        return t(url, headers, body)

    def sleep(s):
        waits.append(s)
        now[0] += s

    feed.run_forever(stripe_settings(sentry_dsn=dsn), db, clock=lambda: now[0],
                     sleep=sleep, stop=lambda: len(waits) >= rounds,
                     sender=_NoSender(), transport=transport)
    assert times == expected
    assert all(p[0].endswith(f"/{PLANTED_DSN_KEY}/") for p in t.posts)
