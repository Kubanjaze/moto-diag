"""Phase 219 — Ducati desmodromic valve service.

The service that Phases 216, 217 and 218 all deferred here, and a
**procedure** phase rather than a failure phase.

**The roadmap row named the wrong mechanism.** It read "shim-over-bucket
opener/closer". Desmodromic valve gear has two rocker arms per valve —
opening and closing — and two shims: a small one on the valve stem
setting the opening clearance, and a large one wrapping the stem and
retaining the collets, setting the closing clearance. **There are no
buckets.** "Shim-over-bucket" describes a spring-valve design, which is
what the corpus's other 22 valve entries cover. The row is corrected.

That contrast is also this phase's justification: 22 spring-valve
clearance entries exist across four Japanese makes, several of them
explicitly "shim-under-bucket", and none describes a desmodromic system.
So the assertions here run the opposite way to Phase 213's — the danger
is writing a *generic valve-clearance* entry, and every entry must name
desmodromic hardware.

**Negation is checked in both directions, and named systems are
exempt.** "There is no bucket" negates before the term; "the Granturismo
is not [desmodromic]" negates after it; and "shim-under-bucket" is a
proper name for the contrasting design, not a claim this engine has one.
All three tripped a first-pass validator — the fourth consecutive phase
where my own check, not the content, was at fault.
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
DESMO_FILE = K / "known_issues_ducati_desmo.json"
DUCATI_FILES = [
    K / f"known_issues_ducati_{n}.json"
    for n in ("monster", "panigale", "multistrada", "desmo")
]

NEGATION = re.compile(
    r"\bno\b|\bnot\b|neither|unlike|never|rather than|instead of|without|does not|nor ",
    re.I,
)
#: A proper name for the contrasting spring-valve design. Its appearance
#: is a reference, never a claim that this engine has a bucket.
NAMED_SYSTEM = re.compile(r"shim[- ]?(under|over)[- ]?bucket", re.I)

#: Hardware that must appear, or the entry is a generic valve-clearance
#: entry wearing a Ducati badge — and the corpus has 22 of those.
DESMO_HARDWARE = ("opening rocker", "closing rocker", "opening shim",
                  "closing shim", "collet", "half-ring", "half ring", "desmo")


def _claims(e: dict) -> str:
    return " ".join([e["title"], e["description"], e["fix_procedure"]] + e["causes"])


def _asserts(text: str, term: str, window: int = 90) -> bool:
    """A positive claim about this engine. Negation may precede OR follow
    the term, and a named-system compound is not a claim at all."""
    for m in re.finditer(re.escape(term), text, re.I):
        if NAMED_SYSTEM.search(text[max(0, m.start() - 14):m.start() + 14]):
            continue
        before = text[max(0, m.start() - window):m.start()]
        after = text[m.end():m.end() + window]
        if not (NEGATION.search(before) or NEGATION.search(after)):
            return True
    return False


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "desmo.db")
    init_db(path)
    load_known_issues_file(DESMO_FILE, path)
    return path


@pytest.fixture
def raw():
    return json.loads(DESMO_FILE.read_text(encoding="utf-8"))


class TestContent:
    def test_loads_six(self, db_path):
        assert count_known_issues(db_path=db_path) == 6

    def test_all_are_ducati(self, raw):
        assert {e["make"] for e in raw} == {"Ducati"}

    def test_severity_years_procedures(self, raw):
        for e in raw:
            assert e["severity"] in {"critical", "high", "medium", "low"}
            assert 1993 <= e["year_start"] <= e["year_end"] <= 2026, e["title"]
            assert e["fix_procedure"].strip() and e["estimated_hours"] > 0, e["title"]
            assert e["parts_needed"], e["title"]

    def test_the_collet_step_is_rated_critical(self, raw):
        """A released collet drops a valve into a running engine. If any
        entry in this file is critical it is that one."""
        collet = [e for e in raw if "collet" in e["title"].lower()]
        assert collet and any(e["severity"] == "critical" for e in collet)


class TestTheMechanismIsDescribedCorrectly:
    def test_no_entry_claims_this_engine_has_a_bucket(self, raw):
        for e in raw:
            assert not _asserts(_claims(e), "bucket"), (
                f"{e['title']}: claims a bucket on a desmodromic engine"
            )

    def test_the_contrasting_system_may_still_be_named(self, raw):
        """"shim-under-bucket" is how you refer to the design a mechanic
        is coming from. Naming it is the point of several entries."""
        assert NAMED_SYSTEM.search(json.dumps(raw))

    def test_both_rockers_and_both_shims_are_covered(self, raw):
        blob = json.dumps(raw).lower()
        for term in ("opening rocker", "closing rocker",
                     "opening clearance", "closing clearance"):
            assert term in blob, f"{term} never described"

    def test_the_spring_valve_files_still_own_buckets(self):
        """Counter-assertion — the term is real in this corpus, just on
        engines that have them."""
        zx6r = (K / "known_issues_kawasaki_zx6r.json").read_text(encoding="utf-8")
        assert "bucket" in zx6r.lower()


class TestScopeAndExclusions:
    def test_the_granturismo_is_excluded(self, raw):
        """Phase 218 established the Multistrada V4 has spring valves."""
        blob = json.dumps(raw)
        assert "Granturismo" in blob, "the exclusion is not stated"
        for e in raw:
            assert not _asserts(_claims(e), "Granturismo"), (
                f"{e['title']}: treats the Granturismo as desmodromic"
            )

    def test_every_entry_names_desmodromic_hardware(self, raw):
        """The reverse of Phase 213's genericness test: with 22
        spring-valve entries in the corpus, an entry that does not name
        desmo hardware is one of those with a Ducati badge."""
        for e in raw:
            blob = _claims(e).lower()
            assert any(h in blob for h in DESMO_HARDWARE), e["title"]

    def test_no_cam_belt_procedure_is_rewritten(self, raw):
        """Belts belong to 216 and 218. Referring to the scheduling
        overlap is allowed; re-teaching the belt job is not."""
        for e in raw:
            assert "belt" not in e["title"].lower(), e["title"]

    def test_no_fault_codes_or_tool_content(self, raw):
        blob = json.dumps(raw).lower()
        for e in raw:
            assert e["dtc_codes"] == [], e["title"]
        for term in ("marelli", "dda+", "dds tool"):
            assert term not in blob, term


class TestIntervalsAreDeferredNotQuoted:
    """A wrong interval becomes a wrong quote, which is the specific
    harm this phase is about."""

    def test_no_entry_states_a_mileage_interval_as_fact(self, raw):
        for e in raw:
            claims = _claims(e)
            hits = re.findall(r"\b\d{1,3},?\d{3}\s*(?:mi|mile|miles|km)\b", claims, re.I)
            assert not hits, f"{e['title']}: states an interval figure {hits}"

    def test_the_interval_entry_defers_to_the_manual(self, raw):
        interval = [e for e in raw if "interval" in e["title"].lower()]
        assert interval, "no interval entry"
        for e in interval:
            assert "manual" in _claims(e).lower(), e["title"]


class TestProvenanceAndSearchability:
    def test_every_entry_is_tagged(self, db_path, raw):
        rows = search_known_issues(make="Ducati", db_path=db_path)
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
        "two shims per valve",
        "collet not seating correctly",
        "bike stuck waiting on shims",
    ])
    def test_a_mechanic_query_finds_the_entry(self, db_path, needle):
        assert find_issues_by_symptom(needle, db_path), needle


class TestAllFourDucatiFilesCoexist:
    def test_they_load_together(self, tmp_path):
        path = str(tmp_path / "duc.db")
        init_db(path)
        for f in DUCATI_FILES:
            load_known_issues_file(f, path)
        assert count_known_issues(db_path=path) == 36
        assert len(search_known_issues(make="Ducati", db_path=path)) == 36

    def test_no_title_collides(self):
        titles = []
        for f in DUCATI_FILES:
            titles += [e["title"] for e in json.loads(f.read_text(encoding="utf-8"))]
        assert len(titles) == len(set(titles))
