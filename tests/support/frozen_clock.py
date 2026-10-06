"""Phase 370 — freeze the session clock at one instant, under one time zone.

F10 bit on a month's last evening in a US timezone: local time still the
31st, UTC already the 1st. This puts a test at that moment.

- ``frozen_datetime(instant)`` is a ``datetime`` whose ``now()`` returns
  ``instant``: as local naive time with no argument (what the old naive
  stamps called), in the zone asked for otherwise.
- ``set_zone(name)`` sets ``TZ`` and calls ``time.tzset()``, so naive local
  time, ``astimezone()`` and SQLite's ``'localtime'`` all follow it.
- ``CLOCKED`` are the modules whose ``datetime`` is replaced. They are where
  session times are made.

As a plugin (``-p support.frozen_clock``, with ``tests`` on the path), it
freezes the whole run when ``MOTODIAG_FROZEN_UTC`` is set, in
``MOTODIAG_FROZEN_TZ`` (default America/New_York), and names the moment in
the report header. ``tests/test_phase370_session_utc.py`` runs gate 9's
lifecycle and the Phase 178 quota tests that way.
"""

from __future__ import annotations

import importlib
import os
import time
from datetime import datetime, timezone

CLOCKED = ("motodiag.core.session_repo", "motodiag.core.timestamps")
DEFAULT_ZONE = "America/New_York"


def frozen_datetime(instant: datetime) -> type[datetime]:
    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return instant.astimezone().replace(tzinfo=None)
            return instant.astimezone(tz)

    return Frozen


def set_zone(name: str | None) -> None:
    if name is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = name
    time.tzset()


def pytest_configure(config) -> None:
    instant = os.environ.get("MOTODIAG_FROZEN_UTC")
    if not instant:
        return
    set_zone(os.environ.get("MOTODIAG_FROZEN_TZ", DEFAULT_ZONE))
    frozen = frozen_datetime(datetime.fromisoformat(instant))
    for name in CLOCKED:
        importlib.import_module(name).datetime = frozen


def pytest_report_header(config) -> str | None:
    if not os.environ.get("MOTODIAG_FROZEN_UTC"):
        return None
    # The time session_repo itself sees, so a freeze that did not take hold
    # shows the real clock here.
    seen = importlib.import_module(CLOCKED[0]).datetime
    return (f"frozen clock: local {seen.now().isoformat()}"
            f" ({os.environ.get('TZ')}), UTC {seen.now(timezone.utc).isoformat()}")
