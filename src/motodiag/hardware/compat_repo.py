"""Adapter compatibility repository — CRUD, ranking, AutoDetector hook.

Phase 145. The third schema layer in the hardware stack: Phases 134-138
own wire protocols; Phase 139 owns the detection heuristic; this module
owns the mechanic-facing knowledge base that says "will adapter X work
on bike Y?"

Design notes
------------

- **INSERT OR IGNORE on the adapter slug.** Re-seeding is a first-class
  operation — mechanics run `motodiag hardware compat seed` after every
  update. A duplicate slug on a second seed must not raise; instead the
  existing id is returned so loaders can link compat rows to it.

- **Reliability and price checks happen in Python BEFORE SQL.** The
  CHECK constraints exist for integrity, but the repo raises
  :class:`ValueError` / :class:`TypeError` with clearer error messages
  so the CLI (and tests) never have to parse SQLite's
  "CHECK constraint failed" text.

- **Ranking is status-tier first.** A mechanic shopping for an adapter
  for a 2011 Road Glide wants the FULL-support entries at the top,
  then PARTIAL, then READ-ONLY. Within a tier, most-reliable first;
  within the same reliability, cheapest first. Final tiebreaker is
  ``adapter_id ASC`` to keep results stable across SQLite versions.

- **Specificity scoring in check_compatibility.** Exact model-pattern
  matches (no ``%`` wildcard) beat ``'CBR%'``-style patterns. Narrower
  year ranges beat wider ranges. ``added_at DESC`` is the final
  tiebreaker so the most recently-verified row wins when everything
  else ties.

- **protocols_to_skip_for_make is conservative.** With fewer than 3
  compat rows for a make, we return the empty set — not enough data
  to justify skipping any protocol. The AutoDetector hook is a
  latency optimization, not a correctness layer; a bad filter is
  worse than no filter. Token mapping:
  ``'ISO 15765' → 'CAN'``, ``'ISO 14230' | 'ISO 9141' → 'KLINE'``,
  ``'J1850 VPW' | 'J1850 PWM' → 'J1850'``. ``ELM327`` is never
  skipped — it's the universal fallback.

- **get_compat_notes(make=…) returns scoped + wildcard rows.** When a
  caller asks for notes on (adapter=obdlink-mx-plus, make=harley),
  we return both rows scoped to harley AND rows scoped to the ``'*'``
  any-make wildcard. This matches mechanic mental-model — a Bluetooth-
  pairing quirk applies regardless of the bike.
"""

from __future__ import annotations

from typing import Any, Iterable, List, Optional

from motodiag.core.database import get_connection


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


#: Valid status values. Ordered to match the CHECK constraint in the
#: migration and the status-tier ranking (full=0, partial=1,
#: read-only=2, incompatible=3).
STATUS_VALUES: tuple[str, ...] = (
    "full", "partial", "read-only", "incompatible",
)

#: Rank mapping used for ordering results in list_compatible_adapters.
_STATUS_TIER: dict[str, int] = {
    "full": 0, "partial": 1, "read-only": 2, "incompatible": 3,
}

#: Valid note_type values. Matches the CHECK constraint in the migration.
NOTE_TYPES: tuple[str, ...] = (
    "quirk", "workaround", "known-failure", "tip",
)

#: Canonical protocol labels used by AutoDetector (matches
#: motodiag.hardware.ecu_detect.PROTOCOL_CAN / _KLINE / _J1850 / _ELM327).
_PROTO_CAN: str = "CAN"
_PROTO_KLINE: str = "KLINE"
_PROTO_J1850: str = "J1850"
_PROTO_ELM327: str = "ELM327"

#: Map raw supported_protocols_csv tokens → canonical protocol labels.
#: Case-insensitive on the lookup side.
_PROTOCOL_TOKEN_MAP: dict[str, str] = {
    "iso 15765": _PROTO_CAN,
    "iso15765": _PROTO_CAN,
    "can": _PROTO_CAN,
    "iso 14230": _PROTO_KLINE,
    "iso14230": _PROTO_KLINE,
    "kwp2000": _PROTO_KLINE,
    "iso 9141": _PROTO_KLINE,
    "iso9141": _PROTO_KLINE,
    "kline": _PROTO_KLINE,
    "k-line": _PROTO_KLINE,
    "j1850 vpw": _PROTO_J1850,
    "j1850 pwm": _PROTO_J1850,
    "j1850": _PROTO_J1850,
    "elm327": _PROTO_ELM327,
}

