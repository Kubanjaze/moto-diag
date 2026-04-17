# MotoDiag Phase 122 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-17 | **Completed:** 2026-04-17
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-17 21:20 — Plan written, v1.0
First post-retrofit user-facing phase. Replaces `garage` CLI stub with full vehicle management + photo-based bike identification using Claude Haiku 4.5 vision. New `src/motodiag/intake/` package with VehicleIdentifier orchestrator. Migration 013 adds `intake_usage_log` table. Tier caps 20/200/unlimited per month; 80% budget alert. Pillow as optional dep. Two CLI surfaces: `garage add-from-photo` (commit) and `intake photo` (preview).

### 2026-04-17 22:05 — Build complete (with 1 build-phase fix)
Created 3 files in new `src/motodiag/intake/` package + expanded `cli/main.py` + installed Pillow to .venv.

**Build-phase fix:**
- `test_garage_remove` initially failed because `init_db()` in the CLI reads `settings.db_path` from a `@lru_cache`-cached Settings instance. Monkeypatching `MOTODIAG_DB_PATH` doesn't take effect until the cache is invalidated. Added a `cli_db` fixture that calls `reset_settings()` after the env-var patch. Clean resolution — documented in Key Concepts.

Phase 122 tests (49): all pass. Full regression: **2051/2051 passing (zero regressions, 12:05 runtime)**.

**Zero live API tokens burned during build or testing** — all vision calls use the injected `vision_call=mock` pattern.

### 2026-04-17 22:10 — Documentation update
v1.0 → v1.1: all sections updated with as-built state, verification checklist marked `[x]`, Results table added, 3 deviations documented (placeholder cached VehicleGuess vs full-preservation, test count 49 vs ~40 planned, `cli_db` fixture not in plan but needed). Key finding: **the retrofit pays off immediately** — `subscriptions.tier` from Phase 118 is load-bearing for tier-based quota enforcement, and `users` from Phase 112 is the FK target of `intake_usage_log`. The substrate-first approach integrates cleanly with zero schema surprises. First customer-facing feature post-retrofit ships with full test coverage on a single phase.

Track D resumes at Phase 123 (interactive diagnostic session).
