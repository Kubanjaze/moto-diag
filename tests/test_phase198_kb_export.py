"""Phase 198 — KB export endpoint tests (offline-cache snapshot).

Mirrors the Phase 179 KB-API test idiom: tmp DB seeded with KB rows,
authed TestClient. Pins the export contract the mobile offline cache
builds on: full snapshot, content-hash version stamp (stable across
calls, changes when content changes), auth boundary.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import get_connection, init_db


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase198_api.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()
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
    reset_settings()
    yield path
    reset_settings()


def _make_user(db_path, username="kb_export_user"):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES (?, 'ke@ex.com', 'individual', 1)",
            (username,),
        )
        return cursor.lastrowid


def _authed_client(api_db):
    user_id = _make_user(api_db)
    _, plaintext = create_api_key(user_id, db_path=api_db)
    app = create_app(db_path_override=api_db)
    client = TestClient(app, raise_server_exceptions=False)
    return client, plaintext


class TestAuth:

    def test_unauth_export_401(self, api_db):
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/v1/kb/export")
        assert r.status_code == 401


class TestExport:

    def test_export_returns_full_snapshot(self, api_db):
        client, key = _authed_client(api_db)
        r = client.get("/v1/kb/export", headers={"X-API-Key": key})
        assert r.status_code == 200
        body = r.json()
        assert set(body.keys()) >= {"kb_version", "dtcs", "categories"}
        codes = [d["code"] for d in body["dtcs"]]
        assert codes == sorted(codes)  # code-ordered
        assert "P0171" in codes and "B1001" in codes
        p0171 = next(d for d in body["dtcs"] if d["code"] == "P0171")
        assert p0171["common_causes"] == ["dirty MAF", "vacuum leak"]
        assert p0171["fix_summary"] == "Inspect MAF + vacuum lines"
        # Category meta rows come from init_db's migration seed.
        assert isinstance(body["categories"], list)

    def test_version_stamp_stable_across_calls(self, api_db):
        client, key = _authed_client(api_db)
        r1 = client.get("/v1/kb/export", headers={"X-API-Key": key})
        r2 = client.get("/v1/kb/export", headers={"X-API-Key": key})
        assert r1.json()["kb_version"] == r2.json()["kb_version"]
        assert len(r1.json()["kb_version"]) == 64  # sha256 hex

    def test_version_stamp_changes_when_content_changes(self, api_db):
        client, key = _authed_client(api_db)
        before = client.get(
            "/v1/kb/export", headers={"X-API-Key": key},
        ).json()["kb_version"]
        with get_connection(api_db) as conn:
            conn.execute(
                """INSERT INTO dtc_codes (code, description, category,
                    severity) VALUES ('P0300', 'Random misfire',
                    'ignition', 'high')""",
            )
        after = client.get(
            "/v1/kb/export", headers={"X-API-Key": key},
        ).json()["kb_version"]
        assert before != after
