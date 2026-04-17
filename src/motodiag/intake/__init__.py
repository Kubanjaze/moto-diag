"""Intake package — photo-based vehicle identification substrate.

Phase 122: VehicleIdentifier wraps Claude Vision (Haiku 4.5 with Sonnet
fallback) to turn a motorcycle photo into an approximate VehicleGuess
(make, model, year_range, engine_cc_range, confidence). Quota-enforced
per tier via intake_usage_log table; sha256 image cache avoids re-burn
on accidental re-uploads. Image bytes never persist.
"""

from motodiag.intake.models import (
    IdentifyKind,
    VehicleGuess,
    IntakeUsageEntry,
    IntakeQuota,
    IntakeError,
    QuotaExceededError,
)
from motodiag.intake.vehicle_identifier import (
    VehicleIdentifier,
    MONTHLY_CAPS,
    BUDGET_ALERT_THRESHOLD,
    SONNET_ESCALATION_THRESHOLD,
    HAIKU_MODEL_ID,
    SONNET_MODEL_ID,
)

__all__ = [
    "IdentifyKind",
    "VehicleGuess",
    "IntakeUsageEntry",
    "IntakeQuota",
    "IntakeError",
    "QuotaExceededError",
    "VehicleIdentifier",
    "MONTHLY_CAPS",
    "BUDGET_ALERT_THRESHOLD",
    "SONNET_ESCALATION_THRESHOLD",
    "HAIKU_MODEL_ID",
    "SONNET_MODEL_ID",
]
