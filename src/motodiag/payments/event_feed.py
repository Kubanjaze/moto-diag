"""The payments feed: the server asks Stripe for its news (Phase 371).

The backend is tailnet-only (the operator's decision 3 of 2026-09-28), so
Stripe cannot reach the webhook route. The operator's K65 (2026-11-05,
option A): the server asks Stripe for new events about every 20 seconds,
for the platform account and each connected shop, and hands each one to
the existing handler, :func:`dispatch_event`, which records every event
id and acknowledges a repeat without running its handler.

**The place** is a row per account in ``stripe_event_cursors``: the
newest event's ``created`` (UTC seconds). Every round asks from 300
seconds before it, because Stripe does not deliver ``created`` in strict
order and a repeat costs nothing. Because the place is in the database, a
restore from a backup takes an older place with it, and the next round
asks again from there. Stripe keeps 30 days of events; a place older than
that is raised to 30 days back and the gap is written in ``last_error``.

**The limit check** (K65 (2)) runs at start and on the first round of
each UTC day: one notice at 50 connected shops, one at 100, and at most
one a day when news ran more than 2 minutes late or Stripe refused or
rate-limited an ask. Each notice sent is a row in
``stripe_feed_notices``, which is how "once" is known across restarts.

Nothing here prints or logs a key, a secret or a payload: the log names
the account, the event id, the type and the outcome.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from motodiag import __version__
from motodiag.billing.providers import get_billing_provider
from motodiag.billing.webhook_handlers import (
    HANDLERS,
    LiveEventRefused,
    dispatch_event,
)
from motodiag.core.config import Settings
from motodiag.core.database import get_connection
from motodiag.payments import stripe_api
from motodiag.telemetry import monitor
from motodiag.telemetry.dsn import DsnError, parse_dsn
from motodiag.telemetry.events import message_event
from motodiag.telemetry.sender import Transport

logger = logging.getLogger("motodiag.payments.feed")

#: The eight event types the handler knows, read from it so the two
#: cannot drift.
FEED_TYPES: tuple[str, ...] = tuple(HANDLERS)

PLATFORM = "platform"
#: Every round asks from this many seconds before the place.
OVERLAP_S = 300
#: Stripe keeps events this long.
MAX_AGE_S = 30 * 86400
PAGE_LIMIT = 100
#: After a ``busy`` or ``unreachable`` answer the wait doubles up to this.
MAX_BACKOFF_S = 300
WARN_EVERY_S = 60.0
BACKOFF_KINDS = ("busy", "unreachable")
REFUSAL_KINDS = ("refused", "busy")

GUIDE = "docs/guide/payments.md"
UPGRADE_SECTION = "'When it is time to upgrade'"
NOTICES_SECTION = "'The notices'"
#: The two shop-count lines are sent once ever: a count does not uncross.
ONCE_EVER = ("shops_plan", "shops_upgrade")


def stamp(seconds: float) -> str:
    """UTC seconds in the stored format (Phase 370)."""
    return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat(
        timespec="milliseconds")


def utc_day(seconds: float) -> str:
    return datetime.fromtimestamp(seconds, tz=timezone.utc).date().isoformat()


@dataclass
class RoundResult:
    """One account's round."""

    account: str
    seen: int = 0
    handled: int = 0
    lag_s: float = 0.0
    error_kind: Optional[str] = None
    error: Optional[str] = None


@dataclass
class DayStats:
    """The job's memory of one UTC day; a restart starts it empty."""

    day: str
    max_lag_s: float = 0.0
    refusals: int = 0

    def add(self, results: list[RoundResult]) -> None:
        for r in results:
            self.max_lag_s = max(self.max_lag_s, r.lag_s)
            if r.error_kind in REFUSAL_KINDS:
                self.refusals += 1


@dataclass
class _Cursor:
    last_created: int
    last_event_id: Optional[str]


@dataclass
class _Handled:
    newest: int = 0
    newest_id: Optional[str] = None
    handled: int = 0
    lag_s: float = 0.0
    hold: bool = False
    errors: list[str] = field(default_factory=list)
    kind: Optional[str] = None


# ---------------------------------------------------------------- accounts


