"""Phase 82 — Multi-step diagnostic workflow tests.

Tests workflow creation, step progression, result reporting, predefined templates,
and AI-generated steps with mocked API calls.
"""

import json
from unittest.mock import MagicMock

import pytest

from motodiag.engine.workflows import (
    WorkflowStep,
    StepResult,
    WorkflowStatus,
    DiagnosticWorkflow,
    create_no_start_workflow,
    create_charging_workflow,
    create_overheating_workflow,
    generate_next_step,
    WORKFLOW_STEP_PROMPT,
)
from motodiag.engine.client import DiagnosticClient


# --- WorkflowStep model ---


class TestWorkflowStep:
    def test_step_creation(self):
        step = WorkflowStep(
            step_number=1,
            test_instruction="Check battery voltage with multimeter.",
            expected_pass="12.4V or higher",
            expected_fail="Below 12.0V",
            diagnosis_if_fail="Dead battery",
        )
        assert step.step_number == 1
        assert step.result is None
        assert step.diagnosis_if_fail == "Dead battery"

    def test_step_result_recording(self):
        step = WorkflowStep(step_number=1, test_instruction="Test")
        step.result = StepResult.FAIL
        step.mechanic_notes = "Reads 10.8V"
        assert step.result == StepResult.FAIL
        assert step.mechanic_notes == "Reads 10.8V"


# --- DiagnosticWorkflow state management ---


class TestDiagnosticWorkflow:
    def _make_simple_workflow(self) -> DiagnosticWorkflow:
        return DiagnosticWorkflow(
            workflow_id="test-wf",
            vehicle_context="2015 Suzuki GSX-R600",
            initial_complaint="won't start",
            steps=[
                WorkflowStep(
                    step_number=1,
                    test_instruction="Check battery voltage",
                    expected_pass="12.4V+",
                    expected_fail="Below 12V",
                    diagnosis_if_fail="Dead battery",
                ),
                WorkflowStep(
                    step_number=2,
                    test_instruction="Check fuel pump prime",
                    expected_pass="Pump buzzes for 2-3 seconds",
                    expected_fail="No buzz",
                    diagnosis_if_fail="Fuel pump or relay failure",
                ),
                WorkflowStep(
                    step_number=3,
                    test_instruction="Check for spark",
                    expected_pass="Blue/white spark visible",
                    expected_fail="No spark",
                    diagnosis_if_fail="Ignition system failure",
                ),
            ],
        )

    def test_get_current_step(self):
        wf = self._make_simple_workflow()
        step = wf.get_current_step()
        assert step is not None
        assert step.step_number == 1
        assert "battery" in step.test_instruction.lower()

    def test_report_result_advances_workflow(self):
        wf = self._make_simple_workflow()
        next_step = wf.report_result(StepResult.PASS)
        assert next_step is not None
        assert next_step.step_number == 2
        assert wf.current_step_index == 1
        assert wf.status == WorkflowStatus.IN_PROGRESS

    def test_fail_result_sets_working_diagnosis(self):
        wf = self._make_simple_workflow()
        wf.report_result(StepResult.FAIL, notes="Battery reads 10.2V")
        assert wf.working_diagnosis == "Dead battery"

    def test_pass_result_eliminates_cause(self):
        wf = self._make_simple_workflow()
        wf.remaining_causes = ["Dead battery", "Fuel pump failure"]
        wf.report_result(StepResult.PASS)
        assert "Dead battery" in wf.eliminated_causes

    def test_workflow_completes_on_fail_diagnosis(self):
        wf = self._make_simple_workflow()
        wf.report_result(StepResult.FAIL)  # Battery fails → working diagnosis set
        assert wf.is_complete() is True
        assert wf.status == WorkflowStatus.COMPLETE

    def test_workflow_completes_when_all_steps_done(self):
        wf = self._make_simple_workflow()
        wf.report_result(StepResult.PASS)  # Step 1 pass
        wf.report_result(StepResult.PASS)  # Step 2 pass
        wf.report_result(StepResult.PASS)  # Step 3 pass — all steps done
        assert wf.is_complete() is True

    def test_max_steps_limit(self):
        wf = DiagnosticWorkflow(
            workflow_id="test",
            max_steps=2,
            steps=[
                WorkflowStep(step_number=i, test_instruction=f"Test {i}")
                for i in range(5)
            ],
        )
        wf.report_result(StepResult.PASS)
        wf.report_result(StepResult.PASS)
        assert wf.is_complete() is True  # Hit max_steps

    def test_results_summary(self):
        wf = self._make_simple_workflow()
        wf.report_result(StepResult.PASS, notes="12.6V")
        wf.report_result(StepResult.FAIL, notes="No pump sound")

        summary = wf.get_results_summary()
        assert summary["steps_completed"] == 2
        assert summary["status"] == "complete"
        assert summary["working_diagnosis"] == "Fuel pump or relay failure"
        assert len(summary["test_results"]) == 3

    def test_unclear_result_handling(self):
        wf = self._make_simple_workflow()
        next_step = wf.report_result(StepResult.UNCLEAR, notes="Can't get a good reading")
        assert next_step is not None  # Should still advance
        assert wf.working_diagnosis == ""  # No diagnosis from unclear result

    def test_skipped_result_handling(self):
        wf = self._make_simple_workflow()
        next_step = wf.report_result(StepResult.SKIPPED, notes="Don't have a multimeter")
        assert next_step is not None  # Should still advance


# --- Predefined workflow templates ---


