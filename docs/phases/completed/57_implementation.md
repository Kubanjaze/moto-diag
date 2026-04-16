# MotoDiag Phase 57 — Suzuki GSX-R600 (1997+)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
The Gixxer 600 — Suzuki's flagship 600cc supersport across all generations from SRAD to current.

CLI: `python -m pytest tests/test_phase57_suzuki_gsx_r600.py -v`

Outputs: `data/knowledge/known_issues_suzuki_gsx_r600.json` (10 issues), 6 tests

## Key Concepts
- Stator/reg-rec failure: the #1 electrical issue — MOSFET upgrade and solder connector bypass
- CCT rattle: APE manual tensioner replaces worn automatic unit
- PAIR system: block-off plates eliminate decel popping with aftermarket exhaust
- Fuel pump and filter: high-RPM starvation from clogged filter, relay is cheapest check
- Fork seal maintenance: Seal Mate tool saves full replacement 50% of the time
- Valve clearance: exhaust valves tighten first, 15K street / 10K track check interval
- Coolant system: thermostat and fan switch failures, Engine Ice for track use
- S-DMS and TC (2011+): dirty wheel speed sensors cause most faults
- Brake caliper sticking: flush fluid every 2 years, Motul RBF 600 for track
- Clutch basket notching: Hinson billet basket is the permanent fix

## Verification Checklist
- [x] All 6 tests pass (1.65s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Tests | 6/6, 1.65s |
| Severity breakdown | 0 critical, 4 high, 5 medium, 1 low |
| Year coverage | 1997-2026 |
