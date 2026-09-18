"""Hardware interface — OBD adapter communication, ECU protocols, sensor data.

Phase 134 adds the :mod:`motodiag.hardware.protocols` subpackage with
the :class:`ProtocolAdapter` ABC and its supporting models/exceptions.
The most common names are re-exported here so downstream code can do::

    from motodiag.hardware import ProtocolAdapter

without reaching into the ``protocols`` submodule.
"""

from motodiag.hardware.protocols import (
    ConnectionError,
    ProtocolAdapter,
    ProtocolError,
    TimeoutError,
    UnsupportedCommandError,
)

__all__ = [
    "ProtocolAdapter",
    "ProtocolError",
    "ConnectionError",
    "TimeoutError",
    "UnsupportedCommandError",
]
