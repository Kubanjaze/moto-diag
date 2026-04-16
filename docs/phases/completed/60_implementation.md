# MotoDiag Phase 60 — Suzuki GSX-R1100 (1986-1998)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
The air/oil-cooled legend — Suzuki's 1127cc inline-4 that defined the open-class sport bike category.

CLI: `python -m pytest tests/test_phase60_suzuki_gsx_r1100.py -v`

Outputs: `data/knowledge/known_issues_suzuki_gsx_r1100.json` (10 issues), 6 tests

## Key Concepts
- Air/oil cooled (1986-1992) overheating in traffic: larger oil cooler is the #1 upgrade
- 4x Mikuni BST36/40 carb bank: full rebuild and sync is the most transformative maintenance
- Charging system: same GSX-R family weakness, proactive replacement at this age is mandatory
- CCT: guaranteed worn at 25-35 years, APE manual tensioner replacement
- Conventional fork / early USD: Race Tech emulators + aftermarket rear shock
- CDI ignition: pickup coil wiring degrades, intermittent misfires from cracked insulation
- Fuel petcock and tank rust: Pingel manual petcock, POR-15 tank sealer, inline filter
- Brake system: complete refresh needed — rebuild calipers, stainless lines, fresh fluid
- Wiring harness: 25-35 year old insulation cracks, clean grounds solve most electrical gremlins
- 530 chain: heavy-duty chain mandatory for 1127cc torque, always replace countershaft seal

## Verification Checklist
- [x] All 6 tests pass (1.77s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Tests | 6/6, 1.77s |
| Severity breakdown | 1 critical, 4 high, 5 medium |
| Year coverage | 1986-1998 |
