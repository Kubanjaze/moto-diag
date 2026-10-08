"""Phase 379, F176 — `garage remove` refuses a bike that records still name.

`work_orders.vehicle_id` references `vehicles(id) ON DELETE RESTRICT`, and
`garage remove` let the `IntegrityError` out as a traceback (Phase 357's
Step 0). Phase 379's Step 0 found five tables that block the delete:
`intake_visits`, `work_orders` and `workflow_runs` (`RESTRICT`), and
`diagnostic_sessions` and `repair_plans` (`NO ACTION`). The refusal reads
them from the schema and names each with its count.
"""

from __future__ import annotations

import pytest

from support.phase274 import cli, new_db, ok, refused, seed_bike, seed_customer, seed_shop, sql


@pytest.fixture
def db(tmp_path):
    path = new_db(tmp_path)
    shop = seed_shop(path, "Harbor Moto")
    customer = seed_customer(path, shop, "Dana Rider")
    seed_bike(path, "Honda", "CBR600RR", 2005)
    return path, shop, customer


def _plant(path, shop, customer, table):
    rows = {
        "work_orders": ("INSERT INTO work_orders (shop_id, vehicle_id, customer_id, title) "
                        "VALUES (?, 1, ?, 'Brakes')", (shop, customer)),
        "intake_visits": ("INSERT INTO intake_visits (shop_id, customer_id, vehicle_id) "
                          "VALUES (?, ?, 1)", (shop, customer)),
        "diagnostic_sessions": ("INSERT INTO diagnostic_sessions (vehicle_make, vehicle_model, "
                                "vehicle_year, vehicle_id) VALUES ('Honda', 'CBR600RR', 2005, 1)",
                                ()),
        "repair_plans": ("INSERT INTO repair_plans (title, vehicle_id) VALUES ('Plan', 1)", ()),
    }
    query, params = rows[table]
    sql(path, query, params)


@pytest.mark.parametrize("table, words", [
    ("work_orders", "1 work orders"), ("intake_visits", "1 intake visits"),
    ("diagnostic_sessions", "1 diagnostic sessions"), ("repair_plans", "1 repair plans")])
def test_a_bike_with_history_is_refused_and_says_why(db, table, words):
    path, shop, customer = db
    _plant(path, shop, customer, table)
    out = refused(path, "garage", "remove", "1", "--yes")
    flat = " ".join(out.split())
    assert "Traceback" not in out and "IntegrityError" not in out
    assert f"is still named by: {words}" in flat
    assert "Its history is kept, so it cannot be removed." in flat
    assert sql(path, "SELECT COUNT(*) FROM vehicles") == [(1,)]


def test_the_exit_code_is_1(db):
    path, shop, customer = db
    _plant(path, shop, customer, "work_orders")
    res = cli(path, "garage", "remove", "1", "--yes")
    assert res.exit_code == 1


def test_a_saved_run_is_counted_with_the_rest(db):
    from motodiag.vehicles.registry import vehicle_dependents

    path, shop, customer = db
    _plant(path, shop, customer, "work_orders")
    _plant(path, shop, customer, "work_orders")
    sql(path, "INSERT INTO workflow_templates (slug, name, category) "
              "VALUES ('t', 'T', 'ppi')")
    template = sql(path, "SELECT MAX(id) FROM workflow_templates")[0][0]
    sql(path, "INSERT INTO workflow_runs (template_id, vehicle_id, powertrain) "
              "VALUES (?, 1, 'ice')", (template,))
    assert vehicle_dependents(1, db_path=path) == {"work_orders": 2, "workflow_runs": 1}


def test_a_bike_with_no_history_is_removed_as_before(db):
    path, *_ = db
    ok(path, "garage", "remove", "1", "--yes")
    assert sql(path, "SELECT COUNT(*) FROM vehicles") == [(0,)]


def test_the_blocking_tables_come_from_the_schema(db):
    """The five Step 0 found, by reading the foreign keys: a table added
    later joins by itself."""
    path, *_ = db
    blocking = set()
    for (table,) in sql(path, "SELECT name FROM sqlite_master WHERE type = 'table'"):
        for fk in sql(path, f"PRAGMA foreign_key_list('{table}')"):
            if fk[2] == "vehicles" and fk[6] in ("RESTRICT", "NO ACTION"):
                blocking.add(table)
    assert {"intake_visits", "work_orders", "workflow_runs", "diagnostic_sessions",
            "repair_plans"} <= blocking
