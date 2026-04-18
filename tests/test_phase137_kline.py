"""Phase 137 — K-line / KWP2000 adapter tests.

Covers the full surface of :mod:`motodiag.hardware.protocols.kline`:

* ``TestSlowBaudInit`` — 5-baud address-byte handshake: bit-clocking,
  keybyte exchange, sync-byte validation, timeout on silent ECU.
* ``TestFastInit`` — ISO 14230-2 fast-init wakeup pattern and
  StartCommunication echo.
* ``TestFraming`` — FMT byte duality, checksum, length mismatch
  detection — exercised as module-level pure functions so they run
  without a serial port.
* ``TestEchoCancellation`` — half-duplex echo drain, mismatch raises
  a wiring-hint :class:`ProtocolError`.
* ``TestServiceMethods`` — read DTCs, clear DTCs, reset ECU, read ECU
  identification, VIN, negative-response translation.
* ``TestDefensive`` — lazy pyserial import, idempotent disconnect,
  invalid constructor args, StopSession failure suppression.
* ``TestConstants`` — ISO-14230 service IDs and timing envelope values
  are pinned so future refactors don't drift.

Strategy: a purpose-built :class:`ScriptedSerial` stands in for the
real ``serial.Serial`` with a queued RX buffer, captured writes, and a
setattr hook that records ``break_condition`` toggles (used to prove
the 5-baud init clocks the line correctly). ``time.sleep`` is
monkeypatched to a no-op so the full suite runs in sub-second wall
time even though the production slow-init takes ~2.2 s. No live
hardware, no real waits, zero tokens.
"""

from __future__ import annotations

from typing import List

import pytest

