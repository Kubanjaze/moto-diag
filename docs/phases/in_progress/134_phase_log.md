# MotoDiag Phase 134 — Phase Log

**Status:** 📝 Planned | **Started:** 2026-04-17 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-17 00:00 — Plan written, v1.0
Track E kickoff — pure abstraction phase. Defines `ProtocolAdapter` ABC (8 abstract methods + 1 concrete `is_connected` property), three Pydantic v2 data models (`ProtocolConnection`, `DTCReadResult`, `PIDResponse`), and a four-class exception hierarchy (`ProtocolError` root + `ConnectionError` / `TimeoutError` / `UnsupportedCommandError` subclasses) in a new `src/motodiag/hardware/protocols/` package. Updates the `hardware/__init__.py` stub (previously one-line docstring) to re-export the public contract.

Method signatures finalized:
- `connect(port: str, baud: int) -> None` — raises `ConnectionError` on failure, idempotent
- `disconnect() -> None` — idempotent, swallows cleanup errors
- `send_command(cmd: bytes) -> bytes` — raw escape hatch, raises `TimeoutError` / `ConnectionError`
- `read_dtcs() -> list[str]` — Mode 03 equivalent, empty list = no faults
- `clear_dtcs() -> bool` — Mode 04 equivalent, False = ECU refused (not an error)
- `read_pid(pid: int) -> Optional[int]` — simple int return, None = unsupported PID
- `read_vin() -> Optional[str]` — Mode 09 PID 02, raises `UnsupportedCommandError` only if protocol physically can't carry VIN
- `get_protocol_name() -> str` — stable human-readable identifier
- `is_connected` (property) — concrete default, reads `self._is_connected`

Key design calls captured: exception-shadowing of Python built-ins is intentional (domain vocabulary wins; docstrings flag it); `ProtocolConnection` is frozen; `PIDResponse` enforces paired presence of `parsed_value`/`parsed_unit`; DTC regex `^[PCBU][0-9A-F]{4}$` validates + uppercases at the model boundary; `is_connected` stays concrete with a sensible default so subclasses only flip `_is_connected`. No CLI, no migration, no tokens — Phase 140 owns the first real wiring through `motodiag hardware diagnose`.

Test plan: ~25-30 tests across 5 classes — `TestProtocolAdapterABC` (8), `TestProtocolConnection` (5), `TestDTCReadResult` (5), `TestPIDResponse` (5), `TestExceptionHierarchy` (4), `TestPublicReExports` (3). All pure Python; zero hardware, zero network, zero tokens.

Next: hand off to Builder (or direct build) — create `src/motodiag/hardware/protocols/` (`__init__.py`, `base.py`, `models.py`, `exceptions.py`), update `src/motodiag/hardware/__init__.py`, author `tests/test_phase134_protocol_abstraction.py`, run locally, update to v1.1.
