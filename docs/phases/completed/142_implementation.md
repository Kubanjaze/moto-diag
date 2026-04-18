# MotoDiag Phase 142 — Data Logging + Recording

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-18

## Goal

Turn Phase 141's ephemeral sensor stream into persistent recordings a mechanic can replay, diff across visits, and export. Solves "bike is running hot at idle NOW — was it last oil change?". Start recording with `motodiag hardware log start`, do the diagnostic work, `log stop`, then `log diff`, `log replay`, or `log export` into Excel/Parquet.

CLI subgroup `motodiag hardware log`:
- `log start --port COM3 [--bike SLUG | --make MAKE] [--label TEXT] [--pids CSV] [--interval 0.5] [--duration N] [--notes TEXT] [--baud N] [--timeout 2.0] [--mock] [--background]`
- `log stop RECORDING_ID [--force]`
- `log list [--bike SLUG] [--since DATE] [--until DATE] [--limit 50]`
- `log show RECORDING_ID`
- `log replay RECORDING_ID [--speed 1.0] [--pids CSV]`
- `log diff ID1 ID2 [--metric avg|min|max]`
- `log export RECORDING_ID [--format csv|json|parquet] [--output PATH]`
- `log prune [--older-than 30] [--yes]`

Outputs:
- Migration 016 (schema v15 → v16): `sensor_recordings` + `sensor_samples` tables + 4 indexes.
- `src/motodiag/hardware/recorder.py` (~350 LoC) — `RecordingManager` CRUD, SQLite/JSONL split, `load_recording` transparent merge, `DiffReport` with linear-interp alignment.
- `src/motodiag/cli/hardware.py` +~400 LoC (`register_log(hardware_group)` + 8 subcommands). Additive only.
- `pyproject.toml` +3 LoC (new `parquet = ["pyarrow>=15.0"]` optional extra).
- `tests/test_phase142_log.py` (~900 LoC, ~50 tests across 5 classes). Zero live hardware, zero tokens.

## Logic

### Migration 016 — sensor_recordings + sensor_samples

`sensor_recordings`: id PK, vehicle_id INTEGER NULL (FK→vehicles ON DELETE SET NULL — dealer-lot scenario), session_label TEXT, started_at TIMESTAMP NOT NULL, stopped_at TIMESTAMP NULL, protocol_name TEXT NOT NULL, pids_csv TEXT NOT NULL (e.g. `"0C,05,0B"` uppercase, no `0x`), notes TEXT NULL, sample_count INTEGER NOT NULL DEFAULT 0, max_hz REAL NULL, min_hz REAL NULL, file_ref TEXT NULL (relative path to JSONL sidecar), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP.

`sensor_samples`: id PK, recording_id FK CASCADE, captured_at TIMESTAMP NOT NULL (ISO-8601 with ms), pid_hex TEXT NOT NULL, value REAL, raw INTEGER, unit TEXT.

Indexes: `idx_recordings_vehicle`, `idx_recordings_started`, `idx_samples_recording_time` on `(recording_id, captured_at)`, `idx_samples_recording_pid` on `(recording_id, pid_hex)`.

Rollback: `DROP TABLE IF EXISTS sensor_samples; DROP TABLE IF EXISTS sensor_recordings;` (child first).

SCHEMA_VERSION bump 15 → 16 in `core/database.py`.

### SQLite + JSONL split policy (NON-NEGOTIABLE)

Threshold: **1000 rows**. Flush every **1 second or 100 samples**, whichever first.

- Under 1000 rows: all samples in `sensor_samples`. `file_ref = NULL`.
- Above 1000 rows: spill to `~/.motodiag/recordings/<uuid>.jsonl` (lazy-allocated UUID, written to `file_ref` on first spill). `sensor_samples` retains every 100th reading as sparse summary.
- `load_recording` transparently merges SQLite sparse + JSONL full in time order. Consumers never know.
- Crash budget: max 1 second of samples lost.

