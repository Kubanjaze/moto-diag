"""Phase 253 — Yamaha's scooters and the Taiwanese makers.

Before this file the corpus held no row naming the Zuma, the Vino, Kymco, SYM
or Genuine. Three separate searches said otherwise and all three were wrong:
`LIKE '%SYM%'` returned 117 rows, every one of them *symptom* or *system*;
`LIKE '%Genuine%'` returned 60, every one of them *genuine part*; `%Buddy%`
returned five, none of them the scooter. Phase 252 met this once, as *grommet*.

Because two of the three new marque names are ordinary English words, the first
question was a safety question rather than a content one, and it was measured on
a copy of the live database before anything was written: adding makes literally
named `SYM` and `Genuine` does not capture prose. That check is repeated here
against the shipped rows.

The rest guards sentences three refuters corrected, and they are worth naming
because every one was researched, plausible and wrong:

* "the words Zuma and BWS appear in none of the fourteen documents" — Zuma is on
  the cover of two of them, and the sweep had cited one of those documents
  itself;
* "SYM's entire statement about Honda is one clause with no dates or models" —
  SYM's *US* host gives a year, the relationship type and two named cars;
* "Kymco and SYM print no fault codes" — they print them under their own
  vocabulary, which the search never included;
* "the Rattler 50 has a different plug gap from the Buddy 50" — the Rattler's
  own manual gives two different gaps, so the difference is a defect, not a spec;
* "campaign 04V381000 covers the Super-9" — it covers the Vitality too;
* "one of the two NIU campaigns is a do-not-ride" — both are.

Each of those has a test here.
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
from motodiag.knowledge.vehicle_resolver import known_makes, known_models, resolve_vehicle

ROOT = Path(__file__).resolve().parent.parent
K = ROOT / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"
SEED = K / "known_issues_yamaha_kymco_sym_genuine.json"

#: What the roadmap row promised: the machines, the Taiwanese makers, and
#: parts availability.
CONCEPTS = {
    "zuma": (r"\bZuma\b",),
    "vino": (r"\bVino\b",),
    "kymco": (r"\bKymco\b",),
    "sym": (r"\bSYM\b",),
    "genuine": (r"\bGenuine\b",),
    "two-stroke split": (r"two-stroke|2-stroke",),
    "fuel system": (r"carburett?or|fuel injection|injected",),
    "parts availability": (r"parts\b|dealer network|stocks millions|support",),
    "regulator record": (r"\bcampaign\b|\brecall\b",),
}

#: 248's fix: a word boundary can never match after "%", so a lookahead is
#: required. Extended here for the units these documents actually print.
_NUMBER = re.compile(
    r"\b\d+(?:[.,]\d+)?\s?(?:mm|cm3|cc|km|mi|miles|psi|kPa|kgf|rpm|Nm|N-m|V|A|Ah|"
    r"qt|L|lb|lbs|in|%)(?!\w)", re.I)

#: A service-manual row names its document. These makers use LIT numbers,
#: publication codes, part numbers, or a dated imprint.
_DOCUMENT = re.compile(
    r"LIT-\d{5}-\d{2}-\d{2}|[A-Z0-9]{3}-F\d{4}-\d{2}|T300-[A-Z0-9]+|"
    r"owner'?s manual|service manual|specification sheet|imprint|"
    r"recall portal|product page|about page", re.I)

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
    """The whole corpus, so the new marques are derived against everything."""
    from motodiag.core.config import reset_settings

    path = str(tmp_path_factory.mktemp("p253") / "p253.db")
    init_db(path)
    for f in sorted(K.glob("known_issues_*.json")):
        load_known_issues_file(f, path)
    rebuild_make_index_at(path)
    rebuild_model_index_at(path)
    reset_settings()
    return path


# ---------------------------------------------------------------------------
# 1. Coverage, and nothing another row owns
# ---------------------------------------------------------------------------
class TestTheRowIsCovered:
    def test_the_seed_file_loads(self, db):
        assert search_known_issues(db_path=db)

    def test_fourteen_rows_shipped(self):
        assert len(_entries()) == 14

    @pytest.mark.parametrize("concept", sorted(CONCEPTS))
    def test_each_concept_has_a_row(self, concept):
        patterns = CONCEPTS[concept]
        assert any(any(re.search(p, _text(e), re.I | re.S) for p in patterns)
                   for e in _entries()), concept

    def test_no_row_writes_the_generic_cvt_layer(self):
        """Row 254 owns CVT diagnostics. 253 may name a published belt
        interval; it may not explain the mechanism."""
        body = _corpus().lower()
        for owned in ("variator", "roller weight", "clutch bell", "driven pulley"):
            assert owned not in body, owned

    def test_no_row_writes_the_generic_scooter_electrical_layer(self):
        """Row 256."""
        body = _corpus().lower()
        for owned in ("stator", "rectifier", "regulator/rectifier"):
            assert owned not in body, owned

    def test_no_row_writes_the_generic_carburettor_layer(self):
        """Row 257. 253 records WHICH machines are carburetted, with the
        document that says so. Servicing the carburettor is 257's."""
        body = _corpus().lower()
        for owned in ("float bowl", "pilot screw", "main jet", "slow jet",
                      "carburettor rebuild", "carburetor rebuild"):
            assert owned not in body, owned

    def test_no_row_restates_phase_252(self):
        """252 closed hours earlier on adjacent machines — the same class,
        the same regulator, the same access problems. Its Honda rows are
        referenced, never rewritten."""
        body = _corpus()
        for foreign in ("Honda Ruckus", "Metropolitan", "Grom", "GROM125",
                        "PCX", "Super Cub", "Trail 125"):
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
        """Yamaha's 111 existing rows are all `unverified`. These are the
        first that are not."""
        assert {e["source"] for e in _entries()} <= LABELS

    def test_the_yamaha_rows_name_yamahas_own_library(self):
        """These came off Yamaha's own owner's-manual library, not a mirror,
        and the row says so rather than leaving provenance open."""
        row = _row("three different engines")
        assert "Yamaha's own owner's-manual library" in row["description"]


