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

from motodiag.advanced.comparative import (
    FLEET_UNAVAILABLE,
    PeerComparison,
    _fleet_tables_available,
    _normalize_pid_hex,
    compare_against_peers,
)
from motodiag.advanced.predictor import predict_failures
from motodiag.cli.theme import (
    ICON_OK,
    ICON_WARN,
    format_severity,
    get_console,
)
from motodiag.core.database import get_connection, init_db


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

    # --- compare subgroup (Phase 156) --------------------------------
    #
    # Peer-cohort anomaly detection. Nested under the shared ``advanced``
    # group so ``motodiag advanced compare {bike,recording,fleet}`` is
    # grouped with Phase 148's ``predict`` in ``--help`` output.

    @advanced_group.group("compare")
    def compare_group() -> None:
        """Compare one bike's sensor data against peer recordings."""

    # --- compare bike -------------------------------------------------
    @compare_group.command("bike")
    @click.option(
        "--bike", "bike", required=True,
        help="Garage bike slug (same grammar as `advanced predict --bike`).",
    )
    @click.option(
        "--pid", "pid_hex", default="0x05", show_default=True,
        help="OBD-II PID to compare — hex string (e.g. 0x05 for coolant).",
    )
    @click.option(
        "--cohort",
        type=click.Choice(["same-model", "strict", "fleet"], case_sensitive=False),
        default="same-model", show_default=True,
        help="Peer-selection mode.",
    )
    @click.option(
        "--peers-min",
        type=click.IntRange(min=1),
        default=5, show_default=True,
        help="Minimum peer-recording count before percentiles are trusted.",
    )
    @click.option(
        "--metric",
        type=click.Choice(["avg", "max", "p95"], case_sensitive=False),
        default="avg", show_default=True,
        help="Per-recording reducer applied before percentile math.",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of the Rich table.",
    )
    def compare_bike_cmd(
        bike: str,
        pid_hex: str,
        cohort: str,
        peers_min: int,
        metric: str,
        json_output: bool,
    ) -> None:
        """Compare a garage bike's most recent recording against peers."""
        console = get_console()
        init_db()

        try:
            canonical_pid = _normalize_pid_hex(pid_hex)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc

        from motodiag.cli.diagnose import _resolve_bike_slug

        resolved = _resolve_bike_slug(bike)
        if resolved is None:
            _render_bike_not_found(console, bike)
            raise click.exceptions.Exit(1)

        vehicle_id = int(resolved["id"])
        recording_id = _latest_recording_for_vehicle(vehicle_id)
        if recording_id is None:
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} No completed recordings for "
                    f"bike #{vehicle_id}.[/yellow]\n\n"
                    "[dim]Run [bold]motodiag hardware log start[/bold] to "
                    "capture a session first.[/dim]",
                    title="No recordings",
                    border_style="yellow",
                )
            )
            return

        _run_comparison(
            console,
            vehicle_recording_id=recording_id,
            pid_hex=canonical_pid,
            cohort_filter=cohort,
            metric=metric,
            peers_min=peers_min,
            json_output=json_output,
        )

    # --- compare recording --------------------------------------------
    @compare_group.command("recording")
    @click.argument("recording_id", type=int)
    @click.option(
        "--pid", "pid_hex", default="0x05", show_default=True,
        help="OBD-II PID to compare.",
    )
    @click.option(
        "--cohort",
        type=click.Choice(["same-model", "strict", "fleet"], case_sensitive=False),
        default="same-model", show_default=True,
        help="Peer-selection mode.",
    )
    @click.option(
        "--peers-min",
        type=click.IntRange(min=1),
        default=5, show_default=True,
        help="Minimum peer-recording count.",
    )
    @click.option(
        "--metric",
        type=click.Choice(["avg", "max", "p95"], case_sensitive=False),
        default="avg", show_default=True,
        help="Per-recording reducer.",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of the Rich table.",
    )
    def compare_recording_cmd(
        recording_id: int,
        pid_hex: str,
        cohort: str,
        peers_min: int,
        metric: str,
        json_output: bool,
    ) -> None:
        """Compare a specific recording ID against peers."""
        console = get_console()
        init_db()

        try:
            canonical_pid = _normalize_pid_hex(pid_hex)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc

        _run_comparison(
            console,
            vehicle_recording_id=recording_id,
            pid_hex=canonical_pid,
            cohort_filter=cohort,
            metric=metric,
            peers_min=peers_min,
            json_output=json_output,
        )

    # --- compare fleet ------------------------------------------------
    @compare_group.command("fleet")
    @click.option(
        "--bike", "bike", required=True,
        help="Garage bike slug for the target recording.",
    )
    @click.option(
        "--pid", "pid_hex", default="0x05", show_default=True,
        help="OBD-II PID to compare.",
    )
    @click.option(
        "--peers-min",
        type=click.IntRange(min=1),
        default=5, show_default=True,
        help="Minimum peer-recording count.",
    )
    @click.option(
        "--metric",
        type=click.Choice(["avg", "max", "p95"], case_sensitive=False),
        default="avg", show_default=True,
        help="Per-recording reducer.",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of the Rich table.",
    )
    def compare_fleet_cmd(
        bike: str,
        pid_hex: str,
        peers_min: int,
        metric: str,
        json_output: bool,
    ) -> None:
        """Compare against a fleet cohort (requires Phase 150)."""
        console = get_console()
        init_db()

        if not _fleet_tables_available():
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} Fleet cohorts require Phase 150 "
                    "(fleet_memberships table).[/yellow]\n\n"
                    "[dim]Run [bold]motodiag advanced compare bike "
                    "--cohort same-model[/bold] in the meantime, or wait "
                    "for Phase 150 to land fleet tagging.[/dim]",
                    title="Phase 150 required",
                    border_style="yellow",
                )
            )
            return

        try:
            canonical_pid = _normalize_pid_hex(pid_hex)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc

        from motodiag.cli.diagnose import _resolve_bike_slug

        resolved = _resolve_bike_slug(bike)
        if resolved is None:
            _render_bike_not_found(console, bike)
            raise click.exceptions.Exit(1)

        vehicle_id = int(resolved["id"])
        recording_id = _latest_recording_for_vehicle(vehicle_id)
        if recording_id is None:
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} No completed recordings for "
                    f"bike #{vehicle_id}.[/yellow]",
                    title="No recordings",
                    border_style="yellow",
                )
            )
            return

        _run_comparison(
            console,
            vehicle_recording_id=recording_id,
            pid_hex=canonical_pid,
            cohort_filter="fleet",
            metric=metric,
            peers_min=peers_min,
            json_output=json_output,
        )

    # --- Phase 158: ``advanced drift`` nested subgroup ---------------
    # Nested under the same ``advanced`` group so phase 158's drift
    # subcommands appear alongside ``predict`` and ``compare`` in
    # ``motodiag advanced --help``. Four subcommands cover the mechanic
    # workflow: single-PID deep dive (``bike``), three-bucket summary
    # (``show``), intra-session trend (``recording``), and ASCII
    # sparkline / wide-CSV export (``plot``).

    @advanced_group.group("drift")
    def drift_group() -> None:
        """Track slow-onset sensor drift across recordings of one bike."""

    # --- drift bike ---------------------------------------------------
    @drift_group.command("bike")
    @click.option(
        "--bike", "bike", required=True,
        help="Garage bike slug (same grammar as `advanced predict --bike`).",
    )
    @click.option(
        "--pid", "pid_hex", required=True,
        help="OBD-II PID to analyze — hex string (e.g. 0x05 for coolant).",
    )
    @click.option(
        "--since", "since", default=None,
        help="Lower bound ISO 8601 captured_at filter (e.g. 2025-01-01).",
    )
    @click.option(
        "--until", "until", default=None,
        help="Upper bound ISO 8601 captured_at filter.",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of the Rich panel.",
    )
    def drift_bike_cmd(
        bike: str,
        pid_hex: str,
        since: Optional[str],
        until: Optional[str],
        json_output: bool,
    ) -> None:
        """Fit a linear trend for one PID on one bike across sessions."""
        console = get_console()
        init_db()

        if since and until and str(since) > str(until):
            raise click.ClickException(
                "--since must be <= --until (ISO 8601 lexical order).",
            )

        from motodiag.advanced.drift import compute_trend
        from motodiag.cli.diagnose import _resolve_bike_slug

        resolved = _resolve_bike_slug(bike)
        if resolved is None:
            _render_bike_not_found(console, bike)
            raise click.exceptions.Exit(1)

        vehicle_id = int(resolved["id"])
        result = compute_trend(
            vehicle_id=vehicle_id,
            pid_hex=pid_hex,
            since=since,
            until=until,
        )

        if result is None:
            if json_output:
                click.echo(_json.dumps({"result": None}, indent=2))
                return
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} Not enough samples to fit a "
                    f"trend for PID {pid_hex} on bike "
                    f"#{vehicle_id}.[/yellow]\n\n"
                    "[dim]Drift tracking needs at least 2 recorded "
                    "samples across ≥1 session. Try widening --since "
                    "or running more recordings with "
                    "[bold]motodiag hardware log start[/bold].[/dim]",
                    title="Insufficient data",
                    border_style="yellow",
                )
            )
            return

        if json_output:
            click.echo(
                _json.dumps(result.model_dump(mode="json"),
                            indent=2, default=str),
            )
            return

        _render_drift_bike(console, result)

    # --- drift show ---------------------------------------------------
    @drift_group.command("show")
    @click.option(
        "--bike", "bike", required=True,
        help="Garage bike slug.",
    )
    @click.option(
        "--threshold-pct",
        type=click.FloatRange(min=0.0),
        default=5.0, show_default=True,
        help="Drift percentage (per 30 days) above which a PID is flagged.",
    )
    @click.option(
        "--since", "since", default=None,
        help="Lower bound ISO 8601 captured_at filter.",
    )
    @click.option(
        "--until", "until", default=None,
        help="Upper bound ISO 8601 captured_at filter.",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of the Rich table.",
    )
    def drift_show_cmd(
        bike: str,
        threshold_pct: float,
        since: Optional[str],
        until: Optional[str],
        json_output: bool,
    ) -> None:
        """Three-bucket summary of every recorded PID for a bike."""
        console = get_console()
        init_db()

        if since and until and str(since) > str(until):
            raise click.ClickException(
                "--since must be <= --until (ISO 8601 lexical order).",
            )

        from motodiag.advanced.drift import summary_for_bike
        from motodiag.cli.diagnose import _resolve_bike_slug

        resolved = _resolve_bike_slug(bike)
        if resolved is None:
            _render_bike_not_found(console, bike)
            raise click.exceptions.Exit(1)

        vehicle_id = int(resolved["id"])
        summary = summary_for_bike(
            vehicle_id=vehicle_id,
            threshold_pct=threshold_pct,
            since=since,
            until=until,
        )

        if json_output:
            payload = {
                "vehicle_id": vehicle_id,
                "threshold_pct": threshold_pct,
                "summary": {
                    k: [r.model_dump(mode="json") for r in v]
                    for k, v in summary.items()
                },
            }
            click.echo(_json.dumps(payload, indent=2, default=str))
            return

        _render_drift_summary(console, summary, vehicle_id, threshold_pct)

    # --- drift recording ----------------------------------------------
    @drift_group.command("recording")
    @click.argument("recording_id", type=int)
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of the Rich table.",
    )
    def drift_recording_cmd(
        recording_id: int,
        json_output: bool,
    ) -> None:
        """Intra-session drift trend — per-PID regression inside one recording."""
        console = get_console()
        init_db()

        from motodiag.advanced.drift import _render_sparkline, compute_trend
        from motodiag.hardware.recorder import RecordingManager

        try:
            manager = RecordingManager()
            meta, samples = manager.load_recording(recording_id)
        except KeyError:
            console.print(
                Panel(
                    f"[red]Recording #{recording_id} not found.[/red]",
                    title="Unknown recording",
                    border_style="red",
                )
            )
            raise click.exceptions.Exit(1)

        # Bucket by pid_hex so each PID gets its own short regression
        # over intra-session captured_at.
        by_pid: dict[str, list[dict]] = {}
        for s in samples:
            if s.get("value") is None:
                continue
            by_pid.setdefault(s.get("pid_hex") or "", []).append(s)

        vehicle_id = meta.get("vehicle_id")
        results = []
        for pid_hex, rows in sorted(by_pid.items()):
            # For intra-session we can't use compute_trend (that reads
            # from the DB via vehicle_id). Hand-fit from the in-memory
            # rows we already have.
            from motodiag.advanced.drift import (
                _linear_regression,
                _normalize_pid_hex,
                _parse_iso,
                _pid_catalog_entry,
            )

            parsed = []
            for r in rows:
                dt = _parse_iso(r.get("captured_at"))
                if dt is None:
                    continue
                try:
                    val = float(r["value"])
                except (TypeError, ValueError):
                    continue
                parsed.append((dt, val))
            if len(parsed) < 2:
                continue
            t0 = parsed[0][0]
            xs = [(p[0].timestamp() - t0.timestamp()) / 86400.0 for p in parsed]
            ys = [p[1] for p in parsed]
            reg = _linear_regression(xs, ys)
            if reg is None:
                continue
            slope, intercept, r_squared = reg
            mean_y = sum(ys) / len(ys)
            pct = 0.0 if mean_y == 0.0 else (
                100.0 * slope * 30.0 / mean_y
            )
            canonical = _normalize_pid_hex(pid_hex)
            name, unit = _pid_catalog_entry(canonical)
            results.append(
                {
                    "pid_hex": canonical,
                    "pid_name": name,
                    "unit": unit,
                    "n_samples": len(parsed),
                    "slope_per_day": slope,
                    "intercept": intercept,
                    "r_squared": r_squared,
                    "mean_value": mean_y,
                    "drift_pct_per_30_days": pct,
                    "sparkline": _render_sparkline(ys, width=40),
                }
            )

        if json_output:
            click.echo(
                _json.dumps(
                    {
                        "recording_id": recording_id,
                        "vehicle_id": vehicle_id,
                        "results": results,
                    },
                    indent=2, default=str,
                )
            )
            return

        _render_drift_recording(console, recording_id, vehicle_id, results)

    # --- drift plot ---------------------------------------------------
    @drift_group.command("plot")
    @click.option(
        "--bike", "bike", required=True,
        help="Garage bike slug.",
    )
    @click.option(
        "--pid", "pid_hex", required=True,
        help="OBD-II PID to plot.",
    )
    @click.option(
        "--output", "output_path",
        type=click.Path(dir_okay=False, writable=True),
        default=None,
        help="Output file path; omit for stdout (ASCII mode only).",
    )
    @click.option(
        "--format", "fmt",
        type=click.Choice(["ascii", "csv"], case_sensitive=False),
        default="ascii", show_default=True,
        help="Render mode: ASCII sparkline (stdout/file) or wide-format CSV.",
    )
    @click.option(
        "--since", "since", default=None,
        help="Lower bound ISO 8601 captured_at filter.",
    )
    def drift_plot_cmd(
        bike: str,
        pid_hex: str,
        output_path: Optional[str],
        fmt: str,
        since: Optional[str],
    ) -> None:
        """ASCII sparkline or wide-format CSV of per-recording trends."""
        console = get_console()
        init_db()

        from motodiag.advanced.drift import (
            _normalize_pid_hex,
            _render_csv,
            _render_sparkline,
        )
        from motodiag.cli.diagnose import _resolve_bike_slug

        resolved = _resolve_bike_slug(bike)
        if resolved is None:
            _render_bike_not_found(console, bike)
            raise click.exceptions.Exit(1)

        vehicle_id = int(resolved["id"])
        canonical_pid = _normalize_pid_hex(pid_hex)

        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT s.recording_id, r.started_at,
                       AVG(s.value) AS mean_v,
                       MIN(s.value) AS min_v,
                       MAX(s.value) AS max_v,
                       COUNT(s.value) AS n_samples
                  FROM sensor_samples s
                  JOIN sensor_recordings r ON r.id = s.recording_id
                 WHERE r.vehicle_id = ?
                   AND s.pid_hex = ?
                   AND s.value IS NOT NULL
                   AND (? IS NULL OR s.captured_at >= ?)
              GROUP BY s.recording_id, r.started_at
              ORDER BY r.started_at ASC
                """,
                (vehicle_id, canonical_pid, since, since),
            ).fetchall()

        recordings_data = [
            {
                "recording_id": r["recording_id"],
                "started_at": r["started_at"],
                "pid_hex": canonical_pid,
                "mean": r["mean_v"],
                "min": r["min_v"],
                "max": r["max_v"],
                "n_samples": r["n_samples"],
            }
            for r in rows
        ]

        if fmt.lower() == "csv":
            import io

            buf = io.StringIO(newline="")
            writer = csv.DictWriter(
                buf,
                fieldnames=[
                    "recording_id", "started_at", "pid_hex",
                    "mean", "min", "max", "n_samples",
                ],
                lineterminator="\n",
            )
            writer.writeheader()
            _render_csv(recordings_data, writer)
            payload = buf.getvalue()
            if output_path:
                with open(output_path, "w", encoding="utf-8", newline="") as fh:
                    fh.write(payload)
                console.print(
                    f"[green]{ICON_OK} Wrote {len(recordings_data)} "
                    f"rows to {output_path}[/green]"
                )
            else:
                click.echo(payload, nl=False)
            return

        # ASCII mode
        if not recordings_data:
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} No samples for PID "
                    f"{canonical_pid} on bike #{vehicle_id}.[/yellow]",
                    title="No data",
                    border_style="yellow",
                )
            )
            return
        values = [row["mean"] for row in recordings_data if row["mean"] is not None]
        spark = _render_sparkline(values, width=60)
        header = (
            f"Bike #{vehicle_id}  PID {canonical_pid}  "
            f"{len(recordings_data)} recordings"
        )
        payload = f"{header}\n{spark}\n"
        if output_path:
            with open(output_path, "w", encoding="utf-8") as fh:
                fh.write(payload)
            console.print(
                f"[green]{ICON_OK} Wrote sparkline to {output_path}[/green]"
            )
        else:
            click.echo(payload, nl=False)

    # --- wear (Phase 149) --------------------------------------------
    #
    # Symptom-driven wear-pattern matcher. Companion to ``predict`` —
    # where ``predict`` answers "what's next based on miles + age",
    # ``wear`` answers "mechanic is reporting these symptoms, which
    # worn components best match?". File-seeded catalog, no AI, no
    # migration, no network.

    @advanced_group.command("wear")
    @click.option(
        "--bike", default=None,
        help="Garage bike slug (same grammar as `advanced predict --bike`). "
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
        "--symptoms", required=True,
        help="Observed symptoms. Comma- or semicolon-delimited "
             "(e.g. 'tick of death, dim headlight'). Quote so the "
             "shell doesn't split on the commas.",
    )
    @click.option(
        "--min-confidence", type=float, default=0.5, show_default=True,
        help="Drop matches whose final score falls below this floor.",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON (vehicle + matches) instead of the Rich table.",
    )
    def wear_cmd(
        bike: Optional[str],
        make: Optional[str],
        model_name: Optional[str],
        year: Optional[int],
        symptoms: str,
        min_confidence: float,
        json_output: bool,
    ) -> None:
        """Rank curated wear patterns against observed symptoms.

        Uses a file-seeded catalog of ~30 mechanic-vocabulary patterns
        (Harley TC88 tensioner, KLR doohickey, fork seals, wheel
        bearings, etc.) plus forum-consensus citations. Returns matches
        sorted by confidence DESC → matched-count DESC → pattern_id
        ASC.
        """
        console = get_console()
        init_db()

        # --- Mutex + field validation ---
        direct_args = any([make, model_name, year is not None])
        if bike and direct_args:
            raise click.ClickException(
                "--bike and direct-args (--make/--model/--year) are "
                "mutually exclusive; choose one.",
            )
        if not bike and not (make and model_name and year is not None):
            raise click.ClickException(
                "Specify --bike SLUG OR all of "
                "--make MAKE --model MODEL --year YEAR.",
            )
        if not (0.0 <= min_confidence <= 1.0):
            raise click.ClickException(
                "--min-confidence must be between 0.0 and 1.0.",
            )

        # --- Resolve vehicle ---
        vehicle: dict
        bike_label: str
        if bike:
            from motodiag.cli.diagnose import _resolve_bike_slug

            resolved = _resolve_bike_slug(bike)
            if resolved is None:
                _render_bike_not_found(console, bike)
                raise click.exceptions.Exit(1)
            vehicle = dict(resolved)
            bike_label = (
                f"#{vehicle.get('id')}  "
                f"{vehicle.get('year')} {vehicle.get('make')} {vehicle.get('model')}"
            )
        else:
            vehicle = {
                "make": (make or "").strip(),
                "model": model_name,
                "year": int(year),
            }
            bike_label = f"{year} {make} {model_name}"

        # --- Analyze ---
        from motodiag.advanced.wear import analyze_wear

        matches = analyze_wear(
            vehicle=vehicle,
            symptoms=symptoms,
            min_confidence=min_confidence,
        )

        # --- JSON mode ---
        if json_output:
            vehicle_out = {
                "make": vehicle.get("make"),
                "model": vehicle.get("model"),
                "year": vehicle.get("year"),
            }
            if vehicle.get("id") is not None:
                vehicle_out["id"] = vehicle["id"]
            output = {
                "vehicle": vehicle_out,
                "symptoms": symptoms,
                "min_confidence": min_confidence,
                "matches": [m.model_dump(mode="json") for m in matches],
            }
            click.echo(_json.dumps(output, indent=2, default=str))
            return

        # --- Rich table mode ---
        if not matches:
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} No wear patterns match the "
                    f"supplied symptoms for {bike_label}.[/yellow]\n\n"
                    "[dim]Tip: use mechanic vocabulary ('tick of death', "
                    "'chain slap', 'dim headlight at idle', 'clunk over "
                    "bumps') rather than generic descriptions. Lower "
                    "[bold]--min-confidence[/bold] to widen the net.[/dim]",
                    title="No wear matches",
                    border_style="yellow",
                )
            )
            return

        _render_wear_matches(console, matches, bike_label=bike_label)

    # --- Phase 150: ``advanced fleet`` nested subgroup ---------------
    #
    # Fleet management: named groupings of bikes (rental fleets, demo
    # lineups, race teams, shop customer rosters). Nested under the
    # shared ``advanced`` group so ``motodiag advanced fleet {...}`` is
    # grouped with the other Track F subcommands in ``--help`` output.

    @advanced_group.group("fleet")
    def fleet_group() -> None:
        """Manage fleets: groupings of bikes for rental / demo / race / customer."""

    # --- fleet create -------------------------------------------------
    @fleet_group.command("create")
    @click.argument("name")
    @click.option(
        "--description", "description", default=None,
        help="Optional free-text description.",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of a Rich panel.",
    )
    def fleet_create_cmd(
        name: str,
        description: Optional[str],
        json_output: bool,
    ) -> None:
        """Create a new fleet.

        Raises a clean error when the name already exists under the
        current owner (UNIQUE(owner_user_id, name)).
        """
        from motodiag.advanced.fleet_repo import (
            FleetNameExistsError,
            create_fleet,
        )

        console = get_console()
        init_db()
        try:
            fleet_id = create_fleet(name=name, description=description)
        except FleetNameExistsError as exc:
            raise click.ClickException(str(exc)) from exc
        if json_output:
            click.echo(_json.dumps({
                "fleet_id": fleet_id,
                "name": name,
                "description": description,
            }, indent=2))
            return
        body = f"[green]{ICON_OK} Created fleet #{fleet_id}[/green]\n\n[bold]{name}[/bold]"
        if description:
            body += f"\n[dim]{description}[/dim]"
        console.print(
            Panel(
                body,
                title="Fleet created",
                border_style="green",
            )
        )

    # --- fleet list ---------------------------------------------------
    @fleet_group.command("list")
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of the Rich table.",
    )
    def fleet_list_cmd(json_output: bool) -> None:
        """List fleets with bike counts."""
        from motodiag.advanced.fleet_repo import list_fleets

        console = get_console()
        init_db()
        fleets = list_fleets()
        if json_output:
            click.echo(_json.dumps({"fleets": fleets}, indent=2, default=str))
            return
        if not fleets:
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} No fleets yet.[/yellow]\n\n"
                    "[dim]Create one with [bold]motodiag advanced fleet "
                    "create <name>[/bold].[/dim]",
                    title="No fleets",
                    border_style="yellow",
                )
            )
            return
        table = Table(
            title=f"Fleets ({len(fleets)})",
            header_style="bold cyan",
        )
        table.add_column("ID", no_wrap=True, justify="right")
        table.add_column("Name")
        table.add_column("Description", overflow="fold", max_width=40)
        table.add_column("Bikes", no_wrap=True, justify="right")
        table.add_column("Created", no_wrap=True)
        for f in fleets:
            table.add_row(
                str(f.get("id", "")),
                f.get("name", "") or "",
                f.get("description", "") or "[dim]-[/dim]",
                str(f.get("bike_count", 0) or 0),
                str(f.get("created_at", "") or "")[:10],
            )
        console.print(table)

    # --- fleet show ---------------------------------------------------
    @fleet_group.command("show")
    @click.argument("fleet")
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of Rich tables.",
    )
    def fleet_show_cmd(fleet: str, json_output: bool) -> None:
        """Show a fleet's details + bike roster."""
        from motodiag.advanced.fleet_repo import list_bikes_in_fleet

        console = get_console()
        init_db()
        fleet_row = _resolve_fleet_or_die(fleet)
        bikes = list_bikes_in_fleet(int(fleet_row["id"]))
        if json_output:
            click.echo(_json.dumps({
                "fleet": fleet_row,
                "bikes": bikes,
            }, indent=2, default=str))
            return
        console.print(
            Panel(
                f"[bold]{fleet_row.get('name')}[/bold]\n"
                f"[dim]{fleet_row.get('description') or '(no description)'}[/dim]\n"
                f"Bikes: {len(bikes)}",
                title=f"Fleet #{fleet_row.get('id')}",
                border_style="cyan",
            )
        )
        if not bikes:
            console.print(
                "[dim]No bikes in this fleet yet. Add one with "
                "[bold]motodiag advanced fleet add-bike[/bold].[/dim]"
            )
            return
        table = Table(header_style="bold cyan")
        table.add_column("Bike", no_wrap=True, justify="right")
        table.add_column("Make / Model / Year")
        table.add_column("Role", no_wrap=True)
        table.add_column("Added", no_wrap=True)
        for b in bikes:
            table.add_row(
                f"#{b.get('id', '')}",
                f"{b.get('year', '')} {b.get('make', '')} {b.get('model', '')}",
                b.get("role", "") or "",
                str(b.get("added_at", "") or "")[:10],
            )
        console.print(table)

    # --- fleet add-bike ----------------------------------------------
    @fleet_group.command("add-bike")
    @click.argument("fleet")
    @click.option(
        "--bike", "bike", required=True,
        help="Garage bike slug to add (same grammar as `advanced predict --bike`).",
    )
    @click.option(
        "--role",
        type=click.Choice(
            ["rental", "demo", "race", "customer"], case_sensitive=False,
        ),
        default="customer", show_default=True,
        help="Role for this bike in the fleet.",
    )
    def fleet_add_bike_cmd(fleet: str, bike: str, role: str) -> None:
        """Add a bike to a fleet."""
        from motodiag.advanced.fleet_repo import (
            BikeAlreadyInFleetError,
            add_bike_to_fleet,
        )

        console = get_console()
        init_db()
        fleet_row = _resolve_fleet_or_die(fleet)

        from motodiag.cli.diagnose import _resolve_bike_slug

        resolved = _resolve_bike_slug(bike)
        if resolved is None:
            _render_bike_not_found(console, bike)
            raise click.exceptions.Exit(1)

        try:
            add_bike_to_fleet(
                int(fleet_row["id"]),
                int(resolved["id"]),
                role=role,
            )
        except BikeAlreadyInFleetError as exc:
            raise click.ClickException(str(exc)) from exc
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        console.print(
            f"[green]{ICON_OK} Added "
            f"#{resolved['id']} ({resolved.get('year')} "
            f"{resolved.get('make')} {resolved.get('model')}) "
            f"to fleet '{fleet_row.get('name')}' as {role}.[/green]"
        )

    # --- fleet remove-bike -------------------------------------------
    @fleet_group.command("remove-bike")
    @click.argument("fleet")
    @click.option(
        "--bike", "bike", required=True,
        help="Garage bike slug to remove from the fleet.",
    )
    def fleet_remove_bike_cmd(fleet: str, bike: str) -> None:
        """Remove a bike from a fleet (vehicle record survives)."""
        from motodiag.advanced.fleet_repo import remove_bike_from_fleet

        console = get_console()
        init_db()
        fleet_row = _resolve_fleet_or_die(fleet)

        from motodiag.cli.diagnose import _resolve_bike_slug

        resolved = _resolve_bike_slug(bike)
        if resolved is None:
            _render_bike_not_found(console, bike)
            raise click.exceptions.Exit(1)

        removed = remove_bike_from_fleet(
            int(fleet_row["id"]), int(resolved["id"]),
        )
        if removed:
            console.print(
                f"[green]{ICON_OK} Removed #{resolved['id']} from "
                f"fleet '{fleet_row.get('name')}'.[/green]"
            )
        else:
            console.print(
                f"[yellow]{ICON_WARN} Bike #{resolved['id']} was not in "
                f"fleet '{fleet_row.get('name')}'.[/yellow]"
            )

    # --- fleet rename ------------------------------------------------
    @fleet_group.command("rename")
    @click.argument("fleet")
    @click.argument("new_name")
    def fleet_rename_cmd(fleet: str, new_name: str) -> None:
        """Rename a fleet."""
        from motodiag.advanced.fleet_repo import (
            FleetNameExistsError,
            rename_fleet,
        )

        console = get_console()
        init_db()
        fleet_row = _resolve_fleet_or_die(fleet)
        try:
            ok = rename_fleet(int(fleet_row["id"]), new_name)
        except FleetNameExistsError as exc:
            raise click.ClickException(str(exc)) from exc
        if ok:
            console.print(
                f"[green]{ICON_OK} Renamed fleet #{fleet_row['id']} -> "
                f"[bold]{new_name}[/bold][/green]"
            )
        else:
            raise click.ClickException(
                f"rename failed for fleet id={fleet_row['id']}"
            )

    # --- fleet delete ------------------------------------------------
    @fleet_group.command("delete")
    @click.argument("fleet")
    @click.option(
        "--force", "force", is_flag=True, default=False,
        help="Skip the confirmation prompt.",
    )
    def fleet_delete_cmd(fleet: str, force: bool) -> None:
        """Delete a fleet. Bikes survive (CASCADE drops junction only)."""
        from motodiag.advanced.fleet_repo import delete_fleet

        console = get_console()
        init_db()
        fleet_row = _resolve_fleet_or_die(fleet)
        if not force:
            confirm = click.confirm(
                f"Delete fleet '{fleet_row.get('name')}' "
                f"(id={fleet_row.get('id')})? Bikes will survive.",
                default=False,
            )
            if not confirm:
                console.print("[yellow]Aborted.[/yellow]")
                return
        ok = delete_fleet(int(fleet_row["id"]))
        if ok:
            console.print(
                f"[green]{ICON_OK} Deleted fleet #{fleet_row['id']} "
                f"('{fleet_row.get('name')}').[/green]"
            )
        else:
            raise click.ClickException(
                f"delete failed for fleet id={fleet_row['id']}"
            )

    # --- fleet status ------------------------------------------------
    @fleet_group.command("status")
    @click.argument("fleet")
    @click.option(
        "--horizon-days", type=int, default=180, show_default=True,
        help="Passed to predict_failures for each bike in the fleet.",
    )
    @click.option(
        "--min-severity",
        type=click.Choice(
            ["low", "medium", "high", "critical"], case_sensitive=False,
        ),
        default=None,
        help="Drop predictions below this severity for all bikes.",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of Rich tables + panel.",
    )
    def fleet_status_cmd(
        fleet: str,
        horizon_days: int,
        min_severity: Optional[str],
        json_output: bool,
    ) -> None:
        """Roll up predictions + wear + open sessions for every bike in a fleet."""
        from motodiag.advanced.fleet_analytics import fleet_status_summary

        console = get_console()
        init_db()
        fleet_row = _resolve_fleet_or_die(fleet)
        if horizon_days < 1:
            raise click.ClickException("--horizon-days must be >= 1.")

        summary = fleet_status_summary(
            int(fleet_row["id"]),
            horizon_days=horizon_days,
            min_severity=min_severity,
        )
        if json_output:
            click.echo(_json.dumps(summary, indent=2, default=str))
            return

        _render_fleet_status(console, summary)


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


