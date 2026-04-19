"""JSON seeder for the Phase 153 parts cross-reference database.

Two input files live under ``data/`` next to this module:

- ``parts.json`` — an array of part objects matching
  :func:`motodiag.advanced.parts_repo.add_part` kwargs.
- ``parts_xref.json`` — an array of xref objects matching
  :func:`motodiag.advanced.parts_repo.add_xref` kwargs.

Both file-level loaders are idempotent — :func:`add_part` uses
``INSERT OR IGNORE`` on slug, and :func:`add_xref` does the same on
``UNIQUE(oem_part_id, aftermarket_part_id)``. Running :func:`seed_all`
twice produces identical state; the second run inserts zero new rows.

Dependency order: parts first, xref second. ``parts_xref.json``'s
``oem_slug`` + ``aftermarket_slug`` fields must resolve to rows
already in the ``parts`` table or :func:`add_xref` raises
``ValueError``. :func:`seed_all` enforces this order so a single call
sets up the whole knowledge base from scratch.

Malformed JSON surfaces as a :class:`ValueError` containing the
filename + JSON line/column position — the raw
:class:`json.JSONDecodeError` exposes ``lineno`` and ``colno`` which
we pass straight through so a mechanic editing a file on a shop
laptop gets a pointer to the exact character that broke parsing
(same ergonomic contract as the Phase 145 compat loader).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from motodiag.advanced.parts_repo import add_part, add_xref


#: Default data directory — ``advanced/data`` next to this module. The
#: directory is created/maintained by Phases 151/152/153 and is
#: shared across those loaders.
DEFAULT_DATA_DIR: Path = Path(__file__).parent / "data"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_json_array(path: Path) -> list[dict]:
    """Parse a JSON file and return its top-level array.

    Raises
    ------
    FileNotFoundError
        If ``path`` does not exist.
    ValueError
        If the file is malformed JSON or the top-level value is not
        a list. The message always includes the filename and (for
        malformed JSON) the line/column reported by the stdlib parser.
    """
    if not path.exists():
        raise FileNotFoundError(f"parts data file not found: {path}")
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path.name}: malformed JSON at line {exc.lineno}, "
            f"col {exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(data, list):
        raise ValueError(
            f"{path.name}: expected a JSON array at the top level, "
            f"got {type(data).__name__}"
        )
    return data


# ---------------------------------------------------------------------------
# Per-file loaders
# ---------------------------------------------------------------------------


def load_parts_file(
    path: Path,
    db_path: Optional[str] = None,
) -> int:
    """Load a ``parts.json`` file; return rows processed.

    The return value counts input rows (not distinct inserts) — a
    second run against the same file returns the same count even
    though every row was a duplicate. Mechanics auditing the output
    should query the parts table before/after to see what actually
    landed.
    """
    data = _load_json_array(Path(path))
    count = 0
    for row in data:
        add_part(
            slug=row["slug"],
            oem_part_number=row.get("oem_part_number"),
            brand=row["brand"],
            description=row["description"],
            category=row["category"],
            make=row["make"],
            model_pattern=row["model_pattern"],
            year_min=row.get("year_min"),
            year_max=row.get("year_max"),
            typical_cost_cents=row.get("typical_cost_cents", 0),
            purchase_url=row.get("purchase_url"),
            notes=row.get("notes"),
            verified_by=row.get("verified_by"),
            db_path=db_path,
        )
        count += 1
    return count


def load_parts_xref_file(
    path: Path,
    db_path: Optional[str] = None,
) -> int:
    """Load a ``parts_xref.json`` file; return rows processed.

    Each row must carry ``oem_slug`` + ``aftermarket_slug`` fields
    that resolve to already-seeded parts. :func:`add_xref` raises
    ``ValueError`` with the unknown slug in the message when a row
    refers to a missing part — dependency order matters.
    """
    data = _load_json_array(Path(path))
    count = 0
    for row in data:
        add_xref(
            oem_slug=row["oem_slug"],
            aftermarket_slug=row["aftermarket_slug"],
            equivalence_rating=row.get("equivalence_rating", 3),
            notes=row.get("notes"),
            source_url=row.get("source_url"),
            submitted_by_user_id=row.get("submitted_by_user_id", 1),
            db_path=db_path,
        )
        count += 1
    return count


# ---------------------------------------------------------------------------
# Full seed
# ---------------------------------------------------------------------------


def seed_all(
    data_dir: Optional[Path] = None,
    db_path: Optional[str] = None,
) -> dict[str, int]:
    """Load both JSON files from ``data_dir`` in dependency order.

    Dependency order: parts → xref. ``parts_xref`` rows reference
    ``parts`` by slug, so parts must be seeded first.

    Returns
    -------
    dict
        Keys ``parts``, ``xref`` → rows processed. Missing JSON files
        are reported as 0 without raising, so a partial install (e.g.
        a fresh clone with only ``parts.json`` populated) still seeds
        what's available.
    """
    data_dir = Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR
    summary: dict[str, int] = {"parts": 0, "xref": 0}

    parts_path = data_dir / "parts.json"
    if parts_path.exists():
        summary["parts"] = load_parts_file(parts_path, db_path=db_path)

    xref_path = data_dir / "parts_xref.json"
    if xref_path.exists():
        summary["xref"] = load_parts_xref_file(xref_path, db_path=db_path)

    return summary


__all__ = [
    "DEFAULT_DATA_DIR",
    "load_parts_file",
    "load_parts_xref_file",
    "seed_all",
]
