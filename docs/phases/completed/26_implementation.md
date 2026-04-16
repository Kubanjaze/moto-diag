# MotoDiag Phase 26 — Honda CBR1000RR / RR-R (2004+)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build the known-issues knowledge base for the Honda CBR1000RR (2004-2019) and CBR1000RR-R Fireblade SP (2020+). Honda's liter-class superbike.

CLI: `python -m pytest tests/test_phase26_honda_cbr1000rr.py -v`

Outputs: `data/knowledge/known_issues_honda_cbr1000rr.json` (10 issues), 6 tests

## Key Concepts
- Reg/rec failure even more critical on liter bike — higher stator output cooks regulator faster
- HESD failure at liter-bike speeds is safety-critical — steering damping is non-optional
- HSTC false intervention: crude on 2008-2016 (wheel speed only), better on 2017+ (IMU)
- Quickshifter calibration on SP/RR-R: shift rod adjustment is the hidden fix
- RR-R winglets: expensive, fragile, but only aerodynamically significant above 100 mph

## Verification Checklist
- [x] 10 issues load into database
- [x] Year range correct for 2015 (5+ issues)
- [x] Critical severity present (2: reg/rec, HESD)
- [x] Handling symptom finds HESD and rear linkage issues
- [x] Forum tips in all procedures
- [x] All 6 tests pass (0.89s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (reg/rec, HSTC, CCT, HESD, quickshifter, exhaust servo/PAIR, coolant, rear linkage, brakes, RR-R winglets) |
| Tests | 6/6, 0.89s |
| Severity breakdown | 2 critical, 3 high, 4 medium, 1 low |
| Year coverage | 2004-2025 |

Completes the Honda CBR sport bike trilogy (Phases 23-26). The liter bike adds higher stakes to every shared platform issue — reg/rec failure, HESD failure, and CCT failure all have worse consequences at higher speeds and power levels.
