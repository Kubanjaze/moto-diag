"""Purchase orders generated locally from reorder points.

An inventory item is due for reorder when its stock is at or below its
reorder point (``item_repo.items_below_reorder``). :func:`reorder_plan`
decides, item by item, whether a PO can order it and, if not, why not;
:func:`generate_purchase_orders` turns the orderable lines into one draft
PO per vendor.

Nothing here sends anything. ``sent`` is a status the user sets after
sending the PO by their own means; ordering through a supplier's system is
a supplier integration, which is not built.

Status moves: draft → sent → received; draft or sent → cancelled.
Receiving adds each line's quantity to the item's stock.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from motodiag.core.database import get_connection
from motodiag.inventory.item_repo import adjust_quantity, items_below_reorder

PO_STATUSES: tuple[str, ...] = ("draft", "sent", "received", "cancelled")
OPEN_STATUSES: tuple[str, ...] = ("draft", "sent")

_MOVES: dict[str, tuple[str, ...]] = {
    "draft": ("sent", "cancelled"),
    "sent": ("received", "cancelled"),
    "received": (),
    "cancelled": (),
}
_STAMP = {"sent": "sent_at", "received": "received_at", "cancelled": "cancelled_at"}


class PurchaseOrderError(ValueError):
    """A PO that does not exist, or a status move that is not allowed."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _cents(dollars) -> int:
    return int(round(float(dollars or 0.0) * 100))


def _items_on_open_pos(conn) -> set[int]:
    rows = conn.execute(
        "SELECT DISTINCT l.item_id FROM purchase_order_lines l "
        "JOIN purchase_orders p ON p.id = l.po_id "
        f"WHERE p.status IN ({', '.join('?' * len(OPEN_STATUSES))})",
        OPEN_STATUSES,
    ).fetchall()
    return {int(r[0]) for r in rows}


def reorder_plan(db_path: Optional[str] = None) -> list[dict]:
    """Every item at or below its reorder point, and what a PO would do.

    Each entry is the item plus ``order_quantity`` (its ``reorder_quantity``
    when it can be ordered, else None) and ``skip_reason`` (None when it can
    be ordered).
    """
    due = items_below_reorder(db_path=db_path)
    with get_connection(db_path) as conn:
        on_order = _items_on_open_pos(conn)
    plan = []
    for item in due:
        reason = None
        if item["id"] in on_order:
            reason = "already on an open purchase order"
        elif not item.get("reorder_quantity"):
            reason = "no reorder quantity set"
        elif item.get("vendor_id") is None:
            reason = "no vendor set"
        plan.append({
            **item,
            "order_quantity": None if reason else int(item["reorder_quantity"]),
            "skip_reason": reason,
        })
    return plan


def _next_po_number(conn, vendor_id: int, stamp: str) -> str:
    base = f"PO-{stamp}-V{vendor_id}"
    n = conn.execute(
        "SELECT COUNT(*) FROM purchase_orders WHERE po_number LIKE ?",
        (base + "%",),
    ).fetchone()[0]
    return base if n == 0 else f"{base}-{n + 1}"


def generate_purchase_orders(
    db_path: Optional[str] = None,
) -> tuple[list[int], list[dict]]:
    """Create one draft PO per vendor from the orderable lines of the plan.

    Returns ``(po_ids, skipped)``: the new POs' ids, and the plan entries
    that were not ordered, each with its ``skip_reason``.
    """
    plan = reorder_plan(db_path=db_path)
    orderable = [p for p in plan if p["skip_reason"] is None]
    skipped = [p for p in plan if p["skip_reason"] is not None]
    by_vendor: dict[int, list[dict]] = {}
    for p in orderable:
        by_vendor.setdefault(int(p["vendor_id"]), []).append(p)
    po_ids: list[int] = []
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    with get_connection(db_path) as conn:
        for vendor_id in sorted(by_vendor):
            number = _next_po_number(conn, vendor_id, stamp)
            po_id = conn.execute(
                "INSERT INTO purchase_orders (po_number, vendor_id, status) "
                "VALUES (?, ?, 'draft')",
                (number, vendor_id),
            ).lastrowid
            for p in by_vendor[vendor_id]:
                conn.execute(
                    "INSERT INTO purchase_order_lines "
                    "(po_id, item_id, quantity, unit_cost_cents) VALUES (?, ?, ?, ?)",
                    (po_id, p["id"], p["order_quantity"], _cents(p.get("unit_cost"))),
                )
            po_ids.append(int(po_id))
    return po_ids, skipped


