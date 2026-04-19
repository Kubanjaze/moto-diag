# MotoDiag Phase 157 — Performance Baselining

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-19

## Goal

Tenth Track F phase. Derive canonical "healthy baseline" profile per (make, model_pattern, year_range, pid_hex, operating_state). Mechanics flag known-good recordings as exemplars; Phase 157 aggregates into reusable profile (min/median/max per PID per operating state). Phase 156 comparative queries can then hit one baseline row instead of peer-by-peer scans.

CLI: `motodiag advanced baseline {show, flag-healthy, rebuild, list}`.

No AI, no tokens. Migration 024 (next available).

Outputs:
- Migration 024: `performance_baselines` (make + model_pattern SQL LIKE + year_min/max + pid_hex + operating_state CHECK in ('idle','2500rpm','redline') + expected_min/max/median + sample_count + last_rebuilt_at + confidence_1to5 CHECK 1-5 + CHECK min≤median≤max) + `baseline_exemplars` (vehicle_id FK SET NULL, recording_id FK CASCADE UNIQUE, flagged_at, flagged_by_user_id FK SET DEFAULT). 2 indexes.
- `advanced/baseline.py` (~280 LoC): `BaselineProfile` + `OperatingState` Pydantic models; `flag_recording_as_healthy(recording_id)` (validates stopped_at NOT NULL, vehicle_id NOT NULL, idempotent via UNIQUE, auto-rebuild); `rebuild_baseline(make, model_pattern, year_min, year_max)` (aggregate 5/50/95 percentiles via `statistics.quantiles(n=20)`; confidence_1to5 from exemplar count thresholds 3/6/11/26 → 1/2/3/4/5); `get_baseline(make, model, year, pid_hex, operating_state)` (narrowest year band wins tiebreak); `_detect_operating_state(rpm_readings)` classifies RPM traces (`idle` <1200 stable >3s, `2500rpm` 2000-4000 stable >3s, `redline` >7000 stable >1s; else unclassified).
- `advanced/__init__.py` +4 LoC exports.
- `cli/advanced.py` +~250 LoC: `baseline` subgroup (show/flag-healthy/rebuild/list). Rich Table per command with confidence ramp (1→cyan, 5→cyan-bright). `flag-healthy` confirm prompt unless `--yes`. Auto-rebuild after flag.
- `tests/test_phase157_baseline.py` (~30 tests, 4 classes).

## Key Concepts

- Two-table split: aggregate (performance_baselines) + provenance (baseline_exemplars) — mirrors Phase 145 obd_adapters + compat_notes.
- Three canonical operating states: idle / 2500rpm / redline. Service-manual reference points.
- 5/50/95 percentile band trims outliers without full-distribution loss.
- Confidence from exemplar count (not sample count) — 100k samples from 1 bike is still 1-bike data.
- Auto-rebuild on flag (mechanic doesn't have to remember); explicit `rebuild` for broader sweeps.
- Stdlib statistics only (`statistics.quantiles` + `bisect` fallback at n<20).
- Phase 142 transparent JSONL merge used via `RecordingManager.load_recording`.
- Phase 156 consumer: `get_baseline` called instead of N-way peer scan.

## Verification Checklist

- [x] Migration 024 + 2 indexes + 3 CHECK constraints + rollback child-first.
- [x] `operating_state` CHECK rejects invalid enum values.
- [x] `UNIQUE(recording_id)` on exemplars (idempotent flag).
- [x] FK CASCADE on recording_id delete; SET NULL on vehicle_id.
- [x] `_detect_operating_state` returns ordered spans on synthetic mixed-trace.
- [x] `flag_recording_as_healthy` rejects in-progress + dealer-lot (vehicle_id NULL).
- [x] `rebuild_baseline` confidence map 1/2/3/4/5 matches 0/3/6/11/26 exemplar thresholds.
- [x] `get_baseline` narrowest-year tiebreak.
- [x] 5/50/95 percentile math on synthetic values.
- [x] Stale-row DELETE before INSERT atomic.
- [x] CLI 4 subcommands + `--json` round-trip + `--yes` skip confirm + Phase 125 remediation.
- [x] Phase 142 + Phase 148 regressions green.

## Risks

- Migration slot race (next integer at build).
- Phase 156 not merged first — no code dep; function signature pinned, integration zero-refactor when 156 lands.
- `model_pattern` wildcard collision (CBR% + CBR600RR both match same bike) — narrowest-year-band tiebreak + confidence sort handles.
- Electric bikes no 0x0C RPM — `_detect_operating_state` returns all-unclassified; `rebuild_baseline` skips. Phase 158+ motor-kW states.
- Sparse-SQLite+JSONL merge tested via artificially-spilled 1500-sample recording.
- Percentile approximation imprecise <20 samples — bisect fallback.
- Cross-model exemplar mismatch → 0 matches, yellow panel, no crash.
- Concurrent rebuilds serialized by SQLite; last-writer-wins on aggregate row.

## Deviations from Plan

- Test count 31 vs ~30 target — one extra test for `_detect_operating_state` on single-sample RPM traces (unclassified guard).
- Zero bug fixes needed on first pytest run.

## Results

| Metric | Value |
|--------|-------|
| Tests | 31 GREEN |
| LoC delivered | ~530 (baseline.py ~280 + cli/advanced.py +~250) |
| Bug fixes | 0 |
| Commit | `68f65f4` |

Phase 157 delivers per-(make, model, year-band, PID, operating-state) healthy baselines aggregated from mechanic-flagged exemplar recordings. Phase 156 can now hit one baseline row instead of scanning N peers, and operating-state auto-classification (idle / 2500rpm / redline) trims the RPM-dependent noise that was confounding peer comparisons.
