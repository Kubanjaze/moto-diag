"""Hardware CLI — ``motodiag hardware`` scan / clear / info (Phase 140).

First user-facing Track E phase. Wires Phase 139's
:class:`~motodiag.hardware.ecu_detect.AutoDetector` and Phases 134-138's
protocol adapters into a Click command group so a mechanic can plug an
OBD dongle into a serial port and actually read / clear DTCs.

Three subcommands under the ``hardware`` group:

- ``motodiag hardware scan --port COM3 [--bike SLUG | --make MAKE]
  [--baud N] [--timeout 2.0] [--mock]`` — auto-detect the ECU, read
  stored DTCs, render a Rich table with code / description / category /
  severity / source enrichment.
- ``motodiag hardware clear --port COM3 [--bike ...] [--yes] [--mock]``
  — show a safety warning, confirm (unless ``--yes``), issue Mode 04.
- ``motodiag hardware info --port COM3 [--bike ...] [--mock]`` — auto-
  detect and print an ECU identity panel.

All three surface :class:`NoECUDetectedError` from Phase 139 as a
mechanic-friendly red panel that unpacks the per-adapter error list
(``errors=[(AdapterName, exception), …]``) into separate rows.
Exit code 1 on any failure, 0 on success.

**Paywall posture**: Phase 140 has no tier gates — the hardware CLI is
a core utility every subscription tier should have. Tier-driven
enforcement (e.g. monthly clear-ops cap) lands in Track H alongside
billing.
"""

from __future__ import annotations

import csv
import time as _time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

import click
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from motodiag.cli.diagnose import _resolve_bike_slug
from motodiag.cli.theme import (
    ICON_FAIL,
    ICON_OK,
    ICON_WARN,
    format_severity,
    get_console,
)
from motodiag.core.database import init_db
from motodiag.hardware.connection import (
    HardwareSession,
    RetryPolicy,
)
from motodiag.hardware.ecu_detect import AutoDetector, NoECUDetectedError
from motodiag.hardware.protocols.exceptions import ProtocolError
from motodiag.hardware.protocols.exceptions import (
    UnsupportedCommandError,
)
from motodiag.hardware.scenarios import BUILTIN_NAMES
from motodiag.hardware.sensors import (
    SENSOR_CATALOG,
    SensorReading,
    SensorStreamer,
    parse_pid_list,
)
from motodiag.hardware.simulator import (
    RecordingSupportUnavailable,
    Scenario,
    ScenarioLoader,
    ScenarioParseError,
    ScenarioValidationError,
    SimulatedAdapter,
    SimulationClock,
)
from motodiag.knowledge.dtc_lookup import resolve_dtc_info


# --- Phase 141 stream defaults ----------------------------------------
#
# Default PID set when the mechanic does not pass ``--pids``. Six rows
# covering the "first-look" live view: RPM, coolant, IAT, throttle,
# battery, O2 voltage sensor 1. Vehicle speed (0x0D) is intentionally
# omitted — a bike on a dyno has a stationary frame but a turning
# wheel, so VSS can be misleading on the first glance. Mechanics who
# want VSS pass it explicitly.
_DEFAULT_STREAM_PIDS: tuple[int, ...] = (0x0C, 0x05, 0x0F, 0x11, 0x42, 0x14)

# ELM327 adapters spend 50-100 ms per AT command in round-trip
# overhead, so anything above ~10 Hz is wasted effort (the adapter
# itself becomes the bottleneck and the reported rate drifts). We clamp
# with a visible warning rather than silently downshifting.
_MAX_STREAM_HZ: float = 10.0


# --- Source label → Rich markup ---------------------------------------
#
# Colors the Source column in the scan table so the mechanic can tell
# at a glance whether a code came from a make-specific DB row (best
# provenance), a generic fallback (decent), or the pattern classifier
# (weakest — description is "Classified by pattern only"). Matches the
# theme palette established in Phase 129.
_SOURCE_STYLES: dict[str, str] = {
    "db_make": "green",
    "db_generic": "cyan",
    "classifier": "yellow",
}


def _format_source(source: str) -> str:
    """Return a Rich markup string for a DTC enrichment source label."""
    style = _SOURCE_STYLES.get(source, "dim")
    return f"[{style}]{source}[/{style}]"


# --- Make-hint resolution ---------------------------------------------


def _resolve_make_hint(
    bike: Optional[str], make: Optional[str],
) -> Tuple[Optional[str], Optional[dict]]:
    """Resolve --bike / --make into a normalized make hint + matched row.

    Returns
    -------
    tuple
        ``(make_hint, matched_vehicle_dict_or_None)``. When ``--bike`` is
        given, matches the slug against the garage via
        :func:`_resolve_bike_slug` and returns the vehicle row so the
        caller can surface "bike not found" hints. When ``--make`` is
        given directly, just normalizes and returns it with ``None``
        for the vehicle.
    """
    if bike:
        vehicle = _resolve_bike_slug(bike)
        if vehicle is None:
            return None, None
        raw_make = (vehicle.get("make") or "").strip().lower()
        return raw_make or None, vehicle
    if make:
        return make.strip().lower() or None, None
    return None, None


# --- Shared error rendering -------------------------------------------


def _render_no_ecu_panel(
    console, port: str, make_hint: Optional[str],
    errors: list[tuple[str, BaseException]],
) -> None:
    """Render the red "no ECU detected" panel with per-adapter failures.

    Unpacks Phase 139's :attr:`NoECUDetectedError.errors` list (pairs of
    ``(AdapterName, exception)``) into one line per attempted adapter
    so the mechanic sees the real failure mode, not just a single
    summary string. Also surfaces the ``--mock`` hint because the first
    real-world failure for new users is running without a dongle.
    """
    hint_line = f"make_hint=[cyan]{make_hint}[/cyan]" if make_hint else \
        "make_hint=[dim]none[/dim]"
    lines: list[str] = [
        f"[bold red]{ICON_FAIL} No ECU detected on {port}[/bold red]",
        hint_line,
    ]
    if errors:
        lines.append("")
        lines.append("[bold]Adapters attempted:[/bold]")
        for name, exc in errors:
            short_err = str(exc).strip() or type(exc).__name__
            if len(short_err) > 140:
                short_err = short_err[:137] + "..."
            lines.append(f"  • [cyan]{name}[/cyan]: {short_err}")
    else:
        lines.append("")
        lines.append("[dim]No adapters were attempted.[/dim]")
    lines.append("")
    lines.append(
        "[dim]hint: pass [bold]--mock[/bold] to test without hardware.[/dim]"
    )
    console.print(
        Panel(
            "\n".join(lines),
            title="Hardware scan failed",
            border_style="red",
        )
    )


def _bike_not_found(console, bike: str) -> None:
    """Render the red "bike slug not found" panel.

    Matches the Phase 125 "no garage entries yet" pattern so the user
    sees a consistent remediation path across commands.
    """
    console.print(
        Panel(
            f"[red]No bike matches slug {bike!r}.[/red]\n\n"
            "[dim]Add one first with [bold]motodiag garage add[/bold]\n"
            "or run [bold]motodiag garage list[/bold] to see existing "
            "slugs.[/dim]",
            title="Bike not found",
            border_style="red",
        )
    )


# --- Command: scan -----------------------------------------------------


def _run_scan(
    port: str,
    make_hint: Optional[str],
    baud: Optional[int],
    timeout_s: float,
    mock: bool,
    retry_policy: Optional[RetryPolicy] = None,
) -> int:
    """Execute the scan flow. Returns the shell exit code.

    The optional ``retry_policy`` (Phase 146) wraps the negotiated
    adapter in a :class:`ResilientAdapter` so transient
    connect/read failures retry with exponential backoff. When
    ``None`` the Phase 140 code path runs unchanged.
    """
    console = get_console()
    try:
        with HardwareSession(
            port=port,
            make_hint=make_hint,
            baud=baud,
            timeout_s=timeout_s,
            mock=mock,
            retry_policy=retry_policy,
        ) as adapter:
            dtcs = adapter.read_dtcs()
            protocol_name = adapter.get_protocol_name()
            # Best-effort VIN peek for the scan footer — failures here
            # shouldn't abort the scan; the dedicated `info` command is
            # the authoritative source.
            try:
                vin = adapter.read_vin()
            except Exception:  # noqa: BLE001
                vin = None
    except NoECUDetectedError as exc:
        _render_no_ecu_panel(
            console, exc.port, exc.make_hint, exc.errors,
        )
        return 1
    except Exception as exc:  # noqa: BLE001
        # Anything else — bad port string, unexpected protocol bug, etc.
        console.print(
            Panel(
                f"[red]{ICON_FAIL} Hardware scan failed: {exc}[/red]\n\n"
                f"[dim]hint: pass [bold]--mock[/bold] to test without "
                f"hardware.[/dim]",
                title="Hardware scan failed",
                border_style="red",
            )
        )
        return 1

    # Header with the [MOCK] badge when appropriate.
    badge = "[bold yellow][MOCK][/bold yellow] " if mock else ""
    console.print(
        f"\n{badge}[bold cyan]{ICON_OK} Connected[/bold cyan] on "
        f"[bold]{port}[/bold] via [bold]{protocol_name}[/bold]"
    )

    if not dtcs:
        console.print(
            Panel(
                f"[green]{ICON_OK} No codes stored.[/green]\n\n"
                "[dim]The ECU reports a clean fault memory.[/dim]",
                title="DTC scan",
                border_style="green",
            )
        )
    else:
        table = Table(
            title=f"DTCs stored ({len(dtcs)})",
            header_style="bold cyan",
        )
        table.add_column("Code", style="bold")
        table.add_column("Description", overflow="fold")
        table.add_column("Category")
        table.add_column("Severity")
        table.add_column("Source")
        for raw_code in dtcs:
            info = resolve_dtc_info(raw_code, make_hint=make_hint)
            table.add_row(
                info["code"],
                info.get("description") or "-",
                info.get("category") or "-",
                format_severity(info.get("severity")),
                _format_source(info["source"]),
            )
        console.print(table)

    # Summary footer — VIN is a nice-to-have; absent mock on real ECUs
    # that don't expose it, we just skip the line rather than showing
    # a bare "VIN: None".
    footer_parts: list[str] = [f"Protocol: [bold]{protocol_name}[/bold]"]
    if vin:
        footer_parts.append(f"VIN: [bold]{vin}[/bold]")
    console.print("\n" + "   ".join(footer_parts))
    if dtcs:
        console.print(
            "[dim]hint: run [bold]motodiag hardware clear --port "
            f"{port}[/bold] after confirming the fix.[/dim]"
        )
    return 0


# --- Command: clear ----------------------------------------------------


def _run_clear(
    port: str,
    make_hint: Optional[str],
    baud: Optional[int],
    timeout_s: float,
    mock: bool,
    assume_yes: bool,
    retry_policy: Optional[RetryPolicy] = None,
) -> int:
    """Execute the clear flow. Returns the shell exit code.

    The optional ``retry_policy`` (Phase 146) is explicitly default-off
    for ``clear`` commands — duplicating a Mode 04 on a Harley is a
    mechanic-surprise hazard. A mechanic who wants to retry transient
    connect failures can pass ``--retry`` on the CLI; even then the
    :class:`ResilientAdapter` wrapper does NOT retry ``clear_dtcs``
    itself (destructive-op protection).
    """
    console = get_console()

    console.print(
        Panel(
            f"[bold yellow]{ICON_WARN} This will clear ALL stored DTCs "
            "from the ECU.[/bold yellow]\n\n"
            "Do NOT clear before diagnosis is complete. Mechanics should "
            "only clear AFTER identifying and fixing the root cause — "
            "otherwise valuable diagnostic context is lost and the fault "
            "may immediately return without the code trail that led you "
            "to it.",
            title="Clear DTCs — safety warning",
            border_style="yellow",
        )
    )

    if not assume_yes:
        if not click.confirm("Proceed?", default=False):
            console.print("[yellow]Aborted — no codes cleared.[/yellow]")
            return 0

    try:
        with HardwareSession(
            port=port,
            make_hint=make_hint,
            baud=baud,
            timeout_s=timeout_s,
            mock=mock,
            retry_policy=retry_policy,
        ) as adapter:
            cleared = adapter.clear_dtcs()
    except NoECUDetectedError as exc:
        _render_no_ecu_panel(
            console, exc.port, exc.make_hint, exc.errors,
        )
        return 1
    except Exception as exc:  # noqa: BLE001
        console.print(
            Panel(
                f"[red]{ICON_FAIL} Clear failed: {exc}[/red]",
                title="Hardware clear failed",
                border_style="red",
            )
        )
        return 1

    badge = "[bold yellow][MOCK][/bold yellow] " if mock else ""
    if cleared:
        console.print(
            Panel(
                f"{badge}[green]{ICON_OK} ECU accepted the clear. "
                "Stored DTCs wiped.[/green]",
                title="Clear DTCs",
                border_style="green",
            )
        )
        return 0
    # ECU refused — typical cause is ignition on / engine running.
    console.print(
        Panel(
            f"{badge}[red]{ICON_FAIL} ECU refused the clear.[/red]\n\n"
            "[dim]Typical cause: ignition on / engine running. Turn "
            "ignition on with engine OFF, then retry. If the refusal "
            "persists, the ECU may have a hardware-protected code "
            "class that requires a dealer tool.[/dim]",
            title="Clear DTCs",
            border_style="red",
        )
    )
    return 1


# --- Command: info -----------------------------------------------------


def _run_info(
    port: str,
    make_hint: Optional[str],
    baud: Optional[int],
    timeout_s: float,
    mock: bool,
    console=None,
    retry_policy: Optional[RetryPolicy] = None,
) -> int:
    """Execute the info flow. Returns the shell exit code.

    Calls :meth:`HardwareSession.identify_ecu` while the session is
    open (so the adapter is still connected), then lets the ``with``
    block tear down the connection cleanly on exit.

    The optional ``retry_policy`` (Phase 146) wraps the negotiated
    adapter in a :class:`ResilientAdapter` so transient
    connect/read failures retry with exponential backoff. When
    ``None`` the Phase 140 code path runs unchanged.
    """
    if console is None:
        console = get_console()
    try:
        session = HardwareSession(
            port=port,
            make_hint=make_hint,
            baud=baud,
            timeout_s=timeout_s,
            mock=mock,
            retry_policy=retry_policy,
        )
        with session:
            info = session.identify_ecu()
    except NoECUDetectedError as exc:
        _render_no_ecu_panel(
            console, exc.port, exc.make_hint, exc.errors,
        )
        return 1
    except Exception as exc:  # noqa: BLE001
        console.print(
            Panel(
                f"[red]{ICON_FAIL} Info lookup failed: {exc}[/red]",
                title="Hardware info failed",
                border_style="red",
            )
        )
        return 1

    # Render the identity panel. Fields with ``None`` values render as
    # a friendly placeholder so the table stays aligned.
    vin = info.get("vin") or "[dim]not available[/dim]"
    ecu_part = info.get("ecu_part") or "[dim]not available[/dim]"
    sw_version = info.get("sw_version") or "[dim]not available[/dim]"
    protocol_name = info.get("protocol_name") or "[dim]unknown[/dim]"

    # Supported-modes checklist across the standard OBD-II subset.
    supported = set(info.get("supported_modes") or [])
    mode_rows: list[str] = []
    for mode in (1, 3, 4, 9):
        marker = f"[green]{ICON_OK}[/green]" if mode in supported else \
            f"[dim]{ICON_FAIL}[/dim]"
        mode_rows.append(f"  {marker} Mode {mode:02d}")

    badge = "[bold yellow][MOCK][/bold yellow]\n" if mock else ""
    body = (
        f"{badge}"
        f"Protocol:      [bold]{protocol_name}[/bold]\n"
        f"VIN:           [bold]{vin}[/bold]\n"
        f"ECU Part #:    [bold]{ecu_part}[/bold]\n"
        f"SW Version:    [bold]{sw_version}[/bold]\n\n"
        "Supported OBD Modes:\n" + "\n".join(mode_rows)
    )
    console.print(
        Panel(
            body,
            title=f"ECU info — {port}",
            border_style="cyan",
        )
    )
    return 0


# --- Command: stream (Phase 141) --------------------------------------


