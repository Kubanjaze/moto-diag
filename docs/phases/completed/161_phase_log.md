# MotoDiag Phase 161 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-21 | **Completed:** 2026-04-21
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

### 2026-04-21 16:30 — Build complete

Architect-direct auto-iterate build. All six code blocks shipped:

1. **Migration 026** appended to `core/migrations.py` + `SCHEMA_VERSION` 25 → 26 in `core/database.py`. FK semantics: shop_id CASCADE, intake_visit_id SET NULL, vehicle_id + customer_id RESTRICT, assigned_mechanic_user_id SET NULL.
2. **`shop/work_order_repo.py`** — 748 LoC, 14 functions + 7 dedicated lifecycle transition helpers + 3 exceptions. `_VALID_TRANSITIONS` dict drives the lifecycle guard. `_UPDATABLE_FIELDS` whitelist excludes status + all timestamp + all `*_reason` columns. Composable filters on `list_work_orders` cover every Phase 163-172 query shape.
3. **`shop/__init__.py`** +25 LoC — re-exports 19 names (12 functions + 3 exceptions + 2 constants + WORK_ORDER_TERMINAL_STATUSES).
4. **`cli/shop.py`** +473 LoC — `work-order` subgroup + 12 subcommands + Rich panel renderer + denormalized row accessors + Phase 125-style remediation errors. Total `cli/shop.py` now 1476 LoC.
5. **`cli/main.py`** unchanged — Phase 160's `register_shop` registration carries 161's new subgroup automatically via additive `@shop_group.group("work-order")`.
6. **47 tests** in `test_phase161_work_orders.py` across 4 classes — TestMigration026 (5), TestWorkOrderRepo (18), TestIntakeLinkage (8), TestWorkOrderCLI (14, including `+resume_from_open_raises_clear_error`). 62.29s phase-specific runtime. All GREEN.

Build deviations:
- CLI `start WO_ID` auto-opens drafts before transitioning to in_progress. Mechanic convenience; repo layer unchanged.
- One CLI list test switched to `--json` mode for assertion isolation (loose `1`/`2` substrings in mileage/year/phone columns collided with naïve substring checks).
- 47 tests vs ~45 planned (slight overshoot for resume-from-open + intake-mismatch edge cases).

### 2026-04-21 17:50 — Full regression dispatched

Background pytest run launched against full test suite. Slow run expected (system load high — Phase 160 regression took 3h24m last week; this one ran 4h32m).

### 2026-04-21 22:22 — Regression returned: 3441 passed / 1 failed

Full regression result: 3441 passed, 1 failed in 16359.81s (4:32:39).

**Failure:** `tests/test_phase160_shop.py::TestMigration025::test_rollback_drops_child_first` — `sqlite3.OperationalError: no such table: main.intake_visits`.

**Root cause:** Phase 160's rollback test runs `rollback_migration(25)` directly, attempting `DROP TABLE intake_visits` while Phase 161's `work_orders` table (from migration 026) still references `intake_visits` via the `intake_visit_id` FK. With `PRAGMA foreign_keys = ON`, the drop fails — exactly the error pattern Track F flagged with the SCHEMA_VERSION `>= N` loosening pass.

**Fix:** swapped both Phase 160 + Phase 161 rollback tests to use `rollback_to_version(target_version, path)` which peels migrations beyond `target_version` in correct reverse-version order. Phase 160's test now uses `rollback_to_version(24, ...)` (peels 025 + any later migrations); Phase 161's preemptively uses `rollback_to_version(25, ...)` (peels 026 + future 027+). Forward-compat protection is now standardized for all future migration rollback tests.

**Re-verified:** 91/91 Phase 160 + Phase 161 tests GREEN in 56.98s after fix. Single failure resolved without rebuilding any phase logic — pure test-only forward-compat patch.

### 2026-04-21 22:30 — Documentation finalization

`implementation.md` promoted to v1.1 — Verification Checklist all `[x]`, Deviations from Plan section appended (3 build observations + 1 forward-compat bug fix), Results table populated with as-built metrics (47 phase tests + 3441 regression + LoC + DB tables/indexes + lifecycle transition count), key finding documented (guarded-lifecycle pattern now canonical across 3 Track G repos; `rollback_to_version` is the new standard test pattern).

`phase_log.md` carries this entry plus the "Build complete" + "Regression returned" + "Documentation finalization" timestamps.

Phase moved `docs/phases/in_progress/161_*.md` → `docs/phases/completed/161_*.md`.

Project-level updates landing in same commit (Architect-Auditor flagged 5 fixes, all applied):
1. `implementation.md` schema_version footnote: "(currently v25 after Phase 160)" → "(currently v26 after Phase 161)"
2. `implementation.md` Database Tables: append `work_orders` row with full column description
3. `implementation.md` Phase History: append Phase 161 row with rollout details + bug-fix note
4. `implementation.md` Shop management CLI Commands: bump from 22 → 34 subcommands; add `motodiag shop work-order` row
5. `implementation.md` Version footnote near header: clarify pyproject vs doc-version split
6. `phase_log.md` project-level: new entry covering Track G work-order pillar landing + bug fix + Auditor findings closure
7. `docs/ROADMAP.md`: Phase 161 row → ✅ with rollout summary

Project version 0.9.1 → 0.9.2.

**Key finding:** the rollback-test forward-compat pattern (`rollback_to_version(target)` instead of `rollback_migration(specific_version)`) is the second instance (after Phase 145/150 SCHEMA_VERSION loosening) where a downstream phase's migration broke an upstream phase's test. Codifying this pattern in Phase 161 means every future phase inherits forward-compat protection automatically — Phase 162's rollback test should use `rollback_to_version(26, path)` and so on.
