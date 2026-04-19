"""Parts cross-reference repository — CRUD over ``parts`` + ``parts_xref``.

Phase 153. Sixth Track F phase. OEM ↔ aftermarket parts cross-reference
with curated equivalence ratings. Mechanic sees ``HD-26499-08`` (Twin Cam
cam tensioner) and asks for alternatives — the repo returns the Feuling
4124 and S&S 33-4220 drop-ins ranked by equivalence_rating then cost.

The module also exposes :func:`lookup_typical_cost`, the opportunistic
hook used by the Phase 148 predictor to populate
``FailurePrediction.parts_cost_cents`` without introducing a hard
dependency: the predictor imports this module through a try/except so
Phase 148's 44-test regression stays green even when the parts table
is empty or the migration has not yet been applied.

Design notes
------------

- **INSERT OR IGNORE on slug.** Re-seeding is idempotent — the loader
  can run ``seed_all`` repeatedly without mutating existing rows. The
  existing id is returned on duplicate so the xref loader can still
  resolve its foreign keys.

- **Lowercase-on-insert for make.** SQLite's LIKE is case-insensitive
  for ASCII, but we normalise anyway so equality joins (``make = ?``)
  also work regardless of the caller's casing. Matches the Phase 145
  compat pattern.

- **Ranking is rating-first.** ``get_xrefs`` returns rows sorted
  rating DESC → cost ASC → brand ASC → id ASC. A shop mechanic looking
  at a tensioner replacement wants the 5-star drop-in at the top;
  within a tier the cheapest drop-in wins; within the same price the
  alphabetical brand order keeps the view deterministic across
  SQLite versions.

- **Self-xref rejected at two layers.** The CHECK constraint in
  migration 021 is the last line of defence, but :func:`add_xref`
  catches self-reference in Python first so the CLI and tests get a
  clean ValueError rather than SQLite's raw constraint-failed text.

- **Three-tier cost lookup.** :func:`lookup_typical_cost` tries the
  most precise match first: exact ``oem_part_number`` after
  alphanumeric normalisation (strips dashes/spaces so
  ``HD-26499-08`` matches ``HD2649908``). Falls back to a fuzzy LIKE
  over ``description`` (e.g. mechanic writes ``"cam tensioner"`` and
  the repo finds the HD-26499-08 row). Final fallback is keyword
  matching on make + category (e.g. ``"oil filter"`` on a Honda
  returns the 15410-MCJ-505 row). Returns ``None`` when all three
  tiers miss — the predictor callers treat None as "no estimate
  available" rather than zero cost.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any, List, Optional

from motodiag.core.database import get_connection


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


#: Valid equivalence_rating range. Matches the CHECK constraint in
#: migration 021.
_RATING_MIN: int = 1
_RATING_MAX: int = 5


#: Category keywords used by :func:`lookup_typical_cost` tier 3 — if
#: the caller's ``part_name`` contains one of these substrings
#: (case-insensitive), the fallback narrows to that category.
_CATEGORY_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("oil filter", "oil-filter"),
    ("air filter", "air-filter"),
    ("brake pad", "brake-pads"),
    ("brake pads", "brake-pads"),
    ("tensioner", "cam-tensioner"),
    ("stator", "stator"),
    ("clutch", "clutch"),
    ("water pump", "water-pump"),
    ("doohickey", "balancer-tensioner"),
    ("sprocket", "sprocket"),
    ("chain", "chain"),
    ("seal", "seal"),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_rating(rating: int) -> int:
    """Clamp-check equivalence_rating to [1, 5] or raise ValueError."""
    if isinstance(rating, bool) or not isinstance(rating, int):
        raise ValueError(
            f"equivalence_rating must be an int in [{_RATING_MIN}..{_RATING_MAX}] "
            f"(got {type(rating).__name__} {rating!r})"
        )
    if rating < _RATING_MIN or rating > _RATING_MAX:
        raise ValueError(
            f"equivalence_rating must be in [{_RATING_MIN}..{_RATING_MAX}] "
            f"(got {rating})"
        )
    return rating


def _validate_cost(cost: int) -> int:
    """Check cost_cents is an int >= 0 or raise TypeError/ValueError."""
    # bool subclasses int — reject explicitly so True/False don't
    # silently become 1/0 (mechanic typo catcher, matches Phase 145).
    if isinstance(cost, bool) or not isinstance(cost, int):
        raise TypeError(
            f"typical_cost_cents must be an int (got "
            f"{type(cost).__name__} {cost!r})"
        )
    if cost < 0:
        raise ValueError(
            f"typical_cost_cents must be >= 0 (got {cost})"
        )
    return cost


def _normalize_make(make: str) -> str:
    """Lowercase + strip; raise ValueError on empty."""
    if make is None:
        raise ValueError("make must not be None")
    normalized = str(make).strip().lower()
    if not normalized:
        raise ValueError("make must not be empty")
    return normalized


def _alnum(text: str) -> str:
    """Return ``text`` reduced to ASCII alphanumerics, uppercased.

    Used by the tier-1 ``lookup_typical_cost`` match so ``HD-26499-08``
    normalises to ``HD2649908`` and will match a user-typed
    ``hd 26499 08`` or ``hd2649908`` without a separate index.
    """
    if not text:
        return ""
    return re.sub(r"[^A-Za-z0-9]+", "", str(text)).upper()


def _row_to_dict(row) -> dict:
    """Turn a sqlite3.Row into a plain dict."""
    return dict(row) if row is not None else None


# ---------------------------------------------------------------------------
# Parts CRUD
# ---------------------------------------------------------------------------


def add_part(
    slug: str,
    oem_part_number: Optional[str],
    brand: str,
    description: str,
    category: str,
    make: str,
    model_pattern: str,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    typical_cost_cents: int = 0,
    purchase_url: Optional[str] = None,
    notes: Optional[str] = None,
    verified_by: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    """Insert a part; return existing id on duplicate slug.

    Validates ``typical_cost_cents`` in Python before touching SQL so
    callers (and :mod:`parts_loader`) get a clean TypeError/ValueError
    rather than SQLite's raw ``CHECK constraint failed`` text. Returns
    the part id in either the freshly-inserted or duplicate-slug case.

    ``make`` is lowercased on insert; other fields are passed through
    verbatim (model_pattern keeps its wildcards, brand keeps its case).
    """
    if not slug:
        raise ValueError("slug must not be empty")
    typical_cost_cents = _validate_cost(typical_cost_cents)
    norm_make = _normalize_make(make)

    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT OR IGNORE INTO parts
               (slug, oem_part_number, brand, description, category,
                make, model_pattern, year_min, year_max,
                typical_cost_cents, purchase_url, notes, verified_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                slug, oem_part_number, brand, description, category,
                norm_make, model_pattern, year_min, year_max,
                typical_cost_cents, purchase_url, notes, verified_by,
            ),
        )
        cursor = conn.execute(
            "SELECT id FROM parts WHERE slug = ?", (slug,),
        )
        row = cursor.fetchone()
        return int(row[0]) if row else 0


def get_part(slug: str, db_path: Optional[str] = None) -> Optional[dict]:
    """Return the part row dict for a slug, or ``None`` if not found."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM parts WHERE slug = ?", (slug,),
        )
        return _row_to_dict(cursor.fetchone())


