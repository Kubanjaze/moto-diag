# MotoDiag Phase 122 — Vehicle Garage Management + Photo-Based Bike Intake

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
First post-retrofit user-facing phase. Replaces the `garage` CLI stub with full vehicle management commands (add/list/remove) AND introduces photo-based bike identification — snap or upload a picture, get back `VehicleGuess(make, model, year_range, engine_cc_range, confidence, reasoning)` auto-populating VehicleBase fields. Uses Claude Haiku 4.5 by default (escalates to Sonnet when confidence < 0.5), with a sha256 image cache, 1024-pixel pre-send resize, tiered monthly caps, and an 80%-of-cap budget alert. New `src/motodiag/intake/` package plus one migration for the monthly-usage ledger.

CLI:
- `motodiag garage add --make X --model Y --year Z` — manual vehicle add
- `motodiag garage list` — list current user's garage
- `motodiag garage remove <id>` — delete vehicle
- `motodiag garage add-from-photo <path>` — NEW: photo intake flow
- `motodiag intake photo <path>` — NEW: identify-only (no auto-save) for preview

Outputs: `src/motodiag/intake/` package (3 files: `__init__.py`, `models.py`, `vehicle_identifier.py`), CLI expansion in `cli/main.py`, migration 013 (`intake_usage_log` table), ~40 new tests

## Logic

### 1. Migration 013 — intake usage ledger
- `CREATE TABLE intake_usage_log`: id, user_id (FK users, CASCADE), kind (enum: 'identify' for vision calls, 'manual_add' for hand entry — manual_add rows help future analytics without a separate table), model_used (text: 'haiku' / 'sonnet' / null for manual), confidence (REAL, nullable), image_hash (TEXT, nullable — sha256), tokens_input/tokens_output (INTEGER), cost_cents (INTEGER computed), created_at
- 3 indexes: user_id, (user_id, created_at), image_hash
- `SCHEMA_VERSION` 12 → 13
- Rollback drops the table

### 2. New `src/motodiag/intake/` package

**`models.py`** — 3 Pydantic models + 1 enum:
- `IdentifyKind` enum: `IDENTIFY` ("identify"), `MANUAL_ADD` ("manual_add")
- `VehicleGuess` — make, model, year_range (tuple[int, int]), engine_cc_range (tuple[int, int] | None for electric), confidence (float 0.0-1.0), reasoning (str), model_used (str), image_hash (str), powertrain_guess (ICE/ELECTRIC/HYBRID)
- `IntakeUsageEntry` — id, user_id, kind, model_used, confidence, image_hash, tokens_input, tokens_output, cost_cents, created_at
- `IntakeQuota` — tier, monthly_limit (int | None for unlimited), used_this_month (int), remaining (int), percent_used (float)

**`vehicle_identifier.py`** — main workhorse:
- `IDENTIFIER_SYSTEM_PROMPT` — tuned for motorcycle ID (tank badge/emblem, engine layout visible, fairing silhouette, exhaust note visible cues, fender lines). Instructs JSON-only output.
- `IDENTIFIER_USER_PROMPT` — template with slot for optional user-provided hints.
- `VehicleIdentifier` class:
  - `__init__(client=None, default_model="haiku", sonnet_escalation_threshold=0.5, db_path=None)`
  - `identify(image_path: str | Path, user_id: int = 1, hints: Optional[str] = None, force_model: Optional[str] = None) -> VehicleGuess` — orchestrates: quota check → hash → cache lookup → resize → base64 → vision call (Haiku) → parse → if confidence < threshold, escalate to Sonnet → log usage → return
  - `check_quota(user_id: int) -> IntakeQuota` — reads subscriptions.tier for user, counts `intake_usage_log` rows in current calendar month, returns remaining/percent_used
  - `_preprocess_image(path: Path) -> tuple[bytes, str]` — resize via Pillow to max 1024×1024 preserving aspect, return (bytes, sha256_hash)
  - `_cache_lookup(image_hash: str) -> Optional[dict]` — query most recent identify row for this hash, return cached guess if found (zero-token path)
  - `_call_vision(image_bytes: bytes, hints: Optional[str], model: str) -> tuple[VehicleGuess, TokenUsage]` — builds messages.create payload with image content block, parses JSON response
  - `_log_usage(user_id, kind, model_used, confidence, image_hash, tokens_input, tokens_output) -> None`
  - `_compute_cost_cents(model: str, in_tokens: int, out_tokens: int) -> int` — Haiku ~$1/MTok input, Sonnet ~$3/MTok input (rough — real pricing TBD in constants)

