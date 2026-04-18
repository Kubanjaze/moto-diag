"""Pydantic data models for OBD protocol adapters (Phase 134).

These are data containers only — zero behavior, zero I/O. Concrete
adapters (Phases 135-139) populate these on the way out; callers
consume them as plain read-only records.

Three models live here:

- :class:`ProtocolConnection` — immutable descriptor of an active link
  (port, baud, timeout, protocol name). Frozen so the descriptor can be
  passed around without defensive copies.

- :class:`DTCReadResult` — the output of a Mode 03 read: a list of DTC
  codes in ``P0171`` format, plus the source protocol and a UTC
  timestamp. Codes are regex-validated at construction to reject
  typos at the boundary.

- :class:`PIDResponse` — the output of a Mode 01/22 PID read: the PID
  number, raw bytes, and an optional decoded (value, unit) pair. The
  paired-presence rule (both set or both None) is validated so no
  consumer ever sees a decoded value without a unit label.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


# OBD-II DTC code format: P|C|B|U followed by four hex digits.
# Examples: P0171, C1234, B2468, U0100.
_DTC_CODE_RE = re.compile(r"^[PCBU][0-9A-F]{4}$")


class ProtocolConnection(BaseModel):
    """Immutable descriptor of a live protocol adapter connection.

    Constructed by the adapter after a successful ``connect()`` and
    handed back to callers that want to record the negotiated link
    state. Frozen because connection descriptors should not mutate mid
    session — if the baud renegotiates, the adapter constructs a *new*
    :class:`ProtocolConnection` (see Phase 135 ELM327 handshake).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    port: str = Field(
        ...,
        description=(
            "Serial device path ('COM3', '/dev/ttyUSB0') or Bluetooth "
            "address ('AA:BB:CC:DD:EE:FF')."
        ),
    )
    baud: int = Field(
        default=38400,
        gt=0,
        le=1_000_000,
        description="Serial baud rate. 38400 matches ELM327 factory default.",
    )
    timeout_s: float = Field(
        default=2.0,
        gt=0.0,
        le=60.0,
        description="Per-operation timeout in seconds.",
    )
    protocol_name: str = Field(
        ...,
        description=(
            "Human-readable protocol identifier, e.g. "
            "'ISO 15765-4 (CAN 11/500)'. Matches "
            "ProtocolAdapter.get_protocol_name()."
        ),
    )


class DTCReadResult(BaseModel):
    """Structured result of a diagnostic-trouble-code read.

    Produced by callers that wrap :meth:`ProtocolAdapter.read_dtcs`
    with a timestamp and source-protocol label. The adapter itself
    returns a bare ``list[str]`` — this model is the trace-friendly
    envelope consumers use when recording a session.

    Code format is validated at construction:

    - Each code must match ``^[PCBU][0-9A-F]{4}$`` (case-insensitive
      input, uppercase storage).
    - Empty list is valid — means "no stored faults."
    - ``read_at`` defaults to the current UTC timestamp.
    """

    model_config = ConfigDict(extra="forbid")

    codes: list[str] = Field(
        default_factory=list,
        description="DTC codes in P0171 format. Empty list == no faults.",
    )
    source_protocol: str = Field(
        ...,
        description="Protocol identifier this read came from.",
    )
    read_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the read completed.",
    )

    @field_validator("codes", mode="before")
    @classmethod
    def _normalize_and_validate_codes(cls, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("codes must be a list of strings")
        normalized: list[str] = []
        for entry in value:
            if not isinstance(entry, str):
                raise ValueError(f"DTC code must be str, got {type(entry).__name__}")
            upper = entry.upper()
            if not _DTC_CODE_RE.match(upper):
                raise ValueError(
                    f"Invalid DTC code format: {entry!r} "
                    "(expected [PCBU] + 4 hex digits, e.g. 'P0171')"
                )
            normalized.append(upper)
        return normalized


class PIDResponse(BaseModel):
    """Structured result of a Mode 01 / Mode 22 PID read.

    The adapter's own :meth:`ProtocolAdapter.read_pid` shortcut returns
    ``int | None`` for simple cases. Adapters that want to return
    richer data (raw bytes, decoded float, unit label) expose their own
    higher-level methods that produce this model.

    Pairing rule: ``parsed_value`` and ``parsed_unit`` must be both
    ``None`` or both set. A value without a unit is ambiguous; a unit
    without a value is meaningless.
    """

    model_config = ConfigDict(extra="forbid")

    pid: int = Field(
        ...,
        ge=0,
        le=0xFFFF,
        description="PID number — 0-0xFF for Mode 01, 0-0xFFFF for Mode 22.",
    )
    raw_bytes: bytes = Field(
        ...,
        description="Raw bytes from the adapter after protocol framing is stripped.",
    )
    parsed_value: Optional[float] = Field(
        default=None,
        description="Decoded physical value, or None if no decode available.",
    )
    parsed_unit: Optional[str] = Field(
        default=None,
        description="Unit label for parsed_value ('°C', 'rpm', 'kPa', ...). Paired with parsed_value.",
    )

    @model_validator(mode="after")
    def _check_paired_presence(self) -> "PIDResponse":
        value_set = self.parsed_value is not None
        unit_set = self.parsed_unit is not None
        if value_set != unit_set:
            raise ValueError(
                "parsed_value and parsed_unit must be both set or both None "
                f"(got parsed_value={self.parsed_value!r}, parsed_unit={self.parsed_unit!r})"
            )
        return self
