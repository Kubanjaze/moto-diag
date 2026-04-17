"""Phase 111 — Knowledge base schema expansion tests.

Tests cover:
- Migration 004 applied correctly
- DTCCategory enum has all required categories (ICE + electric)
- dtc_category_meta table populated with expected rows
- DTC repo supports dtc_category filtering
- DTCCode model accepts optional dtc_category
- fault_codes classify_code handles European + electric formats
- All 1651 pre-retrofit tests still pass
"""

import pytest

from motodiag.core.database import (
    init_db, get_schema_version, SCHEMA_VERSION, get_connection,
)
from motodiag.core.migrations import (
    MIGRATIONS, get_migration_by_version, rollback_migration, apply_pending_migrations,
)
from motodiag.core.models import (
    DTCCode, DTCCategory, SymptomCategory, Severity,
)
from motodiag.knowledge.dtc_repo import (
    add_dtc, get_dtc, get_dtcs_by_category,
    get_category_meta, list_all_categories, count_dtcs,
)
from motodiag.engine.fault_codes import classify_code, CodeFormat


# --- DTCCategory enum ---


class TestDTCCategory:
    def test_ice_categories_exist(self):
        assert DTCCategory.ENGINE.value == "engine"
        assert DTCCategory.FUEL.value == "fuel"
        assert DTCCategory.IGNITION.value == "ignition"
        assert DTCCategory.EMISSIONS.value == "emissions"
        assert DTCCategory.TRANSMISSION.value == "transmission"
        assert DTCCategory.COOLING.value == "cooling"
        assert DTCCategory.EXHAUST.value == "exhaust"

    def test_chassis_safety_categories(self):
        assert DTCCategory.ABS.value == "abs"
        assert DTCCategory.AIRBAG.value == "airbag"
        assert DTCCategory.IMMOBILIZER.value == "immobilizer"
        assert DTCCategory.TPMS.value == "tpms"

    def test_electric_categories(self):
        assert DTCCategory.HV_BATTERY.value == "hv_battery"
        assert DTCCategory.MOTOR.value == "motor"
        assert DTCCategory.REGEN.value == "regen"
        assert DTCCategory.CHARGING_PORT.value == "charging_port"
        assert DTCCategory.THERMAL.value == "thermal"
        assert DTCCategory.INVERTER.value == "inverter"

    def test_unknown_fallback(self):
        assert DTCCategory.UNKNOWN.value == "unknown"

    def test_enum_count_meets_minimum(self):
        # 20 categories minimum (14 ICE/chassis + 6 electric)
        assert len(list(DTCCategory)) >= 20


# --- Migration 004 ---


