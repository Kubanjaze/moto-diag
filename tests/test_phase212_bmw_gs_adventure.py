"""Phase 212 — BMW F-series GS (chain-driven adventure line).

The roadmap row for this phase said "paralever final drive". It is
wrong: Paralever is the boxer/K-series shaft swingarm and no F-series
GS has ever had one — they are all chain-driven. Two independent
premise checkers reached that conclusion without seeing each other, and
it is the reason almost none of Phase 211's boxer topics could be
ported. Several assertions here exist specifically to stop R-series
hardware being relabelled onto an F.

The content was drafted by six independent lenses and each candidate
faced three refuters (attribution / invented figures / safety), each
defaulting to refuted when uncertain. 17 drafted, 14 survived, 12 kept.
That process is recorded in the phase log; what it cannot do is make
model-generated content true, which is why every entry is tagged and
these tests assert the tag.
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

F_FILE = SEED_DATA_DIR / "knowledge" / "known_issues_bmw_f_series_gs.json"
R_FILE = SEED_DATA_DIR / "knowledge" / "known_issues_bmw_r_series.json"

#: Every F/G model this phase may name. A model string matching none of
#: these means the entry is on an unidentified bike.
F_MODEL = re.compile(r"F650GS|F700GS|F750GS|F800GS|F850GS|F900GS|G650GS")

#: Hardware that exists only on the shaft-driven boxer. If any of these
#: appears in an F-series entry, a Phase 211 topic has been ported onto
#: a platform that does not have the part.
BOXER_ONLY = [
    "paralever", "telelever", "final drive housing", "crown wheel",
    "dry clutch", "diode board", "slip ring", "alternator belt",
    "input-shaft spline", "cardan",
]


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "fgs.db")
    init_db(path)
    load_known_issues_file(F_FILE, path)
    return path


@pytest.fixture
def raw():
    return json.loads(F_FILE.read_text(encoding="utf-8"))


class TestFSeriesContent:
    def test_loads_twelve(self, db_path):
        assert count_known_issues(db_path=db_path) == 12

    def test_all_are_bmw(self, db_path):
        assert len(search_known_issues(make="BMW", db_path=db_path)) == 12

    @pytest.mark.parametrize("year,minimum", [
        (2005, 2),   # Rotax 652 single era
        (2010, 5),   # 798cc twins
        (2015, 5),   # 798cc twins, late
        (2020, 3),   # 853cc F750/F850GS
    ])
    def test_generations_are_covered(self, db_path, year, minimum):
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


class TestNoBikeIsMisidentified:
    """The naming traps that would put an entry on the wrong machine:
    F650GS is a 652cc single AND a 798cc twin; F800GS is 798cc AND
    895cc; no twin's displacement matches its badge."""

    def test_every_model_string_names_a_specific_f_or_g_model(self, raw):
        for e in raw:
            assert F_MODEL.search(e["model"]), f"{e['title']}: {e['model']!r}"

    def test_no_entry_says_bare_gs(self, raw):
        for e in raw:
            assert e["model"].strip().upper() not in {"GS", "BMW GS"}, e["title"]

    def test_ambiguous_badges_carry_their_generation(self, raw):
        """F650GS and F800GS each name two unrelated bikes, so any entry
        using those badges must disambiguate by displacement or years."""
        for e in raw:
            m = e["model"]
            if "F650GS" in m or "F800GS" in m:
                assert re.search(r"\d{3}cc|\d{4}", m), (
                    f"{e['title']}: {m!r} does not say which generation"
                )

    def test_years_are_ordered_and_plausible(self, raw):
        for e in raw:
            assert 1993 <= e["year_start"] <= e["year_end"] <= 2026, e["title"]


class TestNoBoxerHardwareWasPortedOntoAChainBike:
    """The specific failure the roadmap row invited. The F-series has a
    chain, a wet clutch and a permanent-magnet generator; it has no
    Paralever, no final-drive housing, no dry clutch, no diode board."""

    @pytest.mark.parametrize("term", BOXER_ONLY)
    def test_no_r_series_only_component_appears(self, raw, term):
        for e in raw:
            blob = json.dumps(e).lower()
            assert term not in blob, f"{e['title']}: mentions {term!r}"

    def test_the_r_series_file_still_owns_paralever(self):
        """Proves the assertion above is meaningful — the term does
        exist in the corpus, just not on the F-series."""
        assert "paralever" in R_FILE.read_text(encoding="utf-8").lower()


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
    """Symptoms are matched with SQL LIKE, so a full sentence is
    effectively unsearchable. The drafters returned sentences; they were
    normalised to the short phrases the rest of the corpus uses."""

    def test_symptoms_are_short_phrases(self, raw):
        for e in raw:
            for s in e["symptoms"]:
                assert len(s) <= 55, f"{e['title']}: {s!r} is too long to match"

    def test_symptoms_are_not_sentences(self, raw):
        for e in raw:
            for s in e["symptoms"]:
                assert not s.endswith("."), f"{e['title']}: {s!r}"

    @pytest.mark.parametrize("needle,minimum", [
        ("steering notchy", 2),
        ("chain slap", 1),
        ("heated grips not working", 1),
        ("play at rear wheel", 1),
    ])
    def test_a_mechanic_query_finds_the_entry(self, db_path, needle, minimum):
        assert len(find_issues_by_symptom(needle, db_path)) >= minimum


class TestItCoexistsWithPhase211:
    def test_both_bmw_files_load_together(self, tmp_path):
        path = str(tmp_path / "both.db")
        init_db(path)
        load_known_issues_file(R_FILE, path)
        load_known_issues_file(F_FILE, path)
        FILES = (R_FILE, F_FILE)
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

    def test_the_widened_fuel_strip_entry_names_the_f800_family(self):
        """Phase 212's audit found the 211 fuel-strip entry was scoped
        to R1200GS although the same part fails the same way on the
        F800 family. It was widened rather than duplicated — so no
        F-series entry may re-tell it."""
        r = json.loads(R_FILE.read_text(encoding="utf-8"))
        strip = [e for e in r if "strip sensor" in e["title"].lower()]
        assert len(strip) == 1
        assert "F800" in strip[0]["model"]
        f_titles = " ".join(
            e["title"].lower()
            for e in json.loads(F_FILE.read_text(encoding="utf-8"))
        )
        assert "strip sensor" not in f_titles, "duplicated the widened entry"
