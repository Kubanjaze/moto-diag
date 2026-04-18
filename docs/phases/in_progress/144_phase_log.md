# MotoDiag Phase 144 — Phase Log

**Status:** 🟡 Planned | **Started:** 2026-04-18 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-18 10:30 — Plan written, v1.0

Planner-144 drafted v1.0 for Phase 144 — hardware simulator. Track E's test-infra substrate. Turn Phase 140's static MockAdapter into a scriptable scenario-driven simulator that drives repeatable CI, replays Phase 142 recordings, and lets mechanics author YAML scenarios from service manuals. **`hardware/mock.py` stays frozen**; simulator is a sibling (not subclass) at `hardware/simulator.py`.

**Scope:**
- New `src/motodiag/hardware/simulator.py` (~500 LoC) — `SimulationClock`, 9 Pydantic event models (StartState/RampPid/InjectDTC/ClearDTC/InjectTimeout/Disconnect/Reconnect/PhaseTransition/EndScenario), `Scenario` aggregate with cross-event validators, `ScenarioLoader` (from_yaml/from_recording/list_builtins/find), `SimulatedAdapter(ProtocolAdapter)` with 8 ABC methods driven by state-fold over timeline at clock.now().
- New `src/motodiag/hardware/scenarios/` package with 10 built-in YAMLs (healthy_idle/cold_start/overheat/misfire/lean_fault/o2_sensor_fail/charging_fault/ecu_crash_recovery/harley_sporty_warmup/cbr600_warm_idle). Mechanic-friendly names matching real diagnostic scenarios.
- CLI new `simulate` subgroup — list/run/validate. Plus `--simulator SCENARIO` opt-in flag on scan/clear/info (mutex with `--mock`). Badge `[SIM: name]` magenta distinct from `[MOCK]` yellow.
- `hardware_group.command("stream")` registers flag if Phase 141 merged; skipped conditionally.
- ~55 tests across 6 classes. Zero `time.sleep` in tests (CI grep enforces).
- New base dep `pyyaml>=6`. Setuptools `package-data` entry for YAMLs.

**Design non-negotiables:**
1. **Determinism.** Same scenario + same clock start = same reads. Manual-tick SimulationClock injected as constructor kwarg; tests never touch wall time.
2. **No real-time in tests.** `time.sleep` count MUST be 0 in test_phase144_simulator.py (CI grep).
3. **YAML mechanic-facing.** No Python required. `simulate validate` is lint gate with YAML line/column + Pydantic logical errors.
4. **Zero live hardware.** Everything simulated end-to-end.
5. **`hardware/mock.py` is frozen.** Production `--mock` stays Phase 140 simple static adapter. Simulator sibling, not subclass. CI diff-check enforces.

**Key design decisions:**
- **Sibling, not subclass.** MockAdapter + SimulatedAdapter both implement ProtocolAdapter directly. ~6 LoC boilerplate duplication acceptable; Phase 140 contract guard stays sharp.
- **State fold per read, not per tick.** Reads pure function of (scenario, t). No mutable cached state.
- **Pydantic discriminated union on `action`.** YAML → typed event with `extra="forbid"`.
- **`importlib.resources` for YAMLs.** Works in wheel, zipapp, editable. Phase 111 pattern.
- **`HardwareSession.adapter_override` integration point** — Phase 140 shipped; verified in `connection.py:82-85`.
- **YAML "from" reserved-word workaround** — `Field(alias="from")` on `RampPid.from_`.
- **PID coercion** — `_coerce_pid` accepts int/hex-int/hex-string/symbolic.

**Test plan (55 tests):**
- `TestSimulationClock` (5) — tick/advance/now, backward rejection, 10k-tick monotonic, reset.
- `TestScenarioModels` (10) — 8 event round-trips + invalid raises + all-10-builtins parse.
- `TestSimulatedAdapter` (15) — initial/mid-ramp/end/pre-ramp, DTC inject/clear/adapter-clear, disconnect/reconnect, timeout window, phase no-op, vin/protocol passthrough, ABC contract instantiates, determinism across constructor repeats.
- `TestBuiltinScenarios` (10) — 1 per YAML, asserts named invariant (zero DTCs for healthy_idle, ≥115°C overheat + P0217, RPM std>50 misfire, etc.). Run under `speed=0` in sub-second wall time.
- `TestScenarioFromRecording` (5) — PID round-trip, VIN preserve, protocol preserve, DTC audit, empty-recording error. **All 5 skip if Phase 142 absent.**
- `TestSimulateCommand` (10) — list/run/validate paths + unknown-scenario + with-log + mutex tests.

**Dependencies flagged:**
- Phase 140 shipped — HardwareSession adapter_override verified.
- Phase 142 soft dep — from_recording guarded, tests skip gracefully.
- Phases 141/143/145 share cli/hardware.py — additive only, no flag-name collisions.
- New base dep `pyyaml>=6` — one-line pyproject change.