from motodiag.hardware.protocols.exceptions import ProtocolError
from motodiag.hardware.protocols.kline import (
    ADDR_ECU_DEFAULT,
    ADDR_TESTER_DEFAULT,
    DIAG_MODE_DEFAULT,
    FAST_INIT_TINIL,
    FAST_INIT_TWUP,
    NEGATIVE_RESPONSE_SID,
    P1_MAX,
    P2_MAX,
    P2_MIN,
    POSITIVE_RESPONSE_OFFSET,
    SID_CLEAR_DIAGNOSTIC_INFO,
    SID_ECU_RESET,
    SID_READ_DTC_BY_STATUS,
    SID_READ_ECU_IDENTIFICATION,
    SID_START_DIAGNOSTIC_SESSION,
    W1_MAX,
    W2_MAX,
    W3_MAX,
    W4,
    W5_MIN,
    KLineAdapter,
    _build_frame,
    _decode_kwp_dtc,
    _parse_frame,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class ScriptedSerial:
    """A MagicMock-compatible fake ``serial.Serial``.

    ``write()`` captures outbound bytes and (by default) stages them
    back as echo for the next ``read()``. Callers can additionally
    stage ECU response bytes via :meth:`queue_response` — these are
    appended after any pending echo.

    The scripted-response model mirrors the half-duplex K-line wire:
    every TX byte bounces back before the ECU reply arrives.
    """

    def __init__(self, baud: int = 10400, local_echo: bool = True) -> None:
        self.is_open: bool = True
        self.baudrate: int = baud
        self.break_condition: bool = False
        self._local_echo: bool = local_echo
        self._rx: bytearray = bytearray()
        self.writes: List[bytes] = []
        self.break_toggles: List[bool] = []
        self.closed: bool = False

    # --- properties mocked to track break toggles ---

    def __setattr__(self, name: str, value: object) -> None:
        if name == "break_condition" and "_rx" in self.__dict__:
            self.__dict__.setdefault("break_toggles", []).append(bool(value))
        object.__setattr__(self, name, value)

    # --- pyserial-compatible methods ---

    def write(self, data: bytes) -> int:
        data = bytes(data)
        self.writes.append(data)
        if self._local_echo:
            self._rx.extend(data)
        return len(data)

    def read(self, n: int = 1) -> bytes:
        if n <= 0 or not self._rx:
            return b""
        n = min(n, len(self._rx))
        chunk = bytes(self._rx[:n])
        del self._rx[:n]
        return chunk

    def close(self) -> None:
        self.is_open = False
        self.closed = True

    # --- test-only utilities ---

    def queue_response(self, data: bytes) -> None:
        self._rx.extend(bytes(data))

    def queue_at_head(self, data: bytes) -> None:
        """Queue bytes before any currently-pending RX (rare)."""
        self._rx = bytearray(bytes(data)) + self._rx

    def clear_rx(self) -> None:
        self._rx.clear()

    def disable_echo(self) -> None:
        self._local_echo = False


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutralize ``time.sleep`` across the module so slow-init is ~instant."""
    import time as _time

    monkeypatch.setattr(_time, "sleep", lambda *a, **kw: None)
    # Belt and suspenders: kline.py imported ``time`` at module level.
    import motodiag.hardware.protocols.kline as _kline_mod

    monkeypatch.setattr(_kline_mod.time, "sleep", lambda *a, **kw: None)


@pytest.fixture
def fake_serial_factory(monkeypatch: pytest.MonkeyPatch):
    """Return a factory that installs a :class:`ScriptedSerial` at import time."""
    import serial as _pyserial

    def _install(baud: int = 10400, local_echo: bool = True) -> ScriptedSerial:
        fake = ScriptedSerial(baud=baud, local_echo=local_echo)
        monkeypatch.setattr(
            _pyserial, "Serial", lambda *a, **kw: fake
        )
        return fake

    return _install


def _frame(
    payload: bytes,
    ecu_address: int = ADDR_ECU_DEFAULT,
    tester_address: int = ADDR_TESTER_DEFAULT,
) -> bytes:
    """Build a valid KWP2000 ECU-origin frame for scripted responses.

    For ECU responses the target (TGT) is the tester and the source
    (SRC) is the ECU, so we swap addresses relative to a tester
    request.
    """
    return _build_frame(
        payload=payload,
        ecu_address=tester_address,  # ECU targets tester
        tester_address=ecu_address,  # ECU sources from its own address
    )


def _build_successful_adapter(
    fake_serial_factory,
    *,
    baud: int = 10400,
    init_mode: str = "slow",
    ecu_address: int = ADDR_ECU_DEFAULT,
) -> tuple[KLineAdapter, ScriptedSerial]:
    """Construct + connect a fully-handshaken KLineAdapter on a ScriptedSerial.

    This is the standard setup for service-method tests so each one
    doesn't have to re-stage the full wakeup.
    """
    fake = fake_serial_factory(baud=baud, local_echo=False)
    # local_echo=False: we'll hand-queue echo + response so the test
    # controls exact byte ordering.

    adapter = KLineAdapter(
        port="COM_FAKE",
        baud=baud,
        ecu_address=ecu_address,
        init_mode=init_mode,  # type: ignore[arg-type]
    )

    if init_mode == "slow":
        # Pre-queue: sync, kb1, kb2, (echo of ~kb2 — we insert
        # inline), final ECU address echo
        inverted_kb2 = bytes([(0xEF ^ 0xFF) & 0xFF])
        fake.queue_response(b"\x55\x8F\xEF" + inverted_kb2 + bytes([(ecu_address ^ 0xFF) & 0xFF]))
    else:
        # Fast init: build a framed StartCommunication response
        # [0xC1, kb1, kb2].
        fastinit_resp = _frame(bytes([0xC1, 0x8F, 0xEF]))
        # The adapter also writes its own StartCommunication frame and
        # drains echo — with local_echo=False we must queue that echo
        # explicitly. We know the exact frame bytes: FMT=(0x80|1)=0x81,
        # TGT=ecu, SRC=tester, 0x81, CS.
        request = _build_frame(
            payload=bytes([0x81]),
            ecu_address=ecu_address,
            tester_address=ADDR_TESTER_DEFAULT,
        )
        fake.queue_response(request + fastinit_resp)

    # After init the adapter sends StartDiagnosticSession 0x10 0x81
    # and expects a framed 0x50 0x81 response. Stage the echo +
    # response.
    sds_request = _build_frame(
        payload=bytes([SID_START_DIAGNOSTIC_SESSION, DIAG_MODE_DEFAULT]),
        ecu_address=ecu_address,
        tester_address=ADDR_TESTER_DEFAULT,
    )
    sds_response = _build_frame(
        payload=bytes([
            SID_START_DIAGNOSTIC_SESSION + POSITIVE_RESPONSE_OFFSET,
            0x81,
        ]),
        ecu_address=ADDR_TESTER_DEFAULT,  # ECU's frame: swap addresses
        tester_address=ecu_address,
    )
    fake.queue_response(sds_request + sds_response)

    adapter.connect()
    return adapter, fake


# ---------------------------------------------------------------------------
# TestSlowBaudInit
# ---------------------------------------------------------------------------


class TestSlowBaudInit:
    def test_slow_init_success_10400_baud(self, fake_serial_factory) -> None:
        adapter, fake = _build_successful_adapter(
            fake_serial_factory, baud=10400, init_mode="slow"
        )
        assert adapter.is_connected is True
        assert adapter.keybytes == (0x8F, 0xEF)
        # One break toggle per bit-cell: start + 8 data + stop = 10
        assert len(fake.break_toggles) >= 10

    def test_slow_init_success_9600_baud(self, fake_serial_factory) -> None:
        adapter, fake = _build_successful_adapter(
            fake_serial_factory, baud=9600, init_mode="slow"
        )
        assert adapter.is_connected is True
        # Adapter must have switched pyserial to 9600 at the end of
        # the slow-baud window.
        assert fake.baudrate == 9600

    def test_slow_init_sync_byte_mismatch(self, fake_serial_factory) -> None:
        fake = fake_serial_factory(local_echo=False)
        adapter = KLineAdapter(port="COM_FAKE")
        # Queue 0x00 instead of 0x55 — sync check should blow up.
        fake.queue_response(b"\x00")
        with pytest.raises(ProtocolError) as excinfo:
            adapter.connect()
        assert "sync byte mismatch" in str(excinfo.value)
        assert adapter.is_connected is False

    def test_slow_init_address_echo_mismatch(
        self, fake_serial_factory
    ) -> None:
        fake = fake_serial_factory(local_echo=False)
        adapter = KLineAdapter(port="COM_FAKE", ecu_address=0x11)
        # Good sync + keybytes + wrong final echo byte
        fake.queue_response(b"\x55\x8F\xEF")
        # Echo of ~kb2 (0x10) then wrong final byte (0xAB instead of 0xEE)
        fake.queue_response(b"\x10\xAB")
        with pytest.raises(ProtocolError) as excinfo:
            adapter.connect()
        assert "final handshake mismatch" in str(excinfo.value)
        assert adapter.is_connected is False

    def test_slow_init_timeout_on_sync(self, fake_serial_factory) -> None:
        fake = fake_serial_factory(local_echo=False)
        adapter = KLineAdapter(port="COM_FAKE")
        # Queue nothing — _read_exact must raise ProtocolTimeoutError.
        with pytest.raises(ProtocolError) as excinfo:
            adapter.connect()
        # Either a timeout OR a sync-byte mismatch on empty bytes.
        assert (
            "timeout" in str(excinfo.value).lower()
            or "sync byte" in str(excinfo.value).lower()
        )

    def test_slow_init_bit_clocking_count(self, fake_serial_factory) -> None:
        """break_condition should toggle through start + 8 data + stop = 10 transitions."""
        adapter, fake = _build_successful_adapter(
            fake_serial_factory, baud=10400, init_mode="slow"
        )
        # First 10 toggles should cover the slow-init bit sequence.
        # The fake tracks every set; we expect at least 10.
        assert len(fake.break_toggles) >= 10


# ---------------------------------------------------------------------------
# TestFastInit
# ---------------------------------------------------------------------------


class TestFastInit:
    def test_fast_init_success(self, fake_serial_factory) -> None:
        adapter, fake = _build_successful_adapter(
            fake_serial_factory, baud=10400, init_mode="fast"
        )
        assert adapter.is_connected is True
        assert adapter.keybytes == (0x8F, 0xEF)

    def test_fast_init_rejects_non_c1_leading_byte(
        self, fake_serial_factory
    ) -> None:
        fake = fake_serial_factory(local_echo=False)
        adapter = KLineAdapter(port="COM_FAKE", init_mode="fast")

        # Script: adapter writes a StartCommunication frame (we echo)
        # then we respond with a framed payload whose first byte is
        # NOT 0xC1.
        request = _build_frame(
            payload=bytes([0x81]),
            ecu_address=ADDR_ECU_DEFAULT,
            tester_address=ADDR_TESTER_DEFAULT,
        )
        bad_response = _build_frame(
            payload=bytes([0xBB, 0x8F, 0xEF]),
            ecu_address=ADDR_TESTER_DEFAULT,
            tester_address=ADDR_ECU_DEFAULT,
        )
        fake.queue_response(request + bad_response)

        with pytest.raises(ProtocolError) as excinfo:
            adapter.connect()
        assert "fast init" in str(excinfo.value).lower()
        assert adapter.is_connected is False


# ---------------------------------------------------------------------------
# TestFraming
# ---------------------------------------------------------------------------


class TestFraming:
    def test_build_frame_short_payload(self) -> None:
        payload = bytes([0x10, 0x81])  # 2-byte payload
        frame = _build_frame(payload, ecu_address=0x11, tester_address=0xF1)
        # FMT = 0b10_000010 = 0x82
        assert frame[0] == 0x82
        assert frame[1] == 0x11   # TGT (ECU)
        assert frame[2] == 0xF1   # SRC (tester)
        assert frame[3:5] == payload
        expected_cs = (0x82 + 0x11 + 0xF1 + 0x10 + 0x81) & 0xFF
        assert frame[-1] == expected_cs
        assert len(frame) == 3 + len(payload) + 1  # header + payload + cs

    def test_build_frame_long_payload(self) -> None:
        payload = bytes([0x5A] + [i & 0xFF for i in range(79)])  # 80 bytes
        frame = _build_frame(payload, ecu_address=0x11, tester_address=0xF1)
        # FMT low 6 bits = 0 → explicit LEN byte, high 2 bits = 0b10
        assert frame[0] == 0b10_000000
        assert frame[1] == 0x11
        assert frame[2] == 0xF1
        assert frame[3] == 80  # LEN byte
        assert frame[4 : 4 + len(payload)] == payload
        expected_cs = sum(frame[:-1]) & 0xFF
        assert frame[-1] == expected_cs
        assert len(frame) == 4 + len(payload) + 1

    def test_build_frame_functional_addressing(self) -> None:
        payload = bytes([0x10])
        frame = _build_frame(
            payload, ecu_address=0x33, tester_address=0xF1, functional=True
        )
        # FMT high 2 bits = 0b11 (functional)
        assert (frame[0] >> 6) & 0b11 == 0b11

    def test_build_frame_payload_too_long(self) -> None:
        with pytest.raises(ProtocolError) as excinfo:
            _build_frame(b"\x10" * 256, ecu_address=0x11, tester_address=0xF1)
        assert "too long" in str(excinfo.value).lower()

    def test_build_frame_empty_payload(self) -> None:
        with pytest.raises(ProtocolError):
            _build_frame(b"", ecu_address=0x11, tester_address=0xF1)

    def test_parse_frame_valid(self) -> None:
        payload = bytes([0x50, 0x81])
        frame = _build_frame(payload, ecu_address=0xF1, tester_address=0x11)
        parsed = _parse_frame(frame)
        assert parsed == payload

    def test_parse_frame_long_payload(self) -> None:
        payload = bytes([0x5A] + list(range(80)))
        frame = _build_frame(payload, ecu_address=0xF1, tester_address=0x11)
        parsed = _parse_frame(frame)
        assert parsed == payload

    def test_parse_frame_bad_checksum(self) -> None:
        payload = bytes([0x50, 0x81])
        frame = bytearray(_build_frame(payload, ecu_address=0xF1, tester_address=0x11))
        frame[-1] = (frame[-1] ^ 0xFF) & 0xFF  # corrupt checksum
        with pytest.raises(ProtocolError) as excinfo:
            _parse_frame(bytes(frame))
        assert "checksum" in str(excinfo.value).lower()

    def test_parse_frame_length_mismatch(self) -> None:
        # Claim length 5 via FMT = 0x85, but supply only 2 payload bytes
        frame = bytes([0x85, 0xF1, 0x11, 0x50, 0x81, 0x00])  # too short
        with pytest.raises(ProtocolError) as excinfo:
            _parse_frame(frame)
        assert "length mismatch" in str(excinfo.value).lower()

    def test_parse_frame_too_short(self) -> None:
        with pytest.raises(ProtocolError):
            _parse_frame(b"\x00\x00")


# ---------------------------------------------------------------------------
# TestEchoCancellation
# ---------------------------------------------------------------------------


class TestEchoCancellation:
    def test_echo_matches_sent(self, fake_serial_factory) -> None:
        """Local echo that matches TX must be drained without error."""
        adapter, fake = _build_successful_adapter(
            fake_serial_factory, init_mode="slow"
        )
        # Build a request payload and stage matching echo + a valid
        # ECU response.
        request_payload = bytes([SID_ECU_RESET, 0x01])
        request_frame = _build_frame(
            payload=request_payload,
            ecu_address=adapter.ecu_address,
            tester_address=adapter.tester_address,
        )
        response_frame = _build_frame(
            payload=bytes([SID_ECU_RESET + POSITIVE_RESPONSE_OFFSET, 0x01]),
            ecu_address=adapter.tester_address,
            tester_address=adapter.ecu_address,
        )
        fake.queue_response(request_frame + response_frame)
        # Should NOT raise
        adapter.reset_ecu()

    def test_echo_mismatch_raises(self, fake_serial_factory) -> None:
        """Local echo that differs from TX must raise a wiring-hint error."""
        adapter, fake = _build_successful_adapter(
            fake_serial_factory, init_mode="slow"
        )
        # Queue corrupted echo (flip one bit) before the response.
        request_payload = bytes([SID_ECU_RESET, 0x01])
        request_frame = _build_frame(
            payload=request_payload,
            ecu_address=adapter.ecu_address,
            tester_address=adapter.tester_address,
        )
        corrupted_echo = bytes(
            [request_frame[0] ^ 0xFF]
        ) + request_frame[1:]
        fake.queue_response(corrupted_echo)

        with pytest.raises(ProtocolError) as excinfo:
            adapter.reset_ecu()
        assert "echo mismatch" in str(excinfo.value).lower()

    def test_echo_short_read_raises(self, fake_serial_factory) -> None:
        """If echo bytes are fewer than sent, drain must raise ProtocolError."""
        adapter, fake = _build_successful_adapter(
            fake_serial_factory, init_mode="slow"
        )
        # Queue only 2 bytes of echo (real frame is 6+).
        fake.queue_response(b"\x82\x11")
        with pytest.raises(ProtocolError) as excinfo:
            adapter.reset_ecu()
        # Either a short/mismatched echo or a downstream timeout; both
        # are surfaced as ProtocolError with a helpful string.
        msg = str(excinfo.value).lower()
        assert "echo" in msg or "timeout" in msg


# ---------------------------------------------------------------------------
# TestServiceMethods
# ---------------------------------------------------------------------------


def _queue_service_exchange(
    fake: ScriptedSerial,
    adapter: KLineAdapter,
    request_payload: bytes,
    response_payload: bytes,
) -> None:
    """Queue a full request-echo + ECU-response exchange on the fake serial."""
    request_frame = _build_frame(
        payload=request_payload,
        ecu_address=adapter.ecu_address,
        tester_address=adapter.tester_address,
    )
    response_frame = _build_frame(
        payload=response_payload,
        ecu_address=adapter.tester_address,
        tester_address=adapter.ecu_address,
    )
    fake.queue_response(request_frame + response_frame)


class TestServiceMethods:
    def test_read_dtcs_parses_two_codes(self, fake_serial_factory) -> None:
        adapter, fake = _build_successful_adapter(
            fake_serial_factory, init_mode="slow"
        )
        # Response payload: [0x58, num, high1, low1, status1, high2, low2, status2]
        # DTC 1: 0x01 0x11 → P + decade=0 + digit1=1 + digit2=1 + digit3=1 = "P0111"
        # DTC 2: 0x02 0x01 → P + decade=0 + digit1=2 + digit2=0 + digit3=1 = "P0201"
        response = bytes([
            SID_READ_DTC_BY_STATUS + POSITIVE_RESPONSE_OFFSET,
            2,
            0x01, 0x11, 0x21,
            0x02, 0x01, 0x21,
        ])
        _queue_service_exchange(
            fake, adapter,
            request_payload=bytes([SID_READ_DTC_BY_STATUS, 0x00, 0xFF]),
            response_payload=response,
        )
        dtcs = adapter.read_dtcs()
        assert dtcs == ["P0111", "P0201"]

    def test_read_dtcs_empty_list(self, fake_serial_factory) -> None:
        adapter, fake = _build_successful_adapter(
            fake_serial_factory, init_mode="slow"
        )
        response = bytes([SID_READ_DTC_BY_STATUS + POSITIVE_RESPONSE_OFFSET, 0])
        _queue_service_exchange(
            fake, adapter,
            request_payload=bytes([SID_READ_DTC_BY_STATUS, 0x00, 0xFF]),
            response_payload=response,
        )
        assert adapter.read_dtcs() == []

    def test_read_dtcs_negative_response(self, fake_serial_factory) -> None:
        adapter, fake = _build_successful_adapter(
            fake_serial_factory, init_mode="slow"
        )
        # Negative response: 0x7F <requested SID> <NRC>
        response = bytes([NEGATIVE_RESPONSE_SID, SID_READ_DTC_BY_STATUS, 0x11])
        _queue_service_exchange(
            fake, adapter,
            request_payload=bytes([SID_READ_DTC_BY_STATUS, 0x00, 0xFF]),
            response_payload=response,
        )
        with pytest.raises(ProtocolError) as excinfo:
            adapter.read_dtcs()
        msg = str(excinfo.value)
        assert "negative response" in msg.lower()
        assert "0x18" in msg
        assert "0x11" in msg

    def test_clear_dtcs_success(self, fake_serial_factory) -> None:
        adapter, fake = _build_successful_adapter(
            fake_serial_factory, init_mode="slow"
        )
        response = bytes([SID_CLEAR_DIAGNOSTIC_INFO + POSITIVE_RESPONSE_OFFSET])
        _queue_service_exchange(
            fake, adapter,
            request_payload=bytes([SID_CLEAR_DIAGNOSTIC_INFO, 0xFF, 0x00]),
            response_payload=response,
        )
        assert adapter.clear_dtcs() is True

    def test_reset_ecu_success(self, fake_serial_factory) -> None:
        adapter, fake = _build_successful_adapter(
            fake_serial_factory, init_mode="slow"
        )
        response = bytes([SID_ECU_RESET + POSITIVE_RESPONSE_OFFSET, 0x01])
        _queue_service_exchange(
            fake, adapter,
            request_payload=bytes([SID_ECU_RESET, 0x01]),
            response_payload=response,
        )
        # Should not raise
        adapter.reset_ecu()

    def test_read_ecu_id_parses_block(self, fake_serial_factory) -> None:
        adapter, fake = _build_successful_adapter(
            fake_serial_factory, init_mode="slow"
        )
        # 0x5A 0x9B + 20 bytes of ASCII identification
        ident_block = b"HONDA-ECM-V1.23-0001"
        response = bytes([
            SID_READ_ECU_IDENTIFICATION + POSITIVE_RESPONSE_OFFSET,
            0x9B,
        ]) + ident_block
        _queue_service_exchange(
            fake, adapter,
            request_payload=bytes([SID_READ_ECU_IDENTIFICATION, 0x9B]),
            response_payload=response,
        )
        result = adapter.read_ecu_id()
        assert result["identifier"] == "0x9b"
        assert result["raw_hex"] == ident_block.hex()
        assert "HONDA-ECM" in result["ascii"]

    def test_read_vin_parses_ascii(self, fake_serial_factory) -> None:
        adapter, fake = _build_successful_adapter(
            fake_serial_factory, init_mode="slow"
        )
        vin = "1HGCM82633A004352"  # Honda VIN (17 chars)
        response = bytes([
            SID_READ_ECU_IDENTIFICATION + POSITIVE_RESPONSE_OFFSET,
            0x90,
        ]) + vin.encode("ascii")
        _queue_service_exchange(
            fake, adapter,
            request_payload=bytes([SID_READ_ECU_IDENTIFICATION, 0x90]),
            response_payload=response,
        )
        assert adapter.read_vin() == vin

    def test_read_pid_returns_none(self, fake_serial_factory) -> None:
        """KWP2000 has no universal Mode 01 PID mapping; read_pid returns None."""
        adapter, _ = _build_successful_adapter(
            fake_serial_factory, init_mode="slow"
        )
        assert adapter.read_pid(0x0C) is None

    def test_send_command_disconnected_raises(self) -> None:
        adapter = KLineAdapter(port="COM_FAKE")
        with pytest.raises(ProtocolError):
            adapter.send_command(bytes([SID_ECU_RESET, 0x01]))


# ---------------------------------------------------------------------------
# TestDefensive
# ---------------------------------------------------------------------------


class TestDefensive:
    def test_invalid_init_mode_raises(self) -> None:
        with pytest.raises(ValueError):
            KLineAdapter(port="COM_FAKE", init_mode="medium")  # type: ignore[arg-type]

    def test_invalid_ecu_address_raises(self) -> None:
        with pytest.raises(ValueError):
            KLineAdapter(port="COM_FAKE", ecu_address=0x1FF)

    def test_invalid_read_timeout_raises(self) -> None:
        with pytest.raises(ValueError):
            KLineAdapter(port="COM_FAKE", read_timeout=0)

    def test_disconnect_when_never_connected(self) -> None:
        adapter = KLineAdapter(port="COM_FAKE")
        # Must not raise; must be a clean no-op.
        adapter.disconnect()
        assert adapter.is_connected is False

    def test_disconnect_suppresses_stopsession_failure(
        self, fake_serial_factory
    ) -> None:
        adapter, fake = _build_successful_adapter(
            fake_serial_factory, init_mode="slow"
        )
        # StopSession expects a framed response; we queue nothing, so
        # the adapter's _receive_framed will raise, but disconnect
        # must swallow it.
        fake.clear_rx()
        adapter.disconnect()
        assert adapter.is_connected is False
        assert fake.closed is True

    def test_connect_idempotent(self, fake_serial_factory) -> None:
        adapter, _ = _build_successful_adapter(
            fake_serial_factory, init_mode="slow"
        )
        # Second connect should short-circuit without error and without
        # doing anything with the (exhausted) fake serial.
        adapter.connect()
        assert adapter.is_connected is True

    def test_connect_without_port_raises(self) -> None:
        adapter = KLineAdapter()  # no port
        with pytest.raises(ProtocolError):
            adapter.connect()

    def test_pyserial_missing_raises_protocol_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If pyserial is not importable, connect raises a friendly error."""
        import builtins
        import sys

        # Evict any cached ``serial`` so our fake import hits the ImportError.
        monkeypatch.setitem(sys.modules, "serial", None)

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "serial":
                raise ImportError("No module named 'serial'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        adapter = KLineAdapter(port="COM_FAKE")
        with pytest.raises(ProtocolError) as excinfo:
            adapter.connect()
        assert "pyserial" in str(excinfo.value).lower()
        assert "motodiag[hardware]" in str(excinfo.value)

    def test_get_protocol_name(self) -> None:
        adapter = KLineAdapter(port="COM_FAKE")
        assert "KWP2000" in adapter.get_protocol_name()
        assert "14230" in adapter.get_protocol_name()


# ---------------------------------------------------------------------------
# TestConstants — pin the ISO 14230-3 service IDs and the timing envelope.
# ---------------------------------------------------------------------------


class TestConstants:
    def test_kwp_service_ids_are_iso_14230_3(self) -> None:
        assert SID_START_DIAGNOSTIC_SESSION == 0x10
        assert SID_ECU_RESET == 0x11
        assert SID_CLEAR_DIAGNOSTIC_INFO == 0x14
        assert SID_READ_DTC_BY_STATUS == 0x18
        assert SID_READ_ECU_IDENTIFICATION == 0x1A
        assert POSITIVE_RESPONSE_OFFSET == 0x40
        assert NEGATIVE_RESPONSE_SID == 0x7F

    def test_timing_constants_within_iso_14230_2_envelope(self) -> None:
        assert P1_MAX <= 20
        assert P2_MIN >= 25
        assert P2_MAX <= 50
        assert W1_MAX <= 300
        assert W2_MAX <= 20
        assert W3_MAX <= 20
        assert W4 >= 25 - 5  # 25 ms nominal, allow ±5 ms
        assert W5_MIN >= 300
        assert FAST_INIT_TINIL >= 25 - 5
        assert FAST_INIT_TWUP >= 50 - 5

    def test_decode_kwp_dtc_p_code(self) -> None:
        assert _decode_kwp_dtc(0x01, 0x11) == "P0111"

    def test_decode_kwp_dtc_b_code(self) -> None:
        # Domain bits 0b10 = 'B', decade 0, digits 2, 3, 4 → "B0234"
        high = (0b10 << 6) | (0b00 << 4) | 0x02
        low = 0x34
        assert _decode_kwp_dtc(high, low) == "B0234"

    def test_decode_kwp_dtc_u_code(self) -> None:
        # Domain bits 0b11 = 'U', decade 0, digits 1, 0, 0 → "U0100"
        high = (0b11 << 6) | (0b00 << 4) | 0x01
        low = 0x00
        assert _decode_kwp_dtc(high, low) == "U0100"
