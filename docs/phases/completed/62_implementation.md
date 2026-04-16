# MotoDiag Phase 62 — Suzuki V-Strom 650/1000/1050 (2002+)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Suzuki's adventure-touring platform — V-Strom 650, 1000, and the 2020+ 1050 with electronic throttle.

CLI: `python -m pytest tests/test_phase62_suzuki_vstrom.py -v`

Outputs: `data/knowledge/known_issues_suzuki_vstrom.json` (10 issues), 6 tests

## Key Concepts
- V-Strom 650 FI lean surge: Dobeck EJK + O2 eliminator + PAIR block-off is the standard fix
- V-Strom 1000 CCT noise: same SV1000 engine, APE manual tensioners for both banks
- Windscreen buffeting: CalSci or MadStad adjustable screen, or MRA clip-on deflector
- Suspension sag for adventure loading: match spring rates to total loaded weight
- V-Strom 1050 (2020+) electronic throttle: B mode for smooth city, TPS relearn after battery disconnect
- Charging system: same Suzuki weakness, adventure accessories push marginal system to limits
- Chain wear from loaded touring: Scottoiler is the most popular V-Strom accessory
- Valve clearance: V-twin only has 8 valves, front cylinder requires radiator removal
- Side stand switch corrosion: exposed to mud and water on adventure rides, carry a jumper wire
- ABS sensor maintenance: clean at every tire change, rear sensor prone to chain lube contamination

## Verification Checklist
- [x] All 6 tests pass (1.79s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Tests | 6/6, 1.79s |
| Severity breakdown | 0 critical, 2 high, 7 medium, 1 low |
| Year coverage | 2002-2026 |
