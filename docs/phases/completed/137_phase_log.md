# MotoDiag Phase 137 — Phase Log

**Status:** Planned | **Started:** 2026-04-17 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-17 — Plan written, v1.0

Second concrete `ProtocolAdapter` in Track E — K-line / KWP2000 (ISO 14230-4) for 90s/2000s Japanese bikes (Honda CBR/CRF, Kawasaki ZX, Suzuki GSX-R/SV650, Yamaha R1/R6) and equivalent-era Euro bikes (Aprilia, Ducati, KTM) before the CAN migration.

Scope (library only — no CLI, no migration):
- New `src/motodiag/hardware/protocols/kline.py` (~450-550 LoC): `KLineAdapter(ProtocolAdapter)` inheriting from the Phase 134 base.
- KWP2000 service identifiers exposed: `0x10` StartDiagnosticSession, `0x11` ECUReset, `0x14` ClearDiagnosticInformation, `0x18` ReadDTCsByStatus, `0x1A` ReadECUIdentification. Write services (SecurityAccess, WriteData, StartRoutine) deliberately out of scope — tune-writing lands in a later dedicated phase with multi-layer safety confirmations.
- Dual wakeup paths: `init_mode="slow"` (5-baud address-byte init, default — universal on legacy Jp bikes) and `init_mode="fast"` (ISO 14230-2 25 ms low + 25 ms high wakeup for newer ECUs). Both paths converge on a `StartDiagnosticSession 0x81` (default) handshake.
- Framing: `[FMT][TGT][SRC][LEN?][DATA...][CS]` per ISO 14230-2. FMT byte duality (length in low-6-bits for ≤63-byte payloads, explicit LEN byte for 64-255) handled transparently. 8-bit sum-mod-256 checksum validated on parse, computed on build.
- Two baud rates: 10400 (KWP2000 canonical) and 9600 (older Honda/Suzuki). Constructor param.
- Default addresses: ECU 0x11 (Honda/Kawasaki), tester 0xF1 (SAE J2190). Overridable per make — Yamaha uses 0x12, some Suzukis 0x10. Future phase (likely 146 or vehicle profile) will add per-make lookup.

**Key design decisions:**

**1. 5-baud slow init via `break_condition` toggling.**
pyserial doesn't support 5 baud directly on most USB-serial chips (FTDI, CH340 both reject sub-50-baud). We fake it by setting the UART to an arbitrary low baud then toggling `serial.break_condition` True/False on 200 ms intervals to physically drive the TX line low/high bit-by-bit. Sequence: 200 ms low start bit → 8 bits of ECU address (LSB-first, break=low=0, no-break=high=1, 200 ms each) → 200 ms high stop bit. Total wall-clock: ~2.0 s per wakeup. Then switch UART to real baud (10400) and read sync (`0x55`) + keybyte1 + keybyte2 within W1+W2+W3 windows (300+20+20 ms). After W4 (25 ms) the tester echoes `~keybyte2` back; ECU finally echoes `~ecu_address`. Match = handshake complete.

**2. Echo cancellation via `_drain_echo()` — the non-obvious-but-critical piece.**
K-line is single-wire half-duplex. Every byte the tester writes to the UART is electrically echoed back on the same line and ends up in the UART's RX FIFO. Without filtering, the first bytes of what looks like an "ECU response" are actually the tail of the tester's own request — checksum will always fail, framing will be wrong, debugging is miserable. The adapter drains exactly `len(sent)` bytes from RX after every write and asserts strict byte-equality with what was sent. Mismatch = wiring fault or wrong ECU address; raise `ProtocolError` immediately rather than shifting the frame parser by a byte and hoping. This is the #1 gotcha in DIY K-line projects and the reason professional tools (Launch X431, MC33290 transceivers) handle echo at the hardware layer. We do it in software.

**3. Dual-mode wakeup with slow as default.**
`init_mode="slow"` is the safe default — works on 100% of the target-era bikes. `init_mode="fast"` is a power-user option for newer platforms that honor ISO 14230-2 fast init. Users with an unknown bike try slow first; if it succeeds but they want quicker reconnects for subsequent sessions, they can try fast as an optimization.

**4. Defensive pyserial import (lazy, not module-level).**
`import serial` lives inside `_ensure_pyserial()` called at the top of `connect()`. Rationale: machines without the `[hardware]` extras should still be able to `from motodiag.hardware.protocols.kline import KLineAdapter` for type checks, `--help` output, and anything that doesn't actually open a port. Missing-dep error message includes exact `pip install 'motodiag[hardware]'` hint — same pattern Phase 132 used for `markdown`/`xhtml2pdf`.

**5. ~26 tests, fully mocked.**
7 test classes: `TestSlowBaudInit` (5), `TestFastInit` (2), `TestFraming` (5), `TestEchoCancellation` (3), `TestServiceMethods` (6), `TestDefensive` (3), `TestConstants` (2). All use `MagicMock(spec=serial.Serial)` with scripted `read()`/`write()` behavior; `time.sleep` autouse-monkeypatched to no-op so the whole file runs in <100 ms. Zero hardware, zero network, zero API tokens. Wire-level validation deferred to Phase 147 (Gate 6) with a real Honda CBR600RR ECU.

**6. Tight scope — no CLI, no migration, no write services.**
This phase is strictly the protocol module + its tests. `motodiag connect --protocol kline` wiring lands in Phase 140 (connection manager). Tune-writing (SecurityAccess, WriteData) lands in a much later dedicated phase with explicit user confirmations. The `[hardware]` extras entry is already declared from Phase 135 — no `pyproject.toml` change.

Plan docs written to `docs/phases/in_progress/137_implementation.md` and `137_phase_log.md`. Not yet committed or pushed per caller's instruction.
