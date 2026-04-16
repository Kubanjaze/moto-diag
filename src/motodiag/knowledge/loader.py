"""Knowledge base loader — import DTC codes and other data from JSON files."""

import json
from pathlib import Path

from motodiag.core.models import DTCCode, SymptomCategory, Severity
from motodiag.knowledge.dtc_repo import add_dtc


def load_dtc_file(file_path: str | Path, db_path: str | None = None) -> int:
    """Load DTCs from a JSON file into the database.

    JSON format: array of objects with keys matching DTCCode fields.
    Returns number of DTCs loaded.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"DTC file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array, got {type(data).__name__}")

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
