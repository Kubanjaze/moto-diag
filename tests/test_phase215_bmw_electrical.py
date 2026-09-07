"""Phase 215 — BMW electrical, ZFE, GS-911 and the fault-code backlog.

This phase closes the BMW block and touches three surfaces rather than
one: the DTC seed, the hardware adapter catalog, and known_issues.

Its governing constraint is that **a wrong fault code is worse than a
missing one**. A vague knowledge-base entry wastes an hour; a code
number sends a mechanic to a specific component with false confidence,
because a code reads as a fact rather than an opinion. So the DTC
assertions here are about identity and honesty, not coverage:

- every code is a real, standard-format number;
- no invented entry in the manufacturer-defined P1xxx range;
- no BMW *proprietary* code (the kind GS-911 and ISTA read) smuggled in
  wearing P-code clothing — those are not P-codes, and this phase
  documents their existence as knowledge rather than fabricating rows;
- and because `get_dtcs` resolves make-specific **before** generic, a
  BMW row *shadows* the generic row for a BMW bike. A row that merely
  restates the generic text would actively hide better content, so the
  shadowing tests check that the BMW rows add something.

That last check is not hypothetical: the one code dropped in this phase
(P0135) was killed by exactly that reasoning — the generic O2 entry
already carried a heater-resistance range and eliminator guidance the
BMW row would have hidden.
"""

from __future__ import annotations

import json
import re

import pytest

from motodiag.core.config import SEED_DATA_DIR
from motodiag.core.database import get_connection, init_db
from motodiag.knowledge.dtc_repo import get_dtcs
from motodiag.knowledge.issues_repo import count_known_issues, search_known_issues
from motodiag.knowledge.loader import load_dtc_file, load_known_issues_file

BMW_DTC = SEED_DATA_DIR / "dtc_codes" / "bmw.json"
GENERIC_DTC = SEED_DATA_DIR / "dtc_codes" / "generic.json"
BMW_ELEC = SEED_DATA_DIR / "knowledge" / "known_issues_bmw_electrical.json"
F_FILE = SEED_DATA_DIR / "knowledge" / "known_issues_bmw_f_series_gs.json"

COMPAT = (
    SEED_DATA_DIR.parent.parent / "hardware" / "compat_data"
)
ADAPTERS = COMPAT / "adapters.json"
MATRIX = COMPAT / "compat_matrix.json"

#: Standard OBD-II shape. Anything else is either a typo or a BMW
#: proprietary code that does not belong in this table.
STD_CODE = re.compile(r"^[PUBC][0-3][0-9A-F]{3}$")


@pytest.fixture
def dtc_db(tmp_path):
    path = str(tmp_path / "dtc.db")
    init_db(path)
    load_dtc_file(GENERIC_DTC, path)
    load_dtc_file(BMW_DTC, path)
    return path


@pytest.fixture
def raw_dtc():
    return json.loads(BMW_DTC.read_text(encoding="utf-8"))


@pytest.fixture
def raw_issues():
    return json.loads(BMW_ELEC.read_text(encoding="utf-8"))


class TestNoFabricatedCodes:
    """The phase's governing constraint."""

    def test_every_code_is_standard_format(self, raw_dtc):
        for c in raw_dtc:
            assert STD_CODE.match(c["code"]), f"{c['code']!r} is not a standard DTC"

    def test_no_invented_manufacturer_range_codes(self, raw_dtc):
        """P1xxx is the manufacturer-defined range. The plan forbids
        inventing a BMW number there, and nothing survived that would
        have required one."""
        for c in raw_dtc:
            assert not c["code"].startswith("P1"), (
                f"{c['code']}: P1xxx requires a documented BMW motorcycle "
                "source, not a plausible guess"
            )

    def test_no_duplicate_codes_in_the_file(self, raw_dtc):
        codes = [c["code"] for c in raw_dtc]
        assert len(codes) == len(set(codes))

    def test_every_row_is_marked_bmw(self, raw_dtc):
        assert {c["make"] for c in raw_dtc} == {"BMW"}

    def test_vocabularies_are_valid(self, raw_dtc):
        from motodiag.core.models import Severity, SymptomCategory

        cats = {e.value for e in SymptomCategory}
        sevs = {e.value for e in Severity}
        for c in raw_dtc:
            assert c["category"] in cats, f"{c['code']}: {c['category']}"
            assert c["severity"] in sevs, f"{c['code']}: {c['severity']}"

    def test_every_row_has_causes_and_a_fix(self, raw_dtc):
        for c in raw_dtc:
            assert c["common_causes"], c["code"]
            assert c["fix_summary"].strip(), c["code"]


