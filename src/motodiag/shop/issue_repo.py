"""Structured issue logging + categorization repository.

Phase 162. Promotes Phase 161 ``work_orders.reported_problems`` freetext
into a first-class structured list. Each issue attaches to a work order
via ``work_order_id`` FK CASCADE, carries title + description +
12-category taxonomy + 4-tier severity + guarded status lifecycle, and
optionally cross-references a DTC code + symptom + diagnostic session.

12-category taxonomy
--------------------

Override per the Domain-Researcher brief: existing 7 SymptomCategory
values misfile ~40-50% of real shop tickets to "other." Phase 162 ships
with 12 categories — original 7 (engine/fuel_system/electrical/cooling/
exhaust/transmission/other) PLUS new brakes, suspension, drivetrain,
tires_wheels, accessories, rider_complaint. Covers ~95% of real shop
tickets per HD Forums + ADVrider + r/MotoMechanic synthesis.

Status lifecycle (guarded)
--------------------------

    open → resolved | duplicate | wont_fix → (reopen) → open

Only the dedicated transition functions (``resolve_issue``,
``mark_duplicate_issue``, ``mark_wontfix_issue``, ``reopen_issue``)
can mutate ``status``, ``resolved_at``, ``resolution_notes``, and
``duplicate_of_issue_id``. The generic :func:`update_issue` whitelist
excludes all four. Same canonical pattern as Phases 160 (intake) and
161 (work_orders).

Soft vs hard FK validation
--------------------------

- ``linked_dtc_code`` is TEXT, not FK — survives ``dtc_codes`` seed
  reloads. Soft-validated (``logging.warning`` on miss; persist anyway)
  so issue log stays populated on fresh shop installs.
- ``linked_symptom_id`` is hard FK with SET NULL — symptoms table is
  shop-lifetime stable; SET NULL covers rare hard-deletes.
- ``duplicate_of_issue_id`` is self-referencing FK with SET NULL on
  canonical delete. Self-reference rejected at repo layer.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from typing import Optional

from motodiag.core.database import get_connection


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class IssueNotFoundError(ValueError):
    """Raised when an issue id does not resolve."""


class InvalidIssueTransition(ValueError):
    """Raised when a lifecycle transition is illegal given current status."""


class IssueFKError(ValueError):
    """Raised when an FK violation surfaces during create/update."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


ISSUE_CATEGORIES: tuple[str, ...] = (
    "engine", "fuel_system", "electrical", "cooling",
    "exhaust", "transmission", "brakes", "suspension",
    "drivetrain", "tires_wheels", "accessories", "rider_complaint",
    "other",
)


ISSUE_SEVERITIES: tuple[str, ...] = ("low", "medium", "high", "critical")


SEVERITY_RANK: dict[str, int] = {
    "low": 1, "medium": 2, "high": 3, "critical": 4,
}


ISSUE_STATUSES: tuple[str, ...] = (
    "open", "resolved", "duplicate", "wont_fix",
)


TERMINAL_ISSUE_STATUSES: frozenset[str] = frozenset({
    "resolved", "duplicate", "wont_fix",
})


_VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    "open":      frozenset({"resolved", "duplicate", "wont_fix"}),
    "resolved":  frozenset({"open"}),
    "duplicate": frozenset({"open"}),
    "wont_fix":  frozenset({"open"}),
}


# Whitelist for ``update_issue``. Status + resolved_at + resolution_notes +
# duplicate_of_issue_id are owned by the lifecycle functions.
_UPDATABLE_FIELDS: frozenset[str] = frozenset({
    "title",
    "description",
    "category",
    "severity",
    "linked_dtc_code",
    "linked_symptom_id",
    "diagnostic_session_id",
})


# Crosswalk for Phase 163 AI categorization to map SymptomCategory →
# shop ISSUE_CATEGORIES. Single authoritative source for the mapping.
SYMPTOM_CATEGORY_TO_ISSUE_CATEGORY: dict[str, str] = {
    "engine": "engine",
    "fuel": "fuel_system",
    "fuel_system": "fuel_system",
    "electrical": "electrical",
    "cooling": "cooling",
    "exhaust": "exhaust",
    "transmission": "transmission",
    "drivetrain": "drivetrain",
    "brakes": "brakes",
    "suspension": "suspension",
    "tires_wheels": "tires_wheels",
    "accessories": "accessories",
    "starting": "electrical",
    "idle": "engine",
    "noise": "rider_complaint",
    "vibration": "rider_complaint",
    "other": "other",
}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _validate_category(category: str) -> str:
    if category not in ISSUE_CATEGORIES:
        raise ValueError(
            f"category must be one of {ISSUE_CATEGORIES} (got {category!r})"
        )
    return category


