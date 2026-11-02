"""What a Sentry event may carry (Phase 343, the operator's rule).

An error event: the exception's type; its message with every session
token, email address and phone number blanked, cut to 500 characters; the
stack frames as file, function, line and an in-app flag; the request id,
the method, the route template, the status, the release, the environment
and the host name. A transaction: the same route template, method and
status, and its two times.
"""

from __future__ import annotations

import re
import traceback
import uuid
from pathlib import Path
from typing import Callable, Optional

from motodiag import __version__
from motodiag.cli.serve import REDACTED as TOKEN_REDACTED
from motodiag.cli.serve import SESSION_TOKEN_RE
from motodiag.core.timestamps import utc_now

MESSAGE_LIMIT = 500
SDK = {"name": "motodiag.telemetry", "version": __version__}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
EMAIL_REDACTED = "[email redacted]"
#: 7 to 15 digits, led by an optional "+", each separated by at most one
#: space, dot, dash or bracket, touching no letter or digit either side.
PHONE_RE = re.compile(
    r"(?<![\w+])\+?\(?\d(?:[ .\-()]?\(?\d\)?){6,14}(?![\w])")
PHONE_REDACTED = "[phone redacted]"

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent


def redact(text: str) -> str:
    """Blank session tokens, emails and phone numbers; cut to the limit."""
    out = SESSION_TOKEN_RE.sub(TOKEN_REDACTED, text)
    out = EMAIL_RE.sub(EMAIL_REDACTED, out)
    out = PHONE_RE.sub(PHONE_REDACTED, out)
    return out[:MESSAGE_LIMIT]


def _hex32() -> str:
    return uuid.uuid4().hex


def _frame_file(filename: str) -> tuple[str, bool]:
    """The frame's file, relative to the package when it is the package's.

    Elsewhere, the part after ``site-packages``, else the bare name, so no
    home directory travels.
    """
    path = Path(filename)
    try:
        rel = path.resolve().relative_to(_PACKAGE_ROOT)
    except (ValueError, OSError):
        parts = path.parts
        if "site-packages" in parts:
            idx = parts.index("site-packages")
            return "/".join(parts[idx + 1:]), False
        return path.name, False
    return f"motodiag/{rel.as_posix()}", True


def frames(exc: BaseException) -> list[dict]:
    """The stack, oldest call first, with no variables and no source."""
    out = []
    for summary in traceback.extract_tb(exc.__traceback__):
        filename, in_app = _frame_file(summary.filename)
        out.append({"filename": filename, "function": summary.name,
                    "lineno": summary.lineno, "in_app": in_app})
    return out


def _tags(request_id: Optional[str], route: str, method: str,
          status: int) -> dict:
    return {"request_id": request_id or "-", "route": route,
            "method": method, "status": str(status)}


def _common(release: str, environment: str, server_name: str) -> dict:
    return {"platform": "python", "release": release,
            "environment": environment, "server_name": server_name,
            "sdk": dict(SDK)}


def error_event(exc: BaseException, *, request_id: Optional[str],
                method: str, route: str, status: int, release: str,
                environment: str, server_name: str,
                clock: Optional[Callable[[], str]] = None) -> dict:
    """One Sentry error event for an unhandled exception."""
    return {
        "event_id": _hex32(),
        "timestamp": (clock or utc_now)(),
        "level": "error",
        "logger": "motodiag.api",
        **_common(release, environment, server_name),
        "tags": _tags(request_id, route, method, status),
        "request": {"method": method, "url": route},
        "exception": {"values": [{
            "type": type(exc).__name__,
            "value": redact(str(exc)),
            "stacktrace": {"frames": frames(exc)},
        }]},
    }


def transaction_event(*, route: str, method: str, status: int,
                      started: float, ended: float,
                      request_id: Optional[str], release: str,
                      environment: str, server_name: str) -> dict:
    """One Sentry transaction: the route, the method, the status, the times."""
    return {
        "event_id": _hex32(),
        "type": "transaction",
        "transaction": f"{method} {route}",
        "start_timestamp": started,
        "timestamp": ended,
        **_common(release, environment, server_name),
        "tags": _tags(request_id, route, method, status),
        "request": {"method": method, "url": route},
        "contexts": {"trace": {
            "trace_id": _hex32(),
            "span_id": uuid.uuid4().hex[:16],
            "op": "http.server",
            "status": "ok" if status < 500 else "internal_error",
        }},
        "spans": [],
    }


def message_event(text: str, *, release: str, environment: str,
                  server_name: str,
                  clock: Optional[Callable[[], str]] = None) -> dict:
    """The one event ``motodiag telemetry check`` sends."""
    return {
        "event_id": _hex32(),
        "timestamp": (clock or utc_now)(),
        "level": "info",
        "logger": "motodiag.telemetry",
        **_common(release, environment, server_name),
        "message": {"formatted": text[:MESSAGE_LIMIT]},
    }
