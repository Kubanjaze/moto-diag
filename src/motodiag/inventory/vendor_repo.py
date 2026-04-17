"""Vendor repository."""

from typing import Optional

from motodiag.core.database import get_connection
from motodiag.inventory.models import Vendor


def add_vendor(vendor: Vendor, db_path: str | None = None) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO vendors
               (name, contact_name, email, phone, website, address,
                payment_terms, notes, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                vendor.name, vendor.contact_name, vendor.email, vendor.phone,
                vendor.website, vendor.address, vendor.payment_terms,
                vendor.notes, 1 if vendor.is_active else 0,
            ),
        )
        return cursor.lastrowid


def get_vendor(vendor_id: int, db_path: str | None = None) -> Optional[dict]:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM vendors WHERE id = ?", (vendor_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_vendor_by_name(name: str, db_path: str | None = None) -> Optional[dict]:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM vendors WHERE name = ?", (name,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def list_vendors(
    is_active: Optional[bool] = None, db_path: str | None = None,
) -> list[dict]:
    query = "SELECT * FROM vendors WHERE 1=1"
    params: list = []
    if is_active is not None:
        query += " AND is_active = ?"
        params.append(1 if is_active else 0)
    query += " ORDER BY name"
    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]


def update_vendor(vendor_id: int, db_path: str | None = None, **fields) -> bool:
    if not fields:
        return False
    if "is_active" in fields and isinstance(fields["is_active"], bool):
        fields["is_active"] = 1 if fields["is_active"] else 0
    keys = ", ".join(f"{k} = ?" for k in fields)
    params = list(fields.values()) + [vendor_id]
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE vendors SET {keys} WHERE id = ?", params,
        )
        return cursor.rowcount > 0


def delete_vendor(vendor_id: int, db_path: str | None = None) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM vendors WHERE id = ?", (vendor_id,),
        )
        return cursor.rowcount > 0
