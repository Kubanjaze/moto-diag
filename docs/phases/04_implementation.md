# MotoDiag Phase 04 — Vehicle Registry Data Model

**Version:** 1.1 | **Tier:** Micro | **Date:** 2026-04-15

## Goal
Build the vehicle registry with full CRUD operations so mechanics can manage their garage — add bikes, list/filter them, update details, and remove them. This is the first functional module that writes to the database.

CLI: No direct CLI yet (garage command still stub). Registry accessed via Python API.

Outputs: `vehicles/registry.py` with 6 functions, 14 tests

## Logic
1. Created `vehicles/registry.py` with 6 CRUD functions:
   - `add_vehicle(vehicle: VehicleBase)` → returns ID
   - `get_vehicle(vehicle_id: int)` → dict or None
   - `list_vehicles(make?, model?, year?)` → filtered list of dicts
   - `update_vehicle(vehicle_id, updates)` → bool (whitelisted fields only)
   - `delete_vehicle(vehicle_id)` → bool
   - `count_vehicles()` → int
2. All functions accept optional `db_path` parameter for testability
3. `list_vehicles` supports LIKE queries for make/model partial matching
4. `update_vehicle` whitelists allowed fields (make, model, year, engine_cc, vin, protocol, notes) — rejects unknown fields for safety
5. Timestamps: `created_at` on insert, `updated_at` on update

## Key Concepts
- Repository pattern: data access functions wrapping raw SQL
- Parameterized queries (no SQL injection risk)
- Field whitelisting on update to prevent arbitrary column writes
- `sqlite3.Row` dict-style access from Phase 03 connection manager
- Optional `db_path` parameter pattern for test isolation (each test gets its own tmp_path DB)

## Verification Checklist
- [x] `add_vehicle()` returns auto-increment ID
- [x] `get_vehicle()` returns dict with all fields
- [x] `get_vehicle()` returns None for missing ID
- [x] `list_vehicles()` returns all vehicles when no filter
- [x] `list_vehicles(make="Honda")` filters correctly
- [x] `list_vehicles(year=2001)` filters correctly
- [x] `list_vehicles()` returns empty list on empty DB
- [x] `update_vehicle()` modifies specified fields
- [x] `update_vehicle()` rejects non-whitelisted fields
- [x] `delete_vehicle()` removes vehicle
- [x] `delete_vehicle()` returns False for non-existent ID
- [x] `count_vehicles()` returns correct count
- [x] Multiple vehicles have unique IDs
- [x] 14 tests pass in 0.86s

## Risks
- ~~SQL injection via LIKE queries~~ — mitigated by parameterized queries with `?` placeholders
- No pagination on `list_vehicles()` — acceptable for mechanic-scale garages (dozens, not millions)

## Results
| Metric | Value |
|--------|-------|
| Functions | 6 (add, get, list, update, delete, count) |
| Test count | 14 |
| Test time | 0.86s |
| Whitelist fields | 7 (make, model, year, engine_cc, vin, protocol, notes) |

Vehicle registry is the first functional data module. Mechanics can now add their bikes to a persistent garage.