class _StreamCsvWriter:
    """Append-mode CSV sink for :func:`_run_stream`.

    Opens ``path`` in append mode (UTF-8, ``newline=""``) so a mechanic
    can keep one long log across multiple ``motodiag hardware stream
    --output log.csv`` sessions. On a brand-new file the writer emits a
    single header row; on an existing file it skips the header so the
    combined log stays parseable as one CSV document.

    Column layout:

    - ``timestamp_utc_iso`` — ISO-8601 UTC timestamp of the first PID
      captured in the tick (from :attr:`SensorReading.captured_at`).
    - ``elapsed_s`` — seconds since the stream started, rounded to
      millisecond precision via ``f"{elapsed:.3f}"``.
    - One column per PID, labelled ``"{name} ({unit})"`` for catalog
      entries or ``"PID 0x{pid:02X}"`` for unknown PIDs.

    Cell values are ``f"{value:.6g}"`` for ``ok`` readings and an empty
    string for ``unsupported`` / ``timeout`` — keeps the file friendly
    to Excel, pandas, and plain ``cut``.
    """

    def __init__(self, path: Path, pids: List[int]) -> None:
        # Stash the PID order so write_row doesn't have to infer column
        # order from the readings (a caller could theoretically reorder
        # them between ticks — we treat our construction-time order as
        # the authoritative schema).
        self._pids: List[int] = list(pids)
        self._path: Path = path
        existed = path.exists() and path.stat().st_size > 0
        # Opening in append mode surfaces path errors (non-writable
        # directory, parent missing, etc.) before we've paid to spin
        # up the serial adapter — _run_stream constructs the writer
        # up-front for exactly this reason.
        self._fh = open(path, "a", encoding="utf-8", newline="")
        self._writer = csv.writer(self._fh)
        if not existed:
            header: List[str] = ["timestamp_utc_iso", "elapsed_s"]
            for pid in self._pids:
                spec = SENSOR_CATALOG.get(pid)
                if spec is None:
                    header.append(f"PID 0x{pid:02X}")
                else:
                    header.append(f"{spec.name} ({spec.unit})")
            self._writer.writerow(header)
            self._fh.flush()

    def write_row(
        self, readings: List[SensorReading], elapsed_s: float,
    ) -> None:
        """Append one tick's worth of readings to the CSV.

        The ``elapsed_s`` argument comes from the caller's monotonic
        clock so the CSV's elapsed column matches the on-screen footer
        exactly — using the per-reading ``captured_at`` delta would
        drift by fractions of a millisecond per PID because the reads
        happen sequentially within a tick.
        """
        # Index readings by PID so we can look each one up in the
        # writer's own column order, not the order the streamer
        # happened to yield them in (defensive — today they match).
        by_pid = {r.pid: r for r in readings}
        # Timestamp comes from the first reading's captured_at — all
        # readings in one tick share effectively the same UTC second.
        ts_iso = (
            readings[0].captured_at.isoformat()
            if readings
            else datetime.now(timezone.utc).isoformat()
        )
        row: List[str] = [ts_iso, f"{elapsed_s:.3f}"]
        for pid in self._pids:
            reading = by_pid.get(pid)
            if reading is None or reading.status != "ok" or reading.value is None:
                row.append("")
            else:
                row.append(f"{reading.value:.6g}")
        self._writer.writerow(row)
        self._fh.flush()

    def close(self) -> None:
        """Flush and close the file handle. Idempotent."""
        if self._fh is not None and not self._fh.closed:
            self._fh.flush()
            self._fh.close()


def _render_stream_panel(
    readings: List[SensorReading],
    hz: float,
    elapsed_s: float,
    mock: bool,
) -> Panel:
    """Build the Rich Panel for one poll tick of the live stream.

    The panel wraps a :class:`~rich.table.Table` with four columns —
    PID / Name / Value / Unit — so the mechanic's eye lands on the
    value column without scanning. Status encoding:

    - ``ok`` → raw value formatted via ``f"{value:g}"`` (scientific
      form stays out of the way for normal ranges).
    - ``unsupported`` → dim em-dash ``[dim]—[/dim]`` so an
      unsupported PID is visually quiet.
    - ``timeout`` → yellow ``timeout`` to flag transient ECU
      unresponsiveness without alarming the mechanic.

    The panel title includes ``[MOCK]`` in yellow when the session is
    running against :class:`~motodiag.hardware.mock.MockAdapter` so
    screenshots and videos never mislead about the data provenance.
    """
    table = Table(header_style="bold cyan", expand=True)
    table.add_column("PID", style="bold", no_wrap=True)
    table.add_column("Name", overflow="fold")
    table.add_column("Value", justify="right")
    table.add_column("Unit")
    for r in readings:
        if r.status == "ok" and r.value is not None:
            value_cell = f"{r.value:g}"
        elif r.status == "timeout":
            value_cell = "[yellow]timeout[/yellow]"
        else:
            # unsupported — dim em-dash matches the Phase 129 theme
            # convention for "absent but expected" cells.
            value_cell = "[dim]—[/dim]"
        table.add_row(r.pid_hex, r.name, value_cell, r.unit or "")
    badge = "[bold yellow][MOCK][/bold yellow] " if mock else ""
    title = f"{badge}Live sensors ({hz:g} Hz)  •  elapsed {elapsed_s:.1f}s"
    return Panel(table, title=title, border_style="cyan")


def _run_stream(
    port: str,
    make_hint: Optional[str],
    baud: Optional[int],
    timeout_s: float,
    mock: bool,
    pids: List[int],
    hz: float,
    duration: float,
    output_path: Optional[Path],
) -> int:
    """Execute the live-sensor streaming flow. Returns the shell exit code.

    Five linear phases:

    1. **hz validation** — reject ``<= 0`` as a hard error; clamp
       ``> _MAX_STREAM_HZ`` (10 Hz) with a visible warning panel so
       the mechanic knows the ELM327 ceiling kicked in.
    2. **CSV writer setup** — if ``--output`` was supplied, open the
       sink *before* the serial port so a bad path fails fast (no
       point connecting to the ECU to then fail on a write).
    3. **HardwareSession** — same detection / error surface as
       :func:`_run_scan`. :class:`NoECUDetectedError` renders the red
       per-adapter failure panel and returns 1.
    4. **Streaming loop** — one :class:`Rich.Live` context wraps the
       :class:`SensorStreamer.iter_readings` generator. Each tick
       refreshes the panel, optionally writes a CSV row, and checks
       the duration cap. :class:`KeyboardInterrupt` breaks cleanly
       (exit 0); :class:`ProtocolError` renders a red "ECU went
       silent" panel and returns 1.
    5. **Footer** — cycles polled + total elapsed, printed after the
       Live block exits so it's not overwritten by the final refresh.

    The CSV writer (if any) is always closed in ``finally`` so a mid-
    stream abort never leaks a file handle.
    """
    console = get_console()

    # --- 1. hz validation -----------------------------------------------
    if hz <= 0:
        raise click.ClickException(
            f"--hz must be > 0 (got {hz!r}); try --hz 2.0"
        )
    clamped_hz = hz
    if hz > _MAX_STREAM_HZ:
        clamped_hz = _MAX_STREAM_HZ
        console.print(
            Panel(
                f"[yellow]{ICON_WARN} --hz {hz:g} exceeds the {_MAX_STREAM_HZ:g} Hz "
                "ceiling and was clamped.[/yellow]\n\n"
                "[dim]ELM327-class adapters spend 50-100 ms per AT "
                "command, so polling faster than 10 Hz just drops "
                "ticks at the driver. Native CAN can sustain more — "
                "contact support if you need a raised ceiling.[/dim]",
                title="Rate clamped",
                border_style="yellow",
            )
        )

    # --- 2. CSV writer (optional) ---------------------------------------
    csv_writer: Optional[_StreamCsvWriter] = None
    if output_path is not None:
        try:
            csv_writer = _StreamCsvWriter(output_path, pids)
        except OSError as exc:
            console.print(
                Panel(
                    f"[red]{ICON_FAIL} Could not open output file "
                    f"{output_path}: {exc}[/red]",
                    title="Stream output failed",
                    border_style="red",
                )
            )
            return 1

    # --- 3/4/5. Session + streaming loop --------------------------------
    cycles = 0
    stream_start = _time.monotonic()
    try:
        try:
            session = HardwareSession(
                port=port,
                make_hint=make_hint,
                baud=baud,
                timeout_s=timeout_s,
                mock=mock,
            )
            with session as adapter:
                protocol_name = adapter.get_protocol_name()
                badge = "[bold yellow][MOCK][/bold yellow] " if mock else ""
                console.print(
                    f"\n{badge}[bold cyan]{ICON_OK} Connected[/bold cyan] "
                    f"on [bold]{port}[/bold] via "
                    f"[bold]{protocol_name}[/bold]"
                )

                streamer = SensorStreamer(adapter, pids, hz=clamped_hz)
                # Initial empty panel so Live has something to render
                # before the first tick lands (keeps the terminal from
                # flashing between the header print and the first
                # refresh).
                initial_panel = _render_stream_panel([], clamped_hz, 0.0, mock)
                try:
                    with Live(
                        initial_panel,
                        console=console,
                        auto_refresh=False,
                        transient=False,
                    ) as live:
                        try:
                            for tick in streamer.iter_readings():
                                cycles += 1
                                elapsed = _time.monotonic() - stream_start
                                panel = _render_stream_panel(
                                    tick, clamped_hz, elapsed, mock,
                                )
                                live.update(panel, refresh=True)
                                if csv_writer is not None:
                                    csv_writer.write_row(tick, elapsed)
                                if duration > 0 and elapsed >= duration:
                                    break
                        except KeyboardInterrupt:
                            # Mechanics use Ctrl+C to stop a live stream.
                            # Clean exit, not an error.
                            pass
                except ProtocolError as exc:
                    # Either the adapter broke mid-stream or the ECU
                    # went silent. Either way, the session's __exit__
                    # will still run on the way out of the outer
                    # ``with session`` — we just render the panel and
                    # return 1.
                    console.print(
                        Panel(
                            f"[red]{ICON_FAIL} ECU went silent mid-stream: "
                            f"{exc}[/red]\n\n"
                            "[dim]Check the cable, ignition state, and "
                            "rerun [bold]motodiag hardware info[/bold] "
                            "to confirm the adapter is still "
                            "reachable.[/dim]",
                            title="Stream aborted",
                            border_style="red",
                        )
                    )
                    return 1
        except NoECUDetectedError as exc:
            _render_no_ecu_panel(
                console, exc.port, exc.make_hint, exc.errors,
            )
            return 1

        elapsed_total = _time.monotonic() - stream_start
        console.print(
            f"\n[dim]Polled {cycles} cycle{'s' if cycles != 1 else ''} "
            f"in {elapsed_total:.2f}s.[/dim]"
        )
        return 0
    finally:
        if csv_writer is not None:
            csv_writer.close()


# --- Phase 144: simulator helpers --------------------------------------
#
# These live outside ``register_hardware`` so the ``scan`` / ``clear`` /
# ``info`` option-handlers can invoke them without threading state
# through Click's closure capture. They are strictly additive — nothing
# below this line changes any behavior that pre-dates Phase 144.


def _resolve_scenario(
    name_or_path: str,
    user_paths: tuple[Path, ...] = (),
) -> Scenario:
    """Resolve a scenario name or YAML path through the loader.

    Thin wrapper around :meth:`ScenarioLoader.find` — exists as a named
    helper so the CLI can swap in a fake for tests that don't want to
    hit the filesystem.
    """
    return ScenarioLoader.find(name_or_path, user_paths=user_paths)


def _simulator_badge(scenario_name: str) -> str:
    """Return the magenta ``[SIM: name]`` badge used by scan/clear/info.

    Matches the :``[MOCK]`` badge pattern from Phase 140 — Rich renders
    unknown tag-like text literally, so ``[SIM: healthy_idle]`` shows
    up verbatim in output after the surrounding magenta style resolves.
    """
    return f"[bold magenta][SIM: {scenario_name}][/bold magenta]"


def _run_scenario(
    scenario: Scenario,
    *,
    speed: float = 0.0,
    clock: Optional[SimulationClock] = None,
    max_duration_s: float = 300.0,
    log: bool = False,
    console=None,
) -> int:
    """Execute a scenario end-to-end through :class:`SimulatedAdapter`.

    Returns the shell exit code. At ``speed=0`` the clock jumps directly
    from event to event — the full timeline completes in well under a
    second, which is what the Phase 144 test suite relies on. Any
    ``speed > 0`` would use wall-clock pacing via ``time.sleep``; tests
    never engage that path (CI greps ``time.sleep`` in the test file).
    """
    if console is None:
        console = get_console()
    clk = clock if clock is not None else SimulationClock(start_s=0.0)
    adapter = SimulatedAdapter(scenario=scenario, clock=clk)
    # Connect once; the scenario's own Disconnect/Reconnect events drive
    # the live state visible through ``is_connected``.
    adapter.connect(port=f"sim://{scenario.name}", baud=0)

    try:
        # At speed=0, iterate event-by-event by advancing the clock to
        # each event's timestamp. At speed>0, wall-clock pacing — but
        # tests never pass speed>0 so we guard the sleep behind an
        # explicit branch.
        last_t = 0.0
        for idx, event in enumerate(scenario.timeline):
            if event.at_s > max_duration_s:
                console.print(
                    f"[yellow]{ICON_WARN} simulation truncated at "
                    f"{max_duration_s}s[/yellow]"
                )
                break
            if speed > 0.0:  # pragma: no cover — tests use speed=0
                dt = event.at_s - last_t
                if dt > 0:
                    _time.sleep(dt / speed)
            clk.advance(event.at_s)
            last_t = event.at_s
            if log:
                action = type(event).__name__
                console.print(
                    f"  [dim]t={event.at_s:6.2f}s[/dim]  "
                    f"[cyan]{action}[/cyan]"
                )
    finally:
        adapter.disconnect()

    return 0


# --- Phase 143: dashboard helpers --------------------------------------
#
# Module-scope helpers for the ``motodiag hardware dashboard`` subcommand.
# Kept outside ``register_hardware`` so the Phase 143 test suite can
# exercise them directly without spinning up Click. Additive only —
# Phase 140-142 / 144-145 code above this line is untouched.


def _require_textual() -> None:
    """Raise a :class:`click.ClickException` with the install hint.

    Mirrors :func:`motodiag.hardware.dashboard._require_textual` so the
    CLI surfaces the missing-dep error before any other argument
    validation runs — the mechanic sees the install command first.
    """
    from motodiag.hardware.dashboard import (
        TEXTUAL_AVAILABLE,
        _require_textual as _inner_require,
    )

    if not TEXTUAL_AVAILABLE:
        _inner_require()


def _validate_dashboard_args(
    port: Optional[str],
    replay_id: Optional[str],
    speed: float,
    bike: Optional[str],
    make: Optional[str],
    mock: bool,
) -> None:
    """Enforce the ``hardware dashboard`` flag-compatibility rules.

    Rules:

    - ``--port`` and ``--replay`` are mutually exclusive; at least one
      required.
    - ``--speed`` is replay-only and must live in ``(0.1, 100.0]``.
    - ``--bike`` / ``--make`` / ``--mock`` are live-mode only — combining
      any of them with ``--replay`` is a user error.
    - Default ``--speed=1.0`` does not trigger the "replay-only" check
      (it is the documented default) — the check only fires when the
      user explicitly sets a non-default speed in live mode.
    """
    if port and replay_id:
        raise click.UsageError(
            "--port and --replay are mutually exclusive; choose one."
        )
    if not port and not replay_id:
        raise click.UsageError(
            "--port or --replay is required — live mode needs a port, "
            "replay mode needs a recording id."
        )
    if replay_id:
        # Replay mode: live-only flags are errors.
        if bike:
            raise click.UsageError(
                "--bike is live-mode only; cannot combine with --replay."
            )
        if make:
            raise click.UsageError(
                "--make is live-mode only; cannot combine with --replay."
            )
        if mock:
            raise click.UsageError(
                "--mock is live-mode only; cannot combine with --replay."
            )
        # Validate speed inside (0.1, 100.0].
        if speed <= 0.1 or speed > 100.0:
            raise click.UsageError(
                f"--speed must be in (0.1, 100.0] (got {speed!r})."
            )
        return
    # Live mode.
    if speed != 1.0:
        raise click.UsageError(
            "--speed is only valid with --replay (replay-mode playback "
            "speed multiplier)."
        )


def _parse_dashboard_pids(raw: str) -> List[int]:
    """Parse ``--pids`` for the dashboard subcommand.

    Thin wrapper around :func:`parse_pid_list` — kept separate so the
    dashboard-specific tests can mock this without affecting the Phase
    141 stream parser.
    """
    return parse_pid_list(raw)


