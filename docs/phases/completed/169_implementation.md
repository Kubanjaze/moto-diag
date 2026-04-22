# MotoDiag Phase 169 — Revenue Tracking + Invoicing

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-22

## Goal

Generate invoices from completed Phase 161 work orders. Pulls Phase 165 `work_order_parts` for parts line items, Phase 167 `actual_hours` (or `labor_estimates`) for labor line, applies shop-level tax + shop-supplies fee, writes to the existing Phase 118 `invoices` + `invoice_line_items` tables (no duplication). Adds one column (`invoices.work_order_id` FK) so invoices reference WOs cleanly. Zero AI.

CLI — `motodiag shop invoice {generate, list, show, mark-paid, revenue}` — 5 subcommands.

**Design rule:** zero AI, zero tokens, micro migration 033 (single ALTER TABLE). Reuses Phase 118 `accounting.invoice_repo` CRUD. Additive-only to `cli/shop.py`.

Outputs:
- Migration 033 (~25 LoC): `ALTER TABLE invoices ADD COLUMN work_order_id INTEGER` (nullable, FK SET NULL via runtime logic — SQLite ALTER can't add FK directly).
- `src/motodiag/shop/invoicing.py` (~350 LoC) — generate_invoice_for_wo + mark_invoice_paid + list_invoices_for_shop + revenue_rollup + 3 Pydantic models + 2 exceptions.
- `src/motodiag/shop/__init__.py` +18 LoC re-exports.
- `src/motodiag/cli/shop.py` +200 LoC — `invoice` subgroup with 5 subcommands.
- `src/motodiag/core/database.py` SCHEMA_VERSION 32 → 33.
- `tests/test_phase169_invoicing.py` (~28 tests).

## Logic

### Migration 033

```sql
ALTER TABLE invoices ADD COLUMN work_order_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_invoices_work_order ON invoices(work_order_id);
```

Rollback uses rename-recreate pattern (Phase 164 precedent).

**FK handling:** SQLite doesn't allow adding FK via ALTER. We treat `work_order_id` as a soft reference — the repo layer validates on write; deletions handled via a trigger-free convention (mechanics don't delete work_orders; Phase 161 uses status='cancelled').

### `shop/invoicing.py` — function inventory

```python
def generate_invoice_for_wo(
    wo_id: int,
    tax_rate: float = 0.0,                    # e.g. 0.0825 for 8.25% sales tax
    shop_supplies_pct: float = 0.0,           # e.g. 0.05 for 5% shop supplies fee
    shop_supplies_flat_cents: int = 0,        # alternative: flat fee
    diagnostic_fee_cents: int = 0,            # optional diagnostic line
    labor_hourly_rate_cents: Optional[int] = None,  # override per-shop rate
    db_path: Optional[str] = None,
) -> int:
    """Build an invoice from a completed WO. Returns invoice_id.

    Reads Phase 161 work_order (requires status='completed').
    Reads Phase 165 work_order_parts (installed/received rows → parts lines).
    Labor line uses WO.actual_hours (falls back to estimated_hours).
    Default labor rate from Phase G `labor_rates` table (first matching
    row by state or 'national' fallback); override via param.

    Idempotent per WO: raises InvoiceGenerationError if an invoice
    already exists for this wo_id (use mark_invoice_paid or regenerate
    path, not this function).
    """

def mark_invoice_paid(
    invoice_id: int, paid_at: Optional[str] = None,
    db_path: Optional[str] = None,
) -> bool:
    """Set invoices.status='paid' + paid_at timestamp."""

def get_invoice_with_items(
    invoice_id: int, db_path: Optional[str] = None,
) -> Optional[InvoiceSummary]:
    """Load invoice header + denormalized items + customer name."""

def list_invoices_for_shop(
    shop_id: int, status: Optional[str] = None,
    since: Optional[str] = None, limit: int = 100,
    db_path: Optional[str] = None,
) -> list[dict]:
    """List invoices by walking work_orders → shop."""

def revenue_rollup(
    shop_id: Optional[int] = None,
    since: Optional[str] = None,
    db_path: Optional[str] = None,
) -> RevenueRollup:
    """Sum invoice totals by status (paid/pending/overdue) for dashboard."""
```

Pydantic models: `InvoiceSummary` (invoice dict + items + customer_name + wo_reference) / `InvoiceLineItemSummary` / `RevenueRollup` (calls + totals + by_status dict).

