"""Shop management endpoints (Phase 180).

Exposes Track G's 16-subgroup shop console over HTTP as 24 pragmatic
endpoints across 9 sub-surfaces (profile, members, customers, intake,
work-orders, issues, invoices, notifications, analytics).

All endpoints require `require_tier("shop")` + shop membership check
via Phase 172 RBAC. Cross-shop attempts return 403 (not 404) because
shops are global-registry entities — the honest response when a user
isn't a member of a named shop is "forbidden", not "doesn't exist".

Zero migration — composes existing `motodiag.shop.*` functions.
"""

from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field

from motodiag.api.deps import get_db_path
from motodiag.auth.deps import (
    AuthedUser, SUBSCRIPTION_TIERS, get_current_user, require_tier,
)
from motodiag.shop import (
    add_shop_member,
    build_triage_queue,
    create_intake,
    create_issue,
    create_shop,
    create_work_order,
    dashboard_snapshot,
    generate_invoice_for_wo,
    get_shop,
    get_shop_by_name,
    get_invoice_with_items,
    has_shop_permission,
    list_invoices_for_shop,
    list_issues,
    list_intakes,
    list_notifications,
    list_shop_members,
    list_shops,
    list_work_orders,
    get_work_order,
    require_shop_permission,
    revenue_rollup,
    seed_first_owner,
    top_issues,
    trigger_notification,
    update_shop,
)
from motodiag.shop.rbac import PermissionDenied
from motodiag.shop.work_order_repo import (
    cancel_work_order, complete_work_order,
    open_work_order, pause_work, reopen_work_order,
    resume_work, start_work,
)
from motodiag.crm import customer_repo
from motodiag.crm.models import Customer


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/shop", tags=["shop-management"])


# ---------------------------------------------------------------------------
# Shop-scope authorization
# ---------------------------------------------------------------------------


def require_shop_access(
    shop_id: int,
    user: AuthedUser,
    db_path: str,
    permission: Optional[str] = None,
) -> None:
    """Combined tier + shop-membership check.

    Two modes:
    - ``permission=None`` (default for reads): caller must be any
      active member of the shop (any role).
    - ``permission="manage_shop"`` (for mutations): caller must hold
      the named Phase 112 permission via their per-shop role.

    `require_tier("shop")` has already fired before this is called.
    Non-members get 403 (Phase 172 semantics).
    """
    from motodiag.shop import get_shop_member
    if permission is None:
        member = get_shop_member(
            shop_id=shop_id, user_id=user.id, db_path=db_path,
        )
        if member is None or not member.is_active:
            raise PermissionDenied(
                f"user id={user.id} is not an active member of "
                f"shop id={shop_id}"
            )
        return
    if not has_shop_permission(
        shop_id=shop_id, user_id=user.id,
        permission=permission, db_path=db_path,
    ):
        raise PermissionDenied(
            f"user id={user.id} lacks {permission!r} at shop id={shop_id}"
        )


# ---------------------------------------------------------------------------
# Shared schemas
# ---------------------------------------------------------------------------


TransitionAction = Literal[
    "open", "start", "pause", "resume",
    "complete", "cancel", "reopen",
]


class ShopCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., min_length=1, max_length=200)
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    tax_id: Optional[str] = None


class ShopUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    tax_id: Optional[str] = None


class MemberAddRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: int
    role: Literal["owner", "tech", "service_writer", "apprentice"]


class CustomerCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(..., min_length=1, max_length=200)
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class IntakeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    customer_id: int
    vehicle_id: int
    reported_problems: Optional[str] = None
    mileage_at_intake: Optional[int] = Field(None, ge=0)


class WorkOrderCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    vehicle_id: int
    customer_id: int
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    priority: int = Field(3, ge=1, le=5)
    estimated_hours: Optional[float] = Field(None, ge=0)
    intake_visit_id: Optional[int] = None


class WorkOrderTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    action: TransitionAction
    reason: Optional[str] = None
    actual_hours: Optional[float] = Field(None, ge=0)


class IssueCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    work_order_id: int
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: str = "other"
    severity: Literal["low", "medium", "high", "critical"] = "medium"


class InvoiceGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    work_order_id: int
    tax_rate: float = Field(0.0, ge=0.0, le=1.0)
    shop_supplies_pct: float = Field(0.0, ge=0.0, le=1.0)
    shop_supplies_flat_cents: int = Field(0, ge=0)
    diagnostic_fee_cents: int = Field(0, ge=0)
    labor_hourly_rate_cents: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None


class NotificationTriggerRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    event: str
    wo_id: Optional[int] = None
    invoice_id: Optional[int] = None
    customer_id: Optional[int] = None
    channel: Literal["email", "sms", "in_app"] = "email"
    extra_context: Optional[dict] = None


# ---------------------------------------------------------------------------
# Profile routes
# ---------------------------------------------------------------------------


@router.get(
    "/profile/list",
    summary="List shops the caller has a membership at",
    dependencies=[Depends(require_tier("shop"))],
)
def list_shops_endpoint(
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    from motodiag.shop import list_shops_for_user
    memberships = list_shops_for_user(user.id, db_path=db_path)
    shops = []
    for m in memberships:
        shop = get_shop(m.shop_id, db_path=db_path)
        if shop is not None:
            shops.append({**shop, "my_role": m.role})
    return {"items": shops, "total": len(shops)}


@router.post(
    "/profile",
    status_code=201,
    summary="Create a new shop (caller becomes owner)",
    dependencies=[Depends(require_tier("shop"))],
)
def create_shop_endpoint(
    req: ShopCreateRequest,
    response: Response,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    shop_id = create_shop(
        name=req.name, address=req.address, city=req.city,
        state=req.state, zip=req.zip, phone=req.phone,
        email=req.email, tax_id=req.tax_id, db_path=db_path,
    )
    # Stamp caller as owner (idempotent seed)
    seed_first_owner(shop_id, user.id, db_path=db_path)
    row = get_shop(shop_id, db_path=db_path)
    response.headers["Location"] = f"/v1/shop/profile/{shop_id}"
    return row


@router.get(
    "/profile/{shop_id}",
    summary="Fetch a shop profile",
    dependencies=[Depends(require_tier("shop"))],
)
def get_shop_profile(
    shop_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    require_shop_access(shop_id, user, db_path)
    row = get_shop(shop_id, db_path=db_path)
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"shop id={shop_id} not found",
        )
    return row


@router.patch(
    "/profile/{shop_id}",
    summary="Update a shop profile",
    dependencies=[Depends(require_tier("shop"))],
)
def update_shop_profile(
    shop_id: int,
    req: ShopUpdateRequest,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    require_shop_access(shop_id, user, db_path, permission="manage_shop")
    updates = {
        k: v for k, v in req.model_dump(exclude_unset=True).items()
        if v is not None
    }
    if updates:
        update_shop(shop_id, updates, db_path=db_path)
    row = get_shop(shop_id, db_path=db_path)
    if row is None:
        raise HTTPException(status_code=404, detail="shop not found")
    return row


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------


@router.get(
    "/{shop_id}/members",
    summary="List shop members",
    dependencies=[Depends(require_tier("shop"))],
)
def list_members(
    shop_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    require_shop_access(shop_id, user, db_path)
    members = list_shop_members(shop_id, db_path=db_path)
    return {
        "items": [m.model_dump() for m in members],
        "total": len(members),
    }


@router.post(
    "/{shop_id}/members",
    status_code=201,
    summary="Add a member to the shop",
    dependencies=[Depends(require_tier("shop"))],
)
def add_member(
    shop_id: int,
    req: MemberAddRequest,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    require_shop_access(shop_id, user, db_path, permission="manage_shop")
    add_shop_member(
        shop_id=shop_id, user_id=req.user_id, role=req.role,
        db_path=db_path,
    )
    return {"shop_id": shop_id, "user_id": req.user_id, "role": req.role}


@router.delete(
    "/{shop_id}/members/{target_user_id}",
    status_code=204,
    summary="Deactivate a shop member",
    dependencies=[Depends(require_tier("shop"))],
)
def deactivate_member_endpoint(
    shop_id: int,
    target_user_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> Response:
    require_shop_access(shop_id, user, db_path, permission="manage_shop")
    from motodiag.shop import deactivate_member
    deactivate_member(shop_id, target_user_id, db_path=db_path)
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Customers (thin wrapper over Phase 113 CRM repo)
# ---------------------------------------------------------------------------


@router.get(
    "/{shop_id}/customers",
    summary="List customers registered at the shop",
    dependencies=[Depends(require_tier("shop"))],
)
def list_customers_endpoint(
    shop_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    require_shop_access(shop_id, user, db_path)
    rows = customer_repo.list_customers(db_path=db_path)
    return {"items": rows, "total": len(rows)}


@router.post(
    "/{shop_id}/customers",
    status_code=201,
    summary="Add a customer to the shop",
    dependencies=[Depends(require_tier("shop"))],
)
def create_customer_endpoint(
    shop_id: int,
    req: CustomerCreateRequest,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    require_shop_access(shop_id, user, db_path)
    customer = Customer(
        name=req.name, email=req.email, phone=req.phone,
        address=req.address, notes=req.notes,
    )
    cid = customer_repo.create_customer(customer, db_path=db_path)
    return customer_repo.get_customer(cid, db_path=db_path)


@router.get(
    "/{shop_id}/customers/{customer_id}",
    summary="Fetch a customer record",
    dependencies=[Depends(require_tier("shop"))],
)
def get_customer_endpoint(
    shop_id: int,
    customer_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    require_shop_access(shop_id, user, db_path)
    row = customer_repo.get_customer(customer_id, db_path=db_path)
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"customer id={customer_id} not found",
        )
    return row


# ---------------------------------------------------------------------------
# Intake
# ---------------------------------------------------------------------------


@router.get(
    "/{shop_id}/intakes",
    summary="List bike intakes at the shop",
    dependencies=[Depends(require_tier("shop"))],
)
def list_intakes_endpoint(
    shop_id: int,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    require_shop_access(shop_id, user, db_path)
    rows = list_intakes(
        shop_id=shop_id, status=status, limit=limit, db_path=db_path,
    )
    return {"items": rows, "total": len(rows)}


@router.post(
    "/{shop_id}/intakes",
    status_code=201,
    summary="Log a bike intake",
    dependencies=[Depends(require_tier("shop"))],
)
def create_intake_endpoint(
    shop_id: int,
    req: IntakeCreateRequest,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    require_shop_access(shop_id, user, db_path)
    intake_id = create_intake(
        shop_id=shop_id, customer_id=req.customer_id,
        vehicle_id=req.vehicle_id,
        reported_problems=req.reported_problems,
        mileage_at_intake=req.mileage_at_intake,
        intake_user_id=user.id, db_path=db_path,
    )
    from motodiag.shop import get_intake
    return get_intake(intake_id, db_path=db_path)


# ---------------------------------------------------------------------------
# Work orders
# ---------------------------------------------------------------------------


@router.get(
    "/{shop_id}/work-orders",
    summary="List work orders for the shop",
    dependencies=[Depends(require_tier("shop"))],
)
def list_work_orders_endpoint(
    shop_id: int,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    sort: Optional[Literal["newest", "priority", "triage"]] = Query(
        None,
        description=(
            "Order: 'newest' (created_at DESC), 'priority' (priority "
            "ASC then created_at DESC — same as omitting), or "
            "'triage' (build_triage_queue scoring; rich score / rank / "
            "parts-ready context computed server-side, response shape "
            "stays uniform — see Phase 193 plan v1.0 + F35 candidate)."
        ),
    ),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    """List shop work orders with optional sort dispatch.

    Phase 193 Commit 0: ``sort`` query param added for the mobile
    Shop Dashboard's `Newest / Priority / Triage` toggle. Default
    behavior preserved (omitting `sort` matches existing
    `list_work_orders` ordering — backward compatible).

    Triage sort calls :func:`build_triage_queue` server-side and
    unwraps each :class:`TriageItem` to its plain ``work_order``
    dict — clients get a uniform response shape regardless of sort.
    Triage rank / score / parts-ready context stay server-side this
    phase; explainability surface is filed as F35 (mobile FOLLOWUPS).
    """
    require_shop_access(shop_id, user, db_path)
    if sort == "triage":
        items = build_triage_queue(shop_id=shop_id, db_path=db_path)
        # Unwrap to plain WO dicts in triage-rank order.
        rows = [item.work_order for item in items]
        # Honor `status` filter post-triage so the UI's status filter
        # still applies. build_triage_queue's include_terminal default
        # already excludes completed/cancelled.
        if status is not None:
            rows = [r for r in rows if r.get("status") == status]
        # Honor `limit` post-triage.
        if limit and limit > 0:
            rows = rows[:limit]
    else:
        rows = list_work_orders(
            shop_id=shop_id, status=status, limit=limit, db_path=db_path,
        )
        if sort == "newest":
            # Re-sort the priority-default ordering by created_at DESC.
            # Stable secondary by id DESC matches list_work_orders'
            # tiebreaker pattern.
            rows = sorted(
                rows,
                key=lambda r: (r.get("created_at") or "", r.get("id") or 0),
                reverse=True,
            )
        # sort == "priority" or sort is None → existing ordering.
    return {"items": rows, "total": len(rows)}


@router.post(
    "/{shop_id}/work-orders",
    status_code=201,
    summary="Create a work order",
    dependencies=[Depends(require_tier("shop"))],
)
def create_work_order_endpoint(
    shop_id: int,
    req: WorkOrderCreateRequest,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    require_shop_access(shop_id, user, db_path)
    wo_id = create_work_order(
        shop_id=shop_id, vehicle_id=req.vehicle_id,
        customer_id=req.customer_id, title=req.title,
        description=req.description, priority=req.priority,
        estimated_hours=req.estimated_hours,
        intake_visit_id=req.intake_visit_id,
        db_path=db_path,
    )
    return get_work_order(wo_id, db_path=db_path)


@router.get(
    "/{shop_id}/work-orders/{wo_id}",
    summary="Fetch a work order",
    dependencies=[Depends(require_tier("shop"))],
)
def get_work_order_endpoint(
    shop_id: int,
    wo_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    require_shop_access(shop_id, user, db_path)
    row = get_work_order(wo_id, db_path=db_path)
    if row is None or row.get("shop_id") != shop_id:
        raise HTTPException(
            status_code=404, detail=f"work order id={wo_id} not found",
        )
    return row


@router.post(
    "/{shop_id}/work-orders/{wo_id}/transition",
    summary="Transition a work order through its lifecycle",
    dependencies=[Depends(require_tier("shop"))],
)
def transition_work_order(
    shop_id: int,
    wo_id: int,
    req: WorkOrderTransitionRequest,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    require_shop_access(shop_id, user, db_path)
    wo = get_work_order(wo_id, db_path=db_path)
    if wo is None or wo.get("shop_id") != shop_id:
        raise HTTPException(
            status_code=404, detail=f"work order id={wo_id} not found",
        )
    action = req.action
    if action == "open":
        open_work_order(wo_id, db_path=db_path)
    elif action == "start":
        start_work(wo_id, db_path=db_path)
    elif action == "pause":
        pause_work(wo_id, reason=req.reason, db_path=db_path)
    elif action == "resume":
        resume_work(wo_id, db_path=db_path)
    elif action == "complete":
        complete_work_order(
            wo_id, actual_hours=req.actual_hours, db_path=db_path,
        )
    elif action == "cancel":
        cancel_work_order(
            wo_id, reason=req.reason or "customer-withdrew",
            db_path=db_path,
        )
    elif action == "reopen":
        reopen_work_order(wo_id, db_path=db_path)
    return get_work_order(wo_id, db_path=db_path)


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------


@router.get(
    "/{shop_id}/issues",
    summary="List issues at the shop",
    dependencies=[Depends(require_tier("shop"))],
)
def list_issues_endpoint(
    shop_id: int,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    require_shop_access(shop_id, user, db_path)
    rows = list_issues(
        shop_id=shop_id, status=status, severity=severity,
        limit=limit, db_path=db_path,
    )
    return {"items": rows, "total": len(rows)}


@router.post(
    "/{shop_id}/issues",
    status_code=201,
    summary="Log an issue against a work order",
    dependencies=[Depends(require_tier("shop"))],
)
def create_issue_endpoint(
    shop_id: int,
    req: IssueCreateRequest,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    require_shop_access(shop_id, user, db_path)
    issue_id = create_issue(
        work_order_id=req.work_order_id,
        title=req.title, description=req.description,
        category=req.category, severity=req.severity,
        reported_by_user_id=user.id, db_path=db_path,
    )
    from motodiag.shop import get_issue
    return get_issue(issue_id, db_path=db_path)


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------


@router.get(
    "/{shop_id}/invoices",
    summary="List invoices at the shop",
    dependencies=[Depends(require_tier("shop"))],
)
def list_invoices_endpoint(
    shop_id: int,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    require_shop_access(shop_id, user, db_path)
    rows = list_invoices_for_shop(
        shop_id=shop_id, status=status, limit=limit, db_path=db_path,
    )
    return {"items": rows, "total": len(rows)}


@router.post(
    "/{shop_id}/invoices/generate",
    status_code=201,
    summary="Generate an invoice from a completed work order",
    dependencies=[Depends(require_tier("shop"))],
)
def generate_invoice_endpoint(
    shop_id: int,
    req: InvoiceGenerateRequest,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    require_shop_access(shop_id, user, db_path)
    wo = get_work_order(req.work_order_id, db_path=db_path)
    if wo is None or wo.get("shop_id") != shop_id:
        raise HTTPException(
            status_code=404,
            detail=f"work order id={req.work_order_id} not found",
        )
    invoice_id = generate_invoice_for_wo(
        wo_id=req.work_order_id,
        tax_rate=req.tax_rate,
        shop_supplies_pct=req.shop_supplies_pct,
        shop_supplies_flat_cents=req.shop_supplies_flat_cents,
        diagnostic_fee_cents=req.diagnostic_fee_cents,
        labor_hourly_rate_cents=req.labor_hourly_rate_cents,
        notes=req.notes,
        db_path=db_path,
    )
    summary = get_invoice_with_items(invoice_id, db_path=db_path)
    return summary.model_dump() if summary else {"id": invoice_id}


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


@router.get(
    "/{shop_id}/notifications",
    summary="List customer notifications at the shop",
    dependencies=[Depends(require_tier("shop"))],
)
def list_notifications_endpoint(
    shop_id: int,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    require_shop_access(shop_id, user, db_path)
    rows = list_notifications(
        shop_id=shop_id, status=status, limit=limit, db_path=db_path,
    )
    return {"items": rows, "total": len(rows)}


@router.post(
    "/{shop_id}/notifications/trigger",
    status_code=201,
    summary="Render + queue a customer notification",
    dependencies=[Depends(require_tier("shop"))],
)
def trigger_notification_endpoint(
    shop_id: int,
    req: NotificationTriggerRequest,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    require_shop_access(shop_id, user, db_path)
    nid = trigger_notification(
        event=req.event, wo_id=req.wo_id, invoice_id=req.invoice_id,
        customer_id=req.customer_id, channel=req.channel,
        extra_context=req.extra_context,
        triggered_by_user_id=user.id, db_path=db_path,
    )
    from motodiag.shop import get_notification
    notif = get_notification(nid, db_path=db_path)
    return notif.model_dump() if notif else {"id": nid}


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


@router.get(
    "/{shop_id}/analytics/snapshot",
    summary="Dashboard snapshot (composes all Phase 171 rollups)",
    dependencies=[Depends(require_tier("shop"))],
)
def analytics_snapshot_endpoint(
    shop_id: int,
    since: str = "30d",
    utilization_days: int = Query(7, ge=1, le=60),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    require_shop_access(shop_id, user, db_path)
    snap = dashboard_snapshot(
        shop_id=shop_id, since=since,
        utilization_window_days=utilization_days,
        db_path=db_path,
    )
    return snap.model_dump()


@router.get(
    "/{shop_id}/analytics/revenue",
    summary="Revenue rollup by status",
    dependencies=[Depends(require_tier("shop"))],
)
def analytics_revenue_endpoint(
    shop_id: int,
    since: Optional[str] = None,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    require_shop_access(shop_id, user, db_path)
    rollup = revenue_rollup(
        shop_id=shop_id, since=since, db_path=db_path,
    )
    return rollup.model_dump()


@router.get(
    "/{shop_id}/analytics/top-issues",
    summary="Top issue categories this window",
    dependencies=[Depends(require_tier("shop"))],
)
def analytics_top_issues_endpoint(
    shop_id: int,
    since: str = "30d",
    limit: int = Query(10, ge=1, le=50),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    require_shop_access(shop_id, user, db_path)
    rows = top_issues(
        shop_id=shop_id, since=since, limit=limit, db_path=db_path,
    )
    return {
        "items": [r.model_dump() for r in rows],
        "total": len(rows),
    }
