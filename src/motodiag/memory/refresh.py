"""Phase 209C — memory follows the session close.

Per-machine memory (Phase 244M) compiled only when someone ran
``motodiag memory compile``, so on a live server the history fed to the next
vision prompt went stale. The operator's decision on 2026-09-17 (209B,
*Decisions §6*): recompile on session close.

:func:`refresh_after_close` is called by ``core.session_repo.close_session``,
the one function every close goes through -- the API's close route, a PATCH
to ``status: "closed"``, and the CLI's ``diagnose`` flows.

It is best-effort by design. The close has already committed when this runs,
and a memory problem must never turn a finished job into an error on the
technician's screen. Failures are logged and swallowed; the next close, or a
manual compile, catches up, because a compile is idempotent.
"""

from __future__ import annotations

import logging
from typing import Optional

from motodiag.core.database import get_connection
from motodiag.memory.compile import CompileResult, compile_vehicle_detailed

log = logging.getLogger(__name__)


def refresh_after_close(
    session_id: int, db_path: Optional[str] = None,
) -> Optional[CompileResult]:
    """Recompile the closed session's machine. Never raises.

    Returns the compile's result, or ``None`` when there was nothing to do (no
    such session, or a session with no ``vehicle_id``) or the compile failed.
    """
    vehicle_id: Optional[int] = None
    try:
        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT vehicle_id FROM diagnostic_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
        if row is None or row[0] is None:
            return None
        vehicle_id = int(row[0])
        result = compile_vehicle_detailed(vehicle_id, db_path=db_path)
    except Exception:
        log.warning(
            "memory refresh after closing session %s (vehicle %s) failed; "
            "the close stands",
            session_id, vehicle_id, exc_info=True,
        )
        return None
    log.info(
        "memory refresh after closing session %s: vehicle %s, "
        "%d new, %d superseded, %d revived",
        session_id, vehicle_id,
        result.inserted, result.superseded, result.revived,
    )
    return result
