"""Async voice-transcript extraction pipeline — Phase 195B (Commit 1).

The orchestrator the upload route hands to ``BackgroundTasks`` after
returning 201. Phase 191B's Vision ``analysis_worker`` is the
precedent shape: the route returns immediately with
``extraction_state='extracting'``; this pipeline runs the slow work
out-of-band, then atomically finalizes.

Pipeline stages (per Phase 195B plan v1.0 §1/§2/§3/§6):

1. **Whisper transcribe** the stored audio (`whisper_client`). On
   success: write the ``whisper_*`` columns + record a ``cost_events``
   row. On ``WhisperUnavailableError`` / ``WhisperTranscriptionError``:
   degrade silently — the pipeline continues using the on-device
   ``preview_text``. Whisper failure is NOT an extraction failure.
2. **Pick the best transcript text** — the Whisper-canonical text
   when available, else ``preview_text``.
3. **Keyword extraction** over the best text (`transcript_extraction`).
4. **Threshold gate** — `should_run_claude_fallback`. Below the
   coverage threshold → run **Claude-rich extraction**
   (`DiagnosticClient.extract_symptoms`, tool-use, Haiku) + record a
   second ``cost_events`` row. On ``ClaudeExtractionMalformedError``
   or a not-configured client: keep the keyword rows, finalize state
   ``extraction_failed`` (plan §2 graceful degradation).
5. **Atomic finalize** — `finalize_extraction` writes every symptom
   row + flips ``extraction_state`` in ONE transaction (the Commit 1
   acceptance criterion: no torn mid-pipeline state).

Every stage is defensive — a BackgroundTask raising would be
swallowed by the framework + leave the transcript stuck in
``extracting`` forever. The top-level catch finalizes
``extraction_failed`` so the row never hangs.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from motodiag.media.transcript_extraction import (
    categories,
    extract_symptoms_from_transcript,
    should_run_claude_fallback,
)
from motodiag.media.whisper_client import (
    WhisperTranscriptionError,
    WhisperUnavailableError,
    transcribe,
)
from motodiag.shop.cost_repo import record_cost_event
from motodiag.shop.extracted_symptom_repo import finalize_extraction
from motodiag.shop.transcript_repo import (
    get_voice_transcript,
    update_whisper_result,
)


_log = logging.getLogger(__name__)


def run_extraction_pipeline(
    transcript_id: int,
    shop_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> None:
    """Run the full async extraction pipeline for one transcript.

    Designed as a ``BackgroundTasks.add_task`` target — returns None,
    swallows nothing silently (logs every degradation), and ALWAYS
    finalizes the transcript out of ``extracting`` (success or
    failure) so a row can never hang.
    """
    try:
        _run(transcript_id, shop_id, db_path)
    except Exception as exc:  # noqa: BLE001 — last-resort safety net
        # A BackgroundTask exception is swallowed by the framework +
        # would strand the transcript in 'extracting'. Finalize
        # 'extraction_failed' with whatever keyword rows we can still
        # compute, so the row never hangs.
        _log.error(
            "extraction pipeline crashed for transcript %d: %s",
            transcript_id, exc,
        )
        try:
            _finalize_failed_keyword_only(transcript_id, db_path)
        except Exception:  # noqa: BLE001
            _log.error(
                "could not finalize crashed transcript %d; "
                "it may remain stuck in 'extracting'",
                transcript_id,
            )


def _run(
    transcript_id: int,
    shop_id: Optional[int],
    db_path: Optional[str],
) -> None:
    row = get_voice_transcript(transcript_id, db_path=db_path)
    if row is None:
        _log.warning(
            "extraction pipeline: transcript %d not found (deleted "
            "before the background task ran?)",
            transcript_id,
        )
        return

    audio_path = row.get("audio_path") or ""
    preview_text = row.get("preview_text")
    language = row.get("language") or "en-US"
    duration_ms = int(row.get("duration_ms") or 0)

    # --- Stage 1: Whisper transcribe (degrade on failure) ---
    whisper_text: Optional[str] = None
    try:
        result = transcribe(
            audio_path, duration_ms=duration_ms, language=language,
        )
        whisper_text = result.text
        segments_json = json.dumps([
            {"start_ms": s.start_ms, "end_ms": s.end_ms, "text": s.text}
            for s in result.segments
        ])
        update_whisper_result(
            transcript_id,
            whisper_transcript=result.text,
            whisper_segments_json=segments_json,
            whisper_cost_usd_cents=result.cost_usd_cents,
            whisper_model=result.model,
            db_path=db_path,
        )
        record_cost_event(
            "whisper", result.model, result.cost_usd_cents,
            transcript_id=transcript_id, shop_id=shop_id,
            units_label="duration_ms", units_value=result.duration_ms,
            db_path=db_path,
        )
        _log.info(
            "transcript %d: whisper ok (%d cents)",
            transcript_id, result.cost_usd_cents,
        )
    except (WhisperUnavailableError, WhisperTranscriptionError) as exc:
        # Degrade — not an extraction failure. Continue with
        # preview_text.
        _log.info(
            "transcript %d: whisper unavailable/failed (%s); "
            "degrading to on-device preview_text",
            transcript_id, exc,
        )

    # --- Stage 2: pick the best transcript text ---
    best_text = whisper_text if whisper_text else preview_text

    # --- Stage 3: keyword extraction over the best text ---
    keyword_phrases = extract_symptoms_from_transcript(best_text)
    symptom_rows: list[dict] = [
        {
            "text": p.text,
            "category": p.category,
            "confidence": p.confidence,
            "extraction_method": "keyword",
        }
        for p in keyword_phrases
    ]

    # --- Stage 4: threshold gate → Claude-rich extraction ---
    final_state = "extracted"
    if should_run_claude_fallback(best_text, keyword_phrases):
        try:
            claude_rows = _run_claude(
                best_text or "", transcript_id, shop_id, db_path,
            )
            symptom_rows.extend(claude_rows)
        except Exception as exc:  # noqa: BLE001
            # Malformed output OR not-configured OR API error — keep
            # the keyword rows, flag the state. Plan v1.0 §2.
            _log.info(
                "transcript %d: claude-fallback failed (%s); "
                "keeping keyword rows, state=extraction_failed",
                transcript_id, exc,
            )
            final_state = "extraction_failed"

    # --- Stage 5: atomic finalize ---
    inserted = finalize_extraction(
        transcript_id, symptom_rows, final_state,
        replace_existing=True, db_path=db_path,
    )
    _log.info(
        "transcript %d: finalized state=%s rows=%d",
        transcript_id, final_state, inserted,
    )


def _run_claude(
    transcript_text: str,
    transcript_id: int,
    shop_id: Optional[int],
    db_path: Optional[str],
) -> list[dict]:
    """Run Claude-rich extraction; record the cost event; return rows.

    Raises on any failure (not-configured, malformed, API error) —
    the caller catches + degrades to keyword-only.
    """
    from motodiag.engine.client import DiagnosticClient

    client = DiagnosticClient(model="haiku")
    symptoms, usage = client.extract_symptoms(
        transcript_text, categories=categories(),
    )
    # TokenUsage.cost_estimate is USD; cost_events stores cents.
    cost_cents = int(round((usage.cost_estimate or 0.0) * 100))
    record_cost_event(
        "claude_extraction", usage.model, cost_cents,
        transcript_id=transcript_id, shop_id=shop_id,
        units_label="tokens",
        units_value=usage.input_tokens + usage.output_tokens,
        db_path=db_path,
    )
    return [
        {
            "text": s["text"],
            "category": s.get("category"),
            "confidence": 1.0,
            "extraction_method": "claude",
        }
        for s in symptoms
    ]


def _finalize_failed_keyword_only(
    transcript_id: int, db_path: Optional[str],
) -> None:
    """Last-resort finalize when the pipeline itself crashed.

    Recomputes keyword rows from whatever transcript text is on the
    row + finalizes ``extraction_failed`` so the transcript never
    hangs in ``extracting``.
    """
    row = get_voice_transcript(transcript_id, db_path=db_path)
    if row is None:
        return
    text = row.get("whisper_transcript") or row.get("preview_text")
    phrases = extract_symptoms_from_transcript(text)
    rows = [
        {
            "text": p.text, "category": p.category,
            "confidence": p.confidence, "extraction_method": "keyword",
        }
        for p in phrases
    ]
    finalize_extraction(
        transcript_id, rows, "extraction_failed",
        replace_existing=True, db_path=db_path,
    )
