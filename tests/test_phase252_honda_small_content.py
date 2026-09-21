"""Phase 252 — Honda's small machines: the four the corpus never named.

Before this file the corpus held no row naming the Ruckus, the Metropolitan or
the PCX, and a `LIKE '%Grom%'` search returned four rows that were all the word
*grommet*. What it did hold was 142 Honda rows, every one of them `unverified`,
including one (model `All`, so it reaches every Honda ever made) carrying an
unanchored ten-entry blink-code table and a sentence beginning "Forum tip:"
inside its `fix_procedure`. So these rows are not the first Honda answer in the
corpus — they are the first Honda answer that names a document.

Most of this file is the ordinary Track L discipline: anchored or not written,
every number labelled, one row one label, a mirrored document named as mirrored,
a regulator record written as a floor. The rest guards sentences that three
refuters corrected, and those are worth naming, because each was researched,
plausible, and wrong:

* the Ruckus primary reduction printed "2.8:1 ~ 0.86:1" against
  "2.85:1 - 0.86:1" — read as Honda contradicting itself, when the hyphen form
  was **the Metropolitan's** and all four Ruckus manuals use the tilde;
* "the Ruckus gives no coolant calendar interval" — it gives two years, in a
  footnote, against the Metropolitan's three;
* one oil-spec change, when there were two (the "resource conserving" exclusion
  arrived in 2022, the SG-to-SJ change in 2024);
* a service manual said to name itself nowhere — it says "This manual describes
  the service procedures for the GROM125", once, and never says MSX at all;
* a CHF50 manual whose filename was said to contradict its edition line, when
  "2002-2006" is printed on Honda's own cover;
* and, across three separate sweeps, an HTTP 400 read as "unrecognised model
  string" when it simply means zero results — a recognised string returns it for
  the years that have no campaign.

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
from motodiag.knowledge.vehicle_resolver import known_models, resolve_vehicle

ROOT = Path(__file__).resolve().parent.parent
K = ROOT / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"
SEED = K / "known_issues_honda_small.json"

#: The concepts the roadmap row promised: the four machines, plus the modding
#: community it names explicitly.
CONCEPTS = {
    "ruckus": (r"\bRuckus\b",),
    "metropolitan": (r"\bMetropolitan\b",),
    "grom": (r"\bGrom\b|\bGROM125\b",),
    "pcx": (r"\bPCX\b",),
    "fuelling split": (r"carburett?or.*PGM-FI|PGM-FI.*carburett?or",),
    "diagnostics": (r"\bMIL\b|malfunction indicator|data link connector",),
    "service data": (r"valve clearance|spark plug|tyre pressure|tire pressure",),
    "regulator record": (r"\bcampaign\b|\brecall\b",),
    "modding community": (r"tampering|non-compliant component",),
}

#: A number in this corpus carries a unit. 248's fix: a word boundary can never
#: match after "%", so a lookahead is required.
_NUMBER = re.compile(
    r"\b\d+(?:[.,]\d+)?\s?(?:mm|cm3|km|mi|miles|psi|kPa|rpm|N-m|kgf|V|A|Ah|"
    r"qt|L|in|degrees|%)(?!\w)", re.I)

#: A Honda service-manual row names its document. Honda's own codes look like
#: 31GJP610, 31GGA6300, 31K1ZA40, 61GJB04, 61CSM00 — or the document carries a
#: dated imprint instead, which is all the GROM125 manual has.
_DOCUMENT = re.compile(
    r"\b\d{2}[A-Z]{1,4}\d{2,5}\b|owner'?s manual|service manual|"
    r"Date of Issue|press release|specification release|features release", re.I)

#: A campaign number, as the regulator writes it.
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
    """The whole corpus, so the models are derived against everything."""
    from motodiag.core.config import reset_settings

    path = str(tmp_path_factory.mktemp("p252") / "p252.db")
    init_db(path)
    for f in sorted(K.glob("known_issues_*.json")):
        load_known_issues_file(f, path)
    rebuild_make_index_at(path)
    rebuild_model_index_at(path)
    reset_settings()
    return path


# ---------------------------------------------------------------------------
# 1. The row covers what it said it would, and nothing another row owns
# ---------------------------------------------------------------------------
class TestTheRowIsCovered:
    def test_the_seed_file_loads(self, db):
        assert search_known_issues(db_path=db)

    def test_thirteen_rows_shipped(self):
        assert len(_entries()) == 13

    @pytest.mark.parametrize("concept", sorted(CONCEPTS))
    def test_each_concept_has_a_row(self, concept):
        patterns = CONCEPTS[concept]
        assert any(any(re.search(p, _text(e), re.I | re.S) for p in patterns)
                   for e in _entries()), concept

    def test_no_row_writes_the_generic_cvt_layer(self):
        """Row 254 is "Small-displacement CVT diagnostics". 252 may name a
        published belt-service indicator; it may not explain the mechanism."""
        body = _corpus().lower()
        for owned in ("variator", "roller weight", "clutch bell", "driven pulley"):
            assert owned not in body, owned

    def test_no_row_writes_the_generic_scooter_electrical_layer(self):
        """Row 256. Per-machine fuse and battery part numbers are this row's;
        how a stator charges a battery is not."""
        body = _corpus().lower()
        for owned in ("stator", "rectifier", "regulator/rectifier"):
            assert owned not in body, owned

    def test_no_row_writes_the_generic_carburettor_layer(self):
        """Row 257. 252 records THAT the Ruckus is carburetted, with the
        document that says so. Servicing the carburettor is 257's."""
        body = _corpus().lower()
        for owned in ("float bowl", "pilot screw", "main jet", "slow jet",
                      "carburettor rebuild", "carburetor rebuild"):
            assert owned not in body, owned

    def test_no_row_restates_the_other_repeat_campaign_rows(self):
        """Two rows already carry a campaign that followed a campaign: a
        Triumph radiator fan whose first repair may not have been effective,
        and 251's Vespa brake platings where the remedy failed in turn. The
        Grom's mechanism is a third one and must stand on its own."""
        body = _corpus()
        for foreign in ("Triumph", "Speed Triple", "Vespa", "Piaggio", "Aprilia"):
            assert foreign not in body, foreign


