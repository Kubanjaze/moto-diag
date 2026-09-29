"""`motodiag shop customer` additions: the communication log and bike ownership.

Attached to the existing ``customer`` group by :func:`register_crm`, which
``register_shop`` calls once the group exists.
"""

from __future__ import annotations

import json as _json
from typing import Optional

import click
from rich.table import Table

from motodiag.cli.theme import get_console
from motodiag.core.database import init_db
from motodiag.crm import communication_repo, customer_bikes_repo
from motodiag.crm.models import CustomerRelationship


def register_crm(customer_group: click.Group) -> None:
    from motodiag.cli.shop import (
        _resolve_bike_slug_or_id,
        _resolve_customer_identifier,
    )

    @customer_group.command("log-contact")
    @click.argument("customer_identifier")
    @click.option("--channel", required=True,
                  type=click.Choice(communication_repo.CHANNELS))
    @click.option("--direction", required=True,
                  type=click.Choice(communication_repo.DIRECTIONS),
                  help="inbound: the customer contacted the shop; "
                       "outbound: the shop contacted the customer.")
    @click.option("--summary", required=True, help="What was said or agreed.")
    @click.option("--wo", "work_order_id", type=int, default=None,
                  help="Work order the contact was about.")
    @click.option("--at", "occurred_at", default=None,
                  help="When it happened (ISO date or date-time). Default: now.")
    @click.option("--by", "logged_by_user_id", type=int, default=None,
                  help="User id of the person who logged it.")
    def customer_log_contact(
        customer_identifier: str, channel: str, direction: str, summary: str,
        work_order_id: Optional[int], occurred_at: Optional[str],
        logged_by_user_id: Optional[int],
    ) -> None:
        """Record a phone call, visit, email or text with a customer."""
        console = get_console()
        init_db()
        customer = _resolve_customer_identifier(customer_identifier)
        try:
            contact_id = communication_repo.log_contact(
                customer["id"], direction, channel, summary,
                shop_id=customer.get("shop_id"),
                work_order_id=work_order_id,
                logged_by_user_id=logged_by_user_id,
                occurred_at=occurred_at,
            )
        except ValueError as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[green]Logged contact #{contact_id} with {customer['name']} "
            f"({direction}, {channel}).[/green]"
        )

    @customer_group.command("history")
    @click.argument("customer_identifier")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def customer_history(customer_identifier: str, as_json: bool) -> None:
        """A customer's contacts and notifications, newest first."""
        console = get_console()
        init_db()
        customer = _resolve_customer_identifier(customer_identifier)
        entries = communication_repo.customer_timeline(customer["id"])
        if as_json:
            click.echo(_json.dumps(entries, default=str, indent=2))
            return
        if not entries:
            console.print(f"[dim]Nothing logged for {customer['name']} yet.[/dim]")
            return
        table = Table(title=f"History for {customer['name']}", show_lines=False)
        table.add_column("When")
        table.add_column("Source")
        table.add_column("Way")
        table.add_column("Channel")
        table.add_column("WO", justify="right")
        table.add_column("What")
        for e in entries:
            source = e["source"]
            if source == "notification":
                source = f"notification ({e['event']}, {e['status']})"
            table.add_row(
                str(e["at"]), source, e["direction"], e["channel"],
                str(e["work_order_id"] or "—"), e["text"] or "",
            )
        console.print(table)

    @customer_group.command("transfer-bike")
    @click.option("--bike", "bike_identifier", required=True)
    @click.option("--from", "from_identifier", required=True,
                  help="The bike's current owner.")
    @click.option("--to", "to_identifier", required=True,
                  help="The new owner.")
    @click.option("--notes", default=None)
    def customer_transfer_bike(
        bike_identifier: str, from_identifier: str, to_identifier: str,
        notes: Optional[str],
    ) -> None:
        """Move a bike to a new owner; the old owner becomes a previous owner."""
        console = get_console()
        init_db()
        bike = _resolve_bike_slug_or_id(bike_identifier)
        old = _resolve_customer_identifier(from_identifier)
        new = _resolve_customer_identifier(to_identifier)
        if old["id"] == new["id"]:
            raise click.ClickException("The bike already belongs to that customer.")
        owners = customer_bikes_repo.list_customers_for_bike(
            bike["id"], relationship=CustomerRelationship.OWNER,
        )
        if old["id"] not in {o["id"] for o in owners}:
            raise click.ClickException(
                f"{old['name']} is not the recorded owner of bike id={bike['id']}. "
                f"Run `motodiag shop customer bike-owners {bike['id']}` to see who is."
            )
        customer_bikes_repo.transfer_ownership(
            bike["id"], old["id"], new["id"], notes=notes,
        )
        console.print(
            f"[green]Bike id={bike['id']} now belongs to {new['name']}; "
            f"{old['name']} is recorded as a previous owner.[/green]"
        )

    @customer_group.command("bike-owners")
    @click.argument("bike_identifier")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def customer_bike_owners(bike_identifier: str, as_json: bool) -> None:
        """Everyone linked to a bike, current owner first: its ownership history."""
        console = get_console()
        init_db()
        bike = _resolve_bike_slug_or_id(bike_identifier)
        rows = customer_bikes_repo.list_customers_for_bike(bike["id"])
        rows.sort(key=lambda r: (r["cb_relationship"] != "owner",))
        if as_json:
            click.echo(_json.dumps(rows, default=str, indent=2))
            return
        label = f"{bike.get('year') or ''} {bike.get('make')} {bike.get('model')}".strip()
        if not rows:
            console.print(f"[dim]No customer is linked to {label}.[/dim]")
            return
        table = Table(title=f"Owners of {label} (id={bike['id']})", show_lines=False)
        table.add_column("Customer ID", justify="right")
        table.add_column("Name")
        table.add_column("Relationship")
        table.add_column("Linked")
        table.add_column("Notes")
        for r in rows:
            table.add_row(
                str(r["id"]), r["name"], r["cb_relationship"],
                str(r["cb_assigned_at"] or "—"), r.get("cb_notes") or "",
            )
        console.print(table)
