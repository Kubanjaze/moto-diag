"""Phase 348, Logic item 3 — the audit log's store, `motodiag.audit.log`.

On fresh migrated databases (never live): the chain from GENESIS; a hash
recomputed from the array exactly as the plan defines it; `verify_chain` on an
intact log, a changed row, a removed middle row and dropped triggers; two
connections appending at once; no token text in the table; `list_events`'
filters, paging and empty case; `export_events` refusing to overwrite.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import threading

import pytest

from motodiag.audit import (
    GENESIS,
    AuditEvent,
    append_event,
    export_events,
    list_events,
    verify_chain,
)
from motodiag.core.database import get_connection, init_db

#: The plan's order (Logic item 3), written out here rather than read from
#: HASHED_COLUMNS, so a change to that constant's order is caught.
PLAN_ORDER = [
    "id", "occurred_at", "request_id", "actor_user_id", "actor_username",
    "credential_kind", "credential_id", "client_address", "forwarded_for",
    "method", "path", "endpoint", "path_params", "shop_id", "status",
]


@pytest.fixture(scope="module")
def template(tmp_path_factory) -> str:
    path = str(tmp_path_factory.mktemp("audit") / "template.db")
    init_db(path)
    return path


@pytest.fixture
def db(template, tmp_path) -> str:
    path = str(tmp_path / "audit.db")
    shutil.copy(template, path)
    return path


def _ev(i: int, **kw) -> AuditEvent:
    base = dict(method="POST", path=f"/v1/shop/{kw.get('shop_id') or 0}/x/{i}",
                status=200, request_id=f"rid{i}", endpoint="ep",
                occurred_at=f"2026-10-{10 + i:02d}T12:00:00.000+00:00")
    base.update(kw)
    return AuditEvent(**base)


def _append(db: str, *events: AuditEvent) -> list[int]:
    with get_connection(db) as conn:
        return [append_event(conn, e) for e in events]


def _verify(db: str):
    with get_connection(db) as conn:
        return verify_chain(conn)


def _raw(db: str, *stmts: str) -> None:
    c = sqlite3.connect(db)
    for s in stmts:
        c.execute(s)
    c.commit()
    c.close()


def _rows(db: str) -> list[dict]:
    with get_connection(db) as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM audit_events ORDER BY id")]


class TestTheChain:
    def test_the_first_row_links_to_genesis_and_each_next_to_the_one_before(self, db):
        _append(db, _ev(1), _ev(2), _ev(3))
        rows = _rows(db)
        assert GENESIS == "0" * 64
        assert rows[0]["prev_hash"] == GENESIS
        assert rows[1]["prev_hash"] == rows[0]["row_hash"]
        assert rows[2]["prev_hash"] == rows[1]["row_hash"]

    def test_a_hash_recomputed_from_the_plan_definition_equals_the_stored_one(self, db):
        _append(db, _ev(1, actor_user_id=7, actor_username="olga", credential_kind="session",
                        credential_id=3, path_params='{"shop_id":"4"}', shop_id=4,
                        client_address="10.0.0.1", forwarded_for="1.2.3.4"),
                _ev(2))
        for row in _rows(db):
            arr = [row["prev_hash"], *(row[c] for c in PLAN_ORDER)]
            payload = json.dumps(arr, separators=(",", ":"), ensure_ascii=True)
            assert hashlib.sha256(payload.encode()).hexdigest() == row["row_hash"]

    def test_an_intact_log_verifies(self, db):
        _append(db, _ev(1), _ev(2), _ev(3))
        report = _verify(db)
        assert report.ok
        assert report.count == 3
        assert report.head_hash == _rows(db)[-1]["row_hash"]
        assert report.first_bad_id is None and report.missing_triggers == ()

    def test_an_empty_log_verifies_with_genesis_as_its_head(self, db):
        report = _verify(db)
        assert report.ok and report.count == 0 and report.head_hash == GENESIS

    def test_a_changed_row_is_named(self, db):
        _append(db, _ev(1), _ev(2), _ev(3))
        _raw(db, "DROP TRIGGER audit_events_no_update",
             "UPDATE audit_events SET status = 500 WHERE id = 2")
        report = _verify(db)
        assert not report.ok
        assert report.first_bad_id == 2
        assert report.missing_triggers == ("audit_events_no_update",)

    def test_a_row_removed_from_the_middle_is_found_at_the_row_after_it(self, db):
        _append(db, _ev(1), _ev(2), _ev(3))
        _raw(db, "DROP TRIGGER audit_events_no_delete", "DELETE FROM audit_events WHERE id = 2",
             "CREATE TRIGGER audit_events_no_delete BEFORE DELETE ON audit_events "
             "BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END")
        report = _verify(db)
        assert report.missing_triggers == ()
        assert report.first_bad_id == 3
        assert not report.ok

    @pytest.mark.parametrize("trigger", ["audit_events_no_update", "audit_events_no_delete"])
    def test_a_dropped_trigger_is_named(self, db, trigger):
        _append(db, _ev(1))
        _raw(db, f"DROP TRIGGER {trigger}")
        report = _verify(db)
        assert report.missing_triggers == (trigger,)
        assert report.first_bad_id is None
        assert not report.ok

    def test_two_connections_appending_at_once_leave_one_intact_chain(self, db):
        errors: list[BaseException] = []
        start = threading.Barrier(2)

        def writer(tag: int) -> None:
            try:
                start.wait()
                for i in range(15):
                    with get_connection(db) as conn:
                        append_event(conn, _ev(i, request_id=f"w{tag}-{i}"))
            except BaseException as e:  # noqa: BLE001 — reported below
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(t,)) for t in (1, 2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        report = _verify(db)
        assert report.ok and report.count == 30
        assert [r["id"] for r in _rows(db)] == list(range(1, 31))


class TestNoTokenInTheTable:
    TOKEN = "mdk_" + "s3cr3t" * 4

    def _dump(self, db: str) -> str:
        return json.dumps(_rows(db))

    def test_a_token_in_the_query_string_never_reaches_the_table(self, tmp_path, monkeypatch):
        from support.phase303 import client, new_db, sql
        path = new_db(tmp_path, monkeypatch)
        c = client(path)
        c.post(f"/v1/shop/1/work-orders?api_key={self.TOKEN}&token=mds_x", json={})
        c.delete(f"/v1/sessions/1?key={self.TOKEN}")
        assert sql(path, "SELECT count(*) FROM audit_events")[0][0] == 2
        dump = self._dump(path)
        assert "mdk_" not in dump and "mds_" not in dump

    def test_control_a_planted_token_is_seen_by_the_same_assertion(self, db):
        _append(db, _ev(1, path=f"/v1/x?api_key={self.TOKEN}"))
        dump = self._dump(db)
        assert "mdk_" in dump


class TestListEvents:
    def test_a_fresh_database_has_none(self, db):
        with get_connection(db) as conn:
            assert list_events(conn) == []

    def test_newest_first_and_each_filter(self, db):
        _append(db,
                _ev(1, shop_id=1, actor_user_id=10, path="/v1/shop/1/a"),
                _ev(2, shop_id=2, actor_user_id=11, path="/v1/shop/2/a"),
                _ev(3, shop_id=1, actor_user_id=11, path="/v1/auth/login"),
                _ev(4, shop_id=None, actor_user_id=10, path="/v1/vehicles"))
        with get_connection(db) as conn:
            def ids(**kw):
                return [r["id"] for r in list_events(conn, **kw)]
            assert ids() == [4, 3, 2, 1]
            assert ids(shop_id=1) == [3, 1]
            assert ids(user_id=11) == [3, 2]
            assert ids(path_prefix="/v1/shop/") == [2, 1]
            assert ids(since="2026-10-12T12:00:00+00:00") == [4, 3, 2]
            assert ids(until="2026-10-12T12:00:00+00:00") == [2, 1]
            assert ids(limit=2) == [4, 3]
            assert ids(before_id=3) == [2, 1]

    def test_paging_walks_the_whole_trail_once(self, db):
        _append(db, *[_ev(i) for i in range(1, 12)])
        seen: list[int] = []
        before = None
        with get_connection(db) as conn:
            while True:
                page = list_events(conn, limit=4, before_id=before)
                if not page:
                    break
                seen += [r["id"] for r in page]
                before = page[-1]["id"]
        assert seen == list(range(11, 0, -1))

    def test_a_bad_since_is_refused(self, db):
        with get_connection(db) as conn, pytest.raises(ValueError):
            list_events(conn, since="yesterday-ish")


class TestExport:
    def test_every_event_one_json_line_oldest_first(self, db, tmp_path):
        _append(db, _ev(1), _ev(2))
        out = tmp_path / "trail.jsonl"
        with get_connection(db) as conn:
            assert export_events(conn, out) == 2
        lines = [json.loads(x) for x in out.read_text().splitlines()]
        assert [x["id"] for x in lines] == [1, 2]
        assert lines[1]["prev_hash"] == lines[0]["row_hash"]

    def test_it_refuses_a_file_that_exists(self, db, tmp_path):
        _append(db, _ev(1))
        out = tmp_path / "trail.jsonl"
        out.write_text("keep me\n")
        with get_connection(db) as conn, pytest.raises(FileExistsError):
            export_events(conn, out)
        assert out.read_text() == "keep me\n"
