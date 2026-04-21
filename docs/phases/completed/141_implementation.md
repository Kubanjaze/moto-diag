# MotoDiag Phase 141 — Live Sensor Data Streaming

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-18

## Goal

Second user-facing Track E phase. Adds `motodiag hardware stream` — polls OBD Mode 01 PIDs on a synchronous loop and renders a live-updating Rich `Live` panel. Before this phase, Mode 01 was library-only; after, a mechanic with a running bike can watch RPM / coolant / throttle / battery / intake / O2 voltage refresh in real-time from the CLI. Optional CSV logging per poll cycle.

CLI: `motodiag hardware stream --port COM3 [--bike SLUG | --make MAKE] [--baud N] [--timeout 2.0] [--mock] [--pids 0x0C,0x05,0x11,0x42,0x0F,0x14] [--hz 2.0] [--duration 0] [--output PATH]`

Outputs:
- `src/motodiag/hardware/sensors.py` (~300 LoC) — `SENSOR_CATALOG` with SAE J1979 decode formulas, `SensorSpec` dataclass, `SensorReading` Pydantic v2 model, `SensorStreamer` one-shot generator, `parse_pid_list` helper, `decode_pid` helper.
- `src/motodiag/cli/hardware.py` +~250 LoC (stream subcommand, `_run_stream`, `_render_stream_panel`, `_StreamCsvWriter`). **Additive only** — Phase 140's scan/clear/info bodies byte-identical.
- `src/motodiag/hardware/mock.py` +1 kwarg (`pid_values: Optional[dict[int, int]] = None`). Additive — Phase 140 behavior preserved when unset.
- `tests/test_phase141_stream.py` (~750 LoC, ~40 tests across 5 classes).

No migration, no new DB tables, no AI, no async, no new pyproject deps.

## Logic

### `SENSOR_CATALOG` (SAE J1979 authoritative)

| PID | Name | Bytes | Formula (on assembled int raw=A or raw=(A<<8)|B) | Unit |
|---|---|---|---|---|
| 0x04 | Calculated engine load | 1 | `raw * 100 / 255` | `%` |
| 0x05 | Engine coolant temperature | 1 | `raw - 40` | `°C` |
| 0x0A | Fuel rail pressure (gauge) | 1 | `raw * 3` | `kPa` |
| 0x0B | Intake manifold absolute pressure | 1 | `raw` | `kPa` |
| 0x0C | Engine RPM | 2 | `raw / 4` | `rpm` |
| 0x0D | Vehicle speed | 1 | `raw` | `km/h` |
| 0x0E | Timing advance | 1 | `raw / 2 - 64` | `° BTDC` |
| 0x0F | Intake air temperature | 1 | `raw - 40` | `°C` |
| 0x10 | MAF air flow rate | 2 | `raw / 100` | `g/s` |
| 0x11 | Throttle position | 1 | `raw * 100 / 255` | `%` |
| 0x14–0x1B | O2 sensor voltage (8 PIDs) | 2 | `(raw >> 8) / 200` | `V` (STFT in lower byte deferred) |
| 0x1F | Run time since engine start | 2 | `raw` | `s` |
| 0x2F | Fuel tank level | 1 | `raw * 100 / 255` | `%` |
| 0x42 | Control module voltage (battery) | 2 | `raw / 1000` | `V` |
| 0x46 | Ambient air temperature | 1 | `raw - 40` | `°C` |
| 0x5C | Engine oil temperature | 1 | `raw - 40` | `°C` |

`read_pid` per Phase 134 ABC returns `Optional[int]` already assembled — decoder operates on the int. Every decode returns float. Canonical test vectors: RPM 0x1AF8→1726, coolant 0x5A→50°C, battery 0x3600→13.824V, O2 0x5AB0→0.45V, throttle 0xFF→100%.

### `SensorReading` (Pydantic v2 BaseModel)

Fields: `pid: int` (0-255), `pid_hex: str` (uppercase `^0x[0-9A-F]{2}$`), `name: str`, `value: Optional[float]`, `unit: str`, `raw: Optional[int]`, `captured_at: datetime`, `status: Literal["ok", "unsupported", "timeout"]`. Validator enforces: `value is None` iff `status != "ok"`.

### `SensorStreamer`

Constructor: `(adapter, pids, hz=2.0, sleep=time.sleep, clock=lambda: datetime.now(timezone.utc))`. `iter_readings() -> Iterator[list[SensorReading]]`. One-shot: second call to `iter_readings` raises `RuntimeError("one-shot")`.

Per-tick: for each PID, call `adapter.read_pid(pid)`:
- Returns `None` → status=unsupported, value=None, raw=None.
- Raises `TimeoutError` → status=timeout, value=None, raw=None. **Do not re-raise** — next tick retries.
- Returns int → decode via catalog → status=ok.
- Any other `ProtocolError` → **re-raises** immediately (loop stops, CLI renders red panel).
- Unknown PID (not in catalog) → status=unsupported, name=f"PID 0x{pid:02X}", unit="".

