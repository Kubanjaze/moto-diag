"""Phase 201 — parts ordering from mobile.

Composes the Track G parts domain (`shop/parts_needs.py`,
`advanced/parts_repo.py`) over HTTP. Those functions have carried the
CLI since Phase 153/164 and have their own tests; this module adds HTTP
shape, shop scoping, and exactly one new behaviour — the long-missing
`parts_arrived` producer on the `received` transition.

Route map (all `require_tier("shop")` + active shop membership):

    GET    /shop/{shop_id}/parts/search                         catalog browse
    GET    /shop/{shop_id}/parts/needs                          consolidated open needs
    GET    /shop/{shop_id}/parts/requisitions                   list snapshots
    POST   /shop/{shop_id}/parts/requisitions                   snapshot the shopping list
    GET    /shop/{shop_id}/parts/requisitions/{req_id}
    GET    /shop/{shop_id}/parts/{part_id}                      catalog detail + xrefs
    GET    /shop/{shop_id}/work-orders/{wo_id}/parts            the cart
    POST   /shop/{shop_id}/work-orders/{wo_id}/parts            add to cart
    POST   /shop/{shop_id}/work-orders/{wo_id}/parts/order      Order: every open line → ordered
    PATCH  /shop/{shop_id}/work-orders/{wo_id}/parts/{wop_id}   quantity / cost override
    DELETE /shop/{shop_id}/work-orders/{wo_id}/parts/{wop_id}   remove (open) or cancel
    POST   /shop/{shop_id}/work-orders/{wo_id}/parts/{wop_id}/transition

The cart is a view, not a thing: `work_order_parts.status = 'open'` IS
cart membership (Phase 201 user decision). That is why no client-side
store exists on mobile and why ADR-003 stays untripped.

"Order" is the internal line lifecycle, not a supplier purchase order —
no supplier integration exists anywhere and Track O Phase 279 reserves
PO generation. `vendors` / `inventory_items` are not touched here.
"""

from __future__ import annotations

import logging
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field

from motodiag.advanced.parts_repo import (
    get_xrefs,
    list_parts_for_bike,
    search_parts,
)
from motodiag.api.deps import get_db_path
from motodiag.api.routes.shop_mgmt import require_shop_access
from motodiag.auth.deps import AuthedUser, get_current_user, require_tier
from motodiag.core.database import get_connection
from motodiag.push.events import notify_parts_arrived
from motodiag.shop.notifications import (
    NotificationContextError,
    trigger_notification,
)
from motodiag.shop.parts_needs import (
    ConsolidatedPartNeed,
    Requisition,
    WorkOrderPartLine,
    add_part_to_work_order,
    build_requisition,
    cancel_part_need,
    get_requisition,
    list_parts_for_shop_open_wos,
    list_parts_for_wo,
    list_requisitions,
    mark_part_installed,
    mark_part_ordered,
    mark_part_received,
    remove_part_from_work_order,
    update_part_cost_override,
    update_part_quantity,
)
from motodiag.shop.work_order_repo import get_work_order

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/shop", tags=["parts"])

#: Wire-level transition verbs. Mirrors the CHECK constraint on
#: `work_order_parts.status` (F37 Literal discipline) — `cancel` is a
#: verb here because the domain function is `cancel_part_need`, not a
#: status transition to a target.
PartTransitionAction = Literal["ordered", "received", "installed", "cancel"]


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class PartSummary(BaseModel):
    """Catalog row as the browse screen sees it."""
    model_config = ConfigDict(extra="ignore")

    id: int
    slug: str
    oem_part_number: Optional[str] = None
    brand: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    make: Optional[str] = None
    model_pattern: Optional[str] = None
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    typical_cost_cents: Optional[int] = None
    purchase_url: Optional[str] = None


class PartDetail(PartSummary):
    """Catalog row + ranked aftermarket alternatives."""
    xrefs: list[dict[str, Any]] = Field(default_factory=list)


class AddPartRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    part_id: int
    quantity: int = Field(1, ge=1, le=999)
    unit_cost_cents_override: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=500)


class PartLineResponse(WorkOrderPartLine):
    """A cart line. `merged` is True when an add landed on an existing
    open line for the same part and bumped its quantity instead."""
    merged: bool = False


class UpdatePartLineRequest(BaseModel):
    """Both fields optional; `unit_cost_cents_override` distinguishes
    "not sent" from explicit `null` (clear the override) via
    `model_fields_set` — a 0 here means "free", not "no override"."""
    model_config = ConfigDict(extra="ignore")
    quantity: Optional[int] = Field(None, ge=1, le=999)
    unit_cost_cents_override: Optional[int] = Field(None, ge=0)


class PartTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    action: PartTransitionAction
    reason: Optional[str] = Field(None, max_length=200)


class OrderAllResponse(BaseModel):
    ordered: int
    lines: list[PartLineResponse]


class RequisitionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    wo_ids: Optional[list[int]] = None
    notes: Optional[str] = Field(None, max_length=500)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_wo(shop_id: int, wo_id: int, db_path: str) -> dict:
    """Work order must exist AND belong to this shop; else 404 (the
    existing cross-shop enumeration posture)."""
    wo = get_work_order(wo_id, db_path=db_path)
    if wo is None or wo.get("shop_id") != shop_id:
        raise HTTPException(
            status_code=404, detail=f"work order id={wo_id} not found",
        )
    return wo


def _line_dict_to_response(d: dict, merged: bool = False) -> PartLineResponse:
    """`list_parts_for_wo` joins raw catalog columns onto the line row;
    the wire model uses the `part_*` names from WorkOrderPartLine."""
    return PartLineResponse.model_validate({
        **d,
        "part_number": d.get("oem_part_number"),
        "part_brand": d.get("brand"),
        "part_description": d.get("description"),
        "part_category": d.get("category"),
        "merged": merged,
    })


def _lines(wo_id: int, db_path: str, include_cancelled: bool = False) -> list[dict]:
    return list_parts_for_wo(
        wo_id, include_cancelled=include_cancelled, db_path=db_path,
    )


def _require_line(wo_id: int, wop_id: int, db_path: str) -> dict:
    """Line must belong to THIS work order. A line id from another WO
    in the same shop is a 404, not a cross-WO edit."""
    for line in _lines(wo_id, db_path, include_cancelled=True):
        if int(line["id"]) == wop_id:
            return line
    raise HTTPException(
        status_code=404,
        detail=f"part line id={wop_id} not found on work order id={wo_id}",
    )


def _get_part_by_id(part_id: int, db_path: str) -> Optional[dict]:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM parts WHERE id = ?", (part_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def _fire_parts_arrived(
    wo: dict, line: dict, user: AuthedUser, db_path: str,
) -> None:
    """The `parts_arrived` producer Phase 170 never got.

    Two consumers, both best-effort and both isolated from the response
    path: the customer notification queue (transport-less until Track
    J — this records intent, it does not send) and a Phase 199 push to
    the assigned mechanic (self-suppressed inside).
    """
    try:
        trigger_notification(
            "parts_arrived",
            wo_id=int(wo["id"]),
            triggered_by_user_id=user.id,
            db_path=db_path,
        )
    except NotificationContextError as exc:
        # EXPECTED and common: the work order's customer has no email
        # (or is the id-1 "Unassigned" sentinel). Not a defect — plenty
        # of real jobs are walk-ins with no contact on file. One
        # readable line, no traceback: a stack trace here would train
        # everyone to ignore this log.
        logger.info(
            "parts_arrived not queued for wo=%s: %s", wo.get("id"), exc,
        )
    except Exception:  # noqa: BLE001 — a queue hiccup never blocks receiving parts
        # UNEXPECTED: keep the traceback, this one deserves attention.
        logger.exception(
            "parts_arrived queue trigger failed for wo=%s (suppressed)",
            wo.get("id"),
        )
    notify_parts_arrived(wo, line, user.id, db_path=db_path)


# ---------------------------------------------------------------------------
# Catalog browse
# ---------------------------------------------------------------------------


