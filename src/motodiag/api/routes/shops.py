"""Shop smoke route — GET /v1/shops/{id} (Phase 175).

Proves the full dependency-injection chain works end-to-end. Phase
180 replaced it for the app with ``/v1/shop/profile/{id}``.

Phase 409 prebuild: the route answered anyone, with the whole shop row
(address, phone, email, tax id), to any id. It now needs a signed-in
active member of that shop: anyone else is 401 or 403, and a shop that
does not exist is 403 too, so ids cannot be walked.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from motodiag.api.deps import get_db_path
from motodiag.auth.deps import AuthedUser, get_current_user
from motodiag.shop.rbac import PermissionDenied, get_shop_member
from motodiag.shop.shop_repo import ShopNotFoundError, get_shop

router = APIRouter(tags=["shops"])


@router.get(
    "/shops/{shop_id}",
    summary="Fetch a shop profile by id (members only)",
)
def get_shop_endpoint(
    shop_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    """Return the shop row to an active member, else 403; 404 via
    :class:`ShopNotFoundError` only if a member's shop is gone."""
    member = get_shop_member(shop_id=shop_id, user_id=user.id, db_path=db_path)
    if member is None or not member.is_active:
        raise PermissionDenied(
            f"user id={user.id} is not an active member of shop id={shop_id}"
        )
    row = get_shop(shop_id, db_path=db_path)
    if row is None:
        raise ShopNotFoundError(f"shop not found: id={shop_id}")
    return row
