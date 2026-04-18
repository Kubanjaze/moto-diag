"""Phase 143 — Real-time Textual TUI dashboard tests.

Seven test classes, ~35-45 tests. Whole module skips when Textual is
not installed so CI without the ``motodiag[dashboard]`` extra still
runs the rest of the Phase 140-142 regression suite.

Test strategy
-------------

- Widget tests call :meth:`render` directly. No Textual App mounting
  required for :class:`GaugeWidget`, :class:`PidChart`, :class:`DTCPanel`
  value-update / render-output behavior.
- App-level tests use Textual's :meth:`App.run_test` async harness
  which returns an :class:`~textual.pilot.Pilot`. Because
  ``pytest-asyncio`` is not a project dependency we wrap each async
  test body in :func:`asyncio.run` via the :func:`_asyncio_test`
  helper rather than the ``@pytest.mark.asyncio`` decorator.
- CLI tests use :class:`~click.testing.CliRunner` with
  :meth:`DashboardApp.run` monkey-patched to a :class:`MagicMock` —
  no actual TUI is painted, we just verify the right source /
  arguments made it into the constructor.
- :class:`TestTextualMissing` patches ``TEXTUAL_AVAILABLE = False`` to
  exercise the install-hint path.

Every test avoids real serial I/O via :class:`MockAdapter` + direct
dict fixtures so the suite runs under 2 s on a developer laptop.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, List, Optional
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("textual")

import click  # noqa: E402 — after importorskip
from click.testing import CliRunner  # noqa: E402

from motodiag.cli.hardware import register_hardware  # noqa: E402
from motodiag.core.database import init_db  # noqa: E402
from motodiag.hardware import dashboard as dashboard_mod  # noqa: E402
from motodiag.hardware.dashboard import (  # noqa: E402
    DashboardApp,
    DTCPanel,
    GaugeWidget,
    LiveDashboardSource,
    PidChart,
    ReplayCompleteMessage,
    ReplayDashboardSource,
    StatusBar,
)
from motodiag.hardware.mock import MockAdapter  # noqa: E402


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _asyncio_test(coro_fn: Callable[..., Any]) -> Callable[..., Any]:
    """Run an async test body via :func:`asyncio.run`.

    Removes the need for ``pytest-asyncio``. The decorated test stays
    a sync ``def test_…`` from pytest's perspective; the inner async
    function is driven by a fresh event loop each call so side-effects
    from one test don't leak into another.
    """

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return asyncio.run(coro_fn(*args, **kwargs))

    wrapper.__name__ = coro_fn.__name__
    wrapper.__doc__ = coro_fn.__doc__
    return wrapper


def _make_cli():
    """Build a minimal Click group with only ``hardware`` attached."""

    @click.group()
    def root() -> None:
        """test root"""

    register_hardware(root)
    return root


@pytest.fixture(autouse=True)
def _patch_init_db(monkeypatch, tmp_path):
    """Point ``init_db`` at a per-test tmp DB (mirrors Phase 141/142)."""
    db_path = str(tmp_path / "phase143.db")
    init_db(db_path)

    from motodiag.cli import hardware as hw_mod

    original_init_db = hw_mod.init_db

    def _patched(*args, **kwargs):
        if args or kwargs:
            return original_init_db(db_path, *args[1:], **kwargs)
        return original_init_db(db_path)

    monkeypatch.setattr(hw_mod, "init_db", _patched)
    yield db_path


class _FakeReading:
    """Minimal duck-typed sensor reading for widget-level tests.

    Mirrors the five attributes :class:`DashboardApp._handle_reading`
    consumes (``pid``, ``pid_hex``, ``name``, ``value``, ``unit``).
    """

    __slots__ = ("pid", "pid_hex", "name", "value", "unit", "status",
                 "raw", "captured_at")

    def __init__(
        self,
        pid: int,
        pid_hex: str,
        name: str,
        value: Optional[float],
        unit: str = "",
    ) -> None:
        self.pid = pid
        self.pid_hex = pid_hex
        self.name = name
        self.value = value
        self.unit = unit
        self.status = "ok" if value is not None else "unsupported"
        self.raw = None
        self.captured_at = datetime.now(timezone.utc)


def _fake_batch(*pairs: tuple[int, Optional[float]]) -> List[_FakeReading]:
    """Build a list of :class:`_FakeReading` from ``(pid, value)`` pairs."""
    out: list[_FakeReading] = []
    for pid, value in pairs:
        out.append(
            _FakeReading(
                pid=pid,
                pid_hex=f"0x{pid:02X}",
                name=f"PID 0x{pid:02X}",
                value=value,
                unit="rpm" if pid == 0x0C else "",
            )
        )
    return out


# ===========================================================================
# 1. TestDashboardApp — App-level integration via Textual's run_test harness
# ===========================================================================


class _StubSource:
    """Async :class:`DashboardSource` stub used by App-level tests.

    Lets each test feed batches manually via :meth:`push` so we don't
    depend on real hardware or the SensorStreamer timing loop.
    """

    protocol_name = "ISO 15765-4"
    vin = "1HD1KHM19NB123456"
    is_finite = False
    progress = None

    def __init__(self, dtcs: Optional[List[str]] = None) -> None:
        self._subscribers: list[Callable[[List[Any]], None]] = []
        self._dtcs: list[str] = list(dtcs or [])
        self.start_called: int = 0
        self.stop_called: int = 0

    async def start(self) -> None:
        self.start_called += 1

    async def stop(self) -> None:
        self.stop_called += 1

    def subscribe(self, cb: Callable[[List[Any]], None]) -> None:
        self._subscribers.append(cb)

    def read_dtcs(self) -> List[str]:
        return list(self._dtcs)

    def push(self, batch: List[Any]) -> None:
        for cb in list(self._subscribers):
            cb(batch)


class TestDashboardApp:
    """App-level integration via Textual's ``run_test`` async harness."""

    @_asyncio_test
    async def test_mount_composes_all_widgets(self):
        source = _StubSource()
        app = DashboardApp(source=source, pids=[0x0C, 0x05, 0x11, 0x42])
        async with app.run_test() as pilot:
            # Let compose + on_mount settle.
            await pilot.pause()
            # Source was started exactly once.
            assert source.start_called == 1
            # Gauges, chart, DTC panel, status bar all present.
            gauges = [w for w in app._gauges.values()]
            assert len(gauges) == 4
            assert app._chart is not None
            assert app._dtc_panel is not None
            assert app._status_bar is not None

    @_asyncio_test
    async def test_gauge_updates_on_reading(self):
        source = _StubSource()
        app = DashboardApp(source=source, pids=[0x0C, 0x05])
        async with app.run_test() as pilot:
            await pilot.pause()
            source.push(_fake_batch((0x0C, 1725.0), (0x05, 90.0)))
            await pilot.pause()
            assert app._gauges["0x0C"].value == 1725.0
            assert app._gauges["0x05"].value == 90.0

    @_asyncio_test
    async def test_dtc_panel_populates_on_mount(self):
        source = _StubSource(dtcs=["P0115", "P0300"])
        app = DashboardApp(source=source, pids=[0x0C])
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app._dtc_panel is not None
            assert app._dtc_panel._codes == ["P0115", "P0300"]

    @_asyncio_test
    async def test_status_bar_shows_protocol_and_vin(self):
        source = _StubSource()
        app = DashboardApp(source=source, pids=[0x0C])
        async with app.run_test() as pilot:
            await pilot.pause()
            rendered = app._status_bar.render()
            assert "ISO 15765-4" in rendered
            assert "1HD1KHM19NB123456" in rendered

    @_asyncio_test
    async def test_ctrl_q_exits_cleanly(self):
        source = _StubSource()
        app = DashboardApp(source=source, pids=[0x0C])
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("ctrl+q")
            await pilot.pause()
        # On unmount the source was stopped.
        assert source.stop_called >= 1

    @_asyncio_test
    async def test_ctrl_r_starts_recording(self):
        source = _StubSource()
        rec_mgr = MagicMock()
        rec_mgr.start_recording.return_value = 7
        app = DashboardApp(
            source=source, pids=[0x0C, 0x05], recording_manager=rec_mgr,
        )
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("ctrl+r")
            await pilot.pause()
            rec_mgr.start_recording.assert_called_once()
            kwargs = rec_mgr.start_recording.call_args.kwargs
            assert kwargs["vehicle_id"] is None
            assert kwargs["protocol_name"] == source.protocol_name
            assert "0x0C" in kwargs["pids"]
            assert kwargs["label"].startswith("dashboard-")
            assert app._active_recording_id == 7

    @_asyncio_test
    async def test_ctrl_r_twice_stops_recording(self):
        source = _StubSource()
        rec_mgr = MagicMock()
        rec_mgr.start_recording.return_value = 42
        app = DashboardApp(
            source=source, pids=[0x0C], recording_manager=rec_mgr,
        )
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("ctrl+r")
            await pilot.pause()
            await pilot.press("ctrl+r")
            await pilot.pause()
            rec_mgr.stop_recording.assert_called_once_with(42)
            assert app._active_recording_id is None

    @_asyncio_test
    async def test_number_key_switches_chart_pid(self):
        source = _StubSource()
        app = DashboardApp(source=source, pids=[0x0C, 0x05, 0x11, 0x42])
        async with app.run_test() as pilot:
            await pilot.pause()
            # Default select is PID index 0 (0x0C).
            assert app._chart.current_pid == "0x0C"
            await pilot.press("2")
            await pilot.pause()
            assert app._chart.current_pid == "0x05"
            await pilot.press("4")
            await pilot.pause()
            assert app._chart.current_pid == "0x42"

    @_asyncio_test
    async def test_d_toggles_dtc_panel(self):
        source = _StubSource(dtcs=["P0115"])
        app = DashboardApp(source=source, pids=[0x0C])
        async with app.run_test() as pilot:
            await pilot.pause()
            initial = str(app._dtc_panel.styles.display)
            await pilot.press("d")
            await pilot.pause()
            assert str(app._dtc_panel.styles.display) != initial
            await pilot.press("d")
            await pilot.pause()
            assert str(app._dtc_panel.styles.display) == initial

    @_asyncio_test
    async def test_replay_complete_message_handled(self):
        source = _StubSource()
        app = DashboardApp(source=source, pids=[0x0C])
        async with app.run_test() as pilot:
            await pilot.pause()
            # Direct invocation — we only verify the handler doesn't
            # throw and that the status bar picks up the completed
            # progress value.
            app.on_replay_complete_message(ReplayCompleteMessage())
            assert app._status_bar.progress_value == 1.0


