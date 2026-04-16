"""Tests for the pricing/repair plan module."""

import pytest
from motodiag.core.database import init_db
from motodiag.core.config import DATA_DIR
from motodiag.knowledge.loader import load_known_issues_file
from motodiag.pricing.labor_rates import (
    add_labor_rate, get_labor_rate, get_rate_comparison,
    list_all_rates, load_labor_rates_file,
)
from motodiag.pricing.repair_plan import (
    create_plan, get_plan, update_plan, delete_plan, list_plans,
    add_item, update_item, remove_item, get_plan_items,
    create_plan_from_issues, add_prep_labor_to_plan,
    load_prep_labor_file, list_prep_labor,
)
from motodiag.pricing.estimate import (
    estimate_issue_cost, estimate_issue_cost_comparison, get_plan_summary,
)


@pytest.fixture
def db_path(tmp_path):
    """Fresh database with labor rates and some known issues loaded."""
    path = str(tmp_path / "test.db")
    init_db(path)

    # Load labor rates
    rates_file = DATA_DIR / "pricing" / "labor_rates.json"
    if rates_file.exists():
        load_labor_rates_file(rates_file, path)

    # Load prep labor catalog
    prep_file = DATA_DIR / "pricing" / "prep_labor.json"
    if prep_file.exists():
        load_prep_labor_file(prep_file, path)

    # Load some known issues for plan-from-issues tests
    issues_file = DATA_DIR / "knowledge" / "known_issues_harley_cross_era.json"
    if issues_file.exists():
        load_known_issues_file(issues_file, path)

    return path


# ---------------------------------------------------------------------------
# Labor rate tests
# ---------------------------------------------------------------------------

class TestLaborRates:
    def test_load_rates(self, db_path):
        rates = list_all_rates(db_path)
        assert len(rates) >= 20

    def test_get_national_independent(self, db_path):
        rate = get_labor_rate("national", "independent", db_path=db_path)
        assert rate is not None
        assert rate["hourly_rate"] == 95.00

    def test_get_national_dealership(self, db_path):
        rate = get_labor_rate("national", "dealership", db_path=db_path)
        assert rate is not None
        assert rate["hourly_rate"] == 135.00

    def test_state_override(self, db_path):
        rate = get_labor_rate("west", "independent", state="CA", db_path=db_path)
        assert rate is not None
        assert rate["hourly_rate"] == 130.00  # CA premium

    def test_fallback_to_regional(self, db_path):
        rate = get_labor_rate("southeast", "independent", state="GA", db_path=db_path)
        # GA has no state-specific rate, falls to southeast regional
        assert rate is not None
        assert rate["hourly_rate"] == 85.00

    def test_rate_comparison(self, db_path):
        rates = get_rate_comparison("national", db_path=db_path)
        assert len(rates) == 3  # independent, dealership, mobile
        types = {r["rate_type"] for r in rates}
        assert types == {"independent", "dealership", "mobile"}


# ---------------------------------------------------------------------------
# Repair plan CRUD tests
# ---------------------------------------------------------------------------