def key_livemode(settings: Settings) -> int:
    return 0 if stripe_api.is_test_key(settings.stripe_api_key) else 1


def accounts(settings: Settings, db_path: Optional[str]) -> list[str]:
    """``platform``, then each connected shop of the key's mode, by shop."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT stripe_account_id FROM shop_payment_accounts "
            "WHERE livemode = ? ORDER BY shop_id",
            (key_livemode(settings),),
        ).fetchall()
    return [PLATFORM] + [r[0] for r in rows]


# ---------------------------------------------------------------- the place


def read_cursor(db_path: Optional[str], account: str) -> Optional[_Cursor]:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT last_created, last_event_id FROM stripe_event_cursors "
            "WHERE account = ?", (account,),
        ).fetchone()
    return None if row is None else _Cursor(int(row[0]), row[1])


def write_cursor(db_path: Optional[str], account: str, *, last_created: int,
                 last_event_id: Optional[str], polled_at: str,
                 last_error: Optional[str], livemode: int) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT INTO stripe_event_cursors
                   (account, last_created, last_event_id, polled_at,
                    last_error, livemode)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(account) DO UPDATE SET
                   last_created = excluded.last_created,
                   last_event_id = excluded.last_event_id,
                   polled_at = excluded.polled_at,
                   last_error = excluded.last_error,
                   livemode = excluded.livemode""",
            (account, last_created, last_event_id, polled_at, last_error,
             livemode),
        )


def cursor_rows(db_path: Optional[str]) -> list[dict]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM stripe_event_cursors ORDER BY account = 'platform' "
            "DESC, account").fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------- the asks


def fetch_events(client: Any, account: str, since: int) -> list[dict]:
    """Every event of :data:`FEED_TYPES` created at or after ``since``,
    following ``has_more``; oldest first."""
    params: dict[str, Any] = {"created": {"gte": since},
                              "types": list(FEED_TYPES), "limit": PAGE_LIMIT}
    options = None if account == PLATFORM else {"stripe_account": account}
    events: list[dict] = []
    while True:
        page = _list_page(client, dict(params), options)
        data = [stripe_api.as_dict(e) for e in page.get("data") or []]
        events.extend(data)
        if not page.get("has_more") or not data:
            break
        params["starting_after"] = data[-1]["id"]
    return sorted(events, key=lambda e: (int(e.get("created") or 0),
                                         str(e.get("id"))))


def _list_page(client: Any, params: dict, options: Optional[dict]) -> dict:
    return stripe_api.as_dict(stripe_api.call(
        "list events", lambda: client.v1.events.list(params, options)))


def _place(cursor: Optional[_Cursor], now: int) -> tuple[int, int, Optional[str]]:
    """(the place, the first ``created`` to ask for, the gap if any)."""
    floor = now - MAX_AGE_S
    place = cursor.last_created if cursor else now
    gap = None
    if place < floor:
        gap = (f"the place was {stamp(place)}, older than the 30 days Stripe "
               f"keeps; events before {stamp(floor)} were not asked for")
        place = floor + OVERLAP_S
    return place, max(place - OVERLAP_S, floor), gap


def _handle(events: list[dict], account: str, settings: Settings,
            db_path: Optional[str], clock: Callable[[], float]) -> _Handled:
    out = _Handled()
    provider = get_billing_provider(settings=settings)
    for event in events:
        if account != PLATFORM and not event.get("account"):
            # _check_source compares it with the payment's account, and
            # Stripe's pages do not promise it on a listed event.
            event["account"] = account
        created = int(event.get("created") or 0)
        try:
            result = dispatch_event(event, db_path=db_path, provider=provider,
                                    settings=settings)
        except LiveEventRefused as exc:
            out.errors.append(f"event {event.get('id')} refused: {exc}")
            out.kind = out.kind or "live_event"
            continue
        if result.retry:
            out.hold = True
            out.errors.append(f"event {result.event_id} must be asked for again")
            out.kind = out.kind or "retry"
            continue
        logger.info("payments feed %s: %s %s %s", account, result.event_id,
                    result.event_type,
                    "handled" if result.processed else "already seen")
        if result.processed:
            out.handled += 1
            out.lag_s = max(out.lag_s, clock() - created)
        if created >= out.newest:
            out.newest, out.newest_id = created, result.event_id
    return out


