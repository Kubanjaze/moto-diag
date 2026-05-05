"""Phase 177 — Vehicle endpoints (HTTP CRUD + tier quota) tests.

Six test classes across ~30 tests. Zero AI, zero Stripe network.
"""

from __future__ import annotations

import json as _json

import pytest
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import (
    SCHEMA_VERSION, get_connection, init_db, table_exists,
)
from motodiag.core.models import (
    PowertrainType, ProtocolType, VehicleBase,
)
from motodiag.core.migrations import rollback_to_version
from motodiag.vehicles.registry import (
    TIER_VEHICLE_LIMITS,
    VehicleOwnershipError,
    VehicleQuotaExceededError,
    add_vehicle_for_owner,
    check_vehicle_quota,
    count_vehicles_for_owner,
    delete_vehicle_for_owner,
    get_vehicle_for_owner,
    list_vehicles_for_owner,
    update_vehicle_for_owner,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase177.db")
    init_db(path)
    return path


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase177_api.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    # Loosen rate limits so tests don't trip 429s
    monkeypatch.setenv("MOTODIAG_RATE_LIMIT_ANONYMOUS_PER_MINUTE", "9999")
    monkeypatch.setenv("MOTODIAG_RATE_LIMIT_INDIVIDUAL_PER_MINUTE", "9999")
    monkeypatch.setenv("MOTODIAG_RATE_LIMIT_SHOP_PER_MINUTE", "9999")
    monkeypatch.setenv("MOTODIAG_RATE_LIMIT_COMPANY_PER_MINUTE", "9999")
    reset_settings()
    yield path
    reset_settings()


def _make_user(db_path, username="bob", email="b@ex.com"):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES (?, ?, 'individual', 1)",
            (username, email),
        )
        return cursor.lastrowid


