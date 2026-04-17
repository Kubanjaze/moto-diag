# MotoDiag Phase 97 — Audio Spectrogram Analysis

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build a SpectrogramAnalyzer that computes frequency-domain representations of motorcycle engine audio using pure Python DFT (no numpy). Identifies dominant frequency bands relevant to motorcycle diagnostics — firing frequency, valve train noise, exhaust note, bearing whine, and knock signatures. Operates on a small sample window (first 1024 samples) for performance while maintaining sufficient frequency resolution for diagnostic purposes.

CLI: `python -m pytest tests/test_phase97_spectrogram.py -v`

Outputs: `src/motodiag/media/spectrogram.py` (SpectrogramAnalyzer + FrequencyBand + SpectrogramResult + MOTORCYCLE_FREQUENCY_BANDS), 30 tests

## Logic
- FrequencyBand model defines named frequency ranges: name, freq_low, freq_high, description
- SpectrogramResult model holds DFT output: frequency_bins, magnitude_bins, peak_frequency, dominant_bands, band_energies, duration_analyzed
- MOTORCYCLE_FREQUENCY_BANDS defines 6 diagnostic bands: low_rumble (20-100 Hz), firing_frequency (50-250 Hz), exhaust_note (200-1000 Hz), valve_train (500-2000 Hz), knock (1000-4000 Hz), bearing_whine (2000-8000 Hz)
- SpectrogramAnalyzer.compute_fft(): takes AudioSample, extracts first window_size samples, applies Hann window to reduce spectral leakage, computes DFT via sum of cos/sin products, returns frequency/magnitude pairs up to Nyquist
- SpectrogramAnalyzer.identify_dominant_bands(): sums squared magnitudes in each band's range, ranks bands by energy, returns top N
- SpectrogramAnalyzer.detect_peak_frequency(): finds highest-magnitude bin (skipping DC component)
- SpectrogramAnalyzer.analyze(): full pipeline — compute_fft → detect_peak → identify_dominant_bands → SpectrogramResult

## Key Concepts
- Pure Python DFT: X[k] = sum(x[n] * e^{-j*2*pi*k*n/N}) implemented with math.cos/sin — no numpy dependency
- Hann window: w[n] = 0.5 * (1 - cos(2*pi*n/(N-1))) reduces spectral leakage at window boundaries
- Frequency resolution = sample_rate / window_size (e.g., 44100/1024 = 43 Hz per bin)
- Only compute bins 0..N/2 (Nyquist limit) — real-valued input has symmetric spectrum
- Magnitudes normalized by window size to make results amplitude-independent
- Band energy = sum of squared magnitudes in frequency range — proportional to power
- DC component (bin 0) skipped in peak detection — represents signal mean, not oscillation
- 6 motorcycle-specific bands cover the full diagnostic spectrum from 20 Hz to 8 kHz
- Overlapping bands (e.g., exhaust_note and valve_train both cover 500-1000 Hz) allow multiple classifications
- Window size 1024 balances frequency resolution (43 Hz) against computation time for pure Python DFT

## Verification Checklist
- [x] FrequencyBand model creates with all fields (1 test)
- [x] All 6 motorcycle frequency bands defined with correct ranges (2 tests)
- [x] SpectrogramResult default and populated construction (2 tests)
- [x] compute_fft returns correct-length frequency/magnitude arrays (3 tests)
- [x] compute_fft empty and short sample handling (2 tests)
- [x] Peak detection finds correct frequency for 440 Hz, 3000 Hz sine waves (2 tests)
- [x] Peak detection handles empty and single-bin edge cases (2 tests)
- [x] Dominant band identification: 100 Hz → firing_frequency, 3000 Hz → knock/bearing (2 tests)
- [x] Top-N limiting, empty input, and all-bands-in-energies-dict (3 tests)
- [x] Full analyze pipeline: result type, empty, duration, composite, window/sample_rate recorded (6 tests)
- [x] Custom window size and custom bands (2 tests)

## Risks
- Pure Python DFT is O(N^2) — window_size must stay small (1024 max recommended). Mitigated by only analyzing first 1024 samples.
- 43 Hz frequency resolution means closely-spaced frequencies (e.g., 100 Hz and 130 Hz) may not be resolved. Acceptable for motorcycle band identification which uses broad ranges.
- Hann window reduces amplitude of signals at window edges — acceptable tradeoff for reduced spectral leakage.

## Results
| Metric | Value |
|--------|-------|
| Files created | 1 (spectrogram.py) |
| Tests | 30 |
| Frequency bands | 6 (motorcycle-specific) |
| DFT window | 1024 samples (pure Python) |
| External deps | 0 (pure Python: math only) |

Key finding: The pure Python DFT is computationally feasible for small windows and provides sufficient frequency resolution to distinguish all 6 motorcycle diagnostic bands. The Hann windowing and magnitude normalization produce clean spectral results from synthetic test signals with peaks correctly identified within one frequency bin of the true value.
