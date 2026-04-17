"""Knowledge base browser CLI — `motodiag kb ...` subcommands.

Phase 128: attach a `kb` click.group to the top-level CLI with five
read-only subcommands for browsing the `known_issues` table:

    motodiag kb list                                # rich table, newest first
    motodiag kb list --make Honda --severity high   # structured filters
    motodiag kb show 42                             # full issue detail panel
    motodiag kb search "stator"                     # free-text LIKE search
    motodiag kb by-symptom "won't start"            # symptom-array match
    motodiag kb by-code P0562                       # DTC-code array match

All five subcommands are pure reads over the Phase 08 repo functions —
no AI, no writes, no mutation. Editing the knowledge base is done via
the JSON loader (Phase 05/08) so content curation stays in source
control, not in the CLI.

Wiring: `register_kb(cli)` is called from `cli/main.py` after
`register_quick(cli)`. Tests exercise via Click's CliRunner.
"""

from __future__ import annotations

from typing import Any, Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from motodiag.cli.theme import get_console, severity_style
from motodiag.core.database import init_db
from motodiag.knowledge.issues_repo import (
    find_issues_by_dtc,
    find_issues_by_symptom,
    get_known_issue,
    search_known_issues,
    search_known_issues_text,
)

# Maximum title width in the list/search/by-* tables before truncation.
# 60 chars keeps the Rich table readable on an 80-col terminal while still
# giving the title enough room to convey the issue without ambiguity.
_TITLE_TRUNC = 60


def _year_range_str(row: dict) -> str:
    """Format year_start/year_end into a compact display string.

    Rules:
        - both set → "2001-2017"
        - only year_start → "2001+"
        - only year_end → "up to 2017"  (rare — exposed defensively)
        - neither → "any"
    """
    ys = row.get("year_start")
    ye = row.get("year_end")
    if ys and ye:
        return f"{ys}-{ye}"
    if ys:
        return f"{ys}+"
    if ye:
        return f"up to {ye}"
    return "any"


def _truncate(text: Optional[str], width: int = _TITLE_TRUNC) -> str:
    """Truncate `text` to `width` chars with ellipsis suffix. None → '-'.

    Preserves the Phase 123 truncation semantics used in `diagnose list`:
    strings at exactly `width` are kept whole; anything longer loses the
    tail and gains `...`.
    """
    if text is None:
        return "-"
    s = str(text)
    if len(s) <= width:
        return s
    return s[: width - 3] + "..."


def _render_issue_table(
    rows: list[dict],
    console: Console,
    title: str,
) -> None:
    """Render a list of issue dicts as a Rich table.

    Columns: ID, Make, Model, Years, Severity, Title (trunc), # fixes.
    The "# fixes" column shows `len(parts_needed)` as a rough indicator of
    how actionable the entry is — a title alone doesn't tell a mechanic
    whether parts are listed.
    """
    table = Table(title=title)
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Make", style="green")
    table.add_column("Model")
    table.add_column("Years", style="magenta")
    table.add_column("Severity")
    table.add_column("Title", overflow="fold")
    table.add_column("# fixes", justify="right", style="dim")

    for row in rows:
        parts = row.get("parts_needed") or []
        sev = row.get("severity")
        sev_text = sev if sev else "-"
        # Phase 129: severity color from the shared theme map so a future
        # theme swap is a one-file edit.
        sev_style = severity_style(sev)
        table.add_row(
            str(row.get("id", "?")),
            row.get("make") or "all",
            row.get("model") or "all",
            _year_range_str(row),
            f"[{sev_style}]{sev_text}[/{sev_style}]",
            _truncate(row.get("title")),
            str(len(parts)),
        )
    console.print(table)


def _render_bullet_list(
    console: Console,
    heading: str,
    items: Optional[list[Any]],
    empty_text: str = "(none recorded)",
) -> None:
    """Print a bold heading, then either bulleted items or a dim empty marker.

    Used by `_render_issue_detail` so every subsection has consistent
    rendering for None / [] / populated cases — no "null" strings in the
    output, no silent omission of empty fields.
    """
    console.print(f"[bold]{heading}[/bold]")
    if not items:
        console.print(f"  [dim]{empty_text}[/dim]")
        return
    for item in items:
        console.print(f"  • {item}")