class TestRepairPlanCRUD:
    def test_create_plan(self, db_path):
        plan_id = create_plan(
            title="2005 Sportster — full service",
            labor_rate=95.00,
            customer_name="John Doe",
            db_path=db_path,
        )
        assert plan_id > 0

    def test_get_plan(self, db_path):
        plan_id = create_plan(title="Test Plan", labor_rate=100.00, db_path=db_path)
        plan = get_plan(plan_id, db_path)
        assert plan is not None
        assert plan["title"] == "Test Plan"
        assert plan["status"] == "draft"
        assert plan["labor_rate_used"] == 100.00
        assert plan["items"] == []

    def test_update_plan(self, db_path):
        plan_id = create_plan(title="Draft Plan", labor_rate=90.00, db_path=db_path)
        updated = update_plan(plan_id, {"status": "quoted"}, db_path)
        assert updated is True
        plan = get_plan(plan_id, db_path)
        assert plan["status"] == "quoted"

    def test_delete_plan(self, db_path):
        plan_id = create_plan(title="Delete Me", labor_rate=90.00, db_path=db_path)
        assert delete_plan(plan_id, db_path) is True
        assert get_plan(plan_id, db_path) is None

    def test_list_plans(self, db_path):
        create_plan(title="Plan A", labor_rate=90.00, db_path=db_path)
        create_plan(title="Plan B", labor_rate=90.00, db_path=db_path)
        plans = list_plans(db_path=db_path)
        assert len(plans) >= 2

    def test_list_plans_by_status(self, db_path):
        pid = create_plan(title="Quoted Plan", labor_rate=90.00, db_path=db_path)
        update_plan(pid, {"status": "quoted"}, db_path)
        create_plan(title="Draft Plan", labor_rate=90.00, db_path=db_path)
        quoted = list_plans(status="quoted", db_path=db_path)
        assert len(quoted) >= 1
        assert all(p["status"] == "quoted" for p in quoted)


# ---------------------------------------------------------------------------
# Line item tests
# ---------------------------------------------------------------------------

class TestLineItems:
    def test_add_labor_item(self, db_path):
        plan_id = create_plan(title="Labor Test", labor_rate=100.00, db_path=db_path)
        item_id = add_item(
            plan_id=plan_id,
            item_type="repair_labor",
            title="Replace regulator/rectifier",
            labor_hours=1.0,
            db_path=db_path,
        )
        assert item_id > 0
        plan = get_plan(plan_id, db_path)
        assert plan["total_labor_hours"] == 1.0
        assert plan["total_labor_cost"] == 100.00
        assert plan["total_estimate"] == 100.00

    def test_add_parts_item(self, db_path):
        plan_id = create_plan(title="Parts Test", labor_rate=100.00, db_path=db_path)
        add_item(
            plan_id=plan_id,
            item_type="parts",
            title="MOSFET regulator",
            quantity=1.0,
            unit_cost=65.00,
            db_path=db_path,
        )
        plan = get_plan(plan_id, db_path)
        assert plan["total_parts_cost"] == 65.00
        assert plan["total_estimate"] == 65.00

    def test_mixed_items_total(self, db_path):
        plan_id = create_plan(title="Mixed Test", labor_rate=100.00, db_path=db_path)
        add_item(plan_id=plan_id, item_type="repair_labor",
                 title="Repair", labor_hours=2.0, db_path=db_path)
        add_item(plan_id=plan_id, item_type="parts",
                 title="Part A", quantity=1, unit_cost=50.00, db_path=db_path)
        add_item(plan_id=plan_id, item_type="prep_labor",
                 title="Remove fairings", labor_hours=1.0, db_path=db_path)

        plan = get_plan(plan_id, db_path)
        assert plan["total_labor_hours"] == 3.0  # 2.0 repair + 1.0 prep
        assert plan["total_labor_cost"] == 300.00  # 3 hours * $100
        assert plan["total_parts_cost"] == 50.00
        assert plan["total_estimate"] == 350.00

    def test_remove_item_recalculates(self, db_path):
        plan_id = create_plan(title="Remove Test", labor_rate=100.00, db_path=db_path)
        item_id = add_item(plan_id=plan_id, item_type="repair_labor",
                           title="To remove", labor_hours=2.0, db_path=db_path)
        add_item(plan_id=plan_id, item_type="repair_labor",
                 title="Keep", labor_hours=1.0, db_path=db_path)

        remove_item(item_id, db_path)
        plan = get_plan(plan_id, db_path)
        assert plan["total_labor_hours"] == 1.0
        assert plan["total_estimate"] == 100.00

    def test_add_prep_labor(self, db_path):
        plan_id = create_plan(title="Prep Test", labor_rate=95.00, db_path=db_path)
        item_id = add_prep_labor_to_plan(
            plan_id=plan_id,
            prep_name="Remove fairings — full sport bike",
            prep_hours=1.0,
            prep_description="Full fairing removal on CBR600RR",
            db_path=db_path,
        )
        assert item_id > 0
        items = get_plan_items(plan_id, db_path)
        assert len(items) == 1
        assert items[0]["item_type"] == "prep_labor"
        assert items[0]["labor_hours"] == 1.0


