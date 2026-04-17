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
        from motodiag.core.config import DATA_DIR
        generic = DATA_DIR / "dtc_codes" / "generic.json"
        if generic.exists():
            count = load_dtc_file(generic, db_path)
            assert count == 20

    def test_load_real_harley(self, db_path):
        from motodiag.core.config import DATA_DIR
        harley = DATA_DIR / "dtc_codes" / "harley_davidson.json"
        if harley.exists():
            count = load_dtc_file(harley, db_path)
            assert count == 20

    def test_file_not_found(self, db_path):
        with pytest.raises(FileNotFoundError):
            load_dtc_file("/nonexistent/file.json", db_path)


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
