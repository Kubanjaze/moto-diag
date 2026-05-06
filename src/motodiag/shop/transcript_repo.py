"""Voice transcript repository — Phase 195 (Commit 0) substrate.

Function-based repo mirroring ``wo_photo_repo.py`` / ``video_repo.py``
shape (no class-based ORM, no SQLAlchemy — plain sqlite3 row dicts via
the project-standard ``get_connection`` context manager).

Design notes:

* Soft-delete via ``deleted_at``. ``get_voice_transcript`` and the list
  helpers exclude soft-deleted rows; ``soft_delete_voice_transcript``
  is idempotent.
* ``ON DELETE CASCADE`` on the FK to ``work_orders(id)`` (migration
  042) cleans up transcripts when their owning WO is deleted.
* ``audio_deleted_at`` distinct from ``deleted_at``: the former is
  set by the 60-day sweep (audio bytes pruned, transcript row stays);
  the latter soft-deletes the whole row. Both fields nullable.
* Owner-aware access at the route layer (Phase 193 ``require_shop_access``
  pattern); the repo trusts the caller-supplied ``work_order_id``
  filter.
* Quota helpers for per-WO + monthly-per-uploader enforcement at
  the route. Same shape as Phase 194's photo quota.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from motodiag.core.database import get_connection


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class VoiceTranscriptOwnershipError(ValueError):
    """Raised when a caller tries to touch a transcript they don't own.

    Routes translate to HTTP 404 (cross-WO; cross-shop is 403 from
    require_shop_access). Mirrors ``WorkOrderPhotoOwnershipError``.
    """


class VoiceTranscriptQuotaExceededError(Exception):
    """Raised when uploading one more transcript would exceed a quota.

    Mapped to HTTP 402 (per-WO count + monthly aggregate). Mirrors
    ``WorkOrderPhotoQuotaExceededError`` shape.
    """

    def __init__(
        self,
        current: int,
        limit: int,
        scope: str,
        unit: str = "count",
    ) -> None:
        self.current = current
        self.limit = limit
        self.scope = scope  # "wo" | "monthly"
        self.unit = unit
        super().__init__(
            f"voice transcript quota exceeded: "
            f"{current}/{limit} {unit} ({scope})"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _row_to_dict(row) -> Optional[dict]:
    """Convert a sqlite3.Row to a plain dict, deserializing JSON fields."""
    if row is None:
        return None
    d = dict(row)
    segments = d.get("whisper_segments")
    if segments:
        try:
            d["whisper_segments"] = json.loads(segments)
        except (json.JSONDecodeError, TypeError):
            d["whisper_segments"] = None
    else:
        d["whisper_segments"] = None
    return d


def _month_start_iso() -> str:
    """First instant of current UTC calendar month, SQLite-compatible.

    Format MUST match SQLite's ``datetime('now')`` output (space
    separator, no tz, no microseconds) for lex comparison in WHERE
    clauses. Same fix as ``video_repo._month_start_iso`` /
    ``wo_photo_repo._month_start_iso`` (post 2026-05-01 boundary bug).
    """
    now = datetime.now(timezone.utc)
    return now.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0,
    ).strftime("%Y-%m-%d %H:%M:%S")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _update_audio_path(
    transcript_id: int, audio_path: str, db_path: Optional[str] = None,
) -> bool:
    """Update the ``audio_path`` after writing the file to disk.

    Internal helper — the canonical disk path is derived from
    ``transcript_id``, so it's only known post-INSERT. Mirrors
    ``wo_photo_repo._update_file_path``.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE voice_transcripts SET audio_path = ?, "
            "updated_at = ? WHERE id = ?",
            (audio_path, _now_iso(), transcript_id),
        )
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Core CRUD
# ---------------------------------------------------------------------------


