# MotoDiag Phase 142 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-18 | **Completed:** 2026-04-18
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

### 2026-04-18 14:30 — Build complete (Builder-142 + Architect trust-but-verify)

Thirteenth agent-delegated phase. Builder-142 shipped the spec: new `src/motodiag/hardware/recorder.py` (864 LoC — overshot ~350 LoC target per "detailed and meticulous" quality bar; RecordingManager with SQLite/JSONL split at 1000 rows, linear-interp `DiffReport` via stdlib `bisect`, transparent load-recording merge with `(captured_at, pid_hex, raw)` signature dedup), extended `cli/hardware.py` (+~1300 LoC — new `register_log` subgroup with 8 subcommands), migration 016 (`sensor_recordings` + `sensor_samples` + 4 indexes with FK CASCADE, child-first rollback), extended `pyproject.toml` (parquet optional extra), new `tests/test_phase142_log.py` (1217 LoC, 52 tests across 5 classes).

`hardware/mock.py`, Phase 140 scan/clear/info bodies, Phase 141 stream subcommand — all byte-untouched.

Sandbox blocked Python for Builder-142 AND Builder-142-Fix. Architect ran trust-but-verify as Phase 125 discipline documents.

### 2026-04-18 14:35 — Trust-but-verify: test suite GREEN 52/52

**Run:** `.venv/Scripts/python.exe -m pytest tests/test_phase142_log.py -q` → `52 passed in 24.21s`.

No bug fixes needed. Builder-142-Fix's static analysis was accurate:
- Phase 141 `SensorReading` contract alignment via `_reading_to_sample_row` duck-type (attribute-access + dict fallback) — works correctly for real Pydantic model AND test synthetic dataclass.
- SQLite/JSONL split at 1000 rows traces correctly: under-1000 → all SQLite file_ref=NULL; over-1000 → 5 sparse summary rows (every 100th) + JSONL sidecar; merge dedup via `(captured_at, pid_hex, raw)` signature.
- Migration 016 in place at `migrations.py:1017-1087` with proper FK CASCADE + child-first rollback.
- Replay speed=0 bypasses `time.sleep` via `if speed > 0` gate; speed=1/10 scales correctly.
- Parquet lazy-import with install-hint ClickException.

**Build-complete sign-off:** Phase 142 moves from YELLOW → GREEN. Docs ready to finalize to v1.1 + move to `completed/`.

**Next:** finalize docs + commit as own `Phase 142 Verified` entry + push.
