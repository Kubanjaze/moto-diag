"""Phase 94 — AI evaluation + accuracy tracking tests.

Tests diagnostic outcome recording, quality scorecard calculation,
ADR-005 composite scoring, model comparison, and report formatting.
"""

import pytest
from datetime import datetime, timezone

from motodiag.engine.evaluation import (
    DiagnosticOutcome,
    QualityScorecard,
    EvaluationTracker,
)


# --- Models ---


class TestDiagnosticOutcome:
    def test_basic_creation(self):
        outcome = DiagnosticOutcome(
            session_id="test-001",
            predicted_diagnosis="Stator failure",
            predicted_confidence=0.85,
            actual_diagnosis="Stator failure",
            was_correct=True,
            was_helpful=True,
            api_cost_usd=0.003,
            latency_ms=1200,
            tokens_used=800,
            model_used="haiku",
        )
        assert outcome.session_id == "test-001"
        assert outcome.was_correct is True
        assert outcome.api_cost_usd == 0.003

    def test_outcome_without_result(self):
        outcome = DiagnosticOutcome(
            session_id="test-002",
            predicted_diagnosis="CCT failure",
            predicted_confidence=0.70,
        )
        assert outcome.was_correct is None
        assert outcome.actual_diagnosis == ""

    def test_timestamp_auto_set(self):
        outcome = DiagnosticOutcome(
            session_id="test-003",
            predicted_diagnosis="Test",
            predicted_confidence=0.5,
        )
        assert outcome.timestamp is not None


class TestQualityScorecard:
    def test_empty_scorecard(self):
        sc = QualityScorecard()
        assert sc.composite_score == 0.0
        assert sc.total_sessions == 0

    def test_perfect_scorecard(self):
        sc = QualityScorecard(
            accuracy_rate=1.0,
            helpfulness_rate=1.0,
            confidence_calibration=1.0,
            quality_score=1.0,
            cost_efficiency=1.0,
            cost_score=1.0,
            latency_score=1.0,
            composite_score=1.0,
        )
        assert sc.composite_score == 1.0


# --- EvaluationTracker ---


class TestEvaluationTracker:
    def _make_outcome(self, correct=True, helpful=True, confidence=0.8, cost=0.003, latency=1000, model="haiku"):
        return DiagnosticOutcome(
            session_id=f"test-{id(correct)}",
            predicted_diagnosis="Stator failure",
            predicted_confidence=confidence,
            actual_diagnosis="Stator failure" if correct else "Reg/rec failure",
            was_correct=correct,
            was_helpful=helpful,
            api_cost_usd=cost,
            latency_ms=latency,
            tokens_used=800,
            model_used=model,
        )

    def test_empty_tracker(self):
        tracker = EvaluationTracker()
        sc = tracker.get_scorecard()
        assert sc.total_sessions == 0
        assert sc.composite_score == 0.0

    def test_single_correct_outcome(self):
        tracker = EvaluationTracker()
        tracker.record_outcome(self._make_outcome(correct=True))
        sc = tracker.get_scorecard()
        assert sc.total_sessions == 1
        assert sc.accuracy_rate == 1.0
        assert sc.sessions_with_outcome == 1

    def test_mixed_outcomes(self):
        tracker = EvaluationTracker()
        tracker.record_outcome(self._make_outcome(correct=True))
        tracker.record_outcome(self._make_outcome(correct=True))
        tracker.record_outcome(self._make_outcome(correct=False))
        sc = tracker.get_scorecard()
        assert sc.total_sessions == 3
        assert 0.6 < sc.accuracy_rate < 0.7  # 2/3

    def test_cost_efficiency_low_cost(self):
        tracker = EvaluationTracker()
        tracker.record_outcome(self._make_outcome(cost=0.003))
        sc = tracker.get_scorecard()
        assert sc.cost_efficiency > 0.9  # Very cheap

    def test_cost_efficiency_high_cost(self):
        tracker = EvaluationTracker()
        tracker.record_outcome(self._make_outcome(cost=0.15))
        sc = tracker.get_scorecard()
        assert sc.cost_efficiency == 0.0  # Too expensive

    def test_latency_score_fast(self):
        tracker = EvaluationTracker()
        tracker.record_outcome(self._make_outcome(latency=500))
        sc = tracker.get_scorecard()
        assert sc.latency_score == 1.0  # <1s

    def test_latency_score_slow(self):
        tracker = EvaluationTracker()
        tracker.record_outcome(self._make_outcome(latency=6000))
        sc = tracker.get_scorecard()
        assert sc.latency_score == 0.1  # >5s

    def test_composite_score_weights(self):
        """Composite = Quality*0.4 + Cost*0.4 + Latency*0.2"""
        tracker = EvaluationTracker()
        # Perfect accuracy, cheap, fast
        tracker.record_outcome(self._make_outcome(correct=True, helpful=True, cost=0.001, latency=500))
        sc = tracker.get_scorecard()
        assert sc.composite_score > 0.8  # Should be very high

    def test_helpfulness_tracking(self):
        tracker = EvaluationTracker()
        tracker.record_outcome(self._make_outcome(helpful=True))
        tracker.record_outcome(self._make_outcome(helpful=True))
        tracker.record_outcome(self._make_outcome(helpful=False))
        sc = tracker.get_scorecard()
        assert 0.6 < sc.helpfulness_rate < 0.7  # 2/3

    def test_confidence_calibration_perfect(self):
        """When confidence matches accuracy, calibration should be high."""
        tracker = EvaluationTracker()
        # 80% confidence, 80% accuracy → perfect calibration
        for i in range(8):
            tracker.record_outcome(self._make_outcome(correct=True, confidence=0.8))
        for i in range(2):
            tracker.record_outcome(self._make_outcome(correct=False, confidence=0.8))
        sc = tracker.get_scorecard()
        assert sc.confidence_calibration > 0.9

    def test_confidence_calibration_poor(self):
        """When confidence doesn't match accuracy, calibration should be low."""
        tracker = EvaluationTracker()
        # 90% confidence but only 20% accuracy → poor calibration
        for i in range(2):
            tracker.record_outcome(self._make_outcome(correct=True, confidence=0.9))
        for i in range(8):
            tracker.record_outcome(self._make_outcome(correct=False, confidence=0.9))
        sc = tracker.get_scorecard()
        assert sc.confidence_calibration < 0.5


