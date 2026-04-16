# MotoDiag Phase 49 — Kawasaki ZX-10R (2004+)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Kawasaki's flagship superbike: ZX-10R across 6 generations from raw 2004 debut to current electronics-laden model.

CLI: `python -m pytest tests/test_phase49_kawasaki_zx10r.py -v`

Outputs: `data/knowledge/known_issues_kawasaki_zx10r.json` (10 issues), 6 tests

## Key Concepts
- 2004-2005 headshake is a known design issue — aftermarket steering damper is mandatory safety equipment
- Charging system failure is more common on literbike due to higher heat and current demands
- 2016+ IMU-based electronics (KTRC, KIBS, KECS) need sensor cleaning and IMU recalibration after crashes
- CCT on a 200hp engine: use premium oil, check manual tensioner after every track day
- Fuel pump weakness shows as high-RPM lean stumble — dangerous at literbike speeds
- Valve check is a $600-800 shop job (16 valves, tight engine bay)
- KLEEN removal is universal first mod — same as ZX-6R
- Track crash damage: GB Racing case covers mandatory, bolt-on subframe makes repair easier
- Quick shifter + auto-blipper (2016+) tuning: shift rod length is the critical adjustment
- Cooling system operates near limits during track use — Engine Ice coolant is the standard

## Verification Checklist
- [x] 10 issues load correctly
- [x] Year range queries return correct results (2020 query returns 7+ hits)
- [x] Critical severity issues present (headshake, charging)
- [x] Symptom searches work (loss of power: 2+, won't start: 1+)
- [x] Forum tips present in fix procedures
- [x] All 6 tests pass (1.70s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (headshake, charging, IMU electronics, CCT, fuel pump, valves, KLEEN, crash damage, QS/blipper, cooling) |
| Tests | 6/6, 1.70s |
| Severity breakdown | 2 critical, 3 high, 5 medium, 0 low |
| Year coverage | 2004-2026 |

The ZX-10R is the most track-focused Kawasaki — diagnostic knowledge leans heavily toward track-use damage patterns, high-output thermal stress, and sophisticated electronics calibration.
