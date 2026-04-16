"""Shared test fixtures for MotoDiag."""

import pytest

from motodiag.core.database import init_db
from motodiag.core.models import VehicleBase, DTCCode, ProtocolType, SymptomCategory, Severity
from motodiag.vehicles.registry import add_vehicle
from motodiag.knowledge.dtc_repo import add_dtc
from motodiag.knowledge.symptom_repo import add_symptom
from motodiag.knowledge.issues_repo import add_known_issue
from motodiag.core.session_repo import create_session


# --- Model fixtures (no DB) ---

@pytest.fixture
def sample_vehicle():
    """A sample Harley-Davidson Sportster for testing."""
    return VehicleBase(
        make="Harley-Davidson",
        model="Sportster 1200",
        year=2001,
        engine_cc=1200,
        protocol=ProtocolType.J1850,
        notes="Test vehicle",
    )


@pytest.fixture
def sample_dtc():
    """A sample diagnostic trouble code."""
    return DTCCode(
        code="P0115",
        description="Engine Coolant Temperature Circuit Malfunction",
        category=SymptomCategory.COOLING,
        severity=Severity.MEDIUM,
        common_causes=[
            "Faulty coolant temperature sensor",
            "Wiring issue in coolant temp circuit",
            "Corroded connector",
        ],
        fix_summary="Check sensor connector, test sensor resistance, replace if out of spec.",
    )


# --- Database fixtures ---

@pytest.fixture
def fresh_db(tmp_path):
    """A fresh initialized database (empty tables)."""
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


@pytest.fixture
def populated_db(tmp_path):
    """A database pre-loaded with realistic sample data across all stores."""
    path = str(tmp_path / "populated.db")
    init_db(path)

    # Vehicles
    add_vehicle(VehicleBase(
        make="Harley-Davidson", model="Sportster 1200", year=2001,
        engine_cc=1200, protocol=ProtocolType.J1850,
    ), path)
    add_vehicle(VehicleBase(
        make="Honda", model="CBR929RR", year=2001,
        engine_cc=929, protocol=ProtocolType.K_LINE,
    ), path)
    add_vehicle(VehicleBase(
        make="Kawasaki", model="ZX-6R", year=2003,
        engine_cc=636, protocol=ProtocolType.K_LINE,
    ), path)

    # DTCs
    add_dtc(DTCCode(
        code="P0562", description="System Voltage Low",
        category=SymptomCategory.ELECTRICAL, severity=Severity.HIGH,
        common_causes=["Faulty stator", "Bad regulator", "Weak battery"],
    ), path)
    add_dtc(DTCCode(
        code="P0115", description="Engine Coolant Temperature Circuit",
        category=SymptomCategory.COOLING, severity=Severity.MEDIUM,
    ), path)
    add_dtc(DTCCode(
        code="P0300", description="Random/Multiple Cylinder Misfire",
        category=SymptomCategory.ENGINE, severity=Severity.HIGH,
    ), path)

    # Symptoms
    add_symptom("battery not charging", "Battery voltage drops while riding",
                "electrical", ["electrical"], path)
    add_symptom("won't start", "Engine cranks but does not fire",
                "starting", ["fuel", "electrical", "engine"], path)
    add_symptom("rough idle", "Engine runs unevenly at idle",
                "idle", ["fuel", "idle", "engine"], path)
    add_symptom("overheating", "Engine temp rises above normal",
                "cooling", ["cooling", "engine"], path)

    # Known issues
    add_known_issue(
        title="Stator failure — chronic undercharging",
        description="Stator windings break down from heat causing charging failure",
        make="Harley-Davidson", year_start=1999, year_end=2017,
        severity="high",
        symptoms=["battery not charging", "headlight dim or flickering"],
        dtc_codes=["P0562"],
        causes=["Stator winding insulation breakdown"],
        fix_procedure="Test stator AC output, replace if low. Forum tip: upgrade to Cycle Electric.",
        parts_needed=["Stator assembly", "Stator gasket"],
        estimated_hours=3.5,
        db_path=path,
    )
    add_known_issue(
        title="Regulator/rectifier failure",
        description="Voltage regulator fails causing overcharging or no charging",
        make="Honda", year_start=1991, year_end=2006,
        severity="high",
        symptoms=["battery not charging", "battery drains overnight"],
        dtc_codes=["P0562"],
        causes=["Internal MOSFET failure", "Overheating"],
        fix_procedure="Test charging voltage. Replace with MOSFET-style upgrade.",
        parts_needed=["Voltage regulator (MOSFET upgrade)", "Connector"],
        estimated_hours=1.0,
        db_path=path,
    )

    # Session
    create_session(
        "Harley-Davidson", "Sportster 1200", 2001,
        symptoms=["battery not charging", "headlight dim or flickering"],
        fault_codes=["P0562"],
        db_path=path,
    )

    return path


# --- Vehicle model fixtures ---

@pytest.fixture
def sample_harley():
    return VehicleBase(
        make="Harley-Davidson", model="Sportster 1200", year=2001,
        engine_cc=1200, protocol=ProtocolType.J1850,
    )


@pytest.fixture
def sample_honda():
    return VehicleBase(
        make="Honda", model="CBR929RR", year=2001,
        engine_cc=929, protocol=ProtocolType.K_LINE,
    )


@pytest.fixture
def sample_kawasaki():
    return VehicleBase(
        make="Kawasaki", model="ZX-6R", year=2003,
        engine_cc=636, protocol=ProtocolType.K_LINE,
    )
