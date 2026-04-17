"""Phase 96 — Audio capture + preprocessing tests.

Tests AudioConfig, AudioSample, AudioPreprocessor pipeline,
AudioFileManager (save/load WAV), and synthetic audio generation.
All tests use synthetic waveforms — no audio hardware required.
"""

import math
import pytest
from pathlib import Path

from motodiag.media.audio_capture import (
    AudioConfig,
    AudioSample,
    AudioPreprocessor,
    AudioFileManager,
    generate_sine_wave,
    generate_composite_wave,
)


# --- AudioConfig ---


class TestAudioConfig:
    def test_default_config(self):
        config = AudioConfig()
        assert config.sample_rate == 44100
        assert config.channels == 1
        assert config.sample_width == 2
        assert config.chunk_duration_sec == 2.0

    def test_custom_config(self):
        config = AudioConfig(sample_rate=22050, noise_gate_threshold=0.05)
        assert config.sample_rate == 22050
        assert config.noise_gate_threshold == 0.05


# --- AudioSample ---


class TestAudioSample:
    def test_empty_sample(self):
        sample = AudioSample()
        assert sample.sample_count == 0
        assert sample.get_peak_amplitude() == 0.0
        assert sample.get_rms_amplitude() == 0.0

    def test_sample_with_data(self):
        sample = AudioSample(
            samples=[0.0, 0.5, 1.0, -1.0, 0.0],
            sample_rate=44100,
            channels=1,
            duration_seconds=5 / 44100,
        )
        assert sample.sample_count == 5
        assert sample.get_peak_amplitude() == 1.0

    def test_rms_amplitude(self):
        # Sine wave at amplitude 1.0 has RMS of ~0.707
        sample = generate_sine_wave(frequency=440, duration=1.0, amplitude=1.0)
        rms = sample.get_rms_amplitude()
        assert 0.65 < rms < 0.75  # RMS of sine ≈ 0.707

    def test_metadata(self):
        sample = AudioSample(
            samples=[0.0],
            metadata={"make": "Honda", "model": "CBR600RR", "rpm": 3000},
        )
        assert sample.metadata["make"] == "Honda"
        assert sample.metadata["rpm"] == 3000


# --- Synthetic audio generation ---


class TestSineWaveGeneration:
    def test_correct_duration(self):
        sample = generate_sine_wave(duration=2.0, sample_rate=44100)
        assert sample.sample_count == 88200
        assert abs(sample.duration_seconds - 2.0) < 0.01

    def test_correct_amplitude(self):
        sample = generate_sine_wave(amplitude=0.5)
        peak = sample.get_peak_amplitude()
        assert 0.48 < peak < 0.52  # Close to 0.5

    def test_source_is_synthetic(self):
        sample = generate_sine_wave()
        assert sample.source == "synthetic"

    def test_metadata_includes_frequency(self):
        sample = generate_sine_wave(frequency=1000)
        assert sample.metadata["frequency_hz"] == 1000


class TestCompositeWaveGeneration:
    def test_multiple_frequencies(self):
        sample = generate_composite_wave(frequencies=[100, 200, 300], duration=1.0)
        assert sample.sample_count == 44100
        assert sample.get_peak_amplitude() <= 1.0  # Normalized

    def test_metadata_includes_frequencies(self):
        freqs = [50, 100, 150]
        sample = generate_composite_wave(frequencies=freqs)
        assert sample.metadata["frequencies_hz"] == freqs

    def test_empty_frequencies(self):
        sample = generate_composite_wave(frequencies=[], duration=1.0)
        assert sample.sample_count == 44100
        assert sample.get_peak_amplitude() == 0.0  # All silence


# --- AudioPreprocessor ---