#: Minimum compat rows for a make before protocols_to_skip_for_make
#: returns a non-empty set. Below this threshold we have too little
#: data to confidently skip a protocol.
_MIN_COMPAT_ROWS_FOR_SKIP: int = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_reliability(reliability: int) -> int:
    """Clamp-check reliability to [1, 5] and return it, or raise ValueError."""
    if not isinstance(reliability, int) or isinstance(reliability, bool):
        raise ValueError(
            f"reliability_1to5 must be an int in [1..5] (got "
            f"{type(reliability).__name__} {reliability!r})"
        )
    if reliability < 1 or reliability > 5:
        raise ValueError(
            f"reliability_1to5 must be in [1..5] (got {reliability})"
        )
    return reliability


def _validate_price(price: int) -> int:
    """Check price is an int >= 0 and return it, or raise TypeError/ValueError."""
    # bool is a subclass of int — reject it explicitly so True/False don't
    # silently become 1/0 prices (mechanic typo catcher).
    if isinstance(price, bool) or not isinstance(price, int):
        raise TypeError(
            f"price_usd_cents must be an int (got "
            f"{type(price).__name__} {price!r})"
        )
    if price < 0:
        raise ValueError(
            f"price_usd_cents must be >= 0 (got {price})"
        )
    return price


def _normalize_make(make: str) -> str:
    """Lowercase + strip; raise ValueError on empty."""
    if make is None:
        raise ValueError("make must not be None")
    normalized = str(make).strip().lower()
    if not normalized:
        raise ValueError("make must not be empty")
    return normalized


def _bool_to_int(flag: Any) -> int:
    """Coerce truthy/falsy to 0/1 for the SQLite bit columns."""
    return 1 if bool(flag) else 0


def _row_to_adapter_dict(row) -> dict:
    """Turn a sqlite3.Row into a plain dict with bool flags decoded."""
    d = dict(row)
    d["supports_bidirectional"] = bool(d.get("supports_bidirectional"))
    d["supports_mode22"] = bool(d.get("supports_mode22"))
    return d


# ---------------------------------------------------------------------------
# Adapter CRUD
# ---------------------------------------------------------------------------


def add_adapter(
    slug: str,
    brand: str,
    model: str,
    chipset: str,
    transport: str,
    price_usd_cents: int,
    supported_protocols_csv: str,
    supports_bidirectional: bool = False,
    supports_mode22: bool = False,
    reliability_1to5: int = 3,
    purchase_url: Optional[str] = None,
    known_issues: Optional[str] = None,
    notes: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    """Insert an adapter; return existing id on duplicate slug.

    Validates reliability and price in Python before touching SQL so
    callers (especially :mod:`compat_loader`) get clean error messages
    rather than CHECK-constraint text. Returns the adapter id in either
    the freshly-inserted or duplicate-slug case.
    """
    reliability_1to5 = _validate_reliability(reliability_1to5)
    price_usd_cents = _validate_price(price_usd_cents)
    bidir = _bool_to_int(supports_bidirectional)
    mode22 = _bool_to_int(supports_mode22)

    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT OR IGNORE INTO obd_adapters
               (slug, brand, model, chipset, transport,
                price_usd_cents, purchase_url, supported_protocols_csv,
                supports_bidirectional, supports_mode22, reliability_1to5,
                known_issues, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                slug, brand, model, chipset, transport,
                price_usd_cents, purchase_url, supported_protocols_csv,
                bidir, mode22, reliability_1to5,
                known_issues, notes,
            ),
        )
        cursor = conn.execute(
            "SELECT id FROM obd_adapters WHERE slug = ?", (slug,),
        )
        row = cursor.fetchone()
        return int(row[0]) if row else 0


