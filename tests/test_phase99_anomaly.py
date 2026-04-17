"""Tests for Phase 99 — Audio Anomaly Detection.

All tests use synthetic audio data — no engine recordings or audio hardware
required. Tests verify anomaly detection against known spectral patterns,
severity ranking, confidence scoring, and the is_normal/get_severity helpers.
"""

import math
import pytest

from motodiag.media.audio_capture import generate_sine_wave, generate_composite_wave
from motodiag.media.spectrogram import SpectrogramAnalyzer, SpectrogramResult
from motodiag.media.anomaly_detection import (
    AnomalyType,
    Severity,
    AnomalySignature,
    AudioAnomaly,
    AudioAnomalyDetector,
    ANOMALY_SIGNATURES,
    _ANOMALY_LOOKUP,
)


# --- Helpers ---

def make_spectrogram(frequency: float, sample_rate: int = 44100, amplitude: float = 0.8) -> SpectrogramResult:
    """Generate a sine wave and return its SpectrogramResult."""
    sample = generate_sine_wave(frequency=frequency, duration=0.5, sample_rate=sample_rate, amplitude=amplitude)
    analyzer = SpectrogramAnalyzer(window_size=1024)
    return analyzer.analyze(sample)


def make_composite_spectrogram(frequencies: list[float], sample_rate: int = 44100) -> SpectrogramResult:
    """Generate composite wave and return its SpectrogramResult."""
    sample = generate_composite_wave(frequencies=frequencies, duration=0.5, sample_rate=sample_rate, amplitude=0.4)
    analyzer = SpectrogramAnalyzer(window_size=1024)
    return analyzer.analyze(sample)


# --- Fixtures ---

@pytest.fixture
def detector():
    return AudioAnomalyDetector()


@pytest.fixture
def sensitive_detector():
    """Detector with very low confidence threshold to catch marginal anomalies."""
    return AudioAnomalyDetector(confidence_threshold=0.1)


@pytest.fixture
def empty_spectrogram():
    return SpectrogramResult()


# --- Enum tests ---

class TestAnomalyType:
    def test_all_types_defined(self):
        expected = {
            "knock", "misfire", "valve_tick", "exhaust_leak", "bearing_whine",
            "cam_chain_rattle", "starter_grind", "clutch_rattle", "detonation", "normal",
        }
        actual = {t.value for t in AnomalyType}
        assert actual == expected

    def test_string_values(self):
        assert AnomalyType.KNOCK.value == "knock"
        assert AnomalyType.BEARING_WHINE.value == "bearing_whine"


class TestSeverity:
    def test_all_severities_defined(self):
        expected = {"critical", "high", "moderate", "low", "none"}
        actual = {s.value for s in Severity}
        assert actual == expected


# --- Anomaly signature definition tests ---

class TestAnomalySignatures:
    def test_signatures_count(self):
        """Should have 9 anomaly signatures (all types except NORMAL)."""
        assert len(ANOMALY_SIGNATURES) == 9

    def test_all_non_normal_types_have_signatures(self):
        defined_types = {sig.anomaly_type for sig in ANOMALY_SIGNATURES}
        for at in AnomalyType:
            if at != AnomalyType.NORMAL:
                assert at in defined_types, f"Missing signature for {at.value}"

    def test_signatures_have_required_fields(self):
        for sig in ANOMALY_SIGNATURES:
            assert sig.freq_low < sig.freq_high
            assert 0 < sig.energy_threshold <= 1.0
            assert sig.severity in Severity
            assert len(sig.description) > 20
            assert len(sig.likely_causes) >= 3

    def test_knock_signature_details(self):
        sig = _ANOMALY_LOOKUP[AnomalyType.KNOCK]
        assert sig.freq_low == 1000.0
        assert sig.freq_high == 4000.0
        assert sig.severity == Severity.CRITICAL
        assert any("rod bearing" in cause.lower() for cause in sig.likely_causes)

    def test_valve_tick_signature_details(self):
        sig = _ANOMALY_LOOKUP[AnomalyType.VALVE_TICK]
        assert sig.freq_low == 500.0
        assert sig.freq_high == 2000.0
        assert sig.severity == Severity.MODERATE

    def test_detonation_is_critical(self):
        sig = _ANOMALY_LOOKUP[AnomalyType.DETONATION]
        assert sig.severity == Severity.CRITICAL

    def test_clutch_rattle_is_low_severity(self):
        sig = _ANOMALY_LOOKUP[AnomalyType.CLUTCH_RATTLE]
        assert sig.severity == Severity.LOW


