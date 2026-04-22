"""Vehicle CRUD endpoints (Phase 177).

First full-CRUD domain router on top of Phase 175 (FastAPI scaffold)
+ Phase 176 (auth + paywall). All endpoints require an authenticated
caller via :func:`motodiag.auth.deps.get_current_user`; tier-gated
vehicle quota enforced at POST time.

Cross-user vehicles return 404 (not 403) — standard enumeration-
attack prevention. The repo-layer :func:`get_vehicle_for_owner` does
the right thing by construction: it returns None both for missing
ids and for ids owned by a different user.
"""

from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from motodiag.api.deps import get_db_path
from motodiag.auth.deps import AuthedUser, get_current_user
from motodiag.core.models import (
    BatteryChemistry, EngineType, PowertrainType,
    ProtocolType, VehicleBase,
)
from motodiag.vehicles.registry import (
    TIER_VEHICLE_LIMITS,
    VehicleOwnershipError,
    VehicleQuotaExceededError,
    add_vehicle_for_owner,
    check_vehicle_quota,
    count_vehicles_for_owner,
    delete_vehicle_for_owner,
    get_vehicle_for_owner,
    list_vehicles_for_owner,
    update_vehicle_for_owner,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/vehicles", tags=["vehicles"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


ProtocolLiteral = Literal[
    "none", "obd2", "can", "k_line", "j1850_pwm", "j1850_vpw",
    "iso9141", "iso14230", "iso15765", "ford_msc", "kawasaki_kds",
    "suzuki_sds", "yamaha_yds",
]

PowertrainLiteral = Literal[
    "ice", "electric", "hybrid_parallel", "hybrid_series",
]

EngineTypeLiteral = Literal[
    "four_stroke", "two_stroke", "rotary", "diesel", "none",
]


class VehicleCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    make: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=100)
    year: int = Field(..., ge=1900, le=2100)
    engine_cc: Optional[int] = Field(None, ge=0)
    vin: Optional[str] = Field(None, max_length=30)
    protocol: ProtocolLiteral = "none"
    notes: Optional[str] = None
    powertrain: PowertrainLiteral = "ice"
    engine_type: EngineTypeLiteral = "four_stroke"
    battery_chemistry: Optional[str] = None
    motor_kw: Optional[float] = Field(None, ge=0)
    bms_present: bool = False
    mileage: Optional[int] = Field(None, ge=0)


class VehicleUpdateRequest(BaseModel):
    """Partial update — every field optional."""

    model_config = ConfigDict(extra="ignore")

    make: Optional[str] = Field(None, min_length=1, max_length=100)
    model: Optional[str] = Field(None, min_length=1, max_length=100)
    year: Optional[int] = Field(None, ge=1900, le=2100)
    engine_cc: Optional[int] = Field(None, ge=0)
    vin: Optional[str] = Field(None, max_length=30)
    protocol: Optional[ProtocolLiteral] = None
    notes: Optional[str] = None
    powertrain: Optional[PowertrainLiteral] = None
    engine_type: Optional[EngineTypeLiteral] = None
    battery_chemistry: Optional[str] = None
    motor_kw: Optional[float] = Field(None, ge=0)
    bms_present: Optional[bool] = None
    mileage: Optional[int] = Field(None, ge=0)


class VehicleResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    owner_user_id: int
    make: str
    model: str
    year: int
    engine_cc: Optional[int] = None
    vin: Optional[str] = None
    protocol: str
    notes: Optional[str] = None
    powertrain: Optional[str] = None
    engine_type: Optional[str] = None
    battery_chemistry: Optional[str] = None
    motor_kw: Optional[float] = None
    bms_present: Optional[bool] = None
    mileage: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class VehicleListResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    items: list[VehicleResponse]
    total: int
    tier: Optional[str] = None
    quota_limit: Optional[int] = None  # None when unlimited
    quota_remaining: Optional[int] = None


class SessionsForVehicleResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    vehicle_id: int
    sessions: list[dict]
    total: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_response(row: dict) -> VehicleResponse:
    return VehicleResponse(
        id=int(row["id"]),
        owner_user_id=int(row.get("owner_user_id", 0)),
        make=str(row["make"]),
        model=str(row["model"]),
        year=int(row["year"]),
        engine_cc=row.get("engine_cc"),
        vin=row.get("vin"),
        protocol=str(row.get("protocol", "none")),
        notes=row.get("notes"),
        powertrain=row.get("powertrain"),
        engine_type=row.get("engine_type"),
        battery_chemistry=row.get("battery_chemistry"),
        motor_kw=row.get("motor_kw"),
        bms_present=bool(row.get("bms_present") or 0),
        mileage=row.get("mileage"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def _quota_for(tier: Optional[str]) -> tuple[Optional[int], str]:
    """Return (limit, effective_tier). limit is None when unlimited."""
    effective = (
        tier if tier in TIER_VEHICLE_LIMITS else "individual"
    )
    limit = TIER_VEHICLE_LIMITS[effective]
    return (None if limit < 0 else limit), effective


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=VehicleListResponse,
    summary="List vehicles in the caller's garage",
)
def list_vehicles_endpoint(
    make: Optional[str] = None,
    model: Optional[str] = None,
    year: Optional[int] = None,
    powertrain: Optional[PowertrainLiteral] = None,
    limit: int = 100,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> VehicleListResponse:
    rows = list_vehicles_for_owner(
        owner_user_id=user.id,
        make=make, model=model, year=year, powertrain=powertrain,
        limit=limit, db_path=db_path,
    )
    total = count_vehicles_for_owner(user.id, db_path=db_path)
    quota_limit, effective_tier = _quota_for(user.tier)
    remaining = (
        None if quota_limit is None
        else max(quota_limit - total, 0)
    )
    return VehicleListResponse(
        items=[_row_to_response(r) for r in rows],
        total=total,
        tier=effective_tier,
        quota_limit=quota_limit,
        quota_remaining=remaining,
    )


@router.post(
    "",
    response_model=VehicleResponse,
    status_code=201,
    summary="Add a vehicle to the caller's garage",
)
def create_vehicle_endpoint(
    req: VehicleCreateRequest,
    response: Response,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> VehicleResponse:
    # Enforce tier quota BEFORE inserting.
    check_vehicle_quota(
        owner_user_id=user.id, tier=user.tier, db_path=db_path,
    )
    # Build the Phase 04 VehicleBase from the request (coerce the
    # string literals into the enum types the registry expects).
    vehicle = VehicleBase(
        make=req.make, model=req.model, year=req.year,
        engine_cc=req.engine_cc, vin=req.vin,
        protocol=ProtocolType(req.protocol),
        notes=req.notes,
        powertrain=PowertrainType(req.powertrain),
        engine_type=EngineType(req.engine_type),
        battery_chemistry=(
            BatteryChemistry(req.battery_chemistry)
            if req.battery_chemistry else None
        ),
        motor_kw=req.motor_kw,
        bms_present=req.bms_present,
    )
    vid = add_vehicle_for_owner(
        vehicle, owner_user_id=user.id, db_path=db_path,
    )
    # Persist mileage post-insert via the Phase 152 whitelist
    # (add_vehicle_for_owner doesn't handle it directly).
    if req.mileage is not None:
        update_vehicle_for_owner(
            vid, user.id, {"mileage": req.mileage}, db_path=db_path,
        )
    row = get_vehicle_for_owner(vid, user.id, db_path=db_path)
    assert row is not None
    response.headers["Location"] = f"/v1/vehicles/{vid}"
    return _row_to_response(row)


@router.get(
    "/{vehicle_id}",
    response_model=VehicleResponse,
    summary="Fetch one vehicle from the caller's garage",
)
def get_vehicle_endpoint(
    vehicle_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> VehicleResponse:
    row = get_vehicle_for_owner(
        vehicle_id, user.id, db_path=db_path,
    )
    if row is None:
        raise VehicleOwnershipError(
            f"vehicle id={vehicle_id} not found"
        )
    return _row_to_response(row)


@router.patch(
    "/{vehicle_id}",
    response_model=VehicleResponse,
    summary="Partially update a vehicle",
)
def update_vehicle_endpoint(
    vehicle_id: int,
    req: VehicleUpdateRequest,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> VehicleResponse:
    updates = {
        k: v for k, v in req.model_dump(exclude_unset=True).items()
        if v is not None
    }
    if not updates:
        # No-op update — return current state.
        row = get_vehicle_for_owner(
            vehicle_id, user.id, db_path=db_path,
        )
        if row is None:
            raise VehicleOwnershipError(
                f"vehicle id={vehicle_id} not found"
            )
        return _row_to_response(row)
    try:
        changed = update_vehicle_for_owner(
            vehicle_id, user.id, updates, db_path=db_path,
        )
    except VehicleOwnershipError:
        # Surface as 404 (not 403) — prevents enumeration.
        raise VehicleOwnershipError(
            f"vehicle id={vehicle_id} not found"
        )
    if not changed:
        raise VehicleOwnershipError(
            f"vehicle id={vehicle_id} not found"
        )
    row = get_vehicle_for_owner(
        vehicle_id, user.id, db_path=db_path,
    )
    assert row is not None
    return _row_to_response(row)


@router.delete(
    "/{vehicle_id}",
    status_code=204,
    summary="Hard-delete a vehicle (no FK refs allowed)",
)
def delete_vehicle_endpoint(
    vehicle_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> Response:
    import sqlite3
    try:
        deleted = delete_vehicle_for_owner(
            vehicle_id, user.id, db_path=db_path,
        )
    except VehicleOwnershipError:
        raise VehicleOwnershipError(
            f"vehicle id={vehicle_id} not found"
        )
    except sqlite3.IntegrityError as e:
        # FK constraint — diagnostic sessions / known issues exist
        raise HTTPException(
            status_code=409,
            detail=(
                "vehicle has diagnostic history; archive instead of "
                "delete (FK constraint violated)"
            ),
        ) from e
    if not deleted:
        raise VehicleOwnershipError(
            f"vehicle id={vehicle_id} not found"
        )
    return Response(status_code=204)


@router.get(
    "/{vehicle_id}/sessions",
    response_model=SessionsForVehicleResponse,
    summary="List diagnostic sessions for a vehicle",
)
def list_vehicle_sessions_endpoint(
    vehicle_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> SessionsForVehicleResponse:
    # 404 on missing/cross-user vehicle
    row = get_vehicle_for_owner(
        vehicle_id, user.id, db_path=db_path,
    )
    if row is None:
        raise VehicleOwnershipError(
            f"vehicle id={vehicle_id} not found"
        )
    from motodiag.core.database import get_connection
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT * FROM diagnostic_sessions
               WHERE vehicle_id = ?
               ORDER BY created_at DESC, id DESC""",
            (vehicle_id,),
        ).fetchall()
    sessions = [dict(r) for r in rows]
    return SessionsForVehicleResponse(
        vehicle_id=vehicle_id,
        sessions=sessions,
        total=len(sessions),
    )
