"""CLI: ``motodiag manuals {reviewer grant|revoke|list, render}`` (Phase 293).

The server's own commands for the shop manual library. A reviewer, the
person at Mekno who opens every upload before its shop can (K119), is
granted only here, never through the API. ``render`` makes missing page
images again: after a restore (the images are not backed up) or a render a
restart cut short. On live, run only after a backup.
"""

from __future__ import annotations

from typing import Optional

import click

from motodiag.auth.users_repo import get_user_by_username
from motodiag.cli.theme import get_console
from motodiag.core.database import init_db
from motodiag.manuals.render import render_manual, render_missing
from motodiag.manuals.review import grant_reviewer, list_reviewers, revoke_reviewer


def _user_id(username: str) -> int:
    user = get_user_by_username(username)
    if user is None:
        raise click.ClickException(f"no user named {username!r}; nothing was changed")
    return int(user["id"])


def register_manuals(cli_group: click.Group) -> None:
    """Attach the ``manuals`` group to the top-level CLI."""

    @cli_group.group("manuals")
    def manuals_group() -> None:
        """The shop manual library: its reviewers and its page images (Phase 293)."""

    @manuals_group.group("reviewer")
    def reviewer_group() -> None:
        """Who reviews uploaded manuals before a shop can open them."""

    @reviewer_group.command("grant")
    @click.argument("username")
    def reviewer_grant_cmd(username: str) -> None:
        """Let USERNAME review every shop's uploaded manuals."""
        init_db()
        new = grant_reviewer(_user_id(username))
        get_console().print(
            f"{username} now reviews uploaded manuals." if new
            else f"{username} already reviews uploaded manuals; nothing changed.")

    @reviewer_group.command("revoke")
    @click.argument("username")
    def reviewer_revoke_cmd(username: str) -> None:
        """Stop USERNAME reviewing uploaded manuals."""
        init_db()
        gone = revoke_reviewer(_user_id(username))
        get_console().print(
            f"{username} no longer reviews uploaded manuals." if gone
            else f"{username} was not a reviewer; nothing changed.")

    @reviewer_group.command("list")
    def reviewer_list_cmd() -> None:
        """Everyone who reviews uploaded manuals, and since when."""
        init_db()
        rows = list_reviewers()
        console = get_console()
        if not rows:
            console.print("No one reviews uploaded manuals yet.")
        for r in rows:
            console.print(f"{r['username']} (user {r['user_id']}), since {r['granted_at']}")

    @manuals_group.command("render")
    @click.option("--manual", "manual_id", type=int, default=None,
                  help="Render one manual's missing pages, by its id.")
    def render_cmd(manual_id: Optional[int]) -> None:
        """Make every missing page image again, or one manual's."""
        init_db()
        done = ({manual_id: render_manual(manual_id)} if manual_id is not None
                else render_missing())
        console = get_console()
        if not done:
            console.print("Every manual's pages are on disk; nothing to render.")
        for mid, pages in done.items():
            console.print(f"Manual {mid}: {pages} page images written.")
        console.print(f"{sum(done.values())} page images written in all.")
