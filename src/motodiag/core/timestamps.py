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
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

SESSION_TIME_FIELDS = ("created_at", "updated_at", "closed_at")


def utc_now() -> str:
    """The current time in the stored format."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def to_utc(value: str) -> str:
    """A stored session time in the stored format (see the module note)."""
    if " " in value and "T" not in value:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc)
    else:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.astimezone()  # this machine's zone, that date's offset
    return parsed.astimezone(timezone.utc).isoformat(timespec="milliseconds")


def local_display(value: Optional[str]) -> Optional[str]:
    """An aware time as local ``YYYY-MM-DDTHH:MM:SS``; anything else as given.

    A naive value is returned unchanged: the old session times were already
    local, and other tables' naive values are not this function's to guess.
    """
    if not value:
        return value
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return value
    if parsed.tzinfo is None:
        return value
    return parsed.astimezone().replace(tzinfo=None).isoformat(timespec="seconds")


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
