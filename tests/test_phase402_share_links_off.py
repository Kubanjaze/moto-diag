"""Phase 402 — customer share links off, and the Stripe return pages (K74).

``MOTODIAG_SHARE_LINKS_ENABLED=false`` refuses minting a link and opening
any link, old ones too (K79), and the prod start-up check stops asking for
``MOTODIAG_PUBLIC_BASE_URL``. ``MOTODIAG_STRIPE_RETURN_PAGE_URL`` is one
address for the six Stripe return settings, unless one is set on its own.
With both at their defaults everything behaves as before; the controls
below hold that.
"""

from __future__ import annotations

from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from motodiag.api.app import create_app
from motodiag.api.routes.share import SHARE_LINKS_OFF_MESSAGE
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.config import (
    STRIPE_RETURN_URL_FIELDS,
    Environment,
    Settings,
    reset_settings,
)
from motodiag.core.database import get_connection, init_db
from motodiag.core.public_url import (
    check_public_base_url,
    startup_public_url_problems,
)

PAGE = "https://example.org/thanks"

#: Today's defaults for the six, as Phase 176 and 273 set them.
DEFAULTS = {
    "checkout_success_url": "http://localhost:3000/billing/success",
    "checkout_cancel_url": "http://localhost:3000/billing/cancel",
    "billing_portal_return_url": "http://localhost:3000/billing",
    "invoice_payment_return_url": "http://localhost:3000/payments/done",
    "connect_return_url": "http://localhost:3000/payments/connected",
    "connect_refresh_url": "http://localhost:3000/payments/connect-again",
}

#: Every URL tests/test_f64_public_url.py checks.
F64_URLS = [
    "",
    "http://10.0.0.147:8000",
    "http://192.168.1.50:8000",
    "http://172.16.4.4:8000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://macbook.local",
    "http://100.80.109.103:8000",
    "https://app.motodiag.com",
    "https://motodiag.example.co.uk/",
    "https://kerwyns-macbook-air.taila45995.ts.net",
    "https://box.tailnet.ts.net",
    "http://app.motodiag.com",
    "ftp://app.motodiag.com",
    "https://app.motodiag.com/api",
    "https://app.motodiag.com/",
]


@pytest.fixture
def clean_env(monkeypatch):
    """No 402 setting and none of the six given by the environment."""
    for name in ("SHARE_LINKS_ENABLED", "STRIPE_RETURN_PAGE_URL",
                 "PUBLIC_BASE_URL", "ENV"):
        monkeypatch.delenv(f"MOTODIAG_{name}", raising=False)
    for field in STRIPE_RETURN_URL_FIELDS:
        monkeypatch.delenv(f"MOTODIAG_{field.upper()}", raising=False)
    return monkeypatch


# ---------------------------------------------------------------------------
# The settings
# ---------------------------------------------------------------------------


class TestSettings:
    def test_the_new_settings_default_to_todays_behaviour(self, clean_env):
        s = Settings()
        assert s.share_links_enabled is True
        assert s.stripe_return_page_url == ""

    def test_the_six_keep_their_defaults(self, clean_env):
        s = Settings()
        assert {f: getattr(s, f) for f in STRIPE_RETURN_URL_FIELDS} == DEFAULTS

    def test_the_six_are_the_six(self):
        assert set(STRIPE_RETURN_URL_FIELDS) == set(DEFAULTS)

    def test_the_switch_is_read(self, clean_env):
        clean_env.setenv("MOTODIAG_SHARE_LINKS_ENABLED", "false")
        assert Settings().share_links_enabled is False

    def test_the_page_alone_sets_all_six(self, clean_env):
        clean_env.setenv("MOTODIAG_STRIPE_RETURN_PAGE_URL", PAGE)
        s = Settings()
        assert {f: getattr(s, f) for f in STRIPE_RETURN_URL_FIELDS} == {
            f: PAGE for f in STRIPE_RETURN_URL_FIELDS
        }

    @pytest.mark.parametrize("field", STRIPE_RETURN_URL_FIELDS)
    def test_one_given_on_its_own_keeps_its_value(self, clean_env, field):
        own = f"https://example.org/{field}"
        clean_env.setenv("MOTODIAG_STRIPE_RETURN_PAGE_URL", PAGE)
        clean_env.setenv(f"MOTODIAG_{field.upper()}", own)
        s = Settings()
        assert getattr(s, field) == own
        for other in STRIPE_RETURN_URL_FIELDS:
            if other != field:
                assert getattr(s, other) == PAGE, other

    def test_the_page_empty_with_one_given(self, clean_env):
        own = "https://example.org/cancel"
        clean_env.setenv("MOTODIAG_CHECKOUT_CANCEL_URL", own)
        s = Settings()
        assert s.checkout_cancel_url == own
        for other in STRIPE_RETURN_URL_FIELDS:
            if other != "checkout_cancel_url":
                assert getattr(s, other) == DEFAULTS[other], other

    def test_the_plans_finish_line(self, clean_env):
        clean_env.setenv("MOTODIAG_STRIPE_RETURN_PAGE_URL", PAGE)
        clean_env.setenv(
            "MOTODIAG_CHECKOUT_CANCEL_URL", "https://example.org/cancel",
        )
        s = Settings()
        values = [getattr(s, f) for f in STRIPE_RETURN_URL_FIELDS]
        assert values.count(PAGE) == 5
        assert s.checkout_cancel_url == "https://example.org/cancel"


