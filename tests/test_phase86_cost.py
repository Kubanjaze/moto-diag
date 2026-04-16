"""Phase 86 — Cost estimation tests.

20+ tests covering CostLineItem, CostEstimate, CostEstimator,
compare_shop_types, DIY savings, format_estimate, and edge cases.
All pure logic — no API calls or database needed.
"""

import pytest

from motodiag.engine.cost import (
    LABOR_RATES,
    CostEstimate,
    CostEstimator,
    CostLineItem,
    PartCost,
    ShopType,
    format_estimate,
)
from motodiag.engine.models import DiagnosisItem, DiagnosticSeverity


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def estimator():
    return CostEstimator()


@pytest.fixture
def sample_parts():
    return [
        PartCost(name="Brake pads (front)", cost_low=35.0, cost_high=65.0),
        PartCost(name="Brake fluid DOT4", cost_low=8.0, cost_high=15.0),
    ]


@pytest.fixture
def sample_diagnosis():
    return DiagnosisItem(
        diagnosis="Worn front brake pads causing reduced stopping power",
        confidence=0.85,
        severity=DiagnosticSeverity.HIGH,
        evidence=["Squealing noise", "Thin pad material visible"],
        repair_steps=["Remove caliper", "Replace pads", "Bleed brakes"],
        estimated_hours=1.5,
        parts_needed=["Front brake pads", "Brake fluid DOT4"],
    )


# ---------------------------------------------------------------------------
# CostLineItem model tests
# ---------------------------------------------------------------------------

class TestCostLineItem:
    def test_create_labor_item(self):
        item = CostLineItem(
            description="Labor (1.5 hrs)", category="labor",
            amount_low=120.0, amount_high=150.0,
        )
        assert item.category == "labor"
        assert item.amount_low == 120.0
        assert item.amount_high == 150.0

    def test_create_parts_item(self):
        item = CostLineItem(
            description="Brake pads", category="parts",
            amount_low=35.0, amount_high=65.0,
        )
        assert item.category == "parts"

    def test_create_supplies_item(self):
        item = CostLineItem(
            description="Rags and cleaner", category="supplies",
            amount_low=10.0, amount_high=10.0,
        )
        assert item.category == "supplies"

    def test_invalid_category_rejected(self):
        with pytest.raises(Exception):
            CostLineItem(
                description="Bad", category="unknown",
                amount_low=10.0, amount_high=20.0,
            )

    def test_negative_amount_rejected(self):
        with pytest.raises(Exception):
            CostLineItem(
                description="Negative", category="parts",
                amount_low=-5.0, amount_high=10.0,
            )


# ---------------------------------------------------------------------------
# CostEstimate model tests
# ---------------------------------------------------------------------------

class TestCostEstimate:
    def test_create_estimate(self):
        est = CostEstimate(
            labor_hours=2.0, labor_rate=90.0,
            labor_total_low=160.0, labor_total_high=200.0,
            parts_cost_low=50.0, parts_cost_high=80.0,
            total_low=210.0, total_high=280.0,
            diy_parts_only=50.0,
            diy_savings_low=160.0, diy_savings_high=230.0,
            shop_type=ShopType.INDEPENDENT,
        )
        assert est.labor_hours == 2.0
        assert est.shop_type == ShopType.INDEPENDENT
        assert est.line_items == []

    def test_estimate_with_line_items(self):
        item = CostLineItem(
            description="Test", category="parts",
            amount_low=10.0, amount_high=20.0,
        )
        est = CostEstimate(
            labor_hours=1.0, labor_rate=90.0,
            labor_total_low=80.0, labor_total_high=100.0,
            parts_cost_low=10.0, parts_cost_high=20.0,
            total_low=90.0, total_high=120.0,
            diy_parts_only=10.0,
            diy_savings_low=80.0, diy_savings_high=110.0,
            line_items=[item],
            shop_type=ShopType.INDEPENDENT,
        )
        assert len(est.line_items) == 1

    def test_supplies_default_zero(self):
        est = CostEstimate(
            labor_hours=1.0, labor_rate=90.0,
            labor_total_low=80.0, labor_total_high=100.0,
            total_low=80.0, total_high=100.0,
            diy_parts_only=0.0,
            diy_savings_low=80.0, diy_savings_high=100.0,
            shop_type=ShopType.INDEPENDENT,
        )
        assert est.supplies_cost == 0.0


# ---------------------------------------------------------------------------
# CostEstimator.estimate() tests
# ---------------------------------------------------------------------------

