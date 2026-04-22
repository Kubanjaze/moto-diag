# MotoDiag Phase 177 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-22 | **Completed:** 2026-04-22
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-22 — Plan written

Plan v1.0 authored in-session. Scope: first full-CRUD domain router
in Track H. `GET/POST/PATCH/DELETE /v1/vehicles*` exposes the Phase
04 vehicles table via HTTP with owner scoping + tier-gated quotas.

Key design decisions:
- **Retrofit owner_user_id** via migration 038 (Phase 112 pattern).
  Pre-retrofit rows default to system user id=1 — invisible via API
  until an operator explicitly re-owns them.
- **Owner scope at the repo layer**, not in middleware. New
  `_for_owner` helpers take owner_user_id as a required arg.
  Existing unscoped helpers stay working (CLI + background jobs).
- **Tier quota at POST time** (not schema CHECK). Count-then-insert
  races are acceptable for Phase 177; serializable transactions
  deferred.
- **404 for cross-user vehicles**, not 403. Prevents enumeration
  attacks.
- **No CLI changes.** `garage` CLI continues to operate globally;
  Phase 178+ may add session auth + current-user scoping.
- **Tier limits** hardcoded in the route module for Phase 177:
  individual=5, shop=50, company=unlimited. Aligns with Phase 109
  TIER_LIMITS but avoids the CLI→API coupling for now.

Outputs: migration 038 + ~80 LoC in vehicles/registry.py + ~230 LoC
in new api/routes/vehicles.py + 2 new exceptions mapped in
api/errors.py + ~28 tests. Zero AI.

### 2026-04-22 — Build complete

Files shipped (~547 LoC):

1. **Migration 038** (schema v37→v38): `ALTER TABLE vehicles ADD
   COLUMN owner_user_id INTEGER NOT NULL DEFAULT 1` + `idx_vehicles_
   owner`. Rollback uses rename-recreate to preserve the Phase
   04+110+152 shape of the vehicles table (id/make/model/year/
   engine_cc/vin/protocol/notes/powertrain/engine_type/battery_
   chemistry/motor_kw/bms_present/customer_id/mileage + indexes).

2. **`vehicles/registry.py`** +180 LoC: 2 new exceptions
   (`VehicleOwnershipError`, `VehicleQuotaExceededError`) + the
   `TIER_VEHICLE_LIMITS` map (5/50/-1 for individual/shop/company)
   + 7 new functions: `add_vehicle_for_owner`,
   `list_vehicles_for_owner`, `count_vehicles_for_owner`,
   `get_vehicle_for_owner`, `update_vehicle_for_owner`,
   `delete_vehicle_for_owner`, `check_vehicle_quota`.

3. **`api/routes/vehicles.py`** (301 LoC): 6 endpoints (list, create,
   get, patch, delete, vehicle-sessions) + 4 Pydantic request/
   response schemas. Every endpoint requires
   `Depends(get_current_user)`. POST enforces tier quota via
   `check_vehicle_quota` before calling `add_vehicle_for_owner`.
   404 returned for both "not found" and "cross-user" (enumeration
   prevention).

4. **`api/errors.py`** +6 LoC: 2 new exception mappings
   (VehicleOwnershipError 404, VehicleQuotaExceededError 402).

5. **`api/app.py`** +2 LoC: `vehicles_router` import + mount at
   `/v1` prefix.

6. **`tests/test_phase177_vehicle_api.py`** (33 tests, 5 classes):
   TestMigration038×4 + TestOwnerScopedRepo×8 + TestQuota×5 +
   TestVehicleEndpointsHappy×8 + TestVehicleEndpointsErrors×8.

**Single-pass: 33 GREEN in 26.07s.** No fixups needed.

**Targeted regression: 784/784 GREEN in 528.58s (8m 49s)** covering
Phase 04 (vehicles) + 113 + 118 + 131 + 153 + Track G 160-174 +
162.5 + 175 + 176 + 177. Zero regressions — the Phase 04 unscoped
helpers continue to work exactly as they did (CLI + background jobs
still see every vehicle globally).

Build deviations vs plan:
- 33 tests vs ~28 planned (+5 on tier-quota display in list response
  and cross-user PATCH boundary).
- No other deviations — the plan held exactly as written.

### 2026-04-22 — Documentation finalization

`implementation.md` promoted to v1.1. All `[x]` in Verification
Checklist. Deviations + Results sections populated.

Project-level updates:
- `implementation.md` schema_version footnote v37 → v38
- `implementation.md` Phase History: append Phase 177 row (first
  full-CRUD Track H domain router)
- `implementation.md` Endpoint inventory: add 6 vehicle endpoints
- `phase_log.md` project-level: Phase 177 closure
- `docs/ROADMAP.md`: Phase 177 row → ✅
- Project version 0.12.0 → **0.12.1** (first domain router, points
  bump)

**Key finding:** Phase 177 proves out the per-route velocity that
Phases 178-180 will inherit. The 301-LoC router is possible because
Phase 175 + 176 did the heavy structural work: auth is automatic,
exceptions auto-map to HTTP, Pydantic handles validation, and the
`_for_owner` repo convention makes scoping structurally enforced.
Domain routers from here on should each take <400 LoC + 25-35 tests
+ <1hr per phase. Track H's remaining phases (178 session / 179 KB /
180 shop / 181 WS / 182 reports / 183 OpenAPI / 184 Gate 9) are now
"fill in the table" work — the pattern is settled.
