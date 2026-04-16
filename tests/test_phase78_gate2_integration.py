"""Phase 78 — Gate 2 integration test: Vehicle knowledge base end-to-end.

Verifies the full mechanic workflow: query any target bike from the 5-make fleet
and get DTCs, symptoms, known issues, and fixes. This test loads ALL knowledge
base data files and verifies cross-store queries work across the entire dataset.
"""

import pytest
import os
from pathlib import Path
from motodiag.core.database import init_db
from motodiag.knowledge.loader import load_known_issues_file
from motodiag.knowledge.issues_repo import (
    search_known_issues, find_issues_by_symptom, find_issues_by_dtc, count_known_issues,
)
from motodiag.core.config import DATA_DIR


@pytest.fixture
def full_db(tmp_path):
    """Load ALL knowledge base JSON files into a single test database."""
    path = str(tmp_path / "gate2.db")
    init_db(path)
    knowledge_dir = DATA_DIR / "knowledge"
    loaded = 0
    for f in sorted(knowledge_dir.glob("known_issues_*.json")):
        load_known_issues_file(f, path)
        loaded += 1
    assert loaded >= 30, f"Expected 30+ knowledge files, found {loaded}"
    return path


class TestGate2KnowledgeBaseIntegration:
    """Gate 2: Query any target bike → get DTCs, symptoms, known issues, fixes."""

    # --- Total knowledge base size ---

    def test_total_issue_count(self, full_db):
        """The knowledge base should contain 650+ issues across all phases."""
        total = count_known_issues(db_path=full_db)
        assert total >= 650, f"Expected 650+ total issues, got {total}"

    # --- Per-make coverage: every target manufacturer has issues ---

    def test_harley_coverage(self, full_db):
        results = search_known_issues(make="Harley-Davidson", db_path=full_db)
        assert len(results) >= 100, f"Harley: expected 100+ issues, got {len(results)}"

    def test_honda_coverage(self, full_db):
        results = search_known_issues(make="Honda", db_path=full_db)
        assert len(results) >= 100, f"Honda: expected 100+ issues, got {len(results)}"

    def test_yamaha_coverage(self, full_db):
        results = search_known_issues(make="Yamaha", db_path=full_db)
        assert len(results) >= 90, f"Yamaha: expected 90+ issues, got {len(results)}"

    def test_kawasaki_coverage(self, full_db):
        results = search_known_issues(make="Kawasaki", db_path=full_db)
        assert len(results) >= 100, f"Kawasaki: expected 100+ issues, got {len(results)}"

    def test_suzuki_coverage(self, full_db):
        results = search_known_issues(make="Suzuki", db_path=full_db)
        assert len(results) >= 100, f"Suzuki: expected 100+ issues, got {len(results)}"

    # --- Symptom-based queries work across all makes ---

    def test_wont_start_cross_make(self, full_db):
        """'Won't start' should return issues from multiple manufacturers."""
        results = find_issues_by_symptom("won't start", full_db)
        assert len(results) >= 50, f"Expected 50+ 'won't start' issues, got {len(results)}"
        makes = set(r.get("make", "") for r in results)
        assert len(makes) >= 4, f"Expected 4+ makes with 'won't start', got {makes}"

    def test_overheating_cross_make(self, full_db):
        results = find_issues_by_symptom("overheating", full_db)
        assert len(results) >= 20, f"Expected 20+ overheating issues, got {len(results)}"

    def test_noise_cross_make(self, full_db):
        results = find_issues_by_symptom("noise", full_db)
        assert len(results) >= 50, f"Expected 50+ noise issues, got {len(results)}"

    def test_battery_not_charging(self, full_db):
        results = find_issues_by_symptom("battery not charging", full_db)
        assert len(results) >= 30, f"Expected 30+ charging issues, got {len(results)}"

    # --- Year-based queries span the full fleet ---

    def test_modern_bikes_2020(self, full_db):
        """2020 model year should return issues from all 5 makes."""
        results = search_known_issues(year=2020, db_path=full_db)
        assert len(results) >= 100, f"Expected 100+ issues for 2020, got {len(results)}"

    def test_vintage_bikes_1985(self, full_db):
        """1985 model year should return vintage issues."""
        results = search_known_issues(year=1985, db_path=full_db)
        assert len(results) >= 20, f"Expected 20+ issues for 1985, got {len(results)}"

    # --- Specific model queries ---

    def test_query_harley_sportster(self, full_db):
        results = search_known_issues(query="Sportster", db_path=full_db)
        assert len(results) >= 5, f"Expected 5+ Sportster issues, got {len(results)}"

    def test_query_honda_cbr(self, full_db):
        results = search_known_issues(query="CBR", db_path=full_db)
        assert len(results) >= 10, f"Expected 10+ CBR issues, got {len(results)}"

    def test_query_gsxr(self, full_db):
        results = search_known_issues(query="GSX-R", db_path=full_db)
        assert len(results) >= 10, f"Expected 10+ GSX-R issues, got {len(results)}"

    # --- Fix procedures contain forum tips ---

    def test_forum_tips_present(self, full_db):
        """Every issue should have a 'Forum tip' in its fix_procedure."""
        all_issues = search_known_issues(db_path=full_db)
        issues_with_tips = sum(
            1 for issue in all_issues
            if "Forum tip" in issue.get("fix_procedure", "")
        )
        # At least 90% should have forum tips
        assert issues_with_tips >= len(all_issues) * 0.9, (
            f"Only {issues_with_tips}/{len(all_issues)} issues have forum tips"
        )

    # --- Cross-platform system queries ---

    def test_cross_platform_charging(self, full_db):
        """Charging system issues should span multiple makes."""
        results = search_known_issues(query="stator", db_path=full_db)
        assert len(results) >= 10, f"Expected 10+ stator issues, got {len(results)}"

    def test_cross_platform_cam_chain(self, full_db):
        results = search_known_issues(query="cam chain", db_path=full_db)
        assert len(results) >= 10, f"Expected 10+ CCT issues, got {len(results)}"

    def test_cross_platform_brakes(self, full_db):
        results = search_known_issues(query="brake fluid", db_path=full_db)
        assert len(results) >= 5, f"Expected 5+ brake fluid issues, got {len(results)}"

    # --- Severity distribution ---

    def test_critical_issues_present(self, full_db):
        critical = search_known_issues(severity="critical", db_path=full_db)
        assert len(critical) >= 20, f"Expected 20+ critical issues, got {len(critical)}"

    def test_severity_distribution(self, full_db):
        """Knowledge base should have a reasonable severity distribution."""
        critical = len(search_known_issues(severity="critical", db_path=full_db))
        high = len(search_known_issues(severity="high", db_path=full_db))
        medium = len(search_known_issues(severity="medium", db_path=full_db))
        total = count_known_issues(db_path=full_db)
        # High + medium should be the majority
        assert (high + medium) > total * 0.6, "High + medium should be >60% of issues"
        # Critical should be a meaningful minority
        assert critical >= 15, f"Expected 15+ critical issues, got {critical}"
