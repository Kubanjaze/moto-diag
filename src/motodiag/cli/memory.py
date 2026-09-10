"""CLI entrypoint: ``motodiag memory`` — the shop's memory of a machine.

Phase 244M. Six subcommands:

    motodiag memory attach --vehicle 10 --customer 2
    motodiag memory compile [--vehicle 10]
    motodiag memory show --vehicle 10
    motodiag memory ask --vehicle 10 "what was done to it"
    motodiag memory forget --customer 2 [--dry-run]
    motodiag memory stats

``ask`` spends nothing. That is the point of it, and `--verbose` prints the
intent it matched so a surprising answer can be traced to a phrase rather than
guessed at.
"""

from __future__ import annotations

import click

from motodiag.memory import (
    answer_from_memory,
    attach_vehicle,
    compile_all,
    compile_vehicle,
    erase_customer,
    erase_plan,
    recall,
)
from motodiag.core.database import get_connection


def register_memory(cli: click.Group) -> None:
    """Register the ``memory`` subgroup on the root CLI."""
    cli.add_command(memory)


@click.group()
def memory() -> None:
    """Per-machine long-term memory (Phase 244M+)."""


@memory.command("attach")
@click.option("--vehicle", type=int, required=True, help="Vehicle id.")
@click.option("--customer", type=int, required=True, help="Customer id.")
def attach_cmd(vehicle: int, customer: int) -> None:
    """Record who owns a machine, so erasure can resolve to a person."""
    try:
        attach_vehicle(vehicle, customer)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Vehicle {vehicle} attached to customer {customer}.")


@memory.command("compile")
@click.option("--vehicle", type=int, default=None, help="One machine, or all.")
def compile_cmd(vehicle: int | None) -> None:
    """Compile recorded interactions into facts. Idempotent."""
    if vehicle is not None:
        inserted = compile_vehicle(vehicle)
        click.echo(f"Vehicle {vehicle}: {inserted} new fact(s).")
        return

    results = compile_all()
    total = sum(results.values())
    for vid, count in sorted(results.items()):
        if count:
            click.echo(f"  vehicle {vid}: {count} new fact(s)")
    # "inserted", not "walked" -- a re-compile reports 0, which is the
    # honest answer and the one Phase 244D's loader failed to give.
    click.echo(f"{total} new fact(s) across {len(results)} machine(s).")


@memory.command("show")
@click.option("--vehicle", type=int, required=True)
@click.option("--limit", type=int, default=None, help="Truncate the list.")
def show_cmd(vehicle: int, limit: int | None) -> None:
    """List what is known about a machine, best-supported first."""
    facts = recall(vehicle, limit=limit)
    if not facts:
        click.echo(f"No memory compiled for vehicle {vehicle}.")
        return
    click.echo(f"Memory for vehicle {vehicle} — {len(facts)} fact(s):")
    for fact in facts:
        miles = f", {fact.at_miles:,} mi" if fact.at_miles else ""
        detail = f" — {fact.value}" if fact.value else ""
        click.echo(
            f"  [{fact.fact_kind}] {fact.subject}{detail}\n"
            f"      {fact.established_at or 'date unknown'}{miles} · "
            f"{fact.source} · from {fact.origin_table}"
        )


@memory.command("ask")
@click.option("--vehicle", type=int, required=True)
@click.option("--verbose", is_flag=True, help="Show the intent that matched.")
@click.argument("question")
def ask_cmd(vehicle: int, question: str, verbose: bool) -> None:
    """Answer from memory. Never calls the API."""
    result = answer_from_memory(vehicle, question)
    if verbose and result.intent:
        click.echo(f"(intent: {result.intent})")
    click.echo(result.text)
    if not result.answered:
        raise SystemExit(1)


@memory.command("forget")
@click.option("--customer", type=int, required=True)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show exactly what would be deleted, and delete nothing.",
)
def forget_cmd(customer: int, dry_run: bool) -> None:
    """Erase a customer's compiled memory. Origin records are not touched."""
    plan = erase_plan(customer)
    if plan.refused:
        raise click.ClickException(plan.reason)

    if not plan.vehicle_ids:
        click.echo(f"Customer {customer} owns no machines — nothing to erase.")
        return

    vehicles = ", ".join(str(v) for v in plan.vehicle_ids)
    if dry_run:
        click.echo(
            f"Would delete {plan.fact_count} compiled fact(s) across "
            f"vehicle(s) {vehicles}."
        )
        click.echo(
            "Work orders, sessions and invoices are NOT touched — those are "
            "mandated records, and the compiled memory is not."
        )
        return

    deleted = erase_customer(customer)
    click.echo(f"Deleted {deleted} compiled fact(s) across vehicle(s) {vehicles}.")


@memory.command("stats")
def stats_cmd() -> None:
    """How much history actually exists, so thinness is legible."""
    with get_connection(None) as conn:
        total = conn.execute("SELECT COUNT(*) FROM memory_facts").fetchone()[0]
        by_kind = conn.execute(
            "SELECT fact_kind, COUNT(*) FROM memory_facts "
            "GROUP BY fact_kind ORDER BY 2 DESC"
        ).fetchall()
        by_source = conn.execute(
            "SELECT source, COUNT(*) FROM memory_facts "
            "GROUP BY source ORDER BY 2 DESC"
        ).fetchall()
        machines = conn.execute(
            "SELECT COUNT(DISTINCT vehicle_id) FROM memory_facts"
        ).fetchone()[0]
        unassigned = conn.execute(
            "SELECT COUNT(*) FROM vehicles WHERE customer_id = 1"
        ).fetchone()[0]
        vehicles = conn.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0]

    click.echo(f"{total} fact(s) across {machines} machine(s).")
    if by_kind:
        click.echo("  by kind:")
        for kind, count in by_kind:
            click.echo(f"    {kind:<16} {count}")
    if by_source:
        click.echo("  by source:")
        for source, count in by_source:
            click.echo(f"    {source:<18} {count}")
    if unassigned:
        click.echo(
            f"\n  {unassigned} of {vehicles} vehicle(s) still owned by the "
            "`Unassigned` sentinel — their memory cannot be attributed to a "
            "person, so an erasure request cannot reach it. "
            "`motodiag memory attach` fixes that."
        )
