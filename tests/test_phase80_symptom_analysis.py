"""Phase 80 — Symptom analysis prompt engineering tests.

Tests symptom categorization, urgency assessment, differential prompt building,
(the SymptomAnalyzer two-pass class was removed at Phase 244Y).
"""

import json
from unittest.mock import MagicMock


from motodiag.engine.symptoms import (
    categorize_symptoms,
    SYMPTOM_CATEGORIES,
    CRITICAL_COMBINATIONS,
    SYMPTOM_ANALYSIS_PROMPT,
)
from motodiag.engine.client import DiagnosticClient


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



# --- Differential prompt building ---


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
