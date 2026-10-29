"""CLI: ``motodiag user {create, list, set-password, deactivate, sessions,
logout}`` (Phase 303).

Staff logins. A user made here has a password and can log in through
``POST /v1/auth/login``; their role at a shop comes from the existing
``motodiag shop member add``. A password is read from a hidden prompt, or
from one line of standard input with ``--password-stdin``, and is never
printed, logged or put in ``--json``.
"""

from __future__ import annotations

import json as _json
import sqlite3
from typing import Optional

import click

from motodiag.auth.models import User
from motodiag.auth.passwords import (
    MIN_PASSWORD_LENGTH,
    PasswordTooShort,
    hash_password,
)
from motodiag.auth.sessions_repo import (
    list_user_sessions,
    revoke_user_sessions,
    session_client,
    session_expires_at,
)
from motodiag.auth.users_repo import (
    create_user,
    deactivate_user,
    get_user,
    get_user_by_username,
    list_users,
    update_user,
)
from motodiag.cli.theme import get_console
from motodiag.core.database import init_db


def _read_password(from_stdin: bool) -> str:
    if from_stdin:
        return click.get_text_stream("stdin").readline().rstrip("\r\n")
    return click.prompt(
        "Password", hide_input=True, confirmation_prompt=True,
    )


def _hash_or_fail(plain: str) -> str:
    try:
        return hash_password(plain)
    except PasswordTooShort as e:
        raise click.ClickException(
            f"a password needs at least {MIN_PASSWORD_LENGTH} characters"
        ) from e


def _resolve_user(identifier: str) -> dict:
    user = (
        get_user(int(identifier)) if identifier.isdigit()
        else get_user_by_username(identifier)
    )
    if user is None:
        raise click.ClickException(f"no user matching {identifier!r}")
    return user


def _lifetime() -> int:
    from motodiag.core.config import get_settings

    return get_settings().session_lifetime_days


def register_user(cli_group: click.Group) -> None:
    """Attach the ``user`` subgroup to the top-level CLI."""

    @cli_group.group("user")
    def user_group() -> None:
        """Manage staff logins (Phase 303)."""

    @user_group.command("create")
    @click.option("--username", required=True, help="The login name.")
    @click.option("--full-name", required=True, help="The person's name.")
    @click.option("--email", default=None)
    @click.option("--password-stdin", is_flag=True, default=False,
                  help="Read the password from one line of standard input.")
    def user_create_cmd(
        username: str, full_name: str, email: Optional[str],
        password_stdin: bool,
    ):
        """Create a user who can log in."""
        console = get_console()
        init_db()
        password_hash = _hash_or_fail(_read_password(password_stdin))
        try:
            user_id = create_user(User(
                username=username, full_name=full_name, email=email,
                password_hash=password_hash,
            ))
        except sqlite3.IntegrityError as e:
            raise click.ClickException(
                f"username {username!r} is already taken"
            ) from e
        console.print(f"[green]Created user #{user_id} ({username}).[/green]")
        console.print(
            "Give them a role at a shop with: "
            f"motodiag shop member add --shop <shop> --user {user_id} "
            "--role <owner|tech|service_writer|apprentice>"
        )

    @user_group.command("list")
    @click.option("--include-inactive", is_flag=True, default=False)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def user_list_cmd(include_inactive: bool, as_json: bool):
        """List users: whether a password is set, never the hash."""
        console = get_console()
        init_db()
        rows = list_users(is_active=None if include_inactive else True)
        users = [
            {
                "id": int(u["id"]),
                "username": u["username"],
                "full_name": u.get("full_name"),
                "is_active": bool(u["is_active"]),
                "password_set": bool(u.get("password_hash")),
                "open_sessions": len(list_user_sessions(int(u["id"]))),
            }
            for u in rows
        ]
        if as_json:
            click.echo(_json.dumps(users, indent=2))
            return
        from rich.table import Table
        table = Table(title="Users")
        for col in ("ID", "Username", "Name", "Active", "Password",
                    "Sessions"):
            table.add_column(col)
        for u in users:
            table.add_row(
                str(u["id"]), u["username"], u["full_name"] or "—",
                "yes" if u["is_active"] else "no",
                "set" if u["password_set"] else "none",
                str(u["open_sessions"]),
            )
        console.print(table)

    @user_group.command("set-password")
    @click.argument("user")
    @click.option("--password-stdin", is_flag=True, default=False,
                  help="Read the password from one line of standard input.")
    def user_set_password_cmd(user: str, password_stdin: bool):
        """Set a user's password (an id or a username). Ends their
        sessions."""
        console = get_console()
        init_db()
        row = _resolve_user(user)
        password_hash = _hash_or_fail(_read_password(password_stdin))
        update_user(int(row["id"]), {"password_hash": password_hash})
        ended = revoke_user_sessions(int(row["id"]))
        console.print(
            f"[green]Password set for {row['username']}; "
            f"{ended} session(s) ended.[/green]"
        )

    @user_group.command("deactivate")
    @click.argument("user")
    def user_deactivate_cmd(user: str):
        """Deactivate a user and end their sessions."""
        console = get_console()
        init_db()
        row = _resolve_user(user)
        try:
            deactivate_user(int(row["id"]))
        except ValueError as e:
            raise click.ClickException(str(e)) from e
        ended = revoke_user_sessions(int(row["id"]))
        console.print(
            f"[red]{row['username']} deactivated; "
            f"{ended} session(s) ended.[/red]"
        )

    @user_group.command("sessions")
    @click.argument("user")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def user_sessions_cmd(user: str, as_json: bool):
        """List a user's open login sessions."""
        console = get_console()
        init_db()
        row = _resolve_user(user)
        lifetime = _lifetime()
        items = [
            {
                "id": s.id,
                "prefix": s.key_prefix,
                "client": session_client(s),
                "created_at": s.created_at,
                "expires_at": session_expires_at(s, lifetime),
                "last_used_at": s.last_used_at,
            }
            for s in list_user_sessions(int(row["id"]))
        ]
        if as_json:
            click.echo(_json.dumps(items, indent=2))
            return
        if not items:
            console.print(f"[dim]No open sessions for {row['username']}.[/dim]")
            return
        from rich.table import Table
        table = Table(title=f"Sessions — {row['username']}")
        for col in ("ID", "Prefix", "Client", "Created", "Expires",
                    "Last used"):
            table.add_column(col)
        for s in items:
            table.add_row(
                str(s["id"]), s["prefix"], s["client"] or "—",
                str(s["created_at"]), s["expires_at"],
                str(s["last_used_at"] or "—"),
            )
        console.print(table)

    @user_group.command("logout")
    @click.argument("user")
    def user_logout_cmd(user: str):
        """End every login session of a user."""
        console = get_console()
        init_db()
        row = _resolve_user(user)
        ended = revoke_user_sessions(int(row["id"]))
        console.print(f"{ended} session(s) ended for {row['username']}.")
