# MotoDiag Phase 111 — Knowledge Base Schema Expansion

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Extend the knowledge base schema to support new DTC categories (HV, battery, motor, regen, TPMS, emissions, charging port, thermal, inverter) required for electric motorcycles (Track L) and modern ICE bikes. Add OEM-specific DTC format classifiers for BMW (ISTA), Ducati (DDS), KTM (KDS), Triumph (TuneECU), Aprilia (Marelli), and electric bikes (HV_/MC_/BMS_/INV_/CHG_/REG_ prefixes). Use migration 004 to apply schema changes without breaking existing DTC data.

CLI: `python -m pytest tests/test_phase111_kb_schema_expansion.py -v`

Outputs: Migration 004 in `core/migrations.py`, `DTCCategory` enum in `core/models.py`, 6 OEM classifiers in `engine/fault_codes.py`, 3 new functions in `knowledge/dtc_repo.py`, 43 tests

## Logic
1. **Migration 004** (`core/migrations.py`):
   - `ALTER TABLE dtc_codes ADD COLUMN dtc_category TEXT DEFAULT 'unknown'`
   - Creates `dtc_category_meta` table with category taxonomy (name, description, applicable_powertrains JSON array, severity_default)
   - Populates 20 categories: 7 ICE (engine/fuel/ignition/emissions/transmission/cooling/exhaust), 7 chassis/safety (abs/airbag/immobilizer/body/network/tpms), 6 electric (hv_battery/motor/regen/charging_port/thermal/inverter), plus unknown

2. **`core/models.py`** — Added `DTCCategory` enum with 20 members. Extended `DTCCode` model with optional `dtc_category` field (default `DTCCategory.UNKNOWN`). Backward compat preserved: existing `category: SymptomCategory` unchanged.

3. **`knowledge/dtc_repo.py`** — Added 3 new functions:
   - `get_dtcs_by_category(dtc_category, make=None)` — query by new taxonomy, accepts enum or string
   - `get_category_meta(dtc_category)` — fetch category metadata (desc, applicable powertrains, severity default)
   - `list_all_categories()` — return all 20 categories with metadata, sorted
   - `add_dtc()` updated to persist `dtc_category` column

4. **`engine/fault_codes.py`** — Added 6 new code format classifiers:
   - BMW_ISTA: 5-char hex codes requiring `make="BMW"` context
   - DUCATI_DDS: `DTC-P0xxx` (powertrain) or `DTC-A0xxx` (auxiliary)
   - KTM_KDS: `KP-xxxx` (powertrain) or `KC-xxxx` (chassis)
   - TRIUMPH_TUNEECU: `T-xxx` 3-digit hex
   - APRILIA_DIAG: `DTC-xxxx` numeric, requires `make="Aprilia"` context
   - ELECTRIC_HV: `HV_`, `MC_`, `BMS_`, `INV_`, `CHG_`, `REG_` prefixed codes for electric bikes

## Key Concepts
- Two-axis taxonomy: `SymptomCategory` (what the mechanic observes) vs `DTCCategory` (what the DTC represents). Orthogonal — a motor controller fault (DTCCategory.MOTOR) causes symptoms across ELECTRICAL and ENGINE categories.
- Migration 004 additive-only: `ALTER TABLE ADD COLUMN` preserves existing rows; new column defaults to `'unknown'` for legacy DTCs
- OEM classifier ordering matters: Aprilia checked before Ducati because both use `DTC-` prefix but with different post-prefix patterns (numeric vs letter+digit)
- Make hint provides critical disambiguation: BMW 5-char hex only classifies correctly when `make="BMW"` passed; without hint it falls through to OBD-II checks
- Electric bike DTC prefixes (HV/MC/BMS/INV/CHG/REG) derived from Zero Motorcycles and Energica real-world diagnostic data
- Metadata-driven categories: `dtc_category_meta` table allows runtime querying of "which categories apply to electric bikes" without hardcoding
- Backward compat: all 1651 pre-phase-111 tests still pass

## Verification Checklist
- [x] Migration 004 adds `dtc_category` column and `dtc_category_meta` table (4 tests)
- [x] 20 categories populated with correct metadata including applicable_powertrains (4 tests)
- [x] DTCCategory enum has all ICE + electric + chassis categories (5 tests)
- [x] DTCCode model accepts optional dtc_category, defaults to UNKNOWN (3 tests)
- [x] dtc_repo.get_dtcs_by_category() filters correctly (5 tests)
- [x] dtc_repo.get_category_meta() returns metadata with applicable_powertrains (2 tests)
- [x] BMW_ISTA classifier (2 tests)
- [x] DUCATI_DDS powertrain + auxiliary (2 tests)
- [x] KTM_KDS powertrain + chassis (2 tests)
- [x] TRIUMPH_TUNEECU T-prefix (1 test)
- [x] APRILIA_DIAG with make context (1 test) — confirmed Aprilia wins over Ducati DTC- prefix
- [x] ELECTRIC_HV covers all 6 prefixes (6 tests)
- [x] Backward compat: OBD-II, Kawasaki, Suzuki, Honda, Harley, Unknown classifications unchanged (6 tests)
- [x] Rollback of migration 004 removes column and meta table (1 test)
- [x] All 1651 existing tests still pass (full regression)
- [x] All 43 new Phase 111 tests pass (1.31s)

## Deviations from Plan
- Initially placed Aprilia classifier AFTER Ducati, causing `DTC-4212` (Aprilia) to match Ducati regex. Fixed by tightening Ducati regex to require letter prefix (`DTC-[PA]...`) and placing Aprilia check first when `make="Aprilia"` hint present.
- Used SQLite `IF NOT EXISTS` for `dtc_category_meta` table creation and `INSERT OR IGNORE` for metadata seeding — makes migration 004 idempotent (safe to re-apply if partial failure).

## Risks
- Migration 004 writes to existing rows (defaults applied) — **Resolved:** SQLite's DEFAULT clause handles this automatically; no UPDATE required.
- OEM DTC formats poorly documented — **Accepted:** best-effort classification. Real codes from manufacturer service tools (BMW ISTA, Ducati DDS) will need refinement when Track K phases build out per-brand diagnostic specifics.
- Aprilia/Ducati DTC-prefix collision — **Discovered + fixed:** ordering + tighter Ducati regex resolves disambiguation.

## Results
| Metric | Value |
|--------|-------|
| Files modified | 4 (models.py, migrations.py, dtc_repo.py, fault_codes.py) |
| New Pydantic enum | DTCCategory (20 members) |
| New model fields | DTCCode.dtc_category (optional, default UNKNOWN) |
| New DTC format classifiers | 6 (BMW, Ducati, KTM, Triumph, Aprilia, Electric) |
| New repo functions | 3 (get_dtcs_by_category, get_category_meta, list_all_categories) |
| New DB tables | 1 (dtc_category_meta) |
| New DB columns | 1 (dtc_codes.dtc_category) |
| Migrations in registry | 2 (003 + 004) |
| Tests added | 43/43 passing in 1.31s |
| Full regression | 1694/1694 tests passing in 3m 14s (zero regressions) |
| Schema version | 3 → 4 |

Key finding: The classifier ordering discovery (Aprilia before Ducati) is exactly the kind of subtle issue the retrofit track is designed to catch BEFORE Track K's European brand phases start consuming these classifiers. The two-axis taxonomy (SymptomCategory + DTCCategory) turns out to be more powerful than expected — a single motor controller fault can simultaneously categorize as ELECTRICAL symptom (what rider notices), ENGINE behavior (loss of power), and MOTOR DTC (underlying cause). Future diagnostic prompts can query across axes for richer context.
