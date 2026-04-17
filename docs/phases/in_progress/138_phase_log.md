# MotoDiag Phase 138 — Phase Log

**Status:** 🔲 Planned | **Started:** 2026-04-17 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-17 00:00 — Plan written, v1.0
Third concrete `ProtocolAdapter` in Track E: J1850 VPW for pre-2011 Harley-Davidson ECMs. Follows Phase 136 (CAN / ISO 15765) and Phase 137 (K-line / KWP2000) in the hardware protocol stack, all built on Phase 134's `ProtocolAdapter` abstraction.

**Scope locked:**
- New `src/motodiag/hardware/protocols/j1850.py` (~420 LoC): `J1850Adapter` class, bridge-command tables, Harley DTC parser, multi-module (ECM + BCM + ABS) response handling.
- New `tests/test_phase138_j1850.py` (~22 tests, 6 classes): `TestMockSerial`, `TestJ1850AdapterConnect`, `TestJ1850AdapterReadDTC`, `TestJ1850DtcParsing`, `TestJ1850BridgeVariants`, `TestJ1850ClearAndInfo`.
- `pyproject.toml`: confirm/add `hardware = ["pyserial>=3.5"]` in optional-dependencies.
- No migration, no schema change, no new CLI command.

**Key design decisions recorded in v1.0 plan:**
1. **10.4 kbps VPW only** — `J1850_VPW_BAUD = 10400`. Not the 41.6 kbps PWM Ford variant. Pre-2011 Harleys are all VPW.
2. **Bridge abstraction over direct bus access**: Harleys need a hard-wired bridge device (Daytona Twin Tec, Scan Gauge II, Dynojet PC) that already speaks J1850 to the bike; our adapter speaks serial to the bridge. `_BRIDGE_COMMANDS` dict isolates bridge-specific byte differences — extensible by dict entry, not subclass. Initial support: `daytona_twin_tec`, `scan_gauge_ii`, `dynojet_pc`, `generic_j1850`.
3. **Multi-ECM polling (ECM + BCM + ABS)**: single `read_dtc()` call queries three separate module addresses sequentially (parallel would collide on the shared bus). Results merged in order with per-module `module` field on each `DTCReading`. ECM → P-codes (powertrain), BCM → B-codes (body / security / lights), ABS → C-codes (chassis, Touring + later Dyna only).
4. **Prefix override over SAE nibble**: Harley's ECM occasionally emits wrong high-nibble for non-P codes; we know from the module address which prefix is correct and override (BCM response → B-codes guaranteed). Future-proofs against firmware variations.
5. **Lazy `pyserial` import** via `_ensure_pyserial()` with ClickException install-hint, mirroring Phase 132's `_ensure_markdown_installed()` pattern. Mechanics using only cloud / KB features don't pay the dependency cost.
6. **`serial_factory` DI**: `MockSerial` injected via constructor, not monkeypatch. Test file has zero dependency on real `pyserial`. Zero real hardware required for any test. Zero live API tokens.
7. **Sequential, not parallel, module polling**: J1850 VPW is a shared-bus collision-arbitrated protocol. Parallel reads via `asyncio.gather` would corrupt frames. Sequential matches Digital Tech II / Twin Tec real-world behavior.
8. **Lenient frame parser**: `_parse_j1850_response` tolerates optional header byte, optional count byte, optional checksum, whitespace, case, and embedded prompt byte. Harley bridges are notoriously inconsistent about framing. Robust error-recovery (retry, reconnect) is Phase 146's job.
9. **`read_live_data` raises `NotImplementedError`**: live PIDs on J1850 require per-bike PID maps (Phase 141). Phase 140 (fault code read/clear) is the only consumer of Phase 138 and does not call live-data.
10. **Harley model coverage documented**: pre-2007 Sportster / Big Twin Evo / TC88 (pure Harley-proprietary J1850); 2007-2010 EFI Harleys (Delphi / Magneti Marelli ECMs, partial OBD-II Mode 03 bolted on); 2011+ → CAN (Phase 136, not this phase).

**Risks flagged:**
- Phase 134 `ProtocolAdapter` contract may drift — plan is self-describing so Builder can adapt at build-time with v1.2 deviation entry.
- `_BRIDGE_COMMANDS` byte tables are research-based, not shop-floor calibrated — Phase 147 (Gate 6) is the real-hardware integration test. Expect byte corrections then. **By design** — Phase 138 is about adapter shape, not byte-perfect compatibility with every bridge firmware revision.
- 2.5s default timeout may be tight for cold-bus cranking-on ECMs (pre-2007 Sportsters can take 3+ seconds on first query). `timeout_s` is exposed on the constructor for override; Phase 146 adds smart retry.

**Verification plan (summary):**
- All 22 tests in `test_phase138_j1850.py` pass without `pyserial` installed (mock-only).
- Full regression pass (Phases 01-132) — zero regressions expected since this is a pure additive module.
- Zero live API tokens burned.

Next step: Builder (agent or direct) implements per plan, runs tests locally, updates to v1.1.
