"""Phase 134 — OBD protocol abstraction layer tests.

Covers:

- ``TestProtocolAdapterABC`` — the :class:`ProtocolAdapter` ABC
  enforces that every concrete subclass implements all eight abstract
  methods; the ``is_connected`` property is concrete with a sensible
  default backed by ``self._is_connected``.
- ``TestProtocolConnection`` — the frozen Pydantic model with
  ``extra="forbid"``, baud/timeout validation, default values.
- ``TestDTCReadResult`` — DTC regex validation, uppercase
  normalization, UTC-aware default timestamp, empty-list support.
- ``TestPIDResponse`` — paired-presence rule on
  ``parsed_value``/``parsed_unit``, PID range enforcement.
- ``TestExceptionHierarchy`` — all protocol exceptions descend from
  :class:`ProtocolError`; :class:`UnsupportedCommandError` carries a
  ``.command`` attribute.
- ``TestPublicReExports`` — canonical import paths work and
  ``__all__`` lists exactly the expected names.

Zero hardware, zero serial, zero tokens — pure Python.
"""

from __future__ import annotations

import abc
from datetime import datetime, timezone
from typing import Optional

import pytest
from pydantic import ValidationError

from motodiag.hardware.protocols import (
    ConnectionError as ProtocolConnectionError,
)
from motodiag.hardware.protocols import (
    DTCReadResult,
    PIDResponse,
    ProtocolAdapter,
    ProtocolConnection,
    ProtocolError,
    UnsupportedCommandError,
)
from motodiag.hardware.protocols import (
    TimeoutError as ProtocolTimeoutError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_complete_subclass(name: str = "FullAdapter") -> type[ProtocolAdapter]:
    """Build a subclass that implements every abstract method with stubs."""

    class _Full(ProtocolAdapter):
        def connect(self, port: str, baud: int) -> None:  # pragma: no cover - stub
            self._is_connected = True

        def disconnect(self) -> None:  # pragma: no cover - stub
            self._is_connected = False

        def send_command(self, cmd: bytes) -> bytes:  # pragma: no cover - stub
            return b""

        def read_dtcs(self) -> list[str]:  # pragma: no cover - stub
            return []

        def clear_dtcs(self) -> bool:  # pragma: no cover - stub
            return True

        def read_pid(self, pid: int) -> Optional[int]:  # pragma: no cover - stub
            return None

        def read_vin(self) -> Optional[str]:  # pragma: no cover - stub
            return None

        def get_protocol_name(self) -> str:  # pragma: no cover - stub
            return "TEST"

    _Full.__name__ = name
    return _Full


_ABSTRACT_METHODS = (
    "connect",
    "disconnect",
    "send_command",
    "read_dtcs",
    "clear_dtcs",
    "read_pid",
    "read_vin",
    "get_protocol_name",
)


# ---------------------------------------------------------------------------
# TestProtocolAdapterABC
# ---------------------------------------------------------------------------


class TestProtocolAdapterABC:
    """The ABC refuses incomplete subclasses and provides is_connected."""

    def test_cannot_instantiate_base_class(self) -> None:
        with pytest.raises(TypeError) as exc_info:
            ProtocolAdapter()  # type: ignore[abstract]
        assert "abstract" in str(exc_info.value).lower()

    @pytest.mark.parametrize("missing_method", _ABSTRACT_METHODS)
    def test_subclass_missing_one_method_cannot_instantiate(
        self, missing_method: str
    ) -> None:
        Full = _make_complete_subclass()
        # Strip the one method — mark it as abstract again by deleting it.
        body = {
            name: getattr(Full, name)
            for name in _ABSTRACT_METHODS
            if name != missing_method
        }
        Partial = type("PartialAdapter", (ProtocolAdapter,), body)
        with pytest.raises(TypeError) as exc_info:
            Partial()
        assert "abstract" in str(exc_info.value).lower()

    def test_complete_subclass_instantiates(self) -> None:
        Full = _make_complete_subclass()
        instance = Full()
        assert isinstance(instance, ProtocolAdapter)

    def test_is_connected_defaults_to_false(self) -> None:
        Full = _make_complete_subclass()
        instance = Full()
        assert instance.is_connected is False

    def test_is_connected_reflects_backing_attribute(self) -> None:
        Full = _make_complete_subclass()
        instance = Full()
        instance._is_connected = True  # type: ignore[attr-defined]
        assert instance.is_connected is True
        instance._is_connected = False  # type: ignore[attr-defined]
        assert instance.is_connected is False

    def test_is_connected_is_a_property_not_callable(self) -> None:
        assert isinstance(ProtocolAdapter.is_connected, property)

    def test_abstract_methods_set_matches_spec(self) -> None:
        assert ProtocolAdapter.__abstractmethods__ == frozenset(_ABSTRACT_METHODS)

    def test_base_uses_abcmeta(self) -> None:
        assert issubclass(ProtocolAdapter, abc.ABC)
        assert isinstance(ProtocolAdapter, abc.ABCMeta)


# ---------------------------------------------------------------------------
# TestProtocolConnection
# ---------------------------------------------------------------------------


class TestProtocolConnection:
    """ProtocolConnection — frozen, validated, sensible defaults."""

    def test_valid_construction_with_defaults(self) -> None:
        conn = ProtocolConnection(port="COM3", protocol_name="ISO 15765-4 (CAN)")
        assert conn.port == "COM3"
        assert conn.baud == 38400
        assert conn.timeout_s == 2.0
        assert conn.protocol_name == "ISO 15765-4 (CAN)"

    @pytest.mark.parametrize("bad_baud", [0, -1, 1_000_001])
    def test_invalid_baud_rejected(self, bad_baud: int) -> None:
        with pytest.raises(ValidationError):
            ProtocolConnection(
                port="COM3", baud=bad_baud, protocol_name="CAN"
            )

    @pytest.mark.parametrize("bad_timeout", [0.0, -0.5, 60.01])
    def test_invalid_timeout_rejected(self, bad_timeout: float) -> None:
        with pytest.raises(ValidationError):
            ProtocolConnection(
                port="COM3", timeout_s=bad_timeout, protocol_name="CAN"
            )

    def test_model_is_frozen(self) -> None:
        conn = ProtocolConnection(port="COM3", protocol_name="CAN")
        with pytest.raises(ValidationError):
            conn.port = "COM7"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ProtocolConnection(
                port="COM3",
                protocol_name="CAN",
                portt="typo",  # type: ignore[call-arg]
            )


# ---------------------------------------------------------------------------
# TestDTCReadResult
# ---------------------------------------------------------------------------


class TestDTCReadResult:
    """DTCReadResult — regex validation, uppercase, UTC default."""

    def test_codes_normalize_to_uppercase(self) -> None:
        result = DTCReadResult(
            codes=["p0171", "c1234", "b2468", "u0100"],
            source_protocol="ISO 15765-4 (CAN)",
        )
        assert result.codes == ["P0171", "C1234", "B2468", "U0100"]

    @pytest.mark.parametrize(
        "bad_code",
        ["X1234", "P12", "P0G71", "", "P01710", "12345", "PP171"],
    )
    def test_invalid_code_format_rejected(self, bad_code: str) -> None:
        with pytest.raises(ValidationError):
            DTCReadResult(codes=[bad_code], source_protocol="CAN")

    def test_empty_codes_list_valid(self) -> None:
        result = DTCReadResult(codes=[], source_protocol="CAN")
        assert result.codes == []

    def test_read_at_defaults_to_utc_aware_datetime(self) -> None:
        before = datetime.now(timezone.utc)
        result = DTCReadResult(source_protocol="CAN")
        after = datetime.now(timezone.utc)
        assert isinstance(result.read_at, datetime)
        assert result.read_at.tzinfo is not None
        # UTC offset is zero
        assert result.read_at.utcoffset() == timezone.utc.utcoffset(None)
        assert before <= result.read_at <= after

    def test_source_protocol_is_required(self) -> None:
        with pytest.raises(ValidationError):
            DTCReadResult(codes=["P0171"])  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# TestPIDResponse
# ---------------------------------------------------------------------------


class TestPIDResponse:
    """PIDResponse — paired presence, PID range."""

    def test_valid_with_parsed_value_and_unit(self) -> None:
        resp = PIDResponse(
            pid=0x0C,
            raw_bytes=b"\x1a\xf8",
            parsed_value=1726.0,
            parsed_unit="rpm",
        )
        assert resp.parsed_value == 1726.0
        assert resp.parsed_unit == "rpm"

    def test_valid_with_both_none(self) -> None:
        resp = PIDResponse(pid=0x0C, raw_bytes=b"\x1a\xf8")
        assert resp.parsed_value is None
        assert resp.parsed_unit is None

    def test_value_without_unit_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PIDResponse(
                pid=0x0C,
                raw_bytes=b"\x00",
                parsed_value=42.0,
                # parsed_unit omitted
            )

    def test_unit_without_value_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PIDResponse(
                pid=0x0C,
                raw_bytes=b"\x00",
                parsed_unit="rpm",
            )

    @pytest.mark.parametrize("bad_pid", [-1, 0x10000, 70000])
    def test_pid_out_of_range_rejected(self, bad_pid: int) -> None:
        with pytest.raises(ValidationError):
            PIDResponse(pid=bad_pid, raw_bytes=b"\x00")


# ---------------------------------------------------------------------------
# TestExceptionHierarchy
# ---------------------------------------------------------------------------


class TestExceptionHierarchy:
    """All protocol exceptions descend from ProtocolError."""

    def test_connection_error_subclass_of_protocol_error(self) -> None:
        assert issubclass(ProtocolConnectionError, ProtocolError)
        assert issubclass(ProtocolError, Exception)

    def test_timeout_error_subclass_of_protocol_error(self) -> None:
        assert issubclass(ProtocolTimeoutError, ProtocolError)

    def test_unsupported_command_error_carries_command_attribute(self) -> None:
        err = UnsupportedCommandError("read_vin")
        assert issubclass(UnsupportedCommandError, ProtocolError)
        assert err.command == "read_vin"
        assert "read_vin" in str(err)

    def test_unsupported_command_caught_via_protocol_error(self) -> None:
        caught: Optional[ProtocolError] = None
        try:
            raise UnsupportedCommandError("read_vin")
        except ProtocolError as exc:
            caught = exc
        assert isinstance(caught, UnsupportedCommandError)
        assert caught.command == "read_vin"


# ---------------------------------------------------------------------------
# TestPublicReExports
# ---------------------------------------------------------------------------


class TestPublicReExports:
    """Canonical import paths and __all__ correctness."""

    def test_protocols_package_exports(self) -> None:
        # Re-import in a fresh binding and assert the full surface is present.
        import motodiag.hardware.protocols as proto

        for name in (
            "ProtocolAdapter",
            "ProtocolConnection",
            "DTCReadResult",
            "PIDResponse",
            "ProtocolError",
            "ConnectionError",
            "TimeoutError",
            "UnsupportedCommandError",
        ):
            assert hasattr(proto, name), f"motodiag.hardware.protocols missing {name}"

    def test_hardware_package_convenience_reexport(self) -> None:
        from motodiag.hardware import ProtocolAdapter as HW_Adapter
        from motodiag.hardware import ProtocolConnection as HW_Connection

        assert HW_Adapter is ProtocolAdapter
        assert HW_Connection is ProtocolConnection

    def test_protocols_all_lists_exact_public_names(self) -> None:
        # Forward-compat: Phases 135-138 append concrete adapters to __all__.
        # Assert the Phase 134 baseline set is a subset rather than exact match.
        import motodiag.hardware.protocols as proto

        phase_134_baseline = {
            "ProtocolAdapter",
            "ProtocolConnection",
            "DTCReadResult",
            "PIDResponse",
            "ProtocolError",
            "ConnectionError",
            "TimeoutError",
            "UnsupportedCommandError",
        }
        assert phase_134_baseline.issubset(set(proto.__all__))