Yield the list, then `sleep(1/hz)`.

### `parse_pid_list(spec)`

Accepts `"0x0C,0x05,17,0x42"` — mixed hex/decimal. Trims whitespace. Rejects: empty, non-parsable, out-of-range (0-255), with ClickException naming the bad token. Dedupes preserving first-seen order.

### `cli/hardware.py` `stream` subcommand

Flow in `_run_stream`:
1. Validate `--hz`: `<=0` rejected; `>10.0` clamped with yellow warning panel.
2. If `--output`, create `_StreamCsvWriter(output_path, pids)` up-front (surface path errors before opening serial).
3. Open `HardwareSession(port, make_hint, baud, timeout_s, mock)`. On `NoECUDetectedError` → red panel + exit 1.
4. Print `[MOCK] ✓ Connected on PORT via PROTOCOL` header.
5. `Live(panel, auto_refresh=False)` loop over `SensorStreamer.iter_readings()`:
   - Each tick: update panel, `live.refresh()`, optional CSV row.
   - `--duration > 0` and elapsed >= duration → break.
   - `KeyboardInterrupt` → break (clean exit 0).
   - `ProtocolError` → red "ECU went silent" panel + exit 1.
6. Footer: `Polled N cycles in T.TTs.`
7. `HardwareSession.__exit__` disconnects.

Rendering: Table columns `PID / Name / Value / Unit` — ok cell uses `f"{value:g}"`; unsupported → dim em-dash `—`; timeout → yellow `timeout`. Panel title `Live sensors ({hz:g} Hz)` with `[MOCK]` yellow badge prefix when mock.

`_StreamCsvWriter`: opens `"a"` mode, writes header on new file (`timestamp_utc_iso,elapsed_s,<pid columns>`), data row is `captured_at.isoformat()` + `f"{elapsed_s:.3f}"` + per-PID `f"{value:.6g}"` (empty string on timeout/unsupported). UTF-8, `newline=""`.

### `MockAdapter` extension (hardware/mock.py)

One new constructor kwarg `pid_values: Optional[dict[int, int]] = None`. `read_pid(pid)` gets new top branch:
```python
if self._pid_values is not None:
    return self._pid_values.get(pid)
if pid in self._supported_modes:
    return pid * 10
return None
```
Defensive-copy on construction. Phase 140 behavior preserved when unset.

## Key Concepts

- **SAE J1979 is the authoritative PID catalog.** Every decode formula cites the standard. Canonical test vectors lock decoder correctness.
- **`read_pid` returns pre-assembled int per Phase 134 ABC.** Adapter handles `(A << 8) | B`; decoder is pure `(pid, int) -> float`.
- **Synchronous poll loop, not async.** `time.sleep(1/hz)` is fine for 2-10 Hz on serial hardware. `KeyboardInterrupt` trivially handled. Async would complicate Ctrl+C without buying anything.
- **`Live(auto_refresh=False)` + explicit refresh** — visible refresh rate equals `--hz`, not Rich's default 4 Hz.
- **`SensorStreamer.iter_readings` is one-shot.** Holds adapter state; mixing iterations would corrupt CSV row ordering.
- **Error taxonomy:** `TimeoutError` → per-cell degraded state, keep going. `ConnectionError` / other `ProtocolError` → red panel, exit 1. `KeyboardInterrupt` → exit 0 with `disconnect()` via `__exit__`.
- **`--hz` clamp at 10 Hz.** ELM327 adapters have 50-100 ms per-AT-command overhead; faster is pointless. Clamp + yellow warning.
- **MockAdapter `pid_values` is additive test DX.** `MockAdapter(pid_values={0x0C: 0x1AF8, 0x05: 0x5A})` reads like a fixture.

## Verification Checklist

- [x] `sensors.py` created with catalog, `SensorSpec`, `SensorReading`, `SensorStreamer`, `decode_pid`, `parse_pid_list`.
- [x] Catalog has entries for PIDs 0x04, 0x05, 0x0A-0x11, 0x14-0x1B, 0x1F, 0x2F, 0x42, 0x46, 0x5C.
- [x] 8 canonical J1979 test vectors pass.
- [x] `SensorReading` Pydantic v2 with validator enforcing pid_hex uppercase + status-value coherence.
- [x] `SensorStreamer.iter_readings` one-shot (second call raises).
- [x] `TimeoutError` mid-stream → status=timeout reading, next tick retries; does NOT re-raise.
- [x] `ConnectionError` mid-stream re-raises (loop stops).
- [x] `hz` throttle calls injected `sleep` with `1/hz`.
- [x] `parse_pid_list` accepts mixed hex/decimal; rejects empty/garbage/out-of-range.
- [x] `MockAdapter(pid_values=...)` returns configured value or None; `pid_values=None` preserves Phase 140 behavior.
- [x] `stream --mock --duration 1 --hz 2` prints 6-row default table, exits 0.
- [x] `stream --mock --pids 0x0C,0x42` prints exactly 2 rows.
- [x] `--hz 0` rejected; `--hz 20` clamped + yellow warning.
- [x] `--output` CSV has header once + rows; re-run appends without duplicate header.
- [x] Unsupported PID shown as `—`; ECU silence → red panel + exit 1.
- [x] Ctrl+C exits 0 with `disconnect()` called.
- [x] ~40 tests in `test_phase141_stream.py`; zero live hardware; zero tokens.
- [x] All Phase 140 tests still pass.

