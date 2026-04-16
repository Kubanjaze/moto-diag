# MotoDiag Phase 59 — Suzuki GSX-R1000 (2001+)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Suzuki's liter-class superbike — the GSX-R1000 across all generations from K1 to current.

CLI: `python -m pytest tests/test_phase59_suzuki_gsx_r1000.py -v`

Outputs: `data/knowledge/known_issues_suzuki_gsx_r1000.json` (10 issues), 6 tests

## Key Concepts
- K5-K8 engine case cracking at oil drain boss: torque to 20 Nm, new crush washer every change
- Stator/charging: same family weakness, worst on 1000 due to highest output demand
- S-DMS / Motion Track TCS / IMU (2012+): sensor cleaning and IMU recalibration after battery disconnect
- CCT failure: same manual tensioner fix, 2017+ improved CCT design significantly
- SET exhaust servo: can remove with eliminator kit or fix servo motor
- Fuel pump relay: $15 part, carry a spare, welded-closed relay is a fire risk
- Valve clearance: 15K street / 7.5K track, exhaust valves tighten first
- Quickshifter (2017+): shift rod preload adjustment critical for proper function
- Cooling for track use: Engine Ice, thermostat removal, clean radiator core
- Rear wheel bearing: 20-25K street, 10-15K track, check cush drive rubbers too

## Verification Checklist
- [x] All 6 tests pass (1.74s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Tests | 6/6, 1.74s |
| Severity breakdown | 1 critical, 3 high, 5 medium, 1 low |
| Year coverage | 2001-2026 |
