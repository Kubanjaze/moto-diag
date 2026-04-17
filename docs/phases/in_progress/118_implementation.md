# MotoDiag Phase 118 — Billing/Invoicing/Inventory/Scheduling Substrate

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Create the business-operations substrate that Tracks O/S phases (273-292, 328-342) will consume. 4 new packages — `billing`, `accounting`, `inventory`, `scheduling` — plus 8 new tables covering subscriptions/payments, invoices, parts inventory, vendors, recalls, warranties, and appointments. Schema + minimal CRUD only. Actual Stripe integration (Track O 273-277), QuickBooks/Xero export (278-281), and customer-portal billing (Track S 328-329) are NOT built here — they plug into this substrate. Foundation work for every revenue-generating feature downstream.

CLI: `python -m pytest tests/test_phase118_ops_substrate.py -v`

Outputs: 4 packages (`billing/`, `accounting/`, `inventory/`, `scheduling/`), migration 011, ~50 tests

## Logic
1. **Migration 011** — 8 new tables:
   - **Billing** (Track O 273-277, Track S 328-329):
     - `subscriptions` — user_id (FK), tier, status (active/cancelled/past_due/trialing), started_at, ends_at, stripe_customer_id, stripe_subscription_id
     - `payments` — user_id (FK), subscription_id (FK nullable), amount, currency, status (pending/succeeded/failed/refunded), stripe_payment_intent_id, payment_method, created_at
   - **Accounting** (Track O 278-281):
     - `invoices` — customer_id (FK customers), repair_plan_id (FK nullable), invoice_number (unique), status (draft/sent/paid/overdue/cancelled), subtotal, tax_amount, total, issued_at, due_at, paid_at, notes
     - `invoice_line_items` — invoice_id (FK CASCADE), item_type (labor/parts/diagnostic/misc), description, quantity, unit_price, line_total, source_repair_plan_item_id (FK nullable)
   - **Inventory** (Track O 282-285):
     - `inventory_items` — sku (unique), name, description, category, make, model_applicable (JSON), quantity_on_hand, reorder_point, unit_cost, unit_price, vendor_id (FK nullable), location, last_counted_at, created_at, updated_at
     - `vendors` — name (unique), contact_name, email, phone, website, address, payment_terms, notes, is_active, created_at
   - **Warranty/Recalls** (Track O 286-287):
     - `recalls` — campaign_number (unique), make, model, year_start, year_end, description, severity, remedy, notification_date, created_at
     - `warranties` — vehicle_id (FK), coverage_type (powertrain/comprehensive/extended/aftermarket), provider, start_date, end_date, mileage_limit, terms, claim_count, created_at
   - **Scheduling** (Track O 288-289):
     - `appointments` — customer_id (FK), vehicle_id (FK nullable), user_id (FK — assigned mechanic), appointment_type (ppi/diagnostic/service/consultation), status (scheduled/confirmed/in_progress/completed/cancelled/no_show), scheduled_start, scheduled_end, actual_start, actual_end, notes, created_at, updated_at
   - **Indexes**: ~14 indexes on FKs + enum columns + sku/invoice_number/campaign_number for unique lookups
   - **Rollback**: drops all 9 tables (appointments are first due to FKs, then billing/accounting/inventory/warranty/recalls)

Wait — that's 9 tables with appointments. Let me recount: subscriptions, payments (2) + invoices, invoice_line_items (2) + inventory_items, vendors (2) + recalls, warranties (2) + appointments (1) = 9 tables.

2. **4 packages** (`src/motodiag/billing/`, `accounting/`, `inventory/`, `scheduling/`):
   - Each has `__init__.py`, `models.py`, one or more `*_repo.py` files
   - Enums: `SubscriptionTier` (individual/shop/company — mirrors MOTODIAG_SUBSCRIPTION_TIER env var), `SubscriptionStatus`, `PaymentStatus`, `InvoiceStatus`, `InvoiceLineItemType`, `CoverageType`, `AppointmentType`, `AppointmentStatus`
   - CRUD functions: add/get/list/update/delete for each table. Total ~40 functions across 9 tables.

