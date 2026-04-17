"""Inventory item repository."""

import json
from typing import Optional

from motodiag.core.database import get_connection
from motodiag.inventory.models import InventoryItem


def _row_to_item(row) -> dict:
    d = dict(row)
    if d.get("model_applicable"):
        try:
            d["model_applicable"] = json.loads(d["model_applicable"])
        except (json.JSONDecodeError, TypeError):
            d["model_applicable"] = []
    else:
        d["model_applicable"] = []
    return d


def add_item(item: InventoryItem, db_path: str | None = None) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO inventory_items
               (sku, name, description, category, make, model_applicable,
                quantity_on_hand, reorder_point, unit_cost, unit_price,
                vendor_id, location)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item.sku, item.name, item.description, item.category,
                item.make, json.dumps(item.model_applicable),
                item.quantity_on_hand, item.reorder_point,
                item.unit_cost, item.unit_price, item.vendor_id, item.location,
            ),
        )
        return cursor.lastrowid


def get_item(item_id: int, db_path: str | None = None) -> Optional[dict]:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM inventory_items WHERE id = ?", (item_id,),
        )
        row = cursor.fetchone()
        return _row_to_item(row) if row else None


def get_item_by_sku(sku: str, db_path: str | None = None) -> Optional[dict]:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM inventory_items WHERE sku = ?", (sku,),
        )
        row = cursor.fetchone()
        return _row_to_item(row) if row else None


def list_items(
    category: Optional[str] = None,
    vendor_id: Optional[int] = None,
    make: Optional[str] = None,
    db_path: str | None = None,
) -> list[dict]:
    query = "SELECT * FROM inventory_items WHERE 1=1"
    params: list = []
    if category is not None:
        query += " AND category = ?"
        params.append(category)
    if vendor_id is not None:
        query += " AND vendor_id = ?"
        params.append(vendor_id)
    if make is not None:
        query += " AND (make IS NULL OR make = ?)"
        params.append(make)
    query += " ORDER BY name"
    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [_row_to_item(r) for r in cursor.fetchall()]


def update_item(item_id: int, db_path: str | None = None, **fields) -> bool:
    if not fields:
        return False
    if "model_applicable" in fields and isinstance(fields["model_applicable"], list):
        fields["model_applicable"] = json.dumps(fields["model_applicable"])
    keys = ", ".join(f"{k} = ?" for k in fields)
    params = list(fields.values()) + [item_id]
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE inventory_items SET {keys} WHERE id = ?", params,
        )
        return cursor.rowcount > 0


def delete_item(item_id: int, db_path: str | None = None) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM inventory_items WHERE id = ?", (item_id,),
        )
        return cursor.rowcount > 0


def adjust_quantity(
    item_id: int, delta: int, db_path: str | None = None,
) -> Optional[int]:
    """Add `delta` to quantity_on_hand (negative = consume). Returns new qty or None."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT quantity_on_hand FROM inventory_items WHERE id = ?",
            (item_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        new_qty = row[0] + delta
        conn.execute(
            "UPDATE inventory_items SET quantity_on_hand = ? WHERE id = ?",
            (new_qty, item_id),
        )
        return new_qty


def items_below_reorder(db_path: str | None = None) -> list[dict]:
    """Return items where quantity_on_hand <= reorder_point (and reorder_point > 0)."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM inventory_items "
            "WHERE reorder_point > 0 AND quantity_on_hand <= reorder_point "
            "ORDER BY (reorder_point - quantity_on_hand) DESC, name"
        )
        return [_row_to_item(r) for r in cursor.fetchall()]
