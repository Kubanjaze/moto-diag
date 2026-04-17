# MotoDiag Phase 103 — Comparative Audio Analysis

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build a ComparativeAnalyzer class for "before vs after" audio comparison. Records a baseline engine audio (before repair), performs the repair, records current audio (after repair), compares frequency spectra to detect new peaks, disappeared peaks, amplitude changes, and frequency shifts. Produces an improvement score from -1.0 (worse) to 1.0 (fully resolved) with detailed difference reports and diagnostic hints.

CLI: `python -m pytest tests/test_phase103_comparative.py -v`

Outputs: `src/motodiag/media/comparative.py` (ComparativeAnalyzer + spectrogram support + models), 30 tests

## Logic
- FrequencyPeak model: frequency_hz, amplitude, bandwidth_hz. Computed: is_low_frequency (<200 Hz), is_mid_frequency (200-2000 Hz), is_high_frequency (>2000 Hz).
- SpectrogramData model: peaks list, dominant_frequency_hz, total_energy, noise_floor, sample_rate. Computed: peak_count, snr (signal-to-noise ratio).
- analyze_frequencies(): basic DFT-based frequency analysis on AudioSample. Logarithmic frequency spacing from 20 Hz to 10 kHz. Detects peaks as local maxima, returns top N by amplitude.
- FrequencyChange model: frequency_hz, baseline/current amplitude, change_type (new_peak, disappeared_peak, amplitude_increase, amplitude_decrease, frequency_shift), change_magnitude, diagnostic_hint.
- ComparisonResult model: baseline_summary, current_summary, differences list, frequency_changes list, improvement_score (-1.0 to 1.0), new_anomalies, resolved_anomalies, energy_change_percent, dominant_frequency_shift_hz. Computed: improved (>0), worsened (<0), unchanged (abs < 0.05).
- ComparativeAnalyzer.compare(): takes baseline + current AudioSample (and optional pre-computed spectra), analyzes both, calls identify_changes and score_improvement, builds summaries and difference lists.
- ComparativeAnalyzer.identify_changes(): matches peaks between baseline and current by frequency proximity (within tolerance_hz), detects new/disappeared peaks and amplitude changes exceeding threshold.
- ComparativeAnalyzer.score_improvement(): weights resolved peaks (+0.3), new peaks (-0.3), amplitude decreases (+0.15), amplitude increases (-0.15), energy decrease (+0.1), normalizes to -1.0 to 1.0.
- _FREQUENCY_HINTS: 12 diagnostic hints mapped by change type (new/gone/louder/quieter) and frequency band (low/mid/high). Examples: "New high-frequency peak may indicate bearing wear" or "Disappeared mid-frequency noise — valve train issue may be resolved."
- Phase 97 (SpectrogramAnalyzer) does not exist yet — local FrequencyPeak/SpectrogramData/analyze_frequencies defined here as a stopgap. Will be replaced with proper imports when Phase 97 is built.

## Key Concepts
- Before/after comparison workflow: baseline capture → repair → current capture → compare
- Frequency proximity matching (tolerance_hz) handles slight RPM differences between recordings
- Improvement scoring: resolved anomalies push score positive, new anomalies push negative
- Diagnostic hints by frequency band: low (<200 Hz) = exhaust/mounting, mid (200-2000 Hz) = valve train/chain, high (>2000 Hz) = bearings/belts
- DFT-based frequency analysis with logarithmic bin spacing (motorcycle-relevant 20 Hz - 10 kHz range)
- Local spectrogram support as stopgap for Phase 97

## Verification Checklist
- [x] FrequencyPeak: low, mid, high frequency bands, boundary 200 Hz, boundary 2000 Hz (5 tests)
- [x] SpectrogramData: empty, peak_count, snr calculation, snr zero noise (4 tests)
- [x] analyze_frequencies: empty sample, single frequency detected near expected, total energy positive, noise floor < dominant, very short sample (5 tests)
- [x] ComparisonResult: improved, worsened, unchanged, unchanged boundary (4 tests)
- [x] identify_changes: no changes identical, new peak, disappeared peak, amplitude increase, amplitude decrease, small change ignored, frequency tolerance matching, diagnostic hints populated (8 tests)
- [x] score_improvement: no changes zero, resolved positive, new negative, bounded -1 to 1 (4 tests)
- [x] compare: identical samples, precomputed spectra with new peak, resolved anomaly, energy change, dominant frequency shift, summaries populated, differences list populated (7 tests)

## Deviations from Plan
- Phase 97 (SpectrogramAnalyzer) does not exist yet. Defined local FrequencyPeak, SpectrogramData, and analyze_frequencies() as stopgap. These will be replaced with imports from `motodiag.media.spectrogram` when Phase 97 is built.

## Risks
- DFT analysis is naive (not FFT) and slow for large samples — adequate for comparison but not production spectrogram display
- Frequency tolerance matching assumes similar RPM between recordings — large RPM differences could misalign peaks
- Improvement score weighting is heuristic — may need tuning based on real diagnostic outcomes

## Results
| Metric | Value |
|--------|-------|
| Files created | 1 (comparative.py) |
| Tests | 30 (all synthetic audio, no API calls) |
| Models | 5 (FrequencyPeak, SpectrogramData, FrequencyChange, ComparisonResult, + analyze_frequencies) |
| Diagnostic hints | 12 (4 change types x 3 frequency bands) |
| Analyzer methods | 3 (compare, identify_changes, score_improvement) |
| External deps | 0 (uses AudioSample from Phase 96) |

Key finding: The frequency proximity matching with configurable tolerance (default 15 Hz) is essential for real-world use — a mechanic won't hold the exact same RPM for both recordings. Without tolerance, every peak would appear as new+disappeared instead of matched.
