# MotoDiag Phase 93 — Torque Specs + Service Data Lookup

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Provide structured service reference data for common motorcycle maintenance: torque specifications, fluid capacities, service intervals, and valve clearances. Quick-lookup functions and AI context building for embedding service data into diagnostic prompts. All values are typical/generic — always verify against model-specific service manual.

CLI: `python -m pytest tests/test_phase93_service_data.py -v`

Outputs: `src/motodiag/engine/service_data.py` (20 torque specs + 14 intervals + 8 clearances + lookup functions), 39 tests

## Key Concepts
- TorqueSpec model: fastener, spec_nm, auto-calculated spec_ftlbs, thread_locker, notes
- ServiceInterval model: service_item, interval_miles, interval_km, interval_months, notes
- Clearance model: component, spec_mm_low, spec_mm_high, notes
- 20 common torque specs: drain plug, spark plug, axle nuts, caliper bolts, brake disc, sprocket, cam cover, handlebar, triple clamp, steering stem, banjo bolt, exhaust, footpeg, etc.
- 14 service intervals: oil change, filter, coolant, brake fluid, spark plugs, air filter, valves, chain, fork oil, tires, battery, shaft drive, steering bearings
- 8 valve clearance specs: inline-4 intake/exhaust, V-twin intake/exhaust, single intake/exhaust, Harley Twin Cam intake/exhaust
- Thread locker requirements documented (Loctite 243 blue on all caliper and sprocket bolts)
- Lookup functions: get_torque_spec(), get_service_interval(), get_valve_clearance() — all partial match + case insensitive
- build_service_data_context(): combines specs, intervals, and clearances into formatted text for AI prompts
- Safety-critical fastener notes: caliper bolts, brake disc bolts, axle nuts all flagged

## Verification Checklist
- [x] 20+ torque specs with Nm, auto-converted ft-lbs, thread locker, and notes (39 tests)
- [x] 14+ service intervals covering all major maintenance items
- [x] 8+ valve clearance specs across all engine types (inline-4, V-twin, single, Harley)
- [x] Lookup functions find data by partial name, case insensitive
- [x] Context builder produces formatted text for AI prompt injection
- [x] All 39 tests pass (0.25s)

## Results
| Metric | Value |
|--------|-------|
| Files created | 1 (service_data.py) |
| Tests | 39/39, 0.25s |
| Torque specs | 20 common fasteners |
| Service intervals | 14 standard items |
| Valve clearances | 8 engine-type specs |
| Data entries total | 42 |
