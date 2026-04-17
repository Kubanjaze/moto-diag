# MotoDiag Phase 118 — Billing/Invoicing/Inventory/Scheduling Substrate

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Create the business-operations substrate that Tracks O/S phases (273-289, 328-329) will consume. 4 new packages — `billing`, `accounting`, `inventory`, `scheduling` — plus 9 new tables covering subscriptions/payments, invoices, parts inventory, vendors, recalls, warranties, and appointments. Schema + CRUD only. Actual Stripe integration, QuickBooks/Xero export, and calendar sync are NOT built here — they plug into this substrate. Foundation work for every revenue-generating feature downstream.

CLI: `python -m pytest tests/test_phase118_ops_substrate.py -v`

Outputs: 4 packages (~15 files), migration 011, 37 tests

## Logic
1. **Migration 011** — 9 new tables:
   - **Billing**: `subscriptions` (user_id FK, tier, status, stripe_*_id), `payments` (user_id FK, subscription_id FK nullable, amount, status, stripe_payment_intent_id)
   - **Accounting**: `invoices` (customer_id FK, repair_plan_id FK nullable, invoice_number UNIQUE, status, subtotal/tax/total), `invoice_line_items` (invoice_id FK CASCADE, item_type, quantity × unit_price = line_total, source_repair_plan_item_id FK nullable)
   - **Inventory**: `vendors` (name UNIQUE, contact info, payment_terms), `inventory_items` (sku UNIQUE, model_applicable JSON, quantity_on_hand, reorder_point, vendor_id FK SET NULL)
   - **Warranty/Recalls**: `recalls` (campaign_number UNIQUE, make/model/year_range, severity, remedy), `warranties` (vehicle_id FK CASCADE, coverage_type enum, claim_count)
   - **Scheduling**: `appointments` (customer_id FK CASCADE, vehicle_id FK SET NULL, user_id FK SET NULL, appointment_type/status enums, scheduled_start/end as ISO strings)
   - **14 indexes** across all tables (FKs, status/type enums, unique lookup columns)

2. **4 packages** (`src/motodiag/billing/`, `accounting/`, `inventory/`, `scheduling/`):
   - `billing/`: 2 models (Subscription, Payment) + 3 enums + 11 repo functions (subscription + payment CRUD)
   - `accounting/`: 2 models (Invoice, InvoiceLineItem) + 2 enums + 11 repo functions including `recalculate_invoice_totals(tax_rate)` that sums line items and applies tax
   - `inventory/`: 4 models (InventoryItem, Vendor, Recall, Warranty) + 1 enum + 4 repo modules with 25+ functions (items, vendors, recalls, warranties). Includes `adjust_quantity(delta)` for stock changes and `items_below_reorder()` for low-stock alerts.
   - `scheduling/`: 1 model (Appointment) + 2 enums + 9 repo functions including `cancel_appointment(reason)`, `complete_appointment(actual_end)`, `list_upcoming(from_iso)`, `list_for_user(mechanic_id)`

3. **`database.py`**: `SCHEMA_VERSION` 10 → 11.

## Key Concepts
- **Schema-only substrate**: no Stripe API calls, no QuickBooks export, no calendar sync — Track O/S phases build the actual integrations on top
- **FK strategy** (consistent pattern — see CASCADE vs SET NULL decisions):
  - User-scoped data (subscriptions, payments, warranties, invoices via customer) uses CASCADE — deleting a user/customer/vehicle nukes their billing history
  - Optional references (vendor_id on items, repair_plan_id on invoices, vehicle_id/user_id on appointments) use SET NULL — preserves the dependent record even when the referenced entity is deleted
