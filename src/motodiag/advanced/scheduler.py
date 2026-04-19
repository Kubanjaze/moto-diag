"""Phase 151 — service-interval scheduler.

Pure computation layer on top of :mod:`motodiag.advanced.schedule_repo`.

Three entrypoints drive the CLI:

- :func:`due_items` — intervals within ``horizon_miles`` / ``horizon_days``.
- :func:`overdue_items` — intervals past their due-point, most-overdue first.
- :func:`record_completion` — write a completion, re-compute next-due.

Internal :func:`next_due_calc` does the dual-axis arithmetic with a
month-addition routine that respects calendar month-lengths
(Feb 28 + 2 months = Apr 28, Jan 31 + 1 month = Feb 28/29).

Phase 152 soft-dependency
-------------------------

This phase runs before Phase 152 adds ``vehicles.mileage`` +
``service_history``. :func:`record_completion` tries to read
``vehicles.mileage`` and to INSERT into ``service_history`` wrapped in
``try`` / ``except sqlite3.OperationalError`` — when 152 lands, both
paths "just work" with no code change here.
"""

from __future__ import annotations

import calendar
import sqlite3
from datetime import date, datetime, timezone
from typing import Optional

from motodiag.core.database import get_connection
from motodiag.advanced.schedule_repo import (
    ServiceIntervalError,
    get_interval_by_slug,
    list_intervals,
    update_interval,
)


# ---------------------------------------------------------------------------
# Helpers — date parsing + month arithmetic
# ---------------------------------------------------------------------------


def _parse_iso_date(value: str) -> date:
    """Parse ISO-8601 (date or datetime) into a ``date``.

    Accepts ``'2024-05-01'`` and ``'2024-05-01T12:34:56'`` — both
    collapse to a naive date since service-interval granularity is days.
    Raises ``ValueError`` with a clear message on malformed input.
    """
    if not value:
        raise ValueError("empty date string")
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        pass
    # Plain YYYY-MM-DD
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(
            f"invalid ISO-8601 date: {value!r} — expected YYYY-MM-DD or ISO datetime"
        ) from exc


def _add_months(start: date, months: int) -> date:
    """Add ``months`` calendar months to ``start``, clamping to month-end.

    Examples:
      * ``_add_months(date(2024, 2, 28), 2)`` → ``date(2024, 4, 28)``.
      * ``_add_months(date(2024, 1, 31), 1)`` → ``date(2024, 2, 29)``
        (2024 is a leap year).
      * ``_add_months(date(2023, 1, 31), 1)`` → ``date(2023, 2, 28)``.

    Uses ``calendar.monthrange`` to find the last valid day of the
    target month.
    """
    if months == 0:
        return start
    year = start.year + (start.month - 1 + months) // 12
    month = (start.month - 1 + months) % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(start.day, last_day)
    return date(year, month, day)


def _today_utc() -> date:
    """Return today's UTC date — isolated so tests can monkeypatch it."""
    return datetime.now(timezone.utc).date()


# ---------------------------------------------------------------------------
# Core calculation
# ---------------------------------------------------------------------------


def next_due_calc(
    interval: dict,
    *,
    done_miles: Optional[int] = None,
    done_at: Optional[str] = None,
    current_miles: Optional[int] = None,
) -> tuple[Optional[int], Optional[str]]:
    """Compute ``(next_due_miles, next_due_at)`` for a completion event.

    Parameters
    ----------
    interval : dict
        A service_intervals row (or a ServiceInterval-ish dict) with
        ``every_miles`` / ``every_months`` keys.
    done_miles : int or None
        Mileage at which the service was completed. If None, miles-side
        is omitted from the output.
    done_at : str or None
        ISO-8601 date (or datetime) of completion. If None, falls back
        to today's UTC date when the interval has ``every_months``.
    current_miles : int or None
        Current-odometer signal — unused here but accepted for API
        symmetry with the rest of the module.

    Returns
    -------
    (next_due_miles, next_due_at) : tuple
        Each may be ``None`` if the axis is not configured or the
        required input is missing. The CHECK constraint guarantees at
        least one of every_miles / every_months is set, so at least one
        side of the output is always populated when done_* is supplied.
    """
    every_miles = interval.get("every_miles")
    every_months = interval.get("every_months")
    if every_miles is None and every_months is None:
        raise ServiceIntervalError(
            "interval has neither every_miles nor every_months set"
        )

    next_miles: Optional[int] = None
    next_at: Optional[str] = None

    if every_miles is not None and done_miles is not None:
        next_miles = int(done_miles) + int(every_miles)

    if every_months is not None:
        if done_at is not None:
            base = _parse_iso_date(done_at)
        else:
            base = _today_utc()
        next_date = _add_months(base, int(every_months))
        next_at = next_date.isoformat()

    return next_miles, next_at


# ---------------------------------------------------------------------------
# Due / overdue loading
# ---------------------------------------------------------------------------


