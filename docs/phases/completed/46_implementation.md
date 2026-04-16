# MotoDiag Phase 46 — Kawasaki ZX-6R (1995+)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Kawasaki's 600cc supersport: ZX-6R across all generations including the unique 636cc displacement.

CLI: `python -m pytest tests/test_phase46_kawasaki_zx6r.py -v`

Outputs: `data/knowledge/known_issues_kawasaki_zx6r.json` (10 issues), 6 tests

## Key Concepts
- 636cc vs 599cc displacement alternated by year — parts NOT interchangeable, affects racing eligibility
- Stator/charging failure follows same pattern as all Japanese sport bikes — MOSFET upgrade mandatory
- CCT failure from 15,500+ RPM operation — APE manual tensioner is standard preventive upgrade
- KLEEN system is Kawasaki's AIS equivalent — block-off plates eliminate decel popping
- Valve check is a 5-hour 16-valve job — exhaust valves tighten first
- Fuel pump fails from running tank low — keep above 1/4
- Cooling system requires working fan — test at every spring startup
- KTRC traction control (2009+) is basic wheel-speed comparison — clean sensors regularly
- Fork seals fail from aggressive riding — seal saver tool doubles seal life
- Quick shifter works best above 7000 RPM — check clutch cable before assuming QS fault

## Verification Checklist
- [x] 10 issues load correctly
- [x] Year range queries return correct results (2015 query returns 7+ hits)
- [x] Critical severity issues present (stator/charging)
- [x] Symptom searches work (loss of power: 2+, won't start: 1+)
- [x] Forum tips present in fix procedures
- [x] All 6 tests pass (1.66s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (636/599 confusion, stator, CCT, KLEEN, valves, fuel pump, cooling, KTRC, forks, QS/transmission) |
| Tests | 6/6, 1.66s |
| Severity breakdown | 1 critical, 3 high, 6 medium, 0 low |
| Year coverage | 1995-2026 |

The ZX-6R's defining diagnostic quirk is the 636/599 displacement confusion — a unique challenge in the 600cc supersport class that affects parts ordering, ECU tuning, and racing eligibility.