def create_voice_transcript(
    work_order_id: int,
    audio_path: str,
    audio_size_bytes: int,
    audio_format: str,
    audio_sha256: str,
    duration_ms: int,
    captured_at: str,
    uploaded_by_user_id: int,
    sample_rate_hz: int = 16000,
    language: str = "en-US",
    issue_id: Optional[int] = None,
    preview_text: Optional[str] = None,
    preview_engine: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    """Insert a new ``voice_transcripts`` row; return id.

    ``extraction_state`` defaults to 'pending' at the SQL layer
    (migration 042); the route updates to 'extracted' /
    'extraction_failed' after running keyword extraction.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO voice_transcripts (
                   work_order_id, issue_id,
                   audio_path, audio_size_bytes, audio_format,
                   audio_sha256, duration_ms, sample_rate_hz,
                   language, captured_at, uploaded_by_user_id,
                   preview_text, preview_engine
               )
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                work_order_id, issue_id,
                audio_path, audio_size_bytes, audio_format,
                audio_sha256, duration_ms, sample_rate_hz,
                language, captured_at, uploaded_by_user_id,
                preview_text, preview_engine,
            ),
        )
        return int(cursor.lastrowid)


def get_voice_transcript(
    transcript_id: int, db_path: Optional[str] = None,
) -> Optional[dict]:
    """Fetch one transcript by id. None if not found OR soft-deleted."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM voice_transcripts "
            "WHERE id = ? AND deleted_at IS NULL",
            (transcript_id,),
        )
        return _row_to_dict(cursor.fetchone())


def list_wo_voice_transcripts(
    work_order_id: int, db_path: Optional[str] = None,
) -> list[dict]:
    """List all live transcripts for a WO, newest captured-at first."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """SELECT * FROM voice_transcripts
               WHERE work_order_id = ? AND deleted_at IS NULL
               ORDER BY captured_at DESC, id DESC""",
            (work_order_id,),
        )
        return [
            d for d in (_row_to_dict(r) for r in cursor.fetchall())
            if d is not None
        ]


def update_extraction_state(
    transcript_id: int,
    new_state: str,
    db_path: Optional[str] = None,
) -> bool:
    """Update ``extraction_state`` and stamp ``extracted_at`` on success.

    ``new_state`` should be 'pending' / 'extracting' / 'extracted' /
    'extraction_failed' (CHECK constraint at the SQL layer).
    Stamps ``extracted_at = now`` when transitioning into 'extracted'.
    """
    now = _now_iso()
    with get_connection(db_path) as conn:
        if new_state == "extracted":
            cursor = conn.execute(
                "UPDATE voice_transcripts "
                "SET extraction_state = ?, extracted_at = ?, "
                "    updated_at = ? "
                "WHERE id = ? AND deleted_at IS NULL",
                (new_state, now, now, transcript_id),
            )
        else:
            cursor = conn.execute(
                "UPDATE voice_transcripts "
                "SET extraction_state = ?, updated_at = ? "
                "WHERE id = ? AND deleted_at IS NULL",
                (new_state, now, transcript_id),
            )
        return cursor.rowcount > 0


def soft_delete_voice_transcript(
    transcript_id: int, db_path: Optional[str] = None,
) -> bool:
    """Set ``deleted_at = now()`` on the transcript; idempotent.

    The FK CASCADE on ``extracted_symptoms.transcript_id`` only fires on
    real DELETE (not column updates). For soft-delete, we leave
    extracted_symptoms in place — they're effectively orphaned but still
    visible to direct queries; the route layer's get/list helpers all
    join through the transcript and filter on ``deleted_at IS NULL``,
    so the orphans don't surface in the UI.
    """
    now = _now_iso()
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE voice_transcripts "
            "SET deleted_at = ?, updated_at = ? "
            "WHERE id = ? AND deleted_at IS NULL",
            (now, now, transcript_id),
        )
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Quota helpers
# ---------------------------------------------------------------------------


def count_wo_voice_transcripts(
    work_order_id: int, db_path: Optional[str] = None,
) -> int:
    """Count live transcripts on a WO."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM voice_transcripts "
            "WHERE work_order_id = ? AND deleted_at IS NULL",
            (work_order_id,),
        )
        row = cursor.fetchone()
        return int(row[0]) if row else 0


def count_voice_transcripts_this_month_for_uploader(
    uploaded_by_user_id: int, db_path: Optional[str] = None,
) -> int:
    """Count transcripts this user uploaded so far this calendar month.

    Per-tier monthly aggregate enforcement: shop=200/mo, company=
    unlimited. Mirrors ``wo_photo_repo`` shape.
    """
    month_start = _month_start_iso()
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM voice_transcripts "
            "WHERE uploaded_by_user_id = ? "
            "AND created_at >= ? "
            "AND deleted_at IS NULL",
            (uploaded_by_user_id, month_start),
        )
        row = cursor.fetchone()
        return int(row[0]) if row else 0
