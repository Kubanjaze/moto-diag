# MotoDiag Phase 139 — Phase Log

**Status:** 🔲 Planned | **Started:** 2026-04-17 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-17 — Plan written, v1.0

Planner agent (moto-diag) drafted v1.0 plan docs for Phase 139 — ECU auto-detection + handshake. Phase 139 is the glue layer that sits on top of Phases 134-138's protocol adapters: given a serial port and an optional bike make hint, it picks a protocol priority order, tries each adapter's `connect()` in sequence, and returns the first one that succeeds. After connection, it issues OBD mode 09 reads (VIN, ECU ID, calibration ID, software version) plus a supported-modes probe to produce a best-effort ECU identification dict.

**Scope locked in v1.0:**
- New file `src/motodiag/hardware/ecu_detect.py` (~280 LoC) with `AutoDetector` class + `NoECUDetectedError(ProtocolError)` exception.
- `AutoDetector(port, baud=None, make_hint=None, timeout_s=5.0)` constructor.
- `detect() -> ProtocolAdapter` — tries protocols in priority order, returns first connected adapter, raises `NoECUDetectedError` on full failure. Caller owns the returned adapter's lifecycle (no auto-disconnect).
- `identify_ecu(adapter) -> dict` — returns `{vin, ecu_id, ecu_part_number, software_version, supported_modes}`, best-effort (any field may be None).
- ~20-25 tests in `tests/test_phase139_ecu_detect.py`, all using `MagicMock` adapters — zero live hardware, zero AI calls.
- **No CLI command** (Phase 140 owns `motodiag diagnose connect` or equivalent).
- **No migration.**
- **No new pyproject deps** (all serial/adapter deps added by 134-138).

**Key design decisions:**
1. **Make-hint priority logic** — hardcoded lookup table maps make to adapter sequence:
   - `harley` → J1850 → CAN → ELM327 (K-line excluded; not a Harley protocol)
   - `honda` / `yamaha` / `kawasaki` / `suzuki` → K-line → CAN → ELM327 (J1850 excluded)
   - `ducati` / `bmw` / `ktm` / `triumph` → CAN → K-line → ELM327 (J1850 excluded)
   - `None` or unknown → CAN → K-line → J1850 → ELM327
   Rationale: each failed `connect()` costs ~5s wall time, so excluding impossible protocols per-make trims worst-case detection from 20s (all four) to ~10s (three) or ~5s (first-try success on a known Harley).

2. **ECU identification is best-effort** — VIN, ECU ID, part number, and software version are independent reads; any can fail without tanking the others. Unparseable responses (wrong-length VIN, empty ASCII decode) yield `None` rather than raising. Pre-OBD-II bikes that don't respond to mode 09 simply return a dict of Nones — caller can still use the connected adapter for Phase 140's DTC reads.

3. **Non-ProtocolError exceptions are caught during detection** — if one adapter raises an unexpected `OSError` or `ValueError`, detection moves to the next candidate rather than propagating. Full failure list is preserved in `NoECUDetectedError.message` for debugging.

4. **Lazy adapter imports inside `_protocol_order_for_hint`** — defensive against partial cross-phase builds; a missing 138 module only breaks detection for Harleys, not for Japanese bikes.

5. **First-connect-wins, no auto-disconnect** — caller owns the lifecycle. Phase 140's CLI wraps detection in try/finally.

**Dependencies flagged:**
- Phases 134 (ProtocolAdapter ABC + ProtocolError), 135 (ELM327), 136 (CAN), 137 (K-line), 138 (J1850) must all be built first. Plan assumes uniform `(port, baud, timeout)` constructor signature and `connect()` / `disconnect()` / `send_request(mode, pid)` method signatures across adapters. If 134's abstraction settles on different names, Phase 139 code needs a small rework — documented in Risks.

Next step: wait for Phases 134-138 to land, then either auto-iterate the build or hand v1.0 off to Pisces for a standard-mode architect pass.