Exceptions: `InvoiceGenerationError` (duplicate for WO, WO not completed, etc.), `InvoiceNotFoundError`.

### Line-item composition (generate_invoice_for_wo)

1. **Labor line** (item_type='labor'): qty = actual_hours; unit_price = labor_hourly_rate (cents per hour / 100 = dollars); line_total = qty × unit_price.
2. **Parts lines** (item_type='parts'): one line per installed/received work_order_parts row. qty = quantity; unit_price = override-or-catalog; line_total = qty × unit_price.
3. **Diagnostic line** (optional): item_type='diagnostic', qty=1, unit_price=diagnostic_fee_cents/100.
4. **Shop supplies line** (if shop_supplies_pct > 0 OR shop_supplies_flat_cents > 0): item_type='misc', qty=1. Percentage applied to parts+labor subtotal.
5. **Tax**: applied to subtotal (all lines). Stored on `invoices.tax_amount`.
6. **Totals**: subtotal = SUM(line_total), total = subtotal + tax.

Invoice number format: `"INV-{shop_id}-{wo_id}-{YYYYMMDD}"`.

### CLI subgroup

- `invoice generate WO_ID [--tax-rate 0.0825] [--supplies-pct 0.05] [--supplies-flat ¢N] [--diagnostic-fee ¢N] [--hourly-rate ¢N] [--json]`
- `invoice list [--shop X] [--status open|paid|overdue] [--since 30d] [--limit 50] [--json]`
- `invoice show INVOICE_ID [--json]`
- `invoice mark-paid INVOICE_ID [--paid-at ISO]`
- `invoice revenue [--shop X] [--since 30d] [--json]`

## Key Concepts

- **Reuses Phase 118 substrate:** `invoices` + `invoice_line_items` tables + `accounting.invoice_repo` CRUD exist from Phase 118. Phase 169 adds ONE column + orchestration module — zero table duplication.
- **Idempotency per WO:** `generate_invoice_for_wo` raises on duplicate generation. Mechanics can void + regenerate (Phase 170+ adds void flow); this phase keeps scope tight.
- **Labor rate fallback:** looks up `labor_rates` table by state then 'national'; caller can override via `labor_hourly_rate_cents`.
- **No AI.** Pure arithmetic + orchestration.
- **No raw SQL against work_orders.** Reads via Phase 161 `get_work_order`; no write-back on this path (invoices are downstream state).

## Verification Checklist

- [x] Migration 033 adds `invoices.work_order_id` column + index.
- [x] SCHEMA_VERSION 32 → 33.
- [x] Rollback to 32 drops column cleanly (rename-recreate).
- [x] `generate_invoice_for_wo` on non-completed WO raises.
- [x] `generate_invoice_for_wo` persists invoice + lines (labor + parts + tax as applicable).
- [x] Duplicate generation raises `InvoiceGenerationError`.
- [x] Labor line uses actual_hours when present; falls back to estimated_hours.
- [x] Parts lines match Phase 165 work_order_parts installed rows.
- [x] Tax rate applied to subtotal correctly.
- [x] Shop supplies pct + flat combine correctly.
- [x] Invoice number format `INV-{shop}-{wo}-{YYYYMMDD}` (with `-Rn` suffix on regeneration).
- [x] `mark_invoice_paid` sets status + paid_at.
- [x] `list_invoices_for_shop` filters by shop.
- [x] `revenue_rollup` aggregates by status correctly.
- [x] CLI `invoice generate`/`list`/`show`/`mark-paid`/`void`/`revenue` round-trip.
- [x] Phase 113/118/131/153/160-168 tests still GREEN (511/511 targeted regression).
- [x] Zero AI calls.

## Risks

