"""JSON seeder for the Phase 145 adapter compatibility database.

Three input files live under ``compat_data/`` next to this module:

- ``adapters.json`` — an array of adapter objects matching
  :func:`motodiag.hardware.compat_repo.add_adapter` kwargs.
- ``compat_matrix.json`` — an array of compat row objects matching
  :func:`motodiag.hardware.compat_repo.add_compatibility` kwargs.
- ``compat_notes.json`` — an array of note objects matching
  :func:`motodiag.hardware.compat_repo.add_compat_note` kwargs.

All three file-level loaders are idempotent — `add_adapter` uses
INSERT OR IGNORE on slug, and `add_compatibility` does a natural-key
lookup before INSERT. Running ``seed_all`` twice produces identical
state.

Malformed JSON surfaces as a :class:`ValueError` containing the
filename + JSON line/column position — the raw :class:`json.JSONDecodeError`
exposes ``lineno`` and ``colno`` which we pass straight through so
a mechanic editing a file on a shop laptop gets a pointer to the
exact character that broke parsing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from motodiag.hardware.compat_repo import (
    add_adapter,
    add_compat_note,
    add_compatibility,
)


DEFAULT_DATA_DIR: Path = Path(__file__).parent / "compat_data"


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
        raise FileNotFoundError(f"compat data file not found: {path}")
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


def load_adapters_file(
    path: Path,
    db_path: Optional[str] = None,
) -> int:
    """Load an ``adapters.json`` file; return rows processed.

    The return value counts input rows (not distinct inserts) — a
    second run against the same file returns the same count even
    though every row was a duplicate. Mechanics auditing the output
    should check ``list_adapters`` before/after to see what actually
    landed.
    """
    data = _load_json_array(Path(path))
    count = 0
    for row in data:
        add_adapter(
            slug=row["slug"],
            brand=row["brand"],
            model=row["model"],
            chipset=row["chipset"],
            transport=row["transport"],
            price_usd_cents=row.get("price_usd_cents", 0),
            supported_protocols_csv=row["supported_protocols_csv"],
            supports_bidirectional=row.get("supports_bidirectional", False),
            supports_mode22=row.get("supports_mode22", False),
            reliability_1to5=row.get("reliability_1to5", 3),
            purchase_url=row.get("purchase_url"),
            known_issues=row.get("known_issues"),
            notes=row.get("notes"),
            db_path=db_path,
        )
        count += 1
    return count


def load_compat_matrix_file(
    path: Path,
    db_path: Optional[str] = None,
) -> int:
    """Load a ``compat_matrix.json`` file; return rows processed."""
    data = _load_json_array(Path(path))
    count = 0
    for row in data:
        add_compatibility(
            adapter_slug=row["adapter_slug"],
            make=row["make"],
            model_pattern=row["model_pattern"],
            status=row["status"],
            year_min=row.get("year_min"),
            year_max=row.get("year_max"),
            notes=row.get("notes"),
            verified_by=row.get("verified_by"),
            db_path=db_path,
        )
        count += 1
    return count


def load_compat_notes_file(
    path: Path,
    db_path: Optional[str] = None,
) -> int:
    """Load a ``compat_notes.json`` file; return rows processed."""
    data = _load_json_array(Path(path))
    count = 0
    for row in data:
        add_compat_note(
            adapter_slug=row["adapter_slug"],
            make=row["make"],
            note_type=row["note_type"],
            body=row["body"],
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
    """Load all three JSON files from ``data_dir`` in dependency order.

    Dependency order: adapters → matrix → notes. The matrix and notes
    tables both FK to :class:`obd_adapters.id`, so the adapters file
    must be loaded first.

    Returns
    -------
    dict
        Keys ``adapters``, ``matrix``, ``notes`` → rows processed.
        Missing JSON files are reported as 0 without raising, so a
        partial install (e.g. a fresh clone with only adapters.json
        populated) still seeds what's available.
    """
    data_dir = Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR
    summary = {"adapters": 0, "matrix": 0, "notes": 0}

    adapters_path = data_dir / "adapters.json"
    if adapters_path.exists():
        summary["adapters"] = load_adapters_file(adapters_path, db_path=db_path)

    matrix_path = data_dir / "compat_matrix.json"
    if matrix_path.exists():
        summary["matrix"] = load_compat_matrix_file(matrix_path, db_path=db_path)

    notes_path = data_dir / "compat_notes.json"
    if notes_path.exists():
        summary["notes"] = load_compat_notes_file(notes_path, db_path=db_path)

    return summary


__all__ = [
    "DEFAULT_DATA_DIR",
    "load_adapters_file",
    "load_compat_matrix_file",
    "load_compat_notes_file",
    "seed_all",
]
