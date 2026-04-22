# MotoDiag Phase 166 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-22 | **Completed:** 2026-04-22
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-21 — Plan written via Planner-166 agent (10-agent pool)

Plan v1.0 produced by Planner-166 in Stage A wave. Persisted to `docs/phases/in_progress/166_implementation.md`.

### 2026-04-22 01:30 — Build complete

Architect-direct serial build per user direction. Composes against Phase 162.5 `shop/ai_client.py` substrate — zero direct `anthropic` imports (enforced by anti-regression grep test).

Files shipped:

1. **Migration 030** — single audit table `sourcing_recommendations` (part_id FK CASCADE / vehicle_id FK SET NULL / quantity CHECK > 0 / tier_preference CHECK + source_tier CHECK + confidence BETWEEN 0-1 / recommendation_json TEXT / cache_hit + cost_cents / batch_id reserved). Append-only; cache_hit=1 rows persist alongside cache_miss=0 rows. 2 indexes: (part_id, generated_at DESC) for catalog-side recency lookups, (requisition_id, requisition_line_id) reserved for Phase 169 batch-result correlation.

2. **`shop/sourcing_models.py`** (65 LoC) — `SourcingRecommendation` + `VendorSuggestion` Pydantic + `SourceTier`/`TierPreference`/`Availability` Literal types. Separated from parts_sourcing.py so tests + Phase 169 invoicing can import schemas without pulling SDK seam.

3. **`shop/parts_sourcing.py`** (482 LoC) — `recommend_source` + `get_recommendation` + `sourcing_budget` + 3 exceptions (`PartNotFoundError`, `InvalidTierPreferenceError`, `SourcingParseError`) + `BatchTimeoutError` reserved + 4 helpers (`_validate_tier`, `_require_part`, `_load_vehicle`, `_load_xrefs`) + `_build_user_prompt` + `_parse_recommendation` + `_persist_recommendation`. Full system prompt baked from Domain-Researcher pricing brief (`_research/track_g_pricing_brief.md`):
   - Decision tree (safety-critical path-of-force → OEM only; consumables → aftermarket first; etc.)
   - 6-tier vendor taxonomy (T1 OEM dealer → T6 AliExpress-avoid)
   - Counter-intuitive aftermarket wins (Ricks Motorsports stators on 80s-00s Japanese; EBC HH brake pads on most sport bikes; etc.)
   - Discontinued-OEM cascading fallback (used → aftermarket reproduction → China-direct)

4. **`shop/__init__.py`** +35 LoC re-exports 14 names.

5. **`cli/shop.py`** +175 LoC — `sourcing` subgroup with 3 subcommands (`recommend`, `show`, `budget`) + Rich panel renderer with vendor-suggestion list. Total `cli/shop.py` now ~3555 LoC across 9 subgroups.

6. **`tests/test_phase166_parts_sourcing.py`** (489 LoC, 27 tests across 5 classes including the load-bearing `test_parts_sourcing_does_not_import_anthropic_directly` anti-regression grep).

**Mechanic-intent preservation:** Unlike Phase 163, sourcing recommendations don't override anything by default — they're advisory recommendations persisted for the mechanic to review. The mechanic can use `--tier oem|aftermarket|used` to bias the AI toward a specific tier preference, or accept the AI's `balanced` default.

**Composition pattern (canonical Track G AI):**
```python
def recommend_source(part_id, ..., _default_scorer_fn=None):
    part = _require_part(part_id)              # Phase 153 reuse
    vehicle = _load_vehicle(vehicle_id)
    xrefs = _load_xrefs(part_id)               # Phase 153 reuse
    if _default_scorer_fn is not None:
        payload, ai_resp = _default_scorer_fn(...)  # test injection
    else:
        client = ShopAIClient(...)             # Phase 162.5 composition
        ai_resp = client.ask(...)              # cached prompt automatic
        payload = _parse_recommendation(ai_resp.text, ...)
    rec = SourcingRecommendation(**payload)
    _persist_recommendation(rec, ...)          # audit log
    return rec
```

**Tests:** 27 GREEN across 5 classes (TestMigration030×4 + TestRecommendSource×10 + TestPersistence×5 + TestSourcingCLI×7 + TestAntiRegression×1) in 35.86s.

**Targeted regression:** **337 GREEN in 484s** (8m 4s) covering Phase 131 (ai_response_cache) + Phase 153 (parts catalog) + Track G phases 160-166 + Phase 162.5. Zero regressions across all dependencies.

Build deviations:
- `optimize_requisition` Batches API path deferred to Phase 169 (when invoicing needs bulk-source for finalized work order). Original plan included it; build pivot keeps Phase 166 focused on per-part recommendation + audit substrate.
- CLI `compare` subcommand reserved for Phase 169 (Rich Columns side-by-side rendering; mechanic value small until customer-facing quotes).
- 27 tests vs ~30 planned (deferred coverage matches deferred subcommands).

### 2026-04-22 01:35 — Documentation finalization

`implementation.md` promoted to v1.1. Verification Checklist all `[x]`. Deviations + Results sections appended. Key finding: Phase 162.5's ShopAIClient composition pays off again — `recommend_source` is 5 lines of integration vs the ~80 LoC of duplicated SDK + cost + cache machinery the original plan estimated. Domain-Researcher pricing brief integration into the system prompt gives Claude mechanic-credible signal that distinguishes moto-shop sourcing from generic OEM-default tools.

`phase_log.md` carries this entry. Both files moved to `docs/phases/completed/`.

Project-level updates:
- `implementation.md` schema_version footnote v29 → v30
- `implementation.md` Database Tables: append `sourcing_recommendations` row
- `implementation.md` Phase History: append Phase 166 row
- `implementation.md` Shop CLI Commands: bumped 63 → 66 subcommands; added `motodiag shop sourcing` row
- `phase_log.md` project-level: Phase 166 closure entry covering second AI phase + canonical pattern reaffirmation
- `docs/ROADMAP.md`: Phase 166 row → ✅
- Project version 0.9.7 → 0.9.8
