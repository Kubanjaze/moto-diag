"""MotoDiag CLI — main entry point."""

import click
from rich.panel import Panel
from rich.table import Table

from motodiag import __version__, __app_name__
from motodiag.cli.subscription import (
    SubscriptionTier,
    current_tier,
    get_tier_features,
    format_tier_comparison,
    get_enforcement_mode,
)
from motodiag.cli.code import register_code
from motodiag.cli.completion import register_completion
from motodiag.cli.diagnose import register_diagnose, register_quick
from motodiag.cli.kb import register_kb
from motodiag.cli.theme import get_console, status, tier_style

console = get_console()


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
    table.add_row("tier", "Show subscription tier and features")
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


@cli.command()
@click.option("--compare", is_flag=True, help="Show side-by-side tier comparison table.")
def tier(compare: bool) -> None:
    """Show current subscription tier, limits, and upgrade options."""
    if compare:
        console.print()
        console.print(format_tier_comparison())
        console.print()
        return

    user_tier = current_tier()
    features = get_tier_features(user_tier)
    mode = get_enforcement_mode()

    # Tier header panel. The color comes from the shared theme map
    # (Phase 129) so a future theme swap is a one-dict edit.
    color = tier_style(user_tier.value)
    mode_note = (
        "[dim](dev mode — paywall not enforced)[/dim]"
        if mode == "soft" else "[red](paywall enforced)[/red]"
    )

    console.print()
    console.print(Panel(
        f"[bold {color}]{features.display_name}[/bold {color}]\n"
        f"${features.price_monthly_usd:.2f}/month · ${features.price_yearly_usd:.2f}/year\n\n"
        f"Enforcement: {mode_note}",
        title=f"Current tier: {user_tier.value}",
        border_style=color,
    ))

    # Limits table
    table = Table(show_header=True, header_style="bold cyan", title="Your limits")
    table.add_column("Resource", style="green")
    table.add_column("Limit")

    def fmt(n: int) -> str:
        return "Unlimited" if n == -1 else f"{n:,}"

    table.add_row("Max vehicles in garage", fmt(features.max_vehicles))
    table.add_row("Diagnostic sessions / month", fmt(features.max_sessions_per_month))
    table.add_row("User accounts", fmt(features.max_users))
    table.add_row("Physical locations", fmt(features.max_locations))
    table.add_row("AI models available", ", ".join(features.ai_model_access))
    table.add_row("AI cost cap / month", f"${features.ai_monthly_cost_cap_usd:.2f}")
    console.print(table)

    # Features table
    feat_table = Table(show_header=True, header_style="bold cyan", title="Features")
    feat_table.add_column("Feature", style="green")
    feat_table.add_column("Included")
    feat_rows = [
        ("Export to PDF", features.can_export_pdf),
        ("Share reports with customers", features.can_share_reports),
        ("Audio/video diagnostics", features.can_use_media_diagnostics),
        ("REST API access", features.can_use_api),
        ("Team management", features.can_manage_team),
        ("Shop management (work orders, scheduling)", features.can_access_shop_management),
        ("Custom branding", features.can_customize_branding),
        ("Priority support", features.priority_support),
    ]
    for name, included in feat_rows:
        check = "[green]✓[/green]" if included else "[dim]—[/dim]"
        feat_table.add_row(name, check)
    console.print(feat_table)

    # Upgrade hint if not on top tier
    if user_tier != SubscriptionTier.COMPANY:
        console.print()
        console.print(
            "[dim]Run [bold]motodiag tier --compare[/bold] to see all tiers side-by-side.[/dim]"
        )
        console.print(
            "[dim]Upgrade: https://motodiag.app/pricing[/dim]"
        )
    console.print()


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


# Phase 124: `code` command registered below via register_code(cli).


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


@cli.group()
def db() -> None:
    """Database management commands."""
    pass