## Risks

- **FILE-OVERLAP `cli/hardware.py`:** shared with Phases 142 (log), 143 (dashboard), 144 (simulator), 145 (compat). **Strictly additive** — add new subcommand + 3 helpers; do NOT refactor existing `_run_scan`/`_run_clear`/`_run_info`. `git diff` should be additions only.
- **FILE-OVERLAP `hardware/mock.py`:** Phase 144 simulator further extends. One new kwarg + one branch in `read_pid` — additive only. `identify_info()`, `_DEFAULT_*` constants, and other methods untouched.
- **O2 voltage lower-byte STFT omitted in v1.** Voltage only. Future phase can add secondary_value/secondary_unit pair.
- **Motorcycle-specific PID support is spotty.** Harleys may not support 0x42; streamer handles None correctly (shows em-dash). Not a bug.
- **ELM327 latency ceiling.** 10 Hz clamp calibrated for ELM327 50-100 ms per-AT overhead. Native CAN could sustain 30+ Hz but Phase 141 uses safe ceiling.
- **`Live` + Ctrl+C cursor restoration** verified in Rich ≥ 13; Phase 129 pinned. Don't bump.
- **Deterministic test clock.** `SensorStreamer(sleep=Mock(), clock=lambda: FIXED_UTC)` kwargs exist specifically for testability.
- **`--pids` default excludes VSS (0x0D)** — dyno has wheel turning but frame stationary. Documented in help.
- **Pydantic v2** — project uses v2 idioms (`@field_validator`). Builder should verify via pyproject pin.

## Deviations from Plan

1. **LoC overshot on `sensors.py`** (617 vs ~300 target) and `cli/hardware.py` (+400 vs ~250 target). Every extra LoC is docstring, inline rationale, or SAE J1979 citation — zero logic padding. Judged against the "detailed and meticulous" quality bar.
2. **`status` field uses Pydantic v2 `Literal[...]` natively** — separate vocabulary validator removed as redundant once `Literal["ok", "unsupported", "timeout"]` captured the enum at the type layer.
3. **`_StreamCsvWriter.write_row(readings, elapsed_s)` takes elapsed monotonic clock as arg** rather than recomputing from `captured_at` — avoids sub-millisecond drift accumulation across long recording sessions.
4. **Empty placeholder panel rendered before first tick** to prevent Rich Live flicker on cold start.
5. **Panel title augmented with `• elapsed {elapsed_s:.1f}s`** so mechanics see the clock running between ticks even when values haven't changed yet.
6. **Bug fix #1 (hz-throttle test expectation):** `test_hz_throttle_calls_sleep_with_reciprocal` originally expected 2 sleep calls after 2 `next()` invocations. Corrected to 3 `next()` calls — `SensorStreamer` is a generator that sleeps AFTER each yield, so N `next()` invocations trigger N-1 sleeps. Inline comment added explaining generator + post-yield sleep semantics.

## Results

| Metric | Value |
|--------|------:|
| New files | 2 (`src/motodiag/hardware/sensors.py` 617 LoC, `tests/test_phase141_stream.py` 724 LoC) |
| Modified files | 2 (`cli/hardware.py` +~400 LoC additive, `hardware/mock.py` +34 LoC one kwarg) |
| New tests | 42 across 6 classes (passed locally 42/42) |
| Total test count after | 2614 |
| Live API tokens burned | 0 |
| Bug fixes during build | 1 (hz-throttle test expectation) |

**Commit:** `4943db1` (Wave 1+2: Phase 141 shipped — sensor streaming + Phase 144 partial + Phase 142/145 code landed).

**Key finding:** Phase 141 turned the Track E hardware stack from library-only into a mechanic's live diagnostic tool — `motodiag hardware stream --port COM3 --pids 0x0C,0x05,0x11,0x42` is the first phase where a mechanic can actually watch RPM / coolant / throttle / battery refresh in real-time from the CLI. The `SensorStreamer(sleep=Mock(), clock=lambda: FIXED_UTC)` test-DX decision (inject both time sources via constructor kwargs) became the template Phases 142 / 143 / 144 adopted for their own deterministic time-based tests across the remainder of Track E.
