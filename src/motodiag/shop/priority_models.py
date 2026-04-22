"""Pydantic models for Phase 163 AI repair priority scoring.

Kept in a separate module from `priority_scorer.py` so tests can import
the schemas without pulling in the (mockable) Anthropic SDK seam.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


RidabilityImpact = Literal["none", "low", "med", "high"]
SeverityTier = Literal[1, 2, 3, 4, 5]


class PriorityScorerInput(BaseModel):
    """Serialized snapshot of everything the AI scorer needs for one WO."""

    model_config = ConfigDict(extra="ignore")

    wo_id: int
    title: str
    description: Optional[str] = None
    current_priority: int = Field(ge=1, le=5)
    wait_hours: float = Field(ge=0.0)
    vehicle_year: Optional[int] = None
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    issues: list[dict] = Field(default_factory=list)
    known_issue_matches: list[dict] = Field(default_factory=list)
    rubric_floor: int = Field(ge=1, le=5)
    customer_prior_ticket_count_12mo: int = Field(default=0, ge=0)


class PriorityScoreResponse(BaseModel):
    """Exact JSON shape the AI must return."""

    model_config = ConfigDict(extra="ignore")

    priority: SeverityTier
    rationale: str = Field(min_length=8, max_length=400)
    confidence: float = Field(ge=0.0, le=1.0)
    safety_risk: bool
    ridability_impact: RidabilityImpact
    computed_score: Optional[float] = None


class PriorityScore(BaseModel):
    """Full record persisted to ai_response_cache + returned to callers."""

    model_config = ConfigDict(extra="ignore")

    wo_id: int
    priority_before: int = Field(ge=1, le=5)
    priority_after: int = Field(ge=1, le=5)
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)
    safety_risk: bool
    ridability_impact: RidabilityImpact
    computed_score: Optional[float] = None
    ai_model: str
    cost_cents: int = Field(ge=0)
    tokens_in: int = Field(ge=0)
    tokens_out: int = Field(ge=0)
    cache_hit: bool = False
    generated_at: datetime
    applied: bool = False
