"""Phase 329: the Resend sender, what happens when an email fails, the
per-address cap, the 30-day purge, Stripe's cancel address per plan, and
the browser's form-action through every redirect.

No test reaches the network: Resend's transport is a stand-in, the billing
provider is the fake one, and the database is a scratch file.
"""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.error
from pathlib import Path
from urllib.parse import urlparse

import pytest
from pydantic import ValidationError
from support.stripe_fixtures import stripe_settings
from test_phase329_signup_flow import (
    FORM,
    INDIVIDUAL,
    SITE,
    _client,
    _code_from,
    _db,
    _paid_sub,
    _sign_up,
    _sql,
    _sub_event,
)

from motodiag.api import create_app
from motodiag.auth import email_sender as email_mod
from motodiag.auth.email_sender import (
    RESEND_URL,
    Email,
    EmailNotConfigured,
    EmailSendError,
    FakeEmailSender,
    ResendEmailSender,
    get_email_sender,
    urllib_transport,
)
from motodiag.auth.signup_repo import (
    CODE_KEEP_S,
    UNPAID_KEEP_S,
    get_signup,
    purge_stale,
)
from motodiag.billing.providers import FakeBillingProvider
from motodiag.billing.webhook_handlers import dispatch_event
from motodiag.core.config import Environment, Settings
from motodiag.core.database import get_connection

ROOT = Path(__file__).resolve().parent.parent
KEY = "re_test_0123456789abcdef"


class Recorder:
    """Resend's stand-in transport: keeps each request, answers as told."""

    def __init__(self, status=200, body=b'{"id": "em_1"}'):
        self.status, self.body, self.requests = status, body, []

    def __call__(self, req):
        self.requests.append(req)
        return self.status, self.body


def _resend(transport) -> ResendEmailSender:
    return ResendEmailSender(api_key=KEY, sender="Mekno <support@getmekno.com>",
                             reply_to="support@getmekno.com", transport=transport)


MAIL = Email("rider@home.example", "Confirm your email for Mekno",
             "Confirm it here:\nhttps://api.getmekno.com/v1/signup/confirm?code=SECRETCODE\n")


# ---------------------------------------------------------------- the sender


class TestResendSender:
    def test_one_post_to_resend_with_the_key_and_the_email(self):
        t = Recorder()
        _resend(t).send(MAIL)
        (req,) = t.requests
        assert req.full_url == RESEND_URL == "https://api.resend.com/emails"
        assert req.get_method() == "POST"
        headers = {k.lower(): v for k, v in req.header_items()}
        assert headers["authorization"] == f"Bearer {KEY}"
        assert headers["content-type"] == "application/json"
        assert headers["user-agent"].startswith("mekno-server/")
        assert json.loads(req.data) == {
            "from": "Mekno <support@getmekno.com>", "to": ["rider@home.example"],
            "subject": MAIL.subject, "text": MAIL.text,
            "reply_to": "support@getmekno.com"}

    @pytest.mark.parametrize("status,body,shown", [
        (403, b'{"name": "invalid_api_key", "message": "API key is invalid re_test"}',
         "Resend answered 403 (invalid_api_key)"),
        (422, b'{"name": "validation_error"}', "Resend answered 422 (validation_error)"),
        (500, b"<html>oops</html>", "Resend answered 500"),
        (429, b"", "Resend answered 429"),
    ])
    def test_a_refusal_names_the_status_and_never_the_key_or_the_text(self, status, body, shown):
        with pytest.raises(EmailSendError) as e:
            _resend(Recorder(status, body)).send(MAIL)
        assert str(e.value) == shown
        assert KEY not in str(e.value) and "SECRETCODE" not in str(e.value)

    def test_the_network_failing_is_a_send_error(self, monkeypatch):
        def down(req, timeout):
            raise urllib.error.URLError("no route")
        monkeypatch.setattr(email_mod.urllib.request, "urlopen", down)
        with pytest.raises(EmailSendError, match="could not be reached: URLError"):
            urllib_transport(_resend(Recorder()).request(MAIL))

    def test_an_http_error_is_read_as_its_status(self, monkeypatch):
        import io

        def refused(req, timeout):
            raise urllib.error.HTTPError(RESEND_URL, 401, "no", {},
                                         io.BytesIO(b'{"name": "missing_api_key"}'))
        monkeypatch.setattr(email_mod.urllib.request, "urlopen", refused)
        assert urllib_transport(_resend(Recorder()).request(MAIL)) == (
            401, b'{"name": "missing_api_key"}')

    def test_a_bad_address_is_refused_before_any_request(self):
        t = Recorder()
        with pytest.raises(ValueError):
            _resend(t).send(Email("rider@home.example\nBcc: x@y.z", "s", "t"))
        assert t.requests == []

    def test_the_key_is_kept_out_of_every_repr(self):
        assert KEY not in repr(_resend(Recorder()))
        assert KEY not in repr(Settings(resend_api_key=KEY))


