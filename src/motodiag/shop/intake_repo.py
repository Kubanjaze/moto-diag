"""Intake visit repository — CRUD + status lifecycle for ``intake_visits``.

Phase 160. The "arrived on lot" event: a mechanic logs that a given
customer brought a given bike into a given shop at a given timestamp
with mechanic-freetext ``reported_problems``. Structured issue tagging
lands in Phase 162; work-order creation in Phase 161. This phase is
intentionally narrow — just the arrival record.

Status lifecycle
----------------

Guarded. The generic :func:`update_intake` CANNOT mutate ``status``;
only the dedicated transition functions can:

- :func:`create_intake` — status starts at ``'open'``.
- :func:`close_intake` — ``open`` → ``closed`` with a ``close_reason``
  (default ``'completed'``). Raises :class:`IntakeAlreadyClosedError`
  if the intake is already non-open.
- :func:`cancel_intake` — ``open`` → ``'cancelled'`` with a reason.
  Distinct from close so Phase 171 analytics can separate completed
  from withdrawn visits.
- :func:`reopen_intake` — non-open → ``'open'``, clears ``closed_at``
  and ``close_reason``. Mechanics reopen when "fixed" turns out to be
  "not fixed."

Denormalized reads
------------------

:func:`get_intake` and :func:`list_intakes` JOIN customers + vehicles +
shops so the CLI layer can render names without a second round-trip.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from motodiag.core.database import get_connection


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class IntakeNotFoundError(ValueError):
    """Raised when an intake id does not resolve."""


class IntakeAlreadyClosedError(ValueError):
    """Raised when a close/cancel transition targets a non-open intake."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


INTAKE_STATUSES: tuple[str, ...] = ("open", "closed", "cancelled")


INTAKE_CLOSE_REASONS: tuple[str, ...] = (
    "completed",
    "customer-withdrew",
    "no-fault-found",
    "transferred",
)


