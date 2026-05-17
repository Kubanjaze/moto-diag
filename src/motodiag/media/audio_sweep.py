"""60-day audio retention sweep — Phase 195 (Commit 0) Section 5.

Pure function `prune_old_audio(now, retention_days, db_path)` walks
``voice_transcripts`` rows older than the retention threshold whose
audio files haven't been pruned yet, unlinks the files, and stamps
``audio_deleted_at`` so subsequent calls are idempotent. Transcripts +
extracted_symptoms remain in place — only the audio bytes are pruned.

Same shape as Phase 192B's share-temp sweep + Phase 194's
``cleanupOldPhotos`` mobile-side discipline:
- Exact-threshold cases tested (60-day boundary; 60 days minus 1
  second; 60 days plus 1 second).
- Missing-file no-op (file already swept by an earlier run, by an
  operator, or by a backup-restore mismatch).
- Sweep-failure recovery (per-row try/except; one bad row doesn't
  abort the whole sweep; errors collected for caller observability).

CLI entry point: ``motodiag transcripts sweep`` (manual trigger;
cron/scheduler integration is a Phase 195B concern).

Risk #8 cost-monitoring substrate: every prune logs at INFO with
duration / file-size-bytes for grep-pattern observability. Phase 195B
will aggregate these into a dashboard.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from motodiag.core.database import get_connection


_log = logging.getLogger(__name__)


# Default retention per Phase 195 v1.0 Section 5 lock.
DEFAULT_RETENTION_DAYS = 60


@dataclass(frozen=True)
class SweepResult:
    """Per-call sweep telemetry. Returned to callers (CLI, future cron,
    test assertions) for observability."""
    pruned_count: int
    total_bytes_freed: int
    errors: list[str]


def prune_old_audio(
    now: datetime,
    *,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    db_path: Optional[str] = None,
) -> SweepResult:
    """Prune audio bytes older than ``retention_days``.

    Idempotent — rows whose ``audio_deleted_at`` is already set are
    skipped. Test-deterministic by accepting an explicit ``now``
    timestamp.

    Returns a ``SweepResult`` with counts + any per-row errors so the
    caller can log / surface / fail-loud.
    """
    cutoff = now - timedelta(days=retention_days)
    cutoff_iso = cutoff.strftime("%Y-%m-%d %H:%M:%S")

    pruned_count = 0
    total_bytes_freed = 0
    errors: list[str] = []

    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT id, audio_path, audio_size_bytes
               FROM voice_transcripts
               WHERE created_at < ?
                 AND audio_deleted_at IS NULL
                 AND deleted_at IS NULL""",
            (cutoff_iso,),
        ).fetchall()

    now_iso = now.astimezone(timezone.utc).isoformat()

    for row in rows:
        transcript_id = int(row[0])
        audio_path = str(row[1])
        size_bytes = int(row[2])
        try:
            path = Path(audio_path)
            if path.exists():
                path.unlink()
            else:
                # Missing file is fine — log + continue stamping
                # audio_deleted_at so we don't keep retrying.
                _log.info(
                    "audio_sweep: file already absent at prune time "
                    "transcript_id=%d path=%s",
                    transcript_id, audio_path,
                )

            with get_connection(db_path) as conn:
                conn.execute(
                    "UPDATE voice_transcripts "
                    "SET audio_deleted_at = ?, updated_at = ? "
                    "WHERE id = ?",
                    (now_iso, now_iso, transcript_id),
                )

            pruned_count += 1
            total_bytes_freed += size_bytes
            _log.info(
                "audio_sweep: pruned transcript_id=%d size_bytes=%d",
                transcript_id, size_bytes,
            )
        except OSError as exc:
            err = (
                f"audio_sweep: failed to prune transcript_id="
                f"{transcript_id} path={audio_path}: {exc!s}"
            )
            _log.warning(err)
            errors.append(err)

    return SweepResult(
        pruned_count=pruned_count,
        total_bytes_freed=total_bytes_freed,
        errors=errors,
    )
