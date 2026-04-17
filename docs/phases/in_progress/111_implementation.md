# MotoDiag Phase 111 — Knowledge Base Schema Expansion

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Extend the knowledge base schema to support new DTC categories (HV, battery, motor, regen, TPMS, emissions) required for electric motorcycles and modern ICE bikes. Add OEM-specific DTC format classifiers for BMW, Ducati, KTM, Triumph, Aprilia (building on the existing Harley/Kawasaki/Suzuki/Honda classifiers from phase 81). Use migration 004 to apply schema changes without breaking existing DTC data.

CLI: `python -m pytest tests/test_phase111_kb_schema_expansion.py -v`

Outputs: Migration 004 in `core/migrations.py`, extended `knowledge/dtc_repo.py`, new DTC category enum in `core/models.py`, OEM DTC classifiers in `engine/fault_codes.py`, tests

## Logic
1. **Migration 004**: add `dtc_categories` column to `dtc_codes` table, create new `dtc_category_meta` table with category taxonomy (category name, applicable_powertrains, description, severity_default)
2. **`core/models.py`** — Add `DTCCategory` enum covering: ENGINE, FUEL, IGNITION, EMISSIONS, HV_BATTERY, MOTOR, REGEN, TPMS, ABS, AIRBAG, IMMOBILIZER, BODY, TRANSMISSION, NETWORK
3. **`knowledge/dtc_repo.py`** — Extended CRUD to filter by category; new `get_dtcs_by_category()` function
4. **`engine/fault_codes.py`** — Add classifiers for BMW (ISTA-style), Ducati (DDS format), KTM (KDS format), Triumph (TuneECU blink), Aprilia — all detect and route to appropriate namespace

## Key Concepts
- DTC categories support both ICE and electric bikes via single taxonomy
- HV_BATTERY category crucial for Zero/LiveWire/Energica diagnostics
- MOTOR category for electric motor controller faults (IGBT, phase loss, overcurrent)
- REGEN category for regenerative braking system faults
- OEM classifier pattern matches phase 81 approach — regex on code prefix
- Backward compat: existing DTC rows get auto-classified into legacy categories
- Migration is additive only — no existing rows modified or dropped

## Verification Checklist
- [ ] Migration 004 applies cleanly
- [ ] DTCCategory enum covers all required categories
- [ ] dtc_repo.get_dtcs_by_category() works
- [ ] BMW/Ducati/KTM/Triumph/Aprilia classifiers detect their respective DTC formats
- [ ] All 1651 existing tests still pass
- [ ] New tests cover the full expansion

## Risks
- Migration 004 writes to existing dtc_codes rows (auto-classify) — must be idempotent
- OEM DTC formats are proprietary and poorly documented — best-effort classification
