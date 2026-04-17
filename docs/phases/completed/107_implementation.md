# MotoDiag Phase 107 — AI Audio Coaching

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build an AudioCoach class that guides mechanics through standardized audio capture protocols to ensure recordings are usable for diagnostic analysis. Provides step-by-step instructions with RPM targets and mic positioning, evaluates capture quality (duration, signal level, clipping, SNR), and selects appropriate protocols based on reported symptoms or engine type. Includes 5 predefined protocols covering the most common diagnostic scenarios. Works entirely offline — no API calls needed.

CLI: `python -m pytest tests/test_phase107_coaching.py -v`

Outputs: `src/motodiag/media/coaching.py` (AudioCoach + 5 CaptureProtocols + QualityAssessment), 30 tests

## Logic
- CoachingStep model: step_number, instruction, expected_condition, duration_seconds, rpm_target (optional), mic_position, notes
- CaptureProtocol model: name, description, steps list, total_duration, engine_types_applicable, symptoms_applicable, min_quality_required
- QualityAssessment model: quality (excellent/good/acceptable/poor/unusable), score (0.0-1.0), issues list, suggestions list, meets_minimum bool, metrics dict
- 5 predefined CAPTURE_PROTOCOLS:
  - idle_baseline: 3 steps, 50s — cold start to stable idle for baseline sound signature
  - rev_sweep: 5 steps, 40s — slow RPM sweep to capture sound at all speeds
  - load_test: 4 steps, 35s — throttle blips to test transient response
  - cold_start: 4 steps, 85s — full cold start sequence from crank to stable idle
  - decel_pop: 5 steps, 48s — rev to 5000 then snap throttle closed for backfire detection
- SYMPTOM_PROTOCOL_MAP: maps 20+ symptoms to ranked protocol lists
- AudioCoach.get_protocol(): select by name, symptom (direct + fuzzy match), or engine type
- AudioCoach.get_protocols_for_symptom(): returns all applicable protocols ranked by relevance
- AudioCoach.list_protocols(): returns summary list of all 5 protocols
- AudioCoach.start_protocol(): begins coaching session, returns first step
- AudioCoach.get_current_step(): returns current instruction
- AudioCoach.advance_step(): moves to next step, returns None when protocol complete
- AudioCoach.finish_protocol(): ends session, returns summary with steps completed, quality assessments
- AudioCoach.evaluate_capture(): 4-factor quality assessment:
  1. Duration check: at least 50% of protocol step duration
  2. Signal level: RMS must be > 0.01 (not silent) and > 0.05 (strong enough)
  3. Clipping: >5% of samples at 0.99 = severe, >1% = mild
  4. Signal-to-noise: compares loudest 10% vs quietest 10% of sub-windows, SNR < 2x = poor

## Key Concepts
- CaptureQuality enum with 5 levels mapped to score thresholds: excellent (0.85+), good (0.70+), acceptable (0.50+), poor (0.30+), unusable (<0.30)
- EngineType enum: single_cylinder, v_twin, parallel_twin, inline_four, v_four, flat_twin, unknown
- Protocol selection via symptom mapping: direct match in SYMPTOM_PROTOCOL_MAP, then fuzzy match against protocol symptoms_applicable, then default to idle_baseline
- Quality evaluation is entirely local — no API call needed to assess capture quality
- Each protocol step includes mic_position guidance (e.g., "12 inches from exhaust pipe opening", "near cylinder head")
- Protocol steps include RPM targets for mechanic reference and notes with diagnostic interpretation tips
- Session state tracks progress (0.0-1.0) and stores per-step quality assessments
- Quality suggestions are actionable: "Move the phone closer", "Reduce background noise", "Record at least N more seconds"

## Verification Checklist
- [x] CoachingStep and CaptureProtocol model creation (2 tests)
- [x] Quality score mapping (1 test)
- [x] All 5 predefined protocols exist with correct structure (7 tests)
- [x] Protocol selection: by name, unknown name raises, by symptom (direct, fuzzy, default fallback), default, for_symptom multiple, list_protocols (8 tests)
- [x] Coaching session: start, double-start raises, empty protocol raises, get_current_step (active and inactive), advance through all steps, advance no session raises, finish with summary, finish no session raises, progress tracking (9 tests)
- [x] Capture evaluation: good sample, silent sample, clipped sample, short sample, stores in session, metrics present, empty sample (7 tests)

## Risks
- Quality thresholds are heuristic — may need tuning with real-world recordings from motorcycle shops. The threshold values (0.85/0.70/0.50/0.30) are reasonable starting points based on audio engineering norms.
- Protocol durations are approximations. Real mechanics may take longer or shorter depending on the bike and their comfort level.
- SNR estimation is approximate — compares sub-window RMS values rather than true spectral SNR. Sufficient for "good enough" vs "too noisy" decisions.

## Results
| Metric | Value |
|--------|-------|
| Files created | 1 (coaching.py) |
| Tests | 30 |
| Models | 3 (CoachingStep, CaptureProtocol, QualityAssessment) |
| Predefined protocols | 5 (idle_baseline, rev_sweep, load_test, cold_start, decel_pop) |
| Symptom mappings | 20+ symptoms mapped to protocol recommendations |
| Quality factors | 4 (duration, signal level, clipping, SNR) |
| Quality levels | 5 (excellent, good, acceptable, poor, unusable) |
| External deps | 0 (uses Phase 96 AudioSample) |

Key finding: The coaching system is the bridge between "mechanic holds phone near bike" and "AI has usable audio to analyze." The 5 protocols cover the most common diagnostic scenarios in motorcycle shops: baseline comparison, full-range sweep, transient response, cold start behavior, and exhaust condition. The quality evaluator gives immediate feedback so the mechanic can re-record before leaving the diagnostic session.
