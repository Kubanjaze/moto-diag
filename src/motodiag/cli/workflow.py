"""CLI entrypoint: ``motodiag workflow`` — the template substrate, finally reachable.

Phase 259. Phases 82 and 114 shipped the workflow machinery: an in-memory
diagnostic engine, then `workflow_templates` + `checklist_items` with a
full CRUD repo — and no command or route ever called any of it. A
template seeded by a Track N phase would have been as unreachable as
Phase 92's reference data was before 244V gave it a front door.

This module is that front door:

    motodiag workflow list
    motodiag workflow list --category ppi
    motodiag workflow show ppi_engine_v1
    motodiag workflow run brake_service_v1 --powertrain electric

`run` (Phase 356) walks a checklist through Phase 82's step engine, one
item at a time, and saves nothing.

Saved runs (Phase 357, migration 073) walk the same way and write each
answer as it is given:

    motodiag workflow start ppi_chassis_v1 --bike srf-2021 --powertrain electric
    motodiag workflow record 4 3 fail --notes "front pads at 2 mm"
    motodiag workflow resume 4
    motodiag workflow finish 4
    motodiag workflow runs --bike srf-2021
    motodiag workflow report 4

**On provenance** (the 244V rule): the content behind these screens is
authored per item, and every figure an item states cites the document it
came from, in the item's own description and instruction text. Where no
document sets a figure — the leak-down percentage, per Phase 259's census
of the research library — the item says where the figure belongs and
invents nothing. Nothing in this module computes; it reads and prints.
"""

from __future__ import annotations

import json

import click
from rich.table import Table

from motodiag.cli.theme import get_console
from motodiag.core.database import get_db_path
from motodiag.engine.workflows import StepResult
from motodiag.workflows import (
    WorkflowCategory,
    get_checklist_items,
    get_template_by_slug,
    list_templates,
)
from motodiag.workflows import run_repo
from motodiag.workflows.runner import checklist_workflow


def register_workflow(cli: click.Group) -> None:
    """Attach the ``workflow`` command group to the main CLI group."""
    cli.add_command(workflow)


@click.group("workflow")
def workflow() -> None:
    """Browse and run workflow templates (PPI, winterization, service protocols)."""


@workflow.command("list")
@click.option(
    "--category",
    type=click.Choice([c.value for c in WorkflowCategory], case_sensitive=False),
    default=None,
    help="Only templates in this category.",
)
def list_cmd(category: str | None) -> None:
    """List active workflow templates."""
    console = get_console()
    templates = list_templates(get_db_path(), category=category, is_active=True)
    if not templates:
        console.print(
            "[yellow]No active workflow templates"
            + (f" in category '{category}'" if category else "")
            + ".[/yellow]"
        )
        raise SystemExit(1)

    table = Table(show_header=True, header_style="bold cyan")
    # The slug is what `workflow show` takes and the category what
    # `--category` takes: both must print whole. Rich elides a column that
    # does not fit ("suspension_se…" at 80 columns), so these two never
    # shrink, and the free-text columns fold rather than elide.
    table.add_column("Slug", style="green", no_wrap=True)
    table.add_column("Category", no_wrap=True)
    table.add_column("Name", overflow="fold")
    table.add_column("Powertrains", overflow="fold")
    table.add_column("Minutes", justify="right")
    for t in templates:
        table.add_row(
            t["slug"],
            t["category"],
            t["name"],
            ", ".join(t["applicable_powertrains"]),
            str(t["estimated_duration_minutes"] or "—"),
        )
    console.print(table)
    console.print(
        "\n[dim]Run 'motodiag workflow show <slug>' for the full checklist.[/dim]\n"
    )


@workflow.command("show")
@click.argument("slug")
def show_cmd(slug: str) -> None:
    """Print a template's full checklist: instructions, pass/fail, diagnosis."""
    console = get_console()
    template = _template_or_refuse(console, slug)

    console.print()
    console.print(f"[bold]{template['name']}[/bold]")
    console.print(f"[dim]{template['slug']} · category {template['category']}"
                  f" · for {', '.join(template['applicable_powertrains'])}"
                  f" · ~{template['estimated_duration_minutes'] or '?'} minutes"
                  f" · tier {template['required_tier']}[/dim]")
    if template.get("description"):
        console.print(f"\n{template['description']}\n")

    items = get_checklist_items(template["id"], get_db_path())
    for item in items:
        _print_item(console, item)
        if item.get("diagnosis_if_fail"):
            console.print(f"  [yellow]If fail:[/yellow] {item['diagnosis_if_fail']}")
        if item.get("tools_needed"):
            console.print(f"  [dim]Tools: {', '.join(item['tools_needed'])}[/dim]")
    console.print()


