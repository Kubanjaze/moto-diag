"""Phase 211 — BMW R-series boxer twin, and the provenance column.

Two things are under test. The BMW content itself follows the Track B
pattern (load the file, assert coverage). The provenance column is new:
Track K is thirty phases of repair knowledge authored from training
data, and until migration 051 nothing distinguished a service-manual
figure from a generated one. So this file also asserts that every BMW
entry says where it came from, that legacy files load honestly as
`unverified`, that the CHECK stops a typo becoming a fourth silent
category, and that the CLI actually warns a mechanic — because a
provenance field nobody sees protects nobody.
"""

from __future__ import annotations

import json
import sqlite3

import pytest
from click.testing import CliRunner

from motodiag.cli.main import cli
from motodiag.core.config import SEED_DATA_DIR
from motodiag.core.database import get_connection, init_db
from motodiag.knowledge.issues_repo import (
    add_known_issue,
    count_known_issues,
    find_issues_by_symptom,
    get_known_issue,
    search_known_issues,
)
from motodiag.knowledge.loader import load_known_issues_file

BMW_FILE = SEED_DATA_DIR / "knowledge" / "known_issues_bmw_r_series.json"
LEGACY_FILE = SEED_DATA_DIR / "knowledge" / "known_issues_honda_cbr600f.json"


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "bmw.db")
    init_db(path)
    load_known_issues_file(BMW_FILE, path)
    return path


class TestBMWRSeriesData:
    def test_loads_twelve(self, db_path):
        assert count_known_issues(db_path=db_path) == 12

    def test_all_are_bmw(self, db_path):
        rows = search_known_issues(make="BMW", db_path=db_path)
        assert len(rows) == 12

    @pytest.mark.parametrize("year,minimum", [
        (1975, 2),   # airhead: diode board, rotor
        (1999, 5),   # oilhead: surging, HES, clutch, splines, iABS...
        (2008, 5),   # hexhead: final drive, fuel strip, iABS tail, belt...
        (2018, 2),   # wethead: water pump, belt-alternator span
    ])
    def test_every_generation_is_covered(self, db_path, year, minimum):
        rows = search_known_issues(year=year, make="BMW", db_path=db_path)
        assert len(rows) >= minimum, f"{year}: {[r['title'] for r in rows]}"

    def test_the_headline_failures_are_present(self, db_path):
        titles = " ".join(r["title"].lower()
                          for r in search_known_issues(make="BMW", db_path=db_path))
        for needle in ("final drive", "surging", "hall-effect", "integral abs",
                       "diode board", "spline"):
            assert needle in titles, f"missing {needle!r}"

    def test_charging_symptom_reaches_three_generations(self, db_path):
        rows = find_issues_by_symptom("battery not charging", db_path)
        models = {r["model"] for r in rows}
        assert len(rows) >= 3
        assert any("airhead" in m for m in models)
        assert any("belt" in m for m in models)

    def test_critical_entries_are_the_dangerous_ones(self, db_path):
        rows = search_known_issues(severity="critical", make="BMW", db_path=db_path)
        titles = {r["title"] for r in rows}
        assert any("Final drive" in t for t in titles)
        assert any("ABS" in t for t in titles)

    def test_every_entry_has_a_procedure_and_parts(self, db_path):
        for row in search_known_issues(make="BMW", db_path=db_path):
            assert row["fix_procedure"], row["title"]
            parts = row["parts_needed"]
            # the repo deserialises JSON columns; tolerate a raw string
            # in case that ever changes, since this is a content check
            if isinstance(parts, str):
                parts = json.loads(parts)
            assert parts, row["title"]
            assert row["estimated_hours"] > 0, row["title"]


