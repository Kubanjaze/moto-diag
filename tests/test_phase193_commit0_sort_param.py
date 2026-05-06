"""Phase 193 Commit 0 — sort param on GET /v1/shop/{shop_id}/work-orders.

Pins the new ``sort`` query param's three values + None default:
- omitted / None → existing behavior (priority ASC, created_at DESC)
- 'priority' → same as omitting (explicit form for client clarity)
- 'newest' → re-sort by created_at DESC
- 'triage' → call build_triage_queue, unwrap to plain WO dicts
- invalid → 422

Response shape is uniform across all sort modes ({items, total} of
plain WO dicts) — triage scoring + rank context stay server-side
this phase per Phase 193 plan v1.0 + F35 candidate (mobile-side
explainability deferred until backend exposes the rich shape AND
mechanic-pull demand surfaces).

Pre-existing GET /work-orders behavior unchanged when sort is
omitted (backward-compat regression guard).
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import get_connection, init_db
from motodiag.shop import (
    create_shop, create_work_order, seed_first_owner,
)


# ---------------------------------------------------------------------------
# Fixtures (mirror Phase 180 style)
# ---------------------------------------------------------------------------


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase193_c0.db")
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


def _seed_shop_with_wos(db_path, user_id):
    """Create a shop owned by user_id + 4 WOs spanning priorities 1, 2,
    3, 5 with varied created_at to exercise both priority-sort and
    newest-sort orderings."""
    shop_id = create_shop("TestShop", db_path=db_path)
    seed_first_owner(shop_id, user_id, db_path=db_path)

    # Need a vehicle + customer for the FKs.
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

    # Create 4 WOs with explicit timestamps: oldest priority-5,
    # middle priority-1 (highest), middle-late priority-3, newest
    # priority-2. So orderings differ:
    #   priority sort: P1, P2, P3, P5 (best first)
    #   newest sort: P2 (newest), P3, P1, P5 (oldest)
    wo_ids = []
    for prio, label in [(5, "old-p5"), (1, "mid-p1"), (3, "mid-p3"), (2, "new-p2")]:
        wo_id = create_work_order(
            shop_id=shop_id, vehicle_id=vid, customer_id=cust_id,
            title=label, priority=prio, db_path=db_path,
        )
        wo_ids.append(wo_id)
        # Spread created_at — list_work_orders orders by it as
        # tiebreaker so we need monotonic timestamps. The tiniest
        # sleep keeps the underlying sqlite default datetime('now')
        # ordering deterministic on Windows + Linux.
        time.sleep(0.01)
    return shop_id, wo_ids


@pytest.fixture
def authed(api_db):
    user_id = _make_user(api_db, "owner", sub_tier="shop")
    _, plaintext = create_api_key(user_id, db_path=api_db)
    shop_id, wo_ids = _seed_shop_with_wos(api_db, user_id)
    return user_id, plaintext, shop_id, wo_ids


@pytest.fixture
def client(api_db):
    return TestClient(create_app(db_path_override=api_db))


# ---------------------------------------------------------------------------
# 1. Default behavior (sort omitted) — backward-compat regression
# ---------------------------------------------------------------------------


class TestDefaultUnchanged:

    def test_omitting_sort_preserves_priority_ordering(
        self, client, authed,
    ):
        """No sort param → existing list_work_orders ordering applies
        (priority ASC, created_at DESC). Priority-1 first, priority-5
        last. Backward-compat with pre-Commit-0 callers."""
        _, key, shop_id, _ = authed
        r = client.get(
            f"/v1/shop/{shop_id}/work-orders",
            headers={"X-API-Key": key},
        )
        assert r.status_code == 200
        items = r.json()["items"]
        priorities = [item["priority"] for item in items]
        # Priority ASC — so [1, 2, 3, 5].
        assert priorities == [1, 2, 3, 5]


# ---------------------------------------------------------------------------
# 2. Explicit sort=priority — same as default
# ---------------------------------------------------------------------------


class TestSortPriority:

    def test_explicit_priority_matches_default(self, client, authed):
        _, key, shop_id, _ = authed
        omit = client.get(
            f"/v1/shop/{shop_id}/work-orders",
            headers={"X-API-Key": key},
        )
        explicit = client.get(
            f"/v1/shop/{shop_id}/work-orders?sort=priority",
            headers={"X-API-Key": key},
        )
        assert omit.status_code == 200
        assert explicit.status_code == 200
        assert omit.json()["items"] == explicit.json()["items"]


# ---------------------------------------------------------------------------
# 3. sort=newest — re-sort by created_at DESC
# ---------------------------------------------------------------------------


class TestSortNewest:

    def test_newest_orders_by_created_at_desc(self, client, authed):
        _, key, shop_id, _ = authed
        r = client.get(
            f"/v1/shop/{shop_id}/work-orders?sort=newest",
            headers={"X-API-Key": key},
        )
        assert r.status_code == 200
        items = r.json()["items"]
        # Order of insertion was old-p5, mid-p1, mid-p3, new-p2 →
        # newest first = ['new-p2', 'mid-p3', 'mid-p1', 'old-p5'].
        titles = [item["title"] for item in items]
        assert titles == ["new-p2", "mid-p3", "mid-p1", "old-p5"]

    def test_newest_response_shape_uniform_with_priority(
        self, client, authed,
    ):
        """Sort doesn't change the response shape — same {items, total}
        envelope, same per-item fields. Only ordering differs."""
        _, key, shop_id, _ = authed
        priority = client.get(
            f"/v1/shop/{shop_id}/work-orders?sort=priority",
            headers={"X-API-Key": key},
        )
        newest = client.get(
            f"/v1/shop/{shop_id}/work-orders?sort=newest",
            headers={"X-API-Key": key},
        )
        priority_keys = set(priority.json()["items"][0].keys())
        newest_keys = set(newest.json()["items"][0].keys())
        assert priority_keys == newest_keys


# ---------------------------------------------------------------------------
# 4. sort=triage — call build_triage_queue + unwrap to plain WO dicts
# ---------------------------------------------------------------------------


class TestSortTriage:

    def test_triage_returns_plain_wo_dicts_not_triage_items(
        self, client, authed,
    ):
        """build_triage_queue returns TriageItem (work_order + score +
        rank + parts_ready). Route MUST unwrap to plain WO dicts so
        the response shape stays uniform with the other sort modes.
        Triage rank/score is server-side only this phase (F35)."""
        _, key, shop_id, _ = authed
        r = client.get(
            f"/v1/shop/{shop_id}/work-orders?sort=triage",
            headers={"X-API-Key": key},
        )
        assert r.status_code == 200
        items = r.json()["items"]
        for item in items:
            # Plain WO dict has these fields.
            assert "id" in item
            assert "title" in item
            assert "priority" in item
            # MUST NOT include the TriageItem wrapper fields —
            # rank / score / parts_ready are server-side only this
            # phase per Phase 193 plan + F35 candidate.
            assert "rank" not in item
            assert "triage_score" not in item
            assert "parts_ready" not in item

    def test_triage_excludes_terminal_states_by_default(
        self, client, api_db, authed,
    ):
        """build_triage_queue's include_terminal=False default means
        completed / cancelled WOs don't appear in the triage list.
        Pin so future refactors don't accidentally include them."""
        _, key, shop_id, wo_ids = authed
        # Mark one WO as completed via direct SQL (bypassing the
        # transition flow — pure setup).
        with get_connection(api_db) as conn:
            conn.execute(
                "UPDATE work_orders SET status = 'completed' "
                "WHERE id = ?",
                (wo_ids[0],),
            )
        r = client.get(
            f"/v1/shop/{shop_id}/work-orders?sort=triage",
            headers={"X-API-Key": key},
        )
        assert r.status_code == 200
        ids = [item["id"] for item in r.json()["items"]]
        assert wo_ids[0] not in ids