def _print_item(console, item: dict) -> None:
    """An item's heading, description, instruction and pass/fail lines."""
    flag = "" if item["required"] else " [dim](optional)[/dim]"
    console.print(
        f"\n[bold cyan]{item['sequence_number']}. {item['title']}[/bold cyan]{flag}"
        + (
            f" [dim]· {item['estimated_minutes']} min[/dim]"
            if item["estimated_minutes"]
            else ""
        )
    )
    if item.get("description"):
        console.print(f"[dim]{item['description']}[/dim]")
    console.print(f"  {item['instruction_text']}")
    console.print(f"  [green]Pass:[/green] {item['expected_pass']}")
    console.print(f"  [red]Fail:[/red] {item['expected_fail']}")


def _template_or_refuse(console, slug: str) -> dict:
    """The active template, or the refusal `show` prints and exit 1."""
    template = get_template_by_slug(slug, get_db_path())
    if template is None:
        console.print(f"[red]No workflow template with slug '{slug}'.[/red]")
        console.print("[dim]Run 'motodiag workflow list' to see what exists.[/dim]")
        raise SystemExit(1)
    if not template["is_active"]:
        # Phase 359: a retired template's checklist is not shown. Its
        # description says it is retired and names what replaces it.
        console.print(f"[yellow]{slug}[/yellow]: {template['description'] or 'Retired.'}")
        raise SystemExit(1)
    return template


POWERTRAINS = ["ice", "electric", "hybrid"]
_ANSWERS = {"p": StepResult.PASS, "f": StepResult.FAIL, "s": StepResult.SKIPPED}


def _walk(console, template: dict, items: list[dict], save=None):
    """Ask each item in order through the step engine; return the engine.

    `save(item, result)` is called after each answer, before the next item
    is shown: `run` passes none, the saved commands (Phase 357) write it.
    """
    run = checklist_workflow(template, items)
    for item in items:
        _print_item(console, item)
        if item.get("tools_needed"):
            console.print(f"  [dim]Tools: {', '.join(item['tools_needed'])}[/dim]")
        choices = ["p", "f"] if item["required"] else ["p", "f", "s"]
        answer = click.prompt(
            f"  Result ({'/'.join(choices)})",
            type=click.Choice(choices, case_sensitive=False),
            show_choices=False,
        )
        result = _ANSWERS[answer.lower()]
        run.report_result(result)
        if answer.lower() == "f" and item.get("diagnosis_if_fail"):
            console.print(f"  [yellow]Diagnosis:[/yellow] {item['diagnosis_if_fail']}")
        if save is not None:
            save(item, result)
    return run


@workflow.command("run")
@click.argument("slug")
@click.option(
    "--powertrain",
    type=click.Choice(POWERTRAINS, case_sensitive=False),
    default=None,
    help="The machine's powertrain. Asked for when not given.",
)
def run_cmd(slug: str, powertrain: str | None) -> None:
    """Work through a template's checklist, one item at a time.

    Each answer is recorded as pass or fail (or skip, on an optional
    item); a fail prints the item's diagnosis; a summary ends the run.
    Nothing is saved.
    """
    console = get_console()
    template = _template_or_refuse(console, slug)
    if powertrain is None:
        powertrain = click.prompt(
            "Powertrain", type=click.Choice(POWERTRAINS, case_sensitive=False),
        )
    powertrain = powertrain.lower()
    covers = template["applicable_powertrains"]
    if powertrain not in covers:
        console.print(
            f"[red]{slug} covers {', '.join(covers)}, not {powertrain}.[/red]"
        )
        raise SystemExit(1)

    items = get_checklist_items(template["id"], get_db_path())
    console.print()
    console.print(f"[bold]{template['name']}[/bold]")
    console.print(f"[dim]{slug} · for {powertrain} · {len(items)} items[/dim]")

    run = _walk(console, template, items)

    results = [step.result for step in run.steps]
    console.print()
    console.print(
        f"[bold]Summary[/bold] · {slug} · for {powertrain}: "
        f"{results.count(StepResult.PASS)} passed, "
        f"{results.count(StepResult.FAIL)} failed, "
        f"{results.count(StepResult.SKIPPED)} skipped of {len(items)}"
    )
    for item, step in zip(items, run.steps):
        if step.result == StepResult.FAIL:
            console.print(
                f"  [red]{item['sequence_number']}. {item['title']}[/red]"
                + (f": {item['diagnosis_if_fail']}" if item.get("diagnosis_if_fail") else "")
            )
    console.print("[dim]Nothing was saved: this run exists only in this terminal.[/dim]")
    console.print()


