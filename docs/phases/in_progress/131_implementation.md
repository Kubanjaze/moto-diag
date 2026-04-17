# MotoDiag Phase 131 — Offline Mode + AI Response Caching

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-18

## Goal
Cache AI responses keyed on input hash so repeat lookups are free and the tool keeps working without internet. Supports three scenarios: (1) repeat-identical-query serves from cache transparently, zero tokens; (2) `--offline` flag forces cache-only mode, errors clearly on cache-miss; (3) shop-owner cache management (`motodiag cache stats/purge/clear`).

Applies to two AI call paths: `DiagnosticClient.diagnose()` (Phase 123's diagnose quick/start flow) and `FaultCodeInterpreter.interpret()` (Phase 124's `code --explain` flow). Migration 015 adds `ai_response_cache` table. New `src/motodiag/engine/cache.py` module + small integration edits in `engine/client.py` + `engine/fault_codes.py` + `cli/diagnose.py` + `cli/code.py`.

CLI surface:
```
motodiag diagnose quick --vehicle-id 42 --symptoms "won't start"   # cached on repeat
motodiag diagnose quick --vehicle-id 42 --symptoms "..." --offline  # cache-only, errors on miss
motodiag code P0115 --explain --vehicle-id 42 [--offline]
motodiag cache stats                                                  # count, total size, oldest
motodiag cache purge [--older-than 30]                                # delete rows older than N days
motodiag cache clear                                                  # delete all rows (confirms)
```

Outputs: migration 015 (`ai_response_cache` table), new `src/motodiag/engine/cache.py` (~180 LoC), new `src/motodiag/cli/cache.py` (~120 LoC), integration edits (~40 LoC across 4 files), ~30 new tests.

## Logic

### 1. Migration 015 — `ai_response_cache`
- `CREATE TABLE ai_response_cache`: id, cache_key TEXT UNIQUE NOT NULL, kind TEXT ('diagnose' | 'interpret'), model_used TEXT, response_json TEXT NOT NULL, tokens_input INTEGER, tokens_output INTEGER, cost_cents INTEGER, created_at TIMESTAMP, last_used_at TIMESTAMP, hit_count INTEGER DEFAULT 0
- 2 indexes: `cache_key` (for lookup), `created_at` (for purge-older-than queries)
- `SCHEMA_VERSION` 14 → 15
- Rollback drops the table

### 2. New `src/motodiag/engine/cache.py` (~180 LoC)

Pure cache logic — no CLI, no HTTP. Callable from both diagnose and interpret integrations.

- `_make_cache_key(kind, payload_dict) -> str` — canonicalizes the dict via `json.dumps(sort_keys=True, default=str)` and returns `sha256(canonical_bytes).hexdigest()`. `kind` prefixed into the hash so diagnose-keys and interpret-keys never collide even on identical payloads.
- `get_cached_response(cache_key, db_path=None) -> Optional[dict]` — SELECT-and-increment-hit-count on lookup. Returns the full row as a dict (response_json parsed back to a Python dict). Returns None on miss.
- `set_cached_response(cache_key, kind, model_used, response_dict, tokens_input, tokens_output, cost_cents, db_path=None) -> int` — INSERT OR REPLACE. Returns row id.
- `purge_cache(older_than_days=None, db_path=None) -> int` — DELETE rows older than N days (based on `created_at`). If `older_than_days` is None, deletes all. Returns rowcount.
- `get_cache_stats(db_path=None) -> dict` — Returns `{total_rows, total_hits, total_cost_cents_saved, oldest_entry_date, newest_entry_date}`.
- Cache payload includes the full diagnose response dict (parsed from `DiagnosticResponse` via `.model_dump()` or `.dict()` depending on Pydantic version) — so on hit, the caller reconstructs `DiagnosticResponse(**row["response"])`.

### 3. Integration: `DiagnosticClient.diagnose()` cache-first

