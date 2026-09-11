"""Phase 244N — keep the sweep that a re-analysis used to destroy.

``set_analysis_findings`` ran ``UPDATE videos SET analysis_findings = ?``. One
blob per video, no history, so re-analysing a video deleted everything the
previous sweep had found.

That is not hypothetical. Commit ``d2c23f8`` -- *"Preserve session 6's pre-244B
sweep before overwriting it"* -- exists because a sweep had to be rescued into
git by hand before a re-run, and git was the only place it could be put.

**The `videos.analysis_findings` column is not changed.** It keeps holding the
current sweep in the same shape, so Phase 244M's compile, the API responses and
the reports all keep reading it exactly as before. It stops being the *only*
copy and becomes a pointer to the latest one.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from motodiag.core.database import get_connection

_log = logging.getLogger(__name__)


def record_analysis(
    video_id: int,
    findings_json: str,
    *,
    model_used: Optional[str] = None,
    cost_usd_cents: Optional[int] = None,
    frames_analyzed: Optional[int] = None,
    analyzed_at: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Optional[int]:
    """Append a sweep to the video's history. Returns the row id, or None.

    Marks every prior un-superseded analysis for this video as superseded
    **before** inserting, so "the current one" is unambiguous at every instant
    and a crash between the two statements leaves no second current row.

    Never raises. A history write that fails an analysis has destroyed the
    thing it was meant to preserve.
    """
    try:
        with get_connection(db_path) as conn:
            conn.execute(
                "UPDATE video_analyses SET superseded_at = datetime('now') "
                "WHERE video_id = ? AND superseded_at IS NULL",
                (video_id,),
            )
            cursor = conn.execute(
                """
                INSERT INTO video_analyses
                    (video_id, findings_json, model_used, cost_usd_cents,
                     frames_analyzed, analyzed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    video_id,
                    findings_json,
                    model_used,
                    cost_usd_cents,
                    frames_analyzed,
                    analyzed_at,
                ),
            )
            return cursor.lastrowid
    except Exception as exc:
        _log.warning("Analysis history not recorded for video %s: %s", video_id, exc)
        return None


def _row(r) -> dict:
    return {
        "id": r[0],
        "video_id": r[1],
        "findings": json.loads(r[2]) if r[2] else None,
        "model_used": r[3],
        "cost_usd_cents": r[4],
        "frames_analyzed": r[5],
        "analyzed_at": r[6],
        "superseded_at": r[7],
    }


_SELECT = (
    "SELECT id, video_id, findings_json, model_used, cost_usd_cents, "
    "       frames_analyzed, analyzed_at, superseded_at "
    "FROM video_analyses"
)


def list_analyses(
    video_id: int,
    *,
    db_path: Optional[str] = None,
) -> list[dict]:
    """Every sweep recorded for a video, newest first."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            f"{_SELECT} WHERE video_id = ? ORDER BY id DESC", (video_id,)
        ).fetchall()
    return [_row(r) for r in rows]


def current_analysis(
    video_id: int,
    *,
    db_path: Optional[str] = None,
) -> Optional[dict]:
    """The sweep that has not been superseded, if there is one."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            f"{_SELECT} WHERE video_id = ? AND superseded_at IS NULL "
            "ORDER BY id DESC LIMIT 1",
            (video_id,),
        ).fetchone()
    return _row(row) if row is not None else None
