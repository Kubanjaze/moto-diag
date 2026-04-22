# MotoDiag Phase 162.5 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-21 | **Completed:** 2026-04-21
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-21 23:30 — Plan written (NEW micro-phase, not in original ROADMAP)

Inserted between Phase 162 and Phase 163 per `_research/consolidation_notes.md`. Three independent Track G AI planners (163, 166, 167) all flagged the same code triplication risk: each would re-implement Anthropic SDK setup, cost-cents math, prompt-cache toggling, JSON-fence extraction, and Phase 131 `ai_response_cache` integration. Rule-of-three extract: write the helper module BEFORE the 3 AI phases ship, save ~250 LoC across 163/166/167, and standardize "ephemeral prompt caching always-on" as the Track G AI default.

### 2026-04-21 23:35 — Build complete

Architect-direct. Single new module `src/motodiag/shop/ai_client.py` (273 LoC):

- `MODEL_ALIASES` dict (haiku/sonnet/opus → full ids).
- `MODEL_PRICING` dict (cents per million tokens, kept in sync with `engine/client.py`).
- `TokenUsage` + `AIResponse` frozen dataclasses.
- `resolve_model(alias_or_full)` — alias resolver, raises `ShopAIClientError` on unknown.
- `calculate_cost(model, usage)` — integer cents; cache_read at 10%, cache_creation at 125% per Anthropic pricing.
- `extract_json_block(text)` — strips ` ```json ... ``` ` or bare ` ``` ... ``` ` fences.
- `get_anthropic_client(api_key=None)` — lazy `@lru_cache(maxsize=1)` singleton; raises on missing SDK or unset key.
- `ShopAIClient` class — high-level wrapper with `.ask(user_prompt, system_prompt=None, cache_kind=None, cache_payload=None, ...)`. Sends system block with `cache_control={"type": "ephemeral"}` always-on. Phase 131 cache hit returns `cache_hit=True, cost_cents=0`. Cache miss calls Anthropic, persists, returns fresh `AIResponse`. Cache write errors silently swallowed (never break the call).
- Exception: `ShopAIClientError` wraps SDK errors + setup failures.

`shop/__init__.py` +12 LoC re-exports 10 names.

**Tests:** 20 GREEN across 2 classes (TestHelpers×12 + TestShopAIClient×8) in 2.08s. All Anthropic SDK calls mocked via `unittest.mock.patch` — zero live tokens. Tests cover: alias resolution + passthrough + unknown-error, cost math (input-only / cache-read / cache-creation / zero / unknown-model), JSON fence extraction (json-tagged / bare / none), client init alias resolution + unknown-error, system-block cache_control verification via mock kwargs assertion, cache hit returns zero cost, cache miss persists to Phase 131 store, SDK error wrapped in ShopAIClientError, cache write failure swallowed.

Build deviation: 20 tests vs ~15 planned — added 4 helper coverage variants + 1 ShopAIClient test. One iteration on mock token counts (had to bump to 1M+ for cost to round to non-zero cents); test now verifies exact 160¢ math.

**Targeted regression sample:** 183 GREEN in 99.43s covering Phase 131 (ai_response_cache — direct dependency) + Phase 160 (shop) + Phase 161 (work_orders) + Phase 162 (issues) + Phase 162.5 (this). Zero regressions.

### 2026-04-21 23:40 — Documentation finalization

`implementation.md` promoted to v1.1. Verification Checklist all `[x]`. Deviations + Results sections appended. Key finding: the rule-of-three extract pays for itself immediately — Phase 163 (next) will compose against `ShopAIClient.ask(...)` in 3 lines instead of ~80 LoC of duplicated SDK setup + cost math + cache integration. Phase 166 + 167 inherit the same savings. Ephemeral `cache_control` is now always-on default for Track G AI phases.

`phase_log.md` carries this entry.

Project-level updates:
- `implementation.md` Package Inventory: shop package status updated to note ai_client.py
- `implementation.md` Phase History: append Phase 162.5 row (NEW micro-phase, not in original ROADMAP)
- `phase_log.md` project-level: 162.5 closure entry — extraction landed; Track G AI phases (163/166/167) now compose on shared helper
- Project version 0.9.3 → 0.9.4 (micro bump)

Phase moved `docs/phases/in_progress/162_5_*.md` → `docs/phases/completed/162_5_*.md`.

**Key finding:** 162.5 is the most strategically important micro-phase in Track G — by extracting the AI helper BEFORE Phase 163 ships, we avoid 3 separate phases each re-implementing the same boilerplate, then needing a future consolidation phase to clean it up. Three planners independently flagging the duplication was the signal; acting on it immediately was the correct response. Total Phase 162.5 cost: ~30 minutes wall-clock + 0 AI tokens. Estimated savings across 163/166/167: ~250 LoC of duplication avoided + ~3 hours of consolidation refactor work that won't be needed.
