"""Subscription tier system — 3-tier access control for MotoDiag.

Phase 109: Foundational subscription infrastructure. Three tiers:
- INDIVIDUAL: single mechanic, personal use, 5 vehicles, basic diagnostics
- SHOP: small/medium shop, multi-mechanic, 50 vehicles, team features
- COMPANY: multi-location, unlimited vehicles, API access, fleet management

Tier enforcement happens at the CLI layer before commands execute. All
downstream Track D/H/I phases will use this system. Real payment integration
is out of scope — this provides the architecture for it.
"""

import os
from enum import Enum
from functools import wraps
from typing import Callable, Optional

from pydantic import BaseModel, Field


class SubscriptionTier(str, Enum):
    """MotoDiag subscription tiers, ordered from lowest to highest privilege."""
    INDIVIDUAL = "individual"
    SHOP = "shop"
    COMPANY = "company"

    @property
    def rank(self) -> int:
        """Numeric rank for comparison. Higher = more privileged."""
        return {"individual": 1, "shop": 2, "company": 3}[self.value]

    def meets_minimum(self, required: "SubscriptionTier") -> bool:
        """Check if this tier meets or exceeds the required tier."""
        return self.rank >= required.rank


class TierFeatures(BaseModel):
    """Feature flags and limits for a subscription tier."""
    tier: SubscriptionTier = Field(..., description="The tier these features belong to")
    display_name: str = Field(..., description="Human-readable tier name")
    price_monthly_usd: float = Field(default=0.0, description="Monthly price in USD (placeholder)")
    price_yearly_usd: float = Field(default=0.0, description="Yearly price in USD (placeholder)")

    # Usage limits
    max_vehicles: int = Field(..., description="Max vehicles in garage. -1 = unlimited.")
    max_sessions_per_month: int = Field(..., description="Max diagnostic sessions per month. -1 = unlimited.")
    max_users: int = Field(default=1, description="Max users/accounts. -1 = unlimited.")
    max_locations: int = Field(default=1, description="Max physical locations. -1 = unlimited.")

    # Feature access
    can_export_pdf: bool = Field(default=False, description="Export reports to PDF")
    can_share_reports: bool = Field(default=False, description="Share diagnostic reports with customers")
    can_use_media_diagnostics: bool = Field(default=False, description="Audio/video diagnostic features")
    can_use_api: bool = Field(default=False, description="REST API access")
    can_manage_team: bool = Field(default=False, description="Team/user management")
    can_customize_branding: bool = Field(default=False, description="Custom branding on reports")
    can_access_shop_management: bool = Field(default=False, description="Shop management features (work orders, scheduling)")
    priority_support: bool = Field(default=False, description="Priority customer support")

    # AI limits
    ai_model_access: list[str] = Field(default_factory=lambda: ["haiku"], description="Available AI models")
    ai_monthly_cost_cap_usd: float = Field(default=5.0, description="Monthly AI API cost cap in USD")


# --- Tier definitions (pricing is placeholder — user confirmed it can change) ---

TIER_LIMITS: dict[SubscriptionTier, TierFeatures] = {
    SubscriptionTier.INDIVIDUAL: TierFeatures(
        tier=SubscriptionTier.INDIVIDUAL,
        display_name="Solo Mechanic",
        price_monthly_usd=19.00,
        price_yearly_usd=190.00,
        max_vehicles=5,
        max_sessions_per_month=50,
        max_users=1,
        max_locations=1,
        can_export_pdf=False,
        can_share_reports=False,
        can_use_media_diagnostics=True,
        can_use_api=False,
        can_manage_team=False,
        can_customize_branding=False,
        can_access_shop_management=False,
        priority_support=False,
        ai_model_access=["haiku"],
        ai_monthly_cost_cap_usd=5.0,
    ),
    SubscriptionTier.SHOP: TierFeatures(
        tier=SubscriptionTier.SHOP,
        display_name="Shop (per location)",
        price_monthly_usd=99.00,
        price_yearly_usd=990.00,
        max_vehicles=50,
        max_sessions_per_month=500,
        max_users=10,
        max_locations=1,
        can_export_pdf=True,
        can_share_reports=True,
        can_use_media_diagnostics=True,
        can_use_api=False,
        can_manage_team=True,
        can_customize_branding=True,
        can_access_shop_management=True,
        priority_support=False,
        ai_model_access=["haiku", "sonnet"],
        ai_monthly_cost_cap_usd=50.0,
    ),
    SubscriptionTier.COMPANY: TierFeatures(
        tier=SubscriptionTier.COMPANY,
        display_name="Multi-Location / Enterprise",
        price_monthly_usd=299.00,
        price_yearly_usd=2990.00,
        max_vehicles=-1,         # unlimited
        max_sessions_per_month=-1,
        max_users=-1,
        max_locations=-1,
        can_export_pdf=True,
        can_share_reports=True,
        can_use_media_diagnostics=True,
        can_use_api=True,
        can_manage_team=True,
        can_customize_branding=True,
        can_access_shop_management=True,
        priority_support=True,
        ai_model_access=["haiku", "sonnet"],
        ai_monthly_cost_cap_usd=500.0,
    ),
}


