"""Phase 200 — report share links (capability URLs for bike owners).

A share is a row that says "this opaque token grants read access to
session N's customer-preset report until <expires_at>, unless revoked".
The token IS the authorization: the recipient is a customer with no
account, so there is no second factor by design. The security model is
therefore exactly three things — entropy, a hard expiry, and revocation.

Two deliberate design calls, documented here so they read as decisions:

1. **The token is stored in PLAINTEXT**, diverging from ``api_keys``
   (sha256-hashed, plaintext shown once). An API key is an account
   credential that must survive a database read; a share token is a
   capability *locator* for a document sitting in that same database.
   Hashing would protect nothing a database reader could not already
   read directly, and it would make the link un-recopyable — which the
   mechanic needs when a customer loses the text message.

2. **``created_by_user_id`` is load-bearing, not audit trim.**
   ``build_session_report_doc`` is owner-scoped (Phase 178 retrofit), so
   rendering the page for an anonymous viewer needs a user id. Using the
   minting user's preserves the ownership invariant exactly: the
   document a viewer sees is the one the minter was entitled to at mint
   time, never more.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from motodiag.core.database import get_connection

#: ``secrets.token_urlsafe(32)`` → 43 chars, 256 bits of entropy.
#: Enumeration is not a threat model at this size; the generic 404 on
#: unknown tokens is belt-and-braces.
SHARE_TOKEN_NBYTES = 32

#: Default link lifetime. Bounds exposure when a customer forwards the
#: link onward, which they will.
DEFAULT_SHARE_TTL_DAYS = 30

#: Resolution outcomes. The public route renders a different page for
#: each, so they must stay distinguishable — collapsing "expired" and
#: "revoked" into "missing" would be a worse customer experience.
ShareStatus = Literal["ok", "expired", "revoked", "missing"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.isoformat()


def create_share(
    session_id: int,
    created_by_user_id: int,
    preset: str = "customer",
    ttl_days: int = DEFAULT_SHARE_TTL_DAYS,
    db_path: Optional[str] = None,
) -> dict:
    """Mint a share link. Returns the full row as a dict.

    Callers MUST have verified that ``created_by_user_id`` may read the
    session before calling — this function does no authorization of its
    own (the route validates by building the document first).
    """
    if ttl_days <= 0:
        raise ValueError(f"ttl_days must be positive, got {ttl_days}")
    token = secrets.token_urlsafe(SHARE_TOKEN_NBYTES)
    now = _now()
    expires_at = now + timedelta(days=ttl_days)
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO report_shares
                 (token, session_id, created_by_user_id, preset,
                  created_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                token, session_id, created_by_user_id, preset,
                _iso(now), _iso(expires_at),
            ),
        )
        share_id = cursor.lastrowid
    return {
        "id": share_id,
        "token": token,
        "session_id": session_id,
        "created_by_user_id": created_by_user_id,
        "preset": preset,
        "created_at": _iso(now),
        "expires_at": _iso(expires_at),
        "revoked_at": None,
        "view_count": 0,
        "last_viewed_at": None,
    }


def resolve_share(
    token: str,
    now: Optional[datetime] = None,
    db_path: Optional[str] = None,
) -> tuple[ShareStatus, Optional[dict]]:
    """Look a token up and classify it.

    Check order is missing → revoked → expired. Revocation is reported
    ahead of expiry so a link the shop explicitly killed says so, even
    if it had also aged out.
    """
    moment = now or _now()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM report_shares WHERE token = ?", (token,),
        ).fetchone()
    if row is None:
        return "missing", None
    share = dict(row)
    if share.get("revoked_at"):
        return "revoked", share
    try:
        expires_at = datetime.fromisoformat(str(share["expires_at"]))
    except ValueError:
        # Unparseable timestamp is treated as expired rather than
        # trusted — fail closed on a public route.
        return "expired", share
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= moment:
        return "expired", share
    return "ok", share


def record_view(share_id: int, db_path: Optional[str] = None) -> None:
    """Stamp a successful view. Best-effort: never blocks the page."""
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE report_shares SET view_count = view_count + 1, "
            "last_viewed_at = ? WHERE id = ?",
            (_iso(_now()), share_id),
        )


def revoke_share(
    share_id: int,
    user_id: int,
    db_path: Optional[str] = None,
) -> bool:
    """Revoke a share the caller minted. True if this call revoked it.

    Scoped to ``created_by_user_id`` so one mechanic cannot kill
    another's links. Idempotent: revoking an already-revoked share
    returns False and leaves the original timestamp intact.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE report_shares SET revoked_at = ? "
            "WHERE id = ? AND created_by_user_id = ? "
            "AND revoked_at IS NULL",
            (_iso(_now()), share_id, user_id),
        )
        return cursor.rowcount > 0


def list_shares_for_session(
    session_id: int,
    user_id: int,
    db_path: Optional[str] = None,
) -> list[dict]:
    """All shares this user minted for this session, newest first."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM report_shares WHERE session_id = ? "
            "AND created_by_user_id = ? ORDER BY created_at DESC",
            (session_id, user_id),
        ).fetchall()
    return [dict(row) for row in rows]
