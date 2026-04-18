# MotoDiag Phase 137 — K-line / KWP2000 Protocol Adapter (ISO 14230)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-18

## Results
| Metric | Value |
|--------|------:|
| New files | 2 (`src/motodiag/hardware/protocols/kline.py` ~670 LoC, `tests/test_phase137_kline.py` ~775 LoC) |
| New tests | 44 (passed locally 44/44 in 0.96s) |
| Live API tokens burned | 0 |

**Deviations**: ABC signature reconciliation (same pattern as 135/136). `_build_frame`/`_parse_frame` module-level pure functions for testability. DTC decode corrected: `(0x02, 0x01) → P0201`. `read_vin` uses SID 0x1A identifier 0x90. Write services (0x27/0x2E/0x31) out of scope (tune-writing safety).

---

## Goal (v1.0)
Add a second concrete `ProtocolAdapter` implementation (after Phase 136's CAN adapter): a K-line / KWP2000 (ISO 14230-4) adapter covering the 90s/2000s Japanese sport-bike era — Honda CBR600/900/1000RR, Kawasaki ZX-6R/ZX-10R, Suzuki GSX-R/SV650, Yamaha YZF-R1/R6 — and many Euro bikes of the same vintage (Aprilia RSV, Ducati 748/996/998, KTM LC4/Adventure) before they migrated to CAN. K-line is electrically simple (a single bidirectional data line + ground, typically 12V idle with active-low signalling) but protocol-wise it's finicky: a slow-baud wakeup handshake, strict inter-byte and inter-message timing windows, and the transmitter reads its own transmissions back (local echo) which must be filtered out before treating incoming bytes as ECU responses.

This phase wires that protocol on top of `pyserial`, uses `ProtocolAdapter` as the abstract parent (defined in Phase 134), exposes KWP2000 diagnostic services 0x10/0x11/0x14/0x18/0x1A, and ships ~20-25 unit tests that drive a mocked serial port through every bytewise corner — wakeup, framing, checksum, echo cancellation, short/long reads, and defensive failure modes. No CLI wiring and no migration land in this phase — Phase 140 (connection manager) picks the adapter up and plumbs it into `motodiag connect`.

CLI: *(none — library-only phase. Phase 140 wires `motodiag connect --protocol kline`.)*

Outputs:
- `src/motodiag/hardware/protocols/__init__.py` — package marker (created if missing; Phase 136 may already have created it)
- `src/motodiag/hardware/protocols/kline.py` — `KLineAdapter(ProtocolAdapter)` implementation (~450-550 LoC)
- `tests/test_phase137_kline.py` — ~20-25 tests using `unittest.mock` to fake the serial port
- *No* `pyproject.toml` change — `pyserial` is already declared in the existing `motodiag[hardware]` optional-dependencies group (see Phase 135 or whichever phase first added it).

## Logic

### 1. `src/motodiag/hardware/protocols/kline.py`

Single module with one public class `KLineAdapter`, a small set of module-level constants for KWP2000 service IDs and timing windows, and two private helper functions for framing.

#### 1.1 Module constants
```python
# KWP2000 diagnostic service identifiers (ISO 14230-3)
SID_START_DIAGNOSTIC_SESSION = 0x10
SID_ECU_RESET                = 0x11
SID_CLEAR_DIAGNOSTIC_INFO    = 0x14
SID_READ_DTC_BY_STATUS       = 0x18
SID_READ_ECU_IDENTIFICATION  = 0x1A

POSITIVE_RESPONSE_OFFSET = 0x40   # ECU response SID = request SID + 0x40
NEGATIVE_RESPONSE_SID    = 0x7F   # ECU sends 0x7F <requestedSID> <NRC> on error

# KWP2000 "Start Diagnostic Session" subfunctions
DIAG_MODE_DEFAULT        = 0x81
DIAG_MODE_ECU_PROGRAMMING = 0x85
DIAG_MODE_ECU_ADJUSTMENT  = 0x87

# Default K-line physical addresses (can be overridden per-make)
ADDR_TESTER_DEFAULT = 0xF1   # SAE J2190 convention
ADDR_ECU_DEFAULT    = 0x11   # ISO 14230 default ECU address; many Jp bikes use 0x11 or 0x12

# ISO 14230-2 timing (milliseconds)
P1_MAX = 20    # Inter-byte time in ECU response
P2_MIN = 25    # Time between tester request end and ECU response start
P2_MAX = 50    # Max time before we declare timeout (ECU may extend via 0x78 NRC)
P3_MIN = 55    # Time between ECU response end and next tester request
P3_MAX = 5000  # Max idle before session is lost
P4_MIN = 5     # Inter-byte time in tester request

W1_MAX = 300   # Max time from tester end-of-wakeup to ECU sync byte
W2_MAX = 20    # Max time ECU takes to send keybyte 1 after sync
W3_MAX = 20    # Max time between ECU keybyte 1 and keybyte 2
W4       = 25  # Tester wait before inverting keybyte 2
W5_MIN = 300   # Minimum bus-idle time before a new 5-baud init

FAST_INIT_TINIL = 25   # WakeUp "low" time for fast init (ms)
FAST_INIT_TWUP  = 50   # Full wakeup pattern time for fast init (ms)
```

Constants are declared at module level so tests can import and assert timing values without touching private state.

#### 1.2 `KLineAdapter` class skeleton

```python
class KLineAdapter(ProtocolAdapter):
    """KWP2000 over K-line (ISO 14230-4) adapter.

    Works with a USB-to-serial K-line interface (typically an FTDI FT232RL or
    CH340 wired to a 12V tolerant transceiver — e.g., a MC33290 or a bespoke
    bike-ECU cable). The UART drives the K-line at either 10400 or 9600 baud
    once the wakeup handshake completes.
    """

    PROTOCOL_NAME = "kline"  # matches ProtocolAdapter.PROTOCOL_NAME contract

    def __init__(
        self,
        port: str,
        baud: int = 10400,
        ecu_address: int = ADDR_ECU_DEFAULT,
        tester_address: int = ADDR_TESTER_DEFAULT,
        init_mode: Literal["slow", "fast"] = "slow",
        read_timeout: float = 1.0,
    ) -> None: ...
```

Key field defaults:
- `baud=10400` — KWP2000 canonical. `baud=9600` allowed for older Honda/Suzuki platforms that run slower.
- `init_mode="slow"` — 5-baud address-byte init (works on 100% of bikes we target). `"fast"` is the ISO 14230-2 fast-init for newer ECUs that honor it.
- `read_timeout=1.0s` — wall-clock read timeout per serial read; used as an upper bound, not a precise inter-byte clock (KWP2000's true P1/P2 timing is enforced at a higher layer using `time.monotonic()`).

#### 1.3 `connect()` — two-path wakeup

```python
def connect(self) -> None:
    self._ensure_pyserial()
    self._open_serial()
    try:
        if self.init_mode == "slow":
            self._slow_baud_init()
        else:
            self._fast_init()
        self._start_diagnostic_session()
        self._connected = True
    except Exception:
        self._close_serial_safe()
        raise
```

##### `_slow_baud_init()` — 5-baud address init (ISO 14230-2 §4.2.1)

This is the defining handshake for legacy Japanese bikes. The tester holds the K-line low for 200 ms (start bit), then clocks out the ECU target address (`ADDR_ECU_DEFAULT = 0x11` or a make-specific value) bit-by-bit at 5 bits per second — each bit takes 200 ms, so the whole address byte takes ~1800 ms. After the address frame, the ECU replies at the real baud rate (10400 or 9600) with a synchronization pattern `0x55`, followed by two keybytes (keyBytes 1 and 2). The tester then inverts keyByte 2 and sends it back; the ECU finally inverts the tester address byte (`~0x11 = 0xEE`) and returns it, completing the handshake.

Implementation strategy:
```python
def _slow_baud_init(self) -> None:
    # pyserial doesn't support 5 baud directly on most USB-serial chips. We
    # fake it by toggling break/line manually with precise timing.
    #
    # 1. Drive K-line low (break signal) for 200 ms — start bit.
    # 2. For each bit of ecu_address (LSB-first), drive line high (mark) for
    #    200 ms per 1-bit, low (space) for 200 ms per 0-bit.
    # 3. Drive high for 200 ms — stop bit.
    # 4. Switch serial to real baud (10400 or 9600) and read sync + keybytes.

    self._serial.baudrate = 5
    self._serial.break_condition = True
    time.sleep(0.2)
    for i in range(8):
        bit = (self.ecu_address >> i) & 1
        self._serial.break_condition = (bit == 0)  # break = low = logical 0
        time.sleep(0.2)
    self._serial.break_condition = False  # stop bit (mark)
    time.sleep(0.2)

    # Switch to real baud
    self._serial.baudrate = self.baud

    # Read sync byte (0x55), then keybyte1, keybyte2, within W1_MAX + W2_MAX + W3_MAX
    sync = self._read_exact(1, timeout_ms=W1_MAX)
    if sync != b"\x55":
        raise ProtocolError(f"K-line sync byte mismatch: expected 0x55, got {sync.hex()}")
    kb1 = self._read_exact(1, timeout_ms=W2_MAX)
    kb2 = self._read_exact(1, timeout_ms=W3_MAX)
    self._keybytes = (kb1[0], kb2[0])

    # W4 delay, then echo ~kb2
    time.sleep(W4 / 1000)
    self._write(bytes([kb2[0] ^ 0xFF]))

    # ECU echoes ~ecu_address back
    echo = self._read_exact(1, timeout_ms=50)
    expected = (self.ecu_address ^ 0xFF) & 0xFF
    if echo[0] != expected:
        raise ProtocolError(
            f"K-line init final handshake mismatch: expected {expected:#04x}, got {echo[0]:#04x}"
        )
```

**Test-only realism**: in production this sequence takes ~2.2 seconds of wall-clock time. Tests replace `time.sleep` with a no-op via `monkeypatch` and replace `_serial` with a `MagicMock` that scripted-returns sync/keybyte/echo bytes — so the test suite runs in milliseconds.

##### `_fast_init()` — ISO 14230-2 fast init

For ECUs that support it (mostly newer bikes that straddle the CAN transition), a 25 ms low + 25 ms high wakeup pattern at the normal baud rate, followed immediately by a `StartCommunication` (0x81) request. Simpler to implement but not universal. Logic:
```python
self._serial.baudrate = self.baud
self._serial.break_condition = True
time.sleep(FAST_INIT_TINIL / 1000)
self._serial.break_condition = False
time.sleep((FAST_INIT_TWUP - FAST_INIT_TINIL) / 1000)
# Send StartCommunication request with SID 0x81
self._send_framed(bytes([0x81]))
response = self._receive_framed()
# Expect positive response 0xC1 <keybyte1> <keybyte2>
if response[0] != 0xC1:
    raise ProtocolError(f"Fast init failed — ECU returned {response.hex()}")
self._keybytes = (response[1], response[2])
```

##### `_start_diagnostic_session()` — SID 0x10

After wakeup, send SID 0x10 with subfunction 0x81 (defaultSession). Positive response is `0x50 0x81`. This confirms the ECU is now in a diagnostic session and ready for real service requests.

#### 1.4 Framing

KWP2000 message frame (ISO 14230-2 §4.3):

```
[ FMT ][ TGT ][ SRC ][ LEN? ][ DATA... ][ CS ]
```

- **FMT** — format byte. Top 2 bits are `AddressMode`: `10` = physical + length-in-format-byte, `11` = functional. Low 6 bits are `DataLength` (1-63). If length is 0, the byte after SRC is an explicit length byte (0-255). MotoDiag always uses physical addressing with length in FMT when ≤63 bytes, and explicit length byte when longer (DTCs usually exceed 63).
- **TGT** — target address (ECU when tester sends, tester when ECU sends).
- **SRC** — source address (tester when tester sends, ECU when ECU sends).
- **LEN** — optional extra length byte (present if FMT low-6-bits == 0).
- **DATA** — first byte is SID, remaining bytes are service-specific parameters.
- **CS** — 8-bit sum of all preceding bytes mod 256.

Helper functions:
```python
def _build_frame(self, payload: bytes, functional: bool = False) -> bytes:
    if len(payload) > 255:
        raise ProtocolError(f"Payload too long for KWP2000 frame: {len(payload)} bytes")
    fmt_high = 0b11 if functional else 0b10
    if len(payload) <= 63:
        fmt = (fmt_high << 6) | len(payload)
        header = bytes([fmt, self.ecu_address, self.tester_address])
    else:
        fmt = (fmt_high << 6) | 0  # length in separate byte
        header = bytes([fmt, self.ecu_address, self.tester_address, len(payload)])
    frame = header + payload
    checksum = sum(frame) & 0xFF
    return frame + bytes([checksum])

def _parse_frame(self, raw: bytes) -> bytes:
    # Returns the payload (SID + params). Raises ProtocolError on bad checksum
    # or malformed frame.
    if len(raw) < 5:
        raise ProtocolError(f"K-line frame too short: {raw.hex()}")
    fmt = raw[0]
    length_in_fmt = fmt & 0x3F
    if length_in_fmt == 0:
        payload_len = raw[3]
        header_len = 4
    else:
        payload_len = length_in_fmt
        header_len = 3
    expected_total = header_len + payload_len + 1
    if len(raw) != expected_total:
        raise ProtocolError(
            f"K-line frame length mismatch: expected {expected_total}, got {len(raw)}"
        )
    checksum_expected = sum(raw[:-1]) & 0xFF
    checksum_actual = raw[-1]
    if checksum_expected != checksum_actual:
        raise ProtocolError(
            f"K-line checksum fail: expected {checksum_expected:#04x}, got {checksum_actual:#04x}"
        )
    return raw[header_len : header_len + payload_len]
```

#### 1.5 Half-duplex transmit + echo cancellation

The single-wire nature of K-line means every byte the tester puts on the wire is read back immediately by the tester's own UART (the RX line is tied to TX through the transceiver). The adapter must drain exactly `len(frame)` bytes of echo before waiting for the ECU response. If the echoed bytes don't match what was sent, the bus is faulty (wrong voltage, bad ground, wrong bike) — raise `ProtocolError` immediately rather than trying to parse garbage.

```python
def _transmit_and_receive(self, payload: bytes) -> bytes:
    frame = self._build_frame(payload)
    self._wait_p3_idle()          # honor P3_MIN since last response
    self._write(frame)
    self._drain_echo(frame)       # remove our own bytes from RX buffer
    return self._receive_framed() # wait for and parse ECU response

def _drain_echo(self, sent: bytes) -> None:
    deadline = time.monotonic() + (len(sent) * 10 / self.baud) + 0.1
    buf = bytearray()
    while len(buf) < len(sent) and time.monotonic() < deadline:
        chunk = self._serial.read(len(sent) - len(buf))
        if chunk:
            buf.extend(chunk)
    if bytes(buf) != sent:
        raise ProtocolError(
            f"K-line echo mismatch: sent {sent.hex()}, echoed {bytes(buf).hex()} "
            f"— check wiring, voltage, or wrong ECU address"
        )
```

Why this matters: many early K-line bugs in DIY bike-OBD projects are misdiagnosed as "my protocol is wrong" when the real issue is that the echo isn't being filtered and the tester is trying to checksum its own request bytes as if they were the ECU's response.

#### 1.6 Receiving a framed response

```python
def _receive_framed(self) -> bytes:
    deadline = time.monotonic() + (self.read_timeout)
    # 1. Read FMT byte
    fmt_bytes = self._read_exact(1, timeout_ms=P2_MAX)
    fmt = fmt_bytes[0]
    length_in_fmt = fmt & 0x3F
    # 2. Read TGT, SRC
    addrs = self._read_exact(2, timeout_ms=P1_MAX * 2)
    # 3. Read LEN if needed
    if length_in_fmt == 0:
        len_byte = self._read_exact(1, timeout_ms=P1_MAX)
        payload_len = len_byte[0]
        header = fmt_bytes + addrs + len_byte
    else:
        payload_len = length_in_fmt
        header = fmt_bytes + addrs
    # 4. Read payload + checksum
    rest = self._read_exact(payload_len + 1, timeout_ms=P1_MAX * (payload_len + 1) + 100)
    raw = bytes(header) + bytes(rest)
    payload = self._parse_frame(raw)
    # 5. Check for negative response
    if payload[0] == NEGATIVE_RESPONSE_SID:
        requested_sid = payload[1]
        nrc = payload[2]
        raise ProtocolError(
            f"K-line negative response: SID={requested_sid:#04x}, NRC={nrc:#04x}"
        )
    return payload
```

#### 1.7 Service methods (implementing `ProtocolAdapter` abstract contract)

Each maps one KWP2000 service to the abstract API. Assumed abstract contract on `ProtocolAdapter` (from Phase 134):
- `connect() -> None`
- `disconnect() -> None`
- `read_dtcs() -> list[DTC]`
- `clear_dtcs() -> None`
- `read_ecu_id() -> dict[str, str]`
- `reset_ecu() -> None`
- `is_connected() -> bool`

```python
def read_dtcs(self) -> list[DTC]:
    # SID 0x18 ReadDiagnosticTroubleCodesByStatus
    # Params: 0x00 (group: all DTCs), 0xFF (status mask: report all)
    payload = bytes([SID_READ_DTC_BY_STATUS, 0x00, 0xFF])
    response = self._transmit_and_receive(payload)
    if response[0] != SID_READ_DTC_BY_STATUS + POSITIVE_RESPONSE_OFFSET:
        raise ProtocolError(f"Unexpected DTC response SID: {response[0]:#04x}")
    num_dtcs = response[1]
    dtcs = []
    for i in range(num_dtcs):
        offset = 2 + i * 3
        high = response[offset]
        low = response[offset + 1]
        status = response[offset + 2]
        dtc_code = self._decode_kwp_dtc(high, low)  # e.g., "P0301"
        dtcs.append(DTC(code=dtc_code, status=status, source=self.PROTOCOL_NAME))
    return dtcs

def clear_dtcs(self) -> None:
    # SID 0x14 ClearDiagnosticInformation, group 0xFF00 (all)
    payload = bytes([SID_CLEAR_DIAGNOSTIC_INFO, 0xFF, 0x00])
    response = self._transmit_and_receive(payload)
    if response[0] != SID_CLEAR_DIAGNOSTIC_INFO + POSITIVE_RESPONSE_OFFSET:
        raise ProtocolError(f"Unexpected ClearDTCs response: {response.hex()}")

def read_ecu_id(self) -> dict[str, str]:
    # SID 0x1A ReadECUIdentification, identifier 0x9B (ECU manufacturing info)
    payload = bytes([SID_READ_ECU_IDENTIFICATION, 0x9B])
    response = self._transmit_and_receive(payload)
    # Parse manufacturer-specific identification block (vendor-dependent)
    return self._decode_ecu_id(response)

def reset_ecu(self) -> None:
    # SID 0x11 ECUReset, subfunction 0x01 (powerOnReset)
    payload = bytes([SID_ECU_RESET, 0x01])
    self._transmit_and_receive(payload)

def disconnect(self) -> None:
    if self._serial is not None:
        # Attempt a clean StopDiagnosticSession (SID 0x20) but don't fail disconnect if it errors
        with contextlib.suppress(Exception):
            self._transmit_and_receive(bytes([0x20]))
        self._close_serial_safe()
    self._connected = False

def is_connected(self) -> bool:
    return self._connected and self._serial is not None and self._serial.is_open
```

#### 1.8 Defensive pyserial import

```python
def _ensure_pyserial(self) -> None:
    try:
        import serial  # noqa: F401
    except ImportError as e:
        raise ProtocolError(
            "pyserial is required for K-line support. "
            "Install with: pip install 'motodiag[hardware]'"
        ) from e
```

Called at the top of `connect()` so failures happen before any state change. Import is deferred (not at module top) to keep `from motodiag.hardware.protocols.kline import KLineAdapter` importable on machines without pyserial — important for tests that don't need the real dep, and for import-time safety in the CLI.

#### 1.9 DTC decoding — `_decode_kwp_dtc`

KWP2000 returns 16-bit DTCs; the upper 2 bits select the domain letter (P/C/B/U), the next 2 bits are the decade, the remaining 12 bits are the numeric suffix encoded as BCD-ish nibbles. The standard mapping (ISO 15031-6 and SAE J2012, also used by KWP2000 on bikes):

```python
_DTC_DOMAIN = {0b00: "P", 0b01: "C", 0b10: "B", 0b11: "U"}

def _decode_kwp_dtc(high: int, low: int) -> str:
    domain_bits = (high >> 6) & 0b11
    decade = (high >> 4) & 0b11
    digit1 = high & 0x0F
    digit2 = (low >> 4) & 0x0F
    digit3 = low & 0x0F
    return f"{_DTC_DOMAIN[domain_bits]}{decade}{digit1:X}{digit2:X}{digit3:X}"
```

Example: high=0x01, low=0x11 → domain=P (0b00), decade=0, digits=1,1,1 → `P0111`.

### 2. Testing — `tests/test_phase137_kline.py`

Test strategy: mock `serial.Serial` (the pyserial class) as a `MagicMock` with scripted `read()` / `write()` / `break_condition` behavior. `time.sleep` is monkeypatched to a no-op so slow-init tests run in <1 ms. No real serial port, no hardware, no network.

Shared fixtures:
```python
@pytest.fixture
def mock_serial(monkeypatch):
    import serial
    fake = MagicMock(spec=serial.Serial)
    fake.is_open = True
    fake.baudrate = 10400
    fake.break_condition = False
    monkeypatch.setattr(serial, "Serial", lambda *a, **kw: fake)
    return fake

@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *a, **kw: None)
```

Test classes (~20-25 tests total across 5 classes):

**TestSlowBaudInit** (5 tests)
- `test_slow_init_success_10400_baud` — scripted read returns `\x55`, keybyte1=`\x8F`, keybyte2=`\xEF`, then echo `~ecu_address = 0xEE`. Assert `connect()` succeeds and `is_connected()` True.
- `test_slow_init_success_9600_baud` — same sequence at 9600 baud (Honda CBR600F4i era).
- `test_slow_init_sync_byte_mismatch` — scripted sync byte `\x00` instead of `\x55` → `ProtocolError` with message containing "sync byte mismatch".
- `test_slow_init_address_echo_mismatch` — ECU returns wrong final echo byte → `ProtocolError` with "final handshake mismatch".
- `test_slow_init_timeout_on_sync` — `_read_exact` returns empty → `ProtocolError("timeout")`.

**TestFastInit** (2 tests)
- `test_fast_init_success` — `KLineAdapter(..., init_mode="fast")`, scripted StartCommunication positive response `0xC1 0x8F 0xEF` → `connect()` succeeds.
- `test_fast_init_negative_response` — ECU returns `0x7F 0x81 0x10` (generalReject) → `ProtocolError("Fast init failed")`.

**TestFraming** (5 tests)
- `test_build_frame_short_payload` — payload=3 bytes → FMT=0x83 (0b10000011), header + checksum correct.
- `test_build_frame_long_payload` — payload=80 bytes → FMT=0x80 (length in separate byte), 5-byte header, correct checksum.
- `test_parse_frame_valid` — valid frame → returns just the payload bytes.
- `test_parse_frame_bad_checksum` — flipped last byte → `ProtocolError("checksum fail")`.
- `test_parse_frame_length_mismatch` — truncated frame → `ProtocolError("length mismatch")`.

**TestEchoCancellation** (3 tests)
- `test_echo_matches_sent` — scripted `_serial.read()` returns the same bytes that `write()` was called with → no error.
- `test_echo_mismatch_raises` — scripted echo differs from sent → `ProtocolError("echo mismatch")` with wiring hint.
- `test_echo_short_read_timeout` — `_serial.read()` returns fewer bytes than sent within deadline → `ProtocolError("echo mismatch")` (buf != sent).

**TestServiceMethods** (6 tests)
- `test_read_dtcs_parses_two_codes` — scripted response frame encodes num=2, DTCs (0x01, 0x11, status), (0x02, 0x01, status) → returns `[DTC("P0111", ...), DTC("P2001", ...)]`.
- `test_read_dtcs_empty_list` — response with num=0 → returns `[]`.
- `test_read_dtcs_negative_response` — ECU returns `0x7F 0x18 0x11` (serviceNotSupported) → `ProtocolError`.
- `test_clear_dtcs_success` — positive response `0x54` → no error.
- `test_reset_ecu_success` — positive response `0x51 0x01` → no error.
- `test_read_ecu_id_parses_block` — scripted 0x5A 0x9B + 20 bytes of identification block → returns dict with manufacturer/part keys.

**TestDefensive** (3 tests)
- `test_pyserial_missing_raises_protocol_error` — `monkeypatch.setitem(sys.modules, "serial", None)` + attempted `connect()` → `ProtocolError` with "pip install 'motodiag[hardware]'" hint.
- `test_disconnect_when_never_connected` — `KLineAdapter(...).disconnect()` no-ops cleanly (no exception).
- `test_disconnect_suppresses_stopsession_failure` — scripted `StopDiagnosticSession` raises → `disconnect()` still closes the serial port and sets `_connected = False`.

**TestConstants** (2 tests)
- `test_kwp_service_ids_are_iso_14230_3` — asserts `SID_START_DIAGNOSTIC_SESSION == 0x10`, etc. (protects against constant drift).
- `test_timing_constants_within_iso_14230_2_envelope` — asserts `P1_MAX <= 20`, `P2_MIN >= 25`, `W5_MIN >= 300`.

Total: 26 tests across 7 classes. (May land as 24 or 25 if any are collapsed during build.)

### 3. Package initialization
`src/motodiag/hardware/protocols/__init__.py` — should be created by Phase 136 (CAN adapter) or Phase 134 (base). If missing at build time (because 136 hasn't landed), create an empty `__init__.py`. If Phase 134's `ProtocolAdapter` base class isn't importable yet, the plan explicitly says Phase 137 depends on 134 — Builder should verify `from motodiag.hardware.protocols.base import ProtocolAdapter` resolves and fail fast if not.

## Key Concepts

- **ISO 14230-4 = KWP2000 over K-line.** The "-4" suffix nails the physical layer (K-line single-wire at 12V), the "-3" suffix covers the diagnostic service identifiers (SID 0x10-0x3E), the "-2" suffix covers data-link and timing (P1-P4, W1-W5), the "-1" suffix is the physical layer spec.
- **Service Identifier (SID) + 0x40 = positive response.** Universal KWP2000 convention. Request 0x18 → response 0x58. Request 0x14 → response 0x54. Request 0x1A → response 0x5A.
- **Negative response is always `0x7F <reqSID> <NRC>`.** NRC = Negative Response Code. Common NRCs: 0x11 (serviceNotSupported), 0x12 (subFunctionNotSupported), 0x22 (conditionsNotCorrect), 0x78 (requestCorrectlyReceived-ResponsePending — ECU asking for more time, should retry P2* = 5000 ms later).
- **5-baud slow init is mandatory for legacy Jp bikes.** Honda CBR600RR (PC37/PC40), Kawasaki ZX-6R (ZX636B/C), Suzuki GSX-R750 K4-K5, Yamaha R1 (5VY/4C8) all refuse fast-init. The 200 ms bit-clocking is literally specified so that ECUs built in 1998 with 8-bit MCUs could catch the wakeup reliably.
- **Echo cancellation is non-negotiable.** Single-wire K-line means TX and RX are the same physical line. Every byte written to the UART is immediately echoed back into the UART's receive buffer. Without draining the echo, the first bytes of a "response" are actually the tail of the request — checksum will always fail, and debugging is miserable. This is why dedicated K-line interfaces (MC33290, Launch X431) have built-in local-echo suppression at the transceiver level; software-only USB-serial adapters don't, so we filter in Python.
- **Timing (P1-P4, W1-W5) are enforced best-effort**. On Windows + pyserial we can't hit hard-real-time microsecond accuracy; Python's GIL + non-realtime OS scheduler means ±5 ms jitter is normal. Real bike ECUs tolerate this because automotive timing specs are generous. If a user hits repeated timing failures on a stingy ECU, the adapter should expose a `timing_profile="strict"|"relaxed"` setting later — deferred beyond this phase.
- **Frame FMT byte duality.** FMT low-6-bits encode length when 1-63, or 0 + explicit LEN byte for 0-255. This lets short requests (e.g., `SID 0x10 0x81`) fit in 5 bytes while DTC read responses (potentially 20+ DTCs × 3 bytes each) gracefully extend. Our `_build_frame` picks the right encoding automatically.
- **Physical address 0x11 vs 0x12.** Honda ECMs typically respond on 0x11; Yamaha on 0x12; Kawasaki on 0x11 (engine) or 0x33 (ABS); Suzuki varies. `ecu_address` is a constructor param so vehicle profiles can override per-make. A future phase can add a make-lookup table.
- **StartDiagnosticSession 0x81 (default) vs 0x85 (programming) vs 0x87 (adjustment).** 0x81 is read-only diagnostics; 0x85/0x87 enable dangerous operations like fuel-map writes and TPS resets. Phase 137 only issues 0x81 — write operations are out of scope until a much later phase explicitly adds tune-writing with multi-layer confirmations.
- **Module-level import of `serial` is avoided.** Machines without pyserial can still `from motodiag.hardware.protocols.kline import KLineAdapter` to pass `--help` and type-check; only `connect()` requires the real dep. Same lazy-import pattern Phase 132 used for `markdown` / `xhtml2pdf`.
- **`ProtocolError` is the single exception type raised.** Inherits from a base defined in Phase 134 (`src/motodiag/hardware/errors.py` or similar). Every failure mode — missing dep, wrong baud, wrong echo, bad checksum, timeout, negative response — lands as a `ProtocolError` with a specific diagnostic message. Callers catch one type, not fifteen.

## Verification Checklist
- [ ] `src/motodiag/hardware/protocols/kline.py` exists and declares `class KLineAdapter(ProtocolAdapter)`
- [ ] `KLineAdapter.PROTOCOL_NAME == "kline"`
- [ ] Constructor accepts `port`, `baud`, `ecu_address`, `tester_address`, `init_mode`, `read_timeout` with sensible defaults
- [ ] `init_mode` accepts `"slow"` and `"fast"`; raises `ValueError` on other values
- [ ] `connect()` dispatches to `_slow_baud_init()` or `_fast_init()` based on `init_mode`
- [ ] `_slow_baud_init()` emits exactly 200 ms per bit via `break_condition` toggling (test asserts call count via mock)
- [ ] `_slow_baud_init()` reads 3 bytes (sync + 2 keybytes) and writes inverted keybyte2
- [ ] `_slow_baud_init()` verifies ECU echoes `~ecu_address`
- [ ] `_fast_init()` sends `0x81` StartCommunication and validates `0xC1` positive response
- [ ] `_build_frame()` encodes payload ≤63 bytes as 3-byte header + payload + 1-byte checksum
- [ ] `_build_frame()` encodes payload >63 bytes as 4-byte header (with LEN byte) + payload + checksum
- [ ] `_parse_frame()` validates checksum and raises `ProtocolError` on mismatch
- [ ] `_parse_frame()` validates length and raises `ProtocolError` on truncation/overrun
- [ ] `_drain_echo()` reads back exactly the sent bytes and raises `ProtocolError` on mismatch
- [ ] `read_dtcs()` returns `list[DTC]` with codes in P/C/B/U format (e.g., `"P0111"`)
- [ ] `read_dtcs()` handles empty DTC list (num=0) without error
- [ ] `clear_dtcs()` sends SID 0x14 with group 0xFF00 and validates 0x54 positive response
- [ ] `reset_ecu()` sends SID 0x11 subfunction 0x01 and validates 0x51 positive response
- [ ] `read_ecu_id()` sends SID 0x1A identifier 0x9B and returns `dict[str, str]`
- [ ] Negative response `0x7F <sid> <nrc>` raises `ProtocolError` with SID and NRC in message
- [ ] Missing pyserial raises `ProtocolError` with `pip install 'motodiag[hardware]'` hint
- [ ] `disconnect()` is idempotent (safe to call when never connected)
- [ ] `disconnect()` suppresses StopDiagnosticSession failures and still closes the port
- [ ] All ~20-25 tests in `tests/test_phase137_kline.py` pass
- [ ] Full existing regression suite still passes (zero regressions)
- [ ] No live serial port required — all tests run with mocked `serial.Serial`
- [ ] Zero live API tokens (pure protocol code, no AI involvement)

## Risks
- **pyserial `break_condition` toggle latency on Windows.** The `pyserial` implementation on Windows uses `SetCommBreak`/`ClearCommBreak` which are kernel calls; rapid toggling at 5 baud (5 bits/sec) may actually work fine, but real-hardware slow-init has been flaky on USB-to-serial FTDI adapters for 20 years. *Mitigation*: tests use a mocked `break_condition` property so this is a runtime-only risk. Document in Phase 147 (Gate 6) that users with init failures should try the MC33290 + native serial route.
- **Timing precision on non-realtime OS.** `time.sleep(0.2)` has ±5-15 ms jitter on Windows. 5-baud init tolerates this because bit times are 200 ms wide; fast-init's 25 ms pattern is tighter and may fail on some adapters. *Mitigation*: default to `init_mode="slow"`, document the jitter, expose `init_mode="fast"` as a power-user override.
- **Echo cancellation may over-read on noisy lines.** If the bus has ringing or reflections, `_drain_echo()` may consume the first real response byte as if it were echo residue. *Mitigation*: strict byte-equality check — if echo bytes don't match sent bytes exactly, fail fast rather than silently shift the frame parser.
- **ECU address varies by make/model/year.** `ADDR_ECU_DEFAULT = 0x11` covers Honda and most Kawasaki, but Yamaha uses 0x12, some Suzukis use 0x10. *Mitigation*: constructor parameter `ecu_address=0x11` is explicit; a later phase (likely Phase 146 or the vehicle profile system) can add per-make address tables.
- **Real-hardware testing deferred.** This phase has zero real-ECU testing. Full bike-in-loop testing lands in Phase 147 (Gate 6 — Hardware integration test). *Mitigation*: mocked-serial tests cover every protocol branch exhaustively; Gate 6 will confirm wire-level correctness against a real Honda CBR600RR ECU.
- **KWP2000 extended services (security access, tuning writes) deliberately out of scope.** SID 0x27 (SecurityAccess), 0x2E (WriteDataByIdentifier), 0x31 (StartRoutineByLocalIdentifier) are not implemented. *Mitigation*: plan is to add them in a dedicated tune-writing phase with a user-confirmation safety layer.
- **Echo cancellation assumes full local echo.** If a user's adapter has hardware echo suppression (e.g., MC33290 + dedicated transceiver), our `_drain_echo()` will time out waiting for bytes that never come, then fail. *Mitigation*: add `echo_mode="auto"|"on"|"off"` constructor param in a follow-up if user reports this. Default `"on"` matches the cheapest / most common DIY adapters.
