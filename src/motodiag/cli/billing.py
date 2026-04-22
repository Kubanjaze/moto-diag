"""CLI: ``motodiag subscription {show, checkout-url, portal-url,
cancel, sync}`` (Phase 176).

Named ``billing.py`` to avoid clashing with :mod:`motodiag.cli.subscription`
(which is the Phase 109 tier-enforcement utility module — not a CLI
subgroup).
"""

from __future__ import annotations

import json as _json
from typing import Optional

import click

from motodiag.billing.providers import (
    BillingProviderError, get_billing_provider,
)
from motodiag.billing.subscription_repo import (
    get_active_subscription, update_subscription, upsert_from_stripe,
)
from motodiag.cli.theme import get_console
from motodiag.core.config import get_settings
from motodiag.core.database import get_connection, init_db


SUBSCRIPTION_TIERS = ("individual", "shop", "company")


def register_subscription(cli_group: click.Group) -> None:
    """Attach the ``subscription`` subgroup to the top-level CLI."""

    @cli_group.group("subscription")
    def sub_group() -> None:
        """Manage subscriptions (Phase 176)."""

    def _resolve_user_email(user_id: int) -> Optional[str]:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT email FROM users WHERE id = ?", (user_id,),
            ).fetchone()
        return row["email"] if row else None

    @sub_group.command("show")
    @click.option("--user", "user_id", type=int, required=True)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def sub_show_cmd(user_id: int, as_json: bool):
        """Show the user's active subscription."""
        console = get_console()
        init_db()
        sub = get_active_subscription(user_id)
        if sub is None:
            if as_json:
                click.echo(_json.dumps({"active": False}))
                return
            console.print(
                f"[yellow]No active subscription for "
                f"user id={user_id}.[/yellow]"
            )
            return
        if as_json:
            click.echo(_json.dumps(
                sub.model_dump(), default=str, indent=2,
            ))
            return
        from rich.panel import Panel
        lines = [
            f"[bold]Subscription #{sub.id}[/bold]",
            f"User:                 {sub.user_id}",
            f"Tier:                 {sub.tier}",
            f"Status:               {sub.status}",
            f"Stripe customer:      {sub.stripe_customer_id or '—'}",
            f"Stripe subscription:  {sub.stripe_subscription_id or '—'}",
            f"Period ends:          {sub.current_period_end or '—'}",
            f"Cancel at period end: "
            f"{'yes' if sub.cancel_at_period_end else 'no'}",
        ]
        console.print(Panel("\n".join(lines), title="Subscription"))

    @sub_group.command("checkout-url")
    @click.option("--user", "user_id", type=int, required=True)
    @click.option("--tier",
                  type=click.Choice(list(SUBSCRIPTION_TIERS)),
                  required=True)
    def sub_checkout_cmd(user_id: int, tier: str):
        """Print a checkout URL for the user to start a subscription."""
        console = get_console()
        init_db()
        settings = get_settings()
        provider = get_billing_provider(settings=settings)
        email = _resolve_user_email(user_id)
        try:
            result = provider.create_checkout_session(
                user_id=user_id, email=email, tier=tier,
                success_url=settings.checkout_success_url,
                cancel_url=settings.checkout_cancel_url,
            )
        except BillingProviderError as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[green]Checkout URL for user id={user_id} "
            f"(tier={tier}):[/green]\n"
        )
        console.print(f"    {result.checkout_url}\n")
        console.print(
            f"[dim]Session id: {result.session_id}[/dim]"
        )

    @sub_group.command("portal-url")
    @click.option("--user", "user_id", type=int, required=True)
    def sub_portal_cmd(user_id: int):
        """Print a Customer Portal URL for the user."""
        console = get_console()
        init_db()
        settings = get_settings()
        provider = get_billing_provider(settings=settings)
        sub = get_active_subscription(user_id)
        if sub is None or not sub.stripe_customer_id:
            raise click.ClickException(
                f"user id={user_id} has no active subscription with "
                f"a Stripe customer id"
            )
        try:
            url = provider.create_portal_session(
                stripe_customer_id=sub.stripe_customer_id,
                return_url=settings.billing_portal_return_url,
            )
        except BillingProviderError as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[green]Portal URL for user id={user_id}:[/green]\n"
        )
        console.print(f"    {url}\n")

    @sub_group.command("cancel")
    @click.option("--user", "user_id", type=int, required=True)
    @click.option("--immediate", is_flag=True, default=False,
                  help="Cancel now (default: cancel at period end).")
    def sub_cancel_cmd(user_id: int, immediate: bool):
        """Cancel the user's active subscription."""
        console = get_console()
        init_db()
        sub = get_active_subscription(user_id)
        if sub is None:
            raise click.ClickException(
                f"user id={user_id} has no active subscription"
            )
        settings = get_settings()
        provider = get_billing_provider(settings=settings)
        if sub.stripe_subscription_id:
            try:
                provider.cancel_subscription(
                    sub.stripe_subscription_id,
                    immediate=immediate,
                )
            except BillingProviderError as e:
                raise click.ClickException(str(e)) from e
        # Mirror state locally (webhook will also update, but we
        # don't want the CLI to return before local DB shows
        # cancel_at_period_end=1).
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        if immediate:
            update_subscription(
                sub.id,
                status="canceled", canceled_at=now, updated_at=now,
            )
            console.print(
                f"[red]Subscription #{sub.id} "
                f"for user id={user_id} canceled immediately.[/red]"
            )
        else:
            update_subscription(
                sub.id,
                cancel_at_period_end=1, updated_at=now,
            )
            console.print(
                f"[yellow]Subscription #{sub.id} "
                f"for user id={user_id} will cancel at period end "
                f"({sub.current_period_end or 'unknown'}).[/yellow]"
            )

    @sub_group.command("sync")
    @click.option("--user", "user_id", type=int, required=True)
    def sub_sync_cmd(user_id: int):
        """Pull subscription state from the billing provider and
        reconcile the local row. Useful when a webhook is missed."""
        console = get_console()
        init_db()
        sub = get_active_subscription(user_id)
        if sub is None or not sub.stripe_subscription_id:
            raise click.ClickException(
                f"user id={user_id} has no active subscription "
                f"with a provider sub id to sync"
            )
        settings = get_settings()
        provider = get_billing_provider(settings=settings)
        try:
            remote = provider.retrieve_subscription(
                sub.stripe_subscription_id,
            )
        except BillingProviderError as e:
            raise click.ClickException(str(e)) from e
        # Apply relevant remote fields
        data = {
            "status": remote.get("status"),
            "cancel_at_period_end": bool(
                remote.get("cancel_at_period_end") or False,
            ),
        }
        upsert_from_stripe(
            user_id=user_id,
            stripe_subscription_id=sub.stripe_subscription_id,
            data=data,
        )
        console.print(
            f"[green]Synced subscription for user id={user_id} "
            f"from provider (remote status: "
            f"{remote.get('status', 'unknown')}).[/green]"
        )