- **Tax + shop supplies are floats → cents conversion.** Rounding edge cases at $0.01 boundaries. Mitigation: compute in cents throughout; convert to display dollars only at render. Tests cover the common rates (0, 8.25%, 10%). Resolved: module accepts cents at boundary, computes in cents, converts to dollars at write to the Phase 118 float-dollar schema.
- **Idempotency enforced at app layer, not schema.** No UNIQUE constraint on `invoices.work_order_id` because soft-references allow voided-and-regenerated flows. Mitigation: repo check before insert; documented in module docstring. Resolved via `_check_existing_invoice` (scopes on `status != 'cancelled'`) and `INV-...-Rn` suffix on regeneration to avoid `invoice_number` UNIQUE collision.
- **`labor_rates` lookup by state requires shop state.** Phase 160 `shops.state` is optional; if NULL, falls back to 'national' rate row or raises `InvoiceGenerationError` with remediation hint. Resolved: three-stage lookup (state → national → any) with explicit `labor_hourly_rate_cents` kwarg override documented in CLI `--hourly-rate`.
- **Phase 118 substrate vocabulary mismatch (surfaced during build).** Phase 118 `InvoiceStatus` enum uses ``"sent"`` + ``"cancelled"``, not the ``"issued"`` + ``"void"`` vocabulary the plan assumed. Plus Phase 118 stores amounts as **dollar floats** in `subtotal/tax_amount/total`, not integer cents. Plus `invoices.customer_id` is NOT NULL — work orders with no customer can't be invoiced at all. Mitigation: invoicing module reconciles at the boundary (cents in public API; dollars on write; `"sent"` on insert; `"cancelled"` on void; reject WOs without customer_id with a clear error). All documented in the module's cents/dollars convention docstring.

## Deviations from Plan

- **Added `void_invoice` as a public function (not just CLI).** Plan called for mark-paid + regenerate path only; build surfaced need for an explicit void function so tests can exercise the "void then regenerate" flow end-to-end. CLI gains `shop invoice void <id> [--reason X]`. Total CLI subcommands: 6 (generate/list/show/mark-paid/void/revenue), not 5.
- **Invoice number collision fix: `-Rn` suffix.** Plan's invoice-number format `INV-{shop}-{wo}-{YYYYMMDD}` collides on `invoices.invoice_number UNIQUE` when a WO gets its invoice voided + regenerated on the same day. Fixed by counting prior invoices for the WO (including cancelled) and appending `-R{n}` when n > 0.
- **Dropped the "no customer" branch from tests.** Phase 161 made `work_orders.customer_id` NOT NULL, so the "WO without customer" case is structurally unreachable. Removed that test case; kept the defensive runtime check in `generate_invoice_for_wo` for future-proofing.
- **`list_invoices_for_shop` is strict-shop-scoped.** Earlier draft used a LEFT JOIN that also surfaced unlinked invoices; simplified to INNER JOIN on `work_orders` since Phase 169 owns the invoice creation path and always sets `work_order_id`. Pre-Phase 169 invoices (no WO link) remain reachable via `get_invoice_with_items(id)` directly.
- **Revenue rollup: two query modes, not one.** When `shop_id=None`, the rollup skips the `work_orders` JOIN entirely and aggregates across all invoices — enables shop-agnostic dashboards (multi-tenant, future API).

## Results

| Metric | Value |
|--------|-------|
| Phase 169 tests landed | 32 GREEN (6 classes) |
| Targeted regression | 511/511 GREEN in 328.77s (5m 28s) |
| Coverage range | Phase 113 (CRM) + 118 (accounting) + 131 (ai-cache) + 153 (parts) + 160-168 (Track G) + 169 |
| Migration LoC | 33 LoC (upgrade SQL + rename-recreate rollback) |
| `shop/invoicing.py` LoC | 496 (headers, helpers, public API) |
| `cli/shop.py` addition | +196 LoC (`invoice` subgroup: 6 subcommands + Panel renderer) |
| `shop/__init__.py` addition | +14 re-exports |
| Total `cli/shop.py` | ~4340 LoC, **12 subgroups**, **88 subcommands** |
| SCHEMA_VERSION | 32 → **33** |
| AI calls | 0 (zero tokens spent) |

**Key finding:** Phase 169 closes Track G's commercial core — the mechanic now has a workflow that goes from intake → triage → priority score → work order → parts sourcing → labor estimate → bay schedule → completion → invoice → revenue dashboard, all through `motodiag shop *` without a single cross-phase handoff. The Phase 118 substrate (which shipped untouched since early in the roadmap) integrated cleanly: only one column (`work_order_id`) needed to wire work orders to invoices; the existing `accounting.invoice_repo` CRUD handled the rest. The build surfaced three substrate mismatches (enum values, cents-vs-dollars, NOT NULL customer_id) — all reconciled at the invoicing-module boundary without touching Phase 118 code, preserving 40+ billing/accounting tests unchanged. Gate 8 (Phase 174) can now assert a full intake-to-invoice integration across all nine Track G phases.
