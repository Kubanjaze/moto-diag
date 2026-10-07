"""Session times: one stored format, in UTC, and its local display.

Phase 370 (F10). A diagnostic session's times are stored as
``YYYY-MM-DDTHH:MM:SS.mmm+00:00`` (``2026-10-06T19:42:07.123+00:00``):

- UTC, so ``created_at >= month_start`` compares one clock with one clock.
  Before 370 sessions were stamped in naive local time against a UTC month
  start, and on a month's last evening in a US timezone a new session
  counted toward neither month;
- the ``T`` shape the month start, the API's ``since`` and the CLI's filters
  compare in. A space against a ``T`` on the same date is 191B's bug;
- the offset in the string, so no reader takes it for local time;
- exactly three fraction digits: ECMAScript's own date-time format, which
  the app's ``new Date()`` must parse on any engine.

Values written before 370 are naive. One with a ``T`` was local time (the
old ``datetime.now().isoformat()``); one with a space is SQLite's
``CURRENT_TIMESTAMP``, which is UTC. Migration 079 converts them with
:func:`to_utc`.

Phase 377 (F186, F191) puts the shop's tables on the same footing. Their
writers store this format too; columns that default to
``CURRENT_TIMESTAMP`` keep SQLite's shape. So a stored time is compared
parsed, never as text: ``datetime(col) >= ?`` against :func:`utc_cutoff`,
SQLite's canonical UTC ``YYYY-MM-DD HH:MM:SS``, which ``datetime()`` makes
of every shape stored here.

"Local" is the server's zone, because a shop records no time zone (F192).
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Union

SESSION_TIME_FIELDS = ("created_at", "updated_at", "closed_at")
SQLITE_UTC = "%Y-%m-%d %H:%M:%S"
_RELATIVE = re.compile(r"^(\d+)([dhm])$")
_NAIVE_LOCAL = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d(:\d\d(\.\d+)?)?$")
_SQLITE_SHAPE = re.compile(r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$")


def utc_now() -> str:
    """The current time in the stored format."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def stored_instant(value: str) -> datetime:
    """A stored time as an aware UTC datetime, by the module note's rule.

    Naive with a ``T`` is local time; naive with a space is SQLite's
    ``CURRENT_TIMESTAMP``, so UTC; an offset or ``Z`` is that instant.
    Raises ``ValueError`` on anything else.
    """
    text = str(value).strip()
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        if "T" in text:
            parsed = parsed.astimezone()  # this machine's zone, that date's offset
        else:
            parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def to_utc(value: str) -> str:
    """A stored time in the stored format (see the module note)."""
    return stored_instant(value).isoformat(timespec="milliseconds")


def utc_cutoff(value: Union[str, datetime, None]) -> Optional[str]:
    """A ``since`` or ``until`` as SQLite's UTC shape, for ``datetime(col) >= ?``.

    ``Nd``, ``Nh`` and ``Nm`` count back from now. A date or date-time with
    no zone is the shop's (local) time; one with an offset is converted.
    ``None`` or blank gives ``None``; anything else raises ``ValueError``.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        moment = value
    else:
        text = str(value).strip()
        if not text:
            return None
        relative = _RELATIVE.match(text)
        if relative:
            n = int(relative.group(1))
            delta = {"d": timedelta(days=n), "h": timedelta(hours=n),
                     "m": timedelta(minutes=n)}[relative.group(2)]
            moment = datetime.now(timezone.utc) - delta
        else:
            try:
                moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError as e:
                raise ValueError(
                    f"since must be Nd, Nh, Nm or an ISO date or time, got {text!r}"
                ) from e
    if moment.tzinfo is None:
        moment = moment.astimezone()  # the shop's zone (F192)
    return moment.astimezone(timezone.utc).strftime(SQLITE_UTC)


def local_day_start(day: Union[str, date]) -> str:
    """The UTC moment the shop's day ``YYYY-MM-DD`` begins, in SQLite's shape.

    A window of days is ``[local_day_start(first), local_day_start(last + 1))``.
    """
    the_day = date.fromisoformat(day) if isinstance(day, str) else day
    midnight = datetime(the_day.year, the_day.month, the_day.day).astimezone()
    return midnight.astimezone(timezone.utc).strftime(SQLITE_UTC)


def local_display(value: Optional[str]) -> Optional[str]:
    """A stored time as local ``YYYY-MM-DDTHH:MM:SS``; anything else as given.

    An aware value and SQLite's space-shaped UTC are converted. A naive
    ``T`` value is returned unchanged: it was written in local time.
    """
    if not value:
        return value
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return value
    if parsed.tzinfo is None:
        if not _SQLITE_SHAPE.match(text):
            return value
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone().replace(tzinfo=None).isoformat(timespec="seconds")


def local_day(value: str) -> str:
    """The shop's day (``YYYY-MM-DD``) of a stored time."""
    return stored_instant(value).astimezone().date().isoformat()


