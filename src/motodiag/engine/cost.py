"""Cost estimation engine — pure calculation logic for repair cost estimates.

Phase 86: Takes labor hours, parts lists, and shop type to produce
structured cost estimates with low/high ranges and DIY savings.
No API calls or database access required.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from motodiag.engine.models import DiagnosisItem


class ShopType(str, Enum):
    """Type of repair shop — determines labor rate."""
    DEALER = "dealer"
    INDEPENDENT = "independent"
    DIY = "diy"


# Labor rate ranges by shop type (USD/hr)
# Based on 2024-2025 national averages for motorcycle repair
LABOR_RATES: dict[str, dict[str, float]] = {
    "dealer": {"low": 120.0, "high": 150.0, "avg": 135.0},
    "independent": {"low": 80.0, "high": 100.0, "avg": 90.0},
    "national_average": {"low": 85.0, "high": 110.0, "avg": 95.0},
    "diy": {"low": 0.0, "high": 0.0, "avg": 0.0},
}


class CostLineItem(BaseModel):
    """A single line item in a cost estimate."""
    description: str = Field(..., description="What this line item is for")
    category: str = Field(
        ...,
        description="Category: labor, parts, or supplies",
        pattern="^(labor|parts|supplies)$",
    )
    amount_low: float = Field(..., ge=0.0, description="Low-end cost estimate")
    amount_high: float = Field(..., ge=0.0, description="High-end cost estimate")


class CostEstimate(BaseModel):
    """Full cost estimate for a repair, with low/high ranges and DIY comparison."""
    labor_hours: float = Field(..., ge=0.0, description="Estimated labor hours")
    labor_rate: float = Field(..., ge=0.0, description="Hourly labor rate used")
    labor_total_low: float = Field(..., ge=0.0, description="Low-end labor cost")
    labor_total_high: float = Field(..., ge=0.0, description="High-end labor cost")
    parts_cost_low: float = Field(0.0, ge=0.0, description="Low-end parts cost")
    parts_cost_high: float = Field(0.0, ge=0.0, description="High-end parts cost")
    supplies_cost: float = Field(0.0, ge=0.0, description="Consumables/supplies cost")
    total_low: float = Field(..., ge=0.0, description="Total low-end estimate")
    total_high: float = Field(..., ge=0.0, description="Total high-end estimate")
    diy_parts_only: float = Field(
        ..., ge=0.0, description="Parts-only cost for DIY repair"
    )
    diy_savings_low: float = Field(
        ..., ge=0.0, description="Low-end savings doing it yourself"
    )
    diy_savings_high: float = Field(
        ..., ge=0.0, description="High-end savings doing it yourself"
    )
    line_items: list[CostLineItem] = Field(
        default_factory=list, description="Itemized cost breakdown"
    )
    shop_type: ShopType = Field(..., description="Shop type used for estimate")


class PartCost(BaseModel):
    """A part with its estimated cost range."""
    name: str = Field(..., description="Part name/description")
    cost_low: float = Field(..., ge=0.0, description="Low-end part cost")
    cost_high: float = Field(..., ge=0.0, description="High-end part cost")


class CostEstimator:
    """Pure-math cost estimator — no API or database needed.

    Takes labor hours, parts lists, and shop type to produce
    structured estimates with ranges and DIY savings.
    """

    def __init__(self, custom_rates: Optional[dict[str, dict[str, float]]] = None):
        """Initialize with optional custom labor rates.

        Args:
            custom_rates: Override default LABOR_RATES. Same structure:
                          {"dealer": {"low": X, "high": Y, "avg": Z}, ...}
        """
        self.rates = custom_rates if custom_rates is not None else LABOR_RATES

    def _get_rate(self, shop_type: ShopType) -> dict[str, float]:
        """Get the labor rate dict for a shop type."""
        return self.rates.get(shop_type.value, self.rates.get("national_average", {
            "low": 95.0, "high": 110.0, "avg": 95.0,
        }))

    def estimate(
        self,
        labor_hours: float,
        parts: Optional[list[PartCost]] = None,
        shop_type: ShopType = ShopType.INDEPENDENT,
        supplies_cost: float = 0.0,
    ) -> CostEstimate:
        """Build a cost estimate from labor hours, parts, and shop type.

        Args:
            labor_hours: Estimated labor hours for the repair.
            parts: List of PartCost items with name and cost range.
            shop_type: Type of shop (dealer, independent, DIY).
            supplies_cost: Flat cost for consumables (rags, cleaner, etc.).

        Returns:
            CostEstimate with full breakdown and DIY savings.
        """
        parts = parts or []
        rate = self._get_rate(shop_type)

        # Labor calculations
        labor_rate_avg = rate["avg"]
        labor_total_low = round(labor_hours * rate["low"], 2)
        labor_total_high = round(labor_hours * rate["high"], 2)

        # Parts calculations
        parts_cost_low = round(sum(p.cost_low for p in parts), 2)
        parts_cost_high = round(sum(p.cost_high for p in parts), 2)

        # Totals
        total_low = round(labor_total_low + parts_cost_low + supplies_cost, 2)
        total_high = round(labor_total_high + parts_cost_high + supplies_cost, 2)

        # DIY comparison (parts + supplies only, no labor)
        diy_parts_only = round(parts_cost_low + supplies_cost, 2)
        if shop_type == ShopType.DIY:
            # Already DIY — no savings to show
            diy_savings_low = 0.0
            diy_savings_high = 0.0
        else:
            diy_savings_low = round(max(0.0, total_low - diy_parts_only), 2)
            diy_savings_high = round(max(0.0, total_high - diy_parts_only), 2)

        # Build line items
        line_items: list[CostLineItem] = []

        if labor_hours > 0 and shop_type != ShopType.DIY:
            line_items.append(CostLineItem(
                description=f"Labor ({labor_hours:.1f} hrs @ ${rate['low']:.0f}-${rate['high']:.0f}/hr)",
                category="labor",
                amount_low=labor_total_low,
                amount_high=labor_total_high,
            ))

        for part in parts:
            line_items.append(CostLineItem(
                description=part.name,
                category="parts",
                amount_low=part.cost_low,
                amount_high=part.cost_high,
            ))

        if supplies_cost > 0:
            line_items.append(CostLineItem(
                description="Supplies and consumables",
                category="supplies",
                amount_low=supplies_cost,
                amount_high=supplies_cost,
            ))

        return CostEstimate(
            labor_hours=labor_hours,
            labor_rate=labor_rate_avg,
            labor_total_low=labor_total_low,
            labor_total_high=labor_total_high,
            parts_cost_low=parts_cost_low,
            parts_cost_high=parts_cost_high,
            supplies_cost=supplies_cost,
            total_low=total_low,
            total_high=total_high,
            diy_parts_only=diy_parts_only,
            diy_savings_low=diy_savings_low,
            diy_savings_high=diy_savings_high,
            line_items=line_items,
            shop_type=shop_type,
        )

    def estimate_from_diagnosis(
        self,
        diagnosis: DiagnosisItem,
        parts_with_costs: Optional[list[PartCost]] = None,
        shop_type: ShopType = ShopType.INDEPENDENT,
        supplies_cost: float = 0.0,
    ) -> CostEstimate:
        """Build a cost estimate from a DiagnosisItem.

        Uses the diagnosis's estimated_hours and parts_needed fields.
        If parts_with_costs is provided, those costs are used directly.
        Otherwise, parts_needed names are listed with zero cost (unknown).

        Args:
            diagnosis: DiagnosisItem from the diagnostic engine.
            parts_with_costs: Optional list of PartCost with real prices.
            shop_type: Type of shop for labor rate selection.
            supplies_cost: Flat cost for consumables.

        Returns:
            CostEstimate based on the diagnosis.
        """
        labor_hours = diagnosis.estimated_hours or 0.0

        if parts_with_costs is not None:
            parts = parts_with_costs
        else:
            # Use parts_needed names with zero cost (price unknown)
            parts = [
                PartCost(name=name, cost_low=0.0, cost_high=0.0)
                for name in diagnosis.parts_needed
            ]

        return self.estimate(
            labor_hours=labor_hours,
            parts=parts,
            shop_type=shop_type,
            supplies_cost=supplies_cost,
        )

    def compare_shop_types(
        self,
        labor_hours: float,
        parts: Optional[list[PartCost]] = None,
        supplies_cost: float = 0.0,
    ) -> dict[ShopType, CostEstimate]:
        """Compare costs across dealer, independent, and DIY.

        Returns a dict mapping ShopType to CostEstimate for each.
        Parts costs are the same across all — only labor changes.

        Args:
            labor_hours: Estimated labor hours.
            parts: List of PartCost items.
            supplies_cost: Flat cost for consumables.

        Returns:
            Dict with keys DEALER, INDEPENDENT, DIY and CostEstimate values.
        """
        return {
            shop_type: self.estimate(
                labor_hours=labor_hours,
                parts=parts,
                shop_type=shop_type,
                supplies_cost=supplies_cost,
            )
            for shop_type in ShopType
        }


def format_estimate(estimate: CostEstimate) -> str:
    """Format a CostEstimate as a human-readable string summary.

    Args:
        estimate: The CostEstimate to format.

    Returns:
        Multi-line string with the cost breakdown.
    """
    lines: list[str] = []
    lines.append(f"=== Cost Estimate ({estimate.shop_type.value.title()}) ===")
    lines.append("")

    # Line items
    if estimate.line_items:
        for item in estimate.line_items:
            if item.amount_low == item.amount_high:
                lines.append(f"  {item.description}: ${item.amount_low:.2f}")
            else:
                lines.append(
                    f"  {item.description}: ${item.amount_low:.2f} - ${item.amount_high:.2f}"
                )
        lines.append("")

    # Subtotals
    if estimate.labor_hours > 0:
        lines.append(
            f"Labor: ${estimate.labor_total_low:.2f} - ${estimate.labor_total_high:.2f} "
            f"({estimate.labor_hours:.1f} hrs @ ${estimate.labor_rate:.0f}/hr avg)"
        )
    lines.append(
        f"Parts: ${estimate.parts_cost_low:.2f} - ${estimate.parts_cost_high:.2f}"
    )
    if estimate.supplies_cost > 0:
        lines.append(f"Supplies: ${estimate.supplies_cost:.2f}")

    # Total
    lines.append("")
    lines.append(
        f"TOTAL: ${estimate.total_low:.2f} - ${estimate.total_high:.2f}"
    )

    # DIY savings
    if estimate.shop_type != ShopType.DIY and estimate.diy_savings_low > 0:
        lines.append("")
        lines.append(f"DIY (parts only): ${estimate.diy_parts_only:.2f}")
        lines.append(
            f"DIY savings: ${estimate.diy_savings_low:.2f} - ${estimate.diy_savings_high:.2f}"
        )

    return "\n".join(lines)