# --- Click wiring ------------------------------------------------------


def register_hardware(cli_group: click.Group) -> None:
    """Attach the ``hardware`` subgroup to the top-level CLI.

    Registers three subcommands — ``scan``, ``clear``, ``info`` —
    following the same ``register_*(cli_group)`` pattern used by
    :func:`cli.diagnose.register_diagnose`, :func:`cli.code.register_code`,
    :func:`cli.cache.register_cache`, etc.
    """

    @cli_group.group("hardware")
    def hardware_group() -> None:
        """Talk to the bike — scan, clear, and inspect the ECU."""

    # --- scan ---------------------------------------------------------
    @hardware_group.command("scan")
    @click.option("--port", "port", required=True,
                  help="Serial port (e.g. COM3, /dev/ttyUSB0).")
    @click.option("--bike", default=None,
                  help="Bike slug from the garage (e.g. harley-glide-2015). "
                       "Mutually exclusive with --make.")
    @click.option("--make", "make", default=None,
                  help="Manufacturer hint when no garage slug is used.")
    @click.option("--baud", type=int, default=None,
                  help="Override the per-protocol baud rate.")
    @click.option("--timeout", "timeout_s", type=float, default=2.0,
                  show_default=True,
                  help="Per-adapter connect timeout in seconds.")
    @click.option("--mock", is_flag=True, default=False,
                  help="Use the in-memory MockAdapter — no real "
                       "hardware required. Useful for dev / CI.")
    @click.option("--simulator", "simulator", default=None,
                  help="Run against a Phase 144 scenario (built-in name "
                       "or path to a YAML file). Mutually exclusive "
                       "with --mock.")
    @click.option("--retry/--no-retry", "retry", default=True,
                  show_default=True,
                  help="Retry transient connect/read failures with "
                       "exponential backoff (Phase 146). Defaults to "
                       "on for scan (safe read-only operation). "
                       "Mutually exclusive with --simulator.")
    def scan_cmd(
        port: str, bike: Optional[str], make: Optional[str],
        baud: Optional[int], timeout_s: float, mock: bool,
        simulator: Optional[str], retry: bool,
    ) -> None:
        """Read stored DTCs from the ECU and print an enriched table."""
        console = get_console()
        init_db()
        if mock and simulator:
            raise click.UsageError(
                "--mock and --simulator are mutually exclusive; choose one."
            )
        if simulator and retry:
            # Simulator has no transient failure modes; retry wrapping is a no-op. Disable silently.
            retry = False
        if bike and make:
            raise click.ClickException(
                "--bike and --make are mutually exclusive; choose one."
            )
        make_hint, _vehicle = _resolve_make_hint(bike, make)
        if bike and _vehicle is None:
            _bike_not_found(console, bike)
            raise click.exceptions.Exit(1)
        if simulator:
            # Phase 144 simulator path — build a SimulatedAdapter,
            # inject it into HardwareSession, and re-use the existing
            # scan rendering pipeline. The port string is cosmetic in
            # this branch; the session skips AutoDetector entirely.
            try:
                scenario = _resolve_scenario(simulator)
            except (FileNotFoundError, ScenarioParseError,
                    ScenarioValidationError) as exc:
                console.print(
                    Panel(
                        f"[red]{ICON_FAIL} scenario load failed: "
                        f"{exc}[/red]",
                        title="Simulator error",
                        border_style="red",
                    )
                )
                raise click.exceptions.Exit(1)
            sim_adapter = SimulatedAdapter(scenario=scenario)
            sim_adapter.connect(port=port, baud=0)
            console.print(
                f"{_simulator_badge(scenario.name)} "
                f"[dim]scenario loaded — {scenario.description}[/dim]"
            )
            dtcs = sim_adapter.read_dtcs()
            protocol_name = sim_adapter.get_protocol_name()
            vin = sim_adapter.read_vin()
            sim_adapter.disconnect()
            # Render the same scan output format the default path uses.
            if not dtcs:
                console.print(
                    Panel(
                        f"[green]{ICON_OK} No codes stored.[/green]",
                        title="DTC scan",
                        border_style="green",
                    )
                )
            else:
                table = Table(
                    title=f"DTCs stored ({len(dtcs)})",
                    header_style="bold cyan",
                )
                table.add_column("Code", style="bold")
                table.add_column("Description", overflow="fold")
                table.add_column("Category")
                table.add_column("Severity")
                table.add_column("Source")
                for raw_code in dtcs:
                    info = resolve_dtc_info(raw_code, make_hint=make_hint)
                    table.add_row(
                        info["code"],
                        info.get("description") or "-",
                        info.get("category") or "-",
                        format_severity(info.get("severity")),
                        _format_source(info["source"]),
                    )
                console.print(table)
            footer_parts = [f"Protocol: [bold]{protocol_name}[/bold]"]
            if vin:
                footer_parts.append(f"VIN: [bold]{vin}[/bold]")
            console.print("\n" + "   ".join(footer_parts))
            return
        retry_policy = RetryPolicy() if retry else None
        code = _run_scan(
            port, make_hint, baud, timeout_s, mock,
            retry_policy=retry_policy,
        )
        if code != 0:
            raise click.exceptions.Exit(code)

    # --- clear --------------------------------------------------------
    @hardware_group.command("clear")
    @click.option("--port", "port", required=True,
                  help="Serial port (e.g. COM3, /dev/ttyUSB0).")
    @click.option("--bike", default=None,
                  help="Bike slug from the garage. Mutually exclusive "
                       "with --make.")
    @click.option("--make", "make", default=None,
                  help="Manufacturer hint when no garage slug is used.")
    @click.option("--baud", type=int, default=None,
                  help="Override the per-protocol baud rate.")
    @click.option("--timeout", "timeout_s", type=float, default=2.0,
                  show_default=True,
                  help="Per-adapter connect timeout in seconds.")
    @click.option("--yes", "-y", "assume_yes", is_flag=True, default=False,
                  help="Skip the confirmation prompt.")
    @click.option("--mock", is_flag=True, default=False,
                  help="Use the in-memory MockAdapter instead of real "
                       "hardware.")
    @click.option("--simulator", "simulator", default=None,
                  help="Run against a Phase 144 scenario (built-in name "
                       "or path to a YAML file). Mutually exclusive "
                       "with --mock.")
    @click.option("--retry/--no-retry", "retry", default=False,
                  show_default=True,
                  help="Retry transient connect failures with "
                       "exponential backoff (Phase 146). Defaults to "
                       "OFF for clear — destructive ops don't duplicate "
                       "well. The ResilientAdapter wrapper never "
                       "retries clear_dtcs itself even with --retry.")
    def clear_cmd(
        port: str, bike: Optional[str], make: Optional[str],
        baud: Optional[int], timeout_s: float, assume_yes: bool,
        mock: bool, simulator: Optional[str], retry: bool,
    ) -> None:
        """Clear stored DTCs from the ECU (Mode 04)."""
        console = get_console()
        init_db()
        if mock and simulator:
            raise click.UsageError(
                "--mock and --simulator are mutually exclusive; choose one."
            )
        if simulator and retry:
            # Simulator has no transient failure modes; retry wrapping is a no-op. Disable silently.
            retry = False
        if bike and make:
            raise click.ClickException(
                "--bike and --make are mutually exclusive; choose one."
            )
        make_hint, _vehicle = _resolve_make_hint(bike, make)
        if bike and _vehicle is None:
            _bike_not_found(console, bike)
            raise click.exceptions.Exit(1)
        if simulator:
            try:
                scenario = _resolve_scenario(simulator)
            except (FileNotFoundError, ScenarioParseError,
                    ScenarioValidationError) as exc:
                console.print(
                    Panel(
                        f"[red]{ICON_FAIL} scenario load failed: "
                        f"{exc}[/red]",
                        title="Simulator error",
                        border_style="red",
                    )
                )
                raise click.exceptions.Exit(1)
            # Safety warning + confirm prompt still apply on the
            # simulator path so mechanics get the same UX.
            console.print(
                Panel(
                    f"[bold yellow]{ICON_WARN} This will clear ALL "
                    "stored DTCs from the ECU.[/bold yellow]",
                    title="Clear DTCs — safety warning",
                    border_style="yellow",
                )
            )
            if not assume_yes:
                if not click.confirm("Proceed?", default=False):
                    console.print(
                        "[yellow]Aborted — no codes cleared.[/yellow]"
                    )
                    return
            sim_adapter = SimulatedAdapter(scenario=scenario)
            sim_adapter.connect(port=port, baud=0)
            try:
                cleared = sim_adapter.clear_dtcs()
            finally:
                sim_adapter.disconnect()
            if cleared:
                console.print(
                    Panel(
                        f"{_simulator_badge(scenario.name)} "
                        f"[green]{ICON_OK} Simulator accepted "
                        "the clear.[/green]",
                        title="Clear DTCs",
                        border_style="green",
                    )
                )
                return
            console.print(
                Panel(
                    f"{_simulator_badge(scenario.name)} "
                    f"[red]{ICON_FAIL} Simulator refused the "
                    "clear.[/red]",
                    title="Clear DTCs",
                    border_style="red",
                )
            )
            raise click.exceptions.Exit(1)
        retry_policy = RetryPolicy() if retry else None
        code = _run_clear(
            port, make_hint, baud, timeout_s, mock, assume_yes,
            retry_policy=retry_policy,
        )
        if code != 0:
            raise click.exceptions.Exit(code)

    # --- info ---------------------------------------------------------
    @hardware_group.command("info")
    @click.option("--port", "port", required=True,
                  help="Serial port (e.g. COM3, /dev/ttyUSB0).")
    @click.option("--bike", default=None,
                  help="Bike slug from the garage. Mutually exclusive "
                       "with --make.")
    @click.option("--make", "make", default=None,
                  help="Manufacturer hint when no garage slug is used.")
    @click.option("--baud", type=int, default=None,
                  help="Override the per-protocol baud rate.")
    @click.option("--timeout", "timeout_s", type=float, default=2.0,
                  show_default=True,
                  help="Per-adapter connect timeout in seconds.")
    @click.option("--mock", is_flag=True, default=False,
                  help="Use the in-memory MockAdapter instead of real "
                       "hardware.")
    @click.option("--simulator", "simulator", default=None,
                  help="Run against a Phase 144 scenario (built-in name "
                       "or path to a YAML file). Mutually exclusive "
                       "with --mock.")
    @click.option("--retry/--no-retry", "retry", default=True,
                  show_default=True,
                  help="Retry transient connect/read failures with "
                       "exponential backoff (Phase 146). Defaults to "
                       "on for info (safe read-only operation). "
                       "Mutually exclusive with --simulator.")
    def info_cmd(
        port: str, bike: Optional[str], make: Optional[str],
        baud: Optional[int], timeout_s: float, mock: bool,
        simulator: Optional[str], retry: bool,
    ) -> None:
        """Identify the connected ECU — protocol, VIN, part #, sw version."""
        console = get_console()
        init_db()
        if mock and simulator:
            raise click.UsageError(
                "--mock and --simulator are mutually exclusive; choose one."
            )
        if simulator and retry:
            # Simulator has no transient failure modes; retry wrapping is a no-op. Disable silently.
            retry = False
        if bike and make:
            raise click.ClickException(
                "--bike and --make are mutually exclusive; choose one."
            )
        make_hint, _vehicle = _resolve_make_hint(bike, make)
        if bike and _vehicle is None:
            _bike_not_found(console, bike)
            raise click.exceptions.Exit(1)
        if simulator:
            try:
                scenario = _resolve_scenario(simulator)
            except (FileNotFoundError, ScenarioParseError,
                    ScenarioValidationError) as exc:
                console.print(
                    Panel(
                        f"[red]{ICON_FAIL} scenario load failed: "
                        f"{exc}[/red]",
                        title="Simulator error",
                        border_style="red",
                    )
                )
                raise click.exceptions.Exit(1)
            sim_adapter = SimulatedAdapter(scenario=scenario)
            sim_adapter.connect(port=port, baud=0)
            info = sim_adapter.identify_info()
            sim_adapter.disconnect()
            vin = info.get("vin") or "[dim]not available[/dim]"
            protocol_name = info.get("protocol_name") or "[dim]unknown[/dim]"
            body = (
                f"{_simulator_badge(scenario.name)}\n"
                f"Protocol:      [bold]{protocol_name}[/bold]\n"
                f"VIN:           [bold]{vin}[/bold]\n"
                f"Scenario:      [bold]{scenario.name}[/bold]\n"
                f"Description:   {scenario.description}"
            )
            console.print(
                Panel(
                    body,
                    title=f"ECU info — {port}",
                    border_style="cyan",
                )
            )
            return
        retry_policy = RetryPolicy() if retry else None
        code = _run_info(
            port, make_hint, baud, timeout_s, mock, console,
            retry_policy=retry_policy,
        )
        if code != 0:
            raise click.exceptions.Exit(code)

    # --- stream (Phase 141) -------------------------------------------
    @hardware_group.command("stream")
    @click.option("--port", "port", required=True,
                  help="Serial port (e.g. COM3, /dev/ttyUSB0).")
    @click.option("--bike", default=None,
                  help="Bike slug from the garage. Mutually exclusive "
                       "with --make.")
    @click.option("--make", "make", default=None,
                  help="Manufacturer hint when no garage slug is used.")
    @click.option("--baud", type=int, default=None,
                  help="Override the per-protocol baud rate.")
    @click.option("--timeout", "timeout_s", type=float, default=2.0,
                  show_default=True,
                  help="Per-adapter connect timeout in seconds.")
    @click.option("--mock", is_flag=True, default=False,
                  help="Use the in-memory MockAdapter instead of real "
                       "hardware.")
    @click.option("--pids", "pids_spec", default=None,
                  help="Comma-separated PID list (hex or decimal). "
                       "Defaults to RPM, coolant, IAT, throttle, "
                       "battery, O2 B1S1 voltage. "
                       "VSS (0x0D) omitted by default — add it "
                       "explicitly if your bike is not on a dyno.")
    @click.option("--hz", "hz", type=float, default=2.0,
                  show_default=True,
                  help="Poll rate in ticks per second. Capped at "
                       "10 Hz for ELM327-class adapters.")
    @click.option("--duration", "duration", type=float, default=0.0,
                  show_default=True,
                  help="Stop after this many seconds. 0 = run until "
                       "Ctrl+C.")
    @click.option("--output", "output_path",
                  type=click.Path(dir_okay=False, path_type=Path),
                  default=None,
                  help="Append each poll tick to this CSV file. "
                       "Creates the file with a header row on first "
                       "use; subsequent runs with the same path "
                       "append without duplicating the header.")
    def stream_cmd(
        port: str,
        bike: Optional[str],
        make: Optional[str],
        baud: Optional[int],
        timeout_s: float,
        mock: bool,
        pids_spec: Optional[str],
        hz: float,
        duration: float,
        output_path: Optional[Path],
    ) -> None:
        """Stream live Mode 01 PID values from the ECU.

        Polls a list of OBD-II PIDs on a synchronous loop and renders a
        Rich Live panel that refreshes at the requested rate. Runs until
        Ctrl+C (or ``--duration`` elapses). Optionally appends every
        tick to a CSV via ``--output`` for later analysis.
        """
        console = get_console()
        init_db()
        if bike and make:
            raise click.ClickException(
                "--bike and --make are mutually exclusive; choose one."
            )
        make_hint, _vehicle = _resolve_make_hint(bike, make)
        if bike and _vehicle is None:
            _bike_not_found(console, bike)
            raise click.exceptions.Exit(1)
        # Parse --pids into an int list (or fall back to the default
        # six-PID first-look set). parse_pid_list raises ClickException
        # on any validation failure — we let that propagate to Click's
        # standard error surface (exit 1 with a clean message).
        if pids_spec is None:
            pids: List[int] = list(_DEFAULT_STREAM_PIDS)
        else:
            pids = parse_pid_list(pids_spec)
        code = _run_stream(
            port=port,
            make_hint=make_hint,
            baud=baud,
            timeout_s=timeout_s,
            mock=mock,
            pids=pids,
            hz=hz,
            duration=duration,
            output_path=output_path,
        )
        if code != 0:
            raise click.exceptions.Exit(code)

    # --- simulate (Phase 144) -----------------------------------------
    @hardware_group.group("simulate")
    def simulate_group() -> None:
        """Drive the hardware stack against a scripted scenario (Phase 144)."""

    @simulate_group.command("list")
    @click.option("--user-path", "user_paths",
                  multiple=True, type=click.Path(path_type=Path),
                  help="Additional directory to search for user-authored "
                       "scenario YAML files. Repeatable.")
    def simulate_list(user_paths: tuple[Path, ...]) -> None:
        """List built-in scenarios plus any in user-supplied paths."""
        console = get_console()
        table = Table(
            title="Available simulator scenarios",
            header_style="bold magenta",
        )
        table.add_column("Name", style="bold")
        table.add_column("Description", overflow="fold")
        table.add_column("Protocol")
        table.add_column("Source")
        # Built-ins via ScenarioLoader.list_builtins — a single parse
        # error surfaces as a ScenarioValidationError which we let
        # propagate (built-ins are ours; a parse error is a bug).
        for scenario in ScenarioLoader.list_builtins():
            table.add_row(
                scenario.name,
                scenario.description or "-",
                scenario.protocol,
                "[green]built-in[/green]",
            )
        # User-supplied paths — load each *.yaml and show its header.
        for user_path in user_paths:
            up = Path(user_path)
            if not up.is_dir():
                continue
            for candidate in sorted(up.glob("*.yaml")):
                try:
                    scen = ScenarioLoader.from_yaml(candidate)
                except (ScenarioParseError, ScenarioValidationError):
                    continue
                table.add_row(
                    scen.name,
                    scen.description or "-",
                    scen.protocol,
                    f"[cyan]user:{candidate}[/cyan]",
                )
        console.print(table)

    @simulate_group.command("run")
    @click.argument("scenario", required=True)
    @click.option("--port", "port", default="sim://virtual",
                  show_default=True,
                  help="Virtual port label displayed in output only.")
    @click.option("--bike", default=None,
                  help="Bike slug for label-only display.")
    @click.option("--make", "make", default=None,
                  help="Manufacturer hint for label-only display.")
    @click.option("--speed", "speed", type=float, default=0.0,
                  show_default=True,
                  help="Playback speed multiplier. 0 = jump directly "
                       "from event to event (fastest, used by tests). "
                       "1 = real-time wall clock. 10 = 10x faster.")
    @click.option("--log", "log", is_flag=True, default=False,
                  help="Print one line per timeline event as it fires.")
    @click.option("--log-name", "log_name", default=None,
                  help="Optional recording name if Phase 142 is "
                       "available — captures the run for later replay.")
    @click.option("--max-duration-s", "max_duration_s", type=float,
                  default=300.0, show_default=True,
                  help="Hard stop after this many simulated seconds.")
    @click.option("--user-path", "user_paths", multiple=True,
                  type=click.Path(path_type=Path),
                  help="Extra directories to search for the scenario.")
    def simulate_run(
        scenario: str, port: str, bike: Optional[str],
        make: Optional[str], speed: float, log: bool,
        log_name: Optional[str], max_duration_s: float,
        user_paths: tuple[Path, ...],
    ) -> None:
        """Execute a scenario end-to-end through SimulatedAdapter."""
        console = get_console()
        try:
            scen = _resolve_scenario(scenario, user_paths=tuple(user_paths))
        except FileNotFoundError as exc:
            # Offer near-match hints from BUILTIN_NAMES so mechanics
            # who typo a name get a helpful nudge.
            import difflib
            suggestions = difflib.get_close_matches(
                scenario, BUILTIN_NAMES, n=3, cutoff=0.5,
            )
            body = f"[red]{ICON_FAIL} {exc}[/red]"
            if suggestions:
                sug_line = "  ".join(suggestions)
                body += f"\n\n[dim]Did you mean: [bold]{sug_line}[/bold]?[/dim]"
            console.print(
                Panel(body, title="Unknown scenario", border_style="red")
            )
            raise click.exceptions.Exit(1)
        except (ScenarioParseError, ScenarioValidationError) as exc:
            console.print(
                Panel(
                    f"[red]{ICON_FAIL} scenario load failed: {exc}[/red]",
                    title="Simulator error",
                    border_style="red",
                )
            )
            raise click.exceptions.Exit(1)
        console.print(
            f"{_simulator_badge(scen.name)} "
            f"[dim]{scen.description}[/dim]"
        )
        rc = _run_scenario(
            scen,
            speed=speed,
            max_duration_s=max_duration_s,
            log=log,
            console=console,
        )
        if log_name:
            console.print(
                f"[dim]--log-name was requested as {log_name!r}, but "
                "Phase 142 recording support is not yet available — "
                "the scenario ran without capturing.[/dim]"
            )
        console.print(
            Panel(
                f"[green]{ICON_OK} scenario {scen.name!r} "
                f"complete.[/green]",
                title="Simulator",
                border_style="green",
            )
        )
        if rc != 0:
            raise click.exceptions.Exit(rc)

    @simulate_group.command("validate")
    @click.argument("yaml_path",
                    type=click.Path(dir_okay=False, path_type=Path))
    def simulate_validate(yaml_path: Path) -> None:
        """Lint a scenario YAML — green OK panel or red line/column error."""
        console = get_console()
        try:
            scen = ScenarioLoader.from_yaml(yaml_path, validate_only=True)
        except ScenarioParseError as exc:
            loc = ""
            if exc.line is not None and exc.col is not None:
                loc = f" (line {exc.line}, col {exc.col})"
            console.print(
                Panel(
                    f"[red]{ICON_FAIL} YAML parse error{loc}: "
                    f"{exc.msg}[/red]",
                    title="Validate failed",
                    border_style="red",
                )
            )
            raise click.exceptions.Exit(1)
        except ScenarioValidationError as exc:
            console.print(
                Panel(
                    f"[red]{ICON_FAIL} scenario failed validation:"
                    f"\n{exc}[/red]",
                    title="Validate failed",
                    border_style="red",
                )
            )
            raise click.exceptions.Exit(1)
        console.print(
            Panel(
                f"[green]{ICON_OK} {scen.name}: OK[/green]\n\n"
                f"[dim]{scen.description}[/dim]\n"
                f"Protocol: {scen.protocol}\n"
                f"Timeline: {len(scen.timeline)} events",
                title="Validate",
                border_style="green",
            )
        )

    # --- dashboard (Phase 143) ----------------------------------------
    @hardware_group.command("dashboard")
    @click.option("--port", "port", default=None,
                  help="Serial port (e.g. COM3, /dev/ttyUSB0). "
                       "Mutually exclusive with --replay.")
    @click.option("--bike", default=None,
                  help="Bike slug from the garage. Live-mode only.")
    @click.option("--make", "make", default=None,
                  help="Manufacturer hint. Live-mode only.")
    @click.option("--mock", is_flag=True, default=False,
                  help="Use the in-memory MockAdapter. Live-mode only.")
    @click.option("--replay", "replay_id", default=None,
                  help="Replay a recorded session by ID. Mutually "
                       "exclusive with --port.")
    @click.option("--speed", "speed", type=float, default=1.0,
                  show_default=True,
                  help="Replay playback speed multiplier. Valid range "
                       "(0.1, 100.0]. Requires --replay.")
    @click.option("--pids", "pids_raw", default="0x0C,0x05,0x11,0x42",
                  show_default=True,
                  help="Comma-separated PID list (hex or decimal).")
    @click.option("--hz", type=float, default=5.0, show_default=True,
                  help="Poll rate in ticks per second. Live mode only. "
                       "Must be in [0.5, 20.0].")
    @click.option("--baud", type=int, default=None,
                  help="Override the per-protocol baud rate.")
    @click.option("--timeout", "timeout_s", type=float, default=2.0,
                  show_default=True,
                  help="Per-adapter connect timeout (live mode).")
    def dashboard_cmd(
        port: Optional[str],
        bike: Optional[str],
        make: Optional[str],
        mock: bool,
        replay_id: Optional[str],
        speed: float,
        pids_raw: str,
        hz: float,
        baud: Optional[int],
        timeout_s: float,
    ) -> None:
        """Launch the real-time Textual TUI dashboard.

        Requires the ``motodiag[dashboard]`` optional extra. Either
        provide ``--port`` (live) or ``--replay`` (historical playback).
        """
        # Import gate first so the user sees the install hint before
        # any other validation error.
        _require_textual()
        _validate_dashboard_args(port, replay_id, speed, bike, make, mock)
        # --hz bounds (live mode only; replay ignores it).
        if not replay_id and (hz < 0.5 or hz > 20.0):
            raise click.UsageError(
                f"--hz must be in [0.5, 20.0] (got {hz!r})."
            )
        pids = _parse_dashboard_pids(pids_raw)
        init_db()
        # --- replay mode ---------------------------------------------
        if replay_id:
            from motodiag.hardware.dashboard import (
                DashboardApp,
                ReplayDashboardSource,
            )

            try:
                rec_id_int = int(replay_id)
            except (TypeError, ValueError):
                raise click.UsageError(
                    f"--replay must be an integer recording id (got "
                    f"{replay_id!r})."
                ) from None
            source = ReplayDashboardSource(rec_id_int, speed=speed)
            app = DashboardApp(
                source=source,
                pids=pids,
                recording_manager=None,
            )
            app.run()
            return
        # --- live mode ------------------------------------------------
        console = get_console()
        if bike and make:
            raise click.ClickException(
                "--bike and --make are mutually exclusive; choose one."
            )
        make_hint, _veh = _resolve_make_hint(bike, make)
        if bike and _veh is None:
            _bike_not_found(console, bike)
            raise click.exceptions.Exit(1)
        from motodiag.hardware.dashboard import (
            DashboardApp,
            LiveDashboardSource,
        )
        from motodiag.hardware.recorder import RecordingManager

        # port must be non-None here (validator guarantees it).
        with HardwareSession(
            port=port or "",
            make_hint=make_hint,
            baud=baud,
            timeout_s=timeout_s,
            mock=mock,
        ) as adapter:
            source = LiveDashboardSource(adapter, pids, hz)
            rec_mgr = RecordingManager()
            vehicle_id_fk = None
            if _veh is not None:
                vehicle_id_fk = _veh.get("id")
            app = DashboardApp(
                source=source,
                pids=pids,
                recording_manager=rec_mgr,
                vehicle_id=vehicle_id_fk,
                make_hint=make_hint,
            )
            app.run()

    # --- log (Phase 142) ----------------------------------------------
    # Attach the `log` subgroup last so Phase 140/141/144 registration
    # remains byte-for-byte identical above this line.
    register_log(hardware_group)

    # --- compat (Phase 145) -------------------------------------------
    # Adapter compatibility knowledge base. Additive — Phase 140/141/
    # 142/144 registration remains unchanged.
    register_compat(hardware_group)

    # --- diagnose (Phase 146) -----------------------------------------
    # 5-step interactive connection troubleshooter. Additive — no
    # existing command body changes.
    register_diagnose(hardware_group)


