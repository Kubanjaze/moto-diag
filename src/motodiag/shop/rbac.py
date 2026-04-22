"""Shop-scoped RBAC + multi-mechanic assignment (Phase 172).

Sits on top of Phase 112's global users / roles / permissions tables.
Adds per-shop role membership (a user can own one shop AND be a tech
at another) + a `work_order_assignments` audit trail.

``reassign_work_order`` updates ``work_orders.assigned_mechanic_user_id``
via Phase 161's :func:`update_work_order` whitelist — never raw SQL.
An anti-regression grep test enforces this.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from motodiag.core.database import get_connection
from motodiag.shop.work_order_repo import (
    InvalidWorkOrderTransition, TERMINAL_STATUSES, WorkOrderNotFoundError,
    require_work_order, update_work_order,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


SHOP_ROLES: tuple[str, ...] = (
    "owner", "tech", "service_writer", "apprentice",
)

ShopRole = Literal["owner", "tech", "service_writer", "apprentice"]

# Roles that can be assigned to a work order (do the actual wrenching)
ELIGIBLE_ASSIGN_ROLES: tuple[str, ...] = ("owner", "tech")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ShopMembershipNotFoundError(ValueError):
    """Raised when a (shop_id, user_id) pair has no membership row."""


class InvalidRoleError(ValueError):
    """Raised when a role string is not in SHOP_ROLES."""


class PermissionDenied(PermissionError):
    """Raised by require_shop_permission on a denied check."""


class MechanicNotInShopError(ValueError):
    """Raised when reassigning to a user who is not an active
    tech/owner of the WO's shop."""


# ---------------------------------------------------------------------------
# Pydantic
# ---------------------------------------------------------------------------


class ShopMember(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: int
    shop_id: int
    role: str
    joined_at: str
    is_active: bool
    username: Optional[str] = None
    full_name: Optional[str] = None


class WorkOrderAssignment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    work_order_id: int
    mechanic_user_id: Optional[int]
    mechanic_username: Optional[str] = None
    assigned_at: str
    unassigned_at: Optional[str] = None
    assigned_by_user_id: Optional[int] = None
    reason: Optional[str] = None


class MechanicWorkload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    mechanic_user_id: int
    open_count: int = 0
    in_progress_count: int = 0
    on_hold_count: int = 0
    total_open: int = 0


# ---------------------------------------------------------------------------
# Membership CRUD
# ---------------------------------------------------------------------------


def _validate_role(role: str) -> None:
    if role not in SHOP_ROLES:
        raise InvalidRoleError(
            f"role {role!r} not in {SHOP_ROLES}"
        )


def _row_to_member(row) -> ShopMember:
    d = dict(row)
    return ShopMember(
        user_id=int(d["user_id"]),
        shop_id=int(d["shop_id"]),
        role=str(d["role"]),
        joined_at=str(d["joined_at"]),
        is_active=bool(d["is_active"]),
        username=d.get("username"),
        full_name=d.get("full_name"),
    )


def add_shop_member(
    shop_id: int, user_id: int, role: str,
    db_path: Optional[str] = None,
) -> bool:
    """Insert or reactivate. Idempotent: adding an existing active
    member with the same role is a no-op; an existing deactivated row
    is reactivated and role-updated."""
    _validate_role(role)
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT role, is_active FROM shop_members "
            "WHERE shop_id = ? AND user_id = ?",
            (shop_id, user_id),
        ).fetchone()
        if row is None:
            conn.execute(
                """INSERT INTO shop_members
                   (user_id, shop_id, role, is_active, updated_at)
                   VALUES (?, ?, ?, 1, ?)""",
                (user_id, shop_id, role, now),
            )
            return True
        # Reactivate + role-update
        conn.execute(
            "UPDATE shop_members SET role = ?, is_active = 1, "
            "updated_at = ? WHERE shop_id = ? AND user_id = ?",
            (role, now, shop_id, user_id),
        )
        return True


def get_shop_member(
    shop_id: int, user_id: int, db_path: Optional[str] = None,
) -> Optional[ShopMember]:
    with get_connection(db_path) as conn:
        row = conn.execute(
            """SELECT sm.*, u.username, u.full_name
               FROM shop_members sm
               LEFT JOIN users u ON u.id = sm.user_id
               WHERE sm.shop_id = ? AND sm.user_id = ?""",
            (shop_id, user_id),
        ).fetchone()
    return _row_to_member(row) if row else None


def list_shop_members(
    shop_id: int, role: Optional[str] = None,
    active_only: bool = True, db_path: Optional[str] = None,
) -> list[ShopMember]:
    if role is not None:
        _validate_role(role)
    query = (
        "SELECT sm.*, u.username, u.full_name "
        "FROM shop_members sm "
        "LEFT JOIN users u ON u.id = sm.user_id "
        "WHERE sm.shop_id = ?"
    )
    params: list = [shop_id]
    if active_only:
        query += " AND sm.is_active = 1"
    if role is not None:
        query += " AND sm.role = ?"
        params.append(role)
    query += " ORDER BY sm.role, sm.user_id"
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_member(r) for r in rows]