# ===========================================================================
# 2. TestDashboardSources — live + replay wrappers
# ===========================================================================


class TestDashboardSources:
    """LiveDashboardSource + ReplayDashboardSource behaviour."""

    @_asyncio_test
    async def test_live_source_wraps_streamer(self):
        """LiveDashboardSource walks a streamer iterator and emits."""
        adapter = MockAdapter(pid_values={0x0C: 0x1AF8})

        class _FakeStreamer:
            def __init__(self, *a, **kw):
                pass

            def iter_readings(self):
                yield _fake_batch((0x0C, 1725.0))
                yield _fake_batch((0x0C, 1730.0))

        received: list[list[Any]] = []
        source = LiveDashboardSource(
            adapter, pids=[0x0C], hz=100.0,
            streamer_factory=lambda a, p, h: _FakeStreamer(),
        )
        source.subscribe(lambda batch: received.append(batch))
        await source.start()
        # Drive the event loop until both batches arrive or 1s passes.
        for _ in range(200):
            if len(received) >= 2:
                break
            await asyncio.sleep(0.01)
        await source.stop()
        assert len(received) >= 1
        assert received[0][0].pid_hex == "0x0C"

    def test_live_source_is_infinite(self):
        adapter = MockAdapter()
        source = LiveDashboardSource(adapter, pids=[0x0C], hz=5.0)
        assert source.is_finite is False
        assert source.progress is None

    def test_live_source_surfaces_protocol_name(self):
        adapter = MockAdapter(protocol_name="ISO 15765-4 (CAN)")
        source = LiveDashboardSource(adapter, pids=[0x0C], hz=5.0)
        assert source.protocol_name == "ISO 15765-4 (CAN)"

    @_asyncio_test
    async def test_replay_source_walks_recording(self):
        """ReplayDashboardSource calls load_recording(int_id)."""
        t0 = datetime(2026, 4, 18, 12, 0, 0, tzinfo=timezone.utc)
        rows = [
            {"captured_at": t0.isoformat(), "pid_hex": "0x0C",
             "value": 1725.0, "raw": 0x1AF8, "unit": "rpm"},
            {"captured_at": (t0 + timedelta(seconds=0.2)).isoformat(),
             "pid_hex": "0x0C", "value": 1730.0, "raw": 0x1AF9,
             "unit": "rpm"},
        ]
        metadata = {"protocol_name": "ISO 15765-4",
                    "dtcs_csv": "P0115", "vin": None}
        fake_mgr = MagicMock()
        fake_mgr.load_recording.return_value = (metadata, iter(rows))
        source = ReplayDashboardSource(
            recording_id=5, speed=100.0,
            manager_factory=lambda: fake_mgr,
        )
        received: list[list[Any]] = []
        source.subscribe(lambda batch: received.append(batch))
        await source.start()
        # Playback at 100x of 0.2s = 0.002s per step, plus task
        # scheduling overhead — 0.5s is plenty.
        for _ in range(100):
            if len(received) >= 2:
                break
            await asyncio.sleep(0.01)
        await source.stop()
        fake_mgr.load_recording.assert_called_once_with(5)
        assert len(received) >= 1

    def test_replay_source_is_finite(self):
        fake_mgr = MagicMock()
        source = ReplayDashboardSource(
            recording_id=1, speed=1.0,
            manager_factory=lambda: fake_mgr,
        )
        assert source.is_finite is True

    def test_replay_source_rejects_zero_speed(self):
        with pytest.raises(ValueError):
            ReplayDashboardSource(recording_id=1, speed=0.0)

    def test_replay_source_read_dtcs_returns_stored(self):
        fake_mgr = MagicMock()
        fake_mgr.load_recording.return_value = (
            {"protocol_name": "X", "dtcs_csv": "P0115,P0300", "vin": None},
            iter([]),
        )
        source = ReplayDashboardSource(
            recording_id=1, speed=10.0,
            manager_factory=lambda: fake_mgr,
        )
        # Before start, DTCs come from the initial empty list.
        assert source.read_dtcs() == []

    @_asyncio_test
    async def test_replay_source_populates_dtcs_after_start(self):
        fake_mgr = MagicMock()
        fake_mgr.load_recording.return_value = (
            {"protocol_name": "X", "dtcs_csv": "P0115,P0300", "vin": None},
            iter([]),
        )
        source = ReplayDashboardSource(
            recording_id=1, speed=10.0,
            manager_factory=lambda: fake_mgr,
        )
        await source.start()
        try:
            assert source.read_dtcs() == ["P0115", "P0300"]
        finally:
            await source.stop()


