# MotoDiag Phase 138 — J1850 VPW Protocol Adapter (Pre-2011 Harley-Davidson)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-18

## Results
| Metric | Value |
|--------|------:|
| New files | 2 (`src/motodiag/hardware/protocols/j1850.py` ~600 LoC, `tests/test_phase138_j1850.py` ~25 tests) |
| Modified files | 1 (`hardware/protocols/__init__.py` export) |
| New tests | 27 (passed locally 27/27 in batch run) |
| Live API tokens burned | 0 |

**Deviations**: ABC signature reconciliation (same pattern as other Wave 2 phases). `read_dtcs() -> list[str]` flat merge (ECM→BCM→ABS); supplementary `read_dtcs_by_module() -> dict[str, list[str]]` for labeled access. `clear_dtcs(module=None)` accepts optional module kwarg while preserving bool return. `read_pid` raises `NotImplementedError` with Phase-141 pointer; `read_vin` raises `UnsupportedCommandError` (pre-2008 Harleys lacked Mode 09). Bridge keys simplified: `daytona/scangauge/dynojet/generic`.

---

## Goal (v1.0)
Implement `J1850Adapter`, the third concrete `ProtocolAdapter` in the Track E hardware stack (after Phase 136 CAN / ISO 15765 and Phase 137 K-line / KWP2000). J1850 VPW is the pre-2011 Harley-Davidson ECM diagnostic protocol — specifically 10.4 kbps Variable Pulse Width, not the 41.6 kbps PWM variant. Pre-2007 Sportsters / Big Twin Evo / TC88 Touring bikes speak pure Harley-proprietary J1850; 2007-2010 EFI Harleys (Delphi / Magneti Marelli ECMs, Delphi BCM, Brembo/HD ABS modules) speak J1850 VPW with partial SAE OBD-II Mode 03 bolted on. 2011+ Harleys moved to CAN (Phase 136). Because genuine J1850 silicon is rare and consumer ELM327 clones drop back to `ATTP 2`/`ATTP A`-style auto-detect badly on Harley-proprietary frames, real shop-floor workflow goes through a hard-wired **bridge device** (Scan Gauge II, Daytona Twin Tec TCFI tuner, Dynojet Power Commander diagnostic mode, Harley Digital Tech II clones). Our adapter talks serial to that bridge, the bridge talks J1850 VPW to the bike. No direct bus-level bit-banging from Python.

Adds the multi-ECM story that neither Phase 136 nor 137 needed: a single `read_dtc()` call must query **ECM (powertrain / P-codes)**, **BCM (body / B-codes)**, and on 2007+ Touring **ABS (chassis / C-codes)** — three separate module addresses on the same J1850 bus, each with its own DTC list. The adapter concatenates all three into the `DTCReading` list Phase 140 consumes.

```
# Not directly invoked in this phase — Phase 139 auto-detect and Phase 140
# read/clear are what instantiate this class. This phase is adapter + tests only.
from motodiag.hardware.protocols.j1850 import J1850Adapter
adapter = J1850Adapter(port="COM5", baudrate=10400, bridge="daytona_twin_tec")
adapter.connect()
dtcs = adapter.read_dtc()   # queries ECM + BCM + ABS, returns merged list
adapter.disconnect()
```

Outputs:
- New `src/motodiag/hardware/protocols/__init__.py` (package marker — may already exist from 136/137; idempotent).
- New `src/motodiag/hardware/protocols/j1850.py` (~420 LoC): `J1850Adapter`, bridge-command tables, Harley DTC decoder (P/B/C prefix + 4-digit), multi-module response parser.
- New `tests/test_phase138_j1850.py` (~22 tests across 6 classes): mock serial I/O, DTC read (ECM / BCM / ABS / combined), Harley P-code / B-code / C-code parsing, bridge handshake, multi-ECM merge, error paths (no response, checksum fail, unknown module).
- `pyproject.toml`: `pyserial>=3.5` moves from Phase 137's optional `kline` extras into a shared `serial_protocols` extras group (or is already there from Phase 135 ELM327) — adapter imports `pyserial` lazily with an install-hint ClickException to avoid penalizing users who only use cloud mode.
- No migration, no new CLI command, no schema change.

## Logic

