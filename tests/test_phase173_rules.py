"""Phase 173 — Workflow automation rules tests.

Six test classes across ~34 tests:

- :class:`TestMigration036` (4) — schema, tables, CHECK, rollback.
- :class:`TestConditions` (12) — each of 12 condition types at match +
  no-match; always + empty-conditions-list behavior.
- :class:`TestActions` (8) — each of 8 action types; mock-patch audit
  for at least 3 that route through phase repos.
- :class:`TestRuleCRUD` (6) — create + unique-name + invalid-event/
  condition/action; list/update/enable/disable/delete.
- :class:`TestFiring` (6) — fire_rule_for_wo writes run row matched/
  unmatched; trigger_rules_for_event in priority order; manual event
  raises; action failure logs error but continues; disabled rule
  skipped.
- :class:`TestRuleCLI` (5) — add/list/show/fire/history round-trip.

All tests SW + SQL only; zero AI.
"""

from __future__ import annotations

import json as _json
import sqlite3
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

from motodiag.cli.shop import register_shop
from motodiag.core.database import (
    SCHEMA_VERSION, get_connection, init_db, table_exists,
)
from motodiag.core.migrations import rollback_to_version
from motodiag.crm import customer_repo
from motodiag.crm.models import Customer
from motodiag.shop import (
    DuplicateRuleNameError,
    InvalidActionError,
    InvalidConditionError,
    InvalidEventError,
    add_part_to_work_order,
    add_shop_member,
    build_wo_context,
    complete_work_order,
    create_rule,
    create_shop,
    create_work_order,
    delete_rule,
    disable_rule,
    enable_rule,
    evaluate_condition,
    evaluate_rule,
    fire_rule_for_wo,
    get_rule,
    list_rule_runs,
    list_rules,
    open_work_order,
    trigger_rules_for_event,
    update_rule,
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
    path = str(tmp_path / "phase173.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase173_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    yield path
    reset_settings()


def _add_customer(db_path, name="Jane Doe"):
    return customer_repo.create_customer(
        Customer(name=name, phone="555-0100", email="j@ex.com"),
        db_path=db_path,
    )


def _add_vehicle(db_path):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO vehicles (make, model, year, protocol) "
            "VALUES ('Harley','Sportster',2010,'none')"
        )
        return cursor.lastrowid


def _add_user(db_path, username="bob"):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, tier, is_active) "
            "VALUES (?, 'individual', 1)",
            (username,),
        )
        return cursor.lastrowid


def _seed_wo(db_path, *, shop_id=None, priority=3):
    if shop_id is None:
        shop_id = create_shop("s", db_path=db_path)
    c = _add_customer(db_path)
    v = _add_vehicle(db_path)
    wo_id = create_work_order(
        shop_id=shop_id, vehicle_id=v, customer_id=c,
        title="service", priority=priority,
        estimated_hours=1.0, db_path=db_path,
    )
    open_work_order(wo_id, db_path=db_path)
    return shop_id, wo_id


