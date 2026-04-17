"""Fault code lookup CLI orchestration.

Phase 124: turns `motodiag code <code>` into a fast lookup that resolves a
DTC ("P0115", "C1234", Kawasaki dealer codes, Zero HV_ codes...) into plain
English output via `knowledge.dtc_repo` + `engine.fault_codes.classify_code`.

Default mode is DB-only (zero AI cost). The `--explain` flag runs
`FaultCodeInterpreter` for AI-generated root-cause analysis with the same
tier gates as Phase 123 (`diagnose`). `--category` lists DTCs in a given
category (leverages Phase 111's dtc_category_meta taxonomy).

All AI calls go through an injectable `_default_interpret_fn` so tests never
burn tokens.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from motodiag.cli.theme import get_console, status as theme_status, severity_style
from motodiag.cli.diagnose import (
    _resolve_model,
    _load_vehicle,
    _load_known_issues,
    _parse_symptoms,
)
from motodiag.cli.completion import complete_dtc_code
from motodiag.cli.subscription import current_tier
from motodiag.core.database import init_db
from motodiag.engine.fault_codes import classify_code
from motodiag.knowledge.dtc_repo import (
    get_dtc,
    get_dtcs_by_category,
)

# Engine imports are lazy inside `_default_interpret_fn` to keep CLI import
# fast and to make mocking via the `interpret_fn` parameter straightforward.


# --- Severity colors for rich rendering ---
#
# Phase 129: the canonical severity → style map lives in
# :mod:`motodiag.cli.theme`. We re-export the ``severity_style``
# helper above so existing call sites keep working unchanged.


# --- Core lookup helpers ---


def _lookup_local(
    code: str,
    make: Optional[str],
    db_path: Optional[str] = None,
) -> Optional[dict]:
    """Resolve a DTC row from the local DB.

    Fallback chain:
      1. If `make` provided, try make-specific row (handled by `get_dtc`).
      2. If no match and `make` was provided, retry with `make=None` for the
         generic row explicitly (defensive — `get_dtc` already falls back to
         generic then any-match, but this keeps the behavior explicit if the
         repo layer changes).
      3. Return None if nothing matches.
    """
    row = get_dtc(code, make=make, db_path=db_path)
    if row is not None:
        return row
    if make is not None:
        row = get_dtc(code, make=None, db_path=db_path)
        if row is not None:
            return row
    return None


def _classify_fallback(code: str, make: Optional[str]) -> dict:
    """Build a dtc_row-shaped dict from the classify_code heuristic.

    Used when the DB has no entry for the code. Gives the mechanic at least a
    code format + system description. Marked with `source="classify_fallback"`
    so the renderer can show a yellow "no DB entry" banner.
    """
    code_format, description = classify_code(code, make)
    return {
        "code": code.upper(),
        "code_format": code_format,
        "description": description,
        "source": "classify_fallback",
        "category": None,
        "severity": None,
        "make": make,
        "common_causes": [],
        "fix_summary": None,
    }


# --- Default production interpret caller ---


def _default_interpret_fn(
    code: str,
    vehicle: dict,
    symptoms: list[str],
    ai_model: str,
    known_issues: Optional[list[dict]],
    offline: bool = False,
) -> tuple[Any, Any]:
    """Default production implementation — calls FaultCodeInterpreter.interpret().

    Separate from orchestration so tests inject a mock without needing the
    anthropic SDK installed. Returns (FaultCodeResult, TokenUsage).

    Phase 131: ``offline`` passes through to the engine's cache-first
    path.
    """
    from motodiag.engine.client import DiagnosticClient
    from motodiag.engine.fault_codes import FaultCodeInterpreter

    client = DiagnosticClient(model=ai_model)
    interpreter = FaultCodeInterpreter(client)
    return interpreter.interpret(
        code=code,
        make=vehicle["make"],
        model_name=vehicle["model"],
        year=vehicle["year"],
        symptoms=symptoms or None,
        mileage=vehicle.get("mileage"),
        known_issues=known_issues,
        ai_model=ai_model,
        offline=offline,
    )


# --- Orchestration ---


def _run_explain(
    vehicle: dict,
    code: str,
    symptoms: list[str],
    ai_model: str,
    db_path: Optional[str] = None,
    interpret_fn: Optional[Callable] = None,
    offline: bool = False,
) -> tuple[Any, Any]:
    """Load known issues for the bike, then call the interpreter.

    Returns (FaultCodeResult, TokenUsage).

    Phase 131: ``offline`` passes through to the interpret call. Legacy
    test doubles that don't accept ``offline=`` still work via the
    TypeError fallback — the same pattern as ``_run_quick``.
    """
    call = interpret_fn or _default_interpret_fn
    known = _load_known_issues(
        vehicle["make"], vehicle["model"], vehicle["year"], db_path=db_path,
    )
    try:
        return call(
            code=code,
            vehicle=vehicle,
            symptoms=symptoms,
            ai_model=ai_model,
            known_issues=known,
            offline=offline,
        )
    except TypeError:
        return call(
            code=code,
            vehicle=vehicle,
            symptoms=symptoms,
            ai_model=ai_model,
            known_issues=known,
        )


# --- Rendering ---


def _render_local(row: dict, console: Console) -> None:
    """Pretty-print a DTC row (DB-backed or classify_fallback)."""
    is_fallback = row.get("source") == "classify_fallback"

    if is_fallback:
        console.print(
            "[yellow]⚠ No DB entry — heuristic classification only[/yellow]"
        )

    sev = row.get("severity") or "unknown"
    sev_style = severity_style(sev)
    category = row.get("category") or row.get("code_format") or "unknown"
    make_str = row.get("make") or "Generic (all makes)"

    body = (
        f"[bold]{row['code']}[/bold] — {row.get('description', '')}\n\n"
        f"Category: [cyan]{category}[/cyan]\n"
        f"Severity: [{sev_style}]{str(sev).upper()}[/{sev_style}]\n"
        f"Make: {make_str}"
    )
    console.print(
        Panel(body, title=f"DTC {row['code']}", border_style="yellow")
    )

    causes = row.get("common_causes") or []
    if causes:
        console.print("\n[bold]Common causes:[/bold]")
        for i, cause in enumerate(causes, 1):
            console.print(f"  {i}. {cause}")

    fix = row.get("fix_summary")
    if fix:
        console.print(f"\n[bold]Fix:[/bold] {fix}")

    if is_fallback:
        console.print(
            "\n[dim]Tip: run with [bold]--explain[/bold] for AI root-cause analysis.[/dim]"
        )


def _render_explain(result: Any, console: Console) -> None:
    """Pretty-print a FaultCodeResult."""
    code = getattr(result, "code", "?")
    code_format = getattr(result, "code_format", "?")
    system = getattr(result, "system", "") or getattr(result, "description", "")

    header = (
        f"[bold]{code}[/bold]  "
        f"[dim]format:[/dim] {code_format}   "
        f"[dim]system:[/dim] {system}"
    )
    console.print(Panel(header, title="Fault Code Interpretation",
                        border_style="cyan"))

    if getattr(result, "safety_critical", False):
        console.print(
            "[red bold]⚠ SAFETY-CRITICAL — inspect before further use[/red bold]"
        )

    causes = getattr(result, "possible_causes", []) or []
    if causes:
        t = Table(title="Possible Causes (ranked)")
        t.add_column("#", style="cyan", justify="right")
        t.add_column("Cause", overflow="fold")
        for i, cause in enumerate(causes, 1):
            t.add_row(str(i), str(cause))
        console.print(t)

    tests = getattr(result, "tests_to_confirm", []) or []
    if tests:
        console.print("\n[bold]Tests to confirm:[/bold]")
        for test in tests:
            console.print(f"  • {test}")

    related = getattr(result, "related_symptoms", []) or []
    if related:
        console.print("\n[bold]Related symptoms:[/bold]")
        for sym in related:
            console.print(f"  • {sym}")

    steps = getattr(result, "repair_steps", []) or []
    if steps:
        console.print("\n[bold]Repair steps:[/bold]")
        for i, step in enumerate(steps, 1):
            console.print(f"  {i}. {step}")

    hours = getattr(result, "estimated_hours", None)
    cost = getattr(result, "estimated_cost", None)
    if hours is not None or cost:
        parts = []
        if hours is not None:
            parts.append(f"[bold]Labor:[/bold] {hours:.1f} hr")
        if cost:
            parts.append(f"[bold]Cost:[/bold] {cost}")
        console.print("\n" + "   ".join(parts))

    notes = getattr(result, "notes", None)
    if notes:
        console.print(Panel(notes, title="Notes", border_style="dim"))


def _render_category_list(
    rows: list[dict], console: Console, category: str,
) -> None:
    """Render a table of DTCs matching a category."""
    if not rows:
        console.print(
            f"[yellow]No DTCs found in category '{category}'.[/yellow]"
        )
        return

    t = Table(title=f"DTCs in category: {category}  ({len(rows)} found)")
    t.add_column("Code", style="cyan")
    t.add_column("Description", overflow="fold")
    t.add_column("Severity")
    t.add_column("Make")
    for row in rows:
        sev = row.get("severity") or "-"
        sev_style = severity_style(sev)
        t.add_row(
            row.get("code", "?"),
            row.get("description", "") or "-",
            f"[{sev_style}]{str(sev).upper()}[/{sev_style}]",
            row.get("make") or "Generic",
        )
    console.print(t)


# --- Click command registered in cli/main.py via register_code(cli) ---


def register_code(cli_group: click.Group) -> None:
    """Attach the `code` command to the top-level CLI.

    Single command (not a subgroup) with these mutually informed modes:
      1. `--category <cat>` — list all DTCs in a category (ignores other flags).
      2. `--explain --vehicle-id N` — AI root-cause analysis, tier-gated.
      3. Default — DB lookup with classify_code fallback.
    """

    # If a legacy `code` command is already attached (from earlier scaffolding),
    # evict it so our richer implementation owns the name.
    if "code" in cli_group.commands:
        del cli_group.commands["code"]

    @cli_group.command("code")
    @click.argument("dtc_code", required=False, shell_complete=complete_dtc_code)
    @click.option("--make", "-m", default=None,
                  help="Narrow to a manufacturer-specific DTC entry.")
    @click.option("--category", default=None,
                  help="List all DTCs in a category (skips other flags).")
    @click.option("--explain", is_flag=True,
                  help="Run AI interpretation for root-cause analysis.")
    @click.option("--vehicle-id", default=None, type=int,
                  help="Required when --explain is set.")
    @click.option("--symptoms", default=None,
                  help="Optional symptom context for --explain (comma-separated).")
    @click.option("--model", "ai_model_flag", default=None,
                  type=click.Choice(["haiku", "sonnet"], case_sensitive=False))
    @click.option("--offline", is_flag=True, default=False,
                  help="With --explain: serve from cache only; error on "
                       "cache miss. Useful for re-reading a previously "
                       "cached interpretation without internet.")
    def code(
        dtc_code: Optional[str],
        make: Optional[str],
        category: Optional[str],
        explain: bool,
        vehicle_id: Optional[int],
        symptoms: Optional[str],
        ai_model_flag: Optional[str],
        offline: bool,
    ) -> None:
        """Look up a diagnostic trouble code (e.g., P0115)."""
        console = get_console()
        init_db()

        # --- Mode 1: category list ---
        if category:
            rows = get_dtcs_by_category(category, make=make)
            _render_category_list(rows, console, category)
            return

        # --- Mode 2: AI explain ---
        if explain:
            if not dtc_code:
                raise click.ClickException(
                    "The DTC code argument is required with --explain."
                )
            if vehicle_id is None:
                raise click.ClickException(
                    "--vehicle-id is required with --explain."
                )
            vehicle = _load_vehicle(vehicle_id)
            if vehicle is None:
                raise click.ClickException(
                    f"Vehicle #{vehicle_id} not found. "
                    f"Add one first with 'garage add'."
                )

            tier = current_tier().value
            ai_model = _resolve_model(tier, ai_model_flag)
            if ai_model_flag and ai_model != ai_model_flag.lower():
                console.print(
                    "[yellow]⚠ Sonnet requires Shop tier+. "
                    "Falling back to Haiku (soft enforcement).[/yellow]"
                )

            symptom_list = _parse_symptoms(symptoms or "")
            # Phase 129: spinner during the AI interpretation.
            try:
                with theme_status("Interpreting fault code..."):
                    result, _usage = _run_explain(
                        vehicle=vehicle,
                        code=dtc_code,
                        symptoms=symptom_list,
                        ai_model=ai_model,
                        offline=offline,
                    )
            except RuntimeError as exc:
                # Phase 131: offline cache-miss path.
                console.print(f"[red]{exc}[/red]")
                raise click.exceptions.Exit(1) from exc
            _render_explain(result, console)
            return

        # --- Mode 3: default DB lookup ---
        if not dtc_code:
            raise click.ClickException(
                "A DTC code argument is required (or use --category)."
            )

        row = _lookup_local(dtc_code, make=make)
        if row is not None:
            _render_local(row, console)
            return

        # Fall back to classify heuristic
        fallback = _classify_fallback(dtc_code, make)
        _render_local(fallback, console)
