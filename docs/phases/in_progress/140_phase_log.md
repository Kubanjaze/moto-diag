# MotoDiag Phase 140 — Phase Log

**Status:** 🟡 Planned | **Started:** 2026-04-18
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-18 07:45 — Plan written, v1.0

First user-facing Track E phase. Wires Phase 139's `AutoDetector` + Phases 134-138 adapters into a Click command group so a mechanic can actually pull DTCs off a bike from the terminal — this is the phase that turns hardware from library code into a shippable feature.

**Scope:**
- **New `hardware` CLI group** with 3 subcommands: `scan` (read DTCs + enrich via `dtc_codes` 3-tier fallback), `clear` (Mode 04 with yellow safety warning + confirm), `info` (identify_ecu printout).
- **`HardwareSession` context manager** wrapping `AutoDetector` with `__enter__`/`__exit__` lifecycle — guarantees `disconnect()` fires on exception paths.
- **`MockAdapter`** — concrete `ProtocolAdapter` subclass with configurable DTCs/VIN/ECU state. Used by `--mock` flag (dev/offline test path) AND becomes substrate for Phase 144's full hardware simulator.
- **DTC enrichment:** reuse the 3-tier fallback from `cli/code.py` (make-specific → generic → classifier heuristic) — extract into `knowledge/dtc_lookup.py` if not already shared.
- **No migration, no new DB tables, no AI.** Phase 140 is pure hardware → CLI plumbing. Persistence into `diagnostic_sessions` (bridge to Phase 123 AI diagnose flow) deferred to Phase 145.

**Design non-negotiables:**
1. **`--mock` flag is mandatory for CI + offline dev.** Bypasses `AutoDetector` + pyserial entirely; instantiates `MockAdapter` directly. CLI output shows `[MOCK]` badge so it is unmistakable in logs/screenshots.
2. **Safety warning on `clear`.** Mechanics who clear DTCs before finding root cause lose diagnostic signal — yellow-panel warning before the confirm prompt, reminding them to diagnose first.
3. **`NoECUDetectedError` unpacked into a mechanic-friendly panel.** The `errors=[(name, exception)]` list from Phase 139 must render as a readable per-adapter breakdown ("Tried J1850 → no response; CAN → timeout; KWP2000 → handshake failed"), not a raw traceback.
4. **Rich formatting via existing `theme` module.** Phase 129 already owns the Console singleton + color maps + icons — reuse `get_console()`, `format_severity`, `ICON_OK/WARN/FAIL`.
5. **Context-manager lifecycle.** `HardwareSession.__exit__` calls `disconnect()` unconditionally, swallows cleanup exceptions per Phase 134 ABC contract. Disconnect never masks an earlier error.

**Test plan:**
- ~40 tests in `tests/test_phase140_hardware_cli.py`.
- Happy-path coverage uses `--mock` + `MockAdapter` (real object, real method semantics — not `MagicMock`, so ABC contract drift fails the test rather than silently passes).
- Edge cases (port open failure, NoECUDetectedError rendering, clear-refused, VIN-unavailable, garage empty) use `unittest.mock.patch` on the adapter factories.
- CliRunner-driven, no subprocess, no real pyserial touched.

**Next:** build — can either dispatch to Builder-A (agent-delegated, same pattern as phases 125-139) OR build directly. Given this phase is ~560 LoC across 3 new files + 1 extended (`cli/code.py` DTC helper extraction), medium-complexity — delegate to Builder-A for parallel efficiency with architect trust-but-verify.
