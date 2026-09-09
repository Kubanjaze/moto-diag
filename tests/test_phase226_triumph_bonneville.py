"""Phase 226 — Triumph Bonneville family (Hinckley, 2001 on). Opens the
Triumph block.

**The first phase whose entries are not `model-generated`.** Every Track K
file so far has carried that provenance, honestly, because it was written
from training data. These entries are not: they come from Triumph owner's
handbooks and the T120 service manual, and from recall records filed with
national road-safety regulators. Marking them `model-generated` would
understate provenance, and provenance accuracy is the entire reason the
`source` column exists. Ten are `service-manual`; the one resting on
owner-forum consensus is `forum`, and it says so in its own prose.

**That required fixing Gate 2, and the bug was instructive.** Gate 2's
forum-tip rule excluded by denylist — `source != "model-generated"` —
which silently assumed the corpus would only ever hold two populations.
A third makes a denylist demand forum tips from service-manual entries.
It now names the population it measures (`unverified` plus `forum`), and
its sibling assertion was widened the same way. Same encoding bug as the
Phase 221 "no sibling KTM file" guard and the Phase 222 hardcoded count:
a rule that names what to exclude rather than what it means.

**Four findings researched, two refuted, and the refutations changed the
content.** The engine-number breakpoint separating 790 from 865 turned
out to be the T100's changeover only — the base Bonneville and America
stayed 790 with engine numbers well beyond it, and their breakpoint is
not established anywhere consulted. Writing it as a general rule would
have sent someone to order the wrong pistons. And a forum line stating
Triumph advises no parts commonality between the generations was
contradicted in its own thread; the entry now carries the documented rim
that would not lace and says the wider claim is disputed.

**The crank angle is not the air-cooled/liquid-cooled split**, and this
phase's own plan got that wrong before the research corrected it. The
America, Speedmaster and Scrambler are 270-degree engines while
air-cooled.
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
BONNIE = K / "known_issues_triumph_bonneville.json"
COMPAT = SEED_DATA_DIR.parent.parent / "hardware" / "compat_data" / "compat_matrix.json"

#: The five Triumph compat rows that existed before Phase 230 filled the
#: gap. Phases 226-229 each asserted the count was exactly 5 — the right
#: guard while the gap was open, and the wrong shape once it closed. Same
#: "constant standing in for an invariant" bug as the KTM count at 222.
#: These now assert the original rows SURVIVED, which is what they meant.
ORIGINAL_TRIUMPH_ROWS = {
    ("obdlink-mx-plus", "tiger%"),
    ("obdlink-mx-plus", "675"),
    ("obdlink-lx", "bonneville%"),
    ("elm327-generic-bt-clone", "675"),
    ("obdlink-sx", "tiger%"),
}


#: A Bonneville-family designation. The bar is naming one — it is what a
#: parallel-twin entry from another make cannot do.
DESIGNATIONS = {
    "Bonneville": r"Bonneville",
    "T100": r"\bT100\b",
    "T120": r"\bT120\b",
    "Thruxton": r"Thruxton",
    "Scrambler": r"Scrambler",
    "Speedmaster": r"Speedmaster",
    # "America" alone matches "North America" in other makes' entries, so
    # the corpus-wide counter-assertion below uses UNAMBIGUOUS only.
    "America": r"\bAmerica\b",
    "Street Twin": r"Street Twin",
    "865": r"\b865\b",
    "790": r"\b790\b",
    "1200": r"\b1200\b",
    "900": r"\b900\b",
}
#: Designations that cannot appear innocently in another make's entry.
#: "America" and bare displacements are excluded: "North America" and
#: "900" are ordinary text elsewhere in the corpus.
UNAMBIGUOUS = {
    "Bonneville": r"Bonneville",
    "T100": r"\bT100\b",
    "T120": r"\bT120\b",
    "Thruxton": r"Thruxton",
    "Speedmaster": r"Speedmaster",
    "Street Twin": r"Street Twin",
}

#: The 270-degree models. Three of them are air-cooled, which is the
#: whole point of the crank entry.
TWO_SEVENTY = ("America", "Speedmaster", "Scrambler")

#: A title that mentions a recall to say there is NOT one is not a recall
#: entry. Eighth phase in which my own selector confused mention with use.
NOT_A_RECALL = re.compile(r"never got a recall|no recall", re.I)


def _is_recall_entry(e: dict) -> bool:
    return bool(re.search(r"recall", e["title"], re.I)) and not NOT_A_RECALL.search(
        e["title"]
    )


def _claims(e: dict) -> str:
    return " ".join([e["title"], e["description"], e["fix_procedure"]] + e["causes"])


def _named(e: dict, where: str = "both") -> list[str]:
    text = e["title"] if where == "title" else _claims(e)
    return [n for n, p in DESIGNATIONS.items() if re.search(p, text)]


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "bonnie.db")
    init_db(path)
    load_known_issues_file(BONNIE, path)
    return path


@pytest.fixture
def raw():
    return json.loads(BONNIE.read_text(encoding="utf-8"))


class TestContent:
    def test_loads_eleven(self, db_path):
        assert count_known_issues(db_path=db_path) == 11

    def test_all_are_triumph(self, raw, db_path):
        assert {e["make"] for e in raw} == {"Triumph"}
        assert len(search_known_issues(make="Triumph", db_path=db_path)) == 11

    def test_severity_years_procedures(self, raw):
        for e in raw:
            assert e["severity"] in {"critical", "high", "medium", "low"}
            assert 2001 <= e["year_start"] <= e["year_end"] <= 2026, e["title"]
            assert e["fix_procedure"].strip() and e["estimated_hours"] > 0, e["title"]
            assert e["parts_needed"], e["title"]

    def test_the_do_not_drive_recall_is_the_critical_one(self, raw):
        """A live campaign telling owners not to ride the machine is the
        only thing in this file that rates critical."""
        crit = [e for e in raw if e["severity"] == "critical"]
        assert len(crit) == 1
        assert "Do-Not-Drive" in crit[0]["title"]


class TestProvenanceIsRecordedHonestly:
    """The first Track K file that is not `model-generated`."""

    def test_sources_are_service_manual_or_forum(self, raw):
        assert {e["source"] for e in raw} <= {"service-manual", "forum"}

    def test_nothing_here_is_marked_model_generated(self, raw):
        """These came from Triumph publications and regulator records.
        Marking them model-generated would understate provenance as
        surely as the reverse would overstate it."""
        assert not [e for e in raw if e["source"] == "model-generated"]

    def test_no_entry_claims_to_be_general_knowledge(self, raw):
        """Every earlier Track K file opens its descriptions with
        'General knowledge entry'. These must not, because they are not."""
        for e in raw:
            assert "general knowledge" not in e["description"].lower(), e["title"]

    def test_every_entry_says_what_it_is_drawn_from(self, raw):
        for e in raw:
            assert re.search(r"[Dd]rawn from", e["description"]), e["title"]

    def test_the_forum_tip_marker_tracks_the_source(self, raw):
        """Rule 3, as a biconditional rather than its negative half alone.

        Re-scoped at Phase 240B. This asserted only that no entry claims a
        forum tip — Gate 2's reverse half. That is correct for every entry
        whose source is not forum-derived, but it says nothing about the
        forward half, so a `forum` entry with no tip passed. In two files
        (226, 233) the file *had* such an entry, and this assertion was
        actively forbidding the fix.

        The audit found the family: 14 copies under 8 names, 10 of them
        asserting the negative half only. Keying both halves off `source`
        makes the guard correct by construction rather than by accident —
        it stays green while a file has no forum entry, and fires the day
        one is added untipped."""
        for e in raw:
            assert ("Forum tip" in e["fix_procedure"]) == (e["source"] == "forum"), e["title"]

    def test_the_forum_sourced_entry_says_so_in_prose(self, raw):
        """The one entry resting on owner reports rather than documents
        declares that in its own text, because the shop conversation it
        implies is different — there is no campaign to quote."""
        forum = [e for e in raw if e["source"] == "forum"]
        assert len(forum) == 1
        text = _claims(forum[0]).lower()
        assert "forum" in text and "not from a recall" in text

    def test_recall_entries_are_not_marked_forum(self, raw):
        recall_entries = [e for e in raw if _is_recall_entry(e)]
        assert recall_entries, "no recall entries found"
        for e in recall_entries:
            assert e["source"] == "service-manual", e["title"]

    def test_the_entry_that_says_there_is_no_recall_is_excluded(self, raw):
        """Guard on the guard. The forum entry's title contains the word
        'recall' precisely to say there was never one; a selector that
        cannot tell mention from use would demand a document for it."""
        forum = [e for e in raw if e["source"] == "forum"][0]
        assert "recall" in forum["title"].lower()
        assert not _is_recall_entry(forum)


class TestTheDesignationBar:
    def test_every_entry_names_a_designation_in_title_and_body(self, raw):
        for e in raw:
            assert _named(e, "title"), f"{e['title']}: title names none"
            assert _named(e, "both"), f"{e['title']}: body names none"

    def test_the_recall_entries_name_the_affected_models(self, raw):
        """A shop needs to know whether the T120 in front of it is in
        the population. 'Liquid-cooled twins' does not answer that."""
        for e in raw:
            if _is_recall_entry(e):
                assert len(_named(e, "title")) >= 2, e["title"]

    def test_no_other_makes_parallel_twin_entries_score(self):
        """The counter-assertion, run over the whole corpus rather than
        one hand-picked entry (the Phase 223 improvement).

        Exempts the `european_*` cross-make files (Phase 236 on) by
        prefix, as five sibling guards now do: they own a comparison
        axis and cannot be written without naming the models they
        scope, and their own tests forbid model-specific failure
        content. This was the sixth copy of this guard found, and the
        first three sweeps missed it because they matched on the test's
        NAME — this one is `..._parallel_twin_entries_score`, not
        `..._entry_scores`. The sweep that found it matched on shape:
        every test that globs the knowledge directory and skips by
        filename."""
        for f in K.glob("known_issues_*.json"):
            if "triumph" in f.name or f.name.startswith("known_issues_european_"):
                continue
            for e in json.loads(f.read_text(encoding="utf-8")):
                hits = [n for n, p in UNAMBIGUOUS.items()
                        if re.search(p, json.dumps(e))]
                assert not hits, f"{f.name}: {e['title'][:40]} scores {hits}"


class TestTheRefutationsAreReflectedInTheContent:
    def test_the_engine_number_rule_is_scoped_to_the_t100(self, raw):
        """Refuted: the breakpoint is the T100's changeover, not a
        family rule. Writing it generally orders the wrong pistons."""
        ident = [e for e in raw if "790 from an 865" in e["title"]]
        assert ident, "no 790/865 identification entry"
        text = _claims(ident[0])
        assert "T100" in text
        assert "not established" in text, "the unknown breakpoint is not admitted"

    def test_no_specific_breakpoint_number_is_published(self, raw):
        """The figure itself is a forum member's reading of a parts
        listing. The rule survived refutation; the number did not."""
        assert "211132" not in json.dumps(raw)
        assert "211133" not in json.dumps(raw)

    def test_the_parts_commonality_claim_is_marked_disputed(self, raw):
        """Refuted: attributed to the wrong person and contradicted in
        its own thread. The documented rim stays; the generalisation is
        labelled."""
        names = [e for e in raw if "model name spans" in e["title"]]
        assert names
        text = _claims(names[0])
        assert "could not be laced" in text, "the documented fact was lost"
        assert "disputed" in text or "contradicted" in text

    def test_the_early_starter_cable_recall_is_present(self, raw):
        """A refuter found a third carburetted-era recall the research
        had missed — a fire-risk one. It is here because of that."""
        assert [e for e in raw if "oil cooler return pipe" in e["title"]]


class TestTheCrankAngleIsNotTheCoolingSplit:
    def test_the_three_air_cooled_270_models_are_named(self, raw):
        crank = [e for e in raw if "Crank angle" in e["title"]][0]
        text = _claims(crank)
        for m in TWO_SEVENTY:
            assert m in text, f"{m} not named as a 270-degree model"

    def test_no_entry_asserts_air_cooled_means_360(self, raw):
        """The assumption this phase's own plan made before the research
        corrected it. Naming it in order to correct it is required;
        asserting it is the error."""
        for e in raw:
            text = _claims(e)
            for m in re.finditer(r"air-cooled[^.]{0,60}?360", text):
                seg = text[max(0, m.start() - 90):m.end() + 90]
                assert re.search(r"natural to assume|wrong|not\b|assumption", seg, re.I), (
                    f"{e['title']}: asserts air-cooled means 360"
                )


class TestIntervalsAreTriumphCited:
    def test_only_the_valve_entry_states_intervals(self, raw):
        """Every other entry defers. This one carries figures because
        Triumph's own handbooks were opened for both generations."""
        with_figures = [
            e for e in raw
            if re.search(r"\b\d{1,3},\d{3}\s*(?:mi|miles?|km)\b", _claims(e), re.I)
        ]
        assert len(with_figures) == 1
        assert "valve job" in with_figures[0]["title"]

    def test_both_generations_intervals_are_given(self, raw):
        valve = [e for e in raw if "valve job" in e["title"]][0]
        text = _claims(valve)
        assert "12,000" in text and "20,000" in text

    def test_the_entry_attributes_them_to_triumph(self, raw):
        valve = [e for e in raw if "valve job" in e["title"]][0]
        assert re.search(r"handbook|service manual", _claims(valve), re.I)


