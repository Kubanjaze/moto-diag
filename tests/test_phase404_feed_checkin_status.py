"""Phase 404, Logic item 4 (F274) — a payments status that tells the truth.

The feed records each check-in's outcome in ``stripe_feed_checkins``;
``payments feed status`` names the last check-in's time and Sentry's
answer, and exits 1 when the alarm has never checked in, the last check-in
was refused, or none was accepted within two check-in intervals. With the
alarm off nothing changes (the control). ``feed run --once`` prints what it
printed before. A stand-in transport takes every check-in; Stripe answers
through ``FixtureHTTP``; no planted key appears anywhere.
"""

from __future__ import annotations

import time

import pytest
from support.phase273 import STRIPE_ENV, answer, cli, new_db, seed_account, seed_invoice, sql
from support.phase371 import DSN_TEXT, PLANTED_DSN_KEY, ask
from support.stripe_fixtures import FROZEN_AT, SHOP_ACCOUNT, TEST_KEY, TEST_SECRET, stripe_settings

from motodiag.core.timestamps import utc_at
from motodiag.payments import event_feed as feed
from motodiag.telemetry import monitor
from motodiag.telemetry.dsn import parse_dsn

ALARM_ENV = {**STRIPE_ENV, "MOTODIAG_SENTRY_DSN": DSN_TEXT}


class StandIn:
    """Sentry's ingest server, answering ``answer`` or raising ``raises``."""

    def __init__(self, answer=(202, "Accepted", {}), raises=None):
        self.answer, self.raises = answer, raises
        self.urls: list[str] = []

    def __call__(self, url, headers, body):
        self.urls.append(url)
        if self.raises:
            raise self.raises
        return self.answer


class _NoSender:
    enabled = False
    environment = "test"
    server_name = "bench"

    def capture(self, event):
        return False


@pytest.fixture
def db(tmp_path):
    path = new_db(tmp_path)
    seed_account(path, seed_invoice(path)["shop_id"])
    return path


def _run_once(db, monkeypatch, sentry: StandIn) -> None:
    """The job, one round and one check-in, on the real clock."""
    answer(monkeypatch, [ask(), ask()])
    rounds: list[float] = []
    feed.run_forever(stripe_settings(sentry_dsn=DSN_TEXT), db, clock=time.time,
                     sleep=rounds.append, stop=lambda: len(rounds) >= 1,
                     sender=_NoSender(), transport=sentry)
    assert len(sentry.urls) == 1


def _rows(db) -> list[tuple]:
    rows = sql(db, "SELECT ok, answer, slug FROM stripe_feed_checkins ORDER BY id")
    return [tuple(r) for r in rows]


# ---------------------------------------------------------------------------
# The answer comes back
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("transport,expected", [
    (StandIn((202, "Accepted", {})), (True, "202 Accepted")),
    (StandIn((401, "Unauthorized", {})), (False, "401 Unauthorized")),
    (StandIn(raises=ConnectionRefusedError("refused")), (False, "ConnectionRefusedError")),
])
def test_checkin_answer_returns_sentrys_answer(transport, expected):
    got = monitor.checkin_answer(parse_dsn(DSN_TEXT), "s", transport, interval_minutes=5)
    assert (got.ok, got.answer) == expected
    assert PLANTED_DSN_KEY not in got.answer


def test_checkin_still_returns_a_bool():
    assert monitor.checkin(parse_dsn(DSN_TEXT), "s", StandIn(), interval_minutes=5) is True
    assert monitor.checkin(parse_dsn(DSN_TEXT), "s", StandIn((401, "Unauthorized", {})),
                           interval_minutes=5) is False


# ---------------------------------------------------------------------------
# The record
# ---------------------------------------------------------------------------


def test_the_job_records_each_checkin(db, monkeypatch):
    _run_once(db, monkeypatch, StandIn((401, "Unauthorized", {})))
    assert _rows(db) == [(0, "401 Unauthorized", "motodiag-payments-feed")]


def test_the_job_writes_nothing_with_the_alarm_off(db, monkeypatch):
    answer(monkeypatch, [ask(), ask()])
    rounds: list[float] = []
    sentry = StandIn()
    feed.run_forever(stripe_settings(sentry_dsn=""), db, clock=time.time,
                     sleep=rounds.append, stop=lambda: len(rounds) >= 1,
                     sender=_NoSender(), transport=sentry)
    assert sentry.urls == [] and _rows(db) == []


def test_no_key_is_stored(db, monkeypatch):
    _run_once(db, monkeypatch, StandIn())
    dump = repr(sql(db, "SELECT * FROM stripe_feed_checkins"))
    assert PLANTED_DSN_KEY not in dump


def test_rows_older_than_30_days_go_at_the_days_turn(db, monkeypatch):
    day = 86400.0
    now = [float(FROZEN_AT)]
    for age_days, ok in ((31, 1), (30.5, 0), (29, 1), (1, 1)):
        sql(db, "INSERT INTO stripe_feed_checkins (sent_at, ok, answer, slug) "
                "VALUES (?, ?, 'x', 's')", (utc_at(now[0] + day - age_days * day), ok))
    job = feed._Job(stripe_settings(sentry_dsn=DSN_TEXT), db, lambda: now[0],
                    _NoSender(), StandIn())
    answer(monkeypatch, [ask(), ask(), ask(), ask()])
    job.round()
    assert len(_rows(db)) == 4, "nothing is deleted before the day turns"
    now[0] += day
    job.round()
    kept = sql(db, "SELECT sent_at FROM stripe_feed_checkins ORDER BY sent_at")
    assert [r[0] for r in kept] == [utc_at(now[0] - 29 * day), utc_at(now[0] - day)]


