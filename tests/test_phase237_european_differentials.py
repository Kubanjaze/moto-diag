"""Phase 237 — European failure patterns as differential diagnosis by make.

The row's topics were saturated three times over (generic cross-platform
files plus 26 European make-files), so the refuters were told to score
genericness. 19 of 34 proposed entries were flagged as duplicates of
named existing entries and dropped. What ships is the differential: same
symptom, different make, different first check.
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
K = ROOT / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"
FILE = K / "known_issues_european_differentials.json"
MAKES = ("BMW", "Ducati", "KTM", "Triumph", "Aprilia", "Moto Guzzi")

#: Phrases from the entries a refuter identified as already present in
#: named existing files. None may reappear here — the duplication was
#: caught by evidence, and this pins the exclusion.
ALREADY_IN_CORPUS = (
    "Hall-effect sensor wiring", "Integral ABS", "Telelever",
    "two rockers and two shims", "dry clutch idle rattle",
    "slave cylinder weeping", "sprag", "Rotax",
    "unsealed stator-to-regulator", "tensioner bearings fail more",
)


MILEAGE = (
    r"\b\d{1,3}(?:,\d{3})+\s*(?:km|miles|mi)\b"      # 12,000 km
    r"|\b\d{4,6}\s*(?:km|miles|mi)\b"                 # 12000 km  (uncomma'd)
    r"|\b\d{1,3}k\s*(?:km|miles|mi)\b"                # 12k miles
)


@pytest.fixture(scope="module")
def raw():
    return json.loads(FILE.read_text(encoding="utf-8"))


def _claims(e):
    return " ".join([e["title"], e["description"], e["fix_procedure"]] + e["causes"])


class TestFileShape:
    def test_fifteen_entries(self, raw):
        assert len(raw) == 15

    def test_required_keys(self, raw):
        need = {"title", "description", "make", "model", "year_start", "year_end",
                "severity", "symptoms", "causes", "fix_procedure", "parts_needed",
                "estimated_hours", "dtc_codes", "source"}
        for e in raw:
            assert need <= set(e), e["title"]

    def test_symptoms_are_short_phrases(self, raw):
        for e in raw:
            for s in e["symptoms"]:
                assert len(s) <= 55 and not s.endswith("."), f"{e['title']}: {s!r}"

    def test_every_entry_says_what_it_is_drawn_from(self, raw):
        for e in raw:
            assert re.search(r"[Dd]rawn\b[\w' ]{0,16}\bfrom", e["description"]), e["title"]

    def test_forum_entries_carry_a_tip_and_others_do_not(self, raw):
        for e in raw:
            has = "Forum tip" in e["fix_procedure"]
            assert has == (e["source"] == "forum"), e["title"]

    def test_no_title_collides_corpus_wide(self):
        titles = []
        for f in K.glob("known_issues_*.json"):
            titles += [e["title"] for e in json.loads(f.read_text(encoding="utf-8"))]
        assert len(titles) == len(set(titles))


class TestTheDifferentialFraming:
    def test_every_entry_is_anchored_to_one_european_make(self, raw):
        for e in raw:
            assert e["make"] in MAKES, e["title"]
            assert e["make"] in e["title"], e["title"]

    def test_every_fix_states_an_order_of_checks(self, raw):
        """A differential is a claim about what to do FIRST. An entry
        without an ordering is a description, not a differential."""
        for e in raw:
            assert re.search(r"\bfirst\b|\bbefore\b|\bstart\b", e["fix_procedure"], re.I), e["title"]

    def test_the_contrast_entry_names_both_makes(self, raw):
        e = next(x for x in raw if "opposite call" in x["title"])
        text = _claims(e)
        assert "BMW" in text and "Triumph" in text
        assert re.search(r"opposite", text)

    def test_no_entry_duplicates_what_the_refuter_found_already_present(self, raw):
        text = " ".join(_claims(e) for e in raw)
        for phrase in ALREADY_IN_CORPUS:
            assert phrase not in text, phrase


class TestTheCorrectionsRefutationForced:
    def test_ktm_regulator_is_scoped_to_the_super_enduro_r(self, raw):
        """The research read 'SE-R' as a regulator type. It is the 950
        Super Enduro R — a model — and the source confines the failure
        to it. Scope narrowed from '950/990 all years' to one machine."""
        e = next(x for x in raw if "Super Enduro R" in x["title"])
        assert e["model"] == "950 Super Enduro R"
        assert "990" not in _claims(e)
        text = _claims(e)
        assert re.search(r"boiling|steam", text) and "safety valve" in text
        assert "rear exhaust header" in text

    def test_ktm_water_pump_carries_no_weep_hole_claim(self, raw):
        """The 'warning sign deleted by year' hook was attributed to a
        page that contains the word 'weep' zero times. It is gone, and
        the entry now says only what the source supports."""
        e = next(x for x in raw if "water pump seal" in x["title"])
        text = _claims(e)
        assert not re.search(r"weep[- ]?hole", text, re.I)
        assert "casting sand" in text and "Teflon" in text
        assert re.search(r"not printed here", text)

    def test_guzzi_entry_prints_no_currency_figure(self, raw):
        """A refuter found an NZD figure rendered as USD. No figure ships."""
        e = next(x for x in raw if "Moto Guzzi 1200 8V" in x["title"])
        text = _claims(e)
        assert not re.search(r"\$|USD|NZD|\b\d,\d{3}\b", text)
        assert "engine number" in text

    def test_no_campaign_reference_numbers(self, raw):
        for e in raw:
            assert not re.findall(r"\b\d{2}V\d{6}\b", _claims(e)), e["title"]


class TestBoundaries:
    def test_no_fault_codes(self, raw):
        for e in raw:
            assert e["dtc_codes"] == []
            assert not re.findall(r"\bP0\d{3}\b", _claims(e)), e["title"]

    def test_no_valve_interval_figures(self, raw):
        """Phase 238 owns intervals. Scoped to mileages used AS an
        interval, as at 225B, so an owner's failure mileage passes."""
        interval = r"(valve|service|interval|schedule|due|every)"
        for e in raw:
            text = _claims(e)
            for m in re.finditer(MILEAGE, text):
                window = text[max(0, m.start() - 90):m.end() + 90]
                assert not re.search(interval, window, re.I), f"{e['title']}: {m.group(0)}"

    def test_does_not_restate_the_generic_charging_file(self, raw):
        generic = json.loads((K / "known_issues_cross_platform_charging.json").read_text(encoding="utf-8"))
        stems = {" ".join(g["title"].split()[:5]).lower() for g in generic}
        for e in raw:
            assert " ".join(e["title"].split()[:5]).lower() not in stems, e["title"]


