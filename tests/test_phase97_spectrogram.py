"""Tests for Phase 97 — Audio Spectrogram Analysis.

All tests use synthetic audio data — no audio hardware required.
Tests verify DFT computation, frequency band identification, peak detection,
and the full analysis pipeline using generated sine and composite waves.
"""

import math
import pytest

from motodiag.media.audio_capture import (
    AudioSample,
    AudioConfig,
    generate_sine_wave,
    generate_composite_wave,
)
from motodiag.media.spectrogram import (
    FrequencyBand,
    SpectrogramResult,
    SpectrogramAnalyzer,
    MOTORCYCLE_FREQUENCY_BANDS,
    _BAND_LOOKUP,
)


# --- Fixtures ---

@pytest.fixture
def analyzer():
    """Default spectrogram analyzer with 1024-sample window."""
    return SpectrogramAnalyzer(window_size=1024)


@pytest.fixture
def small_analyzer():
    """Analyzer with smaller window for fast tests."""
    return SpectrogramAnalyzer(window_size=256)


@pytest.fixture
def sine_440():
    """440 Hz sine wave, 1 second at 44100 Hz."""
    return generate_sine_wave(frequency=440.0, duration=1.0, sample_rate=44100, amplitude=0.8)


@pytest.fixture
def sine_100():
    """100 Hz sine wave — firing frequency range."""
    return generate_sine_wave(frequency=100.0, duration=1.0, sample_rate=44100, amplitude=0.8)


@pytest.fixture
def sine_3000():
    """3000 Hz sine wave — knock/bearing whine range."""
    return generate_sine_wave(frequency=3000.0, duration=1.0, sample_rate=44100, amplitude=0.8)


@pytest.fixture
def composite_engine():
    """Composite wave simulating engine harmonics: 100 Hz fundamental + 200, 300, 400 Hz harmonics."""
    return generate_composite_wave(
        frequencies=[100.0, 200.0, 300.0, 400.0],
        duration=1.0,
        sample_rate=44100,
        amplitude=0.3,
    )


@pytest.fixture
def empty_sample():
    """Empty audio sample."""
    return AudioSample(samples=[], sample_rate=44100, channels=1, duration_seconds=0.0)


@pytest.fixture
def short_sample():
    """Very short sample — fewer samples than default window size."""
    return generate_sine_wave(frequency=440.0, duration=0.005, sample_rate=44100, amplitude=0.5)


# --- FrequencyBand model tests ---

class TestFrequencyBand:
    def test_create_band(self):
        band = FrequencyBand(name="test_band", freq_low=100.0, freq_high=500.0, description="Test")
        assert band.name == "test_band"
        assert band.freq_low == 100.0
        assert band.freq_high == 500.0

    def test_motorcycle_bands_defined(self):
        """All 6 motorcycle frequency bands must be defined."""
        assert len(MOTORCYCLE_FREQUENCY_BANDS) == 6
        expected_names = {"low_rumble", "firing_frequency", "exhaust_note", "valve_train", "knock", "bearing_whine"}
        actual_names = {b.name for b in MOTORCYCLE_FREQUENCY_BANDS}
        assert actual_names == expected_names

    def test_band_lookup_dict(self):
        """Lookup dict maps names to FrequencyBand objects."""
        assert "low_rumble" in _BAND_LOOKUP
        assert _BAND_LOOKUP["low_rumble"].freq_low == 20.0
        assert _BAND_LOOKUP["bearing_whine"].freq_high == 8000.0


# --- SpectrogramResult model tests ---

class TestSpectrogramResult:
    def test_default_result(self):
        result = SpectrogramResult()
        assert result.frequency_bins == []
        assert result.magnitude_bins == []
        assert result.peak_frequency == 0.0
        assert result.dominant_bands == []
        assert result.duration_analyzed == 0.0

    def test_result_with_data(self):
        result = SpectrogramResult(
            frequency_bins=[0.0, 43.0, 86.0],
            magnitude_bins=[0.01, 0.5, 0.1],
            peak_frequency=43.0,
            dominant_bands=["firing_frequency"],
            duration_analyzed=0.023,
            band_energies={"firing_frequency": 0.25},
        )
        assert result.peak_frequency == 43.0
        assert "firing_frequency" in result.dominant_bands


# --- DFT computation tests ---

class TestComputeFFT:
    def test_fft_returns_frequency_and_magnitude(self, analyzer, sine_440):
        freqs, mags = analyzer.compute_fft(sine_440)
        assert len(freqs) > 0
        assert len(mags) > 0
        assert len(freqs) == len(mags)

    def test_fft_empty_sample(self, analyzer, empty_sample):
        freqs, mags = analyzer.compute_fft(empty_sample)
        assert freqs == []
        assert mags == []

    def test_fft_peak_near_input_frequency(self, analyzer, sine_440):
        """DFT of a 440 Hz sine wave should have its peak near 440 Hz."""
        freqs, mags = analyzer.compute_fft(sine_440)
        # Find peak (skip DC)
        max_idx = max(range(1, len(mags)), key=lambda i: mags[i])
        peak_freq = freqs[max_idx]
        # Tolerance: frequency resolution = 44100/1024 ≈ 43 Hz
        assert abs(peak_freq - 440.0) < 50.0, f"Peak at {peak_freq}, expected near 440"

    def test_fft_peak_near_100hz(self, analyzer, sine_100):
        """DFT of a 100 Hz sine wave should peak near 100 Hz."""
        freqs, mags = analyzer.compute_fft(sine_100)
        max_idx = max(range(1, len(mags)), key=lambda i: mags[i])
        peak_freq = freqs[max_idx]
        assert abs(peak_freq - 100.0) < 50.0, f"Peak at {peak_freq}, expected near 100"

    def test_fft_output_length(self, analyzer, sine_440):
        """Output length should be window_size / 2."""
        freqs, mags = analyzer.compute_fft(sine_440)
        assert len(freqs) == 1024 // 2

    def test_fft_short_sample(self, small_analyzer, short_sample):
        """Should handle samples shorter than window size."""
        freqs, mags = small_analyzer.compute_fft(short_sample)
        assert len(freqs) > 0
        # Length should be actual_samples / 2, not window_size / 2
        actual_n = min(256, len(short_sample.samples))
        assert len(freqs) == actual_n // 2

    def test_fft_frequencies_ascending(self, analyzer, sine_440):
        """Frequency bins should be monotonically increasing."""
        freqs, _ = analyzer.compute_fft(sine_440)
        for i in range(1, len(freqs)):
            assert freqs[i] > freqs[i - 1]

    def test_fft_magnitudes_non_negative(self, analyzer, sine_440):
        """All magnitudes should be non-negative."""
        _, mags = analyzer.compute_fft(sine_440)
        assert all(m >= 0 for m in mags)


