# Track G Planner Consolidation Notes (Phases 162-168)

Compiled 2026-04-21 from 10-agent peak-efficiency pool output. Records overrides to apply during each phase's build, cross-phase dependencies, and architectural decisions that changed after Planner return.

---

## Migration number reservation (locked)

| Phase | Migration | Notes |
|---|---|---|
| 161 (done) | 026 | work_orders table |
| 162 | 027 | issues table |
| 163 | (none) | AI phase, reuses ai_response_cache |
| 164 | 028 | shops.triage_weights column |
| 165 | 029 | work_order_parts + parts_requisitions + parts_requisition_items |
| 166 | 030 | sourcing_recommendations table |
| 167 | 031 | labor_estimates table |
| 168 | 032 | shop_bays + bay_schedule_slots tables |

Strictly serial. No parallel builders across 162-168 (cli/shop.py edits + SCHEMA_VERSION bump each serialize).

---

## Phase 162 override — ship 12 categories, not 7

**Planner-162 proposed:** reuse existing 7 `SymptomCategory` values (engine/fuel_system/electrical/cooling/exhaust/transmission/other).

**Domain-Researcher-Workflow found:** existing 7 misfile ~40-50% of real shop tickets into "other." Real shop ticket distribution requires brakes + suspension + drivetrain + tires_wheels + accessories as first-class categories.

**Build override:** migration 027 CHECK constraint must include 12 categories:
```sql
CHECK (category IN (
    'engine', 'fuel_system', 'electrical', 'cooling',
    'exhaust', 'transmission', 'brakes', 'suspension',
    'drivetrain', 'tires_wheels', 'accessories', 'rider_complaint',
    'other'
))
```

`ISSUE_CATEGORIES` tuple in `issue_repo.py` must carry all 12. `SYMPTOM_CATEGORY_TO_ISSUE_CATEGORY` crosswalk dict must route the existing SymptomCategory values into the new richer vocabulary (e.g. `brakes → brakes`, not `→ other`).

Rationale: mechanic user, 30+ years experience, will know a ticket filed as "other: brake squeal" is a tooling smell. Ship the right taxonomy on day one.

---

## Phase 163 overrides — adopt research-driven priority formula

**Planner-163 proposed:** `priority_score = base_tier + wait_age_bonus + customer_history_bonus` with tier scores 1000/500/200/50 + aging rates 100/50/20/10.

**Domain-Researcher-Workflow found:** same formula with same coefficients. **Planner + Researcher converged independently.** Ship as-is.

**Build note:** Include the worked examples from the research brief in the `priority_scorer.py` module docstring + in the v1.1 implementation.md Results section.

