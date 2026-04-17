# MotoDiag Phase 96 — Audio Capture + Preprocessing

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Build the audio capture and preprocessing foundation for media diagnostics. Handles recording engine audio (from file or synthetic generation), applying noise reduction, normalizing sample rate and amplitude, segmenting into analyzable chunks, and managing audio files on disk. Designed for phone microphone input in noisy motorcycle shop environments. Pure Python — no external audio libraries required.

CLI: `python -m pytest tests/test_phase96_audio_capture.py -v`

Outputs: `src/motodiag/media/audio_capture.py` (AudioPreprocessor + AudioFileManager + generators), 36 tests

## Key Concepts
- AudioConfig: configurable sample rate (44100 Hz), channels (mono), chunk duration, overlap, noise gate threshold, target amplitude
- AudioSample model: samples as float list (-1.0 to 1.0), peak/RMS amplitude, metadata dict for vehicle info
- AudioPreprocessor.normalize_amplitude(): scales peak to target level — equalizes near vs far mic placement
- AudioPreprocessor.apply_noise_gate(): silences samples below threshold — removes shop background noise
- AudioPreprocessor.resample(): linear interpolation to target rate — handles varying phone mic sample rates
- AudioPreprocessor.segment(): splits into overlapping chunks (2s with 0.5s overlap) — no transient events lost
- AudioPreprocessor.prepare_for_analysis(): chains normalize → gate → resample → segment
- AudioFileManager: save/load WAV files, list recordings with metadata, auto-generated filenames
- generate_sine_wave(): synthetic test audio at specified frequency/amplitude/duration
- generate_composite_wave(): multi-frequency waveform simulating engine harmonics (fundamental + overtones)

## Verification Checklist
- [x] AudioConfig creates with correct defaults and custom values (2 tests)
- [x] AudioSample: empty, with data, RMS amplitude, metadata (4 tests)
- [x] Sine wave generation: duration, amplitude, source, metadata (4 tests)
- [x] Composite wave: multiple frequencies, normalization, empty (3 tests)
- [x] Normalize: quiet amplified, loud reduced, empty handled, metadata tracked (4 tests)
- [x] Noise gate: low-level removed, metadata, empty (3 tests)
- [x] Resample: upsample, downsample, same-rate passthrough, metadata (4 tests)
- [x] Segment: chunk count, duration, metadata, empty, short sample (5 tests)
- [x] Full pipeline: prepare_for_analysis, different rate (2 tests)
- [x] File manager: save/load roundtrip, auto filename, list, empty dir, amplitude preserved (5 tests)
- [x] All 36 tests pass (1.36s)

## Results
| Metric | Value |
|--------|-------|
| Files created | 1 (audio_capture.py) |
| Tests | 36/36, 1.36s |
| Pipeline steps | 4 (normalize, noise gate, resample, segment) |
| File formats | WAV (16-bit PCM) |
| External deps | 0 (pure Python: wave, struct, array, math) |

Key finding: The audio module is entirely self-contained with no external dependencies. The phone captures audio natively (React Native Track I), sends it to the backend, and this module preprocesses it into uniform chunks ready for spectrogram analysis. The synthetic generators enable comprehensive testing without any audio hardware.