# --- Phase 142: log subgroup ------------------------------------------
#
# Eight subcommands under ``motodiag hardware log``: start, stop, list,
# show, replay, diff, export, prune. All additive — Phase 140/141/144
# code paths above this line are untouched.


def _resolve_vehicle_id_for_log(
    bike: Optional[str], make: Optional[str],
) -> Tuple[Optional[int], Optional[str], Optional[dict]]:
    """Translate --bike/--make into a vehicle_id FK + make hint.

    Mirrors :func:`_resolve_make_hint` but returns the vehicle row's
    primary key (nullable — dealer-lot pre-sale workflow allows
    ``vehicle_id=NULL``). Raises :class:`click.ClickException` on the
    --bike / --make mutex collision so the CLI surface stays consistent
    with Phases 140, 141, and 144.
    """
    if bike and make:
        raise click.ClickException(
            "--bike and --make are mutually exclusive; choose one."
        )
    if bike:
        vehicle = _resolve_bike_slug(bike)
        if vehicle is None:
            return None, None, None
        raw_make = (vehicle.get("make") or "").strip().lower()
        return vehicle.get("id"), raw_make or None, vehicle
    if make:
        return None, make.strip().lower() or None, None
    return None, None, None


def _run_log_start_inline(
    *,
    adapter,
    recorder,
    vehicle_id: Optional[int],
    label: Optional[str],
    pids: List[int],
    protocol_name: str,
    notes: Optional[str],
    interval: float,
    duration: float,
) -> Tuple[int, int]:
    """Inline polling loop that feeds ``recorder.append_samples``.

    Phase 142 ships without a strict dependency on Phase 141's
    :class:`~motodiag.hardware.sensors.SensorStreamer`. When the
    streamer is importable we use it (so we get the SAE J1979 catalog
    decoder for free); when it isn't we fall back to calling
    ``adapter.read_pid(pid)`` directly and building dict-shaped
    "readings" the recorder adaptation helper understands.

    Returns ``(recording_id, cycles_run)``.
    """
    pids_hex_strings = [f"0x{pid:02X}" for pid in pids]
    recording_id = recorder.start_recording(
        vehicle_id=vehicle_id,
        label=label,
        pids=pids_hex_strings,
        protocol_name=protocol_name,
        notes=notes,
    )

    streamer = None
    try:  # pragma: no cover — happy path with Phase 141 landed
        from motodiag.hardware.sensors import SensorStreamer
        streamer = SensorStreamer(
            adapter, pids, hz=(1.0 / max(interval, 0.001)),
        )
    except Exception:  # noqa: BLE001 — defensive fallback
        streamer = None

    cycles = 0
    start = _time.monotonic()
    try:
        if streamer is not None:  # pragma: no cover
            for tick in streamer.iter_readings():
                cycles += 1
                recorder.append_samples(recording_id, tick)
                elapsed = _time.monotonic() - start
                if duration > 0 and elapsed >= duration:
                    break
        else:
            while True:
                cycles += 1
                readings = []
                now = datetime.now(timezone.utc)
                for pid in pids:
                    try:
                        raw = adapter.read_pid(pid)
                    except Exception:  # noqa: BLE001
                        raw = None
                    readings.append(
                        {
                            "pid": pid,
                            "pid_hex": f"0x{pid:02X}",
                            "name": f"PID 0x{pid:02X}",
                            "value": float(raw) if raw is not None else None,
                            "unit": "",
                            "raw": raw,
                            "captured_at": now,
                            "status": "ok" if raw is not None else "unsupported",
                        }
                    )
                recorder.append_samples(recording_id, readings)
                elapsed = _time.monotonic() - start
                if duration > 0 and elapsed >= duration:
                    break
                _time.sleep(interval)
    except KeyboardInterrupt:
        pass

    return recording_id, cycles