# --- Phase 156: compare helpers ----------------------------------------


def _latest_recording_for_vehicle(vehicle_id: int) -> Optional[int]:
    """Return the most-recent stopped recording ID for a vehicle, or None.

    Only considers stopped recordings (``stopped_at IS NOT NULL``) so we
    don't accidentally peer-compare a live session still buffering
    samples.
    """
    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM sensor_recordings "
                "WHERE vehicle_id = ? AND stopped_at IS NOT NULL "
                "ORDER BY started_at DESC LIMIT 1",
                (int(vehicle_id),),
            ).fetchone()
    except Exception:
        return None
    if row is None:
        return None
    return int(row["id"])


def _run_comparison(
    console,
    *,
    vehicle_recording_id: int,
    pid_hex: str,
    cohort_filter: str,
    metric: str,
    peers_min: int,
    json_output: bool,
) -> None:
    """Invoke :func:`compare_against_peers` + render or JSON-emit."""
    try:
        comparison = compare_against_peers(
            vehicle_recording_id=vehicle_recording_id,
            pid_hex=pid_hex,
            cohort_filter=cohort_filter,
            metric=metric,
            peers_min=peers_min,
        )
    except ValueError as exc:
        # Orphan recording or unknown recording ID — red panel + exit 1.
        console.print(
            Panel(
                f"[red]{str(exc)}[/red]",
                title="Comparison failed",
                border_style="red",
            )
        )
        raise click.exceptions.Exit(1) from exc

    if json_output:
        _emit_comparison_json(comparison)
        return

    _render_comparison(console, comparison)