**Open questions:**
1. Phase 142 RecordingManager final interface — Builder lifts at build time; one-line shim if method-name mismatch.
2. `pyyaml` base vs `[sim]` extra — plan rules base (simulate validate must just work).
3. PID float-to-int rounding at boundary — documented; architect sign-off requested.
4. Scenario unit convention (native OBD units vs human-readable) — plan chose native per OBD faithfulness.
5. `schema_version: int = 1` in YAMLs for forward-compat — low-risk addition.

**Next:** delegate build to Builder-144 — Wave 1 candidate (independent of 141's cli/hardware.py since 144 adds its own `simulate` subgroup). Parallel with Phase 141. Architect trust-but-verify. Require recording-roundtrip green if Phase 142 landed; graceful-skip path green otherwise.

### 2026-04-18 13:00 — Build complete (Builder-144 + Architect trust-but-verify)

Twelfth agent-delegated phase. Builder-144 shipped: new `src/motodiag/hardware/simulator.py` (1212 LoC — overshot ~500 target due to extensive Pydantic validators + exception context + PID-alias table + duration parser + ScenarioLoader), `scenarios/__init__.py` (59 LoC) + 10 built-in YAML scenarios, extended `cli/hardware.py` (+~630 LoC — new `simulate` subgroup + `--simulator` opt-in on scan/clear/info), extended `pyproject.toml` (added `pyyaml>=6` base dep + `[tool.setuptools.package-data]` entry), new `tests/test_phase144_simulator.py` (939 LoC, 63 test functions + parametrize expansions).

`hardware/mock.py` byte-untouched per CI diff-check requirement.

Sandbox blocked Python for Builder — Architect ran trust-but-verify.

### 2026-04-18 13:22 — Bug fix #1: `_coerce_pid` bare-number hex-vs-decimal ambiguity

**Issue:** `test_start_state_roundtrip` failed — Pydantic model round-trip via `model_dump_json` → `model_validate_json` produced wrong dict keys. Input `{0x0C: 1800}` round-tripped to `{0x12: 1800}` (12 decimal → "12" JSON string → 0x12 hex = 18 decimal).

**Root cause:** `_coerce_pid` at line 150 had fallback `return int(lower, 16)` for bare numeric strings — correctly parsing `"0x05"` as hex but incorrectly treating `"12"` (JSON round-trip of int key) as hex `0x12 = 18`.

**Fix:** Changed the bare-numeric path to decimal (`int(lower, 10)`). Hex parsing now requires explicit `"0x"` or `"0X"` prefix. This preserves JSON round-trip identity: `{12: ...}` serializes to `{"12": ...}` and deserializes back to `{12: ...}`.

**Files:** `src/motodiag/hardware/simulator.py` lines 144-152.

**Verified:** `pytest tests/test_phase144_simulator.py::TestScenarioModels::test_start_state_roundtrip -v` → PASS.

### 2026-04-18 13:45 — KNOWN ISSUES — follow-up Builder-144-Fix needed

Architect trust-but-verify surfaced **35 additional test failures beyond the 2 bugs fixed above**. Not blocking Phase 141 commit but require a dedicated follow-up before Phase 144 can close to v1.1.

**Failure clusters:**
1. **TestScenarioFromRecording (5 tests)** — `ScenarioLoader.from_recording(recording_id)` calls `int(recording_id)` but tests pass string IDs like `"test_rec_1"`. Tests need either (a) integer IDs via real `RecordingManager.start_recording()` setup, or (b) graceful ValueError handling. Builder's deviation note confirms this cluster was substituted with guard-path coverage instead of real round-trip assertions — the substituted tests still fail on the int() conversion.
2. **TestSimulateCommand (7+ tests)** — `simulate validate <builtin_yaml>` + `simulate run <builtin>` paths fail. Likely scenario YAML schema mismatch with Pydantic validators, OR `--simulator` flag + `--mock` mutex not properly wired on scan command.
3. **Builtin YAML validation failures** — `misfire.yaml`, `o2_sensor_fail.yaml`, `overheat.yaml` fail `simulate validate`. Likely overlapping RampPid entries (Phase 144 validators reject same-PID overlap) in the Builder's misfire scenario (which uses 20+ rapid ramps).
4. **Malformed-YAML / reconnect-without-disconnect** — CLI error surfacing not matching test expectations.

**Recommendation:** dispatch Builder-144-Fix agent to:
- Review + fix the 10 built-in YAML scenarios (especially `misfire.yaml` RampPid overlap).
- Rewrite TestScenarioFromRecording to use real int IDs from a setup fixture creating a mock recording.
- Verify `--simulator` flag wiring end-to-end through CliRunner.
- Target: bring Phase 144 from 91 pass / 35 fail to full green.

### 2026-04-18 13:50 — Build-incomplete sign-off (v1.0 plan met; v1.1 finalization BLOCKED)

Production code ships (all spec artifacts present). **Docs do NOT move to `completed/` until Builder-144-Fix closes the 35 test failures.** Phase 144 stays in `in_progress/` until green regression.

**Fix #1 verified:** the `_coerce_pid` bare-number correctness bug is a genuine root-cause fix (not a test hack) — protects future phases that JSON-serialize scenarios.

**Next:** Builder-144-Fix dispatch.
