"""Phase 139 — ECU auto-detection + handshake tests.

Seven test classes, ~25 tests, zero real serial I/O, zero live tokens.
All adapter classes are patched via :func:`unittest.mock.patch` at the
``motodiag.hardware.ecu_detect`` module level so constructor and
``connect()`` behavior are fully controlled by the tests.

Test classes
------------

- :class:`TestProtocolOrder` (6) — make-hint priority table correctness.
- :class:`TestDetectSuccess` (4) — each connect-order path.
- :class:`TestDetectFailure` (3) — :class:`NoECUDetectedError` behavior
  when every candidate fails (including a non-:class:`ProtocolError`).
- :class:`TestIdentifyEcuSuccess` (4) — happy path decode of all 4 fields
  and all 5 supported modes.
- :class:`TestIdentifyEcuPartialFailure` (4) — some reads fail, others
  succeed; partial results.
- :class:`TestAutoDetectorWiring` (3) — constructor defaults, hint
  normalization, timeout / baud passthrough.
- :class:`TestErrorClass` (1) — :class:`NoECUDetectedError` is catchable
  as :class:`ProtocolError`.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from motodiag.hardware.ecu_detect import (
    AutoDetector,
    NoECUDetectedError,
    PROTOCOL_CAN,
    PROTOCOL_ELM327,
    PROTOCOL_J1850,
    PROTOCOL_KLINE,
)
from motodiag.hardware.protocols.exceptions import (
    ConnectionError as ProtocolConnectionError,
    ProtocolError,
    TimeoutError as ProtocolTimeoutError,
)


# ---------------------------------------------------------------------------
# Helper: make a MagicMock that looks like a connected adapter.
# ---------------------------------------------------------------------------


def _make_adapter_mock(
    name: str,
    *,
    connect_raises: Exception | None = None,
) -> MagicMock:
    """Return a MagicMock that mimics a :class:`ProtocolAdapter`.

    If ``connect_raises`` is set, the mock's ``connect()`` method raises
    that exception; otherwise ``connect()`` returns ``None`` (success).
    The mock's class name (as seen by ``type(m).__name__``) is set to
    ``name`` via a dynamically-subclassed ``MagicMock``.
    """
    cls = type(name, (MagicMock,), {})
    instance = cls(spec=[
        "connect",
        "disconnect",
        "send_command",
        "send_request",
        "read_dtcs",
        "clear_dtcs",
        "read_pid",
        "read_vin",
        "get_protocol_name",
    ])
    if connect_raises is not None:
        instance.connect.side_effect = connect_raises
    else:
        instance.connect.return_value = None
    return instance


def _patch_adapter_factories(
    *,
    can_factory=None,
    kline_factory=None,
    j1850_factory=None,
    elm327_factory=None,
):
    """Return a context manager that patches all four adapter imports.

    :meth:`AutoDetector._build_adapter` imports each adapter class
    lazily from its home module. We patch the symbols at their source
    locations so the lazy import picks up the mock.
    """
    # Default no-ops raise an assertion error if a protocol is tried
    # without an explicit factory — tests that only exercise one path
    # should pass factories for exactly the protocols they expect to be
    # constructed.
    def _unexpected(name: str):
        def _raise(*args, **kwargs):
            raise AssertionError(
                f"{name} adapter unexpectedly constructed "
                f"(args={args}, kwargs={kwargs})"
            )
        return _raise

    can_factory = can_factory or _unexpected("CAN")
    kline_factory = kline_factory or _unexpected("KLine")
    j1850_factory = j1850_factory or _unexpected("J1850")
    elm327_factory = elm327_factory or _unexpected("ELM327")

    return _MultiPatch(
        can=can_factory,
        kline=kline_factory,
        j1850=j1850_factory,
        elm327=elm327_factory,
    )


class _MultiPatch:
    """Compose four :func:`patch` calls into a single context manager."""

    def __init__(self, *, can, kline, j1850, elm327) -> None:
        self._patches = [
            patch(
                "motodiag.hardware.protocols.can.CANAdapter",
                side_effect=can,
            ),
            patch(
                "motodiag.hardware.protocols.kline.KLineAdapter",
                side_effect=kline,
            ),
            patch(
                "motodiag.hardware.protocols.j1850.J1850Adapter",
                side_effect=j1850,
            ),
            patch(
                "motodiag.hardware.protocols.elm327.ELM327Adapter",
                side_effect=elm327,
            ),
        ]
        self._started: list = []

    def __enter__(self):
        for p in self._patches:
            p.start()
            self._started.append(p)
        return self

    def __exit__(self, exc_type, exc, tb):
        while self._started:
            self._started.pop().stop()
        return False


# ---------------------------------------------------------------------------
# TestProtocolOrder
# ---------------------------------------------------------------------------


class TestProtocolOrder:
    """Assert :meth:`_protocol_order_for_hint` returns the right sequence."""

    def _order(self, hint):
        det = AutoDetector(port="COM3", make_hint=hint)
        return det._protocol_order_for_hint(det.make_hint)

    def test_harley_priority(self):
        assert self._order("harley") == (
            PROTOCOL_J1850,
            PROTOCOL_CAN,
            PROTOCOL_ELM327,
        )

    @pytest.mark.parametrize(
        "make", ["honda", "yamaha", "kawasaki", "suzuki"]
    )
    def test_japanese_priority(self, make):
        assert self._order(make) == (
            PROTOCOL_KLINE,
            PROTOCOL_CAN,
            PROTOCOL_ELM327,
        )

    @pytest.mark.parametrize(
        "make", ["ducati", "bmw", "ktm", "triumph"]
    )
    def test_european_priority(self, make):
        assert self._order(make) == (
            PROTOCOL_CAN,
            PROTOCOL_KLINE,
            PROTOCOL_ELM327,
        )

    def test_none_priority_is_default_four(self):
        assert self._order(None) == (
            PROTOCOL_CAN,
            PROTOCOL_KLINE,
            PROTOCOL_J1850,
            PROTOCOL_ELM327,
        )

    def test_unknown_hint_falls_back_to_default(self):
        assert self._order("acme-motorcycles") == (
            PROTOCOL_CAN,
            PROTOCOL_KLINE,
            PROTOCOL_J1850,
            PROTOCOL_ELM327,
        )

    def test_hint_normalization_uppercase_and_whitespace(self):
        # "  HARLEY  " should normalize to "harley" and pick the Harley
        # priority list.
        det = AutoDetector(port="COM3", make_hint="  HARLEY  ")
        assert det.make_hint == "harley"
        assert det._protocol_order_for_hint(det.make_hint) == (
            PROTOCOL_J1850,
            PROTOCOL_CAN,
            PROTOCOL_ELM327,
        )


# ---------------------------------------------------------------------------
# TestDetectSuccess
# ---------------------------------------------------------------------------


class TestDetectSuccess:
    """Verify :meth:`detect` returns the first successfully-connected adapter."""

    def test_first_try_succeeds_no_others_attempted(self):
        can_mock = _make_adapter_mock("CANAdapter")

        with _patch_adapter_factories(
            can_factory=lambda **kw: can_mock,
            # Others unpatched → side-effect raises AssertionError if tried.
        ):
            det = AutoDetector(port="COM3")  # default order: CAN first
            adapter = det.detect()

        assert adapter is can_mock
        assert can_mock.connect.call_count == 1
        # disconnect() must NOT be called on a successful adapter.
        assert can_mock.disconnect.call_count == 0

    def test_second_try_succeeds_after_first_protocol_error(self):
        can_mock = _make_adapter_mock(
            "CANAdapter",
            connect_raises=ProtocolConnectionError("no response"),
        )
        kline_mock = _make_adapter_mock("KLineAdapter")

        # Default order: CAN → K-line → J1850 → ELM327
        with _patch_adapter_factories(
            can_factory=lambda **kw: can_mock,
            kline_factory=lambda **kw: kline_mock,
        ):
            det = AutoDetector(port="COM3")
            adapter = det.detect()

        assert adapter is kline_mock
        assert can_mock.connect.call_count == 1
        assert kline_mock.connect.call_count == 1

    def test_third_try_succeeds_after_two_failures(self):
        can_mock = _make_adapter_mock(
            "CANAdapter", connect_raises=ProtocolTimeoutError("timeout")
        )
        kline_mock = _make_adapter_mock(
            "KLineAdapter",
            connect_raises=ProtocolConnectionError("framing"),
        )
        j1850_mock = _make_adapter_mock("J1850Adapter")

        with _patch_adapter_factories(
            can_factory=lambda **kw: can_mock,
            kline_factory=lambda **kw: kline_mock,
            j1850_factory=lambda **kw: j1850_mock,
        ):
            det = AutoDetector(port="COM3")  # default order has J1850 third
            adapter = det.detect()

        assert adapter is j1850_mock
        assert can_mock.connect.call_count == 1
        assert kline_mock.connect.call_count == 1
        assert j1850_mock.connect.call_count == 1

    def test_fallback_elm327_succeeds_when_all_others_fail(self):
        can_mock = _make_adapter_mock(
            "CANAdapter", connect_raises=ProtocolError("bus off")
        )
        kline_mock = _make_adapter_mock(
            "KLineAdapter", connect_raises=ProtocolError("no wakeup")
        )
        j1850_mock = _make_adapter_mock(
            "J1850Adapter", connect_raises=ProtocolError("bridge refused")
        )
        elm_mock = _make_adapter_mock("ELM327Adapter")

        with _patch_adapter_factories(
            can_factory=lambda **kw: can_mock,
            kline_factory=lambda **kw: kline_mock,
            j1850_factory=lambda **kw: j1850_mock,
            elm327_factory=lambda **kw: elm_mock,
        ):
            det = AutoDetector(port="COM3")
            adapter = det.detect()

        assert adapter is elm_mock
        assert can_mock.connect.call_count == 1
        assert kline_mock.connect.call_count == 1
        assert j1850_mock.connect.call_count == 1
        assert elm_mock.connect.call_count == 1


# ---------------------------------------------------------------------------
# TestDetectFailure
# ---------------------------------------------------------------------------


class TestDetectFailure:
    """Verify :class:`NoECUDetectedError` behavior when every adapter fails."""

    def test_all_adapters_fail_raises_no_ecu_detected(self):
        can_mock = _make_adapter_mock(
            "CANAdapter", connect_raises=ProtocolError("can err")
        )
        kline_mock = _make_adapter_mock(
            "KLineAdapter", connect_raises=ProtocolError("kline err")
        )
        j1850_mock = _make_adapter_mock(
            "J1850Adapter", connect_raises=ProtocolError("j1850 err")
        )
        elm_mock = _make_adapter_mock(
            "ELM327Adapter", connect_raises=ProtocolError("elm err")
        )

        with _patch_adapter_factories(
            can_factory=lambda **kw: can_mock,
            kline_factory=lambda **kw: kline_mock,
            j1850_factory=lambda **kw: j1850_mock,
            elm327_factory=lambda **kw: elm_mock,
        ):
            det = AutoDetector(port="COM3")
            with pytest.raises(NoECUDetectedError) as excinfo:
                det.detect()

        assert len(excinfo.value.errors) == 4
        names = [name for name, _ in excinfo.value.errors]
        # Names are adapter class names (from MagicMock class).
        assert "CANAdapter" in names
        assert "KLineAdapter" in names
        assert "J1850Adapter" in names
        assert "ELM327Adapter" in names

    def test_non_protocol_error_does_not_abort_detection(self):
        # CAN raises OSError (a non-ProtocolError) on connect. The next
        # adapter should still be tried, and ELM327 ultimately succeeds.
        can_mock = _make_adapter_mock(
            "CANAdapter", connect_raises=OSError("serial port busy")
        )
        kline_mock = _make_adapter_mock(
            "KLineAdapter",
            connect_raises=ValueError("buggy adapter"),  # non-ProtocolError
        )
        j1850_mock = _make_adapter_mock(
            "J1850Adapter", connect_raises=ProtocolError("no bridge")
        )
        elm_mock = _make_adapter_mock("ELM327Adapter")

        with _patch_adapter_factories(
            can_factory=lambda **kw: can_mock,
            kline_factory=lambda **kw: kline_mock,
            j1850_factory=lambda **kw: j1850_mock,
            elm327_factory=lambda **kw: elm_mock,
        ):
            det = AutoDetector(port="COM3")
            adapter = det.detect()

        assert adapter is elm_mock
        assert can_mock.connect.call_count == 1
        assert kline_mock.connect.call_count == 1
        assert j1850_mock.connect.call_count == 1
        assert elm_mock.connect.call_count == 1

    def test_error_summary_contains_port_and_make_hint(self):
        can_mock = _make_adapter_mock(
            "CANAdapter", connect_raises=ProtocolError("no response")
        )
        kline_mock = _make_adapter_mock(
            "KLineAdapter", connect_raises=ProtocolError("no wakeup")
        )
        elm_mock = _make_adapter_mock(
            "ELM327Adapter", connect_raises=ProtocolError("no prompt")
        )

        with _patch_adapter_factories(
            can_factory=lambda **kw: can_mock,
            kline_factory=lambda **kw: kline_mock,
            elm327_factory=lambda **kw: elm_mock,
        ):
            det = AutoDetector(port="COM9", make_hint="honda")
            with pytest.raises(NoECUDetectedError) as excinfo:
                det.detect()

        msg = str(excinfo.value)
        assert "COM9" in msg
        assert "honda" in msg
        # Per-adapter summary lines must appear.
        assert "CANAdapter" in msg
        assert "KLineAdapter" in msg or "KLine" in msg


# ---------------------------------------------------------------------------
# TestIdentifyEcuSuccess
# ---------------------------------------------------------------------------


# Canonical test VIN (a real-format Harley VIN).
_TEST_VIN = "1HD1KHM14FB123456"


def _make_identify_adapter(
    *,
    vin: bytes | None = None,
    ecu_name: bytes | None = None,
    cal_id: bytes | None = None,
    sw_ver: bytes | None = None,
    supported_modes: list[int] | None = None,
) -> MagicMock:
    """Build a MagicMock adapter that scripts Mode 09 + mode-probe replies.

    ``send_request(mode, pid)`` is dispatched on ``(mode, pid)`` pairs:

    - ``(0x09, 0x02)`` → ``vin`` bytes (or raise ProtocolError if None).
    - ``(0x09, 0x0A)`` → ``ecu_name`` bytes (or raise if None).
    - ``(0x09, 0x04)`` → ``cal_id`` bytes (or raise if None).
    - ``(0x09, 0x08)`` → ``sw_ver`` bytes (or raise if None).
    - ``(mode, 0x00)`` for mode in ``[0x01, 0x02, 0x03, 0x04, 0x09]`` →
      ``b'\\x00'`` if ``mode in supported_modes``, else raise.

    Any other call raises :class:`ProtocolError`.
    """
    supported = set(supported_modes or [])

    def _send_request(*, mode: int, pid: int):
        if mode == 0x09 and pid == 0x02:
            if vin is None:
                raise ProtocolError("no data")
            return vin
        if mode == 0x09 and pid == 0x0A:
            if ecu_name is None:
                raise ProtocolError("no data")
            return ecu_name
        if mode == 0x09 and pid == 0x04:
            if cal_id is None:
                raise ProtocolError("no data")
            return cal_id
        if mode == 0x09 and pid == 0x08:
            if sw_ver is None:
                raise ProtocolError("no data")
            return sw_ver
        if pid == 0x00:  # mode-support probe
            if mode in supported:
                return b"\x00"
            raise ProtocolError("mode not supported")
        raise ProtocolError(f"unexpected request mode={mode:#x} pid={pid:#x}")

    adapter = MagicMock()
    adapter.send_request.side_effect = _send_request
    return adapter


class TestIdentifyEcuSuccess:
    """Happy-path identify_ecu — every read succeeds."""

    def test_all_four_fields_populated_plus_all_modes(self):
        adapter = _make_identify_adapter(
            vin=_TEST_VIN.encode("ascii"),
            ecu_name=b"ECM-1234   ",
            cal_id=b"CAL-5678",
            sw_ver=b"SW v2.1.0",
            supported_modes=[0x01, 0x02, 0x03, 0x04, 0x09],
        )

        det = AutoDetector(port="COM3")
        result = det.identify_ecu(adapter)

        assert result["vin"] == _TEST_VIN
        assert result["ecu_id"] == "ECM-1234"
        assert result["ecu_part_number"] == "CAL-5678"
        assert result["software_version"] == "SW v2.1.0"
        assert set(result["supported_modes"]) == {0x01, 0x02, 0x03, 0x04, 0x09}

    def test_vin_exactly_17_chars(self):
        adapter = _make_identify_adapter(
            vin=_TEST_VIN.encode("ascii"),
            supported_modes=[],
        )
        det = AutoDetector(port="COM3")
        result = det.identify_ecu(adapter)
        assert result["vin"] is not None
        assert len(result["vin"]) == 17
        assert result["vin"] == _TEST_VIN

    def test_vin_with_obd_echo_prefix_still_decodes(self):
        # Adapters that don't strip the "49 02 01" service/PID/count
        # prefix should still yield a valid 17-char VIN after our decode.
        raw = bytes([0x49, 0x02, 0x01]) + _TEST_VIN.encode("ascii")
        adapter = _make_identify_adapter(vin=raw, supported_modes=[])
        det = AutoDetector(port="COM3")
        result = det.identify_ecu(adapter)
        assert result["vin"] == _TEST_VIN

    def test_ascii_decode_strips_padding_bytes(self):
        # ECU name with 0x00 padding + leading/trailing spaces.
        padded = b"\x00\x00 ECM-1234 \x00\xff"
        adapter = _make_identify_adapter(
            ecu_name=padded, supported_modes=[]
        )
        det = AutoDetector(port="COM3")
        result = det.identify_ecu(adapter)
        assert result["ecu_id"] == "ECM-1234"


# ---------------------------------------------------------------------------
# TestIdentifyEcuPartialFailure
# ---------------------------------------------------------------------------


class TestIdentifyEcuPartialFailure:
    """identify_ecu never raises — partial failures produce None fields."""

    def test_vin_read_fails_other_fields_still_populated(self):
        adapter = _make_identify_adapter(
            vin=None,  # VIN read raises
            ecu_name=b"ECM-1234",
            cal_id=b"CAL-5678",
            sw_ver=b"SW v1.0",
            supported_modes=[0x01, 0x03],
        )
        det = AutoDetector(port="COM3")
        result = det.identify_ecu(adapter)

        assert result["vin"] is None
        assert result["ecu_id"] == "ECM-1234"
        assert result["ecu_part_number"] == "CAL-5678"
        assert result["software_version"] == "SW v1.0"
        assert set(result["supported_modes"]) == {0x01, 0x03}

    def test_all_reads_fail_all_fields_none_modes_empty(self):
        adapter = _make_identify_adapter(
            vin=None,
            ecu_name=None,
            cal_id=None,
            sw_ver=None,
            supported_modes=[],  # no modes supported
        )
        det = AutoDetector(port="COM3")
        result = det.identify_ecu(adapter)

        assert result["vin"] is None
        assert result["ecu_id"] is None
        assert result["ecu_part_number"] is None
        assert result["software_version"] is None
        assert result["supported_modes"] == []

    def test_vin_wrong_length_returns_none_not_bogus_truncation(self):
        # ECU returns only 10 chars — we must NOT emit a truncated VIN.
        adapter = _make_identify_adapter(
            vin=b"1HD1KHM14F",  # 10 chars, not 17
            supported_modes=[],
        )
        det = AutoDetector(port="COM3")
        result = det.identify_ecu(adapter)
        assert result["vin"] is None

    def test_supported_modes_only_contains_modes_that_responded(self):
        adapter = _make_identify_adapter(
            vin=None,
            supported_modes=[0x01, 0x09],  # only these two respond
        )
        det = AutoDetector(port="COM3")
        result = det.identify_ecu(adapter)
        assert set(result["supported_modes"]) == {0x01, 0x09}
        # Order preserved from the probe list.
        assert result["supported_modes"] == [0x01, 0x09]


# ---------------------------------------------------------------------------
# TestAutoDetectorWiring
# ---------------------------------------------------------------------------


class TestAutoDetectorWiring:
    """Constructor defaults, normalization, and timeout/baud passthrough."""

    def test_constructor_accepts_and_normalizes_make_hint(self):
        det = AutoDetector(port="COM3", make_hint="  YAMAHA  ")
        assert det.make_hint == "yamaha"
        # Empty string after strip also normalizes to None.
        det2 = AutoDetector(port="COM3", make_hint="   ")
        assert det2.make_hint is None
        # None stays None.
        det3 = AutoDetector(port="COM3", make_hint=None)
        assert det3.make_hint is None

    def test_timeout_s_is_passed_into_adapter_factories(self):
        captured_kwargs: dict[str, dict] = {}

        def _capture(protocol_key):
            def _factory(**kw):
                captured_kwargs[protocol_key] = kw
                # Raise ProtocolError so detect() moves on to next.
                raise ProtocolError("test")
            return _factory

        with _patch_adapter_factories(
            can_factory=_capture("can"),
            kline_factory=_capture("kline"),
            j1850_factory=_capture("j1850"),
            elm327_factory=_capture("elm"),
        ):
            det = AutoDetector(port="COM3", timeout_s=12.5)
            with pytest.raises(NoECUDetectedError):
                det.detect()

        # CAN uses request_timeout for the per-call timeout.
        assert captured_kwargs["can"]["request_timeout"] == 12.5
        # K-line uses read_timeout.
        assert captured_kwargs["kline"]["read_timeout"] == 12.5
        # J1850 uses timeout_s.
        assert captured_kwargs["j1850"]["timeout_s"] == 12.5
        # ELM327 uses timeout.
        assert captured_kwargs["elm"]["timeout"] == 12.5

    def test_baud_none_vs_explicit(self):
        captured_none: dict[str, dict] = {}

        def _capture_none(protocol_key):
            def _factory(**kw):
                captured_none[protocol_key] = kw
                raise ProtocolError("test")
            return _factory

        # baud=None → adapter factories must NOT receive a baud kwarg.
        with _patch_adapter_factories(
            can_factory=_capture_none("can"),
            kline_factory=_capture_none("kline"),
            j1850_factory=_capture_none("j1850"),
            elm327_factory=_capture_none("elm"),
        ):
            det = AutoDetector(port="COM3", baud=None)
            with pytest.raises(NoECUDetectedError):
                det.detect()

        assert "bitrate" not in captured_none["can"]
        assert "baud" not in captured_none["kline"]
        assert "baudrate" not in captured_none["j1850"]
        assert "baud" not in captured_none["elm"]

        # baud=500000 → adapter factories receive the protocol-specific
        # baud kwarg.
        captured_explicit: dict[str, dict] = {}

        def _capture_expl(protocol_key):
            def _factory(**kw):
                captured_explicit[protocol_key] = kw
                raise ProtocolError("test")
            return _factory

        with _patch_adapter_factories(
            can_factory=_capture_expl("can"),
            kline_factory=_capture_expl("kline"),
            j1850_factory=_capture_expl("j1850"),
            elm327_factory=_capture_expl("elm"),
        ):
            det = AutoDetector(port="COM3", baud=500000)
            with pytest.raises(NoECUDetectedError):
                det.detect()

        assert captured_explicit["can"]["bitrate"] == 500000
        assert captured_explicit["kline"]["baud"] == 500000
        assert captured_explicit["j1850"]["baudrate"] == 500000
        assert captured_explicit["elm"]["baud"] == 500000


# ---------------------------------------------------------------------------
# TestErrorClass
# ---------------------------------------------------------------------------


class TestErrorClass:
    """:class:`NoECUDetectedError` is a :class:`ProtocolError` subclass."""

    def test_no_ecu_detected_is_protocol_error_subclass(self):
        # Consumer code with `except ProtocolError:` must catch this.
        assert issubclass(NoECUDetectedError, ProtocolError)
        err = NoECUDetectedError(
            port="COM3",
            make_hint="harley",
            errors=[("CANAdapter", ProtocolError("can err"))],
        )
        # Attributes preserved.
        assert err.port == "COM3"
        assert err.make_hint == "harley"
        assert len(err.errors) == 1
        # Catchable as ProtocolError.
        caught = False
        try:
            raise err
        except ProtocolError:
            caught = True
        assert caught
