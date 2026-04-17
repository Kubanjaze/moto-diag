# MotoDiag Phase 134 — OBD Protocol Abstraction Layer

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Stand up the Track E foundation: a pure-Python `ProtocolAdapter` abstract base class plus supporting Pydantic models and an exception hierarchy, so later phases (135 ELM327, 136 CAN, 137 K-line, 138 J1850, 139 ECU detect) can each drop in a concrete implementation without touching each other or shared client code. This is a definitional phase — no hardware I/O, no CLI surface, no migration, zero tokens. Phase 140 wires the first real adapter through a `hardware diagnose` CLI; this phase gives that wiring a contract to code against.

CLI: **none** — this phase adds no new command. Protocol adapters are internal library surfaces consumed by later Track E phases and by Phase 140's `motodiag hardware diagnose` command.

Outputs: new `src/motodiag/hardware/protocols/` package (`__init__.py`, `base.py`, `models.py`, `exceptions.py`), updated `src/motodiag/hardware/__init__.py` (re-exports), new `tests/test_phase134_protocol_abstraction.py` (~25-30 tests). Roughly 180-220 LoC of production code + 300-350 LoC of tests.

## Logic

### 1. `src/motodiag/hardware/protocols/__init__.py`
Thin re-export module so callers import from `motodiag.hardware.protocols` rather than the internal file names:
- Re-exports `ProtocolAdapter` from `base.py`
- Re-exports `ProtocolConnection`, `DTCReadResult`, `PIDResponse` from `models.py`
- Re-exports `ProtocolError`, `ConnectionError`, `TimeoutError`, `UnsupportedCommandError` from `exceptions.py`
- `__all__` list matches the above — makes the public surface explicit and lintable.

