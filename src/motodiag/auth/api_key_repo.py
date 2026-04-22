"""API key generation, hashing, and CRUD (Phase 176).

Stripe-style keys: ``mdk_live_<32-char-url-safe-base64>`` for prod,
``mdk_test_*`` for test-env. Hashed with sha256 once at creation —
plaintext is returned exactly once to the caller and never stored.

Prefix (first 12 chars, e.g. ``mdk_live_AbCd``) is safe to log /
display; the remaining 20+ chars are the secret.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

from motodiag.core.database import get_connection


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class InvalidApiKeyError(ValueError):
    """Raised for malformed, unknown, or revoked keys."""


class ApiKeyNotFoundError(ValueError):
    """Raised when a key_id does not resolve."""


# ---------------------------------------------------------------------------
# Pydantic
# ---------------------------------------------------------------------------


class ApiKey(BaseModel):
    """An API key row (never contains the plaintext secret)."""

    model_config = ConfigDict(extra="ignore")

    id: int
    user_id: int
    key_prefix: str
    key_hash: str
    name: Optional[str] = None
    last_used_at: Optional[str] = None
    is_active: bool
    created_at: str
    revoked_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Key generation / hashing
# ---------------------------------------------------------------------------


KEY_ENV_LIVE = "live"
KEY_ENV_TEST = "test"
KEY_PREFIX_CHARS = 12  # "mdk_live_AbCd" / "mdk_test_AbCd"
KEY_SECRET_NBYTES = 24  # secrets.token_urlsafe(24) → 32 chars


def generate_api_key(env: Literal["live", "test"] = "live") -> str:
    """Return a freshly-generated API key.

    Format: ``mdk_<env>_<32-char-url-safe-secret>``. Total length 41.
    Callers must hash before persisting — see :func:`create_api_key`
    for the full create-and-persist helper.
    """
    if env not in (KEY_ENV_LIVE, KEY_ENV_TEST):
        raise ValueError(f"env must be 'live' or 'test', got {env!r}")
    secret = secrets.token_urlsafe(KEY_SECRET_NBYTES)
    return f"mdk_{env}_{secret}"


def hash_api_key(key: str) -> str:
    """Deterministic sha256 of the full key. Used both for initial
    persistence and for auth-time lookup."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def key_prefix(key: str) -> str:
    """Return the first :data:`KEY_PREFIX_CHARS` of the key — safe to
    log / display."""
    return key[:KEY_PREFIX_CHARS]


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def _row_to_key(row) -> ApiKey:
    d = dict(row)
    return ApiKey(
        id=int(d["id"]),
        user_id=int(d["user_id"]),
        key_prefix=str(d["key_prefix"]),
        key_hash=str(d["key_hash"]),
        name=d.get("name"),
        last_used_at=d.get("last_used_at"),
        is_active=bool(d.get("is_active", 1)),
        created_at=str(d["created_at"]),
        revoked_at=d.get("revoked_at"),
    )


def create_api_key(
    user_id: int,
    name: Optional[str] = None,
    env: Literal["live", "test"] = "live",
    db_path: Optional[str] = None,
) -> tuple[ApiKey, str]:
    """Create + persist a new API key.

    Returns ``(ApiKey record, plaintext_key)``. **The plaintext key is
    only ever returned here — caller must display it to the user
    immediately and store it securely.** Lost keys are unrecoverable;
    user must create a new one.
    """
    plaintext = generate_api_key(env)
    prefix = key_prefix(plaintext)
    khash = hash_api_key(plaintext)
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO api_keys
               (user_id, key_prefix, key_hash, name, is_active)
               VALUES (?, ?, ?, ?, 1)""",
            (user_id, prefix, khash, name),
        )
        key_id = int(cursor.lastrowid)
        row = conn.execute(
            "SELECT * FROM api_keys WHERE id = ?", (key_id,),
        ).fetchone()
    return _row_to_key(row), plaintext


def verify_api_key(
    plaintext: str, db_path: Optional[str] = None,
) -> Optional[ApiKey]:
    """Look up an active API key by hash. Returns ``None`` for
    missing / revoked / malformed keys.

    Side effect: best-effort update of ``last_used_at`` on success.
    Failure to update is logged but does NOT fail auth.
    """
    if not plaintext or not plaintext.startswith(("mdk_live_", "mdk_test_")):
        return None
    khash = hash_api_key(plaintext)
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM api_keys WHERE key_hash = ?", (khash,),
        ).fetchone()
        if row is None or not row["is_active"]:
            return None
        try:
            conn.execute(
                "UPDATE api_keys SET last_used_at = ? WHERE id = ?",
                (now, row["id"]),
            )
        except Exception as e:
            logger.warning(
                "failed to update last_used_at for api_key id=%d: %s",
                row["id"], e,
            )
    return _row_to_key(row)


def list_api_keys(
    user_id: int,
    include_revoked: bool = False,
    db_path: Optional[str] = None,
) -> list[ApiKey]:
    query = "SELECT * FROM api_keys WHERE user_id = ?"
    params: list = [user_id]
    if not include_revoked:
        query += " AND is_active = 1"
    query += " ORDER BY id DESC"
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_key(r) for r in rows]


def get_api_key_by_id(
    key_id: int, db_path: Optional[str] = None,
) -> Optional[ApiKey]:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM api_keys WHERE id = ?", (key_id,),
        ).fetchone()
    return _row_to_key(row) if row else None


def get_api_key_by_prefix(
    prefix: str, db_path: Optional[str] = None,
) -> Optional[ApiKey]:
    """Lookup by prefix — handy for CLI 'show' commands where the
    user has the visible prefix but not the full key. Returns the
    most recently created match if multiple exist (prefix collisions
    are possible but vanishingly rare at 96 bits)."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM api_keys WHERE key_prefix = ? "
            "ORDER BY id DESC LIMIT 1",
            (prefix,),
        ).fetchone()
    return _row_to_key(row) if row else None


def revoke_api_key(
    key_id: int, db_path: Optional[str] = None,
) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE api_keys SET is_active = 0, revoked_at = ? "
            "WHERE id = ? AND is_active = 1",
            (now, key_id),
        )
        if cursor.rowcount == 0:
            # Either doesn't exist or already revoked
            existing = conn.execute(
                "SELECT id FROM api_keys WHERE id = ?", (key_id,),
            ).fetchone()
            if existing is None:
                raise ApiKeyNotFoundError(
                    f"api key not found: id={key_id}"
                )
            return False
        return True