**Tier cap table** (hardcoded; Track H 178 will move to DB config):
```python
MONTHLY_CAPS = {
    "individual": 20,
    "shop": 200,
    "company": None,  # unlimited
}
BUDGET_ALERT_THRESHOLD = 0.80  # 80%
```

### 3. CLI expansion in `cli/main.py`

Replace the `garage` placeholder with a `@click.group`:
- `motodiag garage add --make --model --year [--vin --engine-cc --protocol --powertrain]` — manual add via VehicleBase
- `motodiag garage list [--customer-id N]` — list current garage
- `motodiag garage remove <vehicle_id>` — remove with confirmation prompt
- `motodiag garage add-from-photo <path> [--hints "sport bike"]` — runs `VehicleIdentifier.identify()` → shows preview → `Save this vehicle? [y/N]` → saves via `add_vehicle()` on confirm
- `motodiag intake photo <path> [--hints]` — identify-only, prints full VehicleGuess with confidence + reasoning, no save
- `motodiag intake quota` — prints tier, usage, remaining, percent_used — shows `[!]` warning if ≥80%

Uses `rich.table` + `rich.console` for pretty output (already a project dep). Reads current user via subscription inference (user_id=1 system user as default pre-auth — Track H 175 switches to real auth).

### 4. Image preprocessing details
- Uses `Pillow` (PIL). Not currently a project dep — adds to `pyproject.toml` `[project.optional-dependencies] vision = ["pillow>=10.0"]`. CLI gracefully degrades if Pillow missing: `add-from-photo` prints an install hint; `garage add` manual flow unaffected.
- Resize: `ImageOps.contain(img, (1024, 1024))` — preserves aspect ratio, never upscales.
- Re-encode as JPEG quality 85 for payload. PNG for images with alpha → flatten to white background.
- Hash computed on the **preprocessed bytes** (not original) so identical visual content with different metadata still hits the cache.

### 5. Cache semantics
- Cache hit = same image_hash + same model in an `intake_usage_log` row. Returns the stored `VehicleGuess` with `cached=True` marker, zero API call, zero tokens logged for the hit (separate lightweight log row with tokens=0).
- TTL: none — image → bike mapping doesn't stale. If we ever need TTL, add a `created_at` comparison.
- Privacy: hash is stored, not the image itself. Image bytes never persist.

### 6. Budget alert mechanism
- On each `identify()` call, after logging usage, check `percent_used` against `BUDGET_ALERT_THRESHOLD`.
- If percent_used crossed the 80% threshold (was below before this call, now at or above), include an `alert` field in the returned VehicleGuess: `"You've used 80% of your monthly photo-ID quota (16/20)."`
- CLI surfaces the alert in yellow.

### 7. Error handling
- File not found → `ValueError("Image file not found: {path}")`
- Unsupported format → `ValueError("Unsupported image format: {ext}")`
- Pillow missing → `RuntimeError` with install hint
- Quota exhausted → `QuotaExceededError` (new exception class) with tier + used/limit in message. CLI catches and suggests tier upgrade.
- Claude API error → caught and surfaces as `IntakeError` with response detail; CLI prints the user-facing message without stack trace.
- JSON parse failure (model returned malformed JSON) → retry once with a "respond ONLY with JSON" reinforcement. If second attempt also fails, raise `IntakeError`.