class TestEstimate:
    def test_simple_labor_only(self, estimator):
        est = estimator.estimate(labor_hours=2.0, shop_type=ShopType.INDEPENDENT)
        assert est.labor_hours == 2.0
        assert est.labor_total_low == 160.0  # 2 * 80
        assert est.labor_total_high == 200.0  # 2 * 100
        assert est.parts_cost_low == 0.0
        assert est.total_low == 160.0
        assert est.total_high == 200.0

    def test_with_parts(self, estimator, sample_parts):
        est = estimator.estimate(
            labor_hours=1.0, parts=sample_parts,
            shop_type=ShopType.INDEPENDENT,
        )
        assert est.parts_cost_low == 43.0  # 35 + 8
        assert est.parts_cost_high == 80.0  # 65 + 15
        assert est.total_low == 123.0  # 80 + 43
        assert est.total_high == 180.0  # 100 + 80

    def test_with_supplies(self, estimator, sample_parts):
        est = estimator.estimate(
            labor_hours=1.0, parts=sample_parts,
            shop_type=ShopType.INDEPENDENT, supplies_cost=15.0,
        )
        assert est.supplies_cost == 15.0
        assert est.total_low == 138.0  # 80 + 43 + 15
        assert est.total_high == 195.0  # 100 + 80 + 15

    def test_dealer_rates_higher(self, estimator, sample_parts):
        est = estimator.estimate(
            labor_hours=2.0, parts=sample_parts,
            shop_type=ShopType.DEALER,
        )
        assert est.labor_total_low == 240.0  # 2 * 120
        assert est.labor_total_high == 300.0  # 2 * 150
        assert est.labor_rate == 135.0

    def test_diy_zero_labor(self, estimator, sample_parts):
        est = estimator.estimate(
            labor_hours=2.0, parts=sample_parts,
            shop_type=ShopType.DIY,
        )
        assert est.labor_total_low == 0.0
        assert est.labor_total_high == 0.0
        assert est.total_low == 43.0  # parts only
        assert est.total_high == 80.0

    def test_line_items_generated(self, estimator, sample_parts):
        est = estimator.estimate(
            labor_hours=1.5, parts=sample_parts,
            shop_type=ShopType.INDEPENDENT, supplies_cost=10.0,
        )
        categories = [item.category for item in est.line_items]
        assert "labor" in categories
        assert "parts" in categories
        assert "supplies" in categories
        assert len(est.line_items) == 4  # 1 labor + 2 parts + 1 supplies

    def test_diy_no_labor_line_item(self, estimator, sample_parts):
        est = estimator.estimate(
            labor_hours=2.0, parts=sample_parts,
            shop_type=ShopType.DIY,
        )
        categories = [item.category for item in est.line_items]
        assert "labor" not in categories


# ---------------------------------------------------------------------------
# DIY savings tests
# ---------------------------------------------------------------------------

class TestDIYSavings:
    def test_diy_savings_calculation(self, estimator, sample_parts):
        est = estimator.estimate(
            labor_hours=2.0, parts=sample_parts,
            shop_type=ShopType.INDEPENDENT,
        )
        # diy_parts_only = parts_cost_low + supplies = 43 + 0
        assert est.diy_parts_only == 43.0
        # savings = total - diy_parts_only
        assert est.diy_savings_low == est.total_low - est.diy_parts_only
        assert est.diy_savings_high == est.total_high - est.diy_parts_only

    def test_diy_savings_with_supplies(self, estimator, sample_parts):
        est = estimator.estimate(
            labor_hours=1.0, parts=sample_parts,
            shop_type=ShopType.DEALER, supplies_cost=20.0,
        )
        # DIY still pays for parts + supplies
        assert est.diy_parts_only == 63.0  # 43 + 20
        assert est.diy_savings_low == est.total_low - est.diy_parts_only

    def test_diy_shop_type_zero_savings(self, estimator, sample_parts):
        est = estimator.estimate(
            labor_hours=2.0, parts=sample_parts,
            shop_type=ShopType.DIY,
        )
        assert est.diy_savings_low == 0.0
        assert est.diy_savings_high == 0.0


# ---------------------------------------------------------------------------
# compare_shop_types() tests
# ---------------------------------------------------------------------------

class TestCompareShopTypes:
    def test_returns_three_estimates(self, estimator, sample_parts):
        comparison = estimator.compare_shop_types(
            labor_hours=2.0, parts=sample_parts,
        )
        assert len(comparison) == 3
        assert ShopType.DEALER in comparison
        assert ShopType.INDEPENDENT in comparison
        assert ShopType.DIY in comparison

    def test_dealer_most_expensive(self, estimator, sample_parts):
        comparison = estimator.compare_shop_types(
            labor_hours=2.0, parts=sample_parts,
        )
        assert comparison[ShopType.DEALER].total_high > comparison[ShopType.INDEPENDENT].total_high
        assert comparison[ShopType.INDEPENDENT].total_high > comparison[ShopType.DIY].total_high

    def test_parts_same_across_types(self, estimator, sample_parts):
        comparison = estimator.compare_shop_types(
            labor_hours=2.0, parts=sample_parts,
        )
        for est in comparison.values():
            assert est.parts_cost_low == 43.0
            assert est.parts_cost_high == 80.0

    def test_diy_cheapest(self, estimator, sample_parts):
        comparison = estimator.compare_shop_types(
            labor_hours=3.0, parts=sample_parts,
        )
        diy = comparison[ShopType.DIY]
        assert diy.labor_total_low == 0.0
        assert diy.total_low == diy.parts_cost_low


