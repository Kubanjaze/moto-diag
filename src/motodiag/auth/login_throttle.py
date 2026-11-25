"""Failed-login guard (Phase 409 prebuild).

The rate limiter counts every anonymous request per address, so on the
public internet one address gets 100 guesses a day at any one name, and
many addresses get as many as they have. This guard counts *failed*
logins, in memory, in a sliding window:

- one name from one address: ``login_failure_limit`` failures, then 429;
- one name from every address together: five times that, then 429.

A refused attempt never reaches the password check, so a correct password
is refused too while the pair is held. A good login clears its own pair,
never the name's total, so a guesser cannot reset the count by logging in
to their own account. State is per process, like the rate limiter's, and
a restart clears it.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Callable, Optional

from motodiag.auth.rate_limiter import RateLimitExceededError
from motodiag.core.config import Settings, get_settings

NAME_WIDE_FACTOR = 5


class LoginThrottledError(RateLimitExceededError):
    """Too many failed logins for this name; answered 429 with Retry-After."""

    def __init__(self, retry_after_s: int, limit: int) -> None:
        super().__init__(retry_after_s, "login", limit, limit)
        self.args = (
            "too many failed logins for this name; try again later",
        )


class LoginThrottle:
    """Sliding-window counts of failed logins, keyed by name and address."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        *,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        s = settings or get_settings()
        self._limit = max(int(s.login_failure_limit), 1)
        self._window = max(int(s.login_failure_window_s), 1)
        self._clock = clock or time.time
        self._fails: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _keys(username: str, address: str) -> tuple[str, str]:
        name = (username or "").strip().lower()
        return f"pair:{address}|{name}", f"name:{name}"

    def _prune(self, key: str, now: float) -> deque[float]:
        q = self._fails.setdefault(key, deque())
        while q and q[0] <= now - self._window:
            q.popleft()
        return q

    def check(self, username: str, address: str) -> None:
        """Raise :class:`LoginThrottledError` while the name is held."""
        now = self._clock()
        pair, name = self._keys(username, address)
        with self._lock:
            for key, limit in ((pair, self._limit),
                               (name, self._limit * NAME_WIDE_FACTOR)):
                q = self._prune(key, now)
                if len(q) >= limit:
                    retry = int(q[0] + self._window - now) + 1
                    raise LoginThrottledError(max(retry, 1), limit)

    def record_failure(self, username: str, address: str) -> None:
        now = self._clock()
        with self._lock:
            for key in self._keys(username, address):
                self._prune(key, now).append(now)

    def record_success(self, username: str, address: str) -> None:
        pair, _ = self._keys(username, address)
        with self._lock:
            self._fails.pop(pair, None)


_THROTTLE: Optional[LoginThrottle] = None
_THROTTLE_LOCK = threading.Lock()


def get_login_throttle() -> LoginThrottle:
    global _THROTTLE
    with _THROTTLE_LOCK:
        if _THROTTLE is None:
            _THROTTLE = LoginThrottle()
        return _THROTTLE


def reset_login_throttle(
    settings: Optional[Settings] = None,
    *,
    clock: Optional[Callable[[], float]] = None,
) -> LoginThrottle:
    """Fresh state; ``create_app`` calls it, as it resets the rate limiter."""
    global _THROTTLE
    with _THROTTLE_LOCK:
        _THROTTLE = LoginThrottle(settings, clock=clock)
        return _THROTTLE
