"""Real-time Textual TUI dashboard (Phase 143).

Fourth Track E phase. Ships the full-screen terminal dashboard the
mechanic lives in while troubleshooting — big gauges for the primary
engine vitals, a rolling Braille sparkline for any single PID, a
periodic-polling DTC panel with a stale-after-15s indicator, and a
status bar with protocol + VIN + record-state.

The module is structured around three pieces:

- :class:`DashboardSource` — ``Protocol`` (PEP 544) abstracting live
  hardware from replay playback. ``on_reading`` is implemented via
  :meth:`~DashboardSource.subscribe`, so widgets register callbacks and
  the source fans out each tick to every subscriber. Two concrete
  implementations ship: :class:`LiveDashboardSource` wraps Phase 141's
  :class:`~motodiag.hardware.sensors.SensorStreamer` iterator,
  :class:`ReplayDashboardSource` wraps Phase 142's
  :meth:`~motodiag.hardware.recorder.RecordingManager.load_recording`
  iterator and walks it at a caller-chosen speed.
- Reusable widgets — :class:`GaugeWidget`, :class:`PidChart`,
  :class:`DTCPanel` — all Textual :class:`~textual.widgets.Static`
  subclasses. Each is independently testable and can be dropped into
  other Track E UIs.
- :class:`DashboardApp` — the Textual :class:`~textual.app.App` that
  composes the widgets, routes source events into widget reactive
  values, and owns keybindings + recording lifecycle.

Textual is a **soft** dependency behind the ``motodiag[dashboard]``
extra. The top-level lazy import installs stub base classes on an
``ImportError`` so every class definition still parses; classes that
inherit from a stub (i.e. ``object``) are never instantiated in a
no-Textual environment — the CLI's :func:`_require_textual` gate
enforces that. Tests that exercise the widgets use
``pytest.importorskip("textual")`` so the whole module skips when the
dep isn't installed.

Design notes
------------

- **Iterator, not callback.** Phase 141's ``SensorStreamer`` is a one-
  shot iterator (:meth:`iter_readings`), not an event bus. The
  :class:`LiveDashboardSource` therefore owns an asyncio task that
  walks the iterator and fans out each yielded batch via the
  :meth:`DashboardSource.subscribe` hook.
- **Replay is first-class.** ``ReplayDashboardSource`` sleeps between
  samples using the real inter-sample delta divided by the playback
  speed. A speed of 0 would be divide-by-zero; the CLI validator caps
  speed to ``(0.1, 100.0]`` before construction.
- **Recording integration is lazy.** Ctrl+R toggles recording via the
  manager passed in at construction; replay mode passes ``None`` which
  degrades the keybinding to a silent no-op.
- **No threads.** Every periodic job uses :meth:`App.set_interval` so
  Textual's event loop owns scheduling.
- **Stale DTC panel.** The panel polls every 5s. If a poll doesn't
  complete within 15s the header renders ``[dim]DTCs (N) — stale[/dim]``
  so the mechanic knows the code list on screen may be behind reality.
  The last successful snapshot stays visible — we never clear it on
  transient adapter hiccups.
"""

from __future__ import annotations

import asyncio
import collections
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Iterator, List, Optional, Protocol

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lazy Textual import
# ---------------------------------------------------------------------------


try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Container, Horizontal, Vertical
    from textual.message import Message
    from textual.reactive import reactive
    from textual.widgets import Footer, Header, Static

    TEXTUAL_AVAILABLE = True
except ImportError:  # pragma: no cover — covered by TestTextualMissing
    TEXTUAL_AVAILABLE = False
    # Stubs so the class definitions below parse. Classes that inherit
    # from these stubs are never instantiated without Textual installed
    # — ``_require_textual`` guards the CLI entry point.
    App = object  # type: ignore[assignment,misc]
    ComposeResult = object  # type: ignore[assignment,misc]
    Binding = object  # type: ignore[assignment,misc]
    Container = object  # type: ignore[assignment,misc]
    Horizontal = object  # type: ignore[assignment,misc]
    Vertical = object  # type: ignore[assignment,misc]
    Message = object  # type: ignore[assignment,misc]
    Footer = object  # type: ignore[assignment,misc]
    Header = object  # type: ignore[assignment,misc]
    Static = object  # type: ignore[assignment,misc]

    def reactive(default, *args, **kwargs):  # type: ignore[misc]
        """Stub for ``textual.reactive.reactive`` when Textual is absent."""
        return default


# ---------------------------------------------------------------------------
# Braille sparkline alphabet
# ---------------------------------------------------------------------------
#
# Eight vertical "block" glyphs at increasing heights. Picked by
# :class:`PidChart` per sample by normalizing the current value onto
# this range. Using the Unicode 1/8 block set (U+2581..U+2588) instead
# of true Braille because most Windows Terminal fonts render the blocks
# reliably; Braille-proper can go missing.
_SPARK_CHARS: tuple[str, ...] = (
    "\u2581",  # ▁
    "\u2582",  # ▂
    "\u2583",  # ▃
    "\u2584",  # ▄
    "\u2585",  # ▅
    "\u2586",  # ▆
    "\u2587",  # ▇
    "\u2588",  # █
)