class TestShadowingIsEarned:
    """`get_dtcs` resolves make-specific before generic, so a BMW row
    hides the generic row for a BMW bike. It has to be worth hiding it."""

    def test_a_bmw_bike_gets_the_bmw_row(self, dtc_db):
        rows = get_dtcs(["P0335"], make="BMW", db_path=dtc_db)
        row = rows[0] if isinstance(rows, list) else list(rows.values())[0]
        assert row["make"] == "BMW"

    def test_another_make_still_gets_the_generic_row(self, dtc_db):
        rows = get_dtcs(["P0335"], make="Honda", db_path=dtc_db)
        row = rows[0] if isinstance(rows, list) else list(rows.values())[0]
        assert row["make"] is None, "a BMW row leaked onto a Honda"

    def test_shadowing_rows_do_not_restate_the_generic_text(self, raw_dtc):
        """The specific failure the shadow refuter exists to catch: a
        BMW row whose causes are the generic causes with a badge on."""
        generic = {
            c["code"]: c
            for c in json.loads(GENERIC_DTC.read_text(encoding="utf-8"))
        }
        for c in raw_dtc:
            g = generic.get(c["code"])
            if not g:
                continue
            assert c["common_causes"] != g.get("common_causes"), (
                f"{c['code']}: BMW causes identical to generic — this row "
                "hides the generic row and adds nothing"
            )
            assert c["fix_summary"] != g.get("fix_summary"), c["code"]

    def test_at_least_one_row_actually_shadows(self, raw_dtc):
        """Keeps the test above from passing vacuously."""
        generic = {
            c["code"] for c in json.loads(GENERIC_DTC.read_text(encoding="utf-8"))
        }
        assert {c["code"] for c in raw_dtc} & generic


class TestTheDealerModeEntriesAreTheRealDeliverable:
    def test_entries_load(self, tmp_path):
        path = str(tmp_path / "e.db")
        init_db(path)
        n = load_known_issues_file(BMW_ELEC, path)
        assert n == count_known_issues(db_path=path) == len(
            json.loads(BMW_ELEC.read_text(encoding="utf-8"))
        )

    def test_the_read_access_problem_is_covered(self, raw_issues):
        """The most useful thing this phase can say: a generic ELM327
        reads emissions P-codes but is blind to BMW's proprietary
        session, so "no codes found" is not "no fault"."""
        blob = json.dumps(raw_issues).lower()
        assert "elm327" in blob
        assert "gs-911" in blob or "gs911" in blob

    def test_proprietary_codes_are_described_not_enumerated(self, raw_issues):
        """The format is documented as knowledge; the numbers are not
        invented as data. Any code cited must be standard-format."""
        for e in raw_issues:
            for code in e["dtc_codes"]:
                assert STD_CODE.match(code), (
                    f"{e['title']}: {code!r} is not a standard DTC — BMW "
                    "proprietary codes must not be transcribed"
                )

    def test_it_does_not_restate_phase_212s_zfe_accessory_entries(self, raw_issues):
        """Phase 212 wrote three ZFE *accessory* entries for the
        F-series. This phase covers the ZFE as a diagnostic subject."""
        f_titles = {
            e["title"] for e in json.loads(F_FILE.read_text(encoding="utf-8"))
        }
        for e in raw_issues:
            assert e["title"] not in f_titles, e["title"]
        titles = " ".join(e["title"].lower() for e in raw_issues)
        assert "heated grips" not in titles
        assert "accessory spliced" not in titles

    def test_contract_holds(self, raw_issues):
        for e in raw_issues:
            assert e["make"] == "BMW", e["title"]
            assert e["source"] == "model-generated", e["title"]
            assert "general knowledge" in e["description"].lower(), e["title"]
            assert e["severity"] in {"critical", "high", "medium", "low"}
            for s in e["symptoms"]:
                assert len(s) <= 55 and not s.endswith("."), f"{e['title']}: {s!r}"


