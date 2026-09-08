"""Phase 227 — Triumph Tiger adventure line.

**The make was absent and the topic saturated.** Tiger returned zero
mentions across 784 entries, but 66 adventure entries already exist
across the GS, Multistrada, V-Strom and dual-sport files. So the
backwards genericness test runs at full strength: every entry names a
Tiger designation, and the counter-assertion sweeps every non-Triumph
file rather than one hand-picked entry.

**Five researched claims were refuted and none of them shipped.** The
Tiger 1050's front wheel is 17 inches, not the 19 the finding's prose
claimed — and 17 is what it *shares* with the Speed Triple, so the
sentence inverted its own point. "Off-Road Pro" is exclusive to the
Rally Pro, not part of the general Pro package. The brake-pad
corrosion mechanism (nickel, porosity) is not in the dealer notice
that was cited for it; the regulator's own wording is used instead.
The XR/XC acronym expansion is undocumented, so it is not published.
And the 18,000-mile valve interval for the 2024 Tiger 900, repeated
widely online, is **false** — a refuter extracted the handbook's
maintenance table with per-word coordinates and resolved the valve row
to the 12,000 and 24,000 columns. The entry states it is wrong rather
than staying silent.

**One finding was handed to another phase rather than used.** A refuter
surfaced P0315, a crankshaft-position adaption code that cannot be
cleared with the normal erase function. That is Phase 230's scope, so
it is recorded on the roadmap and asserted absent here.
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
TIGER = K / "known_issues_triumph_tiger.json"
BONNIE = K / "known_issues_triumph_bonneville.json"
COMPAT = SEED_DATA_DIR.parent.parent / "hardware" / "compat_data" / "compat_matrix.json"

DESIGNATIONS = {
    "Tiger 800": r"Tiger 800",
    "Tiger 900": r"Tiger 900",
    "Tiger 1200": r"Tiger 1200",
    "Explorer": r"Explorer",
    "Tiger 1050": r"Tiger 1050",
    "T-plane": r"T-plane",
    "XC": r"\bXC\b",
    "XR": r"\bXR\b",
    "Rally": r"\bRally\b",
    "GT": r"\bGT\b",
    "Tiger": r"\bTiger\b",
}
#: Designations that cannot appear innocently in another make's entry.
#: The bare variant letters are excluded — "GT" and "XR" are ordinary
#: model suffixes elsewhere in the corpus (the Phase 226 lesson, where
#: "America" matched "North America").
UNAMBIGUOUS = {k: v for k, v in DESIGNATIONS.items()
               if k not in ("XC", "XR", "GT", "Rally")}


def _claims(e: dict) -> str:
    return " ".join([e["title"], e["description"], e["fix_procedure"]] + e["causes"])


def _named(e: dict, where: str = "both") -> list[str]:
    text = e["title"] if where == "title" else _claims(e)
    return [n for n, p in DESIGNATIONS.items() if re.search(p, text)]


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "tiger.db")
    init_db(path)
    load_known_issues_file(TIGER, path)
    return path


@pytest.fixture
def raw():
    return json.loads(TIGER.read_text(encoding="utf-8"))


class TestContent:
    def test_loads_eleven(self, db_path):
        assert count_known_issues(db_path=db_path) == 11

    def test_all_are_triumph(self, raw, db_path):
        assert {e["make"] for e in raw} == {"Triumph"}
        assert len(search_known_issues(make="Triumph", db_path=db_path)) == 11

    def test_severity_years_procedures(self, raw):
        for e in raw:
            assert e["severity"] in {"critical", "high", "medium", "low"}
            assert 1993 <= e["year_start"] <= e["year_end"] <= 2026, e["title"]
            assert e["fix_procedure"].strip() and e["estimated_hours"] > 0, e["title"]
            assert e["parts_needed"], e["title"]

    def test_the_brake_recall_is_the_critical_one(self, raw):
        crit = [e for e in raw if e["severity"] == "critical"]
        assert len(crit) == 1
        assert "brake pads" in crit[0]["title"]


class TestTheDesignationBar:
    def test_every_entry_names_a_designation_in_title_and_body(self, raw):
        for e in raw:
            assert _named(e, "title"), f"{e['title']}: title names none"
            assert _named(e, "both"), f"{e['title']}: body names none"

    def test_no_other_makes_entry_scores(self):
        """66 adventure entries exist across the GS, Multistrada, V-Strom
        and dual-sport files. If any scored a Tiger designation the bar
        would be measuring nothing. Swept corpus-wide, not sampled."""
        for f in K.glob("known_issues_*.json"):
            if "triumph" in f.name:
                continue
            for e in json.loads(f.read_text(encoding="utf-8")):
                hits = [n for n, p in UNAMBIGUOUS.items()
                        if re.search(p, json.dumps(e))]
                assert not hits, f"{f.name}: {e['title'][:40]} scores {hits}"

    def test_no_symptom_resolves_to_both_triumph_files(self, raw):
        mine = {s for e in raw for s in e["symptoms"]}
        theirs = {s for e in json.loads(BONNIE.read_text(encoding="utf-8"))
                  for s in e["symptoms"]}
        assert not (mine & theirs), mine & theirs


class TestProvenance:
    def test_every_entry_is_service_manual_sourced(self, raw):
        """Unlike Phase 226, no entry here rests on forum consensus
        alone — the driveline reports are carried inside a
        manual-sourced entry and labelled as owner reports in prose."""
        assert {e["source"] for e in raw} == {"service-manual"}

    def test_nothing_is_model_generated(self, raw):
        assert not [e for e in raw if e["source"] == "model-generated"]

    def test_no_entry_claims_to_be_general_knowledge(self, raw):
        for e in raw:
            assert "general knowledge" not in e["description"].lower(), e["title"]

    def test_every_entry_says_what_it_is_drawn_from(self, raw):
        for e in raw:
            assert re.search(r"[Dd]rawn from", e["description"]), e["title"]

    def test_no_entry_fabricates_a_forum_tip(self, raw):
        for e in raw:
            assert "Forum tip" not in e["fix_procedure"], e["title"]

    def test_the_forum_level_driveline_reports_are_labelled(self, raw):
        """The Explorer bevel-box reports are owner-level, and the entry
        carrying them says so — there is no campaign and no free
        remedy, which is the shop's conversation, not a detail."""
        shaft = [e for e in raw if "shaft drive" in e["title"]][0]
        text = _claims(shaft).lower()
        assert "owner" in text and "not a recall" in text


