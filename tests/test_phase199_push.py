"""Phase 199 — push notification tests.

Covers: token registry (register/rebind/delete), the register/deregister
endpoints (auth boundary), the DryRunSender seam, event glue (recipient
resolution, self-suppression, 410-prune), and the WO-transition hook
wiring guard (integration-gap discipline: endpoint actually fires the
notify). Zero network, zero Apple — the ApnsSender's live path is the
device smoke's job.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import get_connection, init_db
from motodiag.push import events as push_events
from motodiag.push.registry import (
    delete_token, register_token, tokens_for_user,
)
from motodiag.push.sender import DryRunSender, PushResult


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase199_api.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("MOTODIAG_APNS_DRY_RUN", "1")
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()
    yield path
    reset_settings()


def _make_user(db_path, username="push_user"):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES (?, ?, 'individual', 1)",
            (username, f"{username}@ex.com"),
        )
        return cursor.lastrowid


def _authed_client(api_db, username="push_user"):
    user_id = _make_user(api_db, username)
    _, plaintext = create_api_key(user_id, db_path=api_db)
    app = create_app(db_path_override=api_db)
    client = TestClient(app, raise_server_exceptions=False)
    return client, plaintext, user_id


TOKEN_A = "a" * 64
TOKEN_B = "b" * 64


class TestRegistry:

    def test_register_and_list(self, api_db):
        uid = _make_user(api_db, "reg1")
        register_token(uid, TOKEN_A, db_path=api_db)
        assert tokens_for_user(uid, db_path=api_db) == [TOKEN_A]

    def test_rebind_on_user_switch(self, api_db):
        """Invariant: one row per TOKEN — rebinding, never duplicating."""
        u1 = _make_user(api_db, "reg2a")
        u2 = _make_user(api_db, "reg2b")
        register_token(u1, TOKEN_A, db_path=api_db)
        register_token(u2, TOKEN_A, db_path=api_db)
        assert tokens_for_user(u1, db_path=api_db) == []
        assert tokens_for_user(u2, db_path=api_db) == [TOKEN_A]

    def test_delete(self, api_db):
        uid = _make_user(api_db, "reg3")
        register_token(uid, TOKEN_A, db_path=api_db)
        assert delete_token(TOKEN_A, db_path=api_db) is True
        assert tokens_for_user(uid, db_path=api_db) == []
        assert delete_token(TOKEN_A, db_path=api_db) is False


class TestEndpoints:

    def test_register_requires_auth(self, api_db):
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post("/v1/push/register", json={"token": TOKEN_A})
        assert r.status_code == 401

    def test_register_roundtrip(self, api_db):
        client, key, uid = _authed_client(api_db, "ep1")
        r = client.post(
            "/v1/push/register",
            json={"token": TOKEN_A, "platform": "ios"},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 200
        assert r.json() == {"registered": True}
        assert tokens_for_user(uid, db_path=api_db) == [TOKEN_A]

    def test_deregister(self, api_db):
        client, key, uid = _authed_client(api_db, "ep2")
        client.post(
            "/v1/push/register", json={"token": TOKEN_A},
            headers={"X-API-Key": key},
        )
        r = client.request(
            "DELETE", "/v1/push/register",
            json={"token": TOKEN_A}, headers={"X-API-Key": key},
        )
        assert r.status_code == 200
        assert tokens_for_user(uid, db_path=api_db) == []


class TestEventGlue:

    def _wire_dry_sender(self, monkeypatch):
        sender = DryRunSender()
        monkeypatch.setattr(push_events, "get_sender", lambda: sender)
        return sender

    def test_wo_transition_notifies_assignee(self, api_db, monkeypatch):
        sender = self._wire_dry_sender(monkeypatch)
        mechanic = _make_user(api_db, "glue1")
        register_token(mechanic, TOKEN_A, db_path=api_db)
        wo = {"id": 7, "title": "Fork seals", "assigned_mechanic_user_id": mechanic}
        push_events.notify_wo_transition(wo, "complete", acting_user_id=999, db_path=api_db)
        assert len(sender.sent) == 1
        assert "Work order #7" in sender.sent[0]["title"]
        assert sender.sent[0]["thread_id"] == "wo-7"

    def test_self_suppression(self, api_db, monkeypatch):
        sender = self._wire_dry_sender(monkeypatch)
        mechanic = _make_user(api_db, "glue2")
        register_token(mechanic, TOKEN_A, db_path=api_db)
        wo = {"id": 8, "title": "x", "assigned_mechanic_user_id": mechanic}
        push_events.notify_wo_transition(wo, "complete", acting_user_id=mechanic, db_path=api_db)
        assert sender.sent == []

    def test_unassigned_wo_is_quiet(self, api_db, monkeypatch):
        sender = self._wire_dry_sender(monkeypatch)
        push_events.notify_wo_transition(
            {"id": 9, "assigned_mechanic_user_id": None}, "complete",
            acting_user_id=1, db_path=api_db,
        )
        assert sender.sent == []

    def test_410_prunes_token(self, api_db, monkeypatch):
        class DeadTokenSender:
            def __init__(self):
                self.calls = 0

            def send(self, token, title, body, thread_id=None):
                self.calls += 1
                return PushResult(ok=False, unregistered=True, detail="410")

        sender = DeadTokenSender()
        monkeypatch.setattr(push_events, "get_sender", lambda: sender)
        mechanic = _make_user(api_db, "glue3")
        register_token(mechanic, TOKEN_B, db_path=api_db)
        wo = {"id": 10, "title": "x", "assigned_mechanic_user_id": mechanic}
        push_events.notify_wo_transition(wo, "complete", acting_user_id=1, db_path=api_db)
        assert sender.calls == 1
        assert tokens_for_user(mechanic, db_path=api_db) == []

    def test_analysis_complete_notifies_session_owner(self, api_db, monkeypatch):
        sender = self._wire_dry_sender(monkeypatch)
        owner = _make_user(api_db, "glue4")
        register_token(owner, TOKEN_A, db_path=api_db)
        with get_connection(api_db) as conn:
            cursor = conn.execute(
                "INSERT INTO diagnostic_sessions "
                "(vehicle_make, vehicle_model, vehicle_year, status, user_id) "
                "VALUES ('Harley', 'Sportster', 2008, 'open', ?)",
                (owner,),
            )
            session_id = cursor.lastrowid
        push_events.notify_analysis_complete(session_id, video_id=1, db_path=api_db)
        assert len(sender.sent) == 1
        assert "analysis" in sender.sent[0]["title"].lower()
        assert "Harley Sportster" in sender.sent[0]["body"]


def _make_sub(db_path, user_id, tier="shop"):
    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT INTO subscriptions
               (user_id, tier, status, current_period_end)
               VALUES (?, ?, 'active', datetime('now', '+30 days'))""",
            (user_id, tier),
        )


