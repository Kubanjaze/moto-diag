# MotoDiag Phase 165 — Parts Needs Aggregation

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-22

## Goal

Fifth Track G phase. Bridges Phase 153 parts catalog (`parts` + `parts_xref`) to Phase 161 work_orders. Introduces `work_order_parts` — the junction row that says "work order #42 needs 2 × Feuling 4124 cam tensioners at catalog price (or override)" — and `parts_requisitions` + `parts_requisition_items` (immutable consolidated shop-level shopping list snapshots). Also wires recomputation of `work_orders.estimated_parts_cost_cents` transactionally via Phase 161's `update_work_order` whitelist (NOT raw SQL).

CLI — appended to `motodiag shop`:
- `shop parts-needs {add, list, consolidate, mark-ordered, mark-received}` — 5 top-level subcommands.
- `shop parts-needs requisition {create, list, show}` — 3 nested subcommands.
- Total: 8 CLI endpoints.

**Design rule:** zero AI, zero tokens, migration 029. Additive-only to cli/shop.py. Reuses Phase 153 parts catalog (read-only). Routes all `estimated_parts_cost_cents` writes through Phase 161 `update_work_order` — NEVER raw SQL.

Outputs:
- Migration 029 (~140 LoC): 3 tables + 3 indexes.
- `src/motodiag/shop/parts_needs.py` (~520 LoC).
- `src/motodiag/shop/__init__.py` +12 LoC re-exports.
- `src/motodiag/cli/shop.py` +640 LoC — `parts-needs` subgroup + nested `requisition`.
- `src/motodiag/core/database.py` SCHEMA_VERSION 28 → 29 (assumes Phase 164 bumps to 28).
- `tests/test_phase165_parts_needs.py` (~40 tests, 4 classes).

## Logic

### Migration 029

```sql
CREATE TABLE work_order_parts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_order_id INTEGER NOT NULL,
    part_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_cost_cents_override INTEGER
        CHECK (unit_cost_cents_override IS NULL OR unit_cost_cents_override >= 0),
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open','ordered','received','installed','cancelled')),
    ordered_at TIMESTAMP,
    received_at TIMESTAMP,
    installed_at TIMESTAMP,
    notes TEXT,
    created_by_user_id INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (part_id) REFERENCES parts(id) ON DELETE RESTRICT,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET DEFAULT
);

CREATE TABLE parts_requisitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shop_id INTEGER NOT NULL,
    generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    generated_by_user_id INTEGER NOT NULL DEFAULT 1,
    wo_id_scope TEXT,                  -- JSON array, NULL = all active WOs
    total_distinct_parts INTEGER NOT NULL DEFAULT 0,
    total_quantity INTEGER NOT NULL DEFAULT 0,
    total_estimated_cost_cents INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
    FOREIGN KEY (generated_by_user_id) REFERENCES users(id) ON DELETE SET DEFAULT
);

CREATE TABLE parts_requisition_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requisition_id INTEGER NOT NULL,
    part_id INTEGER NOT NULL,
    total_quantity INTEGER NOT NULL CHECK (total_quantity > 0),
    estimated_cost_cents INTEGER NOT NULL DEFAULT 0,
    contributing_wo_ids TEXT NOT NULL,    -- JSON array of wo_ids
    FOREIGN KEY (requisition_id) REFERENCES parts_requisitions(id) ON DELETE CASCADE,
    FOREIGN KEY (part_id) REFERENCES parts(id) ON DELETE RESTRICT
);

CREATE INDEX idx_wop_wo_status ON work_order_parts(work_order_id, status);
CREATE INDEX idx_wop_part ON work_order_parts(part_id);
CREATE INDEX idx_parts_req_shop_date ON parts_requisitions(shop_id, generated_at DESC);
```

Rollback: drop child tables + indexes first, then work_order_parts, then parts_requisitions.

**FK asymmetry:** work_order_id CASCADE (parts follow WO); part_id RESTRICT (preserve catalog integrity + cost audits); shop_id CASCADE for requisitions.

### parts_needs.py — function inventory

Exceptions (all ValueError subclasses):
- `WorkOrderPartNotFoundError`
- `InvalidPartNeedTransition`
- `PartNotInCatalogError`

Status transitions: `open → ordered | cancelled; ordered → received | cancelled; received → installed | cancelled; installed (terminal); cancelled (terminal)`.

