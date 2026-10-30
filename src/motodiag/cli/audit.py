"""CLI: ``motodiag audit {list, verify, export}`` (Phase 348).

The operator's view of the whole audit log: every write request the API
answered, who made it and when. ``verify`` proves the hash chain and the
two append-only triggers intact; ``export`` writes a copy to keep, since
nothing is ever deleted from the log.
"""

from __future__ import annotations

import json as _json
from typing import Optional

import click

from motodiag.audit import export_events, list_events, verify_chain
from motodiag.auth.users_repo import get_user_by_username
from motodiag.cli.theme import get_console
from motodiag.core.database import get_connection, init_db


def _user_id(user: Optional[str]) -> Optional[int]:
    if user is None:
        return None
    if user.isdigit():
        return int(user)
    row = get_user_by_username(user)
    if row is None:
        raise click.ClickException(f"no user matching {user!r}")
    return int(row["id"])


def register_audit(cli_group: click.Group) -> None:
    """Attach the ``audit`` subgroup to the top-level CLI."""

    @cli_group.group("audit")
    def audit_group() -> None:
        """Read, verify and export the audit log (Phase 348)."""

    @audit_group.command("list")
    @click.option("--user", default=None, help="A user id or username.")
    @click.option("--shop", type=int, default=None, help="A shop id.")
    @click.option("--since", default=None, help="Nd, Nh, Nm or an ISO time.")
    @click.option("--until", default=None, help="Nd, Nh, Nm or an ISO time.")
    @click.option("--path", default=None, help="Only paths starting with this.")
    @click.option("--limit", type=int, default=50, show_default=True)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def audit_list_cmd(
        user: Optional[str], shop: Optional[int], since: Optional[str],
        until: Optional[str], path: Optional[str], limit: int, as_json: bool,
    ):
        """The trail, newest first."""
        init_db()
        try:
            with get_connection() as conn:
                rows = list_events(
                    conn, shop_id=shop, user_id=_user_id(user), since=since,
                    until=until, path_prefix=path, limit=limit,
                )
        except ValueError as e:
            raise click.ClickException(str(e)) from e
        if as_json:
            click.echo(_json.dumps(rows, indent=2))
            return
        console = get_console()
        if not rows:
            console.print("The audit log has no events yet.")
            return
        from rich.table import Table
        table = Table(title="Audit log")
        for col in ("ID", "When (UTC)", "Who", "Method", "Path", "Status"):
            table.add_column(col)
        for r in rows:
            who = (f"{r['actor_username']} (#{r['actor_user_id']}, {r['credential_kind']})"
                   if r["actor_user_id"] is not None else "anonymous")
            table.add_row(str(r["id"]), r["occurred_at"], who, r["method"],
                          r["path"], str(r["status"]))
        console.print(table)

    @audit_group.command("verify")
    def audit_verify_cmd():
        """Check every row's hash and link, and both triggers."""
        init_db()
        with get_connection() as conn:
            report = verify_chain(conn)
        click.echo(f"events: {report.count}")
        click.echo(f"head hash: {report.head_hash}")
        if report.missing_triggers:
            click.echo("missing trigger: " + ", ".join(report.missing_triggers))
        if report.first_bad_id is not None:
            click.echo(f"chain broken at event {report.first_bad_id}")
        if not report.ok:
            raise SystemExit(1)
        click.echo("chain intact")

    @audit_group.command("export")
    @click.argument("file", type=click.Path(dir_okay=False))
    def audit_export_cmd(file: str):
        """Every event as one JSON line, to a new FILE."""
        init_db()
        try:
            with get_connection() as conn:
                n = export_events(conn, file)
        except FileExistsError as e:
            raise click.ClickException(f"{file} exists; refusing to overwrite it") from e
        click.echo(f"wrote {n} events to {file}")
