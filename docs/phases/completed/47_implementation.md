# MotoDiag Phase 47 — Kawasaki ZX-7R / ZX-7RR (1996-2003)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Kawasaki's carb-era 750cc supersport: ZX-7R (street) and ZX-7RR (homologation special). Last generation of carbureted Kawasaki superbikes, now 20-30 years old.

CLI: `python -m pytest tests/test_phase47_kawasaki_zx7r.py -v`

Outputs: `data/knowledge/known_issues_kawasaki_zx7r.json` (10 issues), 6 tests

## Key Concepts
- ZX-7R CV carbs: diaphragm pinholes are the #1 age-related failure after 20 years
- ZX-7RR FCR flat-slide carbs need expert tuning — accelerator pump diaphragm failure common
- Entire fuel system (petcock, lines, filter, tank) needs replacement as a set on 20+ year old bikes
- Charging system: same stator connector/shunt regulator failure as all 90s Japanese sport bikes
- CCT on a 20-30 year old 750: likely at end of auto-tensioner range — convert to manual
- Wiring harness insulation becomes brittle — connector cleaning fixes 80% of mystery electrical faults
- ALL rubber components (hoses, boots, seals, gaskets) past service life — budget for complete refresh
- Suspension hasn't been serviced on most examples — fork oil change transforms handling
- Brakes are a safety priority — fluid flush, caliper rebuild, braided lines mandatory
- Ignition: plug wires and caps cause misfires that mimic carb problems

## Verification Checklist
- [x] 10 issues load correctly
- [x] Year range queries return correct results (2000 query returns 8+ hits)
- [x] Critical severity issues present (fuel system, brakes)
- [x] Symptom searches work (loss of power: 2+, won't start: 1+)
- [x] Forum tips present in fix procedures
- [x] All 6 tests pass (1.65s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (carbs, fuel system, charging, FCR carbs, CCT, wiring, rubber, suspension, brakes, ignition) |
| Tests | 6/6, 1.65s |
| Severity breakdown | 2 critical, 4 high, 4 medium, 0 low |
| Year coverage | 1996-2003 |

The ZX-7R phase is a masterclass in age-related motorcycle failures — every issue traces back to 20-30 years of component degradation. This knowledge applies to any vintage Japanese sport bike in the shop.
