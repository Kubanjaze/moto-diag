# MotoDiag Phase 123 — Interactive Diagnostic Session (CLI)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Wire the AI engine into an **interactive** CLI diagnosis flow. The engine (`DiagnosticClient.diagnose()`) and session persistence (`session_repo`) already worked at the library level — what was missing was the CLI surface. Phase 123 adds `motodiag diagnose {start,quick,list,show}`. Each user-visible interaction = one `diagnostic_sessions` row; rounds within the interactive flow accumulate `tokens_used`. Uses Phase 118 subscription tier to gate model access (individual → Haiku forced; shop/company → Sonnet unlocked via `--model sonnet`). No new package — thin orchestration lives in a new `cli/diagnose.py` module alongside existing `cli/subscription.py` and `cli/registry.py`.

CLI:
- `motodiag diagnose start [--vehicle-id N] [--model haiku|sonnet]` — interactive Q&A flow
- `motodiag diagnose quick --vehicle-id N --symptoms "..." [--description "..."] [--model haiku|sonnet]` — one-shot
- `motodiag diagnose list [--status open|diagnosed|closed]` — rich table of sessions
- `motodiag diagnose show <session_id>` — render a stored diagnosis panel

Outputs: `src/motodiag/cli/diagnose.py` (~450 LoC orchestration + 4 Click commands), CLI registration in `cli/main.py`, 39 new tests. **No migration.**

## Logic

### 1. New `src/motodiag/cli/diagnose.py`

Thin orchestration module (not a new package). Public surface:

