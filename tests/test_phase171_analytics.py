"""Phase 171 — Shop analytics dashboard tests.

Five test classes across ~30 tests:

- :class:`TestDateWindow` (5) — Nd/Nh/ISO parsing, bad input raises,
  output format, tz handling, date range.
- :class:`TestRollups` (12) — throughput buckets + completions-by-day,
  turnaround mean/median/p90 with small sample (None), utilization
  aggregation, overrun rate + per-mechanic, labor accuracy buckets,
  top_issues ordering, top_parts with override priority, mechanic
  performance NULL bucket, customer repeat rate.
- :class:`TestDashboardSnapshot` (3) — composes all rollups,
  includes Phase 169 revenue, deterministic output with same args.
- :class:`TestAnalyticsCLI` (8) — each subcommand round-trip + snapshot.
- :class:`TestAntiRegression` (2) — no migrations run, shop/__init__
  re-exports.

All tests SW + SQL only; zero AI.
"""

from __future__ import annotations

import json as _json
from datetime import datetime, timedelta

import click
import pytest
from click.testing import CliRunner

from motodiag.cli.shop import register_shop
from motodiag.core.database import (
    SCHEMA_VERSION, get_connection, init_db,
)
from motodiag.crm import customer_repo
from motodiag.crm.models import Customer
from motodiag.shop import (
    add_bay, add_part_to_work_order, assign_mechanic,
    complete_work_order, create_shop, create_work_order,
    customer_repeat_rate, dashboard_snapshot,
    labor_accuracy, mechanic_performance, open_work_order,
    overrun_rate, schedule_wo, start_slot, complete_slot,
    start_work, throughput, top_issues, top_parts,
    turnaround, utilization_rollup,
)
from motodiag.shop.analytics import (
    _daterange, _parse_date_window,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_cli():
    @click.group()
    def root() -> None:
        """test root"""

    register_shop(root)
    return root


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase171.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase171_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    yield path
    reset_settings()


def _add_customer(db_path, name="Jane Doe", email="j@ex.com"):
    return customer_repo.create_customer(
        Customer(name=name, phone="555-0100", email=email),
        db_path=db_path,
    )


def _add_vehicle(db_path, make="Harley-Davidson",
                 model="Sportster 1200", year=2010):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO vehicles (make, model, year, protocol) "
            "VALUES (?, ?, ?, 'none')", (make, model, year),
        )
        return cursor.lastrowid


