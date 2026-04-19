"""Phase 152 — service_history repository.

Thin CRUD layer over the Phase 152 ``service_history`` table. Every
function accepts an optional ``db_path`` so tests can point at a temp
DB; production paths resolve from ``get_settings().db_path``.

Design notes
------------

- ``add_service_event`` is the single write path. It performs TWO
  statements inside the same ``get_connection`` context (the context
  manager commits on success and rolls back on any exception, so the
  INSERT + the monotonic UPDATE succeed or fail together):

    1. ``INSERT INTO service_history ...``
    2. ``UPDATE vehicles SET mileage = ? WHERE id = ? AND
       (mileage IS NULL OR mileage < ?)`` — the monotonic bump. The
       ``WHERE mileage IS NULL OR mileage < ?`` clause is the
       no-decrease guard: back-dated or lower-mileage events leave
       ``vehicles.mileage`` alone. When ``at_miles`` is ``None`` the
       UPDATE is skipped entirely (diagnostic events with no reading
       shouldn't force a mileage write).

- List/query functions return plain ``dict`` rows, not
  :class:`ServiceEvent` instances — mirrors Phase 151's
  ``scheduling.repo`` which does the same. CLI renderers and downstream
  phases can lift to Pydantic with ``ServiceEvent.model_validate`` as
  needed.

- CHECK-constraint violations on ``event_type`` raise
  ``sqlite3.IntegrityError``; callers that want a friendlier surface
  should validate via :class:`ServiceEvent` (Pydantic Literal) first.

- FK cascades are delegated to the schema (PRAGMA foreign_keys=ON is
  set by ``get_connection``). Deleting a vehicle drops its history;
  deleting a user nulls the ``mechanic_user_id`` on every row.

- ``list_service_events`` supports filters the CLI needs today:
  ``since`` (ISO date str, inclusive), ``until`` (ISO date str,
  inclusive), ``event_type`` (exact match), and ``limit`` (default 50).
  Sort is always ``at_date DESC, id DESC`` — newest first, stable on
  ties.
"""

from __future__ import annotations

from datetime import date as _date
from typing import Optional

from motodiag.advanced.models import ServiceEvent
from motodiag.core.database import get_connection


class ServiceEventNotFoundError(LookupError):
    """Raised when a lookup by id misses the service_history table."""


def _iso_date(value) -> str:
    """Coerce a ``date``/``datetime``/``str`` to an ISO-8601 date string.

    Accepts either a ``date`` (isoformat → ``YYYY-MM-DD``) or a string
    that's already ISO. Normalises whatever the caller passed so the
    DB always stores a consistent shape.
    """
    if isinstance(value, _date):
        return value.isoformat()
    if isinstance(value, str):
        return value
    # Fallback: str() on whatever the caller gave us.
    return str(value)


def add_service_event(
    event: ServiceEvent,
    db_path: Optional[str] = None,
) -> int:
    """Insert one service event and return its id.

    Also bumps ``vehicles.mileage`` monotonically when
    ``event.at_miles`` is set. Both writes share a single
    ``get_connection`` transaction (commits or rolls back together).

    Parameters
    ----------
    event : ServiceEvent
        Pydantic-validated event. ``event_type`` has already been
        rejected against the 11-value Literal; the DB CHECK provides
        a secondary gate.
    db_path : str, optional
        Test override.

    Returns
    -------
    int
        The newly-inserted row's id.
    """
    at_date_iso = _iso_date(event.at_date)

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO service_history (
                vehicle_id, event_type, at_miles, at_date, notes,
                cost_cents, mechanic_user_id, parts_csv
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                int(event.vehicle_id),
                event.event_type,
                int(event.at_miles) if event.at_miles is not None else None,
                at_date_iso,
                event.notes,
                int(event.cost_cents) if event.cost_cents is not None else None,
                int(event.mechanic_user_id)
                if event.mechanic_user_id is not None
                else None,
                event.parts_csv,
            ),
        )
        new_id = cursor.lastrowid

        # Monotonic mileage bump — only when at_miles is set AND the
        # new reading exceeds whatever is currently stored (or the
        # column is NULL). No-decrease guard is enforced at the SQL
        # level so even concurrent writers can't trample each other.
        if event.at_miles is not None:
            at_miles = int(event.at_miles)
            conn.execute(
                """UPDATE vehicles
                   SET mileage = ?
                   WHERE id = ?
                     AND (mileage IS NULL OR mileage < ?)""",
                (at_miles, int(event.vehicle_id), at_miles),
            )

        return int(new_id)