# ---------------------------------------------------------------------------
# The share routes
# ---------------------------------------------------------------------------


@pytest.fixture
def api(tmp_path, clean_env):
    db = str(tmp_path / "phase402.db")
    init_db(db)
    clean_env.setenv("MOTODIAG_DB_PATH", db)
    for tier in ("anonymous", "individual", "shop", "company"):
        clean_env.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()
    with get_connection(db) as conn:
        uid = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES ('p402', 'p402@ex.com', 'individual', 1)",
        ).lastrowid
        sid = conn.execute(
            "INSERT INTO diagnostic_sessions "
            "(vehicle_make, vehicle_model, vehicle_year, status, user_id) "
            "VALUES ('Honda', 'CB', 2020, 'open', ?)", (uid,),
        ).lastrowid
    _, key = create_api_key(uid, db_path=db)
    client = TestClient(
        create_app(db_path_override=db), raise_server_exceptions=False,
    )

    def switch(on: bool) -> None:
        clean_env.setenv(
            "MOTODIAG_SHARE_LINKS_ENABLED", "true" if on else "false",
        )
        reset_settings()

    yield {"db": db, "sid": sid, "key": key, "client": client,
           "switch": switch}
    reset_settings()


def _mint(api, sid=None):
    return api["client"].post(
        f"/v1/reports/session/{sid or api['sid']}/share", json={},
        headers={"X-API-Key": api["key"]},
    )


def _share_rows(db) -> list[tuple]:
    with get_connection(db) as conn:
        return conn.execute(
            "SELECT id, view_count FROM report_shares ORDER BY id",
        ).fetchall()


class TestMinting:
    def test_off_refuses_with_the_message_and_writes_no_row(self, api):
        api["switch"](False)
        r = _mint(api)
        assert r.status_code == 403, r.text
        assert r.json()["detail"] == SHARE_LINKS_OFF_MESSAGE
        assert _share_rows(api["db"]) == []

    def test_off_is_the_same_answer_for_a_session_that_does_not_exist(
        self, api,
    ):
        api["switch"](False)
        r = _mint(api, sid=987654)
        assert r.status_code == 403
        assert r.json()["detail"] == SHARE_LINKS_OFF_MESSAGE

    def test_on_mints_as_today(self, api):
        api["switch"](True)
        r = _mint(api)
        assert r.status_code == 201, r.text
        assert len(_share_rows(api["db"])) == 1

    def test_the_message_is_the_plans(self):
        assert SHARE_LINKS_OFF_MESSAGE == (
            "Share links are switched off for now. "
            "You can still send the report as a PDF."
        )


