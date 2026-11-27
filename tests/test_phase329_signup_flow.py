"""Phase 329 prebuild: self-serve sign-up and the password reset by email,
end to end against a scratch database, the fake billing provider and the
stand-in email sender. No network, no live database, no real email.

The operator's answers of 2026-11-25: the form on the website, pay first,
Resend later (the stand-in until then), both switches off by default.
"""

from __future__ import annotations

import copy
import re
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from support.stripe_fixtures import body, event, stripe_settings

from motodiag.api import create_app
from motodiag.api.routes.billing import get_provider
from motodiag.auth import email_sender as email_mod
from motodiag.auth.email_sender import FakeEmailSender
from motodiag.auth.passwords import hash_password, verify_password
from motodiag.auth.sessions_repo import create_session, list_user_sessions
from motodiag.auth.signup_repo import (
    SignupError,
    complete_signup,
    create_signup,
    get_signup,
)
from motodiag.auth.terms_acceptance import TERMS_VERSION, has_accepted
from motodiag.billing.providers import (
    BillingProviderError,
    FakeBillingProvider,
    signup_checkout_params,
)
from motodiag.billing.webhook_handlers import dispatch_event
from motodiag.core.config import Environment, Settings, reset_settings
from motodiag.core.database import SCHEMA_VERSION, get_connection, init_db
from motodiag.core.migrations import get_migration_by_version, rollback_to_version

SITE = "https://getmekno.com"
#: The individual's form has no shop name (the website's /signup/individual/).
INDIVIDUAL = dict(tier="individual", shop_name="", email="rider@home.example",
                  owner_name="Rita Rider", username="rita")
FORM = dict(email="Owner@Shop.example ", owner_name="Olga Owner",
            username="Olga", password="correct horse", shop_name="Olga's Moto",
            tier="shop", accept_terms="yes")


@pytest.fixture
def outbox(monkeypatch):
    """One stand-in sender for the whole test, so its outbox can be read."""
    sender = FakeEmailSender()
    monkeypatch.setattr("motodiag.api.routes.signup.get_email_sender",
                        lambda provider: sender)
    monkeypatch.setattr(email_mod, "get_email_sender", lambda provider: sender)
    return sender.outbox


def _db(tmp_path, monkeypatch, *, signup=True, reset=True, individual=True) -> str:
    path = str(tmp_path / "phase329.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999")
    monkeypatch.setenv("MOTODIAG_SELF_SERVE_SIGNUP_ENABLED", "true" if signup else "false")
    monkeypatch.setenv("MOTODIAG_PASSWORD_RESET_EMAIL_ENABLED", "true" if reset else "false")
    monkeypatch.setenv("MOTODIAG_INDIVIDUAL_SIGNUP_ENABLED", "true" if individual else "false")
    reset_settings()
    return path


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = _db(tmp_path, monkeypatch)
    yield path
    reset_settings()


def _client(db_path: str, provider=None) -> TestClient:
    app = create_app(db_path_override=db_path)
    app.dependency_overrides[get_provider] = lambda: provider or FakeBillingProvider()
    return TestClient(app, raise_server_exceptions=False, follow_redirects=False)


def _sql(db_path, q, params=()):
    with get_connection(db_path) as conn:
        return [tuple(r) for r in conn.execute(q, params).fetchall()]


def _code_from(mail) -> str:
    link = re.search(r"https?://\S+", mail.text).group(0)
    return parse_qs(urlparse(link).query)["code"][0]


def _sign_up(c, **changes):
    return c.post("/v1/signup", data={**FORM, **changes})


def _paid_sub(signup_id: int, status: str = "active", sub_id: str = "sub_signup_1") -> dict:
    sub = body("subscription_active")
    sub["id"] = sub_id
    sub["status"] = status
    sub["metadata"] = {"signup_id": str(signup_id), "tier": "shop"}
    return sub


def _sub_event(sub_id="sub_signup_1", event_id="evt_s1"):
    return event("customer.subscription.created",
                 {"id": sub_id, "object": "subscription", "status": "active",
                  "metadata": {}}, event_id=event_id)


