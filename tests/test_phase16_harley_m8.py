"""Phase 16 — Harley Milwaukee-Eight knowledge base tests."""

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
    f = DATA_DIR / "knowledge" / "known_issues_harley_m8.json"
    if f.exists():
        load_known_issues_file(f, path)
    return path


class TestM8Data:
    def test_loads(self, db_path):
        assert count_known_issues(db_path=db_path) == 10

    def test_year_range(self, db_path):
        results = search_known_issues(year=2022, make="Harley", db_path=db_path)
        assert len(results) >= 5

    def test_touring_specific(self, db_path):
        results = search_known_issues(model="Touring", db_path=db_path)
        assert len(results) >= 3

    def test_compensator_limited_years(self, db_path):
        results = search_known_issues(query="compensator", year=2021, db_path=db_path)
        assert len(results) == 0  # compensator issue is 2017-2019 only

    def test_oil_pressure_sensor(self, db_path):
        results = search_known_issues(query="oil pressure sensor", db_path=db_path)
        assert len(results) >= 1

    def test_forum_tips(self, db_path):
        results = search_known_issues(query="exhaust header", db_path=db_path)
        assert len(results) >= 1
        assert "Forum tip" in results[0].get("fix_procedure", "")

    def test_vibration_symptom(self, db_path):
        results = find_issues_by_symptom("vibration at speed", db_path)
        assert len(results) >= 1