# ---------------------------------------------------------------------------
# 5. Invalid sort value → 422
# ---------------------------------------------------------------------------


class TestSortValidation:

    def test_invalid_sort_value_returns_422(self, client, authed):
        _, key, shop_id, _ = authed
        r = client.get(
            f"/v1/shop/{shop_id}/work-orders?sort=alphabetical",
            headers={"X-API-Key": key},
        )
        assert r.status_code == 422

    def test_status_filter_still_applies_with_sort_newest(
        self, client, api_db, authed,
    ):
        """sort + status filter compose. Pin so a future refactor
        doesn't drop the status filter when sort is set."""
        _, key, shop_id, wo_ids = authed
        with get_connection(api_db) as conn:
            conn.execute(
                "UPDATE work_orders SET status = 'in_progress' "
                "WHERE id = ?",
                (wo_ids[1],),
            )
        r = client.get(
            f"/v1/shop/{shop_id}/work-orders?sort=newest&status=in_progress",
            headers={"X-API-Key": key},
        )
        assert r.status_code == 200
        ids = [item["id"] for item in r.json()["items"]]
        assert ids == [wo_ids[1]]

    def test_status_filter_still_applies_with_sort_triage(
        self, client, api_db, authed,
    ):
        _, key, shop_id, wo_ids = authed
        with get_connection(api_db) as conn:
            conn.execute(
                "UPDATE work_orders SET status = 'in_progress' "
                "WHERE id = ?",
                (wo_ids[1],),
            )
        r = client.get(
            f"/v1/shop/{shop_id}/work-orders?sort=triage&status=in_progress",
            headers={"X-API-Key": key},
        )
        assert r.status_code == 200
        ids = [item["id"] for item in r.json()["items"]]
        assert ids == [wo_ids[1]]
