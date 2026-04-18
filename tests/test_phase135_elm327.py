"""Phase 135 — ELM327 adapter tests.

Every test here is pure-Python: zero real serial ports, zero real
timeouts (one test uses a 0.01 s wall-clock budget to exercise the
timeout path without flaking CI), zero live tokens. The mock seam is
:func:`motodiag.hardware.protocols.elm327._get_serial_module` — tests
monkey-patch that indirection to return a fake ``serial`` module whose
``Serial(...)`` constructor returns a :class:`_FakeSerial` whose
``.read(n)`` pops bytes from a pre-queued ``bytearray``.

Test classes
------------

- :class:`TestDTCDecoder` — pure-function SAE J2012 decoder tests.
- :class:`TestHelperParsers` — ``_is_elm_error``, ``_strip_noise``,
  ``_strip_multiframe_prefixes`` pure helpers.
- :class:`TestConnectDisconnect` — init sequence, idempotency,
  install-hint when pyserial missing, SerialException wrap.
- :class:`TestSendCommand` — clean response, timeout, error-token
  detection, noise stripping.
- :class:`TestReadDTCs` — single code, multi-code, NO DATA → [],
  multi-frame reassembly.
- :class:`TestClearDTCs` — 44 ACK, 7F NACK, unexpected response.
- :class:`TestReadPID` — single-byte, two-byte, invalid args,
  unsupported (7F NACK) → None.
- :class:`TestReadVIN` — 3-frame reassembly, short-response guard.
- :class:`TestPublicAPI` — ``ELM327Adapter`` is importable from the
  package surface; ``get_protocol_name`` lookup.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from motodiag.hardware.protocols import (
    ELM327Adapter,
    ProtocolAdapter,
    ProtocolError,
)
from motodiag.hardware.protocols import (
    ConnectionError as ProtocolConnectionError,
)
from motodiag.hardware.protocols import (
    TimeoutError as ProtocolTimeoutError,
)
from motodiag.hardware.protocols import elm327 as elm327_mod
from motodiag.hardware.protocols.elm327 import (
    _is_elm_error,
    _parse_dtc_hex,
    _strip_multiframe_prefixes,
    _strip_noise,
)


# ---------------------------------------------------------------------------
# Mock-serial infrastructure
# ---------------------------------------------------------------------------


class _FakeSerial:
    """Minimal stand-in for ``serial.Serial``.

    Tests push bytes onto ``_rx_buffer`` via the module-level
    :func:`feed` helper; each ``.read(n)`` call pops up to ``n`` bytes
    off the front. ``.write(data)`` records the last payload on
    ``last_write`` so assertions like "did the adapter send ATZ first?"
    are one-liners.
    """

    def __init__(self, port: str, baud: int, timeout: float) -> None:
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.is_open = True
        self._rx_buffer = bytearray()
        self.writes: list[bytes] = []
        self.last_write: bytes = b""
        self.closed = False

    def read(self, n: int = 1) -> bytes:
        if not self._rx_buffer:
            return b""
        take = min(n, len(self._rx_buffer))
        out = bytes(self._rx_buffer[:take])
        del self._rx_buffer[:take]
        return out

    def write(self, data: bytes) -> int:
        self.writes.append(bytes(data))
        self.last_write = bytes(data)
        return len(data)

    def close(self) -> None:
        self.closed = True
        self.is_open = False

    def reset_input_buffer(self) -> None:
        # Intentionally a no-op. In real hardware this drains stale
        # bytes on the wire; in tests the buffer is the staged reply,
        # so clearing it would wipe out the next response.
        return None


class _FakeSerialModule:
    """Fake ``serial`` module exposing ``Serial`` and ``SerialException``."""

    class SerialException(Exception):
        pass

    def __init__(self) -> None:
        self._next_serial: _FakeSerial | None = None
        self._raise_on_open: Exception | None = None
        self.last_port: str | None = None
        self.last_baud: int | None = None
        self.last_timeout: float | None = None

    def Serial(self, port: str, baud: int, timeout: float) -> _FakeSerial:
        self.last_port = port
        self.last_baud = baud
        self.last_timeout = timeout
        if self._raise_on_open is not None:
            raise self._raise_on_open
        if self._next_serial is None:
            self._next_serial = _FakeSerial(port, baud, timeout)
        return self._next_serial


def feed(fake: _FakeSerial, payload: bytes) -> None:
    """Stage a full ELM reply in the mock's rx buffer.

    Ensures the payload ends with ``>`` so the read-until-prompt
    loop terminates. Callers pass bytes exactly as the chip would
    emit them (CR-separated, typically ending in ``\\r>``).
    """

    fake._rx_buffer.extend(payload)
    if not payload.endswith(b">"):
        fake._rx_buffer.extend(b"\r>")


def queue_ok_init(fake: _FakeSerial, banner: bytes = b"ELM327 v1.5") -> None:
    """Queue the six init responses (banner + 5x OK).

    ATZ echoes the banner; ATE0/ATL0/ATS0/ATH0/ATSP0 each echo ``OK``.
    """

    feed(fake, banner + b"\r\r>")
    for _ in range(5):
        feed(fake, b"OK\r>")


@pytest.fixture
def fake_serial_module(monkeypatch):
    """Install a fake ``serial`` module via the ``_get_serial_module`` seam."""

    mod = _FakeSerialModule()
    monkeypatch.setattr(elm327_mod, "_get_serial_module", lambda: mod)
    return mod


@pytest.fixture
def connected_adapter(fake_serial_module) -> tuple[ELM327Adapter, _FakeSerial]:
    """Pre-connected adapter plus the fake serial it's talking to."""

    fake = _FakeSerial("COM5", 38400, 2.0)
    fake_serial_module._next_serial = fake
    queue_ok_init(fake)
    adapter = ELM327Adapter("COM5")
    adapter.connect()
    # Clear the write log so per-test assertions start fresh.
    fake.writes.clear()
    return adapter, fake


