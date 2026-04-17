"""Audio capture and preprocessing for media diagnostics.

Phase 96: Records engine audio (from file or generates test samples),
applies noise reduction, normalizes sample rate and amplitude, segments
into analyzable chunks, and manages audio files on disk.

Uses pure Python (struct, wave, array) — no external audio libraries required.
Designed for phone microphone input in noisy motorcycle shop environments.
"""

import array
import math
import os
import struct
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class AudioConfig(BaseModel):
    """Configuration for audio capture and processing."""
    sample_rate: int = Field(default=44100, description="Samples per second (Hz). 44100 captures all engine frequencies.")
    channels: int = Field(default=1, description="Number of channels. Mono (1) is sufficient for diagnostics.")
    sample_width: int = Field(default=2, description="Bytes per sample. 2 = 16-bit PCM.")
    chunk_duration_sec: float = Field(default=2.0, description="Duration of each analysis chunk in seconds.")
    chunk_overlap_sec: float = Field(default=0.5, description="Overlap between consecutive chunks in seconds.")
    noise_gate_threshold: float = Field(default=0.02, description="Amplitude below this fraction of max is silenced. 0.0-1.0.")
    target_amplitude: float = Field(default=0.8, description="Target peak amplitude after normalization. 0.0-1.0.")


class AudioSample(BaseModel):
    """A single audio recording or segment."""
    samples: list[float] = Field(default_factory=list, description="Audio samples as floats (-1.0 to 1.0)")
    sample_rate: int = Field(default=44100, description="Sample rate in Hz")
    channels: int = Field(default=1, description="Number of channels")
    duration_seconds: float = Field(default=0.0, description="Duration in seconds")
    source: str = Field(default="unknown", description="Source: 'file', 'microphone', 'synthetic'")
    timestamp: Optional[datetime] = Field(default=None, description="When this was recorded")
    metadata: dict = Field(default_factory=dict, description="Additional metadata (make, model, RPM, etc.)")

    model_config = {"arbitrary_types_allowed": True}

    @property
    def sample_count(self) -> int:
        return len(self.samples)

    def get_peak_amplitude(self) -> float:
        """Return the peak absolute amplitude in the sample."""
        if not self.samples:
            return 0.0
        return max(abs(s) for s in self.samples)

    def get_rms_amplitude(self) -> float:
        """Return the RMS (root mean square) amplitude."""
        if not self.samples:
            return 0.0
        sum_squares = sum(s * s for s in self.samples)
        return math.sqrt(sum_squares / len(self.samples))


