"""Work order repository — CRUD + guarded status lifecycle.

Phase 161. The mechanic's unit of work on a specific bike: attaches to
Phase 160 `intake_visits` via nullable `intake_visit_id`, carries title +
description + priority + estimated/actual hours, and moves through a
guarded lifecycle:

    draft → open → in_progress → (on_hold | completed | cancelled) → (reopen) → open

Status lifecycle is guarded — only the dedicated transition functions
(`open_work_order`, `start_work`, `pause_work`, `resume_work`,
`complete_work_order`, `cancel_work_order`, `reopen_work_order`) can
mutate `status`, `opened_at`, `started_at`, `completed_at`, `closed_at`,
`on_hold_reason`, or `cancellation_reason`. The generic
:func:`update_work_order` whitelist excludes all of these, so CLI or
future-API code cannot bypass the lifecycle.

Denormalized FKs
----------------

`shop_id` + `vehicle_id` + `customer_id` are duplicated onto every work
order row even when an `intake_visit_id` supplies the same values.
Dominant queries (by shop, by bike, by customer) are single-index
lookups rather than JOINs. :func:`create_work_order` validates cross-
table consistency when both `intake_visit_id` and explicit
`vehicle_id`/`customer_id` are supplied; `update_work_order` cannot
touch these columns so consistency cannot drift.

Denormalized display reads
--------------------------

:func:`get_work_order` and :func:`list_work_orders` JOIN shops +
customers + vehicles + (optional) intake_visits + (optional) mechanic
user so CLI rendering has every label without a second round-trip.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional

from motodiag.core.database import get_connection


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class WorkOrderNotFoundError(ValueError):
    """Raised when a work order id does not resolve."""


class InvalidWorkOrderTransition(ValueError):
    """Raised when a lifecycle transition is illegal given current status."""


class WorkOrderFKError(ValueError):
    """Raised when an FK violation surfaces during create/update."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


WORK_ORDER_STATUSES: tuple[str, ...] = (
    "draft", "open", "in_progress", "on_hold", "completed", "cancelled",
)


TERMINAL_STATUSES: frozenset[str] = frozenset({"completed", "cancelled"})


# Legal from-status → set of to-statuses. Drives the lifecycle guard.
_VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"open", "cancelled"}),
    "open": frozenset({"in_progress", "on_hold", "cancelled"}),
    "in_progress": frozenset({"on_hold", "completed", "cancelled"}),
    "on_hold": frozenset({"in_progress", "cancelled"}),
    "completed": frozenset({"open"}),   # via reopen
    "cancelled": frozenset({"open"}),   # via reopen
}


