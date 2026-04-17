"""AI response cache management CLI (Phase 131).

Three subcommands under ``motodiag cache``:

- ``cache stats`` — counts, hits, dollar value saved, oldest/newest entry
- ``cache purge [--older-than N] [--yes]`` — delete rows older than N days
- ``cache clear [--yes]`` — delete everything (confirms by default)

All three talk to :mod:`motodiag.engine.cache` — the CLI is a thin
presentation layer. The engine module is callable from scripts, tests,
and the REST API without importing Click.
"""

from __future__ import annotations

from typing import Optional

import click
from rich.panel import Panel
from rich.table import Table

from motodiag.cli.theme import get_console
from motodiag.core.database import init_db
from motodiag.engine.cache import (
    get_cache_stats,
    purge_cache,
)


# Default age cutoff for `cache purge` when the user doesn't override it.
# 30 days matches the knowledge-base freshness horizon (most fault-code
# interpretations don't drift over a month); shop owners who want
# aggressive turnover can drop this or run `cache clear`.
DEFAULT_PURGE_OLDER_THAN_DAYS = 30


def _format_dollars_from_cents(cents: int) -> str:
    """Render integer cents as a dollar string. 12345 → '$123.45'."""
    return f"${cents / 100:,.2f}"


def _short_ts(ts: Optional[str]) -> str:
    """Truncate an ISO timestamp to 'YYYY-MM-DD HH:MM:SS' or return '—'."""
    if not ts:
        return "—"
    s = str(ts)
    return s[:19] if len(s) > 19 else s


def register_cache(cli_group: click.Group) -> None:
    """Attach the ``cache`` subgroup to the top-level CLI.

    Mirrors the registration pattern used by :func:`cli.diagnose.register_diagnose`
    and :func:`cli.code.register_code` so the import-order dance in
    ``cli/main.py`` stays uniform.
    """

    @cli_group.group("cache")
    def cache_group() -> None:
        """Manage the AI response cache."""

    @cache_group.command("stats")
    def cache_stats() -> None:
        """Show cache size, hit count, and approximate dollars saved."""
        console = get_console()
        init_db()

        stats = get_cache_stats()

        if stats["total_rows"] == 0:
            console.print(
                Panel(
                    "Cache is empty.\n\n"
                    "[dim]Run a diagnose or code --explain command online "
                    "to populate it.[/dim]",
                    title="AI Response Cache",
                    border_style="yellow",
                )
            )
            return

        saved = _format_dollars_from_cents(stats["total_cost_cents_saved"])
        body_table = Table.grid(padding=(0, 2))
        body_table.add_column(style="cyan", justify="right")
        body_table.add_column()
        body_table.add_row("Entries:", f"[bold]{stats['total_rows']:,}[/bold]")
        body_table.add_row("Total hits:", f"[bold]{stats['total_hits']:,}[/bold]")
        body_table.add_row("Approx saved:", f"[bold green]{saved}[/bold green]")
        body_table.add_row("Oldest entry:", _short_ts(stats["oldest_entry"]))
        body_table.add_row("Newest entry:", _short_ts(stats["newest_entry"]))

        console.print(
            Panel(
                body_table,
                title="AI Response Cache",
                border_style="cyan",
            )
        )

    @cache_group.command("purge")
    @click.option(
        "--older-than", "older_than", type=int,
        default=DEFAULT_PURGE_OLDER_THAN_DAYS,
        show_default=True,
        help="Delete entries older than N days.",
    )
    @click.option(
        "--yes", "-y", "assume_yes", is_flag=True, default=False,
        help="Skip confirmation prompt.",
    )
    def cache_purge(older_than: int, assume_yes: bool) -> None:
        """Delete cache entries older than N days (default 30)."""
        console = get_console()
        init_db()

        if not assume_yes:
            if not click.confirm(
                f"Delete cache entries older than {older_than} days?",
                default=False,
            ):
                console.print("[yellow]Cancelled.[/yellow]")
                return

        deleted = purge_cache(older_than_days=older_than)
        if deleted == 0:
            console.print(
                f"[dim]No entries older than {older_than} days found.[/dim]"
            )
        else:
            console.print(
                f"[green]Purged {deleted} cache "
                f"{'entry' if deleted == 1 else 'entries'} "
                f"older than {older_than} days.[/green]"
            )

    @cache_group.command("clear")
    @click.option(
        "--yes", "-y", "assume_yes", is_flag=True, default=False,
        help="Skip confirmation prompt.",
    )
    def cache_clear(assume_yes: bool) -> None:
        """Delete ALL cache entries. Confirms before running."""
        console = get_console()
        init_db()

        if not assume_yes:
            if not click.confirm(
                "This deletes ALL cached responses. Continue?",
                default=False,
            ):
                console.print("[yellow]Cancelled.[/yellow]")
                return

        deleted = purge_cache(older_than_days=None)
        console.print(
            f"[green]Cleared {deleted} cache "
            f"{'entry' if deleted == 1 else 'entries'}.[/green]"
        )


__all__ = ["register_cache"]
