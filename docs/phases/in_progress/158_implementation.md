# MotoDiag Phase 158 — Sensor Degradation Tracking (drift)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-18

## Goal

Eleventh Track F phase. Track slow-onset sensor drift across monthly recordings of same bike. Fit linear trend lines per PID; flag drifting >5% per 30 days. O2 sensor aging, coolant-at-idle creeping (silting radiator), battery-resting-voltage decaying.

No AI, no migration, no tokens. Pure SQL on Phase 142 `sensor_samples` + `statistics` stdlib.

CLI: `motodiag advanced drift {bike, show, recording, plot}`.

Outputs:
- `advanced/drift.py` (~280 LoC): `compute_trend(vehicle_id, pid_hex, since, until)` (stdlib mean-of-products linear regression, no numpy); `detect_drifting_pids(vehicle_id, threshold_pct=5)` (scans all recorded PIDs, filter ≥ threshold); `summary_for_bike(vehicle_id)` (three-bucket dict: stable / drifting-slow / drifting-fast); `_render_sparkline` (Unicode 1/8 blocks U+2581..U+2588 copied from Phase 143 — no Textual dep); `_render_csv` (wide format, one row per recording).
- `DriftResult` + `DriftBucket` Pydantic frozen models.
- `advanced/__init__.py` +6 LoC exports.
- `cli/advanced.py` +~250 LoC: `drift` subgroup (4 subcommands). Rich panel with signed drift_pct (positive coolant = bad; positive battery = good — colored differently). `drift plot --format ascii` (stdout) / `csv --output PATH`.
- `advanced/predictor.py` +~25 LoC: opt-in `_apply_drift_bonus`: drifting-fast PIDs whose catalog name overlaps `issue.symptoms[]` → `+0.1` confidence via `model_copy(update=...)` (frozen-safe). Capped +0.1 regardless of matches; best-effort (broad except — never break predict).
- `tests/test_phase158_drift.py` (~30 tests, 4 classes).

No migration. No tables.

## Logic

**Trend formula (stdlib only):**
```
slope = sum((x-mean_x)*(y-mean_y)) / sum((x-mean_x)**2)
intercept = mean_y - slope * mean_x
r² = sxy² / (sxx * syy)
drift_pct_per_30_days = 100 * slope_per_day * 30 / mean_y   # signed
```

Edge cases: `n < 2` → None; `sxx == 0` (all same instant) → None; `syy == 0` → r²=1, slope=0 (flat = stable).

**Thresholds** (default `threshold_pct=5.0`):
- `|pct| < threshold` → STABLE.
- `threshold ≤ |pct| < 2*threshold` → DRIFTING_SLOW (5-10%/30d).
- `|pct| ≥ 2*threshold` → DRIFTING_FAST (≥10%/30d).

**Sparse summary OK for monthly cross-recording trend** — 12 recordings × ~100 sparse samples = 1200 points for regression. Full fidelity via `load_recording` reserved for `drift recording` intra-session.

**Phase 148 integration:** `_apply_drift_bonus` lazy-imports drift module (avoid circular within `advanced`), catches any exception → returns unbonused score. Single `+0.1` cap across any number of matching drifting-fast PIDs.

## Verification Checklist

- [ ] `compute_trend` stdlib-only (no numpy/scipy/pandas).
- [ ] Slope/intercept/r² match hand-computed fixture to 4 decimals.
- [ ] `n<2` → None; `sxx==0` → None.
- [ ] `drift_pct_per_30_days` signed.
- [ ] Bucket boundaries at threshold + 2*threshold.
- [ ] `summary_for_bike` three buckets always present.
- [ ] `_detect_drifting_pids` deterministic sort by `abs(pct) DESC, pid_hex ASC`.
- [ ] CLI 4 subcommands + `--json` + `--since/--until` validation + `--bike MISSING` → remediation.
- [ ] `drift plot --format ascii` Unicode blocks; `csv --output PATH` wide format.
- [ ] `_apply_drift_bonus` +0.1 on match; no-op on no-id/no-drift/no-overlap; never breaks predict.
- [ ] Phase 148 44 tests + Phase 142 tests still green.
- [ ] No migration; SCHEMA_VERSION unchanged.

## Risks

- SQL join scales linearly with history (N bikes × 120 recordings). Phase 142 `idx_samples_recording_pid` exists; verify via EXPLAIN QUERY PLAN.
- ISO 8601 parsing cost on 1M+ samples — profile; cache or precompute epoch if slow.
- Threshold 5%/30d calibrated to O2 aging; per-PID overrides Phase 159+.
- JSONL-spilled recordings invisible to drift bike/show (SQLite-only). Documented; `drift recording` uses full fidelity.
- Predictor circular (predictor↔drift in `advanced`) — lazy import inside helper.
- FailurePrediction frozen + `model_copy(update={"confidence_score":..., "confidence":...})` — re-bucket HIGH/MEDIUM/LOW if threshold crosses.
- Sparse summary uniform in count not time — acceptable (captured_at is x).
- Windows CSV blank-row: use `newline=""` + csv.DictWriter.
- Zero-variance flat series → stable (correct).
