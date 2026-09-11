"""Phase 244N — persist the guidance question and its answer.

`/ask` produced a full :class:`GuidanceResponse` -- the restated question,
ranked candidates each carrying why it is plausible, the check that
discriminates it from the others, and a ``Grounding`` label, plus what would
narrow the set and what could not be established -- serialised it to the
client, and dropped it.

Since Phase 244L a `vision_guidance` cost row survives the request. So the
product recorded what the question **cost** and not what it **was**.

This is the highest-value signal the product could have: a real technician, on
a real machine, mid-repair, asking what they actually need to know.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from motodiag.core.database import get_connection

_log = logging.getLogger(__name__)


def _as_dict(response: Any) -> dict:
    """Accept a pydantic model or a plain dict, return a dict."""
    if hasattr(response, "model_dump"):
        return response.model_dump(mode="json")
    if isinstance(response, dict):
        return response
    raise TypeError(f"cannot serialise {type(response)!r}")


def record_guidance_interaction(
    question: str,
    response: Any,
    *,
    video_id: Optional[int] = None,
    vehicle_id: Optional[int] = None,
    session_id: Optional[int] = None,
    model_used: Optional[str] = None,
    cost_event_id: Optional[int] = None,
    asked_by_user_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> Optional[int]:
    """Record one guidance interaction. Returns the row id, or None on failure.

    **Never raises.** The answer has already been produced and paid for by the
    time this runs; a logging failure must not cost the technician the thing
    they asked for. Phase 244L set this contract for cost recording and it
    applies for the same reason.

    The whole response is stored as JSON *and* three fields are promoted to
    columns. ``answers_the_question`` especially: "how often can the product
    not answer what was asked" is the most interesting question anyone will ask
    of this table, and it must not require scanning JSON to count.
    """
    try:
        payload = _as_dict(response)
    except TypeError:
        _log.warning("Guidance interaction not recorded: unserialisable response")
        return None

    candidates = payload.get("candidates") or []
    answered = payload.get("answers_the_question")

    try:
        with get_connection(db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO guidance_interactions
                    (video_id, vehicle_id, session_id, question,
                     question_understood_as, answers_the_question,
                     candidate_count, response_json, model_used,
                     cost_event_id, asked_by_user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    video_id,
                    vehicle_id,
                    session_id,
                    question,
                    payload.get("question_understood_as") or "",
                    None if answered is None else int(bool(answered)),
                    len(candidates) if isinstance(candidates, list) else 0,
                    json.dumps(payload, sort_keys=True, default=str),
                    model_used,
                    cost_event_id,
                    asked_by_user_id,
                ),
            )
            conn.commit()
            return cursor.lastrowid
    except Exception as exc:
        # Includes the FK case: a video_id that no longer resolves must not
        # lose the interaction. Logged and dropped rather than raised, because
        # the alternative is failing a request that already succeeded.
        _log.warning("Guidance interaction not recorded: %s", exc)
        return None


def list_interactions(
    *,
    vehicle_id: Optional[int] = None,
    video_id: Optional[int] = None,
    limit: int = 50,
    db_path: Optional[str] = None,
) -> list[dict]:
    """Recorded interactions, newest first."""
    sql = [
        "SELECT id, video_id, vehicle_id, session_id, question,",
        "       question_understood_as, answers_the_question,",
        "       candidate_count, response_json, model_used, created_at",
        "FROM guidance_interactions WHERE 1=1",
    ]
    params: list[Any] = []
    if vehicle_id is not None:
        sql.append("AND vehicle_id = ?")
        params.append(vehicle_id)
    if video_id is not None:
        sql.append("AND video_id = ?")
        params.append(video_id)
    sql.append("ORDER BY created_at DESC, id DESC LIMIT ?")
    params.append(limit)

    with get_connection(db_path) as conn:
        rows = conn.execute(" ".join(sql), params).fetchall()

    out = []
    for r in rows:
        out.append(
            {
                "id": r[0],
                "video_id": r[1],
                "vehicle_id": r[2],
                "session_id": r[3],
                "question": r[4],
                "question_understood_as": r[5],
                "answers_the_question": None if r[6] is None else bool(r[6]),
                "candidate_count": r[7],
                "response": json.loads(r[8]),
                "model_used": r[9],
                "created_at": r[10],
            }
        )
    return out
