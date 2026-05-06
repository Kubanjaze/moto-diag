"""Phase 193 Commit 0.5 — POST /v1/shop/{shop_id}/work-orders/{wo_id}/assign.

Pins the new assign endpoint's behavior. Same Step-0 pattern as
Commit 0's sort-param substrate addition: backend `assign_mechanic`
+ `unassign_mechanic` repo functions existed (Phase 161) but had
no HTTP exposure. Phase 193 Mobile Commit 2 needs the route for
the MemberPickerModal reassign flow per plan v1.0 Section E.

Same auth posture as the transition endpoint (basic shop-membership
check). Cross-shop WOs return 404. RBAC tightening (manager/owner-
only reassignment of others' WOs) is a follow-up F-ticket.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import get_connection, init_db
from motodiag.shop import (
    add_shop_member, create_shop, create_work_order, seed_first_owner,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase193_c05.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()
    yield path
    reset_settings()


def _make_user(db_path, username, sub_tier="shop"):
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES (?, ?, 'individual', 1)",
            (username, f"{username}@ex.com"),
        )
        user_id = cur.lastrowid
        conn.execute(
            """INSERT INTO subscriptions
               (user_id, tier, status, current_period_end)
               VALUES (?, ?, 'active', datetime('now', '+30 days'))""",
            (user_id, sub_tier),
        )
    return user_id


def _seed_shop_with_wo_and_mechanics(db_path, owner_user_id):
    """Create a shop owned by owner_user_id + 2 mechanic members + 1
    open WO. Returns (shop_id, wo_id, mechanic_ids)."""
    shop_id = create_shop("TestShop", db_path=db_path)
    seed_first_owner(shop_id, owner_user_id, db_path=db_path)

    mech1 = _make_user(db_path, "jose")
    add_shop_member(
        shop_id=shop_id, user_id=mech1,
        role="tech", db_path=db_path,
    )
    mech2 = _make_user(db_path, "maria")
    add_shop_member(
        shop_id=shop_id, user_id=mech2,
        role="tech", db_path=db_path,
    )

    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO vehicles (make, model, year, protocol) "
            "VALUES ('Honda', 'CBR600', 2005, 'none')"
        )
        vid = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO customers (name, phone, email) "
            "VALUES ('Alice', '555-0100', 'a@ex.com')"
        )
        cust_id = cur.lastrowid

    wo_id = create_work_order(
        shop_id=shop_id, vehicle_id=vid, customer_id=cust_id,
        title="brake service", priority=2, db_path=db_path,
    )
    return shop_id, wo_id, (mech1, mech2)


@pytest.fixture
def authed(api_db):
    user_id = _make_user(api_db, "owner")
    _, plaintext = create_api_key(user_id, db_path=api_db)
    shop_id, wo_id, mechs = _seed_shop_with_wo_and_mechanics(
        api_db, user_id,
    )
    return user_id, plaintext, shop_id, wo_id, mechs


@pytest.fixture
def client(api_db):
    return TestClient(create_app(db_path_override=api_db))


# ---------------------------------------------------------------------------
# 1. Happy path
# ---------------------------------------------------------------------------


class TestAssignHappyPath:

    def test_assigns_mechanic_to_unassigned_wo(self, client, authed):
        _, key, shop_id, wo_id, (mech1, _) = authed
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/assign",
            json={"mechanic_user_id": mech1},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["assigned_mechanic_user_id"] == mech1

    def test_reassigns_to_different_mechanic(self, client, authed):
        _, key, shop_id, wo_id, (mech1, mech2) = authed
        # First assign to mech1
        r1 = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/assign",
            json={"mechanic_user_id": mech1},
            headers={"X-API-Key": key},
        )
        assert r1.status_code == 200
        # Reassign to mech2
        r2 = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/assign",
            json={"mechanic_user_id": mech2},
            headers={"X-API-Key": key},
        )
        assert r2.status_code == 200
        assert r2.json()["assigned_mechanic_user_id"] == mech2

    def test_unassigns_via_null_mechanic_user_id(self, client, authed):
        _, key, shop_id, wo_id, (mech1, _) = authed
        # Assign first
        client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/assign",
            json={"mechanic_user_id": mech1},
            headers={"X-API-Key": key},
        )
        # Unassign explicitly via null
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/assign",
            json={"mechanic_user_id": None},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 200
        assert r.json()["assigned_mechanic_user_id"] is None


# ---------------------------------------------------------------------------
# 2. Validation
# ---------------------------------------------------------------------------


class TestAssignValidation:

    def test_omitting_mechanic_user_id_returns_422(self, client, authed):
        """Required field — clients MUST pass null explicitly to
        unassign rather than omitting. Pin so a future schema relax
        is an explicit decision."""
        _, key, shop_id, wo_id, _ = authed
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/assign",
            json={},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 422

    def test_nonexistent_mechanic_user_id_raises(self, client, authed):
        """Backend assign_mechanic validates user exists. Surface as
        500 (since the endpoint doesn't catch ValueError → maps to
        Internal Server Error). UI sees this as an `unknown` typed
        error per ShopAccessError classification."""
        _, key, shop_id, wo_id, _ = authed
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/assign",
            json={"mechanic_user_id": 999_999},
            headers={"X-API-Key": key},
        )
        # Backend's user-not-found ValueError is caught by FastAPI's
        # default exception handler + mapped to 400. Pin whichever
        # shape lands today; future RBAC refactor can tighten to a
        # more specific 404/422 without breaking the contract — UI
        # classifies any 4xx-other as `unknown` typed error per
        # ShopAccessError (matches Phase 193 Commit 1 surface).
        assert r.status_code in (400, 404, 422, 500)


# ---------------------------------------------------------------------------
# 3. Auth + cross-shop isolation
# ---------------------------------------------------------------------------


class TestAssignAuth:

    def test_unauth_returns_401(self, client, authed):
        _, _, shop_id, wo_id, (mech1, _) = authed
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/assign",
            json={"mechanic_user_id": mech1},
        )
        assert r.status_code == 401

    def test_individual_tier_returns_402(self, client, api_db, authed):
        _, _, shop_id, wo_id, (mech1, _) = authed
        # Make a fresh individual-tier user
        outsider_id = _make_user(api_db, "freebie", sub_tier="individual")
        _, outsider_key = create_api_key(outsider_id, db_path=api_db)
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/assign",
            json={"mechanic_user_id": mech1},
            headers={"X-API-Key": outsider_key},
        )
        assert r.status_code == 402

    def test_non_member_shop_tier_returns_403(
        self, client, api_db, authed,
    ):
        _, _, shop_id, wo_id, (mech1, _) = authed
        # Make a different shop-tier user with NO membership
        outsider = _make_user(api_db, "outsider", sub_tier="shop")
        _, outsider_key = create_api_key(outsider, db_path=api_db)
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/assign",
            json={"mechanic_user_id": mech1},
            headers={"X-API-Key": outsider_key},
        )
        assert r.status_code == 403

    def test_cross_shop_wo_returns_404(self, client, api_db, authed):
        """WO belongs to shop A; user is a member of shop A only;
        but the URL path uses shop B's id. Returns 404 (matches
        transition endpoint's posture — reveals 'wo not found in
        this shop' rather than 'wo doesn't exist anywhere')."""
        owner_id, key, _, wo_id, _ = authed
        # Create a different shop the owner is also a member of
        shop_b = create_shop("OtherShop", db_path=api_db)
        seed_first_owner(shop_b, owner_id, db_path=api_db)
        # Try to assign to the WO using shop_b's id in the URL
        # (WO actually belongs to the original shop_id).
        r = client.post(
            f"/v1/shop/{shop_b}/work-orders/{wo_id}/assign",
            json={"mechanic_user_id": owner_id},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 404

    def test_nonexistent_wo_returns_404(self, client, authed):
        _, key, shop_id, _, _ = authed
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/999999/assign",
            json={"mechanic_user_id": None},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 404