def register_log(hardware_group: click.Group) -> None:
    """Attach the ``hardware log`` subgroup to the hardware command group.

    Eight subcommands cover the recording lifecycle: start / stop / list
    / show / replay / diff / export / prune. Each opens its own
    :class:`~motodiag.hardware.recorder.RecordingManager` so the
    short-lived CLI processes don't hold onto stale in-memory buffers
    between invocations.
    """

    @hardware_group.group("log")
    def log_group() -> None:
        """Record sensor streams to disk — replay, diff, export later."""

    # --- log start ----------------------------------------------------
    @log_group.command("start")
    @click.option("--port", "port", required=True,
                  help="Serial port (e.g. COM3, /dev/ttyUSB0).")
    @click.option("--bike", default=None,
                  help="Bike slug from the garage. Mutually exclusive "
                       "with --make.")
    @click.option("--make", "make", default=None,
                  help="Manufacturer hint when no garage slug is used.")
    @click.option("--label", default=None,
                  help="Short human-readable label for this recording "
                       "(e.g. 'hot-idle pre-fix').")
    @click.option("--pids", "pids_spec", default=None,
                  help="Comma-separated PID list (hex or decimal). "
                       "Defaults to Phase 141's 6-PID first-look set.")
    @click.option("--interval", "interval", type=float, default=0.5,
                  show_default=True,
                  help="Seconds between polls. 0.5 = 2 Hz.")
    @click.option("--duration", "duration", type=float, default=0.0,
                  show_default=True,
                  help="Stop after this many seconds. 0 = run until "
                       "Ctrl+C.")
    @click.option("--notes", default=None,
                  help="Free-form notes stored on the recording row.")
    @click.option("--baud", type=int, default=None,
                  help="Override the per-protocol baud rate.")
    @click.option("--timeout", "timeout_s", type=float, default=2.0,
                  show_default=True,
                  help="Per-adapter connect timeout in seconds.")
    @click.option("--mock", is_flag=True, default=False,
                  help="Use the in-memory MockAdapter instead of real "
                       "hardware.")
    @click.option("--background", is_flag=True, default=False,
                  help="Poll in a daemon thread. Stop via "
                       "`motodiag hardware log stop <id>`.")
    def log_start_cmd(
        port: str, bike: Optional[str], make: Optional[str],
        label: Optional[str], pids_spec: Optional[str],
        interval: float, duration: float, notes: Optional[str],
        baud: Optional[int], timeout_s: float, mock: bool,
        background: bool,
    ) -> None:
        """Start a new recording session."""
        from motodiag.hardware.recorder import RecordingManager
        console = get_console()
        init_db()
        vehicle_id, make_hint, vehicle = _resolve_vehicle_id_for_log(
            bike, make,
        )
        if bike and vehicle is None:
            _bike_not_found(console, bike)
            raise click.exceptions.Exit(1)
        if interval <= 0:
            raise click.ClickException("--interval must be > 0")
        if pids_spec is None:
            pids: List[int] = list(_DEFAULT_STREAM_PIDS)
        else:
            pids = parse_pid_list(pids_spec)

        recorder = RecordingManager()

        try:
            session = HardwareSession(
                port=port, make_hint=make_hint, baud=baud,
                timeout_s=timeout_s, mock=mock,
            )
            with session as adapter:
                protocol_name = adapter.get_protocol_name()
                badge = "[bold yellow][MOCK][/bold yellow] " if mock else ""
                console.print(
                    f"\n{badge}[bold cyan]{ICON_OK} Recording started"
                    f"[/bold cyan] on [bold]{port}[/bold] via "
                    f"[bold]{protocol_name}[/bold]"
                )
                recording_id, cycles = _run_log_start_inline(
                    adapter=adapter, recorder=recorder,
                    vehicle_id=vehicle_id, label=label, pids=pids,
                    protocol_name=protocol_name, notes=notes,
                    interval=interval, duration=duration,
                )
                recorder.stop_recording(recording_id)
                console.print(
                    f"[dim]Recorded {cycles} polling cycles — "
                    f"recording id [bold cyan]{recording_id}"
                    f"[/bold cyan].[/dim]"
                )
        except NoECUDetectedError as exc:
            _render_no_ecu_panel(
                console, exc.port, exc.make_hint, exc.errors,
            )
            raise click.exceptions.Exit(1)
        except click.ClickException:
            raise
        except Exception as exc:  # noqa: BLE001
            console.print(
                Panel(
                    f"[red]{ICON_FAIL} log start failed: {exc}[/red]",
                    title="Recording failed",
                    border_style="red",
                )
            )
            raise click.exceptions.Exit(1)

    # --- log stop -----------------------------------------------------
    @log_group.command("stop")
    @click.argument("recording_id", type=int)
    @click.option("--force", is_flag=True, default=False,
                  help="Stop even if the recording appears already "
                       "stopped.")
    def log_stop_cmd(recording_id: int, force: bool) -> None:
        """Stop an in-progress recording."""
        from motodiag.hardware.recorder import RecordingManager
        console = get_console()
        init_db()
        recorder = RecordingManager()
        meta = recorder._fetch_metadata(recording_id)
        if meta is None:
            raise click.ClickException(
                f"Recording {recording_id} not found."
            )
        if meta.get("stopped_at") and not force:
            console.print(
                f"[yellow]{ICON_WARN} Recording {recording_id} already "
                f"stopped at {meta['stopped_at']}. Use --force to "
                f"override.[/yellow]"
            )
            return
        recorder.stop_recording(recording_id)
        console.print(
            f"[green]{ICON_OK} Recording {recording_id} stopped.[/green]"
        )

    # --- log list -----------------------------------------------------
    @log_group.command("list")
    @click.option("--bike", default=None,
                  help="Filter by bike slug.")
    @click.option("--since", default=None,
                  help="ISO date filter (e.g. 2026-04-01).")
    @click.option("--until", default=None,
                  help="ISO date upper bound.")
    @click.option("--limit", type=int, default=50, show_default=True,
                  help="Cap the number of rows returned.")
    def log_list_cmd(
        bike: Optional[str], since: Optional[str],
        until: Optional[str], limit: int,
    ) -> None:
        """List recent recordings."""
        from motodiag.hardware.recorder import RecordingManager
        console = get_console()
        init_db()
        vehicle_id = None
        if bike:
            vehicle = _resolve_bike_slug(bike)
            if vehicle is None:
                _bike_not_found(console, bike)
                raise click.exceptions.Exit(1)
            vehicle_id = vehicle.get("id")

        recorder = RecordingManager()
        rows = recorder.list_recordings(
            vehicle_id=vehicle_id, since=since, until=until, limit=limit,
        )
        if not rows:
            console.print(
                "[yellow]No recordings match the current filters."
                "[/yellow]"
            )
            return

        table = Table(title=f"Recordings ({len(rows)})",
                      header_style="bold cyan")
        table.add_column("ID", style="bold", justify="right")
        table.add_column("Started")
        table.add_column("Stopped")
        table.add_column("Samples", justify="right")
        table.add_column("Protocol")
        table.add_column("Label")
        for row in rows:
            table.add_row(
                str(row["id"]),
                str(row.get("started_at") or "-"),
                str(row.get("stopped_at") or "[dim]active[/dim]"),
                str(row.get("sample_count") or 0),
                row.get("protocol_name") or "-",
                row.get("session_label") or "-",
            )
        console.print(table)

    # --- log show -----------------------------------------------------
    @log_group.command("show")
    @click.argument("recording_id", type=int)
    def log_show_cmd(recording_id: int) -> None:
        """Show metadata for a recording."""
        from motodiag.hardware.recorder import RecordingManager
        console = get_console()
        init_db()
        recorder = RecordingManager()
        try:
            meta, _ = recorder.load_recording(recording_id)
        except KeyError:
            raise click.ClickException(
                f"Recording {recording_id} not found."
            )
        lines = [
            f"[bold]ID:[/bold] {meta['id']}",
            f"[bold]Started:[/bold] {meta.get('started_at') or '-'}",
            (f"[bold]Stopped:[/bold] "
             f"{meta.get('stopped_at') or '[dim]active[/dim]'}"),
            f"[bold]Protocol:[/bold] {meta.get('protocol_name') or '-'}",
            f"[bold]PIDs:[/bold] {meta.get('pids_csv') or '-'}",
            f"[bold]Samples:[/bold] {meta.get('sample_count') or 0}",
            (f"[bold]File ref:[/bold] "
             f"{meta.get('file_ref') or '[dim]none[/dim]'}"),
            f"[bold]Label:[/bold] {meta.get('session_label') or '-'}",
            f"[bold]Notes:[/bold] {meta.get('notes') or '-'}",
        ]
        console.print(
            Panel("\n".join(lines),
                  title=f"Recording {recording_id}",
                  border_style="cyan")
        )

    # --- log replay ---------------------------------------------------
    @log_group.command("replay")
    @click.argument("recording_id", type=int)
    @click.option("--speed", type=float, default=1.0, show_default=True,
                  help="Playback speed. 0 = instant dump, 1 = "
                       "real-time, 10 = 10x faster than real-time.")
    @click.option("--pids", "pids_filter", default=None,
                  help="Restrict replay to this PID subset.")
    def log_replay_cmd(
        recording_id: int, speed: float, pids_filter: Optional[str],
    ) -> None:
        """Replay a recording in the terminal."""
        from motodiag.hardware.recorder import RecordingManager
        console = get_console()
        init_db()
        recorder = RecordingManager()
        try:
            meta, iterator = recorder.load_recording(recording_id)
        except KeyError:
            raise click.ClickException(
                f"Recording {recording_id} not found."
            )
        allowed_pids: Optional[set[str]] = None
        if pids_filter:
            allowed_pids = {
                f"0x{pid:02X}" for pid in parse_pid_list(pids_filter)
            }
        console.print(
            f"[dim]Replaying recording {recording_id} at "
            f"{speed:g}x — Ctrl+C to stop.[/dim]"
        )

        last_dt: Optional[datetime] = None
        try:
            for row in iterator:
                pid_hex = row.get("pid_hex") or ""
                if allowed_pids is not None and pid_hex not in allowed_pids:
                    continue
                captured_at = row.get("captured_at")
                dt = _parse_iso_dt(captured_at)
                if speed > 0 and last_dt is not None and dt is not None:
                    delta = (dt - last_dt).total_seconds()
                    if delta > 0:
                        _time.sleep(delta / speed)
                last_dt = dt if dt is not None else last_dt
                value = row.get("value")
                unit = row.get("unit") or ""
                val_cell = (
                    f"{value:g}" if isinstance(value, (int, float)) else "-"
                )
                console.print(
                    f"  [dim]{captured_at}[/dim]  "
                    f"[cyan]{pid_hex}[/cyan]  "
                    f"[bold]{val_cell}[/bold] {unit}"
                )
        except KeyboardInterrupt:
            console.print("[yellow]Replay aborted.[/yellow]")

    # --- log diff -----------------------------------------------------
    @log_group.command("diff")
    @click.argument("id1", type=int)
    @click.argument("id2", type=int)
    @click.option("--metric", type=click.Choice(["min", "max", "avg"]),
                  default="avg", show_default=True,
                  help="Stat to compare per PID.")
    def log_diff_cmd(id1: int, id2: int, metric: str) -> None:
        """Compare two recordings and flag large deltas."""
        from motodiag.hardware.recorder import RecordingManager
        console = get_console()
        init_db()
        recorder = RecordingManager()
        try:
            report = recorder.diff_recordings(id1, id2, metric=metric)
        except KeyError as exc:
            raise click.ClickException(str(exc))

        if not report.matched:
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} No overlapping PIDs between "
                    f"recordings {id1} and {id2}.[/yellow]",
                    title="Diff — zero overlap",
                    border_style="yellow",
                )
            )
            raise click.exceptions.Exit(1)

        table = Table(
            title=f"Diff {id1} -> {id2} ({metric})",
            header_style="bold cyan",
        )
        table.add_column("PID", style="bold")
        table.add_column("Name", overflow="fold")
        table.add_column(f"{metric} #1", justify="right")
        table.add_column(f"{metric} #2", justify="right")
        table.add_column("Δ", justify="right")
        table.add_column("%", justify="right")
        table.add_column("Flag")
        for d in report.matched:
            stat_1 = f"{d.stat_1:g}" if d.stat_1 is not None else "—"
            stat_2 = f"{d.stat_2:g}" if d.stat_2 is not None else "—"
            delta = f"{d.delta:+g}" if d.delta is not None else "—"
            pct = f"{d.pct_change:+.1f}%"
            flag = "🔥" if d.flagged else ""
            table.add_row(
                d.pid_hex, d.name, stat_1, stat_2, delta, pct, flag,
            )
        console.print(table)

        if report.only_in_1 or report.only_in_2:
            console.print(
                f"[dim]Only in #{id1}:[/dim] "
                f"{', '.join(report.only_in_1) or '—'}"
            )
            console.print(
                f"[dim]Only in #{id2}:[/dim] "
                f"{', '.join(report.only_in_2) or '—'}"
            )

    # --- log export ---------------------------------------------------
    @log_group.command("export")
    @click.argument("recording_id", type=int)
    @click.option("--format", "fmt",
                  type=click.Choice(["csv", "json", "parquet"]),
                  default="csv", show_default=True)
    @click.option("--output", "output_path",
                  type=click.Path(dir_okay=False, path_type=Path),
                  default=None,
                  help="Output file path (parent dirs auto-created).")
    def log_export_cmd(
        recording_id: int, fmt: str, output_path: Optional[Path],
    ) -> None:
        """Export a recording to CSV / JSON / Parquet."""
        from motodiag.hardware.recorder import RecordingManager
        console = get_console()
        init_db()
        recorder = RecordingManager()
        try:
            meta, iterator = recorder.load_recording(recording_id)
        except KeyError:
            raise click.ClickException(
                f"Recording {recording_id} not found."
            )
        samples = list(iterator)

        if output_path is None:
            output_path = Path.cwd() / f"recording_{recording_id}.{fmt}"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if fmt == "csv":
            _export_csv(output_path, meta, samples)
        elif fmt == "json":
            _export_json(output_path, meta, samples)
        else:  # parquet
            _export_parquet(output_path, meta, samples)
        console.print(
            f"[green]{ICON_OK} Exported recording {recording_id} to "
            f"[bold]{output_path}[/bold][/green]"
        )

    # --- log prune ----------------------------------------------------
    @log_group.command("prune")
    @click.option("--older-than", "older_than", type=int,
                  default=30, show_default=True,
                  help="Delete recordings older than N days.")
    @click.option("--yes", "-y", is_flag=True, default=False,
                  help="Skip the confirmation prompt.")
    def log_prune_cmd(older_than: int, yes: bool) -> None:
        """Prune old recordings and their JSONL sidecars."""
        from motodiag.hardware.recorder import RecordingManager
        console = get_console()
        init_db()
        recorder = RecordingManager()
        if not yes:
            if not click.confirm(
                f"Delete recordings older than {older_than} days?",
                default=False,
            ):
                console.print(
                    "[yellow]Aborted — nothing deleted.[/yellow]"
                )
                return
        rowcount, bytes_freed = recorder.prune(older_than_days=older_than)
        if rowcount == 0:
            console.print(
                "[dim]No recordings matched the age cutoff.[/dim]"
            )
            return
        console.print(
            f"[green]{ICON_OK} Pruned {rowcount} recording(s); "
            f"freed {bytes_freed} bytes of JSONL sidecars.[/green]"
        )


# --- Phase 142 helpers -------------------------------------------------


