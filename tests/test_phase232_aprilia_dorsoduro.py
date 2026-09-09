"""Phase 232 — Aprilia Dorsoduro / Shiver / SR Max.

**Written from a paired research run.** Phase 231's capped 6-agent
workflow carried two questions, one per phase; this file writes from the
survivors of the second, without launching a run of its own. That is the
point of pairing — one run, two phases, the cap respected on each.

**Same make, different engine.** Phase 231 covers the 65-degree V4; this
covers the 90-degree longitudinal V-twin. The vee angle, the cylinder
identification and the rider-aid package all differ, so nothing carries
across and no symptom may resolve to both files.

**The most useful entry is a negative finding.** Chronic fuel-pump and
charging failure is widely claimed for these machines and appears in
none of three national recall databases, while two genuine safety
campaigns — a gearbox output shaft that can let the front sprocket
fastening loosen with the rear wheel able to lock, and a front brake
master cylinder that can drag or self-apply with no brake light — are
real and are what a frame number should be checked against. The entry
states the absence carefully: no such campaign in the databases
consulted, which is not the same as no such failure.

**No campaign numbers appear**, carrying forward the Phase 231 decision
taken after a cited UK reference turned out to be a Citroën recall.
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
DORSO = K / "known_issues_aprilia_dorsoduro.json"
RSV4 = K / "known_issues_aprilia_rsv4.json"
COMPAT = SEED_DATA_DIR.parent.parent / "hardware" / "compat_data" / "compat_matrix.json"

DESIGNATIONS = {"Dorsoduro": r"Dorsoduro", "Shiver": r"Shiver", "SR Max": r"SR Max",
                "V-twin": r"V-twin", "Aprilia": r"Aprilia"}
UNAMBIGUOUS = {k: v for k, v in DESIGNATIONS.items() if k in ("Dorsoduro", "Shiver", "SR Max")}


def _claims(e):
    return " ".join([e["title"], e["description"], e["fix_procedure"]] + e["causes"])


def _named(e, where="both"):
    text = e["title"] if where == "title" else _claims(e)
    return [n for n, p in DESIGNATIONS.items() if re.search(p, text)]


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "d.db"); init_db(path)
    load_known_issues_file(DORSO, path); return path


@pytest.fixture
def raw():
    return json.loads(DORSO.read_text(encoding="utf-8"))


class TestContent:
    def test_loads_five(self, db_path):
        assert count_known_issues(db_path=db_path) == 5

    def test_all_are_aprilia(self, raw, db_path):
        assert {e["make"] for e in raw} == {"Aprilia"}
        assert len(search_known_issues(make="Aprilia", db_path=db_path)) == 5

    def test_severity_years_procedures(self, raw):
        for e in raw:
            assert e["severity"] in {"critical", "high", "medium", "low"}
            assert 2007 <= e["year_start"] <= e["year_end"] <= 2020, e["title"]
            assert e["fix_procedure"].strip() and e["estimated_hours"] > 0, e["title"]
            assert e["parts_needed"], e["title"]


class TestItDoesNotCollideWithThePhase231File:
    def test_no_symptom_resolves_to_both_aprilia_files(self, raw):
        mine = {s for e in raw for s in e["symptoms"]}
        theirs = {s for e in json.loads(RSV4.read_text(encoding="utf-8"))
                  for s in e["symptoms"]}
        assert not (mine & theirs), mine & theirs

    def test_no_v4_content(self, raw):
        """231 owns the V4 machines. Same make, different engine."""
        for e in raw:
            assert not re.findall(r"RSV4|Tuono|aPRC|\bV4\b", _claims(e)), e["title"]

    def test_the_vee_angle_is_the_other_one(self, raw):
        """90 degrees here, 65 in the V4 file. Stating it prevents a
        technician carrying an angle across two Aprilia files."""
        blob = json.dumps(raw)
        assert "90-degree" in blob or "90 degree" in blob
        assert "65" not in blob

    def test_no_title_collides_corpus_wide(self):
        titles = []
        for f in K.glob("known_issues_*.json"):
            titles += [e["title"] for e in json.loads(f.read_text(encoding="utf-8"))]
        assert len(titles) == len(set(titles))


class TestTheDesignationBar:
    def test_every_entry_names_a_designation_in_title_and_body(self, raw):
        for e in raw:
            assert _named(e, "title"), f"{e['title']}: title names none"
            assert _named(e, "both"), f"{e['title']}: body names none"

    def test_no_other_makes_entry_scores(self):
        """Exempts the `european_*` cross-make files (Phase 236 on) by
        prefix — they own a comparison axis and cannot be written
        without naming the models they scope. Prefix rather than
        filename so no later cross-make phase extends a list; their
        own tests forbid model-specific failure content."""
        for f in K.glob("known_issues_*.json"):
            if ("aprilia" in f.name
                    or f.name.startswith("known_issues_european_")):
                continue
            for e in json.loads(f.read_text(encoding="utf-8")):
                hits = [n for n, p in UNAMBIGUOUS.items() if re.search(p, json.dumps(e))]
                assert not hits, f"{f.name}: {e['title'][:40]} scores {hits}"


class TestTheNegativeFinding:
    def test_it_is_present_and_scoped_carefully(self, raw):
        """The claim is that the databases consulted hold no such
        campaign — not that no such failure occurs. Over-claiming the
        absence would be the mirror of the folklore it corrects."""
        neg = [e for e in raw if "not in any recall database" in e["title"]]
        assert neg, "the negative finding was dropped"
        text = _claims(neg[0])
        assert re.search(r"databases consulted|three .{0,20}databases", text, re.I)
        assert re.search(r"fuel[- ]pump", text, re.I)

    def test_it_names_the_campaigns_that_do_exist(self, raw):
        """An absence is only useful next to the presences. Both real
        campaigns are described, so the frame-number check has a target."""
        neg = [e for e in raw if "not in any recall database" in e["title"]][0]
        text = _claims(neg)
        assert re.search(r"output shaft", text, re.I)
        assert re.search(r"master cylinder", text, re.I)
        assert re.search(r"rear wheel.{0,30}lock", text, re.I)

    def test_no_campaign_number_appears(self, raw):
        """The Phase 231 decision, carried forward after a cited UK
        reference turned out to be a Citroen recall."""
        blob = json.dumps(raw)
        assert not re.findall(r"\b\d{2}V\d{3}\b", blob)
        assert not re.findall(r"RM/\d{4}/\d+", blob)


class TestTheRideByWireEntries:
    def test_the_key_on_self_learn_is_the_stated_mechanism(self, raw):
        rbw = [e for e in raw if "self-learns at every key-on" in e["title"]][0]
        text = _claims(rbw)
        assert re.search(r"weak battery|battery", text, re.I)
        assert re.search(r"before the (machine|bike) moves|at key-on", text, re.I)

    def test_the_tracks_are_stated_not_to_be_mirrored(self, raw):
        rbw = [e for e in raw if "self-learns at every key-on" in e["title"]][0]
        assert re.search(r"not a mirrored pair|are not", _claims(rbw), re.I)

    def test_the_silent_shutdown_is_recorded(self, raw):
        """A safety layer that stops the engine while storing a code the
        dash never showed — so 'nothing on the screen' is not 'no fault'."""
        rbw = [e for e in raw if "self-learns at every key-on" in e["title"]][0]
        assert re.search(r"never (displayed|showed)|without displaying", _claims(rbw), re.I)

    def test_the_throttle_body_is_stated_non_serviceable(self, raw):
        tb = [e for e in raw if "non-serviceable assembly" in e["title"]][0]
        text = _claims(tb)
        assert re.search(r"not sold separately|complete assembly", text, re.I)
        assert re.search(r"calibration screws", text, re.I)

    def test_it_tells_the_shop_to_exclude_the_inputs_first(self, raw):
        """The parts are expensive, so the entry earns its place by
        saying what to rule out before ordering one."""
        tb = [e for e in raw if "non-serviceable assembly" in e["title"]][0]
        assert re.search(r"exclude the inputs|battery.{0,60}intake", _claims(tb), re.I)


class TestTheScooterIsSeparated:
    def test_the_sr_max_entry_exists(self, raw):
        assert [e for e in raw if "SR Max is a scooter" in e["title"]]

    def test_it_states_the_machine_class_difference(self, raw):
        sr = [e for e in raw if "SR Max is a scooter" in e["title"]][0]
        text = _claims(sr)
        assert re.search(r"machine class", text, re.I)
        assert re.search(r"continuously variable", text, re.I)
        assert re.search(r"single-cylinder", text, re.I)

    def test_it_says_nothing_transfers(self, raw):
        sr = [e for e in raw if "SR Max is a scooter" in e["title"]][0]
        assert re.search(r"shares no|nothing.{0,30}transfers|does not", _claims(sr), re.I)


class TestDeferralBoundaries:
    def test_no_mv_agusta_content(self, raw):
        for e in raw:
            assert not re.findall(r"MV Agusta|Brutale|Turismo", _claims(e)), e["title"]

    def test_no_tooling_or_code_content(self, raw):
        for e in raw:
            assert not re.findall(r"\bP0\d{3}\b|\bPADS\b", _claims(e)), e["title"]
            assert e["dtc_codes"] == [], e["title"]

    def test_235_filled_the_adapter_gap_this_phase_guarded(self):
        """Inverted at Phase 235 — see the fuller note in Phase 231's
        copy of this test. Asserts the invariant (gap filled, slug
        spelled `mv-agusta`) rather than a slug list that later phases
        would have to maintain."""
        matrix = json.loads(COMPAT.read_text(encoding="utf-8"))
        makes = {r["make"] for r in matrix}
        assert {"aprilia", "mv-agusta"} <= makes, "Phase 235 fills this gap"
        assert not {"mv", "mvagusta"} & makes, "the make slug is mv-agusta"
        assert "triumph" in makes


class TestProvenanceAndSearchability:
    def test_every_entry_is_service_manual_sourced(self, raw):
        assert {e["source"] for e in raw} == {"service-manual"}

    def test_every_entry_says_what_it_is_drawn_from(self, raw):
        for e in raw:
            assert re.search(r"[Dd]rawn from", e["description"]), e["title"]

    def test_symptoms_are_short_phrases(self, raw):
        for e in raw:
            for s in e["symptoms"]:
                assert len(s) <= 55 and not s.endswith("."), f"{e['title']}: {s!r}"

    @pytest.mark.parametrize("needle", [
        "which cylinder is front on a shiver",
        "throttle fault at key on",
        "can you replace just the throttle potentiometer",
        "chronic fuel pump failure on a shiver",
        "is the sr max the same as a shiver",
    ])
    def test_a_mechanic_query_finds_the_entry(self, db_path, needle):
        assert find_issues_by_symptom(needle, db_path), needle
