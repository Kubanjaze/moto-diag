"""Phase 254 — small-displacement CVT diagnostics, the layer three rows left alone.

251, 252 and 253 wrote the machines and each forbade `variator`, `roller weight`,
`clutch bell` and `driven pulley` in its own rows so that this one could own
them. Before this file those four terms returned zero across 1033 rows, and the
single `CVT` row and single `variator` row were the same Piaggio row.

Most of this file is the ordinary discipline. The rest guards a hypothesis that
died three times in three different shapes, which is why it is worth naming:

* "only Piaggio publishes a belt wear limit" — every maker publishes roller
  limits, in service manuals;
* "owner's manuals give intervals, service manuals give limits" — three service
  manuals carry both;
* "every belt *number* lives in a service manual" — a Bintelli owner's manual
  prints "Belt Model Gates 669MM", a *length*. What survives is narrower and
  duller: **no owner's manual publishes a belt width or wear limit**, tested
  across 34 of them.

And four refuter corrections that each reversed a sweep:

* the Kymco Agility manual contradicts itself **four** times, not three, and the
  direction of error is inconsistent, so "trust the table" is not available;
* its FILLY pages are a recycled page template in two chapters and whole-chapter
  in two others — the either/or framing was wrong;
* Piaggio's belt minimum splits by **engine displacement class**, not platform,
  and one manual prints two of the three figures on the same page;
* the regulator's index contradiction runs in **both** directions, not one.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from motodiag.core.database import init_db
from motodiag.knowledge.issues_repo import search_known_issues
from motodiag.knowledge.loader import load_known_issues_file
from motodiag.knowledge.marques import rebuild_make_index_at
from motodiag.knowledge.models import rebuild_model_index_at
from motodiag.knowledge.vehicle_resolver import resolve_vehicle

ROOT = Path(__file__).resolve().parent.parent
K = ROOT / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"
SEED = K / "known_issues_cvt.json"

#: What the roadmap row promised: belt wear, variator/clutch bells, roller
#: weights, kickstart backup.
CONCEPTS = {
    "belt wear": (r"belt.*(wear|width|limit)",),
    "variator": (r"\bvariator\b|drive pulley|movable drive face|primary sheave",),
    "clutch bell": (r"clutch bell|clutch outer|clutch housing",),
    "roller weights": (r"weight roller|roller weights|primary sheave weight",),
    "kickstart backup": (r"kick ?start",),
    "symptom linkage": (r"will not move|lack of power|creep",),
    "regulator record": (r"\bcampaign\b|\brecall\b",),
}

#: 248's fix: a word boundary can never match after "%", so a lookahead.
_NUMBER = re.compile(
    r"\b\d+(?:[.,]\d+)?\s?(?:mm|cm3|cc|km|mi|miles|rpm|Nm|N-m|kgf|kg|g|V|A|in|%)(?!\w)", re.I)

#: A service-manual row names its document: a maker's publication code, a model
#: code, or the document class in words.
_DOCUMENT = re.compile(
    r"\b6\d{5}\b|\b\d{2}[A-Z]{2}\d{6,}\b|service manual|workshop manual|"
    r"service station manual|owner'?s manual|user'?s manual|specification table", re.I)

_CAMPAIGN = re.compile(r"\b\d{2}V\d{6}\b")
LABELS = {"service-manual", "regulation"}


def _entries() -> list[dict]:
    return json.loads(SEED.read_text(encoding="utf-8"))


def _text(e: dict) -> str:
    return " ".join(str(e.get(k) or "") for k in ("title", "description", "fix_procedure"))


def _corpus() -> str:
    return " ".join(_text(e) for e in _entries())


def _row(fragment: str) -> dict:
    hits = [e for e in _entries() if fragment.lower() in e["title"].lower()]
    assert len(hits) == 1, (fragment, [e["title"][:60] for e in hits])
    return hits[0]


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    from motodiag.core.config import reset_settings

    path = str(tmp_path_factory.mktemp("p254") / "p254.db")
    init_db(path)
    for f in sorted(K.glob("known_issues_*.json")):
        load_known_issues_file(f, path)
    rebuild_make_index_at(path)
    rebuild_model_index_at(path)
    reset_settings()
    return path


# ---------------------------------------------------------------------------
# 1. Coverage, and the boundaries the rest of the track owns
# ---------------------------------------------------------------------------
#: The twelve rows Phase 254 shipped, by title. This file is shared with
#: later phases, so 254's contribution is pinned by name rather than by
#: the file's length.
TITLES_254 = frozenset({
    "What a scooter CVT is, in the makers' own words — and why searching for the word 'variator' finds nothing",
    "Three unrelated components are all called a drive belt, and a search for one returns the other two",
    "Every maker publishes a roller wear limit — in a service manual, and two of them publish it twice with different numbers",
    "The clutch side: one maker publishes an engagement speed, one publishes a 1 mm lining limit where everyone else says 2 mm",
    "No scooter owner's manual publishes a belt width or wear limit — one even prints the measuring figure with the number left off",
    "A Kymco service manual gives four CVT figures twice with different numbers, and carries three different model names in its own page headers",
    "What the makers themselves say a CVT symptom means — quoted rather than inferred",
    "Kickstart backup, and the scooter named Kick that has none",
    "No maker publishes a fault code for a CVT — the transmission is diagnosed by symptom, not by the lamp",
    "Piaggio's belt limit is three different numbers, and one manual prints two of them on the same page",
    "A CVT recall exists that no belt, pulley or variator search would find — it is filed under the word sheave",
    "What the regulator record shows for scooter CVTs — one campaign, and two indexes that disagree with each other and with the data",
})

#: Rows added to this file after 254, each named with the phase that added
#: it. An unexplained thirteenth row fails the coverage test above.
TITLES_ADDED_LATER = {
    "The regulator's two indexes contradict each other, and an empty recall answer is not a clean record":
        "255B — the general half split out of 4615",
}


class TestTheLayerIsCovered:
    def test_the_seed_file_loads(self, db):
        assert search_known_issues(db_path=db)

    def test_the_file_is_254s_twelve_plus_named_later_additions(self):
        """254 shipped twelve, and the seed file is now shared.

        Phase 255B split two of those twelve — the retained half keeps the
        original title, because the title is part of the UNIQUE identity
        index and changing it would duplicate rather than update (F129) —
        and added the half that came out. A bare `len() == 12` would have
        failed for a legitimate reason and told no one which row moved, so
        this pins 254's twelve BY TITLE and requires every later addition
        to be named with the phase that made it.
        """
        have = {e["title"] for e in _entries()}
        missing = TITLES_254 - have
        assert not missing, f"254 rows gone from the file: {sorted(missing)}"
        unaccounted = have - TITLES_254 - set(TITLES_ADDED_LATER)
        assert not unaccounted, (
            "rows in this file that neither 254 shipped nor a later phase "
            f"claimed: {sorted(unaccounted)}")
        assert len(have) == len(TITLES_254) + len(TITLES_ADDED_LATER)

    @pytest.mark.parametrize("concept", sorted(CONCEPTS))
    def test_each_concept_has_a_row(self, concept):
        patterns = CONCEPTS[concept]
        assert any(any(re.search(p, _text(e), re.I | re.S) for p in patterns)
                   for e in _entries()), concept

    def test_no_row_writes_the_twist_and_go_comparison(self):
        """Row 255 owns scooter-versus-small-motorcycle diagnostics."""
        # The phrase is legitimate as a machine descriptor — row 255 owns the
        # comparison, not the words. So this checks for a comparison.
        for e in _entries():
            for sentence in re.split(r"(?<=[.])\s+", _text(e)):
                low = sentence.lower()
                if not any(p in low for p in ("twist-and-go", "twist and go")):
                    continue
                comparing = any(p in low for p in (
                    "versus", "compared with", "unlike a manual", "differs from a manual",
                    "rather than a manual motorcycle"))
                assert not comparing, (e["title"][:50], sentence[:120])

    def test_no_row_writes_the_scooter_electrical_layer(self):
        """Row 256."""
        body = _corpus().lower()
        for owned in ("stator", "rectifier", "12v wiring", "charging circuit"):
            assert owned not in body, owned

    def test_no_row_writes_the_carburettor_service_layer(self):
        """Row 257. 254 may note that a machine is carburetted where a maker's
        own kickstart statement depends on it; servicing the carburettor is
        257's."""
        body = _corpus().lower()
        for owned in ("float bowl", "pilot screw", "main jet", "slow jet",
                      "carburettor rebuild", "carburetor rebuild", "jetting"):
            assert owned not in body, owned

    def test_no_row_restates_a_per_machine_row_from_251_to_253(self):
        """Those three rows wrote the machines. 254 references and does not
        rewrite — so the per-machine identifiers they own stay out of here."""
        body = _corpus()
        for foreign in ("Ruckus", "Metropolitan", "Grom", "GROM125", "Symba",
                        "Zuma 50F", "Vino", "HPE", "Roughhouse"):
            assert foreign not in body, foreign


