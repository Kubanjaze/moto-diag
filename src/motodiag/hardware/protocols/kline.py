"""K-line / KWP2000 protocol adapter (Phase 137, ISO 14230-4).

This is the second concrete :class:`ProtocolAdapter` after the Phase 136
CAN adapter. It covers the 90s/2000s Japanese sport-bike era — Honda
CBR600/900/1000RR, Kawasaki ZX-6R/ZX-10R, Suzuki GSX-R/SV650, Yamaha
YZF-R1/R6 — and many Euro bikes of the same vintage (Aprilia RSV,
Ducati 748/996/998, KTM LC4/Adventure) before they migrated to CAN.

K-line is electrically simple — a single bidirectional data line
plus ground, 12 V idle with active-low signalling — but the protocol
layer is finicky: a slow-baud wakeup handshake, strict inter-byte and
inter-message timing windows, and the transmitter reads its own
transmissions back (local echo) which must be filtered out before
treating incoming bytes as ECU responses.

Services implemented (read-only / safe):

* ``0x10`` — StartDiagnosticSession (defaultSession, subfunction ``0x81``)
* ``0x11`` — ECUReset (powerOnReset, subfunction ``0x01``)
* ``0x14`` — ClearDiagnosticInformation (group ``0xFF00`` — all)
* ``0x18`` — ReadDiagnosticTroubleCodesByStatus (group ``0x00``, mask ``0xFF``)
* ``0x1A`` — ReadECUIdentification (identifier ``0x9B``)

Write services (``0x27`` SecurityAccess, ``0x2E`` WriteDataByIdentifier,
``0x31`` StartRoutineByLocalIdentifier) are intentionally out of scope
for safety — a dedicated tune-writing phase will add them behind a
multi-layer user-confirmation gate.
"""

from __future__ import annotations

import contextlib
import time
from typing import Any, Literal, Optional

from motodiag.hardware.protocols.base import ProtocolAdapter
from motodiag.hardware.protocols.exceptions import (
    ConnectionError as ProtocolConnectionError,
)
from motodiag.hardware.protocols.exceptions import (
    ProtocolError,
    TimeoutError as ProtocolTimeoutError,
)


# ---------------------------------------------------------------------------
# KWP2000 service identifiers (ISO 14230-3)
# ---------------------------------------------------------------------------

SID_START_DIAGNOSTIC_SESSION: int = 0x10
SID_ECU_RESET: int = 0x11
SID_CLEAR_DIAGNOSTIC_INFO: int = 0x14
SID_READ_DTC_BY_STATUS: int = 0x18
SID_READ_ECU_IDENTIFICATION: int = 0x1A
SID_STOP_DIAGNOSTIC_SESSION: int = 0x20

POSITIVE_RESPONSE_OFFSET: int = 0x40   # response SID = request SID + 0x40
NEGATIVE_RESPONSE_SID: int = 0x7F      # 0x7F <reqSID> <NRC>

# KWP2000 "Start Diagnostic Session" subfunctions
DIAG_MODE_DEFAULT: int = 0x81
DIAG_MODE_ECU_PROGRAMMING: int = 0x85
DIAG_MODE_ECU_ADJUSTMENT: int = 0x87

# Default K-line physical addresses (can be overridden per-make)
ADDR_TESTER_DEFAULT: int = 0xF1   # SAE J2190 convention
ADDR_ECU_DEFAULT: int = 0x11      # ISO 14230 default ECU address

# ISO 14230-2 timing (milliseconds)
P1_MAX: int = 20    # inter-byte time in ECU response
P2_MIN: int = 25    # time between tester request end and ECU response start
P2_MAX: int = 50    # max time before we declare timeout
P3_MIN: int = 55    # time between ECU response end and next tester request
P3_MAX: int = 5000  # max idle before session is lost
P4_MIN: int = 5     # inter-byte time in tester request

W1_MAX: int = 300   # max time from tester end-of-wakeup to ECU sync byte
W2_MAX: int = 20    # max time ECU takes to send keybyte 1 after sync
W3_MAX: int = 20    # max time between ECU keybyte 1 and keybyte 2
W4: int = 25        # tester wait before inverting keybyte 2
W5_MIN: int = 300   # minimum bus-idle time before a new 5-baud init

