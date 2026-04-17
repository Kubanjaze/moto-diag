"""Phase 113 — Customer/CRM foundation tests.

Tests cover:
- Migration 006 creates customers + customer_bikes tables
- Unassigned placeholder customer seeded at id=1
- customer_id column added to vehicles
- Existing vehicles default to unassigned customer (id=1)
- Customer CRUD + search
- Customer-bike linking with ownership history
- Ownership transfer (demote owner to previous_owner + assign new owner)
- Backward compat: all existing tests still pass
"""

import pytest

from motodiag.core.database import (
    init_db, get_schema_version, SCHEMA_VERSION, get_connection,
)
from motodiag.core.migrations import get_migration_by_version, rollback_migration
from motodiag.crm.models import Customer, CustomerRelationship
from motodiag.crm.customer_repo import (
    create_customer, get_customer, get_unassigned_customer,
    list_customers, search_customers, update_customer,
    deactivate_customer, count_customers,
    UNASSIGNED_CUSTOMER_ID,
)
from motodiag.crm.customer_bikes_repo import (
    link_customer_bike, unlink_customer_bike,
    list_bikes_for_customer, list_customers_for_bike,
    get_current_owner, transfer_ownership,
)
from motodiag.core.models import VehicleBase
from motodiag.vehicles.registry import add_vehicle


# --- Migration 006 ---


