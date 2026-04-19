# MotoDiag Phase 152 — Phase Log

**Status:** 🟡 Planned | **Started:** 2026-04-18 | **Completed:** —
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
