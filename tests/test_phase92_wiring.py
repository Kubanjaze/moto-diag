"""Phase 92 — Wiring diagram reference tests.

Tests circuit reference data, lookup functions, wire models,
and context building for AI prompt injection.
"""

import pytest

from motodiag.engine.wiring import (
    WireReference,
    CircuitReference,
    CIRCUIT_REFERENCES,
    get_circuit_reference,
    get_circuits_by_system,
    list_all_circuits,
    build_wiring_context,
)


# --- Models ---


class TestWireReference:
    def test_basic_creation(self):
        wire = WireReference(
            color="Yellow",
            function="Stator AC output",
            connector_location="Behind left engine cover",
            expected_voltage="50-80V AC at 5000 RPM",
        )
        assert wire.color == "Yellow"
        assert wire.function == "Stator AC output"
        assert wire.expected_voltage == "50-80V AC at 5000 RPM"

    def test_minimal_creation(self):
        wire = WireReference(color="Red", function="Power")
        assert wire.expected_voltage is None
        assert wire.expected_resistance is None


class TestCircuitReference:
    def test_basic_creation(self):
        circuit = CircuitReference(
            circuit_name="Test circuit",
            system="electrical",
            description="A test circuit",
            makes_applicable=["Honda", "Suzuki"],
            wires=[WireReference(color="Red", function="Power")],
            test_points=["Check voltage"],
            common_failures=["Wire breaks"],
            diagnostic_tips=["Use a multimeter"],
        )
        assert circuit.circuit_name == "Test circuit"
        assert len(circuit.wires) == 1
        assert len(circuit.makes_applicable) == 2


# --- Circuit reference data ---


class TestCircuitReferences:
    def test_at_least_5_circuits(self):
        assert len(CIRCUIT_REFERENCES) >= 5

    def test_all_circuits_have_required_fields(self):
        for ref in CIRCUIT_REFERENCES:
            assert "circuit_name" in ref
            assert "system" in ref
            assert "description" in ref
            assert "makes_applicable" in ref
            assert "wires" in ref
            assert "test_points" in ref
            assert "common_failures" in ref
            assert "diagnostic_tips" in ref

    def test_charging_circuit_exists(self):
        names = [r["circuit_name"].lower() for r in CIRCUIT_REFERENCES]
        assert any("charging" in n or "stator" in n for n in names)

    def test_starting_circuit_exists(self):
        names = [r["circuit_name"].lower() for r in CIRCUIT_REFERENCES]
        assert any("starting" in n or "starter" in n for n in names)

    def test_fuel_injection_circuit_exists(self):
        names = [r["circuit_name"].lower() for r in CIRCUIT_REFERENCES]
        assert any("fuel" in n or "injection" in n for n in names)

    def test_ignition_circuit_exists(self):
        names = [r["circuit_name"].lower() for r in CIRCUIT_REFERENCES]
        assert any("ignition" in n for n in names)

    def test_abs_circuit_exists(self):
        names = [r["circuit_name"].lower() for r in CIRCUIT_REFERENCES]
        assert any("abs" in n or "speed sensor" in n for n in names)

    def test_all_circuits_cover_multiple_makes(self):
        for ref in CIRCUIT_REFERENCES:
            assert len(ref["makes_applicable"]) >= 3, f"Circuit '{ref['circuit_name']}' has too few makes"

    def test_all_circuits_have_wires(self):
        for ref in CIRCUIT_REFERENCES:
            assert len(ref["wires"]) >= 2, f"Circuit '{ref['circuit_name']}' needs at least 2 wires"

    def test_all_circuits_have_test_points(self):
        for ref in CIRCUIT_REFERENCES:
            assert len(ref["test_points"]) >= 3, f"Circuit '{ref['circuit_name']}' needs at least 3 test points"


# --- Lookup functions ---


class TestGetCircuitReference:
    def test_find_charging_circuit(self):
        circuit = get_circuit_reference("charging")
        assert circuit is not None
        assert "charging" in circuit.circuit_name.lower() or "stator" in circuit.circuit_name.lower()

    def test_find_starting_circuit(self):
        circuit = get_circuit_reference("starting")
        assert circuit is not None

    def test_find_fuel_circuit(self):
        circuit = get_circuit_reference("fuel")
        assert circuit is not None

    def test_case_insensitive(self):
        circuit = get_circuit_reference("CHARGING")
        assert circuit is not None

    def test_not_found_returns_none(self):
        circuit = get_circuit_reference("nonexistent circuit xyz")
        assert circuit is None

    def test_returned_circuit_has_wires(self):
        circuit = get_circuit_reference("charging")
        assert circuit is not None
        assert len(circuit.wires) >= 2
        assert all(isinstance(w, WireReference) for w in circuit.wires)


class TestGetCircuitsBySystem:
    def test_electrical_system(self):
        circuits = get_circuits_by_system("electrical")
        assert len(circuits) >= 2

    def test_fuel_system(self):
        circuits = get_circuits_by_system("fuel")
        assert len(circuits) >= 1

    def test_ignition_system(self):
        circuits = get_circuits_by_system("ignition")
        assert len(circuits) >= 1

    def test_empty_for_unknown_system(self):
        circuits = get_circuits_by_system("nonexistent")
        assert circuits == []


class TestListAllCircuits:
    def test_returns_list_of_strings(self):
        names = list_all_circuits()
        assert isinstance(names, list)
        assert all(isinstance(n, str) for n in names)
        assert len(names) >= 5


# --- Context building ---


class TestBuildWiringContext:
    def test_context_includes_circuit_name(self):
        circuit = get_circuit_reference("charging")
        assert circuit is not None
        ctx = build_wiring_context(circuit)
        assert circuit.circuit_name in ctx

    def test_context_includes_wire_colors(self):
        circuit = get_circuit_reference("charging")
        assert circuit is not None
        ctx = build_wiring_context(circuit)
        assert "Yellow" in ctx  # Stator wires are yellow

    def test_context_includes_test_points(self):
        circuit = get_circuit_reference("charging")
        assert circuit is not None
        ctx = build_wiring_context(circuit)
        assert "Test points" in ctx

    def test_context_includes_diagnostic_tips(self):
        circuit = get_circuit_reference("starting")
        assert circuit is not None
        ctx = build_wiring_context(circuit)
        assert "Diagnostic tips" in ctx

    def test_context_includes_common_failures(self):
        circuit = get_circuit_reference("fuel")
        assert circuit is not None
        ctx = build_wiring_context(circuit)
        assert "Common failures" in ctx
