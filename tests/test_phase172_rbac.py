"""Phase 172 — Multi-mechanic assignment + shop-scoped RBAC tests.

Five test classes across ~31 tests:

- :class:`TestMigration035` (4) — schema_version, tables + CHECK +
  indexes present, rollback.
- :class:`TestMembership` (10) — add/list/get/set-role/deactivate/
  reactivate; idempotent add reactivates; bogus role raises.
- :class:`TestShopPermissions` (5) — owner has everything, tech has
  write_garage, apprentice denied manage_shop, inactive member denied,
  require_shop_permission raises.
- :class:`TestReassignment` (7) — reassign logs history, closes prior
  row, updates work_orders via Phase 161 whitelist (mock-patch audit),
  unassign preserves history, non-shop mechanic raises, terminal WO
  raises, current_assignment returns open row.
- :class:`TestRbacCLI` (5) — member add/list/set-role/deactivate,
  work-order reassign/assignments CLI round-trip.

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
    InvalidRoleError, MechanicNotInShopError,
    PermissionDenied, ShopMembershipNotFoundError,
    add_shop_member, cancel_work_order, complete_work_order,
    create_shop, create_work_order, current_assignment,
    deactivate_member, get_shop_member, has_shop_permission,
    list_shop_mechanics, list_shop_members,
    list_work_order_assignments, mechanic_workload,
    open_work_order, reactivate_member, reassign_work_order,
    require_shop_permission, seed_first_owner, set_member_role,
    start_work,
)
from motodiag.shop.work_order_repo import InvalidWorkOrderTransition


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
    path = str(tmp_path / "phase172.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase172_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    yield path
    reset_settings()


def _add_user(db_path, username="bob", full_name="Bob Tech",
              tier="individual"):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO users (username, full_name, tier, is_active)
               VALUES (?, ?, ?, 1)""",
            (username, full_name, tier),
        )
        return cursor.lastrowid


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


def _seed_shop_with_user(db_path, role="tech", username="bob"):
    shop_id = create_shop("s", db_path=db_path)
    user_id = _add_user(db_path, username=username)
    add_shop_member(shop_id, user_id, role, db_path=db_path)
    return shop_id, user_id


def _seed_wo(db_path, shop_id=None):
    if shop_id is None:
        shop_id = create_shop("s", db_path=db_path)
    c = _add_customer(db_path)
    v = _add_vehicle(db_path)
    wo_id = create_work_order(
        shop_id=shop_id, vehicle_id=v, customer_id=c,
        title="service", estimated_hours=1.0, db_path=db_path,
    )
    open_work_order(wo_id, db_path=db_path)
    return shop_id, wo_id


# ===========================================================================
# 1. Migration 035
# ===========================================================================


class TestMigration035:

    def test_schema_version_bumped(self, db):
        assert SCHEMA_VERSION >= 35

    def test_tables_created(self, db):
        assert table_exists("shop_members", db)
        assert table_exists("work_order_assignments", db)

    def test_role_check_enforced(self, db):
        shop_id = create_shop("s", db_path=db)
        uid = _add_user(db)
        with pytest.raises(sqlite3.IntegrityError):
            with get_connection(db) as conn:
                conn.execute(
                    "INSERT INTO shop_members "
                    "(user_id, shop_id, role) VALUES (?, ?, 'bogus')",
                    (uid, shop_id),
                )

    def test_rollback_drops_tables(self, tmp_path):
        path = str(tmp_path / "rollback.db")
        init_db(path)
        assert table_exists("shop_members", path)
        rollback_to_version(34, path)
        assert not table_exists("shop_members", path)
        assert not table_exists("work_order_assignments", path)
        # Prior tables preserved
        assert table_exists("customer_notifications", path)


# ===========================================================================
# 2. Membership CRUD
# ===========================================================================


