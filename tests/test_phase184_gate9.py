"""Phase 184 — Gate 9: intake-to-invoice via HTTP integration test.

**Closes Track H.** Walks the full mechanic workflow from customer
intake to paid invoice using only the HTTP endpoints Phases
175-183 shipped — no CLI, no direct repo calls in the assertion
path. Some bootstrapping (user row, API key, subscription, shop
membership) seeds via direct repo calls because those API surfaces
are owned by Track I (signup / Stripe checkout / role assignment
flows) and aren't exercised by Gate 9 itself.

Five test classes:
- :class:`TestGate9HappyPath` — single-walk end-to-end flow.
- :class:`TestGate9CrossUserIsolation` — owner scoping holds.
- :class:`TestGate9CrossShopIsolation` — shop membership boundary holds.
- :class:`TestGate9OpenAPIContract` — Phase 183 enrichment intact.
- :class:`TestGate9AntiRegression` — schema unchanged, summary docs ship.

Zero AI, zero network.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.api.openapi import (
    ERROR_RESPONSES, SECURITY_SCHEMES, TAG_CATALOG,
)
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import (
    SCHEMA_VERSION, get_connection, init_db,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase184.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()
    yield path
    reset_settings()


def _make_user(db_path, username):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES (?, ?, 'individual', 1)",
            (username, f"{username}@ex.com"),
        )
        return cursor.lastrowid


def _make_sub(db_path, user_id, tier="shop"):
    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT INTO subscriptions
               (user_id, tier, status, current_period_end)
               VALUES (?, ?, 'active', datetime('now', '+30 days'))""",
            (user_id, tier),
        )


def _seed_shop_owner(db_path, username="owner", tier="shop"):
    """Bootstrap: create a user row + active subscription + API key.
    Returns (user_id, api_key_plaintext)."""
    uid = _make_user(db_path, username)
    _make_sub(db_path, uid, tier=tier)
    _, plaintext = create_api_key(uid, db_path=db_path)
    return uid, plaintext


def _seed_membership(db_path, user_id, shop_id):
    """Bootstrap: link a user to a shop as `owner` so
    require_shop_access() passes."""
    from motodiag.shop import seed_first_owner
    seed_first_owner(shop_id, user_id, db_path=db_path)


# ===========================================================================
# 1. End-to-end happy path
# ===========================================================================


