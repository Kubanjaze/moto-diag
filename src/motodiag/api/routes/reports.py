"""PDF report endpoints (Phase 182).

Six endpoints across three report kinds, each with a JSON preview
and a PDF download variant:

- ``GET /v1/reports/session/{id}`` / ``/pdf``
- ``GET /v1/reports/work-order/{id}`` / ``/pdf``
- ``GET /v1/reports/invoice/{id}`` / ``/pdf``

JSON-preview endpoints return the normalized ``ReportDocument``
dict. PDF endpoints stream ``application/pdf`` bytes with a
``Content-Disposition: attachment; filename=...`` header.

Auth / scoping:

- **Session reports** — owner-only. Cross-user raises
  :class:`SessionOwnershipError` → 404.
- **Work-order + invoice reports** — shop-tier + membership via
  Phase 172 :func:`require_shop_access`. Cross-shop raises
  :class:`PermissionDenied` → 403.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Response

from motodiag.api.deps import get_db_path
from motodiag.auth.deps import AuthedUser, get_current_user, require_tier
from motodiag.reporting import (
    build_invoice_report_doc,
    build_session_report_doc,
    build_work_order_report_doc,
    get_renderer,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pdf_response(doc: dict, filename: str) -> Response:
    renderer = get_renderer("pdf")
    body = renderer.render(doc)
    return Response(
        content=body,
        media_type=renderer.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# ---------------------------------------------------------------------------
# Session reports (owner-only)
# ---------------------------------------------------------------------------


@router.get(
    "/session/{session_id}",
    summary="Preview a diagnostic session report (JSON)",
)
def get_session_report(
    session_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict[str, Any]:
    return build_session_report_doc(
        session_id, user.id, db_path=db_path,
    )


@router.get(
    "/session/{session_id}/pdf",
    summary="Download a diagnostic session report (PDF)",
    response_class=Response,
)
def get_session_report_pdf(
    session_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> Response:
    doc = build_session_report_doc(
        session_id, user.id, db_path=db_path,
    )
    return _pdf_response(doc, f"session-{session_id}.pdf")


# ---------------------------------------------------------------------------
# Work-order reports (shop-tier + membership)
# ---------------------------------------------------------------------------


@router.get(
    "/work-order/{wo_id}",
    summary="Preview a work-order report (JSON)",
)
def get_work_order_report(
    wo_id: int,
    user: AuthedUser = Depends(require_tier("shop")),
    db_path: str = Depends(get_db_path),
) -> dict[str, Any]:
    return build_work_order_report_doc(
        wo_id, user.id, db_path=db_path,
    )


@router.get(
    "/work-order/{wo_id}/pdf",
    summary="Download a work-order report (PDF)",
    response_class=Response,
)
def get_work_order_report_pdf(
    wo_id: int,
    user: AuthedUser = Depends(require_tier("shop")),
    db_path: str = Depends(get_db_path),
) -> Response:
    doc = build_work_order_report_doc(
        wo_id, user.id, db_path=db_path,
    )
    return _pdf_response(doc, f"work-order-{wo_id}.pdf")


# ---------------------------------------------------------------------------
# Invoice reports (shop-tier + membership)
# ---------------------------------------------------------------------------


@router.get(
    "/invoice/{invoice_id}",
    summary="Preview an invoice report (JSON)",
)
def get_invoice_report(
    invoice_id: int,
    user: AuthedUser = Depends(require_tier("shop")),
    db_path: str = Depends(get_db_path),
) -> dict[str, Any]:
    return build_invoice_report_doc(
        invoice_id, user.id, db_path=db_path,
    )


@router.get(
    "/invoice/{invoice_id}/pdf",
    summary="Download an invoice report (PDF)",
    response_class=Response,
)
def get_invoice_report_pdf(
    invoice_id: int,
    user: AuthedUser = Depends(require_tier("shop")),
    db_path: str = Depends(get_db_path),
) -> Response:
    doc = build_invoice_report_doc(
        invoice_id, user.id, db_path=db_path,
    )
    return _pdf_response(doc, f"invoice-{invoice_id}.pdf")
