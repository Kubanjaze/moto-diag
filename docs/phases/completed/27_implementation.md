# MotoDiag Phase 27 — Honda Cruisers: Shadow 600/750/1100, VTX 1300/1800

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build the known-issues knowledge base for Honda's cruiser lineup. V-twin cruisers spanning carb and EFI eras, shaft and chain drive.

CLI: `python -m pytest tests/test_phase27_honda_cruisers.py -v`

Outputs: `data/knowledge/known_issues_honda_cruisers.json` (10 issues), 6 tests

## Key Concepts
- Reg/rec failure even worse on cruisers due to extended idle times and low-airflow mounting
- Shaft drive final gear oil is the most neglected service on Honda cruisers
- VTX 1800 starter clutch fails from high compression — Barnett HD replacement recommended
- VTX 1300 hydraulic lifter tick at cold start is "normal" per Honda
- Clutch drag / hard neutral = 90% clutch cable adjustment, not plate failure
- Crossover pipe rust is universal on shaft-drive cruisers in wet climates

## Verification Checklist
- [x] 10 issues load into database
- [x] Year range correct for 2005
- [x] Critical severity present (1: reg/rec)
- [x] Won't start finds fuel pump and starter clutch
- [x] Oil leak finds shaft drive issue
- [x] Forum tips in all procedures
- [x] All 6 tests pass (0.94s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (reg/rec, shaft drive leak, carb clogging, VTX starter clutch, fuel pump, lifter noise, clutch drag, exhaust crossover rust, seat height, speedo cable) |
| Tests | 6/6, 0.94s |
| Severity breakdown | 1 critical, 2 high, 4 medium, 3 low |
| Year coverage | 1988-2020 |

Honda cruisers are a different diagnostic world from sport bikes — shaft drive maintenance, hydraulic lifter behavior, and ergonomic issues are unique to this segment.
