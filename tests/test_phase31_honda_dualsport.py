"""Phase 31 — Honda dual-sport XR650L, CRF250L/300L, Africa Twin knowledge base tests."""

import pytest
from motodiag.core.database import init_db
from motodiag.knowledge.loader import load_known_issues_file
from motodiag.knowledge.issues_repo import (
    search_known_issues, find_issues_by_symptom, find_issues_by_dtc, count_known_issues,
)
from motodiag.core.config import DATA_DIR


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    f = DATA_DIR / "knowledge" / "known_issues_honda_dualsport.json"
    if f.exists():
        load_known_issues_file(f, path)
    return path


class TestHondaDualSportData:
    def test_loads(self, db_path):
        assert count_known_issues(db_path=db_path) == 10

    def test_year_range(self, db_path):
        results = search_known_issues(year=2020, make="Honda", db_path=db_path)
        assert len(results) >= 5

    def test_high_severity(self, db_path):
        results = search_known_issues(severity="high", db_path=db_path)
        assert len(results) >= 2

    def test_overheating_symptom(self, db_path):
        results = find_issues_by_symptom("overheating", db_path)
        assert len(results) >= 1

    def test_loss_of_power(self, db_path):
        results = find_issues_by_symptom("loss of power", db_path)
        assert len(results) >= 2

    def test_forum_tips(self, db_path):
        results = search_known_issues(query="jetting", db_path=db_path)
        assert len(results) >= 1
        assert "Forum tip" in results[0].get("fix_procedure", "")