def _parse_iso_dt(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 string into a datetime (or None)."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _export_csv(
    output_path: Path, meta: dict, samples: list[dict],
) -> None:
    """Write the recording as a wide-format CSV.

    One column per PID, plus a leading ``captured_at`` column. Cells
    are empty strings for ticks where the PID was absent/unsupported.
    """
    pids_csv = meta.get("pids_csv") or ""
    column_pids = [
        f"0x{p.strip().upper()}" for p in pids_csv.split(",") if p.strip()
    ]
    seen = {p for p in column_pids}
    for row in samples:
        ph = row.get("pid_hex")
        if ph and ph not in seen:
            column_pids.append(ph)
            seen.add(ph)

    by_ts: dict[str, dict] = {}
    for row in samples:
        ts = row.get("captured_at") or ""
        by_ts.setdefault(ts, {})[row.get("pid_hex") or ""] = row.get("value")

    headers = ["captured_at"] + [f"pid_{p}" for p in column_pids]
    with open(output_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        for ts in sorted(by_ts.keys()):
            record = by_ts[ts]
            out_row = {"captured_at": ts}
            for p in column_pids:
                val = record.get(p)
                out_row[f"pid_{p}"] = "" if val is None else val
            writer.writerow(out_row)


def _export_json(
    output_path: Path, meta: dict, samples: list[dict],
) -> None:
    """Write the recording as ``{metadata, samples}`` JSON."""
    import json as _json
    payload = {
        "metadata": {k: v for k, v in meta.items()},
        "samples": samples,
    }
    with open(output_path, "w", encoding="utf-8") as fh:
        _json.dump(payload, fh, default=str, indent=2)


def _export_parquet(
    output_path: Path, meta: dict, samples: list[dict],
) -> None:
    """Write the recording as a Parquet file via pyarrow.

    pyarrow is a 40 MB install, so we lazy-import here and surface a
    friendly ``ClickException`` with the exact pip install hint rather
    than letting Python's ``ModuleNotFoundError`` bubble up.
    """
    try:
        import pyarrow as pa  # type: ignore
        import pyarrow.parquet as pq  # type: ignore
    except ImportError:
        raise click.ClickException(
            "Parquet export requires pyarrow. Install with: "
            "pip install 'motodiag[parquet]'"
        )
    table = pa.Table.from_pylist(samples) if samples else pa.table({})
    pq.write_table(table, str(output_path))


# ----------------------------------------------------------------------
# Phase 145: compat subgroup
# ----------------------------------------------------------------------
#
# The `motodiag hardware compat` subgroup wires the Phase 145 adapter
# compatibility knowledge base into the CLI. Seven subcommands are
# exposed under `hardware compat`: list, recommend, check, show, seed,
# note add, note list. All queries go through
# :mod:`motodiag.hardware.compat_repo`; JSON output is additive
# (``--json`` emits raw dicts for agent/automation consumption).
#
# The module is strictly additive — nothing above this line changes the
# behavior of scan/clear/info/stream/simulate/log commands. Existing
# Phase 139 / 140 / 141 / 142 / 144 tests pass unchanged.


_COMPAT_STATUS_STYLES: dict[str, str] = {
    "full": "green",
    "partial": "cyan",
    "read-only": "yellow",
    "incompatible": "red",
}


def _format_compat_status(status: str) -> str:
    """Return Rich markup for a compat status label."""
    style = _COMPAT_STATUS_STYLES.get(status, "dim")
    return f"[{style}]{status}[/{style}]"


def _format_price_cents(price_cents: int) -> str:
    """Format an integer cents price as a human-friendly USD string."""
    dollars = price_cents / 100.0
    return f"${dollars:,.2f}"


def register_compat(hardware_group: click.Group) -> None:
    """Attach the ``compat`` subgroup to the ``hardware`` group.

    Phase 145 entry point. Called from :func:`register_hardware` so the
    ``hardware compat`` subgroup is registered alongside scan / clear /
    info / stream / simulate / log.

    Subcommands:

    - ``compat list`` — Rich table of all adapters with optional chipset
      / transport filters.
    - ``compat recommend`` — ranked adapters for a given bike.
    - ``compat check`` — color-coded verdict for a specific
      adapter-vs-bike pair.
    - ``compat show`` — adapter detail + nested compat matrix.
    - ``compat seed`` — idempotent reload of the JSON knowledge base.
    - ``compat note add`` / ``compat note list`` — mechanic notes layer.
    """
    import json as _json
    from motodiag.hardware import compat_loader as _cl
    from motodiag.hardware import compat_repo as _cr

    @hardware_group.group("compat")
    def compat_group() -> None:
        """Adapter compatibility knowledge base (Phase 145)."""

    # --- compat list ------------------------------------------------------
    @compat_group.command("list")
    @click.option("--chipset", default=None,
                  help="Filter by chipset (ELM327, STN1110, STN2100, "
                       "proprietary, etc.).")
    @click.option("--transport", default=None,
                  help="Filter by transport (bluetooth, usb, wifi, "
                       "obd-dongle, bridge).")
    @click.option("--json", "as_json", is_flag=True, default=False,
                  help="Emit raw JSON (agent / automation mode).")
    def compat_list(
        chipset: Optional[str],
        transport: Optional[str],
        as_json: bool,
    ) -> None:
        """List all known OBD adapters with capability flags."""
        console = get_console()
        init_db()
        rows = _cr.list_adapters(chipset=chipset, transport=transport)
        if as_json:
            click.echo(_json.dumps(rows, indent=2, default=str))
            return
        if not rows:
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} No adapters match the filter."
                    "[/yellow]\n\n[dim]Run "
                    "[bold]motodiag hardware compat seed[/bold] to load "
                    "the knowledge base.[/dim]",
                    title="Adapter catalog",
                    border_style="yellow",
                )
            )
            return
        table = Table(
            title=f"OBD Adapter Catalog ({len(rows)} entries)",
            header_style="bold cyan",
        )
        table.add_column("Brand")
        table.add_column("Model", overflow="fold")
        table.add_column("Chipset")
        table.add_column("Transport")
        table.add_column("Price", justify="right")
        table.add_column("BiDir", justify="center")
        table.add_column("M22", justify="center")
        table.add_column("Rel.", justify="center")
        for row in rows:
            bidir_mark = "[green]yes[/green]" if row.get("supports_bidirectional") else "[dim]no[/dim]"
            m22_mark = "[green]yes[/green]" if row.get("supports_mode22") else "[dim]no[/dim]"
            rel = int(row.get("reliability_1to5") or 3)
            rel_str = str(rel) + "/5"
            table.add_row(
                str(row.get("brand") or "-"),
                str(row.get("model") or "-"),
                str(row.get("chipset") or "-"),
                str(row.get("transport") or "-"),
                _format_price_cents(int(row.get("price_usd_cents") or 0)),
                bidir_mark,
                m22_mark,
                rel_str,
            )
        console.print(table)

    # --- compat recommend -------------------------------------------------
    @compat_group.command("recommend")
    @click.option("--bike", default=None,
                  help="Bike slug from the garage. Mutually exclusive "
                       "with --make/--model.")
    @click.option("--make", "make", default=None,
                  help="Bike make (used with --model).")
    @click.option("--model", "model", default=None,
                  help="Bike model (used with --make).")
    @click.option("--year", "year", type=int, default=None,
                  help="Bike year for tighter year-range matching.")
    @click.option("--min-status", "min_status", default="read-only",
                  type=click.Choice(list(_cr.STATUS_VALUES)),
                  show_default=True,
                  help="Weakest status to include.")
    @click.option("--limit", "limit", type=int, default=20,
                  show_default=True,
                  help="Max results (0 = no limit).")
    @click.option("--json", "as_json", is_flag=True, default=False,
                  help="Emit raw JSON.")
    def compat_recommend(
        bike: Optional[str],
        make: Optional[str],
        model: Optional[str],
        year: Optional[int],
        min_status: str,
        limit: int,
        as_json: bool,
    ) -> None:
        """Rank adapters compatible with a given bike."""
        console = get_console()
        init_db()
        if bike and (make or model):
            raise click.ClickException(
                "--bike is mutually exclusive with --make/--model."
            )
        resolved_make: Optional[str] = None
        resolved_model: Optional[str] = None
        resolved_year: Optional[int] = year
        if bike:
            vehicle = _resolve_bike_slug(bike)
            if vehicle is None:
                _bike_not_found(console, bike)
                raise click.exceptions.Exit(1)
            resolved_make = (vehicle.get("make") or "").strip().lower() or None
            resolved_model = (vehicle.get("model") or "").strip() or None
            if resolved_year is None and vehicle.get("year"):
                resolved_year = int(vehicle["year"])
        else:
            if not make or not model:
                raise click.ClickException(
                    "Provide --bike or both --make and --model."
                )
            resolved_make = make.strip().lower()
            resolved_model = model.strip()

        rows = _cr.list_compatible_adapters(
            make=resolved_make,
            model=resolved_model,
            year=resolved_year,
            min_status=min_status,
        )
        if limit and limit > 0:
            rows = rows[:limit]

        if as_json:
            click.echo(_json.dumps(rows, indent=2, default=str))
            return

        header = (
            f"Recommended adapters for "
            f"[bold]{resolved_make}[/bold] "
            f"[bold]{resolved_model}[/bold]"
        )
        if resolved_year:
            header += f" ([bold]{resolved_year}[/bold])"
        console.print(f"\n{header}")

        if not rows:
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} No compat entries known for this "
                    "bike.[/yellow]\n\n"
                    "[dim]Run [bold]motodiag hardware compat list[/bold] to "
                    "see the full catalog, or contribute a note via "
                    "[bold]motodiag hardware compat note add[/bold].[/dim]",
                    title="No matches",
                    border_style="yellow",
                )
            )
            return

        # Group by status tier for visual clarity.
        status_order = ("full", "partial", "read-only", "incompatible")
        grouped: dict[str, list[dict]] = {s: [] for s in status_order}
        for r in rows:
            s = r.get("status", "read-only")
            if s in grouped:
                grouped[s].append(r)

        for status in status_order:
            group_rows = grouped[status]
            if not group_rows:
                continue
            table = Table(
                title=f"{_format_compat_status(status)} "
                      f"({len(group_rows)})",
                header_style="bold cyan",
            )
            table.add_column("Brand")
            table.add_column("Model", overflow="fold")
            table.add_column("Chipset")
            table.add_column("Price", justify="right")
            table.add_column("Rel.", justify="center")
            table.add_column("BiDir", justify="center")
            table.add_column("Notes", overflow="fold")
            for row in group_rows:
                bidir_mark = "[green]yes[/green]" if row.get("supports_bidirectional") else "[dim]no[/dim]"
                rel = int(row.get("reliability_1to5") or 3)
                rel_str = f"{rel}/5"
                compat_notes = row.get("compat_notes") or ""
                if len(compat_notes) > 80:
                    compat_notes = compat_notes[:77] + "..."
                table.add_row(
                    str(row.get("brand") or "-"),
                    str(row.get("adapter_model") or "-"),
                    str(row.get("chipset") or "-"),
                    _format_price_cents(int(row.get("price_usd_cents") or 0)),
                    rel_str,
                    bidir_mark,
                    compat_notes or "[dim]—[/dim]",
                )
            console.print(table)

    # --- compat check -----------------------------------------------------
    @compat_group.command("check")
    @click.option("--adapter", "adapter_slug", required=True,
                  help="Adapter slug to check.")
    @click.option("--bike", default=None,
                  help="Bike slug. Mutually exclusive with --make/--model.")
    @click.option("--make", "make", default=None,
                  help="Bike make.")
    @click.option("--model", "model", default=None,
                  help="Bike model.")
    @click.option("--year", "year", type=int, default=None,
                  help="Bike year.")
    @click.option("--json", "as_json", is_flag=True, default=False,
                  help="Emit raw JSON.")
    def compat_check(
        adapter_slug: str,
        bike: Optional[str],
        make: Optional[str],
        model: Optional[str],
        year: Optional[int],
        as_json: bool,
    ) -> None:
        """Color-coded compatibility verdict for (adapter, bike)."""
        console = get_console()
        init_db()
        if bike and (make or model):
            raise click.ClickException(
                "--bike is mutually exclusive with --make/--model."
            )
        resolved_make: Optional[str] = None
        resolved_model: Optional[str] = None
        resolved_year: Optional[int] = year
        if bike:
            vehicle = _resolve_bike_slug(bike)
            if vehicle is None:
                _bike_not_found(console, bike)
                raise click.exceptions.Exit(1)
            resolved_make = (vehicle.get("make") or "").strip().lower() or None
            resolved_model = (vehicle.get("model") or "").strip() or None
            if resolved_year is None and vehicle.get("year"):
                resolved_year = int(vehicle["year"])
        else:
            if not make or not model:
                raise click.ClickException(
                    "Provide --bike or both --make and --model."
                )
            resolved_make = make.strip().lower()
            resolved_model = model.strip()

        adapter = _cr.get_adapter(adapter_slug)
        if adapter is None:
            console.print(
                Panel(
                    f"[red]{ICON_FAIL} Unknown adapter "
                    f"[bold]{adapter_slug!r}[/bold].[/red]\n\n"
                    "[dim]Run [bold]motodiag hardware compat list[/bold] "
                    "to see known slugs.[/dim]",
                    title="Adapter not found",
                    border_style="red",
                )
            )
            raise click.exceptions.Exit(1)

        result = _cr.check_compatibility(
            adapter_slug=adapter_slug,
            make=resolved_make,
            model=resolved_model,
            year=resolved_year,
        )
        notes = _cr.get_compat_notes(adapter_slug, make=resolved_make)

        if as_json:
            click.echo(_json.dumps(
                {
                    "adapter": adapter,
                    "bike": {
                        "make": resolved_make,
                        "model": resolved_model,
                        "year": resolved_year,
                    },
                    "verdict": result,
                    "notes": notes,
                },
                indent=2, default=str,
            ))
            return

        brand = adapter.get("brand") or "-"
        adapter_model = adapter.get("model") or "-"
        if result is None:
            body = (
                f"[dim]{ICON_WARN} Unknown: no compat entry for "
                f"[bold]{brand} {adapter_model}[/bold] on "
                f"[bold]{resolved_make} {resolved_model}"
                f"{f' ({resolved_year})' if resolved_year else ''}[/bold]."
                "[/dim]\n\n"
                "[dim]This is NOT the same as 'incompatible' — it means "
                "we have no data. Consider contributing via "
                "[bold]motodiag hardware compat note add[/bold].[/dim]"
            )
            border = "yellow"
            title = "Compat verdict — unknown"
        else:
            status = result.get("status", "unknown")
            border = _COMPAT_STATUS_STYLES.get(status, "dim")
            title = f"Compat verdict — {status}"
            verdict_line = _format_compat_status(status)
            body_lines = [
                f"{verdict_line}  "
                f"[bold]{brand} {adapter_model}[/bold] on "
                f"[bold]{resolved_make} {resolved_model}"
                f"{f' ({resolved_year})' if resolved_year else ''}[/bold]",
            ]
            if result.get("compat_notes"):
                body_lines.append("")
                body_lines.append(
                    f"[dim]Details:[/dim] {result['compat_notes']}"
                )
            if result.get("verified_by"):
                body_lines.append(
                    f"[dim]Verified by:[/dim] {result['verified_by']}"
                )
            body = "\n".join(body_lines)

        console.print(Panel(body, title=title, border_style=border))

        if notes:
            notes_table = Table(
                title=f"Related notes ({len(notes)})",
                header_style="bold magenta",
            )
            notes_table.add_column("Type")
            notes_table.add_column("Make")
            notes_table.add_column("Body", overflow="fold")
            notes_table.add_column("Source", overflow="fold")
            for note in notes[:10]:
                notes_table.add_row(
                    str(note.get("note_type", "-")),
                    str(note.get("vehicle_make", "-")),
                    str(note.get("body", "-")),
                    str(note.get("source_url") or "[dim]—[/dim]"),
                )
            console.print(notes_table)

    # --- compat show ------------------------------------------------------
    @compat_group.command("show")
    @click.option("--adapter", "adapter_slug", required=True,
                  help="Adapter slug to show.")
    @click.option("--json", "as_json", is_flag=True, default=False,
                  help="Emit raw JSON.")
    def compat_show(adapter_slug: str, as_json: bool) -> None:
        """Show adapter detail + its full compat matrix."""
        console = get_console()
        init_db()
        adapter = _cr.get_adapter(adapter_slug)
        if adapter is None:
            console.print(
                Panel(
                    f"[red]{ICON_FAIL} Unknown adapter "
                    f"[bold]{adapter_slug!r}[/bold].[/red]",
                    title="Adapter not found",
                    border_style="red",
                )
            )
            raise click.exceptions.Exit(1)

        # Fetch all compat rows for the adapter directly — the
        # list_compatible_adapters helper is bike-scoped.
        from motodiag.core.database import get_connection
        with get_connection() as conn:
            cursor = conn.execute(
                """SELECT vehicle_make, vehicle_model_pattern,
                          year_min, year_max, status, notes, verified_by
                   FROM adapter_compatibility
                   WHERE adapter_id = ?
                   ORDER BY vehicle_make COLLATE NOCASE,
                            vehicle_model_pattern COLLATE NOCASE,
                            year_min""",
                (adapter["id"],),
            )
            compat_rows = [dict(r) for r in cursor.fetchall()]

        if as_json:
            click.echo(_json.dumps(
                {"adapter": adapter, "compat": compat_rows},
                indent=2, default=str,
            ))
            return

        body = (
            f"[bold]{adapter.get('brand')} {adapter.get('model')}[/bold]\n\n"
            f"Slug:        [cyan]{adapter.get('slug')}[/cyan]\n"
            f"Chipset:     [bold]{adapter.get('chipset')}[/bold]\n"
            f"Transport:   [bold]{adapter.get('transport')}[/bold]\n"
            f"Price:       [bold]{_format_price_cents(int(adapter.get('price_usd_cents') or 0))}[/bold]\n"
            f"Protocols:   {adapter.get('supported_protocols_csv')}\n"
            f"BiDir:       {'[green]yes[/green]' if adapter.get('supports_bidirectional') else '[dim]no[/dim]'}\n"
            f"Mode 22:     {'[green]yes[/green]' if adapter.get('supports_mode22') else '[dim]no[/dim]'}\n"
            f"Reliability: [bold]{adapter.get('reliability_1to5')}/5[/bold]"
        )
        if adapter.get("purchase_url"):
            body += f"\nURL:         [dim]{adapter['purchase_url']}[/dim]"
        if adapter.get("notes"):
            body += f"\n\n[dim]{adapter['notes']}[/dim]"
        if adapter.get("known_issues"):
            body += (
                f"\n\n[yellow]Known issues:[/yellow] "
                f"[dim]{adapter['known_issues']}[/dim]"
            )
        console.print(
            Panel(body, title="Adapter detail", border_style="cyan")
        )

        if compat_rows:
            table = Table(
                title=f"Compatibility matrix ({len(compat_rows)} rows)",
                header_style="bold cyan",
            )
            table.add_column("Make")
            table.add_column("Model pattern", overflow="fold")
            table.add_column("Years", justify="center")
            table.add_column("Status")
            table.add_column("Notes", overflow="fold")
            for row in compat_rows:
                ymin = row.get("year_min")
                ymax = row.get("year_max")
                if ymin is None and ymax is None:
                    year_str = "all"
                elif ymin is None:
                    year_str = f"<={ymax}"
                elif ymax is None:
                    year_str = f"{ymin}+"
                else:
                    year_str = f"{ymin}-{ymax}"
                table.add_row(
                    str(row.get("vehicle_make") or "-"),
                    str(row.get("vehicle_model_pattern") or "-"),
                    year_str,
                    _format_compat_status(str(row.get("status") or "-")),
                    str(row.get("notes") or "[dim]—[/dim]"),
                )
            console.print(table)

    # --- compat note group ------------------------------------------------
    @compat_group.group("note")
    def compat_note_group() -> None:
        """Mechanic-contributed compat notes (quirk/workaround/tip)."""

    @compat_note_group.command("add")
    @click.option("--adapter", "adapter_slug", required=True,
                  help="Adapter slug the note applies to.")
    @click.option("--make", "make", required=True,
                  help="Bike make (or '*' for any-make).")
    @click.option("--type", "note_type", required=True,
                  type=click.Choice(list(_cr.NOTE_TYPES)),
                  help="Note type.")
    @click.argument("body", required=True)
    @click.option("--source", "source_url", default=None,
                  help="Optional citation URL.")
    def compat_note_add(
        adapter_slug: str,
        make: str,
        note_type: str,
        body: str,
        source_url: Optional[str],
    ) -> None:
        """Add a compat note for (adapter, make)."""
        console = get_console()
        init_db()
        try:
            note_id = _cr.add_compat_note(
                adapter_slug=adapter_slug,
                make=make,
                note_type=note_type,
                body=body,
                source_url=source_url,
            )
        except ValueError as exc:
            console.print(
                Panel(
                    f"[red]{ICON_FAIL} {exc}[/red]",
                    title="Note add failed",
                    border_style="red",
                )
            )
            raise click.exceptions.Exit(1)
        console.print(
            Panel(
                f"[green]{ICON_OK} Added note #{note_id} "
                f"({note_type}) for "
                f"[bold]{adapter_slug}[/bold] / "
                f"[bold]{make}[/bold].[/green]",
                title="Note added",
                border_style="green",
            )
        )

    @compat_note_group.command("list")
    @click.option("--adapter", "adapter_slug", required=True,
                  help="Adapter slug.")
    @click.option("--make", "make", default=None,
                  help="Filter to a specific make (wildcard '*' rows "
                       "are always included).")
    @click.option("--type", "note_type", default=None,
                  type=click.Choice(list(_cr.NOTE_TYPES)),
                  help="Filter by note type.")
    @click.option("--json", "as_json", is_flag=True, default=False,
                  help="Emit raw JSON.")
    def compat_note_list(
        adapter_slug: str,
        make: Optional[str],
        note_type: Optional[str],
        as_json: bool,
    ) -> None:
        """List notes for an adapter."""
        console = get_console()
        init_db()
        notes = _cr.get_compat_notes(adapter_slug, make=make)
        if note_type:
            notes = [n for n in notes if n.get("note_type") == note_type]
        if as_json:
            click.echo(_json.dumps(notes, indent=2, default=str))
            return
        if not notes:
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} No notes for "
                    f"[bold]{adapter_slug}[/bold]"
                    f"{f' / {make}' if make else ''}.[/yellow]",
                    title="No notes",
                    border_style="yellow",
                )
            )
            return
        table = Table(
            title=f"Notes for {adapter_slug} ({len(notes)})",
            header_style="bold magenta",
        )
        table.add_column("ID", justify="right")
        table.add_column("Type")
        table.add_column("Make")
        table.add_column("Body", overflow="fold")
        table.add_column("Source", overflow="fold")
        for note in notes:
            table.add_row(
                str(note.get("id", "-")),
                str(note.get("note_type", "-")),
                str(note.get("vehicle_make", "-")),
                str(note.get("body", "-")),
                str(note.get("source_url") or "[dim]—[/dim]"),
            )
        console.print(table)

    # --- compat seed ------------------------------------------------------
    @compat_group.command("seed")
    @click.option("--data-dir", "data_dir", default=None,
                  type=click.Path(path_type=Path, file_okay=False),
                  help="Override the default compat_data/ directory.")
    @click.option("--yes", "-y", "assume_yes", is_flag=True, default=False,
                  help="Skip the confirmation prompt.")
    def compat_seed(
        data_dir: Optional[Path],
        assume_yes: bool,
    ) -> None:
        """Idempotent load of the JSON compat knowledge base."""
        console = get_console()
        init_db()
        if not assume_yes:
            if not click.confirm(
                "Seed the adapter compatibility knowledge base?",
                default=True,
            ):
                console.print("[yellow]Aborted.[/yellow]")
                return
        try:
            summary = _cl.seed_all(data_dir=data_dir)
        except (FileNotFoundError, ValueError) as exc:
            console.print(
                Panel(
                    f"[red]{ICON_FAIL} Seed failed: {exc}[/red]",
                    title="Seed error",
                    border_style="red",
                )
            )
            raise click.exceptions.Exit(1)
        console.print(
            Panel(
                f"[green]{ICON_OK} Loaded "
                f"{summary['adapters']} adapters, "
                f"{summary['matrix']} compat entries, "
                f"{summary['notes']} notes.[/green]\n\n"
                f"[dim]Re-running this command is idempotent — "
                f"duplicates are skipped at the slug / natural-key "
                f"level.[/dim]",
                title="Compat seed complete",
                border_style="green",
            )
        )


