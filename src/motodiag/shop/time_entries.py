"""Phase 202 — per-mechanic labor time entries.

The ledger that makes "how long did this job take" answerable. Before
this module the question had no answer and could not be reconstructed:
:func:`start_work` overwrites ``work_orders.started_at`` on every start
and :func:`pause_work` stamps nothing, so a job that was started, paused
and resumed retained a single timestamp and no record of the gap.

Closed entries sum into ``work_orders.actual_hours`` — the existing sink
that invoicing (with its ``estimated_hours`` fallback), the labor
reconciler and analytics already consume. This module never writes that
column itself; the complete-transition does, and only when the caller
supplied nothing. **Manual always wins** — auto-fill is a default, not
an authority, which is what keeps the Gate 9 invoice contract intact and
leaves a mechanic able to bill for time the timer missed.

Two invariants, and only one of them is enforced here:

1. **One OPEN entry per mechanic** — enforced by a partial unique index
   in migration 047, not by this code. An application-level check would
   race a double-tap or a second device. :func:`clock_in` closes the
   caller's existing open entry first so the common path never trips it.
2. **A forgotten entry closes at the cap, not at discovery.** The
   mechanic did not work until whenever someone next opened the app, so
   :func:`close_stale_entries` stamps ``started_at + cap`` and flags the
   row ``needs_review`` rather than inventing hours.

All timestamps are server-side UTC ISO strings. The client sends none —
a device clock an hour out would otherwise bill an hour.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from motodiag.core.config import get_settings
from motodiag.core.database import get_connection

logger = logging.getLogger(__name__)


class TimeEntryNotFoundError(ValueError):
    """No such time entry."""


class NoOpenTimeEntryError(ValueError):
    """Clock-out attempted with nothing running."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.isoformat()


def _parse(stamp: str) -> datetime:
    parsed = datetime.fromisoformat(str(stamp))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _cap_hours() -> float:
    return float(get_settings().max_open_time_entry_hours)


def _close_row(
    conn, row: dict, ended_at: datetime, needs_review: bool = False,
) -> dict:
    """Stamp an end + duration on one open row. Returns the closed row."""
    started = _parse(row["started_at"])
    duration = max(0, int((ended_at - started).total_seconds()))
    conn.execute(
        "UPDATE work_order_time_entries SET ended_at = ?, "
        "duration_seconds = ?, needs_review = ?, updated_at = ? "
        "WHERE id = ?",
        (
            _iso(ended_at), duration, 1 if needs_review else 0,
            _iso(_now()), row["id"],
        ),
    )
    closed = dict(row)
    closed.update({
        "ended_at": _iso(ended_at),
        "duration_seconds": duration,
        "needs_review": 1 if needs_review else 0,
    })
    return closed


def close_stale_entries(db_path: Optional[str] = None) -> list[dict]:
    """Auto-close entries left open past the cap. Returns what closed.

    Runs lazily from :func:`clock_in` and :func:`get_open_entry_for_user`
    — the same best-effort-sweep-on-access posture the mobile app uses
    for its caches. No cron, no worker, nothing new to operate.
    """
    cap = _cap_hours()
    cutoff = _now() - timedelta(hours=cap)
    closed: list[dict] = []
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM work_order_time_entries "
            "WHERE ended_at IS NULL AND started_at <= ?",
            (_iso(cutoff),),
        ).fetchall()
        for row in rows:
            row = dict(row)
            # Close AT the cap, not now — inventing the intervening
            # hours would silently bill them.
            end = _parse(row["started_at"]) + timedelta(hours=cap)
            closed.append(_close_row(conn, row, end, needs_review=True))
    for row in closed:
        logger.info(
            "auto-closed stale time entry id=%s (user=%s wo=%s) at the "
            "%sh cap; flagged needs_review",
            row["id"], row["user_id"], row["work_order_id"], cap,
        )
    return closed


def get_open_entry_for_user(
    user_id: int, db_path: Optional[str] = None,
) -> Optional[dict]:
    """The mechanic's currently-running entry, or None. Sweeps first."""
    close_stale_entries(db_path=db_path)
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM work_order_time_entries "
            "WHERE user_id = ? AND ended_at IS NULL",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def clock_in(
    wo_id: int,
    user_id: int,
    db_path: Optional[str] = None,
) -> tuple[dict, Optional[dict]]:
    """Start the clock. Returns ``(new_entry, auto_closed_entry_or_None)``.

    Closes whatever the caller had running ANYWHERE first — the physical
    reality is that a mechanic is on one bike at a time. The caller is
    told what was closed so the UI can say "stopped your timer on WO 41";
    a mechanic who never sees that message will not understand where
    their time went.
    """
    close_stale_entries(db_path=db_path)
    now = _now()
    auto_closed: Optional[dict] = None
    with get_connection(db_path) as conn:
        open_row = conn.execute(
            "SELECT * FROM work_order_time_entries "
            "WHERE user_id = ? AND ended_at IS NULL",
            (user_id,),
        ).fetchone()
        if open_row is not None:
            auto_closed = _close_row(conn, dict(open_row), now)
        cursor = conn.execute(
            """INSERT INTO work_order_time_entries
                 (work_order_id, user_id, started_at, source,
                  created_at, updated_at)
               VALUES (?, ?, ?, 'timer', ?, ?)""",
            (wo_id, user_id, _iso(now), _iso(now), _iso(now)),
        )
        entry_id = cursor.lastrowid
        new_row = dict(conn.execute(
            "SELECT * FROM work_order_time_entries WHERE id = ?",
            (entry_id,),
        ).fetchone())
    logger.info(
        "clock-in: user=%s wo=%s entry=%s%s",
        user_id, wo_id, entry_id,
        f" (auto-closed entry {auto_closed['id']} on wo "
        f"{auto_closed['work_order_id']})" if auto_closed else "",
    )
    return new_row, auto_closed


