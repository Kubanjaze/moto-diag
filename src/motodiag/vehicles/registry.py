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


# ---------------------------------------------------------------------------
# Phase 177 additions: owner scoping + tier quotas
# ---------------------------------------------------------------------------


class VehicleOwnershipError(ValueError):
    """Raised when a caller tries to touch a vehicle they don't own."""


class VehicleQuotaExceededError(Exception):
    """Raised when creating a vehicle would exceed the caller's tier
    quota. Mapped to HTTP 402 in :mod:`motodiag.api.errors`."""

    def __init__(
        self, current_count: int, limit: int, tier: str,
    ) -> None:
        self.current_count = current_count
        self.limit = limit
        self.tier = tier
        super().__init__(
            f"vehicle quota exceeded: {current_count}/{limit} "
            f"({tier} tier). Upgrade to add more vehicles."
        )


# Phase 177 tier-to-quota mapping. ``-1`` = unlimited.
TIER_VEHICLE_LIMITS: dict[str, int] = {
    "individual": 5,
    "shop": 50,
    "company": -1,
}


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
        # Phase 152: persistent mileage source-of-truth. Added by migration
        # 020; update_vehicle is the only non-add_service_event writer.
        "mileage",
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


# ---------------------------------------------------------------------------
# Phase 177: owner-scoped CRUD helpers
# ---------------------------------------------------------------------------


def add_vehicle_for_owner(
    vehicle: VehicleBase, owner_user_id: int,
    db_path: str | None = None,
) -> int:
    """Same as :func:`add_vehicle` but stamps ``owner_user_id``.
    Returns the new vehicle id. Does NOT check tier quota — callers
    (typically the HTTP POST route) should call
    :func:`count_vehicles_for_owner` first and raise
    :class:`VehicleQuotaExceededError` before calling this."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO vehicles (
                make, model, year, engine_cc, vin, protocol, notes,
                created_at, powertrain, engine_type,
                battery_chemistry, motor_kw, bms_present,
                owner_user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                vehicle.make, vehicle.model, vehicle.year,
                vehicle.engine_cc, vehicle.vin, vehicle.protocol.value,
                vehicle.notes, datetime.now().isoformat(),
                vehicle.powertrain.value,
                vehicle.engine_type.value,
                vehicle.battery_chemistry.value
                    if vehicle.battery_chemistry else None,
                vehicle.motor_kw,
                1 if vehicle.bms_present else 0,
                owner_user_id,
            ),
        )
        return cursor.lastrowid


def list_vehicles_for_owner(
    owner_user_id: int,
    make: str | None = None,
    model: str | None = None,
    year: int | None = None,
    powertrain: PowertrainType | str | None = None,
    limit: int = 100,
    db_path: str | None = None,
) -> list[dict]:
    """List vehicles owned by ``owner_user_id`` with optional filters."""
    query = "SELECT * FROM vehicles WHERE owner_user_id = ?"
    params: list = [owner_user_id]
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
        pt_val = (
            powertrain.value if isinstance(powertrain, PowertrainType)
            else powertrain
        )
        query += " AND powertrain = ?"
        params.append(pt_val)
    query += " ORDER BY make, model, year"
    if limit and limit > 0:
        query += " LIMIT ?"
        params.append(int(limit))
    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]


def count_vehicles_for_owner(
    owner_user_id: int, db_path: str | None = None,
) -> int:
    """Count vehicles owned by ``owner_user_id``. Uses the
    ``idx_vehicles_owner`` index added in migration 038."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM vehicles WHERE owner_user_id = ?",
            (owner_user_id,),
        )
        return cursor.fetchone()[0]


def get_vehicle_for_owner(
    vehicle_id: int, owner_user_id: int,
    db_path: str | None = None,
) -> dict | None:
    """Return the vehicle iff it's owned by ``owner_user_id``.

    Returns None both for nonexistent ids AND for ids owned by a
    different user — routes translate both into 404 (prevents
    enumeration)."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM vehicles WHERE id = ? AND owner_user_id = ?",
            (vehicle_id, owner_user_id),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def update_vehicle_for_owner(
    vehicle_id: int, owner_user_id: int, updates: dict,
    db_path: str | None = None,
) -> bool:
    """Update allowed fields on a vehicle the caller owns.

    Raises :class:`VehicleOwnershipError` when the vehicle exists but
    belongs to someone else (distinct from "not found" which returns
    False). Route handlers translate the error to 404 (same as not-
    found — deliberate).
    """
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT owner_user_id FROM vehicles WHERE id = ?",
            (vehicle_id,),
        ).fetchone()
        if row is None:
            return False
        if int(row["owner_user_id"]) != owner_user_id:
            raise VehicleOwnershipError(
                f"vehicle id={vehicle_id} not owned by "
                f"user id={owner_user_id}"
            )
    return update_vehicle(vehicle_id, updates, db_path=db_path)


def delete_vehicle_for_owner(
    vehicle_id: int, owner_user_id: int,
    db_path: str | None = None,
) -> bool:
    """Delete if owned; raise :class:`VehicleOwnershipError` on cross-
    owner attempt."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT owner_user_id FROM vehicles WHERE id = ?",
            (vehicle_id,),
        ).fetchone()
        if row is None:
            return False
        if int(row["owner_user_id"]) != owner_user_id:
            raise VehicleOwnershipError(
                f"vehicle id={vehicle_id} not owned by "
                f"user id={owner_user_id}"
            )
        cursor = conn.execute(
            "DELETE FROM vehicles WHERE id = ?", (vehicle_id,),
        )
        return cursor.rowcount > 0


def check_vehicle_quota(
    owner_user_id: int, tier: str | None,
    db_path: str | None = None,
) -> None:
    """Raise :class:`VehicleQuotaExceededError` when creating one
    more vehicle would exceed the tier quota. No-op for unlimited
    tiers. Uses ``individual`` defaults for None/unknown tiers —
    matches Phase 175's anonymous-discovery-tier leniency."""
    effective_tier = tier if tier in TIER_VEHICLE_LIMITS else "individual"
    limit = TIER_VEHICLE_LIMITS[effective_tier]
    if limit < 0:
        return  # unlimited
    current = count_vehicles_for_owner(owner_user_id, db_path=db_path)
    if current >= limit:
        raise VehicleQuotaExceededError(
            current_count=current, limit=limit, tier=effective_tier,
        )
