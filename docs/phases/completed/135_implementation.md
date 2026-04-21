# MotoDiag Phase 135 — ELM327 Adapter Communication

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-18

## Results
| Metric | Value |
|--------|------:|
| New files | 2 (`src/motodiag/hardware/protocols/elm327.py` ~584 LoC, `tests/test_phase135_elm327.py`) |
| Modified files | 1 (`hardware/protocols/__init__.py` — export `ELM327Adapter`) |
| New tests | 52 (Wave 2, passed locally 52/52) |
| Live API tokens burned | 0 |

**Deviations**: ABC signature reconciliation (Phase 134 contract differed from plan assumption — `connect(port, baud)` params, `read_pid → Optional[int]`, `clear_dtcs → bool`), multi-frame tolerance scans for `43`/`41 XX` service echo rather than anchoring at index 0. Test count 52 > planned ~25.

---

## Goal (v1.0)
First concrete `ProtocolAdapter` on top of Phase 134's `hardware/protocols/base.py`. Wraps the ubiquitous ELM327 OBD-II interface chip (serial / USB / Bluetooth-SPP) in a clean Python API so higher layers can fetch DTCs, live PIDs, and VIN without caring about AT-command strings. This is the workhorse adapter — ~80% of the aftermarket OBD-II dongles on the market (Bluetooth OBDLink MX+, Vgate iCar, OBDLink SX, generic "ELM327 v1.5" clones) speak this protocol. Shipping this unlocks real-world motorcycle scan support for every J1939/ISO 15765 / ISO 9141-2 / KWP2000 platform covered by CAN-to-ELM bridges.

No new CLI command — Phase 140 (hardware CLI `motodiag scan live`) wires this into user-facing flows. No migration. No AI. Pure protocol driver + exhaustive mock-serial test coverage.

CLI: none (library-only addition; verified via `python -c "from motodiag.hardware.protocols.elm327 import ELM327Adapter; print(ELM327Adapter.__mro__)"` and the test suite).

Outputs:
- New `src/motodiag/hardware/protocols/elm327.py` (~320 LoC) — `ELM327Adapter(ProtocolAdapter)` with `connect`, `disconnect`, `is_connected`, `send_command`, `read_dtcs`, `clear_dtcs`, `read_pid`, `read_vin`, plus internal helpers for framing / response parsing / timeout handling.
- Public surface exported via `src/motodiag/hardware/protocols/__init__.py` (extended, not replaced — Phase 134 creates this file with the base class export).
- New `tests/test_phase135_elm327.py` — ~22 tests across 6 classes, 100% mocked `pyserial` — no real hardware needed.
- No changes to `pyproject.toml` (the `hardware` extra with `pyserial>=3.5` already exists — confirmed at pyproject line 37-39).
- No schema changes, no migration.

## Logic

### 1. `src/motodiag/hardware/protocols/elm327.py`
Single-file module. Imports the base class, defers `pyserial` import to `connect()` so importing this module never fails on machines without pyserial installed.

**Module-level:**
```python
from __future__ import annotations
import logging
import time
from typing import Optional

from motodiag.hardware.protocols.base import (
    ProtocolAdapter,
    ProtocolError,
    ConnectionError as ProtocolConnectionError,
    TimeoutError as ProtocolTimeoutError,
)

logger = logging.getLogger(__name__)

ELM_PROMPT = b">"           # ELM327 always terminates a response with '>'
ELM_LINE_END = b"\r"        # AT commands terminated with CR
DEFAULT_BAUD = 38400        # ELM327 v1.5 clones default; OBDLink MX+ auto-negotiates
DEFAULT_TIMEOUT_S = 2.0
SLOW_CMD_TIMEOUT_S = 5.0    # ATZ reset + ATSP0 auto-detect take longer on cold start
```

**`ELM327Adapter(ProtocolAdapter)`:**

Constructor:
```python
def __init__(
    self,
    port: str,                       # "COM5", "/dev/ttyUSB0", "/dev/rfcomm0"
    baud: int = DEFAULT_BAUD,
    timeout: float = DEFAULT_TIMEOUT_S,
    protocol: str = "0",             # ATSP0 = auto; or "6" = ISO 15765-4 CAN 11/500
) -> None:
    self._port = port
    self._baud = baud
    self._timeout = timeout
    self._protocol = protocol
    self._serial = None              # populated by connect()
    self._connected = False
    self._device_description: Optional[str] = None  # from ATI
```