def _render_issue_detail(row: dict, console: Console) -> None:
    """Render a single known_issue dict in full detail.

    Layout:
        - Header panel:       id, make, model, year range, severity
        - Description:        free paragraph
        - Symptoms:           bulleted list
        - DTC codes:          bulleted list
        - Causes:             bulleted list
        - Fix procedure:      free paragraph
        - Parts needed:       bulleted list
        - Estimated hours:    callout (bottom)

    Every subsection handles empty/None gracefully so entries with sparse
    knowledge-base data (e.g., no DTC codes, no estimated hours) still
    render cleanly instead of printing "None" or crashing.
    """
    issue_id = row.get("id", "?")
    title = row.get("title") or "(untitled)"
    make = row.get("make") or "all makes"
    model = row.get("model") or "all models"
    years = _year_range_str(row)
    severity_raw = row.get("severity")
    severity_text = severity_raw if severity_raw else "-"
    # Phase 129: severity color from the shared theme map.
    severity_rich = (
        f"[{severity_style(severity_raw)}]{severity_text}"
        f"[/{severity_style(severity_raw)}]"
    )

    header = (
        f"[bold]Issue #{issue_id}[/bold]   [dim]severity:[/dim] {severity_rich}\n"
        f"[bold yellow]{title}[/bold yellow]\n"
        f"[dim]{make} {model}   {years}[/dim]"
    )
    console.print(Panel(header, title="Known Issue", border_style="cyan"))

    description = row.get("description")
    if description:
        console.print("[bold]Description[/bold]")
        console.print(f"  {description}\n")
    else:
        console.print("[bold]Description[/bold]")
        console.print("  [dim](none recorded)[/dim]\n")

    _render_bullet_list(console, "Symptoms", row.get("symptoms"))
    console.print()
    _render_bullet_list(console, "DTC Codes", row.get("dtc_codes"))
    console.print()
    _render_bullet_list(console, "Common causes", row.get("causes"))
    console.print()

    fix_procedure = row.get("fix_procedure")
    console.print("[bold]Fix procedure[/bold]")
    if fix_procedure:
        console.print(f"  {fix_procedure}")
    else:
        console.print("  [dim](none recorded)[/dim]")
    console.print()

    _render_bullet_list(console, "Parts needed", row.get("parts_needed"))
    console.print()

    hours = row.get("estimated_hours")
    if hours is not None:
        console.print(f"[bold]Estimated labor:[/bold] {hours} hours")
    else:
        console.print("[bold]Estimated labor:[/bold] [dim](not recorded)[/dim]")


# --- Phase 132: Issue formatters (pure dict → str) ------------------------
#
# Mirror of Phase 126's _format_session_md for the known-issues table so
# `kb show` can reuse the shared HTML/PDF pipeline in cli/export.py.
# Every section gracefully handles None / empty lists to keep sparse
# knowledge-base entries (no parts, no DTC codes, no estimated hours)
# rendering cleanly.


def _format_issue_md(row: dict) -> str:
    """Render a known_issue dict as GitHub-flavored markdown.

    Structure:
        # {title}
        ## Overview
        - Make: ...
        - Model: ...
        - Year range: ...
        - Severity: ...
        ## Description
        {paragraph}
        ## Symptoms
        - ...
        ## Fault Codes
        - `...`
        ## Causes
        - ...
        ## Fix Procedure
        {paragraph}
        ## Parts Needed
        - ...
        ## Labor Hours
        {hours} hours
    """
    title = row.get("title") or "(untitled)"
    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")

    # --- Overview
    lines.append("## Overview")
    lines.append("")
    lines.append(f"- Make: {row.get('make') or 'all makes'}")
    lines.append(f"- Model: {row.get('model') or 'all models'}")
    lines.append(f"- Year range: {_year_range_str(row)}")
    sev = row.get("severity") or "-"
    lines.append(f"- Severity: {sev}")
    if row.get("id") is not None:
        lines.append(f"- Issue ID: {row.get('id')}")
    lines.append("")

    # --- Description (optional)
    description = row.get("description")
    if description:
        lines.append("## Description")
        lines.append("")
        lines.append(str(description))
        lines.append("")

    # --- Symptoms
    symptoms = row.get("symptoms") or []
    if symptoms:
        lines.append("## Symptoms")
        lines.append("")
        for s in symptoms:
            lines.append(f"- {s}")
        lines.append("")

    # --- Fault Codes
    dtc_codes = row.get("dtc_codes") or []
    if dtc_codes:
        lines.append("## Fault Codes")
        lines.append("")
        for c in dtc_codes:
            lines.append(f"- `{c}`")
        lines.append("")

    # --- Causes
    causes = row.get("causes") or []
    if causes:
        lines.append("## Causes")
        lines.append("")
        for c in causes:
            lines.append(f"- {c}")
        lines.append("")

    # --- Fix Procedure
    fix_procedure = row.get("fix_procedure")
    if fix_procedure:
        lines.append("## Fix Procedure")
        lines.append("")
        lines.append(str(fix_procedure))
        lines.append("")

    # --- Parts Needed
    parts = row.get("parts_needed") or []
    if parts:
        lines.append("## Parts Needed")
        lines.append("")
        for p in parts:
            lines.append(f"- {p}")
        lines.append("")

    # --- Labor Hours
    hours = row.get("estimated_hours")
    if hours is not None:
        lines.append("## Labor Hours")
        lines.append("")
        lines.append(f"{hours} hours")
        lines.append("")

    return "\n".join(lines)


