"""Phase 202 — mechanic time tracking.

Covers migration 047's database-enforced invariant, the repo lifecycle
(clock in / auto-close / clock out / cap sweep / adjust), the five
routes with their tier + membership + cross-shop gating, and the two
contracts this phase must not break: **manual actual_hours always wins**
and a WO with no entries still falls back to estimated_hours.

Gate 9's exact invoice scenario is re-asserted here on purpose. That
test lives in another file and could pass for the wrong reason once
auto-fill exists; pinning it beside the feature makes the coupling
visible to whoever changes this next.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from motodiag.api.app import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import SCHEMA_VERSION, get_connection, init_db
from motodiag.shop.time_entries import (
    NoOpenTimeEntryError,
    adjust_entry,
    clock_in,
    clock_out,
    close_stale_entries,
    get_open_entry_for_user,
    total_seconds_for_wo,
)


@pytest.fixture
def db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase202.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()
    yield path
    reset_settings()


def _user(db_path, username, sub_tier="shop"):
    with get_connection(db_path) as conn:
        uid = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES (?, ?, 'individual', 1)",
            (username, f"{username}@ex.com"),
        ).lastrowid
        if sub_tier:
            conn.execute(
                """INSERT INTO subscriptions (user_id, tier, status, current_period_end)
                   VALUES (?, ?, 'active', datetime('now', '+30 days'))""",
                (uid, sub_tier),
            )
    return uid


def _shop_with_wo(db_path, owner_id, title="Timer WO"):
    from motodiag.crm import customer_repo
    from motodiag.crm.models import Customer
    from motodiag.shop import create_shop, create_work_order, seed_first_owner
    shop_id = create_shop(name=f"Shop {title}", db_path=db_path)
    seed_first_owner(shop_id, owner_id, db_path=db_path)
    cust = customer_repo.create_customer(
        Customer(name="c", phone="555", email="c@ex.com"), db_path=db_path,
    )
    with get_connection(db_path) as conn:
        vid = conn.execute(
            "INSERT INTO vehicles (make, model, year, protocol) "
            "VALUES ('Honda', 'CB500', 2020, 'none')",
        ).lastrowid
    wo_id = create_work_order(
        shop_id=shop_id, vehicle_id=vid, customer_id=cust,
        title=title, db_path=db_path,
    )
    return shop_id, wo_id


def _wo_in_shop(db_path, shop_id, title="Second WO"):
    """Another work order in an EXISTING shop (not a new one) — the
    auto-close path is same-shop, and a cross-shop WO correctly 404s."""
    from motodiag.crm import customer_repo
    from motodiag.crm.models import Customer
    from motodiag.shop import create_work_order
    cust = customer_repo.create_customer(
        Customer(name="c2", phone="556", email="c2@ex.com"), db_path=db_path,
    )
    with get_connection(db_path) as conn:
        vid = conn.execute(
            "INSERT INTO vehicles (make, model, year, protocol) "
            "VALUES ('Yamaha', 'MT-07', 2021, 'none')",
        ).lastrowid
    return create_work_order(
        shop_id=shop_id, vehicle_id=vid, customer_id=cust,
        title=title, db_path=db_path,
    )


def _client(db_path):
    return TestClient(
        create_app(db_path_override=db_path), raise_server_exceptions=False,
    )


def _backdate(db_path, entry_id, hours):
    stamp = (
        datetime.now(timezone.utc) - timedelta(hours=hours)
    ).isoformat()
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE work_order_time_entries SET started_at = ? WHERE id = ?",
            (stamp, entry_id),
        )
    return stamp


class TestMigration047:
    def test_schema_version(self, db):
        assert SCHEMA_VERSION >= 47

    def test_table_shape(self, db):
        with get_connection(db) as conn:
            cols = {r[1] for r in conn.execute(
                "PRAGMA table_info(work_order_time_entries)",
            )}
        assert {
            "id", "work_order_id", "user_id", "started_at", "ended_at",
            "duration_seconds", "source", "needs_review", "note",
            "created_at", "updated_at",
        } <= cols

    def test_one_open_entry_per_mechanic_is_enforced_by_the_database(self, db):
        """The invariant must hold even when the app layer is bypassed —
        that is the whole reason it is a partial unique index."""
        owner = _user(db, "dbowner")
        _, wo = _shop_with_wo(db, owner)
        now = datetime.now(timezone.utc).isoformat()
        with get_connection(db) as conn:
            conn.execute(
                "INSERT INTO work_order_time_entries "
                "(work_order_id, user_id, started_at, source, created_at, updated_at) "
                "VALUES (?, ?, ?, 'timer', ?, ?)",
                (wo, owner, now, now, now),
            )
        with pytest.raises(Exception):
            with get_connection(db) as conn:
                conn.execute(
                    "INSERT INTO work_order_time_entries "
                    "(work_order_id, user_id, started_at, source, created_at, updated_at) "
                    "VALUES (?, ?, ?, 'timer', ?, ?)",
                    (wo, owner, now, now, now),
                )

    def test_closed_entries_do_not_block_a_new_one(self, db):
        owner = _user(db, "reopener")
        _, wo = _shop_with_wo(db, owner)
        clock_in(wo, owner, db_path=db)
        clock_out(owner, db_path=db)
        entry, auto = clock_in(wo, owner, db_path=db)
        assert entry["ended_at"] is None and auto is None


class TestRepoLifecycle:
    def test_clock_in_then_out_records_a_duration(self, db):
        owner = _user(db, "lifecycle")
        _, wo = _shop_with_wo(db, owner)
        entry, auto = clock_in(wo, owner, db_path=db)
        assert auto is None and entry["ended_at"] is None
        _backdate(db, entry["id"], hours=1.5)
        closed = clock_out(owner, db_path=db)
        assert closed["ended_at"] is not None
        assert 5350 <= closed["duration_seconds"] <= 5450  # ~1.5h

    def test_clocking_in_elsewhere_auto_closes_the_first(self, db):
        owner = _user(db, "switcher")
        _, wo_a = _shop_with_wo(db, owner, "A")
        _, wo_b = _shop_with_wo(db, owner, "B")
        first, _ = clock_in(wo_a, owner, db_path=db)
        _backdate(db, first["id"], hours=2)
        second, auto = clock_in(wo_b, owner, db_path=db)
        assert auto is not None
        assert auto["id"] == first["id"]
        assert auto["work_order_id"] == wo_a
        assert 7150 <= auto["duration_seconds"] <= 7250  # ~2h
        assert second["work_order_id"] == wo_b
        assert get_open_entry_for_user(owner, db_path=db)["id"] == second["id"]

    def test_two_mechanics_may_be_clocked_in_at_once(self, db):
        """The invariant is per-mechanic, not per-work-order."""
        owner = _user(db, "mech_a")
        other = _user(db, "mech_b")
        _, wo = _shop_with_wo(db, owner)
        clock_in(wo, owner, db_path=db)
        clock_in(wo, other, db_path=db)
        assert get_open_entry_for_user(owner, db_path=db) is not None
        assert get_open_entry_for_user(other, db_path=db) is not None

    def test_clock_out_with_nothing_running_raises(self, db):
        owner = _user(db, "nothing")
        with pytest.raises(NoOpenTimeEntryError):
            clock_out(owner, db_path=db)

    def test_clock_out_from_the_wrong_work_order_raises(self, db):
        """A stale screen must not stop a timer started somewhere else."""
        owner = _user(db, "stale")
        _, wo_a = _shop_with_wo(db, owner, "A")
        _, wo_b = _shop_with_wo(db, owner, "B")
        clock_in(wo_a, owner, db_path=db)
        with pytest.raises(NoOpenTimeEntryError):
            clock_out(owner, wo_id=wo_b, db_path=db)

    def test_open_entries_contribute_nothing_to_the_total(self, db):
        owner = _user(db, "openzero")
        _, wo = _shop_with_wo(db, owner)
        clock_in(wo, owner, db_path=db)
        assert total_seconds_for_wo(wo, db_path=db) == 0


class TestStaleCap:
    def test_closes_at_the_cap_not_at_discovery(self, db):
        """A forgotten timer must not bill the hours nobody worked."""
        owner = _user(db, "forgot")
        _, wo = _shop_with_wo(db, owner)
        entry, _ = clock_in(wo, owner, db_path=db)
        _backdate(db, entry["id"], hours=30)  # cap is 12
        closed = close_stale_entries(db_path=db)
        assert len(closed) == 1
        # 12h at the cap, NOT the 30h that elapsed.
        assert 12 * 3600 - 60 <= closed[0]["duration_seconds"] <= 12 * 3600 + 60
        assert closed[0]["needs_review"] == 1

    def test_a_fresh_entry_is_untouched(self, db):
        owner = _user(db, "fresh")
        _, wo = _shop_with_wo(db, owner)
        clock_in(wo, owner, db_path=db)
        assert close_stale_entries(db_path=db) == []

    def test_the_sweep_runs_lazily_on_clock_in(self, db):
        owner = _user(db, "lazysweep")
        _, wo = _shop_with_wo(db, owner)
        stale, _ = clock_in(wo, owner, db_path=db)
        _backdate(db, stale["id"], hours=30)
        fresh, auto = clock_in(wo, owner, db_path=db)
        # Swept and capped, so clock_in saw nothing open to auto-close.
        assert auto is None
        with get_connection(db) as conn:
            row = dict(conn.execute(
                "SELECT needs_review, duration_seconds FROM "
                "work_order_time_entries WHERE id = ?", (stale["id"],),
            ).fetchone())
        assert row["needs_review"] == 1
        assert row["duration_seconds"] <= 12 * 3600 + 60


class TestAdjust:
    def test_corrects_times_and_recomputes_duration(self, db):
        owner = _user(db, "adjuster")
        _, wo = _shop_with_wo(db, owner)
        entry, _ = clock_in(wo, owner, db_path=db)
        clock_out(owner, db_path=db)
        start = datetime(2026, 9, 4, 9, 0, tzinfo=timezone.utc)
        updated = adjust_entry(
            entry["id"],
            started_at=start.isoformat(),
            ended_at=(start + timedelta(hours=3)).isoformat(),
            note="corrected", needs_review=False, db_path=db,
        )
        assert updated["duration_seconds"] == 3 * 3600
        assert updated["source"] == "manual"
        assert updated["needs_review"] == 0

    def test_rejects_an_end_before_the_start(self, db):
        owner = _user(db, "typo")
        _, wo = _shop_with_wo(db, owner)
        entry, _ = clock_in(wo, owner, db_path=db)
        clock_out(owner, db_path=db)
        start = datetime(2026, 9, 4, 9, 0, tzinfo=timezone.utc)
        with pytest.raises(ValueError):
            adjust_entry(
                entry["id"], started_at=start.isoformat(),
                ended_at=(start - timedelta(hours=1)).isoformat(),
                db_path=db,
            )


class TestRoutes:
    def _setup(self, db, username="routeowner"):
        owner = _user(db, username)
        _, key = create_api_key(owner, db_path=db)
        shop_id, wo_id = _shop_with_wo(db, owner)
        return _client(db), key, owner, shop_id, wo_id

    def test_clock_in_out_roundtrip(self, db):
        client, key, _, shop_id, wo_id = self._setup(db)
        h = {"X-API-Key": key}
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/clock-in", headers=h,
        )
        assert r.status_code == 201, r.text
        assert r.json()["auto_closed"] is None
        assert r.json()["entry"]["ended_at"] is None

        mine = client.get(f"/v1/shop/{shop_id}/time-entries/mine/open", headers=h)
        assert mine.status_code == 200
        assert mine.json()["entry"]["work_order_id"] == wo_id

        out = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/clock-out", headers=h,
        )
        assert out.status_code == 200, out.text
        assert out.json()["ended_at"] is not None

        after = client.get(f"/v1/shop/{shop_id}/time-entries/mine/open", headers=h)
        assert after.json()["entry"] is None

    def test_clock_in_response_reports_what_it_auto_closed(self, db):
        """The UI cannot tell the mechanic where their time went unless
        the API says which entry it stopped."""
        client, key, owner, shop_id, wo_a = self._setup(db)
        wo_b = _wo_in_shop(db, shop_id, "B")
        h = {"X-API-Key": key}
        client.post(f"/v1/shop/{shop_id}/work-orders/{wo_a}/clock-in", headers=h)
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_b}/clock-in", headers=h,
        )
        assert r.status_code == 201, r.text
        assert r.json()["auto_closed"]["work_order_id"] == wo_a

    def test_clock_out_with_nothing_running_is_409(self, db):
        client, key, _, shop_id, wo_id = self._setup(db)
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/clock-out",
            headers={"X-API-Key": key},
        )
        assert r.status_code == 409, r.text

    def test_entries_list_reports_totals(self, db):
        client, key, owner, shop_id, wo_id = self._setup(db)
        h = {"X-API-Key": key}
        entry = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/clock-in", headers=h,
        ).json()["entry"]
        _backdate(db, entry["id"], hours=2)
        client.post(f"/v1/shop/{shop_id}/work-orders/{wo_id}/clock-out", headers=h)
        r = client.get(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/time-entries", headers=h,
        )
        assert r.status_code == 200
        assert len(r.json()["entries"]) == 1
        assert r.json()["total_hours"] == pytest.approx(2.0, abs=0.05)

    def test_requires_auth(self, db):
        client, _, _, shop_id, wo_id = self._setup(db)
        r = client.post(f"/v1/shop/{shop_id}/work-orders/{wo_id}/clock-in")
        assert r.status_code == 401

    def test_requires_shop_tier(self, db):
        client, _, _, shop_id, wo_id = self._setup(db)
        indie = _user(db, "indie", sub_tier="individual")
        _, indie_key = create_api_key(indie, db_path=db)
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/clock-in",
            headers={"X-API-Key": indie_key},
        )
        assert r.status_code == 402

    def test_non_member_is_403(self, db):
        client, _, _, shop_id, wo_id = self._setup(db)
        stranger = _user(db, "stranger")
        _, sk = create_api_key(stranger, db_path=db)
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/clock-in",
            headers={"X-API-Key": sk},
        )
        assert r.status_code == 403

    def test_other_shops_work_order_is_404(self, db):
        client, key, _, shop_id, _ = self._setup(db)
        other_owner = _user(db, "otherowner")
        _, other_wo = _shop_with_wo(db, other_owner, "Other")
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{other_wo}/clock-in",
            headers={"X-API-Key": key},
        )
        assert r.status_code == 404

    def test_mine_open_hides_an_entry_from_another_shop(self, db):
        client, key, owner, shop_id, _ = self._setup(db)
        other_shop, other_wo = _shop_with_wo(db, owner, "Elsewhere")
        h = {"X-API-Key": key}
        client.post(
            f"/v1/shop/{other_shop}/work-orders/{other_wo}/clock-in", headers=h,
        )
        r = client.get(f"/v1/shop/{shop_id}/time-entries/mine/open", headers=h)
        assert r.status_code == 200 and r.json()["entry"] is None

    def test_adjust_over_http(self, db):
        client, key, _, shop_id, wo_id = self._setup(db)
        h = {"X-API-Key": key}
        entry = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/clock-in", headers=h,
        ).json()["entry"]
        client.post(f"/v1/shop/{shop_id}/work-orders/{wo_id}/clock-out", headers=h)
        start = "2026-09-04T09:00:00+00:00"
        r = client.patch(
            f"/v1/shop/{shop_id}/time-entries/{entry['id']}", headers=h,
            json={"started_at": start, "ended_at": "2026-09-04T12:00:00+00:00",
                  "note": "fixed"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["duration_seconds"] == 3 * 3600


class TestActualHoursContract:
    """The two behaviours this phase must not break."""

    def _setup(self, db):
        owner = _user(db, "hoursowner")
        _, key = create_api_key(owner, db_path=db)
        shop_id, wo_id = _shop_with_wo(db, owner)
        client = _client(db)
        client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/transition",
            json={"action": "open"}, headers={"X-API-Key": key},
        )
        client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/transition",
            json={"action": "start"}, headers={"X-API-Key": key},
        )
        return client, key, shop_id, wo_id

    def test_manual_hours_always_win(self, db):
        client, key, shop_id, wo_id = self._setup(db)
        h = {"X-API-Key": key}
        entry = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/clock-in", headers=h,
        ).json()["entry"]
        _backdate(db, entry["id"], hours=8)  # tracked 8h...
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/transition",
            json={"action": "complete", "actual_hours": 2.0}, headers=h,
        )
        assert r.status_code == 200, r.text
        # ...but the supplied 2.0 wins. This is the Gate 9 contract.
        assert r.json()["actual_hours"] == pytest.approx(2.0)

    def test_auto_fills_from_the_ledger_when_nothing_supplied(self, db):
        client, key, shop_id, wo_id = self._setup(db)
        h = {"X-API-Key": key}
        entry = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/clock-in", headers=h,
        ).json()["entry"]
        _backdate(db, entry["id"], hours=3)
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/transition",
            json={"action": "complete"}, headers=h,
        )
        assert r.status_code == 200, r.text
        assert r.json()["actual_hours"] == pytest.approx(3.0, abs=0.05)

    def test_completing_closes_a_running_timer(self, db):
        client, key, shop_id, wo_id = self._setup(db)
        h = {"X-API-Key": key}
        client.post(f"/v1/shop/{shop_id}/work-orders/{wo_id}/clock-in", headers=h)
        client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/transition",
            json={"action": "complete"}, headers=h,
        )
        assert client.get(
            f"/v1/shop/{shop_id}/time-entries/mine/open", headers=h,
        ).json()["entry"] is None

    def test_a_work_order_with_no_entries_is_unchanged(self, db):
        """Pre-202 behaviour: no entries, nothing supplied → actual_hours
        stays None and invoicing still falls back to estimated_hours."""
        client, key, shop_id, wo_id = self._setup(db)
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/transition",
            json={"action": "complete"}, headers={"X-API-Key": key},
        )
        assert r.status_code == 200, r.text
        assert r.json().get("actual_hours") is None

    def test_gate9_invoice_scenario_still_holds(self, db):
        """Re-assert Gate 9's exact path beside the feature that could
        break it: complete with 2.0 hours → a 20000-cent labor line."""
        client, key, shop_id, wo_id = self._setup(db)
        h = {"X-API-Key": key}
        # Nine hours on the clock, deliberately contradicting the 2.0
        # the mechanic types — the timer must not win.
        entry = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/clock-in", headers=h,
        ).json()["entry"]
        _backdate(db, entry["id"], hours=9)
        client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/transition",
            json={"action": "complete", "actual_hours": 2.0}, headers=h,
        )
        # Same route and same assertion Gate 9 makes.
        r = client.post(
            f"/v1/shop/{shop_id}/invoices/generate", headers=h,
            json={"work_order_id": wo_id, "labor_hourly_rate_cents": 10000,
                  "tax_rate": 0.0},
        )
        assert r.status_code == 201, r.text
        assert r.json()["subtotal_cents"] == 20000  # 2h × $100, not 9h


class TestObservability:
    """The F52 lesson: a state change that leaves no trace is not
    verifiable in production, however green its test is."""

    def test_clock_in_and_out_log_at_info(self, db, caplog):
        owner = _user(db, "logger")
        _, wo = _shop_with_wo(db, owner)
        with caplog.at_level(logging.INFO, logger="motodiag.shop.time_entries"):
            clock_in(wo, owner, db_path=db)
            clock_out(owner, db_path=db)
        text = " ".join(r.message for r in caplog.records)
        assert "clock-in" in text and "clock-out" in text

    def test_auto_close_logs_at_info(self, db, caplog):
        owner = _user(db, "caplogger")
        _, wo = _shop_with_wo(db, owner)
        entry, _ = clock_in(wo, owner, db_path=db)
        _backdate(db, entry["id"], hours=30)
        with caplog.at_level(logging.INFO, logger="motodiag.shop.time_entries"):
            close_stale_entries(db_path=db)
        assert any("auto-closed stale" in r.message for r in caplog.records)


class TestOpenApiContract:
    def test_tag_catalog_carries_time_tracking(self, db):
        spec = create_app(db_path_override=db).openapi()
        assert any(t["name"] == "time-tracking" for t in spec["tags"])
        op = spec["paths"][
            "/v1/shop/{shop_id}/work-orders/{wo_id}/clock-in"
        ]["post"]
        assert op["tags"] == ["time-tracking"]
        assert op.get("security")  # authed, unlike the Phase 200 share page