# ---------------------------------------------------------------------------
# TestDTCDecoder — pure function, no mocking needed
# ---------------------------------------------------------------------------


class TestDTCDecoder:
    """Direct unit tests for ``_parse_dtc_hex``."""

    def test_p_code(self):
        assert _parse_dtc_hex([("01", "33")]) == ["P0133"]

    def test_c_code(self):
        assert _parse_dtc_hex([("41", "23")]) == ["C0123"]

    def test_b_code(self):
        assert _parse_dtc_hex([("81", "56")]) == ["B0156"]

    def test_u_code(self):
        assert _parse_dtc_hex([("C1", "89")]) == ["U0189"]

    def test_filters_zero_padding(self):
        # 00 00 is the zero-padding byte pair used by ECUs to fill
        # the response frame — must be dropped.
        result = _parse_dtc_hex([("01", "33"), ("00", "00")])
        assert result == ["P0133"]

    def test_empty_input(self):
        assert _parse_dtc_hex([]) == []

    def test_multiple_mixed_prefixes(self):
        result = _parse_dtc_hex(
            [("01", "71"), ("43", "05"), ("82", "22"), ("C0", "FF")]
        )
        assert result == ["P0171", "C0305", "B0222", "U00FF"]


# ---------------------------------------------------------------------------
# TestHelperParsers — more pure functions
# ---------------------------------------------------------------------------


class TestHelperParsers:
    def test_is_elm_error_no_data(self):
        assert _is_elm_error("NO DATA") == "NO DATA"

    def test_is_elm_error_unable_to_connect(self):
        assert _is_elm_error("UNABLE TO CONNECT") == "UNABLE TO CONNECT"

    def test_is_elm_error_can_error(self):
        assert _is_elm_error("CAN ERROR") == "CAN ERROR"

    def test_is_elm_error_question_mark_alone(self):
        assert _is_elm_error("?") == "?"

    def test_is_elm_error_none_on_clean(self):
        assert _is_elm_error("41 0C 1A F8") is None
        assert _is_elm_error("") is None

    def test_strip_noise_removes_searching(self):
        assert _strip_noise("SEARCHING...\nOK") == "OK"

    def test_strip_multiframe_prefixes_joins_lines(self):
        raw = "0: 49 02 01 31 48 47\n1: 43 4D 38 32 36 33\n2: 33 41 30 30 34 33"
        joined = _strip_multiframe_prefixes(raw)
        assert "0:" not in joined
        assert "1:" not in joined
        assert "49 02 01" in joined
        assert "30 30 34 33" in joined


