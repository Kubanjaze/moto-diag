"""Tests for Phase 107 — AI Audio Coaching.

Tests AudioCoach, CaptureProtocol, CoachingStep, protocol selection,
step-by-step coaching, capture quality evaluation, and all 5 predefined protocols.
All tests use synthetic audio — no hardware or API calls.
"""

import math
import pytest

from motodiag.media.coaching import (
    AudioCoach,
    CaptureProtocol,
    CoachingStep,
    CaptureQuality,
    EngineType,
    QualityAssessment,
    CAPTURE_PROTOCOLS,
    SYMPTOM_PROTOCOL_MAP,
    _score_to_quality,
)
from motodiag.media.audio_capture import (
    AudioSample,
    generate_sine_wave,
    generate_composite_wave,
)


# --- Helpers ---

def _make_good_sample(duration: float = 5.0) -> AudioSample:
    """Create a clean, loud-enough audio sample."""
    return generate_sine_wave(frequency=100.0, duration=duration, amplitude=0.5)


def _make_silent_sample(duration: float = 2.0) -> AudioSample:
    """Create a near-silent audio sample."""
    return AudioSample(
        samples=[0.001 * (i % 2) for i in range(int(44100 * duration))],
        sample_rate=44100,
        channels=1,
        duration_seconds=duration,
        source="synthetic",
    )


def _make_clipped_sample(duration: float = 2.0) -> AudioSample:
    """Create an audio sample with heavy clipping."""
    sr = 44100
    n = int(sr * duration)
    # Square wave that clips at 0.99
    samples = [0.99 if math.sin(2 * math.pi * 100 * i / sr) > 0 else -0.99 for i in range(n)]
    return AudioSample(
        samples=samples,
        sample_rate=sr,
        channels=1,
        duration_seconds=duration,
        source="synthetic",
    )


# --- CaptureProtocol and CoachingStep model tests ---

class TestModels:
    def test_coaching_step_creation(self):
        step = CoachingStep(
            step_number=1,
            instruction="Start the engine.",
            expected_condition="Engine running at idle.",
            duration_seconds=10,
            rpm_target=1000,
        )
        assert step.step_number == 1
        assert step.duration_seconds == 10
        assert step.rpm_target == 1000
        assert step.mic_position == "near exhaust"

    def test_capture_protocol_creation(self):
        proto = CaptureProtocol(
            name="test_protocol",
            description="A test protocol.",
            steps=[
                CoachingStep(step_number=1, instruction="Do X", expected_condition="Y", duration_seconds=5),
                CoachingStep(step_number=2, instruction="Do Z", expected_condition="W", duration_seconds=10),
            ],
            total_duration=15,
        )
        assert proto.step_count == 2
        assert proto.total_duration == 15

    def test_quality_score_mapping(self):
        assert _score_to_quality(0.90) == CaptureQuality.EXCELLENT
        assert _score_to_quality(0.75) == CaptureQuality.GOOD
        assert _score_to_quality(0.55) == CaptureQuality.ACCEPTABLE
        assert _score_to_quality(0.35) == CaptureQuality.POOR
        assert _score_to_quality(0.10) == CaptureQuality.UNUSABLE


# --- Predefined protocol tests ---

