# MotoDiag Phase 51 — Kawasaki Ninja H2 / H2R (2015+)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Kawasaki's supercharged hyperbike: Ninja H2 (street), H2 SX (sport-tourer), and H2R (track-only). The only supercharged production motorcycle.

CLI: `python -m pytest tests/test_phase51_kawasaki_h2.py -v`

Outputs: `data/knowledge/known_issues_kawasaki_h2.json` (10 issues), 6 tests

## Key Concepts
- Supercharger is sealed/maintenance-free — intake ducting seals and intercooler are the service items
- Cooling system operates at absolute limits — dual radiator, no thermal margin, both fans must work
- IMU-based electronics (KTRC/KIBS/KLCM/KEBC) plus boost control = most complex Kawasaki system
- Mirror chrome paint requires hand-wash only — pH-neutral products, no abrasives
- 525 chain under supercharged torque shock loads — premium X-ring chain mandatory
- Oil change at 3,750 miles (not 7,500) — supercharger planetary gears break down oil faster
- Fuel system must maintain pressure against boost — lean under boost is catastrophic
- H2 SX cruise control is vacuum-operated — hose leaks cause random disengagement
- Brakes need annual fluid flush — 200mph braking generates extreme heat
- Valve clearance tightens faster than NA engines — don't extend intervals on the H2

## Verification Checklist
- [x] 10 issues load correctly
- [x] Year range queries return correct results (2022 query returns 8+ hits)
- [x] Critical severity issues present (cooling, fuel under boost)
- [x] Symptom searches work (loss of power: 2+, won't start: 1+)
- [x] Forum tips present in fix procedures
- [x] All 6 tests pass (1.65s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (supercharger, cooling, electronics, paint, chain, oil, fuel, H2 SX, brakes, valves) |
| Tests | 6/6, 1.65s |
| Severity breakdown | 2 critical, 4 high, 4 medium, 0 low |
| Year coverage | 2015-2026 |

The H2 phase introduces supercharger diagnostics — a completely unique category in motorcycle maintenance. Every issue traces back to the demands of forced induction: more heat, more stress, more fuel, shorter service intervals.