# ---------------------------------------------------------------------------
# TestConnectDisconnect
# ---------------------------------------------------------------------------


class TestConnectDisconnect:
    def test_connect_sends_init_sequence_in_order(self, fake_serial_module):
        fake = _FakeSerial("COM5", 38400, 2.0)
        fake_serial_module._next_serial = fake
        queue_ok_init(fake)

        adapter = ELM327Adapter("COM5")
        adapter.connect()

        # Extract the command part (before CR) from each write.
        cmds = [w.split(b"\r")[0].decode("ascii") for w in fake.writes]
        assert cmds[:6] == ["ATZ", "ATE0", "ATL0", "ATS0", "ATH0", "ATSP0"]
        assert adapter.is_connected is True
        assert "ELM327" in (adapter._device_description or "")

    def test_connect_honors_custom_protocol(self, fake_serial_module):
        fake = _FakeSerial("COM5", 38400, 2.0)
        fake_serial_module._next_serial = fake
        queue_ok_init(fake)

        adapter = ELM327Adapter("COM5", protocol="6")
        adapter.connect()

        cmds = [w.split(b"\r")[0].decode("ascii") for w in fake.writes]
        assert "ATSP6" in cmds

    def test_connect_is_idempotent(self, connected_adapter):
        adapter, fake = connected_adapter
        pre_count = len(fake.writes)
        adapter.connect()  # second call — should no-op
        assert len(fake.writes) == pre_count

    def test_connect_raises_when_pyserial_missing(self, monkeypatch):
        def _boom():
            raise ImportError("No module named 'serial'")

        monkeypatch.setattr(elm327_mod, "_get_serial_module", _boom)
        adapter = ELM327Adapter("COM5")
        with pytest.raises(ProtocolError) as exc:
            adapter.connect()
        assert "pip install" in str(exc.value)
        assert "motodiag[hardware]" in str(exc.value)

    def test_connect_wraps_serial_exception(self, fake_serial_module):
        fake_serial_module._raise_on_open = fake_serial_module.SerialException(
            "port busy"
        )
        adapter = ELM327Adapter("COM5")
        with pytest.raises(ProtocolConnectionError) as exc:
            adapter.connect()
        assert "COM5" in str(exc.value)

    def test_connect_cleans_up_on_init_failure(self, fake_serial_module):
        fake = _FakeSerial("COM5", 38400, 2.0)
        fake_serial_module._next_serial = fake
        # Banner OK; ATE0 reply is junk → init should abort.
        feed(fake, b"ELM327 v1.5\r>")
        feed(fake, b"WHAT?\r>")  # ATE0 reply (no 'OK')

        adapter = ELM327Adapter("COM5")
        with pytest.raises(ProtocolConnectionError):
            adapter.connect()
        assert adapter.is_connected is False
        assert fake.closed is True

    def test_disconnect_is_idempotent(self, connected_adapter):
        adapter, fake = connected_adapter
        adapter.disconnect()
        adapter.disconnect()  # must not raise
        assert adapter.is_connected is False
        assert fake.closed is True

    def test_disconnect_swallows_cleanup_errors(self, connected_adapter):
        adapter, fake = connected_adapter
        # Force close() to raise — disconnect() must not propagate.
        fake.close = MagicMock(side_effect=OSError("device removed"))
        adapter.disconnect()
        assert adapter.is_connected is False

    def test_is_connected_is_false_before_connect(self, fake_serial_module):
        adapter = ELM327Adapter("COM5")
        assert adapter.is_connected is False

    def test_is_subclass_of_protocol_adapter(self):
        assert issubclass(ELM327Adapter, ProtocolAdapter)


# ---------------------------------------------------------------------------
# TestSendCommand
# ---------------------------------------------------------------------------