class TestGs911IsInTheCatalog:
    @pytest.fixture(scope="class")
    def adapters(self):
        return json.loads(ADAPTERS.read_text(encoding="utf-8"))

    @pytest.fixture(scope="class")
    def matrix(self):
        return json.loads(MATRIX.read_text(encoding="utf-8"))

    def test_the_adapter_exists(self, adapters):
        slugs = {a["slug"] for a in adapters}
        assert "hex-gs-911-wifi" in slugs

    def test_it_matches_the_catalog_schema(self, adapters):
        gs = next(a for a in adapters if a["slug"] == "hex-gs-911-wifi")
        peer = next(a for a in adapters if a["slug"] == "obdlink-mx-plus")
        assert set(gs) == set(peer), "GS-911 row diverges from the schema"

    def test_mode22_is_false(self, adapters):
        """The drafting agent flagged this against itself: the GS-911
        reads live data through BMW proprietary service requests, not
        generic OBD Mode 22. The flag feeds the recommender, so the
        honest value matters."""
        gs = next(a for a in adapters if a["slug"] == "hex-gs-911-wifi")
        assert gs["supports_mode22"] is False

    def test_compat_rows_are_bmw_only(self, matrix):
        rows = [r for r in matrix if r["adapter_slug"] == "hex-gs-911-wifi"]
        assert rows, "no compat rows for the GS-911"
        assert {r["make"] for r in rows} == {"bmw"}, (
            "the GS-911 is unusable on any other make"
        )

    def test_every_row_declares_its_provenance(self, matrix):
        rows = [r for r in matrix if r["adapter_slug"] == "hex-gs-911-wifi"]
        for r in rows:
            assert r["verified_by"].strip(), r["model_pattern"]

    def test_the_speculative_future_model_row_was_dropped(self, matrix):
        """The draft included an R1300GS row it described as 'the most
        speculative item here ... inferred, not sourced'. It was cut
        rather than shipped with a hedge."""
        rows = [r for r in matrix if r["adapter_slug"] == "hex-gs-911-wifi"]
        assert not any(r["model_pattern"].startswith("R13") for r in rows)

    def test_it_covers_the_bmw_families_this_corpus_knows(self, matrix):
        rows = [r for r in matrix if r["adapter_slug"] == "hex-gs-911-wifi"]
        patterns = " ".join(r["model_pattern"] for r in rows)
        for family in ("R12", "F", "S1000", "K1"):
            assert family in patterns, f"no coverage row for {family}"


class TestTheWholeBmwBlockStillCoheres:
    def test_all_five_bmw_files_load_together(self, tmp_path):
        path = str(tmp_path / "bmw.db")
        init_db(path)
        files = list((SEED_DATA_DIR / "knowledge").glob("known_issues_bmw_*.json"))
        assert len(files) == 5, [f.name for f in files]
        for f in files:
            load_known_issues_file(f, path)
        assert len(search_known_issues(make="BMW", db_path=path)) == 44

    def test_no_title_collides_across_the_bmw_files(self):
        titles = []
        for f in (SEED_DATA_DIR / "knowledge").glob("known_issues_bmw_*.json"):
            titles += [e["title"] for e in json.loads(f.read_text(encoding="utf-8"))]
        assert len(titles) == len(set(titles))
