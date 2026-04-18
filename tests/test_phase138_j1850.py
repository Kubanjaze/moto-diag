"""Phase 138 — J1850 VPW protocol adapter tests.

Six test classes, ~22 tests, zero hardware, zero pyserial dependency
(``MockSerial`` is injected through the ``serial_factory`` constructor
kwarg so ``_ensure_pyserial`` is never called).

Test classes
------------

- :class:`TestMockSerial` (3) — sanity-check the test fixture itself.
- :class:`TestJ1850AdapterConnect` (4) — init / handshake / disconnect.
- :class:`TestJ1850AdapterReadDTC` (5) — multi-ECM polling and merge.
- :class:`TestJ1850DtcParsing` (4) — lenient parser in isolation.
- :class:`TestJ1850BridgeVariants` (3) — per-bridge command byte tables.
- :class:`TestJ1850ClearAndInfo` (3) — clear_dtcs + adapter_info.

The ``MockSerial`` fixture is a deliberately small stand-in for
``pyserial.Serial``: it accepts a ``responses`` dict mapping written
byte sequences (stripped of trailing ``\\r``) to response byte strings,
records every write to ``sent_frames``, and returns scripted bytes on
each ``read()`` call.
"""

from __future__ import annotations

import pytest

from motodiag.hardware.protocols.exceptions import (
    ConnectionError as ProtocolConnectionError,
)
from motodiag.hardware.protocols.exceptions import (
    TimeoutError as ProtocolTimeoutError,
)
from motodiag.hardware.protocols.exceptions import UnsupportedCommandError
from motodiag.hardware.protocols.j1850 import (
    DEFAULT_READ_TIMEOUT_S,
    J1850_VPW_BAUD,
    MODULE_ADDRESS,
    PROTOCOL_NAME,
    SUPPORTED_BRIDGES,
    J1850Adapter,
    J1850ClearError,
    J1850ConnectionError,
    _BRIDGE_COMMANDS,
    _parse_j1850_response,
)


# ---------------------------------------------------------------------------
# MockSerial test helper
# ---------------------------------------------------------------------------


