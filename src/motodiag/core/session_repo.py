"""Diagnostic session repository — lifecycle management for troubleshooting sessions."""

import json
import logging
from datetime import datetime
from typing import Optional

from motodiag.core.database import get_connection

log = logging.getLogger("motodiag.sessions")


def create_session(
    vehicle_make: str,
    vehicle_model: str,
    vehicle_year: int,
    symptoms: list[str] | None = None,
    fault_codes: list[str] | None = None,
    vehicle_id: int | None = None,
    db_path: str | None = None,
) -> int:
    """Create a new diagnostic session. Returns session ID."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO diagnostic_sessions
               (vehicle_id, vehicle_make, vehicle_model, vehicle_year,
                status, symptoms, fault_codes, created_at)
               VALUES (?, ?, ?, ?, 'open', ?, ?, ?)""",
            (
                vehicle_id, vehicle_make, vehicle_model, vehicle_year,
                json.dumps(symptoms or []),
                json.dumps(fault_codes or []),
                datetime.now().isoformat(),
            ),
        )
        sid = cursor.lastrowid
        log.info("Session %d created: %s %s %d", sid, vehicle_make, vehicle_model, vehicle_year)
        return sid


def get_session(session_id: int, db_path: str | None = None) -> dict | None:
    """Get a diagnostic session by ID."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM diagnostic_sessions WHERE id = ?", (session_id,)
        )
        row = cursor.fetchone()
        return _row_to_dict(row) if row else None


def update_session(session_id: int, updates: dict, db_path: str | None = None) -> bool:
    """Update session fields. Returns True if updated."""
    allowed = {
        "status", "diagnosis", "confidence", "severity",
        "cost_estimate", "ai_model_used", "tokens_used",
    }
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return False

    filtered["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in filtered)
    values = list(filtered.values()) + [session_id]

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE diagnostic_sessions SET {set_clause} WHERE id = ?", values
        )
        return cursor.rowcount > 0


def add_symptom_to_session(
    session_id: int, symptom: str, db_path: str | None = None
) -> bool:
    """Append a symptom to the session's symptom list."""
    session = get_session(session_id, db_path)
    if not session:
        return False

    symptoms = session.get("symptoms", [])
    if symptom not in symptoms:
        symptoms.append(symptom)

    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE diagnostic_sessions SET symptoms = ?, updated_at = ? WHERE id = ?",
            (json.dumps(symptoms), datetime.now().isoformat(), session_id),
        )
    return True


def add_fault_code_to_session(
    session_id: int, code: str, db_path: str | None = None
) -> bool:
    """Append a fault code to the session's fault code list."""
    session = get_session(session_id, db_path)
    if not session:
        return False

    codes = session.get("fault_codes", [])
    if code not in codes:
        codes.append(code)

    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE diagnostic_sessions SET fault_codes = ?, updated_at = ? WHERE id = ?",
            (json.dumps(codes), datetime.now().isoformat(), session_id),
        )
    return True


def set_diagnosis(
    session_id: int,
    diagnosis: str,
    confidence: float | None = None,
    severity: str | None = None,
    repair_steps: list[str] | None = None,
    db_path: str | None = None,
) -> bool:
    """Set the diagnosis for a session, transitioning status to 'diagnosed'."""
    log.info("Session %d diagnosed: %s (confidence=%.2f)", session_id, diagnosis[:80], confidence or 0)
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """UPDATE diagnostic_sessions
               SET diagnosis = ?, confidence = ?, severity = ?,
                   repair_steps = ?, status = 'diagnosed', updated_at = ?
               WHERE id = ?""",
            (
                diagnosis, confidence, severity,
                json.dumps(repair_steps or []),
                now, session_id,
            ),
        )
        return cursor.rowcount > 0


def close_session(session_id: int, db_path: str | None = None) -> bool:
    """Close a session, setting status to 'closed' and closed_at timestamp."""
    log.info("Session %d closed", session_id)
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """UPDATE diagnostic_sessions
               SET status = 'closed', closed_at = ?, updated_at = ?
               WHERE id = ?""",
            (now, now, session_id),
        )
        return cursor.rowcount > 0


