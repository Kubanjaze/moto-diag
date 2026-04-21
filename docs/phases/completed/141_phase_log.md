# MotoDiag Phase 141 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-18 | **Completed:** 2026-04-18
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-18 09:00 — Plan written, v1.0

Planner-141 drafted v1.0 for Phase 141 — live sensor data streaming. Second user-facing Track E phase. Adds `motodiag hardware stream` — synchronous-loop OBD Mode 01 PID polling with Rich `Live` panel rendering + optional CSV logging per poll cycle.

**Scope:**
- New `src/motodiag/hardware/sensors.py` (~300 LoC): SAE J1979 PID catalog with decode formulas for RPM, coolant, throttle, battery, intake, O2, VSS, MAP, MAF, run-time, fuel level, ambient, engine load, oil temp, timing advance, fuel pressure. `SensorSpec` dataclass, `SensorReading` Pydantic v2 model, `SensorStreamer` one-shot generator class, `parse_pid_list` helper.
- Extended `cli/hardware.py` (~250 LoC added): one new `stream` subcommand + 3 helpers (`_run_stream`, `_render_stream_panel`, `_StreamCsvWriter`). Existing scan/clear/info byte-identical.
- Extended `hardware/mock.py`: one kwarg `pid_values: Optional[dict[int, int]] = None`. Additive — Phase 140 preserved when unset.
- CLI flags: `--port` (required), `--bike`/`--make` mutex, `--baud`, `--timeout`, `--mock`, `--pids` (default starter set `0x0C,0x05,0x11,0x42,0x0F,0x14`), `--hz` (default 2.0, max 10.0 clamped), `--duration` (0=unlimited), `--output` (CSV append path).
- ~40 tests across 5 classes. Zero live hardware, zero tokens, no migration, no AI, no async, no new pyproject deps.

**Design non-negotiables:**
1. **SAE J1979 authoritative** — every decode cites the standard with canonical test vectors.
2. **`read_pid` contract is `Optional[int]`** — adapter does A/B assembly; decoder is pure `(pid, int) -> float`.
3. **Synchronous poll, no async** — `time.sleep(1/hz)` at 2-10 Hz on serial; Ctrl+C trivially handled.
4. **`Live(auto_refresh=False)` + explicit refresh** — visible rate equals `--hz`.
5. **Error taxonomy:** `TimeoutError` → per-cell degraded, keep going. `ConnectionError` / other → red panel + exit 1. `KeyboardInterrupt` → exit 0 with `disconnect()`.
6. **`--hz` clamp at 10 Hz** — ELM327 per-AT overhead makes faster pointless.
7. **`SensorStreamer.iter_readings` one-shot** — second call raises RuntimeError.
8. **MockAdapter `pid_values` additive** — Phase 140 behavior preserved when unset.
9. **CSV format:** `timestamp_utc_iso,elapsed_s,<pid columns>`; header once; append on re-run.

**Test plan (40 tests):**
- `TestSensorCatalog` (8): each key PID decodes J1979 canonical vector; unknown PID raises ValueError.
- `TestSensorReading` (4): Pydantic round-trip, ISO UTC, pid_hex uppercase, status-value coherence.
- `TestSensorStreamer` (8): happy path, unsupported → None, TimeoutError caught, ConnectionError re-raises, hz throttle via injected sleep, custom clock, one-shot, non-catalog PID.
- `TestStreamCommand` (13-15): happy path, default starter set, --pids override, empty/OOR/garbage rejected, hz 0/neg/>10, CSV header+rows, append no dup header, unsupported em-dash, ECU silence red panel, Ctrl+C, --help.
- `TestMockAdapterExtension` (5): pid_values happy, missing key None, overrides legacy, None preserves, defensive copy.

**File-overlap non-negotiables:**
- `cli/hardware.py` shared with 142/143/144/145. Additive only. No refactors.
- `hardware/mock.py` shared with Phase 144. One kwarg, one new branch. Existing methods untouched.

**Next:** build — dispatch to Builder-141 after coordination with 142/144 (Wave 1 — independent files). Medium complexity (~900 LoC across 1 new + 2 extended files + ~40 tests).

### 2026-04-18 13:15 — Build complete (Builder-141 + Architect trust-but-verify)

Eleventh agent-delegated phase. Builder-141 shipped the spec: new `src/motodiag/hardware/sensors.py` (617 LoC — overshot ~300 LoC target per CLAUDE.md "detailed and meticulous" standard, all extra is docstring + SAE J1979 citations + design-decision notes), extended `cli/hardware.py` (+~400 LoC additive — new `stream` subcommand + `_run_stream`/`_render_stream_panel`/`_StreamCsvWriter` helpers), extended `hardware/mock.py` (+34 LoC — one `pid_values: Optional[dict[int, int]] = None` kwarg + one branch in `read_pid`), new `tests/test_phase141_stream.py` (724 LoC, 42 tests across 6 classes).

Sandbox blocked Python for Builder — Architect ran trust-but-verify.

**Test run: 42 tests, initial 1 failure, fixed, now 42/42 passing.**

### 2026-04-18 13:20 — Bug fix #1: hz-throttle test expectation

**Issue:** `test_hz_throttle_calls_sleep_with_reciprocal` failed with `AssertionError: assert 1 == 2`. Test called `next(gen)` twice and expected 2 sleep calls.

**Root cause:** SensorStreamer's contract (per spec) sleeps AFTER each yield — so after the 2nd `next()` returns tick 2's readings, only 1 sleep has fired (between yield 1 and the work for yield 2). The 2nd sleep fires AFTER yield 2 but only when the consumer calls `next()` a 3rd time, forcing the generator's loop body to resume and sleep.

**Fix:** Added a 3rd `next(gen)` call to trigger the 2nd sleep. Test assertion `call_count == 2` remains correct. Updated inline comment explaining generator + post-yield sleep semantics.

**Files:** `tests/test_phase141_stream.py` lines 311-314.

**Verified:** `pytest tests/test_phase141_stream.py::TestSensorStreamer -v` → 8/8 passing.

### 2026-04-18 13:30 — Build-complete sign-off

42/42 phase tests passing locally. Additive-only changes verified (`git diff` on `cli/hardware.py` and `mock.py` show additions only — Phase 140 `_run_scan`/`_run_clear`/`_run_info` and existing mock kwargs untouched). Zero live tokens, no migration.

Deviations from plan v1.0:
1. LoC overshot on sensors.py (617 vs ~300 target) and cli/hardware.py (+400 vs ~250 target). Every extra LoC is docstring/inline rationale — zero logic padding. Judged as "detailed and meticulous" quality bar.
2. `status` field uses Pydantic v2 `Literal[...]` natively; separate vocabulary validator removed as redundant.
3. `_StreamCsvWriter.write_row(readings, elapsed_s)` takes elapsed monotonic clock as arg rather than recomputing from `captured_at` — avoids sub-ms drift accumulation.
4. Empty placeholder panel rendered before first tick to prevent Rich Live flicker.
5. Title augmented with `• elapsed {elapsed_s:.1f}s` so mechanics see clock running between ticks.

**Next:** finalize to v1.1 + move to `completed/` + update project implementation.md + ROADMAP.md.