# ----------------------------------------------------------------------
# Phase 146: diagnose subcommand (5-step interactive troubleshooter)
# ----------------------------------------------------------------------
#
# ``motodiag hardware diagnose --port COM3 [--bike SLUG] [--make MAKE]
# [--mock] [--verbose]`` walks the mechanic through five numbered checks
# and emits a summary panel at the end. Each step renders a Rich panel
# with a green OK / yellow WARN / red FAIL icon, a plain-English
# observation, and (on WARN/FAIL) specific mechanic-facing remediation.
#
# Design rules that flow through every step:
#
# - No raw Python tracebacks ever reach the mechanic. Every caught
#   exception becomes a shop-floor-vocabulary sentence.
# - WARN does NOT short-circuit the run — the mechanic still gets the
#   remaining diagnostic signal. FAIL short-circuits ONLY when a later
#   step physically cannot succeed (e.g. step 1 port-open failure means
#   steps 2-5 cannot run; step 3 protocol-negotiate failure means
#   steps 4-5 cannot read).
# - ``--mock`` auto-passes the transport-level steps (1, 2) and uses
#   :class:`MockAdapter` for step 3. Steps 4 and 5 run against the mock
#   just like the real path so green-screen demos read the same way.


def _render_diagnose_step_panel(
    console,
    step_num: int,
    step_title: str,
    status: str,  # "OK", "WARN", or "FAIL"
    observation: str,
    remediation: Optional[str] = None,
) -> None:
    """Render a Rich panel for one diagnose step.

    Status colors:

    - ``"OK"`` — green border, :data:`ICON_OK` prefix.
    - ``"WARN"`` — yellow border, :data:`ICON_WARN` prefix.
    - ``"FAIL"`` — red border, :data:`ICON_FAIL` prefix.

    The observation line is always rendered; the remediation block (if
    supplied) follows an empty line for visual breathing room. The
    panel title includes the step number so the mechanic can jump to
    the right spot in the summary's "(step 3) FAIL" reference.
    """
    if status == "OK":
        icon = ICON_OK
        border = "green"
        style = "green"
    elif status == "WARN":
        icon = ICON_WARN
        border = "yellow"
        style = "yellow"
    else:  # FAIL
        icon = ICON_FAIL
        border = "red"
        style = "red"
    body_lines: list[str] = [f"[{style}]{icon} {observation}[/{style}]"]
    if remediation:
        body_lines.append("")
        body_lines.append(remediation)
    console.print(
        Panel(
            "\n".join(body_lines),
            title=f"Step {step_num}: {step_title}",
            border_style=border,
        )
    )


def _diagnose_step1_port(
    console,
    port: str,
    mock: bool,
) -> Tuple[str, Optional[str]]:
    """Run step 1 — verify the serial port can be opened.

    Returns ``(status, failure_message)``. ``status`` is ``"OK"``,
    ``"FAIL"``. On ``"OK"`` the caller proceeds; on ``"FAIL"`` the
    caller short-circuits the remaining steps because steps 2-5
    physically require an open port.

    ``--mock`` auto-passes — the mock has no real transport.
    """
    if mock:
        _render_diagnose_step_panel(
            console, 1, "Serial port open",
            "OK",
            f"[MOCK] skipping real port open on {port}",
        )
        return "OK", None
    try:
        import serial  # type: ignore
    except ImportError:
        observation = (
            "pyserial not importable — cannot check the serial port."
        )
        remediation = (
            "[dim]Install pyserial: [bold]pip install pyserial[/bold]."
            "[/dim]"
        )
        _render_diagnose_step_panel(
            console, 1, "Serial port open",
            "FAIL", observation, remediation,
        )
        return "FAIL", "pyserial missing"
    try:
        ser = serial.Serial(port)
        ser.close()
    except Exception as exc:  # noqa: BLE001
        # Serial exceptions subclass OSError on many platforms and
        # SerialException on Windows. Catch broadly — we want to
        # produce mechanic-facing prose for any open failure.
        observation = f"Could not open [bold]{port}[/bold]: {exc}"
        remediation = (
            "[dim]Remediation:[/dim]\n"
            "  • [bold]Windows:[/bold] run "
            "[bold]python -m serial.tools.list_ports[/bold] or check "
            "Device Manager → Ports (COM & LPT) for the right port "
            "name.\n"
            "  • [bold]Linux/macOS:[/bold] [bold]ls /dev/tty*[/bold] "
            "to find the adapter; add your user to the [bold]dialout"
            "[/bold] group "
            "([bold]sudo usermod -aG dialout $USER[/bold], then log out"
            " and back in).\n"
            "  • [bold]Bluetooth adapter:[/bold] pair and trust it in "
            "the OS Bluetooth settings first — paired devices expose "
            "a virtual COM / rfcomm port.\n"
            "  • [bold]USB-serial driver missing:[/bold] common "
            "chipsets are CH340, FTDI, CP210x — install the "
            "manufacturer driver if Windows doesn't recognize the "
            "adapter."
        )
        _render_diagnose_step_panel(
            console, 1, "Serial port open",
            "FAIL", observation, remediation,
        )
        return "FAIL", str(exc)
    _render_diagnose_step_panel(
        console, 1, "Serial port open",
        "OK",
        f"Port [bold]{port}[/bold] opened successfully.",
    )
    return "OK", None


def _diagnose_step2_atz(
    console,
    port: str,
    mock: bool,
) -> Tuple[str, Optional[str]]:
    """Run step 2 — ATZ handshake probe.

    Writes ``b"ATZ\\r"`` to the port, reads up to 50 bytes with a 2s
    timeout, and checks whether the reply contains any printable
    characters. A printable reply indicates an ELM327-compatible
    adapter; silence does NOT indicate failure — many non-ELM adapters
    legitimately don't speak AT. Returns ``"OK"`` on a printable reply,
    ``"WARN"`` on silence (not ``"FAIL"``).

    ``--mock`` auto-passes.
    """
    if mock:
        _render_diagnose_step_panel(
            console, 2, "Adapter responds to ATZ",
            "OK",
            "[MOCK] skipping real AT handshake — mock adapter is "
            "always ready.",
        )
        return "OK", None
    try:
        import serial  # type: ignore
    except ImportError:
        # Already handled in step 1 — this branch is defensive only.
        return "WARN", "pyserial missing"
    try:
        ser = serial.Serial(port, timeout=2.0)
        try:
            ser.write(b"ATZ\r")
            reply = ser.read(50)
        finally:
            ser.close()
    except Exception as exc:  # noqa: BLE001
        observation = (
            f"Could not send ATZ to [bold]{port}[/bold]: {exc}"
        )
        remediation = (
            "[dim]This usually means the port opened but the adapter "
            "did not accept the write. Power-cycle the adapter and "
            "retry.[/dim]"
        )
        _render_diagnose_step_panel(
            console, 2, "Adapter responds to ATZ",
            "WARN", observation, remediation,
        )
        return "WARN", str(exc)
    printable_count = sum(1 for b in bytes(reply) if 0x20 <= b < 0x7F)
    if printable_count > 0:
        _render_diagnose_step_panel(
            console, 2, "Adapter responds to ATZ",
            "OK",
            "Adapter responded to ATZ — appears ELM327-compatible.",
        )
        return "OK", None
    observation = (
        "No printable reply to ATZ within 2 seconds."
    )
    remediation = (
        "[dim]Not all adapters speak AT (native CAN dongles don't). "
        "But if yours should:[/dim]\n"
        "  • [bold]Adapter power:[/bold] OBD-II pin 16 carries +12V "
        "directly from the battery — verify with a multimeter. No "
        "power means a blown OBD fuse or a bike that cuts OBD power "
        "when the ignition is off.\n"
        "  • [bold]Power-cycle:[/bold] unplug the adapter for 10 "
        "seconds, then plug it back in. Many ELM327 clones latch up "
        "on a bad first handshake.\n"
        "  • [bold]Bluetooth:[/bold] unpair and re-pair the adapter "
        "in OS settings — stale pairings lose the serial service.\n"
        "  • [bold]Ignition:[/bold] some bikes power the OBD port "
        "only when the ignition is ON. Turn the key."
    )
    _render_diagnose_step_panel(
        console, 2, "Adapter responds to ATZ",
        "WARN", observation, remediation,
    )
    return "WARN", "silence"


