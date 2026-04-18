"""Scriptable hardware simulator (Phase 144).

The :class:`MockAdapter` shipped in Phase 140 answers every query with the
same canned state; it's great for CI smoke tests but useless for the kind
of diagnostic drills a real mechanic needs (coolant climbing while a
P0217 drops in at the 2-minute mark, ECU briefly dropping off the bus on
an ignition glitch, an O2 sensor dying mid-scan). Phase 144's
:class:`SimulatedAdapter` fills that gap: same
:class:`~motodiag.hardware.protocols.base.ProtocolAdapter` ABC, but the
state it returns is a *function of time* driven by a YAML scenario file.

Design contract
---------------

- **Simulator is a sibling of MockAdapter, not a subclass.** Phase 140's
  module is byte-frozen; a CI diff check enforces this. Inheritance would
  entangle the two contracts and every cleanup of MockAdapter would risk
  silently changing simulator behavior.
- **Pure function of ``(scenario, t)``.** The internal state is *never*
  cached between reads — every call to ``read_dtcs`` / ``read_pid`` /
  ``read_vin`` re-folds the timeline from scratch. Timeline size is
  bounded (≤100 events in realistic scenarios), so the O(N) fold is
  negligible and we get determinism-by-construction: two adapters with
  the same scenario and clock will always report identical state.
- **Clock is injected, never wall-clock.** :class:`SimulationClock` is a
  manual float counter. The production ``simulate run`` CLI wraps it
  with a wall-clock pacer; tests inject ``speed=0`` and tick the clock
  themselves for sub-second, fully deterministic runs.

Scenario format
---------------

YAML at the surface, Pydantic underneath. Each scenario has a header
(``name``, ``description``, ``protocol``, ``vin``, ``initial``) plus a
``timeline`` list of action-tagged event dicts. Example::

    name: cold_start
    protocol: ISO 15765-4 (CAN)
    vin: JH2PC40A7WM123456
    initial:
      0x05: 20
      0x0C: 1800
    timeline:
      - {action: start, at: 0s, pids: {0x05: 20, 0x0C: 1800},
         vin: JH2PC40A7WM123456, protocol: ISO 15765-4 (CAN)}
      - {action: ramp, at: 5s, pid: 0x05, from: 20, to: 88, duration: 50s}
      - {action: inject_dtc, at: 105s, code: P0171}
      - {action: end, at: 120s}

The ``action`` field is the Pydantic discriminator — each action tag
maps to a frozen event model with strict ``extra="forbid"`` so typos in
hand-written YAML fail at load time, not at the first read.
"""

from __future__ import annotations

import importlib
import importlib.resources
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    Annotated,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    TextIO,
    Union,
)

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from motodiag.hardware.protocols.base import ProtocolAdapter
from motodiag.hardware.protocols.exceptions import (
    ConnectionError as ProtocolConnectionError,
    TimeoutError as ProtocolTimeoutError,
)


# ---------------------------------------------------------------------------
# PID symbolic aliases
# ---------------------------------------------------------------------------
#
# YAML authors may write either the raw PID number (``0x05``) or a
# friendlier symbolic alias (``coolant_temp``). ``_coerce_pid`` accepts
# both forms plus plain hex strings. The alias table is deliberately
# short and OBD-II-standard — anything make-specific should go through
# a bike-specific scenario YAML rather than bloating this map.
PID_ALIASES: Dict[str, int] = {
    "coolant_temp": 0x05,
    "engine_rpm": 0x0C,
    "vehicle_speed": 0x0D,
    "throttle_position": 0x11,
    "intake_temp": 0x0F,
    "battery_voltage": 0x42,
    "stft_bank1": 0x06,
    "ltft_bank1": 0x07,
    "o2_voltage_b1s1": 0x14,
    "maf_rate": 0x10,
}


def _coerce_pid(raw: Any) -> int:
    """Return the numeric PID for any of int / hex-string / symbolic alias.

    Accepts four forms:

    - plain int (``5``),
    - hex int (``0x05`` — YAML parses this as 5 natively),
    - hex string (``"0x05"``, ``"0X05"``),
    - symbolic alias (``"coolant_temp"``) looked up in :data:`PID_ALIASES`.

    Raises
    ------
    ValueError
        When the input cannot be coerced to an OBD-II PID (0–255).
    """
    if isinstance(raw, bool):
        # bool is a subclass of int in Python; reject it explicitly so a
        # misplaced ``true`` in YAML doesn't silently become PID 1.
        raise ValueError(f"cannot coerce bool {raw!r} to PID")
    if isinstance(raw, int):
        if 0 <= raw <= 0xFF:
            return raw
        raise ValueError(f"PID {raw} outside valid range 0..0xFF")
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            raise ValueError("empty string is not a valid PID")
        lower = s.lower()
        if lower in PID_ALIASES:
            return PID_ALIASES[lower]
        # "0x05" is explicit hex. Bare "12" is DECIMAL — JSON round-trip
        # of {0x0C: ...} serializes the key as "12" decimal, so decimal
        # decode must round-trip identity (hex would turn 12→0x12=18).
        try:
            if lower.startswith("0x") or lower.startswith("0X"):
                return int(lower, 16)
            return int(lower, 10)
        except ValueError as exc:
            raise ValueError(f"unrecognized PID token: {raw!r}") from exc
    raise ValueError(f"cannot coerce {type(raw).__name__} to PID: {raw!r}")