class TestDeferralBoundaries:
    def test_no_tiger_content(self, raw):
        for e in raw:
            assert not re.search(r"\bTiger\b", _claims(e)), e["title"]

    def test_no_triple_content(self, raw):
        forbidden = r"Street Triple|Speed Triple|Daytona|\b675\b|\b765\b|\b1050\b|\btriple\b"
        for e in raw:
            hits = re.findall(forbidden, _claims(e), re.I)
            assert not hits, f"{e['title']}: {hits} belongs to Phase 228"

    def test_no_pre_hinckley_content(self, raw):
        forbidden = r"Meriden|T509|T595|pre-Hinckley"
        for e in raw:
            hits = re.findall(forbidden, _claims(e), re.I)
            assert not hits, f"{e['title']}: {hits} belongs to Phase 229"

    def test_no_fault_codes_or_tooling_content(self, raw):
        """230 owns the DTC format, TuneECU and dealer mode. Saying a
        procedure requires the dealer tool is a service fact; naming
        codes or tuning software is 230's."""
        forbidden = r"\bP0\d{3}\b|\bP1\d{3}\b|TuneECU|TuneBoy|dealer mode"
        for e in raw:
            hits = re.findall(forbidden, _claims(e), re.I)
            assert not hits, f"{e['title']}: {hits} belongs to Phase 230"
        for e in raw:
            assert e["dtc_codes"] == [], e["title"]


