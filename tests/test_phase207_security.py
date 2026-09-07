"""Phase 207 — security audit findings, pinned as tests.

Each class corresponds to a finding. Live probes against the running
server informed these; the tests are the durable form.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from motodiag.api.app import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import get_connection, init_db

#: Larger than SQLite's 64-bit signed integer, so binding it raises
#: OverflowError inside the repo layer.
OVERSIZED_ID = 999999999999999999999999


@pytest.fixture
def api(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "sec.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()
    with get_connection(path) as conn:
        uid = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES ('sec', 'sec@ex.com', 'company', 1)",
        ).lastrowid
        conn.execute(
            "INSERT INTO subscriptions (user_id, tier, status, "
            " current_period_end) VALUES (?, 'company', 'active', "
            " datetime('now', '+30 days'))", (uid,),
        )
        sid = conn.execute(
            "INSERT INTO diagnostic_sessions (vehicle_make, vehicle_model,"
            " vehicle_year, status, user_id) "
            "VALUES ('Honda','CB',2020,'open',?)", (uid,),
        ).lastrowid
    _, key = create_api_key(uid, db_path=path)
    client = TestClient(
        create_app(db_path_override=path), raise_server_exceptions=False,
    )
    yield client, key, uid, sid
    reset_settings()


class TestOversizedIdIsInvalidInputNotAServerFault:
    """An id beyond SQLite's 64-bit range reached the database before
    anything rejected it, raising OverflowError and surfacing as a 500
    with a full stack trace in the log — on every route family with an
    integer id.

    Nothing leaked to the client, but it let any key-holder fill the
    error log, and it broke the pattern its neighbours follow.
    """

    @pytest.mark.parametrize("path", [
        f"/v1/sessions/{OVERSIZED_ID}",
        f"/v1/reports/session/{OVERSIZED_ID}",
        f"/v1/sessions/{OVERSIZED_ID}/videos",
        f"/v1/shop/{OVERSIZED_ID}/work-orders",
    ])
    def test_oversized_id_is_422_not_500(self, api, path):
        client, key, _uid, _sid = api
        r = client.get(path, headers={"X-API-Key": key})
        assert r.status_code == 422, (
            f"{path} returned {r.status_code}; an unparseable id must "
            "not reach the database"
        )

    def test_the_response_says_nothing_about_internals(self, api):
        client, key, _uid, _sid = api
        r = client.get(
            f"/v1/sessions/{OVERSIZED_ID}", headers={"X-API-Key": key},
        )
        body = r.text.lower()
        for leak in ("sqlite", "traceback", "overflowerror", "site-packages"):
            assert leak not in body, f"response leaks {leak!r}"

    def test_neighbouring_id_shapes_are_unchanged(self, api):
        """The fix must not move behaviour it was not aimed at. A
        non-numeric id was already 422 and a negative one 404; only the
        oversized case was out of line."""
        client, key, _uid, sid = api
        assert client.get(
            "/v1/sessions/abc", headers={"X-API-Key": key},
        ).status_code == 422
        assert client.get(
            "/v1/sessions/-5", headers={"X-API-Key": key},
        ).status_code == 404
        assert client.get(
            f"/v1/sessions/{sid}", headers={"X-API-Key": key},
        ).status_code == 200


class TestAuthenticationBasics:

    @pytest.mark.parametrize("headers", [
        {},
        {"X-API-Key": ""},
        {"X-API-Key": "mdk_live_not_a_real_key"},
        {"X-API-Key": "garbage"},
    ])
    def test_no_valid_key_means_401(self, api, headers):
        client, _key, _uid, _sid = api
        assert client.get("/v1/sessions", headers=headers).status_code == 401


class TestCrossUserIsolation:
    """A second user must not reach the first user's session-scoped data
    by changing the id in the path."""

    def _second_user(self, db_path):
        with get_connection(db_path) as conn:
            uid = conn.execute(
                "INSERT INTO users (username, email, tier, is_active) "
                "VALUES ('other', 'other@ex.com', 'company', 1)",
            ).lastrowid
            conn.execute(
                "INSERT INTO subscriptions (user_id, tier, status, "
                " current_period_end) VALUES (?, 'company', 'active', "
                " datetime('now', '+30 days'))", (uid,),
            )
        return uid

    @pytest.mark.parametrize("template", [
        "/v1/sessions/{sid}",
        "/v1/reports/session/{sid}",
        "/v1/sessions/{sid}/videos",
    ])
    def test_another_user_cannot_read_the_session(
        self, api, tmp_path, template,
    ):
        client, key, _uid, sid = api
        db_path = str(tmp_path / "sec.db")
        other = self._second_user(db_path)
        _, other_key = create_api_key(other, db_path=db_path)

        path = template.format(sid=sid)
        assert client.get(
            path, headers={"X-API-Key": key},
        ).status_code == 200, "owner should be able to read it"
        assert client.get(
            path, headers={"X-API-Key": other_key},
        ).status_code in (403, 404), f"{path} is reachable cross-user"

    def test_another_user_cannot_mint_a_share_link(self, api, tmp_path):
        """Phase 200 links are capability URLs — minting one for someone
        else's session would hand over their report permanently."""
        client, _key, _uid, sid = api
        db_path = str(tmp_path / "sec.db")
        other = self._second_user(db_path)
        _, other_key = create_api_key(other, db_path=db_path)
        r = client.post(
            f"/v1/reports/session/{sid}/share",
            json={}, headers={"X-API-Key": other_key},
        )
        assert r.status_code in (403, 404)


class TestSearchInputIsParameterised:
    """Search terms reach SQL as bound parameters, so quotes and
    statement separators are literal text, not syntax."""

    @pytest.mark.parametrize("payload", [
        "' OR '1'='1",
        "'; DROP TABLE known_issues;--",
        "%' UNION SELECT null,null--",
        '" OR 1=1 --',
    ])
    def test_injection_payloads_are_treated_as_text(self, api, payload):
        client, key, _uid, _sid = api
        r = client.get(
            "/v1/kb/issues", params={"q": payload},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 200
        # Treated as a literal search string, so it matches nothing.
        assert r.json()["items"] == []

    def test_the_table_survives(self, api, tmp_path):
        client, key, _uid, _sid = api
        client.get(
            "/v1/kb/issues", params={"q": "'; DROP TABLE known_issues;--"},
            headers={"X-API-Key": key},
        )
        with get_connection(str(tmp_path / "sec.db")) as conn:
            # The table still answers; a successful DROP would raise.
            conn.execute("SELECT COUNT(*) FROM known_issues").fetchone()


class TestPublicShareRouteIsNotAnOpenDoor:
    """`/v1/share/{token}` is unauthenticated by design, so its
    boundaries are the whole security model."""

    @pytest.mark.parametrize("token", [
        "a" * 43,
        "../../etc/passwd",
        "' OR 1=1--",
        "",
    ])
    def test_unknown_tokens_do_not_resolve(self, api, token):
        client, _key, _uid, _sid = api
        r = client.get(f"/v1/share/{token}")
        assert r.status_code in (404, 405, 307), r.status_code
        assert "PRIVATE" not in r.text.upper()
