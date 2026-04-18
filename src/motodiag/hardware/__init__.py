"""Hardware interface — OBD adapter communication, ECU protocols, sensor data.

Phase 134 adds the :mod:`motodiag.hardware.protocols` subpackage with
the :class:`ProtocolAdapter` ABC and its supporting models/exceptions.
The most common names are re-exported here so downstream code can do::

    from motodiag.hardware import ProtocolAdapter

without reaching into the ``protocols`` submodule.
"""

from motodiag.hardware.protocols import (
    ConnectionError,
    DTCReadResult,
    PIDResponse,
    ProtocolAdapter,
    ProtocolConnection,
    ProtocolError,
    TimeoutError,
    UnsupportedCommandError,
)

__all__ = [
    "ProtocolAdapter",
    "ProtocolConnection",
    "DTCReadResult",
    "PIDResponse",
    "ProtocolError",
    "ConnectionError",
    "TimeoutError",
    "UnsupportedCommandError",
]
