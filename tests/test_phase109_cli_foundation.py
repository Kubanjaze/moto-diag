"""Phase 109 — CLI foundation + subscription tier tests."""

import os
from unittest.mock import patch

from motodiag.cli.subscription import (
    SubscriptionTier,
    TIER_LIMITS,
    current_tier,
    format_tier_comparison,
)


# --- SubscriptionTier enum ---


class TestSubscriptionTier:
    def test_three_tiers_exist(self):
        tiers = list(SubscriptionTier)
        assert len(tiers) == 3
        assert SubscriptionTier.INDIVIDUAL in tiers
        assert SubscriptionTier.SHOP in tiers
        assert SubscriptionTier.COMPANY in tiers

    def test_tier_ranks(self):
        assert SubscriptionTier.INDIVIDUAL.rank == 1
        assert SubscriptionTier.SHOP.rank == 2
        assert SubscriptionTier.COMPANY.rank == 3

    def test_rank_ordering(self):
        assert SubscriptionTier.COMPANY.rank > SubscriptionTier.SHOP.rank
        assert SubscriptionTier.SHOP.rank > SubscriptionTier.INDIVIDUAL.rank

    def test_meets_minimum_same_tier(self):
        assert SubscriptionTier.SHOP.meets_minimum(SubscriptionTier.SHOP)

    def test_meets_minimum_higher_tier(self):
        assert SubscriptionTier.COMPANY.meets_minimum(SubscriptionTier.SHOP)
        assert SubscriptionTier.COMPANY.meets_minimum(SubscriptionTier.INDIVIDUAL)

    def test_meets_minimum_lower_tier(self):
        assert not SubscriptionTier.INDIVIDUAL.meets_minimum(SubscriptionTier.SHOP)
        assert not SubscriptionTier.SHOP.meets_minimum(SubscriptionTier.COMPANY)


# --- TierFeatures and TIER_LIMITS ---


class TestTierFeatures:
    def test_individual_tier_features(self):
        features = TIER_LIMITS[SubscriptionTier.INDIVIDUAL]
        assert features.tier == SubscriptionTier.INDIVIDUAL
        assert features.price_monthly_usd == 19.00
        assert features.max_vehicles == 5
        assert features.max_users == 1
        assert features.can_export_pdf is False
        assert features.can_use_api is False

    def test_shop_tier_features(self):
        features = TIER_LIMITS[SubscriptionTier.SHOP]
        assert features.tier == SubscriptionTier.SHOP
        assert features.price_monthly_usd == 99.00
        assert features.max_vehicles == 50
        assert features.max_users == 10
        assert features.can_export_pdf is True
        assert features.can_share_reports is True
        assert features.can_manage_team is True

    def test_company_tier_features(self):
        features = TIER_LIMITS[SubscriptionTier.COMPANY]
        assert features.tier == SubscriptionTier.COMPANY
        assert features.price_monthly_usd == 299.00
        assert features.max_vehicles == -1  # unlimited
        assert features.max_users == -1
        assert features.max_locations == -1
        assert features.can_use_api is True
        assert features.priority_support is True

    def test_ai_model_access_escalates(self):
        """Higher tiers should have access to more AI models."""
        individual = TIER_LIMITS[SubscriptionTier.INDIVIDUAL]
        shop = TIER_LIMITS[SubscriptionTier.SHOP]
        company = TIER_LIMITS[SubscriptionTier.COMPANY]

        assert "haiku" in individual.ai_model_access
        assert "sonnet" in shop.ai_model_access
        assert "sonnet" in company.ai_model_access

    def test_cost_caps_escalate(self):
        individual = TIER_LIMITS[SubscriptionTier.INDIVIDUAL]
        shop = TIER_LIMITS[SubscriptionTier.SHOP]
        company = TIER_LIMITS[SubscriptionTier.COMPANY]
        assert shop.ai_monthly_cost_cap_usd > individual.ai_monthly_cost_cap_usd
        assert company.ai_monthly_cost_cap_usd > shop.ai_monthly_cost_cap_usd

    def test_pricing_escalates(self):
        individual = TIER_LIMITS[SubscriptionTier.INDIVIDUAL]
        shop = TIER_LIMITS[SubscriptionTier.SHOP]
        company = TIER_LIMITS[SubscriptionTier.COMPANY]
        assert shop.price_monthly_usd > individual.price_monthly_usd
        assert company.price_monthly_usd > shop.price_monthly_usd


# --- current_tier() ---


class TestCurrentTier:
    def test_default_is_individual(self):
        with patch.dict(os.environ, {}, clear=True):
            assert current_tier() == SubscriptionTier.INDIVIDUAL

    def test_env_override_shop(self):
        with patch.dict(os.environ, {"MOTODIAG_SUBSCRIPTION_TIER": "shop"}):
            assert current_tier() == SubscriptionTier.SHOP

    def test_env_override_company(self):
        with patch.dict(os.environ, {"MOTODIAG_SUBSCRIPTION_TIER": "company"}):
            assert current_tier() == SubscriptionTier.COMPANY

    def test_env_case_insensitive(self):
        with patch.dict(os.environ, {"MOTODIAG_SUBSCRIPTION_TIER": "SHOP"}):
            assert current_tier() == SubscriptionTier.SHOP

    def test_invalid_env_falls_back_to_default(self):
        with patch.dict(os.environ, {"MOTODIAG_SUBSCRIPTION_TIER": "enterprise"}):
            assert current_tier() == SubscriptionTier.INDIVIDUAL


# --- has_feature() ---



# --- requires_tier decorator ---



# --- format_tier_comparison ---


class TestFormatTierComparison:
    def test_comparison_table_contains_all_tiers(self):
        output = format_tier_comparison()
        assert "Individual" in output
        assert "Shop" in output
        assert "Company" in output

    def test_comparison_contains_pricing(self):
        output = format_tier_comparison()
        assert "$19.00" in output or "19.00" in output
        assert "$99.00" in output or "99.00" in output
        assert "$299.00" in output or "299.00" in output

    def test_comparison_contains_feature_names(self):
        output = format_tier_comparison()
        assert "API" in output or "api" in output.lower()
        assert "PDF" in output or "Export" in output


# --- CommandRegistry ---



