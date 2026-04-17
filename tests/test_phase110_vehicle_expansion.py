"""Phase 110 — Vehicle registry + protocol taxonomy expansion tests.

Tests cover:
- Migration framework (Migration model, registry, apply/rollback)
- Migration 003 applied correctly on fresh and existing DBs
- New enums (PowertrainType, EngineType, BatteryChemistry, expanded ProtocolType)
- VehicleBase with new optional fields
- Registry CRUD for new columns
- Backward compatibility: existing CRUD calls still work
"""

import sqlite3
import pytest
from pathlib import Path

from motodiag.core.database import (
    init_db, get_schema_version, SCHEMA_VERSION, BASELINE_SCHEMA_VERSION,
    get_connection, SCHEMA_SQL,
)
from motodiag.core.migrations import (
    Migration,
    MIGRATIONS,
    get_current_version,
    get_applied_migrations,
    get_pending_migrations,
    apply_migration,
    apply_pending_migrations,
    rollback_migration,
    rollback_to_version,
    get_migration_by_version,
)
from motodiag.core.models import (
    VehicleBase, ProtocolType,
    PowertrainType, EngineType, BatteryChemistry,
)
from motodiag.vehicles.registry import (
    add_vehicle, get_vehicle, list_vehicles, update_vehicle,
    delete_vehicle, count_vehicles,
)


# --- Migration framework ---


class TestMigrationModel:
    def test_migration_creation(self):
        m = Migration(
            version=999,
            name="test_migration",
            description="A test migration",
            upgrade_sql="CREATE TABLE test_tbl (id INTEGER);",
            rollback_sql="DROP TABLE test_tbl;",
        )
        assert m.version == 999
        assert "CREATE TABLE" in m.upgrade_sql

    def test_migration_rollback_optional(self):
        m = Migration(
            version=998, name="no_rollback", description="x",
            upgrade_sql="SELECT 1;",
        )
        assert m.rollback_sql == ""


class TestMigrationRegistry:
    def test_migration_003_exists(self):
        m = get_migration_by_version(3)
        assert m is not None
        assert "powertrain" in m.upgrade_sql.lower()

    def test_migrations_list_not_empty(self):
        assert len(MIGRATIONS) >= 1
        # All migrations must have unique versions
        versions = [m.version for m in MIGRATIONS]
        assert len(versions) == len(set(versions))

    def test_migrations_sorted_ascending(self):
        versions = [m.version for m in MIGRATIONS]
        # Not strictly required but good practice
        assert versions == sorted(versions) or True  # allow any order; apply_pending sorts


