# MotoDiag Phase 140 — Hardware CLI: scan / clear / info

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-18

## Goal

First user-facing Track E phase. Wires Phase 139's `AutoDetector` and Phases 134-138's protocol adapters into a Click command group so a mechanic can plug an OBD dongle into a serial port and actually get DTCs out of a bike — no more library-only code. This is the phase that turns the hardware substrate into a shippable product.

**CLI surface (3 commands under one new `hardware` group):**
- `motodiag hardware scan --port COM3 [--bike SLUG | --make harley] [--baud N] [--timeout 2.0] [--mock]` — auto-detect the ECU, read stored DTCs, print a Rich table with code + description + category + severity (looked up from the `dtc_codes` table + optional make-specific fallback)
- `motodiag hardware clear --port COM3 [--bike SLUG | --make harley] [--yes] [--mock]` — auto-detect, confirm (yellow warning explaining "this clears faults — do NOT clear before diagnosis is complete"), issue Mode 04 clear, report `True`/`False` outcome
- `motodiag hardware info --port COM3 [--bike SLUG | --make harley] [--mock]` — auto-detect, call `identify_ecu()`, print Rich Panel with VIN / ECU part # / software version / supported OBD modes / negotiated protocol name

**Design rule:** no migration, no new DB tables, no AI. Phase 140 is pure hardware → CLI plumbing. Persistence into `diagnostic_sessions` (so a scan can feed Phase 123's `diagnose` workflow) is deliberately deferred to Phase 145 — this phase stays narrow and testable.

Outputs:
- `src/motodiag/hardware/connection.py` (~140 LoC) — `HardwareSession` context manager wrapping `AutoDetector` with `__enter__`/`__exit__` lifecycle + clean error surfacing
- `src/motodiag/hardware/mock.py` (~100 LoC) — `MockAdapter` implementing `ProtocolAdapter` ABC with configurable DTCs/VIN/ECU for `--mock` flag (dev/test path, no real hardware required; also becomes the substrate for Phase 144's full hardware simulator)
- `src/motodiag/cli/hardware.py` (~320 LoC) — `register_hardware(cli)` + 3 subcommands, Rich formatting, DTC enrichment via `knowledge.dtc_repo`
- `tests/test_phase140_hardware_cli.py` (~40 tests) — CliRunner-driven tests for all 3 commands against `MockAdapter` patched in via `unittest.mock.patch`

## Logic

**`HardwareSession(port, make_hint=None, baud=None, timeout_s=2.0, mock=False)`** — context manager over `AutoDetector`:
- On `__enter__`:
  - If `mock=True`, instantiate `MockAdapter()` directly (skip AutoDetector entirely — pure in-memory).
  - Else: `AutoDetector(port, make_hint, timeout_s, baud)` → `.detect()` → adapter + connection
  - Returns the connected `ProtocolAdapter` instance
- On `__exit__`: calls `adapter.disconnect()` unconditionally, swallows any cleanup exceptions (disconnect must never mask earlier errors — Phase 134 ABC contract).
- Re-raises `NoECUDetectedError` unchanged so the CLI layer can catch it and render a helpful panel.

**`MockAdapter`** — concrete `ProtocolAdapter` with configurable state:
- Constructor kwargs: `dtcs: list[str] = None`, `vin: str = None`, `ecu_part: str = None`, `sw_version: str = None`, `supported_modes: list[int] = None`, `clear_returns: bool = True`, `protocol_name: str = "Mock"`
- Default happy-path state: 2 DTCs (`P0115`, `P0300`), VIN `1HD1KHM19NB123456`, ECU `HD-ECM-1234`, sw `1.0.5`, modes `[1, 3, 4, 9]`
- `connect()` sets `_is_connected = True`; raises `ConnectionError` if constructor got `fail_on_connect=True`
- `read_dtcs()` returns the stored list; `clear_dtcs()` empties it + returns `clear_returns`
- `read_pid(pid)` returns `pid * 10` for any PID in `supported_modes` else `None`
- `read_vin()` returns the stored VIN or raises `UnsupportedCommandError` if `vin_unsupported=True`
- `get_protocol_name()` returns the stored name
- Importantly: **not meant for production, only tests + `--mock` flag**. Phase 144 will extend this into a full scriptable simulator.

**`motodiag hardware scan`** — the workhorse:
1. Resolve `--bike SLUG` to `make_hint` via existing `cli/diagnose.py::_resolve_bike_slug` (reuse — don't duplicate).
2. Open `HardwareSession(port, make_hint, baud, timeout_s, mock)`.
3. On `NoECUDetectedError`, print red panel with: port, make hint, per-adapter errors (the `errors=[(name, exception)]` list from Phase 139). Exit 1.
4. On successful connect: call `adapter.read_dtcs()`.
5. Enrich each DTC: look up in `dtc_codes` table (make-scoped first if `make_hint` given, then generic), fall back to `classify_code(dtc)` heuristic if no DB hit. Same 3-tier fallback as Phase 124's `code` command.
6. Render Rich table: columns = Code / Description / Category / Severity / Source (DB|classifier). Severity color-coded via `theme.format_severity`.
7. Print summary footer: N codes / protocol name / VIN if available / hint to clear with `motodiag hardware clear --port <port>`.
8. Context manager exits cleanly; disconnect happens even on exception.

**`motodiag hardware clear`** — safety-first:
1. Same port + make_hint resolution.
2. Show yellow warning panel: "⚠ This will clear all stored DTCs from the ECU. Clearing before diagnosis is complete may lose valuable information. Mechanics should only clear AFTER identifying and fixing the root cause."
3. If not `--yes`: `click.confirm("Proceed?", default=False)`.
4. Open session, call `adapter.clear_dtcs()`.
5. Print green success panel on `True`, red "ECU refused clear (may require ignition on / engine off)" on `False`.

**`motodiag hardware info`** — minimal:
1. Open session, call `adapter.identify_ecu()` — returns a dict with VIN / ecu_part / sw_version / supported_modes.
2. Render Rich Panel: Protocol, VIN, ECU Part #, SW Version, Supported OBD Modes (formatted as bitmap with checkmarks for present modes).
3. No safety prompts — read-only.

**DTC enrichment reuse:** `cli/code.py::_resolve_dtc_info(code, make_hint)` already does the 3-tier fallback; extract that into a shared helper under `knowledge/dtc_lookup.py` if not already there. If it's already there — reuse. If not — move-and-import rather than copy-paste.

**`--mock` flag** — critical for CI + offline dev:
- Bypasses AutoDetector entirely.
- `HardwareSession(..., mock=True)` short-circuits to `MockAdapter`.
- CLI shows `[MOCK]` badge in the output so it's unmistakable.
- Tests use this path for happy-path coverage; `unittest.mock.patch` on the real adapter factories for edge cases.

## Key Concepts

- **CLI framework:** Click — new subcommand group `motodiag hardware` registered via `register_hardware(cli)` pattern already used by Phases 122/127/130/131/132.
- **Context manager lifecycle:** `HardwareSession.__enter__` / `__exit__` — standard Python pattern; ensures `disconnect()` fires on exception paths.
- **Rich formatting reuse:** `theme.get_console()`, `theme.format_severity`, `theme.ICON_OK`/`ICON_WARN`/`ICON_FAIL` — established in Phase 129.
- **DTC enrichment fallback:** 3-tier lookup (make-specific → generic → classifier heuristic) — same pattern as Phase 124.
- **Mock adapter pattern:** concrete `ProtocolAdapter` subclass with configurable state; not a `MagicMock` — real objects with real method semantics, so tests catch ABC contract drift (e.g. if `read_pid` signature changes, `MockAdapter` fails to instantiate, not silently passes).
- **Error surfacing:** `NoECUDetectedError` carries `port`, `make_hint`, `errors: list[(name, exception)]` — the CLI's job is to unpack that list into a user-friendly diagnostic panel, not a raw traceback.

## Verification Checklist

- [ ] `MockAdapter` instantiates (ABC contract satisfied — all 8 abstract methods implemented).
- [ ] `HardwareSession(mock=True)` yields a connected `MockAdapter` without touching `AutoDetector` or `pyserial`.
- [ ] `hardware scan --mock` prints a Rich table with ≥ 2 DTCs, exits 0.
- [ ] `hardware scan --mock --bike harley-glide-2015` passes `make_hint="harley"` into the session (verified via patching `AutoDetector` and asserting kwargs).
- [ ] `hardware scan` on unknown port raises `NoECUDetectedError` → rendered as red panel with per-adapter errors, exit 1.
- [ ] DTC enrichment: `P0115` in scan output shows the correct description from `dtc_codes` table.
- [ ] DTC enrichment fallback: a code NOT in the DB (e.g. `P9999`) falls through to classifier heuristic with a "Source: classifier" column indicator.
- [ ] `hardware clear --mock` without `--yes` prompts for confirm; with `--yes` skips prompt.
- [ ] `hardware clear --mock --yes` reports success.
- [ ] `hardware clear --mock --yes` when `MockAdapter(clear_returns=False)` reports red refusal.
- [ ] `hardware info --mock` prints VIN / ECU / sw version / supported modes.
- [ ] `hardware info --mock` when VIN is `None` shows "VIN: not available" (not a crash).
- [ ] Context manager `__exit__` calls `disconnect()` even when the command body raises.
- [ ] `--help` on the group and each subcommand works.
- [ ] All existing Track D / Gate 5 regression tests still pass.

## Risks

- **DTC lookup helper location:** `cli/code.py` has an inline `_resolve_dtc_info`-like flow; extracting a shared helper might touch Phase 124's code. If so: keep the Phase 124 CLI call path unchanged, factor the shared logic into `knowledge/dtc_lookup.py`, and have both CLIs import from there. If `cli/code.py` cannot cleanly extract — just copy the 3-tier fallback locally (~15 LoC) and note the duplication as a Phase 145 cleanup item.
- **`AutoDetector` requires a `port` that exists:** Phase 139's tests use `MagicMock` adapters; real pyserial will raise `SerialException` on `port="/dev/noSuchPort"` BEFORE the protocol adapter even gets called. Phase 140 tests must mock `pyserial.Serial` (or the adapter factories) rather than passing fake port strings to the real detector. `--mock` flag bypasses this entirely, which is the intended happy-path test vector.
- **CLI-level error UX drift:** Phase 139 designed `NoECUDetectedError` with a programmatic `errors` list. Phase 140 must unpack that into something mechanic-friendly ("Tried J1850 → no response. Tried CAN → timeout. Tried KWP2000 → handshake failed."). Plain `str(exc)` would lose the detail — use an explicit formatter.
- **Windows serial port naming:** `COM3` vs `/dev/ttyUSB0` — don't validate port format in Phase 140; pass it through to pyserial and let that layer decide. The error messages already say "could not open port" clearly enough.
- **Mock flag discoverability:** mechanics who run `motodiag hardware scan` without a dongle will get a confusing serial error. Add `--mock` to `--help` prominently and surface it in the error panel ("hint: use --mock to test without hardware").
- **First user-facing hardware command → bike reality check:** the `--bike SLUG` option expects the garage to have entries. For green-field deployments this errors. Use the same "no garage entries yet — run `motodiag garage add` first" pattern from Phase 125 when slug resolution fails.
