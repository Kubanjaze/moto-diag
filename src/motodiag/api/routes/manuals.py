"""Phase 293 — the shop manual library's routes (K94, K119, K123).

Two routers. ``/v1/shop/{shop_id}/manuals…`` (tag ``manuals``) is the
shop's: its admin uploads, every member lists, opens, searches and flags.
Every route checks membership first (403 for a non-member) and then that the
manual is this shop's (404 otherwise); a page or a search reaches only an
``approved`` manual, so a pending file is not told apart from none. Another
shop never sees any of it. ``/v1/review/manuals…`` (tag ``manual-review``)
is the reviewer's, and only the reviewer's (``require_reviewer``).

The fixed words ``usage`` and ``search`` are declared before every
``{manual_id}`` route, and ``manual_id`` is an integer, so neither word is
ever read as an id.

The upload, in order: the tag (422); the bytes, at most 300 MB (413); this
shop already holding the same file (409); the shop's plan and its storage
(402); the server's checks (422); the virus scan (422 infected, 503 with no
scanner); then the row, the file moved into place, and the render queued.
The temporary file is removed on every path.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Literal, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi import Path as PathParam
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from motodiag.api.deps import get_db_path
from motodiag.api.deps import get_settings as get_api_settings
from motodiag.api.routes.shop_mgmt import require_shop_access
from motodiag.api.uploads import read_bounded
from motodiag.auth.deps import AuthedUser, get_current_user, require_tier
from motodiag.billing.subscription_repo import shop_plan
from motodiag.core.config import Settings
from motodiag.manuals import (
    ManualDuplicateError,
    ManualNotFoundError,
    ManualRefusedError,
    ManualScannerUnavailableError,
    ManualStorageExceededError,
    ShopPlanRequiredError,
    storage,
)
from motodiag.manuals.checks import check_pdf, page_count
from motodiag.manuals.render import render_manual
from motodiag.manuals.review import decide, flag, require_reviewer
from motodiag.manuals.scan import scan_file
from motodiag.media.paths import resolve_media_path, stored_media_path
from motodiag.reference import manual_repo
from motodiag.reference.models import (
    ManualKind,
    ManualReference,
    ManualSource,
    ManualStatus,
    ReviewDecision,
)

YEAR_MIN, YEAR_MAX = 1970, 2030  # VehicleBase's bounds
FREE_SPACE = "Delete a manual from the list to free space."
PageSize = Literal["full", "thumb"]


# ---------------------------------------------------------------- wire shapes
# f9-table: manual_references
class ManualUploadMetadata(BaseModel):
    """The JSON ``metadata`` part of the upload: the manual's tag."""
    model_config = ConfigDict(extra="ignore")

    title: str = Field(..., min_length=1, max_length=300)
    kind: ManualKind = "service_manual"
    source: ManualSource = ManualSource.OTHER
    publisher: Optional[str] = Field(None, max_length=200)
    make: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    year_start: Optional[int] = Field(None, ge=YEAR_MIN, le=YEAR_MAX)
    year_end: Optional[int] = Field(None, ge=YEAR_MIN, le=YEAR_MAX)


# f9-table: manual_references
class ManualResponse(BaseModel):
    """A manual as the shop sees it: its tag, its review and its pages;
    never where the file is stored or its hash."""
    model_config = ConfigDict(extra="ignore")

    id: int
    shop_id: int
    title: str
    kind: Optional[ManualKind]
    source: str
    publisher: Optional[str]
    make: Optional[str]
    model: Optional[str]
    year_start: Optional[int]
    year_end: Optional[int]
    status: ManualStatus
    review_reason: Optional[str]
    reviewed_at: Optional[str]
    page_count: Optional[int]
    rendered_pages: int
    render_error: Optional[str]
    file_size_bytes: Optional[int]
    uploaded_by_user_id: Optional[int]
    created_at: Optional[str]


# f9-table: manual_references
class ReviewQueueItem(ManualResponse):
    """A manual in the reviewer's queue, with whose it is."""
    shop_name: Optional[str] = None
    uploader_username: Optional[str] = None
    reviewed_by_user_id: Optional[int] = None


class ManualUsageResponse(BaseModel):
    plan: Optional[str]
    used_bytes: int
    limit_bytes: Optional[int]
    file_cap_bytes: int


class ManualSearchHit(BaseModel):
    manual_id: int
    title: str
    page_number: int
    snippet: str


class ManualFlagRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    page_number: int = Field(..., ge=1)
    reason: str = Field(..., min_length=1, max_length=2000)


class ReviewDecisionRequest(BaseModel):
    """A decision, with any tag fields the reviewer corrects first."""
    model_config = ConfigDict(extra="ignore")

    decision: ReviewDecision
    reason: Optional[str] = Field(None, max_length=2000)
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    kind: Optional[ManualKind] = None
    make: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    year_start: Optional[int] = Field(None, ge=YEAR_MIN, le=YEAR_MAX)
    year_end: Optional[int] = Field(None, ge=YEAR_MIN, le=YEAR_MAX)


router = APIRouter(prefix="/shop", tags=["manuals"])
review_router = APIRouter(prefix="/review", tags=["manual-review"])


# ---------------------------------------------------------------- helpers
def _manual_in_shop(shop_id: int, manual_id: int, db_path: str) -> dict:
    """The manual IFF it is this shop's; else 404 (``_verify_wo_in_shop``'s form)."""
    manual = manual_repo.get_manual(manual_id, db_path=db_path)
    if manual is None or manual.get("shop_id") != shop_id:
        raise ManualNotFoundError(f"manual id={manual_id} not found")
    return manual


def _uploaded_manual(manual_id: int, db_path: str) -> dict:
    manual = manual_repo.get_manual(manual_id, db_path=db_path)
    if manual is None or manual.get("shop_id") is None:
        raise ManualNotFoundError(f"manual id={manual_id} not found")
    return manual


def _page_file(manual: dict, n: int, size: PageSize, settings: Settings,
               db_path: str) -> FileResponse:
    page = manual_repo.get_page(int(manual["id"]), n, db_path=db_path)
    if page is None:
        raise ManualNotFoundError(f"page {n} of manual id={manual['id']} not found")
    path = resolve_media_path(page["thumb_path" if size == "thumb" else "image_path"],
                              settings.data_dir)
    if not path.exists():
        raise ManualNotFoundError(f"page {n} of manual id={manual['id']} is not on disk")
    return FileResponse(path=str(path), media_type="image/jpeg",
                        filename=f"manual_{manual['id']}_page_{n}.jpg")


def _storage_check(shop_id: int, size: int, db_path: str) -> None:
    limit = storage.storage_limit_bytes(shop_id, db_path)
    if limit is None:
        raise ShopPlanRequiredError()
    used = manual_repo.storage_used_bytes(shop_id, db_path=db_path)
    if used + size > limit:
        raise ManualStorageExceededError(
            f"The shop's {shop_plan(shop_id, db_path)} plan stores {limit} bytes of "
            f"manuals; {used} bytes are used and this file is {size} bytes. "
            f"Rejected and taken-down manuals count until they are deleted. {FREE_SPACE}")


def _refuse_unsafe(path: Path) -> None:
    reasons = check_pdf(path)
    if reasons:
        raise ManualRefusedError("; ".join(reasons))
    scanned = scan_file(path)
    if scanned.status == "infected":
        raise ManualRefusedError("the file failed the virus scan")
    if scanned.status == "unavailable":
        raise ManualScannerUnavailableError(
            "the server's virus scanner is not available, so no upload is accepted")


def _store(meta: ManualUploadMetadata, tmp: Path, sha256: str, size: int, shop_id: int,
           user_id: int, settings: Settings, db_path: str) -> int:
    pages = page_count(tmp)
    manual_id = manual_repo.add_manual(ManualReference(
        source=meta.source, title=meta.title, publisher=meta.publisher, make=meta.make,
        model=meta.model, year_start=meta.year_start, year_end=meta.year_end,
        shop_id=shop_id, uploaded_by_user_id=user_id, kind=meta.kind,
        status="pending_review", page_count=pages,
    ), db_path=db_path)
    final = storage.manual_file_path(settings.data_dir, shop_id, manual_id)
    final.parent.mkdir(parents=True, exist_ok=True)
    os.replace(tmp, final)
    manual_repo.set_file(manual_id, stored_media_path(final, settings.data_dir), sha256,
                         size, pages, db_path=db_path)
    return manual_id


