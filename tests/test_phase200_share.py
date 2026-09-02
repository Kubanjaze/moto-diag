"""Phase 200 — customer-facing report share links.

Covers: migration 045 shape, the share repo lifecycle (including the
expiry boundary and creator-scoped revocation), the three authed
endpoints, and the PUBLIC page — its four outcomes, its customer-preset
filtering, its HTML escaping, and the two contracts that make an
unauthenticated route on a paywalled API safe (OpenAPI publicity, and
staying OFF the rate-limit exempt list).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from motodiag.api.app import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import SCHEMA_VERSION, get_connection, init_db
from motodiag.reporting.renderers import get_renderer
from motodiag.reporting.share_repo import (
    create_share,
    list_shares_for_session,
    resolve_share,
    revoke_share,
)


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase200_api.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()
    yield path
    reset_settings()


def _make_user(db_path, username="share_user"):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES (?, ?, 'individual', 1)",
            (username, f"{username}@ex.com"),
        )
        return cursor.lastrowid


def _make_session(
    db_path, user_id, make="Honda", model="CBR600RR", notes="mechanic-only",
):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO diagnostic_sessions "
            "(vehicle_make, vehicle_model, vehicle_year, status, user_id, "
            " notes) VALUES (?, ?, 2016, 'open', ?, ?)",
            (make, model, user_id, notes),
        )
        return cursor.lastrowid


def _client(api_db, username="share_user"):
    user_id = _make_user(api_db, username)
    _, plaintext = create_api_key(user_id, db_path=api_db)
    app = create_app(db_path_override=api_db)
    return TestClient(app, raise_server_exceptions=False), plaintext, user_id


def _expire(db_path, token):
    past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE report_shares SET expires_at = ? WHERE token = ?",
            (past, token),
        )


class TestMigration045:
    def test_schema_version_advanced(self, api_db):
        assert SCHEMA_VERSION >= 45

    def test_table_shape(self, api_db):
        with get_connection(api_db) as conn:
            cols = {r[1] for r in conn.execute(
                "PRAGMA table_info(report_shares)",
            )}
        assert {
            "id", "token", "session_id", "created_by_user_id", "preset",
            "created_at", "expires_at", "revoked_at", "view_count",
            "last_viewed_at",
        } <= cols

    def test_token_is_unique(self, api_db):
        uid = _make_user(api_db)
        sid = _make_session(api_db, uid)
        share = create_share(sid, uid, db_path=api_db)
        with pytest.raises(Exception):
            with get_connection(api_db) as conn:
                conn.execute(
                    "INSERT INTO report_shares (token, session_id, "
                    "created_by_user_id, preset, created_at, expires_at) "
                    "VALUES (?, ?, ?, 'customer', 'x', 'y')",
                    (share["token"], sid, uid),
                )


class TestShareRepo:
    def test_create_then_resolve_ok(self, api_db):
        uid = _make_user(api_db)
        sid = _make_session(api_db, uid)
        share = create_share(sid, uid, db_path=api_db)
        assert len(share["token"]) >= 40
        status, row = resolve_share(share["token"], db_path=api_db)
        assert status == "ok"
        assert row["session_id"] == sid

    def test_unknown_token_is_missing(self, api_db):
        status, row = resolve_share("nope", db_path=api_db)
        assert status == "missing" and row is None

    def test_expiry_boundary(self, api_db):
        uid = _make_user(api_db)
        sid = _make_session(api_db, uid)
        share = create_share(sid, uid, ttl_days=1, db_path=api_db)
        expires_at = datetime.fromisoformat(share["expires_at"])
        # One second before → live; exactly at the boundary → expired.
        before = expires_at - timedelta(seconds=1)
        assert resolve_share(
            share["token"], now=before, db_path=api_db,
        )[0] == "ok"
        assert resolve_share(
            share["token"], now=expires_at, db_path=api_db,
        )[0] == "expired"

    def test_revoke_wins_over_expiry(self, api_db):
        uid = _make_user(api_db)
        sid = _make_session(api_db, uid)
        share = create_share(sid, uid, db_path=api_db)
        assert revoke_share(share["id"], uid, db_path=api_db) is True
        _expire(api_db, share["token"])
        # Explicitly killed reads as revoked even once it has also aged out.
        assert resolve_share(
            share["token"], db_path=api_db,
        )[0] == "revoked"

    def test_revoke_is_idempotent_and_creator_scoped(self, api_db):
        owner = _make_user(api_db, "owner")
        other = _make_user(api_db, "other")
        sid = _make_session(api_db, owner)
        share = create_share(sid, owner, db_path=api_db)
        assert revoke_share(share["id"], other, db_path=api_db) is False
        assert revoke_share(share["id"], owner, db_path=api_db) is True
        assert revoke_share(share["id"], owner, db_path=api_db) is False

    def test_list_is_creator_scoped(self, api_db):
        owner = _make_user(api_db, "owner")
        other = _make_user(api_db, "other")
        sid = _make_session(api_db, owner)
        create_share(sid, owner, db_path=api_db)
        assert len(list_shares_for_session(sid, owner, db_path=api_db)) == 1
        assert list_shares_for_session(sid, other, db_path=api_db) == []

    def test_rejects_non_positive_ttl(self, api_db):
        uid = _make_user(api_db)
        sid = _make_session(api_db, uid)
        with pytest.raises(ValueError):
            create_share(sid, uid, ttl_days=0, db_path=api_db)


class TestAuthedEndpoints:
    def test_mint_requires_auth(self, api_db):
        client, _, uid = _client(api_db)
        sid = _make_session(api_db, uid)
        r = client.post(f"/v1/reports/session/{sid}/share", json={})
        assert r.status_code == 401

    def test_mint_returns_absolute_url(self, api_db):
        client, key, uid = _client(api_db)
        sid = _make_session(api_db, uid)
        r = client.post(
            f"/v1/reports/session/{sid}/share", json={},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["token"] in body["url"]
        assert body["url"].startswith("http")
        assert body["session_id"] == sid

    def test_mint_on_someone_elses_session_is_404(self, api_db):
        client, key, _ = _client(api_db, "minter")
        stranger = _make_user(api_db, "stranger")
        sid = _make_session(api_db, stranger)
        r = client.post(
            f"/v1/reports/session/{sid}/share", json={},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 404

    def test_list_then_revoke_roundtrip(self, api_db):
        client, key, uid = _client(api_db)
        sid = _make_session(api_db, uid)
        headers = {"X-API-Key": key}
        minted = client.post(
            f"/v1/reports/session/{sid}/share", json={}, headers=headers,
        ).json()
        listed = client.get(
            f"/v1/reports/session/{sid}/shares", headers=headers,
        )
        assert listed.status_code == 200
        assert [s["id"] for s in listed.json()] == [minted["id"]]
        killed = client.request(
            "DELETE", f"/v1/reports/shares/{minted['id']}", headers=headers,
        )
        assert killed.status_code == 200
        assert killed.json() == {"revoked": True}


class TestPublicPage:
    def _minted(self, api_db, notes="mechanic-only", make="Honda"):
        client, key, uid = _client(api_db)
        sid = _make_session(api_db, uid, make=make, notes=notes)
        body = client.post(
            f"/v1/reports/session/{sid}/share", json={},
            headers={"X-API-Key": key},
        ).json()
        return client, key, body

    def test_live_link_renders_html_without_credentials(self, api_db):
        client, _, share = self._minted(api_db)
        r = client.get(f"/v1/share/{share['token']}")
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("text/html")
        assert r.headers["cache-control"] == "private, no-store"
        assert "<!doctype html>" in r.text
        assert "Diagnostic session report" in r.text

    def test_unknown_token_is_generic_404_html(self, api_db):
        client, _, _ = self._minted(api_db)
        r = client.get("/v1/share/not-a-real-token")
        assert r.status_code == 404
        assert r.headers["content-type"].startswith("text/html")

    def test_revoked_link_is_410(self, api_db):
        client, key, share = self._minted(api_db)
        client.request(
            "DELETE", f"/v1/reports/shares/{share['id']}",
            headers={"X-API-Key": key},
        )
        r = client.get(f"/v1/share/{share['token']}")
        assert r.status_code == 410
        assert "no longer active" in r.text

    def test_expired_link_is_410(self, api_db):
        client, _, share = self._minted(api_db)
        _expire(api_db, share["token"])
        assert client.get(f"/v1/share/{share['token']}").status_code == 410

    def test_customer_preset_hides_the_notes_section(self, api_db):
        client, _, share = self._minted(
            api_db, notes="INTERNAL do not show the customer",
        )
        page = client.get(f"/v1/share/{share['token']}").text
        assert "INTERNAL do not show the customer" not in page
        assert "<h2>Notes</h2>" not in page

    def test_free_text_is_escaped_not_executed(self, api_db):
        client, _, share = self._minted(
            api_db, make="<script>alert(1)</script>",
        )
        page = client.get(f"/v1/share/{share['token']}").text
        assert "<script>alert(1)</script>" not in page
        assert "&lt;script&gt;" in page

    def test_view_is_counted(self, api_db):
        client, key, share = self._minted(api_db)
        client.get(f"/v1/share/{share['token']}")
        client.get(f"/v1/share/{share['token']}")
        with get_connection(api_db) as conn:
            row = conn.execute(
                "SELECT view_count, last_viewed_at FROM report_shares "
                "WHERE id = ?", (share["id"],),
            ).fetchone()
        assert row[0] == 2 and row[1] is not None


class TestHtmlRenderer:
    def test_registered_in_the_factory(self):
        renderer = get_renderer("html")
        assert renderer.content_type.startswith("text/html")

    def test_renders_every_section_variant(self):
        doc = {
            "title": "T", "subtitle": "S", "issued_at": "2026-09-02",
            "footer": "F",
            "sections": [
                {"heading": "Body", "body": "one\ntwo"},
                {"heading": "Rows", "rows": [("k", "v")]},
                {"heading": "Bullets", "bullets": ["a", "b"]},
                {"heading": "Table", "table": {
                    "columns": ["c1"], "rows": [["r1"]]}},
                {"heading": "Videos", "videos": [
                    {"filename": "clip.mp4", "duration_ms": 5,
                     "analysis_state": "analyzed"}]},
            ],
        }
        page = get_renderer("html").render(doc).decode("utf-8")
        for expected in (
            "<h2>Body</h2>", "<p>one</p>", "<dt>k</dt>", "<li>a</li>",
            "<th>c1</th>", "clip.mp4", "<footer>F</footer>",
        ):
            assert expected in page

    def test_unknown_kind_still_raises(self):
        with pytest.raises(ValueError):
            get_renderer("carrier-pigeon")


class TestPublicRouteContracts:
    """The two invariants that keep an unauthenticated route defensible."""

    def test_openapi_marks_the_share_path_public(self, api_db):
        app = create_app(db_path_override=api_db)
        spec = app.openapi()
        op = spec["paths"]["/v1/share/{token}"]["get"]
        assert not op.get("security")
        assert "401" not in op.get("responses", {})
        # ...while a sibling authed route in the same router still is.
        minted = spec["paths"][
            "/v1/reports/session/{session_id}/share"
        ]["post"]
        assert minted.get("security")

    def test_share_route_is_not_rate_limit_exempt(self):
        from motodiag.api.middleware import _RATE_LIMIT_EXEMPT_PATHS
        assert not any(
            "share" in str(path) for path in _RATE_LIMIT_EXEMPT_PATHS
        )