# ---------------------------------------------------------------------------
# 2. Anchored and labelled
# ---------------------------------------------------------------------------
class TestEveryRowIsAnchored:
    @pytest.mark.parametrize("entry", _entries() if SEED.exists() else [],
                             ids=lambda e: e["title"][:40])
    def test_a_service_manual_row_names_its_document(self, entry):
        if entry["source"] == "service-manual":
            assert _DOCUMENT.search(entry["description"]), entry["title"][:60]

    @pytest.mark.parametrize("entry", _entries() if SEED.exists() else [],
                             ids=lambda e: e["title"][:40])
    def test_a_regulation_row_names_its_campaign_number(self, entry):
        if entry["source"] == "regulation":
            assert _CAMPAIGN.search(_text(entry)), entry["title"][:60]

    @pytest.mark.parametrize("entry", _entries() if SEED.exists() else [],
                             ids=lambda e: e["title"][:40])
    def test_a_number_is_never_unlabelled(self, entry):
        if _NUMBER.search(_text(entry)):
            assert entry["source"] in LABELS, entry["title"][:60]

    def test_nothing_is_model_generated_or_unverified(self):
        assert {e["source"] for e in _entries()} <= LABELS

    def test_the_mirror_provenance_is_stated_for_the_service_manuals(self):
        """Every service manual read for the variator work came from a
        third-party mirror — Piaggio's own server refused a plain request, and
        none of these makers publishes a service manual on its own site."""
        row = _row("in the makers' own words")
        assert re.search(r"third-party mirror", row["description"])
        assert re.search(r"none of these makers publishes a service manual on its own site",
                         row["description"])


