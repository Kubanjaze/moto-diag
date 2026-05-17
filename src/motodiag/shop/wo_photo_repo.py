"""Work-order photo repository — Phase 194 (Commit 0) substrate.

Function-based repo mirroring ``video_repo.py`` shape (no class-based ORM,
no SQLAlchemy — plain sqlite3 row dicts via the project-standard
``get_connection`` context manager).

Design notes:

* Soft-delete via the ``deleted_at`` column. ``get_wo_photo`` and the list
  helpers exclude soft-deleted rows; ``soft_delete_wo_photo`` is idempotent
  (a no-op if the row is already deleted, returning False).
* ``ON DELETE CASCADE`` on the FK to ``work_orders(id)`` (set up in
  migration 041) cleans up photos when their owning WO is deleted.
  ``ON DELETE SET NULL`` for ``issue_id`` keeps the photo at WO scope
  if the issue is deleted; ``ON DELETE SET NULL`` for ``pair_id`` lets
  the orphan side of a pair stand on its own.
* Owner-aware variants don't exist at the repo layer — Phase 193's
  shop-management routes use ``require_shop_access`` (basic membership
  check via ``get_shop_member``) and verify ``work_orders.shop_id``
  matches the URL ``shop_id`` parameter. Photo-route auth follows the
  same posture and checks ownership at the route layer.
* Quota math splits into per-WO count, per-issue count, and per-tier
  monthly aggregate. Substrate-anticipates-feature (Phase 194B):
  ``analysis_state`` + ``analysis_findings`` columns are present but
  Phase 194 never writes them.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from motodiag.core.database import get_connection


# ---------------------------------------------------------------------------
# Custom exceptions (mirror video_repo's pattern)
# ---------------------------------------------------------------------------


class WorkOrderPhotoOwnershipError(ValueError):
    """Raised when a caller tries to touch a photo they don't own.

    Routes translate this to HTTP 403/404 with a ProblemDetail envelope.
    Mirrors ``video_repo.VideoOwnershipError``.
    """


class WorkOrderPhotoQuotaExceededError(Exception):
    """Raised when uploading one more photo would exceed a quota.

    Mapped to HTTP 402 (per-WO count, per-issue count, monthly aggregate).
    Mirrors ``video_repo.VideoQuotaExceededError`` shape.
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
        self.scope = scope  # "wo" | "issue" | "monthly"
        self.unit = unit    # "count"
        super().__init__(
            f"work-order photo quota exceeded: "
            f"{current}/{limit} {unit} ({scope})"
        )


class WorkOrderPhotoPairingError(ValueError):
    """Raised when ``update_pairing`` references a non-existent partner.

    Routes translate to 422. Distinct from ``WorkOrderPhotoOwnershipError``
    because it's a payload-shape problem (pair_id targets a deleted /
    non-existent row), not an auth problem.
    """


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _row_to_dict(row) -> Optional[dict]:
    """Convert a sqlite3.Row to a plain dict, deserializing JSON fields."""
    if row is None:
        return None
    d = dict(row)
    findings = d.get("analysis_findings")
    if findings:
        try:
            d["analysis_findings"] = json.loads(findings)
        except (json.JSONDecodeError, TypeError):
            d["analysis_findings"] = None
    else:
        d["analysis_findings"] = None
    return d


def _month_start_iso() -> str:
    """First instant of the current UTC calendar month.

    Format MUST match SQLite's ``datetime('now')`` output for lex
    comparison to work in WHERE clauses (space-separated, no microseconds,
    no timezone suffix — ``'2026-05-01 00:00:00'``). Same fix applied to
    ``video_repo._month_start_iso`` and ``session_repo._month_start_iso``
    after the 2026-05-01 boundary-day quota bug.
    """
    now = datetime.now(timezone.utc)
    return now.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0,
    ).strftime("%Y-%m-%d %H:%M:%S")


def _now_iso() -> str:
    """Current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _update_file_path(
    photo_id: int, file_path: str, db_path: Optional[str] = None,
) -> bool:
    """Update the ``file_path`` column for a photo row; return True on success.

    Internal helper used by the upload route after writing the file to
    disk: the canonical disk path is derived from ``photo_id``, so it's
    only known post-INSERT. Mirrors ``video_repo._update_file_path``.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE work_order_photos SET file_path = ?, "
            "updated_at = ? WHERE id = ?",
            (file_path, _now_iso(), photo_id),
        )
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Core CRUD
# ---------------------------------------------------------------------------


def create_wo_photo(
    work_order_id: int,
    file_path: str,
    file_size_bytes: int,
    width: int,
    height: int,
    sha256: str,
    captured_at: str,
    uploaded_by_user_id: int,
    role: str = "general",
    issue_id: Optional[int] = None,
    pair_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> int:
    """Insert a new ``work_order_photos`` row; return id.

    ``role`` defaults to 'general' at the SQL layer (CHECK constraint
    in migration 041 enforces the enum). ``issue_id`` and ``pair_id``
    are nullable; the route layer is responsible for verifying that
    ``issue_id`` belongs to the same WO and ``pair_id`` (if set)
    references a live photo on the same WO.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO work_order_photos (
                   work_order_id, issue_id, role, pair_id,
                   file_path, file_size_bytes, width, height,
                   sha256, captured_at, uploaded_by_user_id
               )
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                work_order_id, issue_id, role, pair_id,
                file_path, file_size_bytes, width, height,
                sha256, captured_at, uploaded_by_user_id,
            ),
        )
        return int(cursor.lastrowid)


def get_wo_photo(
    photo_id: int, db_path: Optional[str] = None,
) -> Optional[dict]:
    """Fetch one photo by id. Returns None if not found OR soft-deleted."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM work_order_photos "
            "WHERE id = ? AND deleted_at IS NULL",
            (photo_id,),
        )
        return _row_to_dict(cursor.fetchone())


