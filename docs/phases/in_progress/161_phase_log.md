# MotoDiag Phase 161 — Phase Log

**Status:** Planned | **Started:** 2026-04-21 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-21 16:00 — Plan written, initial push

Second Track G phase. Introduces `work_orders` — the mechanic's unit of work on a specific bike. Attaches to Phase 160's `intake_visits` row via nullable `intake_visit_id` FK (SET NULL on intake delete — work history survives accidental intake wipes). Denormalizes `shop_id` / `vehicle_id` / `customer_id` onto the work order itself so the dominant "list work orders for shop X / bike Y / customer Z" queries are single-index lookups; `create_work_order` validates cross-table consistency when `intake_visit_id` is supplied.

Architectural decisions baked into v1.0:

1. **Guarded status lifecycle, same pattern as Phase 160.** `draft → open → in_progress → (on_hold | completed | cancelled) → (reopen) → open`. Generic `update_work_order` cannot mutate `status`, `opened_at`, `completed_at`, `closed_at`, or any `*_reason` column — only the 7 dedicated transition functions can (`open_work_order` / `start_work` / `pause_work` / `resume_work` / `complete_work_order` / `cancel_work_order` / `reopen_work_order`). Prevents CLI/future-API bypass. `_VALID_TRANSITIONS` dict drives the guard; `InvalidWorkOrderTransition` on misuse.

2. **FK asymmetry mirrors Phase 160.** `shop_id` CASCADE (explicit + rare). `intake_visit_id` SET NULL (orphaning is correct — work history shouldn't evaporate with the intake row). `vehicle_id` + `customer_id` RESTRICT (prevents accidental history erasure). `assigned_mechanic_user_id` SET NULL (Phase 172 re-assignment flow). `created_by_user_id` SET DEFAULT (system user 1 fallback, Phase 112 pattern).

3. **Composable filters on `list_work_orders`.** Every query shape Phases 163-172 will need — by shop / status / mechanic / bike / customer / intake / priority / time window — is a single repo call with kwargs. Avoids growing a zoo of `list_by_X` variants the way Phase 113's `crm/` did before Phase 160 surfaced it.

4. **Priority 1-5 CHECK-bounded integer.** Grid-sortable, mechanic-settable, AI-overridable in Phase 163 (only when confidence exceeds a threshold, to avoid AI drift over mechanic intent). CHECK constraint enforces bounds at the schema layer.

5. **Reopen clears terminal timestamps.** If work wasn't actually done, the `completed_at` was a lie. Phase 169 invoicing reads `completed_at` as "invoice-generated-at" display, not as logic — cleanly clearing on reopen prevents double-invoicing logic drift.

6. **1:N intake → work orders.** One customer bringing a bike in with three problems → one intake, three work orders. Tests cover the multi-WO-per-intake shape; Phase 164 triage queue surfaces the grouping.

7. **Append-only CLI additions.** `cli/shop.py` gains a new `@shop_group.group("work-order")` nested subgroup (12 subcommands) without touching Phase 160's `profile` / `customer` / `intake` subgroups. No edit to `cli/main.py` — `register_shop` wired in Phase 160 already.

Test plan: ~45 tests across 4 classes — `TestMigration026` (5) + `TestWorkOrderRepo` (18 — CRUD + all 7 lifecycle transitions + FK asymmetry + composable filters + denormalization consistency) + `TestWorkOrderCLI` (14) + `TestIntakeLinkage` (8 — 1:N intake relationship, auto-fill from `--intake`, cross-table consistency rejection).

Risk flagged: Phase 162 follows with migration 027 (structured issues attached to work orders). Serial ordering is strict — 161 ships first, 162 rebases on SCHEMA_VERSION=26, same for `cli/main.py` edits (none this phase). No parallel Builders across 161/162/163.

Risk flagged: cancel from `draft` is allowed (mechanic might draft a WO and realize mid-intake the customer changed their mind). Tests cover that path explicitly so future refactors don't silently tighten the transition matrix.

CLI command this phase: `motodiag shop work-order {create, list, show, update, start, pause, resume, complete, cancel, reopen, assign, unassign}`.