### 8. Testing strategy
- Mock the vision API (don't burn tokens on tests). `_call_vision` is replaced via a test fixture returning canned `VehicleGuess` + `TokenUsage`.
- Test scenarios (~40):
  - Preprocessing: resize math, hash determinism, JPEG re-encode bytes stable, PNG alpha handling
  - Cache: second call with same image returns cached result with 0 new tokens logged
  - Quota: individual user at 0/5/19/20 → correct remaining + percent_used + budget alert transitions
  - Quota exceeded: `QuotaExceededError` raised with clear message
  - Sonnet escalation: Haiku returns confidence 0.4 → triggers Sonnet call → final VehicleGuess uses Sonnet's higher-confidence result
  - Model used logged correctly for each call
  - VehicleGuess JSON parse: valid, malformed (retry path), malformed-twice (error)
  - CLI: `intake photo` prints full guess; `intake quota` shows warning at ≥80%
  - CLI: `garage add-from-photo` full flow with y/N confirm
  - Manual garage add/list/remove still work post-refactor (regression safety)

## Key Concepts
- **Two CLI surfaces for intake**: `garage add-from-photo` (commit flow) vs `intake photo` (preview flow). Lets mechanics try a photo without polluting the garage with bad guesses.
- **Cost per call**: Haiku 4.5 pricing roughly $1/MTok input, $5/MTok output (approximate — `_compute_cost_cents` uses constants, easy to tune). A 1024×1024 JPEG at quality 85 is ~100-200 KB → ~1500 image tokens. Plus 200 prompt tokens + 400 response tokens. Per identify call ≈ 0.3-0.5¢ at Haiku rates. Individual tier (20/mo) = $0.10 / user / month. Shop tier (200/mo) = $1.00 / user / month. Both below pricing floor.
- **The preprocessed-bytes hash** means re-uploading the same photo from a different camera app (same visual content but different EXIF) hits the cache. The alternative (hashing the original) would miss those cases.
- **Escalation strategy is narrow**: only Haiku → Sonnet, not Opus. If Haiku fails confidently and Sonnet isn't meaningfully better, we'd be burning expensive tokens without gain. Haiku 4.5 is already very good at "is this a Ducati Panigale or a Honda Fireblade" — the escalation is cheap insurance for the rare ambiguous shot.
- **Year as range, not single year**: visual ID rarely nails the exact MY. A CBR929RR could be a 2000 or 2001; a Street Triple could be any 675 year 2007-2016. The model returns `(2000, 2001)` and the CLI asks the user to refine.
- **Engine size as range too** for the same reason. Electric bikes get `None` — motor kW is a separate field.
- **Quota enforcement reads subscriptions.tier** — means the tier column retrofitted in Phase 118 becomes load-bearing here. Phase 109's env-var tier is the fallback when subscriptions table has no row for this user.
- **Image bytes never persist** — only the sha256 hash. Privacy-friendly and database-size-friendly.

## Verification Checklist
- [ ] Migration 013 creates intake_usage_log with 3 indexes
- [ ] Rollback drops the table cleanly
- [ ] IdentifyKind enum has 2 members; 3 Pydantic models validate
- [ ] `_preprocess_image` resizes to fit 1024×1024, preserves aspect
- [ ] Image hash is deterministic across re-runs
- [ ] JPEG re-encoding flattens PNG alpha to white background
- [ ] Missing Pillow → graceful error with install hint (not crash)
- [ ] Mock vision call: `identify()` returns VehicleGuess with all fields populated
- [ ] Cache hit: second call with same image returns cached guess, zero API tokens
- [ ] Sonnet escalation: Haiku confidence 0.4 → second call to Sonnet, final result uses Sonnet
- [ ] check_quota: individual tier returns remaining based on current-month rows
- [ ] check_quota: company tier returns `monthly_limit=None`, percent_used=0.0 always
- [ ] QuotaExceededError raised when individual at 20/20
- [ ] Budget alert appears when crossing 80% threshold (not on every subsequent call, just the crossing)
- [ ] Usage log records tokens_input, tokens_output, cost_cents, model_used
- [ ] CLI `garage add --make --model --year` saves vehicle
- [ ] CLI `garage list` shows vehicles in a rich table
- [ ] CLI `garage remove` prompts for confirmation (--yes to skip)
- [ ] CLI `garage add-from-photo <path>` runs identify, shows preview, asks y/N, saves on yes
- [ ] CLI `intake photo <path>` prints VehicleGuess without saving
- [ ] CLI `intake quota` shows current usage, warns ≥80%
- [ ] Malformed JSON from model → one retry, error after second failure
- [ ] File-not-found and unsupported-format raise clear ValueErrors
- [ ] Schema version assertions use `>= 13` (forward-compat)
- [ ] All 2002 existing tests still pass (zero regressions)

## Risks
- **Pillow optional dep**: if user doesn't install `motodiag[vision]`, photo flows fail gracefully but `garage add` manual flow still works. CI doesn't install `[vision]` by default — tests that need preprocessing mock Pillow or install it.
- **Real API cost during development**: tests mock vision. During manual QA, cap to 3-5 real calls — confirm model returns parsable JSON, then stop. The phase's verification does NOT require live API validation; the mock coverage is sufficient.
- **Pricing constants will drift**: `_compute_cost_cents` uses hardcoded rates. Acknowledged — Track T 343 (billing observability) owns dynamic pricing. Phase 122 stores `cost_cents` but nothing depends on its absolute accuracy.
- **Cache false positives**: two visually-different photos could hash the same after aggressive resize? Vanishingly unlikely with sha256 over ~200KB of bytes. Not a real risk.
- **Year/engine range ambiguity**: model could return `(1995, 2023)` if uncertain. Current threshold is just confidence < 0.5 escalate. A future enhancement: also escalate when `year_range` span > 10.
- **`intake` CLI group collides with existing command?** Checked — no existing `intake` command. Safe to add.
- **Tier cap enforcement assumes the user has a row in `subscriptions`**: if none exists, we default to `individual` tier via a helper. Documented in code.

## Deviations from Plan
(To be filled in during build.)

## Results
(To be filled in after regression.)
