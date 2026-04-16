"""Phase 93 — Torque specs + service data reference tests.

Tests torque specifications, service intervals, valve clearances,
lookup functions, and context building.
"""

import pytest

from motodiag.engine.service_data import (
    TorqueSpec,
    FluidCapacity,
    ServiceInterval,
    Clearance,
    COMMON_TORQUE_SPECS,
    COMMON_SERVICE_INTERVALS,
    COMMON_VALVE_CLEARANCES,
    get_torque_spec,
    get_service_interval,
    get_valve_clearance,
    list_all_torque_specs,
    list_all_service_intervals,
    build_service_data_context,
)


# --- Models ---


class TestTorqueSpec:
    def test_basic_creation(self):
        spec = TorqueSpec(fastener="Oil drain plug", spec_nm=20.0)
        assert spec.spec_nm == 20.0
        assert spec.spec_ftlbs > 0  # Auto-calculated

    def test_auto_conversion_nm_to_ftlbs(self):
        spec = TorqueSpec(fastener="Test bolt", spec_nm=100.0)
        assert 73.0 < spec.spec_ftlbs < 74.0  # 100 Nm ≈ 73.76 ft-lbs

    def test_with_thread_locker(self):
        spec = TorqueSpec(fastener="Caliper bolt", spec_nm=30.0, thread_locker="Loctite 243 blue")
        assert spec.thread_locker == "Loctite 243 blue"

    def test_with_notes(self):
        spec = TorqueSpec(fastener="Drain plug", spec_nm=20.0, notes="Replace crush washer")
        assert "crush washer" in spec.notes


class TestServiceInterval:
    def test_basic_creation(self):
        interval = ServiceInterval(
            service_item="Oil change",
            interval_miles=4000,
            interval_km=6000,
            interval_months=12,
        )
        assert interval.interval_miles == 4000

    def test_time_based_only(self):
        interval = ServiceInterval(
            service_item="Brake fluid flush",
            interval_months=24,
        )
        assert interval.interval_miles == 0
        assert interval.interval_months == 24


class TestClearance:
    def test_basic_creation(self):
        cl = Clearance(component="Intake valve", spec_mm_low=0.10, spec_mm_high=0.20)
        assert cl.spec_mm_low == 0.10
        assert cl.spec_mm_high == 0.20

    def test_with_notes(self):
        cl = Clearance(component="Exhaust valve", spec_mm_low=0.20, spec_mm_high=0.30, notes="Tightens first")
        assert "Tightens first" in cl.notes


# --- Data coverage ---


class TestDataCoverage:
    def test_at_least_15_torque_specs(self):
        assert len(COMMON_TORQUE_SPECS) >= 15

    def test_at_least_12_service_intervals(self):
        assert len(COMMON_SERVICE_INTERVALS) >= 12

    def test_at_least_6_valve_clearances(self):
        assert len(COMMON_VALVE_CLEARANCES) >= 6

    def test_torque_specs_have_required_fields(self):
        for spec in COMMON_TORQUE_SPECS:
            assert "fastener" in spec
            assert "spec_nm" in spec
            assert spec["spec_nm"] > 0

    def test_service_intervals_have_required_fields(self):
        for interval in COMMON_SERVICE_INTERVALS:
            assert "service_item" in interval
            assert interval.get("interval_miles", 0) > 0 or interval.get("interval_months", 0) > 0

    def test_valve_clearances_have_required_fields(self):
        for cl in COMMON_VALVE_CLEARANCES:
            assert "component" in cl
            assert "spec_mm_low" in cl
            assert "spec_mm_high" in cl
            assert cl["spec_mm_high"] > cl["spec_mm_low"]

    def test_oil_drain_plug_spec_exists(self):
        fasteners = [s["fastener"].lower() for s in COMMON_TORQUE_SPECS]
        assert any("drain" in f for f in fasteners)

    def test_spark_plug_spec_exists(self):
        fasteners = [s["fastener"].lower() for s in COMMON_TORQUE_SPECS]
        assert any("spark" in f for f in fasteners)

    def test_caliper_bolt_spec_exists(self):
        fasteners = [s["fastener"].lower() for s in COMMON_TORQUE_SPECS]
        assert any("caliper" in f for f in fasteners)

    def test_oil_change_interval_exists(self):
        items = [s["service_item"].lower() for s in COMMON_SERVICE_INTERVALS]
        assert any("oil" in i for i in items)

    def test_valve_check_interval_exists(self):
        items = [s["service_item"].lower() for s in COMMON_SERVICE_INTERVALS]
        assert any("valve" in i for i in items)

    def test_brake_fluid_interval_exists(self):
        items = [s["service_item"].lower() for s in COMMON_SERVICE_INTERVALS]
        assert any("brake fluid" in i for i in items)


