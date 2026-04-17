# MotoDiag Phase 124 — Fault Code Lookup Command (CLI)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Add `motodiag code <code>` — a fast CLI lookup that turns a DTC ("P0115", "C1234", a Kawasaki dealer code, a Zero `HV_*` code) into plain-English output: code format, system affected, description, severity, common causes, and fix summary. Default mode hits only the local DB (zero cost); `--explain` flag runs `FaultCodeInterpreter` for a richer AI-generated root-cause analysis (tier-gated like Phase 123). Uses the already-built `knowledge.dtc_repo` + `engine.fault_codes.classify_code` + `engine.fault_codes.FaultCodeInterpreter`. Pure orchestration — no migration, no new package.

CLI (as-built):
- `motodiag code <code>` — local DB lookup, zero tokens
- `motodiag code <code> --make Honda` — narrow to make-specific DTC entry
- `motodiag code <code> --explain --vehicle-id N [--symptoms "..."] [--model haiku|sonnet]` — AI-interpreted root cause
- `motodiag code --category hv_battery` — list all DTCs in a category (covers the browse-by-category use case from Phase 111)
- `motodiag code --help` — argparse help always works

Outputs: `src/motodiag/cli/code.py` (392 LoC CLI + orchestration), wired into `cli/main.py` via `register_code(cli)`, 33 new tests. **No migration.**

## Logic

### 1. New `src/motodiag/cli/code.py`
- `_lookup_local(code, make, db_path) -> Optional[dict]` — calls `dtc_repo.get_dtc(code, make, db_path)`; if that misses and a make was provided, retries `get_dtc(code, None)` explicitly for the generic row; returns None if neither.
- `_classify_fallback(code, make) -> dict` — when DB has nothing, uses `engine.fault_codes.classify_code()` to get at least format + system description. Returns a dtc_row-shaped dict with `source="classify_fallback"` marker so the renderer can show a yellow "no DB entry" banner.
- `_default_interpret_fn(code, vehicle, symptoms, ai_model, known_issues) -> (FaultCodeResult, TokenUsage)` — lazy-imports `DiagnosticClient` and `FaultCodeInterpreter`, calls `.interpret(...)`. Separated from orchestration so tests can mock it via `patch("motodiag.cli.code._default_interpret_fn", fn)`.
- `_run_explain(vehicle, code, symptoms, ai_model, db_path, interpret_fn=None)` — loads known issues via `_load_known_issues` (reused from cli.diagnose), calls the injected `interpret_fn` or the default. Returns `(FaultCodeResult, TokenUsage)`.
- `_render_local(row, console)` — rich Panel with code / description / category / severity / make. Numbered list for common_causes, fix_summary as text. If `source == "classify_fallback"`, prints a yellow "⚠ No DB entry — heuristic classification only" banner before the panel and suggests `--explain` at the end.
- `_render_explain(result, console)` — rich Panel header (code + format + system) + optional red "SAFETY-CRITICAL" banner + Table for possible_causes (rank/cause) + bulleted tests_to_confirm + bulleted related_symptoms + numbered repair_steps + hours+cost callout + optional notes panel.
- `_render_category_list(rows, console, category)` — rich Table for `--category` mode (code / description / severity / make); prints a "No DTCs found" message when the list is empty.
- `register_code(cli_group)` — attaches a SINGLE `@cli_group.command("code")` (not a subgroup, since the Phase 111 browse-by-category mode still operates on DTC concepts). If a legacy `code` command already exists on the group, it is evicted first.

### 2. CLI command (single command, not a group)
`motodiag code [DTC_CODE]`:
- `--make/-m TEXT` — narrow lookup; defaults to None (try make-specific first, fall back to generic)
- `--category TEXT` — if set, list all DTCs in category (skips other flags)
- `--explain` — enables AI interpretation (requires `--vehicle-id`)
- `--vehicle-id INT` — required when `--explain` is set
- `--symptoms TEXT` — comma/semicolon/newline-separated; passed to `FaultCodeInterpreter.interpret` as context
- `--model haiku|sonnet` — tier-gated via shared `_resolve_model` from `cli.diagnose`

Flow:
1. If `--category`: call `dtc_repo.get_dtcs_by_category(category, make=make)`, render as table.
2. If `--explain`: require `code` + `--vehicle-id`, else raise `ClickException`. Resolve model via `_resolve_model(current_tier().value, model_flag)`. Load vehicle; error if missing. Run `_run_explain`. Render.
3. Default: `_lookup_local(code, make)` → if hit, `_render_local(row)`; if miss, `_classify_fallback(code, make)` → `_render_local(fallback)` which prints the yellow banner. If `code` missing and no `--category`, raise `ClickException`.

