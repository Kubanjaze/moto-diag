"""Phase 404, Logic item 1 (F270) — the Shop plan has no bike limit.

A Shop account adds its 51st bike through ``POST /v1/vehicles``; an
Individual account's next bike past its limit is still 402 (the control);
Company is unchanged; and the CLI's plan table agrees with the server's
limits for every plan, bikes and diagnoses both. Fresh databases only.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.cli.subscription import TIER_LIMITS, SubscriptionTier
from motodiag.core.database import get_connection, init_db
from motodiag.core.session_repo import TIER_SESSION_MONTHLY_LIMITS
from motodiag.vehicles.registry import TIER_VEHICLE_LIMITS


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase404_bikes.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999")
    reset_settings()
    yield path
    reset_settings()


def _account(db_path: str, tier: str) -> str:
    with get_connection(db_path) as conn:
        uid = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) VALUES (?, ?, ?, 1)",
            (f"u_{tier}", f"{tier}@ex.com", tier),
        ).lastrowid
        conn.execute(
            "INSERT INTO subscriptions (user_id, tier, status, current_period_end) "
            "VALUES (?, ?, 'active', datetime('now', '+30 days'))",
            (uid, tier),
        )
    return create_api_key(uid, db_path=db_path)[1]


def _post(client: TestClient, key: str, i: int):
    return client.post("/v1/vehicles", headers={"X-API-Key": key},
                       json={"make": "Honda", "model": f"CB{i}", "year": 2005})


def _client(db_path: str) -> TestClient:
    return TestClient(create_app(db_path_override=db_path),
                      raise_server_exceptions=False)


def test_a_shop_account_adds_its_51st_bike(api_db):
    key = _account(api_db, "shop")
    client = _client(api_db)
    codes = [_post(client, key, i).status_code for i in range(51)]
    assert codes == [201] * 51
    body = client.get("/v1/vehicles", headers={"X-API-Key": key}).json()
    assert body["tier"] == "shop"
    assert body["total"] == 51
    assert body["quota_limit"] is None
    assert body["quota_remaining"] is None


def test_control_an_individual_account_is_refused_past_its_limit(api_db):
    key = _account(api_db, "individual")
    client = _client(api_db)
    allowed = TIER_VEHICLE_LIMITS["individual"]
    assert [_post(client, key, i).status_code for i in range(allowed)] == [201] * allowed
    r = _post(client, key, allowed)
    assert r.status_code == 402
    assert r.json()["type"].endswith("vehicle-quota-exceeded")


def test_a_company_account_is_unchanged(api_db):
    key = _account(api_db, "company")
    client = _client(api_db)
    assert [_post(client, key, i).status_code for i in range(51)] == [201] * 51
    body = client.get("/v1/vehicles", headers={"X-API-Key": key}).json()
    assert body["quota_limit"] is None and body["quota_remaining"] is None


@pytest.mark.parametrize("plan", list(SubscriptionTier))
def test_the_cli_table_and_the_servers_limits_agree(plan):
    features = TIER_LIMITS[plan]
    assert features.max_vehicles == TIER_VEHICLE_LIMITS[plan.value]
    assert features.max_sessions_per_month == TIER_SESSION_MONTHLY_LIMITS[plan.value]


def test_the_tables_name_the_same_plans():
    names = {p.value for p in SubscriptionTier}
    assert set(TIER_VEHICLE_LIMITS) == names
    assert set(TIER_SESSION_MONTHLY_LIMITS) == names