def current_tier() -> SubscriptionTier:
    """Get the current subscription tier from env or config.

    Priority: MOTODIAG_SUBSCRIPTION_TIER env var > settings.subscription_tier > INDIVIDUAL default.
    """
    # Env override (useful for testing)
    env_tier = os.environ.get("MOTODIAG_SUBSCRIPTION_TIER", "").lower()
    if env_tier in ("individual", "shop", "company"):
        return SubscriptionTier(env_tier)

    # TODO: eventually pull from settings or backend API
    # For now, default to INDIVIDUAL
    return SubscriptionTier.INDIVIDUAL


def get_tier_features(tier: Optional[SubscriptionTier] = None) -> TierFeatures:
    """Get features for the specified tier, or the current tier if not specified."""
    tier = tier or current_tier()
    return TIER_LIMITS[tier]


def has_feature(feature_name: str, tier: Optional[SubscriptionTier] = None) -> bool:
    """Check if the specified tier (or current) has a specific feature flag."""
    features = get_tier_features(tier)
    return bool(getattr(features, feature_name, False))


# Enforcement modes — see project_motodiag_paywall_strategy memory
# SOFT (dev default): warn but allow. HARD (Track H+): raise TierAccessDenied.
ENFORCEMENT_MODE_SOFT = "soft"
ENFORCEMENT_MODE_HARD = "hard"


def get_enforcement_mode() -> str:
    """Return the current enforcement mode.

    During Tracks D-G (development): soft (warn only).
    At Track H (API + billing): hard (block + redirect to upgrade).

    Override with MOTODIAG_PAYWALL_MODE env var ("soft" or "hard").
    """
    mode = os.environ.get("MOTODIAG_PAYWALL_MODE", "").lower()
    if mode in (ENFORCEMENT_MODE_SOFT, ENFORCEMENT_MODE_HARD):
        return mode
    return ENFORCEMENT_MODE_SOFT  # Development default


