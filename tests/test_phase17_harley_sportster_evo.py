"""Phase 17 — Harley Sportster Evo knowledge base tests."""

import pytest
from motodiag.core.database import init_db
from motodiag.knowledge.loader import load_known_issues_file
from motodiag.knowledge.issues_repo import (
    search_known_issues, find_issues_by_symptom, count_known_issues,
)
from motodiag.core.config import DATA_DIR


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    f = DATA_DIR / "knowledge" / "known_issues_harley_sportster_evo.json"
    if f.exists():
        load_known_issues_file(f, path)
    return path


class TestSportsterEvoData:
    def test_loads(self, db_path):
        assert count_known_issues(db_path=db_path) == 10

    def test_sportster_model_filter(self, db_path):
        results = search_known_issues(model="Sportster", db_path=db_path)
        assert len(results) >= 5

    def test_year_range(self, db_path):
        results = search_known_issues(year=1995, make="Harley", db_path=db_path)
        assert len(results) >= 5

    def test_shared_oil_system(self, db_path):
        results = search_known_issues(query="shared oil", db_path=db_path)
        assert len(results) >= 1

    def test_clutch_cable(self, db_path):
        results = find_issues_by_symptom("clutch slipping", db_path)
        assert len(results) >= 1

    def test_cold_start_issues(self, db_path):
        results = find_issues_by_symptom("hard to start when cold", db_path)
        assert len(results) >= 1

    def test_forum_tips(self, db_path):
        results = search_known_issues(query="starter motor", db_path=db_path)
        assert len(results) >= 1
        assert "Forum tip" in results[0].get("fix_procedure", "")