def poll_account(client: Any, account: str, settings: Settings,
                 db_path: Optional[str], clock: Callable[[], float]) -> RoundResult:
    """One account's round: ask from the place, hand each event on, and
    write the place. Raises :class:`stripe_api.StripeUnavailable`."""
    cursor = read_cursor(db_path, account)
    now = int(clock())
    place, since, gap = _place(cursor, now)
    events = fetch_events(client, account, since)
    done = _handle(events, account, settings, db_path, clock)
    errors = ([gap] if gap else []) + done.errors
    last_created, last_id = place, cursor.last_event_id if cursor else None
    if not done.hold and done.newest > place:
        last_created, last_id = done.newest, done.newest_id
    write_cursor(db_path, account, last_created=last_created,
                 last_event_id=last_id, polled_at=stamp(clock()),
                 last_error="; ".join(errors) or None,
                 livemode=key_livemode(settings))
    return RoundResult(account, seen=len(events), handled=done.handled,
                       lag_s=done.lag_s,
                       error_kind=done.kind or ("gap" if gap else None),
                       error="; ".join(errors) or None)


def poll_once(settings: Settings, db_path: Optional[str],
              clock: Callable[[], float]) -> list[RoundResult]:
    """A round over every account. Raises :class:`StripeNotConfigured` or
    :class:`LiveKeyRefused` before any ask; one account's
    :class:`StripeUnavailable` is written to its row and the others go on."""
    client = stripe_api.client(settings)
    results = []
    for account in accounts(settings, db_path):
        try:
            results.append(poll_account(client, account, settings, db_path, clock))
        except stripe_api.StripeUnavailable as exc:
            cursor = read_cursor(db_path, account)
            write_cursor(
                db_path, account,
                last_created=cursor.last_created if cursor else int(clock()),
                last_event_id=cursor.last_event_id if cursor else None,
                polled_at=stamp(clock()), last_error=exc.message,
                livemode=key_livemode(settings))
            logger.warning("payments feed %s: %s", account, exc.message)
            results.append(RoundResult(account, error_kind=exc.kind,
                                       error=exc.message))
    return results


# ---------------------------------------------------------------- the limits


def notice_text(line: str, settings: Settings, shops: int, day: DayStats) -> str:
    if line == "shops_plan":
        return (f"Payments feed: {shops} shops are connected; time to start "
                f"planning the upgrade. See {GUIDE}, {UPGRADE_SECTION}.")
    if line == "shops_upgrade":
        return (f"Payments feed: {shops} shops are connected; time to upgrade "
                f"to webhooks. See {GUIDE}, {UPGRADE_SECTION}.")
    if line == "news_late":
        return (f"Payments feed: news of a payment ran {day.max_lag_s:.0f} "
                f"seconds late (the limit is {settings.stripe_feed_late_s}). "
                f"See {GUIDE}, {NOTICES_SECTION}.")
    return (f"Payments feed: Stripe refused or rate-limited {day.refusals} "
            f"asks. See {GUIDE}, {NOTICES_SECTION}.")


def crossed_lines(settings: Settings, shops: int, day: DayStats) -> list[str]:
    lines = []
    if shops >= settings.stripe_feed_shops_plan:
        lines.append("shops_plan")
    if shops >= settings.stripe_feed_shops_upgrade:
        lines.append("shops_upgrade")
    if day.max_lag_s > settings.stripe_feed_late_s:
        lines.append("news_late")
    if day.refusals > 0:
        lines.append("stripe_refused")
    return lines


def already_sent(db_path: Optional[str], line: str, today: str) -> bool:
    with get_connection(db_path) as conn:
        if line in ONCE_EVER:
            row = conn.execute(
                "SELECT 1 FROM stripe_feed_notices WHERE line = ? LIMIT 1",
                (line,)).fetchone()
        else:
            row = conn.execute(
                "SELECT 1 FROM stripe_feed_notices WHERE line = ? "
                "AND substr(sent_at, 1, 10) = ? LIMIT 1",
                (line, today)).fetchone()
    return row is not None


