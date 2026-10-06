"""CLI for payments through Stripe (Phase 273).

- ``motodiag payments check``: whether Stripe is set up, never a value.
- ``motodiag shop payments connect|status``: a shop's connected account.
- ``motodiag shop terminal setup|pay``: the simulated reader.
- ``motodiag shop invoice pay-link|payments``: an invoice paid online.

No command marks an invoice paid: Stripe's verified event does, through
the webhook (``/v1/billing/webhooks/stripe``).
"""

from __future__ import annotations

from typing import Optional

import click
from rich.table import Table

from motodiag.cli.theme import get_console
from motodiag.core.database import init_db
from motodiag.core.timestamps import local_display
from motodiag.payments import stripe_api
from motodiag.payments.connect import (
    ConnectError, connect_shop, get_shop_account, onboarding_link,
    refresh_status,
)
from motodiag.payments.invoice_payments import (
    payments_for_invoice, start_checkout, start_terminal,
)
from motodiag.payments.terminal import setup_simulated_reader

PAID_BY_EVENT = (
    "The invoice is not paid yet. It becomes paid when Stripe's verified "
    "payment_intent.succeeded event reaches the webhook."
)


def _money(cents: int, currency: str) -> str:
    return f"{cents / 100:.2f} {currency.upper()}"


def _fail(console, e: Exception) -> None:
    """Every refusal names what failed and exits non-zero."""
    if isinstance(e, stripe_api.StripeUnavailable):
        console.print(f"[red]{e.message}[/red]")
    else:
        console.print(f"[red]{e}[/red]")
    raise click.exceptions.Exit(1)


EXPECTED = (ConnectError, stripe_api.StripeUnavailable,
            stripe_api.StripeNotConfigured, stripe_api.LiveKeyRefused)


def register_payments_check(cli_group: click.Group) -> None:
    @cli_group.group("payments")
    def payments_group() -> None:
        """Payments through Stripe (Phase 273)."""

    @payments_group.command("check")
    def check_cmd() -> None:
        """Whether Stripe is set up. Prints no key or secret, nor any part of one."""
        console = get_console()
        st = stripe_api.key_status()
        try:
            import stripe
            sdk = f"stripe {stripe.VERSION}"
        except ImportError:
            sdk = "not installed (motodiag[payments])"
        console.print(f"Provider:        {st.provider}")
        console.print(f"API key:         {'set' if st.api_key_set else 'not set'}")
        mode = ("yes" if st.test_mode else "no") if st.api_key_set else "no key"
        console.print(f"Test mode:       {mode}")
        console.print(f"Webhook secret:  {'set' if st.webhook_secret_set else 'not set'}")
        console.print(f"Tier prices:     {st.prices_set} of 3 set"
                      + (", test placeholders" if st.prices_are_placeholders else ""))
        console.print(f"Library:         {sdk}")
        console.print(f"API version:     {stripe_api.API_VERSION}")
        if st.api_key_set and not st.test_mode:
            console.print("[yellow]The key is not a test-mode key. Outside "
                          "env=prod a live key is refused.[/yellow]")


