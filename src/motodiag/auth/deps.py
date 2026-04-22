"""FastAPI dependencies for auth + subscription gating (Phase 176).

Every ``/v1/*`` route declares its authentication requirement via one
of:

- ``Depends(get_api_key)``          — optional auth (anonymous OK)
- ``Depends(require_api_key)``      — 401 if missing/invalid
- ``Depends(get_current_user)``     — resolves the caller's User row
- ``Depends(require_tier("shop"))`` — 402 if subscription < shop

Tier ordering (ascending): ``anonymous < individual < shop < company``.
A company subscription satisfies any tier requirement; shop
subscriptions satisfy individual + shop; individual subscriptions
satisfy only individual.
"""

from __future__ import annotations

from typing import Literal, Optional

from fastapi import Depends, Header, Request
from pydantic import BaseModel, ConfigDict

from motodiag.api.deps import get_db_path
from motodiag.auth.api_key_repo import (
    ApiKey, InvalidApiKeyError, verify_api_key,
)


API_KEY_HEADER = "X-API-Key"
BEARER_PREFIX = "Bearer "


SubscriptionTier = Literal["individual", "shop", "company"]
SUBSCRIPTION_TIERS: tuple[str, ...] = ("individual", "shop", "company")
_TIER_RANK: dict[str, int] = {
    "individual": 1, "shop": 2, "company": 3,
}


class SubscriptionRequiredError(Exception):
    """Raised when a route needs an active subscription but the
    caller has none. Maps to HTTP 402."""

    def __init__(self, required_tier: str) -> None:
        super().__init__(
            f"active subscription required (tier >= {required_tier!r})"
        )
        self.required_tier = required_tier


class SubscriptionTierInsufficientError(Exception):
    """Raised when a caller has a subscription but it's below the
    route's required tier. Maps to HTTP 402."""

    def __init__(self, current: str, required: str) -> None:
        super().__init__(
            f"subscription tier {current!r} is insufficient; "
            f"route requires >= {required!r}"
        )
        self.current = current
        self.required = required


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class AuthedUser(BaseModel):
    """Minimal view of the caller as resolved from their API key."""

    model_config = ConfigDict(extra="ignore")

    id: int
    username: str
    email: Optional[str] = None
    tier: Optional[str] = None  # subscription tier (not users.tier)
    is_active: bool
    api_key_id: int
    api_key_prefix: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def tier_meets(current: Optional[str], required: str) -> bool:
    """Does ``current`` meet or exceed ``required``?"""
    if current is None:
        return False
    if current not in _TIER_RANK or required not in _TIER_RANK:
        return False
    return _TIER_RANK[current] >= _TIER_RANK[required]


def _extract_key_from_headers(
    api_key_header: Optional[str],
    authorization: Optional[str],
) -> Optional[str]:
    """Pick the API key out of either header, returning the first
    non-empty value."""
    if api_key_header and api_key_header.strip():
        return api_key_header.strip()
    if authorization and authorization.startswith(BEARER_PREFIX):
        candidate = authorization[len(BEARER_PREFIX):].strip()
        if candidate:
            return candidate
    return None


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


async def get_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias=API_KEY_HEADER),
    authorization: Optional[str] = Header(None),
    db_path: str = Depends(get_db_path),
) -> Optional[ApiKey]:
    """Resolve the caller's API key or return None for anonymous.

    Checks ``X-API-Key`` header first, then ``Authorization: Bearer
    <key>``. Invalid/revoked keys return None (route can decide
    whether to 401). The verified key is stashed on
    ``request.state.api_key`` so middleware (e.g. rate limiter) can
    pick it up without re-querying.
    """
    plaintext = _extract_key_from_headers(x_api_key, authorization)
    if plaintext is None:
        return None
    key = verify_api_key(plaintext, db_path=db_path)
    if key is not None:
        request.state.api_key = key
    return key


async def require_api_key(
    api_key: Optional[ApiKey] = Depends(get_api_key),
) -> ApiKey:
    """401 if the caller has no valid API key."""
    if api_key is None:
        raise InvalidApiKeyError(
            "valid API key required (X-API-Key header or "
            "Authorization: Bearer <key>)"
        )
    return api_key


async def get_current_user(
    api_key: ApiKey = Depends(require_api_key),
    db_path: str = Depends(get_db_path),
) -> AuthedUser:
    """Resolve the user row behind the API key. Includes the caller's
    active subscription tier (None if no active sub)."""
    from motodiag.billing.subscription_repo import get_active_subscription
    from motodiag.core.database import get_connection

    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, username, email, is_active FROM users "
            "WHERE id = ?",
            (api_key.user_id,),
        ).fetchone()
    if row is None or not row["is_active"]:
        raise InvalidApiKeyError(
            f"user id={api_key.user_id} not found or inactive"
        )
    sub = get_active_subscription(api_key.user_id, db_path=db_path)
    return AuthedUser(
        id=int(row["id"]),
        username=str(row["username"]),
        email=row["email"],
        tier=sub.tier if sub is not None else None,
        is_active=True,
        api_key_id=api_key.id,
        api_key_prefix=api_key.key_prefix,
    )


def require_tier(required_tier: SubscriptionTier):
    """Dependency factory: 402 if caller's subscription doesn't meet
    ``required_tier``.

    Usage::

        @router.get(
            "/v1/shops/{id}",
            dependencies=[Depends(require_tier("shop"))],
        )
    """
    if required_tier not in SUBSCRIPTION_TIERS:
        raise ValueError(
            f"required_tier must be one of {SUBSCRIPTION_TIERS}"
        )

    async def _check(
        user: AuthedUser = Depends(get_current_user),
    ) -> AuthedUser:
        if user.tier is None:
            raise SubscriptionRequiredError(required_tier)
        if not tier_meets(user.tier, required_tier):
            raise SubscriptionTierInsufficientError(
                current=user.tier, required=required_tier,
            )
        return user

    return _check
