"""Tests for Phase 98 — Engine Sound Signature Database.

All tests use synthetic audio and the spectrogram analyzer — no real
engine recordings or audio hardware required. Tests verify firing frequency
calculations, signature database lookups, RPM estimation, and profile
matching against known spectral patterns.
"""

import math
import pytest

from motodiag.media.audio_capture import generate_sine_wave, generate_composite_wave
from motodiag.media.spectrogram import SpectrogramAnalyzer, SpectrogramResult
from motodiag.media.sound_signatures import (
    EngineType,
    SoundSignature,
    SignatureMatch,
    SoundSignatureDB,
    SIGNATURES,
    rpm_to_firing_frequency,
    _ENGINE_CYLINDERS,
)


# --- Fixtures ---

@pytest.fixture
def db():
    """Default sound signature database."""
    return SoundSignatureDB()


@pytest.fixture
def analyzer():
    return SpectrogramAnalyzer(window_size=1024)


def make_spectrogram(frequency: float, sample_rate: int = 44100) -> SpectrogramResult:
    """Helper: generate a sine wave and analyze it, returning SpectrogramResult."""
    sample = generate_sine_wave(frequency=frequency, duration=0.5, sample_rate=sample_rate, amplitude=0.8)
    analyzer = SpectrogramAnalyzer(window_size=1024)
    return analyzer.analyze(sample)


def make_composite_spectrogram(frequencies: list[float], sample_rate: int = 44100) -> SpectrogramResult:
    """Helper: generate composite wave and analyze it."""
    sample = generate_composite_wave(frequencies=frequencies, duration=0.5, sample_rate=sample_rate, amplitude=0.3)
    analyzer = SpectrogramAnalyzer(window_size=1024)
    return analyzer.analyze(sample)


# --- EngineType enum tests ---

class TestEngineType:
    def test_all_engine_types_defined(self):
        # Forward-compat: Phase 120 adds brand/powertrain-specific variants.
        # Assert the original 7 are present rather than requiring exact match.
        expected_baseline = {
            "single_cylinder", "v_twin", "parallel_twin", "inline_three",
            "inline_four", "v_four", "boxer_twin",
        }
        actual = {e.value for e in EngineType}
        assert expected_baseline.issubset(actual)

    def test_engine_type_string_value(self):
        assert EngineType.V_TWIN.value == "v_twin"
        assert EngineType.INLINE_FOUR.value == "inline_four"


# --- Firing frequency calculation tests ---

class TestRPMToFiringFrequency:
    def test_single_at_1000rpm(self):
        """Single cylinder at 1000 RPM: (1000/60) * (1/2) = 8.33 Hz."""
        freq = rpm_to_firing_frequency(1000, EngineType.SINGLE_CYLINDER)
        assert abs(freq - 8.333) < 0.01

    def test_vtwin_at_1000rpm(self):
        """V-twin at 1000 RPM: (1000/60) * (2/2) = 16.67 Hz."""
        freq = rpm_to_firing_frequency(1000, EngineType.V_TWIN)
        assert abs(freq - 16.667) < 0.01

    def test_inline4_at_6000rpm(self):
        """Inline-4 at 6000 RPM: (6000/60) * (4/2) = 200 Hz."""
        freq = rpm_to_firing_frequency(6000, EngineType.INLINE_FOUR)
        assert abs(freq - 200.0) < 0.01

    def test_inline3_at_5000rpm(self):
        """Inline-3 at 5000 RPM: (5000/60) * (3/2) = 125 Hz."""
        freq = rpm_to_firing_frequency(5000, EngineType.INLINE_THREE)
        assert abs(freq - 125.0) < 0.01

    def test_zero_rpm(self):
        freq = rpm_to_firing_frequency(0, EngineType.SINGLE_CYLINDER)
        assert freq == 0.0

    def test_all_engine_types_have_cylinder_count(self):
        """Every engine type must have a cylinder count entry."""
        for et in EngineType:
            assert et in _ENGINE_CYLINDERS


# --- Signature database tests ---

