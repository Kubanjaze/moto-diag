"""Phase 377 — F186 and F191: the shop's times stored in UTC, compared parsed.

Until 377 the shop's writers stamped naive local time, ``--since`` built a
local cutoff in the ``T`` shape against UTC stamps in SQLite's space shape
(F191), and analytics compared a UTC cutoff with local completions (F186).
Every test here runs on Phase 370's frozen clock in New York, at two moments:

- the evening of 2026-10-06, 23:26:39 EDT (2026-10-07 03:26:39 UTC), where
  the local date and the UTC date differ;
- midday on 2026-10-15, 12:00 EDT (16:00 UTC), where they agree and the
  separator alone decided the old comparison.

"Local" is the server's zone, because a shop records no time zone (F192).
The planted return to local time is ``377_mutate.py``'s first mutation.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from motodiag.core.database import get_connection, init_db
from motodiag.core.migrations import (
    apply_pending_migrations, get_migration_by_version, rollback_to_version,
)
from motodiag.core.timestamps import (
    SHOP_TIME_FIELDS_082,
    convert_shop_times_082,
    local_day,
    local_day_start,
    local_display,
    stored_instant,
    utc_cutoff,
    with_utc_times,
)
from motodiag.shop import analytics, intake_repo, issue_repo
from motodiag.shop import work_order_repo as wor
from support.frozen_clock import CLOCKED, frozen_datetime, set_zone
from support.phase274 import ok, seed_bike, seed_customer, seed_shop, sql

REPO = Path(__file__).resolve().parent.parent
ZONE = "America/New_York"
EVENING = datetime(2026, 10, 7, 3, 26, 39, tzinfo=timezone.utc)   # 2026-10-06 23:26:39 EDT
MIDDAY = datetime(2026, 10, 15, 16, 0, tzinfo=timezone.utc)       # 2026-10-15 12:00 EDT
MIDDAY_STORED = "2026-10-15T16:00:00.000+00:00"
STORED = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}\+00:00$")
# Modules that read the clock themselves, beside the two 370 freezes:
# intake_at (374's own stamp) and an invoice's issued_at.
ALSO_CLOCKED = ("motodiag.shop.intake_repo", "motodiag.shop.invoicing")


@pytest.fixture
def clock(monkeypatch):
    """Freeze the clock at ``MIDDAY`` in New York; ``clock(instant)`` moves it.
    TZ is restored, and tzset called, afterwards."""
    previous = os.environ.get("TZ")
    set_zone(ZONE)

    def at(instant: datetime) -> None:
        frozen = frozen_datetime(instant)
        for name in CLOCKED + ALSO_CLOCKED:
            monkeypatch.setattr(f"{name}.datetime", frozen)

    at(MIDDAY)
    yield at
    monkeypatch.undo()
    set_zone(previous)


@pytest.fixture
def shop(clock, tmp_path):
    """A shop, a customer and a bike, made at ``MIDDAY``."""
    db = str(tmp_path / "phase377.db")
    init_db(db)
    shop_id = seed_shop(db)
    return db, shop_id, seed_customer(db, shop_id, "Ann"), seed_bike(db)


def sqlite_utc(instant: datetime) -> str:
    """What SQLite's ``CURRENT_TIMESTAMP`` writes at ``instant``."""
    return instant.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def new_work_order(db, shop_id, customer_id, bike_id, title="job", **kw) -> int:
    return wor.create_work_order(shop_id, bike_id, customer_id, title, db_path=db, **kw)


# --- F191: --since 30m includes the last minute and excludes three hours ago ---


