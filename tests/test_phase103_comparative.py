"""Phase 103 — Comparative audio analysis tests.

Tests FrequencyPeak, SpectrogramData, analyze_frequencies, FrequencyChange,
ComparisonResult, ComparativeAnalyzer (compare, identify_changes,
score_improvement), and diagnostic hint mapping.

All tests use synthetic audio — no real recordings required.
"""

import math

import pytest

from motodiag.media.audio_capture import AudioSample, generate_sine_wave, generate_composite_wave
from motodiag.media.comparative import (
    FrequencyPeak,
    SpectrogramData,
    FrequencyChange,
    ComparisonResult,
    ComparativeAnalyzer,
    analyze_frequencies,
)


# --- Helpers ---


def _make_sample(
    frequencies: list[float] | None = None,
    duration: float = 0.5,
    sample_rate: int = 8000,
    amplitude: float = 0.5,
) -> AudioSample:
    """Create a synthetic AudioSample for testing."""
    if frequencies is None:
        frequencies = [440.0]
    if len(frequencies) == 1:
        return generate_sine_wave(
            frequency=frequencies[0],
            duration=duration,
            sample_rate=sample_rate,
            amplitude=amplitude,
        )
    return generate_composite_wave(
        frequencies=frequencies,
        duration=duration,
        sample_rate=sample_rate,
        amplitude=amplitude,
    )


def _make_spectrum(
    peaks: list[tuple[float, float]] | None = None,
    dominant: float = 0.0,
    total_energy: float = 1.0,
    noise_floor: float = 0.01,
) -> SpectrogramData:
    """Create a SpectrogramData for testing."""
    freq_peaks = []
    if peaks:
        for freq, amp in peaks:
            freq_peaks.append(FrequencyPeak(frequency_hz=freq, amplitude=amp))
    return SpectrogramData(
        peaks=freq_peaks,
        dominant_frequency_hz=dominant or (freq_peaks[0].frequency_hz if freq_peaks else 0.0),
        total_energy=total_energy,
        noise_floor=noise_floor,
    )


# --- FrequencyPeak ---


class TestFrequencyPeak:
    def test_low_frequency(self):
        peak = FrequencyPeak(frequency_hz=100.0, amplitude=0.5)
        assert peak.is_low_frequency
        assert not peak.is_mid_frequency
        assert not peak.is_high_frequency

    def test_mid_frequency(self):
        peak = FrequencyPeak(frequency_hz=500.0, amplitude=0.3)
        assert not peak.is_low_frequency
        assert peak.is_mid_frequency
        assert not peak.is_high_frequency

    def test_high_frequency(self):
        peak = FrequencyPeak(frequency_hz=5000.0, amplitude=0.1)
        assert not peak.is_low_frequency
        assert not peak.is_mid_frequency
        assert peak.is_high_frequency

    def test_boundary_200hz(self):
        peak = FrequencyPeak(frequency_hz=200.0, amplitude=0.3)
        assert peak.is_mid_frequency

    def test_boundary_2000hz(self):
        peak = FrequencyPeak(frequency_hz=2000.0, amplitude=0.3)
        assert peak.is_high_frequency


# --- SpectrogramData ---


class TestSpectrogramData:
    def test_empty_spectrum(self):
        spec = SpectrogramData()
        assert spec.peak_count == 0
        assert spec.snr == 0.0

    def test_peak_count(self):
        spec = _make_spectrum(peaks=[(100, 0.5), (200, 0.3)])
        assert spec.peak_count == 2

    def test_snr_calculation(self):
        spec = _make_spectrum(peaks=[(100, 1.0)], noise_floor=0.1)
        assert abs(spec.snr - 10.0) < 0.001

    def test_snr_zero_noise(self):
        spec = _make_spectrum(peaks=[(100, 1.0)], noise_floor=0.0, dominant=100.0)
        assert spec.snr == float("inf")


# --- analyze_frequencies ---