def get_service_event(
    event_id: int,
    db_path: Optional[str] = None,
) -> Optional[dict]:
    """Return one event row by id, or ``None`` if missing."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM service_history WHERE id = ?",
            (int(event_id),),
        ).fetchone()
        return dict(row) if row else None


def list_service_events(
    vehicle_id: int,
    *,
    since: Optional[str] = None,
    until: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 50,
    db_path: Optional[str] = None,
) -> list[dict]:
    """List service events for one bike, newest first.

    Parameters
    ----------
    vehicle_id : int
        Required — this is the per-bike timeline query.
    since : str, optional
        ISO-8601 date (inclusive). Drops rows with ``at_date < since``.
    until : str, optional
        ISO-8601 date (inclusive). Drops rows with ``at_date > until``.
    event_type : str, optional
        Exact-match filter on the 11-value vocabulary.
    limit : int
        Max rows to return. Default 50.
    db_path : str, optional
        Test override.
    """
    clauses = ["vehicle_id = ?"]
    params: list = [int(vehicle_id)]
    if since is not None:
        clauses.append("at_date >= ?")
        params.append(since)
    if until is not None:
        clauses.append("at_date <= ?")
        params.append(until)
    if event_type is not None:
        clauses.append("event_type = ?")
        params.append(event_type)
    where = " AND ".join(clauses)
    params.append(int(limit))

    query = (
        "SELECT * FROM service_history "
        f"WHERE {where} "
        "ORDER BY at_date DESC, id DESC "
        "LIMIT ?"
    )
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def list_all_service_events(
    *,
    since: Optional[str] = None,
    until: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
    db_path: Optional[str] = None,
) -> list[dict]:
    """Cross-bike list of recent events (newest first).

    Same filters as :func:`list_service_events` minus the required
    ``vehicle_id``. Useful for the global ``history show-all`` feed.
    """
    clauses: list[str] = []
    params: list = []
    if since is not None:
        clauses.append("at_date >= ?")
        params.append(since)
    if until is not None:
        clauses.append("at_date <= ?")
        params.append(until)
    if event_type is not None:
        clauses.append("event_type = ?")
        params.append(event_type)
    params.append(int(limit))

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    query = (
        "SELECT * FROM service_history"
        f"{where} "
        "ORDER BY at_date DESC, id DESC "
        "LIMIT ?"
    )
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def list_by_type(
    event_type: str,
    *,
    limit: int = 100,
    db_path: Optional[str] = None,
) -> list[dict]:
    """List all events of one type across the whole garage."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM service_history WHERE event_type = ? "
            "ORDER BY at_date DESC, id DESC LIMIT ?",
            (event_type, int(limit)),
        ).fetchall()
        return [dict(r) for r in rows]


def count_service_events(
    vehicle_id: Optional[int] = None,
    *,
    event_type: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    """Count service_history rows, optionally scoped per-bike or per-type."""
    clauses: list[str] = []
    params: list = []
    if vehicle_id is not None:
        clauses.append("vehicle_id = ?")
        params.append(int(vehicle_id))
    if event_type is not None:
        clauses.append("event_type = ?")
        params.append(event_type)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    query = f"SELECT COUNT(*) FROM service_history{where}"
    with get_connection(db_path) as conn:
        row = conn.execute(query, params).fetchone()
        return int(row[0]) if row else 0


def delete_service_event(
    event_id: int,
    db_path: Optional[str] = None,
) -> bool:
    """Delete one event row. Returns True when a row was removed.

    Does NOT roll back ``vehicles.mileage`` — deletion is bookkeeping
    correction, and the column is still a monotonic high-water mark.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM service_history WHERE id = ?",
            (int(event_id),),
        )
        return cursor.rowcount > 0
