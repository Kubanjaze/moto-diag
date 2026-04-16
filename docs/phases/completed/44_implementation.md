# MotoDiag Phase 44 — Yamaha Common Cross-Model Issues

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Final Yamaha phase. Cross-model issues that appear across the entire Yamaha lineup. Completes Yamaha coverage at 100 known issues across 10 phases (35-44).

CLI: `python -m pytest tests/test_phase44_yamaha_crossmodel.py -v`

Outputs: `data/knowledge/known_issues_yamaha_crossmodel.json` (10 issues), 6 tests

## Key Concepts
- CCT failure is the universal Yamaha engine issue — APE Pro Series manual tensioner is the cross-model fix
- Ethanol fuel damage is the #1 preventable storage problem — stabilizer + carb drain for carb bikes
- Valve clearance tightening is a Yamaha-wide pattern — hot-start difficulty is the canary in the coal mine
- EXUP valve system spans the sport/standard range — cable lube is the cheapest preventive maintenance
- Brake fluid neglect causes ABS modulator corrosion — 2-year change interval is critical for ABS bikes
- Chain wear rates vary dramatically by riding style: sport (12-18K), naked (15-20K), adventure (10-15K off-road)
- Coolant hose replacement at 10 years regardless of appearance — silicone upgrade for track use
- Tire age matters more than tread depth — 5-year max regardless of wear
- Winterization: stabilized fuel + battery tender + fresh oil prevents 90% of spring problems
- Aftermarket exhaust always needs a tune: exhaust + AIS removal + ECU flash/rejet = correct order

## Verification Checklist
- [x] 10 issues load correctly
- [x] Year range queries return correct results (2020 query returns 7+ hits)
- [x] Critical severity issues present (CCT)
- [x] Symptom searches work (loss of power: 2+, won't start: 1+)
- [x] Forum tips present in fix procedures
- [x] All 6 tests pass (1.74s)
- [x] Full regression suite: 361/361 tests passing (85s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (CCT, ethanol, valves, EXUP, brakes, chain, coolant, tires, winterization, exhaust mods) |
| Tests | 6/6, 1.74s |
| Severity breakdown | 1 critical, 2 high, 7 medium, 0 low |
| Year coverage | 1968-2026 |
| **Yamaha total** | **100 known issues across 10 phases (35-44)** |
| **Full KB total** | **330 known issues (Harley 100, Honda 120, Yamaha 100, pricing module)** |
| **Full test suite** | **361/361 passing** |

Yamaha section complete. The cross-model phase ties together patterns that span the brand — CCT, stator connectors, valve clearance, and ethanol damage are the four pillars of Yamaha maintenance that every mechanic should understand.