def _emit_comparison_json(comparison: PeerComparison) -> None:
    """Emit the comparison as JSON via ``click.echo``.

    We construct a plain-dict shape rather than :func:`dataclasses.asdict`
    so the serialization stays stable if we add fields that should not
    land in the CLI contract (e.g. internal debug counters).
    """
    cohort = comparison.cohort
    payload = {
        "vehicle_recording_id": comparison.vehicle_recording_id,
        "pid_hex": comparison.pid_hex,
        "pid_name": comparison.pid_name,
        "target_summary": comparison.target_summary,
        "bucket": comparison.bucket,
        "anomaly_flag": comparison.anomaly_flag,
        "cohort_filter": comparison.cohort_filter,
        "cohort": {
            "size": cohort.cohort_size,
            "distinct_bikes": cohort.distinct_bikes,
            "p25": cohort.p25,
            "p50": cohort.p50,
            "p75": cohort.p75,
            "p95": cohort.p95,
            "unit": cohort.unit,
            "metric": cohort.metric,
            "warning": cohort.warning,
        },
    }
    click.echo(_json.dumps(payload, indent=2, default=str))


def _render_comparison(console, comparison: PeerComparison) -> None:
    """Render the comparison as a Rich Table + summary panel."""
    cohort = comparison.cohort

    # Yellow panel — fleet unavailable OR insufficient cohort.
    if cohort.warning and "Phase 150" in cohort.warning:
        console.print(
            Panel(
                f"[yellow]{ICON_WARN} {cohort.warning}[/yellow]",
                title="Phase 150 required",
                border_style="yellow",
            )
        )
        return
    if cohort.cohort_size == 0:
        console.print(
            Panel(
                f"[yellow]{ICON_WARN} No peer recordings found for "
                f"PID {comparison.pid_hex} "
                f"({comparison.pid_name}) under cohort "
                f"'{comparison.cohort_filter}'.[/yellow]\n\n"
                "[dim]Try a wider --cohort, or seed more recordings "
                "via [bold]motodiag hardware log start[/bold].[/dim]",
                title="Insufficient cohort",
                border_style="yellow",
            )
        )
        return
    if cohort.warning:
        console.print(
            Panel(
                f"[yellow]{ICON_WARN} {cohort.warning}[/yellow]",
                title="Insufficient cohort",
                border_style="yellow",
            )
        )
        # Continue — render what we have so the mechanic sees the
        # percentiles even when the cohort is small.

    unit = f" {cohort.unit}" if cohort.unit else ""

    table = Table(
        title=(
            f"Peer comparison — {comparison.pid_name} "
            f"({comparison.pid_hex}) vs cohort '{comparison.cohort_filter}'"
        ),
        header_style="bold cyan",
    )
    table.add_column("Band", style="dim", no_wrap=True)
    table.add_column("Value", no_wrap=True)

    def _fmt(v: Optional[float]) -> str:
        return f"{v:.2f}{unit}" if v is not None else "[dim]-[/dim]"

    target_style = "red" if comparison.anomaly_flag else "green"
    target_cell = (
        f"[{target_style}]{_fmt(comparison.target_summary)}[/{target_style}]"
        if comparison.target_summary is not None
        else "[dim]PID not recorded in target[/dim]"
    )
    table.add_row("target", target_cell)
    table.add_row("p25", _fmt(cohort.p25))
    table.add_row("p50 (median)", _fmt(cohort.p50))
    table.add_row("p75", _fmt(cohort.p75))
    table.add_row("p95", _fmt(cohort.p95))

    console.print(table)

    # --- Footer ---
    footer_parts = [
        f"cohort size: {cohort.cohort_size}",
        f"distinct bikes: {cohort.distinct_bikes}",
        f"metric: {cohort.metric}",
    ]
    if comparison.bucket:
        bucket_color = "red" if comparison.anomaly_flag else "cyan"
        footer_parts.append(
            f"bucket: [{bucket_color}]{comparison.bucket}[/{bucket_color}]"
        )
    console.print("\n" + "   •   ".join(footer_parts))

    if comparison.anomaly_flag:
        console.print(
            f"[red]{ICON_WARN} Anomaly — target is in the "
            f"'{comparison.bucket}' tail of the peer cohort.[/red]"
        )
    elif comparison.bucket is not None:
        console.print(
            f"[dim]{ICON_OK} Target within normal peer range "
            f"({comparison.bucket}).[/dim]"
        )
    console.print(
        "[dim]hint: pass [bold]--json[/bold] for machine-readable output, "
        "or re-run with [bold]--cohort strict[/bold] for a tighter peer set.[/dim]"
    )


