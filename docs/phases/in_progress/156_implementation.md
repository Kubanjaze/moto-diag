# MotoDiag Phase 156 — Comparative Diagnostics (Peer-Cohort Anomaly Detection)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-18

## Goal

Ninth Track F phase. Spot anomalies by comparing one bike's recorded sensor data against peer recordings. Mechanic's 2015 Road Glide at 112°C coolant idle → Phase 156 looks up 20 other 2015 Road Glide recordings in `sensor_recordings` (Phase 142), computes peer median/p25/p75/p95, reports "p95 hottest; peer median 92°C, p75 98°C — likely cooling-system issue".

No AI, no migration, no tokens. Pure SQL on Phase 142 tables + `statistics` stdlib.

CLI: `motodiag advanced compare {bike, recording, fleet}`.

Outputs:
- `advanced/comparative.py` (~300 LoC): `find_peer_recordings(vehicle, cohort_filter, db_path, target_recording_id)`, `compute_peer_stats(peer_ids, pid_hex, metric)`, `compare_against_peers(...)`, `PeerStats` + `PeerComparison` frozen dataclasses.
- `advanced/__init__.py` +3 LoC exports.
- `cli/advanced.py` +~250 LoC: `compare` subgroup. 3 subcommands.
- `tests/test_phase156_comparative.py` (~28 tests, 4 classes).

No migration. No tables.

## Logic

**Cohort modes** (`--cohort`):
- `same-model` (DEFAULT): make + model match + year ±1.
- `strict`: + exact year + same protocol_name.
- `fleet`: vehicle_id IN fleet_memberships (Phase 150 feature-detect via sqlite_master; yellow panel when absent).

**Target always excluded** (by recording_id or vehicle_id).

**Two-stage reduction**: per-recording summary (avg/max/p95 via `--metric`) → percentile-across-recordings (p25/p50/p75/p95 via `statistics.quantiles` stdlib).

**`--peers-min 5`** (default): below threshold → yellow "insufficient cohort" panel, no garbage stats.

**200-row cohort cap** (`LIMIT 200`): keeps math cheap.

**pid_hex normalization**: canonical `"0x05"` via 3-line inline helper (no cross-module coupling).

**Percentile bucketing**: target → `<p25` / `p25-p50` / `p50-p75` / `p75-p95` / `>=p95`. `anomaly_flag = True` when in tails.

**Phase 150 graceful absence**: `--cohort fleet` feature-detects `fleet_memberships` table; yellow "Phase 150 required" panel when absent.

## Verification Checklist

- [ ] `compare bike` returns non-None peer stats when ≥5 same-model peers.
- [ ] `<5 peers` → "insufficient cohort" yellow + exit 0.
- [ ] `compare recording <id>` end-to-end.
- [ ] `--cohort strict` narrows to exact year + protocol.
- [ ] `--cohort fleet` without Phase 150 table → yellow panel + exit 0.
- [ ] Target excluded from peer set (assertion).
- [ ] Orphan recording (vehicle_id NULL) → yellow panel + exit 1.
- [ ] `--pid 0x5` / `05` / `5` / `0x05` all canonical `"0x05"`.
- [ ] Unknown bike → Phase 125 remediation.
- [ ] Bucket at boundary: target == p95 → `">=p95"`.
- [ ] `anomaly_flag=True` at tails.
- [ ] `--json` round-trip.
- [ ] `distinct_bikes` count in payload distinct from `cohort.size`.
- [ ] LIMIT 200 honored on synthetic 300-recording cohort.
- [ ] Phase 148 + Phase 142 regressions green.

## Risks

- Cohort size tiny for non-Harley bikes; warning panel + hint.
- Sparse-summary bias on JSONL-spilled recordings (1-in-100 summary retained in SQLite is acceptable for peer percentile comparison — we're aggregating across recordings, not within).
- Protocol drift (K-line vs CAN) — `--cohort strict` filters; default accepts mix + footer note.
- Unit mismatches free-text — first-non-empty; Phase 141 normalizes units in practice.
- Percentile math on n<5 handled via `statistics.quantiles` inclusive method + `--peers-min` guard.
- `cli/advanced.py` growth (~530 LoC) acceptable; extraction option documented.
- Phase 150 fleet branch tested via monkeypatched True path + documented False path.
