# MotoDiag Phase 67 — Suzuki Vintage: GS550/750/850/1000/1100, Katana 1100

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Suzuki's air-cooled inline-4 classics from the late 1970s through mid-1980s — the GS series and the iconic GSX1100S Katana.

CLI: `python -m pytest tests/test_phase67_suzuki_vintage.py -v`

Outputs: `data/knowledge/known_issues_suzuki_vintage.json` (10 issues), 6 tests

## Key Concepts
- GS1000/1100 CCT: automatic tensioner worn after 40+ years, APE manual replacement
- GS550/750/850 charging: MOSFET reg/rec upgrade is the #1 electrical fix, solder stator wires
- GS/Katana carb bank: 4x Mikuni CV carbs, Keyster rebuild kits, vacuum sync is transformative
- GS ignition: Dyna S conversion for points models, pickup coil wiring for electronic models
- GSX1100 Katana fuel system: iconic tank rusts internally, Pingel manual petcock, POR-15 sealer
- GS/Katana suspension: Race Tech emulators + Hagon/Works Performance rear shocks
- GS/Katana brakes: complete refresh needed at 40+ years, stainless lines are the #1 upgrade
- Oil leaks: cam cover gasket first, Hylomar on rough casting surfaces, torque to spec
- Wiring harness: 40-year-old insulation cracks, clean every ground and connector, blade fuse upgrade
- Drive chain: O-ring/X-ring upgrade from non-sealed, 520 conversion for weight savings

## Verification Checklist
- [x] All 6 tests pass (0.68s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Tests | 6/6, 0.68s |
| Severity breakdown | 1 critical, 4 high, 5 medium |
| Year coverage | 1977-1984 |