# ---------------------------------------------------------------- the shop's routes
@router.post(
    "/{shop_id}/manuals",
    response_model=ManualResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF manual or parts book the shop owns",
)
async def upload_manual(
    background: BackgroundTasks,
    shop_id: int = PathParam(..., gt=0),
    file: UploadFile = File(...),
    metadata: str = Form(...),
    user: AuthedUser = Depends(require_tier("individual")),
    db_path: str = Depends(get_db_path),
    settings: Settings = Depends(get_api_settings),
) -> ManualResponse:
    """Multipart ``file`` (the PDF) and ``metadata`` (its tag, JSON). The
    owner and the service writer upload (``manage_shop``). The manual waits
    for review before anyone can open it."""
    require_shop_access(shop_id, user, db_path, permission="manage_shop")
    try:
        meta = ManualUploadMetadata.model_validate_json(metadata)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
    data = await read_bounded(file, storage.MANUAL_FILE_BYTES_CAP, kind="manual")
    sha256 = hashlib.sha256(data).hexdigest()
    same = manual_repo.find_by_sha(shop_id, sha256, db_path=db_path)
    if same is not None:
        raise ManualDuplicateError(
            f"this shop already has this file as manual id={same['id']} "
            f"({same['status']}); delete it first to upload it again")
    _storage_check(shop_id, len(data), db_path)
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=settings.data_dir, prefix=".manual_upload_", suffix=".pdf")
    tmp = Path(name)
    try:
        with os.fdopen(fd, "wb") as fout:
            fout.write(data)
        _refuse_unsafe(tmp)
        manual_id = _store(meta, tmp, sha256, len(data), shop_id, user.id, settings, db_path)
    finally:
        tmp.unlink(missing_ok=True)
    background.add_task(render_manual, manual_id, db_path, settings.data_dir)
    return ManualResponse(**_manual_in_shop(shop_id, manual_id, db_path))