# --- Peak frequency detection tests ---

class TestDetectPeakFrequency:
    def test_peak_of_440hz_sine(self, analyzer, sine_440):
        freqs, mags = analyzer.compute_fft(sine_440)
        peak = analyzer.detect_peak_frequency(freqs, mags)
        assert abs(peak - 440.0) < 50.0

    def test_peak_of_3000hz_sine(self, analyzer, sine_3000):
        freqs, mags = analyzer.compute_fft(sine_3000)
        peak = analyzer.detect_peak_frequency(freqs, mags)
        assert abs(peak - 3000.0) < 50.0

    def test_peak_empty_data(self, analyzer):
        assert analyzer.detect_peak_frequency([], []) == 0.0

    def test_peak_single_bin(self, analyzer):
        """Single bin should return 0.0 (not enough data)."""
        assert analyzer.detect_peak_frequency([0.0], [1.0]) == 0.0


# --- Dominant band identification tests ---

class TestIdentifyDominantBands:
    def test_100hz_in_firing_frequency_band(self, analyzer, sine_100):
        """100 Hz tone should put energy in the firing_frequency band (50-250 Hz)."""
        freqs, mags = analyzer.compute_fft(sine_100)
        bands, energies = analyzer.identify_dominant_bands(freqs, mags)
        assert "firing_frequency" in bands

    def test_3000hz_in_knock_or_bearing(self, analyzer, sine_3000):
        """3000 Hz tone should activate knock (1000-4000 Hz) and/or bearing_whine (2000-8000 Hz)."""
        freqs, mags = analyzer.compute_fft(sine_3000)
        bands, energies = analyzer.identify_dominant_bands(freqs, mags)
        assert "knock" in bands or "bearing_whine" in bands

    def test_top_n_limits_results(self, analyzer, composite_engine):
        freqs, mags = analyzer.compute_fft(composite_engine)
        bands_2, _ = analyzer.identify_dominant_bands(freqs, mags, top_n=2)
        assert len(bands_2) <= 2

    def test_empty_returns_empty(self, analyzer):
        bands, energies = analyzer.identify_dominant_bands([], [])
        assert bands == []
        # With empty input, all bands have zero energy
        assert all(v == 0.0 for v in energies.values())

    def test_energies_dict_has_all_bands(self, analyzer, sine_440):
        freqs, mags = analyzer.compute_fft(sine_440)
        _, energies = analyzer.identify_dominant_bands(freqs, mags)
        for band in MOTORCYCLE_FREQUENCY_BANDS:
            assert band.name in energies


# --- Full analysis pipeline tests ---

class TestAnalyze:
    def test_analyze_returns_spectrogram_result(self, analyzer, sine_440):
        result = analyzer.analyze(sine_440)
        assert isinstance(result, SpectrogramResult)
        assert result.peak_frequency > 0
        assert len(result.frequency_bins) > 0
        assert len(result.dominant_bands) > 0

    def test_analyze_empty_sample(self, analyzer, empty_sample):
        result = analyzer.analyze(empty_sample)
        assert result.peak_frequency == 0.0
        assert result.frequency_bins == []
        assert result.duration_analyzed == 0.0

    def test_analyze_duration(self, analyzer, sine_440):
        result = analyzer.analyze(sine_440)
        expected_duration = 1024 / 44100
        assert abs(result.duration_analyzed - expected_duration) < 0.001

    def test_analyze_composite_engine_sound(self, analyzer, composite_engine):
        """Composite engine harmonics should produce meaningful spectral results."""
        result = analyzer.analyze(composite_engine)
        assert result.peak_frequency > 0
        assert len(result.dominant_bands) > 0
        assert result.band_energies  # Should have band energy data
        # The 100 Hz fundamental should land in firing_frequency band
        assert result.band_energies.get("firing_frequency", 0.0) > 0

    def test_analyze_window_size_recorded(self, analyzer, sine_440):
        result = analyzer.analyze(sine_440)
        assert result.window_size == 1024

    def test_analyze_sample_rate_recorded(self, analyzer, sine_440):
        result = analyzer.analyze(sine_440)
        assert result.sample_rate == 44100

    def test_custom_window_size(self, sine_440):
        analyzer = SpectrogramAnalyzer(window_size=512)
        result = analyzer.analyze(sine_440)
        assert result.window_size == 512
        assert len(result.frequency_bins) == 256  # N/2

    def test_custom_bands(self, sine_440):
        custom_bands = [FrequencyBand(name="custom", freq_low=400.0, freq_high=500.0)]
        analyzer = SpectrogramAnalyzer(window_size=1024, bands=custom_bands)
        result = analyzer.analyze(sine_440)
        assert "custom" in result.band_energies
        assert result.band_energies["custom"] > 0