# --- Phase 158: drift rendering helpers --------------------------------


# Bucket → Rich style. Cyan = stable (default, comforting), yellow =
# slow drift (watch it), red = fast drift (act). Mirrors the Phase 148
# confidence palette so a mechanic's eye learns one color grammar.
_DRIFT_BUCKET_STYLES: dict[str, str] = {
    "stable": "cyan",
    "drifting-slow": "yellow",
    "drifting-fast": "red",
}


def _format_drift_bucket(bucket_value: str) -> str:
    """Return a Rich markup string for a :class:`DriftBucket` label."""
    style = _DRIFT_BUCKET_STYLES.get(bucket_value, "dim")
    return f"[{style}]{bucket_value}[/{style}]"


def _render_drift_bike(console, result) -> None:
    """Rich panel for ``advanced drift bike`` output.

    Single-PID deep-dive — shows slope, r², signed drift %, mean value,
    sample/recording count, and the full span covered by the data.
    """
    bucket_markup = _format_drift_bucket(result.bucket.value)
    pct = result.drift_pct_per_30_days
    pct_style = "red" if abs(pct) >= 10.0 else (
        "yellow" if abs(pct) >= 5.0 else "green"
    )
    pct_sign = "+" if pct > 0 else ""
    body = (
        f"[bold]{result.pid_name}[/bold] "
        f"({result.pid_hex}, {result.unit or '—'})\n\n"
        f"Bucket:           {bucket_markup}\n"
        f"Drift/30 days:    "
        f"[{pct_style}]{pct_sign}{pct:.2f} %[/{pct_style}]\n"
        f"Slope / day:      {result.slope_per_day:+.6f} "
        f"{result.unit or ''}\n"
        f"Intercept:        {result.intercept:.4f}\n"
        f"R² (fit quality): {result.r_squared:.4f}\n"
        f"Mean value:       {result.mean_value:.4f} "
        f"{result.unit or ''}\n"
        f"Samples:          {result.n_samples} across "
        f"{result.n_recordings} recording(s)\n"
        f"Span:             {result.span_days:.1f} days  "
        f"({result.first_captured_at} → {result.last_captured_at})"
    )
    border = _DRIFT_BUCKET_STYLES.get(result.bucket.value, "cyan")
    console.print(
        Panel(
            body,
            title=f"Sensor drift — bike #{result.vehicle_id}",
            border_style=border,
        )
    )