def requires_tier(minimum: SubscriptionTier, feature_name: Optional[str] = None) -> Callable:
    """Decorator that gates a CLI command by minimum subscription tier.

    Usage:
        @requires_tier(SubscriptionTier.SHOP)
        def export_pdf(): ...

        @requires_tier(SubscriptionTier.SHOP, feature_name="can_export_pdf")
        def export_pdf(): ...

    Behavior depends on MOTODIAG_PAYWALL_MODE:
      - "soft" (default during dev): prints upgrade warning but allows execution
      - "hard" (Track H+): raises TierAccessDenied
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_tier = current_tier()
            if not user_tier.meets_minimum(minimum):
                mode = get_enforcement_mode()
                feat = feature_name or func.__name__
                if mode == ENFORCEMENT_MODE_HARD:
                    raise TierAccessDenied(
                        required_tier=minimum,
                        current_tier=user_tier,
                        feature_name=feat,
                    )
                # Soft mode: warn but continue
                import sys
                sys.stderr.write(
                    f"[motodiag] ⚠ Feature '{feat}' is gated to {minimum.value} tier or higher "
                    f"(you have {user_tier.value}). Allowed in dev mode. "
                    f"Upgrade: https://motodiag.app/pricing\n"
                )
            return func(*args, **kwargs)
        wrapper._required_tier = minimum  # type: ignore[attr-defined]
        wrapper._feature_name = feature_name  # type: ignore[attr-defined]
        return wrapper
    return decorator


class TierAccessDenied(Exception):
    """Raised when the current subscription tier doesn't meet a command's minimum."""

    def __init__(
        self,
        required_tier: SubscriptionTier,
        current_tier: SubscriptionTier,
        feature_name: str = "",
    ):
        self.required_tier = required_tier
        self.current_tier_val = current_tier
        self.feature_name = feature_name
        super().__init__(
            f"Feature '{feature_name}' requires {required_tier.value} tier "
            f"(you have {current_tier.value}). Upgrade at https://motodiag.app/pricing"
        )


def format_tier_comparison() -> str:
    """Return a formatted text table comparing all three tiers."""
    individual = TIER_LIMITS[SubscriptionTier.INDIVIDUAL]
    shop = TIER_LIMITS[SubscriptionTier.SHOP]
    company = TIER_LIMITS[SubscriptionTier.COMPANY]

    def fmt_limit(n: int) -> str:
        return "Unlimited" if n == -1 else str(n)

    def fmt_bool(b: bool) -> str:
        return "✓" if b else "—"

    lines = [
        "┌─────────────────────────────┬──────────────┬──────────────┬──────────────┐",
        "│ Feature                     │ Individual   │ Shop         │ Company      │",
        "├─────────────────────────────┼──────────────┼──────────────┼──────────────┤",
        f"│ Monthly price               │ ${individual.price_monthly_usd:>11.2f} │ ${shop.price_monthly_usd:>11.2f} │ ${company.price_monthly_usd:>11.2f} │",
        f"│ Yearly price                │ ${individual.price_yearly_usd:>11.2f} │ ${shop.price_yearly_usd:>11.2f} │ ${company.price_yearly_usd:>11.2f} │",
        f"│ Max vehicles                │ {fmt_limit(individual.max_vehicles):>12} │ {fmt_limit(shop.max_vehicles):>12} │ {fmt_limit(company.max_vehicles):>12} │",
        f"│ Sessions/month              │ {fmt_limit(individual.max_sessions_per_month):>12} │ {fmt_limit(shop.max_sessions_per_month):>12} │ {fmt_limit(company.max_sessions_per_month):>12} │",
        f"│ Max users                   │ {fmt_limit(individual.max_users):>12} │ {fmt_limit(shop.max_users):>12} │ {fmt_limit(company.max_users):>12} │",
        f"│ Export PDF                  │ {fmt_bool(individual.can_export_pdf):>12} │ {fmt_bool(shop.can_export_pdf):>12} │ {fmt_bool(company.can_export_pdf):>12} │",
        f"│ Share reports               │ {fmt_bool(individual.can_share_reports):>12} │ {fmt_bool(shop.can_share_reports):>12} │ {fmt_bool(company.can_share_reports):>12} │",
        f"│ Media diagnostics           │ {fmt_bool(individual.can_use_media_diagnostics):>12} │ {fmt_bool(shop.can_use_media_diagnostics):>12} │ {fmt_bool(company.can_use_media_diagnostics):>12} │",
        f"│ API access                  │ {fmt_bool(individual.can_use_api):>12} │ {fmt_bool(shop.can_use_api):>12} │ {fmt_bool(company.can_use_api):>12} │",
        f"│ Team management             │ {fmt_bool(individual.can_manage_team):>12} │ {fmt_bool(shop.can_manage_team):>12} │ {fmt_bool(company.can_manage_team):>12} │",
        f"│ Shop management             │ {fmt_bool(individual.can_access_shop_management):>12} │ {fmt_bool(shop.can_access_shop_management):>12} │ {fmt_bool(company.can_access_shop_management):>12} │",
        f"│ Priority support            │ {fmt_bool(individual.priority_support):>12} │ {fmt_bool(shop.priority_support):>12} │ {fmt_bool(company.priority_support):>12} │",
        "└─────────────────────────────┴──────────────┴──────────────┴──────────────┘",
    ]
    return "\n".join(lines)