# ---------------------------------------------------------------------------
# Create plan from issues (the "click through" workflow)
# ---------------------------------------------------------------------------

class TestPlanFromIssues:
    def test_create_from_issues(self, db_path):
        # Get some known issue IDs (loaded from harley_cross_era.json)
        from motodiag.knowledge.issues_repo import search_known_issues
        issues = search_known_issues(db_path=db_path)
        assert len(issues) >= 2

        issue_ids = [issues[0]["id"], issues[1]["id"]]
        plan_id = create_plan_from_issues(
            title="2005 Sportster — diagnosed issues",
            issue_ids=issue_ids,
            labor_rate=95.00,
            db_path=db_path,
        )

        plan = get_plan(plan_id, db_path)
        assert plan is not None
        assert plan["status"] == "draft"
        assert plan["total_labor_hours"] > 0
        assert plan["total_estimate"] > 0
        # Should have diagnostic + 2 repair labor items + parts + test ride
        assert len(plan["items"]) >= 4


# ---------------------------------------------------------------------------
# Estimate engine tests
# ---------------------------------------------------------------------------

class TestEstimate:
    def test_estimate_issue_cost(self, db_path):
        result = estimate_issue_cost(2.0, "national", "independent", db_path=db_path)
        assert result["labor_cost"] == 190.00  # 2h * $95
        assert result["hourly_rate"] == 95.00

    def test_estimate_comparison(self, db_path):
        results = estimate_issue_cost_comparison(2.0, "national", db_path=db_path)
        assert len(results) == 3
        # Independent should be cheapest
        independent = next(r for r in results if r["rate_type"] == "independent")
        dealership = next(r for r in results if r["rate_type"] == "dealership")
        assert independent["labor_cost"] < dealership["labor_cost"]

    def test_plan_summary(self, db_path):
        plan_id = create_plan(title="Summary Test", labor_rate=100.00, db_path=db_path)
        add_item(plan_id=plan_id, item_type="diagnostic",
                 title="Scan", labor_hours=0.5, db_path=db_path)
        add_item(plan_id=plan_id, item_type="prep_labor",
                 title="Remove fairings", labor_hours=1.0, db_path=db_path)
        add_item(plan_id=plan_id, item_type="repair_labor",
                 title="Replace reg/rec", labor_hours=1.0, db_path=db_path)
        add_item(plan_id=plan_id, item_type="parts",
                 title="MOSFET reg/rec", quantity=1, unit_cost=65.00, db_path=db_path)

        summary = get_plan_summary(plan_id, db_path)
        assert summary is not None
        assert summary["total_estimate"] == 315.00  # (0.5+1.0+1.0)*$100 + $65
        assert "diagnostic" in summary["subtotals"]
        assert "prep_labor" in summary["subtotals"]
        assert "repair_labor" in summary["subtotals"]
        assert "parts" in summary["subtotals"]


# ---------------------------------------------------------------------------
# Prep labor catalog tests
# ---------------------------------------------------------------------------

class TestPrepLaborCatalog:
    def test_load_catalog(self, db_path):
        items = list_prep_labor(db_path=db_path)
        assert len(items) >= 15

    def test_filter_by_category(self, db_path):
        access_items = list_prep_labor(category="access", db_path=db_path)
        assert len(access_items) >= 5
        assert all(i["category"] == "access" for i in access_items)

    def test_diagnostic_items(self, db_path):
        diag_items = list_prep_labor(category="diagnostic", db_path=db_path)
        assert len(diag_items) >= 2