### 2. `src/motodiag/hardware/protocols/exceptions.py`
Exception hierarchy, defined first because `base.py` references these types in method docstrings.
- `class ProtocolError(Exception)` — base; subclass of built-in `Exception`. Docstring explains this is the root of every protocol-layer exception so callers can do `except ProtocolError` to catch anything from a misbehaving adapter.
- `class ConnectionError(ProtocolError)` — raised when `connect()` fails (port unavailable, adapter unresponsive, handshake refused). Note: deliberately shadows Python built-in `ConnectionError` inside this module's namespace — consumers import as `from motodiag.hardware.protocols import ConnectionError as ProtocolConnectionError` if they need to disambiguate, or more commonly just catch `ProtocolError`. Docstring flags the shadowing so nobody is surprised.
- `class TimeoutError(ProtocolError)` — raised when an adapter read/write exceeds its configured `timeout_s`. Same shadowing note as `ConnectionError`.
- `class UnsupportedCommandError(ProtocolError)` — raised when a caller asks an adapter to do something the underlying protocol cannot (e.g., `read_vin()` on a J1850 VPW link that doesn't expose Mode 09). Carries the command name as `.command: str` attribute for log legibility.

No custom `__init__` on the subclasses; they inherit `Exception`'s. Each class is ~3-6 LoC including docstring.

### 3. `src/motodiag/hardware/protocols/models.py`
Pydantic v2 models — data containers only, no behavior.

- `class ProtocolConnection(BaseModel)`:
  - `port: str` — serial device path (`COM3`, `/dev/ttyUSB0`) or Bluetooth address (`AA:BB:CC:DD:EE:FF`).
  - `baud: int = 38400` — default matches ELM327 factory setting. `Field(gt=0, le=1000000)`.
  - `timeout_s: float = 2.0` — per-operation timeout. `Field(gt=0.0, le=60.0)`.
  - `protocol_name: str` — human-readable identifier returned by the adapter's `get_protocol_name()` (e.g., `"ISO 15765-4 (CAN 11/500)"`).
  - `model_config = ConfigDict(frozen=True)` — connection descriptors are immutable once the adapter is connected.

- `class DTCReadResult(BaseModel)`:
  - `codes: list[str]` — DTC codes in standard format (`P0171`, `C1234`, `B2468`, `U0100`). Empty list == no faults. `Field(default_factory=list)`.
  - `source_protocol: str` — which protocol produced this read, for trace/debug. Matches `ProtocolConnection.protocol_name`.
  - `read_at: datetime` — timestamp (UTC) when the read completed. `Field(default_factory=lambda: datetime.now(timezone.utc))`.
  - Validator on `codes`: each code must match `^[PCBU][0-9A-F]{4}$` (case-insensitive); normalize to uppercase. Invalid codes raise `ValueError` at model-construction time — surfaced as `pydantic.ValidationError` to the caller.

- `class PIDResponse(BaseModel)`:
  - `pid: int` — `Field(ge=0, le=0xFFFF)` — covers Mode 01 (1-byte) and Mode 22 (2-byte) PIDs.
  - `raw_bytes: bytes` — exact bytes returned by the adapter after stripping the protocol framing.
  - `parsed_value: Optional[float] = None` — decoded physical value if the adapter recognized the PID; `None` means "raw bytes only, no decode table entry."
  - `parsed_unit: Optional[str] = None` — unit label for `parsed_value` (e.g., `"°C"`, `"rpm"`, `"kPa"`). Must be `None` iff `parsed_value` is `None`; validator enforces this paired-presence rule.

All three models use `model_config = ConfigDict(extra="forbid")` to prevent silent typos in construction.

### 4. `src/motodiag/hardware/protocols/base.py`
The `ProtocolAdapter` ABC. Every method documented with "what a concrete implementation must do" semantics so Phases 135-139 can be implemented from the docstring alone.

```python
from abc import ABC, abstractmethod
from typing import Optional

class ProtocolAdapter(ABC):
    """Abstract contract every Track E protocol adapter implements."""

    @abstractmethod
    def connect(self, port: str, baud: int) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def send_command(self, cmd: bytes) -> bytes: ...

    @abstractmethod
    def read_dtcs(self) -> list[str]: ...

    @abstractmethod
    def clear_dtcs(self) -> bool: ...

    @abstractmethod
    def read_pid(self, pid: int) -> Optional[int]: ...

    @abstractmethod
    def read_vin(self) -> Optional[str]: ...

    @abstractmethod
    def get_protocol_name(self) -> str: ...

    @property
    def is_connected(self) -> bool:
        return getattr(self, "_is_connected", False)
```

**Method-by-method contract** (copied into docstrings verbatim so agents implementing 135-139 can code against the comment):

- `connect(port, baud) -> None` — open the underlying transport, run the protocol handshake, leave the adapter ready to send commands. Must raise `ConnectionError` (the module-local one) on failure, never return partial state. On success the implementation sets `self._is_connected = True`. Idempotent: calling `connect()` on an already-connected adapter is a no-op, not an error.

- `disconnect() -> None` — close the transport, flush buffers, release serial/Bluetooth handles. Must not raise — log-and-swallow on cleanup errors. Sets `self._is_connected = False`. Also idempotent.

- `send_command(cmd: bytes) -> bytes` — send raw protocol bytes, return the adapter's raw reply with protocol framing stripped but without any semantic parsing. Raises `TimeoutError` if `timeout_s` elapses before a complete reply arrives. Raises `ConnectionError` if called on a disconnected adapter. This is the low-level escape hatch for commands the higher-level methods don't cover (custom Mode 22 reads, manufacturer-specific Mode 21, etc.).

- `read_dtcs() -> list[str]` — execute Mode 03 (stored codes) or the protocol equivalent, parse the reply, return DTC strings in `P0171` format. Empty list means no codes, not an error. Consumers typically wrap this in a `DTCReadResult` themselves (with timestamp + source_protocol) — the adapter stays schema-free.

- `clear_dtcs() -> bool` — execute Mode 04, return `True` on acknowledged clear, `False` on refusal (some ECUs require ignition-on/engine-off). Does not raise on a "refused" — only raises on comm errors. Caller decides whether False is fatal to their workflow.

- `read_pid(pid: int) -> Optional[int]` — execute Mode 01 PID read, return the integer value if the PID is supported and the decode is unambiguous, `None` if the ECU replies "PID not supported" (NACK or all-zeros service-01 support mask). For multi-byte PIDs the adapter is responsible for the protocol-specific bit-shift/scaling. More complex decodes (floats, multi-field) go through `send_command` + caller-side parsing in later phases; the simple int surface keeps phase-140 wiring trivial. Note: the full `PIDResponse` model exists for adapters that want to return richer data — they can, via their own higher-level methods; `read_pid` is the always-available shortcut.

- `read_vin() -> Optional[str]` — execute Mode 09 PID 02, return the 17-char VIN as uppercase ASCII, or `None` if the protocol does not support VIN retrieval (pre-2008 K-line, some J1850 VPW). Raises `UnsupportedCommandError` only if the caller insists on VIN on a protocol that physically cannot carry it (some early Harleys) — returning None is preferred where the protocol *could* support VIN but the specific ECU does not.

- `get_protocol_name() -> str` — human-readable protocol identifier, stable across the life of the adapter instance. Feeds `DTCReadResult.source_protocol` and any UI that tells the mechanic what's connected.

- `is_connected` (property, concrete not abstract) — defaults to `getattr(self, "_is_connected", False)`. Subclasses set `self._is_connected` in their `connect()` / `disconnect()` implementations. Keeping this concrete with a sensible default means subclasses don't have to reimplement the property — they just flip the backing attribute.

### 5. `src/motodiag/hardware/__init__.py` update
Before this phase the file is a one-line docstring stub. After:
- Keep the docstring.
- Add re-exports of `ProtocolAdapter` and the four model/exception classes from `.protocols` so downstream code can `from motodiag.hardware import ProtocolAdapter` without reaching into `.protocols`. Both import paths stay valid — `protocols.*` for package-local clarity, `hardware.*` for consumer convenience.

### 6. Tests — `tests/test_phase134_protocol_abstraction.py`
~25-30 tests across 5 test classes. All pure Python, no serial / no hardware, no monkeypatching of hardware libs. Zero network, zero tokens.

- **`TestProtocolAdapterABC` (~8 tests)**:
  1. `ProtocolAdapter` cannot be instantiated directly (`pytest.raises(TypeError)` with message containing `"abstract"`).
  2. A subclass missing one abstract method cannot be instantiated — parametrize over each of the 8 abstract methods; each omission raises `TypeError`.
  3. A subclass implementing all 8 abstract methods instantiates cleanly.
  4. The complete subclass's `is_connected` returns `False` before anyone sets `_is_connected`.
  5. Setting `_is_connected = True` on an instance flips `is_connected` to True without the subclass overriding the property.
  6. `is_connected` is a property, not a callable (assert `isinstance(type(instance).is_connected, property)`).
  7. All abstract methods are decorated with `@abstractmethod` (introspect via `ProtocolAdapter.__abstractmethods__` — assert exact set of names).
  8. `ProtocolAdapter` is a subclass of `abc.ABC` (or equivalently has `ABCMeta` as metaclass).

- **`TestProtocolConnection` (~5 tests)**:
  9. Valid construction with defaults: port set, baud=38400, timeout_s=2.0.
  10. Invalid baud (0, negative, > 1_000_000) raises `ValidationError`.
  11. Invalid timeout (0, negative, > 60) raises `ValidationError`.
  12. Model is frozen — mutation raises `ValidationError`.
  13. `extra="forbid"` — passing a typo field name raises `ValidationError`.

- **`TestDTCReadResult` (~5 tests)**:
  14. Valid codes list normalizes to uppercase (`"p0171"` → `"P0171"`).
  15. Invalid code format (e.g. `"X1234"`, `"P12"`, `"P0G71"`) raises `ValidationError`.
  16. Empty codes list is valid (no-DTC case).
  17. `read_at` auto-populates with a timezone-aware datetime in UTC.
  18. `source_protocol` is required (no default) — omission raises `ValidationError`.

- **`TestPIDResponse` (~5 tests)**:
  19. Valid construction with `parsed_value` + `parsed_unit` both present.
  20. Valid construction with both `None`.
  21. `parsed_value` set but `parsed_unit` None raises `ValidationError` (paired rule).
  22. `parsed_value` None but `parsed_unit` set raises `ValidationError`.
  23. `pid` out of range (`-1`, `0x10000`) raises `ValidationError`.

- **`TestExceptionHierarchy` (~4 tests)**:
  24. `ConnectionError` is a subclass of `ProtocolError`.
  25. `TimeoutError` is a subclass of `ProtocolError`.
  26. `UnsupportedCommandError` is a subclass of `ProtocolError` and carries a `.command` attribute when constructed with one.
  27. `try: raise UnsupportedCommandError("read_vin") except ProtocolError as e: ...` catches it cleanly.

- **`TestPublicReExports` (~3 tests)**:
  28. `from motodiag.hardware.protocols import ProtocolAdapter, ProtocolConnection, DTCReadResult, PIDResponse, ProtocolError, ConnectionError, TimeoutError, UnsupportedCommandError` all succeed.
  29. `from motodiag.hardware import ProtocolAdapter` succeeds (convenience re-export).
  30. `motodiag.hardware.protocols.__all__` lists exactly the expected public names.

Target: 30 tests. All must pass on first run locally; full existing suite (2326 tests from Phase 132) must continue passing.

## Key Concepts

- **Abstract base class via `abc.ABC` + `@abstractmethod`**: enforces that concrete adapters (Phases 135-139) implement every required method before instantiation is even possible. Phase 134 tests this enforcement explicitly — the agent implementing Phase 135 cannot ship a partial ELM327 adapter; Python will refuse to instantiate it.

- **Exception shadowing is intentional**: `ConnectionError` and `TimeoutError` deliberately match Python built-in names. Inside `motodiag.hardware.protocols` they're module-local; any consumer that needs to disambiguate aliases on import (`from motodiag.hardware.protocols import TimeoutError as ProtocolTimeoutError`). The tradeoff: consistent domain vocabulary (every protocol error catchable as `ProtocolError`) over import-time friction. Docstrings flag the shadowing on each class.

- **Pydantic v2 for data models**: consistent with the rest of the codebase (Phase 03 onward). `ConfigDict(frozen=True)` on `ProtocolConnection` prevents a common hardware-layer bug where someone mutates a live connection descriptor mid-session.

- **Paired-optional validation on `PIDResponse`**: `parsed_value` and `parsed_unit` must be both None or both set. Prevents the "decoded value with no unit label" ambiguity that Phase 135/136 would otherwise have to re-specify.

- **DTC code regex** (`^[PCBU][0-9A-F]{4}$`): matches the four OBD-II DTC families — Powertrain, Chassis, Body, Network. Case-insensitive input, uppercase storage. Rejects common typos at the model boundary so later pipeline stages can trust the shape.

- **`is_connected` as concrete property, not abstract**: the default (`getattr(self, "_is_connected", False)`) works for 100% of realistic adapter implementations. Making it abstract would force every subclass to write the same 3-line getter. Keeping it concrete with a sane default is the right ergonomics for a 5-adapter future.

- **`read_pid` returns `int | None`, not `PIDResponse`**: the simple int surface keeps Phase 140's CLI wiring trivial (`pid = adapter.read_pid(0x0C); click.echo(f"RPM: {pid}")`). Adapters that need to expose richer data (raw bytes, decoded float with unit) can offer their own higher-level methods in addition to `read_pid`. This follows the "progressive disclosure" pattern: the common case is one-liner; the complex case is a separate method.

- **No CLI, no migration, no tokens**: this is a pure abstraction phase. The value delivered is contract-stability for Phases 135-139, not user-visible features. The Verification Checklist reflects that — every check is a code-level assertion, not a CLI invocation.

- **Phase 140 will own the wiring**: `motodiag hardware diagnose` is explicitly out of scope here. The split keeps Phase 134 small and reviewable; Phase 140 becomes the integration test that proves the abstraction survives contact with a real CLI.

## Verification Checklist
- [ ] `src/motodiag/hardware/protocols/__init__.py` re-exports all 8 public names
- [ ] `src/motodiag/hardware/protocols/base.py` defines `ProtocolAdapter` as an `abc.ABC` subclass
- [ ] All 8 interface methods (`connect`, `disconnect`, `send_command`, `read_dtcs`, `clear_dtcs`, `read_pid`, `read_vin`, `get_protocol_name`) are decorated with `@abstractmethod`
- [ ] `is_connected` is a concrete property returning `self._is_connected` (default False)
- [ ] `ProtocolAdapter` cannot be instantiated directly (raises `TypeError`)
- [ ] A subclass missing any abstract method also cannot be instantiated
- [ ] A fully-implemented subclass instantiates cleanly
- [ ] `ProtocolConnection` has `port`, `baud=38400`, `timeout_s=2.0`, `protocol_name` fields
- [ ] `ProtocolConnection` is frozen (immutable after construction)
- [ ] `ProtocolConnection` rejects invalid baud / timeout via Pydantic validation
- [ ] `ProtocolConnection` rejects extra fields (`extra="forbid"`)
- [ ] `DTCReadResult` normalizes lowercase codes to uppercase
- [ ] `DTCReadResult` rejects malformed codes via regex validator
- [ ] `DTCReadResult.read_at` defaults to UTC-aware `datetime.now`
- [ ] `DTCReadResult` accepts empty codes list (no-DTC case)
- [ ] `PIDResponse.pid` enforces 0 ≤ pid ≤ 0xFFFF
- [ ] `PIDResponse` enforces paired presence/absence of `parsed_value` and `parsed_unit`
- [ ] `ProtocolError` is a subclass of `Exception`
- [ ] `ConnectionError`, `TimeoutError`, `UnsupportedCommandError` all subclass `ProtocolError`
- [ ] `UnsupportedCommandError` carries a `.command` attribute
- [ ] `from motodiag.hardware.protocols import ProtocolAdapter` succeeds
- [ ] `from motodiag.hardware import ProtocolAdapter` succeeds (convenience re-export)
- [ ] `motodiag.hardware.protocols.__all__` lists exactly the 8 public names
- [ ] 25-30 new tests in `tests/test_phase134_protocol_abstraction.py` all pass
- [ ] Full existing suite (2326 tests) continues to pass — zero regressions
- [ ] Zero live API tokens burned
- [ ] No new runtime dependencies added to `pyproject.toml` (uses stdlib `abc` + existing `pydantic`)

## Risks
- **Exception name shadowing (`ConnectionError`, `TimeoutError`) vs Python built-ins**: if a consumer does `from motodiag.hardware.protocols import *` plus catches Python's built-in `ConnectionError` in the same scope, they'll get the protocol one instead. Mitigation: docstrings call this out explicitly; `__all__` is explicit (no wildcard hazard for most callers); Phase 140 documentation will recommend `import motodiag.hardware.protocols as proto` and `except proto.ConnectionError`. Re-evaluate if Phase 140/141 tests report confusion.
- **ABC is compile-time enforcement, not runtime discipline**: a subclass can still implement all 8 methods as `raise NotImplementedError` stubs and satisfy the ABC. Mitigation: Phase 135's tests verify real behavior; the ABC is the first guardrail, not the last.
- **`read_pid` returning `int | None` limits the PID surface**: adapters needing floats or multi-field decodes must add their own methods. Risk: consumers forget and use `read_pid` for a PID that only makes sense as a float (e.g., engine-coolant-temp that's signed + offset). Mitigation: docstring explicitly points to `send_command` + `PIDResponse` for rich cases; Phase 136's CAN adapter will be the first real-world test of whether the simple surface is sufficient.
- **`clear_dtcs` returning `bool` loses error context**: `False` could mean "ECU refused" or "comms fine but ACK lost." Mitigation: higher-level adapters can log the raw reply from the failed clear; the abstraction intentionally hides that detail from the generic interface.
- **Scope-creep temptation during build**: it will be tempting to sneak an `ELM327Adapter` stub into Phase 134 to "validate the abstraction." Resist — Phase 135 is the dedicated slot. Phase 134's validation is the passing test suite proving the contract holds. If the build agent proposes a stub adapter, reject it.
- **Frozen `ProtocolConnection` + runtime baud change**: some ELM327 adapters negotiate to a higher baud after handshake. Mitigation: the ELM327 adapter in Phase 135 creates a *new* `ProtocolConnection` for the post-handshake state rather than mutating the original. Documented when 135 is planned.
