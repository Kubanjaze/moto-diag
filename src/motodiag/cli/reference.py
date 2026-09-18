"""CLI entrypoint: ``motodiag ref`` — the reference data, finally reachable.

Phase 244V. Phases 92 and 93 shipped a reference layer: 20 torque specs, 8
valve clearances, 14 service intervals and 5 wiring circuit references,
complete and tested. **No command or route could reach any of it**, and the
209B reachability gate could not see that until Phase 244U stopped a package
re-export from counting as a use.

The wiring data is the part a technician keeps a manual open for: the three
yellow stator leads and what they read at 5000 RPM, the safety-switch chain
that must be complete before the starter relay clicks, and the tips that come
from having done the job.

Usage:
    motodiag ref torque "drain plug"
    motodiag ref valve inline-4
    motodiag ref interval "brake fluid"
    motodiag ref circuit charging
    motodiag ref circuit --system electrical

**On provenance.** These values are generic and authored for this project,
not manufacturer data — the modules have always said so in a docstring, which
is not where anyone reads a number. Every screen here says it, and torque
leads with it, because an under-torqued caliper bolt is a brake failure and an
over-torqued one strips an aluminium case.
"""

from __future__ import annotations

from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from motodiag.cli.theme import ICON_WARN, get_console
from motodiag.engine.service_data import (
    # The clearance table has no ``list_all_`` accessor of its own: Phases
    # 92/93 gave torque specs, intervals and circuits a name-lister and left
    # clearances without one. Reading the table directly keeps this phase to
    # wiring up what exists rather than growing the module it wires.
    COMMON_VALVE_CLEARANCES,
    Clearance,
    ServiceInterval,
    TorqueSpec,
    get_service_interval,
    get_torque_spec,
    get_valve_clearance,
    list_all_service_intervals,
    list_all_torque_specs,
)
from motodiag.engine.wiring import (
    CircuitReference,
    get_circuit_reference,
    get_circuits_by_system,
    list_all_circuits,
)

#: Rendered under every result in this group. Phase 244V: the data is
#: authored generic reference, from the same era as a recall fixture whose
#: identifiers turned out to be fabricated (F86). Nothing here impersonates an
#: official identifier, and "typical torque for an M12 drain plug" is a real
#: category — but a reader deserves to know which kind of number they are
#: looking at, at the moment they read it, not in a module docstring.
PROVENANCE = (
    "Generic reference values curated for MotoDiag — not manufacturer data. "
    "Verify against the model-specific service manual before you rely on them."
)

#: Torque leads with its warning rather than trailing it: the number is acted
#: on the moment it is read, and both directions of error are expensive.
TORQUE_WARNING = (
    "Generic figures — check the manual for THIS bike before you pull. "
    "An under-torqued caliper bolt is a brake failure; an over-torqued one "
    "strips an aluminium case."
)

#: The valve clearances are all cold specs, which is the kind of thing that is
#: obvious to whoever wrote the table and invisible to whoever reads one row.
VALVE_NOTE = "All clearances are COLD specifications."


def register_reference(cli: click.Group) -> None:
    """Register the ``ref`` subgroup on the root CLI."""
    cli.add_command(ref)


def _provenance(console: Console) -> None:
    console.print(f"[dim]{PROVENANCE}[/dim]")


def _no_match(console: Console, query: str, available: list[str]) -> None:
    """Say what exists rather than printing nothing.

    Phase 244R fixed this same silence for ``code --category``, where a typo
    and an empty category printed the identical line. A lookup that finds
    nothing is the moment the user most needs the vocabulary.
    """
    console.print(f"[yellow]{ICON_WARN} Nothing matches {query!r}.[/yellow]")
    console.print("\n[bold]Available:[/bold]")
    for name in available:
        console.print(f"  • {name}")


@click.group()
def ref() -> None:
    """Reference data: torque specs, valve clearances, intervals, wiring."""


@ref.command("torque")
@click.argument("query", required=False)
def ref_torque(query: Optional[str]) -> None:
    """Torque specs by fastener name, or the whole table."""
    console = get_console()
    console.print(Panel(
        f"{ICON_WARN} {TORQUE_WARNING}",
        title="Before you pull the wrench",
        border_style="yellow",
    ))

    names = list_all_torque_specs()
    if query:
        spec = get_torque_spec(query)
        if spec is None:
            _no_match(console, query, names)
            raise click.exceptions.Exit(1)
        specs: list[TorqueSpec] = [spec]
    else:
        specs = [s for s in (get_torque_spec(n) for n in names) if s is not None]

    table = Table(title="Torque specifications")
    table.add_column("Fastener", style="cyan", overflow="fold")
    table.add_column("Nm", justify="right")
    table.add_column("ft-lb", justify="right")
    table.add_column("Thread locker", overflow="fold")
    table.add_column("Notes", overflow="fold")
    for spec in specs:
        table.add_row(
            spec.fastener,
            f"{spec.spec_nm:g}",
            f"{spec.spec_ftlbs:g}",
            spec.thread_locker or "—",
            spec.notes or "",
        )
    console.print(table)
    _provenance(console)


