"""Phase 195 (Commit 0) — voice transcript upload + CRUD endpoints.

Six endpoints, fully nested under
``/v1/shop/{shop_id}/work-orders/{wo_id}/transcripts``:

  POST   /v1/shop/{shop_id}/work-orders/{wo_id}/transcripts
                                          require_tier('shop')
  GET    /v1/shop/{shop_id}/work-orders/{wo_id}/transcripts
                                          require_api_key
  GET    /v1/shop/{shop_id}/work-orders/{wo_id}/transcripts/{transcript_id}
                                          require_api_key
  PATCH  /v1/shop/{shop_id}/work-orders/{wo_id}/transcripts/{transcript_id}
            /extracted-symptoms/{extracted_id}
                                          require_tier('shop')
  DELETE /v1/shop/{shop_id}/work-orders/{wo_id}/transcripts/{transcript_id}
                                          require_tier('shop')
  GET    /v1/shop/{shop_id}/work-orders/{wo_id}/transcripts/{transcript_id}/audio
                                          require_api_key

All endpoints layer ``require_shop_access`` on top of the tier gate
(Phase 193 pattern). Cross-shop returns 403; cross-WO returns 404.

Quotas (per Phase 195 v1.0 plan):
  Per-WO count cap:    30 transcripts
  Per-tier monthly aggregate (per uploader):
    individual: 0  (require_tier already 402s; defense-in-depth)
    shop:       200 / month
    company:    unlimited

Storage (per Phase 195 v1.0 + plan Section 5):
  ``{settings.data_dir}/audio/shop_{shop_id}/work_order_{wo_id}/{transcript_id}.{ext}``
  where ``{ext}`` is the detected format (m4a / wav / ogg). Audio
  bytes pruned by the 60-day sweep (audio_sweep.prune_old_audio);
  transcripts permanent.

Keyword extraction (Section 2 γ substrate, Phase 195 scope):
  - In-handler sync call after the audio bytes land. Reads
    ``preview_text`` from the multipart metadata; runs the keyword
    matcher; inserts one ``extracted_symptoms`` row per match.
  - Phase 195B will extend this to a Claude-fallback async pass
    when the keyword pass yields zero rows or low coverage.
"""

from __future__ import annotations

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
from motodiag.media.audio_pipeline import inspect_audio
from motodiag.media.transcript_extraction import (
    extract_symptoms_from_transcript,
)
from motodiag.shop import get_work_order
from motodiag.shop.extracted_symptom_repo import (
    confirm_extracted_symptom,
    create_extracted_symptom,
    get_extracted_symptom,
    list_for_transcript,
)
from motodiag.shop.transcript_repo import (
    VoiceTranscriptOwnershipError,
    VoiceTranscriptQuotaExceededError,
    _update_audio_path,
    count_voice_transcripts_this_month_for_uploader,
    count_wo_voice_transcripts,
    create_voice_transcript,
    get_voice_transcript,
    list_wo_voice_transcripts,
    soft_delete_voice_transcript,
    update_extraction_state,
)


_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Quota constants
# ---------------------------------------------------------------------------


PER_WO_TRANSCRIPT_COUNT_CAP = 30
TIER_MONTHLY_TRANSCRIPT_LIMITS: dict[str, Optional[int]] = {
    "individual": 0,
    "shop": 200,
    "company": None,
}


PreviewEngine = Literal[
    "ios-speech",
    "android-speech-recognizer",
    "none",
]


# ---------------------------------------------------------------------------
# Wire shapes
# ---------------------------------------------------------------------------


class TranscriptUploadMetadata(BaseModel):
    """JSON body field accompanying the multipart audio upload.

    ``preview_text`` is the on-device STT result (when available);
    Phase 195's keyword extraction operates on this. ``preview_engine``
    identifies which on-device STT produced the text.

    ``duration_ms`` is mobile-supplied (authoritative when the audio
    pipeline header parser returns None for non-WAV formats).
    """
    model_config = ConfigDict(extra="ignore")

    captured_at: str
    duration_ms: int = Field(..., ge=0)
    language: str = Field("en-US")
    issue_id: Optional[int] = Field(None, ge=1)
    preview_text: Optional[str] = None
    preview_engine: Optional[PreviewEngine] = None


