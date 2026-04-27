"""Phase 05 — DTC schema, repo, and loader tests."""

import json
import pytest
from pathlib import Path

from motodiag.core.database import init_db
from motodiag.core.models import DTCCode, SymptomCategory, Severity
from motodiag.knowledge.dtc_repo import add_dtc, get_dtc, search_dtcs, list_dtcs_by_make, count_dtcs
from motodiag.knowledge.loader import load_dtc_file, load_dtc_directory


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


@pytest.fixture
def sample_dtc():
    return DTCCode(
        code="P0115",
        description="Engine Coolant Temperature Circuit Malfunction",
        category=SymptomCategory.COOLING,
        severity=Severity.MEDIUM,
        common_causes=["Faulty sensor", "Bad wiring", "Corroded connector"],
        fix_summary="Check sensor resistance, replace if out of spec.",
    )


@pytest.fixture
def harley_dtc():
    return DTCCode(
        code="P0115",
        description="ECT Sensor Low Input — Harley-Davidson specific",
        category=SymptomCategory.COOLING,
        severity=Severity.MEDIUM,
        make="Harley-Davidson",
        common_causes=["Faulty ECT sensor at cylinder head"],
        fix_summary="Test ECT sensor resistance per HD service manual.",
    )


class TestDTCRepo:
    def test_add_and_get(self, db_path, sample_dtc):
        add_dtc(sample_dtc, db_path)
        result = get_dtc("P0115", db_path=db_path)
        assert result is not None
        assert result["code"] == "P0115"
        assert result["description"] == "Engine Coolant Temperature Circuit Malfunction"

    def test_get_not_found(self, db_path):
        assert get_dtc("PXXXX", db_path=db_path) is None

    def test_make_specific_lookup(self, db_path, sample_dtc, harley_dtc):
        add_dtc(sample_dtc, db_path)
        add_dtc(harley_dtc, db_path)
        # Harley-specific lookup
        result = get_dtc("P0115", make="Harley-Davidson", db_path=db_path)
        assert "Harley-Davidson specific" in result["description"]
        # Generic fallback
        result = get_dtc("P0115", make="Honda", db_path=db_path)
        assert "Harley-Davidson specific" not in result["description"]

    def test_common_causes_parsed(self, db_path, sample_dtc):
        add_dtc(sample_dtc, db_path)
        result = get_dtc("P0115", db_path=db_path)
        assert isinstance(result["common_causes"], list)
        assert len(result["common_causes"]) == 3

    def test_search_by_category(self, db_path, sample_dtc):
        add_dtc(sample_dtc, db_path)
        results = search_dtcs(category="cooling", db_path=db_path)
        assert len(results) == 1

    def test_search_by_query(self, db_path, sample_dtc):
        add_dtc(sample_dtc, db_path)
        results = search_dtcs(query="coolant", db_path=db_path)
        assert len(results) == 1

    def test_search_empty(self, db_path):
        assert search_dtcs(query="nonexistent", db_path=db_path) == []

    def test_list_by_make(self, db_path, harley_dtc):
        add_dtc(harley_dtc, db_path)
        results = list_dtcs_by_make("Harley-Davidson", db_path=db_path)
        assert len(results) == 1

    def test_count(self, db_path, sample_dtc, harley_dtc):
        add_dtc(sample_dtc, db_path)
        add_dtc(harley_dtc, db_path)
        assert count_dtcs(db_path) == 2