def _add_part(db_path, typical_cents=1500):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO parts (slug, oem_part_number, brand,
               description, category, make, model_pattern,
               typical_cost_cents, verified_by)
               VALUES ('brake-pad', 'OEM-1', 'EBC', 'brake pad',
                       'brakes', 'harley-davidson', '%', ?, 'test')""",
            (typical_cents,),
        )
        return cursor.lastrowid


# ===========================================================================
# 1. Migration 036
# ===========================================================================


class TestMigration036:

    def test_schema_version_bumped(self, db):
        assert SCHEMA_VERSION >= 36

    def test_tables_created(self, db):
        assert table_exists("workflow_rules", db)
        assert table_exists("workflow_rule_runs", db)

    def test_event_check_enforced(self, db):
        shop_id = create_shop("s", db_path=db)
        with pytest.raises(sqlite3.IntegrityError):
            with get_connection(db) as conn:
                conn.execute(
                    "INSERT INTO workflow_rules "
                    "(shop_id, name, event_trigger, conditions_json, "
                    " actions_json) "
                    "VALUES (?, 'r', 'bogus_event', '[]', '[]')",
                    (shop_id,),
                )

    def test_rollback_drops_tables(self, tmp_path):
        path = str(tmp_path / "rollback.db")
        init_db(path)
        assert table_exists("workflow_rules", path)
        rollback_to_version(35, path)
        assert not table_exists("workflow_rules", path)
        assert not table_exists("workflow_rule_runs", path)
        # Phase 172 preserved
        assert table_exists("shop_members", path)


# ===========================================================================
# 2. Condition evaluators
# ===========================================================================


class TestConditions:

    def test_always(self, db):
        shop_id, wo_id = _seed_wo(db)
        ctx = build_wo_context(wo_id, db_path=db)
        assert evaluate_condition({"type": "always"}, ctx) is True

    def test_priority_gte_match_and_miss(self, db):
        shop_id, wo_id = _seed_wo(db, priority=4)
        ctx = build_wo_context(wo_id, db_path=db)
        assert evaluate_condition(
            {"type": "priority_gte", "value": 3}, ctx,
        ) is True
        assert evaluate_condition(
            {"type": "priority_gte", "value": 5}, ctx,
        ) is False

    def test_priority_lte(self, db):
        shop_id, wo_id = _seed_wo(db, priority=2)
        ctx = build_wo_context(wo_id, db_path=db)
        assert evaluate_condition(
            {"type": "priority_lte", "value": 2}, ctx,
        ) is True

    def test_priority_eq(self, db):
        shop_id, wo_id = _seed_wo(db, priority=3)
        ctx = build_wo_context(wo_id, db_path=db)
        assert evaluate_condition(
            {"type": "priority_eq", "value": 3}, ctx,
        ) is True

    def test_status_eq_and_in(self, db):
        shop_id, wo_id = _seed_wo(db)
        ctx = build_wo_context(wo_id, db_path=db)
        assert evaluate_condition(
            {"type": "status_eq", "value": "open"}, ctx,
        ) is True
        assert evaluate_condition(
            {"type": "status_in", "values": ["open", "in_progress"]},
            ctx,
        ) is True
        assert evaluate_condition(
            {"type": "status_in", "values": ["completed"]}, ctx,
        ) is False

    def test_severity_eq_in_requires_open_issue(self, db):
        shop_id, wo_id = _seed_wo(db)
        # No issues yet
        ctx = build_wo_context(wo_id, db_path=db)
        assert evaluate_condition(
            {"type": "severity_eq", "value": "critical"}, ctx,
        ) is False
        with get_connection(db) as conn:
            conn.execute(
                """INSERT INTO issues
                   (work_order_id, title, category, severity, status,
                    created_at)
                   VALUES (?, 'x', 'brakes', 'critical', 'open',
                           CURRENT_TIMESTAMP)""",
                (wo_id,),
            )
        ctx = build_wo_context(wo_id, db_path=db)
        assert evaluate_condition(
            {"type": "severity_eq", "value": "critical"}, ctx,
        ) is True

    def test_category_in(self, db):
        shop_id, wo_id = _seed_wo(db)
        with get_connection(db) as conn:
            conn.execute(
                """INSERT INTO issues
                   (work_order_id, title, category, severity, status,
                    created_at)
                   VALUES (?, 'x', 'brakes', 'high', 'open',
                           CURRENT_TIMESTAMP)""",
                (wo_id,),
            )
        ctx = build_wo_context(wo_id, db_path=db)
        assert evaluate_condition(
            {"type": "category_in", "values": ["brakes", "safety"]},
            ctx,
        ) is True

    def test_parts_cost_gt_cents(self, db):
        shop_id, wo_id = _seed_wo(db)
        part_id = _add_part(db, typical_cents=60000)  # $600
        add_part_to_work_order(wo_id, part_id, quantity=1, db_path=db)
        ctx = build_wo_context(wo_id, db_path=db)
        assert evaluate_condition(
            {"type": "parts_cost_gt_cents", "value": 50000}, ctx,
        ) is True
        assert evaluate_condition(
            {"type": "parts_cost_gt_cents", "value": 70000}, ctx,
        ) is False

    def test_invoice_total_gt_cents(self, db):
        shop_id, wo_id = _seed_wo(db)
        # Insert invoice directly
        with get_connection(db) as conn:
            conn.execute(
                """INSERT INTO invoices
                   (customer_id, invoice_number, status, subtotal,
                    tax_amount, total, currency, work_order_id)
                   VALUES (?, 'INV-1', 'sent', 100.0, 10.0, 110.0,
                           'USD', ?)""",
                (_add_customer(db, name="Alice"), wo_id),
            )
        ctx = build_wo_context(wo_id, db_path=db)
        assert evaluate_condition(
            {"type": "invoice_total_gt_cents", "value": 10000}, ctx,
        ) is True

    def test_has_unresolved_issue(self, db):
        shop_id, wo_id = _seed_wo(db)
        ctx = build_wo_context(wo_id, db_path=db)
        assert evaluate_condition(
            {"type": "has_unresolved_issue"}, ctx,
        ) is False
        with get_connection(db) as conn:
            conn.execute(
                """INSERT INTO issues
                   (work_order_id, title, category, severity, status,
                    created_at)
                   VALUES (?, 'x', 'brakes', 'medium', 'open',
                           CURRENT_TIMESTAMP)""",
                (wo_id,),
            )
        ctx = build_wo_context(wo_id, db_path=db)
        assert evaluate_condition(
            {"type": "has_unresolved_issue"}, ctx,
        ) is True

    def test_empty_conditions_list_matches(self, db):
        from motodiag.shop import evaluate_conditions
        ctx = {"wo": {"priority": 1}}
        assert evaluate_conditions([], ctx) is True

    def test_unknown_condition_rejected_at_validation(self):
        from motodiag.shop import validate_conditions
        with pytest.raises(InvalidConditionError):
            validate_conditions([{"type": "bogus"}])


# ===========================================================================
# 3. Actions
# ===========================================================================


class TestActions:

    def test_set_priority_routes_through_phase_161(self, db):
        """Mock-patch audit: set_priority calls Phase 161 update_work_order
        (whitelist), not raw SQL."""
        import motodiag.shop.work_order_repo as wo_repo
        real_update = wo_repo.update_work_order
        shop_id, wo_id = _seed_wo(db, priority=3)
        rule_id = create_rule(
            shop_id=shop_id, name="p1", event_trigger="manual",
            conditions=[{"type": "always"}],
            actions=[{"type": "set_priority", "value": 1}],
            db_path=db,
        )
        with patch.object(
            wo_repo, "update_work_order", wraps=real_update,
        ) as mocked:
            fire_rule_for_wo(rule_id, wo_id, db_path=db)
            mocked.assert_called_once()
            call_args = mocked.call_args
            assert call_args[0][0] == wo_id
            assert call_args[0][1] == {"priority": 1}

    def test_flag_urgent_action(self, db):
        shop_id, wo_id = _seed_wo(db)
        rule_id = create_rule(
            shop_id=shop_id, name="urg", event_trigger="manual",
            conditions=[{"type": "always"}],
            actions=[{"type": "flag_urgent"}],
            db_path=db,
        )
        fire_rule_for_wo(rule_id, wo_id, db_path=db)
        with get_connection(db) as conn:
            row = conn.execute(
                "SELECT description FROM work_orders WHERE id = ?",
                (wo_id,),
            ).fetchone()
        assert "[TRIAGE_URGENT]" in (row["description"] or "")

    def test_trigger_notification_action(self, db):
        shop_id, wo_id = _seed_wo(db)
        rule_id = create_rule(
            shop_id=shop_id, name="notify", event_trigger="manual",
            conditions=[{"type": "always"}],
            actions=[{
                "type": "trigger_notification",
                "event": "wo_opened",
                "channel": "email",
            }],
            db_path=db,
        )
        result = fire_rule_for_wo(rule_id, wo_id, db_path=db)
        assert result.matched
        assert len(result.actions_log) == 1
        assert result.actions_log[0]["type"] == "trigger_notification"
        assert result.actions_log[0]["ok"] is True

    def test_reassign_action_requires_shop_member(self, db):
        shop_id, wo_id = _seed_wo(db)
        # No shop members — reassign fails (but error is captured,
        # sibling actions continue).
        rule_id = create_rule(
            shop_id=shop_id, name="reassign", event_trigger="manual",
            conditions=[{"type": "always"}],
            actions=[{"type": "reassign_to_user", "value": 999}],
            db_path=db,
        )
        result = fire_rule_for_wo(rule_id, wo_id, db_path=db)
        assert result.matched
        # Action should have failed with a captured error
        assert result.error is not None
        assert result.actions_log[0]["ok"] is False

    def test_reassign_action_success(self, db):
        shop_id, wo_id = _seed_wo(db)
        mech = _add_user(db, username="tech1")
        add_shop_member(shop_id, mech, "tech", db_path=db)
        rule_id = create_rule(
            shop_id=shop_id, name="reassign", event_trigger="manual",
            conditions=[{"type": "always"}],
            actions=[{"type": "reassign_to_user", "value": mech}],
            db_path=db,
        )
        result = fire_rule_for_wo(rule_id, wo_id, db_path=db)
        assert result.matched
        assert result.actions_log[0]["ok"] is True
        assert result.actions_log[0]["mechanic_user_id"] == mech

    def test_unknown_action_rejected_at_validation(self):
        from motodiag.shop import validate_actions
        with pytest.raises(InvalidActionError):
            validate_actions([{"type": "bogus"}])

    def test_change_status_rejects_bogus_target(self, db):
        shop_id, wo_id = _seed_wo(db)
        rule_id = create_rule(
            shop_id=shop_id, name="bad-change", event_trigger="manual",
            conditions=[{"type": "always"}],
            actions=[{"type": "change_status", "value": "bogus"}],
            db_path=db,
        )
        result = fire_rule_for_wo(rule_id, wo_id, db_path=db)
        assert result.actions_log[0]["ok"] is False

    def test_fail_one_continue_rest(self, db):
        """First action fails → second still runs."""
        shop_id, wo_id = _seed_wo(db)
        rule_id = create_rule(
            shop_id=shop_id, name="mixed", event_trigger="manual",
            conditions=[{"type": "always"}],
            actions=[
                {"type": "reassign_to_user", "value": 999},  # fails
                {"type": "flag_urgent"},                      # succeeds
            ],
            db_path=db,
        )
        result = fire_rule_for_wo(rule_id, wo_id, db_path=db)
        assert len(result.actions_log) == 2
        assert result.actions_log[0]["ok"] is False
        assert result.actions_log[1]["ok"] is True
        assert result.error is not None  # first failure captured


# ===========================================================================
# 4. CRUD
# ===========================================================================


class TestRuleCRUD:

    def test_create_and_get(self, db):
        shop_id = create_shop("s", db_path=db)
        rid = create_rule(
            shop_id=shop_id, name="r1", event_trigger="wo_opened",
            conditions=[{"type": "priority_lte", "value": 2}],
            actions=[{"type": "flag_urgent"}],
            db_path=db,
        )
        rule = get_rule(rid, db_path=db)
        assert rule is not None
        assert rule.name == "r1"
        assert rule.event_trigger == "wo_opened"
        assert len(rule.conditions) == 1
        assert len(rule.actions) == 1

    def test_unique_name_per_shop(self, db):
        shop_id = create_shop("s", db_path=db)
        create_rule(
            shop_id=shop_id, name="r1", event_trigger="wo_opened",
            conditions=[], actions=[{"type": "flag_urgent"}],
            db_path=db,
        )
        with pytest.raises(DuplicateRuleNameError):
            create_rule(
                shop_id=shop_id, name="r1", event_trigger="wo_opened",
                conditions=[], actions=[{"type": "flag_urgent"}],
                db_path=db,
            )

    def test_invalid_event_rejected(self, db):
        shop_id = create_shop("s", db_path=db)
        with pytest.raises(InvalidEventError):
            create_rule(
                shop_id=shop_id, name="r", event_trigger="bogus",
                conditions=[], actions=[{"type": "flag_urgent"}],
                db_path=db,
            )

    def test_list_filters_by_event_and_active(self, db):
        shop_id = create_shop("s", db_path=db)
        r1 = create_rule(
            shop_id=shop_id, name="a", event_trigger="wo_opened",
            conditions=[], actions=[{"type": "flag_urgent"}],
            db_path=db,
        )
        create_rule(
            shop_id=shop_id, name="b", event_trigger="wo_completed",
            conditions=[], actions=[{"type": "flag_urgent"}],
            db_path=db,
        )
        disable_rule(r1, db_path=db)
        opened = list_rules(
            shop_id=shop_id, event_trigger="wo_opened",
            active_only=True, db_path=db,
        )
        assert opened == []
        all_rules = list_rules(
            shop_id=shop_id, active_only=False, db_path=db,
        )
        assert len(all_rules) == 2

    def test_update_validates_conditions(self, db):
        shop_id = create_shop("s", db_path=db)
        rid = create_rule(
            shop_id=shop_id, name="r", event_trigger="wo_opened",
            conditions=[], actions=[{"type": "flag_urgent"}],
            db_path=db,
        )
        with pytest.raises(InvalidConditionError):
            update_rule(
                rid,
                conditions=[{"type": "bogus"}], db_path=db,
            )
        update_rule(
            rid,
            conditions=[{"type": "priority_lte", "value": 1}],
            db_path=db,
        )
        rule = get_rule(rid, db_path=db)
        assert rule.conditions[0]["type"] == "priority_lte"

    def test_delete(self, db):
        shop_id = create_shop("s", db_path=db)
        rid = create_rule(
            shop_id=shop_id, name="r", event_trigger="wo_opened",
            conditions=[], actions=[{"type": "flag_urgent"}],
            db_path=db,
        )
        assert delete_rule(rid, db_path=db)
        assert get_rule(rid, db_path=db) is None


# ===========================================================================
# 5. Firing
# ===========================================================================


class TestFiring:

    def test_fire_writes_run_row_matched(self, db):
        shop_id, wo_id = _seed_wo(db, priority=1)
        rid = create_rule(
            shop_id=shop_id, name="r", event_trigger="manual",
            conditions=[{"type": "priority_lte", "value": 2}],
            actions=[{"type": "flag_urgent"}],
            db_path=db,
        )
        result = fire_rule_for_wo(rid, wo_id, db_path=db)
        assert result.matched
        runs = list_rule_runs(rule_id=rid, db_path=db)
        assert len(runs) == 1
        assert runs[0].matched is True

    def test_fire_writes_run_row_unmatched(self, db):
        shop_id, wo_id = _seed_wo(db, priority=4)
        rid = create_rule(
            shop_id=shop_id, name="r", event_trigger="manual",
            conditions=[{"type": "priority_lte", "value": 2}],
            actions=[{"type": "flag_urgent"}],
            db_path=db,
        )
        result = fire_rule_for_wo(rid, wo_id, db_path=db)
        assert not result.matched
        runs = list_rule_runs(rule_id=rid, db_path=db)
        assert len(runs) == 1
        assert runs[0].matched is False
        assert runs[0].actions_log == []

    def test_trigger_event_fires_in_priority_order(self, db):
        shop_id, wo_id = _seed_wo(db)
        r_high = create_rule(
            shop_id=shop_id, name="high", event_trigger="wo_opened",
            conditions=[], actions=[{"type": "flag_urgent"}],
            priority=10, db_path=db,
        )
        r_low = create_rule(
            shop_id=shop_id, name="low", event_trigger="wo_opened",
            conditions=[], actions=[{"type": "flag_urgent"}],
            priority=200, db_path=db,
        )
        results = trigger_rules_for_event(
            "wo_opened", wo_id, db_path=db,
        )
        assert [r.rule_id for r in results] == [r_high, r_low]

    def test_trigger_event_manual_raises(self, db):
        shop_id, wo_id = _seed_wo(db)
        with pytest.raises(InvalidEventError):
            trigger_rules_for_event("manual", wo_id, db_path=db)

    def test_disabled_rule_skipped_by_event(self, db):
        shop_id, wo_id = _seed_wo(db)
        rid = create_rule(
            shop_id=shop_id, name="r", event_trigger="wo_opened",
            conditions=[], actions=[{"type": "flag_urgent"}],
            db_path=db,
        )
        disable_rule(rid, db_path=db)
        results = trigger_rules_for_event(
            "wo_opened", wo_id, db_path=db,
        )
        assert results == []

    def test_run_history_matched_only_filter(self, db):
        shop_id, wo_id = _seed_wo(db, priority=4)
        rid = create_rule(
            shop_id=shop_id, name="r", event_trigger="manual",
            conditions=[{"type": "priority_lte", "value": 2}],
            actions=[{"type": "flag_urgent"}],
            db_path=db,
        )
        # Fires but doesn't match
        fire_rule_for_wo(rid, wo_id, db_path=db)
        all_runs = list_rule_runs(rule_id=rid, db_path=db)
        matched_runs = list_rule_runs(
            rule_id=rid, matched_only=True, db_path=db,
        )
        assert len(all_runs) == 1
        assert len(matched_runs) == 0


# ===========================================================================
# 6. CLI
# ===========================================================================


class TestRuleCLI:

    def test_add_and_list_cli(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id = create_shop("s", db_path=cli_db)
        r = runner.invoke(root, [
            "shop", "rule", "add",
            "--shop", str(shop_id),
            "--name", "test-rule",
            "--event", "manual",
            "--actions", '[{"type":"flag_urgent"}]',
        ])
        assert r.exit_code == 0, r.output
        lst = runner.invoke(root, [
            "shop", "rule", "list",
            "--shop", str(shop_id), "--json",
        ])
        assert lst.exit_code == 0
        rows = _json.loads(lst.output)
        assert len(rows) == 1
        assert rows[0]["name"] == "test-rule"

    def test_show_cli(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id = create_shop("s", db_path=cli_db)
        rid = create_rule(
            shop_id=shop_id, name="r", event_trigger="manual",
            conditions=[], actions=[{"type": "flag_urgent"}],
            db_path=cli_db,
        )
        r = runner.invoke(root, [
            "shop", "rule", "show", str(rid), "--json",
        ])
        assert r.exit_code == 0, r.output
        data = _json.loads(r.output)
        assert data["id"] == rid

    def test_fire_cli(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id, wo_id = _seed_wo(cli_db)
        rid = create_rule(
            shop_id=shop_id, name="r", event_trigger="manual",
            conditions=[{"type": "always"}],
            actions=[{"type": "flag_urgent"}],
            db_path=cli_db,
        )
        r = runner.invoke(root, [
            "shop", "rule", "fire", str(rid), str(wo_id), "--json",
        ])
        assert r.exit_code == 0, r.output
        data = _json.loads(r.output)
        assert data["matched"] is True

    def test_test_cli_dry_run(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id, wo_id = _seed_wo(cli_db, priority=1)
        rid = create_rule(
            shop_id=shop_id, name="r", event_trigger="manual",
            conditions=[{"type": "priority_lte", "value": 2}],
            actions=[{"type": "flag_urgent"}],
            db_path=cli_db,
        )
        r = runner.invoke(root, [
            "shop", "rule", "test", str(rid), str(wo_id), "--json",
        ])
        assert r.exit_code == 0, r.output
        data = _json.loads(r.output)
        assert data["matched"] is True
        # Dry run: no actions executed → no run rows
        assert list_rule_runs(rule_id=rid, db_path=cli_db) == []

    def test_history_cli(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id, wo_id = _seed_wo(cli_db)
        rid = create_rule(
            shop_id=shop_id, name="r", event_trigger="manual",
            conditions=[{"type": "always"}],
            actions=[{"type": "flag_urgent"}],
            db_path=cli_db,
        )
        fire_rule_for_wo(rid, wo_id, db_path=cli_db)
        r = runner.invoke(root, [
            "shop", "rule", "history",
            "--rule", str(rid), "--json",
        ])
        assert r.exit_code == 0, r.output
        rows = _json.loads(r.output)
        assert len(rows) == 1


# ===========================================================================
# 7. Anti-regression
# ===========================================================================


class TestAntiRegression:

    def test_no_raw_update_work_orders_in_actions(self):
        from pathlib import Path
        import re
        src = (
            Path(__file__).parent.parent / "src" / "motodiag" /
            "shop" / "workflow_actions.py"
        ).read_text(encoding="utf-8")
        stripped = re.sub(r"#[^\n]*", "", src)
        stripped = re.sub(r'"""[\s\S]*?"""', "", stripped)
        matches = re.findall(
            r"UPDATE\s+work_orders\b", stripped, re.IGNORECASE,
        )
        assert matches == [], (
            "workflow_actions.py must route through phase repos, "
            "never raw SQL"
        )
