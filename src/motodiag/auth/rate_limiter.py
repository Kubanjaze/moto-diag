"""In-memory token-bucket rate limiter (Phase 176).

Single-process state. Multi-worker deployments should swap in a
shared-state backend (Redis, etc.) in Track J. Configured via
``Settings.rate_limit_*_per_minute`` / ``_per_day`` fields.

Two buckets per caller:
- **minute**: resets at the start of each minute
- **day**: resets at midnight UTC (calendar-day)

On a restart, the in-memory state is wiped — the daily bucket falls
back to "remaining = today's full budget", which is acceptable for
Phase 176 (single-worker, restart cadence measured in weeks).
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional

from motodiag.core.config import Settings, get_settings


logger = logging.getLogger(__name__)


Tier = Literal["anonymous", "individual", "shop", "company"]
TIERS: tuple[Tier, ...] = ("anonymous", "individual", "shop", "company")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class RateLimitExceededError(Exception):
    """Raised when a caller exceeds their rate-limit budget."""

    def __init__(
        self, retry_after_s: int, tier: str,
        limit_per_minute: int, limit_per_day: int,
    ) -> None:
        super().__init__(
            f"rate limit exceeded ({tier} tier: "
            f"{limit_per_minute}/min, {limit_per_day}/day)"
        )
        self.retry_after_s = retry_after_s
        self.tier = tier
        self.limit_per_minute = limit_per_minute
        self.limit_per_day = limit_per_day


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


@dataclass
class _Bucket:
    """One caller's live bucket counts."""

    minute_count: int = 0
    day_count: int = 0
    minute_window_start: float = 0.0  # epoch seconds
    day_date: str = ""                 # YYYY-MM-DD (UTC)


@dataclass
class RateLimitState:
    """Snapshot returned to callers + used to set response headers."""

    tier: str
    allowed: bool
    retry_after_s: int = 0
    limit_per_minute: int = 0
    limit_per_day: int = 0
    remaining_minute: int = 0
    remaining_day: int = 0
    minute_reset_ts: int = 0


# ---------------------------------------------------------------------------
# Limiter
# ---------------------------------------------------------------------------


class RateLimiter:
    """Thread-safe in-memory token-bucket rate limiter.

    Keyed by caller identity (``"key:<id>"`` for authed,
    ``"ip:<addr>"`` for anonymous). Tier determines the budget.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        *,
        clock=None,  # test hook — defaults to time.time
    ) -> None:
        self._settings = settings or get_settings()
        self._clock = clock or time.time
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.RLock()

    # --- configuration ---

    def _limits_for(self, tier: str) -> tuple[int, int]:
        """Return (per_minute, per_day) for the given tier."""
        s = self._settings
        if tier == "anonymous":
            return (
                s.rate_limit_anonymous_per_minute,
                s.rate_limit_anonymous_per_day,
            )
        if tier == "shop":
            return (
                s.rate_limit_shop_per_minute,
                s.rate_limit_shop_per_day,
            )
        if tier == "company":
            return (
                s.rate_limit_company_per_minute,
                s.rate_limit_company_per_day,
            )
        # default (individual + unknown)
        return (
            s.rate_limit_individual_per_minute,
            s.rate_limit_individual_per_day,
        )

    # --- public API ---

    def check_and_consume(
        self, caller_key: str, tier: str,
    ) -> RateLimitState:
        """Atomically check + consume one token from both buckets.

        Returns a :class:`RateLimitState` with ``allowed=True`` on
        success, else ``allowed=False`` + a non-zero ``retry_after_s``
        hint.
        """
        now = self._clock()
        minute_start = int(now // 60) * 60
        day_str = (
            datetime.fromtimestamp(now, tz=timezone.utc)
            .strftime("%Y-%m-%d")
        )
        per_min, per_day = self._limits_for(tier)
        with self._lock:
            bucket = self._buckets.setdefault(caller_key, _Bucket())
            # Reset minute window if stale
            if bucket.minute_window_start != minute_start:
                bucket.minute_count = 0
                bucket.minute_window_start = minute_start
            # Reset daily window if stale
            if bucket.day_date != day_str:
                bucket.day_count = 0
                bucket.day_date = day_str
            # Check both budgets
            if bucket.minute_count >= per_min:
                retry = int(60 - (now - minute_start))
                return RateLimitState(
                    tier=tier, allowed=False,
                    retry_after_s=max(retry, 1),
                    limit_per_minute=per_min,
                    limit_per_day=per_day,
                    remaining_minute=0,
                    remaining_day=max(per_day - bucket.day_count, 0),
                    minute_reset_ts=int(minute_start + 60),
                )
            if bucket.day_count >= per_day:
                # Seconds until next midnight UTC
                tomorrow = (
                    datetime.fromtimestamp(now, tz=timezone.utc)
                    .replace(hour=0, minute=0, second=0, microsecond=0)
                )
                midnight_tomorrow = tomorrow.timestamp() + 86400
                retry = int(midnight_tomorrow - now)
                return RateLimitState(
                    tier=tier, allowed=False,
                    retry_after_s=max(retry, 1),
                    limit_per_minute=per_min,
                    limit_per_day=per_day,
                    remaining_minute=max(
                        per_min - bucket.minute_count, 0,
                    ),
                    remaining_day=0,
                    minute_reset_ts=int(minute_start + 60),
                )
            # Consume
            bucket.minute_count += 1
            bucket.day_count += 1
            return RateLimitState(
                tier=tier, allowed=True,
                retry_after_s=0,
                limit_per_minute=per_min,
                limit_per_day=per_day,
                remaining_minute=per_min - bucket.minute_count,
                remaining_day=per_day - bucket.day_count,
                minute_reset_ts=int(minute_start + 60),
            )

    def reset(self) -> None:
        """Clear all in-memory state. Test hook."""
        with self._lock:
            self._buckets.clear()


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


_SINGLETON: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Return the process-level RateLimiter singleton."""
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = RateLimiter()
    return _SINGLETON


def reset_rate_limiter(
    settings: Optional[Settings] = None,
    clock=None,
) -> RateLimiter:
    """Build a fresh limiter and install it as the singleton. Used by
    tests + the app factory to isolate state per-app."""
    global _SINGLETON
    _SINGLETON = RateLimiter(settings=settings, clock=clock)
    return _SINGLETON
