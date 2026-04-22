"""Pydantic models for Phase 166 AI parts sourcing.

Separated from `parts_sourcing.py` so tests + Phase 169 invoicing
can import schemas without pulling the SDK seam.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


SourceTier = Literal["oem", "aftermarket", "used", "superseded"]
TierPreference = Literal["oem", "aftermarket", "used", "balanced"]
Availability = Literal["in_stock", "3-5_days", "backorder", "discontinued"]


class VendorSuggestion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    url: Optional[str] = None
    rough_price_cents: int = Field(ge=0)
    availability: Availability
    notes: Optional[str] = None


class SourcingRecommendation(BaseModel):
    """Full record persisted to sourcing_recommendations + returned to callers."""

    model_config = ConfigDict(extra="ignore")

    part_id: int
    quantity: int = Field(default=1, ge=1)
    source_tier: SourceTier
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=8, max_length=2000)
    estimated_cost_cents: int = Field(default=0, ge=0)
    risk_notes: Optional[str] = None
    alternative_parts: list[int] = Field(default_factory=list)
    vendor_suggestions: list[VendorSuggestion] = Field(
        default_factory=list, max_length=5,
    )
    ai_model: str
    tokens_in: int = Field(default=0, ge=0)
    tokens_out: int = Field(default=0, ge=0)
    cost_cents: int = Field(default=0, ge=0)
    cache_hit: bool = False
    batch_id: Optional[str] = None
    generated_at: datetime