class AudioPreprocessor:
    """Preprocesses audio for diagnostic analysis.

    Pipeline: normalize_amplitude → apply_noise_gate → resample → segment.
    Each step can be used independently or chained via prepare_for_analysis().
    """

    def __init__(self, config: Optional[AudioConfig] = None):
        self.config = config or AudioConfig()

    def normalize_amplitude(self, sample: AudioSample) -> AudioSample:
        """Scale amplitude so the peak reaches the target level.

        Prevents volume differences between recordings from affecting analysis.
        A recording made with the phone close vs far from the engine should
        produce the same normalized output.
        """
        if not sample.samples:
            return sample

        peak = sample.get_peak_amplitude()
        if peak == 0.0:
            return sample

        scale_factor = self.config.target_amplitude / peak
        normalized = [min(1.0, max(-1.0, s * scale_factor)) for s in sample.samples]

        return AudioSample(
            samples=normalized,
            sample_rate=sample.sample_rate,
            channels=sample.channels,
            duration_seconds=sample.duration_seconds,
            source=sample.source,
            timestamp=sample.timestamp,
            metadata={**sample.metadata, "normalized": True, "scale_factor": scale_factor},
        )

    def apply_noise_gate(self, sample: AudioSample) -> AudioSample:
        """Remove low-level background noise below the threshold.

        In a motorcycle shop, there's constant background noise from compressors,
        fans, and other bikes. The noise gate silences anything below the threshold
        so only the target engine's sound is analyzed.
        """
        if not sample.samples:
            return sample

        threshold = self.config.noise_gate_threshold
        gated = [s if abs(s) >= threshold else 0.0 for s in sample.samples]

        return AudioSample(
            samples=gated,
            sample_rate=sample.sample_rate,
            channels=sample.channels,
            duration_seconds=sample.duration_seconds,
            source=sample.source,
            timestamp=sample.timestamp,
            metadata={**sample.metadata, "noise_gated": True, "gate_threshold": threshold},
        )

    def resample(self, sample: AudioSample, target_rate: Optional[int] = None) -> AudioSample:
        """Convert audio to the target sample rate using linear interpolation.

        Phone microphones may record at different rates (8000, 16000, 44100, 48000).
        Resampling to a consistent rate ensures analysis operates on uniform data.
        """
        target = target_rate or self.config.sample_rate
        if sample.sample_rate == target or not sample.samples:
            return sample

        ratio = target / sample.sample_rate
        new_length = int(len(sample.samples) * ratio)
        resampled = []

        for i in range(new_length):
            src_idx = i / ratio
            idx_low = int(src_idx)
            idx_high = min(idx_low + 1, len(sample.samples) - 1)
            frac = src_idx - idx_low
            value = sample.samples[idx_low] * (1 - frac) + sample.samples[idx_high] * frac
            resampled.append(value)

        return AudioSample(
            samples=resampled,
            sample_rate=target,
            channels=sample.channels,
            duration_seconds=len(resampled) / target,
            source=sample.source,
            timestamp=sample.timestamp,
            metadata={**sample.metadata, "resampled_from": sample.sample_rate, "resampled_to": target},
        )

    def segment(self, sample: AudioSample) -> list[AudioSample]:
        """Split audio into fixed-length overlapping chunks for analysis.

        Each chunk is `chunk_duration_sec` long with `chunk_overlap_sec` overlap.
        This ensures no transient events (misfires, knocks) are split across chunk boundaries.
        """
        if not sample.samples:
            return []

        chunk_samples = int(self.config.chunk_duration_sec * sample.sample_rate)
        overlap_samples = int(self.config.chunk_overlap_sec * sample.sample_rate)
        step = chunk_samples - overlap_samples

        if step <= 0:
            step = chunk_samples  # No overlap if misconfigured

        chunks = []
        for start in range(0, len(sample.samples), step):
            end = start + chunk_samples
            chunk_data = sample.samples[start:end]

            # Skip very short trailing chunks (less than 25% of target)
            if len(chunk_data) < chunk_samples * 0.25:
                continue

            chunks.append(AudioSample(
                samples=chunk_data,
                sample_rate=sample.sample_rate,
                channels=sample.channels,
                duration_seconds=len(chunk_data) / sample.sample_rate,
                source=sample.source,
                timestamp=sample.timestamp,
                metadata={
                    **sample.metadata,
                    "chunk_index": len(chunks),
                    "chunk_start_sec": start / sample.sample_rate,
                },
            ))

        return chunks

    def prepare_for_analysis(self, sample: AudioSample) -> list[AudioSample]:
        """Full preprocessing pipeline: normalize → noise gate → resample → segment.

        Returns a list of preprocessed audio chunks ready for spectrogram analysis.
        """
        # Step 1: Normalize amplitude
        normalized = self.normalize_amplitude(sample)
        # Step 2: Apply noise gate
        gated = self.apply_noise_gate(normalized)
        # Step 3: Resample to target rate
        resampled = self.resample(gated)
        # Step 4: Segment into chunks
        chunks = self.segment(resampled)

        return chunks


