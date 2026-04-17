"""Video tutorials repository.

Phase 117: CRUD for tutorial video index (YouTube/Vimeo/internal).
"""

import json
from typing import Optional

from motodiag.core.database import get_connection
from motodiag.reference.models import VideoTutorial, SkillLevel


def _row_to_video(row) -> dict:
    d = dict(row)
    if d.get("topic_tags"):
        try:
            d["topic_tags"] = json.loads(d["topic_tags"])
        except (json.JSONDecodeError, TypeError):
            d["topic_tags"] = []
    else:
        d["topic_tags"] = []
    return d


def add_video(video: VideoTutorial, db_path: str | None = None) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO video_tutorials
               (title, description, source, source_video_id, url,
                duration_seconds, make, model, year_start, year_end,
                skill_level, topic_tags)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                video.title, video.description, video.source, video.source_video_id,
                video.url, video.duration_seconds, video.make, video.model,
                video.year_start, video.year_end, video.skill_level.value,
                json.dumps(video.topic_tags),
            ),
        )
        return cursor.lastrowid


def get_video(video_id: int, db_path: str | None = None) -> Optional[dict]:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM video_tutorials WHERE id = ?", (video_id,),
        )
        row = cursor.fetchone()
        return _row_to_video(row) if row else None


def list_videos(
    source: Optional[str] = None,
    skill_level: SkillLevel | str | None = None,
    make: Optional[str] = None,
    model: Optional[str] = None,
    target_year: Optional[int] = None,
    topic: Optional[str] = None,
    db_path: str | None = None,
) -> list[dict]:
    """List videos. `topic` does a LIKE match against topic_tags JSON text."""
    query = "SELECT * FROM video_tutorials WHERE 1=1"
    params: list = []
    if source is not None:
        query += " AND source = ?"
        params.append(source)
    if skill_level is not None:
        sval = skill_level.value if isinstance(skill_level, SkillLevel) else skill_level
        query += " AND skill_level = ?"
        params.append(sval)
    if make is not None:
        query += " AND (make IS NULL OR make = ?)"
        params.append(make)
    if model is not None:
        query += " AND (model IS NULL OR model = ?)"
        params.append(model)
    if target_year is not None:
        query += (
            " AND (year_start IS NULL OR year_start <= ?)"
            " AND (year_end IS NULL OR year_end >= ?)"
        )
        params.extend([target_year, target_year])
    if topic is not None:
        query += " AND topic_tags LIKE ?"
        params.append(f'%"{topic}"%')
    query += " ORDER BY title"
    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [_row_to_video(r) for r in cursor.fetchall()]


def update_video(video_id: int, db_path: str | None = None, **fields) -> bool:
    if not fields:
        return False
    if "topic_tags" in fields and isinstance(fields["topic_tags"], list):
        fields["topic_tags"] = json.dumps(fields["topic_tags"])
    if "skill_level" in fields and isinstance(fields["skill_level"], SkillLevel):
        fields["skill_level"] = fields["skill_level"].value
    keys = ", ".join(f"{k} = ?" for k in fields)
    params = list(fields.values()) + [video_id]
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE video_tutorials SET {keys} WHERE id = ?", params,
        )
        return cursor.rowcount > 0


def delete_video(video_id: int, db_path: str | None = None) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM video_tutorials WHERE id = ?", (video_id,),
        )
        return cursor.rowcount > 0