In `engine/client.py`, add an optional `use_cache=True` kwarg to `diagnose()`. When True:
1. Build cache key from `(kind="diagnose", make, model_name, year, symptoms, description, mileage, engine_type, modifications, ai_model)`.
2. `get_cached_response(key)` — if hit, reconstruct DiagnosticResponse + TokenUsage (tokens_input/output=0 to reflect no-new-call) and return early.
3. If miss: current flow (call Claude API, parse response). After successful call, `set_cached_response(...)` with the fresh response.
4. Cache lookup and store errors are swallowed (log warning) — never break the actual diagnose flow due to cache issues.

When `use_cache=False`: skip cache entirely (existing behavior).

When `offline=True`: pass this through the existing `use_cache=True` path but raise a clear `RuntimeError("Offline mode: no cached response for this query. Either remove --offline or prime the cache with an online run.")` on cache miss.

### 4. Integration: `FaultCodeInterpreter.interpret()` cache-first

Same pattern in `engine/fault_codes.py`. Cache key inputs: `(kind="interpret", code, make, model_name, year, symptoms, mileage, ai_model)`. Response payload = `FaultCodeResult.model_dump()`.

### 5. CLI flag: `--offline`

On `diagnose quick`, `diagnose start`, `code --explain`: adds `--offline` boolean flag. When set, the orchestration (cli/diagnose.py `_run_quick` / `_run_interactive` and cli/code.py `_run_explain`) passes `offline=True` to the engine call. On RuntimeError from cache miss, the CLI catches and prints a clear red message with exit code 1.

### 6. New `src/motodiag/cli/cache.py` (~120 LoC)

`register_cache(cli_group)` attaches a `cache` group with 3 subcommands:

- `cache stats` — calls `get_cache_stats()`, prints rich Panel: total rows, total hits, total dollar value saved (from summed `cost_cents`), oldest/newest entry dates. Zero rows → "Cache is empty" message.
- `cache purge [--older-than INT] [--yes]` — calls `purge_cache(older_than_days)`. Default `--older-than 30`. Prompts for confirmation (skipped with `--yes`). Prints rowcount deleted.
- `cache clear [--yes]` — calls `purge_cache(older_than_days=None)`. Confirms by default ("This deletes ALL cached responses. Continue?"). Prints rowcount deleted.

Wire `register_cache(cli)` into `cli/main.py` after the other register_* calls.

### 7. Testing (~30 tests)