# ===========================================================================
# 3. TestGaugeWidget — render / reactive / color-zone behavior
# ===========================================================================


class TestGaugeWidget:
    """Pure-widget tests — no App mount required."""

    def test_value_none_renders_dim_dash(self):
        g = GaugeWidget("RPM", 0.0, 8000.0, "rpm")
        rendered = g.render()
        assert "--" in rendered
        assert "RPM" in rendered

    def test_value_clamps_to_min_max(self):
        g = GaugeWidget("Throttle", 0.0, 100.0, "%")
        g.value = 250.0
        rendered = g.render()
        # Clamped to 100.0.
        assert "100.00" in rendered
        g.value = -30.0
        rendered = g.render()
        assert "0.00" in rendered

    def test_color_zones_change_at_thresholds(self):
        g = GaugeWidget(
            "RPM", 0.0, 100.0, "rpm",
            color_thresholds=[(0.5, "green"), (0.8, "yellow"), (1.0, "red")],
        )
        g.value = 25.0
        assert "green" in g.render()
        g.value = 70.0
        assert "yellow" in g.render()
        g.value = 95.0
        assert "red" in g.render()

    def test_unit_is_rendered(self):
        g = GaugeWidget("Coolant", -40.0, 215.0, "\u00b0C")
        g.value = 95.0
        assert "\u00b0C" in g.render()

    def test_rejects_invalid_min_max(self):
        with pytest.raises(ValueError):
            GaugeWidget("Bad", 100.0, 0.0, "")
        with pytest.raises(ValueError):
            GaugeWidget("Bad", 10.0, 10.0, "")

    def test_rejects_bad_color_thresholds(self):
        with pytest.raises(ValueError):
            GaugeWidget("Bad", 0.0, 100.0, "",
                        color_thresholds=[(0.5, "green")])  # final < 1.0
        with pytest.raises(ValueError):
            GaugeWidget("Bad", 0.0, 100.0, "", color_thresholds=[])


