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

import json
import os
import textwrap
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
    close_session, update_session, reopen_session, append_note, get_notes,
)
from motodiag.knowledge.issues_repo import search_known_issues
from motodiag.vehicles.registry import get_vehicle

# --- Slug parsing tunables ---

SLUG_YEAR_MIN = 1980
SLUG_YEAR_MAX = 2035

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


def _parse_slug(slug: str) -> tuple[str, Optional[int]]:
    """Split a slug like 'sportster-2001' into (stem, year_or_None).

    Rules:
    - Split on the LAST '-'. If the trailing token is a 4-digit int within
      [SLUG_YEAR_MIN, SLUG_YEAR_MAX], treat it as a year; otherwise no year.
    - Stem is lowercased and trimmed.
    - A slug with no '-' (e.g., 'sportster') returns (slug_lower, None).
    """
    if not slug:
        return "", None
    s = slug.strip().lower()
    if "-" not in s:
        return s, None
    stem, _, tail = s.rpartition("-")
    try:
        year = int(tail)
    except ValueError:
        return s, None
    if SLUG_YEAR_MIN <= year <= SLUG_YEAR_MAX:
        return stem.strip(), year
    # Out-of-range integer — treat the whole thing as stem.
    return s, None


def _resolve_bike_slug(
    slug: str, db_path: Optional[str] = None,
) -> Optional[dict]:
    """Resolve a human-friendly bike slug to a vehicle row dict (or None).

    Slug format: ``<stem>[-<year>]`` where stem matches make or model
    case-insensitively via LIKE. Examples: ``sportster-2001``, ``cbr929-2000``,
    ``harley``.

    Match priority:
      1. Exact model match (model = stem, case-insensitive)
      2. Exact make match (make = stem, case-insensitive)
      3. Partial model LIKE match
      4. Partial make LIKE match

    Within each tier, if multiple rows match we prefer the oldest by
    ``created_at`` (deterministic). If a year is parsed from the slug, it
    is applied as a hard filter in all tiers.

    Returns None when no row matches.
    """
    stem, year = _parse_slug(slug)
    if not stem:
        return None

    with get_connection(db_path) as conn:
        # Tier 1: exact model match
        q1 = "SELECT * FROM vehicles WHERE LOWER(model) = ?"
        params1: list = [stem]
        if year is not None:
            q1 += " AND year = ?"
            params1.append(year)
        q1 += " ORDER BY created_at, id LIMIT 1"
        row = conn.execute(q1, params1).fetchone()
        if row is not None:
            return dict(row)

        # Tier 2: exact make match
        q2 = "SELECT * FROM vehicles WHERE LOWER(make) = ?"
        params2: list = [stem]
        if year is not None:
            q2 += " AND year = ?"
            params2.append(year)
        q2 += " ORDER BY created_at, id LIMIT 1"
        row = conn.execute(q2, params2).fetchone()
        if row is not None:
            return dict(row)

        # Tier 3: partial model LIKE
        q3 = "SELECT * FROM vehicles WHERE LOWER(model) LIKE ?"
        params3: list = [f"%{stem}%"]
        if year is not None:
            q3 += " AND year = ?"
            params3.append(year)
        q3 += " ORDER BY created_at, id LIMIT 1"
        row = conn.execute(q3, params3).fetchone()
        if row is not None:
            return dict(row)

        # Tier 4: partial make LIKE
        q4 = "SELECT * FROM vehicles WHERE LOWER(make) LIKE ?"
        params4: list = [f"%{stem}%"]
        if year is not None:
            q4 += " AND year = ?"
            params4.append(year)
        q4 += " ORDER BY created_at, id LIMIT 1"
        row = conn.execute(q4, params4).fetchone()
        if row is not None:
            return dict(row)

    return None