def with_utc_times(row: Optional[dict]) -> Optional[dict]:
    """A row for the API: each ``…_at`` string in the stored format.

    A value that is not a time is left as it is.
    """
    if row is None:
        return None
    out = dict(row)
    for key, value in row.items():
        if key.endswith("_at") and isinstance(value, str) and value:
            try:
                out[key] = to_utc(value)
            except ValueError:
                pass  # not a stored time; the API passes it on as it is
    return out


def convert_session_times_079(conn) -> int:
    """Migration 079's ``post_apply``: every session time to the stored format.

    Returns the number of fields changed. Idempotent: a value already in the
    format converts to itself.
    """
    changed = 0
    rows = conn.execute(
        "SELECT id, " + ", ".join(SESSION_TIME_FIELDS) + " FROM diagnostic_sessions"
    ).fetchall()
    for row in rows:
        updates = {}
        for name, value in zip(SESSION_TIME_FIELDS, tuple(row)[1:]):
            if value is None:
                continue
            converted = to_utc(str(value))
            if converted != value:
                updates[name] = converted
        if updates:
            conn.execute(
                "UPDATE diagnostic_sessions SET "
                + ", ".join(f"{name} = ?" for name in updates)
                + " WHERE id = ?",
                (*updates.values(), tuple(row)[0]),
            )
            changed += len(updates)
    return changed


# The shop's columns that Phase 377's writers stamp. known_issues is left
# (the operator's 2A), and appointments' scheduled and actual times are the
# shop's clock (booking.py's rule), so only their updated_at is here.
SHOP_TIME_FIELDS_082: dict[str, tuple[str, ...]] = {
    "customers": ("created_at", "updated_at"),
    "vehicles": ("created_at", "updated_at"),
    "work_orders": ("opened_at", "started_at", "completed_at", "closed_at", "updated_at"),
    "issues": ("resolved_at", "updated_at"),
    "intake_visits": ("updated_at", "closed_at"),
    "repair_plans": ("created_at", "updated_at", "approved_at", "completed_at"),
    "appointments": ("updated_at",),
    "shops": ("updated_at",),
    "workflow_templates": ("created_at", "updated_at"),
    "customer_bikes": ("assigned_at",),
    "users": ("created_at",),
    "performance_baselines": ("last_rebuilt_at",),
}


def convert_shop_times_082(conn) -> int:
    """Migration 082's ``post_apply``: each naive local time to the stored format.

    Only a naive ``T`` value changes; SQLite's space-shaped UTC stays as
    written. Returns the number of fields changed. Idempotent.
    """
    changed = 0
    for table, fields in SHOP_TIME_FIELDS_082.items():
        # rowid: customer_bikes has a two-column key and no id.
        rows = conn.execute(
            f"SELECT rowid, {', '.join(fields)} FROM {table}"
        ).fetchall()
        for row in rows:
            updates = {
                name: to_utc(str(value))
                for name, value in zip(fields, tuple(row)[1:])
                if value is not None and _NAIVE_LOCAL.match(str(value))
            }
            if updates:
                conn.execute(
                    f"UPDATE {table} SET "
                    + ", ".join(f"{name} = ?" for name in updates)
                    + " WHERE rowid = ?",
                    (*updates.values(), tuple(row)[0]),
                )
                changed += len(updates)
    return changed