@pytest.mark.parametrize("now", [EVENING, MIDDAY], ids=["evening", "midday"])
class TestSince30m:

    def test_intakes_listed_and_counted(self, clock, shop, now):
        db, s, c, b = shop
        clock(now - timedelta(hours=3))
        old = intake_repo.create_intake(s, c, b, db_path=db)
        clock(now - timedelta(minutes=1))
        new = intake_repo.create_intake(s, c, b, db_path=db)
        clock(now)
        listed = intake_repo.list_intakes(shop_id=s, since="30m", db_path=db)
        assert [r["id"] for r in listed] == [new], f"three hours ago is {old}"
        assert intake_repo.count_intakes(shop_id=s, since="30m", db_path=db) == 1

    def test_intake_list_command(self, clock, shop, now):
        db, s, c, b = shop
        clock(now - timedelta(hours=3))
        intake_repo.create_intake(s, c, b, db_path=db)
        clock(now - timedelta(minutes=1))
        new = intake_repo.create_intake(s, c, b, db_path=db)
        clock(now)
        out = ok(db, "shop", "intake", "list", "--since", "30m", "--json")
        assert [r["id"] for r in json.loads(out)] == [new]

    def test_work_orders(self, clock, shop, now):
        db, s, c, b = shop
        old, new = new_work_order(db, s, c, b, "old"), new_work_order(db, s, c, b, "new")
        # created_at is the column's CURRENT_TIMESTAMP, which the frozen
        # clock does not reach; write what it would have written then.
        sql(db, "UPDATE work_orders SET created_at = ? WHERE id = ?",
            (sqlite_utc(now - timedelta(hours=3)), old))
        sql(db, "UPDATE work_orders SET created_at = ? WHERE id = ?",
            (sqlite_utc(now - timedelta(minutes=1)), new))
        clock(now)
        listed = wor.list_work_orders(shop_id=s, since="30m", db_path=db)
        assert [r["id"] for r in listed] == [new]

    def test_issues(self, clock, shop, now):
        db, s, c, b = shop
        w = new_work_order(db, s, c, b)
        old = issue_repo.create_issue(w, "old", db_path=db)
        new = issue_repo.create_issue(w, "new", db_path=db)
        sql(db, "UPDATE issues SET reported_at = ? WHERE id = ?",
            (sqlite_utc(now - timedelta(hours=3)), old))
        sql(db, "UPDATE issues SET reported_at = ? WHERE id = ?",
            (sqlite_utc(now - timedelta(minutes=1)), new))
        clock(now)
        listed = issue_repo.list_issues(shop_id=s, since="30m", db_path=db)
        assert [r["id"] for r in listed] == [new]


# --- F186: a window's first day, and the shop's day ---


def completed_work_order(clock, db, s, c, b, done: datetime, hours_open: float = 2.0,
                         actual_hours: float | None = None) -> int:
    """A work order opened ``hours_open`` before ``done`` and completed then."""
    clock(done - timedelta(hours=hours_open))
    w = new_work_order(db, s, c, b, f"done {done.isoformat()}", estimated_hours=1.0)
    wor.open_work_order(w, db_path=db)
    wor.start_work(w, db_path=db)
    clock(done)
    wor.complete_work_order(w, actual_hours=actual_hours, db_path=db)
    return w


def add_labour_estimate(db, wo_id: int, hours: float) -> None:
    sql(db, "INSERT INTO labor_estimates (wo_id, base_hours, adjusted_hours, "
            "confidence, rationale, ai_model) VALUES (?, ?, ?, 0.9, 'test', 'test')",
        (wo_id, hours, hours))


class TestWindowFirstDay:
    """At 2026-10-15 12:00 EDT a 30-day window starts 2026-09-15 12:00 EDT."""

    def test_before_the_cutoff_on_its_day_is_out(self, clock, shop):
        db, s, c, b = shop
        for hour_utc in (13, 17):          # 09:00 EDT (out), 13:00 EDT (in)
            w = completed_work_order(clock, db, s, c, b,
                                     datetime(2026, 9, 15, hour_utc, tzinfo=timezone.utc),
                                     actual_hours=1.0)
            add_labour_estimate(db, w, 1.0)
        clock(MIDDAY)
        assert analytics.throughput(s, since="30d", db_path=db).completed_total == 1
        turn = analytics.turnaround(s, since="30d", db_path=db)
        assert (turn.sample_size, turn.mean_hours) == (1, 2.0)
        assert analytics.labor_accuracy(s, since="30d", db_path=db).sample_size == 1

    def test_completions_are_grouped_by_the_shops_day(self, clock, shop):
        db, s, c, b = shop
        # 2026-10-14 22:00 EDT is 2026-10-15 02:00 UTC.
        completed_work_order(clock, db, s, c, b,
                             datetime(2026, 10, 15, 2, 0, tzinfo=timezone.utc))
        clock(MIDDAY)
        days = analytics.throughput(s, since="7d", db_path=db).completions_by_day
        assert [(d.date, d.count) for d in days] == [("2026-10-14", 1)]

    def test_a_typed_date_is_the_shops_day(self, clock, shop):
        db, s, c, b = shop
        # 2026-10-14 23:30 EDT is the 14th in the shop, the 15th in UTC.
        completed_work_order(clock, db, s, c, b,
                             datetime(2026, 10, 15, 3, 30, tzinfo=timezone.utc))
        clock(MIDDAY)
        assert analytics.throughput(s, since="2026-10-15", db_path=db).completed_total == 0
        assert analytics.throughput(s, since="2026-10-14", db_path=db).completed_total == 1