class TestNormalizeAmplitude:
    def test_normalize_quiet_signal(self):
        """A quiet signal should be amplified to target amplitude."""
        preprocessor = AudioPreprocessor(AudioConfig(target_amplitude=0.8))
        quiet_sample = generate_sine_wave(amplitude=0.1, duration=0.5)
        assert quiet_sample.get_peak_amplitude() < 0.15

        normalized = preprocessor.normalize_amplitude(quiet_sample)
        peak = normalized.get_peak_amplitude()
        assert 0.75 < peak < 0.85  # Close to 0.8 target

    def test_normalize_loud_signal(self):
        """A loud signal should be reduced to target amplitude."""
        preprocessor = AudioPreprocessor(AudioConfig(target_amplitude=0.8))
        loud_sample = AudioSample(samples=[1.0, -1.0, 0.5], sample_rate=44100)

        normalized = preprocessor.normalize_amplitude(loud_sample)
        peak = normalized.get_peak_amplitude()
        assert 0.75 < peak < 0.85

    def test_normalize_empty(self):
        preprocessor = AudioPreprocessor()
        empty = AudioSample()
        result = preprocessor.normalize_amplitude(empty)
        assert result.sample_count == 0

    def test_normalize_metadata(self):
        preprocessor = AudioPreprocessor()
        sample = generate_sine_wave(amplitude=0.3, duration=0.1)
        normalized = preprocessor.normalize_amplitude(sample)
        assert normalized.metadata.get("normalized") is True


class TestNoiseGate:
    def test_removes_low_level_noise(self):
        """Samples below threshold should be zeroed."""
        preprocessor = AudioPreprocessor(AudioConfig(noise_gate_threshold=0.1))
        # Create sample with loud and quiet parts
        samples = [0.5, 0.05, -0.03, 0.8, 0.02, -0.7]
        sample = AudioSample(samples=samples, sample_rate=44100)

        gated = preprocessor.apply_noise_gate(sample)
        # Loud samples preserved, quiet ones zeroed
        assert gated.samples[0] == 0.5
        assert gated.samples[1] == 0.0  # Below threshold
        assert gated.samples[2] == 0.0  # Below threshold
        assert gated.samples[3] == 0.8

    def test_noise_gate_metadata(self):
        preprocessor = AudioPreprocessor()
        sample = generate_sine_wave(duration=0.1)
        gated = preprocessor.apply_noise_gate(sample)
        assert gated.metadata.get("noise_gated") is True

    def test_noise_gate_empty(self):
        preprocessor = AudioPreprocessor()
        result = preprocessor.apply_noise_gate(AudioSample())
        assert result.sample_count == 0


class TestResample:
    def test_upsample(self):
        """Upsampling should increase sample count."""
        preprocessor = AudioPreprocessor(AudioConfig(sample_rate=44100))
        low_rate = generate_sine_wave(duration=1.0, sample_rate=22050)
        assert low_rate.sample_count == 22050

        resampled = preprocessor.resample(low_rate)
        assert resampled.sample_rate == 44100
        assert resampled.sample_count == 44100

    def test_downsample(self):
        """Downsampling should decrease sample count."""
        preprocessor = AudioPreprocessor()
        high_rate = generate_sine_wave(duration=1.0, sample_rate=48000)

        resampled = preprocessor.resample(high_rate, target_rate=22050)
        assert resampled.sample_rate == 22050
        assert 22000 < resampled.sample_count < 22100

    def test_same_rate_no_change(self):
        preprocessor = AudioPreprocessor()
        sample = generate_sine_wave(sample_rate=44100)
        resampled = preprocessor.resample(sample)
        assert resampled.samples == sample.samples

    def test_resample_metadata(self):
        preprocessor = AudioPreprocessor()
        sample = generate_sine_wave(sample_rate=22050, duration=0.5)
        resampled = preprocessor.resample(sample)
        assert resampled.metadata.get("resampled_from") == 22050


