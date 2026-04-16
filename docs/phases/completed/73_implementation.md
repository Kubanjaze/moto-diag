# MotoDiag Phase 73 — Starting System Diagnostics (Cross-Platform)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Universal starting system diagnostics — starter relay, motor, clutch/sprag, safety switches, battery cables, tip-over sensor, neutral switch, and compression release across all makes.

CLI: `python -m pytest tests/test_phase73_cross_platform_starting.py -v`

Outputs: `data/knowledge/known_issues_cross_platform_starting.json` (10 issues), 6 tests

## Key Concepts
- Starter relay: $15-25 part, most common single-part no-start cause, tap-test diagnostic
- Starter motor: brush wear, commutator cleaning, rebuild vs replace decision tree
- Starter clutch/sprag: one-way bearing failure on Honda/Kawasaki/Suzuki, labor-intensive repair
- Clutch safety switch: cheap plastic switch fails open, jumper test, many riders bypass
- Kickstand switch: corrodes from weather, especially on adventure and dual-sport bikes
- Kill switch: intermittent open from corroded contacts, contact cleaner fix
- Battery cable voltage drop: terminal corrosion, max 0.5V drop during cranking
- Tip-over sensor: modern bikes won't start after a drop, reset by cycling ignition
- Neutral switch: false neutral detection preventing start in neutral
- Compression release: high-compression singles/twins need strong battery or decomp lever

## Verification Checklist
- [x] All 6 tests pass
- [x] Multi-make coverage verified (Honda 3, Kawasaki 2, Suzuki 2, Yamaha 1, Harley 2)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Tests | 6/6 |
| Severity breakdown | 0 critical, 6 high, 4 medium |
| Year coverage | 1980-2026 |
| Makes covered | Honda, Yamaha, Kawasaki, Suzuki, Harley-Davidson |
