"""Phase 251 — Vespa and Piaggio: a new marque, anchored per document.

Track M opens on an empty subject: before this file the corpus held no
Vespa row, nothing on CVT, variator or roller weights, and nothing on the
MP3's tilting front end. The five Piaggio mentions it did hold came
sideways through Track K's Aprilia and Moto Guzzi work, and four of them
are the Group's dealer tooling — so the tooling was written and the
machines were not.

Most of this file is the ordinary Track L discipline: every row anchored
to a document named in its description, every number labelled, one row one
label. The rest is unusual, and worth explaining. Three refuters re-fetched
every page these rows cite, and what they corrected was never a figure —
the intervals, the pinout, the 10-bar threshold and the wear limits all
survived — but the *glosses* the sweeps had wrapped around them:

* a brake bulletin described as replacing an "ineffective" procedure, when
  Piaggio wrote only that the new one "improves the bleeding effectiveness";
* a bench sentence read as "the system fails safe locked by design", which
  the owner's manual contradicts for in-service failures;
* a two-state lamp decode that is really three states, with an audible
  alarm as the discriminator;
* a pre-delivery fluid check presented as scheduled maintenance;
* "four campaigns, one defect", when the fourth is a different plating —
  the one that had replaced the first, failing in turn;
* a universal negative about engine names, drawn from four manuals chosen
  where those names would never appear.

Each of those has a test here, because each was a plausible sentence that
a reader could not have distinguished from the verified ones.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from motodiag.core.database import init_db
from motodiag.knowledge.issues_repo import search_known_issues
from motodiag.knowledge.loader import load_known_issues_file
from motodiag.knowledge.marques import rebuild_make_index_at
from motodiag.knowledge.models import rebuild_model_index_at
from motodiag.knowledge.vehicle_resolver import known_makes, known_models, resolve_vehicle

ROOT = Path(__file__).resolve().parent.parent
K = ROOT / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"
SEED = K / "known_issues_vespa_piaggio.json"

#: The concepts the row promised to cover.
CONCEPTS = {
    "service schedule": (r"\bdrive belt\b", r"\binterval\b"),
    "manual availability": (r"frame number|frame/chassis number|VIN-gated|request form|dealer",),
    "diagnostic access": (r"\bOBD port\b|diagnostic tool|six pins|six-pin",),
    "tilting three-wheeler": (r"roll lock|tilting|tilt lock",),
    "regulator record": (r"campaign|recall",),
    "cvt": (r"\bbelt\b.*\bwidth\b|variator|driven half-pulley|driven pulley",),
    "engine families": (r"i-Get|hpe|Hi-PER2",),
}

#: A number in this corpus carries a unit. 248 fixed the trailing-\b bug:
#: a word boundary can never match after "%", so the lookahead is required.
_NUMBER = re.compile(
    r"\b\d+(?:[.,]\d+)?\s?(?:mm|cm3|km|mi|Nm|V|kOhm|Ohm|rpm|bar|A|kW|%|degrees?)(?!\w)", re.I)

#: A service-manual row names its document. Piaggio codes look like
#: 1Q000478, 664503, 633225, EVPP000USC, or a named communication.
_DOCUMENT = re.compile(
    r"1Q\d{6}|6\d{5}|EVPP\w+|ESCA\w+|ECP\w+|owner'?s manual|service station manual|"
    r"workshop manual|parts catalogue|technical communication|dealer bulletin|owner letter",
    re.I)

#: An NHTSA campaign number, as the regulator writes it.
_CAMPAIGN = re.compile(r"\b\d{2}V\d{6}\b")

LABELS = {"service-manual", "forum", "regulation", "model-generated", "unverified"}


def _entries() -> list[dict]:
    return json.loads(SEED.read_text(encoding="utf-8"))


def _text(e: dict) -> str:
    return " ".join(str(e.get(k) or "") for k in ("title", "description", "fix_procedure"))


def _row(fragment: str) -> dict:
    """The one row whose title contains this fragment."""
    hits = [e for e in _entries() if fragment.lower() in e["title"].lower()]
    assert len(hits) == 1, (fragment, [e["title"][:50] for e in hits])
    return hits[0]


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    """The whole corpus, so the new marques are derived against everything."""
    from motodiag.core.config import reset_settings

    path = str(tmp_path_factory.mktemp("p251") / "p251.db")
    init_db(path)
    for f in sorted(K.glob("known_issues_*.json")):
        load_known_issues_file(f, path)
    rebuild_make_index_at(path)
    rebuild_model_index_at(path)
    reset_settings()
    return path


# ---------------------------------------------------------------------------
# 1. The row covers what it said it would
# ---------------------------------------------------------------------------
class TestTheRowIsCovered:
    def test_the_seed_file_loads(self, db):
        assert search_known_issues(db_path=db)

    @pytest.mark.parametrize("concept", sorted(CONCEPTS))
    def test_each_concept_has_a_row(self, concept):
        patterns = CONCEPTS[concept]
        assert any(any(re.search(p, _text(e), re.I) for p in patterns)
                   for e in _entries()), concept

    def test_ten_rows_shipped(self):
        assert len(_entries()) == 10

    def test_no_row_restates_track_ks_piaggio_tooling(self):
        """PADS, DiagCode and the shared parts catalogue are already shipped
        rows under Aprilia and Moto Guzzi. 251 references them; it does not
        write them again."""
        for e in _entries():
            body = _text(e)
            assert "PADS" not in body, e["title"][:50]
            assert "DiagCode" not in body, e["title"][:50]


# ---------------------------------------------------------------------------
# 2. Anchored, labelled, and honest about where it was read
# ---------------------------------------------------------------------------
class TestEveryRowIsAnchored:
    @pytest.mark.parametrize("entry", _entries() if SEED.exists() else [],
                             ids=lambda e: e["title"][:40])
    def test_a_service_manual_row_names_its_document(self, entry):
        if entry["source"] == "service-manual":
            assert _DOCUMENT.search(entry["description"]), entry["title"][:50]

    @pytest.mark.parametrize("entry", _entries() if SEED.exists() else [],
                             ids=lambda e: e["title"][:40])
    def test_a_regulation_row_names_its_campaign_number(self, entry):
        if entry["source"] == "regulation":
            assert _CAMPAIGN.search(_text(entry)), entry["title"][:50]

    @pytest.mark.parametrize("entry", _entries() if SEED.exists() else [],
                             ids=lambda e: e["title"][:40])
    def test_a_number_is_never_unlabelled(self, entry):
        if _NUMBER.search(_text(entry)):
            assert entry["source"] in {"service-manual", "regulation", "forum"}, entry["title"][:50]

    def test_nothing_is_model_generated_or_unverified(self):
        assert {e["source"] for e in _entries()} <= {"service-manual", "regulation"}

    def test_the_mirror_provenance_is_stated_where_it_applies(self):
        """Phase 246's rule: a row read from a mirror copy says so. Piaggio
        serves its own documents 403 to every non-browser client, so most of
        these were read from mirrors — and a row may never imply the
        statement came off a Piaggio server."""
        mirrored = [e for e in _entries()
                    if re.search(r"1Q\d{6}|66\d{4}|633\d{3}", e["description"])]
        assert mirrored, "expected rows citing Piaggio document codes"
        assert any(re.search(r"mirror", e["description"], re.I) for e in mirrored)

    def test_no_forum_row_exists(self):
        """The only community source found had no readable page date, so under
        the rule it cannot carry a row. 249 shipped no forum row for the same
        reason."""
        assert not [e for e in _entries() if e["source"] == "forum"]


# ---------------------------------------------------------------------------
# 3. The corrections the refuters forced
#
# Each test here corresponds to a sentence that was researched, plausible,
# and wrong. They are the reason this phase ran a refuter per document.
# ---------------------------------------------------------------------------
class TestWhatTheRefutersCorrected:
    def test_no_row_calls_the_superseded_brake_procedure_ineffective(self):
        """Piaggio wrote that the new procedure "improves the bleeding
        effectiveness". The words ineffective, failed and defective appear
        nowhere in that communication. On a brake document, the stronger
        claim is a liability the source does not make."""
        for e in _entries():
            body = _text(e).lower()
            if "bleed" in body:
                for word in ("ineffective", "did not work", "defective procedure"):
                    assert word not in body, (e["title"][:40], word)

    def test_the_fail_safe_sentence_never_appears_without_its_scope(self):
        """"If this is not successful, the tilt locking mechanism remains
        locked for safety" is a real quote — about a bench potentiometer
        reset. Generalised, it says the opposite of what the owner's manual
        documents for an in-service failure: the lock disengaged, with a
        30 km/h cap. The quote may ship; the generalisation may not."""
        for e in _entries():
            body = _text(e).lower()
            assert "fails safe locked" not in body, e["title"][:40]
            if "remains locked for safety" in body:
                assert "bench" in body, (e["title"][:40], "quote shipped without its scope")
                assert "in service" in body or "disengaged" in body, e["title"][:40]

    def test_the_lamp_decode_carries_three_states_and_the_alarm(self):
        """A two-state decode — flashing means failure, steady means rider —
        is what the sweep reported and it is wrong: steady WITH the
        continuous alarm is a stuck lock. The discriminator is the sound."""
        row = _row("failure lamp means two different things")
        decode = row["description"].lower()
        assert "alarm" in decode, (
            "the discriminator must be in the decode itself, not only the title")
        assert "flashing" in decode and "steady" in decode
        assert "stuck" in decode
        assert row["fix_procedure"].lower().count("alarm") >= 1, (
            "a technician reading the procedure must be told to listen")

    def test_no_row_schedules_the_roll_lock_fluid_level(self):
        """It is a pre-delivery levels check. Presenting it as scheduled
        would invent a maintenance item; the only scheduled roll-lock entry
        is adjusting the caliper control cable."""
        for e in _entries():
            body = _text(e).lower()
            if "fluid" in body and "roll lock" in body or "tilt" in body and "fluid level" in body:
                assert "pre-delivery" in body or "scheduled" not in body, e["title"][:40]

    def test_the_reset_is_three_steps_and_names_the_last_one(self):
        """The sweep stopped at the lower stop search — step one of three —
        and omitted the potentiometer reset, which is the step the manual's
        own caution attaches to."""
        row = _row("three-step reset")
        body = _text(row).lower()
        assert "potentiometer reset" in body
        assert "three steps" in body or "three-step" in body

    def test_the_brake_campaigns_row_names_both_platings(self):
        """One supplier and one failure mode, but two plating processes: the
        zinc-nickel lines were the fix for the zinc ones, and failed in turn.
        Flattening it to one defect is contradicted by the filing itself."""
        row = _row("two different platings")
        body = _text(row).lower()
        assert "zinc-nickel" in body or "zinc/nickel" in body
        assert body.count("zinc") >= 2

    def test_the_exhaust_row_carries_both_vocabularies(self):
        """NHTSA's summary says bushing; every Piaggio document says gasket.
        A technician searches with the service literature's word."""
        row = _row("exhaust gasket")
        body = _text(row).lower()
        assert "gasket" in body and "bushing" in body

    def test_the_regulator_row_refuses_to_claim_completeness(self):
        """NHTSA's index flags model years its own endpoints will not return,
        including a 2006-2007 LX150 window. That is unverified, not
        recall-free."""
        row = _row("what the US regulator record covers")
        body = _text(row).lower()
        assert "unverified" in body
        assert "near-complete" in body or "incomplete" in body
        for absolute in ("every recall", "all recalls", "complete history"):
            assert absolute not in body, absolute

    def test_the_engine_family_row_scopes_its_negative(self):
        """"Quasar appears in no Piaggio document" cannot be established by
        four manuals chosen where it would never appear. The row says which
        documents were searched."""
        row = _row("Engine family names")
        body = _text(row).lower()
        assert "quasar" in body
        named = [m for m in ("beverly 125", "fly 125-150", "typhoon 50", "mp3 400")
                 if m in body]
        assert len(named) >= 3, (
            "the row must name the documents its negative was drawn from", named)
        # A negative about Piaggio's documents is allowed — it just has to say
        # which documents. "No Piaggio document read for this entry maps engine
        # families to model years" is scoped and true; "Quasar appears in no
        # Piaggio document" is a universal four manuals cannot establish.
        scopes = ("read for this entry", "read here", "manuals checked",
                  "those four", "these four", "read for this row")
        for sentence in re.split(r"(?<=[.!?])\s+", body):
            if re.search(r"no piaggio (?:document|publication)|any piaggio document", sentence):
                assert any(scope in sentence for scope in scopes), (
                    "unscoped universal negative", sentence[:100])

    def test_no_row_claims_these_machines_speak_obd_two(self):
        """Piaggio writes "OBD port" and documents six pins. The row is
        allowed — required, really — to say that no document uses OBD-II,
        J1962 or EOBD; what it may not do is assert the standard applies.
        So the terms may appear only inside a negation."""
        claim = re.compile(
            r"(?:follows|complies with|conforms to|compliant with|supports|uses|is|are)\s+"
            r"(?:the\s+)?(?:OBD-II|OBD2|J1962|EOBD)", re.I)
        for e in _entries():
            body = _text(e)
            found = claim.search(body)
            assert not found, (e["title"][:40], found and found.group(0))
            for sentence in re.split(r"(?<=[.!?])\s+", body):
                if re.search(r"OBD-II|OBD2|J1962|EOBD", sentence):
                    assert re.search(r"\bno\b|\bnot\b|\bnever\b", sentence, re.I), (
                        e["title"][:40], sentence[:90])


