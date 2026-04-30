"""Phase 191B — video upload + AI analysis endpoints.

Five endpoints, fully nested under ``/v1/sessions/{id}/videos`` per the
codebase pattern (see :mod:`motodiag.api.routes.sessions` which uses the
same shape for ``/symptoms``, ``/fault-codes``, ``/notes``, ``/close``,
``/reopen``).

Auth posture (per Phase 191B v1.0 plan A2):
  POST   /v1/sessions/{id}/videos              require_tier('shop')
  GET    /v1/sessions/{id}/videos              require_api_key
  GET    /v1/sessions/{id}/videos/{video_id}   require_api_key
  DELETE /v1/sessions/{id}/videos/{video_id}   require_api_key
  GET    /v1/sessions/{id}/videos/{video_id}/file  require_api_key

Quotas (per A3):
  Per-session count cap: 10 videos
  Per-session size cap:  1 GB
  Per-tier monthly aggregate:
    individual: 0  (require_tier already 402s; defense-in-depth)
    shop:       200 / month
    company:    unlimited

Storage (per B1):
  ``{settings.data_dir}/videos/shop_{shop_id}/session_{session_id}/{video_id}.mp4``
  (``shop_id`` falls back to user id when the user has no shop membership.)

Background analysis (per "Background task wiring" + state machine):
  POST returns 201 immediately with ``analysis_state='pending'``;
  ``BackgroundTasks.add_task`` fires
  :func:`motodiag.media.analysis_worker.run_analysis_pipeline`.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, Form, HTTPException,
    Path as PathParam, UploadFile, status,
)
from fastapi.responses import FileResponse
from pydantic import ValidationError

from motodiag.api.deps import get_db_path, get_settings as get_api_settings
from motodiag.auth.deps import (
    AuthedUser, get_current_user, require_tier,
)
from motodiag.core import video_repo
from motodiag.core.config import Settings
from motodiag.core.models import VideoBase, VideoResponse


_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Quota constants (per Phase 191B v1.0 plan A3)
# ---------------------------------------------------------------------------


PER_SESSION_COUNT_CAP = 10
PER_SESSION_BYTES_CAP = 1 * 1024 * 1024 * 1024  # 1 GB
TIER_MONTHLY_VIDEO_LIMITS: dict[str, Optional[int]] = {
    "individual": 0,
    "shop": 200,
    "company": None,  # unlimited
}


# ---------------------------------------------------------------------------
# Custom exception (mapped to 413 in api/errors.py)
# ---------------------------------------------------------------------------


class VideoFileTooLargeError(Exception):
    """Raised when an upload would exceed the per-session size cap.

    Distinct from ``VideoQuotaExceededError`` (count + monthly aggregate
    → 402) because byte-overflow is semantically a payload issue → 413.
    """


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


router = APIRouter(prefix="/sessions", tags=["videos"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hash_file_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _resolve_storage_dir(
    settings: Settings, shop_id: int, session_id: int,
) -> Path:
    """Build (and create) the canonical storage directory for a video.

    Layout per B1: ``{data_dir}/videos/shop_{shop_id}/session_{session_id}/``.
    ``shop_id`` falls back to user id when no shop membership exists
    (individual tier callers are 402'd before reaching here, but the
    fallback keeps the path computable for any tier).
    """
    base = (
        Path(settings.data_dir)
        / "videos"
        / f"shop_{shop_id}"
        / f"session_{session_id}"
    )
    base.mkdir(parents=True, exist_ok=True)
    return base


def _enforce_per_session_caps(
    session_id: int, incoming_bytes: int, db_path: str,
) -> None:
    """Raise on per-session count or byte cap violation.

    Raises ``VideoQuotaExceededError`` when the count cap is hit (402)
    and ``VideoFileTooLargeError`` when adding ``incoming_bytes`` would
    push the session over the bytes cap (413). Defense-in-depth — mobile
    already has 5/500MB caps; backend enforces stricter 10/1GB to absorb
    retries.
    """
    current_count = video_repo.count_videos_in_session(
        session_id, db_path=db_path,
    )
    if current_count >= PER_SESSION_COUNT_CAP:
        raise video_repo.VideoQuotaExceededError(
            current=current_count,
            limit=PER_SESSION_COUNT_CAP,
            scope="session",
            unit="count",
        )
    existing_bytes = video_repo.count_bytes_in_session(
        session_id, db_path=db_path,
    )
    if existing_bytes + incoming_bytes > PER_SESSION_BYTES_CAP:
        raise VideoFileTooLargeError(
            f"Adding this video ({incoming_bytes} bytes) would exceed "
            f"the per-session size cap of {PER_SESSION_BYTES_CAP} bytes "
            f"(currently {existing_bytes} bytes used)."
        )


def _enforce_monthly_quota(
    user_tier: Optional[str], user_id: int, db_path: str,
) -> None:
    """Enforce the per-tier monthly aggregate quota.

    The ``require_tier('shop')`` gate already 402s individual-tier
    callers, but this is defense-in-depth + applies to shop callers.
    Company tier is unlimited and short-circuits.
    """
    effective_tier = user_tier or "individual"
    cap = TIER_MONTHLY_VIDEO_LIMITS.get(effective_tier)
    if cap is None:
        return  # company tier — unlimited
    used = video_repo.count_videos_this_month_for_owner(
        user_id, db_path=db_path,
    )
    if used >= cap:
        raise video_repo.VideoQuotaExceededError(
            current=used,
            limit=cap,
            scope="monthly",
            unit="count",
        )


def _row_to_video_response(row: dict) -> VideoResponse:
    """Convert a video_repo row dict to a wire ``VideoResponse``.

    ``file_path`` and ``sha256`` are deliberately omitted from the
    response shape (they're internal storage details).
    """
    return VideoResponse(
        id=int(row["id"]),
        session_id=int(row["session_id"]),
        started_at=str(row["started_at"]),
        duration_ms=int(row["duration_ms"]),
        width=int(row["width"]),
        height=int(row["height"]),
        file_size_bytes=int(row["file_size_bytes"]),
        format=str(row.get("format") or "mp4"),
        codec=str(row.get("codec") or "h264"),
        interrupted=bool(row.get("interrupted") or False),
        upload_state=row.get("upload_state") or "uploaded",
        analysis_state=row.get("analysis_state") or "pending",
        analysis_findings=row.get("analysis_findings"),
        analyzed_at=row.get("analyzed_at"),
        created_at=str(row.get("created_at") or ""),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{session_id}/videos",
    response_model=VideoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a video to a session and queue analysis",
)
async def upload_video(
    background_tasks: BackgroundTasks,
    session_id: int = PathParam(..., gt=0),
    file: UploadFile = File(...),
    metadata: str = Form(...),
    user: AuthedUser = Depends(require_tier("shop")),
    db_path: str = Depends(get_db_path),
    settings: Settings = Depends(get_api_settings),
) -> VideoResponse:  # noqa: ARG001 — background_tasks is FastAPI-injected
    """Upload an mp4 + sidecar metadata; queue Vision analysis.

    Multipart fields:
      file:     mp4 binary
      metadata: JSON string mirroring :class:`VideoBase` shape
                (started_at, duration_ms, width, height,
                file_size_bytes, format, codec, interrupted)
    """
    # 1. Parse + validate metadata JSON
    try:
        meta_obj = VideoBase.model_validate_json(metadata)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    # 2. Read multipart payload
    body = await file.read()
    sha256 = _hash_file_bytes(body)
    incoming_bytes = len(body)

    # 3. Caps BEFORE writing file (avoid wasted IO on quota fail)
    _enforce_per_session_caps(session_id, incoming_bytes, db_path)
    _enforce_monthly_quota(user.tier, user.id, db_path)

    # 4. Insert DB row with placeholder file_path (path is video_id-derived,
    #    only known post-INSERT). Owner-aware variant verifies session
    #    ownership and returns None on missing session → translate to 404.
    new_video_id = video_repo.create_video_for_owner(
        user_id=user.id,
        session_id=session_id,
        file_path="",
        sha256=sha256,
        started_at=meta_obj.started_at,
        duration_ms=meta_obj.duration_ms,
        width=meta_obj.width,
        height=meta_obj.height,
        file_size_bytes=meta_obj.file_size_bytes,
        format=meta_obj.format,
        codec=meta_obj.codec,
        interrupted=meta_obj.interrupted,
        db_path=db_path,
    )
    if new_video_id is None:
        raise video_repo.VideoOwnershipError(
            f"session id={session_id} not found"
        )

    # 5. Resolve canonical disk path (mkdir parents=True), write bytes,
    #    update DB row with the real path.
    shop_id = getattr(user, "shop_id", None) or user.id
    storage_dir = _resolve_storage_dir(settings, shop_id, session_id)
    file_path = storage_dir / f"{new_video_id}.mp4"
    file_path.write_bytes(body)
    video_repo._update_file_path(
        new_video_id, str(file_path), db_path=db_path,
    )

    # 6. Queue background analysis (BackgroundTasks is always non-None
    #    when injected by FastAPI; the guard is paranoia for tests).
    if background_tasks is not None:
        from motodiag.media.analysis_worker import run_analysis_pipeline
        background_tasks.add_task(
            run_analysis_pipeline, new_video_id, db_path,
        )

    # 7. Return the freshly-written row as a VideoResponse
    row = video_repo.get_video(new_video_id, db_path=db_path)
    if row is None:
        # Should never happen — we just inserted + updated.
        raise video_repo.VideoOwnershipError(
            f"video id={new_video_id} not found after insert"
        )
    return _row_to_video_response(row)


@router.get(
    "/{session_id}/videos",
    response_model=list[VideoResponse],
    summary="List videos for a session",
)
async def list_videos(
    session_id: int = PathParam(..., gt=0),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> list[VideoResponse]:
    rows = video_repo.list_session_videos_for_owner(
        user_id=user.id, session_id=session_id, db_path=db_path,
    )
    if rows is None:
        # Session does not exist (cross-owner case raises
        # VideoOwnershipError inside the repo; both surface as 404).
        raise video_repo.VideoOwnershipError(
            f"session id={session_id} not found"
        )
    return [_row_to_video_response(r) for r in rows]


@router.get(
    "/{session_id}/videos/{video_id}",
    response_model=VideoResponse,
    summary="Get one video by id",
)
async def get_one_video(
    session_id: int = PathParam(..., gt=0),
    video_id: int = PathParam(..., gt=0),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> VideoResponse:
    row = video_repo.get_video_for_owner(
        user_id=user.id, video_id=video_id, db_path=db_path,
    )
    if row is None or int(row["session_id"]) != session_id:
        raise video_repo.VideoOwnershipError(
            f"video id={video_id} not found"
        )
    return _row_to_video_response(row)


@router.delete(
    "/{session_id}/videos/{video_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a video",
)
async def delete_video(
    session_id: int = PathParam(..., gt=0),
    video_id: int = PathParam(..., gt=0),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> None:
    """Soft-delete via ``deleted_at``. Idempotent — second call also 204."""
    video_repo.soft_delete_video_for_owner(
        user_id=user.id, video_id=video_id, db_path=db_path,
    )
    return None


@router.get(
    "/{session_id}/videos/{video_id}/file",
    summary="Stream the binary mp4 file",
    responses={200: {"content": {"video/mp4": {}}}},
)
async def get_video_file(
    session_id: int = PathParam(..., gt=0),
    video_id: int = PathParam(..., gt=0),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> FileResponse:
    row = video_repo.get_video_for_owner(
        user_id=user.id, video_id=video_id, db_path=db_path,
    )
    if row is None or int(row["session_id"]) != session_id:
        raise video_repo.VideoOwnershipError(
            f"video id={video_id} not found"
        )
    file_path = Path(row["file_path"])
    if not file_path.exists():
        raise video_repo.VideoOwnershipError(
            f"video id={video_id} file missing on disk"
        )
    # FileResponse handles Content-Type + Content-Length + Accept-Ranges.
    return FileResponse(
        path=str(file_path),
        media_type="video/mp4",
        filename=f"video_{video_id}.mp4",
    )
