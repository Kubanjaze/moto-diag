# MotoDiag Phase 99 — Audio Anomaly Detection

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build an AudioAnomalyDetector that identifies specific mechanical problems from engine sound spectrograms. Checks spectral energy distribution against 9 predefined anomaly signatures (knock, misfire, valve tick, exhaust leak, bearing whine, cam chain rattle, starter grind, clutch rattle, detonation). Returns ranked findings with confidence, severity, likely causes, and shop-appropriate repair recommendations.

CLI: `python -m pytest tests/test_phase99_anomaly.py -v`

Outputs: `src/motodiag/media/anomaly_detection.py` (AudioAnomalyDetector + AnomalyType + Severity + AnomalySignature + AudioAnomaly + ANOMALY_SIGNATURES), 29 tests

## Logic
- AnomalyType enum: 10 values (9 fault types + NORMAL)
- Severity enum: CRITICAL, HIGH, MODERATE, LOW, NONE — maps to shop urgency
- AnomalySignature model: anomaly_type, freq_low/high, energy_threshold, severity, description, likely_causes, secondary_bands
- ANOMALY_SIGNATURES: 9 predefined patterns with real-world frequency ranges, thresholds, and diagnostic content
- AudioAnomaly model: detection result with anomaly_type, confidence, frequency_range, description, likely_causes, severity, energy_fraction, recommendation
- AudioAnomalyDetector.detect(): for each signature, compute energy fraction in its frequency range, compare against threshold, calculate confidence from excess ratio, generate recommendation
- AudioAnomalyDetector.is_normal(): returns True if no anomalies above confidence threshold
- AudioAnomalyDetector.get_severity(): returns highest severity among all detected anomalies

## Key Concepts
- Energy fraction = sum(mag^2 in band) / sum(mag^2 total) — ratio of spectral power in anomaly band vs total
- Confidence scales from 0.3 (at threshold) to 1.0 (at 2x threshold): confidence = 0.3 + 0.7 * (excess_ratio - 1.0)
- Knock (1000-4000 Hz): sharp metallic impact from rod/main bearing wear, piston slap, wrist pin wear — CRITICAL
- Misfire (50-250 Hz): missing exhaust pulse from fouled plug, weak coil, vacuum leak, clogged injector — HIGH
- Valve tick (500-2000 Hz): consistent metallic tick from loose clearances or collapsed lifters — MODERATE
- Exhaust leak (200-4000 Hz): broadband hissing from blown gasket, cracked header, loose clamp — MODERATE
- Bearing whine (2000-8000 Hz): continuous high-frequency tone from worn crank/rod/cam/transmission bearings — HIGH
- Cam chain rattle (800-3000 Hz): slapping sound from worn tensioner or stretched chain — MODERATE
- Detonation (2000-6000 Hz): metallic pinging from low octane, carbon buildup, lean mixture, advanced timing — CRITICAL
- Each anomaly includes shop-specific recommendations: what to check, how to test, when to stop riding
- Configurable confidence_threshold and custom signatures allow tuning detection sensitivity

## Verification Checklist
- [x] AnomalyType enum has all 10 values (2 tests)
- [x] Severity enum has all 5 levels (1 test)
- [x] 9 anomaly signatures defined with required fields, correct severity levels (4 tests)
- [x] Knock and valve tick signature detail validation (2 tests)
- [x] AudioAnomaly model construction and defaults (2 tests)
- [x] detect() returns list, handles empty spectrogram, sorted by confidence (3 tests)
- [x] High-frequency signal triggers bearing/detonation/knock anomalies (1 test)
- [x] Detected anomalies have non-empty recommendations and valid confidence/energy ranges (3 tests)
- [x] is_normal() returns bool, empty spectrogram is normal (2 tests)
- [x] get_severity() returns NONE for empty, valid enum for non-empty, severity ordering (3 tests)
- [x] Custom threshold: strict produces fewer results than loose (1 test)
- [x] Custom signatures and empty signatures work correctly (2 tests)

## Risks
- Energy-threshold-based detection is a simplification — real anomaly detection should also consider temporal patterns (periodicity with RPM, transient vs continuous). Future phases can add time-domain analysis.
- Overlapping frequency ranges between anomaly types (e.g., knock 1000-4000 and detonation 2000-6000) can produce multiple detections from a single source. This is by design — the mechanic evaluates the ranked list.
- Confidence scaling assumes a linear relationship between excess energy and detection certainty. Real-world calibration against engine recordings would improve accuracy.

## Results
| Metric | Value |
|--------|-------|
| Files created | 1 (anomaly_detection.py) |
| Tests | 29 |
| Anomaly types | 9 (+ NORMAL) |
| Severity levels | 5 (CRITICAL, HIGH, MODERATE, LOW, NONE) |
| External deps | 0 (pure Python + Pydantic) |

Key finding: The energy-fraction-based detection correctly identifies frequency bands with elevated energy and maps them to specific mechanical anomalies. The confidence scaling (threshold to 2x threshold) provides differentiated results — marginal detections get low confidence while clear anomalies get high confidence. The shop-specific recommendations embed real diagnostic workflow knowledge (e.g., "drain oil and inspect for metallic particles" for bearing whine, "use carb cleaner spray test for vacuum leaks" for misfire).