def _validate_severity(severity: str) -> str:
    if severity not in ISSUE_SEVERITIES:
        raise ValueError(
            f"severity must be one of {ISSUE_SEVERITIES} (got {severity!r})"
        )
    return severity


def _require_row(
    conn: sqlite3.Connection, table: str, row_id: int, label: str,
) -> dict:
    row = conn.execute(
        f"SELECT * FROM {table} WHERE id = ?", (row_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"{label} not found: id={row_id}")
    return dict(row)


def _soft_validate_dtc_code(
    conn: sqlite3.Connection, code: Optional[str],
) -> None:
    if not code:
        return
    row = conn.execute(
        "SELECT 1 FROM dtc_codes WHERE code = ? LIMIT 1", (code,),
    ).fetchone()
    if row is None:
        logger.warning(
            "linked_dtc_code %r not found in dtc_codes (persisting anyway)",
            code,
        )


def _assert_transition(
    from_status: str, to_status: str, issue_id: int,
) -> None:
    if to_status not in _VALID_TRANSITIONS.get(from_status, frozenset()):
        raise InvalidIssueTransition(
            f"issue id={issue_id} cannot transition "
            f"{from_status!r} → {to_status!r}. "
            f"Legal from {from_status!r}: "
            f"{sorted(_VALID_TRANSITIONS.get(from_status, []))}"
        )


# ---------------------------------------------------------------------------
# Create + read
# ---------------------------------------------------------------------------


def create_issue(
    work_order_id: int,
    title: str,
    description: Optional[str] = None,
    category: str = "other",
    severity: str = "medium",
    linked_dtc_code: Optional[str] = None,
    linked_symptom_id: Optional[int] = None,
    diagnostic_session_id: Optional[int] = None,
    reported_by_user_id: int = 1,
    reported_at: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    """Create an issue. Returns the new id.

    Pre-checks: work_order exists (ValueError); category in
    ISSUE_CATEGORIES (ValueError); severity in ISSUE_SEVERITIES
    (ValueError); linked_symptom_id exists if supplied (ValueError);
    diagnostic_session_id exists if supplied (ValueError).
    linked_dtc_code is soft-validated (warn-only).

    Starts in status='open' with resolved_at NULL.
    """
    if not title or not str(title).strip():
        raise ValueError("title must not be empty")
    category = _validate_category(category)
    severity = _validate_severity(severity)

    with get_connection(db_path) as conn:
        _require_row(conn, "work_orders", work_order_id, "work order")
        if linked_symptom_id is not None:
            _require_row(conn, "symptoms", linked_symptom_id, "symptom")
        if diagnostic_session_id is not None:
            _require_row(
                conn, "diagnostic_sessions",
                diagnostic_session_id, "diagnostic session",
            )
        _soft_validate_dtc_code(conn, linked_dtc_code)

        columns = [
            "work_order_id", "title", "description",
            "category", "severity",
            "reported_by_user_id",
            "diagnostic_session_id", "linked_dtc_code",
            "linked_symptom_id",
        ]
        values: list = [
            work_order_id, str(title).strip(), description,
            category, severity,
            reported_by_user_id,
            diagnostic_session_id, linked_dtc_code,
            linked_symptom_id,
        ]
        if reported_at is not None:
            columns.append("reported_at")
            values.append(str(reported_at))

        placeholders = ", ".join("?" for _ in columns)
        column_list = ", ".join(columns)
        try:
            cursor = conn.execute(
                f"INSERT INTO issues ({column_list}) "
                f"VALUES ({placeholders})",
                values,
            )
        except sqlite3.IntegrityError as e:
            raise IssueFKError(f"FK violation creating issue: {e}") from e
        return int(cursor.lastrowid)


def get_issue(
    issue_id: int, db_path: Optional[str] = None,
) -> Optional[dict]:
    """Fetch one issue with denormalized display fields.

    JOINs work_orders + shops + customers + vehicles + (optional)
    symptoms + (optional) dtc_codes + (optional) duplicate_of issue.
    Returns None on miss.
    """
    query = """
        SELECT i.*,
               wo.title AS work_order_title,
               wo.shop_id AS shop_id,
               wo.vehicle_id AS vehicle_id,
               wo.customer_id AS customer_id,
               s.name AS shop_name,
               c.name AS customer_name,
               v.make AS vehicle_make,
               v.model AS vehicle_model,
               v.year AS vehicle_year,
               sym.name AS linked_symptom_name,
               dt.description AS linked_dtc_description,
               dup.title AS duplicate_of_title
        FROM issues i
        LEFT JOIN work_orders wo ON wo.id = i.work_order_id
        LEFT JOIN shops s ON s.id = wo.shop_id
        LEFT JOIN customers c ON c.id = wo.customer_id
        LEFT JOIN vehicles v ON v.id = wo.vehicle_id
        LEFT JOIN symptoms sym ON sym.id = i.linked_symptom_id
        LEFT JOIN dtc_codes dt ON dt.code = i.linked_dtc_code
        LEFT JOIN issues dup ON dup.id = i.duplicate_of_issue_id
        WHERE i.id = ?
    """
    with get_connection(db_path) as conn:
        row = conn.execute(query, (issue_id,)).fetchone()
        return dict(row) if row else None


def require_issue(
    issue_id: int, db_path: Optional[str] = None,
) -> dict:
    """:func:`get_issue` that raises :class:`IssueNotFoundError`."""
    row = get_issue(issue_id, db_path=db_path)
    if row is None:
        raise IssueNotFoundError(f"issue not found: id={issue_id}")
    return row


def list_issues(
    work_order_id: Optional[int] = None,
    category: Optional[str | list[str]] = None,
    severity: Optional[str | list[str]] = None,
    status: Optional[str | list[str]] = None,
    shop_id: Optional[int] = None,
    vehicle_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    since: Optional[str] = None,
    include_terminal: bool = False,
    limit: int = 100,
    db_path: Optional[str] = None,
) -> list[dict]:
    """List issues with composable filters.

    Sort: severity DESC (critical first), reported_at DESC, id DESC.
    Default excludes terminal statuses unless ``include_terminal=True``
    or ``status='all'``.
    """
    # Normalize status arg
    status_list: Optional[list[str]] = None
    if isinstance(status, str):
        if status.lower() == "all":
            include_terminal = True
        else:
            if status not in ISSUE_STATUSES:
                raise ValueError(
                    f"status must be one of {ISSUE_STATUSES} or 'all' "
                    f"(got {status!r})"
                )
            status_list = [status]
    elif isinstance(status, (list, tuple)):
        for s in status:
            if s not in ISSUE_STATUSES:
                raise ValueError(
                    f"status entry {s!r} not in {ISSUE_STATUSES}"
                )
        status_list = list(status)

    if status_list is None and not include_terminal:
        status_list = [
            s for s in ISSUE_STATUSES if s not in TERMINAL_ISSUE_STATUSES
        ]

    cat_list: Optional[list[str]] = None
    if isinstance(category, str):
        cat_list = [_validate_category(category)]
    elif isinstance(category, (list, tuple)):
        cat_list = [_validate_category(c) for c in category]

    sev_list: Optional[list[str]] = None
    if isinstance(severity, str):
        sev_list = [_validate_severity(severity)]
    elif isinstance(severity, (list, tuple)):
        sev_list = [_validate_severity(s) for s in severity]

    cutoff: Optional[str] = None
    if since is not None:
        from motodiag.shop.intake_repo import _since_cutoff
        cutoff = _since_cutoff(since)

    query = """
        SELECT i.*,
               wo.title AS work_order_title,
               wo.shop_id AS shop_id,
               wo.vehicle_id AS vehicle_id,
               wo.customer_id AS customer_id,
               s.name AS shop_name,
               c.name AS customer_name,
               v.make AS vehicle_make,
               v.model AS vehicle_model,
               v.year AS vehicle_year
        FROM issues i
        LEFT JOIN work_orders wo ON wo.id = i.work_order_id
        LEFT JOIN shops s ON s.id = wo.shop_id
        LEFT JOIN customers c ON c.id = wo.customer_id
        LEFT JOIN vehicles v ON v.id = wo.vehicle_id
    """
    conditions: list[str] = []
    params: list = []
    if work_order_id is not None:
        conditions.append("i.work_order_id = ?")
        params.append(work_order_id)
    if shop_id is not None:
        conditions.append("wo.shop_id = ?")
        params.append(shop_id)
    if vehicle_id is not None:
        conditions.append("wo.vehicle_id = ?")
        params.append(vehicle_id)
    if customer_id is not None:
        conditions.append("wo.customer_id = ?")
        params.append(customer_id)
    if cat_list:
        placeholders = ",".join("?" for _ in cat_list)
        conditions.append(f"i.category IN ({placeholders})")
        params.extend(cat_list)
    if sev_list:
        placeholders = ",".join("?" for _ in sev_list)
        conditions.append(f"i.severity IN ({placeholders})")
        params.extend(sev_list)
    if status_list:
        placeholders = ",".join("?" for _ in status_list)
        conditions.append(f"i.status IN ({placeholders})")
        params.extend(status_list)
    if cutoff is not None:
        conditions.append("i.reported_at >= ?")
        params.append(cutoff)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += (
        " ORDER BY CASE i.severity "
        "WHEN 'critical' THEN 4 WHEN 'high' THEN 3 "
        "WHEN 'medium' THEN 2 WHEN 'low' THEN 1 ELSE 0 END DESC, "
        "i.reported_at DESC, i.id DESC"
    )
    if limit and limit > 0:
        query += " LIMIT ?"
        params.append(int(limit))

    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def count_issues(
    work_order_id: Optional[int] = None,
    shop_id: Optional[int] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    """Count issues matching filters."""
    if status is not None and status not in ISSUE_STATUSES:
        raise ValueError(
            f"status must be one of {ISSUE_STATUSES} or None "
            f"(got {status!r})"
        )
    if category is not None:
        _validate_category(category)
    if severity is not None:
        _validate_severity(severity)

    query = (
        "SELECT COUNT(*) AS n FROM issues i "
        "LEFT JOIN work_orders wo ON wo.id = i.work_order_id"
    )
    conditions: list[str] = []
    params: list = []
    if work_order_id is not None:
        conditions.append("i.work_order_id = ?")
        params.append(work_order_id)
    if shop_id is not None:
        conditions.append("wo.shop_id = ?")
        params.append(shop_id)
    if status is not None:
        conditions.append("i.status = ?")
        params.append(status)
    if category is not None:
        conditions.append("i.category = ?")
        params.append(category)
    if severity is not None:
        conditions.append("i.severity = ?")
        params.append(severity)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    with get_connection(db_path) as conn:
        row = conn.execute(query, params).fetchone()
        return int(row["n"]) if row else 0


# ---------------------------------------------------------------------------
# Update (whitelist)
# ---------------------------------------------------------------------------


def update_issue(
    issue_id: int,
    updates: dict,
    db_path: Optional[str] = None,
) -> bool:
    """Update whitelisted fields. Cannot mutate status/resolved_at/
    resolution_notes/duplicate_of_issue_id (lifecycle-owned).

    Raises :class:`IssueNotFoundError` if missing.
    """
    if not isinstance(updates, dict):
        raise TypeError(f"updates must be a dict, got {type(updates).__name__}")
    filtered = {k: v for k, v in updates.items() if k in _UPDATABLE_FIELDS}
    if not filtered:
        return False

    if "category" in filtered:
        filtered["category"] = _validate_category(filtered["category"])
    if "severity" in filtered:
        filtered["severity"] = _validate_severity(filtered["severity"])
    if "title" in filtered:
        new_title = str(filtered["title"]).strip()
        if not new_title:
            raise ValueError("title must not be empty")
        filtered["title"] = new_title

    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM issues WHERE id = ?", (issue_id,),
        ).fetchone()
        if row is None:
            raise IssueNotFoundError(f"issue not found: id={issue_id}")

        if "linked_symptom_id" in filtered and filtered[
            "linked_symptom_id"
        ] is not None:
            _require_row(
                conn, "symptoms",
                filtered["linked_symptom_id"], "symptom",
            )
        if "diagnostic_session_id" in filtered and filtered[
            "diagnostic_session_id"
        ] is not None:
            _require_row(
                conn, "diagnostic_sessions",
                filtered["diagnostic_session_id"], "diagnostic session",
            )
        if "linked_dtc_code" in filtered:
            _soft_validate_dtc_code(conn, filtered["linked_dtc_code"])

        set_clauses = ", ".join(f"{k} = ?" for k in filtered.keys())
        params: list = list(filtered.values())
        params.append(datetime.now().isoformat())
        params.append(issue_id)
        cursor = conn.execute(
            f"UPDATE issues SET {set_clauses}, updated_at = ? "
            "WHERE id = ?",
            params,
        )
        return cursor.rowcount > 0


def categorize_issue(
    issue_id: int,
    category: str,
    severity: Optional[str] = None,
    db_path: Optional[str] = None,
) -> bool:
    """Convenience wrapper around update_issue for re-triage flow."""
    updates = {"category": category}
    if severity is not None:
        updates["severity"] = severity
    return update_issue(issue_id, updates, db_path=db_path)


def link_dtc(
    issue_id: int, dtc_code: str, db_path: Optional[str] = None,
) -> bool:
    """Set linked_dtc_code (soft-validate; persist on miss with warning)."""
    return update_issue(
        issue_id, {"linked_dtc_code": dtc_code}, db_path=db_path,
    )


def link_symptom(
    issue_id: int, symptom_id: int, db_path: Optional[str] = None,
) -> bool:
    """Set linked_symptom_id (hard-fail on missing symptom)."""
    return update_issue(
        issue_id, {"linked_symptom_id": symptom_id}, db_path=db_path,
    )


# ---------------------------------------------------------------------------
# Lifecycle transitions
# ---------------------------------------------------------------------------


def resolve_issue(
    issue_id: int,
    resolution_notes: Optional[str] = None,
    db_path: Optional[str] = None,
) -> bool:
    """Transition open → resolved. Sets resolved_at, persists notes."""
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, status FROM issues WHERE id = ?", (issue_id,),
        ).fetchone()
        if row is None:
            raise IssueNotFoundError(f"issue not found: id={issue_id}")
        _assert_transition(row["status"], "resolved", issue_id)
        cursor = conn.execute(
            """UPDATE issues
                   SET status = 'resolved',
                       resolved_at = ?,
                       resolution_notes = ?,
                       updated_at = ?
                 WHERE id = ?""",
            (now, resolution_notes, now, issue_id),
        )
        return cursor.rowcount > 0


def mark_duplicate_issue(
    issue_id: int,
    duplicate_of_issue_id: int,
    resolution_notes: Optional[str] = None,
    db_path: Optional[str] = None,
) -> bool:
    """Transition open → duplicate. Pre-check: canonical exists + not
    self-reference + canonical is not itself a duplicate (cycle prevention)."""
    if duplicate_of_issue_id == issue_id:
        raise ValueError(
            f"issue id={issue_id} cannot be a duplicate of itself"
        )
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, status FROM issues WHERE id = ?", (issue_id,),
        ).fetchone()
        if row is None:
            raise IssueNotFoundError(f"issue not found: id={issue_id}")
        canonical = conn.execute(
            "SELECT id, status FROM issues WHERE id = ?",
            (duplicate_of_issue_id,),
        ).fetchone()
        if canonical is None:
            raise ValueError(
                f"canonical issue not found: id={duplicate_of_issue_id}"
            )
        if canonical["status"] == "duplicate":
            raise ValueError(
                f"canonical issue id={duplicate_of_issue_id} is itself a "
                "duplicate; mark this issue as duplicate of the original "
                "canonical instead (one-hop chains only)"
            )
        _assert_transition(row["status"], "duplicate", issue_id)
        cursor = conn.execute(
            """UPDATE issues
                   SET status = 'duplicate',
                       resolved_at = ?,
                       resolution_notes = ?,
                       duplicate_of_issue_id = ?,
                       updated_at = ?
                 WHERE id = ?""",
            (now, resolution_notes, duplicate_of_issue_id, now, issue_id),
        )
        return cursor.rowcount > 0


