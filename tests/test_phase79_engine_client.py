"""Phase 79 — Claude API integration + base client tests.

All tests use mocked API calls — no live API key required.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from motodiag.engine.client import (
    DiagnosticClient,
    _calculate_cost,
    _resolve_model,
    MODEL_PRICING,
    MODEL_ALIASES,
)
from motodiag.engine.models import (
    DiagnosticResponse,
    DiagnosisItem,
    DiagnosticSeverity,
    TokenUsage,
    SessionMetrics,
)
from motodiag.engine.prompts import (
    DIAGNOSTIC_SYSTEM_PROMPT,
    build_vehicle_context,
    build_symptom_context,
    build_knowledge_context,
    build_full_prompt,
)


# --- Model resolution and pricing ---


class TestModelResolution:
    def test_resolve_haiku_alias(self):
        assert _resolve_model("haiku") == "claude-haiku-4-5-20251001"

    def test_resolve_sonnet_alias(self):
        assert _resolve_model("sonnet") == "claude-sonnet-4-5-20241022"

    def test_resolve_full_model_id_passthrough(self):
        full_id = "claude-haiku-4-5-20251001"
        assert _resolve_model(full_id) == full_id

    def test_resolve_unknown_passthrough(self):
        assert _resolve_model("some-custom-model") == "some-custom-model"


class TestCostCalculation:
    def test_haiku_cost(self):
        cost = _calculate_cost("claude-haiku-4-5-20251001", 1000, 500)
        # 1000 input * 0.80/1M + 500 output * 4.00/1M = 0.0008 + 0.002 = 0.0028
        assert 0.002 < cost < 0.004

    def test_sonnet_cost_higher(self):
        haiku_cost = _calculate_cost("claude-haiku-4-5-20251001", 1000, 500)
        sonnet_cost = _calculate_cost("claude-sonnet-4-5-20241022", 1000, 500)
        assert sonnet_cost > haiku_cost

    def test_zero_tokens_zero_cost(self):
        assert _calculate_cost("claude-haiku-4-5-20251001", 0, 0) == 0.0

    def test_unknown_model_uses_fallback_pricing(self):
        cost = _calculate_cost("unknown-model", 1000, 500)
        assert cost > 0  # Uses fallback pricing


# --- Response models ---


class TestResponseModels:
    def test_diagnosis_item_creation(self):
        item = DiagnosisItem(
            diagnosis="Stator winding failure",
            confidence=0.85,
            severity=DiagnosticSeverity.HIGH,
            evidence=["Battery voltage drops below 12V at 5000 RPM"],
            repair_steps=["Test stator AC output", "Replace stator + reg/rec"],
            estimated_hours=2.5,
            estimated_cost="$200-350",
            parts_needed=["Stator", "MOSFET reg/rec"],
        )
        assert item.confidence == 0.85
        assert item.severity == DiagnosticSeverity.HIGH
        assert len(item.evidence) == 1
        assert len(item.repair_steps) == 2

    def test_diagnostic_response_creation(self):
        response = DiagnosticResponse(
            vehicle_summary="2015 Suzuki GSX-R600",
            symptoms_acknowledged=["battery not charging", "dim lights at idle"],
            diagnoses=[
                DiagnosisItem(
                    diagnosis="Stator failure",
                    confidence=0.9,
                    severity=DiagnosticSeverity.HIGH,
                )
            ],
        )
        assert response.vehicle_summary == "2015 Suzuki GSX-R600"
        assert len(response.diagnoses) == 1
        assert response.diagnoses[0].confidence == 0.9

    def test_token_usage_creation(self):
        usage = TokenUsage(
            input_tokens=500,
            output_tokens=300,
            model="claude-haiku-4-5-20251001",
            cost_estimate=0.0028,
            latency_ms=450,
        )
        assert usage.input_tokens == 500
        assert usage.output_tokens == 300

    def test_session_metrics_accumulation(self):
        session = SessionMetrics(session_id="test-session")
        usage1 = TokenUsage(input_tokens=100, output_tokens=50, model="haiku", cost_estimate=0.001, latency_ms=200)
        usage2 = TokenUsage(input_tokens=200, output_tokens=100, model="haiku", cost_estimate=0.002, latency_ms=300)
        session.add_usage(usage1)
        session.add_usage(usage2)
        assert session.call_count == 2
        assert session.total_input_tokens == 300
        assert session.total_output_tokens == 150
        assert session.total_tokens == 450
        assert session.total_cost == 0.003
        assert session.avg_latency_ms == 250.0

    def test_session_metrics_multiple_models(self):
        session = SessionMetrics(session_id="test")
        session.add_usage(TokenUsage(model="haiku", cost_estimate=0.001))
        session.add_usage(TokenUsage(model="sonnet", cost_estimate=0.01))
        assert len(session.models_used) == 2
        assert "haiku" in session.models_used
        assert "sonnet" in session.models_used


# --- Prompt builders ---


class TestPromptBuilders:
    def test_vehicle_context_basic(self):
        ctx = build_vehicle_context("Honda", "CBR600RR", 2007)
        assert "2007 Honda CBR600RR" in ctx

    def test_vehicle_context_with_mileage(self):
        ctx = build_vehicle_context("Suzuki", "SV650", 2003, mileage=35000)
        assert "35,000" in ctx
        assert "SV650" in ctx

    def test_vehicle_context_with_modifications(self):
        ctx = build_vehicle_context(
            "Kawasaki", "ZX-6R", 2012,
            modifications=["Akrapovic exhaust", "Power Commander V"],
        )
        assert "Akrapovic exhaust" in ctx
        assert "Power Commander V" in ctx

    def test_symptom_context(self):
        ctx = build_symptom_context(["won't start", "clicking sound"])
        assert "won't start" in ctx
        assert "clicking sound" in ctx
        assert "Reported symptoms" in ctx

    def test_symptom_context_with_description(self):
        ctx = build_symptom_context(
            ["overheating"],
            description="Only in traffic, fine on highway",
        )
        assert "overheating" in ctx
        assert "Only in traffic" in ctx

    def test_knowledge_context_empty(self):
        assert build_knowledge_context([]) == ""

    def test_knowledge_context_with_issues(self):
        issues = [
            {
                "title": "GSX-R600 stator failure",
                "severity": "high",
                "symptoms": ["battery not charging"],
                "causes": ["Winding insulation breakdown"],
                "fix_procedure": "Replace stator + MOSFET reg/rec upgrade...",
            }
        ]
        ctx = build_knowledge_context(issues)
        assert "GSX-R600 stator failure" in ctx
        assert "high" in ctx
        assert "battery not charging" in ctx

    def test_full_prompt_assembly(self):
        vehicle = build_vehicle_context("Honda", "CBR600RR", 2007)
        symptoms = build_symptom_context(["won't start"])
        full = build_full_prompt(vehicle, symptoms)
        assert "2007 Honda CBR600RR" in full
        assert "won't start" in full
        assert "DiagnosticResponse" in full

    def test_system_prompt_exists_and_has_content(self):
        assert len(DIAGNOSTIC_SYSTEM_PROMPT) > 200
        assert "MotoDiag" in DIAGNOSTIC_SYSTEM_PROMPT
        assert "mechanic" in DIAGNOSTIC_SYSTEM_PROMPT.lower()


# --- Client initialization ---


class TestClientInit:
    def test_client_init_with_key(self):
        client = DiagnosticClient(api_key="sk-test-key-12345678")
        assert client.is_configured is True
        assert client.model == "claude-haiku-4-5-20251001"

    def test_client_init_without_key(self):
        with patch.dict("os.environ", {}, clear=True):
            client = DiagnosticClient(api_key="")
            # May or may not be configured depending on settings
            # Just verify it doesn't crash

    def test_client_model_override(self):
        client = DiagnosticClient(api_key="sk-test", model="sonnet")
        assert client.model == "claude-sonnet-4-5-20241022"

    def test_client_session_initialized(self):
        client = DiagnosticClient(api_key="sk-test")
        assert client.session.call_count == 0
        assert client.session.total_cost == 0.0
        assert client.session.session_id.startswith("diag-")

    def test_client_get_session_summary(self):
        client = DiagnosticClient(api_key="sk-test")
        summary = client.get_session_summary()
        assert "session_id" in summary
        assert "call_count" in summary
        assert summary["call_count"] == 0
        assert summary["total_cost_usd"] == "$0.0000"


# --- Client API call (mocked) ---


class TestClientMockedAPI:
    def _make_mock_response(self, text: str, input_tokens: int = 500, output_tokens: int = 300):
        """Create a mock Anthropic API response."""
        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.text = text
        mock_response.content = [mock_block]
        mock_response.usage.input_tokens = input_tokens
        mock_response.usage.output_tokens = output_tokens
        return mock_response

    @patch("motodiag.engine.client.DiagnosticClient._get_client")
    def test_ask_returns_text_and_usage(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = self._make_mock_response(
            "The stator is likely failed.", 500, 300
        )
        mock_get_client.return_value = mock_client

        client = DiagnosticClient(api_key="sk-test")
        client._client = mock_client

        text, usage = client.ask("Why is the battery dying?")
        assert "stator" in text.lower()
        assert usage.input_tokens == 500
        assert usage.output_tokens == 300
        assert usage.cost_estimate > 0
        assert client.session.call_count == 1

    @patch("motodiag.engine.client.DiagnosticClient._get_client")
    def test_diagnose_returns_structured_response(self, mock_get_client):
        # Create a valid JSON diagnostic response
        diagnostic_json = json.dumps({
            "vehicle_summary": "2015 Suzuki GSX-R600",
            "symptoms_acknowledged": ["battery not charging"],
            "diagnoses": [
                {
                    "diagnosis": "Stator winding failure",
                    "confidence": 0.85,
                    "severity": "high",
                    "evidence": ["Voltage test shows 11.5V at 5000 RPM"],
                    "repair_steps": ["Test stator AC", "Replace stator + reg/rec"],
                    "estimated_hours": 2.5,
                    "parts_needed": ["Stator", "MOSFET reg/rec"],
                }
            ],
        })

        mock_client = MagicMock()
        mock_client.messages.create.return_value = self._make_mock_response(diagnostic_json)
        mock_get_client.return_value = mock_client

        client = DiagnosticClient(api_key="sk-test")
        client._client = mock_client

        response, usage = client.diagnose(
            make="Suzuki",
            model_name="GSX-R600",
            year=2015,
            symptoms=["battery not charging"],
        )

        assert isinstance(response, DiagnosticResponse)
        assert response.vehicle_summary == "2015 Suzuki GSX-R600"
        assert len(response.diagnoses) == 1
        assert response.diagnoses[0].confidence == 0.85
        assert response.diagnoses[0].severity == DiagnosticSeverity.HIGH
        assert usage.input_tokens > 0

    @patch("motodiag.engine.client.DiagnosticClient._get_client")
    def test_diagnose_with_knowledge_context(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = self._make_mock_response(
            '{"vehicle_summary": "2015 Suzuki GSX-R600", "symptoms_acknowledged": ["noise"], "diagnoses": []}'
        )
        mock_get_client.return_value = mock_client

        client = DiagnosticClient(api_key="sk-test")
        client._client = mock_client

        known_issues = [
            {
                "title": "CCT rattle",
                "severity": "high",
                "symptoms": ["noise"],
                "causes": ["Automatic tensioner worn"],
                "fix_procedure": "Replace with APE manual CCT...",
            }
        ]

        response, usage = client.diagnose(
            make="Suzuki",
            model_name="GSX-R600",
            year=2015,
            symptoms=["noise"],
            known_issues=known_issues,
        )

        # Verify knowledge context was passed in the prompt
        call_args = mock_client.messages.create.call_args
        user_message = call_args[1]["messages"][0]["content"]
        assert "CCT rattle" in user_message
        assert "APE manual CCT" in user_message

    @patch("motodiag.engine.client.DiagnosticClient._get_client")
    def test_diagnose_fallback_on_unparseable_response(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = self._make_mock_response(
            "This is not valid JSON — just a plain text response about the diagnosis."
        )
        mock_get_client.return_value = mock_client

        client = DiagnosticClient(api_key="sk-test")
        client._client = mock_client

        response, usage = client.diagnose(
            make="Honda",
            model_name="CBR600RR",
            year=2007,
            symptoms=["won't start"],
        )

        # Should still return a valid DiagnosticResponse with fallback
        assert isinstance(response, DiagnosticResponse)
        assert "2007 Honda CBR600RR" in response.vehicle_summary
        assert len(response.diagnoses) == 1
        assert response.notes is not None
        assert "not in structured JSON" in response.notes

    @patch("motodiag.engine.client.DiagnosticClient._get_client")
    def test_session_metrics_accumulate_across_calls(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = self._make_mock_response("Response 1", 100, 50)
        mock_get_client.return_value = mock_client

        client = DiagnosticClient(api_key="sk-test")
        client._client = mock_client

        client.ask("Question 1")
        mock_client.messages.create.return_value = self._make_mock_response("Response 2", 200, 100)
        client.ask("Question 2")

        assert client.session.call_count == 2
        assert client.session.total_input_tokens == 300
        assert client.session.total_output_tokens == 150
        assert client.session.total_cost > 0
