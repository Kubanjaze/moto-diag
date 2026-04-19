"""Phase 154 — Technical Service Bulletin (TSB) repository.

CRUD + query layer over the ``technical_service_bulletins`` table
created by migration 022. A TSB is an OEM-issued official fix for a
known issue — distinct from Phase 155 federal safety recalls and from
Phase 08 forum-consensus ``known_issues``. The three provenance layers
stack: a mechanic looking at a 2012 Dyna with a weak charging system
sees the forum-sourced stator prediction (Phase 08/148), any open
safety recall (Phase 155), AND any HD-issued TSB (this phase) — each
annotated with its own verification chain.

Design notes
------------

- **UNIQUE tsb_number + INSERT OR IGNORE** makes re-seeding
  idempotent. A mechanic editing ``tsbs.json`` and re-running the
  loader gets the same state regardless of how many times they re-
  import.
- **Lowercase make on insert** normalizes ``"Harley-Davidson"``,
  ``"harley"``, and ``"HARLEY"`` to the same canonical key. Query-
  side callers do the same lowercasing for symmetric matching.
- **SQL LIKE model_pattern** lets one row cover ``"Dyna%"`` (all
  Dyna variants) or ``"CBR600%"`` (all CBR600 sub-models). Callers
  pass the bike's exact model at query time and the DB applies the
  pattern via ``model LIKE pattern``.
- **Severity CHECK** is enforced by the DB schema; we re-validate in
  Python so callers get a clean ``ValueError`` with the bad value
  rather than an opaque ``sqlite3.IntegrityError``.
- **ISO issued_date** (YYYY-MM-DD) is validated via
  ``datetime.fromisoformat`` so the index on issued_date DESC sorts
  lexicographically the same way it sorts chronologically.
- **Graceful degradation** on a pre-migration-022 DB: the Phase 148
  hook ``tsb_numbers_for_vehicle`` catches ``sqlite3.OperationalError``
  and returns ``[]`` so predictors keep running on older schemas.
- **Pattern specificity** for ``list_tsbs_for_bike`` is computed in
  Python — specific patterns (``"Sportster 1200"``) outrank family
  patterns (``"Sportster%"``) which outrank wildcards (``"%"``).
  Fighting SQL for a specificity score is worse than a quick sort.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from motodiag.core.database import get_connection


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


VALID_SEVERITIES: tuple[str, ...] = ("critical", "high", "medium", "low")

# Severity bucket-adjacent window used by the Phase 148 hook. Two bands
# adjacent in the severity ladder are considered "close enough" for
# predictor TSB attachment — a ``high`` predicted failure gets
# ``high``+``critical``+``medium`` TSBs, not just ``high``.
_SEVERITY_ORDER: dict[str, int] = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate_tsb_fields(
    tsb_number: str,
    make: str,
    severity: str,
    issued_date: str,
) -> tuple[str, str, str, str]:
    """Normalize + validate the four canonically-required TSB fields.

    Returns the sanitized ``(tsb_number, make, severity, issued_date)``
    tuple. Raises ``ValueError`` with an actionable message on any
    invalid input.
    """
    if tsb_number is None or not str(tsb_number).strip():
        raise ValueError("tsb_number must be a non-empty string")
    if make is None or not str(make).strip():
        raise ValueError("make must be a non-empty string")

    normalized_severity = str(severity or "medium").strip().lower()
    if normalized_severity not in VALID_SEVERITIES:
        raise ValueError(
            f"severity must be one of {VALID_SEVERITIES} (got {severity!r})"
        )

    normalized_date = str(issued_date).strip()
    try:
        datetime.fromisoformat(normalized_date)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"issued_date must be ISO format (YYYY-MM-DD); got {issued_date!r}"
        ) from exc

    return (
        str(tsb_number).strip(),
        str(make).strip().lower(),
        normalized_severity,
        normalized_date,
    )


def _pattern_specificity(pattern: str) -> int:
    """Return a sortable int where lower = more specific.

    Heuristic: count wildcard characters + reward exact literals. A
    pattern of ``"%"`` or ``"*"`` (wildcard-only) sinks to the bottom;
    a bare literal like ``"Sportster 1200"`` floats to the top. Used
    by ``list_tsbs_for_bike`` to present the most-targeted TSB first
    when multiple rows match the same bike.
    """
    if not pattern:
        return 10_000
    wildcard_count = pattern.count("%") + pattern.count("*")
    # Shorter literals are less specific than longer ones. Weight the
    # wildcard count heavily (100 per) so any wildcard beats any literal
    # of similar length.
    return wildcard_count * 100 - len(pattern)


# ---------------------------------------------------------------------------
# Write API
# ---------------------------------------------------------------------------


def add_tsb(
    tsb_number: str,
    make: str,
    model_pattern: str,
    title: str,
    description: str,
    fix_procedure: str,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    severity: str = "medium",
    issued_date: Optional[str] = None,
    source_url: Optional[str] = None,
    verified_by: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    """Insert a TSB row. Returns the rowid (existing or newly inserted).

    Uses INSERT OR IGNORE on ``tsb_number`` so re-running the loader
    produces no duplicates. When ``issued_date`` is omitted, today's
    date is used.
    """
    if not model_pattern or not str(model_pattern).strip():
        raise ValueError("model_pattern must be a non-empty string")
    if not title or not str(title).strip():
        raise ValueError("title must be a non-empty string")
    if not description:
        description = ""
    if not fix_procedure:
        fix_procedure = ""

    effective_issued = issued_date if issued_date else date.today().isoformat()

    (
        clean_tsb_number,
        clean_make,
        clean_severity,
        clean_issued_date,
    ) = _validate_tsb_fields(
        tsb_number=tsb_number,
        make=make,
        severity=severity,
        issued_date=effective_issued,
    )

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO technical_service_bulletins
                (tsb_number, make, model_pattern, year_min, year_max,
                 title, description, fix_procedure, severity,
                 issued_date, source_url, verified_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                clean_tsb_number,
                clean_make,
                str(model_pattern).strip(),
                year_min,
                year_max,
                str(title).strip(),
                description,
                fix_procedure,
                clean_severity,
                clean_issued_date,
                source_url,
                verified_by,
            ),
        )
        if cursor.lastrowid:
            return int(cursor.lastrowid)
        # INSERT OR IGNORE skipped — fetch the existing row's id.
        row = conn.execute(
            "SELECT id FROM technical_service_bulletins WHERE tsb_number = ?",
            (clean_tsb_number,),
        ).fetchone()
        return int(row[0]) if row else 0


# ---------------------------------------------------------------------------
# Read API
# ---------------------------------------------------------------------------


def get_tsb(tsb_number: str, db_path: Optional[str] = None) -> Optional[dict]:
    """Fetch one TSB by its (whitespace-normalized) number. None when missing."""
    if tsb_number is None:
        return None
    normalized = str(tsb_number).strip()
    if not normalized:
        return None
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM technical_service_bulletins WHERE tsb_number = ?",
            (normalized,),
        ).fetchone()
        return dict(row) if row else None


def list_tsbs(
    limit: Optional[int] = None,
    db_path: Optional[str] = None,
) -> list[dict]:
    """List every TSB in reverse-chronological order (most recent first).

    Sort order: ``issued_date DESC, id DESC`` so same-day TSBs tiebreak
    by insertion order (most recent insert first).
    """
    sql = (
        "SELECT * FROM technical_service_bulletins "
        "ORDER BY issued_date DESC, id DESC"
    )
    params: tuple = ()
    if limit is not None:
        sql += " LIMIT ?"
        params = (int(limit),)
    with get_connection(db_path) as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def list_tsbs_for_bike(
    make: str,
    model: str,
    year: Optional[int] = None,
    db_path: Optional[str] = None,
) -> list[dict]:
    """Return TSBs applicable to a specific (make, model, year) bike.

    Match rules:
      - ``make`` lowercased both sides.
      - DB row's ``model_pattern`` is the SQL LIKE pattern; the bike's
        concrete model is the LHS (``? LIKE model_pattern``).
      - ``year`` filters on ``(year_min IS NULL OR year >= year_min)
        AND (year_max IS NULL OR year <= year_max)`` when supplied;
        when omitted, year bounds are ignored.

    Python-side post-sort by pattern specificity (narrowest first),
    then ``issued_date DESC``.
    """
    if not make or not model:
        return []
    normalized_make = str(make).strip().lower()
    normalized_model = str(model).strip()

    params: list = [normalized_make, normalized_model]
    sql = (
        "SELECT * FROM technical_service_bulletins "
        "WHERE make = ? AND ? LIKE model_pattern"
    )
    if year is not None:
        sql += (
            " AND (year_min IS NULL OR ? >= year_min)"
            " AND (year_max IS NULL OR ? <= year_max)"
        )
        params.extend([int(year), int(year)])

    with get_connection(db_path) as conn:
        rows = [dict(row) for row in conn.execute(sql, params).fetchall()]

    rows.sort(
        key=lambda r: (
            _pattern_specificity(r.get("model_pattern") or ""),
            # Invert issued_date for DESC sort.
            -_date_sort_key(r.get("issued_date") or ""),
            int(r.get("id") or 0),
        )
    )
    return rows


def _date_sort_key(iso_date: str) -> int:
    """Turn an ISO date string into a sortable int (YYYYMMDD)."""
    if not iso_date:
        return 0
    try:
        parts = iso_date.split("-")
        return int(parts[0]) * 10000 + int(parts[1]) * 100 + int(parts[2])
    except (ValueError, IndexError):
        return 0


def search_tsbs(
    query: str,
    make: Optional[str] = None,
    limit: Optional[int] = None,
    db_path: Optional[str] = None,
) -> list[dict]:
    """Case-insensitive LIKE search across title + description + fix_procedure.

    Empty query short-circuits to ``[]`` (no full-table dump).
    """
    if query is None:
        return []
    normalized_query = str(query).strip()
    if not normalized_query:
        return []
    like_pattern = f"%{normalized_query}%"

    params: list = [like_pattern, like_pattern, like_pattern]
    sql = (
        "SELECT * FROM technical_service_bulletins "
        "WHERE (title LIKE ? OR description LIKE ? OR fix_procedure LIKE ?)"
    )
    if make:
        sql += " AND make = ?"
        params.append(str(make).strip().lower())
    sql += " ORDER BY issued_date DESC, id DESC"
    if limit is not None:
        sql += " LIMIT ?"
        params.append(int(limit))

    with get_connection(db_path) as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def count_tsbs(db_path: Optional[str] = None) -> int:
    """Return the total number of TSB rows. 0 on a missing table."""
    try:
        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM technical_service_bulletins"
            ).fetchone()
            return int(row[0]) if row else 0
    except sqlite3.OperationalError:
        return 0


def tsb_numbers_for_vehicle(
    make: str,
    model: str,
    year: Optional[int] = None,
    severity: Optional[str] = None,
    db_path: Optional[str] = None,
) -> list[str]:
    """Phase 148 hook — return the TSB numbers that apply to a vehicle.

    When ``severity`` is supplied, only returns TSBs in that severity
    band OR one bucket up/down (bucket-adjacent match). Graceful on
    a pre-migration-022 DB: catches ``sqlite3.OperationalError`` on
    the first query and returns ``[]``.
    """
    try:
        rows = list_tsbs_for_bike(
            make=make, model=model, year=year, db_path=db_path,
        )
    except sqlite3.OperationalError:
        return []

    if severity:
        normalized_severity = str(severity).strip().lower()
        target_weight = _SEVERITY_ORDER.get(normalized_severity, 0)
        if target_weight:
            rows = [
                r for r in rows
                if abs(
                    _SEVERITY_ORDER.get((r.get("severity") or "").lower(), 0)
                    - target_weight
                ) <= 1
            ]
    return [r["tsb_number"] for r in rows if r.get("tsb_number")]


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def load_tsbs_file(
    path: str,
    db_path: Optional[str] = None,
) -> int:
    """Load a TSBs JSON file into the DB. Returns rows processed.

    Idempotent: ``add_tsb`` uses INSERT OR IGNORE on ``tsb_number``.
    Re-running against the same file produces the same DB state.

    Malformed JSON raises ``ValueError`` with the filename + line:col
    pulled from the stdlib ``JSONDecodeError``. Invalid row fields
    (bad severity / non-ISO date / empty tsb_number) propagate as
    ``ValueError`` from ``add_tsb``.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"TSB data file not found: {file_path}")
    raw = file_path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{file_path.name}: malformed JSON at line {exc.lineno}, "
            f"col {exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(data, list):
        raise ValueError(
            f"{file_path.name}: expected a JSON array at the top level, "
            f"got {type(data).__name__}"
        )

    count = 0
    for row in data:
        add_tsb(
            tsb_number=row["tsb_number"],
            make=row["make"],
            model_pattern=row["model_pattern"],
            title=row["title"],
            description=row.get("description", ""),
            fix_procedure=row.get("fix_procedure", ""),
            year_min=row.get("year_min"),
            year_max=row.get("year_max"),
            severity=row.get("severity", "medium"),
            issued_date=row.get("issued_date"),
            source_url=row.get("source_url"),
            verified_by=row.get("verified_by"),
            db_path=db_path,
        )
        count += 1
    return count


__all__ = [
    "VALID_SEVERITIES",
    "add_tsb",
    "get_tsb",
    "list_tsbs",
    "list_tsbs_for_bike",
    "search_tsbs",
    "count_tsbs",
    "tsb_numbers_for_vehicle",
    "load_tsbs_file",
]
