"""AI response caching — transparent SHA256-keyed cache for diagnose + interpret.

Phase 131: cache any AI response keyed on canonical-JSON payload hash so
repeat-identical queries serve from cache with zero tokens. Used by two
engine call paths:

- :class:`motodiag.engine.client.DiagnosticClient.diagnose` (symptom-based
  diagnosis)
- :class:`motodiag.engine.fault_codes.FaultCodeInterpreter.interpret` (DTC
  root-cause analysis)

Design:
    - Cache key is ``sha256(kind + "|" + canonical_json(payload)).hexdigest()``.
      ``kind`` ("diagnose" or "interpret") is prefixed so an identical
      payload can't collide across the two call paths.
    - Payload JSON uses ``sort_keys=True`` so dict insertion order is
      irrelevant. ``default=str`` coerces any non-JSON-native types.
    - One table, one schema (`ai_response_cache`), two logical partitions
      via ``kind`` column. Keeps the cache simple; `kind` is indexed
      implicitly via the unique ``cache_key`` index.
    - All SQLite errors are swallowed by the callers (client.py,
      fault_codes.py). This module can raise freely — the caller wraps.
    - No TTL by default. Explicit purge via :func:`purge_cache` or the
      ``motodiag cache`` CLI.

Response payload is stored as JSON (not Pickle) for portability and to
prevent code-execution risk if a cache DB is restored on a different
machine or inspected with `sqlite3`.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Optional

from motodiag.core.database import get_connection


# --- Cache key construction ---


def _make_cache_key(kind: str, payload: dict) -> str:
    """Build a deterministic SHA256 cache key from a kind + payload.

    Args:
        kind: Category discriminator — "diagnose" or "interpret". Prevents
            collisions between the two call paths on identical payloads.
        payload: Arbitrary JSON-serializable dict of inputs. Keys are sorted
            so insertion order is irrelevant. ``default=str`` handles
            datetimes, Decimals, and other non-native types.

    Returns:
        64-char hex SHA256 digest.
    """
    canonical = json.dumps(payload, sort_keys=True, default=str)
    material = kind.encode("utf-8") + b"|" + canonical.encode("utf-8")
    return hashlib.sha256(material).hexdigest()


# --- CRUD ---


def get_cached_response(
    cache_key: str,
    db_path: Optional[str] = None,
) -> Optional[dict]:
    """Look up a cached response by key. Increments hit_count on hit.

    Args:
        cache_key: SHA256 hex digest built via :func:`_make_cache_key`.
        db_path: Optional override — defaults to the configured DB path.

    Returns:
        ``None`` on miss. On hit, returns a dict with keys:

        - ``id`` (int): row id
        - ``cache_key`` (str)
        - ``kind`` (str): "diagnose" or "interpret"
        - ``model_used`` (Optional[str]): the model that produced the
          cached response
        - ``response`` (dict): parsed JSON — the model_dump() of the
          original DiagnosticResponse or FaultCodeResult
        - ``tokens_input`` (int), ``tokens_output`` (int)
        - ``cost_cents`` (int): cost of the original call
        - ``created_at`` (str), ``last_used_at`` (str)
        - ``hit_count`` (int): count BEFORE this lookup incremented it

    Raises:
        Any sqlite3.Error — the caller is expected to wrap in try/except.
    """
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, cache_key, kind, model_used, response_json, "
            "tokens_input, tokens_output, cost_cents, "
            "created_at, last_used_at, hit_count "
            "FROM ai_response_cache WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
        if row is None:
            return None

        # Bump hit_count + touch last_used_at. We record the prior hit_count
        # in the returned dict so callers can see "how many times before me"
        # separate from "how many times now including me".
        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE ai_response_cache "
            "SET hit_count = hit_count + 1, last_used_at = ? "
            "WHERE id = ?",
            (now_iso, row["id"]),
        )

        try:
            response_dict = json.loads(row["response_json"])
        except (TypeError, ValueError):
            # Corrupted cache entry — treat as miss so the caller can
            # refresh it on the next online call.
            return None

        return {
            "id": row["id"],
            "cache_key": row["cache_key"],
            "kind": row["kind"],
            "model_used": row["model_used"],
            "response": response_dict,
            "tokens_input": row["tokens_input"],
            "tokens_output": row["tokens_output"],
            "cost_cents": row["cost_cents"],
            "created_at": row["created_at"],
            "last_used_at": row["last_used_at"],
            "hit_count": row["hit_count"],
        }


def set_cached_response(
    cache_key: str,
    kind: str,
    model_used: Optional[str],
    response_dict: dict,
    tokens_input: int = 0,
    tokens_output: int = 0,
    cost_cents: int = 0,
    db_path: Optional[str] = None,
) -> int:
    """Insert or replace a cache entry. Returns the row id.

    Uses ``INSERT OR REPLACE`` so a duplicate ``cache_key`` silently
    overwrites the prior entry. ``hit_count`` resets to 0 on replace by
    design — a replaced entry is effectively a new one (updated model,
    updated inputs-to-outputs-via-updated-prompt, etc.).
    """
    response_json = json.dumps(response_dict, default=str)
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT OR REPLACE INTO ai_response_cache "
            "(cache_key, kind, model_used, response_json, "
            " tokens_input, tokens_output, cost_cents, "
            " created_at, last_used_at, hit_count) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, NULL, 0)",
            (
                cache_key,
                kind,
                model_used,
                response_json,
                int(tokens_input or 0),
                int(tokens_output or 0),
                int(cost_cents or 0),
            ),
        )
        return cursor.lastrowid


def purge_cache(
    older_than_days: Optional[int] = None,
    db_path: Optional[str] = None,
) -> int:
    """Delete cache rows. Returns rowcount.

    Args:
        older_than_days: If None, delete ALL rows (hard clear). Otherwise
            delete rows where ``created_at`` is older than N days from
            now.
        db_path: Optional DB path override.

    Returns:
        Number of rows deleted.
    """
    with get_connection(db_path) as conn:
        if older_than_days is None:
            cursor = conn.execute("DELETE FROM ai_response_cache")
        else:
            # `datetime('now', '-N days')` is SQLite's built-in date math.
            # Parameterizing the offset keeps the SQL safe.
            cursor = conn.execute(
                "DELETE FROM ai_response_cache "
                "WHERE created_at < datetime('now', ?)",
                (f"-{int(older_than_days)} days",),
            )
        return cursor.rowcount


def get_cache_stats(db_path: Optional[str] = None) -> dict:
    """Return aggregate stats for the cache.

    Returns:
        A dict with these keys:

        - ``total_rows`` (int)
        - ``total_hits`` (int): sum of hit_count across all rows
        - ``total_cost_cents_saved`` (int): sum of ``cost_cents *
          hit_count`` — approximates the dollars saved by re-serving
          cached responses instead of hitting the API again
        - ``oldest_entry`` (Optional[str]): MIN(created_at), or None if
          empty
        - ``newest_entry`` (Optional[str]): MAX(created_at), or None
    """
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT "
            "  COUNT(*) AS total_rows, "
            "  COALESCE(SUM(hit_count), 0) AS total_hits, "
            "  COALESCE(SUM(cost_cents * hit_count), 0) AS total_cost_cents_saved, "
            "  MIN(created_at) AS oldest_entry, "
            "  MAX(created_at) AS newest_entry "
            "FROM ai_response_cache"
        ).fetchone()

        return {
            "total_rows": int(row["total_rows"] or 0),
            "total_hits": int(row["total_hits"] or 0),
            "total_cost_cents_saved": int(row["total_cost_cents_saved"] or 0),
            "oldest_entry": row["oldest_entry"],
            "newest_entry": row["newest_entry"],
        }


# --- Helper: turn float dollars into integer cents, rounding up ---


def cost_dollars_to_cents(cost_usd: float) -> int:
    """Convert a USD float cost to an integer-cents representation.

    Rounds up to the nearest cent so cache savings are never under-reported.
    A $0.00001 (one-thousandth of a cent) call becomes 1 cent in the cache
    stats — small cost but meaningful hit-count signal when multiplied
    across many cache hits.
    """
    try:
        cents = float(cost_usd) * 100.0
    except (TypeError, ValueError):
        return 0
    # Standard rounding — half to even — gives accurate totals across many
    # small values, unlike always-round-up which would over-count.
    return max(0, round(cents))


__all__ = [
    "_make_cache_key",
    "get_cached_response",
    "set_cached_response",
    "purge_cache",
    "get_cache_stats",
    "cost_dollars_to_cents",
]
