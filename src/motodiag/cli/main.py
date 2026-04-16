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


# Placeholder subcommands — will be implemented in later phases
@cli.command()
def diagnose() -> None:
    """Start an interactive diagnostic session. (Coming in Phase 29+)"""
    console.print("[yellow]Diagnostic engine coming in Track C (Phases 29-45).[/yellow]")
    console.print("For now, use [bold]motodiag info[/bold] to check system status.")


@cli.command()
@click.argument("dtc_code", required=False)
def code(dtc_code: str | None) -> None:
    """Look up a diagnostic trouble code. (Coming in Phase 05)"""
    if dtc_code:
        console.print(f"[yellow]DTC lookup for '{dtc_code}' coming in Phase 05.[/yellow]")
    else:
        console.print("[yellow]Usage: motodiag code P0115[/yellow]")


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