Rationale: SQLite INSERT performance degrades linearly past ~100k rows. 1-hour recording at 5 Hz × 10 PIDs = 180,000 samples; without split, DB bloats and queries slow.

### RecordingManager API

```python
class RecordingManager:
    def __init__(self, db_path, recordings_dir=Path.home()/".motodiag"/"recordings"): ...
    def start_recording(vehicle_id, label, pids: list[str], protocol_name, notes=None) -> int
    def append_samples(recording_id, readings: list[SensorReading]) -> None  # buffer + flush per policy
    def stop_recording(recording_id, hz_stats=None) -> None
    def load_recording(recording_id) -> tuple[dict, Iterator[SensorReading]]
    def list_recordings(vehicle_id=None, since=None, until=None, limit=50) -> list[dict]
    def prune(older_than_days=None) -> tuple[int, int]  # (rowcount, bytes_freed)
    def diff_recordings(id1, id2, metric="avg") -> DiffReport
```

Buffer guarded by `threading.Lock`. One RecordingManager per process expected.

### DiffReport + linear-interp alignment

```python
@dataclass(frozen=True)
class PIDDiff:
    pid_hex: str
    name: str
    unit: str
    stat_1: float
    stat_2: float
    delta: float
    pct_change: float  # 0.0 when stat_1 == 0
    flagged: bool       # abs(pct_change) > 10.0

@dataclass(frozen=True)
class DiffReport:
    recording_1_id: int
    recording_2_id: int
    matched: list[PIDDiff]
    only_in_1: list[str]
    only_in_2: list[str]
```

Alignment: bucket per-PID values in each recording; `matched = pids_1 ∩ pids_2`; linear-interp resample both series to the shorter session's sample count (stdlib `bisect` + manual interp — no numpy dep). Per-PID compute `min/max/avg`. Flag when `|pct_change| > 10%`.

Edge cases: zero-overlap → empty matched + warning panel + exit 1. Empty recording → stats None, rendered as `—`. `stat_1 == 0` → `pct_change=0.0` (avoid div/0).

### CLI subgroup via `register_log(hardware_group)`

Sub-registration inside `register_hardware`'s body:
```python
def register_log(hardware_group):
    @hardware_group.group("log")
    def log_group(): ...
    @log_group.command("start") ...
    # 7 more
```
Called one line at the bottom of `register_hardware`:
```python
register_log(hardware_group)
```

Rich rendering: `theme.get_console()`, `ICON_OK/WARN/FAIL`, `format_severity`. `[MOCK]` badge when protocol_name is Mock. `init_db()` at top of each subcommand. Test fixture monkey-patches `init_db` → tmp_path.

Background recording uses `threading.Thread(daemon=True)` + DB-polling for stop signal (thread polls `sensor_recordings.stopped_at` every flush). No inter-process signals. True detach deferred.

### Export formats

- **CSV**: wide format — one column per PID. Header `captured_at, pid_0C, pid_05, ...`. Built with `csv.DictWriter`. Mechanics open in Excel.
- **JSON**: `{"metadata": <recording_row>, "samples": [<dicts>]}`.
- **Parquet**: lazy `import pyarrow.pa`; on `ImportError` raise ClickException with install hint. `parquet = ["pyarrow>=15.0"]` optional extra.

### Phase 141 dependency surface

Imports: `SensorReading`, `SensorStreamer`, PID catalog from `motodiag.hardware.sensors`. Single adaptation point: `_reading_to_sample_row(reading) -> dict` — if 141 renames fields, one helper changes. Tests use **synthetic SensorReading-shaped dataclasses defined locally** — decoupled from 141's final API, so test suite survives 141 drift.

## Key Concepts

