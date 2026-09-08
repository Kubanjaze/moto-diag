"""Phase 220 — Ducati electrical + FI. Closes the Ducati block.

The direct analogue of Phase 215 (BMW electrical), and it inherits that
phase's finding rather than just its shape. In 215 the fabricated-code
lens found nothing; the **shadowing** lens found the real hazard. Because
`get_dtcs` resolves make-specific rows *before* generic ones, a Ducati
row that merely restates the generic row does not fail to help — it
**hides** the better generic answer. 215 dropped its only rejected code
(P0135) on exactly that reasoning.

So every one of the six codes here shadows a generic row deliberately,
and each is asserted to differ from the row it displaces. The strongest
Ducati-specific content is **cylinder identity on an L-twin**: cylinder
1 is the horizontal front cylinder and cylinder 2 the vertical rear one,
which no generic misfire row can say and which sends a mechanic to the
wrong cylinder if read as an inline engine.

Two things this phase deliberately does *not* do. It adds nothing to the
adapter catalog — the OEM DDS and seven other adapters already carry
eight Ducati compat rows, and the catalog already records that
counterfeit ELM327 silicon fails on newer Ducati CAN. And it transcribes
no Ducati proprietary fault number; that numbering is documented as a
format, exactly as BMW's was.
"""

from __future__ import annotations

import json
import re

import pytest

from motodiag.core.config import SEED_DATA_DIR
from motodiag.core.database import init_db
from motodiag.knowledge.dtc_repo import get_dtcs
from motodiag.knowledge.issues_repo import (
    count_known_issues,
    find_issues_by_symptom,
    search_known_issues,
)
from motodiag.knowledge.loader import load_dtc_file, load_known_issues_file

D = SEED_DATA_DIR / "dtc_codes"
K = SEED_DATA_DIR / "knowledge"
DUC_DTC = D / "ducati.json"
GEN_DTC = D / "generic.json"
ELEC = K / "known_issues_ducati_electrical.json"
DUCATI_FILES = [
    K / f"known_issues_ducati_{n}.json"
    for n in ("monster", "panigale", "multistrada", "desmo", "electrical")
]
COMPAT = SEED_DATA_DIR.parent.parent / "hardware" / "compat_data" / "compat_matrix.json"

STD_CODE = re.compile(r"^[PUBC][0-3][0-9A-F]{3}$")


@pytest.fixture
def dtc_db(tmp_path):
    path = str(tmp_path / "d.db")
    init_db(path)
    load_dtc_file(GEN_DTC, path)
    load_dtc_file(DUC_DTC, path)
    return path


@pytest.fixture
def codes():
    return json.loads(DUC_DTC.read_text(encoding="utf-8"))


@pytest.fixture
def issues():
    return json.loads(ELEC.read_text(encoding="utf-8"))


class TestNoFabricatedCodes:
    def test_every_code_is_standard_format(self, codes):
        for c in codes:
            assert STD_CODE.match(c["code"]), c["code"]

    def test_no_invented_manufacturer_range_code(self, codes):
        """P1xxx is manufacturer-defined; inventing one is forbidden."""
        for c in codes:
            assert not c["code"].startswith("P1"), c["code"]

    def test_no_duplicates_and_all_marked_ducati(self, codes):
        assert len({c["code"] for c in codes}) == len(codes)
        assert {c["make"] for c in codes} == {"Ducati"}

    def test_vocabularies_are_valid(self, codes):
        from motodiag.core.models import Severity, SymptomCategory

        cats = {e.value for e in SymptomCategory}
        sevs = {e.value for e in Severity}
        for c in codes:
            assert c["category"] in cats and c["severity"] in sevs, c["code"]

    def test_the_review_only_field_was_stripped(self, codes):
        """`why_shadow` justified each row during drafting; it is not
        part of the shipped record shape."""
        for c in codes:
            assert "why_shadow" not in c, c["code"]


class TestEveryRowEarnsItsShadow:
    """The Phase 215 finding: a make row that restates the generic one
    hides it."""

    def test_all_six_shadow_a_generic_row(self, codes):
        generic = {c["code"] for c in json.loads(GEN_DTC.read_text(encoding="utf-8"))}
        shadowed = [c["code"] for c in codes if c["code"] in generic]
        assert len(shadowed) == len(codes), "a row shadows nothing to compare against"

    def test_no_row_repeats_the_generic_causes_or_fix(self, codes):
        generic = {
            c["code"]: c for c in json.loads(GEN_DTC.read_text(encoding="utf-8"))
        }
        for c in codes:
            g = generic[c["code"]]
            assert c["common_causes"] != g.get("common_causes"), c["code"]
            assert c["fix_summary"] != g.get("fix_summary"), c["code"]

    def test_a_ducati_gets_the_ducati_row(self, dtc_db):
        rows = get_dtcs(["P0302"], make="Ducati", db_path=dtc_db)
        row = rows[0] if isinstance(rows, list) else list(rows.values())[0]
        assert row["make"] == "Ducati"

    def test_another_make_still_gets_generic(self, dtc_db):
        rows = get_dtcs(["P0302"], make="Honda", db_path=dtc_db)
        row = rows[0] if isinstance(rows, list) else list(rows.values())[0]
        assert row["make"] is None, "a Ducati row leaked onto a Honda"


