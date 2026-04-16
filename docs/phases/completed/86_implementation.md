# MotoDiag Phase 86 — Cost Estimation

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build a pure-calculation cost estimation module in the diagnostic engine that takes labor hours, parts lists with price ranges, and shop type to produce structured cost estimates with low/high ranges, line-item breakdowns, and DIY savings comparisons. No API calls or database access needed — this is standalone math that bridges diagnosis output to customer-facing cost info.

CLI: `python -m pytest tests/test_phase86_cost.py -v`

Outputs: `src/motodiag/engine/cost.py`, `tests/test_phase86_cost.py` (25 tests)

## Logic
1. Define `ShopType` enum (DEALER, INDEPENDENT, DIY) and `LABOR_RATES` dict with rate ranges per shop type
2. `CostLineItem` Pydantic model holds a single line (description, category, low/high amounts)
3. `CostEstimate` Pydantic model holds the full estimate: labor totals, parts totals, supplies, grand total (all low/high), DIY parts-only cost, DIY savings, line items list, shop type
4. `PartCost` Pydantic model represents a part with name and cost range
5. `CostEstimator` class:
   - `estimate()`: multiplies labor_hours by rate range, sums parts costs, adds supplies, computes DIY savings as total minus parts-only cost
   - `estimate_from_diagnosis()`: extracts `estimated_hours` and `parts_needed` from a `DiagnosisItem`, delegates to `estimate()`
   - `compare_shop_types()`: calls `estimate()` three times (dealer, independent, DIY) and returns a dict
6. `format_estimate()` standalone function: renders a `CostEstimate` as a human-readable multi-line string with line items, subtotals, total, and DIY savings
7. DIY estimates have zero labor cost — the `diy_parts_only` field equals `parts_cost_low + supplies_cost`
8. Custom rates supported via constructor injection — allows regional or shop-specific overrides

## Key Concepts
- ShopType enum: DEALER ($120-150/hr), INDEPENDENT ($80-100/hr), DIY ($0/hr)
- LABOR_RATES dict: keyed by shop type, each has low/high/avg hourly rates
- CostLineItem: category field validated to labor|parts|supplies via regex pattern
- CostEstimate: all monetary fields have `ge=0.0` constraint, supplies defaults to 0
- PartCost model: decouples part pricing from part names in DiagnosisItem
- estimate() builds line items automatically: 1 labor + N parts + optional supplies
- DIY shop type suppresses labor line item in output
- diy_savings = total - diy_parts_only (captures what you save by not paying labor)
- format_estimate(): includes "DIY savings" section only for non-DIY shop types
- compare_shop_types(): returns dict[ShopType, CostEstimate] for side-by-side comparison

## Verification Checklist
- [x] CostLineItem rejects invalid categories (not labor/parts/supplies)
- [x] CostLineItem rejects negative amounts
- [x] CostEstimate creates with correct defaults (supplies=0, line_items=[])
- [x] estimate() computes correct labor totals for each shop type
- [x] estimate() sums parts costs correctly
- [x] estimate() includes supplies in total
- [x] DIY estimate has zero labor cost
- [x] DIY estimate has no labor line item
- [x] DIY savings = total - diy_parts_only
- [x] compare_shop_types() returns 3 estimates with dealer > independent > DIY
- [x] Parts costs identical across all shop types in comparison
- [x] estimate_from_diagnosis() uses DiagnosisItem.estimated_hours
- [x] estimate_from_diagnosis() handles None estimated_hours (defaults to 0)
- [x] estimate_from_diagnosis() with no parts_with_costs creates zero-cost part items
- [x] format_estimate() includes shop type, TOTAL, line items
- [x] format_estimate() shows DIY savings for non-DIY types
- [x] format_estimate() hides DIY savings for DIY type
- [x] Edge case: zero hours produces zero labor
- [x] Edge case: empty parts list produces zero parts cost
- [x] Edge case: very high estimate (engine rebuild) computes correctly
- [x] Custom rates override defaults
- [x] LABOR_RATES dict has expected keys and structure
- [x] Engine __init__.py exports all cost module types
- [x] 25/25 tests pass

## Risks
- **Parts pricing unknown at diagnosis time**: estimate_from_diagnosis() gracefully handles this by creating zero-cost PartCost items from parts_needed names. The caller can provide real prices via parts_with_costs parameter.
- **Regional rate variation**: Default rates are national averages. The existing `pricing` module in motodiag has DB-backed regional rates — integration between the two modules is a future concern (likely Phase 148+ shop management).
- **No inflation adjustment**: Rates are 2024-2025 static values. Custom rates constructor param allows overrides.

## Deviations from Plan
- Added `PartCost` model (not in original spec) to cleanly separate part names from price ranges — cleaner API than passing raw dicts
- Used regex pattern validation on CostLineItem.category instead of a separate enum — simpler for 3 fixed values

## Results

| Metric | Value |
|--------|-------|
| Module | `src/motodiag/engine/cost.py` |
| Models | 4 (ShopType, CostLineItem, CostEstimate, PartCost) |
| Classes | 1 (CostEstimator with 3 methods) |
| Functions | 1 (format_estimate) |
| Test file | `tests/test_phase86_cost.py` |
| Tests | 25 |
| API calls | 0 (pure calculation) |
| Lines of code | ~240 (module) + ~280 (tests) |

Pure-math cost estimation bridges the gap between AI diagnosis output and customer-facing repair quotes — the CostEstimator takes a DiagnosisItem and produces structured estimates that can be compared across shop types and rendered for display.