Ceiling/floor rules from research:
- Max priority_score = 1500 (aged Tier 4 can't beat fresh Tier 1)
- Tier 1 floors at 1000 regardless of age
- `rider_complaint` category defaults to 300 until reclassified

---

## Micro-phase 162.5 — extract shop/ai_client.py (NEW, not in ROADMAP)

**Independently flagged by Planner-163, Planner-166, Planner-167:** all three AI phases reimplement Anthropic client setup, cost-cents calculation, prompt caching, and JSON extraction from markdown fences. Code triplication across three phases, with a fourth phase (AI analytics, future) coming. Three independent planners flagging this = strong signal.

**Decision:** insert micro-phase **162.5** after Phase 162 lands. Extract shared helpers into `src/motodiag/shop/ai_client.py`:

- `resolve_model(alias_or_full) -> str` — reads `MODEL_ALIASES` dict
- `calculate_cost(model, tokens_in, tokens_out) -> int` (cents)
- `MODEL_PRICING` dict (kept in sync with engine/client.py's table — or extract engine's too)
- `get_anthropic_client(api_key=None) -> anthropic.Anthropic` (lazy singleton)
- `ShopAIClient.ask(prompt, system, model, use_cache, cache_kind) -> (text, TokenUsage, cost_cents)` — thin wrapper threading Phase 131 prompt cache

Phases 163, 166, 167 then import from `shop.ai_client` instead of reimplementing.

**Scope:** no migration, no new CLI, ~150 LoC module + ~15 tests. Should complete in 30-45 min. Justifies itself on Phase 163's first build — saves ~250 LoC across 3 subsequent phases.

**Schedule:** build immediately after Phase 162 lands. Phase 163 depends on it.

---

## Phase 164 — soft-guard Phase 165 parts availability

Planner-164 chose the right pattern: `importlib.util.find_spec("motodiag.shop.parts_order_repo")` returns None → treat all parts as ready. Matches Phase 150 fleet_analytics → Phase 149 wear_repo precedent.

**Naming contract reserved:** Phase 165's module must export `list_parts_orders_for_work_order(wo_id, db_path=None)` function or Phase 164's soft-guard silently fails to resolve.

**Actually:** Phase 165's Planner named the function `list_parts_for_wo(wo_id, ...)` — **MISMATCH**. During Phase 164/165 build, reconcile to one name. Prefer the shorter `list_parts_for_wo` that Phase 165 planner proposed. Update Phase 164's soft-guard call site accordingly.

---

## Phase 165 — reuse Phase 153 parts catalog (no duplication)

Planner-165 correctly reuses `motodiag.advanced.parts_repo` (Phase 153's catalog). No schema duplication. `work_order_parts.part_id → parts(id)` foreign key. `parts_repo.get_xrefs(oem_part_number)` for OEM↔aftermarket cost population.

**Function name contract:** export `list_parts_for_wo` + `list_parts_for_shop_open_wos` + `build_requisition` + `mark_part_ordered` / `mark_part_received`. Phase 164 + Phase 166 both depend on these names.

---

## Phase 166 — integrate research brief into system prompt

Planner-166 proposed a generic sourcing policy in the system prompt. **Replace/augment** with the detailed rubric from `track_g_pricing_brief.md`:

- Use the decision tree from research (safety-critical path-of-force → OEM only; consumables → aftermarket first; etc.)
- Include the 10 concrete examples table (Harley M8 brake pads, CBR900 stator, GSX-R750 fairing, etc.) as few-shot exemplars
- Use the 6-tier vendor taxonomy (T1 OEM dealer → T6 AliExpress-avoid) explicitly in vendor suggestion ranking

**Critical mechanic-credibility signal:** the AI must know Ricks Motorsports aftermarket stators > OEM on 80s-00s Honda/Yamaha/Kawasaki. Bake this into the prompt explicitly; default-OEM-for-electrical rules would miss this.

---

## Phase 167 — integrate research brief labor norms

Planner-167's seeded rubric (oil change 0.5h, valve adjust 2-3h, etc.) is CONSISTENT with the pricing research brief. Same numbers, same skill multipliers (apprentice 1.35x, journeyman 1.00x, master 0.80x — note: Planner wrote +25% / 0% / -15% which is mathematically equivalent), same mileage adjustments.

**Merge during build:** use the fuller per-platform baseline table from the research brief (HD TC/M8 vs Honda CBR vs Yamaha R1 vs Suzuki GSX-R vs Kawasaki ZX vs dual-sport vs cruiser). Provides platform-specific priors Claude can anchor on.

**Critical write-back rule (Planner-167 emphasized):** estimated_hours MUST be written via `update_work_order({estimated_hours: ...})` — never raw SQL. Preserves Phase 161 whitelist guard. Test must `grep -v "UPDATE work_orders" src/motodiag/shop/labor_estimator.py`.

---

## Phase 168 — stdlib-only scheduling

Planner-168's stdlib-only (greedy + simulated annealing, no scipy/numpy) choice is right for shop scale (≤20 bays, ≤50 slots/day). Ship as planned.

**Calendar rendering risk:** 20-bay × 13-hour Rich table exceeds 80-col terminals. Planner mitigated with `--bay` filter and `Console().width` adaptive pagination. Acceptable.

---

## Architect-Auditor findings for Phase 161 finalize

All FIXes the Auditor surfaced must land in the Phase 161 finalize commit (not backfilled later):

1. **FAIL:** `implementation.md` line 170 footnote — update `"(currently v25 after Phase 160)"` → `"(currently v26 after Phase 161)"`. (Already partially done; re-verify.)
2. **FAIL:** `implementation.md` Database Tables — add `work_orders` row describing Phase 161 schema.
3. **FIX:** `implementation.md` Phase History — append Phase 161 row with full work_orders rollout details.
4. **FIX:** `implementation.md` Shop management CLI Commands subsection — bump from 22 subcommands → 34 (add the 12 `shop work-order {create,list,show,update,start,pause,resume,complete,cancel,reopen,assign,unassign}` entries).
5. **RECOMMENDED:** `implementation.md` — one-line footnote near Version header clarifying the package/doc version split (pyproject.toml tracks package releases; implementation.md tracks track-completion milestones).

`phase_log.md` project-level needs a Phase 161 completion entry per Auditor's caveat.

---

## Build order (revised, locked)

```
1. Finalize Phase 161 (regression-GREEN pending → apply Auditor fixes → commit + push)
2. Phase 162 build (override: 12 categories) → test → regression → finalize
3. Phase 162.5 build (NEW: shop/ai_client.py extraction) → test → regression → finalize
4. Phase 163 build (uses shop.ai_client; adopt research priority formula) → test → regression → finalize
5. Phase 164 build (reconcile name `list_parts_for_wo` with Phase 165 contract)
6. Phase 165 build (reuse Phase 153 parts catalog)
7. Phase 166 build (uses shop.ai_client; integrate pricing research brief)
8. Phase 167 build (uses shop.ai_client; integrate labor norms table)
9. Phase 168 build (stdlib scheduling)
10. Phase 169-173 (planned in later wave)
11. Phase 174 Gate 8
```

Parallel Builder dispatch possible only for non-migration-touching phases; 162→168 all touch `cli/shop.py` + migrations serial.