class TestMembership:

    def test_add_creates_row(self, db):
        shop_id = create_shop("s", db_path=db)
        uid = _add_user(db)
        add_shop_member(shop_id, uid, "tech", db_path=db)
        m = get_shop_member(shop_id, uid, db_path=db)
        assert m is not None
        assert m.role == "tech"
        assert m.is_active

    def test_add_is_idempotent_and_reactivates(self, db):
        shop_id = create_shop("s", db_path=db)
        uid = _add_user(db)
        add_shop_member(shop_id, uid, "tech", db_path=db)
        deactivate_member(shop_id, uid, db_path=db)
        add_shop_member(shop_id, uid, "owner", db_path=db)
        m = get_shop_member(shop_id, uid, db_path=db)
        assert m.is_active is True
        assert m.role == "owner"

    def test_add_rejects_bogus_role(self, db):
        shop_id = create_shop("s", db_path=db)
        uid = _add_user(db)
        with pytest.raises(InvalidRoleError):
            add_shop_member(shop_id, uid, "bogus", db_path=db)

    def test_list_members(self, db):
        shop_id = create_shop("s", db_path=db)
        u1 = _add_user(db, username="a")
        u2 = _add_user(db, username="b")
        add_shop_member(shop_id, u1, "tech", db_path=db)
        add_shop_member(shop_id, u2, "apprentice", db_path=db)
        members = list_shop_members(shop_id, db_path=db)
        assert len(members) == 2

    def test_list_filters_by_role(self, db):
        shop_id = create_shop("s", db_path=db)
        u1 = _add_user(db, username="a")
        u2 = _add_user(db, username="b")
        add_shop_member(shop_id, u1, "tech", db_path=db)
        add_shop_member(shop_id, u2, "apprentice", db_path=db)
        techs = list_shop_members(shop_id, role="tech", db_path=db)
        assert len(techs) == 1
        assert techs[0].user_id == u1

    def test_list_excludes_inactive_by_default(self, db):
        shop_id = create_shop("s", db_path=db)
        uid = _add_user(db)
        add_shop_member(shop_id, uid, "tech", db_path=db)
        deactivate_member(shop_id, uid, db_path=db)
        active = list_shop_members(shop_id, db_path=db)
        assert active == []
        all_m = list_shop_members(
            shop_id, active_only=False, db_path=db,
        )
        assert len(all_m) == 1

    def test_set_role_raises_when_missing(self, db):
        shop_id = create_shop("s", db_path=db)
        with pytest.raises(ShopMembershipNotFoundError):
            set_member_role(shop_id, 9999, "tech", db_path=db)

    def test_set_role_rejects_bogus(self, db):
        shop_id, uid = _seed_shop_with_user(db)
        with pytest.raises(InvalidRoleError):
            set_member_role(shop_id, uid, "bogus", db_path=db)

    def test_deactivate_reactivate_roundtrip(self, db):
        shop_id, uid = _seed_shop_with_user(db)
        assert deactivate_member(shop_id, uid, db_path=db)
        assert get_shop_member(shop_id, uid, db_path=db).is_active is False
        assert reactivate_member(shop_id, uid, db_path=db)
        assert get_shop_member(shop_id, uid, db_path=db).is_active is True

    def test_seed_first_owner_idempotent(self, db):
        shop_id = create_shop("s", db_path=db)
        uid = _add_user(db)
        assert seed_first_owner(shop_id, uid, db_path=db) is True
        # Second call is a no-op
        assert seed_first_owner(shop_id, uid, db_path=db) is False
        m = get_shop_member(shop_id, uid, db_path=db)
        assert m.role == "owner"


# ===========================================================================
# 3. Shop-scoped permissions
# ===========================================================================


