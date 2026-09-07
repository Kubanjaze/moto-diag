"""Store + alert-suppression for OBD field-failure reports.

Why this exists: the BLE transport ships UNVERIFIED against real
hardware. Rather than buy an adapter to exercise a path no user can
currently reach (`OBD_SUPPORT` is dev-only), the first real-world
failure is made to reach the maintainer with enough context to
reproduce it — the error kind, the transport, the device id, and the
app/OS build it happened on.

The suppression window matters more than it looks. A mechanic whose
adapter will not connect does not try once; they try repeatedly. Without
it, one bad dongle becomes a dozen identical pushes, the alerts get
muted, and the mechanism is worse than useless because it now hides the
next real signal.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from motodiag.core.database import get_connection

#: Don't re-alert for the same (kind, transport) inside this window.
#: One dongle failing repeatedly is ONE story, not twelve.
ALERT_SUPPRESSION_MINUTES = 60


def _now() -> datetime:
    return datetime.now(timezone.utc)


def record_failure(
    user_id: int,
    error_kind: str,
    transport: Optional[str] = None,
    device_id: Optional[str] = None,
    message: Optional[str] = None,
    app_version: Optional[str] = None,
    platform: Optional[str] = None,
    os_version: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    """Persist one failure report. Returns its id."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO obd_failure_reports
                 (user_id, error_kind, transport, device_id, message,
                  app_version, platform, os_version, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id, error_kind, transport, device_id, message,
                app_version, platform, os_version, _now().isoformat(),
            ),
        )
        return int(cursor.lastrowid)


def should_alert(
    error_kind: str,
    transport: Optional[str],
    now: Optional[datetime] = None,
    db_path: Optional[str] = None,
) -> bool:
    """True when no alert for this (kind, transport) fired recently."""
    moment = now or _now()
    cutoff = (moment - timedelta(minutes=ALERT_SUPPRESSION_MINUTES)).isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM obd_failure_reports "
            "WHERE error_kind = ? AND COALESCE(transport, '') = ? "
            "AND notified_at IS NOT NULL AND notified_at > ? LIMIT 1",
            (error_kind, transport or "", cutoff),
        ).fetchone()
    return row is None


def mark_notified(
    report_id: int,
    now: Optional[datetime] = None,
    db_path: Optional[str] = None,
) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE obd_failure_reports SET notified_at = ? WHERE id = ?",
            ((now or _now()).isoformat(), report_id),
        )


def list_failures(
    limit: int = 50,
    db_path: Optional[str] = None,
) -> list[dict]:
    """Most recent field failures first — the maintainer's read path."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM obd_failure_reports "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