# ---------------------------------------------------------------------------
# Saved runs (Phase 357, F165): start, record, resume, finish, runs, report
# ---------------------------------------------------------------------------

_RESULT_WORDS = {"pass": "pass", "fail": "fail", "skip": "skipped"}


def _bike_label(row: dict) -> str:
    return f"{row['vehicle_year']} {row['vehicle_make']} {row['vehicle_model']}"


def _refuse(console, message: str) -> None:
    console.print(f"[red]{message}[/red]")
    raise SystemExit(1)


def _vehicle_or_refuse(console, bike: str | None, vehicle_id: int | None) -> dict | None:
    """The garage bike named by --bike or --vehicle-id, or None if neither."""
    from motodiag.cli.diagnose import _resolve_bike_slug
    from motodiag.vehicles.registry import get_vehicle

    if vehicle_id is not None:
        vehicle = get_vehicle(vehicle_id, db_path=get_db_path())
        if vehicle is None:
            _refuse(console, f"No bike with id {vehicle_id} in the garage.")
        return vehicle
    if bike:
        vehicle = _resolve_bike_slug(bike, get_db_path())
        if vehicle is None:
            _refuse(console, f"No bike matches {bike!r}. Run 'motodiag garage list'.")
        return vehicle
    return None


def _run_or_refuse(console, run_id: int) -> dict:
    run = run_repo.get_run(run_id, get_db_path())
    if run is None:
        _refuse(console, f"No saved run #{run_id}. Run 'motodiag workflow runs' to list them.")
    return run


def _walkable(row: dict) -> dict:
    """A run's item row in the shape `_print_item` and the engine read."""
    item = dict(row)
    tools = item.get("tools_needed")
    item["tools_needed"] = json.loads(tools) if tools else []
    if item.get("instruction_text") is None:
        item["instruction_text"] = "(This item has been removed from the template.)"
    return item


def _saver(run_id: int):
    def save(item: dict, result: StepResult) -> None:
        run_repo.record_result(
            run_id, item["sequence_number"], result.value,
            diagnosis=item.get("diagnosis_if_fail"), db_path=get_db_path(),
        )
    return save


def _counts(rows: list[dict]) -> str:
    results = [r["result"] for r in rows]
    return (f"{results.count('pass')} passed, {results.count('fail')} failed, "
            f"{results.count('skipped')} skipped, {results.count(None)} unanswered "
            f"of {len(rows)}")


def _walk_saved(console, run: dict, template: dict) -> None:
    """Walk the run's unanswered items, saving each answer; then offer to
    finish. End of input leaves the run unfinished, every answer kept."""
    rows = run_repo.get_run_items(run["id"], get_db_path())
    items = [_walkable(r) for r in rows if r["result"] is None]
    try:
        _walk(console, template, items, save=_saver(run["id"]))
    except click.Abort:
        console.print(
            f"\n[yellow]Run #{run['id']} is saved unfinished.[/yellow] "
            f"Resume it with: motodiag workflow resume {run['id']}"
        )
        raise SystemExit(1)
    rows = run_repo.get_run_items(run["id"], get_db_path())
    console.print()
    console.print(f"[bold]Run #{run['id']}[/bold] · {_counts(rows)}")
    for r in rows:
        if r["result"] == "fail":
            console.print(f"  [red]{r['sequence_number']}. {r['title']}[/red]"
                          + (f": {r['diagnosis']}" if r["diagnosis"] else ""))
    if click.confirm("Finish this run now?", default=True):
        _finish(console, run["id"])
    else:
        console.print(f"[dim]Finish it later with: motodiag workflow finish {run['id']}[/dim]")