@router.get(
    "/{shop_id}/manuals",
    response_model=list[ManualResponse],
    summary="The shop's manuals, of every status, by bike",
)
def list_shop_manuals(
    shop_id: int = PathParam(..., gt=0),
    make: Optional[str] = None,
    model: Optional[str] = None,
    year: Optional[int] = Query(None, ge=YEAR_MIN, le=YEAR_MAX),
    kind: Optional[ManualKind] = None,
    status_filter: Optional[ManualStatus] = Query(None, alias="status"),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> list[ManualResponse]:
    require_shop_access(shop_id, user, db_path)
    rows = manual_repo.list_manuals(make=make, model=model, target_year=year,
                                    shop_id=shop_id, status=status_filter, kind=kind,
                                    db_path=db_path)
    return [ManualResponse(**r) for r in rows]


@router.get(
    "/{shop_id}/manuals/usage",
    response_model=ManualUsageResponse,
    summary="The shop's manual storage: used, its plan's limit, the file cap",
)
def manual_usage(
    shop_id: int = PathParam(..., gt=0),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> ManualUsageResponse:
    require_shop_access(shop_id, user, db_path)
    return ManualUsageResponse(
        plan=shop_plan(shop_id, db_path),
        used_bytes=manual_repo.storage_used_bytes(shop_id, db_path=db_path),
        limit_bytes=storage.storage_limit_bytes(shop_id, db_path),
        file_cap_bytes=storage.MANUAL_FILE_BYTES_CAP,
    )


@router.get(
    "/{shop_id}/manuals/search",
    response_model=list[ManualSearchHit],
    summary="Find the page with the words, in the shop's approved manuals",
)
def search_shop_manuals(
    shop_id: int = PathParam(..., gt=0),
    q: str = Query(..., min_length=1, max_length=200),
    make: Optional[str] = None,
    model: Optional[str] = None,
    year: Optional[int] = Query(None, ge=YEAR_MIN, le=YEAR_MAX),
    limit: int = Query(20, ge=1, le=100),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> list[ManualSearchHit]:
    require_shop_access(shop_id, user, db_path)
    hits = manual_repo.search_pages(shop_id, q, make=make, model=model, target_year=year,
                                    limit=limit, db_path=db_path)
    return [ManualSearchHit(**h) for h in hits]


@router.get(
    "/{shop_id}/manuals/{manual_id}",
    response_model=ManualResponse,
    summary="One of the shop's manuals, any status",
)
def get_shop_manual(
    shop_id: int = PathParam(..., gt=0),
    manual_id: int = PathParam(..., gt=0),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> ManualResponse:
    require_shop_access(shop_id, user, db_path)
    return ManualResponse(**_manual_in_shop(shop_id, manual_id, db_path))


@router.get(
    "/{shop_id}/manuals/{manual_id}/pages/{n}",
    summary="A page of an approved manual, as a JPEG",
    responses={200: {"content": {"image/jpeg": {}}}},
)
def get_shop_manual_page(
    shop_id: int = PathParam(..., gt=0),
    manual_id: int = PathParam(..., gt=0),
    n: int = PathParam(..., ge=1),
    size: PageSize = "full",
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
    settings: Settings = Depends(get_api_settings),
) -> FileResponse:
    require_shop_access(shop_id, user, db_path)
    manual = _manual_in_shop(shop_id, manual_id, db_path)
    if manual["status"] != "approved":
        raise ManualNotFoundError(f"manual id={manual_id} not found")
    return _page_file(manual, n, size, settings, db_path)


@router.post(
    "/{shop_id}/manuals/{manual_id}/flag",
    response_model=ManualResponse,
    summary="Send an approved manual back for review, naming a page and why",
)
def flag_shop_manual(
    req: ManualFlagRequest,
    shop_id: int = PathParam(..., gt=0),
    manual_id: int = PathParam(..., gt=0),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> ManualResponse:
    require_shop_access(shop_id, user, db_path)
    _manual_in_shop(shop_id, manual_id, db_path)
    return ManualResponse(**flag(manual_id, user.id, req.page_number, req.reason,
                                 db_path=db_path))


@router.delete(
    "/{shop_id}/manuals/{manual_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a manual: its file, its page images and its rows",
)
def delete_shop_manual(
    shop_id: int = PathParam(..., gt=0),
    manual_id: int = PathParam(..., gt=0),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
    settings: Settings = Depends(get_api_settings),
) -> None:
    """Idempotent: a manual already gone is 204 again."""
    require_shop_access(shop_id, user, db_path, permission="manage_shop")
    manual = manual_repo.get_manual(manual_id, db_path=db_path)
    if manual is None:
        return None
    if manual.get("shop_id") != shop_id:
        raise ManualNotFoundError(f"manual id={manual_id} not found")
    storage.remove_manual_files(settings.data_dir, shop_id, manual_id)
    manual_repo.delete_manual(manual_id, db_path=db_path)
    return None


# ---------------------------------------------------------------- the reviewer's routes
@review_router.get(
    "/manuals",
    response_model=list[ReviewQueueItem],
    summary="The review queue across every shop, oldest first",
)
def review_queue(
    status_filter: ManualStatus = Query("pending_review", alias="status"),
    reviewer: AuthedUser = Depends(require_reviewer),
    db_path: str = Depends(get_db_path),
) -> list[ReviewQueueItem]:
    return [ReviewQueueItem(**r) for r in manual_repo.list_for_review(status_filter, db_path)]


@review_router.get(
    "/manuals/{manual_id}",
    response_model=ReviewQueueItem,
    summary="One uploaded manual, any status, any shop",
)
def review_manual(
    manual_id: int = PathParam(..., gt=0),
    reviewer: AuthedUser = Depends(require_reviewer),
    db_path: str = Depends(get_db_path),
) -> ReviewQueueItem:
    return ReviewQueueItem(**_uploaded_manual(manual_id, db_path))


@review_router.get(
    "/manuals/{manual_id}/pages/{n}",
    summary="A page of any uploaded manual, as a JPEG",
    responses={200: {"content": {"image/jpeg": {}}}},
)
def review_manual_page(
    manual_id: int = PathParam(..., gt=0),
    n: int = PathParam(..., ge=1),
    size: PageSize = "full",
    reviewer: AuthedUser = Depends(require_reviewer),
    db_path: str = Depends(get_db_path),
    settings: Settings = Depends(get_api_settings),
) -> FileResponse:
    return _page_file(_uploaded_manual(manual_id, db_path), n, size, settings, db_path)


@review_router.post(
    "/manuals/{manual_id}/decision",
    response_model=ReviewQueueItem,
    summary="Approve, fix the tag and approve, reject, or take down",
)
def review_decision(
    req: ReviewDecisionRequest,
    manual_id: int = PathParam(..., gt=0),
    reviewer: AuthedUser = Depends(require_reviewer),
    db_path: str = Depends(get_db_path),
) -> ReviewQueueItem:
    tag = req.model_dump(include={"title", "kind", "make", "model", "year_start", "year_end"},
                         exclude_none=True)
    row = decide(manual_id, req.decision, req.reason, reviewer.id, tag_fixes=tag,
                 db_path=db_path)
    return ReviewQueueItem(**row)
