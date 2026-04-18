"""Advanced diagnostics CLI — ``motodiag advanced predict`` (Phase 148).

First user-facing Track F command. Wires
:func:`motodiag.advanced.predictor.predict_failures` into a Click
subcommand using the Phase 140 two-mode grammar:

- ``motodiag advanced predict --bike SLUG [--current-miles N]
  [--horizon-days 180] [--min-severity medium] [--json]``
- ``motodiag advanced predict --make MAKE --model MODEL --year YEAR
  --current-miles MI [--horizon-days 180] [--min-severity medium]
  [--json]``

Rendering
---------

Without ``--json``, prints a Rich Table with seven columns — Issue,
Typical onset, Gap to onset, Confidence, Preventive action, Parts $,
Severity — plus a footer that summarises predictions, the matched bike,
current mileage, horizon, and how many predictions were flagged as
forum-verified (honors the "every Track B phase must include forum-
sourced fixes" user-memory rule).

With ``--json``, emits a JSON object with ``vehicle`` + ``predictions``
keys. Every :class:`~motodiag.advanced.models.FailurePrediction` is
dumped via ``model_dump(mode="json")`` so the enum serializes as its
string value and tuples serialize as JSON arrays.

Phases 149-159 will extend this group with new subcommands
(``advanced wear-dashboard``, ``advanced fleet-summary``, etc.) —
Click's ``@group.command("...")`` adds them without re-registering.
"""

from __future__ import annotations

import json as _json
from typing import Optional

import click
from rich.panel import Panel
from rich.table import Table

from motodiag.advanced.predictor import predict_failures
from motodiag.cli.theme import (
    ICON_OK,
    ICON_WARN,
    format_severity,
    get_console,
)
from motodiag.core.database import init_db


# --- Styling helpers ----------------------------------------------------


# Confidence → Rich style. Cyan = HIGH (strongest trust signal), yellow
# = MEDIUM, dim = LOW. Mirrors the Phase 129 "visual attention weight"
# convention: cyan draws the eye to actionable rows.
_CONFIDENCE_STYLES: dict[str, str] = {
    "high": "cyan",
    "medium": "yellow",
    "low": "dim",
}


def _format_confidence(conf_value: str) -> str:
    """Return a Rich markup string for a :class:`PredictionConfidence` label."""
    style = _CONFIDENCE_STYLES.get(conf_value, "dim")
    return f"[{style}]{conf_value}[/{style}]"


def _format_gap(miles_to_onset: Optional[int], years_to_onset: Optional[float]) -> str:
    """Render the 'gap to onset' cell with a red style for overdue rows.

    Shows miles when known; falls back to years when only the age
    signal was available. Negative values render in red because the
    bike is past the heuristic onset window — that's the mechanic-facing
    "already due" signal.
    """
    if miles_to_onset is not None:
        if miles_to_onset < 0:
            return f"[red]{miles_to_onset:,} mi[/red]"
        return f"{miles_to_onset:,} mi"
    if years_to_onset is not None:
        if years_to_onset < 0:
            return f"[red]{years_to_onset:.1f} yr[/red]"
        return f"{years_to_onset:.1f} yr"
    return "[dim]-[/dim]"


def _format_onset(
    typical_onset_miles: Optional[int],
    typical_onset_years: Optional[int],
) -> str:
    """Render the 'typical onset' cell — mileage + age band summary."""
    parts: list[str] = []
    if typical_onset_miles is not None:
        parts.append(f"{typical_onset_miles:,} mi")
    if typical_onset_years is not None:
        parts.append(f"{typical_onset_years} yr")
    if not parts:
        return "[dim]-[/dim]"
    return " / ".join(parts)


