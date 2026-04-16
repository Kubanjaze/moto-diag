"""Diagnostic session repository — lifecycle management for troubleshooting sessions."""

import json
import logging
from datetime import datetime

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
) -> list[dict]:
    """List sessions with optional filters."""
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

    sql += " ORDER BY created_at DESC"

    with get_connection(db_path) as conn:
        cursor = conn.execute(sql, params)
        return [_row_to_dict(row) for row in cursor.fetchall()]


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
