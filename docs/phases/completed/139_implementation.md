# MotoDiag Phase 139 — ECU Auto-Detection + Handshake

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-18

## Results
| Metric | Value |
|--------|------:|
| New files | 2 (`src/motodiag/hardware/ecu_detect.py` ~460 LoC, `tests/test_phase139_ecu_detect.py` ~680 LoC) |
| New tests | 25 methods / 31 collected (passed locally 31/31 in 0.25s) |
| Live API tokens burned | 0 |

**Key deviation**: adapter constructor non-uniformity confirmed (flagged in plan's Risks). Each adapter uses different kwargs: CAN `channel/bitrate/request_timeout+multiframe_timeout`, K-line `port/baud/read_timeout`, J1850 `port/baudrate/timeout_s`, ELM327 `port/baud/timeout`. Solved via per-protocol `_build_adapter` with string-label priority table. Lazy imports per-adapter so missing optional deps only surface when tried. Best-effort `send_request` with fallback to `send_command`. `_decode_vin` handles both `49 02 01`-echo and stripped responses. `NoECUDetectedError` carries `port`, `make_hint`, and `errors: list[(name, exception)]` for programmatic introspection.

---

## Goal (v1.0)
Glue layer over Phases 134-138's protocol adapters. Given a serial port (and optionally a bike make hint), try each protocol adapter in a priority order chosen from the hint, negotiate a live session, and identify the ECU (VIN + ECU part number + software version). Returns the successfully-connected `ProtocolAdapter` ready for Phase 140's DTC read/clear operations. No new CLI command in this phase (Phase 140 owns the user-facing surface). No migration. No live hardware — all tests use `MagicMock` adapters.

```python
from motodiag.hardware.ecu_detect import AutoDetector, NoECUDetectedError

detector = AutoDetector(port="COM3", make_hint="harley", timeout_s=5.0)
adapter = detector.detect()                    # returns a connected ProtocolAdapter
ecu_info = detector.identify_ecu(adapter)      # {vin, ecu_id, ecu_part_number, software_version, supported_modes}
```

Outputs: new `src/motodiag/hardware/ecu_detect.py` (~280 LoC), new exception class `NoECUDetectedError(ProtocolError)` in same module, new `tests/test_phase139_ecu_detect.py` with ~20-25 tests. **No migration.** **No CLI command.** **No new pyproject deps** (all deps added in 134-138).

## Logic

### 1. `NoECUDetectedError(ProtocolError)`
Raised when `detect()` has exhausted the entire candidate protocol list and none connected. Message includes the port, the make_hint, and a summary of which protocols were tried and the error each produced (e.g. `"No ECU detected on COM3 (make_hint=harley). Tried: J1850 (timeout), CAN (no response), K-line (framing error)."`). Subclass of Phase 134's base `ProtocolError` so existing catch-all handlers in `cli/` already cover it without needing import changes there.

### 2. `AutoDetector` class
```python
class AutoDetector:
    def __init__(
        self,
        port: str,
        baud: int | None = None,
        make_hint: str | None = None,
        timeout_s: float = 5.0,
    ) -> None: ...

    def detect(self) -> ProtocolAdapter: ...
    def identify_ecu(self, adapter: ProtocolAdapter) -> dict: ...
```

**Constructor:**
- `port`: serial port string (`"COM3"`, `"/dev/ttyUSB0"`, or a Bluetooth port).
- `baud`: optional override. If `None`, each adapter uses its own default (CAN=500k, K-line=10400, J1850=41.6k, ELM327=38400). Passed through unchanged when set.
- `make_hint`: normalized to lowercase, stripped; accepts `"harley"`, `"honda"`, `"yamaha"`, `"kawasaki"`, `"suzuki"`, `"ducati"`, `"bmw"`, `"ktm"`, `"triumph"`, or `None`. Unknown values are accepted silently and fall to the default order.
- `timeout_s`: applied per-adapter `connect()` attempt. Adapters that support a `timeout` kwarg receive it; adapters that don't get ignored.

### 3. Make-hint priority logic (`_protocol_order_for_hint`)

Private helper returns a list of adapter factory callables in the order they should be tried. Each factory is `lambda: AdapterClass(port=self.port, baud=self.baud, timeout=self.timeout_s)`.

| make_hint | Priority order | Rationale |
|---|---|---|
| `harley` | J1850 → CAN → ELM327 | Pre-2011 Harleys use J1850 VPW/PWM; 2011+ use CAN. ELM327 as universal fallback for generic OBD dongles paired with adapter cables. K-line excluded — not a Harley protocol. |
| `honda`, `yamaha`, `kawasaki`, `suzuki` | K-line → CAN → ELM327 | 90s-2010 Japanese bikes predominantly K-line/KWP2000. 2010+ moved to CAN. ELM327 fallback. J1850 excluded — not used on Japanese bikes. |
| `ducati`, `bmw`, `ktm`, `triumph` | CAN → K-line → ELM327 | Modern European bikes are CAN-first. Older models fall back to K-line. J1850 excluded. |
| `None` or unknown | CAN → K-line → J1850 → ELM327 | No hint: try modern first (CAN covers most post-2011 bikes), then the pre-CAN protocols, then the universal ELM327. |

Adapter classes are imported from Phases 134-138:
- `CanAdapter` from `motodiag.hardware.can_adapter` (Phase 136)
- `KlineAdapter` from `motodiag.hardware.kline_adapter` (Phase 137)
- `J1850Adapter` from `motodiag.hardware.j1850_adapter` (Phase 138)
- `Elm327Adapter` from `motodiag.hardware.elm327_adapter` (Phase 135)

Imports are lazy inside `_protocol_order_for_hint` so missing-module ImportErrors only surface if the hint actually requires that adapter (defensive against partial installs during cross-phase builds).

### 4. `detect() -> ProtocolAdapter`

```python
def detect(self) -> ProtocolAdapter:
    candidates = self._protocol_order_for_hint(self.make_hint)
    errors: list[tuple[str, Exception]] = []
    for factory in candidates:
        adapter = factory()
        try:
            adapter.connect()
        except ProtocolError as err:
            errors.append((type(adapter).__name__, err))
            continue
        except Exception as err:
            # unexpected failure — record and continue (don't let one bad adapter kill detection)
            errors.append((type(adapter).__name__, err))
            continue
        # connected — adapter is live and owned by the caller
        return adapter
    raise NoECUDetectedError(self._format_error_summary(errors))
```

Behavior notes:
- First successful `connect()` wins — returned adapter is **not** disconnected by `detect()`. Caller owns lifecycle.
- On failure of one adapter, the next is tried — earlier adapters are garbage-collected (their `connect()` never completed, so no resource leak).
- Any non-`ProtocolError` exception is caught and recorded as a detection failure rather than propagated, so a buggy adapter in one protocol doesn't prevent the others from being tried. The full error list is preserved in the raised `NoECUDetectedError`.
- Errors list is formatted as `"{AdapterName} ({short_error})"` joined by commas.

### 5. `identify_ecu(adapter) -> dict`

Issues two OBD-style requests against the connected adapter and returns a best-effort dict. Neither request is mandatory — any field may be `None` if the ECU doesn't respond or the response is unparseable.

```python
def identify_ecu(self, adapter: ProtocolAdapter) -> dict:
    result = {
        "vin": None,
        "ecu_id": None,
        "ecu_part_number": None,
        "software_version": None,
        "supported_modes": [],
    }
    # VIN read — Mode 09 PID 02 (standard OBD-II)
    try:
        vin_bytes = adapter.send_request(mode=0x09, pid=0x02)
        result["vin"] = self._decode_vin(vin_bytes)
    except ProtocolError:
        pass
    # ECU identification — Mode 09 PID 0A (ECU name) + PID 04 (calibration ID)
    try:
        ecu_name_bytes = adapter.send_request(mode=0x09, pid=0x0A)
        result["ecu_id"] = self._decode_ascii(ecu_name_bytes)
    except ProtocolError:
        pass
    try:
        cal_id_bytes = adapter.send_request(mode=0x09, pid=0x04)
        result["ecu_part_number"] = self._decode_ascii(cal_id_bytes)
    except ProtocolError:
        pass
    try:
        sw_ver_bytes = adapter.send_request(mode=0x09, pid=0x08)
        result["software_version"] = self._decode_ascii(sw_ver_bytes)
    except ProtocolError:
        pass
    # Supported modes — Mode 01 PID 00 returns a bitmask of supported PIDs; we probe modes 01/02/03/04/09
    result["supported_modes"] = self._probe_supported_modes(adapter)
    return result
```

Private decoders:
- `_decode_vin(b: bytes) -> str | None` — VIN is 17 ASCII chars; strips OBD padding bytes (`0x00`, `0xFF`) and leading mode/PID echo bytes; validates length==17 else returns None.
- `_decode_ascii(b: bytes) -> str | None` — generic ASCII decode, strips non-printable bytes, returns `None` if result is empty.
- `_probe_supported_modes(adapter) -> list[int]` — issues `adapter.send_request(mode=m, pid=0x00)` for m in `[0x01, 0x02, 0x03, 0x04, 0x09]`; any that returns without raising is added to the list.

### 6. Tests (~20-25 tests in `tests/test_phase139_ecu_detect.py`)

All tests use `MagicMock` / `unittest.mock.patch` to stand in for the four adapter classes. **Zero real serial I/O.** Adapter factories are patched at the `motodiag.hardware.ecu_detect` module level.

**TestProtocolOrder (6 tests)** — assert `_protocol_order_for_hint` returns the right adapter sequence:
- `harley` → [J1850, CAN, ELM327]
- `honda` / `yamaha` / `kawasaki` / `suzuki` (one test each, 4 total) → [K-line, CAN, ELM327]
- `ducati` / `bmw` / `ktm` / `triumph` → merged into one parametrized test → [CAN, K-line, ELM327]
- `None` → [CAN, K-line, J1850, ELM327]
- `"unknown-make"` → same as None fallback

**TestDetectSuccess (4 tests)**:
- First-try success: CAN adapter connect() succeeds → returned adapter is the CAN instance, no others attempted.
- Second-try success: CAN fails with ProtocolError, K-line succeeds → returned adapter is the K-line instance, CAN.connect was called once.
- Third-try success: CAN + K-line both fail, J1850 succeeds → J1850 returned, other two called once each.
- Fallback ELM327 success: all three primary adapters fail, ELM327 succeeds.

**TestDetectFailure (3 tests)**:
- All adapters fail with ProtocolError → `NoECUDetectedError` raised with summary listing all 4 tried adapters.
- Non-ProtocolError exception in one adapter (e.g. `OSError`) doesn't abort detection — next adapter still tried.
- Error summary string contains the port and the make_hint.

**TestIdentifyEcuSuccess (4 tests)**:
- All four reads succeed → dict has vin, ecu_id, ecu_part_number, software_version populated + non-empty supported_modes.
- VIN is a valid 17-char string when the mock returns the canonical "1HD1KHM14FB123456" ASCII bytes.
- ECU ID correctly ASCII-decoded from padded response.
- `supported_modes` contains all 5 modes when every probe succeeds.

**TestIdentifyEcuPartialFailure (4 tests)**:
- VIN read raises ProtocolError → `vin` is None, other fields still populated.
- All four reads raise → all four fields None, `supported_modes` == [].
- VIN response is wrong length (not 17 chars) → `vin` is None, not a bogus truncation.
- `supported_modes` only contains modes that didn't raise.

**TestAutoDetectorWiring (3 tests)**:
- Constructor accepts and normalizes `make_hint` (uppercase, whitespace both stripped).
- `timeout_s` is passed into the adapter factories.
- `baud=None` → adapters get no explicit baud override; `baud=500000` → adapters receive it.

**TestErrorClass (1 test)**:
- `NoECUDetectedError` is a subclass of `ProtocolError` — existing `except ProtocolError:` handlers catch it.

Total: 25 tests. All use `MagicMock` for adapters — **zero live hardware, zero AI calls, zero live API tokens.**

## Key Concepts

- **Detection is a glue layer, not a protocol.** 134-138 each own one wire protocol; 139 owns the decision of which one to try first for a given bike. This keeps individual adapter modules focused and keeps the heuristic (make → protocol) isolated and tweakable in one place.
- **Make-hint is optional and advisory.** With no hint, detection still works — it just tries more candidates. A good hint lets us connect in <2s on a Harley; a bad or missing hint might take 10-15s on the same bike. Mechanics using the CLI will always pass a hint (from `garage` metadata); hobbyists scanning an unknown bike get the fallback.
- **Japanese bikes don't use J1850; Harleys don't use K-line.** Hardcoding these exclusions in the order table is cheaper than trying and failing — each failed `connect()` attempt costs real wall-clock time (5s timeout each).
- **First-connect-wins returns a live adapter.** The caller owns the lifecycle and is responsible for `adapter.disconnect()` when done. `detect()` does NOT close the returned adapter. Phase 140's CLI command will wrap detection in a `with` block or try/finally.
- **Non-ProtocolError exceptions are caught, not propagated.** A `OSError` or `ValueError` from a buggy adapter should not prevent the other three from being tried. The full failure list surfaces in `NoECUDetectedError.message` so debugging is still possible.
- **`identify_ecu` is best-effort.** Any OBD read can fail on a non-compliant ECU — Harley VINs aren't always on Mode 09 PID 02, older Japanese ECUs may return garbage for calibration ID. Returning `None` for individual fields instead of raising lets the UI show partial info ("VIN: 1HD...; ECU: unknown") rather than failing outright.
- **Supported modes list is a capability advertisement.** Phase 140 uses it to decide whether Mode 03 (read DTCs) is even available before issuing the request — avoids a timeout on ECUs that don't implement Mode 03.
- **No live hardware in tests.** `MagicMock` adapters with `connect()` that succeeds or raises on demand is enough to exercise every code path. Real-hardware tests are a future integration-test phase (Gate 6 / Phase 147).

## Verification Checklist
- [x] `src/motodiag/hardware/ecu_detect.py` exists with `AutoDetector` class + `NoECUDetectedError` exception
- [x] `NoECUDetectedError` is a subclass of `ProtocolError` (Phase 134 base class)
- [x] `AutoDetector.__init__` accepts `port`, `baud=None`, `make_hint=None`, `timeout_s=5.0`
- [x] `make_hint` is normalized (lowercase + strip) before dispatch
- [x] `_protocol_order_for_hint("harley")` returns `[J1850, CAN, ELM327]`
- [x] `_protocol_order_for_hint("honda")` returns `[K-line, CAN, ELM327]` (same for yamaha/kawasaki/suzuki)
- [x] `_protocol_order_for_hint("ducati")` returns `[CAN, K-line, ELM327]` (same for bmw/ktm/triumph)
- [x] `_protocol_order_for_hint(None)` returns `[CAN, K-line, J1850, ELM327]`
- [x] `_protocol_order_for_hint("unknown-make")` returns the same default fallback
- [x] `detect()` returns the first adapter whose `connect()` succeeds
- [x] `detect()` does NOT call `disconnect()` on the successful adapter
- [x] `detect()` tries each candidate exactly once before giving up
- [x] `detect()` raises `NoECUDetectedError` when every candidate fails
- [x] `NoECUDetectedError` message includes port, make_hint, and per-adapter error summary
- [x] `detect()` catches non-`ProtocolError` exceptions and continues (doesn't propagate)
- [x] `identify_ecu()` returns a dict with keys `vin`, `ecu_id`, `ecu_part_number`, `software_version`, `supported_modes`
- [x] `identify_ecu()` never raises — partial failures yield `None` for affected fields
- [x] VIN decoder validates 17-char length and rejects malformed responses
- [x] `supported_modes` probes modes 01, 02, 03, 04, 09 and lists only those that responded
- [x] ~20-25 tests in `tests/test_phase139_ecu_detect.py` — all pass with zero live hardware
- [x] All tests use `MagicMock` adapters — zero real serial I/O, zero AI calls

## Risks
- **Phases 134-138 adapter signatures may differ from assumed.** Plan assumes each adapter has `connect()`, `disconnect()`, `send_request(mode, pid)` and raises `ProtocolError` on failure. If 134's abstraction layer settles on different method names, `ecu_detect.py` needs to match. Mitigation: read 134's `ProtocolAdapter` ABC before coding and update method calls accordingly. If signatures diverge significantly, bump to v1.2.
- **Adapter constructor kwargs differ per protocol.** CAN's constructor may want `bitrate=`, K-line may want `init_pattern=`, etc. Plan uses a uniform `(port, baud, timeout)` signature via factory lambdas — if an adapter requires protocol-specific kwargs, the factory lambda for that protocol carries them. Mitigation: confirm constructor signatures in 134-138 before wiring factories.
- **`timeout_s` may not map cleanly to every adapter.** ELM327 uses AT-command timeouts in ms, CAN uses socket timeouts in s, K-line uses inter-byte gap timeouts. Plan: pass `timeout_s` as a generic kwarg and let each adapter translate. If an adapter has no compatible timeout knob, accept that and document.
- **`detect()` wall-clock cost with no hint.** 4 adapters × 5s timeout = 20s worst case. Acceptable for a one-shot detection (human waits at CLI), unacceptable for automated loops. Phase 140 should cache the detected protocol on the vehicle record so subsequent sessions skip detection.
- **ECU identification assumes OBD-II mode 09.** Pre-OBD-II bikes (90s Harleys with proprietary protocols, some early Japanese bikes) don't respond to mode 09 at all. Plan's best-effort return (all fields None) is the right answer — caller shows "ECU: unknown, protocol: K-line connected" and moves on.
- **Garbage-collection of failed adapters.** A partial `connect()` that holds a serial port open and then raises could leak the port. Plan: adapters are expected to clean up their own state in `connect()`'s exception path (Phase 134 ABC contract). If an adapter violates this, port stays locked until process exit — worth a regression test but out of scope here.
- **Mock-heavy tests may mask real integration bugs.** MagicMock accepts any method call, so a typo in `send_request` vs `send_request_raw` would pass tests but fail on hardware. Mitigation: Gate 6 (Phase 147) runs against the simulator from Phase 144. Phase 139 tests are correctness for the orchestration logic, not the protocol wire.
