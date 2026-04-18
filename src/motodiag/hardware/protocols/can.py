"""Phase 136 — CAN bus protocol adapter (ISO 15765-4).

This module implements :class:`CANAdapter`, a concrete
:class:`~motodiag.hardware.protocols.base.ProtocolAdapter` that speaks
ISO 15765-4 (OBD-II over CAN). Used by 2011+ Harley-Davidson Touring
models, Japanese sportbikes with OBD-II-compliant ECUs, and virtually
every post-2010 EU-market motorcycle.

Transport layer:

- Physical bus access via ``python-can`` (any back-end — SocketCAN,
  PCAN, Vector, Kvaser, slcan). Lazy-imported so the module itself can
  be imported in environments without ``python-can`` (useful for unit
  tests and for mechanics who only install the base package).

- ISO-TP (ISO 15765-2) framing for payloads that exceed CAN's 8-byte
  frame limit. Hand-rolled sender + receiver supporting Single Frame,
  First Frame + Flow Control + Consecutive Frame multi-frame sessions,
  with sequence-number wrap (0xF -> 0x0).

Addressing:

- 11-bit standard CAN IDs only. Functional request on ``0x7DF``;
  physical responses accepted from ``0x7E8``-``0x7EF``. 29-bit extended
  IDs are deferred to a future phase (some proprietary diagnostic
  buses use them; OBD-II standard services do not).

Scope:

- Read-side OBD-II: Mode 03 (stored DTCs), Mode 04 (clear DTCs),
  Mode 09 PID 02 (VIN), Mode 01 arbitrary PID, plus
  :meth:`~CANAdapter.send_command` as the escape hatch for custom
  requests (UDS Mode 22 ReadDataByIdentifier, etc.).

- Write-side active tests, bi-directional control, session
  management, and tester-present heartbeats are intentionally out of
  scope — they belong to the UDS / KWP2000 territory of Phase 137+.

NRC (Negative Response Code) handling:

- Common ISO 14229-1 NRCs are decoded to human-readable names
  (``serviceNotSupported``, ``conditionsNotCorrect``,
  ``requestOutOfRange``, etc.). Unknown NRCs fall back to
  ``unknownNRC(0xNN)``. NRC 0x78 (``requestCorrectlyReceivedResponsePending``)
  is currently treated as an error — v1.1 may extend the deadline
  instead. See Risks in the phase plan.
"""

from __future__ import annotations

import time
from types import ModuleType
from typing import Optional

from motodiag.hardware.protocols.base import ProtocolAdapter
from motodiag.hardware.protocols.exceptions import (
    ConnectionError as ProtocolConnectionError,
)
from motodiag.hardware.protocols.exceptions import (
    ProtocolError,
)
from motodiag.hardware.protocols.exceptions import (
    TimeoutError as ProtocolTimeoutError,
)

# ---------------------------------------------------------------------------
# OBD-II service IDs (SAE J1979 / ISO 15031-5)
# ---------------------------------------------------------------------------

SERVICE_SHOW_CURRENT_DATA = 0x01
SERVICE_SHOW_FREEZE_FRAME = 0x02
SERVICE_READ_DTCS = 0x03
SERVICE_CLEAR_DTCS = 0x04
SERVICE_READ_PENDING_DTCS = 0x07
SERVICE_READ_VEHICLE_INFO = 0x09  # Mode 09 — VIN is PID 0x02
SERVICE_READ_PERMANENT_DTCS = 0x0A

# Positive-response offset: ECU replies with (request_sid | 0x40)
POSITIVE_RESPONSE_OFFSET = 0x40

# Negative-response sentinel: response byte 0 == 0x7F, byte 1 = echoed SID,
# byte 2 = NRC (Negative Response Code).
NEGATIVE_RESPONSE_SID = 0x7F

# ---------------------------------------------------------------------------
# 11-bit CAN IDs (standard OBD-II)
# ---------------------------------------------------------------------------

FUNCTIONAL_REQUEST_ID = 0x7DF  # broadcast to all OBD-II-compliant ECUs
PHYSICAL_RESPONSE_RANGE: tuple[int, int] = (0x7E8, 0x7EF)

# ---------------------------------------------------------------------------
# ISO-TP (ISO 15765-2) PCI type nibbles
# ---------------------------------------------------------------------------

