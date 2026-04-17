# MotoDiag Phase 110 — Vehicle Registry + Protocol Taxonomy Expansion

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
First phase of the Retrofit track. Built a **reusable schema migration system** (the foundation for 11 subsequent retrofit phases) and extended the vehicle registry to support electric powertrains, expanded engine taxonomy (4-stroke/2-stroke/electric/hybrid/desmo), European OBD protocols (BMW K-CAN, Ducati/KTM CAN), and battery chemistry. Migration 003 brings the DB schema from baseline (v2) to target (v3) while preserving all existing data.

CLI: `python -m pytest tests/test_phase110_vehicle_expansion.py -v`

Outputs: `src/motodiag/core/migrations.py` (migration framework), updated `core/models.py` (new enums), updated `core/database.py` (integrated migrations into init_db), updated `vehicles/registry.py` (new CRUD fields), 35 tests

## Logic
1. **`core/migrations.py`** — Reusable migration framework:
   - `Migration` Pydantic model: version, name, description, upgrade_sql, rollback_sql
   - `MIGRATIONS` list — ordered registry that retrofit/expansion phases append to
   - `apply_pending_migrations()`: applies any Migrations with version > current, transactionally
   - `rollback_migration()` / `rollback_to_version()`: reverse migrations (testing + emergency recovery)
   - `get_current_version()`, `get_applied_migrations()`, `get_pending_migrations()`, `get_migration_by_version()` helpers
   - Migration 003 included: adds powertrain, engine_type, battery_chemistry, motor_kw, bms_present to vehicles table

2. **`core/models.py` expansion** — New enums:
   - `PowertrainType`: ICE, ELECTRIC, HYBRID (3 members)
   - `EngineType`: FOUR_STROKE, TWO_STROKE, ELECTRIC_MOTOR, HYBRID, DESMODROMIC (5 members)
   - `BatteryChemistry`: LI_ION, LFP, NMC, NCA, LEAD_ACID (5 members)
   - `ProtocolType` expanded: added BMW_K_CAN, DUCATI_CAN, KTM_CAN alongside existing CAN, K_LINE, J1850, PROPRIETARY, NONE (8 total)
   - `VehicleBase` extended: added optional powertrain/engine_type/battery_chemistry/motor_kw/bms_present fields with sensible ICE/4-stroke defaults

3. **`core/database.py` integration**:
   - `SCHEMA_VERSION = 3` (target version), `BASELINE_SCHEMA_VERSION = 2` (what SCHEMA_SQL alone produces)
   - `init_db()` now inserts baseline version then runs `apply_pending_migrations()` to bring to target
   - New `apply_migrations=False` flag enables testing migration behavior explicitly

4. **`vehicles/registry.py` updates**:
   - `add_vehicle()` persists new columns from VehicleBase model
   - `list_vehicles()` + `count_vehicles()` gain optional `powertrain` filter parameter
   - `update_vehicle()` handles enum-to-string conversion for new fields
   - **Backward compatibility preserved**: `db_path` remains first positional arg in all functions

## Key Concepts
- Migration framework is load-bearing for 11 more retrofit phases — designed for longevity
- SQLite ALTER TABLE ADD COLUMN with DEFAULT preserves existing rows' values
- Rollback uses CREATE-COPY-DROP-RENAME pattern for SQLite pre-3.35 compatibility
- Two-tier versioning: BASELINE_SCHEMA_VERSION (SCHEMA_SQL state) + SCHEMA_VERSION (target after migrations)
- Enum expansion: new values added to ProtocolType without breaking existing string-value round-trips
- Backward compat proof: all 1616 pre-retrofit tests still pass
- Pydantic v2 auto-validates: existing code that creates VehicleBase without new fields gets ICE/4-stroke defaults
- CRUD signature discipline: `db_path` must remain first positional arg — downstream phases will follow this rule

## Verification Checklist
- [x] Migration framework applies forward migrations in order (3 tests)
- [x] Migration framework rolls back migrations correctly (2 tests)
- [x] Migration 003 adds all new columns to fresh and existing DBs (4 tests)
- [x] PowertrainType / EngineType / BatteryChemistry enums have correct members (6 tests)
- [x] ProtocolType expansion keeps original values + adds European variants (3 tests)
- [x] VehicleBase accepts new optional fields, defaults preserve ICE/4-stroke behavior (4 tests)
- [x] Registry CRUD persists and queries new columns (6 tests)
- [x] Existing calls like `count_vehicles(db_path)` still work (1 regression test)
- [x] European protocol round-trips: Ducati DUCATI_CAN, BMW BMW_K_CAN, KTM KTM_CAN (3 tests)
- [x] All 1616 existing tests still pass (verified via full regression)
- [x] All 35 new Phase 110 tests pass (1.39s)

## Risks
- Migration framework is load-bearing for 11 more phases — any bug blocks entire retrofit. **Mitigated:** comprehensive test coverage including rollback paths.
- SQLite ALTER TABLE has limitations — need to verify ADD COLUMN patterns work. **Resolved:** migration 003 uses only ADD COLUMN with DEFAULT, which SQLite supports universally.
- Enum expansion could break existing code. **Resolved:** all pre-retrofit tests pass; round-trip tests confirm backward compatibility.
- Default values must preserve semantic meaning. **Resolved:** defaults chosen as ICE/FOUR_STROKE — matches every motorcycle in the pre-retrofit knowledge base.
- CRUD signature change breaking callers. **Discovered + fixed:** initial design put `powertrain` before `db_path` in `count_vehicles()` signature, broke `test_count`. Fixed by keeping `db_path` as first positional arg.

## Deviations from Plan
- Plan specified simple approach; actual build added `BASELINE_SCHEMA_VERSION` constant to cleanly separate baseline state from target state. This was necessary because `get_schema_version == SCHEMA_VERSION` is asserted by existing tests.
- Added `apply_migrations=False` flag to `init_db()` to enable testing migration behavior in isolation. Not in original plan but needed for unit tests.
- `count_vehicles()` signature kept `db_path` as first positional arg (not `powertrain` as originally designed) — preserves backward compatibility with existing `test_count`.

## Results
| Metric | Value |
|--------|-------|
| Files created | 1 (migrations.py) |
| Files modified | 3 (models.py, database.py, registry.py) |
| New Pydantic enums | 3 (PowertrainType, EngineType, BatteryChemistry) |
| ProtocolType members | 5 → 8 (+3 European variants) |
| VehicleBase new fields | 5 (powertrain, engine_type, battery_chemistry, motor_kw, bms_present) |
| Migrations in registry | 1 (migration 003) |
| Tests added | 35/35 passing in 1.39s |
| Full regression | 1651/1651 tests passing in 2m 48s (zero regressions) |
| Schema version | Baseline 2 → Target 3 |

Key finding: The migration framework design paid off immediately — it caught two subtle backward-compatibility issues (SCHEMA_VERSION assertion and count_vehicles signature) that would have been harder to find mid-refactor. The two-tier version approach (baseline + target) is a cleaner pattern than single-constant schema versioning and will scale through all 11 remaining retrofit phases.
