# MotoDiag Phase 48 — Kawasaki ZX-9R (1998-2003)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Kawasaki's open-class sport bike: ZX-9R spanning carbureted (1998-1999) and early FI (2000-2003).

CLI: `python -m pytest tests/test_phase48_kawasaki_zx9r.py -v`

Outputs: `data/knowledge/known_issues_kawasaki_zx9r.json` (10 issues), 6 tests

## Key Concepts
- Carbureted 1998-1999: same CV diaphragm/pilot jet/sync issues as ZX-7R
- Early FI 2000-2003: simple open-loop TPS-based injection — no self-correction, must maintain manually
- Charging system: identical weakness to all Kawasaki sport bikes — triple upgrade mandatory
- CCT at 20+ years: convert to manual APE tensioner proactively
- Cooling: thermostat and fan relay are $30 total that prevent $1000 in overheating damage
- Fuel pump (FI models): weak pump causes high-RPM stumble that mimics ignition problems
- Suspension and brakes: same age-related urgency as ZX-7R, but heavier bike makes it more critical
- Valve clearance: 900cc engine tightens more slowly than 600, but still needs checking at 20+ years
- Ignition switch and ground corrosion: the most common cause of intermittent electrical gremlins

## Verification Checklist
- [x] 10 issues load correctly
- [x] Year range queries return correct results (2001 query returns 7+ hits)
- [x] Critical severity issues present (charging, brakes)
- [x] Symptom searches work (loss of power: 2+, won't start: 1+)
- [x] Forum tips present in fix procedures
- [x] All 6 tests pass (1.79s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (carbs, early FI, charging, CCT, cooling, fuel pump, forks, brakes, valves, ignition switch) |
| Tests | 6/6, 1.79s |
| Severity breakdown | 2 critical, 3 high, 5 medium, 0 low |
| Year coverage | 1998-2003 |

The ZX-9R shares most of its diagnostic DNA with the ZX-7R (same era, same age-related failures) but the early FI models introduce Kawasaki's first-gen fuel injection — a transitional system that's simpler than modern FI but more complex than carbs.