PCI_SINGLE_FRAME = 0x0  # SF — complete message <= 7 bytes
PCI_FIRST_FRAME = 0x1  # FF — start of a multi-frame message
PCI_CONSECUTIVE_FRAME = 0x2  # CF — continuation frame
PCI_FLOW_CONTROL = 0x3  # FC — receiver -> sender handshake

# Flow-Control flag values (first nibble of FC byte 0's low nibble)
FC_FLAG_CONTINUE_TO_SEND = 0x0  # CTS — sender may proceed
FC_FLAG_WAIT = 0x1  # WAIT — sender should re-wait for another FC
FC_FLAG_OVERFLOW = 0x2  # OVFLW — receiver buffer too small

# ---------------------------------------------------------------------------
# Bitrate + timeout defaults
# ---------------------------------------------------------------------------

SUPPORTED_BITRATES: tuple[int, ...] = (500_000, 250_000)
DEFAULT_BITRATE = 500_000

DEFAULT_REQUEST_TIMEOUT = 1.0  # per-frame receive timeout (seconds)
DEFAULT_MULTIFRAME_TIMEOUT = 5.0  # total time budget for multi-frame assembly

# ---------------------------------------------------------------------------
# NRC decoding table (ISO 14229-1 §8.7.5)
# ---------------------------------------------------------------------------

_NRC_TABLE: dict[int, str] = {
    0x10: "generalReject",
    0x11: "serviceNotSupported",
    0x12: "subFunctionNotSupported",
    0x13: "incorrectMessageLengthOrInvalidFormat",
    0x22: "conditionsNotCorrect",
    0x31: "requestOutOfRange",
    0x33: "securityAccessDenied",
    0x78: "requestCorrectlyReceivedResponsePending",
    0x7E: "subFunctionNotSupportedInActiveSession",
    0x7F: "serviceNotSupportedInActiveSession",
}


def _decode_nrc(nrc: int) -> str:
    """Return the ISO 14229-1 name for an NRC byte, or ``unknownNRC(0xNN)``."""
    if nrc in _NRC_TABLE:
        return _NRC_TABLE[nrc]
    return f"unknownNRC(0x{nrc:02X})"


# ---------------------------------------------------------------------------
# Lazy python-can loader
# ---------------------------------------------------------------------------


def _load_can() -> ModuleType:
    """Import ``can`` on demand. Raises :class:`ProtocolConnectionError`.

    Why lazy: ``python-can`` is an optional dependency. Mechanics who use
    motodiag purely for the AI diagnostic layer (no physical bike hookup)
    should not be forced to install SocketCAN drivers or PCAN SDKs just
    to ``import`` this module. Tests also rely on this — they inject a
    mocked ``can`` module via ``monkeypatch`` without shipping the real
    library.

    The hint string is matched verbatim by the Phase 136 tests, so keep
    the ``pip install 'motodiag[can]'`` wording stable.
    """
    try:
        import can  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ProtocolConnectionError(
            "python-can is not installed. Install with: "
            "pip install 'motodiag[can]'"
        ) from exc
    return can


# ---------------------------------------------------------------------------
# DTC byte-pair decoder (ISO 15031-6)
# ---------------------------------------------------------------------------

_DTC_LETTER_MAP = {0b00: "P", 0b01: "C", 0b10: "B", 0b11: "U"}


def _decode_dtc_pair(high: int, low: int) -> str:
    """Turn two ISO 15031-6 bytes into an OBD-II DTC string (e.g. ``P0133``).

    Byte layout: top 2 bits of ``high`` pick the letter (P/C/B/U); the
    next 2 bits become the leading decimal digit (0-3); the low nibble
    of ``high`` is the second digit (hex); ``low`` contributes two more
    hex digits.
    """
    letter = _DTC_LETTER_MAP[(high >> 6) & 0b11]
    first_digit = (high >> 4) & 0b11
    second_digit = high & 0x0F
    return f"{letter}{first_digit}{second_digit:X}{low:02X}"


# ---------------------------------------------------------------------------
# CANAdapter
# ---------------------------------------------------------------------------


