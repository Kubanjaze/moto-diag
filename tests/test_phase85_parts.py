"""Phase 85 — Parts + tools recommendation tests.

Tests PartSource enum, PartRecommendation model, ToolRecommendation model,
PartsRecommender with mocked API, prompt validation, and edge cases.
All mocked — zero API calls.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from motodiag.engine.client import MODEL_ALIASES
from motodiag.engine.models import TokenUsage
from motodiag.engine.parts import (
    PartSource,
    PartRecommendation,
    ToolRecommendation,
    PartsRecommender,
    PARTS_PROMPT,
)


# ---------------------------------------------------------------------------
# PartSource enum
# ---------------------------------------------------------------------------


class TestPartSource:
    def test_oem_value(self):
        assert PartSource.OEM == "oem"

    def test_aftermarket_value(self):
        assert PartSource.AFTERMARKET == "aftermarket"

    def test_used_value(self):
        assert PartSource.USED == "used"

    def test_generic_value(self):
        assert PartSource.GENERIC == "generic"

    def test_all_sources_count(self):
        assert len(PartSource) == 4


# ---------------------------------------------------------------------------
# PartRecommendation model
# ---------------------------------------------------------------------------


class TestPartRecommendation:
    def test_minimal_part(self):
        part = PartRecommendation(
            part_name="Stator assembly",
            brand="Rick's Motorsport Electrics",
            price_range_low=120.0,
            price_range_high=180.0,
            source=PartSource.AFTERMARKET,
        )
        assert part.part_name == "Stator assembly"
        assert part.part_number is None
        assert part.notes is None
        assert part.cross_references == []

    def test_part_with_part_number(self):
        part = PartRecommendation(
            part_name="Regulator/Rectifier",
            part_number="21-554",
            brand="Rick's Motorsport Electrics",
            price_range_low=85.0,
            price_range_high=130.0,
            source=PartSource.AFTERMARKET,
        )
        assert part.part_number == "21-554"

    def test_part_with_cross_references(self):
        part = PartRecommendation(
            part_name="Spark plug",
            part_number="CR9EIA-9",
            brand="NGK",
            price_range_low=8.0,
            price_range_high=12.0,
            source=PartSource.AFTERMARKET,
            cross_references=["Denso IU27", "Champion RA8HC"],
        )
        assert len(part.cross_references) == 2
        assert "Denso IU27" in part.cross_references

    def test_part_with_notes(self):
        part = PartRecommendation(
            part_name="Chain kit",
            brand="DID",
            price_range_low=100.0,
            price_range_high=200.0,
            source=PartSource.AFTERMARKET,
            notes="525 pitch for 2003-2006; 2007+ uses 520 conversion",
        )
        assert "525 pitch" in part.notes

    def test_oem_part(self):
        part = PartRecommendation(
            part_name="Cam chain tensioner",
            part_number="14520-MFJ-D01",
            brand="Honda OEM",
            price_range_low=45.0,
            price_range_high=65.0,
            source=PartSource.OEM,
        )
        assert part.source == PartSource.OEM

    def test_price_range_validation(self):
        """Price range low/high must be >= 0."""
        with pytest.raises(Exception):
            PartRecommendation(
                part_name="Bad part",
                brand="None",
                price_range_low=-5.0,
                price_range_high=10.0,
                source=PartSource.GENERIC,
            )


# ---------------------------------------------------------------------------
# ToolRecommendation model
# ---------------------------------------------------------------------------


class TestToolRecommendation:
    def test_essential_tool(self):
        tool = ToolRecommendation(
            tool_name="Flywheel puller",
            specification="27mm x 1.0 LH thread (Honda specific)",
            price_range="$25-40",
            essential=True,
        )
        assert tool.essential is True
        assert tool.alternative is None

    def test_optional_tool_with_alternative(self):
        tool = ToolRecommendation(
            tool_name="Torque wrench",
            specification="3/8 drive, 10-80 ft-lb",
            price_range="$30-80",
            essential=False,
            alternative="Tighten by feel — but torque wrench strongly recommended for critical fasteners",
        )
        assert tool.essential is False
        assert "Tighten by feel" in tool.alternative

    def test_consumable_as_tool(self):
        tool = ToolRecommendation(
            tool_name="Dielectric grease",
            specification="Small tube, silicone-based",
            price_range="$5-10",
            essential=False,
            alternative="Vaseline in an emergency (not ideal)",
        )
        assert tool.tool_name == "Dielectric grease"

    def test_socket_specification(self):
        tool = ToolRecommendation(
            tool_name="Socket",
            specification="10mm, 3/8 drive, 6-point",
            price_range="$5-8",
            essential=True,
        )
        assert "10mm" in tool.specification


# ---------------------------------------------------------------------------
# PARTS_PROMPT validation
# ---------------------------------------------------------------------------


class TestPartsPrompt:
    def test_prompt_mentions_ngk(self):
        assert "NGK" in PARTS_PROMPT

    def test_prompt_mentions_did(self):
        assert "DID" in PARTS_PROMPT

    def test_prompt_mentions_ebc(self):
        assert "EBC" in PARTS_PROMPT

    def test_prompt_mentions_all_balls(self):
        assert "All Balls" in PARTS_PROMPT

    def test_prompt_mentions_ricks(self):
        assert "Rick's Motorsport" in PARTS_PROMPT

    def test_prompt_mentions_oem_vs_aftermarket(self):
        assert "OEM" in PARTS_PROMPT
        assert "aftermarket" in PARTS_PROMPT

    def test_prompt_requires_part_numbers(self):
        assert "part number" in PARTS_PROMPT.lower()

    def test_prompt_requires_cross_references(self):
        assert "cross-reference" in PARTS_PROMPT.lower() or "cross_reference" in PARTS_PROMPT.lower()

    def test_prompt_requires_json_format(self):
        assert "JSON" in PARTS_PROMPT

    def test_prompt_mentions_price_range(self):
        assert "price_range" in PARTS_PROMPT or "price range" in PARTS_PROMPT.lower()


# ---------------------------------------------------------------------------
# PartsRecommender (mocked API)
# ---------------------------------------------------------------------------


def _make_mock_client(response_text: str) -> MagicMock:
    """Create a mock DiagnosticClient that returns the given text."""
    client = MagicMock()
    usage = TokenUsage(
        input_tokens=500,
        output_tokens=800,
        model=MODEL_ALIASES["haiku"],
        cost_estimate=0.0036,
        latency_ms=450,
    )
    client.ask.return_value = (response_text, usage)
    return client


SAMPLE_RESPONSE = json.dumps({
    "parts": [
        {
            "part_name": "Stator assembly",
            "part_number": "21-554",
            "brand": "Rick's Motorsport Electrics",
            "price_range_low": 120.0,
            "price_range_high": 180.0,
            "source": "aftermarket",
            "notes": "Direct replacement for OEM Honda 31120-MFJ-D01",
            "cross_references": ["ElectroSport ESG794", "Caltric GS-104"],
        },
        {
            "part_name": "Regulator/Rectifier",
            "part_number": "10-554",
            "brand": "Rick's Motorsport Electrics",
            "price_range_low": 85.0,
            "price_range_high": 130.0,
            "source": "aftermarket",
            "notes": "MOSFET style — runs cooler than OEM shunt type",
            "cross_references": ["SH847AA OEM"],
        },
    ],
    "tools": [
        {
            "tool_name": "Flywheel puller",
            "specification": "27mm x 1.0 LH thread",
            "price_range": "$25-40",
            "essential": True,
            "alternative": None,
        },
        {
            "tool_name": "Multimeter",
            "specification": "Digital, AC/DC voltage + resistance",
            "price_range": "$20-50",
            "essential": True,
            "alternative": None,
        },
        {
            "tool_name": "Dielectric grease",
            "specification": "Small tube",
            "price_range": "$5-10",
            "essential": False,
            "alternative": "Skip if connectors are clean and dry",
        },
    ],
})


class TestPartsRecommender:
    def test_recommend_returns_parts_and_tools(self):
        client = _make_mock_client(SAMPLE_RESPONSE)
        recommender = PartsRecommender(client)
        parts, tools, usage = recommender.recommend(
            diagnosis="Stator failure — no AC output at connector",
            make="Honda",
            model="CBR600RR",
            year=2005,
        )
        assert len(parts) == 2
        assert len(tools) == 3
        assert isinstance(usage, TokenUsage)

    def test_parts_are_part_recommendation_instances(self):
        client = _make_mock_client(SAMPLE_RESPONSE)
        recommender = PartsRecommender(client)
        parts, _, _ = recommender.recommend("Stator failure", "Honda", "CBR600RR", 2005)
        for p in parts:
            assert isinstance(p, PartRecommendation)

    def test_tools_are_tool_recommendation_instances(self):
        client = _make_mock_client(SAMPLE_RESPONSE)
        recommender = PartsRecommender(client)
        _, tools, _ = recommender.recommend("Stator failure", "Honda", "CBR600RR", 2005)
        for t in tools:
            assert isinstance(t, ToolRecommendation)

    def test_recommend_passes_correct_prompt(self):
        client = _make_mock_client(SAMPLE_RESPONSE)
        recommender = PartsRecommender(client)
        recommender.recommend("Stator failure", "Honda", "CBR600RR", 2005)
        call_args = client.ask.call_args
        prompt_text = call_args.kwargs.get("prompt") or call_args[0][0]
        assert "Honda" in prompt_text
        assert "CBR600RR" in prompt_text
        assert "2005" in prompt_text
        assert "Stator failure" in prompt_text

    def test_recommend_uses_parts_prompt_as_system(self):
        client = _make_mock_client(SAMPLE_RESPONSE)
        recommender = PartsRecommender(client)
        recommender.recommend("Stator failure", "Honda", "CBR600RR", 2005)
        call_args = client.ask.call_args
        system_text = call_args.kwargs.get("system")
        assert system_text == PARTS_PROMPT

    def test_handles_bad_json_gracefully(self):
        client = _make_mock_client("This is not JSON at all")
        recommender = PartsRecommender(client)
        parts, tools, usage = recommender.recommend("Bad input", "Honda", "CBR600RR", 2005)
        assert parts == []
        assert tools == []
        assert isinstance(usage, TokenUsage)

    def test_handles_partial_json_gracefully(self):
        """JSON is valid but individual items may be malformed."""
        bad_response = json.dumps({
            "parts": [
                {"part_name": "Good part", "brand": "NGK", "price_range_low": 10.0,
                 "price_range_high": 15.0, "source": "aftermarket"},
                {"bad_field": "missing required fields"},
            ],
            "tools": [
                {"tool_name": "Good tool", "specification": "10mm", "price_range": "$5",
                 "essential": True},
                {"missing": "required fields"},
            ],
        })
        client = _make_mock_client(bad_response)
        recommender = PartsRecommender(client)
        parts, tools, usage = recommender.recommend("Test", "Honda", "CBR600RR", 2005)
        assert len(parts) == 1
        assert len(tools) == 1

    def test_handles_json_in_code_fence(self):
        fenced = f"```json\n{SAMPLE_RESPONSE}\n```"
        client = _make_mock_client(fenced)
        recommender = PartsRecommender(client)
        parts, tools, _ = recommender.recommend("Stator failure", "Honda", "CBR600RR", 2005)
        assert len(parts) == 2
        assert len(tools) == 3

    def test_handles_empty_parts_and_tools(self):
        empty = json.dumps({"parts": [], "tools": []})
        client = _make_mock_client(empty)
        recommender = PartsRecommender(client)
        parts, tools, _ = recommender.recommend("Unknown", "Honda", "CBR600RR", 2005)
        assert parts == []
        assert tools == []

    def test_cross_references_preserved(self):
        client = _make_mock_client(SAMPLE_RESPONSE)
        recommender = PartsRecommender(client)
        parts, _, _ = recommender.recommend("Stator failure", "Honda", "CBR600RR", 2005)
        stator = parts[0]
        assert len(stator.cross_references) == 2
        assert "ElectroSport ESG794" in stator.cross_references
