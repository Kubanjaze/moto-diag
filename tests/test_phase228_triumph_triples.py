"""Phase 228 — Triumph Street Triple / Speed Triple / Daytona.

**The first file with mixed provenance by construction rather than by
subject.** Research was capped, then dropped, then reinstated mid-phase.
Five entries were written from general knowledge in the gap and three of
them stay `model-generated`; the rest, and two corrections to those five,
are `service-manual`. The split is asserted rather than described: a
`model-generated` entry may not carry a recall campaign number, a
manufacturer publication number or a service interval, because those are
exactly what an unsourced entry would be tempted to invent.

**Research corrected two entries I had already written.** I wrote that
the Daytona 675 and Street Triple 675 share an engine in different
tunes — true only to 2012. From 2013 the Daytona took a bigger bore and
shorter stroke with higher compression while the Street Triple kept the
original, so they are genuinely different engines, not different
calibrations. And I wrote that trim suffixes never change the engine —
except the 2017–2022 Street Triple **S** is a 660, not a 765. Both would
have sent someone to order the wrong parts.

**Both refuters caught the same misreading of a recall form.** The
research read the Part 573's *candidate* model list as the recall
population; section 3's unit table shows the detent-spring campaign is
one model, with the rest at zero. What survives is stranger and more
useful: the regulator's structured model index for that campaign lists
models with zero units and omits the one that is affected, so a
model-name query never returns it. The entry says look it up by frame
number.

**Ninth phase in which my own selector confused mention with use.** A
crude regex read "for 2013–2017 they are **not** the same engine" as a
sharing claim, and read boundary references to the Tiger 1200 as Tiger
content. Both are handled here by asserting what the entries must say
rather than pattern-matching what they must not.
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
TRIPLES = K / "known_issues_triumph_triples.json"
TRIUMPH_FILES = sorted(K.glob("known_issues_triumph_*.json"))
COMPAT = SEED_DATA_DIR.parent.parent / "hardware" / "compat_data" / "compat_matrix.json"

DESIGNATIONS = {
    "Street Triple": r"Street Triple",
    "Speed Triple": r"Speed Triple",
    "Daytona": r"Daytona",
    "675": r"\b675\b",
    "765": r"\b765\b",
    "1050": r"\b1050\b",
    "1200": r"\b1200\b",
}
UNAMBIGUOUS = {k: v for k, v in DESIGNATIONS.items() if not k.isdigit()}

#: What an unsourced entry would be tempted to invent: campaign numbers,
#: manufacturer references, publication numbers, interval figures.
SOURCED_ONLY = re.compile(
    r"\b\d{2}V\d{3}\b|\bSRAN\s?\d+|\bSB\d{3}\b|\bRM/\d{4}/\d+\b|"
    r"\b\d{1,3},\d{3}\s*(?:mi|miles?|km)\b|\b38\d{5}-EN\b"
)


def _claims(e: dict) -> str:
    return " ".join([e["title"], e["description"], e["fix_procedure"]] + e["causes"])


def _named(e: dict, where: str = "both") -> list[str]:
    text = e["title"] if where == "title" else _claims(e)
    return [n for n, p in DESIGNATIONS.items() if re.search(p, text)]


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "triples.db")
    init_db(path)
    load_known_issues_file(TRIPLES, path)
    return path


@pytest.fixture
def raw():
    return json.loads(TRIPLES.read_text(encoding="utf-8"))


class TestContent:
    def test_loads_eleven(self, db_path):
        assert count_known_issues(db_path=db_path) == 11

    def test_all_are_triumph(self, raw, db_path):
        assert {e["make"] for e in raw} == {"Triumph"}
        assert len(search_known_issues(make="Triumph", db_path=db_path)) == 11

    def test_severity_years_procedures(self, raw):
        for e in raw:
            assert e["severity"] in {"critical", "high", "medium", "low"}
            assert 2005 <= e["year_start"] <= e["year_end"] <= 2026, e["title"]
            assert e["fix_procedure"].strip() and e["estimated_hours"] > 0, e["title"]
            assert e["parts_needed"], e["title"]

    def test_the_silent_abs_failure_is_the_critical_one(self, raw):
        """A safety system that stops working without lighting a lamp is
        the only thing here that rates critical — the harm is that the
        ordinary check gives a false pass."""
        crit = [e for e in raw if e["severity"] == "critical"]
        assert len(crit) == 1
        assert "anti-lock" in crit[0]["title"]


class TestTheProvenanceSplitIsAssertedNotDescribed:
    def test_both_populations_exist(self, raw):
        sources = {e["source"] for e in raw}
        assert sources == {"model-generated", "service-manual"}

    def test_no_model_generated_entry_carries_a_sourced_figure(self, raw):
        """The load-bearing assertion of this phase. An entry written
        without sources may not carry a recall number, a publication
        number or an interval — those are precisely what would be
        invented to make it look as authoritative as its neighbours."""
        for e in raw:
            if e["source"] != "model-generated":
                continue
            hits = SOURCED_ONLY.findall(_claims(e))
            assert not hits, f"{e['title']}: unsourced entry cites {hits}"

    def test_service_manual_entries_say_what_they_are_drawn_from(self, raw):
        for e in raw:
            if e["source"] == "service-manual":
                assert re.search(r"[Dd]rawn from", e["description"]), e["title"]

    def test_model_generated_entries_use_the_general_knowledge_opening(self, raw):
        for e in raw:
            if e["source"] == "model-generated":
                assert e["description"].startswith("General knowledge"), e["title"]

    def test_no_entry_fabricates_a_forum_tip(self, raw):
        for e in raw:
            assert "Forum tip" not in e["fix_procedure"], e["title"]


class TestResearchCorrectedWhatMemoryGotWrong:
    def test_the_engine_sharing_is_bounded_at_2013(self, raw):
        """Written from memory as a blanket claim; corrected. Both halves
        must be present — shared to 2012, different from 2013 — because
        stating only one of them is the error in the other direction."""
        shared = [e for e in raw if "shared an engine only until 2013" in e["title"]]
        assert shared, "the corrected engine-sharing entry is missing"
        text = _claims(shared[0])
        assert re.search(r"2006[–-]2012[^.]{0,60}shared", text), "the sharing half is gone"
        assert re.search(r"2013[–-]2017[^.]{0,60}not the same engine", text), (
            "the divergence half is gone"
        )
        assert re.search(r"bore|stroke|compression", text), (
            "the entry does not say what actually differs"
        )

    def test_no_cross_model_sharing_claim_is_left_unbounded(self, raw):
        """Scoped to the Daytona/Street Triple relationship, which is the
        claim that was wrong. An earlier version of this test matched any
        sentence containing "share an engine" and flagged "do not apply
        the general rule that trims share an engine without checking" —
        a different subject, and an instruction not to apply the rule.
        Tenth phase in which my own selector confused mention with use."""
        for e in raw:
            text = _claims(e)
            for m in re.finditer(r"shared? (?:one|an|the same) engine", text):
                window = text[max(0, m.start() - 150):m.end() + 60]
                if "Daytona" not in window:
                    continue  # not the cross-model claim this rule is about
                assert re.search(r"20\d\d", window), (
                    f"{e['title']}: unbounded Daytona/Street Triple sharing claim"
                )

    def test_the_trims_rule_is_stated_as_defeasible(self, raw):
        """Guard on the guard above: the trims entry must say the general
        rule needs checking rather than asserting it holds."""
        trims = [e for e in raw if "S, R and RS" in e["title"]][0]
        assert re.search(r"without checking|confirm the displacement", _claims(trims))

    def test_the_street_triple_s_exception_is_stated(self, raw):
        """Written from memory as 'trims never change the engine'. The
        2017-2022 Street Triple S is a 660, not a 765."""
        trims = [e for e in raw if "S, R and RS" in e["title"]]
        assert trims
        text = _claims(trims[0])
        assert "660" in text, "the S-is-a-660 exception is missing"
        assert re.search(r"exception|except", text, re.I)

    def test_no_entry_says_trims_never_change_the_engine(self, raw):
        for e in raw:
            assert not re.search(
                r"(suffix|trim)[^.]{0,50}(never|do not|does not)[^.]{0,30}engine",
                _claims(e), re.I,
            ), e["title"]


class TestTheRecallScopeSurvivedRefutation:
    def test_the_detent_campaign_is_not_given_a_wide_model_scope(self, raw):
        """Both refuters caught the research reading the Part 573's
        candidate list as the population. The unit table shows one model
        affected and the rest at zero."""
        blob = json.dumps(raw).lower()
        assert "eight models" not in blob
        for other in ("sprint st", "sprint gt"):
            assert other not in blob, f"{other} is not in the population"

    def test_the_index_defect_is_what_the_entry_teaches(self, raw):
        """What survived refutation is the search problem, not a wide
        scope: the structured index lists models with zero units and
        omits the affected one."""
        rec = [e for e in raw if "hides one of them" in e["title"]]
        assert rec, "the two-campaign entry is missing"
        text = _claims(rec[0])
        assert re.search(r"frame number", text, re.I)
        assert re.search(r"omit|hides|never see", text, re.I)

    def test_it_states_the_ranges_do_not_overlap(self, raw):
        rec = [e for e in raw if "hides one of them" in e["title"]][0]
        assert re.search(r"do not overlap|never both|one or the other", _claims(rec))

    def test_the_superseded_remedy_pattern_is_recorded(self, raw):
        """Second instance after the Bonneville alternator connector: a
        completed first campaign is not reassurance when the remedy is
        what was superseded."""
        fan = [e for e in raw if "radiator-fan recall" in e["title"]]
        assert fan
        text = _claims(fan[0])
        assert re.search(r"may not have been effective", text)
        assert re.search(r"frame number", text, re.I)

    def test_the_negative_finding_on_the_675_valve_train_is_present(self, raw):
        """No recall touches this engine's valve gear, and three
        different things get blamed on it."""
        neg = [e for e in raw if "no cam or valve-gear recall" in e["title"]]
        assert neg
        text = _claims(neg[0])
        assert "design change" in text or "specification revision" in text
        assert re.search(r"exhaust power valve", text, re.I)
        assert re.search(r"no free remedy|there is no campaign|none exists", text, re.I)


class TestCrossModelReferencesAreBoundariesNotContent:
    """The Tiger and Bonneville appear here only to be contrasted with.
    A crude forbidden-word check cannot tell that apart, so the
    assertions are about what the entries claim, not which words appear."""

    def test_no_entry_is_about_a_tiger_or_a_bonneville(self, raw):
        for e in raw:
            assert not re.search(r"Tiger|Bonneville", e["title"]) or "not the Tiger" in e["title"], e["title"]
            assert not re.search(r"Tiger|Bonneville", e["model"]), e["model"]

    def test_every_tiger_mention_is_a_contrast(self, raw):
        for e in raw:
            text = _claims(e)
            for m in re.finditer(r"Tiger", text):
                window = text[max(0, m.start() - 130):m.end() + 130]
                assert re.search(
                    r"\bnot\b|does not transfer|do not carry|by analogy|conventional|"
                    r"shares[^.]{0,40}but", window
                ), f"{e['title']}: Tiger named without a contrast"

    def test_the_speed_triple_1200_is_never_called_t_plane(self, raw):
        """The Phase 227 boundary, asserted from this side too."""
        for e in raw:
            text = _claims(e)
            for m in re.finditer(r"T-plane", text):
                window = text[max(0, m.start() - 90):m.end() + 60]
                assert re.search(r"\bnot\b|Tiger", window), (
                    f"{e['title']}: attributes a T-plane crank to a Speed Triple"
                )


class TestTheDesignationBar:
    def test_every_entry_names_a_designation_in_title_and_body(self, raw):
        for e in raw:
            assert _named(e, "title"), f"{e['title']}: title names none"
            assert _named(e, "both"), f"{e['title']}: body names none"

    def test_no_other_makes_entry_scores(self):
        """The naked segment is crowded — MT-09, Z900, GSX-S, Monster.
        Swept corpus-wide rather than sampled."""
        for f in K.glob("known_issues_*.json"):
            if "triumph" in f.name:
                continue
            for e in json.loads(f.read_text(encoding="utf-8")):
                hits = [n for n, p in UNAMBIGUOUS.items()
                        if re.search(p, json.dumps(e))]
                assert not hits, f"{f.name}: {e['title'][:40]} scores {hits}"

    def test_no_symptom_resolves_to_two_triumph_files(self, raw):
        mine = {s for e in raw for s in e["symptoms"]}
        for f in TRIUMPH_FILES:
            if f == TRIPLES:
                continue
            theirs = {s for e in json.loads(f.read_text(encoding="utf-8"))
                      for s in e["symptoms"]}
            assert not (mine & theirs), f"{f.name}: {mine & theirs}"


class TestTheDaytonaScope:
    def test_the_daytona_is_stated_to_be_faired(self, raw):
        d = [e for e in raw if "faired supersport" in e["title"]]
        assert d, "the Daytona scope entry is missing"
        text = _claims(d[0])
        assert "naked" in text and "faired" in text

    def test_it_says_what_actually_carries_across(self, raw):
        d = [e for e in raw if "faired supersport" in e["title"]][0]
        assert re.search(r"engine", _claims(d), re.I)


class TestIntervalsAreHandbookCited:
    def test_the_1200_outlier_is_stated(self, raw):
        v = [e for e in raw if "valve intervals" in e["title"]]
        assert v
        text = _claims(v[0])
        assert "12,000" in text and "20,000" in text
        assert re.search(r"Speed Triple 1200[^.]{0,60}20,000|20,000[^.]{0,60}Speed Triple 1200", text)

    def test_the_unestablished_generations_are_admitted(self, raw):
        """No handbook was obtained for the 675 generation. The entry
        says so rather than letting the 12,000 figure carry back."""
        v = [e for e in raw if "valve intervals" in e["title"]][0]
        text = _claims(v)
        assert "675" in text
        assert re.search(r"not established|should not be assumed", text)

    def test_it_attributes_the_figures(self, raw):
        v = [e for e in raw if "valve intervals" in e["title"]][0]
        assert re.search(r"handbook|maintenance table", _claims(v), re.I)


class TestDeferralBoundaries:
    def test_no_pre_hinckley_content(self, raw):
        for e in raw:
            assert not re.findall(r"Meriden|T509|T595", _claims(e)), e["title"]

    def test_no_fault_codes_or_tooling_content(self, raw):
        forbidden = r"\bP0\d{3}\b|\bP1\d{3}\b|\bC1\d{3}\b|TuneECU|TuneBoy|dealer mode"
        for e in raw:
            hits = re.findall(forbidden, _claims(e), re.I)
            assert not hits, f"{e['title']}: {hits} belongs to Phase 230"
        for e in raw:
            assert e["dtc_codes"] == [], e["title"]

    def test_the_adapter_catalog_is_unchanged(self):
        matrix = json.loads(COMPAT.read_text(encoding="utf-8"))
        assert len([r for r in matrix if r["make"] == "triumph"]) == 5


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
        "daytona part on a street triple",
        "is the daytona the same as a street triple",
        "booking just says street triple",
        "uneven idle on a speed triple 1200",
        "does the r trim have a different engine",
        "neutral light on with a gear engaged",
        "radiator fan failed on a speed triple 1200",
        "noise from the cam chain on a 675",
        "valve interval on a street triple",
        "abs light off but abs not working",
        "battery flat again on a daytona",
    ])
    def test_a_mechanic_query_finds_the_entry(self, db_path, needle):
        assert find_issues_by_symptom(needle, db_path), needle
