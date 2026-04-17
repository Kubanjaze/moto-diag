"""Customer-vehicle link repository — many-to-many with ownership history.

Phase 113: manages the customer_bikes join table. A customer can own
multiple bikes; a bike can have multiple historical owners (transferred
ownership, pre-purchase inspections). Track H phase 180 (share report with
customer) relies on this.
"""

from datetime import datetime
from typing import Optional

from motodiag.core.database import get_connection
from motodiag.crm.models import CustomerRelationship


def link_customer_bike(
    customer_id: int,
    vehicle_id: int,
    relationship: CustomerRelationship | str = CustomerRelationship.OWNER,
    notes: Optional[str] = None,
    db_path: str | None = None,
) -> None:
    """Link a customer to a vehicle with the specified relationship.

    Idempotent on (customer_id, vehicle_id, relationship) — re-linking with
    the same relationship is a no-op. Linking with a different relationship
    creates a new row (allowing a customer to be previous_owner AND interested
    in the same bike, for example).
    """
    rel_val = relationship.value if isinstance(relationship, CustomerRelationship) else relationship
    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT OR IGNORE INTO customer_bikes
               (customer_id, vehicle_id, relationship, assigned_at, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (customer_id, vehicle_id, rel_val, datetime.now().isoformat(), notes),
        )


def unlink_customer_bike(
    customer_id: int,
    vehicle_id: int,
    relationship: CustomerRelationship | str | None = None,
    db_path: str | None = None,
) -> int:
    """Remove a customer-vehicle link. Returns number of rows deleted.

    If relationship is None, removes ALL relationships between the customer
    and vehicle. If specified, removes only that specific relationship.
    """
    with get_connection(db_path) as conn:
        if relationship is None:
            cursor = conn.execute(
                "DELETE FROM customer_bikes WHERE customer_id = ? AND vehicle_id = ?",
                (customer_id, vehicle_id),
            )
        else:
            rel_val = relationship.value if isinstance(relationship, CustomerRelationship) else relationship
            cursor = conn.execute(
                "DELETE FROM customer_bikes WHERE customer_id = ? AND vehicle_id = ? AND relationship = ?",
                (customer_id, vehicle_id, rel_val),
            )
        return cursor.rowcount


def list_bikes_for_customer(
    customer_id: int,
    relationship: CustomerRelationship | str | None = None,
    db_path: str | None = None,
) -> list[dict]:
    """List all bikes a customer is linked to, optionally filtered by relationship.

    Returns joined rows including vehicle details.
    """
    query = """
        SELECT v.*, cb.relationship AS cb_relationship, cb.assigned_at AS cb_assigned_at,
               cb.notes AS cb_notes
        FROM vehicles v
        INNER JOIN customer_bikes cb ON cb.vehicle_id = v.id
        WHERE cb.customer_id = ?
    """
    params: list = [customer_id]
    if relationship is not None:
        rel_val = relationship.value if isinstance(relationship, CustomerRelationship) else relationship
        query += " AND cb.relationship = ?"
        params.append(rel_val)
    query += " ORDER BY cb.assigned_at DESC"

    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def list_customers_for_bike(
    vehicle_id: int,
    relationship: CustomerRelationship | str | None = None,
    db_path: str | None = None,
) -> list[dict]:
    """List all customers linked to a bike (current + historical owners)."""
    query = """
        SELECT c.*, cb.relationship AS cb_relationship, cb.assigned_at AS cb_assigned_at,
               cb.notes AS cb_notes
        FROM customers c
        INNER JOIN customer_bikes cb ON cb.customer_id = c.id
        WHERE cb.vehicle_id = ?
    """
    params: list = [vehicle_id]
    if relationship is not None:
        rel_val = relationship.value if isinstance(relationship, CustomerRelationship) else relationship
        query += " AND cb.relationship = ?"
        params.append(rel_val)
    query += " ORDER BY cb.assigned_at DESC"

    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_current_owner(vehicle_id: int, db_path: str | None = None) -> dict | None:
    """Return the current owner customer for a vehicle, or None.

    A vehicle should have exactly one 'owner' relationship at a time; if
    multiple exist (bug), returns the most recently assigned.
    """
    owners = list_customers_for_bike(
        vehicle_id,
        relationship=CustomerRelationship.OWNER,
        db_path=db_path,
    )
    return owners[0] if owners else None


def transfer_ownership(
    vehicle_id: int,
    from_customer_id: int,
    to_customer_id: int,
    notes: Optional[str] = None,
    db_path: str | None = None,
) -> None:
    """Transfer bike ownership: mark current owner as previous_owner, assign new owner.

    Atomic operation — both updates happen in one transaction via
    get_connection's auto-commit.
    """
    with get_connection(db_path) as conn:
        # Demote old owner to previous_owner
        conn.execute(
            """UPDATE customer_bikes
               SET relationship = 'previous_owner'
               WHERE vehicle_id = ? AND customer_id = ? AND relationship = 'owner'""",
            (vehicle_id, from_customer_id),
        )
        # Add new owner
        conn.execute(
            """INSERT OR IGNORE INTO customer_bikes
               (customer_id, vehicle_id, relationship, assigned_at, notes)
               VALUES (?, ?, 'owner', ?, ?)""",
            (to_customer_id, vehicle_id, datetime.now().isoformat(), notes),
        )
