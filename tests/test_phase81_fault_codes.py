"""Phase 81 — Fault code interpretation tests.

Tests code classification, make-specific format handling, FaultCodeResult model,
DTC prompt template, and FaultCodeInterpreter with mocked API calls.
"""

import json
from unittest.mock import MagicMock

import pytest

from motodiag.engine.fault_codes import (
    classify_code,
    CodeFormat,
    FaultCodeResult,
    FaultCodeInterpreter,
    DTC_INTERPRETATION_PROMPT,
    KAWASAKI_CODE_MAP,
    SUZUKI_CODE_MAP,
    OBD2_SYSTEM_MAP,
)
from motodiag.engine.client import DiagnosticClient


# --- Code classification ---


class TestCodeClassification:
    def test_obd2_generic_p0301(self):
        fmt, system = classify_code("P0301")
        assert fmt == CodeFormat.OBD2_GENERIC
        assert system == "ignition_misfire"

    def test_obd2_generic_p0171(self):
        fmt, system = classify_code("P0171")
        assert fmt == CodeFormat.OBD2_GENERIC
        assert system == "fuel_and_air_metering"

    def test_obd2_generic_p0420(self):
        fmt, system = classify_code("P0420")
        assert fmt == CodeFormat.OBD2_GENERIC
        assert system == "auxiliary_emissions"

    def test_obd2_manufacturer_p1xxx(self):
        fmt, system = classify_code("P1300")
        assert fmt == CodeFormat.OBD2_MANUFACTURER
        assert system == "manufacturer_specific"

    def test_kawasaki_dealer_mode_12(self):
        fmt, desc = classify_code("12")
        assert fmt == CodeFormat.KAWASAKI_DEALER
        assert "ISC" in desc

    def test_kawasaki_dealer_mode_13(self):
        fmt, desc = classify_code("13")
        assert fmt == CodeFormat.KAWASAKI_DEALER
        assert "TPS" in desc

    def test_kawasaki_dealer_mode_42(self):
        fmt, desc = classify_code("42")
        assert fmt == CodeFormat.KAWASAKI_DEALER
        assert "Fuel pump" in desc

    def test_suzuki_cmode_c28(self):
        fmt, desc = classify_code("C28")
        assert fmt == CodeFormat.SUZUKI_CMODE
        assert "Fuel pump" in desc or "FI relay" in desc

    def test_suzuki_cmode_c12(self):
        fmt, desc = classify_code("C12")
        assert fmt == CodeFormat.SUZUKI_CMODE
        assert "TPS" in desc

    def test_suzuki_cmode_c46(self):
        fmt, desc = classify_code("C46")
        assert fmt == CodeFormat.SUZUKI_CMODE
        assert "wheel speed" in desc.lower()

    def test_honda_blink_code(self):
        fmt, desc = classify_code("7")
        assert fmt == CodeFormat.HONDA_BLINK
        assert "Honda blink" in desc

    def test_harley_b_code(self):
        fmt, system = classify_code("B1004")
        assert fmt == CodeFormat.HARLEY_DTC
        assert system == "body_electrical"

    def test_harley_u_code(self):
        fmt, system = classify_code("U1300")
        assert fmt == CodeFormat.HARLEY_DTC
        assert system == "communication_network"

    def test_unknown_code(self):
        fmt, desc = classify_code("ZZZZ")
        assert fmt == CodeFormat.UNKNOWN
        assert "unrecognized" in desc.lower()

    def test_yamaha_2digit_with_make(self):
        fmt, desc = classify_code("14", make="Yamaha")
        assert fmt == CodeFormat.YAMAHA_DIAG
        assert "Yamaha" in desc

    def test_case_insensitive(self):
        fmt1, _ = classify_code("p0301")
        fmt2, _ = classify_code("P0301")
        assert fmt1 == fmt2

    def test_whitespace_handling(self):
        fmt, _ = classify_code("  P0301  ")
        assert fmt == CodeFormat.OBD2_GENERIC


# --- FaultCodeResult model ---


