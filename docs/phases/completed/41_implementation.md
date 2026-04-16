# MotoDiag Phase 41 — Yamaha Dual-Sport: WR250R/X, XT250, Tenere 700

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Yamaha's dual-sport and adventure lineup: WR250R/X (2008-2020), XT250 (2008-2023), and Tenere 700 (2021+). Different price points, different missions, all off-road capable.

CLI: `python -m pytest tests/test_phase41_yamaha_dualsport.py -v`

Outputs: `data/knowledge/known_issues_yamaha_dualsport.json` (10 issues), 6 tests

## Key Concepts
- WR250R stator can't keep up with EFI demand at low RPM — LED headlight swap and lithium battery are essential
- WR250R has premium suspension that needs maintenance — seal saver tool prevents most fork seal failures
- WR250R cold-start issues trace to weak battery from charging deficit
- XT250 is the simplest Yamaha — one carb, screw-type valves, 15-minute maintenance jobs
- XT250 chain wears fast from off-road contamination — clean after every trail ride
- Tenere 700 needs crash protection before first off-road ride — $500-900 investment
- Tenere 700 CP2 lean spot is worse off-road because trail riding lives in the 3000-4500 RPM zone
- Tenere 700 stock shock fails under luggage weight — aftermarket shock is the #1 upgrade
- Wind protection is the universal Tenere 700 complaint — aftermarket screen is mandatory for highway

## Verification Checklist
- [x] 10 issues load correctly (3 WR250R, 3 XT250, 4 Tenere 700)
- [x] Year range queries return correct results (2022 query returns 5+ hits)
- [x] Critical severity issues present (Tenere crash protection)
- [x] Symptom searches work (loss of power: 2+, won't start: 1+)
- [x] Forum tips present in fix procedures
- [x] All 6 tests pass (1.13s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (WR250R: stator/suspension/cold start; XT250: carb/chain/valves; Tenere: wind/crash/lean spot/shock) |
| Tests | 6/6, 1.13s |
| Severity breakdown | 1 critical, 3 high, 6 medium, 0 low |
| Year coverage | 2008-2026 |

The dual-sport lineup reveals off-road-specific diagnostic needs: crash damage prevention, suspension maintenance from harsh terrain, and charging systems stressed by low-RPM trail riding.
