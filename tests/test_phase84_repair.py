"""Phase 84 — Repair Procedure Generator tests.

Tests RepairStep model, RepairProcedure model, SkillLevel assessment,
RepairProcedureGenerator with mocked API calls, and REPAIR_PROMPT validation.
All mocked — zero API calls.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from motodiag.engine.client import MODEL_ALIASES
from motodiag.engine.repair import (
    SkillLevel,
    RepairStep,
    RepairProcedure,
    RepairProcedureGenerator,
    assess_skill_level,
    REPAIR_PROMPT,
)
from motodiag.engine.models import TokenUsage


# --- RepairStep model tests ---


class TestRepairStep:
    def test_basic_step(self):
        step = RepairStep(step_number=1, instruction="Remove the drain plug.")
        assert step.step_number == 1
        assert step.instruction == "Remove the drain plug."
        assert step.tip is None
        assert step.warning is None

    def test_step_with_tip(self):
        step = RepairStep(
            step_number=2,
            instruction="Install new oil filter.",
            tip="Pre-fill the filter with oil to reduce dry-start time.",
        )
        assert step.tip == "Pre-fill the filter with oil to reduce dry-start time."
        assert step.warning is None

    def test_step_with_warning(self):
        step = RepairStep(
            step_number=3,
            instruction="Disconnect the fuel line.",
            warning="Fuel vapor is flammable — work in a ventilated area, no open flames.",
        )
        assert step.warning is not None
        assert "flammable" in step.warning

    def test_step_with_tip_and_warning(self):
        step = RepairStep(
            step_number=4,
            instruction="Remove caliper bolts.",
            tip="Use a 6-point socket to avoid rounding.",
            warning="Support the caliper — do not let it hang by the brake hose.",
        )
        assert step.tip is not None
        assert step.warning is not None

    def test_step_number_must_be_positive(self):
        with pytest.raises(Exception):
            RepairStep(step_number=0, instruction="Invalid step")


# --- RepairProcedure model tests ---


class TestRepairProcedure:
    def test_minimal_procedure(self):
        proc = RepairProcedure(
            title="Oil Change",
            description="Standard oil and filter change.",
        )
        assert proc.title == "Oil Change"
        assert proc.steps == []
        assert proc.tools_needed == []
        assert proc.parts_needed == []
        assert proc.estimated_hours == 0.0
        assert proc.skill_level == SkillLevel.INTERMEDIATE
        assert proc.safety_warnings == []
        assert proc.notes is None

    def test_full_procedure(self):
        proc = RepairProcedure(
            title="Stator Replacement",
            description="Replace failed stator on 2005 Honda CBR600RR.",
            steps=[
                RepairStep(step_number=1, instruction="Disconnect battery negative terminal."),
                RepairStep(step_number=2, instruction="Drain engine oil."),
                RepairStep(step_number=3, instruction="Remove stator cover bolts (8mm)."),
            ],
            tools_needed=["8mm socket", "oil drain pan", "torque wrench"],
            parts_needed=["OEM stator assembly", "stator cover gasket", "3 quarts engine oil"],
            estimated_hours=2.5,
            skill_level=SkillLevel.INTERMEDIATE,
            safety_warnings=["Disconnect battery before working on electrical components."],
            notes="Rick's Motorsport Electrics makes a quality aftermarket stator.",
        )
        assert len(proc.steps) == 3
        assert len(proc.tools_needed) == 3
        assert len(proc.parts_needed) == 3
        assert proc.estimated_hours == 2.5
        assert proc.skill_level == SkillLevel.INTERMEDIATE
        assert proc.notes is not None

    def test_procedure_with_advanced_skill(self):
        proc = RepairProcedure(
            title="Top End Rebuild",
            description="Rebuild cylinder head and replace piston rings.",
            skill_level=SkillLevel.ADVANCED,
        )
        assert proc.skill_level == SkillLevel.ADVANCED

    def test_procedure_with_beginner_skill(self):
        proc = RepairProcedure(
            title="Battery Replacement",
            description="Replace dead battery.",
            skill_level=SkillLevel.BEGINNER,
        )
        assert proc.skill_level == SkillLevel.BEGINNER


# --- SkillLevel enum tests ---


class TestSkillLevel:
    def test_enum_values(self):
        assert SkillLevel.BEGINNER.value == "beginner"
        assert SkillLevel.INTERMEDIATE.value == "intermediate"
        assert SkillLevel.ADVANCED.value == "advanced"

    def test_enum_from_string(self):
        assert SkillLevel("beginner") == SkillLevel.BEGINNER
        assert SkillLevel("advanced") == SkillLevel.ADVANCED


# --- assess_skill_level tests ---


class TestAssessSkillLevel:
    def test_beginner_oil_change(self):
        assert assess_skill_level("Oil change and filter replacement") == SkillLevel.BEGINNER

    def test_beginner_air_filter(self):
        assert assess_skill_level("Replace air filter element") == SkillLevel.BEGINNER

    def test_beginner_spark_plug(self):
        assert assess_skill_level("Replace spark plug") == SkillLevel.BEGINNER

    def test_beginner_chain_adjustment(self):
        assert assess_skill_level("Chain adjustment and lube") == SkillLevel.BEGINNER

    def test_intermediate_electrical(self):
        assert assess_skill_level("Electrical fault in wiring harness") == SkillLevel.INTERMEDIATE

    def test_intermediate_stator(self):
        assert assess_skill_level("Stator replacement needed") == SkillLevel.INTERMEDIATE

    def test_intermediate_fork_seal(self):
        assert assess_skill_level("Fork seal replacement") == SkillLevel.INTERMEDIATE

    def test_intermediate_valve_adjustment(self):
        assert assess_skill_level("Valve adjustment due at 16k miles") == SkillLevel.INTERMEDIATE

    def test_intermediate_carburetor_rebuild(self):
        assert assess_skill_level("Carburetor rebuild — all four carbs") == SkillLevel.INTERMEDIATE

    def test_advanced_engine_rebuild(self):
        assert assess_skill_level("Full engine rebuild required") == SkillLevel.ADVANCED

    def test_advanced_engine_internal(self):
        assert assess_skill_level("Engine internal bearing failure") == SkillLevel.ADVANCED

    def test_advanced_transmission_rebuild(self):
        assert assess_skill_level("Transmission rebuild — 2nd gear dogs worn") == SkillLevel.ADVANCED

    def test_advanced_crankshaft(self):
        assert assess_skill_level("Crankshaft bearing replacement") == SkillLevel.ADVANCED

    def test_advanced_top_end_rebuild(self):
        assert assess_skill_level("Top end rebuild with new pistons") == SkillLevel.ADVANCED

    def test_default_intermediate(self):
        """Unknown repairs default to intermediate."""
        assert assess_skill_level("Something unusual and unrecognized") == SkillLevel.INTERMEDIATE

    def test_case_insensitive(self):
        assert assess_skill_level("OIL CHANGE") == SkillLevel.BEGINNER
        assert assess_skill_level("ENGINE REBUILD") == SkillLevel.ADVANCED


# --- REPAIR_PROMPT validation tests ---


class TestRepairPrompt:
    def test_prompt_not_empty(self):
        assert len(REPAIR_PROMPT) > 100

    def test_prompt_mentions_torque_specs(self):
        assert "torque" in REPAIR_PROMPT.lower()

    def test_prompt_mentions_safety(self):
        assert "safety" in REPAIR_PROMPT.lower()

    def test_prompt_mentions_json(self):
        assert "JSON" in REPAIR_PROMPT

    def test_prompt_mentions_skill_levels(self):
        assert "beginner" in REPAIR_PROMPT.lower()
        assert "intermediate" in REPAIR_PROMPT.lower()
        assert "advanced" in REPAIR_PROMPT.lower()

    def test_prompt_mentions_fuel_warning(self):
        assert "fuel" in REPAIR_PROMPT.lower()

    def test_prompt_mentions_brake_warning(self):
        assert "brake" in REPAIR_PROMPT.lower()

    def test_prompt_mentions_electrical_warning(self):
        assert "electrical" in REPAIR_PROMPT.lower()

    def test_prompt_mentions_alternative_approaches(self):
        assert "alternative" in REPAIR_PROMPT.lower() or "DIY" in REPAIR_PROMPT


# --- RepairProcedureGenerator mocked API tests ---


def _make_mock_client(response_text: str) -> MagicMock:
    """Create a mock DiagnosticClient that returns the given response."""
    mock_client = MagicMock()
    mock_usage = TokenUsage(
        input_tokens=500,
        output_tokens=800,
        model=MODEL_ALIASES["haiku"],
        cost_estimate=0.0036,
        latency_ms=1200,
    )
    mock_client.ask.return_value = (response_text, mock_usage)
    return mock_client


class TestRepairProcedureGenerator:
    def test_generate_returns_structured_procedure(self):
        """Mocked API returns valid JSON -> parsed into RepairProcedure."""
        api_response = json.dumps({
            "title": "Stator Replacement",
            "description": "Replace failed stator on 2005 Honda CBR600RR.",
            "steps": [
                {"step_number": 1, "instruction": "Disconnect battery negative terminal.", "tip": None, "warning": "Always disconnect battery first."},
                {"step_number": 2, "instruction": "Drain engine oil into a catch pan.", "tip": "Warm the engine first for faster draining.", "warning": None},
                {"step_number": 3, "instruction": "Remove stator cover bolts (8mm).", "tip": "Use a 6-point socket.", "warning": None},
            ],
            "tools_needed": ["8mm socket", "torque wrench", "oil drain pan"],
            "parts_needed": ["OEM stator", "cover gasket"],
            "estimated_hours": 2.5,
            "skill_level": "intermediate",
            "safety_warnings": ["Disconnect battery before electrical work."],
            "notes": "Aftermarket stators from Rick's Motorsport are a quality option.",
        })
        mock_client = _make_mock_client(api_response)
        generator = RepairProcedureGenerator(mock_client)

        proc, usage = generator.generate(
            diagnosis="Stator failure — not charging",
            make="Honda",
            model="CBR600RR",
            year=2005,
        )

        assert proc.title == "Stator Replacement"
        assert len(proc.steps) == 3
        assert proc.steps[0].warning == "Always disconnect battery first."
        assert proc.estimated_hours == 2.5
        assert proc.skill_level == SkillLevel.INTERMEDIATE
        assert len(proc.tools_needed) == 3
        assert len(proc.parts_needed) == 2
        assert usage.input_tokens == 500
        mock_client.ask.assert_called_once()

    def test_generate_handles_json_in_code_fence(self):
        """API returns JSON wrapped in markdown code fences."""
        inner_json = json.dumps({
            "title": "Oil Change",
            "description": "Routine oil and filter change.",
            "steps": [{"step_number": 1, "instruction": "Drain old oil."}],
            "tools_needed": ["17mm wrench"],
            "parts_needed": ["4 quarts 10W-40"],
            "estimated_hours": 0.5,
            "skill_level": "beginner",
            "safety_warnings": [],
            "notes": None,
        })
        api_response = f"```json\n{inner_json}\n```"
        mock_client = _make_mock_client(api_response)
        generator = RepairProcedureGenerator(mock_client)

        proc, usage = generator.generate(
            diagnosis="Routine maintenance",
            make="Yamaha",
            model="MT-09",
            year=2021,
        )

        assert proc.title == "Oil Change"
        assert proc.skill_level == SkillLevel.BEGINNER

    def test_generate_bad_json_fallback(self):
        """API returns non-JSON text -> fallback procedure created."""
        api_response = "I think you should check the stator output with a multimeter. Here are the steps..."
        mock_client = _make_mock_client(api_response)
        generator = RepairProcedureGenerator(mock_client)

        proc, usage = generator.generate(
            diagnosis="Charging system failure",
            make="Kawasaki",
            model="ZX-6R",
            year=2012,
        )

        assert "Repair:" in proc.title
        assert len(proc.steps) == 1
        assert proc.steps[0].warning is not None
        assert "not in structured JSON" in proc.notes
        assert usage.input_tokens == 500

    def test_generate_passes_correct_prompt(self):
        """Verify the generator sends the right system prompt and user content."""
        api_response = json.dumps({
            "title": "Brake Pad Replacement",
            "description": "Replace front brake pads.",
            "steps": [{"step_number": 1, "instruction": "Remove caliper."}],
            "tools_needed": ["12mm socket"],
            "parts_needed": ["Front brake pads"],
            "estimated_hours": 0.5,
            "skill_level": "beginner",
            "safety_warnings": ["Verify brake function before riding."],
        })
        mock_client = _make_mock_client(api_response)
        generator = RepairProcedureGenerator(mock_client)

        proc, usage = generator.generate(
            diagnosis="Front brake pads worn",
            make="Suzuki",
            model="SV650",
            year=2007,
        )

        call_args = mock_client.ask.call_args
        assert "2007 Suzuki SV650" in call_args.kwargs.get("prompt", call_args[0][0] if call_args[0] else "")
        assert call_args.kwargs.get("system") == REPAIR_PROMPT

    def test_generate_empty_response_fallback(self):
        """API returns empty string -> fallback procedure."""
        mock_client = _make_mock_client("")
        generator = RepairProcedureGenerator(mock_client)

        proc, usage = generator.generate(
            diagnosis="Unknown issue",
            make="Harley-Davidson",
            model="Sportster 1200",
            year=2008,
        )

        assert len(proc.steps) == 1
        assert "consult service manual" in proc.steps[0].instruction.lower()
