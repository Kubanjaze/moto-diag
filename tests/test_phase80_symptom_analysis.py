"""Phase 80 — Symptom analysis prompt engineering tests.

Tests symptom categorization, urgency assessment, differential prompt building,
and the SymptomAnalyzer two-pass approach with mocked API calls.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from motodiag.engine.symptoms import (
    categorize_symptoms,
    assess_urgency,
    build_differential_prompt,
    SymptomAnalyzer,
    SYMPTOM_CATEGORIES,
    CRITICAL_COMBINATIONS,
    SYMPTOM_ANALYSIS_PROMPT,
)
from motodiag.engine.client import DiagnosticClient
from motodiag.engine.models import DiagnosticResponse, DiagnosticSeverity


# --- Symptom categorization ---


class TestSymptomCategorization:
    def test_electrical_symptoms(self):
        result = categorize_symptoms(["won't start", "battery not charging"])
        assert "electrical" in result
        assert len(result["electrical"]) == 2

    def test_fuel_symptoms(self):
        result = categorize_symptoms(["rough idle", "backfires"])
        assert "fuel" in result
        assert len(result["fuel"]) == 2

    def test_mechanical_symptoms(self):
        result = categorize_symptoms(["noise", "vibration at speed"])
        assert "mechanical" in result
        assert len(result["mechanical"]) >= 1

    def test_cooling_symptoms(self):
        result = categorize_symptoms(["overheating", "coolant leak"])
        assert "cooling" in result
        assert len(result["cooling"]) == 2

    def test_multi_category_symptom(self):
        """Some symptoms map to multiple categories."""
        result = categorize_symptoms(["vibration at speed"])
        # vibration at speed is in both mechanical and drivetrain
        categories_with_match = [k for k, v in result.items() if "vibration at speed" in v]
        assert len(categories_with_match) >= 1

    def test_uncategorized_symptom(self):
        result = categorize_symptoms(["makes a weird smell when hot"])
        assert "other" in result
        assert "makes a weird smell when hot" in result["other"]

    def test_mixed_symptoms(self):
        result = categorize_symptoms([
            "won't start",
            "rough idle",
            "overheating",
            "noise",
        ])
        assert "electrical" in result
        assert "fuel" in result
        assert "cooling" in result
        assert "mechanical" in result

    def test_empty_symptoms(self):
        result = categorize_symptoms([])
        assert result == {}


# --- Urgency assessment ---


class TestUrgencyAssessment:
    def test_overheating_and_power_loss_critical(self):
        alerts = assess_urgency(["overheating", "loss of power", "steam"])
        assert len(alerts) >= 1
        assert any("CRITICAL" in a for a in alerts)

    def test_fuel_smell_and_wont_start_critical(self):
        alerts = assess_urgency(["fuel smell", "won't start"])
        assert len(alerts) >= 1
        assert any("fire risk" in a.lower() for a in alerts)

    def test_brake_failure_critical(self):
        alerts = assess_urgency(["spongy brake lever", "brake fade"])
        assert len(alerts) >= 1
        assert any("brake" in a.lower() for a in alerts)

    def test_no_critical_for_minor_symptoms(self):
        alerts = assess_urgency(["rough idle"])
        assert len(alerts) == 0

    def test_no_critical_for_empty_symptoms(self):
        alerts = assess_urgency([])
        assert len(alerts) == 0

    def test_noise_and_power_loss_warning(self):
        alerts = assess_urgency(["noise", "loss of power", "check engine light on"])
        assert len(alerts) >= 1
        assert any("WARNING" in a or "CRITICAL" in a for a in alerts)


# --- Differential prompt building ---


class TestDifferentialPrompt:
    def test_basic_prompt(self):
        prompt = build_differential_prompt(
            vehicle_context="Vehicle: 2015 Suzuki GSX-R600",
            symptoms=["battery not charging", "dim lights"],
        )
        assert "2015 Suzuki GSX-R600" in prompt
        assert "battery not charging" in prompt
        assert "DiagnosticResponse" in prompt

    def test_prompt_with_categories(self):
        prompt = build_differential_prompt(
            vehicle_context="Vehicle: 2007 Honda CBR600RR",
            symptoms=["won't start"],
            categorized_symptoms={"electrical": ["won't start"]},
        )
        assert "ELECTRICAL" in prompt

    def test_prompt_with_urgency_alerts(self):
        prompt = build_differential_prompt(
            vehicle_context="Vehicle: 2003 Yamaha R6",
            symptoms=["overheating", "loss of power"],
            urgency_alerts=["CRITICAL: Possible head gasket failure"],
        )
        assert "SAFETY ALERTS" in prompt
        assert "CRITICAL" in prompt

    def test_prompt_with_knowledge_context(self):
        issues = [
            {
                "title": "GSX-R600 stator failure",
                "severity": "high",
                "symptoms": ["battery not charging"],
                "causes": ["Winding insulation breakdown"],
                "fix_procedure": "Replace stator...",
            }
        ]
        prompt = build_differential_prompt(
            vehicle_context="Vehicle: 2015 Suzuki GSX-R600",
            symptoms=["battery not charging"],
            knowledge_matches=issues,
        )
        assert "GSX-R600 stator failure" in prompt
        assert "Winding insulation breakdown" in prompt

    def test_prompt_with_description(self):
        prompt = build_differential_prompt(
            vehicle_context="Vehicle: 2010 Kawasaki ZX-6R",
            symptoms=["overheating"],
            description="Only in traffic, fine on the highway",
        )
        assert "Only in traffic" in prompt


# --- SymptomAnalyzer with mocked API ---


class TestSymptomAnalyzerMocked:
    def _make_mock_client(self, response_text: str = None):
        """Create a DiagnosticClient with mocked API."""
        if response_text is None:
            response_text = json.dumps({
                "vehicle_summary": "2015 Suzuki GSX-R600",
                "symptoms_acknowledged": ["battery not charging"],
                "diagnoses": [
                    {
                        "diagnosis": "Stator failure",
                        "confidence": 0.85,
                        "severity": "high",
                        "evidence": ["Low voltage at RPM"],
                        "repair_steps": ["Test stator AC output"],
                    }
                ],
            })

        mock_anthropic_client = MagicMock()
        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.text = response_text
        mock_response.content = [mock_block]
        mock_response.usage.input_tokens = 800
        mock_response.usage.output_tokens = 400
        mock_anthropic_client.messages.create.return_value = mock_response

        client = DiagnosticClient(api_key="sk-test")
        client._client = mock_anthropic_client
        return client

    def test_analyze_returns_response_and_metadata(self):
        client = self._make_mock_client()
        analyzer = SymptomAnalyzer(client)

        response, usage, metadata = analyzer.analyze(
            make="Suzuki",
            model_name="GSX-R600",
            year=2015,
            symptoms=["battery not charging"],
        )

        assert isinstance(response, DiagnosticResponse)
        assert usage.input_tokens == 800
        assert "categorized_symptoms" in metadata
        assert "urgency_alerts" in metadata
        assert "electrical" in metadata["categorized_symptoms"]

    def test_analyze_with_knowledge_context(self):
        client = self._make_mock_client()
        analyzer = SymptomAnalyzer(client)

        known_issues = [
            {
                "title": "Stator failure",
                "severity": "high",
                "symptoms": ["battery not charging"],
                "causes": ["Winding insulation breakdown"],
                "fix_procedure": "Replace stator + MOSFET reg/rec...",
            }
        ]

        response, usage, metadata = analyzer.analyze(
            make="Suzuki",
            model_name="GSX-R600",
            year=2015,
            symptoms=["battery not charging"],
            known_issues=known_issues,
        )

        assert metadata["knowledge_matches_count"] == 1

        # Verify the knowledge context was passed to the API call
        call_args = client._client.messages.create.call_args
        user_message = call_args[1]["messages"][0]["content"]
        assert "Stator failure" in user_message

    def test_analyze_urgency_detection(self):
        client = self._make_mock_client()
        analyzer = SymptomAnalyzer(client)

        response, usage, metadata = analyzer.analyze(
            make="Honda",
            model_name="CBR600RR",
            year=2007,
            symptoms=["overheating", "loss of power", "steam"],
        )

        assert len(metadata["urgency_alerts"]) >= 1
        assert any("CRITICAL" in a for a in metadata["urgency_alerts"])

    def test_analyze_uses_symptom_analysis_prompt(self):
        client = self._make_mock_client()
        analyzer = SymptomAnalyzer(client)

        analyzer.analyze(
            make="Kawasaki",
            model_name="ZX-6R",
            year=2012,
            symptoms=["noise", "rough idle"],
        )

        call_args = client._client.messages.create.call_args
        system_prompt = call_args[1]["system"]
        assert "DIFFERENTIAL DIAGNOSIS" in system_prompt
        assert "SAFETY CHECK" in system_prompt


# --- Prompt template validation ---


class TestPromptTemplate:
    def test_symptom_analysis_prompt_has_all_steps(self):
        assert "STEP 1" in SYMPTOM_ANALYSIS_PROMPT
        assert "STEP 2" in SYMPTOM_ANALYSIS_PROMPT
        assert "STEP 3" in SYMPTOM_ANALYSIS_PROMPT
        assert "STEP 4" in SYMPTOM_ANALYSIS_PROMPT
        assert "STEP 5" in SYMPTOM_ANALYSIS_PROMPT

    def test_symptom_analysis_prompt_mentions_knowledge_base(self):
        assert "knowledge base" in SYMPTOM_ANALYSIS_PROMPT.lower()

    def test_symptom_analysis_prompt_requires_json(self):
        assert "DiagnosticResponse" in SYMPTOM_ANALYSIS_PROMPT

    def test_symptom_categories_cover_major_systems(self):
        assert "electrical" in SYMPTOM_CATEGORIES
        assert "fuel" in SYMPTOM_CATEGORIES
        assert "mechanical" in SYMPTOM_CATEGORIES
        assert "cooling" in SYMPTOM_CATEGORIES
        assert "drivetrain" in SYMPTOM_CATEGORIES
        assert "braking" in SYMPTOM_CATEGORIES

    def test_critical_combinations_exist(self):
        assert len(CRITICAL_COMBINATIONS) >= 3
        for combo in CRITICAL_COMBINATIONS:
            assert "symptoms" in combo
            assert "alert" in combo
            assert len(combo["symptoms"]) >= 2
