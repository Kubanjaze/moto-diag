"""Phase 194 (Commit 0) — work-order photo upload + CRUD endpoints.

Six endpoints, fully nested under
``/v1/shop/{shop_id}/work-orders/{wo_id}/photos`` per the
Phase 193 shop-management routing pattern.

Auth posture (per Phase 194 v1.0 plan Section B):
  POST   /v1/shop/{shop_id}/work-orders/{wo_id}/photos              require_tier('shop')
  GET    /v1/shop/{shop_id}/work-orders/{wo_id}/photos              require_tier('shop')
  GET    /v1/shop/{shop_id}/work-orders/{wo_id}/photos/{photo_id}   require_tier('shop')
  PATCH  /v1/shop/{shop_id}/work-orders/{wo_id}/photos/{photo_id}   require_tier('shop')
  DELETE /v1/shop/{shop_id}/work-orders/{wo_id}/photos/{photo_id}   require_tier('shop')
  GET    /v1/shop/{shop_id}/work-orders/{wo_id}/photos/{photo_id}/file
                                                                    require_tier('shop')

All endpoints layer ``require_shop_access`` (basic shop-membership check)
on top of the tier gate, mirroring Phase 193's transition + assign
endpoints. Cross-shop attempts return 403 (not 404) because shops are
global-registry entities — the honest response when a user isn't a
member of a named shop is "forbidden", not "doesn't exist". WO 404s
when the WO id exists but doesn't belong to the URL shop_id.

Quotas (per Section A + plan Risks):
  Per-WO count cap:    30 photos
  Per-issue count cap: 10 photos (when issue_id is set)
  Per-tier monthly aggregate (per uploader):
    individual: 0  (require_tier already 402s; defense-in-depth)
    shop:       500 / month
    company:    unlimited

Storage (per Section K + plan Logic):
  ``{settings.data_dir}/photos/shop_{shop_id}/work_order_{wo_id}/{photo_id}.jpg``

Image pipeline (per Section K, photo_pipeline.normalize_photo):
  decode (HEIC via pillow-heif when registered) → exif_transpose to
  upright pixels → strip EXIF → resize to 2048px long-edge bound →
  JPEG quality 85. Synchronous in-handler; sub-second for typical
  mobile camera output (4032×3024 HEIC ~3MB → 2048×1536 JPEG ~400KB).
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Literal, Optional

from fastapi import (
    APIRouter, Depends, File, Form, HTTPException,
    Path as PathParam, UploadFile, status,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from motodiag.api.deps import get_db_path, get_settings as get_api_settings
from motodiag.api.routes.shop_mgmt import require_shop_access
from motodiag.auth.deps import (
    AuthedUser, get_current_user, require_tier,
)
from motodiag.core.config import Settings
from motodiag.media.photo_pipeline import normalize_photo
from motodiag.shop import get_work_order
from motodiag.shop.wo_photo_repo import (
    WorkOrderPhotoOwnershipError,
    WorkOrderPhotoPairingError,
    WorkOrderPhotoQuotaExceededError,
    _update_file_path,
    count_issue_photos,
    count_wo_photos,
    count_wo_photos_this_month_for_uploader,
    create_wo_photo,
    get_wo_photo,
    get_wo_photo_for_pairing,
    list_wo_photos,
    soft_delete_wo_photo,
    update_pairing,
)


_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Quota constants (per Phase 194 v1.0 plan Risks; revisit after smoke gate)
# ---------------------------------------------------------------------------


PER_WO_COUNT_CAP = 30
PER_ISSUE_COUNT_CAP = 10
TIER_MONTHLY_PHOTO_LIMITS: dict[str, Optional[int]] = {
    "individual": 0,
    "shop": 500,
    "company": None,  # unlimited
}


PhotoRole = Literal["before", "after", "general", "undecided"]


# ---------------------------------------------------------------------------
# Wire shapes (Pydantic models for request body + response)
# ---------------------------------------------------------------------------


class PhotoUploadMetadata(BaseModel):
    """JSON body field accompanying the multipart upload.

    Mirrors Phase 191B's ``VideoBase`` shape — metadata travels
    alongside the file in the multipart payload. ``captured_at`` is
    the mobile-side capture timestamp (server time can differ from
    device time; preserving the device clock for forensics).
    """
    model_config = ConfigDict(extra="ignore")

    captured_at: str = Field(..., description="ISO 8601 capture time (mobile clock)")
    role: PhotoRole = Field("general", description="Photo classification at capture")
    issue_id: Optional[int] = Field(None, ge=1, description="Optional issue attribution")
    pair_id: Optional[int] = Field(None, ge=1, description="Optional sibling photo for before/after pairing")


class PhotoPatchRequest(BaseModel):
    """PATCH body for post-capture re-classification + pairing updates."""
    model_config = ConfigDict(extra="ignore")

    role: Optional[PhotoRole] = None
    pair_id: Optional[int] = Field(None, ge=1)
    issue_id: Optional[int] = Field(None, ge=1)


class WorkOrderPhotoResponse(BaseModel):
    """Wire response — internal storage details (sha256, file_path) omitted."""
    model_config = ConfigDict(extra="ignore")

    id: int
    work_order_id: int
    issue_id: Optional[int]
    role: PhotoRole
    pair_id: Optional[int]
    width: int
    height: int
    file_size_bytes: int
    captured_at: str
    uploaded_by_user_id: int
    analysis_state: Optional[str]
    analysis_findings: Optional[dict]
    source: Optional[str]
    created_at: str


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


router = APIRouter(prefix="/shop", tags=["work-order-photos"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _resolve_storage_dir(
    settings: Settings, shop_id: int, wo_id: int,
) -> Path:
    """Build (and create) the canonical storage directory for a photo.

    Layout per Section K + Logic:
    ``{data_dir}/photos/shop_{shop_id}/work_order_{wo_id}/``.
    """
    base = (
        Path(settings.data_dir)
        / "photos"
        / f"shop_{shop_id}"
        / f"work_order_{wo_id}"
    )
    base.mkdir(parents=True, exist_ok=True)
    return base


def _enforce_quotas(
    *,
    work_order_id: int,
    issue_id: Optional[int],
    user_tier: Optional[str],
    user_id: int,
    db_path: str,
) -> None:
    """Raise ``WorkOrderPhotoQuotaExceededError`` on any quota violation.

    Three checks:
    1. Per-WO count cap (30).
    2. Per-issue count cap (10) — only when ``issue_id`` is provided.
    3. Per-tier monthly aggregate per uploader.

    Order matters: per-WO is the most specific limit so it surfaces
    first; per-issue is conditional; monthly is the broadest and
    fires last. The route layer translates this exception to 402.
    """
    current_wo = count_wo_photos(work_order_id, db_path=db_path)
    if current_wo >= PER_WO_COUNT_CAP:
        raise WorkOrderPhotoQuotaExceededError(
            current=current_wo, limit=PER_WO_COUNT_CAP, scope="wo",
        )
    if issue_id is not None:
        current_issue = count_issue_photos(issue_id, db_path=db_path)
        if current_issue >= PER_ISSUE_COUNT_CAP:
            raise WorkOrderPhotoQuotaExceededError(
                current=current_issue,
                limit=PER_ISSUE_COUNT_CAP,
                scope="issue",
            )
    effective_tier = user_tier or "individual"
    cap = TIER_MONTHLY_PHOTO_LIMITS.get(effective_tier)
    if cap is None:
        return  # company tier — unlimited
    used = count_wo_photos_this_month_for_uploader(
        user_id, db_path=db_path,
    )
    if used >= cap:
        raise WorkOrderPhotoQuotaExceededError(
            current=used, limit=cap, scope="monthly",
        )


def _verify_wo_in_shop(shop_id: int, wo_id: int, db_path: str) -> dict:
    """Fetch the WO row IFF it belongs to ``shop_id``; else 404.

    Returns the WO dict on success. Mirrors the pattern used by
    Phase 193's transition + assign endpoints — cross-shop WO ids
    surface as 404 (the WO is "not found" from this shop's
    perspective; ``require_shop_access`` already handled the
    cross-shop membership check).
    """
    wo = get_work_order(wo_id, db_path=db_path)
    if wo is None or wo.get("shop_id") != shop_id:
        raise HTTPException(
            status_code=404, detail=f"work order id={wo_id} not found",
        )
    return wo


def _row_to_response(row: dict) -> WorkOrderPhotoResponse:
    """Convert a wo_photo_repo row dict to a wire response."""
    return WorkOrderPhotoResponse(
        id=int(row["id"]),
        work_order_id=int(row["work_order_id"]),
        issue_id=(
            int(row["issue_id"]) if row.get("issue_id") is not None else None
        ),
        role=row["role"],
        pair_id=(
            int(row["pair_id"]) if row.get("pair_id") is not None else None
        ),
        width=int(row["width"]),
        height=int(row["height"]),
        file_size_bytes=int(row["file_size_bytes"]),
        captured_at=str(row["captured_at"]),
        uploaded_by_user_id=int(row["uploaded_by_user_id"]),
        analysis_state=row.get("analysis_state"),
        analysis_findings=row.get("analysis_findings"),
        source=row.get("source"),
        created_at=str(row.get("created_at") or ""),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{shop_id}/work-orders/{wo_id}/photos",
    response_model=WorkOrderPhotoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a photo to a work order (and optionally an issue)",
)
async def upload_wo_photo(
    shop_id: int = PathParam(..., gt=0),
    wo_id: int = PathParam(..., gt=0),
    file: UploadFile = File(...),
    metadata: str = Form(...),
    user: AuthedUser = Depends(require_tier("shop")),
    db_path: str = Depends(get_db_path),
    settings: Settings = Depends(get_api_settings),
) -> WorkOrderPhotoResponse:
    """Multipart upload: ``file`` (image bytes) + ``metadata`` (JSON).

    Pipeline (per Section K):
    1. Validate WO + shop scope (403/404).
    2. Parse + validate metadata JSON (422 on shape error).
    3. Read multipart payload.
    4. Enforce quotas BEFORE running the pipeline (avoid wasted CPU
       on quota-exceeded calls).
    5. Run ``photo_pipeline.normalize_photo`` — surfaces decode errors
       as 422 and unsupported-format (HEIC without pillow-heif) as 415.
    6. Validate ``pair_id`` if present (must reference a live photo on
       the same WO; 422 otherwise).
    7. Insert DB row with placeholder file_path; resolve canonical disk
       path; write JPEG bytes; update DB row with the real path.
    8. Return 201 with the freshly-written row.
    """
    require_shop_access(shop_id, user, db_path)
    _verify_wo_in_shop(shop_id, wo_id, db_path)

    try:
        meta = PhotoUploadMetadata.model_validate_json(metadata)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    raw_bytes = await file.read()
    incoming_size = len(raw_bytes)
    sha256 = _hash_bytes(raw_bytes)

    _enforce_quotas(
        work_order_id=wo_id,
        issue_id=meta.issue_id,
        user_tier=user.tier,
        user_id=user.id,
        db_path=db_path,
    )

    # Normalization runs synchronously (sub-second for typical mobile
    # camera output). Decode/format errors propagate as typed exceptions
    # mapped by api/errors.py to 415/422.
    normalized = normalize_photo(raw_bytes)

    # Validate pair_id (if any) targets a live photo on the same WO.
    if meta.pair_id is not None:
        partner = get_wo_photo_for_pairing(
            meta.pair_id, expected_wo_id=wo_id, db_path=db_path,
        )
        if partner is None:
            raise WorkOrderPhotoPairingError(
                f"pair_id={meta.pair_id} does not reference a live "
                f"photo on work_order_id={wo_id}"
            )

    # Insert with placeholder path; resolve real path post-INSERT.
    photo_id = create_wo_photo(
        work_order_id=wo_id,
        file_path="",
        file_size_bytes=len(normalized.jpeg_bytes),
        width=normalized.width,
        height=normalized.height,
        sha256=sha256,
        captured_at=meta.captured_at,
        uploaded_by_user_id=user.id,
        role=meta.role,
        issue_id=meta.issue_id,
        pair_id=meta.pair_id,
        db_path=db_path,
    )

    storage_dir = _resolve_storage_dir(settings, shop_id, wo_id)
    file_path = storage_dir / f"{photo_id}.jpg"
    file_path.write_bytes(normalized.jpeg_bytes)
    _update_file_path(photo_id, str(file_path), db_path=db_path)

    # If pair_id was specified, mirror the pairing on the partner so
    # both sides reference each other (symmetric pair). Roles are
    # asymmetric (one side 'before', other 'after'); pair_id is
    # symmetric. Caller specifies the pair_id from the new photo's
    # perspective; we update the partner to point back at the new id.
    if meta.pair_id is not None:
        update_pairing(meta.pair_id, pair_id=photo_id, db_path=db_path)

    row = get_wo_photo(photo_id, db_path=db_path)
    if row is None:
        # Should never happen — we just inserted + updated.
        raise WorkOrderPhotoOwnershipError(
            f"photo id={photo_id} not found after insert"
        )
    # Ignore unused-incoming-size (kept for SHA-collision logging hooks
    # in a future telemetry phase).
    _ = incoming_size
    return _row_to_response(row)


@router.get(
    "/{shop_id}/work-orders/{wo_id}/photos",
    response_model=list[WorkOrderPhotoResponse],
    summary="List photos attached to a work order",
)
async def list_wo_photos_endpoint(
    shop_id: int = PathParam(..., gt=0),
    wo_id: int = PathParam(..., gt=0),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> list[WorkOrderPhotoResponse]:
    require_shop_access(shop_id, user, db_path)
    _verify_wo_in_shop(shop_id, wo_id, db_path)
    rows = list_wo_photos(wo_id, db_path=db_path)
    return [_row_to_response(r) for r in rows]


@router.get(
    "/{shop_id}/work-orders/{wo_id}/photos/{photo_id}",
    response_model=WorkOrderPhotoResponse,
    summary="Get one photo by id",
)
async def get_wo_photo_endpoint(
    shop_id: int = PathParam(..., gt=0),
    wo_id: int = PathParam(..., gt=0),
    photo_id: int = PathParam(..., gt=0),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> WorkOrderPhotoResponse:
    require_shop_access(shop_id, user, db_path)
    _verify_wo_in_shop(shop_id, wo_id, db_path)
    row = get_wo_photo(photo_id, db_path=db_path)
    if row is None or int(row["work_order_id"]) != wo_id:
        raise WorkOrderPhotoOwnershipError(
            f"photo id={photo_id} not found"
        )
    return _row_to_response(row)


@router.patch(
    "/{shop_id}/work-orders/{wo_id}/photos/{photo_id}",
    response_model=WorkOrderPhotoResponse,
    summary="Re-classify a photo (post-capture role / pair / issue updates)",
)
async def patch_wo_photo(
    shop_id: int = PathParam(..., gt=0),
    wo_id: int = PathParam(..., gt=0),
    photo_id: int = PathParam(..., gt=0),
    req: PhotoPatchRequest = ...,
    user: AuthedUser = Depends(require_tier("shop")),
    db_path: str = Depends(get_db_path),
) -> WorkOrderPhotoResponse:
    """Post-capture re-classification surface.

    Used by the "X photos waiting to be classified" affordance — moves
    photos from ``role='undecided'`` to a typed role + optionally pairs
    them. Only fields present in the request body are updated.
    """
    require_shop_access(shop_id, user, db_path)
    _verify_wo_in_shop(shop_id, wo_id, db_path)
    row = get_wo_photo(photo_id, db_path=db_path)
    if row is None or int(row["work_order_id"]) != wo_id:
        raise WorkOrderPhotoOwnershipError(
            f"photo id={photo_id} not found"
        )

    # Validate pair_id targets a live photo on the same WO (if set).
    if req.pair_id is not None:
        partner = get_wo_photo_for_pairing(
            req.pair_id, expected_wo_id=wo_id, db_path=db_path,
        )
        if partner is None:
            raise WorkOrderPhotoPairingError(
                f"pair_id={req.pair_id} does not reference a live "
                f"photo on work_order_id={wo_id}"
            )

    update_pairing(
        photo_id,
        pair_id=req.pair_id,
        role=req.role,
        issue_id=req.issue_id,
        db_path=db_path,
    )
    # Mirror the pairing on the partner (symmetric pair_id).
    if req.pair_id is not None:
        update_pairing(req.pair_id, pair_id=photo_id, db_path=db_path)

    updated = get_wo_photo(photo_id, db_path=db_path)
    if updated is None:
        raise WorkOrderPhotoOwnershipError(
            f"photo id={photo_id} not found after update"
        )
    return _row_to_response(updated)


@router.delete(
    "/{shop_id}/work-orders/{wo_id}/photos/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a photo",
)
async def delete_wo_photo(
    shop_id: int = PathParam(..., gt=0),
    wo_id: int = PathParam(..., gt=0),
    photo_id: int = PathParam(..., gt=0),
    user: AuthedUser = Depends(require_tier("shop")),
    db_path: str = Depends(get_db_path),
) -> None:
    """Soft-delete via ``deleted_at``. Idempotent — second call also 204.

    Photos that referenced this one as ``pair_id`` will see their
    ``pair_id`` SET NULL via the FK constraint (migration 041).
    """
    require_shop_access(shop_id, user, db_path)
    _verify_wo_in_shop(shop_id, wo_id, db_path)
    soft_delete_wo_photo(photo_id, db_path=db_path)
    return None


@router.get(
    "/{shop_id}/work-orders/{wo_id}/photos/{photo_id}/file",
    summary="Stream the binary JPEG file",
    responses={200: {"content": {"image/jpeg": {}}}},
)
async def get_wo_photo_file(
    shop_id: int = PathParam(..., gt=0),
    wo_id: int = PathParam(..., gt=0),
    photo_id: int = PathParam(..., gt=0),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> FileResponse:
    require_shop_access(shop_id, user, db_path)
    _verify_wo_in_shop(shop_id, wo_id, db_path)
    row = get_wo_photo(photo_id, db_path=db_path)
    if row is None or int(row["work_order_id"]) != wo_id:
        raise WorkOrderPhotoOwnershipError(
            f"photo id={photo_id} not found"
        )
    file_path = Path(row["file_path"])
    if not file_path.exists():
        raise WorkOrderPhotoOwnershipError(
            f"photo id={photo_id} file missing on disk"
        )
    return FileResponse(
        path=str(file_path),
        media_type="image/jpeg",
        filename=f"wo_photo_{photo_id}.jpg",
    )