# ---------------------------------------------------------------------------
# 2. Anchored, labelled, and honest about where it was read
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
        """The corpus holds 142 Honda rows and every one is `unverified`.
        These are the first that are not."""
        assert {e["source"] for e in _entries()} <= LABELS

    def test_the_mirror_provenance_is_stated_wherever_the_grom_manual_is_cited(self):
        """Phase 246's rule. Honda publishes no service manual free, so the
        GROM125 book was read from a third-party mirror, and a row citing it
        may never imply the statement came off a Honda server."""
        citing = [e for e in _entries() if "GROM125" in e["description"]
                  and "service manual" in e["description"].lower()]
        assert citing, "expected rows citing the GROM125 service manual"
        for e in citing:
            assert re.search(r"mirror", e["description"], re.I), e["title"][:60]

    def test_a_honda_server_row_is_not_described_as_mirrored(self):
        """The owner's manuals came off Honda's own CDN. Saying otherwise
        would be as wrong as the reverse."""
        pcx = _row("PCX changed displacement three times")
        assert "Honda's own CDN" in pcx["description"]


# ---------------------------------------------------------------------------
# 3. The corrections the refuters forced
#
# Each test here is a sentence that was researched, plausible and wrong.
# ---------------------------------------------------------------------------
class TestWhatTheRefutersCorrected:
    def test_the_primary_reduction_difference_is_the_number_not_the_punctuation(self):
        """The sweep read "2.8:1 ~ 0.86:1" against "2.85:1 - 0.86:1" as Honda
        printing one spec two ways. Verified at codepoint level, all four
        Ruckus manuals use the tilde; the hyphen form is the METROPOLITAN's.
        The real disagreement is 2.8 against 2.85."""
        row = _row("What changed between Ruckus editions")
        body = row["description"]
        assert "2.8:1" in body and "2.85:1" in body
        assert body.count("~") >= 2, "both Ruckus figures must carry the tilde as printed"
        assert " - 0.86" not in body, "the hyphen form belongs to the Metropolitan"

    def test_the_oil_specification_is_two_changes_not_one(self):
        """The sweep quoted 2012 and 2022 as one identical string. They are
        not: "or resource conserving" arrived in 2022, and only then did the
        classification move SG to SJ in 2024."""
        row = _row("What changed between Ruckus editions")
        body = row["description"]
        assert "resource conserving" in body, "the first of the two changes is missing"
        assert "SG" in body and "SJ" in body
        assert "twice" in body.lower() or "two" in body.lower()

    def test_the_ruckus_coolant_interval_is_never_called_absent(self):
        """The sweep said the Ruckus gives no coolant calendar interval. It
        gives two years, in footnote 4, against the Metropolitan's three. A
        claimed absence that was really a difference — 251 met this repeatedly."""
        body = _corpus().lower()
        for banned in ("no coolant interval", "gives no coolant",
                       "no calendar interval for coolant"):
            assert banned not in body, banned

    def test_no_row_claims_a_filename_versus_edition_conflict(self):
        """The sweep said the CHF50 mirror's filename said 2002-2006 while the
        document said July 2007. Rendering the cover showed "2002-2006" printed
        on Honda's own cover, so there is no conflict — a 2007 issue date on a
        2002-2006 manual is an ordinary reprint."""
        body = _corpus().lower()
        for banned in ("filename says", "the mirror's filename", "contradicts its edition"):
            assert banned not in body, banned

    def test_the_grom_manual_is_cited_by_the_name_it_prints(self):
        """The sweep reported that the manual never names itself. It does, once:
        "This manual describes the service procedures for the GROM125". And
        "MSX" appears nowhere in its 266 pages, though the mirror's filename
        says MSX125."""
        citing = [e for e in _entries() if "Date of Issue" in e["description"]]
        assert citing, "expected rows citing the manual by its dated imprint"
        for e in citing:
            assert "GROM125" in e["description"], e["title"][:60]
        assert not re.search(r"MSX\w*\s+(?:service )?manual", _corpus(), re.I), (
            "the mirror's filename says MSX125; the document never does")

    def test_the_inverted_code_pair_ships_as_an_erratum_with_both_codes(self):
        """Honda printed 9-1 and 9-2 the opposite way round from every other
        pair in the table. Rendered at 7x and 14x: the words are unambiguous,
        so it is Honda's error and not a scan artifact. Shipping one half of
        the pair, or shipping it silently, would both mislead."""
        row = _row("eleven codes a GROM125 can show")
        body = row["description"]
        assert "9-1" in body and "9-2" in body
        assert "invert" in body.lower()
        assert re.search(r"7-1", body), "the control pair must be shown beside it"
        assert re.search(r"magnif|rendered", body, re.I), (
            "the row must say the inversion was verified, not assumed")

    def test_the_code_meanings_are_hondas_not_the_legacy_tables(self):
        """The corpus already answers a Grom FI question, through an
        `unverified` row whose model column is the wildcard. Its table says
        7 is TPS, 8 is intake air temp, 9 is coolant temp and 33 is fuel pump.
        Honda's own index for this machine says 7 is EOT, 8 is TP, 9 is IAT and
        33 is EEPROM. This row must carry Honda's meanings, not be harmonised
        toward the older ones."""
        row = _row("eleven codes a GROM125 can show")
        body = row["description"]
        assert re.search(r"7-1.{0,80}oil temperature", body, re.I | re.S)
        assert re.search(r"8-1.{0,80}throttle position", body, re.I | re.S)
        assert re.search(r"9-1.{0,80}intake air", body, re.I | re.S)
        assert re.search(r"33-2.{0,40}EEPROM", body, re.I)
        assert "coolant" not in body.lower(), "9 is intake air temperature on this machine"

    def test_the_eleven_codes_are_exactly_the_eleven_printed(self):
        row = _row("eleven codes a GROM125 can show")
        assert row["dtc_codes"] == ["7-1", "7-2", "8-1", "8-2", "9-1", "9-2",
                                    "12-1", "21-1", "33-2", "54-1", "54-2"]

    def test_the_pcx_carries_all_three_spark_plugs_or_none(self):
        """A two-way 2015-against-2025 comparison silently mis-serves every
        2020 and 2021 machine, which take a third plug the sweeps missed."""
        body = _corpus()
        plugs = ("CPR7EA-9", "MR8K-9", "LMAR8L-9")
        present = [p for p in plugs if p in body]
        assert present in ([], list(plugs)), present

    def test_no_row_presents_pcx160_as_hondas_name(self):
        """PCX160 appears in none of the Honda documents read. It is a name
        from the roadmap row's vocabulary — 251's "HiPER" lesson."""
        for e in _entries():
            body = e["description"]
            if "PCX160" in body:
                assert re.search(r"does not use the name PCX160|not use that name", body), \
                    e["title"][:60]

    def test_no_engine_family_name_is_invented(self):
        """No engine-family name appears in any of the ten Ruckus, Metropolitan
        and CHF50 documents read. eSP and eSP+ appear only in Honda press copy,
        never in an owner's manual, so neither may be presented as service
        vocabulary."""
        body = _corpus()
        for invented in ("HiPER", "Hi-PER", "eSP+", "eSP "):
            assert invented not in body, invented

    def test_the_tampering_list_is_scoped_to_the_noise_control_system(self):
        """The sweep called it "the emissions/tampering list". It sits under
        NOISE EMISSION CONTROL SYSTEM specifically, and the wider reading
        overstates what Honda claims."""
        row = _row("four acts its noise-emission section presumes to be tampering")
        body = row["description"]
        assert "noise emission control system" in body.lower()
        assert re.search(r"not to the manual'?s emissions sections generally|"
                         r"belongs to the noise emission control system specifically", body, re.I)

    def test_the_reflector_campaign_is_not_presented_as_uniform(self):
        """The 22 model rows are not uniform across 2020 and 2021: a Grom is
        covered for 2020 only. A blanket reading would clear a machine that is
        covered and cover one that is not."""
        row = _row("Two miniMOTO campaigns that are easy to misread")
        body = row["description"]
        assert "not uniform" in body.lower()
        assert re.search(r"GROM125.{0,60}2020 only", body, re.I | re.S)

    def test_the_metropolitan_symptom_sentence_is_attributed_to_the_filing(self):
        """That sentence exists only in the manufacturer's Part 573 filing,
        not in the regulator's summary. Citing it to the summary would be
        citing a document that does not contain it."""
        row = _row("Metropolitan transmission campaign")
        body = row["description"]
        assert "Abnormal sounds coming from the rear wheel area" in body
        assert re.search(r"only in the manufacturer'?s filing", body, re.I)

    def test_the_transmission_oil_row_is_a_sequence_not_a_cause(self):
        """Honda's manuals gained a transmission-oil capacity row in the 2025
        edition, and the campaign covers 2016-2025. No document read connects
        them, so the row must say so rather than implying it."""
        row = _row("Metropolitan transmission campaign")
        body = row["description"]
        assert re.search(r"no document read states any connection|none is asserted", body, re.I)