class CANAdapter(ProtocolAdapter):
    """ISO 15765-4 (OBD-II over CAN) protocol adapter.

    Uses ``python-can`` for physical bus I/O and a hand-rolled ISO-TP
    state machine for framing. Stateless request/response — each
    high-level call is a fresh ISO-TP transaction.
    """

    def __init__(
        self,
        channel: str,
        interface: str = "socketcan",
        bitrate: int = DEFAULT_BITRATE,
        request_id: int = FUNCTIONAL_REQUEST_ID,
        response_id_range: tuple[int, int] = PHYSICAL_RESPONSE_RANGE,
        request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
        multiframe_timeout: float = DEFAULT_MULTIFRAME_TIMEOUT,
    ) -> None:
        if bitrate not in SUPPORTED_BITRATES:
            raise ValueError(
                f"Unsupported bitrate: {bitrate}. "
                f"Supported bitrates: {list(SUPPORTED_BITRATES)}"
            )
        self.channel = channel
        self.interface = interface
        self.bitrate = bitrate
        self.request_id = request_id
        self.response_id_range = response_id_range
        self.request_timeout = request_timeout
        self.multiframe_timeout = multiframe_timeout
        self._bus: Optional[object] = None
        self._is_connected: bool = False

    # ------------------------------------------------------------------
    # ProtocolAdapter contract
    # ------------------------------------------------------------------

    def connect(self, port: str = "", baud: int = 0) -> None:
        """Open the CAN bus. ``port``/``baud`` are accepted for contract
        parity with the base class but the real channel + bitrate come
        from the constructor (CAN back-ends don't use serial-port
        parameters). Idempotent — a second call is a no-op.
        """
        if self._is_connected:
            return
        can_mod = _load_can()
        try:
            # Prefer the 4.x keyword name ``interface``; older builds used
            # ``bustype`` and still accept ``interface`` via a shim. We
            # stick to the documented 4.x name.
            self._bus = can_mod.Bus(
                channel=self.channel,
                interface=self.interface,
                bitrate=self.bitrate,
            )
        except Exception as exc:  # noqa: BLE001 — wrap any backend error
            raise ProtocolConnectionError(
                f"Failed to open CAN bus on channel={self.channel!r} "
                f"interface={self.interface!r}: {exc}"
            ) from exc
        self._is_connected = True

    def disconnect(self) -> None:
        """Close the CAN bus. Idempotent — swallow shutdown errors."""
        bus = self._bus
        if bus is not None:
            try:
                bus.shutdown()
            except Exception:  # noqa: BLE001 — never raise from disconnect
                pass
        self._bus = None
        self._is_connected = False

    def send_command(self, cmd: bytes) -> bytes:
        """Raw send — ``cmd[0]`` is the service byte, rest is payload.

        Returns the response payload bytes *including* the echoed SID
        (i.e. the full positive-response body, not just the data after
        the SID). This mirrors ELM327-style behavior where callers can
        verify the echo themselves if they want strict framing checks.
        """
        if not self._is_connected or self._bus is None:
            raise ProtocolConnectionError(
                "send_command() called on a disconnected CANAdapter"
            )
        if len(cmd) == 0:
            raise ProtocolError("send_command requires at least a service byte")
        self._send_iso_tp(cmd)
        deadline = time.monotonic() + self.multiframe_timeout
        payload = self._receive_iso_tp(deadline)
        self._raise_if_negative(payload)
        return payload

    def read_dtcs(self) -> list[str]:
        """Mode 03 — read stored diagnostic trouble codes."""
        payload = self._request_and_reply(
            service=SERVICE_READ_DTCS, data=b""
        )
        # SID echo already stripped; payload starts with DTC count byte.
        if len(payload) == 0:
            return []
        count = payload[0]
        dtc_bytes = payload[1:]
        codes: list[str] = []
        for i in range(count):
            start = i * 2
            if start + 1 >= len(dtc_bytes):
                # Short payload — fewer DTCs than the count claimed.
                # Don't crash; return what we decoded.
                break
            codes.append(_decode_dtc_pair(dtc_bytes[start], dtc_bytes[start + 1]))
        return codes

    def clear_dtcs(self) -> bool:
        """Mode 04 — clear stored DTCs.

        Returns True on positive response. Returns False if the ECU
        refused with ``conditionsNotCorrect`` (0x22) — a common state
        when the engine is running or ignition is off. Other NRCs raise.
        """
        try:
            self._request_and_reply(service=SERVICE_CLEAR_DTCS, data=b"")
        except ProtocolError as exc:
            # Refuse-but-not-error for "conditions not correct" only —
            # every other error propagates.
            if "conditionsNotCorrect" in str(exc):
                return False
            raise
        return True

    def read_pid(self, pid: int) -> Optional[int]:
        """Mode 01 PID read. Returns a simple integer (0..0xFFFFFFFF).

        Multi-byte PIDs are combined big-endian. Returns ``None`` if the
        ECU replies with no data bytes (some ECUs indicate "not
        supported" by returning a shorter response than expected — this
        is distinct from a formal NRC).
        """
        if not (0 <= pid <= 0xFF):
            raise ValueError(f"Mode 01 PID must be 0x00..0xFF, got 0x{pid:X}")
        payload = self._request_and_reply(
            service=SERVICE_SHOW_CURRENT_DATA, data=bytes([pid])
        )
        # payload = [echoed PID] + data bytes
        if len(payload) < 1:
            return None
        if payload[0] != pid:
            raise ProtocolError(
                f"Mode 01 response echoed PID 0x{payload[0]:02X}, expected 0x{pid:02X}"
            )
        data = payload[1:]
        if len(data) == 0:
            return None
        value = 0
        for byte in data:
            value = (value << 8) | byte
        return value

    def read_vin(self) -> Optional[str]:
        """Mode 09 PID 02 — read the 17-char VIN.

        Returns the uppercase ASCII VIN. Raises :class:`ProtocolError`
        if the decoded VIN is not exactly 17 characters (indicates a
        malformed ECU response).
        """
        payload = self._request_and_reply(
            service=SERVICE_READ_VEHICLE_INFO, data=bytes([0x02])
        )
        # payload = [echoed PID, data-item-count, <17 VIN bytes>]
        if len(payload) < 2:
            raise ProtocolError("VIN response too short — missing PID echo")
        if payload[0] != 0x02:
            raise ProtocolError(
                f"VIN response echoed PID 0x{payload[0]:02X}, expected 0x02"
            )
        # Strip PID echo and data-item-count, then remaining bytes = VIN ASCII.
        vin_bytes = payload[2:]
        # Some ECUs prefix with the item count (1); some don't. Tolerate both
        # by stripping trailing/leading NULs and validating length.
        vin_stripped = vin_bytes.rstrip(b"\x00").lstrip(b"\x00")
        try:
            vin = vin_stripped.decode("ascii")
        except UnicodeDecodeError as exc:
            raise ProtocolError(
                f"malformed VIN — response is not ASCII: {vin_bytes!r}"
            ) from exc
        if len(vin) != 17:
            raise ProtocolError(
                f"malformed VIN — expected 17 characters, got {len(vin)}: {vin!r}"
            )
        return vin.upper()

    def get_protocol_name(self) -> str:
        """Return the stable protocol label."""
        kbps = self.bitrate // 1000
        return f"ISO 15765-4 (CAN 11/{kbps})"

    # ------------------------------------------------------------------
    # ISO-TP framing (the load-bearing core)
    # ------------------------------------------------------------------

    def _request_and_reply(self, service: int, data: bytes) -> bytes:
        """Send a request, receive + validate the positive response.

        Returns the payload *after* the SID echo, ready for the caller's
        service-specific parser.
        """
        if not self._is_connected or self._bus is None:
            raise ProtocolConnectionError(
                "Adapter must be connected before sending requests"
            )
        request = bytes([service]) + data
        self._send_iso_tp(request)
        deadline = time.monotonic() + self.multiframe_timeout
        response = self._receive_iso_tp(deadline)
        self._raise_if_negative(response)
        expected = service + POSITIVE_RESPONSE_OFFSET
        if len(response) == 0 or response[0] != expected:
            raise ProtocolError(
                f"Unexpected response SID: got 0x{response[0] if response else 0:02X}, "
                f"expected 0x{expected:02X}"
            )
        return response[1:]

    def _raise_if_negative(self, payload: bytes) -> None:
        """If ``payload`` is an ISO 14229-1 negative response, raise."""
        if len(payload) >= 3 and payload[0] == NEGATIVE_RESPONSE_SID:
            echoed_sid = payload[1]
            nrc = payload[2]
            name = _decode_nrc(nrc)
            raise ProtocolError(
                f"Negative response to service 0x{echoed_sid:02X}: "
                f"NRC=0x{nrc:02X} ({name})"
            )

    def _send_iso_tp(self, payload: bytes) -> None:
        """Serialize and send ``payload`` as one or more CAN frames.

        Single frame if ``len(payload) <= 7``; otherwise ISO-TP
        multi-frame with FF + FC handshake + CFs honoring the flow-
        control block size and separation time.
        """
        assert self._bus is not None  # guarded by callers
        can_mod = _load_can()

        if len(payload) <= 7:
            # Single Frame: byte 0 = (PCI_SF << 4) | len, then payload,
            # padded to 8 bytes with 0x00.
            frame_data = bytes([(PCI_SINGLE_FRAME << 4) | len(payload)]) + payload
            frame_data = frame_data.ljust(8, b"\x00")
            msg = can_mod.Message(
                arbitration_id=self.request_id,
                data=frame_data,
                is_extended_id=False,
            )
            self._bus.send(msg)
            return

        # Multi-frame send.
        total = len(payload)
        if total > 0xFFF:
            raise ProtocolError(
                f"ISO-TP payload too large for 12-bit length field: {total} bytes"
            )
        # First Frame: byte 0 = (PCI_FF << 4) | ((len >> 8) & 0x0F);
        # byte 1 = len & 0xFF; bytes 2..7 = first 6 payload bytes.
        ff = bytes(
            [
                (PCI_FIRST_FRAME << 4) | ((total >> 8) & 0x0F),
                total & 0xFF,
            ]
        ) + payload[:6]
        ff = ff.ljust(8, b"\x00")
        self._bus.send(
            can_mod.Message(
                arbitration_id=self.request_id, data=ff, is_extended_id=False
            )
        )
        # Wait for Flow Control.
        block_size, st_ms = self._await_flow_control()
        # Stream Consecutive Frames.
        offset = 6
        sequence = 1
        cfs_in_block = 0
        while offset < total:
            chunk = payload[offset : offset + 7]
            cf = bytes([(PCI_CONSECUTIVE_FRAME << 4) | (sequence & 0x0F)]) + chunk
            cf = cf.ljust(8, b"\x00")
            self._bus.send(
                can_mod.Message(
                    arbitration_id=self.request_id, data=cf, is_extended_id=False
                )
            )
            offset += len(chunk)
            sequence = (sequence + 1) & 0x0F
            cfs_in_block += 1
            if st_ms > 0:
                time.sleep(st_ms / 1000.0)
            if block_size != 0 and cfs_in_block >= block_size and offset < total:
                # Re-handshake for the next block.
                block_size, st_ms = self._await_flow_control()
                cfs_in_block = 0

    def _await_flow_control(self) -> tuple[int, int]:
        """Wait for an FC frame; return ``(block_size, separation_time_ms)``.

        Honors CTS and briefly re-waits on WAIT. Raises on OVFLW or any
        malformed FC. Separation time is interpreted per ISO 15765-2:
        values 0x00-0x7F are milliseconds; 0xF1-0xF9 are microseconds
        (100us-900us) — the latter is rounded up to 1ms for our use (a
        1ms sleep on a 500 kbit/s bus is still faster than the ECU can
        accept frames).
        """
        assert self._bus is not None
        deadline = time.monotonic() + self.request_timeout
        while time.monotonic() < deadline:
            msg = self._bus.recv(timeout=self.request_timeout)
            if msg is None:
                continue
            if not self._is_response_id(msg.arbitration_id):
                continue
            data = bytes(msg.data)
            if len(data) < 3:
                raise ProtocolError(
                    f"Malformed Flow Control frame (too short): {data.hex()}"
                )
            pci = (data[0] >> 4) & 0x0F
            if pci != PCI_FLOW_CONTROL:
                raise ProtocolError(
                    f"Expected Flow Control frame, got PCI=0x{pci:X}"
                )
            flag = data[0] & 0x0F
            if flag == FC_FLAG_OVERFLOW:
                raise ProtocolError(
                    "Flow Control OVFLW — receiver buffer too small"
                )
            if flag == FC_FLAG_WAIT:
                # Briefly re-wait for CTS. Don't loop forever.
                continue
            if flag != FC_FLAG_CONTINUE_TO_SEND:
                raise ProtocolError(
                    f"Flow Control unknown flag: 0x{flag:X}"
                )
            block_size = data[1]
            st_raw = data[2]
            if st_raw <= 0x7F:
                st_ms = st_raw
            elif 0xF1 <= st_raw <= 0xF9:
                # Microsecond range — round up to 1ms.
                st_ms = 1
            else:
                st_ms = 0
            return block_size, st_ms
        raise ProtocolTimeoutError(
            f"timeout waiting for Flow Control frame (>{self.request_timeout}s)"
        )

    def _receive_iso_tp(self, deadline: float) -> bytes:
        """Receive one complete ISO-TP message before ``deadline``.

        ``deadline`` is a ``time.monotonic()``-relative timestamp (not a
        delta). Returns the full assembled payload bytes (post-framing,
        no PCI bytes, no padding).
        """
        assert self._bus is not None
        can_mod = _load_can()

        # Wait for the first frame (SF or FF).
        first = self._recv_next_response_frame(deadline)
        data = bytes(first.data)
        if len(data) == 0:
            raise ProtocolError("Received empty CAN frame from response ID")
        pci = (data[0] >> 4) & 0x0F

        if pci == PCI_SINGLE_FRAME:
            length = data[0] & 0x0F
            if length > 7:
                raise ProtocolError(
                    f"Invalid Single Frame length: {length}"
                )
            return data[1 : 1 + length]

        if pci == PCI_FIRST_FRAME:
            total = ((data[0] & 0x0F) << 8) | data[1]
            if total <= 7:
                raise ProtocolError(
                    f"First Frame length {total} should have been a Single Frame"
                )
            assembled = bytearray(data[2:8])  # first 6 payload bytes
            # Send Flow Control: CTS, block_size=0 (no more FC), ST=0.
            fc = bytes([
                (PCI_FLOW_CONTROL << 4) | FC_FLAG_CONTINUE_TO_SEND,
                0x00,  # block_size = receive all remaining frames
                0x00,  # separation time = 0ms (as fast as possible)
                0, 0, 0, 0, 0,  # padding
            ])
            self._bus.send(
                can_mod.Message(
                    arbitration_id=self.request_id,
                    data=fc,
                    is_extended_id=False,
                )
            )
            expected_sn = 1
            while len(assembled) < total:
                cf = self._recv_next_response_frame(deadline)
                cf_data = bytes(cf.data)
                if len(cf_data) == 0:
                    raise ProtocolError("Received empty CAN frame during CF stream")
                cf_pci = (cf_data[0] >> 4) & 0x0F
                if cf_pci != PCI_CONSECUTIVE_FRAME:
                    raise ProtocolError(
                        f"Expected Consecutive Frame, got PCI=0x{cf_pci:X}"
                    )
                sn = cf_data[0] & 0x0F
                if sn != expected_sn:
                    raise ProtocolError(
                        f"ISO-TP sequence error: expected SN={expected_sn}, got SN={sn}"
                    )
                remaining = total - len(assembled)
                take = min(7, remaining)
                assembled.extend(cf_data[1 : 1 + take])
                expected_sn = (expected_sn + 1) & 0x0F
            return bytes(assembled)

        if pci == PCI_FLOW_CONTROL:
            # Shouldn't happen on the receive path — someone sent us an FC
            # without an outstanding multi-frame send.
            raise ProtocolError("Unexpected Flow Control frame during receive")

        raise ProtocolError(f"Unknown ISO-TP PCI type: 0x{pci:X}")

    def _recv_next_response_frame(self, deadline: float):
        """Pull the next CAN frame whose ID is in the response range.

        Frames outside the response range (other ECU chatter on the bus)
        are silently dropped. Raises :class:`ProtocolTimeoutError` if
        ``deadline`` passes before a matching frame arrives.
        """
        assert self._bus is not None
        while True:
            now = time.monotonic()
            remaining = deadline - now
            if remaining <= 0:
                raise ProtocolTimeoutError(
                    f"timeout waiting for ISO-TP response (>{self.multiframe_timeout}s)"
                )
            # Cap per-recv timeout at remaining; some back-ends treat 0 as
            # "forever", so ensure a small positive value.
            per_call = min(self.request_timeout, max(remaining, 0.001))
            msg = self._bus.recv(timeout=per_call)
            if msg is None:
                continue
            if not self._is_response_id(msg.arbitration_id):
                continue
            return msg

    def _is_response_id(self, arb_id: int) -> bool:
        """True if ``arb_id`` falls in the configured response ID range."""
        lo, hi = self.response_id_range
        return lo <= arb_id <= hi