def _render_drift_summary(
    console,
    summary: dict,
    vehicle_id: int,
    threshold_pct: float,
) -> None:
    """Three-bucket table for ``advanced drift show``.

    Rows group by bucket (stable, drifting-slow, drifting-fast) with
    colored bucket labels and signed drift percentages. Empty buckets
    are still surfaced with a dim placeholder so a mechanic can see at
    a glance that "nothing is fast-drifting" is a real answer.
    """
    total = sum(len(v) for v in summary.values())
    table = Table(
        title=(
            f"Sensor drift summary — bike #{vehicle_id} "
            f"(threshold ±{threshold_pct} %/30 d, {total} PIDs)"
        ),
        header_style="bold cyan",
    )
    table.add_column("Bucket", no_wrap=True)
    table.add_column("PID", no_wrap=True)
    table.add_column("Name", overflow="fold", max_width=40)
    table.add_column("Drift %/30d", no_wrap=True)
    table.add_column("R²", no_wrap=True)
    table.add_column("n_samples", no_wrap=True, justify="right")

    # Render fast first (most urgent), then slow, then stable.
    for bucket_key in ("drifting-fast", "drifting-slow", "stable"):
        rows = summary.get(bucket_key, [])
        if not rows:
            table.add_row(
                _format_drift_bucket(bucket_key),
                "[dim]—[/dim]", "[dim](none)[/dim]",
                "[dim]—[/dim]", "[dim]—[/dim]", "[dim]—[/dim]",
            )
            continue
        for r in rows:
            pct = r.drift_pct_per_30_days
            pct_sign = "+" if pct > 0 else ""
            pct_style = _DRIFT_BUCKET_STYLES.get(bucket_key, "dim")
            table.add_row(
                _format_drift_bucket(bucket_key),
                r.pid_hex,
                r.pid_name,
                f"[{pct_style}]{pct_sign}{pct:.2f}[/{pct_style}]",
                f"{r.r_squared:.3f}",
                str(r.n_samples),
            )
    console.print(table)

    if summary.get("drifting-fast"):
        n_fast = len(summary["drifting-fast"])
        console.print(
            f"[red]{ICON_WARN} {n_fast} PID(s) drifting fast — "
            f"inspect before next service interval.[/red]"
        )
    elif summary.get("drifting-slow"):
        n_slow = len(summary["drifting-slow"])
        console.print(
            f"[yellow]{ICON_WARN} {n_slow} PID(s) drifting slowly — "
            f"monitor over next recordings.[/yellow]"
        )
    else:
        console.print(
            f"[green]{ICON_OK} All sensors stable within "
            f"±{threshold_pct} %/30 d.[/green]"
        )


