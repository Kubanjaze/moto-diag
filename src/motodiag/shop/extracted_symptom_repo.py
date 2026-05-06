"""Extracted symptom repository — Phase 195 (Commit 0) substrate.

Function-based repo paired with ``transcript_repo``. Each row is a
single extracted-symptom phrase pulled from a transcript by either
the keyword-extraction pass (Phase 195) or future Claude-fallback /
manual-edit (Phase 195B + later).

Soft-delete via ``deleted_at``. Confirmation tracking via
``confirmed_by_user_id`` + ``confirmed_at`` (mechanic taps a chip in
the UI to confirm an extracted symptom is correct).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from motodiag.core.database import get_connection


ExtractionMethod = Literal["keyword", "claude", "manual_edit"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row) -> Optional[dict]:
    if row is None:
        return None
    return dict(row)


# ---------------------------------------------------------------------------
# Core CRUD
# ---------------------------------------------------------------------------


def create_extracted_symptom(
    transcript_id: int,
    text: str,
    extraction_method: ExtractionMethod = "keyword",
    category: Optional[str] = None,
    linked_symptom_id: Optional[int] = None,
    confidence: float = 1.0,
    segment_start_ms: Optional[int] = None,
    segment_end_ms: Optional[int] = None,
    db_path: Optional[str] = None,
) -> int:
    """Insert a new ``extracted_symptoms`` row; return id."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO extracted_symptoms (
                   transcript_id, text, category,
                   linked_symptom_id, confidence,
                   extraction_method,
                   segment_start_ms, segment_end_ms
               )
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                transcript_id, text, category,
                linked_symptom_id, confidence,
                extraction_method,
                segment_start_ms, segment_end_ms,
            ),
        )
        return int(cursor.lastrowid)


def get_extracted_symptom(
    extracted_id: int, db_path: Optional[str] = None,
) -> Optional[dict]:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM extracted_symptoms "
            "WHERE id = ? AND deleted_at IS NULL",
            (extracted_id,),
        )
        return _row_to_dict(cursor.fetchone())


def list_for_transcript(
    transcript_id: int, db_path: Optional[str] = None,
) -> list[dict]:
    """List all live extracted symptoms for a transcript, ordered by id ASC.

    Order is insertion-order rather than newest-first: the keyword
    extraction pass walks the preview_text in order; preserving that
    order lets the UI render symptom chips in the same sequence as
    the transcript's narrative.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM extracted_symptoms "
            "WHERE transcript_id = ? AND deleted_at IS NULL "
            "ORDER BY id ASC",
            (transcript_id,),
        )
        return [
            d for d in (_row_to_dict(r) for r in cursor.fetchall())
            if d is not None
        ]


def confirm_extracted_symptom(
    extracted_id: int,
    confirmed_by_user_id: int,
    text: Optional[str] = None,
    linked_symptom_id: Optional[int] = None,
    category: Optional[str] = None,
    db_path: Optional[str] = None,
) -> bool:
    """Mechanic-confirm flow — sets ``confirmed_by_user_id`` +
    ``confirmed_at`` and optionally edits text / linked_symptom_id /
    category. ``extraction_method`` flips to 'manual_edit' iff text
    or linked_symptom_id changes (mechanic overrode the keyword
    pass).

    Only the fields explicitly passed update; None means "leave
    unchanged" (NOT "clear to NULL").
    """
    sets = ["confirmed_by_user_id = ?", "confirmed_at = ?"]
    params: list = [confirmed_by_user_id, _now_iso()]
    method_flipped = False

    if text is not None:
        sets.append("text = ?")
        params.append(text)
        method_flipped = True
    if linked_symptom_id is not None:
        sets.append("linked_symptom_id = ?")
        params.append(linked_symptom_id)
        method_flipped = True
    if category is not None:
        sets.append("category = ?")
        params.append(category)

    if method_flipped:
        sets.append("extraction_method = ?")
        params.append("manual_edit")

    params.append(extracted_id)
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE extracted_symptoms SET {', '.join(sets)} "
            f"WHERE id = ? AND deleted_at IS NULL",
            tuple(params),
        )
        return cursor.rowcount > 0


def soft_delete_extracted_symptom(
    extracted_id: int, db_path: Optional[str] = None,
) -> bool:
    """Set ``deleted_at = now()``; idempotent."""
    now = _now_iso()
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE extracted_symptoms SET deleted_at = ? "
            "WHERE id = ? AND deleted_at IS NULL",
            (now, extracted_id),
        )
        return cursor.rowcount > 0
