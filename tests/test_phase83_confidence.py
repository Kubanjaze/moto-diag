"""Phase 83 — Confidence scoring system tests.

Tests evidence weighting, score calculation, normalization, labeling,
the convenience scoring function, and diagnosis ranking.
"""

import pytest

from motodiag.engine.confidence import (
    EvidenceWeight,
    EvidenceItem,
    ConfidenceScore,
    score_diagnosis_from_evidence,
    rank_diagnoses,
)


# --- Evidence items ---


class TestEvidenceItem:
    def test_supporting_evidence(self):
        item = EvidenceItem(
            source="symptom",
            description="Battery voltage low matches charging system failure",
            weight=EvidenceWeight.SYMPTOM_MATCH,
            supports_diagnosis=True,
        )
        assert item.supports_diagnosis is True
        assert item.weight == 0.15

    def test_contradicting_evidence(self):
        item = EvidenceItem(
            source="diagnostic_test",
            description="Stator AC output is normal — rules out stator failure",
            weight=EvidenceWeight.TEST_RESULT_DENY,
            supports_diagnosis=False,
        )
        assert item.supports_diagnosis is False


# --- Confidence score calculation ---


class TestConfidenceScore:
    def test_empty_score(self):
        score = ConfidenceScore(diagnosis="Stator failure")
        assert score.normalized_score == 0.0
        assert score.evidence_count == 0
        assert score.confidence_label == "unknown"

    def test_single_symptom_evidence(self):
        score = ConfidenceScore(diagnosis="Stator failure")
        score.add_evidence(EvidenceItem(
            source="symptom", description="Battery not charging",
            weight=EvidenceWeight.SYMPTOM_MATCH, supports_diagnosis=True,
        ))
        assert score.evidence_count == 1
        assert score.supporting_count == 1
        assert score.normalized_score > 0.0
        assert score.confidence_label in ("low", "moderate")

    def test_strong_evidence_high_confidence(self):
        score = ConfidenceScore(diagnosis="Stator failure")
        # DTC match + KB match + symptom + test confirmed
        score.add_evidence(EvidenceItem(source="dtc", description="DTC match", weight=EvidenceWeight.DTC_CODE_MATCH, supports_diagnosis=True))
        score.add_evidence(EvidenceItem(source="kb", description="KB match", weight=EvidenceWeight.KB_ISSUE_MATCH, supports_diagnosis=True))
        score.add_evidence(EvidenceItem(source="symptom", description="Symptom match", weight=EvidenceWeight.SYMPTOM_MATCH, supports_diagnosis=True))
        score.add_evidence(EvidenceItem(source="test", description="Test confirmed", weight=EvidenceWeight.TEST_RESULT_CONFIRM, supports_diagnosis=True))
        assert score.normalized_score >= 0.75
        assert score.confidence_label in ("high", "very_high")

    def test_contradicting_evidence_lowers_score(self):
        score = ConfidenceScore(diagnosis="Stator failure")
        # Add some supporting evidence
        score.add_evidence(EvidenceItem(source="symptom", description="Match", weight=0.15, supports_diagnosis=True))
        score.add_evidence(EvidenceItem(source="dtc", description="DTC", weight=0.25, supports_diagnosis=True))
        initial_score = score.normalized_score

        # Add contradicting test result
        score.add_evidence(EvidenceItem(source="test", description="Stator tests good", weight=0.25, supports_diagnosis=False))
        assert score.normalized_score < initial_score
        assert score.contradicting_count == 1

    def test_score_bounds(self):
        score = ConfidenceScore(diagnosis="Test")
        # Add lots of supporting evidence
        for i in range(10):
            score.add_evidence(EvidenceItem(source="test", description=f"Evidence {i}", weight=0.3, supports_diagnosis=True))
        assert score.normalized_score <= 1.0

        # Score with lots of contradicting evidence
        score2 = ConfidenceScore(diagnosis="Test2")
        for i in range(10):
            score2.add_evidence(EvidenceItem(source="test", description=f"Against {i}", weight=0.3, supports_diagnosis=False))
        assert score2.normalized_score >= 0.0

    def test_confidence_labels(self):
        """Test all confidence label thresholds."""
        # Very high
        score_vh = ConfidenceScore(diagnosis="VH")
        score_vh.add_evidence(EvidenceItem(source="test", description="confirmed", weight=0.30, supports_diagnosis=True))
        score_vh.add_evidence(EvidenceItem(source="dtc", description="DTC", weight=0.25, supports_diagnosis=True))
        score_vh.add_evidence(EvidenceItem(source="kb", description="KB", weight=0.20, supports_diagnosis=True))
        score_vh.add_evidence(EvidenceItem(source="sym", description="sym", weight=0.15, supports_diagnosis=True))
        assert score_vh.confidence_label in ("high", "very_high")

        # Low
        score_low = ConfidenceScore(diagnosis="Low")
        score_low.add_evidence(EvidenceItem(source="env", description="Maybe", weight=0.05, supports_diagnosis=True))
        assert score_low.confidence_label in ("very_low", "low")


