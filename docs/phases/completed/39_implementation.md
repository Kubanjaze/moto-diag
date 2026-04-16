# MotoDiag Phase 39 — Yamaha Cruisers: V-Star / Bolt

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Yamaha's cruiser lineup: V-Star 250 (2008-2021), V-Star 650 (1998-2019), V-Star 950 (2009-2017), V-Star 1100 (1999-2009), V-Star 1300 (2007-2017), and Bolt/R-Spec (2014+). Air-cooled V-twins spanning carbureted and EFI eras.

CLI: `python -m pytest tests/test_phase39_yamaha_cruisers.py -v`

Outputs: `data/knowledge/known_issues_yamaha_cruisers.json` (10 issues), 6 tests

## Key Concepts
- V-Star 650 carb maintenance is the #1 issue — pilot jet clogging from ethanol and storage
- Vacuum petcock failure puts fuel in oil — sneaky engine killer on V-Star 650/1100
- V-Star 1100 stator/charging failure same pattern as all Yamaha V-twins — MOSFET upgrade mandatory
- Shaft drive on V-Star 950/1300 requires gear oil changes that most owners skip entirely
- V-Star 250 valve adjustment is the easiest on any motorcycle — 15-minute job with basic tools
- Bolt runs hot in traffic like all air-cooled cruisers — full synthetic oil and oil cooler for commuters
- V-Star 650 starter clutch is an expensive repair ($500-800) at 30K-40K miles
- V-Star 1300 ISC valve carbon buildup causes idle surge — clean every 10K miles
- Bolt belt drive is low maintenance but belt failure is catastrophic — inspect regularly
- AIS removal is the universal V-Star mod — eliminates decel popping

## Verification Checklist
- [x] 10 issues load correctly
- [x] Year range queries return correct results (2015 query returns 5+ hits)
- [x] Critical severity issues present (petcock fuel-in-oil)
- [x] Symptom searches work (loss of power: 2+, won't start: 1+)
- [x] Forum tips present in fix procedures
- [x] All 6 tests pass (1.13s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (V-Star carbs, petcock, stator, shaft drive, V-Star 250 valves, Bolt heat, starter clutch, ISC surge, Bolt belt, AIS popping) |
| Tests | 6/6, 1.13s |
| Severity breakdown | 1 critical, 3 high, 6 medium, 0 low |
| Year coverage | 1998-2026 |

The cruiser lineup reveals a different owner demographic than sport bikes — seasonal riders who store bikes for months (carb/petcock issues), commuters who skip maintenance (shaft drive), and beginners who need simple maintenance guidance (V-Star 250 valves).