class TestMigration006:
    def test_migration_006_exists(self):
        m = get_migration_by_version(6)
        assert m is not None
        assert "customers" in m.upgrade_sql.lower()
        assert "customer_bikes" in m.upgrade_sql.lower()

    def test_customers_table_created(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='customers'"
            )
            assert cursor.fetchone() is not None

    def test_customer_bikes_table_created(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='customer_bikes'"
            )
            assert cursor.fetchone() is not None

    def test_unassigned_customer_seeded(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        unassigned = get_unassigned_customer(db)
        assert unassigned is not None
        assert unassigned["id"] == 1
        assert unassigned["name"] == "Unassigned"
        assert unassigned["owner_user_id"] == 1  # Owned by system user

    def test_customer_id_added_to_vehicles(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        with get_connection(db) as conn:
            cursor = conn.execute("PRAGMA table_info(vehicles)")
            columns = {row[1] for row in cursor.fetchall()}
        assert "customer_id" in columns

    def test_existing_vehicles_default_to_unassigned(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        vid = add_vehicle(VehicleBase(make="Honda", model="CBR600RR", year=2007), db)
        with get_connection(db) as conn:
            cursor = conn.execute("SELECT customer_id FROM vehicles WHERE id = ?", (vid,))
            assert cursor.fetchone()["customer_id"] == UNASSIGNED_CUSTOMER_ID

    def test_schema_version_at_6(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        # After migration 006 applies, schema is at least 6. Later retrofit
        # phases bump further; use >= for forward compatibility.
        assert get_schema_version(db) >= 6

    def test_rollback_drops_crm_tables(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        m = get_migration_by_version(6)
        rollback_migration(m, db)
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name IN ('customers', 'customer_bikes')"
            )
            assert cursor.fetchall() == []


# --- CustomerRelationship enum ---


class TestCustomerRelationship:
    def test_members(self):
        assert CustomerRelationship.OWNER.value == "owner"
        assert CustomerRelationship.PREVIOUS_OWNER.value == "previous_owner"
        assert CustomerRelationship.INTERESTED.value == "interested"


# --- Customer model ---


class TestCustomerModel:
    def test_minimal(self):
        c = Customer(name="John Doe")
        assert c.name == "John Doe"
        assert c.owner_user_id == 1  # Defaults to system
        assert c.is_active is True

    def test_full(self):
        c = Customer(
            owner_user_id=5, name="Jane Smith",
            email="jane@example.com", phone="555-1234",
            address="123 Main St", notes="VIP",
        )
        assert c.owner_user_id == 5
        assert c.phone == "555-1234"


# --- Customer repo ---


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "crm_test.db")
    init_db(path)
    return path


class TestCustomerRepo:
    def test_create_and_get(self, db):
        cid = create_customer(
            Customer(owner_user_id=1, name="Alice", email="alice@shop.com"),
            db,
        )
        c = get_customer(cid, db)
        assert c["name"] == "Alice"
        assert c["email"] == "alice@shop.com"

    def test_list_customers(self, db):
        create_customer(Customer(owner_user_id=1, name="Alice"), db)
        create_customer(Customer(owner_user_id=1, name="Bob"), db)
        customers = list_customers(db)
        # Includes unassigned + Alice + Bob
        assert len(customers) == 3

    def test_list_by_owner(self, db):
        # Create two users first so FK constraints pass
        from motodiag.auth.users_repo import create_user
        from motodiag.auth.models import User
        u2 = create_user(User(username="shop2"), db)
        u3 = create_user(User(username="shop3"), db)
        create_customer(Customer(owner_user_id=u2, name="Shop2 Customer"), db)
        create_customer(Customer(owner_user_id=u3, name="Shop3 Customer"), db)
        shop2 = list_customers(db, owner_user_id=u2)
        shop3 = list_customers(db, owner_user_id=u3)
        assert len(shop2) == 1
        assert len(shop3) == 1
        assert shop2[0]["name"] == "Shop2 Customer"

    def test_search_by_email(self, db):
        create_customer(Customer(name="Carol", email="carol@example.com"), db)
        results = search_customers("carol@", db)
        assert len(results) == 1
        assert results[0]["name"] == "Carol"

    def test_search_by_phone(self, db):
        create_customer(Customer(name="Dan", phone="555-9876"), db)
        results = search_customers("555-9876", db)
        assert len(results) == 1

    def test_search_by_name(self, db):
        create_customer(Customer(name="Emma Johnson"), db)
        results = search_customers("Johnson", db)
        assert any(c["name"] == "Emma Johnson" for c in results)

    def test_update_customer(self, db):
        cid = create_customer(Customer(name="Frank"), db)
        ok = update_customer(cid, {"email": "frank@shop.com", "phone": "555-0001"}, db)
        assert ok is True
        c = get_customer(cid, db)
        assert c["email"] == "frank@shop.com"

    def test_cannot_rename_unassigned(self, db):
        with pytest.raises(ValueError):
            update_customer(UNASSIGNED_CUSTOMER_ID, {"name": "New Name"}, db)

    def test_cannot_deactivate_unassigned(self, db):
        with pytest.raises(ValueError):
            deactivate_customer(UNASSIGNED_CUSTOMER_ID, db)

    def test_deactivate_customer(self, db):
        cid = create_customer(Customer(name="Gabby"), db)
        ok = deactivate_customer(cid, db)
        assert ok is True
        c = get_customer(cid, db)
        assert c["is_active"] == 0

    def test_count_customers(self, db):
        before = count_customers(db)
        create_customer(Customer(name="Hank"), db)
        create_customer(Customer(name="Ivy"), db)
        assert count_customers(db) == before + 2


# --- Customer-bike linking ---


class TestCustomerBikes:
    def _setup(self, db) -> tuple[int, int]:
        """Create a customer + vehicle, return (customer_id, vehicle_id)."""
        cid = create_customer(Customer(name="Test Customer"), db)
        vid = add_vehicle(VehicleBase(make="Honda", model="CBR600RR", year=2007), db)
        return cid, vid

    def test_link_as_owner(self, db):
        cid, vid = self._setup(db)
        link_customer_bike(cid, vid, CustomerRelationship.OWNER, db_path=db)
        links = list_customers_for_bike(vid, db_path=db)
        assert len(links) == 1
        assert links[0]["cb_relationship"] == "owner"

    def test_link_idempotent(self, db):
        cid, vid = self._setup(db)
        link_customer_bike(cid, vid, db_path=db)
        link_customer_bike(cid, vid, db_path=db)  # Duplicate
        links = list_customers_for_bike(vid, db_path=db)
        assert len(links) == 1

    def test_multiple_relationships_different_types(self, db):
        cid, vid = self._setup(db)
        link_customer_bike(cid, vid, CustomerRelationship.PREVIOUS_OWNER, db_path=db)
        link_customer_bike(cid, vid, CustomerRelationship.INTERESTED, db_path=db)
        links = list_customers_for_bike(vid, db_path=db)
        assert len(links) == 2

    def test_unlink_specific_relationship(self, db):
        cid, vid = self._setup(db)
        link_customer_bike(cid, vid, CustomerRelationship.OWNER, db_path=db)
        link_customer_bike(cid, vid, CustomerRelationship.INTERESTED, db_path=db)
        removed = unlink_customer_bike(cid, vid, CustomerRelationship.INTERESTED, db_path=db)
        assert removed == 1
        links = list_customers_for_bike(vid, db_path=db)
        assert len(links) == 1
        assert links[0]["cb_relationship"] == "owner"

    def test_unlink_all_relationships(self, db):
        cid, vid = self._setup(db)
        link_customer_bike(cid, vid, CustomerRelationship.OWNER, db_path=db)
        link_customer_bike(cid, vid, CustomerRelationship.INTERESTED, db_path=db)
        removed = unlink_customer_bike(cid, vid, db_path=db)
        assert removed == 2

    def test_list_bikes_for_customer(self, db):
        cid = create_customer(Customer(name="Multi-bike owner"), db)
        v1 = add_vehicle(VehicleBase(make="Honda", model="CBR600RR", year=2007), db)
        v2 = add_vehicle(VehicleBase(make="Kawasaki", model="Ninja 400", year=2019), db)
        link_customer_bike(cid, v1, db_path=db)
        link_customer_bike(cid, v2, db_path=db)
        bikes = list_bikes_for_customer(cid, db_path=db)
        assert len(bikes) == 2

    def test_list_bikes_filter_by_relationship(self, db):
        cid = create_customer(Customer(name="Test"), db)
        v1 = add_vehicle(VehicleBase(make="Honda", model="A", year=2007), db)
        v2 = add_vehicle(VehicleBase(make="Honda", model="B", year=2010), db)
        link_customer_bike(cid, v1, CustomerRelationship.OWNER, db_path=db)
        link_customer_bike(cid, v2, CustomerRelationship.PREVIOUS_OWNER, db_path=db)

        current = list_bikes_for_customer(cid, CustomerRelationship.OWNER, db_path=db)
        past = list_bikes_for_customer(cid, CustomerRelationship.PREVIOUS_OWNER, db_path=db)
        assert len(current) == 1
        assert len(past) == 1

    def test_get_current_owner(self, db):
        cid, vid = self._setup(db)
        link_customer_bike(cid, vid, CustomerRelationship.OWNER, db_path=db)
        owner = get_current_owner(vid, db_path=db)
        assert owner is not None
        assert owner["id"] == cid

    def test_get_current_owner_none(self, db):
        _, vid = self._setup(db)
        # No owner linked
        owner = get_current_owner(vid, db_path=db)
        assert owner is None


class TestOwnershipTransfer:
    def test_transfer_demotes_old_owner(self, db):
        old = create_customer(Customer(name="Old Owner"), db)
        new = create_customer(Customer(name="New Owner"), db)
        vid = add_vehicle(VehicleBase(make="Honda", model="CBR600RR", year=2007), db)

        link_customer_bike(old, vid, CustomerRelationship.OWNER, db_path=db)
        transfer_ownership(vid, old, new, notes="Sold to new customer", db_path=db)

        # Old is now previous_owner
        old_links = list_bikes_for_customer(old, db_path=db)
        assert len(old_links) == 1
        assert old_links[0]["cb_relationship"] == "previous_owner"

        # New is current owner
        new_owner = get_current_owner(vid, db_path=db)
        assert new_owner["id"] == new

    def test_ownership_history_preserved(self, db):
        a = create_customer(Customer(name="A"), db)
        b = create_customer(Customer(name="B"), db)
        c = create_customer(Customer(name="C"), db)
        vid = add_vehicle(VehicleBase(make="Kawasaki", model="ZX-6R", year=2015), db)

        # A owns first, transfers to B, transfers to C
        link_customer_bike(a, vid, CustomerRelationship.OWNER, db_path=db)
        transfer_ownership(vid, a, b, db_path=db)
        transfer_ownership(vid, b, c, db_path=db)

        history = list_customers_for_bike(vid, db_path=db)
        relationships = {h["name"]: h["cb_relationship"] for h in history}
        assert relationships["A"] == "previous_owner"
        assert relationships["B"] == "previous_owner"
        assert relationships["C"] == "owner"


# --- Backward compat ---


class TestBackwardCompat:
    def test_existing_vehicle_inserts_still_work(self, db):
        # The old INSERT (no customer_id) must still work
        vid = add_vehicle(VehicleBase(make="Honda", model="CBR600RR", year=2007), db)
        with get_connection(db) as conn:
            row = conn.execute(
                "SELECT customer_id FROM vehicles WHERE id = ?", (vid,)
            ).fetchone()
        assert row["customer_id"] == 1  # Unassigned placeholder

    def test_vehicle_crud_unchanged(self, db):
        """Existing vehicles/registry CRUD still works without customer awareness."""
        from motodiag.vehicles.registry import list_vehicles, count_vehicles
        add_vehicle(VehicleBase(make="Honda", model="X", year=2010), db)
        add_vehicle(VehicleBase(make="Honda", model="Y", year=2012), db)
        assert count_vehicles(db) == 2
        assert len(list_vehicles(db_path=db)) == 2