# ---------------------------------------------------------------------------
# 4. The regulator record is a floor, and says what it cannot know
# ---------------------------------------------------------------------------
class TestTheRegulatorRecordIsAFloor:
    def test_the_record_row_declares_itself_a_floor(self):
        row = _row("What the US regulator record shows")
        body = row["description"]
        assert "floor" in body.lower()
        assert re.search(r"not a census|no completeness claim", body, re.I)

    def test_no_row_claims_the_list_is_complete(self):
        """251 shipped a guard that banned a string and failed on a legitimate
        negation. So this tests the claim, not the token: a completeness
        phrase may appear only inside a sentence forbidding it."""
        for e in _entries():
            for sentence in re.split(r"(?<=[.;])\s+", _text(e)):
                low = sentence.lower()
                claim = any(p in low for p in (
                    "the complete history", "all recalls for", "every campaign affecting",
                    "recall-free", "has no recalls", "have no recalls"))
                if not claim:
                    continue
                forbidden = any(p in low for p in (
                    "do not", "never", "is not the same", "rather than",
                    "no completeness", "not a census"))
                assert forbidden, (e["title"][:50], sentence[:120])

    def test_the_ruckus_is_unverified_rather_than_clear(self):
        """Nothing was retrievable for the Ruckus. 120 lookups across five name
        spellings and 24 model years returned nothing — which is not the same
        as the machine having no campaigns."""
        row = _row("What the US regulator record shows")
        body = row["description"]
        assert re.search(r"unverified rather than clear", body, re.I)
        assert "not the same as" in body.lower()

    def test_no_row_says_a_400_means_an_unrecognised_model_string(self):
        """Three sweeps in a row concluded this and it is wrong: a recognised
        string returns the same 400 for the years that hold no campaign. The
        status carries no information about the query."""
        body = _corpus().lower()
        for banned in ("unrecognised model string", "unrecognized model string",
                       "wrong model name returns", "bad model string"):
            assert banned not in body, banned
        row = _row("What the US regulator record shows")
        assert re.search(r"as readily as for a name it does not recognise|"
                         r"ordinary empty year", row["description"], re.I)

    def test_no_row_claims_an_indexed_ruckus_recall(self):
        """A sweep reported that the regulator indexes a 2015 NPS50 recall its
        own endpoint would not serve. The record is a COMPLAINT. The endpoint
        that appeared to be a recall index takes an inert parameter."""
        body = _corpus().lower()
        for banned in ("indexes at least one", "indexed recall", "hidden recall"):
            assert banned not in body, banned