# ===========================================================================
# 4. TestPidChart — history_len window / Braille chars / set_pid
# ===========================================================================


class TestPidChart:

    def test_history_len_windowed(self):
        chart = PidChart(history_len=5)
        chart.set_pid("0x0C", "RPM", "rpm")
        for v in [1000.0, 1100.0, 1200.0, 1300.0, 1400.0, 1500.0]:
            chart.push(v)
        # Only last 5 survive.
        assert len(chart._deque) == 5
        assert list(chart._deque) == [1100.0, 1200.0, 1300.0, 1400.0, 1500.0]

    def test_braille_chars_in_output(self):
        chart = PidChart(history_len=10)
        chart.set_pid("0x0C", "RPM", "rpm")
        for v in [0.0, 25.0, 50.0, 75.0, 100.0]:
            chart.push(v)
        rendered = chart.render()
        # At least one block char present.
        assert any(ch in rendered for ch in "\u2581\u2582\u2583\u2584"
                   "\u2585\u2586\u2587\u2588")

    def test_unit_and_label_rendered(self):
        chart = PidChart(history_len=10)
        chart.set_pid("0x0C", "Engine RPM", "rpm")
        chart.push(1500.0)
        rendered = chart.render()
        assert "Engine RPM" in rendered
        assert "0x0C" in rendered
        assert "rpm" in rendered

    def test_none_creates_gap(self):
        chart = PidChart(history_len=10)
        chart.set_pid("0x0C", "RPM", "rpm")
        chart.push(100.0)
        chart.push(None)
        chart.push(200.0)
        # Deque carries the explicit None.
        assert list(chart._deque) == [100.0, None, 200.0]

    def test_set_pid_resets_history(self):
        chart = PidChart(history_len=10)
        chart.set_pid("0x0C", "RPM", "rpm")
        chart.push(1500.0)
        chart.push(1600.0)
        assert len(chart._deque) == 2
        chart.set_pid("0x05", "Coolant", "\u00b0C")
        assert len(chart._deque) == 0
        assert chart.current_pid == "0x05"


