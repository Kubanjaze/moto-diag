"""Tests for Phase 88 — Diagnostic History + Learning.

30 tests covering DiagnosticRecord model, DiagnosticHistory class (add_record,
get_record, get_records with filters, get_recent, get_statistics, find_similar,
clear, remove_record, export/import), and HistoryStatistics model.
All pure logic — no API calls, no database, no filesystem.
"""

import pytest
from datetime import datetime, timezone, timedelta

from motodiag.engine.history import (
    DiagnosticRecord,
    DiagnosticHistory,
    HistoryStatistics,
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
    resolution: str | None = "Replaced stator and regulator-rectifier",
    cost: float | None = 450.0,
    duration_minutes: int | None = 120,
    timestamp: datetime | None = None,
    system_category: str | None = "electrical",
) -> DiagnosticRecord:
    """Helper to build a DiagnosticRecord with sensible defaults."""
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
        duration_minutes=duration_minutes,
        system_category=system_category,
    )


@pytest.fixture
def empty_history() -> DiagnosticHistory:
    return DiagnosticHistory()


@pytest.fixture
def populated_history() -> DiagnosticHistory:
    """History with 5 diverse records."""
    h = DiagnosticHistory()
    now = datetime.now(timezone.utc)

    h.add_record(_make_record(
        record_id="REC-001", make="Harley-Davidson", model="Sportster 1200",
        year=2005, symptoms=["battery not charging", "dim lights"],
        diagnosis="Stator failure", confidence=0.85, cost=450.0,
        duration_minutes=120, timestamp=now - timedelta(days=10),
        system_category="electrical",
    ))
    h.add_record(_make_record(
        record_id="REC-002", make="Honda", model="CBR600RR",
        year=2008, symptoms=["overheating", "loss of power", "coolant smell"],
        diagnosis="Head gasket failure", confidence=0.90, cost=1200.0,
        duration_minutes=480, timestamp=now - timedelta(days=5),
        system_category="cooling",
    ))
    h.add_record(_make_record(
        record_id="REC-003", make="Harley-Davidson", model="Road King",
        year=2012, symptoms=["rough idle", "backfires"],
        diagnosis="Intake vacuum leak", confidence=0.75, cost=150.0,
        duration_minutes=60, timestamp=now - timedelta(days=3),
        system_category="fuel", resolution=None,
    ))
    h.add_record(_make_record(
        record_id="REC-004", make="Yamaha", model="YZF-R1",
        year=2015, symptoms=["noise", "vibration at speed", "chain noise"],
        diagnosis="Worn chain and sprockets", confidence=0.92, cost=320.0,
        duration_minutes=90, timestamp=now - timedelta(days=1),
        system_category="drivetrain",
    ))
    h.add_record(_make_record(
        record_id="REC-005", make="Harley-Davidson", model="Sportster 883",
        year=2003, symptoms=["battery not charging", "check engine light on"],
        diagnosis="Stator failure", confidence=0.88, cost=420.0,
        duration_minutes=110, timestamp=now,
        system_category="electrical",
    ))
    return h


# ---------------------------------------------------------------------------
# DiagnosticRecord model tests
# ---------------------------------------------------------------------------

class TestDiagnosticRecord:
    """Tests for the DiagnosticRecord Pydantic model."""

    def test_create_full_record(self):
        r = _make_record()
        assert r.record_id == "REC-001"
        assert r.make == "Harley-Davidson"
        assert r.model == "Sportster 1200"
        assert r.year == 2005
        assert r.confidence == 0.85

    def test_default_timestamp_is_utc(self):
        r = _make_record()
        assert r.timestamp.tzinfo is not None

    def test_symptoms_list(self):
        r = _make_record(symptoms=["overheating", "loss of power", "coolant smell"])
        assert len(r.symptoms) == 3
        assert "overheating" in r.symptoms

    def test_optional_fields_none(self):
        r = _make_record(resolution=None, cost=None, duration_minutes=None)
        assert r.resolution is None
        assert r.cost is None
        assert r.duration_minutes is None

    def test_confidence_bounds_valid(self):
        r = _make_record(confidence=0.0)
        assert r.confidence == 0.0
        r2 = _make_record(confidence=1.0)
        assert r2.confidence == 1.0

    def test_confidence_out_of_bounds_raises(self):
        with pytest.raises(Exception):
            _make_record(confidence=1.5)

    def test_year_bounds(self):
        r = _make_record(year=1950)
        assert r.year == 1950

    def test_parts_used_default_empty(self):
        r = _make_record()
        assert r.parts_used == []

    def test_system_category_stored(self):
        r = _make_record(system_category="cooling")
        assert r.system_category == "cooling"


