"""Login sessions and the password check (Phase 303).

A session is a row of the ``api_keys`` table, the operator's pick at the
phase's stop: the token is ``mds_`` plus a URL-safe secret, shown once and
stored as its prefix and sha256 exactly as an API key is, with ``name``
``session:<client>``. A key begins ``mdk_``, and
:func:`~motodiag.auth.api_key_repo.verify_api_key` refuses anything else,
so the two never pass for each other.

A session's expiry is ``created_at`` plus ``session_lifetime_days``,
computed and never stored. ``created_at`` is SQLite's
``CURRENT_TIMESTAMP`` (``YYYY-MM-DD HH:MM:SS``, UTC), so it is parsed into
an aware UTC time and compared with the current UTC time, never as text
(the operator's K56).

Every function that lists or revokes touches only rows whose prefix begins
``mds_``: an API key is never listed or revoked here.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from motodiag.auth.api_key_repo import (
    ApiKey,
    _row_to_key,
    hash_api_key,
    key_prefix,
)
from motodiag.auth.passwords import SCHEME, verify_password
from motodiag.auth.users_repo import get_user_by_username
from motodiag.core.database import get_connection
from motodiag.core.timestamps import stored_instant

logger = logging.getLogger(__name__)


class LoginFailedError(Exception):
    """A login, or a password change's current password, did not match."""


class NotASessionError(ValueError):
    """An action only a session can take was called with an API key."""


class LoginSessionNotFoundError(ValueError):
    """No session of the caller's has this id."""


SESSION_PREFIX = "mds_"
SESSION_SECRET_NBYTES = 24
SESSION_NAME = "session"

#: The one reason a login gives for every failure: an unknown name, a wrong
#: password, a user with no password and an inactive user alike.
LOGIN_FAILED = "invalid username or password"

#: A well-formed hash of a random string nobody kept. ``authenticate`` checks
#: against it when the name is unknown or has no password, so a wrong name
#: and a wrong password take the same time (the operator's K56).
DUMMY_HASH = (
    "scrypt$16384$8$1$ae2b067dcf1009103ad606aff35ecf5a$"
    "483fcd0e2a44c2eb0abef727f75f880e4abc21636bf905906ab1ad22393c6c1a"
)

# SQL for "this row is a session". Not LIKE 'mds_%': '_' is a LIKE wildcard.
_IS_SESSION = f"substr(key_prefix, 1, {len(SESSION_PREFIX)}) = '{SESSION_PREFIX}'"


def generate_session_token() -> str:
    return SESSION_PREFIX + secrets.token_urlsafe(SESSION_SECRET_NBYTES)


def create_session(
    user_id: int,
    client: Optional[str] = None,
    db_path: Optional[str] = None,
) -> tuple[ApiKey, str]:
    """Create a session row. Returns ``(row, plaintext)``; the plaintext is
    returned here only, for the login response."""
    plaintext = generate_session_token()
    name = f"{SESSION_NAME}:{client}" if client else SESSION_NAME
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO api_keys
               (user_id, key_prefix, key_hash, name, is_active)
               VALUES (?, ?, ?, ?, 1)""",
            (user_id, key_prefix(plaintext), hash_api_key(plaintext), name),
        )
        row = conn.execute(
            "SELECT * FROM api_keys WHERE id = ?", (int(cursor.lastrowid),),
        ).fetchone()
    return _row_to_key(row), plaintext


def _expires(created_at: str, lifetime_days: int) -> datetime:
    return stored_instant(created_at) + timedelta(days=lifetime_days)


def session_expires_at(row: ApiKey, lifetime_days: int) -> str:
    """The session's expiry, as an ISO UTC time."""
    return _expires(row.created_at, lifetime_days).isoformat(
        timespec="seconds",
    )


def session_client(row: ApiKey) -> Optional[str]:
    """The client named at login, or None."""
    name = row.name or ""
    prefix = SESSION_NAME + ":"
    return name[len(prefix):] if name.startswith(prefix) else None


