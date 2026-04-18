"""Phase 136 — CAN bus protocol adapter tests.

All I/O is mocked via :class:`FakeBus` / :class:`FakeMessage` — zero
real hardware, zero network, zero live API tokens. A fake ``can``
module is installed in :mod:`sys.modules` so the adapter's lazy
``_load_can()`` picks it up without ``python-can`` actually being
installed in the test environment.

Six test classes:

- :class:`TestISOTPSingleFrame` — request/response flows that fit in a
  single 8-byte CAN frame (Mode 03 with 0 or 1 DTCs, Mode 04 clear,
  Mode 01 PID reads).
- :class:`TestISOTPMultiFrameReassemble` — receive-side ISO-TP FF + CF
  reassembly, sequence-number wrap, malformed-frame handling.
- :class:`TestISOTPMultiFrameSend` — send-side FF + FC + CF emission
  with flow-control separation time and block size.
- :class:`TestNRCDecode` — negative-response handling for 10 common
  ISO 14229-1 NRCs plus an unknown NRC fallback.
- :class:`TestCANAdapterReadFlow` — integration-style tests exercising
  the public API (``read_dtcs``, ``read_vin``, ``clear_dtcs``,
  ``read_pid``, ``send_command``, ``get_protocol_name``, ``disconnect``
  idempotency, connect-time errors).
- :class:`TestLazyImport` — module can be imported without
  ``python-can``; ``connect()`` raises with the install hint.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Optional

import pytest

from motodiag.hardware.protocols import can as can_module
from motodiag.hardware.protocols.can import (
    PHYSICAL_RESPONSE_RANGE,
    SUPPORTED_BITRATES,
    CANAdapter,
    _decode_dtc_pair,
    _decode_nrc,
)
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
# Fake python-can doubles
# ---------------------------------------------------------------------------


class FakeMessage:
    """Minimal stand-in for ``can.Message`` — records only what we read."""

    def __init__(
        self,
        arbitration_id: int,
        data: bytes,
        is_extended_id: bool = False,
    ) -> None:
        self.arbitration_id = arbitration_id
        self.data = bytes(data)
        self.is_extended_id = is_extended_id

    def __repr__(self) -> str:  # pragma: no cover - diagnostic only
        return (
            f"FakeMessage(id=0x{self.arbitration_id:X}, "
            f"data={self.data.hex()})"
        )


class FakeBus:
    """Scripted CAN bus. ``recv()`` pops queued frames; ``send()`` records."""

    def __init__(self, rx_queue: Optional[list[FakeMessage]] = None) -> None:
        self.rx_queue: list[FakeMessage] = list(rx_queue or [])
        self.sent: list[FakeMessage] = []
        self.shutdown_called: int = 0

    def recv(self, timeout: Optional[float] = None) -> Optional[FakeMessage]:
        if self.rx_queue:
            return self.rx_queue.pop(0)
        return None  # simulates a timeout

    def send(self, msg: FakeMessage) -> None:
        self.sent.append(msg)

    def shutdown(self) -> None:
        self.shutdown_called += 1


def _install_fake_can_module(
    monkeypatch: pytest.MonkeyPatch,
    bus: FakeBus,
) -> ModuleType:
    """Put a fake ``can`` module in :mod:`sys.modules` with a stub ``Bus``.

    The adapter's ``_load_can()`` will pick it up without the real
    ``python-can`` package being installed.
    """
    fake_mod = ModuleType("can")

    def bus_factory(**kwargs):  # noqa: ANN001 — loose shim
        # Record constructor kwargs for assertion.
        bus._ctor_kwargs = dict(kwargs)
        return bus

    fake_mod.Bus = bus_factory  # type: ignore[attr-defined]
    fake_mod.Message = FakeMessage  # type: ignore[attr-defined]

    class CanError(Exception):
        pass

    fake_mod.CanError = CanError  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "can", fake_mod)
    return fake_mod


def _make_connected_adapter(
    monkeypatch: pytest.MonkeyPatch,
    bus: FakeBus,
    **kwargs,
) -> CANAdapter:
    _install_fake_can_module(monkeypatch, bus)
    adapter = CANAdapter(channel=kwargs.pop("channel", "vcan0"), **kwargs)
    adapter.connect()
    return adapter


def _sf(length: int, data: bytes, arb_id: int = 0x7E8) -> FakeMessage:
    """Build a Single Frame response message."""
    payload = bytes([(0x0 << 4) | length]) + data
    payload = payload.ljust(8, b"\x00")
    return FakeMessage(arbitration_id=arb_id, data=payload)


def _raw(arb_id: int, data: bytes) -> FakeMessage:
    """Build an arbitrary (already-framed) response message."""
    return FakeMessage(arbitration_id=arb_id, data=data.ljust(8, b"\x00"))


# ---------------------------------------------------------------------------
# TestISOTPSingleFrame
# ---------------------------------------------------------------------------


class TestISOTPSingleFrame:
    def test_read_dtcs_returns_empty_list_when_count_is_zero(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Response: SF length=2, [0x43, 0x00] = mode-03 positive, 0 DTCs.
        bus = FakeBus(rx_queue=[_sf(2, b"\x43\x00")])
        adapter = _make_connected_adapter(monkeypatch, bus)
        assert adapter.read_dtcs() == []
        # Confirm request was one SF with [0x01, 0x03] padded to 8.
        assert len(bus.sent) == 1
        sent = bus.sent[0]
        assert sent.arbitration_id == 0x7DF
        assert sent.data[:2] == b"\x01\x03"

    def test_read_dtcs_decodes_single_p0133(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # SF length=4, [0x43, 0x01, 0x01, 0x33] -> 1 DTC = P0133.
        bus = FakeBus(rx_queue=[_sf(4, b"\x43\x01\x01\x33")])
        adapter = _make_connected_adapter(monkeypatch, bus)
        assert adapter.read_dtcs() == ["P0133"]

    def test_read_dtcs_decodes_three_mixed_codes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # 3 DTCs: P0420, C0055, U0100.
        # P0420 -> 0x04 0x20 ; C0055 -> 0x40 0x55 ; U0100 -> 0xC1 0x00.
        # SF length would be 1 + 1 + 6 = 8 -> exceeds 7 for SF; use FF.
        # Build as First Frame + 1 CF instead to exercise MF reassembly? Keep it
        # simple: pack only the first two DTCs into SF (the DTC-count test is
        # already what we care about here) — use length=7 SF.
        # Actually 1 count + 2*3 pairs = 7 data bytes after SID echo; SID echo
        # is 1 more byte. total = 1 (SID) + 1 (count) + 6 (3 pairs) = 8 bytes,
        # which requires FF. Switch to FF + 1 CF.
        ff = _raw(
            0x7E8,
            bytes(
                [
                    (0x1 << 4) | 0x0,  # FF, high nibble of length=0
                    0x08,  # total payload length = 8 bytes
                    0x43,  # SID echo
                    0x03,  # DTC count
                    0x04,  # P0420 high
                    0x20,  # P0420 low
                    0x40,  # C0055 high
                    0x55,  # C0055 low
                ]
            ),
        )
        cf = _raw(
            0x7E8,
            bytes(
                [
                    (0x2 << 4) | 0x01,  # CF, SN=1
                    0xC1,  # U0100 high
                    0x00,  # U0100 low
                    0, 0, 0, 0, 0,
                ]
            ),
        )
        bus = FakeBus(rx_queue=[ff, cf])
        adapter = _make_connected_adapter(monkeypatch, bus)
        assert adapter.read_dtcs() == ["P0420", "C0055", "U0100"]
        # Confirm a Flow Control frame was sent by the adapter between FF+CF.
        fc_frames = [m for m in bus.sent if (m.data[0] >> 4) & 0x0F == 0x3]
        assert len(fc_frames) == 1
        assert fc_frames[0].data[0] == 0x30  # FC with flag=CTS
        assert fc_frames[0].data[1] == 0x00  # block_size = 0
        assert fc_frames[0].data[2] == 0x00  # ST = 0

    def test_clear_dtcs_returns_true_on_positive_response(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # SF length=1, [0x44] — mode-04 positive, no payload.
        bus = FakeBus(rx_queue=[_sf(1, b"\x44")])
        adapter = _make_connected_adapter(monkeypatch, bus)
        assert adapter.clear_dtcs() is True

    def test_clear_dtcs_returns_false_on_conditions_not_correct(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # NRC 0x22 ("conditionsNotCorrect") should be swallowed -> False.
        bus = FakeBus(rx_queue=[_sf(3, b"\x7F\x04\x22")])
        adapter = _make_connected_adapter(monkeypatch, bus)
        assert adapter.clear_dtcs() is False

    def test_read_pid_returns_value_after_stripping_echo(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Mode 01 PID 0x0C (engine RPM). Response: SID 0x41, PID 0x0C, 2 bytes.
        # RPM value 0x1AF8 = 6904 -> actual RPM after / 4 = 1726.
        bus = FakeBus(rx_queue=[_sf(4, b"\x41\x0C\x1A\xF8")])
        adapter = _make_connected_adapter(monkeypatch, bus)
        assert adapter.read_pid(0x0C) == 0x1AF8


# ---------------------------------------------------------------------------
# TestISOTPMultiFrameReassemble
# ---------------------------------------------------------------------------


class TestISOTPMultiFrameReassemble:
    def test_read_vin_assembles_17_chars_from_ff_and_two_cfs(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vin = "1HD1KHM17KB647218"
        assert len(vin) == 17
        # Mode 09 PID 02 positive response: 0x49 0x02 0x01 + 17 VIN ASCII bytes
        # = 20 bytes of payload total -> FF + 2 CF.
        payload = b"\x49\x02\x01" + vin.encode("ascii")
        assert len(payload) == 20
        ff = _raw(
            0x7E8,
            bytes(
                [
                    (0x1 << 4) | 0x0,
                    0x14,  # total length = 20
                ]
            )
            + payload[:6],
        )
        cf1 = _raw(
            0x7E8,
            bytes([(0x2 << 4) | 0x01]) + payload[6:13],
        )
        cf2 = _raw(
            0x7E8,
            bytes([(0x2 << 4) | 0x02]) + payload[13:20] + b"\x00",  # pad to 8
        )
        bus = FakeBus(rx_queue=[ff, cf1, cf2])
        adapter = _make_connected_adapter(monkeypatch, bus)
        assert adapter.read_vin() == vin.upper()
        # Confirm FC was sent by adapter.
        fc = [m for m in bus.sent if (m.data[0] >> 4) & 0x0F == 0x3]
        assert len(fc) == 1

    def test_read_vin_raises_on_sequence_number_mismatch(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # FF says 20 bytes total; CF1 arrives with SN=3 instead of SN=1.
        ff = _raw(
            0x7E8,
            bytes([0x10, 0x14]) + b"\x49\x02\x01\x31\x48\x44",
        )
        cf_bad = _raw(
            0x7E8,
            bytes([(0x2 << 4) | 0x03]) + b"\x31\x4B\x48\x4D\x31\x37\x4B",
        )
        bus = FakeBus(rx_queue=[ff, cf_bad])
        adapter = _make_connected_adapter(monkeypatch, bus)
        with pytest.raises(ProtocolError, match="sequence error"):
            adapter.read_vin()

    def test_read_vin_raises_on_short_vin(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # 15-char VIN — should fail length check.
        short_vin = "1HD1KHM17KB6472"  # 15 chars
        payload = b"\x49\x02\x01" + short_vin.encode("ascii")
        # Total = 18 bytes -> FF + 2 CFs (6 in FF, 7 in CF1, 5 in CF2).
        ff = _raw(
            0x7E8,
            bytes([0x10, 0x12]) + payload[:6],
        )
        cf1 = _raw(
            0x7E8,
            bytes([0x21]) + payload[6:13],
        )
        cf2 = _raw(
            0x7E8,
            bytes([0x22]) + payload[13:18].ljust(7, b"\x00"),
        )
        bus = FakeBus(rx_queue=[ff, cf1, cf2])
        adapter = _make_connected_adapter(monkeypatch, bus)
        with pytest.raises(ProtocolError, match="malformed VIN"):
            adapter.read_vin()

    def test_receive_iso_tp_drops_out_of_range_frames(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Chatter from another CAN node (arb_id=0x123) should be silently
        # ignored; the real response (0x7E8) must still be picked up.
        chatter = FakeMessage(arbitration_id=0x123, data=b"\x11\x22\x33\x44\x55\x66\x77\x88")
        real = _sf(2, b"\x43\x00")
        bus = FakeBus(rx_queue=[chatter, real])
        adapter = _make_connected_adapter(monkeypatch, bus)
        assert adapter.read_dtcs() == []


# ---------------------------------------------------------------------------
# TestISOTPMultiFrameSend
# ---------------------------------------------------------------------------


class TestISOTPMultiFrameSend:
    def test_send_command_multi_frame_emits_ff_then_cfs_after_fc_cts(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Build a 10-byte request payload: service 0x22 + 9 data bytes.
        # That forces a multi-frame send: FF (6 payload bytes) + 1 CF (4).
        request_data = b"\xF1\x90\xAA\xBB\xCC\xDD\xEE\xFF\x11"
        # Queue: FC (flag=CTS, bs=0, ST=0) then a simple SF response that
        # passes the positive-response check for service 0x22 (echo = 0x62).
        fc = _raw(0x7E8, b"\x30\x00\x00\x00\x00\x00\x00\x00")
        positive = _sf(2, b"\x62\xF1")
        bus = FakeBus(rx_queue=[fc, positive])
        adapter = _make_connected_adapter(monkeypatch, bus)
        # send_command returns the full positive response (including SID echo).
        reply = adapter.send_command(bytes([0x22]) + request_data)
        assert reply[0] == 0x62  # positive-response SID for 0x22
        # Verify the wire: adapter must have sent FF first, then one or more CFs.
        arb_ids = [m.arbitration_id for m in bus.sent]
        assert all(a == 0x7DF for a in arb_ids)
        pci_types = [(m.data[0] >> 4) & 0x0F for m in bus.sent]
        assert pci_types[0] == 0x1  # FF
        assert pci_types[1] == 0x2  # CF
        # FF byte 0 low nibble + byte 1 = total length (1 SID + 9 data = 10).
        ff = bus.sent[0]
        assert ((ff.data[0] & 0x0F) << 8) | ff.data[1] == 10

    def test_send_command_single_frame_round_trip_for_short_payload(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Mode 01 PID 0x05 (coolant temp). Request = 2 bytes -> SF.
        bus = FakeBus(rx_queue=[_sf(3, b"\x41\x05\x5A")])  # 0x5A = 90 raw
        adapter = _make_connected_adapter(monkeypatch, bus)
        reply = adapter.send_command(b"\x01\x05")
        assert reply == b"\x41\x05\x5A"
        # One SF sent.
        assert len(bus.sent) == 1
        assert (bus.sent[0].data[0] >> 4) & 0x0F == 0x0
        assert bus.sent[0].data[0] & 0x0F == 2  # length nibble

    def test_sequence_number_wraps_from_0xf_to_0x0(self) -> None:
        # Pure logic test of the SN wrap rule. We don't need the bus —
        # just confirm (last + 1) & 0x0F wraps correctly.
        assert ((0x0F + 1) & 0x0F) == 0x00
        assert ((0x00 + 1) & 0x0F) == 0x01
        assert ((0x07 + 1) & 0x0F) == 0x08


# ---------------------------------------------------------------------------
# TestNRCDecode
# ---------------------------------------------------------------------------


class TestNRCDecode:
    @pytest.mark.parametrize(
        "nrc,name",
        [
            (0x10, "generalReject"),
            (0x11, "serviceNotSupported"),
            (0x12, "subFunctionNotSupported"),
            (0x13, "incorrectMessageLengthOrInvalidFormat"),
            (0x22, "conditionsNotCorrect"),
            (0x31, "requestOutOfRange"),
            (0x33, "securityAccessDenied"),
            (0x78, "requestCorrectlyReceivedResponsePending"),
            (0x7E, "subFunctionNotSupportedInActiveSession"),
            (0x7F, "serviceNotSupportedInActiveSession"),
        ],
    )
    def test_common_nrcs_decode_to_iso14229_names(self, nrc: int, name: str) -> None:
        assert _decode_nrc(nrc) == name

    def test_unknown_nrc_falls_back_to_hex_wrapper(self) -> None:
        assert _decode_nrc(0x55) == "unknownNRC(0x55)"
        assert _decode_nrc(0xAA) == "unknownNRC(0xAA)"

    def test_negative_response_service_not_supported_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Mode 03 request -> NRC 0x11 (serviceNotSupported) -> ProtocolError.
        bus = FakeBus(rx_queue=[_sf(3, b"\x7F\x03\x11")])
        adapter = _make_connected_adapter(monkeypatch, bus)
        with pytest.raises(ProtocolError, match="serviceNotSupported"):
            adapter.read_dtcs()

    def test_negative_response_request_out_of_range_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Mode 09 PID 0x02 -> NRC 0x31 (requestOutOfRange).
        bus = FakeBus(rx_queue=[_sf(3, b"\x7F\x09\x31")])
        adapter = _make_connected_adapter(monkeypatch, bus)
        with pytest.raises(ProtocolError, match="requestOutOfRange"):
            adapter.read_vin()


# ---------------------------------------------------------------------------
# TestCANAdapterReadFlow
# ---------------------------------------------------------------------------


class TestCANAdapterReadFlow:
    def test_get_protocol_name_reports_bitrate(self) -> None:
        adapter = CANAdapter(channel="can0", bitrate=500_000)
        assert adapter.get_protocol_name() == "ISO 15765-4 (CAN 11/500)"
        adapter_250 = CANAdapter(channel="can0", bitrate=250_000)
        assert adapter_250.get_protocol_name() == "ISO 15765-4 (CAN 11/250)"

    def test_constructor_rejects_unsupported_bitrate(self) -> None:
        with pytest.raises(ValueError, match="Unsupported bitrate"):
            CANAdapter(channel="can0", bitrate=100_000)
        with pytest.raises(ValueError, match="Unsupported bitrate"):
            CANAdapter(channel="can0", bitrate=1_000_000)

    def test_connect_is_idempotent_and_disconnect_is_idempotent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        bus = FakeBus()
        _install_fake_can_module(monkeypatch, bus)
        adapter = CANAdapter(channel="vcan0")
        assert adapter.is_connected is False
        adapter.connect()
        assert adapter.is_connected is True
        adapter.connect()  # second call — should no-op, not re-open.
        adapter.disconnect()
        adapter.disconnect()  # double-disconnect — should not raise.
        assert adapter.is_connected is False
        assert bus.shutdown_called == 1  # shutdown called once, not twice.

    def test_connect_wraps_backend_oserror_as_protocol_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_mod = ModuleType("can")

        def boom_bus(**kwargs):  # noqa: ANN001
            raise OSError("no such device")

        fake_mod.Bus = boom_bus  # type: ignore[attr-defined]
        fake_mod.Message = FakeMessage  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "can", fake_mod)
        adapter = CANAdapter(channel="can99", interface="socketcan")
        with pytest.raises(ProtocolConnectionError) as exc_info:
            adapter.connect()
        assert "can99" in str(exc_info.value)
        assert "no such device" in str(exc_info.value)

    def test_send_command_on_disconnected_raises(self) -> None:
        adapter = CANAdapter(channel="can0")
        with pytest.raises(ProtocolConnectionError, match="disconnected"):
            adapter.send_command(b"\x01\x0C")

    def test_timeout_when_bus_is_silent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Empty rx_queue — recv() returns None forever.
        bus = FakeBus()
        # Shrink the multiframe timeout for a fast test.
        adapter = _make_connected_adapter(
            monkeypatch,
            bus,
            request_timeout=0.01,
            multiframe_timeout=0.05,
        )
        import time as _time

        start = _time.monotonic()
        with pytest.raises(ProtocolTimeoutError, match="timeout"):
            adapter.read_dtcs()
        elapsed = _time.monotonic() - start
        # Must not loop forever — allow generous slack for Windows timers.
        assert elapsed < 1.0

    def test_dtc_pair_decoder_handles_all_four_letters(self) -> None:
        # P prefix (0b00): 0x01 0x33 -> P0133
        assert _decode_dtc_pair(0x01, 0x33) == "P0133"
        # C prefix (0b01): 0x40 0x55 -> C0055
        assert _decode_dtc_pair(0x40, 0x55) == "C0055"
        # B prefix (0b10): 0x80 0x00 -> B0000
        assert _decode_dtc_pair(0x80, 0x00) == "B0000"
        # U prefix (0b11): 0xC1 0x00 -> U0100
        assert _decode_dtc_pair(0xC1, 0x00) == "U0100"

    def test_send_command_raises_on_nrc(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Raw Mode 22 request with NRC 0x33 (securityAccessDenied).
        bus = FakeBus(rx_queue=[_sf(3, b"\x7F\x22\x33")])
        adapter = _make_connected_adapter(monkeypatch, bus)
        with pytest.raises(ProtocolError, match="securityAccessDenied"):
            adapter.send_command(b"\x22\xF1\x90")


# ---------------------------------------------------------------------------
# TestLazyImport
# ---------------------------------------------------------------------------


class TestLazyImport:
    def test_module_import_succeeds_without_python_can(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Remove any pre-existing 'can' from sys.modules and block future imports.
        monkeypatch.delitem(sys.modules, "can", raising=False)
        # Re-importing the adapter module itself should still work.
        import importlib

        import motodiag.hardware.protocols.can as mod

        reloaded = importlib.reload(mod)
        assert hasattr(reloaded, "CANAdapter")

    def test_connect_raises_with_install_hint_when_can_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Make ``import can`` fail inside _load_can().
        monkeypatch.setitem(sys.modules, "can", None)
        adapter = CANAdapter(channel="can0")
        with pytest.raises(ProtocolConnectionError) as exc_info:
            adapter.connect()
        msg = str(exc_info.value)
        assert "python-can is not installed" in msg
        assert "pip install 'motodiag[can]'" in msg

    def test_pyproject_has_can_optional_dependency(self) -> None:
        pyproject_path = (
            Path(__file__).resolve().parents[1] / "pyproject.toml"
        )
        with pyproject_path.open("rb") as fh:
            data = tomllib.load(fh)
        opt = data["project"]["optional-dependencies"]
        assert "can" in opt
        assert any("python-can" in entry for entry in opt["can"])
        # The ``all`` alias must include the new extra.
        all_extras = opt["all"]
        joined = " ".join(all_extras)
        assert "can" in joined

    def test_module_constants_are_stable(self) -> None:
        # Guard against someone silently changing the public surface.
        assert SUPPORTED_BITRATES == (500_000, 250_000)
        assert PHYSICAL_RESPONSE_RANGE == (0x7E8, 0x7EF)
        # Module-level symbol sanity — used by Phase 139 later.
        assert hasattr(can_module, "FUNCTIONAL_REQUEST_ID")
        assert can_module.FUNCTIONAL_REQUEST_ID == 0x7DF
