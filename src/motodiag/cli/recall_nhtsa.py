"""`motodiag advanced recall refresh` and `motodiag advanced vin decode`.

The commands that call NHTSA's recall service and vPIC, and the one
renderer every recall lookup uses to say what the stored data does and does
not show. Attached by ``register_advanced``.
"""

from __future__ import annotations

import json as _json
from typing import Optional

import click
from rich.panel import Panel

from motodiag.advanced import recall_repo
from motodiag.cli.theme import get_console
from motodiag.core.database import init_db
from motodiag.core.outbound import ServiceUnavailable

VIN_INCLUSION_NOTE = (
    "These campaigns may apply to this bike. Whether this VIN is included is not "
    "in NHTSA's public data: check nhtsa.gov/recalls or the maker."
)


def render_recalls(console, rows: list[dict], title: str) -> None:
    from motodiag.cli.advanced import _render_recall_table

    _render_recall_table(console, rows, title)


def render_none_found(console, make: str, model: str, year: int, state: dict) -> None:
    """Zero stored campaigns for a make, model and year: say what that means."""
    fetch = state.get("fetch")
    failure = state.get("last_failure")
    if failure:
        console.print(f"[yellow]The last refresh, {failure['fetched_at'][:10]}, failed: "
                      f"{failure['error']}[/yellow]")
    if fetch is None:
        console.print(Panel(
            f"[yellow]No recall data is fetched for {year} {make} {model} — this is NOT "
            f"an all-clear.[/yellow]\n\n"
            f"[dim]Fetch NHTSA's recalls with `motodiag advanced recall refresh --make "
            f"\"{make}\" --model \"{model}\" --year {year}`. The sample file shipped with "
            f"this project carries illustrative campaign ids, not filed NHTSA campaigns, "
            f"and nothing seeds it. Or check the manufacturer or NHTSA directly.[/dim]",
            title="Recall lookup unavailable", border_style="yellow",
        ))
        return
    console.print(Panel(
        f"[yellow]NHTSA listed no recall for {year} {fetch['make'].upper()} "
        f"{fetch['model'].upper()} as named, on {fetch['fetched_at'][:10]}.[/yellow]\n\n"
        "[dim]NHTSA matches the model name exactly, and a name it does not use also "
        "returns none: this is not an all-clear. Check the model name at "
        "nhtsa.gov/recalls, or ask the maker.[/dim]",
        title="No recall listed as named", border_style="yellow",
    ))


def register_recall_refresh(recall_group: click.Group) -> None:
    @recall_group.command("refresh")
    @click.option("--make", default=None)
    @click.option("--model", "model_name", default=None)
    @click.option("--year", type=int, default=None)
    @click.option("--bike", default=None, help="A garage bike's slug.")
    @click.option("--vin", default=None, help="Decode with vPIC first, then fetch.")
    @click.option("--all-bikes", is_flag=True, default=False,
                  help="Every garage bike with a make, model and year.")
    def refresh(make: Optional[str], model_name: Optional[str], year: Optional[int],
                bike: Optional[str], vin: Optional[str], all_bikes: bool) -> None:
        """Fetch NHTSA's recalls and store them with the date fetched."""
        console = get_console()
        init_db()
        chosen = sum([bool(make or model_name or year), bool(bike), bool(vin), all_bikes])
        if chosen != 1:
            raise click.UsageError(
                "give one of: --make/--model/--year, --bike, --vin, or --all-bikes")
        if all_bikes:
            _refresh_all(console)
            return
        if bike:
            from motodiag.cli.diagnose import _resolve_bike_slug
            resolved = _resolve_bike_slug(bike)
            if resolved is None:
                raise click.ClickException(f"no garage bike matches {bike!r}")
            make, model_name, year = resolved.get("make"), resolved.get("model"), \
                resolved.get("year")
            if not (make and model_name and year):
                raise click.ClickException(
                    f"bike {bike!r} needs a make, model and year to ask NHTSA")
        elif vin:
            try:
                decoded = recall_repo.decode_vin_online(vin)
            except ValueError as e:
                raise click.ClickException(str(e)) from e
            except ServiceUnavailable as e:
                console.print(f"[red]{e.message}[/red]")
                raise click.exceptions.Exit(1)
            make, model_name, year = decoded["make"], decoded["model"], decoded["model_year"]
            if not (make and model_name and year):
                raise click.ClickException(
                    f"vPIC did not give a make, model and year for {vin.upper()} "
                    f"(error {decoded.get('error_code')}: {decoded.get('error_text')})")
            console.print(f"vPIC: {year} {make} {model_name} (decoded "
                          f"{str(decoded['fetched_at'])[:10]}).")
        elif not (make and model_name and year):
            raise click.UsageError("--make, --model and --year are all needed")
        try:
            res = recall_repo.refresh_recalls(make, model_name, int(year))
        except ServiceUnavailable as e:
            console.print(f"[red]{e.message}[/red]")
            state = recall_repo.recall_state(make, model_name, int(year))
            if state["recalls"]:
                render_recalls(console, state["recalls"],
                               f"Stored recalls for {year} {make} {model_name} (not refreshed)")
            elif state["fetch"] is not None:
                console.print(f"Stored: NHTSA listed none as named on "
                              f"{state['fetch']['fetched_at'][:10]}.")
            else:
                console.print("Nothing is stored for this model.")
            raise click.exceptions.Exit(1)
        console.print(f"[green]NHTSA: {res['count']} campaign(s) for {year} {make.upper()} "
                      f"{model_name.upper()}, fetched {res['fetched_at'][:10]}.[/green]")
        state = recall_repo.recall_state(make, model_name, int(year))
        if state["recalls"]:
            render_recalls(console, state["recalls"], f"Recalls for {year} {make} {model_name}")
            console.print(f"[dim]{VIN_INCLUSION_NOTE}[/dim]")
        else:
            render_none_found(console, make, model_name, int(year), state)


