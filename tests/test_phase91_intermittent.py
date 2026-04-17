"""Tests for Phase 91 — Intermittent Fault Analysis.

32 tests covering EnvironmentalFactor model, IntermittentPattern model,
IntermittentMatch model, INTERMITTENT_PATTERNS coverage, IntermittentAnalyzer class
(analyze, extract_conditions, get_pattern_by_id, get_patterns_by_system, get_prompt),
INTERMITTENT_PROMPT content, and edge cases. All pure logic — no API calls.
"""

import pytest

from motodiag.engine.intermittent import (
    EnvironmentalFactor,
    IntermittentPattern,
    IntermittentMatch,
    IntermittentAnalyzer,
    INTERMITTENT_PATTERNS,
    INTERMITTENT_PROMPT,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def analyzer() -> IntermittentAnalyzer:
    return IntermittentAnalyzer()


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestEnvironmentalFactor:
    """Tests for the EnvironmentalFactor model."""

    def test_create_factor(self):
        f = EnvironmentalFactor(
            factor_type="temperature",
            description="Cold conditions reported",
            relevance=0.7,
        )
        assert f.factor_type == "temperature"
        assert f.relevance == 0.7

    def test_default_relevance(self):
        f = EnvironmentalFactor(
            factor_type="humidity",
            description="Wet conditions",
        )
        assert f.relevance == 0.5

    def test_relevance_bounds(self):
        f = EnvironmentalFactor(factor_type="load", description="test", relevance=0.0)
        assert f.relevance == 0.0
        f2 = EnvironmentalFactor(factor_type="load", description="test", relevance=1.0)
        assert f2.relevance == 1.0


class TestIntermittentPattern:
    """Tests for the IntermittentPattern model."""

    def test_create_pattern(self):
        p = IntermittentPattern(
            pattern_id="TEST-001",
            description="Test pattern",
            trigger_conditions=["condition 1"],
            likely_causes=["cause 1"],
            diagnostic_approach=["step 1"],
        )
        assert p.pattern_id == "TEST-001"
        assert p.system_category == "general"

    def test_keywords_default_empty(self):
        p = IntermittentPattern(
            pattern_id="TEST-002",
            description="Test",
            trigger_conditions=["x"],
            likely_causes=["y"],
            diagnostic_approach=["z"],
        )
        assert p.keywords == []


class TestIntermittentMatch:
    """Tests for the IntermittentMatch model."""

    def test_match_defaults(self):
        p = IntermittentPattern(
            pattern_id="T-001", description="X",
            trigger_conditions=["a"], likely_causes=["b"],
            diagnostic_approach=["c"],
        )
        m = IntermittentMatch(pattern=p)
        assert m.match_score == 0.0
        assert m.keyword_hits == []
        assert m.extracted_factors == []


# ---------------------------------------------------------------------------
# INTERMITTENT_PATTERNS — coverage and structure tests
# ---------------------------------------------------------------------------

class TestIntermittentPatternsCoverage:
    """Tests for the predefined INTERMITTENT_PATTERNS list."""

    def test_minimum_pattern_count(self):
        assert len(INTERMITTENT_PATTERNS) >= 10

    def test_all_patterns_have_required_fields(self):
        for p in INTERMITTENT_PATTERNS:
            assert p.pattern_id, f"Pattern missing ID"
            assert p.description, f"{p.pattern_id} missing description"
            assert len(p.trigger_conditions) >= 1, f"{p.pattern_id} no trigger conditions"
            assert len(p.likely_causes) >= 2, f"{p.pattern_id} needs >= 2 likely causes"
            assert len(p.diagnostic_approach) >= 2, f"{p.pattern_id} needs >= 2 diagnostic steps"
            assert len(p.keywords) >= 2, f"{p.pattern_id} needs >= 2 keywords"

    def test_unique_pattern_ids(self):
        ids = [p.pattern_id for p in INTERMITTENT_PATTERNS]
        assert len(ids) == len(set(ids)), "Duplicate pattern IDs found"

    def test_cold_start_pattern_present(self):
        cold = [p for p in INTERMITTENT_PATTERNS if "cold" in p.description.lower()]
        assert len(cold) >= 1
        assert any("cold" in kw for kw in cold[0].keywords)

    def test_hot_pattern_present(self):
        hot = [p for p in INTERMITTENT_PATTERNS if "hot" in p.description.lower()]
        assert len(hot) >= 1

    def test_rain_pattern_present(self):
        rain = [p for p in INTERMITTENT_PATTERNS if "rain" in p.description.lower()]
        assert len(rain) >= 1

    def test_load_pattern_present(self):
        load = [p for p in INTERMITTENT_PATTERNS if "load" in p.description.lower()]
        assert len(load) >= 1

    def test_high_rpm_pattern_present(self):
        rpm = [p for p in INTERMITTENT_PATTERNS if "rpm" in p.description.lower()]
        assert len(rpm) >= 1

    def test_random_pattern_present(self):
        rand = [p for p in INTERMITTENT_PATTERNS if "random" in p.description.lower()]
        assert len(rand) >= 1

    def test_has_electrical_patterns(self):
        elec = [p for p in INTERMITTENT_PATTERNS if p.system_category == "electrical"]
        assert len(elec) >= 2

    def test_has_fuel_patterns(self):
        fuel = [p for p in INTERMITTENT_PATTERNS if p.system_category == "fuel"]
        assert len(fuel) >= 2


# ---------------------------------------------------------------------------
# INTERMITTENT_PROMPT content tests
# ---------------------------------------------------------------------------

class TestIntermittentPrompt:
    """Tests for the specialized AI prompt content."""

    def test_prompt_not_empty(self):
        assert len(INTERMITTENT_PROMPT) > 100

    def test_prompt_mentions_intermittent(self):
        assert "intermittent" in INTERMITTENT_PROMPT.lower()

    def test_prompt_mentions_temperature(self):
        assert "temperature" in INTERMITTENT_PROMPT.lower()

    def test_prompt_mentions_vibration(self):
        assert "vibration" in INTERMITTENT_PROMPT.lower()

    def test_prompt_warns_about_stator(self):
        assert "stator" in INTERMITTENT_PROMPT.lower()


# ---------------------------------------------------------------------------
# IntermittentAnalyzer — extract_conditions
# ---------------------------------------------------------------------------

class TestExtractConditions:
    """Tests for environmental condition extraction from freeform text."""

    def test_extract_cold_condition(self, analyzer):
        factors = analyzer.extract_conditions("It only happens when the engine is cold")
        types = [f.factor_type for f in factors]
        assert "temperature" in types

    def test_extract_rain_condition(self, analyzer):
        factors = analyzer.extract_conditions("The bike stalls in the rain")
        types = [f.factor_type for f in factors]
        assert "humidity" in types

    def test_extract_load_condition(self, analyzer):
        factors = analyzer.extract_conditions("It hesitates under load on hills")
        types = [f.factor_type for f in factors]
        assert "load" in types

    def test_extract_multiple_conditions(self, analyzer):
        factors = analyzer.extract_conditions(
            "It happens in cold rain when accelerating uphill"
        )
        types = set(f.factor_type for f in factors)
        assert "temperature" in types
        assert "humidity" in types

    def test_extract_empty_text(self, analyzer):
        assert analyzer.extract_conditions("") == []

    def test_extract_no_conditions(self, analyzer):
        factors = analyzer.extract_conditions("The motorcycle is blue and shiny")
        # May or may not find anything — shouldn't crash
        assert isinstance(factors, list)

    def test_extract_idle_condition(self, analyzer):
        factors = analyzer.extract_conditions("It only dies at idle in traffic")
        types = [f.factor_type for f in factors]
        assert "rpm" in types

    def test_extract_fuel_level_condition(self, analyzer):
        factors = analyzer.extract_conditions("Stalls on low fuel after cornering")
        types = [f.factor_type for f in factors]
        assert "fuel_level" in types


# ---------------------------------------------------------------------------
# IntermittentAnalyzer — analyze
# ---------------------------------------------------------------------------

class TestAnalyze:
    """Tests for full analysis matching."""

    def test_cold_start_match(self, analyzer):
        matches = analyzer.analyze(
            symptom="hard starting",
            condition_description="only when the engine is cold, first start of the day in winter",
        )
        assert len(matches) > 0
        assert any("cold" in m.pattern.description.lower() for m in matches)

    def test_rain_match(self, analyzer):
        matches = analyzer.analyze(
            symptom="engine misfires",
            condition_description="only happens when riding in the rain or on wet roads",
        )
        assert len(matches) > 0
        assert any("rain" in m.pattern.description.lower() for m in matches)

    def test_random_fault_match(self, analyzer):
        matches = analyzer.analyze(
            symptom="engine cuts out",
            condition_description="completely random, sometimes happens, can't reproduce it",
        )
        assert len(matches) > 0
        assert any("random" in m.pattern.description.lower() for m in matches)

    def test_load_dependent_match(self, analyzer):
        matches = analyzer.analyze(
            symptom="loss of power",
            condition_description="only under load, full throttle acceleration or going uphill",
        )
        assert len(matches) > 0
        assert any("load" in m.pattern.description.lower() for m in matches)

    def test_no_match_returns_empty(self, analyzer):
        matches = analyzer.analyze(
            symptom="sparkly paint",
            condition_description="only when looking at it funny",
            min_score=0.5,
        )
        assert matches == []

    def test_top_n_limits_results(self, analyzer):
        matches = analyzer.analyze(
            symptom="stalls",
            condition_description="cold rain idle low fuel random sometimes intermittent",
            top_n=3,
        )
        assert len(matches) <= 3

    def test_results_sorted_by_score(self, analyzer):
        matches = analyzer.analyze(
            symptom="misfire",
            condition_description="cold start morning winter overnight choke",
        )
        for i in range(len(matches) - 1):
            assert matches[i].match_score >= matches[i + 1].match_score

    def test_keyword_hits_populated(self, analyzer):
        matches = analyzer.analyze(
            symptom="hard starting",
            condition_description="only in cold weather, winter mornings",
        )
        cold_match = [m for m in matches if "cold" in m.pattern.description.lower()]
        assert len(cold_match) > 0
        assert len(cold_match[0].keyword_hits) > 0


# ---------------------------------------------------------------------------
# IntermittentAnalyzer — lookup methods
# ---------------------------------------------------------------------------

class TestAnalyzerLookup:
    """Tests for pattern lookup methods."""

    def test_get_pattern_by_id(self, analyzer):
        p = analyzer.get_pattern_by_id("INT-001")
        assert p is not None
        assert "cold" in p.description.lower()

    def test_get_pattern_by_id_not_found(self, analyzer):
        assert analyzer.get_pattern_by_id("NONEXISTENT") is None

    def test_get_patterns_by_system(self, analyzer):
        electrical = analyzer.get_patterns_by_system("electrical")
        assert all(p.system_category == "electrical" for p in electrical)
        assert len(electrical) >= 2

    def test_pattern_count(self, analyzer):
        assert analyzer.pattern_count >= 10

    def test_get_prompt(self, analyzer):
        prompt = analyzer.get_prompt()
        assert "intermittent" in prompt.lower()
        assert len(prompt) > 100
