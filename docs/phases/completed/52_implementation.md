# MotoDiag Phase 52 — Kawasaki Z Naked Series

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Kawasaki's naked/standard lineup: Z400 through Z H2. Shared engines with Ninja line, naked chassis exposure considerations.

CLI: `python -m pytest tests/test_phase52_kawasaki_z_naked.py -v`

Outputs: `data/knowledge/known_issues_kawasaki_z_naked.json` (10 issues), 6 tests

## Key Concepts
- Exposed radiators on all Z models — guards mandatory, stone damage is the #1 naked bike risk
- Z1000 throttle response is aggressive (no power modes) — ECU flash is the only fix
- Z650/Z400 inherit Ninja platform issues plus weather exposure on connectors
- Z750/Z800 charging system: same shunt reg weakness, naked chassis runs hotter
- Z H2 supercharged engine in naked chassis = extreme thermal stress, no fairing airflow
- Commuter Z bikes eat chains faster from stop-start and rain riding
- Z900 KTRC sensors more exposed than Ninja equivalents — clean after wet rides
- Z1000 CCT: spirited naked riding = frequent high RPM = faster wear
- Z400/Z650 beginner patterns: drops, chain neglect, oil ignorance
- Headlight upgrades common — stock beam often inadequate for highway night riding

## Verification Checklist
- [x] 10 issues load correctly
- [x] Year range queries return correct results (2022 returns 6+ hits)
- [x] Critical severity present (radiator vulnerability)
- [x] Symptom searches work (loss of power: 2+, won't start: 1+)
- [x] Forum tips present
- [x] All 6 tests pass (1.63s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (radiator, Z1000 throttle, Z650/Z400 connectors, charging, Z H2 heat, chain, KTRC, CCT, beginner, headlights) |
| Tests | 6/6, 1.63s |
| Severity breakdown | 1 critical, 3 high, 6 medium, 0 low |
| Year coverage | 2003-2026 |

The Z naked series phase mirrors Yamaha's FZ/MT phase — sport bike engines in exposed chassis create a consistent set of diagnostic patterns: more weather exposure, more thermal stress, more vulnerability to road debris.
