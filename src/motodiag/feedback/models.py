"""Feedback package Pydantic models.

Phase 116: DiagnosticFeedback captures what actually went wrong vs what
the AI suggested. SessionOverride records field-level disagreements
(e.g., mechanic changed the diagnosis or severity).
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class FeedbackOutcome(str, Enum):
    """Overall feedback outcome — AI accuracy signal."""
    CORRECT = "correct"
    PARTIALLY_CORRECT = "partially_correct"
    INCORRECT = "incorrect"
    INCONCLUSIVE = "inconclusive"


class OverrideField(str, Enum):
    """Session fields that can be overridden by the mechanic."""
    DIAGNOSIS = "diagnosis"
    SEVERITY = "severity"
    COST_ESTIMATE = "cost_estimate"
    CONFIDENCE = "confidence"
    REPAIR_STEPS = "repair_steps"
    PARTS = "parts"


class DiagnosticFeedback(BaseModel):
    """Post-diagnosis feedback captured from the mechanic.

    One feedback record per session; session_id FKs diagnostic_sessions.
    parts_used is a free-form list of part names/numbers actually installed.
    """
    id: Optional[int] = None
    session_id: int = Field(..., description="FK diagnostic_sessions.id")
    submitted_by_user_id: int = Field(
        default=1, description="FK users.id — defaults to system user"
    )
    ai_suggested_diagnosis: Optional[str] = Field(
        None, description="What the AI engine suggested at session close"
    )
    ai_confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="AI confidence at session close"
    )
    actual_diagnosis: Optional[str] = Field(
        None, description="What the mechanic actually determined"
    )
    actual_fix: Optional[str] = Field(
        None, description="The repair procedure applied"
    )
    outcome: FeedbackOutcome = Field(
        ..., description="Overall accuracy judgement"
    )
    mechanic_notes: Optional[str] = None
    parts_used: list[str] = Field(default_factory=list)
    actual_labor_hours: Optional[float] = Field(None, ge=0.0)
    submitted_at: Optional[datetime] = None


class SessionOverride(BaseModel):
    """A single field override on a diagnostic session."""
    id: Optional[int] = None
    session_id: int = Field(..., description="FK diagnostic_sessions.id")
    field_name: OverrideField = Field(..., description="Which field was overridden")
    ai_value: Optional[str] = Field(None, description="Value the AI produced (stringified)")
    override_value: Optional[str] = Field(None, description="Value the mechanic set (stringified)")
    overridden_by_user_id: int = Field(default=1, description="FK users.id")
    reason: Optional[str] = Field(None, description="Why the mechanic overrode")
    overridden_at: Optional[datetime] = None
