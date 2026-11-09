"""CLI for payments through Stripe (Phase 273).

- ``motodiag payments check``: whether Stripe is set up, never a value.
- ``motodiag shop payments connect|status``: a shop's connected account.
- ``motodiag shop terminal setup|pay``: the simulated reader.
- ``motodiag shop invoice pay-link|payments``: an invoice paid online.
- ``motodiag payments feed run|status`` (Phase 371): the server asks
  Stripe for its news, and whether it is doing so.

No command marks an invoice paid: Stripe's event does, when it reaches
the webhook (``/v1/billing/webhooks/stripe``) or the feed.
"""

from __future__ import annotations

import time
from typing import Optional

import click
from rich.table import Table

from motodiag.cli.theme import get_console
from motodiag.core.config import get_settings
from motodiag.core.database import init_db
from motodiag.core.timestamps import local_display, stored_instant, utc_at
from motodiag.payments import event_feed, stripe_api
from motodiag.payments.connect import (
    ConnectError,
    connect_shop,
    get_shop_account,
    onboarding_link,
    refresh_status,
)
from motodiag.payments.invoice_payments import (
    payments_for_invoice,
    start_checkout,
    start_terminal,
)
from motodiag.payments.terminal import setup_simulated_reader
from motodiag.telemetry.sender import make_sender

PAID_BY_EVENT = (
    "The invoice is not paid yet. It becomes paid when Stripe's verified "
    "payment_intent.succeeded event reaches the webhook or the feed."
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

    register_feed(payments_group)


# ---------------------------------------------------------------------------
# Phase 371: the feed. Neither command opens the database through init_db,
# so no migration ever runs through them (migrations reach live by deploy.py).
# ---------------------------------------------------------------------------


def _alarm_line(settings) -> str:
    dsn = event_feed.alarm_dsn(settings)
    if dsn is None:
        return "Alarm: off: no Sentry DSN"
    return (f"Alarm: checks in to {dsn} every "
            f"{settings.stripe_poll_checkin_s // 60} minutes")


def _configured_or_exit(console, settings) -> None:
    """Exit 2, with the gateway's own message, when Stripe cannot be used."""
    try:
        stripe_api.client(settings)
    except (stripe_api.StripeNotConfigured, stripe_api.LiveKeyRefused) as e:
        console.print(f"[red]{e}[/red]")
        raise click.exceptions.Exit(2)


def _round_line(r: event_feed.RoundResult) -> str:
    line = (f"{r.account}: {r.seen} seen, {r.handled} handled, "
            f"largest lag {r.lag_s:.0f} s")
    return line + (f"; error: {r.error}" if r.error else "")


def _stale(row: dict, now: float, interval_s: int) -> bool:
    asked = stored_instant(row["polled_at"]).timestamp()
    return now - asked > 2 * interval_s


def _status_problems(settings, db_path: str, rows: list[dict], now: float) -> list[str]:
    by_account = {r["account"]: r for r in rows}
    problems = []
    for account in event_feed.accounts(settings, db_path):
        row = by_account.get(account)
        if row is None:
            problems.append(f"{account} has never been asked")
        elif _stale(row, now, settings.stripe_poll_interval_s):
            problems.append(f"{account} was not asked within two intervals")
        elif row["last_error"]:
            problems.append(f"{account}'s last round ended in an error")
    return problems


def register_feed(payments_group: click.Group) -> None:
    @payments_group.group("feed")
    def feed_group() -> None:
        """The server asks Stripe for its news (Phase 371)."""

    @feed_group.command("run")
    @click.option("--once", is_flag=True,
                  help="One round, one line per account, then exit.")
    def feed_run_cmd(once: bool) -> None:
        """Ask Stripe for new events every interval and hand each to the handler."""
        console = get_console()
        settings = get_settings()
        _configured_or_exit(console, settings)
        console.print(_alarm_line(settings))
        if not once:
            event_feed.run_forever(settings, settings.db_path, clock=time.time,
                                   sleep=time.sleep, stop=lambda: False,
                                   sender=make_sender(settings))
            return
        results = event_feed.poll_once(settings, settings.db_path, time.time)
        for r in results:
            click.echo(_round_line(r))
        if any(r.error for r in results):
            raise click.exceptions.Exit(1)

    @feed_group.command("status")
    def feed_status_cmd() -> None:
        """When each account was last asked, the notices sent, and the alarm."""
        console = get_console()
        settings = get_settings()
        _configured_or_exit(console, settings)
        now = time.time()
        rows = event_feed.cursor_rows(settings.db_path)
        for row in rows:
            ago = now - stored_instant(row["polled_at"]).timestamp()
            click.echo(
                f"{row['account']}: last asked {local_display(row['polled_at'])} "
                f"({ago:.0f} s ago); newest event "
                f"{local_display(utc_at(row['last_created']))}; "
                f"last error: {row['last_error'] or 'none'}")
        notices = event_feed.notices_since(settings.db_path,
                                           utc_at(now - 30 * 86400))
        click.echo(f"Notices in the last 30 days: {len(notices)}")
        for n in notices:
            click.echo(f"  {local_display(n['sent_at'])}: {n['detail']}")
        click.echo(_alarm_line(settings))
        problems = _status_problems(settings, settings.db_path, rows, now)
        for p in problems:
            click.echo(f"Not right: {p}")
        if problems:
            raise click.exceptions.Exit(1)


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
        click.echo(url)  # never through rich: it wraps long URLs (bug fix #1)
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
        click.echo(started.checkout_url)  # never through rich (bug fix #1)
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
