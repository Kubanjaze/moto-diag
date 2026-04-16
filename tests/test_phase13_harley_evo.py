"""Phase 13 — Harley Evo Big Twin knowledge base tests."""

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
    f = DATA_DIR / "knowledge" / "known_issues_harley_evo_bigtwin.json"
    if f.exists():
        load_known_issues_file(f, path)
    return path


class TestEvoData:
    def test_loads(self, db_path):
        assert count_known_issues(db_path=db_path) == 10

    def test_year_range(self, db_path):
        results = search_known_issues(year=1995, make="Harley", db_path=db_path)
        assert len(results) >= 5  # most issues span 1984-1999

    def test_outside_year(self, db_path):
        results = search_known_issues(year=2020, make="Harley", db_path=db_path)
        # Should not match Evo issues (1984-1999)
        assert len(results) == 0

    def test_oil_leak_searchable(self, db_path):
        results = find_issues_by_symptom("oil leak", db_path)
        assert len(results) >= 3  # base gasket, rocker box, cam cover, pushrod tubes

    def test_forum_tips_present(self, db_path):
        results = search_known_issues(query="base gasket", db_path=db_path)
        assert len(results) >= 1
        fix = results[0].get("fix_procedure", "")
        assert "Forum tip" in fix or "forum tip" in fix.lower()

    def test_parts_included(self, db_path):
        results = search_known_issues(query="starter clutch", db_path=db_path)
        assert len(results) >= 1
        parts = results[0].get("parts_needed", [])
        assert len(parts) >= 1

    def test_critical_issues_flagged(self, db_path):
        results = search_known_issues(severity="critical", db_path=db_path)
        assert len(results) >= 1  # voltage regulator overheating