def _format_issue_text(row: dict) -> str:
    """Render a known_issue dict as plain text.

    v1 implementation: reuses the markdown output. The markdown syntax
    used (``# heading``, ``- bullet``, backtick code) is already
    human-readable in a monospace terminal / email client, so stripping
    the syntax isn't necessary to be useful. A future phase can swap in
    a dedicated plain-text formatter if customer feedback calls for it.
    """
    return _format_issue_md(row)


# --- Command registration ---


def register_kb(cli_group: click.Group) -> None:
    """Attach the `kb` subgroup and its five subcommands to the top-level CLI.

    Called from `cli/main.py` after `register_quick(cli)`. Keeping the
    wiring explicit (vs auto-discovery) mirrors the Phase 123/124/125
    pattern and makes ordering (quick depends on diagnose, kb depends on
    nothing) auditable in one place.
    """

    @cli_group.group("kb")
    def kb() -> None:
        """Browse the knowledge base — list, show, search known issues."""

    @kb.command("list")
    @click.option("--make", default=None,
                  help="Filter by manufacturer (case-insensitive substring).")
    @click.option("--model", "model_", default=None,
                  help="Filter by model (case-insensitive substring).")
    @click.option("--year", default=None, type=int,
                  help="Filter to issues covering this model year.")
    @click.option("--severity", default=None,
                  type=click.Choice(
                      ["critical", "high", "medium", "low", "info"],
                      case_sensitive=False,
                  ),
                  help="Filter by severity level.")
    @click.option("--symptom", default=None,
                  help="Filter to issues with a symptom containing this text.")
    @click.option("--limit", default=50, type=int, show_default=True,
                  help="Cap number of rows returned.")
    def kb_list(
        make: Optional[str],
        model_: Optional[str],
        year: Optional[int],
        severity: Optional[str],
        symptom: Optional[str],
        limit: int,
    ) -> None:
        """List known issues with optional structured filters.

        Without flags, prints the newest (by insertion-id) issues up to
        `--limit`. With flags, applies structured filtering via the
        existing `search_known_issues` function — same AND semantics as
        Phase 08.
        """
        console = get_console()
        init_db()

        # search_known_issues doesn't support a symptom filter directly
        # (that is handled by the dedicated find_issues_by_symptom function).
        # If --symptom is the only filter, route through that function;
        # otherwise apply --symptom as a post-filter after the structured
        # search. Either way the user gets one combined result.
        rows = search_known_issues(
            make=make,
            model=model_,
            year=year,
            severity=severity.lower() if severity else None,
        )
        if symptom:
            needle = symptom.lower()
            rows = [
                r for r in rows
                if any(needle in str(s).lower() for s in (r.get("symptoms") or []))
            ]

        # Apply limit after filtering so --symptom post-filter still caps
        # appropriately. Limit is int; >=1 per Click's int type.
        if len(rows) > limit:
            rows = rows[:limit]

        if not rows:
            any_filter = any(
                v is not None and v != ""
                for v in (make, model_, year, severity, symptom)
            )
            if any_filter:
                console.print("[yellow]No issues match the filters.[/yellow]")
            else:
                console.print(
                    "[yellow]No known issues in the knowledge base yet. "
                    "Load one with 'motodiag db init'.[/yellow]"
                )
            return

        _render_issue_table(rows, console, title="Known Issues")

    @kb.command("show")
    @click.argument("issue_id", type=int)
    @click.option(
        "--format", "output_format",
        type=click.Choice(
            ["terminal", "txt", "md", "html", "pdf"],
            case_sensitive=False,
        ),
        default="terminal",
        show_default=True,
        help=(
            "Output format. 'terminal' preserves the Phase 128 Rich rendering; "
            "'html' / 'pdf' (Phase 132) require the motodiag[export] extra."
        ),
    )
    @click.option(
        "--output", "output_path",
        type=click.Path(dir_okay=False, writable=True, resolve_path=False),
        default=None,
        help=(
            "Write to PATH instead of stdout. Ignored with --format terminal. "
            "Required for --format pdf."
        ),
    )
    @click.option(
        "--yes", "-y", "assume_yes",
        is_flag=True, default=False,
        help="Skip overwrite confirmation when --output points to an existing file.",
    )
    def kb_show(
        issue_id: int,
        output_format: str,
        output_path: Optional[str],
        assume_yes: bool,
    ) -> None:
        """Render the full detail of a single known issue by ID.

        Without flags, renders a Rich Panel to the terminal (Phase 128 behavior).
        With --format txt|md, prints to stdout or writes to --output PATH.
        With --format html|pdf (Phase 132), converts via the shared export
        pipeline. PDF output requires --output (binary to stdout is useless).
        """
        console = get_console()
        init_db()

        row = get_known_issue(issue_id)
        if row is None:
            raise click.ClickException(f"Known issue #{issue_id} not found.")

        fmt = output_format.lower()

        # Phase 128 terminal path — unchanged behavior.
        if fmt == "terminal":
            if output_path:
                console.print(
                    "[yellow]⚠ --output ignored with --format terminal. "
                    "Use --format txt|md|html|pdf to write a file.[/yellow]"
                )
            _render_issue_detail(row, console)
            return

        # Lazy imports so core users never pay for the markdown/xhtml2pdf
        # import cost when they only ever use the terminal path.
        title = row.get("title") or f"Known Issue #{issue_id}"

        if fmt == "txt":
            content = _format_issue_text(row)
        elif fmt == "md":
            content = _format_issue_md(row)
        elif fmt == "html":
            from motodiag.cli.export import format_as_html
            content = format_as_html(
                title=title,
                body_md=_format_issue_md(row),
            )
        elif fmt == "pdf":
            if not output_path:
                raise click.ClickException(
                    "PDF format requires --output PATH. "
                    "Example: --format pdf --output issue.pdf"
                )
            from pathlib import Path
            from motodiag.cli.export import format_as_pdf, write_binary
            pdf_bytes = format_as_pdf(
                title=title,
                body_md=_format_issue_md(row),
            )
            write_binary(
                Path(output_path),
                pdf_bytes,
                overwrite_confirmed=assume_yes,
            )
            click.echo(f"Saved to {output_path}")
            return
        else:  # pragma: no cover — click.Choice guards this
            raise click.ClickException(f"Unknown format: {output_format}")

        if output_path:
            # Reuse Phase 126's writer for consistent overwrite/parent-dir
            # handling. The md/html/txt outputs are all text so the text
            # writer is the right tool.
            from motodiag.cli.diagnose import _write_report_to_file
            _write_report_to_file(
                output_path, content, overwrite_confirmed=assume_yes,
            )
            click.echo(f"Saved to {output_path}")
        else:
            click.echo(content, nl=False)

    @kb.command("search")
    @click.argument("query")
    @click.option("--limit", default=50, type=int, show_default=True,
                  help="Cap number of rows returned.")
    def kb_search(query: str, limit: int) -> None:
        """Free-text search across title, description, and symptoms.

        Case-insensitive LIKE. Empty query is rejected — searching for
        '%%' would dump the whole knowledge base with no signal.
        """
        console = get_console()
        init_db()

        if not query or not query.strip():
            raise click.ClickException(
                "Search query is empty. Provide a non-whitespace term "
                "(e.g. 'stator', 'regulator', 'won't start')."
            )

        rows = search_known_issues_text(query, limit=limit)
        if not rows:
            console.print(
                f"[yellow]No issues mention {query!r}.[/yellow]"
            )
            return

        _render_issue_table(
            rows, console, title=f"Known Issues matching {query!r}",
        )

    @kb.command("by-symptom")
    @click.argument("symptom")
    def kb_by_symptom(symptom: str) -> None:
        """Find known issues that list the given symptom in their symptoms array."""
        console = get_console()
        init_db()

        rows = find_issues_by_symptom(symptom)
        if not rows:
            console.print(
                f"[yellow]No issues list the symptom {symptom!r}.[/yellow]"
            )
            return

        _render_issue_table(
            rows, console, title=f"Issues with symptom {symptom!r}",
        )

    @kb.command("by-code")
    @click.argument("dtc")
    def kb_by_code(dtc: str) -> None:
        """Find known issues that reference the given DTC code (e.g. P0562).

        DTC input is force-uppercased before the lookup — mechanics in
        the field frequently type codes in lowercase, and the
        knowledge-base JSON stores them uppercase by convention.
        """
        console = get_console()
        init_db()

        code = (dtc or "").strip().upper()
        if not code:
            raise click.ClickException("DTC code is empty.")

        rows = find_issues_by_dtc(code)
        if not rows:
            console.print(
                f"[yellow]No issues reference DTC {code!r}.[/yellow]"
            )
            return

        _render_issue_table(
            rows, console, title=f"Issues for DTC {code}",
        )