# ---------------------------------------------------------------------------
# 5. The machines are reachable — which is the point of writing them
# ---------------------------------------------------------------------------
class TestTheMachinesResolve:
    @pytest.mark.parametrize("name", [
        "Ruckus", "NPS50", "Metropolitan", "NCW50", "Giorno", "CHF50",
        "Grom", "GROM125", "PCX", "PCX150", "Monkey 125", "Super Cub C125",
        "Trail 125", "CT125",
    ])
    def test_the_machine_resolves_exactly(self, db, name):
        """Before this phase Honda's model pool was 27 entries and every one
        was 250 cm3 or larger, so all of these resolved to nothing."""
        identity = resolve_vehicle("Honda", name, db_path=db)
        assert identity.make.resolved == "Honda"
        assert identity.model.method == "exact", (name, identity.model.method)

    def test_the_honda_pool_grew_and_kept_what_it_had(self, db):
        pool = known_models("Honda", db_path=db)
        assert len(pool) > 27, len(pool)
        for kept in ("CBR1000RR", "Rebel", "Africa Twin", "GL1800 Gold Wing"):
            assert kept in pool, kept

    def test_no_other_marque_gained_these_models(self, db):
        """Every row here is single-marque, so 250C's first attribution rung
        files each token under Honda and nowhere else."""
        for other in ("Yamaha", "Kawasaki", "Suzuki"):
            pool = known_models(other, db_path=db)
            for ours in ("Ruckus", "Grom", "PCX", "Metropolitan"):
                assert ours not in pool, (other, ours)
