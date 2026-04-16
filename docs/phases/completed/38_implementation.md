# MotoDiag Phase 38 — Yamaha FZ/MT Naked Series

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Yamaha's naked/standard lineup: FZ6/FZ6R (2004-2017), FZ8 (2011-2013), FZ-09/MT-09 (2014+), FZ-10/MT-10 (2016+), MT-03 (2020+), MT-07/FZ-07 (2015+). These are Yamaha's highest-volume models — the MT-07 is the best-selling motorcycle in Europe. Covers CP2, CP3, and crossplane-4 engine platforms in naked configuration.

CLI: `python -m pytest tests/test_phase38_yamaha_fz_mt.py -v`

Outputs: `data/knowledge/known_issues_yamaha_fz_mt.json` (10 issues), 6 tests

## Key Concepts
- MT-09/FZ-09 snatchy throttle is the #1 owner complaint — B-mode or ECU flash is the fix
- MT-09 CP3 valve clearance tightens same as R6 — 4-5 hour service job
- MT-07 CP2 charging system is improved (factory MOSFET) but stator connector still the weak point
- FZ6/FZ6R detuned R6 engine overheats in traffic — naked chassis lacks R6's directed airflow
- MT-10 has R1 electronics exposed to weather — sensor contamination is the #1 diagnostic issue
- MT-03 is a beginner-drop bike — frame sliders are day-one purchase
- FZ8 short production run (2011-2013) — parts interchange with FZ1
- Exposed radiators on all naked models need guards to prevent stone damage
- MT-09 fuel pump issues can mimic the snatchy throttle problem — diagnose before tuning

## Verification Checklist
- [x] 10 issues load correctly
- [x] Year range queries return correct results (2020 query returns 5+ hits)
- [x] Critical severity issues present (radiator vulnerability)
- [x] Symptom searches work (loss of power: 2+, won't start: 1+)
- [x] Forum tips present in fix procedures
- [x] All 6 tests pass (1.28s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (MT-09 throttle/valves/fuel pump, MT-07 charging/chain, FZ6 overheating, MT-10 electronics, MT-03 drops, FZ8 idle, radiator guards) |
| Tests | 6/6, 1.28s |
| Severity breakdown | 1 critical, 2 high, 7 medium, 0 low |
| Year coverage | 2004-2026 |

The FZ/MT naked series shares a common theme: sport bike engines in exposed chassis. Every platform-specific issue traces back to this fundamental design choice — less weather protection, more heat exposure, more vulnerability to road debris.
