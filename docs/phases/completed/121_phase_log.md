# MotoDiag Phase 121 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-17 | **Completed:** 2026-04-17
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-17 20:50 — Plan written, v1.0
Gate R: Retrofit integration test. Single test file with 3 parts — (A) end-to-end shop workflow exercising every retrofit package, (B) migration replay verification, (C) CLI smoke test. No new production code. Pass/fail checkpoint before Track D resumes at Phase 122.

### 2026-04-17 21:00 — Build + gate execution complete
Created `tests/test_phase121_gate_r.py` with 10 integration tests across 4 test classes.

**Build-phase fixes (2 caught by test run):**
1. Used wrong function name `get_dtc_by_code` → real API is `get_dtc(code, make, db_path)`. Fixed.
2. Used `EngineType.ELECTRIC` for core/models.EngineType → real enum value is `EngineType.ELECTRIC_MOTOR`. Fixed.

**Design change mid-build (1 legitimate finding):**
Initial rollback-and-replay test failed with `duplicate column name: user_id`. Investigation revealed migration 005's rollback SQL intentionally does not drop ALTER-added columns (documented as harmless, pre-3.35 SQLite lacks DROP COLUMN). So in-place replay is not supported by design. Replaced the single replay test with two more focused tests: `test_two_fresh_dbs_have_identical_table_sets` (determinism) + `test_full_rollback_to_baseline_drops_retrofit_tables` (rollback at table level works). Documented limitation in test docstrings and implementation.md.

**Gate R execution — PASSED:**
- All 10 Gate R tests pass in isolation.
- Full regression: **2002/2002 passing** (was 1992, +10 for Gate R). Runtime 10:43.
- Zero regressions across the entire suite.

### 2026-04-17 21:10 — 🎉 RETROFIT COMPLETE
The retrofit track (phases 110-121) is closed. Summary:
- **12 phases** built: 110 (vehicle+protocol), 111 (DTC taxonomy), 112 (auth), 113 (CRM), 114 (workflows), 115 (i18n), 116 (feedback), 117 (reference), 118 (ops substrate), 119 (photo annotations), 120 (sound signatures), 121 (Gate R).
- **10 migrations** (003-012), **23 new tables**, **12 new packages** (auth, crm, workflows, i18n, feedback, reference, billing, accounting, inventory, scheduling + 2 media-package additions).
- **386 new tests**: 1616 → 2002 passing end-to-end. Zero regressions throughout.
- **One known limitation documented**: migration 005 ALTER-added columns don't drop on rollback, so in-place replay unsafe. Fresh init is fully deterministic (two-fresh-DB test proves it).
- **Forward-compat pattern formalized**: `>=` for schema versions, `issubset` for enum membership, `continue` for powertrain-specific skip (electric motor in combustion-only loops).
- **Next**: Track D resumes at Phase 122 (vehicle garage management + photo-based bike intake with Claude Haiku 4.5).

### 2026-04-17 21:15 — Documentation update
v1.0 → v1.1: all sections updated with as-built state, verification checklist marked `[x]`, Results table added, 3 deviations documented (test count reduction from ~20 to 10 but higher coverage; rollback-and-replay design change; added redundant import test). Key finding: **the retrofit never degraded the regression suite** — every phase maintained zero regressions, validating that the substrate-first approach (schema + CRUD before feature integration) scales cleanly across 12 phases and 23 tables.
