"""FeedbackReader — read-only hook for Track R learning phases.

Phase 116: exposes pure-read accessors over diagnostic_feedback and
session_overrides so Track R phases 318-327 (human-in-loop learning,
continuous learning, repair success prediction) can pull feedback history
without coupling to the write path. No side effects.
"""

from datetime import datetime
from typing import Iterator, Optional

from motodiag.core.database import get_connection
from motodiag.feedback.feedback_repo import (
    count_feedback_by_outcome, _row_to_feedback,
)
from motodiag.feedback.models import FeedbackOutcome


class FeedbackReader:
    """Read-only interface over feedback data.

    Track R builds the actual learning loop on top of this. Adding methods
    here is fine; adding writes is a design violation — feedback_repo owns
    all writes.
    """

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path

    def iter_feedback(
        self,
        since: Optional[datetime] = None,
        outcome: FeedbackOutcome | str | None = None,
    ) -> Iterator[dict]:
        """Yield feedback rows in chronological order (oldest first).

        Streams via a generator so Track R can process large histories
        without loading everything into memory.
        """
        query = "SELECT * FROM diagnostic_feedback WHERE 1=1"
        params: list = []
        if since is not None:
            query += " AND submitted_at >= ?"
            params.append(since.isoformat())
        if outcome is not None:
            out_val = outcome.value if isinstance(outcome, FeedbackOutcome) else outcome
            query += " AND outcome = ?"
            params.append(out_val)
        query += " ORDER BY submitted_at, id"

        with get_connection(self.db_path) as conn:
            cursor = conn.execute(query, params)
            for row in cursor.fetchall():
                yield _row_to_feedback(row)

    def get_accuracy_metrics(self) -> dict:
        """Summarize AI accuracy over all submitted feedback.

        Returns:
            {
                'total': int,
                'correct': int, 'partially_correct': int,
                'incorrect': int, 'inconclusive': int,
                'correct_ratio': float,     # correct / total
                'partial_plus_correct_ratio': float,  # (correct + partial) / total
            }
        """
        counts = count_feedback_by_outcome(self.db_path)
        total = sum(counts.values())
        correct = counts.get(FeedbackOutcome.CORRECT.value, 0)
        partial = counts.get(FeedbackOutcome.PARTIALLY_CORRECT.value, 0)

        correct_ratio = round(correct / total, 4) if total > 0 else 0.0
        partial_ratio = round((correct + partial) / total, 4) if total > 0 else 0.0

        return {
            "total": total,
            "correct": correct,
            "partially_correct": partial,
            "incorrect": counts.get(FeedbackOutcome.INCORRECT.value, 0),
            "inconclusive": counts.get(FeedbackOutcome.INCONCLUSIVE.value, 0),
            "correct_ratio": correct_ratio,
            "partial_plus_correct_ratio": partial_ratio,
        }

    def get_common_overrides(self, top_n: int = 5) -> list[dict]:
        """Top-N most-overridden fields across all sessions.

        Returns list of {field_name, count} sorted by count desc.
        """
        with get_connection(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT field_name, COUNT(*) as c FROM session_overrides "
                "GROUP BY field_name ORDER BY c DESC LIMIT ?",
                (top_n,),
            )
            return [{"field_name": row[0], "count": row[1]} for row in cursor.fetchall()]
