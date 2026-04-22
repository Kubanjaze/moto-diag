"""Phase 179 — KB endpoints tests. Read-only, zero AI."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import get_connection, init_db


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase179_api.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()
    # Seed basic KB data
    with get_connection(path) as conn:
        conn.execute(
            """INSERT INTO dtc_codes (code, description, category,
                severity, make, common_causes, fix_summary)
               VALUES ('P0171', 'System too lean (Bank 1)',
                       'fuel_system', 'medium', NULL,
                       '["dirty MAF","vacuum leak"]',
                       'Inspect MAF + vacuum lines')""",
        )
        conn.execute(
            """INSERT INTO dtc_codes (code, description, category,
                severity, make)
               VALUES ('B1001', 'Harley-specific fault',
                       'body', 'low', 'harley-davidson')""",
        )
        conn.execute(
            """INSERT INTO symptoms
                (name, description, category, related_systems)
               VALUES ('stalling at idle',
                       'Engine dies when warm at idle',
                       'engine',
                       '["fuel","ignition"]')""",
        )
        conn.execute(
            """INSERT INTO known_issues
                (title, description, make, model, year_start,
                 year_end, severity, symptoms, dtc_codes, causes,
                 fix_procedure, parts_needed, estimated_hours)
               VALUES ('Sportster stalling at idle',
                       'Common fuel-pump issue on 2004-2010',
                       'harley-davidson', 'Sportster', 2004, 2010,
                       'medium', '["stalling"]', '["P0171"]',
                       '["fuel pump failure"]',
                       'Replace fuel pump assembly',
                       '["fuel pump"]', 2.5)""",
        )
    reset_settings()
    yield path
    reset_settings()


def _authed_client(api_db):
    user_id = _make_user(api_db)
    _, plaintext = create_api_key(user_id, db_path=api_db)
    app = create_app(db_path_override=api_db)
    client = TestClient(app, raise_server_exceptions=False)
    return client, plaintext


def _make_user(db_path, username="kb_user"):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES (?, 'k@ex.com', 'individual', 1)",
            (username,),
        )
        return cursor.lastrowid


# ===========================================================================
# Auth boundary
# ===========================================================================


class TestAuth:

    def test_unauth_dtc_list_401(self, api_db):
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/v1/kb/dtc")
        assert r.status_code == 401

    def test_unauth_search_401(self, api_db):
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/v1/kb/search?q=stall")
        assert r.status_code == 401


# ===========================================================================
# DTC endpoints
# ===========================================================================


class TestDTCEndpoints:

    def test_get_dtc_by_code(self, api_db):
        client, token = _authed_client(api_db)
        r = client.get(
            "/v1/kb/dtc/P0171", headers={"X-API-Key": token},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["code"] == "P0171"
        assert "lean" in body["description"].lower()
        assert body["common_causes"] == ["dirty MAF", "vacuum leak"]

    def test_get_dtc_not_found(self, api_db):
        client, token = _authed_client(api_db)
        r = client.get(
            "/v1/kb/dtc/P9999", headers={"X-API-Key": token},
        )
        assert r.status_code == 404

    def test_search_dtcs_all(self, api_db):
        client, token = _authed_client(api_db)
        r = client.get(
            "/v1/kb/dtc", headers={"X-API-Key": token},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 2

    def test_search_dtcs_by_query(self, api_db):
        client, token = _authed_client(api_db)
        r = client.get(
            "/v1/kb/dtc?q=lean", headers={"X-API-Key": token},
        )
        body = r.json()
        assert body["total"] >= 1
        assert any(
            "lean" in item["description"].lower()
            for item in body["items"]
        )

    def test_search_dtcs_by_make(self, api_db):
        client, token = _authed_client(api_db)
        r = client.get(
            "/v1/kb/dtc?make=harley-davidson",
            headers={"X-API-Key": token},
        )
        body = r.json()
        codes = {it["code"] for it in body["items"]}
        assert "B1001" in codes

    def test_limit_honored(self, api_db):
        client, token = _authed_client(api_db)
        r = client.get(
            "/v1/kb/dtc?limit=1", headers={"X-API-Key": token},
        )
        body = r.json()
        assert len(body["items"]) == 1


# ===========================================================================
# Symptom endpoints
# ===========================================================================


class TestSymptomEndpoints:

    def test_search_symptoms(self, api_db):
        client, token = _authed_client(api_db)
        r = client.get(
            "/v1/kb/symptoms?q=stalling",
            headers={"X-API-Key": token},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 1
        assert "stalling" in body["items"][0]["name"].lower()

    def test_symptoms_empty_query_returns_all(self, api_db):
        client, token = _authed_client(api_db)
        r = client.get(
            "/v1/kb/symptoms", headers={"X-API-Key": token},
        )
        assert r.status_code == 200
        assert r.json()["total"] >= 1


# ===========================================================================
# Known-issue endpoints
# ===========================================================================


class TestKnownIssueEndpoints:

    def test_search_issues_by_text(self, api_db):
        client, token = _authed_client(api_db)
        r = client.get(
            "/v1/kb/issues?q=stalling",
            headers={"X-API-Key": token},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 1

    def test_search_issues_by_make(self, api_db):
        client, token = _authed_client(api_db)
        r = client.get(
            "/v1/kb/issues?make=harley-davidson",
            headers={"X-API-Key": token},
        )
        body = r.json()
        assert body["total"] >= 1
        assert body["items"][0]["make"] == "harley-davidson"

    def test_get_issue_by_id(self, api_db):
        client, token = _authed_client(api_db)
        # Find the seeded issue
        list_r = client.get(
            "/v1/kb/issues?q=stalling",
            headers={"X-API-Key": token},
        )
        issue_id = list_r.json()["items"][0]["id"]
        r = client.get(
            f"/v1/kb/issues/{issue_id}",
            headers={"X-API-Key": token},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == issue_id
        assert body["estimated_hours"] == 2.5
        assert "fuel pump" in body["parts_needed"]

    def test_get_issue_not_found(self, api_db):
        client, token = _authed_client(api_db)
        r = client.get(
            "/v1/kb/issues/99999",
            headers={"X-API-Key": token},
        )
        assert r.status_code == 404


# ===========================================================================
# Unified search
# ===========================================================================


class TestUnifiedSearch:

    def test_search_returns_mixed_results(self, api_db):
        client, token = _authed_client(api_db)
        r = client.get(
            "/v1/kb/search?q=stalling",
            headers={"X-API-Key": token},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["query"] == "stalling"
        # Symptoms OR known_issues should hit
        assert (len(body["symptoms"]) + len(body["known_issues"])) >= 1

    def test_search_requires_query(self, api_db):
        client, token = _authed_client(api_db)
        r = client.get(
            "/v1/kb/search",
            headers={"X-API-Key": token},
        )
        # FastAPI coerces missing required query param to 422
        assert r.status_code == 422


# ===========================================================================
# DTC categories
# ===========================================================================


class TestCategories:

    def test_list_categories(self, api_db):
        client, token = _authed_client(api_db)
        r = client.get(
            "/v1/kb/dtc/categories",
            headers={"X-API-Key": token},
        )
        assert r.status_code == 200
        assert isinstance(r.json(), list)
