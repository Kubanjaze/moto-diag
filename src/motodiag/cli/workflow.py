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
from motodiag.workflows import (
    WorkflowCategory,
    get_checklist_items,
    get_template_by_slug,
    list_templates,
)


def register_workflow(cli: click.Group) -> None:
    """Attach the ``workflow`` command group to the main CLI group."""
    cli.add_command(workflow)


@click.group("workflow")
def workflow() -> None:
    """Browse workflow templates (PPI, winterization, service protocols)."""


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
    table.add_column("Slug", style="green")
    table.add_column("Category")
    table.add_column("Name")
    table.add_column("Powertrains")
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
    template = get_template_by_slug(slug, get_db_path())
    if template is None:
        console.print(f"[red]No workflow template with slug '{slug}'.[/red]")
        console.print("[dim]Run 'motodiag workflow list' to see what exists.[/dim]")
        raise SystemExit(1)

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
        if item.get("diagnosis_if_fail"):
            console.print(f"  [yellow]If fail:[/yellow] {item['diagnosis_if_fail']}")
        if item.get("tools_needed"):
            console.print(f"  [dim]Tools: {', '.join(item['tools_needed'])}[/dim]")
    console.print()
