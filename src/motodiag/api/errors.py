"""RFC 7807 problem-detail error handling (Phase 175).

Maps Track A-G domain exceptions onto uniform JSON responses. Route
handlers raise the domain exception as-is; the registered handlers
translate to the right HTTP status + ``ProblemDetail`` body.

Adding a new Track's exceptions: extend :data:`EXCEPTION_STATUS_MAP`
with the exception class → (http_status, type_uri, title) tuple.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict


logger = logging.getLogger(__name__)


class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details for HTTP APIs.

    https://www.rfc-editor.org/rfc/rfc7807
    """

    model_config = ConfigDict(extra="ignore")

    type: str = "about:blank"
    title: str
    status: int
    detail: Optional[str] = None
    request_id: Optional[str] = None
    instance: Optional[str] = None


_TYPE_PREFIX = "https://motodiag.dev/problems/"


def _type_uri(slug: str) -> str:
    return f"{_TYPE_PREFIX}{slug}"


def _exc_class_chain():
    """Resolve exception classes lazily so the module imports fast.

    Phase 175 is Track H's entry point; importing Track G modules
    eagerly at FastAPI boot isn't ideal. Lazy resolution keeps
    ``from motodiag.api import create_app`` fast.
    """
    from motodiag.shop.bay_scheduler import (
        BayNotFoundError, InvalidSlotTransition, SlotNotFoundError,
        SlotOverlapError,
    )
    from motodiag.shop.invoicing import (
        InvoiceGenerationError, InvoiceNotFoundError,
    )
    from motodiag.shop.issue_repo import (
        InvalidIssueTransition, IssueFKError, IssueNotFoundError,
    )
    from motodiag.shop.notifications import (
        InvalidNotificationTransition, NotificationContextError,
        NotificationNotFoundError,
    )
    from motodiag.shop.parts_needs import (
        InvalidPartNeedTransition, PartNotInCatalogError,
        WorkOrderPartNotFoundError,
    )
    from motodiag.shop.rbac import (
        InvalidRoleError, MechanicNotInShopError, PermissionDenied,
        ShopMembershipNotFoundError,
    )
    from motodiag.shop.shop_repo import (
        ShopNameExistsError, ShopNotFoundError,
    )
    from motodiag.shop.intake_repo import (
        IntakeAlreadyClosedError, IntakeNotFoundError,
    )
    from motodiag.shop.work_order_repo import (
        InvalidWorkOrderTransition, WorkOrderFKError,
        WorkOrderNotFoundError,
    )
    from motodiag.shop.workflow_actions import InvalidActionError
    from motodiag.shop.workflow_conditions import InvalidConditionError
    from motodiag.shop.workflow_rules import (
        DuplicateRuleNameError, InvalidEventError, RuleNotFoundError,
    )

    # tuple of (exception_class, http_status, slug, title)
    return [
        # 404 — not found
        (ShopNotFoundError, 404, "shop-not-found", "Shop not found"),
        (IntakeNotFoundError, 404, "intake-not-found",
         "Intake visit not found"),
        (WorkOrderNotFoundError, 404, "work-order-not-found",
         "Work order not found"),
        (IssueNotFoundError, 404, "issue-not-found", "Issue not found"),
        (WorkOrderPartNotFoundError, 404, "work-order-part-not-found",
         "Work-order parts line not found"),
        (PartNotInCatalogError, 404, "part-not-in-catalog",
         "Part not in catalog"),
        (BayNotFoundError, 404, "bay-not-found", "Bay not found"),
        (SlotNotFoundError, 404, "slot-not-found", "Slot not found"),
        (InvoiceNotFoundError, 404, "invoice-not-found",
         "Invoice not found"),
        (NotificationNotFoundError, 404, "notification-not-found",
         "Notification not found"),
        (ShopMembershipNotFoundError, 404, "membership-not-found",
         "Shop membership not found"),
        (RuleNotFoundError, 404, "rule-not-found", "Rule not found"),
        # 403 — permission
        (PermissionDenied, 403, "permission-denied", "Permission denied"),
        # 409 — state conflict (lifecycle + uniqueness)
        (InvalidWorkOrderTransition, 409, "invalid-transition",
         "Invalid work-order state transition"),
        (InvalidIssueTransition, 409, "invalid-transition",
         "Invalid issue state transition"),
        (InvalidSlotTransition, 409, "invalid-transition",
         "Invalid bay-slot state transition"),
        (InvalidNotificationTransition, 409, "invalid-transition",
         "Invalid notification state transition"),
        (InvalidPartNeedTransition, 409, "invalid-transition",
         "Invalid parts-needs state transition"),
        (IntakeAlreadyClosedError, 409, "intake-already-closed",
         "Intake already closed"),
        (SlotOverlapError, 409, "slot-overlap", "Slot overlap detected"),
        (ShopNameExistsError, 409, "shop-name-exists",
         "Shop name already exists"),
        (DuplicateRuleNameError, 409, "duplicate-rule-name",
         "Rule name already used in shop"),
        # 422 — business-rule unprocessable
        (InvoiceGenerationError, 422, "invoice-generation-failed",
         "Invoice cannot be generated"),
        (MechanicNotInShopError, 422, "mechanic-not-in-shop",
         "Mechanic is not an active member of this shop"),
        (NotificationContextError, 422, "notification-context",
         "Notification template context incomplete"),
        (IssueFKError, 422, "issue-fk", "Issue foreign-key violation"),
        (WorkOrderFKError, 422, "work-order-fk",
         "Work-order foreign-key violation"),
        # 400 — input validation
        (InvalidRoleError, 400, "invalid-role", "Invalid role"),
        (InvalidEventError, 400, "unknown-event", "Unknown event"),
        (InvalidConditionError, 400, "invalid-condition",
         "Invalid rule condition"),
        (InvalidActionError, 400, "invalid-action",
         "Invalid rule action"),
    ]


