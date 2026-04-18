# MotoDiag Phase 143 — Phase Log

**Status:** 🟡 Planned | **Started:** 2026-04-18 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-18 10:00 — Plan written, v1.0

Planner-143 drafted v1.0 for Phase 143 — real-time terminal dashboard. Settles the Textual-TUI debt Phase 129 deferred ("Textual full TUI explicitly deferred"). Full-screen TUI over Phase 141's SensorStreamer + Phase 142's RecordingManager. Lands in parallel with 141/142 — plan assumes both contracts will be in place when Phase 143 Builder starts.

**Scope:**
- New optional dep `textual>=0.40` behind `motodiag[dashboard]`. Missing → ClickException with install hint. Core install unchanged.
- New `src/motodiag/hardware/dashboard.py` (~500 LoC). Five classes + `DashboardSource` Protocol:
  - `DashboardApp(textual.App)` — 3-column grid (gauges/chart/DTC) + status bar.
  - `GaugeWidget(Static)` — reactive widget, clamped bar, color thresholds, `None`→`--`.
  - `PidChart(Static)` — rolling Braille-sparkline, `history_len` deque, `set_pid` reset.
  - `DTCPanel(Static)` — 5s poll via `set_interval`; Rich Table inside; stale after 15s.
  - `LiveDashboardSource(adapter, pids, hz)` wraps SensorStreamer; `ReplayDashboardSource(recording_id, speed)` walks recording.
- New CLI subcommand `motodiag hardware dashboard` (~150 LoC in `cli/hardware.py`). `--port`/`--replay` mutex, `--bike`/`--make`, `--mock`, `--pids`, `--hz`, `--speed` (replay-only). Textual import inside callback — Textual-less installs still register subcommand.
- Recording integration: Ctrl+R toggles Phase 142 recording mid-session; `[●REC]` indicator; auto-stop on exit.
- Keybindings: Ctrl+Q quit, Ctrl+R record, D toggle DTC, 1-6 chart PID. Mechanic-hands-dirty friendly.
- No migration, no new DB tables, no AI.

**Design non-negotiables:**
1. **Textual or nothing.** Rich Live covered the one-liner; full-screen deserves the framework.
2. **Textual is optional.** `motodiag[dashboard]`; core install unchanged.
3. **Replay is first-class.** Same UI live + replay.
4. **Zero live hardware in tests.** MagicMock adapters + SensorReading fixtures + `App.run_test()` harness.
5. **Async-first.** Textual owns the event loop; `set_interval(...)`, not threads.

**Test plan (~45 tests, 7 classes):**
- `TestDashboardApp` (10) — mount, reactive updates, Ctrl+Q/R/D, number keys, DTC panel, status bar, ReplayCompleteMessage.
- `TestDashboardSources` (8) — live wraps streamer, replay walks recording + respects speed + fires completion.
- `TestGaugeWidget` (6) — clamping, thresholds, unit, None placeholder, reactive redraw.
- `TestPidChart` (5) — deque windowing, sparkline chars, unit/label, None gaps, set_pid reset.
- `TestDTCPanel` (4) — empty/populated, stale timeout, interval refresh.
- `TestDashboardCommand` (10) — mock launch, replay launch, speed validation, mutex, PID parsing, help.
- `TestTextualMissing` (2) — lazy-import hint, other subcommands unaffected.

All tests `pytest.mark.asyncio`, skipped via `pytest.importorskip("textual")` at module top.

**Dependencies:**
- Phase 141 — SensorStreamer / SensorReading. Single adaptation in `LiveDashboardSource.start`.
- Phase 142 — RecordingManager. Single adaptation in `action_toggle_recording`.
- `cli/hardware.py` shared with 141/142/144/145 — all additive via `register_<subgroup>` pattern. Alphabetical order: clear, dashboard, info, log, scan, stream.
- No schema migration. No new DB tables. Schema version unchanged.

**Open questions flagged:**
1. Phase 141 `SensorStreamer.subscribe` vs `.on_reading`? Adapt at build.
2. Phase 142 RecordingManager API shape (start/stop/ID vs context-manager)? Plan assumes former.
3. Textual version pin `>=0.40,<1.0` — confirm tighter pin preferred.
4. PID default starter set alignment with Phase 141 — confirm `0x0C,0x05,0x11,0x42`.
5. Textual `run_test()` harness API stability across 0.4x→0.6x.
6. Subcommand ordering in `register_hardware` — alphabetical for clean `--help`.

**Next:** wait for 141/142 to merge, lift final adapter/recording signatures, then auto-iterate or hand to Builder-A.

### 2026-04-18 15:30 — Build complete (Builder-143 + Architect trust-but-verify)

Fourteenth agent-delegated phase. Builder-143 shipped: new `hardware/dashboard.py` (1282 LoC — lazy Textual import with stubs for missing-dep mode, `DashboardSource` Protocol + `LiveDashboardSource` + `ReplayDashboardSource`, `GaugeWidget`/`PidChart`/`DTCPanel`/`StatusBar` widgets, `DashboardApp` with 3-column layout + keybindings ctrl+q/ctrl+r/d/1-6, `ReplayCompleteMessage`), extended `cli/hardware.py` +233 LoC additive (`_require_textual`, `_validate_dashboard_args`, `_parse_dashboard_pids`, `dashboard` subcommand), `pyproject.toml` +4 LoC (`dashboard = ["textual>=0.40,<1.0"]` optional extra + appended to `all`), new `tests/test_phase143_dashboard.py` (814 LoC, 46 tests across 7 classes with `pytest.importorskip("textual")` at module top).

Sandbox blocked Python for Builder. Architect installed Textual 6.5.0 + ran trust-but-verify.

### 2026-04-18 15:35 — Bug fix #1: GaugeWidget numeric display not clamped

**Issue:** `test_value_clamps_to_min_max` failed. Expected `100.00` (clamped) but widget rendered `250.00` (unclamped).

**Root cause:** `GaugeWidget.render()` correctly computed `clamped = max(min, min(max, numeric))` and used `clamped` for the bar fill fraction, but the numeric display line used `{numeric:>7.2f}` (unclamped).

**Fix:** Changed `{numeric:>7.2f}` → `{clamped:>7.2f}` on line 694 of `hardware/dashboard.py`.

**Files:** `src/motodiag/hardware/dashboard.py` line 694.

**Verified:** `.venv/Scripts/python.exe -m pytest tests/test_phase143_dashboard.py -q` → `46 passed in 16.38s`.

**Build-complete sign-off:** Phase 143 GREEN. Dashboard Textual TUI shipped.
