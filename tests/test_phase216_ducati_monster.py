"""Phase 216 — Ducati Monster / Streetfighter V-twins.

Two things make this file's assertions unusual.

**The guardrail inverts against the BMW block.** Three BMW entries
describe dry-clutch failures, so a check that treated "dry clutch" as
foreign hardware would reject every correct Ducati entry. Ducati's is
different hardware with the same name: an exposed multi-plate stack in
an aluminium basket behind a vented cover, replaced through the cover,
with an idle rattle that is *normal*. The BMW entries are about a
single-plate clutch oil-contaminated by a seal, diagnosed at a
bellhousing weep hole and repaired by an engine/gearbox split. So the
assertions below permit the hardware and police the *mechanism*.

**They check claims, not mentions.** These entries correctly say "there
is no bellhousing, no flywheel face and no engine/gearbox split" and
"no cam chain and no cam-chain tensioner" — the very sentences that
prove they are about the right machine. A first-pass validator flagged
those as violations. `_asserts` therefore ignores a term preceded by a
negation, and the 937 frame test requires the entry to *state* the
absence rather than merely avoid the word.
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

D_FILE = SEED_DATA_DIR / "knowledge" / "known_issues_ducati_monster.json"
BMW_R = SEED_DATA_DIR / "knowledge" / "known_issues_bmw_r_series.json"

NEGATION = re.compile(r"\bno\b|\bnot\b|unlike|never|rather than|instead of", re.I)

#: Hardware the entries IN THIS FILE may only mention in order to deny it.
#: "cam chain" — the Monster-line engines covered here (Desmodue,
#: Desmoquattro, Testastretta) are belt driven. That is NOT true of
#: Ducati generally: the Panigale's Superquadro and the V4 Desmosedici
#: Stradale use a chain-and-gear cam drive, so Phase 217 must not
#: inherit this rule. Corrected during the Phase 217 audit, where the
#: original blanket comment ("Ducatis are belt driven") was found wrong.
DENIED_ONLY = ["cam chain", "bellhousing", "gearbox split", "spline greas",
               "rear main seal"]


def _asserts(text: str, term: str) -> bool:
    """True only where `term` is a positive claim about this bike."""
    for m in re.finditer(re.escape(term), text, re.I):
        if not NEGATION.search(text[max(0, m.start() - 70):m.start()]):
            return True
    return False


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "duc.db")
    init_db(path)
    load_known_issues_file(D_FILE, path)
    return path


@pytest.fixture
def raw():
    return json.loads(D_FILE.read_text(encoding="utf-8"))


class TestContent:
    def test_loads_twelve(self, db_path):
        assert count_known_issues(db_path=db_path) == 12

    def test_all_are_ducati(self, db_path):
        assert len(search_known_issues(make="Ducati", db_path=db_path)) == 12

    def test_generations_are_covered(self, raw):
        models = " ".join(e["model"] for e in raw)
        for gen in ("M900", "S4R", "696", "821", "937", "Streetfighter 1098"):
            assert gen in models, f"no entry for {gen}"

    def test_severity_and_years(self, raw):
        for e in raw:
            assert e["severity"] in {"critical", "high", "medium", "low"}
            assert 1993 <= e["year_start"] <= e["year_end"] <= 2026, e["title"]

    def test_procedures_and_hours(self, raw):
        for e in raw:
            assert e["fix_procedure"].strip(), e["title"]
            assert e["estimated_hours"] > 0, e["title"]

    def test_only_a_no_fault_entry_may_list_no_parts(self, raw):
        """The dry-clutch rattle entry concludes 'this is normal, do not
        quote a clutch job' — requiring parts on it would be wrong."""
        for e in raw:
            if not e["parts_needed"]:
                assert re.search(r"normal|mistaken|triage", e["title"], re.I), (
                    f"{e['title']}: repair entry with no parts"
                )


class TestTheBmwDryClutchSeamHolds:
    def test_no_entry_claims_boxer_clutch_hardware(self, raw):
        for e in raw:
            blob = json.dumps(e)
            for term in DENIED_ONLY:
                assert not _asserts(blob, term), f"{e['title']}: asserts {term!r}"

    def test_the_denial_is_actually_present(self, raw):
        """Keeps the test above from passing merely because nobody
        mentioned the terms — the entries are supposed to draw the
        distinction explicitly."""
        blob = json.dumps(raw).lower()
        assert "no bellhousing" in blob or "no engine/gearbox split" in blob
        assert "no cam chain" in blob

    def test_no_ducati_title_collides_with_a_bmw_one(self, raw):
        bmw = {e["title"] for e in json.loads(BMW_R.read_text(encoding="utf-8"))}
        assert not {e["title"] for e in raw} & bmw

    def test_the_bmw_file_still_owns_its_mechanism(self):
        """Counter-assertion: the seam terms do exist in the corpus,
        just on the boxer."""
        assert "bellhousing" in BMW_R.read_text(encoding="utf-8").lower()


class TestGenerationsAreNotConfused:
    def test_no_bare_monster_model_string(self, raw):
        for e in raw:
            assert e["model"].strip() not in {"Monster", "Ducati Monster"}, e["title"]

    def test_streetfighter_v4_and_v2_are_out_of_scope(self, raw):
        """They are Panigale-derived and belong to Phase 217."""
        blob = json.dumps(raw)
        assert not re.search(r"Streetfighter V[42]\b", blob, re.I)

    def test_the_937_states_it_has_no_trellis(self, raw):
        """The 2021+ Monster is the first without one. An entry may
        discuss the trellis only to say it is absent."""
        for e in raw:
            if "937" in e["model"] and re.search(r"trellis", json.dumps(e), re.I):
                assert re.search(r"no (tubular steel )?trellis|not a trellis",
                                 json.dumps(e), re.I), e["title"]

    def test_clutch_type_is_stated_where_it_varies_by_year(self, raw):
        """1100 is dry, 1100 EVO is wet; SF 1098 dry, SF 848 wet."""
        for e in raw:
            if re.search(r"clutch", e["title"], re.I):
                assert re.search(r"\bdry\b|\bwet\b", e["model"], re.I), (
                    f"{e['title']}: clutch entry without dry/wet in the model"
                )


class TestDeferralsToLaterPhases:
    def test_no_fault_codes(self, raw):
        """Ducati codes belong to Phase 220."""
        for e in raw:
            assert e["dtc_codes"] == [], e["title"]

    def test_no_valve_service_content(self, raw):
        """Desmo service — intervals, opener/closer shims, clearances —
        belongs to Phase 219. Cam belts are in scope here."""
        for e in raw:
            t = e["title"].lower()
            assert "valve clearance" not in t and "desmo service" not in t, e["title"]
            assert "shim" not in t, e["title"]

    def test_no_ecu_or_tool_content(self, raw):
        """Marelli ECU, DDA+, DDS and CAN belong to Phase 220."""
        blob = json.dumps(raw).lower()
        for term in ("marelli", "dda+", "dds tool", "ducati diagnostic system"):
            assert term not in blob, term

    def test_cam_belts_are_in_scope_and_present(self, raw):
        titles = " ".join(e["title"].lower() for e in raw)
        assert "cam belt" in titles


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
        "cam belt overdue by age",
        "clutch drags when engine is hot",
        "belt teeth missing or frayed",
    ])
    def test_a_mechanic_query_finds_the_entry(self, db_path, needle):
        """Needles read from the shipped data. The first draft of this
        test invented three phrases and one missed — the same slip as
        Phase 214, and the reason these are quoted verbatim."""
        assert find_issues_by_symptom(needle, db_path), needle
