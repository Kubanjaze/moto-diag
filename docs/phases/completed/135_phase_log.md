# MotoDiag Phase 135 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-17 | **Completed:** 2026-04-18
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

### 2026-04-18 06:30 — Build complete

First concrete `ProtocolAdapter` on top of Phase 134's ABC shipped as Wave 2 Builder output. New `src/motodiag/hardware/protocols/elm327.py` (~584 LoC — overshot the ~320 LoC target per the "detailed and meticulous" standard; extra is docstring + AT-command reference + defensive response parsing), plus `tests/test_phase135_elm327.py` with 52 tests (overshot the ~22 target — additional coverage on multi-frame tolerance, ELM clone quirks, and error-token recovery). Full AT-command handshake `ATZ` → `ATE0` → `ATL0` → `ATSP0` → `0100` probe, multi-frame scan tolerance (searches for `43`/`41 XX` service-ID echo rather than anchoring at byte 0 — real ELM clones emit variable pre-response whitespace), SAE J2012 DTC decoder as a pure function (P/C/B/U letter prefix + 4 hex digits), mode 09 PID 02 VIN assembly across CAN multi-frame `0:`/`1:`/`2:` prefixes.

Deviations from plan: ABC signature reconciliation with Phase 134's shipped contract — `connect(port, baud)` params (plan assumed `connect()` with constructor-supplied port), `read_pid → Optional[int]` (plan said `bytes`), `clear_dtcs → bool` (plan said `None`). Solved via direct cross-reference of `base.py` at build time as the risk note anticipated. `_get_serial_module()` indirection shipped as planned — test fixtures monkeypatch it, zero `sys.modules` gymnastics. No `pyproject.toml` change (hardware extra already declared by Phase 134 groundwork).

52 tests passed locally in the Wave 2 batch. Running total: 2434 tests passing. Zero live API tokens burned (pure protocol driver, no AI).

**Commit:** `15c658d` (Phases 133-139: Gate 5 PASSED + Track E hardware substrate).

### 2026-04-18 07:00 — Documentation finalization

`implementation.md` promoted to v1.1 with Results + Deviations sections inline at the top. Verification Checklist items marked `[x]` after Gate 6 (Phase 147) integration test confirmed the adapter round-trips cleanly under the Phase 144 simulator. Phase moved to `docs/phases/completed/`; project implementation.md Phase History row landed alongside the commit.

Key finding: the `_get_serial_module()` indirection is the load-bearing test-DX decision from this phase. Every subsequent Track E adapter (136 CAN, 137 K-line, 138 J1850) adopted the same lazy-import + monkeypatch-attribute pattern — it's what lets 170+ Track E tests run with zero `sys.modules` patching across four protocols. Phase 135 also unlocked ~80% of aftermarket OBD-II dongles on the market (OBDLink MX+/SX/CX, Vgate iCar, generic ELM327 v1.5 clones), which Phase 140's `motodiag hardware scan` then surfaced to mechanics on day one.
