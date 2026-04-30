"""Video repository for Phase 191B — diagnostic video metadata + analysis state.

Function-based repo mirroring `session_repo.py` shape (no class-based ORM,
no SQLAlchemy — plain sqlite3 row dicts via the project-standard
`get_connection` context manager).

Design notes:

* Soft-delete via the `deleted_at` column. `get_video` and
  `list_session_videos` exclude soft-deleted rows; `soft_delete_video`
  is idempotent (a no-op if the row is already deleted, returning
  False).
* `ON DELETE CASCADE` on the FK to `diagnostic_sessions(id)` (set up in
  migration 039) cleans up videos when their owning session is deleted.
  Mobile-side orphan cleanup (Phase 191 `cleanupOrphanedVideos`) is
  unchanged and runs on the local-cache copy.
* Owner-aware variants (`*_for_owner`) JOIN against
  `diagnostic_sessions.user_id` to enforce ownership at the repo layer.
  Routes translate `None`/`False` into 404, and `VideoOwnershipError`
  into 403 (mirrors `session_repo.SessionOwnershipError`).
* Quota math splits into per-session (count + bytes) and per-tier
  monthly aggregate (200/mo for shop tier; unlimited for company; 0 for
  individual which the `require_tier('shop')` gate already 403s).

Phase 191B Commit 1 covers the data layer only. The HTTP routes that
use these helpers land in Commit 3.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from motodiag.core.database import get_connection


# ---------------------------------------------------------------------------
# Custom exceptions (mirror session_repo's pattern)
# ---------------------------------------------------------------------------


class VideoOwnershipError(ValueError):
    """Raised when a caller tries to touch a video they don't own.

    Routes translate this to HTTP 403 with a ProblemDetail envelope.
    Mirrors `session_repo.SessionOwnershipError`.
    """


class VideoQuotaExceededError(Exception):
    """Raised when uploading one more video would exceed the caller's
    per-session count, per-session bytes, or per-tier monthly aggregate
    quota. Mapped to HTTP 402 (per-session count + monthly aggregate)
    or 413 (per-session bytes; the bytes failure mode is closer to
    `Payload Too Large` semantically).
    """

    def __init__(
        self,
        current: int,
        limit: int,
        scope: str,
        unit: str = "count",
    ) -> None:
        self.current = current
        self.limit = limit
        self.scope = scope  # "session" | "monthly" | "session_bytes"
        self.unit = unit    # "count" | "bytes"
        super().__init__(
            f"video quota exceeded: {current}/{limit} {unit} ({scope})"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _row_to_dict(row) -> Optional[dict]:
    """Convert a sqlite3.Row to a plain dict, deserializing JSON fields.

    Returns None when row is None so callers can treat
    `_row_to_dict(cursor.fetchone())` as a single-shot lookup.
    """
    if row is None:
        return None
    d = dict(row)
    findings = d.get("analysis_findings")
    if findings:
        try:
            d["analysis_findings"] = json.loads(findings)
        except (json.JSONDecodeError, TypeError):
            # Malformed JSON shouldn't crash the read path — surface
            # as None so the route can return a partial response.
            d["analysis_findings"] = None
    else:
        d["analysis_findings"] = None
    # Coerce sqlite-stored bool-as-int → bool for ergonomic dict use.
    if "interrupted" in d:
        d["interrupted"] = bool(d["interrupted"])
    return d


def _month_start_iso() -> str:
    """First instant of the current UTC calendar month, as ISO string.

    Mirrors `session_repo._month_start_iso` for consistency. Used by
    the per-tier monthly aggregate quota query.
    """
    now = datetime.now(timezone.utc)
    return now.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0,
    ).isoformat()


def _now_iso() -> str:
    """Current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _update_file_path(
    video_id: int, file_path: str, db_path: Optional[str] = None,
) -> bool:
    """Update the `file_path` column for a video row; return True on success.

    Internal helper used by the upload route after writing the file to
    disk: the canonical disk path is derived from ``video_id``, so it's
    only known post-INSERT. The route inserts with a placeholder, writes
    the file, then calls this to record the real path.
    """
    path = db_path
    with get_connection(path) as conn:
        cursor = conn.execute(
            "UPDATE videos SET file_path = ? WHERE id = ?",
            (file_path, video_id),
        )
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Core CRUD
# ---------------------------------------------------------------------------


def create_video(
    session_id: int,
    file_path: str,
    sha256: str,
    started_at: str,
    duration_ms: int,
    width: int,
    height: int,
    file_size_bytes: int,
    format: str = "mp4",
    codec: str = "h264",
    interrupted: bool = False,
    db_path: Optional[str] = None,
) -> int:
    """Insert a new video row; return id.

    `analysis_state` defaults to 'pending' at the SQL layer (see
    migration 039); the BackgroundTask in the upload route picks it up
    and transitions to 'analyzing' before calling the Vision pipeline.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO videos (
                   session_id, started_at, duration_ms,
                   width, height, file_size_bytes,
                   format, codec, interrupted,
                   file_path, sha256,
                   upload_state, analysis_state
               )
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                       'uploaded', 'pending')""",
            (
                session_id, started_at, duration_ms,
                width, height, file_size_bytes,
                format, codec, 1 if interrupted else 0,
                file_path, sha256,
            ),
        )
        return int(cursor.lastrowid)