def get_adapter(slug: str, db_path: Optional[str] = None) -> Optional[dict]:
    """Return the adapter row dict for a slug, or ``None`` if not found."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM obd_adapters WHERE slug = ?", (slug,),
        )
        row = cursor.fetchone()
        return _row_to_adapter_dict(row) if row else None


def list_adapters(
    chipset: Optional[str] = None,
    transport: Optional[str] = None,
    db_path: Optional[str] = None,
) -> list[dict]:
    """List adapters with optional filters, sorted by brand then model."""
    sql = "SELECT * FROM obd_adapters WHERE 1=1"
    params: list = []
    if chipset:
        sql += " AND chipset = ?"
        params.append(chipset)
    if transport:
        sql += " AND transport = ?"
        params.append(transport)
    sql += " ORDER BY brand COLLATE NOCASE, model COLLATE NOCASE, id"
    with get_connection(db_path) as conn:
        cursor = conn.execute(sql, params)
        return [_row_to_adapter_dict(r) for r in cursor.fetchall()]


def update_adapter(
    slug: str,
    db_path: Optional[str] = None,
    **fields: Any,
) -> bool:
    """Partial update by slug; return True if a row was modified.

    Only whitelisted column names are accepted — unknown kwargs raise
    :class:`ValueError` rather than silently being ignored. Validation
    for reliability / price runs when those fields are present.
    """
    allowed = {
        "brand", "model", "chipset", "transport",
        "price_usd_cents", "purchase_url", "supported_protocols_csv",
        "supports_bidirectional", "supports_mode22", "reliability_1to5",
        "known_issues", "notes",
    }
    if not fields:
        return False
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(
            f"update_adapter got unknown fields: {sorted(unknown)!r}"
        )

    if "reliability_1to5" in fields:
        fields["reliability_1to5"] = _validate_reliability(
            fields["reliability_1to5"]
        )
    if "price_usd_cents" in fields:
        fields["price_usd_cents"] = _validate_price(
            fields["price_usd_cents"]
        )
    if "supports_bidirectional" in fields:
        fields["supports_bidirectional"] = _bool_to_int(
            fields["supports_bidirectional"]
        )
    if "supports_mode22" in fields:
        fields["supports_mode22"] = _bool_to_int(fields["supports_mode22"])

    set_clauses = ", ".join(f"{k} = ?" for k in fields)
    params = list(fields.values()) + [slug]

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE obd_adapters SET {set_clauses} WHERE slug = ?",
            params,
        )
        return cursor.rowcount > 0


def remove_adapter(slug: str, db_path: Optional[str] = None) -> bool:
    """Delete an adapter by slug; cascades to compat + notes. Returns True if removed."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM obd_adapters WHERE slug = ?", (slug,),
        )
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Compatibility entries
# ---------------------------------------------------------------------------


