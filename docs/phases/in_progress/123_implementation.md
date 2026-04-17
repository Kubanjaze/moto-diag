# MotoDiag Phase 123 — Interactive Diagnostic Session (CLI)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Wire the AI engine into an **interactive** CLI diagnosis flow. Current state: `DiagnosticClient.diagnose()` (engine/client.py) works, `session_repo.create_session/set_diagnosis/close_session` persists, but the CLI has no `diagnose` command — it's all library-level. Phase 123 adds `motodiag diagnose start` (Q&A loop) and `motodiag diagnose quick` (one-shot). Each session persists to `diagnostic_sessions`; the Q&A flow calls the AI up to 3 clarifying rounds; output is a ranked diagnosis list + suggested additional tests + close-session action. Uses existing Phase 118 subscriptions tier to gate which model (individual → Haiku only; shop/company → Sonnet available with `--model sonnet`). No new packages; extends `cli/main.py` + thin orchestration in a new `cli/diagnose.py` helper module.

CLI:
- `motodiag diagnose start [--vehicle-id ID]` — interactive Q&A flow
- `motodiag diagnose quick --vehicle-id ID --symptoms "won't start, cold only"` — one-shot
- `motodiag diagnose list [--status open|closed]` — list past sessions
- `motodiag diagnose show <session_id>` — render a closed session's diagnosis

Outputs: `src/motodiag/cli/diagnose.py` (CLI + orchestration, ~300 LoC), expansion in `cli/main.py`, ~35 new tests. **No migration.**

## Logic

### 1. New `src/motodiag/cli/diagnose.py`

