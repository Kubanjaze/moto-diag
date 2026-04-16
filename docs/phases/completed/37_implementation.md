# MotoDiag Phase 37 — Yamaha YZF-R7 + YZF600R Thundercat

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Budget sport platforms: YZF600R Thundercat (1996-2007) — Yamaha's sport-touring 600 with a detuned engine and comfortable ergonomics; and YZF-R7 (2021+) — the modern CP2 twin-cylinder sport bike built on the MT-07 platform. Two very different bikes that share the "budget sport" positioning in Yamaha's lineup.

CLI: `python -m pytest tests/test_phase37_yamaha_r7_thundercat.py -v`

Outputs: `data/knowledge/known_issues_yamaha_r7_thundercat.json` (10 issues), 6 tests

## Key Concepts
- Thundercat is carbureted — 4-carb sync with vacuum gauges, EPA-capped mixture screws need removal
- Vacuum petcock failure is sneaky — floods cylinders, dilutes oil, can destroy engine bearings
- Thundercat shares FZR600 charging system — same MOSFET upgrade path as all 90s Yamaha sport bikes
- R7 CP2 twin has characteristic clutch chatter from 270-degree crank torque pulses — not a defect
- R7 suspension is the weak link — budget KYB components need upgrading for any track use
- R7 quick shifter (accessory) is less refined than R6/R1 integrated system
- R7 runs hotter than naked MT-07 due to full fairing blocking airflow
- R7 has emissions-driven lean spot at 3000-4500 RPM — ECU flash is the real fix

## Verification Checklist
- [x] 10 issues load correctly (5 Thundercat, 5 R7)
- [x] Year range queries return correct results (2023 query returns 4+ R7 hits)
- [x] Critical severity issues present (Thundercat charging)
- [x] Symptom searches work (loss of power: 2+, won't start: 1+)
- [x] Forum tips present in fix procedures
- [x] All 6 tests pass (1.14s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (Thundercat: carbs, petcock, charging, chain, forks; R7: clutch, suspension, QS, heat, lean spot) |
| Tests | 6/6, 1.14s |
| Severity breakdown | 1 critical, 2 high, 7 medium, 0 low |
| Year coverage | 1996-2026 |

Two distinct platforms well differentiated: the Thundercat is a carb-era parts bike with FZR600 DNA, while the R7 is a modern budget track platform with CP2 twin characteristics that owners mistake for defects.
