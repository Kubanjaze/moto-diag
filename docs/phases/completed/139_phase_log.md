# MotoDiag Phase 139 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-17 | **Completed:** 2026-04-18
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

### 2026-04-18 07:00 — Build complete

Wave 3 Builder shipped `src/motodiag/hardware/ecu_detect.py` (~460 LoC — overshot ~280 target due to per-adapter factory kwargs reconciliation + best-effort ECU identification probes + `NoECUDetectedError` programmatic error list) plus `tests/test_phase139_ecu_detect.py` (~680 LoC) with 31 tests collected (25 test methods). Glue layer over Phases 134-138's protocol adapters. `AutoDetector(port, make_hint=None, timeout_s=2.0, baud=None)` given a serial port and optional make hint tries protocol adapters in priority order until one negotiates.

Priority tables: Harley → J1850 first (covers pre-2011 FLH/FXR/Sportster) then CAN (2011+ Touring); Japanese → CAN then KWP2000 then ELM327 (covers R1/CBR/ZX/GSX-R/SV modern + vintage); European → CAN then KWP2000 (covers Ducati/BMW/KTM/Triumph); unknown → all four in default order. Worst-case detection ~20s → ~5s on a known-make first-try hit.

Deviations from plan: adapter constructor non-uniformity confirmed as flagged in Risks. CAN uses `channel/bitrate/request_timeout+multiframe_timeout`, K-line uses `port/baud/read_timeout`, J1850 uses `port/baudrate/timeout_s`, ELM327 uses `port/baud/timeout`. Solved via per-protocol `_build_adapter` factory with string-label priority table + lazy per-adapter imports (missing optional deps only surface when that protocol is actually tried). `identify_ecu()` is best-effort — VIN + ECU part number + software version + supported OBD modes independently probed. `_decode_vin` handles both `49 02 01`-echo and stripped response forms, ASCII decode strips padding bytes, returns `None` on wrong length (no bogus truncation). `NoECUDetectedError(port, make_hint, errors=[(name, exception)])` subclasses `ProtocolError` and carries programmatic error list for introspection.

31 tests passed locally in 0.25s. Running total: 2574 tests. Zero live hardware — all tests use `MagicMock` adapters.

**Commit:** `15c658d` (Phases 133-139: Gate 5 PASSED + Track E hardware substrate).

### 2026-04-18 07:30 — Documentation finalization

`implementation.md` already at v1.1 with Results + Deviations. Verification Checklist marked `[x]` post-Gate 6. Moved to `docs/phases/completed/`.

Key finding: Phase 139 is what makes the Phase 134-138 protocol layer actually usable — before this glue layer, a mechanic pointed at a bike had to manually pick a protocol. The `make_hint` priority tables turn ECU detection from a 20-second full scan into a sub-5-second first-try hit on any bike whose make is already in the garage. Phase 140 (`motodiag hardware scan`) consumes this detector as its core flow, and Phase 146's `diagnose` troubleshooter step 3 wraps it with verbose per-attempt callbacks for mechanic-readable negotiation traces.
