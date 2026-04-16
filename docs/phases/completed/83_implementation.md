# MotoDiag Phase 83 — Confidence Scoring

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Build a structured confidence scoring system that weights evidence from multiple sources (symptoms, DTCs, knowledge base, test results, vehicle history, environmental factors) to produce calibrated probability estimates for each diagnosis. Provides both raw scores and human-readable confidence labels.

CLI: `python -m pytest tests/test_phase83_confidence.py -v`

Outputs: `src/motodiag/engine/confidence.py`, 23 tests

## Key Concepts
- EvidenceWeight constants: test_confirmed (0.30) > DTC match (0.25) > KB match (0.20) > symptom (0.15) > history (0.10) > environmental (0.05)
- EvidenceItem model: source, description, weight, supports_diagnosis flag
- ConfidenceScore: accumulates evidence items, normalizes raw score to 0.0-1.0, assigns confidence label
- Normalization: sigmoid-like mapping — raw scores below 0 map to very low confidence, above 0.6 map to high/very high
- Confidence labels: very_high (>=0.85), high (>=0.65), moderate (>=0.40), low (>=0.20), very_low (<0.20)
- Contradicting evidence: test_denied subtracts from score, supports honest uncertainty
- Convenience function: score_diagnosis_from_evidence() builds score from discrete flags
- Symptom cap at 5: prevents over-weighting from many symptoms pointing to same cause
- rank_diagnoses(): sorts multiple diagnoses by confidence, highest first

## Verification Checklist
- [x] Evidence items create with correct weight and direction (2 tests)
- [x] Score calculation: empty, single, strong, contradicting, bounds (6 tests)
- [x] Convenience function: no evidence, symptom only, full stack, denied, cap, history, environmental (7 tests)
- [x] Ranking: correct order, empty, single, preservation (4 tests)
- [x] Weight constants: correct hierarchy (4 tests)
- [x] All 23 tests pass (0.07s)

## Results
| Metric | Value |
|--------|-------|
| Files created | 1 (confidence.py) |
| Tests | 23/23, 0.07s |
| Evidence types | 8 (symptom, DTC, KB, test confirm, test deny, history, correlation, environmental) |
| Confidence labels | 5 (very_high, high, moderate, low, very_low) |