def get_part_by_oem(
    oem_part_number: str, db_path: Optional[str] = None,
) -> Optional[dict]:
    """Return a part row by its OEM part number, or ``None``.

    Exact match on ``oem_part_number``. Use
    :func:`search_parts` for fuzzy lookup.
    """
    if not oem_part_number:
        return None
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM parts WHERE oem_part_number = ? "
            "ORDER BY id LIMIT 1",
            (oem_part_number,),
        )
        return _row_to_dict(cursor.fetchone())


def search_parts(
    query: str,
    make: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 20,
    db_path: Optional[str] = None,
) -> list[dict]:
    """Fuzzy LIKE search across oem_part_number, description, brand, make.

    Case-insensitive (SQLite LIKE is CI on ASCII). Optional ``make``
    and ``category`` filters narrow the result set. Returns up to
    ``limit`` rows ordered by brand then id for determinism.
    """
    q = f"%{(query or '').strip()}%"
    sql_parts = [
        "SELECT * FROM parts WHERE (",
        "  oem_part_number LIKE ? OR ",
        "  description LIKE ? OR ",
        "  brand LIKE ? OR ",
        "  make LIKE ?",
        ")",
    ]
    params: list = [q, q, q, q]
    if make:
        sql_parts.append("AND make = ?")
        params.append(_normalize_make(make))
    if category:
        sql_parts.append("AND category = ?")
        params.append(category)
    sql_parts.append("ORDER BY brand COLLATE NOCASE, id LIMIT ?")
    params.append(int(limit))
    sql = " ".join(sql_parts)

    with get_connection(db_path) as conn:
        cursor = conn.execute(sql, params)
        return [_row_to_dict(r) for r in cursor.fetchall()]