# ---------------------------------------------------------------------------
# 3. The corrections the refuters forced
# ---------------------------------------------------------------------------
class TestWhatTheRefutersCorrected:
    def test_the_naming_claim_is_year_dependent_not_absent(self):
        """A sweep reported that "Zuma" and "BWS" appear in none of fourteen
        documents. "Zuma" is on the cover of two of them — and the sweep had
        cited one of those documents itself. The corrected finding is that
        naming is year-dependent, which still argues for keying on the code."""
        row = _row("names itself only in some model years")
        body = row["description"]
        assert "exactly two covers" in body
        assert re.search(r"positive controls|1,711", body), (
            "the counts must carry the control that makes the zeros credible")
        # The ban is on the REFUTED claim, not on the token: "BWS appears zero
        # times" is the surviving scoped negative and a sibling test requires
        # it. So only sentences about the marketing names are checked.
        for sentence in re.split(r"(?<=[.])\s+", body):
            if not re.search(r"\bZuma\b|\bVino\b", sentence):
                continue
            low = sentence.lower()
            for banned in ("appears in none", "never appears", "in no document"):
                assert banned not in low, (banned, sentence[:100])

    def test_the_bws_zero_is_kept_because_it_survived(self):
        """BWS = 0 did survive re-checking with apostrophe variants, so it
        may ship — scoped to the documents read."""
        row = _row("names itself only in some model years")
        assert "'BWS' appears zero times in any of them" in row["description"]

    def test_the_xc50_vino_bridge_is_documented_and_scoped(self):
        """One sweep called this unanchored folklore. A refuter found the
        2007 Vino 50 manual carries XC50W on its cover and VINO on page 5 —
        the campaign's own model year. The bridge may ship; it must carry
        its scope, because by 2011 the manual drops the name."""
        row = _row("names itself only in some model years")
        body = row["description"]
        assert "08V461000" in body
        assert re.search(r"XC50W on its cover and 'VINO' on page 5", body)
        assert re.search(r"anchored for 2006 and 2007 and lapses", body)

    def test_the_sym_honda_statement_is_the_us_hosts_not_the_global_ones(self):
        """A sweep scoped to SYM's global site and concluded its whole Honda
        statement was one vague clause. SYM's US host gives a year, the
        relationship type and two named cars. The row must not carry the
        refuted version."""
        body = _corpus().lower()
        for banned in ("one clause", "cooperating with honda", "no dates, no models"):
            assert banned not in body, banned

    def test_no_row_cites_reprinted_magazine_text_as_the_makers_own(self):
        """SYM's own domain republishes third-party reviews asserting licence
        terms and an end date. Hosting is not authorship."""
        body = _corpus().lower()
        for banned in ("under license from honda", "cb125s under licence",
                       "between 1969 and 2002"):
            assert banned not in body, banned

    def test_the_fault_code_vocabulary_is_the_makers_own(self):
        """A sweep searched five standard strings, found zero, and concluded
        these makers print no codes. They do — under "error code", not
        "fault code". The row must carry the maker's vocabulary."""
        row = _row("under names no standard diagnostic vocabulary would find")
        body = row["description"]
        assert "Fi error code indicator" in body
        assert "Engine Warning Indicator" in body
        assert "EFi Trouble Indicator" in body
        assert "Fault indicator light" in body

    def test_the_scoped_zero_carries_its_coverage_caveat(self):
        """One of the twenty-one manuals has no text on 47 of its 57 pages.
        A zero from a document that cannot be searched is not a zero, and the
        row must say so rather than resting on the count."""
        row = _row("under names no standard diagnostic vocabulary would find")
        assert re.search(r"no usable text on forty-seven of its fifty-seven pages",
                         row["description"])

    def test_the_jaso_zero_is_scoped_to_kymco_not_the_corpus(self):
        """JASO is absent from the Kymco manuals but present once, in SYM's
        Wolf CR300i. A corpus-wide zero would have been wrong."""
        row = _row("under names no standard diagnostic vocabulary would find")
        body = row["description"]
        assert "JASO MA" in body and "Wolf CR300i" in body

    def test_the_rattler_gap_is_a_defect_not_a_specification(self):
        """A sweep reported the Rattler 50 and Buddy 50 as differing in plug
        gap. The Rattler's own manual gives both figures, so the divergence
        is internal to one document."""
        row = _row("introduces the wrong scooter")
        body = row["description"]
        assert re.search(r"gap twice and disagrees with itself", body)
        assert "0.6 to 0.7 mm" in body and "0.7 to 0.8 mm" in body

    def test_the_pgo_chain_ships_as_a_chain_with_its_counterweights(self):
        """The chain is documentary and strong. A manufacturing declaration
        would not be, and three facts cut against it."""
        row = _row("answerable as a chain of records")
        body = row["description"]
        assert "chain" in body.lower()
        assert re.search(r"What no document says", body)
        assert "self-selected category" in body
        assert "Each vehicle manufactured by Genuine Scooter Company" in body

    def test_pgo_residue_absence_is_not_used_to_exclude_a_model(self):
        """The residue is in three manuals and absent from three others, so
        its absence proves nothing about lineage."""
        row = _row("answerable as a chain of records")
        assert re.search(r"absence cannot be used to place a model outside",
                         row["description"])

    def test_the_super_8_name_collision_is_inside_the_documents(self):
        """A sweep called this a site-labelling defect. Kymco's site labels
        the 50X and 50R correctly and the manuals match their machines; the
        collision is in the documents' own headings."""
        row = _row("serves a 2009 carburetted manual")
        body = row["description"]
        assert re.search(r"not a defect, despite appearances", body)
        assert "50X" in body and "50R" in body

    def test_the_people_s_claim_says_fuel_injection_not_injection(self):
        """"No injection" was literally false — the manual describes
        secondary air injection. Only fuel injection is absent."""
        row = _row("serves a 2009 carburetted manual")
        body = row["description"]
        assert "which is not fuel injection" in body

    def test_the_symba_outlier_is_identified_by_its_sibling(self):
        """The Wolf 150's prose is internally consistent, which is what
        makes the Symba the outlier rather than the pair being ambiguous."""
        row = _row("three times more often than its own schedule")
        body = row["description"]
        assert "Wolf 150" in body
        assert re.search(r"lone outlier", body)

    def test_the_vitality_is_named_in_the_engine_campaign(self):
        """04V381000 covers the Vitality as well as the Super-9. A label
        naming only the Super-9 drops half the affected fleet."""
        row = _row("an engine replaced whole")
        body = row["description"]
        assert "Vitality" in body

    def test_both_niu_campaigns_are_do_not_ride(self):
        """A sweep implied only one was. Both carry the regulator's do-not-ride
        flag; only one also has an undeveloped remedy and a refund."""
        row = _row("both telling the rider to stop riding")
        body = row["description"]
        assert re.search(r"Both are park-it campaigns", body)
        assert re.search(r"no fix", body)

    def test_the_two_like_campaigns_are_not_collapsed(self):
        row = _row("an engine replaced whole")
        body = row["description"]
        assert "19V037000" in body and "20V350000" in body
        assert re.search(r"must not be collapsed", body)