def _add_part(db_path, slug="brake-pad-x", typical_cents=2000):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO parts (slug, oem_part_number, brand,
               description, category, make, model_pattern,
               typical_cost_cents, verified_by)
               VALUES (?, 'OEM-1', 'EBC', 'brake pad', 'brakes',
                       'harley-davidson', '%', ?, 'test')""",
            (slug, typical_cents),
        )
        return cursor.lastrowid


def _seed_completed_wo(
    db_path, *, shop_id=None, customer_id=None, vehicle_id=None,
    mechanic_id=None, actual_hours=2.0, title="service",
):
    if shop_id is None:
        shop_id = create_shop("s", db_path=db_path)
    if customer_id is None:
        customer_id = _add_customer(db_path)
    if vehicle_id is None:
        vehicle_id = _add_vehicle(db_path)
    wo_id = create_work_order(
        shop_id=shop_id, vehicle_id=vehicle_id, customer_id=customer_id,
        title=title, estimated_hours=2.0, db_path=db_path,
    )
    open_work_order(wo_id, db_path=db_path)
    if mechanic_id is not None:
        assign_mechanic(wo_id, mechanic_id, db_path=db_path)
    start_work(wo_id, db_path=db_path)
    complete_work_order(
        wo_id, actual_hours=actual_hours, db_path=db_path,
    )
    return shop_id, customer_id, vehicle_id, wo_id


# ===========================================================================
# 1. _parse_date_window + _daterange
# ===========================================================================


class TestDateWindow:

    def test_nd_window(self):
        out = _parse_date_window("7d")
        # Output matches ISO-ish format
        parsed = datetime.strptime(out, "%Y-%m-%d %H:%M:%S")
        now = datetime.utcnow()
        assert (now - parsed).days >= 6  # Approx 7 days ago

    def test_nh_window(self):
        out = _parse_date_window("24h")
        parsed = datetime.strptime(out, "%Y-%m-%d %H:%M:%S")
        now = datetime.utcnow()
        assert (now - parsed).total_seconds() >= 23 * 3600

    def test_iso_input(self):
        out = _parse_date_window("2026-04-01T10:00:00")
        assert out.startswith("2026-04-01 10:00")

    def test_bad_input_raises(self):
        with pytest.raises(ValueError):
            _parse_date_window("")
        with pytest.raises(ValueError):
            _parse_date_window("not-a-date")

    def test_daterange_inclusive(self):
        dates = _daterange("2026-04-20", "2026-04-22")
        assert dates == ["2026-04-20", "2026-04-21", "2026-04-22"]


# ===========================================================================
# 2. Individual rollups
# ===========================================================================


class TestRollups:

    def test_throughput_by_status(self, db):
        shop_id, _, _, _ = _seed_completed_wo(db)
        t = throughput(shop_id, since="1d", db_path=db)
        assert t.completed_total == 1
        assert t.by_status.get("completed") == 1

    def test_throughput_empty_shop(self, db):
        shop_id = create_shop("s", db_path=db)
        t = throughput(shop_id, since="30d", db_path=db)
        assert t.completed_total == 0
        assert t.by_status == {}

    def test_turnaround_small_sample_returns_none_p90(self, db):
        shop_id, _, _, _ = _seed_completed_wo(db)
        t = turnaround(shop_id, since="1d", db_path=db)
        assert t.sample_size == 1
        assert t.mean_hours is not None
        assert t.p90_hours is None  # < 5 sample

    def test_turnaround_zero_sample(self, db):
        shop_id = create_shop("s", db_path=db)
        t = turnaround(shop_id, since="30d", db_path=db)
        assert t.sample_size == 0
        assert t.mean_hours is None
        assert t.median_hours is None

    def test_utilization_rollup(self, db):
        shop_id = create_shop("s", db_path=db)
        # Empty shop: all days at 0.0 utilization
        today = datetime.utcnow().strftime("%Y-%m-%d")
        yesterday = (
            datetime.utcnow() - timedelta(days=1)
        ).strftime("%Y-%m-%d")
        u = utilization_rollup(
            shop_id, yesterday, today, db_path=db,
        )
        assert len(u.days) == 2
        assert u.mean_pct == 0.0
        assert u.over_threshold_days == 0

    def test_overrun_rate_empty_shop(self, db):
        shop_id = create_shop("s", db_path=db)
        o = overrun_rate(shop_id, since="30d", db_path=db)
        assert o.total_slots == 0
        assert o.rate == 0.0

    def test_overrun_rate_with_slots(self, db):
        shop_id, _, _, wo_id = _seed_completed_wo(db)
        bay_id = add_bay(shop_id, "Bay 1", "lift", db_path=db)
        # Insert overrun + completed slot rows directly (bypass
        # schedule_wo terminal-WO guard) so we can test rollup logic.
        now_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        soon_str = (
            datetime.utcnow() + timedelta(hours=1)
        ).strftime("%Y-%m-%dT%H:%M:%S")
        with get_connection(db) as conn:
            conn.execute(
                """INSERT INTO bay_schedule_slots
                   (bay_id, work_order_id, scheduled_start, scheduled_end,
                    actual_start, actual_end, status)
                   VALUES (?, ?, ?, ?, ?, ?, 'overrun')""",
                (bay_id, wo_id, now_str, soon_str, now_str, soon_str),
            )
            conn.execute(
                """INSERT INTO bay_schedule_slots
                   (bay_id, work_order_id, scheduled_start, scheduled_end,
                    actual_start, actual_end, status)
                   VALUES (?, ?, ?, ?, ?, ?, 'completed')""",
                (bay_id, wo_id, now_str, soon_str, now_str, soon_str),
            )
        o = overrun_rate(shop_id, since="1d", db_path=db)
        assert o.total_slots == 2
        assert o.overrun_slots == 1
        assert o.rate == 0.5

    def test_labor_accuracy_handles_empty(self, db):
        shop_id = create_shop("s", db_path=db)
        la = labor_accuracy(shop_id, since="30d", db_path=db)
        assert la.sample_size == 0
        assert la.within_pct == 0.0

    def test_top_issues_ordering(self, db):
        shop_id, _, _, wo_id = _seed_completed_wo(db)
        # Insert issues directly (bypass Phase 162 repo for brevity)
        with get_connection(db) as conn:
            for sev in ("high", "high", "medium"):
                conn.execute(
                    """INSERT INTO issues (work_order_id, title, category,
                       severity, status, created_at)
                       VALUES (?, 'x', 'electrical', ?, 'open',
                       CURRENT_TIMESTAMP)""",
                    (wo_id, sev),
                )
        rows = top_issues(shop_id, since="1d", db_path=db)
        assert len(rows) >= 1
        # Highest count first
        assert rows[0].count >= rows[-1].count

    def test_top_parts_aggregates_cost(self, db):
        shop_id, _, _, wo_id = _seed_completed_wo(db)
        pid = _add_part(db, typical_cents=1500)
        add_part_to_work_order(wo_id, pid, quantity=3, db_path=db)
        rows = top_parts(shop_id, since="1d", db_path=db)
        assert len(rows) >= 1
        assert rows[0].total_qty == 3
        assert rows[0].total_cost_cents == 4500

    def test_top_parts_respects_override(self, db):
        shop_id, _, _, wo_id = _seed_completed_wo(db)
        pid = _add_part(db, typical_cents=1500)
        wop_id = add_part_to_work_order(wo_id, pid, quantity=2, db_path=db)
        # Override unit cost
        from motodiag.shop import update_part_cost_override
        update_part_cost_override(wop_id, 2500, db_path=db)
        rows = top_parts(shop_id, since="1d", db_path=db)
        assert rows[0].total_cost_cents == 5000  # 2 * 2500

    def test_mechanic_performance_null_bucket(self, db):
        shop_id, _, _, _ = _seed_completed_wo(db)
        perf = mechanic_performance(shop_id, since="1d", db_path=db)
        # Unassigned WO → mechanic_id=None bucket
        assert any(p.mechanic_id is None for p in perf)

    def test_customer_repeat_rate(self, db):
        shop_id = create_shop("s", db_path=db)
        c = _add_customer(db)
        v = _add_vehicle(db)
        # First WO (prior)
        wo1 = create_work_order(
            shop_id=shop_id, vehicle_id=v, customer_id=c,
            title="first", estimated_hours=1.0, db_path=db,
        )
        open_work_order(wo1, db_path=db)
        start_work(wo1, db_path=db)
        complete_work_order(wo1, actual_hours=1.0, db_path=db)
        # Second WO (repeat)
        wo2 = create_work_order(
            shop_id=shop_id, vehicle_id=v, customer_id=c,
            title="second", estimated_hours=1.0, db_path=db,
        )
        open_work_order(wo2, db_path=db)
        start_work(wo2, db_path=db)
        complete_work_order(wo2, actual_hours=1.0, db_path=db)
        rate = customer_repeat_rate(shop_id, since="1d", db_path=db)
        assert rate.total_wos == 2
        assert rate.repeat_wos == 1
        assert rate.repeat_rate == 0.5


# ===========================================================================
# 3. dashboard_snapshot composition
# ===========================================================================


class TestDashboardSnapshot:

    def test_snapshot_composes_all(self, db):
        shop_id, _, _, _ = _seed_completed_wo(db)
        snap = dashboard_snapshot(shop_id, since="1d", db_path=db)
        assert snap.shop_id == shop_id
        assert snap.throughput.completed_total >= 1
        assert snap.turnaround.sample_size >= 1
        assert snap.revenue is not None

    def test_snapshot_empty_shop(self, db):
        shop_id = create_shop("s", db_path=db)
        snap = dashboard_snapshot(shop_id, since="30d", db_path=db)
        assert snap.throughput.completed_total == 0
        assert snap.turnaround.sample_size == 0
        assert snap.revenue.invoice_count == 0

    def test_snapshot_deterministic(self, db):
        shop_id, _, _, _ = _seed_completed_wo(db)
        s1 = dashboard_snapshot(shop_id, since="1d", db_path=db)
        s2 = dashboard_snapshot(shop_id, since="1d", db_path=db)
        # generated_at will differ; compare the deterministic parts
        assert s1.throughput.completed_total == s2.throughput.completed_total
        assert s1.top_issues == s2.top_issues
        assert s1.top_parts == s2.top_parts


# ===========================================================================
# 4. CLI round-trip
# ===========================================================================


class TestAnalyticsCLI:

    def test_snapshot_cli(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id, _, _, _ = _seed_completed_wo(cli_db)
        r = runner.invoke(root, [
            "shop", "analytics", "snapshot",
            "--shop", str(shop_id), "--since", "1d", "--json",
        ])
        assert r.exit_code == 0, r.output
        data = _json.loads(r.output)
        assert data["shop_id"] == shop_id

    def test_throughput_cli(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id, _, _, _ = _seed_completed_wo(cli_db)
        r = runner.invoke(root, [
            "shop", "analytics", "throughput",
            "--shop", str(shop_id), "--since", "1d", "--json",
        ])
        assert r.exit_code == 0, r.output
        data = _json.loads(r.output)
        assert data["completed_total"] == 1

    def test_turnaround_cli(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id, _, _, _ = _seed_completed_wo(cli_db)
        r = runner.invoke(root, [
            "shop", "analytics", "turnaround",
            "--shop", str(shop_id), "--since", "1d", "--json",
        ])
        assert r.exit_code == 0, r.output

    def test_utilization_cli(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id = create_shop("s", db_path=cli_db)
        today = datetime.utcnow().strftime("%Y-%m-%d")
        r = runner.invoke(root, [
            "shop", "analytics", "utilization",
            "--shop", str(shop_id),
            "--from", today, "--to", today, "--json",
        ])
        assert r.exit_code == 0, r.output

    def test_top_issues_cli(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id, _, _, _ = _seed_completed_wo(cli_db)
        r = runner.invoke(root, [
            "shop", "analytics", "top-issues",
            "--shop", str(shop_id), "--since", "1d", "--json",
        ])
        assert r.exit_code == 0, r.output

    def test_top_parts_cli(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id, _, _, _ = _seed_completed_wo(cli_db)
        r = runner.invoke(root, [
            "shop", "analytics", "top-parts",
            "--shop", str(shop_id), "--since", "1d", "--json",
        ])
        assert r.exit_code == 0, r.output

    def test_mechanic_cli(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id, _, _, _ = _seed_completed_wo(cli_db)
        r = runner.invoke(root, [
            "shop", "analytics", "mechanic",
            "--shop", str(shop_id), "--since", "1d", "--json",
        ])
        assert r.exit_code == 0, r.output

    def test_customer_repeat_cli(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id, _, _, _ = _seed_completed_wo(cli_db)
        r = runner.invoke(root, [
            "shop", "analytics", "customer-repeat",
            "--shop", str(shop_id), "--since", "1d", "--json",
        ])
        assert r.exit_code == 0, r.output


# ===========================================================================
# 5. Anti-regression
# ===========================================================================


class TestAntiRegression:

    def test_no_migration_added(self):
        # Phase 171 itself is read-only — it shipped at schema v34
        # without bumping. Later phases may bump further.
        assert SCHEMA_VERSION >= 34

    def test_analytics_reexports(self):
        from motodiag.shop import (
            DashboardSnapshot, ThroughputRollup, dashboard_snapshot,
            top_parts,
        )
        assert DashboardSnapshot is not None
        assert ThroughputRollup is not None
        assert callable(dashboard_snapshot)
        assert callable(top_parts)
