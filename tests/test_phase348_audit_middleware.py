"""Phase 348, Logic items 4 and 5 — `AuditMiddleware` and the login's caller.

On `create_app(db_path_override=...)` under `TestClient`, with the helpers in
`tests/support/phase303.py` (a scratch database per test, never live). The
app has no PUT route, so each test app also mounts one probe route that takes
every method and reads the caller the way a real route does.
"""

from __future__ import annotations

import logging

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.auth.deps import AuthedUser, get_current_user
from motodiag.core.migrations import rollback_to_version

from support.phase303 import (
    PASSWORD, auth, login, make_key, make_shop, make_sub, make_user, new_db, sql,
)

WRITES = ["POST", "PUT", "PATCH", "DELETE"]
PROBE = "/v1/t348/{shop_id}/thing/{thing_id}"
#: A row's kind is its prefix's (`ApiKey.kind`).
SESSION = "key_prefix LIKE 'mds\\_%' ESCAPE '\\'"
KEY = "key_prefix NOT LIKE 'mds\\_%' ESCAPE '\\'"


def _app(db: str) -> TestClient:
    app = create_app(db_path_override=db)

    @app.api_route(PROBE, methods=[*WRITES, "GET"])
    def probe(shop_id: int, thing_id: int,
              user: AuthedUser = Depends(get_current_user)) -> dict:
        return {"ok": True}

    @app.post("/v1/t348/raise")
    def boom(user: AuthedUser = Depends(get_current_user)) -> dict:
        raise RuntimeError("route failed")

    return TestClient(app, raise_server_exceptions=False)


def _events(db: str) -> list[dict]:
    rows = sql(db, "SELECT * FROM audit_events ORDER BY id")
    cols = [r[1] for r in sql(db, "PRAGMA table_info(audit_events)")]
    return [dict(zip(cols, r)) for r in rows]


@pytest.fixture
def db(tmp_path, monkeypatch):
    return new_db(tmp_path, monkeypatch)


@pytest.fixture
def olga(db):
    uid = make_user(db, "olga", full_name="Olga Owner")
    make_sub(db, uid, "shop")
    shop = make_shop(db, "Shop A", uid)
    return uid, shop


def _credential(db: str, c: TestClient, kind: str, user_id: int) -> tuple[dict, int]:
    if kind == "api_key":
        headers = {"X-API-Key": make_key(db, user_id)}
        cid = sql(db, f"SELECT max(id) FROM api_keys WHERE {KEY}")[0][0]
    else:
        headers = auth(login(c, "olga"))
        cid = sql(db, f"SELECT max(id) FROM api_keys WHERE {SESSION}")[0][0]
    return headers, cid


class TestEachWriteIsRecorded:
    @pytest.mark.parametrize("kind", ["api_key", "session"])
    @pytest.mark.parametrize("method", WRITES)
    def test_one_event_with_the_actor_path_endpoint_status_and_request_id(
        self, db, olga, kind, method,
    ):
        uid, shop = olga
        c = _app(db)
        headers, cid = _credential(db, c, kind, uid)
        before = len(_events(db))
        r = c.request(method, f"/v1/t348/{shop}/thing/9?x=1",
                      headers={**headers, "X-Forwarded-For": "203.0.113.5"})
        assert r.status_code == 200
        events = _events(db)
        assert len(events) == before + 1
        e = events[-1]
        assert (e["actor_user_id"], e["actor_username"]) == (uid, "olga")
        assert (e["credential_kind"], e["credential_id"]) == (kind, cid)
        assert (e["method"], e["path"], e["endpoint"], e["status"]) == (
            method, f"/v1/t348/{shop}/thing/9", "probe", 200)
        assert e["request_id"] == r.headers["X-Request-ID"]
        assert e["shop_id"] == shop
        assert e["path_params"] == f'{{"shop_id":"{shop}","thing_id":"9"}}'
        assert (e["client_address"], e["forwarded_for"]) == ("testclient", "203.0.113.5")

    def test_control_a_get_on_the_same_path_leaves_none(self, db, olga):
        uid, shop = olga
        c = _app(db)
        r = c.get(f"/v1/t348/{shop}/thing/9", headers={"X-API-Key": make_key(db, uid)})
        assert r.status_code == 200
        assert _events(db) == []

    def test_a_real_route_records_its_shop_and_endpoint(self, db, olga):
        uid, shop = olga
        c = _app(db)
        r = c.patch(f"/v1/shop/profile/{shop}", json={"phone": "555-0100"},
                    headers={"X-API-Key": make_key(db, uid)})
        assert r.status_code == 200, r.text
        e = _events(db)[-1]
        assert (e["endpoint"], e["shop_id"], e["status"]) == ("update_shop_profile", shop, 200)

    def test_the_username_is_the_one_at_the_time(self, db, olga):
        uid, shop = olga
        c = _app(db)
        c.post(f"/v1/t348/{shop}/thing/1", headers={"X-API-Key": make_key(db, uid)})
        sql(db, "UPDATE users SET username = 'olga2' WHERE id = ?", (uid,))
        assert _events(db)[-1]["actor_username"] == "olga"