class TestPredefinedWorkflows:
    def test_no_start_workflow_creation(self):
        wf = create_no_start_workflow("2007 Honda CBR600RR")
        assert wf.workflow_type == "no_start"
        assert len(wf.steps) >= 4
        assert wf.vehicle_context == "2007 Honda CBR600RR"
        assert wf.status == WorkflowStatus.NOT_STARTED
        assert len(wf.remaining_causes) >= 4

    def test_no_start_workflow_first_step_is_battery(self):
        wf = create_no_start_workflow("2015 Kawasaki ZX-6R")
        step = wf.get_current_step()
        assert "battery" in step.test_instruction.lower()
        assert "voltage" in step.test_instruction.lower()

    def test_charging_workflow_creation(self):
        wf = create_charging_workflow("2010 Suzuki GSX-R750")
        assert wf.workflow_type == "charging"
        assert len(wf.steps) >= 3
        assert len(wf.remaining_causes) >= 4

    def test_charging_workflow_first_step_is_voltage(self):
        wf = create_charging_workflow("2010 Suzuki GSX-R750")
        step = wf.get_current_step()
        assert "5000 RPM" in step.test_instruction
        assert "voltage" in step.test_instruction.lower()

    def test_overheating_workflow_creation(self):
        wf = create_overheating_workflow("2018 Yamaha MT-09")
        assert wf.workflow_type == "overheating"
        assert len(wf.steps) >= 3

    def test_overheating_workflow_first_step_is_coolant(self):
        wf = create_overheating_workflow("2018 Yamaha MT-09")
        step = wf.get_current_step()
        assert "coolant" in step.test_instruction.lower()

    def test_all_templates_have_mechanic_friendly_instructions(self):
        """Test instructions should be clear and specific, not just jargon."""
        for factory in [create_no_start_workflow, create_charging_workflow, create_overheating_workflow]:
            wf = factory("2020 Honda CB500F")
            for step in wf.steps:
                # Each instruction should be substantial (not just "check battery")
                assert len(step.test_instruction) >= 50, f"Step {step.step_number} instruction too brief: {step.test_instruction[:50]}"
                # Expected pass/fail should be filled in
                assert step.expected_pass, f"Step {step.step_number} missing expected_pass"
                assert step.expected_fail, f"Step {step.step_number} missing expected_fail"


# --- Full workflow walkthrough ---


class TestWorkflowWalkthrough:
    def test_no_start_battery_fail_path(self):
        """Simulate: battery is dead → diagnosis found in step 1."""
        wf = create_no_start_workflow("2012 Kawasaki Ninja 650")
        wf.report_result(StepResult.FAIL, notes="10.2V — battery is dead")
        assert wf.is_complete() is True
        assert wf.working_diagnosis == "Dead or weak battery"

    def test_no_start_fuel_fail_path(self):
        """Simulate: battery OK → no fuel pump prime → fuel system diagnosis."""
        wf = create_no_start_workflow("2008 Suzuki SV650")
        wf.report_result(StepResult.PASS, notes="12.6V")  # Battery OK
        wf.report_result(StepResult.FAIL, notes="No pump sound at all")  # No fuel
        assert wf.is_complete() is True
        assert "fuel" in wf.working_diagnosis.lower()

    def test_charging_stator_fail_path(self):
        """Simulate: low voltage → stator AC low → stator failure diagnosed."""
        wf = create_charging_workflow("2005 Honda CBR600RR")
        wf.report_result(StepResult.FAIL, notes="12.1V at 5000 RPM")  # Low voltage
        assert wf.is_complete() is True
        assert wf.working_diagnosis  # Should have a diagnosis


# --- AI-generated workflow step ---


class TestGenerateNextStep:
    def test_generate_step_with_mocked_api(self):
        step_json = json.dumps({
            "test_instruction": "Check the regulator/rectifier output with a multimeter.",
            "expected_pass": "13.8-14.5V at the reg/rec output connector",
            "expected_fail": "Below 13.5V or above 15.0V",
            "diagnosis_if_fail": "Regulator/rectifier internal failure",
            "next_step_if_pass": "Check stator connector condition",
            "next_step_if_fail": "Replace reg/rec with MOSFET upgrade",
        })

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.text = step_json
        mock_response.content = [mock_block]
        mock_response.usage.input_tokens = 400
        mock_response.usage.output_tokens = 200
        mock_client.messages.create.return_value = mock_response

        client = DiagnosticClient(api_key="sk-test")
        client._client = mock_client

        wf = create_charging_workflow("2015 Suzuki GSX-R600")
        wf.report_result(StepResult.PASS)  # Voltage OK at RPM
        wf.report_result(StepResult.PASS)  # Stator AC OK

        step, usage = generate_next_step(client, wf)
        assert step is not None
        assert "regulator" in step.test_instruction.lower()
        assert usage.input_tokens == 400

    def test_generate_step_bad_json_returns_none(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.text = "This is not valid JSON."
        mock_response.content = [mock_block]
        mock_response.usage.input_tokens = 300
        mock_response.usage.output_tokens = 100
        mock_client.messages.create.return_value = mock_response

        client = DiagnosticClient(api_key="sk-test")
        client._client = mock_client

        wf = DiagnosticWorkflow(workflow_id="test", vehicle_context="2020 Honda CB500F")
        step, usage = generate_next_step(client, wf)
        assert step is None
        assert usage is not None  # Usage is still tracked even on parse failure


# --- Workflow prompt template ---


class TestWorkflowPrompt:
    def test_prompt_template_has_placeholders(self):
        assert "{previous_results}" in WORKFLOW_STEP_PROMPT
        assert "{working_diagnosis}" in WORKFLOW_STEP_PROMPT
        assert "{eliminated_causes}" in WORKFLOW_STEP_PROMPT
        assert "{remaining_causes}" in WORKFLOW_STEP_PROMPT

    def test_prompt_requests_json_response(self):
        assert "JSON" in WORKFLOW_STEP_PROMPT
        assert "test_instruction" in WORKFLOW_STEP_PROMPT