def _make_sub(db_path, user_id, tier="individual", status="active"):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO subscriptions
               (user_id, tier, status, current_period_end)
               VALUES (?, ?, ?, datetime('now', '+30 days'))""",
            (user_id, tier, status),
        )
        return cursor.lastrowid


def _vehicle(make="Honda", model="CBR600", year=2005):
    return VehicleBase(
        make=make, model=model, year=year,
        protocol=ProtocolType.NONE,
    )


# ===========================================================================
# 1. Migration 038
# ===========================================================================


class TestMigration038:

    def test_schema_version_bumped(self, db):
        assert SCHEMA_VERSION >= 38

    def test_owner_column_exists(self, db):
        with get_connection(db) as conn:
            cols = {
                r[1] for r in conn.execute(
                    "PRAGMA table_info(vehicles)"
                ).fetchall()
            }
        assert "owner_user_id" in cols

    def test_owner_index_present(self, db):
        with get_connection(db) as conn:
            names = {
                r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                ).fetchall()
            }
        assert "idx_vehicles_owner" in names

    def test_rollback_drops_column(self, tmp_path):
        path = str(tmp_path / "rollback.db")
        init_db(path)
        # Confirm column exists at 38
        with get_connection(path) as conn:
            cols = {
                r[1] for r in conn.execute(
                    "PRAGMA table_info(vehicles)"
                ).fetchall()
            }
        assert "owner_user_id" in cols
        rollback_to_version(37, path)
        with get_connection(path) as conn:
            cols = {
                r[1] for r in conn.execute(
                    "PRAGMA table_info(vehicles)"
                ).fetchall()
            }
        assert "owner_user_id" not in cols


# ===========================================================================
# 2. Repo-layer helpers
# ===========================================================================


class TestOwnerScopedRepo:

    def test_add_stamps_owner(self, db):
        vid = add_vehicle_for_owner(_vehicle(), 42, db_path=db)
        row = get_vehicle_for_owner(vid, 42, db_path=db)
        assert row is not None
        assert row["owner_user_id"] == 42

    def test_get_returns_none_for_cross_owner(self, db):
        vid = add_vehicle_for_owner(_vehicle(), 1, db_path=db)
        assert get_vehicle_for_owner(vid, 2, db_path=db) is None

    def test_list_scopes_to_owner(self, db):
        add_vehicle_for_owner(_vehicle("Honda"), 1, db_path=db)
        add_vehicle_for_owner(_vehicle("Yamaha"), 2, db_path=db)
        one = list_vehicles_for_owner(1, db_path=db)
        assert len(one) == 1
        assert one[0]["make"] == "Honda"
        two = list_vehicles_for_owner(2, db_path=db)
        assert len(two) == 1
        assert two[0]["make"] == "Yamaha"

    def test_count_scopes_to_owner(self, db):
        for _ in range(3):
            add_vehicle_for_owner(_vehicle(), 7, db_path=db)
        add_vehicle_for_owner(_vehicle(), 9, db_path=db)
        assert count_vehicles_for_owner(7, db_path=db) == 3
        assert count_vehicles_for_owner(9, db_path=db) == 1

    def test_update_raises_on_cross_owner(self, db):
        vid = add_vehicle_for_owner(_vehicle(), 1, db_path=db)
        with pytest.raises(VehicleOwnershipError):
            update_vehicle_for_owner(
                vid, owner_user_id=2,
                updates={"notes": "pwned"}, db_path=db,
            )

    def test_update_returns_false_for_missing(self, db):
        assert update_vehicle_for_owner(
            vehicle_id=9999, owner_user_id=1,
            updates={"notes": "x"}, db_path=db,
        ) is False

    def test_delete_raises_on_cross_owner(self, db):
        vid = add_vehicle_for_owner(_vehicle(), 1, db_path=db)
        with pytest.raises(VehicleOwnershipError):
            delete_vehicle_for_owner(vid, 2, db_path=db)

    def test_delete_happy(self, db):
        vid = add_vehicle_for_owner(_vehicle(), 1, db_path=db)
        assert delete_vehicle_for_owner(vid, 1, db_path=db) is True
        assert get_vehicle_for_owner(vid, 1, db_path=db) is None


# ===========================================================================
# 3. Tier quota
# ===========================================================================


class TestQuota:

    def test_individual_limit_5(self, db):
        for _ in range(5):
            check_vehicle_quota(1, "individual", db_path=db)
            add_vehicle_for_owner(_vehicle(), 1, db_path=db)
        with pytest.raises(VehicleQuotaExceededError) as exc:
            check_vehicle_quota(1, "individual", db_path=db)
        assert exc.value.limit == 5
        assert exc.value.tier == "individual"

    def test_shop_limit_50(self, db):
        # Populate 49, expect still-allowed; then add 50th, expect blocked on 51st.
        for _ in range(50):
            add_vehicle_for_owner(_vehicle(), 1, db_path=db)
        with pytest.raises(VehicleQuotaExceededError):
            check_vehicle_quota(1, "shop", db_path=db)

    def test_company_unlimited(self, db):
        for _ in range(60):
            add_vehicle_for_owner(_vehicle(), 1, db_path=db)
        # Should not raise
        check_vehicle_quota(1, "company", db_path=db)

    def test_unknown_tier_defaults_to_individual(self, db):
        for _ in range(5):
            add_vehicle_for_owner(_vehicle(), 1, db_path=db)
        with pytest.raises(VehicleQuotaExceededError) as exc:
            check_vehicle_quota(1, None, db_path=db)
        # Unknown tier → effective tier = individual (limit 5)
        assert exc.value.tier == "individual"

    def test_tier_limits_map(self):
        assert TIER_VEHICLE_LIMITS["individual"] == 5  # f9-noqa: ssot-pin contract-pin: individual tier vehicle cap is the entry-tier conversion lever; bumping it changes the effective free-tier value and triggers a Stripe price-tier review per Phase 176 billing wire-up.
        assert TIER_VEHICLE_LIMITS["shop"] == 50  # f9-noqa: ssot-pin contract-pin: shop-tier vehicle cap is sized for a 2-3 mechanic small shop's working garage; bumping requires re-validating quota gate behavior in test_phase177 + reconciling with shop-tier billing collateral that quotes "up to 50 bikes."
        assert TIER_VEHICLE_LIMITS["company"] == -1  # f9-noqa: ssot-pin contract-pin: -1 is the unlimited-tier sentinel; changing it (e.g., to None or to a hard cap) breaks the check_vehicle_quota dispatch in src/motodiag/vehicles/registry.py and the company-tier UI badge that renders "Unlimited" when seeing -1.


# ===========================================================================
# 4. HTTP endpoints — happy paths
# ===========================================================================


class TestVehicleEndpointsHappy:

    def test_unauthenticated_returns_401(self, api_db):
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/v1/vehicles")
        assert r.status_code == 401

    def test_empty_garage(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            "/v1/vehicles", headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 0
        assert body["items"] == []
        # User has no sub → defaults to individual tier quota
        assert body["quota_limit"] == 5

    def test_create_happy(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            "/v1/vehicles",
            headers={"X-API-Key": plaintext},
            json={
                "make": "Honda", "model": "CBR600", "year": 2005,
            },
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["id"] > 0
        assert body["make"] == "Honda"
        assert body["owner_user_id"] == user_id
        assert r.headers["Location"] == f"/v1/vehicles/{body['id']}"

    def test_get_by_id_happy(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        vid = add_vehicle_for_owner(_vehicle(), user_id, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/vehicles/{vid}",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200
        assert r.json()["id"] == vid

    def test_patch_partial_update(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        vid = add_vehicle_for_owner(_vehicle(), user_id, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.patch(
            f"/v1/vehicles/{vid}",
            headers={"X-API-Key": plaintext},
            json={"notes": "updated"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["notes"] == "updated"

    def test_delete_204(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        vid = add_vehicle_for_owner(_vehicle(), user_id, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.delete(
            f"/v1/vehicles/{vid}",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 204

    def test_list_only_my_vehicles(self, api_db):
        me = _make_user(api_db, "me", "me@ex.com")
        other = _make_user(api_db, "other", "other@ex.com")
        _, plaintext = create_api_key(me, db_path=api_db)
        add_vehicle_for_owner(_vehicle("Honda"), me, db_path=api_db)
        add_vehicle_for_owner(_vehicle("Yamaha"), other, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            "/v1/vehicles", headers={"X-API-Key": plaintext},
        )
        body = r.json()
        assert body["total"] == 1
        assert body["items"][0]["make"] == "Honda"

    def test_sessions_endpoint(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        vid = add_vehicle_for_owner(
            _vehicle(), user_id, db_path=api_db,
        )
        # Insert a diagnostic session directly
        with get_connection(api_db) as conn:
            conn.execute(
                """INSERT INTO diagnostic_sessions
                   (vehicle_id, vehicle_make, vehicle_model,
                    vehicle_year, status)
                   VALUES (?, 'Honda', 'CBR600', 2005, 'open')""",
                (vid,),
            )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/vehicles/{vid}/sessions",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["vehicle_id"] == vid


# ===========================================================================
# 5. Error paths
# ===========================================================================


class TestVehicleEndpointsErrors:

    def test_get_cross_user_returns_404(self, api_db):
        me = _make_user(api_db, "me")
        other = _make_user(api_db, "other", "other@ex.com")
        _, plaintext = create_api_key(me, db_path=api_db)
        vid = add_vehicle_for_owner(
            _vehicle(), other, db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/vehicles/{vid}",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 404
        body = r.json()
        assert body["type"].endswith("vehicle-not-found")

    def test_get_nonexistent_returns_404(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            "/v1/vehicles/99999",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 404

    def test_patch_cross_user_returns_404(self, api_db):
        me = _make_user(api_db, "me")
        other = _make_user(api_db, "other", "other@ex.com")
        _, plaintext = create_api_key(me, db_path=api_db)
        vid = add_vehicle_for_owner(
            _vehicle(), other, db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.patch(
            f"/v1/vehicles/{vid}",
            headers={"X-API-Key": plaintext},
            json={"notes": "pwn"},
        )
        assert r.status_code == 404

    def test_quota_exceeded_returns_402(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        # Pre-populate 5 (individual limit)
        for i in range(5):
            add_vehicle_for_owner(
                _vehicle(year=2000 + i),
                user_id, db_path=api_db,
            )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            "/v1/vehicles",
            headers={"X-API-Key": plaintext},
            json={"make": "Suzuki", "model": "GSX", "year": 2010},
        )
        assert r.status_code == 402
        body = r.json()
        assert body["type"].endswith("vehicle-quota-exceeded")
        assert "individual" in (body.get("detail") or "")

    def test_shop_tier_gets_bigger_quota(self, api_db):
        user_id = _make_user(api_db)
        _make_sub(api_db, user_id, tier="shop")
        _, plaintext = create_api_key(user_id, db_path=api_db)
        # Add 5 — still fine at shop tier (limit 50)
        for i in range(6):
            add_vehicle_for_owner(
                _vehicle(year=2000 + i),
                user_id, db_path=api_db,
            )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            "/v1/vehicles", headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["tier"] == "shop"
        assert body["quota_limit"] == 50
        assert body["quota_remaining"] == 44

    def test_company_tier_shows_unlimited(self, api_db):
        user_id = _make_user(api_db)
        _make_sub(api_db, user_id, tier="company")
        _, plaintext = create_api_key(user_id, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            "/v1/vehicles", headers={"X-API-Key": plaintext},
        )
        body = r.json()
        assert body["tier"] == "company"
        assert body["quota_limit"] is None
        assert body["quota_remaining"] is None

    def test_invalid_create_body_returns_422(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        # Missing make
        r = client.post(
            "/v1/vehicles",
            headers={"X-API-Key": plaintext},
            json={"model": "x", "year": 2005},
        )
        assert r.status_code == 422

    def test_invalid_year_range(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            "/v1/vehicles",
            headers={"X-API-Key": plaintext},
            json={"make": "x", "model": "x", "year": 1800},
        )
        assert r.status_code == 422
