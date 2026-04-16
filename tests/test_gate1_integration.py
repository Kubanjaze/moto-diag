"""Gate 1 — Core infrastructure end-to-end integration test.

Validates the full mechanic workflow: create vehicle → add symptoms → create session
→ add fault codes → search knowledge base → set diagnosis → close session.
"""

import pytest
from motodiag.core.database import init_db
from motodiag.core.models import VehicleBase, ProtocolType
from motodiag.vehicles.registry import add_vehicle, get_vehicle
from motodiag.knowledge.dtc_repo import add_dtc, get_dtc
from motodiag.knowledge.symptom_repo import add_symptom, search_symptoms
from motodiag.knowledge.issues_repo import (
    add_known_issue, find_issues_by_symptom, find_issues_by_dtc,
)
from motodiag.core.session_repo import (
    create_session, get_session, add_symptom_to_session,
    add_fault_code_to_session, set_diagnosis, close_session,
)
from motodiag.core.search import search_all
from motodiag.knowledge.loader import (
    load_dtc_file, load_symptom_file, load_known_issues_file,
)
from motodiag.core.config import DATA_DIR
from motodiag.core.models import DTCCode, SymptomCategory, Severity


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "gate1.db")
    init_db(path)
    return path


class TestGate1FullWorkflow:
    """End-to-end: the complete mechanic diagnostic workflow."""

    def test_full_diagnostic_journey(self, db):
        """Simulate a mechanic diagnosing a Harley Sportster with a dead battery."""

        # Step 1: Mechanic adds their bike to the garage
        vehicle_id = add_vehicle(VehicleBase(
            make="Harley-Davidson", model="Sportster 1200", year=2001,
            engine_cc=1200, protocol=ProtocolType.J1850,
            notes="Customer bike — battery keeps dying",
        ), db)
        vehicle = get_vehicle(vehicle_id, db)
        assert vehicle["make"] == "Harley-Davidson"

        # Step 2: Load knowledge base data
        dtc_dir = DATA_DIR / "dtc_codes"
        if dtc_dir.is_dir():
            load_dtc_file(dtc_dir / "generic.json", db)
            load_dtc_file(dtc_dir / "harley_davidson.json", db)
        symptoms_file = DATA_DIR / "knowledge" / "symptoms.json"
        if symptoms_file.exists():
            load_symptom_file(symptoms_file, db)
        issues_file = DATA_DIR / "knowledge" / "known_issues_harley.json"
        if issues_file.exists():
            load_known_issues_file(issues_file, db)

        # Step 3: Create diagnostic session with initial symptoms
        session_id = create_session(
            "Harley-Davidson", "Sportster 1200", 2001,
            symptoms=["battery not charging"],
            vehicle_id=vehicle_id,
            db_path=db,
        )
        session = get_session(session_id, db)
        assert session["status"] == "open"
        assert "battery not charging" in session["symptoms"]

        # Step 4: Mechanic adds more symptoms during inspection
        add_symptom_to_session(session_id, "headlight dim or flickering", db)
        session = get_session(session_id, db)
        assert len(session["symptoms"]) == 2

        # Step 5: Mechanic reads fault code from ECU
        add_fault_code_to_session(session_id, "P0562", db)
        session = get_session(session_id, db)
        assert "P0562" in session["fault_codes"]

        # Step 6: Look up the fault code
        dtc = get_dtc("P0562", make="Harley-Davidson", db_path=db)
        assert dtc is not None
        assert "voltage" in dtc["description"].lower() or "stator" in str(dtc.get("common_causes", "")).lower()

        # Step 7: Search knowledge base for related issues
        issues_by_symptom = find_issues_by_symptom("battery not charging", db)
        assert len(issues_by_symptom) >= 1
        stator_issue = [i for i in issues_by_symptom if "stator" in i["title"].lower()]
        assert len(stator_issue) >= 1

        issues_by_dtc = find_issues_by_dtc("P0562", db)
        assert len(issues_by_dtc) >= 1

        # Step 8: Unified search confirms the diagnosis path
        results = search_all("stator", make="Harley-Davidson", db_path=db)
        assert results["total"] > 0
        assert len(results["known_issues"]) >= 1

        # Step 9: Mechanic sets diagnosis with confidence
        known = stator_issue[0]
        set_diagnosis(
            session_id,
            diagnosis=f"Stator failure — {known['title']}. {known.get('fix_procedure', '')[:100]}",
            confidence=0.90,
            severity="high",
            repair_steps=[
                "Test stator AC output (18-22V per leg at 2000 RPM)",
                "Check for shorts to ground on stator legs",
                "Replace stator (upgrade to Cycle Electric)",
                "Replace voltage regulator if connector shows heat damage",
                "Test charging system after repair (13.5-14.5V at 2000 RPM)",
            ],
            db_path=db,
        )
        session = get_session(session_id, db)
        assert session["status"] == "diagnosed"
        assert session["confidence"] == 0.90
        assert len(session["repair_steps"]) == 5

        # Step 10: Close the session after repair
        close_session(session_id, db)
        session = get_session(session_id, db)
        assert session["status"] == "closed"
        assert session["closed_at"] is not None

    def test_cross_store_linkage(self, db):
        """Verify that symptoms, DTCs, and known issues are linked correctly."""
        # Add a DTC
        add_dtc(DTCCode(
            code="P0300", description="Random/Multiple Cylinder Misfire",
            category=SymptomCategory.ENGINE, severity=Severity.HIGH,
        ), db)

        # Add related symptom
        add_symptom("misfires", "Engine skips under load",
                    "engine", ["fuel", "engine", "electrical"], db)

        # Add known issue linking both
        issue_id = add_known_issue(
            title="Intake manifold air leak causing misfire",
            description="Cracked intake seals cause lean misfire",
            make="Harley-Davidson", year_start=1984,
            severity="high",
            symptoms=["misfires", "rough idle", "backfires"],
            dtc_codes=["P0300", "P1010"],
            causes=["Cracked intake seal"],
            fix_procedure="Spray carb cleaner at seals to confirm. Replace both seals.",
            db_path=db,
        )

        # Verify cross-store query: symptom → known issue
        issues = find_issues_by_symptom("misfires", db)
        assert len(issues) >= 1
        assert issues[0]["title"] == "Intake manifold air leak causing misfire"

        # Verify cross-store query: DTC → known issue
        issues = find_issues_by_dtc("P0300", db)
        assert len(issues) >= 1

        # Verify unified search finds everything
        results = search_all("misfire", db_path=db)
        assert results["total"] >= 2  # at least DTC + known issue


class TestDBInitCLI:
    def test_db_init_command(self):
        from click.testing import CliRunner
        from motodiag.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["db", "init"])
        assert result.exit_code == 0
        assert "Database ready" in result.output

    def test_db_init_loads_data(self):
        from click.testing import CliRunner
        from motodiag.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["db", "init"])
        assert "DTC codes" in result.output
        assert "symptoms" in result.output
        assert "known issues" in result.output
