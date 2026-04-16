# MotoDiag Phase 64 — Suzuki GSX-S750/1000 + Katana (2015+)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Suzuki's modern naked sport bikes — GSX-S750, GSX-S1000, and the 2019+ Katana revival, all using detuned GSX-R engines.

CLI: `python -m pytest tests/test_phase64_suzuki_gsx_s.py -v`

Outputs: `data/knowledge/known_issues_suzuki_gsx_s.json` (10 issues), 6 tests

## Key Concepts
- GSX-S throttle-by-wire jerkiness: B mode for city, Power Commander for permanent fix
- GSX-S1000 CCT from GSX-R1000 K5 engine: same APE manual tensioner, same procedure
- Katana heat management: retro fairing restricts airflow vs naked GSX-S, Engine Ice coolant
- Charging system: inherited from GSX-R, MOSFET reg/rec upgrade mandatory
- Fuel pump relay: same $15 failure point across entire Suzuki sport bike range
- GSX-S750 chain maintenance: commuter use accelerates countershaft sprocket wear
- Katana mirror vibration: CRG Arrow mirrors or bar-end weights fix resonance
- Valve clearance: same specs as GSX-R donor engine, commuting heat cycles may shorten interval
- ABS and TC sensor maintenance: dirty wheel speed sensors cause most electronic faults
- Fork seal and oil service: same GSX-R forks, Seal Mate tool, 15K mile oil change

## Verification Checklist
- [x] All 6 tests pass (1.68s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Tests | 6/6, 1.68s |
| Severity breakdown | 0 critical, 3 high, 5 medium, 2 low |
| Year coverage | 2015-2026 |
