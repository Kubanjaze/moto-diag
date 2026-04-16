# MotoDiag Phase 94 — AI Evaluation + Accuracy Tracking

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Track diagnostic accuracy against known outcomes, monitor API cost per diagnosis, and produce quality scorecards using the ADR-005 evaluation framework: Quality (40%) + Cost (40%) + Latency (20%). Enables continuous improvement by measuring what matters.

CLI: `python -m pytest tests/test_phase94_evaluation.py -v`

Outputs: `src/motodiag/engine/evaluation.py` (EvaluationTracker + scorecard), 21 tests

## Key Concepts
- DiagnosticOutcome model: predicted vs actual diagnosis, was_correct, was_helpful, cost, latency, tokens, model
- QualityScorecard: 3 weighted components — quality (accuracy + helpfulness + calibration), cost efficiency, latency
- ADR-005 composite: Quality × 0.4 + Cost × 0.4 + Latency × 0.2
- Accuracy rate: correct diagnoses / total with known outcomes
- Helpfulness rate: useful outputs / total with feedback (separate from accuracy)
- Confidence calibration: how closely predicted confidence matches actual accuracy (perfect = 1.0)
- Cost efficiency: $0 = 1.0, $0.10+ = 0.0 — penalizes expensive diagnoses heavily
- Latency scoring: <1s = 1.0, 1-3s = 0.7, 3-5s = 0.4, >5s = 0.1
- Model comparison: accuracy_by_model() and cost_by_model() for Haiku vs Sonnet decisions
- format_scorecard(): human-readable ASCII report with all metrics

## Verification Checklist
- [x] DiagnosticOutcome creates with and without actual outcome (3 tests)
- [x] QualityScorecard creates with all metrics (2 tests)
- [x] EvaluationTracker: empty, single, mixed outcomes, cost, latency, composite, helpfulness, calibration (11 tests)
- [x] Model comparison: accuracy by model, cost by model (2 tests)
- [x] Report formatting: produces string, empty tracker, includes accuracy (3 tests)
- [x] All 21 tests pass (0.22s)

## Results
| Metric | Value |
|--------|-------|
| Files created | 1 (evaluation.py) |
| Tests | 21/21, 0.22s |
| Evaluation dimensions | 3 (quality, cost, latency) |
| Quality sub-metrics | 3 (accuracy, helpfulness, calibration) |
| ADR-005 weights | Q:40% + C:40% + L:20% |
