"""Phase 155 — NHTSA safety recall lookup.

Builds on the Phase 118 ``recalls`` substrate (schema-only, zero data)
and the Phase 155 migration 023 extension (nhtsa_id, vin_range, open
columns + recall_resolutions table). This module is the user-facing
repo layer: VIN decoding, VIN-range matching, open-recall listing per
bike, idempotent mark-resolved, seed-loader from
``advanced/data/recalls.json``.

Distinct from :mod:`motodiag.inventory.recall_repo` — that module is
the Phase 118 CRUD substrate and stays unchanged. This module is the
safety-recall specialization: NHTSA campaigns only, VIN-scoped
filtering, per-vehicle resolution tracking.

Design rules (Track F conventions):
  * Zero AI calls, zero network, zero token budget.
  * Graceful degradation: any OperationalError (missing tables, pre-
    migration-023 DB) falls through to ``[]`` so the Phase 148
    predictor hook never breaks predictive maintenance.
  * Idempotent loader: ``INSERT OR IGNORE`` on the partial-UNIQUE
    ``nhtsa_id`` so re-seeding is safe.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from motodiag.core.database import get_connection


# ---------------------------------------------------------------------------
# VIN decoding
# ---------------------------------------------------------------------------

# World Manufacturer Identifier (WMI) → make. Position 1-3 of a 17-char
# VIN identifies the manufacturer. Curated to the major motorcycle OEMs
# this project tracks. Keys are uppercase; callers normalize before
# lookup.
_WMI_TO_MAKE: dict[str, str] = {
    # Harley-Davidson
    "1HD": "Harley-Davidson",
    "5HD": "Harley-Davidson",
    # Honda
    "JH2": "Honda",
    "1HF": "Honda",
    "LAL": "Honda",
    # Suzuki
    "JS1": "Suzuki",
    "JSA": "Suzuki",
    # Yamaha
    "JYA": "Yamaha",
    "1YA": "Yamaha",
    # Kawasaki
    "JKA": "Kawasaki",
    "JKB": "Kawasaki",
    "1KA": "Kawasaki",
    # KTM
    "KM1": "KTM",
    "VBK": "KTM",
    # Ducati
    "ZDM": "Ducati",
    # Aprilia
    "ZD4": "Aprilia",
    # BMW Motorrad
    "WB1": "BMW",
    "WB2": "BMW",
    "WB3": "BMW",
    # Triumph
    "SMT": "Triumph",
    # Indian Motorcycle
    "56K": "Indian",
    "5FP": "Indian",
}

# Position-10 year-code character → base year. VINs cycle every 30
# years; we disambiguate by picking the candidate year closest to
# today (±1 tolerance). VIN position 10 skips I, O, Q, U, Z, 0 by
# NHTSA convention.
_YEAR_CODE_TO_BASE: dict[str, int] = {
    "A": 1980, "B": 1981, "C": 1982, "D": 1983, "E": 1984,
    "F": 1985, "G": 1986, "H": 1987, "J": 1988, "K": 1989,
    "L": 1990, "M": 1991, "N": 1992, "P": 1993, "R": 1994,
    "S": 1995, "T": 1996, "V": 1997, "W": 1998, "X": 1999,
    "Y": 2000,
    "1": 2001, "2": 2002, "3": 2003, "4": 2004, "5": 2005,
    "6": 2006, "7": 2007, "8": 2008, "9": 2009,
}

# VIN character set (per NHTSA): alphanumeric minus I, O, Q.
_VIN_INVALID_CHARS: set[str] = {"I", "O", "Q"}
_VIN_LENGTH: int = 17


def _is_valid_vin(vin: str) -> bool:
    """Return True if ``vin`` is 17 chars of uppercase alphanumeric
    minus I/O/Q. Case-normalization is the caller's job.
    """
    if not isinstance(vin, str):
        return False
    if len(vin) != _VIN_LENGTH:
        return False
    for ch in vin:
        if not ch.isalnum():
            return False
        if ch in _VIN_INVALID_CHARS:
            return False
    return True


def decode_vin(vin: str) -> dict:
    """Decode a 17-char VIN into a ``{make, year, wmi, year_code}`` dict.

    Parameters
    ----------
    vin : str
        17-character VIN. Case-insensitive; normalized to uppercase
        before lookup.

    Returns
    -------
    dict
        Keys ``make`` (str|None — None for unknown WMI), ``year``
        (int|None — None if year-code is U/Z/0 or otherwise unmapped),
        ``wmi`` (str, the 3-char prefix), ``year_code`` (str, the
        position-10 char).

    Raises
    ------
    ValueError
        If ``vin`` fails the length / charset validation.
    """
    if not isinstance(vin, str):
        raise ValueError(f"VIN must be a string, got {type(vin).__name__}")
    vin_upper = vin.strip().upper()
    if len(vin_upper) != _VIN_LENGTH:
        raise ValueError(
            f"VIN must be exactly {_VIN_LENGTH} characters; got "
            f"{len(vin_upper)}: {vin_upper!r}"
        )
    for ch in vin_upper:
        if not ch.isalnum():
            raise ValueError(
                f"VIN contains non-alphanumeric character {ch!r}: {vin_upper!r}"
            )
        if ch in _VIN_INVALID_CHARS:
            raise ValueError(
                f"VIN contains forbidden character {ch!r} (I/O/Q are "
                f"not allowed in NHTSA VINs): {vin_upper!r}"
            )

    wmi = vin_upper[:3]
    year_code = vin_upper[9]
    make = _WMI_TO_MAKE.get(wmi)
    year = _disambiguate_year(year_code)
    return {
        "make": make,
        "year": year,
        "wmi": wmi,
        "year_code": year_code,
    }


def _disambiguate_year(year_code: str) -> Optional[int]:
    """Map a VIN position-10 char to a 4-digit year, closest to today.

    VIN year codes cycle every 30 years: ``L`` is both 1990 and 2020.
    We resolve by picking the candidate year closest to the current
    year, within ±1 tolerance (so a 2024 build stamped with a code
    that nominally means 1994 still maps to 2024).
    """
    base = _YEAR_CODE_TO_BASE.get(year_code)
    if base is None:
        return None
    current = datetime.now().year
    # Two candidate years: base and base+30. Pick the one closest to
    # current year.
    candidates = [base, base + 30]
    # If current year is far beyond base+30, add another cycle (rare;
    # supports VINs stamped 2040+ during code lifetime).
    while candidates[-1] + 15 < current:
        candidates.append(candidates[-1] + 30)
    # Pick the candidate minimizing |candidate - current|.
    best = min(candidates, key=lambda y: abs(y - current))
    return best


# ---------------------------------------------------------------------------
# VIN-range matching
# ---------------------------------------------------------------------------


def _vin_in_range(vin: str, vin_range_json: Optional[str]) -> bool:
    """Return True if ``vin`` falls inside the ``vin_range`` spec.

    Parameters
    ----------
    vin : str
        Full 17-char VIN (validated by caller).
    vin_range_json : str or None
        Either ``None`` (all-VIN campaign — always True), or a JSON
        string encoding a list of ``[prefix_start, prefix_end]``
        tuples. A VIN matches if its uppercase prefix is >= start and
        <= end for ANY tuple (lexicographic / prefix compare).

    Returns
    -------
    bool
        True if the recall applies to this VIN.
    """
    if vin_range_json is None:
        return True
    try:
        spec = json.loads(vin_range_json)
    except (TypeError, ValueError):
        # Malformed spec — conservative: treat as all-VIN so the
        # mechanic sees the recall even if the data is suspect. Better
        # to over-flag than silently drop a safety recall.
        return True
    if not isinstance(spec, list) or not spec:
        return True
    vin_upper = vin.upper()
    for entry in spec:
        if not (isinstance(entry, (list, tuple)) and len(entry) == 2):
            continue
        start = str(entry[0]).upper()
        end = str(entry[1]).upper()
        # Compare VIN prefix lexicographically. Use max(len(start),
        # len(end)) to get consistent prefix length.
        prefix_len = max(len(start), len(end))
        vin_prefix = vin_upper[:prefix_len]
        # Pad start/end to prefix_len for clean compare.
        if start <= vin_prefix <= end:
            return True
    return False


# ---------------------------------------------------------------------------
# Core query API
# ---------------------------------------------------------------------------


def check_vin(vin: str, db_path: Optional[str] = None) -> list[dict]:
    """Look up open NHTSA recalls for a VIN.

    Validates + decodes the VIN, queries recalls scoped to the decoded
    make/year, filters by VIN range match, filters by ``open=1``,
    dedupes by ``nhtsa_id``. Returns an ordered list of recall dicts.

    Parameters
    ----------
    vin : str
        17-char VIN.
    db_path : str, optional
        Override the default database path (used by tests).

    Returns
    -------
    list[dict]
        Dict rows from the recalls table. Ordered by severity DESC,
        then nhtsa_id. Empty list if VIN can't be decoded (unknown
        WMI) or no recalls apply.

    Raises
    ------
    ValueError
        If the VIN fails length / charset validation.
    """
    decoded = decode_vin(vin)
    make = decoded.get("make")
    year = decoded.get("year")

    if make is None:
        # Unknown WMI — we can't match recalls without a make filter.
        # Returning empty is safer than scanning all recalls.
        return []

    # Use the inventory repo's list helper for the make/year query,
    # then post-filter by vin_range + open.
    try:
        from motodiag.inventory.recall_repo import list_recalls_for_vehicle
        candidates = list_recalls_for_vehicle(
            make=make, model=None, year=year, db_path=db_path,
        )
    except sqlite3.OperationalError:
        # Pre-migration-011 or corrupt DB — degrade gracefully.
        return []

    matched: list[dict] = []
    seen_nhtsa: set[str] = set()
    for row in candidates:
        # Only surface rows flagged open=1. Phase 118 NULL-open rows
        # (pre-migration-023) are defaulted to 1 by ALTER; post-
        # migration rows carry explicit values.
        if row.get("open") == 0:
            continue
        if not _vin_in_range(vin, row.get("vin_range")):
            continue
        nhtsa_id = row.get("nhtsa_id")
        if nhtsa_id and nhtsa_id in seen_nhtsa:
            continue
        if nhtsa_id:
            seen_nhtsa.add(nhtsa_id)
        matched.append(dict(row))
    return matched


def list_open_for_bike(
    vehicle_id: int, db_path: Optional[str] = None,
) -> list[dict]:
    """List open recalls that apply to a garage bike, excluding resolved.

    LEFT JOINs recalls against recall_resolutions (scoped to the
    vehicle) and filters where no resolution row exists. Recalls are
    matched by make (case-insensitive), model overlap (NULL model in
    recalls = make-wide), and year in [year_start, year_end] (NULL
    endpoints = open-ended).

    Parameters
    ----------
    vehicle_id : int
        Row ID from the ``vehicles`` table.
    db_path : str, optional
        Override the default database path.

    Returns
    -------
    list[dict]
        Open + unresolved recall rows. Empty list if vehicle missing,
        tables missing, or no recalls apply.
    """
    try:
        with get_connection(db_path) as conn:
            veh_row = conn.execute(
                "SELECT id, make, model, year FROM vehicles WHERE id = ?",
                (vehicle_id,),
            ).fetchone()
            if veh_row is None:
                return []
            make = veh_row["make"]
            model = veh_row["model"]
            year = veh_row["year"]

            # LEFT JOIN lets us detect resolutions (we filter NULL).
            # Year / model filters mirror Phase 118 list_recalls_for_vehicle
            # but add the open=1 and NOT-resolved predicates.
            query = """
                SELECT r.*
                FROM recalls r
                LEFT JOIN recall_resolutions rr
                    ON rr.recall_id = r.id AND rr.vehicle_id = ?
                WHERE rr.id IS NULL
                  AND r.open = 1
                  AND LOWER(r.make) = LOWER(?)
                  AND (r.model IS NULL OR LOWER(r.model) = LOWER(?))
                  AND (r.year_start IS NULL OR r.year_start <= ?)
                  AND (r.year_end IS NULL OR r.year_end >= ?)
                ORDER BY r.severity DESC, r.nhtsa_id
            """
            rows = conn.execute(
                query, (vehicle_id, make, model, year, year),
            ).fetchall()
            return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        # Pre-migration DB — degrade gracefully.
        return []


def mark_resolved(
    vehicle_id: int,
    recall_id: int,
    resolved_by_user_id: Optional[int] = None,
    resolved_at: Optional[str] = None,
    notes: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    """Record a recall resolution for a vehicle. Idempotent.

    Attempts INSERT; catches IntegrityError on duplicate
    (UNIQUE(vehicle_id, recall_id)) and returns 0. Use the return
    value to decide whether to render a green 'resolved' panel or a
    yellow 'already marked' panel.

    Parameters
    ----------
    vehicle_id : int
        Row ID from ``vehicles``.
    recall_id : int
        Row ID from ``recalls``.
    resolved_by_user_id : int, optional
        Row ID from ``users``. NULL allowed — FK SET NULL preserves
        history on user deletion.
    resolved_at : str, optional
        Override the resolution timestamp. Defaults to NOW via
        CURRENT_TIMESTAMP on the column default.
    notes : str, optional
        Free-text notes.
    db_path : str, optional
        Override database path.

    Returns
    -------
    int
        1 if a new row was inserted, 0 if already resolved (duplicate).
    """
    try:
        with get_connection(db_path) as conn:
            if resolved_at is not None:
                cursor = conn.execute(
                    "INSERT INTO recall_resolutions "
                    "(vehicle_id, recall_id, resolved_at, "
                    " resolved_by_user_id, notes) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (vehicle_id, recall_id, resolved_at,
                     resolved_by_user_id, notes),
                )
            else:
                cursor = conn.execute(
                    "INSERT INTO recall_resolutions "
                    "(vehicle_id, recall_id, "
                    " resolved_by_user_id, notes) "
                    "VALUES (?, ?, ?, ?)",
                    (vehicle_id, recall_id, resolved_by_user_id, notes),
                )
            return 1 if cursor.rowcount > 0 else 0
    except sqlite3.IntegrityError:
        # UNIQUE(vehicle_id, recall_id) — already resolved. Idempotent.
        return 0


def get_resolutions_for_bike(
    vehicle_id: int, db_path: Optional[str] = None,
) -> list[dict]:
    """Return all recall resolutions for a vehicle, with recall detail.

    INNER JOIN recall_resolutions × recalls so each returned row
    carries both the resolution metadata (resolved_at, notes,
    resolved_by_user_id) and the recall itself (nhtsa_id, description,
    severity).
    """
    try:
        with get_connection(db_path) as conn:
            query = """
                SELECT rr.id AS resolution_id,
                       rr.vehicle_id,
                       rr.recall_id,
                       rr.resolved_at,
                       rr.resolved_by_user_id,
                       rr.notes AS resolution_notes,
                       r.nhtsa_id,
                       r.campaign_number,
                       r.description,
                       r.severity,
                       r.remedy
                FROM recall_resolutions rr
                INNER JOIN recalls r ON r.id = rr.recall_id
                WHERE rr.vehicle_id = ?
                ORDER BY rr.resolved_at DESC
            """
            rows = conn.execute(query, (vehicle_id,)).fetchall()
            return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        return []


def lookup(
    make: str,
    model: Optional[str] = None,
    year: Optional[int] = None,
    open_only: bool = True,
    db_path: Optional[str] = None,
) -> list[dict]:
    """List recalls matching make/model/year criteria.

    Thin wrapper that layers open=1 filter on top of the Phase 118
    list_recalls_for_vehicle helper. ``make`` is required; ``model``
    and ``year`` widen/narrow. With ``open_only=False`` returns both
    open and closed recalls.
    """
    try:
        from motodiag.inventory.recall_repo import list_recalls_for_vehicle
        rows = list_recalls_for_vehicle(
            make=make, model=model, year=year, db_path=db_path,
        )
    except sqlite3.OperationalError:
        return []
    if open_only:
        rows = [r for r in rows if r.get("open") != 0]
    return rows


# ---------------------------------------------------------------------------
# Seed loader
# ---------------------------------------------------------------------------


_DEFAULT_RECALLS_PATH = (
    Path(__file__).parent / "data" / "recalls.json"
)


def load_recalls_from_json(
    path: Optional[str] = None, db_path: Optional[str] = None,
) -> int:
    """Load the recalls.json seed into the DB. Idempotent on nhtsa_id.

    Uses ``INSERT OR IGNORE`` on the partial UNIQUE INDEX over
    nhtsa_id — re-running the loader is safe and cheap.

    Parameters
    ----------
    path : str, optional
        Path to recalls.json. Defaults to
        ``advanced/data/recalls.json`` shipped with the package.
    db_path : str, optional
        Override database path.

    Returns
    -------
    int
        Number of rows newly inserted. Previously-loaded rows count
        as 0 (so repeat invocations after first successful load
        return 0).

    Raises
    ------
    FileNotFoundError
        If the JSON file is missing.
    ValueError
        If the JSON is malformed (wraps the underlying json error
        with the filename + line for debuggability).
    """
    json_path = Path(path) if path else _DEFAULT_RECALLS_PATH
    if not json_path.exists():
        raise FileNotFoundError(
            f"Recalls seed file not found: {json_path}"
        )
    try:
        with json_path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Malformed JSON in {json_path} at line {exc.lineno} "
            f"col {exc.colno}: {exc.msg}"
        ) from exc

    if not isinstance(raw, list):
        raise ValueError(
            f"Expected a JSON array at the top level of {json_path}; "
            f"got {type(raw).__name__}"
        )

    inserted = 0
    with get_connection(db_path) as conn:
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            nhtsa_id = entry.get("nhtsa_id")
            campaign_number = entry.get("campaign_number")
            if not campaign_number:
                # campaign_number is NOT NULL UNIQUE per Phase 118 schema.
                continue
            vin_range = entry.get("vin_range")
            if vin_range is not None:
                vin_range_json = json.dumps(vin_range)
            else:
                vin_range_json = None
            open_flag = int(entry.get("open", 1))

            try:
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO recalls
                    (nhtsa_id, campaign_number, make, model,
                     year_start, year_end, description, severity,
                     remedy, notification_date, vin_range, open)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        nhtsa_id,
                        campaign_number,
                        entry.get("make"),
                        entry.get("model"),
                        entry.get("year_start"),
                        entry.get("year_end"),
                        entry.get("description", ""),
                        entry.get("severity", "medium"),
                        entry.get("remedy"),
                        entry.get("notification_date"),
                        vin_range_json,
                        open_flag,
                    ),
                )
                if cursor.rowcount > 0:
                    inserted += 1
            except sqlite3.IntegrityError:
                # Duplicate campaign_number UNIQUE — treat as
                # already-loaded, skip.
                continue
    return inserted
