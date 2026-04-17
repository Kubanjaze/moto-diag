# MotoDiag Phase 123 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-17 | **Completed:** 2026-04-17
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-17 22:20 — Plan written, v1.0
Interactive diagnostic session CLI. New `src/motodiag/cli/diagnose.py` orchestration module + 4 CLI subcommands (start/quick/list/show). Tier-based model access (individual → Haiku; shop/company → Sonnet available). Q&A loop terminates at confidence ≥ 0.7, empty/skip input, or 3-round hard cap. One `diagnostic_sessions` row per user-visible interaction; rounds accumulate tokens_used. No migration — reuses Phase 03 substrate.

### 2026-04-17 22:40 — Build complete (with 1 build-phase fix)
Created `src/motodiag/cli/diagnose.py` (~450 LoC: constants + helpers + orchestration + rendering + Click commands via `register_diagnose(cli_group)`). Wired into `cli/main.py`. Added `_FakeUsage` shim so `_persist_response` can accept accumulated token totals across interactive rounds.

**Build-phase fix (caught during test run):**
- Test helper `make_response` initially used a nested class; Python class bodies don't close over enclosing-function params. Switched to `types.SimpleNamespace` — cleaner anyway.

**Test run:**
- Phase 123 tests (39): all pass.
- Full regression: **2090/2090 passing (zero regressions, 11:43 runtime)**.
- Zero live API tokens burned — all `_default_diagnose_fn` calls intercepted via `patch()`.

### 2026-04-17 22:45 — Documentation update
v1.0 → v1.1: all sections updated with as-built state, verification checklist marked `[x]`, Results table added, 3 deviations documented (`patch()`-based mock injection instead of diagnose_fn kwarg, test count 39 vs 35, `_FakeUsage` shim not in plan).

Key finding: **Phase 118's `subscriptions.tier` is now load-bearing a second time** — Phase 122 used it for quota enforcement, Phase 123 uses it for model access. The retrofit keeps paying off: Phase 123 required **zero new migrations** because Phase 03's `diagnostic_sessions` table already had every column needed (`diagnosis`, `confidence`, `severity`, `repair_steps`, `ai_model_used`, `tokens_used`). The substrate-first discipline of phases 110-121 continues to compound.

Track D resumes at Phase 124 (Fault code lookup command).