class TestSegment:
    def test_correct_chunk_count(self):
        """A 10-second recording with 2-second chunks and 0.5s overlap should produce ~6 chunks."""
        preprocessor = AudioPreprocessor(AudioConfig(chunk_duration_sec=2.0, chunk_overlap_sec=0.5))
        sample = generate_sine_wave(duration=10.0)
        chunks = preprocessor.segment(sample)
        assert 5 <= len(chunks) <= 7

    def test_chunk_duration(self):
        preprocessor = AudioPreprocessor(AudioConfig(chunk_duration_sec=2.0))
        sample = generate_sine_wave(duration=10.0)
        chunks = preprocessor.segment(sample)
        for chunk in chunks[:-1]:  # Last chunk may be shorter
            assert 1.9 < chunk.duration_seconds < 2.1

    def test_chunk_metadata(self):
        preprocessor = AudioPreprocessor()
        sample = generate_sine_wave(duration=5.0)
        chunks = preprocessor.segment(sample)
        assert chunks[0].metadata.get("chunk_index") == 0
        assert chunks[0].metadata.get("chunk_start_sec") == 0.0

    def test_empty_sample_no_chunks(self):
        preprocessor = AudioPreprocessor()
        chunks = preprocessor.segment(AudioSample())
        assert chunks == []

    def test_short_sample_one_chunk(self):
        preprocessor = AudioPreprocessor(AudioConfig(chunk_duration_sec=2.0))
        sample = generate_sine_wave(duration=1.5)
        chunks = preprocessor.segment(sample)
        assert len(chunks) == 1


class TestFullPipeline:
    def test_prepare_for_analysis(self):
        """Full pipeline should produce normalized, gated, resampled, segmented chunks."""
        preprocessor = AudioPreprocessor()
        sample = generate_sine_wave(frequency=200, duration=5.0, amplitude=0.3)

        chunks = preprocessor.prepare_for_analysis(sample)
        assert len(chunks) >= 2
        # Each chunk should be normalized
        for chunk in chunks:
            assert chunk.metadata.get("normalized") is True
            assert chunk.sample_rate == 44100

    def test_pipeline_with_different_rate(self):
        preprocessor = AudioPreprocessor(AudioConfig(sample_rate=22050))
        sample = generate_sine_wave(frequency=100, duration=4.0, sample_rate=44100)
        chunks = preprocessor.prepare_for_analysis(sample)
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.sample_rate == 22050


# --- AudioFileManager ---


class TestAudioFileManager:
    def test_save_and_load_roundtrip(self, tmp_path):
        manager = AudioFileManager(recordings_dir=tmp_path)
        original = generate_sine_wave(frequency=440, duration=1.0, amplitude=0.5)

        filepath = manager.save_recording(original, filename="test.wav")
        assert filepath.exists()

        loaded = manager.load_recording(filepath)
        assert loaded.sample_rate == original.sample_rate
        assert loaded.channels == original.channels
        # Allow small rounding differences from float→int→float conversion
        assert abs(loaded.sample_count - original.sample_count) < 5
        assert loaded.source == "file"

    def test_save_auto_filename(self, tmp_path):
        manager = AudioFileManager(recordings_dir=tmp_path)
        sample = generate_sine_wave(duration=0.5)
        filepath = manager.save_recording(sample)
        assert filepath.exists()
        assert filepath.suffix == ".wav"

    def test_list_recordings(self, tmp_path):
        manager = AudioFileManager(recordings_dir=tmp_path)
        # Save 3 recordings
        for i in range(3):
            sample = generate_sine_wave(duration=0.5)
            manager.save_recording(sample, filename=f"test_{i}.wav")

        recordings = manager.list_recordings()
        assert len(recordings) == 3
        assert all("duration_seconds" in r for r in recordings)
        assert all("sample_rate" in r for r in recordings)

    def test_list_empty_directory(self, tmp_path):
        manager = AudioFileManager(recordings_dir=tmp_path)
        recordings = manager.list_recordings()
        assert recordings == []

    def test_amplitude_preserved_after_save_load(self, tmp_path):
        """Save/load should preserve amplitude within 16-bit quantization error."""
        manager = AudioFileManager(recordings_dir=tmp_path)
        original = generate_sine_wave(frequency=440, duration=0.5, amplitude=0.8)
        original_peak = original.get_peak_amplitude()

        filepath = manager.save_recording(original, filename="amp_test.wav")
        loaded = manager.load_recording(filepath)
        loaded_peak = loaded.get_peak_amplitude()

        # 16-bit quantization: max error is 1/32767 ≈ 0.00003
        assert abs(original_peak - loaded_peak) < 0.01