def get_video(
    video_id: int, db_path: Optional[str] = None,
) -> Optional[dict]:
    """Fetch one video by id. Returns None if not found OR soft-deleted.

    The soft-delete filter is intentional — a soft-deleted row is
    indistinguishable from a missing row to API callers (route handler
    returns 404 with ProblemDetail in either case).
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM videos WHERE id = ? AND deleted_at IS NULL",
            (video_id,),
        )
        return _row_to_dict(cursor.fetchone())


def list_session_videos(
    session_id: int, db_path: Optional[str] = None,
) -> list[dict]:
    """List all live (non-soft-deleted) videos for a session, newest first.

    Ordering: `created_at DESC, id DESC` mirrors `list_sessions` so
    rapid-fire uploads with the same `created_at` clock-second tie-break
    by insertion order.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """SELECT * FROM videos
               WHERE session_id = ? AND deleted_at IS NULL
               ORDER BY created_at DESC, id DESC""",
            (session_id,),
        )
        return [
            d for d in (_row_to_dict(r) for r in cursor.fetchall())
            if d is not None
        ]


def soft_delete_video(
    video_id: int, db_path: Optional[str] = None,
) -> bool:
    """Set `deleted_at = now()`; idempotent. Returns True if a row was
    updated (i.e., the video existed AND was not already deleted).

    The route handler returns 204 in both the True and False cases —
    soft-delete-of-an-already-deleted row is treated as a successful
    no-op (idempotent DELETE semantics per RFC 7231).
    """
    now = _now_iso()
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE videos SET deleted_at = ? "
            "WHERE id = ? AND deleted_at IS NULL",
            (now, video_id),
        )
        return cursor.rowcount > 0


