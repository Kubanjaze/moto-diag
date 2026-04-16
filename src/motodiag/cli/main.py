"""MotoDiag CLI — main entry point."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from motodiag import __version__, __app_name__

console = Console()


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show version and exit.")
@click.pass_context
def cli(ctx: click.Context, version: bool) -> None:
    """MotoDiag — AI-powered motorcycle diagnostic tool.

    Diagnose issues, look up fault codes, and troubleshoot motorcycles
    with AI-assisted guidance. Built for mechanics, by mechanics.
    """
    if version:
        console.print(f"[bold]{__app_name__}[/bold] v{__version__}")
        return

    if ctx.invoked_subcommand is None:
        _show_welcome()


def _show_welcome() -> None:
    """Show welcome screen with available commands."""
    console.print()
    console.print(
        Panel(
            f"[bold yellow]MotoDiag[/bold yellow] v{__version__}\n"
            "[dim]AI-powered motorcycle diagnostic tool[/dim]\n\n"
            "Built for Harley-Davidson, Honda, Yamaha, Kawasaki, Suzuki\n"
            "Late 90s sport bikes • Early 2000s • All-era Harleys",
            title="🔧 MotoDiag",
            border_style="yellow",
        )
    )

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Command", style="green")
    table.add_column("Description")
    table.add_row("diagnose", "Start an interactive diagnostic session")
    table.add_row("code", "Look up a fault code (e.g., P0115)")
    table.add_row("garage", "Manage your vehicle garage")
    table.add_row("history", "Browse past diagnostic sessions")
    table.add_row("config", "Show or inspect configuration")
    table.add_row("info", "Show system info and package status")
    console.print(table)
    console.print("\n[dim]Run 'motodiag <command> --help' for details[/dim]\n")


@cli.command()
def info() -> None:
    """Show system info, installed packages, and track status."""
    table = Table(title="MotoDiag System Info", show_header=True, header_style="bold")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")

    # Check which optional packages are available
    packages = {
        "core": ("motodiag.core.config", "Settings, database, models"),
        "vehicles": ("motodiag.vehicles", "Vehicle registry"),
        "knowledge": ("motodiag.knowledge", "DTC codes, symptoms, known issues"),
        "engine": ("motodiag.engine", "AI diagnostic engine"),
        "cli": ("motodiag.cli", "Terminal interface"),
        "hardware": ("motodiag.hardware", "OBD adapter interface"),
        "advanced": ("motodiag.advanced", "Fleet, maintenance, prediction"),
        "api": ("motodiag.api", "REST API"),
    }

    for name, (module_path, desc) in packages.items():
        try:
            __import__(module_path)
            table.add_row(f"{name} — {desc}", "✓ installed")
        except ImportError:
            table.add_row(f"{name} — {desc}", "✗ missing")

    # Check optional dependencies
    console.print(table)
    console.print()

    opt_deps = {
        "anthropic": "AI Engine (Claude API)",
        "fastapi": "REST API",
        "serial": "Hardware (pyserial)",
    }
    dep_table = Table(title="Optional Dependencies", show_header=True, header_style="bold")
    dep_table.add_column("Package", style="cyan")
    dep_table.add_column("Purpose")
    dep_table.add_column("Status", style="green")

    for pkg, purpose in opt_deps.items():
        try:
            __import__(pkg)
            dep_table.add_row(pkg, purpose, "✓ installed")
        except ImportError:
            dep_table.add_row(pkg, purpose, "— not installed")

    console.print(dep_table)


@cli.group()
def config() -> None:
    """Show or inspect configuration settings."""
    pass


@config.command("show")
def config_show() -> None:
    """Display all current configuration values."""
    from motodiag.core.config import get_settings

    settings = get_settings()
    table = Table(title="Configuration", show_header=True, header_style="bold")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    for key, value in settings.model_dump().items():
        # Mask API key
        display = "****" + str(value)[-4:] if "api_key" in key and value else str(value)
        table.add_row(key, display)

    console.print(table)


@config.command("paths")
def config_paths() -> None:
    """Show data and output directory paths with existence status."""
    from pathlib import Path
    from motodiag.core.config import get_settings

    settings = get_settings()
    table = Table(title="Directory Paths", show_header=True, header_style="bold")
    table.add_column("Directory", style="cyan")
    table.add_column("Path")
    table.add_column("Exists", style="green")

    dirs = {
        "Data": settings.data_dir,
        "Data / DTC Codes": str(Path(settings.data_dir) / "dtc_codes"),
        "Data / Vehicles": str(Path(settings.data_dir) / "vehicles"),
        "Data / Knowledge": str(Path(settings.data_dir) / "knowledge"),
        "Output": settings.output_dir,
        "Database": settings.db_path,
    }

    for name, path in dirs.items():
        exists = Path(path).exists()
        status = "[green]yes[/green]" if exists else "[red]no[/red]"
        table.add_row(name, path, status)

    console.print(table)


@config.command("init")
def config_init() -> None:
    """Create all required data directories."""
    from motodiag.core.config import ensure_directories

    results = ensure_directories()
    for name, created in results.items():
        if created:
            console.print(f"  [green]Created[/green] {name}/")
        else:
            console.print(f"  [dim]Exists[/dim]  {name}/")
    console.print("[green]All directories ready.[/green]")


# Placeholder subcommands — will be implemented in later phases
@cli.command()
def diagnose() -> None:
    """Start an interactive diagnostic session. (Coming in Phase 29+)"""
    console.print("[yellow]Diagnostic engine coming in Track C (Phases 29-45).[/yellow]")
    console.print("For now, use [bold]motodiag info[/bold] to check system status.")


@cli.command()
@click.argument("dtc_code", required=False)
@click.option("--make", "-m", help="Filter by manufacturer (e.g., Harley-Davidson)")
def code(dtc_code: str | None, make: str | None) -> None:
    """Look up a diagnostic trouble code (e.g., P0115)."""
    from motodiag.core.database import init_db
    from motodiag.knowledge.dtc_repo import get_dtc, search_dtcs

    init_db()

    if not dtc_code:
        console.print("[yellow]Usage: motodiag code P0115[/yellow]")
        console.print("[dim]  --make / -m  Filter by manufacturer[/dim]")
        return

    result = get_dtc(dtc_code, make=make)
    if not result:
        console.print(f"[red]DTC '{dtc_code}' not found.[/red]")
        console.print("[dim]Try loading DTC data: motodiag code --load[/dim]")
        return

    # Display formatted DTC info
    severity_colors = {
        "critical": "red bold", "high": "red", "medium": "yellow",
        "low": "green", "info": "dim",
    }
    sev = result.get("severity", "medium")
    sev_style = severity_colors.get(sev, "white")

    console.print()
    console.print(Panel(
        f"[bold]{result['code']}[/bold] — {result['description']}\n\n"
        f"Category: [cyan]{result.get('category', 'unknown')}[/cyan]\n"
        f"Severity: [{sev_style}]{sev.upper()}[/{sev_style}]\n"
        f"Make: {result.get('make') or 'Generic (all makes)'}",
        title=f"DTC {result['code']}",
        border_style="yellow",
    ))

    causes = result.get("common_causes", [])
    if causes:
        console.print("\n[bold]Common Causes:[/bold]")
        for i, cause in enumerate(causes, 1):
            console.print(f"  {i}. {cause}")

    fix = result.get("fix_summary")
    if fix:
        console.print(f"\n[bold]Fix:[/bold] {fix}")
    console.print()


@cli.command()
@click.argument("query")
@click.option("--make", "-m", help="Filter by manufacturer")
def search(query: str, make: str | None) -> None:
    """Search across all knowledge stores (DTCs, symptoms, known issues)."""
    from motodiag.core.database import init_db
    from motodiag.core.search import search_all

    init_db()
    results = search_all(query, make=make)

    if results["total"] == 0:
        console.print(f"[yellow]No results for '{query}'.[/yellow]")
        return

    console.print(f"\n[bold]Search results for '{query}'[/bold] ({results['total']} total)\n")

    if results["dtc_codes"]:
        console.print(f"[bold cyan]DTC Codes ({len(results['dtc_codes'])})[/bold cyan]")
        for dtc in results["dtc_codes"][:5]:
            sev = dtc.get("severity", "")
            console.print(f"  [green]{dtc['code']}[/green] — {dtc['description']} [{sev}]")
        console.print()

    if results["symptoms"]:
        console.print(f"[bold cyan]Symptoms ({len(results['symptoms'])})[/bold cyan]")
        for s in results["symptoms"][:5]:
            console.print(f"  {s['name']} — {s['description']} [{s['category']}]")
        console.print()

    if results["known_issues"]:
        console.print(f"[bold cyan]Known Issues ({len(results['known_issues'])})[/bold cyan]")
        for issue in results["known_issues"][:5]:
            make_str = issue.get("make") or "All"
            yrs = ""
            if issue.get("year_start"):
                yrs = f" ({issue['year_start']}-{issue.get('year_end', 'present')})"
            console.print(f"  [{issue.get('severity', 'medium')}] {issue['title']} — {make_str}{yrs}")
        console.print()

    if results["vehicles"]:
        console.print(f"[bold cyan]Vehicles ({len(results['vehicles'])})[/bold cyan]")
        for v in results["vehicles"][:5]:
            console.print(f"  {v['year']} {v['make']} {v['model']}")
        console.print()


@cli.command()
def garage() -> None:
    """Manage your vehicle garage. (Coming in Phase 04)"""
    console.print("[yellow]Vehicle garage coming in Phase 04.[/yellow]")


@cli.command()
def history() -> None:
    """Browse past diagnostic sessions. (Coming in Phase 07)"""
    console.print("[yellow]Session history coming in Phase 07.[/yellow]")


if __name__ == "__main__":
    cli()
