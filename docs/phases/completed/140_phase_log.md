# MotoDiag Phase 140 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-18 | **Completed:** 2026-04-18
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

---

### 2026-04-18 08:30 — Build complete (Builder-A + Architect trust-but-verify)

Tenth agent-delegated phase. **Builder-A's cleanest first pass yet** — no sandbox block this time, so Builder actually ran the test suite before reporting: 40 tests passed locally in 21.24s. Architect's trust-but-verify reproduced 40/40 in 24.52s, zero iterative fixes needed.

**Files shipped:**
- `src/motodiag/hardware/mock.py` (249 LoC) — `MockAdapter(ProtocolAdapter)` with configurable `dtcs`/`vin`/`ecu_part`/`sw_version`/`supported_modes`/`clear_returns`/`protocol_name`/`fail_on_connect`/`vin_unsupported` kwargs. All 8 ABC methods satisfied. Additional `identify_info()` helper (additive, not a contract change). Docstring marks it "not for production — substrate for `--mock` flag and Phase 144 simulator."
- `src/motodiag/hardware/connection.py` (255 LoC) — `HardwareSession` context manager wrapping `AutoDetector`. Three construction paths: real (AutoDetector → detect), mock (MockAdapter default state), adapter_override (test injection). `__exit__` swallows disconnect failures per Phase 134 ABC contract — never masks propagating exception.
- `src/motodiag/knowledge/dtc_lookup.py` (147 LoC) — `resolve_dtc_info(code, make_hint)` 3-tier fallback (db_make → db_generic → classifier). `source` discriminator checks the returned row's `.make` field to accurately distinguish make-specific hits from generic fallthroughs inside the existing `get_dtc()` internal cascade.
- `src/motodiag/cli/hardware.py` (556 LoC) — `register_hardware(cli)` + 3 Click subcommands (scan/clear/info). Reuses `_resolve_bike_slug` from `cli.diagnose`, `get_console()` + `format_severity` + `ICON_*` from `cli.theme`. Rich table for scan, Rich Panel for clear + info. `[MOCK]` yellow badge when `--mock`. `NoECUDetectedError` handler unpacks `errors=[(name, exception)]` into per-adapter breakdown with actionable "hint: use --mock to test without hardware" footer.
- `tests/test_phase140_hardware_cli.py` (805 LoC) — 40 tests across 6 classes: `TestMockAdapterContract` (5: ABC-satisfaction + state round-trip), `TestHardwareSession` (6: mock, override, disconnect-on-exception, NoECUDetectedError propagation), `TestScanCommand` (10: happy path, bike resolution, DB vs classifier enrichment, unknown port, empty list, mutex `--bike`/`--make`, slug-not-found remediation), `TestClearCommand` (8: safety warning, prompt flow, yes-skip, success/refusal panels, abort, slug-not-found), `TestInfoCommand` (6: all-fields/VIN-None/VIN-unsupported/empty-modes paths), `TestDTCLookup` (5: source discriminator semantics).

**File modified:** `src/motodiag/cli/main.py` — added `from motodiag.cli.hardware import register_hardware` and `register_hardware(cli)` call after cache registration.

**Deviations from plan (all reasonable, documented in 140_implementation.md v1.1):**
1. **DTC lookup extraction deferred.** `cli/code.py` has renderer-entangled lookup flow (populates `common_causes`/`fix_summary`/`code_format` beyond `DTCInfo`'s schema). Clean extraction would require touching renderer too — out of scope. `cli/hardware.py` uses new helper; `cli/code.py` unchanged; TODO noted for Phase 145 cleanup.
2. **`MockAdapter.identify_info()` helper.** Additive-only — ABC unchanged. Session method delegates to this on mock path, `AutoDetector.identify_ecu()` on real path.
3. **`_resolve_bike_slug` imported as underscore-private.** Matches existing cross-module reuse patterns in codebase.
4. **`source` discriminator nuance.** `get_dtc()`'s internal fallback meant `db_make` → `db_generic` downgrade logic had to live in `resolve_dtc_info` — checks row's `.make` field post-query.
5. **`classify_code` tuple unpacking.** `(code_format, system_description)` → Builder put `system_description` into `DTCInfo.category` (semantic-meaningful "coolant_temp" rather than "OBD2_GENERIC" for the UI column).
6. **Test DB fixture.** `autouse` fixture monkey-patches `init_db` to tmp_path — follows Phase 128's `cli_db` pattern.

**Verification:** 40/40 phase tests passed locally (Builder) + reproduced in trust-but-verify (Architect, 24.52s). Regression smoke samples: Phase 139 (31) + Phase 124 (33) still 64/64 passing. Full regression launched in background.

**Next:** full regression confirmation, finalize to v1.1, move docs to completed/, update project implementation.md + phase_log.md + ROADMAP.md, commit + push, then proceed to Phase 141 (live sensor data streaming).
