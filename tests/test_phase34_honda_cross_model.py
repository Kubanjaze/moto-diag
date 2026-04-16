"""Phase 34 — Honda common cross-model issues knowledge base tests."""

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
    f = DATA_DIR / "knowledge" / "known_issues_honda_cross_model.json"
    if f.exists():
        load_known_issues_file(f, path)
    return path


class TestHondaCrossModelData:
    def test_loads(self, db_path):
        assert count_known_issues(db_path=db_path) == 10

    def test_cross_era(self, db_path):
        results = search_known_issues(year=2010, db_path=db_path)
        assert len(results) >= 8

    def test_critical_severity(self, db_path):
        results = search_known_issues(severity="critical", db_path=db_path)
        assert len(results) >= 1

    def test_noise_symptom(self, db_path):
        results = find_issues_by_symptom("noise", db_path)
        assert len(results) >= 1

    def test_handling_symptom(self, db_path):
        results = find_issues_by_symptom("handling instability", db_path)
        assert len(results) >= 1

    def test_forum_tips(self, db_path):
        results = search_known_issues(query="cam chain", db_path=db_path)
        assert len(results) >= 1
        assert "Forum tip" in results[0].get("fix_procedure", "")
