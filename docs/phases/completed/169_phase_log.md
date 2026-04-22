# MotoDiag Phase 169 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-22 | **Completed:** 2026-04-22
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-22 — Plan written

Plan v1.0 authored in-session (serial per-phase discipline, no Planner
agent dispatched for this phase). Pushed as commit `76d1f22` with
`docs/phases/in_progress/169_implementation.md`. Scope: reuse Phase 118
`invoices` + `invoice_line_items` + `accounting.invoice_repo` CRUD;
add one column (`invoices.work_order_id`) via micro-migration 033;
build a `shop/invoicing.py` orchestration layer that pulls Phase 167
labor hours + Phase 165 installed parts into invoice line items with
tax + shop-supplies + optional diagnostic fee stacking. Zero AI.

### 2026-04-22 — Build complete

Files shipped:

1. **Migration 033** (schema v32→v33) — `ALTER TABLE invoices ADD COLUMN
   work_order_id INTEGER` + index `idx_invoices_work_order`. Rollback
   uses rename-recreate pattern (SQLite limitation). Registered via
   `Migration(version=33, name="invoices_work_order_id", ...)`.

2. **`shop/invoicing.py`** (~496 LoC):
   - 3 Pydantic models: `InvoiceLineItemSummary`, `InvoiceSummary`,
     `RevenueRollup`.
   - 2 exceptions: `InvoiceGenerationError`, `InvoiceNotFoundError`.
   - Public API: `generate_invoice_for_wo`, `mark_invoice_paid`,
     `void_invoice`, `get_invoice_with_items`, `list_invoices_for_shop`,
     `revenue_rollup`.
   - Private helpers: `_lookup_labor_rate_cents` (state → national →
     any fallback), `_check_existing_invoice`, `_format_invoice_number`
     (with `-Rn` regeneration suffix), `_get_customer_name`,
     `_load_installed_parts`, `_add_line_cents` (cents→dollars boundary),
     `_cents_to_dollars`, `_dollars_to_cents`.
   - Constants: `INVOICE_STATUSES = ("draft","sent","paid","overdue","cancelled")`
     matching Phase 118 enum.

3. **`shop/__init__.py`** +14 re-exports.

4. **`cli/shop.py`** +196 LoC — `invoice` subgroup with **6 subcommands**
   (`generate`, `list`, `show`, `mark-paid`, `void`, `revenue`) + new
   `_render_invoice_panel` helper. Total `cli/shop.py` now ~4340 LoC
   across 12 subgroups and 88 subcommands.

5. **`tests/test_phase169_invoicing.py`** (32 tests across 6 classes):
   - `TestMigration033` (5) — schema version, column, index, registry,
     rollback-to-32.
   - `TestInvoiceGeneration` (9) — happy path, idempotency, non-completed
     reject, no-hours reject, estimated fallback, missing labor rate
     reject, installed parts, tax + supplies stacking, invoice number
     format.
   - `TestMarkPaidAndVoid` (5) — mark paid + timestamp + not-found; void
     + regeneration allowed.
   - `TestListAndRollup` (6) — by shop, by status, bogus status reject,
     rollup buckets, all-shops rollup, pending math.
   - `TestInvoiceCLI` (6) — generate/show/mark-paid round-trip, list
     filters, void, revenue, error surface, not-found surface.
   - `TestAntiRegression` (1) — no `anthropic` import in `invoicing.py`.

**Phase 118 substrate reconciliation (surfaced mid-build):** Phase 118
uses `InvoiceStatus` enum with ``"sent"``/``"cancelled"`` (not
``"issued"``/``"void"`` from the plan), stores amounts as **dollar
floats** (not integer cents), and enforces NOT NULL on
`invoices.customer_id`. The invoicing module reconciles entirely at its
boundary — public API accepts cents (CLI `--hourly-rate 10000` =
$100/hr); writes dollars to the DB; uses Phase 118 enum values
internally; rejects customer-less WOs with a clear error. Phase 118
tests (40+) pass unchanged.

**Invoice number collision fix (surfaced mid-test):** Phase 118's
`invoices.invoice_number` is UNIQUE, and the plan's format
`INV-{shop}-{wo}-{YYYYMMDD}` collides when a WO gets voided +
regenerated on the same day. Resolved: `_format_invoice_number`
counts prior invoices for the WO (including cancelled ones) and
appends `-R{n}` when n > 0. Test `test_void_allows_regeneration_for_same_wo`
covers this.

**Tests:** 32 GREEN in 53.62s. Phase-specific run, single pass (two
test fixes during build: "no-customer" case dropped as structurally
unreachable after Phase 161's NOT NULL; parts pipeline lifecycle
corrected to `open → ordered → received`).

**Targeted regression: 511 GREEN in 328.77s (5m 28s)** covering
Phase 113 (CRM) + Phase 118 (billing/accounting) + Phase 131 (ai-cache)
+ Phase 153 (parts catalog) + Track G phases 160-169 + Phase 162.5.
Zero regressions.

Build deviations vs plan:
- Added `void_invoice` public function (plan had only mark-paid); CLI
  gains `shop invoice void <id>` for total 6 subcommands not 5.
- Invoice number format extended with `-Rn` regeneration suffix.
- Dropped "no customer" test branch (structurally unreachable after
  Phase 161 NOT NULL).
- `list_invoices_for_shop` uses INNER JOIN on work_orders (strict
  shop-scope); unlinked pre-Phase-169 invoices reachable via
  `get_invoice_with_items(id)` directly.
- `revenue_rollup` dual-mode: shop-scoped (JOIN) or all-invoices
  (no JOIN) for future multi-tenant / cross-shop dashboards.

### 2026-04-22 — Documentation finalization

`implementation.md` promoted to v1.1. Verification Checklist all `[x]`.
Deviations section lists the 5 deviations above. Results table
populated (32 tests, 511 regression GREEN, ~496 LoC invoicing module,
6 CLI subcommands, schema v33). Key finding captures Track G commercial
core closure: intake → triage → WO → parts → labor → bay → completion
→ invoice → revenue, all through `motodiag shop *`.

`phase_log.md` carries this entry. Both files moved to
`docs/phases/completed/`.

Project-level updates:
- `implementation.md` schema_version footnote v32 → v33
- `implementation.md` Database Tables: note `invoices.work_order_id`
  column addition (no new tables)
- `implementation.md` Phase History: append Phase 169 row
- `implementation.md` Shop CLI Commands: 82 → 88 subcommands; added
  `motodiag shop invoice` row (12th subgroup)
- `phase_log.md` project-level: Phase 169 closure entry; Track G
  commercial core (intake → invoice) complete
- `docs/ROADMAP.md`: Phase 169 row → ✅
- Project version 0.10.0 → **0.10.1** (Track G commercial core closure;
  one phase past Gate 8 runway entry)

**Key finding:** Phase 169 validates the "reuse-existing-substrate"
pattern across a 50+ phase gap. Phase 118 shipped the `invoices` +
`invoice_line_items` + `accounting.invoice_repo` substrate in an earlier
track; Phase 169 added a single column and an orchestration module and
got a working revenue-tracking console without touching Phase 118 code.
Three substrate mismatches (enum vocabulary, dollars vs cents, NOT NULL
customer) all reconciled at the invoicing-module boundary. Zero Phase
118 test regressions. The pattern generalizes: future phases that
leverage older substrate (e.g., Phase 172 building on Phase 117
mechanic RBAC) should expect 2-3 vocabulary/convention mismatches and
reconcile at the new module's boundary — never reach back and rename
old fields.