class TestShopPermissions:

    def test_owner_has_manage_shop(self, db):
        shop_id, uid = _seed_shop_with_user(db, role="owner")
        assert has_shop_permission(
            shop_id, uid, "manage_shop", db_path=db,
        )

    def test_tech_has_write_garage(self, db):
        shop_id, uid = _seed_shop_with_user(db, role="tech")
        assert has_shop_permission(
            shop_id, uid, "write_garage", db_path=db,
        )

    def test_apprentice_denied_manage_shop(self, db):
        shop_id, uid = _seed_shop_with_user(db, role="apprentice")
        assert not has_shop_permission(
            shop_id, uid, "manage_shop", db_path=db,
        )

    def test_inactive_member_denied(self, db):
        shop_id, uid = _seed_shop_with_user(db, role="owner")
        deactivate_member(shop_id, uid, db_path=db)
        assert not has_shop_permission(
            shop_id, uid, "manage_shop", db_path=db,
        )

    def test_require_shop_permission_raises(self, db):
        shop_id, uid = _seed_shop_with_user(db, role="apprentice")
        with pytest.raises(PermissionDenied):
            require_shop_permission(
                shop_id, uid, "manage_shop", db_path=db,
            )


# ===========================================================================
# 4. Work-order reassignment
# ===========================================================================


class TestReassignment:

    def test_reassign_logs_history(self, db):
        shop_id, wo_id = _seed_wo(db)
        mech = _add_user(db, username="tech1")
        add_shop_member(shop_id, mech, "tech", db_path=db)
        aid = reassign_work_order(
            wo_id, new_mechanic_user_id=mech, db_path=db,
        )
        assert aid > 0
        history = list_work_order_assignments(wo_id, db_path=db)
        assert len(history) == 1
        assert history[0].mechanic_user_id == mech

    def test_reassign_closes_prior_row(self, db):
        shop_id, wo_id = _seed_wo(db)
        m1 = _add_user(db, username="t1")
        m2 = _add_user(db, username="t2")
        add_shop_member(shop_id, m1, "tech", db_path=db)
        add_shop_member(shop_id, m2, "tech", db_path=db)
        reassign_work_order(wo_id, m1, db_path=db)
        reassign_work_order(wo_id, m2, db_path=db)
        history = list_work_order_assignments(wo_id, db_path=db)
        assert len(history) == 2
        # Older row's unassigned_at stamped
        older = [h for h in history if h.mechanic_user_id == m1][0]
        assert older.unassigned_at is not None
        # Newer row still open
        newer = [h for h in history if h.mechanic_user_id == m2][0]
        assert newer.unassigned_at is None

    def test_reassign_updates_wo_via_whitelist(self, db):
        """Write-back routes through Phase 161 update_work_order
        whitelist — not raw SQL. Mock-patch audit."""
        shop_id, wo_id = _seed_wo(db)
        mech = _add_user(db, username="tech1")
        add_shop_member(shop_id, mech, "tech", db_path=db)
        with patch(
            "motodiag.shop.rbac.update_work_order",
            wraps=__import__(
                "motodiag.shop.rbac", fromlist=["update_work_order"],
            ).update_work_order,
        ) as mocked:
            reassign_work_order(wo_id, mech, db_path=db)
            mocked.assert_called_once()
            call = mocked.call_args
            assert call[0][0] == wo_id
            assert call[0][1] == {
                "assigned_mechanic_user_id": mech,
            }

    def test_unassign_preserves_history(self, db):
        shop_id, wo_id = _seed_wo(db)
        mech = _add_user(db, username="tech1")
        add_shop_member(shop_id, mech, "tech", db_path=db)
        reassign_work_order(wo_id, mech, db_path=db)
        reassign_work_order(wo_id, None, reason="gone", db_path=db)
        history = list_work_order_assignments(wo_id, db_path=db)
        assert len(history) == 2
        # Current is the NULL-assignment row
        curr = current_assignment(wo_id, db_path=db)
        assert curr is not None
        assert curr.mechanic_user_id is None

    def test_reassign_to_non_shop_member_raises(self, db):
        shop_id, wo_id = _seed_wo(db)
        outsider = _add_user(db, username="outside")
        # outsider is not a member of this shop
        with pytest.raises(MechanicNotInShopError):
            reassign_work_order(wo_id, outsider, db_path=db)

    def test_reassign_to_apprentice_raises(self, db):
        shop_id, wo_id = _seed_wo(db)
        app = _add_user(db, username="app")
        add_shop_member(shop_id, app, "apprentice", db_path=db)
        # apprentice is not in ELIGIBLE_ASSIGN_ROLES
        with pytest.raises(MechanicNotInShopError):
            reassign_work_order(wo_id, app, db_path=db)

    def test_reassign_terminal_wo_raises(self, db):
        shop_id, wo_id = _seed_wo(db)
        start_work(wo_id, db_path=db)
        complete_work_order(wo_id, actual_hours=1.0, db_path=db)
        mech = _add_user(db, username="tech1")
        add_shop_member(shop_id, mech, "tech", db_path=db)
        with pytest.raises(InvalidWorkOrderTransition):
            reassign_work_order(wo_id, mech, db_path=db)