def test_the_days_turn_deletes_from_no_other_table(db, monkeypatch):
    sql(db, "INSERT INTO stripe_feed_notices (line, sent_at, detail, delivered) "
            "VALUES ('news_late', ?, 'old', 1)", (utc_at(FROZEN_AT - 90 * 86400),))
    now = [float(FROZEN_AT)]
    job = feed._Job(stripe_settings(sentry_dsn=DSN_TEXT), db, lambda: now[0],
                    _NoSender(), StandIn())
    answer(monkeypatch, [ask(), ask()])
    now[0] += 86400
    job.round()
    assert sql(db, "SELECT count(*) FROM stripe_feed_notices")[0][0] == 1


# ---------------------------------------------------------------------------
# The status
# ---------------------------------------------------------------------------


def test_a_refused_checkin_turns_the_status_red(db, monkeypatch):
    _run_once(db, monkeypatch, StandIn((401, "Unauthorized", {})))
    out = cli(db, "payments", "feed", "status", env=ALARM_ENV)
    assert out.exit_code == 1, out.output
    assert "Sentry refused it: 401 Unauthorized" in out.output
    assert "Not right: the last check-in was refused: 401 Unauthorized" in out.output


def test_an_accepted_checkin_is_green_and_named(db, monkeypatch):
    _run_once(db, monkeypatch, StandIn((202, "Accepted", {})))
    out = cli(db, "payments", "feed", "status", env=ALARM_ENV)
    assert out.exit_code == 0, out.output
    line = next(x for x in out.output.splitlines() if x.startswith("Last check-in:"))
    assert "Sentry accepted it: 202 Accepted" in line
    assert " s ago)" in line
    assert "Not right" not in out.output


def test_a_network_failure_turns_it_red(db, monkeypatch):
    _run_once(db, monkeypatch, StandIn(raises=ConnectionRefusedError("refused")))
    out = cli(db, "payments", "feed", "status", env=ALARM_ENV)
    assert out.exit_code == 1
    assert "the last check-in was refused: ConnectionRefusedError" in out.output


def test_the_newest_accepted_older_than_two_intervals_is_red(db, monkeypatch):
    _run_once(db, monkeypatch, StandIn())
    sql(db, "UPDATE stripe_feed_checkins SET sent_at = ?", (utc_at(time.time() - 601),))
    out = cli(db, "payments", "feed", "status", env=ALARM_ENV)
    assert out.exit_code == 1, out.output
    assert "Not right: no check-in succeeded within two intervals" in out.output


def test_control_an_accepted_checkin_inside_two_intervals_is_green(db, monkeypatch):
    _run_once(db, monkeypatch, StandIn())
    sql(db, "UPDATE stripe_feed_checkins SET sent_at = ?", (utc_at(time.time() - 500),))
    assert cli(db, "payments", "feed", "status", env=ALARM_ENV).exit_code == 0


def test_no_row_with_the_alarm_on_is_red(db, monkeypatch):
    answer(monkeypatch, [ask(), ask()])
    assert cli(db, "payments", "feed", "run", "--once", env=ALARM_ENV).exit_code == 0
    out = cli(db, "payments", "feed", "status", env=ALARM_ENV)
    assert out.exit_code == 1, out.output
    assert "Last check-in: none yet" in out.output
    assert "Not right: the alarm has never checked in" in out.output


def test_control_the_alarm_off_is_the_old_status(db, monkeypatch):
    answer(monkeypatch, [ask(), ask()])
    assert cli(db, "payments", "feed", "run", "--once").exit_code == 0
    out = cli(db, "payments", "feed", "status")
    assert out.exit_code == 0, out.output
    assert "Alarm: off: no Sentry DSN" in out.output
    assert "check-in" not in out.output


def test_feed_run_once_prints_what_it_printed_before(db, monkeypatch):
    answer(monkeypatch, [ask(), ask()])
    out = cli(db, "payments", "feed", "run", "--once", env=ALARM_ENV)
    assert out.exit_code == 0, out.output
    assert out.output.splitlines() == [
        "Alarm: checks in to o0.ingest.sentry.io/0 every 5 minutes",
        "platform: 0 seen, 0 handled, largest lag 0 s",
        f"{SHOP_ACCOUNT}: 0 seen, 0 handled, largest lag 0 s",
    ]
    assert _rows(db) == []


def test_no_planted_key_in_any_output(db, monkeypatch):
    _run_once(db, monkeypatch, StandIn((401, "Unauthorized", {})))
    answer(monkeypatch, [ask(), ask()])
    outs = [cli(db, "payments", "feed", "status", env=ALARM_ENV),
            cli(db, "payments", "feed", "run", "--once", env=ALARM_ENV)]
    for out in outs:
        for key in (PLANTED_DSN_KEY, TEST_KEY, TEST_SECRET):
            assert key not in out.output


def test_control_the_planted_key_is_in_the_url_the_stand_in_saw(db, monkeypatch):
    sentry = StandIn()
    _run_once(db, monkeypatch, sentry)
    assert PLANTED_DSN_KEY in sentry.urls[0]
