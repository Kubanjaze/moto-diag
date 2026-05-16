"""CLI entrypoint: ``motodiag costs`` — cloud-API cost monitoring.

Phase 195B (Commit 0) ships one subcommand: ``motodiag costs report``
rolls up the `cost_events` ledger (OpenAI Whisper transcription +
Claude-rich extraction calls). Backs the cost-monitoring surface
from Risk 8 of the Phase 195 pre-plan — admin-visible cost rollup +
the data behind the soft per-shop monthly cap.

Usage:
    motodiag costs report
    motodiag costs report --since 2026-05-01
    motodiag costs report --shop 1
    motodiag costs report --this-month --shop 1

Web dashboard is deferred (no admin web UI exists; building one is
its own phase). CLI report is the Phase 195B surface.
"""

from __future__ import annotations

from datetime import datetime, timezone

import click

from motodiag.shop.cost_repo import _month_start_iso, aggregate_costs


def register_costs(cli: click.Group) -> None:
    """Register the ``costs`` subgroup on the root CLI."""
    cli.add_command(costs)


@click.group()
def costs() -> None:
    """Cloud-API cost monitoring commands (Phase 195B+)."""


def _fmt_usd(cents: int) -> str:
    """Format integer USD cents as a dollar string."""
    return f"${cents / 100:.2f}"


@costs.command("report")
@click.option(
    "--since",
    type=str,
    default=None,
    help="Inclusive lower bound on event date (YYYY-MM-DD). "
    "Omit for all-time.",
)
@click.option(
    "--this-month",
    is_flag=True,
    default=False,
    help="Shorthand for --since <first-of-current-UTC-month>. "
    "Overrides --since when both are given.",
)
@click.option(
    "--shop",
    type=int,
    default=None,
    help="Filter to one shop id. Omit for all shops.",
)
def costs_report(
    since: str | None, this_month: bool, shop: int | None,
) -> None:
    """Roll up the cost_events ledger.

    Reports total spend + a per-kind + per-model breakdown over the
    selected window. ``--this-month`` is the cap-relevant window —
    it matches what the soft per-shop monthly cap check measures.
    """
    effective_since: str | None
    if this_month:
        effective_since = _month_start_iso()
    elif since is not None:
        # Normalize a bare YYYY-MM-DD to the SQLite-comparable form.
        try:
            datetime.strptime(since, "%Y-%m-%d")
            effective_since = f"{since} 00:00:00"
        except ValueError:
            raise click.BadParameter(
                "--since must be YYYY-MM-DD", param_hint="--since",
            )
    else:
        effective_since = None

    rollup = aggregate_costs(since=effective_since, shop_id=shop)

    window = (
        f"since {effective_since}"
        if effective_since is not None
        else "all-time"
    )
    scope = f"shop {shop}" if shop is not None else "all shops"
    click.echo(f"Cost report — {window}, {scope}")
    click.echo(
        f"  total: {_fmt_usd(rollup.total_usd_cents)} "
        f"across {rollup.event_count} call(s)"
    )
    if rollup.event_count == 0:
        return
    click.echo("  by kind:")
    for kind, cents in sorted(rollup.by_kind.items()):
        click.echo(f"    {kind:20s} {_fmt_usd(cents)}")
    click.echo("  by model:")
    for model, cents in sorted(rollup.by_model.items()):
        click.echo(f"    {model:20s} {_fmt_usd(cents)}")