def mark_wontfix_issue(
    issue_id: int,
    resolution_notes: str,
    db_path: Optional[str] = None,
) -> bool:
    """Transition open → wont_fix. resolution_notes REQUIRED (audit trail
    for deliberate non-action — e.g. 'customer declined $800 rebuild on
    $400 bike')."""
    if not resolution_notes or not str(resolution_notes).strip():
        raise ValueError(
            "resolution_notes is required for mark_wontfix_issue "
            "(audit-trail requirement for deliberate non-action)"
        )
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, status FROM issues WHERE id = ?", (issue_id,),
        ).fetchone()
        if row is None:
            raise IssueNotFoundError(f"issue not found: id={issue_id}")
        _assert_transition(row["status"], "wont_fix", issue_id)
        cursor = conn.execute(
            """UPDATE issues
                   SET status = 'wont_fix',
                       resolved_at = ?,
                       resolution_notes = ?,
                       updated_at = ?
                 WHERE id = ?""",
            (now, str(resolution_notes).strip(), now, issue_id),
        )
        return cursor.rowcount > 0


def reopen_issue(
    issue_id: int, db_path: Optional[str] = None,
) -> bool:
    """Transition resolved|duplicate|wont_fix → open. Clears
    resolved_at + resolution_notes + duplicate_of_issue_id.

    Audit semantics: if resolution wasn't actually correct, the trace
    was a lie and should not persist.
    """
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, status FROM issues WHERE id = ?", (issue_id,),
        ).fetchone()
        if row is None:
            raise IssueNotFoundError(f"issue not found: id={issue_id}")
        if row["status"] == "open":
            return False
        _assert_transition(row["status"], "open", issue_id)
        cursor = conn.execute(
            """UPDATE issues
                   SET status = 'open',
                       resolved_at = NULL,
                       resolution_notes = NULL,
                       duplicate_of_issue_id = NULL,
                       updated_at = ?
                 WHERE id = ?""",
            (now, issue_id),
        )
        return cursor.rowcount > 0