@db.command("init")
def db_init() -> None:
    """Initialize database and load all starter data (DTCs, symptoms, known issues)."""
    from motodiag.core.database import init_db
    from motodiag.core.config import get_settings, DATA_DIR
    from motodiag.knowledge.loader import (
        load_dtc_directory, load_symptom_file, load_known_issues_file,
    )

    settings = get_settings()
    console.print("[bold]Initializing MotoDiag database...[/bold]")

    # Init DB
    init_db()
    console.print("  [green]✓[/green] Database created")

    # Load DTCs
    dtc_dir = DATA_DIR / "dtc_codes"
    if dtc_dir.is_dir():
        results = load_dtc_directory(dtc_dir)
        total = sum(results.values())
        console.print(f"  [green]✓[/green] Loaded {total} DTC codes from {len(results)} files")

    # Load symptoms
    symptoms_file = DATA_DIR / "knowledge" / "symptoms.json"
    if symptoms_file.exists():
        count = load_symptom_file(symptoms_file)
        console.print(f"  [green]✓[/green] Loaded {count} symptoms")

    # Load known issues
    for issue_file in sorted((DATA_DIR / "knowledge").glob("known_issues_*.json")):
        count = load_known_issues_file(issue_file)
        name = issue_file.stem.replace("known_issues_", "").replace("_", " ").title()
        console.print(f"  [green]✓[/green] Loaded {count} known issues ({name})")

    console.print("\n[bold green]Database ready.[/bold green]")
    console.print(f"  Path: {settings.db_path}")


@cli.group()
def garage() -> None:
    """Manage your vehicle garage — add, list, remove bikes."""


@garage.command("add")
@click.option("--make", required=True, help="Manufacturer (e.g., Honda, Harley-Davidson).")
@click.option("--model", "model_name", required=True, help="Model name.")
@click.option("--year", required=True, type=int, help="Model year.")
@click.option("--engine-cc", type=int, default=None, help="Engine displacement in cc.")
@click.option("--vin", default=None, help="Vehicle identification number.")
@click.option("--protocol", default="none",
              type=click.Choice(["none", "j1850", "k_line", "can", "can_hd",
                                "bmw_k_can", "ducati_can", "ktm_can", "j1939"]),
              help="Diagnostic protocol.")
@click.option("--powertrain", default="ice",
              type=click.Choice(["ice", "electric", "hybrid"]),
              help="Powertrain type.")
@click.option("--notes", default=None, help="Free-text notes.")
def garage_add(make: str, model_name: str, year: int, engine_cc: int | None,
               vin: str | None, protocol: str, powertrain: str,
               notes: str | None) -> None:
    """Add a bike to the garage manually."""
    from motodiag.core.database import init_db
    from motodiag.core.models import (
        VehicleBase, ProtocolType, PowertrainType, EngineType,
    )
    from motodiag.vehicles.registry import add_vehicle

    init_db()
    try:
        vehicle = VehicleBase(
            make=make,
            model=model_name,
            year=year,
            engine_cc=engine_cc,
            vin=vin,
            protocol=ProtocolType(protocol),
            powertrain=PowertrainType(powertrain),
            engine_type=(
                EngineType.ELECTRIC_MOTOR if powertrain == "electric"
                else EngineType.FOUR_STROKE
            ),
            notes=notes,
        )
    except Exception as e:
        console.print(f"[red]Invalid vehicle data: {e}[/red]")
        raise click.Abort() from e

    vid = add_vehicle(vehicle)
    console.print(f"[green]Added vehicle #{vid}: {year} {make} {model_name}[/green]")


@garage.command("list")
def garage_list() -> None:
    """List vehicles in the garage."""
    from motodiag.core.database import init_db
    from motodiag.vehicles.registry import list_vehicles

    init_db()
    vehicles = list_vehicles()
    if not vehicles:
        console.print("[yellow]Garage is empty. Add a bike with:  "
                      "motodiag garage add --make ... --model ... --year ...[/yellow]")
        return

    table = Table(title="Your Garage")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Year", style="magenta")
    table.add_column("Make", style="green")
    table.add_column("Model")
    table.add_column("Engine")
    table.add_column("Powertrain")
    table.add_column("VIN", style="dim")

    for v in vehicles:
        engine = (
            f"{v['engine_cc']}cc"
            if v.get("engine_cc")
            else f"{v.get('motor_kw', '?')}kW" if v.get("powertrain") == "electric"
            else "-"
        )
        table.add_row(
            str(v["id"]), str(v["year"]), v["make"], v["model"],
            engine, v.get("powertrain", "ice") or "ice",
            v.get("vin") or "-",
        )
    console.print(table)