# ---------------------------------------------------------------------------
# DiagnosticHistory — add / get / count
# ---------------------------------------------------------------------------

class TestHistoryBasicOperations:
    """Tests for add_record, get_record, count, clear, remove."""

    def test_empty_history_count_zero(self, empty_history):
        assert empty_history.count == 0

    def test_add_record_increments_count(self, empty_history):
        empty_history.add_record(_make_record())
        assert empty_history.count == 1

    def test_get_record_by_id(self, populated_history):
        r = populated_history.get_record("REC-002")
        assert r is not None
        assert r.make == "Honda"

    def test_get_record_missing_returns_none(self, populated_history):
        assert populated_history.get_record("NONEXISTENT") is None

    def test_duplicate_id_raises(self, empty_history):
        empty_history.add_record(_make_record(record_id="DUP-001"))
        with pytest.raises(ValueError, match="already exists"):
            empty_history.add_record(_make_record(record_id="DUP-001"))

    def test_clear_removes_all(self, populated_history):
        assert populated_history.count == 5
        populated_history.clear()
        assert populated_history.count == 0

    def test_remove_record_success(self, populated_history):
        assert populated_history.remove_record("REC-003") is True
        assert populated_history.count == 4
        assert populated_history.get_record("REC-003") is None

    def test_remove_record_not_found(self, populated_history):
        assert populated_history.remove_record("NONEXISTENT") is False
        assert populated_history.count == 5


# ---------------------------------------------------------------------------
# DiagnosticHistory — filtered retrieval
# ---------------------------------------------------------------------------

class TestHistoryFiltering:
    """Tests for get_records with various filters."""

    def test_filter_by_make(self, populated_history):
        results = populated_history.get_records(make="Harley")
        assert len(results) == 3  # REC-001, REC-003, REC-005

    def test_filter_by_model(self, populated_history):
        results = populated_history.get_records(model="Sportster")
        assert len(results) == 2  # REC-001, REC-005

    def test_filter_by_year_range(self, populated_history):
        results = populated_history.get_records(year_min=2010, year_max=2020)
        assert len(results) == 2  # REC-003 (2012), REC-004 (2015)

    def test_filter_by_symptom_keywords(self, populated_history):
        results = populated_history.get_records(symptom_keywords=["overheating"])
        assert len(results) == 1
        assert results[0].record_id == "REC-002"

    def test_filter_by_diagnosis_keywords(self, populated_history):
        results = populated_history.get_records(diagnosis_keywords=["stator"])
        assert len(results) == 2  # REC-001, REC-005

    def test_filter_by_system_category(self, populated_history):
        results = populated_history.get_records(system_category="electrical")
        assert len(results) == 2

    def test_filter_by_min_confidence(self, populated_history):
        results = populated_history.get_records(min_confidence=0.90)
        assert len(results) == 2  # REC-002 (0.90), REC-004 (0.92)

    def test_filter_with_limit(self, populated_history):
        results = populated_history.get_records(limit=2)
        assert len(results) == 2

    def test_combined_filters(self, populated_history):
        results = populated_history.get_records(make="Harley", system_category="electrical")
        assert len(results) == 2  # REC-001, REC-005

    def test_no_match_returns_empty(self, populated_history):
        results = populated_history.get_records(make="Ducati")
        assert results == []

    def test_results_ordered_newest_first(self, populated_history):
        results = populated_history.get_records(make="Harley")
        # REC-005 is newest, then REC-003, then REC-001
        assert results[0].record_id == "REC-005"
        assert results[-1].record_id == "REC-001"


# ---------------------------------------------------------------------------
# DiagnosticHistory — get_recent
# ---------------------------------------------------------------------------