# ---------------------------------------------------------------------------
# 3. The hypothesis that died three times
# ---------------------------------------------------------------------------
class TestTheHypothesisStaysDead:
    def test_no_row_claims_only_one_maker_publishes_a_limit(self):
        """Sweep A killed this: every maker publishes roller limits."""
        for e in _entries():
            for sentence in re.split(r"(?<=[.])\s+", _text(e)):
                low = sentence.lower()
                if "only" not in low:
                    continue
                # The dead hypothesis was about WEAR LIMITS specifically.
                if not re.search(r"wear limit|belt limit|roller limit|minimum width", low):
                    continue
                if not re.search(r"only .{0,30}(piaggio|maker|one)", low):
                    continue
                # A scoped claim naming its sample is allowed; an unscoped one is not.
                scoped = any(p in low for p in (
                    "in this set", "of the manuals read", "read for this entry",
                    "among the", "of the eight", "of the sixteen"))
                assert scoped, sentence[:140]

    def test_no_row_claims_limits_live_only_in_service_manuals(self):
        """Sweep B killed this: three service manuals carry the interval too,
        so the split is not intervals-there-limits-here."""
        row = _row("No scooter owner's manual publishes a belt width")
        body = row["description"]
        assert re.search(r"those service manuals carry intervals too", body)
        assert re.search(r"not intervals here and limits there", body)

    def test_the_belt_claim_says_width_or_wear_limit_not_number(self):
        """Refuter 3 killed the 'number' framing with a counter-example, so the
        surviving claim is narrower and must be worded as such."""
        row = _row("No scooter owner's manual publishes a belt width")
        body = row["description"]
        assert "width or a wear limit" in body or "width or wear limit" in body
        # the counter-example must be present, or the claim is overstated
        assert "669" in body, "the belt-length counter-example must ship with the claim"
        assert re.search(r"length identifying the part, not a width", body)

    def test_the_sample_behind_the_claim_is_stated(self):
        """A claim this broad is only as good as the sample, and the sample
        included image-only scans that had to be OCR'd rather than counted."""
        row = _row("No scooter owner's manual publishes a belt width")
        body = row["description"]
        assert "thirty-four" in body
        assert re.search(r"image-only scans", body)