# ---------------------------------------------------------------------------
# 4. A new marque, reachable the day it lands
# ---------------------------------------------------------------------------
class TestTheNewMarquesResolve:
    @pytest.mark.parametrize("marque", ["Vespa", "Piaggio"])
    def test_the_marque_is_derived_from_the_corpus(self, db, marque):
        assert marque in known_makes(db)

    @pytest.mark.parametrize("marque", ["Vespa", "Piaggio"])
    def test_the_marque_has_models(self, db, marque):
        assert known_models(marque, db_path=db)

    @pytest.mark.parametrize("marque,model", [
        ("Vespa", "GTS 300"), ("Vespa", "GTS 310 HPE"),
        ("Piaggio", "MP3 500"), ("Piaggio", "Beverly 125"),
    ])
    def test_a_machine_resolves_to_its_model(self, db, marque, model):
        """250C keys the model vocabulary by derived marque, so a new
        marque's models are reachable as soon as its rows land — provided
        the make column names the marque plainly, which is why these rows
        are written the way they are."""
        resolution = resolve_vehicle(marque, model, db_path=db)
        assert resolution.make.applied and resolution.model.applied, (
            marque, model, resolution.model.method)

    @pytest.mark.parametrize("term", ["drive belt", "roll lock", "i-Get"])
    def test_kb_search_reaches_the_row_with_its_label(self, db, monkeypatch, term):
        from motodiag.cli.main import cli
        from motodiag.core.config import reset_settings

        monkeypatch.setenv("MOTODIAG_DB_PATH", db)
        monkeypatch.setenv("COLUMNS", "220")
        reset_settings()
        try:
            out = CliRunner().invoke(cli, ["kb", "search", term]).output
        finally:
            reset_settings()
        assert term.split()[0].lower() in out.lower(), out[-600:]
        assert any(label in out for label in LABELS), "the label travels with the row"
