# MotoDiag Phase 65 — Suzuki Cruisers: Intruder/Boulevard Series

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Suzuki's cruiser lineup — Intruder 800/1500, Boulevard S50/C50/M50/C90/M109R across all eras.

CLI: `python -m pytest tests/test_phase65_suzuki_cruisers.py -v`

Outputs: `data/knowledge/known_issues_suzuki_cruisers.json` (10 issues), 6 tests

## Key Concepts
- Intruder/Boulevard 800 carb issues: pilot jet clogging, enrichment cable stretch, drain for storage
- Boulevard C50/M50 FI lean surge: Dobeck EJK + O2 eliminator + PAIR block-off
- Boulevard C90/M109R shaft drive: 6K mile oil change interval, M109R torque demands it
- M109R clutch drag: Barnett heavy-duty kit, hydraulic clutch conversion for better modulation
- Intruder/Boulevard 1500 starter clutch failure: sprag wear, labor-intensive repair
- Charging system: MOSFET upgrade critical for cruisers with chrome, lights, and audio accessories
- Air-cooled V-twin heat: full-synthetic 20W-50, oil cooler for commuters
- M109R fuel pump and relay: high-flow pump for 1783cc, same relay failure as all Suzuki
- Exhaust modifications: carb rejetting or EFI fuel controller + PAIR removal
- Brake system: rear drum adjustment, front caliper corrosion from infrequent use

## Verification Checklist
- [x] All 6 tests pass (1.65s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Tests | 6/6, 1.65s |
| Severity breakdown | 0 critical, 5 high, 5 medium |
| Year coverage | 1992-2026 |
