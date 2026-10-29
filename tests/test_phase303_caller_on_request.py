"""Phase 303 — the resolved caller is left on the request, the seam Phase 348
reads to log which staff login did what.

`request.state.caller` is (user id, credential kind, credential id), set
wherever a key or a session resolves: on a route that needs only a key
(the knowledge base) and on one that resolves the user.
"""

from __future__ import annotations

import pytest
from fastapi import Depends, Request

from motodiag.auth.deps import Caller, get_api_key, get_current_user

from support.phase303 import auth, client, login, make_key, make_user, new_db, sql


@pytest.fixture
def seen(tmp_path, monkeypatch):
    db = new_db(tmp_path, monkeypatch)
    c = client(db)
    got: dict = {}

    @c.app.get("/v1/_probe/user")
    def probe_user(request: Request, _=Depends(get_current_user)):
        got["user"] = request.state.caller
        return {}

    @c.app.get("/v1/_probe/key")
    def probe_key(request: Request, _=Depends(get_api_key)):
        got["key"] = getattr(request.state, "caller", None)
        return {}

    return db, c, got


def test_a_key_caller(seen):
    db, c, got = seen
    uid = make_user(db, "kim")
    key = make_key(db, uid)
    key_id = sql(db, "SELECT id FROM api_keys WHERE user_id = ?", (uid,))[0][0]
    for path in ("/v1/_probe/user", "/v1/_probe/key"):
        assert c.get(path, headers={"X-API-Key": key}).status_code == 200
    assert got["user"] == got["key"] == Caller(uid, "api_key", key_id)


def test_a_session_caller(seen):
    db, c, got = seen
    uid = make_user(db, "tess")
    token = login(c, "tess")
    session_id = sql(db, "SELECT id FROM api_keys WHERE key_prefix = ?", (token[:12],))[0][0]
    for path in ("/v1/_probe/user", "/v1/_probe/key"):
        assert c.get(path, headers=auth(token)).status_code == 200
    assert got["user"] == got["key"] == Caller(uid, "session", session_id)
    assert got["user"].credential_kind == "session"


def test_an_anonymous_caller_leaves_none(seen):
    _, c, got = seen
    assert c.get("/v1/_probe/key").status_code == 200
    assert got["key"] is None