class TestTheShopsMonth:
    """An invoice issued 2026-10-31 21:00 EDT (2026-11-01 01:00 UTC) is October's."""

    @pytest.fixture
    def october_invoice(self, clock, shop):
        from motodiag.shop.invoicing import generate_invoice_for_wo
        from support.tax_on_record import record_tax
        db, s, c, b = shop
        record_tax(db, s)
        late = datetime(2026, 11, 1, 1, 0, tzinfo=timezone.utc)
        w = completed_work_order(clock, db, s, c, b, late - timedelta(hours=1),
                                 actual_hours=1.0)
        clock(late)
        inv = generate_invoice_for_wo(w, labor_hourly_rate_cents=10000, db_path=db)
        return db, s, inv

    def test_the_p_and_l(self, october_invoice):
        db, s, _ = october_invoice
        october = analytics.financial_report(s, period="month", period_key="2026-10", db_path=db)
        november = analytics.financial_report(s, period="month", period_key="2026-11", db_path=db)
        assert sum(g.work_orders for g in october.groups) == 1
        assert sum(g.work_orders for g in november.groups) == 0

    def test_the_accounting_export(self, october_invoice):
        from motodiag.accounting.export import _us_date, invoices_in_range
        db, s, inv = october_invoice
        rows, _ = invoices_in_range(s, "2026-10-01", "2026-10-31", "quickbooks_online", db_path=db)
        assert [r["id"] for r in rows] == [inv]
        assert invoices_in_range(s, "2026-11-01", "2026-11-30", "quickbooks_online", db_path=db)[0] == []
        assert _us_date(rows[0]["issued_at"]) == "10/31/2026"
        assert _us_date("2026-10-31") == "10/31/2026"   # a bare date stays as written


# --- Every writer stamps the stored format ---


