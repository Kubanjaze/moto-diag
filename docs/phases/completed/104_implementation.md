# MotoDiag Phase 104 — Real-Time Audio Monitoring

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build a RealtimeMonitor class that processes AudioSample chunks as they arrive during a live diagnostic session. Estimates engine RPM from audio using zero-crossing rate, computes anomaly scores to detect misfires and mechanical issues, and generates alerts when anomaly thresholds are exceeded. Simulated monitoring — no actual microphone capture, but processes chunks fed by the caller (CLI, API, or mobile app).

CLI: `python -m pytest tests/test_phase104_realtime.py -v`

Outputs: `src/motodiag/media/realtime.py` (RealtimeMonitor + RPM estimation + anomaly detection), 26 tests

## Logic
- MonitorConfig: configurable analysis_interval_sec, alert_threshold (0.0-1.0), display_mode (compact/detailed/alerts_only), rpm_smoothing_window
- MonitorEvent: timestamp, event_type (analysis_result/alert/status/session_start/session_stop), severity (info/warning/critical), data dict, message
- MonitorSession: session_id, started_at, ended_at, events list, is_active flag, current_rpm_estimate, rpm_history, anomaly_count, chunks_processed, total_audio_seconds
- RealtimeMonitor.start_session(): creates MonitorSession, adds SESSION_START event, raises if already active
- RealtimeMonitor.process_chunk(): preprocesses chunk (normalize + noise gate), estimates RPM via zero-crossing, computes anomaly score, generates ANALYSIS_RESULT event, generates ALERT events if anomaly exceeds threshold or RPM delta > 500
- RealtimeMonitor.get_status(): returns dict with session state (RPM, anomalies, duration, chunk count)
- RealtimeMonitor.stop_session(): finalizes session, adds SESSION_STOP event, returns summary with RPM range, avg/max anomaly scores, alert count
- estimate_rpm_from_samples(): counts zero-crossings, derives fundamental frequency, converts to RPM (single-cylinder 4-stroke: RPM = freq * 120), clamps to 200-18000 RPM range
- compute_anomaly_score(): combines transient spike ratio (60% weight) with amplitude coefficient of variation across sub-windows (40% weight), returns 0.0-1.0

## Key Concepts
- Zero-crossing rate for fundamental frequency estimation: frequency = crossings / (2 * duration)
- RPM from single-cylinder 4-stroke firing frequency: RPM = frequency * 120
- RPM smoothing via sliding window average (configurable window size)
- Anomaly detection via transient spike counting (samples > 3x RMS) and amplitude variability (coefficient of variation across sub-windows)
- Alert severity levels: info (anomaly 0.15-0.4), warning (0.4-0.7), critical (>0.7)
- RPM delta alerts when consecutive estimates differ by > 500 RPM
- Preprocessing reuses AudioPreprocessor from Phase 96 (normalize + noise gate)
- Session lifecycle: start_session() -> process_chunk() loop -> get_status() -> stop_session()

## Verification Checklist
- [x] MonitorConfig defaults and custom values (2 tests)
- [x] MonitorEvent creation with types and severity (2 tests)
- [x] MonitorSession creation, properties, alert/analysis event filtering (2 tests)
- [x] RPM estimation: known frequency, idle frequency, too short, empty, out of range (5 tests)
- [x] Anomaly score: clean signal, noisy signal, empty, silent (4 tests)
- [x] Session lifecycle: start, double-start raises, stop, stop-without-start raises, process-without-start raises, status-without-session raises (6 tests)
- [x] Processing: single chunk, multiple chunks with RPM update, alert generation, status keys, summary with RPM range, RPM smoothing window, stop event recorded, full lifecycle (8 tests)

## Risks
- Zero-crossing RPM estimation is rough — works for single dominant frequency but may be confused by rich harmonics. Acceptable for real-time monitoring where precision is secondary to change detection.
- Anomaly score is heuristic-based. Will be refined in later Track C phases with ML models.

## Results
| Metric | Value |
|--------|-------|
| Files created | 1 (realtime.py) |
| Tests | 26 |
| Models | 3 (MonitorConfig, MonitorEvent, MonitorSession) |
| Functions | 2 standalone (estimate_rpm_from_samples, compute_anomaly_score) |
| Alert severity levels | 3 (info, warning, critical) |
| External deps | 0 (uses Phase 96 AudioSample + AudioPreprocessor) |

Key finding: The RealtimeMonitor processes audio chunks without any hardware dependency — chunks arrive from whatever source (mic, file, synthetic) and the monitor applies the same analysis pipeline. RPM estimation via zero-crossing is fast enough for real-time use and provides reasonable estimates for single-dominant-frequency engine audio.