### 1. Package scaffolding — `src/motodiag/hardware/protocols/__init__.py`
Idempotent. If Phase 134 (abstraction layer) created it, touch only the `__all__` list to add `"J1850Adapter"`. If it doesn't exist yet, create an empty marker. Keep this file thin — concrete adapters are discovered by name, not by star-import.

### 2. `src/motodiag/hardware/protocols/j1850.py` — core module

#### 2a. Imports + module-level constants
- Lazy `pyserial` import via `_ensure_pyserial()` helper returning the `serial` module. Raises `ClickException("J1850 support requires pyserial. Install with: pip install 'motodiag[hardware]'")` on ImportError.
- `RDLogger`-style noise suppression is not applicable here (no chem libs).
- Constants:
  - `J1850_VPW_BAUD = 10400` (variable pulse width, not PWM 41600)
  - `DEFAULT_READ_TIMEOUT_S = 2.5` (J1850 frames are slow; 0.5s is not enough for multi-frame DTC dumps on a cold bus)
  - `MODULE_ADDRESS = {"ECM": 0x10, "BCM": 0x40, "ABS": 0x28}` — Harley module IDs on the J1850 bus. ABS only present on 2007+ Touring + 2008+ Dyna.
  - `DTC_PREFIX_BY_MODULE = {"ECM": "P", "BCM": "B", "ABS": "C"}`
  - `SUPPORTED_BRIDGES = {"daytona_twin_tec", "scan_gauge_ii", "dynojet_pc", "generic_j1850"}` — strings, not an enum, so plan-time extensibility is cheap.

#### 2b. Bridge command tables
Each bridge speaks a slightly different serial protocol to our host. We abstract by a `_BRIDGE_COMMANDS` dict of dicts:
```python
_BRIDGE_COMMANDS = {
    "daytona_twin_tec": {
        "handshake": b"AT@1\r",           # returns device ID string
        "set_protocol_j1850_vpw": b"ATSP 2\r",
        "read_dtc_ecm": b"03\r",          # Mode 03 passthrough to ECM
        "read_dtc_bcm": b"1901\r",        # Harley proprietary: $19 mode + $01 ECU filter = BCM
        "read_dtc_abs": b"1902\r",        # $19 mode + $02 ECU filter = ABS
        "clear_dtc_ecm": b"04\r",
        "clear_dtc_bcm": b"1904\r",
        "clear_dtc_abs": b"1905\r",
        "prompt": b">",                   # bridge ready prompt
    },
    "scan_gauge_ii": { ... similar shape, different bytes ... },
    "dynojet_pc": { ... },
    "generic_j1850": {
        # Raw passthrough: caller sends J1850-VPW frames as hex text
        "handshake": b"ATI\r",
        "set_protocol_j1850_vpw": b"ATSP 2\r",
        "read_dtc_ecm": b"01 03\r",        # IFR=01 (ECM), service=03
        "read_dtc_bcm": b"01 19 01\r",
        ...
    },
}
```
Rationale: the plan does not promise byte-perfect correctness for every bridge model — real-world calibration happens in Phase 147 (Gate 6 hardware integration) where we plug into actual ECMs. Phase 138's goal is the *shape* of the protocol and a clean abstraction where a future bridge plugin only has to add a dict entry.

#### 2c. `J1850Adapter(ProtocolAdapter)` class
Public surface inherits from Phase 134's base (assumed contract — this phase references it but does not modify it):
- `connect() -> None`
- `disconnect() -> None`
- `is_connected() -> bool`
- `read_dtc() -> list[DTCReading]`
- `clear_dtc(module: str | None = None) -> int`
- `read_live_data(pid: str) -> LiveDataPoint`  → raise `NotImplementedError` in this phase; live data on J1850 is Phase 141's concern and requires per-bike PID maps.
- `adapter_info() -> dict`  → `{"protocol": "J1850_VPW", "baud": 10400, "bridge": self.bridge, "port": self.port}`

Constructor:
```python
def __init__(
    self,
    port: str,
    baudrate: int = J1850_VPW_BAUD,
    bridge: str = "generic_j1850",
    timeout_s: float = DEFAULT_READ_TIMEOUT_S,
    serial_factory: Callable[..., Any] | None = None,   # tests inject a fake
):
```
`serial_factory` defaults to `_ensure_pyserial().Serial` — overridable so tests pass `MockSerial` without monkeypatching `pyserial` globally.

