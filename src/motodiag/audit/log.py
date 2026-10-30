"""The audit log's store, the table ``audit_events`` (Phase 348, migration 088).

Append-only twice over: two triggers refuse UPDATE and DELETE, and every row
carries ``row_hash``, SHA-256 over the compact JSON of one array,
``[prev_hash, *the row's HASHED_COLUMNS]``, where ``prev_hash`` is the row
before's ``row_hash`` (``GENESIS`` for the first). A row changed or removed
from the middle breaks the chain, and :func:`verify_chain` names it.

Nothing here deletes a row: there is no retention period (the operator,
Phase 348). A copy for keeping is :func:`export_events`.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union

from motodiag.core.timestamps import utc_cutoff, utc_now

GENESIS = "0" * 64

#: The row's fields in the table's column order, from ``id`` to ``status``:
#: the one order the hash is computed in, by both the writer and the checker.
HASHED_COLUMNS: tuple[str, ...] = (
    "id", "occurred_at", "request_id", "actor_user_id", "actor_username",
    "credential_kind", "credential_id", "client_address", "forwarded_for",
    "method", "path", "endpoint", "path_params", "shop_id", "status",
)

TRIGGERS = ("audit_events_no_update", "audit_events_no_delete")


@dataclass(frozen=True)
class AuditEvent:
    """One write request, as the middleware saw it. ``path_params`` is the
    stored string (compact JSON); ``occurred_at`` defaults to the append's
    own clock."""

    method: str
    path: str
    status: int
    request_id: Optional[str] = None
    actor_user_id: Optional[int] = None
    actor_username: Optional[str] = None
    credential_kind: Optional[str] = None
    credential_id: Optional[int] = None
    client_address: Optional[str] = None
    forwarded_for: Optional[str] = None
    endpoint: Optional[str] = None
    path_params: Optional[str] = None
    shop_id: Optional[int] = None
    occurred_at: Optional[str] = None


@dataclass(frozen=True)
class ChainReport:
    """What :func:`verify_chain` found. ``ok`` only with every row's hash and
    link intact and both triggers present."""

    count: int
    head_hash: str
    first_bad_id: Optional[int]
    missing_triggers: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return self.first_bad_id is None and not self.missing_triggers


def row_hash(prev_hash: str, values: list[Any]) -> str:
    """The hash of one row: ``values`` are its ``HASHED_COLUMNS`` in order."""
    payload = json.dumps([prev_hash, *values], separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def append_event(conn: sqlite3.Connection, event: AuditEvent) -> int:
    """Append one event in its own ``BEGIN IMMEDIATE`` transaction, chained
    to the last row; returns its id. Two writers at once take turns."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        last = conn.execute(
            "SELECT id, row_hash FROM audit_events ORDER BY id DESC LIMIT 1"
        ).fetchone()
        prev = last[1] if last else GENESIS
        new_id = int(last[0]) + 1 if last else 1
        row = {
            "id": new_id,
            "occurred_at": event.occurred_at or utc_now(),
            "request_id": event.request_id,
            "actor_user_id": event.actor_user_id,
            "actor_username": event.actor_username,
            "credential_kind": event.credential_kind,
            "credential_id": event.credential_id,
            "client_address": event.client_address,
            "forwarded_for": event.forwarded_for,
            "method": event.method,
            "path": event.path,
            "endpoint": event.endpoint,
            "path_params": event.path_params,
            "shop_id": event.shop_id,
            "status": event.status,
        }
        values = [row[c] for c in HASHED_COLUMNS]
        conn.execute(
            f"INSERT INTO audit_events ({', '.join(HASHED_COLUMNS)}, prev_hash, row_hash) "
            f"VALUES ({', '.join('?' * (len(HASHED_COLUMNS) + 2))})",
            (*values, prev, row_hash(prev, values)),
        )
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return new_id


def list_events(
    conn: sqlite3.Connection,
    *,
    shop_id: Optional[int] = None,
    user_id: Optional[int] = None,
    since: Union[str, datetime, None] = None,
    until: Union[str, datetime, None] = None,
    path_prefix: Optional[str] = None,
    limit: int = 100,
    before_id: Optional[int] = None,
) -> list[dict]:
    """Events newest first. ``since`` and ``until`` take what
    :func:`~motodiag.core.timestamps.utc_cutoff` takes; ``before_id`` pages."""
    where: list[str] = []
    params: list[Any] = []
    if shop_id is not None:
        where.append("shop_id = ?")
        params.append(shop_id)
    if user_id is not None:
        where.append("actor_user_id = ?")
        params.append(user_id)
    lower, upper = utc_cutoff(since), utc_cutoff(until)
    if lower is not None:
        where.append("datetime(occurred_at) >= ?")
        params.append(lower)
    if upper is not None:
        where.append("datetime(occurred_at) <= ?")
        params.append(upper)
    if path_prefix:
        where.append("substr(path, 1, ?) = ?")
        params += [len(path_prefix), path_prefix]
    if before_id is not None:
        where.append("id < ?")
        params.append(before_id)
    query = "SELECT * FROM audit_events"
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    cur = conn.execute(query, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def verify_chain(conn: sqlite3.Connection) -> ChainReport:
    """Walk every row in id order, recompute its hash and check its link;
    and check both triggers are still there."""
    present = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'trigger' AND tbl_name = 'audit_events'"
    )}
    missing = tuple(t for t in TRIGGERS if t not in present)
    prev, count, bad = GENESIS, 0, None
    cur = conn.execute(
        f"SELECT {', '.join(HASHED_COLUMNS)}, prev_hash, row_hash FROM audit_events ORDER BY id"
    )
    for r in cur:
        count += 1
        values = list(r[:len(HASHED_COLUMNS)])
        stored_prev, stored_hash = r[-2], r[-1]
        if bad is None and (stored_prev != prev or row_hash(stored_prev, values) != stored_hash):
            bad = int(r[0])
        prev = stored_hash
    return ChainReport(count=count, head_hash=prev, first_bad_id=bad, missing_triggers=missing)


def export_events(conn: sqlite3.Connection, out_path: Union[str, Path]) -> int:
    """Every event, oldest first, one JSON line each, hashes included, to a
    new file; refuses one that exists. Returns the count."""
    cur = conn.execute("SELECT * FROM audit_events ORDER BY id")
    cols = [d[0] for d in cur.description]
    n = 0
    with open(out_path, "x", encoding="utf-8") as f:
        for r in cur:
            f.write(json.dumps(dict(zip(cols, r)), separators=(",", ":")) + "\n")
            n += 1
    return n