FAST_INIT_TINIL: int = 25   # fast-init low time (ms)
FAST_INIT_TWUP: int = 50    # full wakeup pattern time for fast init (ms)

# Bit-time for 5-baud init: 1 / 5 Hz = 200 ms per bit
_SLOW_INIT_BIT_TIME_S: float = 0.2

# DTC domain letters (ISO 15031-6 / SAE J2012 mapping also used by KWP2000)
_DTC_DOMAIN: dict[int, str] = {0b00: "P", 0b01: "C", 0b10: "B", 0b11: "U"}


# ---------------------------------------------------------------------------
# Framing helpers (pure functions — no I/O, no state)
# ---------------------------------------------------------------------------


def _build_frame(
    payload: bytes,
    ecu_address: int,
    tester_address: int,
    functional: bool = False,
) -> bytes:
    """Build a KWP2000 (ISO 14230-2 §4.3) message frame.

    Frame layout::

        [FMT][TGT][SRC][LEN?][DATA...][CS]

    * **FMT** — top 2 bits are AddressMode (``0b10`` physical,
      ``0b11`` functional); low 6 bits encode payload length 1-63,
      or ``0`` when followed by an explicit LEN byte for 64-255.
    * **TGT / SRC** — target and source physical addresses.
    * **LEN** — only present when FMT low-6-bits == 0.
    * **DATA** — SID followed by service-specific parameters.
    * **CS** — 8-bit sum of all preceding bytes mod 256.
    """
    if not isinstance(payload, (bytes, bytearray)):
        raise ProtocolError(
            f"KWP2000 payload must be bytes-like, got {type(payload).__name__}"
        )
    if len(payload) == 0:
        raise ProtocolError("KWP2000 payload must contain at least one byte (the SID)")
    if len(payload) > 255:
        raise ProtocolError(
            f"KWP2000 payload too long for frame: {len(payload)} bytes (max 255)"
        )

    fmt_high = 0b11 if functional else 0b10
    if len(payload) <= 63:
        fmt = (fmt_high << 6) | len(payload)
        header = bytes([fmt, ecu_address, tester_address])
    else:
        fmt = (fmt_high << 6) | 0  # length in separate LEN byte
        header = bytes([fmt, ecu_address, tester_address, len(payload)])

    frame = header + bytes(payload)
    checksum = sum(frame) & 0xFF
    return frame + bytes([checksum])


def _parse_frame(raw: bytes) -> bytes:
    """Validate a KWP2000 frame and return the raw payload (SID + params).

    Raises :class:`ProtocolError` on length mismatch or checksum failure.
    Does **not** interpret negative-response frames — callers need the
    raw payload to construct an informative error.
    """
    raw = bytes(raw)
    # Minimum frame: FMT + TGT + SRC + 1 payload byte + CS = 5 bytes
    if len(raw) < 5:
        raise ProtocolError(f"K-line frame too short: {raw.hex()}")

    fmt = raw[0]
    length_in_fmt = fmt & 0x3F
    if length_in_fmt == 0:
        if len(raw) < 5:  # pragma: no cover - already guarded above
            raise ProtocolError(f"K-line frame too short for LEN byte: {raw.hex()}")
        payload_len = raw[3]
        header_len = 4
    else:
        payload_len = length_in_fmt
        header_len = 3

    expected_total = header_len + payload_len + 1  # +1 for checksum
    if len(raw) != expected_total:
        raise ProtocolError(
            f"K-line frame length mismatch: expected {expected_total} bytes, "
            f"got {len(raw)} (raw={raw.hex()})"
        )

    checksum_expected = sum(raw[:-1]) & 0xFF
    checksum_actual = raw[-1]
    if checksum_expected != checksum_actual:
        raise ProtocolError(
            f"K-line checksum fail: expected {checksum_expected:#04x}, "
            f"got {checksum_actual:#04x}"
        )

    return raw[header_len : header_len + payload_len]