def issue_stats(
    work_order_id: Optional[int] = None,
    shop_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> dict:
    """Return rollup stats: total + by_status + by_category + by_severity
    + open_count + critical_open_count.
    """
    base_filter = []
    params: list = []
    if work_order_id is not None:
        base_filter.append("i.work_order_id = ?")
        params.append(work_order_id)
    if shop_id is not None:
        base_filter.append("wo.shop_id = ?")
        params.append(shop_id)
    where_clause = ""
    if base_filter:
        where_clause = " WHERE " + " AND ".join(base_filter)

    join_clause = " LEFT JOIN work_orders wo ON wo.id = i.work_order_id"

    with get_connection(db_path) as conn:
        total = conn.execute(
            f"SELECT COUNT(*) AS n FROM issues i{join_clause}{where_clause}",
            params,
        ).fetchone()["n"]

        by_status: dict[str, int] = {s: 0 for s in ISSUE_STATUSES}
        rows = conn.execute(
            f"SELECT i.status, COUNT(*) AS n FROM issues i"
            f"{join_clause}{where_clause} GROUP BY i.status",
            params,
        ).fetchall()
        for r in rows:
            by_status[r["status"]] = r["n"]

        by_category: dict[str, int] = {c: 0 for c in ISSUE_CATEGORIES}
        rows = conn.execute(
            f"SELECT i.category, COUNT(*) AS n FROM issues i"
            f"{join_clause}{where_clause} GROUP BY i.category",
            params,
        ).fetchall()
        for r in rows:
            by_category[r["category"]] = r["n"]

        by_severity: dict[str, int] = {s: 0 for s in ISSUE_SEVERITIES}
        rows = conn.execute(
            f"SELECT i.severity, COUNT(*) AS n FROM issues i"
            f"{join_clause}{where_clause} GROUP BY i.severity",
            params,
        ).fetchall()
        for r in rows:
            by_severity[r["severity"]] = r["n"]

        open_count = by_status.get("open", 0)

        crit_filter = list(base_filter) + ["i.status = 'open'", "i.severity = 'critical'"]
        crit_where = " WHERE " + " AND ".join(crit_filter)
        crit_row = conn.execute(
            f"SELECT COUNT(*) AS n FROM issues i{join_clause}{crit_where}",
            params,
        ).fetchone()
        critical_open_count = crit_row["n"] if crit_row else 0

    return {
        "total": int(total),
        "by_status": by_status,
        "by_category": by_category,
        "by_severity": by_severity,
        "open_count": int(open_count),
        "critical_open_count": int(critical_open_count),
    }