@garage.command("remove")
@click.argument("vehicle_id", type=int)
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
def garage_remove(vehicle_id: int, yes: bool) -> None:
    """Remove a vehicle by ID."""
    from motodiag.core.database import init_db
    from motodiag.vehicles.registry import get_vehicle, delete_vehicle

    init_db()
    v = get_vehicle(vehicle_id)
    if v is None:
        console.print(f"[red]No vehicle with ID {vehicle_id}.[/red]")
        raise click.Abort()

    label = f"{v['year']} {v['make']} {v['model']}"
    if not yes and not click.confirm(f"Remove vehicle #{vehicle_id} ({label})?"):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    if delete_vehicle(vehicle_id):
        console.print(f"[green]Removed #{vehicle_id}: {label}[/green]")
    else:
        console.print(f"[red]Failed to remove #{vehicle_id}.[/red]")
        raise click.Abort()


@garage.command("add-from-photo")
@click.argument("image_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--hints", default=None, help="Optional text hints (e.g., 'sport bike, red').")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
def garage_add_from_photo(image_path: str, hints: str | None, yes: bool) -> None:
    """Identify a bike from a photo and add it to the garage."""
    from motodiag.core.database import init_db
    from motodiag.core.models import (
        VehicleBase, ProtocolType, PowertrainType, EngineType,
    )
    from motodiag.intake import VehicleIdentifier, QuotaExceededError, IntakeError
    from motodiag.vehicles.registry import add_vehicle

    init_db()
    identifier = VehicleIdentifier()
    try:
        with status("Identifying bike..."):
            guess = identifier.identify(image_path, user_id=1, hints=hints)
    except QuotaExceededError as e:
        console.print(f"[red]{e}[/red]")
        raise click.Abort() from e
    except (IntakeError, ValueError, RuntimeError) as e:
        console.print(f"[red]Identification failed: {e}[/red]")
        raise click.Abort() from e

    _print_guess(guess)
    if guess.alert:
        console.print(f"[yellow]⚠ {guess.alert}[/yellow]")

    if not yes and not click.confirm("Save this vehicle to your garage?"):
        console.print("[yellow]Not saved.[/yellow]")
        return

    # Use the midpoint of the year range; user can edit later
    year_mid = (guess.year_range[0] + guess.year_range[1]) // 2
    engine_cc = (
        (guess.engine_cc_range[0] + guess.engine_cc_range[1]) // 2
        if guess.engine_cc_range
        else None
    )
    powertrain = PowertrainType(guess.powertrain_guess)
    engine_type = (
        EngineType.ELECTRIC_MOTOR if guess.powertrain_guess == "electric"
        else EngineType.FOUR_STROKE
    )
    vehicle = VehicleBase(
        make=guess.make,
        model=guess.model,
        year=year_mid,
        engine_cc=engine_cc,
        protocol=ProtocolType.NONE,
        powertrain=powertrain,
        engine_type=engine_type,
        notes=f"Added from photo. Confidence: {guess.confidence:.2f}. {guess.reasoning}",
    )
    vid = add_vehicle(vehicle)
    console.print(f"[green]Added vehicle #{vid}: {year_mid} {guess.make} {guess.model}[/green]")


@cli.group()
def intake() -> None:
    """Photo-based bike identification (preview-only) and quota status."""


@intake.command("photo")
@click.argument("image_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--hints", default=None, help="Optional text hints.")
def intake_photo(image_path: str, hints: str | None) -> None:
    """Identify a bike from a photo without saving (preview only)."""
    from motodiag.core.database import init_db
    from motodiag.intake import VehicleIdentifier, QuotaExceededError, IntakeError

    init_db()
    identifier = VehicleIdentifier()
    try:
        with status("Identifying bike..."):
            guess = identifier.identify(image_path, user_id=1, hints=hints)
    except QuotaExceededError as e:
        console.print(f"[red]{e}[/red]")
        raise click.Abort() from e
    except (IntakeError, ValueError, RuntimeError) as e:
        console.print(f"[red]Identification failed: {e}[/red]")
        raise click.Abort() from e

    _print_guess(guess)
    if guess.alert:
        console.print(f"[yellow]⚠ {guess.alert}[/yellow]")


