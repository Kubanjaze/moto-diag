"""Phase 200 — customer-facing report share links.

Four endpoints, three authed and one deliberately public:

- ``POST   /v1/reports/session/{session_id}/share``  mint a link
- ``GET    /v1/reports/session/{session_id}/shares`` list this user's links
- ``DELETE /v1/reports/shares/{share_id}``           revoke one
- ``GET    /v1/share/{token}``                       **PUBLIC** HTML page

The public route is the point of the phase: a bike owner has no account
and no API key, so the unguessable token in the path is the whole
authorization. Three things make that safe enough to ship, and all three
must stay true:

1. The token carries 256 bits of entropy and the route returns a generic
   404 for anything it does not recognise, so the space cannot be walked.
2. Links expire (30 days by default) and can be revoked immediately.
3. The route is NOT on the rate-limit exempt list — anonymous IP
   bucketing is the only abuse control a credential-free route gets, and
   removing it would be a silent regression. ``tests/test_phase200_share``
   pins that, plus the OpenAPI publicity contract.

The public route answers in HTML for every outcome, including failures.
Its consumer is a browser held by a customer, not a client library, so a
JSON problem-detail envelope would be the wrong answer to "this link
stopped working".
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from motodiag.api.deps import get_db_path
from motodiag.auth.deps import AuthedUser, get_current_user
from motodiag.core.config import get_settings
from motodiag.reporting.builders import build_session_report_doc
from motodiag.reporting.renderers import get_renderer
from motodiag.reporting.share_repo import (
    DEFAULT_SHARE_TTL_DAYS,
    create_share,
    list_shares_for_session,
    record_view,
    resolve_share,
    revoke_share,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["share"])

#: Every share renders the customer preset. The share route does NOT
#: accept a preset from the caller: "what a customer may see" is a
#: product decision that lives in the builder
#: (``_CUSTOMER_HIDDEN_HEADINGS``), not a per-request parameter that a
#: mechanic could widen by accident.
SHARE_PRESET = "customer"


class ShareCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ttl_days: int = Field(
        DEFAULT_SHARE_TTL_DAYS, ge=1, le=365,
        description="Link lifetime in days (1-365; default 30).",
    )


class ShareResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    token: str
    url: str
    session_id: int
    expires_at: str
    revoked_at: Optional[str] = None
    view_count: int = 0
    last_viewed_at: Optional[str] = None


def _share_url(request: Request, token: str) -> str:
    """Absolute URL for a token.

    Prefers the configured ``MOTODIAG_PUBLIC_BASE_URL``. The request's
    own base URL is the fallback — correct for dev and tailnet use,
    wrong behind a proxy that rewrites Host, which is exactly why the
    setting exists.
    """
    configured = (get_settings().public_base_url or "").rstrip("/")
    base = configured or str(request.base_url).rstrip("/")
    return f"{base}/v1/share/{token}"


def _to_response(request: Request, share: dict) -> ShareResponse:
    return ShareResponse(
        id=int(share["id"]),
        token=str(share["token"]),
        url=_share_url(request, str(share["token"])),
        session_id=int(share["session_id"]),
        expires_at=str(share["expires_at"]),
        revoked_at=share.get("revoked_at"),
        view_count=int(share.get("view_count") or 0),
        last_viewed_at=share.get("last_viewed_at"),
    )


# ---------------------------------------------------------------------------
# Authed: mint / list / revoke
# ---------------------------------------------------------------------------


@router.post(
    "/reports/session/{session_id}/share",
    response_model=ShareResponse,
    status_code=201,
    summary="Mint a customer share link for a session report",
)
def create_session_share(
    session_id: int,
    req: ShareCreateRequest,
    request: Request,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> ShareResponse:
    # Build the document FIRST. It is owner-scoped, so this both proves
    # the caller may read the session (SessionOwnershipError -> 404) and
    # proves the page will actually render — you cannot mint a link to a
    # report that would 500 when a customer opens it.
    build_session_report_doc(
        session_id, user.id, db_path=db_path, preset=SHARE_PRESET,
    )
    share = create_share(
        session_id=session_id,
        created_by_user_id=user.id,
        preset=SHARE_PRESET,
        ttl_days=req.ttl_days,
        db_path=db_path,
    )
    logger.info(
        "minted share id=%s for session=%s by user=%s (ttl=%sd)",
        share["id"], session_id, user.id, req.ttl_days,
    )
    return _to_response(request, share)


@router.get(
    "/reports/session/{session_id}/shares",
    response_model=list[ShareResponse],
    summary="List the share links you minted for a session",
)
def list_session_shares(
    session_id: int,
    request: Request,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> list[ShareResponse]:
    # Ownership check via the same owner-scoped builder used at mint.
    build_session_report_doc(
        session_id, user.id, db_path=db_path, preset=SHARE_PRESET,
    )
    return [
        _to_response(request, share)
        for share in list_shares_for_session(
            session_id, user.id, db_path=db_path,
        )
    ]


@router.delete(
    "/reports/shares/{share_id}",
    summary="Revoke a share link immediately",
)
def revoke_session_share(
    share_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict[str, Any]:
    revoked = revoke_share(share_id, user.id, db_path=db_path)
    return {"revoked": revoked}


# ---------------------------------------------------------------------------
# Public: the customer's page
# ---------------------------------------------------------------------------


_MESSAGE_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{title}</title>
<style>
:root {{ color-scheme: light dark; }}
body {{ margin:0; min-height:100vh; display:flex; align-items:center;
 justify-content:center; padding:32px;
 font:16px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
 Helvetica, Arial, sans-serif; color:#16181d; background:#f7f8fa; }}
div {{ max-width:26rem; text-align:center; }}
h1 {{ font-size:1.25rem; margin:0 0 10px; }}
p {{ margin:0; color:#4a5160; }}
@media (prefers-color-scheme: dark) {{
 body {{ color:#e6e8ec; background:#14161a; }} p {{ color:#a9b1bf; }} }}
</style></head>
<body><div><h1>{title}</h1><p>{body}</p></div></body></html>
"""


