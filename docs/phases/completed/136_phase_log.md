# MotoDiag Phase 136 — Phase Log

**Status:** Planned | **Started:** 2026-04-17 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-17 — Plan written, v1.0
CAN bus protocol (ISO 15765) — concrete `ProtocolAdapter` for 2011+ Harleys, modern sportbikes, and post-2010 CAN-OBD-compliant motorcycles. Built on Phase 134's `ProtocolAdapter` base (to be delivered first). Ships library code only — no new CLI command, no migration.

Scope of the v1.0 plan:
- New `src/motodiag/hardware/protocols/__init__.py` (empty package marker).
- New `src/motodiag/hardware/protocols/can.py` (~380–450 LoC) — `CANAdapter(ProtocolAdapter)` implementing ISO 15765-4 (OBD-II over CAN) + ISO 15765-2 (ISO-TP transport).
- Uses `python-can>=4.0` as optional dep via new `motodiag[can]` extras entry. Defensive lazy import — module imports without python-can installed; `connect()` raises a clear `HardwareError` with `pip install 'motodiag[can]'` hint.
- Supported bitrates: 500 kbit/s (modern bikes) + 250 kbit/s (some OEM diagnostic links). Auto-detect is Phase 139's job.
- 11-bit CAN IDs only: functional request 0x7DF, physical response range 0x7E8–0x7EF. 29-bit extended IDs deferred to a future phase.

Key design decisions captured in the plan:
1. **ISO-TP is the hinge**: CAN's 8-byte frame limit makes ISO 15765-2 mandatory for any response > 7 bytes (notably the 17-char VIN). Hand-rolled stateless sender + receiver, no `python-can-isotp` dep — narrower scope, more auditable, and teaches the protocol to readers.
2. **Sender/receiver asymmetry**: multi-frame **receive** is load-bearing (VIN, long DTC lists, freeze-frame); multi-frame **send** is implemented but almost never exercised in OBD-II — included for symmetry and future UDS use in Phase 137+.
3. **Stateless transactions**: each `read_dtcs`/`read_vin`/etc. is a full ISO-TP round-trip from scratch. No session management, no tester-present heartbeat, no asyncio. Keeps the adapter at ~400 LoC and inspectable end-to-end.
4. **Flow Control policy**: on receive, we emit `[0x30, 0x00, 0x00, ...]` (CTS, block_size=0, ST=0 — "send all remaining frames as fast as possible"). This is the most common ECU-friendly default and avoids implementing a per-CF wait loop.
5. **NRC decoding**: ~10 common ISO 14229-1 NRCs hard-coded (0x10, 0x11, 0x12, 0x13, 0x22, 0x31, 0x33, 0x78, 0x7E, 0x7F); unknown NRCs fall back to `unknownNRC(0xNN)`. A mechanic seeing `"conditionsNotCorrect"` in a log knows the fix (ignition on, engine warm, battery > 12V) without looking up the spec.
6. **NRC 0x78 `responsePending` deferred**: v1.0 treats it as an error; a v1.1 patch can add deadline-extension if real hardware testing in Phase 133 Gate 5 or later surfaces it. Flagged in Risks.
7. **~22 tests, all mock-based**: `FakeBus` helper class (~40 LoC in the test file) simulates `can.Bus` with `sent`/`rx_queue` lists. Zero real hardware, zero live API tokens, full suite runs in < 2s. Covers SF/MF/NRC/timeout/bus-error paths.
8. **`python-can-isotp` deliberately NOT used** — three reasons documented in Key Concepts: fewer Windows-build-fragile deps, narrow scope, educational value for mechanics reading the source.

Dependency ordering: Phase 134 (abstract `ProtocolAdapter` base + `HardwareError` class) must land before Phase 136's build step can start. The plan assumes the base's contract; if Phase 134 ships different method signatures, this plan needs minor revision before builder dispatch. Flagged to the sequencing agent.

Out of scope (intentional):
- Active tests / bi-directional control (UDS security access, actuator control) — deferred to later Track F work.
- 29-bit extended addressing — no 2011+ bike under current Track B coverage requires it for OBD-II-standard services.
- Real-hardware integration tests — a dedicated future phase will validate against a CANable dongle + ECU simulator + real bench-test bike.
- Any new CLI command — Phase 139 (auto-detect + handshake) is what exposes these adapters to the user.

Docs at `docs/phases/in_progress/136_implementation.md` (v1.0) and `docs/phases/in_progress/136_phase_log.md` (this file). Not committed yet — Planner agent output only. No build has started.
