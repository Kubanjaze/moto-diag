"""Vehicle registry — CRUD operations for the garage.

Phase 110 (Retrofit): extended to support powertrain/engine_type/battery
fields while preserving full backward compatibility with existing callers.
"""

import json
from datetime import datetime
from typing import Optional

from motodiag.core.database import get_connection, init_db
from motodiag.core.models import (
    VehicleBase, ProtocolType,
    PowertrainType, EngineType, BatteryChemistry,
)


def add_vehicle(vehicle: VehicleBase, db_path: str | None = None) -> int:
    """Add a vehicle to the garage. Returns the vehicle ID.

    Phase 110: persists new powertrain/engine_type/battery_chemistry/motor_kw/
    bms_present columns. Callers using the old VehicleBase (without those
    fields) get the ICE/four_stroke defaults from the model.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO vehicles (
                make, model, year, engine_cc, vin, protocol, notes, created_at,
                powertrain, engine_type, battery_chemistry, motor_kw, bms_present
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                vehicle.make, vehicle.model, vehicle.year,
                vehicle.engine_cc, vehicle.vin, vehicle.protocol.value,
                vehicle.notes, datetime.now().isoformat(),
                vehicle.powertrain.value,
                vehicle.engine_type.value,
                vehicle.battery_chemistry.value if vehicle.battery_chemistry else None,
                vehicle.motor_kw,
                1 if vehicle.bms_present else 0,
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
    powertrain: PowertrainType | str | None = None,
    db_path: str | None = None,
) -> list[dict]:
    """List vehicles with optional filters.

    Phase 110: adds `powertrain` filter so downstream code can query e.g.
    all electric bikes or all ICE bikes in a garage.
    """
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
    if powertrain:
        pt_val = powertrain.value if isinstance(powertrain, PowertrainType) else powertrain
        query += " AND powertrain = ?"
        params.append(pt_val)

    query += " ORDER BY make, model, year"

    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def update_vehicle(vehicle_id: int, updates: dict, db_path: str | None = None) -> bool:
    """Update a vehicle's fields. Returns True if updated.

    Phase 110: expanded allowed fields to include new powertrain columns.
    """
    allowed = {
        "make", "model", "year", "engine_cc", "vin", "protocol", "notes",
        "powertrain", "engine_type", "battery_chemistry", "motor_kw", "bms_present",
    }
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return False

    # Convert enum instances to their string values for DB storage
    for key in ("protocol", "powertrain", "engine_type", "battery_chemistry"):
        if key in filtered and hasattr(filtered[key], "value"):
            filtered[key] = filtered[key].value
    if "bms_present" in filtered and isinstance(filtered["bms_present"], bool):
        filtered["bms_present"] = 1 if filtered["bms_present"] else 0

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


def count_vehicles(
    db_path: str | None = None,
    powertrain: PowertrainType | str | None = None,
) -> int:
    """Get total vehicle count.

    Phase 110: optional powertrain filter for electric-vs-ICE counts.
    db_path remains the first positional arg for backward compatibility.
    """
    if powertrain is None:
        query = "SELECT COUNT(*) FROM vehicles"
        params: tuple = ()
    else:
        pt_val = powertrain.value if isinstance(powertrain, PowertrainType) else powertrain
        query = "SELECT COUNT(*) FROM vehicles WHERE powertrain = ?"
        params = (pt_val,)

    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return cursor.fetchone()[0]