# Whitelist of fields ``update_intake`` is allowed to mutate.
# ``status``/``closed_at``/``close_reason`` are owned by the transition
# functions so the lifecycle cannot be bypassed.
_UPDATABLE_FIELDS: frozenset[str] = frozenset({
    "mileage_at_intake",
    "reported_problems",
})


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _require_row(
    conn: sqlite3.Connection, table: str, row_id: int, label: str,
) -> dict:
    """Fetch ``table.id=row_id`` or raise a user-facing ValueError."""
    row = conn.execute(
        f"SELECT * FROM {table} WHERE id = ?", (row_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"{label} not found: id={row_id}")
    return dict(row)


def _since_cutoff(since: Optional[str]) -> Optional[str]:
    """Interpret a ``since`` token as an ISO timestamp cutoff.

    Accepted forms:
    - ``None`` → no filter.
    - ISO timestamp (``'2026-04-21T00:00:00'``) → passthrough.
    - Relative offset (``'7d'``, ``'24h'``, ``'30m'``) → ``now - offset``.
    """
    if since is None:
        return None
    s = str(since).strip()
    if not s:
        return None
    if s[-1:] in ("d", "h", "m") and s[:-1].isdigit():
        n = int(s[:-1])
        unit = s[-1]
        delta = {
            "d": timedelta(days=n),
            "h": timedelta(hours=n),
            "m": timedelta(minutes=n),
        }[unit]
        return (datetime.now() - delta).isoformat()
    # Assume ISO; SQLite comparison works lexicographically.
    return s


# ---------------------------------------------------------------------------
# Intake CRUD
# ---------------------------------------------------------------------------


def create_intake(
    shop_id: int,
    customer_id: int,
    vehicle_id: int,
    reported_problems: Optional[str] = None,
    mileage_at_intake: Optional[int] = None,
    intake_user_id: int = 1,
    intake_at: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    """Create an intake visit row. Returns the new intake id.

    Performs explicit pre-checks on ``shop_id``, ``customer_id``, and
    ``vehicle_id`` so callers get a named error rather than a raw
    SQLite IntegrityError. Status defaults to ``'open'``.
    """
    if mileage_at_intake is not None:
        try:
            mileage_at_intake = int(mileage_at_intake)
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"mileage_at_intake must be an integer or None (got "
                f"{mileage_at_intake!r})"
            ) from e
        if mileage_at_intake < 0:
            raise ValueError(
                f"mileage_at_intake must be >= 0 (got {mileage_at_intake})"
            )

    with get_connection(db_path) as conn:
        _require_row(conn, "shops", shop_id, "shop")
        _require_row(conn, "customers", customer_id, "customer")
        _require_row(conn, "vehicles", vehicle_id, "vehicle")

        columns = [
            "shop_id", "customer_id", "vehicle_id",
            "mileage_at_intake", "reported_problems", "intake_user_id",
        ]
        values: list = [
            shop_id, customer_id, vehicle_id,
            mileage_at_intake, reported_problems, intake_user_id,
        ]
        if intake_at is not None:
            columns.append("intake_at")
            values.append(str(intake_at))

        placeholders = ", ".join("?" for _ in columns)
        column_list = ", ".join(columns)
        cursor = conn.execute(
            f"INSERT INTO intake_visits ({column_list}) VALUES ({placeholders})",
            values,
        )
        return int(cursor.lastrowid)


def get_intake(
    intake_id: int, db_path: Optional[str] = None,
) -> Optional[dict]:
    """Fetch one intake with denormalized shop/customer/vehicle fields.

    Returns None on miss (use :func:`require_intake` for a raising variant).
    """
    query = """
        SELECT iv.*,
               s.name AS shop_name,
               c.name AS customer_name,
               c.phone AS customer_phone,
               c.email AS customer_email,
               v.make AS vehicle_make,
               v.model AS vehicle_model,
               v.year AS vehicle_year
        FROM intake_visits iv
        LEFT JOIN shops s ON s.id = iv.shop_id
        LEFT JOIN customers c ON c.id = iv.customer_id
        LEFT JOIN vehicles v ON v.id = iv.vehicle_id
        WHERE iv.id = ?
    """
    with get_connection(db_path) as conn:
        row = conn.execute(query, (intake_id,)).fetchone()
        return dict(row) if row else None


def require_intake(
    intake_id: int, db_path: Optional[str] = None,
) -> dict:
    """Same as :func:`get_intake` but raises :class:`IntakeNotFoundError`."""
    row = get_intake(intake_id, db_path=db_path)
    if row is None:
        raise IntakeNotFoundError(f"intake not found: id={intake_id}")
    return row


def list_intakes(
    shop_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    vehicle_id: Optional[int] = None,
    status: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 100,
    db_path: Optional[str] = None,
) -> list[dict]:
    """List intake visits matching the given filters, most-recent first.

    Returns denormalized rows (shop/customer/vehicle display fields).
    ``since`` accepts ISO timestamp or relative offset ``'7d'``/
    ``'24h'``/``'30m'``. ``limit=0`` disables the cap.
    """
    if status is not None and status not in INTAKE_STATUSES:
        raise ValueError(
            f"status must be one of {INTAKE_STATUSES} or None "
            f"(got {status!r})"
        )
    cutoff = _since_cutoff(since)

    query = """
        SELECT iv.*,
               s.name AS shop_name,
               c.name AS customer_name,
               v.make AS vehicle_make,
               v.model AS vehicle_model,
               v.year AS vehicle_year
        FROM intake_visits iv
        LEFT JOIN shops s ON s.id = iv.shop_id
        LEFT JOIN customers c ON c.id = iv.customer_id
        LEFT JOIN vehicles v ON v.id = iv.vehicle_id
    """
    conditions: list[str] = []
    params: list = []
    if shop_id is not None:
        conditions.append("iv.shop_id = ?")
        params.append(shop_id)
    if customer_id is not None:
        conditions.append("iv.customer_id = ?")
        params.append(customer_id)
    if vehicle_id is not None:
        conditions.append("iv.vehicle_id = ?")
        params.append(vehicle_id)
    if status is not None:
        conditions.append("iv.status = ?")
        params.append(status)
    if cutoff is not None:
        conditions.append("iv.intake_at >= ?")
        params.append(cutoff)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY iv.intake_at DESC, iv.id DESC"
    if limit and limit > 0:
        query += " LIMIT ?"
        params.append(int(limit))

    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def list_open_for_bike(
    vehicle_id: int, db_path: Optional[str] = None,
) -> list[dict]:
    """Return the open intakes currently logged against a given bike.

    UX helper for the "is this bike already checked in?" duplicate-
    intake guard. Empty list means safe to create a new intake.
    """
    return list_intakes(
        vehicle_id=vehicle_id, status="open", limit=0, db_path=db_path,
    )


def update_intake(
    intake_id: int,
    updates: dict,
    db_path: Optional[str] = None,
) -> bool:
    """Update whitelisted fields on an intake row. Returns True on success.

    Cannot mutate ``status``/``closed_at``/``close_reason`` — use the
    lifecycle functions instead. Raises :class:`IntakeNotFoundError`
    when the row does not exist.
    """
    if not isinstance(updates, dict):
        raise TypeError(f"updates must be a dict, got {type(updates).__name__}")
    filtered = {k: v for k, v in updates.items() if k in _UPDATABLE_FIELDS}
    if not filtered:
        return False
    if "mileage_at_intake" in filtered and filtered["mileage_at_intake"] is not None:
        try:
            filtered["mileage_at_intake"] = int(filtered["mileage_at_intake"])
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"mileage_at_intake must be an integer or None "
                f"(got {filtered['mileage_at_intake']!r})"
            ) from e
        if filtered["mileage_at_intake"] < 0:
            raise ValueError(
                f"mileage_at_intake must be >= 0 "
                f"(got {filtered['mileage_at_intake']})"
            )

    set_clauses = ", ".join(f"{k} = ?" for k in filtered.keys())
    params: list = list(filtered.values())
    params.append(datetime.now().isoformat())
    params.append(intake_id)

    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM intake_visits WHERE id = ?", (intake_id,),
        ).fetchone()
        if row is None:
            raise IntakeNotFoundError(f"intake not found: id={intake_id}")
        cursor = conn.execute(
            f"UPDATE intake_visits SET {set_clauses}, updated_at = ? "
            "WHERE id = ?",
            params,
        )
        return cursor.rowcount > 0