class TestPredefinedProtocols:
    def test_all_five_protocols_exist(self):
        expected = ["idle_baseline", "rev_sweep", "load_test", "cold_start", "decel_pop"]
        for name in expected:
            assert name in CAPTURE_PROTOCOLS

    def test_idle_baseline_structure(self):
        proto = CAPTURE_PROTOCOLS["idle_baseline"]
        assert proto.step_count == 3
        assert proto.total_duration == 50
        assert "rough idle" in proto.symptoms_applicable

    def test_rev_sweep_structure(self):
        proto = CAPTURE_PROTOCOLS["rev_sweep"]
        assert proto.step_count == 5
        assert proto.total_duration == 40
        assert "flat spot" in proto.symptoms_applicable

    def test_load_test_structure(self):
        proto = CAPTURE_PROTOCOLS["load_test"]
        assert proto.step_count == 4
        assert proto.total_duration == 35

    def test_cold_start_structure(self):
        proto = CAPTURE_PROTOCOLS["cold_start"]
        assert proto.step_count == 4
        assert proto.total_duration == 85
        assert "hard starting" in proto.symptoms_applicable

    def test_decel_pop_structure(self):
        proto = CAPTURE_PROTOCOLS["decel_pop"]
        assert proto.step_count == 5
        assert proto.total_duration == 48
        assert "decel popping" in proto.symptoms_applicable

    def test_all_protocols_have_steps(self):
        for name, proto in CAPTURE_PROTOCOLS.items():
            assert proto.step_count > 0, f"{name} has no steps"
            assert proto.total_duration > 0, f"{name} has no duration"


# --- AudioCoach protocol selection tests ---

class TestGetProtocol:
    def test_get_by_name(self):
        coach = AudioCoach()
        proto = coach.get_protocol(name="rev_sweep")
        assert proto.name == "rev_sweep"

    def test_get_unknown_name_raises(self):
        coach = AudioCoach()
        with pytest.raises(ValueError, match="Unknown protocol"):
            coach.get_protocol(name="nonexistent")

    def test_get_by_symptom_direct_match(self):
        coach = AudioCoach()
        proto = coach.get_protocol(symptom="decel popping")
        assert proto.name == "decel_pop"

    def test_get_by_symptom_fuzzy_match(self):
        coach = AudioCoach()
        proto = coach.get_protocol(symptom="backfire")
        assert proto.name == "decel_pop"

    def test_get_by_symptom_default_fallback(self):
        coach = AudioCoach()
        proto = coach.get_protocol(symptom="something very obscure")
        assert proto.name == "idle_baseline"

    def test_get_default_protocol(self):
        coach = AudioCoach()
        proto = coach.get_protocol()
        assert proto.name == "idle_baseline"

    def test_get_protocols_for_symptom(self):
        coach = AudioCoach()
        protos = coach.get_protocols_for_symptom("misfire")
        assert len(protos) >= 2
        names = [p.name for p in protos]
        assert "load_test" in names

    def test_list_protocols(self):
        coach = AudioCoach()
        listing = coach.list_protocols()
        assert len(listing) == 5
        assert all("name" in p for p in listing)
        assert all("total_duration" in p for p in listing)


# --- AudioCoach coaching session tests ---

class TestCoachingSession:
    def test_start_protocol(self):
        coach = AudioCoach()
        proto = coach.get_protocol(name="idle_baseline")
        step = coach.start_protocol(proto)
        assert coach.is_active is True
        assert step.step_number == 1
        assert coach.progress == 0.0

    def test_start_when_active_raises(self):
        coach = AudioCoach()
        proto = coach.get_protocol(name="idle_baseline")
        coach.start_protocol(proto)
        with pytest.raises(RuntimeError, match="already active"):
            coach.start_protocol(proto)

    def test_start_empty_protocol_raises(self):
        coach = AudioCoach()
        empty = CaptureProtocol(name="empty", description="No steps")
        with pytest.raises(ValueError, match="no steps"):
            coach.start_protocol(empty)

    def test_get_current_step(self):
        coach = AudioCoach()
        proto = coach.get_protocol(name="load_test")
        coach.start_protocol(proto)
        step = coach.get_current_step()
        assert step is not None
        assert step.step_number == 1

    def test_get_current_step_no_session(self):
        coach = AudioCoach()
        assert coach.get_current_step() is None

    def test_advance_step(self):
        coach = AudioCoach()
        proto = coach.get_protocol(name="idle_baseline")  # 3 steps
        coach.start_protocol(proto)
        step2 = coach.advance_step()
        assert step2 is not None
        assert step2.step_number == 2
        step3 = coach.advance_step()
        assert step3 is not None
        assert step3.step_number == 3
        step4 = coach.advance_step()
        assert step4 is None  # Past the end

    def test_advance_no_session_raises(self):
        coach = AudioCoach()
        with pytest.raises(RuntimeError, match="No active"):
            coach.advance_step()

    def test_finish_protocol(self):
        coach = AudioCoach()
        proto = coach.get_protocol(name="idle_baseline")
        coach.start_protocol(proto)
        coach.advance_step()
        coach.advance_step()
        summary = coach.finish_protocol()
        assert summary["protocol"] == "idle_baseline"
        assert summary["steps_total"] == 3
        assert summary["steps_completed"] == 2
        assert coach.is_active is False

    def test_finish_no_session_raises(self):
        coach = AudioCoach()
        with pytest.raises(RuntimeError, match="No active"):
            coach.finish_protocol()

    def test_progress_tracking(self):
        coach = AudioCoach()
        proto = coach.get_protocol(name="idle_baseline")  # 3 steps
        coach.start_protocol(proto)
        assert coach.progress == pytest.approx(0.0)
        coach.advance_step()
        assert coach.progress == pytest.approx(1 / 3, abs=0.01)
        coach.advance_step()
        assert coach.progress == pytest.approx(2 / 3, abs=0.01)


