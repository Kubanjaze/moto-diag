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


# ---------------------------------------------------------------------------
# Phase 195B (Commit 1) — atomic extraction finalize
# ---------------------------------------------------------------------------


def finalize_extraction(
    transcript_id: int,
    symptoms: list[dict],
    final_state: str,
    *,
    replace_existing: bool = False,
    db_path: Optional[str] = None,
) -> int:
    """Atomically write extracted-symptom rows + flip extraction_state.

    Phase 195B Backend Commit 1 ACCEPTANCE CRITERION (architect-
    elevated from a risk-register line): the async extraction
    pipeline's final write — the ``extracted_symptoms`` row INSERTs
    AND the ``voice_transcripts.extraction_state`` flip — MUST be a
    single atomic DB transaction. A mobile refetch landing mid-
    pipeline must see EITHER ``(extracting, no new rows)`` OR
    ``(<final_state>, all new rows)`` — never a torn state where the
    badge says one thing and the chips say another.

    ``get_connection`` commits once on clean ``with``-block exit and
    rolls back on any exception (verified: ``core/database.py``), so
    doing every INSERT + the UPDATE inside ONE ``with`` block IS the
    single transaction. This function is the only finalize path —
    callers MUST NOT interleave ``create_extracted_symptom`` +
    ``update_extraction_state`` separately (that is two transactions
    = the torn-state window).

    ``symptoms`` — list of dicts; each needs ``text``, optionally
    ``category`` / ``extraction_method`` (default 'keyword') /
    ``linked_symptom_id`` / ``confidence`` (default 1.0) /
    ``segment_start_ms`` / ``segment_end_ms``.

    ``replace_existing`` — when True, soft-deletes the transcript's
    current live extracted_symptoms before inserting the new set
    (used when the async pipeline re-extracts from the Whisper-
    canonical transcript + supersedes the sync keyword pass). All
    inside the same transaction.

    ``final_state`` — 'extracted' or 'extraction_failed'. Stamps
    ``extracted_at`` when 'extracted'.

    Returns the count of extracted_symptoms rows inserted.
    """
    now = _now_iso()
    with get_connection(db_path) as conn:
        if replace_existing:
            conn.execute(
                "UPDATE extracted_symptoms SET deleted_at = ? "
                "WHERE transcript_id = ? AND deleted_at IS NULL",
                (now, transcript_id),
            )
        inserted = 0
        for s in symptoms:
            text = s.get("text")
            if not text:
                continue
            conn.execute(
                """INSERT INTO extracted_symptoms (
                       transcript_id, text, category,
                       linked_symptom_id, confidence,
                       extraction_method,
                       segment_start_ms, segment_end_ms
                   )
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    transcript_id,
                    text,
                    s.get("category"),
                    s.get("linked_symptom_id"),
                    s.get("confidence", 1.0),
                    s.get("extraction_method", "keyword"),
                    s.get("segment_start_ms"),
                    s.get("segment_end_ms"),
                ),
            )
            inserted += 1
        # The state flip — same connection, same transaction.
        if final_state == "extracted":
            conn.execute(
                "UPDATE voice_transcripts "
                "SET extraction_state = ?, extracted_at = ?, "
                "    updated_at = ? "
                "WHERE id = ? AND deleted_at IS NULL",
                (final_state, now, now, transcript_id),
            )
        else:
            conn.execute(
                "UPDATE voice_transcripts "
                "SET extraction_state = ?, updated_at = ? "
                "WHERE id = ? AND deleted_at IS NULL",
                (final_state, now, transcript_id),
            )
        return inserted