# Whitelist for ``update_work_order``. Status + all lifecycle timestamps +
# all *_reason fields are OWNED by the transition functions. The
# denormalized FKs (shop_id / vehicle_id / customer_id / intake_visit_id)
# are excluded by design — if a mechanic captured the wrong intake,
# cancel the WO and recreate rather than mutating cross-table state.
_UPDATABLE_FIELDS: frozenset[str] = frozenset({
    "title",
    "description",
    "priority",
    "estimated_hours",
    "estimated_parts_cost_cents",
    "actual_hours",
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


def _validate_priority(priority: Optional[int]) -> int:
    """Clamp + validate a priority value (1-5)."""
    if priority is None:
        return 3
    try:
        p = int(priority)
    except (TypeError, ValueError) as e:
        raise ValueError(
            f"priority must be an integer 1-5 (got {priority!r})"
        ) from e
    if not 1 <= p <= 5:
        raise ValueError(
            f"priority must be between 1 and 5 (got {p})"
        )
    return p


def _validate_hours(value: Optional[float], label: str) -> Optional[float]:
    """Coerce an hours value to float and reject negatives."""
    if value is None:
        return None
    try:
        hours = float(value)
    except (TypeError, ValueError) as e:
        raise ValueError(
            f"{label} must be numeric or None (got {value!r})"
        ) from e
    if hours < 0:
        raise ValueError(f"{label} must be >= 0 (got {hours})")
    return hours


def _assert_transition(
    from_status: str, to_status: str, wo_id: int,
) -> None:
    """Raise :class:`InvalidWorkOrderTransition` when illegal."""
    if to_status not in _VALID_TRANSITIONS.get(from_status, frozenset()):
        raise InvalidWorkOrderTransition(
            f"work order id={wo_id} cannot transition "
            f"{from_status!r} → {to_status!r}. "
            f"Legal from {from_status!r}: "
            f"{sorted(_VALID_TRANSITIONS.get(from_status, []))}"
        )


# ---------------------------------------------------------------------------
# Create + read
# ---------------------------------------------------------------------------


def create_work_order(
    shop_id: int,
    vehicle_id: int,
    customer_id: int,
    title: str,
    description: Optional[str] = None,
    priority: int = 3,
    estimated_hours: Optional[float] = None,
    estimated_parts_cost_cents: Optional[int] = None,
    intake_visit_id: Optional[int] = None,
    assigned_mechanic_user_id: Optional[int] = None,
    created_by_user_id: int = 1,
    db_path: Optional[str] = None,
) -> int:
    """Create a work order in ``draft`` status. Returns the new id.

    Performs explicit pre-checks on shop/vehicle/customer (and optionally
    intake_visit + mechanic) so callers get a named error rather than a
    raw SQLite IntegrityError. When ``intake_visit_id`` is supplied,
    asserts that the intake's ``vehicle_id`` + ``customer_id`` +
    ``shop_id`` match the explicit arguments — prevents denormalization
    drift from the moment of creation.
    """
    if not title or not str(title).strip():
        raise ValueError("title must not be empty")
    priority = _validate_priority(priority)
    estimated_hours = _validate_hours(estimated_hours, "estimated_hours")
    if estimated_parts_cost_cents is not None:
        try:
            estimated_parts_cost_cents = int(estimated_parts_cost_cents)
        except (TypeError, ValueError) as e:
            raise ValueError(
                "estimated_parts_cost_cents must be an integer or None "
                f"(got {estimated_parts_cost_cents!r})"
            ) from e
        if estimated_parts_cost_cents < 0:
            raise ValueError(
                "estimated_parts_cost_cents must be >= 0 "
                f"(got {estimated_parts_cost_cents})"
            )

    with get_connection(db_path) as conn:
        _require_row(conn, "shops", shop_id, "shop")
        _require_row(conn, "vehicles", vehicle_id, "vehicle")
        _require_row(conn, "customers", customer_id, "customer")
        if intake_visit_id is not None:
            intake = _require_row(
                conn, "intake_visits", intake_visit_id, "intake visit",
            )
            # Cross-table consistency at moment of creation.
            mismatches: list[str] = []
            if intake["shop_id"] != shop_id:
                mismatches.append(
                    f"shop_id {shop_id} vs intake.shop_id {intake['shop_id']}"
                )
            if intake["vehicle_id"] != vehicle_id:
                mismatches.append(
                    f"vehicle_id {vehicle_id} vs intake.vehicle_id "
                    f"{intake['vehicle_id']}"
                )
            if intake["customer_id"] != customer_id:
                mismatches.append(
                    f"customer_id {customer_id} vs intake.customer_id "
                    f"{intake['customer_id']}"
                )
            if mismatches:
                raise ValueError(
                    "intake_visit denormalization mismatch: "
                    + "; ".join(mismatches)
                )
        if assigned_mechanic_user_id is not None:
            _require_row(
                conn, "users", assigned_mechanic_user_id, "mechanic user",
            )

        try:
            cursor = conn.execute(
                """INSERT INTO work_orders (
                    shop_id, intake_visit_id, vehicle_id, customer_id,
                    title, description, priority,
                    estimated_hours, estimated_parts_cost_cents,
                    assigned_mechanic_user_id, created_by_user_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    shop_id, intake_visit_id, vehicle_id, customer_id,
                    str(title).strip(), description, priority,
                    estimated_hours, estimated_parts_cost_cents,
                    assigned_mechanic_user_id, created_by_user_id,
                ),
            )
        except sqlite3.IntegrityError as e:
            raise WorkOrderFKError(f"FK violation creating work order: {e}") from e
        return int(cursor.lastrowid)


def get_work_order(
    wo_id: int, db_path: Optional[str] = None,
) -> Optional[dict]:
    """Fetch one work order with denormalized shop/customer/vehicle fields.

    Returns None on miss (use :func:`require_work_order` for raising).
    """
    query = """
        SELECT wo.*,
               s.name AS shop_name,
               c.name AS customer_name,
               c.phone AS customer_phone,
               c.email AS customer_email,
               v.make AS vehicle_make,
               v.model AS vehicle_model,
               v.year AS vehicle_year,
               iv.intake_at AS intake_at,
               iv.reported_problems AS intake_problems,
               u.username AS assigned_mechanic_name
        FROM work_orders wo
        LEFT JOIN shops s ON s.id = wo.shop_id
        LEFT JOIN customers c ON c.id = wo.customer_id
        LEFT JOIN vehicles v ON v.id = wo.vehicle_id
        LEFT JOIN intake_visits iv ON iv.id = wo.intake_visit_id
        LEFT JOIN users u ON u.id = wo.assigned_mechanic_user_id
        WHERE wo.id = ?
    """
    with get_connection(db_path) as conn:
        row = conn.execute(query, (wo_id,)).fetchone()
        return dict(row) if row else None


def require_work_order(
    wo_id: int, db_path: Optional[str] = None,
) -> dict:
    """:func:`get_work_order` that raises :class:`WorkOrderNotFoundError`."""
    row = get_work_order(wo_id, db_path=db_path)
    if row is None:
        raise WorkOrderNotFoundError(f"work order not found: id={wo_id}")
    return row


def list_work_orders(
    shop_id: Optional[int] = None,
    vehicle_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    assigned_mechanic_user_id: Optional[int] = None,
    status: Optional[str | list[str]] = None,
    priority: Optional[int] = None,
    since: Optional[str] = None,
    intake_visit_id: Optional[int] = None,
    include_terminal: bool = False,
    limit: int = 100,
    db_path: Optional[str] = None,
) -> list[dict]:
    """List work orders with composable filters, most-recent first.

    ``status`` can be a single string, a list of strings, or ``None``
    (meaning default: exclude terminal unless ``include_terminal=True``).
    ``since`` accepts ISO timestamp or relative offset ('7d','24h','30m')
    — reuses Phase 160's :func:`motodiag.shop.intake_repo._since_cutoff`
    lazily so both repos share semantics without coupling imports at
    module load.
    """
    # Status validation + normalization to list
    status_list: Optional[list[str]] = None
    if isinstance(status, str):
        if status.lower() == "all":
            status_list = None
            include_terminal = True
        else:
            if status not in WORK_ORDER_STATUSES:
                raise ValueError(
                    f"status must be one of {WORK_ORDER_STATUSES} or "
                    f"'all' (got {status!r})"
                )
            status_list = [status]
    elif isinstance(status, (list, tuple)):
        for s in status:
            if s not in WORK_ORDER_STATUSES:
                raise ValueError(
                    f"status entry {s!r} not in {WORK_ORDER_STATUSES}"
                )
        status_list = list(status)

    # Default behaviour: exclude terminal states unless caller asks for them.
    if status_list is None and not include_terminal:
        status_list = [
            s for s in WORK_ORDER_STATUSES if s not in TERMINAL_STATUSES
        ]

    cutoff: Optional[str] = None
    if since is not None:
        from motodiag.shop.intake_repo import _since_cutoff
        cutoff = _since_cutoff(since)

    query = """
        SELECT wo.*,
               s.name AS shop_name,
               c.name AS customer_name,
               v.make AS vehicle_make,
               v.model AS vehicle_model,
               v.year AS vehicle_year,
               u.username AS assigned_mechanic_name
        FROM work_orders wo
        LEFT JOIN shops s ON s.id = wo.shop_id
        LEFT JOIN customers c ON c.id = wo.customer_id
        LEFT JOIN vehicles v ON v.id = wo.vehicle_id
        LEFT JOIN users u ON u.id = wo.assigned_mechanic_user_id
    """
    conditions: list[str] = []
    params: list = []
    if shop_id is not None:
        conditions.append("wo.shop_id = ?")
        params.append(shop_id)
    if vehicle_id is not None:
        conditions.append("wo.vehicle_id = ?")
        params.append(vehicle_id)
    if customer_id is not None:
        conditions.append("wo.customer_id = ?")
        params.append(customer_id)
    if assigned_mechanic_user_id is not None:
        conditions.append("wo.assigned_mechanic_user_id = ?")
        params.append(assigned_mechanic_user_id)
    if intake_visit_id is not None:
        conditions.append("wo.intake_visit_id = ?")
        params.append(intake_visit_id)
    if priority is not None:
        _validate_priority(priority)
        conditions.append("wo.priority = ?")
        params.append(int(priority))
    if status_list:
        placeholders = ",".join("?" for _ in status_list)
        conditions.append(f"wo.status IN ({placeholders})")
        params.extend(status_list)
    if cutoff is not None:
        conditions.append("wo.created_at >= ?")
        params.append(cutoff)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY wo.priority ASC, wo.created_at DESC, wo.id DESC"
    if limit and limit > 0:
        query += " LIMIT ?"
        params.append(int(limit))

    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def count_work_orders(
    shop_id: Optional[int] = None,
    status: Optional[str] = None,
    assigned_mechanic_user_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> int:
    """Count work orders matching filters. Dashboard roll-up helper."""
    if status is not None and status not in WORK_ORDER_STATUSES:
        raise ValueError(
            f"status must be one of {WORK_ORDER_STATUSES} or None "
            f"(got {status!r})"
        )
    query = "SELECT COUNT(*) AS n FROM work_orders wo"
    conditions: list[str] = []
    params: list = []
    if shop_id is not None:
        conditions.append("wo.shop_id = ?")
        params.append(shop_id)
    if status is not None:
        conditions.append("wo.status = ?")
        params.append(status)
    if assigned_mechanic_user_id is not None:
        conditions.append("wo.assigned_mechanic_user_id = ?")
        params.append(assigned_mechanic_user_id)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    with get_connection(db_path) as conn:
        row = conn.execute(query, params).fetchone()
        return int(row["n"]) if row else 0


# ---------------------------------------------------------------------------
# Update (whitelist)
# ---------------------------------------------------------------------------


def update_work_order(
    wo_id: int,
    updates: dict,
    db_path: Optional[str] = None,
) -> bool:
    """Update whitelisted fields. Cannot touch status or any lifecycle column.

    Returns True on success. Raises :class:`WorkOrderNotFoundError`
    when the row does not exist.
    """
    if not isinstance(updates, dict):
        raise TypeError(f"updates must be a dict, got {type(updates).__name__}")
    filtered = {k: v for k, v in updates.items() if k in _UPDATABLE_FIELDS}
    if not filtered:
        return False

    if "priority" in filtered:
        filtered["priority"] = _validate_priority(filtered["priority"])
    if "estimated_hours" in filtered:
        filtered["estimated_hours"] = _validate_hours(
            filtered["estimated_hours"], "estimated_hours",
        )
    if "actual_hours" in filtered:
        filtered["actual_hours"] = _validate_hours(
            filtered["actual_hours"], "actual_hours",
        )
    if "title" in filtered:
        new_title = str(filtered["title"]).strip()
        if not new_title:
            raise ValueError("title must not be empty")
        filtered["title"] = new_title
    if "estimated_parts_cost_cents" in filtered and filtered[
        "estimated_parts_cost_cents"
    ] is not None:
        try:
            filtered["estimated_parts_cost_cents"] = int(
                filtered["estimated_parts_cost_cents"]
            )
        except (TypeError, ValueError) as e:
            raise ValueError(
                "estimated_parts_cost_cents must be an integer or None"
            ) from e
        if filtered["estimated_parts_cost_cents"] < 0:
            raise ValueError(
                "estimated_parts_cost_cents must be >= 0"
            )

    set_clauses = ", ".join(f"{k} = ?" for k in filtered.keys())
    params: list = list(filtered.values())
    params.append(datetime.now().isoformat())
    params.append(wo_id)

    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM work_orders WHERE id = ?", (wo_id,),
        ).fetchone()
        if row is None:
            raise WorkOrderNotFoundError(f"work order not found: id={wo_id}")
        cursor = conn.execute(
            f"UPDATE work_orders SET {set_clauses}, updated_at = ? "
            "WHERE id = ?",
            params,
        )
        return cursor.rowcount > 0


def assign_mechanic(
    wo_id: int,
    user_id: int,
    db_path: Optional[str] = None,
) -> bool:
    """Assign a mechanic to a work order. Validates user exists."""
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM work_orders WHERE id = ?", (wo_id,),
        ).fetchone()
        if row is None:
            raise WorkOrderNotFoundError(f"work order not found: id={wo_id}")
        _require_row(conn, "users", user_id, "mechanic user")
        cursor = conn.execute(
            "UPDATE work_orders SET assigned_mechanic_user_id = ?, "
            "updated_at = ? WHERE id = ?",
            (user_id, now, wo_id),
        )
        return cursor.rowcount > 0


def unassign_mechanic(
    wo_id: int, db_path: Optional[str] = None,
) -> bool:
    """Clear the assigned mechanic."""
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM work_orders WHERE id = ?", (wo_id,),
        ).fetchone()
        if row is None:
            raise WorkOrderNotFoundError(f"work order not found: id={wo_id}")
        cursor = conn.execute(
            "UPDATE work_orders SET assigned_mechanic_user_id = NULL, "
            "updated_at = ? WHERE id = ?",
            (now, wo_id),
        )
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Lifecycle transitions
# ---------------------------------------------------------------------------


def open_work_order(
    wo_id: int, db_path: Optional[str] = None,
) -> bool:
    """Transition draft → open. Sets ``opened_at`` to now."""
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, status FROM work_orders WHERE id = ?", (wo_id,),
        ).fetchone()
        if row is None:
            raise WorkOrderNotFoundError(f"work order not found: id={wo_id}")
        _assert_transition(row["status"], "open", wo_id)
        cursor = conn.execute(
            """UPDATE work_orders
                   SET status = 'open',
                       opened_at = COALESCE(opened_at, ?),
                       updated_at = ?
                 WHERE id = ?""",
            (now, now, wo_id),
        )
        return cursor.rowcount > 0


def start_work(
    wo_id: int, db_path: Optional[str] = None,
) -> bool:
    """Transition open | on_hold → in_progress. Sets ``started_at``.

    ``started_at`` is overwritten on each start — reflects the most
    recent resumption of work. ``on_hold_reason`` is cleared when
    resuming from on_hold (so the UI does not carry a stale reason).
    """
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, status FROM work_orders WHERE id = ?", (wo_id,),
        ).fetchone()
        if row is None:
            raise WorkOrderNotFoundError(f"work order not found: id={wo_id}")
        _assert_transition(row["status"], "in_progress", wo_id)
        cursor = conn.execute(
            """UPDATE work_orders
                   SET status = 'in_progress',
                       started_at = ?,
                       on_hold_reason = NULL,
                       updated_at = ?
                 WHERE id = ?""",
            (now, now, wo_id),
        )
        return cursor.rowcount > 0


def pause_work(
    wo_id: int,
    reason: Optional[str] = None,
    db_path: Optional[str] = None,
) -> bool:
    """Transition in_progress → on_hold with optional reason."""
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, status FROM work_orders WHERE id = ?", (wo_id,),
        ).fetchone()
        if row is None:
            raise WorkOrderNotFoundError(f"work order not found: id={wo_id}")
        _assert_transition(row["status"], "on_hold", wo_id)
        cursor = conn.execute(
            """UPDATE work_orders
                   SET status = 'on_hold',
                       on_hold_reason = ?,
                       updated_at = ?
                 WHERE id = ?""",
            (reason, now, wo_id),
        )
        return cursor.rowcount > 0


def resume_work(
    wo_id: int, db_path: Optional[str] = None,
) -> bool:
    """Alias for :func:`start_work` when prior status is on_hold.

    If the work order is not on_hold, raises
    :class:`InvalidWorkOrderTransition` so callers get a more specific
    error than the generic start_work path.
    """
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, status FROM work_orders WHERE id = ?", (wo_id,),
        ).fetchone()
        if row is None:
            raise WorkOrderNotFoundError(f"work order not found: id={wo_id}")
        if row["status"] != "on_hold":
            raise InvalidWorkOrderTransition(
                f"work order id={wo_id} is {row['status']!r}, not "
                f"'on_hold' — use start_work() instead of resume_work()."
            )
    return start_work(wo_id, db_path=db_path)


def complete_work_order(
    wo_id: int,
    actual_hours: Optional[float] = None,
    db_path: Optional[str] = None,
) -> bool:
    """Transition in_progress → completed. Sets completed_at + closed_at.

    ``actual_hours`` is optionally persisted if supplied.
    """
    now = datetime.now().isoformat()
    actual_hours = _validate_hours(actual_hours, "actual_hours")
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, status FROM work_orders WHERE id = ?", (wo_id,),
        ).fetchone()
        if row is None:
            raise WorkOrderNotFoundError(f"work order not found: id={wo_id}")
        _assert_transition(row["status"], "completed", wo_id)
        cursor = conn.execute(
            """UPDATE work_orders
                   SET status = 'completed',
                       completed_at = ?,
                       closed_at = ?,
                       actual_hours = COALESCE(?, actual_hours),
                       updated_at = ?
                 WHERE id = ?""",
            (now, now, actual_hours, now, wo_id),
        )
        return cursor.rowcount > 0


def cancel_work_order(
    wo_id: int,
    reason: Optional[str] = "customer-withdrew",
    db_path: Optional[str] = None,
) -> bool:
    """Transition any non-terminal status → cancelled."""
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, status FROM work_orders WHERE id = ?", (wo_id,),
        ).fetchone()
        if row is None:
            raise WorkOrderNotFoundError(f"work order not found: id={wo_id}")
        _assert_transition(row["status"], "cancelled", wo_id)
        cursor = conn.execute(
            """UPDATE work_orders
                   SET status = 'cancelled',
                       cancellation_reason = ?,
                       closed_at = ?,
                       updated_at = ?
                 WHERE id = ?""",
            (reason, now, now, wo_id),
        )
        return cursor.rowcount > 0


def reopen_work_order(
    wo_id: int, db_path: Optional[str] = None,
) -> bool:
    """Transition completed | cancelled → open.

    Clears ``completed_at``, ``closed_at``, ``cancellation_reason``,
    ``on_hold_reason``. If the work wasn't actually done, the
    completion timestamp was a lie and should not persist — Phase 169
    invoicing reads completed_at for display, not logic.
    """
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, status FROM work_orders WHERE id = ?", (wo_id,),
        ).fetchone()
        if row is None:
            raise WorkOrderNotFoundError(f"work order not found: id={wo_id}")
        _assert_transition(row["status"], "open", wo_id)
        cursor = conn.execute(
            """UPDATE work_orders
                   SET status = 'open',
                       completed_at = NULL,
                       closed_at = NULL,
                       cancellation_reason = NULL,
                       on_hold_reason = NULL,
                       updated_at = ?
                 WHERE id = ?""",
            (now, wo_id),
        )
        return cursor.rowcount > 0