# ---------------------------------------------------------------------------
# 4. The corrections the refuters forced
# ---------------------------------------------------------------------------
class TestWhatTheRefutersCorrected:
    def test_the_kymco_manual_has_four_contradictions_not_three(self):
        row = _row("four CVT figures twice with different numbers")
        body = row["description"]
        for item in ("weight roller", "drive face collar", "clutch lining",
                     "driven face spring"):
            assert item in body, item
        assert "15.4" in body and "12.4" in body
        assert "154.6" in body and "92.8" in body

    def test_trust_the_table_is_explicitly_ruled_out(self):
        """The direction of error is inconsistent — the table is right on the
        roller and probably wrong on the spring — so a reader must not be left
        with a shortcut the evidence does not support."""
        row = _row("four CVT figures twice with different numbers")
        body = row["description"]
        assert re.search(r"no rule that rescues this|do not run one way", body, re.I)
        assert "130.5" in body, "the sibling figure that settles the spring must ship"

    def test_the_fifth_torque_disagreement_and_the_unit_defect_ship(self):
        row = _row("four CVT figures twice with different numbers")
        body = row["description"]
        assert "5.5 to 6.5" in body
        assert re.search(r"gram-metres where kilogram-force metres are meant", body)

    def test_the_filly_pages_are_not_described_as_two_machines_documented_together(self):
        """Refuter 2: the strict odd/even alternation is a recycled page
        template, not two machines side by side — and two chapters are
        whole-chapter, where provenance really is unestablished."""
        row = _row("four CVT figures twice with different numbers")
        body = row["description"]
        assert re.search(r"not an appendix", body)
        assert re.search(r"recycled page template", body)
        assert re.search(r"odd and even folio", body)
        assert "AGIKITY" in body, "the third header spelling must ship"

    def test_the_kymco_defect_is_scoped_to_one_book(self):
        row = _row("four CVT figures twice with different numbers")
        body = row["description"]
        assert re.search(r"defect in one book, not a maker's habit", body)
        assert "People S 250" in body

    def test_the_piaggio_split_is_by_displacement_not_platform(self):
        """Sweep C claimed the figures belonged to one platform. Refuter 1
        found them in four manuals, with one printing two pairs on one page."""
        row = _row("three different numbers")
        body = row["description"]
        assert re.search(r"displacement class rather than by model family", body)
        assert "618162" in body
        assert re.search(r"same page", body)

    def test_the_counter_intuitive_direction_is_stated(self):
        """The 250/300 minimum is narrower than the 125/150 minimum, which a
        reader will get backwards if it is not said."""
        row = _row("three different numbers")
        assert re.search(r"narrower minimum than the 125 and 150", row["description"])

    def test_the_recall_is_filed_under_xc155_and_smax_is_not_claimed(self):
        """Refuter 1: 'SMAX' does not appear in the regulator's data at all."""
        row = _row("no belt, pulley or variator search would find")
        body = row["description"]
        assert "XC155" in body
        assert "SMAX" not in body and "S-MAX" not in body

    def test_the_bare_component_is_not_called_an_anomaly(self):
        """It is 10 of 1,125 campaigns with 233 colon-free — a taxonomy gap,
        not a one-off, and the sweep overstated it."""
        row = _row("no belt, pulley or variator search would find")
        body = row["description"]
        assert re.search(r"That is not unique", body)
        assert "233" in body

    def test_the_index_contradiction_is_bidirectional(self):
        """Refuter 1 corrected 'systematically omits' to a two-way defect.

        Phase 255B split this claim out of the CVT row: it was never about
        CVTs, and declaring {cvt} withheld it from every other machine.
        The claim is unchanged; only the row carrying it moved.
        """
        row = _row("two indexes contradict each other")
        body = row["description"]
        assert re.search(r"in both directions", body)
        assert "thirteen" in body and "twelve" in body
        assert re.search(r"sample and not a census", body)

    def test_the_floor_is_shown_by_the_sweeps_own_miss(self):
        """The strongest evidence that the list is a floor is that the sweep's
        own enumeration missed a campaign it had already confirmed."""
        row = _row("two indexes that disagree")
        assert re.search(r"omitted campaign 26V302000, a real 2026 Vespa campaign that the same "
                         r"sweep had already confirmed", row["description"])


