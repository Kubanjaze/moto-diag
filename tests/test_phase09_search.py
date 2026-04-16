"""Phase 09 — unified search engine tests."""

import pytest
from motodiag.core.database import init_db
from motodiag.core.search import search_all
from motodiag.core.models import DTCCode, SymptomCategory, Severity
from motodiag.knowledge.dtc_repo import add_dtc
from motodiag.knowledge.symptom_repo import add_symptom
from motodiag.knowledge.issues_repo import add_known_issue
from motodiag.vehicles.registry import add_vehicle
from motodiag.core.models import VehicleBase, ProtocolType


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


@pytest.fixture
def populated_db(db_path):
    """Populate DB with sample data across all stores."""
    # Vehicle
    add_vehicle(VehicleBase(
        make="Harley-Davidson", model="Sportster 1200", year=2001,
        protocol=ProtocolType.J1850,
    ), db_path)
    # DTC
    add_dtc(DTCCode(
        code="P0562", description="System Voltage Low",
        category=SymptomCategory.ELECTRICAL, severity=Severity.HIGH,
        common_causes=["Faulty stator", "Bad regulator"],
    ), db_path)
    # Symptom
    add_symptom("battery not charging", "Battery voltage drops while riding",
                "electrical", ["electrical"], db_path)
    # Known issue
    add_known_issue(
        title="Stator failure — chronic undercharging",
        description="Harley stators break down from heat",
        make="Harley-Davidson", year_start=1999, year_end=2017,
        severity="high",
        symptoms=["battery not charging"],
        dtc_codes=["P0562"],
        db_path=db_path,
    )
    return db_path


class TestSearchAll:
    def test_finds_across_stores(self, populated_db):
        results = search_all("stator", db_path=populated_db)
        assert results["total"] > 0
        # Should find in known issues (title matches)
        assert len(results["known_issues"]) >= 1

    def test_finds_dtc_by_code(self, populated_db):
        results = search_all("P0562", db_path=populated_db)
        assert len(results["dtc_codes"]) >= 1

    def test_finds_symptom(self, populated_db):
        results = search_all("charging", db_path=populated_db)
        assert len(results["symptoms"]) >= 1

    def test_empty_query(self, populated_db):
        results = search_all("", db_path=populated_db)
        assert results["total"] == 0

    def test_no_results(self, populated_db):
        results = search_all("xyznonexistent", db_path=populated_db)
        assert results["total"] == 0

    def test_with_make_filter(self, populated_db):
        results = search_all("stator", make="Harley-Davidson", db_path=populated_db)
        assert len(results["known_issues"]) >= 1


class TestSearchCLI:
    def test_search_command(self):
        from click.testing import CliRunner
        from motodiag.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "test"])
        assert result.exit_code == 0
