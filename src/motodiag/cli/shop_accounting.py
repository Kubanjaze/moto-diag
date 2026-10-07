"""`motodiag shop accounting`: the account mapping and the export files.

Attached to the ``shop`` group by :func:`register_accounting`, which
``register_shop`` calls.
"""

from __future__ import annotations

import json as _json
from typing import Optional

import click
from rich.table import Table

from motodiag.accounting import export as acct_export
from motodiag.cli.theme import get_console
from motodiag.core.database import init_db

_TARGET_CHOICE = click.Choice(list(acct_export.TARGETS))


def register_accounting(shop_group: click.Group) -> None:
    @shop_group.group("accounting")
    def accounting_group() -> None:
        """Export invoices as files for QuickBooks Online or Xero to import."""

    @accounting_group.group("map")
    def map_group() -> None:
        """Which of your accounts each kind of amount goes to."""

    @map_group.command("set")
    @click.option("--shop", "shop_id", type=int, required=True)
    @click.option("--target", required=True, type=_TARGET_CHOICE)
    @click.option("--kind", required=True, type=click.Choice(acct_export.KINDS),
                  help="labor, parts, diagnostic, misc (shop supplies), tax "
                       "(QuickBooks: the sales-tax liability account) or "
                       "receivable (QuickBooks: accounts receivable).")
    @click.option("--account", required=True,
                  help="The account exactly as your accounting software names it "
                       "(Xero: its code).")
    @click.option("--tax-type", default=None,
                  help="Xero only: the tax rate's display name, in full.")
    def map_set(shop_id: int, target: str, kind: str, account: str,
                tax_type: Optional[str]) -> None:
        """Map a kind of amount to one of your accounts."""
        console = get_console()
        init_db()
        try:
            acct_export.set_account(shop_id, target, kind, account, tax_type)
        except acct_export.ExportError as e:
            raise click.ClickException(str(e)) from e
        extra = f", tax rate {tax_type!r}" if tax_type else ""
        console.print(
            f"[green]{target}: {acct_export.KIND_LABELS[kind]} goes to "
            f"{account!r}{extra}.[/green]"
        )

    @map_group.command("list")
    @click.option("--shop", "shop_id", type=int, required=True)
    @click.option("--target", default=None, type=_TARGET_CHOICE)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def map_list(shop_id: int, target: Optional[str], as_json: bool) -> None:
        """The shop's account mapping."""
        console = get_console()
        init_db()
        rows = acct_export.list_accounts(shop_id, target)
        if as_json:
            click.echo(_json.dumps(rows, default=str, indent=2))
            return
        if not rows:
            console.print("[dim]No accounts mapped yet.[/dim]")
            return
        table = Table(title=f"Account mapping, shop {shop_id}", show_lines=False)
        for col in ("Target", "Kind", "Account", "Tax rate"):
            table.add_column(col)
        for r in rows:
            table.add_row(
                next(k for k, v in acct_export.TARGETS.items() if v == r["target"]),
                acct_export.KIND_LABELS[r["kind"]], r["account"], r["tax_type"] or "—",
            )
        console.print(table)

    @accounting_group.command("export")
    @click.option("--shop", "shop_id", type=int, required=True)
    @click.option("--target", required=True, type=_TARGET_CHOICE)
    @click.option("--from", "from_day", required=True, help="First issue day, YYYY-MM-DD.")
    @click.option("--to", "to_day", required=True, help="Last issue day, YYYY-MM-DD.")
    @click.option("--out", "out_path", required=True, type=click.Path(dir_okay=False),
                  help="The .csv file to write.")
    @click.option("--include-exported", is_flag=True, default=False,
                  help="Also write invoices an earlier export already carried.")
    def accounting_export(shop_id: int, target: str, from_day: str, to_day: str,
                          out_path: str, include_exported: bool) -> None:
        """Write the invoices issued in a date range as an import file.

        The file is written here; nothing is uploaded. Cancelled invoices are
        left out, and so are invoices an earlier export to the same target
        carried, unless --include-exported.
        """
        console = get_console()
        init_db()
        try:
            result = acct_export.export_file(shop_id, target, from_day, to_day,
                                             out_path, include_exported)
        except acct_export.ExportError as e:
            raise click.ClickException(str(e)) from e
        claims = (f" and {result.claim_count} warranty claim(s) owed by their providers"
                  if result.claim_count else "")
        console.print(
            f"[green]Wrote {result.invoice_count} invoice(s){claims}, {result.row_count} "
            f"row(s), to {result.path}.[/green]"
        )
        for note in result.notes:
            click.echo(note)
        if result.skipped:
            click.echo(
                f"Left out, already exported: {', '.join(result.skipped)}."
            )
        if result.shortfalls_left_out:
            click.echo(
                "Left out, a warranty claim's shortfall billed to the customer (claim "
                "settlements are not in the export yet): "
                f"{', '.join(result.shortfalls_left_out)}."
            )

    @accounting_group.command("exports")
    @click.option("--shop", "shop_id", type=int, required=True)
    def accounting_exports(shop_id: int) -> None:
        """The export files written so far."""
        console = get_console()
        init_db()
        rows = acct_export.list_exports(shop_id)
        if not rows:
            console.print("[dim]No exports yet.[/dim]")
            return
        table = Table(title=f"Exports, shop {shop_id}", show_lines=False)
        for col in ("ID", "When", "Target", "From", "To", "Invoices", "File"):
            table.add_column(col)
        for r in rows:
            table.add_row(
                str(r["id"]), r["exported_at"],
                next(k for k, v in acct_export.TARGETS.items() if v == r["target"]),
                r["period_from"], r["period_to"], str(r["invoice_count"]),
                r["file_name"],
            )
        console.print(table)