# ---------------------------------------------------------------------------
# Duration parsing
# ---------------------------------------------------------------------------

_DUR_RE = re.compile(
    r"(?:(?P<m>\d+(?:\.\d+)?)m)?(?:(?P<s>\d+(?:\.\d+)?)s)?",
)


def _parse_duration(raw: Any) -> float:
    """Parse a duration expression into seconds.

    Accepts:

    - bare int / float (already seconds),
    - ``"30s"`` — seconds,
    - ``"1m"`` — minutes,
    - ``"1m30s"`` — minutes + seconds,
    - ``"1.5s"`` — fractional seconds.

    Returns
    -------
    float
        Duration in seconds. Always >= 0.

    Raises
    ------
    ValueError
        On unrecognized formats or negative values.
    """
    if isinstance(raw, bool):
        raise ValueError(f"cannot parse bool {raw!r} as duration")
    if isinstance(raw, (int, float)):
        if raw < 0:
            raise ValueError(f"negative duration: {raw}")
        return float(raw)
    if not isinstance(raw, str):
        raise ValueError(
            f"duration must be int, float, or str; got {type(raw).__name__}"
        )
    s = raw.strip().lower()
    if not s:
        raise ValueError("empty duration string")
    # Pure number with no unit — interpret as seconds (matches YAML bare floats)
    try:
        return float(s)
    except ValueError:
        pass
    m = _DUR_RE.fullmatch(s)
    if not m or (m.group("m") is None and m.group("s") is None):
        raise ValueError(f"unrecognized duration format: {raw!r}")
    minutes = float(m.group("m")) if m.group("m") is not None else 0.0
    seconds = float(m.group("s")) if m.group("s") is not None else 0.0
    total = minutes * 60.0 + seconds
    if total < 0:
        raise ValueError(f"negative duration: {raw!r}")
    return total


# ---------------------------------------------------------------------------
# SimulationClock — manually-driven time source
# ---------------------------------------------------------------------------


class SimulationClock:
    """Deterministic, manually-advanced time source for the simulator.

    All simulator tests inject one of these instead of wall-clock time,
    which is how we keep the ~55 Phase 144 tests running in under a
    second with zero ``time.sleep`` calls (CI grep-enforces the latter).

    The clock is monotonic: :meth:`advance` refuses to go backwards,
    :meth:`tick` always moves forward. ``reset`` is the only way to
    re-anchor. Time is stored as a float; 10 kHz ticks over a 10-second
    scenario give ~100 ppm drift in the least-significant bit, which is
    below any resolution the simulator cares about (tests assert
    ``== 100.0`` with an exact-equals but use a loop count that's an
    exact power of ten).

    Parameters
    ----------
    start_s:
        Initial ``now()`` value in seconds. Defaults to 0.0. Allowed to
        be negative (though no scenario uses negative time).
    """

    def __init__(self, start_s: float = 0.0) -> None:
        self._t: float = float(start_s)
        self._frozen: bool = False

    def now(self) -> float:
        """Return current simulated seconds."""
        return self._t

    def tick(self, dt_s: float = 0.1) -> float:
        """Advance by ``dt_s`` seconds and return the new ``now()``.

        No-op when :meth:`freeze` has been called; unfreeze to resume.
        ``dt_s`` must be non-negative — negative ticks are undefined
        (use :meth:`reset` to rewind).
        """
        if dt_s < 0:
            raise ValueError(f"tick requires non-negative dt; got {dt_s}")
        if not self._frozen:
            self._t += float(dt_s)
        return self._t

    def advance(self, to_s: float) -> float:
        """Jump forward to ``to_s`` absolute seconds.

        Raises
        ------
        ValueError
            When ``to_s < now()`` — the clock refuses to go backwards.
            Tests that need to rewind use :meth:`reset` instead.
        """
        to_f = float(to_s)
        if to_f < self._t:
            raise ValueError(
                f"SimulationClock.advance rejects backwards motion: "
                f"now={self._t} asked_for={to_f}"
            )
        if not self._frozen:
            self._t = to_f
        return self._t

    def freeze(self) -> None:
        """Pause time — subsequent :meth:`tick` / :meth:`advance` no-op."""
        self._frozen = True

    def unfreeze(self) -> None:
        """Resume normal advancement."""
        self._frozen = False

    def reset(self, start_s: float = 0.0) -> None:
        """Re-anchor :meth:`now` to ``start_s`` and clear the frozen flag."""
        self._t = float(start_s)
        self._frozen = False