def set_member_role(
    shop_id: int, user_id: int, role: str,
    db_path: Optional[str] = None,
) -> bool:
    _validate_role(role)
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT role FROM shop_members "
            "WHERE shop_id = ? AND user_id = ?",
            (shop_id, user_id),
        ).fetchone()
        if row is None:
            raise ShopMembershipNotFoundError(
                f"no membership: shop_id={shop_id}, user_id={user_id}"
            )
        cursor = conn.execute(
            "UPDATE shop_members SET role = ?, updated_at = ? "
            "WHERE shop_id = ? AND user_id = ?",
            (role, now, shop_id, user_id),
        )
        return cursor.rowcount > 0


def _set_active(
    shop_id: int, user_id: int, active: int,
    db_path: Optional[str],
) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT is_active FROM shop_members "
            "WHERE shop_id = ? AND user_id = ?",
            (shop_id, user_id),
        ).fetchone()
        if row is None:
            raise ShopMembershipNotFoundError(
                f"no membership: shop_id={shop_id}, user_id={user_id}"
            )
        cursor = conn.execute(
            "UPDATE shop_members SET is_active = ?, updated_at = ? "
            "WHERE shop_id = ? AND user_id = ?",
            (active, now, shop_id, user_id),
        )
        return cursor.rowcount > 0


def deactivate_member(
    shop_id: int, user_id: int, db_path: Optional[str] = None,
) -> bool:
    return _set_active(shop_id, user_id, 0, db_path)


def reactivate_member(
    shop_id: int, user_id: int, db_path: Optional[str] = None,
) -> bool:
    return _set_active(shop_id, user_id, 1, db_path)


def list_shops_for_user(
    user_id: int, active_only: bool = True,
    db_path: Optional[str] = None,
) -> list[ShopMember]:
    query = (
        "SELECT sm.*, u.username, u.full_name "
        "FROM shop_members sm "
        "LEFT JOIN users u ON u.id = sm.user_id "
        "WHERE sm.user_id = ?"
    )
    params: list = [user_id]
    if active_only:
        query += " AND sm.is_active = 1"
    query += " ORDER BY sm.shop_id"
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_member(r) for r in rows]


def seed_first_owner(
    shop_id: int, owner_user_id: int,
    db_path: Optional[str] = None,
) -> bool:
    """Idempotent: add owner membership if none exists.

    Phase 160 doesn't know about Phase 172 yet, so newly-created shops
    have no member rows. This helper lets callers + backfill scripts
    stamp an owner without racing on duplicate inserts.
    """
    existing = get_shop_member(shop_id, owner_user_id, db_path=db_path)
    if existing is not None and existing.is_active and existing.role == "owner":
        return False
    add_shop_member(shop_id, owner_user_id, "owner", db_path=db_path)
    return True


# ---------------------------------------------------------------------------
# Shop-scoped permission checks
# ---------------------------------------------------------------------------