def _list_garage_summary(db_path: Optional[str] = None, limit: int = 10) -> list[dict]:
    """Return a small list of garage rows for error-path hints. Best-effort."""
    try:
        with get_connection(db_path) as conn:
            rows = conn.execute(
                "SELECT id, make, model, year FROM vehicles "
                "ORDER BY created_at, id LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


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


# --- Phase 126: Report formatters (pure dict → str) ---
#
# Three output formats for `motodiag diagnose show --format ...`:
#   txt  — plain text for email / print (no Rich markup)
#   json — structured, versioned dump (full session row)
#   md   — GitHub-flavored markdown, headings + key-value table
#
# Each formatter is a pure function of the session dict so they can be
# unit-tested without file I/O and reused by Phase 132 (export/share).

# Bumps on any schema change to the JSON output.
_REPORT_FORMAT_VERSION = "1"

# Text-wrap column width for the plain-text formatter.
_TEXT_WRAP_COL = 80


def _short_ts(ts: Any) -> str:
    """Return the first 19 chars of an ISO timestamp, or '-' for None/empty.

    Timestamps from session_repo are ISO strings like
    '2026-04-17T14:33:21.123456'. Truncating to 19 chars gives 'YYYY-MM-DD
    HH:MM:SS' which is readable in all three formats.
    """
    if not ts:
        return "-"
    s = str(ts)
    return s[:19] if len(s) > 19 else s


def _fmt_list(items: Optional[list], empty: str = "-") -> str:
    """Join a list with ', ' or return `empty` if None/empty.

    Defensive against None — session_repo guarantees a list but external
    callers (and tests with minimal dicts) may pass None.
    """
    if not items:
        return empty
    return ", ".join(str(x) for x in items)


def _fmt_conf(conf: Optional[float]) -> str:
    """Format confidence as '0.87' or '-' if None."""
    if conf is None:
        return "-"
    try:
        return f"{float(conf):.2f}"
    except (TypeError, ValueError):
        return "-"


def _format_session_text(session: dict) -> str:
    """Render a session dict as plain text (no Rich markup, 80-col wrapped).

    Layout:
        Session #42   status: closed
        ============================

        Vehicle
        -------
        2001 Harley-Davidson Sportster 1200

        Symptoms
        --------
        won't start, cranks slow

        Fault codes
        -----------
        P0300

        Diagnosis
        ---------
        Stator failure — voltage drops under load.
        Confidence: 0.87   Severity: high

        Repair steps
        ------------
          1. Check stator continuity (service manual §7-3)
          2. Replace stator if reading < 0.2Ω

        Metadata
        --------
        AI model: haiku    Tokens: 1432
        Created: 2026-04-17 14:33:21
        Closed:  2026-04-17 14:34:05
    """
    sid = session.get("id", "?")
    status = session.get("status") or "-"

    lines: list[str] = []
    heading = f"Session #{sid}   status: {status}"
    lines.append(heading)
    lines.append("=" * len(heading))
    lines.append("")

    # --- Vehicle
    lines.append("Vehicle")
    lines.append("-------")
    vehicle_str = (
        f"{session.get('vehicle_year', '?')} "
        f"{session.get('vehicle_make', '?')} "
        f"{session.get('vehicle_model', '?')}"
    )
    lines.append(vehicle_str.strip())
    lines.append("")

    # --- Symptoms
    lines.append("Symptoms")
    lines.append("--------")
    symp_text = _fmt_list(session.get("symptoms"))
    lines.append(textwrap.fill(symp_text, width=_TEXT_WRAP_COL) or "-")
    lines.append("")

    # --- Fault codes
    lines.append("Fault codes")
    lines.append("-----------")
    fc_text = _fmt_list(session.get("fault_codes"))
    lines.append(textwrap.fill(fc_text, width=_TEXT_WRAP_COL) or "-")
    lines.append("")

    # --- Diagnosis
    lines.append("Diagnosis")
    lines.append("---------")
    diag = session.get("diagnosis") or "(none)"
    # textwrap.fill handles long diagnosis text; preserve paragraph breaks
    # by wrapping each non-empty line independently.
    for para in str(diag).split("\n"):
        wrapped = textwrap.fill(para, width=_TEXT_WRAP_COL) if para else ""
        lines.append(wrapped)
    conf_str = _fmt_conf(session.get("confidence"))
    sev = session.get("severity") or "-"
    lines.append(f"Confidence: {conf_str}   Severity: {sev}")
    lines.append("")

    # --- Repair steps
    lines.append("Repair steps")
    lines.append("------------")
    steps = session.get("repair_steps") or []
    if steps:
        for i, step in enumerate(steps, 1):
            # Wrap long steps with a hanging indent matching the bullet.
            prefix = f"  {i}. "
            wrapped = textwrap.fill(
                str(step),
                width=_TEXT_WRAP_COL,
                initial_indent=prefix,
                subsequent_indent=" " * len(prefix),
            )
            lines.append(wrapped)
    else:
        lines.append("  (none)")
    lines.append("")

    # --- Notes (Phase 127) — append-only annotations. Each entry starts
    # with a ``[YYYY-MM-DDTHH:MM]`` prefix separated from the next by a
    # blank line. Wrap long lines but preserve the paragraph breaks.
    notes = session.get("notes")
    if notes:
        lines.append("Notes")
        lines.append("-----")
        for para in str(notes).split("\n"):
            wrapped = textwrap.fill(para, width=_TEXT_WRAP_COL) if para else ""
            lines.append(wrapped)
        lines.append("")

    # --- Metadata
    lines.append("Metadata")
    lines.append("--------")
    model = session.get("ai_model_used") or "-"
    tokens = session.get("tokens_used")
    tokens_str = str(tokens) if tokens is not None else "-"
    lines.append(f"AI model: {model}    Tokens: {tokens_str}")
    lines.append(f"Created: {_short_ts(session.get('created_at'))}")
    if session.get("closed_at"):
        lines.append(f"Closed:  {_short_ts(session.get('closed_at'))}")
    elif session.get("updated_at"):
        lines.append(f"Updated: {_short_ts(session.get('updated_at'))}")

    # Trailing newline so Unix pipelines play nicely.
    return "\n".join(lines) + "\n"


def _format_session_json(session: dict) -> str:
    """Render a session dict as pretty-printed JSON with a format_version tag.

    The output is a JSON object with the version key first, then all session
    fields verbatim. Round-trips through `json.loads` with all fields preserved.
    Uses `indent=2` and `ensure_ascii=False` so non-ASCII symptom text
    (e.g. mechanic notes) survives untouched.
    """
    # Ordered: version key first, then the rest of the session dict in its
    # existing key order.  dict() preserves insertion order in 3.7+.
    out: dict = {"format_version": _REPORT_FORMAT_VERSION}
    for k, v in session.items():
        out[k] = v
    return json.dumps(out, indent=2, ensure_ascii=False, default=str)


def _format_session_md(session: dict) -> str:
    """Render a session dict as GitHub-flavored markdown.

    Structure:
        # Session #42
        ## Vehicle
        - Year: 2001
        - Make: Harley-Davidson
        ...
        ## Symptoms
        - won't start
        ...
        ## Diagnosis
        Stator failure — voltage drops under load.
        | Confidence | Severity | AI model | Tokens |
        |---|---|---|---|
        | 0.87 | high | haiku | 1432 |
        ## Repair Steps
        1. Check stator continuity
        2. Replace stator
        ## Timestamps
        - Created: 2026-04-17 14:33:21
        - Closed:  2026-04-17 14:34:05
    """
    sid = session.get("id", "?")
    status = session.get("status") or "-"
    lines: list[str] = []

    lines.append(f"# Session #{sid}")
    lines.append("")
    lines.append(f"_Status_: **{status}**")
    lines.append("")

    # --- Vehicle
    lines.append("## Vehicle")
    lines.append("")
    lines.append(f"- Year: {session.get('vehicle_year', '?')}")
    lines.append(f"- Make: {session.get('vehicle_make', '?')}")
    lines.append(f"- Model: {session.get('vehicle_model', '?')}")
    if session.get("vehicle_id") is not None:
        lines.append(f"- Vehicle ID: {session.get('vehicle_id')}")
    lines.append("")

    # --- Symptoms
    lines.append("## Symptoms")
    lines.append("")
    symptoms = session.get("symptoms") or []
    if symptoms:
        for s in symptoms:
            lines.append(f"- {s}")
    else:
        lines.append("_none recorded_")
    lines.append("")

    # --- Fault codes
    lines.append("## Fault Codes")
    lines.append("")
    codes = session.get("fault_codes") or []
    if codes:
        for c in codes:
            lines.append(f"- `{c}`")
    else:
        lines.append("_none recorded_")
    lines.append("")

    # --- Diagnosis
    lines.append("## Diagnosis")
    lines.append("")
    diag = session.get("diagnosis") or "_(none)_"
    lines.append(str(diag))
    lines.append("")
    # Metadata table
    conf_str = _fmt_conf(session.get("confidence"))
    sev = session.get("severity") or "-"
    model = session.get("ai_model_used") or "-"
    tokens = session.get("tokens_used")
    tokens_str = str(tokens) if tokens is not None else "-"
    lines.append("| Confidence | Severity | AI model | Tokens |")
    lines.append("|---|---|---|---|")
    lines.append(f"| {conf_str} | {sev} | {model} | {tokens_str} |")
    lines.append("")

    # --- Repair Steps
    lines.append("## Repair Steps")
    lines.append("")
    steps = session.get("repair_steps") or []
    if steps:
        for i, step in enumerate(steps, 1):
            lines.append(f"{i}. {step}")
    else:
        lines.append("_no repair steps recorded_")
    lines.append("")

    # --- Notes (Phase 127) — included only when present. Preserves the
    # ``[YYYY-MM-DDTHH:MM]`` prefix and the blank-line separator between
    # entries so markdown renderers show each annotation as its own
    # paragraph.
    notes = session.get("notes")
    if notes:
        lines.append("## Notes")
        lines.append("")
        lines.append(str(notes))
        lines.append("")

    # --- Timestamps
    lines.append("## Timestamps")
    lines.append("")
    lines.append(f"- Created: {_short_ts(session.get('created_at'))}")
    if session.get("updated_at"):
        lines.append(f"- Updated: {_short_ts(session.get('updated_at'))}")
    if session.get("closed_at"):
        lines.append(f"- Closed: {_short_ts(session.get('closed_at'))}")
    lines.append("")

    return "\n".join(lines)


def _write_report_to_file(path: str, content: str, overwrite_confirmed: bool) -> None:
    """Write `content` to `path` (UTF-8, LF line endings).

    - Creates parent directories as needed.
    - If `path` is an existing directory → ClickException.
    - If `path` exists as a file and `overwrite_confirmed` is False → prompts via
      click.confirm; raising Abort on decline.
    - PermissionError → ClickException with clear message.

    `newline=""` is passed to `open()` to prevent Python from translating
    the LF in our formatter output to CRLF on Windows, which would double
    up line endings if the content already contained `\r\n`.
    """
    # Directory-as-output guard — must come before anything that would create
    # a parent directory (which could swallow the error as "file exists").
    if os.path.isdir(path):
        raise click.ClickException(
            f"Output path is a directory, not a file: {path}"
        )

    if os.path.exists(path) and not overwrite_confirmed:
        if not click.confirm(
            f"File exists: {path}. Overwrite?", default=False
        ):
            raise click.Abort()

    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        try:
            os.makedirs(parent, exist_ok=True)
        except PermissionError as e:
            raise click.ClickException(
                f"Permission denied creating directory {parent}: {e}"
            ) from e

    try:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(content)
    except PermissionError as e:
        raise click.ClickException(
            f"Permission denied writing to {path}: {e}"
        ) from e
    except IsADirectoryError as e:  # pragma: no cover — covered by isdir() above
        raise click.ClickException(
            f"Output path is a directory, not a file: {path}"
        ) from e


# --- Click commands registered in cli/main.py via register_diagnose(cli) ---


def register_diagnose(cli_group: click.Group) -> None:
    """Attach the `diagnose` subgroup to the top-level CLI."""

    @cli_group.group()
    def diagnose() -> None:
        """AI-assisted diagnostic sessions."""

    @diagnose.command("quick")
    @click.option("--vehicle-id", default=None, type=int,
                  help="Numeric vehicle ID from the garage.")
    @click.option("--bike", default=None,
                  help="Human-friendly bike slug, e.g. 'sportster-2001' or 'cbr929-2000'.")
    @click.option("--symptoms", required=True, help="Comma-separated symptom list.")
    @click.option("--description", default=None, help="Optional free-text description.")
    @click.option("--model", "ai_model_flag", default=None,
                  type=click.Choice(["haiku", "sonnet"], case_sensitive=False))
    def diagnose_quick(vehicle_id: Optional[int], bike: Optional[str],
                       symptoms: str, description: Optional[str],
                       ai_model_flag: Optional[str]) -> None:
        """Run a one-shot diagnosis without Q&A."""
        console = Console()
        init_db()

        # Resolve vehicle — either by ID (primary) or by slug (sugar).
        if vehicle_id is None and not bike:
            console.print(
                "[red]Specify a vehicle with --vehicle-id N or --bike SLUG "
                "(e.g. --bike sportster-2001).[/red]"
            )
            raise click.Abort()

        if vehicle_id is not None and bike:
            console.print(
                "[yellow]⚠ Both --vehicle-id and --bike given; using --vehicle-id.[/yellow]"
            )

        vehicle: Optional[dict]
        if vehicle_id is not None:
            vehicle = _load_vehicle(vehicle_id)
            if vehicle is None:
                console.print(
                    f"[red]Vehicle #{vehicle_id} not found. "
                    f"Add one first with 'garage add'.[/red]"
                )
                raise click.Abort()
        else:
            # bike is non-empty here
            vehicle = _resolve_bike_slug(bike)  # type: ignore[arg-type]
            if vehicle is None:
                console.print(f"[red]No bike matches slug {bike!r}.[/red]")
                garage = _list_garage_summary()
                if garage:
                    console.print("[dim]Your garage:[/dim]")
                    for v in garage:
                        console.print(
                            f"  [cyan]#{v['id']}[/cyan]  "
                            f"{v['year']} {v['make']} {v['model']}"
                        )
                else:
                    console.print(
                        "[dim]Your garage is empty. "
                        "Add a bike with 'motodiag garage add'.[/dim]"
                    )
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
                  type=click.Choice(["open", "diagnosed", "closed"], case_sensitive=False),
                  help="Filter by lifecycle status.")
    @click.option("--vehicle-id", "vehicle_id", default=None, type=int,
                  help="Filter to sessions for a specific vehicle ID.")
    @click.option("--make", "make", default=None,
                  help="Filter by vehicle make (case-insensitive substring).")
    @click.option("--model", "model_", default=None,
                  help="Filter by vehicle model (case-insensitive substring).")
    @click.option("--search", default=None,
                  help="Case-insensitive substring search on diagnosis text.")
    @click.option("--since", default=None,
                  help="Include sessions created on or after this ISO date (YYYY-MM-DD).")
    @click.option("--until", default=None,
                  help="Include sessions created on or before this ISO date (YYYY-MM-DD).")
    @click.option("--limit", default=50, type=int, show_default=True,
                  help="Cap number of rows returned (prevents terminal-spam on large histories).")
    def diagnose_list_cmd(
        status: Optional[str],
        vehicle_id: Optional[int],
        make: Optional[str],
        model_: Optional[str],
        search: Optional[str],
        since: Optional[str],
        until: Optional[str],
        limit: int,
    ) -> None:
        """List diagnostic sessions.

        Phase 127 adds richer filtering: vehicle_id, make/model, free-text
        search on diagnosis, created_at date range, and a result cap. All
        filters AND together. Newest-first ordering preserved from Phase 123.
        """
        console = Console()
        init_db()

        # `--until YYYY-MM-DD` is inclusive of that whole day. Append a time
        # suffix so the string comparison against ISO timestamps includes
        # anything recorded on the until date (otherwise `2026-04-15` < any
        # timestamp on 2026-04-15 and the day's sessions would be dropped).
        until_param = until
        if until_param and "T" not in until_param and " " not in until_param:
            until_param = f"{until_param}T23:59:59"

        sessions = list_sessions(
            status=status,
            vehicle_make=make,
            vehicle_model=model_,
            vehicle_id=vehicle_id,
            search=search,
            since=since,
            until=until_param,
            limit=limit,
        )
        if not sessions:
            # Phase 127 tweak: if any filter was applied, the "no match"
            # wording is more accurate than the Phase 123 "no sessions yet".
            any_filter = any(
                v is not None for v in
                (status, vehicle_id, make, model_, search, since, until)
            )
            if any_filter:
                console.print(
                    "[yellow]No sessions match the filters.[/yellow]"
                )
            else:
                console.print(
                    "[yellow]No sessions yet. Start one with "
                    "'diagnose start' or 'diagnose quick'.[/yellow]"
                )
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

    @diagnose.command("reopen")
    @click.argument("session_id", type=int)
    def diagnose_reopen_cmd(session_id: int) -> None:
        """Reopen a closed diagnostic session for continued work.

        Flips status from 'closed' (or 'diagnosed') back to 'open' and
        clears closed_at. The existing diagnosis, confidence, repair_steps,
        and all other fields are preserved — this is a pure status flip.
        Calling reopen on an already-open session is a no-op and prints a
        yellow warning.
        """
        console = Console()
        init_db()

        existing = get_session(session_id)
        if existing is None:
            raise click.ClickException(
                f"Session #{session_id} not found."
            )

        if existing.get("status") == "open":
            console.print(
                f"[yellow]Session #{session_id} is already open; "
                f"nothing to do.[/yellow]"
            )
            return

        ok = reopen_session(session_id)
        if not ok:
            # Race condition: session disappeared between check and update.
            raise click.ClickException(
                f"Session #{session_id} could not be reopened."
            )
        console.print(f"[green]Session #{session_id} reopened.[/green]")

    @diagnose.command("annotate")
    @click.argument("session_id", type=int)
    @click.argument("note_text")
    def diagnose_annotate_cmd(session_id: int, note_text: str) -> None:
        """Append a timestamped note to a diagnostic session.

        Notes are append-only so annotation history is preserved. Each
        entry is prefixed with ``[YYYY-MM-DDTHH:MM]``. The full accumulated
        notes column is printed after appending so the mechanic can verify
        the chronological trail.
        """
        console = Console()
        init_db()

        existing = get_session(session_id)
        if existing is None:
            raise click.ClickException(
                f"Session #{session_id} not found."
            )

        ok = append_note(session_id, note_text)
        if not ok:
            raise click.ClickException(
                f"Session #{session_id} could not be annotated."
            )
        console.print(
            f"[green]Note added to session #{session_id}.[/green]"
        )
        # Echo the accumulated notes so the mechanic can see the full trail.
        current = get_notes(session_id)
        if current:
            console.print(Panel(current, title="Notes", border_style="dim"))

    @diagnose.command("show")
    @click.argument("session_id", type=int)
    @click.option(
        "--format", "output_format",
        type=click.Choice(["terminal", "txt", "json", "md"], case_sensitive=False),
        default="terminal",
        show_default=True,
        help="Output format. 'terminal' preserves the Phase 123 Rich rendering.",
    )
    @click.option(
        "--output", "output_path",
        type=click.Path(dir_okay=False, writable=True, resolve_path=False),
        default=None,
        help="Write report to PATH instead of stdout. Ignored with --format terminal.",
    )
    @click.option(
        "--yes", "-y", "assume_yes",
        is_flag=True, default=False,
        help="Skip overwrite confirmation when --output points to an existing file.",
    )
    def diagnose_show(
        session_id: int,
        output_format: str,
        output_path: Optional[str],
        assume_yes: bool,
    ) -> None:
        """Render a saved diagnostic session.

        Without flags, renders a Rich Panel to the terminal (Phase 123 behavior).
        With --format txt|json|md, prints the chosen format to stdout, or writes
        to --output PATH if given.
        """
        console = Console()
        init_db()
        s = get_session(session_id)
        if s is None:
            console.print(f"[red]Session #{session_id} not found.[/red]")
            raise click.Abort()

        fmt = output_format.lower()

        # Phase 123 terminal path — unchanged behavior.
        if fmt == "terminal":
            if output_path:
                console.print(
                    "[yellow]⚠ --output ignored with --format terminal. "
                    "Use --format txt|json|md to write a file.[/yellow]"
                )

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

            # Phase 127: show annotation history below the Result panel so
            # a mechanic reviewing a reopened session sees the post-hoc
            # notes trail immediately (and doesn't need `diagnose show
            # --format md` just to find them).
            notes = s.get("notes")
            if notes:
                console.print(Panel(str(notes), title="Notes", border_style="dim"))
            return

        # Non-terminal export formats
        if fmt == "txt":
            content = _format_session_text(s)
        elif fmt == "json":
            content = _format_session_json(s)
        elif fmt == "md":
            content = _format_session_md(s)
        else:  # pragma: no cover — click.Choice guards this
            raise click.ClickException(f"Unknown format: {output_format}")

        if output_path:
            _write_report_to_file(output_path, content, overwrite_confirmed=assume_yes)
            click.echo(f"Saved to {output_path}")
        else:
            # Use click.echo so CliRunner captures it and newline handling
            # is consistent with other commands.
            click.echo(content, nl=False)


