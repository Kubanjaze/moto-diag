"""Phase 303 — the auth routes (Logic items 4, 6 and 7; the operator's K56
requirement 1).

Shop A is Olga's (owner, shop subscription). Tess is a tech there and Abe an
apprentice, neither with a subscription of their own. Fixtures follow
`tests/test_phase180_shop_api.py`'s: `init_db` on a temp path,
`create_app(db_path_override=...)`, `TestClient`.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from motodiag.auth.passwords import verify_password
from motodiag.auth.sessions_repo import create_session, list_user_sessions
from motodiag.auth.users_repo import deactivate_user
from motodiag.shop.rbac import list_member_permissions

from support.phase303 import (
    PASSWORD, add_member, auth, client, login, make_key, make_shop, make_sub,
    make_user, new_db, sql,
)

PROBLEM = "https://motodiag.dev/problems/"


@pytest.fixture
def db(tmp_path, monkeypatch):
    return new_db(tmp_path, monkeypatch)


@pytest.fixture
def shop(db):
    olga = make_user(db, "olga", full_name="Olga Owner")
    make_sub(db, olga, "shop")
    a = make_shop(db, "Shop A", olga)
    tess = make_user(db, "tess")
    abe = make_user(db, "abe")
    add_member(db, a, tess, "tech")
    add_member(db, a, abe, "apprentice")
    return SimpleNamespace(db=db, olga=olga, a=a, tess=tess, abe=abe, c=client(db))


def _hash(db, uid):
    return sql(db, "SELECT password_hash FROM users WHERE id = ?", (uid,))[0][0]


class TestLogin:
    def test_200_carries_token_user_and_memberships(self, shop):
        r = shop.c.post("/v1/auth/login", json={"username": "tess", "password": PASSWORD,
                                                "client": "phone"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["token"].startswith("mds_")
        assert body["expires_at"].endswith("+00:00")
        assert body["user"] == {"id": shop.tess, "username": "tess",
                                "full_name": "Tess", "email": "tess@ex.com"}
        assert body["memberships"] == [{
            "shop_id": shop.a, "shop_name": "Shop A", "role": "tech",
            "permissions": list_member_permissions(shop.a, shop.tess, db_path=shop.db),
        }]
        assert "write_session" in body["memberships"][0]["permissions"]

    @pytest.mark.parametrize("case", ["unknown", "wrong", "no-password", "inactive"])
    def test_every_failure_is_one_401(self, shop, case):
        if case == "no-password":
            make_user(shop.db, "nopass", None)
        if case == "inactive":
            deactivate_user(shop.abe, db_path=shop.db)
        name = {"unknown": "nobody", "wrong": "tess", "no-password": "nopass",
                "inactive": "abe"}[case]
        password = "wrong horse" if case == "wrong" else PASSWORD
        r = shop.c.post("/v1/auth/login", json={"username": name, "password": password})
        assert r.status_code == 401
        body = r.json()
        assert (body["type"], body["title"], body["detail"]) == (
            PROBLEM + "login-failed", "Login failed", "invalid username or password")

    def test_the_problem_envelope_and_request_id_match_the_other_routes(self, shop):
        r = shop.c.post("/v1/auth/login", json={"username": "x", "password": "y"},
                        headers={"X-Request-ID": "rid-303"})
        assert r.headers["X-Request-ID"] == "rid-303"
        assert r.json()["request_id"] == "rid-303"
        assert r.json()["instance"] == "/v1/auth/login" and r.json()["status"] == 401

    def test_a_login_needs_no_credential_and_writes_one_row(self, shop):
        before = sql(shop.db, "SELECT count(*) FROM api_keys")[0][0]
        login(shop.c, "tess")
        assert sql(shop.db, "SELECT count(*) FROM api_keys")[0][0] == before + 1


class TestTheTokenAppearsOnce:
    def test_in_exactly_one_response_body(self, shop):
        r = shop.c.post("/v1/auth/login", json={"username": "tess", "password": PASSWORD})
        token = r.json()["token"]
        bodies = [r.text]
        h = auth(token)
        for method, path in [("get", "/v1/auth/me"), ("get", "/v1/auth/sessions"),
                             ("get", "/v1/shop/profile/list"), ("post", "/v1/auth/logout")]:
            bodies.append(getattr(shop.c, method)(path, headers=h).text)
        bodies.append(shop.c.get("/v1/auth/me", headers=h).text)  # now 401
        assert [token in b for b in bodies] == [True] + [False] * 5


class TestMe:
    def test_a_session(self, shop):
        token = login(shop.c, "tess")
        body = shop.c.get("/v1/auth/me", headers=auth(token)).json()
        assert body["credential"]["kind"] == "session"
        assert body["credential"]["prefix"] == token[:12]
        assert body["tier"] == "shop"  # Olga's
        assert body["memberships"][0]["role"] == "tech"
        assert body["user"]["username"] == "tess"

    def test_a_key(self, shop):
        key = make_key(shop.db, shop.olga)
        body = shop.c.get("/v1/auth/me", headers={"X-API-Key": key}).json()
        assert body["credential"]["kind"] == "api_key" and body["tier"] == "shop"

    def test_no_credential_401(self, shop):
        assert shop.c.get("/v1/auth/me").status_code == 401


class TestLogout:
    def test_204_then_the_session_is_401(self, shop):
        token = login(shop.c, "tess")
        assert shop.c.post("/v1/auth/logout", headers=auth(token)).status_code == 204
        r = shop.c.get("/v1/auth/me", headers=auth(token))
        assert r.status_code == 401
        assert "session token" in r.json()["detail"]

    def test_a_key_caller_gets_400(self, shop):
        key = make_key(shop.db, shop.olga)
        r = shop.c.post("/v1/auth/logout", headers={"X-API-Key": key})
        assert r.status_code == 400
        assert r.json()["type"] == PROBLEM + "not-a-session"


class TestSessions:
    def test_lists_the_callers_sessions_and_which_is_current(self, shop):
        t1 = login(shop.c, "tess", client="phone")
        login(shop.c, "tess", client="tablet")
        login(shop.c, "olga")
        make_key(shop.db, shop.tess)
        items = shop.c.get("/v1/auth/sessions", headers=auth(t1)).json()["items"]
        assert sorted(i["client"] for i in items) == ["phone", "tablet"]
        assert [i["current"] for i in items if i["client"] == "phone"] == [True]
        assert all(i["prefix"].startswith("mds_") and i["expires_at"] for i in items)

    def test_delete_own_204(self, shop):
        t1 = login(shop.c, "tess")
        t2 = login(shop.c, "tess")
        other = [i for i in shop.c.get("/v1/auth/sessions", headers=auth(t1)).json()["items"]
                 if not i["current"]][0]
        assert shop.c.delete(f"/v1/auth/sessions/{other['id']}", headers=auth(t1)).status_code == 204
        assert shop.c.get("/v1/auth/me", headers=auth(t2)).status_code == 401
        assert shop.c.get("/v1/auth/me", headers=auth(t1)).status_code == 200

    def test_delete_anyone_elses_or_a_keys_id_404(self, shop):
        t1 = login(shop.c, "tess")
        olga_session, _ = create_session(shop.olga, db_path=shop.db)
        make_key(shop.db, shop.tess)
        key_id = sql(shop.db, "SELECT id FROM api_keys WHERE substr(key_prefix,1,4)='mdk_'")[0][0]
        for target in (olga_session.id, key_id, 99999):
            r = shop.c.delete(f"/v1/auth/sessions/{target}", headers=auth(t1))
            assert r.status_code == 404, target
            assert r.json()["type"] == PROBLEM + "login-session-not-found"
        assert list_user_sessions(shop.olga, db_path=shop.db)[0].is_active


class TestPasswordChange:
    def test_204_keeps_the_calling_session_and_ends_the_others(self, shop):
        mine = login(shop.c, "tess")
        other = login(shop.c, "tess")
        r = shop.c.post("/v1/auth/password", headers=auth(mine),
                        json={"current_password": PASSWORD, "new_password": "new horse 1"})
        assert r.status_code == 204
        assert shop.c.get("/v1/auth/me", headers=auth(mine)).status_code == 200
        assert shop.c.get("/v1/auth/me", headers=auth(other)).status_code == 401
        assert shop.c.post("/v1/auth/login", json={"username": "tess", "password": PASSWORD}
                           ).status_code == 401
        login(shop.c, "tess", "new horse 1")

    def test_wrong_current_401(self, shop):
        mine = login(shop.c, "tess")
        before = _hash(shop.db, shop.tess)
        r = shop.c.post("/v1/auth/password", headers=auth(mine),
                        json={"current_password": "nope", "new_password": "new horse 1"})
        assert r.status_code == 401 and _hash(shop.db, shop.tess) == before

    def test_too_short_422(self, shop):
        mine = login(shop.c, "tess")
        before = _hash(shop.db, shop.tess)
        r = shop.c.post("/v1/auth/password", headers=auth(mine),
                        json={"current_password": PASSWORD, "new_password": "short"})
        assert r.status_code == 422
        assert r.json()["type"] == PROBLEM + "password-too-short"
        assert _hash(shop.db, shop.tess) == before


class TestOwnersReset:
    def _reset(self, shop, caller_token, target, password="reset horse"):
        return shop.c.post(f"/v1/auth/shops/{shop.a}/members/{target}/password",
                           headers=auth(caller_token), json={"new_password": password})

    def test_the_control_a_plain_tech_is_reset_and_their_sessions_end(self, shop):
        tess_token = login(shop.c, "tess")
        assert self._reset(shop, login(shop.c, "olga"), shop.tess).status_code == 204
        assert shop.c.get("/v1/auth/me", headers=auth(tess_token)).status_code == 401
        login(shop.c, "tess", "reset horse")

    def test_an_apprentice_may_not(self, shop):
        r = self._reset(shop, login(shop.c, "abe"), shop.tess)
        assert r.status_code == 403 and r.json()["type"] == PROBLEM + "permission-denied"

    def test_a_tech_may_not(self, shop):
        assert self._reset(shop, login(shop.c, "tess"), shop.abe).status_code == 403

    def test_an_owner_of_another_shop_may_not(self, shop):
        bob = make_user(shop.db, "bob")
        make_sub(shop.db, bob, "shop")
        make_shop(shop.db, "Shop B", bob)
        assert self._reset(shop, login(shop.c, "bob"), shop.tess).status_code == 403

    def test_a_non_member_target_is_404(self, shop):
        stranger = make_user(shop.db, "stranger")
        r = self._reset(shop, login(shop.c, "olga"), stranger)
        assert r.status_code == 404

    def test_too_short_is_422(self, shop):
        before = _hash(shop.db, shop.tess)
        r = self._reset(shop, login(shop.c, "olga"), shop.tess, "short")
        assert r.status_code == 422 and _hash(shop.db, shop.tess) == before

    def test_an_owner_with_no_subscription_gets_402(self, db):
        olga = make_user(db, "olga")
        a = make_shop(db, "Shop A", olga)
        tess = make_user(db, "tess")
        add_member(db, a, tess)
        c = client(db)
        r = c.post(f"/v1/auth/shops/{a}/members/{tess}/password",
                   headers=auth(login(c, "olga")), json={"new_password": "reset horse"})
        assert r.status_code == 402


class TestOwnersResetK56:
    """K56 requirement 1: a member who owns a second shop, an owner at any
    shop, and a member of another shop where the caller has no
    manage_users are each refused; nothing about the target changes."""

    def _refused(self, shop, target):
        target_token = login(shop.c, sql(shop.db, "SELECT username FROM users WHERE id = ?",
                                         (target,))[0][0])
        before = _hash(shop.db, target)
        sessions_before = [s.id for s in list_user_sessions(target, db_path=shop.db)]
        r = shop.c.post(f"/v1/auth/shops/{shop.a}/members/{target}/password",
                        headers=auth(login(shop.c, "olga")), json={"new_password": "reset horse"})
        assert r.status_code == 403, r.text
        assert _hash(shop.db, target) == before
        assert verify_password(PASSWORD, _hash(shop.db, target))
        assert [s.id for s in list_user_sessions(target, db_path=shop.db)] == sessions_before
        assert shop.c.get("/v1/auth/me", headers=auth(target_token)).status_code == 200

    def test_a_member_who_owns_a_second_shop(self, shop):
        mo = make_user(shop.db, "mo")
        add_member(shop.db, shop.a, mo, "tech")
        make_shop(shop.db, "Mo's Shop", mo)
        self._refused(shop, mo)

    def test_an_owner_at_any_shop_including_this_one(self, shop):
        co = make_user(shop.db, "co")
        add_member(shop.db, shop.a, co, "owner")
        self._refused(shop, co)

    def test_a_member_of_another_shop_where_the_caller_lacks_manage_users(self, shop):
        dee = make_user(shop.db, "dee")
        add_member(shop.db, shop.a, dee, "tech")
        bob = make_user(shop.db, "bob")
        b = make_shop(shop.db, "Shop B", bob)
        add_member(shop.db, b, dee, "service_writer")
        self._refused(shop, dee)

    def test_a_member_set_aside_at_another_shop_is_still_refused(self, shop):
        from motodiag.shop.rbac import deactivate_member

        dee = make_user(shop.db, "dee")
        add_member(shop.db, shop.a, dee, "tech")
        bob = make_user(shop.db, "bob")
        b = make_shop(shop.db, "Shop B", bob)
        add_member(shop.db, b, dee, "tech")
        deactivate_member(b, dee, db_path=shop.db)
        self._refused(shop, dee)

    def test_the_control_a_member_of_two_shops_both_the_callers_is_reset(self, shop):
        """The other-shop rule refuses only where the caller lacks the
        permission: Olga owns both shops here."""
        b = make_shop(shop.db, "Shop B", shop.olga)
        add_member(shop.db, b, shop.tess, "tech")
        r = shop.c.post(f"/v1/auth/shops/{shop.a}/members/{shop.tess}/password",
                        headers=auth(login(shop.c, "olga")), json={"new_password": "reset horse"})
        assert r.status_code == 204


class TestASessionOnExistingRoutes:
    def test_a_techs_session_reaches_a_shop_route(self, shop):
        r = shop.c.get("/v1/shop/profile/list", headers=auth(login(shop.c, "tess")))
        assert r.status_code == 200
        assert r.json()["items"][0]["my_role"] == "tech"

    def test_a_session_gets_403_where_a_key_does(self, shop):
        bob = make_user(shop.db, "bob")
        make_sub(shop.db, bob, "shop")
        b = make_shop(shop.db, "Shop B", bob)
        assert shop.c.get(f"/v1/shop/profile/{b}",
                          headers=auth(login(shop.c, "tess"))).status_code == 403

    def test_a_session_gets_402_where_a_key_does(self, db):
        loner = make_user(db, "loner")
        make_sub(db, loner, "individual")
        c = client(db)
        assert c.get("/v1/shop/profile/list", headers=auth(login(c, "loner"))).status_code == 402

    def test_expired_and_revoked_sessions_are_401(self, shop):
        expired = login(shop.c, "tess")
        sql(shop.db, "UPDATE api_keys SET created_at = datetime('now', '-31 days') "
                     "WHERE key_prefix = ?", (expired[:12],))
        revoked = login(shop.c, "tess")
        shop.c.post("/v1/auth/logout", headers=auth(revoked))
        for token in (expired, revoked):
            assert shop.c.get("/v1/shop/profile/list", headers=auth(token)).status_code == 401

    def test_the_x_api_key_header_takes_a_session_too(self, shop):
        token = login(shop.c, "tess")
        assert shop.c.get("/v1/shop/profile/list",
                          headers={"X-API-Key": token}).status_code == 200

    def test_the_kb_routes_answer_a_session(self, shop):
        token = login(shop.c, "tess")
        assert shop.c.get("/v1/kb/dtc/categories").status_code == 401
        assert shop.c.get("/v1/kb/dtc/categories", headers=auth(token)).status_code == 200


class TestListMemberPermissions:
    """Logic item 8: the names a member's role grants, by has_shop_permission's join."""

    def test_an_owner_lists_every_seeded_permission(self, shop):
        every = [r[0] for r in sql(shop.db, "SELECT name FROM permissions ORDER BY name")]
        assert list_member_permissions(shop.a, shop.olga, db_path=shop.db) == every

    def test_an_apprentice_its_read_mostly_set(self, shop):
        assert list_member_permissions(shop.a, shop.abe, db_path=shop.db) == [
            "read_garage", "read_repair_plan", "read_session", "run_diagnose"]

    def test_a_non_member_and_an_inactive_member_list_nothing(self, shop):
        from motodiag.shop.rbac import deactivate_member

        stranger = make_user(shop.db, "stranger")
        assert list_member_permissions(shop.a, stranger, db_path=shop.db) == []
        deactivate_member(shop.a, shop.tess, db_path=shop.db)
        assert list_member_permissions(shop.a, shop.tess, db_path=shop.db) == []

    def test_has_shop_permission_agrees_for_every_name(self, shop):
        from motodiag.shop.rbac import has_shop_permission

        every = [r[0] for r in sql(shop.db, "SELECT name FROM permissions")]
        for uid in (shop.olga, shop.tess, shop.abe):
            listed = set(list_member_permissions(shop.a, uid, db_path=shop.db))
            for name in every:
                assert has_shop_permission(shop.a, uid, name, db_path=shop.db) == (name in listed)


class TestRateLimiter:
    def test_a_session_callers_limit_is_their_tier(self, shop):
        r = shop.c.get("/v1/auth/me", headers=auth(login(shop.c, "tess")))
        assert r.headers["X-RateLimit-Tier"] == "shop"
        assert r.headers["X-RateLimit-Limit"] == "9999"

    def test_a_credentialed_caller_with_no_tier_stays_individual(self, db):
        loner = make_user(db, "loner")
        c = client(db)
        assert c.get("/v1/auth/me", headers=auth(login(c, "loner"))
                     ).headers["X-RateLimit-Tier"] == "individual"
        assert c.get("/v1/auth/me", headers={"X-API-Key": make_key(db, loner)}
                     ).headers["X-RateLimit-Tier"] == "individual"

    def test_login_counts_against_the_anonymous_budget(self, tmp_path, monkeypatch):
        db = new_db(tmp_path, monkeypatch)
        from motodiag.core.config import reset_settings
        monkeypatch.setenv("MOTODIAG_RATE_LIMIT_ANONYMOUS_PER_MINUTE", "2")
        reset_settings()
        make_user(db, "tess")
        c = client(db)
        codes = [c.post("/v1/auth/login", json={"username": "tess", "password": "x"}
                        ).status_code for _ in range(3)]
        assert codes == [401, 401, 429]
        reset_settings()
