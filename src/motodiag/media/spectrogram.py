"""Audio spectrogram analysis for motorcycle engine diagnostics.

Phase 97: Computes frequency-domain representations of engine audio using
pure Python DFT (no numpy). Identifies dominant frequency bands relevant
to motorcycle diagnostics — firing frequency, valve train noise, exhaust
note, bearing whine, and knock signatures.

Uses a simplified DFT on a small sample window (first 1024 samples) for
performance. The frequency resolution is sufficient for identifying the
broad spectral characteristics that distinguish healthy engines from
mechanical problems.
"""

import math
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from motodiag.media.audio_capture import AudioSample


class FrequencyBand(BaseModel):
    """A named frequency range relevant to motorcycle engine diagnostics.

    Each band corresponds to a class of mechanical sounds — e.g., valve train
    components oscillate at 500-2000 Hz, while rod knock produces sharp
    impulses in the 1-4 kHz range.
    """
    name: str = Field(description="Identifier: low_rumble, firing_frequency, valve_train, etc.")
    freq_low: float = Field(description="Lower bound of band in Hz")
    freq_high: float = Field(description="Upper bound of band in Hz")
    description: str = Field(default="", description="What mechanical source produces sound in this band")


class SpectrogramResult(BaseModel):
    """Result of spectral analysis on an audio sample.

    Contains the raw frequency/magnitude data plus derived information
    about which frequency bands dominate the signal. The peak frequency
    and dominant bands are the primary diagnostic indicators.
    """
    frequency_bins: list[float] = Field(default_factory=list, description="Frequency values in Hz for each DFT bin")
    magnitude_bins: list[float] = Field(default_factory=list, description="Magnitude (absolute) for each DFT bin")
    peak_frequency: float = Field(default=0.0, description="Frequency with highest magnitude in Hz")
    dominant_bands: list[str] = Field(default_factory=list, description="Names of bands with highest energy")
    duration_analyzed: float = Field(default=0.0, description="Duration of audio actually analyzed in seconds")
    band_energies: dict[str, float] = Field(default_factory=dict, description="Energy per named frequency band")
    sample_rate: int = Field(default=44100, description="Sample rate of analyzed audio")
    window_size: int = Field(default=0, description="Number of samples used in DFT window")


# --- Motorcycle-specific frequency bands ---
# These bands cover the spectral regions where key mechanical sounds appear.
# A healthy engine concentrates energy in firing_frequency and exhaust_note.
# Elevated energy in knock, bearing_whine, or valve_train bands signals trouble.

MOTORCYCLE_FREQUENCY_BANDS: list[FrequencyBand] = [
    FrequencyBand(
        name="low_rumble",
        freq_low=20.0,
        freq_high=100.0,
        description="Low-frequency vibration from engine rotation, frame resonance, "
                    "and exhaust backpressure pulses. Prominent in large V-twins at idle.",
    ),
    FrequencyBand(
        name="firing_frequency",
        freq_low=50.0,
        freq_high=250.0,
        description="Fundamental combustion frequency determined by RPM and cylinder count. "
                    "A single at 3000 RPM fires at 25 Hz; a V-twin at ~50 Hz; an inline-4 at ~100 Hz.",
    ),
    FrequencyBand(
        name="exhaust_note",
        freq_low=200.0,
        freq_high=1000.0,
        description="Harmonics of the firing frequency shaped by exhaust pipe length, "
                    "muffler design, and header configuration. Defines the bike's audible character.",
    ),
    FrequencyBand(
        name="valve_train",
        freq_low=500.0,
        freq_high=2000.0,
        description="Cam chain, rocker arms, valve springs, and lifter impacts. "
                    "Excessive energy here indicates worn cam chain tensioner, loose valve "
                    "clearances, or collapsed hydraulic lifters.",
    ),
    FrequencyBand(
        name="knock",
        freq_low=1000.0,
        freq_high=4000.0,
        description="Metal-on-metal impulse from rod knock, piston slap, or detonation. "
                    "Short-duration broadband spikes periodic with engine rotation.",
    ),
    FrequencyBand(
        name="bearing_whine",
        freq_low=2000.0,
        freq_high=8000.0,
        description="Continuous high-frequency tone from worn bearings — crankshaft main, "
                    "rod, cam, or transmission. Pitch rises linearly with RPM.",
    ),
]

# Build a lookup dict for fast access by name
_BAND_LOOKUP: dict[str, FrequencyBand] = {b.name: b for b in MOTORCYCLE_FREQUENCY_BANDS}