class TestSendCommand:
    def test_send_command_returns_bytes(self, connected_adapter):
        adapter, fake = connected_adapter
        feed(fake, b"ELM327 v1.5\r>")
        reply = adapter.send_command("ATI")
        assert isinstance(reply, bytes)
        assert b"ELM327" in reply

    def test_send_command_writes_cr_terminator(self, connected_adapter):
        adapter, fake = connected_adapter
        feed(fake, b"OK\r>")
        adapter.send_command("ATI")
        assert fake.last_write.endswith(b"\r")

    def test_send_command_times_out_on_no_prompt(self, connected_adapter):
        adapter, _fake = connected_adapter
        # rx buffer empty — read_until_prompt must raise TimeoutError
        # within the tiny real-clock budget. 0.01 s is fast enough that
        # even a heavily-loaded CI runner will hit the deadline quickly.
        with pytest.raises(ProtocolTimeoutError):
            adapter.send_command("ATI", timeout=0.01)

    def test_send_command_raises_on_no_data(self, connected_adapter):
        adapter, fake = connected_adapter
        feed(fake, b"NO DATA\r>")
        with pytest.raises(ProtocolError) as exc:
            adapter.send_command("0100")
        assert "NO DATA" in str(exc.value)

    def test_send_command_raises_on_unable_to_connect(self, connected_adapter):
        adapter, fake = connected_adapter
        feed(fake, b"UNABLE TO CONNECT\r>")
        with pytest.raises(ProtocolError):
            adapter.send_command("0100")

    def test_send_command_strips_searching_noise(self, connected_adapter):
        adapter, fake = connected_adapter
        feed(fake, b"SEARCHING...\r41 0C 1A F8\r>")
        reply = adapter.send_command("010C")
        assert b"SEARCHING" not in reply
        assert b"41 0C" in reply

    def test_send_command_when_not_connected_raises(self):
        adapter = ELM327Adapter("COM5")
        with pytest.raises(ProtocolConnectionError):
            adapter.send_command("ATI")


# ---------------------------------------------------------------------------
# TestReadDTCs
# ---------------------------------------------------------------------------


class TestReadDTCs:
    def test_single_code(self, connected_adapter):
        adapter, fake = connected_adapter
        # 43 (Mode 03 + 0x40), count byte 01, then the one DTC: 01 33.
        feed(fake, b"43 01 01 33 00 00 00 00\r>")
        codes = adapter.read_dtcs()
        assert codes == ["P0133"]

    def test_multi_code_mixed_prefixes(self, connected_adapter):
        adapter, fake = connected_adapter
        # Four codes: P0171, C0123, B0456, U0789.
        # B0456 encoding: byte1 = 0x80 | 0x04 = 0x84, byte2 = 0x56
        # U0789 encoding: byte1 = 0xC0 | 0x07 = 0xC7, byte2 = 0x89
        feed(fake, b"43 04 01 71 41 23 84 56 C7 89\r>")
        codes = adapter.read_dtcs()
        assert codes == sorted(["P0171", "C0123", "B0456", "U0789"])

    def test_no_data_returns_empty(self, connected_adapter):
        adapter, fake = connected_adapter
        feed(fake, b"NO DATA\r>")
        assert adapter.read_dtcs() == []

    def test_multiframe_response(self, connected_adapter):
        adapter, fake = connected_adapter
        # A multi-line CAN response: count header, then three DTCs
        # split across two ELM lines with 0: / 1: prefixes.
        feed(
            fake,
            b"009\r0: 43 03 01 33 01 34\r1: 01 35 00 00 00 00\r>",
        )
        codes = adapter.read_dtcs()
        assert set(codes) == {"P0133", "P0134", "P0135"}

    def test_missing_43_prefix_raises(self, connected_adapter):
        adapter, fake = connected_adapter
        feed(fake, b"42 01 02 03\r>")
        with pytest.raises(ProtocolError):
            adapter.read_dtcs()


# ---------------------------------------------------------------------------
# TestClearDTCs
# ---------------------------------------------------------------------------


class TestClearDTCs:
    def test_clear_success(self, connected_adapter):
        adapter, fake = connected_adapter
        feed(fake, b"44\r>")
        assert adapter.clear_dtcs() is True

    def test_clear_nack_returns_false(self, connected_adapter):
        adapter, fake = connected_adapter
        # 7F 04 22 = negative response to Mode 04 (conditions not
        # correct — e.g., ignition off, engine running).
        feed(fake, b"7F 04 22\r>")
        assert adapter.clear_dtcs() is False

    def test_clear_unexpected_response_raises(self, connected_adapter):
        adapter, fake = connected_adapter
        feed(fake, b"99 99\r>")
        with pytest.raises(ProtocolError):
            adapter.clear_dtcs()


