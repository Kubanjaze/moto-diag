# MotoDiag Phase 165 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-22 | **Completed:** 2026-04-22
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-21 — Plan written via Planner-165 agent (10-agent pool)

Plan v1.0 produced by Planner-165 in Stage A wave. Persisted to `docs/phases/in_progress/165_implementation.md`.

### 2026-04-22 00:55 — Build complete

Architect-direct serial build per user direction. Bridges Phase 153 parts catalog (`parts` + `parts_xref`) to Phase 161 work_orders. Files shipped:

1. **Migration 029** — three new tables in one migration:
   - `work_order_parts` — junction (work_order_id FK CASCADE, part_id FK RESTRICT) + 5-state lifecycle (open → ordered → received → installed; cancelled from any non-terminal) + ordered_at/received_at/installed_at timestamps + unit_cost_cents_override (nullable; NULL = catalog default).
   - `parts_requisitions` — immutable consolidated shopping-list snapshots (shop_id FK CASCADE, generated_at, wo_id_scope as JSON, frozen totals).
   - `parts_requisition_items` — frozen per-part rows in a snapshot (requisition_id FK CASCADE, part_id FK RESTRICT, contributing_wo_ids as JSON).
   - 3 indexes (idx_wop_wo_status, idx_wop_part, idx_parts_req_shop_date). Bumps SCHEMA_VERSION 28 → 29.

2. **`shop/parts_needs.py`** (605 LoC) — 18 functions including:
   - 5 CRUD: `add_part_to_work_order` / `remove_part_from_work_order` / `update_part_quantity` / `update_part_cost_override` / `cancel_part_need`.
   - 3 lifecycle transitions: `mark_part_ordered` / `mark_part_received` / `mark_part_installed` (terminal — surfaced for Phase 166).
   - 1 critical helper: `_recompute_wo_parts_cost(wo_id)` — the ONLY way to write `work_orders.estimated_parts_cost_cents`. Sums `quantity * effective_unit_cost` (override or catalog) across non-cancelled rows, then writes back via Phase 161 `update_work_order(wo_id, {"estimated_parts_cost_cents": new_total})` — NEVER raw SQL.
   - 2 read APIs: `list_parts_for_wo` (Phase 164 contract!) + `list_parts_for_shop_open_wos` (cross-WO consolidation with OEM/aftermarket cost surfacing via `parts_repo.get_xrefs`).
   - 3 requisition APIs: `build_requisition` (immutable snapshot; validates wo_ids belong to shop_id) + `get_requisition` + `list_requisitions`.
   - 3 Pydantic models: `WorkOrderPartLine` / `ConsolidatedPartNeed` / `Requisition`.
   - 3 exceptions: `WorkOrderPartNotFoundError` / `InvalidPartNeedTransition` / `PartNotInCatalogError`.

3. **`shop/__init__.py`** +25 LoC re-exports 19 names.

4. **`cli/shop.py`** +320 LoC — `parts-needs` subgroup with 5 top-level subcommands (`add`, `list`, `consolidate`, `mark-ordered`, `mark-received`) + nested `requisition` sub-subgroup with 3 (`create`, `list`, `show`). 8 subcommands total. Total `cli/shop.py` now ~3380 LoC across 7 subgroups (profile/customer/intake/work-order/issue/priority/triage/parts-needs).

5. **`tests/test_phase165_parts_needs.py`** (555 LoC, 38 tests across 5 classes including the load-bearing `test_recompute_routes_through_update_work_order` mock-patch + `test_phase164_soft_guard_contract`).

**Phase 164 contract satisfied:** `list_parts_for_wo(wo_id, db_path=None)` exported. Phase 164's triage queue's `_parts_available_for` soft-guard now picks up real parts-availability data automatically. The `test_phase164_soft_guard_contract` test in this phase's suite verifies the contract end-to-end.

**Critical audit guarantee:** `test_recompute_routes_through_update_work_order` patches `motodiag.shop.parts_needs.update_work_order` and asserts it's called with `{"estimated_parts_cost_cents": new_total}` in the updates dict — proves the cost recompute routes through the Phase 161 whitelist, never raw SQL. If a future author tries to bypass, the test fails loudly.

**Tests:** 38 GREEN across 5 classes (TestMigration029×5 + TestPartsNeedsCRUD×12 + TestPartsLifecycle×5 + TestRequisitions×8 + TestPartsNeedsCLI×8) in 32.96s. Targeted regression sample (Phase 131 + 153 + 160-165 + 162.5): 310 GREEN in 229.41s — Phase 153 parts catalog tests pass unchanged (parts row format compatible).

Build deviations:
- `get_xrefs` shape adapter: Phase 153's get_xrefs returns role-tagged `{role, part: {...}, equivalence_rating}` shape. Plan referenced flatter access; build adapts via `xr.get("part") or {}` fallback in xref enrichment loop. Read-only adapter; no Phase 153 change.
- 38 tests vs ~40 planned (replicated coverage trimmed; critical mock-patch + soft-guard contract tests added).
- Empty requisition still creates header row with zero counts (intentional — explicit "we checked, found nothing" record).

### 2026-04-22 01:00 — Documentation finalization

`implementation.md` promoted to v1.1. Verification Checklist all `[x]`. Deviations + Results sections appended. Key finding: Phase 165 satisfies Phase 164's soft-guard automatically; cost-recompute discipline preserves Phase 161 whitelist via mock-patch audit test; immutable requisition snapshots give shop "as-of" records.

`phase_log.md` carries this entry. Both files moved to `docs/phases/completed/`.

Project-level updates:
- `implementation.md` schema_version footnote v28 → v29
- `implementation.md` Database Tables: append work_order_parts + parts_requisitions + parts_requisition_items rows
- `implementation.md` Phase History: append Phase 165 row
- `implementation.md` Shop CLI Commands: bumped 55 → 63 subcommands; added `motodiag shop parts-needs` row (with nested requisition)
- `phase_log.md` project-level: Phase 165 closure entry covering Phase 164 contract satisfaction + cost-recompute audit pattern + Phase 153 catalog reuse
- `docs/ROADMAP.md`: Phase 165 row → ✅
- Project version 0.9.6 → 0.9.7
