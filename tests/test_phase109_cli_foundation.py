"""Phase 109 — CLI foundation + subscription tier tests."""

import os
import pytest
from unittest.mock import patch

from motodiag.cli.subscription import (
    SubscriptionTier,
    TierFeatures,
    TIER_LIMITS,
    current_tier,
    get_tier_features,
    has_feature,
    requires_tier,
    TierAccessDenied,
    format_tier_comparison,
)
from motodiag.cli.registry import (
    CommandInfo,
    CommandRegistry,
    get_registry,
    register_command,
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


class TestHasFeature:
    def test_individual_lacks_export_pdf(self):
        assert has_feature("can_export_pdf", SubscriptionTier.INDIVIDUAL) is False

    def test_shop_has_export_pdf(self):
        assert has_feature("can_export_pdf", SubscriptionTier.SHOP) is True

    def test_company_has_api_access(self):
        assert has_feature("can_use_api", SubscriptionTier.COMPANY) is True

    def test_shop_lacks_api_access(self):
        assert has_feature("can_use_api", SubscriptionTier.SHOP) is False

    def test_unknown_feature_returns_false(self):
        assert has_feature("can_teleport", SubscriptionTier.COMPANY) is False


# --- requires_tier decorator ---


class TestRequiresTier:
    def test_allowed_tier_passes(self):
        @requires_tier(SubscriptionTier.INDIVIDUAL)
        def my_command():
            return "success"

        with patch.dict(os.environ, {"MOTODIAG_SUBSCRIPTION_TIER": "shop"}):
            assert my_command() == "success"

    def test_exact_tier_passes(self):
        @requires_tier(SubscriptionTier.SHOP)
        def my_command():
            return "success"

        with patch.dict(os.environ, {"MOTODIAG_SUBSCRIPTION_TIER": "shop"}):
            assert my_command() == "success"

    def test_insufficient_tier_hard_mode_raises(self):
        @requires_tier(SubscriptionTier.SHOP)
        def my_command():
            return "success"

        with patch.dict(os.environ, {
            "MOTODIAG_SUBSCRIPTION_TIER": "individual",
            "MOTODIAG_PAYWALL_MODE": "hard",
        }):
            with pytest.raises(TierAccessDenied):
                my_command()

    def test_insufficient_tier_soft_mode_warns_but_allows(self):
        """Soft mode (dev default) allows execution with a warning."""
        @requires_tier(SubscriptionTier.SHOP)
        def my_command():
            return "success"

        with patch.dict(os.environ, {
            "MOTODIAG_SUBSCRIPTION_TIER": "individual",
            "MOTODIAG_PAYWALL_MODE": "soft",
        }):
            # Should NOT raise — should return success
            assert my_command() == "success"

    def test_default_mode_is_soft(self):
        """With no MOTODIAG_PAYWALL_MODE set, default is soft (dev mode)."""
        @requires_tier(SubscriptionTier.COMPANY)
        def premium():
            return "allowed in dev"

        with patch.dict(os.environ, {"MOTODIAG_SUBSCRIPTION_TIER": "individual"}, clear=True):
            # No paywall mode set → soft by default
            assert premium() == "allowed in dev"

    def test_company_tier_required_hard_mode(self):
        @requires_tier(SubscriptionTier.COMPANY, feature_name="api_access")
        def api_command():
            return "ok"

        with patch.dict(os.environ, {
            "MOTODIAG_SUBSCRIPTION_TIER": "shop",
            "MOTODIAG_PAYWALL_MODE": "hard",
        }):
            with pytest.raises(TierAccessDenied) as exc_info:
                api_command()
            assert "api_access" in str(exc_info.value)

    def test_exception_includes_tier_info(self):
        @requires_tier(SubscriptionTier.COMPANY)
        def premium_cmd():
            pass

        with patch.dict(os.environ, {
            "MOTODIAG_SUBSCRIPTION_TIER": "individual",
            "MOTODIAG_PAYWALL_MODE": "hard",
        }):
            with pytest.raises(TierAccessDenied) as exc_info:
                premium_cmd()
            assert exc_info.value.required_tier == SubscriptionTier.COMPANY
            assert exc_info.value.current_tier_val == SubscriptionTier.INDIVIDUAL


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


class TestCommandRegistry:
    def test_empty_registry(self):
        reg = CommandRegistry()
        assert reg.count() == 0
        assert reg.list_commands() == []

    def test_register_command(self):
        reg = CommandRegistry()

        def my_cmd():
            return "hi"

        reg.register("test", my_cmd, description="A test", group="main", added_in_phase=109)
        assert reg.count() == 1
        assert reg.is_registered("test")
        info = reg.get("test")
        assert info is not None
        assert info.name == "test"
        assert info.description == "A test"

    def test_get_callback(self):
        reg = CommandRegistry()

        def my_cmd():
            return "hello"

        reg.register("greet", my_cmd)
        cb = reg.get_callback("greet")
        assert cb is not None
        assert cb() == "hello"

    def test_list_by_group(self):
        reg = CommandRegistry()
        reg.register("a", lambda: None, group="main")
        reg.register("b", lambda: None, group="main")
        reg.register("c", lambda: None, group="admin")

        main = reg.list_commands(group="main")
        admin = reg.list_commands(group="admin")
        assert len(main) == 2
        assert len(admin) == 1

    def test_groups(self):
        reg = CommandRegistry()
        reg.register("a", lambda: None, group="main")
        reg.register("b", lambda: None, group="diagnostic")
        reg.register("c", lambda: None, group="admin")
        assert set(reg.groups()) == {"main", "diagnostic", "admin"}

    def test_clear(self):
        reg = CommandRegistry()
        reg.register("a", lambda: None)
        reg.clear()
        assert reg.count() == 0

    def test_register_with_tier_requirement(self):
        reg = CommandRegistry()
        reg.register("premium", lambda: None, required_tier="shop")
        info = reg.get("premium")
        assert info.required_tier == "shop"


class TestGlobalRegistry:
    def test_global_registry_is_singleton(self):
        reg1 = get_registry()
        reg2 = get_registry()
        assert reg1 is reg2

    def test_register_command_decorator(self):
        # Use a fresh registry state for isolation
        reg = get_registry()
        initial_count = reg.count()

        @register_command("phase109_test_cmd", description="Test", added_in_phase=109)
        def _test_cmd():
            return "test_result"

        assert reg.is_registered("phase109_test_cmd")
        info = reg.get("phase109_test_cmd")
        assert info.added_in_phase == 109

        # Clean up to avoid polluting other tests
        reg._commands.pop("phase109_test_cmd", None)
        reg._callbacks.pop("phase109_test_cmd", None)