class TestTheRefutationsAreReflectedInTheContent:
    def test_the_tiger_1050_is_not_given_a_19_inch_front(self, raw):
        """Refuted: it is 17 inches, and 17 is what it shares with the
        Speed Triple — the original prose inverted its own point."""
        assert not re.search(r"Tiger 1050[^.]{0,80}19", json.dumps(raw))

    def test_the_xr_xc_expansion_is_not_published(self, raw):
        """Refuted: no Triumph source states what the letters
        abbreviate. The entry says what they do and declines to say
        what they stand for."""
        blob = json.dumps(raw).lower()
        assert "cross country" not in blob and "cross road" not in blob
        variants = [e for e in raw if "XR and XC" in e["title"]][0]
        assert "not documented" in variants["title"] or "not" in _claims(variants)

    def test_the_pad_corrosion_mechanism_is_not_asserted(self, raw):
        """Refuted: nickel content and porosity appear nowhere in the
        dealer notice cited for them. The regulator's own wording —
        pads may corrode, friction material may detach — is used."""
        assert not re.search(r"nickel|porous", json.dumps(raw), re.I)
        pads = [e for e in raw if "brake pads" in e["title"]][0]
        text = _claims(pads).lower()
        assert "corrode" in text and "detach" in text

    def test_off_road_pro_is_not_attributed_to_the_gt_pro(self, raw):
        """Refuted: it is Rally Pro exclusive."""
        assert not re.search(r"GT Pro[^.]{0,60}Off-Road Pro", json.dumps(raw))

    def test_the_false_18000_mile_interval_is_named_as_false(self, raw):
        """The strongest refuter result: positional extraction of the
        2024 handbook resolved the valve row to the 12,000 and 24,000
        columns. The entry states the circulating figure is wrong
        rather than staying quiet about it."""
        valves = [e for e in raw if "valve intervals" in e["title"]][0]
        text = _claims(valves)
        assert "18,000" in text, "the false figure is never addressed"
        m = re.search(r"[^.]{0,160}18,000[^.]{0,160}", text)
        assert re.search(r"false|wrong|misread", m.group(), re.I), (
            "18,000 appears without being marked false"
        )


class TestTheTPlaneBoundaries:
    def test_the_t_plane_models_are_named(self, raw):
        tp = [e for e in raw if "fire unevenly" in e["title"]][0]
        text = _claims(tp)
        for m in ("Tiger 900", "Tiger 1200", "850 Sport"):
            assert m in text, f"{m} not named"

    def test_the_non_t_plane_tigers_are_excluded_explicitly(self, raw):
        """A Tiger Sport 660 or 800 is a conventional triple. An entry
        that only says which bikes are T-plane invites the reader to
        assume every Tiger is."""
        tp = [e for e in raw if "fire unevenly" in e["title"]][0]
        text = _claims(tp)
        assert "660" in text and "Sport 800" in text
        assert "Speed Triple 1200" in text

    def test_the_press_derived_numbers_are_labelled(self, raw):
        """Triumph publishes the firing order and the phrase; the degree
        intervals and pin angles come from launch briefings. The entry
        says so rather than presenting them as first-party."""
        tp = [e for e in raw if "fire unevenly" in e["title"]][0]
        assert "press-derived" in _claims(tp)

    def test_no_pin_angle_or_interval_numbers_are_stated_as_fact(self, raw):
        """Having labelled them, the entry does not then print them."""
        blob = json.dumps(raw)
        assert not re.search(r"180\s*/\s*270\s*/\s*270", blob)
        assert not re.search(r"0/90/180", blob)


