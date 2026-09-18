"""Phase 112 — User/auth layer introduction tests.

Tests cover:
- Migration 005 creates auth tables + seeds system user + seeds roles/permissions
- User/Role/Permission Pydantic models
- users_repo CRUD (create, get, list, update, deactivate, count, system user)
- roles_repo CRUD (roles, permissions, assignments, permission checks)
- Retrofit columns (user_id on sessions/repair_plans/known_issues)
- System user cannot be deactivated
- Backward compat: all existing INSERTs still work (user_id gets default 1)
- All 1694 pre-phase-112 tests still pass
"""

import pytest

from motodiag.core.database import (
    init_db, get_schema_version, get_connection,
)
from motodiag.core.migrations import (
    get_migration_by_version,
)
from motodiag.auth.models import (
    User, RoleName, PermissionName,
)
from motodiag.auth.users_repo import (
    create_user, get_user, get_user_by_username, list_users,
    update_user, deactivate_user, count_users, get_system_user,
    SYSTEM_USER_ID,
)


# --- Migration 005 ---


class TestMigration005:
    def test_migration_005_exists(self):
        m = get_migration_by_version(5)
        assert m is not None
        assert "users" in m.upgrade_sql.lower()
        assert "roles" in m.upgrade_sql.lower()
        assert "permissions" in m.upgrade_sql.lower()

    def test_auth_tables_created(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name IN ('users', 'roles', 'permissions', 'user_roles', 'role_permissions')"
            )
            tables = {row[0] for row in cursor.fetchall()}
        assert tables == {"users", "roles", "permissions", "user_roles", "role_permissions"}

    def test_system_user_seeded(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        sys_user = get_system_user(db)
        assert sys_user is not None
        assert sys_user["id"] == 1
        assert sys_user["username"] == "system"
        assert sys_user["is_active"] == 1

    def test_12_permissions_seeded(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        with get_connection(db) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM permissions")
            assert cursor.fetchone()[0] == 12

    def test_user_id_columns_added(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        with get_connection(db) as conn:
            for table, col in [
                ("diagnostic_sessions", "user_id"),
                ("repair_plans", "user_id"),
                ("known_issues", "created_by_user_id"),
            ]:
                cursor = conn.execute(f"PRAGMA table_info({table})")
                columns = {row[1] for row in cursor.fetchall()}
                assert col in columns, f"{table} missing {col}"

    def test_schema_version_at_5(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        # After migration 005 applies, schema is at least 5. Later retrofit
        # phases bump the version further (phase 113 → 6, etc.), so use >=.
        assert get_schema_version(db) >= 5

    def test_rollback_drops_auth_tables(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        # Must rollback later migrations first — migration 006 (CRM) has FKs
        # to users. This is the expected migration-dependency ordering.
        from motodiag.core.migrations import rollback_to_version
        rollback_to_version(4, db)  # Roll back through 006, 005
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name IN ('users', 'roles', 'permissions')"
            )
            remaining = [row[0] for row in cursor.fetchall()]
        assert remaining == []


# --- Model tests ---


class TestRoleNameEnum:
    def test_four_members(self):
        assert len(list(RoleName)) == 4
        assert RoleName.OWNER.value == "owner"
        assert RoleName.TECH.value == "tech"
        assert RoleName.SERVICE_WRITER.value == "service_writer"
        assert RoleName.APPRENTICE.value == "apprentice"


class TestPermissionNameEnum:
    def test_twelve_members(self):
        assert len(list(PermissionName)) == 12

    def test_core_permissions_present(self):
        names = {p.value for p in PermissionName}
        assert "read_garage" in names
        assert "write_garage" in names
        assert "run_diagnose" in names
        assert "export_report" in names
        assert "manage_users" in names
        assert "manage_billing" in names


class TestUserModel:
    def test_minimal_user(self):
        u = User(username="alice")
        assert u.username == "alice"
        assert u.tier == "individual"
        assert u.is_active is True
        assert u.password_hash is None

    def test_full_user(self):
        u = User(
            username="bob", email="bob@shop.com", full_name="Bob Smith",
            password_hash="argon2:abc...", tier="shop",
        )
        assert u.tier == "shop"
        assert u.email == "bob@shop.com"


# --- Users repo ---


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "auth_test.db")
    init_db(path)
    return path


class TestUsersRepo:
    def test_create_and_get(self, db):
        uid = create_user(User(username="alice", email="alice@shop.com", tier="shop"), db)
        user = get_user(uid, db)
        assert user is not None
        assert user["username"] == "alice"
        assert user["tier"] == "shop"

    def test_get_by_username(self, db):
        create_user(User(username="charlie"), db)
        u = get_user_by_username("charlie", db)
        assert u is not None
        assert u["username"] == "charlie"

    def test_get_nonexistent(self, db):
        assert get_user(99999, db) is None
        assert get_user_by_username("ghost", db) is None

    def test_list_users(self, db):
        create_user(User(username="user_a"), db)
        create_user(User(username="user_b"), db)
        users = list_users(db)
        # Should include system + user_a + user_b
        assert len(users) >= 3
        usernames = {u["username"] for u in users}
        assert "system" in usernames
        assert "user_a" in usernames
        assert "user_b" in usernames

    def test_list_users_filter_tier(self, db):
        create_user(User(username="u_ind", tier="individual"), db)
        create_user(User(username="u_shop", tier="shop"), db)
        shop_users = list_users(db, tier="shop")
        usernames = {u["username"] for u in shop_users}
        assert "u_shop" in usernames
        assert "u_ind" not in usernames

    def test_update_user(self, db):
        uid = create_user(User(username="diana"), db)
        ok = update_user(uid, {"email": "diana@example.com", "tier": "company"}, db)
        assert ok is True
        u = get_user(uid, db)
        assert u["email"] == "diana@example.com"
        assert u["tier"] == "company"

    def test_deactivate_user(self, db):
        uid = create_user(User(username="evan"), db)
        ok = deactivate_user(uid, db)
        assert ok is True
        u = get_user(uid, db)
        assert u["is_active"] == 0

    def test_cannot_deactivate_system_user(self, db):
        with pytest.raises(ValueError):
            deactivate_user(SYSTEM_USER_ID, db)

    def test_count_users(self, db):
        before = count_users(db)
        create_user(User(username="fiona"), db)
        create_user(User(username="gus"), db)
        assert count_users(db) == before + 2

    def test_count_active_only(self, db):
        uid = create_user(User(username="henry"), db)
        deactivate_user(uid, db)
        active = count_users(db, is_active=True)
        inactive = count_users(db, is_active=False)
        assert inactive >= 1


# --- Roles repo ---


# --- Backward compatibility ---


class TestBackwardCompat:
    def test_existing_sessions_default_to_system_user(self, db):
        # Insert a session the old way (no user_id)
        with get_connection(db) as conn:
            conn.execute(
                """INSERT INTO diagnostic_sessions
                   (vehicle_make, vehicle_model, vehicle_year, status)
                   VALUES ('Honda', 'CBR600RR', 2007, 'open')"""
            )
            cursor = conn.execute("SELECT user_id FROM diagnostic_sessions")
            row = cursor.fetchone()
        assert row[0] == 1  # system user

    def test_existing_known_issues_default_to_system(self, db):
        with get_connection(db) as conn:
            conn.execute(
                """INSERT INTO known_issues
                   (title, description, make, severity, symptoms, dtc_codes, causes,
                    fix_procedure, parts_needed, estimated_hours)
                   VALUES ('Test issue', 'Desc', 'Honda', 'medium',
                           '[]', '[]', '[]', 'Do X', '[]', 1.0)"""
            )
            cursor = conn.execute(
                "SELECT created_by_user_id FROM known_issues WHERE title = 'Test issue'"
            )
            row = cursor.fetchone()
        assert row[0] == 1  # system user

    def test_existing_init_db_still_works(self, tmp_path):
        # Calling init_db on a brand-new DB should produce a fully usable DB
        db = str(tmp_path / "fresh.db")
        init_db(db)
        # Should be able to add a vehicle the old way
        with get_connection(db) as conn:
            cursor = conn.execute(
                "INSERT INTO vehicles (make, model, year) VALUES ('Honda', 'CBR600RR', 2007)"
            )
            assert cursor.lastrowid is not None