`connect()`:
1. Open serial port at `baudrate` (10400) with 8N1, no flow control, `timeout=timeout_s`.
2. Send bridge `handshake` command, read until `prompt` byte or timeout.
3. Send `set_protocol_j1850_vpw` command, expect `OK` or prompt.
4. Flip `self._connected = True`.
5. Raise `J1850ConnectionError` (new exception in this module) on handshake failure, with the bytes received appended.

`disconnect()`: close serial, clear `_connected`.

`read_dtc()`:
1. For each module in `("ECM", "BCM", "ABS")`:
   1. Send that module's `read_dtc_*` command.
   2. Read response until prompt.
   3. If response is empty, `"NO DATA"`, or `"?"`, record zero DTCs for that module (not an error — ABS is absent on non-Touring).
   4. Else parse frame: `_parse_j1850_response(raw_bytes, module_prefix)` returns list of raw 16-bit DTC codes.
   5. Decode each code: high nibble of high byte → character (`0x0`→P, `0x4`→C, `0x8`→B, `0xC`→U per SAE); override with Harley module-specific prefix if our bridge already routed it (i.e., we know BCM is always B-codes, so prefer `B` over the SAE nibble which Harley's proprietary ECM often sets wrong).
   6. Build `DTCReading(code="P0172", module="ECM", raw_hex="...", description_ref=None)` — `description_ref` is left None in this phase; Phase 140 joins against the DTC catalog.
2. Merge all three lists preserving order (ECM → BCM → ABS) and return.

`clear_dtc(module)`:
- If `module is None`, clear all three in order. Return count of successful clears.
- If `module` is specific (`"ECM"`, `"BCM"`, `"ABS"`), send only that command. Return `1` on success, raise `J1850ClearError` on bridge-reported failure.

#### 2d. Parser — `_parse_j1850_response(raw: bytes, expected_module: str) -> list[str]`
J1850 DTC payload, after the bridge strips framing, is a sequence of:
- Header byte (module ID echo, optional depending on bridge — `scan_gauge_ii` includes it, `daytona_twin_tec` doesn't)
- Count byte (how many 2-byte DTCs follow)
- N × 2-byte DTC codes
- Checksum byte (optional; some bridges strip it)

Steps:
1. Strip whitespace, uppercase, remove the bridge prompt byte if present.
2. Try hex-decode the remaining ASCII into bytes.
3. Heuristic header-detection: if first byte matches `MODULE_ADDRESS[expected_module]`, drop it.
4. If next byte ≤ 16, treat as count; else assume count omitted and take all pairs as DTCs.
5. For each 2-byte pair, format: `"{prefix}{high_nibble_low_bits:01X}{low_nibble_high:01X}{low_byte:02X}"` → e.g. `0x01 0x72` + prefix `P` → `"P0172"`.
6. Return list (may be empty).

This is **intentionally lenient** — Harley bridges are notoriously inconsistent about framing. Real-world robustness is Phase 146 (troubleshooting + recovery). Phase 138 covers the happy path and three well-documented bridge shapes.

#### 2e. Multi-ECM response handling
Key design decision: we do **not** run the three module reads in parallel. J1850 VPW is a shared bus with collision arbitration; overlapping requests from the bridge cause frame corruption. Sequential is correct and matches how Digital Tech II / Twin Tec tuners operate on the shop floor. Each module read is a blocking call with its own timeout; a frozen BCM does not block the ECM read because each command is issued only after the prior completes (or times out cleanly).

#### 2f. Error classes (module-local)
- `J1850Error(ProtocolAdapterError)` — base. (ProtocolAdapterError from Phase 134.)
- `J1850ConnectionError(J1850Error)` — handshake / port open failure.
- `J1850ClearError(J1850Error)` — `clear_dtc` rejected by bridge.
- `J1850ParseError(J1850Error)` — frame unintelligible.

These are exported from `j1850.py`; not re-exported from `protocols/__init__.py` yet (avoid polluting Phase 134's public surface before Phase 147).

### 3. `pyproject.toml` update
- Confirm `hardware` extras group exists (added by Phase 135 ELM327). If not, add `hardware = ["pyserial>=3.5"]` to `[project.optional-dependencies]` and include in `all` alias.
- Phase 138 imports `pyserial` lazily — unit tests inject `MockSerial`, so `pytest` passes without `pyserial` installed for anyone running only `pytest -k "not phase138_live"` (we don't add live tests here; everything is mocked).

### 4. Tests — `tests/test_phase138_j1850.py` (~22 tests, 6 classes)

#### TestMockSerial (3)
Sanity-check the test fixture itself before testing the adapter.
1. `test_mock_serial_write_records_bytes` — write queues bytes, `sent_frames` list grows.
2. `test_mock_serial_read_returns_scripted_response` — programmable per-command response map works.
3. `test_mock_serial_timeout_returns_empty` — no scripted response for a command → `read()` returns `b""` after timeout.

#### TestJ1850AdapterConnect (4)
1. `test_connect_sends_handshake_and_set_protocol` — verifies both bytes appear in `sent_frames` in order.
2. `test_connect_marks_connected` — `is_connected()` returns True after.
3. `test_connect_raises_on_handshake_timeout` — empty response → `J1850ConnectionError` with "handshake" substring.
4. `test_disconnect_closes_serial_and_clears_state` — post-disconnect `is_connected()` is False, mock `.close()` was called.

#### TestJ1850AdapterReadDTC (5)
1. `test_read_dtc_ecm_only_returns_p_codes` — mock scripts ECM returning two DTCs, BCM empty, ABS empty → result list length 2, both prefixed `P`.
2. `test_read_dtc_bcm_returns_b_codes` — BCM scripted with a body fault → `B1121` (security system ground fault, common on 2007-2010 Softails) decoded correctly, prefix is B not P even though SAE high-nibble might say otherwise.
3. `test_read_dtc_abs_returns_c_codes` — Touring-style response → `C1014` (ABS wheel-speed sensor rear) appears with prefix C.
4. `test_read_dtc_merges_all_three_modules_in_order` — ECM + BCM + ABS all have faults → result is `[P*, P*, B*, C*]` — order matters for UX in Phase 140's diagnosis screen.
5. `test_read_dtc_empty_when_no_faults` — all three scripted with `"NO DATA"` → returns `[]` without raising.

#### TestJ1850DtcParsing (4)
Unit tests on `_parse_j1850_response` in isolation (no adapter).
1. `test_parse_ecm_two_codes_with_header_and_count` — `"10 02 01 72 00 43"` with `expected_module="ECM"` → `["P0172", "P0043"]`.
2. `test_parse_bcm_single_code_no_header` — `"01 91 21"` with `expected_module="BCM"` → `["B1121"]`. Bridge stripped module-ID echo.
3. `test_parse_handles_whitespace_and_case` — `"10 02 01 72 00 43 >"` (with prompt byte mixed in) → same result; lenient cleanup.
4. `test_parse_empty_response_returns_empty_list` — `b""` or `b"NO DATA"` → `[]`.

#### TestJ1850BridgeVariants (3)
1. `test_daytona_twin_tec_uses_its_command_bytes` — adapter configured `bridge="daytona_twin_tec"` → `sent_frames` contains `b"AT@1\r"` (not `b"ATI\r"`).
2. `test_scan_gauge_ii_handshake_differs` — same test, different bridge, different bytes.
3. `test_unknown_bridge_raises_value_error` — `bridge="made_up"` → constructor raises `ValueError` with list of supported bridges.

#### TestJ1850ClearAndInfo (3)
1. `test_clear_dtc_all_sends_three_commands` — `clear_dtc()` with no arg → ECM, BCM, ABS clear bytes all sent, returns 3.
2. `test_clear_dtc_specific_module` — `clear_dtc("ECM")` → only ECM clear byte sent, returns 1.
3. `test_adapter_info_returns_protocol_metadata` — `adapter_info()` dict contains `protocol="J1850_VPW"`, `baud=10400`, `bridge="daytona_twin_tec"`, `port="COM_TEST"`.

All tests use a `MockSerial` fixture defined at top of test file — no `pytest-serial` dependency, no real hardware, zero API calls, zero live tokens.

### 5. ProtocolAdapter base contract (inherited, not modified)
Phase 138 assumes Phase 134 has landed `ProtocolAdapter` ABC at `src/motodiag/hardware/protocols/base.py` with method signatures matching section 2c above and a `ProtocolAdapterError` exception base. If Phase 134's actual signatures differ at build time, the Builder documents the deviation in v1.1 and adapts. Phase 138 does not block on Phase 134 details — this plan is self-describing enough to port.

## Key Concepts

- **J1850 VPW vs PWM**: Harley-Davidson used **Variable Pulse Width** at **10.4 kbps** on all pre-2011 bikes (Sportster 883/1200, Dyna, Softail, Touring with Evo/TC88/TC96 engines). Ford used PWM at 41.6 kbps — **do not confuse**. Our constant is `J1850_VPW_BAUD = 10400`. Anyone grafting Ford OBD tooling onto a Harley is in for a bad time.
- **Multi-module bus (ECM + BCM + ABS)**: Harleys from the late-90s onward have multiple modules on the same J1850 physical layer. A real diagnostic workflow must poll each module separately because they are separate ECUs with separate DTC tables. Digital Tech II does this by cycling through module addresses; we mirror that.
- **Harley DTC code prefixes**: `P` = powertrain (ECM — fuel, ignition, sensors), `B` = body (BCM — security, lights, turn signal module, speedometer), `C` = chassis (ABS on Touring / later Dyna — wheel speed, pump motor, valve solenoids). `U`-codes (network) are rare on J1850 because the bus itself is the "network"; they appear on 2011+ CAN bikes (Phase 136).
- **Bridge abstraction (Scan Gauge II / Daytona Twin Tec / Dynojet PC)**: no affordable direct-J1850 USB adapter exists as a first-class shop tool. Real mechanics use one of these bridges, which already speak J1850 to the bike and USB-serial to the laptop. Our adapter talks the serial protocol of the bridge, not raw J1850 frames. The `_BRIDGE_COMMANDS` dict isolates bridge-specific byte differences.
- **Lazy `pyserial` import**: mechanics running only cloud/KB features should not need `pyserial` installed. `_ensure_pyserial()` mirrors the Phase 132 `_ensure_markdown_installed()` pattern — install-hint ClickException on ImportError.
- **`serial_factory` DI for tests**: `MockSerial` is injected via constructor, not monkeypatch. Phase 131's cache fixture pattern. Test file has zero dependency on actual `pyserial`.
- **Sequential module polling (not parallel)**: J1850 is a shared-bus collision-arbitrated protocol. Parallel requests cause frame corruption. Sequential matches Digital Tech II behavior and is correct.
- **Lenient parser**: Harley bridges inconsistently include header bytes, count bytes, and checksums. `_parse_j1850_response` tolerates all three variants via heuristic. Robust frame-level error recovery is Phase 146 — this phase covers happy-path + three well-documented bridges.
- **`_BRIDGE_COMMANDS` dict, not class hierarchy**: adding a fourth bridge (say, `harley_digital_tech_ii` clone from AliExpress) is a single dict entry, not a new class. Extensibility bias toward data over code.
- **Prefix override over SAE nibble**: Harley's proprietary ECM sometimes emits the wrong high-nibble for non-P codes. We know from the module address which prefix is correct (ECM→P, BCM→B, ABS→C) and override. Future-proofs against ECM firmware variations.
- **No `read_live_data` yet**: live PIDs on J1850 are per-bike, per-model-year specific and need the PID map catalog built in Phase 141. This adapter raises `NotImplementedError` for `read_live_data` — Phase 140 (fault codes) does not call it.
- **No migration, no CLI, no schema change**: pure module addition. Zero risk to Phase 132's database or Phase 130's CLI surface. This phase is fully invisible to end-users until Phase 139 (auto-detect) and Phase 140 (fault code read/clear) wire it into the diagnostic flow.

## Verification Checklist
- [ ] `src/motodiag/hardware/protocols/j1850.py` exists and imports without side effects
- [ ] `J1850Adapter` inherits from `ProtocolAdapter` (Phase 134)
- [ ] `J1850_VPW_BAUD` constant equals `10400` (not 41600 — that's Ford PWM)
- [ ] `MODULE_ADDRESS` dict contains `"ECM": 0x10, "BCM": 0x40, "ABS": 0x28`
- [ ] `SUPPORTED_BRIDGES` contains at least `daytona_twin_tec`, `scan_gauge_ii`, `dynojet_pc`, `generic_j1850`
- [ ] `_ensure_pyserial()` raises ClickException with install hint when `pyserial` missing
- [ ] Constructor accepts `serial_factory` kwarg for test DI
- [ ] `connect()` sends handshake then set-protocol bytes in order; raises `J1850ConnectionError` on timeout
- [ ] `disconnect()` closes serial and clears `_connected`
- [ ] `read_dtc()` polls ECM, BCM, ABS in that order, sequentially, not in parallel
- [ ] `read_dtc()` returns merged `list[DTCReading]` with `module` field set per source
- [ ] `read_dtc()` returns `[]` (no raise) when all three modules respond empty / `NO DATA`
- [ ] `clear_dtc()` with no arg sends all three clear commands; returns count of successes
- [ ] `clear_dtc("ECM")` sends only ECM clear; raises `J1850ClearError` if bridge rejects
- [ ] `read_live_data(pid)` raises `NotImplementedError` with reference to Phase 141
- [ ] `adapter_info()` returns dict with protocol, baud, bridge, port
- [ ] `_parse_j1850_response` decodes `"10 02 01 72 00 43"` (ECM) → `["P0172", "P0043"]`
- [ ] `_parse_j1850_response` handles BCM single-code frame without header byte
- [ ] `_parse_j1850_response` strips prompt byte `>` and whitespace and is case-insensitive
- [ ] `_parse_j1850_response` returns `[]` on empty / `NO DATA` response
- [ ] Module prefix overrides SAE high-nibble (BCM frame returns `B*` not `P*`)
- [ ] Unknown bridge string raises `ValueError` in constructor with supported-list message
- [ ] `pyproject.toml` has `hardware` extras with `pyserial>=3.5` (confirmed or added)
- [ ] ~22 new tests in `tests/test_phase138_j1850.py` across 6 classes, all pass
- [ ] Zero regressions in Phases 01-132 test suite
- [ ] Zero live API tokens burned (pure mock-serial, no AI)
- [ ] Zero real hardware required for any test

## Risks

- **Phase 134 `ProtocolAdapter` contract drift**: we are planning Phase 138 before Phase 134 is built. If Phase 134's actual method signatures differ (e.g., it names the method `read_fault_codes` instead of `read_dtc`), Builder adapts at build time and logs a v1.2 deviation. Mitigation: the plan is deliberately self-describing — every signature is spelled out so the adapter works even if we rewrote the base contract.
- **Bridge byte tables not calibrated against real hardware**: `_BRIDGE_COMMANDS` is researched from published Daytona Twin Tec / Scan Gauge II / Dynojet documentation but is not shop-floor validated in this phase. Phase 147 (Gate 6) is the integration test that plugs into a real bike. Expect `_BRIDGE_COMMANDS` byte corrections in Phase 147 or a follow-up tuning phase. **This is by design** — Phase 138 is about the adapter *shape*, not exhaustive byte-perfect compatibility.
- **Harley-proprietary DTC codes outside SAE J2012**: some Harley B-codes (e.g., `B2185` turn-signal module serial-link loss on 2007-10 Softails) are not in standard SAE tables. Phase 140's DTC catalog handles description mapping; this adapter only returns the code string, so Harley-proprietary codes flow through unchanged. No risk to the adapter itself.
- **ABS module absence on non-Touring bikes**: `read_dtc_abs` on a Dyna without ABS returns `NO DATA`. We treat this as zero DTCs, not as an error. Edge case: some bridges return `?` or `UNABLE TO CONNECT` instead — `_parse_j1850_response` treats both as empty lists. Logged.
- **J1850 bus collision on parallel module polling**: mitigated by sequential design. Documented in Key Concepts so no future refactor accidentally introduces `asyncio.gather` here.
- **Timeout of 2.5s may be too short for cold-bus cranking-on ECMs**: pre-2007 Sportster ECMs can take 3+ seconds to respond on first query after ignition-on. Phase 146 adds retry + longer cold-start timeout. Phase 138 uses 2.5s as a middle ground; constructor exposes `timeout_s` for override.
- **Optional `pyserial` test-collection failures**: if a developer runs `pytest` without `pyserial` installed, import of the production `j1850.py` must not fail at collection. Lazy import (`_ensure_pyserial()` only called inside `connect()`, never at module top) handles this. The test file itself imports `J1850Adapter` but never triggers `_ensure_pyserial` because `serial_factory=MockSerial` short-circuits before the pyserial check. Verified in Verification Checklist.
- **Windows COM port permission flakiness**: not relevant in this phase — no real ports opened in tests. Phase 147 deals with it.
