"""`motodiag shop tax`: a shop's tax jurisdiction, its rate and its line rules.

Attached to the ``shop`` group by :func:`register_tax`, which
``register_shop`` calls.
"""

from __future__ import annotations

import json as _json
from typing import Optional

import click
from rich.table import Table

from motodiag.accounting import tax as tax_mod
from motodiag.cli.theme import get_console
from motodiag.core.database import init_db


def _percent_to_fraction(percent: float) -> float:
    if not (0.0 <= percent < 100.0):
        raise click.BadParameter(f"a rate is a percentage from 0 up to 100 (got {percent:g})")
    return round(percent / 100.0, 8)


def _describe(item: tax_mod.TaxItem) -> str:
    basis = "a reading of the source" if item.basis == "reading" else "stated by the source"
    who = "regulation" if item.provenance == "regulation" else "entered by the shop"
    return (f"{item.source_text}; {basis}; {who}; checked {item.checked_on}; "
            f"effective {item.effective_from}")


def register_tax(shop_group: click.Group) -> None:
    @shop_group.group("tax")
    def tax_group() -> None:
        """Sales tax: the shop's jurisdiction, its rate, and what is taxable."""

    @tax_group.group("jurisdiction")
    def jurisdiction_group() -> None:
        """Tax jurisdictions, and which one a shop is in."""

    @jurisdiction_group.command("add")
    @click.option("--code", required=True, help="Country and region, e.g. US-NH, CA-ON, GB.")
    @click.option("--name", required=True)
    @click.option("--currency", required=True, help="The currency its invoices are in.")
    def jurisdiction_add(code: str, name: str, currency: str) -> None:
        """Add a jurisdiction. Its rate and rules are entered by each shop in it."""
        init_db()
        try:
            tax_mod.add_jurisdiction(code, name, currency)
        except tax_mod.TaxRecordError as e:
            raise click.ClickException(str(e)) from e
        get_console().print(f"[green]Added {code.upper()} ({name}), invoiced in "
                            f"{currency.upper()}.[/green]")

    @jurisdiction_group.command("list")
    def jurisdiction_list() -> None:
        """Every jurisdiction on record."""
        init_db()
        console = get_console()
        rows = tax_mod.list_jurisdictions()
        table = Table(title="Tax jurisdictions")
        for col in ("Code", "Name", "Currency"):
            table.add_column(col)
        for r in rows:
            table.add_row(r["code"], r["name"], r["currency"])
        console.print(table)

    @jurisdiction_group.command("set")
    @click.option("--shop", "shop_id", type=int, required=True)
    @click.option("--code", required=True)
    def jurisdiction_set(shop_id: int, code: str) -> None:
        """Set which jurisdiction the shop is in."""
        init_db()
        try:
            jur = tax_mod.set_shop_jurisdiction(shop_id, code)
        except tax_mod.TaxRecordError as e:
            raise click.ClickException(str(e)) from e
        get_console().print(f"[green]Shop {shop_id} is in {jur['code']} ({jur['name']}); "
                            f"its invoices are in {jur['currency']}.[/green]")

    @tax_group.group("rate")
    def rate_group() -> None:
        """The shop's own sales tax rate."""

    @rate_group.command("set")
    @click.option("--shop", "shop_id", type=int, required=True)
    @click.option("--rate", "percent", type=float, required=True,
                  help="The combined rate as a percentage, e.g. 6.25.")
    @click.option("--effective", required=True, help="The date it takes effect (YYYY-MM-DD).")
    @click.option("--valid-until", required=True,
                  help="The date it must be re-checked by (YYYY-MM-DD).")
    @click.option("--source-title", required=True, help="Where the rate comes from.")
    @click.option("--source-url", default=None)
    @click.option("--checked-on", required=True, help="When you read the source (YYYY-MM-DD).")
    def rate_set(shop_id: int, percent: float, effective: str, valid_until: str,
                 source_title: str, source_url: Optional[str], checked_on: str) -> None:
        """Record the shop's own rate, with its source and validity."""
        init_db()
        fraction = _percent_to_fraction(percent)
        try:
            tax_mod.set_shop_rate(shop_id, fraction, effective, valid_until, source_title,
                                  checked_on, source_url)
        except tax_mod.TaxRecordError as e:
            raise click.ClickException(str(e)) from e
        get_console().print(f"[green]Shop {shop_id}: {percent:g}% (stored as {fraction:g}), "
                            f"effective {effective}, valid until {valid_until}.[/green]")

    @tax_group.group("rule")
    def rule_group() -> None:
        """Whether a kind of invoice line is taxable, for the shop."""

    @rule_group.command("set")
    @click.option("--shop", "shop_id", type=int, required=True)
    @click.option("--line-type", required=True, type=click.Choice(tax_mod.LINE_TYPES),
                  help="labor, parts, diagnostic, or misc (shop supplies).")
    @click.option("--taxable/--not-taxable", required=True)
    @click.option("--effective", required=True)
    @click.option("--valid-until", required=True)
    @click.option("--source-title", required=True)
    @click.option("--source-url", default=None)
    @click.option("--clause", default=None, help="The section or clause relied on.")
    @click.option("--checked-on", required=True)
    @click.option("--reading", is_flag=True, default=False,
                  help="The source does not state this; it is your reading of it.")
    def rule_set(shop_id: int, line_type: str, taxable: bool, effective: str,
                 valid_until: str, source_title: str, source_url: Optional[str],
                 clause: Optional[str], checked_on: str, reading: bool) -> None:
        """Record whether a line type is taxable, with its source and validity."""
        init_db()
        try:
            tax_mod.set_shop_rule(shop_id, line_type, taxable, effective, valid_until,
                                  source_title, checked_on, source_url, clause,
                                  "reading" if reading else "stated")
        except tax_mod.TaxRecordError as e:
            raise click.ClickException(str(e)) from e
        verdict = "taxable" if taxable else "not taxable"
        get_console().print(f"[green]Shop {shop_id}: {tax_mod.LINE_LABELS[line_type]} "
                            f"{verdict}, valid until {valid_until}.[/green]")

    @tax_group.group("warranty-rule")
    def warranty_rule_group() -> None:
        """Whether the tax on covered warranty work goes on the claim, by who owes it."""

    @warranty_rule_group.command("set")
    @click.option("--shop", "shop_id", type=int, required=True)
    @click.option("--payer", required=True, type=click.Choice(tax_mod.PAYERS),
                  help="maker_with_bike, other (someone else's plan or contract), "
                       "or shop_contract (a contract this shop sold).")
    @click.option("--on-claim/--not-on-claim", "taxed_on_claim", required=True,
                  help="Whether covered work is taxed and the tax added to the claim.")
    @click.option("--effective", required=True)
    @click.option("--valid-until", required=True)
    @click.option("--source-title", required=True)
    @click.option("--source-url", default=None)
    @click.option("--clause", default=None, help="The section or clause relied on.")
    @click.option("--checked-on", required=True)
    @click.option("--reading", is_flag=True, default=False,
                  help="The source does not state this; it is your reading of it.")
    def warranty_rule_set(shop_id: int, payer: str, taxed_on_claim: bool, effective: str,
                          valid_until: str, source_title: str, source_url: Optional[str],
                          clause: Optional[str], checked_on: str, reading: bool) -> None:
        """Record whether covered warranty work's tax goes on the claim."""
        init_db()
        try:
            tax_mod.set_shop_warranty_rule(shop_id, payer, taxed_on_claim, effective,
                                           valid_until, source_title, checked_on,
                                           source_url, clause,
                                           "reading" if reading else "stated")
        except tax_mod.TaxRecordError as e:
            raise click.ClickException(str(e)) from e
        verdict = "taxed on the claim" if taxed_on_claim else "not taxed on the claim"
        get_console().print(f"[green]Shop {shop_id}: work owed by "
                            f"{tax_mod.PAYER_LABELS[payer]} is {verdict}, valid until "
                            f"{valid_until}.[/green]")

    @tax_group.group("settlement-rule")
    def settlement_rule_group() -> None:
        """The tax charged on a warranty claim whose shortfall the shop absorbs."""

    @settlement_rule_group.command("set")
    @click.option("--shop", "shop_id", type=int, required=True)
    @click.option("--effective", required=True)
    @click.option("--valid-until", required=True)
    @click.option("--source-title", required=True)
    @click.option("--source-url", default=None)
    @click.option("--clause", default=None, help="The section or clause relied on.")
    @click.option("--checked-on", required=True)
    @click.option("--reading", is_flag=True, default=False,
                  help="The source does not state this; it is your reading of it.")
    def settlement_rule_set(shop_id: int, effective: str, valid_until: str,
                            source_title: str, source_url: Optional[str],
                            clause: Optional[str], checked_on: str, reading: bool) -> None:
        """Record that the tax charged on a claim stays owed when the shop absorbs
        its shortfall, from your jurisdiction's source."""
        init_db()
        try:
            tax_mod.set_shop_settlement_rule(shop_id, effective, valid_until, source_title,
                                             checked_on, source_url, clause,
                                             "reading" if reading else "stated")
        except tax_mod.TaxRecordError as e:
            raise click.ClickException(str(e)) from e
        get_console().print(f"[green]Shop {shop_id}: the tax charged on a claim stays "
                            f"owed when the shop absorbs its shortfall, valid until "
                            f"{valid_until}.[/green]")

    @tax_group.command("confirm")
    @click.option("--jurisdiction", "code", required=True)
    @click.option("--checked-on", required=True, help="When the regulator's pages were read.")
    @click.option("--source-url", required=True, help="The page that was read.")
    def confirm(code: str, checked_on: str, source_url: str) -> None:
        """Record a new check of a regulation rate against the regulator's pages."""
        init_db()
        try:
            res = tax_mod.confirm_regulation(code, checked_on, source_url)
        except tax_mod.TaxRecordError as e:
            raise click.ClickException(str(e)) from e
        get_console().print(
            f"[green]{res['code']}: rate, {res['rules']} rules and "
            f"{res['warranty_rules']} warranty rules and {res['settlement_rules']} "
            f"settlement rule(s) checked on "
            f"{res['checked_on']}; must be re-checked by {res['valid_until']}.[/green]"
        )

    @tax_group.command("status")
    @click.option("--shop", "shop_id", type=int, required=True)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def status(shop_id: int, as_json: bool) -> None:
        """What is on record for the shop today; fails when anything is past its validity."""
        init_db()
        console = get_console()
        st = tax_mod.tax_status(shop_id, tax_mod.today())
        if as_json:
            click.echo(_json.dumps({
                "shop_id": shop_id, "ok": st.ok, "jurisdiction": st.jurisdiction,
                "recheck_by": st.recheck_by,
                "rate": st.rate.__dict__ if st.rate else None,
                "rules": {k: v.__dict__ for k, v in st.rules.items()},
                "failures": st.failures, "not_on_record": st.not_on_record,
                "warranty_rules": {k: v.__dict__ for k, v in st.warranty_rules.items()},
                "warranty_not_on_record": st.warranty_not_on_record,
                "settlement_rule": st.settlement_rule.__dict__ if st.settlement_rule
                else None,
            }, indent=2, default=str))
        else:
            if st.jurisdiction:
                jur = st.jurisdiction
                console.print(f"Shop {shop_id}: {jur['code']} ({jur['name']}), "
                              f"invoices in {jur['currency']}")
            if st.rate:
                console.print(f"Rate: {st.rate.value * 100:g}%, must be re-checked by "
                              f"{st.rate.valid_until}. {_describe(st.rate)}")
            for line_type in tax_mod.LINE_TYPES:
                label = tax_mod.LINE_LABELS[line_type]
                if line_type in st.rules:
                    rule = st.rules[line_type]
                    verdict = "taxable" if rule.value else "not taxable"
                    console.print(f"{label.capitalize()}: {verdict}, must be re-checked by "
                                  f"{rule.valid_until}. {_describe(rule)}")
                elif line_type in st.not_on_record:
                    console.print(f"{label.capitalize()}: no rule on record; an invoice "
                                  f"with a {label} line is refused until one is recorded.")
            for payer in tax_mod.PAYERS:
                label = tax_mod.PAYER_LABELS[payer]
                if payer in st.warranty_rules:
                    rule = st.warranty_rules[payer]
                    verdict = "taxed on the claim" if rule.value else "not taxed on the claim"
                    console.print(f"Warranty work owed by {label}: {verdict}, must be "
                                  f"re-checked by {rule.valid_until}. {_describe(rule)}")
                elif payer in st.warranty_not_on_record:
                    console.print(f"Warranty work owed by {label}: no rule on record; an "
                                  f"invoice with such a claim is refused until one is "
                                  f"recorded.")
            if st.settlement_rule:
                console.print(f"A warranty shortfall the shop absorbs: the tax charged on "
                              f"the claim stays owed, must be re-checked by "
                              f"{st.settlement_rule.valid_until}. "
                              f"{_describe(st.settlement_rule)}")
            elif st.settlement_not_on_record:
                console.print("A warranty shortfall the shop absorbs: no rule on record; "
                              "exporting one whose claim carried tax is refused until one "
                              "is recorded.")
            for failure in st.failures:
                console.print(f"[red]FAILS: {failure}[/red]")
        if not st.ok:
            raise click.exceptions.Exit(1)
