"""Intake package Pydantic models + exceptions.

Phase 122: VehicleGuess captures a photo-based vehicle ID result with
year/engine ranges (visual ID rarely nails a single year or exact cc).
IntakeUsageEntry records per-call usage for quota + cost reporting.
IntakeQuota is a derived view showing current tier usage.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class IdentifyKind(str, Enum):
    """What kind of intake action was logged.

    - IDENTIFY: a vision API call (Haiku or Sonnet) that burned tokens
    - MANUAL_ADD: a hand-entered vehicle (logged for analytics, zero tokens)
    """
    IDENTIFY = "identify"
    MANUAL_ADD = "manual_add"


class VehicleGuess(BaseModel):
    """Result of a photo-based vehicle identification."""
    make: str = Field(..., description="Manufacturer (e.g., 'Honda', 'Harley-Davidson')")
    model: str = Field(..., description="Model name (e.g., 'CBR929RR', 'Sportster 1200')")
    year_range: tuple[int, int] = Field(
        ...,
        description="Likely model year range (low, high). Visual ID rarely nails one MY.",
    )
    engine_cc_range: Optional[tuple[int, int]] = Field(
        None,
        description="Likely displacement range in cc. None for electric (no ICE cc).",
    )
    powertrain_guess: str = Field(
        default="ice",
        description="Powertrain: 'ice', 'electric', or 'hybrid'",
    )
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str = Field(
        default="",
        description="Brief rationale (tank badge, engine layout, fairing silhouette, etc.)",
    )
    model_used: str = Field(
        default="haiku",
        description="Which Claude model produced this guess — 'haiku' or 'sonnet'",
    )
    image_hash: str = Field(
        default="",
        description="sha256 of the preprocessed image bytes (post-resize)",
    )
    cached: bool = Field(
        default=False,
        description="True if this result came from the hash cache (zero tokens burned)",
    )
    alert: Optional[str] = Field(
        default=None,
        description="Budget alert message if this call crossed the 80% threshold",
    )


class IntakeUsageEntry(BaseModel):
    """A single row from intake_usage_log."""
    id: Optional[int] = None
    user_id: int
    kind: IdentifyKind
    model_used: Optional[str] = None
    confidence: Optional[float] = None
    image_hash: Optional[str] = None
    tokens_input: int = 0
    tokens_output: int = 0
    cost_cents: int = 0
    created_at: Optional[datetime] = None


class IntakeQuota(BaseModel):
    """Current-month quota status for a user."""
    tier: str = Field(..., description="Subscription tier: individual, shop, or company")
    monthly_limit: Optional[int] = Field(
        None,
        description="Identify calls per calendar month. None = unlimited (company tier).",
    )
    used_this_month: int = Field(default=0, ge=0)
    remaining: Optional[int] = Field(
        None,
        description="monthly_limit - used_this_month, or None if unlimited.",
    )
    percent_used: float = Field(default=0.0, ge=0.0)


# --- Exceptions ---


class IntakeError(Exception):
    """Generic intake-layer error (bad response, API failure, malformed JSON)."""


class QuotaExceededError(IntakeError):
    """Raised when a user has hit their monthly identify quota.

    Carries tier + used/limit for a human-readable CLI message.
    """

    def __init__(self, tier: str, used: int, limit: int) -> None:
        self.tier = tier
        self.used = used
        self.limit = limit
        super().__init__(
            f"Monthly photo-ID quota exhausted for {tier} tier: {used}/{limit}. "
            f"Upgrade to the next tier for more IDs."
        )
