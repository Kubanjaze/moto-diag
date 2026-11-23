"""Manual references repository.

Phase 117: CRUD for service manual citations (Clymer/Haynes/OEM/forum).

Phase 293: a shop's own uploaded manuals (migration 092). A row with a
``shop_id`` is that shop's file, private to it; its pages are rows of
``manual_pages``, whose text the FTS5 index ``manual_pages_fts`` holds. Only
an ``approved`` manual is opened or searched by the shop (K119).
"""

import json
from typing import Callable, Optional

from motodiag.core.database import get_connection
from motodiag.core.timestamps import utc_now
from motodiag.reference.models import ManualReference, ManualSource

_TAG_FIELDS = ("title", "kind", "make", "model", "year_start", "year_end")


def _row_to_manual(row) -> dict:
    d = dict(row)
    if d.get("section_titles"):
        try:
            d["section_titles"] = json.loads(d["section_titles"])
        except (json.JSONDecodeError, TypeError):
            d["section_titles"] = []
    else:
        d["section_titles"] = []
    return d


def add_manual(manual: ManualReference, db_path: str | None = None) -> int:
    """Insert a manual reference. Returns row id."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO manual_references
               (source, title, publisher, isbn, make, model,
                year_start, year_end, page_count, section_titles, url, notes,
                shop_id, file_path, file_sha256, file_size_bytes,
                uploaded_by_user_id, kind, status, rendered_pages)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                       ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                manual.source.value, manual.title, manual.publisher, manual.isbn,
                manual.make, manual.model, manual.year_start, manual.year_end,
                manual.page_count, json.dumps(manual.section_titles),
                manual.url, manual.notes,
                manual.shop_id, manual.file_path, manual.file_sha256,
                manual.file_size_bytes, manual.uploaded_by_user_id, manual.kind,
                manual.status, manual.rendered_pages,
            ),
        )
        return cursor.lastrowid


def get_manual(manual_id: int, db_path: str | None = None) -> Optional[dict]:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM manual_references WHERE id = ?", (manual_id,),
        )
        row = cursor.fetchone()
        return _row_to_manual(row) if row else None


def list_manuals(
    source: ManualSource | str | None = None,
    make: Optional[str] = None,
    model: Optional[str] = None,
    target_year: Optional[int] = None,
    db_path: str | None = None,
    shop_id: Optional[int] = None,
    status: Optional[str] = None,
    kind: Optional[str] = None,
) -> list[dict]:
    """List manuals with optional filters. target_year matches year_start <= Y <= year_end
    (NULL year_start means universal)."""
    query = "SELECT * FROM manual_references WHERE 1=1"
    params: list = []
    if source is not None:
        sval = source.value if isinstance(source, ManualSource) else source
        query += " AND source = ?"
        params.append(sval)
    if shop_id is not None:
        query += " AND shop_id = ?"
        params.append(shop_id)
    if status is not None:
        query += " AND status = ?"
        params.append(status)
    if kind is not None:
        query += " AND kind = ?"
        params.append(kind)
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
    query += " ORDER BY title"
    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [_row_to_manual(r) for r in cursor.fetchall()]


def update_manual(manual_id: int, db_path: str | None = None, **fields) -> bool:
    """Update arbitrary fields on a manual. Returns True if a row was updated."""
    if not fields:
        return False
    if "section_titles" in fields and isinstance(fields["section_titles"], list):
        fields["section_titles"] = json.dumps(fields["section_titles"])
    if "source" in fields and isinstance(fields["source"], ManualSource):
        fields["source"] = fields["source"].value
    keys = ", ".join(f"{k} = ?" for k in fields)
    params = list(fields.values()) + [manual_id]
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE manual_references SET {keys} WHERE id = ?", params,
        )
        return cursor.rowcount > 0


def delete_manual(manual_id: int, db_path: str | None = None) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM manual_references WHERE id = ?", (manual_id,),
        )
        return cursor.rowcount > 0


# --------------------------------------------------- Phase 293: a shop's files
def set_file(manual_id: int, file_path: str, sha256: str, size: int,
             page_count: int, db_path: str | None = None) -> bool:
    """Record where the uploaded file is, its hash, its size and its pages."""
    return update_manual(manual_id, db_path=db_path, file_path=file_path,
                         file_sha256=sha256, file_size_bytes=size,
                         page_count=page_count)


def set_status(manual_id: int, status: str, reviewed_by_user_id: Optional[int],
               reason: Optional[str], clock: Callable[[], str] = utc_now,
               db_path: str | None = None) -> bool:
    """A review decision: the status, who made it, when (UTC) and why."""
    return update_manual(manual_id, db_path=db_path, status=status,
                         reviewed_by_user_id=reviewed_by_user_id,
                         reviewed_at=clock(), review_reason=reason)


def update_tag(manual_id: int, title: Optional[str] = None, kind: Optional[str] = None,
               make: Optional[str] = None, model: Optional[str] = None,
               year_start: Optional[int] = None, year_end: Optional[int] = None,
               db_path: str | None = None) -> bool:
    """Change the tag fields given; a field left None is unchanged."""
    values = dict(zip(_TAG_FIELDS, (title, kind, make, model, year_start, year_end)))
    return update_manual(manual_id, db_path=db_path,
                         **{k: v for k, v in values.items() if v is not None})


def find_by_sha(shop_id: int, sha256: str, db_path: str | None = None) -> Optional[dict]:
    """This shop's manual with the same file, whatever its status."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM manual_references WHERE shop_id = ? AND file_sha256 = ? "
            "ORDER BY id LIMIT 1", (shop_id, sha256),
        ).fetchone()
    return _row_to_manual(row) if row else None