class MockSerial:
    """In-memory stand-in for ``pyserial.Serial``.

    Scripts per-command responses via the ``responses`` dict, records
    every ``write()`` call on ``sent_frames`` for post-hoc assertions,
    and returns queued bytes on each ``read()`` call.

    The ``responses`` dict maps raw command bytes (exactly as the
    adapter writes them, trailing ``\\r`` included) to the bytes the
    mock will emit on subsequent reads. Unknown commands return
    ``b""`` on the first read (simulating pyserial's timeout-returns-
    empty-bytes behavior).

    The adapter's exchange loop reads until it sees the ``prompt``
    byte, so every scripted response must end in the bridge's prompt
    byte (``b">"`` for every bridge in :data:`_BRIDGE_COMMANDS`).
    """

    def __init__(
        self,
        port: str,
        baudrate: int,
        bytesize: int = 8,
        parity: str = "N",
        stopbits: int = 1,
        timeout: float = 2.5,
        responses: dict | None = None,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.sent_frames: list[bytes] = []
        self.closed: bool = False

        # Responses keyed by the exact bytes written.
        self._responses: dict[bytes, bytes] = dict(responses or {})
        # Pending read buffer — filled on write, drained on read.
        self._read_buffer: bytearray = bytearray()
        # Next-response queue for fallback when exact match misses.
        self._next_response: bytes = b""

    # -- write / read wiring expected by the adapter -----------------------

    def write(self, data: bytes) -> int:
        self.sent_frames.append(bytes(data))
        if data in self._responses:
            self._read_buffer.extend(self._responses[data])
        else:
            self._read_buffer.extend(self._next_response)
            self._next_response = b""
        return len(data)

    def read(self, size: int = 1) -> bytes:
        if not self._read_buffer:
            return b""
        chunk = bytes(self._read_buffer[:size])
        del self._read_buffer[:size]
        return chunk

    def close(self) -> None:
        self.closed = True

    # -- test-side helpers -------------------------------------------------

    def script_next(self, response: bytes) -> None:
        """Queue a response for whichever write comes next."""
        self._next_response = response

    def script(self, cmd: bytes, response: bytes) -> None:
        """Map a command to a response for the remainder of the test."""
        self._responses[cmd] = response


def _factory_returning(mock: MockSerial):
    """Return a ``serial_factory`` callable that always yields ``mock``."""

    def _factory(**_kwargs):
        # Record the kwargs pyserial would have received so tests can
        # assert on port/baud/timeout if they care.
        mock.init_kwargs = _kwargs  # type: ignore[attr-defined]
        return mock

    return _factory


# ---------------------------------------------------------------------------
# TestMockSerial — sanity-check the fixture itself
# ---------------------------------------------------------------------------


class TestMockSerial:
    def test_mock_serial_write_records_bytes(self):
        mock = MockSerial(port="COM_TEST", baudrate=10400)
        mock.write(b"hello\r")
        mock.write(b"world\r")
        assert mock.sent_frames == [b"hello\r", b"world\r"]

    def test_mock_serial_read_returns_scripted_response(self):
        mock = MockSerial(
            port="COM_TEST",
            baudrate=10400,
            responses={b"PING\r": b"PONG>"},
        )
        mock.write(b"PING\r")
        # Read in chunks >= payload length to fully drain in one call.
        payload = mock.read(128)
        assert payload == b"PONG>"

    def test_mock_serial_timeout_returns_empty(self):
        mock = MockSerial(port="COM_TEST", baudrate=10400)
        # No scripted response + no pending buffer → empty bytes.
        assert mock.read(128) == b""


# ---------------------------------------------------------------------------
# TestJ1850AdapterConnect — handshake + lifecycle
# ---------------------------------------------------------------------------


class TestJ1850AdapterConnect:
    def test_connect_sends_handshake_and_set_protocol(self):
        bridge = "daytona"
        cmds = _BRIDGE_COMMANDS[bridge]
        mock = MockSerial(
            port="COM_TEST",
            baudrate=J1850_VPW_BAUD,
            responses={
                cmds["handshake"]: b"DAYTONA-TWIN-TEC>",
                cmds["set_protocol_j1850_vpw"]: b"OK>",
            },
        )
        adapter = J1850Adapter(
            port="COM_TEST",
            bridge=bridge,
            serial_factory=_factory_returning(mock),
        )
        adapter.connect()

        # Handshake must come first, then set-protocol.
        assert mock.sent_frames[0] == cmds["handshake"]
        assert mock.sent_frames[1] == cmds["set_protocol_j1850_vpw"]
        assert adapter.is_connected is True

    def test_connect_marks_connected(self):
        cmds = _BRIDGE_COMMANDS["generic"]
        mock = MockSerial(
            port="COM_TEST",
            baudrate=J1850_VPW_BAUD,
            responses={
                cmds["handshake"]: b"ELM327>",
                cmds["set_protocol_j1850_vpw"]: b"OK>",
            },
        )
        adapter = J1850Adapter(
            port="COM_TEST",
            serial_factory=_factory_returning(mock),
        )
        assert adapter.is_connected is False
        adapter.connect()
        assert adapter.is_connected is True

    def test_connect_raises_on_handshake_timeout(self):
        # No scripted response to handshake → mock returns b"" on read,
        # which the adapter surfaces as ProtocolTimeoutError and wraps
        # into J1850ConnectionError.
        mock = MockSerial(
            port="COM_TEST",
            baudrate=J1850_VPW_BAUD,
            responses={},
        )
        adapter = J1850Adapter(
            port="COM_TEST",
            serial_factory=_factory_returning(mock),
        )
        with pytest.raises(J1850ConnectionError) as excinfo:
            adapter.connect()
        assert "handshake" in str(excinfo.value).lower()
        assert adapter.is_connected is False

    def test_disconnect_closes_serial_and_clears_state(self):
        cmds = _BRIDGE_COMMANDS["generic"]
        mock = MockSerial(
            port="COM_TEST",
            baudrate=J1850_VPW_BAUD,
            responses={
                cmds["handshake"]: b"ELM327>",
                cmds["set_protocol_j1850_vpw"]: b"OK>",
            },
        )
        adapter = J1850Adapter(
            port="COM_TEST",
            serial_factory=_factory_returning(mock),
        )
        adapter.connect()
        assert adapter.is_connected is True

        adapter.disconnect()
        assert adapter.is_connected is False
        assert mock.closed is True


# ---------------------------------------------------------------------------
# TestJ1850AdapterReadDTC — multi-module polling
# ---------------------------------------------------------------------------


def _connected_adapter(bridge: str = "generic", extra_responses=None):
    """Helper: build a connected adapter with ECM/BCM/ABS all scripted empty."""

    cmds = _BRIDGE_COMMANDS[bridge]
    responses = {
        cmds["handshake"]: b"BRIDGE>",
        cmds["set_protocol_j1850_vpw"]: b"OK>",
        # Default: all three modules report NO DATA.
        cmds["read_dtc_ecm"]: b"NO DATA>",
        cmds["read_dtc_bcm"]: b"NO DATA>",
        cmds["read_dtc_abs"]: b"NO DATA>",
        cmds["clear_dtc_ecm"]: b"OK>",
        cmds["clear_dtc_bcm"]: b"OK>",
        cmds["clear_dtc_abs"]: b"OK>",
    }
    if extra_responses:
        responses.update(extra_responses)

    mock = MockSerial(
        port="COM_TEST",
        baudrate=J1850_VPW_BAUD,
        responses=responses,
    )
    adapter = J1850Adapter(
        port="COM_TEST",
        bridge=bridge,
        serial_factory=_factory_returning(mock),
    )
    adapter.connect()
    return adapter, mock


class TestJ1850AdapterReadDTC:
    def test_read_dtc_ecm_only_returns_p_codes(self):
        cmds = _BRIDGE_COMMANDS["generic"]
        # ECM frame: header 0x10, count 0x02, two DTCs 0x0172, 0x0043.
        adapter, _mock = _connected_adapter(
            extra_responses={
                cmds["read_dtc_ecm"]: b"10 02 01 72 00 43>",
            },
        )
        codes = adapter.read_dtcs()
        assert codes == ["P0172", "P0043"]

    def test_read_dtc_bcm_returns_b_codes(self):
        cmds = _BRIDGE_COMMANDS["generic"]
        # BCM frame sans header: count 0x01, DTC 0x1121
        # → "B1121" (security system ground fault on 2007-2010 Softails).
        adapter, _mock = _connected_adapter(
            extra_responses={
                cmds["read_dtc_bcm"]: b"01 11 21>",
            },
        )
        codes = adapter.read_dtcs()
        assert codes == ["B1121"]
        # Prefix must be B, never P — module prefix overrides SAE nibble.
        assert all(code.startswith("B") for code in codes)

    def test_read_dtc_abs_returns_c_codes(self):
        cmds = _BRIDGE_COMMANDS["generic"]
        # ABS frame: header 0x28, count 0x01, DTC 0x1014
        # → "C1014" (wheel speed sensor rear, Touring).
        adapter, _mock = _connected_adapter(
            extra_responses={
                cmds["read_dtc_abs"]: b"28 01 10 14>",
            },
        )
        codes = adapter.read_dtcs()
        assert codes == ["C1014"]

    def test_read_dtc_merges_all_three_modules_in_order(self):
        cmds = _BRIDGE_COMMANDS["generic"]
        adapter, _mock = _connected_adapter(
            extra_responses={
                # ECM: P0172, P0301
                cmds["read_dtc_ecm"]: b"10 02 01 72 03 01>",
                # BCM: B1121
                cmds["read_dtc_bcm"]: b"01 11 21>",
                # ABS: C1014
                cmds["read_dtc_abs"]: b"28 01 10 14>",
            },
        )
        codes = adapter.read_dtcs()
        # Order matters — ECM first, then BCM, then ABS.
        assert codes == ["P0172", "P0301", "B1121", "C1014"]

    def test_read_dtc_empty_when_no_faults(self):
        adapter, _mock = _connected_adapter()  # defaults are all NO DATA
        codes = adapter.read_dtcs()
        assert codes == []


# ---------------------------------------------------------------------------
# TestJ1850DtcParsing — unit tests on the parser in isolation
# ---------------------------------------------------------------------------


class TestJ1850DtcParsing:
    def test_parse_ecm_two_codes_with_header_and_count(self):
        # Header 0x10 (ECM echo), count 0x02, two DTCs.
        codes = _parse_j1850_response(b"10 02 01 72 00 43", "ECM")
        assert codes == ["P0172", "P0043"]

    def test_parse_bcm_single_code_no_header(self):
        # Bridge stripped module-ID echo. Count 0x01, DTC 0x1121.
        codes = _parse_j1850_response(b"01 11 21", "BCM")
        assert codes == ["B1121"]

    def test_parse_handles_whitespace_and_case(self):
        # Lowercase input, messy whitespace, embedded prompt byte.
        codes = _parse_j1850_response(b" 10  02   01 72 00 43  > ", "ECM")
        assert codes == ["P0172", "P0043"]

    def test_parse_empty_response_returns_empty_list(self):
        assert _parse_j1850_response(b"", "ECM") == []
        assert _parse_j1850_response(b"NO DATA", "ECM") == []
        assert _parse_j1850_response(b"?", "ABS") == []
        assert _parse_j1850_response(b"UNABLE TO CONNECT", "BCM") == []


# ---------------------------------------------------------------------------
# TestJ1850BridgeVariants — per-bridge command bytes
# ---------------------------------------------------------------------------


class TestJ1850BridgeVariants:
    def test_daytona_twin_tec_uses_its_command_bytes(self):
        cmds = _BRIDGE_COMMANDS["daytona"]
        mock = MockSerial(
            port="COM_TEST",
            baudrate=J1850_VPW_BAUD,
            responses={
                cmds["handshake"]: b"DAYTONA>",
                cmds["set_protocol_j1850_vpw"]: b"OK>",
            },
        )
        adapter = J1850Adapter(
            port="COM_TEST",
            bridge="daytona",
            serial_factory=_factory_returning(mock),
        )
        adapter.connect()
        assert b"AT@1\r" in mock.sent_frames
        # Must NOT have sent scangauge or dynojet handshake.
        assert b"DJI\r" not in mock.sent_frames

    def test_scan_gauge_ii_handshake_differs(self):
        cmds = _BRIDGE_COMMANDS["scangauge"]
        mock = MockSerial(
            port="COM_TEST",
            baudrate=J1850_VPW_BAUD,
            responses={
                cmds["handshake"]: b"SGII>",
                cmds["set_protocol_j1850_vpw"]: b"OK>",
            },
        )
        adapter = J1850Adapter(
            port="COM_TEST",
            bridge="scangauge",
            serial_factory=_factory_returning(mock),
        )
        adapter.connect()
        assert cmds["handshake"] in mock.sent_frames
        # Scangauge handshake bytes differ from daytona.
        assert cmds["handshake"] != _BRIDGE_COMMANDS["daytona"]["handshake"]

    def test_unknown_bridge_raises_value_error(self):
        with pytest.raises(ValueError) as excinfo:
            J1850Adapter(port="COM_TEST", bridge="made_up_bridge")
        msg = str(excinfo.value)
        assert "made_up_bridge" in msg
        # Message should mention at least one supported bridge name.
        assert any(bridge in msg for bridge in SUPPORTED_BRIDGES)


# ---------------------------------------------------------------------------
# TestJ1850ClearAndInfo — clear_dtcs + metadata surface
# ---------------------------------------------------------------------------


class TestJ1850ClearAndInfo:
    def test_clear_dtc_all_sends_three_commands(self):
        adapter, mock = _connected_adapter()
        result = adapter.clear_dtcs()
        cmds = _BRIDGE_COMMANDS["generic"]

        # All three clear-commands must appear in the sent-frames log.
        assert cmds["clear_dtc_ecm"] in mock.sent_frames
        assert cmds["clear_dtc_bcm"] in mock.sent_frames
        assert cmds["clear_dtc_abs"] in mock.sent_frames
        assert result is True

    def test_clear_dtc_specific_module(self):
        adapter, mock = _connected_adapter()
        # Reset sent_frames to only measure clear-time writes.
        mock.sent_frames.clear()

        result = adapter.clear_dtcs(module="ECM")
        cmds = _BRIDGE_COMMANDS["generic"]
        assert mock.sent_frames == [cmds["clear_dtc_ecm"]]
        # BCM and ABS clear commands must NOT have been sent.
        assert cmds["clear_dtc_bcm"] not in mock.sent_frames
        assert cmds["clear_dtc_abs"] not in mock.sent_frames
        assert result is True

    def test_adapter_info_returns_protocol_metadata(self):
        adapter = J1850Adapter(
            port="COM_TEST",
            bridge="daytona",
            # No serial_factory needed — adapter_info doesn't touch I/O.
            serial_factory=lambda **_: MockSerial(port="COM_TEST", baudrate=10400),
        )
        info = adapter.adapter_info()
        assert info["protocol"] == PROTOCOL_NAME
        assert info["baud"] == J1850_VPW_BAUD
        assert info["bridge"] == "daytona"
        assert info["port"] == "COM_TEST"
        # Not connected yet.
        assert info["connected"] is False
        assert info["timeout_s"] == DEFAULT_READ_TIMEOUT_S

    def test_read_pid_raises_not_implemented(self):
        # Bonus coverage: read_pid is a Phase 141 stub.
        adapter, _mock = _connected_adapter()
        with pytest.raises(NotImplementedError) as excinfo:
            adapter.read_pid(0x0C)
        assert "141" in str(excinfo.value)

    def test_read_vin_raises_unsupported(self):
        # Bonus coverage: VIN not supported on pre-2008 Harley J1850.
        adapter, _mock = _connected_adapter()
        with pytest.raises(UnsupportedCommandError) as excinfo:
            adapter.read_vin()
        assert excinfo.value.command == "read_vin"

    def test_get_protocol_name_stable(self):
        # Bonus: ensure the Phase 134 protocol-name contract is honored.
        adapter = J1850Adapter(
            port="COM_TEST",
            serial_factory=lambda **_: MockSerial(port="COM_TEST", baudrate=10400),
        )
        assert adapter.get_protocol_name() == "SAE J1850 VPW"


# ---------------------------------------------------------------------------
# Additional coverage — disconnected-adapter safety
# ---------------------------------------------------------------------------


class TestJ1850DisconnectedSafety:
    def test_read_dtcs_raises_when_disconnected(self):
        adapter = J1850Adapter(
            port="COM_TEST",
            serial_factory=lambda **_: MockSerial(port="COM_TEST", baudrate=10400),
        )
        with pytest.raises(ProtocolConnectionError):
            adapter.read_dtcs()

    def test_send_command_raises_when_disconnected(self):
        adapter = J1850Adapter(
            port="COM_TEST",
            serial_factory=lambda **_: MockSerial(port="COM_TEST", baudrate=10400),
        )
        with pytest.raises(ProtocolConnectionError):
            adapter.send_command(b"anything\r")
