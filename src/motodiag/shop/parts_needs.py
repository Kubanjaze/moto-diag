"""Parts-needs aggregation (Phase 165).

Bridges Phase 153 parts catalog (`parts` + `parts_xref`) to Phase 161
work_orders. Three new tables (migration 029):
- ``work_order_parts`` — junction with 5-state lifecycle (open → ordered
  → received → installed; + cancelled from any non-terminal).
- ``parts_requisitions`` — immutable consolidated shopping-list snapshots.
- ``parts_requisition_items`` — frozen per-part rows in a snapshot.

CRITICAL: every state-changing function ends with
:func:`_recompute_wo_parts_cost(wo_id)` which writes back to
``work_orders.estimated_parts_cost_cents`` via Phase 161
:func:`update_work_order` whitelist — NEVER raw SQL. Preserves the
lifecycle guard + audit integrity Phase 161 established.

Phase 164 contract: this module exports
:func:`list_parts_for_wo` — Phase 164's triage queue's
``_parts_available_for`` soft-guard calls this exact function name when
the module is importable.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from motodiag.advanced.parts_repo import get_xrefs
from motodiag.core.database import get_connection
from motodiag.shop.work_order_repo import (
    WorkOrderNotFoundError, require_work_order, update_work_order,
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class WorkOrderPartNotFoundError(ValueError):
    """Raised when a work_order_parts row id does not resolve."""


class InvalidPartNeedTransition(ValueError):
    """Raised when a status transition is illegal given current state."""


class PartNotInCatalogError(ValueError):
    """Raised when a part_id is not in the Phase 153 catalog."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


PART_STATUSES: tuple[str, ...] = (
    "open", "ordered", "received", "installed", "cancelled",
)


_VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    "open":      frozenset({"ordered", "cancelled"}),
    "ordered":   frozenset({"received", "cancelled"}),
    "received":  frozenset({"installed", "cancelled"}),
    "installed": frozenset(),                  # terminal
    "cancelled": frozenset(),                  # terminal
}


# ---------------------------------------------------------------------------
# Pydantic
# ---------------------------------------------------------------------------


PartCostSource = Literal["override", "catalog", "zero"]
PartLineStatus = Literal["open", "ordered", "received", "installed", "cancelled"]


