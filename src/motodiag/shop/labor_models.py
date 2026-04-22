"""Pydantic models for Phase 167 AI labor time estimation."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


SkillTier = Literal["apprentice", "journeyman", "master"]
ReconcileBucket = Literal["under", "within", "over"]


class LaborStep(BaseModel):
    model_config = ConfigDict(extra="ignore")

    step_name: str
    step_hours: float = Field(ge=0.0, le=50.0)
    tools_needed: list[str] = Field(default_factory=list)


class AlternativeEstimate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    scenario_name: str
    hours: float = Field(ge=0.0, le=100.0)
    notes: str = ""


class LaborEstimate(BaseModel):
    """Persisted record + AI response shape for Phase 167."""

    model_config = ConfigDict(extra="ignore")

    wo_id: int
    base_hours: float = Field(ge=0.0, le=100.0)
    adjusted_hours: float = Field(ge=0.0, le=100.0)
    skill_adjustment: float = Field(ge=-1.0, le=2.0)
    mileage_adjustment: float = Field(ge=-0.5, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1, max_length=2000)
    breakdown: list[LaborStep] = Field(default_factory=list)
    alternative_estimates: list[AlternativeEstimate] = Field(default_factory=list)
    skill_tier: SkillTier = "journeyman"
    environment_notes: Optional[str] = Field(default=None, max_length=500)
    ai_model: str
    tokens_in: int = Field(default=0, ge=0)
    tokens_out: int = Field(default=0, ge=0)
    cost_cents: int = Field(default=0, ge=0)
    prompt_cache_hit: bool = False
    generated_at: datetime


class ReconciliationReport(BaseModel):
    model_config = ConfigDict(extra="ignore")

    wo_id: int
    estimated_hours: float
    actual_hours: float
    delta_hours: float
    delta_pct: Optional[float] = None
    bucket: ReconcileBucket
    notes: str
