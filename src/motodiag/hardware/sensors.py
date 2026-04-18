"""Live-sensor catalog + streamer for Mode 01 PID polling (Phase 141).

Second user-facing Track E phase. This module is the pure
knowledge-and-decode layer that sits between the protocol adapters
(Phases 134-138, which already assemble raw multi-byte responses into
:class:`int` values via
:meth:`~motodiag.hardware.protocols.base.ProtocolAdapter.read_pid`) and
the :class:`~motodiag.cli.hardware.stream_cmd` Rich-live renderer.

SAE J1979 is the authoritative source for every PID name, byte count,
and decode formula encoded in :data:`SENSOR_CATALOG`. The formulas have
been cross-referenced against the SAE J1979-DA digital annex (2021
revision) and ISO 15031-5 — both normative for OBD-II PID 0x00–0x5F.
Test vectors in ``tests/test_phase141_stream.py`` lock the decoders to
canonical values (RPM 0x1AF8 → 1726 rpm, coolant 0x5A → 50 °C,
battery 0x3600 → 13.824 V, O2 voltage 0x5AB0 → 0.45 V, etc.).

Three concrete things live here:

- :data:`SENSOR_CATALOG` — ``dict[int, SensorSpec]`` mapping each
  supported PID to its human name, unit, byte count, and decoder.
- :class:`SensorReading` — Pydantic v2 model capturing one cell of a
  single poll tick (``ok`` / ``unsupported`` / ``timeout`` + metadata).
- :class:`SensorStreamer` — one-shot generator that loops over a fixed
  list of PIDs at a configurable poll rate, yielding a list of
  :class:`SensorReading` per tick. Translates per-PID
  :class:`~motodiag.hardware.protocols.exceptions.TimeoutError` into a
  timeout cell (next tick retries), re-raises any other
  :class:`~motodiag.hardware.protocols.exceptions.ProtocolError`
  immediately so the CLI can render a red failure panel.

Design notes
------------

- ``read_pid`` per the Phase 134 ABC returns an ``Optional[int]`` that
  is **already assembled** (``(A << 8) | B`` for 2-byte PIDs). Decoders
  here operate on that integer — there is no byte juggling in this
  module.
- O2 sensor voltage PIDs 0x14-0x1B are 2-byte: the upper byte is
  voltage (``A / 200``), the lower byte is short-term fuel trim percent.
  Phase 141 reports voltage only; STFT is deferred because every PID
  today maps to a single ``value + unit`` — a ``secondary_value`` /
  ``secondary_unit`` pair is a later roadmap item.
- Unknown PIDs (not in the catalog) are **not** an error at the stream
  level: the streamer emits an ``unsupported`` reading with
  ``name=f"PID 0x{pid:02X}"`` and ``unit=""`` so the CLI table keeps
  its row layout. Callers who want hard validation should go through
  :func:`parse_pid_list`, which only accepts numerically-valid tokens.
- :class:`SensorStreamer` is deliberately one-shot. Consuming the
  generator twice would silently emit a second, overlapping poll
  sequence onto the same adapter — calling
  :meth:`SensorStreamer.iter_readings` a second time raises
  :class:`RuntimeError` so the caller gets a loud failure instead.
- ``sleep`` and ``clock`` are injectable kwargs specifically for
  deterministic tests — pass :class:`unittest.mock.Mock` to verify the
  throttle and a frozen-UTC ``lambda`` to pin timestamps.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterator, List, Literal, Optional

import click
from pydantic import BaseModel, Field, field_validator, model_validator

from motodiag.hardware.protocols.exceptions import (
    TimeoutError as ProtocolTimeoutError,
)


# ---------------------------------------------------------------------------
# SensorSpec — immutable catalog row
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SensorSpec:
    """One row in :data:`SENSOR_CATALOG`.

    Parameters
    ----------
    pid:
        OBD-II Mode 01 PID number (0-255). Stored on the spec as well
        as the catalog key for self-description — a :class:`SensorSpec`
        copied out of the catalog still knows its own PID.
    name:
        Human-readable sensor name exactly as it appears on the
        mechanic's live-view table (e.g. ``"Engine RPM"``).
    unit:
        Short physical unit (``"rpm"``, ``"°C"``, ``"kPa"``, ``"V"``,
        ``"%"``, ``"g/s"``, ``"° BTDC"``, ``"km/h"``, ``"s"``). Empty
        string ``""`` only for non-catalog PIDs surfaced via the
        streamer's "unsupported" fallback (those never go through this
        dataclass).
    byte_count:
        Number of bytes the ECU returns for this PID, per SAE J1979.
        ``1`` or ``2`` for every Phase 141 entry. Stored so the catalog
        can be reflected on by :class:`SensorStreamer` (and, later,
        Phase 144's hardware simulator).
    decode:
        Pure function ``(raw: int) -> float`` that converts the
        adapter-assembled integer into a human-legible float. Must be
        referentially transparent — no I/O, no exceptions on well-formed
        input. Called exactly once per poll-cycle per PID.
    """

    pid: int
    name: str
    unit: str
    byte_count: int
    decode: Callable[[int], float]


# ---------------------------------------------------------------------------
# Decoder helpers — one line each; live here so SENSOR_CATALOG stays readable
# ---------------------------------------------------------------------------


def _decode_percent_255(raw: int) -> float:
    """``raw * 100 / 255`` — used by load, throttle, fuel-tank level."""
    return raw * 100.0 / 255.0


def _decode_offset_40(raw: int) -> float:
    """``raw - 40`` — used by the four ``°C`` temperature PIDs."""
    return float(raw - 40)


def _decode_rpm(raw: int) -> float:
    """``raw / 4`` — J1979 engine-RPM formula."""
    return raw / 4.0


def _decode_identity(raw: int) -> float:
    """Pass-through decoder (e.g. vehicle speed ``km/h``, runtime ``s``)."""
    return float(raw)


def _decode_timing_advance(raw: int) -> float:
    """``raw / 2 - 64`` — timing advance in ``° BTDC``."""
    return raw / 2.0 - 64.0


def _decode_maf(raw: int) -> float:
    """``raw / 100`` — MAF air-flow rate in ``g/s``."""
    return raw / 100.0


def _decode_fuel_rail(raw: int) -> float:
    """``raw * 3`` — fuel-rail gauge pressure in ``kPa``."""
    return float(raw * 3)


def _decode_battery_voltage(raw: int) -> float:
    """``raw / 1000`` — control-module voltage in ``V`` (2-byte mV)."""
    return raw / 1000.0


def _decode_o2_voltage(raw: int) -> float:
    """``(raw >> 8) / 200`` — upper byte is voltage; lower byte is STFT.

    J1979 PIDs 0x14–0x1B pack two sensors in one response: the
    high byte is O2 voltage (0-1.275 V in 5 mV steps), the low byte is
    short-term fuel trim (%). Phase 141 reports voltage only.
    """
    return (raw >> 8) / 200.0


# ---------------------------------------------------------------------------
# SENSOR_CATALOG — the authoritative Phase 141 PID set
# ---------------------------------------------------------------------------


def _o2_spec(pid: int, label: str) -> SensorSpec:
    """Build one of the eight O2 voltage :class:`SensorSpec` rows."""
    return SensorSpec(
        pid=pid,
        name=f"O2 sensor {label} voltage",
        unit="V",
        byte_count=2,
        decode=_decode_o2_voltage,
    )


SENSOR_CATALOG: dict[int, SensorSpec] = {
    0x04: SensorSpec(0x04, "Calculated engine load", "%", 1, _decode_percent_255),
    0x05: SensorSpec(0x05, "Engine coolant temperature", "°C", 1, _decode_offset_40),
    0x0A: SensorSpec(0x0A, "Fuel rail pressure (gauge)", "kPa", 1, _decode_fuel_rail),
    0x0B: SensorSpec(
        0x0B,
        "Intake manifold absolute pressure",
        "kPa",
        1,
        _decode_identity,
    ),
    0x0C: SensorSpec(0x0C, "Engine RPM", "rpm", 2, _decode_rpm),
    0x0D: SensorSpec(0x0D, "Vehicle speed", "km/h", 1, _decode_identity),
    0x0E: SensorSpec(0x0E, "Timing advance", "° BTDC", 1, _decode_timing_advance),
    0x0F: SensorSpec(0x0F, "Intake air temperature", "°C", 1, _decode_offset_40),
    0x10: SensorSpec(0x10, "MAF air flow rate", "g/s", 2, _decode_maf),
    0x11: SensorSpec(0x11, "Throttle position", "%", 1, _decode_percent_255),
    # O2 sensor voltage, Bank 1/2 × Sensor 1-4 (8 PIDs, 2-byte each).
    0x14: _o2_spec(0x14, "B1S1"),
    0x15: _o2_spec(0x15, "B1S2"),
    0x16: _o2_spec(0x16, "B1S3"),
    0x17: _o2_spec(0x17, "B1S4"),
    0x18: _o2_spec(0x18, "B2S1"),
    0x19: _o2_spec(0x19, "B2S2"),
    0x1A: _o2_spec(0x1A, "B2S3"),
    0x1B: _o2_spec(0x1B, "B2S4"),
    0x1F: SensorSpec(0x1F, "Run time since engine start", "s", 2, _decode_identity),
    0x2F: SensorSpec(0x2F, "Fuel tank level", "%", 1, _decode_percent_255),
    0x42: SensorSpec(
        0x42,
        "Control module voltage",
        "V",
        2,
        _decode_battery_voltage,
    ),
    0x46: SensorSpec(0x46, "Ambient air temperature", "°C", 1, _decode_offset_40),
    0x5C: SensorSpec(0x5C, "Engine oil temperature", "°C", 1, _decode_offset_40),
}


# ---------------------------------------------------------------------------
# Public decoding / parsing helpers
# ---------------------------------------------------------------------------


def decode_pid(pid: int, raw: int) -> float:
    """Decode a raw integer value for ``pid`` via :data:`SENSOR_CATALOG`.

    Thin wrapper so callers don't have to reach into the catalog dict
    directly. Raises :class:`ValueError` when ``pid`` is not in the
    catalog — i.e. the PID is not one Phase 141 knows how to decode.

    Parameters
    ----------
    pid:
        OBD-II Mode 01 PID (0-255). Must be a catalog entry.
    raw:
        Pre-assembled integer returned by
        :meth:`~motodiag.hardware.protocols.base.ProtocolAdapter.read_pid`.

    Returns
    -------
    float
        Decoded value in the spec's :attr:`~SensorSpec.unit`.
    """
    try:
        spec = SENSOR_CATALOG[pid]
    except KeyError:
        raise ValueError(
            f"Unknown PID 0x{pid:02X} — not in SENSOR_CATALOG"
        ) from None
    return spec.decode(raw)


def parse_pid_list(spec: str) -> List[int]:
    """Parse a comma-separated PID spec into a deduplicated list of ints.

    Accepts a mix of hex (``"0x0C"``) and decimal (``"17"``) tokens,
    trims whitespace, enforces the 0-255 byte range, and deduplicates
    while preserving first-seen order. Empty input (or input that is
    only whitespace and commas) is treated as invalid.

    Parameters
    ----------
    spec:
        Raw CLI value for ``--pids``, e.g.
        ``"0x0C,0x05,17,0x42"``.

    Returns
    -------
    list[int]
        Deduplicated list of PIDs in their original order.

    Raises
    ------
    click.ClickException
        On empty input, unparsable tokens, or out-of-range values.
        The message names the offending token so the mechanic can fix
        their flag.
    """
    if spec is None or not spec.strip():
        raise click.ClickException(
            "--pids must be a non-empty comma-separated list "
            "(e.g. --pids 0x0C,0x05,0x42)"
        )
    seen: set[int] = set()
    result: List[int] = []
    for raw_token in spec.split(","):
        token = raw_token.strip()
        if not token:
            # Skip empty parts (trailing comma) — but only if we eventually
            # produce at least one PID. An all-empty spec is caught above.
            continue
        try:
            value = int(token, 16) if token.lower().startswith("0x") else int(token)
        except ValueError:
            raise click.ClickException(
                f"--pids: invalid token {token!r} — use hex (0x0C) "
                "or decimal (12)"
            ) from None
        if not (0 <= value <= 255):
            raise click.ClickException(
                f"--pids: {token!r} out of range — PIDs must be 0-255"
            )
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    if not result:
        raise click.ClickException(
            "--pids must be a non-empty comma-separated list "
            "(e.g. --pids 0x0C,0x05,0x42)"
        )
    return result


# ---------------------------------------------------------------------------
# SensorReading — Pydantic v2 model
# ---------------------------------------------------------------------------


_PID_HEX_RE = re.compile(r"^0x[0-9A-F]{2}$")


class SensorReading(BaseModel):
    """One cell of a single :class:`SensorStreamer` poll-tick.

    A list of readings (one per requested PID) is yielded by
    :meth:`SensorStreamer.iter_readings` on every poll cycle. The CLI
    renderer reads exactly these fields; downstream consumers (Phase
    142 log command, Phase 143 dashboard) read the same shape.

    Three statuses capture every outcome of a single PID read:

    - ``ok`` — adapter returned an int, decoded cleanly.
      :attr:`value` and :attr:`raw` are populated.
    - ``unsupported`` — adapter returned ``None`` or the PID is not in
      the catalog. :attr:`value` and :attr:`raw` are both ``None``.
    - ``timeout`` — adapter raised
      :class:`~motodiag.hardware.protocols.exceptions.TimeoutError`.
      :attr:`value` and :attr:`raw` are both ``None``. The next tick
      will retry the PID.

    The ``value is None iff status != "ok"`` invariant is enforced by
    :meth:`_check_value_status_coherence` so downstream code never has
    to write defensive null-checks.
    """

    pid: int = Field(ge=0, le=255, description="OBD-II Mode 01 PID (0-255)")
    pid_hex: str = Field(
        description="Uppercase hex form, e.g. '0x0C'. Enforced by regex.",
    )
    name: str = Field(description="Human-readable sensor name.")
    value: Optional[float] = Field(
        default=None,
        description=(
            "Decoded value in :attr:`unit`. ``None`` for unsupported or "
            "timeout readings."
        ),
    )
    unit: str = Field(
        description=(
            "Physical unit string (e.g. 'rpm', '°C'). Empty string for "
            "non-catalog PIDs surfaced as ``unsupported``."
        ),
    )
    raw: Optional[int] = Field(
        default=None,
        description="Pre-decode integer from adapter. ``None`` on non-ok.",
    )
    captured_at: datetime = Field(
        description="UTC timestamp when the adapter returned (or timed out).",
    )
    status: Literal["ok", "unsupported", "timeout"] = Field(
        description=(
            "Reading outcome: ``ok`` (decoded), ``unsupported`` (ECU "
            "or catalog declined), or ``timeout`` (adapter raised)."
        ),
    )

    @field_validator("pid_hex")
    @classmethod
    def _check_pid_hex_format(cls, value: str) -> str:
        """Reject lowercase or malformed hex strings.

        A strict uppercase form (``"0x0C"``, not ``"0x0c"``) keeps the
        CSV column headers and log lines visually consistent — OBD-II
        PIDs are conventionally rendered in uppercase hex.
        """
        if not _PID_HEX_RE.match(value):
            raise ValueError(
                f"pid_hex {value!r} must match 0xNN (uppercase hex byte)"
            )
        return value

    @model_validator(mode="after")
    def _check_value_status_coherence(self) -> "SensorReading":
        """Enforce ``value is None iff status != 'ok'``.

        Catches invariant violations at construction time rather than
        letting them leak into the CSV writer or the Rich table, which
        both trust the invariant when rendering.
        """
        if self.status == "ok" and self.value is None:
            raise ValueError(
                "SensorReading with status='ok' must have a non-None value"
            )
        if self.status != "ok" and self.value is not None:
            raise ValueError(
                f"SensorReading with status={self.status!r} must have "
                "value=None"
            )
        return self


# ---------------------------------------------------------------------------
# SensorStreamer — one-shot polling generator
# ---------------------------------------------------------------------------


def _default_clock() -> datetime:
    """UTC timestamp factory. Separate function so tests can replace it."""
    return datetime.now(timezone.utc)


class SensorStreamer:
    """Polls a fixed PID list on an adapter at a configurable rate.

    Designed as a one-shot generator: calling
    :meth:`iter_readings` twice on the same instance is a bug
    (would overlap two poll sequences on one adapter) and raises
    :class:`RuntimeError`. Consumers who need to re-poll construct a
    new :class:`SensorStreamer`.

    Parameters
    ----------
    adapter:
        A connected
        :class:`~motodiag.hardware.protocols.base.ProtocolAdapter`.
        The streamer never calls ``connect()``/``disconnect()`` — the
        :class:`~motodiag.hardware.connection.HardwareSession`
        ``with`` block owns lifecycle.
    pids:
        List of PIDs to poll every tick. Order is preserved in each
        yielded list.
    hz:
        Poll rate in ticks-per-second. The streamer sleeps
        ``1 / hz`` seconds after yielding each tick. Must be > 0; the
        CLI layer enforces the 10 Hz ceiling before this class sees it.
    sleep:
        Injectable sleep function — defaults to :func:`time.sleep`,
        tests pass a :class:`unittest.mock.Mock` to assert the throttle
        without actually waiting.
    clock:
        Injectable UTC-timestamp function — defaults to ``datetime.now``
        in the UTC timezone. Tests pass a ``lambda`` returning a frozen
        :class:`datetime` to keep output deterministic.
    """

    def __init__(
        self,
        adapter,
        pids: List[int],
        hz: float = 2.0,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], datetime] = _default_clock,
    ) -> None:
        if hz <= 0:
            raise ValueError(f"hz must be > 0 (got {hz!r})")
        self._adapter = adapter
        self._pids: List[int] = list(pids)
        self._hz: float = float(hz)
        self._sleep = sleep
        self._clock = clock
        # One-shot guard. Flipped to True on the first call to
        # iter_readings so a second call raises loudly.
        self._iter_started: bool = False

    @property
    def pids(self) -> List[int]:
        """Return a defensive copy of the PID list."""
        return list(self._pids)

    def iter_readings(self) -> Iterator[List[SensorReading]]:
        """Yield one list of :class:`SensorReading` per poll tick.

        The generator runs indefinitely — the caller (typically the
        CLI's :func:`~motodiag.cli.hardware._run_stream`) decides when
        to break (duration cap, Ctrl+C, ECU silence). Sleeps
        ``1 / hz`` seconds *after* each yield so consumers that break
        immediately don't eat a pointless wait.

        Raises
        ------
        RuntimeError
            If called more than once on the same instance (one-shot).
        ConnectionError
            Propagated unchanged from the adapter — CLI renders a red
            "ECU went silent" panel and exits 1.
        ProtocolError
            Any other protocol-layer error besides
            :class:`TimeoutError` (which is caught per-PID and turned
            into a degraded reading). Propagated unchanged.
        """
        if self._iter_started:
            raise RuntimeError(
                "SensorStreamer.iter_readings() is one-shot — construct a "
                "new SensorStreamer to poll again"
            )
        self._iter_started = True
        while True:
            tick: List[SensorReading] = []
            for pid in self._pids:
                tick.append(self._read_one(pid))
            yield tick
            # Sleep after yield so ``break`` after the first tick is fast.
            self._sleep(1.0 / self._hz)

    def _read_one(self, pid: int) -> SensorReading:
        """Read one PID and turn the outcome into a :class:`SensorReading`.

        Four mutually-exclusive branches:

        1. Unknown PID (not in catalog) → we still call ``read_pid``
           to let the adapter decide, but build the reading around a
           synthetic "PID 0xNN" name + empty unit. Any adapter success
           still yields ``status="unsupported"`` because we have no
           decoder — a future phase could graduate these to ``ok`` once
           a decoder is registered.
        2. ``TimeoutError`` → ``status="timeout"``. Not re-raised —
           next tick retries.
        3. ``adapter.read_pid`` returns ``None`` → ``status="unsupported"``.
        4. ``adapter.read_pid`` returns ``int`` → decode via catalog
           into ``status="ok"``.

        Any other :class:`ProtocolError` (notably
        :class:`ConnectionError`) bubbles out of this method, breaking
        the outer poll loop. The CLI renders a red failure panel.
        """
        spec = SENSOR_CATALOG.get(pid)
        try:
            raw = self._adapter.read_pid(pid)
        except ProtocolTimeoutError:
            return SensorReading(
                pid=pid,
                pid_hex=f"0x{pid:02X}",
                name=spec.name if spec else f"PID 0x{pid:02X}",
                value=None,
                unit=spec.unit if spec else "",
                raw=None,
                captured_at=self._clock(),
                status="timeout",
            )
        # ConnectionError and any other ProtocolError propagate — we
        # don't mask them into a cell-level status because the adapter
        # is likely unusable.

        captured = self._clock()
        if spec is None:
            # Unknown PID: whatever the adapter returned, we can't
            # decode — flag as unsupported so the table shows an em-dash
            # and the user knows Phase 141 doesn't cover this code yet.
            return SensorReading(
                pid=pid,
                pid_hex=f"0x{pid:02X}",
                name=f"PID 0x{pid:02X}",
                value=None,
                unit="",
                raw=None,
                captured_at=captured,
                status="unsupported",
            )
        if raw is None:
            return SensorReading(
                pid=pid,
                pid_hex=f"0x{pid:02X}",
                name=spec.name,
                value=None,
                unit=spec.unit,
                raw=None,
                captured_at=captured,
                status="unsupported",
            )
        value = spec.decode(raw)
        return SensorReading(
            pid=pid,
            pid_hex=f"0x{pid:02X}",
            name=spec.name,
            value=float(value),
            unit=spec.unit,
            raw=raw,
            captured_at=captured,
            status="ok",
        )


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "SensorSpec",
    "SENSOR_CATALOG",
    "decode_pid",
    "parse_pid_list",
    "SensorReading",
    "SensorStreamer",
]
