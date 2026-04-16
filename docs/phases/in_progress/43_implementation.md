# MotoDiag Phase 43 — Yamaha Electrical Systems + Diagnostics

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Cross-model Yamaha electrical systems and diagnostic procedures. Covers the Yamaha self-diagnostic system (FI light blink codes), stator/regulator patterns across the lineup, wiring harness issues, and diagnostic tools. This phase consolidates electrical knowledge that applies to multiple Yamaha models.

CLI: `python -m pytest tests/test_phase43_yamaha_electrical.py -v`

Outputs: `data/knowledge/known_issues_yamaha_electrical.json` (10 issues), 6 tests

## Logic
- Create 10 known issues covering cross-model electrical systems
- Self-diagnostic mode procedure (FI light blink codes)
- Stator/regulator failure patterns that span all models
- Wiring harness degradation, grounding issues, fuse/relay diagnostics
- Diagnostic tools: Woolich Racing, dealer tool alternatives

## Key Concepts
- Yamaha self-diagnostic mode uses FI light blink codes (short/long blinks = tens/units digit)
- Every Yamaha from the 1990s onward has the same stator connector weakness
- MOSFET regulator upgrade applies to every model — universal recommendation
- Woolich Racing is the aftermarket diagnostic tool that covers all modern Yamahas
- Ground wire corrosion is the most misdiagnosed electrical fault on Yamahas

## Verification Checklist
- [ ] 10 issues load correctly
- [ ] Year range queries return correct results
- [ ] Critical severity issues present
- [ ] Symptom searches work
- [ ] Forum tips present in fix procedures
- [ ] All tests pass

## Risks
- Cross-model phase must be clearly differentiated from model-specific electrical issues in earlier phases