class TestTheLTwinCylinderIdentity:
    """The single most useful thing a Ducati fault code can carry."""

    def test_both_misfire_rows_name_the_physical_cylinder(self, codes):
        by_code = {c["code"]: c for c in codes}
        assert "horizontal" in json.dumps(by_code["P0301"]).lower()
        assert "vertical" in json.dumps(by_code["P0302"]).lower()

    def test_the_mapping_never_contradicts_itself(self, codes):
        """Both rows restate the mapping — P0301's fix summary names both
        cylinders so the mechanic can orient. Every statement of it must
        agree: 1 is horizontal, 2 is vertical, everywhere it appears. A
        single reversed sentence is worse than saying nothing, because it
        is the sentence the mechanic acts on."""
        expected = {"1": "horizontal", "2": "vertical"}
        stated = re.findall(
            r"cylinder ([12]) is the ([A-Za-z]+)", json.dumps(codes), re.I
        )
        assert stated, "the mapping is never actually stated"
        for num, orientation in stated:
            assert orientation.lower() == expected[num], (
                f"cylinder {num} called {orientation!r}"
            )


class TestProprietaryCodesAreDescribedNotTranscribed:
    def test_the_read_access_problem_is_covered(self, issues):
        blob = json.dumps(issues).lower()
        assert "dds" in blob
        assert "elm327" in blob

    def test_prose_entries_cite_no_codes(self, issues):
        """The fault numbers live in the DTC table; these entries explain
        the format, and must not invent numbers of their own."""
        for e in issues:
            assert e["dtc_codes"] == [], e["title"]

    def test_no_proprietary_number_is_transcribed(self, issues):
        """A bare non-P-code fault number would be exactly the
        fabrication this phase refuses."""
        blob = json.dumps(issues)
        assert not re.search(r"\bfault (?:code )?\d{3,5}\b", blob, re.I)


class TestNothingWasDuplicated:
    def test_the_adapter_catalog_is_untouched(self):
        """Unlike Phase 215, where the GS-911 was genuinely missing, the
        Ducati adapter surface was already covered — eight compat rows
        including the OEM DDS."""
        matrix = json.loads(COMPAT.read_text(encoding="utf-8"))
        ducati = [r for r in matrix if r["make"] == "ducati"]
        assert len(ducati) == 8
        assert any(r["adapter_slug"] == "ducati-dds-readiness-tool" for r in ducati)

    def test_no_title_collides_across_the_five_ducati_files(self):
        titles = []
        for f in DUCATI_FILES:
            titles += [e["title"] for e in json.loads(f.read_text(encoding="utf-8"))]
        assert len(titles) == len(set(titles))

    def test_all_five_files_load_together(self, tmp_path):
        path = str(tmp_path / "duc.db")
        init_db(path)
        for f in DUCATI_FILES:
            load_known_issues_file(f, path)
        assert count_known_issues(db_path=path) == 41
        assert len(search_known_issues(make="Ducati", db_path=path)) == 41


class TestProvenanceAndSearchability:
    @pytest.fixture
    def issue_db(self, tmp_path):
        path = str(tmp_path / "e.db")
        init_db(path)
        load_known_issues_file(ELEC, path)
        return path

    def test_every_entry_is_tagged(self, issue_db, issues):
        rows = search_known_issues(make="Ducati", db_path=issue_db)
        assert {r["source"] for r in rows} == {"model-generated"}
        assert all(e.get("source") == "model-generated" for e in issues)

    def test_every_description_admits_its_origin(self, issues):
        for e in issues:
            assert "general knowledge" in e["description"].lower(), e["title"]

    def test_symptoms_are_short_phrases(self, issues):
        for e in issues:
            for s in e["symptoms"]:
                assert len(s) <= 55 and not s.endswith("."), f"{e['title']}: {s!r}"

    @pytest.mark.parametrize("needle", [
        "no codes found on a generic scanner",
        "runs worse after throttle body work",
        "immobiliser light on the dash",
    ])
    def test_a_mechanic_query_finds_the_entry(self, issue_db, needle):
        assert find_issues_by_symptom(needle, issue_db), needle
