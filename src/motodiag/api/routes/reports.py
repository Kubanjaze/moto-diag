"""PDF report endpoints (Phase 182, extended Phase 192B).

Six endpoints across three report kinds, each with a JSON preview
and a PDF download variant:

- ``GET /v1/reports/session/{id}`` / ``/pdf``
- ``GET /v1/reports/work-order/{id}`` / ``/pdf``
- ``GET /v1/reports/invoice/{id}`` / ``/pdf``

JSON-preview endpoints return the normalized ``ReportDocument``
dict. PDF endpoints stream ``application/pdf`` bytes with a
``Content-Disposition: attachment; filename=...`` header.

Phase 192B adds a sibling **POST** ``/v1/reports/session/{id}/pdf``
route for preset-filtered session PDFs (Customer hides Notes;
Insurance + Full hide nothing). The existing GET sibling stays
unchanged and continues to render the full document. The POST
body's ``preset`` field is required (FastAPI 422 if absent); the
``overrides`` field is reserved for future per-card UI (F28) and
not yet exposed in this phase.

Auth / scoping:

- **Session reports** — owner-only. Cross-user raises
  :class:`SessionOwnershipError` → 404.
- **Work-order + invoice reports** — shop-tier + membership via
  Phase 172 :func:`require_shop_access`. Cross-shop raises
  :class:`PermissionDenied` → 403.
"""

from __future__ import annotations

import logging
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field

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


def _pdf_response(
    doc: dict, filename: str, *, deterministic: bool = False,
) -> Response:
    """Render ``doc`` as a PDF response with the given filename.

    Phase 192B Commit 1.5 added the ``deterministic`` opt-in. POST
    routes (preset-filtered share-flow callers) pass ``True`` so
    two shares of the same session+preset hash identically.
    Existing GET routes keep the default ``False`` to preserve
    revision-tracking semantics.
    """
    renderer = get_renderer("pdf", deterministic=deterministic)
    body = renderer.render(doc)
    return Response(
        content=body,
        media_type=renderer.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# ---------------------------------------------------------------------------
# Phase 192B request models
# ---------------------------------------------------------------------------


class PdfRenderRequest(BaseModel):
    """Body for POST ``/v1/reports/session/{id}/pdf`` (Phase 192B).

    ``preset`` is required (FastAPI returns 422 if absent); the
    sibling GET route is kept for the unfiltered "full PDF" case.
    ``overrides`` is reserved for the future per-card-toggle UI
    (filed as F28 in mobile FOLLOWUPS) — accepted by the composer
    but NOT yet exposed by this route. Adding it to the schema now
    would build unused API surface; it'll land alongside the
    matching mobile UI when F28 ships.
    """

    preset: Literal["full", "customer", "insurance"] = Field(
        ...,
        description=(
            "Section-visibility preset. 'customer' hides "
            "diagnostic-internal sections (currently 'Notes'); "
            "'insurance' + 'full' hide nothing. Mirrors the "
            "mobile-side preset semantics in "
            "src/screens/reportPresets.ts exactly."
        ),
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
    summary="Download a diagnostic session report (PDF, full)",
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


@router.post(
    "/session/{session_id}/pdf",
    summary="Download a diagnostic session report (PDF, preset-filtered)",
    response_class=Response,
)
def post_session_report_pdf(
    session_id: int,
    body: PdfRenderRequest,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> Response:
    """Phase 192B: preset-filtered session PDF.

    Same auth posture as the GET sibling (owner-only with 404 for
    cross-owner). The composer applies the section-visibility
    filter BEFORE handing the document to the PDF renderer, so PDF
    output is exactly what the in-app viewer shows under the same
    preset (WYSIWYG mobile/PDF symmetry).
    """
    doc = build_session_report_doc(
        session_id, user.id, db_path=db_path, preset=body.preset,
    )
    return _pdf_response(
        doc, f"session-{session_id}.pdf", deterministic=True,
    )


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
