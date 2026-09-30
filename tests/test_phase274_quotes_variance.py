"""Phase 274 — F182, the quote record, `shop labor-rate`, and row 291.

F182: the estimate a customer was sent was the estimated hours times a
hard-coded $100, parts left out. The estimate is now the hours at the rate
`generate_invoice_for_wo` looks up, plus the estimated parts, and is refused
when either figure is missing. Each queued estimate is recorded, and `shop
analytics variance` compares the invoice with that record; with none it says
"no quote recorded".
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from support.phase274 import (
    new_db, ok, refused, seed_bike, seed_customer, seed_shop, sql,
)

NOW = datetime.now(timezone.utc)


@pytest.fixture
def db(tmp_path):
    path = new_db(tmp_path)
    seed_shop(path, "Reyes Moto")
    seed_customer(path, 1, "Pat Probe", email="pat@example.com")   # 2
    seed_bike(path)
    return path


def _wo(db, hours=2.0, parts_cents=54991, status="open", actual=None, completed=None):
    sql(db, "INSERT INTO work_orders (shop_id, vehicle_id, customer_id, title, status, "
            "estimated_hours, estimated_parts_cost_cents, actual_hours, opened_at, "
            "completed_at) VALUES (1, 1, 2, 'Valve check', ?, ?, ?, ?, ?, ?)",
        (status, hours, parts_cents, actual, NOW.isoformat(), completed))
    return sql(db, "SELECT MAX(id) FROM work_orders")[0][0]


def _estimate(db, wo, command="trigger", *extra):
    return ok(db, "shop", "notify", command, "estimate_ready", "--wo", wo,
              "--channel", "email", *extra)


def _quotes(db):
    return sql(db, "SELECT work_order_id, notification_id, estimated_hours, "
                   "labor_rate_cents, parts_cents, total_cents FROM work_order_quotes")


class TestTheEstimate:
    def test_hours_at_the_labour_rate_plus_the_parts(self, db):
        ok(db, "shop", "labor-rate", "set", "--hourly-cents", "9500")
        wo = _wo(db)
        out = _estimate(db, wo, "preview")
        # 2.0 h x $95.00 + $549.91; the old code rendered $200.00
        assert "$739.91" in out
        assert "$200.00" not in out

    def test_no_labour_rate_refuses_the_estimate(self, db):
        wo = _wo(db)
        out = refused(db, "shop", "notify", "trigger", "estimate_ready", "--wo", wo)
        assert "no labour rate is recorded" in out
        assert "shop labor-rate set" in out
        assert sql(db, "SELECT COUNT(*) FROM customer_notifications") == [(0,)]
        assert _quotes(db) == []

    def test_no_estimated_hours_refuses_the_estimate(self, db):
        ok(db, "shop", "labor-rate", "set", "--hourly-cents", "9500")
        wo = _wo(db, hours=None)
        out = refused(db, "shop", "notify", "trigger", "estimate_ready", "--wo", wo)
        assert "no estimated hours" in out

    def test_no_parts_estimate_is_labour_only(self, db):
        ok(db, "shop", "labor-rate", "set", "--hourly-cents", "9500")
        wo = _wo(db, hours=1.5, parts_cents=None)
        assert "$142.50" in _estimate(db, wo, "preview")

    def test_the_figures_cannot_be_overridden(self, db):
        ok(db, "shop", "labor-rate", "set", "--hourly-cents", "9500")
        wo = _wo(db)
        out = refused(db, "shop", "notify", "trigger", "estimate_ready", "--wo", wo,
                      "--extra", '{"estimate_total": "1.00"}')
        assert "cannot be overridden" in out
        assert _quotes(db) == []

    def test_the_labour_rate_list(self, db):
        assert "No labour rate recorded" in ok(db, "shop", "labor-rate", "list")
        ok(db, "shop", "labor-rate", "set", "--hourly-cents", "9500", "--state", "ma",
           "--source", "posted board")
        out = ok(db, "shop", "labor-rate", "list")
        assert "MA" in out and "$95.00" in out and "posted board" in out


class TestTheQuoteRecord:
    def test_queuing_an_estimate_records_the_quote(self, db):
        ok(db, "shop", "labor-rate", "set", "--hourly-cents", "9500")
        wo = _wo(db)
        _estimate(db, wo)
        nid = sql(db, "SELECT id FROM customer_notifications")[0][0]
        assert _quotes(db) == [(wo, nid, 2.0, 9500, 54991, 73991)]
        quoted_at = sql(db, "SELECT quoted_at FROM work_order_quotes")[0][0]
        assert quoted_at[:10] == NOW.strftime("%Y-%m-%d")

    def test_a_preview_records_nothing(self, db):
        ok(db, "shop", "labor-rate", "set", "--hourly-cents", "9500")
        _estimate(db, _wo(db), "preview")
        assert _quotes(db) == []

    def test_a_resend_repeats_the_message_not_the_quote(self, db):
        ok(db, "shop", "labor-rate", "set", "--hourly-cents", "9500")
        _estimate(db, _wo(db))
        ok(db, "shop", "notify", "resend", "1")
        assert sql(db, "SELECT COUNT(*) FROM customer_notifications") == [(2,)]
        assert len(_quotes(db)) == 1

    def test_another_event_records_no_quote(self, db):
        _wo(db)
        ok(db, "shop", "notify", "trigger", "wo_opened", "--wo", "1")
        assert _quotes(db) == []

    def test_the_quote_and_the_invoice_charge_the_same_rate(self, db):
        ok(db, "shop", "labor-rate", "set", "--hourly-cents", "9500")
        wo = _wo(db, status="completed", actual=2.0, completed=NOW.isoformat())
        _estimate(db, wo)
        ok(db, "shop", "invoice", "generate", wo)
        invoice_rate = sql(db, "SELECT unit_price FROM invoice_line_items "
                               "WHERE item_type = 'labor'")[0][0]
        assert round(invoice_rate * 100) == _quotes(db)[0][3] == 9500


class TestVariance:
    def _completed(self, db, hours, actual, parts_cents, part_lines=()):
        wo = _wo(db, hours=hours, parts_cents=parts_cents, status="completed",
                 actual=actual, completed=NOW.isoformat())
        for i, billed in enumerate(part_lines):
            sql(db, "INSERT INTO parts (slug, brand, description, category, make, "
                    "model_pattern, typical_cost_cents) VALUES (?, 'OEM', 'Part', "
                    "'engine', 'Honda', '%', ?)", (f"p{wo}-{i}", billed))
            part = sql(db, "SELECT MAX(id) FROM parts")[0][0]
            sql(db, "INSERT INTO work_order_parts (work_order_id, part_id, quantity, "
                    "status) VALUES (?, ?, 1, 'installed')", (wo, part))
        return wo

    def _report(self, db):
        return {r["work_order_id"]: r for r in json.loads(
            ok(db, "shop", "analytics", "variance", "--json"))["rows"]}

    def test_labour_parts_and_quote_against_the_invoice(self, db):
        ok(db, "shop", "labor-rate", "set", "--hourly-cents", "10000")
        wo = self._completed(db, 2.0, 2.5, 5000, part_lines=(3000, 3000))
        _estimate(db, wo)                                  # quote 200 + 50 = 250
        ok(db, "shop", "invoice", "generate", wo)          # 250 + 60 = 310
        row = self._report(db)[wo]
        assert row["labour_delta_pct"] == 0.25
        assert (row["actual_parts_cents"], row["parts_delta_pct"]) == (6000, 0.2)
        assert (row["quote_total_cents"], row["invoice_subtotal_cents"],
                row["quote_delta_pct"]) == (25000, 31000, 0.24)

    def test_no_quote_recorded_is_said_not_recomputed(self, db):
        ok(db, "shop", "labor-rate", "set", "--hourly-cents", "10000")
        wo = self._completed(db, 2.0, 2.0, 0)
        ok(db, "shop", "invoice", "generate", wo)
        row = self._report(db)[wo]
        assert (row["quote_note"], row["quote_total_cents"],
                row["quote_delta_pct"]) == ("no quote recorded", None, None)
        assert "no quote recorded" in ok(db, "shop", "analytics", "variance")

    def test_a_quote_made_after_the_invoice_is_not_used(self, db):
        ok(db, "shop", "labor-rate", "set", "--hourly-cents", "10000")
        wo = self._completed(db, 2.0, 2.0, 0)
        ok(db, "shop", "invoice", "generate", wo)
        later = (NOW + timedelta(days=1)).isoformat()
        sql(db, "INSERT INTO work_order_quotes (work_order_id, estimated_hours, "
                "labor_rate_cents, parts_cents, total_cents, quoted_at) "
                "VALUES (?, 2.0, 10000, 0, 20000, ?)", (wo, later))
        assert self._report(db)[wo]["quote_note"] == "no quote recorded"

    def test_missing_estimates_are_named_not_scored(self, db):
        wo = self._completed(db, None, 1.0, None)
        report = json.loads(ok(db, "shop", "analytics", "variance", "--json"))
        row = report["rows"][0]
        assert (row["work_order_id"], row["labour_note"], row["parts_note"],
                row["quote_note"]) == (wo, "no estimate", "no estimate", "not invoiced")
        assert (report["labour_scored"], report["parts_scored"],
                report["quotes_scored"]) == (0, 0, 0)

    def test_the_medians(self, db):
        for est, act in ((2.0, 2.0), (2.0, 3.0), (4.0, 3.0)):
            self._completed(db, est, act, None)
        report = json.loads(ok(db, "shop", "analytics", "variance", "--json"))
        assert report["labour_scored"] == 3
        assert report["labour_median_delta_pct"] == 0.0
        out = ok(db, "shop", "analytics", "variance")
        assert "Scored: labour 3, parts 0, quotes 0" in out

    def test_an_open_work_order_is_not_reported(self, db):
        _wo(db)
        assert "No completed work orders" in ok(db, "shop", "analytics", "variance")