def close_intake(
    intake_id: int,
    close_reason: str = "completed",
    db_path: Optional[str] = None,
) -> bool:
    """Transition an intake from ``open`` → ``closed``.

    Raises :class:`IntakeNotFoundError` on missing id,
    :class:`IntakeAlreadyClosedError` on non-open status.
    """
    if close_reason is not None and close_reason not in INTAKE_CLOSE_REASONS:
        raise ValueError(
            f"close_reason must be one of {INTAKE_CLOSE_REASONS} or None "
            f"(got {close_reason!r})"
        )
    return _transition_out_of_open(
        intake_id, "closed", close_reason, db_path,
    )


def cancel_intake(
    intake_id: int,
    reason: str = "customer-withdrew",
    db_path: Optional[str] = None,
) -> bool:
    """Transition an intake from ``open`` → ``cancelled``.

    Distinct from :func:`close_intake` so Phase 171 analytics can filter
    completed from withdrawn visits.
    """
    if reason is not None and reason not in INTAKE_CLOSE_REASONS:
        raise ValueError(
            f"reason must be one of {INTAKE_CLOSE_REASONS} or None "
            f"(got {reason!r})"
        )
    return _transition_out_of_open(
        intake_id, "cancelled", reason, db_path,
    )


def reopen_intake(
    intake_id: int, db_path: Optional[str] = None,
) -> bool:
    """Transition an intake from ``closed``/``cancelled`` → ``open``.

    Clears ``closed_at`` and ``close_reason``. No-op on already-open
    intakes (idempotent).
    """
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, status FROM intake_visits WHERE id = ?",
            (intake_id,),
        ).fetchone()
        if row is None:
            raise IntakeNotFoundError(f"intake not found: id={intake_id}")
        if row["status"] == "open":
            return False
        cursor = conn.execute(
            """UPDATE intake_visits
                   SET status = 'open',
                       closed_at = NULL,
                       close_reason = NULL,
                       updated_at = ?
                 WHERE id = ?""",
            (now, intake_id),
        )
        return cursor.rowcount > 0


def count_intakes(
    shop_id: Optional[int] = None,
    status: Optional[str] = None,
    since: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    """Count intakes matching filters. Dashboard roll-up helper."""
    if status is not None and status not in INTAKE_STATUSES:
        raise ValueError(
            f"status must be one of {INTAKE_STATUSES} or None "
            f"(got {status!r})"
        )
    cutoff = _since_cutoff(since)
    query = "SELECT COUNT(*) AS n FROM intake_visits iv"
    conditions: list[str] = []
    params: list = []
    if shop_id is not None:
        conditions.append("iv.shop_id = ?")
        params.append(shop_id)
    if status is not None:
        conditions.append("iv.status = ?")
        params.append(status)
    if cutoff is not None:
        conditions.append("iv.intake_at >= ?")
        params.append(cutoff)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    with get_connection(db_path) as conn:
        row = conn.execute(query, params).fetchone()
        return int(row["n"]) if row else 0


# ---------------------------------------------------------------------------
# Private lifecycle helper
# ---------------------------------------------------------------------------


def _transition_out_of_open(
    intake_id: int,
    new_status: str,
    reason: Optional[str],
    db_path: Optional[str],
) -> bool:
    """Shared ``open -> closed|cancelled`` transition."""
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, status FROM intake_visits WHERE id = ?",
            (intake_id,),
        ).fetchone()
        if row is None:
            raise IntakeNotFoundError(f"intake not found: id={intake_id}")
        if row["status"] != "open":
            raise IntakeAlreadyClosedError(
                f"intake id={intake_id} is already {row['status']!r}; "
                f"call reopen_intake first if you need to re-transition"
            )
        cursor = conn.execute(
            """UPDATE intake_visits
                   SET status = ?,
                       closed_at = ?,
                       close_reason = ?,
                       updated_at = ?
                 WHERE id = ?""",
            (new_status, now, reason, now, intake_id),
        )
        return cursor.rowcount > 0