class TestFaultCodeResult:
    def test_basic_creation(self):
        result = FaultCodeResult(
            code="P0301",
            code_format=CodeFormat.OBD2_GENERIC,
            description="Cylinder 1 misfire detected",
            system="ignition_misfire",
            possible_causes=["Fouled spark plug", "Ignition coil failure", "Low compression"],
            tests_to_confirm=["Check spark plug condition", "Swap coils between cylinders"],
            related_symptoms=["rough idle", "loss of power", "check engine light on"],
            repair_steps=["Replace spark plug", "If persists, test coil resistance"],
            estimated_hours=0.5,
            estimated_cost="$10-150",
            safety_critical=False,
        )
        assert result.code == "P0301"
        assert len(result.possible_causes) == 3
        assert len(result.tests_to_confirm) == 2
        assert result.safety_critical is False

    def test_safety_critical_code(self):
        result = FaultCodeResult(
            code="C46",
            code_format=CodeFormat.SUZUKI_CMODE,
            description="Front wheel speed sensor",
            system="ABS",
            safety_critical=True,
        )
        assert result.safety_critical is True

    def test_minimal_creation(self):
        result = FaultCodeResult(code="12", code_format=CodeFormat.KAWASAKI_DEALER)
        assert result.code == "12"
        assert result.possible_causes == []
        assert result.notes is None


# --- Code database coverage ---


class TestCodeDatabases:
    def test_kawasaki_code_map_coverage(self):
        assert len(KAWASAKI_CODE_MAP) >= 20
        assert "12" in KAWASAKI_CODE_MAP  # ISC
        assert "13" in KAWASAKI_CODE_MAP  # TPS
        assert "42" in KAWASAKI_CODE_MAP  # Fuel pump

    def test_suzuki_code_map_coverage(self):
        assert len(SUZUKI_CODE_MAP) >= 18
        assert "C28" in SUZUKI_CODE_MAP  # Fuel pump
        assert "C12" in SUZUKI_CODE_MAP  # TPS
        assert "C46" in SUZUKI_CODE_MAP  # Wheel speed

    def test_obd2_system_map_coverage(self):
        assert len(OBD2_SYSTEM_MAP) >= 7
        assert "3" in OBD2_SYSTEM_MAP  # ignition_misfire
        assert "1" in OBD2_SYSTEM_MAP  # fuel_and_air_metering


# --- DTC prompt template ---


class TestDtcPrompt:
    def test_prompt_has_all_steps(self):
        assert "STEP 1" in DTC_INTERPRETATION_PROMPT
        assert "STEP 2" in DTC_INTERPRETATION_PROMPT
        assert "STEP 3" in DTC_INTERPRETATION_PROMPT
        assert "STEP 4" in DTC_INTERPRETATION_PROMPT
        assert "STEP 5" in DTC_INTERPRETATION_PROMPT

    def test_prompt_emphasizes_testing_first(self):
        assert "check before replacing" in DTC_INTERPRETATION_PROMPT.lower()
        assert "testing first" in DTC_INTERPRETATION_PROMPT.lower()

    def test_prompt_mentions_symptom_not_diagnosis(self):
        assert "SYMPTOM" in DTC_INTERPRETATION_PROMPT


# --- FaultCodeInterpreter with mocked API ---