class TestProvenanceIsRecorded:
    """The point of the phase. Content that cannot say where it came
    from cannot be reviewed."""

    def test_every_bmw_entry_is_tagged_model_generated(self, db_path):
        rows = search_known_issues(make="BMW", db_path=db_path)
        assert {r["source"] for r in rows} == {"model-generated"}

    def test_the_seed_file_says_so_too(self):
        """The tag lives in the JSON, not just the loader default —
        so it survives a re-import and is visible in the repo."""
        data = json.loads(BMW_FILE.read_text(encoding="utf-8"))
        assert len(data) == 12
        assert all(item.get("source") == "model-generated" for item in data)

    def test_every_bmw_description_admits_its_origin(self):
        """A reader of the raw text, with no schema in front of them,
        should still be told."""
        data = json.loads(BMW_FILE.read_text(encoding="utf-8"))
        for item in data:
            assert "general knowledge" in item["description"].lower(), item["title"]

    def test_a_legacy_file_loads_as_unverified(self, tmp_path):
        """The 660 pre-existing entries carry no `source` key. Their
        origin was never recorded; `unverified` is the true value, not a
        downgrade."""
        path = str(tmp_path / "legacy.db")
        init_db(path)
        load_known_issues_file(LEGACY_FILE, path)
        rows = search_known_issues(make="Honda", db_path=path)
        assert rows and {r["source"] for r in rows} == {"unverified"}

    def test_the_default_on_insert_is_unverified(self, tmp_path):
        path = str(tmp_path / "ins.db")
        init_db(path)
        iid = add_known_issue("t", "d", make="X", db_path=path)
        assert get_known_issue(iid, db_path=path)["source"] == "unverified"

    def test_the_check_rejects_a_typo(self, tmp_path):
        """`model_generated` with an underscore must not become a fourth
        silent category."""
        path = str(tmp_path / "chk.db")
        init_db(path)
        with pytest.raises(sqlite3.IntegrityError):
            add_known_issue("t", "d", db_path=path, source="model_generated")

    @pytest.mark.parametrize("value", [
        "unverified", "model-generated", "forum",
        "service-manual", "mechanic-verified",
        "regulation",  # Phase 235B, migration 052
    ])
    def test_the_full_vocabulary_is_accepted(self, tmp_path, value):
        path = str(tmp_path / f"{value}.db")
        init_db(path)
        iid = add_known_issue("t", "d", db_path=path, source=value)
        assert get_known_issue(iid, db_path=path)["source"] == value


class TestTheMechanicIsActuallyWarned:
    """A provenance field the CLI does not render protects nobody."""

    def _show(self, db_path, issue_id):
        return CliRunner().invoke(
            cli, ["kb", "show", str(issue_id)],
            env={"MOTODIAG_DB_PATH": db_path, "COLUMNS": "120"},
        )

    def test_model_generated_shows_source_and_warning(self, db_path, monkeypatch):
        from motodiag.core.config import reset_settings
        monkeypatch.setenv("MOTODIAG_DB_PATH", db_path); reset_settings()
        row = search_known_issues(make="BMW", db_path=db_path)[0]
        result = self._show(db_path, row["id"])
        assert result.exit_code == 0, result.output
        assert "model-generated" in result.output
        assert "service manual" in result.output.lower()
        reset_settings()

    def test_verified_content_is_not_nagged(self, tmp_path, monkeypatch):
        """The warning only means something if it can be absent."""
        from motodiag.core.config import reset_settings
        path = str(tmp_path / "ver.db")
        init_db(path)
        iid = add_known_issue("Verified thing", "d", make="BMW",
                              fix_procedure="do it", db_path=path,
                              source="service-manual")
        monkeypatch.setenv("MOTODIAG_DB_PATH", path); reset_settings()
        result = self._show(path, iid)
        assert result.exit_code == 0, result.output
        assert "service-manual" in result.output
        assert "⚠" not in result.output
        reset_settings()

    def test_list_shows_a_source_column(self, db_path, monkeypatch):
        from motodiag.core.config import reset_settings
        monkeypatch.setenv("MOTODIAG_DB_PATH", db_path); reset_settings()
        result = CliRunner().invoke(
            cli, ["kb", "list", "--make", "bmw"],
            env={"MOTODIAG_DB_PATH": db_path, "COLUMNS": "160"},
        )
        assert result.exit_code == 0, result.output
        assert "Source" in result.output
        assert "model-generated" in result.output
        reset_settings()


class TestTheApiCarriesProvenance:
    def test_issue_response_includes_source(self, db_path):
        from fastapi.testclient import TestClient

        from motodiag.api.app import create_app
        from motodiag.auth.api_key_repo import create_api_key

        with get_connection(db_path) as conn:
            uid = conn.execute(
                "INSERT INTO users (username, email, tier, is_active) "
                "VALUES ('u', 'u@ex.com', 'individual', 1)",
            ).lastrowid
        _, key = create_api_key(uid, db_path=db_path)
        client = TestClient(create_app(db_path_override=db_path))
        row = search_known_issues(make="BMW", db_path=db_path)[0]
        r = client.get(f"/v1/kb/issues/{row['id']}", headers={"X-API-Key": key})
        assert r.status_code == 200, r.text
        assert r.json()["source"] == "model-generated"

    def test_openapi_emits_a_strict_enum(self):
        """So the mobile codegen gets a typed union, not a string — the
        F37 discipline the F9 lint enforced on this very field."""
        from motodiag.api.app import create_app

        prop = create_app().openapi()["components"]["schemas"][
            "KnownIssueResponse"]["properties"]["source"]
        assert set(prop["enum"]) == {
            "unverified", "model-generated", "forum",
            "service-manual", "mechanic-verified",
            "regulation",  # Phase 235B, migration 052
        }