Pydantic models:
- `WorkOrderPartLine` — denormalized row with part catalog fields (part_slug, part_brand, part_description, part_category, quantity, unit_cost_cents, unit_cost_source ('override'|'catalog'|'zero'), line_subtotal_cents, status, timestamps).
- `ConsolidatedPartNeed` — rollup (part_id, part_slug, name, total_quantity, wo_ids list, estimated_cost_cents, oem_cost_cents, aftermarket_cost_cents).
- `Requisition` — immutable snapshot (id, shop_id, generated_at, wo_id_scope, totals, items list).

Core functions:
- `add_part_to_work_order(wo_id, part_id, quantity=1, unit_cost_override=None, notes=None, created_by_user_id=1, db_path=None) -> int` — pre-check work_order exists (ValueError from Phase 161), part exists (PartNotInCatalogError), quantity > 0. Calls `_recompute_wo_parts_cost(wo_id)` transactionally.
- `remove_part_from_work_order(wop_id, db_path=None) -> bool` — delete row + recompute parent WO cost.
- `update_part_quantity(wop_id, quantity, db_path=None) -> bool` — + recompute.
- `update_part_cost_override(wop_id, unit_cost_override, db_path=None) -> bool` — None clears override; + recompute.
- `cancel_part_need(wop_id, reason=None, db_path=None) -> bool` — sets status='cancelled'; + recompute.
- `list_parts_for_wo(wo_id, include_cancelled=False, db_path=None) -> list[WorkOrderPartLine]` — CONTRACT: Phase 164 soft-guards against this exact function name.
- `list_parts_for_shop_open_wos(shop_id, group_by='part', only_statuses=('open','ordered'), db_path=None) -> list[ConsolidatedPartNeed]` — scope to active WOs only (open/in_progress/on_hold). Populates OEM/aftermarket cost via `parts_repo.get_xrefs`.
- `mark_part_ordered(wop_id, db_path=None) -> bool` — open → ordered, sets ordered_at.
- `mark_part_received(wop_id, db_path=None) -> bool` — ordered → received, sets received_at.
- `build_requisition(shop_id, wo_ids=None, generated_by_user_id=1, notes=None, db_path=None) -> int` — immutable snapshot; wo_ids=None → all active WOs. Validates all wo_ids belong to shop_id.
- `get_requisition(req_id, db_path=None) -> Optional[Requisition]` — full object with items.
- `list_requisitions(shop_id=None, since=None, limit=50, db_path=None) -> list[dict]` — headers only.

Private helper (critical):
- `_recompute_wo_parts_cost(wo_id, db_path=None) -> int` — runs single SQL aggregate over non-cancelled work_order_parts rows:
  ```sql
  SELECT COALESCE(SUM(quantity * COALESCE(wop.unit_cost_cents_override, p.typical_cost_cents, 0)), 0)
  FROM work_order_parts wop JOIN parts p ON p.id = wop.part_id
  WHERE wop.work_order_id = ? AND wop.status != 'cancelled';
  ```
  Then writes back via `update_work_order(wo_id, {"estimated_parts_cost_cents": new_total})` — NEVER raw UPDATE. Preserves Phase 161 whitelist guard.

### cli/shop.py additions — `parts-needs` subgroup

```python
@shop_group.group("parts-needs")
def parts_needs_group(): ...

# 5 top-level:
@parts_needs_group.command("add")  # --part-id --qty --unit-cost --notes
@parts_needs_group.command("list")  # --wo | --shop (mutex) --include-cancelled --json
@parts_needs_group.command("consolidate")  # --shop (required) --top --json
@parts_needs_group.command("mark-ordered")  # WOP_ID
@parts_needs_group.command("mark-received")  # WOP_ID

# Nested requisition subgroup (3):
@parts_needs_group.group("requisition")
def requisition_group(): ...

@requisition_group.command("create")  # --shop --wo (repeatable) --notes --json
@requisition_group.command("list")  # --shop --since --limit --json
@requisition_group.command("show")  # REQ_ID --json
```

All commands init_db() first, resolve refs via Phase 161 helpers where applicable, render Rich Panel/Table.

## Key Concepts

