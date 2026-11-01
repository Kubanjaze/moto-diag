"""Sentry's envelope format (Phase 343).

Three newline-terminated UTF-8 lines: the envelope header (``event_id``,
``sent_at``, ``dsn``), the item header (``type`` and the payload's
``length`` in bytes) and the JSON payload.
"""

from __future__ import annotations

import json

from motodiag.telemetry.dsn import Dsn


def _line(obj: dict) -> bytes:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def envelope(event: dict, dsn: Dsn, sent_at: str) -> bytes:
    """One event or transaction as an envelope's bytes."""
    payload = _line(event)
    item_type = "transaction" if event.get("type") == "transaction" else "event"
    header = {"event_id": event["event_id"], "sent_at": sent_at, "dsn": dsn.text}
    item = {"type": item_type, "length": len(payload)}
    return b"\n".join((_line(header), _line(item), payload)) + b"\n"
