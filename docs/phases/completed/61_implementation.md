# MotoDiag Phase 61 — Suzuki SV650/1000 + Gladius (1999+)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Suzuki's iconic V-twin platform — SV650 (carb and FI), SV1000, and Gladius generations.

CLI: `python -m pytest tests/test_phase61_suzuki_sv650.py -v`

Outputs: `data/knowledge/known_issues_suzuki_sv650.json` (10 issues), 6 tests

## Key Concepts
- SV650 reg/rec failure: same Suzuki charging weakness, MOSFET upgrade + solder connector
- Carbureted SV650 (1999-2002): lean factory jetting, enrichment cable stretch, sync and shim needles
- V-twin CCT: two tensioners (front and rear), front cylinder more failure-prone, APE manual for both
- Clutch spring and basket: V-twin torque pulses accelerate basket notching, EBC heavy-duty springs
- Fuel pump failure (2003+ FI): relay is cheapest check, same platform as GSX-R family
- Budget suspension upgrades: fork springs + Race Tech emulators + used GSX-R rear shock
- SV1000 STPS surging: secondary throttle valve creates non-linear response, Power Commander
- Gladius (2009-2015): under-tail exhaust heat, mirror vibration, same V-twin engine underneath
- Fork seal maintenance: Seal Mate tool saves full replacement 50% of the time
- Exhaust mods require fueling: Power Commander (FI) or Dynojet kit (carb) + PAIR block-off

## Verification Checklist
- [x] All 6 tests pass (1.74s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Tests | 6/6, 1.74s |
| Severity breakdown | 0 critical, 3 high, 6 medium, 1 low |
| Year coverage | 1999-2026 |
