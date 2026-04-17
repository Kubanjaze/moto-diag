# MotoDiag Phase 124 — Phase Log

**Status:** 🔄 In Progress | **Started:** 2026-04-17 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-17 22:50 — Plan written, v1.0
Fault code lookup CLI. New `src/motodiag/cli/code.py` orchestration (~250 LoC) + one `@cli.command code` with --make/--category/--explain/--vehicle-id/--symptoms/--model options. Default mode is DB-only (zero tokens) via `knowledge.dtc_repo`; `--explain` flag runs `FaultCodeInterpreter` for AI root-cause analysis with the same tier gates as Phase 123. Fallback chain: make-specific DB row → generic row → `engine.fault_codes.classify_code()` heuristic. `--category` lists all DTCs in a powertrain/system category (leverages Phase 111's dtc_category_meta). Pure orchestration — no migration. Reuses Phase 123's `_resolve_model`, `_load_vehicle`, `_load_known_issues`, `_parse_symptoms`. ~20 tests planned, all AI calls mocked.