def has_shop_permission(
    shop_id: int, user_id: int, permission: str,
    db_path: Optional[str] = None,
) -> bool:
    """Walk shop_members.role → roles → role_permissions → permissions."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            """SELECT 1
               FROM shop_members sm
               JOIN roles r ON r.name = sm.role
               JOIN role_permissions rp ON rp.role_id = r.id
               JOIN permissions p ON p.id = rp.permission_id
               WHERE sm.shop_id = ? AND sm.user_id = ?
                 AND sm.is_active = 1
                 AND p.name = ?
               LIMIT 1""",
            (shop_id, user_id, permission),
        ).fetchone()
    return row is not None


def require_shop_permission(
    shop_id: int, user_id: int, permission: str,
    db_path: Optional[str] = None,
) -> None:
    if not has_shop_permission(shop_id, user_id, permission, db_path=db_path):
        raise PermissionDenied(
            f"user id={user_id} lacks {permission!r} at shop id={shop_id}"
        )


def list_shop_mechanics(
    shop_id: int, active_only: bool = True,
    db_path: Optional[str] = None,
) -> list[ShopMember]:
    """Members eligible for WO assignment (tech + owner)."""
    query = (
        "SELECT sm.*, u.username, u.full_name "
        "FROM shop_members sm "
        "LEFT JOIN users u ON u.id = sm.user_id "
        "WHERE sm.shop_id = ? AND sm.role IN ('tech', 'owner')"
    )
    params: list = [shop_id]
    if active_only:
        query += " AND sm.is_active = 1"
    query += " ORDER BY sm.role DESC, sm.user_id"  # owner first, then techs
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_member(r) for r in rows]


def _is_active_assignable(
    shop_id: int, user_id: int, db_path: Optional[str],
) -> bool:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM shop_members "
            "WHERE shop_id = ? AND user_id = ? AND is_active = 1 "
            "AND role IN ('tech', 'owner') LIMIT 1",
            (shop_id, user_id),
        ).fetchone()
    return row is not None


# ---------------------------------------------------------------------------
# Work-order assignment flow
# ---------------------------------------------------------------------------


def _row_to_assignment(row) -> WorkOrderAssignment:
    d = dict(row)
    return WorkOrderAssignment(
        id=int(d["id"]),
        work_order_id=int(d["work_order_id"]),
        mechanic_user_id=d.get("mechanic_user_id"),
        mechanic_username=d.get("mechanic_username"),
        assigned_at=str(d["assigned_at"]),
        unassigned_at=d.get("unassigned_at"),
        assigned_by_user_id=d.get("assigned_by_user_id"),
        reason=d.get("reason"),
    )


def reassign_work_order(
    wo_id: int,
    new_mechanic_user_id: Optional[int],
    assigned_by_user_id: Optional[int] = None,
    reason: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    """Change WO assignment + log to work_order_assignments.

    Closes the current open assignment (if any) by stamping
    `unassigned_at`. Inserts a new row with the new mechanic
    (or NULL if unassigning). Updates
    `work_orders.assigned_mechanic_user_id` via Phase 161
    :func:`update_work_order` — never raw SQL.

    Raises :class:`InvalidWorkOrderTransition` if WO is terminal.
    Raises :class:`MechanicNotInShopError` if new mechanic is not an
    active tech/owner of the WO's shop.

    Returns the new assignment_id.
    """
    wo = require_work_order(wo_id, db_path=db_path)
    if wo["status"] in TERMINAL_STATUSES:
        raise InvalidWorkOrderTransition(
            f"work order id={wo_id} is terminal ({wo['status']!r}); "
            "cannot reassign"
        )
    if new_mechanic_user_id is not None:
        if not _is_active_assignable(
            wo["shop_id"], new_mechanic_user_id, db_path,
        ):
            raise MechanicNotInShopError(
                f"user id={new_mechanic_user_id} is not an active "
                f"tech/owner of shop id={wo['shop_id']}"
            )
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        # Close any currently-open assignment for this WO
        conn.execute(
            """UPDATE work_order_assignments
               SET unassigned_at = ?
               WHERE work_order_id = ? AND unassigned_at IS NULL""",
            (now, wo_id),
        )
        cursor = conn.execute(
            """INSERT INTO work_order_assignments
               (work_order_id, mechanic_user_id, assigned_at,
                assigned_by_user_id, reason)
               VALUES (?, ?, ?, ?, ?)""",
            (
                wo_id, new_mechanic_user_id, now,
                assigned_by_user_id, reason,
            ),
        )
        new_id = int(cursor.lastrowid)
    # Write-back through Phase 161 whitelist (no raw UPDATE work_orders SQL).
    update_work_order(
        wo_id,
        {"assigned_mechanic_user_id": new_mechanic_user_id},
        db_path=db_path,
    )
    return new_id


def list_work_order_assignments(
    wo_id: int, db_path: Optional[str] = None,
) -> list[WorkOrderAssignment]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT wa.*, u.username AS mechanic_username
               FROM work_order_assignments wa
               LEFT JOIN users u ON u.id = wa.mechanic_user_id
               WHERE wa.work_order_id = ?
               ORDER BY wa.assigned_at DESC, wa.id DESC""",
            (wo_id,),
        ).fetchall()
    return [_row_to_assignment(r) for r in rows]


def current_assignment(
    wo_id: int, db_path: Optional[str] = None,
) -> Optional[WorkOrderAssignment]:
    with get_connection(db_path) as conn:
        row = conn.execute(
            """SELECT wa.*, u.username AS mechanic_username
               FROM work_order_assignments wa
               LEFT JOIN users u ON u.id = wa.mechanic_user_id
               WHERE wa.work_order_id = ? AND wa.unassigned_at IS NULL
               ORDER BY wa.id DESC LIMIT 1""",
            (wo_id,),
        ).fetchone()
    return _row_to_assignment(row) if row else None


def mechanic_workload(
    mechanic_user_id: int,
    shop_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> MechanicWorkload:
    query = (
        "SELECT status, COUNT(*) AS n FROM work_orders "
        "WHERE assigned_mechanic_user_id = ? "
        "AND status IN ('open', 'in_progress', 'on_hold')"
    )
    params: list = [mechanic_user_id]
    if shop_id is not None:
        query += " AND shop_id = ?"
        params.append(shop_id)
    query += " GROUP BY status"
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    by_status = {r["status"]: int(r["n"]) for r in rows}
    open_c = int(by_status.get("open", 0))
    ip_c = int(by_status.get("in_progress", 0))
    oh_c = int(by_status.get("on_hold", 0))
    return MechanicWorkload(
        mechanic_user_id=mechanic_user_id,
        open_count=open_c, in_progress_count=ip_c, on_hold_count=oh_c,
        total_open=open_c + ip_c + oh_c,
    )
