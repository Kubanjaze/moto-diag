# MotoDiag Phase 98 — Engine Sound Signature Database

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build a SoundSignatureDB with known-good baseline sound profiles for 7 engine types. Maps each engine configuration to expected firing frequency ranges (idle and 5000 RPM), harmonic patterns, and characteristic sounds. Enables identifying engine type from audio and detecting deviations from expected profiles. Includes RPM estimation from firing frequency and confidence-scored profile matching.

CLI: `python -m pytest tests/test_phase98_sound_signatures.py -v`

Outputs: `src/motodiag/media/sound_signatures.py` (SoundSignatureDB + SoundSignature + EngineType + SignatureMatch + SIGNATURES dict + rpm_to_firing_frequency()), 25 tests

## Logic
- EngineType enum: 7 configurations (SINGLE_CYLINDER, V_TWIN, PARALLEL_TWIN, INLINE_THREE, INLINE_FOUR, V_FOUR, BOXER_TWIN)
- SoundSignature model: engine_type, idle_rpm_range, firing_freq at idle and 5000 RPM, expected_harmonics multipliers, characteristic_sounds descriptions, cylinders, strokes, notes
- rpm_to_firing_frequency(): (RPM/60) * (cylinders/2) for 4-stroke engines
- SIGNATURES dict: pre-built signature for each engine type with real-world frequency ranges, harmonic patterns, and shop-relevant sound descriptions
- SoundSignatureDB.get_signature(): lookup by engine type
- SoundSignatureDB.estimate_rpm(): inverse calculation — firing_freq * 120 / cylinders
- SoundSignatureDB.match_profile(): compares SpectrogramResult against all signatures using 3-criterion scoring:
  1. Peak frequency in expected firing range (0-50 points)
  2. Harmonic pattern match — checks if expected harmonics have significant energy (0-30 points)
  3. Band energy distribution — whether energy concentrates in expected bands for that engine type (0-20 points)
- Returns ranked SignatureMatch list with confidence, firing_freq_match flag, harmonic_score, and diagnostic notes

## Key Concepts
- Firing frequency formula: freq = (RPM/60) * (cylinders/2) — fundamental combustion frequency for 4-stroke engines
- V-twin uneven firing intervals (315/405 degrees for 45-degree V) produce sub-harmonics and characteristic "potato-potato" sound
- Inline-4 even firing produces strong even-order harmonics (2nd, 4th, 6th) with suppressed odd harmonics
- Inline-3 has characteristically strong 3rd harmonic from 120-degree firing intervals (Triumph triples)
- Boxer twin fires at even 360-degree intervals but produces lateral rocking vibration unique to the configuration
- V-four combines twin-like uneven firing with 4-cylinder power — Honda VFR gear whine is normal, not a fault
- Harmonic scoring checks each expected multiplier (1x, 2x, 3x...) for significant energy — hits/total = score
- Band distribution scoring compares actual energy concentration against engine-type-specific expected bands
- RPM estimation is the inverse of firing frequency: RPM = firing_freq * 120 / cylinders
- Partial credit scoring for peak frequencies near (but not in) expected ranges prevents hard cutoff artifacts

## Verification Checklist
- [x] EngineType enum has all 7 types with correct string values (2 tests)
- [x] rpm_to_firing_frequency: single@1000RPM=8.33Hz, vtwin@1000=16.67Hz, inline4@6000=200Hz, inline3@5000=125Hz, zero RPM (5 tests)
- [x] All engine types have cylinder counts and signatures defined (2 tests)
- [x] Signature fields fully populated: RPM ranges, firing freqs, harmonics, characteristic sounds (2 tests)
- [x] V-twin and inline-4 signature content validation (2 tests)
- [x] SoundSignatureDB.get_signature(): exists, all types, missing in empty DB (3 tests)
- [x] estimate_rpm: single@8.33Hz=1000RPM, inline4@200Hz=6000RPM, roundtrip for all types (3 tests)
- [x] match_profile: returns list, sorted by confidence, top_n limits, empty spectrogram, required fields (5 tests)
- [x] High-freq signal does not strongly match single-cylinder idle (1 test)
- [x] Composite engine harmonics produce meaningful matches (1 test)

## Risks
- Frequency resolution of the spectrogram (43 Hz at 1024/44100) limits ability to distinguish engines with similar firing frequencies. Mitigated by combining frequency match with harmonic pattern and band distribution scoring.
- Confidence scoring weights are heuristic — may need calibration against real engine recordings. Current weights (50/30/20) prioritize firing frequency match.
- Single-spectrogram matching does not account for RPM changes during recording. Future enhancement: track firing frequency over time.

## Results
| Metric | Value |
|--------|-------|
| Files created | 1 (sound_signatures.py) |
| Tests | 25 |
| Engine types | 7 (all common motorcycle configurations) |
| Scoring criteria | 3 (firing freq, harmonics, band distribution) |
| External deps | 0 (pure Python + Pydantic) |

Key finding: The three-criterion scoring system (firing frequency match + harmonic pattern + band distribution) provides differentiated confidence scores across engine types. V-twins and inline-4s are the most spectrally distinct due to their different harmonic structures. The RPM-to-frequency roundtrip is exact (floating point), confirming the formula implementation.