@ref.command("valve")
@click.argument("query", required=False)
def ref_valve(query: Optional[str]) -> None:
    """Valve clearances by component or engine layout."""
    console = get_console()

    names = [c["component"] for c in COMMON_VALVE_CLEARANCES]
    if query:
        clearance = get_valve_clearance(query)
        if clearance is None:
            _no_match(console, query, names)
            raise click.exceptions.Exit(1)
        items: list[Clearance] = [clearance]
    else:
        items = [c for c in (get_valve_clearance(n) for n in names) if c is not None]

    table = Table(title=f"Valve clearances — {VALVE_NOTE}")
    table.add_column("Component", style="cyan", overflow="fold")
    table.add_column("Range (mm)", justify="right")
    table.add_column("Notes", overflow="fold")
    for item in items:
        table.add_row(
            item.component,
            f"{item.spec_mm_low:g}–{item.spec_mm_high:g}",
            item.notes or "",
        )
    console.print(table)
    _provenance(console)


@ref.command("interval")
@click.argument("query", required=False)
def ref_interval(query: Optional[str]) -> None:
    """Service intervals by item."""
    console = get_console()

    names = list_all_service_intervals()
    if query:
        interval = get_service_interval(query)
        if interval is None:
            _no_match(console, query, names)
            raise click.exceptions.Exit(1)
        items: list[ServiceInterval] = [interval]
    else:
        items = [i for i in (get_service_interval(n) for n in names) if i is not None]

    table = Table(title="Service intervals")
    table.add_column("Item", style="cyan", overflow="fold")
    table.add_column("Miles", justify="right")
    table.add_column("km", justify="right")
    table.add_column("Months", justify="right")
    table.add_column("Notes", overflow="fold")
    for item in items:
        table.add_row(
            item.service_item,
            f"{item.interval_miles:,}" if item.interval_miles else "—",
            f"{item.interval_km:,}" if item.interval_km else "—",
            str(item.interval_months) if item.interval_months else "—",
            item.notes or "",
        )
    console.print(table)
    _provenance(console)


@ref.command("circuit")
@click.argument("name", required=False)
@click.option(
    "--system",
    type=str,
    default=None,
    help="Show every circuit in one system (electrical, fuel, ignition, braking).",
)
def ref_circuit(name: Optional[str], system: Optional[str]) -> None:
    """Wiring reference: wire colours, expected readings, test points, failures."""
    console = get_console()
    names = list_all_circuits()

    if system:
        circuits = get_circuits_by_system(system)
        if not circuits:
            _no_match(console, system, _systems(names))
            raise click.exceptions.Exit(1)
    elif name:
        circuit = get_circuit_reference(name)
        if circuit is None:
            _no_match(console, name, names)
            raise click.exceptions.Exit(1)
        circuits = [circuit]
    else:
        console.print("[bold]Circuit references[/bold]")
        for circuit_name in names:
            console.print(f"  • {circuit_name}")
        console.print(
            f"\n[dim]Systems: {', '.join(_systems(names))}. "
            "Show one with `motodiag ref circuit \"charging\"`.[/dim]"
        )
        _provenance(console)
        return

    for circuit in circuits:
        _render_circuit(console, circuit)
    _provenance(console)


def _systems(names: list[str]) -> list[str]:
    """The distinct system categories, via the public lookup only."""
    found = {c.system for c in (get_circuit_reference(n) for n in names)
             if c is not None and c.system}
    return sorted(found)


def _render_circuit(console: Console, circuit: CircuitReference) -> None:
    """One circuit, in the order a technician works it: what it does, what the
    wires should read, where to put the probes, what usually fails."""
    console.print(Panel(
        f"{circuit.description}\n\n"
        f"[dim]Applies to: {', '.join(circuit.makes_applicable) or 'unspecified'}[/dim]",
        # Parentheses, not brackets: rich reads `[electrical]` as a
        # markup tag and drops it, so the system silently vanished.
        title=f"{circuit.circuit_name}  ({circuit.system})",
        border_style="cyan",
    ))

    if circuit.wires:
        wires = Table(title="Wires")
        wires.add_column("Colour", style="cyan", overflow="fold")
        wires.add_column("Function", overflow="fold")
        wires.add_column("Connector", overflow="fold")
        wires.add_column("Expected reading", overflow="fold")
        for wire in circuit.wires:
            reading = wire.expected_voltage or wire.expected_resistance or "—"
            wires.add_row(
                wire.color, wire.function, wire.connector_location or "—", reading,
            )
        console.print(wires)

    for heading, rows in (
        ("Test points", circuit.test_points),
        ("Common failures", circuit.common_failures),
        ("Diagnostic tips", circuit.diagnostic_tips),
    ):
        if not rows:
            continue
        console.print(f"\n[bold]{heading}[/bold]")
        for row in rows:
            console.print(f"  • {row}")
    console.print()