class TestChoosingTheSender:
    def test_resend_needs_its_key(self):
        with pytest.raises(EmailNotConfigured, match="MOTODIAG_RESEND_API_KEY"):
            get_email_sender("resend", Settings(email_provider="resend"))
        with pytest.raises(EmailNotConfigured):
            get_email_sender("resend")

    def test_resend_with_its_key_is_the_resend_sender(self):
        s = get_email_sender("resend", Settings(email_provider="resend", resend_api_key=KEY,
                                                email_reply_to="help@getmekno.com"))
        assert isinstance(s, ResendEmailSender)
        assert (s.api_key, s.sender, s.reply_to) == (
            KEY, "Mekno <support@getmekno.com>", "help@getmekno.com")

    def test_fake_stays_the_stand_in(self):
        assert isinstance(get_email_sender("fake", Settings()), FakeEmailSender)

    @pytest.mark.parametrize("name", ["smtp", "Resend", "postmark", ""])
    def test_the_settings_take_only_the_two_names(self, name):
        with pytest.raises(ValidationError):
            Settings(email_provider=name)

    def test_prod_refuses_resend_with_no_key(self):
        s = Settings(env=Environment.PROD, billing_provider="stripe",
                     stripe_api_key="sk_test_x", stripe_webhook_secret="whsec_x",
                     email_provider="resend")
        with pytest.raises(RuntimeError, match="no MOTODIAG_RESEND_API_KEY"):
            create_app(settings=s)

    def test_prod_starts_with_resend_its_key_and_the_switches_on(self):
        s = Settings(env=Environment.PROD, billing_provider="stripe",
                     stripe_api_key="sk_test_x", stripe_webhook_secret="whsec_x",
                     email_provider="resend", resend_api_key=KEY,
                     individual_signup_enabled=True, password_reset_email_enabled=True)
        create_app(settings=s)


# ---------------------------------------------------------------- an email that fails


class Failing:
    def __init__(self):
        self.tried = 0

    def send(self, email):
        self.tried += 1
        raise EmailSendError("Resend answered 500")


@pytest.fixture
def failing(monkeypatch):
    sender = Failing()
    monkeypatch.setattr("motodiag.api.routes.signup.get_email_sender",
                        lambda provider, settings=None: sender)
    monkeypatch.setattr(email_mod, "get_email_sender", lambda provider, settings=None: sender)
    return sender


@pytest.fixture
def outbox(monkeypatch):
    sender = FakeEmailSender()
    monkeypatch.setattr("motodiag.api.routes.signup.get_email_sender",
                        lambda provider, settings=None: sender)
    monkeypatch.setattr(email_mod, "get_email_sender", lambda provider, settings=None: sender)
    return sender.outbox


@pytest.fixture
def db(tmp_path, monkeypatch):
    return _db(tmp_path, monkeypatch)


