"""`motodiag shop inventory`: stock, reorder points and local purchase orders.

The shop's own parts stock (``inventory_items``), which is separate from the
parts a work order needs (``shop parts-needs``). A PO is generated and
printed here; sending it to the supplier is left to the user.
"""

from __future__ import annotations

import json as _json
from pathlib import Path
from typing import Optional

import click
from rich.table import Table

from motodiag.cli.theme import get_console
from motodiag.core.database import init_db
from motodiag.inventory import item_repo, purchase_orders, vendor_repo
from motodiag.inventory.models import InventoryItem, Vendor


def _money(cents: int) -> str:
    return f"${cents / 100:,.2f}"


def _dollars(cents: Optional[int]) -> Optional[float]:
    return None if cents is None else round(cents / 100, 2)


def _resolve_item(sku: str) -> dict:
    item = item_repo.get_item_by_sku(sku)
    if item is None:
        raise click.ClickException(
            f"No inventory item with SKU {sku!r}. "
            "Run `motodiag shop inventory list` to see the stock."
        )
    return item


def _resolve_vendor(identifier: str) -> dict:
    try:
        vendor = vendor_repo.get_vendor(int(identifier))
    except ValueError:
        vendor = vendor_repo.get_vendor_by_name(identifier)
    if vendor is None:
        raise click.ClickException(
            f"No vendor {identifier!r}. "
            "Run `motodiag shop inventory vendor list` to see them."
        )
    return vendor


