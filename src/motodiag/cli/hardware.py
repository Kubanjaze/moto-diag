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

from typing import Optional, Tuple

import click
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
from motodiag.hardware.connection import HardwareSession
from motodiag.hardware.ecu_detect import NoECUDetectedError
from motodiag.knowledge.dtc_lookup import resolve_dtc_info


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
) -> int:
    """Execute the scan flow. Returns the shell exit code."""
    console = get_console()
    try:
        with HardwareSession(
            port=port,
            make_hint=make_hint,
            baud=baud,
            timeout_s=timeout_s,
            mock=mock,
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
) -> int:
    """Execute the clear flow. Returns the shell exit code."""
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
) -> int:
    """Execute the info flow. Returns the shell exit code.

    Calls :meth:`HardwareSession.identify_ecu` while the session is
    open (so the adapter is still connected), then lets the ``with``
    block tear down the connection cleanly on exit.
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
    def scan_cmd(
        port: str, bike: Optional[str], make: Optional[str],
        baud: Optional[int], timeout_s: float, mock: bool,
    ) -> None:
        """Read stored DTCs from the ECU and print an enriched table."""
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
        code = _run_scan(port, make_hint, baud, timeout_s, mock)
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
    def clear_cmd(
        port: str, bike: Optional[str], make: Optional[str],
        baud: Optional[int], timeout_s: float, assume_yes: bool,
        mock: bool,
    ) -> None:
        """Clear stored DTCs from the ECU (Mode 04)."""
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
        code = _run_clear(
            port, make_hint, baud, timeout_s, mock, assume_yes,
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
    def info_cmd(
        port: str, bike: Optional[str], make: Optional[str],
        baud: Optional[int], timeout_s: float, mock: bool,
    ) -> None:
        """Identify the connected ECU — protocol, VIN, part #, sw version."""
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
        code = _run_info(
            port, make_hint, baud, timeout_s, mock, console,
        )
        if code != 0:
            raise click.exceptions.Exit(code)


__all__ = ["register_hardware"]
