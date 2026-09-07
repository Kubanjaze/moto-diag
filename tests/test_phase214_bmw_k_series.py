"""Phase 214 — BMW K-series touring, where the attribution risk inverts.

Phases 212 and 213 policed misattribution: Paralever and shaft drive on
a chain-driven F-series or S1000 are hardware those bikes do not have.
The K-series genuinely IS shaft-driven with Paralever and genuinely did
carry servo Integral ABS, so those references are correct here — a
refuter briefed as before would have killed every valid entry.

What replaces that risk is duplication of the existing R-series file,
and getting the generation wrong. Duolever arrives with the transverse
K1200S in 2005; the longitudinal K1200RS/GT/LT are Telelever. Neither is
a telescopic fork, so fork-seal and stanchion diagnostics do not apply
to either — which is the single most useful thing this file adds, since
no entry anywhere in the corpus previously described either front end.

Note on the cross-mention tests below: these entries legitimately name
the *other* front end, and the boxer, in scope notes ("does NOT apply
to the 2006-onward transverse K1200GT, which uses Duolever"). That is
correct disambiguation, not misattribution, so the assertions check
what an entry CLAIMS about its own bike rather than which words appear.
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

K_FILE = SEED_DATA_DIR / "knowledge" / "known_issues_bmw_k_series.json"
R_FILE = SEED_DATA_DIR / "knowledge" / "known_issues_bmw_r_series.json"
F_FILE = SEED_DATA_DIR / "knowledge" / "known_issues_bmw_f_series_gs.json"
S_FILE = SEED_DATA_DIR / "knowledge" / "known_issues_bmw_s1000.json"
BMW_FILES = (R_FILE, F_FILE, S_FILE, K_FILE)

K_MODEL = re.compile(r"K7[05]|K100|K1100|K1200|K1300|K1600")
TRANSVERSE = re.compile(r"K1200S|K1200R\b|K1300|K1600")
LONGITUDINAL = re.compile(r"K7[05]|K100|K1100|K1200RS|K1200LT")

#: Terms with no legitimate reason to appear on a K-series entry, even
#: as a contrast. "boxer" is deliberately NOT here — these entries cite
#: it correctly to distinguish K driveshaft wear from boxer clutch-hub
#: spline wear.
FOREIGN = ["s1000", "rotax", "zfe", "shiftcam", "f800gs", "f650gs"]


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "k.db")
    init_db(path)
    load_known_issues_file(K_FILE, path)
    return path


@pytest.fixture
def raw():
    return json.loads(K_FILE.read_text(encoding="utf-8"))


class TestKSeriesContent:
    def test_loads_eleven(self, db_path):
        assert count_known_issues(db_path=db_path) == 11

    def test_all_are_bmw(self, db_path):
        assert len(search_known_issues(make="BMW", db_path=db_path)) == 11

    def test_every_entry_has_a_procedure_parts_and_hours(self, db_path):
        for row in search_known_issues(make="BMW", db_path=db_path):
            assert row["fix_procedure"].strip(), row["title"]
            parts = row["parts_needed"]
            if isinstance(parts, str):
                parts = json.loads(parts)
            assert parts, row["title"]
            assert row["estimated_hours"] > 0, row["title"]

    def test_severity_vocabulary(self, raw):
        assert {e["severity"] for e in raw} <= {"critical", "high", "medium", "low"}

    def test_no_bmw_fault_codes(self, raw):
        """Reserved for Phase 215."""
        for e in raw:
            assert e["dtc_codes"] == [], f"{e['title']}: {e['dtc_codes']}"


class TestTheFrontEndsAreOnTheRightBikes:
    """Duolever from the transverse K1200S (2005); Telelever on the
    longitudinal K1200RS/GT/LT. The roadmap row lists 'K1200RS ...
    Duolever front' as topics, and an entry that read it as one claim
    would be wrong."""

    def test_a_duolever_title_names_a_transverse_bike(self, raw):
        for e in raw:
            if "duolever" in e["title"].lower():
                assert TRANSVERSE.search(e["model"]), (
                    f"{e['title']}: Duolever claimed on {e['model']!r}"
                )

    def test_a_telelever_title_names_a_longitudinal_bike(self, raw):
        for e in raw:
            if "telelever" in e["title"].lower():
                assert LONGITUDINAL.search(e["model"]), (
                    f"{e['title']}: Telelever claimed on {e['model']!r}"
                )

    def test_both_front_ends_are_actually_covered(self, raw):
        """The corpus had no Duolever or Telelever entry before this
        phase — that gap was the phase's clearest justification."""
        titles = " ".join(e["title"].lower() for e in raw)
        assert "duolever" in titles
        assert "telelever" in titles

    def test_neither_front_end_is_described_as_having_forks(self, raw):
        """A Telelever/Duolever bike has no stanchions to pit and no
        fork seals to weep; treating one as a fork is the mistake these
        entries exist to prevent."""
        for e in raw:
            t = e["title"].lower()
            if "duolever" in t or "telelever" in t:
                assert "fork seal" not in t and "stanchion" not in t, e["title"]