3. **`database.py`**: `SCHEMA_VERSION` 10 → 11.

## Key Concepts
- **Schema-only substrate**: no Stripe API calls, no QuickBooks export, no calendar sync — Track O/S phases build the actual integrations on top
- **FK strategy**:
  - `subscriptions.user_id` / `payments.user_id` → users.id ON DELETE CASCADE (if a user is deleted, their billing history goes with them)
  - `invoices.customer_id` → customers.id ON DELETE CASCADE; `invoices.repair_plan_id` → repair_plans.id ON DELETE SET NULL (don't lose invoice when a plan is deleted)
  - `invoice_line_items.invoice_id` → invoices.id ON DELETE CASCADE
  - `inventory_items.vendor_id` → vendors.id ON DELETE SET NULL
  - `warranties.vehicle_id` → vehicles.id ON DELETE CASCADE
  - `appointments.customer_id` → customers.id ON DELETE CASCADE; vehicle_id/user_id → SET NULL (if mechanic leaves, reassign later)
- **Invoice numbering**: store as opaque unique string; Track O 278 generates the actual format (e.g., "INV-2026-0001")
- **Stripe column naming**: `stripe_customer_id`, `stripe_subscription_id`, `stripe_payment_intent_id` match Stripe's own naming — when Track O 273 wires Stripe up, these columns just need `UPDATE`
- **Subscription tier mirrors existing enforcement**: Phase 109 introduced MOTODIAG_SUBSCRIPTION_TIER env var + soft/hard paywall mode. Phase 118's `subscriptions.tier` column is the same enum stored per-user — Track H 178 will switch enforcement to read from the DB instead of env.
- **Appointment times as ISO strings**: `scheduled_start`/`scheduled_end` stored as TEXT ISO 8601. Track O 289 can add iCal/Google sync on top.
- **Inventory `model_applicable` JSON array**: lets a single part SKU cover multiple bikes (e.g., Honda CBR929RR and CBR954RR share brake calipers).

## Verification Checklist
- [ ] Migration 011 creates all 9 tables
- [ ] 14+ indexes created
- [ ] 8 enums defined with correct member counts
- [ ] 9 Pydantic models validate correctly
- [ ] CRUD round-trips for each table
- [ ] FK CASCADE: deleting user cascades subscriptions + payments
- [ ] FK CASCADE: deleting invoice cascades line items
- [ ] FK SET NULL: deleting vendor sets inventory_items.vendor_id NULL
- [ ] FK SET NULL: deleting repair_plan sets invoice.repair_plan_id NULL
- [ ] Unique constraint on subscriptions.stripe_subscription_id (NULL allowed)
- [ ] Unique constraint on invoices.invoice_number
- [ ] Unique constraint on inventory_items.sku
- [ ] Unique constraint on vendors.name
- [ ] Unique constraint on recalls.campaign_number
- [ ] JSON columns round-trip correctly (model_applicable)
- [ ] Rollback drops all 9 tables cleanly
- [ ] All 1895 existing tests still pass (zero regressions)
- [ ] Schema version assertions use `>=` (forward-compat)

## Risks
- **Scope is large (9 tables, 4 packages)**: mitigated by schema-only scope — no external integrations. Each package is thin: models + basic CRUD. Total new code is ~1500-2000 LoC, but mechanical and tested.
- **Stripe column names baked in now**: if we switch from Stripe to a different processor later, these columns would need renaming. Accepted — Stripe is the ecosystem standard and switching is unlikely.
- **Invoice format flexibility**: Invoice numbering is just a TEXT column — Track O 278 decides format. No commitment here.
- **Appointment timezone**: storing ISO 8601 strings without a timezone column is fine for single-shop use. Multi-location (Track T 346) will need per-shop timezone — can add column then.
