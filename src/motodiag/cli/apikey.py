"""CLI: ``motodiag apikey {create, list, revoke, show}`` (Phase 176)."""

from __future__ import annotations

import json as _json
from typing import Optional

import click

from motodiag.auth.api_key_repo import (
    ApiKeyNotFoundError,
    create_api_key,
    get_api_key_by_id,
    get_api_key_by_prefix,
    list_api_keys,
    revoke_api_key,
)
from motodiag.cli.theme import get_console
from motodiag.core.database import init_db


def register_apikey(cli_group: click.Group) -> None:
    """Attach the ``apikey`` subgroup to the top-level CLI."""

    @cli_group.group("apikey")
    def apikey_group() -> None:
        """Manage API keys (Phase 176)."""

    @apikey_group.command("create")
    @click.option("--user", "user_id", type=int, required=True,
                  help="Owner user id.")
    @click.option("--name", default=None,
                  help="Human label (e.g. 'laptop', 'ci-bot').")
    @click.option("--env",
                  type=click.Choice(["live", "test"]),
                  default="live",
                  help="Key environment (default: live).")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def apikey_create_cmd(
        user_id: int, name: Optional[str], env: str, as_json: bool,
    ):
        """Generate + persist a new API key.

        **The plaintext key is only shown once. Save it immediately.**
        """
        console = get_console()
        init_db()
        key, plaintext = create_api_key(
            user_id=user_id, name=name, env=env,
        )
        if as_json:
            payload = key.model_dump()
            payload["plaintext"] = plaintext
            click.echo(_json.dumps(payload, default=str, indent=2))
            return
        console.print(
            f"[green]Created API key #{key.id}"
            f"{' (' + name + ')' if name else ''} "
            f"for user id={user_id}.[/green]"
        )
        console.print(
            "\n[bold yellow]Save this key NOW — it won't be "
            "shown again:[/bold yellow]"
        )
        console.print(f"\n    {plaintext}\n")
        console.print(
            f"[dim]Prefix: {key.key_prefix}   "
            f"(use this to identify the key in the future)[/dim]"
        )

    @apikey_group.command("list")
    @click.option("--user", "user_id", type=int, required=True)
    @click.option("--include-revoked", is_flag=True, default=False)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def apikey_list_cmd(
        user_id: int, include_revoked: bool, as_json: bool,
    ):
        """List API keys for a user (prefix + metadata only;
        plaintext is never stored)."""
        console = get_console()
        init_db()
        keys = list_api_keys(
            user_id=user_id, include_revoked=include_revoked,
        )
        if as_json:
            click.echo(_json.dumps(
                [k.model_dump() for k in keys], default=str, indent=2,
            ))
            return
        if not keys:
            console.print(
                f"[dim]No API keys for user id={user_id}.[/dim]"
            )
            return
        from rich.table import Table
        table = Table(title=f"API keys — user id={user_id}")
        table.add_column("ID", justify="right")
        table.add_column("Prefix")
        table.add_column("Name")
        table.add_column("Active")
        table.add_column("Last used")
        table.add_column("Created")
        for k in keys:
            table.add_row(
                str(k.id),
                k.key_prefix,
                k.name or "—",
                "yes" if k.is_active else "no",
                str(k.last_used_at or "—"),
                str(k.created_at),
            )
        console.print(table)

    @apikey_group.command("revoke")
    @click.argument("key_id", type=int)
    def apikey_revoke_cmd(key_id: int):
        """Revoke (deactivate) an API key. Irreversible."""
        console = get_console()
        init_db()
        try:
            changed = revoke_api_key(key_id)
        except ApiKeyNotFoundError as e:
            raise click.ClickException(str(e)) from e
        if not changed:
            console.print(
                f"[yellow]API key #{key_id} was already revoked.[/yellow]"
            )
            return
        console.print(
            f"[red]API key #{key_id} revoked. "
            f"All authenticated requests using this key will "
            f"now return 401.[/red]"
        )

    @apikey_group.command("show")
    @click.argument("prefix_or_id")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def apikey_show_cmd(prefix_or_id: str, as_json: bool):
        """Show metadata for a key by prefix (``mdk_live_AbCd``) or id."""
        console = get_console()
        init_db()
        key = None
        if prefix_or_id.isdigit():
            key = get_api_key_by_id(int(prefix_or_id))
        else:
            key = get_api_key_by_prefix(prefix_or_id)
        if key is None:
            raise click.ClickException(
                f"no API key found matching {prefix_or_id!r}"
            )
        if as_json:
            click.echo(_json.dumps(
                key.model_dump(), default=str, indent=2,
            ))
            return
        from rich.panel import Panel
        lines = [
            f"[bold]API key #{key.id}[/bold]",
            f"User:       {key.user_id}",
            f"Prefix:     {key.key_prefix}",
            f"Name:       {key.name or '—'}",
            f"Active:     {'yes' if key.is_active else 'no'}",
            f"Last used:  {key.last_used_at or '—'}",
            f"Created:    {key.created_at}",
        ]
        if key.revoked_at:
            lines.append(f"Revoked:    {key.revoked_at}")
        console.print(Panel("\n".join(lines), title="API key"))