# ===========================================================================
# 5. TestDTCPanel — poll / stale / interval refresh
# ===========================================================================


class TestDTCPanel:

    def test_empty_list_renders(self):
        source = _StubSource(dtcs=[])
        panel = DTCPanel(source)
        panel._refresh()
        rendered = panel.render()
        assert "DTCs (0)" in rendered
        assert "no codes" in rendered

    def test_populated_list_renders(self):
        source = _StubSource(dtcs=["P0115", "P0300"])
        panel = DTCPanel(source)
        panel._refresh()
        rendered = panel.render()
        assert "P0115" in rendered
        assert "P0300" in rendered
        assert "DTCs (2)" in rendered

    def test_stale_after_timeout(self):
        source = _StubSource(dtcs=["P0115"])
        panel = DTCPanel(source, stale_after_s=0.0)
        panel._refresh()
        # Force the "last_ok" into the past by backdating.
        panel._last_ok = datetime.now(timezone.utc) - timedelta(seconds=30)
        rendered = panel.render()
        assert "stale" in rendered

    def test_interval_refresh_count(self):
        source = _StubSource(dtcs=["P0115"])
        panel = DTCPanel(source)
        panel._refresh()
        panel._refresh()
        panel._refresh()
        assert panel._poll_count == 3


# ===========================================================================
# 6. TestDashboardCommand — CliRunner, monkey-patched DashboardApp.run
# ===========================================================================