def clock_out(
    user_id: int,
    wo_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> dict:
    """Stop the caller's running entry. Returns the closed row.

    ``wo_id``, when given, asserts the running entry belongs to that
    work order — so a stale screen cannot stop a timer the mechanic
    started somewhere else.
    """
    now = _now()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM work_order_time_entries "
            "WHERE user_id = ? AND ended_at IS NULL",
            (user_id,),
        ).fetchone()
        if row is None:
            raise NoOpenTimeEntryError(
                f"user id={user_id} has no running time entry"
            )
        row = dict(row)
        if wo_id is not None and int(row["work_order_id"]) != int(wo_id):
            raise NoOpenTimeEntryError(
                f"user id={user_id} is clocked in on work order "
                f"{row['work_order_id']}, not {wo_id}"
            )
        closed = _close_row(conn, row, now)
    logger.info(
        "clock-out: user=%s wo=%s entry=%s duration=%ss",
        user_id, closed["work_order_id"], closed["id"],
        closed["duration_seconds"],
    )
    return closed


def list_entries_for_wo(
    wo_id: int, db_path: Optional[str] = None,
) -> list[dict]:
    """Every entry on a work order, newest first. Open entries included."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM work_order_time_entries "
            "WHERE work_order_id = ? ORDER BY started_at DESC, id DESC",
            (wo_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def total_seconds_for_wo(
    wo_id: int, db_path: Optional[str] = None,
) -> int:
    """Summed duration of CLOSED entries. Open entries contribute 0.

    Deliberate: an open entry has no defensible duration to bill, and
    including a running timer would make the total change on every read.
    """
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(duration_seconds), 0) "
            "FROM work_order_time_entries "
            "WHERE work_order_id = ? AND ended_at IS NOT NULL",
            (wo_id,),
        ).fetchone()
    return int(row[0] or 0)


def close_open_entries_for_wo(
    wo_id: int, db_path: Optional[str] = None,
) -> list[dict]:
    """Close anything still running on a work order. Used on complete."""
    now = _now()
    closed: list[dict] = []
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM work_order_time_entries "
            "WHERE work_order_id = ? AND ended_at IS NULL",
            (wo_id,),
        ).fetchall()
        for row in rows:
            closed.append(_close_row(conn, dict(row), now))
    if closed:
        logger.info(
            "closed %s running time entr%s on completed wo=%s",
            len(closed), "y" if len(closed) == 1 else "ies", wo_id,
        )
    return closed


def adjust_entry(
    entry_id: int,
    started_at: Optional[str] = None,
    ended_at: Optional[str] = None,
    note: Optional[str] = None,
    needs_review: Optional[bool] = None,
    db_path: Optional[str] = None,
) -> dict:
    """Correct an entry's times / note, or clear its review flag.

    Recomputes ``duration_seconds`` whenever either bound moves and the
    entry is closed. Raises when the result would be negative — a
    correction that ends before it starts is a typo, not data.
    """
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM work_order_time_entries WHERE id = ?",
            (entry_id,),
        ).fetchone()
        if row is None:
            raise TimeEntryNotFoundError(f"time entry not found: id={entry_id}")
        row = dict(row)
        new_started = started_at or row["started_at"]
        new_ended = ended_at if ended_at is not None else row["ended_at"]
        duration = row["duration_seconds"]
        if new_ended is not None:
            seconds = int(
                (_parse(new_ended) - _parse(new_started)).total_seconds()
            )
            if seconds < 0:
                raise ValueError(
                    f"time entry id={entry_id}: ended_at precedes started_at"
                )
            duration = seconds
        flag = row["needs_review"] if needs_review is None else int(needs_review)
        conn.execute(
            "UPDATE work_order_time_entries SET started_at = ?, "
            "ended_at = ?, duration_seconds = ?, note = ?, "
            "needs_review = ?, source = 'manual', updated_at = ? "
            "WHERE id = ?",
            (
                new_started, new_ended, duration,
                note if note is not None else row["note"],
                flag, _iso(_now()), entry_id,
            ),
        )
        updated = dict(conn.execute(
            "SELECT * FROM work_order_time_entries WHERE id = ?",
            (entry_id,),
        ).fetchone())
    logger.info("adjusted time entry id=%s", entry_id)
    return updated
