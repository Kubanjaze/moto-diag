"""Phase 70 — Cross-platform carburetor troubleshooting knowledge base tests."""

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
    f = DATA_DIR / "knowledge" / "known_issues_cross_platform_carbs.json"
    if f.exists():
        load_known_issues_file(f, path)
    return path


class TestCrossPlatformCarbsData:
    def test_loads(self, db_path):
        assert count_known_issues(db_path=db_path) == 10

    def test_multi_make(self, db_path):
        """Cross-platform phases should reference multiple makes."""
        honda = search_known_issues(make="Honda", db_path=db_path)
        kawasaki = search_known_issues(make="Kawasaki", db_path=db_path)
        suzuki = search_known_issues(make="Suzuki", db_path=db_path)
        yamaha = search_known_issues(make="Yamaha", db_path=db_path)
        assert len(honda) >= 2
        assert len(kawasaki) >= 2
        assert len(suzuki) >= 2

    def test_critical_severity(self, db_path):
        results = search_known_issues(severity="critical", db_path=db_path)
        assert len(results) >= 1

    def test_rough_idle(self, db_path):
        results = find_issues_by_symptom("rough idle", db_path)
        assert len(results) >= 4

    def test_wont_start(self, db_path):
        results = find_issues_by_symptom("won't start", db_path)
        assert len(results) >= 2

    def test_forum_tips(self, db_path):
        results = search_known_issues(query="pilot jet", db_path=db_path)
        assert len(results) >= 1
        assert "Forum tip" in results[0].get("fix_procedure", "")