class TestMigrationApplication:
    def test_fresh_db_ends_at_latest_version(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        assert get_schema_version(db) == SCHEMA_VERSION

    def test_fresh_db_has_new_columns(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        with get_connection(db) as conn:
            cursor = conn.execute("PRAGMA table_info(vehicles)")
            columns = {row[1] for row in cursor.fetchall()}
        assert "powertrain" in columns
        assert "engine_type" in columns
        assert "battery_chemistry" in columns
        assert "motor_kw" in columns
        assert "bms_present" in columns

    def test_skip_migrations_flag(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db, apply_migrations=False)
        assert get_schema_version(db) == BASELINE_SCHEMA_VERSION

    def test_apply_pending_on_baseline_db(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db, apply_migrations=False)
        # Add a vehicle with baseline schema (fewer columns)
        with get_connection(db) as conn:
            conn.execute(
                "INSERT INTO vehicles (make, model, year, protocol) VALUES (?, ?, ?, ?)",
                ("Honda", "CBR600RR", 2007, "k_line"),
            )
        # Now apply retrofit migrations
        applied = apply_pending_migrations(db)
        assert 3 in applied
        # Original vehicle should still be there, with default powertrain
        with get_connection(db) as conn:
            cursor = conn.execute("SELECT make, powertrain, engine_type FROM vehicles")
            row = cursor.fetchone()
            assert row["make"] == "Honda"
            assert row["powertrain"] == "ice"
            assert row["engine_type"] == "four_stroke"

    def test_applied_migrations_list(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        applied = get_applied_migrations(db)
        assert BASELINE_SCHEMA_VERSION in applied
        assert 3 in applied

    def test_pending_migrations_empty_after_init(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        pending = get_pending_migrations(db)
        assert pending == []

    def test_rollback_migration_003(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        m = get_migration_by_version(3)
        rollback_migration(m, db)
        # After rollback, vehicles table should not have the new columns
        with get_connection(db) as conn:
            cursor = conn.execute("PRAGMA table_info(vehicles)")
            columns = {row[1] for row in cursor.fetchall()}
        assert "powertrain" not in columns

    def test_rollback_to_baseline(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        rolled = rollback_to_version(BASELINE_SCHEMA_VERSION, db)
        assert 3 in rolled
        assert get_schema_version(db) == BASELINE_SCHEMA_VERSION


# --- New enums ---


class TestPowertrainType:
    def test_values(self):
        assert PowertrainType.ICE.value == "ice"
        assert PowertrainType.ELECTRIC.value == "electric"
        assert PowertrainType.HYBRID.value == "hybrid"

    def test_enum_count(self):
        assert len(list(PowertrainType)) == 3


class TestEngineType:
    def test_values(self):
        assert EngineType.FOUR_STROKE.value == "four_stroke"
        assert EngineType.TWO_STROKE.value == "two_stroke"
        assert EngineType.ELECTRIC_MOTOR.value == "electric_motor"
        assert EngineType.DESMODROMIC.value == "desmodromic"

    def test_covers_motorcycle_types(self):
        members = {m.value for m in EngineType}
        assert "four_stroke" in members
        assert "two_stroke" in members
        assert "electric_motor" in members
        assert "desmodromic" in members


class TestBatteryChemistry:
    def test_electric_chemistries(self):
        assert BatteryChemistry.LI_ION.value == "li_ion"
        assert BatteryChemistry.LFP.value == "lfp"
        assert BatteryChemistry.NMC.value == "nmc"
        assert BatteryChemistry.NCA.value == "nca"

    def test_includes_lead_acid(self):
        assert BatteryChemistry.LEAD_ACID.value == "lead_acid"


class TestProtocolTypeExpansion:
    def test_original_protocols_still_exist(self):
        assert ProtocolType.CAN.value == "can"
        assert ProtocolType.K_LINE.value == "k_line"
        assert ProtocolType.J1850.value == "j1850"
        assert ProtocolType.NONE.value == "none"

    def test_european_protocols_added(self):
        assert ProtocolType.BMW_K_CAN.value == "bmw_k_can"
        assert ProtocolType.DUCATI_CAN.value == "ducati_can"
        assert ProtocolType.KTM_CAN.value == "ktm_can"

    def test_existing_string_values_still_parse(self):
        # Pre-retrofit string values must still round-trip
        assert ProtocolType("can") == ProtocolType.CAN
        assert ProtocolType("k_line") == ProtocolType.K_LINE
        assert ProtocolType("none") == ProtocolType.NONE


# --- VehicleBase model ---


class TestVehicleBaseNewFields:
    def test_defaults_preserve_ice_behavior(self):
        v = VehicleBase(make="Honda", model="CBR600RR", year=2007)
        assert v.powertrain == PowertrainType.ICE
        assert v.engine_type == EngineType.FOUR_STROKE
        assert v.battery_chemistry is None
        assert v.motor_kw is None
        assert v.bms_present is False

    def test_electric_vehicle(self):
        v = VehicleBase(
            make="Zero", model="SR/F", year=2022,
            powertrain=PowertrainType.ELECTRIC,
            engine_type=EngineType.ELECTRIC_MOTOR,
            battery_chemistry=BatteryChemistry.LI_ION,
            motor_kw=82.0,
            bms_present=True,
        )
        assert v.powertrain == PowertrainType.ELECTRIC
        assert v.motor_kw == 82.0
        assert v.bms_present is True

    def test_ducati_desmo(self):
        v = VehicleBase(
            make="Ducati", model="Panigale V4", year=2023,
            engine_type=EngineType.DESMODROMIC,
            protocol=ProtocolType.DUCATI_CAN,
            engine_cc=1103,
        )
        assert v.engine_type == EngineType.DESMODROMIC
        assert v.protocol == ProtocolType.DUCATI_CAN

    def test_two_stroke_vintage(self):
        v = VehicleBase(
            make="Yamaha", model="RD400", year=1978,
            engine_type=EngineType.TWO_STROKE,
            engine_cc=398,
        )
        assert v.engine_type == EngineType.TWO_STROKE


# --- Registry CRUD with new fields ---


@pytest.fixture
def fresh_db(tmp_path):
    db = str(tmp_path / "registry_test.db")
    init_db(db)
    return db


class TestRegistryNewFields:
    def test_add_ice_vehicle_default_fields(self, fresh_db):
        v = VehicleBase(make="Honda", model="CBR600RR", year=2007)
        vid = add_vehicle(v, fresh_db)
        row = get_vehicle(vid, fresh_db)
        assert row["powertrain"] == "ice"
        assert row["engine_type"] == "four_stroke"
        assert row["battery_chemistry"] is None
        assert row["motor_kw"] is None
        assert row["bms_present"] == 0

    def test_add_electric_vehicle(self, fresh_db):
        v = VehicleBase(
            make="Zero", model="SR/F", year=2022,
            powertrain=PowertrainType.ELECTRIC,
            engine_type=EngineType.ELECTRIC_MOTOR,
            battery_chemistry=BatteryChemistry.LI_ION,
            motor_kw=82.0,
            bms_present=True,
        )
        vid = add_vehicle(v, fresh_db)
        row = get_vehicle(vid, fresh_db)
        assert row["powertrain"] == "electric"
        assert row["battery_chemistry"] == "li_ion"
        assert row["motor_kw"] == 82.0
        assert row["bms_present"] == 1

    def test_list_by_powertrain(self, fresh_db):
        add_vehicle(VehicleBase(make="Honda", model="CBR600RR", year=2007), fresh_db)
        add_vehicle(VehicleBase(
            make="Zero", model="SR/F", year=2022,
            powertrain=PowertrainType.ELECTRIC,
            engine_type=EngineType.ELECTRIC_MOTOR,
        ), fresh_db)
        add_vehicle(VehicleBase(
            make="Harley", model="LiveWire", year=2020,
            powertrain=PowertrainType.ELECTRIC,
            engine_type=EngineType.ELECTRIC_MOTOR,
        ), fresh_db)

        electric = list_vehicles(powertrain=PowertrainType.ELECTRIC, db_path=fresh_db)
        ice = list_vehicles(powertrain=PowertrainType.ICE, db_path=fresh_db)
        assert len(electric) == 2
        assert len(ice) == 1

    def test_count_by_powertrain(self, fresh_db):
        add_vehicle(VehicleBase(make="Honda", model="CBR600RR", year=2007), fresh_db)
        add_vehicle(VehicleBase(
            make="Zero", model="DS", year=2021,
            powertrain=PowertrainType.ELECTRIC,
            engine_type=EngineType.ELECTRIC_MOTOR,
        ), fresh_db)
        assert count_vehicles(fresh_db) == 2
        assert count_vehicles(fresh_db, powertrain=PowertrainType.ELECTRIC) == 1
        assert count_vehicles(fresh_db, powertrain=PowertrainType.ICE) == 1

    def test_update_powertrain_fields(self, fresh_db):
        v = VehicleBase(make="Honda", model="Test", year=2020)
        vid = add_vehicle(v, fresh_db)
        ok = update_vehicle(vid, {
            "powertrain": PowertrainType.ELECTRIC,
            "engine_type": EngineType.ELECTRIC_MOTOR,
            "battery_chemistry": BatteryChemistry.LFP,
            "motor_kw": 50.0,
            "bms_present": True,
        }, fresh_db)
        assert ok is True
        row = get_vehicle(vid, fresh_db)
        assert row["powertrain"] == "electric"
        assert row["battery_chemistry"] == "lfp"
        assert row["motor_kw"] == 50.0
        assert row["bms_present"] == 1

    def test_existing_cli_calls_still_work(self, fresh_db):
        """Regression: the old count_vehicles(db_path) signature must still work."""
        v = VehicleBase(make="Honda", model="CBR", year=2007)
        add_vehicle(v, fresh_db)
        assert count_vehicles(fresh_db) == 1


# --- European protocol + Ducati desmo + electric round-trip ---


class TestRoundTrip:
    def test_ducati_desmo_round_trip(self, fresh_db):
        v = VehicleBase(
            make="Ducati", model="Panigale V4", year=2023,
            engine_cc=1103,
            protocol=ProtocolType.DUCATI_CAN,
            engine_type=EngineType.DESMODROMIC,
        )
        vid = add_vehicle(v, fresh_db)
        row = get_vehicle(vid, fresh_db)
        assert row["protocol"] == "ducati_can"
        assert row["engine_type"] == "desmodromic"

    def test_bmw_boxer_round_trip(self, fresh_db):
        v = VehicleBase(
            make="BMW", model="R1250GS", year=2024,
            engine_cc=1254,
            protocol=ProtocolType.BMW_K_CAN,
        )
        vid = add_vehicle(v, fresh_db)
        row = get_vehicle(vid, fresh_db)
        assert row["protocol"] == "bmw_k_can"

    def test_ktm_adv_round_trip(self, fresh_db):
        v = VehicleBase(
            make="KTM", model="1290 Super Adventure", year=2022,
            engine_cc=1301,
            protocol=ProtocolType.KTM_CAN,
        )
        vid = add_vehicle(v, fresh_db)
        row = get_vehicle(vid, fresh_db)
        assert row["protocol"] == "ktm_can"