def get_purchase_order(po_id: int, db_path: Optional[str] = None) -> Optional[dict]:
    """The PO with its vendor and lines (each with the item's SKU and name)."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT p.*, v.name AS vendor_name, v.contact_name AS vendor_contact, "
            "v.email AS vendor_email, v.phone AS vendor_phone, "
            "v.address AS vendor_address, v.payment_terms AS vendor_terms "
            "FROM purchase_orders p JOIN vendors v ON v.id = p.vendor_id "
            "WHERE p.id = ?",
            (po_id,),
        ).fetchone()
        if row is None:
            return None
        po = dict(row)
        lines = conn.execute(
            "SELECT l.*, i.sku, i.name AS item_name FROM purchase_order_lines l "
            "JOIN inventory_items i ON i.id = l.item_id WHERE l.po_id = ? "
            "ORDER BY i.sku",
            (po_id,),
        ).fetchall()
    po["lines"] = [dict(r) for r in lines]
    po["total_cents"] = sum(ln["quantity"] * ln["unit_cost_cents"] for ln in po["lines"])
    return po


def list_purchase_orders(
    status: Optional[str] = None, db_path: Optional[str] = None,
) -> list[dict]:
    """POs newest first, each with its vendor's name, line count and total."""
    query = (
        "SELECT p.*, v.name AS vendor_name, "
        "(SELECT COUNT(*) FROM purchase_order_lines l WHERE l.po_id = p.id) AS line_count, "
        "(SELECT COALESCE(SUM(l.quantity * l.unit_cost_cents), 0) "
        " FROM purchase_order_lines l WHERE l.po_id = p.id) AS total_cents "
        "FROM purchase_orders p JOIN vendors v ON v.id = p.vendor_id"
    )
    params: list = []
    if status is not None:
        if status not in PO_STATUSES:
            raise PurchaseOrderError(f"status must be one of {', '.join(PO_STATUSES)}")
        query += " WHERE p.status = ?"
        params.append(status)
    query += " ORDER BY p.id DESC"
    with get_connection(db_path) as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def set_status(po_id: int, target: str, db_path: Optional[str] = None) -> dict:
    """Move a PO to ``target``; receiving adds its lines to stock.

    Returns the PO after the move. Raises :class:`PurchaseOrderError` for an
    unknown PO or a move ``_MOVES`` does not allow.
    """
    po = get_purchase_order(po_id, db_path=db_path)
    if po is None:
        raise PurchaseOrderError(f"purchase order not found: id={po_id}")
    if target not in _MOVES.get(po["status"], ()):
        raise PurchaseOrderError(
            f"purchase order {po['po_number']} is {po['status']}; "
            f"it cannot be marked {target}"
        )
    with get_connection(db_path) as conn:
        conn.execute(
            f"UPDATE purchase_orders SET status = ?, {_STAMP[target]} = ? WHERE id = ?",
            (target, _now(), po_id),
        )
    if target == "received":
        for line in po["lines"]:
            adjust_quantity(line["item_id"], int(line["quantity"]), db_path=db_path)
    return get_purchase_order(po_id, db_path=db_path)


def render_purchase_order(po: dict, shop: Optional[dict] = None) -> str:
    """A printable plain-text PO."""
    out: list[str] = []
    out.append(f"PURCHASE ORDER {po['po_number']}")
    out.append(f"Status: {po['status']}    Created: {po['created_at']}")
    if shop:
        addr = ", ".join(b for b in (shop.get("address"), shop.get("city"),
                                     shop.get("state"), shop.get("zip")) if b)
        out.append("")
        out.append(f"From: {shop['name']}")
        if addr:
            out.append(f"      {addr}")
        if shop.get("phone"):
            out.append(f"      {shop['phone']}")
    out.append("")
    out.append(f"To:   {po['vendor_name']}")
    for label, key in (("Attn", "vendor_contact"), ("Email", "vendor_email"),
                       ("Phone", "vendor_phone"), ("Address", "vendor_address"),
                       ("Terms", "vendor_terms")):
        if po.get(key):
            out.append(f"      {label}: {po[key]}")
    out.append("")
    out.append(f"{'SKU':<16} {'Item':<36} {'Qty':>5} {'Unit':>10} {'Line':>11}")
    for line in po["lines"]:
        unit = line["unit_cost_cents"] / 100
        total = line["quantity"] * line["unit_cost_cents"] / 100
        out.append(f"{line['sku']:<16} {line['item_name'][:36]:<36} "
                   f"{line['quantity']:>5} {unit:>10.2f} {total:>11.2f}")
    out.append(f"{'':<16} {'':<36} {'':>5} {'Total':>10} {po['total_cents'] / 100:>11.2f}")
    if po.get("notes"):
        out.append("")
        out.append(f"Notes: {po['notes']}")
    return "\n".join(out) + "\n"