def storage_used_bytes(shop_id: int, db_path: str | None = None) -> int:
    """The bytes of the files the shop uploaded, of every status; never the
    page images made from them (K123)."""
    with get_connection(db_path) as conn:
        (total,) = conn.execute(
            "SELECT COALESCE(SUM(file_size_bytes), 0) FROM manual_references WHERE shop_id = ?",
            (shop_id,),
        ).fetchone()
    return int(total)


def add_page(manual_id: int, page_number: int, image_path: str, thumb_path: str,
             text: str, db_path: str | None = None) -> int:
    """One rendered page; the triggers put its text in the FTS index."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO manual_pages (manual_id, page_number, image_path, thumb_path, text) "
            "VALUES (?, ?, ?, ?, ?)",
            (manual_id, page_number, image_path, thumb_path, text),
        )
        return int(cursor.lastrowid or 0)


def get_page(manual_id: int, page_number: int, db_path: str | None = None) -> Optional[dict]:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM manual_pages WHERE manual_id = ? AND page_number = ?",
            (manual_id, page_number),
        ).fetchone()
    return dict(row) if row else None


def list_pages(manual_id: int, db_path: str | None = None) -> list[dict]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM manual_pages WHERE manual_id = ? ORDER BY page_number",
            (manual_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def set_rendered(manual_id: int, rendered_pages: int, render_error: Optional[str] = None,
                 db_path: str | None = None) -> bool:
    return update_manual(manual_id, db_path=db_path, rendered_pages=rendered_pages,
                         render_error=render_error)


def fts_query(q: str) -> str:
    """Each term of ``q`` quoted for FTS5 (embedded quotes doubled), so the
    query's own syntax is read as words and never as an FTS5 expression."""
    return " ".join('"' + term.replace('"', '""') + '"' for term in q.split())


def search_pages(shop_id: int, q: str, make: Optional[str] = None,
                 model: Optional[str] = None, target_year: Optional[int] = None,
                 limit: int = 20, db_path: str | None = None) -> list[dict]:
    """The pages of this shop's approved manuals holding every word of ``q``,
    best first, each with a snippet."""
    match = fts_query(q)
    if not match:
        return []
    query = (
        "SELECT m.id AS manual_id, m.title, p.page_number, "
        "snippet(manual_pages_fts, 0, '[', ']', '…', 12) AS snippet "
        "FROM manual_pages_fts "
        "JOIN manual_pages p ON p.id = manual_pages_fts.rowid "
        "JOIN manual_references m ON m.id = p.manual_id "
        "WHERE manual_pages_fts MATCH ?"
        " AND m.shop_id = ?"
        " AND m.status = 'approved'"
    )
    params: list = [match, shop_id]
    if make is not None:
        query += " AND (m.make IS NULL OR m.make = ?)"
        params.append(make)
    if model is not None:
        query += " AND (m.model IS NULL OR m.model = ?)"
        params.append(model)
    if target_year is not None:
        query += (" AND (m.year_start IS NULL OR m.year_start <= ?)"
                  " AND (m.year_end IS NULL OR m.year_end >= ?)")
        params.extend([target_year, target_year])
    query += " ORDER BY rank LIMIT ?"
    params.append(limit)
    with get_connection(db_path) as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def list_for_review(status: str = "pending_review", db_path: str | None = None) -> list[dict]:
    """Every shop's manuals of this status, oldest first, with the shop's
    name and the uploader's username: the reviewer's queue."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT m.*, s.name AS shop_name, u.username AS uploader_username "
            "FROM manual_references m "
            "LEFT JOIN shops s ON s.id = m.shop_id "
            "LEFT JOIN users u ON u.id = m.uploaded_by_user_id "
            "WHERE m.shop_id IS NOT NULL AND m.status = ? "
            "ORDER BY m.created_at, m.id",
            (status,),
        ).fetchall()
    return [_row_to_manual(r) for r in rows]
