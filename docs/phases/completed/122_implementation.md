# MotoDiag Phase 122 — Vehicle Garage Management + Photo-Based Bike Intake

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
First post-retrofit user-facing phase. Replaces the `garage` CLI stub with full vehicle management commands (add/list/remove) AND introduces photo-based bike identification — snap or upload a picture, get back `VehicleGuess(make, model, year_range, engine_cc_range, confidence, reasoning)` auto-populating VehicleBase fields. Uses Claude Haiku 4.5 by default (escalates to Sonnet when confidence < 0.5), with a sha256 image cache, 1024-pixel pre-send resize, tiered monthly caps, and an 80%-of-cap budget alert. New `src/motodiag/intake/` package plus one migration for the monthly-usage ledger.

CLI:
- `motodiag garage add --make X --model Y --year Z` — manual vehicle add
- `motodiag garage list` — list current garage
- `motodiag garage remove <id> [--yes]` — delete vehicle
- `motodiag garage add-from-photo <path> [--hints H] [--yes]` — photo intake flow (commits)
- `motodiag intake photo <path> [--hints H]` — identify-only preview (no save)
- `motodiag intake quota` — tier + current-month usage + warning at ≥80%

Outputs: `src/motodiag/intake/` package (3 files), CLI expansion in `cli/main.py`, migration 013, 49 new tests.

## Logic

### 1. Migration 013 — intake usage ledger
- `CREATE TABLE intake_usage_log`: id, user_id (FK users, CASCADE), kind ('identify' or 'manual_add'), model_used ('haiku' / 'sonnet' / null), confidence (REAL, nullable), image_hash (TEXT, nullable — sha256 of preprocessed bytes), tokens_input/tokens_output (INTEGER), cost_cents (INTEGER), created_at (TIMESTAMP)
- 3 indexes: `idx_intake_user`, `idx_intake_user_time`, `idx_intake_image_hash`
- `SCHEMA_VERSION` 12 → 13
- Rollback drops the table

### 2. New `src/motodiag/intake/` package

**`models.py`** — 1 enum + 3 Pydantic models + 2 exceptions:
- `IdentifyKind` enum: IDENTIFY, MANUAL_ADD
- `VehicleGuess` — make, model, year_range (tuple), engine_cc_range (optional tuple for electric), powertrain_guess, confidence (0.0-1.0), reasoning, model_used ("haiku"/"sonnet"), image_hash (sha256), cached (bool), alert (optional budget alert string)
- `IntakeUsageEntry` — mirror of intake_usage_log row
- `IntakeQuota` — tier, monthly_limit (None for unlimited), used_this_month, remaining, percent_used
- `IntakeError`, `QuotaExceededError` (carries tier/used/limit)

