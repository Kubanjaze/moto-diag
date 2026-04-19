# MotoDiag Phase 158 — Phase Log

**Status:** 🟡 Planned | **Started:** 2026-04-18 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag

### 2026-04-18 19:15 — Plan written, v1.0

Eleventh Track F phase. Sensor degradation tracking — linear regression across cross-recording samples per PID. Flag drifting >5%/30d (slow) / ≥10%/30d (fast). O2 aging / coolant-at-idle silting / battery decay.

**Scope:** `advanced/drift.py` (~280 LoC) — stdlib mean-of-products regression (no numpy), `compute_trend`/`detect_drifting_pids`/`summary_for_bike`/`_render_sparkline` (Unicode 1/8 blocks copied from Phase 143, no Textual dep)/`_render_csv` (wide format one row per recording). DriftResult + DriftBucket frozen Pydantic. `cli/advanced.py` +250 LoC `drift` subgroup (4 subcommands). `advanced/predictor.py` +25 LoC opt-in `_apply_drift_bonus` (capped +0.1, best-effort, lazy-imported to avoid circular). ~30 tests.

**Non-negotiables:** Stdlib-only regression (no numpy dep). Signed drift_pct (direction matters). Sparse summary acceptable for cross-recording. 5%/30d threshold calibrated to O2 aging. Predictor bonus capped + best-effort + frozen-model-safe via `model_copy`. Lazy cross-module import avoids circular. Unicode blocks inline (not via Textual Phase 143). Wide-format CSV Excel-friendly.

**Test plan ~30:** TestComputeTrend (8), TestDetectDriftingPids (6), TestSummary (6), TestDriftCLI (10).

**Dependencies:** Phase 142 hard (sensor_recordings+samples+indexes). Phase 148 hard (FailurePrediction model + advanced group). Phase 143 — copy 8-char tuple only, no import. Phase 141 PID_CATALOG best-effort.

**Next:** Builder-158 agent-delegated. Architect trust-but-verify + Phase 148/142 regression.

### 2026-04-18 19:48 — Build complete (Builder-158 + Architect trust-but-verify)

Phase 158 shipped. `advanced/drift.py` 597 LoC + `cli/advanced.py` +540 LoC drift subgroup + `predictor.py` +90 LoC drift-bonus hook + 39 tests.

### 2026-04-18 19:50 — Bug fix #1: `_normalize_pid_hex` missing zero-pad

**Issue:** `test_pid_hex_normalization` failed. `compute_trend(vid, "5")` returned None because normalized query used `"0x5"` but sensor_samples stores canonical `"0x05"`.

**Fix:** `_normalize_pid_hex` changed `body.upper()` → `body.upper().zfill(2)`. One-line fix.

**Files:** `src/motodiag/advanced/drift.py:156`.

**Verified:** 39/39 tests GREEN in 10.23s.
