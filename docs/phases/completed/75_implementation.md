# MotoDiag Phase 75 — Cooling System Diagnostics (Cross-Platform)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Universal cooling system diagnostics — thermostat, fan switch, coolant degradation, water pump, radiator, air-cooled heat management, hoses, head gasket, radiator cap, and track coolant requirements across all makes.

CLI: `python -m pytest tests/test_phase75_cross_platform_cooling.py -v`

Outputs: `data/knowledge/known_issues_cross_platform_cooling.json` (10 issues), 6 tests

## Key Concepts
- Thermostat failure: stuck closed = overheating, stuck open = slow warmup, $15 part 30-minute job
- Radiator fan switch/relay: jumper test confirms fan motor health, switch is the common failure
- Coolant degradation: becomes acidic after 2 years, corrodes internals, 2-year flush cycle mandatory
- Water pump seal: weep hole diagnosis, seal kit vs pump replacement decision
- Radiator core blockage: external debris (bugs/mud) and internal corrosion, compressed air from inside out
- Air-cooled heat management: full-synthetic oil, oil cooler for commuters, riding technique in traffic
- Coolant hose failure: rubber hardens after 10+ years, Samco/silicone upgrades last indefinitely
- Head gasket failure: coolant in oil (milky appearance), Lisle block tester confirms, expensive repair
- Radiator cap: pressure rating matters, weak cap lowers boiling point, $10 preventive replacement
- Track coolant: Engine Ice, Water Wetter, org regulations on glycol vs non-glycol

## Verification Checklist
- [x] All 6 tests pass
- [x] Multi-make coverage verified (Honda 2, Kawasaki 3, Suzuki 2, Yamaha 2, Harley 1)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Tests | 6/6 |
| Severity breakdown | 2 critical, 4 high, 4 medium |
| Year coverage | 1970-2026 |
| Makes covered | Honda, Yamaha, Kawasaki, Suzuki, Harley-Davidson |