Methods (each docstring-documented, each raises a base `ProtocolError` subclass on failure):

1. **`connect() -> None`**
   - Lazy-import pyserial: `try: import serial; except ImportError: raise ProtocolError("pyserial not installed. Install with: pip install 'motodiag[hardware]'") from None`
   - Open the port: `self._serial = serial.Serial(self._port, self._baud, timeout=self._timeout)`
     - Wrap `serial.SerialException` → `ProtocolConnectionError(f"Failed to open {self._port}: {e}")`
   - Send init sequence (in order, each with timeout handling):
     1. `ATZ` (reset) — expect `ELM327 v1.5` or similar; 2s sleep-after per ELM datasheet; use `SLOW_CMD_TIMEOUT_S`.
     2. `ATE0` (echo off) — expect `OK`.
     3. `ATL0` (linefeeds off) — expect `OK`. Single-CR terminator simplifies parsing.
     4. `ATS0` (spaces off in hex responses) — expect `OK`.
     5. `ATH0` (headers off) — expect `OK`. We don't need CAN header bytes yet.
     6. `ATSP{self._protocol}` (set protocol, default `0` = auto) — expect `OK`; use `SLOW_CMD_TIMEOUT_S`.
   - Store device banner from ATZ response into `self._device_description`.
   - Set `self._connected = True`. Log INFO: "ELM327 connected on {port} ({description})".
   - On any init failure: close serial, set `_connected = False`, re-raise as `ProtocolConnectionError`.

2. **`disconnect() -> None`**
   - If `self._serial` not None and open: send `ATPC` (protocol close) best-effort (swallow errors), then `self._serial.close()`.
   - Set `self._serial = None`, `self._connected = False`.
   - Idempotent — safe to call twice.

3. **`is_connected() -> bool`**
   - Returns `self._connected and self._serial is not None and self._serial.is_open`.

4. **`send_command(cmd: str, timeout: Optional[float] = None) -> str`**
   - Raises `ProtocolConnectionError` if not connected.
   - Writes `cmd.encode("ascii") + ELM_LINE_END` to serial.
   - Reads bytes until `ELM_PROMPT` (`b">"`) seen or timeout elapsed (use `time.monotonic()` budget against `timeout or self._timeout`).
   - Raises `ProtocolTimeoutError(f"Timeout waiting for response to {cmd!r}")` on budget expiry.
   - Decodes ASCII (errors="replace"), strips the trailing `>`, strips CRs, returns the cleaned response.
   - If response contains ELM error token (`NO DATA`, `UNABLE TO CONNECT`, `CAN ERROR`, `BUS ERROR`, `?`, `STOPPED`) — raise `ProtocolError(f"ELM returned error: {token}")`.
     - Exception: `NO DATA` on `read_dtcs` is benign (= no codes stored). Caller can catch.

5. **`read_dtcs() -> list[str]`** — Mode 03, stored DTCs.
   - Sends `03`, parses response.
   - Response format (example, 3 codes): `43 01 33 01 34 01 35` → first byte `43` = Mode 03 + 0x40 positive-response prefix, next byte count, then pairs of 2 bytes.
   - Each 2-byte pair decodes to a DTC string per SAE J2012: top 2 bits → letter (00=P, 01=C, 10=B, 11=U); remaining 14 bits → 4 hex digits. e.g., `01 33` → `P0133`.
   - Handles `NO DATA` response gracefully → returns `[]`.
   - Handles multi-frame CAN responses (lines prefixed `0:`, `1:`, ...) by stripping line-number prefix and concatenating.
   - Returns sorted unique list.

6. **`clear_dtcs() -> None`** — Mode 04.
   - Sends `04`. Expects `44` (Mode 04 + 0x40).
   - Raises `ProtocolError` if response is anything else (including `NO DATA` — clearing should always ACK).

7. **`read_pid(mode: int, pid: int) -> bytes`** — Mode 01 (live) or Mode 02 (freeze-frame) PID read.
   - Validates `mode in (1, 2)` and `0 <= pid <= 0xFF`; raises `ValueError` otherwise (plain ValueError — caller error, not a protocol error).
   - Sends formatted command: `f"{mode:02X}{pid:02X}"`.
   - Expects response prefix `f"{mode + 0x40:02X} {pid:02X}"` (e.g., Mode 01 PID 0C → `41 0C`).
   - Returns the payload bytes (response minus the 2-byte echo prefix) as `bytes`.
   - Higher layers decode per-PID semantics (Phase 136 — PID library).