# ---------------------------------------------------------------------------
# DashboardSource protocol + concrete implementations
# ---------------------------------------------------------------------------


class DashboardSource(Protocol):
    """Contract the :class:`DashboardApp` consumes.

    Hides the distinction between live hardware polling and recording
    playback. Both implementations funnel ``SensorReading`` batches to
    every subscriber registered via :meth:`subscribe`. ``start`` is
    async so implementations that spawn an asyncio task (both do in
    practice) can ``await`` any initial handshake before returning.
    """

    protocol_name: str
    vin: Optional[str]

    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    def subscribe(
        self, callback: Callable[[List[Any]], None]
    ) -> None: ...

    def read_dtcs(self) -> List[str]: ...

    @property
    def is_finite(self) -> bool: ...

    @property
    def progress(self) -> Optional[float]: ...


class _SubscriberMixin:
    """Shared callback-registry logic for both dashboard sources.

    Not a protocol-runtime helper — purely an implementation detail so
    :class:`LiveDashboardSource` and :class:`ReplayDashboardSource`
    don't each re-implement the subscribe / emit loop.
    """

    def __init__(self) -> None:
        self._subscribers: list[Callable[[List[Any]], None]] = []

    def subscribe(self, callback: Callable[[List[Any]], None]) -> None:
        """Register a reading-batch callback.

        Callbacks fire with the full list the source just produced
        (live tick, or a single-reading batch built from one JSONL
        row). Exceptions in a callback are logged + suppressed so one
        misbehaving widget does not break the dashboard.
        """
        self._subscribers.append(callback)

    def _emit(self, batch: List[Any]) -> None:
        for cb in list(self._subscribers):
            try:
                cb(batch)
            except Exception:  # noqa: BLE001
                logger.exception("dashboard subscriber raised; ignoring")


class LiveDashboardSource(_SubscriberMixin):
    """Wrap a live :class:`~motodiag.hardware.sensors.SensorStreamer`.

    Owns an asyncio task that walks the streamer's
    :meth:`~motodiag.hardware.sensors.SensorStreamer.iter_readings`
    iterator in an executor (so the blocking ``time.sleep`` inside
    the streamer does not pin the event loop) and fans each tick out
    to subscribers.

    Parameters
    ----------
    adapter:
        Connected Phase 134 protocol adapter.
    pids:
        List of PIDs to stream.
    hz:
        Poll rate in ticks per second (1-20 typical).
    streamer_factory:
        Optional injection point for tests — callable ``(adapter, pids,
        hz) -> iterable-of-lists``. Defaults to
        :class:`~motodiag.hardware.sensors.SensorStreamer`.
    """

    is_finite: bool = False
    progress: Optional[float] = None

    def __init__(
        self,
        adapter: Any,
        pids: List[int],
        hz: float = 5.0,
        streamer_factory: Optional[Callable[..., Any]] = None,
    ) -> None:
        super().__init__()
        self._adapter = adapter
        self._pids: List[int] = list(pids)
        self._hz: float = float(hz)
        self._protocol_name: str = self._safe_protocol_name(adapter)
        self._vin: Optional[str] = self._safe_vin(adapter)
        self._task: Optional[asyncio.Task] = None
        self._stop_flag: bool = False
        self._streamer_factory = streamer_factory

    @property
    def protocol_name(self) -> str:
        return self._protocol_name

    @property
    def vin(self) -> Optional[str]:
        return self._vin

    @staticmethod
    def _safe_protocol_name(adapter: Any) -> str:
        try:
            return str(adapter.get_protocol_name())
        except Exception:  # noqa: BLE001
            return "unknown"

    @staticmethod
    def _safe_vin(adapter: Any) -> Optional[str]:
        try:
            return adapter.read_vin()
        except Exception:  # noqa: BLE001
            return None

    def _build_streamer(self) -> Any:
        if self._streamer_factory is not None:
            return self._streamer_factory(self._adapter, self._pids, self._hz)
        from motodiag.hardware.sensors import SensorStreamer

        return SensorStreamer(self._adapter, self._pids, self._hz)

    async def start(self) -> None:
        """Spawn the walk-iterator asyncio task."""
        self._stop_flag = False
        streamer = self._build_streamer()
        self._task = asyncio.create_task(self._run(streamer))

    async def _run(self, streamer: Any) -> None:
        """Walk the streamer iterator + emit until stopped."""
        try:
            iterator: Iterator[List[Any]] = iter(streamer.iter_readings())
        except Exception:  # noqa: BLE001
            logger.exception("LiveDashboardSource: streamer setup failed")
            return

        loop = asyncio.get_event_loop()

        def _next_batch() -> Optional[List[Any]]:
            try:
                return next(iterator)
            except StopIteration:
                return None

        while not self._stop_flag:
            try:
                batch = await loop.run_in_executor(None, _next_batch)
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                logger.exception("LiveDashboardSource: read tick failed")
                # Pause a beat before retrying so we don't busy-loop on
                # a pathologically failing adapter.
                await asyncio.sleep(1.0 / max(self._hz, 1.0))
                continue
            if batch is None:
                # Iterator exhausted (rare for live; SensorStreamer is
                # infinite). Just stop emitting.
                break
            self._emit(batch)
            # Yield back to the event loop so widget redraw can paint.
            await asyncio.sleep(0)

    async def stop(self) -> None:
        """Cancel the walker task and wait for clean shutdown."""
        self._stop_flag = True
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._task = None

    def read_dtcs(self) -> List[str]:
        """Delegate to the adapter. Exceptions surface to the caller."""
        try:
            return list(self._adapter.read_dtcs())
        except Exception:  # noqa: BLE001
            logger.exception("LiveDashboardSource: read_dtcs failed")
            raise


