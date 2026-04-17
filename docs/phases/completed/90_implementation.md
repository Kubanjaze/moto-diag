# MotoDiag Phase 90 — Multi-Symptom Correlation

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Connect seemingly unrelated symptoms to a single root cause using predefined correlation rules. When a mechanic reports "overheating + loss of power + coolant smell," the correlator identifies "head gasket failure" with high confidence. 15+ predefined rules covering the most common multi-symptom patterns across all makes.

CLI: `python -m pytest tests/test_phase90_correlation.py -v`

Outputs: `src/motodiag/engine/correlation.py`, 38 tests

## Key Concepts
- CorrelationRule model: symptom_set, root_cause, confidence, explanation, affected_system
- 15+ predefined rules covering: head gasket, stator/reg-rec, fuel flooding, CCT, vacuum leak, chain/sprocket, clutch drag, overcharging, fuel pump, starter clutch, brake failure, carburetor sync, ignition coil, coolant system, valve clearance
- Match quality scoring: symptoms matched / total in rule — partial matches (>=2 of 3+) included
- SymptomCorrelator.correlate(): takes symptom list → returns ranked matching rules
- Rules ranked by match quality × rule confidence
- Each rule includes affected_system for directing diagnostic workflow
- Pure pattern matching — no API calls needed

## Verification Checklist
- [x] 15+ correlation rules with complete data (38 tests)
- [x] Full symptom set matches score highest
- [x] Partial matches (2 of 3) included at reduced confidence
- [x] Rules ranked by match quality
- [x] All 38 tests pass (pure logic)

## Results
| Metric | Value |
|--------|-------|
| Files created | 1 (correlation.py) |
| Tests | 38/38 |
| Correlation rules | 15+ predefined multi-symptom patterns |
| Systems covered | electrical, fuel, mechanical, cooling, drivetrain, braking |
