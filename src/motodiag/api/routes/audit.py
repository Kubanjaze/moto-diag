"""A shop's audit trail over HTTP (Phase 348).

``GET /v1/shop/{shop_id}/audit``: the shop's own events, newest first, for
a member who holds ``manage_users`` at that shop (the operator's choice;
the seeded roles give it to the owner only). The hashes are not here: the
chain is checked by the operator's ``motodiag audit verify``.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from motodiag.api.deps import get_db_path
from motodiag.audit import list_events
from motodiag.auth.deps import AuthedUser, require_tier
from motodiag.core.database import get_connection
from motodiag.shop.rbac import require_shop_permission

router = APIRouter(prefix="/shop", tags=["audit"])


def _item(row: dict) -> dict:
    return {
        "id": row["id"],
        "occurred_at": row["occurred_at"],
        "actor": {
            "user_id": row["actor_user_id"],
            "username": row["actor_username"],
            "credential_kind": row["credential_kind"],
        },
        "method": row["method"],
        "path": row["path"],
        "endpoint": row["endpoint"],
        "status": row["status"],
        "request_id": row["request_id"],
    }


@router.get("/{shop_id}/audit", summary="A shop's audit trail, newest first")
def shop_audit(
    shop_id: int,
    since: Optional[str] = None,
    until: Optional[str] = None,
    user_id: Optional[int] = None,
    limit: int = Query(100, ge=1, le=500),
    before_id: Optional[int] = None,
    user: AuthedUser = Depends(require_tier("shop")),
    db_path: str = Depends(get_db_path),
) -> dict:
    """Pass the last item's id as ``before_id`` for the next page;
    ``next_before_id`` is null on the last page."""
    require_shop_permission(shop_id, user.id, "manage_users", db_path=db_path)
    with get_connection(db_path) as conn:
        rows = list_events(
            conn, shop_id=shop_id, user_id=user_id, since=since, until=until,
            limit=limit, before_id=before_id,
        )
    items = [_item(r) for r in rows]
    return {
        "items": items,
        "next_before_id": items[-1]["id"] if len(items) == limit else None,
    }