class TestSoundSignature:
    def test_all_engine_types_have_signatures(self):
        """Every engine type must have a signature entry."""
        for et in EngineType:
            assert et in SIGNATURES, f"Missing signature for {et.value}"

    def test_signature_fields_populated(self):
        for et, sig in SIGNATURES.items():
            assert sig.engine_type == et
            # Phase 120: ELECTRIC_MOTOR has no idle (0, 0) and 0 cylinders;
            # firing_freq_* fields are reinterpreted as motor whine frequencies.
            # Skip combustion-specific assertions for the electric variant.
            if et == EngineType.ELECTRIC_MOTOR:
                assert sig.cylinders == 0
                assert sig.firing_freq_idle_low > 0  # whine fundamental
                assert sig.firing_freq_5000_low > 0
                assert len(sig.characteristic_sounds) >= 3
                continue
            assert sig.idle_rpm_range[0] < sig.idle_rpm_range[1]
            assert sig.firing_freq_idle_low > 0
            assert sig.firing_freq_idle_high > sig.firing_freq_idle_low
            assert sig.firing_freq_5000_low > 0
            assert sig.firing_freq_5000_high > sig.firing_freq_5000_low
            assert len(sig.expected_harmonics) >= 3
            assert len(sig.characteristic_sounds) >= 3
            assert sig.cylinders > 0

    def test_vtwin_signature_content(self):
        sig = SIGNATURES[EngineType.V_TWIN]
        assert sig.cylinders == 2
        assert sig.idle_rpm_range == (800, 1100)
        # Should mention uneven firing
        has_uneven = any("uneven" in s.lower() for s in sig.characteristic_sounds)
        assert has_uneven, "V-twin signature should mention uneven firing"

    def test_inline4_signature_content(self):
        sig = SIGNATURES[EngineType.INLINE_FOUR]
        assert sig.cylinders == 4
        # Should mention scream or smooth
        has_character = any("scream" in s.lower() or "smooth" in s.lower() for s in sig.characteristic_sounds)
        assert has_character


# --- SoundSignatureDB class tests ---

class TestSoundSignatureDB:
    def test_get_signature_exists(self, db):
        sig = db.get_signature(EngineType.V_TWIN)
        assert sig is not None
        assert sig.engine_type == EngineType.V_TWIN

    def test_get_signature_all_types(self, db):
        for et in EngineType:
            sig = db.get_signature(et)
            assert sig is not None

    def test_get_signature_missing(self):
        """Empty DB should return None."""
        empty_db = SoundSignatureDB(signatures={})
        result = empty_db.get_signature(EngineType.V_TWIN)
        assert result is None

    def test_estimate_rpm_single(self, db):
        """8.33 Hz firing on a single = 1000 RPM."""
        rpm = db.estimate_rpm(8.333, EngineType.SINGLE_CYLINDER)
        assert abs(rpm - 1000.0) < 1.0

    def test_estimate_rpm_inline4(self, db):
        """200 Hz firing on inline-4 = 6000 RPM."""
        rpm = db.estimate_rpm(200.0, EngineType.INLINE_FOUR)
        assert abs(rpm - 6000.0) < 1.0

    def test_estimate_rpm_roundtrip(self, db):
        """RPM → firing_freq → RPM should be identity for combustion engines.

        Phase 120: ELECTRIC_MOTOR is exempted — electric motors have no
        combustion firing frequency; estimate_rpm is combustion-specific.
        """
        for et in EngineType:
            if et == EngineType.ELECTRIC_MOTOR:
                continue
            original_rpm = 3500.0
            freq = rpm_to_firing_frequency(original_rpm, et)
            recovered_rpm = db.estimate_rpm(freq, et)
            assert abs(recovered_rpm - original_rpm) < 0.1, f"Roundtrip failed for {et.value}"


# --- Profile matching tests ---

class TestMatchProfile:
    def test_match_returns_list(self, db):
        spec = make_spectrogram(100.0)
        matches = db.match_profile(spec)
        assert isinstance(matches, list)
        assert len(matches) > 0

    def test_match_sorted_by_confidence(self, db):
        spec = make_spectrogram(100.0)
        matches = db.match_profile(spec)
        for i in range(1, len(matches)):
            assert matches[i].confidence <= matches[i - 1].confidence

    def test_match_top_n_limits(self, db):
        spec = make_spectrogram(100.0)
        matches = db.match_profile(spec, top_n=2)
        assert len(matches) <= 2

    def test_match_empty_spectrogram(self, db):
        empty = SpectrogramResult()
        matches = db.match_profile(empty)
        assert matches == []

    def test_match_has_required_fields(self, db):
        spec = make_spectrogram(100.0)
        matches = db.match_profile(spec)
        for m in matches:
            assert isinstance(m, SignatureMatch)
            assert 0.0 <= m.confidence <= 1.0
            assert isinstance(m.engine_type, EngineType)
            assert isinstance(m.firing_freq_match, bool)
            assert isinstance(m.harmonic_score, float)

    def test_high_freq_favors_bearing_or_knock(self, db):
        """A 3000 Hz tone should NOT match single cylinder idle."""
        spec = make_spectrogram(3000.0)
        matches = db.match_profile(spec, top_n=7)
        # The top match should not be single cylinder (which expects 8-10 Hz at idle)
        if matches:
            top = matches[0]
            # Single cylinder should have low confidence for a 3000 Hz signal
            single_match = next((m for m in matches if m.engine_type == EngineType.SINGLE_CYLINDER), None)
            if single_match:
                assert single_match.confidence < 0.8

    def test_composite_engine_harmonics(self, db):
        """A signal with 100 + 200 + 300 + 400 Hz should match engines with firing freq near 100 Hz."""
        spec = make_composite_spectrogram([100.0, 200.0, 300.0, 400.0])
        matches = db.match_profile(spec, top_n=7)
        assert len(matches) > 0
        # Should have non-zero confidence for at least one type
        assert matches[0].confidence > 0.0
