"""Phase 14 — Harley Twin Cam 88 knowledge base tests."""

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
    f = DATA_DIR / "knowledge" / "known_issues_harley_tc88.json"
    if f.exists():
        load_known_issues_file(f, path)
    return path


class TestTC88Data:
    def test_loads(self, db_path):
        assert count_known_issues(db_path=db_path) == 10

    def test_cam_tensioner_critical(self, db_path):
        results = search_known_issues(severity="critical", db_path=db_path)
        assert len(results) >= 1
        titles = [r["title"].lower() for r in results]
        assert any("cam" in t or "tensioner" in t for t in titles)

    def test_year_range(self, db_path):
        results = search_known_issues(year=2003, make="Harley", db_path=db_path)
        assert len(results) >= 5

    def test_compensator_searchable(self, db_path):
        results = search_known_issues(query="compensator", db_path=db_path)
        assert len(results) >= 1

    def test_find_by_symptom(self, db_path):
        results = find_issues_by_symptom("ticking or tapping", db_path)
        assert len(results) >= 2  # cam tensioner + cam bearing

    def test_find_by_dtc(self, db_path):
        results = find_issues_by_dtc("P0562", db_path)
        assert len(results) >= 1  # stator failure

    def test_forum_tips(self, db_path):
        results = search_known_issues(query="cam chain tensioner", db_path=db_path)
        assert len(results) >= 1
        fix = results[0].get("fix_procedure", "")
        assert "Forum tip" in fix or "forum" in fix.lower()