# ---------------------------------------------------------------------------
# 5. The claims that must stay scoped
# ---------------------------------------------------------------------------
class TestClaimsStayScoped:
    def test_roller_limits_are_never_presented_as_transferable(self):
        row = _row("Every maker publishes a roller wear limit")
        body = row["description"]
        assert re.search(r"meaningless without the machine", body)
        assert "15.40" in body and "22.0" in body

    def test_clutch_lining_limits_are_not_merged(self):
        """Piaggio's 1 mm and everyone else's 2 mm are not interchangeable."""
        row = _row("The clutch side")
        body = row["description"]
        assert re.search(r"1 mm limit and a 2 mm limit are not interchangeable", body)

    def test_the_vocabulary_row_carries_both_word_orders(self):
        """Measured after the first load: a search for 'roller weight' returned
        zero, because every maker writes 'weight roller' and the rows had
        inherited the makers' ordering."""
        row = _row("in the makers' own words")
        body = row["description"]
        assert "roller weights" in body and "weight rollers" in body
        assert "roller weights" in row["symptoms"]

    def test_no_row_claims_a_recall_list_is_complete(self):
        """251's lesson: test the claim, scoped to a sentence, not the token."""
        for e in _entries():
            for sentence in re.split(r"(?<=[.;])\s+", _text(e)):
                low = sentence.lower()
                claim = any(p in low for p in (
                    "the only campaign", "all campaigns", "every campaign",
                    "no campaigns exist", "recall-free"))
                if not claim:
                    continue
                disclaimed = any(p in low for p in (
                    "floor", "not a census", "no claim", "do not", "not the only",
                    "lower bound"))
                assert disclaimed, (e["title"][:50], sentence[:130])

    def test_no_row_reads_an_empty_response_as_a_clean_record(self):
        # Moved to the unscoped half by Phase 255B's split; see above.
        row = _row("two indexes contradict each other")
        body = row["description"]
        assert re.search(r"cannot distinguish a wrong name from a clean record", body)
        assert re.search(r"reads exactly like a machine with no campaigns", body)

    def test_the_fault_code_zero_states_its_sample_and_its_controls(self):
        row = _row("No maker publishes a fault code")
        body = row["description"]
        assert "sixteen documents" in body
        assert re.search(r"confirmed searchable before its zero was counted", body)


# ---------------------------------------------------------------------------
# 6. The layer is reachable — which is the point of writing it
# ---------------------------------------------------------------------------
class TestTheLayerIsReachable:
    @pytest.mark.parametrize("query,minimum", [
        ("variator", 4), ("weight roller", 3), ("clutch bell", 2),
        ("kickstart", 2), ("primary sheave", 2), ("drive belt", 10),
    ])
    def test_the_vocabulary_now_returns_rows(self, db, query, minimum):
        """Before this phase: variator 1, weight roller 0, clutch bell 0,
        kickstart 0, primary sheave 0, drive belt 8 with one CVT entry."""
        rows = search_known_issues(query=query, db_path=db, limit=40)
        assert len(rows) >= minimum, (query, len(rows))

    def test_a_drive_belt_search_now_reaches_the_cvt_layer(self, db):
        """Step 0 measured eight rows for this phrase, of which exactly one
        was a CVT belt and it came last."""
        rows = search_known_issues(query="drive belt", db_path=db, limit=40)
        cvt = [r for r in rows
               if re.search(r"cvt|variator|scooter", r["title"] + r["description"], re.I)]
        assert len(cvt) >= 4, len(cvt)

    def test_no_new_marque_was_created(self, db):
        """Every make in this layer already existed. The one counter-example
        maker named in a row is cited in text and deliberately not made a
        marque, because it would carry no machines of its own."""
        from motodiag.knowledge.vehicle_resolver import known_makes
        assert "Bintelli" not in known_makes(db)

    @pytest.mark.parametrize("make,model", [
        ("Yamaha", "XC155"), ("Piaggio", "Beverly 125"), ("Kymco", "Agility 50"),
        ("Genuine", "Buddy 125"), ("Vespa", "GTS 300"),
    ])
    def test_the_machines_named_in_the_layer_resolve(self, db, make, model):
        identity = resolve_vehicle(make, model, db_path=db)
        assert identity.model.method == "exact", (make, model, identity.model.method)