class TestWhatIsRecordedWithoutACaller:
    def test_an_anonymous_401_write_has_no_actor(self, db, olga):
        _, shop = olga
        r = _app(db).post(f"/v1/shop/{shop}/customers", json={"name": "x"})
        assert r.status_code == 401
        e = _events(db)[-1]
        assert e["status"] == 401
        assert (e["actor_user_id"], e["actor_username"], e["credential_kind"],
                e["credential_id"]) == (None, None, None, None)
        assert e["shop_id"] == shop

    def test_a_raising_route_is_recorded_as_500_and_the_client_gets_500(self, db, olga):
        uid, _ = olga
        r = _app(db).post("/v1/t348/raise", headers={"X-API-Key": make_key(db, uid)})
        assert r.status_code == 500
        e = _events(db)[-1]
        assert (e["status"], e["endpoint"], e["actor_user_id"]) == (500, "boom", uid)


class TestTheRateLimit:
    def test_a_429_leaves_none_and_the_allowed_request_before_it_one(self, tmp_path, monkeypatch):
        db = new_db(tmp_path, monkeypatch, rate_limit="1")
        c = _app(db)
        first = c.post("/v1/shop/1/customers", json={})
        assert first.status_code == 401  # allowed through the limiter
        assert len(_events(db)) == 1
        second = c.post("/v1/shop/1/customers", json={})
        assert second.status_code == 429
        assert len(_events(db)) == 1


class TestAFailedAuditWriteNeverFailsTheRequest:
    def test_a_database_without_the_table_answers_as_before_with_one_error(
        self, db, olga, caplog,
    ):
        uid, shop = olga
        key = make_key(db, uid)
        rollback_to_version(87, db)
        assert sql(db, "SELECT count(*) FROM sqlite_master WHERE name = 'audit_events'")[0][0] == 0
        c = _app(db)
        with caplog.at_level(logging.ERROR, logger="motodiag.audit"):
            r = c.post(f"/v1/t348/{shop}/thing/1", headers={"X-API-Key": key})
        assert (r.status_code, r.json()) == (200, {"ok": True})
        errors = [rec for rec in caplog.records
                  if rec.name == "motodiag.audit" and rec.levelno == logging.ERROR]
        assert len(errors) == 1
        assert r.headers["X-Request-ID"] in errors[0].getMessage()


class TestTheLogin:
    def test_a_successful_login_names_the_user_and_the_new_session(self, db, olga):
        uid, _ = olga
        c = _app(db)
        token = login(c, "olga")
        e = _events(db)[-1]
        sid = sql(db, f"SELECT max(id) FROM api_keys WHERE {SESSION}")[0][0]
        assert (e["path"], e["endpoint"], e["status"]) == ("/v1/auth/login", "login", 200)
        assert (e["actor_user_id"], e["actor_username"]) == (uid, "olga")
        assert (e["credential_kind"], e["credential_id"]) == ("session", sid)
        dump = repr(_events(db))
        assert token not in dump and PASSWORD not in dump and "mds_" not in dump

    def test_a_failed_login_has_no_actor_and_no_password(self, db, olga):
        c = _app(db)
        r = c.post("/v1/auth/login", json={"username": "olga", "password": "wrong-pass-1"})
        assert r.status_code == 401
        e = _events(db)[-1]
        assert (e["status"], e["actor_user_id"], e["actor_username"]) == (401, None, None)
        assert "wrong-pass-1" not in repr(_events(db))