class WorkOrderPartLine(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    work_order_id: int
    part_id: int
    part_slug: str
    part_number: Optional[str] = None
    part_brand: Optional[str] = None
    part_description: Optional[str] = None
    part_category: Optional[str] = None
    quantity: int
    unit_cost_cents: int
    unit_cost_source: PartCostSource
    line_subtotal_cents: int
    status: PartLineStatus
    ordered_at: Optional[str] = None
    received_at: Optional[str] = None
    installed_at: Optional[str] = None
    notes: Optional[str] = None


class ConsolidatedPartNeed(BaseModel):
    model_config = ConfigDict(extra="ignore")

    part_id: int
    part_slug: str
    part_number: Optional[str] = None
    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    total_quantity: int
    wo_ids: list[int] = Field(default_factory=list)
    estimated_cost_cents: int
    oem_cost_cents: Optional[int] = None
    aftermarket_cost_cents: Optional[int] = None


class Requisition(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    shop_id: int
    generated_at: str
    generated_by_user_id: int
    wo_id_scope: Optional[list[int]] = None
    total_distinct_parts: int
    total_quantity: int
    total_estimated_cost_cents: int
    items: list[ConsolidatedPartNeed] = Field(default_factory=list)
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Cost recompute (routes through Phase 161 update_work_order — NEVER raw SQL)
# ---------------------------------------------------------------------------


def _recompute_wo_parts_cost(
    wo_id: int, db_path: Optional[str] = None,
) -> int:
    """Recompute work_orders.estimated_parts_cost_cents transactionally.

    Sums quantity * effective_unit_cost across non-cancelled
    work_order_parts rows then writes via Phase 161 update_work_order
    whitelist. CRITICAL: never raw SQL.
    """
    with get_connection(db_path) as conn:
        row = conn.execute(
            """SELECT COALESCE(SUM(
                wop.quantity * COALESCE(
                    wop.unit_cost_cents_override, p.typical_cost_cents, 0
                )
            ), 0) AS total
            FROM work_order_parts wop
            JOIN parts p ON p.id = wop.part_id
            WHERE wop.work_order_id = ? AND wop.status != 'cancelled'""",
            (wo_id,),
        ).fetchone()
    new_total = int(row["total"]) if row else 0
    update_work_order(
        wo_id, {"estimated_parts_cost_cents": new_total},
        db_path=db_path,
    )
    return new_total


# ---------------------------------------------------------------------------
# Part validators
# ---------------------------------------------------------------------------


def _require_part(
    conn: sqlite3.Connection, part_id: int,
) -> dict:
    """Fetch parts row by id; raise PartNotInCatalogError on miss."""
    row = conn.execute(
        "SELECT id, slug, oem_part_number, brand, description, category, "
        "       typical_cost_cents "
        "FROM parts WHERE id = ?",
        (part_id,),
    ).fetchone()
    if row is None:
        raise PartNotInCatalogError(f"part not in catalog: id={part_id}")
    return dict(row)


def _resolve_unit_cost(
    override: Optional[int], catalog_cost: Optional[int],
) -> tuple[int, PartCostSource]:
    """Effective unit cost + source flag."""
    if override is not None:
        return (int(override), "override")
    if catalog_cost is not None and catalog_cost > 0:
        return (int(catalog_cost), "catalog")
    return (0, "zero")


def _row_to_line(row: dict) -> WorkOrderPartLine:
    """Map a JOINed work_order_parts + parts row to WorkOrderPartLine."""
    unit_cost, source = _resolve_unit_cost(
        row.get("unit_cost_cents_override"),
        row.get("typical_cost_cents"),
    )
    qty = int(row.get("quantity", 1))
    return WorkOrderPartLine(
        id=row["id"],
        work_order_id=row["work_order_id"],
        part_id=row["part_id"],
        part_slug=str(row.get("slug") or ""),
        part_number=row.get("oem_part_number"),
        part_brand=row.get("brand"),
        part_description=row.get("description"),
        part_category=row.get("category"),
        quantity=qty,
        unit_cost_cents=unit_cost,
        unit_cost_source=source,
        line_subtotal_cents=qty * unit_cost,
        status=row.get("status", "open"),
        ordered_at=row.get("ordered_at"),
        received_at=row.get("received_at"),
        installed_at=row.get("installed_at"),
        notes=row.get("notes"),
    )


# ---------------------------------------------------------------------------
# Public API — CRUD
# ---------------------------------------------------------------------------


def add_part_to_work_order(
    wo_id: int,
    part_id: int,
    quantity: int = 1,
    unit_cost_override: Optional[int] = None,
    notes: Optional[str] = None,
    created_by_user_id: int = 1,
    db_path: Optional[str] = None,
) -> int:
    """Insert a work_order_parts row. Returns the new wop_id.

    Pre-checks: WO exists (raises WorkOrderNotFoundError), part exists
    in Phase 153 catalog (raises PartNotInCatalogError), quantity > 0
    (raises ValueError), unit_cost_override is None or int >= 0
    (raises ValueError).

    On success, calls :func:`_recompute_wo_parts_cost` transactionally
    to refresh the parent WO's ``estimated_parts_cost_cents``.
    """
    if quantity is None or int(quantity) <= 0:
        raise ValueError(f"quantity must be > 0 (got {quantity!r})")
    if unit_cost_override is not None:
        try:
            unit_cost_override = int(unit_cost_override)
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"unit_cost_override must be int or None (got "
                f"{unit_cost_override!r})"
            ) from e
        if unit_cost_override < 0:
            raise ValueError(
                f"unit_cost_override must be >= 0 (got {unit_cost_override})"
            )
    require_work_order(wo_id, db_path=db_path)
    with get_connection(db_path) as conn:
        _require_part(conn, part_id)
        cursor = conn.execute(
            """INSERT INTO work_order_parts
               (work_order_id, part_id, quantity, unit_cost_cents_override,
                notes, created_by_user_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                wo_id, part_id, int(quantity), unit_cost_override,
                notes, created_by_user_id,
            ),
        )
        wop_id = int(cursor.lastrowid)
    _recompute_wo_parts_cost(wo_id, db_path=db_path)
    return wop_id


def remove_part_from_work_order(
    wop_id: int, db_path: Optional[str] = None,
) -> bool:
    """Delete a work_order_parts row + recompute parent WO cost."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT work_order_id FROM work_order_parts WHERE id = ?",
            (wop_id,),
        ).fetchone()
        if row is None:
            raise WorkOrderPartNotFoundError(
                f"work_order_part not found: id={wop_id}"
            )
        wo_id = int(row["work_order_id"])
        cursor = conn.execute(
            "DELETE FROM work_order_parts WHERE id = ?", (wop_id,),
        )
        if cursor.rowcount == 0:
            return False
    _recompute_wo_parts_cost(wo_id, db_path=db_path)
    return True


def update_part_quantity(
    wop_id: int, quantity: int, db_path: Optional[str] = None,
) -> bool:
    """Change quantity on an existing line; triggers cost recompute."""
    if quantity is None or int(quantity) <= 0:
        raise ValueError(f"quantity must be > 0 (got {quantity!r})")
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT work_order_id FROM work_order_parts WHERE id = ?",
            (wop_id,),
        ).fetchone()
        if row is None:
            raise WorkOrderPartNotFoundError(
                f"work_order_part not found: id={wop_id}"
            )
        wo_id = int(row["work_order_id"])
        conn.execute(
            "UPDATE work_order_parts SET quantity = ?, updated_at = ? "
            "WHERE id = ?",
            (int(quantity), datetime.now(timezone.utc).isoformat(), wop_id),
        )
    _recompute_wo_parts_cost(wo_id, db_path=db_path)
    return True


