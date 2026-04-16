# MotoDiag Phase 72 — Charging System Diagnostics (Cross-Platform)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Universal charging system diagnostics covering all motorcycles — stator testing, reg/rec diagnosis, MOSFET upgrade, battery selection, parasitic draw, ground circuits, and accessory load management across Honda, Yamaha, Kawasaki, Suzuki, and Harley-Davidson.

CLI: `python -m pytest tests/test_phase72_cross_platform_charging.py -v`

Outputs: `data/knowledge/known_issues_cross_platform_charging.json` (10 issues), 6 tests

## Key Concepts
- Stator winding failure: insulation breakdown from heat cycling — universal across all makes
- Reg/rec failure: shunt-type vs MOSFET comparison, MOSFET runs cooler and lasts longer
- Stator connector melting: fire risk on all makes, solder bypass is the permanent fix
- Rotor magnet degradation: loss of charging output on older bikes, re-magnetization vs replacement
- Battery selection: AGM for reliability, lithium for weight savings, conventional for budget
- Parasitic draw testing: systematic fuse-pull method, 1-5mA is normal, Battery Tender for storage
- Universal 3-step diagnostic: (1) voltage at RPM, (2) stator AC output, (3) reg/rec diode check
- Ground circuit resistance: voltage drop testing under load, 0.1V max across any ground path
- Accessory load management: calculate total draw vs charging output at idle
- Alternator belt (Harley) vs direct-drive charging differences across makes

## Verification Checklist
- [x] All 6 tests pass (0.71s)
- [x] Multi-make coverage verified (Honda 3, Kawasaki 3, Suzuki 3, Harley 1)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Tests | 6/6, 0.71s |
| Severity breakdown | 3 critical, 4 high, 3 medium |
| Year coverage | 1970-2026 |
| Makes covered | Honda, Kawasaki, Suzuki, Harley-Davidson |
