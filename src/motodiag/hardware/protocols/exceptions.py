"""Exception hierarchy for OBD protocol adapters (Phase 134).

Every adapter-raised exception descends from :class:`ProtocolError`, so
callers can do ``except ProtocolError`` to catch anything coming out of
a misbehaving adapter without enumerating every subclass.

.. note::

   :class:`ConnectionError` and :class:`TimeoutError` defined in this
   module deliberately shadow the Python built-ins of the same name
   inside ``motodiag.hardware.protocols``'s namespace. This is a
   conscious tradeoff: we want a consistent domain vocabulary where
   every protocol error is catchable as ``ProtocolError``. Consumers
   that need to disambiguate should alias on import, e.g.::

       from motodiag.hardware.protocols import ConnectionError as ProtocolConnectionError

   or (preferred) catch ``ProtocolError`` and branch on the concrete
   subclass. The shadowing is documented on each class docstring so
   nobody is surprised at the REPL.
"""

from __future__ import annotations


class ProtocolError(Exception):
    """Base class for every protocol-layer error.

    Direct subclass of :class:`Exception`. Adapters (ELM327 in Phase
    135, CAN in Phase 136, K-line in Phase 137, J1850 in Phase 138, ECU
    auto-detect in Phase 139) raise one of the concrete subclasses
    below. Callers that don't care about the specific failure mode can
    catch ``ProtocolError`` and log/abort generically.
    """


class ConnectionError(ProtocolError):  # noqa: A001 — intentional shadow
    """Raised when ``ProtocolAdapter.connect()`` cannot establish a link.

    Typical triggers: serial port unavailable, Bluetooth pairing
    refused, ELM327 ``AT Z`` handshake timeout, ignition off.

    .. warning::

       This class deliberately shadows the built-in
       :class:`ConnectionError` inside this module. If a consumer needs
       the Python built-in in the same scope, alias on import::

           from motodiag.hardware.protocols import ConnectionError as ProtocolConnectionError
    """


class TimeoutError(ProtocolError):  # noqa: A001 — intentional shadow
    """Raised when an adapter read/write exceeds its configured timeout.

    The timeout is set on :class:`~motodiag.hardware.protocols.models.ProtocolConnection`
    (``timeout_s``, default 2.0s). Adapter implementations must raise
    this, not the built-in :class:`TimeoutError`, so callers can
    uniformly catch ``ProtocolError``.

    .. warning::

       This class deliberately shadows the built-in
       :class:`TimeoutError` inside this module. Alias on import if you
       need the built-in in the same scope::

           from motodiag.hardware.protocols import TimeoutError as ProtocolTimeoutError
    """


class UnsupportedCommandError(ProtocolError):
    """Raised when a caller asks an adapter to do something the protocol cannot.

    Example: calling ``read_vin()`` on a J1850 VPW link that doesn't
    expose Mode 09, or a PID read on a K-line ECU that predates OBD-II.

    The command name is preserved on the ``.command`` attribute for
    log legibility::

        try:
            adapter.read_vin()
        except UnsupportedCommandError as exc:
            logger.warning("protocol cannot service %s", exc.command)

    Parameters
    ----------
    command:
        Human-readable name of the command that was rejected
        (e.g. ``"read_vin"``, ``"clear_dtcs"``, ``"mode_09_pid_02"``).
    """

    def __init__(self, command: str) -> None:
        super().__init__(f"Protocol does not support command: {command}")
        self.command: str = command