class TestMigration004:
    def test_migration_004_exists(self):
        m = get_migration_by_version(4)
        assert m is not None
        assert "dtc_category" in m.upgrade_sql.lower()
        assert "dtc_category_meta" in m.upgrade_sql.lower()

    def test_fresh_db_has_dtc_category_column(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        with get_connection(db) as conn:
            cursor = conn.execute("PRAGMA table_info(dtc_codes)")
            columns = {row[1] for row in cursor.fetchall()}
        assert "dtc_category" in columns

    def test_fresh_db_has_dtc_category_meta_table(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='dtc_category_meta'"
            )
            assert cursor.fetchone() is not None

    def test_meta_table_populated(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        categories = list_all_categories(db)
        # 20 categories from migration 004
        assert len(categories) == 20

    def test_hv_battery_meta_electric_only(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        meta = get_category_meta(DTCCategory.HV_BATTERY, db)
        assert meta is not None
        assert "electric" in meta["applicable_powertrains"]
        assert meta["severity_default"] == "critical"

    def test_engine_meta_ice_hybrid(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        meta = get_category_meta(DTCCategory.ENGINE, db)
        assert meta is not None
        assert "ice" in meta["applicable_powertrains"]
        assert "hybrid" in meta["applicable_powertrains"]

    def test_schema_version_at_target(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        assert get_schema_version(db) == SCHEMA_VERSION

    def test_rollback_004_removes_column_and_table(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        m = get_migration_by_version(4)
        rollback_migration(m, db)
        with get_connection(db) as conn:
            # dtc_category column should be gone
            cursor = conn.execute("PRAGMA table_info(dtc_codes)")
            columns = {row[1] for row in cursor.fetchall()}
            assert "dtc_category" not in columns
            # dtc_category_meta table should be gone
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='dtc_category_meta'"
            )
            assert cursor.fetchone() is None


# --- DTCCode model with dtc_category ---


class TestDTCCodeModel:
    def test_default_dtc_category_is_unknown(self):
        d = DTCCode(
            code="P0301", description="Test",
            category=SymptomCategory.ENGINE,
        )
        assert d.dtc_category == DTCCategory.UNKNOWN

    def test_explicit_dtc_category(self):
        d = DTCCode(
            code="HV_B001", description="HV battery overvoltage",
            category=SymptomCategory.ELECTRICAL,
            dtc_category=DTCCategory.HV_BATTERY,
        )
        assert d.dtc_category == DTCCategory.HV_BATTERY

    def test_backward_compat_category_still_required(self):
        # Existing code passing only category still works
        d = DTCCode(
            code="P0301", description="Misfire",
            category=SymptomCategory.ENGINE,
        )
        assert d.category == SymptomCategory.ENGINE
        assert d.dtc_category == DTCCategory.UNKNOWN


# --- DTC repo queries with dtc_category ---


@pytest.fixture
def db_with_dtcs(tmp_path):
    db = str(tmp_path / "dtc_test.db")
    init_db(db)

    # Add some DTCs across categories
    add_dtc(DTCCode(
        code="P0301", description="Cyl 1 misfire",
        category=SymptomCategory.ENGINE,
        dtc_category=DTCCategory.ENGINE,
    ), db)
    add_dtc(DTCCode(
        code="HV_B001", description="HV battery overvoltage",
        category=SymptomCategory.ELECTRICAL,
        dtc_category=DTCCategory.HV_BATTERY,
        make="Zero",
    ), db)
    add_dtc(DTCCode(
        code="MC_001", description="Motor controller IGBT fault",
        category=SymptomCategory.ELECTRICAL,
        dtc_category=DTCCategory.MOTOR,
        make="Zero",
    ), db)
    add_dtc(DTCCode(
        code="REG_001", description="Regen brake sensor fault",
        category=SymptomCategory.BRAKES,
        dtc_category=DTCCategory.REGEN,
    ), db)
    return db


class TestDTCRepoCategoryQuery:
    def test_get_dtcs_by_category_hv_battery(self, db_with_dtcs):
        results = get_dtcs_by_category(DTCCategory.HV_BATTERY, db_path=db_with_dtcs)
        assert len(results) == 1
        assert results[0]["code"] == "HV_B001"

    def test_get_dtcs_by_category_motor(self, db_with_dtcs):
        results = get_dtcs_by_category(DTCCategory.MOTOR, db_path=db_with_dtcs)
        assert len(results) == 1
        assert "IGBT" in results[0]["description"]

    def test_get_dtcs_by_category_string_arg(self, db_with_dtcs):
        # Accept string argument as well as enum
        results = get_dtcs_by_category("regen", db_path=db_with_dtcs)
        assert len(results) == 1

    def test_get_dtcs_by_category_no_match(self, db_with_dtcs):
        results = get_dtcs_by_category(DTCCategory.AIRBAG, db_path=db_with_dtcs)
        assert results == []

    def test_add_dtc_persists_dtc_category(self, db_with_dtcs):
        # Retrieve and verify dtc_category was saved
        result = get_dtc("HV_B001", make="Zero", db_path=db_with_dtcs)
        assert result is not None
        assert result.get("dtc_category") == "hv_battery"

    def test_category_meta_descriptions(self, db_with_dtcs):
        meta = get_category_meta(DTCCategory.MOTOR, db_with_dtcs)
        assert meta is not None
        assert "IGBT" in meta["description"] or "motor" in meta["description"].lower()

    def test_list_all_categories_sorted(self, db_with_dtcs):
        cats = list_all_categories(db_with_dtcs)
        category_names = [c["category"] for c in cats]
        assert category_names == sorted(category_names)


# --- Fault code classifiers (European + electric) ---


class TestBMWClassifier:
    def test_bmw_ista_5char_hex(self):
        fmt, desc = classify_code("A0B12", make="BMW")
        assert fmt == CodeFormat.BMW_ISTA
        assert "BMW" in desc

    def test_bmw_without_make_falls_back(self):
        # Without make hint, "A0B12" could be ambiguous
        fmt, _ = classify_code("A0B12")
        # Should not be BMW_ISTA without make context
        assert fmt != CodeFormat.BMW_ISTA


class TestDucatiClassifier:
    def test_ducati_dds_powertrain(self):
        fmt, desc = classify_code("DTC-P0042")
        assert fmt == CodeFormat.DUCATI_DDS
        assert "powertrain" in desc.lower()

    def test_ducati_dds_auxiliary(self):
        fmt, desc = classify_code("DTC-A0100")
        assert fmt == CodeFormat.DUCATI_DDS
        assert "auxiliary" in desc.lower()


class TestKTMClassifier:
    def test_ktm_kds_powertrain(self):
        fmt, desc = classify_code("KP-0101")
        assert fmt == CodeFormat.KTM_KDS
        assert "powertrain" in desc.lower()

    def test_ktm_kds_chassis(self):
        fmt, desc = classify_code("KC-0200")
        assert fmt == CodeFormat.KTM_KDS
        assert "chassis" in desc.lower()


class TestTriumphClassifier:
    def test_triumph_tuneecu_t_prefix(self):
        fmt, desc = classify_code("T-1A3")
        assert fmt == CodeFormat.TRIUMPH_TUNEECU
        assert "Triumph" in desc


class TestApriliaClassifier:
    def test_aprilia_diag(self):
        fmt, desc = classify_code("DTC-4212", make="Aprilia")
        assert fmt == CodeFormat.APRILIA_DIAG
        assert "Aprilia" in desc


class TestElectricClassifier:
    def test_hv_battery_code(self):
        fmt, desc = classify_code("HV_B001")
        assert fmt == CodeFormat.ELECTRIC_HV
        assert "high-voltage" in desc.lower()

    def test_motor_controller_code(self):
        fmt, desc = classify_code("MC_I001")
        assert fmt == CodeFormat.ELECTRIC_HV
        assert "motor controller" in desc.lower()

    def test_bms_code(self):
        fmt, desc = classify_code("BMS_OVT")
        assert fmt == CodeFormat.ELECTRIC_HV
        assert "battery management" in desc.lower()

    def test_inverter_code(self):
        fmt, desc = classify_code("INV_F01")
        assert fmt == CodeFormat.ELECTRIC_HV
        assert "inverter" in desc.lower()

    def test_charging_code(self):
        fmt, desc = classify_code("CHG_001")
        assert fmt == CodeFormat.ELECTRIC_HV
        assert "charging" in desc.lower()

    def test_regen_code(self):
        fmt, desc = classify_code("REG_001")
        assert fmt == CodeFormat.ELECTRIC_HV
        assert "regen" in desc.lower()


class TestBackwardCompatibility:
    def test_obd2_generic_still_works(self):
        fmt, _ = classify_code("P0301")
        assert fmt == CodeFormat.OBD2_GENERIC

    def test_kawasaki_dealer_still_works(self):
        fmt, _ = classify_code("12")
        assert fmt == CodeFormat.KAWASAKI_DEALER

    def test_suzuki_cmode_still_works(self):
        fmt, _ = classify_code("C28")
        assert fmt == CodeFormat.SUZUKI_CMODE

    def test_honda_blink_still_works(self):
        fmt, _ = classify_code("7")
        assert fmt == CodeFormat.HONDA_BLINK

    def test_harley_body_code_still_works(self):
        fmt, _ = classify_code("B1004")
        assert fmt == CodeFormat.HARLEY_DTC

    def test_unknown_fallback_unchanged(self):
        fmt, _ = classify_code("ZZZZZZ")
        assert fmt == CodeFormat.UNKNOWN
