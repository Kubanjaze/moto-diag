# MotoDiag Phase 143 — Real-Time Terminal Dashboard (Textual TUI)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-18

## Goal

Track E's full-screen TUI. Settles the Textual debt Phase 129 deferred. Ships `motodiag hardware dashboard` — live-mode (real adapter or `--mock`) or replay-mode (Phase 142 recording). Big gauges for RPM/coolant/TPS/battery, rolling sparkline for any PID, DTC panel with 5s polling + stale-after-15s indicator, status bar with protocol + VIN + record indicator. Ctrl+R toggles mid-session recording.

CLI: `motodiag hardware dashboard [--port PORT] [--bike SLUG | --make MAKE] [--mock] [--replay REC_ID] [--speed N] [--pids CSV] [--hz 5.0] [--baud N] [--timeout 2.0]`. `--port`/`--replay` mutex; `--speed` replay-only; `--mock`/`--bike`/`--make` live-only.

Outputs:
- New optional dep `textual>=0.40` behind `motodiag[dashboard]`. Missing → ClickException with install hint. Core install unchanged.
- `src/motodiag/hardware/dashboard.py` (~500 LoC): `DashboardApp(App)`, `GaugeWidget(Static)` reusable reactive, `PidChart(Static)` rolling sparkline, `DTCPanel(Static)` periodic poll with stale indicator, `DashboardSource(Protocol)` interface with `LiveDashboardSource` + `ReplayDashboardSource` concretes.
- `src/motodiag/cli/hardware.py` +~150 LoC (new `dashboard` subcommand + helpers). Additive only.
- `pyproject.toml` +3 LoC (`dashboard = ["textual>=0.40,<1.0"]` optional group + append to `all`).
- `tests/test_phase143_dashboard.py` (~35-45 tests across 7 classes).

No migration, no new DB tables, no AI.

## Logic

### Lazy Textual import strategy

Top of `dashboard.py`:
```python
try:
    from textual.app import App, ComposeResult
    from textual.widgets import Static, Header, Footer
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    App = object; Static = object  # stub bases so tests exercising install-hint don't explode on class defs
```

CLI subcommand body imports `motodiag.hardware.dashboard` inside the callback — so `cli/hardware.py` stays Textual-free and other subcommands register fine without Textual.

`_require_textual()` helper raises `click.ClickException("Textual is required for the dashboard. Install with: pip install 'motodiag[dashboard]'")`.

### `DashboardSource` protocol (PEP 544)

```python
class DashboardSource(Protocol):
    protocol_name: str
    vin: Optional[str]
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    def subscribe(self, cb: Callable[[SensorReading], None]) -> None: ...
    def read_dtcs(self) -> list[str]: ...
    @property
    def is_finite(self) -> bool: ...
    @property
    def progress(self) -> Optional[float]: ...
```

**`LiveDashboardSource(adapter, pids, hz)`:** wraps Phase 141's `SensorStreamer`. `start()` attaches listener to `SensorStreamer.on_reading` and launches tick loop. `stop()` signals halt + awaits cleanup. `read_dtcs()` delegates to `self._adapter.read_dtcs()`. `is_finite=False`, `progress=None`.

**`ReplayDashboardSource(recording_id, speed=1.0)`:** wraps Phase 142's `RecordingManager.load_recording`. Loads recording iterator, async-task walks it, inter-sample sleep `(next_ts - prev_ts) / self._speed`. `read_dtcs()` returns recording's stored DTC snapshot. `is_finite=True`, `progress=_samples_played/_total`. On exhaustion, posts `ReplayCompleteMessage` to app.

### Widgets

**`GaugeWidget(Static)`:** `value: reactive[Optional[float]] = reactive(None)`. Constructor `(label, min, max, unit, color_thresholds=[(0.6, "green"), (0.85, "yellow"), (1.0, "red")])`. `render()` produces big-text label + clamped bar + unit suffix + color from fraction-of-range thresholds. `value=None` → dim `--`.

**`PidChart(Static)`:** `history_len=120` `collections.deque(maxlen=history_len)` of floats (None = gap). `render()` picks sparkline chars from Braille Unicode `U+2581..U+2588` normalized to observed min/max. `set_pid(pid, label, unit)` swaps tracked PID + clears deque.

**`DTCPanel(Static)`:** `on_mount` installs `self.set_interval(5.0, self._refresh)`. `_refresh()` calls `source.read_dtcs()` + `knowledge.dtc_lookup.resolve_dtc_info` enrichment → Rich Table inside Static. `stale_after_s=15.0` — if no successful poll in 15s, header shows `[dim]DTCs (N) — stale[/dim]`. Adapter exception → keep last snapshot, mark stale, don't kill dashboard.

### DashboardApp(App)

Layout (CSS grid, 3 columns × 2 rows): Gauges (left) | PidChart (center-big) | DTCPanel (right) | Status bar (bottom full-width).