def verify_session(
    plaintext: str,
    lifetime_days: int,
    db_path: Optional[str] = None,
) -> Optional[ApiKey]:
    """The session row for ``plaintext``, or None unless it is a session,
    active, unexpired, and its user is active.

    Side effect: ``last_used_at`` is updated, as
    :func:`~motodiag.auth.api_key_repo.verify_api_key` does for a key.
    """
    if not plaintext or not plaintext.startswith(SESSION_PREFIX):
        return None
    with get_connection(db_path) as conn:
        row = conn.execute(
            """SELECT ak.*, u.is_active AS user_is_active
               FROM api_keys ak JOIN users u ON u.id = ak.user_id
               WHERE ak.key_hash = ?""",
            (hash_api_key(plaintext),),
        ).fetchone()
        if row is None or not str(row["key_prefix"]).startswith(SESSION_PREFIX):
            return None
        if not row["is_active"] or not row["user_is_active"]:
            return None
        now = datetime.now(timezone.utc)
        if now >= _expires(str(row["created_at"]), lifetime_days):
            return None
        try:
            conn.execute(
                "UPDATE api_keys SET last_used_at = ? WHERE id = ?",
                (now.isoformat(), row["id"]),
            )
        except Exception as e:
            logger.warning(
                "failed to update last_used_at for session id=%d: %s",
                row["id"], e,
            )
    return _row_to_key(row)


def get_session(
    session_id: int, db_path: Optional[str] = None,
) -> Optional[ApiKey]:
    """A session row by id; None for a key's id or an unknown one."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            f"SELECT * FROM api_keys WHERE id = ? AND {_IS_SESSION}",
            (session_id,),
        ).fetchone()
    return _row_to_key(row) if row else None


def revoke_session(session_id: int, db_path: Optional[str] = None) -> bool:
    """Revoke one session. False when it is not an active session."""
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE api_keys SET is_active = 0, revoked_at = ? "
            f"WHERE id = ? AND is_active = 1 AND {_IS_SESSION}",
            (now, session_id),
        )
        return cursor.rowcount > 0


def revoke_user_sessions(
    user_id: int,
    keep_session_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> int:
    """Revoke every active session of the user but ``keep_session_id``.
    Returns how many were revoked."""
    now = datetime.now(timezone.utc).isoformat()
    query = (
        "UPDATE api_keys SET is_active = 0, revoked_at = ? "
        f"WHERE user_id = ? AND is_active = 1 AND {_IS_SESSION}"
    )
    params: list = [now, user_id]
    if keep_session_id is not None:
        query += " AND id != ?"
        params.append(keep_session_id)
    with get_connection(db_path) as conn:
        return conn.execute(query, params).rowcount


def list_user_sessions(
    user_id: int,
    include_revoked: bool = False,
    db_path: Optional[str] = None,
) -> list[ApiKey]:
    query = f"SELECT * FROM api_keys WHERE user_id = ? AND {_IS_SESSION}"
    if not include_revoked:
        query += " AND is_active = 1"
    query += " ORDER BY id DESC"
    with get_connection(db_path) as conn:
        rows = conn.execute(query, (user_id,)).fetchall()
    return [_row_to_key(r) for r in rows]


def authenticate(
    username: str, password: str, db_path: Optional[str] = None,
) -> Optional[dict]:
    """The user row when the name and password match an active user, else
    None, with no way to tell which failure it was.

    The password check runs exactly once on every path: against the user's
    hash, or against :data:`DUMMY_HASH` when the name is unknown or the user
    has no password of this module's form.
    """
    user = get_user_by_username(username, db_path=db_path)
    stored = (user or {}).get("password_hash") or ""
    has_password = stored.startswith(SCHEME + "$")
    matched = verify_password(password, stored if has_password else DUMMY_HASH)
    if user is None or not has_password or not matched:
        return None
    if not user.get("is_active"):
        return None
    return user
