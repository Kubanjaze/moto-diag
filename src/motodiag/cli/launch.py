"""CLI: ``motodiag launch check`` (Phase 210).

Run on the server, with the server's settings in the environment. It prints
one line per launch condition, ``ready:`` or ``NOT READY:``, then ``ALL GOOD``
(exit 0) or ``SOMETHING IS OFF`` (exit 1); a database it cannot open is
exit 2. It writes nothing and prints no key or secret.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

import click

from motodiag.core.config import get_settings
from motodiag.launch import check


def register_launch(cli_group: click.Group) -> None:
    """Attach the ``launch`` group to the top-level CLI."""

    @cli_group.group("launch")
    def launch_group() -> None:
        """Launch readiness: whether one paying shop can start on live (Phase 210)."""

    @launch_group.command("check")
    @click.option("--db", "db_path", default=None,
                  help="The database to read. Default: the settings' MOTODIAG_DB_PATH.")
    def check_cmd(db_path: Optional[str]) -> None:
        """Say, read-only, whether every launch condition holds on this server."""
        settings = get_settings()
        path = db_path or settings.db_path
        try:
            conn = check.open_read_only(path)
        except sqlite3.Error as e:
            click.echo(f"The database cannot be opened: {e}")
            click.echo("SOMETHING IS OFF")
            raise click.exceptions.Exit(2) from e
        try:
            results = check.run_conditions(settings, path, conn)
        finally:
            conn.close()
        for condition in results:
            click.echo(condition.line())
        if all(c.ready for c in results):
            click.echo("ALL GOOD")
            return
        click.echo("SOMETHING IS OFF")
        raise click.exceptions.Exit(1)
