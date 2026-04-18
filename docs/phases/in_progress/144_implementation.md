# MotoDiag Phase 144 — Hardware Simulator

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-18

## Goal

Turn Phase 140's static `MockAdapter` into a **scriptable scenario-driven simulator**. Extends hardware substrate so mechanics + CI can exercise the entire diagnostic stack without physical hardware. Three inputs: built-in YAML scenarios, user-authored YAMLs, Phase 142 recordings. **`hardware/mock.py` is UNTOUCHED** — simulator is a sibling, not a subclass.

CLI: `motodiag hardware simulate {list,run,validate}`. Plus opt-in `--simulator SCENARIO` flag on `scan`/`clear`/`info` (mutex with `--mock`). Badge `[SIM: name]` magenta, distinct from `[MOCK]` yellow.

Outputs:
- `src/motodiag/hardware/simulator.py` (~500 LoC) — `SimulationClock`, 9 Pydantic event models, `Scenario` aggregate with validators, `ScenarioLoader` (`from_yaml`/`from_recording`/`list_builtins`/`find`), `SimulatedAdapter(ProtocolAdapter)`.
- `src/motodiag/hardware/scenarios/__init__.py` (~40 LoC) + 10 built-in YAMLs.
- `src/motodiag/cli/hardware.py` +~150 LoC (additive).
- `pyproject.toml` +1 base dep `pyyaml>=6` + `[tool.setuptools.package-data]` entry for YAML assets.
- `tests/test_phase144_simulator.py` (~1050 LoC, ~55 tests across 6 classes).

No migration, no new DB tables, no AI. Zero `time.sleep` in tests (CI grep enforces).

## Logic

### `SimulationClock` — deterministic time source

```python
class SimulationClock:
    def __init__(self, start_s: float = 0.0): ...
    def now(self) -> float: ...
    def tick(self, dt_s: float = 0.1): ...
    def advance(self, to_s: float): ...   # must be >= now(); raises ValueError if backwards
    def freeze/unfreeze/reset(start_s=0.0): ...
```

Floats. Monotonic. Tests drive it entirely. Production `simulate run` wraps with a RealTimeClock adapter calling `tick(0.01)` with `time.sleep(0.01/speed)` — tests never instantiate that wrapper.

### Scenario event models (Pydantic, frozen, `extra="forbid"`)

Discriminated union on `action` field. All events carry `at_s: float >= 0`.

- `StartState(action="start", at_s=0.0, pids: dict[int, float], dtcs=[], vin=None, protocol="SimProtocol")` — must be index 0.
- `RampPid(action="ramp", at_s, pid, from_: float = Field(alias="from"), to, duration_s, shape="linear")` — `ease_in_out` validated-but-NotImplementedError v1.
- `InjectDTC(action="inject_dtc", at_s, code)` — regex `^[PCBU][0-9A-F]{4}$`.
- `ClearDTC(action="clear_dtc", at_s, code)` — cross-validates with earlier InjectDTC.
- `InjectTimeout(action="inject_timeout", at_s, duration_s)` — window during which reads raise `TimeoutError`.
- `Disconnect(action="disconnect", at_s)` / `Reconnect(action="reconnect", at_s)` — reconnect validates prior disconnect.
- `PhaseTransition(action="phase", at_s, name)` — event log only, no state mutation.
- `EndScenario(action="end", at_s)` — exactly one, last.

`Scenario` validators: StartState at index 0, EndScenario at -1, timeline sorted by `at_s`, `initial` keys referenced in StartState, `vin` 17-char format, ramp PIDs in StartState, DTC clear matches prior inject, reconnect follows disconnect.

### ScenarioLoader

```python
def from_yaml(path_or_str_or_textio, *, validate_only=False) -> Scenario: ...
def from_recording(recording_id, db=None) -> Scenario: ...
def list_builtins() -> list[Scenario]: ...
def find(name, *, user_paths=()) -> Scenario: ...
```

`from_yaml`: `yaml.safe_load` → `Scenario(**raw)`. YAMLError → `ScenarioParseError(path, line, col, msg)`; ValidationError → `ScenarioValidationError(path, errors)`.

`from_recording`: guarded by `_phase142_available()` probe. Walks recording samples, emits StartState + RampPid events for PID changes + EndScenario. If Phase 142 unavailable → raise `RecordingSupportUnavailable`.

`list_builtins`: iterates `importlib.resources.files("motodiag.hardware.scenarios").iterdir()`.

### SimulatedAdapter(ProtocolAdapter) — 8 ABC methods driven by state fold

`__init__(scenario, clock=None)`. Clock defaults to fresh `SimulationClock()`. Adapter does NOT own clock advance — callers tick.