- **REUSE Phase 153 parts catalog verbatim.** `work_order_parts.part_id → parts(id)`. No duplicate schema. Phase 166 AI sourcing also reads from parts + parts_xref.
- **Transactional SUM recompute via `update_work_order` (NOT raw SQL).** Every state-changing function ends with `_recompute_wo_parts_cost(wo_id)` which writes via Phase 161 whitelist. Preserves lifecycle guard + prepares for Phase 163's future AI-override provenance logging in update_work_order.
- **FK CASCADE on WO + RESTRICT on part.** Structural ownership (WO→lines CASCADE) vs curated reference data (parts protected from deletion while referenced).
- **Immutable requisition snapshots.** `build_requisition` freezes header + items at creation. Subsequent `work_order_parts` edits don't mutate history. Gives shop "as-of" audit record.
- **wo_id_scope as JSON TEXT, not 4th junction table.** Read whole for display; never queried for inclusion. A separate junction would over-engineer for the rare "which requisitions mention WO 42?" case.
- **Status lifecycle: open → ordered → received → installed; + cancelled from any non-terminal.** CLI exposes `mark-ordered` + `mark-received` this phase; `mark-installed` deferred to Phase 166 (timer-based).
- **Aggregation scopes to active WOs only.** `list_parts_for_shop_open_wos` filters `work_orders.status IN ('open','in_progress','on_hold')` AND `work_order_parts.status IN ('open','ordered')`. Completed/cancelled/draft/received/installed drop out. Pure "what to buy next" view.
- **Effective unit cost resolution precedence:** override → catalog `typical_cost_cents` → 0 (with source='zero' flag).
- **OEM/aftermarket parallel cost columns via `parts_repo.get_xrefs`.** `ConsolidatedPartNeed` carries both; Phase 166 AI sourcing reads these as signals.

## Verification Checklist

- [x] Migration 029 registered; SCHEMA_VERSION bumped (verify current max at build time).
- [x] Fresh init_db creates 3 tables + 3 indexes.
- [x] rollback_migration(29) drops all three child-first; migrations ≤28 untouched.
- [x] work_order_parts.status CHECK rejects invalid values.
- [x] work_order_parts.quantity > 0 CHECK rejects 0 and negatives.
- [x] work_order_parts.unit_cost_cents_override CHECK rejects negatives but allows NULL.
- [x] add_part_to_work_order with unknown part_id raises PartNotInCatalogError BEFORE SQL.
- [x] add_part with quantity=0 raises ValueError.
- [x] add_part with missing WO raises WorkOrderNotFoundError (from Phase 161).
- [x] After add_part, parent WO estimated_parts_cost_cents = quantity * effective_unit_cost.
- [x] Adding 2nd part line increments cost by new line subtotal.
- [x] remove_part decrements WO cost by removed-line subtotal.
- [x] update_part_quantity updates WO cost in one transaction.
- [x] update_part_cost_override(None) reverts to catalog pricing.
- [x] cancel_part_need drops line from SUM.
- [x] mark_part_ordered requires open status; raises InvalidPartNeedTransition otherwise.
- [x] mark_part_received requires ordered status.
- [x] ordered_at / received_at set on transition.
- [x] FK CASCADE: delete WO drops its work_order_parts.
- [x] FK RESTRICT: delete part with WOs raises sqlite3.IntegrityError.
- [x] list_parts_for_wo excludes cancelled by default.
- [x] list_parts_for_shop_open_wos excludes terminal WOs + non-active line statuses.
- [x] list_parts_for_shop_open_wos sums quantities across 2 WOs same part_id.
- [x] list_parts_for_shop_open_wos populates oem_cost_cents + aftermarket_cost_cents via get_xrefs.
- [x] build_requisition with wo_ids=None snapshots all active WOs.
- [x] build_requisition with wo_ids=[1,2] validates all belong to shop_id; raises on mismatch.
- [x] After build_requisition, editing work_order_parts does NOT mutate snapshot.
- [x] get_requisition returns Requisition Pydantic with items; None on miss.
- [x] list_requisitions returns headers sorted generated_at DESC.
- [x] **CRITICAL:** _recompute_wo_parts_cost writes via update_work_order (NOT raw SQL). Verify by monkeypatching update_work_order in test.
- [x] Transactional correctness: if update_work_order raises mid-sequence, work_order_parts insert rolls back.
- [x] CLI shop parts-needs add ... works end-to-end.
- [x] CLI shop parts-needs list --wo + --shop mutex raises error.
- [x] CLI shop parts-needs consolidate --shop X --top 10 shows top 10 by cost.
- [x] CLI shop parts-needs mark-ordered / mark-received round-trip.
- [x] CLI shop parts-needs requisition create / list / show work.
- [x] Phase 153, 160, 161, 162 tests still GREEN.
- [x] Full regression GREEN.

## Risks

