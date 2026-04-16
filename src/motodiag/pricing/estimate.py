"""Cost estimation engine — connects diagnostics to pricing."""

from motodiag.pricing.labor_rates import get_labor_rate, get_rate_comparison
from motodiag.pricing.repair_plan import get_plan, get_plan_items


def estimate_issue_cost(
    estimated_hours: float,
    region: str = "national",
    rate_type: str = "independent",
    state: str | None = None,
    db_path: str | None = None,
) -> dict:
    """Estimate the labor cost for a single known issue.

    Returns a dict with rate info and computed cost, or empty dict
    if no rate data is available.
    """
    rate = get_labor_rate(region, rate_type, state, db_path)
    if not rate:
        return {}

    hourly = rate["hourly_rate"]
    return {
        "estimated_hours": estimated_hours,
        "hourly_rate": hourly,
        "labor_cost": round(estimated_hours * hourly, 2),
        "region": rate["region"],
        "state": rate.get("state"),
        "rate_type": rate["rate_type"],
        "source": rate.get("source"),
    }


def estimate_issue_cost_comparison(
    estimated_hours: float,
    region: str = "national",
    state: str | None = None,
    db_path: str | None = None,
) -> list[dict]:
    """Estimate costs across all shop types for comparison.

    Returns a list of estimates (independent, dealership, mobile)
    so the mechanic can show the customer competitive positioning.
    """
    rates = get_rate_comparison(region, state, db_path)
    results = []
    for rate in rates:
        hourly = rate["hourly_rate"]
        results.append({
            "rate_type": rate["rate_type"],
            "hourly_rate": hourly,
            "labor_cost": round(estimated_hours * hourly, 2),
            "region": rate["region"],
            "state": rate.get("state"),
        })
    return results


def get_plan_summary(plan_id: int, db_path: str | None = None) -> dict | None:
    """Get a formatted summary of a repair plan for display.

    Returns a structured dict with grouped line items, subtotals,
    and the total estimate — ready for display or export.
    """
    plan = get_plan(plan_id, db_path)
    if not plan:
        return None

    items = plan.get("items", [])

    # Group items by type
    groups = {
        "diagnostic": [],
        "prep_labor": [],
        "repair_labor": [],
        "parts": [],
        "misc": [],
    }
    for item in items:
        itype = item.get("item_type", "misc")
        if itype in groups:
            groups[itype].append(item)
        else:
            groups["misc"].append(item)

    # Compute subtotals per group
    subtotals = {}
    for group_name, group_items in groups.items():
        if group_items:
            subtotals[group_name] = {
                "count": len(group_items),
                "hours": sum(i.get("labor_hours", 0) for i in group_items),
                "cost": sum(i.get("line_total", 0) for i in group_items),
            }

    return {
        "plan_id": plan["id"],
        "title": plan["title"],
        "status": plan["status"],
        "labor_rate": plan.get("labor_rate_used"),
        "customer_name": plan.get("customer_name"),
        "groups": groups,
        "subtotals": subtotals,
        "total_parts": plan.get("total_parts_cost", 0),
        "total_labor_hours": plan.get("total_labor_hours", 0),
        "total_labor_cost": plan.get("total_labor_cost", 0),
        "total_estimate": plan.get("total_estimate", 0),
        "created_at": plan.get("created_at"),
        "notes": plan.get("notes"),
    }
