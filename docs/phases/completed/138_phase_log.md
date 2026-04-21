# MotoDiag Phase 138 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-17 | **Completed:** 2026-04-18
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

### 2026-04-18 06:30 — Build complete

Wave 2 Builder shipped `src/motodiag/hardware/protocols/j1850.py` (~600 LoC — overshot ~420 target per "detailed and meticulous" standard; extra is bridge-specific command table docs + multi-ECM coordination commentary + Harley model-year coverage narrative) plus `tests/test_phase138_j1850.py` with 27 tests across 6 classes. Target: pre-2011 Harley-Davidson — pre-2007 Sportster / Big Twin Evo / TC88 (pure Harley-proprietary J1850), 2007-2010 EFI HDs (Delphi / Magneti Marelli ECMs, partial SAE Mode 03 bolted on). 2011+ HDs use CAN (Phase 136, not this phase).

No direct bit-banging — adapter talks serial to hard-wired bridge devices (Scan Gauge II / Daytona Twin Tec TCFI tuner / Dynojet Power Commander diagnostic mode / Harley Digital Tech II clones), bridge talks J1850 VPW (10.4 kbps Variable Pulse Width — NOT the 41.6 kbps PWM Ford variant) to the bike. Multi-ECM diagnostic story is this adapter's unique value: single `read_dtcs()` call queries ECM (P-codes) + BCM (B-codes) + 2007+ Touring ABS (C-codes) via three separate module addresses on the same bus, merges into a flat list (ECM → BCM → ABS order). Supplementary `read_dtcs_by_module() -> dict[str, list[str]]` for labeled access.

Deviations from plan: ABC signature reconciliation (same Wave 2 pattern). `clear_dtcs(module=None)` accepts optional module kwarg while preserving `bool` ABC return. `read_pid` raises `NotImplementedError` with a Phase-141 pointer (Harley PIDs require per-bridge knowledge — deferred to live sensor streaming work). `read_vin` raises `UnsupportedCommandError` (pre-2008 HDs lacked Mode 09 PID 02 — Phase 146's `diagnose` step 4 surfaces this as a WARN with "frame neck sticker" guidance). Bridge variants: `daytona` / `scangauge` / `dynojet` / `generic` (plan had longer names; Builder shortened for CLI usability).

27 tests passed locally. Running total: 2543 tests. Zero live API tokens.

**Commit:** `15c658d` (Phases 133-139: Gate 5 PASSED + Track E hardware substrate).

### 2026-04-18 07:00 — Documentation finalization

`implementation.md` already at v1.1 with Results + Deviations. Verification Checklist marked `[x]` after Gate 6 integration test. Moved to `docs/phases/completed/`.

Key finding: the bridge-device abstraction is the pragmatic win of this phase. Real J1850 silicon is rare and consumer ELM327 clones handle Harley-proprietary frames poorly — by designing around the bridge layer (which every real-world HD mechanic already owns), Phase 138 ships usable Harley diagnostics without requiring anyone to buy a purpose-built J1850 transceiver. The `_BRIDGE_COMMANDS` dict + variant kwarg makes future bridge additions a data change, not a code change.
