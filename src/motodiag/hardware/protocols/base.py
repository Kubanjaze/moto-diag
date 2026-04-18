"""Abstract base class for OBD protocol adapters (Phase 134).

This is a pure-contract module: it declares the methods every adapter
(ELM327 in Phase 135, native CAN in Phase 136, K-line in Phase 137,
J1850 in Phase 138, ECU auto-detect in Phase 139) must implement. No
concrete I/O lives here — the ABC is the first guardrail so Python
refuses to instantiate a half-built adapter.

The ``is_connected`` property is intentionally concrete: every
realistic adapter tracks its connection state in ``self._is_connected``,
so making each subclass re-implement the same three-line getter would
be pure noise. Subclasses flip the backing attribute from ``connect()``
and ``disconnect()``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class ProtocolAdapter(ABC):
    """Abstract contract every Track E protocol adapter implements.

    Concrete subclasses must implement all eight abstract methods below.
    Python's ABC machinery will refuse to instantiate any subclass that
    misses even one — verified by Phase 134 tests.

    The ``is_connected`` property is concrete with a sensible default:
    subclasses just set ``self._is_connected`` from their ``connect()``
    and ``disconnect()`` implementations, they do not need to override
    the property itself.

    Exception contract (from :mod:`motodiag.hardware.protocols.exceptions`):

    - :class:`~motodiag.hardware.protocols.ConnectionError` —
      raised by ``connect()`` on handshake failure; raised by
      ``send_command()`` when called on a disconnected adapter.
    - :class:`~motodiag.hardware.protocols.TimeoutError` —
      raised by any read/write that exceeds the configured
      ``timeout_s``.
    - :class:`~motodiag.hardware.protocols.UnsupportedCommandError` —
      raised only when the caller insists on an operation the protocol
      physically cannot carry (see ``read_vin`` below).
    - Every exception above is a subclass of
      :class:`~motodiag.hardware.protocols.ProtocolError`, so callers
      can catch that one base class to handle all adapter failures.
    """

    @abstractmethod
    def connect(self, port: str, baud: int) -> None:
        """Open the transport and bring the adapter to a ready state.

        Must run the protocol handshake before returning. On failure,
        raise :class:`ConnectionError` from
        :mod:`motodiag.hardware.protocols.exceptions` — never return
        with partial state. On success, set
        ``self._is_connected = True`` so the :attr:`is_connected`
        property flips without the subclass touching it.

        Idempotent: calling ``connect()`` on an already-connected
        adapter is a no-op, not an error.

        Parameters
        ----------
        port:
            Serial device path or Bluetooth address.
        baud:
            Serial baud rate. 38400 is the ELM327 factory default.
        """

    @abstractmethod
    def disconnect(self) -> None:
        """Close the transport and release handles.

        Must not raise — log and swallow cleanup errors so a failed
        disconnect never masks an earlier exception. Sets
        ``self._is_connected = False``. Idempotent: calling
        ``disconnect()`` on an already-disconnected adapter is a no-op.
        """

    @abstractmethod
    def send_command(self, cmd: bytes) -> bytes:
        """Send raw protocol bytes, return the raw reply.

        Protocol framing is stripped, but no semantic parsing is done.
        This is the low-level escape hatch for commands the higher-
        level methods do not cover (custom Mode 22 reads, manufacturer-
        specific Mode 21, etc.).

        Raises
        ------
        ConnectionError
            If called on a disconnected adapter.
        TimeoutError
            If the configured ``timeout_s`` elapses before a complete
            reply arrives.
        """

    @abstractmethod
    def read_dtcs(self) -> list[str]:
        """Execute Mode 03 and return stored DTC codes.

        Returns codes in ``P0171`` / ``C1234`` / ``B2468`` / ``U0100``
        format. Empty list means no stored faults (not an error).
        Consumers typically wrap the result in a
        :class:`~motodiag.hardware.protocols.models.DTCReadResult`
        with a timestamp and source-protocol label — the adapter
        itself stays schema-free.
        """

    @abstractmethod
    def clear_dtcs(self) -> bool:
        """Execute Mode 04 to clear stored DTCs.

        Returns
        -------
        bool
            ``True`` if the ECU acknowledged the clear, ``False`` if
            the ECU refused (some ECUs require ignition-on/engine-off).
            Does not raise on a refused clear — only raises on comm
            errors. The caller decides whether a ``False`` is fatal
            to their workflow.
        """

    @abstractmethod
    def read_pid(self, pid: int) -> Optional[int]:
        """Execute a Mode 01 PID read, return the decoded integer.

        For multi-byte PIDs the adapter is responsible for the
        protocol-specific bit-shift and scaling. Returns ``None`` if
        the ECU replies "PID not supported" (NACK or all-zeros
        service-01 support mask).

        For richer decodes (floats, multi-field), adapters can expose
        their own higher-level methods that return a
        :class:`~motodiag.hardware.protocols.models.PIDResponse`; this
        method is the always-available shortcut that keeps Phase 140
        CLI wiring a one-liner.
        """

    @abstractmethod
    def read_vin(self) -> Optional[str]:
        """Execute Mode 09 PID 02 and return the 17-char VIN.

        Returns uppercase ASCII. Returns ``None`` if the protocol could
        support VIN but the specific ECU does not.

        Raises
        ------
        UnsupportedCommandError
            Only when the protocol physically cannot carry VIN data
            (pre-2008 K-line, some J1850 VPW on early Harleys).
            Returning ``None`` is preferred where the protocol *could*
            support VIN but the ECU happens not to.
        """

    @abstractmethod
    def get_protocol_name(self) -> str:
        """Return a stable, human-readable protocol identifier.

        Example: ``"ISO 15765-4 (CAN 11/500)"``, ``"ISO 14230 KWP2000"``,
        ``"SAE J1850 VPW"``. The identifier is stable across the life
        of the adapter instance and feeds
        :attr:`~motodiag.hardware.protocols.models.DTCReadResult.source_protocol`
        plus any UI that tells the mechanic what's connected.
        """

    @property
    def is_connected(self) -> bool:
        """Whether the adapter currently holds an open link.

        Defaults to ``False`` when ``_is_connected`` has not been set.
        Subclasses flip ``self._is_connected`` in their ``connect()``
        and ``disconnect()`` methods — no property override required.
        """
        return getattr(self, "_is_connected", False)