def _render_drift_recording(
    console,
    recording_id: int,
    vehicle_id,
    results: list[dict],
) -> None:
    """Rich table for ``advanced drift recording`` output.

    Shows per-PID intra-session drift with a mini sparkline so the
    mechanic sees the shape of each channel at a glance.
    """
    if not results:
        console.print(
            Panel(
                f"[yellow]{ICON_WARN} Recording #{recording_id} does "
                f"not have ≥2 samples on any PID — can't fit a "
                f"trend.[/yellow]",
                title="Insufficient data",
                border_style="yellow",
            )
        )
        return

    vid_label = f"#{vehicle_id}" if vehicle_id is not None else "unknown"
    table = Table(
        title=(
            f"Intra-session drift — recording #{recording_id} "
            f"(bike {vid_label}, {len(results)} PIDs)"
        ),
        header_style="bold cyan",
    )
    table.add_column("PID", no_wrap=True)
    table.add_column("Name", overflow="fold", max_width=28)
    table.add_column("Drift %/30d", no_wrap=True)
    table.add_column("R²", no_wrap=True)
    table.add_column("n", no_wrap=True, justify="right")
    table.add_column("Sparkline", no_wrap=True)

    for r in results:
        pct = float(r.get("drift_pct_per_30_days") or 0.0)
        pct_sign = "+" if pct > 0 else ""
        style = "red" if abs(pct) >= 10.0 else (
            "yellow" if abs(pct) >= 5.0 else "cyan"
        )
        table.add_row(
            r.get("pid_hex", "") or "",
            r.get("pid_name", "") or "",
            f"[{style}]{pct_sign}{pct:.2f}[/{style}]",
            f"{float(r.get('r_squared') or 0.0):.3f}",
            str(r.get("n_samples", 0)),
            r.get("sparkline", "") or "",
        )
    console.print(table)


