"""Phase 274 — row 290, financial reporting: a gross-margin P&L on recorded costs.

The operator's option B. Revenue comes from invoices the real `shop invoice
generate` writes; costs are recorded through `shop member cost-rate`, `shop
parts-needs cost` and `shop expense add`; the report is `shop analytics pnl`.
Each attribution rule is the operator's words, checked on figures worked out
by hand in the fixture's docstring.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from support.phase274 import (
    new_db, ok, refused, seed_bike, seed_customer, seed_shop, seed_user, sql,
)

MONTH = datetime.now(timezone.utc).strftime("%Y-%m")
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _wo(db, customer, bike, mech, hours, title):
    sql(db, "INSERT INTO work_orders (shop_id, vehicle_id, customer_id, title, status, "
            "actual_hours, assigned_mechanic_user_id, opened_at, completed_at) VALUES "
            "(1, ?, ?, ?, 'completed', ?, ?, ?, ?)",
        (bike, customer, title, hours, mech, f"{TODAY}T08:00:00", f"{TODAY}T17:00:00"))
    return sql(db, "SELECT MAX(id) FROM work_orders")[0][0]


def _part_line(db, wo, qty, billed_cents):
    sql(db, "INSERT INTO parts (slug, brand, description, category, make, model_pattern, "
            "typical_cost_cents) VALUES (?, 'OEM', 'Part', 'engine', 'Honda', '%', ?)",
        (f"p-{wo}-{qty}-{billed_cents}", billed_cents))
    part = sql(db, "SELECT MAX(id) FROM parts")[0][0]
    sql(db, "INSERT INTO work_order_parts (work_order_id, part_id, quantity, status) "
            "VALUES (?, ?, ?, 'installed')", (wo, part, qty))
    return sql(db, "SELECT MAX(id) FROM work_order_parts")[0][0]


def _time(db, wo, user, seconds):
    sql(db, "INSERT INTO work_order_time_entries (work_order_id, user_id, started_at, "
            "ended_at, duration_seconds, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, 'x', 'x')",
        (wo, user, f"{TODAY}T09:00:00+00:00", f"{TODAY}T10:00:00+00:00", seconds))


def _slot(db, bay, wo, start_h, end_h):
    sql(db, "INSERT INTO bay_schedule_slots (bay_id, work_order_id, scheduled_start, "
            "scheduled_end, status) VALUES (?, ?, ?, ?, 'completed')",
        (bay, wo, f"{TODAY}T{start_h:02d}:00:00", f"{TODAY}T{end_h:02d}:00:00"))


@pytest.fixture
def fixture_db(tmp_path):
    """Two mechanics, two customers, two bays, three invoiced work orders.

    WO1: Ana, customer Dana; 2.0 h billed at $100/h, one part billed $50
         (bought $30); Ana logged 2 h at $40/h.  Revenue 250, costs 30 + 80.
         Slots: 3 h in Lift A, 1 h in Lift B.
    WO2: Ben, customer Sam; 1.0 h billed, two parts billed $20 each (bought
         $12 each); Ben logged 1 h at $30/h.     Revenue 140, costs 24 + 30.
         Slot: 2 h in Lift B.
    WO3: no mechanic, customer Dana; 1.0 h billed, no parts; Ana logged
         0.5 h.                                   Revenue 100, costs 0 + 20.
         No slot.
    """
    db = new_db(tmp_path)
    seed_shop(db, "Reyes Moto")
    ana, ben = seed_user(db, "ana"), seed_user(db, "ben")
    for u in (ana, ben):
        sql(db, "INSERT INTO shop_members (user_id, shop_id, role) VALUES (?, 1, 'tech')",
            (u,))
    dana = seed_customer(db, 1, "Dana Reyes")
    sam = seed_customer(db, 1, "Sam Ortiz")
    bike = seed_bike(db)
    sql(db, "INSERT INTO shop_bays (shop_id, name) VALUES (1, 'Lift A'), (1, 'Lift B')")

    wo1 = _wo(db, dana, bike, ana, 2.0, "Valve check")
    line1 = _part_line(db, wo1, 1, 5000)
    _time(db, wo1, ana, 7200)
    _slot(db, 1, wo1, 8, 11)
    _slot(db, 2, wo1, 11, 12)

    wo2 = _wo(db, sam, bike, ben, 1.0, "Brake pads")
    line2 = _part_line(db, wo2, 2, 2000)
    _time(db, wo2, ben, 3600)
    _slot(db, 2, wo2, 13, 15)

    wo3 = _wo(db, dana, bike, None, 1.0, "Diagnosis")
    _time(db, wo3, ana, 1800)

    for wo in (wo1, wo2, wo3):
        ok(db, "shop", "invoice", "generate", wo, "--hourly-rate", "10000")
    return db, {"ana": ana, "ben": ben, "line1": line1, "line2": line2}


def _record_costs(db, ids, skip=()):
    if "rates" not in skip:
        ok(db, "shop", "member", "cost-rate", "--user", ids["ana"],
           "--cents-per-hour", "4000", "--from", "2026-01-01")
        ok(db, "shop", "member", "cost-rate", "--user", ids["ben"],
           "--cents-per-hour", "3000", "--from", "2026-01-01")
    if "parts" not in skip:
        ok(db, "shop", "parts-needs", "cost", ids["line1"], "--cents-each", "3000")
        ok(db, "shop", "parts-needs", "cost", ids["line2"], "--cents-each", "1200")


def _pnl(db, by, *extra):
    return json.loads(ok(db, "shop", "analytics", "pnl", "--by", by, "--for", MONTH,
                         "--json", *extra))


def _groups(report):
    return {g["key"]: (g["revenue_total_cents"], g["parts_cost_cents"],
                       g["labour_cost_cents"], g["gross_margin_cents"])
            for g in report["groups"]}


class TestAttribution:
    def test_by_mechanic_everything_follows_the_assigned_mechanic(self, fixture_db):
        db, ids = fixture_db
        _record_costs(db, ids)
        report = _pnl(db, "mechanic")
        assert report["attribution_rule"].startswith(
            "A work order's revenue and all its costs count for its assigned mechanic")
        # WO3 has no mechanic: its revenue and Ana's 0.5 h both go to unassigned
        assert _groups(report) == {
            str(ids["ana"]): (25000, 3000, 8000, 14000),
            str(ids["ben"]): (14000, 2400, 3000, 8600),
            "unassigned": (10000, 0, 2000, 8000),
        }

    def test_by_bay_a_work_order_is_split_by_its_slot_hours(self, fixture_db):
        db, ids = fixture_db
        _record_costs(db, ids)
        report = _pnl(db, "bay")
        assert "split across bays by the slot hours" in report["attribution_rule"]
        # WO1: 3/4 to Lift A, 1/4 to Lift B; WO2 all Lift B; WO3 no bay
        assert _groups(report) == {
            "Lift A (bay 1)": (18750, 2250, 6000, 10500),
            "Lift B (bay 2)": (6250 + 14000, 750 + 2400, 2000 + 3000, 3500 + 8600),
            "no bay": (10000, 0, 2000, 8000),
        }

    def test_by_customer_the_invoices_customer(self, fixture_db):
        db, ids = fixture_db
        _record_costs(db, ids)
        assert _groups(_pnl(db, "customer")) == {
            "Dana Reyes (customer 2)": (35000, 3000, 10000, 22000),
            "Sam Ortiz (customer 3)": (14000, 2400, 3000, 8600),
        }

    def test_the_revenue_is_split_by_line_type(self, fixture_db):
        db, ids = fixture_db
        groups = {g["key"]: g for g in _pnl(db, "mechanic")["groups"]}
        assert groups[str(ids["ben"])]["revenue_cents"] == {"labor": 10000, "parts": 4000}

    def test_the_text_report_states_the_rule(self, fixture_db):
        db, _ = fixture_db
        out = ok(db, "shop", "analytics", "pnl", "--by", "customer", "--for", MONTH)
        assert "Attribution: Each invoice counts for the invoice's customer." in out
        assert "Labour cost: each logged time entry's hours" in out

    def test_a_cancelled_invoice_is_not_revenue(self, fixture_db):
        db, ids = fixture_db
        _record_costs(db, ids)
        ok(db, "shop", "invoice", "void", "2")
        assert str(ids["ben"]) not in _groups(_pnl(db, "mechanic"))


class TestNothingUnrecordedIsZero:
    def test_a_missing_purchase_cost_blocks_the_margin(self, fixture_db):
        db, ids = fixture_db
        _record_costs(db, ids, skip=("parts",))
        groups = {g["key"]: g for g in _pnl(db, "mechanic")["groups"]}
        ana = groups[str(ids["ana"])]
        assert (ana["parts_cost_cents"], ana["parts_cost_missing"],
                ana["gross_margin_cents"]) == (None, 1, None)
        # WO3 has no part lines: nothing to cost, so its parts cost is known
        assert groups["unassigned"]["parts_cost_cents"] == 0
        out = ok(db, "shop", "analytics", "pnl", "--by", "mechanic", "--for", MONTH)
        assert "not recorded (1 WO)" in out and "not computed" in out

    def test_a_missing_cost_rate_blocks_the_margin(self, fixture_db):
        db, ids = fixture_db
        _record_costs(db, ids, skip=("rates",))
        for g in _pnl(db, "shop")["groups"]:
            assert g["labour_cost_cents"] is None and g["gross_margin_cents"] is None

    def test_a_rate_that_starts_after_the_work_does_not_apply(self, fixture_db):
        db, ids = fixture_db
        _record_costs(db, ids, skip=("rates",))
        ok(db, "shop", "member", "cost-rate", "--user", ids["ana"], "--cents-per-hour",
           "4000", "--from", "2999-01-01")
        ok(db, "shop", "member", "cost-rate", "--user", ids["ben"], "--cents-per-hour",
           "3000", "--from", "2026-01-01")
        groups = {g["key"]: g for g in _pnl(db, "mechanic")["groups"]}
        assert groups[str(ids["ana"])]["labour_cost_cents"] is None
        assert groups[str(ids["ben"])]["labour_cost_cents"] == 3000

    def test_the_later_rate_in_force_is_used(self, fixture_db):
        db, ids = fixture_db
        _record_costs(db, ids)
        ok(db, "shop", "member", "cost-rate", "--user", ids["ben"], "--cents-per-hour",
           "5000", "--from", TODAY)
        groups = {g["key"]: g for g in _pnl(db, "mechanic")["groups"]}
        assert groups[str(ids["ben"])]["labour_cost_cents"] == 5000


class TestShopNet:
    def test_net_subtracts_the_months_expenses(self, fixture_db):
        db, ids = fixture_db
        _record_costs(db, ids)
        ok(db, "shop", "expense", "add", "--month", MONTH, "--category", "rent",
           "--cents", "20000")
        ok(db, "shop", "expense", "add", "--month", MONTH, "--category", "utilities",
           "--cents", "5000")
        report = _pnl(db, "shop")
        assert _groups(report) == {"shop": (49000, 5400, 13000, 30600)}
        assert (report["expenses_cents"], report["net_cents"]) == (25000, 5600)
        assert "Net: $56.00" in ok(db, "shop", "analytics", "pnl", "--for", MONTH)
        assert "rent" in ok(db, "shop", "expense", "list", "--month", MONTH)

    def test_no_net_for_a_period_with_a_month_lacking_expenses(self, fixture_db):
        db, ids = fixture_db
        _record_costs(db, ids)
        ok(db, "shop", "expense", "add", "--month", MONTH, "--category", "rent",
           "--cents", "20000")
        quarter = f"{MONTH[:4]}-Q{(int(MONTH[5:]) - 1) // 3 + 1}"
        report = json.loads(ok(db, "shop", "analytics", "pnl", "--period", "quarter",
                               "--for", quarter, "--json"))
        assert report["net_cents"] is None
        assert len(report["expense_months_missing"]) == 2
        assert MONTH not in report["expense_months_missing"]
        out = ok(db, "shop", "analytics", "pnl", "--period", "quarter", "--for", quarter)
        assert "Net not computed: no expenses recorded for" in out

    def test_expenses_are_never_split_below_the_shop(self, fixture_db):
        db, ids = fixture_db
        _record_costs(db, ids)
        ok(db, "shop", "expense", "add", "--month", MONTH, "--category", "rent",
           "--cents", "20000")
        for by in ("mechanic", "bay", "customer"):
            report = _pnl(db, by)
            assert report["expenses_cents"] is None and report["net_cents"] is None


class TestInputs:
    @pytest.mark.parametrize("period, key", [
        ("month", "2026-13"), ("quarter", "2026-Q5"), ("year", "26"),
    ])
    def test_a_bad_period_is_refused(self, fixture_db, period, key):
        db, _ = fixture_db
        refused(db, "shop", "analytics", "pnl", "--period", period, "--for", key)

    def test_a_cost_rate_for_a_non_member_is_refused(self, fixture_db):
        db, _ = fixture_db
        stranger = seed_user(db, "stranger")
        out = refused(db, "shop", "member", "cost-rate", "--user", stranger,
                      "--cents-per-hour", "100", "--from", "2026-01-01")
        assert "not a member" in out

    def test_a_bad_expense_month_is_refused(self, fixture_db):
        db, _ = fixture_db
        refused(db, "shop", "expense", "add", "--month", "2026-9", "--category", "rent",
                "--cents", "1")
        assert sql(db, "SELECT COUNT(*) FROM shop_expenses") == [(0,)]

    def test_a_cost_for_an_unknown_part_line_is_refused(self, fixture_db):
        db, _ = fixture_db
        assert "not found" in refused(db, "shop", "parts-needs", "cost", "999",
                                      "--cents-each", "1")

    def test_the_rates_are_listed_by_the_cli(self, fixture_db):
        db, ids = fixture_db
        _record_costs(db, ids)
        assert "$40.00" in ok(db, "shop", "member", "cost-rates")


def test_no_api_code_reads_the_cost_rates():
    """A mechanic's cost rate is pay data: no API module names the table or
    the module that reads it."""
    api = Path(__file__).resolve().parents[1] / "src" / "motodiag" / "api"
    naming = []
    for path in sorted(api.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "mechanic_cost_rates" in text or "shop_costs" in text:
            naming.append(path.name)
    assert naming == []
