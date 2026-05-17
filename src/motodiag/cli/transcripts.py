"""CLI entrypoint: ``motodiag transcripts`` — voice transcript admin.

Phase 195 (Commit 0) ships one subcommand: ``motodiag transcripts sweep``
runs the 60-day audio retention sweep manually. Phase 195B can add
cron / scheduler integration; Phase 195 keeps the trigger explicit so
operators can run it from a manual-task runner of their choice.

Usage:
    motodiag transcripts sweep
    motodiag transcripts sweep --retention-days 30
    motodiag transcripts sweep --dry-run

The sweep is idempotent — second run is a no-op. Per-row failures
(disk error, file-already-gone) don't abort the sweep; they collect
into the result errors list which is summarized at exit.
"""

from __future__ import annotations

from datetime import datetime, timezone

import click

from motodiag.media.audio_sweep import (
    DEFAULT_RETENTION_DAYS,
    prune_old_audio,
)


def register_transcripts(cli: click.Group) -> None:
    """Register the ``transcripts`` subgroup on the root CLI."""
    cli.add_command(transcripts)


@click.group()
def transcripts() -> None:
    """Voice transcript admin commands (Phase 195+)."""


@transcripts.command("sweep")
@click.option(
    "--retention-days",
    type=int,
    default=DEFAULT_RETENTION_DAYS,
    show_default=True,
    help="Audio bytes older than this many days are pruned. "
    "Transcripts + extracted_symptoms remain.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Report what would be pruned without unlinking any files.",
)
def transcripts_sweep(retention_days: int, dry_run: bool) -> None:
    """Run the 60-day audio retention sweep.

    Prunes the audio bytes from voice_transcripts rows older than
    ``--retention-days``. Transcripts + extracted_symptoms remain.
    """
    if dry_run:
        click.echo(
            f"[dry-run] would sweep audio bytes older than "
            f"{retention_days} days (no files touched)",
        )
        return

    now = datetime.now(timezone.utc)
    result = prune_old_audio(now, retention_days=retention_days)

    click.echo(
        f"audio sweep complete: pruned={result.pruned_count} "
        f"freed={result.total_bytes_freed} bytes",
    )
    if result.errors:
        click.echo(f"  {len(result.errors)} error(s):")
        for err in result.errors:
            click.echo(f"    - {err}")
