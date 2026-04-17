"""Customer repository — CRUD + search operations.

Phase 113: customers are stored in the `customers` table created by
migration 006. The "unassigned" customer (id=1) is seeded by the migration
and owns all pre-retrofit vehicles. Do not delete the unassigned customer.
"""

from datetime import datetime

from motodiag.core.database import get_connection
from motodiag.crm.models import Customer


UNASSIGNED_CUSTOMER_ID = 1
UNASSIGNED_CUSTOMER_NAME = "Unassigned"


def create_customer(customer: Customer, db_path: str | None = None) -> int:
    """Create a new customer. Returns the new customer ID."""
    with get_connection(db_path) as conn:
        now = datetime.now().isoformat()
        cursor = conn.execute(
            """INSERT INTO customers
               (owner_user_id, name, email, phone, address, notes, is_active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                customer.owner_user_id, customer.name, customer.email,
                customer.phone, customer.address, customer.notes,
                1 if customer.is_active else 0, now, now,
            ),
        )
        return cursor.lastrowid


def get_customer(customer_id: int, db_path: str | None = None) -> dict | None:
    with get_connection(db_path) as conn:
        cursor = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_unassigned_customer(db_path: str | None = None) -> dict | None:
    """Return the seeded 'unassigned' customer that owns pre-retrofit vehicles."""
    return get_customer(UNASSIGNED_CUSTOMER_ID, db_path)


def list_customers(
    db_path: str | None = None,
    owner_user_id: int | None = None,
    is_active: bool | None = None,
) -> list[dict]:
    """List customers, optionally scoped by owner (shop) or activity state."""
    query = "SELECT * FROM customers WHERE 1=1"
    params: list = []
    if owner_user_id is not None:
        query += " AND owner_user_id = ?"
        params.append(owner_user_id)
    if is_active is not None:
        query += " AND is_active = ?"
        params.append(1 if is_active else 0)
    query += " ORDER BY name"

    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def search_customers(
    query: str,
    db_path: str | None = None,
    owner_user_id: int | None = None,
) -> list[dict]:
    """Search customers by name, email, or phone (LIKE match).

    Optionally scope to a single shop's customers via owner_user_id.
    """
    pattern = f"%{query}%"
    sql = """SELECT * FROM customers
             WHERE (name LIKE ? OR email LIKE ? OR phone LIKE ?)"""
    params: list = [pattern, pattern, pattern]
    if owner_user_id is not None:
        sql += " AND owner_user_id = ?"
        params.append(owner_user_id)
    sql += " ORDER BY name"

    with get_connection(db_path) as conn:
        cursor = conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


def update_customer(customer_id: int, updates: dict, db_path: str | None = None) -> bool:
    """Update a customer's fields. Returns True if a row was updated.

    Protects the unassigned customer (id=1) from name changes.
    """
    allowed = {"owner_user_id", "name", "email", "phone", "address", "notes", "is_active"}
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return False

    if customer_id == UNASSIGNED_CUSTOMER_ID and "name" in filtered:
        raise ValueError(
            "Cannot rename the unassigned customer (id=1) — it is a system placeholder"
        )

    if "is_active" in filtered and isinstance(filtered["is_active"], bool):
        filtered["is_active"] = 1 if filtered["is_active"] else 0

    filtered["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in filtered)
    values = list(filtered.values()) + [customer_id]

    with get_connection(db_path) as conn:
        cursor = conn.execute(f"UPDATE customers SET {set_clause} WHERE id = ?", values)
        return cursor.rowcount > 0


def deactivate_customer(customer_id: int, db_path: str | None = None) -> bool:
    """Soft-delete a customer by setting is_active=0. Unassigned customer cannot be deactivated."""
    if customer_id == UNASSIGNED_CUSTOMER_ID:
        raise ValueError("Cannot deactivate the unassigned customer (id=1)")
    return update_customer(customer_id, {"is_active": False}, db_path)


def count_customers(
    db_path: str | None = None,
    owner_user_id: int | None = None,
    is_active: bool | None = None,
) -> int:
    query = "SELECT COUNT(*) FROM customers WHERE 1=1"
    params: list = []
    if owner_user_id is not None:
        query += " AND owner_user_id = ?"
        params.append(owner_user_id)
    if is_active is not None:
        query += " AND is_active = ?"
        params.append(1 if is_active else 0)

    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return cursor.fetchone()[0]
