"""Shared test fixtures for MotoDiag."""

import pytest


@pytest.fixture
def sample_vehicle():
    """A sample Harley-Davidson Sportster for testing."""
    from motodiag.core.models import VehicleBase, ProtocolType

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
    from motodiag.core.models import DTCCode, SymptomCategory, Severity

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