@router.get(
    "/{shop_id}/parts/search",
    response_model=list[PartSummary],
    summary="Browse the parts catalog (free text, or by bike)",
    dependencies=[Depends(require_tier("shop"))],
)
def search_catalog(
    shop_id: int,
    q: str = Query("", max_length=120),
    make: Optional[str] = Query(None, max_length=60),
    model: Optional[str] = Query(None, max_length=60),
    year: Optional[int] = Query(None, ge=1900, le=2100),
    category: Optional[str] = Query(None, max_length=60),
    limit: int = Query(25, ge=1, le=100),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> list[PartSummary]:
    require_shop_access(shop_id, user, db_path)
    # No free text + a known bike → the fitment list for that bike is
    # the better first screen. Free text always wins when present.
    if not q.strip() and make and model:
        rows = list_parts_for_bike(
            make, model, year=year, category=category, db_path=db_path,
        )[:limit]
    else:
        rows = search_parts(
            q, make=make, category=category, limit=limit, db_path=db_path,
        )
    return [PartSummary.model_validate(r) for r in rows]


@router.get(
    "/{shop_id}/parts/needs",
    response_model=list[ConsolidatedPartNeed],
    summary="Consolidated open part needs across the shop's active work orders",
    dependencies=[Depends(require_tier("shop"))],
)
def shop_part_needs(
    shop_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> list[ConsolidatedPartNeed]:
    require_shop_access(shop_id, user, db_path)
    return list_parts_for_shop_open_wos(shop_id, db_path=db_path)


# ---------------------------------------------------------------------------
# Requisitions (declared before /parts/{part_id} so "requisitions" is
# never parsed as a part id)
# ---------------------------------------------------------------------------


@router.get(
    "/{shop_id}/parts/requisitions",
    response_model=list[dict[str, Any]],
    summary="List requisition snapshots, newest first",
    dependencies=[Depends(require_tier("shop"))],
)
def list_shop_requisitions(
    shop_id: int,
    limit: int = Query(50, ge=1, le=200),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> list[dict[str, Any]]:
    require_shop_access(shop_id, user, db_path)
    return list_requisitions(shop_id=shop_id, limit=limit, db_path=db_path)


@router.post(
    "/{shop_id}/parts/requisitions",
    response_model=Requisition,
    status_code=201,
    summary="Snapshot the consolidated shopping list as a requisition",
    dependencies=[Depends(require_tier("shop"))],
)
def create_shop_requisition(
    shop_id: int,
    req: RequisitionCreateRequest,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> Requisition:
    require_shop_access(shop_id, user, db_path)
    req_id = build_requisition(
        shop_id, wo_ids=req.wo_ids, generated_by_user_id=user.id,
        notes=req.notes, db_path=db_path,
    )
    built = get_requisition(req_id, db_path=db_path)
    assert built is not None  # just created
    return built


@router.get(
    "/{shop_id}/parts/requisitions/{req_id}",
    response_model=Requisition,
    summary="One requisition with its items",
    dependencies=[Depends(require_tier("shop"))],
)
def get_shop_requisition(
    shop_id: int,
    req_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> Requisition:
    require_shop_access(shop_id, user, db_path)
    built = get_requisition(req_id, db_path=db_path)
    if built is None or built.shop_id != shop_id:
        raise HTTPException(
            status_code=404, detail=f"requisition id={req_id} not found",
        )
    return built


@router.get(
    "/{shop_id}/parts/{part_id}",
    response_model=PartDetail,
    summary="Catalog part detail with ranked aftermarket alternatives",
    dependencies=[Depends(require_tier("shop"))],
)
def get_catalog_part(
    shop_id: int,
    part_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> PartDetail:
    require_shop_access(shop_id, user, db_path)
    part = _get_part_by_id(part_id, db_path)
    if part is None:
        raise HTTPException(
            status_code=404, detail=f"part id={part_id} not found",
        )
    xrefs = (
        get_xrefs(part["oem_part_number"], db_path=db_path)
        if part.get("oem_part_number") else []
    )
    return PartDetail.model_validate({**part, "xrefs": xrefs})


# ---------------------------------------------------------------------------
# The cart: a work order's part lines
# ---------------------------------------------------------------------------


@router.get(
    "/{shop_id}/work-orders/{wo_id}/parts",
    response_model=list[PartLineResponse],
    summary="Part lines on a work order (open lines are the cart)",
    dependencies=[Depends(require_tier("shop"))],
)
def list_wo_parts(
    shop_id: int,
    wo_id: int,
    include_cancelled: bool = Query(False),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> list[PartLineResponse]:
    require_shop_access(shop_id, user, db_path)
    _require_wo(shop_id, wo_id, db_path)
    return [
        _line_dict_to_response(d)
        for d in _lines(wo_id, db_path, include_cancelled=include_cancelled)
    ]


@router.post(
    "/{shop_id}/work-orders/{wo_id}/parts",
    response_model=PartLineResponse,
    status_code=201,
    summary="Add a catalog part to the work order (open line = in the cart)",
    dependencies=[Depends(require_tier("shop"))],
)
def add_wo_part(
    shop_id: int,
    wo_id: int,
    req: AddPartRequest,
    response: Response,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> PartLineResponse:
    require_shop_access(shop_id, user, db_path)
    _require_wo(shop_id, wo_id, db_path)

    # Same part already open on this WO → bump quantity rather than
    # grow a second line. Composed from existing calls; the domain
    # layer itself does not dedupe (it inserts every time).
    for existing in _lines(wo_id, db_path):
        if (
            int(existing["part_id"]) == req.part_id
            and existing["status"] == "open"
        ):
            update_part_quantity(
                int(existing["id"]),
                int(existing["quantity"]) + req.quantity,
                db_path=db_path,
            )
            response.status_code = 200
            return _line_dict_to_response(
                _require_line(wo_id, int(existing["id"]), db_path),
                merged=True,
            )

    wop_id = add_part_to_work_order(
        wo_id, req.part_id, quantity=req.quantity,
        unit_cost_override=req.unit_cost_cents_override,
        notes=req.notes,
        created_by_user_id=user.id,  # NOT the seed-user default
        db_path=db_path,
    )
    return _line_dict_to_response(_require_line(wo_id, wop_id, db_path))


@router.post(
    "/{shop_id}/work-orders/{wo_id}/parts/order",
    response_model=OrderAllResponse,
    summary="Order: move every open line on the work order to ordered",
    dependencies=[Depends(require_tier("shop"))],
)
def order_wo_parts(
    shop_id: int,
    wo_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> OrderAllResponse:
    require_shop_access(shop_id, user, db_path)
    _require_wo(shop_id, wo_id, db_path)
    ordered = 0
    for line in _lines(wo_id, db_path):
        if line["status"] == "open":
            mark_part_ordered(int(line["id"]), db_path=db_path)
            ordered += 1
    logger.info(
        "user=%s ordered %s line(s) on wo=%s", user.id, ordered, wo_id,
    )
    return OrderAllResponse(
        ordered=ordered,
        lines=[_line_dict_to_response(d) for d in _lines(wo_id, db_path)],
    )


@router.patch(
    "/{shop_id}/work-orders/{wo_id}/parts/{wop_id}",
    response_model=PartLineResponse,
    summary="Change a line's quantity and/or unit-cost override",
    dependencies=[Depends(require_tier("shop"))],
)
def update_wo_part(
    shop_id: int,
    wo_id: int,
    wop_id: int,
    req: UpdatePartLineRequest,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> PartLineResponse:
    require_shop_access(shop_id, user, db_path)
    _require_wo(shop_id, wo_id, db_path)
    _require_line(wo_id, wop_id, db_path)
    if req.quantity is not None:
        update_part_quantity(wop_id, req.quantity, db_path=db_path)
    if "unit_cost_cents_override" in req.model_fields_set:
        update_part_cost_override(
            wop_id, req.unit_cost_cents_override, db_path=db_path,
        )
    return _line_dict_to_response(_require_line(wo_id, wop_id, db_path))


@router.delete(
    "/{shop_id}/work-orders/{wo_id}/parts/{wop_id}",
    summary="Take a line off the work order (delete if open, cancel otherwise)",
    dependencies=[Depends(require_tier("shop"))],
)
def delete_wo_part(
    shop_id: int,
    wo_id: int,
    wop_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict[str, Any]:
    require_shop_access(shop_id, user, db_path)
    _require_wo(shop_id, wo_id, db_path)
    line = _require_line(wo_id, wop_id, db_path)
    if line["status"] == "open":
        remove_part_from_work_order(wop_id, db_path=db_path)
        return {"removed": True, "cancelled": False}
    # Past `open` the line has history worth keeping → cancel, keep row.
    # InvalidPartNeedTransition (already cancelled/installed) → 409 via
    # the existing error mapping.
    cancel_part_need(wop_id, reason="removed from app", db_path=db_path)
    return {"removed": False, "cancelled": True}


@router.post(
    "/{shop_id}/work-orders/{wo_id}/parts/{wop_id}/transition",
    response_model=PartLineResponse,
    summary="Advance a line: ordered → received → installed, or cancel",
    dependencies=[Depends(require_tier("shop"))],
)
def transition_wo_part(
    shop_id: int,
    wo_id: int,
    wop_id: int,
    req: PartTransitionRequest,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> PartLineResponse:
    require_shop_access(shop_id, user, db_path)
    wo = _require_wo(shop_id, wo_id, db_path)
    _require_line(wo_id, wop_id, db_path)

    # Illegal transitions raise InvalidPartNeedTransition → 409 through
    # api/errors.py; nothing to catch here.
    if req.action == "ordered":
        mark_part_ordered(wop_id, db_path=db_path)
    elif req.action == "received":
        mark_part_received(wop_id, db_path=db_path)
    elif req.action == "installed":
        mark_part_installed(wop_id, db_path=db_path)
    else:
        cancel_part_need(wop_id, reason=req.reason, db_path=db_path)

    line = _require_line(wo_id, wop_id, db_path)
    if req.action == "received":
        _fire_parts_arrived(wo, line, user, db_path)
    return _line_dict_to_response(line)
