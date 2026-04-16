# MotoDiag Phase 45 — Kawasaki Ninja 250/300/400

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
First Kawasaki phase. The Ninja beginner bikes: Ninja 250R (1988-2012), Ninja 300 (2013-2017), and Ninja 400 (2018+). The best-selling beginner sport bikes in North America.

CLI: `python -m pytest tests/test_phase45_kawasaki_ninja_small.py -v`

Outputs: `data/knowledge/known_issues_kawasaki_ninja_small.json` (10 issues), 6 tests

## Key Concepts
- Ninja 250R carbs are the easiest to learn on — two carbs, one sync screw, tons of tutorials
- First-bike drop damage is inevitable — frame sliders are day-one purchase
- Small stator on 250R/300 struggles with accessories — LED headlight swap frees capacity
- Ninja 300/400 FI system uses Kawasaki dealer mode for DTC reading (jumper wire on diagnostic connector)
- Chain neglect is the #1 maintenance gap for new riders — lube every other fill-up
- Valve clearance checking at 15K miles — most first-time owners don't know it exists
- Ninja 400 ABS sensor cleaning solves most ABS warning lights
- Ninja 400 header cracking is a known TSB issue — sounds like valve tick
- Oil change neglect: 600-mile break-in service is the most important single maintenance event
- Motorcycle-specific oil only — car oil causes wet clutch slip

## Verification Checklist
- [x] 10 issues load correctly
- [x] Year range queries return correct results (2020 query returns 4+ Kawasaki hits)
- [x] Critical severity issues present (oil neglect)
- [x] Symptom searches work (loss of power: 1+, won't start: 1+)
- [x] Forum tips present in fix procedures
- [x] All 6 tests pass (1.39s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (carbs, drops, charging, fuel pump, chain, valves, ABS, coolant, header crack, oil neglect) |
| Tests | 6/6, 1.39s |
| Severity breakdown | 1 critical, 3 high, 6 medium, 0 low |
| Year coverage | 1988-2026 |

The beginner Ninja phase is unique — issues are as much about new-rider education as they are about mechanical failures. Oil change neglect, chain maintenance, and drop preparedness are diagnostic knowledge that serves the largest segment of first-time motorcycle owners.