class TestIntervalsAreTriumphCited:
    def test_both_families_intervals_are_given(self, raw):
        valves = [e for e in raw if "valve intervals" in e["title"]][0]
        text = _claims(valves)
        for figure in ("12,000", "20,000", "24,000", "6,000"):
            assert figure in text, figure

    def test_the_first_service_split_is_stated(self, raw):
        first = [e for e in raw if "first-service" in e["title"]][0]
        text = _claims(first)
        assert "500 miles" in text and "600 miles" in text

    def test_interval_entries_attribute_to_the_handbook(self, raw):
        for e in raw:
            if re.search(r"\b\d{1,3},\d{3}\s*miles?\b", _claims(e), re.I):
                assert re.search(r"handbook|maintenance table", _claims(e), re.I), (
                    f"{e['title']}: states intervals without attributing them"
                )


class TestDeferralBoundaries:
    def test_no_bonneville_content(self, raw):
        forbidden = r"Bonneville T|T100|T120|Thruxton|Speedmaster|Street Twin"
        for e in raw:
            hits = re.findall(forbidden, _claims(e))
            assert not hits, f"{e['title']}: {hits} belongs to Phase 226"

    def test_no_triple_naked_content(self, raw):
        """228 owns the Street and Speed Triples. Naming the Speed
        Triple 1200 to exclude it from the T-plane claim is a boundary
        statement, not content — so only the nakeds' own models are
        forbidden."""
        forbidden = r"Street Triple|Daytona|\b675\b|\b765\b"
        for e in raw:
            hits = re.findall(forbidden, _claims(e))
            assert not hits, f"{e['title']}: {hits} belongs to Phase 228"

    def test_no_pre_hinckley_content(self, raw):
        for e in raw:
            assert not re.findall(r"Meriden|T509|T595", _claims(e)), e["title"]

    def test_no_fault_codes(self, raw):
        """230 owns the DTC format. A refuter surfaced P0315 — a
        crankshaft-position adaption code that cannot be cleared with
        the normal erase function — which is exactly 230's material and
        is recorded on the roadmap instead of written here."""
        forbidden = r"\bP0\d{3}\b|\bP1\d{3}\b|\bC1\d{3}\b|TuneECU|TuneBoy|dealer mode"
        for e in raw:
            hits = re.findall(forbidden, _claims(e), re.I)
            assert not hits, f"{e['title']}: {hits} belongs to Phase 230"
        for e in raw:
            assert e["dtc_codes"] == [], e["title"]


class TestRecallScopingIsByFrameNumber:
    def test_the_negative_finding_is_present(self, raw):
        """A campaign indexed under the Tiger name that covers only the
        660-class machines. Included because a wrong match costs a
        customer a dealer trip and a false promise of free work."""
        neg = [e for e in raw if "manifold-pressure-hose" in e["title"]]
        assert neg, "the negative finding was dropped"
        text = _claims(neg[0])
        assert "660" in text
        assert re.search(r"does not apply|not the Tiger 900", text)

    def test_every_recall_entry_directs_to_the_frame_number(self, raw):
        for e in raw:
            if re.search(r"recall", e["title"], re.I) and "not apply" not in e["title"]:
                assert re.search(r"frame number", _claims(e), re.I), e["title"]


class TestTheAdapterGapIsLeftForItsOwner:
    def test_the_triumph_catalog_rows_are_unchanged(self):
        matrix = json.loads(COMPAT.read_text(encoding="utf-8"))
        assert len([r for r in matrix if r["make"] == "triumph"]) == 5

    def test_the_tiger_rows_start_at_2013(self):
        """So the 2011-2012 Tiger 800 has no adapter row — the same
        shape as the air-cooled Bonneville gap Phase 226 left. Row 230
        owns Triumph tooling."""
        matrix = json.loads(COMPAT.read_text(encoding="utf-8"))
        tiger = [r for r in matrix
                 if r["make"] == "triumph" and "tiger" in r["model_pattern"]]
        assert tiger and all(r["year_min"] >= 2013 for r in tiger)
        assert all(r["status"] != "full" for r in tiger)


class TestSearchability:
    def test_symptoms_are_short_phrases(self, raw):
        for e in raw:
            for s in e["symptoms"]:
                assert len(s) <= 55 and not s.endswith("."), f"{e['title']}: {s!r}"

    def test_no_title_collides_corpus_wide(self):
        titles = []
        for f in K.glob("known_issues_*.json"):
            titles += [e["title"] for e in json.loads(f.read_text(encoding="utf-8"))]
        assert len(titles) == len(set(titles))

    @pytest.mark.parametrize("needle", [
        "tiger 900 sounds like it is missing",
        "booking just says tiger 900",
        "is this tiger chain or shaft",
        "valve interval on a tiger 900",
        "first service mileage on a tiger",
        "pads look thick but brake is poor",
        "tiger 800 stalls when slowing down",
        "explorer stalls unpredictably",
        "is my tiger 900 in the map sensor recall",
        "head bolts found loose",
        "what does xc mean on a tiger",
    ])
    def test_a_mechanic_query_finds_the_entry(self, db_path, needle):
        assert find_issues_by_symptom(needle, db_path), needle