class TestAnEmailThatFails:
    def test_the_form_says_later_and_keeps_the_signup(self, db, failing):
        r = _sign_up(_client(db))
        assert r.headers["location"] == f"{SITE}/signup/problem/#later"
        assert failing.tried == 1
        assert _sql(db, "SELECT status FROM signups") == [("pending_email",)]

    def test_the_reset_answers_as_ever(self, db, failing):
        with get_connection(db) as conn:
            conn.execute("INSERT INTO users (username, email, password_hash, is_active) "
                         "VALUES ('rider', 'rider@home.example', 'x', 1)")
        r = _client(db).post("/v1/auth/password-reset", data={"email": "rider@home.example"})
        assert r.headers["location"] == f"{SITE}/reset/sent/"
        assert failing.tried == 1

    def _verified(self, db, monkeypatch, **form):
        sender = FakeEmailSender()
        monkeypatch.setattr("motodiag.api.routes.signup.get_email_sender",
                            lambda provider, settings=None: sender)
        c = _client(db)
        _sign_up(c, **form)
        c.post("/v1/signup/confirm", data={"code": _code_from(sender.outbox[0])})
        return 1

    def test_a_failed_welcome_still_makes_the_account(self, db, monkeypatch, caplog):
        sid = self._verified(db, monkeypatch)
        failing = Failing()
        monkeypatch.setattr(email_mod, "get_email_sender", lambda p, settings=None: failing)
        provider = FakeBillingProvider({"sub_signup_1": _paid_sub(sid)})
        with caplog.at_level(logging.ERROR):
            res = dispatch_event(_sub_event(), db_path=db, provider=provider,
                                 settings=stripe_settings())
        assert res.error is None and res.processed
        assert get_signup(sid, db).status == "completed"
        assert failing.tried == 1
        assert "the welcome email was not sent" in caplog.text

    def test_a_paid_signup_that_cannot_finish_tells_support_and_is_kept(self, db, monkeypatch):
        sid = self._verified(db, monkeypatch)
        with get_connection(db) as conn:
            conn.execute("INSERT INTO users (username) VALUES ('olga')")
        sent = FakeEmailSender()
        monkeypatch.setattr(email_mod, "get_email_sender", lambda p, settings=None: sent)
        provider = FakeBillingProvider({"sub_signup_1": _paid_sub(sid)})
        res = dispatch_event(_sub_event(), db_path=db, provider=provider,
                             settings=stripe_settings())
        assert res.error and "operator picks another by hand" in res.error
        (notice,) = sent.outbox
        assert notice.to == "support@getmekno.com"
        assert f"sign-up {sid}" in notice.subject and "refund" in notice.text
        assert _sql(db, "SELECT stripe_subscription_id, user_id FROM signups") == [
            ("sub_signup_1", None)]
        # The purge keeps it, however old.
        purge_stale(time.time() + 365 * 86400, db_path=db)
        assert _sql(db, "SELECT COUNT(*) FROM signups") == [(1,)]


# ---------------------------------------------------------------- the per-address cap


class TestThePerAddressCap:
    def test_five_links_an_hour_then_too_many(self, db, outbox):
        c = _client(db)
        for n in range(5):
            r = _sign_up(c, username=f"olga{n}")
            assert r.headers["location"] == f"{SITE}/signup/check-email/", n
        r = _sign_up(c, username="olga9", email="OWNER@shop.example")
        assert r.headers["location"] == f"{SITE}/signup/problem/#too-many"
        assert len(outbox) == 5
        assert _sql(db, "SELECT COUNT(*) FROM signups") == [(5,)]
        # Another address is not held.
        assert _sign_up(c, username="other", email="other@shop.example").headers[
            "location"] == f"{SITE}/signup/check-email/"

    def test_the_cap_comes_from_the_settings_and_counts_an_hour(
            self, tmp_path, monkeypatch, outbox):
        monkeypatch.setenv("MOTODIAG_SIGNUP_EMAILS_PER_ADDRESS_PER_HOUR", "1")
        db = _db(tmp_path, monkeypatch)
        c = _client(db)
        assert _sign_up(c).headers["location"].endswith("/signup/check-email/")
        assert _sign_up(c, username="olga2").headers["location"].endswith("#too-many")
        with get_connection(db) as conn:
            conn.execute("UPDATE one_time_codes SET issued_at = issued_at - 3601")
        assert _sign_up(c, username="olga3").headers["location"].endswith("/signup/check-email/")

    def test_resets_and_signups_share_the_cap_and_a_held_reset_looks_the_same(
            self, tmp_path, monkeypatch, outbox):
        monkeypatch.setenv("MOTODIAG_SIGNUP_EMAILS_PER_ADDRESS_PER_HOUR", "2")
        db = _db(tmp_path, monkeypatch)
        with get_connection(db) as conn:
            conn.execute("INSERT INTO users (username, email, password_hash, is_active) "
                         "VALUES ('rider', 'rider@home.example', 'x', 1)")
        c = _client(db)
        _sign_up(c, **INDIVIDUAL, password="correct horse", accept_terms="yes")
        r1 = c.post("/v1/auth/password-reset", data={"email": "rider@home.example"})
        r2 = c.post("/v1/auth/password-reset", data={"email": "Rider@home.example"})
        assert r1.headers["location"] == r2.headers["location"] == f"{SITE}/reset/sent/"
        assert len(outbox) == 2


