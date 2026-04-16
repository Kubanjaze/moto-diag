"""Phase 08 — known issues repository tests."""

import pytest
from motodiag.core.database import init_db
from motodiag.knowledge.issues_repo import (
    add_known_issue, get_known_issue, search_known_issues,
    find_issues_by_symptom, find_issues_by_dtc, count_known_issues,
)
from motodiag.knowledge.loader import load_known_issues_file


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


@pytest.fixture
def stator_issue(db_path):
    return add_known_issue(
        title="Stator failure",
        description="Stator windings break down from heat causing charging failure",
        make="Harley-Davidson",
        year_start=1999, year_end=2017,
        severity="high",
        symptoms=["battery not charging", "headlight dim or flickering"],
        dtc_codes=["P0562"],
        causes=["Stator winding insulation breakdown"],
        fix_procedure="Test stator AC output, replace if low.",
        parts_needed=["Stator assembly", "Stator gasket"],
        estimated_hours=3.5,
        db_path=db_path,
    )


class TestAddAndGet:
    def test_returns_id(self, stator_issue):
        assert stator_issue > 0

    def test_get_full(self, db_path, stator_issue):
        issue = get_known_issue(stator_issue, db_path)
        assert issue["title"] == "Stator failure"
        assert issue["make"] == "Harley-Davidson"
        assert issue["year_start"] == 1999
        assert issue["estimated_hours"] == 3.5
        assert "P0562" in issue["dtc_codes"]
        assert len(issue["symptoms"]) == 2

    def test_get_not_found(self, db_path):
        assert get_known_issue(999, db_path) is None


class TestSearch:
    def test_by_make(self, db_path, stator_issue):
        results = search_known_issues(make="Harley", db_path=db_path)
        assert len(results) == 1

    def test_by_query(self, db_path, stator_issue):
        results = search_known_issues(query="stator", db_path=db_path)
        assert len(results) == 1

    def test_by_year(self, db_path, stator_issue):
        results = search_known_issues(year=2010, db_path=db_path)
        assert len(results) == 1
        results = search_known_issues(year=1990, db_path=db_path)
        assert len(results) == 0

    def test_by_severity(self, db_path, stator_issue):
        results = search_known_issues(severity="high", db_path=db_path)
        assert len(results) == 1
        results = search_known_issues(severity="low", db_path=db_path)
        assert len(results) == 0

    def test_empty(self, db_path):
        assert search_known_issues(query="nonexistent", db_path=db_path) == []


class TestFindBy:
    def test_find_by_symptom(self, db_path, stator_issue):
        results = find_issues_by_symptom("battery not charging", db_path)
        assert len(results) == 1
        assert results[0]["title"] == "Stator failure"

    def test_find_by_dtc(self, db_path, stator_issue):
        results = find_issues_by_dtc("P0562", db_path)
        assert len(results) == 1

    def test_find_by_dtc_no_match(self, db_path, stator_issue):
        results = find_issues_by_dtc("P9999", db_path)
        assert len(results) == 0


class TestCount:
    def test_count_all(self, db_path, stator_issue):
        assert count_known_issues(db_path=db_path) == 1

    def test_count_by_make(self, db_path, stator_issue):
        assert count_known_issues(make="Harley", db_path=db_path) == 1
        assert count_known_issues(make="Honda", db_path=db_path) == 0


class TestLoader:
    def test_load_harley_issues(self, db_path):
        from motodiag.core.config import DATA_DIR
        f = DATA_DIR / "knowledge" / "known_issues_harley.json"
        if f.exists():
            count = load_known_issues_file(f, db_path)
            assert count == 10
            assert count_known_issues(db_path=db_path) == 10

    def test_stator_searchable_after_load(self, db_path):
        from motodiag.core.config import DATA_DIR
        f = DATA_DIR / "knowledge" / "known_issues_harley.json"
        if f.exists():
            load_known_issues_file(f, db_path)
            results = find_issues_by_dtc("P0562", db_path)
            assert len(results) >= 1

    def test_file_not_found(self, db_path):
        with pytest.raises(FileNotFoundError):
            load_known_issues_file("/nonexistent.json", db_path)