def list_sessions(
    status: str | None = None,
    vehicle_make: str | None = None,
    vehicle_model: str | None = None,
    db_path: str | None = None,
    *,
    vehicle_id: int | None = None,
    search: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """List sessions with optional filters.

    Phase 127: keyword-only filters for the session history browser:
      - vehicle_id: exact match on the vehicle_id FK column
      - search:     case-insensitive substring match on `diagnosis`
      - since:      sessions with created_at >= since (ISO date/datetime string)
      - until:      sessions with created_at <= until (ISO date/datetime string)
      - limit:      cap on number of returned rows (None = no cap)

    All filters AND together. Existing positional filters (status,
    vehicle_make, vehicle_model) retain their behavior and signature
    position so Phase 123+ callers remain compatible.

    Ordering: ORDER BY created_at DESC, id DESC so ties (same timestamp)
    are broken deterministically by insertion order newest-first — useful
    when seeding closely-timed fixtures in tests.
    """
    sql = "SELECT * FROM diagnostic_sessions WHERE 1=1"
    params: list = []

    if status:
        sql += " AND status = ?"
        params.append(status)
    if vehicle_make:
        sql += " AND vehicle_make LIKE ?"
        params.append(f"%{vehicle_make}%")
    if vehicle_model:
        sql += " AND vehicle_model LIKE ?"
        params.append(f"%{vehicle_model}%")
    if vehicle_id is not None:
        sql += " AND vehicle_id = ?"
        params.append(vehicle_id)
    if search:
        # Case-insensitive LIKE on diagnosis. LOWER() on both sides so the
        # match works regardless of how the diagnosis was stored.
        sql += " AND LOWER(diagnosis) LIKE LOWER(?)"
        params.append(f"%{search}%")
    if since:
        sql += " AND created_at >= ?"
        params.append(since)
    if until:
        sql += " AND created_at <= ?"
        params.append(until)

    sql += " ORDER BY created_at DESC, id DESC"

    if limit is not None:
        sql += " LIMIT ?"
        params.append(int(limit))

    with get_connection(db_path) as conn:
        cursor = conn.execute(sql, params)
        return [_row_to_dict(row) for row in cursor.fetchall()]


def reopen_session(session_id: int, db_path: str | None = None) -> bool:
    """Reopen a closed diagnostic session.

    Flips status back to 'open' and clears closed_at so a mechanic can
    continue a previously-wrapped diagnosis without losing prior context.
    Diagnosis, confidence, repair_steps, and all other fields are preserved
    — this is a pure status flip.

    Returns True if a row was actually updated (i.e., the session exists).
    Returns False if the session_id does not match any row.

    Note: calling reopen_session on an already-open session is a no-op at
    the SQL level (UPDATE still affects 1 row because the WHERE id=? matches),
    so this returns True. CLI callers that want to distinguish already-open
    from missing-session must check status first.
    """
    log.info("Session %d reopened", session_id)
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """UPDATE diagnostic_sessions
               SET status = 'open', closed_at = NULL, updated_at = ?
               WHERE id = ?""",
            (now, session_id),
        )
        return cursor.rowcount > 0


def append_note(
    session_id: int, note_text: str, db_path: str | None = None,
) -> bool:
    """Append a timestamped note to the session's notes column.

    Notes are append-only: each call prepends ``[YYYY-MM-DDTHH:MM] `` to
    note_text and concatenates it to existing notes separated by a blank
    line. If the session has no notes yet, the new string becomes the
    entire value. This preserves annotation history chronologically.

    Returns True if a row was updated, False if the session does not exist.
    """
    # First verify the session exists and fetch existing notes in one step.
    existing = get_notes(session_id, db_path=db_path)
    # get_notes returns None for both "missing session" and "session exists
    # but notes is NULL", so disambiguate with a session lookup.
    session = get_session(session_id, db_path=db_path)
    if session is None:
        return False

    stamp = datetime.now().isoformat(timespec="minutes")
    new_entry = f"[{stamp}] {note_text}"
    combined = new_entry if not existing else f"{existing}\n\n{new_entry}"

    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """UPDATE diagnostic_sessions
               SET notes = ?, updated_at = ?
               WHERE id = ?""",
            (combined, now, session_id),
        )
        return cursor.rowcount > 0