class TestDashboardCommand:
    """CLI-layer tests — DashboardApp.run is stubbed to a MagicMock."""

    def _patched_runner(self, monkeypatch):
        """Return a (CliRunner, captured_args_list, run_mock) triple."""
        captured: list[dict] = []

        from motodiag.hardware import dashboard as dash_mod

        # Capture constructor args without actually running the TUI.
        original_init = dash_mod.DashboardApp.__init__

        def _fake_init(self, *args, **kwargs):
            captured.append({"args": args, "kwargs": kwargs})
            # Call original __init__ via a bypassing path — we don't
            # want Textual's full App init (needs terminal).
            self._source = kwargs.get("source", args[0] if args else None)
            self._pids = list(kwargs.get(
                "pids", args[1] if len(args) > 1 else [],
            ))
            self._recording_manager = kwargs.get(
                "recording_manager",
                args[2] if len(args) > 2 else None,
            )
            self._vehicle_id = kwargs.get("vehicle_id")
            self._make_hint = kwargs.get("make_hint")

        run_mock = MagicMock()
        monkeypatch.setattr(dash_mod.DashboardApp, "__init__", _fake_init)
        monkeypatch.setattr(dash_mod.DashboardApp, "run", run_mock)
        return CliRunner(), captured, run_mock

    def test_mock_live_constructs_live_source(self, monkeypatch):
        runner, captured, run_mock = self._patched_runner(monkeypatch)
        result = runner.invoke(
            _make_cli(),
            ["hardware", "dashboard", "--port", "COM3", "--mock",
             "--pids", "0x0C,0x05"],
        )
        assert result.exit_code == 0, result.output
        assert run_mock.called
        assert len(captured) == 1
        source = captured[0]["kwargs"]["source"]
        assert isinstance(source, LiveDashboardSource)
        assert captured[0]["kwargs"]["pids"] == [0x0C, 0x05]

    def test_replay_constructs_replay_source(self, monkeypatch):
        runner, captured, run_mock = self._patched_runner(monkeypatch)

        # Patch ReplayDashboardSource to accept any recording_id without
        # touching a DB.
        from motodiag.hardware import dashboard as dash_mod

        observed: dict = {}
        original = dash_mod.ReplayDashboardSource

        def _spy(*args, **kwargs):
            observed["args"] = args
            observed["kwargs"] = kwargs
            # Build a MagicMock that satisfies the constructor contract.
            inst = MagicMock(spec=original)
            inst.is_finite = True
            inst._set_app = MagicMock()
            return inst

        monkeypatch.setattr(dash_mod, "ReplayDashboardSource", _spy)
        result = runner.invoke(
            _make_cli(),
            ["hardware", "dashboard", "--replay", "42", "--speed", "5"],
        )
        assert result.exit_code == 0, result.output
        assert observed["args"] == (42,)
        assert observed["kwargs"]["speed"] == 5.0

    def test_speed_out_of_range_rejected(self, monkeypatch):
        self._patched_runner(monkeypatch)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "dashboard", "--replay", "1", "--speed", "200"],
        )
        assert result.exit_code != 0
        assert "speed" in result.output.lower()

    def test_speed_without_replay_rejected(self, monkeypatch):
        self._patched_runner(monkeypatch)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "dashboard", "--port", "COM3", "--mock",
             "--speed", "2.5"],
        )
        assert result.exit_code != 0
        assert "speed" in result.output.lower()

    def test_port_and_replay_mutex(self, monkeypatch):
        self._patched_runner(monkeypatch)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "dashboard", "--port", "COM3", "--replay", "1"],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()

    def test_pids_parses_hex_list(self, monkeypatch):
        runner, captured, run_mock = self._patched_runner(monkeypatch)
        result = runner.invoke(
            _make_cli(),
            ["hardware", "dashboard", "--port", "COM3", "--mock",
             "--pids", "0x0C,0x05,0x42"],
        )
        assert result.exit_code == 0, result.output
        assert captured[0]["kwargs"]["pids"] == [0x0C, 0x05, 0x42]

    def test_garbage_pids_rejected(self, monkeypatch):
        self._patched_runner(monkeypatch)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "dashboard", "--port", "COM3", "--mock",
             "--pids", "garbage"],
        )
        assert result.exit_code != 0
        assert "garbage" in result.output.lower()

    def test_hz_zero_rejected(self, monkeypatch):
        self._patched_runner(monkeypatch)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "dashboard", "--port", "COM3", "--mock",
             "--hz", "0"],
        )
        assert result.exit_code != 0
        assert "hz" in result.output.lower()

    def test_hz_too_high_rejected(self, monkeypatch):
        self._patched_runner(monkeypatch)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "dashboard", "--port", "COM3", "--mock",
             "--hz", "25"],
        )
        assert result.exit_code != 0
        assert "hz" in result.output.lower()

    def test_help_exits_zero(self):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "dashboard", "--help"],
        )
        assert result.exit_code == 0
        assert "dashboard" in result.output.lower()
        assert "--replay" in result.output
        assert "--speed" in result.output

    def test_bike_with_replay_rejected(self, monkeypatch):
        self._patched_runner(monkeypatch)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "dashboard", "--replay", "1",
             "--bike", "my-harley"],
        )
        assert result.exit_code != 0
        assert "bike" in result.output.lower()


# ===========================================================================
# 7. TestTextualMissing — install-hint path
# ===========================================================================


class TestTextualMissing:
    """Ensure missing-Textual degrades gracefully + install hint shows."""

    def test_dashboard_missing_textual_exits_with_hint(self, monkeypatch):
        # Simulate Textual not being importable by patching the gate.
        monkeypatch.setattr(dashboard_mod, "TEXTUAL_AVAILABLE", False)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "dashboard", "--mock", "--port", "COM3"],
        )
        assert result.exit_code != 0
        assert "Textual is required" in result.output
        assert "motodiag[dashboard]" in result.output

    def test_other_hardware_subcommands_unaffected(self, monkeypatch):
        # Even with TEXTUAL_AVAILABLE False, other subcommands work.
        monkeypatch.setattr(dashboard_mod, "TEXTUAL_AVAILABLE", False)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "scan", "--port", "COM3", "--mock"],
        )
        assert result.exit_code == 0, result.output