- **Constants**: `CONFIDENCE_ACCEPT_THRESHOLD = 0.7`, `MAX_CLARIFYING_ROUNDS = 3`, `_TIER_MODEL_ACCESS` table mapping tier → allowed models.
- **`_resolve_model(tier_value, cli_flag) -> str`**: picks "haiku" or "sonnet". Enforces tier gating based on `MOTODIAG_PAYWALL_MODE`: HARD raises `click.ClickException` with upgrade hint; SOFT silently falls back to Haiku with caller-side warning.
- **`_load_vehicle(vehicle_id, db_path)`** / **`_load_known_issues(make, model, year, db_path)`** / **`_parse_symptoms(text)`**: lookup + parsing helpers. Symptom parsing splits on commas, newlines, and semicolons (v1 — NLP upgrade is Phase 125's job).
- **`_default_diagnose_fn(...)`**: production `DiagnosticClient.diagnose()` wrapper. Separate from orchestration so tests inject mocks via `patch("motodiag.cli.diagnose._default_diagnose_fn", fn)` without needing the anthropic SDK.
- **`_run_quick(vehicle, symptoms, description, ai_model, db_path, diagnose_fn)`**: one session row, one AI call, persist, close.
- **`_run_interactive(vehicle, ai_model, db_path, diagnose_fn, prompt_fn)`**: Q&A loop — initial symptom prompt → AI call → check top confidence vs threshold → if low AND additional_tests available, ask one follow-up question and re-call → repeat up to `MAX_CLARIFYING_ROUNDS`. Terminates early on: empty input, "skip"/"stop"/"done", no additional_tests returned, confidence ≥ 0.7.
- **`_FakeUsage`**: tiny shim so `_persist_response` can treat accumulated token totals identically to a single `TokenUsage`.
- **`_persist_response(session_id, response, usage, ai_model, db_path)`**: writes `diagnosis`, `confidence`, `severity`, `repair_steps` via `set_diagnosis()`, then updates `ai_model_used` + `tokens_used`. Falls back to direct SQL if `update_session` rejects the fields (defensive — signature evolves).
- **`_render_response(response, console)`**: rich Panel (vehicle summary) + Table (ranked diagnoses with rank/diagnosis/confidence/severity/rationale) + bulleted additional_tests + notes Panel.
- **`register_diagnose(cli_group)`**: attaches the `diagnose` Click subgroup with 4 commands. Wired into `cli/main.py` via `register_diagnose(cli)`.

### 2. CLI registration in `cli/main.py`
- Added `from motodiag.cli.diagnose import register_diagnose` import
- Call `register_diagnose(cli)` after all `@cli.command()` definitions but before `if __name__ == "__main__"`
- Old `history` command docstring updated to point at `diagnose list`

### 3. Tier enforcement
- Reads `current_tier()` from `cli/subscription.py` (which honors `MOTODIAG_SUBSCRIPTION_TIER` env var)
- `individual` → Haiku only
- `shop` and `company` → Haiku + Sonnet
- `--model sonnet` on individual tier:
  - HARD mode: `click.ClickException` with "Shop tier ($99/mo) or higher" message
  - SOFT mode: falls back to Haiku, CLI prints yellow warning `"⚠ Sonnet requires Shop tier+. Falling back to Haiku (soft enforcement)."`

### 4. Q&A loop termination
Exit conditions (any one triggers break):
- Top diagnosis confidence ≥ `CONFIDENCE_ACCEPT_THRESHOLD` (0.7)
- Response has no `additional_tests`
- `MAX_CLARIFYING_ROUNDS` (3) reached
- Mechanic enters empty string, or "skip" / "stop" / "done" (case-insensitive)

### 5. Persistence pattern (one row per user interaction)
- `_run_interactive` creates one `diagnostic_sessions` row even if the loop runs 3 rounds
- Tokens accumulate across rounds; final `set_diagnosis` overwrites with the last response; `tokens_used` = sum of all rounds
- Session transitions: `open` → `diagnosed` (via `set_diagnosis`) → `closed` (via `close_session`)

### 6. Testing
- All AI calls mocked via `make_diagnose_fn(responses, usages)` factory that yields canned responses in order
- Mock uses `types.SimpleNamespace` (not a class) because Python class bodies don't close over enclosing-function parameters — fixed during build when `_Resp` class couldn't see `diagnoses` kwarg
- `cli_db` fixture mirrors Phase 122 pattern: patch `MOTODIAG_DB_PATH` + `reset_settings()` to invalidate `@lru_cache` on Settings
- Zero live API tokens burned — all `_default_diagnose_fn` calls intercepted via `patch()`

## Key Concepts
- **Interactive vs quick** are two CLI surfaces because the workflows diverge. "Quick" dumps known facts and returns ranked diagnoses — for experienced mechanics. "Start" is discovery-first — AI asks, mechanic answers, iteratively narrow. Both end at the same persisted session shape.
- **Session = user-visible interaction, not API call count.** A single interactive flow that burned 3 rounds = ONE row in `diagnostic_sessions` with `tokens_used = sum(all 3)`. The audit log for per-call billing lives in `intake_usage_log` (Phase 122) — we didn't replicate that here.
- **Tier gating on model access** makes Phase 118's `subscriptions.tier` load-bearing a second time: Phase 122 used it for quota enforcement; Phase 123 uses it for model access. The retrofit continues to pay off.
- **Confidence threshold at 0.7 is conservative.** AI is decent at motorcycle diagnosis but not trustworthy enough above 0.7 without explicit confirmation from the mechanic. Exposed as `CONFIDENCE_ACCEPT_THRESHOLD` so Track R 318 (continuous learning) can tune based on feedback data.
- **Hard cap at 3 rounds** prevents runaway token cost on ambiguous cases. The best-guess diagnoses + suggested tests persist even if the loop didn't converge; mechanic takes it from there offline.
- **Empty/skip input gracefully terminates** — respects mechanic time. If someone realizes the answer after round 2, they hit enter and we persist what we have.
- **`diagnose_fn` injection pattern** (the same pattern Phase 122 used for `vision_call`) keeps tests clean. No mock frameworks, no module-level monkeypatching of the anthropic SDK — just pass a callable.
- **No new migration.** Phase 03's `diagnostic_sessions` table already has every column we need (diagnosis, confidence, severity, repair_steps, ai_model_used, tokens_used). Substrate paid off.

## Verification Checklist
- [x] `motodiag diagnose --help` lists 4 subcommands (start, quick, list, show)
- [x] `_resolve_model("individual", None)` returns "haiku"
- [x] `_resolve_model("individual", "sonnet")` with HARD mode raises with tier upgrade hint
- [x] `_resolve_model("individual", "sonnet")` with SOFT mode falls back to "haiku"
- [x] `_resolve_model("shop", "sonnet")` returns "sonnet"
- [x] `_resolve_model("company", "sonnet")` returns "sonnet"
- [x] `_resolve_model("shop", "opus")` raises (unknown model)
- [x] `_resolve_model` is case-insensitive for both tier and model flag
- [x] `_load_vehicle(valid_id)` returns dict; `_load_vehicle(missing_id)` returns None
- [x] `_load_known_issues` returns a list (empty OK)
- [x] `_parse_symptoms` splits on commas, newlines, semicolons; strips whitespace; drops empties
- [x] `_run_quick` creates session, calls diagnose with right args, set_diagnosis, closes
- [x] `_run_interactive` exits after 1 round when top confidence ≥ 0.7
- [x] `_run_interactive` runs 2 rounds when first < 0.7 + second ≥ 0.7
- [x] `_run_interactive` hard-caps at 3 rounds even when confidence stays low
- [x] `_run_interactive` terminates on empty input
- [x] `_run_interactive` terminates on "skip"
- [x] `_run_interactive` terminates when no additional_tests returned
- [x] `_run_interactive` accumulates tokens across rounds (650 + 800 = 1450 in tests)
- [x] `_persist_response` writes diagnosis + token totals + ai_model_used
- [x] `_persist_response` handles empty diagnoses list (falls back to `response.notes`)
- [x] `_render_response` prints vehicle summary, diagnoses table, additional_tests bullets, notes panel
- [x] `_render_response` shows "No definitive diagnosis" when diagnoses list is empty
- [x] CLI `diagnose quick` happy path: session created + ranked diagnoses printed
- [x] CLI `diagnose quick --vehicle-id 99999` exits nonzero with "not found"
- [x] CLI `diagnose quick --model sonnet` on individual+HARD exits nonzero with Shop tier message
- [x] CLI `diagnose quick --model sonnet` on shop tier succeeds
- [x] CLI `diagnose list` shows "No sessions yet" when empty
- [x] CLI `diagnose list` shows session after `diagnose quick`
- [x] CLI `diagnose list --status closed` filters correctly
- [x] CLI `diagnose list --status open` returns no sessions after quick completes (status=closed)
- [x] CLI `diagnose show <id>` renders stored diagnosis
- [x] CLI `diagnose show <missing>` exits nonzero with "not found"
- [x] `diagnose` group registered alongside all existing CLI groups (info/tier/garage/intake/diagnose)
- [x] All 2051 existing tests still pass — full suite **2090/2090 in 11:43, zero regressions**
- [x] Zero live API tokens burned across test run (all `_default_diagnose_fn` calls mocked via `patch`)

## Risks (all resolved)
- **Class-body closure**: test helper `make_response` originally used a nested class; Python doesn't let class bodies close over enclosing-function parameters. Fixed with `types.SimpleNamespace` — cleaner anyway.
- **Mock injection boundary**: chose `patch("motodiag.cli.diagnose._default_diagnose_fn", fn)` at the module level rather than passing `diagnose_fn=` through the CLI. Rationale: CLI commands don't accept kwargs, and patching the module function is the narrowest surface. Production behavior unchanged.
- **Q&A loop quality depends on AI's `additional_tests` field**: if the model doesn't produce useful tests, the loop terminates naturally on the "no additional_tests" branch. Good enough for v1.
- **Confidence threshold of 0.7 is a guess** — Track R feedback data will tune it.
- **Soft-mode silent downgrade**: individual-tier users who pass `--model sonnet` during development get a warning + Haiku, not an error. Intentional — respects Phase 109 paywall strategy ("soft during dev, hard at Track H").

## Deviations from Plan
- **`diagnose_fn` injection via `patch()` in tests, not via CLI kwargs** — tests patch the module-level default function rather than threading an extra kwarg through every CLI command. Cleaner and matches how production code works.
- **Test count 39 vs planned ~35**: four extras — one for `test_tokens_accumulate_across_rounds` (wasn't in the plan's checklist), one for `test_no_additional_tests_stops_even_at_low_confidence`, two rendering-output tests.
- **`_FakeUsage` helper class added** in production code — plan didn't mention it. Needed because `_persist_response` takes a `TokenUsage`-shaped object, and the interactive flow needs to pass accumulated totals (which aren't a natural `TokenUsage` since they span multiple API calls). Shim keeps the persist path single-codepath.

## Results
| Metric | Value |
|--------|-------|
| New files | 2 (`src/motodiag/cli/diagnose.py`, `tests/test_phase123_diagnose.py`) |
| Modified files | 1 (`src/motodiag/cli/main.py` — import + `register_diagnose(cli)` call + history docstring) |
| New tests | 39 |
| Total tests | **2090 passing** (was 2051) |
| New CLI commands | 4 (`diagnose start/quick/list/show`) |
| Production LoC | ~450 (`diagnose.py`) + ~3 wiring lines in `main.py` |
| New tables | 0 |
| New migrations | 0 |
| Schema version | 13 (unchanged — substrate pays off again) |
| Regression status | Zero regressions — full suite 11:43 runtime |
| Live API tokens burned | **0** (all calls mocked via `patch`) |

Phase 123 turns the AI engine into a first-class CLI feature. The session model (Phase 03) gave us `diagnosis` + `confidence` + `severity` + `repair_steps` + `ai_model_used` + `tokens_used` columns for free. Phase 118's `subscriptions.tier` now gates model access in addition to quota enforcement. The retrofit substrate continues to pay off with zero schema surprises. Track D resumes at Phase 124 (Fault code lookup command).
