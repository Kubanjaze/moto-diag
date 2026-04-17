"""Tests for Phase 90 — Multi-Symptom Correlation.

32 tests covering CorrelationRule model, CorrelationMatch model,
CORRELATION_RULES coverage, SymptomCorrelator class (correlate with full/partial
matches, get_rules_by_system, get_rules_by_severity, get_rule_by_id),
edge cases (empty input, no matches, case insensitivity, min_matched, min_quality).
All pure logic — no API calls.
"""

import pytest

from motodiag.engine.correlation import (
    CorrelationRule,
    CorrelationMatch,
    SymptomCorrelator,
    CORRELATION_RULES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def correlator() -> SymptomCorrelator:
    return SymptomCorrelator()


# ---------------------------------------------------------------------------
# CorrelationRule model tests
# ---------------------------------------------------------------------------

class TestCorrelationRule:
    """Tests for the CorrelationRule Pydantic model."""

    def test_create_rule(self):
        rule = CorrelationRule(
            rule_id="TEST-001",
            symptom_set={"overheating", "loss of power"},
            root_cause="Test cause",
            confidence=0.85,
            explanation="Test explanation",
            system_category="cooling",
        )
        assert rule.rule_id == "TEST-001"
        assert len(rule.symptom_set) == 2
        assert rule.confidence == 0.85

    def test_rule_default_severity(self):
        rule = CorrelationRule(
            rule_id="TEST-002",
            symptom_set={"noise"},
            root_cause="Test",
            confidence=0.5,
            explanation="Test",
            system_category="mechanical",
        )
        assert rule.severity == "medium"

    def test_rule_common_vehicles_default_empty(self):
        rule = CorrelationRule(
            rule_id="TEST-003",
            symptom_set={"noise"},
            root_cause="Test",
            confidence=0.5,
            explanation="Test",
            system_category="mechanical",
        )
        assert rule.common_vehicles == []


# ---------------------------------------------------------------------------
# CorrelationMatch model tests
# ---------------------------------------------------------------------------

class TestCorrelationMatch:
    """Tests for the CorrelationMatch model."""

    def test_match_defaults(self):
        rule = CorrelationRule(
            rule_id="T-001", symptom_set={"a", "b"}, root_cause="X",
            confidence=0.8, explanation="Y", system_category="fuel",
        )
        match = CorrelationMatch(rule=rule)
        assert match.match_quality == 0.0
        assert match.adjusted_confidence == 0.0
        assert match.is_full_match is False

    def test_full_match_flag(self):
        rule = CorrelationRule(
            rule_id="T-002", symptom_set={"a"}, root_cause="X",
            confidence=0.9, explanation="Y", system_category="fuel",
        )
        match = CorrelationMatch(
            rule=rule,
            matched_symptoms={"a"},
            match_quality=1.0,
            adjusted_confidence=0.9,
            is_full_match=True,
        )
        assert match.is_full_match is True


# ---------------------------------------------------------------------------
# CORRELATION_RULES — coverage and structure tests
# ---------------------------------------------------------------------------

class TestCorrelationRulesCoverage:
    """Tests for the predefined CORRELATION_RULES list."""

    def test_minimum_rule_count(self):
        assert len(CORRELATION_RULES) >= 15

    def test_all_rules_have_required_fields(self):
        for rule in CORRELATION_RULES:
            assert rule.rule_id, f"Rule missing ID"
            assert len(rule.symptom_set) >= 2, f"{rule.rule_id} has fewer than 2 symptoms"
            assert rule.root_cause, f"{rule.rule_id} missing root_cause"
            assert 0.0 <= rule.confidence <= 1.0, f"{rule.rule_id} confidence out of range"
            assert rule.explanation, f"{rule.rule_id} missing explanation"
            assert rule.system_category, f"{rule.rule_id} missing system_category"

    def test_unique_rule_ids(self):
        ids = [r.rule_id for r in CORRELATION_RULES]
        assert len(ids) == len(set(ids)), "Duplicate rule IDs found"

    def test_covers_electrical_system(self):
        electrical = [r for r in CORRELATION_RULES if r.system_category == "electrical"]
        assert len(electrical) >= 2

    def test_covers_fuel_system(self):
        fuel = [r for r in CORRELATION_RULES if r.system_category == "fuel"]
        assert len(fuel) >= 2

    def test_covers_mechanical_system(self):
        mech = [r for r in CORRELATION_RULES if r.system_category == "mechanical"]
        assert len(mech) >= 2

    def test_covers_cooling_system(self):
        cooling = [r for r in CORRELATION_RULES if r.system_category == "cooling"]
        assert len(cooling) >= 1

    def test_covers_drivetrain_system(self):
        dt = [r for r in CORRELATION_RULES if r.system_category == "drivetrain"]
        assert len(dt) >= 1

    def test_covers_braking_system(self):
        braking = [r for r in CORRELATION_RULES if r.system_category == "braking"]
        assert len(braking) >= 1

    def test_has_critical_severity_rules(self):
        critical = [r for r in CORRELATION_RULES if r.severity == "critical"]
        assert len(critical) >= 2

    def test_head_gasket_rule_present(self):
        hg = [r for r in CORRELATION_RULES if "head gasket" in r.root_cause.lower()]
        assert len(hg) >= 1
        rule = hg[0]
        assert "overheating" in rule.symptom_set
        assert "loss of power" in rule.symptom_set
        assert "coolant smell" in rule.symptom_set

    def test_stator_rule_present(self):
        stator = [r for r in CORRELATION_RULES if "stator" in r.root_cause.lower()]
        assert len(stator) >= 1

    def test_vacuum_leak_rule_present(self):
        vacuum = [r for r in CORRELATION_RULES if "vacuum leak" in r.root_cause.lower()]
        assert len(vacuum) >= 1

    def test_chain_sprocket_rule_present(self):
        chain = [r for r in CORRELATION_RULES if "chain" in r.root_cause.lower()]
        assert len(chain) >= 1


# ---------------------------------------------------------------------------
# SymptomCorrelator — correlate (full match)
# ---------------------------------------------------------------------------

class TestCorrelatorFullMatch:
    """Tests for full symptom matches."""

    def test_head_gasket_full_match(self, correlator):
        matches = correlator.correlate(["overheating", "loss of power", "coolant smell"])
        assert len(matches) > 0
        top = matches[0]
        assert "head gasket" in top.rule.root_cause.lower()
        assert top.is_full_match is True
        assert top.match_quality == 1.0

    def test_stator_full_match(self, correlator):
        matches = correlator.correlate(["battery not charging", "dim lights", "check engine light on"])
        assert len(matches) > 0
        assert any("stator" in m.rule.root_cause.lower() for m in matches)

    def test_chain_sprocket_full_match(self, correlator):
        matches = correlator.correlate(["vibration at speed", "noise", "chain noise"])
        assert len(matches) > 0
        assert any("chain" in m.rule.root_cause.lower() for m in matches)

    def test_full_match_confidence_equals_base(self, correlator):
        matches = correlator.correlate(["overheating", "loss of power", "coolant smell"])
        hg = [m for m in matches if "head gasket" in m.rule.root_cause.lower()][0]
        assert hg.adjusted_confidence == hg.rule.confidence


# ---------------------------------------------------------------------------
# SymptomCorrelator — correlate (partial match)
# ---------------------------------------------------------------------------

class TestCorrelatorPartialMatch:
    """Tests for partial symptom matches (>= 2 of 3+ symptoms)."""

    def test_partial_match_two_of_three(self, correlator):
        # Only 2 of 3 head gasket symptoms
        matches = correlator.correlate(["overheating", "loss of power"])
        hg = [m for m in matches if "head gasket" in m.rule.root_cause.lower()]
        assert len(hg) > 0
        assert hg[0].is_full_match is False
        assert hg[0].match_quality == pytest.approx(2 / 3, abs=0.01)

    def test_partial_match_reduced_confidence(self, correlator):
        matches = correlator.correlate(["overheating", "loss of power"])
        hg = [m for m in matches if "head gasket" in m.rule.root_cause.lower()]
        assert len(hg) > 0
        assert hg[0].adjusted_confidence < hg[0].rule.confidence

    def test_partial_match_shows_unmatched(self, correlator):
        matches = correlator.correlate(["overheating", "loss of power"])
        hg = [m for m in matches if "head gasket" in m.rule.root_cause.lower()]
        assert len(hg) > 0
        assert "coolant smell" in hg[0].unmatched_rule_symptoms


# ---------------------------------------------------------------------------
# SymptomCorrelator — edge cases
# ---------------------------------------------------------------------------

class TestCorrelatorEdgeCases:
    """Tests for edge cases and parameter variations."""

    def test_empty_symptoms_returns_empty(self, correlator):
        assert correlator.correlate([]) == []

    def test_no_matching_symptoms(self, correlator):
        matches = correlator.correlate(["purple smoke", "teleportation failure"])
        assert matches == []

    def test_case_insensitive_matching(self, correlator):
        matches_lower = correlator.correlate(["overheating", "loss of power", "coolant smell"])
        matches_upper = correlator.correlate(["Overheating", "Loss of Power", "Coolant Smell"])
        assert len(matches_lower) == len(matches_upper)

    def test_min_matched_parameter(self, correlator):
        # With min_matched=3, partial 2-of-3 matches should be excluded
        matches = correlator.correlate(
            ["overheating", "loss of power"],
            min_matched=3,
        )
        hg = [m for m in matches if "head gasket" in m.rule.root_cause.lower()]
        assert len(hg) == 0

    def test_min_quality_filter(self, correlator):
        matches = correlator.correlate(
            ["overheating", "loss of power"],
            min_quality=0.9,
        )
        # No 2-of-3 match should have quality >= 0.9
        for m in matches:
            assert m.match_quality >= 0.9

    def test_results_sorted_by_adjusted_confidence(self, correlator):
        # Broad symptoms that match multiple rules
        matches = correlator.correlate(
            ["overheating", "loss of power", "noise", "rough idle", "backfires"],
        )
        for i in range(len(matches) - 1):
            assert matches[i].adjusted_confidence >= matches[i + 1].adjusted_confidence

    def test_rule_count(self, correlator):
        assert correlator.rule_count >= 15


# ---------------------------------------------------------------------------
# SymptomCorrelator — get_rules_by_* methods
# ---------------------------------------------------------------------------

class TestCorrelatorRuleLookup:
    """Tests for rule retrieval methods."""

    def test_get_rules_by_system(self, correlator):
        electrical = correlator.get_rules_by_system("electrical")
        assert all(r.system_category == "electrical" for r in electrical)
        assert len(electrical) >= 2

    def test_get_rules_by_severity_critical(self, correlator):
        critical = correlator.get_rules_by_severity("critical")
        assert all(r.severity == "critical" for r in critical)

    def test_get_rules_by_severity_medium_includes_higher(self, correlator):
        medium_plus = correlator.get_rules_by_severity("medium")
        # Should include medium, high, and critical
        severities = {r.severity for r in medium_plus}
        assert "critical" in severities or "high" in severities

    def test_get_rule_by_id_found(self, correlator):
        rule = correlator.get_rule_by_id("CORR-001")
        assert rule is not None
        assert "head gasket" in rule.root_cause.lower()

    def test_get_rule_by_id_not_found(self, correlator):
        assert correlator.get_rule_by_id("NONEXISTENT") is None
