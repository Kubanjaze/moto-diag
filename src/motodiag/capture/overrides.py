"""Phase 244N — capture a mechanic's correction as a byproduct of their edit.

This is the cheapest ground truth the product can obtain, and the reason is
that it asks for nothing. A technician corrects the diagnosis because they need
it correct on the work order. Recording *that they changed it* costs them
exactly zero additional effort.

`session_overrides` was built for this at Phase 116 -- `(field_name, ai_value,
override_value, reason)` is precisely "the AI said X, a mechanic changed it to
Y" -- and `feedback_repo.record_override` has been sitting there, correct and
uncalled, ever since. The table has zero rows because **no path ever reached
it**, not because nobody wanted the data.

Meanwhile `PATCH /v1/sessions/{id}` has been accepting `diagnosis`,
`confidence` and `severity` and overwriting them without recording what was
there. The signal was walking past the storage every time.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

_log = logging.getLogger(__name__)

# Only fields the model actually authors, and only those that are BOTH in
# `OverrideField` and accepted by `SessionUpdateRequest` -- the intersection is
# what a PATCH can actually correct. `repair_steps` and `parts` are in the enum
# but not in the request model, so no PATCH can carry them; `status` is in the
# request but is workflow rather than a correction, and recording an open->
# closed transition as an override would dilute the signal with ordinary state
# changes.
CAPTURED_FIELDS: tuple[str, ...] = (
    "diagnosis",
    "confidence",
    "severity",
    "cost_estimate",
)


def _differs(before: Any, after: Any) -> bool:
    """Whether an update actually changes the value.

    Compared as strings because the request carries a float `0.8` while SQLite
    may hand back `0.8` or `'0.8'` depending on the column's declared affinity
    and how the row was written. A no-op PATCH must record nothing -- sending
    the same value is not a correction, and counting it as one would inflate
    every accuracy number computed from this table later.
    """
    if before is None and after is None:
        return False
    if before is None or after is None:
        return True
    return str(before).strip() != str(after).strip()


def capture_session_overrides(
    session_id: int,
    before: dict,
    updates: dict,
    *,
    user_id: int = 1,
    db_path: Optional[str] = None,
) -> int:
    """Record human corrections of AI-authored values. Returns rows written.

    **Never raises.** A capture write that fails a technician's edit has traded
    the thing that matters for the thing that might matter later.

    Three conditions, all of which must hold for a field to be recorded:

    1. The field is one the model authors (:data:`CAPTURED_FIELDS`).
    2. The value actually changed.
    3. The session carries `ai_model_used` -- so the prior value has an author.
       A session the model never touched has no `ai_value` to contrast, and
       recording ``(NULL -> "x")`` as an override would fill the table with
       ordinary data entry and quietly ruin every statistic drawn from it.
    """
    if not before.get("ai_model_used"):
        return 0

    written = 0
    try:
        from motodiag.feedback.feedback_repo import record_override
        from motodiag.feedback.models import OverrideField, SessionOverride

        for field in CAPTURED_FIELDS:
            if field not in updates:
                continue
            new_value = updates[field]
            old_value = before.get(field)
            if not _differs(old_value, new_value):
                continue

            record_override(
                SessionOverride(
                    session_id=session_id,
                    field_name=OverrideField(field),
                    ai_value=None if old_value is None else str(old_value),
                    override_value=None if new_value is None else str(new_value),
                    overridden_by_user_id=user_id,
                    reason="",
                ),
                db_path=db_path,
            )
            written += 1
    except Exception as exc:
        _log.warning("Session override not captured for %s: %s", session_id, exc)
        return written

    return written