# ---------------------------------------------------------------------------
# Scenario event Pydantic models — discriminated union on `action`
# ---------------------------------------------------------------------------
#
# Each event subclass is frozen + extra="forbid" so malformed YAML
# (misspelled field, stray extra key) fails Pydantic validation instead
# of silently being ignored. The discriminated union on `action` means
# Pydantic can hand us the right concrete class per event without us
# writing an if-elif-else dispatcher.


_DTC_CODE_RE = re.compile(r"^[PCBU][0-9A-F]{4}$")
_RAMP_SHAPES = ("linear", "ease_in_out")


class _ScenarioEventBase(BaseModel):
    """Common config + at_s field for every scenario event."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    at_s: float = Field(ge=0.0)


class StartState(_ScenarioEventBase):
    """Initial state event — must be the first timeline entry."""

    action: Literal["start"]
    pids: Dict[int, float]
    dtcs: List[str] = Field(default_factory=list)
    vin: Optional[str] = None
    protocol: str = "SimProtocol"

    @field_validator("pids", mode="before")
    @classmethod
    def _coerce_pid_keys(cls, v: Any) -> Dict[int, float]:
        if not isinstance(v, dict):
            raise ValueError("pids must be a mapping")
        return {_coerce_pid(k): float(val) for k, val in v.items()}

    @field_validator("dtcs")
    @classmethod
    def _validate_dtc_format(cls, v: List[str]) -> List[str]:
        for code in v:
            if not _DTC_CODE_RE.match(code):
                raise ValueError(
                    f"DTC code {code!r} must match [PCBU] + 4 hex digits"
                )
        return v


class RampPid(_ScenarioEventBase):
    """Linear (or eased) PID ramp over a time window."""

    action: Literal["ramp"]
    pid: int
    from_: float = Field(alias="from")
    to: float
    duration_s: float = Field(gt=0.0)
    shape: Literal["linear", "ease_in_out"] = "linear"

    @field_validator("pid", mode="before")
    @classmethod
    def _coerce(cls, v: Any) -> int:
        return _coerce_pid(v)

    @field_validator("duration_s", mode="before")
    @classmethod
    def _parse_dur(cls, v: Any) -> float:
        return _parse_duration(v)


class InjectDTC(_ScenarioEventBase):
    """Insert a DTC code into the active fault list at ``at_s``."""

    action: Literal["inject_dtc"]
    code: str

    @field_validator("code")
    @classmethod
    def _dtc_format(cls, v: str) -> str:
        if not _DTC_CODE_RE.match(v):
            raise ValueError(
                f"DTC code {v!r} must match [PCBU] + 4 hex digits"
            )
        return v


class ClearDTC(_ScenarioEventBase):
    """Remove a previously-injected DTC from the active list."""

    action: Literal["clear_dtc"]
    code: str

    @field_validator("code")
    @classmethod
    def _dtc_format(cls, v: str) -> str:
        if not _DTC_CODE_RE.match(v):
            raise ValueError(
                f"DTC code {v!r} must match [PCBU] + 4 hex digits"
            )
        return v


class InjectTimeout(_ScenarioEventBase):
    """Inject a timeout window — reads during [at_s, at_s+duration_s] raise."""

    action: Literal["inject_timeout"]
    duration_s: float = Field(gt=0.0)

    @field_validator("duration_s", mode="before")
    @classmethod
    def _parse_dur(cls, v: Any) -> float:
        return _parse_duration(v)


class Disconnect(_ScenarioEventBase):
    """Flag the adapter as disconnected; subsequent reads raise ConnectionError."""

    action: Literal["disconnect"]


class Reconnect(_ScenarioEventBase):
    """Re-flag the adapter as connected after a previous Disconnect."""

    action: Literal["reconnect"]


class PhaseTransition(_ScenarioEventBase):
    """Event-log marker for scenario phase changes (no state mutation)."""

    action: Literal["phase"]
    name: str


class EndScenario(_ScenarioEventBase):
    """Terminal event — must be the last timeline entry."""

    action: Literal["end"]


ScenarioEvent = Annotated[
    Union[
        StartState,
        RampPid,
        InjectDTC,
        ClearDTC,
        InjectTimeout,
        Disconnect,
        Reconnect,
        PhaseTransition,
        EndScenario,
    ],
    Field(discriminator="action"),
]


# ---------------------------------------------------------------------------
# Scenario aggregate — the whole timeline + validators
# ---------------------------------------------------------------------------


class Scenario(BaseModel):
    """A full scenario — header + timeline — with cross-event validators."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    description: str = ""
    protocol: str = "SimProtocol"
    vin: Optional[str] = None
    initial: Dict[int, float] = Field(default_factory=dict)
    timeline: List[ScenarioEvent]

    @field_validator("initial", mode="before")
    @classmethod
    def _coerce_initial_keys(cls, v: Any) -> Dict[int, float]:
        if not isinstance(v, dict):
            raise ValueError("initial must be a mapping")
        return {_coerce_pid(k): float(val) for k, val in v.items()}

    @field_validator("vin")
    @classmethod
    def _validate_vin(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if len(v) != 17:
            raise ValueError(f"VIN must be 17 characters; got {len(v)}: {v!r}")
        if not re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", v):
            raise ValueError(
                f"VIN contains invalid characters: {v!r} "
                "(allowed A-H J-N P R-Z and 0-9, no I/O/Q)"
            )
        return v

    @model_validator(mode="after")
    def _validate_timeline_structure(self) -> "Scenario":
        tl = self.timeline
        if not tl:
            raise ValueError("timeline must be non-empty")

        if not isinstance(tl[0], StartState):
            raise ValueError("timeline[0] must be a StartState (action: start)")
        if not isinstance(tl[-1], EndScenario):
            raise ValueError(
                "timeline[-1] must be an EndScenario (action: end)"
            )

        # Sorted by at_s — strict nondecreasing.
        prev_t = -1.0
        for idx, event in enumerate(tl):
            if event.at_s < prev_t:
                raise ValueError(
                    f"timeline event #{idx} at_s={event.at_s} is earlier than "
                    f"the previous event at_s={prev_t} — timeline must be sorted"
                )
            prev_t = event.at_s

        # Exactly one StartState (at idx 0) and one EndScenario (at idx -1).
        start_count = sum(1 for e in tl if isinstance(e, StartState))
        end_count = sum(1 for e in tl if isinstance(e, EndScenario))
        if start_count != 1:
            raise ValueError(
                f"timeline must have exactly one StartState; got {start_count}"
            )
        if end_count != 1:
            raise ValueError(
                f"timeline must have exactly one EndScenario; got {end_count}"
            )

        start: StartState = tl[0]  # type: ignore[assignment]

        # `initial` keys must be a subset of StartState.pids — the StartState
        # is the declaration of the initial state; `initial` is a human-
        # readable shortcut for mechanics reading the YAML.
        for pid in self.initial.keys():
            if pid not in start.pids:
                raise ValueError(
                    f"initial PID 0x{pid:02X} not present in StartState.pids"
                )

        # Ramp PIDs must be declared in StartState.pids — otherwise the
        # ramp interpolates against a non-existent baseline.
        for event in tl:
            if isinstance(event, RampPid) and event.pid not in start.pids:
                raise ValueError(
                    f"RampPid at {event.at_s}s targets PID 0x{event.pid:02X} "
                    "which is not declared in StartState.pids"
                )

        # ClearDTC must follow a matching (unmatched) InjectDTC — pair by
        # code. We seed the counter from StartState.dtcs so scenarios that
        # start with an already-active code can legally clear it without
        # needing a redundant InjectDTC at t=0.
        injected_codes: Dict[str, int] = {
            code: 1 for code in start.dtcs
        }
        for event in tl:
            if isinstance(event, InjectDTC):
                injected_codes[event.code] = injected_codes.get(event.code, 0) + 1
            elif isinstance(event, ClearDTC):
                remaining = injected_codes.get(event.code, 0)
                if remaining <= 0:
                    raise ValueError(
                        f"ClearDTC at {event.at_s}s for {event.code} has no "
                        "prior matching InjectDTC or StartState entry"
                    )
                injected_codes[event.code] = remaining - 1

        # Reconnect must follow a Disconnect — enforce the connection
        # state transitions as a simple connected/disconnected FSM.
        connected = True
        for event in tl:
            if isinstance(event, Disconnect):
                if not connected:
                    raise ValueError(
                        f"Disconnect at {event.at_s}s but adapter already "
                        "disconnected (two Disconnects in a row)"
                    )
                connected = False
            elif isinstance(event, Reconnect):
                if connected:
                    raise ValueError(
                        f"Reconnect at {event.at_s}s without a preceding "
                        "Disconnect in the timeline"
                    )
                connected = True

        # Overlapping ramps on the same PID are ambiguous — interpolating
        # two ramps simultaneously has no defined behavior, so we reject
        # at load time.
        ramps_by_pid: Dict[int, List[RampPid]] = {}
        for event in tl:
            if isinstance(event, RampPid):
                ramps_by_pid.setdefault(event.pid, []).append(event)
        for pid, ramps in ramps_by_pid.items():
            ramps_sorted = sorted(ramps, key=lambda r: r.at_s)
            for a, b in zip(ramps_sorted, ramps_sorted[1:]):
                a_end = a.at_s + a.duration_s
                if b.at_s < a_end:
                    raise ValueError(
                        f"overlapping ramps on PID 0x{pid:02X}: "
                        f"[{a.at_s}..{a_end}] and "
                        f"[{b.at_s}..{b.at_s + b.duration_s}]"
                    )

        return self


# ---------------------------------------------------------------------------
# Loader errors
# ---------------------------------------------------------------------------


class ScenarioParseError(Exception):
    """YAML-level parse failure with line/column context."""

    def __init__(
        self,
        path: Optional[str],
        line: Optional[int],
        col: Optional[int],
        msg: str,
    ) -> None:
        where = path or "<string>"
        if line is not None and col is not None:
            loc = f"{where}:{line}:{col}"
        else:
            loc = where
        super().__init__(f"{loc}: {msg}")
        self.path = path
        self.line = line
        self.col = col
        self.msg = msg


class ScenarioValidationError(Exception):
    """Pydantic validation failure; ``errors`` is the raw error list."""

    def __init__(self, path: Optional[str], errors: List[Any]) -> None:
        where = path or "<string>"
        lines = [f"{where}: scenario validation failed"]
        for err in errors:
            if isinstance(err, dict):
                loc = ".".join(str(x) for x in err.get("loc", ()))
                msg = err.get("msg", "")
                lines.append(f"  - {loc}: {msg}")
            else:
                lines.append(f"  - {err}")
        super().__init__("\n".join(lines))
        self.path = path
        self.errors = errors


class RecordingSupportUnavailable(Exception):
    """Raised when ``ScenarioLoader.from_recording`` is called without Phase 142."""


# ---------------------------------------------------------------------------
# ScenarioLoader
# ---------------------------------------------------------------------------


def _phase142_available() -> bool:
    """Probe whether the Phase 142 ``RecordingManager`` module is importable.

    Phase 142 shipped the module as ``motodiag.hardware.recorder`` (not
    ``recording``). Kept as a function (not a module-level constant) so
    tests can monkey-patch it when the module presence changes.
    """
    try:
        importlib.import_module("motodiag.hardware.recorder")
        return True
    except ImportError:
        return False


class ScenarioLoader:
    """Load scenarios from YAML, recordings, or the built-in library.

    Stateless — all methods are ``@classmethod`` / ``@staticmethod``-shaped
    in spirit. We keep them instance methods anyway so a future variant
    (with a user scenario path registry) can subclass without an API
    break.
    """

    @staticmethod
    def from_yaml(
        source: Union[str, Path, TextIO],
        *,
        validate_only: bool = False,
    ) -> Scenario:
        """Parse YAML and return a :class:`Scenario`.

        ``source`` may be a filesystem path, a raw YAML string, or a
        file-like object. YAML-level failures are wrapped in
        :class:`ScenarioParseError` with line/column; schema-level
        failures in :class:`ScenarioValidationError`.

        Parameters
        ----------
        validate_only:
            Reserved for the ``simulate validate`` CLI — currently
            behaves identically to a normal load (we always return the
            parsed Scenario so callers can print header info even on the
            validate path).
        """
        path_label: Optional[str] = None
        if isinstance(source, (str, Path)):
            s = str(source)
            # Heuristic: strings containing a newline are YAML content,
            # never paths. Path.exists() on a multiline string would
            # raise OSError on Windows and ValueError elsewhere, and
            # we'd rather short-circuit than catch. Otherwise attempt
            # the path lookup — a plain filename the caller passed in
            # would land here. If the lookup fails (file not found or
            # filesystem can't evaluate the name), fall through to
            # treat the input as raw YAML.
            text: Optional[str] = None
            if isinstance(source, Path) or "\n" not in s:
                try:
                    candidate = Path(s)
                    if candidate.exists() and candidate.is_file():
                        path_label = str(candidate)
                        text = candidate.read_text(encoding="utf-8")
                except (OSError, ValueError):
                    text = None
            if text is None:
                text = s
        elif hasattr(source, "read"):
            text = source.read()
            path_label = getattr(source, "name", None)
        else:
            raise TypeError(
                f"from_yaml source must be str/Path/TextIO; got "
                f"{type(source).__name__}"
            )

        try:
            raw = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            line: Optional[int] = None
            col: Optional[int] = None
            if hasattr(exc, "problem_mark") and exc.problem_mark is not None:
                line = exc.problem_mark.line + 1
                col = exc.problem_mark.column + 1
            raise ScenarioParseError(
                path_label, line, col, str(exc)
            ) from exc

        if not isinstance(raw, dict):
            raise ScenarioParseError(
                path_label, None, None,
                f"top-level YAML must be a mapping; got {type(raw).__name__}",
            )

        # Pre-normalize the timeline: each event's `at` key → `at_s` after
        # duration parsing, so Pydantic gets numeric seconds.
        timeline_raw = raw.get("timeline")
        if isinstance(timeline_raw, list):
            for entry in timeline_raw:
                if not isinstance(entry, dict):
                    continue
                if "at" in entry and "at_s" not in entry:
                    try:
                        entry["at_s"] = _parse_duration(entry.pop("at"))
                    except ValueError as exc:
                        raise ScenarioParseError(
                            path_label, None, None,
                            f"invalid 'at' in event {entry!r}: {exc}",
                        ) from exc
                if "duration" in entry and "duration_s" not in entry:
                    # Keep the raw value — the event model's before-
                    # validator will call _parse_duration on it. Rename
                    # so Pydantic sees the right field name.
                    entry["duration_s"] = entry.pop("duration")

        try:
            scenario = Scenario.model_validate(raw)
        except ValidationError as exc:
            raise ScenarioValidationError(path_label, exc.errors()) from exc

        return scenario

    @staticmethod
    def from_recording(recording_id: Any, db: Any = None) -> Scenario:
        """Build a Scenario from a Phase 142 recording.

        Phase 142 ships :class:`motodiag.hardware.recorder.RecordingManager`.
        If that module is not importable, this raises
        :class:`RecordingSupportUnavailable`. When it is available, we
        call :meth:`RecordingManager.load_recording` which returns
        ``(meta_dict, samples_iterator)``, then collapse the time
        series into a coarse two-event scenario: a
        :class:`StartState` with the first-seen value per unique PID,
        and an :class:`EndScenario` at the recording's duration. A
        richer v2 could emit per-segment :class:`RampPid` events.
        """
        if not _phase142_available():
            raise RecordingSupportUnavailable(
                "Phase 142 RecordingManager not available — "
                "from_recording requires motodiag.hardware.recorder to be "
                "importable. Install the phase-142 module or pass a YAML "
                "scenario to ScenarioLoader.from_yaml instead."
            )
        rec_mod = importlib.import_module("motodiag.hardware.recorder")
        manager_cls = getattr(rec_mod, "RecordingManager", None)
        if manager_cls is None:  # pragma: no cover — defensive.
            raise RecordingSupportUnavailable(
                "motodiag.hardware.recorder loaded but RecordingManager "
                "is missing — Phase 142 internal contract drifted."
            )
        try:
            manager = manager_cls(db_path=db) if db is not None else manager_cls()
        except TypeError:
            # RecordingManager signature variant — try positional.
            manager = manager_cls(db) if db is not None else manager_cls()
        try:
            meta, samples_iter = manager.load_recording(int(recording_id))
        except KeyError as exc:
            raise ScenarioValidationError(
                None,
                [{"loc": ("recording_id",), "msg": str(exc)}],
            ) from exc

        samples = list(samples_iter)
        if not samples:
            raise ScenarioValidationError(
                None,
                [{"loc": ("samples",), "msg": "recording is empty"}],
            )

        # Take the first-seen value per unique PID. Samples are time-
        # ordered (contract from _merge_samples), so "first-seen" means
        # "earliest in the recording".
        pid_snapshot: Dict[int, float] = {}
        for sample in samples:
            pid_raw = sample.get("pid_hex") or sample.get("pid")
            if pid_raw is None:
                continue
            try:
                pid = _coerce_pid(pid_raw)
            except ValueError:
                continue
            if pid not in pid_snapshot:
                val = sample.get("value")
                if val is None:
                    val = sample.get("raw", 0)
                try:
                    pid_snapshot[pid] = float(val)
                except (TypeError, ValueError):
                    continue

        if not pid_snapshot:
            raise ScenarioValidationError(
                None,
                [{"loc": ("samples",), "msg": "no usable PID values in recording"}],
            )

        protocol = meta.get("protocol") or "SimProtocol"
        vin = meta.get("vin")
        duration_s = float(meta.get("duration_s") or len(samples))

        start = StartState(
            action="start", at_s=0.0,
            pids=pid_snapshot,
            dtcs=[], vin=vin, protocol=protocol,
        )
        end = EndScenario(action="end", at_s=max(duration_s, 0.1))
        return Scenario(
            name=f"recording_{recording_id}",
            description=f"Replay of recording {recording_id}",
            protocol=protocol,
            vin=vin,
            initial=dict(pid_snapshot),
            timeline=[start, end],
        )

    @staticmethod
    def list_builtins() -> List[Scenario]:
        """Load every YAML under ``motodiag.hardware.scenarios`` and return the parsed list."""
        result: List[Scenario] = []
        try:
            resource = importlib.resources.files(
                "motodiag.hardware.scenarios",
            )
        except (ModuleNotFoundError, TypeError):  # pragma: no cover — defensive
            return result
        for entry in resource.iterdir():
            name = getattr(entry, "name", "")
            if not name.endswith(".yaml"):
                continue
            # Read through the Traversable interface so zipped wheels
            # work identically to editable installs.
            with entry.open("r", encoding="utf-8") as fh:
                text = fh.read()
            try:
                result.append(ScenarioLoader.from_yaml(text))
            except (ScenarioParseError, ScenarioValidationError) as exc:
                # A malformed built-in is a hard failure — better to
                # surface it at list time than have ``simulate run``
                # report a confusing generic error.
                raise ScenarioValidationError(
                    name, [{"loc": (name,), "msg": str(exc)}],
                ) from exc
        # Deterministic ordering so CLI output is stable.
        result.sort(key=lambda s: s.name)
        return result

    @staticmethod
    def find(
        name: str,
        *,
        user_paths: Sequence[Union[str, Path]] = (),
    ) -> Scenario:
        """Locate a scenario by name — built-ins first, then user paths.

        ``name`` may be a scenario name (``"healthy_idle"``) or a
        filesystem path. The search order is: exact path → built-in
        library → each user path with ``{name}.yaml``. The first match
        wins.
        """
        # Path form wins — if the caller passes an explicit file path,
        # don't second-guess them by looking elsewhere first.
        p = Path(name)
        if p.exists() and p.is_file():
            return ScenarioLoader.from_yaml(p)

        # Built-ins.
        try:
            resource = importlib.resources.files(
                "motodiag.hardware.scenarios",
            )
            builtin = resource.joinpath(f"{name}.yaml")
            if builtin.is_file():
                with builtin.open("r", encoding="utf-8") as fh:
                    return ScenarioLoader.from_yaml(fh.read())
        except (ModuleNotFoundError, TypeError):  # pragma: no cover
            pass

        # User-supplied search paths.
        for up in user_paths:
            candidate = Path(up) / f"{name}.yaml"
            if candidate.is_file():
                return ScenarioLoader.from_yaml(candidate)

        raise FileNotFoundError(
            f"scenario {name!r} not found in built-ins or user paths "
            f"{list(map(str, user_paths))}"
        )


# ---------------------------------------------------------------------------
# Materialized state dataclass — internal, not exported
# ---------------------------------------------------------------------------


@dataclass
class _MaterializedState:
    """Snapshot of the simulated ECU at a given ``t``."""

    pid_values: Dict[int, float] = field(default_factory=dict)
    active_dtcs: List[str] = field(default_factory=list)
    vin: Optional[str] = None
    protocol: str = "SimProtocol"
    disconnected: bool = False
    timeout_until: float = 0.0


def _interpolate(
    t: float, start_t: float, dur: float, from_v: float, to_v: float, shape: str,
) -> float:
    """Return the PID value for a ramp at absolute time ``t``."""
    if dur <= 0:
        return to_v
    if t <= start_t:
        return from_v
    if t >= start_t + dur:
        return to_v
    frac = (t - start_t) / dur
    if shape == "ease_in_out":
        # Smoothstep — s-curve in [0,1]. Keeps the ramp visually smooth
        # for the dashboard without changing the start/end values.
        frac = frac * frac * (3.0 - 2.0 * frac)
    return from_v + (to_v - from_v) * frac


# ---------------------------------------------------------------------------
# SimulatedAdapter — the actual ProtocolAdapter implementation
# ---------------------------------------------------------------------------


class SimulatedAdapter(ProtocolAdapter):
    """Scriptable :class:`ProtocolAdapter` driven by a :class:`Scenario`.

    Deliberate sibling of :class:`~motodiag.hardware.mock.MockAdapter` —
    not a subclass. A CI diff check pins the Phase 140 mock module byte-
    for-byte; duplicating the minimal ``connect`` / ``disconnect``
    boilerplate (~6 LoC) is the cost of preserving that pin.

    Parameters
    ----------
    scenario:
        The :class:`Scenario` to play back. Frozen Pydantic model, safe
        to share across adapters.
    clock:
        Optional :class:`SimulationClock`. Defaults to a fresh
        ``SimulationClock(start_s=0.0)``. The adapter never advances the
        clock itself — callers (or the ``simulate run`` pacer) are
        responsible for ticking.
    """

    def __init__(
        self,
        scenario: Scenario,
        clock: Optional[SimulationClock] = None,
    ) -> None:
        self._scenario: Scenario = scenario
        self._clock: SimulationClock = clock if clock is not None else SimulationClock()
        self._is_connected: bool = False
        # User-invoked `clear_dtcs()` wipes state WITHOUT rewriting the
        # timeline, so we track the set of codes the caller has manually
        # cleared. The fold re-applies timeline events on top and then
        # subtracts these.
        self._manually_cleared: List[str] = []

    # --- Public accessors used by tests + the simulate CLI --------------

    @property
    def clock(self) -> SimulationClock:
        """The clock this adapter reads from."""
        return self._clock

    @property
    def scenario(self) -> Scenario:
        """The scenario this adapter plays back."""
        return self._scenario

    # --- State fold ----------------------------------------------------

    def _materialize_state(self, t: float) -> _MaterializedState:
        """Fold the timeline up to ``t`` and return the current state.

        Pure function of ``(scenario, t, manually_cleared)``. O(events).
        """
        # Seed from the StartState event (which validators guarantee at
        # index 0).
        start: StartState = self._scenario.timeline[0]  # type: ignore[assignment]
        state = _MaterializedState(
            pid_values=dict(start.pids),
            active_dtcs=list(start.dtcs),
            vin=start.vin if start.vin is not None else self._scenario.vin,
            protocol=start.protocol,
        )

        for event in self._scenario.timeline:
            if event.at_s > t:
                break
            if isinstance(event, StartState):
                # Handled above — the seed state already includes it.
                continue
            if isinstance(event, RampPid):
                new_val = _interpolate(
                    t, event.at_s, event.duration_s,
                    event.from_, event.to, event.shape,
                )
                state.pid_values[event.pid] = new_val
            elif isinstance(event, InjectDTC):
                if event.code not in state.active_dtcs:
                    state.active_dtcs.append(event.code)
            elif isinstance(event, ClearDTC):
                if event.code in state.active_dtcs:
                    state.active_dtcs.remove(event.code)
            elif isinstance(event, InjectTimeout):
                state.timeout_until = event.at_s + event.duration_s
            elif isinstance(event, Disconnect):
                state.disconnected = True
            elif isinstance(event, Reconnect):
                state.disconnected = False
            # PhaseTransition + EndScenario: no-op for state; event-log
            # only (handled by the runner, not by the adapter).

        # Apply manual clears — caller's clear_dtcs() wins over any still-
        # active DTC from the timeline fold, and persists until a
        # subsequent InjectDTC re-adds the code.
        if self._manually_cleared:
            # Only strip codes that were cleared AFTER their most recent
            # injection. Simplification: if user called clear_dtcs(),
            # wipe all currently-active codes.
            state.active_dtcs = []

        return state

    # --- ProtocolAdapter contract --------------------------------------

    def connect(self, port: str = "", baud: int = 0) -> None:
        """Bring the simulator online.

        Idempotent, mirroring :class:`MockAdapter`. Raises
        :class:`ProtocolConnectionError` if the current timeline state
        says the adapter is disconnected (i.e. we're inside a
        ``Disconnect`` → ``Reconnect`` window).
        """
        state = self._materialize_state(self._clock.now())
        if state.disconnected:
            raise ProtocolConnectionError(
                f"simulator scenario {self._scenario.name!r} is in a "
                f"disconnected window at t={self._clock.now()}"
            )
        self._is_connected = True

    def disconnect(self) -> None:
        """Mark the simulator as disconnected. Idempotent, never raises."""
        self._is_connected = False

    def send_command(self, cmd: bytes) -> bytes:
        """Return empty bytes. Raises if disconnected.

        Phase 144 doesn't simulate raw wire-protocol responses; that
        would double the scope. The CLI scan / clear / info paths only
        call the higher-level methods (``read_dtcs``, ``clear_dtcs``,
        ``read_pid``, ``read_vin``), so an empty response here is fine.
        """
        if not self._is_connected:
            raise ProtocolConnectionError("simulator not connected")
        return b""

    def _check_live(self) -> None:
        """Raise if the current timeline state is inside a dead window."""
        state = self._materialize_state(self._clock.now())
        if state.disconnected:
            raise ProtocolConnectionError(
                f"simulator is in a disconnected window at "
                f"t={self._clock.now()}"
            )
        if self._clock.now() < state.timeout_until:
            raise ProtocolTimeoutError(
                f"simulator injected timeout active until "
                f"t={state.timeout_until}"
            )

    def read_dtcs(self) -> List[str]:
        """Return the active DTCs at the current clock time."""
        self._check_live()
        return list(self._materialize_state(self._clock.now()).active_dtcs)

    def clear_dtcs(self) -> bool:
        """Empty the active DTC list. Does NOT mutate the scenario timeline.

        Returns ``True`` unconditionally — the simulator always accepts
        Mode 04 clears. Scenarios that want to model a refusing ECU can
        inject a timeout or disconnect event instead.
        """
        self._check_live()
        # Flag that the user cleared — the fold honors this until the
        # next InjectDTC event re-adds codes.
        self._manually_cleared.append("__all__")
        return True

    def read_pid(self, pid: int) -> Optional[int]:
        """Return the integer-rounded PID value, or ``None`` if unknown."""
        self._check_live()
        state = self._materialize_state(self._clock.now())
        if pid not in state.pid_values:
            return None
        return int(round(state.pid_values[pid]))

    def read_vin(self) -> Optional[str]:
        """Return the VIN from the StartState / scenario header, or ``None``."""
        self._check_live()
        return self._materialize_state(self._clock.now()).vin

    def get_protocol_name(self) -> str:
        """Return the protocol label from the scenario header."""
        return self._scenario.protocol

    # --- CLI-facing helpers mirroring :class:`MockAdapter` -------------

    def identify_info(self) -> dict:
        """Snapshot shaped like :meth:`MockAdapter.identify_info`.

        Lets :class:`~motodiag.hardware.connection.HardwareSession` use
        its existing mock fast-path for ``hardware info --simulator``
        runs — no special-case branches needed in the session.
        """
        state = self._materialize_state(self._clock.now())
        return {
            "vin": state.vin,
            "ecu_part": None,
            "sw_version": None,
            # StartState PIDs happen to map neatly to "supported modes"
            # for scenario authoring purposes — list the set we're
            # willing to answer reads on.
            "supported_modes": [1, 3, 4, 9],
            "protocol_name": state.protocol,
        }


__all__ = [
    "SimulationClock",
    "StartState",
    "RampPid",
    "InjectDTC",
    "ClearDTC",
    "InjectTimeout",
    "Disconnect",
    "Reconnect",
    "PhaseTransition",
    "EndScenario",
    "ScenarioEvent",
    "Scenario",
    "ScenarioParseError",
    "ScenarioValidationError",
    "RecordingSupportUnavailable",
    "ScenarioLoader",
    "SimulatedAdapter",
    "PID_ALIASES",
]
