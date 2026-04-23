"""Phase 180 — Shop management endpoints tests.

All endpoints require `require_tier("shop")` + shop-membership
check. Cross-shop attempts → 403 (not 404) because shops are
global-registry entities.
"""

from __future__ import annotations

import json as _json

import pytest
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import get_connection, init_db
from motodiag.shop import (
    add_shop_member, create_shop, create_work_order,
    open_work_order, start_work, complete_work_order,
    seed_first_owner,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase180_api.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()
    yield path
    reset_settings()


def _make_user(db_path, username, tier_col="shop"):
    """Create a user row; `tier_col` is the Phase 112 users.tier value
    (not subscription tier)."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES (?, ?, 'individual', 1)",
            (username, f"{username}@ex.com"),
        )
        return cursor.lastrowid


def _make_sub(db_path, user_id, tier="shop"):
    """Make the user's subscription tier, enabling `require_tier(shop)`."""
    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT INTO subscriptions
               (user_id, tier, status, current_period_end)
               VALUES (?, ?, 'active', datetime('now', '+30 days'))""",
            (user_id, tier),
        )


def _authed_owner(api_db):
    """Create a shop-tier user with a fresh shop + owner membership.
    Returns (user_id, api_key_plaintext, shop_id)."""
    user_id = _make_user(api_db, "owner")
    _make_sub(api_db, user_id, tier="shop")
    _, plaintext = create_api_key(user_id, db_path=api_db)
    shop_id = create_shop("TestShop", db_path=api_db)
    seed_first_owner(shop_id, user_id, db_path=api_db)
    return user_id, plaintext, shop_id


# ===========================================================================
# Auth + tier gating
# ===========================================================================


class TestAuthBoundary:

    def test_unauth_returns_401(self, api_db):
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/v1/shop/profile/list")
        assert r.status_code == 401

    def test_individual_tier_gets_402(self, api_db):
        user_id = _make_user(api_db, "basic")
        _make_sub(api_db, user_id, tier="individual")
        _, plaintext = create_api_key(user_id, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            "/v1/shop/profile/list",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 402

    def test_non_member_gets_403(self, api_db):
        _, plaintext, shop_id = _authed_owner(api_db)
        # Create a different shop-tier user who isn't a member
        outsider = _make_user(api_db, "outsider")
        _make_sub(api_db, outsider, tier="shop")
        _, outsider_token = create_api_key(outsider, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/shop/profile/{shop_id}",
            headers={"X-API-Key": outsider_token},
        )
        assert r.status_code == 403


# ===========================================================================
# Profile
# ===========================================================================


class TestProfile:

    def test_list_own_shops(self, api_db):
        _, plaintext, shop_id = _authed_owner(api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            "/v1/shop/profile/list",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["items"][0]["id"] == shop_id
        assert body["items"][0]["my_role"] == "owner"

    def test_create_shop_stamps_owner(self, api_db):
        user_id = _make_user(api_db, "newowner")
        _make_sub(api_db, user_id, tier="shop")
        _, plaintext = create_api_key(user_id, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            "/v1/shop/profile",
            headers={"X-API-Key": plaintext},
            json={"name": "MyMotoShop", "state": "CA"},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        shop_id = body["id"]
        # Caller should now be an owner
        from motodiag.shop import has_shop_permission
        assert has_shop_permission(
            shop_id, user_id, "manage_shop", db_path=api_db,
        )

    def test_get_shop_profile(self, api_db):
        _, plaintext, shop_id = _authed_owner(api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/shop/profile/{shop_id}",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200
        assert r.json()["id"] == shop_id

    def test_patch_shop_profile(self, api_db):
        _, plaintext, shop_id = _authed_owner(api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.patch(
            f"/v1/shop/profile/{shop_id}",
            headers={"X-API-Key": plaintext},
            json={"phone": "555-1234"},
        )
        assert r.status_code == 200
        assert r.json()["phone"] == "555-1234"


# ===========================================================================
# Members
# ===========================================================================


class TestMembers:

    def test_list_members(self, api_db):
        _, plaintext, shop_id = _authed_owner(api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/shop/{shop_id}/members",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200
        assert r.json()["total"] == 1  # owner only

    def test_add_member(self, api_db):
        _, plaintext, shop_id = _authed_owner(api_db)
        new_user = _make_user(api_db, "tech1")
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            f"/v1/shop/{shop_id}/members",
            headers={"X-API-Key": plaintext},
            json={"user_id": new_user, "role": "tech"},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["user_id"] == new_user

    def test_delete_member(self, api_db):
        _, plaintext, shop_id = _authed_owner(api_db)
        new_user = _make_user(api_db, "tech2")
        add_shop_member(shop_id, new_user, "tech", db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.delete(
            f"/v1/shop/{shop_id}/members/{new_user}",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 204


# ===========================================================================
# Customers
# ===========================================================================


class TestCustomers:

    def test_create_customer(self, api_db):
        _, plaintext, shop_id = _authed_owner(api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            f"/v1/shop/{shop_id}/customers",
            headers={"X-API-Key": plaintext},
            json={"name": "Jane Doe", "email": "jane@ex.com"},
        )
        assert r.status_code == 201, r.text
        assert r.json()["name"] == "Jane Doe"

    def test_list_customers(self, api_db):
        _, plaintext, shop_id = _authed_owner(api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        client.post(
            f"/v1/shop/{shop_id}/customers",
            headers={"X-API-Key": plaintext},
            json={"name": "A"},
        )
        r = client.get(
            f"/v1/shop/{shop_id}/customers",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_get_customer_404(self, api_db):
        _, plaintext, shop_id = _authed_owner(api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/shop/{shop_id}/customers/9999",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 404


# ===========================================================================
# Work orders
# ===========================================================================


class TestWorkOrders:

    def _fixture_wo(self, api_db, plaintext, shop_id):
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        # Create a customer + vehicle first
        cust = client.post(
            f"/v1/shop/{shop_id}/customers",
            headers={"X-API-Key": plaintext},
            json={"name": "Alice"},
        ).json()
        with get_connection(api_db) as conn:
            c = conn.execute(
                "INSERT INTO vehicles (make, model, year, protocol) "
                "VALUES ('Honda', 'CBR', 2005, 'none')"
            )
            vid = c.lastrowid
        return client, cust["id"], vid

    def test_create_work_order(self, api_db):
        _, plaintext, shop_id = _authed_owner(api_db)
        client, cust_id, vid = self._fixture_wo(
            api_db, plaintext, shop_id,
        )
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders",
            headers={"X-API-Key": plaintext},
            json={
                "vehicle_id": vid, "customer_id": cust_id,
                "title": "brake service", "estimated_hours": 1.0,
            },
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["title"] == "brake service"
        assert body["status"] == "draft"

    def test_transition_work_order(self, api_db):
        _, plaintext, shop_id = _authed_owner(api_db)
        client, cust_id, vid = self._fixture_wo(
            api_db, plaintext, shop_id,
        )
        wo = client.post(
            f"/v1/shop/{shop_id}/work-orders",
            headers={"X-API-Key": plaintext},
            json={
                "vehicle_id": vid, "customer_id": cust_id,
                "title": "x", "estimated_hours": 1.0,
            },
        ).json()
        wo_id = wo["id"]
        # open
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/transition",
            headers={"X-API-Key": plaintext},
            json={"action": "open"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "open"
        # start
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/transition",
            headers={"X-API-Key": plaintext},
            json={"action": "start"},
        )
        assert r.json()["status"] == "in_progress"
        # complete
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/transition",
            headers={"X-API-Key": plaintext},
            json={"action": "complete", "actual_hours": 1.5},
        )
        assert r.json()["status"] == "completed"

    def test_list_work_orders(self, api_db):
        _, plaintext, shop_id = _authed_owner(api_db)
        client, cust_id, vid = self._fixture_wo(
            api_db, plaintext, shop_id,
        )
        client.post(
            f"/v1/shop/{shop_id}/work-orders",
            headers={"X-API-Key": plaintext},
            json={
                "vehicle_id": vid, "customer_id": cust_id,
                "title": "x", "estimated_hours": 1.0,
            },
        )
        r = client.get(
            f"/v1/shop/{shop_id}/work-orders",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_transition_bogus_action_422(self, api_db):
        _, plaintext, shop_id = _authed_owner(api_db)
        client, cust_id, vid = self._fixture_wo(
            api_db, plaintext, shop_id,
        )
        wo = client.post(
            f"/v1/shop/{shop_id}/work-orders",
            headers={"X-API-Key": plaintext},
            json={
                "vehicle_id": vid, "customer_id": cust_id,
                "title": "x", "estimated_hours": 1.0,
            },
        ).json()
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo['id']}/transition",
            headers={"X-API-Key": plaintext},
            json={"action": "teleport"},
        )
        assert r.status_code == 422


# ===========================================================================
# Invoices
# ===========================================================================


class TestInvoices:

    def test_generate_invoice_flow(self, api_db):
        _, plaintext, shop_id = _authed_owner(api_db)
        # Seed customer + vehicle + completed WO
        from motodiag.crm.models import Customer
        from motodiag.crm import customer_repo
        cust_id = customer_repo.create_customer(
            Customer(name="Alice", phone="555", email="a@ex.com"),
            db_path=api_db,
        )
        with get_connection(api_db) as conn:
            c = conn.execute(
                "INSERT INTO vehicles (make, model, year, protocol) "
                "VALUES ('Honda', 'CBR', 2005, 'none')"
            )
            vid = c.lastrowid
        wo_id = create_work_order(
            shop_id=shop_id, vehicle_id=vid, customer_id=cust_id,
            title="test", estimated_hours=2.0, db_path=api_db,
        )
        open_work_order(wo_id, db_path=api_db)
        start_work(wo_id, db_path=api_db)
        complete_work_order(wo_id, actual_hours=2.0, db_path=api_db)

        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            f"/v1/shop/{shop_id}/invoices/generate",
            headers={"X-API-Key": plaintext},
            json={
                "work_order_id": wo_id,
                "labor_hourly_rate_cents": 10000,
            },
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["subtotal_cents"] == 20000

    def test_invoice_for_other_shops_wo_404(self, api_db):
        _, plaintext, shop_id = _authed_owner(api_db)
        # Create a separate shop + WO owned by another owner
        other_shop = create_shop("OtherShop", db_path=api_db)
        from motodiag.crm.models import Customer
        from motodiag.crm import customer_repo
        cust_id = customer_repo.create_customer(
            Customer(name="Bob", phone="555", email="b@ex.com"),
            db_path=api_db,
        )
        with get_connection(api_db) as conn:
            c = conn.execute(
                "INSERT INTO vehicles (make, model, year, protocol) "
                "VALUES ('X', 'Y', 2000, 'none')"
            )
            vid = c.lastrowid
        wo_id = create_work_order(
            shop_id=other_shop, vehicle_id=vid, customer_id=cust_id,
            title="x", estimated_hours=1.0, db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            f"/v1/shop/{shop_id}/invoices/generate",
            headers={"X-API-Key": plaintext},
            json={"work_order_id": wo_id,
                  "labor_hourly_rate_cents": 10000},
        )
        assert r.status_code == 404


# ===========================================================================
# Analytics
# ===========================================================================


class TestAnalytics:

    def test_snapshot_endpoint(self, api_db):
        _, plaintext, shop_id = _authed_owner(api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/shop/{shop_id}/analytics/snapshot?since=7d",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "throughput" in body
        assert "revenue" in body
        assert "customer_repeat" in body

    def test_revenue_endpoint(self, api_db):
        _, plaintext, shop_id = _authed_owner(api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/shop/{shop_id}/analytics/revenue",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200
        body = r.json()
        assert "total_invoiced_cents" in body

    def test_top_issues_endpoint(self, api_db):
        _, plaintext, shop_id = _authed_owner(api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/shop/{shop_id}/analytics/top-issues?since=30d",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200
        assert "items" in r.json()
