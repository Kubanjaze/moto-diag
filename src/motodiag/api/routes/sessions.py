"""Diagnostic session endpoints (Phase 178).

Exposes Phase 07 `diagnostic_sessions` over HTTP with owner scoping
+ monthly quota (individual=50, shop=500, company=unlimited).

Recipe is identical to Phase 177 vehicles — auth via
`Depends(get_current_user)`, tier quota enforced at POST, cross-user
404 (not 403). Lifecycle transitions (close/reopen) are dedicated
POST endpoints distinct from the generic PATCH.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict, Field

from motodiag.api.deps import get_db_path
from motodiag.auth.deps import AuthedUser, get_current_user
from motodiag.core.session_repo import (
    SessionOwnershipError,
    TIER_SESSION_MONTHLY_LIMITS,
    _assert_owner,
    add_fault_code_for_owner,
    add_symptom_for_owner,
    append_note_for_owner,
    check_session_quota,
    close_session_for_owner,
    count_sessions_this_month_for_owner,
    create_session_for_owner,
    get_session_for_owner,
    list_sessions_for_owner,
    reopen_session_for_owner,
    update_session_for_owner,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["sessions"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_WINDOW_RE = re.compile(r"^(\d+)([dhm])$", re.IGNORECASE)


def _parse_since(since: Optional[str]) -> Optional[str]:
    """Accept `Nd`/`Nh`/`Nm` or ISO; return ISO cutoff."""
    if since is None:
        return None
    s = since.strip()
    if not s:
        return None
    m = _WINDOW_RE.match(s)
    if m is not None:
        n = int(m.group(1))
        unit = m.group(2).lower()
        now = datetime.now(timezone.utc)
        if unit == "d":
            cutoff = now - timedelta(days=n)
        elif unit == "h":
            cutoff = now - timedelta(hours=n)
        else:
            cutoff = now - timedelta(minutes=n)
        return cutoff.isoformat()
    # Try ISO
    try:
        parsed = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError as e:
        raise ValueError(
            f"since must be Nd/Nh/Nm or ISO, got {since!r}"
        ) from e
    return parsed.isoformat()


def _quota_for(tier: Optional[str]) -> tuple[Optional[int], str]:
    effective = (
        tier if tier in TIER_SESSION_MONTHLY_LIMITS else "individual"
    )
    limit = TIER_SESSION_MONTHLY_LIMITS[effective]
    return (None if limit < 0 else limit), effective


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


SessionStatus = Literal["open", "in_progress", "closed"]


class SessionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    vehicle_make: str = Field(..., min_length=1, max_length=100)
    vehicle_model: str = Field(..., min_length=1, max_length=100)
    vehicle_year: int = Field(..., ge=1900, le=2100)
    symptoms: Optional[list[str]] = None
    fault_codes: Optional[list[str]] = None
    vehicle_id: Optional[int] = None


class SessionUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: Optional[SessionStatus] = None
    diagnosis: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    severity: Optional[str] = None
    cost_estimate: Optional[float] = Field(None, ge=0.0)
    ai_model_used: Optional[str] = None
    tokens_used: Optional[int] = Field(None, ge=0)


class SymptomRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    symptom: str = Field(..., min_length=1, max_length=500)


class FaultCodeRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    code: str = Field(..., min_length=1, max_length=50)


class NoteRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    note: str = Field(..., min_length=1, max_length=2000)


class SessionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    user_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    vehicle_make: str
    vehicle_model: str
    vehicle_year: int
    status: str
    symptoms: list[str] = Field(default_factory=list)
    fault_codes: list[str] = Field(default_factory=list)
    diagnosis: Optional[str] = None
    repair_steps: list[str] = Field(default_factory=list)
    confidence: Optional[float] = None
    severity: Optional[str] = None
    cost_estimate: Optional[float] = None
    ai_model_used: Optional[str] = None
    tokens_used: Optional[int] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    closed_at: Optional[str] = None


class SessionListResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    items: list[SessionResponse]
    total_this_month: int
    tier: Optional[str] = None
    monthly_quota_limit: Optional[int] = None
    monthly_quota_remaining: Optional[int] = None


def _row_to_response(row: dict) -> SessionResponse:
    return SessionResponse(
        id=int(row["id"]),
        user_id=row.get("user_id"),
        vehicle_id=row.get("vehicle_id"),
        vehicle_make=str(row.get("vehicle_make", "")),
        vehicle_model=str(row.get("vehicle_model", "")),
        vehicle_year=int(row.get("vehicle_year", 0)),
        status=str(row.get("status", "open")),
        symptoms=row.get("symptoms") or [],
        fault_codes=row.get("fault_codes") or [],
        diagnosis=row.get("diagnosis"),
        repair_steps=row.get("repair_steps") or [],
        confidence=row.get("confidence"),
        severity=row.get("severity"),
        cost_estimate=row.get("cost_estimate"),
        ai_model_used=row.get("ai_model_used"),
        tokens_used=row.get("tokens_used"),
        notes=row.get("notes"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        closed_at=row.get("closed_at"),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=SessionListResponse,
    summary="List diagnostic sessions owned by the caller",
)
def list_sessions_endpoint(
    status: Optional[SessionStatus] = None,
    vehicle_id: Optional[int] = None,
    since: Optional[str] = None,
    limit: int = 100,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> SessionListResponse:
    since_iso = _parse_since(since)
    rows = list_sessions_for_owner(
        owner_user_id=user.id,
        status=status, vehicle_id=vehicle_id,
        since_iso=since_iso, limit=limit, db_path=db_path,
    )
    month_count = count_sessions_this_month_for_owner(
        user.id, db_path=db_path,
    )
    quota_limit, effective_tier = _quota_for(user.tier)
    remaining = (
        None if quota_limit is None
        else max(quota_limit - month_count, 0)
    )
    return SessionListResponse(
        items=[_row_to_response(r) for r in rows],
        total_this_month=month_count,
        tier=effective_tier,
        monthly_quota_limit=quota_limit,
        monthly_quota_remaining=remaining,
    )


@router.post(
    "",
    response_model=SessionResponse,
    status_code=201,
    summary="Start a new diagnostic session",
)
def create_session_endpoint(
    req: SessionCreateRequest,
    response: Response,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> SessionResponse:
    check_session_quota(
        owner_user_id=user.id, tier=user.tier, db_path=db_path,
    )
    sid = create_session_for_owner(
        owner_user_id=user.id,
        vehicle_make=req.vehicle_make,
        vehicle_model=req.vehicle_model,
        vehicle_year=req.vehicle_year,
        symptoms=req.symptoms,
        fault_codes=req.fault_codes,
        vehicle_id=req.vehicle_id,
        db_path=db_path,
    )
    row = get_session_for_owner(sid, user.id, db_path=db_path)
    assert row is not None
    response.headers["Location"] = f"/v1/sessions/{sid}"
    return _row_to_response(row)


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Fetch a diagnostic session",
)
def get_session_endpoint(
    session_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> SessionResponse:
    row = get_session_for_owner(
        session_id, user.id, db_path=db_path,
    )
    if row is None:
        raise SessionOwnershipError(
            f"session id={session_id} not found"
        )
    return _row_to_response(row)


@router.patch(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Partially update a diagnostic session",
)
def update_session_endpoint(
    session_id: int,
    req: SessionUpdateRequest,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> SessionResponse:
    updates = {
        k: v for k, v in req.model_dump(exclude_unset=True).items()
        if v is not None
    }
    if updates:
        try:
            changed = update_session_for_owner(
                session_id, user.id, updates, db_path=db_path,
            )
        except SessionOwnershipError:
            raise SessionOwnershipError(
                f"session id={session_id} not found"
            )
        if not changed:
            raise SessionOwnershipError(
                f"session id={session_id} not found"
            )
    row = get_session_for_owner(
        session_id, user.id, db_path=db_path,
    )
    if row is None:
        raise SessionOwnershipError(
            f"session id={session_id} not found"
        )
    return _row_to_response(row)


@router.post(
    "/{session_id}/close",
    response_model=SessionResponse,
    summary="Close a diagnostic session",
)
def close_session_endpoint(
    session_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> SessionResponse:
    try:
        changed = close_session_for_owner(
            session_id, user.id, db_path=db_path,
        )
    except SessionOwnershipError:
        raise SessionOwnershipError(
            f"session id={session_id} not found"
        )
    if not changed:
        raise SessionOwnershipError(
            f"session id={session_id} not found"
        )
    row = get_session_for_owner(session_id, user.id, db_path=db_path)
    assert row is not None
    return _row_to_response(row)


@router.post(
    "/{session_id}/reopen",
    response_model=SessionResponse,
    summary="Reopen a closed diagnostic session",
)
def reopen_session_endpoint(
    session_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> SessionResponse:
    try:
        changed = reopen_session_for_owner(
            session_id, user.id, db_path=db_path,
        )
    except SessionOwnershipError:
        raise SessionOwnershipError(
            f"session id={session_id} not found"
        )
    if not changed:
        raise SessionOwnershipError(
            f"session id={session_id} not found"
        )
    row = get_session_for_owner(session_id, user.id, db_path=db_path)
    assert row is not None
    return _row_to_response(row)


@router.post(
    "/{session_id}/symptoms",
    response_model=SessionResponse,
    summary="Append a symptom to a session",
)
def add_symptom_endpoint(
    session_id: int,
    req: SymptomRequest,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> SessionResponse:
    try:
        changed = add_symptom_for_owner(
            session_id, user.id, req.symptom, db_path=db_path,
        )
    except SessionOwnershipError:
        raise SessionOwnershipError(
            f"session id={session_id} not found"
        )
    if not changed:
        raise SessionOwnershipError(
            f"session id={session_id} not found"
        )
    row = get_session_for_owner(session_id, user.id, db_path=db_path)
    assert row is not None
    return _row_to_response(row)


@router.post(
    "/{session_id}/fault-codes",
    response_model=SessionResponse,
    summary="Append a fault code to a session",
)
def add_fault_code_endpoint(
    session_id: int,
    req: FaultCodeRequest,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> SessionResponse:
    try:
        changed = add_fault_code_for_owner(
            session_id, user.id, req.code, db_path=db_path,
        )
    except SessionOwnershipError:
        raise SessionOwnershipError(
            f"session id={session_id} not found"
        )
    if not changed:
        raise SessionOwnershipError(
            f"session id={session_id} not found"
        )
    row = get_session_for_owner(session_id, user.id, db_path=db_path)
    assert row is not None
    return _row_to_response(row)


@router.post(
    "/{session_id}/notes",
    response_model=SessionResponse,
    summary="Append a note to a session",
)
def append_note_endpoint(
    session_id: int,
    req: NoteRequest,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> SessionResponse:
    try:
        changed = append_note_for_owner(
            session_id, user.id, req.note, db_path=db_path,
        )
    except SessionOwnershipError:
        raise SessionOwnershipError(
            f"session id={session_id} not found"
        )
    if not changed:
        raise SessionOwnershipError(
            f"session id={session_id} not found"
        )
    row = get_session_for_owner(session_id, user.id, db_path=db_path)
    assert row is not None
    return _row_to_response(row)