@intake.command("quota")
def intake_quota() -> None:
    """Show current photo-ID quota usage for the current user."""
    from motodiag.core.database import init_db
    from motodiag.intake import VehicleIdentifier, BUDGET_ALERT_THRESHOLD

    init_db()
    identifier = VehicleIdentifier()
    quota = identifier.check_quota(user_id=1)

    if quota.monthly_limit is None:
        console.print(
            f"[green]Tier: {quota.tier} — unlimited photo IDs. "
            f"Used this month: {quota.used_this_month}[/green]"
        )
        return

    pct_str = f"{int(quota.percent_used * 100)}%"
    warning = quota.percent_used >= BUDGET_ALERT_THRESHOLD
    style = "yellow" if warning else "green"
    marker = "⚠ " if warning else ""
    console.print(
        f"[{style}]{marker}Tier: {quota.tier} — "
        f"{quota.used_this_month}/{quota.monthly_limit} used ({pct_str}), "
        f"{quota.remaining} remaining this month.[/{style}]"
    )


def _print_guess(guess) -> None:
    """Pretty-print a VehicleGuess."""
    y_low, y_high = guess.year_range
    year_str = str(y_low) if y_low == y_high else f"{y_low}–{y_high}"
    engine_str = "electric" if guess.powertrain_guess == "electric" else (
        f"{guess.engine_cc_range[0]}–{guess.engine_cc_range[1]}cc"
        if guess.engine_cc_range else "?cc"
    )
    cached_tag = " [dim](cached)[/dim]" if guess.cached else ""

    panel_body = (
        f"[bold]{guess.make} {guess.model}[/bold]{cached_tag}\n"
        f"Year:       {year_str}\n"
        f"Engine:     {engine_str}\n"
        f"Powertrain: {guess.powertrain_guess}\n"
        f"Confidence: {guess.confidence:.2f} (via {guess.model_used})\n"
        f"\n[dim]{guess.reasoning}[/dim]"
    )
    console.print(Panel(panel_body, title="Vehicle Identification", border_style="cyan"))


@cli.command()
def history() -> None:
    """Browse past diagnostic sessions. (Use 'diagnose list' for now.)"""
    console.print("[yellow]Use 'motodiag diagnose list' to browse sessions.[/yellow]")


# Phase 123: register the diagnose subgroup (start / quick / list / show)
register_diagnose(cli)

# Phase 125: register the top-level `quick` shortcut (delegates to diagnose quick)
register_quick(cli)

# Phase 128: register the `kb` knowledge-base browser subgroup
register_kb(cli)

# Phase 124: register the `code` command (replaces the legacy inline version)
register_code(cli)

# Phase 130: register shell completion scripts + dynamic completers.
register_completion(cli)


# Phase 130: hidden short aliases for the highest-frequency paths. Each
# alias reuses the already-registered command object so there's only one
# implementation to maintain. `hidden=True` keeps them out of `--help`
# output so newcomers see canonical names only — power users who know
# the aliases still get the keystroke savings.
def _register_short_aliases(cli_group: click.Group) -> None:
    """Attach hidden single-letter aliases for diagnose, kb, garage, quick.

    Aliases wired:
      - ``d`` → ``diagnose`` (group)
      - ``k`` → ``kb`` (group)
      - ``g`` → ``garage`` (group)
      - ``q`` → ``quick`` (command)

    Registration strategy: Click's command objects can be attached under
    multiple names via ``cli.add_command(cmd, name="d")``. We flip
    ``hidden=True`` on the alias so ``motodiag --help`` renders only the
    canonical names. The underlying command objects are shared — any
    later mutation to ``diagnose`` (e.g., a new subcommand) is visible
    via ``d`` automatically.
    """
    for alias, canonical in (("d", "diagnose"), ("k", "kb"),
                             ("g", "garage"), ("q", "quick")):
        cmd = cli_group.commands.get(canonical)
        if cmd is None:
            # Defensive: if the canonical command isn't registered yet,
            # skip silently rather than raising during module import.
            # (Should never happen given the register_* ordering above.)
            continue
        cli_group.add_command(cmd, name=alias)
        # Mutating hidden on the shared object would also hide the
        # canonical. Instead, we wrap it with a thin alias view whose
        # `hidden` flag is independent. Easiest path: register a copy of
        # the command under the alias name with hidden=True.
        aliased = cli_group.commands[alias]
        # If aliased is the same object as the canonical, swap to a
        # hidden shallow clone so `--help` doesn't list the alias.
        if aliased is cmd:
            import copy as _copy
            clone = _copy.copy(cmd)
            clone.hidden = True
            cli_group.commands[alias] = clone


_register_short_aliases(cli)


if __name__ == "__main__":
    cli()
