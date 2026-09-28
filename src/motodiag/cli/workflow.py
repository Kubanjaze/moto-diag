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

**On provenance** (the 244V rule): the content behind these screens is
authored per item, and every figure an item states cites the document it
came from, in the item's own description and instruction text. Where no
document sets a figure — the leak-down percentage, per Phase 259's census
of the research library — the item says where the figure belongs and
invents nothing. Nothing in this module computes; it reads and prints.
"""

from __future__ import annotations

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
    run = checklist_workflow(template, items)
    console.print()
    console.print(f"[bold]{template['name']}[/bold]")
    console.print(f"[dim]{slug} · for {powertrain} · {len(items)} items[/dim]")

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
        run.report_result(_ANSWERS[answer.lower()])
        if answer.lower() == "f" and item.get("diagnosis_if_fail"):
            console.print(f"  [yellow]Diagnosis:[/yellow] {item['diagnosis_if_fail']}")

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