# ===========================================================================
# 5. CLI round-trip
# ===========================================================================


class TestRbacCLI:

    def test_member_add_list(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id = create_shop("s", db_path=cli_db)
        uid = _add_user(cli_db, username="bob")
        r = runner.invoke(root, [
            "shop", "member", "add",
            "--shop", str(shop_id), "--user", str(uid),
            "--role", "tech",
        ])
        assert r.exit_code == 0, r.output
        lst = runner.invoke(root, [
            "shop", "member", "list",
            "--shop", str(shop_id), "--json",
        ])
        assert lst.exit_code == 0
        rows = _json.loads(lst.output)
        assert len(rows) == 1
        assert rows[0]["user_id"] == uid

    def test_member_set_role_cli(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id, uid = _seed_shop_with_user(cli_db, role="tech")
        r = runner.invoke(root, [
            "shop", "member", "set-role",
            "--shop", str(shop_id), "--user", str(uid),
            "--role", "owner",
        ])
        assert r.exit_code == 0, r.output
        m = get_shop_member(shop_id, uid, db_path=cli_db)
        assert m.role == "owner"

    def test_member_deactivate_cli(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id, uid = _seed_shop_with_user(cli_db)
        r = runner.invoke(root, [
            "shop", "member", "deactivate",
            "--shop", str(shop_id), "--user", str(uid),
        ])
        assert r.exit_code == 0, r.output

    def test_work_order_reassign_cli(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id, wo_id = _seed_wo(cli_db)
        mech = _add_user(cli_db, username="tech1")
        add_shop_member(shop_id, mech, "tech", db_path=cli_db)
        r = runner.invoke(root, [
            "shop", "work-order", "reassign", str(wo_id),
            "--to", str(mech), "--reason", "workload rebalance",
        ])
        assert r.exit_code == 0, r.output

    def test_work_order_assignments_cli(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id, wo_id = _seed_wo(cli_db)
        mech = _add_user(cli_db, username="tech1")
        add_shop_member(shop_id, mech, "tech", db_path=cli_db)
        reassign_work_order(wo_id, mech, db_path=cli_db)
        r = runner.invoke(root, [
            "shop", "work-order", "assignments", str(wo_id),
            "--json",
        ])
        assert r.exit_code == 0, r.output
        rows = _json.loads(r.output)
        assert len(rows) == 1


# ===========================================================================
# 6. Anti-regression
# ===========================================================================


class TestAntiRegression:

    def test_no_raw_update_work_orders_in_rbac(self):
        """Phase 161 whitelist discipline — rbac must not use raw SQL."""
        from pathlib import Path
        src = (
            Path(__file__).parent.parent / "src" / "motodiag" /
            "shop" / "rbac.py"
        ).read_text(encoding="utf-8")
        import re
        # Strip comments (anything after `#` on a line) + docstrings
        # before the check — comments mentioning the rule are fine.
        without_comments = re.sub(r"#[^\n]*", "", src)
        without_docstrings = re.sub(
            r'"""[\s\S]*?"""', "", without_comments,
        )
        matches = re.findall(
            r"UPDATE\s+work_orders\b",
            without_docstrings, re.IGNORECASE,
        )
        assert matches == [], (
            "rbac.py must write to work_orders via Phase 161 "
            "update_work_order whitelist, not raw SQL"
        )
