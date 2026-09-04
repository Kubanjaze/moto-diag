"""Phase 202 — mechanic time tracking over HTTP.

Composes `shop/time_entries.py` with the Phase 201 router idiom:
`require_tier("shop")` + active membership + a WO-belongs-to-shop 404.

Route map:
    POST  /shop/{shop_id}/work-orders/{wo_id}/clock-in
    POST  /shop/{shop_id}/work-orders/{wo_id}/clock-out
    GET   /shop/{shop_id}/work-orders/{wo_id}/time-entries
    GET   /shop/{shop_id}/time-entries/mine/open
    PATCH /shop/{shop_id}/time-entries/{entry_id}

Two authorization notes, both deliberate:

- **Any active member may clock in, and the entry is attributed to the
  CALLER** — never to a user id in the request body. Gating on
  `manage_shop` (the only permission mode the shop routes use today)
  would have locked the mechanics out: the seeded matrix gives `tech`
  and `apprentice` no such permission while `service_writer` has it.
  Gating on assignment was rejected because nothing else in the codebase
  enforces assignment.
- **"Mine" means the API key's user.** The mobile client has no notion
  of its own user id, so the server answers "my open entry" rather than
  accepting one to look up. That also makes it impossible to read
  another mechanic's running timer through this route.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from motodiag.api.deps import get_db_path
from motodiag.auth.deps import AuthedUser, get_current_user, require_tier
from motodiag.api.routes.shop_mgmt import require_shop_access
from motodiag.shop.time_entries import (
    adjust_entry,
    clock_in,
    clock_out,
    get_open_entry_for_user,
    list_entries_for_wo,
    total_seconds_for_wo,
)
from motodiag.shop.work_order_repo import get_work_order

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/shop", tags=["time-tracking"])


class TimeEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    work_order_id: int
    user_id: int
    started_at: str
    ended_at: Optional[str] = None
    duration_seconds: Optional[int] = None
    source: str
    needs_review: int = 0
    note: Optional[str] = None


class ClockInResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    entry: TimeEntry
    #: The entry this clock-in stopped, if the caller had one running
    #: elsewhere. The UI must surface it — a mechanic who never sees
    #: this will not understand where their time went.
    auto_closed: Optional[TimeEntry] = None


class WorkOrderTimeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    entries: list[TimeEntry]
    total_seconds: int
    #: Closed-entry total as billable hours, 2dp — the value that would
    #: land in `actual_hours` if the job completed now with nothing
    #: supplied.
    total_hours: float


class OpenEntryResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    entry: Optional[TimeEntry] = None


class TimeEntryAdjustRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    note: Optional[str] = Field(None, max_length=500)
    needs_review: Optional[bool] = None


def _require_wo(shop_id: int, wo_id: int, db_path: str) -> dict:
    """WO must exist AND belong to this shop; else 404 (the existing
    cross-shop enumeration posture)."""
    wo = get_work_order(wo_id, db_path=db_path)
    if wo is None or wo.get("shop_id") != shop_id:
        raise HTTPException(
            status_code=404, detail=f"work order id={wo_id} not found",
        )
    return wo


def _require_entry_in_shop(
    shop_id: int, entry_id: int, db_path: str,
) -> dict:
    """Resolve an entry and prove its work order belongs to this shop."""
    from motodiag.core.database import get_connection
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM work_order_time_entries WHERE id = ?",
            (entry_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"time entry id={entry_id} not found",
        )
    entry = dict(row)
    _require_wo(shop_id, int(entry["work_order_id"]), db_path)
    return entry


@router.post(
    "/{shop_id}/work-orders/{wo_id}/clock-in",
    response_model=ClockInResponse,
    status_code=201,
    summary="Start the labor clock on a work order",
    dependencies=[Depends(require_tier("shop"))],
)
def clock_in_endpoint(
    shop_id: int,
    wo_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> ClockInResponse:
    require_shop_access(shop_id, user, db_path)
    _require_wo(shop_id, wo_id, db_path)
    entry, auto_closed = clock_in(wo_id, user.id, db_path=db_path)
    return ClockInResponse(
        entry=TimeEntry.model_validate(entry),
        auto_closed=(
            TimeEntry.model_validate(auto_closed) if auto_closed else None
        ),
    )


@router.post(
    "/{shop_id}/work-orders/{wo_id}/clock-out",
    response_model=TimeEntry,
    summary="Stop the labor clock on a work order",
    dependencies=[Depends(require_tier("shop"))],
)
def clock_out_endpoint(
    shop_id: int,
    wo_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> TimeEntry:
    require_shop_access(shop_id, user, db_path)
    _require_wo(shop_id, wo_id, db_path)
    # NoOpenTimeEntryError maps to a ProblemDetail via api/errors.py.
    closed = clock_out(user.id, wo_id=wo_id, db_path=db_path)
    return TimeEntry.model_validate(closed)


@router.get(
    "/{shop_id}/work-orders/{wo_id}/time-entries",
    response_model=WorkOrderTimeResponse,
    summary="All labor entries on a work order",
    dependencies=[Depends(require_tier("shop"))],
)
def list_wo_time_entries(
    shop_id: int,
    wo_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> WorkOrderTimeResponse:
    require_shop_access(shop_id, user, db_path)
    _require_wo(shop_id, wo_id, db_path)
    entries = list_entries_for_wo(wo_id, db_path=db_path)
    total = total_seconds_for_wo(wo_id, db_path=db_path)
    return WorkOrderTimeResponse(
        entries=[TimeEntry.model_validate(e) for e in entries],
        total_seconds=total,
        total_hours=round(total / 3600.0, 2),
    )


@router.get(
    "/{shop_id}/time-entries/mine/open",
    response_model=OpenEntryResponse,
    summary="The caller's currently-running entry, if any",
    dependencies=[Depends(require_tier("shop"))],
)
def my_open_entry(
    shop_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> OpenEntryResponse:
    require_shop_access(shop_id, user, db_path)
    entry = get_open_entry_for_user(user.id, db_path=db_path)
    # An entry running on ANOTHER shop's work order is not this shop's
    # business; the client asks per-shop and gets a per-shop answer.
    if entry is not None:
        wo = get_work_order(int(entry["work_order_id"]), db_path=db_path)
        if wo is None or wo.get("shop_id") != shop_id:
            entry = None
    return OpenEntryResponse(
        entry=TimeEntry.model_validate(entry) if entry else None,
    )


@router.patch(
    "/{shop_id}/time-entries/{entry_id}",
    response_model=TimeEntry,
    summary="Correct an entry's times / note, or clear its review flag",
    dependencies=[Depends(require_tier("shop"))],
)
def adjust_time_entry(
    shop_id: int,
    entry_id: int,
    req: TimeEntryAdjustRequest,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> TimeEntry:
    require_shop_access(shop_id, user, db_path)
    _require_entry_in_shop(shop_id, entry_id, db_path)
    updated = adjust_entry(
        entry_id,
        started_at=req.started_at, ended_at=req.ended_at,
        note=req.note, needs_review=req.needs_review, db_path=db_path,
    )
    return TimeEntry.model_validate(updated)
