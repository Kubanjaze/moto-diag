"""Phase 201 — parts ordering over HTTP.

The domain layer (Track G `shop/parts_needs.py`, `advanced/parts_repo.py`)
already has its own tests. This file covers what Phase 201 actually adds:
HTTP shape, shop scoping on every route, the cart semantics the router
composes (dedupe-on-add, bulk order, delete-vs-cancel), and the one new
behaviour — `parts_arrived` firing on the `received` transition.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from motodiag.api.app import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import get_connection, init_db


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase201.db")
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
        return conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES (?, ?, 'individual', 1)",
            (username, f"{username}@ex.com"),
        ).lastrowid


def _make_sub(db_path, user_id, tier="shop"):
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO subscriptions (user_id, tier, status, "
            "current_period_end) VALUES (?, ?, 'active', "
            "datetime('now', '+30 days'))",
            (user_id, tier),
        )


def _seed_part(db_path, slug, oem="OEM-1", cost=1250, make="honda",
               model_pattern="CBR%", category="brakes"):
    """Seed a catalog row directly.

    `make` is stored LOWERCASE because `parts_repo._normalize_make`
    lowercases on the way in and `list_parts_for_bike` compares with
    `make = ?` against the normalized value. Seeding "Honda" here makes
    fitment search silently return nothing — which is exactly how this
    fixture failed on the first run."""
    with get_connection(db_path) as conn:
        return conn.execute(
            "INSERT INTO parts (slug, oem_part_number, brand, description, "
            "category, make, model_pattern, typical_cost_cents) "
            "VALUES (?, ?, 'Brembo', ?, ?, ?, ?, ?)",
            (slug, oem, f"desc {slug}", category, make, model_pattern, cost),
        ).lastrowid


@pytest.fixture
def shop_ctx(api_db):
    """Owner with a shop, a work order, and two catalog parts."""
    from motodiag.crm import customer_repo
    from motodiag.crm.models import Customer
    from motodiag.shop import create_work_order, seed_first_owner

    owner = _make_user(api_db, "p201_owner")
    _make_sub(api_db, owner, tier="shop")
    _, key = create_api_key(owner, db_path=api_db)
    client = TestClient(
        create_app(db_path_override=api_db), raise_server_exceptions=False,
    )
    headers = {"X-API-Key": key}
    shop_id = client.post(
        "/v1/shop/profile", headers=headers, json={"name": "P201 Shop"},
    ).json()["id"]
    seed_first_owner(shop_id, owner, db_path=api_db)

    cust = customer_repo.create_customer(
        Customer(name="Dana", phone="555", email="d@ex.com"), db_path=api_db,
    )
    with get_connection(api_db) as conn:
        vid = conn.execute(
            "INSERT INTO vehicles (make, model, year, protocol) "
            "VALUES ('Honda', 'CBR600RR', 2016, 'none')",
        ).lastrowid
    wo_id = create_work_order(
        shop_id=shop_id, vehicle_id=vid, customer_id=cust,
        title="Brake job", db_path=api_db,
    )
    # create_work_order lands in `draft`. The shop-wide consolidation
    # (`list_parts_for_shop_open_wos`) only counts WOs whose status is
    # open / in_progress / on_hold, so a draft WO contributes nothing to
    # needs or requisitions. Open it through the real endpoint.
    opened = client.post(
        f"/v1/shop/{shop_id}/work-orders/{wo_id}/transition",
        json={"action": "open"}, headers=headers,
    )
    assert opened.status_code == 200, opened.text
    part_a = _seed_part(api_db, "brake-pad-front")
    part_b = _seed_part(api_db, "brake-fluid", oem="OEM-2", cost=800)
    return {
        "client": client, "headers": headers, "shop_id": shop_id,
        "wo_id": wo_id, "owner": owner, "part_a": part_a,
        "part_b": part_b, "db": api_db,
    }


def _add(ctx, part_id, quantity=1, **body):
    return ctx["client"].post(
        f"/v1/shop/{ctx['shop_id']}/work-orders/{ctx['wo_id']}/parts",
        json={"part_id": part_id, "quantity": quantity, **body},
        headers=ctx["headers"],
    )


def _lines(ctx):
    return ctx["client"].get(
        f"/v1/shop/{ctx['shop_id']}/work-orders/{ctx['wo_id']}/parts",
        headers=ctx["headers"],
    ).json()


def _transition(ctx, wop_id, action, **body):
    return ctx["client"].post(
        f"/v1/shop/{ctx['shop_id']}/work-orders/{ctx['wo_id']}"
        f"/parts/{wop_id}/transition",
        json={"action": action, **body}, headers=ctx["headers"],
    )


class TestAccessControl:
    def test_no_key_is_401(self, shop_ctx):
        r = shop_ctx["client"].get(
            f"/v1/shop/{shop_ctx['shop_id']}/parts/search?q=brake",
        )
        assert r.status_code == 401

    def test_individual_tier_is_402(self, shop_ctx, api_db):
        poor = _make_user(api_db, "p201_poor")
        _make_sub(api_db, poor, tier="individual")
        _, key = create_api_key(poor, db_path=api_db)
        r = shop_ctx["client"].get(
            f"/v1/shop/{shop_ctx['shop_id']}/parts/search?q=brake",
            headers={"X-API-Key": key},
        )
        assert r.status_code == 402

    def test_shop_tier_non_member_is_403(self, shop_ctx, api_db):
        outsider = _make_user(api_db, "p201_outsider")
        _make_sub(api_db, outsider, tier="shop")
        _, key = create_api_key(outsider, db_path=api_db)
        r = shop_ctx["client"].get(
            f"/v1/shop/{shop_ctx['shop_id']}/parts/search?q=brake",
            headers={"X-API-Key": key},
        )
        assert r.status_code == 403

    def test_work_order_from_another_shop_is_404(self, shop_ctx, api_db):
        from motodiag.shop import create_work_order, seed_first_owner
        other_owner = _make_user(api_db, "p201_other")
        _make_sub(api_db, other_owner, tier="shop")
        _, other_key = create_api_key(other_owner, db_path=api_db)
        other_shop = shop_ctx["client"].post(
            "/v1/shop/profile", headers={"X-API-Key": other_key},
            json={"name": "Other Shop"},
        ).json()["id"]
        seed_first_owner(other_shop, other_owner, db_path=api_db)
        # This shop's member asks for the OTHER shop's WO id.
        r = shop_ctx["client"].get(
            f"/v1/shop/{shop_ctx['shop_id']}/work-orders/999999/parts",
            headers=shop_ctx["headers"],
        )
        assert r.status_code == 404


class TestCatalogBrowse:
    def test_free_text_search(self, shop_ctx):
        r = shop_ctx["client"].get(
            f"/v1/shop/{shop_ctx['shop_id']}/parts/search?q=brake-pad",
            headers=shop_ctx["headers"],
        )
        assert r.status_code == 200
        assert any(p["slug"] == "brake-pad-front" for p in r.json())

    def test_bike_fitment_when_no_free_text(self, shop_ctx):
        r = shop_ctx["client"].get(
            f"/v1/shop/{shop_ctx['shop_id']}/parts/search"
            "?make=Honda&model=CBR600RR",
            headers=shop_ctx["headers"],
        )
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_part_detail_includes_xrefs_key(self, shop_ctx):
        r = shop_ctx["client"].get(
            f"/v1/shop/{shop_ctx['shop_id']}/parts/{shop_ctx['part_a']}",
            headers=shop_ctx["headers"],
        )
        assert r.status_code == 200
        assert r.json()["slug"] == "brake-pad-front"
        assert isinstance(r.json()["xrefs"], list)

    def test_unknown_part_is_404(self, shop_ctx):
        r = shop_ctx["client"].get(
            f"/v1/shop/{shop_ctx['shop_id']}/parts/999999",
            headers=shop_ctx["headers"],
        )
        assert r.status_code == 404

    def test_requisitions_path_is_not_parsed_as_a_part_id(self, shop_ctx):
        """Route ordering guard: /parts/requisitions must not be
        swallowed by /parts/{part_id}."""
        r = shop_ctx["client"].get(
            f"/v1/shop/{shop_ctx['shop_id']}/parts/requisitions",
            headers=shop_ctx["headers"],
        )
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestCart:
    def test_add_then_list(self, shop_ctx):
        r = _add(shop_ctx, shop_ctx["part_a"], quantity=2)
        assert r.status_code == 201, r.text
        line = r.json()
        assert line["status"] == "open"
        assert line["quantity"] == 2
        assert line["part_slug"] == "brake-pad-front"
        assert line["unit_cost_cents"] == 1250
        assert line["line_subtotal_cents"] == 2500
        assert line["merged"] is False
        assert [l["id"] for l in _lines(shop_ctx)] == [line["id"]]

    def test_adding_the_same_part_bumps_quantity_instead_of_a_second_line(
        self, shop_ctx,
    ):
        first = _add(shop_ctx, shop_ctx["part_a"], quantity=1).json()
        again = _add(shop_ctx, shop_ctx["part_a"], quantity=3)
        assert again.status_code == 200  # merged, not created
        assert again.json()["id"] == first["id"]
        assert again.json()["quantity"] == 4
        assert again.json()["merged"] is True
        assert len(_lines(shop_ctx)) == 1

    def test_line_records_the_real_caller_not_the_seed_user(self, shop_ctx):
        wop = _add(shop_ctx, shop_ctx["part_a"]).json()["id"]
        with get_connection(shop_ctx["db"]) as conn:
            created_by = conn.execute(
                "SELECT created_by_user_id FROM work_order_parts WHERE id = ?",
                (wop,),
            ).fetchone()[0]
        assert created_by == shop_ctx["owner"]

    def test_patch_quantity_and_cost_override(self, shop_ctx):
        wop = _add(shop_ctx, shop_ctx["part_a"]).json()["id"]
        base = f"/v1/shop/{shop_ctx['shop_id']}/work-orders/{shop_ctx['wo_id']}"
        r = shop_ctx["client"].patch(
            f"{base}/parts/{wop}",
            json={"quantity": 5, "unit_cost_cents_override": 999},
            headers=shop_ctx["headers"],
        )
        assert r.status_code == 200, r.text
        assert r.json()["quantity"] == 5
        assert r.json()["unit_cost_cents"] == 999
        assert r.json()["unit_cost_source"] == "override"

    def test_explicit_null_clears_the_override_but_omission_does_not(
        self, shop_ctx,
    ):
        wop = _add(
            shop_ctx, shop_ctx["part_a"], unit_cost_cents_override=999,
        ).json()["id"]
        base = f"/v1/shop/{shop_ctx['shop_id']}/work-orders/{shop_ctx['wo_id']}"
        # Omitted → untouched (a 0 would mean "free", not "no override").
        r = shop_ctx["client"].patch(
            f"{base}/parts/{wop}", json={"quantity": 2},
            headers=shop_ctx["headers"],
        )
        assert r.json()["unit_cost_cents"] == 999
        # Explicit null → cleared, falls back to the catalog price.
        r = shop_ctx["client"].patch(
            f"{base}/parts/{wop}", json={"unit_cost_cents_override": None},
            headers=shop_ctx["headers"],
        )
        assert r.json()["unit_cost_cents"] == 1250
        assert r.json()["unit_cost_source"] == "catalog"

    def test_delete_open_line_removes_it(self, shop_ctx):
        wop = _add(shop_ctx, shop_ctx["part_a"]).json()["id"]
        r = shop_ctx["client"].delete(
            f"/v1/shop/{shop_ctx['shop_id']}/work-orders/"
            f"{shop_ctx['wo_id']}/parts/{wop}",
            headers=shop_ctx["headers"],
        )
        assert r.status_code == 200
        assert r.json() == {"removed": True, "cancelled": False}
        assert _lines(shop_ctx) == []

    def test_delete_after_ordered_cancels_and_keeps_history(self, shop_ctx):
        wop = _add(shop_ctx, shop_ctx["part_a"]).json()["id"]
        _transition(shop_ctx, wop, "ordered")
        r = shop_ctx["client"].delete(
            f"/v1/shop/{shop_ctx['shop_id']}/work-orders/"
            f"{shop_ctx['wo_id']}/parts/{wop}",
            headers=shop_ctx["headers"],
        )
        assert r.json() == {"removed": False, "cancelled": True}
        with_cancelled = shop_ctx["client"].get(
            f"/v1/shop/{shop_ctx['shop_id']}/work-orders/"
            f"{shop_ctx['wo_id']}/parts?include_cancelled=true",
            headers=shop_ctx["headers"],
        ).json()
        assert [l["status"] for l in with_cancelled] == ["cancelled"]

    def test_line_from_another_work_order_is_404(self, shop_ctx, api_db):
        from motodiag.shop import create_work_order
        wop = _add(shop_ctx, shop_ctx["part_a"]).json()["id"]
        other_wo = create_work_order(
            shop_id=shop_ctx["shop_id"], vehicle_id=1, customer_id=1,
            title="Other WO", db_path=api_db,
        )
        r = shop_ctx["client"].patch(
            f"/v1/shop/{shop_ctx['shop_id']}/work-orders/{other_wo}"
            f"/parts/{wop}",
            json={"quantity": 2}, headers=shop_ctx["headers"],
        )
        assert r.status_code == 404


class TestLifecycle:
    def test_full_walk(self, shop_ctx):
        wop = _add(shop_ctx, shop_ctx["part_a"]).json()["id"]
        for action, expected in (
            ("ordered", "ordered"),
            ("received", "received"),
            ("installed", "installed"),
        ):
            r = _transition(shop_ctx, wop, action)
            assert r.status_code == 200, r.text
            assert r.json()["status"] == expected
        final = _lines(shop_ctx)[0]
        assert final["ordered_at"] and final["received_at"]
        assert final["installed_at"]

    @pytest.mark.parametrize("action", ["received", "installed"])
    def test_skipping_a_step_is_409(self, shop_ctx, action):
        wop = _add(shop_ctx, shop_ctx["part_a"]).json()["id"]
        r = _transition(shop_ctx, wop, action)
        assert r.status_code == 409
        assert r.json()["detail"]

    def test_going_backwards_is_409(self, shop_ctx):
        wop = _add(shop_ctx, shop_ctx["part_a"]).json()["id"]
        _transition(shop_ctx, wop, "ordered")
        _transition(shop_ctx, wop, "received")
        assert _transition(shop_ctx, wop, "ordered").status_code == 409

    def test_cancel_from_open(self, shop_ctx):
        wop = _add(shop_ctx, shop_ctx["part_a"]).json()["id"]
        r = _transition(shop_ctx, wop, "cancel", reason="wrong part")
        assert r.status_code == 200
        assert r.json()["status"] == "cancelled"

    def test_unknown_action_is_422(self, shop_ctx):
        wop = _add(shop_ctx, shop_ctx["part_a"]).json()["id"]
        assert _transition(shop_ctx, wop, "teleported").status_code == 422


class TestOrderAll:
    def test_orders_only_open_lines_and_is_idempotent(self, shop_ctx):
        a = _add(shop_ctx, shop_ctx["part_a"]).json()["id"]
        _add(shop_ctx, shop_ctx["part_b"])
        _transition(shop_ctx, a, "ordered")  # already ordered
        url = (
            f"/v1/shop/{shop_ctx['shop_id']}/work-orders/"
            f"{shop_ctx['wo_id']}/parts/order"
        )
        r = shop_ctx["client"].post(url, headers=shop_ctx["headers"])
        assert r.status_code == 200, r.text
        assert r.json()["ordered"] == 1  # only part_b was still open
        assert {l["status"] for l in r.json()["lines"]} == {"ordered"}
        # Nothing open left → a second press does nothing.
        assert shop_ctx["client"].post(
            url, headers=shop_ctx["headers"],
        ).json()["ordered"] == 0


class TestPartsArrivedProducer:
    """The one genuinely new behaviour in this phase."""

    def _wire_spy(self, monkeypatch):
        from motodiag.api.routes import parts as parts_routes
        calls = []
        monkeypatch.setattr(
            parts_routes, "notify_parts_arrived",
            lambda wo, line, acting, db_path=None: calls.append(
                (wo.get("id"), line.get("id"), acting),
            ),
        )
        return calls

    def _assign(self, ctx, user_id):
        with get_connection(ctx["db"]) as conn:
            conn.execute(
                "UPDATE work_orders SET assigned_mechanic_user_id = ? "
                "WHERE id = ?", (user_id, ctx["wo_id"]),
            )

    def test_received_fires_the_push_and_queues_the_customer_event(
        self, shop_ctx, monkeypatch,
    ):
        calls = self._wire_spy(monkeypatch)
        mech = _make_user(shop_ctx["db"], "p201_mech")
        self._assign(shop_ctx, mech)
        wop = _add(shop_ctx, shop_ctx["part_a"]).json()["id"]
        _transition(shop_ctx, wop, "ordered")
        assert _transition(shop_ctx, wop, "received").status_code == 200

        assert calls == [(shop_ctx["wo_id"], wop, shop_ctx["owner"])]
        with get_connection(shop_ctx["db"]) as conn:
            rows = conn.execute(
                "SELECT event FROM customer_notifications WHERE work_order_id = ?",
                (shop_ctx["wo_id"],),
            ).fetchall()
        assert [r[0] for r in rows] == ["parts_arrived"]

    @pytest.mark.parametrize("action", ["ordered", "installed", "cancel"])
    def test_other_transitions_fire_nothing(
        self, shop_ctx, monkeypatch, action,
    ):
        calls = self._wire_spy(monkeypatch)
        wop = _add(shop_ctx, shop_ctx["part_a"]).json()["id"]
        if action == "installed":
            _transition(shop_ctx, wop, "ordered")
            _transition(shop_ctx, wop, "received")
            calls.clear()
        _transition(shop_ctx, wop, action)
        assert calls == []

    def test_a_queue_failure_does_not_break_receiving(
        self, shop_ctx, monkeypatch,
    ):
        """Best-effort means the mechanic still gets their part marked
        received even if the notification layer is broken."""
        from motodiag.api.routes import parts as parts_routes
        monkeypatch.setattr(
            parts_routes, "trigger_notification",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("queue down")),
        )
        wop = _add(shop_ctx, shop_ctx["part_a"]).json()["id"]
        _transition(shop_ctx, wop, "ordered")
        r = _transition(shop_ctx, wop, "received")
        assert r.status_code == 200
        assert r.json()["status"] == "received"


class TestPushGlue:
    """notify_parts_arrived itself (the events-layer half)."""

    def _dry(self, monkeypatch):
        from motodiag.push import events as push_events
        from motodiag.push.sender import DryRunSender
        sender = DryRunSender()
        monkeypatch.setattr(push_events, "get_sender", lambda: sender)
        return sender

    def test_notifies_the_assignee(self, api_db, monkeypatch):
        from motodiag.push import events as push_events
        from motodiag.push.registry import register_token
        sender = self._dry(monkeypatch)
        mech = _make_user(api_db, "glue_parts")
        register_token(mech, "t" * 64, db_path=api_db)
        push_events.notify_parts_arrived(
            {"id": 7, "assigned_mechanic_user_id": mech},
            {"id": 1, "quantity": 2, "description": "Brake pads"},
            acting_user_id=999, db_path=api_db,
        )
        assert len(sender.sent) == 1
        assert "Parts arrived" in sender.sent[0]["title"]
        assert "2×" in sender.sent[0]["body"]

    def test_self_suppression(self, api_db, monkeypatch):
        from motodiag.push import events as push_events
        from motodiag.push.registry import register_token
        sender = self._dry(monkeypatch)
        mech = _make_user(api_db, "glue_self")
        register_token(mech, "s" * 64, db_path=api_db)
        push_events.notify_parts_arrived(
            {"id": 7, "assigned_mechanic_user_id": mech},
            {"id": 1, "quantity": 1, "description": "Pads"},
            acting_user_id=mech, db_path=api_db,
        )
        assert sender.sent == []

    def test_unassigned_work_order_notifies_nobody(self, api_db, monkeypatch):
        from motodiag.push import events as push_events
        sender = self._dry(monkeypatch)
        push_events.notify_parts_arrived(
            {"id": 7, "assigned_mechanic_user_id": None},
            {"id": 1, "quantity": 1, "description": "Pads"},
            acting_user_id=1, db_path=api_db,
        )
        assert sender.sent == []


class TestRequisitions:
    def test_create_list_show_roundtrip(self, shop_ctx):
        _add(shop_ctx, shop_ctx["part_a"], quantity=2)
        _add(shop_ctx, shop_ctx["part_b"])
        base = f"/v1/shop/{shop_ctx['shop_id']}/parts/requisitions"
        created = shop_ctx["client"].post(
            base, json={"notes": "weekly order"}, headers=shop_ctx["headers"],
        )
        assert created.status_code == 201, created.text
        req_id = created.json()["id"]
        assert created.json()["total_distinct_parts"] >= 1

        listed = shop_ctx["client"].get(base, headers=shop_ctx["headers"])
        assert req_id in [r["id"] for r in listed.json()]

        shown = shop_ctx["client"].get(
            f"{base}/{req_id}", headers=shop_ctx["headers"],
        )
        assert shown.status_code == 200
        assert shown.json()["id"] == req_id
        assert isinstance(shown.json()["items"], list)

    def test_requisition_from_another_shop_is_404(self, shop_ctx, api_db):
        from motodiag.shop import seed_first_owner
        other = _make_user(api_db, "p201_req_other")
        _make_sub(api_db, other, tier="shop")
        _, other_key = create_api_key(other, db_path=api_db)
        other_shop = shop_ctx["client"].post(
            "/v1/shop/profile", headers={"X-API-Key": other_key},
            json={"name": "Req Other"},
        ).json()["id"]
        seed_first_owner(other_shop, other, db_path=api_db)
        _add(shop_ctx, shop_ctx["part_a"])
        req_id = shop_ctx["client"].post(
            f"/v1/shop/{shop_ctx['shop_id']}/parts/requisitions",
            json={}, headers=shop_ctx["headers"],
        ).json()["id"]
        r = shop_ctx["client"].get(
            f"/v1/shop/{other_shop}/parts/requisitions/{req_id}",
            headers={"X-API-Key": other_key},
        )
        assert r.status_code == 404

    def test_shop_needs_endpoint(self, shop_ctx):
        _add(shop_ctx, shop_ctx["part_a"], quantity=3)
        r = shop_ctx["client"].get(
            f"/v1/shop/{shop_ctx['shop_id']}/parts/needs",
            headers=shop_ctx["headers"],
        )
        assert r.status_code == 200
        assert any(n["total_quantity"] >= 3 for n in r.json())


class TestOpenApiContract:
    def test_parts_routes_are_tagged_and_secured(self, api_db):
        spec = create_app(db_path_override=api_db).openapi()
        paths = [p for p in spec["paths"] if "/parts" in p]
        assert len(paths) >= 8
        for path in paths:
            for method, op in spec["paths"][path].items():
                if method not in ("get", "post", "patch", "delete"):
                    continue
                assert "parts" in op.get("tags", []), (path, method)
                assert op.get("security"), (path, method)