class AudioFileManager:
    """Manages audio files on disk — save, load, list recordings."""

    def __init__(self, recordings_dir: Optional[Path] = None):
        from motodiag.core.config import DATA_DIR
        self.recordings_dir = recordings_dir or (DATA_DIR / "recordings")
        self.recordings_dir.mkdir(parents=True, exist_ok=True)

    def save_recording(
        self,
        sample: AudioSample,
        filename: Optional[str] = None,
    ) -> Path:
        """Save an AudioSample to a WAV file.

        Args:
            sample: The audio data to save.
            filename: Optional filename (auto-generated if not provided).

        Returns:
            Path to the saved WAV file.
        """
        if filename is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{ts}.wav"

        filepath = self.recordings_dir / filename

        # Convert float samples (-1.0 to 1.0) to 16-bit PCM integers
        max_val = 32767
        pcm_data = array.array('h', [int(max(min(s, 1.0), -1.0) * max_val) for s in sample.samples])

        with wave.open(str(filepath), 'w') as wf:
            wf.setnchannels(sample.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample.sample_rate)
            wf.writeframes(pcm_data.tobytes())

        return filepath

    def load_recording(self, filepath: Path) -> AudioSample:
        """Load a WAV file into an AudioSample."""
        with wave.open(str(filepath), 'r') as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            sample_rate = wf.getframerate()
            n_frames = wf.getnframes()
            raw_data = wf.readframes(n_frames)

        # Convert 16-bit PCM to float (-1.0 to 1.0)
        max_val = 32767.0
        if sample_width == 2:
            pcm_data = struct.unpack(f'<{n_frames * channels}h', raw_data)
            samples = [s / max_val for s in pcm_data]
        else:
            samples = [0.0]  # Unsupported sample width

        return AudioSample(
            samples=samples,
            sample_rate=sample_rate,
            channels=channels,
            duration_seconds=n_frames / sample_rate,
            source="file",
            metadata={"filepath": str(filepath)},
        )

    def list_recordings(self) -> list[dict]:
        """List all WAV recordings in the recordings directory."""
        recordings = []
        for f in sorted(self.recordings_dir.glob("*.wav")):
            try:
                with wave.open(str(f), 'r') as wf:
                    recordings.append({
                        "filename": f.name,
                        "filepath": str(f),
                        "duration_seconds": wf.getnframes() / wf.getframerate(),
                        "sample_rate": wf.getframerate(),
                        "channels": wf.getnchannels(),
                    })
            except wave.Error:
                continue  # Skip corrupted files
        return recordings


# --- Synthetic audio generation for testing ---

def generate_sine_wave(
    frequency: float = 440.0,
    duration: float = 1.0,
    sample_rate: int = 44100,
    amplitude: float = 0.5,
) -> AudioSample:
    """Generate a synthetic sine wave for testing.

    Args:
        frequency: Frequency in Hz (440 = A4 note, 100-200 = motorcycle idle).
        duration: Duration in seconds.
        sample_rate: Samples per second.
        amplitude: Peak amplitude (0.0 to 1.0).

    Returns:
        AudioSample with the generated sine wave.
    """
    n_samples = int(duration * sample_rate)
    samples = [
        amplitude * math.sin(2 * math.pi * frequency * i / sample_rate)
        for i in range(n_samples)
    ]
    return AudioSample(
        samples=samples,
        sample_rate=sample_rate,
        channels=1,
        duration_seconds=duration,
        source="synthetic",
        timestamp=datetime.now(timezone.utc),
        metadata={"frequency_hz": frequency, "amplitude": amplitude},
    )


def generate_composite_wave(
    frequencies: list[float],
    duration: float = 1.0,
    sample_rate: int = 44100,
    amplitude: float = 0.3,
) -> AudioSample:
    """Generate a composite wave from multiple frequencies (simulates engine harmonics).

    A running motorcycle engine produces a fundamental frequency plus harmonics.
    For example, a single-cylinder at 3000 RPM fires at 25 Hz fundamental,
    with harmonics at 50 Hz, 75 Hz, 100 Hz, etc.

    Args:
        frequencies: List of frequencies to combine.
        duration: Duration in seconds.
        sample_rate: Samples per second.
        amplitude: Per-frequency amplitude (0.0 to 1.0).

    Returns:
        AudioSample with the combined waveform.
    """
    n_samples = int(duration * sample_rate)
    samples = [0.0] * n_samples
    for freq in frequencies:
        for i in range(n_samples):
            samples[i] += amplitude * math.sin(2 * math.pi * freq * i / sample_rate)

    # Normalize to prevent clipping
    peak = max(abs(s) for s in samples) if samples else 1.0
    if peak > 1.0:
        samples = [s / peak for s in samples]

    return AudioSample(
        samples=samples,
        sample_rate=sample_rate,
        channels=1,
        duration_seconds=duration,
        source="synthetic",
        timestamp=datetime.now(timezone.utc),
        metadata={"frequencies_hz": frequencies, "amplitude": amplitude},
    )