class TestAnalyzeFrequencies:
    def test_empty_sample(self):
        sample = AudioSample()
        result = analyze_frequencies(sample)
        assert result.peak_count == 0

    def test_single_frequency(self):
        sample = _make_sample(frequencies=[440.0], duration=0.5, sample_rate=8000)
        result = analyze_frequencies(sample, num_peaks=5)
        # Should find a peak near 440 Hz
        assert result.peak_count > 0
        # Dominant frequency should be close to 440 Hz
        assert abs(result.dominant_frequency_hz - 440.0) < 50.0

    def test_total_energy_positive(self):
        sample = _make_sample(frequencies=[200.0])
        result = analyze_frequencies(sample)
        assert result.total_energy > 0

    def test_noise_floor_less_than_dominant(self):
        sample = _make_sample(frequencies=[500.0], amplitude=0.8)
        result = analyze_frequencies(sample)
        if result.peaks:
            assert result.noise_floor < result.peaks[0].amplitude

    def test_very_short_sample(self):
        sample = AudioSample(samples=[0.5], sample_rate=8000, duration_seconds=1 / 8000)
        result = analyze_frequencies(sample)
        assert result.peak_count == 0  # Too short for meaningful analysis


# --- ComparisonResult ---


class TestComparisonResult:
    def test_improved(self):
        result = ComparisonResult(improvement_score=0.5)
        assert result.improved
        assert not result.worsened
        assert not result.unchanged

    def test_worsened(self):
        result = ComparisonResult(improvement_score=-0.5)
        assert result.worsened
        assert not result.improved

    def test_unchanged(self):
        result = ComparisonResult(improvement_score=0.02)
        assert result.unchanged

    def test_unchanged_boundary(self):
        result = ComparisonResult(improvement_score=0.05)
        assert not result.unchanged  # 0.05 is at the boundary (not < 0.05)


# --- ComparativeAnalyzer: identify_changes ---


class TestIdentifyChanges:
    def test_no_changes_identical_spectra(self):
        spec = _make_spectrum(peaks=[(100, 0.5), (200, 0.3)])
        analyzer = ComparativeAnalyzer()
        changes = analyzer.identify_changes(spec, spec)
        assert len(changes) == 0

    def test_new_peak_detected(self):
        baseline = _make_spectrum(peaks=[(100, 0.5)])
        current = _make_spectrum(peaks=[(100, 0.5), (500, 0.4)])
        analyzer = ComparativeAnalyzer()
        changes = analyzer.identify_changes(baseline, current)
        new_peaks = [c for c in changes if c.change_type == "new_peak"]
        assert len(new_peaks) == 1
        assert abs(new_peaks[0].frequency_hz - 500) < 1

    def test_disappeared_peak_detected(self):
        baseline = _make_spectrum(peaks=[(100, 0.5), (500, 0.4)])
        current = _make_spectrum(peaks=[(100, 0.5)])
        analyzer = ComparativeAnalyzer()
        changes = analyzer.identify_changes(baseline, current)
        disappeared = [c for c in changes if c.change_type == "disappeared_peak"]
        assert len(disappeared) == 1
        assert abs(disappeared[0].frequency_hz - 500) < 1

    def test_amplitude_increase(self):
        baseline = _make_spectrum(peaks=[(100, 0.3)])
        current = _make_spectrum(peaks=[(100, 0.6)])
        analyzer = ComparativeAnalyzer(amplitude_change_threshold=0.3)
        changes = analyzer.identify_changes(baseline, current)
        increases = [c for c in changes if c.change_type == "amplitude_increase"]
        assert len(increases) == 1

    def test_amplitude_decrease(self):
        baseline = _make_spectrum(peaks=[(100, 0.6)])
        current = _make_spectrum(peaks=[(100, 0.3)])
        analyzer = ComparativeAnalyzer(amplitude_change_threshold=0.3)
        changes = analyzer.identify_changes(baseline, current)
        decreases = [c for c in changes if c.change_type == "amplitude_decrease"]
        assert len(decreases) == 1

    def test_small_amplitude_change_ignored(self):
        baseline = _make_spectrum(peaks=[(100, 0.50)])
        current = _make_spectrum(peaks=[(100, 0.55)])
        analyzer = ComparativeAnalyzer(amplitude_change_threshold=0.3)
        changes = analyzer.identify_changes(baseline, current)
        assert len(changes) == 0  # 10% change < 30% threshold

    def test_frequency_tolerance_matching(self):
        """Peaks within tolerance are matched, not treated as new/disappeared."""
        baseline = _make_spectrum(peaks=[(100, 0.5)])
        current = _make_spectrum(peaks=[(108, 0.5)])  # 8 Hz off (within 15 Hz tolerance)
        analyzer = ComparativeAnalyzer(frequency_tolerance_hz=15.0)
        changes = analyzer.identify_changes(baseline, current)
        # Should match, not treat as new + disappeared
        new_peaks = [c for c in changes if c.change_type == "new_peak"]
        disappeared = [c for c in changes if c.change_type == "disappeared_peak"]
        assert len(new_peaks) == 0
        assert len(disappeared) == 0

    def test_diagnostic_hints_populated(self):
        baseline = _make_spectrum(peaks=[(100, 0.5)])
        current = _make_spectrum(peaks=[(100, 0.5), (3000, 0.3)])
        analyzer = ComparativeAnalyzer()
        changes = analyzer.identify_changes(baseline, current)
        new_peaks = [c for c in changes if c.change_type == "new_peak"]
        assert len(new_peaks) == 1
        assert len(new_peaks[0].diagnostic_hint) > 0
        assert "high" in new_peaks[0].diagnostic_hint.lower()  # 3000 Hz = high freq