class TestGate9HappyPath:

    def test_full_lifecycle(self, api_db):
        """Walk a single mechanic from signup to paid invoice
        through 27 HTTP calls. Every step asserts status code +
        a structural invariant."""
        owner_id, owner_key = _seed_shop_owner(api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        H = {"X-API-Key": owner_key}

        # 1. Sanity: /v1/version is public + reachable.
        r = client.get("/v1/version")
        assert r.status_code == 200
        version_body = r.json()
        assert "api_version" in version_body
        assert "schema_version" in version_body

        # 2. Create shop.
        r = client.post(
            "/v1/shop/profile", headers=H,
            json={"name": "Bob's Cycle Shop", "phone": "555-0100"},
        )
        assert r.status_code == 201, r.text
        shop_id = r.json()["id"]
        assert shop_id > 0

        # 3. Seed owner membership (Track I will do this via Stripe
        # checkout; Gate 9 boots it directly).
        _seed_membership(api_db, owner_id, shop_id)

        # 4. Create a customer at the shop.
        r = client.post(
            f"/v1/shop/{shop_id}/customers", headers=H,
            json={
                "name": "Alice Rider",
                "email": "alice@ex.com",
                "phone": "555-0200",
            },
        )
        assert r.status_code == 201, r.text
        customer_id = r.json()["id"]
        assert customer_id > 0

        # 5. Register a vehicle in the OWNER's garage (vehicles
        # endpoint is owner-scoped, not shop-scoped).
        r = client.post(
            "/v1/vehicles", headers=H,
            json={
                "make": "Honda", "model": "CBR600",
                "year": 2005, "engine_cc": 599,
                "protocol": "none",
            },
        )
        assert r.status_code == 201, r.text
        vehicle_id = r.json()["id"]
        assert vehicle_id > 0

        # 6. Open a diagnostic session.
        r = client.post(
            "/v1/sessions", headers=H,
            json={
                "vehicle_make": "Honda", "vehicle_model": "CBR600",
                "vehicle_year": 2005,
                "vehicle_id": vehicle_id,
                "symptoms": ["rough idle"],
                "fault_codes": ["P0171"],
            },
        )
        assert r.status_code == 201, r.text
        session_id = r.json()["id"]
        assert r.json()["status"] == "open"

        # 7. Append a second symptom.
        r = client.post(
            f"/v1/sessions/{session_id}/symptoms", headers=H,
            json={"symptom": "stalls below 1500rpm"},
        )
        assert r.status_code == 200
        assert "stalls below 1500rpm" in r.json()["symptoms"]

        # 8. Append a second fault code.
        r = client.post(
            f"/v1/sessions/{session_id}/fault-codes", headers=H,
            json={"code": "P0507"},
        )
        assert r.status_code == 200

        # 9. Set diagnosis + confidence + severity.
        r = client.patch(
            f"/v1/sessions/{session_id}", headers=H,
            json={
                "diagnosis": "fuel filter clogged + dirty IAC valve",
                "confidence": 0.85, "severity": "medium",
                "cost_estimate": 180.00,
            },
        )
        assert r.status_code == 200
        assert r.json()["diagnosis"].startswith("fuel filter clogged")

        # 10. Download session report PDF.
        r = client.get(
            f"/v1/reports/session/{session_id}/pdf", headers=H,
        )
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert r.content[:5] == b"%PDF-"
        assert len(r.content) > 500

        # 11. Look up a DTC.
        r = client.get("/v1/kb/dtc/P0171", headers=H)
        assert r.status_code in (200, 404)  # P0171 may or may not be seeded

        # 12. Unified KB search.
        r = client.get("/v1/kb/search?q=idle", headers=H)
        assert r.status_code == 200

        # 13. Close the session.
        r = client.post(
            f"/v1/sessions/{session_id}/close", headers=H,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "closed"

        # 14. Create a work order in the shop.
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders", headers=H,
            json={
                "vehicle_id": vehicle_id,
                "customer_id": customer_id,
                "title": "Fuel filter + IAC valve service",
                "description": "Per session diagnosis",
                "estimated_hours": 2.0,
                "priority": 3,
            },
        )
        assert r.status_code == 201, r.text
        wo_id = r.json()["id"]
        assert r.json()["status"] == "draft"

        # 15. Open the WO.
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/transition",
            headers=H, json={"action": "open"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "open"

        # 16. Start work.
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/transition",
            headers=H, json={"action": "start"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"

        # 17. Log an issue against the WO.
        r = client.post(
            f"/v1/shop/{shop_id}/issues", headers=H,
            json={
                "work_order_id": wo_id,
                "title": "Fuel filter heavily clogged",
                "category": "fuel_system",
                "severity": "medium",
            },
        )
        assert r.status_code == 201, r.text

        # 18. Complete the WO with actual hours.
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/transition",
            headers=H,
            json={"action": "complete", "actual_hours": 2.0},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "completed"

        # 19. Generate invoice.
        r = client.post(
            f"/v1/shop/{shop_id}/invoices/generate", headers=H,
            json={
                "work_order_id": wo_id,
                "labor_hourly_rate_cents": 10000,
                "tax_rate": 0.0825,
            },
        )
        assert r.status_code == 201, r.text
        inv = r.json()
        invoice_id = inv["id"]
        assert inv["subtotal_cents"] == 20000  # 2h × $100 × 100
        assert inv["tax_cents"] > 0
        assert inv["total_cents"] >= inv["subtotal_cents"]

        # 20. Download work-order receipt PDF.
        r = client.get(
            f"/v1/reports/work-order/{wo_id}/pdf", headers=H,
        )
        assert r.status_code == 200
        assert r.content[:5] == b"%PDF-"
        cd = r.headers.get("content-disposition", "")
        assert f"work-order-{wo_id}" in cd

        # 21. Download invoice PDF.
        r = client.get(
            f"/v1/reports/invoice/{invoice_id}/pdf", headers=H,
        )
        assert r.status_code == 200
        assert r.content[:5] == b"%PDF-"

        # 22. JSON preview of invoice (sanity — same data, no PDF).
        r = client.get(
            f"/v1/reports/invoice/{invoice_id}", headers=H,
        )
        assert r.status_code == 200
        body = r.json()
        totals = next(
            s for s in body["sections"] if s.get("heading") == "Totals"
        )
        assert any("Total" in row[0] for row in totals["rows"])

        # 23. Shop analytics snapshot reflects the completed WO.
        r = client.get(
            f"/v1/shop/{shop_id}/analytics/snapshot", headers=H,
        )
        assert r.status_code == 200
        snapshot = r.json()
        # Snapshot shape varies by Phase 171 — just assert it's a dict
        assert isinstance(snapshot, dict)

        # 24. List sessions surfaces the closed one with quota meta.
        r = client.get("/v1/sessions", headers=H)
        assert r.status_code == 200
        listing = r.json()
        assert listing["total_this_month"] >= 1
        # Owner has shop-tier sub → 500/mo quota.
        assert listing["monthly_quota_limit"] == 500

        # 25. List vehicles surfaces our bike.
        r = client.get("/v1/vehicles", headers=H)
        assert r.status_code == 200
        veh_listing = r.json()
        assert any(
            v["id"] == vehicle_id for v in veh_listing["items"]
        )

        # 26. List the shop's invoices.
        r = client.get(
            f"/v1/shop/{shop_id}/invoices", headers=H,
        )
        assert r.status_code == 200
        assert r.json()["total"] >= 1

        # 27. /openapi.json sanity (Phase 183 enrichment intact).
        r = client.get("/openapi.json")
        assert r.status_code == 200
        spec = r.json()
        assert "servers" in spec
        assert spec["info"]["license"]["name"] == "MIT"


# ===========================================================================
# 2. Cross-user isolation
# ===========================================================================


class TestGate9CrossUserIsolation:

    def test_user_b_cannot_see_user_a_garage_or_session(self, api_db):
        """Two users, two API keys. User B may not enumerate or
        fetch User A's vehicles or session reports."""
        a_id, a_key = _seed_shop_owner(api_db, "alice", tier="individual")
        b_id, b_key = _seed_shop_owner(api_db, "bob", tier="individual")
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)

        # Alice creates a vehicle.
        r = client.post(
            "/v1/vehicles", headers={"X-API-Key": a_key},
            json={
                "make": "Honda", "model": "CBR600",
                "year": 2005, "protocol": "none",
            },
        )
        assert r.status_code == 201
        a_vehicle = r.json()["id"]

        # Alice opens a session.
        r = client.post(
            "/v1/sessions", headers={"X-API-Key": a_key},
            json={
                "vehicle_make": "Honda", "vehicle_model": "CBR600",
                "vehicle_year": 2005,
            },
        )
        assert r.status_code == 201
        a_session = r.json()["id"]

        # Bob tries to fetch Alice's vehicle → 404 (not 403 — we
        # treat unauthorized access and missing-resource the same
        # to prevent enumeration attacks).
        r = client.get(
            f"/v1/vehicles/{a_vehicle}",
            headers={"X-API-Key": b_key},
        )
        assert r.status_code == 404

        # Bob tries to download Alice's session report → 404.
        r = client.get(
            f"/v1/reports/session/{a_session}",
            headers={"X-API-Key": b_key},
        )
        assert r.status_code == 404

        r = client.get(
            f"/v1/reports/session/{a_session}/pdf",
            headers={"X-API-Key": b_key},
        )
        assert r.status_code == 404

        # Bob's own listings are empty.
        r = client.get(
            "/v1/vehicles", headers={"X-API-Key": b_key},
        )
        assert r.json()["items"] == []
        r = client.get(
            "/v1/sessions", headers={"X-API-Key": b_key},
        )
        assert r.json()["items"] == []


# ===========================================================================
# 3. Cross-shop isolation
# ===========================================================================


class TestGate9CrossShopIsolation:

    def _bootstrap_shop_with_invoice(
        self, api_db, owner_username, shop_name,
    ):
        """Build {owner+key, shop, customer, vehicle, completed WO,
        invoice} for one shop. Returns (key, shop_id, wo_id, inv_id)."""
        from motodiag.crm import customer_repo
        from motodiag.crm.models import Customer
        from motodiag.shop import (
            complete_work_order, create_work_order,
            generate_invoice_for_wo, open_work_order, start_work,
        )
        owner_id, key = _seed_shop_owner(
            api_db, owner_username, tier="shop",
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            "/v1/shop/profile", headers={"X-API-Key": key},
            json={"name": shop_name},
        )
        assert r.status_code == 201, r.text
        shop_id = r.json()["id"]
        _seed_membership(api_db, owner_id, shop_id)
        # Customer + vehicle + WO via direct repos (faster than
        # threading through HTTP again).
        cust_id = customer_repo.create_customer(
            Customer(name=f"{owner_username}'s customer",
                     phone="555", email="c@ex.com"),
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
            title="x", estimated_hours=2.0, db_path=api_db,
        )
        open_work_order(wo_id, db_path=api_db)
        start_work(wo_id, db_path=api_db)
        complete_work_order(wo_id, actual_hours=2.0, db_path=api_db)
        inv_id = generate_invoice_for_wo(
            wo_id=wo_id, labor_hourly_rate_cents=10000,
            db_path=api_db,
        )
        return key, shop_id, wo_id, inv_id

    def test_shop_b_cannot_access_shop_a_resources(self, api_db):
        a_key, a_shop, a_wo, a_inv = self._bootstrap_shop_with_invoice(
            api_db, "alice", "Alice's Shop",
        )
        b_key, b_shop, _, _ = self._bootstrap_shop_with_invoice(
            api_db, "bob", "Bob's Shop",
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)

        # Bob tries to download Alice's WO report → 403.
        r = client.get(
            f"/v1/reports/work-order/{a_wo}",
            headers={"X-API-Key": b_key},
        )
        assert r.status_code == 403

        r = client.get(
            f"/v1/reports/work-order/{a_wo}/pdf",
            headers={"X-API-Key": b_key},
        )
        assert r.status_code == 403

        # Bob tries to download Alice's invoice → 403.
        r = client.get(
            f"/v1/reports/invoice/{a_inv}/pdf",
            headers={"X-API-Key": b_key},
        )
        assert r.status_code == 403

        # Bob tries to list Alice's WOs by hitting Alice's shop_id
        # in the URL — 403 (not Bob's shop).
        r = client.get(
            f"/v1/shop/{a_shop}/work-orders",
            headers={"X-API-Key": b_key},
        )
        assert r.status_code == 403

        # Bob tries to create a WO at Alice's shop → 403.
        r = client.post(
            f"/v1/shop/{a_shop}/work-orders",
            headers={"X-API-Key": b_key},
            json={
                "vehicle_id": 999, "customer_id": 999,
                "title": "pwn", "estimated_hours": 1.0,
            },
        )
        assert r.status_code == 403


# ===========================================================================
# 4. OpenAPI contract regression (Phase 183 enrichment intact)
# ===========================================================================


class TestGate9OpenAPIContract:

    def test_all_tags_present(self, api_db):
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        spec = client.get("/openapi.json").json()
        names = {t["name"] for t in spec["tags"]}
        expected = {t["name"] for t in TAG_CATALOG}
        assert names == expected

    def test_all_error_responses_present(self, api_db):
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        spec = client.get("/openapi.json").json()
        for name in ERROR_RESPONSES:
            assert name in spec["components"]["responses"]

    def test_security_schemes_present(self, api_db):
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        spec = client.get("/openapi.json").json()
        for scheme in SECURITY_SCHEMES:
            assert scheme in spec["components"]["securitySchemes"]

    def test_authed_endpoint_has_apikey_security(self, api_db):
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        spec = client.get("/openapi.json").json()
        op = spec["paths"]["/v1/vehicles"]["get"]
        sec = op.get("security") or []
        schemes = {list(entry.keys())[0] for entry in sec}
        assert "apiKey" in schemes


# ===========================================================================
# 5. Anti-regression invariants
# ===========================================================================


class TestGate9AntiRegression:

    def test_schema_version_unchanged(self):
        # Gate 9 anti-regression pin. Last migration was 039 (Phase
        # 191B videos table for video diagnostic capture). Bump this
        # pin alongside any deliberate SCHEMA_VERSION change AND the
        # corresponding migration; an unintended bump must fail loud.
        # F-ticket F20 (filed 2026-05-04 with Phase 191B fix-cycle-5):
        # generalize Phase 191C's no-hardcoded-model-ids lint rule to
        # "no hardcoded SSOT-managed constants in tests" — would have
        # caught this missed-pin-update at Phase 191B finalize.
        assert SCHEMA_VERSION == 39

    def test_track_h_summary_doc_exists(self):
        path = (
            Path(__file__).parent.parent
            / "docs" / "phases" / "completed"
            / "TRACK_H_SUMMARY.md"
        )
        assert path.exists(), (
            "Track H closure summary must ship with Gate 9 — "
            f"expected at {path}"
        )
        text = path.read_text(encoding="utf-8")
        assert "Track H closed" in text

    def test_phase_184_implementation_doc_exists(self):
        # Self-check: Gate 9's own implementation doc must be in
        # `completed/` after the gate ships, not stranded in
        # `in_progress/`.
        path = (
            Path(__file__).parent.parent
            / "docs" / "phases" / "completed"
            / "184_implementation.md"
        )
        # Allow the doc to exist in either location during the
        # build phase; once finalized it must be in completed/.
        in_prog = (
            Path(__file__).parent.parent
            / "docs" / "phases" / "in_progress"
            / "184_implementation.md"
        )
        assert path.exists() or in_prog.exists(), (
            "Phase 184 implementation.md missing from both "
            "completed/ and in_progress/"
        )