def _remaining(
    interval: dict,
    current_miles: Optional[int],
    today: date,
) -> tuple[Optional[int], Optional[int]]:
    """Return (miles_remaining, days_remaining) for a service_intervals row.

    ``miles_remaining`` is negative when overdue. ``days_remaining`` is
    negative when the calendar due-point has passed. Either may be
    ``None`` when the corresponding axis has no data.
    """
    miles_rem: Optional[int] = None
    days_rem: Optional[int] = None

    next_due_miles = interval.get("next_due_miles")
    if next_due_miles is not None and current_miles is not None:
        miles_rem = int(next_due_miles) - int(current_miles)

    next_due_at = interval.get("next_due_at")
    if next_due_at:
        try:
            due_date = _parse_iso_date(next_due_at)
            days_rem = (due_date - today).days
        except ValueError:
            days_rem = None

    return miles_rem, days_rem


def _read_vehicle_miles(
    vehicle_id: int, db_path: Optional[str] = None,
) -> Optional[int]:
    """Read ``vehicles.mileage`` for a bike. Returns None when absent.

    Phase 152 soft-dep: if the column doesn't exist yet, SQLite raises
    ``OperationalError`` and we swallow it — callers fall through to
    None (no current-miles signal).
    """
    try:
        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT mileage FROM vehicles WHERE id = ?", (vehicle_id,),
            ).fetchone()
    except sqlite3.OperationalError:
        return None
    if row is None:
        return None
    return row[0] if row[0] is not None else None


def _annotate(
    interval: dict, current_miles: Optional[int], today: date,
) -> dict:
    """Return an enriched row dict with miles_remaining / days_remaining."""
    miles_rem, days_rem = _remaining(interval, current_miles, today)
    out = dict(interval)
    out["miles_remaining"] = miles_rem
    out["days_remaining"] = days_rem
    out["current_miles"] = current_miles
    return out


def due_items(
    vehicle_id: int,
    *,
    horizon_miles: int = 500,
    horizon_days: int = 30,
    current_miles: Optional[int] = None,
    db_path: Optional[str] = None,
    today: Optional[date] = None,
) -> list[dict]:
    """Return intervals within the horizon but not yet overdue.

    An interval qualifies when ``0 <= miles_remaining <= horizon_miles``
    OR ``0 <= days_remaining <= horizon_days``. Overdue rows
    (negative remaining on the active axis) are excluded — they're
    surfaced by :func:`overdue_items`.

    Ordering: the most-imminent axis first — smallest non-negative
    days_remaining, then smallest non-negative miles_remaining.
    """
    today = today or _today_utc()
    if current_miles is None:
        current_miles = _read_vehicle_miles(vehicle_id, db_path=db_path)

    rows = list_intervals(vehicle_id, db_path=db_path)
    out: list[dict] = []
    for row in rows:
        enriched = _annotate(row, current_miles, today)
        miles_rem = enriched["miles_remaining"]
        days_rem = enriched["days_remaining"]

        miles_in_window = (
            miles_rem is not None and 0 <= miles_rem <= horizon_miles
        )
        days_in_window = (
            days_rem is not None and 0 <= days_rem <= horizon_days
        )
        miles_overdue = miles_rem is not None and miles_rem < 0
        days_overdue = days_rem is not None and days_rem < 0

        if miles_overdue or days_overdue:
            # Handled by overdue_items.
            continue
        if miles_in_window or days_in_window:
            out.append(enriched)

    def _sort_key(entry: dict) -> tuple:
        dr = entry["days_remaining"]
        mr = entry["miles_remaining"]
        return (
            0 if dr is not None else 1,
            dr if dr is not None else 10**9,
            mr if mr is not None else 10**9,
            entry.get("item_slug", ""),
        )

    out.sort(key=_sort_key)
    return out


def overdue_items(
    vehicle_id: int,
    *,
    current_miles: Optional[int] = None,
    db_path: Optional[str] = None,
    today: Optional[date] = None,
) -> list[dict]:
    """Return intervals whose next-due point has been passed.

    Most-overdue first (most-negative remaining on either axis).
    """
    today = today or _today_utc()
    if current_miles is None:
        current_miles = _read_vehicle_miles(vehicle_id, db_path=db_path)

    rows = list_intervals(vehicle_id, db_path=db_path)
    out: list[dict] = []
    for row in rows:
        enriched = _annotate(row, current_miles, today)
        miles_rem = enriched["miles_remaining"]
        days_rem = enriched["days_remaining"]
        if (miles_rem is not None and miles_rem < 0) or (
            days_rem is not None and days_rem < 0
        ):
            out.append(enriched)

    def _worst(entry: dict) -> float:
        """Most-negative axis wins — treat None as neutral (0)."""
        miles_rem = entry["miles_remaining"]
        days_rem = entry["days_remaining"]
        worst = 0
        if miles_rem is not None and miles_rem < 0:
            worst = min(worst, miles_rem)
        if days_rem is not None and days_rem < 0:
            worst = min(worst, days_rem)
        return worst

    out.sort(key=lambda r: (_worst(r), r.get("item_slug", "")))
    return out


# ---------------------------------------------------------------------------
# Completion
# ---------------------------------------------------------------------------