# ---------------------------------------------------------------------------
# 4. The regulator record is a floor, measurably
# ---------------------------------------------------------------------------
class TestTheRegulatorRecordIsAFloor:
    def test_the_record_row_declares_itself_a_floor(self):
        row = _row("under-lists these machines")
        body = row["description"]
        assert "floor" in body.lower()
        assert re.search(r"not a census|no completeness claim", body, re.I)

    def test_the_floor_is_shown_rather_than_asserted(self):
        """The index omits four Kymco model-years and one Genuine model that
        its own campaign records cover. That is why the list is a floor."""
        row = _row("under-lists these machines")
        body = row["description"]
        assert "Vitality" in body and "Buddy Kick" in body
        assert re.search(r"retrievable by exact model string or by campaign number", body)

    def test_no_row_claims_the_list_is_complete(self):
        """251 shipped a guard that banned a string and failed on a legitimate
        negation, so this tests the claim rather than the token."""
        for e in _entries():
            for sentence in re.split(r"(?<=[.;])\s+", _text(e)):
                low = sentence.lower()
                claim = any(p in low for p in (
                    "the complete history", "all recalls for", "every campaign affecting",
                    "recall-free", "has no recalls", "have no recalls"))
                if not claim:
                    continue
                forbidden = any(p in low for p in (
                    "do not", "never", "is not", "rather than", "no completeness",
                    "not a census", "absence"))
                assert forbidden, (e["title"][:50], sentence[:120])

    def test_no_row_reads_a_400_as_an_unrecognised_model_string(self):
        """Three sweeps in Phase 252 concluded this and it is wrong. 253
        adds that the inference does not run in reverse either."""
        # The phrase itself is legitimate — the floor row has to name the case
        # in order to say it is indistinguishable. What may not appear is the
        # INFERENCE, so each sentence using the phrase must disclaim it.
        for e in _entries():
            for sentence in re.split(r"(?<=[.])\s+", _text(e)):
                low = sentence.lower()
                if not any(p in low for p in ("unrecognised model string",
                                              "unrecognized model string",
                                              "bad model string")):
                    continue
                disclaimed = any(p in low for p in (
                    "exactly the same way", "indistinguishable", "cannot",
                    "does not", "not be used", "neither"))
                assert disclaimed, (e["title"][:50], sentence[:120])
        row = _row("under-lists these machines")
        assert re.search(r"indistinguishable by response alone", row["description"])