BINDINGS:
- `ctrl+q` → `action_quit` (if recording live, stop recording first; then `self.exit()`).
- `ctrl+r` → `action_toggle_recording` (start/stop Phase 142 recording; `[●REC]` reactive).
- `d` → `action_toggle_dtc` (hide/show DTCPanel via `styles.display="none"`).
- `1`-`6` → `action_select_pid(idx)` (indexes into `self._pids`; out-of-range silent no-op with 1s status hint).

`on_mount`: `self._source.subscribe(self._handle_reading)`, `await self._source.start()`, `set_interval(0.1, self._tick_replay_progress)` (replay only).

`on_unmount`: `await self._source.stop()`. If recording live, `stop_recording` called.

All periodic work uses `self.set_interval(...)` — no threads, no `asyncio.create_task` outside Textual's machinery.

### Recording integration

Ctrl+R toggles: first press calls `self._recording_manager.start_recording(adapter=..., label=f"dashboard-{ts}", pids=self._pids)` + stashes id; future readings append via `append_samples`. Second press calls `stop_recording` + clears id. Auto-stop on quit/unmount — never leave dangling.

**Phase 142 contract assumption:** `RecordingManager.start_recording(...)/append_samples(id, samples)/stop_recording(id)/load_recording(id) -> iterator`. If Phase 142 API differs (e.g. context-manager), Builder shims; `_active_recording_id` state is UI-only, decoupled.

### CLI wiring

```python
@hardware_group.command("dashboard")
@click.option("--port", default=None)
@click.option("--bike", default=None)
@click.option("--make", "make", default=None)
@click.option("--mock", is_flag=True)
@click.option("--replay", "replay_id", default=None)
@click.option("--speed", type=float, default=1.0, show_default=True)
@click.option("--pids", "pids_raw", default="0x0C,0x05,0x11,0x42", show_default=True)
@click.option("--hz", type=float, default=5.0, show_default=True)
@click.option("--baud", type=int, default=None)
@click.option("--timeout", "timeout_s", type=float, default=2.0, show_default=True)
def dashboard_cmd(...):
    _require_textual()
    _validate_dashboard_args(port, replay_id, speed, bike, make, mock)
    pids = _parse_pids(pids_raw)
    if replay_id:
        from ...dashboard import DashboardApp, ReplayDashboardSource
        source = ReplayDashboardSource(recording_id=replay_id, speed=speed)
        app = DashboardApp(source=source, pids=pids, recording_manager=None)
        app.run(); return
    make_hint, _vehicle = _resolve_make_hint(bike, make)
    if bike and _vehicle is None:
        _bike_not_found(get_console(), bike); raise click.exceptions.Exit(1)
    from ...dashboard import DashboardApp, LiveDashboardSource
    from ...recorder import RecordingManager
    with HardwareSession(port, make_hint, baud, timeout_s, mock) as adapter:
        source = LiveDashboardSource(adapter, pids, hz)
        rec_mgr = RecordingManager()
        app = DashboardApp(source=source, pids=pids, recording_manager=rec_mgr)
        app.run()
```

**Validation:** `--port` xor `--replay`; `--speed` requires `--replay`; `--speed` in `(0.1, 100.0]`; `--bike`/`--make` live-only; `--mock` incompatible with `--replay`; `--hz` in `[0.5, 20.0]`; `--pids` accepts hex/decimal with ClickException on bad token.

## Key Concepts

- **Textual or nothing.** Rich Live covered Phase 141 one-liner; full-screen deserves a framework that solved layout/redraw/async/keybindings. No rolling our own.
- **Reactive widgets.** `textual.reactive` triggers redraw on set — no manual `refresh()`.
- **`DashboardSource` protocol** abstracts live vs replay. Same UI, two drivers.
- **Lazy Textual import.** Core install unchanged. Other `hardware` subcommands unaffected.
- **`set_interval` over threads.** Textual owns the event loop.
- **Mechanic-hands-dirty keybindings.** Single keystrokes; Ctrl for destructive; no mouse, no Alt-combos.
- **Replay is first-class.** Same UI. Mechanic replays a colleague's recording at their desk.
- **Recording-from-dashboard.** Ctrl+R mid-session — spots something unusual, hits record, has the window forever.
- **DTC panel decoupled from gauge ticks.** 5s poll interval independent of 5 Hz gauge rate. Momentary disconnect marks panel stale; gauges keep updating; recovers on next successful poll.

## Verification Checklist

