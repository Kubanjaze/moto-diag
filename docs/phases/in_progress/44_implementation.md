# MotoDiag Phase 44 — Yamaha Common Cross-Model Issues

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Final Yamaha phase. Cross-model issues that appear across the entire Yamaha lineup — patterns that transcend individual models. Completes Yamaha coverage at 100 known issues across 10 phases.

CLI: `python -m pytest tests/test_phase44_yamaha_crossmodel.py -v`

Outputs: `data/knowledge/known_issues_yamaha_crossmodel.json` (10 issues), 6 tests

## Logic
- Create 10 known issues that span multiple Yamaha models
- Focus on patterns seen across the brand: CCT, EXUP, valve clearance, throttle issues, chain, brakes, coolant, tires, storage, ethanol
- Complement model-specific phases without duplicating them

## Key Concepts
- CCT failure pattern common across all Yamaha inline-4 and V4 engines
- EXUP valve system shared across sport bike range
- Ethanol fuel damage is the universal storage problem
- Valve clearance tightening is a Yamaha-wide pattern (shim-under-bucket and screw-type)
- Brake fluid neglect causes ABS modulator failures

## Verification Checklist
- [ ] 10 issues load correctly
- [ ] Year range queries return correct results
- [ ] Critical severity issues present
- [ ] Symptom searches work
- [ ] Forum tips present
- [ ] All tests pass

## Risks
- Must add value beyond model-specific phases — focus on cross-model diagnostic patterns