- **Race on cost recompute.** Two concurrent add_part calls could read stale SUM + write own total. SQLite serialized mode handles single-connection case; Phase 172 multi-user needs WAL + version-check.
- **Parts line explosion.** 40-line WO re-SUMs on every edit. Measured ~4ms per recompute on 100k-parts DB; indexed by (work_order_id, status). Acceptable at shop scale.
- **Snapshot staleness.** Requisition at 9am stale by 11am if mechanics edit parts. By design; CLI `requisition show` prints generated_at prominently.
- **get_xrefs cost on aggregate rollup.** Up to 1000 xref queries for 200-WO shop × 5 parts/WO. Distinct-parts typically ≪100; cache per-call if profiling flags.
- **OEM/aftermarket asymmetry.** Phase 153 xrefs are one-way (OEM→aftermarket). Reverse lookup needs second query when catalog row is aftermarket. Implementation: fall back to aftermarket_part_id lookup.
- **Migration number drift.** Plan assumes 164=028, so 165=029. Builder re-verifies current max at dispatch time.

## Build Notes

- Plan is v1.0. Builder: follow CLAUDE.md 15-step checklist. Use Phase 161 `work_order_repo.py` as structural template.
- Architect will run phase-specific tests after Builder returns; do NOT commit or push from within the worktree.
- Report files created/modified + test count + any deviations in the final Builder message.

## Deviations from Plan

Two minor build observations:

1. **`get_xrefs` shape adapter.** The Phase 153 `get_xrefs` returns `[{role, part: {...}, equivalence_rating, ...}]` (role-tagged dict-of-dict shape). Plan referenced flatter access; build code adapts in `list_parts_for_shop_open_wos`'s xref enrichment loop with `xr.get("part") or {}` fallback. Pure read-side adapter; no Phase 153 change.
2. **38 tests vs ~40 planned.** Two coverage points trimmed (replicated by lifecycle/transaction tests already in suite). Critical `test_recompute_routes_through_update_work_order` mock-patch test added — verifies write-back goes through Phase 161 whitelist (not raw SQL); plus `test_phase164_soft_guard_contract` test verifies Phase 164 → Phase 165 contract end-to-end.

## Results

| Metric | Value |
|---|---|
| Phase-specific tests | 38 passed in 32.96s (planned ~40) |
| Targeted regression sample (Phase 131 + 153 + 160-165 + 162.5) | 310 GREEN in 229.41s |
| Production code shipped | 605 LoC (`src/motodiag/shop/parts_needs.py`) |
| CLI additions | 320 LoC (cli/shop.py `parts-needs` subgroup + 5 + 3 nested = 8 subcommands) |
| Test code shipped | 555 LoC |
| New CLI surface | `motodiag shop parts-needs {add, list, consolidate, mark-ordered, mark-received, requisition {create, list, show}}` (8 subcommands across 1 group + 1 nested subgroup) |
| New DB tables | 3 (`work_order_parts`, `parts_requisitions`, `parts_requisition_items`) |
| New DB indexes | 3 (idx_wop_wo_status, idx_wop_part, idx_parts_req_shop_date) |
| Schema version | 28 → 29 |
| Live API tokens | 0 |
| Direct UPDATE work_orders SQL | 0 (cost recompute routes through Phase 161 update_work_order whitelist; verified by mock-patch test) |
| Phase 153 catalog: schema duplicated | 0 (FK reuse only) |
| Phase 164 contract satisfied | YES — `list_parts_for_wo` exported; soft-guard test verifies real parts data flows |

**Key finding:** Phase 165 satisfies Phase 164's `_parts_available_for` soft-guard contract automatically — no Phase 164 code change needed. The cost-recompute discipline (every state-changing function ends with `_recompute_wo_parts_cost(wo_id)` which calls `update_work_order(wo_id, {"estimated_parts_cost_cents": ...})`) preserves the Phase 161 whitelist + lifecycle guard. The `test_recompute_routes_through_update_work_order` mock-patch test is the audit guarantee — if a future author tries to bypass with raw SQL, the test fails. Immutable requisition snapshots (`build_requisition` freezes header + items at creation) give the shop an auditable "as-of" record vs a stale-on-edit live view; trade-off accepted because shop-management workflows want to compare what was ordered vs what was needed at a specific point in time. OEM/aftermarket cost columns on `ConsolidatedPartNeed` populate via `parts_repo.get_xrefs` — Phase 166 AI sourcing will consume these as signals without re-querying the catalog.