# ---------------------------------------------------------------- migration


class TestMigration093:
    def test_the_head_is_93_with_both_tables(self, db):
        assert SCHEMA_VERSION >= 93
        tables = {r[0] for r in _sql(db, "SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"signups", "one_time_codes"} <= tables

    def test_rollback_drops_both_tables(self, db):
        assert get_migration_by_version(93) is not None
        rollback_to_version(92, db)
        tables = {r[0] for r in _sql(db, "SELECT name FROM sqlite_master WHERE type='table'")}
        assert "signups" not in tables and "one_time_codes" not in tables

    def test_the_columns_refuse_what_the_contract_does_not_name(self, db):
        with pytest.raises(Exception):
            create_signup(email="a@b.co", owner_name="A", username="abc",
                          password_hash="x", shop_name="S", tier="fleet",  # type: ignore[arg-type]
                          terms_version=TERMS_VERSION, db_path=db)
        for tier, shop in (("individual", "S"), ("shop", None)):
            with pytest.raises(SignupError):
                create_signup(email="a@b.co", owner_name="A", username="abc",
                              password_hash="x", shop_name=shop, tier=tier,  # type: ignore[arg-type]
                              terms_version=TERMS_VERSION, db_path=db)
            with pytest.raises(Exception), get_connection(db) as conn:
                conn.execute("INSERT INTO signups (email, owner_name, username, "
                             "password_hash, shop_name, tier, terms_version, "
                             "created_at) VALUES ('a@b.co','A','abc','x',?,?,'1.1','now')",
                             (shop, tier))
        with pytest.raises(Exception), get_connection(db) as conn:
            conn.execute("INSERT INTO signups (email, owner_name, username, "
                         "password_hash, shop_name, tier, terms_version, "
                         "created_at, status) VALUES ('a@b.co','A','abc','x','S',"
                         "'shop','1.1','now','paid')")


# ---------------------------------------------------------------- the switches


class TestTheSwitches:
    ROUTES = [("post", "/v1/signup"), ("get", "/v1/signup/confirm"),
              ("post", "/v1/signup/confirm"), ("post", "/v1/auth/password-reset"),
              ("get", "/v1/auth/password-reset/confirm"),
              ("post", "/v1/auth/password-reset/confirm")]

    def test_they_ship_off(self):
        s = Settings()
        assert s.self_serve_signup_enabled is False
        assert s.individual_signup_enabled is False
        assert s.password_reset_email_enabled is False
        assert s.email_provider == "fake"

    def test_off_every_route_is_404(self, tmp_path, monkeypatch, outbox):
        path = _db(tmp_path, monkeypatch, signup=False, reset=False, individual=False)
        c = _client(path)
        for method, url in self.ROUTES:
            r = getattr(c, method)(url)
            assert r.status_code == 404, (method, url, r.status_code)
        assert outbox == []
        assert _sql(path, "SELECT COUNT(*) FROM signups") == [(0,)]

    def test_each_switch_is_its_own(self, tmp_path, monkeypatch, outbox):
        path = _db(tmp_path, monkeypatch, signup=False, reset=True, individual=False)
        c = _client(path)
        assert _sign_up(c).status_code == 404
        assert _sign_up(c, **INDIVIDUAL).status_code == 404
        assert c.post("/v1/auth/password-reset", data={"email": "x@y.co"}).status_code == 303

    def test_individuals_open_while_shops_wait_for_shop_ten(self, tmp_path, monkeypatch, outbox):
        """K150: individuals sign up on their own; K141: shops after shop 10."""
        path = _db(tmp_path, monkeypatch, signup=False, individual=True)
        c = _client(path)
        assert _sign_up(c).status_code == 404
        assert _sign_up(c, tier="company").status_code == 404
        assert _sign_up(c, **INDIVIDUAL).headers["location"] == f"{SITE}/signup/check-email/"
        assert _sql(path, "SELECT tier, shop_name FROM signups") == [("individual", None)]

    def test_shops_open_alone(self, tmp_path, monkeypatch, outbox):
        path = _db(tmp_path, monkeypatch, signup=True, individual=False)
        c = _client(path)
        assert _sign_up(c, **INDIVIDUAL).status_code == 404
        assert _sign_up(c).status_code == 303

    def test_a_plan_switched_off_after_its_form_goes_no_further(
            self, tmp_path, monkeypatch, outbox):
        path = _db(tmp_path, monkeypatch, signup=True, individual=True)
        _sign_up(_client(path), **INDIVIDUAL)
        path = _db(tmp_path, monkeypatch, signup=True, individual=False)
        r = _client(path).post("/v1/signup/confirm", data={"code": _code_from(outbox[0])})
        assert r.status_code == 404
        assert get_signup(1, path).status == "pending_email"

    def test_the_routes_are_not_in_the_api_schema(self, db):
        paths = _client(db).get("/openapi.json").json()["paths"]
        assert not [p for p in paths if "signup" in p or "password-reset" in p]

    @pytest.mark.parametrize("switch", ["self_serve_signup_enabled",
                                        "individual_signup_enabled",
                                        "password_reset_email_enabled"])
    def test_prod_refuses_to_start_with_a_switch_on_and_no_email_service(self, switch):
        s = Settings(env=Environment.PROD, billing_provider="stripe",
                     stripe_api_key="sk_test_x", stripe_webhook_secret="whsec_x",
                     **{switch: True})
        with pytest.raises(RuntimeError, match="email_provider='fake'"):
            create_app(settings=s)

    def test_prod_starts_with_both_switches_off(self):
        s = Settings(env=Environment.PROD, billing_provider="stripe",
                     stripe_api_key="sk_test_x", stripe_webhook_secret="whsec_x")
        create_app(settings=s)


# ---------------------------------------------------------------- the form


class TestTheForm:
    def test_good_form_stores_a_hashed_signup_and_sends_one_link(self, db, outbox):
        r = _sign_up(_client(db))
        assert r.status_code == 303
        assert r.headers["location"] == f"{SITE}/signup/check-email/"
        rows = _sql(db, "SELECT email, username, password_hash, status, tier, "
                        "terms_version, user_id, shop_id FROM signups")
        assert len(rows) == 1
        email, username, pw_hash, status, tier, terms, user_id, shop_id = rows[0]
        assert (email, username, status, tier, terms) == (
            "owner@shop.example", "olga", "pending_email", "shop", TERMS_VERSION)
        assert pw_hash != FORM["password"] and verify_password(FORM["password"], pw_hash)
        assert user_id is None and shop_id is None
        assert [m.to for m in outbox] == ["owner@shop.example"]
        assert "/v1/signup/confirm?code=" in outbox[0].text
        # No login and no shop before payment.
        assert _sql(db, "SELECT COUNT(*) FROM users WHERE username = 'olga'") == [(0,)]
        assert _sql(db, "SELECT COUNT(*) FROM shops") == [(0,)]

    def test_only_the_codes_hash_is_stored(self, db, outbox):
        _sign_up(_client(db))
        code = _code_from(outbox[0])
        stored = _sql(db, "SELECT code_hash, purpose, subject FROM one_time_codes")
        assert len(stored) == 1 and code not in stored[0][0]
        assert stored[0][1:] == ("verify_email", "signup:1")

    @pytest.mark.parametrize("change,why", [
        (dict(email="not-an-address"), "email"),
        (dict(owner_name=" "), "name"),
        (dict(shop_name=""), "shop"),
        (dict(tier="fleet"), "plan"),
        (dict(tier="company "), "plan"),
        (dict(accept_terms=""), "terms"),
        (dict(username="ab"), "username"),
        (dict(username="-olga"), "username"),
        (dict(username="olga owner"), "username"),
        (dict(password="short"), "password"),
    ])
    def test_a_bad_field_goes_to_its_problem_page_and_stores_nothing(
            self, db, outbox, change, why):
        r = _sign_up(_client(db), **change)
        assert r.status_code == 303
        assert r.headers["location"] == f"{SITE}/signup/problem/#{why}"
        assert _sql(db, "SELECT COUNT(*) FROM signups") == [(0,)]
        assert outbox == []

    def test_a_username_a_login_has_or_a_pending_signup_asks_for_is_taken(self, db, outbox):
        c = _client(db)
        _sign_up(c)
        r = _sign_up(c, email="other@shop.example", username="OLGA")
        assert r.headers["location"] == f"{SITE}/signup/problem/#username-taken"
        with get_connection(db) as conn:
            conn.execute("INSERT INTO users (username) VALUES ('tess')")
        r = _sign_up(c, email="t@shop.example", username="tess")
        assert r.headers["location"] == f"{SITE}/signup/problem/#username-taken"

    def test_the_site_address_comes_from_the_settings(self, tmp_path, monkeypatch, outbox):
        monkeypatch.setenv("MOTODIAG_SIGNUP_SITE_URL", "https://staging.example/")
        path = _db(tmp_path, monkeypatch)
        r = _sign_up(_client(path))
        assert r.headers["location"] == "https://staging.example/signup/check-email/"


# ---------------------------------------------------------------- the email link


class TestTheEmailLink:
    def test_opening_the_link_spends_nothing(self, db, outbox):
        c = _client(db)
        _sign_up(c)
        code = _code_from(outbox[0])
        page = c.get(f"/v1/signup/confirm?code={code}")
        assert page.status_code == 200
        assert "<form method=\"post\" action=\"/v1/signup/confirm\">" in page.text
        assert "default-src 'none'" in page.headers["content-security-policy"]
        assert page.headers["cache-control"] == "no-store"
        assert _sql(db, "SELECT used_at FROM one_time_codes") == [(None,)]
        assert get_signup(1, db).status == "pending_email"

    def test_the_page_escapes_the_code(self, db):
        page = _client(db).get('/v1/signup/confirm?code="><script>x</script>')
        assert "<script>" not in page.text

    def test_the_button_verifies_and_goes_to_checkout(self, db, outbox):
        c = _client(db)
        _sign_up(c)
        r = c.post("/v1/signup/confirm", data={"code": _code_from(outbox[0])})
        assert r.status_code == 303
        assert r.headers["location"] == "https://fake-billing.local/checkout/signup/1/shop"
        assert get_signup(1, db).status == "email_verified"
        assert _sql(db, "SELECT used_at IS NOT NULL FROM one_time_codes") == [(1,)]

    def test_a_used_link_reopens_the_payment_only(self, db, outbox):
        c = _client(db)
        _sign_up(c)
        code = _code_from(outbox[0])
        c.post("/v1/signup/confirm", data={"code": code})
        again = c.post("/v1/signup/confirm", data={"code": code})
        assert again.headers["location"].startswith("https://fake-billing.local/checkout/")
        assert get_signup(1, db).status == "email_verified"

    def test_a_wrong_or_empty_code_is_the_link_problem(self, db, outbox):
        c = _client(db)
        _sign_up(c)
        for code in ("", "nope", _code_from(outbox[0])[:-2]):
            r = c.post("/v1/signup/confirm", data={"code": code})
            assert r.headers["location"] == f"{SITE}/signup/problem/#link"
        assert get_signup(1, db).status == "pending_email"

    def test_an_expired_link_is_the_link_problem(self, db, outbox):
        c = _client(db)
        _sign_up(c)
        _sql(db, "UPDATE one_time_codes SET expires_at = 1, issued_at = 0")
        r = c.post("/v1/signup/confirm", data={"code": _code_from(outbox[0])})
        assert r.headers["location"] == f"{SITE}/signup/problem/#link"
        assert get_signup(1, db).status == "pending_email"

    def test_a_reset_code_never_confirms_a_signup(self, db, outbox):
        c = _client(db)
        with get_connection(db) as conn:
            conn.execute("INSERT INTO users (username, email, password_hash, is_active) "
                         "VALUES ('rider', 'r@shop.example', ?, 1)", (hash_password("x" * 10),))
        c.post("/v1/auth/password-reset", data={"email": "r@shop.example"})
        r = c.post("/v1/signup/confirm", data={"code": _code_from(outbox[0])})
        assert r.headers["location"] == f"{SITE}/signup/problem/#link"

    def test_checkout_failing_says_later(self, db, outbox):
        class Down(FakeBillingProvider):
            def create_signup_checkout_session(self, *a, **k):
                raise BillingProviderError("stripe down")
        c = _client(db, Down())
        _sign_up(c)
        r = c.post("/v1/signup/confirm", data={"code": _code_from(outbox[0])})
        assert r.headers["location"] == f"{SITE}/signup/problem/#later"

    def test_a_completed_signup_goes_to_the_paid_page(self, db, outbox):
        c = _client(db)
        _sign_up(c)
        code = _code_from(outbox[0])
        c.post("/v1/signup/confirm", data={"code": code})
        complete_signup(1, "sub_x", db_path=db)
        r = c.post("/v1/signup/confirm", data={"code": code})
        assert r.headers["location"] == f"{SITE}/signup/paid/"

    def test_each_form_gets_its_own_link(self, db, outbox):
        c = _client(db)
        _sign_up(c)
        first = _code_from(outbox[0])
        # The same person asks again (a new sign-up row, a new link); the old
        # sign-up's link still names the old row and stays its own.
        _sql(db, "DELETE FROM signups")  # free the username for the second form
        _sign_up(c)
        assert len(outbox) == 2 and _code_from(outbox[1]) != first


# ---------------------------------------------------------------- paying


class TestPaying:
    def test_checkout_carries_the_signup_in_the_subscriptions_metadata(self):
        p = signup_checkout_params(signup_id=4, email="o@s.example", tier="shop",
                                   price="price_test_shop",
                                   success_url="https://s/ok", cancel_url="https://s/no")
        assert p["subscription_data"]["metadata"] == {"signup_id": "4", "tier": "shop"}
        assert p["customer_email"] == "o@s.example"
        assert "trial_period_days" not in p["subscription_data"]  # pay first
        assert p["mode"] == "subscription"

    def _verified(self, db, outbox) -> int:
        c = _client(db)
        _sign_up(c)
        c.post("/v1/signup/confirm", data={"code": _code_from(outbox[0])})
        outbox.clear()
        return 1

    def test_paid_makes_login_shop_owner_terms_and_one_welcome(self, db, outbox):
        sid = self._verified(db, outbox)
        provider = FakeBillingProvider({"sub_signup_1": _paid_sub(sid)})
        res = dispatch_event(_sub_event(), db_path=db, provider=provider,
                             settings=stripe_settings())
        assert res.error is None, res.error
        s = get_signup(sid, db)
        assert s.status == "completed" and s.user_id and s.shop_id
        user = _sql(db, "SELECT username, email, full_name, password_hash, tier "
                        "FROM users WHERE id = ?", (s.user_id,))[0]
        assert user[:3] == ("olga", "owner@shop.example", "Olga Owner")
        assert verify_password(FORM["password"], user[3]) and user[4] == "shop"
        assert _sql(db, "SELECT name, email FROM shops WHERE id = ?", (s.shop_id,)) == [
            ("Olga's Moto", "owner@shop.example")]
        assert _sql(db, "SELECT role FROM shop_members WHERE shop_id = ? AND user_id = ?",
                    (s.shop_id, s.user_id)) == [("owner",)]
        assert has_accepted(s.user_id, TERMS_VERSION, db_path=db)
        assert _sql(db, "SELECT user_id, tier, status FROM subscriptions") == [
            (s.user_id, "shop", "active")]
        assert [m.to for m in outbox] == ["owner@shop.example"]
        assert "olga" in outbox[0].text

    def test_the_paid_owner_can_sign_in(self, db, outbox):
        sid = self._verified(db, outbox)
        dispatch_event(_sub_event(), db_path=db,
                       provider=FakeBillingProvider({"sub_signup_1": _paid_sub(sid)}),
                       settings=stripe_settings())
        r = _client(db).post("/v1/auth/login", json={"username": "olga",
                                                      "password": FORM["password"]})
        assert r.status_code == 200, r.text

    @pytest.mark.parametrize("status", ["incomplete", "incomplete_expired",
                                        "trialing", "past_due", "unpaid"])
    def test_unpaid_leaves_no_login_and_no_shop(self, db, outbox, status):
        sid = self._verified(db, outbox)
        res = dispatch_event(_sub_event(), db_path=db,
                             provider=FakeBillingProvider({"sub_signup_1": _paid_sub(sid, status)}),
                             settings=stripe_settings())
        assert res.error is None
        assert get_signup(sid, db).status == "email_verified"
        assert _sql(db, "SELECT COUNT(*) FROM users WHERE username = 'olga'") == [(0,)]
        assert _sql(db, "SELECT COUNT(*) FROM shops") == [(0,)]
        assert outbox == []

    def test_a_second_event_makes_nothing_twice_and_sends_no_second_welcome(self, db, outbox):
        sid = self._verified(db, outbox)
        sub = _paid_sub(sid)
        provider = FakeBillingProvider({"sub_signup_1": sub})
        dispatch_event(_sub_event(), db_path=db, provider=provider, settings=stripe_settings())
        dispatch_event(_sub_event(event_id="evt_s2"), db_path=db,
                       provider=FakeBillingProvider({"sub_signup_1": copy.deepcopy(sub)}),
                       settings=stripe_settings())
        assert _sql(db, "SELECT COUNT(*) FROM users WHERE username = 'olga'") == [(1,)]
        assert _sql(db, "SELECT COUNT(*) FROM shops") == [(1,)]
        assert _sql(db, "SELECT COUNT(*) FROM shop_members") == [(1,)]
        assert len(outbox) == 1

    def test_complete_signup_picks_up_after_a_half_finished_run(self, db, outbox):
        sid = self._verified(db, outbox)
        from motodiag.auth.models import User
        from motodiag.auth.signup_repo import _set
        from motodiag.auth.users_repo import create_user
        uid = int(create_user(User(username="olga", email="owner@shop.example",
                                   password_hash="x"), db_path=db))
        _set(sid, "user_id", uid, db)  # the login was made, then the run stopped
        done = complete_signup(sid, "sub_x", db_path=db)
        assert done.user_id == uid and done.shop_id
        assert _sql(db, "SELECT COUNT(*) FROM users WHERE username = 'olga'") == [(1,)]

    def test_paid_before_the_email_was_checked_is_refused(self, db, outbox):
        _sign_up(_client(db))
        with pytest.raises(SignupError, match="before its email was checked"):
            complete_signup(1, "sub_x", db_path=db)
        res = dispatch_event(_sub_event(), db_path=db,
                             provider=FakeBillingProvider({"sub_signup_1": _paid_sub(1)}),
                             settings=stripe_settings())
        assert res.error and "before its email was checked" in res.error
        assert _sql(db, "SELECT COUNT(*) FROM users WHERE username = 'olga'") == [(0,)]

    def test_a_username_taken_after_the_form_is_left_to_the_operator(self, db, outbox):
        sid = self._verified(db, outbox)
        with get_connection(db) as conn:
            conn.execute("INSERT INTO users (username) VALUES ('olga')")
        with pytest.raises(SignupError, match="operator picks another by hand"):
            complete_signup(sid, "sub_x", db_path=db)
        assert _sql(db, "SELECT COUNT(*) FROM shops") == [(0,)]

    def test_a_signup_id_that_is_not_a_number_is_an_error(self, db, outbox):
        sub = _paid_sub(1)
        sub["metadata"]["signup_id"] = "one"
        res = dispatch_event(_sub_event(), db_path=db,
                             provider=FakeBillingProvider({"sub_signup_1": sub}),
                             settings=stripe_settings())
        assert res.error and "not a number" in res.error

    def test_an_ordinary_users_subscription_is_unchanged(self, db, outbox):
        with get_connection(db) as conn:
            uid = conn.execute("INSERT INTO users (username) VALUES ('rider')").lastrowid
        sub = body("subscription_active")
        sub["id"] = "sub_signup_1"
        sub["metadata"] = {"user_id": str(uid), "tier": "shop"}
        res = dispatch_event(_sub_event(), db_path=db,
                             provider=FakeBillingProvider({"sub_signup_1": sub}),
                             settings=stripe_settings())
        assert res.error is None
        assert _sql(db, "SELECT user_id FROM subscriptions") == [(uid,)]
        assert outbox == []


class TestTheIndividualPlan:
    """K150: an individual's sign-up makes a login and nothing else."""

    def _verified(self, db, outbox, **extra) -> int:
        c = _client(db)
        r = _sign_up(c, **{**INDIVIDUAL, **extra})
        assert r.headers["location"] == f"{SITE}/signup/check-email/"
        r = c.post("/v1/signup/confirm", data={"code": _code_from(outbox[0])})
        assert r.headers["location"] == "https://fake-billing.local/checkout/signup/1/individual"
        outbox.clear()
        return 1

    def test_a_shop_name_sent_with_it_is_dropped(self, db, outbox):
        self._verified(db, outbox, shop_name="Not A Shop")
        assert _sql(db, "SELECT shop_name FROM signups") == [(None,)]

    def test_paid_makes_the_login_and_terms_and_no_shop(self, db, outbox):
        sid = self._verified(db, outbox)
        sub = _paid_sub(sid)
        sub["metadata"]["tier"] = "individual"
        sub["items"]["data"][0]["price"]["id"] = "price_test_individual"
        res = dispatch_event(_sub_event(), db_path=db,
                             provider=FakeBillingProvider({"sub_signup_1": sub}),
                             settings=stripe_settings())
        assert res.error is None, res.error
        s = get_signup(sid, db)
        assert s.status == "completed" and s.user_id and s.shop_id is None
        assert _sql(db, "SELECT username, tier FROM users WHERE id = ?", (s.user_id,)) == [
            ("rita", "individual")]
        assert has_accepted(s.user_id, TERMS_VERSION, db_path=db)
        assert _sql(db, "SELECT COUNT(*) FROM shops") == [(0,)]
        assert _sql(db, "SELECT COUNT(*) FROM shop_members WHERE user_id = ?",
                    (s.user_id,)) == [(0,)]
        assert _sql(db, "SELECT tier, status FROM subscriptions WHERE user_id = ?",
                    (s.user_id,)) == [("individual", "active")]
        assert [m.subject for m in outbox] == ["Your Mekno account is ready"]
        assert "rita" in outbox[0].text and "mechanics" not in outbox[0].text

    def test_checkout_asks_for_the_individual_price(self, monkeypatch):
        from support.stripe_fixtures import TEST_KEY, TEST_SECRET

        from motodiag.billing.providers import StripeBillingProvider
        p = StripeBillingProvider(TEST_KEY, TEST_SECRET, settings=stripe_settings())
        assert p._price_id_for_tier("individual") == "price_test_individual"


# ---------------------------------------------------------------- the reset


class TestPasswordReset:
    @pytest.fixture
    def rider(self, db):
        with get_connection(db) as conn:
            uid = conn.execute(
                "INSERT INTO users (username, email, password_hash, is_active) "
                "VALUES ('rider', 'Rider@Shop.example', ?, 1)",
                (hash_password("old password"),)).lastrowid
        return int(uid)

    def test_the_answer_is_the_same_for_any_address(self, db, rider, outbox):
        c = _client(db)
        for email in ("rider@shop.example", "nobody@shop.example", "not-an-address", ""):
            r = c.post("/v1/auth/password-reset", data={"email": email})
            assert r.status_code == 303
            assert r.headers["location"] == f"{SITE}/reset/sent/"
        assert [m.to for m in outbox] == ["rider@shop.example"]

    def test_no_email_for_an_inactive_login_or_one_without_a_password(self, db, outbox):
        with get_connection(db) as conn:
            conn.execute("INSERT INTO users (username, email, password_hash, is_active) "
                         "VALUES ('gone', 'g@shop.example', 'h', 0)")
            conn.execute("INSERT INTO users (username, email, is_active) "
                         "VALUES ('keyonly', 'k@shop.example', 1)")
        c = _client(db)
        c.post("/v1/auth/password-reset", data={"email": "g@shop.example"})
        c.post("/v1/auth/password-reset", data={"email": "k@shop.example"})
        assert outbox == []

    def test_the_link_sets_the_password_and_ends_every_session(self, db, rider, outbox):
        create_session(rider, client="phone", db_path=db)
        create_session(rider, client="web", db_path=db)
        c = _client(db)
        c.post("/v1/auth/password-reset", data={"email": "rider@shop.example"})
        code = _code_from(outbox[0])
        page = c.get(f"/v1/auth/password-reset/confirm?code={code}")
        assert page.status_code == 200 and 'name="new_password"' in page.text
        r = c.post("/v1/auth/password-reset/confirm",
                   data={"code": code, "new_password": "new password", "again": "new password"})
        assert r.headers["location"] == f"{SITE}/reset/done/"
        pw = _sql(db, "SELECT password_hash FROM users WHERE id = ?", (rider,))[0][0]
        assert verify_password("new password", pw)
        assert not [s for s in list_user_sessions(rider, db_path=db) if s.is_active]
        again = c.post("/v1/auth/password-reset/confirm",
                       data={"code": code, "new_password": "third one!", "again": "third one!"})
        assert again.headers["location"] == f"{SITE}/reset/problem/#link"

    @pytest.mark.parametrize("new,again,why", [
        ("new password", "new passwore", "different"),
        ("short", "short", "password"),
    ])
    def test_a_bad_password_keeps_the_link(self, db, rider, outbox, new, again, why):
        c = _client(db)
        c.post("/v1/auth/password-reset", data={"email": "rider@shop.example"})
        code = _code_from(outbox[0])
        r = c.post("/v1/auth/password-reset/confirm",
                   data={"code": code, "new_password": new, "again": again})
        assert r.headers["location"] == f"{SITE}/reset/problem/#{why}"
        ok = c.post("/v1/auth/password-reset/confirm",
                    data={"code": code, "new_password": "new password", "again": "new password"})
        assert ok.headers["location"] == f"{SITE}/reset/done/"

    def test_an_expired_reset_link_changes_nothing(self, db, rider, outbox):
        c = _client(db)
        c.post("/v1/auth/password-reset", data={"email": "rider@shop.example"})
        _sql(db, "UPDATE one_time_codes SET expires_at = 1, issued_at = 0")
        r = c.post("/v1/auth/password-reset/confirm",
                   data={"code": _code_from(outbox[0]), "new_password": "new password",
                         "again": "new password"})
        assert r.headers["location"] == f"{SITE}/reset/problem/#link"
        pw = _sql(db, "SELECT password_hash FROM users WHERE id = ?", (rider,))[0][0]
        assert verify_password("old password", pw)

    def test_only_the_newest_reset_link_works(self, db, rider, outbox):
        c = _client(db)
        c.post("/v1/auth/password-reset", data={"email": "rider@shop.example"})
        c.post("/v1/auth/password-reset", data={"email": "rider@shop.example"})
        old, new = _code_from(outbox[0]), _code_from(outbox[1])
        form = {"new_password": "new password", "again": "new password"}
        assert c.post("/v1/auth/password-reset/confirm",
                      data={"code": old, **form}).headers["location"].endswith("#link")
        assert c.post("/v1/auth/password-reset/confirm",
                      data={"code": new, **form}).headers["location"] == f"{SITE}/reset/done/"

    def test_a_signup_code_never_resets_a_password(self, db, rider, outbox):
        c = _client(db)
        _sign_up(c)
        r = c.post("/v1/auth/password-reset/confirm",
                   data={"code": _code_from(outbox[0]), "new_password": "new password",
                         "again": "new password"})
        assert r.headers["location"] == f"{SITE}/reset/problem/#link"