def _finish(console, run_id: int) -> None:
    try:
        run_repo.finish_run(run_id, get_db_path())
    except run_repo.RunRefused as e:
        _refuse(console, str(e))
    console.print(f"[green]Run #{run_id} finished.[/green] "
                  f"Read it back with: motodiag workflow report {run_id}")


@workflow.command("start")
@click.argument("slug")
@click.option("--bike", default=None, help="Garage bike slug, e.g. 'sportster-2001'.")
@click.option("--vehicle-id", default=None, type=int, help="Garage bike id.")
@click.option("--work-order", "work_order_id", default=None, type=int,
              help="Work order id; the run is tied to it and to its bike.")
@click.option(
    "--powertrain",
    type=click.Choice(POWERTRAINS, case_sensitive=False),
    default=None,
    help="The machine's powertrain. Asked for when not given.",
)
def start_cmd(slug: str, bike: str | None, vehicle_id: int | None,
              work_order_id: int | None, powertrain: str | None) -> None:
    """Start a saved run of a template on a bike or a work order.

    Every answer is saved as it is given; a run left part-way is resumed
    with 'workflow resume'.
    """
    from motodiag.shop.work_order_repo import get_work_order

    console = get_console()
    template = _template_or_refuse(console, slug)

    vehicle = _vehicle_or_refuse(console, bike, vehicle_id)
    if work_order_id is not None:
        order = get_work_order(work_order_id, db_path=get_db_path())
        if order is None:
            _refuse(console, f"No work order #{work_order_id}.")
        if order["status"] in ("completed", "cancelled"):
            _refuse(console, f"Work order #{work_order_id} is {order['status']}; "
                             "a run cannot be added to it.")
        if vehicle is not None and vehicle["id"] != order["vehicle_id"]:
            _refuse(console, f"Work order #{work_order_id} is for bike #{order['vehicle_id']}, "
                             f"not bike #{vehicle['id']}.")
        if vehicle is None:
            vehicle = _vehicle_or_refuse(console, None, order["vehicle_id"])
    if vehicle is None:
        _refuse(console, "A saved run is tied to a bike or a work order: give --bike, "
                         "--vehicle-id or --work-order. 'motodiag workflow run' walks a "
                         "template without saving.")

    if powertrain is None:
        powertrain = click.prompt(
            "Powertrain", type=click.Choice(POWERTRAINS, case_sensitive=False),
        )
    powertrain = powertrain.lower()
    covers = template["applicable_powertrains"]
    if powertrain not in covers:
        _refuse(console, f"{slug} covers {', '.join(covers)}, not {powertrain}.")
    stored = vehicle.get("powertrain")
    label = f"{vehicle['year']} {vehicle['make']} {vehicle['model']}"
    if stored and stored != powertrain:
        remedy = bike or f"{vehicle['model']}-{vehicle['year']}".lower()
        console.print(f"[red]Bike #{vehicle['id']} ({label}) is stored as {stored}, "
                      f"not {powertrain}. Nothing was saved.[/red]")
        console.print(f"If the bike is {powertrain}: motodiag garage update "
                      f"--bike '{remedy}' --powertrain {powertrain}")
        raise SystemExit(1)

    items = get_checklist_items(template["id"], get_db_path())
    run_id = run_repo.start_run(template, items, vehicle["id"], powertrain,
                                work_order_id=work_order_id, db_path=get_db_path())
    if not stored:
        # Phase 360 (F174), the operator's (ii): the bike had no powertrain
        # on record, and the mechanic has just stated one.
        from motodiag.vehicles.registry import update_vehicle
        update_vehicle(vehicle["id"], {"powertrain": powertrain}, db_path=get_db_path())
        console.print(f"Bike #{vehicle['id']} had no powertrain on record; stored as "
                      f"{powertrain}, as stated.")
    console.print()
    console.print(f"[bold]{template['name']}[/bold]")
    console.print(f"[dim]Run #{run_id} · {slug} · bike #{vehicle['id']} {label}"
                  + (f" · work order #{work_order_id}" if work_order_id else "")
                  + f" · for {powertrain} · {len(items)} items[/dim]")
    _walk_saved(console, _run_or_refuse(console, run_id), template)