def _diagnose_step3_protocol(
    console,
    port: str,
    make_hint: Optional[str],
    mock: bool,
    verbose: bool,
    bike: Optional[str],
) -> Tuple[str, Optional[object], Optional[str]]:
    """Run step 3 — protocol negotiation.

    On ``--mock`` the mock adapter is constructed directly and
    returned. Otherwise a real :class:`AutoDetector` is constructed
    with a live ``on_attempt`` callback that updates a Rich table of
    protocol attempts; the full table renders at the end of the step
    so CliRunner output stays in stable order.

    Returns ``(status, adapter_or_None, failure_message)``.
    On ``"OK"`` the live adapter is returned so steps 4 and 5 can
    read from it. On ``"FAIL"`` the caller short-circuits — steps 4
    and 5 can't run without a live adapter.
    """
    if mock:
        from motodiag.hardware.mock import MockAdapter
        adapter = MockAdapter()
        try:
            adapter.connect(port, 38400)
        except Exception as exc:  # noqa: BLE001
            _render_diagnose_step_panel(
                console, 3, "Negotiate protocol",
                "FAIL",
                f"[MOCK] adapter refused connect: {exc}",
                "[dim]This is an unusual mock configuration — check "
                "test fixtures.[/dim]",
            )
            return "FAIL", None, str(exc)
        _render_diagnose_step_panel(
            console, 3, "Negotiate protocol",
            "OK",
            f"[MOCK] negotiated protocol: "
            f"[bold]{adapter.get_protocol_name()}[/bold].",
        )
        return "OK", adapter, None

    # Real path — AutoDetector with live callback.
    attempts_log: list[tuple[str, Optional[BaseException]]] = []

    def _on_attempt(name: str, err: Optional[BaseException]) -> None:
        attempts_log.append((name, err))

    detector = AutoDetector(
        port=port,
        make_hint=make_hint,
        timeout_s=2.0,
        verbose=verbose,
        on_attempt=_on_attempt,
    )
    try:
        adapter = detector.detect()
    except NoECUDetectedError as exc:
        # Render the attempts table for mechanic-readable failure
        # explanation.
        table = Table(
            title="Protocol attempts",
            header_style="bold cyan",
        )
        table.add_column("Protocol", style="bold")
        table.add_column("Result")
        table.add_column("Detail", overflow="fold")
        for name, err in attempts_log:
            if err is None:
                table.add_row(name, "[green]OK[/green]", "")
            else:
                table.add_row(
                    name,
                    "[red]FAIL[/red]",
                    f"{type(err).__name__}: {err}",
                )
        console.print(table)

        # Mechanic-facing remediation. If the user passed --bike and
        # Phase 145 compat_repo is importable, show ranked compat hits
        # as the primary remediation. Otherwise fall back to generic
        # protocol-era guidance.
        remediation_lines: list[str] = []
        try:
            import importlib.util  # local import — avoid top-level cost
            if bike and importlib.util.find_spec(
                "motodiag.hardware.compat_repo"
            ) is not None:
                from motodiag.hardware import compat_repo as _cr
                from motodiag.cli.diagnose import _resolve_bike_slug
                vehicle = _resolve_bike_slug(bike)
                if vehicle is not None:
                    resolved_make = (
                        (vehicle.get("make") or "").strip().lower()
                        or None
                    )
                    resolved_model = (
                        (vehicle.get("model") or "").strip() or None
                    )
                    resolved_year = vehicle.get("year")
                    if resolved_make and resolved_model:
                        compat_hits = _cr.list_compatible_adapters(
                            make=resolved_make,
                            model=resolved_model,
                            year=resolved_year,
                            min_status="read-only",
                        )
                        top = compat_hits[:3]
                        if top:
                            remediation_lines.append(
                                "[dim]Ranked compat hits for this bike "
                                "(run [bold]motodiag hardware compat "
                                "recommend --bike {}[/bold] for the "
                                "full list):[/dim]".format(bike)
                            )
                            for row in top:
                                remediation_lines.append(
                                    "  • [bold]{} {}[/bold] "
                                    "([cyan]{}[/cyan])".format(
                                        row.get("brand") or "-",
                                        row.get("adapter_model") or "-",
                                        row.get("status") or "-",
                                    )
                                )
        except Exception:  # noqa: BLE001
            # Compat lookup is best-effort — never let a DB miss kill
            # the diagnose flow.
            pass

        if not remediation_lines:
            remediation_lines.append(
                "[dim]Generic guidance by manufacturer era:[/dim]\n"
                "  • [bold]Harley:[/bold] J1850 VPW pre-2011, CAN "
                "11-bit 500k 2011+. K-line is NOT used.\n"
                "  • [bold]Japanese (Honda/Yamaha/Kawasaki/Suzuki):"
                "[/bold] K-line (ISO 14230 KWP2000) pre-2010, CAN "
                "2010+. J1850 is NOT used.\n"
                "  • [bold]European (Ducati/BMW/KTM/Triumph):[/bold] "
                "CAN-first; older models may use K-line.\n"
                "  • [bold]Verify basics:[/bold] bike ignition ON, "
                "adapter LED lit, OBD port cable fully seated."
            )

        observation = (
            f"No ECU detected on [bold]{port}[/bold] after "
            f"{len(attempts_log)} protocol attempts."
        )
        _render_diagnose_step_panel(
            console, 3, "Negotiate protocol",
            "FAIL", observation, "\n".join(remediation_lines),
        )
        return "FAIL", None, str(exc)

    # Render the attempts table on success too — mechanic sees which
    # protocol won.
    if attempts_log:
        table = Table(
            title="Protocol attempts",
            header_style="bold cyan",
        )
        table.add_column("Protocol", style="bold")
        table.add_column("Result")
        table.add_column("Detail", overflow="fold")
        for name, err in attempts_log:
            if err is None:
                table.add_row(name, "[green]OK[/green]", "")
            else:
                table.add_row(
                    name,
                    "[red]FAIL[/red]",
                    f"{type(err).__name__}: {err}",
                )
        console.print(table)

    _render_diagnose_step_panel(
        console, 3, "Negotiate protocol",
        "OK",
        f"Negotiated protocol: "
        f"[bold]{adapter.get_protocol_name()}[/bold].",
    )
    return "OK", adapter, None


def _diagnose_step4_vin(
    console,
    adapter,
) -> Tuple[str, Optional[str]]:
    """Run step 4 — VIN read (Mode 09 PID 02).

    Returns ``(status, detail)``. ``status`` is ``"OK"`` on a 17-char
    VIN, ``"WARN"`` on ``None`` (many pre-2008 bikes don't implement
    Mode 09) or :class:`UnsupportedCommandError`. Never ``"FAIL"`` —
    absence of VIN does not block step 5.
    """
    try:
        vin = adapter.read_vin()
    except UnsupportedCommandError:
        observation = "Adapter reports VIN read is not supported."
        remediation = (
            "[dim]Many pre-2008 bikes predate Mode 09 PID 02. "
            "Physical fallback: check the frame neck sticker or the "
            "engine case stamping. This is not a real failure — most "
            "diagnostic workflows don't need the VIN from the ECU."
            "[/dim]"
        )
        _render_diagnose_step_panel(
            console, 4, "Read VIN",
            "WARN", observation, remediation,
        )
        return "WARN", "unsupported"
    except Exception as exc:  # noqa: BLE001
        observation = f"VIN read raised an error: {exc}"
        remediation = (
            "[dim]Continuing — the DTC scan in step 5 may still work. "
            "If all reads fail, return to step 3 and verify the "
            "protocol negotiation.[/dim]"
        )
        _render_diagnose_step_panel(
            console, 4, "Read VIN",
            "WARN", observation, remediation,
        )
        return "WARN", str(exc)
    if vin is None:
        observation = (
            "ECU did not respond to Mode 09 PID 02 (VIN)."
        )
        remediation = (
            "[dim]Many pre-2008 bikes don't implement VIN. Use the "
            "frame neck sticker or engine case stamping instead. "
            "This is not a real failure — most diagnostic workflows "
            "don't need the VIN from the ECU.[/dim]"
        )
        _render_diagnose_step_panel(
            console, 4, "Read VIN",
            "WARN", observation, remediation,
        )
        return "WARN", "not-responded"
    if len(vin) != 17:
        observation = (
            f"VIN response length {len(vin)} is not the expected 17 "
            f"characters: [bold]{vin}[/bold]"
        )
        remediation = (
            "[dim]The ECU returned a short or garbled VIN — the adapter "
            "may be reassembling a multi-frame response incorrectly. "
            "Try a different adapter if this recurs.[/dim]"
        )
        _render_diagnose_step_panel(
            console, 4, "Read VIN",
            "WARN", observation, remediation,
        )
        return "WARN", "short-vin"
    _render_diagnose_step_panel(
        console, 4, "Read VIN",
        "OK",
        f"Read 17-char VIN: [bold]{vin}[/bold]",
    )
    return "OK", vin


def _diagnose_step5_dtcs(
    console,
    adapter,
    make_hint: Optional[str],
) -> Tuple[str, Optional[str]]:
    """Run step 5 — full DTC scan (Mode 03).

    Returns ``(status, detail)``. ``status`` is ``"OK"`` on a
    successful list (empty list also counts as OK — clean bike), or
    ``"FAIL"`` when the read raises :class:`ProtocolError`. Renders
    the inline enrichment table for context.
    """
    try:
        dtcs = adapter.read_dtcs()
    except ProtocolError as exc:
        observation = f"Mode 03 DTC scan failed: {exc}"
        remediation = (
            "[dim]Typical causes:\n"
            "  • [bold]ECU security lockout:[/bold] turn the ignition "
            "OFF for 30 seconds, then ON — many ECUs auto-clear "
            "lockout after a power cycle.\n"
            "  • [bold]Enhanced DTC modes:[/bold] some makes use "
            "Mode 13 (pending) or Mode 17 (permanent) instead of "
            "Mode 03. A generic OBD-II adapter may not speak those "
            "modes — a manufacturer-specific dongle might.\n"
            "  • [bold]Ignition state:[/bold] Mode 03 requires "
            "ignition ON (engine can be OFF). Verify the key is at "
            "RUN, not OFF or ACC.[/dim]"
        )
        _render_diagnose_step_panel(
            console, 5, "DTC scan",
            "FAIL", observation, remediation,
        )
        return "FAIL", str(exc)
    except Exception as exc:  # noqa: BLE001
        observation = f"DTC scan raised an unexpected error: {exc}"
        remediation = (
            "[dim]This is not a normal protocol failure — may "
            "indicate an adapter driver bug. Power-cycle the adapter "
            "and retry.[/dim]"
        )
        _render_diagnose_step_panel(
            console, 5, "DTC scan",
            "FAIL", observation, remediation,
        )
        return "FAIL", str(exc)
    if not dtcs:
        _render_diagnose_step_panel(
            console, 5, "DTC scan",
            "OK",
            "No DTCs stored — ECU reports clean fault memory.",
        )
        return "OK", "0 codes"
    # Enrich codes via resolve_dtc_info.
    table = Table(
        title=f"DTCs stored ({len(dtcs)})",
        header_style="bold cyan",
    )
    table.add_column("Code", style="bold")
    table.add_column("Description", overflow="fold")
    table.add_column("Category")
    for code in dtcs:
        info = resolve_dtc_info(code, make_hint=make_hint)
        table.add_row(
            info["code"],
            info.get("description") or "-",
            info.get("category") or "-",
        )
    console.print(table)
    _render_diagnose_step_panel(
        console, 5, "DTC scan",
        "OK",
        f"Read {len(dtcs)} stored DTC{'s' if len(dtcs) != 1 else ''}.",
    )
    return "OK", f"{len(dtcs)} codes"


def _run_diagnose(
    port: str,
    make_hint: Optional[str],
    bike: Optional[str],
    mock: bool,
    verbose: bool,
) -> int:
    """Execute the 5-step diagnose flow. Returns the shell exit code.

    Returns 0 when all 5 steps end ``"OK"`` or ``"WARN"``; returns 1
    when any step ends ``"FAIL"``. WARN alone is not a failure — the
    mechanic may proceed to the fault that matters.
    """
    console = get_console()
    badge = "[bold yellow][MOCK][/bold yellow] " if mock else ""
    console.print(
        f"\n{badge}[bold cyan]Running 5-step connection "
        f"diagnose on {port}...[/bold cyan]\n"
    )

    results: list[tuple[int, str, str, Optional[str]]] = []

    # Step 1 — port open.
    s1_status, s1_detail = _diagnose_step1_port(console, port, mock)
    results.append((1, "Serial port open", s1_status, s1_detail))
    if s1_status == "FAIL":
        _render_diagnose_summary(console, results)
        return 1

    # Step 2 — ATZ probe.
    s2_status, s2_detail = _diagnose_step2_atz(console, port, mock)
    results.append((2, "Adapter responds to ATZ", s2_status, s2_detail))

    # Step 3 — protocol negotiate.
    s3_status, adapter, s3_detail = _diagnose_step3_protocol(
        console, port, make_hint, mock, verbose, bike,
    )
    results.append((3, "Negotiate protocol", s3_status, s3_detail))
    if s3_status == "FAIL" or adapter is None:
        _render_diagnose_summary(console, results)
        return 1

    # Step 4 — VIN read.
    try:
        s4_status, s4_detail = _diagnose_step4_vin(console, adapter)
    finally:
        pass
    results.append((4, "Read VIN", s4_status, s4_detail))

    # Step 5 — DTC scan.
    try:
        s5_status, s5_detail = _diagnose_step5_dtcs(
            console, adapter, make_hint,
        )
    finally:
        # Tear down the adapter now that we're done. Never let a
        # disconnect error mask the already-reported step status.
        try:
            adapter.disconnect()
        except Exception:  # noqa: BLE001
            pass
    results.append((5, "DTC scan", s5_status, s5_detail))

    _render_diagnose_summary(console, results)

    # Exit code policy: any FAIL → 1. WARN alone → 0.
    if any(r[2] == "FAIL" for r in results):
        return 1
    return 0


def _render_diagnose_summary(
    console,
    results: list[tuple[int, str, str, Optional[str]]],
) -> None:
    """Render the summary panel after all 5 steps ran (or short-circuited).

    Displays "N/5 checks passed" (OK only), lists WARN/FAIL steps with
    their numbers, and offers a next-step hint keyed to the first
    failure tier found.
    """
    ok_count = sum(1 for r in results if r[2] == "OK")
    total = len(results)
    issues: list[str] = []
    for step_num, title, status, detail in results:
        if status == "WARN":
            issues.append(
                f"[yellow]({step_num}) WARN[/yellow] — {title}"
                + (f": {detail}" if detail else "")
            )
        elif status == "FAIL":
            issues.append(
                f"[red]({step_num}) FAIL[/red] — {title}"
                + (f": {detail}" if detail else "")
            )

    header = f"[bold]{ok_count}/{total} checks passed.[/bold]"
    body_lines: list[str] = [header]
    if issues:
        body_lines.append("")
        body_lines.append("[bold]Issues:[/bold]")
        body_lines.extend(f"  • {line}" for line in issues)

    # Next-step hint — keyed off the highest-severity failure.
    hint: Optional[str] = None
    fails = [r for r in results if r[2] == "FAIL"]
    warns = [r for r in results if r[2] == "WARN"]
    if fails:
        first_fail_step = fails[0][0]
        if first_fail_step == 1:
            hint = (
                "[dim]Next: fix the port name / driver / OS "
                "permissions before retrying.[/dim]"
            )
        elif first_fail_step == 3:
            hint = (
                "[dim]Next: run [bold]motodiag hardware compat "
                "recommend --bike SLUG[/bold] for adapters known to "
                "work with this bike.[/dim]"
            )
        elif first_fail_step == 5:
            hint = (
                "[dim]Next: verify ignition is ON (engine can be "
                "OFF) and retry; if the failure persists the bike "
                "may use enhanced Mode 13/17 DTCs.[/dim]"
            )
        else:
            hint = (
                "[dim]Next: review the failed step's remediation "
                "panel above.[/dim]"
            )
    elif warns:
        hint = (
            "[dim]Hardware is reachable but some optional capabilities "
            "are missing. Proceed with diagnosis — the WARN items "
            "are not blockers.[/dim]"
        )
    else:
        hint = (
            "[dim]Hardware is fully operational. You can proceed to "
            "[bold]motodiag hardware scan[/bold] or [bold]motodiag "
            "hardware stream[/bold].[/dim]"
        )
    if hint:
        body_lines.append("")
        body_lines.append(hint)

    # Overall border color — red if any fail, yellow if only warns,
    # green if all ok.
    if fails:
        border = "red"
        title = "Diagnose summary — failed"
    elif warns:
        border = "yellow"
        title = "Diagnose summary — partial"
    else:
        border = "green"
        title = "Diagnose summary — all green"
    console.print(
        Panel(
            "\n".join(body_lines),
            title=title,
            border_style=border,
        )
    )


def register_diagnose(hardware_group: click.Group) -> None:
    """Attach the ``diagnose`` subcommand to the hardware command group.

    Phase 146 entry point. Called from :func:`register_hardware` after
    the other subgroups so existing command registration remains
    byte-for-byte identical above the call.
    """

    @hardware_group.command("diagnose")
    @click.option("--port", "port", required=True,
                  help="Serial port (e.g. COM3, /dev/ttyUSB0).")
    @click.option("--bike", default=None,
                  help="Bike slug from the garage. Mutually exclusive "
                       "with --make. Used to tailor protocol priority "
                       "and to rank compat hits on failure.")
    @click.option("--make", "make", default=None,
                  help="Manufacturer hint when no garage slug is used.")
    @click.option("--mock", is_flag=True, default=False,
                  help="Use the in-memory MockAdapter for a no-hardware "
                       "happy-path walkthrough of all 5 steps.")
    @click.option("--verbose", is_flag=True, default=False,
                  help="Raise the motodiag.hardware logger to INFO so "
                       "AutoDetector's per-protocol attempt log "
                       "streams to stderr alongside the step panels.")
    def diagnose_cmd(
        port: str, bike: Optional[str], make: Optional[str],
        mock: bool, verbose: bool,
    ) -> None:
        """5-step interactive connection troubleshooter (Phase 146).

        Walks the mechanic through: (1) serial-port open, (2) ATZ
        handshake, (3) protocol negotiate, (4) VIN read, (5) DTC scan.
        Each step renders a green/yellow/red panel with plain-English
        remediation. A summary at the end lists all issues plus a
        next-step hint.
        """
        console = get_console()
        init_db()
        if bike and make:
            raise click.ClickException(
                "--bike and --make are mutually exclusive; choose one."
            )
        make_hint, _vehicle = _resolve_make_hint(bike, make)
        if bike and _vehicle is None:
            _bike_not_found(console, bike)
            raise click.exceptions.Exit(1)
        if verbose:
            # Bump the hardware logger so AutoDetector's "trying CAN"
            # lines reach the mechanic. Best-effort — this does not
            # touch handler configuration.
            import logging as _logging
            _logging.getLogger("motodiag.hardware").setLevel(
                _logging.INFO,
            )
        code = _run_diagnose(port, make_hint, bike, mock, verbose)
        if code != 0:
            raise click.exceptions.Exit(code)


__all__ = [
    "register_hardware",
    "register_log",
    "register_compat",
    "register_diagnose",
]
