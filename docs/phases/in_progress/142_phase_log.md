# MotoDiag Phase 142 — Phase Log

**Status:** 🟡 Planned | **Started:** 2026-04-18 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-18 09:30 — Plan written, v1.0

Planner-142 drafted v1.0 for Phase 142 — data logging + recording. Third Track E phase. Turns Phase 141's ephemeral sensor stream into durable recordings a mechanic can replay, diff across visits, and export.

**The user story:** mechanic on a bike that "runs hot at idle NOW" wants to compare today's coolant trace to the one from 3 months ago. Without Phase 142, Phase 141 stream is throwaway.

**Scope:**
- New `motodiag hardware log` subgroup with 8 subcommands: start, stop, list, show, replay, diff, export, prune. Registered via new `register_log(hardware_group)` sub-function inside `cli/hardware.py` — additive only.
- New `src/motodiag/hardware/recorder.py` (~350 LoC): `RecordingManager` CRUD, flush policy (1s or 100 samples), SQLite/JSONL split at 1000 rows, transparent `load_recording` merge, `DiffReport` with linear-interp alignment.
- Migration 016 (schema v15 → v16): `sensor_recordings` + `sensor_samples` tables, 4 indexes, nullable vehicle_id (dealer-lot).
- Optional `parquet` pip extra (pyarrow ≥15.0).
- ~50 tests across 5 classes. Zero live hardware, zero tokens.

**Design non-negotiables:**
1. **SQLite + JSONL split at 1000 rows.** Multi-hour recordings at 5 Hz × 10 PIDs would bloat DB to hundreds of MB. JSONL sidecar under `~/.motodiag/recordings/<uuid>.jsonl` handles tail; transparent merge in load.
2. **Vehicle FK nullable** — dealer-lot scenario.
3. **CSV export is wide format** — Excel-friendly.
4. **Flush every 1s or 100 samples** — ≤1s crash loss.
5. **No live hardware in tests** — synthetic SensorReading dataclasses defined locally + MockAdapter.
6. **Rich UX matches Phase 140** — `[MOCK]` badge, `ICON_*`, Phase 125/127 remediation patterns.
7. **`cli/hardware.py` additive only** — shared with 141/143/144/145.

**Phase 141 dependency:** imports `SensorReading`, `SensorStreamer`, PID catalog from `motodiag.hardware.sensors`. Single adaptation: `_reading_to_sample_row(reading) -> dict`. Tests use local synthetic dataclasses — API-drift-proof.

**Phase 143 + 144 downstream:** dashboard historical playback; simulator scenario-from-recording. Phase 142's schema is their substrate.

**Test plan (50 tests):**
- `TestMigration016` (4): tables + indexes + SCHEMA_VERSION + rollback.
- `TestRecordingManager` (12): start/stop, under-threshold SQLite, over-threshold JSONL spill, transparent merge, concurrent isolation, prune, nullable vehicle_id.
- `TestLogCLI` (20): 8 subcommand happy paths + error edges.
- `TestDiffReport` (8): matched/unmatched, linear-interp alignment, zero-overlap, flag threshold, empty-recording cells.
- `TestReplay` (6): --speed 0 instant, --speed 1 real-time, --speed 10 scaled, Ctrl+C exits 0, --pids filter, time-ordered merge.

All mock `time.sleep` where relevant; zero real serial; zero tokens.

**Next:** build after Phase 141 merges (recorder.py imports sensors.py). Architect trust-but-verify on migration + JSONL spill (highest-risk pieces).