def test_every_writer_stamps_the_stored_format(clock, shop):
    from motodiag.auth.models import User
    from motodiag.auth.users_repo import create_user
    from motodiag.core.models import VehicleBase
    from motodiag.crm import customer_bikes_repo, customer_repo
    from motodiag.knowledge.issues_repo import add_known_issue
    from motodiag.pricing import repair_plan
    from motodiag.shop.shop_repo import update_shop
    from motodiag.vehicles.registry import add_vehicle, update_vehicle
    from motodiag.workflows.models import WorkflowCategory, WorkflowTemplate
    from motodiag.workflows.template_repo import create_template, update_template

    db, s, c, _ = shop
    bike = add_vehicle(VehicleBase(make="Honda", model="CB500F", year=2020), db_path=db)
    update_vehicle(bike, {"notes": "n"}, db_path=db)
    customer_repo.update_customer(c, {"notes": "n"}, db_path=db)
    customer_bikes_repo.link_customer_bike(c, bike, db_path=db)
    update_shop(s, {"phone": "555"}, db_path=db)
    user = create_user(User(username="mech"), db_path=db)
    known = add_known_issue("t", "d", db_path=db)
    plan = repair_plan.create_plan("p", vehicle_id=bike, db_path=db)
    repair_plan.update_plan(plan, {"status": "approved"}, db_path=db)
    template = create_template(WorkflowTemplate(slug="s377", name="n",
                                                category=WorkflowCategory.PPI), db_path=db)
    update_template(template, {"name": "m"}, db_path=db)
    intake = intake_repo.create_intake(s, c, bike, db_path=db)
    intake_repo.update_intake(intake, {"mileage_at_intake": 1}, db_path=db)
    intake_repo.close_intake(intake, db_path=db)
    w = completed_work_order(clock, db, s, c, bike, MIDDAY, hours_open=0)
    issue = issue_repo.create_issue(w, "i", db_path=db)
    issue_repo.resolve_issue(issue, db_path=db)

    def stamp(table, column, where="id = ?", key=None):
        return sql(db, f"SELECT {column} FROM {table} WHERE {where}", (key,))[0][0]

    stamped = {
        ("vehicles", "created_at"): stamp("vehicles", "created_at", key=bike),
        ("vehicles", "updated_at"): stamp("vehicles", "updated_at", key=bike),
        ("customers", "created_at"): stamp("customers", "created_at", key=c),
        ("customers", "updated_at"): stamp("customers", "updated_at", key=c),
        ("customer_bikes", "assigned_at"): stamp("customer_bikes", "assigned_at",
                                                 "vehicle_id = ?", bike),
        ("shops", "updated_at"): stamp("shops", "updated_at", key=s),
        ("users", "created_at"): stamp("users", "created_at", key=user),
        ("known_issues", "created_at"): stamp("known_issues", "created_at", key=known),
        ("repair_plans", "created_at"): stamp("repair_plans", "created_at", key=plan),
        ("repair_plans", "updated_at"): stamp("repair_plans", "updated_at", key=plan),
        ("repair_plans", "approved_at"): stamp("repair_plans", "approved_at", key=plan),
        ("workflow_templates", "created_at"): stamp("workflow_templates", "created_at", key=template),
        ("workflow_templates", "updated_at"): stamp("workflow_templates", "updated_at", key=template),
        ("intake_visits", "updated_at"): stamp("intake_visits", "updated_at", key=intake),
        ("intake_visits", "closed_at"): stamp("intake_visits", "closed_at", key=intake),
        ("issues", "resolved_at"): stamp("issues", "resolved_at", key=issue),
        ("issues", "updated_at"): stamp("issues", "updated_at", key=issue),
    }
    for column in ("opened_at", "started_at", "completed_at", "closed_at", "updated_at"):
        stamped[("work_orders", column)] = stamp("work_orders", column, key=w)
    wrong = {k: v for k, v in stamped.items() if v != MIDDAY_STORED}
    assert wrong == {}


def test_a_booking_change_stamps_updated_at_in_utc(clock, tmp_path):
    from support.phase275 import new_db, seed_booking_shop

    monday = "2026-10-19"   # after the frozen clock's date; the shop opens Mondays
    db = new_db(tmp_path)
    seed = seed_booking_shop(db)
    ok(db, "shop", "appointment", "book", "--shop", seed["shop"],
       "--customer", seed["dana"], "--bike", seed["bike1"],
       "--start", f"{monday}T10:00", "--minutes", "60", "--mechanic", seed["alex"])
    appt = sql(db, "SELECT id FROM appointments")[0][0]
    ok(db, "shop", "appointment", "confirm", appt, "--channel", "phone")
    updated, start = sql(db, "SELECT updated_at, scheduled_start FROM appointments")[0]
    assert updated == MIDDAY_STORED
    assert start == f"{monday}T10:00"   # the shop's clock, by 275's rule


# --- Turnaround never drops a work order in silence (the operator's condition) ---


class TestTurnaroundFailsLoudly:

    def test_a_legacy_local_opened_at_with_a_new_completed_at_counts(self, clock, shop):
        db, s, c, b = shop
        w = completed_work_order(clock, db, s, c, b, MIDDAY)
        # Written before 377: naive local, two hours before completion.
        sql(db, "UPDATE work_orders SET opened_at = '2026-10-15T10:00:00.123456' WHERE id = ?", (w,))
        turn = analytics.turnaround(s, since="30d", db_path=db)
        assert (turn.sample_size, turn.mean_hours) == (1, 2.0)
        mech = analytics.mechanic_performance(s, since="30d", db_path=db)
        assert [m.avg_turnaround_hours for m in mech] == [2.0]

    @pytest.mark.parametrize("rollup", ["turnaround", "mechanic_performance"])
    def test_a_value_that_is_not_a_time_raises_naming_the_work_order(self, clock, shop, rollup):
        db, s, c, b = shop
        w = completed_work_order(clock, db, s, c, b, MIDDAY)
        sql(db, "UPDATE work_orders SET opened_at = 'yesterday' WHERE id = ?", (w,))
        with pytest.raises(ValueError, match=f"work order {w}"):
            getattr(analytics, rollup)(s, since="30d", db_path=db)