def _render_wear_matches(console, matches, bike_label: str) -> None:
    """Render the 6-column Rich table for the Phase 149 ``wear`` command.

    Columns: Component | Confidence (colored) | Matched (35-char fold) |
    Unmatched (dim 25-char fold) | Inspection steps (55-char fold) |
    Verified by (dim). Confidence coloring follows Phase 148's scheme:
    cyan = high, yellow = medium, dim = low — mechanic's eyes drift to
    cyan rows first, which is what we want for actionable matches.
    """
    table = Table(
        title=f"Wear pattern matches ({len(matches)})",
        header_style="bold cyan",
    )
    table.add_column("Component", overflow="fold", max_width=25)
    table.add_column("Confidence")
    table.add_column("Matched", overflow="fold", max_width=35)
    table.add_column("Unmatched", overflow="fold", max_width=25, style="dim")
    table.add_column("Inspection steps", overflow="fold", max_width=55)
    table.add_column("Verified by", style="dim")

    for m in matches:
        # Confidence color: cyan >= 0.75 (HIGH), yellow >= 0.5 (MEDIUM),
        # dim otherwise. Same three-band palette as Phase 148.
        score = m.confidence_score
        if score >= 0.75:
            color = "cyan"
        elif score >= 0.5:
            color = "yellow"
        else:
            color = "dim"
        conf_cell = f"[{color}]{score:.2f}[/{color}]"

        matched_cell = "\n".join(f"• {s}" for s in m.symptoms_matched) or "-"
        unmatched_cell = (
            "\n".join(f"• {s}" for s in m.symptoms_unmatched) or "-"
        )
        steps_cell = "\n".join(
            f"{i + 1}. {step}" for i, step in enumerate(m.inspection_steps)
        ) or "-"

        table.add_row(
            m.component,
            conf_cell,
            matched_cell,
            unmatched_cell,
            steps_cell,
            m.verified_by,
        )
    console.print(table)

    # Footer — forum-citation count honors the "every Track B phase
    # must include forum-sourced fixes" user-memory priority (same
    # surface Phase 148 uses for forum-verified predictions).
    forum_count = sum(
        1 for m in matches if "forum" in (m.verified_by or "").lower()
    )
    console.print(
        f"\n[bold]{bike_label}[/bold]   •   "
        f"{len(matches)} matches shown"
    )
    if forum_count:
        console.print(
            f"[dim]{ICON_OK} {forum_count} of {len(matches)} matches "
            f"cite forum consensus.[/dim]"
        )
    console.print(
        "[dim]hint: pass [bold]--json[/bold] for machine-readable output.[/dim]"
    )