def _decode_kwp_dtc(high: int, low: int) -> str:
    """Decode a 16-bit KWP2000 DTC to its P/C/B/U letter code.

    Example: ``high=0x01, low=0x11`` → domain ``P``, decade ``0``,
    digits ``1,1,1`` → ``"P0111"``.

    * Top 2 bits of ``high`` → domain (``P/C/B/U``).
    * Next 2 bits of ``high`` → decade digit (0-3).
    * Remaining 4 bits of ``high`` → first hex digit.
    * Upper nibble of ``low`` → second hex digit.
    * Lower nibble of ``low`` → third hex digit.
    """
    high &= 0xFF
    low &= 0xFF
    domain_bits = (high >> 6) & 0b11
    decade = (high >> 4) & 0b11
    digit1 = high & 0x0F
    digit2 = (low >> 4) & 0x0F
    digit3 = low & 0x0F
    return f"{_DTC_DOMAIN[domain_bits]}{decade}{digit1:X}{digit2:X}{digit3:X}"


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class KLineAdapter(ProtocolAdapter):
    """KWP2000 over K-line (ISO 14230-4) adapter.

    Works with a USB-to-serial K-line interface (typically an FTDI
    FT232RL or CH340 wired to a 12 V-tolerant transceiver — MC33290,
    or a bespoke bike-ECU cable). The UART drives the K-line at either
    10400 or 9600 baud once the wakeup handshake completes.

    Instances are constructed without opening the port — :meth:`connect`
    is what actually opens pyserial. This lets a :class:`KLineAdapter`
    be imported and introspected on machines without ``pyserial``
    installed.

    Parameters
    ----------
    port:
        Serial device path (``"COM3"``, ``"/dev/ttyUSB0"``). Stored for
        :meth:`connect`; the base-class ``connect(port, baud)``
        signature is still honored and overrides this default when
        callers pass explicit values.
    baud:
        Target UART baud after the handshake. Canonical KWP2000 is
        10400; older Honda/Suzuki ECUs run 9600.
    ecu_address:
        Physical address of the ECU (0x11 Honda/Kawasaki, 0x12 Yamaha,
        varies for Suzuki).
    tester_address:
        Physical address of the tester (``0xF1`` by SAE J2190
        convention).
    init_mode:
        ``"slow"`` (default) uses the 5-baud address-byte init required
        by legacy Jp bikes. ``"fast"`` uses the ISO 14230-2 25 ms
        wakeup pattern accepted by later ECUs.
    read_timeout:
        Per-read wall-clock timeout in seconds — upper bound only;
        KWP2000's P1/P2 windows are enforced in code.
    """

    PROTOCOL_NAME: str = "kline"

    def __init__(
        self,
        port: str = "",
        baud: int = 10400,
        ecu_address: int = ADDR_ECU_DEFAULT,
        tester_address: int = ADDR_TESTER_DEFAULT,
        init_mode: Literal["slow", "fast"] = "slow",
        read_timeout: float = 1.0,
    ) -> None:
        if init_mode not in ("slow", "fast"):
            raise ValueError(
                f"init_mode must be 'slow' or 'fast', got {init_mode!r}"
            )
        if baud not in (9600, 10400):
            # Accept but warn — some bikes run 4800 or 15625
            # (very rare). Don't block: let pyserial reject invalid
            # values at open time.
            pass
        if not (0 <= ecu_address <= 0xFF):
            raise ValueError(
                f"ecu_address must fit in one byte, got {ecu_address:#x}"
            )
        if not (0 <= tester_address <= 0xFF):
            raise ValueError(
                f"tester_address must fit in one byte, got {tester_address:#x}"
            )
        if read_timeout <= 0:
            raise ValueError(
                f"read_timeout must be positive, got {read_timeout}"
            )

        self.port: str = port
        self.baud: int = baud
        self.ecu_address: int = ecu_address
        self.tester_address: int = tester_address
        self.init_mode: Literal["slow", "fast"] = init_mode
        self.read_timeout: float = read_timeout

        self._serial: Optional[Any] = None  # pyserial.Serial once connected
        self._keybytes: Optional[tuple[int, int]] = None
        self._last_response_end: float = 0.0
        self._is_connected: bool = False

    # ------------------------------------------------------------------
    # Public ProtocolAdapter surface
    # ------------------------------------------------------------------

    def connect(self, port: str = "", baud: int = 0) -> None:
        """Open the serial port and perform the K-line wakeup handshake.

        The base-class signature is ``connect(port, baud)``. If callers
        pass values here they override the constructor defaults. If they
        pass blanks/zeros the adapter falls back to what was configured
        at construction time.

        Idempotent: already-connected adapters short-circuit without
        reopening.
        """
        if self._is_connected:
            return

        if port:
            self.port = port
        if baud:
            self.baud = baud
        if not self.port:
            raise ProtocolConnectionError(
                "K-line connect requires a serial port "
                "(e.g. 'COM3' or '/dev/ttyUSB0')"
            )

        self._ensure_pyserial()
        self._open_serial()
        try:
            if self.init_mode == "slow":
                self._slow_baud_init()
            else:
                self._fast_init()
            self._start_diagnostic_session()
            self._is_connected = True
        except Exception:
            # Failed handshake — tear the port back down so the caller
            # never sees a half-open adapter.
            self._close_serial_safe()
            raise

    def disconnect(self) -> None:
        """Close the transport. Never raises; idempotent."""
        if self._serial is not None and self._is_connected:
            # Best-effort StopDiagnosticSession (0x20). Swallow errors —
            # the session is going away regardless.
            with contextlib.suppress(Exception):
                self._transmit_and_receive(bytes([SID_STOP_DIAGNOSTIC_SESSION]))
        self._close_serial_safe()
        self._is_connected = False

    def send_command(self, cmd: bytes) -> bytes:
        """Send a raw KWP2000 payload (SID + params) and return the response payload.

        Protocol framing (FMT/TGT/SRC/LEN/CS) and echo are handled
        internally — callers pass only the service-layer bytes.
        """
        if not self._is_connected or self._serial is None:
            raise ProtocolConnectionError(
                "K-line send_command called on disconnected adapter"
            )
        if not isinstance(cmd, (bytes, bytearray)):
            raise ProtocolError(
                f"send_command requires bytes, got {type(cmd).__name__}"
            )
        if len(cmd) == 0:
            raise ProtocolError("send_command requires a non-empty payload")
        return self._transmit_and_receive(bytes(cmd))

    def read_dtcs(self) -> list[str]:
        """Execute SID 0x18 ReadDTCsByStatus and return codes in P0111 format.

        Returns an empty list if the ECU reports no stored faults.
        Raises :class:`ProtocolError` on a negative response or
        malformed payload.
        """
        payload = bytes([SID_READ_DTC_BY_STATUS, 0x00, 0xFF])
        response = self._transmit_and_receive(payload)
        expected_sid = SID_READ_DTC_BY_STATUS + POSITIVE_RESPONSE_OFFSET
        if not response or response[0] != expected_sid:
            raise ProtocolError(
                f"Unexpected ReadDTCs response SID: got {response[:1].hex()}, "
                f"expected {expected_sid:#04x}"
            )
        if len(response) < 2:
            raise ProtocolError(
                f"ReadDTCs response too short — no DTC count byte: {response.hex()}"
            )
        num_dtcs = response[1]
        expected_len = 2 + num_dtcs * 3
        if len(response) < expected_len:
            raise ProtocolError(
                f"ReadDTCs response truncated: expected {expected_len} bytes "
                f"for {num_dtcs} DTCs, got {len(response)} "
                f"(raw={response.hex()})"
            )
        dtcs: list[str] = []
        for i in range(num_dtcs):
            offset = 2 + i * 3
            high = response[offset]
            low = response[offset + 1]
            # response[offset + 2] is the status byte — currently
            # discarded because ProtocolAdapter.read_dtcs returns plain
            # strings. A richer higher-level wrapper can re-issue the
            # request and keep status if needed.
            dtcs.append(_decode_kwp_dtc(high, low))
        return dtcs

    def clear_dtcs(self) -> bool:
        """Execute SID 0x14 ClearDiagnosticInformation (group 0xFF00 — all).

        Returns ``True`` on a positive ``0x54`` response, ``False`` if
        the ECU returned anything else that wasn't a negative-response
        error (for example, some ECUs silently NACK when the ignition
        is off).
        """
        payload = bytes([SID_CLEAR_DIAGNOSTIC_INFO, 0xFF, 0x00])
        response = self._transmit_and_receive(payload)
        expected_sid = SID_CLEAR_DIAGNOSTIC_INFO + POSITIVE_RESPONSE_OFFSET
        if not response:
            return False
        return response[0] == expected_sid

    def read_pid(self, pid: int) -> Optional[int]:
        """K-line / KWP2000 does not define Mode 01 PIDs.

        ISO 14230 uses ReadDataByLocalIdentifier (SID 0x21) or
        ReadDataByCommonIdentifier (SID 0x22) instead of Mode 01, and
        the identifier space is vehicle-specific — there is no safe
        default PID to read without a vehicle profile. Returning
        ``None`` keeps the :class:`ProtocolAdapter` contract (the docs
        allow ``None`` for "protocol could support PID but this ECU
        does not") without raising, so the CLI can still enumerate
        adapters without branching on protocol class.
        """
        # Accept any valid PID range to satisfy the abstract contract;
        # KWP2000 simply has no universal mapping.
        if not isinstance(pid, int):
            raise ProtocolError(f"pid must be int, got {type(pid).__name__}")
        return None

    def read_vin(self) -> Optional[str]:
        """Read the ECU-identification block via SID 0x1A 0x90 (VIN).

        Returns ``None`` if the ECU does not expose a VIN identifier
        (pre-2008 K-line rarely does). Never raises
        :class:`UnsupportedCommandError` — the protocol *could* carry
        the field; whether the specific ECU implements it is what the
        ``None`` return signals.
        """
        if not self._is_connected:
            return None
        payload = bytes([SID_READ_ECU_IDENTIFICATION, 0x90])  # 0x90 = VIN
        try:
            response = self._transmit_and_receive(payload)
        except ProtocolError:
            return None
        expected_sid = SID_READ_ECU_IDENTIFICATION + POSITIVE_RESPONSE_OFFSET
        if not response or response[0] != expected_sid:
            return None
        # Response layout: [0x5A][0x90][VIN bytes...]. 17 ASCII chars
        # when present.
        vin_bytes = response[2:]
        if not vin_bytes:
            return None
        try:
            vin = vin_bytes.decode("ascii", errors="replace").strip()
        except Exception:
            return None
        if not vin:
            return None
        return vin.upper()

    def get_protocol_name(self) -> str:
        """Return a stable, human-readable identifier."""
        return "ISO 14230 KWP2000"

    # ------------------------------------------------------------------
    # Higher-level helpers (not part of the abstract contract, but
    # useful enough to expose for the CLI)
    # ------------------------------------------------------------------

    def read_ecu_id(self) -> dict[str, str]:
        """Execute SID 0x1A ReadECUIdentification (identifier 0x9B).

        Identifier 0x9B is KWP2000's ECU-manufacturing-info block.
        The exact byte layout is vendor-specific, so this method
        returns a dict of parsed fields on a best-effort basis —
        callers that need the raw block should call
        :meth:`send_command` with ``bytes([0x1A, 0x9B])`` instead.
        """
        payload = bytes([SID_READ_ECU_IDENTIFICATION, 0x9B])
        response = self._transmit_and_receive(payload)
        expected_sid = SID_READ_ECU_IDENTIFICATION + POSITIVE_RESPONSE_OFFSET
        if not response or response[0] != expected_sid:
            raise ProtocolError(
                f"Unexpected ReadECUIdentification response SID: "
                f"got {response[:1].hex()}, expected {expected_sid:#04x}"
            )
        if len(response) < 2:
            raise ProtocolError(
                f"ReadECUIdentification response missing identifier byte: "
                f"{response.hex()}"
            )
        identifier = response[1]
        block = response[2:]
        # Best-effort parse — vendor-specific layouts are parsed at a
        # higher level (vehicle profile). Return raw hex + ASCII so the
        # caller always gets something human-readable.
        return {
            "identifier": f"{identifier:#04x}",
            "raw_hex": block.hex(),
            "ascii": block.decode("ascii", errors="replace").rstrip("\x00").strip(),
        }

    def reset_ecu(self) -> None:
        """Execute SID 0x11 ECUReset (powerOnReset, subfunction 0x01)."""
        payload = bytes([SID_ECU_RESET, 0x01])
        response = self._transmit_and_receive(payload)
        expected_sid = SID_ECU_RESET + POSITIVE_RESPONSE_OFFSET
        if not response or response[0] != expected_sid:
            raise ProtocolError(
                f"Unexpected ECUReset response SID: got {response[:1].hex()}, "
                f"expected {expected_sid:#04x}"
            )

    @property
    def keybytes(self) -> Optional[tuple[int, int]]:
        """Return the two keybytes negotiated at wakeup, if any."""
        return self._keybytes

    # ------------------------------------------------------------------
    # Lazy pyserial import
    # ------------------------------------------------------------------

    def _ensure_pyserial(self) -> None:
        """Import ``pyserial`` on demand with a friendly error on miss."""
        try:
            import serial  # noqa: F401
        except ImportError as exc:
            raise ProtocolError(
                "pyserial is required for K-line support. "
                "Install with: pip install 'motodiag[hardware]'"
            ) from exc

    def _open_serial(self) -> None:
        """Open the serial port via pyserial, bound to the target baud.

        We open at the target UART baud (10400/9600) even though the
        slow-baud init will temporarily drop to 5 baud via
        ``break_condition`` toggling — pyserial on Windows rejects a
        literal 5 baud on most USB-serial chips, so we toggle the
        break line manually at the 200 ms/bit cadence instead.
        """
        import serial

        # 8-N-1, no flow control is the KWP2000 framing. read_timeout
        # is applied per-read in ``_read_exact`` using
        # ``time.monotonic``; the pyserial-level timeout is a safety
        # ceiling in case our manual loop misbehaves.
        self._serial = serial.Serial(
            port=self.port,
            baudrate=self.baud,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=self.read_timeout,
            write_timeout=self.read_timeout,
        )

    def _close_serial_safe(self) -> None:
        """Close the serial port, swallowing any error."""
        if self._serial is None:
            return
        with contextlib.suppress(Exception):
            if getattr(self._serial, "is_open", False):
                self._serial.close()
        self._serial = None

    # ------------------------------------------------------------------
    # Wakeup handshakes
    # ------------------------------------------------------------------

    def _slow_baud_init(self) -> None:
        """5-baud address-byte init (ISO 14230-2 §4.2.1).

        Clocks out the ECU target address LSB-first at 5 bits per
        second using ``break_condition`` as the signalling line. The
        ECU answers at the real baud rate with a ``0x55`` sync byte,
        two keybytes, then expects the tester to echo ``~keybyte2``;
        finally the ECU echoes ``~ecu_address`` to complete the
        handshake.
        """
        assert self._serial is not None

        # 1. Drop to 5 baud (doesn't matter that the USB-serial chip
        #    may not honor it — the break toggling is what clocks the
        #    line). Wrapped in try/except because some mock/real
        #    serial impls flat-out reject 5.
        with contextlib.suppress(Exception):
            self._serial.baudrate = 5

        # 2. Start bit — drive line low (break) for 200 ms.
        self._serial.break_condition = True
        time.sleep(_SLOW_INIT_BIT_TIME_S)

        # 3. Eight data bits, LSB-first. `break_condition = True` means
        #    the line is low (logical 0); False means idle/mark
        #    (logical 1).
        for i in range(8):
            bit = (self.ecu_address >> i) & 1
            self._serial.break_condition = (bit == 0)
            time.sleep(_SLOW_INIT_BIT_TIME_S)

        # 4. Stop bit — release break (line high) for 200 ms.
        self._serial.break_condition = False
        time.sleep(_SLOW_INIT_BIT_TIME_S)

        # 5. Switch to the real baud before reading the ECU reply.
        self._serial.baudrate = self.baud

        # 6. Read 0x55 sync byte within W1_MAX.
        sync = self._read_exact(1, timeout_ms=W1_MAX)
        if sync != b"\x55":
            raise ProtocolError(
                f"K-line sync byte mismatch: expected 0x55, "
                f"got {sync.hex()} — check baud and wiring"
            )

        # 7. Read keybyte1 within W2_MAX, keybyte2 within W3_MAX.
        kb1 = self._read_exact(1, timeout_ms=W2_MAX + 50)
        kb2 = self._read_exact(1, timeout_ms=W3_MAX + 50)
        self._keybytes = (kb1[0], kb2[0])

        # 8. Wait W4, then echo ~keybyte2.
        time.sleep(W4 / 1000.0)
        inverted_kb2 = bytes([(kb2[0] ^ 0xFF) & 0xFF])
        self._write(inverted_kb2)
        # The K-line echoes our own write back — drain it.
        with contextlib.suppress(ProtocolError):
            self._drain_echo(inverted_kb2)

        # 9. ECU echoes ~ecu_address back — W4 window.
        echo = self._read_exact(1, timeout_ms=W4 + 100)
        expected = (self.ecu_address ^ 0xFF) & 0xFF
        if echo[0] != expected:
            raise ProtocolError(
                f"K-line init final handshake mismatch: "
                f"expected {expected:#04x}, got {echo[0]:#04x} — "
                f"wrong ECU address or bad bus"
            )

    def _fast_init(self) -> None:
        """ISO 14230-2 fast init.

        25 ms low + 25 ms high at the normal baud, followed immediately
        by a StartCommunication (SID 0x81) request. Simpler to
        implement but not universal; only later ECUs accept it.
        """
        assert self._serial is not None
        self._serial.baudrate = self.baud

        # Wakeup pattern
        self._serial.break_condition = True
        time.sleep(FAST_INIT_TINIL / 1000.0)
        self._serial.break_condition = False
        time.sleep(max(FAST_INIT_TWUP - FAST_INIT_TINIL, 0) / 1000.0)

        # StartCommunication (SID 0x81) — NOT framed the same as
        # normal KWP2000 messages; we send the raw SID in a minimal
        # KWP2000 frame so the ECU can respond with 0xC1 keybyte1
        # keybyte2 (also raw, not framed).
        payload = bytes([0x81])
        frame = _build_frame(
            payload=payload,
            ecu_address=self.ecu_address,
            tester_address=self.tester_address,
        )
        self._write(frame)
        with contextlib.suppress(ProtocolError):
            self._drain_echo(frame)

        # Read the StartCommunication response.
        try:
            response = self._receive_framed()
        except ProtocolError as exc:
            raise ProtocolError(f"Fast init failed — {exc}") from exc

        if not response or response[0] != 0xC1:
            raise ProtocolError(
                f"Fast init failed — ECU returned {response.hex()}, "
                f"expected leading 0xC1"
            )
        if len(response) >= 3:
            self._keybytes = (response[1], response[2])

    def _start_diagnostic_session(self) -> None:
        """Send SID 0x10 with subfunction 0x81 (defaultSession)."""
        payload = bytes([SID_START_DIAGNOSTIC_SESSION, DIAG_MODE_DEFAULT])
        response = self._transmit_and_receive(payload)
        expected_sid = SID_START_DIAGNOSTIC_SESSION + POSITIVE_RESPONSE_OFFSET
        if not response or response[0] != expected_sid:
            raise ProtocolError(
                f"StartDiagnosticSession failed: got {response.hex()}, "
                f"expected leading {expected_sid:#04x}"
            )

    # ------------------------------------------------------------------
    # Transmit / receive + echo handling
    # ------------------------------------------------------------------

    def _transmit_and_receive(self, payload: bytes) -> bytes:
        """Frame a payload, transmit it, drain local echo, parse reply."""
        assert self._serial is not None
        frame = _build_frame(
            payload=payload,
            ecu_address=self.ecu_address,
            tester_address=self.tester_address,
        )
        self._wait_p3_idle()
        self._write(frame)
        self._drain_echo(frame)
        response = self._receive_framed()
        self._last_response_end = time.monotonic()
        return response

    def _write(self, data: bytes) -> None:
        """Write bytes to the serial port, fail-fast on short write."""
        assert self._serial is not None
        n = self._serial.write(data)
        if n is not None and n != len(data):
            raise ProtocolError(
                f"K-line short write: wrote {n} of {len(data)} bytes"
            )

    def _drain_echo(self, sent: bytes) -> None:
        """Consume exactly ``len(sent)`` bytes of local echo from RX.

        K-line TX and RX are the same wire, so every byte we write
        comes back to us. We must drain these bytes before they poison
        the next response parse. Mismatched echo means the bus is
        misbehaving (wrong voltage, bad ground, wrong ECU address);
        fail fast with a wiring hint.
        """
        assert self._serial is not None
        # Deadline: generous enough to cover the full echo plus 100 ms
        # slack on a non-realtime OS.
        byte_time_s = 10.0 / max(self.baud, 1)  # 10 bits per UART byte
        deadline = time.monotonic() + len(sent) * byte_time_s + 0.2

        buf = bytearray()
        while len(buf) < len(sent) and time.monotonic() < deadline:
            remaining = len(sent) - len(buf)
            chunk = self._serial.read(remaining) or b""
            if chunk:
                buf.extend(chunk)
            else:
                # No bytes available right now; yield briefly.
                time.sleep(0.001)

        if bytes(buf) != sent:
            raise ProtocolError(
                f"K-line echo mismatch: sent {sent.hex()}, "
                f"echoed {bytes(buf).hex()} — check wiring, voltage, "
                f"or wrong ECU address"
            )

    def _receive_framed(self) -> bytes:
        """Read one KWP2000 frame from RX and return its payload."""
        assert self._serial is not None

        # 1. FMT byte within P2_MAX ms after the request.
        fmt_bytes = self._read_exact(1, timeout_ms=max(P2_MAX, 200))
        fmt = fmt_bytes[0]
        length_in_fmt = fmt & 0x3F

        # 2. TGT + SRC
        addrs = self._read_exact(2, timeout_ms=P1_MAX * 2 + 50)

        # 3. Optional LEN byte.
        if length_in_fmt == 0:
            len_byte = self._read_exact(1, timeout_ms=P1_MAX + 50)
            payload_len = len_byte[0]
            header = fmt_bytes + addrs + len_byte
        else:
            payload_len = length_in_fmt
            header = fmt_bytes + addrs

        if payload_len == 0:
            raise ProtocolError(
                f"K-line frame has zero-length payload: header={header.hex()}"
            )

        # 4. Payload + checksum
        rest = self._read_exact(
            payload_len + 1,
            timeout_ms=P1_MAX * (payload_len + 1) + 100,
        )
        raw = bytes(header) + bytes(rest)
        payload = _parse_frame(raw)

        # 5. Negative response?
        if payload[0] == NEGATIVE_RESPONSE_SID:
            if len(payload) >= 3:
                requested_sid = payload[1]
                nrc = payload[2]
                raise ProtocolError(
                    f"K-line negative response: SID={requested_sid:#04x}, "
                    f"NRC={nrc:#04x}"
                )
            raise ProtocolError(
                f"K-line negative response (malformed): {payload.hex()}"
            )

        return payload

    def _read_exact(self, n: int, timeout_ms: int) -> bytes:
        """Read exactly ``n`` bytes or raise :class:`ProtocolTimeoutError`."""
        assert self._serial is not None
        deadline = time.monotonic() + (timeout_ms / 1000.0)
        buf = bytearray()
        while len(buf) < n and time.monotonic() < deadline:
            chunk = self._serial.read(n - len(buf)) or b""
            if chunk:
                buf.extend(chunk)
            else:
                time.sleep(0.001)
        if len(buf) < n:
            raise ProtocolTimeoutError(
                f"K-line read timeout: expected {n} bytes in {timeout_ms} ms, "
                f"got {len(buf)} ({bytes(buf).hex()!r})"
            )
        return bytes(buf)

    def _wait_p3_idle(self) -> None:
        """Honor P3_MIN since the last response end."""
        if self._last_response_end == 0.0:
            return
        elapsed_ms = (time.monotonic() - self._last_response_end) * 1000.0
        wait_ms = P3_MIN - elapsed_ms
        if wait_ms > 0:
            time.sleep(wait_ms / 1000.0)


__all__ = [
    "KLineAdapter",
    "SID_START_DIAGNOSTIC_SESSION",
    "SID_ECU_RESET",
    "SID_CLEAR_DIAGNOSTIC_INFO",
    "SID_READ_DTC_BY_STATUS",
    "SID_READ_ECU_IDENTIFICATION",
    "SID_STOP_DIAGNOSTIC_SESSION",
    "POSITIVE_RESPONSE_OFFSET",
    "NEGATIVE_RESPONSE_SID",
    "DIAG_MODE_DEFAULT",
    "DIAG_MODE_ECU_PROGRAMMING",
    "DIAG_MODE_ECU_ADJUSTMENT",
    "ADDR_TESTER_DEFAULT",
    "ADDR_ECU_DEFAULT",
    "P1_MAX",
    "P2_MIN",
    "P2_MAX",
    "P3_MIN",
    "P3_MAX",
    "P4_MIN",
    "W1_MAX",
    "W2_MAX",
    "W3_MAX",
    "W4",
    "W5_MIN",
    "FAST_INIT_TINIL",
    "FAST_INIT_TWUP",
]