class TestTheAdapterGapIsLeftForItsOwner:
    """The Phase 221 pattern: a real gap that another row owns."""

    def test_the_triumph_catalog_rows_are_unchanged(self):
        matrix = json.loads(COMPAT.read_text(encoding="utf-8"))
        rows = {(r["adapter_slug"], r["model_pattern"])
                for r in matrix if r["make"] == "triumph"}
        assert ORIGINAL_TRIUMPH_ROWS <= rows, ORIGINAL_TRIUMPH_ROWS - rows

    def test_the_gap_this_phase_left_was_filled_by_its_owner(self):
        """Inverted at Phase 230, deliberately. This phase found no
        full-access Triumph option and no adapter row at all for the
        air-cooled Bonneville it documents, guarded the count, and left
        the gap for row 230. 230 filled it — so the assertion now checks
        the gap is CLOSED, and specifically that the air-cooled family
        this file covers is reachable. A guard should outlive the
        deliverable it was written for; this one outlived the absence."""
        matrix = json.loads(COMPAT.read_text(encoding="utf-8"))
        triumph = [r for r in matrix if r["make"] == "triumph"]
        assert any(r["status"] == "full" for r in triumph), "no full-access option"
        aircooled = [r for r in triumph
                     if "bonneville" in r["model_pattern"].lower()
                     and r["year_min"] < 2016]
        assert aircooled, "the air-cooled Bonneville still has no row"

    def test_the_carburetted_half_is_marked_incompatible_not_missing(self):
        """The honest answer 230 found: those machines have no engine
        control module at all, so no tool exists. An explicit
        incompatible row says that; an absent row implies we simply
        lack coverage."""
        matrix = json.loads(COMPAT.read_text(encoding="utf-8"))
        carb = [r for r in matrix
                if r["make"] == "triumph"
                and "bonneville" in r["model_pattern"].lower()
                and r["year_max"] <= 2007]
        assert carb and all(r["status"] == "incompatible" for r in carb)

    def test_the_makes_it_is_measured_against_still_have_theirs(self):
        matrix = json.loads(COMPAT.read_text(encoding="utf-8"))
        for make in ("bmw", "ducati", "ktm"):
            assert any(r["status"] == "full" for r in matrix if r["make"] == make), make


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
        "burning smell near the alternator",
        "electrical fault changes when bars are turned",
        "blown main fuse on an early america",
        "wrong generation part ordered for a t100",
        "looks carbed but has no fuel tap",
        "is this a 790 or an 865",
        "uneven beat on an air cooled triumph",
        "valve check quoted for the wrong engine",
        "cannot balance throttles with gauges",
        "cannot find the bleed screw on a t120",
        "starter spins but does not engage",
    ])
    def test_a_mechanic_query_finds_the_entry(self, db_path, needle):
        assert find_issues_by_symptom(needle, db_path), needle