def update_analysis_state(
    video_id: int,
    new_state: str,
    db_path: Optional[str] = None,
) -> bool:
    """Update `analysis_state`; returns True on success.

    `new_state` should be a `VideoAnalysisState` enum value. The string
    comparison runs at the SQL layer — invalid values are silently
    accepted but will fail the route response validator on the next
    GET (which round-trips through the Pydantic enum). Callers that
    care about validity should pass `VideoAnalysisState.X.value`.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE videos SET analysis_state = ? "
            "WHERE id = ? AND deleted_at IS NULL",
            (new_state, video_id),
        )
        return cursor.rowcount > 0


def set_analysis_findings(
    video_id: int,
    findings_dict: dict,
    model_used: Optional[str] = None,
    cost_usd: Optional[float] = None,
    db_path: Optional[str] = None,
) -> bool:
    """Persist findings + transition `analysis_state` to 'analyzed'.

    `model_used` and `cost_usd` are optional metadata that get folded
    into the JSON serialization of `findings_dict` (mutating a defensive
    copy so the caller's dict is not modified). The Phase 101
    `VisualAnalysisResult` schema is extended in v1.0.1 with
    `model_used` + `cost_estimate_usd` + `frames_analyzed` fields, but
    a plain `findings_dict` from older callers also works — the extra
    fields just won't render in the response.
    """
    payload = dict(findings_dict)
    if model_used is not None:
        payload.setdefault("model_used", model_used)
    if cost_usd is not None:
        payload.setdefault("cost_estimate_usd", cost_usd)

    now = _now_iso()
    serialized = json.dumps(payload)
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """UPDATE videos
               SET analysis_findings = ?,
                   analyzed_at = ?,
                   analysis_state = 'analyzed'
               WHERE id = ? AND deleted_at IS NULL""",
            (serialized, now, video_id),
        )
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Quota math
# ---------------------------------------------------------------------------


def count_videos_in_session(
    session_id: int, db_path: Optional[str] = None,
) -> int:
    """Count live videos in a session (excludes soft-deleted).

    Used to enforce the per-session count cap (default 10 per
    Phase 191B plan). Soft-deleted rows do NOT count — a mechanic who
    deletes-and-re-uploads should not get blocked by their own cleanup.
    """
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM videos "
            "WHERE session_id = ? AND deleted_at IS NULL",
            (session_id,),
        ).fetchone()
    return int(row["n"]) if row else 0


def count_bytes_in_session(
    session_id: int, db_path: Optional[str] = None,
) -> int:
    """SUM `file_size_bytes` across live videos in a session.

    Used to enforce the per-session size cap (default 1 GB per
    Phase 191B plan). Returns 0 (not None) when the session has no
    videos, so callers can do `if count_bytes_in_session(...) + new
    > LIMIT` without a None guard.
    """
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(file_size_bytes), 0) AS s "
            "FROM videos "
            "WHERE session_id = ? AND deleted_at IS NULL",
            (session_id,),
        ).fetchone()
    return int(row["s"]) if row else 0


def count_videos_this_month_for_owner(
    user_id: int, db_path: Optional[str] = None,
) -> int:
    """Count videos uploaded this calendar month by sessions owned by user_id.

    Per-tier monthly aggregate quota: 200/mo for shop tier; unlimited
    for company; 0 for individual (already gated by `require_tier`).
    JOINs videos against `diagnostic_sessions.user_id` since the videos
    table itself doesn't carry a denormalized owner column.

    Soft-deleted videos DO count toward the monthly aggregate — the
    Anthropic call already happened, the cost was already incurred, and
    counting deletions toward the cap discourages "delete to extend
    quota" gaming. Per-session count caps differ (they exclude
    soft-deleted) because that's a UX-quality-of-life cap, not a
    cost-control cap.
    """
    month_start = _month_start_iso()
    with get_connection(db_path) as conn:
        row = conn.execute(
            """SELECT COUNT(*) AS n
               FROM videos v
               INNER JOIN diagnostic_sessions s
                   ON v.session_id = s.id
               WHERE s.user_id = ?
                 AND v.created_at >= ?""",
            (user_id, month_start),
        ).fetchone()
    return int(row["n"]) if row else 0


# ---------------------------------------------------------------------------
# Owner-aware variants
# ---------------------------------------------------------------------------


def _assert_session_owner(
    session_id: int,
    user_id: int,
    db_path: Optional[str],
) -> Optional[dict]:
    """Return session row when owned by `user_id`; None when missing;
    raise `VideoOwnershipError` on cross-owner.

    Mirrors `session_repo._assert_owner` shape but lives in this module
    so video routes can stay close to their own ownership checks.
    """
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, user_id FROM diagnostic_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    if row is None:
        return None
    if int(row["user_id"] or 0) != user_id:
        raise VideoOwnershipError(
            f"session id={session_id} not owned by user id={user_id}"
        )
    return dict(row)


def create_video_for_owner(
    user_id: int,
    session_id: int,
    file_path: str,
    sha256: str,
    started_at: str,
    duration_ms: int,
    width: int,
    height: int,
    file_size_bytes: int,
    format: str = "mp4",
    codec: str = "h264",
    interrupted: bool = False,
    db_path: Optional[str] = None,
) -> Optional[int]:
    """Same as `create_video` + verifies session is owned by `user_id`.

    Returns the new video id on success; None if the session does not
    exist (route → 404). Raises `VideoOwnershipError` if the session
    exists but is owned by a different user (route → 403).

    Quota checks are NOT done here — the caller (the upload route)
    runs them explicitly so the right error code (402 vs 413) can be
    surfaced based on which cap was hit.
    """
    guard = _assert_session_owner(session_id, user_id, db_path)
    if guard is None:
        return None
    return create_video(
        session_id=session_id,
        file_path=file_path,
        sha256=sha256,
        started_at=started_at,
        duration_ms=duration_ms,
        width=width,
        height=height,
        file_size_bytes=file_size_bytes,
        format=format,
        codec=codec,
        interrupted=interrupted,
        db_path=db_path,
    )


def get_video_for_owner(
    user_id: int,
    video_id: int,
    db_path: Optional[str] = None,
) -> Optional[dict]:
    """Same as `get_video` + ownership check via the owning session.

    Returns None when the video doesn't exist OR is soft-deleted OR
    belongs to a session owned by a different user — all three are
    indistinguishable to the caller (route → 404). This is a
    deliberate information-leak guard.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """SELECT v.* FROM videos v
               INNER JOIN diagnostic_sessions s
                   ON v.session_id = s.id
               WHERE v.id = ?
                 AND v.deleted_at IS NULL
                 AND s.user_id = ?""",
            (video_id, user_id),
        )
        return _row_to_dict(cursor.fetchone())


def list_session_videos_for_owner(
    user_id: int,
    session_id: int,
    db_path: Optional[str] = None,
) -> Optional[list[dict]]:
    """Same as `list_session_videos` + ownership check on the session.

    Returns None when the session does not exist (route → 404); raises
    `VideoOwnershipError` on cross-owner (route → 403); otherwise
    returns the list (which may be empty).
    """
    guard = _assert_session_owner(session_id, user_id, db_path)
    if guard is None:
        return None
    return list_session_videos(session_id, db_path=db_path)


def soft_delete_video_for_owner(
    user_id: int,
    video_id: int,
    db_path: Optional[str] = None,
) -> bool:
    """Same as `soft_delete_video` + ownership check via the owning session.

    Returns True on a successful soft-delete; False when the video
    doesn't exist OR is already soft-deleted OR belongs to a different
    user (route → 204 idempotent in all three cases since DELETE is
    idempotent per HTTP semantics).
    """
    # Look up the owning session via a JOIN so cross-user attempts can't
    # even discover the video's existence.
    with get_connection(db_path) as conn:
        row = conn.execute(
            """SELECT v.id FROM videos v
               INNER JOIN diagnostic_sessions s
                   ON v.session_id = s.id
               WHERE v.id = ?
                 AND v.deleted_at IS NULL
                 AND s.user_id = ?""",
            (video_id, user_id),
        ).fetchone()
    if row is None:
        return False
    return soft_delete_video(video_id, db_path=db_path)