# --- Capture quality evaluation tests ---

class TestEvaluateCapture:
    def test_good_sample_quality(self):
        coach = AudioCoach()
        sample = _make_good_sample(duration=5.0)
        assessment = coach.evaluate_capture(sample)
        assert assessment.quality in (CaptureQuality.EXCELLENT, CaptureQuality.GOOD)
        assert assessment.score >= 0.7
        assert assessment.meets_minimum is True
        # May have minor SNR note for synthetic data — that's acceptable
        assert len(assessment.issues) <= 1

    def test_silent_sample_low_quality(self):
        coach = AudioCoach()
        sample = _make_silent_sample(duration=5.0)
        assessment = coach.evaluate_capture(sample)
        assert assessment.quality in (CaptureQuality.POOR, CaptureQuality.UNUSABLE)
        assert assessment.score < 0.5
        assert len(assessment.issues) > 0
        assert any("signal" in issue.lower() or "silent" in issue.lower() for issue in assessment.issues)

    def test_clipped_sample_issues(self):
        coach = AudioCoach()
        sample = _make_clipped_sample(duration=5.0)
        assessment = coach.evaluate_capture(sample)
        assert any("clip" in issue.lower() for issue in assessment.issues)

    def test_short_sample_issues(self):
        coach = AudioCoach()
        proto = CAPTURE_PROTOCOLS["idle_baseline"]
        coach.start_protocol(proto)
        # First step expects 10s; give 1s
        sample = _make_good_sample(duration=1.0)
        assessment = coach.evaluate_capture(sample, protocol=proto)
        assert any("short" in issue.lower() for issue in assessment.issues)

    def test_evaluate_stores_in_session(self):
        coach = AudioCoach()
        proto = coach.get_protocol(name="idle_baseline")
        coach.start_protocol(proto)
        sample = _make_good_sample(duration=10.0)
        coach.evaluate_capture(sample, protocol=proto)
        summary = coach.finish_protocol()
        assert summary["steps_evaluated"] == 1

    def test_metrics_present(self):
        coach = AudioCoach()
        sample = _make_good_sample(duration=3.0)
        assessment = coach.evaluate_capture(sample)
        assert "duration_seconds" in assessment.metrics
        assert "peak_amplitude" in assessment.metrics
        assert "rms_amplitude" in assessment.metrics
        assert "clip_ratio" in assessment.metrics

    def test_empty_sample(self):
        coach = AudioCoach()
        empty = AudioSample(samples=[], sample_rate=44100, duration_seconds=0.0, source="synthetic")
        assessment = coach.evaluate_capture(empty)
        assert assessment.score < 1.0