class SpectrogramAnalyzer:
    """Computes frequency-domain analysis of motorcycle engine audio.

    Uses a pure-Python DFT (discrete Fourier transform) rather than FFT.
    For performance, operates on a small window (default 1024 samples)
    rather than the full recording. This gives sufficient frequency
    resolution (~43 Hz at 44100 Hz sample rate) to distinguish the
    motorcycle-relevant frequency bands.

    Typical usage:
        analyzer = SpectrogramAnalyzer()
        result = analyzer.analyze(audio_sample)
        print(result.peak_frequency, result.dominant_bands)
    """

    def __init__(self, window_size: int = 1024, bands: Optional[list[FrequencyBand]] = None):
        """Initialize the analyzer.

        Args:
            window_size: Number of samples to use for DFT. Larger = better
                frequency resolution but slower. 1024 is a good balance.
            bands: Custom frequency bands. Defaults to MOTORCYCLE_FREQUENCY_BANDS.
        """
        self.window_size = window_size
        self.bands = bands if bands is not None else MOTORCYCLE_FREQUENCY_BANDS

    def compute_fft(self, sample: AudioSample) -> tuple[list[float], list[float]]:
        """Compute DFT of an AudioSample using pure Python.

        Takes the first `window_size` samples, applies a Hann window to
        reduce spectral leakage, then computes the DFT via the definition:
            X[k] = sum_{n=0}^{N-1} x[n] * e^{-j*2*pi*k*n/N}

        Only computes bins up to Nyquist (N/2) since the input is real-valued
        and the spectrum is symmetric.

        Args:
            sample: Audio data to analyze.

        Returns:
            Tuple of (frequency_bins, magnitude_bins) where each list has
            N/2 entries. Frequencies are in Hz, magnitudes are absolute values
            normalized by window size.
        """
        if not sample.samples:
            return [], []

        # Take first window_size samples (or all if shorter)
        N = min(self.window_size, len(sample.samples))
        data = sample.samples[:N]

        # Apply Hann window to reduce spectral leakage
        # Hann: w[n] = 0.5 * (1 - cos(2*pi*n / (N-1)))
        windowed = []
        for n in range(N):
            if N > 1:
                w = 0.5 * (1.0 - math.cos(2.0 * math.pi * n / (N - 1)))
            else:
                w = 1.0
            windowed.append(data[n] * w)

        # Compute DFT for bins 0..N/2 (up to Nyquist)
        half_N = N // 2
        freq_resolution = sample.sample_rate / N
        frequency_bins = []
        magnitude_bins = []

        for k in range(half_N):
            real_sum = 0.0
            imag_sum = 0.0
            for n in range(N):
                angle = -2.0 * math.pi * k * n / N
                real_sum += windowed[n] * math.cos(angle)
                imag_sum += windowed[n] * math.sin(angle)

            magnitude = math.sqrt(real_sum * real_sum + imag_sum * imag_sum) / N
            frequency_bins.append(k * freq_resolution)
            magnitude_bins.append(magnitude)

        return frequency_bins, magnitude_bins

    def identify_dominant_bands(
        self,
        frequency_bins: list[float],
        magnitude_bins: list[float],
        top_n: int = 3,
    ) -> tuple[list[str], dict[str, float]]:
        """Identify which motorcycle frequency bands have the highest energy.

        Sums the magnitude of all DFT bins that fall within each band's
        frequency range. Returns the top N bands ranked by total energy.

        Args:
            frequency_bins: Frequencies from compute_fft().
            magnitude_bins: Magnitudes from compute_fft().
            top_n: Number of top bands to return.

        Returns:
            Tuple of (band_names sorted by energy descending, dict of band_name -> energy).
        """
        band_energies: dict[str, float] = {}

        for band in self.bands:
            energy = 0.0
            for freq, mag in zip(frequency_bins, magnitude_bins):
                if band.freq_low <= freq <= band.freq_high:
                    energy += mag * mag  # Sum of squared magnitudes = energy
            band_energies[band.name] = energy

        # Sort by energy descending, take top N
        sorted_bands = sorted(band_energies.keys(), key=lambda b: band_energies[b], reverse=True)
        top_bands = [b for b in sorted_bands[:top_n] if band_energies[b] > 0.0]

        return top_bands, band_energies

    def detect_peak_frequency(
        self,
        frequency_bins: list[float],
        magnitude_bins: list[float],
    ) -> float:
        """Find the single frequency with the highest magnitude.

        Skips the DC component (bin 0) since it represents the signal's
        mean value, not an oscillation.

        Args:
            frequency_bins: Frequencies from compute_fft().
            magnitude_bins: Magnitudes from compute_fft().

        Returns:
            Frequency in Hz of the highest-magnitude bin. 0.0 if no data.
        """
        if len(frequency_bins) < 2 or len(magnitude_bins) < 2:
            return 0.0

        # Skip DC component (index 0)
        max_mag = 0.0
        peak_freq = 0.0
        for i in range(1, len(frequency_bins)):
            if magnitude_bins[i] > max_mag:
                max_mag = magnitude_bins[i]
                peak_freq = frequency_bins[i]

        return peak_freq

    def analyze(self, sample: AudioSample, top_n_bands: int = 3) -> SpectrogramResult:
        """Full spectral analysis pipeline.

        Computes DFT, identifies dominant frequency bands, finds peak frequency,
        and packages everything into a SpectrogramResult.

        Args:
            sample: Audio data to analyze.
            top_n_bands: Number of top frequency bands to report.

        Returns:
            SpectrogramResult with all spectral analysis data.
        """
        if not sample.samples:
            return SpectrogramResult(
                duration_analyzed=0.0,
                sample_rate=sample.sample_rate,
                window_size=0,
            )

        frequency_bins, magnitude_bins = self.compute_fft(sample)
        peak_freq = self.detect_peak_frequency(frequency_bins, magnitude_bins)
        dominant_bands, band_energies = self.identify_dominant_bands(
            frequency_bins, magnitude_bins, top_n=top_n_bands
        )

        actual_window = min(self.window_size, len(sample.samples))
        duration_analyzed = actual_window / sample.sample_rate

        return SpectrogramResult(
            frequency_bins=frequency_bins,
            magnitude_bins=magnitude_bins,
            peak_frequency=peak_freq,
            dominant_bands=dominant_bands,
            duration_analyzed=duration_analyzed,
            band_energies=band_energies,
            sample_rate=sample.sample_rate,
            window_size=actual_window,
        )