def limit_check(settings: Settings, db_path: Optional[str], day: DayStats,
                sender: Any, clock: Callable[[], float]) -> list[str]:
    """Send one notice for each line crossed and not yet sent; the lines sent."""
    now = clock()
    shops = len(accounts(settings, db_path)) - 1
    sent = []
    for line in crossed_lines(settings, shops, day):
        if already_sent(db_path, line, utc_day(now)):
            continue
        text = notice_text(line, settings, shops, day)
        delivered = sender.capture(message_event(
            text, release=__version__, environment=sender.environment,
            server_name=sender.server_name, clock=lambda: stamp(now),
            level="warning"))
        if not sender.enabled:
            logger.warning("%s", text)
        with get_connection(db_path) as conn:
            conn.execute(
                "INSERT INTO stripe_feed_notices (line, sent_at, detail, delivered) "
                "VALUES (?, ?, ?, ?)",
                (line, stamp(now), text, 1 if delivered else 0))
        sent.append(line)
    return sent


def notices_since(db_path: Optional[str], since: str) -> list[dict]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT line, sent_at, detail, delivered FROM stripe_feed_notices "
            "WHERE sent_at >= ? ORDER BY id", (since,)).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------- the job


class _Job:
    """The state ``run_forever`` keeps between rounds."""

    def __init__(self, settings: Settings, db_path: Optional[str],
                 clock: Callable[[], float], sender: Any,
                 transport: Optional[Transport]) -> None:
        self.settings, self.db_path, self.clock = settings, db_path, clock
        self.sender, self.transport = sender, transport
        self.wait: float = settings.stripe_poll_interval_s
        self.last_checkin: Optional[float] = None
        self.last_warning: Optional[float] = None
        self.day = DayStats(utc_day(clock()))
        self.dsn = alarm_dsn(settings)

    def round(self) -> list[RoundResult]:
        today = utc_day(self.clock())
        if today != self.day.day:
            limit_check(self.settings, self.db_path, self.day, self.sender,
                        self.clock)
            self.day = DayStats(today)
        try:
            results = poll_once(self.settings, self.db_path, self.clock)
        except (stripe_api.StripeNotConfigured, stripe_api.LiveKeyRefused):
            raise
        except Exception:
            logger.exception("payments feed: the round failed")
            results = []
        self.day.add(results)
        return results

    def backoff(self, results: list[RoundResult]) -> None:
        if any(r.error_kind in BACKOFF_KINDS for r in results):
            self.wait = min(self.wait * 2, MAX_BACKOFF_S)
            now = self.clock()
            if self.last_warning is None or now - self.last_warning >= WARN_EVERY_S:
                self.last_warning = now
                logger.warning("payments feed: Stripe is busy or unreachable; "
                               "the next ask is in %.0f seconds", self.wait)
        else:
            self.wait = self.settings.stripe_poll_interval_s

    def checkin(self) -> None:
        if self.dsn is None:
            return
        now = self.clock()
        if (self.last_checkin is not None
                and now - self.last_checkin < self.settings.stripe_poll_checkin_s):
            return
        self.last_checkin = now
        monitor.checkin(self.dsn, self.settings.stripe_poll_monitor_slug,
                        self.transport,
                        interval_minutes=max(1, self.settings.stripe_poll_checkin_s // 60))


def alarm_dsn(settings: Settings):
    """The DSN the alarm checks in to, or None (the alarm is off)."""
    text = (settings.sentry_dsn or "").strip()
    if not text:
        return None
    try:
        return parse_dsn(text)
    except DsnError as exc:
        logger.error("payments feed: the alarm is off: MOTODIAG_SENTRY_DSN "
                     "cannot be used (%s)", exc)
        return None


def run_forever(settings: Settings, db_path: Optional[str], *,
                clock: Callable[[], float], sleep: Callable[[float], None],
                stop: Callable[[], bool], sender: Any,
                transport: Optional[Transport] = None) -> None:
    """A round, a check-in when due, then the wait; until ``stop()``."""
    job = _Job(settings, db_path, clock, sender, transport)
    limit_check(settings, db_path, job.day, sender, clock)
    while not stop():
        results = job.round()
        job.checkin()
        job.backoff(results)
        sleep(job.wait)
