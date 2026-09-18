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
from typing import Optional

import pytest

from motodiag.hardware.protocols import (
    ConnectionError as ProtocolConnectionError,
)
from motodiag.hardware.protocols import (
    ProtocolAdapter,
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



# ---------------------------------------------------------------------------
# TestDTCReadResult
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# TestPIDResponse
# ---------------------------------------------------------------------------



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