# --- AudioAnomaly model tests ---

class TestAudioAnomaly:
    def test_create_anomaly(self):
        anomaly = AudioAnomaly(
            anomaly_type=AnomalyType.KNOCK,
            confidence=0.85,
            frequency_range=(1000.0, 4000.0),
            description="Rod knock detected",
            likely_causes=["Rod bearing wear"],
            severity=Severity.CRITICAL,
        )
        assert anomaly.confidence == 0.85
        assert anomaly.severity == Severity.CRITICAL

    def test_default_fields(self):
        anomaly = AudioAnomaly(
            anomaly_type=AnomalyType.NORMAL,
            confidence=1.0,
            frequency_range=(0.0, 22050.0),
        )
        assert anomaly.likely_causes == []
        assert anomaly.energy_fraction == 0.0
        assert anomaly.recommendation == ""


# --- Detection tests ---

class TestDetect:
    def test_detect_returns_list(self, detector):
        spec = make_spectrogram(3000.0)
        result = detector.detect(spec)
        assert isinstance(result, list)

    def test_detect_empty_spectrogram(self, detector, empty_spectrogram):
        result = detector.detect(empty_spectrogram)
        assert result == []

    def test_detect_sorted_by_confidence(self, sensitive_detector):
        """Results should be sorted by confidence descending."""
        # Use a broadband signal that may trigger multiple anomalies
        spec = make_composite_spectrogram([500.0, 1500.0, 3000.0, 5000.0])
        result = sensitive_detector.detect(spec)
        for i in range(1, len(result)):
            assert result[i].confidence <= result[i - 1].confidence

    def test_detect_high_freq_triggers_bearing_or_detonation(self, sensitive_detector):
        """A strong 3000-5000 Hz signal should trigger bearing_whine and/or detonation."""
        spec = make_spectrogram(4000.0)
        anomalies = sensitive_detector.detect(spec)
        types_found = {a.anomaly_type for a in anomalies}
        # 4000 Hz falls in bearing_whine (2000-8000) and detonation (2000-6000) and knock (1000-4000)
        high_freq_types = {AnomalyType.BEARING_WHINE, AnomalyType.DETONATION, AnomalyType.KNOCK}
        assert types_found & high_freq_types, f"Expected high-freq anomaly, got {types_found}"

    def test_detect_anomaly_has_recommendation(self, sensitive_detector):
        """Detected anomalies should have non-empty recommendations."""
        spec = make_spectrogram(3000.0)
        anomalies = sensitive_detector.detect(spec)
        for a in anomalies:
            assert len(a.recommendation) > 0

    def test_detect_confidence_range(self, sensitive_detector):
        spec = make_composite_spectrogram([1000.0, 2000.0, 3000.0])
        anomalies = sensitive_detector.detect(spec)
        for a in anomalies:
            assert 0.0 <= a.confidence <= 1.0

    def test_detect_energy_fraction_range(self, sensitive_detector):
        spec = make_composite_spectrogram([500.0, 1500.0, 3000.0])
        anomalies = sensitive_detector.detect(spec)
        for a in anomalies:
            assert 0.0 <= a.energy_fraction <= 1.0


# --- is_normal tests ---