def register_quick(cli_group: click.Group) -> None:
    """Attach the top-level `quick` shortcut command to the CLI.

    Phase 125: `motodiag quick "<symptoms>" [--bike SLUG | --vehicle-id N]`
    collapses `motodiag diagnose quick --symptoms "..."` into one less word.
    Delegates to the existing `diagnose quick` callback via ``ctx.invoke`` so
    there is a single implementation to maintain.

    Must be called AFTER ``register_diagnose(cli_group)`` — this function
    looks up the existing ``diagnose quick`` command on the group.
    """
    # Resolve the already-registered `diagnose quick` command.
    diagnose_group = cli_group.commands.get("diagnose")
    if diagnose_group is None or not isinstance(diagnose_group, click.Group):
        raise RuntimeError(
            "register_quick must be called after register_diagnose — "
            "no 'diagnose' group found on CLI."
        )
    quick_cmd = diagnose_group.commands.get("quick")
    if quick_cmd is None:
        raise RuntimeError(
            "register_quick: 'diagnose quick' command not registered."
        )

    @cli_group.command("quick")
    @click.argument("symptoms")
    @click.option("--vehicle-id", default=None, type=int,
                  help="Numeric vehicle ID from the garage.")
    @click.option("--bike", default=None,
                  help="Human-friendly bike slug, e.g. 'sportster-2001'.")
    @click.option("--description", default=None,
                  help="Optional free-text description.")
    @click.option("--model", "ai_model_flag", default=None,
                  type=click.Choice(["haiku", "sonnet"], case_sensitive=False))
    @click.pass_context
    def quick_shortcut(
        ctx: click.Context,
        symptoms: str,
        vehicle_id: Optional[int],
        bike: Optional[str],
        description: Optional[str],
        ai_model_flag: Optional[str],
    ) -> None:
        """Shortcut for `motodiag diagnose quick` — fewer keystrokes.

        Example: `motodiag quick "won't start when cold" --bike sportster-2001`
        """
        ctx.invoke(
            quick_cmd,
            vehicle_id=vehicle_id,
            bike=bike,
            symptoms=symptoms,
            description=description,
            ai_model_flag=ai_model_flag,
        )
