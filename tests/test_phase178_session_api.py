"""Phase 178 — Diagnostic session endpoints tests.

Five classes, ~32 tests. Zero AI.
"""

from __future__ import annotations

import json as _json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import get_connection, init_db
from motodiag.core.session_repo import (
    SessionOwnershipError,
    SessionQuotaExceededError,
    TIER_SESSION_MONTHLY_LIMITS,
    add_fault_code_for_owner,
    add_symptom_for_owner,
    append_note_for_owner,
    check_session_quota,
    close_session_for_owner,
    count_sessions_this_month_for_owner,
    create_session_for_owner,
    get_session_for_owner,
    list_sessions_for_owner,
    reopen_session_for_owner,
    update_session_for_owner,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase178.db")
    init_db(path)
    return path


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase178_api.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()
    yield path
    reset_settings()


def _make_user(db_path, username="bob"):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES (?, 'b@ex.com', 'individual', 1)",
            (username,),
        )
        return cursor.lastrowid


def _make_sub(db_path, user_id, tier="individual"):
    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT INTO subscriptions
               (user_id, tier, status, current_period_end)
               VALUES (?, ?, 'active', datetime('now', '+30 days'))""",
            (user_id, tier),
        )


# ===========================================================================
# 1. Owner-scoped repo helpers
# ===========================================================================


class TestOwnerScopedRepo:

    def test_create_stamps_owner(self, db):
        sid = create_session_for_owner(
            owner_user_id=42,
            vehicle_make="Honda", vehicle_model="CBR600",
            vehicle_year=2005, db_path=db,
        )
        row = get_session_for_owner(sid, 42, db_path=db)
        assert row is not None
        assert row["user_id"] == 42
        assert row["status"] == "open"

    def test_get_cross_owner_returns_none(self, db):
        sid = create_session_for_owner(
            1, "Honda", "CBR600", 2005, db_path=db,
        )
        assert get_session_for_owner(sid, 2, db_path=db) is None

    def test_list_scopes_to_owner(self, db):
        create_session_for_owner(1, "Honda", "CBR", 2005, db_path=db)
        create_session_for_owner(2, "Yamaha", "R6", 2010, db_path=db)
        me = list_sessions_for_owner(1, db_path=db)
        assert len(me) == 1
        assert me[0]["vehicle_make"] == "Honda"

    def test_list_filters_by_status(self, db):
        a = create_session_for_owner(1, "X", "Y", 2000, db_path=db)
        b = create_session_for_owner(1, "X", "Y", 2001, db_path=db)
        close_session_for_owner(a, 1, db_path=db)
        open_ = list_sessions_for_owner(
            1, status="open", db_path=db,
        )
        closed = list_sessions_for_owner(
            1, status="closed", db_path=db,
        )
        assert len(open_) == 1 and open_[0]["id"] == b
        assert len(closed) == 1 and closed[0]["id"] == a

    def test_update_raises_on_cross_owner(self, db):
        sid = create_session_for_owner(
            1, "Honda", "CBR", 2005, db_path=db,
        )
        with pytest.raises(SessionOwnershipError):
            update_session_for_owner(
                sid, 2, {"diagnosis": "pwn"}, db_path=db,
            )

    def test_close_then_reopen(self, db):
        sid = create_session_for_owner(
            1, "Honda", "CBR", 2005, db_path=db,
        )
        assert close_session_for_owner(sid, 1, db_path=db)
        row = get_session_for_owner(sid, 1, db_path=db)
        assert row["status"] == "closed"
        assert reopen_session_for_owner(sid, 1, db_path=db)
        row = get_session_for_owner(sid, 1, db_path=db)
        assert row["status"] == "open"

    def test_add_symptom(self, db):
        sid = create_session_for_owner(
            1, "Honda", "CBR", 2005,
            symptoms=["stalling"], db_path=db,
        )
        assert add_symptom_for_owner(
            sid, 1, "rough idle", db_path=db,
        )
        row = get_session_for_owner(sid, 1, db_path=db)
        assert "rough idle" in row["symptoms"]

    def test_add_fault_code(self, db):
        sid = create_session_for_owner(
            1, "Honda", "CBR", 2005, db_path=db,
        )
        add_fault_code_for_owner(sid, 1, "P0171", db_path=db)
        row = get_session_for_owner(sid, 1, db_path=db)
        assert "P0171" in row["fault_codes"]

    def test_append_note(self, db):
        sid = create_session_for_owner(
            1, "Honda", "CBR", 2005, db_path=db,
        )
        append_note_for_owner(sid, 1, "first note", db_path=db)
        append_note_for_owner(sid, 1, "second note", db_path=db)
        row = get_session_for_owner(sid, 1, db_path=db)
        assert "first note" in (row.get("notes") or "")
        assert "second note" in (row.get("notes") or "")


# ===========================================================================
# 2. Monthly quota
# ===========================================================================


class TestQuota:

    def test_individual_limit_50(self, db):
        # Seed 50 sessions this month
        for _ in range(50):
            create_session_for_owner(
                1, "X", "Y", 2000, db_path=db,
            )
        assert count_sessions_this_month_for_owner(1, db_path=db) == 50
        with pytest.raises(SessionQuotaExceededError) as exc:
            check_session_quota(1, "individual", db_path=db)
        assert exc.value.limit == 50
        assert exc.value.tier == "individual"

    def test_shop_limit_500(self, db):
        # Seed 500
        for _ in range(500):
            create_session_for_owner(
                1, "X", "Y", 2000, db_path=db,
            )
        with pytest.raises(SessionQuotaExceededError):
            check_session_quota(1, "shop", db_path=db)

    def test_company_unlimited(self, db):
        for _ in range(60):
            create_session_for_owner(
                1, "X", "Y", 2000, db_path=db,
            )
        check_session_quota(1, "company", db_path=db)

    def test_none_tier_defaults_to_individual(self, db):
        for _ in range(50):
            create_session_for_owner(
                1, "X", "Y", 2000, db_path=db,
            )
        with pytest.raises(SessionQuotaExceededError) as exc:
            check_session_quota(1, None, db_path=db)
        assert exc.value.tier == "individual"

    def test_monthly_count_ignores_other_users(self, db):
        for _ in range(50):
            create_session_for_owner(1, "X", "Y", 2000, db_path=db)
        for _ in range(10):
            create_session_for_owner(2, "X", "Y", 2000, db_path=db)
        assert count_sessions_this_month_for_owner(1, db_path=db) == 50
        assert count_sessions_this_month_for_owner(2, db_path=db) == 10

    def test_monthly_count_ignores_prior_month(self, db):
        # Insert a session with a created_at last month
        import sqlite3
        with get_connection(db) as conn:
            conn.execute(
                """INSERT INTO diagnostic_sessions
                   (vehicle_make, vehicle_model, vehicle_year, status,
                    symptoms, fault_codes, created_at, user_id)
                   VALUES ('X', 'Y', 2000, 'open', '[]', '[]',
                           '2020-01-15T00:00:00', 1)""",
            )
        # Current month should still show 0
        assert count_sessions_this_month_for_owner(1, db_path=db) == 0


# ===========================================================================
# 3. HTTP happy paths
# ===========================================================================


class TestSessionEndpointsHappy:

    def test_unauthenticated_returns_401(self, api_db):
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/v1/sessions")
        assert r.status_code == 401

    def test_empty_list_response(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            "/v1/sessions", headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["items"] == []
        assert body["total_this_month"] == 0
        assert body["monthly_quota_limit"] == 50  # individual default

    def test_create_happy(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            "/v1/sessions",
            headers={"X-API-Key": plaintext},
            json={
                "vehicle_make": "Honda",
                "vehicle_model": "CBR600",
                "vehicle_year": 2005,
                "symptoms": ["stalling"],
                "fault_codes": ["P0171"],
            },
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["id"] > 0
        assert body["user_id"] == user_id
        assert body["status"] == "open"
        assert "stalling" in body["symptoms"]
        assert r.headers["Location"] == f"/v1/sessions/{body['id']}"

    def test_get_happy(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        sid = create_session_for_owner(
            user_id, "Honda", "CBR", 2005, db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/sessions/{sid}",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200
        assert r.json()["id"] == sid

    def test_patch_diagnosis(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        sid = create_session_for_owner(
            user_id, "Honda", "CBR", 2005, db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.patch(
            f"/v1/sessions/{sid}",
            headers={"X-API-Key": plaintext},
            json={"diagnosis": "fuel filter clogged",
                  "confidence": 0.85, "severity": "medium"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["diagnosis"] == "fuel filter clogged"
        assert body["confidence"] == 0.85

    def test_close_endpoint(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        sid = create_session_for_owner(
            user_id, "Honda", "CBR", 2005, db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            f"/v1/sessions/{sid}/close",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "closed"

    def test_reopen_endpoint(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        sid = create_session_for_owner(
            user_id, "Honda", "CBR", 2005, db_path=api_db,
        )
        close_session_for_owner(sid, user_id, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            f"/v1/sessions/{sid}/reopen",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "open"

    def test_add_symptom_endpoint(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        sid = create_session_for_owner(
            user_id, "Honda", "CBR", 2005, db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            f"/v1/sessions/{sid}/symptoms",
            headers={"X-API-Key": plaintext},
            json={"symptom": "rough idle at 1200rpm"},
        )
        assert r.status_code == 200, r.text
        assert "rough idle" in " ".join(r.json()["symptoms"])

    def test_add_fault_code_endpoint(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        sid = create_session_for_owner(
            user_id, "Honda", "CBR", 2005, db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            f"/v1/sessions/{sid}/fault-codes",
            headers={"X-API-Key": plaintext},
            json={"code": "P0171"},
        )
        assert r.status_code == 200
        assert "P0171" in r.json()["fault_codes"]

    def test_add_note_endpoint(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        sid = create_session_for_owner(
            user_id, "Honda", "CBR", 2005, db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            f"/v1/sessions/{sid}/notes",
            headers={"X-API-Key": plaintext},
            json={"note": "checked vacuum lines OK"},
        )
        assert r.status_code == 200
        assert "vacuum lines" in (r.json().get("notes") or "")


# ===========================================================================
# 4. Error paths
# ===========================================================================


class TestSessionEndpointsErrors:

    def test_get_cross_user_returns_404(self, api_db):
        me = _make_user(api_db, "me")
        other = _make_user(api_db, "other")
        _, plaintext = create_api_key(me, db_path=api_db)
        sid = create_session_for_owner(
            other, "Honda", "CBR", 2005, db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/sessions/{sid}",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 404
        assert r.json()["type"].endswith("session-not-found")

    def test_get_nonexistent(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            "/v1/sessions/99999",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 404

    def test_quota_exceeded_returns_402(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        # Seed 50 sessions already this month
        for _ in range(50):
            create_session_for_owner(
                user_id, "X", "Y", 2000, db_path=api_db,
            )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            "/v1/sessions",
            headers={"X-API-Key": plaintext},
            json={
                "vehicle_make": "Honda",
                "vehicle_model": "CBR",
                "vehicle_year": 2005,
            },
        )
        assert r.status_code == 402
        body = r.json()
        assert body["type"].endswith("session-quota-exceeded")
        assert "individual" in (body.get("detail") or "")

    def test_shop_tier_bigger_quota(self, api_db):
        user_id = _make_user(api_db)
        _make_sub(api_db, user_id, tier="shop")
        _, plaintext = create_api_key(user_id, db_path=api_db)
        for _ in range(60):
            create_session_for_owner(
                user_id, "X", "Y", 2000, db_path=api_db,
            )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            "/v1/sessions", headers={"X-API-Key": plaintext},
        )
        body = r.json()
        assert body["tier"] == "shop"
        assert body["monthly_quota_limit"] == 500
        assert body["monthly_quota_remaining"] == 440

    def test_company_unlimited_shown_null(self, api_db):
        user_id = _make_user(api_db)
        _make_sub(api_db, user_id, tier="company")
        _, plaintext = create_api_key(user_id, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            "/v1/sessions", headers={"X-API-Key": plaintext},
        )
        body = r.json()
        assert body["tier"] == "company"
        assert body["monthly_quota_limit"] is None
        assert body["monthly_quota_remaining"] is None

    def test_invalid_create_year(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            "/v1/sessions",
            headers={"X-API-Key": plaintext},
            json={
                "vehicle_make": "x", "vehicle_model": "y",
                "vehicle_year": 1800,
            },
        )
        assert r.status_code == 422

    def test_patch_cross_user_404(self, api_db):
        me = _make_user(api_db, "me")
        other = _make_user(api_db, "other")
        _, plaintext = create_api_key(me, db_path=api_db)
        sid = create_session_for_owner(
            other, "Honda", "CBR", 2005, db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.patch(
            f"/v1/sessions/{sid}",
            headers={"X-API-Key": plaintext},
            json={"diagnosis": "pwn"},
        )
        assert r.status_code == 404

    def test_close_cross_user_404(self, api_db):
        me = _make_user(api_db, "me")
        other = _make_user(api_db, "other")
        _, plaintext = create_api_key(me, db_path=api_db)
        sid = create_session_for_owner(
            other, "Honda", "CBR", 2005, db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            f"/v1/sessions/{sid}/close",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 404

    def test_since_filter_on_list(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        create_session_for_owner(
            user_id, "Honda", "CBR", 2005, db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            "/v1/sessions?since=1d",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200
        body = r.json()
        assert len(body["items"]) == 1
        # Very old since cutoff → still includes just-created session
        r2 = client.get(
            "/v1/sessions?since=30d",
            headers={"X-API-Key": plaintext},
        )
        assert len(r2.json()["items"]) == 1


# ===========================================================================
# 5. Constants sanity
# ===========================================================================


class TestConstants:

    def test_tier_limit_values(self):
        assert TIER_SESSION_MONTHLY_LIMITS["individual"] == 50
        assert TIER_SESSION_MONTHLY_LIMITS["shop"] == 500
        assert TIER_SESSION_MONTHLY_LIMITS["company"] == -1