@workflow.command("resume")
@click.argument("run_id", type=int)
def resume_cmd(run_id: int) -> None:
    """Carry on with a saved run's unanswered items."""
    console = get_console()
    run = _run_or_refuse(console, run_id)
    if run["status"] == "complete":
        _refuse(console, f"Run #{run_id} is finished. Read it back with: "
                         f"motodiag workflow report {run_id}")
    from motodiag.workflows import get_template
    template = get_template(run["template_id"], get_db_path())
    console.print()
    console.print(f"[bold]{run['template_name']}[/bold]")
    console.print(f"[dim]Run #{run_id} · {run['template_slug']} · bike #{run['vehicle_id']} "
                  f"{_bike_label(run)} · for {run['powertrain']}[/dim]")
    _walk_saved(console, run, template)


@workflow.command("record")
@click.argument("run_id", type=int)
@click.argument("item", type=int)
@click.argument("result", type=click.Choice(list(_RESULT_WORDS), case_sensitive=False))
@click.option("--notes", default=None, help="What the mechanic saw.")
def record_cmd(run_id: int, item: int, result: str, notes: str | None) -> None:
    """Record or correct one item's result on an unfinished run."""
    console = get_console()
    _run_or_refuse(console, run_id)
    word = _RESULT_WORDS[result.lower()]
    row = next((r for r in run_repo.get_run_items(run_id, get_db_path())
                if r["sequence_number"] == item), None)
    diagnosis = row.get("diagnosis_if_fail") if row else None
    try:
        run_repo.record_result(run_id, item, word, notes=notes, diagnosis=diagnosis,
                               db_path=get_db_path())
    except run_repo.RunRefused as e:
        _refuse(console, str(e))
    console.print(f"Run #{run_id} item {item}: {word}.")
    if word == "fail" and diagnosis:
        console.print(f"  [yellow]Diagnosis:[/yellow] {diagnosis}")


@workflow.command("finish")
@click.argument("run_id", type=int)
def finish_cmd(run_id: int) -> None:
    """Finish a saved run; refused while an item is unanswered."""
    console = get_console()
    _run_or_refuse(console, run_id)
    _finish(console, run_id)


@workflow.command("runs")
@click.option("--bike", default=None, help="Only this garage bike's runs.")
@click.option("--vehicle-id", default=None, type=int, help="Only this bike id's runs.")
@click.option("--work-order", "work_order_id", default=None, type=int,
              help="Only this work order's runs.")
def runs_cmd(bike: str | None, vehicle_id: int | None, work_order_id: int | None) -> None:
    """List saved runs, newest first."""
    console = get_console()
    vehicle = _vehicle_or_refuse(console, bike, vehicle_id)
    runs = run_repo.list_runs(vehicle_id=vehicle["id"] if vehicle else None,
                              work_order_id=work_order_id, db_path=get_db_path())
    if not runs:
        console.print("[yellow]No saved runs.[/yellow]")
        return
    for r in runs:
        console.print(
            f"#{r['id']} {r['template_slug']} · bike #{r['vehicle_id']} {_bike_label(r)}"
            + (f" · work order #{r['work_order_id']}" if r["work_order_id"] else "")
            + f" · {r['powertrain']} · {r['status']} · {r['answered']}/{r['total']} answered"
            + f" · started {r['started_at']}"
        )


@workflow.command("report")
@click.argument("run_id", type=int)
def report_cmd(run_id: int) -> None:
    """Read a saved run back: its bike, status and every item's result."""
    console = get_console()
    run = _run_or_refuse(console, run_id)
    rows = run_repo.get_run_items(run_id, get_db_path())
    console.print()
    console.print(f"[bold]Run #{run_id} · {run['template_name']}[/bold]")
    console.print(f"{run['template_slug']} · bike #{run['vehicle_id']} {_bike_label(run)}"
                  + (f" · work order #{run['work_order_id']}" if run["work_order_id"] else "")
                  + f" · for {run['powertrain']}")
    console.print(f"Status: {run['status']} · started {run['started_at']}"
                  + (f" · finished {run['finished_at']}" if run["finished_at"] else ""))
    for r in rows:
        flag = "" if r["required"] else " (optional)"
        console.print(f"{r['sequence_number']}. {r['title']}{flag}: {r['result'] or 'unanswered'}")
        if r["notes"]:
            console.print(f"   Notes: {r['notes']}")
        if r["diagnosis"]:
            console.print(f"   Diagnosis: {r['diagnosis']}")
    console.print(_counts(rows))
