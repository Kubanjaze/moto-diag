"""The payments feed's alarm: a check-in to a Sentry job monitor (Phase 371).

The operator's K65 (1): the feed checks in every 5 minutes, and Sentry
emails the operator after about 15 minutes of silence. Silence is the
signal, so a stopped job, a dark desktop and a dead internet connection
all raise it. The check-in carries its own ``monitor_config``, so the
monitor creates itself on the first one; the operator's one step in
Sentry is the email rule.

The URL is the shape Sentry's HTTP check-in page gives
(docs.sentry.io/product/crons/getting-started/http/). It carries the
DSN's public key, so it is never logged: a failure names the status and
the host only.
"""

from __future__ import annotations

import http.client
import json
import logging
from typing import Optional

from motodiag.telemetry.dsn import Dsn
from motodiag.telemetry.sender import Transport, urllib_transport

logger = logging.getLogger("motodiag.telemetry.monitor")

#: Sentry marks a check-in missed this many minutes after it was due:
#: 5 minutes' interval plus 10 is K65's "about 15 minutes of silence".
MARGIN_MINUTES = 10


def checkin_url(dsn: Dsn, slug: str) -> str:
    """``<scheme>://<host>/<prefix>api/<project>/cron/<slug>/<public key>/``."""
    return (f"{dsn.scheme}://{dsn.netloc}/{dsn.path_prefix}api/"
            f"{dsn.project_id}/cron/{slug}/{dsn.public_key}/")


def checkin_body(status: str, interval_minutes: int, margin_minutes: int) -> dict:
    return {
        "status": status,
        "monitor_config": {
            "schedule": {"type": "interval", "value": interval_minutes,
                         "unit": "minute"},
            "checkin_margin": margin_minutes,
            "max_runtime": interval_minutes,
            "timezone": "UTC",
        },
    }


def checkin(dsn: Dsn, slug: str, transport: Optional[Transport] = None, *,
            status: str = "ok", interval_minutes: int,
            margin_minutes: int = MARGIN_MINUTES) -> bool:
    """Post one check-in; True on a 2xx. Never raises for the network."""
    body = json.dumps(checkin_body(status, interval_minutes,
                                   margin_minutes)).encode("utf-8")
    headers = {"Content-Type": "application/json",
               "X-Sentry-Auth": dsn.auth_header}
    send = transport or urllib_transport
    try:
        code, reason, _ = send(checkin_url(dsn, slug), headers, body)
    except (OSError, http.client.HTTPException) as exc:
        logger.warning("payments feed: the check-in to %s failed: %s",
                       dsn, type(exc).__name__)
        return False
    if 200 <= code < 300:
        return True
    logger.warning("payments feed: the check-in to %s answered %s %s",
                   dsn, code, reason)
    return False