def _problem_response(
    request: Request, status: int, type_slug: str,
    title: str, detail: Optional[str] = None,
) -> JSONResponse:
    rid = getattr(request.state, "request_id", None)
    body = ProblemDetail(
        type=_type_uri(type_slug),
        title=title,
        status=status,
        detail=detail,
        request_id=rid,
        instance=str(request.url.path),
    ).model_dump(exclude_none=True)
    headers = {}
    if rid:
        headers["X-Request-ID"] = rid
    return JSONResponse(
        status_code=status, content=body, headers=headers,
    )


def _make_handler(status: int, slug: str, title: str):
    async def handler(request: Request, exc: Exception):
        return _problem_response(
            request, status=status, type_slug=slug, title=title,
            detail=str(exc) if str(exc) else None,
        )
    return handler


async def _value_error_handler(request: Request, exc: Exception):
    """Catchall for ValueError subclasses not otherwise mapped."""
    return _problem_response(
        request, status=400, type_slug="validation-error",
        title="Validation error",
        detail=str(exc) if str(exc) else None,
    )


async def _unhandled_handler(request: Request, exc: Exception):
    """Last-resort handler. Logs the stack trace; returns a safe
    500 body (no server internals exposed to clients)."""
    rid = getattr(request.state, "request_id", None)
    logger.exception(
        "unhandled exception in %s %s (request_id=%s): %s",
        request.method, request.url.path, rid, exc,
    )
    return _problem_response(
        request, status=500, type_slug="internal-error",
        title="Internal server error",
        detail=None,  # do NOT leak str(exc) on 500 path
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Wire domain exceptions onto :data:`app` as RFC 7807 responses.

    Order matters: register most general first (``ValueError``) then
    specific subclasses, so FastAPI resolves to the most-specific
    match. The unhandled-``Exception`` handler goes last so anything
    not already caught becomes a safe 500.
    """
    app.add_exception_handler(ValueError, _value_error_handler)
    for exc_cls, status, slug, title in _exc_class_chain():
        app.add_exception_handler(
            exc_cls, _make_handler(status, slug, title),
        )
    app.add_exception_handler(Exception, _unhandled_handler)
