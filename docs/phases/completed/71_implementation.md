# MotoDiag Phase 71 — Fuel Injection Troubleshooting (Cross-Platform)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Universal fuel injection diagnostics covering all EFI motorcycles across Honda, Yamaha, Kawasaki, Suzuki, and Harley-Davidson — sensor diagnostics, fuel delivery, ECU adaptation, and tuning.

CLI: `python -m pytest tests/test_phase71_cross_platform_fi.py -v`

Outputs: `data/knowledge/known_issues_cross_platform_fi.json` (10 issues), 6 tests

## Key Concepts
- Fuel pump failure and testing: listen for prime, check relay first ($15), test pressure at rail (43 PSI typical)
- TPS calibration and failure: closed-throttle voltage spec, ECU adaptation reset after adjustment
- IAP/MAP sensor: intake air pressure sensing, vacuum line integrity, altitude compensation
- O2 sensor: closed-loop hunting at cruise, eliminator resistor forces open-loop, affects emissions only
- ECT sensor: cold start enrichment, hard starting when failed, resistance-based temperature sensing
- Fuel injector clogging: ultrasonic cleaning vs replacement, balance test for multi-cylinder engines
- ISC/IACV valve carbon: blowby gases coat the valve, clean every 10-15K miles, the #1 idle complaint on EFI
- Throttle body cleaning and sync: vacuum gauge sync same concept as carb sync, TPS reset after service
- Fuel pressure regulator: maintains constant rail pressure, vacuum-referenced on most, diaphragm failure
- ECU reset and adaptation relearn: battery disconnect procedure, TPS relearn, idle relearn timing

## Verification Checklist
- [x] All 6 tests pass
- [x] Multi-make coverage verified (Honda, Kawasaki, Suzuki, Yamaha, Harley)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Tests | 6/6 |
| Severity breakdown | 1 critical, 4 high, 4 medium, 1 low |
| Year coverage | 1995-2026 |
| Makes covered | Honda, Yamaha, Kawasaki, Suzuki, Harley-Davidson |
