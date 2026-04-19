# MotoDiag Phase 152 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-18 | **Completed:** 2026-04-19
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-18 18:45 — Plan written, v1.0

Fifth Track F phase. Persistent service-history log + adds `vehicles.mileage` column. Closes Phase 148 deferral. Migration 020: ALTER vehicles + new service_history table (CHECK-gated event_type, FK CASCADE vehicle, FK SET NULL mechanic) + 3 indexes.

**Scope:**
- Migration 020 (next available) — ALTER vehicles ADD mileage + service_history table + 3 indexes.
- `advanced/models.py` +30 LoC ServiceEvent Pydantic v2 with Literal event_type.
- `advanced/history_repo.py` (~220 LoC) 7 CRUD — `add_service_event` monotonically bumps vehicles.mileage.
- `cli/advanced.py` +250 LoC nested `history` subgroup (5 subcommands).
- `cli/main.py` +60 LoC — `garage update --bike --mileage/--notes/--vin` with monotonic guard.
- `vehicles/registry.py` +5 LoC — "mileage" added to update_vehicle.allowed.
- `advanced/predictor.py` +15 LoC — +0.05 bonus on mileage_source="db".
- `tests/test_phase152_history.py` ~35 tests (5 classes: TestMigration020×4, TestHistoryRepo×10, TestHistoryCLI×12, TestPhase148IntegrationBonus×5, TestRegression×4).

**Design non-negotiables:**
1. Flag wins over DB (user override).
2. Monotonic mileage (never decreases silently).
3. FK cascade: CASCADE vehicle_id, SET NULL mechanic_user_id.
4. CHECK-gated vocabulary (11 event types).
5. No seed data (empty day-1).
6. Phase 148 regression untouched — flag path identical scores.
7. Phase 151 integration by pull (Phase 152 exposes column).

**Dependencies:** Phase 148 hard (regression). Phase 149/150/151 unrelated. Migration slot next-integer. Phase 112 auth soft (mechanic username resolution).

**Open questions:** migration version literal vs next-integer, mechanic UX (username vs user_id), --yes vs separate reset command, event type extensibility, auto-log from diagnose (Phase 153), auto-log from hardware scan recall-check (deferred).

**Next:** Builder-152 agent-delegated. Architect trust-but-verify including Phase 148 full 44-test regression.

### 2026-04-19 11:55 — Build complete (Architect trust-but-verify)

Builder-152 delivered: `advanced/history_repo.py` (291 LoC), `cli/advanced.py` +~250 LoC history subgroup (add/list/show/show-all/by-type), migration 020 adds `service_history` table + `vehicles.mileage` column. `predictor.py` +0.05 bonus when `vehicle["mileage_source"]=="db"`. 35 tests delivered.

Architect pytest run: **35/35 GREEN** in 45s after bug fix #1 (below).

**Commit:** 68f65f4 "Track F Wave 1b + Gate 7"

### 2026-04-19 11:40 — Bug fix #1: Phase 148 integration test fixture saturation

**Issue:** 2 tests in `TestPhase148IntegrationBonus` failed with `assert 1.0 > 1.0`. The fixture used an exact-model stator issue whose base match_tier score (1.00) + age bonuses already saturated at the [0.0, 1.0] clamp ceiling, making the +0.05 DB bonus invisible.

**Root cause:** `_MATCH_TIER_SCORE["exact_model"]=1.00` + age-bonus +0.20 for a 2010 Sportster in 2026 = 1.20 pre-clamp → clamped to 1.0. Both `mileage_source="flag"` and `mileage_source="db"` saturated identically, so `stator_db > stator_flag` could never be true.

**Fix:** Rewrote `TestPhase148IntegrationBonus._seed_issue` to use family-make tier (`model=None`, no year_start/year_end, severity=low) producing base 0.50 + age +0.20 = 0.70 pre-bonus. +0.05 DB bonus now observable as a clean 0.05 delta under the clamp ceiling.

**Files:** `tests/test_phase152_history.py:727-749`.

**Verified:** 35/35 tests GREEN in 45s.
