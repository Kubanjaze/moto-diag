"""The shop's money: labour rate, recorded costs, expenses and the reports.

- ``shop labor-rate``: the hourly rate charged to customers, which the
  invoice and the estimate both take through one lookup.
- ``shop member cost-rate``: what an hour of a member's time costs the shop.
  Pay data: shown here and nowhere else.
- ``shop parts-needs cost``: what the shop paid for a work order's part line.
- ``shop expense``: overheads per month.
- ``shop analytics pnl`` and ``shop analytics variance``.
"""

from __future__ import annotations

import json as _json
from datetime import date
from typing import Optional

import click
from rich.table import Table

from motodiag.cli.theme import get_console
from motodiag.core.database import init_db
from motodiag.pricing import labor_rates
from motodiag.shop import analytics, shop_costs

_DATE = click.DateTime(formats=["%Y-%m-%d"])


def _money(cents: Optional[int]) -> str:
    return "not recorded" if cents is None else f"${cents / 100:,.2f}"


def _pct(value: Optional[float]) -> str:
    return "—" if value is None else f"{value * 100:+.1f}%"


def _or_dash(value) -> str:
    return "—" if value is None else str(value)


def register_finance(shop_group: click.Group) -> None:
    from motodiag.cli.shop import _resolve_shop_identifier

    def _shop_id(identifier: Optional[str]) -> int:
        shop = _resolve_shop_identifier(identifier)
        assert shop is not None
        return int(shop["id"])

    # ------------------------------------------------------------ labour rate
    @shop_group.group("labor-rate")
    def labor_rate_group() -> None:
        """The hourly labour rate charged to customers."""

    @labor_rate_group.command("set")
    @click.option("--hourly-cents", type=click.IntRange(min=1), required=True)
    @click.option("--state", default=None,
                  help="Two-letter state the rate applies in; a shop in that "
                       "state uses it first. Omit for a rate used anywhere.")
    @click.option("--from", "effective", type=_DATE, default=None,
                  help="YYYY-MM-DD it takes effect. Default: today.")
    @click.option("--source", default=None, help="Where the figure comes from.")
    def labor_rate_set(hourly_cents: int, state: Optional[str], effective,
                       source: Optional[str]) -> None:
        """Record the labour rate estimates and invoices charge."""
        init_db()
        when = effective.date().isoformat() if effective else date.today().isoformat()
        state = state.upper() if state else None
        labor_rates.add_labor_rate(
            region=state or "national", rate_type="independent",
            hourly_rate=hourly_cents / 100, state=state, source=source,
            effective_date=when,
        )
        where = f" in {state}" if state else ""
        get_console().print(f"[green]Labour rate {_money(hourly_cents)}/h from "
                            f"{when}{where}.[/green]")

    @labor_rate_group.command("list")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def labor_rate_list(as_json: bool) -> None:
        """Recorded labour rates."""
        console = get_console()
        init_db()
        rows = labor_rates.list_all_rates()
        if as_json:
            click.echo(_json.dumps(rows, default=str, indent=2))
            return
        if not rows:
            console.print("[dim]No labour rate recorded. Set one with "
                          "`motodiag shop labor-rate set --hourly-cents N`.[/dim]")
            return
        table = Table(title="Labour rates")
        for col in ("State", "Hourly", "From", "Source"):
            table.add_column(col)
        for r in rows:
            table.add_row(r.get("state") or "any",
                          _money(int(round(float(r["hourly_rate"]) * 100))),
                          _or_dash(r.get("effective_date")), _or_dash(r.get("source")))
        console.print(table)

    # ------------------------------------------------------------ cost rates
    member_group = shop_group.commands["member"]

    @member_group.command("cost-rate")
    @click.option("--shop", "shop_identifier", default=None)
    @click.option("--user", "user_id", type=int, required=True)
    @click.option("--cents-per-hour", type=click.IntRange(min=0), required=True,
                  help="What an hour of this member's time costs the shop.")
    @click.option("--from", "effective", type=_DATE, required=True, help="YYYY-MM-DD")
    def member_cost_rate(shop_identifier, user_id, cents_per_hour, effective) -> None:
        """Record a member's cost rate (pay data: shown only here)."""
        init_db()
        when = effective.date().isoformat()
        try:
            shop_costs.set_mechanic_cost_rate(
                _shop_id(shop_identifier), user_id, cents_per_hour, when,
            )
        except ValueError as e:
            raise click.ClickException(str(e)) from e
        get_console().print(f"[green]Cost rate for user {user_id}: "
                            f"{_money(cents_per_hour)}/h from {when}.[/green]")

    @member_group.command("cost-rates")
    @click.option("--shop", "shop_identifier", default=None)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def member_cost_rates(shop_identifier, as_json) -> None:
        """Members' cost rates (pay data)."""
        console = get_console()
        init_db()
        rows = shop_costs.list_mechanic_cost_rates(_shop_id(shop_identifier))
        if as_json:
            click.echo(_json.dumps(rows, default=str, indent=2))
            return
        if not rows:
            console.print("[dim]No cost rates recorded.[/dim]")
            return
        table = Table(title="Cost rates")
        for col in ("User", "Username", "Per hour", "From"):
            table.add_column(col)
        for r in rows:
            table.add_row(str(r["user_id"]), r["username"],
                          _money(r["cost_cents_per_hour"]), r["effective_from"])
        console.print(table)

    # ------------------------------------------------------------ part cost
    parts_group = shop_group.commands["parts-needs"]

    @parts_group.command("cost")
    @click.argument("line_id", type=int)
    @click.option("--cents-each", type=click.IntRange(min=0), required=True,
                  help="What the shop paid per unit.")
    def parts_cost(line_id: int, cents_each: int) -> None:
        """Record what the shop paid for a work order's part line."""
        init_db()
        try:
            shop_costs.set_part_purchase_cost(line_id, cents_each)
        except ValueError as e:
            raise click.ClickException(str(e)) from e
        get_console().print(f"[green]Part line {line_id}: purchase cost "
                            f"{_money(cents_each)} each.[/green]")

    # ------------------------------------------------------------ expenses
    @shop_group.group("expense")
    def expense_group() -> None:
        """The shop's overheads, by month."""

    @expense_group.command("add")
    @click.option("--shop", "shop_identifier", default=None)
    @click.option("--month", required=True, help="YYYY-MM")
    @click.option("--category", required=True, help="e.g. rent, utilities, tools.")
    @click.option("--cents", "amount_cents", type=click.IntRange(min=0), required=True)
    @click.option("--description", default=None)
    def expense_add(shop_identifier, month, category, amount_cents, description) -> None:
        """Record an expense for a month."""
        init_db()
        try:
            expense_id = shop_costs.add_expense(
                _shop_id(shop_identifier), month, category, amount_cents,
                description=description,
            )
        except ValueError as e:
            raise click.ClickException(str(e)) from e
        get_console().print(f"[green]Expense #{expense_id}: {category} "
                            f"{_money(amount_cents)} for {month}.[/green]")

    @expense_group.command("list")
    @click.option("--shop", "shop_identifier", default=None)
    @click.option("--month", default=None, help="YYYY-MM")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def expense_list(shop_identifier, month, as_json) -> None:
        """List expenses."""
        console = get_console()
        init_db()
        rows = shop_costs.list_expenses(_shop_id(shop_identifier),
                                        months=[month] if month else None)
        if as_json:
            click.echo(_json.dumps(rows, default=str, indent=2))
            return
        if not rows:
            console.print("[dim]No expenses recorded.[/dim]")
            return
        table = Table(title="Expenses")
        for col in ("ID", "Month", "Category", "Amount", "Description"):
            table.add_column(col)
        for r in rows:
            table.add_row(str(r["id"]), r["month"], r["category"],
                          _money(r["amount_cents"]), r.get("description") or "")
        console.print(table)

    # ------------------------------------------------------------ reports
    analytics_group = shop_group.commands["analytics"]

    @analytics_group.command("pnl")
    @click.option("--shop", "shop_identifier", default=None)
    @click.option("--by", type=click.Choice(analytics.PNL_DIMENSIONS), default="shop")
    @click.option("--period", type=click.Choice(analytics.PNL_PERIODS), default="month")
    @click.option("--for", "period_key", default=None,
                  help="2026-09, 2026-Q3 or 2026. Default: the current one.")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def analytics_pnl(shop_identifier, by, period, period_key, as_json) -> None:
        """Profit and loss on recorded costs, by mechanic, bay, customer or shop."""
        console = get_console()
        init_db()
        try:
            report = analytics.financial_report(
                _shop_id(shop_identifier), by=by, period=period, period_key=period_key,
            )
        except ValueError as e:
            raise click.ClickException(str(e)) from e
        if as_json:
            click.echo(_json.dumps(report.model_dump(), default=str, indent=2))
            return
        console.print(f"[bold]P&L by {by}, {period} {report.period_key}[/bold] "
                      f"({report.start} to before {report.end})")
        console.print(f"Attribution: {report.attribution_rule}")
        for rule in report.cost_rules:
            console.print(f"  {rule}")
        if not report.groups:
            console.print("[dim]No invoices issued in this period.[/dim]")
        else:
            table = Table()
            for col in ("Group", "WOs", "Labour rev", "Parts rev", "Other rev",
                        "Revenue", "Parts cost", "Labour cost", "Hours",
                        "Gross margin"):
                table.add_column(col)
            for g in report.groups:
                other = sum(v for t, v in g.revenue_cents.items()
                            if t not in ("labor", "parts"))
                parts_cost = (_money(g.parts_cost_cents) if g.parts_cost_cents is not None
                              else f"not recorded ({g.parts_cost_missing} WO)")
                labour_cost = (_money(g.labour_cost_cents)
                               if g.labour_cost_cents is not None
                               else f"not recorded ({g.labour_cost_missing} WO)")
                margin = (_money(g.gross_margin_cents)
                          if g.gross_margin_cents is not None else "not computed")
                table.add_row(g.key, f"{g.work_orders:g}",
                              _money(g.revenue_cents.get("labor", 0)),
                              _money(g.revenue_cents.get("parts", 0)), _money(other),
                              _money(g.revenue_total_cents), parts_cost, labour_cost,
                              f"{g.labour_hours:.2f}", margin)
            console.print(table)
        if by == "shop":
            console.print(f"Expenses: {_money(report.expenses_cents)}")
            if report.expense_months_missing:
                console.print("[yellow]Net not computed: no expenses recorded for "
                              f"{', '.join(report.expense_months_missing)}.[/yellow]")
            elif report.net_cents is None:
                console.print("[yellow]Net not computed: the gross margin is "
                              "not.[/yellow]")
            else:
                console.print(f"[bold]Net: {_money(report.net_cents)}[/bold]")

    @analytics_group.command("variance")
    @click.option("--shop", "shop_identifier", default=None)
    @click.option("--since", default="30d", help="30d, 12h or an ISO date.")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def analytics_variance(shop_identifier, since, as_json) -> None:
        """Estimate against actual: labour hours, parts cost and the quote."""
        console = get_console()
        init_db()
        try:
            report = analytics.estimate_variance(_shop_id(shop_identifier), since=since)
        except ValueError as e:
            raise click.ClickException(str(e)) from e
        if as_json:
            click.echo(_json.dumps(report.model_dump(), default=str, indent=2))
            return
        if not report.rows:
            console.print("[dim]No completed work orders in the window.[/dim]")
            return
        table = Table(title=f"Estimate vs actual, completed since {since}")
        for col in ("WO", "Title", "Hours est/act", "Labour", "Parts est/act",
                    "Parts", "Quote/invoice", "Quote"):
            table.add_column(col)
        for r in report.rows:
            est_parts = ("—" if r.estimated_parts_cents is None
                         else _money(r.estimated_parts_cents))
            quote = "—" if r.quote_total_cents is None else _money(r.quote_total_cents)
            invoice = ("—" if r.invoice_subtotal_cents is None
                       else _money(r.invoice_subtotal_cents))
            table.add_row(
                str(r.work_order_id), r.title,
                f"{_or_dash(r.estimated_hours)} / {_or_dash(r.actual_hours)}",
                r.labour_note or _pct(r.labour_delta_pct),
                f"{est_parts} / {_money(r.actual_parts_cents)}",
                r.parts_note or _pct(r.parts_delta_pct),
                f"{quote} / {invoice}", r.quote_note or _pct(r.quote_delta_pct),
            )
        console.print(table)
        console.print(
            f"Scored: labour {report.labour_scored}, parts {report.parts_scored}, "
            f"quotes {report.quotes_scored}. Median: labour "
            f"{_pct(report.labour_median_delta_pct)}, parts "
            f"{_pct(report.parts_median_delta_pct)}, quote "
            f"{_pct(report.quote_median_delta_pct)}."
        )