def add_compatibility(
    adapter_slug: str,
    make: str,
    model_pattern: str,
    status: str,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    notes: Optional[str] = None,
    verified_by: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    """Insert a compat row. Duplicate natural keys are skipped (idempotent).

    Natural key: (adapter_id, make, model_pattern, year_min, year_max, status).
    A second insert with identical values returns the existing id rather
    than creating a duplicate — this is what makes :func:`seed_all`
    idempotent across re-runs.
    """
    if status not in STATUS_VALUES:
        raise ValueError(
            f"status must be one of {STATUS_VALUES!r} (got {status!r})"
        )
    norm_make = _normalize_make(make)

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT id FROM obd_adapters WHERE slug = ?", (adapter_slug,),
        )
        row = cursor.fetchone()
        if row is None:
            raise ValueError(
                f"add_compatibility: unknown adapter_slug {adapter_slug!r}"
            )
        adapter_id = int(row[0])

        # Natural-key dedup for idempotent re-seeding. SQLite's
        # parameter binding does not treat `IS ?` with a bound NULL
        # as NULL-equals-NULL; use explicit IS NULL vs = ? branches.
        if year_min is None and year_max is None:
            dedup_sql = (
                """SELECT id FROM adapter_compatibility
                   WHERE adapter_id = ?
                     AND vehicle_make = ?
                     AND vehicle_model_pattern = ?
                     AND year_min IS NULL
                     AND year_max IS NULL
                     AND status = ?"""
            )
            dedup_params: tuple = (
                adapter_id, norm_make, model_pattern, status,
            )
        elif year_min is None:
            dedup_sql = (
                """SELECT id FROM adapter_compatibility
                   WHERE adapter_id = ?
                     AND vehicle_make = ?
                     AND vehicle_model_pattern = ?
                     AND year_min IS NULL
                     AND year_max = ?
                     AND status = ?"""
            )
            dedup_params = (
                adapter_id, norm_make, model_pattern, year_max, status,
            )
        elif year_max is None:
            dedup_sql = (
                """SELECT id FROM adapter_compatibility
                   WHERE adapter_id = ?
                     AND vehicle_make = ?
                     AND vehicle_model_pattern = ?
                     AND year_min = ?
                     AND year_max IS NULL
                     AND status = ?"""
            )
            dedup_params = (
                adapter_id, norm_make, model_pattern, year_min, status,
            )
        else:
            dedup_sql = (
                """SELECT id FROM adapter_compatibility
                   WHERE adapter_id = ?
                     AND vehicle_make = ?
                     AND vehicle_model_pattern = ?
                     AND year_min = ?
                     AND year_max = ?
                     AND status = ?"""
            )
            dedup_params = (
                adapter_id, norm_make, model_pattern,
                year_min, year_max, status,
            )
        cursor = conn.execute(dedup_sql, dedup_params)
        existing = cursor.fetchone()
        if existing:
            return int(existing[0])

        cursor = conn.execute(
            """INSERT INTO adapter_compatibility
               (adapter_id, vehicle_make, vehicle_model_pattern,
                year_min, year_max, status, notes, verified_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (adapter_id, norm_make, model_pattern,
             year_min, year_max, status, notes, verified_by),
        )
        return int(cursor.lastrowid)


def _min_status_tier(min_status: str) -> int:
    """Map min_status string → max status-tier int (inclusive)."""
    if min_status not in _STATUS_TIER:
        raise ValueError(
            f"min_status must be one of {list(_STATUS_TIER)!r} "
            f"(got {min_status!r})"
        )
    return _STATUS_TIER[min_status]


def list_compatible_adapters(
    make: str,
    model: str,
    year: Optional[int] = None,
    min_status: str = "read-only",
    db_path: Optional[str] = None,
) -> list[dict]:
    """Return adapters compatible with a given (make, model[, year]).

    ORDER BY: status_tier ASC (full=0, partial=1, read-only=2,
    incompatible=3), reliability_1to5 DESC, price_usd_cents ASC,
    adapter_id ASC. ``min_status`` excludes weaker entries (default
    ``read-only`` excludes ``incompatible``).

    Result dicts merge adapter fields with compat-row fields — keys
    include ``status``, ``compat_notes``, ``verified_by`` in addition
    to the adapter catalog fields.
    """
    norm_make = _normalize_make(make)
    max_tier = _min_status_tier(min_status)

    # Match model against vehicle_model_pattern using SQL LIKE — the
    # PATTERN column is the side that holds the wildcard, so we flip the
    # argument order from the conventional `WHERE column LIKE ?`.
    sql = """
        SELECT
            a.id AS adapter_id,
            a.slug,
            a.brand, a.model AS adapter_model,
            a.chipset, a.transport,
            a.price_usd_cents, a.purchase_url,
            a.supported_protocols_csv,
            a.supports_bidirectional, a.supports_mode22,
            a.reliability_1to5,
            a.known_issues, a.notes AS adapter_notes,
            c.id AS compat_id,
            c.vehicle_make, c.vehicle_model_pattern,
            c.year_min, c.year_max,
            c.status, c.notes AS compat_notes,
            c.verified_by,
            c.added_at
        FROM adapter_compatibility c
        JOIN obd_adapters a ON a.id = c.adapter_id
        WHERE c.vehicle_make = ?
          AND ? LIKE c.vehicle_model_pattern
    """
    params: list = [norm_make, model]

    if year is not None:
        sql += (
            " AND (c.year_min IS NULL OR c.year_min <= ?)"
            " AND (c.year_max IS NULL OR c.year_max >= ?)"
        )
        params.extend([year, year])

    # Status tier filter (inclusive). Use a CASE expression so we can
    # filter on the derived tier without repeating the mapping in SQL.
    sql += """
        AND CASE c.status
            WHEN 'full' THEN 0
            WHEN 'partial' THEN 1
            WHEN 'read-only' THEN 2
            WHEN 'incompatible' THEN 3
            ELSE 99
        END <= ?
        ORDER BY
            CASE c.status
                WHEN 'full' THEN 0
                WHEN 'partial' THEN 1
                WHEN 'read-only' THEN 2
                WHEN 'incompatible' THEN 3
                ELSE 99
            END ASC,
            a.reliability_1to5 DESC,
            a.price_usd_cents ASC,
            a.id ASC
    """
    params.append(max_tier)

    with get_connection(db_path) as conn:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()

    results: list[dict] = []
    for row in rows:
        d = dict(row)
        d["supports_bidirectional"] = bool(d.get("supports_bidirectional"))
        d["supports_mode22"] = bool(d.get("supports_mode22"))
        results.append(d)
    return results


def _pattern_specificity(pattern: str) -> int:
    """Return a higher number for a more-specific SQL LIKE pattern.

    Heuristic: no wildcard = most specific. Each ``%`` or ``_`` reduces
    specificity. Shorter patterns at the same wildcard count are more
    specific than longer ones (more likely to be an exact family
    identifier vs a loose catch-all).

    The exact score is implementation-defined; only the relative
    ordering matters for :func:`check_compatibility`.
    """
    wildcards = pattern.count("%") + pattern.count("_")
    # Base score: 1000 for zero wildcards, then penalize per wildcard.
    score = 1000 - wildcards * 100
    # Among equally-wildcarded patterns, prefer shorter patterns
    # (tighter families). Subtract length so shorter wins.
    score -= len(pattern)
    return score


def _year_range_tightness(year_min: Optional[int], year_max: Optional[int]) -> int:
    """Return a higher number for a tighter year range (None = loosest)."""
    if year_min is None and year_max is None:
        return 0  # "all years" = loosest
    if year_min is None or year_max is None:
        # Half-open range is still looser than a closed range.
        return 1
    # Closed range — tighter ranges (narrower) win.
    span = max(0, year_max - year_min)
    return 10000 - span


def check_compatibility(
    adapter_slug: str,
    make: str,
    model: str,
    year: Optional[int] = None,
    db_path: Optional[str] = None,
) -> Optional[dict]:
    """Return the most-specific compat row for (adapter, make, model[, year]).

    Most-specific ordering:
      1. Pattern specificity (exact > wildcard).
      2. Year-range tightness (narrower closed > half-open > None/None).
      3. ``added_at DESC`` as final tiebreaker.

    Returns ``None`` when no row matches — explicitly NOT the same as
    'incompatible'. Callers that want to distinguish "unknown" from
    "incompatible" should treat ``None`` as a prompt to surface "run
    `compat note add` to contribute knowledge" rather than "this adapter
    will brick your bike."
    """
    norm_make = _normalize_make(make)

    sql = """
        SELECT
            a.id AS adapter_id,
            a.slug,
            a.brand, a.model AS adapter_model,
            a.chipset, a.transport,
            a.price_usd_cents, a.purchase_url,
            a.supported_protocols_csv,
            a.supports_bidirectional, a.supports_mode22,
            a.reliability_1to5,
            a.known_issues, a.notes AS adapter_notes,
            c.id AS compat_id,
            c.vehicle_make, c.vehicle_model_pattern,
            c.year_min, c.year_max,
            c.status, c.notes AS compat_notes,
            c.verified_by,
            c.added_at
        FROM adapter_compatibility c
        JOIN obd_adapters a ON a.id = c.adapter_id
        WHERE a.slug = ?
          AND c.vehicle_make = ?
          AND ? LIKE c.vehicle_model_pattern
    """
    params: list = [adapter_slug, norm_make, model]

    if year is not None:
        sql += (
            " AND (c.year_min IS NULL OR c.year_min <= ?)"
            " AND (c.year_max IS NULL OR c.year_max >= ?)"
        )
        params.extend([year, year])

    with get_connection(db_path) as conn:
        cursor = conn.execute(sql, params)
        rows = [dict(r) for r in cursor.fetchall()]

    if not rows:
        return None

    # Python-side sort by (pattern_specificity DESC, year_tightness DESC,
    # added_at DESC). We keep the key positive then negate in the sort
    # tuple so a lexicographic max() picks the most-specific row.
    def _key(row):
        return (
            _pattern_specificity(row["vehicle_model_pattern"]),
            _year_range_tightness(row.get("year_min"), row.get("year_max")),
            row.get("added_at") or "",
        )

    best = max(rows, key=_key)
    best["supports_bidirectional"] = bool(best.get("supports_bidirectional"))
    best["supports_mode22"] = bool(best.get("supports_mode22"))
    return best


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


def add_compat_note(
    adapter_slug: str,
    make: str,
    note_type: str,
    body: str,
    source_url: Optional[str] = None,
    submitted_by_user_id: int = 1,
    db_path: Optional[str] = None,
) -> int:
    """Insert a compat note. ``make='*'`` is the any-make wildcard."""
    if note_type not in NOTE_TYPES:
        raise ValueError(
            f"note_type must be one of {NOTE_TYPES!r} (got {note_type!r})"
        )
    if not body or not body.strip():
        raise ValueError("body must not be empty")

    # Allow literal '*' wildcard; otherwise normalize to lowercase.
    if make == "*":
        norm_make = "*"
    else:
        norm_make = _normalize_make(make)

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT id FROM obd_adapters WHERE slug = ?", (adapter_slug,),
        )
        row = cursor.fetchone()
        if row is None:
            raise ValueError(
                f"add_compat_note: unknown adapter_slug {adapter_slug!r}"
            )
        adapter_id = int(row[0])

        cursor = conn.execute(
            """INSERT INTO compat_notes
               (adapter_id, vehicle_make, note_type, body,
                source_url, submitted_by_user_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (adapter_id, norm_make, note_type, body.strip(),
             source_url, submitted_by_user_id),
        )
        return int(cursor.lastrowid)


def get_compat_notes(
    adapter_slug: str,
    make: Optional[str] = None,
    db_path: Optional[str] = None,
) -> list[dict]:
    """Return notes for an adapter. When ``make`` is set, includes ``'*'`` wildcard rows.

    Ordered by ``created_at DESC`` so the newest mechanic-contributed
    notes surface first — the CLI renders only the first N in the
    ``compat check`` panel, so recency matters.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT id FROM obd_adapters WHERE slug = ?", (adapter_slug,),
        )
        row = cursor.fetchone()
        if row is None:
            return []
        adapter_id = int(row[0])

        if make is None:
            cursor = conn.execute(
                """SELECT * FROM compat_notes
                   WHERE adapter_id = ?
                   ORDER BY created_at DESC, id DESC""",
                (adapter_id,),
            )
        else:
            norm_make = _normalize_make(make)
            cursor = conn.execute(
                """SELECT * FROM compat_notes
                   WHERE adapter_id = ?
                     AND vehicle_make IN (?, '*')
                   ORDER BY created_at DESC, id DESC""",
                (adapter_id, norm_make),
            )
        return [dict(r) for r in cursor.fetchall()]


# ---------------------------------------------------------------------------
# AutoDetector hook
# ---------------------------------------------------------------------------


def _protocols_from_csv(csv_tokens: str) -> set[str]:
    """Map a supported_protocols_csv string → set of canonical labels.

    Unknown tokens are silently dropped — a vendor spec sheet can list
    anything from "GMLAN" to "DoIP" and we only care about the four
    labels AutoDetector knows how to dispatch.
    """
    labels: set[str] = set()
    for raw in csv_tokens.split(","):
        key = raw.strip().lower()
        if not key:
            continue
        canonical = _PROTOCOL_TOKEN_MAP.get(key)
        if canonical:
            labels.add(canonical)
    return labels


def protocols_to_skip_for_make(
    make: str,
    db_path: Optional[str] = None,
) -> set[str]:
    """Return protocols that AutoDetector should skip for a make.

    A protocol is skipped when zero compat rows for this make (with
    status != 'incompatible') name an adapter that supports that
    protocol. Conservative behavior:

    - Fewer than :data:`_MIN_COMPAT_ROWS_FOR_SKIP` rows → empty set.
    - ELM327 is never skipped (universal fallback).
    - If every known protocol would be skipped, return empty set (the
      AutoDetector's own fallback also guards this, but we belt-and-
      braces here so a buggy filter can't brick detection).
    """
    norm_make = _normalize_make(make)
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """SELECT a.supported_protocols_csv
               FROM adapter_compatibility c
               JOIN obd_adapters a ON a.id = c.adapter_id
               WHERE c.vehicle_make = ? AND c.status != 'incompatible'""",
            (norm_make,),
        )
        rows = cursor.fetchall()

    if len(rows) < _MIN_COMPAT_ROWS_FOR_SKIP:
        return set()

    seen: set[str] = set()
    for row in rows:
        seen.update(_protocols_from_csv(row[0] or ""))

    # All known protocols minus seen ones = protocols to skip.
    known: set[str] = {_PROTO_CAN, _PROTO_KLINE, _PROTO_J1850, _PROTO_ELM327}
    skip = known - seen
    # ELM327 is always tried; never let it land in the skip set even if
    # no adapter happens to list it.
    skip.discard(_PROTO_ELM327)

    # Safety: if skipping would empty the order list on the caller side,
    # the caller's _protocol_order_for_hint has a `or order` fallback,
    # but we return early here too so the skip set never names the full
    # known protocol set.
    if skip == (known - {_PROTO_ELM327}):
        return set()

    return skip


__all__ = [
    "STATUS_VALUES",
    "NOTE_TYPES",
    "add_adapter",
    "get_adapter",
    "list_adapters",
    "update_adapter",
    "remove_adapter",
    "add_compatibility",
    "list_compatible_adapters",
    "check_compatibility",
    "add_compat_note",
    "get_compat_notes",
    "protocols_to_skip_for_make",
]