class TestOpening:
    def test_an_old_link_stops_opening_and_comes_back(self, api):
        token = _mint(api).json()["token"]
        before = _share_rows(api["db"])

        api["switch"](False)
        r = api["client"].get(f"/v1/share/{token}")
        assert r.status_code == 404
        assert r.headers["content-type"].startswith("text/html")
        assert "<title>Report links are off</title>" in r.text
        assert _share_rows(api["db"]) == before, "no view is recorded"

        made_up = api["client"].get("/v1/share/not-a-real-token")
        assert made_up.status_code == 404
        assert made_up.text == r.text

        api["switch"](True)
        again = api["client"].get(f"/v1/share/{token}")
        assert again.status_code == 200, again.text
        assert "Diagnostic session report" in again.text

    def test_off_does_not_look_the_token_up(self, api):
        api["switch"](False)
        with patch("motodiag.api.routes.share.resolve_share") as resolve:
            r = api["client"].get("/v1/share/anything")
        assert r.status_code == 404
        assert not resolve.called

    def test_on_an_unknown_token_keeps_todays_page(self, api):
        r = api["client"].get("/v1/share/not-a-real-token")
        assert r.status_code == 404
        assert "Link not found" in r.text

    def test_off_list_and_revoke_still_answer(self, api):
        share = _mint(api).json()
        api["switch"](False)
        listed = api["client"].get(
            f"/v1/reports/session/{api['sid']}/shares",
            headers={"X-API-Key": api["key"]},
        )
        assert listed.status_code == 200, listed.text
        assert [s["id"] for s in listed.json()] == [share["id"]]
        revoked = api["client"].request(
            "DELETE", f"/v1/reports/shares/{share['id']}",
            headers={"X-API-Key": api["key"]},
        )
        assert revoked.status_code == 200
        assert revoked.json() == {"revoked": True}


class TestTheDocument:
    def test_the_mint_declares_its_403(self, api):
        spec = api["client"].get("/openapi.json").json()
        responses = spec["paths"]["/v1/reports/session/{session_id}/share"][
            "post"]["responses"]
        assert responses["403"]["description"] == SHARE_LINKS_OFF_MESSAGE


# ---------------------------------------------------------------------------
# The start-up rule
# ---------------------------------------------------------------------------


def _settings(clean_env, *, on: bool, url: str, env: str) -> Settings:
    clean_env.setenv("MOTODIAG_SHARE_LINKS_ENABLED", "true" if on else "false")
    clean_env.setenv("MOTODIAG_PUBLIC_BASE_URL", url)
    clean_env.setenv("MOTODIAG_ENV", env)
    return Settings()


class TestStartupRule:
    @pytest.mark.parametrize("url", [
        "", "https://box.tailnet.ts.net",
    ])
    def test_off_checks_nothing_in_prod(self, clean_env, url):
        s = _settings(clean_env, on=False, url=url, env="prod")
        assert startup_public_url_problems(s) == []

    @pytest.mark.parametrize("env", [Environment.PROD, Environment.DEV])
    @pytest.mark.parametrize("url", F64_URLS)
    def test_on_is_exactly_the_old_check(self, clean_env, url, env):
        s = _settings(clean_env, on=True, url=url, env=env.value)
        assert startup_public_url_problems(s) == check_public_base_url(
            url, env,
        )

    def test_on_in_prod_with_no_address_still_blocks(self, clean_env):
        s = _settings(clean_env, on=True, url="", env="prod")
        problems = startup_public_url_problems(s)
        assert problems and problems[0].severity == "error"


@pytest.fixture
def serve_cli(tmp_path, clean_env):
    clean_env.setenv("MOTODIAG_DB_PATH", str(tmp_path / "phase402_serve.db"))
    clean_env.setenv("MOTODIAG_ENV", "prod")
    clean_env.setenv("MOTODIAG_PUBLIC_BASE_URL", "")
    reset_settings()

    from motodiag.cli.serve import register_serve

    @click.group()
    def root():
        pass

    register_serve(root)
    yield root
    reset_settings()


class TestServe:
    OFF_LINE = (
        "Customer share links are off (MOTODIAG_SHARE_LINKS_ENABLED=false): "
        "MOTODIAG_PUBLIC_BASE_URL is not checked."
    )

    def _run(self, root):
        reset_settings()
        with patch("uvicorn.run") as run:
            result = CliRunner().invoke(root, ["serve"])
        return result, run

    def test_prod_off_with_no_address_starts_and_says_so(
        self, serve_cli, clean_env,
    ):
        clean_env.setenv("MOTODIAG_SHARE_LINKS_ENABLED", "false")
        result, run = self._run(serve_cli)
        assert result.exit_code == 0, result.output
        assert run.called
        assert self.OFF_LINE in result.output

    def test_prod_on_with_no_address_refuses_as_today(
        self, serve_cli, clean_env,
    ):
        clean_env.setenv("MOTODIAG_SHARE_LINKS_ENABLED", "true")
        result, run = self._run(serve_cli)
        assert result.exit_code != 0
        assert not run.called
        assert "Refusing to start in env=prod" in result.output
        assert "Fix MOTODIAG_PUBLIC_BASE_URL" in result.output
        assert self.OFF_LINE not in result.output
