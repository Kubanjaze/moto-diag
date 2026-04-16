# MotoDiag Phase 53 — Kawasaki Vulcan Cruisers

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Kawasaki's cruiser lineup spanning Vulcan 500 through Vulcan 2000.

CLI: `python -m pytest tests/test_phase53_kawasaki_vulcan.py -v`

Outputs: `data/knowledge/known_issues_kawasaki_vulcan.json` (10 issues), 6 tests

## Key Concepts
- Vulcan 800/900 carb issues: pilot jet clogging from storage, single-carb (800) is easiest job
- Vulcan 900/1700 EFI idle surge: ISC valve carbon buildup, clean every 10K miles
- Vulcan 1500/1600 shaft drive: gear oil change every 10K miles, most owners never do it
- Vulcan 750 starter clutch: most expensive common repair, bump-start as backup
- Vulcan 2000: 2053cc requires hydraulic clutch conversion, shorter shaft drive oil interval
- Vulcan 900 belt drive: inspect regularly, failure is sudden and total
- Air-cooled V-twins all run hot in traffic: full-synthetic 20W-50, oil cooler for commuters
- Vulcan 1700 modern electronics: ISC + ABS + cruise control maintenance
- Vulcan 500 = Ninja 500 in cruiser chassis — parts interchange perfectly
- Exhaust mods require fuel adjustment: rejet (carb) or fuel controller (EFI)

## Verification Checklist
- [x] All 6 tests pass (1.77s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Tests | 6/6, 1.77s |
| Severity breakdown | 0 critical, 4 high, 6 medium |
| Year coverage | 1986-2026 |
