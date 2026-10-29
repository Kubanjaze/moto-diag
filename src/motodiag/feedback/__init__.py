"""Feedback package — diagnostic feedback + override tracking + learning hooks.

Phase 116 (Retrofit): introduces diagnostic_feedback and session_overrides
tables plus the read-only FeedbackReader hook interface. Track R phases
318-327 build the actual learning loop on top of this substrate.
"""

from motodiag.feedback.feedback_repo import (
    count_feedback_by_outcome,
    count_overrides_for_field,
    get_feedback,
    get_feedback_for_session,
    get_overrides_for_session,
    list_feedback,
    record_override,
    submit_feedback,
)
from motodiag.feedback.learning_hook import FeedbackReader
from motodiag.feedback.models import (
    DiagnosticFeedback,
    FeedbackOutcome,
    OverrideField,
    SessionOverride,
)

__all__ = [
    "FeedbackOutcome", "OverrideField", "DiagnosticFeedback", "SessionOverride",
    "submit_feedback", "get_feedback", "get_feedback_for_session", "list_feedback",
    "count_feedback_by_outcome", "record_override", "get_overrides_for_session",
    "count_overrides_for_field",
    "FeedbackReader",
]
