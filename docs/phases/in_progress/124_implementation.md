# MotoDiag Phase 124 — Fault Code Lookup Command (CLI)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Add `motodiag code <code>` — a fast CLI lookup that turns a DTC ("P0115", "C1234", a Kawasaki dealer code) into plain-English output: code format, system affected, description, severity, common causes, and fix summary. Default mode hits only the local DB (zero cost); `--explain` flag runs `FaultCodeInterpreter` for a richer AI-generated root-cause analysis (tier-gated like Phase 123). Uses the already-built `knowledge.dtc_repo` + `engine.fault_codes.classify_code` + `engine.fault_codes.FaultCodeInterpreter`. Pure orchestration — no migration, no new package.

CLI:
- `motodiag code <code>` — local DB lookup, zero tokens
- `motodiag code <code> --make Honda` — narrow to make-specific DTC entry
- `motodiag code <code> --explain --vehicle-id N [--symptoms "..."] [--model haiku|sonnet]` — AI-interpreted root cause
- `motodiag code <code> --category hv_battery` — list all DTCs in a category (covers the browse-by-category use case from Phase 111)

Outputs: `src/motodiag/cli/code.py` (~250 LoC CLI + orchestration), wire into `cli/main.py` via `register_code(cli)`, ~20 new tests. **No migration.**

## Logic