# ---------------------------------------------------------------- the plans on the form


class TestThePlansOnTheForm:
    def test_company_is_not_on_the_form(self, db, outbox):
        r = _sign_up(_client(db), tier="company")
        assert r.headers["location"] == f"{SITE}/signup/problem/#plan"
        assert _sql(db, "SELECT COUNT(*) FROM signups") == [(0,)] and outbox == []

    @pytest.mark.parametrize("form,cancel", [
        ({}, f"{SITE}/signup/"),
        ({**INDIVIDUAL}, f"{SITE}/signup/individual/"),
    ])
    def test_stripes_cancel_goes_back_to_the_plans_own_form(self, db, outbox, form, cancel):
        seen = {}

        class Watching(FakeBillingProvider):
            def create_signup_checkout_session(self, signup_id, email, tier,
                                               success_url, cancel_url):
                seen.update(success=success_url, cancel=cancel_url)
                return super().create_signup_checkout_session(
                    signup_id, email, tier, success_url, cancel_url)

        c = _client(db, provider=Watching())
        _sign_up(c, **form)
        c.post("/v1/signup/confirm", data={"code": _code_from(outbox[0])})
        assert seen == {"success": f"{SITE}/signup/paid/", "cancel": cancel}


# ---------------------------------------------------------------- the 30-day purge


class TestThePurge:
    def test_unpaid_signups_go_after_30_days_with_their_codes(self, db, outbox):
        c = _client(db)
        _sign_up(c)
        _sign_up(c, **INDIVIDUAL)
        with get_connection(db) as conn:
            conn.execute("UPDATE signups SET created_at = '2026-01-01T00:00:00.000+00:00' "
                         "WHERE id = 1")
        assert purge_stale(time.time(), db_path=db) == (1, 0)
        assert _sql(db, "SELECT id FROM signups") == [(2,)]
        assert _sql(db, "SELECT subject FROM one_time_codes") == [("signup:2",)]

    def test_the_forms_post_runs_the_purge(self, db, outbox):
        c = _client(db)
        _sign_up(c)
        with get_connection(db) as conn:
            conn.execute("UPDATE signups SET created_at = '2026-01-01 00:00:00'")
        _sign_up(c, **INDIVIDUAL)
        assert _sql(db, "SELECT username FROM signups") == [("rita",)]

    def test_a_completed_signup_and_a_fresh_one_stay(self, db, outbox):
        c = _client(db)
        _sign_up(c)
        with get_connection(db) as conn:
            conn.execute("UPDATE signups SET status = 'completed', user_id = 1, "
                         "created_at = '2026-01-01 00:00:00'")
        _sign_up(c, **INDIVIDUAL)
        assert purge_stale(time.time(), db_path=db)[0] == 0
        assert purge_stale(time.time() + UNPAID_KEEP_S - 3600, db_path=db)[0] == 0
        assert purge_stale(time.time() + UNPAID_KEEP_S + 3600, db_path=db)[0] == 1

    def test_codes_go_a_day_after_they_expire(self, db, outbox):
        _sign_up(_client(db))
        (expires,) = _sql(db, "SELECT expires_at FROM one_time_codes")[0]
        assert purge_stale(expires + CODE_KEEP_S - 1, db_path=db)[1] == 0
        assert purge_stale(expires + CODE_KEEP_S + 1, db_path=db)[1] == 1


# ---------------------------------------------------- form-action, through every redirect


def _site_rules() -> dict[str, str]:
    """`site/_headers`: each path rule's Content-Security-Policy."""
    rules, path = {}, None
    for line in (ROOT / "site" / "_headers").read_text(encoding="utf-8").splitlines():
        if line and not line[0].isspace():
            path = line.strip()
        elif line.strip().startswith("Content-Security-Policy:") and path:
            rules[path] = line.split(":", 1)[1].strip()
    return rules


def _form_action(csp: str) -> list[str]:
    for part in csp.split(";"):
        bits = part.split()
        if bits and bits[0] == "form-action":
            return bits[1:]
    return []


def _allows(sources: list[str], target: str, own_origin: str) -> bool:
    origin = "{0.scheme}://{0.netloc}".format(urlparse(target))
    return any(s == origin or (s == "'self'" and origin == own_origin) for s in sources)


SITE_PAGES = re.compile(r'action="(https://[^"]+)"')


