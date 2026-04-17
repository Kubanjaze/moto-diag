# MotoDiag Phase 110 — Vehicle Registry + Protocol Taxonomy Expansion

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
First phase of the Retrofit track. Extend the vehicle registry to support electric powertrains, expanded engine taxonomy (4-stroke/2-stroke/electric/hybrid/desmo), and European OBD protocols (BMW K-CAN, Ducati/KTM CAN). Introduces a **reusable schema migration system** that all subsequent retrofit phases (111-120) will build on. Migrations must be forward-only with rollback support and preserve all existing data.

CLI: `python -m pytest tests/test_phase110_vehicle_expansion.py -v`

Outputs: `src/motodiag/core/migrations.py` (migration framework), updated `core/models.py` (new enums), updated `core/database.py` (new columns), updated `vehicles/registry.py`, tests

## Logic
1. **`core/migrations.py`** — Migration framework (the reusable infrastructure):
   - `Migration` Pydantic model: version, name, upgrade_sql, rollback_sql, description
   - `MIGRATIONS` list — ordered list of all migrations; retrofit phases append entries here
   - `apply_pending_migrations()`: read current schema_version, apply any Migrations with higher version
   - `rollback_to_version()`: for testing; reverts one or more migrations
   - `get_applied_migrations()`: list which migrations have been applied
   - Transactional: wraps each migration in a single transaction, rolls back on failure

2. **`core/models.py` updates** — New enums:
   - `PowertrainType` enum: ICE, ELECTRIC, HYBRID
   - `EngineType` enum: FOUR_STROKE, TWO_STROKE, ELECTRIC_MOTOR, HYBRID, DESMODROMIC
   - `ProtocolType` expansion: add BMW_K_CAN, DUCATI_CAN, KTM_CAN alongside existing CAN/K_LINE/J1850
   - `BatteryChemistry` enum (for electric): LI_ION, LFP, NMC, NCA
   - Extend `VehicleBase`: add optional powertrain/engine_type/battery_chemistry/motor_kw fields

3. **`vehicles/registry.py` updates** — Extended CRUD to support new fields; backfill existing rows with defaults (ICE / FOUR_STROKE)

4. **Migration 003** (the first retrofit migration): adds columns to `vehicles` table — `powertrain`, `engine_type`, `battery_chemistry`, `motor_kw`, `bms_present`, defaults preserve existing data

## Key Concepts
- Migration framework is the keystone — all retrofit phases depend on it
- Backward compatibility: all existing vehicle rows get sensible defaults (ICE powertrain, 4-stroke engine) via migration
- Pydantic enum extension: ProtocolType gains values but existing string values still parse
- Forward migration + rollback: every migration is reversible (tested in unit tests)
- Transaction safety: migration failure rolls back partial changes, schema_version not bumped
- Testing: migration can run on a fresh DB, existing DB, or partially-migrated DB
- No breaking CLI changes — all existing `motodiag` invocations unaffected

## Verification Checklist
- [ ] Migration framework applies forward migrations in order
- [ ] Migration framework rolls back one-at-a-time correctly
- [ ] Apply migration 003 to existing DB: all vehicle rows gain default values
- [ ] New PowertrainType / EngineType / BatteryChemistry enums work
- [ ] Expanded ProtocolType still accepts existing values (CAN, K_LINE, J1850)
- [ ] VehicleBase accepts new optional fields, defaults preserve old behavior
- [ ] `vehicles/registry.py` CRUD handles new fields
- [ ] All 1616 existing tests still pass
- [ ] New tests pass (migration framework + expanded models + registry CRUD)
- [ ] No existing CLI command broken

## Risks
- Migration framework is load-bearing for 11 more phases — any bug blocks entire retrofit
- SQLite ALTER TABLE has limitations — need to verify ADD COLUMN patterns work
- Enum expansion could break existing code reading ProtocolType via `in` checks — audit needed
- Default values must preserve semantic meaning for existing data
