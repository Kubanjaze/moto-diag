"""CLI entrypoint: ``motodiag capture`` — what the product is accumulating.

Phase 244N. Read-only by design. There is deliberately no ``capture record``
command: if a human has to run something, the capture was not passive, and a
capture that is not passive is the one that sat at zero rows for nine phases.
"""

from __future__ import annotations

import click

from motodiag.capture import capture_stats, list_analyses, list_interactions
from motodiag.core.database import get_connection


def register_capture(cli: click.Group) -> None:
    """Register the ``capture`` subgroup on the root CLI."""
    cli.add_command(capture)


@click.group()
def capture() -> None:
    """Passive capture streams (Phase 244N+)."""


@capture.command("stats")
def stats_cmd() -> None:
    """How much ground truth exists, with the denominators that interpret it."""
    s = capture_stats()

    click.echo("Guidance interactions:")
    click.echo(f"  recorded            {s['guidance_interactions']}")
    if s["guidance_interactions"]:
        click.echo(f"    answered          {s['guidance_answered']}")
        click.echo(f"    could not answer  {s['guidance_unanswered']}")

    click.echo("\nMechanic corrections:")
    click.echo(
        f"  session_overrides   {s['session_overrides']}"
        f"   (of {s['sessions_ai_authored']} AI-authored session(s))"
    )
    click.echo(f"  diagnostic_feedback {s['diagnostic_feedback']}")

    click.echo("\nSweep history:")
    click.echo(
        f"  video_analyses      {s['video_analyses']}"
        f"   ({s['video_analyses_superseded']} superseded)"
    )

    # A capture count alone cannot say whether capture works. Zero overrides
    # against zero AI-authored sessions is nothing to correct; zero against
    # forty is a broken hook.
    if s["sessions_ai_authored"] == 0 and s["session_overrides"] == 0:
        click.echo(
            "\n  No AI-authored sessions yet, so there is nothing to correct. "
            "Zero overrides is expected here, not a broken hook."
        )
    elif s["sessions_ai_authored"] and not s["session_overrides"]:
        click.echo(
            f"\n  {s['sessions_ai_authored']} AI-authored session(s) and no "
            "overrides recorded — either nobody has corrected one, or the "
            "PATCH hook is not firing."
        )


@capture.command("interactions")
@click.option("--vehicle", type=int, default=None)
@click.option("--video", type=int, default=None)
@click.option("--limit", type=int, default=20)
def interactions_cmd(vehicle: int | None, video: int | None, limit: int) -> None:
    """Guidance questions and what was answered, newest first."""
    rows = list_interactions(vehicle_id=vehicle, video_id=video, limit=limit)
    if not rows:
        click.echo("No guidance interactions recorded.")
        return
    for r in rows:
        mark = {True: "answered", False: "could not answer", None: "?"}[
            r["answers_the_question"]
        ]
        click.echo(f"[{r['created_at']}] video {r['video_id']} — {mark}")
        click.echo(f"  Q: {r['question']}")
        if r["question_understood_as"]:
            click.echo(f"  understood as: {r['question_understood_as']}")
        click.echo(f"  {r['candidate_count']} candidate(s)")


@capture.command("overrides")
@click.option("--session", type=int, default=None)
def overrides_cmd(session: int | None) -> None:
    """Corrections a mechanic made to an AI-authored value."""
    sql = (
        "SELECT id, session_id, field_name, ai_value, override_value, "
        "       overridden_at FROM session_overrides"
    )
    params: tuple = ()
    if session is not None:
        sql += " WHERE session_id = ?"
        params = (session,)
    sql += " ORDER BY overridden_at DESC, id DESC LIMIT 50"

    with get_connection(None) as conn:
        rows = conn.execute(sql, params).fetchall()

    if not rows:
        click.echo("No overrides recorded.")
        return
    for r in rows:
        click.echo(f"[{r[5]}] session {r[1]} · {r[2]}")
        click.echo(f"  AI said:  {r[3]}")
        click.echo(f"  corrected to: {r[4]}")


@capture.command("analyses")
@click.option("--video", type=int, required=True)
def analyses_cmd(video: int) -> None:
    """Every sweep recorded for a video, newest first."""
    rows = list_analyses(video)
    if not rows:
        click.echo(f"No analyses recorded for video {video}.")
        return
    for r in rows:
        state = "superseded" if r["superseded_at"] else "current"
        n = len((r["findings"] or {}).get("findings") or [])
        click.echo(
            f"  #{r['id']} {state} · {n} finding(s) · "
            f"{r['analyzed_at'] or 'date unknown'} · {r['model_used'] or '?'}"
        )
