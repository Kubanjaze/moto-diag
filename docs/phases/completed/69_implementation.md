# MotoDiag Phase 69 — Suzuki Common Cross-Model Issues

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Universal Suzuki issues that span all model families — stator connector fire risk, CCT pattern, fuel pump relay, PAIR removal, coolant service, valve clearance, chain maintenance, brake fluid, fork seals, and exhaust fueling.

CLI: `python -m pytest tests/test_phase69_suzuki_common.py -v`

Outputs: `data/knowledge/known_issues_suzuki_common.json` (10 issues), 6 tests

## Key Concepts
- Stator connector melting: the #1 fire risk on any Suzuki — solder the 3 wires as standard service
- CCT failure pattern: APE manual tensioner is the universal fix, model-specific fitment, V-twins need both
- Fuel pump relay: $15 part stranding thousands annually, interchangeable across many models, carry a spare
- PAIR removal: universal concept, model-specific bolt patterns, does NOT affect fueling
- Coolant flush: 2-year cycle, Engine Ice for sport bikes, old coolant becomes acidic
- Valve clearance: 15K street / 7.5K track, exhaust valves tighten first, hard cold start = tight valves
- Chain and sprocket: countershaft sprocket is the canary, X-ring chain 2x the life of budget chain
- Brake fluid: flush every 2 years, Motul RBF 600 for track, replace banjo bolt crush washers
- Fork seals: Seal Mate tool saves 50%, fork oil every 15K miles, weight matters for damping
- Exhaust modifications: exhaust + K&N + fuel controller + PAIR block-off is the universal formula

## Verification Checklist
- [x] All 6 tests pass (0.68s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Tests | 6/6, 0.68s |
| Severity breakdown | 1 critical, 2 high, 6 medium, 1 low |
| Year coverage | 1985-2026 |