# --- Readers show local time; the API sends the stored format ---


class TestReaders:

    def test_the_cli_shows_local_time(self, clock, shop):
        db, s, c, b = shop
        w = completed_work_order(clock, db, s, c, b, MIDDAY, hours_open=1)
        intake = intake_repo.create_intake(s, c, b, db_path=db)
        issue = issue_repo.create_issue(w, "i", db_path=db)
        sql(db, "UPDATE issues SET reported_at = ? WHERE id = ?", (sqlite_utc(MIDDAY), issue))
        issue_repo.resolve_issue(issue, db_path=db)
        shown = ok(db, "shop", "work-order", "show", w)
        assert "Opened:    2026-10-15T11:00:00" in shown
        assert "Completed: 2026-10-15T12:00:00" in shown
        assert "Intake at: 2026-10-15T12:00:00" in ok(db, "shop", "intake", "show", intake)
        listed = ok(db, "shop", "intake", "list")
        assert "2026-10-15T12:00:00" in listed and "16:00:00" not in listed
        issue_shown = ok(db, "shop", "issue", "show", issue)
        assert "Reported: 2026-10-15T12:00:00" in issue_shown
        assert "Resolved: 2026-10-15T12:00:00" in issue_shown

    def test_the_work_order_report_shows_the_intake_in_local_time(self, clock, shop):
        from motodiag.reporting.builders import build_work_order_report_doc
        from support.phase275 import seed_member
        db, s, c, b = shop
        member = seed_member(db, s, "alex")
        intake = intake_repo.create_intake(s, c, b, db_path=db)
        w = new_work_order(db, s, c, b, intake_visit_id=intake)
        doc = build_work_order_report_doc(w, member, db_path=db)
        header = next(sec for sec in doc["sections"] if sec["heading"] == "Work order")
        assert dict(header["rows"])["Intake"] == "2026-10-15T12:00:00"

    def test_the_api_sends_the_stored_format(self, clock, shop):
        from fastapi.testclient import TestClient

        from motodiag.api import create_app
        from motodiag.auth.api_key_repo import create_api_key
        from motodiag.core.config import reset_settings
        from motodiag.shop import seed_first_owner

        db, s, c, b = shop
        w = completed_work_order(clock, db, s, c, b, MIDDAY, hours_open=1)
        sql(db, "UPDATE work_orders SET created_at = ? WHERE id = ?",
            (sqlite_utc(MIDDAY - timedelta(hours=1)), w))
        with get_connection(db) as conn:
            owner = conn.execute("INSERT INTO users (username, tier, is_active) "
                                 "VALUES ('owner', 'individual', 1)").lastrowid
            conn.execute("INSERT INTO subscriptions (user_id, tier, status, current_period_end) "
                          "VALUES (?, 'shop', 'active', datetime('now', '+30 days'))", (owner,))
        _, key = create_api_key(owner, db_path=db)
        seed_first_owner(s, owner, db_path=db)
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("MOTODIAG_DB_PATH", db)
            reset_settings()
            try:
                client = TestClient(create_app())
                got = client.get(f"/v1/shop/{s}/work-orders/{w}", headers={"X-API-Key": key})
                listed = client.get(f"/v1/shop/{s}/work-orders?status=completed",
                                    headers={"X-API-Key": key})
            finally:
                reset_settings()
        assert got.status_code == 200, got.text
        body = got.json()
        assert body["created_at"] == "2026-10-15T15:00:00.000+00:00"   # was 'YYYY-MM-DD HH:MM:SS'
        assert body["opened_at"] == "2026-10-15T15:00:00.000+00:00"
        assert body["completed_at"] == MIDDAY_STORED
        assert listed.json()["items"][0]["created_at"] == "2026-10-15T15:00:00.000+00:00"

    def test_a_vehicle_response_sends_the_stored_format(self):
        from motodiag.api.routes.vehicles import _row_to_response
        row = {"id": 1, "make": "Honda", "model": "CB", "year": 2020,
               "created_at": "2026-10-15 16:00:00", "updated_at": None}
        response = _row_to_response(row)
        assert (response.created_at, response.updated_at) == (MIDDAY_STORED, None)


# --- The helpers ---


