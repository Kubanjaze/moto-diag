"""Phase 221 — KTM 1290 Super Duke / Super Adventure. Opens the KTM block.

**The hazard here is duplication, not fabrication.** KTM had zero entries
before this phase, but the *topic* is the most-covered one in the corpus:
19 rider-electronics entries already exist across nine makes — "cornering
ABS / TC false intervention" on the RevMax, "electronics suite
complexity" on the H2, R1, MT-10 and R6, IMU and sensor calibration on
the ZX-10R, ZX-6R, GSX-R1000, Z900 and ZX-14R. The RevMax entry is
already the generic form of what a KTM cornering-ABS entry would say.

So the genericness test runs **backwards**, as in Phase 219: an entry
must **name** 1290 hardware or nomenclature rather than merely avoid a
shared topic. The counter-assertion is what makes that test mean
something — the RevMax entry is run through the same check and must
**fail** it. A rule that only ever passes proves nothing.

The threshold is distinct terms, not occurrences, so it cannot be
satisfied by repeating "KTM". It was set after the first draft failed it:
five of seven entries scored one distinct term, from the title alone.
Four candidates were cut for genericness and two were rewritten with real
KTM anchoring. The tyre-circumference entry was cut outright — its
mechanism is universal, and a make file is the wrong home for it.

**The adapter catalog is left alone for the opposite reason to Phase
220.** There the Ducati surface was already covered. Here there is a
genuine gap — four KTM rows, every one partial or read-only, no
full-access option — but Phase 225 owns KTM tooling by roadmap row, so
filling it here would pre-empt that phase. The row count is guarded so
the decision is on the record either way.
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
KTM_FILE = K / "known_issues_ktm_1290.json"
COMPAT = SEED_DATA_DIR.parent.parent / "hardware" / "compat_data" / "compat_matrix.json"

#: Hardware and nomenclature only a 1290 entry can name. Matched as
#: DISTINCT terms, so sprinkling one word cannot satisfy the threshold.
SPECIFIC = {
    "MSC": r"\bMSC\b",
    "MTC": r"\bMTC\b",
    "LC8": r"\bLC8\b",
    "Super Duke": r"Super Duke",
    "Super Adventure": r"Super Adventure",
    "1290": r"\b1290\b",
    "KTM": r"\bKTM\b",
    "Bosch": r"\bBosch\b",
    "21-inch": r"21[- ]inch",
    "19-inch": r"19[- ]inch",
}

NEGATION = re.compile(
    r"\bno\b|\bnot\b|neither|unlike|never|rather than|instead of|without|does not|nor ",
    re.I,
)
#: Reported speech. "If a customer says Super Adventure GT" quotes
#: someone else's error; it does not assert the bike exists. Phase 218
#: handled this by treating symptoms as reports, but a report can sit
#: inside an assertion-bearing field too — a fix procedure telling a
#: mechanic what a customer will say is the obvious case.
REPORTED = re.compile(
    r"(says|said|saying|calls? it|called|asks? for|asked for|requests?|"
    r"describ\w+ as|listed as|advertised as|told you|hears?)\s*$",
    re.I,
)


def _claims(e: dict) -> str:
    """Assertion-bearing fields only. Symptoms are reports of what
    someone said, not claims the corpus makes (the Phase 218 lesson)."""
    return " ".join([e["title"], e["description"], e["fix_procedure"]] + e["causes"])


def _distinct_terms(e: dict) -> list[str]:
    text = _claims(e)
    return [n for n, p in SPECIFIC.items() if re.search(p, text, re.I)]


def _asserts(text: str, term: str, window: int = 90) -> bool:
    """A positive claim the corpus makes about the world.

    Negation may precede OR follow the term (the Phase 219 lesson), and
    a term introduced by a speech verb is a quotation of someone else
    rather than a claim (the case this phase found)."""
    for m in re.finditer(term, text, re.I):
        before = text[max(0, m.start() - window):m.start()]
        after = text[m.end():m.end() + window]
        if REPORTED.search(before[-30:]):
            continue
        if not (NEGATION.search(before) or NEGATION.search(after)):
            return True
    return False


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "ktm.db")
    init_db(path)
    load_known_issues_file(KTM_FILE, path)
    return path


@pytest.fixture
def raw():
    return json.loads(KTM_FILE.read_text(encoding="utf-8"))


class TestContent:
    def test_loads_six(self, db_path):
        assert count_known_issues(db_path=db_path) == 6

    def test_all_are_ktm(self, raw, db_path):
        assert {e["make"] for e in raw} == {"KTM"}
        assert len(search_known_issues(make="KTM", db_path=db_path)) == 6

    def test_this_file_still_owns_its_titles(self):
        """This phase opened the KTM block, and the first version of
        this test asserted that by requiring no sibling KTM file to
        exist. That was the wrong encoding of a true fact: it made the
        guard fail the moment the block grew, which Phase 222 duly did.
        A guard should outlive the deliverable it was written for
        (Phase 220's finding), so it now asserts what was meant — the
        1290 file keeps its own entries and does not collide with a
        sibling's titles."""
        mine = {e["title"] for e in json.loads(KTM_FILE.read_text(encoding="utf-8"))}
        assert len(mine) == 6
        for sibling in K.glob("known_issues_ktm_*.json"):
            if sibling.name == KTM_FILE.name:
                continue
            theirs = {
                e["title"] for e in json.loads(sibling.read_text(encoding="utf-8"))
            }
            assert not (mine & theirs), f"{sibling.name} collides: {mine & theirs}"

    def test_severity_years_procedures(self, raw):
        for e in raw:
            assert e["severity"] in {"critical", "high", "medium", "low"}
            assert 2014 <= e["year_start"] <= e["year_end"] <= 2026, e["title"]
            assert e["fix_procedure"].strip() and e["estimated_hours"] > 0, e["title"]
            assert e["parts_needed"], e["title"]

    def test_the_quiet_post_drop_failure_is_the_serious_one(self, raw):
        """If any entry here rates high it is the one where the bike
        rides away with the lean-sensitive functions inactive."""
        drop = [e for e in raw if "after a drop" in e["title"].lower()]
        assert drop and drop[0]["severity"] == "high"


class TestTheGenericnessTestRunsBackwards:
    """19 rider-electronics entries already exist. Avoiding their topic
    is not enough — an entry must name 1290 hardware."""

    def test_every_entry_names_at_least_three_distinct_1290_terms(self, raw):
        for e in raw:
            terms = _distinct_terms(e)
            assert len(terms) >= 3, f"{e['title']}: only names {terms}"

    def test_the_generic_corpus_entry_fails_this_same_check(self):
        """The counter-assertion. Without it the rule proves nothing —
        the RevMax entry is the generic form of a cornering-ABS entry,
        and it must score zero against a test for 1290 specificity."""
        revmax = json.loads(
            (K / "known_issues_harley_revmax.json").read_text(encoding="utf-8")
        )
        generic = [
            e for e in revmax if e["title"].startswith("Cornering ABS / traction")
        ]
        assert generic, "the generic entry this file is measured against is gone"
        assert _distinct_terms(generic[0]) == []

    def test_the_threshold_counts_distinct_terms_not_repetition(self, raw):
        """Guard on the guard: an entry saying "KTM" eight times names
        one thing. Every entry must clear the bar on variety."""
        for e in raw:
            assert len(set(_distinct_terms(e))) == len(_distinct_terms(e))

    def test_msc_is_described_as_a_supplier_system(self, raw):
        """The single fact that separates this file from the Japanese
        electronics entries: MSC is Bosch, not KTM in-house."""
        bosch = [e for e in raw if _asserts(_claims(e), r"\bBosch\b")]
        assert bosch, "no entry states MSC is a Bosch system"
        blob = json.dumps(bosch).lower()
        assert "in-house" in blob, "the contrast with in-house systems is not drawn"

    def test_no_entry_restates_the_generic_intervention_causes(self):
        """The RevMax entry's causes are IMU sensitivity, wheel speed
        contamination and cold tires. Reproducing that list verbatim in
        KTM colours is the failure this phase is guarding against."""
        revmax = json.loads(
            (K / "known_issues_harley_revmax.json").read_text(encoding="utf-8")
        )
        generic_causes = {
            c.lower()
            for e in revmax
            if e["title"].startswith("Cornering ABS / traction")
            for c in e["causes"]
        }
        for e in json.loads(KTM_FILE.read_text(encoding="utf-8")):
            overlap = generic_causes & {c.lower() for c in e["causes"]}
            assert not overlap, f"{e['title']}: repeats {overlap}"


class TestVariantsAreNamedCorrectly:
    """Variant claims are parts claims — getting S versus R wrong sends
    someone to the wrong wheel size."""

    def test_there_is_no_super_adventure_gt(self, raw):
        """The roadmap row said "R/GT variants" while naming both model
        lines. GT is a Super Duke designation; the Super Adventure has
        never had one. Naming the error is allowed; asserting the bike
        exists is not."""
        for e in raw:
            assert not _asserts(_claims(e), r"Super Adventure GT"), e["title"]

    def test_the_conflation_is_called_out_rather_than_silently_avoided(self, raw):
        """A mechanic hearing "Super Adventure GT" from a customer needs
        to be told what it actually is."""
        blob = json.dumps(raw)
        assert "Super Adventure GT" in blob, "the error is never addressed"

    def test_both_lines_variants_are_stated(self, raw):
        blob = json.dumps(raw)
        for token in ("Super Duke R", "Super Duke GT", "Super Adventure S",
                      "Super Adventure R"):
            assert token in blob, f"{token} never named"

    def test_the_front_wheel_split_is_stated(self, raw):
        """21-inch front means the R, 19-inch means the S — the split
        that costs money when a wheel is ordered."""
        variant = [e for e in raw if "Which 1290" in e["title"]]
        assert variant
        text = _claims(variant[0])
        assert re.search(r"19[- ]inch", text, re.I)
        assert re.search(r"21[- ]inch", text, re.I)


class TestDeferralBoundaries:
    """224 owns LC8 failures, 225 the ECU and tooling, 222/223 the other
    model lines. This phase writes none of them."""

    def test_no_phase_224_engine_content(self, raw):
        forbidden = r"cam chain tensioner|electric start|starter (motor|clutch|sprag)|valve clearance|valve service"
        for e in raw:
            hits = re.findall(forbidden, _claims(e), re.I)
            assert not hits, f"{e['title']}: {hits} belongs to Phase 224"

    def test_no_phase_225_ecu_or_tuning_content(self, raw):
        forbidden = r"\bECU\b|Keihin|TuneECU|Tuneboy|remap|reflash|\bP0\d{3}\b"
        for e in raw:
            hits = re.findall(forbidden, _claims(e), re.I)
            assert not hits, f"{e['title']}: {hits} belongs to Phase 225"

    def test_no_fault_codes(self, raw):
        for e in raw:
            assert e["dtc_codes"] == [], e["title"]

    def test_no_other_ktm_model_lines(self, raw):
        """222 owns the Duke line, 223 the enduro singles."""
        forbidden = r"\b(125|390|690|790|890|450|500)\b"
        for e in raw:
            hits = re.findall(forbidden, _claims(e))
            assert not hits, f"{e['title']}: {hits} belongs to Phase 222/223"


class TestTheAdapterGapWasLeftForItsOwnerAndThenFilled:
    """Phase 221 found four KTM compat rows, every one partial or
    read-only, and no full-access option — a real gap of the kind Phase
    215 filled for BMW. It declined to fill it because row 225 owned KTM
    tooling, and guarded the count at 4 so the decision was on record.

    Phase 225 then filled it, with TuneECU and provenance in every row.
    So this guard's job changed: it now asserts that the four original
    rows survived untouched (225 added, it did not rewrite), and that
    the gap is closed — the inverse of what it asserted before. A guard
    should outlive the deliverable it was written for; here it outlived
    the *absence* it was written for."""

    ORIGINAL = {
        ("obdlink-mx-plus", "1290%", "partial"),
        ("autel-ap200bt", "690%", "read-only"),
        ("autel-ap200bt", "390%", "read-only"),
        ("els27-forscan", "1290%", "read-only"),
    }

    def test_the_four_original_rows_are_still_there_unchanged(self):
        matrix = json.loads(COMPAT.read_text(encoding="utf-8"))
        ktm = {(r["adapter_slug"], r["model_pattern"], r["status"])
               for r in matrix if r["make"] == "ktm"}
        assert self.ORIGINAL <= ktm, self.ORIGINAL - ktm

    def test_the_gap_is_now_closed(self):
        """Inverted from Phase 221's `all(status != "full")`. If this
        fails, someone removed the full-access rows Phase 225 added."""
        matrix = json.loads(COMPAT.read_text(encoding="utf-8"))
        ktm = [r for r in matrix if r["make"] == "ktm"]
        assert len(ktm) > 4
        assert any(r["status"] == "full" for r in ktm), "no full-access KTM option"

    def test_the_makes_it_is_measured_against_still_have_theirs(self):
        """Counter-assertion: the comparison that defined the gap."""
        matrix = json.loads(COMPAT.read_text(encoding="utf-8"))
        for make in ("bmw", "ducati"):
            assert any(
                r["status"] == "full" for r in matrix if r["make"] == make
            ), make


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
        "abs turns itself back on",
        "wrong front wheel ordered for a 1290",
        "bike rides fine after a lowside",
        "abs light after a green lane ride",
        "front abs still cuts in with offroad selected",
    ])
    def test_a_mechanic_query_finds_the_entry(self, db_path, needle):
        assert find_issues_by_symptom(needle, db_path), needle
