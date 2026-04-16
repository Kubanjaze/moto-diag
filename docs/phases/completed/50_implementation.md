# MotoDiag Phase 50 — Kawasaki ZX-12R / ZX-14R (2000-2020)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Kawasaki's hyperbikes: ZX-12R (2000-2005) and ZX-14R (2006-2020). Fastest production Kawasakis before the H2.

CLI: `python -m pytest tests/test_phase50_kawasaki_hyperbike.py -v`

Outputs: `data/knowledge/known_issues_kawasaki_hyperbike.json` (10 issues), 6 tests

## Key Concepts
- ZX-12R ram air system adds 5-10hp above 100mph — entire air path must be sealed
- Charging system failure: same pattern as all Kawasaki sport bikes, higher load from accessories
- 500+ lb weight accelerates brake, tire, and chain consumable wear by ~50% vs 600cc bikes
- ZX-14R ride-by-wire has lean spot at low RPM — ECU flash + KLEEN removal is the fix
- ZX-14R ABS/KTRC is simpler than ZX-10R (no IMU) but sensor cleaning still critical
- ZX-14R chain drive (NOT shaft drive) needs frequent lube due to 136+ lb-ft torque
- CCT on hyperbikes: torque stresses chain differently than high-RPM sport bikes
- ZX-14R sport-touring thermal cycling stresses cooling components
- ZX-12R suspension set for 170 lb rider — most owners need stiffer springs
- ZX-14R valve check commonly skipped on high-mileage tourers — engine masks tight valves with torque

## Verification Checklist
- [x] 10 issues load correctly
- [x] Year range queries return correct results (2015 query returns 6+ hits)
- [x] Critical severity issues present (ZX-12R charging)
- [x] Symptom searches work (loss of power: 2+, won't start: 1+)
- [x] Forum tips present in fix procedures
- [x] All 6 tests pass (1.63s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (ram air, charging, consumable wear, FI tuning, ABS/KTRC, chain drive, CCT, cooling, suspension, valves) |
| Tests | 6/6, 1.63s |
| Severity breakdown | 1 critical, 3 high, 6 medium, 0 low |
| Year coverage | 2000-2020 |

The hyperbike phase reveals a unique diagnostic category: bikes that stress every component harder through sheer mass and power output, creating wear patterns that surprise owners coming from lighter machines.
