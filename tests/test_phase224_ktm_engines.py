"""Phase 224 — KTM engine families (LC8 / LC8c / LC4).

**The row's stated content was already written, and this file does not
write it again.** Row 224 reserved cam chain tensioner, electric start
and valve clearance for the LC8. Across 762 entries those topics appear
in 37, 23 and 26 entries, and the procedures already exist in generic
form — starter work in `cross_platform_starting`, cam chain tensioner and
valve clearance in the Honda and Yamaha cross-model files with
`model: "All"`. A KTM cam chain tensioner entry would be the
thirty-eighth. The first assertion in this file is that no such entry
exists here.

**Not knowing is a result.** Honda's cross-model entry can call the
inline-four tensioner a documented make-wide weakness because it is. I
have no equivalent confident knowledge of an LC8-specific tensioner,
starter or valve failure pattern, and inventing one would be fabrication
in the costume of specificity. The absence is asserted, not just
intended.

**What the file does carry** is what only KTM's cross-engine file can:
three architectures under two prefixes, generation span within the LC8,
cylinder identification on a vee (without asserting a numbering I cannot
support), and routing for the three universal topics.

**The scope decision from Phase 222 is settled here**: row 224 widened
from "LC8 V-twin" to the KTM engine families, so the LC8c has a home.
"""

from __future__ import annotations

import json
import re

import pytest

from motodiag.core.config import SEED_DATA_DIR
from motodiag.core.database import init_db
from motodiag.knowledge.issues_repo import (
    count_known_issues,
    find_issues_by_symptom,
    search_known_issues,
)
from motodiag.knowledge.loader import load_known_issues_file

K = SEED_DATA_DIR / "knowledge"
ENGINES_FILE = K / "known_issues_ktm_engines.json"
KTM_FILES = sorted(K.glob("known_issues_ktm_*.json"))

PREFIXES = {"LC8": r"\bLC8\b(?!c)", "LC8c": r"\bLC8c\b", "LC4": r"\bLC4\b"}

#: A make-specific failure claim about one of the three reserved topics.
#: This is the sentence that must not appear.
FAILURE_CLAIM = re.compile(
    r"(LC8c?|LC4|KTM)[^.]{0,60}"
    r"(cam chain tensioner|starter clutch|sprag|valve clearance)[^.]{0,60}"
    r"(weak|fail|known|common|prone|issue|problem)",
    re.I,
)


def _claims(e: dict) -> str:
    return " ".join([e["title"], e["description"], e["fix_procedure"]] + e["causes"])


def _load(name: str) -> list[dict]:
    return json.loads((K / name).read_text(encoding="utf-8"))


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "engines.db")
    init_db(path)
    load_known_issues_file(ENGINES_FILE, path)
    return path


@pytest.fixture
def raw():
    return json.loads(ENGINES_FILE.read_text(encoding="utf-8"))


class TestTheReservedTopicsAreNotRetold:
    """The phase's governing decision."""

    def test_no_entry_claims_a_ktm_specific_failure_pattern(self, raw):
        for e in raw:
            hit = FAILURE_CLAIM.search(_claims(e))
            assert not hit, f"{e['title']}: {hit.group()[:90]!r}"

    def test_no_entry_is_about_one_of_the_three_topics(self, raw):
        """An entry may route to them; it may not be one of them. The
        routing entry names all three in its title and is the only
        entry allowed to."""
        topical = [
            e for e in raw
            if re.search(r"cam chain tensioner|starter clutch|valve clearance",
                         e["title"], re.I)
        ]
        assert len(topical) == 1, [e["title"] for e in topical]
        assert "diagnosed like any engine" in topical[0]["title"]

    def test_the_routing_points_at_entries_that_exist(self):
        """Counter-assertion: the routing entry says the procedures
        already exist, so they had better."""
        starting = [e["title"].lower() for e in _load("known_issues_cross_platform_starting.json")]
        assert any("starter clutch" in t for t in starting)
        assert any("starter relay" in t for t in starting)
        assert any("starter motor" in t for t in starting)
        cross_model = [
            e["title"].lower()
            for f in ("known_issues_honda_cross_model.json", "known_issues_yamaha_crossmodel.json")
            for e in _load(f)
        ]
        assert any("cam chain tensioner" in t for t in cross_model)
        assert any("valve clearance" in t for t in cross_model)

    def test_the_routing_entry_describes_where_they_live_accurately(self, raw):
        """The first draft said all three were cross-platform. Only the
        starter procedures are; the other two are in make-scoped
        cross-model files. The entry must not overstate the corpus."""
        routing = [e for e in raw if "diagnosed like any engine" in e["title"]][0]
        text = _claims(routing).lower()
        assert "cross-platform" in text
        assert "cross-model" in text, "does not distinguish cross-model from cross-platform"


class TestContent:
    def test_loads_four(self, db_path):
        assert count_known_issues(db_path=db_path) == 4

    def test_all_are_ktm(self, raw, db_path):
        assert {e["make"] for e in raw} == {"KTM"}
        assert len(search_known_issues(make="KTM", db_path=db_path)) == 4

    def test_severity_years_procedures(self, raw):
        for e in raw:
            assert e["severity"] in {"critical", "high", "medium", "low"}
            assert 2003 <= e["year_start"] <= e["year_end"] <= 2026, e["title"]
            assert e["fix_procedure"].strip() and e["estimated_hours"] > 0, e["title"]
            assert e["parts_needed"], e["title"]