# --- Phase 150: fleet helpers ------------------------------------------


def _resolve_fleet_or_die(fleet: str) -> dict:
    """Resolve a fleet identifier (id string or name) or raise ClickException.

    Accepts either an integer id (as a string — Click-argument) or a
    human-readable name. Used by every `fleet <subcmd>` to normalize
    fleet addressing. Owner scoping defaults to the system user (id=1).
    """
    from motodiag.advanced.fleet_repo import (
        FleetNotFoundError,
        _resolve_fleet,
    )

    identifier: int | str
    raw = str(fleet).strip()
    if raw.isdigit():
        identifier = int(raw)
    else:
        identifier = raw
    try:
        return _resolve_fleet(identifier)
    except FleetNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc


def _render_fleet_status(console, summary: dict) -> None:
    """Render the Rich output for `fleet status`.

    Per-bike table + totals panel. Critical prediction counts render
    in red; open-session > 0 renders in yellow. A dim em-dash fills
    ``wear_percent`` when Phase 149 isn't available (the soft-guard
    branch).
    """
    fleet = summary.get("fleet", {})
    bikes = summary.get("bikes", [])
    totals = summary.get("totals", {})
    phase149_available = bool(summary.get("phase149_available"))

    console.print(
        Panel(
            f"[bold]{fleet.get('name')}[/bold]\n"
            f"[dim]{fleet.get('description') or '(no description)'}[/dim]\n"
            f"Bikes: {fleet.get('bike_count', 0)}   •   "
            f"Horizon: {summary.get('horizon_days')}d   •   "
            f"Min-severity: {summary.get('min_severity') or 'all'}",
            title=f"Fleet status #{fleet.get('id')}",
            border_style="cyan",
        )
    )

    if not bikes:
        console.print(
            "[dim]No bikes in this fleet. Add one with "
            "[bold]motodiag advanced fleet add-bike[/bold].[/dim]"
        )
        return

    table = Table(
        title=f"Per-bike summary ({len(bikes)})",
        header_style="bold cyan",
    )
    table.add_column("Bike", no_wrap=True, justify="right")
    table.add_column("Make / Model / Year")
    table.add_column("Role", no_wrap=True)
    table.add_column("Predictions", no_wrap=True, justify="right")
    table.add_column("Critical", no_wrap=True, justify="right")
    table.add_column("Top issue", overflow="fold", max_width=35)
    table.add_column("Wear %", no_wrap=True, justify="right")
    table.add_column("Open sessions", no_wrap=True, justify="right")

    for b in bikes:
        crit = int(b.get("critical_prediction_count") or 0)
        crit_cell = f"[red]{crit}[/red]" if crit > 0 else str(crit)
        open_count = int(b.get("open_sessions") or 0)
        open_cell = (
            f"[yellow]{open_count}[/yellow]" if open_count > 0
            else str(open_count)
        )
        wear = b.get("wear_percent")
        if wear is None:
            wear_cell = "[dim]-[/dim]"
        else:
            wear_cell = f"{float(wear):.1f}"
        table.add_row(
            f"#{b.get('vehicle_id', '')}",
            f"{b.get('year', '')} {b.get('make', '')} {b.get('model', '')}",
            b.get("role", "") or "",
            str(b.get("prediction_count") or 0),
            crit_cell,
            b.get("top_prediction") or "[dim]-[/dim]",
            wear_cell,
            open_cell,
        )
    console.print(table)

    totals_body = (
        f"Total predictions: [bold]{totals.get('total_predictions', 0)}[/bold]\n"
        f"Critical: [red]{totals.get('critical_predictions', 0)}[/red]\n"
        f"Bikes w/ critical: {totals.get('bikes_with_critical', 0)}\n"
        f"Bikes w/ open sessions: [yellow]"
        f"{totals.get('bikes_with_open_sessions', 0)}[/yellow]\n"
    )
    avg_wear = totals.get("average_wear_percent")
    if avg_wear is not None:
        totals_body += f"Average wear %: {float(avg_wear):.1f}\n"
    if not phase149_available:
        totals_body += (
            "[dim]Phase 149 wear analytics not available — `wear %` "
            "columns render `-`.[/dim]"
        )
    console.print(
        Panel(
            totals_body.strip(),
            title="Fleet totals",
            border_style="magenta",
        )
    )