# --- Lookup functions ---


class TestGetTorqueSpec:
    def test_find_oil_drain(self):
        spec = get_torque_spec("drain plug")
        assert spec is not None
        assert spec.spec_nm > 0

    def test_find_spark_plug(self):
        spec = get_torque_spec("spark plug")
        assert spec is not None
        assert spec.spec_nm > 0

    def test_find_caliper(self):
        spec = get_torque_spec("caliper")
        assert spec is not None
        assert spec.thread_locker is not None  # Caliper bolts require thread locker

    def test_not_found(self):
        spec = get_torque_spec("nonexistent bolt xyz")
        assert spec is None

    def test_case_insensitive(self):
        spec = get_torque_spec("DRAIN PLUG")
        assert spec is not None


class TestGetServiceInterval:
    def test_find_oil_change(self):
        interval = get_service_interval("oil change")
        assert interval is not None
        assert interval.interval_miles > 0

    def test_find_valve_clearance_check(self):
        interval = get_service_interval("valve clearance")
        assert interval is not None
        assert interval.interval_miles > 0

    def test_find_brake_fluid(self):
        interval = get_service_interval("brake fluid")
        assert interval is not None
        assert interval.interval_months > 0

    def test_not_found(self):
        interval = get_service_interval("nonexistent service xyz")
        assert interval is None


class TestGetValveClearance:
    def test_find_inline4_intake(self):
        cl = get_valve_clearance("inline-4 intake")
        assert cl is not None
        assert cl.spec_mm_low < cl.spec_mm_high

    def test_find_single_exhaust(self):
        cl = get_valve_clearance("single-cylinder exhaust")
        assert cl is not None

    def test_not_found(self):
        cl = get_valve_clearance("nonexistent component xyz")
        assert cl is None


class TestListFunctions:
    def test_list_torque_specs(self):
        names = list_all_torque_specs()
        assert len(names) >= 15
        assert all(isinstance(n, str) for n in names)

    def test_list_service_intervals(self):
        names = list_all_service_intervals()
        assert len(names) >= 12
        assert all(isinstance(n, str) for n in names)


# --- Context building ---


class TestBuildServiceDataContext:
    def test_torque_context(self):
        specs = [TorqueSpec(fastener="Drain plug", spec_nm=20.0, notes="Replace washer")]
        ctx = build_service_data_context(torque_specs=specs)
        assert "Drain plug" in ctx
        assert "20.0 Nm" in ctx
        assert "Replace washer" in ctx

    def test_interval_context(self):
        intervals = [ServiceInterval(service_item="Oil change", interval_miles=4000, interval_months=12)]
        ctx = build_service_data_context(intervals=intervals)
        assert "Oil change" in ctx
        assert "4,000 miles" in ctx

    def test_clearance_context(self):
        clearances = [Clearance(component="Intake", spec_mm_low=0.10, spec_mm_high=0.20, notes="Check cold")]
        ctx = build_service_data_context(clearances=clearances)
        assert "Intake" in ctx
        assert "0.1-0.2 mm" in ctx

    def test_combined_context(self):
        specs = [TorqueSpec(fastener="Bolt", spec_nm=25.0)]
        intervals = [ServiceInterval(service_item="Oil", interval_miles=4000)]
        clearances = [Clearance(component="Valve", spec_mm_low=0.1, spec_mm_high=0.2)]
        ctx = build_service_data_context(torque_specs=specs, intervals=intervals, clearances=clearances)
        assert "Torque Specifications" in ctx
        assert "Service Intervals" in ctx
        assert "Valve Clearances" in ctx

    def test_empty_context(self):
        ctx = build_service_data_context()
        assert ctx == ""
