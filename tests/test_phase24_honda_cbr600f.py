"""Phase 24 — Honda CBR600 F2/F3/F4/F4i knowledge base tests."""

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
    f = DATA_DIR / "knowledge" / "known_issues_honda_cbr600f.json"
    if f.exists():
        load_known_issues_file(f, path)
    return path


class TestHondaCBR600FData:
    def test_loads(self, db_path):
        assert count_known_issues(db_path=db_path) == 10

    def test_year_range(self, db_path):
        results = search_known_issues(year=2003, make="Honda", db_path=db_path)
        assert len(results) >= 5

    def test_critical_severity(self, db_path):
        results = search_known_issues(severity="critical", db_path=db_path)
        assert len(results) >= 1

    def test_overheating_symptom(self, db_path):
        results = find_issues_by_symptom("overheating", db_path)
        assert len(results) >= 1

    def test_rough_idle(self, db_path):
        results = find_issues_by_symptom("rough idle", db_path)
        assert len(results) >= 2

    def test_forum_tips(self, db_path):
        results = search_known_issues(query="carburetor", db_path=db_path)
        assert len(results) >= 1
        assert "Forum tip" in results[0].get("fix_procedure", "")
