"""Phase 73 — Cross-platform starting system diagnostics knowledge base tests."""

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
    f = DATA_DIR / "knowledge" / "known_issues_cross_platform_starting.json"
    if f.exists():
        load_known_issues_file(f, path)
    return path


class TestCrossPlatformStartingData:
    def test_loads(self, db_path):
        assert count_known_issues(db_path=db_path) == 10

    def test_multi_make(self, db_path):
        honda = search_known_issues(make="Honda", db_path=db_path)
        suzuki = search_known_issues(make="Suzuki", db_path=db_path)
        kawasaki = search_known_issues(make="Kawasaki", db_path=db_path)
        assert len(honda) >= 2
        assert len(suzuki) >= 2
        assert len(kawasaki) >= 2

    def test_high_severity(self, db_path):
        results = search_known_issues(severity="high", db_path=db_path)
        assert len(results) >= 3

    def test_wont_start(self, db_path):
        results = find_issues_by_symptom("won't start", db_path)
        assert len(results) >= 5

    def test_noise(self, db_path):
        click = find_issues_by_symptom("clicking noise", db_path)
        grind = find_issues_by_symptom("grinding noise", db_path)
        whir = find_issues_by_symptom("whirring noise", db_path)
        # Deduplicate by title in case any overlap
        titles = set()
        for r in click + grind + whir:
            titles.add(r.get("title", ""))
        assert len(titles) >= 2

    def test_forum_tips(self, db_path):
        results = search_known_issues(query="starter relay", db_path=db_path)
        assert len(results) >= 1
        assert "Forum tip" in results[0].get("fix_procedure", "")
