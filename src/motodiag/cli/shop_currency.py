"""`motodiag shop currency`: exchange rates and conversion.

Attached to the ``shop`` group by :func:`register_currency`, which
``register_shop`` calls.
"""

from __future__ import annotations

import json as _json
from typing import Optional

import click
from rich.table import Table

from motodiag.accounting import exchange
from motodiag.accounting import tax as tax_mod
from motodiag.cli.theme import get_console
from motodiag.core.database import init_db
from motodiag.core.outbound import ServiceUnavailable


def _rates_table(rows: list[dict], title: str) -> Table:
    table = Table(title=title)
    for col in ("From", "To", "Rate", "Rate date", "Valid until", "Source"):
        table.add_column(col)
    for r in rows:
        source = "ECB" if r["source"] == "ecb" else f"shop {r['shop_id']}: {r['source_note']}"
        table.add_row(r["base"], r["quote"], str(r["rate"]), r["rate_date"],
                      r["valid_until"], source)
    return table


def register_currency(shop_group: click.Group) -> None:
    @shop_group.group("currency")
    def currency_group() -> None:
        """Exchange rates: the ECB's reference rates, and the shop's own."""

    @currency_group.command("refresh")
    def refresh() -> None:
        """Fetch today's ECB reference rates."""
        init_db()
        console = get_console()
        try:
            res = exchange.refresh_ecb()
        except ServiceUnavailable as e:
            console.print(f"[red]{e.message}[/red]")
            stored = exchange.list_rates()
            if stored:
                console.print(f"Stored ECB rates, newest dated {stored[0]['rate_date']}, "
                              f"valid until {stored[0]['valid_until']}:")
                console.print(_rates_table(stored[:40], "Stored exchange rates"))
            else:
                console.print("No ECB rates are stored.")
            raise click.exceptions.Exit(1)
        console.print(
            f"[green]ECB reference rates for {res['rate_date']}: {res['currencies']} "
            f"currencies ({res['added']} new), usable until {res['valid_until']}.[/green]"
        )
        console.print(f"[dim]{exchange.ECB_CAVEAT} They are not used on invoices.[/dim]")

    @currency_group.command("rates")
    @click.option("--shop", "shop_id", type=int, default=None,
                  help="Also list this shop's own rates.")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def rates(shop_id: Optional[int], as_json: bool) -> None:
        """The stored rates, with their dates and validity."""
        init_db()
        rows = exchange.list_rates(shop_id=shop_id)
        if as_json:
            click.echo(_json.dumps(rows, indent=2, default=str))
            return
        if not rows:
            get_console().print("No exchange rates are stored. Fetch the ECB's with "
                                "`motodiag shop currency refresh`.")
            return
        get_console().print(_rates_table(rows, "Stored exchange rates"))

    @currency_group.command("set")
    @click.option("--shop", "shop_id", type=int, required=True)
    @click.option("--from", "from_currency", required=True)
    @click.option("--to", "to_currency", required=True)
    @click.option("--rate", required=True, help="1 FROM = RATE TO.")
    @click.option("--rate-date", required=True)
    @click.option("--valid-until", required=True)
    @click.option("--source", "source_note", required=True,
                  help="Who quoted it, e.g. the shop's bank.")
    def set_rate(shop_id: int, from_currency: str, to_currency: str, rate: str,
                 rate_date: str, valid_until: str, source_note: str) -> None:
        """Record the shop's own rate. Only these convert an invoice."""
        init_db()
        try:
            exchange.set_shop_rate(shop_id, from_currency, to_currency, rate, rate_date,
                                   valid_until, source_note)
        except exchange.ExchangeRateError as e:
            raise click.ClickException(str(e)) from e
        get_console().print(
            f"[green]Shop {shop_id}: 1 {from_currency.upper()} = {rate} "
            f"{to_currency.upper()}, dated {rate_date}, valid until {valid_until} "
            f"({source_note}).[/green]"
        )

    @currency_group.command("convert")
    @click.argument("amount")
    @click.argument("from_currency")
    @click.argument("to_currency")
    @click.option("--shop", "shop_id", type=int, default=None,
                  help="Use this shop's own rate when it has one.")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def convert(amount: str, from_currency: str, to_currency: str,
                shop_id: Optional[int], as_json: bool) -> None:
        """Convert an amount, showing the rate, its date and its source."""
        init_db()
        try:
            conv = exchange.convert(amount, from_currency, to_currency, tax_mod.today(),
                                    shop_id)
        except exchange.ExchangeRateError as e:
            raise click.ClickException(str(e)) from e
        if as_json:
            click.echo(_json.dumps({k: str(v) for k, v in conv.__dict__.items()}, indent=2))
            return
        console = get_console()
        console.print(f"{conv.amount} {conv.from_currency} = {conv.result} {conv.to_currency}")
        how = {"direct": "", "inverse": " (the inverse of the euro rate)",
               "cross": " (a cross rate through the euro, from two ECB rates)",
               "same": ""}[conv.method]
        if conv.source == "same":
            return
        source = "ECB" if conv.is_ecb else f"the shop's own rate ({conv.source_note})"
        console.print(f"Rate {conv.rate:.6f}{how}, dated {conv.rate_date}, valid until "
                      f"{conv.valid_until}; source: {source}.")
        if conv.is_ecb:
            console.print(f"[dim]{exchange.ECB_CAVEAT}[/dim]")