class TestFormActionThroughEveryRedirect:
    """A browser holds a form's redirect targets to the posting page's
    form-action too, so each post's every answer must be allowed."""

    def test_the_sites_forms_may_reach_the_api_and_come_back_to_the_site(self):
        rules = _site_rules()
        for path in ("/signup/*", "/reset/*"):
            sources = _form_action(rules[path])
            for target in ("https://api.getmekno.com/v1/signup",
                           f"{SITE}/signup/check-email/", f"{SITE}/reset/sent/",
                           f"{SITE}/signup/problem/#email"):
                assert _allows(sources, target, SITE), (path, target)
            assert not _allows(sources, "https://evil.example/x", SITE)

    def test_every_other_page_keeps_no_form(self):
        rules = _site_rules()
        assert set(rules) == {"/*", "/signup/*", "/reset/*"}
        assert _form_action(rules["/*"]) == ["'none'"]

    def test_each_published_form_posts_where_its_rule_allows(self):
        rules = _site_rules()
        for page in (ROOT / "site").rglob("index.html"):
            rel = "/" + page.relative_to(ROOT / "site").parent.as_posix() + "/"
            for target in SITE_PAGES.findall(page.read_text(encoding="utf-8")):
                rule = "/signup/*" if rel.startswith("/signup/") else \
                    "/reset/*" if rel.startswith("/reset/") else "/*"
                assert _allows(_form_action(rules[rule]), target, SITE), (rel, target)

    def _redirects(self, db, outbox):
        c = _client(db)
        seen = [_sign_up(c, email="bad").headers["location"],
                _sign_up(c).headers["location"]]
        page = c.get("/v1/signup/confirm", params={"code": _code_from(outbox[0])})
        seen.append(c.post("/v1/signup/confirm",
                           data={"code": _code_from(outbox[0])}).headers["location"])
        seen.append(c.post("/v1/signup/confirm", data={"code": "x"}).headers["location"])
        return page, seen

    def test_the_button_pages_allow_the_site_and_stripes_checkout(self, db, outbox):
        page, seen = self._redirects(db, outbox)
        sources = _form_action(page.headers["content-security-policy"])
        api = "http://testserver"
        for target in seen[2:] + ["https://checkout.stripe.com/c/pay/cs_live_x",
                                  f"{SITE}/signup/paid/", f"{SITE}/reset/done/",
                                  f"{api}/v1/signup/confirm"]:
            if "fake-billing.local" in target:
                continue
            assert _allows(sources, target, api), target
        assert not _allows(sources, "https://evil.example/", api)
        assert "default-src 'none'" in page.headers["content-security-policy"]

    def test_the_forms_answers_are_all_site_pages(self, db, outbox):
        _, seen = self._redirects(db, outbox)
        assert all(t.startswith(f"{SITE}/") for t in seen[:2] + seen[3:])


def test_form_keeps_its_fields():
    """The sibling's form helpers still name every field the route reads."""
    assert set(FORM) == {"email", "owner_name", "username", "password", "shop_name",
                         "tier", "accept_terms"}


# ---------------------------------------------------------------- bug fix #2: codes and the log


class TestCodesStayOutOfTheLog:
    """A link's code in the access line (uvicorn logs the query string) is
    masked as a session token is, in the log and in crash reports."""

    def test_every_code_carries_the_prefix_the_filter_masks(self, db, outbox):
        from motodiag.auth.one_time_codes import CODE_PREFIX, issue_code
        assert CODE_PREFIX == "mdc_"
        assert issue_code("reset_password", "user:1", now=0).code.startswith("mdc_")
        _sign_up(_client(db))
        assert _code_from(outbox[0]).startswith("mdc_")

    def test_the_access_line_masks_the_code(self, db, outbox):
        from motodiag.cli.serve import RedactSessionTokens
        _sign_up(_client(db))
        code = _code_from(outbox[0])
        rec = logging.LogRecord("uvicorn.access", logging.INFO, "h11_impl.py", 1,
                                '%s - "%s %s HTTP/%s" %d', ("1.2.3.4:5", "GET",
                                f"/v1/signup/confirm?code={code}", "1.1", 200), None)
        RedactSessionTokens().filter(rec)
        assert code not in rec.getMessage() and "redacted]" in rec.getMessage()

    def test_crash_reports_mask_the_code(self):
        from motodiag.telemetry.events import redact
        out = redact("GET /v1/auth/password-reset/confirm?code=mdc_AbC-_123xyz failed")
        assert "mdc_AbC" not in out and "redacted]" in out