class TestFaultCodeInterpreterMocked:
    def _make_mock_client(self, response_json: dict = None):
        if response_json is None:
            response_json = {
                "possible_causes": ["Fouled spark plug", "Ignition coil failure"],
                "tests_to_confirm": ["Check plug condition", "Swap coils"],
                "related_symptoms": ["rough idle", "loss of power"],
                "repair_steps": ["Replace plug", "Test coil"],
                "estimated_hours": 0.5,
                "estimated_cost": "$10-150",
                "safety_critical": False,
                "notes": "Most common cause is fouled plug on high-mileage engines.",
            }

        mock_anthropic_client = MagicMock()
        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.text = json.dumps(response_json)
        mock_response.content = [mock_block]
        mock_response.usage.input_tokens = 600
        mock_response.usage.output_tokens = 350
        mock_anthropic_client.messages.create.return_value = mock_response

        client = DiagnosticClient(api_key="sk-test")
        client._client = mock_anthropic_client
        return client

    def test_interpret_obd2_code(self):
        client = self._make_mock_client()
        interpreter = FaultCodeInterpreter(client)

        # Phase 131: disable cache so shared default DB state doesn't leak between tests
        result, usage = interpreter.interpret(
            code="P0301",
            make="Honda",
            model_name="CBR600RR",
            year=2007,
            use_cache=False,
        )

        assert isinstance(result, FaultCodeResult)
        assert result.code == "P0301"
        assert result.code_format == CodeFormat.OBD2_GENERIC
        assert len(result.possible_causes) == 2
        assert usage.input_tokens == 600

    def test_interpret_kawasaki_dealer_code(self):
        client = self._make_mock_client()
        interpreter = FaultCodeInterpreter(client)

        result, usage = interpreter.interpret(
            code="12",
            make="Kawasaki",
            model_name="ZX-6R",
            year=2015,
            use_cache=False,
        )

        assert result.code == "12"
        assert result.code_format == CodeFormat.KAWASAKI_DEALER
        assert "ISC" in result.description

    def test_interpret_suzuki_cmode_code(self):
        client = self._make_mock_client()
        interpreter = FaultCodeInterpreter(client)

        result, usage = interpreter.interpret(
            code="C28",
            make="Suzuki",
            model_name="GSX-R600",
            year=2010,
            use_cache=False,
        )

        assert result.code == "C28"
        assert result.code_format == CodeFormat.SUZUKI_CMODE

    def test_interpret_with_symptoms(self):
        client = self._make_mock_client()
        interpreter = FaultCodeInterpreter(client)

        result, usage = interpreter.interpret(
            code="P0301",
            make="Kawasaki",
            model_name="ZX-10R",
            year=2018,
            symptoms=["rough idle", "loss of power"],
            use_cache=False,
        )

        # Verify symptoms were included in the prompt
        call_args = client._client.messages.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "rough idle" in prompt
        assert "loss of power" in prompt

    def test_interpret_with_knowledge_context(self):
        client = self._make_mock_client()
        interpreter = FaultCodeInterpreter(client)

        known_issues = [{"title": "ISC valve carbon", "severity": "medium",
                         "symptoms": ["rough idle"], "causes": ["Carbon buildup"],
                         "fix_procedure": "Clean ISC valve..."}]

        result, usage = interpreter.interpret(
            code="12",
            make="Kawasaki",
            model_name="Vulcan 900",
            year=2015,
            known_issues=known_issues,
            use_cache=False,
        )

        call_args = client._client.messages.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "ISC valve carbon" in prompt

    def test_interpret_uses_dtc_prompt(self):
        client = self._make_mock_client()
        interpreter = FaultCodeInterpreter(client)

        interpreter.interpret(
            code="P0171", make="Honda", model_name="CB500F", year=2020,
            use_cache=False,
        )

        call_args = client._client.messages.create.call_args
        system = call_args[1]["system"]
        assert "ROOT CAUSE ANALYSIS" in system
        assert "check before replacing" in system.lower()

    def test_interpret_fallback_on_bad_json(self):
        mock_anthropic_client = MagicMock()
        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.text = "This is not valid JSON — raw diagnostic text."
        mock_response.content = [mock_block]
        mock_response.usage.input_tokens = 500
        mock_response.usage.output_tokens = 200
        mock_anthropic_client.messages.create.return_value = mock_response

        client = DiagnosticClient(api_key="sk-test")
        client._client = mock_anthropic_client
        interpreter = FaultCodeInterpreter(client)

        # Phase 131: disable the response cache so an entry primed by another
        # test (or a prior run) doesn't mask the bad-JSON fallback path.
        result, usage = interpreter.interpret(
            code="P0301", make="Honda", model_name="CBR600RR", year=2007,
            use_cache=False,
        )

        assert isinstance(result, FaultCodeResult)
        assert result.notes is not None
        assert "not be parsed" in result.notes


# --- Quick lookup (no AI) ---


class TestQuickLookup:
    def test_quick_lookup_known_code(self):
        client = DiagnosticClient(api_key="sk-test")
        interpreter = FaultCodeInterpreter(client)

        info = interpreter.quick_lookup("P0301")
        assert info["code"] == "P0301"
        assert info["code_format"] == CodeFormat.OBD2_GENERIC
        assert info["requires_ai"] is True

    def test_quick_lookup_unknown_code(self):
        client = DiagnosticClient(api_key="sk-test")
        interpreter = FaultCodeInterpreter(client)

        info = interpreter.quick_lookup("ZZZZ")
        assert info["code_format"] == CodeFormat.UNKNOWN
        assert info["requires_ai"] is False

    def test_quick_lookup_kawasaki_with_make(self):
        client = DiagnosticClient(api_key="sk-test")
        interpreter = FaultCodeInterpreter(client)

        info = interpreter.quick_lookup("12", make="Kawasaki")
        assert info["code_format"] == CodeFormat.KAWASAKI_DEALER
        assert "ISC" in info["description"]