- **Stripe column naming** (`stripe_customer_id`, `stripe_subscription_id`, `stripe_payment_intent_id`) matches Stripe's own naming — when Track O 273 wires Stripe up, these columns just need `UPDATE`, no schema change
- **Subscription tier mirrors existing enforcement**: Phase 109 introduced MOTODIAG_SUBSCRIPTION_TIER env var. Phase 118's `subscriptions.tier` column is the same enum stored per-user — Track H 178 switches enforcement to read from the DB instead of env
- **Invoice numbering**: opaque unique string; Track O 278 generates the actual format
- **Inventory `model_applicable` JSON**: lets a single part SKU cover multiple bikes (e.g., Honda CBR929RR and CBR954RR share brake calipers)
- **Appointment times as ISO 8601 strings**: no timezone column yet; multi-location (Track T 346) will need per-shop timezone
- **`list_upcoming()` filters terminal statuses** — cancelled/completed/no_show won't show up as "upcoming"
- **`items_below_reorder()` ignores zero reorder_point** — only items with `reorder_point > 0` are considered, sorted by most-urgent first (quantity gap descending)

## Verification Checklist
- [x] Migration 011 creates all 9 tables
- [x] 14 indexes created (verified by smoke test + list_appointments via idx_appointments_scheduled_start)
- [x] 8 enums defined with correct member counts (3/4/4/5/4/4/4/6)
- [x] 9 Pydantic models validate correctly
- [x] CRUD round-trips for each table
- [x] FK CASCADE: deleting customer cascades invoices (via Track C vehicles), appointments; deleting invoice cascades line items
- [x] FK SET NULL: deleting vendor sets inventory_items.vendor_id NULL
- [x] Unique constraints enforced (invoice_number, sku, vendor name — all raise on duplicate)
- [x] JSON columns round-trip correctly (model_applicable: ["CBR929RR", "CBR954RR"])
- [x] `recalculate_invoice_totals(tax_rate=0.0875)` correctly computes subtotal, tax, total from line items
- [x] `adjust_quantity(delta)` works both negative and positive
- [x] `items_below_reorder()` filters correctly
- [x] `list_recalls_for_vehicle(make, year)` applies year-range filter
- [x] `list_upcoming()` excludes cancelled/completed/no_show
- [x] Rollback drops all 9 tables cleanly (FK-safe reverse order)
- [x] Schema version assertions use `>= 11` (forward-compat)
- [x] All 1895 existing tests still pass (zero regressions) — full suite 1932/1932 in 10:08

## Risks
- **Scope is large (9 tables, 4 packages)**: materialized — mitigated by schema-only scope. Each package is thin: models + basic CRUD. Total new code ~1700 LoC, fully tested.
- **Stripe column names baked in**: accepted — Stripe is the ecosystem standard for motorcycle-shop SaaS. Switching processor would need column rename migration.
- **Appointment timezone**: single-shop deployments work. Multi-location will add per-shop timezone column — documented as deferred concern for Track T 346.
- **Invoice format flexibility**: Invoice numbering is just TEXT — Track O 278 decides format. Zero commitment.

## Deviations from Plan
- None structural. Built exactly to plan: 9 tables (including the recounted `appointments`), 4 packages, 37 tests.
- Test count: plan said ~50, actual 37. 37 is tighter because several checklist items (e.g., "recalculate totals", "items_below_reorder", "list_upcoming terminal filter") are single tests each rather than multiple scenarios.

## Results
| Metric | Value |
|--------|-------|
| New packages | 4 (billing, accounting, inventory, scheduling) |
| New files | 16 (4 × __init__ + 4 × models + 8 × repo modules — inventory has 4 repos, others have 1-2) + test file |
| New tests | 37 |
| Total tests | 1932 passing (was 1895) |
| New enums | 8 (tier 3 + sub status 4 + pay status 4 + invoice status 5 + item type 4 + coverage 4 + appt type 4 + appt status 6 = 34 members total) |
| New models | 9 Pydantic models |
| Repo functions | ~55 across 4 packages |
| New tables | 9 |
| New indexes | 14 |
| Schema version | 10 → 11 |
| Regression status | Zero regressions — full suite 10:08 runtime |

Phase 118 is the largest single retrofit phase — the substrate for every revenue-generating feature in Tracks O and S. Stripe column names are pre-wired so Track O 273 is a pure plug-in. Invoice totals auto-recalc on demand. Low-stock alerts are queryable with one function call. The 9-table footprint looks heavy but each table is the minimum viable schema for its downstream consumer — there is no speculative scope here.