- [x] `pip install motodiag[dashboard]` pulls `textual>=0.40`.
- [x] `pip install motodiag` (no extras) succeeds; `motodiag hardware dashboard --mock` exits 1 with install hint.
- [x] With Textual installed, `--mock` launches TUI with gauges + DTC panel + status bar.
- [x] Ctrl+Q exits cleanly — adapter disconnected, no leaked ports.
- [x] Ctrl+R starts/stops Phase 142 recording; `[●REC]` indicator visible.
- [x] Exiting with active recording auto-stops (no orphans).
- [x] Number keys 1-6 swap chart PID; out-of-range silent.
- [x] `D` toggles DTC panel.
- [x] DTC panel polls every 5s; stale after 15s.
- [x] Gauges clamp to [min, max]; color zones change at thresholds; None → `--`.
- [x] PidChart windows to `history_len`; Braille chars; None creates gaps.
- [x] LiveDashboardSource wraps SensorStreamer; ReplayDashboardSource walks recording.
- [x] Replay speed respects original hz at default; 10× arrives faster; exhaustion fires completion.
- [x] `--port`/`--replay` mutex; `--mock`/`--replay` mutex; `--bike`/`--replay` mutex.
- [x] `--speed` outside `(0.1, 100.0]` rejected; `--speed` without `--replay` rejected.
- [x] `--pids` parses hex/decimal; bad token → ClickException.
- [x] `--hz` outside `[0.5, 20.0]` rejected.
- [x] ~45 tests pass; Textual skipped via `pytest.importorskip`.
- [x] Phase 140/141/142 tests pass unchanged.
- [x] `cli/hardware.py` diff additive; existing subcommands byte-identical.
- [x] `hardware --help` lists `dashboard`.
- [x] No schema migration.

## Risks

- **Textual API drift across 0.40 → 0.60+.** Pin `textual>=0.40,<1.0`; adjust `Pilot.press`/etc. at build time; flag in v1.1.
- **Phase 141/142 API drift.** Source wrappers are the only 2 places touching 141/142 — contained changes.
- **Phase 141/142 not merged at plan time.** Explicit contract here; drift → v1.1 patch.
- **Replay `--speed` precision at 100×** drops below asyncio scheduler granularity. Accept "approximately"; tests use wide tolerance; 100.0 cap prevents meaningless higher.
- **Windows Terminal vs cmd.exe vs PowerShell ISE rendering.** Textual needs ANSI + Unicode. Doc in `--help`: "Windows Terminal or modern pwsh required." Degrades gracefully (boxes vs sparklines), not crashes.
- **`set_interval` drift under heavy load.** Phase 143 is read-only UI; no heavy main-thread work. DTC panel's `read_dtcs()` can be slow; stale indicator engages.
- **Signal-handler conflicts.** Phase 143 installs no signal handlers; relies on Textual's Ctrl+C.
- **Recording lifecycle on crash.** `on_unmount` normally fires even on exception; outer `HardwareSession.__exit__` too. Hard SIGKILL leaks — Phase 146 recovery will handle.
- **Number-keys collision** with Textual widget navigation. If collision arises, bindings move to Alt+1..6. One-line fallback.
- **Color-blind mechanics.** Red/yellow/green canonical; accessibility via future `--palette=high-contrast`.

## Deviations from Plan

1. **LoC overshot on `dashboard.py`** (1282 vs ~500 target). Extra content: lazy Textual import plus stubs for missing-dep environments, extensive reactive widget docstrings, sparkline rendering commentary, async `DashboardSource` Protocol + two concretes (`LiveDashboardSource` with asyncio task fanout, `ReplayDashboardSource` with bisect-based time walking).
2. **`cli/hardware.py` additions** came in at +233 LoC (vs ~150 planned) — subcommand callback with `_require_textual`, `_validate_dashboard_args`, `_parse_dashboard_pids`, and lazy-import fencing so Textual-less installs can still register the subcommand and fail cleanly with an install hint.
3. **Bug fix #1 (Architect trust-but-verify): `GaugeWidget.render()` numeric display not clamped.** The widget correctly computed `clamped = max(min, min(max, numeric))` for the bar fill fraction, but the numeric display line used `{numeric:>7.2f}` (unclamped). Out-of-range values showed their raw number next to a clamped bar — confusing UI. Fixed by changing `{numeric:>7.2f}` → `{clamped:>7.2f}` on line 694. Test `test_value_clamps_to_min_max` now passes.
4. **Textual version pin landed at `>=0.40,<1.0`** as planned. Textual 6.5.0 was the version used during trust-but-verify; no API breaks.

## Results

| Metric | Value |
|--------|------:|
| New files | 2 (`src/motodiag/hardware/dashboard.py` 1282 LoC, `tests/test_phase143_dashboard.py` 814 LoC) |
| Modified files | 2 (`cli/hardware.py` +233 LoC additive, `pyproject.toml` +4 LoC dashboard extra) |
| New tests | 46 across 7 classes (passed locally 46/46 in 16.38s post-fix) |
| Total test count after | 2712 |
| Live API tokens burned | 0 |
| Bug fixes during build | 1 (GaugeWidget numeric display clamping) |

**Commit:** `8e49ecd` (Phase 143: Real-time Textual TUI dashboard — 46/46 GREEN).

**Key finding:** the `DashboardSource` Protocol abstraction is the cleanest reuse-win in Track E — the same `DashboardApp` widget tree drives live mode (Phase 141 `SensorStreamer` wrapped by `LiveDashboardSource`) and replay mode (Phase 142 `RecordingManager.load_recording(int_id)` wrapped by `ReplayDashboardSource`) with zero UI code duplication. Mechanics replay a colleague's recording at their desk with the same widgets they see live on the bike. The async model via `set_interval` (not threads) also avoided Windows terminal cursor issues that bit Phase 129's Rich Live — Textual owns the event loop end-to-end.