class ReplayCompleteMessage(Message):
    """Posted by :class:`ReplayDashboardSource` when playback exhausts.

    The :class:`DashboardApp` listens for this so it can stop driving
    the progress tick and surface a "replay complete" footer. Posted
    as a Textual :class:`~textual.message.Message` so it rides the
    normal widget-message bus — no extra subscribe hook needed.
    """

    pass


class ReplayDashboardSource(_SubscriberMixin):
    """Replay a Phase 142 recording as a live dashboard stream.

    ``load_recording`` returns ``(metadata_dict, samples_iterator)``
    where each sample is a dict like ``{"captured_at": ISO, "pid_hex":
    "0x0C", "value": 1725.0, "raw": 0x1AF8, "unit": "rpm"}``. Samples
    are already time-ordered across both the SQLite side and any JSONL
    spill.

    The task groups samples by timestamp (one batch per unique
    captured_at) and sleeps the inter-batch delta divided by
    ``speed`` before emitting. ``speed=1.0`` matches real time,
    ``speed=10.0`` plays 10x faster. On exhaustion, posts
    :class:`ReplayCompleteMessage` via the attached app (if any).

    Parameters
    ----------
    recording_id:
        Integer primary key of the recording to play.
    speed:
        Playback speed multiplier. Must be in ``(0, inf)``; the CLI
        layer enforces ``(0.1, 100.0]`` before construction.
    manager_factory:
        Optional test-injection for the :class:`RecordingManager`
        constructor. Defaults to the production class.
    protocol_name:
        Override the ``protocol_name`` surfaced to the status bar.
        Defaults to the recording's stored ``protocol_name`` metadata.
    app_ref:
        Optional :class:`DashboardApp` the replay task posts
        :class:`ReplayCompleteMessage` to on exhaustion. Set by the
        app itself inside ``on_mount`` — callers don't pass this.
    """

    is_finite: bool = True

    def __init__(
        self,
        recording_id: int,
        speed: float = 1.0,
        manager_factory: Optional[Callable[[], Any]] = None,
        protocol_name: Optional[str] = None,
    ) -> None:
        super().__init__()
        if speed <= 0:
            raise ValueError(f"speed must be > 0 (got {speed!r})")
        self._recording_id: int = int(recording_id)
        self._speed: float = float(speed)
        self._manager_factory = manager_factory
        self._task: Optional[asyncio.Task] = None
        self._stop_flag: bool = False
        self._samples_played: int = 0
        self._total_samples: int = 0
        self._app_ref: Optional[Any] = None
        self._stored_protocol_name: Optional[str] = protocol_name
        self._stored_vin: Optional[str] = None
        self._stored_dtcs: List[str] = []
        # Metadata is loaded in ``start`` so a construction error here
        # doesn't block unit tests that only inspect ``is_finite`` etc.
        self._loaded: bool = False

    @property
    def protocol_name(self) -> str:
        return self._stored_protocol_name or "replay"

    @property
    def vin(self) -> Optional[str]:
        return self._stored_vin

    @property
    def progress(self) -> Optional[float]:
        """Fraction in ``[0.0, 1.0]`` of replay played so far."""
        if self._total_samples <= 0:
            return 0.0
        return min(1.0, self._samples_played / self._total_samples)

    def _build_manager(self) -> Any:
        if self._manager_factory is not None:
            return self._manager_factory()
        from motodiag.hardware.recorder import RecordingManager

        return RecordingManager()

    def _set_app(self, app: Any) -> None:
        """Called by :class:`DashboardApp` so we can post completion."""
        self._app_ref = app

    async def start(self) -> None:
        """Load metadata and spawn the playback task."""
        self._stop_flag = False
        manager = self._build_manager()
        # Load metadata + samples. ``load_recording`` returns
        # (metadata_dict, samples_iterator). Any KeyError bubbles.
        metadata, samples_iter = manager.load_recording(
            int(self._recording_id)
        )
        if self._stored_protocol_name is None:
            self._stored_protocol_name = metadata.get("protocol_name")
        # VIN isn't in the recording schema today; surface None.
        self._stored_vin = metadata.get("vin")
        # Stored DTCs: recording metadata may carry ``dtcs_csv`` or
        # ``notes`` — we best-effort it and degrade to [] silently.
        dtcs_csv = metadata.get("dtcs_csv") or ""
        self._stored_dtcs = [
            tok.strip() for tok in dtcs_csv.split(",") if tok.strip()
        ]
        # Buffer the samples list so we know total length for progress.
        samples_list = list(samples_iter)
        self._total_samples = len(samples_list)
        self._loaded = True
        self._task = asyncio.create_task(self._run(samples_list))

    async def _run(self, samples: List[dict]) -> None:
        """Walk ``samples`` in wall-clock time, emit per-timestamp batches."""
        # Group samples by (captured_at) so each "tick" matches one
        # live poll cycle. Because samples are pre-sorted, a groupby-
        # like walk is O(n) and doesn't need itertools.
        prev_ts: Optional[datetime] = None
        current_batch: List[Any] = []

        for row in samples:
            if self._stop_flag:
                return
            ts = self._parse_ts(row.get("captured_at"))
            if prev_ts is None:
                prev_ts = ts
            if ts != prev_ts:
                # Emit the batch we've been accumulating, then sleep
                # the delta to the next batch.
                if current_batch:
                    self._emit(current_batch)
                    self._samples_played += len(current_batch)
                current_batch = []
                if prev_ts is not None and ts is not None:
                    delta = (ts - prev_ts).total_seconds()
                    if delta < 0:
                        delta = 0.0
                    sleep_for = delta / self._speed
                    try:
                        await asyncio.sleep(sleep_for)
                    except asyncio.CancelledError:
                        raise
                prev_ts = ts
            current_batch.append(self._row_to_reading(row))

        # Flush any tail batch.
        if current_batch and not self._stop_flag:
            self._emit(current_batch)
            self._samples_played += len(current_batch)

        # Mark exhausted — post completion message.
        if not self._stop_flag and self._app_ref is not None:
            try:
                self._app_ref.post_message(ReplayCompleteMessage())
            except Exception:  # noqa: BLE001
                logger.exception("ReplayDashboardSource: post_message failed")

    @staticmethod
    def _parse_ts(value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _row_to_reading(row: dict) -> Any:
        """Best-effort dict→SensorReading-ish object.

        The dashboard widgets duck-type-consume ``pid_hex``, ``value``,
        ``unit``, ``name`` — we hand them a lightweight class instance
        that exposes those attributes, built straight from the row.
        Avoids pulling the full Phase 141 Pydantic validator into the
        replay path where we already trust the recorded data.
        """

        class _ReplayReading:
            __slots__ = (
                "pid",
                "pid_hex",
                "name",
                "value",
                "unit",
                "raw",
                "captured_at",
                "status",
            )

            def __init__(self, r: dict) -> None:
                pid_hex = str(r.get("pid_hex") or "0x00")
                try:
                    pid_int = int(pid_hex, 16) if pid_hex.lower().startswith(
                        "0x"
                    ) else int(pid_hex)
                except ValueError:
                    pid_int = 0
                self.pid = pid_int
                # Normalize to uppercase-tail form.
                if pid_hex.lower().startswith("0x"):
                    self.pid_hex = "0x" + pid_hex[2:].upper()
                else:
                    self.pid_hex = f"0x{pid_int:02X}"
                self.name = self._lookup_name(pid_int, r)
                self.value = r.get("value")
                self.unit = r.get("unit") or ""
                self.raw = r.get("raw")
                captured = r.get("captured_at")
                if isinstance(captured, datetime):
                    self.captured_at = captured
                else:
                    try:
                        self.captured_at = datetime.fromisoformat(
                            str(captured)
                        )
                    except (TypeError, ValueError):
                        self.captured_at = datetime.now(timezone.utc)
                self.status = "ok" if self.value is not None else "unsupported"

            @staticmethod
            def _lookup_name(pid_int: int, r: dict) -> str:
                # Prefer an explicit name in the row if present; else
                # fall back to the catalog; else synthetic hex name.
                explicit = r.get("name")
                if explicit:
                    return str(explicit)
                try:
                    from motodiag.hardware.sensors import SENSOR_CATALOG

                    spec = SENSOR_CATALOG.get(pid_int)
                    if spec is not None:
                        return spec.name
                except Exception:  # noqa: BLE001
                    pass
                return f"PID 0x{pid_int:02X}"

        return _ReplayReading(row)

    async def stop(self) -> None:
        self._stop_flag = True
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._task = None

    def read_dtcs(self) -> List[str]:
        """Return the recording's captured DTC snapshot (if any)."""
        return list(self._stored_dtcs)


# ---------------------------------------------------------------------------
# Widgets — guarded by TEXTUAL_AVAILABLE
# ---------------------------------------------------------------------------


class GaugeWidget(Static):
    """Large-format labeled gauge with a clamped horizontal bar.

    Color bands follow a fraction-of-range scheme: by default 0-60% of
    the ``(min, max)`` span renders green, 60-85% yellow, 85-100% red.
    ``value = None`` prints a dim ``--`` so newly-mounted gauges don't
    show a confusing "0.00" until the first sample lands.

    Parameters
    ----------
    label:
        Short name (``"RPM"``, ``"Coolant"``).
    min_value, max_value:
        Gauge span used both for the clamped numeric display and the
        bar fill.
    unit:
        Unit string appended to the numeric display.
    color_thresholds:
        Sorted list of ``(fraction, style)`` pairs. The highest
        fraction below the current normalized value wins. Must end
        at ``1.0`` — the constructor raises if not.
    """

    # ``reactive`` at class scope so assigning the attribute on an
    # instance triggers a redraw automatically.
    value: Any = reactive(None)

    DEFAULT_COLORS: tuple[tuple[float, str], ...] = (
        (0.6, "green"),
        (0.85, "yellow"),
        (1.0, "red"),
    )

    def __init__(
        self,
        label: str,
        min_value: float,
        max_value: float,
        unit: str,
        color_thresholds: Optional[List[tuple[float, str]]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        if min_value >= max_value:
            raise ValueError(
                f"GaugeWidget: min_value ({min_value}) must be < max_value "
                f"({max_value})"
            )
        self._label: str = label
        self._min: float = float(min_value)
        self._max: float = float(max_value)
        self._unit: str = unit
        colors = (
            list(color_thresholds)
            if color_thresholds is not None
            else list(self.DEFAULT_COLORS)
        )
        # Invariants: ascending fractions, last must be >= 1.0.
        if not colors:
            raise ValueError("GaugeWidget: color_thresholds must be non-empty")
        if colors[-1][0] < 1.0:
            raise ValueError(
                "GaugeWidget: final color threshold must be >= 1.0"
            )
        self._colors: list[tuple[float, str]] = colors

    def _pick_color(self, fraction: float) -> str:
        for edge, style in self._colors:
            if fraction <= edge:
                return style
        return self._colors[-1][1]

    def render(self) -> str:
        value = self.value
        if value is None:
            return (
                f"[bold]{self._label}[/bold]\n"
                f"[dim]--[/dim] {self._unit}"
            )
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return (
                f"[bold]{self._label}[/bold]\n"
                f"[dim]--[/dim] {self._unit}"
            )
        clamped = max(self._min, min(self._max, numeric))
        span = self._max - self._min
        fraction = 0.0 if span <= 0 else (clamped - self._min) / span
        style = self._pick_color(fraction)
        # Bar: 20 cells of ``█`` / ``░`` split by the fraction.
        bar_width = 20
        filled = int(round(fraction * bar_width))
        bar = "\u2588" * filled + "\u2591" * (bar_width - filled)
        return (
            f"[bold]{self._label}[/bold]\n"
            f"[{style}]{bar}[/{style}]\n"
            f"[{style}]{clamped:>7.2f}[/{style}] {self._unit}"
        )


class PidChart(Static):
    """Rolling Braille sparkline of one PID's history.

    Renders the last :attr:`history_len` samples as a single-line
    string of Unicode 1/8 block characters normalized to the observed
    min/max of the deque. ``None`` entries render as a thin space so
    the time axis stays uniform even across dropped samples.

    Parameters
    ----------
    history_len:
        Number of samples kept in the rolling window. Default 120
        covers 24 seconds at 5 Hz, 60 seconds at 2 Hz — enough to spot
        a trend without burying the tail in old data.
    """

    def __init__(
        self,
        history_len: int = 120,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        if history_len <= 0:
            raise ValueError("PidChart: history_len must be > 0")
        self._history_len: int = int(history_len)
        self._deque: collections.deque[Optional[float]] = collections.deque(
            maxlen=self._history_len
        )
        self._pid_hex: Optional[str] = None
        self._label: str = ""
        self._unit: str = ""

    @property
    def history_len(self) -> int:
        return self._history_len

    def set_pid(
        self,
        pid_hex: str,
        label: str,
        unit: str,
    ) -> None:
        """Switch the tracked PID — clears history so colors don't lie."""
        self._pid_hex = pid_hex
        self._label = label
        self._unit = unit
        self._deque.clear()
        # Trigger redraw on Textual; harmless no-op on the stub base.
        try:
            self.refresh()
        except Exception:  # noqa: BLE001
            pass

    def push(self, value: Optional[float]) -> None:
        """Append one sample to the history (``None`` for a gap)."""
        if value is None:
            self._deque.append(None)
        else:
            try:
                self._deque.append(float(value))
            except (TypeError, ValueError):
                self._deque.append(None)
        try:
            self.refresh()
        except Exception:  # noqa: BLE001
            pass

    @property
    def current_pid(self) -> Optional[str]:
        return self._pid_hex

    def _format_sparkline(self) -> str:
        values = list(self._deque)
        if not values:
            return "[dim]…[/dim]"
        numeric = [v for v in values if v is not None]
        if not numeric:
            return "[dim]" + ("·" * len(values)) + "[/dim]"
        lo = min(numeric)
        hi = max(numeric)
        span = hi - lo
        cells: list[str] = []
        for v in values:
            if v is None:
                cells.append(" ")  # gap: single space preserves axis
                continue
            if span <= 0:
                cells.append(_SPARK_CHARS[len(_SPARK_CHARS) // 2])
                continue
            frac = (v - lo) / span
            idx = min(len(_SPARK_CHARS) - 1, max(0, int(frac * (len(_SPARK_CHARS) - 1))))
            cells.append(_SPARK_CHARS[idx])
        return "".join(cells)

    def render(self) -> str:
        if not self._pid_hex:
            return "[dim]no PID selected — press 1-6[/dim]"
        header = f"[bold]{self._label}[/bold]  [cyan]{self._pid_hex}[/cyan]"
        if self._unit:
            header += f" [dim]{self._unit}[/dim]"
        sparkline = self._format_sparkline()
        return f"{header}\n{sparkline}"


class DTCPanel(Static):
    """Periodically polls ``source.read_dtcs()`` and renders a Rich table.

    Two timers run inside the panel:

    - 5 s poll cadence. Refreshes :attr:`_codes` on every successful
      response from the source.
    - 15 s staleness threshold. If no poll has succeeded inside the
      threshold the header renders with a `` — stale`` suffix so the
      mechanic knows the list on screen may be lagging reality.

    Exceptions from :meth:`DashboardSource.read_dtcs` are caught and
    logged — we keep the last-good snapshot on screen so a transient
    adapter hiccup does not wipe the DTC list.
    """

    DEFAULT_POLL_INTERVAL: float = 5.0
    DEFAULT_STALE_AFTER: float = 15.0

    def __init__(
        self,
        source: DashboardSource,
        make_hint: Optional[str] = None,
        poll_interval_s: float = DEFAULT_POLL_INTERVAL,
        stale_after_s: float = DEFAULT_STALE_AFTER,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._source = source
        self._make_hint = make_hint
        self._poll_interval_s: float = float(poll_interval_s)
        self._stale_after_s: float = float(stale_after_s)
        self._codes: list[str] = []
        self._last_ok: Optional[datetime] = None
        self._interval_handle: Any = None
        # Track poll count for tests that want to assert scheduling.
        self._poll_count: int = 0

    def on_mount(self) -> None:
        # Immediate first poll so the panel isn't blank on first paint.
        self._refresh()
        try:
            self._interval_handle = self.set_interval(
                self._poll_interval_s, self._refresh
            )
        except Exception:  # noqa: BLE001
            # ``set_interval`` is a Textual instance method — on the
            # stub base class it's absent, which is fine for tests
            # that exercise ``render`` directly.
            pass

    def _refresh(self) -> None:
        """One poll cycle. Swallows adapter exceptions."""
        self._poll_count += 1
        try:
            codes = list(self._source.read_dtcs())
        except Exception:  # noqa: BLE001
            logger.exception("DTCPanel: read_dtcs failed; keeping last snapshot")
            # Do not touch self._codes or self._last_ok — we want
            # staleness to engage naturally.
            try:
                self.refresh()
            except Exception:  # noqa: BLE001
                pass
            return
        self._codes = codes
        self._last_ok = datetime.now(timezone.utc)
        try:
            self.refresh()
        except Exception:  # noqa: BLE001
            pass

    def _is_stale(self) -> bool:
        if self._last_ok is None:
            return True
        age = (datetime.now(timezone.utc) - self._last_ok).total_seconds()
        return age > self._stale_after_s

    def render(self) -> str:
        header_text = f"DTCs ({len(self._codes)})"
        if self._is_stale():
            header = f"[dim]{header_text} — stale[/dim]"
        else:
            header = f"[bold]{header_text}[/bold]"
        if not self._codes:
            return f"{header}\n[dim]no codes[/dim]"
        try:
            from motodiag.knowledge.dtc_lookup import resolve_dtc_info

            lines = [header]
            for code in self._codes:
                try:
                    info = resolve_dtc_info(code, make_hint=self._make_hint)
                    desc = info.get("description") or "-"
                    severity = info.get("severity") or "-"
                    lines.append(
                        f"  [bold]{info.get('code', code)}[/bold] "
                        f"[dim]({severity})[/dim] {desc}"
                    )
                except Exception:  # noqa: BLE001
                    lines.append(f"  [bold]{code}[/bold]")
            return "\n".join(lines)
        except ImportError:  # pragma: no cover — knowledge module is core
            return f"{header}\n" + "\n".join(
                f"  [bold]{c}[/bold]" for c in self._codes
            )


# ---------------------------------------------------------------------------
# StatusBar widget — shows protocol / VIN / record state / progress
# ---------------------------------------------------------------------------


class StatusBar(Static):
    """Thin bottom strip: protocol  VIN  replay-progress  record-state."""

    recording: bool = reactive(False)
    progress_value: Any = reactive(None)

    def __init__(
        self,
        source: DashboardSource,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._source = source

    def render(self) -> str:
        parts: list[str] = []
        parts.append(f"Protocol: [cyan]{self._source.protocol_name}[/cyan]")
        vin = self._source.vin
        if vin:
            parts.append(f"VIN: [cyan]{vin}[/cyan]")
        if self._source.is_finite:
            prog = self.progress_value
            if prog is not None:
                try:
                    pct = float(prog) * 100.0
                    parts.append(f"Replay: [magenta]{pct:5.1f}%[/magenta]")
                except (TypeError, ValueError):
                    pass
        if self.recording:
            parts.append("[bold red][REC][/bold red]")
        return "   ".join(parts)


# ---------------------------------------------------------------------------
# DashboardApp
# ---------------------------------------------------------------------------


class DashboardApp(App):
    """The full-screen Textual :class:`~textual.app.App`.

    Parameters
    ----------
    source:
        Any :class:`DashboardSource` implementation. The app only ever
        touches the protocol surface.
    pids:
        PID list to wire gauges / chart PID-selector against. Up to six
        are bound to number keys 1-6; extras past six are dropped from
        the chart selector but still emitted to subscribers (useful for
        longer lists that the gauges row happens to cover).
    recording_manager:
        Optional :class:`~motodiag.hardware.recorder.RecordingManager`.
        When ``None``, ``Ctrl+R`` becomes a silent no-op — used by
        replay mode.
    vehicle_id:
        Optional FK for :meth:`RecordingManager.start_recording`.
        Defaults to ``None`` (unassigned).
    make_hint:
        Propagated to :class:`DTCPanel` for enrichment.
    """

    CSS = """
    Screen {
        layout: vertical;
    }
    #top {
        height: 1fr;
        layout: horizontal;
    }
    #gauges {
        width: 1fr;
        layout: vertical;
    }
    #chart {
        width: 2fr;
    }
    #dtcs {
        width: 1fr;
    }
    #status {
        height: 1;
    }
    """

    # Bindings defined as plain tuples when Textual is absent so the
    # class body doesn't blow up. Textual also accepts the 3-tuple
    # shorthand ``(key, action, description)`` and converts internally.
    if TEXTUAL_AVAILABLE:
        BINDINGS = [
            Binding("ctrl+q", "quit", "Quit"),
            Binding("ctrl+r", "toggle_recording", "Toggle Recording"),
            Binding("d", "toggle_dtc", "Toggle DTCs"),
            Binding("1", "select_pid(0)", "PID 1"),
            Binding("2", "select_pid(1)", "PID 2"),
            Binding("3", "select_pid(2)", "PID 3"),
            Binding("4", "select_pid(3)", "PID 4"),
            Binding("5", "select_pid(4)", "PID 5"),
            Binding("6", "select_pid(5)", "PID 6"),
        ]
    else:  # pragma: no cover — covered by TestTextualMissing
        BINDINGS = []

    def __init__(
        self,
        source: DashboardSource,
        pids: List[int],
        recording_manager: Optional[Any] = None,
        vehicle_id: Optional[int] = None,
        make_hint: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._source = source
        self._pids: List[int] = list(pids)
        self._recording_manager = recording_manager
        self._vehicle_id = vehicle_id
        self._make_hint = make_hint
        self._active_recording_id: Optional[int] = None
        self._gauges: dict[str, GaugeWidget] = {}
        self._chart: Optional[PidChart] = None
        self._dtc_panel: Optional[DTCPanel] = None
        self._status_bar: Optional[StatusBar] = None
        # Attach replay source's message-post hook to us.
        if isinstance(source, ReplayDashboardSource):
            source._set_app(self)

    # ---------------------------------------------------------------------
    # Layout
    # ---------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="top"):
            with Vertical(id="gauges"):
                # Up to 4 big gauges depending on what's in the first
                # few PIDs of the list. We configure canonical gauges
                # when a known PID is present; unknown PIDs fall through
                # to a generic 0-100 gauge.
                for pid in self._pids[:4]:
                    gauge = self._build_gauge_for(pid)
                    self._gauges[self._pid_hex(pid)] = gauge
                    yield gauge
            self._chart = PidChart(id="chart")
            yield self._chart
            self._dtc_panel = DTCPanel(
                self._source, make_hint=self._make_hint, id="dtcs",
            )
            yield self._dtc_panel
        self._status_bar = StatusBar(self._source, id="status")
        yield self._status_bar
        yield Footer()

    @staticmethod
    def _pid_hex(pid: int) -> str:
        return f"0x{int(pid):02X}"

    def _build_gauge_for(self, pid: int) -> GaugeWidget:
        """Construct a :class:`GaugeWidget` with sensible defaults per PID."""
        canonical: dict[int, tuple[str, float, float, str]] = {
            0x0C: ("RPM", 0.0, 8000.0, "rpm"),
            0x05: ("Coolant", -40.0, 215.0, "\u00b0C"),
            0x0F: ("IAT", -40.0, 215.0, "\u00b0C"),
            0x11: ("Throttle", 0.0, 100.0, "%"),
            0x42: ("Battery", 0.0, 20.0, "V"),
            0x04: ("Load", 0.0, 100.0, "%"),
            0x0D: ("Speed", 0.0, 300.0, "km/h"),
            0x0B: ("MAP", 0.0, 255.0, "kPa"),
            0x10: ("MAF", 0.0, 655.0, "g/s"),
            0x46: ("Ambient", -40.0, 215.0, "\u00b0C"),
            0x5C: ("Oil Temp", -40.0, 215.0, "\u00b0C"),
            0x2F: ("Fuel", 0.0, 100.0, "%"),
        }
        if pid in canonical:
            label, lo, hi, unit = canonical[pid]
        else:
            label, lo, hi, unit = (f"PID {self._pid_hex(pid)}", 0.0, 100.0, "")
        return GaugeWidget(label, lo, hi, unit)

    # ---------------------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------------------

    async def on_mount(self) -> None:
        # Initial chart PID = first in the list.
        if self._pids and self._chart is not None:
            self._select_pid_index(0)
        self._source.subscribe(self._handle_reading)
        await self._source.start()
        # Replay-mode: drive the progress tick in the status bar.
        if self._source.is_finite:
            try:
                self.set_interval(0.2, self._tick_progress)
            except Exception:  # noqa: BLE001
                pass

    async def on_unmount(self) -> None:
        # Stop recording first so we never leave a dangling session.
        if (
            self._active_recording_id is not None
            and self._recording_manager is not None
        ):
            try:
                self._recording_manager.stop_recording(
                    self._active_recording_id
                )
            except Exception:  # noqa: BLE001
                logger.exception("DashboardApp: stop_recording on unmount failed")
            self._active_recording_id = None
        try:
            await self._source.stop()
        except Exception:  # noqa: BLE001
            logger.exception("DashboardApp: source.stop on unmount failed")

    def _tick_progress(self) -> None:
        if self._status_bar is not None:
            self._status_bar.progress_value = self._source.progress

    # ---------------------------------------------------------------------
    # Reading dispatch
    # ---------------------------------------------------------------------

    def _handle_reading(self, batch: List[Any]) -> None:
        """Fan one source batch to gauges + chart."""
        for reading in batch:
            self._update_gauge(reading)
            self._update_chart(reading)
        # Append to active recording, if any. Best-effort — failures
        # get logged but don't abort the dashboard.
        if (
            self._active_recording_id is not None
            and self._recording_manager is not None
        ):
            try:
                self._recording_manager.append_samples(
                    self._active_recording_id, batch
                )
            except Exception:  # noqa: BLE001
                logger.exception(
                    "DashboardApp: append_samples failed; recording may be incomplete"
                )

    def _update_gauge(self, reading: Any) -> None:
        pid_hex = getattr(reading, "pid_hex", None)
        if not pid_hex:
            return
        gauge = self._gauges.get(pid_hex)
        if gauge is None:
            return
        gauge.value = getattr(reading, "value", None)

    def _update_chart(self, reading: Any) -> None:
        if self._chart is None:
            return
        if getattr(reading, "pid_hex", None) != self._chart.current_pid:
            return
        self._chart.push(getattr(reading, "value", None))

    # ---------------------------------------------------------------------
    # Actions
    # ---------------------------------------------------------------------

    def action_toggle_dtc(self) -> None:
        if self._dtc_panel is None:
            return
        try:
            current = self._dtc_panel.styles.display
            self._dtc_panel.styles.display = (
                "none" if str(current) != "none" else "block"
            )
        except Exception:  # noqa: BLE001
            # On stub base (no Textual) this is a no-op — tests that
            # exercise action_toggle_dtc directly just verify call-
            # through behavior.
            pass

    async def action_toggle_recording(self) -> None:
        if self._recording_manager is None:
            return
        if self._active_recording_id is not None:
            rec_id = self._active_recording_id
            self._active_recording_id = None
            if self._status_bar is not None:
                self._status_bar.recording = False
            try:
                self._recording_manager.stop_recording(rec_id)
            except Exception:  # noqa: BLE001
                logger.exception("DashboardApp: stop_recording failed")
            return
        # Start a new recording.
        iso_ts = datetime.now(timezone.utc).isoformat()
        pids_as_hex = [self._pid_hex(p) for p in self._pids]
        try:
            rec_id = self._recording_manager.start_recording(
                vehicle_id=self._vehicle_id,
                label=f"dashboard-{iso_ts}",
                pids=pids_as_hex,
                protocol_name=self._source.protocol_name,
            )
            self._active_recording_id = int(rec_id)
            if self._status_bar is not None:
                self._status_bar.recording = True
        except Exception:  # noqa: BLE001
            logger.exception("DashboardApp: start_recording failed")

    def action_select_pid(self, idx: int) -> None:
        self._select_pid_index(int(idx))

    def _select_pid_index(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._pids) or self._chart is None:
            return
        pid = self._pids[idx]
        hex_form = self._pid_hex(pid)
        label, unit = self._label_unit_for(pid)
        self._chart.set_pid(hex_form, label, unit)

    @staticmethod
    def _label_unit_for(pid: int) -> tuple[str, str]:
        try:
            from motodiag.hardware.sensors import SENSOR_CATALOG

            spec = SENSOR_CATALOG.get(int(pid))
            if spec is not None:
                return spec.name, spec.unit
        except Exception:  # noqa: BLE001
            pass
        return (f"PID 0x{int(pid):02X}", "")

    # ---------------------------------------------------------------------
    # Message handling
    # ---------------------------------------------------------------------

    def on_replay_complete_message(
        self, message: ReplayCompleteMessage
    ) -> None:
        """React to ReplayDashboardSource running out of samples."""
        # Update the footer tag; stop pushing gauges.
        if self._status_bar is not None:
            self._status_bar.progress_value = 1.0


# ---------------------------------------------------------------------------
# CLI helper — surface a helpful message when Textual is absent
# ---------------------------------------------------------------------------


def _require_textual() -> None:
    """Raise :class:`click.ClickException` if Textual is not importable.

    Used by the CLI subcommand as the first line of the handler so the
    user gets the install hint *before* any other validation work.
    """
    if not TEXTUAL_AVAILABLE:
        import click

        raise click.ClickException(
            "Textual is required for the dashboard. "
            "Install with: pip install 'motodiag[dashboard]'"
        )


__all__ = [
    "TEXTUAL_AVAILABLE",
    "DashboardSource",
    "LiveDashboardSource",
    "ReplayDashboardSource",
    "ReplayCompleteMessage",
    "GaugeWidget",
    "PidChart",
    "DTCPanel",
    "StatusBar",
    "DashboardApp",
    "_require_textual",
]