def get_notes(session_id: int, db_path: str | None = None) -> Optional[str]:
    """Return the raw notes column for a session, or None if missing/empty."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT notes FROM diagnostic_sessions WHERE id = ?", (session_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return row["notes"] if row["notes"] is not None else None


def count_sessions(status: str | None = None, db_path: str | None = None) -> int:
    """Count sessions, optionally filtered by status."""
    sql = "SELECT COUNT(*) FROM diagnostic_sessions"
    params: list = []

    if status:
        sql += " WHERE status = ?"
        params.append(status)

    with get_connection(db_path) as conn:
        cursor = conn.execute(sql, params)
        return cursor.fetchone()[0]


def _row_to_dict(row) -> dict:
    """Convert a database row to a dict, parsing JSON fields."""
    d = dict(row)
    for field in ("symptoms", "fault_codes", "repair_steps"):
        if d.get(field):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                d[field] = []
        else:
            d[field] = []
    return d


# ---------------------------------------------------------------------------
# Phase 178 additions: owner scoping + monthly quota
# ---------------------------------------------------------------------------


from datetime import timezone


class SessionOwnershipError(ValueError):
    """Raised when a caller tries to touch a session they don't own."""


class SessionQuotaExceededError(Exception):
    """Raised when creating a session would exceed the caller's
    monthly tier quota. Mapped to HTTP 402."""

    def __init__(self, current_count: int, limit: int, tier: str) -> None:
        self.current_count = current_count
        self.limit = limit
        self.tier = tier
        super().__init__(
            f"monthly session quota exceeded: {current_count}/{limit} "
            f"({tier} tier). Upgrade for more diagnostic sessions."
        )


TIER_SESSION_MONTHLY_LIMITS: dict[str, int] = {
    "individual": 50,
    "shop": 500,
    "company": -1,  # unlimited
}


def _month_start_iso() -> str:
    """First instant of the current UTC calendar month as ISO string.

    Note (Phase 191B fix-cycle 2026-05-01): this function has TWO
    pre-existing latent bugs that surface together on calendar-month
    boundaries when the dev machine's local clock and UTC straddle the
    boundary. Filed for follow-up rather than fixed here:

    1. Format mismatch: returns isoformat() (T-separator) but the
       table's `created_at` rows are written by `create_session` using
       ``datetime.now().isoformat()`` (also T-separator, but NAIVE
       LOCAL time). The lex comparison happens to work BECAUSE of (2)
       — fixing one without the other gets a different wrong answer.

    2. Naive-local vs UTC: `create_session` writes naive local-time
       ISO strings; `_month_start_iso` returns aware-UTC ISO. On
       boundary days (e.g., the dev machine in PT during 17:00-23:59
       PT corresponds to UTC May 1 — local-PT-April-30 stamps don't
       count as "this month" by UTC reckoning).

    Fix requires consolidating ALL session_repo writes to UTC + matching
    the format here. Out of scope for the Phase 191B fix-cycle which
    only touches video_repo's identical (but only one-bug) variant.
    Phase 178's quota tests visibly fail today (2026-05-01) until the
    sister fix lands — track as F10 in moto-diag-mobile/docs/FOLLOWUPS.md
    or a backend bug ticket.
    """
    now = datetime.now(timezone.utc)
    return now.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0,
    ).isoformat()


def create_session_for_owner(
    owner_user_id: int,
    vehicle_make: str,
    vehicle_model: str,
    vehicle_year: int,
    symptoms: list[str] | None = None,
    fault_codes: list[str] | None = None,
    vehicle_id: int | None = None,
    db_path: str | None = None,
) -> int:
    """Same as :func:`create_session` but stamps ``user_id``. Does NOT
    check tier quota — caller should call
    :func:`check_session_quota` first."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO diagnostic_sessions
               (vehicle_id, vehicle_make, vehicle_model, vehicle_year,
                status, symptoms, fault_codes, created_at, user_id)
               VALUES (?, ?, ?, ?, 'open', ?, ?, ?, ?)""",
            (
                vehicle_id, vehicle_make, vehicle_model, vehicle_year,
                json.dumps(symptoms or []),
                json.dumps(fault_codes or []),
                datetime.now().isoformat(),
                owner_user_id,
            ),
        )
        return cursor.lastrowid


