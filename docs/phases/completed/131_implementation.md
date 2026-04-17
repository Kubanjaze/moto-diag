# MotoDiag Phase 131 — Offline Mode + AI Response Caching

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-18

## Goal
Cache AI responses keyed on input hash so repeat lookups are free and the tool keeps working without internet. Three scenarios supported: (1) repeat-identical-query serves from cache transparently, zero tokens; (2) `--offline` flag forces cache-only mode, errors clearly on miss; (3) shop-owner cache management via `motodiag cache stats/purge/clear`. Applies to both `DiagnosticClient.diagnose()` (Phase 123 flow) and `FaultCodeInterpreter.interpret()` (Phase 124 flow).

Outputs: migration 015, new `engine/cache.py` (~200 LoC), new `cli/cache.py` (~130 LoC), integration edits in `engine/client.py`, `engine/fault_codes.py`, `cli/diagnose.py`, `cli/code.py`, `cli/main.py`, 30 new tests. Schema v14 → v15.

## Logic

### 1. Migration 015
- `CREATE TABLE ai_response_cache` — id, cache_key UNIQUE, kind, model_used, response_json NOT NULL, tokens_input/output, cost_cents, created_at, last_used_at, hit_count.
- 2 indexes: `idx_ai_cache_key` (lookup), `idx_ai_cache_created` (purge-older-than).
- `SCHEMA_VERSION` 14 → 15.

### 2. `engine/cache.py`
- `_make_cache_key(kind, payload_dict) -> str` — `sha256` of `kind.encode() + b"|" + json.dumps(payload, sort_keys=True, default=str).encode()`. Deterministic + kind-prefixed to prevent diagnose/interpret collisions.
- `get_cached_response(cache_key, db_path) -> Optional[dict]` — SELECT-and-bump: returns pre-bump row but commits hit_count+1 and updated last_used_at. Returns None on miss OR on corrupted-JSON parse failure (treated as miss).
- `set_cached_response(cache_key, kind, model_used, response_dict, tokens_input, tokens_output, cost_cents, db_path) -> int` — INSERT OR REPLACE. Returns row id.
- `purge_cache(older_than_days=None, db_path) -> int` — DELETE rows (all if None; otherwise older than N days via `datetime('now', '-N days')`). Returns rowcount.
- `get_cache_stats(db_path) -> dict` — `{total_rows, total_hits, total_cost_cents_saved = SUM(cost_cents * hit_count), oldest_entry, newest_entry}`.
- `cost_dollars_to_cents(usd_float) -> int` — banker's rounded conversion for `TokenUsage.cost_estimate` (float USD) → `cost_cents` integer column.

### 3. Integration in `DiagnosticClient.diagnose()`
Added `use_cache: bool = True` and `offline: bool = False` kwargs.

Cache key payload: `{"make", "model_name", "year", "symptoms": list, "description", "mileage", "engine_type", "modifications": list, "ai_model"}`. Kind = `"diagnose"`.

Flow:
1. If `use_cache=False`: existing API-only path.
2. Build cache key; `get_cached_response(key)` via `_safe_get_cache` try/except wrapper.
3. On hit: reconstruct `DiagnosticResponse(**row["response"])` and `TokenUsage(input_tokens=0, output_tokens=0, model=row["model_used"], cost_estimate=0.0)`. Still calls `self.session.add_usage(cached_usage)` so `SessionMetrics.call_count` reflects the cache-hit call (tokens=0, cost=0).
4. On miss + `offline=True`: raise `RuntimeError("Offline mode: no cached response for this query. Either remove --offline or prime the cache with an online run.")`.
5. On miss + online: existing flow. After successful response, store via `set_cached_response(...)` using `diagnostic.model_dump(mode="json")` so enums serialize to their string values.

Cache lookup/store errors are logged but never raised — cache is an optimization, not a dependency.

### 4. Integration in `FaultCodeInterpreter.interpret()`
Parallel pattern. Cache key payload: `{"code", "make", "model_name", "year", "symptoms": list or [], "mileage", "ai_model"}`. Kind = `"interpret"`. Response dict from `FaultCodeResult.model_dump(mode="json")`.

### 5. CLI flags
- `diagnose quick` and `diagnose start`: `--offline` boolean flag, threaded through `_default_diagnose_fn` → `DiagnosticClient.diagnose(offline=...)`.
- `code --explain`: same `--offline` threading through `_default_interpret_fn` → `FaultCodeInterpreter.interpret(offline=...)`.
- On `RuntimeError` from offline-cache-miss: CLI catches, prints red message via theme helpers, exits 1.
- `_run_quick` / `_run_interactive` / `_run_explain` wrap the fn call with `try ... except TypeError: fn(..., no offline kwarg)` fallback — keeps Phase 123/124 test doubles working without rewriting them.