class TestThisIsTheCrossEngineFile:
    def test_every_entry_names_a_prefix_in_title_and_body(self, raw):
        for e in raw:
            assert [n for n, p in PREFIXES.items() if re.search(p, e["title"])], (
                f"{e['title']}: title names no prefix"
            )
            assert [n for n, p in PREFIXES.items() if re.search(p, _claims(e))], (
                f"{e['title']}: body names no prefix"
            )

    def test_all_three_architectures_are_mapped(self, raw):
        blob = json.dumps(raw)
        assert re.search(r"LC8\b(?!c)[^.]{0,40}V-twin", blob)
        assert re.search(r"LC8c[^.]{0,40}parallel twin", blob)
        assert re.search(r"LC4[^.]{0,40}single", blob)

    def test_a_cross_platform_entry_names_no_ktm_prefix(self):
        """Counter-assertion: the prefix bar separates this file from
        the generic entries it routes to."""
        blob = json.dumps(_load("known_issues_cross_platform_starting.json"))
        assert not [n for n, p in PREFIXES.items() if re.search(p, blob)]


class TestNothingIsAssertedThatICannotSupport:
    def test_no_cylinder_numbering_is_stated(self, raw):
        """The cylinder entry says front and rear and sends the reader
        to the manual for which is which. It does not guess."""
        cyl = [e for e in raw if "cylinders are front and rear" in e["title"]]
        assert cyl, "no cylinder-identification entry"
        text = _claims(cyl[0])
        assert not re.search(r"cylinder (1|2|one|two|number one)\b", text, re.I), (
            "asserts a numbering"
        )
        assert "documentation" in text.lower() or "manual" in text.lower()

    def test_the_generation_entry_lists_the_span_without_inventing_years(self, raw):
        gen = [e for e in raw if "generation matters" in e["title"]][0]
        text = _claims(gen)
        for d in ("950", "990", "1050", "1090", "1190", "1290"):
            assert d in text, f"{d} missing from the span"
        # No per-generation model-year claims — those belong to a VIN lookup.
        assert not re.search(r"\b(19|20)\d{2}\s*[-–]\s*(19|20)\d{2}\b", text)


class TestBoundariesWithTheRestOfTheBlock:
    def test_the_222_architecture_point_is_not_restated_as_an_entry(self, raw):
        """222 wrote 'the LC8c is a parallel twin, not a V-twin — the
        name is the trap'. The family map here may state the fact; no
        entry here may have that trap as its subject."""
        for e in raw:
            assert "not a V-twin" not in e["title"], e["title"]
            assert "the name is the trap" not in e["title"], e["title"]

    def test_no_symptom_resolves_to_two_ktm_files(self, raw):
        """The real duplication test: if the same mechanic query finds
        an entry in this file and in a sibling, one of them is a
        re-telling."""
        mine = {s for e in raw for s in e["symptoms"]}
        for f in KTM_FILES:
            if f == ENGINES_FILE:
                continue
            theirs = {s for e in json.loads(f.read_text(encoding="utf-8")) for s in e["symptoms"]}
            assert not (mine & theirs), f"{f.name}: {mine & theirs}"

    def test_no_phase_225_ecu_or_tuning_content(self, raw):
        forbidden = r"\bECU\b|Keihin|TuneECU|Tuneboy|remap|reflash|\bP0\d{3}\b"
        for e in raw:
            hits = re.findall(forbidden, _claims(e), re.I)
            assert not hits, f"{e['title']}: {hits} belongs to Phase 225"

    def test_no_fault_codes(self, raw):
        for e in raw:
            assert e["dtc_codes"] == [], e["title"]


class TestTheKtmFilesCoexist:
    def test_they_load_together(self, tmp_path):
        """The invariant, not a constant (the Phase 223 lesson)."""
        path = str(tmp_path / "ktm.db")
        init_db(path)
        expected = 0
        for f in KTM_FILES:
            load_known_issues_file(f, path)
            expected += len(json.loads(f.read_text(encoding="utf-8")))
        assert count_known_issues(db_path=path) == expected
        assert len(search_known_issues(make="KTM", db_path=path)) == expected
        assert len(json.loads(ENGINES_FILE.read_text(encoding="utf-8"))) == 4

    def test_no_title_collides(self):
        titles = []
        for f in KTM_FILES:
            titles += [e["title"] for e in json.loads(f.read_text(encoding="utf-8"))]
        assert len(titles) == len(set(titles))


class TestProvenanceAndSearchability:
    def test_every_entry_is_tagged(self, db_path, raw):
        rows = search_known_issues(make="KTM", db_path=db_path)
        assert {r["source"] for r in rows} == {"model-generated"}
        assert all(e.get("source") == "model-generated" for e in raw)

    def test_every_description_admits_its_origin(self, raw):
        for e in raw:
            assert "general knowledge" in e["description"].lower(), e["title"]

    def test_symptoms_are_short_phrases(self, raw):
        for e in raw:
            for s in e["symptoms"]:
                assert len(s) <= 55 and not s.endswith("."), f"{e['title']}: {s!r}"

    @pytest.mark.parametrize("needle", [
        "unsure which ktm engine family this is",
        "lc8 part does not fit this generation",
        "worked on the wrong cylinder",
        "starter spins but engine does not turn",
    ])
    def test_a_mechanic_query_finds_the_entry(self, db_path, needle):
        assert find_issues_by_symptom(needle, db_path), needle
