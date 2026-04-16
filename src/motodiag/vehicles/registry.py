"""Vehicle registry — CRUD operations for the garage."""

import json
from datetime import datetime
from typing import Optional

from motodiag.core.database import get_connection, init_db
from motodiag.core.models import VehicleBase, ProtocolType


def add_vehicle(vehicle: VehicleBase, db_path: str | None = None) -> int:
    """Add a vehicle to the garage. Returns the vehicle ID."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO vehicles (make, model, year, engine_cc, vin, protocol, notes, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                vehicle.make, vehicle.model, vehicle.year,
                vehicle.engine_cc, vehicle.vin, vehicle.protocol.value,
                vehicle.notes, datetime.now().isoformat(),
            ),
        )
        return cursor.lastrowid


def get_vehicle(vehicle_id: int, db_path: str | None = None) -> dict | None:
    """Get a vehicle by ID."""
    with get_connection(db_path) as conn:
        cursor = conn.execute("SELECT * FROM vehicles WHERE id = ?", (vehicle_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def list_vehicles(
    make: str | None = None,
    model: str | None = None,
    year: int | None = None,
    db_path: str | None = None,
) -> list[dict]:
    """List vehicles with optional filters."""
    query = "SELECT * FROM vehicles WHERE 1=1"
    params: list = []

    if make:
        query += " AND make LIKE ?"
        params.append(f"%{make}%")
    if model:
        query += " AND model LIKE ?"
        params.append(f"%{model}%")
    if year:
        query += " AND year = ?"
        params.append(year)

    query += " ORDER BY make, model, year"

    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def update_vehicle(vehicle_id: int, updates: dict, db_path: str | None = None) -> bool:
    """Update a vehicle's fields. Returns True if updated."""
    allowed = {"make", "model", "year", "engine_cc", "vin", "protocol", "notes"}
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return False

    filtered["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in filtered)
    values = list(filtered.values()) + [vehicle_id]

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE vehicles SET {set_clause} WHERE id = ?", values
        )
        return cursor.rowcount > 0


def delete_vehicle(vehicle_id: int, db_path: str | None = None) -> bool:
    """Delete a vehicle by ID. Returns True if deleted."""
    with get_connection(db_path) as conn:
        cursor = conn.execute("DELETE FROM vehicles WHERE id = ?", (vehicle_id,))
        return cursor.rowcount > 0


def count_vehicles(db_path: str | None = None) -> int:
    """Get total vehicle count."""
    with get_connection(db_path) as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM vehicles")
        return cursor.fetchone()[0]