**`_materialize_state(t)` — core fold:**
```
state = copy(StartState)
for event in timeline where event.at_s <= t:
    apply(event, state, now=t)
```
- RampPid: interpolate linearly if in window; pin to from_/to outside.
- InjectDTC/ClearDTC: add/remove code.
- InjectTimeout: set `timeout_until = at_s + duration_s`; subsequent reads raise TimeoutError if `clock.now() < timeout_until`.
- Disconnect/Reconnect: flip `disconnected` flag.
- PhaseTransition/EndScenario: no state mutation (event log emitted by runner).

Fold runs per-read — O(events) per call, ≤100 events typical — negligible. Keeps adapter stateless-at-rest, deterministic.

ABC methods: `connect` sets `_is_connected=True`; `disconnect` flips False; `send_command` returns `b""`; `read_dtcs` returns copy of `state.active_dtcs`; `clear_dtcs` empties dtcs (doesn't mutate timeline), returns `True`; `read_pid` returns `int(round(state.pid_values.get(pid)))` or None; `read_vin` returns `state.vin`; `get_protocol_name` returns `state.protocol`.

### 10 built-in YAML scenarios

Under `src/motodiag/hardware/scenarios/`:
1. `healthy_idle.yaml` — 60s, 0 DTCs, stable idle.
2. `cold_start.yaml` — 120s, coolant 20°C→90°C, RPM 1800→900.
3. `overheat.yaml` — 180s, coolant 90°C→118°C, P0217 at 120s.
4. `misfire.yaml` — 90s, RPM oscillation, P0300 at 30s.
5. `lean_fault.yaml` — 150s, STFT climbs, P0171 at 60s.
6. `o2_sensor_fail.yaml` — 120s, O2 flatlines at 0.45V, P0134 at 45s.
7. `charging_fault.yaml` — 180s, battery 14.2V→11.8V, P0620 at 90s.
8. `ecu_crash_recovery.yaml` — 60s, Disconnect@20s, InjectTimeout 3s@22s, Reconnect@30s.
9. `harley_sporty_warmup.yaml` — 240s, J1850 VPW, VIN `1HD1CZ3189K456789`.
10. `cbr600_warm_idle.yaml` — 90s, ISO 14230 KWP2000, VIN `JH2PC40A7WM123456`.

### YAML example (cold_start.yaml excerpt)
```yaml
name: cold_start
description: ECU boots cold, warms, develops lean fault
protocol: ISO 15765-4 (CAN)
vin: JH2PC40A7WM123456
initial:
  0x05: 20
  0x0C: 1800
  0x11: 18
  0x06: 128
  0x42: 14100
timeline:
  - {action: start, at: 0s, pids: {0x05: 20, 0x0C: 1800, 0x11: 18, 0x06: 128, 0x42: 14100}, dtcs: [], vin: JH2PC40A7WM123456, protocol: ISO 15765-4 (CAN)}
  - {action: phase, at: 0s, name: cold_start}
  - {action: ramp, at: 5s, pid: 0x05, from: 20, to: 88, duration: 50s}
  - {action: ramp, at: 5s, pid: 0x0C, from: 1800, to: 900, duration: 40s}
  - {action: phase, at: 55s, name: warm_idle}
  - {action: ramp, at: 60s, pid: 0x06, from: 128, to: 148, duration: 45s}
  - {action: inject_dtc, at: 105s, code: P0171}
  - {action: end, at: 120s}
```

Duration parser `_parse_duration(s) -> float` accepts `"30s"`, `"1m30s"`, `"1.5s"`, bare int/float (seconds).

`_coerce_pid(raw)` accepts int, hex int, hex string, symbolic alias (`"coolant_temp"` → 0x05 via PID_ALIASES).

### CLI `simulate` subgroup

Registered additively. `list` prints Rich table (name/desc/protocol/duration/source). `run <scenario> [--port VIRTUAL] [--bike | --make] [--speed N] [--log] [--log-name NAME] [--max-duration-s N]` resolves scenario, runs via `_run_scenario(sc, speed, logger, recorder, clock, max_duration_s)`, prints live event log + completion panel. `validate <path>` runs `from_yaml(path, validate_only=True)` → green OK or red line/column error.

`_run_scenario`:
- Construct `SimulatedAdapter(sc, clock)`.
- `adapter.connect("sim://name", 0)`.
- Tick loop at 10 Hz: emit events where `prev_t < at_s <= now()`; log + optionally record via Phase 142 RecordingManager.
- `speed=0` jumps clock directly to next event (fastest, used in tests).
- `speed>0` wall-clock paces with `time.sleep(dt/speed)`.
- Exit cap at `max_duration_s` (default 300).

### `--simulator` flag on scan/clear/info

Mutex with `--mock` (both → Click `UsageError`). When given: construct `SimulatedAdapter(scenario=...)` + pass via `HardwareSession(adapter_override=sim_adapter)`. No HardwareSession changes — existing Phase 140 override slot.

## Key Concepts

- **Simulator vs MockAdapter separation.** MockAdapter frozen; SimulatedAdapter sibling. Both implement ProtocolAdapter directly. Minimal duplication (~6 LoC boilerplate); Phase 140 contract guard stays sharp.
- **Determinism via manual clock.** All test determinism flows from `SimulationClock` injected constructor kwarg. Production wraps with wall-clock pacing; tests never engage that wrapper.
- **Pydantic discriminated union on `action`.** YAML → Pydantic → typed event in one step. `extra="forbid"` catches typos at boundary.
- **YAML is mechanic-facing.** No Python required. `simulate validate` is lint gate.
- **`importlib.resources` for YAMLs.** Portable across zipapp/wheel/editable. Matches Phase 111 knowledge-pack pattern.
- **Scenario-from-recording is symmetry with Phase 142.** Record once on real hardware, replay N times in CI.
- **`HardwareSession.adapter_override` is the integration point** — shipped Phase 140.
- **State fold is O(events) per read.** Pure function of `(scenario, t)`. Deterministic regardless of call order.

## Verification Checklist

- [ ] `SimulatedAdapter` instantiates (all 8 ABC methods present).
- [ ] `SimulationClock` tick/advance/now monotonic, deterministic, test-controlled.
- [ ] All 10 built-in YAMLs parse cleanly.
- [ ] `simulate list` shows all 10 built-ins.
- [ ] `simulate run healthy_idle` with `--speed 0` completes in <1s; exit 0.
- [ ] `simulate run overheat` emits P0217 + peaks coolant ≥115°C.
- [ ] `simulate validate` rejects malformed YAML with line number.
- [ ] `simulate validate` rejects Reconnect without preceding Disconnect.
- [ ] `hardware scan --simulator healthy_idle` runs against SimulatedAdapter + prints `[SIM: healthy_idle]` magenta badge.
- [ ] `--mock` + `--simulator` mutex on scan/clear/info (Click UsageError exit 2).
- [ ] `hardware/mock.py` byte-unchanged from Phase 140 (CI diff check).
- [ ] `from_recording` round-trip PID values ±1 (skipped if Phase 142 absent).
- [ ] `time.sleep` count in tests is 0 (CI grep).
- [ ] Phase 140's 40 tests pass untouched.
- [ ] `pyyaml>=6` in `pyproject.toml` base deps.
- [ ] Tests don't import `motodiag.hardware.mock` (sibling-not-subclass enforcement).

## Risks

- **Phase 142 not merged when 144 builds.** `ScenarioLoader.from_recording` + 6 tests guarded behind `_phase142_available()` probe; `RecordingSupportUnavailable` raised with mechanic-friendly message; tests skip gracefully. On 142 merge, revisit interface.
- **YAML hex int coercion is parser-dependent.** PyYAML parses `0x05` unquoted as int; `"0x05"` as string. `_coerce_pid` accepts all three forms (int, hex string, symbolic alias). One test covers this.
- **Overlapping RampPid on same PID undefined.** Validator rejects overlaps with clear error.
- **`time.sleep` in wall-clock pacing.** Tests monkey-patch + force `speed=0`. CI grep enforces zero `time.sleep` in test_phase144_simulator.py.
- **Built-in YAML shipping.** `[tool.setuptools.package-data] "motodiag.hardware.scenarios" = ["*.yaml"]` in pyproject. Runtime test asserts `importlib.resources.files(...).joinpath("healthy_idle.yaml").is_file()`.
- **`cli/hardware.py` multi-edit with 141/142/143/145.** Additive only. No flag-name collision (141=stream, 142=log, 143=dashboard, 144=simulate, 145=compat).
- **`read_pid` returns `Optional[int]` but scenarios use floats.** `SimulatedAdapter.read_pid` rounds at boundary. YAML allows floats for authoring ergonomics. Unit convention: native OBD-II (mV, °C, rpm).
- **Determinism + dict iteration order.** Events iterate by at_s index, not dict key. Scenario frozen. Regression test.
- **`mock.py` docstring mentions "Phase 144 will extend".** Sibling chosen instead — docstring left alone in 144 (pedantic cleanup for 145).
- **`pyyaml` as base dep vs `[sim]` extra.** Base dep chosen: `simulate validate` must just work; future phases want YAML too. ~200kB footprint.

## Dependencies flagged

- Phase 140 (ProtocolAdapter ABC, MockAdapter, HardwareSession `adapter_override`) — **shipped**.
- Phase 142 (RecordingManager) — **soft dep**; graceful skip.
- Phases 141/143 share `cli/hardware.py` — additive only.
- New base dep `pyyaml>=6` — one-line pyproject change.