def list_wo_photos(
    work_order_id: int, db_path: Optional[str] = None,
) -> list[dict]:
    """List all live photos for a WO, newest first.

    Ordering: ``captured_at DESC, id DESC`` so rapid-fire uploads with
    the same captured_at clock-second tie-break by insertion order.
    The mobile renderer regroups into pairs + standalones + undecided
    buckets — the repo returns flat newest-first.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """SELECT * FROM work_order_photos
               WHERE work_order_id = ? AND deleted_at IS NULL
               ORDER BY captured_at DESC, id DESC""",
            (work_order_id,),
        )
        return [
            d for d in (_row_to_dict(r) for r in cursor.fetchall())
            if d is not None
        ]


def list_issue_photos(
    issue_id: int, db_path: Optional[str] = None,
) -> list[dict]:
    """List all live photos attached to an issue, newest first."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """SELECT * FROM work_order_photos
               WHERE issue_id = ? AND deleted_at IS NULL
               ORDER BY captured_at DESC, id DESC""",
            (issue_id,),
        )
        return [
            d for d in (_row_to_dict(r) for r in cursor.fetchall())
            if d is not None
        ]


def update_pairing(
    photo_id: int,
    pair_id: Optional[int],
    role: Optional[str] = None,
    issue_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> bool:
    """Update pairing + role + issue_id on a single photo; return True on success.

    Used by the post-capture re-classification surface. ``pair_id=None``
    explicitly unpairs (sets to NULL). ``role`` updates the role enum;
    ``issue_id`` updates issue attribution. All three are optional —
    pass only the fields the caller wants to change.

    The caller MUST verify ``pair_id`` (when not None) references a
    live photo on the same WO before invoking this. Pairing failures
    are surfaced via ``WorkOrderPhotoPairingError`` at the route layer
    (the SQL FK only catches non-existent rows, not WO-scope mismatch).
    """
    sets = ["pair_id = ?", "updated_at = ?"]
    params: list = [pair_id, _now_iso()]
    if role is not None:
        sets.append("role = ?")
        params.append(role)
    if issue_id is not None:
        # Phase 194 only ever PROMOTES from undecided → typed; never
        # clears issue_id. If clearing is needed in a future phase,
        # use a sentinel (issue_id=0 or a separate clear-issue helper).
        sets.append("issue_id = ?")
        params.append(issue_id)
    params.append(photo_id)
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE work_order_photos SET {', '.join(sets)} "
            f"WHERE id = ? AND deleted_at IS NULL",
            tuple(params),
        )
        return cursor.rowcount > 0


def soft_delete_wo_photo(
    photo_id: int, db_path: Optional[str] = None,
) -> bool:
    """Set ``deleted_at = now()``; idempotent. Returns True if a row was updated.

    The route handler returns 204 in both True and False cases —
    soft-delete-of-an-already-deleted row is treated as a successful
    no-op (idempotent DELETE semantics per RFC 7231).

    Photos that referenced this one as ``pair_id`` will see their
    ``pair_id`` SET NULL via the FK constraint (migration 041).
    """
    now = _now_iso()
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE work_order_photos SET deleted_at = ?, "
            "updated_at = ? "
            "WHERE id = ? AND deleted_at IS NULL",
            (now, now, photo_id),
        )
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Quota helpers
# ---------------------------------------------------------------------------


def count_wo_photos(
    work_order_id: int, db_path: Optional[str] = None,
) -> int:
    """Count live (non-soft-deleted) photos on a WO."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM work_order_photos "
            "WHERE work_order_id = ? AND deleted_at IS NULL",
            (work_order_id,),
        )
        row = cursor.fetchone()
        return int(row[0]) if row else 0


def count_issue_photos(
    issue_id: int, db_path: Optional[str] = None,
) -> int:
    """Count live photos attached to an issue."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM work_order_photos "
            "WHERE issue_id = ? AND deleted_at IS NULL",
            (issue_id,),
        )
        row = cursor.fetchone()
        return int(row[0]) if row else 0


def count_wo_photos_this_month_for_uploader(
    uploaded_by_user_id: int, db_path: Optional[str] = None,
) -> int:
    """Count photos this user has uploaded so far this calendar month.

    Used for per-tier monthly aggregate enforcement (shop=500/mo,
    company=unlimited; mirrors video monthly quota shape but tighter
    since photos are smaller per-unit but uploaded more frequently).
    """
    month_start = _month_start_iso()
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM work_order_photos "
            "WHERE uploaded_by_user_id = ? "
            "AND created_at >= ? "
            "AND deleted_at IS NULL",
            (uploaded_by_user_id, month_start),
        )
        row = cursor.fetchone()
        return int(row[0]) if row else 0


def get_wo_photo_for_pairing(
    photo_id: int,
    expected_wo_id: int,
    db_path: Optional[str] = None,
) -> Optional[dict]:
    """Fetch a photo IFF it lives on ``expected_wo_id`` and isn't deleted.

    Used by the route layer to validate ``pair_id`` payloads before
    inserting / updating: the partner must exist, be live, AND be
    attached to the same WO. Returns the row dict on success; None on
    any mismatch (the route surfaces as ``WorkOrderPhotoPairingError``).
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM work_order_photos "
            "WHERE id = ? AND work_order_id = ? AND deleted_at IS NULL",
            (photo_id, expected_wo_id),
        )
        return _row_to_dict(cursor.fetchone())