# ---------------------------------------------------------------------------
# 5. The machines resolve — and the marque names do not capture prose
# ---------------------------------------------------------------------------
class TestTheMachinesResolve:
    @pytest.mark.parametrize("make,model", [
        ("Yamaha", "Zuma"), ("Yamaha", "Zuma 125"), ("Yamaha", "Vino"),
        ("Yamaha", "Vino 50"), ("Yamaha", "XC50A"), ("Yamaha", "GQX125N"),
        ("Kymco", "Agility"), ("Kymco", "Like 150i"), ("Kymco", "Vitality"),
        ("SYM", "Symba"), ("SYM", "Mio 50"), ("SYM", "Wolf CR300i"),
        ("Genuine", "Buddy"), ("Genuine", "Buddy Kick"),
        ("Genuine", "Roughhouse 50"), ("Genuine", "Stella"),
    ])
    def test_the_machine_resolves_exactly(self, db, make, model):
        identity = resolve_vehicle(make, model, db_path=db)
        assert identity.make.resolved == make, (make, identity.make.method)
        assert identity.model.method == "exact", (make, model, identity.model.method)

    @pytest.mark.parametrize("marque", ["Kymco", "SYM", "Genuine"])
    def test_the_new_marque_exists(self, db, marque):
        assert marque in known_makes(db), marque
        assert known_models(marque, db_path=db), marque

    @pytest.mark.parametrize("prose", ["system", "symptom", "genuine part", "systems"])
    def test_a_marque_name_that_is_an_english_word_does_not_capture_prose(self, db, prose):
        """The risk this phase was most exposed to. `SYM` sits inside 397
        rows as *system* or *symptom*, and `Genuine` inside 60 as *genuine
        part*. Measured on a copy before the rows were written, and measured
        here against the shipped rows."""
        identity = resolve_vehicle(prose, "", db_path=db)
        assert identity.make.resolved is None, (prose, identity.make.resolved)

    def test_yamahas_pool_grew_and_kept_what_it_had(self, db):
        pool = known_models("Yamaha", db_path=db)
        assert len(pool) > 23, len(pool)
        for kept in ("YZF-R1", "VMAX", "XS650", "MT-09"):
            assert kept in pool, kept

    def test_no_other_marque_gained_these_models(self, db):
        """Every row here is single-marque except one, so 250C's first
        attribution rung files each token under its own marque."""
        for other in ("Honda", "Suzuki", "Kawasaki"):
            pool = known_models(other, db_path=db)
            for ours in ("Zuma", "Buddy", "Symba", "Agility"):
                assert ours not in pool, (other, ours)