def _list_garage_summary(db_path: Optional[str] = None, limit: int = 10) -> list[dict]:
    """Return a small garage list for the unknown-bike remediation panel.

    Mirrors ``cli.diagnose._list_garage_summary`` — we could import it,
    but keeping the implementation local avoids cross-module coupling
    for a trivial query. Best-effort: any exception returns ``[]``.
    """
    try:
        from motodiag.core.database import get_connection

        with get_connection(db_path) as conn:
            rows = conn.execute(
                "SELECT id, make, model, year FROM vehicles "
                "ORDER BY created_at, id LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


# --- Register ----------------------------------------------------------


def register_advanced(cli_group: click.Group) -> None:
    """Attach the ``advanced`` subgroup to the top-level CLI.

    Phase 148 registers one subcommand (``predict``). Phases 149-159
    will append to the same group via ``advanced_group.command("...")``
    — Click supports this cleanly as long as ``register_advanced`` is
    only called once per CLI.
    """

    @cli_group.group("advanced")
    def advanced_group() -> None:
        """Advanced diagnostics: predictive maintenance, wear analysis, fleet."""

    # --- predict ------------------------------------------------------
    @advanced_group.command("predict")
    @click.option(
        "--bike", default=None,
        help="Garage bike slug (e.g. harley-sportster-2001). "
             "Mutually exclusive with the direct-args mode.",
    )
    @click.option(
        "--make", default=None,
        help="Direct-args mode: bike make.",
    )
    @click.option(
        "--model", "model_name", default=None,
        help="Direct-args mode: bike model.",
    )
    @click.option(
        "--year", type=int, default=None,
        help="Direct-args mode: bike year.",
    )
    @click.option(
        "--current-miles", type=int, default=None,
        help="Current mileage. Required in direct-args mode; optional "
             "in --bike mode (absent ⇒ age-only scoring).",
    )
    @click.option(
        "--horizon-days", type=int, default=180, show_default=True,
        help="Drop predictions whose typical onset is beyond this many days.",
    )
    @click.option(
        "--min-severity",
        type=click.Choice(["low", "medium", "high", "critical"],
                          case_sensitive=False),
        default=None,
        help="Drop predictions below this severity band.",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON (vehicle + predictions) instead of the Rich table.",
    )
    def predict_cmd(
        bike: Optional[str],
        make: Optional[str],
        model_name: Optional[str],
        year: Optional[int],
        current_miles: Optional[int],
        horizon_days: int,
        min_severity: Optional[str],
        json_output: bool,
    ) -> None:
        """Predict likely upcoming failures for a bike.

        Cross-references the ``known_issues`` knowledge base against the
        vehicle's mileage + age and returns heuristically-ranked
        predictions. Zero AI calls, zero network, zero tokens.
        """
        console = get_console()
        init_db()

        # --- Mutex + required-field validation ---
        direct_args = any([make, model_name, year is not None])
        if bike and direct_args:
            raise click.ClickException(
                "--bike and direct-args (--make/--model/--year) are "
                "mutually exclusive; choose one.",
            )
        if not bike and not (
            make and model_name and year is not None and current_miles is not None
        ):
            raise click.ClickException(
                "Specify --bike SLUG OR all of "
                "--make MAKE --model MODEL --year YEAR --current-miles MI.",
            )
        if horizon_days < 1:
            raise click.ClickException("--horizon-days must be >= 1.")

        # --- Resolve vehicle ---
        vehicle: dict
        bike_label: str
        if bike:
            # Delayed import avoids a CLI-level circular with diagnose.py
            # (diagnose imports from cli/theme, and in Phase 149+ we may
            # end up with the reverse relationship too).
            from motodiag.cli.diagnose import _resolve_bike_slug

            resolved = _resolve_bike_slug(bike)
            if resolved is None:
                _render_bike_not_found(console, bike)
                raise click.exceptions.Exit(1)
            vehicle = dict(resolved)
            if current_miles is not None:
                vehicle["mileage"] = int(current_miles)
            bike_label = (
                f"#{vehicle.get('id')}  "
                f"{vehicle.get('year')} {vehicle.get('make')} {vehicle.get('model')}"
            )
        else:
            vehicle = {
                "make": (make or "").strip().lower(),
                "model": model_name,
                "year": int(year),
                "mileage": int(current_miles) if current_miles is not None else None,
            }
            bike_label = f"{year} {make} {model_name}"

        # --- Predict ---
        predictions = predict_failures(
            vehicle,
            horizon_days=horizon_days,
            min_severity=min_severity,
        )

        # --- JSON mode ---
        if json_output:
            # Include only primitive fields in the vehicle summary so
            # the JSON schema is stable (SQL rows may carry implementation
            # details like created_at timestamps that change across runs).
            vehicle_out = {
                "make": vehicle.get("make"),
                "model": vehicle.get("model"),
                "year": vehicle.get("year"),
                "mileage": vehicle.get("mileage"),
            }
            if vehicle.get("id") is not None:
                vehicle_out["id"] = vehicle["id"]
            output = {
                "vehicle": vehicle_out,
                "horizon_days": horizon_days,
                "min_severity": min_severity,
                "predictions": [p.model_dump(mode="json") for p in predictions],
            }
            click.echo(_json.dumps(output, indent=2, default=str))
            return

        # --- Rich table mode ---
        if not predictions:
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} No predicted failures within "
                    f"the {horizon_days}-day horizon for {bike_label}.[/yellow]\n\n"
                    "[dim]Try a wider --horizon-days (e.g. 730 for a "
                    "pre-purchase inspection), lower --min-severity, or "
                    "confirm the knowledge base has entries for this "
                    "make/model (motodiag kb search <term>).[/dim]",
                    title="No predictions",
                    border_style="yellow",
                )
            )
            return

        _render_predictions(
            console,
            predictions,
            bike_label=bike_label,
            current_mileage=vehicle.get("mileage"),
            horizon_days=horizon_days,
        )