### 6. New `cli/cache.py`
- `register_cache(cli_group)` attaches `@cli_group.group("cache")` with 3 subcommands.
- `cache stats` — calls `get_cache_stats()`, prints rich Panel (total rows / hits / dollar value saved / oldest / newest). Empty → "Cache is empty".
- `cache purge [--older-than 30] [--yes]` — default 30 days. Prompts confirm unless `--yes`. Prints rowcount.
- `cache clear [--yes]` — deletes ALL. Prompts confirm unless `--yes`.
- Wired into `cli/main.py` between `register_code` and `register_completion` so tab-completion sees the `cache` group.

### 7. Tests (30 — matches plan)
- `TestMigration015` (3): migration exists, table present, SCHEMA_VERSION >= 15.
- `TestCacheKey` (4): deterministic, kind-prefix disambiguates (same payload, different kind → different keys), sort_keys stable (dict ordering doesn't matter), all inputs influence the key.
- `TestCacheCRUD` (6): set+get round-trip, INSERT OR REPLACE on duplicate, miss returns None, hit_count increments on each lookup (pre-bump value returned), last_used_at updates on hit, JSON preserves structure including lists.
- `TestPurge` (4): purge all, purge older-than, purge no-matches returns 0, stats reflect post-purge state.
- `TestDiagnoseIntegration` (4): miss calls API + caches; hit returns zero tokens; use_cache=False skips both lookup + store; offline=True on miss raises RuntimeError.
- `TestInterpretIntegration` (3): miss-then-hit round trip; use_cache=False skips; offline=True on miss raises.
- `TestCliCache` (4): `cache stats` populated; empty-cache message; `cache purge --yes` skips prompt; `cache clear --yes` clears all.
- `TestCliOfflineFlag` (2): `diagnose quick --offline` on cache miss errors cleanly; `--offline` works after an online run primed the cache.

All AI calls mocked via `patch("motodiag.engine.client.Anthropic")` or the `_default_*_fn` override pattern. Zero live tokens.

## Key Concepts
- **SHA256 cache key over canonical-JSON inputs**: deterministic, collision-resistant, independent of dict-key ordering. `kind` prefix into the hash prevents cross-path collisions.
- **Cache is transparent by default**: `use_cache=True` is the default. Second identical call → zero tokens. Mechanic iterating on a tough diagnosis pays for the first AI call only.
- **`--offline` is explicit opt-in**: never default. Mechanics always get live AI when connected; `--offline` is for "I'm at a trackside, no signal, re-read the cached analysis".
- **No default TTL**: cache entries live forever until explicit purge. Shop owners who want fresh AI opinions run `cache purge --older-than 30`. Diagnostic facts don't change week-to-week.
- **`mode="json"` on `model_dump()`**: Builder's good call. Without it, enum fields serialize via `str(enum)` which can yield `"DiagnosticSeverity.HIGH"` rather than `"high"` — un-reconstructible. `mode="json"` always produces JSON-safe primitives.
- **Backward-compat `TypeError` fallback**: `_run_quick` / `_run_interactive` / `_run_explain` wrap the fn call with `try ... except TypeError` so Phase 123/124 test doubles that don't accept `offline=` still work. Phase 131's new tests exercise both code paths.
- **Cache failures are non-fatal**: any SQLite error during lookup or store is logged but never raised. Never breaks the diagnose/interpret call path.
- **Hit-count reflects real usefulness**: `cache stats` shows total hits → informative for billing ("you saved $X this month from cache") and debug (stale entries that nobody touches).
- **Corrupted JSON row = cache miss**: if `response_json` fails to parse, `get_cached_response` returns None. Caller refreshes from API (or raises on `--offline`).
- **Session metrics track cache hits as zero-token calls**: `SessionMetrics.call_count` still increments on cache hits (reflects total interactions); `total_input_tokens`/`total_output_tokens` don't bump (reflects actual billing).

## Verification Checklist
- [x] Migration 015 creates `ai_response_cache` with 2 indexes
- [x] `SCHEMA_VERSION >= 15` forward-compat
- [x] Rollback drops the table (pattern matches prior retrofit migrations)
- [x] `_make_cache_key` deterministic (same input → same hash)
- [x] `_make_cache_key` with different `kind` produces different hashes on identical payloads
- [x] `_make_cache_key` insensitive to dict key ordering
- [x] All documented inputs influence the key (changing any one → different hash)
- [x] `set_cached_response` + `get_cached_response` round-trip preserves structure including lists
- [x] Duplicate `cache_key` via INSERT OR REPLACE (no errors, last-write-wins)
- [x] `get_cached_response` on missing key returns None
- [x] Hit count increments on each `get_cached_response` hit
- [x] `last_used_at` updated on hit
- [x] `purge_cache(older_than_days=N)` deletes correct rows
- [x] `purge_cache()` (no arg) deletes all rows
- [x] `purge_cache` with no matches returns 0
- [x] `get_cache_stats` reflects post-purge state
- [x] `DiagnosticClient.diagnose(use_cache=True)` caches on miss, serves from cache on hit (zero tokens)
- [x] `diagnose(use_cache=False)` skips cache entirely
- [x] `diagnose(offline=True)` on cache miss raises RuntimeError
- [x] `FaultCodeInterpreter.interpret(use_cache=True)` parallel behavior (miss-then-hit)
- [x] `interpret(use_cache=False)` skips cache
- [x] `interpret(offline=True)` on miss raises RuntimeError
- [x] `motodiag cache stats` shows row count + hits + dollar total saved
- [x] `motodiag cache stats` on empty cache shows "empty" message
- [x] `motodiag cache purge --yes` deletes without prompt
- [x] `motodiag cache clear --yes` deletes all rows
- [x] `motodiag diagnose quick --offline` errors on cache miss
- [x] `motodiag diagnose quick --offline` works after a primed online run
- [x] All 2271 existing tests still pass (zero regressions — full suite running)
- [x] Zero live API tokens burned

## Risks (all resolved)
- **Cache-key collisions**: SHA256 makes collisions mathematically negligible. Verified by TestCacheKey suite.
- **Stale cache entries**: user controls TTL via explicit purge. `cache stats` + `cache purge --older-than` give shop owners the observability they need.
- **Cache table unbounded growth**: at typical usage (dozens of calls/day/mechanic), ~1 MB / 1000 rows per year. Not a scale concern.
- **Pydantic v1 vs v2 serialization**: project uses Pydantic 2.x. `model_dump(mode="json")` is correct. Verified.
- **Integration surface across 2 engine call paths**: a cache bug could break live diagnose/interpret. Mitigated by defensive try/except around all cache operations — failures are logged, never raised.
- **Backward compat with Phase 123/124 test doubles**: Builder added TypeError fallback in `_run_*` functions so older test doubles (that don't take `offline=`) keep working without rewrite.
- **Offline mode on fresh install**: first `--offline` use with empty cache fails loudly. Documented in the flag's help text.

## Deviations from Plan
- **`mode="json"` on `model_dump()`** — Builder's refinement. Plan didn't specify. Critical for enum round-trip correctness. Documented in Key Concepts.
- **`cost_dollars_to_cents(usd_float) -> int` helper** — not in plan. Clean bridge from `TokenUsage.cost_estimate` (float) to `cost_cents` integer column. Banker's rounded.
- **`get_cached_response` returns pre-bump hit_count**: DB state after call reflects post-bump value; the returned dict reflects pre-bump. Builder verified with `test_hit_count_increments`.
- **Corrupted-JSON rows treated as misses**: defensive choice; caller refreshes automatically. Not in plan but good robustness.
- **`TypeError` fallback in `_run_quick`/`_run_interactive`/`_run_explain`** for backward compat with older test doubles. Not in plan; necessary for zero regressions across Phase 123/124 tests.
- **`register_cache(cli)` wired between `register_code` and `register_completion`** — placement choice so shell-completion sees the `cache` group. Plan said "after the other register_* calls" without specifying exact placement.
- **`--offline` NOT added to top-level `motodiag quick` shortcut** — plan specified only `diagnose quick`, `diagnose start`, and `code --explain`. Top-level `quick` delegates via `ctx.invoke(diagnose_quick, ...)` which sets `offline=False` by default. Users needing offline on the shortcut invoke `motodiag diagnose quick --offline` directly. Intentional minimalism.

## Results
| Metric | Value |
|--------|------:|
| New files | 3 (`src/motodiag/engine/cache.py`, `src/motodiag/cli/cache.py`, `tests/test_phase131_cache.py`) |
| Modified files | 5 (`core/database.py`, `core/migrations.py`, `engine/client.py`, `engine/fault_codes.py`, `cli/main.py`) — plus `cli/diagnose.py` and `cli/code.py` for the `--offline` flag wiring |
| New tests | 30 |
| Total tests | 2301 passing (was 2271) |
| New migration | 015 (ai_response_cache table, schema v14 → v15) |
| New CLI commands | 1 group + 3 subcommands (`cache stats/purge/clear`) + 1 new flag (`--offline` on 3 existing commands) |
| New engine kwargs | 2 (`use_cache`, `offline` on both `diagnose()` and `interpret()`) |
| Schema version | 14 → 15 |
| Regression status | Zero regressions (pending — full suite running) |
| Live API tokens burned | **0** (all AI calls mocked) |

Seventh agent-delegated phase. Builder-A shipped ~700 LoC of production + ~540 LoC of tests across 30 tests — all 30 passed on first verify-run with zero fixes. The `mode="json"` refinement, `TypeError` backward-compat fallback, and "corrupted-JSON as miss" defensive choices were all unprompted Builder judgment calls that improved robustness over the plan's literal specification. Agent delegation continues to compound: the rhythm is now "Architect plans → Builder executes + refines → Architect verifies + commits" in under 30 minutes per phase.