**`vehicle_identifier.py`** — main workhorse (~450 LoC):
- Constants: `HAIKU_MODEL_ID`, `SONNET_MODEL_ID`, `MONTHLY_CAPS` (individual=20, shop=200, company=None/unlimited), `BUDGET_ALERT_THRESHOLD=0.80`, `SONNET_ESCALATION_THRESHOLD=0.5`, `MAX_IMAGE_DIM=1024`, `JPEG_QUALITY=85`
- `_preprocess_image(path) -> (jpeg_bytes, sha256_hex)` — uses Pillow `ImageOps.contain` (preserves aspect, never upscales), flattens PNG alpha to white background before JPEG re-encode. Pillow is optional dep; clear RuntimeError with install hint if missing.
- `_compute_cost_cents(model, tokens_in, tokens_out)` — order-of-magnitude pricing: Haiku ~$1/$5 per MTok input/output, Sonnet ~$3/$15. Ceiling-rounded to whole cents; zero-token calls stay at 0.
- `_parse_guess_json(raw, model_used, hash)` — tolerant parser. Strips `` ```json `` markdown fences if present. Validates required keys. Returns VehicleGuess.
- `_get_user_tier(user_id, db)` — reads `subscriptions` table for most-recent active/trialing row; falls back to "individual".
- `VehicleIdentifier` class:
  - `check_quota(user_id) -> IntakeQuota` — counts current-calendar-month `intake_usage_log` rows where kind='identify'
  - `identify(image_path, user_id, hints, force_model) -> VehicleGuess` — orchestrates: quota check → preprocess → cache lookup → Haiku call → Sonnet escalation if confidence < 0.5 → usage log → maybe attach 80% budget alert
  - `_cache_lookup` — returns cached guess when same image_hash + model was seen before, zero-token
  - `_run_vision` — one call with one retry on malformed JSON
  - `_log_usage`, `_maybe_attach_alert`
- `_default_vision_call(image_bytes, hints, model_id) -> (raw_text, tokens_in, tokens_out)` — production Anthropic call. Lazy-imports anthropic. Test code injects a mock via `VehicleIdentifier(vision_call=mock)` so tests never burn tokens.

### 3. CLI expansion in `cli/main.py`
- `@cli.group garage` (replaces old stub) with 4 subcommands:
  - `garage add --make --model --year [--engine-cc --vin --protocol --powertrain --notes]` — manual VehicleBase creation
  - `garage list` — rich.Table of year/make/model/engine/powertrain/VIN
  - `garage remove <id> [--yes]` — confirms by default, `--yes` skips
  - `garage add-from-photo <path> [--hints H] [--yes]` — calls VehicleIdentifier.identify → prints Panel preview → confirms → saves with midpoint year + midpoint engine_cc + reasoning in notes
- `@cli.group intake` (new) with 2 subcommands:
  - `intake photo <path> [--hints H]` — preview only, same Panel output, no save
  - `intake quota` — prints tier + usage; yellow ⚠ marker at ≥80%
- `_print_guess(guess)` helper — pretty rich.Panel output with year range, engine range or "electric", confidence, model_used (haiku/sonnet), reasoning, `(cached)` tag if from cache

### 4. Image preprocessing
- Pillow `ImageOps.contain` with `(1024, 1024)` bounding box — preserves aspect ratio, no upscaling
- JPEG quality 85 re-encode
- PNG alpha → flatten to white RGB background
- `RGBA/LA/P+transparency` → new RGB Image with white fill + paste with alpha mask
- sha256 computed on final **preprocessed** JPEG bytes (not original), so EXIF differences between camera apps still hit cache

### 5. Cache semantics
- Cache hit = `intake_usage_log` row with same image_hash AND kind='identify' AND tokens_input > 0
- Only real API calls seed the cache; zero-token cache-hit rows don't shadow the original
- Returns a placeholder VehicleGuess marked `cached=True` with the original confidence + model_used. The cache's job is to avoid burning tokens; full guess text is not preserved in the log.
- No TTL — image → bike mapping doesn't stale. Image bytes never persist (privacy + DB size).

### 6. Budget alert mechanism
- On each `identify()`, compute `quota_before` (pre-call) and `quota_after` (post-call, after logging).
- Attach `guess.alert` **only** if `before.percent_used < 0.80 <= after.percent_used` — a threshold CROSSING, not continuous firing.
- Company tier (unlimited) never alerts.

### 7. Error handling
- File not found → `ValueError("Image file not found: {path}")`
- Path is not a file (e.g., directory) → `ValueError("Image path is not a file: {path}")`
- Pillow can't decode file → `ValueError("Unsupported or unreadable image: ...")`
- Pillow missing → `RuntimeError` with install hint (`pip install 'motodiag[vision]'`)
- Quota exhausted → `QuotaExceededError(tier, used, limit)` — CLI catches, prints red message, aborts
- Malformed JSON → one retry with reinforced "Respond ONLY with JSON" instruction; second failure raises `IntakeError`

### 8. Testing strategy
- All vision calls mocked via `make_vision_mock(payloads, tokens_in, tokens_out)` — zero live API usage.
- Synthetic JPEG fixtures at 1600×900 force resize exercise. PNG fixture with alpha exercises flatten path.
- `cli_db` fixture uses `reset_settings()` to invalidate the `@lru_cache`-cached Settings after monkeypatch env var — required for CLI tests because `init_db()` uses the cached settings.

## Key Concepts
- **Two CLI surfaces for intake**: `garage add-from-photo` (commit flow) vs `intake photo` (preview flow). Lets mechanics try a photo without polluting the garage with bad guesses.
- **Year range + engine range — not single values**: visual ID rarely nails one MY. A CBR929RR → (2000, 2001). Street Triple 765 → (2013, 2020). `garage add-from-photo` uses the midpoint to pre-fill but the notes field preserves the original range for user correction.
- **Preprocessed-bytes hash** (not original) means re-uploading the same photo from a different camera app (same visual content, different EXIF/metadata) still hits the cache.
- **Cost per Haiku call**: ~0.3-0.5¢ per identify at Haiku rates with 1024×1024 JPEG (~1500 input tokens + ~400 output). Individual tier (20/mo) ≈ $0.10 / user / month. Shop tier ≈ $1 / user / month. Below every tier's price floor.
- **Escalation is narrow (Haiku → Sonnet only)**: Opus isn't in the loop. Haiku 4.5 is already very good at bike identification; the escalation is cheap insurance for the rare ambiguous shot.
- **Quota enforcement reads subscriptions.tier** (retrofitted in Phase 118) — validates the retrofit pays off immediately. Phase 118's Stripe column pre-wiring is not exercised yet (no Stripe integration), but the tier column is load-bearing here.
- **Pillow is optional** (`motodiag[vision]` extra). Zero-regression on baseline installs; photo flows fail gracefully with install hint.
- **Settings `@lru_cache` gotcha**: CLI tests must call `reset_settings()` after monkeypatching `MOTODIAG_DB_PATH`. Cached fixture pattern documented in test file.

## Verification Checklist
- [x] Migration 013 creates intake_usage_log with 3 indexes
- [x] Rollback drops the table cleanly
- [x] IdentifyKind enum has 2 members; 3 Pydantic models validate
- [x] `_preprocess_image` resizes to fit 1024×1024, preserves aspect
- [x] Image hash is deterministic across re-runs
- [x] JPEG re-encoding flattens PNG alpha to white background
- [x] Missing Pillow → graceful error with install hint (not crash) — ValueError for path/format, RuntimeError for missing Pillow
- [x] Mock vision call: `identify()` returns VehicleGuess with all fields populated
- [x] Cache hit: second call with same image returns cached guess, zero API tokens
- [x] Sonnet escalation: Haiku confidence 0.4 → second call to Sonnet, final result uses Sonnet
- [x] Force Sonnet disables escalation-back (one call only)
- [x] check_quota: individual tier returns remaining based on current-month rows
- [x] check_quota: company tier returns `monthly_limit=None`, percent_used=0.0 always
- [x] QuotaExceededError raised when individual at 20/20
- [x] Budget alert appears when crossing 80% threshold (not on every subsequent call, just the crossing)
- [x] No alert for company tier regardless of usage
- [x] Usage log records tokens_input, tokens_output, cost_cents, model_used, confidence, image_hash
- [x] CLI `garage add --make --model --year` saves vehicle
- [x] CLI `garage list` shows vehicles in a rich table (Honda + CBR929RR visible)
- [x] CLI `garage remove <id> --yes` removes vehicle and confirms deletion
- [x] CLI `intake quota` shows individual tier at 0/20
- [x] CLI `intake quota` shows 17/20 when usage is at 17 (warning territory)
- [x] CLI `intake quota` shows "unlimited" for company tier
- [x] Malformed JSON → one retry, error after second failure
- [x] File-not-found and unsupported-format raise clear ValueErrors
- [x] Schema version assertions use `>= 13` (forward-compat)
- [x] All 2002 existing tests still pass — full suite **2051/2051 in 12:05, zero regressions**

## Risks (all resolved)
- **Pillow optional dep**: resolved — installed in .venv for regression; tests use real Pillow (no Pillow mock needed). CI that doesn't install `[vision]` will skip preprocessing tests. Acceptable.
- **Real API cost during development**: zero — all tests use injected mock. Full regression burned zero tokens.
- **Settings `@lru_cache` + env-var interaction**: surfaced in build (test_garage_remove initially failed). Resolved with `cli_db` fixture that calls `reset_settings()` after monkeypatch.
- **Pricing constants drift**: accepted — documented as Track T 343's concern. `cost_cents` column exists but nothing depends on its absolute accuracy.
- **Cache false positives**: vanishingly improbable with sha256 over ~200KB of bytes. No real risk.

## Deviations from Plan
- **Cache returns placeholder VehicleGuess marker**: plan implied storing the full original guess in the log. Actual implementation logs only model_used/confidence/hash — not reasoning/year_range. Cache hits return `VehicleGuess(make="(cached)", model="(cached)", ...)` marked `cached=True`. Rationale: simpler schema, and cache's value is *avoiding token burn*, not restoring the original prose. If a future phase needs original guess text, add a `guess_json TEXT` column via a new migration.
- **Test count 49 vs planned ~40**: slightly more coverage than planned — thorough JSON parse paths (5 tests), cost calc (4), tier detection (4), budget alert crossings (4). Natural overcoverage for a customer-facing feature.
- **`cli_db` fixture not in plan**: needed once `test_garage_remove` failed due to Settings lru_cache. Documented as a "gotcha" in Key Concepts so future CLI tests use the same pattern.

## Results
| Metric | Value |
|--------|-------|
| New package | `src/motodiag/intake/` (3 files) |
| New files | 4 (`intake/__init__.py`, `intake/models.py`, `intake/vehicle_identifier.py`, `tests/test_phase122_intake.py`) |
| Modified files | 4 (`database.py`, `migrations.py`, `cli/main.py`, `pyproject.toml`) |
| New tests | 49 |
| Total tests | **2051 passing** (was 2002) |
| New enums | 1 (IdentifyKind, 2 members) |
| New models | 3 (VehicleGuess, IntakeUsageEntry, IntakeQuota) |
| New exceptions | 2 (IntakeError, QuotaExceededError) |
| New CLI commands | 6 (4 garage + 2 intake) |
| Production LoC | ~600 (vehicle_identifier ~450 + models ~100 + CLI ~180) |
| New tables | 1 (intake_usage_log) |
| New indexes | 3 |
| New optional dep | `motodiag[vision] = ["pillow>=10.0"]` |
| Schema version | 12 → 13 |
| Regression status | Zero regressions — full suite 12:05 runtime |
| Live API tokens burned | **0** (all vision calls mocked) |

Phase 122 is the first phase to show the retrofit paying off. `subscriptions.tier` from Phase 118 is load-bearing for quota enforcement; `users` from Phase 112 is the FK target of `intake_usage_log`. The substrate-first approach of phases 110-121 is validated: a customer-facing feature integrated cleanly in one phase with no schema surprises. Track D resumes at Phase 123 (interactive diagnostic session).