### 3. Tier gating (reuse Phase 123 pattern)
- Imports `_resolve_model` from `motodiag.cli.diagnose`
- `--model sonnet` on individual tier: HARD mode raises `ClickException` with upgrade hint; SOFT mode falls back to Haiku with yellow warning.

### 4. Mock injection (reuse Phase 123 pattern)
- `_default_interpret_fn(code, vehicle, symptoms, ai_model, known_issues)` wraps `FaultCodeInterpreter.interpret()`.
- Tests use `patch("motodiag.cli.code._default_interpret_fn", fn)` — zero live tokens burned.

### 5. Testing (33 tests as-built)
- `_lookup_local` make-specific hit, generic fallback, None make lookup, total miss, miss-with-make
- `_classify_fallback` for P0115 (OBD-II generic), C1234 (chassis/harley_dtc), "NOTACODE" (unknown format), Kawasaki 2-digit dealer code
- `_render_local` for DB row, fallback with banner, and minimal row with no causes
- `_render_explain` for full result, safety-critical banner, and notes section
- `_render_category_list` empty + populated paths
- `_run_explain` injection check (kwargs flow-through)
- CLI `code P0115` local lookup (happy path)
- CLI `code P9999` → yellow unknown banner + classify fallback
- CLI `code P0115 --make Honda` narrows to make-specific row when it exists
- CLI `code P0115 --make Yamaha` falls back to generic (no #3 header note)
- CLI `code --category hv_battery` list mode (populated + empty)
- CLI `code P0115 --explain --vehicle-id N` happy path (mocked interpret)
- CLI `code P0115 --explain` without `--vehicle-id` → clear error
- CLI `code --explain --vehicle-id N` without code arg → clear error
- CLI `code P0115 --explain --vehicle-id MISSING` → "not found" error
- CLI `code P0115 --explain --model sonnet` on individual + HARD → tier error
- CLI `code P0115 --explain --model sonnet` on shop → succeeds with sonnet forwarded to interpret_fn
- CLI `code` (no code, no category) → error
- Registration: `code` is a command (not a group) and co-exists with existing CLI commands.

## Key Concepts
- **Two modes, one command**: default is DB-only and instant. `--explain` unlocks AI — same tier gates as `diagnose`. This keeps the default workflow free (the highest-frequency diagnostic workflow) while giving shops who pay for Sonnet a richer analysis on demand.
- **Fallback chain**: make-specific DB row → generic DB row → `classify_code()` heuristic. Mechanic always gets *something* back, even for unknown codes. The heuristic labels the code's format/system so the mechanic at least knows which subsystem to inspect.
- **`--category` as a browse tool** leverages Phase 111's `dtc_category_meta` table + the `dtc_category` column on `dtc_codes`. Useful for powertrain-specific exploration (`--category hv_battery` shows all EV-specific codes).
- **No new package** — a single `cli/code.py` orchestration module, registered via `register_code(cli)`. Consistent with Phase 123's pattern (`cli/diagnose.py` + `register_diagnose(cli)`).
- **Reuse over duplication**: `_resolve_model`, `_load_vehicle`, `_load_known_issues`, `_parse_symptoms` all imported from `cli.diagnose`. No copy-paste — and if those helpers ever move, `code.py` breaks at import time (surfaces the dependency early).
- **DB-only default keeps cost at zero**: fault code lookup is the highest-frequency diagnostic workflow; making it free by default avoids burning tokens on trivial lookups.
- **Legacy eviction**: `register_code` evicts any existing `code` command from the CLI group before attaching the new one. This lets Track D phases iteratively replace the earlier scaffolding from Phase 01 without the user needing to remove the inline version manually.

## Verification Checklist
- [x] `motodiag code --help` shows all options (make, category, explain, vehicle-id, symptoms, model)
- [x] `_lookup_local(code, make)` returns make-specific row when present
- [x] `_lookup_local(code, None)` returns generic row when no make-specific exists
- [x] `_lookup_local(missing_code)` returns None
- [x] `_classify_fallback("P0115", None)` returns a dict with code_format="obd2_generic"
- [x] `_classify_fallback("NOTACODE", None)` doesn't crash; returns a dict with `code_format == "unknown"` and fallback marker
- [x] `_render_local` prints code, category, severity, common_causes, fix_summary
- [x] `_render_local` shows yellow "No DB entry" banner only when `source == "classify_fallback"`
- [x] `_render_explain` prints possible_causes, tests_to_confirm, related_symptoms, repair_steps
- [x] `_render_explain` shows red "SAFETY-CRITICAL" banner when `safety_critical=True`
- [x] CLI `code P0115` renders DB entry for seeded code
- [x] CLI `code P9999` shows yellow "no DB entry" banner + classify result
- [x] CLI `code P0115 --make Honda` narrows correctly (hits make-specific)
- [x] CLI `code --category hv_battery` lists matching DTCs as table
- [x] CLI `code P0A80 --explain --vehicle-id N` runs interpret, prints result
- [x] CLI `code P0115 --explain` without `--vehicle-id` exits nonzero with error
- [x] CLI `code P0115 --explain --vehicle-id MISSING` exits nonzero with "not found" error
- [x] CLI `code P0115 --explain --model sonnet` on individual+HARD exits with tier error
- [x] `code` command registered in `cli.commands` alongside existing commands
- [x] All existing tests still pass after Phase 05 `test_code_help` update documented under Deviations (2123 total)
- [x] Zero live API tokens burned across test run (all interpret calls mocked via `patch`)

## Risks
- **Reuse imports from `cli.diagnose`** create a dependency: if `cli.diagnose` moves or renames, `cli.code` breaks. Mitigated by module-level imports (errors surface at import time, not at CLI invocation). Resolved — the module imports cleanly in CI and via `python -c`.
- **`classify_code` heuristic quality**: falls back to "unknown" for codes it doesn't recognize. Accepted — that's the fallback, and seeded DB will cover the common cases after Track B content phases run. The renderer's "run with `--explain`" hint gives the mechanic a path forward when the heuristic can't classify.
- **`--category` mode mixes two UIs in one command**: lookup-single-code vs list-by-category. Acceptable since both pivot on DTC concepts. Click's arg-vs-flag distinction keeps it unambiguous — the code arg is optional, and the logic validates that at least one mode is chosen.
- **Empty DB** (fresh install, no DTCs seeded yet): `_lookup_local` returns None → classify fallback kicks in. Mechanic still gets the format + system description.
- **Legacy `code` command collision**: Phase 01 wired an inline `code` command directly in `cli/main.py`. Resolved by deleting the inline version and guarding `register_code` with an explicit eviction step if the command name is already registered.

## Deviations from Plan
- **Phase 01's inline `motodiag code` command was replaced, not augmented.** The v1.0 plan glossed over this; in practice the two commands shared the `code` name so the old inline version had to go. The replacement preserves all of the old command's behavior (DB lookup with severity colors, causes list, fix summary) and adds the new modes.
- **Phase 05 regression test updated.** `tests/test_phase05_dtc.py::TestCLI::test_code_help` originally invoked `motodiag code` (no args) and expected exit 0 + "Usage" in output. The new command correctly raises `ClickException` on missing args per Phase 124's spec. The test was updated to invoke `motodiag code --help` instead, which is the proper surface for verifying CLI wiring. Documented here per CLAUDE.md's "No silent refactors" rule.
- **Test count: 33 instead of ~20.** The plan targeted "~20 tests"; the as-built file runs 33. Extra coverage came from splitting rendering tests across three classes (local/explain/category) and covering more CLI error paths explicitly (missing code arg with --explain, no-arg no-category error).
- **Production LoC: 392 instead of ~250.** The plan targeted ~250 LoC; the as-built module is 392 LoC. The overage is docstrings + the `_render_explain` renderer (which handles seven conditional sections) + the legacy-command eviction guard in `register_code`.

## Results
| Metric | Value |
|--------|-------|
| New files | 2 (`src/motodiag/cli/code.py`, `tests/test_phase124_code.py`) |
| Modified files | 2 (`src/motodiag/cli/main.py`, `tests/test_phase05_dtc.py`) |
| New CLI commands | 1 (`code`, replacing the legacy inline version) |
| New CLI modes | 3 (default DB lookup, `--category` list, `--explain` AI) |
| Production LoC | 392 (`cli/code.py`) |
| Test LoC | ~470 |
| New tests | 33 |
| Phase 05 tests updated | 1 (`test_code_help` switched to `--help`) |
| Total tests | 2123 passing |
| Regression runtime | ~9:58 (full suite) |
| Zero live API tokens | Yes — all `_default_interpret_fn` calls mocked via `patch` |
| Schema changes | None — reuses `dtc_codes` (Phase 03) + `dtc_category_meta` (Phase 111) |

Phase 124 lands the first DB-first CLI in the mechanic workflow: unlike `diagnose`, which always hits the AI, `code` answers most questions for free. The `--explain` escape hatch tier-gates the paid path without splitting the surface into two commands. The legacy-command eviction pattern in `register_code` sets up a clean template for later Track D phases that will similarly replace Phase 01's placeholder commands (`history`, `diagnose` placeholder) with real implementations.