# ---------------------------------------------------------------------------
# estimate_from_diagnosis() tests
# ---------------------------------------------------------------------------

class TestEstimateFromDiagnosis:
    def test_uses_diagnosis_hours(self, estimator, sample_diagnosis):
        parts = [
            PartCost(name="Front brake pads", cost_low=35.0, cost_high=65.0),
            PartCost(name="Brake fluid DOT4", cost_low=8.0, cost_high=15.0),
        ]
        est = estimator.estimate_from_diagnosis(
            sample_diagnosis, parts_with_costs=parts,
        )
        assert est.labor_hours == 1.5

    def test_no_parts_costs_defaults_zero(self, estimator, sample_diagnosis):
        est = estimator.estimate_from_diagnosis(sample_diagnosis)
        assert est.parts_cost_low == 0.0
        assert est.parts_cost_high == 0.0
        # But parts names should still appear as line items
        parts_items = [i for i in est.line_items if i.category == "parts"]
        assert len(parts_items) == 2  # Two parts_needed in diagnosis

    def test_diagnosis_without_hours(self, estimator):
        diag = DiagnosisItem(
            diagnosis="Minor cosmetic issue",
            confidence=0.6,
            severity=DiagnosticSeverity.LOW,
            estimated_hours=None,
        )
        est = estimator.estimate_from_diagnosis(diag)
        assert est.labor_hours == 0.0
        assert est.labor_total_low == 0.0


# ---------------------------------------------------------------------------
# format_estimate() tests
# ---------------------------------------------------------------------------

class TestFormatEstimate:
    def test_format_contains_shop_type(self, estimator, sample_parts):
        est = estimator.estimate(
            labor_hours=1.5, parts=sample_parts,
            shop_type=ShopType.INDEPENDENT,
        )
        text = format_estimate(est)
        assert "Independent" in text

    def test_format_contains_total(self, estimator, sample_parts):
        est = estimator.estimate(
            labor_hours=1.0, parts=sample_parts,
            shop_type=ShopType.INDEPENDENT,
        )
        text = format_estimate(est)
        assert "TOTAL" in text

    def test_format_contains_diy_savings(self, estimator, sample_parts):
        est = estimator.estimate(
            labor_hours=2.0, parts=sample_parts,
            shop_type=ShopType.DEALER,
        )
        text = format_estimate(est)
        assert "DIY savings" in text

    def test_format_diy_no_savings_line(self, estimator, sample_parts):
        est = estimator.estimate(
            labor_hours=2.0, parts=sample_parts,
            shop_type=ShopType.DIY,
        )
        text = format_estimate(est)
        assert "DIY savings" not in text


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_zero_hours(self, estimator):
        est = estimator.estimate(labor_hours=0.0, shop_type=ShopType.INDEPENDENT)
        assert est.labor_total_low == 0.0
        assert est.total_low == 0.0

    def test_zero_parts_cost(self, estimator):
        est = estimator.estimate(labor_hours=1.0, parts=[], shop_type=ShopType.INDEPENDENT)
        assert est.parts_cost_low == 0.0

    def test_very_high_estimate(self, estimator):
        expensive_parts = [
            PartCost(name="Engine rebuild kit", cost_low=2000.0, cost_high=4000.0),
            PartCost(name="Cylinder boring", cost_low=500.0, cost_high=800.0),
        ]
        est = estimator.estimate(
            labor_hours=20.0, parts=expensive_parts,
            shop_type=ShopType.DEALER,
        )
        assert est.total_high > 7000.0  # 20*150 + 4800 = 7800

    def test_custom_rates(self):
        custom = {
            "dealer": {"low": 200.0, "high": 250.0, "avg": 225.0},
            "independent": {"low": 100.0, "high": 120.0, "avg": 110.0},
            "diy": {"low": 0.0, "high": 0.0, "avg": 0.0},
        }
        est = CostEstimator(custom_rates=custom)
        result = est.estimate(labor_hours=1.0, shop_type=ShopType.DEALER)
        assert result.labor_total_low == 200.0
        assert result.labor_total_high == 250.0

    def test_labor_rates_dict_has_expected_keys(self):
        assert "dealer" in LABOR_RATES
        assert "independent" in LABOR_RATES
        assert "diy" in LABOR_RATES
        assert "national_average" in LABOR_RATES
        for key in ["low", "high", "avg"]:
            assert key in LABOR_RATES["dealer"]