def register_inventory(shop_group: click.Group) -> None:

    @shop_group.group("inventory")
    def inventory_group() -> None:
        """Parts stock, reorder points and purchase orders."""

    # ---------------------------------------------------------------- vendors
    @inventory_group.group("vendor")
    def vendor_group() -> None:
        """Suppliers the shop orders stock from."""

    @vendor_group.command("add")
    @click.option("--name", required=True)
    @click.option("--contact", "contact_name", default=None)
    @click.option("--email", default=None)
    @click.option("--phone", default=None)
    @click.option("--website", default=None)
    @click.option("--address", default=None)
    @click.option("--terms", "payment_terms", default=None,
                  help="Payment terms, e.g. 'Net 30'.")
    @click.option("--notes", default=None)
    def vendor_add(name, contact_name, email, phone, website, address,
                   payment_terms, notes) -> None:
        """Add a vendor."""
        init_db()
        if vendor_repo.get_vendor_by_name(name) is not None:
            raise click.ClickException(f"A vendor named {name!r} already exists.")
        vendor_id = vendor_repo.add_vendor(Vendor(
            name=name, contact_name=contact_name, email=email, phone=phone,
            website=website, address=address, payment_terms=payment_terms,
            notes=notes,
        ))
        get_console().print(f"[green]Added vendor #{vendor_id}: {name}.[/green]")

    @vendor_group.command("list")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def vendor_list(as_json: bool) -> None:
        """List vendors."""
        console = get_console()
        init_db()
        rows = vendor_repo.list_vendors()
        if as_json:
            click.echo(_json.dumps(rows, default=str, indent=2))
            return
        if not rows:
            console.print("[dim]No vendors yet.[/dim]")
            return
        table = Table(title="Vendors")
        for col in ("ID", "Name", "Contact", "Email", "Phone", "Terms"):
            table.add_column(col)
        for v in rows:
            table.add_row(str(v["id"]), v["name"], v.get("contact_name") or "—",
                          v.get("email") or "—", v.get("phone") or "—",
                          v.get("payment_terms") or "—")
        console.print(table)

    # ---------------------------------------------------------------- items
    @inventory_group.command("add")
    @click.option("--sku", required=True)
    @click.option("--name", required=True)
    @click.option("--category", default=None)
    @click.option("--make", default=None, help="Make it fits, if one.")
    @click.option("--qty", "quantity_on_hand", type=click.IntRange(min=0), default=0)
    @click.option("--reorder-point", type=click.IntRange(min=0), default=0,
                  help="Reorder when stock falls to this level (0 = never).")
    @click.option("--reorder-qty", "reorder_quantity", type=click.IntRange(min=0),
                  default=0, help="How many to order when it does.")
    @click.option("--unit-cost-cents", type=click.IntRange(min=0), default=0,
                  help="What the shop pays per unit.")
    @click.option("--unit-price-cents", type=click.IntRange(min=0), default=0,
                  help="What the shop charges per unit.")
    @click.option("--vendor", "vendor_identifier", default=None,
                  help="Vendor id or name.")
    @click.option("--location", default=None, help="Shelf or bin.")
    def item_add(sku, name, category, make, quantity_on_hand, reorder_point,
                 reorder_quantity, unit_cost_cents, unit_price_cents,
                 vendor_identifier, location) -> None:
        """Add a stocked part."""
        init_db()
        if item_repo.get_item_by_sku(sku) is not None:
            raise click.ClickException(f"SKU {sku!r} is already in the stock.")
        vendor_id = _resolve_vendor(vendor_identifier)["id"] if vendor_identifier else None
        item_id = item_repo.add_item(InventoryItem(
            sku=sku, name=name, category=category, make=make,
            quantity_on_hand=quantity_on_hand, reorder_point=reorder_point,
            reorder_quantity=reorder_quantity,
            unit_cost=_dollars(unit_cost_cents), unit_price=_dollars(unit_price_cents),
            vendor_id=vendor_id, location=location,
        ))
        get_console().print(f"[green]Added {sku} (item #{item_id}), "
                            f"{quantity_on_hand} on hand.[/green]")

    @inventory_group.command("list")
    @click.option("--low", is_flag=True, default=False,
                  help="Only items at or below their reorder point.")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def item_list(low: bool, as_json: bool) -> None:
        """List the stock."""
        console = get_console()
        init_db()
        rows = item_repo.items_below_reorder() if low else item_repo.list_items()
        if as_json:
            click.echo(_json.dumps(rows, default=str, indent=2))
            return
        if not rows:
            console.print("[dim]Nothing at or below its reorder point.[/dim]" if low
                          else "[dim]No stock recorded yet.[/dim]")
            return
        table = Table(title="Stock at or below reorder point" if low else "Stock")
        for col in ("SKU", "Name", "On hand", "Reorder at", "Reorder qty",
                    "Vendor", "Location"):
            table.add_column(col)
        for r in rows:
            table.add_row(r["sku"], r["name"], str(r["quantity_on_hand"]),
                          str(r["reorder_point"]), str(r.get("reorder_quantity") or "—"),
                          str(r.get("vendor_id") or "—"), r.get("location") or "—")
        console.print(table)

    @inventory_group.command("show")
    @click.argument("sku")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def item_show(sku: str, as_json: bool) -> None:
        """Show one stocked part."""
        console = get_console()
        init_db()
        item = _resolve_item(sku)
        if as_json:
            click.echo(_json.dumps(item, default=str, indent=2))
            return
        for key in ("sku", "name", "category", "make", "quantity_on_hand",
                    "reorder_point", "reorder_quantity", "unit_cost", "unit_price",
                    "vendor_id", "location"):
            value = item.get(key)
            console.print(f"{key}: {value if value is not None else '—'}")

    @inventory_group.command("adjust")
    @click.argument("sku")
    @click.option("--by", "delta", type=int, required=True,
                  help="Change in stock: negative when parts are used.")
    def item_adjust(sku: str, delta: int) -> None:
        """Change a part's stock level."""
        console = get_console()
        init_db()
        item = _resolve_item(sku)
        if item["quantity_on_hand"] + delta < 0:
            raise click.ClickException(
                f"{sku} has {item['quantity_on_hand']} on hand; "
                f"it cannot go down by {-delta}."
            )
        new_qty = item_repo.adjust_quantity(item["id"], delta)
        console.print(f"[green]{sku}: {new_qty} on hand.[/green]")
        if item["reorder_point"] and new_qty <= item["reorder_point"]:
            console.print(f"[yellow]{sku} is at or below its reorder point "
                          f"({item['reorder_point']}).[/yellow]")

    @inventory_group.command("set")
    @click.argument("sku")
    @click.option("--reorder-point", type=click.IntRange(min=0), default=None)
    @click.option("--reorder-qty", "reorder_quantity", type=click.IntRange(min=0),
                  default=None)
    @click.option("--vendor", "vendor_identifier", default=None)
    @click.option("--unit-cost-cents", type=click.IntRange(min=0), default=None)
    @click.option("--unit-price-cents", type=click.IntRange(min=0), default=None)
    @click.option("--location", default=None)
    def item_set(sku, reorder_point, reorder_quantity, vendor_identifier,
                 unit_cost_cents, unit_price_cents, location) -> None:
        """Change a part's reorder point, order quantity, vendor, costs or bin."""
        init_db()
        item = _resolve_item(sku)
        fields: dict = {}
        if reorder_point is not None:
            fields["reorder_point"] = reorder_point
        if reorder_quantity is not None:
            fields["reorder_quantity"] = reorder_quantity
        if vendor_identifier is not None:
            fields["vendor_id"] = _resolve_vendor(vendor_identifier)["id"]
        if unit_cost_cents is not None:
            fields["unit_cost"] = _dollars(unit_cost_cents)
        if unit_price_cents is not None:
            fields["unit_price"] = _dollars(unit_price_cents)
        if location is not None:
            fields["location"] = location
        if not fields:
            raise click.ClickException("Nothing to change: pass at least one option.")
        item_repo.update_item(item["id"], **fields)
        get_console().print(f"[green]Updated {sku}: {', '.join(sorted(fields))}.[/green]")

    @inventory_group.command("reorder")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def item_reorder(as_json: bool) -> None:
        """What is due for reorder, and what a purchase order would order."""
        console = get_console()
        init_db()
        plan = purchase_orders.reorder_plan()
        if as_json:
            click.echo(_json.dumps(plan, default=str, indent=2))
            return
        if not plan:
            console.print("[dim]Nothing is at or below its reorder point.[/dim]")
            return
        table = Table(title="Due for reorder")
        for col in ("SKU", "Name", "On hand", "Reorder at", "Order", "Vendor"):
            table.add_column(col)
        for p in plan:
            order = (str(p["order_quantity"]) if p["skip_reason"] is None
                     else f"not ordered: {p['skip_reason']}")
            table.add_row(p["sku"], p["name"], str(p["quantity_on_hand"]),
                          str(p["reorder_point"]), order, str(p.get("vendor_id") or "—"))
        console.print(table)

    # ---------------------------------------------------------------- POs
    @inventory_group.group("po")
    def po_group() -> None:
        """Purchase orders, generated here and sent by you."""

    @po_group.command("generate")
    def po_generate() -> None:
        """Draft one purchase order per vendor for everything due for reorder."""
        console = get_console()
        init_db()
        po_ids, skipped = purchase_orders.generate_purchase_orders()
        for po_id in po_ids:
            po = purchase_orders.get_purchase_order(po_id)
            console.print(f"[green]Drafted {po['po_number']} (#{po_id}) to "
                          f"{po['vendor_name']}: {len(po['lines'])} line(s), "
                          f"{_money(po['total_cents'])}.[/green]")
        for s in skipped:
            console.print(f"[yellow]Not ordered: {s['sku']} ({s['name']}): "
                          f"{s['skip_reason']}.[/yellow]")
        if not po_ids and not skipped:
            console.print("[dim]Nothing is at or below its reorder point.[/dim]")
        elif po_ids:
            console.print("Print one with `motodiag shop inventory po show ID --out FILE`, "
                          "send it to the vendor, then `po mark-sent ID`.")

    @po_group.command("list")
    @click.option("--status", type=click.Choice(purchase_orders.PO_STATUSES), default=None)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def po_list(status: Optional[str], as_json: bool) -> None:
        """List purchase orders, newest first."""
        console = get_console()
        init_db()
        rows = purchase_orders.list_purchase_orders(status=status)
        if as_json:
            click.echo(_json.dumps(rows, default=str, indent=2))
            return
        if not rows:
            console.print("[dim]No purchase orders.[/dim]")
            return
        table = Table(title="Purchase orders")
        for col in ("ID", "Number", "Vendor", "Status", "Lines", "Total", "Created"):
            table.add_column(col)
        for r in rows:
            table.add_row(str(r["id"]), r["po_number"], r["vendor_name"], r["status"],
                          str(r["line_count"]), _money(r["total_cents"]),
                          str(r["created_at"]))
        console.print(table)

    @po_group.command("show")
    @click.argument("po_id", type=int)
    @click.option("--out", "out_path", type=click.Path(dir_okay=False), default=None,
                  help="Write the printable PO to this file.")
    def po_show(po_id: int, out_path: Optional[str]) -> None:
        """Show a purchase order as printable text."""
        from motodiag.shop import list_shops

        init_db()
        po = purchase_orders.get_purchase_order(po_id)
        if po is None:
            raise click.ClickException(f"No purchase order #{po_id}.")
        shops = list_shops(owner_user_id=None)
        text = purchase_orders.render_purchase_order(
            po, shop=shops[0] if len(shops) == 1 else None,
        )
        if out_path:
            Path(out_path).write_text(text, encoding="utf-8")
            get_console().print(f"[green]Wrote {po['po_number']} to {out_path}.[/green]")
            return
        click.echo(text, nl=False)

    def _move(po_id: int, target: str) -> dict:
        init_db()
        try:
            po = purchase_orders.set_status(po_id, target)
        except purchase_orders.PurchaseOrderError as e:
            raise click.ClickException(str(e)) from e
        get_console().print(f"[green]{po['po_number']} is {target}.[/green]")
        return po

    @po_group.command("mark-sent")
    @click.argument("po_id", type=int)
    def po_mark_sent(po_id: int) -> None:
        """Record that you sent the purchase order to the vendor."""
        _move(po_id, "sent")

    @po_group.command("receive")
    @click.argument("po_id", type=int)
    def po_receive(po_id: int) -> None:
        """Record the delivery: each line's quantity is added to stock."""
        po = _move(po_id, "received")
        for line in po["lines"]:
            get_console().print(f"  +{line['quantity']} {line['sku']}")

    @po_group.command("cancel")
    @click.argument("po_id", type=int)
    def po_cancel(po_id: int) -> None:
        """Cancel a draft or sent purchase order."""
        _move(po_id, "cancelled")