# --- ComparativeAnalyzer: score_improvement ---


class TestScoreImprovement:
    def test_no_changes_zero_score(self):
        analyzer = ComparativeAnalyzer()
        spec = _make_spectrum(peaks=[(100, 0.5)])
        score = analyzer.score_improvement([], 0.0, spec, spec)
        assert score == 0.0

    def test_resolved_peak_positive_score(self):
        analyzer = ComparativeAnalyzer()
        changes = [FrequencyChange(
            frequency_hz=500,
            baseline_amplitude=0.5,
            current_amplitude=0.0,
            change_type="disappeared_peak",
            change_magnitude=-1.0,
        )]
        spec = _make_spectrum()
        score = analyzer.score_improvement(changes, 0.0, spec, spec)
        assert score > 0.0

    def test_new_peak_negative_score(self):
        analyzer = ComparativeAnalyzer()
        changes = [FrequencyChange(
            frequency_hz=500,
            baseline_amplitude=0.0,
            current_amplitude=0.5,
            change_type="new_peak",
            change_magnitude=1.0,
        )]
        spec = _make_spectrum()
        score = analyzer.score_improvement(changes, 0.0, spec, spec)
        assert score < 0.0

    def test_score_bounded_minus_one_to_one(self):
        analyzer = ComparativeAnalyzer()
        many_new = [
            FrequencyChange(frequency_hz=i * 100, change_type="new_peak", change_magnitude=1.0)
            for i in range(1, 20)
        ]
        spec = _make_spectrum()
        score = analyzer.score_improvement(many_new, 50.0, spec, spec)
        assert -1.0 <= score <= 1.0


# --- ComparativeAnalyzer: compare ---