### 1. New `src/motodiag/cli/code.py`
- `_lookup_local(code, make, db_path) -> Optional[dict]` — calls `dtc_repo.get_dtc(code, make, db_path)`; falls back to `get_dtc(code, None, ...)` (generic) if no make-specific row; returns None if neither.
- `_classify_fallback(code, make) -> dict` — when DB has nothing, use `engine.fault_codes.classify_code()` to get at least format + system description. Returns a dict shaped like a dtc_row but with `description` populated from classify and `source="classify_fallback"` marker.
- `_resolve_model(tier, flag)` — reuse from `cli.diagnose` (import, don't copy).
- `_run_explain(vehicle, code, symptoms, model, interpret_fn, db_path)` — load vehicle via `_load_vehicle`, load known issues via `_load_known_issues` (also reused from cli.diagnose), call `FaultCodeInterpreter.interpret()` (or injected mock), return `(FaultCodeResult, TokenUsage)`.
- `_render_local(code, row, console)` — rich Panel with code / category / severity / make. Table or bulleted list for common_causes, fix_summary as text.
- `_render_explain(result, console)` — rich Panel (header: code + format + system) + Table for possible_causes (rank/cause) + bulleted tests_to_confirm + related_symptoms + repair_steps + estimated_hours/cost callout.
- `register_code(cli_group)` — attaches the `code` Click command to the CLI.

### 2. CLI command (single command, not a group)
`motodiag code <code>`:
- `--make TEXT` — narrow lookup; defaults to None (try make-specific first, fall back to generic)
- `--category TEXT` — if set, list all DTCs in category (skips other flags)
- `--explain` — enables AI interpretation (requires `--vehicle-id`)
- `--vehicle-id INT` — required when `--explain` is set
- `--symptoms TEXT` — comma-separated; passed to `FaultCodeInterpreter.interpret` as context
- `--model haiku|sonnet` — tier-gated via shared `_resolve_model`

Flow:
1. If `--category`: call `dtc_repo.get_dtcs_by_category(category)`, render as table.
2. If `--explain`: require `--vehicle-id`; resolve model; run explain flow; render.
3. Default: `_lookup_local` → if hit, `_render_local`; if miss, `_classify_fallback` → render the format + system + the fact that no DB entry exists (yellow "unknown" banner).

### 3. Tier gating (reuse Phase 123 pattern)
- Import `_resolve_model` from `motodiag.cli.diagnose`
- `--model sonnet` on individual tier: HARD mode raises; SOFT mode falls back with warning

### 4. Mock injection (reuse Phase 123 pattern)
- `_default_interpret_fn(code, vehicle, symptoms, ai_model, known_issues)` wraps `FaultCodeInterpreter.interpret()`
- Tests use `patch("motodiag.cli.code._default_interpret_fn", fn)` — zero live tokens

### 5. Testing (~20 tests)
- `_lookup_local` with make-specific hit, generic fallback, total miss
- `_classify_fallback` for P0115 (OBD-II generic), C1234 (chassis), a Kawasaki dealer code
- `_resolve_model` import works (spot-check, most coverage is in Phase 123)
- `_render_local` prints fields (smoke check via captured console)
- `_render_explain` prints all sections
- CLI `code P0115` local lookup (happy path)
- CLI `code UNKNOWN` → yellow unknown banner + classify fallback
- CLI `code P0115 --make Honda` → narrows to make-specific if exists; falls back to generic otherwise
- CLI `code P0A80 --category hv_battery` OR `code --category hv_battery` (list mode)
- CLI `code P0115 --explain --vehicle-id N` happy path (mocked interpret)
- CLI `code P0115 --explain` without `--vehicle-id` → clear error
- CLI `code P0115 --explain --vehicle-id MISSING` → clear error
- CLI `code P0115 --explain --model sonnet` on individual+HARD → error
- Zero live API tokens burned

## Key Concepts
- **Two modes, one command**: default is DB-only and instant. `--explain` unlocks AI — same tier gates as `diagnose`.
- **Fallback chain**: make-specific DB row → generic DB row → `classify_code()` heuristic. Mechanic always gets *something* even for unknown codes.
- **`--category` as a browse tool** leverages Phase 111's `dtc_category_meta` table + the `dtc_category` column on `dtc_codes`. Useful for powertrain-specific exploration (`--category hv_battery` shows all EV-specific codes).
- **No new package** — a single `cli/code.py` orchestration module, registered via `register_code(cli)`. Consistent with Phase 123's pattern (`cli/diagnose.py`).
- **Reuse over duplication**: `_resolve_model`, `_load_vehicle`, `_load_known_issues`, `_parse_symptoms` all imported from `cli.diagnose`. No copy-paste.
- **DB-only default keeps cost at zero**: fault code lookup is the highest-frequency diagnostic workflow; making it free by default avoids burning tokens on trivial lookups.

## Verification Checklist
- [ ] `motodiag code --help` shows all options (make, category, explain, vehicle-id, symptoms, model)
- [ ] `_lookup_local(code, make)` returns make-specific row when present
- [ ] `_lookup_local(code, None)` returns generic row when no make-specific exists
- [ ] `_lookup_local(missing_code)` returns None
- [ ] `_classify_fallback("P0115", None)` returns a dict with code_format="obd2_generic" or similar
- [ ] `_classify_fallback("UNKNOWN", None)` doesn't crash; returns a dict with unknown-format marker
- [ ] `_render_local` prints code, category, severity, common_causes, fix_summary
- [ ] `_render_explain` prints possible_causes, tests_to_confirm, related_symptoms, repair_steps
- [ ] CLI `code P0115` renders DB entry for seeded code
- [ ] CLI `code UNKNOWN` shows yellow "no DB entry" banner + classify result
- [ ] CLI `code P0115 --make Honda` narrows correctly (hits make-specific)
- [ ] CLI `code --category hv_battery` lists matching DTCs as table
- [ ] CLI `code P0A80 --explain --vehicle-id N` runs interpret, prints result
- [ ] CLI `code P0115 --explain` without `--vehicle-id` exits nonzero with error
- [ ] CLI `code P0115 --explain --vehicle-id MISSING` exits nonzero
- [ ] CLI `code P0115 --explain --model sonnet` on individual+HARD exits with tier error
- [ ] `code` command registered in cli.commands alongside existing commands
- [ ] All 2090 existing tests still pass (zero regressions)
- [ ] Zero live API tokens burned across test run

## Risks
- **Reuse imports from `cli.diagnose`** create a dependency: if `cli.diagnose` moves or renames, `cli.code` breaks. Mitigated by an import-test (`from motodiag.cli.diagnose import _resolve_model` at module top surfaces errors at import time).
- **`classify_code` heuristic quality**: falls back to "unknown" for codes it doesn't recognize. Accepted — that's the fallback, and seeded DB will cover the common cases after Track B content phases run.
- **`--category` mode mixes two UIs in one command**: lookup-single-code vs list-by-category. Acceptable since both pivot on DTC concepts; Click's arg-vs-flag distinction keeps it unambiguous (code arg is required except in category mode, which is validated).
- **Empty DB** (fresh install, no DTCs seeded yet): `_lookup_local` returns None → classify fallback kicks in. Mechanic still gets the format + system.