def _refresh_all(console) -> None:
    try:
        res = recall_repo.refresh_all_bikes()
    except recall_repo.RecallCheckFailed as e:
        console.print(f"[red]{e}[/red]")
        raise click.exceptions.Exit(1)
    for item in res["refreshed"]:
        console.print(f"[green]{item['year']} {item['make']} {item['model']}: "
                      f"{item['count']} campaign(s).[/green]")
    for item in res["skipped"]:
        console.print(f"[dim]Skipped bike {item['id']}: {item['reason']}.[/dim]")
    for item in res["failed"]:
        console.print(f"[red]Not refreshed: {item['year']} {item['make']} {item['model']}: "
                      f"{item['error']}. Its stored data is unchanged.[/red]")
    if res["failed"]:
        raise click.exceptions.Exit(1)


def register_vin(advanced_group: click.Group) -> None:
    @advanced_group.group("vin")
    def vin_group() -> None:
        """VIN decoding by NHTSA's vPIC."""

    @vin_group.command("decode")
    @click.argument("vin")
    @click.option("--refresh", is_flag=True, default=False, help="Ask vPIC again.")
    @click.option("--bike", default=None, help="A garage bike's slug, with --save.")
    @click.option("--save", is_flag=True, default=False,
                  help="Write the VIN to --bike when it has none.")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def decode(vin: str, refresh: bool, bike: Optional[str], save: bool,
               as_json: bool) -> None:
        """Decode a VIN: make, model, model year and vehicle type."""
        console = get_console()
        init_db()
        if save and not bike:
            raise click.UsageError("--save needs --bike")
        try:
            decoded = recall_repo.decode_vin_online(vin, refresh=refresh)
        except ValueError as e:
            raise click.ClickException(str(e)) from e
        except ServiceUnavailable as e:
            console.print(f"[red]{e.message}[/red]")
            offline = recall_repo.decode_vin(vin)
            console.print(Panel(
                f"Make: {offline.get('make') or 'unknown'}\n"
                f"Year: {offline.get('year') or 'unknown'}",
                title="Offline: maker and year only", border_style="yellow"))
            raise click.exceptions.Exit(1)
        if as_json:
            click.echo(_json.dumps({k: v for k, v in decoded.items() if k != "response_json"},
                                   indent=2, default=str))
        else:
            lines = [
                f"[bold]{decoded['vin']}[/bold]",
                f"Make: {decoded.get('make') or 'not given'}",
                f"Model: {decoded.get('model') or 'not given'}",
                f"Model year: {decoded.get('model_year') or 'not given'}",
                f"Manufacturer: {decoded.get('manufacturer') or 'not given'}",
                f"Vehicle type: {decoded.get('vehicle_type') or 'not given'}",
            ]
            if recall_repo.decode_is_partial(decoded):
                lines.append(f"[yellow]Partial decode. vPIC error "
                             f"{decoded.get('error_code')}: {decoded.get('error_text')}[/yellow]")
            lines.append(f"[dim]NHTSA vPIC, decoded {str(decoded['fetched_at'])[:10]}.[/dim]")
            console.print(Panel("\n".join(lines), title="VIN decoded", border_style="cyan"))
        if save:
            _save_to_bike(console, bike, decoded)


def _save_to_bike(console, bike: str, decoded: dict) -> None:
    from motodiag.cli.diagnose import _resolve_bike_slug
    resolved = _resolve_bike_slug(bike)
    if resolved is None:
        raise click.ClickException(f"no garage bike matches {bike!r}")
    outcome = recall_repo.save_vin_to_bike(int(resolved["id"]), decoded)
    for note in outcome["disagreements"]:
        console.print(f"[yellow]{note}[/yellow]")
    if outcome["saved"]:
        console.print(f"[green]VIN saved to bike {resolved['id']}.[/green]")
    else:
        console.print(f"[yellow]{outcome['reason']}[/yellow]")
        raise click.exceptions.Exit(1)