- `TestMigration015` (3): migration exists, `ai_response_cache` table present on fresh init, SCHEMA_VERSION >= 15.
- `TestCacheKey` (4): deterministic (same input → same key), `kind` prefix disambiguates (diagnose vs interpret on identical payload), `sort_keys` stability (dict ordering shouldn't matter), includes all relevant inputs.
- `TestCacheCRUD` (6): set + get round-trip; set with same key twice uses INSERT OR REPLACE; get on missing returns None; hit count increments on lookup; response_json round-trips through json; last_used_at updated on hit.
- `TestPurge` (4): purge all / purge older-than / purge with no matches / stats correctly report post-purge state.
- `TestDiagnoseIntegration` (4): `diagnose()` with cache miss calls AI + caches; second call with same inputs hits cache (zero new tokens); `use_cache=False` skips cache entirely; `offline=True` on miss raises clear error.
- `TestInterpretIntegration` (3): same pattern for `FaultCodeInterpreter.interpret()`.
- `TestCliCache` (4): `cache stats` shows counts; `cache purge --yes` deletes with no prompt; `cache clear --yes` clears all; empty-cache stats message.
- `TestCliOfflineFlag` (2): `diagnose quick --offline` on cache-miss errors cleanly; on cache-hit works (after a prior online run primed the cache).

All AI calls mocked via `patch("motodiag.engine.client.Anthropic")` or the injected diagnose_fn pattern. Zero live tokens.

## Key Concepts
- **Cache key is a SHA256 of canonical-JSON inputs** — deterministic, collision-resistant, independent of dict key ordering. `kind` prefix into the hash prevents cross-path collisions (a "diagnose with just 'P0115' as symptom" key never collides with an "interpret P0115" key).
- **Cache is transparent by default**: same prompt twice → same response, zero tokens on second call. Mechanic running `diagnose quick` three times in a row while tweaking other fields pays for the first call only.
- **`--offline` is explicit opt-in**: not default. Mechanics running `diagnose quick` without `--offline` always get live AI when connected; offline flag is for "I'm on the road, no signal, refresh the cached analysis".
- **No TTL by default**: cache entries live forever until explicit purge. Rationale: fault codes and symptoms don't change meaning week-to-week; a cached `P0115 → coolant sensor` from 6 months ago is still correct. If a shop owner wants fresh AI opinions, they `motodiag cache purge --older-than 30`.
- **Hit count tracks usefulness**: which cached queries actually pay off. `cache stats` reports total hits — informative for billing ("you saved $X this month via cache") and debug (unused cache entries could be purged).
- **Cache failures are non-fatal**: any SQLite error during lookup or store is logged but doesn't break the diagnose/interpret call. The cache is an optimization, not a dependency.
- **Response payload is JSON, not Pickle**: portability + inspectability + no code-execution risk if the cache DB is restored on a different machine.
- **Same cache table for both diagnose and interpret**: keeps schema simple. `kind` column partitions logically.

## Verification Checklist
- [ ] Migration 015 creates `ai_response_cache` with 2 indexes
- [ ] `SCHEMA_VERSION >= 15` forward-compat
- [ ] Rollback drops the table
- [ ] `_make_cache_key` is deterministic (same input → same hash)
- [ ] `_make_cache_key` with different `kind` produces different hashes
- [ ] `_make_cache_key` insensitive to dict key ordering
- [ ] `set_cached_response` + `get_cached_response` round-trip
- [ ] Duplicate `cache_key` is handled via INSERT OR REPLACE (no errors)
- [ ] `get_cached_response` on missing key returns None
- [ ] Hit count increments on each `get_cached_response` hit
- [ ] `last_used_at` updated on hit
- [ ] `purge_cache(older_than_days=N)` deletes correct rows
- [ ] `purge_cache()` (no arg) deletes all rows
- [ ] `get_cache_stats` returns accurate counts + min/max dates
- [ ] `DiagnosticClient.diagnose(use_cache=True)` caches on miss, serves from cache on hit
- [ ] Second `diagnose()` call with identical args reports tokens=0 (cache hit)
- [ ] `diagnose(use_cache=False)` skips cache entirely
- [ ] `diagnose(offline=True)` on cache miss raises RuntimeError with clear message
- [ ] `FaultCodeInterpreter.interpret(use_cache=True)` parallel behavior
- [ ] `interpret(offline=True)` on miss raises RuntimeError
- [ ] `motodiag cache stats` shows row count + hits + saved dollar total
- [ ] `motodiag cache stats` on empty cache shows "empty" message
- [ ] `motodiag cache purge --yes` deletes without prompt
- [ ] `motodiag cache clear --yes` deletes all rows
- [ ] `motodiag diagnose quick --offline` errors on cache miss
- [ ] `motodiag diagnose quick --offline` works after primed online run
- [ ] All 2271 existing tests still pass (zero regressions)
- [ ] Zero live API tokens burned

## Risks
- **Cache-key collisions**: SHA256 makes this mathematically negligible. Verified via deterministic-key tests.
- **Stale cache entries**: accepted — user controls TTL via explicit `cache purge`. A shop owner worried about model-drift can add a cron-style `motodiag cache purge --older-than 30` to their workflow.
- **Cache table grows unbounded**: at typical usage (dozens of calls per day per mechanic), 1 MB / ~1000 rows per year. Not a scale concern at any realistic volume.
- **Offline mode on fresh install**: first-ever use of `--offline` with no cache primes fails clearly. Documented in the `--offline` flag's help text.
- **Integration surface across 2 engine call paths**: a bug in the caching wrapper could break live diagnose/interpret. Mitigated by defensive try/except — cache failures are logged, never raised.
- **Pydantic v1 vs v2 dict serialization**: `.model_dump()` (v2) vs `.dict()` (v1). Project uses Pydantic 2.x so `model_dump` is correct; Builder verifies via `pyproject.toml` before coding.
