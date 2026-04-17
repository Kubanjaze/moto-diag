# MotoDiag Phase 135 — Phase Log

**Status:** Planned | **Started:** 2026-04-17 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-17 — Plan written, v1.0
First concrete `ProtocolAdapter` implementation on top of Phase 134's base class. Ships `ELM327Adapter` in `src/motodiag/hardware/protocols/elm327.py` — wraps the ubiquitous ELM327 OBD-II chip (serial / USB / Bluetooth-SPP) behind a clean Python API. Eight public methods: `connect`, `disconnect`, `is_connected`, `send_command`, `read_dtcs`, `clear_dtcs`, `read_pid`, `read_vin`. Init sequence ATZ → ATE0 → ATL0 → ATS0 → ATH0 → ATSP0 (auto protocol). SAE J2012 DTC decoder is a pure function. CAN multi-frame responses (`0:`, `1:` line prefixes) are handled. ELM error tokens (`NO DATA`, `CAN ERROR`, `UNABLE TO CONNECT`, `?`, `STOPPED`, `BUFFER FULL`) raise `ProtocolError`; `SEARCHING...` is treated as informational noise.

Configurable serial port (`COM5` / `/dev/ttyUSB0` / `/dev/rfcomm0`) and baud (default 38400 for ELM327 v1.5 clones). Uses the existing `motodiag[hardware]` extra (`pyserial>=3.5`, already declared at `pyproject.toml` line 37-39) — no pyproject change this phase.

**Key design decision — serial mock pattern for tests:**
The adapter includes a one-line `_get_serial_module()` indirection function that imports pyserial. Tests monkeypatch this function to return a fake `serial` module whose `Serial(...)` constructor returns a `MagicMock` with a `bytearray` rx-buffer. A `feed(mock, b"...\r>")` helper queues responses; the mock's `.read(1)` pops one byte at a time and returns `b""` (simulating timeout) when empty. Each test is 3-5 lines of setup + assertion — zero `sys.modules` trickery, zero import-order fragility. Tests assert on `mock._last_write` to verify the exact AT command bytes the adapter sent.

This indirection also gives us three runtime benefits: (1) importing the module on a machine without pyserial never crashes (only `connect()` does), (2) the missing-dep error message includes the exact install hint `pip install 'motodiag[hardware]'`, (3) the adapter stays testable without any `patch.dict(sys.modules, ...)` gymnastics.

Test plan: ~22 tests across 6-7 classes — `TestConnectDisconnect` (5), `TestSendCommand` (4), `TestReadDTCs` (4), `TestClearDTCs` (2), `TestReadPID` (3), `TestReadVIN` (2), `TestDTCDecoder` (2). Zero real hardware. Zero AI. Zero live API tokens.

No CLI command this phase — Phase 140 (`motodiag scan live`) wires hardware into user-facing flows. Phase 135 is library-only so Phase 136 (PID library) and Phase 137 (DTC lookup) can proceed in parallel.

Risk flagged: Phase 134's base class signatures must be locked before 135 Builder starts coding. If 134 and 135 run concurrently, the 135 Builder must cross-reference `base.py` directly (not just 134's plan doc) mid-build.
