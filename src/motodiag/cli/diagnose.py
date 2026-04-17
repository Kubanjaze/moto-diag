"""Interactive diagnostic session CLI orchestration.

Phase 123: wires DiagnosticClient.diagnose() into the CLI as two surfaces —
`start` (interactive Q&A loop with up to 3 clarifying rounds) and `quick`
(one-shot). Each user-visible interaction = one `diagnostic_sessions` row;
rounds within a session accumulate tokens_used.

Tier-based model access (Phase 118 subscriptions.tier):
  individual → Haiku only
  shop/company → Haiku default, Sonnet unlocked via --model sonnet

All AI calls go through an injectable `diagnose_fn` so tests never burn tokens.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from motodiag.cli.subscription import (
    SubscriptionTier,
    current_tier,
    get_enforcement_mode,
    ENFORCEMENT_MODE_HARD,
)
from motodiag.core.database import init_db, get_connection
from motodiag.core.session_repo import (
    create_session, get_session, list_sessions, set_diagnosis,
    close_session, update_session,
)
from motodiag.knowledge.issues_repo import search_known_issues
from motodiag.vehicles.registry import get_vehicle

# Engine imports are lazy inside functions to keep CLI import fast and
# to make mocking via `diagnose_fn` parameter straightforward in tests.


# --- Tunable constants ---

CONFIDENCE_ACCEPT_THRESHOLD = 0.7
MAX_CLARIFYING_ROUNDS = 3  # Hard cap regardless of confidence


# Tier → allowed AI models (mirrors cli/subscription.TIER_LIMITS but
# simpler local view for model-access gating only)
_TIER_MODEL_ACCESS: dict[str, list[str]] = {
    "individual": ["haiku"],
    "shop": ["haiku", "sonnet"],
    "company": ["haiku", "sonnet"],
}


def _resolve_model(tier_value: str, cli_flag: Optional[str]) -> str:
    """Pick the AI model for a diagnose call given tier + CLI flag.

    Returns "haiku" or "sonnet".

    Raises click.ClickException in HARD paywall mode if the CLI flag
    requests a model the tier doesn't cover. In SOFT mode, we silently
    downgrade and print a warning at the call site.
    """
    allowed = _TIER_MODEL_ACCESS.get(tier_value.lower(), ["haiku"])
    default = "haiku"

    if cli_flag is None:
        return default

    flag = cli_flag.lower()
    if flag not in ("haiku", "sonnet"):
        raise click.ClickException(f"Unknown model: {cli_flag!r}. Use haiku or sonnet.")

    if flag in allowed:
        return flag

    # Requested model not in tier — behavior depends on enforcement mode
    mode = get_enforcement_mode()
    if mode == ENFORCEMENT_MODE_HARD:
        raise click.ClickException(
            f"Sonnet access requires Shop tier ($99/mo) or higher. "
            f"Your current tier: {tier_value}. "
            f"Upgrade at https://motodiag.app/pricing"
        )
    # Soft mode: caller should warn and fall back to default
    return default


def _load_vehicle(vehicle_id: int, db_path: Optional[str] = None) -> Optional[dict]:
    """Resolve a vehicle row from the vehicles table, or None if missing."""
    return get_vehicle(vehicle_id, db_path=db_path)


def _load_known_issues(
    make: str, model_name: str, year: int, db_path: Optional[str] = None,
) -> list[dict]:
    """Retrieve knowledge-base known issues for the vehicle, used as AI context."""
    try:
        return search_known_issues(
            make=make, model=model_name, year=year, db_path=db_path,
        )
    except Exception:
        return []


def _parse_symptoms(text: str) -> list[str]:
    """Split freeform symptom text into a list.

    Simple v1 — split on commas + newlines + semicolons, strip, drop empties.
    Phase 125 + Track R 318 can upgrade to proper NLP.
    """
    if not text:
        return []
    parts: list[str] = []
    for line in text.replace(";", ",").replace("\n", ",").split(","):
        s = line.strip()
        if s:
            parts.append(s)
    return parts


# --- Default production diagnose caller ---


def _default_diagnose_fn(
    make: str,
    model_name: str,
    year: int,
    symptoms: list[str],
    description: Optional[str],
    mileage: Optional[int],
    engine_type: Optional[str],
    known_issues: Optional[list[dict]],
    ai_model: str,
) -> tuple[Any, Any]:
    """Default production implementation — calls DiagnosticClient.diagnose().

    Separate from orchestration functions so tests inject a mock without
    needing anthropic SDK installed. Returns (DiagnosticResponse, TokenUsage).
    """
    from motodiag.engine.client import DiagnosticClient

    client = DiagnosticClient(model=ai_model)
    return client.diagnose(
        make=make,
        model_name=model_name,
        year=year,
        symptoms=symptoms,
        description=description,
        mileage=mileage,
        engine_type=engine_type,
        known_issues=known_issues,
        ai_model=ai_model,
    )


# --- Core orchestrations ---


def _run_quick(
    vehicle: dict,
    symptoms: list[str],
    description: Optional[str],
    ai_model: str,
    db_path: Optional[str] = None,
    diagnose_fn: Optional[Callable] = None,
) -> tuple[int, Any]:
    """Create a session, run one diagnose call, persist, close. Returns (session_id, response)."""
    call = diagnose_fn or _default_diagnose_fn
    session_id = create_session(
        vehicle_make=vehicle["make"],
        vehicle_model=vehicle["model"],
        vehicle_year=vehicle["year"],
        symptoms=symptoms,
        vehicle_id=vehicle.get("id"),
        db_path=db_path,
    )

    known = _load_known_issues(vehicle["make"], vehicle["model"], vehicle["year"], db_path)

    response, usage = call(
        make=vehicle["make"],
        model_name=vehicle["model"],
        year=vehicle["year"],
        symptoms=symptoms,
        description=description,
        mileage=vehicle.get("mileage"),
        engine_type=vehicle.get("engine_type"),
        known_issues=known,
        ai_model=ai_model,
    )

    _persist_response(session_id, response, usage, ai_model, db_path)
    close_session(session_id, db_path)
    return session_id, response


def _run_interactive(
    vehicle: dict,
    ai_model: str,
    db_path: Optional[str] = None,
    diagnose_fn: Optional[Callable] = None,
    prompt_fn: Optional[Callable[[str], str]] = None,
) -> tuple[int, Any]:
    """Interactive Q&A loop. Returns (session_id, final_response).

    Args:
        prompt_fn: Callable(question_text) -> user answer. Defaults to click.prompt.
                   Tests inject a function that returns canned answers.
    """
    call = diagnose_fn or _default_diagnose_fn
    ask = prompt_fn or (lambda q: click.prompt(q, default="", show_default=False))

    initial = ask("Describe the problem (comma-separate symptoms)")
    symptoms = _parse_symptoms(initial)
    description = initial if initial else None

    session_id = create_session(
        vehicle_make=vehicle["make"],
        vehicle_model=vehicle["model"],
        vehicle_year=vehicle["year"],
        symptoms=symptoms,
        vehicle_id=vehicle.get("id"),
        db_path=db_path,
    )

    known = _load_known_issues(vehicle["make"], vehicle["model"], vehicle["year"], db_path)
    total_input = 0
    total_output = 0
    final_response = None

    for round_num in range(1, MAX_CLARIFYING_ROUNDS + 1):
        response, usage = call(
            make=vehicle["make"],
            model_name=vehicle["model"],
            year=vehicle["year"],
            symptoms=symptoms,
            description=description,
            mileage=vehicle.get("mileage"),
            engine_type=vehicle.get("engine_type"),
            known_issues=known,
            ai_model=ai_model,
        )
        total_input += getattr(usage, "input_tokens", 0)
        total_output += getattr(usage, "output_tokens", 0)
        final_response = response

        top = response.diagnoses[0] if response.diagnoses else None
        top_conf = getattr(top, "confidence", 0.0) if top else 0.0

        # Termination conditions
        if top_conf >= CONFIDENCE_ACCEPT_THRESHOLD:
            break
        if not response.additional_tests:
            break
        if round_num == MAX_CLARIFYING_ROUNDS:
            break

        # Ask the mechanic the top suggested test
        test_q = response.additional_tests[0]
        answer = ask(f"Additional info needed — {test_q} (empty to stop)")
        if not answer or answer.strip().lower() in ("skip", "stop", "done"):
            break

        # Append answer to description; leave symptoms as-is
        description = (description or "") + f"\nMechanic answered: {answer}"

    if final_response is not None:
        _persist_response(
            session_id, final_response,
            _FakeUsage(total_input, total_output, ai_model),
            ai_model, db_path,
        )
    close_session(session_id, db_path)
    return session_id, final_response


class _FakeUsage:
    """Minimal shim so _persist_response can handle accumulated totals the same way."""
    def __init__(self, input_tokens: int, output_tokens: int, model: str) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.model = model


def _persist_response(
    session_id: int,
    response: Any,
    usage: Any,
    ai_model: str,
    db_path: Optional[str],
) -> None:
    """Write diagnosis + token metrics to the session row."""
    top = response.diagnoses[0] if getattr(response, "diagnoses", None) else None
    diagnosis_text = (
        f"{top.diagnosis} — {top.rationale}"
        if top and hasattr(top, "diagnosis")
        else (response.notes or "No definitive diagnosis.")
    )
    confidence = getattr(top, "confidence", None) if top else None
    severity = getattr(top, "severity", None) if top else None
    repair_steps = list(getattr(top, "recommended_actions", []) or []) if top else []

    set_diagnosis(
        session_id=session_id,
        diagnosis=diagnosis_text,
        confidence=confidence,
        severity=severity,
        repair_steps=repair_steps,
        db_path=db_path,
    )

    total_tokens = (
        int(getattr(usage, "input_tokens", 0) or 0)
        + int(getattr(usage, "output_tokens", 0) or 0)
    )
    try:
        update_session(
            session_id,
            {"ai_model_used": ai_model, "tokens_used": total_tokens},
            db_path=db_path,
        )
    except Exception:
        # update_session signature may not accept these fields on all paths —
        # fall back to direct SQL
        with get_connection(db_path) as conn:
            conn.execute(
                "UPDATE diagnostic_sessions SET ai_model_used = ?, tokens_used = ? WHERE id = ?",
                (ai_model, total_tokens, session_id),
            )


# --- Rendering ---


def _render_response(response: Any, console: Console) -> None:
    """Pretty-print a DiagnosticResponse."""
    summary = getattr(response, "vehicle_summary", "") or ""
    console.print(Panel(summary or "(no summary)", title="Vehicle", border_style="cyan"))

    diagnoses = getattr(response, "diagnoses", []) or []
    if diagnoses:
        t = Table(title="Ranked Diagnoses")
        t.add_column("#", style="cyan", justify="right")
        t.add_column("Diagnosis", style="bold")
        t.add_column("Confidence", justify="right")
        t.add_column("Severity")
        t.add_column("Rationale", overflow="fold")
        for i, d in enumerate(diagnoses, 1):
            conf = getattr(d, "confidence", 0.0) or 0.0
            t.add_row(
                str(i),
                getattr(d, "diagnosis", "?"),
                f"{conf:.2f}",
                getattr(d, "severity", "-") or "-",
                getattr(d, "rationale", "") or "",
            )
        console.print(t)
    else:
        console.print("[yellow]No definitive diagnosis.[/yellow]")

    tests = getattr(response, "additional_tests", []) or []
    if tests:
        console.print("\n[bold]Suggested additional tests:[/bold]")
        for t_ in tests:
            console.print(f"  • {t_}")

    notes = getattr(response, "notes", None)
    if notes:
        console.print(Panel(notes, title="Notes", border_style="dim"))


# --- Click commands registered in cli/main.py via register_diagnose(cli) ---


def register_diagnose(cli_group: click.Group) -> None:
    """Attach the `diagnose` subgroup to the top-level CLI."""

    @cli_group.group()
    def diagnose() -> None:
        """AI-assisted diagnostic sessions."""

    @diagnose.command("quick")
    @click.option("--vehicle-id", required=True, type=int)
    @click.option("--symptoms", required=True, help="Comma-separated symptom list.")
    @click.option("--description", default=None, help="Optional free-text description.")
    @click.option("--model", "ai_model_flag", default=None,
                  type=click.Choice(["haiku", "sonnet"], case_sensitive=False))
    def diagnose_quick(vehicle_id: int, symptoms: str,
                       description: Optional[str], ai_model_flag: Optional[str]) -> None:
        """Run a one-shot diagnosis without Q&A."""
        console = Console()
        init_db()
        vehicle = _load_vehicle(vehicle_id)
        if vehicle is None:
            console.print(f"[red]Vehicle #{vehicle_id} not found. Add one first with 'garage add'.[/red]")
            raise click.Abort()

        tier = current_tier().value
        ai_model = _resolve_model(tier, ai_model_flag)
        if ai_model_flag and ai_model != ai_model_flag.lower():
            console.print(
                f"[yellow]⚠ Sonnet requires Shop tier+. Falling back to Haiku (soft enforcement).[/yellow]"
            )

        symptom_list = _parse_symptoms(symptoms)
        session_id, response = _run_quick(
            vehicle=vehicle,
            symptoms=symptom_list,
            description=description,
            ai_model=ai_model,
        )
        console.print(f"[green]Session #{session_id} created and diagnosed.[/green]\n")
        _render_response(response, console)

    @diagnose.command("start")
    @click.option("--vehicle-id", default=None, type=int)
    @click.option("--model", "ai_model_flag", default=None,
                  type=click.Choice(["haiku", "sonnet"], case_sensitive=False))
    def diagnose_start(vehicle_id: Optional[int], ai_model_flag: Optional[str]) -> None:
        """Start an interactive diagnostic session with Q&A."""
        console = Console()
        init_db()
        if vehicle_id is None:
            vehicle_id = click.prompt("Vehicle ID", type=int)
        vehicle = _load_vehicle(vehicle_id)
        if vehicle is None:
            console.print(f"[red]Vehicle #{vehicle_id} not found.[/red]")
            raise click.Abort()

        tier = current_tier().value
        ai_model = _resolve_model(tier, ai_model_flag)

        session_id, response = _run_interactive(
            vehicle=vehicle, ai_model=ai_model,
        )
        if response is None:
            console.print("[yellow]Session closed with no diagnosis.[/yellow]")
            return
        console.print(f"\n[green]Session #{session_id} saved.[/green]\n")
        _render_response(response, console)

    @diagnose.command("list")
    @click.option("--status", default=None,
                  type=click.Choice(["open", "diagnosed", "closed"], case_sensitive=False))
    def diagnose_list_cmd(status: Optional[str]) -> None:
        """List diagnostic sessions."""
        console = Console()
        init_db()
        sessions = list_sessions(status=status)
        if not sessions:
            console.print("[yellow]No sessions yet. Start one with 'diagnose start' or 'diagnose quick'.[/yellow]")
            return

        table = Table(title="Diagnostic Sessions")
        table.add_column("ID", style="cyan", justify="right")
        table.add_column("Status")
        table.add_column("Vehicle")
        table.add_column("Top diagnosis", overflow="fold")
        table.add_column("Confidence", justify="right")
        table.add_column("Created", style="dim")
        for s in sessions:
            vehicle_str = f"{s.get('vehicle_year','?')} {s.get('vehicle_make','?')} {s.get('vehicle_model','?')}"
            diag = (s.get("diagnosis") or "-")
            if len(diag) > 60:
                diag = diag[:57] + "..."
            conf = s.get("confidence")
            conf_str = f"{conf:.2f}" if conf is not None else "-"
            table.add_row(
                str(s["id"]), s.get("status", "?"),
                vehicle_str, diag, conf_str,
                str(s.get("created_at", ""))[:19],
            )
        console.print(table)

    @diagnose.command("show")
    @click.argument("session_id", type=int)
    def diagnose_show(session_id: int) -> None:
        """Render a saved diagnostic session."""
        console = Console()
        init_db()
        s = get_session(session_id)
        if s is None:
            console.print(f"[red]Session #{session_id} not found.[/red]")
            raise click.Abort()

        header = (
            f"[bold]Session #{s['id']}[/bold]   status: {s.get('status')}\n"
            f"Vehicle: {s.get('vehicle_year')} {s.get('vehicle_make')} {s.get('vehicle_model')}\n"
            f"Symptoms: {', '.join(s.get('symptoms') or []) or '-'}\n"
            f"Fault codes: {', '.join(s.get('fault_codes') or []) or '-'}\n"
        )
        console.print(Panel(header, title="Session", border_style="cyan"))

        diag = s.get("diagnosis") or "(none)"
        conf = s.get("confidence")
        conf_str = f"{conf:.2f}" if conf is not None else "-"
        sev = s.get("severity") or "-"
        steps = s.get("repair_steps") or []

        body = (
            f"[bold]Diagnosis:[/bold]\n{diag}\n\n"
            f"Confidence: {conf_str}   Severity: {sev}\n"
        )
        if steps:
            body += "\n[bold]Repair steps:[/bold]\n" + "\n".join(f"  • {x}" for x in steps)
        console.print(Panel(body, title="Result", border_style="green"))