# ---------------------------------------------------------------- bug fix #3: the username's case


class TestTheUsernamesCase:
    def test_a_login_in_another_case_takes_the_name(self, db, outbox):
        with get_connection(db) as conn:
            conn.execute("INSERT INTO users (username) VALUES ('Tess')")
        r = _sign_up(_client(db), username="tess")
        assert r.headers["location"] == f"{SITE}/signup/problem/#username-taken"

    def test_the_name_signed_up_with_is_the_name_signed_in_with(self, db, outbox):
        c = _client(db)
        _sign_up(c, **INDIVIDUAL, password="correct horse", accept_terms="yes")
        c.post("/v1/signup/confirm", data={"code": _code_from(outbox[0])})
        sid = _sql(db, "SELECT id FROM signups")[0][0]
        provider = FakeBillingProvider({"sub_signup_1": _paid_sub(sid)})
        dispatch_event(_sub_event(), db_path=db, provider=provider, settings=stripe_settings())
        r = c.post("/v1/auth/login", json={"username": INDIVIDUAL["username"],
                                           "password": "correct horse"})
        assert r.status_code == 200 and r.json()["token"].startswith("mds_")


# ---------------------------------------------------------------- bug fix #4: one sign-up, one payment


class TestOnePayment:
    def _open(self, db, outbox, provider):
        c = _client(db, provider=provider)
        _sign_up(c, **INDIVIDUAL, password="correct horse", accept_terms="yes")
        code = _code_from(outbox[0])
        first = c.post("/v1/signup/confirm", data={"code": code})
        return c, code, first

    def test_reopening_the_link_returns_to_the_same_checkout(self, db, outbox):
        p = FakeBillingProvider()
        c, code, first = self._open(db, outbox, p)
        again = c.post("/v1/signup/confirm", data={"code": code})
        assert again.headers["location"] == first.headers["location"]
        assert len(p.checkout_sessions) == 1
        assert _sql(db, "SELECT stripe_checkout_session_id FROM signups") == [
            ("cs_fake_signup_1_individual",)]

    def test_a_paid_checkout_sends_the_link_to_the_paid_page(self, db, outbox):
        p = FakeBillingProvider()
        c, code, _ = self._open(db, outbox, p)
        p.checkout_sessions["cs_fake_signup_1_individual"]["status"] = "complete"
        again = c.post("/v1/signup/confirm", data={"code": code})
        assert again.headers["location"] == f"{SITE}/signup/paid/"
        assert len(p.checkout_sessions) == 1

    def test_a_subscription_on_the_signup_sends_the_link_to_the_paid_page(self, db, outbox):
        p = FakeBillingProvider()
        c, code, _ = self._open(db, outbox, p)
        with get_connection(db) as conn:
            conn.execute("UPDATE signups SET stripe_subscription_id = 'sub_x'")
        again = c.post("/v1/signup/confirm", data={"code": code})
        assert again.headers["location"] == f"{SITE}/signup/paid/"
        assert len(p.checkout_sessions) == 1

    def test_only_an_expired_checkout_makes_way_for_a_new_one(self, db, outbox):
        p = FakeBillingProvider()
        c, code, _ = self._open(db, outbox, p)
        p.checkout_sessions["cs_fake_signup_1_individual"]["status"] = "expired"
        c.post("/v1/signup/confirm", data={"code": code})
        assert len(p.checkout_sessions) == 2
        assert _sql(db, "SELECT stripe_checkout_session_id FROM signups") == [
            ("cs_fake_signup_1_individual_2",)]

    def test_stripe_unreachable_on_the_reopen_says_later(self, db, outbox):
        from motodiag.billing.providers import BillingProviderError

        class Down(FakeBillingProvider):
            def retrieve_checkout_session(self, session_id):
                raise BillingProviderError("down")
        p = Down()
        c, code, _ = self._open(db, outbox, p)
        again = c.post("/v1/signup/confirm", data={"code": code})
        assert again.headers["location"] == f"{SITE}/signup/problem/#later"
        assert len(p.checkout_sessions) == 1

    def test_the_stripe_provider_reads_the_checkout_back(self):
        from motodiag.billing.providers import StripeBillingProvider
        assert "retrieve_checkout_session" in StripeBillingProvider.__dict__
