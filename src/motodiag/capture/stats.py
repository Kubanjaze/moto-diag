"""Phase 244N — how much ground truth actually exists.

The point of this module is to make "we don't have enough data yet" a **number**
rather than a feeling. Phase 244M shipped a memory whose most valuable compile
path had nothing to compile, and the reason took a Step 0 audit to find. A
count on a screen would have shown it immediately.
"""

from __future__ import annotations

from typing import Optional

from motodiag.core.database import get_connection


def _count(conn, table: str, where: str = "") -> int:
    try:
        clause = f" WHERE {where}" if where else ""
        return conn.execute(f"SELECT COUNT(*) FROM {table}{clause}").fetchone()[0]
    except Exception:
        # A table absent at this install's schema version is 0, not an error.
        return 0


def capture_stats(db_path: Optional[str] = None) -> dict:
    """Counts per capture stream, plus what they are counted against."""
    with get_connection(db_path) as conn:
        interactions = _count(conn, "guidance_interactions")
        unanswered = _count(
            conn, "guidance_interactions", "answers_the_question = 0"
        )
        answered = _count(
            conn, "guidance_interactions", "answers_the_question = 1"
        )
        overrides = _count(conn, "session_overrides")
        feedback = _count(conn, "diagnostic_feedback")
        analyses = _count(conn, "video_analyses")
        superseded = _count(conn, "video_analyses", "superseded_at IS NOT NULL")

        sessions = _count(conn, "diagnostic_sessions")
        ai_sessions = _count(
            conn, "diagnostic_sessions", "ai_model_used IS NOT NULL"
        )
        videos = _count(conn, "videos", "analysis_findings IS NOT NULL")

    return {
        "guidance_interactions": interactions,
        "guidance_answered": answered,
        "guidance_unanswered": unanswered,
        "session_overrides": overrides,
        "diagnostic_feedback": feedback,
        "video_analyses": analyses,
        "video_analyses_superseded": superseded,
        # Denominators. A capture count alone cannot say whether capture is
        # working: 0 overrides against 0 AI-authored sessions is nothing to
        # correct, while 0 against 40 is a broken hook.
        "sessions_total": sessions,
        "sessions_ai_authored": ai_sessions,
        "videos_with_findings": videos,
    }