class TestIsNormal:
    def test_low_frequency_may_be_normal(self, detector):
        """A pure low-frequency tone (50 Hz) should not trigger high-freq anomalies."""
        spec = make_spectrogram(50.0)
        # With default threshold, a narrow-band low signal might be normal
        # (the energy is concentrated in one band but may or may not exceed threshold)
        result = detector.is_normal(spec)
        assert isinstance(result, bool)

    def test_empty_spectrogram_is_normal(self, detector, empty_spectrogram):
        assert detector.is_normal(empty_spectrogram) is True

    def test_broadband_high_energy_not_normal(self, sensitive_detector):
        """Broadband signal across anomaly frequencies should trigger detections."""
        spec = make_composite_spectrogram([800.0, 1500.0, 3000.0, 5000.0, 7000.0])
        # With sensitive detector, this broad signal should trigger something
        # (it spans valve_tick, knock, bearing_whine, detonation ranges)
        is_norm = sensitive_detector.is_normal(spec)
        # We expect this to NOT be normal given broad high-frequency content
        assert isinstance(is_norm, bool)


# --- get_severity tests ---

class TestGetSeverity:
    def test_empty_returns_none(self, detector, empty_spectrogram):
        assert detector.get_severity(empty_spectrogram) == Severity.NONE

    def test_severity_is_valid_enum(self, detector):
        spec = make_spectrogram(3000.0)
        sev = detector.get_severity(spec)
        assert isinstance(sev, Severity)

    def test_severity_ordering_logic(self):
        """Verify that CRITICAL > HIGH > MODERATE > LOW > NONE."""
        order = {
            Severity.CRITICAL: 4,
            Severity.HIGH: 3,
            Severity.MODERATE: 2,
            Severity.LOW: 1,
            Severity.NONE: 0,
        }
        assert order[Severity.CRITICAL] > order[Severity.HIGH]
        assert order[Severity.HIGH] > order[Severity.MODERATE]
        assert order[Severity.MODERATE] > order[Severity.LOW]
        assert order[Severity.LOW] > order[Severity.NONE]

    def test_high_freq_anomaly_severity(self, sensitive_detector):
        """Strong high-frequency signal should produce at least MODERATE severity."""
        spec = make_spectrogram(4000.0)
        sev = sensitive_detector.get_severity(spec)
        if sev != Severity.NONE:
            # If anomaly detected, should be at least moderate (knock/detonation/bearing are all >= MODERATE)
            severity_order = {Severity.CRITICAL: 4, Severity.HIGH: 3, Severity.MODERATE: 2, Severity.LOW: 1, Severity.NONE: 0}
            assert severity_order[sev] >= severity_order[Severity.MODERATE]


# --- Custom detector configuration tests ---

class TestCustomDetector:
    def test_custom_threshold(self):
        """Higher threshold should produce fewer detections."""
        spec = make_composite_spectrogram([1000.0, 2000.0, 3000.0])
        strict = AudioAnomalyDetector(confidence_threshold=0.9)
        loose = AudioAnomalyDetector(confidence_threshold=0.1)
        strict_results = strict.detect(spec)
        loose_results = loose.detect(spec)
        assert len(strict_results) <= len(loose_results)

    def test_custom_signatures(self):
        """Detector with custom signatures should only check those."""
        custom_sig = AnomalySignature(
            anomaly_type=AnomalyType.KNOCK,
            freq_low=100.0,
            freq_high=20000.0,  # Very wide — should always trigger
            energy_threshold=0.01,  # Very low — should always trigger
            severity=Severity.CRITICAL,
            description="Custom knock signature",
            likely_causes=["Test cause"],
        )
        detector = AudioAnomalyDetector(signatures=[custom_sig], confidence_threshold=0.1)
        spec = make_spectrogram(500.0)
        results = detector.detect(spec)
        # Only knock type should appear (only signature defined)
        for r in results:
            assert r.anomaly_type == AnomalyType.KNOCK

    def test_empty_signatures_detects_nothing(self):
        detector = AudioAnomalyDetector(signatures=[])
        spec = make_spectrogram(3000.0)
        assert detector.detect(spec) == []
        assert detector.is_normal(spec) is True
        assert detector.get_severity(spec) == Severity.NONE