class TestHelpers:

    def test_utc_cutoff(self, clock):
        assert utc_cutoff(None) is None and utc_cutoff("  ") is None
        assert utc_cutoff("30m") == "2026-10-15 15:30:00"
        assert utc_cutoff("3h") == "2026-10-15 13:00:00"
        assert utc_cutoff("1d") == "2026-10-14 16:00:00"
        assert utc_cutoff("2026-10-15") == "2026-10-15 04:00:00"              # the shop's midnight
        assert utc_cutoff("2026-10-15T09:00") == "2026-10-15 13:00:00"
        assert utc_cutoff("2026-10-15T09:00:00-07:00") == "2026-10-15 16:00:00"
        assert utc_cutoff("2026-10-15T16:00:00Z") == "2026-10-15 16:00:00"
        assert utc_cutoff(datetime(2026, 10, 15, 9, 0)) == "2026-10-15 13:00:00"
        with pytest.raises(ValueError):
            utc_cutoff("last week")

    def test_local_day_start_follows_daylight_saving(self, clock):
        assert local_day_start("2026-10-15") == "2026-10-15 04:00:00"   # EDT
        assert local_day_start("2026-11-02") == "2026-11-02 05:00:00"   # EST

    def test_the_rule_for_a_stored_value(self, clock):
        utc = timezone.utc
        assert stored_instant("2026-10-15T12:00:00.5") == datetime(2026, 10, 15, 16, 0, 0, 500000, utc)
        assert stored_instant("2026-10-15 16:00:00") == datetime(2026, 10, 15, 16, 0, tzinfo=utc)
        assert stored_instant(MIDDAY_STORED) == MIDDAY
        assert stored_instant("2026-10-15T16:00:00Z") == MIDDAY
        with pytest.raises(ValueError):
            stored_instant("yesterday")
        assert local_day("2026-10-15 03:30:00") == "2026-10-14"

    def test_local_display(self, clock):
        assert local_display(MIDDAY_STORED) == "2026-10-15T12:00:00"
        assert local_display("2026-10-15 16:00:00") == "2026-10-15T12:00:00"   # SQLite's UTC
        assert local_display("2026-10-15T12:00:00.123456") == "2026-10-15T12:00:00.123456"
        assert local_display("2026-10-15") == "2026-10-15"
        assert local_display(None) is None and local_display("n/a") == "n/a"

    def test_with_utc_times(self, clock):
        row = {"id": 1, "created_at": "2026-10-15 16:00:00", "opened_at": "2026-10-15T12:00:00",
               "closed_at": None, "close_reason": "x", "seen_at": "not a time"}
        assert with_utc_times(row) == {
            "id": 1, "created_at": MIDDAY_STORED, "opened_at": MIDDAY_STORED,
            "closed_at": None, "close_reason": "x", "seen_at": "not a time"}
        assert with_utc_times(None) is None


# --- Migration 082 ---


def test_migration_082_converts_naive_local_and_nothing_else(clock, tmp_path):
    db = str(tmp_path / "m082.db")
    init_db(db)
    rollback_to_version(81, db)
    s = seed_shop(db)
    c = seed_customer(db, s, "Ann")
    b = seed_bike(db)
    w = new_work_order(db, s, c, b)
    sql(db, "UPDATE work_orders SET opened_at = '2026-09-04T15:35:46.883930', "
            "created_at = '2026-09-04 19:31:22', started_at = NULL WHERE id = ?", (w,))
    sql(db, "UPDATE customers SET created_at = '2026-09-04T15:31:22.467670' WHERE id = ?", (c,))
    sql(db, "INSERT INTO known_issues (title, description, created_at) "
            "VALUES ('k', 'd', '2026-07-01T20:27:21.863235')")
    apply_pending_migrations(db)

    row = sql(db, "SELECT opened_at, created_at, started_at FROM work_orders WHERE id = ?", (w,))[0]
    assert row == ("2026-09-04T19:35:46.883+00:00", "2026-09-04 19:31:22", None)
    assert sql(db, "SELECT created_at FROM customers WHERE id = ?", (c,))[0][0] == \
        "2026-09-04T19:31:22.467+00:00"
    assert sql(db, "SELECT created_at FROM known_issues WHERE title = 'k'")[0][0] == \
        "2026-07-01T20:27:21.863235"                                     # 2A: left
    with sqlite3.connect(db) as conn:
        assert convert_shop_times_082(conn) == 0                          # idempotent

    rollback_to_version(81, db)
    assert sql(db, "SELECT opened_at FROM work_orders WHERE id = ?", (w,))[0][0] == \
        "2026-09-04T15:35:46.883"


