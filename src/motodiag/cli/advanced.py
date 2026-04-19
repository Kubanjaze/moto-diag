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

import csv
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


# Phase 157 — confidence-ramp mapping for baseline tables. Ramp from
# dim (confidence 1) through cyan (5) so the eye tracks the strongest
# baselines at a glance.
_BASELINE_CONF_STYLES: dict[int, str] = {
    1: "dim",
    2: "yellow",
    3: "green",
    4: "cyan",
    5: "bold cyan",
}


def _format_baseline_confidence(conf: int) -> str:
    """Wrap a 1-5 confidence integer in its Rich ramp style."""
    style = _BASELINE_CONF_STYLES.get(int(conf), "dim")
    return f"[{style}]{int(conf)}[/{style}]"


def _fmt_num(value) -> str:
    """Format a numeric cell for baseline tables; em-dash on None."""
    if value is None:
        return "[dim]—[/dim]"
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return str(value)


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
            # Phase 152 — mileage_source tagging. The predictor's +0.05
            # bonus fires only for "db"-sourced readings (vehicle row
            # column populated by logged service events). A user-
            # asserted --current-miles value always wins over the DB
            # (cluster replacements, borrowed readings, etc.) but that
            # override comes with "flag" source — no bonus — so
            # Phase 148's regression surface is unchanged for the
            # direct-mileage call shape.
            db_mileage = vehicle.get("mileage")
            if current_miles is not None:
                vehicle["mileage"] = int(current_miles)
                vehicle["mileage_source"] = "flag"
            elif db_mileage is not None:
                vehicle["mileage_source"] = "db"
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
                # Direct-args mode always treats the flag as user-
                # asserted. No +0.05 bonus.
                "mileage_source": (
                    "flag" if current_miles is not None else None
                ),
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

    # --- history subgroup (Phase 152) --------------------------------
    #
    # Per-bike service-event log. Five subcommands wrap the thin
    # history_repo CRUD layer with Rich tables + ``--json`` mirroring
    # the Phase 148 rendering conventions.

    @advanced_group.group("history")
    def history_group() -> None:
        """Per-bike service-event log: add, list, show, show-all, by-type."""

    # --- history add ---
    @history_group.command("add")
    @click.option(
        "--bike", required=True,
        help="Garage bike slug (e.g. sportster-2010).",
    )
    @click.option(
        "--type", "event_type",
        type=click.Choice(
            [
                "oil-change", "tire", "valve-adjust", "brake",
                "diagnostic", "recall", "chain", "coolant",
                "air-filter", "spark-plug", "custom",
            ],
            case_sensitive=False,
        ),
        required=True,
        help="Event type (matches the 11-value CHECK vocabulary).",
    )
    @click.option(
        "--at-miles", type=int, default=None,
        help="Mileage at which the event happened. Optional.",
    )
    @click.option(
        "--at-date", "at_date_str", default=None,
        help="ISO-8601 date (YYYY-MM-DD). Defaults to today.",
    )
    @click.option(
        "--notes", default=None,
        help="Free-form notes for the mechanic's record.",
    )
    @click.option(
        "--cost-cents", type=int, default=None,
        help="Cost in cents (e.g. 4999 for $49.99). Optional.",
    )
    @click.option(
        "--mechanic", default=None,
        help=(
            "Mechanic username (resolved to users.id). "
            "Stored as NULL if the auth layer is unavailable."
        ),
    )
    @click.option(
        "--parts", default=None,
        help="Comma-separated part SKUs (e.g. 'O-125,FILT-9').",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON for the created event.",
    )
    def history_add_cmd(
        bike: str,
        event_type: str,
        at_miles: Optional[int],
        at_date_str: Optional[str],
        notes: Optional[str],
        cost_cents: Optional[int],
        mechanic: Optional[str],
        parts: Optional[str],
        json_output: bool,
    ) -> None:
        """Log a completed service event for a bike."""
        from datetime import date as _d
        from motodiag.advanced.history_repo import (
            add_service_event,
            get_service_event,
        )
        from motodiag.advanced.models import ServiceEvent
        from motodiag.cli.diagnose import _resolve_bike_slug

        console = get_console()
        init_db()

        resolved = _resolve_bike_slug(bike)
        if resolved is None:
            _render_bike_not_found(console, bike)
            raise click.exceptions.Exit(1)
        vehicle_id = int(resolved["id"])

        # Parse --at-date (default today).
        if at_date_str:
            try:
                at_date = _d.fromisoformat(at_date_str)
            except ValueError as exc:
                raise click.ClickException(
                    f"--at-date must be ISO-8601 (YYYY-MM-DD); got {at_date_str!r}: {exc}"
                ) from exc
        else:
            at_date = _d.today()

        # Resolve --mechanic → users.id (best effort; NULL fallback).
        mechanic_user_id: Optional[int] = None
        if mechanic:
            try:
                from motodiag.auth.users_repo import get_user_by_username

                row = get_user_by_username(mechanic)
                if row is not None:
                    mechanic_user_id = int(row["id"])
                else:
                    console.print(
                        f"[yellow]{ICON_WARN} Unknown mechanic "
                        f"username {mechanic!r}; attribution left NULL.[/yellow]"
                    )
            except Exception as exc:
                console.print(
                    f"[yellow]{ICON_WARN} Could not resolve mechanic "
                    f"{mechanic!r} ({exc}); attribution left NULL.[/yellow]"
                )

        try:
            event = ServiceEvent(
                vehicle_id=vehicle_id,
                event_type=event_type,
                at_miles=at_miles,
                at_date=at_date,
                notes=notes,
                cost_cents=cost_cents,
                mechanic_user_id=mechanic_user_id,
                parts_csv=parts,
            )
        except Exception as exc:
            raise click.ClickException(
                f"Invalid service event: {exc}"
            ) from exc

        event_id = add_service_event(event)
        row = get_service_event(event_id)

        if json_output:
            click.echo(_json.dumps(row, indent=2, default=str))
            return

        console.print(
            Panel(
                f"[green]{ICON_OK} Logged {event_type} event "
                f"(#{event_id}) on {at_date.isoformat()} for bike "
                f"#{vehicle_id}.[/green]",
                title="Service event recorded",
                border_style="green",
            )
        )

    # --- history list ---
    @history_group.command("list")
    @click.option(
        "--bike", required=True,
        help="Garage bike slug.",
    )
    @click.option(
        "--since", default=None,
        help="ISO-8601 date (inclusive). Drops earlier rows.",
    )
    @click.option(
        "--until", default=None,
        help="ISO-8601 date (inclusive). Drops later rows.",
    )
    @click.option(
        "--type", "event_type",
        type=click.Choice(
            [
                "oil-change", "tire", "valve-adjust", "brake",
                "diagnostic", "recall", "chain", "coolant",
                "air-filter", "spark-plug", "custom",
            ],
            case_sensitive=False,
        ),
        default=None,
        help="Filter to one event_type.",
    )
    @click.option(
        "--limit", type=int, default=50, show_default=True,
        help="Max rows to return.",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON list instead of the Rich table.",
    )
    def history_list_cmd(
        bike: str,
        since: Optional[str],
        until: Optional[str],
        event_type: Optional[str],
        limit: int,
        json_output: bool,
    ) -> None:
        """List service events for a bike (newest first)."""
        from motodiag.advanced.history_repo import list_service_events
        from motodiag.cli.diagnose import _resolve_bike_slug

        console = get_console()
        init_db()

        resolved = _resolve_bike_slug(bike)
        if resolved is None:
            _render_bike_not_found(console, bike)
            raise click.exceptions.Exit(1)
        vehicle_id = int(resolved["id"])

        rows = list_service_events(
            vehicle_id,
            since=since,
            until=until,
            event_type=event_type,
            limit=limit,
        )
        bike_label = (
            f"#{vehicle_id}  {resolved.get('year')} "
            f"{resolved.get('make')} {resolved.get('model')}"
        )

        if json_output:
            click.echo(_json.dumps(rows, indent=2, default=str))
            return

        if not rows:
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} No service events for "
                    f"{bike_label}.[/yellow]\n\n"
                    "[dim]Log one with "
                    "[bold]motodiag advanced history add[/bold].[/dim]",
                    title="No events",
                    border_style="yellow",
                )
            )
            return

        _render_history_rows(console, rows, bike_label=bike_label)

    # --- history show ---
    @history_group.command("show")
    @click.argument("event_id", type=int)
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of a panel.",
    )
    def history_show_cmd(event_id: int, json_output: bool) -> None:
        """Show one service event by id."""
        from motodiag.advanced.history_repo import get_service_event

        console = get_console()
        init_db()

        row = get_service_event(event_id)
        if row is None:
            raise click.ClickException(
                f"No service event with id {event_id}."
            )
        if json_output:
            click.echo(_json.dumps(row, indent=2, default=str))
            return

        body = (
            f"[bold]Event #{row['id']}[/bold]  "
            f"([cyan]{row['event_type']}[/cyan])\n"
            f"Bike: #{row['vehicle_id']}\n"
            f"Date: {row['at_date']}\n"
            f"Miles: {row['at_miles'] if row['at_miles'] is not None else '-'}\n"
            f"Cost: {_format_cost(row.get('cost_cents'))}\n"
            f"Mechanic: {row.get('mechanic_user_id') or '-'}\n"
            f"Parts: {row.get('parts_csv') or '-'}\n"
            f"Notes: {row.get('notes') or '-'}\n"
            f"[dim]Completed at: {row.get('completed_at')}[/dim]"
        )
        console.print(
            Panel(body, title="Service event", border_style="cyan")
        )

    # --- history show-all ---
    @history_group.command("show-all")
    @click.option(
        "--since", default=None, help="ISO-8601 date (inclusive).",
    )
    @click.option(
        "--until", default=None, help="ISO-8601 date (inclusive).",
    )
    @click.option(
        "--type", "event_type",
        type=click.Choice(
            [
                "oil-change", "tire", "valve-adjust", "brake",
                "diagnostic", "recall", "chain", "coolant",
                "air-filter", "spark-plug", "custom",
            ],
            case_sensitive=False,
        ),
        default=None,
        help="Filter to one event_type.",
    )
    @click.option(
        "--limit", type=int, default=100, show_default=True,
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
    )
    def history_show_all_cmd(
        since: Optional[str],
        until: Optional[str],
        event_type: Optional[str],
        limit: int,
        json_output: bool,
    ) -> None:
        """Cross-bike recent-events feed (newest first)."""
        from motodiag.advanced.history_repo import list_all_service_events

        console = get_console()
        init_db()

        rows = list_all_service_events(
            since=since, until=until,
            event_type=event_type, limit=limit,
        )
        if json_output:
            click.echo(_json.dumps(rows, indent=2, default=str))
            return

        if not rows:
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} No service events in "
                    f"the garage yet.[/yellow]\n\n"
                    "[dim]Log one with "
                    "[bold]motodiag advanced history add[/bold].[/dim]",
                    title="No events",
                    border_style="yellow",
                )
            )
            return

        _render_history_rows(
            console, rows, bike_label="all bikes", include_bike_col=True,
        )

    # --- history by-type ---
    @history_group.command("by-type")
    @click.argument(
        "event_type",
        type=click.Choice(
            [
                "oil-change", "tire", "valve-adjust", "brake",
                "diagnostic", "recall", "chain", "coolant",
                "air-filter", "spark-plug", "custom",
            ],
            case_sensitive=False,
        ),
    )
    @click.option(
        "--limit", type=int, default=100, show_default=True,
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
    )
    def history_by_type_cmd(
        event_type: str,
        limit: int,
        json_output: bool,
    ) -> None:
        """List all events of one type across the whole garage."""
        from motodiag.advanced.history_repo import list_by_type

        console = get_console()
        init_db()

        rows = list_by_type(event_type, limit=limit)
        if json_output:
            click.echo(_json.dumps(rows, indent=2, default=str))
            return

        if not rows:
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} No {event_type} "
                    "events in the garage yet.[/yellow]",
                    title="No events",
                    border_style="yellow",
                )
            )
            return

        _render_history_rows(
            console, rows, bike_label=f"type={event_type}",
            include_bike_col=True,
        )

    # --- Phase 151: ``advanced schedule`` nested subgroup ------------
    #
    # Service-interval scheduling. Six subcommands wrap the
    # schedule_repo + scheduler modules with Rich tables + ``--json``,
    # mirroring the Phase 148/150 rendering conventions. Nested under
    # the shared ``advanced`` group so ``motodiag advanced schedule
    # {...}`` groups with predict/fleet/history in ``--help``.

    @advanced_group.group("schedule")
    def schedule_group() -> None:
        """Service-interval scheduling: OEM maintenance cadence per bike."""

    # --- schedule init ------------------------------------------------
    @schedule_group.command("init")
    @click.option(
        "--bike", "bike", required=True,
        help="Garage bike slug (same grammar as `advanced predict --bike`).",
    )
    @click.option(
        "--templates", "templates_path", default=None,
        help="Optional alternate path to the templates JSON catalog.",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of the Rich table.",
    )
    def schedule_init_cmd(
        bike: str,
        templates_path: Optional[str],
        json_output: bool,
    ) -> None:
        """Seed per-bike service intervals from OEM templates.

        Loads the template catalog (idempotent — re-runs insert 0 new
        rows) then materializes per-bike service_intervals for every
        matching template slug the bike does not already have.
        """
        from motodiag.advanced.schedule_repo import (
            list_intervals,
            load_templates_from_json,
            seed_from_template,
        )

        console = get_console()
        init_db()
        from motodiag.cli.diagnose import _resolve_bike_slug

        resolved = _resolve_bike_slug(bike)
        if resolved is None:
            _render_bike_not_found(console, bike)
            raise click.exceptions.Exit(1)
        vehicle_id = int(resolved["id"])

        templates_loaded = load_templates_from_json(templates_path)
        created = seed_from_template(vehicle_id)
        intervals = list_intervals(vehicle_id)

        if json_output:
            click.echo(_json.dumps({
                "vehicle_id": vehicle_id,
                "templates_loaded": templates_loaded,
                "intervals_created": created,
                "intervals": intervals,
            }, indent=2, default=str))
            return

        console.print(
            Panel(
                f"[green]{ICON_OK} Seeded {created} new interval(s); "
                f"loaded {templates_loaded} new template(s).[/green]\n"
                f"Bike: [bold]#{vehicle_id} {resolved.get('year')} "
                f"{resolved.get('make')} {resolved.get('model')}[/bold]\n"
                f"Total intervals on bike: {len(intervals)}",
                title="Schedule initialized",
                border_style="green",
            )
        )
        if intervals:
            table = Table(header_style="bold cyan")
            table.add_column("Item", no_wrap=True)
            table.add_column("Description", overflow="fold", max_width=40)
            table.add_column("Every miles", no_wrap=True, justify="right")
            table.add_column("Every months", no_wrap=True, justify="right")
            for row in intervals:
                table.add_row(
                    row.get("item_slug", ""),
                    row.get("description", "") or "[dim]-[/dim]",
                    (
                        f"{int(row['every_miles']):,}"
                        if row.get("every_miles") is not None
                        else "[dim]-[/dim]"
                    ),
                    (
                        str(int(row["every_months"]))
                        if row.get("every_months") is not None
                        else "[dim]-[/dim]"
                    ),
                )
            console.print(table)

    # --- schedule list ------------------------------------------------
    @schedule_group.command("list")
    @click.option(
        "--bike", "bike", required=True,
        help="Garage bike slug.",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of the Rich table.",
    )
    def schedule_list_cmd(bike: str, json_output: bool) -> None:
        """List all service intervals configured for a bike."""
        from motodiag.advanced.schedule_repo import list_intervals

        console = get_console()
        init_db()
        from motodiag.cli.diagnose import _resolve_bike_slug

        resolved = _resolve_bike_slug(bike)
        if resolved is None:
            _render_bike_not_found(console, bike)
            raise click.exceptions.Exit(1)
        vehicle_id = int(resolved["id"])
        intervals = list_intervals(vehicle_id)

        if json_output:
            click.echo(_json.dumps({
                "vehicle_id": vehicle_id,
                "intervals": intervals,
            }, indent=2, default=str))
            return

        if not intervals:
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} No service intervals configured for "
                    f"bike #{vehicle_id}.[/yellow]\n\n"
                    "[dim]Run [bold]motodiag advanced schedule init --bike "
                    f"{bike}[/bold] to seed from OEM templates.[/dim]",
                    title="No intervals",
                    border_style="yellow",
                )
            )
            return

        table = Table(
            title=(
                f"Service intervals for #{vehicle_id} "
                f"{resolved.get('year')} {resolved.get('make')} "
                f"{resolved.get('model')} ({len(intervals)})"
            ),
            header_style="bold cyan",
        )
        table.add_column("Item", no_wrap=True)
        table.add_column("Description", overflow="fold", max_width=35)
        table.add_column("Every", no_wrap=True)
        table.add_column("Last done", no_wrap=True)
        table.add_column("Next due", no_wrap=True)
        for row in intervals:
            every_parts: list[str] = []
            if row.get("every_miles") is not None:
                every_parts.append(f"{int(row['every_miles']):,} mi")
            if row.get("every_months") is not None:
                every_parts.append(f"{int(row['every_months'])} mo")
            last_parts: list[str] = []
            if row.get("last_done_miles") is not None:
                last_parts.append(f"{int(row['last_done_miles']):,} mi")
            if row.get("last_done_at"):
                last_parts.append(str(row["last_done_at"])[:10])
            next_parts: list[str] = []
            if row.get("next_due_miles") is not None:
                next_parts.append(f"{int(row['next_due_miles']):,} mi")
            if row.get("next_due_at"):
                next_parts.append(str(row["next_due_at"])[:10])
            table.add_row(
                row.get("item_slug", ""),
                row.get("description", "") or "[dim]-[/dim]",
                " / ".join(every_parts) or "[dim]-[/dim]",
                " / ".join(last_parts) or "[dim]-[/dim]",
                " / ".join(next_parts) or "[dim]-[/dim]",
            )
        console.print(table)

    # --- schedule due -------------------------------------------------
    @schedule_group.command("due")
    @click.option(
        "--bike", "bike", required=True,
        help="Garage bike slug.",
    )
    @click.option(
        "--horizon-miles", type=int, default=500, show_default=True,
        help="Include intervals due within this many miles.",
    )
    @click.option(
        "--horizon-days", type=int, default=30, show_default=True,
        help="Include intervals due within this many days.",
    )
    @click.option(
        "--current-miles", type=int, default=None,
        help="Override current mileage (else read vehicles.mileage if available).",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of the Rich table.",
    )
    def schedule_due_cmd(
        bike: str,
        horizon_miles: int,
        horizon_days: int,
        current_miles: Optional[int],
        json_output: bool,
    ) -> None:
        """List intervals due within the miles/days horizon."""
        from motodiag.advanced.scheduler import due_items

        console = get_console()
        init_db()
        if horizon_miles < 0:
            raise click.ClickException("--horizon-miles must be >= 0.")
        if horizon_days < 0:
            raise click.ClickException("--horizon-days must be >= 0.")

        from motodiag.cli.diagnose import _resolve_bike_slug

        resolved = _resolve_bike_slug(bike)
        if resolved is None:
            _render_bike_not_found(console, bike)
            raise click.exceptions.Exit(1)
        vehicle_id = int(resolved["id"])

        items = due_items(
            vehicle_id,
            horizon_miles=horizon_miles,
            horizon_days=horizon_days,
            current_miles=current_miles,
        )

        if json_output:
            click.echo(_json.dumps({
                "vehicle_id": vehicle_id,
                "horizon_miles": horizon_miles,
                "horizon_days": horizon_days,
                "items": items,
            }, indent=2, default=str))
            return

        if not items:
            console.print(
                Panel(
                    f"[green]{ICON_OK} Nothing due within "
                    f"{horizon_miles:,} mi / {horizon_days} days for "
                    f"bike #{vehicle_id}.[/green]",
                    title="Nothing due",
                    border_style="green",
                )
            )
            return

        _render_schedule_rows(
            console,
            items,
            title=(
                f"Due soon ({len(items)}) — horizon {horizon_miles:,} mi "
                f"/ {horizon_days} days"
            ),
        )

    # --- schedule overdue --------------------------------------------
    @schedule_group.command("overdue")
    @click.option(
        "--bike", "bike", required=True,
        help="Garage bike slug.",
    )
    @click.option(
        "--current-miles", type=int, default=None,
        help="Override current mileage (else read vehicles.mileage if available).",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of the Rich table.",
    )
    def schedule_overdue_cmd(
        bike: str,
        current_miles: Optional[int],
        json_output: bool,
    ) -> None:
        """List intervals past their due-point, most-overdue first."""
        from motodiag.advanced.scheduler import overdue_items

        console = get_console()
        init_db()
        from motodiag.cli.diagnose import _resolve_bike_slug

        resolved = _resolve_bike_slug(bike)
        if resolved is None:
            _render_bike_not_found(console, bike)
            raise click.exceptions.Exit(1)
        vehicle_id = int(resolved["id"])

        items = overdue_items(vehicle_id, current_miles=current_miles)

        if json_output:
            click.echo(_json.dumps({
                "vehicle_id": vehicle_id,
                "items": items,
            }, indent=2, default=str))
            return

        if not items:
            console.print(
                Panel(
                    f"[green]{ICON_OK} Nothing overdue for "
                    f"bike #{vehicle_id}.[/green]",
                    title="All caught up",
                    border_style="green",
                )
            )
            return

        _render_schedule_rows(
            console,
            items,
            title=f"Overdue ({len(items)})",
            overdue=True,
        )

    # --- schedule complete -------------------------------------------
    @schedule_group.command("complete")
    @click.option(
        "--bike", "bike", required=True,
        help="Garage bike slug.",
    )
    @click.option(
        "--item", "item_slug", required=True,
        help="Service item slug (e.g. 'oil-change').",
    )
    @click.option(
        "--at-miles", "at_miles", type=int, default=None,
        help="Mileage at completion. Omit to read from vehicles.mileage (Phase 152).",
    )
    @click.option(
        "--at-date", "at_date", default=None,
        help="ISO-8601 date of completion (default: today UTC).",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of the success panel.",
    )
    def schedule_complete_cmd(
        bike: str,
        item_slug: str,
        at_miles: Optional[int],
        at_date: Optional[str],
        json_output: bool,
    ) -> None:
        """Record a completed service event; re-computes next_due."""
        from motodiag.advanced.schedule_repo import ServiceIntervalError
        from motodiag.advanced.scheduler import record_completion

        console = get_console()
        init_db()

        # Pre-validate the ISO date for a clean CLI error.
        if at_date is not None:
            try:
                from motodiag.advanced.scheduler import _parse_iso_date
                _parse_iso_date(at_date)
            except ValueError as exc:
                raise click.ClickException(str(exc)) from exc

        from motodiag.cli.diagnose import _resolve_bike_slug

        resolved = _resolve_bike_slug(bike)
        if resolved is None:
            _render_bike_not_found(console, bike)
            raise click.exceptions.Exit(1)
        vehicle_id = int(resolved["id"])

        try:
            updated = record_completion(
                vehicle_id, item_slug,
                at_miles=at_miles, at_date=at_date,
            )
        except ServiceIntervalError as exc:
            raise click.ClickException(str(exc)) from exc

        if json_output:
            click.echo(_json.dumps({
                "vehicle_id": vehicle_id,
                "item_slug": item_slug,
                "updated": updated,
            }, indent=2, default=str))
            return

        next_bits: list[str] = []
        if updated.get("next_due_miles") is not None:
            next_bits.append(f"{int(updated['next_due_miles']):,} mi")
        if updated.get("next_due_at"):
            next_bits.append(str(updated["next_due_at"])[:10])
        console.print(
            Panel(
                f"[green]{ICON_OK} Recorded {item_slug!r} for "
                f"bike #{vehicle_id}.[/green]\n"
                f"Last done: {updated.get('last_done_at', '') or '-'} "
                f"@ {updated.get('last_done_miles', '') or '-'} mi\n"
                f"Next due: {' / '.join(next_bits) or '-'}",
                title="Service recorded",
                border_style="green",
            )
        )

    # --- schedule history --------------------------------------------
    @schedule_group.command("history")
    @click.option(
        "--bike", "bike", required=True,
        help="Garage bike slug.",
    )
    @click.option(
        "--item", "item_slug", default=None,
        help="Optional filter: only show this item slug.",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of the Rich table.",
    )
    def schedule_history_cmd(
        bike: str,
        item_slug: Optional[str],
        json_output: bool,
    ) -> None:
        """Show service completion history for a bike.

        Pre-Phase-152 this is a snapshot built from ``last_done_*``
        columns on service_intervals (one row per interval that has
        ever been completed). Phase 152 adds a full service_history
        log and this command automatically starts reading from it.
        """
        from motodiag.advanced.scheduler import history as _history

        console = get_console()
        init_db()
        from motodiag.cli.diagnose import _resolve_bike_slug

        resolved = _resolve_bike_slug(bike)
        if resolved is None:
            _render_bike_not_found(console, bike)
            raise click.exceptions.Exit(1)
        vehicle_id = int(resolved["id"])

        rows = _history(vehicle_id, item_slug=item_slug)

        if json_output:
            click.echo(_json.dumps({
                "vehicle_id": vehicle_id,
                "item_slug": item_slug,
                "rows": rows,
            }, indent=2, default=str))
            return

        snapshot_only = all(r.get("source") == "snapshot" for r in rows) if rows else False

        if not rows:
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} No completion history for "
                    f"bike #{vehicle_id}.[/yellow]\n\n"
                    "[dim]Run [bold]motodiag advanced schedule complete[/bold] "
                    "to record your first service.[/dim]",
                    title="No history",
                    border_style="yellow",
                )
            )
            return

        if snapshot_only:
            console.print(
                Panel(
                    "[dim]Showing snapshot from service_intervals "
                    "(Phase 152's service_history table is not yet "
                    "populated — once Phase 152 lands this will show "
                    "the full event log).[/dim]",
                    title="Snapshot view",
                    border_style="dim",
                )
            )

        table = Table(
            title=f"Service history ({len(rows)})",
            header_style="bold cyan",
        )
        table.add_column("Item", no_wrap=True)
        table.add_column("Date", no_wrap=True)
        table.add_column("Miles", no_wrap=True, justify="right")
        table.add_column("Notes", overflow="fold")
        for row in rows:
            miles_val = row.get("performed_at_miles")
            table.add_row(
                row.get("item_slug", "") or "",
                str(row.get("performed_at_date", "") or "")[:10],
                (
                    f"{int(miles_val):,}"
                    if miles_val is not None
                    else "[dim]-[/dim]"
                ),
                row.get("notes", "") or "[dim]-[/dim]",
            )
        console.print(table)

    # --- baseline subgroup (Phase 157) -------------------------------
    #
    # Performance baselines: aggregated healthy-range bands derived
    # from mechanic-flagged exemplar recordings. Four subcommands
    # cover the mechanic workflow: look up a stored baseline
    # (``show``), mark a recording as healthy + auto-rebuild
    # (``flag-healthy``), broad cross-cutting rebuild for a model
    # family (``rebuild``), and top-level inventory (``list``).

    @advanced_group.group("baseline")
    def baseline_group() -> None:
        """Performance baselines: expected-range bands per PID per state."""

    # --- baseline show -----------------------------------------------
    @baseline_group.command("show")
    @click.option(
        "--make", required=True,
        help="Bike make (any case — matched case-insensitively).",
    )
    @click.option(
        "--model", "model_name", required=True,
        help="Exact model string (matched against stored "
             "model_pattern via SQL LIKE).",
    )
    @click.option(
        "--year", type=int, required=True,
        help="Model year (falls inside stored year_min/year_max band).",
    )
    @click.option(
        "--pid", "pid_hex", default=None,
        help="OBD-II PID hex string (e.g. 0x05 for coolant). When "
             "omitted, all PIDs for the state are shown.",
    )
    @click.option(
        "--state", "operating_state",
        type=click.Choice(["idle", "2500rpm", "redline"], case_sensitive=False),
        default=None,
        help="Operating state filter. When omitted, all three states "
             "are shown.",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of the Rich table.",
    )
    def baseline_show_cmd(
        make: str,
        model_name: str,
        year: int,
        pid_hex: Optional[str],
        operating_state: Optional[str],
        json_output: bool,
    ) -> None:
        """Look up stored performance baselines for a bike."""
        from motodiag.advanced.baseline import get_baseline

        console = get_console()
        init_db()

        states = (
            [operating_state.lower()] if operating_state
            else ["idle", "2500rpm", "redline"]
        )

        # Canonicalize the PID if supplied.
        canonical_pid: Optional[str] = None
        if pid_hex:
            p = pid_hex.strip()
            if p.lower().startswith("0x"):
                canonical_pid = "0x" + p[2:].upper()
            else:
                canonical_pid = "0x" + p.upper()

        results: list[dict] = []
        if canonical_pid:
            for st in states:
                profile = get_baseline(
                    make=make,
                    model=model_name,
                    year=int(year),
                    pid_hex=canonical_pid,
                    operating_state=st,
                )
                if profile is not None:
                    results.append(profile.model_dump(mode="json"))
        else:
            # No PID filter — sweep the DB for any baseline that
            # matches this bike + state.
            with get_connection() as conn:
                for st in states:
                    rows = conn.execute(
                        """
                        SELECT * FROM performance_baselines
                         WHERE LOWER(make) = ?
                           AND ? LIKE model_pattern
                           AND (
                               (year_min IS NULL AND year_max IS NULL)
                               OR (? BETWEEN COALESCE(year_min, -9999)
                                             AND COALESCE(year_max, 9999))
                           )
                           AND operating_state = ?
                         ORDER BY confidence_1to5 DESC,
                                  COALESCE(year_max, 9999)
                                  - COALESCE(year_min, -9999) ASC,
                                  id ASC
                        """,
                        (
                            make.strip().lower(),
                            model_name,
                            int(year),
                            st,
                        ),
                    ).fetchall()
                    for r in rows:
                        results.append(dict(r))

        if json_output:
            click.echo(
                _json.dumps({"baselines": results}, indent=2, default=str),
            )
            return

        if not results:
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} No baseline found for "
                    f"{year} {make} {model_name}"
                    + (f" PID {canonical_pid}" if canonical_pid else "")
                    + (f" state={operating_state}" if operating_state else "")
                    + ".[/yellow]\n\n"
                    "[dim]Flag known-healthy recordings with "
                    "[bold]motodiag advanced baseline flag-healthy "
                    "--recording-id N[/bold] to populate the "
                    "baseline.[/dim]",
                    title="No baseline",
                    border_style="yellow",
                )
            )
            return

        table = Table(
            title=(
                f"Baselines — {year} {make} {model_name}"
                f"  ({len(results)} rows)"
            ),
            header_style="bold cyan",
        )
        table.add_column("PID", no_wrap=True)
        table.add_column("State", no_wrap=True)
        table.add_column("Min", justify="right")
        table.add_column("Median", justify="right")
        table.add_column("Max", justify="right")
        table.add_column("Samples", justify="right")
        table.add_column("Conf.", justify="right")

        for r in results:
            conf = int(r.get("confidence_1to5") or 1)
            conf_cell = _format_baseline_confidence(conf)
            table.add_row(
                str(r.get("pid_hex") or ""),
                str(r.get("operating_state") or ""),
                _fmt_num(r.get("expected_min")),
                _fmt_num(r.get("expected_median")),
                _fmt_num(r.get("expected_max")),
                str(int(r.get("sample_count") or 0)),
                conf_cell,
            )
        console.print(table)

        # Footer — model_pattern + year band + last_rebuilt_at from the
        # first row (all rows share the same scope for a given bike
        # lookup, barring overlapping patterns).
        first = results[0]
        footer = (
            f"[dim]model_pattern={first.get('model_pattern') or '-'}  "
            f"year_band="
            f"{first.get('year_min') or '-'}–"
            f"{first.get('year_max') or '-'}  "
            f"last_rebuilt_at={first.get('last_rebuilt_at') or '-'}[/dim]"
        )
        console.print(footer)

    # --- baseline flag-healthy ---------------------------------------
    @baseline_group.command("flag-healthy")
    @click.option(
        "--recording-id", "recording_id", type=int, required=True,
        help="ID of the sensor recording to flag as known-healthy.",
    )
    @click.option(
        "--yes", "skip_confirm", is_flag=True, default=False,
        help="Skip the confirmation prompt.",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of the Rich panel.",
    )
    def baseline_flag_healthy_cmd(
        recording_id: int,
        skip_confirm: bool,
        json_output: bool,
    ) -> None:
        """Flag a recording as healthy and auto-rebuild baselines."""
        from motodiag.advanced.baseline import flag_recording_as_healthy

        console = get_console()
        init_db()

        # Sanity-check the recording exists before prompting — gives a
        # cleaner error than ValueError from the repo layer.
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT r.id, r.vehicle_id, r.stopped_at,
                       v.make, v.model, v.year
                  FROM sensor_recordings r
                  LEFT JOIN vehicles v ON v.id = r.vehicle_id
                 WHERE r.id = ?
                """,
                (int(recording_id),),
            ).fetchone()

        if row is None:
            console.print(
                Panel(
                    f"[red]Recording #{recording_id} not found.[/red]",
                    title="Unknown recording",
                    border_style="red",
                )
            )
            raise click.exceptions.Exit(1)

        if not skip_confirm:
            summary = (
                f"Flag recording #{recording_id} "
                f"({row['year']} {row['make']} {row['model']}) "
                "as known-healthy? This auto-rebuilds baselines "
                "for that bike."
            )
            confirm = click.confirm(summary, default=False)
            if not confirm:
                console.print("[yellow]Aborted.[/yellow]")
                return

        try:
            result = flag_recording_as_healthy(int(recording_id))
        except ValueError as exc:
            console.print(
                Panel(
                    f"[red]{str(exc)}[/red]",
                    title="Cannot flag recording",
                    border_style="red",
                )
            )
            raise click.exceptions.Exit(1) from exc

        if json_output:
            click.echo(_json.dumps(result, indent=2, default=str))
            return

        console.print(
            Panel(
                f"[green]{ICON_OK} Flagged recording "
                f"#{recording_id} — rebuilt "
                f"{result['baselines_created']} baseline"
                f"{'s' if result['baselines_created'] != 1 else ''}.[/green]\n\n"
                f"[dim]exemplar_id={result['exemplar_id']}  "
                f"baselines_updated={result['baselines_updated']}  "
                f"baselines_created={result['baselines_created']}[/dim]",
                title="Recording flagged",
                border_style="green",
            )
        )

    # --- baseline rebuild --------------------------------------------
    @baseline_group.command("rebuild")
    @click.option(
        "--make", required=True,
        help="Bike make (case-insensitive).",
    )
    @click.option(
        "--model", "model_name", required=True,
        help="Model string or SQL LIKE pattern.",
    )
    @click.option(
        "--year-min", type=int, default=None,
        help="Optional lower bound on year.",
    )
    @click.option(
        "--year-max", type=int, default=None,
        help="Optional upper bound on year.",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of a summary + Rich table.",
    )
    def baseline_rebuild_cmd(
        make: str,
        model_name: str,
        year_min: Optional[int],
        year_max: Optional[int],
        json_output: bool,
    ) -> None:
        """Rebuild baselines for a broader (make, model, year) scope."""
        from motodiag.advanced.baseline import rebuild_baseline

        console = get_console()
        init_db()

        result = rebuild_baseline(
            make=make,
            model_pattern=model_name,
            year_min=year_min,
            year_max=year_max,
        )

        if json_output:
            click.echo(_json.dumps(result, indent=2, default=str))
            return

        console.print(
            Panel(
                f"[bold]{make}  {model_name}[/bold]   "
                f"year_band={year_min or '-'}–{year_max or '-'}\n\n"
                f"Exemplars processed: "
                f"{result['exemplar_count']}\n"
                f"Baselines deleted (stale): "
                f"{result['baselines_updated']}\n"
                f"Baselines created: "
                f"[green]{result['baselines_created']}[/green]",
                title="Baseline rebuild",
                border_style="cyan",
            )
        )

        # Show the freshly-inserted rows so the mechanic sees the new
        # state in one shot.
        if result["baselines_created"]:
            with get_connection() as conn:
                clauses = ["LOWER(make) = ?", "model_pattern = ?"]
                params: list = [make.strip().lower(), model_name]
                if year_min is not None:
                    clauses.append("year_min = ?")
                    params.append(int(year_min))
                else:
                    clauses.append("year_min IS NULL")
                if year_max is not None:
                    clauses.append("year_max = ?")
                    params.append(int(year_max))
                else:
                    clauses.append("year_max IS NULL")
                rows = conn.execute(
                    f"""
                    SELECT * FROM performance_baselines
                     WHERE {' AND '.join(clauses)}
                     ORDER BY pid_hex ASC, operating_state ASC
                    """,
                    tuple(params),
                ).fetchall()
            table = Table(header_style="bold cyan")
            table.add_column("PID", no_wrap=True)
            table.add_column("State", no_wrap=True)
            table.add_column("Min", justify="right")
            table.add_column("Median", justify="right")
            table.add_column("Max", justify="right")
            table.add_column("Samples", justify="right")
            table.add_column("Conf.", justify="right")
            for r in rows:
                conf = int(r["confidence_1to5"] or 1)
                table.add_row(
                    r["pid_hex"],
                    r["operating_state"],
                    _fmt_num(r["expected_min"]),
                    _fmt_num(r["expected_median"]),
                    _fmt_num(r["expected_max"]),
                    str(int(r["sample_count"] or 0)),
                    _format_baseline_confidence(conf),
                )
            console.print(table)

    # --- baseline list -----------------------------------------------
    @baseline_group.command("list")
    @click.option(
        "--make", default=None,
        help="Filter to a single make (case-insensitive).",
    )
    @click.option(
        "--min-confidence", type=click.IntRange(1, 5), default=None,
        help="Drop rows whose MAX confidence across PIDs falls "
             "below this floor (1-5).",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of the Rich table.",
    )
    def baseline_list_cmd(
        make: Optional[str],
        min_confidence: Optional[int],
        json_output: bool,
    ) -> None:
        """List every (make, model_pattern, year band) baseline scope."""
        from motodiag.advanced.baseline import list_baselines

        console = get_console()
        init_db()

        rows = list_baselines(
            make=make,
            min_confidence=min_confidence,
        )

        if json_output:
            click.echo(_json.dumps({"scopes": rows}, indent=2, default=str))
            return

        if not rows:
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} No baselines match the "
                    "supplied filter.[/yellow]\n\n"
                    "[dim]Flag at least one recording via "
                    "[bold]motodiag advanced baseline flag-healthy "
                    "--recording-id N[/bold] to populate "
                    "baselines.[/dim]",
                    title="No baselines",
                    border_style="yellow",
                )
            )
            return

        table = Table(
            title=f"Baseline scopes ({len(rows)})",
            header_style="bold cyan",
        )
        table.add_column("Make", no_wrap=True)
        table.add_column("ModelPattern", overflow="fold", max_width=30)
        table.add_column("YearBand", no_wrap=True)
        table.add_column("#PIDs", justify="right")
        table.add_column("Exemplars", justify="right")
        table.add_column("Confidence", justify="right")
        table.add_column("LastRebuilt", no_wrap=True)

        for row in rows:
            y_min = row.get("year_min")
            y_max = row.get("year_max")
            if y_min is None and y_max is None:
                band = "any"
            else:
                band = f"{y_min or '-'}–{y_max or '-'}"
            conf = int(row.get("confidence_1to5") or 1)
            table.add_row(
                row.get("make", "") or "",
                row.get("model_pattern", "") or "",
                band,
                str(int(row.get("pid_count") or 0)),
                str(int(row.get("exemplar_count") or 0)),
                _format_baseline_confidence(conf),
                str(row.get("last_rebuilt_at", "") or "")[:19],
            )
        console.print(table)

    # --- recall subgroup (Phase 155) ---------------------------------
    #
    # NHTSA safety recall lookup. Four subcommands: `list` (browse
    # recalls, optional filters), `check-vin` (decode a VIN + return
    # applicable open recalls), `lookup` (direct make+model+year
    # filter), `mark-resolved` (record per-bike closure). Unlike
    # Phase 154 TSBs, these are federal-mandate-to-fix campaigns —
    # free to the owner, higher trust signal.

    @advanced_group.group("recall")
    def recall_group() -> None:
        """NHTSA safety recall lookup, VIN decoding, and per-bike resolution."""

    # --- recall list --------------------------------------------------
    @recall_group.command("list")
    @click.option(
        "--make", default=None,
        help="Filter by manufacturer (case-insensitive).",
    )
    @click.option(
        "--model", "model_name", default=None,
        help="Filter by model. Requires --make. Exact match.",
    )
    @click.option(
        "--year", type=int, default=None,
        help="Filter by year — only recalls whose year envelope "
             "covers this year are returned.",
    )
    @click.option(
        "--open-only/--all",
        default=True, show_default=True,
        help="Show only open recalls (default), or all including "
             "closed.",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of the Rich table.",
    )
    def recall_list_cmd(
        make: Optional[str],
        model_name: Optional[str],
        year: Optional[int],
        open_only: bool,
        json_output: bool,
    ) -> None:
        """List NHTSA recalls matching the given filters."""
        from motodiag.advanced.recall_repo import lookup as _lookup

        console = get_console()
        init_db()

        if make is None:
            # Broad listing — fall back to direct SQL so we can scope
            # by open flag without requiring a make.
            from motodiag.core.database import get_connection as _gc
            with _gc() as conn:
                base_q = "SELECT * FROM recalls"
                params: list = []
                if open_only:
                    base_q += " WHERE open = 1"
                base_q += " ORDER BY severity DESC, nhtsa_id"
                rows = [dict(r) for r in conn.execute(base_q, params).fetchall()]
        else:
            rows = _lookup(
                make=make, model=model_name, year=year,
                open_only=open_only,
            )

        if json_output:
            click.echo(_json.dumps({"recalls": rows}, indent=2, default=str))
            return

        if not rows:
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} No recalls found matching "
                    f"your filters.[/yellow]\n\n"
                    "[dim]Try widening filters, or run "
                    "[bold]motodiag advanced recall check-vin VIN[/bold] "
                    "for a VIN-specific lookup.[/dim]",
                    title="No recalls",
                    border_style="yellow",
                )
            )
            return

        _render_recall_table(console, rows, title="NHTSA recalls")

    # --- recall check-vin ---------------------------------------------
    @recall_group.command("check-vin")
    @click.argument("vin")
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of the Rich table.",
    )
    def recall_check_vin_cmd(vin: str, json_output: bool) -> None:
        """Decode a VIN and list applicable open NHTSA recalls."""
        from motodiag.advanced.recall_repo import check_vin, decode_vin

        console = get_console()
        init_db()

        # Validate + decode. Let ValueError escalate to a clean
        # click.ClickException so the mechanic sees a readable error.
        try:
            decoded = decode_vin(vin)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc

        rows = check_vin(vin)

        if json_output:
            click.echo(_json.dumps({
                "vin": vin.upper().strip(),
                "decoded": decoded,
                "recalls": rows,
            }, indent=2, default=str))
            return

        console.print(
            Panel(
                f"[bold]{vin.upper().strip()}[/bold]\n"
                f"Make: {decoded.get('make') or '[dim]unknown[/dim]'}\n"
                f"Year: {decoded.get('year') or '[dim]unknown[/dim]'}\n"
                f"WMI: {decoded.get('wmi')}  •  "
                f"Year code: {decoded.get('year_code')}",
                title="VIN decoded",
                border_style="cyan",
            )
        )

        if not rows:
            console.print(
                Panel(
                    f"[green]{ICON_OK} No open recalls for this VIN.[/green]",
                    title="Clear",
                    border_style="green",
                )
            )
            return

        _render_recall_table(console, rows, title="Applicable open recalls")

    # --- recall lookup ------------------------------------------------
    @recall_group.command("lookup")
    @click.option("--make", required=True, help="Manufacturer.")
    @click.option("--model", "model_name", required=True, help="Model.")
    @click.option("--year", type=int, required=True, help="Year.")
    @click.option(
        "--open-only/--all", default=True, show_default=True,
        help="Include closed recalls when --all.",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of the Rich table.",
    )
    def recall_lookup_cmd(
        make: str,
        model_name: str,
        year: int,
        open_only: bool,
        json_output: bool,
    ) -> None:
        """Look up recalls for a specific make / model / year."""
        from motodiag.advanced.recall_repo import lookup as _lookup

        console = get_console()
        init_db()

        rows = _lookup(
            make=make, model=model_name, year=year, open_only=open_only,
        )

        if json_output:
            click.echo(_json.dumps({
                "make": make,
                "model": model_name,
                "year": year,
                "open_only": open_only,
                "recalls": rows,
            }, indent=2, default=str))
            return

        if not rows:
            console.print(
                Panel(
                    f"[green]{ICON_OK} No recalls for "
                    f"{year} {make} {model_name}.[/green]",
                    title="Clear",
                    border_style="green",
                )
            )
            return

        _render_recall_table(
            console, rows,
            title=f"Recalls for {year} {make} {model_name}",
        )

    # --- recall mark-resolved -----------------------------------------
    @recall_group.command("mark-resolved")
    @click.option("--bike", required=True, help="Garage bike slug.")
    @click.option(
        "--recall-id", type=int, required=True,
        help="Recall row ID (from `motodiag advanced recall list`).",
    )
    @click.option(
        "--resolved-at", default=None,
        help="ISO 8601 timestamp. Defaults to now.",
    )
    @click.option("--notes", default=None, help="Free-text notes.")
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of a Rich panel.",
    )
    def recall_mark_resolved_cmd(
        bike: str,
        recall_id: int,
        resolved_at: Optional[str],
        notes: Optional[str],
        json_output: bool,
    ) -> None:
        """Record that a recall has been resolved on a garage bike."""
        from motodiag.advanced.recall_repo import mark_resolved
        from motodiag.cli.diagnose import _resolve_bike_slug

        console = get_console()
        init_db()

        resolved = _resolve_bike_slug(bike)
        if resolved is None:
            _render_bike_not_found(console, bike)
            raise click.exceptions.Exit(1)

        vehicle_id = int(resolved["id"])
        inserted = mark_resolved(
            vehicle_id=vehicle_id,
            recall_id=recall_id,
            resolved_at=resolved_at,
            notes=notes,
        )

        if json_output:
            click.echo(_json.dumps({
                "vehicle_id": vehicle_id,
                "recall_id": recall_id,
                "inserted": inserted,
                "already_resolved": inserted == 0,
            }, indent=2))
            return

        if inserted:
            console.print(
                Panel(
                    f"[green]{ICON_OK} Recall #{recall_id} marked "
                    f"resolved for bike #{vehicle_id}.[/green]"
                    + (f"\n\n[dim]Notes:[/dim] {notes}" if notes else ""),
                    title="Recall resolved",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} Recall #{recall_id} was "
                    f"already marked resolved for bike #{vehicle_id}.[/yellow]\n\n"
                    "[dim]No new row inserted. Re-running "
                    "mark-resolved is idempotent.[/dim]",
                    title="Already resolved",
                    border_style="yellow",
                )
            )

    # === Phase 153: parts cross-reference =============================

    @advanced_group.group("parts")
    def parts_group() -> None:
        """OEM ↔ aftermarket parts cross-reference lookup + seed."""

    # --- parts search -------------------------------------------------
    @parts_group.command("search")
    @click.argument("query")
    @click.option(
        "--make", default=None,
        help="Narrow search to a single make (case-insensitive).",
    )
    @click.option(
        "--category", default=None,
        help="Narrow search to a category slug (e.g. cam-tensioner).",
    )
    @click.option(
        "--limit", type=int, default=20, show_default=True,
        help="Maximum number of rows to return.",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of the Rich table.",
    )
    def parts_search_cmd(
        query: str,
        make: Optional[str],
        category: Optional[str],
        limit: int,
        json_output: bool,
    ) -> None:
        """Fuzzy-search parts by OEM#, description, brand, or make."""
        from motodiag.advanced.parts_repo import search_parts

        console = get_console()
        init_db()
        rows = search_parts(
            query=query, make=make, category=category, limit=limit,
        )
        if json_output:
            click.echo(_json.dumps({"parts": rows}, indent=2, default=str))
            return
        if not rows:
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} No parts match {query!r}.[/yellow]\n\n"
                    "[dim]Run [bold]motodiag advanced parts seed --yes[/bold] "
                    "to populate the parts database, or broaden your query.[/dim]",
                    title="No parts found",
                    border_style="yellow",
                )
            )
            return
        table = Table(
            title=f"Parts matching {query!r} ({len(rows)})",
            header_style="bold cyan",
        )
        table.add_column("OEM#", no_wrap=True)
        table.add_column("Brand", no_wrap=True)
        table.add_column("Description", overflow="fold", max_width=40)
        table.add_column("Category", no_wrap=True)
        table.add_column("Make/Model", no_wrap=True)
        table.add_column("Cost", no_wrap=True, justify="right")
        table.add_column("Verified", no_wrap=True)
        for r in rows:
            cost_cents = r.get("typical_cost_cents") or 0
            cost_str = (
                f"${int(cost_cents)/100:,.2f}" if cost_cents > 0 else "[dim]-[/dim]"
            )
            verified = r.get("verified_by") or ""
            if verified == "forum":
                verified_cell = "[cyan]forum[/cyan]"
            elif verified == "service-manual":
                verified_cell = "[green]manual[/green]"
            else:
                verified_cell = "[dim]-[/dim]"
            table.add_row(
                r.get("oem_part_number") or "[dim]-[/dim]",
                r.get("brand") or "",
                r.get("description") or "",
                r.get("category") or "",
                f"{r.get('make', '')} / {r.get('model_pattern', '')}",
                cost_str,
                verified_cell,
            )
        console.print(table)

    # --- parts xref ---------------------------------------------------
    @parts_group.command("xref")
    @click.argument("oem_part_number")
    @click.option(
        "--min-rating", type=click.IntRange(min=1, max=5),
        default=1, show_default=True,
        help="Filter out cross-references below this equivalence rating.",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of the Rich table.",
    )
    def parts_xref_cmd(
        oem_part_number: str,
        min_rating: int,
        json_output: bool,
    ) -> None:
        """Show ranked aftermarket alternatives for an OEM part number."""
        from motodiag.advanced.parts_repo import get_xrefs

        console = get_console()
        init_db()
        rows = get_xrefs(oem_part_number, min_rating=min_rating)
        if json_output:
            click.echo(
                _json.dumps(
                    {
                        "oem_part_number": oem_part_number,
                        "min_rating": min_rating,
                        "xrefs": rows,
                    },
                    indent=2, default=str,
                )
            )
            return
        if not rows:
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} No cross-references for "
                    f"{oem_part_number!r}"
                    + (
                        f" with rating >= {min_rating}" if min_rating > 1 else ""
                    )
                    + ".[/yellow]\n\n"
                    "[dim]Run [bold]motodiag advanced parts seed --yes[/bold] "
                    "to populate the parts database, or verify the OEM number.[/dim]",
                    title="No cross-references",
                    border_style="yellow",
                )
            )
            return
        table = Table(
            title=f"Aftermarket alternatives for {oem_part_number} ({len(rows)})",
            header_style="bold cyan",
        )
        table.add_column("Rating", no_wrap=True, justify="right")
        table.add_column("Brand", no_wrap=True)
        table.add_column("P/N", no_wrap=True)
        table.add_column("Description", overflow="fold", max_width=36)
        table.add_column("Cost", no_wrap=True, justify="right")
        table.add_column("Notes", overflow="fold", max_width=30)
        table.add_column("Source", overflow="fold", max_width=24)
        for r in rows:
            rating = int(r.get("equivalence_rating") or 0)
            rating_cell = "*" * rating + "." * (5 - rating)
            if rating >= 4:
                rating_cell = f"[cyan]{rating_cell}[/cyan]"
            elif rating >= 3:
                rating_cell = f"[yellow]{rating_cell}[/yellow]"
            else:
                rating_cell = f"[dim]{rating_cell}[/dim]"
            cost_cents = r.get("aftermarket_cost_cents") or 0
            cost_str = (
                f"${int(cost_cents)/100:,.2f}" if cost_cents > 0 else "[dim]-[/dim]"
            )
            table.add_row(
                rating_cell,
                r.get("aftermarket_brand") or "",
                r.get("aftermarket_part_number") or "[dim]-[/dim]",
                r.get("aftermarket_description") or "",
                cost_str,
                r.get("xref_notes") or "[dim]-[/dim]",
                r.get("source_url") or "[dim]-[/dim]",
            )
        console.print(table)

    # --- parts show ---------------------------------------------------
    @parts_group.command("show")
    @click.argument("slug")
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of the Rich panel + table.",
    )
    def parts_show_cmd(slug: str, json_output: bool) -> None:
        """Show a part's details + nested cross-references."""
        from motodiag.advanced.parts_repo import get_part, get_xrefs

        console = get_console()
        init_db()
        part = get_part(slug)
        if part is None:
            console.print(
                Panel(
                    f"[red]No part with slug {slug!r}.[/red]\n\n"
                    "[dim]Run [bold]motodiag advanced parts search <query>[/bold] "
                    "to find slugs.[/dim]",
                    title="Unknown part",
                    border_style="red",
                )
            )
            raise click.exceptions.Exit(1)

        xrefs: list[dict] = []
        oem_pn = part.get("oem_part_number")
        if oem_pn:
            xrefs = get_xrefs(oem_pn)

        if json_output:
            click.echo(
                _json.dumps(
                    {"part": part, "xrefs": xrefs},
                    indent=2, default=str,
                )
            )
            return

        cost_cents = part.get("typical_cost_cents") or 0
        cost_str = (
            f"${int(cost_cents)/100:,.2f}" if cost_cents > 0 else "[dim]-[/dim]"
        )
        years = ""
        y_min = part.get("year_min")
        y_max = part.get("year_max")
        if y_min is not None or y_max is not None:
            years = f" ({y_min or '-'}-{y_max or '-'})"
        body = (
            f"[bold]{part.get('brand', '')}[/bold] "
            f"{part.get('oem_part_number') or '[no OEM#]'}\n"
            f"[dim]{part.get('description', '')}[/dim]\n\n"
            f"Category: {part.get('category', '')}\n"
            f"Make/Model: {part.get('make', '')} / "
            f"{part.get('model_pattern', '')}{years}\n"
            f"Typical cost: {cost_str}\n"
            f"Verified by: {part.get('verified_by') or '[dim]-[/dim]'}"
        )
        if part.get("purchase_url"):
            body += f"\nPurchase: [link]{part.get('purchase_url')}[/link]"
        if part.get("notes"):
            body += f"\n\n[dim]{part.get('notes')}[/dim]"

        console.print(
            Panel(
                body,
                title=f"Part #{part.get('id')} - {slug}",
                border_style="cyan",
            )
        )

        if not xrefs:
            console.print(
                "[dim]No cross-references recorded for this part.[/dim]"
            )
            return

        table = Table(
            title=f"Aftermarket alternatives ({len(xrefs)})",
            header_style="bold cyan",
        )
        table.add_column("Rating", no_wrap=True, justify="right")
        table.add_column("Brand", no_wrap=True)
        table.add_column("P/N", no_wrap=True)
        table.add_column("Description", overflow="fold", max_width=36)
        table.add_column("Cost", no_wrap=True, justify="right")
        table.add_column("Notes", overflow="fold", max_width=30)
        for r in xrefs:
            rating = int(r.get("equivalence_rating") or 0)
            rating_cell = "*" * rating + "." * (5 - rating)
            if rating >= 4:
                rating_cell = f"[cyan]{rating_cell}[/cyan]"
            elif rating >= 3:
                rating_cell = f"[yellow]{rating_cell}[/yellow]"
            else:
                rating_cell = f"[dim]{rating_cell}[/dim]"
            rc = r.get("aftermarket_cost_cents") or 0
            cs = f"${int(rc)/100:,.2f}" if rc > 0 else "[dim]-[/dim]"
            table.add_row(
                rating_cell,
                r.get("aftermarket_brand") or "",
                r.get("aftermarket_part_number") or "[dim]-[/dim]",
                r.get("aftermarket_description") or "",
                cs,
                r.get("xref_notes") or "[dim]-[/dim]",
            )
        console.print(table)

    # --- parts seed ---------------------------------------------------
    @parts_group.command("seed")
    @click.option(
        "--yes", "confirm", is_flag=True, default=False,
        help="Required: confirm you intend to run the seeder.",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON summary instead of the Rich panel.",
    )
    def parts_seed_cmd(confirm: bool, json_output: bool) -> None:
        """Seed parts + parts_xref from bundled JSON (idempotent)."""
        console = get_console()
        if not confirm:
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} Re-run with --yes to confirm.[/yellow]\n\n"
                    "[dim]The seeder loads "
                    "[bold]advanced/data/parts.json[/bold] and "
                    "[bold]parts_xref.json[/bold] into the parts + "
                    "parts_xref tables. Idempotent - duplicate slugs "
                    "and duplicate (OEM,aftermarket) pairs are "
                    "skipped via INSERT OR IGNORE.[/dim]",
                    title="Parts seed - confirmation required",
                    border_style="yellow",
                )
            )
            return

        from motodiag.advanced.parts_loader import seed_all

        init_db()
        summary = seed_all()
        if json_output:
            click.echo(_json.dumps({"summary": summary}, indent=2))
            return
        console.print(
            Panel(
                f"[green]{ICON_OK} Seed complete.[/green]\n\n"
                f"Parts rows processed:   [bold]{summary.get('parts', 0)}[/bold]\n"
                f"Xref rows processed:    [bold]{summary.get('xref', 0)}[/bold]\n\n"
                "[dim]Re-running this command produces the same counts "
                "but inserts zero new rows (INSERT OR IGNORE).[/dim]",
                title="Parts database seeded",
                border_style="green",
            )
        )

    # === Phase 154: Technical Service Bulletins =======================
    #
    # Browse + search OEM-issued TSBs (distinct from NHTSA recalls /
    # forum-consensus known_issues). Nested under the shared
    # ``advanced`` group so ``motodiag advanced tsb {list,search,show,
    # by-make}`` groups with the other Track F subcommands.

    @advanced_group.group("tsb")
    def tsb_group() -> None:
        """Browse OEM Technical Service Bulletins (TSBs)."""

    # --- tsb list -----------------------------------------------------
    @tsb_group.command("list")
    @click.option(
        "--bike", "bike", default=None,
        help="Garage bike slug — list TSBs applicable to this bike only.",
    )
    @click.option(
        "--make", "make", default=None,
        help="Filter by make (case-insensitive). Ignored when --bike used.",
    )
    @click.option(
        "--limit", type=int, default=50, show_default=True,
        help="Maximum number of TSBs to list.",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of the Rich table.",
    )
    def tsb_list_cmd(
        bike: Optional[str],
        make: Optional[str],
        limit: int,
        json_output: bool,
    ) -> None:
        """List TSBs, optionally scoped by bike or make."""
        from motodiag.advanced.tsb_repo import (
            list_tsbs,
            list_tsbs_for_bike,
        )

        console = get_console()
        init_db()

        rows: list[dict]
        scope_label: str
        if bike:
            from motodiag.cli.diagnose import _resolve_bike_slug
            resolved = _resolve_bike_slug(bike)
            if resolved is None:
                _render_bike_not_found(console, bike)
                raise click.exceptions.Exit(1)
            rows = list_tsbs_for_bike(
                make=resolved.get("make") or "",
                model=resolved.get("model") or "",
                year=resolved.get("year"),
            )
            scope_label = (
                f"{resolved.get('year')} {resolved.get('make')} "
                f"{resolved.get('model')}"
            )
        else:
            rows = list_tsbs(limit=max(1, int(limit)))
            if make:
                normalized = str(make).strip().lower()
                rows = [
                    r for r in rows
                    if (r.get("make") or "").lower() == normalized
                ]
            scope_label = f"make={make}" if make else "all makes"

        rows = rows[: max(1, int(limit))]

        if json_output:
            click.echo(_json.dumps(
                {"scope": scope_label, "tsbs": rows},
                indent=2, default=str,
            ))
            return

        if not rows:
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} No TSBs found for "
                    f"{scope_label}.[/yellow]\n\n"
                    "[dim]Try dropping --make, widening --limit, or run "
                    "`motodiag advanced tsb list` with no filters.[/dim]",
                    title="No TSBs",
                    border_style="yellow",
                )
            )
            return

        _render_tsb_table(
            console, rows, title=f"TSBs — {scope_label}",
        )

    # --- tsb search ---------------------------------------------------
    @tsb_group.command("search")
    @click.argument("query")
    @click.option(
        "--make", "make", default=None,
        help="Scope the search to a specific make (case-insensitive).",
    )
    @click.option(
        "--limit", type=int, default=25, show_default=True,
        help="Maximum number of matches to return.",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of the Rich table.",
    )
    def tsb_search_cmd(
        query: str,
        make: Optional[str],
        limit: int,
        json_output: bool,
    ) -> None:
        """Full-text search across TSB title + description + fix."""
        from motodiag.advanced.tsb_repo import search_tsbs

        console = get_console()
        init_db()

        rows = search_tsbs(
            query=query, make=make, limit=max(1, int(limit)),
        )

        if json_output:
            click.echo(_json.dumps(
                {"query": query, "tsbs": rows},
                indent=2, default=str,
            ))
            return

        if not rows:
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} No TSBs matched "
                    f"{query!r}.[/yellow]\n\n"
                    "[dim]Try a shorter term — matches run across title, "
                    "description, and fix procedure.[/dim]",
                    title="No matches",
                    border_style="yellow",
                )
            )
            return

        _render_tsb_table(
            console, rows, title=f"Search — {query!r}",
        )

    # --- tsb show -----------------------------------------------------
    @tsb_group.command("show")
    @click.argument("tsb_number")
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of a Rich panel.",
    )
    def tsb_show_cmd(tsb_number: str, json_output: bool) -> None:
        """Show the full detail panel for one TSB."""
        from motodiag.advanced.tsb_repo import get_tsb

        console = get_console()
        init_db()

        # Normalize whitespace in TSB number lookup — mechanics often
        # paste with trailing space from PDFs.
        normalized = (tsb_number or "").strip()
        row = get_tsb(normalized)

        if row is None:
            if json_output:
                click.echo(_json.dumps(
                    {"tsb_number": normalized, "tsb": None},
                    indent=2,
                ))
                return
            console.print(
                Panel(
                    f"[red]No TSB matches {normalized!r}.[/red]\n\n"
                    "[dim]Run `motodiag advanced tsb list` to see "
                    "known TSB numbers.[/dim]",
                    title="TSB not found",
                    border_style="red",
                )
            )
            raise click.exceptions.Exit(1)

        if json_output:
            click.echo(_json.dumps({"tsb": row}, indent=2, default=str))
            return

        _render_tsb_panel(console, row)

    # --- tsb by-make --------------------------------------------------
    @tsb_group.command("by-make")
    @click.argument("make")
    @click.option(
        "--limit", type=int, default=50, show_default=True,
        help="Maximum number of TSBs to list.",
    )
    @click.option(
        "--json", "json_output", is_flag=True, default=False,
        help="Emit JSON instead of the Rich table.",
    )
    def tsb_by_make_cmd(make: str, limit: int, json_output: bool) -> None:
        """List all TSBs for a given make, newest first."""
        from motodiag.advanced.tsb_repo import list_tsbs

        console = get_console()
        init_db()

        normalized = (make or "").strip().lower()
        rows = [
            r for r in list_tsbs(limit=1000)
            if (r.get("make") or "").lower() == normalized
        ][: max(1, int(limit))]

        if json_output:
            click.echo(_json.dumps(
                {"make": normalized, "tsbs": rows},
                indent=2, default=str,
            ))
            return

        if not rows:
            console.print(
                Panel(
                    f"[yellow]{ICON_WARN} No TSBs found for "
                    f"make {make!r}.[/yellow]\n\n"
                    "[dim]Known makes: harley-davidson, honda, yamaha, "
                    "kawasaki, suzuki, ktm.[/dim]",
                    title="No TSBs",
                    border_style="yellow",
                )
            )
            return

        _render_tsb_table(
            console, rows, title=f"TSBs — {make}",
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


def _render_tsb_table(console, rows: list[dict], title: str) -> None:
    """Render a Rich table of TSB rows. Shared by Phase 154 list/search/by-make."""
    table = Table(
        title=f"{title} ({len(rows)})",
        header_style="bold cyan",
    )
    table.add_column("TSB #", no_wrap=True)
    table.add_column("Make / Pattern", overflow="fold", max_width=28)
    table.add_column("Years", no_wrap=True)
    table.add_column("Title", overflow="fold", max_width=45)
    table.add_column("Severity")
    table.add_column("Issued", no_wrap=True)

    for row in rows:
        ys = row.get("year_min")
        ye = row.get("year_max")
        if ys is not None and ye is not None:
            years_cell = f"{ys}-{ye}" if ys != ye else str(ys)
        elif ys is not None:
            years_cell = f">={ys}"
        elif ye is not None:
            years_cell = f"<={ye}"
        else:
            years_cell = "[dim]-[/dim]"
        make_pattern = row.get("make") or ""
        if row.get("model_pattern"):
            make_pattern += f" / {row.get('model_pattern')}"
        table.add_row(
            row.get("tsb_number") or "",
            make_pattern or "[dim]-[/dim]",
            years_cell,
            row.get("title") or "",
            format_severity(row.get("severity")),
            row.get("issued_date") or "[dim]-[/dim]",
        )
    console.print(table)


def _render_tsb_panel(console, row: dict) -> None:
    """Render a single TSB as a detail Panel."""
    ys = row.get("year_min")
    ye = row.get("year_max")
    if ys is not None and ye is not None:
        years = f"{ys}-{ye}" if ys != ye else str(ys)
    elif ys is not None:
        years = f">={ys}"
    elif ye is not None:
        years = f"<={ye}"
    else:
        years = "-"
    body_lines = [
        f"[bold]TSB #[/bold] {row.get('tsb_number')}",
        f"[bold]Make:[/bold] {row.get('make')}",
        f"[bold]Model pattern:[/bold] {row.get('model_pattern')}",
        f"[bold]Years:[/bold] {years}",
        f"[bold]Severity:[/bold] {format_severity(row.get('severity'))}",
        f"[bold]Issued:[/bold] {row.get('issued_date') or '-'}",
        "",
        f"[bold]Description[/bold]\n{row.get('description') or '-'}",
        "",
        f"[bold]Fix procedure[/bold]\n{row.get('fix_procedure') or '-'}",
    ]
    verified = row.get("verified_by")
    source = row.get("source_url")
    if verified:
        body_lines.append("")
        body_lines.append(f"[dim]Verified by: {verified}[/dim]")
    if source:
        body_lines.append(f"[dim]Source: {source}[/dim]")
    console.print(
        Panel(
            "\n".join(body_lines),
            title=row.get("title") or "TSB",
            border_style="cyan",
        )
    )


def _render_recall_table(console, rows: list[dict], title: str) -> None:
    """Render a Rich table of recall rows. Shared by `list`, `lookup`,
    `check-vin`.
    """
    table = Table(
        title=f"{title} ({len(rows)})",
        header_style="bold cyan",
    )
    table.add_column("ID", no_wrap=True, justify="right")
    table.add_column("NHTSA", no_wrap=True)
    table.add_column("Campaign", no_wrap=True)
    table.add_column("Make / Model", overflow="fold", max_width=28)
    table.add_column("Years", no_wrap=True)
    table.add_column("Severity")
    table.add_column("Description", overflow="fold", max_width=55)
    table.add_column("Open", no_wrap=True, justify="right")

    for row in rows:
        ys = row.get("year_start")
        ye = row.get("year_end")
        if ys is not None and ye is not None:
            years_cell = f"{ys}-{ye}" if ys != ye else str(ys)
        elif ys is not None:
            years_cell = f">={ys}"
        elif ye is not None:
            years_cell = f"<={ye}"
        else:
            years_cell = "[dim]-[/dim]"
        open_flag = row.get("open")
        open_cell = (
            "[green]yes[/green]" if open_flag == 1
            else "[dim]no[/dim]" if open_flag == 0
            else "[dim]-[/dim]"
        )
        make_model = row.get("make") or ""
        if row.get("model"):
            make_model += f" / {row.get('model')}"
        table.add_row(
            str(row.get("id", "")),
            row.get("nhtsa_id") or "[dim]-[/dim]",
            row.get("campaign_number") or "",
            make_model or "[dim]-[/dim]",
            years_cell,
            format_severity(row.get("severity")),
            row.get("description", "") or "",
            open_cell,
        )
    console.print(table)


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

    If the input looks like an integer we try id-lookup first; on miss
    we fall back to name-lookup (in case the mechanic literally named a
    fleet "7"). This keeps both `fleet show 7` (id) and `fleet show
    "7-day loaner"` (name) ergonomic.
    """
    from motodiag.advanced.fleet_repo import (
        FleetNotFoundError,
        _resolve_fleet,
    )

    raw = str(fleet).strip()
    if raw.isdigit():
        try:
            return _resolve_fleet(int(raw))
        except FleetNotFoundError:
            # Fall back to name lookup — mechanic may have named a fleet
            # numerically.
            pass
    try:
        return _resolve_fleet(raw)
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


# --- Phase 152: service history renderers ------------------------------


def _format_cost(cents: Optional[int]) -> str:
    """Render cost_cents as ``$XX.YY`` or a dim em-dash when absent."""
    if cents is None:
        return "[dim]-[/dim]"
    dollars = int(cents) / 100.0
    return f"${dollars:,.2f}"


def _render_history_rows(
    console,
    rows: list[dict],
    *,
    bike_label: str,
    include_bike_col: bool = False,
) -> None:
    """Render a Rich Table for a list of service_history rows.

    Columns: (Bike, optional) | Date | Type | Miles | Cost | Mechanic |
    Parts | Notes. The cross-bike views (show-all, by-type) toggle
    the Bike column on; the per-bike list view omits it.
    """
    table = Table(
        title=f"Service history ({len(rows)}) — {bike_label}",
        header_style="bold cyan",
    )
    if include_bike_col:
        table.add_column("Bike", no_wrap=True, justify="right")
    table.add_column("Date", no_wrap=True)
    table.add_column("Type", no_wrap=True)
    table.add_column("Miles", no_wrap=True, justify="right")
    table.add_column("Cost", no_wrap=True, justify="right")
    table.add_column("Mechanic", no_wrap=True, justify="right")
    table.add_column("Parts", overflow="fold", max_width=30)
    table.add_column("Notes", overflow="fold", max_width=40)

    for r in rows:
        miles_raw = r.get("at_miles")
        miles_cell = (
            f"{int(miles_raw):,}" if miles_raw is not None else "[dim]-[/dim]"
        )
        mech_raw = r.get("mechanic_user_id")
        mech_cell = f"#{int(mech_raw)}" if mech_raw is not None else "[dim]-[/dim]"
        parts_cell = r.get("parts_csv") or "[dim]-[/dim]"
        notes_cell = r.get("notes") or "[dim]-[/dim]"
        cells = []
        if include_bike_col:
            cells.append(f"#{int(r.get('vehicle_id') or 0)}")
        cells.extend([
            str(r.get("at_date") or ""),
            str(r.get("event_type") or ""),
            miles_cell,
            _format_cost(r.get("cost_cents")),
            mech_cell,
            parts_cell,
            notes_cell,
        ])
        table.add_row(*cells)

    console.print(table)


def _render_schedule_rows(
    console,
    items: list[dict],
    *,
    title: str,
    overdue: bool = False,
) -> None:
    """Render the Rich table for ``schedule due`` / ``schedule overdue``.

    Columns: Item / Description / Every / Last done / Next due /
    Miles to go / Days to go. Negative remaining values render red
    (overdue); values within 20 % of the interval render cyan (imminent).
    """
    table = Table(
        title=title,
        header_style="bold red" if overdue else "bold cyan",
    )
    table.add_column("Item", no_wrap=True)
    table.add_column("Description", overflow="fold", max_width=32)
    table.add_column("Every", no_wrap=True)
    table.add_column("Last done", no_wrap=True)
    table.add_column("Next due", no_wrap=True)
    table.add_column("Miles to go", no_wrap=True, justify="right")
    table.add_column("Days to go", no_wrap=True, justify="right")

    for r in items:
        every_parts: list[str] = []
        if r.get("every_miles") is not None:
            every_parts.append(f"{int(r['every_miles']):,} mi")
        if r.get("every_months") is not None:
            every_parts.append(f"{int(r['every_months'])} mo")
        last_parts: list[str] = []
        if r.get("last_done_miles") is not None:
            last_parts.append(f"{int(r['last_done_miles']):,} mi")
        if r.get("last_done_at"):
            last_parts.append(str(r["last_done_at"])[:10])
        next_parts: list[str] = []
        if r.get("next_due_miles") is not None:
            next_parts.append(f"{int(r['next_due_miles']):,} mi")
        if r.get("next_due_at"):
            next_parts.append(str(r["next_due_at"])[:10])

        miles_rem = r.get("miles_remaining")
        days_rem = r.get("days_remaining")

        def _fmt_miles(val: Optional[int]) -> str:
            if val is None:
                return "[dim]-[/dim]"
            every = r.get("every_miles")
            if val < 0:
                return f"[red]{val:,}[/red]"
            if every and every > 0 and val <= int(every) * 0.2:
                return f"[cyan]{val:,}[/cyan]"
            return f"{val:,}"

        def _fmt_days(val: Optional[int]) -> str:
            if val is None:
                return "[dim]-[/dim]"
            every_months = r.get("every_months")
            if val < 0:
                return f"[red]{val}[/red]"
            if every_months and every_months > 0:
                days_interval = int(every_months) * 30
                if days_interval > 0 and val <= days_interval * 0.2:
                    return f"[cyan]{val}[/cyan]"
            return str(val)

        table.add_row(
            r.get("item_slug", ""),
            r.get("description", "") or "[dim]-[/dim]",
            " / ".join(every_parts) or "[dim]-[/dim]",
            " / ".join(last_parts) or "[dim]-[/dim]",
            " / ".join(next_parts) or "[dim]-[/dim]",
            _fmt_miles(miles_rem),
            _fmt_days(days_rem),
        )
    console.print(table)