- **SQLite + JSONL split at 1000 rows** — hot set stays tiny; long-tail streams to disk; transparent merge.
- **Vehicle FK nullable** — dealer-lot pre-sale scenario.
- **CSV is wide format** — Excel-friendly; long format forces pivot-tables.
- **Flush every 1s or 100 samples** — ≤1s data loss on crash.
- **Linear-interp diff alignment** — correct for continuous signals (RPM/temp/MAP); enum PIDs (O2 narrowband) get noisy — documented limitation.
- **10% delta flag threshold** — empirically catches "genuinely hot" without false-alarming on drift.
- **Replay uses wall-clock `time.sleep`** — `--speed 1.0` real-time; `--speed 10` compressed; `--speed 0` instant dump.
- **Parquet optional extra** — pyarrow is 40 MB; not every mechanic needs it.
- **Foundational for Phases 143 + 144** — dashboard historical playback; simulator scenario-from-recording.

## Verification Checklist

- [ ] Migration 016 in MIGRATIONS, version 16.
- [ ] Fresh init_db creates both tables + 4 indexes.
- [ ] SCHEMA_VERSION bumped 15 → 16.
- [ ] rollback_migration(16) drops both.
- [ ] Vehicle_id nullable (dealer-lot); FK=42 invalid raises IntegrityError.
- [ ] Under 1000 rows stay in SQLite; file_ref NULL.
- [ ] Crossing 1000 creates JSONL sidecar; file_ref set; subsequent batches append; sensor_samples grows sparsely.
- [ ] `load_recording` transparent merge yields time-ordered samples.
- [ ] Concurrent recordings' buffers isolated.
- [ ] `prune(30)` removes rows + unlinks JSONL (missing files tolerated).
- [ ] `log start/stop/list/show/replay/diff/export/prune` all work.
- [ ] `--bike MISSING` → Phase 125-style remediation, exit 1.
- [ ] `--bike X --make Y` → ClickException mutex.
- [ ] Ctrl+C in foreground calls stop_recording.
- [ ] `log show MISSING` → clean ClickException.
- [ ] `log replay --speed 0` instant (no sleep — verified via patch).
- [ ] `log replay --speed 1.0` calls `time.sleep` with per-sample deltas.
- [ ] `log replay --speed 10.0` deltas scaled by 1/10.
- [ ] Ctrl+C in replay exits 0.
- [ ] `log diff` fully/partial/zero-overlap all handled.
- [ ] Flag emoji 🔥 at `|pct_change| > 10%`.
- [ ] Diff aligns 200-sample vs 500-sample sessions via linear interp.
- [ ] Export csv/json/parquet; parquet missing-dep → install hint.
- [ ] Export creates parent dir if missing.
- [ ] Export of JSONL-spilled recording = SQLite-only recording (transparent).
- [ ] `log prune` confirm + yes paths.
- [ ] All Track E tests still pass (Phases 134-141).
- [ ] Phase 140's 40 hardware tests pass unchanged.
- [ ] Zero live tokens, zero real serial.

## Risks

- **Phase 141 ships late / different API.** Adapter via `_reading_to_sample_row` shim; tests use local synthetic readings (API-drift-proof).
- **JSONL sidecar orphans** on crash after `file_ref` written but before `stopped_at` set. `prune()` unlinks regardless of row consistency.
- **Linear interp for enum PIDs** makes 10% flag meaningless on O2 narrowband. Documented; Phase 148 may add per-PID `kind=continuous|enum` hints.
- **`cli/hardware.py` contention with 141/143/144/145.** Each adds new `register_<subgroup>(hardware_group)` function, called in `register_hardware`'s body. Append-only merges.
- **Windows file locking** on JSONL during concurrent read. Mitigation: `append_samples` opens-writes-closes each flush (no long-lived handle).
- **`--background` durability** — daemon thread dies with parent. Documented; Phase 147 daemon mode may address. DB-polling stop signal works across processes.
- **Concurrent `append_samples`** from multiple threads on one manager — guarded by `threading.Lock`.
- **Parquet discoverability** — CSV default; parquet hint explicit.
- **Recordings dir on Windows** — `Path.home() / ".motodiag"` for parity with Phase 131.
- **Migration number if Phase 141 adds one** — unlikely, but Builder verifies `MIGRATIONS` before creating 016.