class TestLoader:
    def test_load_file(self, db_path, tmp_path):
        dtc_file = tmp_path / "test.json"
        dtc_file.write_text(json.dumps([
            {"code": "P0300", "description": "Random Misfire", "category": "engine"},
            {"code": "P0301", "description": "Cyl 1 Misfire", "category": "engine"},
        ]))
        count = load_dtc_file(dtc_file, db_path)
        assert count == 2
        assert count_dtcs(db_path) == 2

    def test_load_directory(self, db_path, tmp_path):
        f1 = tmp_path / "a.json"
        f2 = tmp_path / "b.json"
        f1.write_text(json.dumps([{"code": "P0100", "description": "MAF", "category": "fuel"}]))
        f2.write_text(json.dumps([{"code": "P0200", "description": "Injector", "category": "fuel"}]))
        results = load_dtc_directory(tmp_path, db_path)
        assert results["a.json"] == 1
        assert results["b.json"] == 1
        assert count_dtcs(db_path) == 2

    def test_load_real_generic(self, db_path):
        # Phase 190 commit 8 expanded generic.json from 20 → 35
        # codes, adding the common OBD-II codes (P0171/P0172/P0174/
        # P0175 fuel-trim family, P0299 boost, P0302-P0304 misfire
        # extension, P0430 cat bank-2, P0440/P0442/P0455 EVAP,
        # P0506/P0507 idle, P0521 oil pressure) that the catalog
        # was missing. Architect-gate Bug 3 caught the absence at
        # GET /v1/kb/dtc/P0171 → 404. Floor at >= 35 lets future
        # phases extend without churning this assertion; ceiling
        # implicit via the seed file as source of truth.
        from motodiag.core.config import DATA_DIR
        generic = DATA_DIR / "dtc_codes" / "generic.json"
        if generic.exists():
            count = load_dtc_file(generic, db_path)
            assert count >= 35
            # Spot-check the codes from the architect's "top 20
            # most-common" list explicitly so a future seed regression
            # that drops one fails this test loudly.
            from motodiag.knowledge.dtc_repo import get_dtc
            for must_have in ["P0171", "P0300", "P0301", "P0420", "P0440", "P0455"]:
                assert get_dtc(must_have, db_path=db_path) is not None, (
                    f"Phase 190 Bug 3 regression: {must_have} missing from generic seed"
                )

    def test_load_real_harley(self, db_path):
        from motodiag.core.config import DATA_DIR
        harley = DATA_DIR / "dtc_codes" / "harley_davidson.json"
        if harley.exists():
            count = load_dtc_file(harley, db_path)
            assert count == 20

    def test_file_not_found(self, db_path):
        with pytest.raises(FileNotFoundError):
            load_dtc_file("/nonexistent/file.json", db_path)

    def test_reload_same_file_is_idempotent_for_null_make(self, db_path, tmp_path):
        """Phase 190 commit 8 (Bug 3a fix). Re-seeding the generic
        catalog (make=null) used to insert duplicate rows because
        SQLite's UNIQUE(code, make) doesn't enforce uniqueness for
        NULL-make rows (NULL != NULL in UNIQUE semantics). Result:
        architect emulator DBs accumulated 7+ identical P0100 rows
        across multiple `motodiag db init` runs.

        Fix: load_dtc_file now pre-deletes existing rows matching
        each (code, make) pair from the file, including the NULL-
        make path. Re-running the same load is now idempotent.
        """
        dtc_file = tmp_path / "generic_subset.json"
        dtc_file.write_text(json.dumps([
            {"code": "P0100", "description": "MAF", "category": "fuel"},
            {"code": "P0171", "description": "Lean", "category": "fuel"},
        ]))
        # First load
        count1 = load_dtc_file(dtc_file, db_path)
        assert count1 == 2
        assert count_dtcs(db_path) == 2
        # Second load — must NOT duplicate
        count2 = load_dtc_file(dtc_file, db_path)
        assert count2 == 2
        assert count_dtcs(db_path) == 2, (
            f"Bug 3a regression: re-load created duplicate NULL-make "
            f"rows. Got {count_dtcs(db_path)} rows, expected 2."
        )
        # Third load — same result. Belt and suspenders.
        load_dtc_file(dtc_file, db_path)
        assert count_dtcs(db_path) == 2

    def test_reload_dedups_existing_null_make_duplicates(self, db_path, tmp_path):
        """Phase 190 commit 8 (Bug 3a fix). For dev databases that
        already accumulated duplicates pre-fix, re-running the
        seed must clean them up. Simulate the bug state by
        manually inserting duplicate NULL-make rows, then verify
        a re-seed leaves only one of each."""
        from motodiag.core.database import get_connection

        # Manually insert 5 copies of P0100 (all make=NULL) — this
        # is what the architect's pre-fix DB looked like.
        with get_connection(db_path) as conn:
            for _ in range(5):
                conn.execute(
                    "INSERT INTO dtc_codes (code, description, category, severity, make) "
                    "VALUES (?, ?, ?, ?, NULL)",
                    ("P0100", "Mass Air Flow", "fuel", "medium"),
                )
        assert count_dtcs(db_path) == 5

        # Re-seed: load a file that includes P0100 with make=NULL
        dtc_file = tmp_path / "fix_seed.json"
        dtc_file.write_text(json.dumps([
            {"code": "P0100", "description": "MAF (canonical)", "category": "fuel"},
        ]))
        load_dtc_file(dtc_file, db_path)
        # All 5 dups gone, exactly one P0100 row remains.
        assert count_dtcs(db_path) == 1


class TestCLI:
    def test_code_help(self):
        """`motodiag code --help` renders help text (exit 0).

        Phase 124 update: the bare `motodiag code` invocation (no DTC arg)
        now errors with a ClickException, so this test exercises `--help`
        instead. Help text is the right surface to verify CLI wiring.
        """
        from click.testing import CliRunner
        from motodiag.cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["code", "--help"])
        assert result.exit_code == 0
        assert "Usage" in result.output
