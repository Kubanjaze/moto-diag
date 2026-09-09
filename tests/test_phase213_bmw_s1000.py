"""Phase 213 — BMW S1000RR / S1000R / S1000XR.

Six entries, not twelve. That is the finding, not a shortfall: 18 were
drafted and 12 were killed by the attribution refuter, every one of
them fatal, almost all for the same reason — a failure that is equally
true of a ZX-10R or an R1 adds nothing to a corpus that already covers
it four times over. Two whole lenses (RR 2015-2018, S1000R) produced no
survivor at all, so those generations are absent rather than invented.

The tests below therefore assert *specificity* as hard as they assert
the contract: no generic-superbike vocabulary standing alone as a
title, no fourth quickshifter entry, no foreign-platform hardware, and
no BMW fault codes (reserved for Phase 215).
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

S_FILE = SEED_DATA_DIR / "knowledge" / "known_issues_bmw_s1000.json"
R_FILE = SEED_DATA_DIR / "knowledge" / "known_issues_bmw_r_series.json"
F_FILE = SEED_DATA_DIR / "knowledge" / "known_issues_bmw_f_series_gs.json"

S_MODEL = re.compile(r"S1000RR|S1000R\b|S1000XR|HP4")

#: Hardware belonging to the boxer or the F-series. The S1000 is a
#: liquid-cooled inline four with a chain and a wet clutch; if any of
#: these appears, an entry has been ported across platforms — the exact
#: error Phase 212's attribution lens caught on the F-series file.
FOREIGN = [
    "paralever", "telelever", "final drive housing", "crown wheel",
    "dry clutch", "diode board", "rotax", "zfe", "boxer", "cardan",
]


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "s1000.db")
    init_db(path)
    load_known_issues_file(S_FILE, path)
    return path


@pytest.fixture
def raw():
    return json.loads(S_FILE.read_text(encoding="utf-8"))


class TestS1000Content:
    def test_loads_six(self, db_path):
        assert count_known_issues(db_path=db_path) == 6

    def test_all_are_bmw(self, db_path):
        assert len(search_known_issues(make="BMW", db_path=db_path)) == 6

    @pytest.mark.parametrize("year,minimum", [
        (2011, 2),   # K46
        (2016, 2),   # S1000XR first generation
        (2020, 2),   # ShiftCam
    ])
    def test_the_covered_generations_are_reachable(self, db_path, year, minimum):
        rows = search_known_issues(year=year, make="BMW", db_path=db_path)
        assert len(rows) >= minimum, f"{year}: {[r['title'] for r in rows]}"

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


class TestGenerationsAreNamedNotGuessed:
    """S1000RR spans five generations; ShiftCam exists only from 2019
    and the S1000XR vibration complaint belongs to 2015-2019, not the
    revised 2020 bike."""

    def test_every_model_string_names_a_specific_model(self, raw):
        for e in raw:
            assert S_MODEL.search(e["model"]), f"{e['title']}: {e['model']!r}"

    def test_no_entry_says_bare_s1000(self, raw):
        for e in raw:
            assert e["model"].strip().upper() not in {"S1000", "BMW S1000"}, e["title"]

    def test_shiftcam_is_never_attributed_before_2019(self, raw):
        for e in raw:
            if "shiftcam" in json.dumps(e).lower():
                assert e["year_start"] >= 2019, (
                    f"{e['title']}: ShiftCam on a {e['year_start']} bike"
                )

    def test_xr_vibration_stays_on_the_first_generation(self, raw):
        for e in raw:
            if "S1000XR" in e["model"] and "vibration" in e["title"].lower():
                assert e["year_end"] <= 2019, (
                    f"{e['title']}: claims the revised 2020+ XR still has it"
                )

    def test_years_are_ordered_and_plausible(self, raw):
        for e in raw:
            assert 2009 <= e["year_start"] <= e["year_end"] <= 2026, e["title"]


class TestNothingWasPortedFromAnotherPlatform:
    @pytest.mark.parametrize("term", FOREIGN)
    def test_no_foreign_component_appears(self, raw, term):
        for e in raw:
            assert term not in json.dumps(e).lower(), f"{e['title']}: {term!r}"

    def test_the_other_bmw_files_still_own_those_terms(self):
        """Proves the assertion above is meaningful rather than passing
        on an empty corpus."""
        assert "paralever" in R_FILE.read_text(encoding="utf-8").lower()
        assert "zfe" in F_FILE.read_text(encoding="utf-8").lower()


class TestEntriesAreS1000SpecificNotGenericSuperbike:
    """The failure mode this phase was most exposed to. Four litre-class
    peers are already in the corpus, so an entry that would read the
    same on any of them is a duplicate wearing a badge."""

    def test_no_fourth_quickshifter_entry(self, raw):
        """Shift Assist Pro is already covered for the F850GS, and
        quickshifters again on the CBR1000RR and in cross-platform
        drivetrain. The roadmap row named it; the audit said skip it."""
        for e in raw:
            t = e["title"].lower()
            assert "quickshift" not in t and "shift assist" not in t, e["title"]

    def test_no_bmw_fault_codes(self, raw):
        """Reserved for Phase 215."""
        for e in raw:
            assert e["dtc_codes"] == [], f"{e['title']}: {e['dtc_codes']}"

    def test_every_title_carries_a_bmw_specific_noun(self, raw):
        """Each surviving entry names BMW hardware or a BMW system —
        ShiftCam, Race ABS, DDC/Dynamic ESA — or an explicit model."""
        marks = ("shiftcam", "race abs", "ddc", "dynamic esa",
                 "s1000rr", "s1000xr", "s1000r", "k46")
        for e in raw:
            t = e["title"].lower()
            assert any(m in t for m in marks), e["title"]


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
    """Phase 212's drafters returned sentences and had to be corrected
    by hand. This phase put the rule in the schema; these tests are what
    keep it true."""

    def test_symptoms_are_short_phrases(self, raw):
        for e in raw:
            for s in e["symptoms"]:
                assert len(s) <= 55, f"{e['title']}: {s!r}"
                assert not s.endswith("."), f"{e['title']}: {s!r}"

    @pytest.mark.parametrize("needle,minimum", [
        ("rattle on cold start", 2),
        ("vibration through handlebars", 1),
        ("suspension warning light on dash", 1),
        ("flat top end power", 1),
    ])
    def test_a_mechanic_query_finds_the_entry(self, db_path, needle, minimum):
        assert len(find_issues_by_symptom(needle, db_path)) >= minimum


class TestAllThreeBmwFilesCoexist:
    def test_they_load_together(self, tmp_path):
        path = str(tmp_path / "all_bmw.db")
        init_db(path)
        for f in (R_FILE, F_FILE, S_FILE):
            load_known_issues_file(f, path)
        FILES = (R_FILE, F_FILE, S_FILE)
        # Phase 240B: was a hardcoded total. A count derived from the same
        # JSON the test loads survives corpus growth; a literal has to be
        # hand-edited by every later phase that adds an entry. The make
        # filter is a substring match (`make LIKE '%X%'`), so the
        # make-filtered number is counted the same way rather than assumed
        # equal to the file total -- they diverge the moment a compound or
        # cross-make entry lands in a make-prefixed file.
        entries = [e for f in FILES for e in json.loads(f.read_text(encoding="utf-8"))]
        assert count_known_issues(db_path=path) == len(entries)
        assert len(search_known_issues(make="BMW", db_path=path)) == sum(
            1 for e in entries if "bmw" in e["make"].lower()
        )

    def test_no_title_collides_across_the_bmw_files(self):
        titles = []
        for f in (R_FILE, F_FILE, S_FILE):
            titles += [e["title"] for e in json.loads(f.read_text(encoding="utf-8"))]
        assert len(titles) == len(set(titles))