class TestHistoryRecent:
    """Tests for get_recent."""

    def test_get_recent_default(self, populated_history):
        recent = populated_history.get_recent()
        assert len(recent) == 5  # all 5, since n=10 default > 5 records

    def test_get_recent_limited(self, populated_history):
        recent = populated_history.get_recent(n=2)
        assert len(recent) == 2
        assert recent[0].record_id == "REC-005"  # newest

    def test_get_recent_empty_history(self, empty_history):
        assert empty_history.get_recent() == []


# ---------------------------------------------------------------------------
# DiagnosticHistory — statistics
# ---------------------------------------------------------------------------

class TestHistoryStatistics:
    """Tests for get_statistics."""

    def test_statistics_empty_history(self, empty_history):
        stats = empty_history.get_statistics()
        assert stats.total_records == 0
        assert stats.avg_confidence == 0.0

    def test_statistics_total_records(self, populated_history):
        stats = populated_history.get_statistics()
        assert stats.total_records == 5

    def test_statistics_avg_confidence(self, populated_history):
        stats = populated_history.get_statistics()
        expected = (0.85 + 0.90 + 0.75 + 0.92 + 0.88) / 5
        assert abs(stats.avg_confidence - expected) < 0.01

    def test_statistics_avg_cost(self, populated_history):
        stats = populated_history.get_statistics()
        expected = (450 + 1200 + 150 + 320 + 420) / 5
        assert stats.avg_cost is not None
        assert abs(stats.avg_cost - expected) < 1.0

    def test_statistics_most_common_diagnoses(self, populated_history):
        stats = populated_history.get_statistics()
        # "stator failure" appears twice
        top_diag = stats.most_common_diagnoses[0]
        assert top_diag[0] == "stator failure"
        assert top_diag[1] == 2

    def test_statistics_resolution_rate(self, populated_history):
        stats = populated_history.get_statistics()
        # 4 out of 5 have resolution (REC-003 has None)
        assert stats.records_with_resolution == 4
        assert abs(stats.resolution_rate - 0.8) < 0.01


# ---------------------------------------------------------------------------
# DiagnosticHistory — find_similar
# ---------------------------------------------------------------------------

class TestHistoryFindSimilar:
    """Tests for find_similar (RAG-style case lookup)."""

    def test_find_similar_exact_vehicle_match(self, populated_history):
        results = populated_history.find_similar(
            make="Harley-Davidson", model="Sportster 1200",
            year=2005, symptoms=["battery not charging"],
        )
        # REC-001 should be highest — exact make+model+year + symptom match
        assert len(results) > 0
        assert results[0].record_id == "REC-001"

    def test_find_similar_symptom_overlap(self, populated_history):
        results = populated_history.find_similar(
            make="Suzuki", model="GSX-R600",
            year=2010, symptoms=["overheating", "loss of power"],
        )
        # REC-002 has those symptoms
        assert any(r.record_id == "REC-002" for r in results)

    def test_find_similar_empty_history(self, empty_history):
        results = empty_history.find_similar(
            make="Honda", model="CBR600RR", year=2008, symptoms=["overheating"],
        )
        assert results == []

    def test_find_similar_top_n(self, populated_history):
        results = populated_history.find_similar(
            make="Harley-Davidson", model="Sportster 1200",
            year=2005, symptoms=["battery not charging", "dim lights"],
            top_n=2,
        )
        assert len(results) <= 2


# ---------------------------------------------------------------------------
# DiagnosticHistory — export / import
# ---------------------------------------------------------------------------

class TestHistoryExportImport:
    """Tests for export_records and import_records."""

    def test_export_returns_list_of_dicts(self, populated_history):
        exported = populated_history.export_records()
        assert len(exported) == 5
        assert isinstance(exported[0], dict)
        assert "record_id" in exported[0]

    def test_import_into_empty_history(self, populated_history, empty_history):
        exported = populated_history.export_records()
        imported_count = empty_history.import_records(exported)
        assert imported_count == 5
        assert empty_history.count == 5

    def test_import_skips_duplicates(self, populated_history):
        exported = populated_history.export_records()
        # Importing same records again should skip all
        imported_count = populated_history.import_records(exported)
        assert imported_count == 0
        assert populated_history.count == 5

    def test_import_skips_invalid_records(self, empty_history):
        bad_data = [{"invalid": "data"}, {"also": "bad"}]
        imported_count = empty_history.import_records(bad_data)
        assert imported_count == 0