# --- Rendering ---------------------------------------------------------


def _render_bike_not_found(console, bike: str) -> None:
    """Render the Phase 125-style remediation panel for an unknown slug.

    Lists up to 10 garage rows so the mechanic can cross-check the slug
    they meant to type; when the garage is empty, hints at
    ``motodiag garage add``.
    """
    console.print(
        Panel(
            f"[red]No bike matches slug {bike!r}.[/red]\n\n"
            "[dim]Run [bold]motodiag garage list[/bold] to see existing "
            "slugs, or add one with [bold]motodiag garage add[/bold].[/dim]",
            title="Bike not found",
            border_style="red",
        )
    )
    garage = _list_garage_summary()
    if garage:
        console.print("[dim]Your garage:[/dim]")
        for v in garage:
            console.print(
                f"  [cyan]#{v['id']}[/cyan]  "
                f"{v['year']} {v['make']} {v['model']}"
            )


def _render_predictions(
    console,
    predictions: list,
    bike_label: str,
    current_mileage: Optional[int],
    horizon_days: int,
) -> None:
    """Render the Rich Table + footer for a non-empty prediction list."""
    table = Table(
        title=f"Predicted failures ({len(predictions)})",
        header_style="bold cyan",
    )
    table.add_column("Issue", overflow="fold", max_width=45)
    table.add_column("Typical onset", no_wrap=True)
    table.add_column("Gap to onset", no_wrap=True)
    table.add_column("Confidence")
    table.add_column("Preventive action", overflow="fold", max_width=60)
    table.add_column("Parts $", no_wrap=True)
    table.add_column("Severity")

    for p in predictions:
        parts_cell = (
            f"${p.parts_cost_cents / 100:.2f}"
            if p.parts_cost_cents is not None
            else "[dim]—[/dim]"
        )
        table.add_row(
            p.issue_title,
            _format_onset(p.typical_onset_miles, p.typical_onset_years),
            _format_gap(p.miles_to_onset, p.years_to_onset),
            _format_confidence(p.confidence.value),
            p.preventive_action or "[dim]-[/dim]",
            parts_cell,
            format_severity(p.severity),
        )
    console.print(table)

    # --- Footer ---
    verified_count = sum(1 for p in predictions if p.verified_by == "forum")
    mileage_str = (
        f"{current_mileage:,} mi" if current_mileage is not None else "unknown"
    )
    footer_parts = [
        f"[bold]{bike_label}[/bold]",
        f"mileage: {mileage_str}",
        f"horizon: {horizon_days}d",
    ]
    console.print("\n" + "   •   ".join(footer_parts))

    if verified_count:
        console.print(
            f"[dim]{ICON_OK} {verified_count} of {len(predictions)} "
            f"predictions verified by forum sources.[/dim]"
        )
    console.print(
        "[dim]hint: pass [bold]--json[/bold] for machine-readable output, "
        "or [bold]motodiag kb search <term>[/bold] for full issue details.[/dim]"
    )