def update_part_cost_override(
    wop_id: int,
    unit_cost_override: Optional[int],
    db_path: Optional[str] = None,
) -> bool:
    """Set or clear (None) the per-line cost override; triggers cost recompute."""
    if unit_cost_override is not None:
        try:
            unit_cost_override = int(unit_cost_override)
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"unit_cost_override must be int or None (got {unit_cost_override!r})"
            ) from e
        if unit_cost_override < 0:
            raise ValueError("unit_cost_override must be >= 0")
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT work_order_id FROM work_order_parts WHERE id = ?",
            (wop_id,),
        ).fetchone()
        if row is None:
            raise WorkOrderPartNotFoundError(
                f"work_order_part not found: id={wop_id}"
            )
        wo_id = int(row["work_order_id"])
        conn.execute(
            "UPDATE work_order_parts "
            "SET unit_cost_cents_override = ?, updated_at = ? WHERE id = ?",
            (
                unit_cost_override,
                datetime.now(timezone.utc).isoformat(),
                wop_id,
            ),
        )
    _recompute_wo_parts_cost(wo_id, db_path=db_path)
    return True


def cancel_part_need(
    wop_id: int, reason: Optional[str] = None,
    db_path: Optional[str] = None,
) -> bool:
    """Cancel a line from any non-terminal status; triggers recompute."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT work_order_id, status, notes FROM work_order_parts "
            "WHERE id = ?", (wop_id,),
        ).fetchone()
        if row is None:
            raise WorkOrderPartNotFoundError(
                f"work_order_part not found: id={wop_id}"
            )
        if row["status"] in ("cancelled", "installed"):
            raise InvalidPartNeedTransition(
                f"work_order_part id={wop_id} is terminal "
                f"({row['status']!r}); cannot cancel"
            )
        wo_id = int(row["work_order_id"])
        new_notes = row["notes"]
        if reason:
            new_notes = (
                f"[CANCELLED]: {reason}"
                + (f" | {row['notes']}" if row["notes"] else "")
            )
        conn.execute(
            "UPDATE work_order_parts "
            "SET status = 'cancelled', notes = ?, updated_at = ? WHERE id = ?",
            (new_notes, datetime.now(timezone.utc).isoformat(), wop_id),
        )
    _recompute_wo_parts_cost(wo_id, db_path=db_path)
    return True


# ---------------------------------------------------------------------------
# Lifecycle transitions
# ---------------------------------------------------------------------------


def _transition(
    wop_id: int, target: str, db_path: Optional[str] = None,
) -> bool:
    """Generic guarded transition with timestamp side-effect."""
    now = datetime.now(timezone.utc).isoformat()
    timestamp_col = {
        "ordered": "ordered_at",
        "received": "received_at",
        "installed": "installed_at",
    }.get(target)
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT status FROM work_order_parts WHERE id = ?",
            (wop_id,),
        ).fetchone()
        if row is None:
            raise WorkOrderPartNotFoundError(
                f"work_order_part not found: id={wop_id}"
            )
        if target not in _VALID_TRANSITIONS.get(row["status"], frozenset()):
            raise InvalidPartNeedTransition(
                f"work_order_part id={wop_id}: cannot transition "
                f"{row['status']!r} → {target!r}. Legal from {row['status']!r}: "
                f"{sorted(_VALID_TRANSITIONS.get(row['status'], []))}"
            )
        if timestamp_col:
            conn.execute(
                f"UPDATE work_order_parts SET status = ?, "
                f"{timestamp_col} = ?, updated_at = ? WHERE id = ?",
                (target, now, now, wop_id),
            )
        else:
            conn.execute(
                "UPDATE work_order_parts SET status = ?, updated_at = ? "
                "WHERE id = ?",
                (target, now, wop_id),
            )
        return True


def mark_part_ordered(wop_id: int, db_path: Optional[str] = None) -> bool:
    """open → ordered; sets ordered_at."""
    return _transition(wop_id, "ordered", db_path=db_path)


def mark_part_received(wop_id: int, db_path: Optional[str] = None) -> bool:
    """ordered → received; sets received_at."""
    return _transition(wop_id, "received", db_path=db_path)


def mark_part_installed(wop_id: int, db_path: Optional[str] = None) -> bool:
    """received → installed; sets installed_at. (Terminal — Phase 166 surface.)"""
    return _transition(wop_id, "installed", db_path=db_path)


# ---------------------------------------------------------------------------
# Read APIs
# ---------------------------------------------------------------------------


def list_parts_for_wo(
    wo_id: int,
    include_cancelled: bool = False,
    db_path: Optional[str] = None,
) -> list[dict]:
    """Return all parts lines for a single WO as denormalized dicts.

    **Phase 164 contract:** triage_queue.py soft-guards on this exact
    function name.
    """
    query = """
        SELECT wop.*,
               p.slug, p.oem_part_number, p.brand, p.description,
               p.category, p.typical_cost_cents
        FROM work_order_parts wop
        JOIN parts p ON p.id = wop.part_id
        WHERE wop.work_order_id = ?
    """
    params: list = [wo_id]
    if not include_cancelled:
        query += " AND wop.status != 'cancelled'"
    query += (
        " ORDER BY CASE wop.status "
        "WHEN 'open' THEN 1 WHEN 'ordered' THEN 2 "
        "WHEN 'received' THEN 3 WHEN 'installed' THEN 4 "
        "WHEN 'cancelled' THEN 5 ELSE 6 END, "
        "p.category, wop.id"
    )
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    out = []
    for row in rows:
        d = dict(row)
        # Add resolved unit cost + part_slug for Phase 164 soft-guard caller
        unit_cost, source = _resolve_unit_cost(
            d.get("unit_cost_cents_override"),
            d.get("typical_cost_cents"),
        )
        d["unit_cost_cents"] = unit_cost
        d["unit_cost_source"] = source
        d["part_slug"] = d.get("slug")
        d["line_subtotal_cents"] = int(d.get("quantity", 1)) * unit_cost
        out.append(d)
    return out


def list_parts_for_shop_open_wos(
    shop_id: int,
    only_statuses: tuple[str, ...] = ("open", "ordered"),
    db_path: Optional[str] = None,
) -> list[ConsolidatedPartNeed]:
    """Aggregate open parts across all active WOs for a shop.

    Active WO = work_orders.status IN ('open', 'in_progress', 'on_hold').
    Active part line = work_order_parts.status IN only_statuses.

    Returns one ConsolidatedPartNeed per distinct part_id.
    OEM/aftermarket cost columns populated via parts_repo.get_xrefs.
    """
    placeholders = ",".join("?" for _ in only_statuses)
    query = f"""
        SELECT wop.part_id, wop.work_order_id, wop.quantity,
               wop.unit_cost_cents_override,
               p.slug, p.oem_part_number, p.brand, p.description, p.category,
               p.typical_cost_cents
        FROM work_order_parts wop
        JOIN parts p ON p.id = wop.part_id
        JOIN work_orders wo ON wo.id = wop.work_order_id
        WHERE wo.shop_id = ?
          AND wo.status IN ('open', 'in_progress', 'on_hold')
          AND wop.status IN ({placeholders})
    """
    params: list = [shop_id, *only_statuses]
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()

    by_part: dict[int, dict] = {}
    for row in rows:
        d = dict(row)
        pid = int(d["part_id"])
        unit_cost, _ = _resolve_unit_cost(
            d.get("unit_cost_cents_override"),
            d.get("typical_cost_cents"),
        )
        line_cost = int(d.get("quantity", 1)) * unit_cost
        if pid not in by_part:
            by_part[pid] = {
                "part_id": pid,
                "part_slug": d.get("slug") or "",
                "part_number": d.get("oem_part_number"),
                "name": d.get("description") or d.get("slug") or "",
                "brand": d.get("brand"),
                "category": d.get("category"),
                "total_quantity": 0,
                "wo_ids": set(),
                "estimated_cost_cents": 0,
            }
        by_part[pid]["total_quantity"] += int(d.get("quantity", 1))
        by_part[pid]["wo_ids"].add(int(d["work_order_id"]))
        by_part[pid]["estimated_cost_cents"] += line_cost

    results: list[ConsolidatedPartNeed] = []
    for pid, agg in by_part.items():
        # Phase 153 xref enrichment for OEM/aftermarket cost surfacing
        oem_cost = None
        aftermarket_cost = None
        try:
            xrefs = get_xrefs(pid, db_path=db_path) or []
            for xr in xrefs:
                # xrefs returns {role, part: {...}, equivalence_rating, ...}
                role = xr.get("role")
                part = xr.get("part") or {}
                cost = part.get("typical_cost_cents")
                if cost is None:
                    continue
                if role == "oem" and oem_cost is None:
                    oem_cost = int(cost)
                elif role == "aftermarket":
                    if aftermarket_cost is None or int(cost) < aftermarket_cost:
                        aftermarket_cost = int(cost)
        except Exception:
            pass
        results.append(ConsolidatedPartNeed(
            part_id=pid,
            part_slug=agg["part_slug"],
            part_number=agg["part_number"],
            name=agg["name"],
            brand=agg["brand"],
            category=agg["category"],
            total_quantity=agg["total_quantity"],
            wo_ids=sorted(agg["wo_ids"]),
            estimated_cost_cents=agg["estimated_cost_cents"],
            oem_cost_cents=oem_cost,
            aftermarket_cost_cents=aftermarket_cost,
        ))
    # Sort by estimated_cost_cents DESC (most expensive first)
    results.sort(key=lambda r: -r.estimated_cost_cents)
    return results


# ---------------------------------------------------------------------------
# Requisitions (immutable snapshots)
# ---------------------------------------------------------------------------


def build_requisition(
    shop_id: int,
    wo_ids: Optional[list[int]] = None,
    generated_by_user_id: int = 1,
    notes: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    """Snapshot the consolidated parts shopping list. Returns new req_id.

    When ``wo_ids`` is None, snapshots all active WOs for the shop.
    When supplied, validates each wo_id belongs to ``shop_id``; raises
    ValueError on any mismatch.

    Transactional: header insert + items insert + totals update in one
    connection. Empty result still creates a header row (counts=0).
    """
    if wo_ids is not None:
        with get_connection(db_path) as conn:
            placeholders = ",".join("?" for _ in wo_ids)
            rows = conn.execute(
                f"SELECT id, shop_id FROM work_orders WHERE id IN ({placeholders})",
                tuple(wo_ids),
            ).fetchall()
            found = {int(r["id"]) for r in rows}
            missing = [w for w in wo_ids if w not in found]
            if missing:
                raise ValueError(f"work orders not found: {missing}")
            mismatches = [
                int(r["id"]) for r in rows if int(r["shop_id"]) != shop_id
            ]
            if mismatches:
                raise ValueError(
                    f"wo_ids do not belong to shop_id={shop_id}: {mismatches}"
                )

    # Build aggregation either via list_parts_for_shop_open_wos (when
    # wo_ids is None) or scoped manually
    if wo_ids is None:
        items = list_parts_for_shop_open_wos(shop_id, db_path=db_path)
        scope_json = None
    else:
        # Manual scoped aggregation
        if not wo_ids:
            items = []
            scope_json = "[]"
        else:
            placeholders = ",".join("?" for _ in wo_ids)
            query = f"""
                SELECT wop.part_id, wop.work_order_id, wop.quantity,
                       wop.unit_cost_cents_override,
                       p.slug, p.oem_part_number, p.brand,
                       p.description, p.category, p.typical_cost_cents
                FROM work_order_parts wop
                JOIN parts p ON p.id = wop.part_id
                WHERE wop.work_order_id IN ({placeholders})
                  AND wop.status IN ('open', 'ordered')
            """
            with get_connection(db_path) as conn:
                rows = conn.execute(query, tuple(wo_ids)).fetchall()
            by_part: dict[int, dict] = {}
            for row in rows:
                d = dict(row)
                pid = int(d["part_id"])
                unit_cost, _ = _resolve_unit_cost(
                    d.get("unit_cost_cents_override"),
                    d.get("typical_cost_cents"),
                )
                line_cost = int(d.get("quantity", 1)) * unit_cost
                if pid not in by_part:
                    by_part[pid] = {
                        "part_id": pid,
                        "part_slug": d.get("slug") or "",
                        "part_number": d.get("oem_part_number"),
                        "name": d.get("description") or d.get("slug") or "",
                        "brand": d.get("brand"),
                        "category": d.get("category"),
                        "total_quantity": 0,
                        "wo_ids": set(),
                        "estimated_cost_cents": 0,
                    }
                by_part[pid]["total_quantity"] += int(d.get("quantity", 1))
                by_part[pid]["wo_ids"].add(int(d["work_order_id"]))
                by_part[pid]["estimated_cost_cents"] += line_cost
            items = [
                ConsolidatedPartNeed(
                    part_id=agg["part_id"],
                    part_slug=agg["part_slug"],
                    part_number=agg["part_number"],
                    name=agg["name"],
                    brand=agg["brand"],
                    category=agg["category"],
                    total_quantity=agg["total_quantity"],
                    wo_ids=sorted(agg["wo_ids"]),
                    estimated_cost_cents=agg["estimated_cost_cents"],
                )
                for agg in by_part.values()
            ]
            items.sort(key=lambda r: -r.estimated_cost_cents)
            scope_json = json.dumps(sorted(int(w) for w in wo_ids))

    total_distinct = len(items)
    total_qty = sum(item.total_quantity for item in items)
    total_cost = sum(item.estimated_cost_cents for item in items)

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO parts_requisitions
               (shop_id, generated_by_user_id, wo_id_scope,
                total_distinct_parts, total_quantity,
                total_estimated_cost_cents, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                shop_id, generated_by_user_id, scope_json,
                total_distinct, total_qty, total_cost, notes,
            ),
        )
        req_id = int(cursor.lastrowid)
        for item in items:
            conn.execute(
                """INSERT INTO parts_requisition_items
                   (requisition_id, part_id, total_quantity,
                    estimated_cost_cents, contributing_wo_ids)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    req_id, item.part_id, item.total_quantity,
                    item.estimated_cost_cents,
                    json.dumps(item.wo_ids),
                ),
            )
    return req_id