class TestHookWiringGuard:
    """Integration-gap discipline: the ENDPOINT fires the notify —
    function-exists-but-wiring-absent is the F9 subtype this pins.
    Setup mirrors the Gate-9 bootstrap idiom (test_phase184_gate9)."""

    def test_transition_endpoint_invokes_notify(self, api_db, monkeypatch):
        calls = []
        monkeypatch.setattr(
            "motodiag.api.routes.shop_mgmt.notify_wo_transition",
            lambda wo, action, acting, db_path=None: calls.append(
                (wo.get("id"), action, acting),
            ),
        )
        from motodiag.crm import customer_repo
        from motodiag.crm.models import Customer
        from motodiag.shop import create_work_order, seed_first_owner

        owner_id = _make_user(api_db, "hook_owner")
        _make_sub(api_db, owner_id, tier="shop")
        _, key = create_api_key(owner_id, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)

        r = client.post(
            "/v1/shop/profile", headers={"X-API-Key": key},
            json={"name": "Hook Shop"},
        )
        assert r.status_code == 201, r.text
        shop_id = r.json()["id"]
        seed_first_owner(shop_id, owner_id, db_path=api_db)

        cust_id = customer_repo.create_customer(
            Customer(name="guard customer", phone="555", email="g@ex.com"),
            db_path=api_db,
        )
        with get_connection(api_db) as conn:
            cursor = conn.execute(
                "INSERT INTO vehicles (make, model, year, protocol) "
                "VALUES ('Honda', 'CBR', 2005, 'none')",
            )
            vid = cursor.lastrowid
        wo_id = create_work_order(
            shop_id=shop_id, vehicle_id=vid, customer_id=cust_id,
            title="Guard WO", db_path=api_db,
        )

        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/transition",
            json={"action": "open"},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 200, r.text
        assert calls and calls[0][0] == wo_id and calls[0][1] == "open"