# --- Convenience scoring function ---


class TestScoreDiagnosisFromEvidence:
    def test_no_evidence(self):
        score = score_diagnosis_from_evidence("Unknown issue")
        assert score.evidence_count == 0
        assert score.normalized_score == 0.0

    def test_symptom_only(self):
        score = score_diagnosis_from_evidence("Stator failure", symptom_matches=2)
        assert score.evidence_count == 2
        assert score.normalized_score > 0.0

    def test_full_evidence_stack(self):
        score = score_diagnosis_from_evidence(
            "Stator failure",
            symptom_matches=2,
            dtc_match=True,
            kb_match=True,
            test_confirmed=True,
            multiple_symptoms_correlated=True,
        )
        assert score.evidence_count == 6  # 2 symptoms + DTC + KB + test + correlation
        assert score.normalized_score >= 0.80
        assert score.confidence_label in ("high", "very_high")

    def test_test_denied_reduces_confidence(self):
        score_confirmed = score_diagnosis_from_evidence(
            "Stator failure",
            symptom_matches=2,
            dtc_match=True,
        )
        score_denied = score_diagnosis_from_evidence(
            "Stator failure",
            symptom_matches=2,
            dtc_match=True,
            test_denied=True,
        )
        assert score_denied.normalized_score < score_confirmed.normalized_score

    def test_symptom_cap_at_5(self):
        score = score_diagnosis_from_evidence("Test", symptom_matches=10)
        assert score.evidence_count == 5  # Capped at 5

    def test_vehicle_history_adds_weight(self):
        score_no_history = score_diagnosis_from_evidence("Stator", symptom_matches=1)
        score_with_history = score_diagnosis_from_evidence("Stator", symptom_matches=1, vehicle_history_match=True)
        assert score_with_history.normalized_score > score_no_history.normalized_score

    def test_environmental_adds_weight(self):
        score_no_env = score_diagnosis_from_evidence("Overheating", symptom_matches=1)
        score_with_env = score_diagnosis_from_evidence("Overheating", symptom_matches=1, environmental_factor=True)
        assert score_with_env.normalized_score > score_no_env.normalized_score


# --- Diagnosis ranking ---


class TestRankDiagnoses:
    def test_ranking_order(self):
        scores = [
            score_diagnosis_from_evidence("Low confidence", symptom_matches=1),
            score_diagnosis_from_evidence("High confidence", symptom_matches=3, dtc_match=True, kb_match=True),
            score_diagnosis_from_evidence("Medium confidence", symptom_matches=2, kb_match=True),
        ]
        ranked = rank_diagnoses(scores)
        assert ranked[0].diagnosis == "High confidence"
        assert ranked[-1].diagnosis == "Low confidence"

    def test_ranking_empty_list(self):
        assert rank_diagnoses([]) == []

    def test_ranking_single_item(self):
        scores = [score_diagnosis_from_evidence("Only one", symptom_matches=1)]
        ranked = rank_diagnoses(scores)
        assert len(ranked) == 1
        assert ranked[0].diagnosis == "Only one"

    def test_ranking_preserves_all_items(self):
        scores = [
            score_diagnosis_from_evidence(f"Diagnosis {i}", symptom_matches=i)
            for i in range(1, 6)
        ]
        ranked = rank_diagnoses(scores)
        assert len(ranked) == 5


# --- Evidence weight constants ---


class TestEvidenceWeights:
    def test_test_confirmed_is_strongest(self):
        assert EvidenceWeight.TEST_RESULT_CONFIRM > EvidenceWeight.DTC_CODE_MATCH
        assert EvidenceWeight.TEST_RESULT_CONFIRM > EvidenceWeight.KB_ISSUE_MATCH
        assert EvidenceWeight.TEST_RESULT_CONFIRM > EvidenceWeight.SYMPTOM_MATCH

    def test_dtc_stronger_than_symptom(self):
        assert EvidenceWeight.DTC_CODE_MATCH > EvidenceWeight.SYMPTOM_MATCH

    def test_kb_stronger_than_symptom(self):
        assert EvidenceWeight.KB_ISSUE_MATCH > EvidenceWeight.SYMPTOM_MATCH

    def test_environmental_is_weakest(self):
        assert EvidenceWeight.ENVIRONMENTAL < EvidenceWeight.SYMPTOM_MATCH
        assert EvidenceWeight.ENVIRONMENTAL < EvidenceWeight.VEHICLE_HISTORY
