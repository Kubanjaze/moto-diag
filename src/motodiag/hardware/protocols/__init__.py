"""OBD protocol abstraction layer (Phase 134).

This package defines the contract every Track E protocol adapter
implements. Concrete adapters arrive in later phases:

- Phase 135 — ELM327 (serial / Bluetooth)
- Phase 136 — native CAN (ISO 15765-4)
- Phase 137 — K-line (ISO 14230 / KWP2000)
- Phase 138 — J1850 (VPW / PWM for older Harleys)
- Phase 139 — ECU auto-detect

Phase 140 wires the first real adapter through the
``motodiag hardware diagnose`` CLI.

Public surface (re-exported from the sub-modules so callers import
from this package directly)::

    from motodiag.hardware.protocols import (
        ProtocolAdapter,
        ProtocolConnection,
        DTCReadResult,
        PIDResponse,
        ProtocolError,
        ConnectionError,
        TimeoutError,
        UnsupportedCommandError,
    )
"""

from motodiag.hardware.protocols.base import ProtocolAdapter
from motodiag.hardware.protocols.elm327 import ELM327Adapter
from motodiag.hardware.protocols.exceptions import (
    ConnectionError,
    ProtocolError,
    TimeoutError,
    UnsupportedCommandError,
)
from motodiag.hardware.protocols.j1850 import J1850Adapter
from motodiag.hardware.protocols.models import (
    DTCReadResult,
    PIDResponse,
    ProtocolConnection,
)

__all__ = [
    "ProtocolAdapter",
    "ELM327Adapter",
    "J1850Adapter",
    "ProtocolConnection",
    "DTCReadResult",
    "PIDResponse",
    "ProtocolError",
    "ConnectionError",
    "TimeoutError",
    "UnsupportedCommandError",
]