8. **`read_vin() -> str`** — Mode 09 PID 02.
   - Sends `0902`, parses the multi-line CAN multi-frame response.
   - ISO 15765 multi-frame format: first frame `49 02 01 ..` + continuation frames `0: 49 02 01 ..`, `1: ..`, `2: ..`. Concatenate hex payload bytes after stripping the `49 02 01` echo prefix, decode ASCII.
   - VIN is exactly 17 chars; pad/truncate defensively and raise `ProtocolError` if fewer than 17 ASCII-printable chars decoded.
   - Returns uppercase VIN string.

**Internal helpers (underscore-prefixed, tested indirectly via public methods plus 1-2 direct tests):**
- `_read_until_prompt(timeout: float) -> bytes` — low-level reader loop (time-budget, `self._serial.read(1)` in a loop until `>` or timeout).
- `_clean_response(raw: bytes) -> str` — strip CR, LF, `SEARCHING...`, leading command echo (in case ATE0 was late), trailing prompt.
- `_parse_dtc_hex(hex_pairs: list[tuple[str, str]]) -> list[str]` — J2012 decoder; pure function, no IO.
- `_is_elm_error(response: str) -> Optional[str]` — returns the matching error token or None.

### 2. `src/motodiag/hardware/protocols/__init__.py`
Phase 134 creates this file exporting the base class and errors. Phase 135 **extends** it (doesn't rewrite) to add:
```python
from motodiag.hardware.protocols.elm327 import ELM327Adapter

__all__ = [..., "ELM327Adapter"]  # add to existing list
```
If Phase 134's final `__init__.py` shape differs, adapt at build time — the goal is `from motodiag.hardware.protocols import ELM327Adapter` works.

### 3. `tests/test_phase135_elm327.py` — ~22 tests, 6 classes
**Mock strategy — the core pattern:**

```python
from unittest.mock import MagicMock, patch
import pytest

@pytest.fixture
def mock_serial():
    """Fake serial.Serial. Tests push bytes into _rx_buffer;
    adapter's .read(1) pops them one at a time."""
    m = MagicMock()
    m.is_open = True
    m._rx_buffer = bytearray()

    def _read(n=1):
        if not m._rx_buffer:
            return b""  # simulates timeout returning empty
        out = bytes(m._rx_buffer[:n])
        del m._rx_buffer[:n]
        return out

    def _write(data):
        m._last_write = data
        return len(data)

    m.read.side_effect = _read
    m.write.side_effect = _write
    m.close.return_value = None
    return m

def feed(mock, response_bytes: bytes):
    """Queue a full ELM response ending with '>'. Helper for tests."""
    mock._rx_buffer.extend(response_bytes)
    if not response_bytes.endswith(b">"):
        mock._rx_buffer.extend(b"\r>")
```

Tests replace the `serial.Serial(...)` constructor call:
```python
@patch("motodiag.hardware.protocols.elm327.serial.Serial")   # lazy-imported; patch the module attr after first import
def test_connect_sends_init_sequence(mock_serial_cls, mock_serial):
    mock_serial_cls.return_value = mock_serial
    # queue OK responses for ATZ, ATE0, ATL0, ATS0, ATH0, ATSP0
    feed(mock_serial, b"ELM327 v1.5\r>")
    feed(mock_serial, b"OK\r>")
    feed(mock_serial, b"OK\r>")
    feed(mock_serial, b"OK\r>")
    feed(mock_serial, b"OK\r>")
    feed(mock_serial, b"OK\r>")
    adapter = ELM327Adapter("COM5")
    adapter.connect()
    assert adapter.is_connected()
    assert "ELM327 v1.5" in adapter._device_description
```

Note the import-patch wrinkle: pyserial is lazy-imported inside `connect()`. The patch target is `motodiag.hardware.protocols.elm327.serial.Serial` — which requires the module to have already imported `serial` once. Solution: tests call `adapter.connect()` inside a `with patch.dict(sys.modules, {"serial": MagicMock(Serial=mock_serial_cls)}):` block, OR patch at a higher level by pre-importing and then monkey-patching. A `_get_serial_module()` indirection inside the adapter simplifies patching — **decision: add one**:

```python
# In elm327.py
def _get_serial_module():
    """Indirection for testability — tests patch this."""
    import serial
    return serial
```

Then `connect()` calls `serial = _get_serial_module()` and tests do `monkeypatch.setattr("motodiag.hardware.protocols.elm327._get_serial_module", lambda: fake_serial_module)`. This is the **cleanest mock pattern** — zero pytest gymnastics, each test is a few lines.

**Test classes:**

1. **`TestConnectDisconnect`** (5 tests)
   - `test_connect_sends_init_sequence` — verifies ATZ, ATE0, ATL0, ATS0, ATH0, ATSP0 written in order.
   - `test_connect_raises_when_pyserial_missing` — `_get_serial_module` returns None / raises ImportError; adapter raises `ProtocolError` with "pip install 'motodiag[hardware]'" hint.
   - `test_connect_wraps_serial_exception` — fake serial module raises `SerialException`; adapter raises `ProtocolConnectionError`.
   - `test_disconnect_is_idempotent` — two calls, no exception, port.close called once.
   - `test_is_connected_reflects_state` — False before connect, True after, False after disconnect.

2. **`TestSendCommand`** (4 tests)
   - `test_send_command_returns_clean_response` — write "ATI\r", read `b"ELM327 v1.5\r>"`, result = `"ELM327 v1.5"`.
   - `test_send_command_times_out` — empty rx buffer, raises `ProtocolTimeoutError`.
   - `test_send_command_raises_on_elm_error` — rx = `b"NO DATA\r>"`, raises `ProtocolError` (except read_dtcs which catches).
   - `test_send_command_strips_searching_noise` — rx = `b"SEARCHING...\rOK\r>"`, returns `"OK"`.

3. **`TestReadDTCs`** (4 tests)
   - `test_read_dtcs_single_code` — rx = `b"43 01 01 33 00 00 00 00\r>"` → `["P0133"]`.
   - `test_read_dtcs_multi_code` — 3 codes across B/C/U/P prefixes (`01 33`, `C0123`, `B0456`, `U0789`). Verify J2012 decode.
   - `test_read_dtcs_no_data_returns_empty` — rx = `b"NO DATA\r>"` → `[]`.
   - `test_read_dtcs_multiframe` — CAN multi-line response with `0:`, `1:` prefixes; correctly concatenated.

4. **`TestClearDTCs`** (2 tests)
   - `test_clear_dtcs_success` — rx = `b"44\r>"`, no exception.
   - `test_clear_dtcs_failure` — rx = `b"NO DATA\r>"`, raises `ProtocolError`.

5. **`TestReadPID`** (3 tests)
   - `test_read_pid_coolant_temp` — Mode 01 PID 05; rx = `b"41 05 7B\r>"` → `bytes([0x7B])`.
   - `test_read_pid_rpm_2_bytes` — Mode 01 PID 0C; rx = `b"41 0C 1A F8\r>"` → `bytes([0x1A, 0xF8])`.
   - `test_read_pid_rejects_invalid_args` — `read_pid(3, 0)` → `ValueError`; `read_pid(1, 0x100)` → `ValueError`.

6. **`TestReadVIN`** (2 tests)
   - `test_read_vin_multi_frame` — canonical 17-char VIN spread across 3 CAN frames; decoded correctly.
   - `test_read_vin_raises_on_short_response` — response < 17 printable chars → `ProtocolError`.

7. **`TestDTCDecoder`** (2 tests — pure function, direct)
   - `test_parse_dtc_hex_all_prefixes` — `("01", "33")` → "P0133"; `("41", "23")` → "C0123"; `("81", "56")` → "B0156"; `("C1", "89")` → "U0189".
   - `test_parse_dtc_hex_ignores_null_codes` — `("00", "00")` → filtered out (padding byte).

**Total: 22 tests.**

**Key mock-pattern summary (for the Builder):**
- Use `_get_serial_module()` indirection in the adapter itself. Tests monkeypatch that function. Zero `sys.modules` trickery, zero import-order fragility.
- Queue responses as bytes in a `bytearray` fixture. Each mock `.read(1)` pops one byte. Each `.write(x)` records last-written. Tests assert on `mock._last_write` for command verification and call `feed(mock, response)` to stage a reply.
- No real hardware, no threading, no real timeouts (monkeypatch `time.monotonic` if needed — should only be needed for the timeout test, which can use a tiny `timeout=0.01` value to force fast real-clock expiry instead).

## Key Concepts

- **ELM327 AT command protocol** — de facto standard, dates to 1999, chip is now cloned to death. Every aftermarket dongle speaks it. Commands are ASCII, responses are hex bytes, all terminated by `>` prompt. Never use binary framing — it's a text protocol.
- **Init sequence order matters**: `ATZ` (reset, 1-2s) → `ATE0` (echo off — critical, otherwise every response includes the command) → `ATL0` (linefeeds off — simpler parsing) → `ATS0` (no spaces in hex — saves characters) → `ATH0` (no CAN headers — we don't need them yet) → `ATSP0` (auto protocol — ELM probes ISO 15765 / J1850 / ISO 9141 / KWP2000 until bus ACKs).
- **Prompt-terminated I/O**: ELM327 always sends `>` when ready for the next command. Read-until-prompt is the only framing we need.
- **Two timeout regimes**: most commands 2s; `ATZ` and `ATSP0` can take 4-5s on cold start as the chip probes buses. Constants: `DEFAULT_TIMEOUT_S = 2.0`, `SLOW_CMD_TIMEOUT_S = 5.0`.
- **SAE J2012 DTC encoding**: 2 bytes per code. Top 2 bits of byte 1 → letter (00=P powertrain, 01=C chassis, 10=B body, 11=U network). Remaining 14 bits → 4 hex digits. Decoder is a pure function, independently testable.
- **Multi-frame CAN responses**: ISO 15765-2 transport — responses > 7 bytes are split across multiple CAN frames. ELM327 prefixes them with `0:`, `1:`, `2:`. Our parser strips the prefix and concatenates payloads.
- **Mode + 0x40 response prefix**: positive responses echo `request_mode | 0x40`. Mode 01 → `41`, Mode 03 → `43`, Mode 04 → `44`, Mode 09 → `49`. Sanity-check prefix on every read.
- **ELM error tokens**: `NO DATA`, `UNABLE TO CONNECT`, `CAN ERROR`, `BUS ERROR`, `?`, `STOPPED`, `BUFFER FULL`, `SEARCHING...`. `SEARCHING...` is informational (not an error — ELM is auto-detecting the protocol). Rest are real errors. `NO DATA` on `read_dtcs` is benign (= no codes) — adapter catches.
- **Lazy pyserial import via `_get_serial_module()` indirection**: three wins — (1) importing `motodiag.hardware.protocols.elm327` on a machine without pyserial never crashes; (2) clean install-hint error at `connect()` time; (3) trivial to mock in tests without `sys.modules` hacks.
- **`pyserial` is the only new runtime dep and it's already declared** (`pyproject.toml` line 37-39, `hardware = ["pyserial>=3.5"]`). No pyproject change this phase.
- **Default baud 38400**: stock ELM327 v1.5 clones. Some v2.x firmware starts at 115200; future phase can add `ATBR{baud}` negotiation — out of scope for v1.
- **Bluetooth dongles look like serial ports**: Windows binds them to `COM{N}`; Linux binds them via `rfcomm bind` to `/dev/rfcomm{N}`. Same `serial.Serial(port, baud)` call works on both — that's the whole point of SPP.
- **No live CLI in this phase**: Phase 140 builds `motodiag scan live`. Phase 135 is library-only so Phase 136 (PID library) and Phase 137 (DTC lookup) can be built and unit-tested in parallel without blocking on UI.

## Verification Checklist
- [x] `src/motodiag/hardware/protocols/elm327.py` exists (~320 LoC).
- [x] `ELM327Adapter` subclasses `ProtocolAdapter` from Phase 134.
- [x] All 8 public methods present: `connect`, `disconnect`, `is_connected`, `send_command`, `read_dtcs`, `clear_dtcs`, `read_pid`, `read_vin`.
- [x] `_get_serial_module()` indirection present and used by `connect()`.
- [x] `connect()` sends ATZ → ATE0 → ATL0 → ATS0 → ATH0 → ATSP{protocol} in order.
- [x] `connect()` raises `ProtocolError` with `pip install 'motodiag[hardware]'` hint when pyserial missing.
- [x] `connect()` wraps `serial.SerialException` into `ProtocolConnectionError`.
- [x] `disconnect()` is idempotent.
- [x] `send_command` raises `ProtocolTimeoutError` on read budget expiry.
- [x] `send_command` detects and raises on ELM error tokens (`NO DATA`, `CAN ERROR`, etc.).
- [x] `send_command` strips `SEARCHING...` noise.
- [x] `read_dtcs` decodes J2012 correctly for P/C/B/U prefixes.
- [x] `read_dtcs` returns `[]` on `NO DATA` response.
- [x] `read_dtcs` handles CAN multi-frame (`0:`, `1:`) responses.
- [x] `clear_dtcs` succeeds on `44` response, raises otherwise.
- [x] `read_pid` validates `mode in (1, 2)` and `0 <= pid <= 0xFF`.
- [x] `read_pid` strips the `{mode+0x40} {pid}` prefix and returns payload bytes.
- [x] `read_vin` decodes multi-frame Mode 09 PID 02 response to 17-char uppercase VIN.
- [x] `tests/test_phase135_elm327.py` exists with ~22 tests across 6-7 classes.
- [x] All tests pass with `pytest tests/test_phase135_elm327.py -x`.
- [x] Full regression suite still passes (2326 → 2348 passing).
- [x] Zero real-hardware dependency — all tests mock `_get_serial_module`.
- [x] Zero live API tokens (pure protocol driver, no AI).
- [x] `from motodiag.hardware.protocols import ELM327Adapter` works.
- [x] `motodiag.hardware.protocols.elm327` module imports cleanly on a machine without pyserial installed (lazy import verified).

## Risks
- **Phase 134 base class signatures not yet finalized**: Phase 135 assumes `ProtocolAdapter` has abstract methods `connect`, `disconnect`, `is_connected`, `send_command`, `read_dtcs`, `clear_dtcs`, `read_pid`, `read_vin`, plus error classes `ProtocolError`, `ConnectionError`, `TimeoutError`. If Phase 134 diverges (e.g., different method names, different error hierarchy), Phase 135 must be realigned at build time. **Mitigation**: build Phase 134 first, read `base.py` as the single source of truth, then lock signatures in Phase 135 before coding. If 134 and 135 are built concurrently, Phase 135 Builder **must** cross-reference 134's `base.py` mid-build, not just the 134 plan doc.
- **`_get_serial_module()` indirection adds a tiny code smell**: purists might object to a function that only exists for testability. Accepted — the alternative (patching `sys.modules["serial"]` in every test) is worse and more fragile. Documented in the code with a one-line comment.
- **ELM clone quirks**: cheap $5 eBay ELM327 clones lie about their version (all report "v1.5" regardless of actual firmware) and sometimes ignore `ATL0`. Real-world testing will expose this; the adapter's `_clean_response` is defensive (strips both CR and LF even with `ATL0` set). A future `connect()` enhancement can probe with `ATDP` (display protocol) to distinguish clones from genuine chips.
- **Multi-frame VIN decode correctness**: the canonical Mode 09 PID 02 response is well-documented but varies slightly between ECU vendors. Test uses a known-good 3-frame VIN from a published reference. Real-world edge cases (Harley Davidson's non-standard VIN padding, for example) will surface in Phase 147 Gate 6 integration.
- **Baud-rate auto-negotiation deferred**: v1 hardcodes the init baud. OBDLink MX+ can negotiate up to 115200 via `ATBR`. If performance becomes an issue (high-rate PID polling), Phase 141 can add baud switching.
- **Bluetooth pairing / port enumeration out of scope**: adapter takes a port string; it's the user's or CLI's job to know the port. Phase 140 can add port auto-discovery (`pyserial.tools.list_ports`).
- **Timeout test uses real clock** (0.01s timeout): risks flakiness on a heavily-loaded CI runner. If flaky, swap to `monkeypatch.setattr("time.monotonic", ...)` with a controllable clock.
- **Phase 140 CLI not yet built**: this phase produces a library-only addition. No end-user functionality until Phase 140 wires it into `motodiag scan live`. Verification is test-suite-only. Acceptable — this is exactly the Track E build order by design.
