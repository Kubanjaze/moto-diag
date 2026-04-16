# MotoDiag Phase 30 — Honda V4: VFR800, RC51/RVT1000R, VFR1200F

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build the known-issues knowledge base for Honda's V4 motorcycle lineup. Unique platform: gear-driven cams, VTEC, complex fuel injection, linked braking, shaft drive options.

CLI: `python -m pytest tests/test_phase30_honda_v4.py -v`

Outputs: `data/knowledge/known_issues_honda_v4.json` (10 issues), 6 tests

## Key Concepts
- VTEC crossover at ~6800 RPM is by design, not a defect — Ivan's ECU flash smooths it
- Gear-driven cam whine is NORMAL on all Honda V4s — educate owners, don't chase a phantom problem
- V4 configuration traps heat worse than inline-4 — reg/rec failure is accelerated
- VFR800 CBS/C-ABS linked braking has a specific bleed sequence — skip a step and you get air
- RC51 rear cylinder runs 20-30F hotter than front from heat plume in V-twin configuration
- VFR1200F shaft drive + DCT: same low-speed jerkiness as all Honda DCT models

## Verification Checklist
- [x] 10 issues load
- [x] Year range correct for 2010 (5+ issues)
- [x] Critical severity present (1: reg/rec)
- [x] Overheating and won't-start symptoms find relevant issues
- [x] Forum tips in all procedures
- [x] All 6 tests pass (0.92s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (VTEC crossover, reg/rec, RC51 TPS sync, gear-driven cam noise, CBS/C-ABS, RC51 overheating, VFR1200F shaft/DCT, fuel pump relay, exhaust collector, fairing buzz) |
| Tests | 6/6, 0.92s |
| Severity breakdown | 1 critical, 2 high, 4 medium, 3 low |
| Year coverage | 1998-2017 |

The V4 platform is the most mechanically unique Honda lineup — gear-driven cams, VTEC, linked braking, and V4 heat management create a diagnostic profile unlike any other Honda.