Thin orchestration module (not a new package; it's a CLI helper alongside `cli/registry.py` and `cli/subscription.py`):

- `_load_vehicle(vehicle_id: int, db_path) -> dict | None` — resolves a vehicle row from `vehicles` table, returns dict shaped for `DiagnosticClient.diagnose()` (make/model/year/engine_cc/engine_type).
- `_load_known_issues(make, model, year, db_path) -> list[dict]` — calls the existing `knowledge.issues_repo.search_known_issues` for matching known issues; feeds into diagnose() context.
- `_resolve_model(tier: str, cli_flag: Optional[str]) -> str` — enforces tier-based model access. Individual → Haiku forced; Shop/Company → Sonnet allowed via `--model sonnet`. Returns "haiku" or "sonnet".
- `_run_quick(vehicle, symptoms, description, model, db_path) -> tuple[int, DiagnosticResponse]` — creates a session row, calls `DiagnosticClient.diagnose()`, persists `set_diagnosis(...)`, returns (session_id, response).
- `_run_interactive(vehicle, model, db_path) -> tuple[int, DiagnosticResponse]` — the Q&A loop:
  1. Prompt mechanic for initial problem description (click.prompt).
  2. Parse freeform text into symptom list (simple split on commas + newlines for v1; future phase adds NLP).
  3. Call `DiagnosticClient.diagnose()` with what we have.
  4. If response has `additional_tests` AND diagnoses are low-confidence (top diagnosis `confidence < 0.7`), prompt mechanic to answer the top test question, append answer to description, re-call (up to 3 clarifying rounds total).
  5. Persist `set_diagnosis` with the final response.
- `_render_response(response, console)` — pretty rich.Panel output: vehicle summary + ranked diagnoses (cyan table: rank | diagnosis | confidence | rationale) + additional_tests as bullet list + notes section.

### 2. CLI expansion in `cli/main.py`

- `@cli.group diagnose`:
  - `diagnose start [--vehicle-id N] [--model haiku|sonnet]` — prompts for vehicle if no `--vehicle-id`, then runs interactive flow.
  - `diagnose quick --vehicle-id N --symptoms "..." [--description "..."] [--model haiku|sonnet]` — one-shot.
  - `diagnose list [--status open|closed]` — reuses `session_repo.list_sessions()`, renders as rich table.
  - `diagnose show <session_id>` — reuses `session_repo.get_session()`, renders the stored diagnosis JSON as panel.
- Tier-based error: if user passes `--model sonnet` on individual tier, CLI raises a clear error with upgrade hint.
- Replace the old `garage`-style pattern of having the command immediately run DB work — use the same `cli_db`-friendly pattern (read settings lazily inside each subcommand).

### 3. Model gating (tier enforcement)

Reuses `motodiag.cli.subscription.current_tier()` + Phase 118 `subscriptions.tier`:
- `individual` → `["haiku"]`
- `shop` → `["haiku", "sonnet"]`
- `company` → `["haiku", "sonnet"]`

If `--model sonnet` is requested and tier == individual, raise a clear CLI error (red text + exit 1): `"Sonnet access requires Shop tier ($99/mo) or higher. Your current tier: individual."`

### 4. Q&A loop termination conditions

Exit the clarifying-questions loop when any of:
- Top diagnosis confidence >= 0.7 (good enough).
- No `additional_tests` in the response.
- 3 clarifying rounds already done (hard cap to avoid token runaway).
- Mechanic enters empty string or "skip" or Ctrl-C (graceful).

### 5. Persistence pattern

Each CLI invocation that consults the AI creates exactly ONE session row. Rounds within an interactive flow are the SAME session — `set_diagnosis` overwrites with the final answer, and `tokens_used` accumulates across rounds in a single final `update_session` call. This keeps `diagnostic_sessions` row count = user-visible interactions, not API call count.

### 6. Testing strategy

- All `DiagnosticClient.diagnose()` calls mocked via an injectable `diagnose_fn` parameter on the internal `_run_*` functions. Tests construct canned `DiagnosticResponse` with varying confidence levels.
- Zero live API tokens burned across the entire test file.
- CLI tests use the same `cli_db` fixture pattern from Phase 122 (reset_settings after env-var patch).
- Test scenarios (~35):
  - `_resolve_model` for each tier × CLI flag combination
  - `_load_vehicle` returns dict / None / bad ID
  - `_load_known_issues` returns filtered list
  - `_run_quick`: session created, diagnose called with right context, session closed with diagnosis
  - `_run_interactive`: stops at high confidence (1 round), continues until confidence acceptable (2-3 rounds), caps at 3 rounds, terminates on empty/skip input
  - `_render_response` prints all fields (Panel + Table output captured)
  - `diagnose start` happy path
  - `diagnose quick` happy path
  - `diagnose quick` with nonexistent vehicle → clean error
  - `diagnose quick --model sonnet` on individual tier → error
  - `diagnose quick --model sonnet` on shop tier → succeeds
  - `diagnose list` with and without status filter
  - `diagnose show <id>` renders closed session
  - `diagnose show <nonexistent_id>` → clean error

## Key Concepts
- **Interactive vs quick**: two surfaces because workflows diverge. "Quick" is for experienced mechanics who already know what they saw ("dump my facts, give me a ranked list"). "Start" is for discovery — the AI asks, the mechanic answers, iteratively narrow.
- **Session = user-visible interaction, not API call count**: one interactive flow that burned 3 clarifying rounds produces ONE `diagnostic_sessions` row with `tokens_used` = sum of all 3. This keeps the session log readable as workflow history rather than API audit log (`intake_usage_log` from Phase 122 is the audit log).
- **Tier-based model access**: Phase 118's subscription.tier becomes load-bearing again. Individual tier locked to Haiku keeps costs bounded at ~$0.01/session; shop tier unlocks Sonnet for harder diagnoses (~$0.05-0.10/session).
- **Confidence threshold at 0.7** is conservative — AI is decent at motorcycle diagnosis but we don't trust it above that bar without explicit confirmation from the mechanic. Mechanic sees the confidence; they decide whether to act.
- **Hard cap at 3 clarifying rounds** prevents runaway token cost on a hard case. If 3 rounds can't converge, the best-guess diagnoses + suggested tests are persisted and the mechanic takes it from there offline.
- **Empty/skip input gracefully terminates**: respects mechanic time. They might answer two questions and realize the answer is obvious — `Ctrl+C` or empty input ends the loop cleanly, persists what we have.
- **No NEW migration**: Phase 123 uses existing `diagnostic_sessions` table (Phase 03). This phase is pure orchestration — the hard substrate was built long ago.

## Verification Checklist
- [ ] `motodiag diagnose --help` lists 4 subcommands (start, quick, list, show)
- [ ] `_resolve_model("individual", None)` returns "haiku"
- [ ] `_resolve_model("individual", "sonnet")` raises CliError with tier upgrade hint
- [ ] `_resolve_model("shop", "sonnet")` returns "sonnet"
- [ ] `_resolve_model("company", None)` returns "haiku" (default)
- [ ] `_load_vehicle(valid_id)` returns dict shaped for diagnose()
- [ ] `_load_vehicle(missing_id)` returns None
- [ ] `_load_known_issues(make, model, year)` returns filtered list by year-range
- [ ] `_run_quick` creates session, calls diagnose with right args, calls set_diagnosis, closes session
- [ ] `_run_interactive` stops after 1 round when top confidence >= 0.7
- [ ] `_run_interactive` runs 2 rounds when first confidence < 0.7 and second reaches threshold
- [ ] `_run_interactive` hard-caps at 3 rounds
- [ ] `_run_interactive` terminates gracefully on empty input / "skip"
- [ ] `diagnose quick --vehicle-id N --symptoms "..."` happy path: CLI prints ranked diagnoses
- [ ] `diagnose quick --vehicle-id missing` exits 1 with clear error
- [ ] `diagnose quick --model sonnet` on individual tier exits 1 with clear error
- [ ] `diagnose quick --model sonnet` on shop tier succeeds
- [ ] `diagnose start` prompts for symptoms, runs Q&A, saves session
- [ ] `diagnose list` renders rich table of sessions
- [ ] `diagnose list --status closed` filters correctly
- [ ] `diagnose show <id>` renders stored diagnosis panel
- [ ] `diagnose show <missing_id>` exits 1 with clear error
- [ ] All 2051 existing tests still pass (zero regressions)
- [ ] Zero live API tokens burned across test run

## Risks
- **Test runtime for interactive CLI**: Click's CliRunner handles stdin via `input=`; interactive-flow tests feed multi-line input strings. Tested pattern; works fine.
- **Q&A loop quality depends on AI's `additional_tests` field**: if the model doesn't produce useful tests, the loop skips naturally. Good enough v1 — Track R 318 (continuous learning) will tune prompt quality.
- **Confidence threshold of 0.7** is a guess. Track R's mechanic feedback loop (Phase 116 substrate) will tune this. Exposed as a module-level constant `CONFIDENCE_ACCEPT_THRESHOLD` so future phases can bump it.
- **Symptom parsing is dumb** (comma/newline split). Future Phase 125 (Quick diagnosis mode) + Track R 318 can do proper NLP. For now, mechanics are happy with "describe the problem naturally, separated by commas".
- **Simultaneous sessions for same vehicle**: nothing prevents this. Accepted — it's actually useful (compare two runs). `session_repo` already handles it.
- **Tier enforcement is advisory in soft-gate mode**: if `MOTODIAG_PAYWALL_MODE=soft` (Phase 109 default), sonnet-on-individual emits a warning but allows the call. In hard mode it errors. Respects the existing paywall framework.