class TestGenerationsAreDisambiguated:
    def test_every_model_names_a_specific_k(self, raw):
        for e in raw:
            assert K_MODEL.search(e["model"]), f"{e['title']}: {e['model']!r}"

    def test_no_entry_says_bare_k_series(self, raw):
        for e in raw:
            assert e["model"].strip().lower() not in {"k-series", "bmw k-series"}, e["title"]

    def test_the_ambiguous_k1200gt_badge_is_qualified(self, raw):
        """K1200GT names a longitudinal 2003-2005 bike and a transverse
        2006-2008 one."""
        for e in raw:
            if "K1200GT" in e["model"]:
                assert re.search(r"\d{4}|longitudinal|transverse", e["model"]), (
                    f"{e['title']}: {e['model']!r} does not say which K1200GT"
                )

    def test_years_are_ordered_and_plausible(self, raw):
        for e in raw:
            assert 1983 <= e["year_start"] <= e["year_end"] <= 2026, e["title"]


class TestNothingWasPortedFromAnotherBmwPlatform:
    @pytest.mark.parametrize("term", FOREIGN)
    def test_no_foreign_platform_term(self, raw, term):
        for e in raw:
            assert term not in json.dumps(e).lower(), f"{e['title']}: {term!r}"

    def test_the_other_bmw_files_still_own_those_terms(self):
        """Keeps the assertion above honest rather than vacuous."""
        assert "rotax" in F_FILE.read_text(encoding="utf-8").lower()
        assert "shiftcam" in S_FILE.read_text(encoding="utf-8").lower()

    def test_shared_hardware_is_referenced_but_not_restated(self, raw):
        """Paralever, shaft drive and Integral ABS are REAL K hardware,
        so mentioning them is correct — but the R-series entries that
        already cover them must not be duplicated here."""
        r_titles = {
            e["title"] for e in json.loads(R_FILE.read_text(encoding="utf-8"))
        }
        for e in raw:
            assert e["title"] not in r_titles, f"restates R-series: {e['title']}"
        k_titles = " ".join(e["title"].lower() for e in raw)
        assert "paralever pivot bearing wear" not in k_titles
        assert "integral abs" not in k_titles


class TestProvenanceIsRecorded:
    def test_every_entry_is_tagged_model_generated(self, db_path):
        rows = search_known_issues(make="BMW", db_path=db_path)
        assert {r["source"] for r in rows} == {"model-generated"}

    def test_the_tag_is_in_the_json_itself(self, raw):
        assert all(e.get("source") == "model-generated" for e in raw)

    def test_every_description_admits_its_origin(self, raw):
        for e in raw:
            assert "general knowledge" in e["description"].lower(), e["title"]


class TestSymptomsAreSearchable:
    def test_symptoms_are_short_phrases(self, raw):
        for e in raw:
            for s in e["symptoms"]:
                assert len(s) <= 55, f"{e['title']}: {s!r}"
                assert not s.endswith("."), f"{e['title']}: {s!r}"

    @pytest.mark.parametrize("needle,minimum", [
        ("knocking from front end", 2),
        ("vague steering at speed", 2),
        ("telelever ball joint play", 1),
        ("clutch slips under hard acceleration", 1),
        ("driveline lash from rear", 1),
    ])
    def test_a_mechanic_query_finds_the_entry(self, db_path, needle, minimum):
        """Needles taken from the shipped data, not invented — the first
        draft of this test guessed three phrases and all three missed."""
        assert len(find_issues_by_symptom(needle, db_path)) >= minimum, needle


class TestAllFourBmwFilesCoexist:
    def test_they_load_together(self, tmp_path):
        path = str(tmp_path / "all_bmw.db")
        init_db(path)
        for f in BMW_FILES:
            load_known_issues_file(f, path)
        assert count_known_issues(db_path=path) == 41
        assert len(search_known_issues(make="BMW", db_path=path)) == 41

    def test_no_title_collides_across_the_bmw_files(self):
        titles = []
        for f in BMW_FILES:
            titles += [e["title"] for e in json.loads(f.read_text(encoding="utf-8"))]
        assert len(titles) == len(set(titles))
