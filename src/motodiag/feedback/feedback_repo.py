"""Feedback repository — CRUD for diagnostic_feedback and session_overrides.

Phase 116: feedback records are effectively immutable once submitted —
no update/delete API is exposed to preserve training signal integrity.
"""

import json
from typing import Optional

from motodiag.core.database import get_connection
from motodiag.feedback.models import (
    DiagnosticFeedback, SessionOverride, FeedbackOutcome, OverrideField,
)


# --- DiagnosticFeedback ---


def submit_feedback(feedback: DiagnosticFeedback, db_path: str | None = None) -> int:
    """Insert a feedback record. Returns the new row id."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO diagnostic_feedback
               (session_id, submitted_by_user_id, ai_suggested_diagnosis,
                ai_confidence, actual_diagnosis, actual_fix, outcome,
                mechanic_notes, parts_used, actual_labor_hours)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                feedback.session_id, feedback.submitted_by_user_id,
                feedback.ai_suggested_diagnosis, feedback.ai_confidence,
                feedback.actual_diagnosis, feedback.actual_fix,
                feedback.outcome.value, feedback.mechanic_notes,
                json.dumps(feedback.parts_used), feedback.actual_labor_hours,
            ),
        )
        return cursor.lastrowid


def _row_to_feedback(row) -> dict:
    d = dict(row)
    if d.get("parts_used"):
        try:
            d["parts_used"] = json.loads(d["parts_used"])
        except (json.JSONDecodeError, TypeError):
            d["parts_used"] = []
    else:
        d["parts_used"] = []
    return d


def get_feedback(feedback_id: int, db_path: str | None = None) -> Optional[dict]:
    """Fetch a feedback row by id."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM diagnostic_feedback WHERE id = ?", (feedback_id,),
        )
        row = cursor.fetchone()
        return _row_to_feedback(row) if row else None


def get_feedback_for_session(session_id: int, db_path: str | None = None) -> list[dict]:
    """Fetch all feedback rows for a session, ordered by submitted_at."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM diagnostic_feedback WHERE session_id = ? "
            "ORDER BY submitted_at, id",
            (session_id,),
        )
        return [_row_to_feedback(r) for r in cursor.fetchall()]


def list_feedback(
    outcome: FeedbackOutcome | str | None = None,
    user_id: int | None = None,
    limit: int | None = None,
    db_path: str | None = None,
) -> list[dict]:
    """List feedback rows with optional outcome/user filters."""
    query = "SELECT * FROM diagnostic_feedback WHERE 1=1"
    params: list = []
    if outcome is not None:
        out_val = outcome.value if isinstance(outcome, FeedbackOutcome) else outcome
        query += " AND outcome = ?"
        params.append(out_val)
    if user_id is not None:
        query += " AND submitted_by_user_id = ?"
        params.append(user_id)
    query += " ORDER BY submitted_at DESC, id DESC"
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)
    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [_row_to_feedback(r) for r in cursor.fetchall()]


def count_feedback_by_outcome(db_path: str | None = None) -> dict[str, int]:
    """Return {outcome_value: count} for all 4 outcomes, including zeros."""
    counts = {o.value: 0 for o in FeedbackOutcome}
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT outcome, COUNT(*) FROM diagnostic_feedback GROUP BY outcome"
        )
        for row in cursor.fetchall():
            counts[row[0]] = row[1]
    return counts


# --- SessionOverride ---


def record_override(override: SessionOverride, db_path: str | None = None) -> int:
    """Record a field-level override. Returns the new row id."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO session_overrides
               (session_id, field_name, ai_value, override_value,
                overridden_by_user_id, reason)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                override.session_id, override.field_name.value,
                override.ai_value, override.override_value,
                override.overridden_by_user_id, override.reason,
            ),
        )
        return cursor.lastrowid


def get_overrides_for_session(session_id: int, db_path: str | None = None) -> list[dict]:
    """Fetch all overrides for a session, ordered by overridden_at."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM session_overrides WHERE session_id = ? "
            "ORDER BY overridden_at, id",
            (session_id,),
        )
        return [dict(r) for r in cursor.fetchall()]


def count_overrides_for_field(
    field: OverrideField | str, db_path: str | None = None,
) -> int:
    """Count how many times a given field has been overridden across all sessions."""
    fval = field.value if isinstance(field, OverrideField) else field
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM session_overrides WHERE field_name = ?",
            (fval,),
        )
        return cursor.fetchone()[0]