def register_shop_payments(shop_group: click.Group) -> None:
    @shop_group.group("payments")
    def shop_payments_group() -> None:
        """A shop's Stripe account: its customers pay the shop directly."""

    @shop_payments_group.command("connect")
    @click.option("--shop", "shop_id", type=int, required=True)
    @click.option("--email", default=None,
                  help="The shop owner's email, for Stripe (needed the first time).")
    @click.option("--country", default=None,
                  help="Two letters; defaults from the shop's tax jurisdiction.")
    @click.option("--currency", default=None,
                  help="Three letters; defaults from the shop's tax jurisdiction.")
    def connect_cmd(shop_id: int, email: Optional[str], country: Optional[str],
                    currency: Optional[str]) -> None:
        """Create the shop's Stripe account if needed, and print its onboarding link."""
        console = get_console()
        init_db()
        try:
            acct, created = connect_shop(shop_id, email or "", country=country,
                                         currency=currency)
            url, expires = onboarding_link(shop_id)
        except EXPECTED as e:
            _fail(console, e)
        console.print(
            f"[green]{'Created' if created else 'Using'} Stripe account "
            f"{acct.stripe_account_id} for shop {shop_id}.[/green]"
        )
        console.print("Stripe-hosted onboarding link (one use; give it only to "
                      "the shop's owner, inside the app, never by email or text):")
        console.print(f"    {url}")
        if expires:
            console.print(f"[dim]Expires: {expires}[/dim]")
        console.print("Then run `motodiag shop payments status --shop "
                      f"{shop_id}`.")

    @shop_payments_group.command("status")
    @click.option("--shop", "shop_id", type=int, required=True)
    def status_cmd(shop_id: int) -> None:
        """Read the shop's account from Stripe: can it take card payments?"""
        console = get_console()
        init_db()
        try:
            acct = refresh_status(shop_id)
        except stripe_api.StripeUnavailable as e:
            console.print(f"[red]{e.message}[/red]")
            stored = get_shop_account(shop_id)
            if stored is not None:
                console.print(
                    f"Stored, read {local_display(stored.status_checked_at)}: "
                    f"card payments {stored.card_payments_status or 'unknown'}"
                )
            raise click.exceptions.Exit(1)
        except EXPECTED as e:
            _fail(console, e)
        console.print(f"Shop {shop_id}: Stripe account {acct.stripe_account_id}")
        console.print(f"Card payments: {acct.card_payments_status or 'not reported by Stripe'}")
        if acct.requirements_due is not None:
            console.print(f"Requirements Stripe needs now: {acct.requirements_due}")
        console.print(f"[dim]Read {local_display(acct.status_checked_at)}[/dim]")
        if not acct.can_take_payments:
            raise click.exceptions.Exit(1)

    @shop_group.group("terminal")
    def terminal_group() -> None:
        """Card-present payments through Stripe Terminal."""

    @terminal_group.command("setup")
    @click.option("--shop", "shop_id", type=int, required=True)
    @click.option("--line1", default=None)
    @click.option("--city", default=None)
    @click.option("--state", default=None)
    @click.option("--postal-code", "postal_code", default=None)
    @click.option("--simulated", is_flag=True, required=True,
                  help="Register Stripe's simulated reader (test mode).")
    def terminal_setup_cmd(shop_id, line1, city, state, postal_code, simulated):
        """Create the shop's Terminal location and register the simulated reader."""
        console = get_console()
        init_db()
        address = {"line1": line1, "city": city, "state": state,
                   "postal_code": postal_code}
        try:
            reader = setup_simulated_reader(shop_id, address=address)
        except EXPECTED as e:
            _fail(console, e)
        console.print(f"[green]Simulated reader {reader.stripe_reader_id} "
                      f"({reader.label}) at location {reader.stripe_location_id}.[/green]")

    @terminal_group.command("pay")
    @click.argument("invoice_id", type=int)
    def terminal_pay_cmd(invoice_id: int) -> None:
        """Send an invoice's payment to the shop's reader. With the simulated
        reader in test mode, the test card is presented too."""
        console = get_console()
        init_db()
        try:
            started = start_terminal(invoice_id)
        except EXPECTED as e:
            _fail(console, e)
        console.print(
            f"Invoice {started.invoice_number}: "
            f"{_money(started.amount_cents, started.currency)} sent to the reader "
            f"(Payment Intent {started.payment_intent_id}; reader "
            f"{started.reader_action_status or 'status not reported'})."
        )
        console.print(f"[yellow]{PAID_BY_EVENT}[/yellow]")

    invoice_group = shop_group.commands["invoice"]

    @invoice_group.command("pay-link")
    @click.argument("invoice_id", type=int)
    def pay_link_cmd(invoice_id: int) -> None:
        """A Stripe Checkout link for the customer to pay the invoice online."""
        console = get_console()
        init_db()
        try:
            started = start_checkout(invoice_id)
        except EXPECTED as e:
            _fail(console, e)
        console.print(
            f"Pay invoice {started.invoice_number} "
            f"({_money(started.amount_cents, started.currency)}):"
        )
        console.print(f"    {started.checkout_url}")
        console.print(f"[yellow]{PAID_BY_EVENT}[/yellow]")

    @invoice_group.command("payments")
    @click.argument("invoice_id", type=int)
    def invoice_payments_cmd(invoice_id: int) -> None:
        """Stripe payments started for an invoice, and what each came to."""
        console = get_console()
        init_db()
        rows = payments_for_invoice(invoice_id)
        if not rows:
            console.print(f"No Stripe payment has been started for invoice id={invoice_id}.")
            return
        table = Table(title=f"Stripe payments, invoice id={invoice_id}")
        for col in ("#", "Channel", "Amount", "Status", "Outcome", "Refunded",
                    "Started", "Settled"):
            table.add_column(col)
        for r in rows:
            outcome = r["outcome"] or "—"
            if r["outcome_reason"]:
                outcome += f": {r['outcome_reason']}"
            if r["failure_message"] and r["status"] == "failed":
                outcome = f"failed: {r['failure_message']}"
            table.add_row(
                str(r["id"]), r["channel"], _money(r["amount_cents"], r["currency"]),
                r["status"], outcome,
                _money(r["refunded_cents"], r["currency"]) if r["refunded_cents"] else "—",
                local_display(r["started_at"]) or "—",
                local_display(r["settled_at"]) or "—",
            )
        console.print(table)