def get_requisition(
    req_id: int, db_path: Optional[str] = None,
) -> Optional[Requisition]:
    """Load a requisition + its items as a Pydantic Requisition."""
    with get_connection(db_path) as conn:
        head = conn.execute(
            "SELECT * FROM parts_requisitions WHERE id = ?", (req_id,),
        ).fetchone()
        if head is None:
            return None
        item_rows = conn.execute(
            """SELECT pri.*, p.slug, p.oem_part_number, p.brand,
                      p.description, p.category
               FROM parts_requisition_items pri
               JOIN parts p ON p.id = pri.part_id
               WHERE pri.requisition_id = ?
               ORDER BY pri.estimated_cost_cents DESC, pri.id""",
            (req_id,),
        ).fetchall()
    head = dict(head)
    items: list[ConsolidatedPartNeed] = []
    for row in item_rows:
        d = dict(row)
        try:
            wo_ids = list(json.loads(d.get("contributing_wo_ids") or "[]"))
        except (TypeError, ValueError):
            wo_ids = []
        items.append(ConsolidatedPartNeed(
            part_id=int(d["part_id"]),
            part_slug=d.get("slug") or "",
            part_number=d.get("oem_part_number"),
            name=d.get("description") or d.get("slug") or "",
            brand=d.get("brand"),
            category=d.get("category"),
            total_quantity=int(d.get("total_quantity", 0)),
            wo_ids=[int(w) for w in wo_ids],
            estimated_cost_cents=int(d.get("estimated_cost_cents", 0)),
        ))
    scope = None
    if head.get("wo_id_scope"):
        try:
            scope = list(json.loads(head["wo_id_scope"]))
        except (TypeError, ValueError):
            scope = None
    return Requisition(
        id=int(head["id"]),
        shop_id=int(head["shop_id"]),
        generated_at=str(head.get("generated_at") or ""),
        generated_by_user_id=int(head.get("generated_by_user_id", 1)),
        wo_id_scope=scope,
        total_distinct_parts=int(head.get("total_distinct_parts", 0)),
        total_quantity=int(head.get("total_quantity", 0)),
        total_estimated_cost_cents=int(
            head.get("total_estimated_cost_cents", 0)
        ),
        items=items,
        notes=head.get("notes"),
    )


def list_requisitions(
    shop_id: Optional[int] = None,
    since: Optional[str] = None,
    limit: int = 50,
    db_path: Optional[str] = None,
) -> list[dict]:
    """List requisition headers most-recent-first."""
    query = "SELECT * FROM parts_requisitions"
    conditions: list[str] = []
    params: list = []
    if shop_id is not None:
        conditions.append("shop_id = ?")
        params.append(shop_id)
    if since:
        conditions.append("generated_at >= ?")
        params.append(since)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY generated_at DESC, id DESC"
    if limit and limit > 0:
        query += " LIMIT ?"
        params.append(int(limit))
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
