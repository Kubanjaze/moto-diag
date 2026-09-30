"""`motodiag shop warranty`: a bike's coverage, whether it applies, and claims.

Claims are the shop's own records and a printable packet. Submitting a
claim through a maker's own system needs that maker's dealer portal and is
not built.
"""

from __future__ import annotations

import json as _json
from datetime import date
from pathlib import Path
from typing import Optional

import click
from rich.table import Table

from motodiag.cli.theme import get_console
from motodiag.core.database import init_db
from motodiag.inventory import warranty_claims, warranty_repo
from motodiag.inventory.models import CoverageType, Warranty

_DATE = click.DateTime(formats=["%Y-%m-%d"])


def _iso(value) -> Optional[str]:
    return value.date().isoformat() if value is not None else None


def _miles(value: Optional[int]) -> str:
    return "not known" if value is None else f"{value:,} mi"


def register_warranty(shop_group: click.Group) -> None:
    from motodiag.cli.shop import _resolve_bike_slug_or_id

    @shop_group.group("warranty")
    def warranty_group() -> None:
        """Warranty coverage on a bike, whether it applies, and claims."""

    @warranty_group.command("add")
    @click.option("--bike", "bike_identifier", required=True)
    @click.option("--coverage", type=click.Choice([c.value for c in CoverageType]),
                  required=True)
    @click.option("--provider", default=None,
                  help="Who gives the warranty, e.g. the maker.")
    @click.option("--start", type=_DATE, default=None, help="YYYY-MM-DD")
    @click.option("--end", type=_DATE, default=None, help="YYYY-MM-DD")
    @click.option("--mileage-limit", type=click.IntRange(min=0), default=None,
                  help="Miles on the odometer at which it ends.")
    @click.option("--terms", default=None)
    def warranty_add(bike_identifier, coverage, provider, start, end,
                     mileage_limit, terms) -> None:
        """Record a warranty on a bike."""
        init_db()
        bike = _resolve_bike_slug_or_id(bike_identifier)
        if start and end and end < start:
            raise click.ClickException("The end date is before the start date.")
        warranty_id = warranty_repo.add_warranty(Warranty(
            vehicle_id=bike["id"], coverage_type=CoverageType(coverage),
            provider=provider, start_date=_iso(start), end_date=_iso(end),
            mileage_limit=mileage_limit, terms=terms,
        ))
        get_console().print(f"[green]Recorded warranty #{warranty_id} ({coverage}) "
                            f"on bike id={bike['id']}.[/green]")

    @warranty_group.command("list")
    @click.option("--bike", "bike_identifier", required=True)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def warranty_list(bike_identifier: str, as_json: bool) -> None:
        """A bike's recorded warranties."""
        console = get_console()
        init_db()
        bike = _resolve_bike_slug_or_id(bike_identifier)
        rows = warranty_repo.list_warranties_for_vehicle(bike["id"])
        if as_json:
            click.echo(_json.dumps(rows, default=str, indent=2))
            return
        if not rows:
            console.print(f"[dim]No warranty recorded on bike id={bike['id']}.[/dim]")
            return
        table = Table(title=f"Warranties on bike id={bike['id']}")
        for col in ("ID", "Coverage", "Provider", "Start", "End", "Mileage limit",
                    "Claims"):
            table.add_column(col)
        for w in rows:
            limit = w.get("mileage_limit")
            table.add_row(str(w["id"]), w["coverage_type"], w.get("provider") or "—",
                          w.get("start_date") or "—", w.get("end_date") or "—",
                          f"{limit:,}" if limit is not None else "—",
                          str(w["claim_count"]))
        console.print(table)

    @warranty_group.command("check")
    @click.option("--bike", "bike_identifier", required=True)
    @click.option("--on", "on_date", type=_DATE, default=None,
                  help="The date to check (YYYY-MM-DD). Default: today.")
    @click.option("--mileage", type=click.IntRange(min=0), default=None,
                  help="Odometer reading. Default: the bike's recorded mileage.")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def warranty_check(bike_identifier, on_date, mileage, as_json) -> None:
        """Whether each recorded warranty applies on a date at a mileage."""
        console = get_console()
        init_db()
        bike = _resolve_bike_slug_or_id(bike_identifier)
        when = _iso(on_date) or date.today().isoformat()
        miles = mileage if mileage is not None else bike.get("mileage")
        results = []
        for w in warranty_repo.list_warranties_for_vehicle(bike["id"]):
            verdict, reasons = warranty_repo.coverage_status(w, when, miles)
            results.append({"warranty_id": w["id"], "coverage_type": w["coverage_type"],
                            "provider": w.get("provider"), "verdict": verdict,
                            "reasons": reasons})
        if as_json:
            click.echo(_json.dumps({"vehicle_id": bike["id"], "on": when,
                                    "mileage": miles, "coverage": results}, indent=2))
            return
        console.print(f"Bike id={bike['id']} on {when}, mileage {_miles(miles)}")
        if not results:
            console.print("[yellow]No warranty is recorded on this bike, so none "
                          "can be shown to apply.[/yellow]")
            return
        colour = {"valid": "green", "not valid": "red", "cannot tell": "yellow"}
        for r in results:
            c = colour[r["verdict"]]
            provider = f" ({r['provider']})" if r["provider"] else ""
            console.print(f"  #{r['warranty_id']} {r['coverage_type']}{provider}: "
                          f"[{c}]{r['verdict']}[/{c}] — {'; '.join(r['reasons'])}")

    # ---------------------------------------------------------------- claims
    @warranty_group.group("claim")
    def claim_group() -> None:
        """Warranty claims the shop keeps, and the printable packet."""

    @claim_group.command("open")
    @click.option("--warranty", "warranty_id", type=int, required=True)
    @click.option("--wo", "work_order_id", type=int, default=None,
                  help="The work order the repair was done on.")
    @click.option("--description", required=True, help="The failure and the repair.")
    @click.option("--claimed-cents", "amount_claimed_cents",
                  type=click.IntRange(min=0), default=None)
    def claim_open(warranty_id, work_order_id, description, amount_claimed_cents) -> None:
        """Open a draft claim against a recorded warranty."""
        init_db()
        try:
            claim_id = warranty_claims.open_claim(
                warranty_id, description, work_order_id=work_order_id,
                amount_claimed_cents=amount_claimed_cents,
            )
        except warranty_claims.WarrantyClaimError as e:
            raise click.ClickException(str(e)) from e
        get_console().print(
            f"[green]Opened claim #{claim_id} (draft). Print its packet with "
            f"`motodiag shop warranty claim packet {claim_id}`.[/green]"
        )

    @claim_group.command("list")
    @click.option("--status", type=click.Choice(warranty_claims.CLAIM_STATUSES),
                  default=None)
    @click.option("--bike", "bike_identifier", default=None)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def claim_list(status, bike_identifier, as_json) -> None:
        """List claims, newest first."""
        console = get_console()
        init_db()
        vehicle_id = (_resolve_bike_slug_or_id(bike_identifier)["id"]
                      if bike_identifier else None)
        rows = warranty_claims.list_claims(status=status, vehicle_id=vehicle_id)
        if as_json:
            click.echo(_json.dumps(rows, default=str, indent=2))
            return
        if not rows:
            console.print("[dim]No claims.[/dim]")
            return
        table = Table(title="Warranty claims")
        for col in ("ID", "Bike", "Coverage", "WO", "Status", "Claim no.", "Opened"):
            table.add_column(col)
        for c in rows:
            table.add_row(str(c["id"]), str(c["vehicle_id"]), c["coverage_type"],
                          str(c["work_order_id"] or "—"), c["status"],
                          c.get("claim_number") or "—", str(c["opened_at"]))
        console.print(table)

    @claim_group.command("show")
    @click.argument("claim_id", type=int)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def claim_show(claim_id: int, as_json: bool) -> None:
        """Show one claim."""
        init_db()
        claim = warranty_claims.get_claim(claim_id)
        if claim is None:
            raise click.ClickException(f"No claim #{claim_id}.")
        if as_json:
            click.echo(_json.dumps(claim, default=str, indent=2))
            return
        console = get_console()
        for key in ("id", "status", "claim_number", "warranty_id", "coverage_type",
                    "vehicle_id", "work_order_id", "description", "amount_claimed_cents",
                    "amount_approved_cents", "opened_at", "submitted_at",
                    "decided_at", "paid_at"):
            value = claim.get(key)
            console.print(f"{key}: {value if value is not None else '—'}")

    @claim_group.command("status")
    @click.argument("claim_id", type=int)
    @click.option("--to", "target", required=True,
                  type=click.Choice(warranty_claims.CLAIM_STATUSES[1:]))
    @click.option("--claim-number", default=None,
                  help="The maker's number for the claim.")
    @click.option("--approved-cents", "amount_approved_cents",
                  type=click.IntRange(min=0), default=None)
    def claim_status(claim_id, target, claim_number, amount_approved_cents) -> None:
        """Record a claim's progress: submitted, approved, denied or paid."""
        init_db()
        try:
            claim = warranty_claims.set_claim_status(
                claim_id, target, claim_number=claim_number,
                amount_approved_cents=amount_approved_cents,
            )
        except warranty_claims.WarrantyClaimError as e:
            raise click.ClickException(str(e)) from e
        get_console().print(f"[green]Claim #{claim['id']} is {claim['status']}.[/green]")

    @claim_group.command("packet")
    @click.argument("claim_id", type=int)
    @click.option("--out", "out_path", type=click.Path(dir_okay=False), default=None,
                  help="Write the packet to this file.")
    def claim_packet(claim_id: int, out_path: Optional[str]) -> None:
        """The claim's documentation, printable."""
        init_db()
        try:
            text = warranty_claims.render_claim_packet(claim_id)
        except warranty_claims.WarrantyClaimError as e:
            raise click.ClickException(str(e)) from e
        if out_path:
            Path(out_path).write_text(text, encoding="utf-8")
            get_console().print(f"[green]Wrote claim #{claim_id}'s packet to "
                                f"{out_path}.[/green]")
            return
        click.echo(text, nl=False)