def record_completion(
    vehicle_id: int,
    item_slug: str,
    *,
    at_miles: Optional[int] = None,
    at_date: Optional[str] = None,
    db_path: Optional[str] = None,
) -> dict:
    """Record that a maintenance item was completed. Returns the updated row.

    Mileage resolution (in order):
      1. ``at_miles`` argument if provided.
      2. ``vehicles.mileage`` if Phase 152 has landed (try/except).
      3. None — miles-side of next_due is left unchanged.

    Date resolution: ``at_date`` if provided, else today's UTC date.

    Phase 152 soft-dep: also attempts to INSERT into ``service_history``
    — if the table doesn't exist yet, the OperationalError is
    swallowed so this phase runs cleanly pre-152.

    Raises :class:`ServiceIntervalError` when neither date nor miles
    source is available AND the interval has only ``every_miles`` set.
    """
    interval = get_interval_by_slug(vehicle_id, item_slug, db_path=db_path)
    if interval is None:
        raise ServiceIntervalError(
            f"no service interval for vehicle_id={vehicle_id}, "
            f"item_slug={item_slug!r}"
        )

    # Resolve mileage source.
    if at_miles is None:
        at_miles = _read_vehicle_miles(vehicle_id, db_path=db_path)

    # Resolve date source — default to today.
    if at_date is None:
        done_date = _today_utc()
        at_date_iso = done_date.isoformat()
    else:
        # Validate early so we fail before any writes.
        _parse_iso_date(at_date)
        at_date_iso = str(at_date)[:10] if "T" not in str(at_date) else (
            _parse_iso_date(at_date).isoformat()
        )

    # Miles-side sanity: interval requires mileage AND we have none AND
    # interval has no months-side either — impossible here because the
    # CHECK constraint guarantees at least one axis, but we guard anyway.
    if (
        interval.get("every_miles") is not None
        and interval.get("every_months") is None
        and at_miles is None
    ):
        raise ServiceIntervalError(
            f"item {item_slug!r} is mileage-only but no mileage source "
            "is available — pass --at-miles or wait for Phase 152's "
            "vehicles.mileage column."
        )

    # Compute the new next_due.
    next_miles, next_at = next_due_calc(
        interval, done_miles=at_miles, done_at=at_date_iso,
    )

    # Persist the completion + new next-due.
    update_fields: dict = {
        "last_done_at": at_date_iso,
    }
    if at_miles is not None:
        update_fields["last_done_miles"] = at_miles
    if next_miles is not None:
        update_fields["next_due_miles"] = next_miles
    if next_at is not None:
        update_fields["next_due_at"] = next_at

    update_interval(int(interval["id"]), db_path=db_path, **update_fields)

    # Phase 152 soft-dep: record to service_history if the table exists.
    try:
        with get_connection(db_path) as conn:
            conn.execute(
                "INSERT INTO service_history ("
                "  vehicle_id, item_slug, performed_at_miles, "
                "  performed_at_date, notes"
                ") VALUES (?, ?, ?, ?, ?)",
                (
                    vehicle_id,
                    item_slug,
                    at_miles,
                    at_date_iso,
                    None,
                ),
            )
    except sqlite3.OperationalError:
        # service_history table doesn't exist (pre-152). Swallow.
        pass

    # Return the updated row.
    updated = get_interval_by_slug(vehicle_id, item_slug, db_path=db_path)
    return updated or {}


def history(
    vehicle_id: int,
    item_slug: Optional[str] = None,
    db_path: Optional[str] = None,
) -> list[dict]:
    """Return service-completion history for a bike.

    Phase 152 reads the ``service_history`` table. Until then, this
    returns a snapshot built from ``last_done_*`` columns on the
    intervals themselves — one row per interval that has ever been
    completed, ordered by completion date DESC.
    """
    # First try Phase 152's service_history table.
    try:
        with get_connection(db_path) as conn:
            if item_slug:
                rows = conn.execute(
                    "SELECT * FROM service_history "
                    "WHERE vehicle_id = ? AND item_slug = ? "
                    "ORDER BY performed_at_date DESC, id DESC",
                    (vehicle_id, item_slug),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM service_history "
                    "WHERE vehicle_id = ? "
                    "ORDER BY performed_at_date DESC, id DESC",
                    (vehicle_id,),
                ).fetchall()
            return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        pass

    # Pre-152 snapshot from service_intervals.
    rows = list_intervals(vehicle_id, db_path=db_path)
    out: list[dict] = []
    for row in rows:
        if row.get("last_done_at") is None and row.get("last_done_miles") is None:
            continue
        if item_slug and row.get("item_slug") != item_slug:
            continue
        out.append({
            "vehicle_id": vehicle_id,
            "item_slug": row.get("item_slug"),
            "performed_at_miles": row.get("last_done_miles"),
            "performed_at_date": row.get("last_done_at"),
            "source": "snapshot",
        })
    out.sort(
        key=lambda r: (r.get("performed_at_date") or "", r.get("item_slug") or ""),
        reverse=True,
    )
    return out