# ---------------------------------------------------------------------------
# TestReadPID
# ---------------------------------------------------------------------------


class TestReadPID:
    def test_read_pid_single_byte_coolant(self, connected_adapter):
        adapter, fake = connected_adapter
        # Mode 01 PID 05 (coolant temp). Reply: 41 05 7B → raw=0x7B=123.
        feed(fake, b"41 05 7B\r>")
        assert adapter.read_pid(0x05) == 0x7B

    def test_read_pid_two_bytes_rpm(self, connected_adapter):
        adapter, fake = connected_adapter
        # Mode 01 PID 0C (RPM). Reply: 41 0C 1A F8.
        feed(fake, b"41 0C 1A F8\r>")
        assert adapter.read_pid(0x0C) == 0x1AF8

    def test_read_pid_rejects_bad_mode(self, connected_adapter):
        adapter, _fake = connected_adapter
        with pytest.raises(ValueError):
            adapter.read_pid(0x05, mode=3)

    def test_read_pid_rejects_out_of_range(self, connected_adapter):
        adapter, _fake = connected_adapter
        with pytest.raises(ValueError):
            adapter.read_pid(0x100)
        with pytest.raises(ValueError):
            adapter.read_pid(-1)

    def test_read_pid_unsupported_returns_none(self, connected_adapter):
        adapter, fake = connected_adapter
        # 7F 01 12 = negative-response subfunction-not-supported.
        feed(fake, b"7F 01 12\r>")
        assert adapter.read_pid(0x77) is None

    def test_read_pid_no_data_returns_none(self, connected_adapter):
        adapter, fake = connected_adapter
        feed(fake, b"NO DATA\r>")
        assert adapter.read_pid(0x05) is None


# ---------------------------------------------------------------------------
# TestReadVIN
# ---------------------------------------------------------------------------


class TestReadVIN:
    def test_read_vin_multi_frame(self, connected_adapter):
        adapter, fake = connected_adapter
        # Classic 17-char VIN "1HGCM82633A004352" (Honda Accord example,
        # canonical in OBD-II docs — same shape Harley + Honda MC ECUs use).
        # Bytes: 31 48 47 43 4D 38 32 36 33 33 41 30 30 34 33 35 32
        # ELM327 splits the 49 02 01 prefix + 17 payload bytes across
        # three lines of 7 bytes each (line 0 includes the prefix).
        feed(
            fake,
            b"014\r"
            b"0: 49 02 01 31 48 47\r"
            b"1: 43 4D 38 32 36 33 33\r"
            b"2: 41 30 30 34 33 35 32\r>",
        )
        vin = adapter.read_vin()
        assert vin == "1HGCM82633A004352"

    def test_read_vin_short_response_raises(self, connected_adapter):
        adapter, fake = connected_adapter
        # Too-short response — only a few payload bytes.
        feed(fake, b"49 02 01 31 48 47\r>")
        with pytest.raises(ProtocolError):
            adapter.read_vin()

    def test_read_vin_no_data_returns_none(self, connected_adapter):
        adapter, fake = connected_adapter
        feed(fake, b"NO DATA\r>")
        assert adapter.read_vin() is None


# ---------------------------------------------------------------------------
# TestPublicAPI
# ---------------------------------------------------------------------------


class TestPublicAPI:
    def test_elm327_adapter_importable_from_package(self):
        from motodiag.hardware.protocols import ELM327Adapter as Exported

        assert Exported is ELM327Adapter

    def test_get_protocol_name_auto(self):
        adapter = ELM327Adapter("COM5", protocol="0")
        assert "auto" in adapter.get_protocol_name().lower()

    def test_get_protocol_name_iso15765(self):
        adapter = ELM327Adapter("COM5", protocol="6")
        assert "15765" in adapter.get_protocol_name()

    def test_get_protocol_name_unknown_fallback(self):
        adapter = ELM327Adapter("COM5", protocol="Z")
        name = adapter.get_protocol_name()
        assert "Z" in name