# --- Model comparison ---


class TestModelComparison:
    def test_accuracy_by_model(self):
        tracker = EvaluationTracker()
        tracker.record_outcome(DiagnosticOutcome(
            session_id="h1", predicted_diagnosis="Test", predicted_confidence=0.8,
            was_correct=True, model_used="haiku", api_cost_usd=0.001, latency_ms=500,
        ))
        tracker.record_outcome(DiagnosticOutcome(
            session_id="s1", predicted_diagnosis="Test", predicted_confidence=0.9,
            was_correct=True, model_used="sonnet", api_cost_usd=0.01, latency_ms=2000,
        ))
        tracker.record_outcome(DiagnosticOutcome(
            session_id="h2", predicted_diagnosis="Test", predicted_confidence=0.7,
            was_correct=False, model_used="haiku", api_cost_usd=0.001, latency_ms=500,
        ))

        accuracy = tracker.get_accuracy_by_model()
        assert "haiku" in accuracy
        assert "sonnet" in accuracy
        assert accuracy["haiku"] == 0.5  # 1/2
        assert accuracy["sonnet"] == 1.0  # 1/1

    def test_cost_by_model(self):
        tracker = EvaluationTracker()
        tracker.record_outcome(DiagnosticOutcome(
            session_id="h1", predicted_diagnosis="Test", predicted_confidence=0.8,
            was_correct=True, model_used="haiku", api_cost_usd=0.002, latency_ms=500,
        ))
        tracker.record_outcome(DiagnosticOutcome(
            session_id="s1", predicted_diagnosis="Test", predicted_confidence=0.8,
            was_correct=True, model_used="sonnet", api_cost_usd=0.015, latency_ms=2000,
        ))

        costs = tracker.get_cost_by_model()
        assert costs["haiku"] < costs["sonnet"]


# --- Report formatting ---


class TestFormatScorecard:
    def test_format_produces_string(self):
        tracker = EvaluationTracker()
        tracker.record_outcome(DiagnosticOutcome(
            session_id="test", predicted_diagnosis="Test", predicted_confidence=0.8,
            was_correct=True, was_helpful=True, api_cost_usd=0.003, latency_ms=1000,
            model_used="haiku",
        ))
        report = tracker.format_scorecard()
        assert isinstance(report, str)
        assert "COMPOSITE SCORE" in report
        assert "QUALITY" in report
        assert "COST" in report
        assert "LATENCY" in report

    def test_format_empty_tracker(self):
        tracker = EvaluationTracker()
        report = tracker.format_scorecard()
        assert "Sessions evaluated: 0" in report

    def test_format_includes_accuracy(self):
        tracker = EvaluationTracker()
        tracker.record_outcome(DiagnosticOutcome(
            session_id="test", predicted_diagnosis="Test", predicted_confidence=0.8,
            was_correct=True, was_helpful=True, api_cost_usd=0.003, latency_ms=1000,
            model_used="haiku",
        ))
        report = tracker.format_scorecard()
        assert "Accuracy rate" in report
        assert "100.0%" in report