class ExtractedSymptomConfirmRequest(BaseModel):
    """PATCH body for mechanic confirm/edit of an extracted symptom."""
    model_config = ConfigDict(extra="ignore")

    text: Optional[str] = None
    linked_symptom_id: Optional[int] = Field(None, ge=1)
    category: Optional[str] = None


class ExtractedSymptomResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    transcript_id: int
    text: str
    category: Optional[str]
    linked_symptom_id: Optional[int]
    confidence: float
    extraction_method: str
    segment_start_ms: Optional[int]
    segment_end_ms: Optional[int]
    confirmed_by_user_id: Optional[int]
    confirmed_at: Optional[str]
    created_at: str


class VoiceTranscriptResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    work_order_id: int
    issue_id: Optional[int]
    audio_format: str
    audio_size_bytes: int
    duration_ms: int
    sample_rate_hz: int
    language: str
    captured_at: str
    uploaded_by_user_id: int
    preview_text: Optional[str]
    preview_engine: Optional[str]
    extraction_state: str
    extracted_at: Optional[str]
    audio_deleted_at: Optional[str]
    source: Optional[str]
    created_at: str
    extracted_symptoms: list[ExtractedSymptomResponse] = Field(
        default_factory=list,
    )


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


router = APIRouter(prefix="/shop", tags=["voice-transcripts"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_storage_dir(
    settings: Settings, shop_id: int, wo_id: int,
) -> Path:
    """Build (and create) the canonical storage directory for audio.

    Layout: ``{data_dir}/audio/shop_{id}/work_order_{id}/``.
    """
    base = (
        Path(settings.data_dir)
        / "audio"
        / f"shop_{shop_id}"
        / f"work_order_{wo_id}"
    )
    base.mkdir(parents=True, exist_ok=True)
    return base


def _enforce_quotas(
    *,
    work_order_id: int,
    user_tier: Optional[str],
    user_id: int,
    db_path: str,
) -> None:
    """Raise ``VoiceTranscriptQuotaExceededError`` on quota violation."""
    current_wo = count_wo_voice_transcripts(work_order_id, db_path=db_path)
    if current_wo >= PER_WO_TRANSCRIPT_COUNT_CAP:
        raise VoiceTranscriptQuotaExceededError(
            current=current_wo,
            limit=PER_WO_TRANSCRIPT_COUNT_CAP,
            scope="wo",
        )
    effective_tier = user_tier or "individual"
    cap = TIER_MONTHLY_TRANSCRIPT_LIMITS.get(effective_tier)
    if cap is None:
        return
    used = count_voice_transcripts_this_month_for_uploader(
        user_id, db_path=db_path,
    )
    if used >= cap:
        raise VoiceTranscriptQuotaExceededError(
            current=used, limit=cap, scope="monthly",
        )


def _verify_wo_in_shop(shop_id: int, wo_id: int, db_path: str) -> dict:
    """Fetch the WO IFF it belongs to ``shop_id``; else 404."""
    wo = get_work_order(wo_id, db_path=db_path)
    if wo is None or wo.get("shop_id") != shop_id:
        raise HTTPException(
            status_code=404, detail=f"work order id={wo_id} not found",
        )
    return wo


def _row_to_response(
    row: dict,
    extracted_rows: Optional[list[dict]] = None,
) -> VoiceTranscriptResponse:
    """Convert a transcript_repo dict + optional extracted_symptoms list
    to the wire response shape."""
    extracted_responses = [
        ExtractedSymptomResponse(
            id=int(e["id"]),
            transcript_id=int(e["transcript_id"]),
            text=str(e["text"]),
            category=e.get("category"),
            linked_symptom_id=(
                int(e["linked_symptom_id"])
                if e.get("linked_symptom_id") is not None
                else None
            ),
            confidence=float(e["confidence"]),
            extraction_method=str(e["extraction_method"]),
            segment_start_ms=e.get("segment_start_ms"),
            segment_end_ms=e.get("segment_end_ms"),
            confirmed_by_user_id=(
                int(e["confirmed_by_user_id"])
                if e.get("confirmed_by_user_id") is not None
                else None
            ),
            confirmed_at=e.get("confirmed_at"),
            created_at=str(e.get("created_at") or ""),
        )
        for e in (extracted_rows or [])
    ]
    return VoiceTranscriptResponse(
        id=int(row["id"]),
        work_order_id=int(row["work_order_id"]),
        issue_id=(
            int(row["issue_id"])
            if row.get("issue_id") is not None else None
        ),
        audio_format=str(row["audio_format"]),
        audio_size_bytes=int(row["audio_size_bytes"]),
        duration_ms=int(row["duration_ms"]),
        sample_rate_hz=int(row["sample_rate_hz"]),
        language=str(row["language"]),
        captured_at=str(row["captured_at"]),
        uploaded_by_user_id=int(row["uploaded_by_user_id"]),
        preview_text=row.get("preview_text"),
        preview_engine=row.get("preview_engine"),
        extraction_state=str(row["extraction_state"]),
        extracted_at=row.get("extracted_at"),
        audio_deleted_at=row.get("audio_deleted_at"),
        source=row.get("source"),
        created_at=str(row.get("created_at") or ""),
        extracted_symptoms=extracted_responses,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{shop_id}/work-orders/{wo_id}/transcripts",
    response_model=VoiceTranscriptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a voice memo + run keyword extraction",
)
async def upload_voice_transcript(
    shop_id: int = PathParam(..., gt=0),
    wo_id: int = PathParam(..., gt=0),
    file: UploadFile = File(...),
    metadata: str = Form(...),
    user: AuthedUser = Depends(require_tier("shop")),
    db_path: str = Depends(get_db_path),
    settings: Settings = Depends(get_api_settings),
) -> VoiceTranscriptResponse:
    """Multipart upload: ``file`` (audio bytes) + ``metadata`` (JSON).

    Pipeline:
    1. Validate WO + shop scope (403/404).
    2. Parse + validate metadata JSON (422 on shape error).
    3. Read multipart payload + inspect_audio for format detection
       (415 on unsupported, 422 on corrupt).
    4. Enforce quotas (402 on cap).
    5. Insert DB row with placeholder audio_path; resolve canonical
       disk path; write bytes; update DB row.
    6. Run keyword extraction over preview_text; create
       extracted_symptoms rows; flip extraction_state to 'extracted'.
    7. Return 201 with full transcript + extracted_symptoms.
    """
    require_shop_access(shop_id, user, db_path)
    _verify_wo_in_shop(shop_id, wo_id, db_path)

    try:
        meta = TranscriptUploadMetadata.model_validate_json(metadata)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    raw_bytes = await file.read()

    # Audio format detection + metadata extraction. Phase 195 stores
    # bytes verbatim; Phase 195B handles 16 kHz PCM normalization for
    # Whisper input.
    inspected = inspect_audio(raw_bytes)

    _enforce_quotas(
        work_order_id=wo_id,
        user_tier=user.tier,
        user_id=user.id,
        db_path=db_path,
    )

    # Trust mobile metadata for duration_ms when the format header
    # didn't expose it (M4A / Ogg). WAV duration comes from the
    # header parser; fall back to mobile if WAV parsing yielded
    # something inconsistent.
    duration_ms = (
        inspected.duration_ms
        if inspected.duration_ms is not None
        else meta.duration_ms
    )

    transcript_id = create_voice_transcript(
        work_order_id=wo_id,
        audio_path="",  # placeholder; updated post-INSERT
        audio_size_bytes=inspected.size_bytes,
        audio_format=inspected.audio_format,
        audio_sha256=inspected.sha256,
        duration_ms=duration_ms,
        sample_rate_hz=inspected.sample_rate_hz,
        language=meta.language,
        captured_at=meta.captured_at,
        uploaded_by_user_id=user.id,
        issue_id=meta.issue_id,
        preview_text=meta.preview_text,
        preview_engine=meta.preview_engine,
        db_path=db_path,
    )

    # Resolve canonical disk path; write bytes; update DB row.
    storage_dir = _resolve_storage_dir(settings, shop_id, wo_id)
    audio_path = storage_dir / f"{transcript_id}.{inspected.audio_format}"
    audio_path.write_bytes(raw_bytes)
    _update_audio_path(transcript_id, str(audio_path), db_path=db_path)

    # Keyword extraction over the on-device preview text. If
    # preview_text is None / empty, mark 'extracted' with zero rows
    # (the mobile UI can still show the transcript with empty-state
    # copy).
    extracted_phrases = extract_symptoms_from_transcript(meta.preview_text)
    for phrase in extracted_phrases:
        create_extracted_symptom(
            transcript_id=transcript_id,
            text=phrase.text,
            category=phrase.category,
            linked_symptom_id=None,
            confidence=phrase.confidence,
            extraction_method="keyword",
            db_path=db_path,
        )
    update_extraction_state(transcript_id, "extracted", db_path=db_path)

    row = get_voice_transcript(transcript_id, db_path=db_path)
    if row is None:
        raise VoiceTranscriptOwnershipError(
            f"transcript id={transcript_id} not found after insert",
        )
    extracted_rows = list_for_transcript(transcript_id, db_path=db_path)
    return _row_to_response(row, extracted_rows)


@router.get(
    "/{shop_id}/work-orders/{wo_id}/transcripts",
    response_model=list[VoiceTranscriptResponse],
    summary="List voice transcripts attached to a work order",
)
async def list_voice_transcripts_endpoint(
    shop_id: int = PathParam(..., gt=0),
    wo_id: int = PathParam(..., gt=0),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> list[VoiceTranscriptResponse]:
    require_shop_access(shop_id, user, db_path)
    _verify_wo_in_shop(shop_id, wo_id, db_path)
    rows = list_wo_voice_transcripts(wo_id, db_path=db_path)
    out = []
    for r in rows:
        extracted = list_for_transcript(int(r["id"]), db_path=db_path)
        out.append(_row_to_response(r, extracted))
    return out


@router.get(
    "/{shop_id}/work-orders/{wo_id}/transcripts/{transcript_id}",
    response_model=VoiceTranscriptResponse,
    summary="Get one voice transcript by id",
)
async def get_voice_transcript_endpoint(
    shop_id: int = PathParam(..., gt=0),
    wo_id: int = PathParam(..., gt=0),
    transcript_id: int = PathParam(..., gt=0),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> VoiceTranscriptResponse:
    require_shop_access(shop_id, user, db_path)
    _verify_wo_in_shop(shop_id, wo_id, db_path)
    row = get_voice_transcript(transcript_id, db_path=db_path)
    if row is None or int(row["work_order_id"]) != wo_id:
        raise VoiceTranscriptOwnershipError(
            f"transcript id={transcript_id} not found",
        )
    extracted = list_for_transcript(transcript_id, db_path=db_path)
    return _row_to_response(row, extracted)


@router.patch(
    "/{shop_id}/work-orders/{wo_id}/transcripts/{transcript_id}"
    "/extracted-symptoms/{extracted_id}",
    response_model=ExtractedSymptomResponse,
    summary="Mechanic-confirm / edit an extracted symptom",
)
async def confirm_extracted_symptom_endpoint(
    shop_id: int = PathParam(..., gt=0),
    wo_id: int = PathParam(..., gt=0),
    transcript_id: int = PathParam(..., gt=0),
    extracted_id: int = PathParam(..., gt=0),
    req: ExtractedSymptomConfirmRequest = ...,
    user: AuthedUser = Depends(require_tier("shop")),
    db_path: str = Depends(get_db_path),
) -> ExtractedSymptomResponse:
    require_shop_access(shop_id, user, db_path)
    _verify_wo_in_shop(shop_id, wo_id, db_path)

    transcript_row = get_voice_transcript(transcript_id, db_path=db_path)
    if transcript_row is None or int(transcript_row["work_order_id"]) != wo_id:
        raise VoiceTranscriptOwnershipError(
            f"transcript id={transcript_id} not found",
        )

    existing = get_extracted_symptom(extracted_id, db_path=db_path)
    if existing is None or int(existing["transcript_id"]) != transcript_id:
        raise VoiceTranscriptOwnershipError(
            f"extracted symptom id={extracted_id} not found on "
            f"transcript id={transcript_id}",
        )

    confirm_extracted_symptom(
        extracted_id,
        confirmed_by_user_id=user.id,
        text=req.text,
        linked_symptom_id=req.linked_symptom_id,
        category=req.category,
        db_path=db_path,
    )

    updated = get_extracted_symptom(extracted_id, db_path=db_path)
    if updated is None:
        raise VoiceTranscriptOwnershipError(
            f"extracted symptom id={extracted_id} not found after "
            f"update",
        )
    return ExtractedSymptomResponse(
        id=int(updated["id"]),
        transcript_id=int(updated["transcript_id"]),
        text=str(updated["text"]),
        category=updated.get("category"),
        linked_symptom_id=(
            int(updated["linked_symptom_id"])
            if updated.get("linked_symptom_id") is not None else None
        ),
        confidence=float(updated["confidence"]),
        extraction_method=str(updated["extraction_method"]),
        segment_start_ms=updated.get("segment_start_ms"),
        segment_end_ms=updated.get("segment_end_ms"),
        confirmed_by_user_id=(
            int(updated["confirmed_by_user_id"])
            if updated.get("confirmed_by_user_id") is not None else None
        ),
        confirmed_at=updated.get("confirmed_at"),
        created_at=str(updated.get("created_at") or ""),
    )


@router.delete(
    "/{shop_id}/work-orders/{wo_id}/transcripts/{transcript_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a voice transcript",
)
async def delete_voice_transcript(
    shop_id: int = PathParam(..., gt=0),
    wo_id: int = PathParam(..., gt=0),
    transcript_id: int = PathParam(..., gt=0),
    user: AuthedUser = Depends(require_tier("shop")),
    db_path: str = Depends(get_db_path),
) -> None:
    """Soft-delete via ``deleted_at``. Idempotent — second call also 204.

    The audio file on disk is left in place; the 60-day sweep will
    prune it eventually. (Aggressive immediate-unlink could race
    against playback streams; sweep handles cleanup deterministically.)
    """
    require_shop_access(shop_id, user, db_path)
    _verify_wo_in_shop(shop_id, wo_id, db_path)
    soft_delete_voice_transcript(transcript_id, db_path=db_path)
    return None


@router.get(
    "/{shop_id}/work-orders/{wo_id}/transcripts/{transcript_id}/audio",
    summary="Stream the binary audio file (returns 410 Gone if swept)",
    responses={
        200: {"content": {"audio/mp4": {}, "audio/wav": {}, "audio/ogg": {}}},
        410: {"description": "Audio bytes pruned by 60-day retention sweep"},
    },
)
async def stream_voice_transcript_audio(
    shop_id: int = PathParam(..., gt=0),
    wo_id: int = PathParam(..., gt=0),
    transcript_id: int = PathParam(..., gt=0),
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> FileResponse:
    require_shop_access(shop_id, user, db_path)
    _verify_wo_in_shop(shop_id, wo_id, db_path)
    row = get_voice_transcript(transcript_id, db_path=db_path)
    if row is None or int(row["work_order_id"]) != wo_id:
        raise VoiceTranscriptOwnershipError(
            f"transcript id={transcript_id} not found",
        )
    if row.get("audio_deleted_at") is not None:
        raise HTTPException(
            status_code=410,
            detail=(
                f"audio bytes for transcript id={transcript_id} were "
                f"pruned by the 60-day retention sweep at "
                f"{row['audio_deleted_at']}"
            ),
        )
    audio_path = Path(row["audio_path"])
    if not audio_path.exists():
        # File was somehow gone but audio_deleted_at wasn't stamped.
        # Treat as 410 — same UX outcome.
        raise HTTPException(
            status_code=410,
            detail=(
                f"audio file missing on disk for transcript id="
                f"{transcript_id}"
            ),
        )
    media_type_map = {
        "wav": "audio/wav",
        "m4a": "audio/mp4",
        "ogg": "audio/ogg",
    }
    media_type = media_type_map.get(
        str(row["audio_format"]), "application/octet-stream",
    )
    return FileResponse(
        path=str(audio_path),
        media_type=media_type,
        filename=f"voice_memo_{transcript_id}.{row['audio_format']}",
    )
