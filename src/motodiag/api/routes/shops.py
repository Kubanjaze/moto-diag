"""Shop smoke route — GET /v1/shops/{id} (Phase 175).

Proves the full dependency-injection chain works end-to-end. Phase
180 will replace this with a full shop CRUD router composing against
the same pattern (Depends(get_db_path) → Phase 160 repo → JSON).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from motodiag.api.deps import get_db_path
from motodiag.shop.shop_repo import ShopNotFoundError, get_shop


router = APIRouter(tags=["shops"])


@router.get(
    "/shops/{shop_id}",
    summary="Fetch a shop profile by id",
)
def get_shop_endpoint(
    shop_id: int,
    db_path: str = Depends(get_db_path),
) -> dict:
    """Return the shop row, or 404 via
    :class:`ShopNotFoundError` (mapped by the global exception
    handler to an RFC 7807 ProblemDetail)."""
    row = get_shop(shop_id, db_path=db_path)
    if row is None:
        raise ShopNotFoundError(f"shop not found: id={shop_id}")
    return row