def list_parts_for_bike(
    make: str,
    model: str,
    year: Optional[int] = None,
    category: Optional[str] = None,
    db_path: Optional[str] = None,
) -> list[dict]:
    """List parts whose (make, model_pattern, year-range) covers a bike.

    Uses SQL LIKE so one row with ``model_pattern='Sportster%'`` covers
    the whole Sportster family. Year filter applies when the row has
    a bounded range — an unbounded row matches any year.
    """
    norm_make = _normalize_make(make)
    # Use the vehicle's model name against the pattern (reverse LIKE):
    # the stored `model_pattern` may contain wildcards, so we build the
    # query so that ? LIKE model_pattern is true.
    sql_parts = [
        "SELECT * FROM parts WHERE make = ? AND ? LIKE model_pattern",
    ]
    params: list = [norm_make, model]
    if year is not None:
        sql_parts.append(
            "AND (year_min IS NULL OR year_min <= ?) "
            "AND (year_max IS NULL OR year_max >= ?)"
        )
        params.extend([int(year), int(year)])
    if category:
        sql_parts.append("AND category = ?")
        params.append(category)
    sql_parts.append("ORDER BY category, brand COLLATE NOCASE, id")
    sql = " ".join(sql_parts)

    with get_connection(db_path) as conn:
        cursor = conn.execute(sql, params)
        return [_row_to_dict(r) for r in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Cross-reference CRUD
# ---------------------------------------------------------------------------


def add_xref(
    oem_slug: str,
    aftermarket_slug: str,
    equivalence_rating: int = 3,
    notes: Optional[str] = None,
    source_url: Optional[str] = None,
    submitted_by_user_id: int = 1,
    db_path: Optional[str] = None,
) -> int:
    """Insert a cross-reference pair; INSERT OR IGNORE on UNIQUE pair.

    Returns the xref id for freshly-inserted or duplicate-pair cases.
    Rejects self-reference in Python (``oem_slug == aftermarket_slug``)
    before touching SQL so callers get a clean ValueError; the CHECK
    constraint in migration 021 is the last line of defence for direct
    INSERTs that bypass this helper.
    """
    if not oem_slug:
        raise ValueError("oem_slug must not be empty")
    if not aftermarket_slug:
        raise ValueError("aftermarket_slug must not be empty")
    if oem_slug == aftermarket_slug:
        raise ValueError(
            f"self-reference rejected: oem_slug == aftermarket_slug "
            f"({oem_slug!r})"
        )
    equivalence_rating = _validate_rating(equivalence_rating)

    with get_connection(db_path) as conn:
        oem_row = conn.execute(
            "SELECT id FROM parts WHERE slug = ?", (oem_slug,),
        ).fetchone()
        if oem_row is None:
            raise ValueError(
                f"add_xref: unknown oem_slug {oem_slug!r}"
            )
        aft_row = conn.execute(
            "SELECT id FROM parts WHERE slug = ?", (aftermarket_slug,),
        ).fetchone()
        if aft_row is None:
            raise ValueError(
                f"add_xref: unknown aftermarket_slug {aftermarket_slug!r}"
            )
        oem_id = int(oem_row[0])
        aft_id = int(aft_row[0])
        if oem_id == aft_id:
            # Guard against distinct slugs that happen to share an id
            # (shouldn't happen given UNIQUE(slug) but belt-and-braces).
            raise ValueError(
                "self-reference rejected: oem_part_id == aftermarket_part_id"
            )

        conn.execute(
            """INSERT OR IGNORE INTO parts_xref
               (oem_part_id, aftermarket_part_id, equivalence_rating,
                notes, source_url, submitted_by_user_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                oem_id, aft_id, equivalence_rating,
                notes, source_url, submitted_by_user_id,
            ),
        )
        cursor = conn.execute(
            "SELECT id FROM parts_xref "
            "WHERE oem_part_id = ? AND aftermarket_part_id = ?",
            (oem_id, aft_id),
        )
        row = cursor.fetchone()
        return int(row[0]) if row else 0


def get_xrefs(
    oem_part_number: str,
    min_rating: int = 1,
    db_path: Optional[str] = None,
) -> list[dict]:
    """Return aftermarket alternatives for an OEM part, ranked.

    Sort order: equivalence_rating DESC → typical_cost_cents ASC →
    brand ASC → id ASC. The mechanic sees the best drop-in at the top;
    within a tier the cheapest wins; within the same price the
    alphabetical brand keeps results deterministic across SQLite
    versions.

    ``min_rating`` filters out low-equivalence rows — a shop may want
    to hide 1-2 star "related only" entries when building a bill of
    materials.
    """
    if not oem_part_number:
        return []
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """SELECT
                   x.id AS xref_id,
                   x.equivalence_rating,
                   x.notes AS xref_notes,
                   x.source_url,
                   x.submitted_by_user_id,
                   aft.id AS aftermarket_part_id,
                   aft.slug AS aftermarket_slug,
                   aft.oem_part_number AS aftermarket_part_number,
                   aft.brand AS aftermarket_brand,
                   aft.description AS aftermarket_description,
                   aft.category AS aftermarket_category,
                   aft.typical_cost_cents AS aftermarket_cost_cents,
                   aft.purchase_url AS aftermarket_purchase_url,
                   aft.notes AS aftermarket_notes,
                   aft.verified_by AS aftermarket_verified_by,
                   oem.slug AS oem_slug,
                   oem.oem_part_number AS oem_part_number,
                   oem.brand AS oem_brand,
                   oem.description AS oem_description
               FROM parts_xref x
               JOIN parts oem ON oem.id = x.oem_part_id
               JOIN parts aft ON aft.id = x.aftermarket_part_id
               WHERE oem.oem_part_number = ?
                 AND x.equivalence_rating >= ?
               ORDER BY x.equivalence_rating DESC,
                        aft.typical_cost_cents ASC,
                        aft.brand COLLATE NOCASE ASC,
                        x.id ASC""",
            (oem_part_number, int(min_rating)),
        )
        return [_row_to_dict(r) for r in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Phase 148 hook
# ---------------------------------------------------------------------------


def lookup_typical_cost(
    part_name: str,
    make: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Optional[int]:
    """Best-effort typical-cost lookup for a user-provided part name.

    Three-tier fallback:

    1. **Exact OEM match** — normalise ``part_name`` to alphanumerics
       (``HD-26499-08`` → ``HD2649908``) and compare against every
       part's normalised ``oem_part_number``. First hit wins.
    2. **Description LIKE** — fuzzy substring match on
       ``description``, narrowed by ``make`` when supplied.
    3. **Category keyword** — if the part name contains one of
       :data:`_CATEGORY_KEYWORDS` (e.g. ``"oil filter"``), narrow
       the search to that category within the make.

    Returns the first matching ``typical_cost_cents`` or ``None`` when
    all three tiers miss. ``None`` means "no estimate available" — the
    Phase 148 predictor treats this as an absent cost rather than zero.
    Also returns ``None`` when ``part_name`` is empty/None.
    """
    if not part_name:
        return None
    name_stripped = str(part_name).strip()
    if not name_stripped:
        return None

    try:
        with get_connection(db_path) as conn:
            # --- Tier 1: exact OEM match after alphanumeric norm ---
            name_alnum = _alnum(name_stripped)
            if name_alnum:
                rows = conn.execute(
                    "SELECT oem_part_number, typical_cost_cents "
                    "FROM parts WHERE oem_part_number IS NOT NULL"
                ).fetchall()
                for r in rows:
                    if _alnum(r["oem_part_number"] or "") == name_alnum:
                        cost = r["typical_cost_cents"]
                        if cost is not None and int(cost) > 0:
                            return int(cost)

            # --- Tier 2: description LIKE ---
            like = f"%{name_stripped}%"
            sql = (
                "SELECT typical_cost_cents FROM parts "
                "WHERE description LIKE ?"
            )
            params: list = [like]
            if make:
                sql += " AND make = ?"
                params.append(_normalize_make(make))
            sql += (
                " AND typical_cost_cents > 0 "
                "ORDER BY typical_cost_cents ASC LIMIT 1"
            )
            row = conn.execute(sql, params).fetchone()
            if row is not None:
                return int(row["typical_cost_cents"])

            # --- Tier 3: category keyword + make ---
            if make:
                name_lc = name_stripped.lower()
                for kw, cat in _CATEGORY_KEYWORDS:
                    if kw in name_lc:
                        row = conn.execute(
                            "SELECT typical_cost_cents FROM parts "
                            "WHERE make = ? AND category = ? "
                            "AND typical_cost_cents > 0 "
                            "ORDER BY typical_cost_cents ASC LIMIT 1",
                            (_normalize_make(make), cat),
                        ).fetchone()
                        if row is not None:
                            return int(row["typical_cost_cents"])

    except sqlite3.OperationalError:
        # Parts table may not exist yet (migration 021 not applied).
        # Phase 148 regression safety: return None rather than crash.
        return None

    return None


__all__ = [
    "add_part",
    "get_part",
    "get_part_by_oem",
    "search_parts",
    "list_parts_for_bike",
    "add_xref",
    "get_xrefs",
    "lookup_typical_cost",
]
