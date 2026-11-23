"""Subscription tier system — 3-tier access control for MotoDiag.

Phase 109: Foundational subscription infrastructure. Three tiers, named
and limited as the operator set them in Phase 404 (K84):
- INDIVIDUAL ("Individual: for your own bikes"): 5 bikes, $5 of AI a month
- SHOP ("Shop"): no bike limit, team features, $50 of AI a month
- COMPANY ("Company"): no bike limit, 3 locations, API access, $150 of AI
  a month

The server keeps the bike limit (``vehicles.registry.TIER_VEHICLE_LIMITS``),
the diagnosis limit (``core.session_repo.TIER_SESSION_MONTHLY_LIMITS``) and
the AI figure, per shop per calendar month (``shop.cost_cap.PLAN_AI_CENTS``);
``tests/test_phase404_*`` hold this table equal to them. Locations and
people are shown here and kept nowhere.

Tier enforcement happens at the CLI layer before commands execute. All
downstream Track D/H/I phases will use this system. Real payment integration
is out of scope — this provides the architecture for it.
"""

import os
from enum import Enum
from typing import Optional

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

    # Phase 293 (K119, K123): what the shop's uploaded manuals may take, in
    # bytes (GB = 1024**3), counting the files and never their page images.
    manual_storage_bytes: int = Field(
        ..., description="Manual storage for the shop's uploaded files, in bytes")


# --- Tier definitions (pricing is placeholder — user confirmed it can change) ---

TIER_LIMITS: dict[SubscriptionTier, TierFeatures] = {
    SubscriptionTier.INDIVIDUAL: TierFeatures(
        tier=SubscriptionTier.INDIVIDUAL,
        display_name="Individual: for your own bikes",
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
        manual_storage_bytes=2 * 1024**3,
    ),
    SubscriptionTier.SHOP: TierFeatures(
        tier=SubscriptionTier.SHOP,
        display_name="Shop",
        price_monthly_usd=99.00,
        price_yearly_usd=990.00,
        max_vehicles=-1,         # unlimited (Phase 404, F270)
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
        manual_storage_bytes=20 * 1024**3,
    ),
    SubscriptionTier.COMPANY: TierFeatures(
        tier=SubscriptionTier.COMPANY,
        display_name="Company",
        price_monthly_usd=299.00,
        price_yearly_usd=2990.00,
        max_vehicles=-1,         # unlimited
        max_sessions_per_month=-1,
        max_users=-1,
        max_locations=3,         # shown, kept nowhere (Phase 404, F271)
        can_export_pdf=True,
        can_share_reports=True,
        can_use_media_diagnostics=True,
        can_use_api=True,
        can_manage_team=True,
        can_customize_branding=True,
        can_access_shop_management=True,
        priority_support=True,
        ai_model_access=["haiku", "sonnet"],
        ai_monthly_cost_cap_usd=150.0,
        manual_storage_bytes=50 * 1024**3,  # one shop's until its shops are linked (F271)
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



# Enforcement modes — see project_motodiag_paywall_strategy memory
# SOFT (dev default): warn but allow. HARD (Track H+): enforced API-side; the CLI-side raise was removed at Phase 244Y.
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



def format_tier_comparison() -> str:
    """Return a formatted text table comparing all three tiers."""
    individual = TIER_LIMITS[SubscriptionTier.INDIVIDUAL]
    shop = TIER_LIMITS[SubscriptionTier.SHOP]
    company = TIER_LIMITS[SubscriptionTier.COMPANY]

    def fmt_limit(n: int) -> str:
        return "Unlimited" if n == -1 else str(n)

    def fmt_bool(b: bool) -> str:
        return "✓" if b else "—"

    # Phase 404 (F272): every plan name comes from ``display_name``. The full
    # names ride on a line across the table; each column is headed by the
    # name's first part, which fits the column.
    tiers = (individual, shop, company)
    names = "Plans: " + " · ".join(t.display_name for t in tiers)
    heads = [t.display_name.split(":")[0] for t in tiers]

    lines = [
        "┌" + "─" * 74 + "┐",
        f"│ {names:<72} │",
        "├─────────────────────────────┬──────────────┬──────────────┬──────────────┤",
        f"│ Feature                     │ {heads[0]:<12} │ {heads[1]:<12} │ {heads[2]:<12} │",
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
