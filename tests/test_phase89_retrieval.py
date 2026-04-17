"""Tests for Phase 89 — Similar Case Retrieval.

30 tests covering SimilarityScore model, CaseRetriever static methods
(compute_symptom_overlap, compute_vehicle_match, compute_year_proximity),
CaseRetriever class (find_similar_cases, build_case_context), tokenization,
custom weights, and edge cases. All pure logic — no API calls.
"""

import pytest
from datetime import datetime, timezone, timedelta

from motodiag.engine.history import DiagnosticRecord, DiagnosticHistory
from motodiag.engine.retrieval import (
    SimilarityScore,
    CaseRetriever,
    DEFAULT_WEIGHTS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_record(
    record_id: str = "REC-001",
    make: str = "Harley-Davidson",
    model: str = "Sportster 1200",
    year: int = 2005,
    symptoms: list[str] | None = None,
    diagnosis: str = "Stator failure",
    confidence: float = 0.85,
    resolution: str | None = "Replaced stator",
    cost: float | None = 450.0,
    timestamp: datetime | None = None,
) -> DiagnosticRecord:
    return DiagnosticRecord(
        record_id=record_id,
        timestamp=timestamp or datetime.now(timezone.utc),
        make=make,
        model=model,
        year=year,
        symptoms=symptoms or ["battery not charging", "dim lights"],
        diagnosis=diagnosis,
        confidence=confidence,
        resolution=resolution,
        cost=cost,
    )


@pytest.fixture
def history_with_cases() -> DiagnosticHistory:
    h = DiagnosticHistory()
    now = datetime.now(timezone.utc)
    h.add_record(_make_record(
        record_id="REC-001", make="Harley-Davidson", model="Sportster 1200",
        year=2005, symptoms=["battery not charging", "dim lights"],
        diagnosis="Stator failure", confidence=0.85, cost=450.0,
        timestamp=now - timedelta(days=10),
    ))
    h.add_record(_make_record(
        record_id="REC-002", make="Honda", model="CBR600RR",
        year=2008, symptoms=["overheating", "loss of power", "coolant smell"],
        diagnosis="Head gasket failure", confidence=0.90, cost=1200.0,
        timestamp=now - timedelta(days=5),
    ))
    h.add_record(_make_record(
        record_id="REC-003", make="Harley-Davidson", model="Sportster 883",
        year=2003, symptoms=["battery not charging", "check engine light on"],
        diagnosis="Regulator-rectifier failure", confidence=0.88, cost=280.0,
        timestamp=now - timedelta(days=3),
    ))
    h.add_record(_make_record(
        record_id="REC-004", make="Yamaha", model="YZF-R1",
        year=2015, symptoms=["noise", "vibration at speed", "chain noise"],
        diagnosis="Worn chain and sprockets", confidence=0.92, cost=320.0,
        timestamp=now - timedelta(days=1),
    ))
    return h


@pytest.fixture
def retriever(history_with_cases) -> CaseRetriever:
    return CaseRetriever(history=history_with_cases)


# ---------------------------------------------------------------------------
# SimilarityScore model tests
# ---------------------------------------------------------------------------

class TestSimilarityScore:
    """Tests for the SimilarityScore Pydantic model."""

    def test_create_similarity_score(self):
        record = _make_record()
        score = SimilarityScore(
            record=record,
            symptom_overlap=0.5,
            vehicle_match=1.0,
            year_proximity=0.8,
            overall_score=0.7,
        )
        assert score.symptom_overlap == 0.5
        assert score.vehicle_match == 1.0
        assert score.overall_score == 0.7

    def test_default_scores_zero(self):
        record = _make_record()
        score = SimilarityScore(record=record)
        assert score.symptom_overlap == 0.0
        assert score.vehicle_match == 0.0
        assert score.year_proximity == 0.0
        assert score.overall_score == 0.0


# ---------------------------------------------------------------------------
# Static method: compute_symptom_overlap (Jaccard similarity)
# ---------------------------------------------------------------------------

class TestSymptomOverlap:
    """Tests for Jaccard similarity on symptom word sets."""

    def test_identical_symptoms(self):
        symptoms = ["battery not charging", "dim lights"]
        result = CaseRetriever.compute_symptom_overlap(symptoms, symptoms)
        assert result == 1.0

    def test_no_overlap(self):
        a = ["overheating", "coolant smell"]
        b = ["chain noise", "vibration"]
        result = CaseRetriever.compute_symptom_overlap(a, b)
        assert result == 0.0

    def test_partial_overlap(self):
        a = ["battery not charging", "dim lights"]
        b = ["battery not charging", "check engine light on"]
        result = CaseRetriever.compute_symptom_overlap(a, b)
        assert 0.0 < result < 1.0

    def test_both_empty(self):
        assert CaseRetriever.compute_symptom_overlap([], []) == 0.0

    def test_one_empty(self):
        assert CaseRetriever.compute_symptom_overlap(["overheating"], []) == 0.0

    def test_short_words_filtered(self):
        # "a" and "an" should be filtered out (< 3 chars)
        a = ["a dim light"]
        b = ["a dim bulb"]
        result = CaseRetriever.compute_symptom_overlap(a, b)
        # "dim" is in both; "light" and "bulb" are not
        assert result > 0.0


# ---------------------------------------------------------------------------
# Static method: compute_vehicle_match
# ---------------------------------------------------------------------------

class TestVehicleMatch:
    """Tests for vehicle matching logic."""

    def test_exact_match(self):
        assert CaseRetriever.compute_vehicle_match(
            "Harley-Davidson", "Sportster 1200",
            "Harley-Davidson", "Sportster 1200",
        ) == 1.0

    def test_same_make_different_model(self):
        assert CaseRetriever.compute_vehicle_match(
            "Harley-Davidson", "Sportster 1200",
            "Harley-Davidson", "Road King",
        ) == 0.5

    def test_different_make(self):
        assert CaseRetriever.compute_vehicle_match(
            "Harley-Davidson", "Sportster 1200",
            "Honda", "CBR600RR",
        ) == 0.0

    def test_case_insensitive(self):
        assert CaseRetriever.compute_vehicle_match(
            "harley-davidson", "sportster 1200",
            "HARLEY-DAVIDSON", "SPORTSTER 1200",
        ) == 1.0

    def test_whitespace_tolerance(self):
        assert CaseRetriever.compute_vehicle_match(
            " Harley-Davidson ", " Sportster 1200 ",
            "Harley-Davidson", "Sportster 1200",
        ) == 1.0


# ---------------------------------------------------------------------------
# Static method: compute_year_proximity
# ---------------------------------------------------------------------------

class TestYearProximity:
    """Tests for year proximity scoring."""

    def test_same_year(self):
        assert CaseRetriever.compute_year_proximity(2005, 2005) == 1.0

    def test_one_year_apart(self):
        result = CaseRetriever.compute_year_proximity(2005, 2006)
        assert result == 0.9  # 1.0 - 1/10

    def test_five_years_apart(self):
        result = CaseRetriever.compute_year_proximity(2005, 2010)
        assert result == 0.5

    def test_at_window_boundary(self):
        result = CaseRetriever.compute_year_proximity(2005, 2015, window=10)
        assert result == 0.0

    def test_beyond_window(self):
        result = CaseRetriever.compute_year_proximity(2005, 2020, window=10)
        assert result == 0.0

    def test_custom_window(self):
        result = CaseRetriever.compute_year_proximity(2005, 2010, window=20)
        assert result == 0.75  # 1.0 - 5/20


# ---------------------------------------------------------------------------
# CaseRetriever — compute_similarity
# ---------------------------------------------------------------------------

class TestComputeSimilarity:
    """Tests for the full similarity computation."""

    def test_exact_case_match(self, retriever):
        record = retriever.history.get_record("REC-001")
        sim = retriever.compute_similarity(
            "Harley-Davidson", "Sportster 1200", 2005,
            ["battery not charging", "dim lights"], record,
        )
        assert sim.vehicle_match == 1.0
        assert sim.year_proximity == 1.0
        assert sim.symptom_overlap == 1.0
        assert sim.overall_score > 0.9

    def test_no_match_case(self, retriever):
        record = retriever.history.get_record("REC-004")
        sim = retriever.compute_similarity(
            "Ducati", "Monster 821", 2020,
            ["oil leak"], record,
        )
        assert sim.vehicle_match == 0.0
        assert sim.symptom_overlap == 0.0


# ---------------------------------------------------------------------------
# CaseRetriever — find_similar_cases
# ---------------------------------------------------------------------------

class TestFindSimilarCases:
    """Tests for ranked similar case retrieval."""

    def test_find_similar_returns_ranked(self, retriever):
        results = retriever.find_similar_cases(
            make="Harley-Davidson", model="Sportster 1200",
            year=2005, symptoms=["battery not charging", "dim lights"],
        )
        assert len(results) > 0
        # First result should be the exact match
        assert results[0].record.record_id == "REC-001"
        # Scores should be descending
        for i in range(len(results) - 1):
            assert results[i].overall_score >= results[i + 1].overall_score

    def test_find_similar_top_n(self, retriever):
        results = retriever.find_similar_cases(
            make="Harley-Davidson", model="Sportster 1200",
            year=2005, symptoms=["battery not charging"],
            top_n=2,
        )
        assert len(results) <= 2

    def test_find_similar_min_score_filter(self, retriever):
        results = retriever.find_similar_cases(
            make="Ducati", model="Monster", year=2020,
            symptoms=["unique symptom xyz"], min_score=0.5,
        )
        # With a very different vehicle and unique symptoms, nothing should score > 0.5
        assert len(results) == 0

    def test_find_similar_empty_history(self):
        h = DiagnosticHistory()
        r = CaseRetriever(history=h)
        results = r.find_similar_cases("Honda", "CBR", 2010, ["overheating"])
        assert results == []


# ---------------------------------------------------------------------------
# CaseRetriever — build_case_context
# ---------------------------------------------------------------------------

class TestBuildCaseContext:
    """Tests for RAG context string formatting."""

    def test_context_contains_header(self, retriever):
        ctx = retriever.build_case_context(
            make="Harley-Davidson", model="Sportster 1200",
            year=2005, symptoms=["battery not charging"],
        )
        assert "SIMILAR PAST DIAGNOSTICS" in ctx

    def test_context_contains_case_details(self, retriever):
        ctx = retriever.build_case_context(
            make="Harley-Davidson", model="Sportster 1200",
            year=2005, symptoms=["battery not charging"],
        )
        assert "Stator failure" in ctx
        assert "Harley-Davidson" in ctx

    def test_context_empty_when_no_matches(self):
        h = DiagnosticHistory()
        r = CaseRetriever(history=h)
        ctx = r.build_case_context("Ducati", "Monster", 2020, ["oil leak"])
        assert ctx == ""

    def test_context_includes_cost(self, retriever):
        ctx = retriever.build_case_context(
            make="Harley-Davidson", model="Sportster 1200",
            year=2005, symptoms=["battery not charging"],
        )
        assert "$" in ctx

    def test_context_includes_resolution(self, retriever):
        ctx = retriever.build_case_context(
            make="Harley-Davidson", model="Sportster 1200",
            year=2005, symptoms=["battery not charging"],
        )
        assert "Resolution:" in ctx


# ---------------------------------------------------------------------------
# CaseRetriever — custom weights
# ---------------------------------------------------------------------------

class TestCustomWeights:
    """Tests for custom weight configuration."""

    def test_default_weights_sum(self):
        total = sum(DEFAULT_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_custom_weights_applied(self, history_with_cases):
        # Weight symptoms at 100%, ignore vehicle and year
        custom = {"symptom_overlap": 1.0, "vehicle_match": 0.0, "year_proximity": 0.0}
        r = CaseRetriever(history=history_with_cases, weights=custom)
        results = r.find_similar_cases(
            make="Ducati", model="Monster", year=2020,
            symptoms=["battery not charging", "dim lights"],
        )
        # REC-001 should score high on symptoms alone despite wrong vehicle
        assert len(results) > 0
        assert results[0].record.record_id == "REC-001"