class TestSearchability:
    @pytest.mark.parametrize("needle", [
        "bmw r1150 charging low voltage alternator",
        "ktm super enduro battery boiling whistle",
        "aprilia rsv4 stator keeps burning out",
        "bmw boxer clack on startup normal",
        "moto guzzi 8v tappet metal in oil",
        "triumph 955i high idle when warm",
        "bmw led lamp fault canbus",
        "ducati 916 chrome flakes in oil",
    ])
    def test_a_plausible_query_finds_something(self, raw, needle):
        # Hyphens normalised on the content side: a mechanic types
        # "canbus" and the entry says "CAN-bus" — same class of miss as
        # "location" against "located".
        words = [w[:5] for w in re.findall(r"[a-z0-9]+", needle) if len(w) > 3]
        best = max(sum(1 for w in words if w in _claims(e).lower().replace("-", ""))
                   for e in raw)
        assert best >= 3, f"{needle!r} matched only {best} terms"


class TestTheMileagePatternItself:
    """Phase 240B. The interval guard below is a negative assertion over a
    file that contains no mileage token at all, so its loop body has never
    executed -- coverage confirms the assert line is unreached. A guard that
    can go dead through a regex typo and stay green is not a guard.

    The anti-vacuity check is on the PATTERN, not on the file. Asserting the
    file contains a mileage token would be the wrong fix here: this file's
    stated job (Phase 238 owns intervals) is to print none, so satisfying
    such an assertion would mean injecting the very thing the guard forbids.

    The uncomma'd and `12k` forms are not hypothetical -- the corpus already
    authors them (`12000 km` in the MV triple file, `18000 miles` in the
    Triumph Tiger file), and the original comma-only pattern missed both."""

    @pytest.mark.parametrize("s", ["12,000 km", "12000 km", "18,000 miles", "18000 miles", "12k miles"])
    def test_it_matches_the_forms_this_corpus_authors(self, s):
        assert re.search(MILEAGE, s), s

    @pytest.mark.parametrize("s", ["2013", "1200", "1150", "0.5", "R1200GS", "990 LC8"])
    def test_it_does_not_match_bare_numbers(self, s):
        assert not re.search(MILEAGE, s), s
