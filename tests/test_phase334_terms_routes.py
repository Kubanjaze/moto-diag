"""Phase 334 — the terms routes, and the first switch (Logic items 4 to 6).

A fresh database per test with one user, an API key and a session
(`tests/support/phase303.py`). `GET /v1/vehicles` reaches `require_api_key`
through `get_current_user`; `GET /v1/kb/dtc/categories` depends on
`require_api_key` directly, so a check that sits only in `get_current_user`
turns these tests red. No test reads the live database.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from motodiag.auth import terms_acceptance as terms
from motodiag.core.config import reset_settings

from support.phase303 import auth, client, login, make_key, make_user, new_db, sql

PROBLEM = "https://motodiag.dev/problems/"
HELD = ("/v1/vehicles", "/v1/kb/dtc/categories")


@pytest.fixture
def env(tmp_path, monkeypatch):
    db = new_db(tmp_path, monkeypatch)
    uid = make_user(db, "tess")
    key = make_key(db, uid)
    c = client(db)
    token = login(c, "tess")
    yield SimpleNamespace(db=db, uid=uid, c=c, key={"X-API-Key": key},
                          session=auth(token), mp=monkeypatch)
    reset_settings()


def _switch(env, on: bool) -> None:
    env.mp.setenv("MOTODIAG_TERMS_REQUIRED", "true" if on else "false")
    reset_settings()


def _rows(env) -> list:
    return sql(env.db, "SELECT user_id, version, accepted_at FROM terms_acceptances")


class TestGetTerms:
    def test_anonymous_gets_version_date_and_both_addresses(self, env):
        r = env.c.get("/v1/terms")
        assert r.status_code == 200, r.text
        assert r.json() == {
            "version": terms.TERMS_VERSION, "date": terms.TERMS_DATE,
            "terms_url": "https://getmekno.com/terms/",
            "privacy_url": "https://getmekno.com/privacy/",
            "accepted": None, "accepted_at": None,
        }

    def test_the_addresses_follow_their_settings(self, env):
        env.mp.setenv("MOTODIAG_TERMS_URL", "https://example.org/t/")
        env.mp.setenv("MOTODIAG_PRIVACY_URL", "https://example.org/p/")
        reset_settings()
        body = env.c.get("/v1/terms").json()
        assert (body["terms_url"], body["privacy_url"]) == (
            "https://example.org/t/", "https://example.org/p/")

    def test_signed_in_not_yet_accepted(self, env):
        body = env.c.get("/v1/terms", headers=env.session).json()
        assert (body["accepted"], body["accepted_at"]) == (False, None)


class TestAccept:
    def test_accept_writes_one_row_and_get_shows_it(self, env):
        r = env.c.post("/v1/terms/accept", json={"version": terms.TERMS_VERSION},
                       headers=env.session)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["version"] == terms.TERMS_VERSION
        assert body["accepted_at"].endswith("+00:00")
        assert _rows(env) == [(env.uid, terms.TERMS_VERSION, body["accepted_at"])]
        got = env.c.get("/v1/terms", headers=env.session).json()
        assert (got["accepted"], got["accepted_at"]) == (True, body["accepted_at"])

    def test_a_stale_version_is_422_and_writes_nothing(self, env):
        r = env.c.post("/v1/terms/accept", json={"version": "0.9"}, headers=env.session)
        assert r.status_code == 422
        assert r.json()["type"] == PROBLEM + "terms-version-stale"
        assert terms.TERMS_VERSION in r.json()["detail"]
        assert _rows(env) == []

    def test_a_second_accept_writes_no_second_row_and_answers_the_first_time(self, env):
        first = env.c.post("/v1/terms/accept", json={"version": terms.TERMS_VERSION},
                           headers=env.session).json()
        second = env.c.post("/v1/terms/accept", json={"version": terms.TERMS_VERSION},
                            headers=env.key)
        assert second.status_code == 200
        assert second.json() == first
        assert len(_rows(env)) == 1

    def test_accept_needs_a_credential(self, env):
        r = env.c.post("/v1/terms/accept", json={"version": terms.TERMS_VERSION})
        assert r.status_code == 401


class TestTheSwitch:
    @pytest.mark.parametrize("path", HELD)
    def test_off_an_unaccepted_user_reaches_both(self, env, path):
        _switch(env, False)
        assert env.c.get(path, headers=env.session).status_code == 200

    @pytest.mark.parametrize("cred", ["session", "key"])
    @pytest.mark.parametrize("path", HELD)
    def test_on_both_are_403_naming_the_step(self, env, path, cred):
        _switch(env, True)
        r = env.c.get(path, headers=getattr(env, cred))
        assert r.status_code == 403, r.text
        body = r.json()
        assert body["type"] == PROBLEM + "terms-not-accepted"
        assert body["title"] == "Terms of Service not accepted"
        assert body["detail"] == terms.not_accepted_message(terms.TERMS_VERSION)
        assert "GET /v1/terms" in body["detail"]
        assert "POST /v1/terms/accept" in body["detail"]

    def test_on_the_four_exempt_routes_answer_as_before(self, env):
        _switch(env, True)
        assert env.c.get("/v1/terms", headers=env.session).status_code == 200
        assert env.c.get("/v1/auth/me", headers=env.session).status_code == 200
        r = env.c.post("/v1/terms/accept", json={"version": terms.TERMS_VERSION},
                       headers=env.session)
        assert r.status_code == 200
        assert env.c.post("/v1/auth/logout", headers=env.session).status_code == 204

    def test_on_the_exempt_tuple_is_exactly_the_four(self):
        assert terms.TERMS_EXEMPT_PATHS == (
            "/v1/terms", "/v1/terms/accept", "/v1/auth/me", "/v1/auth/logout")

    def test_on_login_is_untouched(self, env):
        _switch(env, True)
        assert env.c.post("/v1/auth/login", json={
            "username": "tess", "password": "correct horse"}).status_code == 200

    def test_on_an_anonymous_call_is_still_401(self, env):
        _switch(env, True)
        assert env.c.get("/v1/kb/dtc/categories").status_code == 401

    @pytest.mark.parametrize("cred", ["session", "key"])
    def test_after_acceptance_both_are_200(self, env, cred):
        _switch(env, True)
        h = getattr(env, cred)
        assert env.c.post("/v1/terms/accept", json={"version": terms.TERMS_VERSION},
                          headers=h).status_code == 200
        for path in HELD:
            assert env.c.get(path, headers=h).status_code == 200, path

    @pytest.mark.parametrize("cred", ["session", "key"])
    def test_a_new_version_must_be_accepted_again(self, env, cred):
        _switch(env, True)
        h = getattr(env, cred)
        before = terms.TERMS_VERSION
        env.c.post("/v1/terms/accept", json={"version": before}, headers=h)
        env.mp.setattr(terms, "TERMS_VERSION", "9.9")
        for path in HELD:
            assert env.c.get(path, headers=h).status_code == 403, path
        assert env.c.get("/v1/terms", headers=h).json()["accepted"] is False
        assert env.c.post("/v1/terms/accept", json={"version": before},
                          headers=h).status_code == 422
        assert env.c.post("/v1/terms/accept", json={"version": "9.9"},
                          headers=h).status_code == 200
        for path in HELD:
            assert env.c.get(path, headers=h).status_code == 200, path
        assert sorted(v for _, v, _ in _rows(env)) == sorted([before, "9.9"])

    def test_the_switch_ships_off(self, monkeypatch):
        from motodiag.core.config import Settings

        monkeypatch.delenv("MOTODIAG_TERMS_REQUIRED", raising=False)
        monkeypatch.delenv("MOTODIAG_CHECKOUT_TERMS_CONSENT", raising=False)
        s = Settings(_env_file=None)
        assert (s.terms_required, s.checkout_terms_consent) == (False, False)


class TestRepository:
    def test_has_accepted_answers_for_exactly_that_version(self, env):
        terms.record_acceptance(env.uid, "1.0", env.db)
        assert terms.has_accepted(env.uid, "1.0", env.db)
        assert not terms.has_accepted(env.uid, "1.1", env.db)
        other = make_user(env.db, "abe")
        assert not terms.has_accepted(other, "1.0", env.db)

    def test_record_twice_returns_the_first_row(self, env):
        first = terms.record_acceptance(env.uid, "1.0", env.db)
        assert terms.record_acceptance(env.uid, "1.0", env.db) == first
        assert len(_rows(env)) == 1