def test_migration_082_names_every_stamped_column():
    """Its fields are the columns this phase's writers stamp, known_issues
    excepted (2A), and its rollback touches each one."""
    migration = get_migration_by_version(82)
    assert migration.post_apply == "motodiag.core.timestamps:convert_shop_times_082"
    assert "known_issues" not in SHOP_TIME_FIELDS_082
    assert SHOP_TIME_FIELDS_082["appointments"] == ("updated_at",)
    for table, columns in SHOP_TIME_FIELDS_082.items():
        for column in columns:
            assert f"UPDATE {table} SET {column} =" in migration.rollback_sql


# --- The census: no unzoned clock, no comparison as text ---


UNZONED = re.compile(r"datetime\.now\(\)")
UNZONED_PINNED = {
    # Phase 275's rule: an appointment's times are the shop's clock.
    ("scheduling/booking.py", "actual_end=_stored(datetime.now()))"),
    ("scheduling/booking.py", "actual_start=_stored(datetime.now()))"),
    ("scheduling/appointment_repo.py", "from_iso = datetime.now().isoformat()"),
    ("scheduling/appointment_repo.py", '"actual_end": actual_end or datetime.now().isoformat(),'),
    # Prose naming the old stamp: a docstring, and migration 079's description.
    ("core/timestamps.py", "old ``datetime.now().isoformat()``); one with a space is SQLite's"),
    ("core/migrations.py",
     '"`closed_at` with naive local `datetime.now().isoformat()` while "'),
    ("core/migrations.py",  # and 082's
     '"stamped naive local `datetime.now().isoformat()`, and cutoffs "'),
}
# Files whose shop-time comparisons Phase 377 parses.
PARSED_FILES = (
    "shop/intake_repo.py", "shop/work_order_repo.py", "shop/issue_repo.py",
    "shop/analytics.py", "shop/invoicing.py", "accounting/export.py",
    "shop/parts_sourcing.py", "shop/labor_estimator.py", "shop/workflow_rules.py",
    "shop/parts_needs.py", "shop/notifications.py", "shop/priority_scorer.py",
    "feedback/learning_hook.py",
)
TEXT_COMPARISON = re.compile(r"\b\w+_(at|start|end)\)?\s*(>=|<=|<|>)\s*\?")


def unzoned_clock_calls(root: Path) -> set[tuple[str, str]]:
    """Code lines calling ``datetime.now()`` with no zone, by F186's rule."""
    found = set()
    for path in sorted(root.rglob("*.py")):
        for line in path.read_text().splitlines():
            text = line.strip()
            if (UNZONED.search(text)
                    and not re.search(r"timezone|\.year|strftime|date\(\)", text)):
                found.add((path.relative_to(root).as_posix(), text))
    return found


def text_comparisons(root: Path) -> list[str]:
    """Time-column comparisons in ``PARSED_FILES`` not wrapped in ``datetime()``."""
    return [f"{name}: {line.strip()}" for name in PARSED_FILES
            for line in (root / name).read_text().splitlines()
            if TEXT_COMPARISON.search(line) and "datetime(" not in line]


def test_no_unzoned_clock_outside_the_pinned_four():
    assert unzoned_clock_calls(REPO / "src" / "motodiag") == UNZONED_PINNED


def test_no_shop_time_is_compared_as_text():
    assert text_comparisons(REPO / "src" / "motodiag") == []


def test_the_census_sees_a_planted_line(tmp_path):
    root = tmp_path / "motodiag"
    for name in PARSED_FILES:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text("")
    (root / "shop" / "analytics.py").write_text(
        'conditions.append("wo.completed_at >= ?")\n'
        "    now = datetime.now().isoformat()\n")
    assert unzoned_clock_calls(root) == {("shop/analytics.py", "now = datetime.now().isoformat()")}
    assert text_comparisons(root) == ['shop/analytics.py: conditions.append("wo.completed_at >= ?")']