def _message_response(
    status_code: int, title: str, body: str,
) -> Response:
    return Response(
        content=_MESSAGE_PAGE.format(title=title, body=body),
        media_type="text/html; charset=utf-8",
        status_code=status_code,
    )


@router.get(
    "/share/{token}",
    response_class=Response,
    summary="View a shared diagnostic report (public, no account needed)",
    responses={
        200: {"content": {"text/html": {}},
              "description": "The customer-preset report as a web page."},
        404: {"content": {"text/html": {}},
              "description": "Unknown link. Generic by design."},
        410: {"content": {"text/html": {}},
              "description": "The link expired or was revoked."},
    },
)
def view_shared_report(
    token: str,
    db_path: str = Depends(get_db_path),
) -> Response:
    status, share = resolve_share(token, db_path=db_path)

    if status == "missing":
        return _message_response(
            404, "Link not found",
            "This link doesn&#39;t match any report. Check that you "
            "copied all of it, or ask your shop to send a new one.",
        )
    if status in ("expired", "revoked"):
        return _message_response(
            410, "Link no longer active",
            "This report link has expired or was turned off by the "
            "shop. Ask them for a fresh link and they can send one in "
            "a moment.",
        )

    assert share is not None  # status == "ok"
    try:
        doc = build_session_report_doc(
            int(share["session_id"]),
            int(share["created_by_user_id"]),
            db_path=db_path,
            preset=str(share.get("preset") or SHARE_PRESET),
        )
    except Exception:
        # The session was deleted, or its owner lost access, after the
        # link was minted. Say "no longer available" rather than leaking
        # which of those happened.
        logger.exception(
            "share id=%s failed to build its document", share.get("id"),
        )
        return _message_response(
            410, "Report no longer available",
            "This report can&#39;t be shown any more. Please ask your "
            "shop for an up-to-date copy.",
        )

    html_bytes = get_renderer("html").render(doc)
    try:
        record_view(int(share["id"]), db_path=db_path)
    except Exception:  # noqa: BLE001 — a view counter never blocks a page
        logger.warning("failed to record view for share id=%s", share.get("id"))
    return Response(
        content=html_bytes,
        media_type="text/html; charset=utf-8",
        headers={
            # Private document behind a capability URL: no shared cache
            # should keep a copy, and no crawler should index it.
            "Cache-Control": "private, no-store",
            "X-Robots-Tag": "noindex, nofollow",
            "Referrer-Policy": "no-referrer",
        },
    )