class TestCompare:
    def test_compare_identical_samples(self):
        sample = _make_sample(frequencies=[440.0], duration=0.2, sample_rate=4000)
        analyzer = ComparativeAnalyzer()
        result = analyzer.compare(sample, sample)
        assert abs(result.improvement_score) < 0.1
        assert len(result.new_anomalies) == 0
        assert len(result.resolved_anomalies) == 0

    def test_compare_with_precomputed_spectra(self):
        baseline = _make_sample(frequencies=[440.0], duration=0.1, sample_rate=4000)
        current = _make_sample(frequencies=[440.0], duration=0.1, sample_rate=4000)
        baseline_spec = _make_spectrum(peaks=[(440, 0.5)])
        current_spec = _make_spectrum(peaks=[(440, 0.5), (2000, 0.3)])

        analyzer = ComparativeAnalyzer()
        result = analyzer.compare(
            baseline, current,
            baseline_spectrum=baseline_spec,
            current_spectrum=current_spec,
        )
        assert len(result.new_anomalies) == 1
        assert result.improvement_score < 0  # New peak = worse

    def test_compare_resolved_anomaly(self):
        baseline = _make_sample(frequencies=[440.0], duration=0.1, sample_rate=4000)
        current = _make_sample(frequencies=[440.0], duration=0.1, sample_rate=4000)
        baseline_spec = _make_spectrum(peaks=[(440, 0.5), (2000, 0.3)])
        current_spec = _make_spectrum(peaks=[(440, 0.5)])

        analyzer = ComparativeAnalyzer()
        result = analyzer.compare(
            baseline, current,
            baseline_spectrum=baseline_spec,
            current_spectrum=current_spec,
        )
        assert len(result.resolved_anomalies) == 1
        assert result.improvement_score > 0  # Resolved peak = better

    def test_compare_energy_change_calculated(self):
        baseline = _make_sample(frequencies=[440.0], duration=0.1, sample_rate=4000)
        current = _make_sample(frequencies=[440.0], duration=0.1, sample_rate=4000)
        baseline_spec = _make_spectrum(peaks=[(440, 0.5)], total_energy=1.0)
        current_spec = _make_spectrum(peaks=[(440, 0.5)], total_energy=0.5)

        analyzer = ComparativeAnalyzer()
        result = analyzer.compare(
            baseline, current,
            baseline_spectrum=baseline_spec,
            current_spectrum=current_spec,
        )
        assert result.energy_change_percent == -50.0

    def test_compare_dominant_frequency_shift(self):
        baseline = _make_sample(frequencies=[440.0], duration=0.1, sample_rate=4000)
        current = _make_sample(frequencies=[440.0], duration=0.1, sample_rate=4000)
        baseline_spec = _make_spectrum(peaks=[(440, 0.5)], dominant=440.0)
        current_spec = _make_spectrum(peaks=[(460, 0.5)], dominant=460.0)

        analyzer = ComparativeAnalyzer()
        result = analyzer.compare(
            baseline, current,
            baseline_spectrum=baseline_spec,
            current_spectrum=current_spec,
        )
        assert abs(result.dominant_frequency_shift_hz - 20.0) < 0.1

    def test_compare_summaries_populated(self):
        baseline = _make_sample(frequencies=[440.0], duration=0.1, sample_rate=4000)
        current = _make_sample(frequencies=[440.0], duration=0.1, sample_rate=4000)
        baseline_spec = _make_spectrum(peaks=[(440, 0.5)], dominant=440.0)
        current_spec = _make_spectrum(peaks=[(440, 0.5)], dominant=440.0)

        analyzer = ComparativeAnalyzer()
        result = analyzer.compare(
            baseline, current,
            baseline_spectrum=baseline_spec,
            current_spectrum=current_spec,
        )
        assert "Baseline" in result.baseline_summary
        assert "Current" in result.current_summary

    def test_compare_differences_list_populated(self):
        baseline = _make_sample(frequencies=[440.0], duration=0.1, sample_rate=4000)
        current = _make_sample(frequencies=[440.0], duration=0.1, sample_rate=4000)
        baseline_spec = _make_spectrum(peaks=[(440, 0.5)])
        current_spec = _make_spectrum(peaks=[(440, 0.5), (3000, 0.4)])

        analyzer = ComparativeAnalyzer()
        result = analyzer.compare(
            baseline, current,
            baseline_spectrum=baseline_spec,
            current_spectrum=current_spec,
        )
        assert len(result.differences) > 0
        assert any("3000" in d for d in result.differences)