def get_session_for_owner(
    session_id: int, owner_user_id: int,
    db_path: str | None = None,
) -> dict | None:
    """Return session iff owned by `owner_user_id`; None otherwise —
    routes translate None → 404 (nonexistent and cross-user
    indistinguishable to the caller)."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM diagnostic_sessions "
            "WHERE id = ? AND user_id = ?",
            (session_id, owner_user_id),
        )
        row = cursor.fetchone()
        return _row_to_dict(row) if row else None


def list_sessions_for_owner(
    owner_user_id: int,
    status: str | None = None,
    vehicle_id: int | None = None,
    since_iso: str | None = None,
    limit: int = 100,
    db_path: str | None = None,
) -> list[dict]:
    query = "SELECT * FROM diagnostic_sessions WHERE user_id = ?"
    params: list = [owner_user_id]
    if status is not None:
        query += " AND status = ?"
        params.append(status)
    if vehicle_id is not None:
        query += " AND vehicle_id = ?"
        params.append(vehicle_id)
    if since_iso is not None:
        query += " AND created_at >= ?"
        params.append(since_iso)
    query += " ORDER BY created_at DESC, id DESC"
    if limit and limit > 0:
        query += " LIMIT ?"
        params.append(int(limit))
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        return [_row_to_dict(r) for r in rows]


def count_sessions_this_month_for_owner(
    owner_user_id: int, db_path: str | None = None,
) -> int:
    """Count sessions created by `owner_user_id` in the current UTC
    calendar month. Used by the POST endpoint's quota check."""
    month_start = _month_start_iso()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM diagnostic_sessions "
            "WHERE user_id = ? AND created_at >= ?",
            (owner_user_id, month_start),
        ).fetchone()
    return int(row["n"]) if row else 0


def check_session_quota(
    owner_user_id: int, tier: str | None,
    db_path: str | None = None,
) -> None:
    """Raise `SessionQuotaExceededError` when creating one more
    session would exceed the monthly tier quota."""
    effective = (
        tier if tier in TIER_SESSION_MONTHLY_LIMITS else "individual"
    )
    limit = TIER_SESSION_MONTHLY_LIMITS[effective]
    if limit < 0:
        return
    current = count_sessions_this_month_for_owner(
        owner_user_id, db_path=db_path,
    )
    if current >= limit:
        raise SessionQuotaExceededError(
            current_count=current, limit=limit, tier=effective,
        )


def _assert_owner(
    session_id: int, owner_user_id: int,
    db_path: str | None,
) -> dict | None:
    """Return session row if owned by caller; None if missing;
    raise `SessionOwnershipError` on cross-owner."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT user_id, status FROM diagnostic_sessions "
            "WHERE id = ?",
            (session_id,),
        ).fetchone()
    if row is None:
        return None
    if int(row["user_id"] or 0) != owner_user_id:
        raise SessionOwnershipError(
            f"session id={session_id} not owned by "
            f"user id={owner_user_id}"
        )
    return dict(row)


def update_session_for_owner(
    session_id: int, owner_user_id: int, updates: dict,
    db_path: str | None = None,
) -> bool:
    guard = _assert_owner(session_id, owner_user_id, db_path)
    if guard is None:
        return False
    return update_session(session_id, updates, db_path=db_path)


def close_session_for_owner(
    session_id: int, owner_user_id: int,
    db_path: str | None = None,
) -> bool:
    guard = _assert_owner(session_id, owner_user_id, db_path)
    if guard is None:
        return False
    return close_session(session_id, db_path=db_path)


def reopen_session_for_owner(
    session_id: int, owner_user_id: int,
    db_path: str | None = None,
) -> bool:
    guard = _assert_owner(session_id, owner_user_id, db_path)
    if guard is None:
        return False
    return reopen_session(session_id, db_path=db_path)


def add_symptom_for_owner(
    session_id: int, owner_user_id: int, symptom: str,
    db_path: str | None = None,
) -> bool:
    guard = _assert_owner(session_id, owner_user_id, db_path)
    if guard is None:
        return False
    return add_symptom_to_session(session_id, symptom, db_path=db_path)


def add_fault_code_for_owner(
    session_id: int, owner_user_id: int, code: str,
    db_path: str | None = None,
) -> bool:
    guard = _assert_owner(session_id, owner_user_id, db_path)
    if guard is None:
        return False
    return add_fault_code_to_session(session_id, code, db_path=db_path)


def append_note_for_owner(
    session_id: int, owner_user_id: int, note: str,
    db_path: str | None = None,
) -> bool:
    guard = _assert_owner(session_id, owner_user_id, db_path)
    if guard is None:
        return False
    return append_note(session_id, note, db_path=db_path)
