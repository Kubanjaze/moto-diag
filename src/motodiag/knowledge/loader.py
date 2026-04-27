"""Knowledge base loader — import DTC codes and other data from JSON files."""

import json
from pathlib import Path

from motodiag.core.models import DTCCode, SymptomCategory, Severity
from motodiag.knowledge.dtc_repo import add_dtc
from motodiag.knowledge.symptom_repo import add_symptom
from motodiag.knowledge.issues_repo import add_known_issue


def load_dtc_file(file_path: str | Path, db_path: str | None = None) -> int:
    """Load DTCs from a JSON file into the database.

    JSON format: array of objects with keys matching DTCCode fields.
    Returns number of DTCs loaded.

    Phase 190 commit 8 (Bug 3a fix). Pre-deletes existing rows
    matching the (code, make) pairs in the file before inserting,
    so re-seeding the same file is idempotent. Necessary because
    SQLite's UNIQUE(code, make) constraint on `dtc_codes` does NOT
    catch duplicates when `make IS NULL` (NULL is not equal to NULL
    in UNIQUE semantics) — without this pre-delete, every
    `motodiag db init` (or any caller of this loader) would insert
    another copy of every generic row, accumulating duplicates and
    breaking direct-lookup determinism. Existing dev DBs that
    accumulated duplicates pre-fix self-clean on the next
    re-seed via this pre-delete.
    """
    from motodiag.core.database import get_connection

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"DTC file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array, got {type(data).__name__}")

    # Pre-delete any rows that match (code, make) pairs about to be
    # inserted. This is the dedupe step — UNIQUE(code, make) doesn't
    # enforce uniqueness for NULL-make rows, so we have to clean
    # them ourselves before INSERT OR REPLACE runs. Done in one
    # transaction so a partial seed leaves the DB at the prior
    # committed state.
    with get_connection(db_path) as conn:
        for item in data:
            code = str(item["code"]).upper()
            make = item.get("make")
            if make is None:
                conn.execute(
                    "DELETE FROM dtc_codes WHERE code = ? AND make IS NULL",
                    (code,),
                )
            else:
                conn.execute(
                    "DELETE FROM dtc_codes WHERE code = ? AND make = ?",
                    (code, make),
                )

    count = 0
    for item in data:
        dtc = DTCCode(
            code=item["code"],
            description=item["description"],
            category=SymptomCategory(item.get("category", "other")),
            severity=Severity(item.get("severity", "medium")),
            make=item.get("make"),
            common_causes=item.get("common_causes", []),
            fix_summary=item.get("fix_summary"),
        )
        add_dtc(dtc, db_path)
        count += 1

    return count


def load_dtc_directory(dir_path: str | Path, db_path: str | None = None) -> dict[str, int]:
    """Load all .json DTC files from a directory.

    Returns dict of {filename: count_loaded}.
    """
    path = Path(dir_path)
    if not path.is_dir():
        raise NotADirectoryError(f"Not a directory: {path}")

    results = {}
    for json_file in sorted(path.glob("*.json")):
        count = load_dtc_file(json_file, db_path)
        results[json_file.name] = count

    return results


def load_symptom_file(file_path: str | Path, db_path: str | None = None) -> int:
    """Load symptoms from a JSON file into the database.

    JSON format: array of objects with name, description, category, related_systems.
    Returns number of symptoms loaded.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Symptom file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array, got {type(data).__name__}")

    count = 0
    for item in data:
        add_symptom(
            name=item["name"],
            description=item["description"],
            category=item.get("category", "other"),
            related_systems=item.get("related_systems", []),
            db_path=db_path,
        )
        count += 1

    return count


def load_known_issues_file(file_path: str | Path, db_path: str | None = None) -> int:
    """Load known issues from a JSON file into the database.

    JSON format: array of objects matching add_known_issue() parameters.
    Returns number of issues loaded.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Known issues file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array, got {type(data).__name__}")

    count = 0
    for item in data:
        add_known_issue(
            title=item["title"],
            description=item["description"],
            make=item.get("make"),
            model=item.get("model"),
            year_start=item.get("year_start"),
            year_end=item.get("year_end"),
            severity=item.get("severity", "medium"),
            symptoms=item.get("symptoms", []),
            dtc_codes=item.get("dtc_codes", []),
            causes=item.get("causes", []),
            fix_procedure=item.get("fix_procedure"),
            parts_needed=item.get("parts_needed", []),
            estimated_hours=item.get("estimated_hours"),
            db_path=db_path,
        )
        count += 1

    return count
