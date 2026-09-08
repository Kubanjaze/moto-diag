"""Phase 231 — Aprilia RSV4 / Tuono V4. Opens the Aprilia + MV block.

**The make is absent and the topic is saturated.** Aprilia returned zero
entries across 824 (four apparent hits were the Honda CBR600F file's
"F2/F3/F4" generation labels), while `V4` matches ten files, traction
control fifteen and Öhlins fifteen. So the backwards genericness test
runs at full strength: an entry that could have been written about
another make's V4 does not belong here.

**Refutation caught a phantom recall number.** The research cited
"RM/2018/049" for a brake master-cylinder campaign; in the UK dataset
that number is a *Citroën* recall, and the real campaign is a Transport
Canada one whose number had been given a UK prefix. It is not in the
shipped file, and no campaign number appears anywhere here — the entries
describe campaigns and send the reader to the frame number instead.

**And it found something better.** The research called the connecting-rod
engine recall UK-only with no US counterpart. There *is* one — but the
regulator files it under the make spelled **"APRILLA"**, so a search by
the correct spelling returns clean on a machine that may be owed a new
engine. That is the same class of finding as the Phase 228 index defect,
and it is why the entry teaches the frame-number habit.

**Twelfth mention-versus-use slip**: a boundary check for the PADS
diagnostic tool matched brake *pads*. Case-sensitive here.
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
RSV4 = K / "known_issues_aprilia_rsv4.json"
COMPAT = SEED_DATA_DIR.parent.parent / "hardware" / "compat_data" / "compat_matrix.json"

DESIGNATIONS = {"RSV4": r"RSV4", "Tuono": r"Tuono", "aPRC": r"aPRC",
                "V4": r"\bV4\b", "Aprilia": r"Aprilia", "1077": r"1077", "1099": r"1099"}
UNAMBIGUOUS = {k: v for k, v in DESIGNATIONS.items() if k in ("RSV4", "Tuono", "aPRC")}


def _claims(e):
    return " ".join([e["title"], e["description"], e["fix_procedure"]] + e["causes"])


def _named(e, where="both"):
    text = e["title"] if where == "title" else _claims(e)
    return [n for n, p in DESIGNATIONS.items() if re.search(p, text)]


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "a.db"); init_db(path)
    load_known_issues_file(RSV4, path); return path


@pytest.fixture
def raw():
    return json.loads(RSV4.read_text(encoding="utf-8"))


class TestContent:
    def test_loads_eight(self, db_path):
        assert count_known_issues(db_path=db_path) == 8

    def test_all_are_aprilia(self, raw, db_path):
        assert {e["make"] for e in raw} == {"Aprilia"}
        assert len(search_known_issues(make="Aprilia", db_path=db_path)) == 8

    def test_severity_years_procedures(self, raw):
        for e in raw:
            assert e["severity"] in {"critical", "high", "medium", "low"}
            assert 2009 <= e["year_start"] <= e["year_end"] <= 2026, e["title"]
            assert e["fix_procedure"].strip() and e["estimated_hours"] > 0, e["title"]
            assert e["parts_needed"], e["title"]

    def test_the_two_critical_entries_are_the_safety_ones(self, raw):
        crit = {e["title"] for e in raw if e["severity"] == "critical"}
        assert len(crit) == 2
        assert any("misspelled make" in t for t in crit)
        assert any("brake" in t.lower() for t in crit)


class TestTheDesignationBar:
    def test_every_entry_names_a_designation_in_title_and_body(self, raw):
        for e in raw:
            assert _named(e, "title"), f"{e['title']}: title names none"
            assert _named(e, "both"), f"{e['title']}: body names none"

    def test_no_other_makes_entry_scores(self):
        """Ten V4 files and fifteen rider-aid files already exist. Swept
        corpus-wide rather than sampled."""
        for f in K.glob("known_issues_*.json"):
            if "aprilia" in f.name:
                continue
            for e in json.loads(f.read_text(encoding="utf-8")):
                hits = [n for n, p in UNAMBIGUOUS.items() if re.search(p, json.dumps(e))]
                assert not hits, f"{f.name}: {e['title'][:40]} scores {hits}"


class TestTheRefutationsAreReflected:
    def test_no_campaign_number_appears_at_all(self, raw):
        """The research produced one phantom number (a UK prefix on a
        Canadian campaign, whose UK counterpart is a Citroën recall).
        Rather than curate numbers, the entries describe campaigns and
        route the reader to the frame number."""
        blob = json.dumps(raw)
        assert not re.findall(r"\b\d{2}V\d{3}\b", blob)
        assert not re.findall(r"RM/\d{4}/\d+", blob)

    def test_the_engine_recall_is_not_called_uk_only(self, raw):
        """Refuted: a US counterpart exists. What is true is that it is
        filed under a misspelled make."""
        blob = json.dumps(raw)
        assert not re.search(r"UK[- ]only|no NHTSA equivalent", blob, re.I)
        rec = [e for e in raw if "misspelled make" in e["title"]][0]
        assert "APRILLA" in _claims(rec), "the actual finding is missing"

    def test_the_misspelling_entry_teaches_the_frame_number_habit(self, raw):
        rec = [e for e in raw if "misspelled make" in e["title"]][0]
        text = _claims(rec)
        assert re.search(r"frame number", text, re.I)
        assert re.search(r"clean (search|result)|no answer", text, re.I)

    def test_no_sensor_gap_figure_is_generalised(self, raw):
        """Refuted: the gap is generation-dependent, so the entry says
        to read it from the model's manual rather than printing one."""
        blob = json.dumps(raw)
        assert not re.search(r"0\.5\s*[-–]\s*2\.0", blob)
        cal = [e for e in raw if "recalibrated" in e["title"]][0]
        assert re.search(r"read.{0,40}from the manual|specified per model|not identical",
                         _claims(cal), re.I)


class TestTheAprilaSpecificFacts:
    def test_the_1100_badge_is_debunked_with_both_capacities(self, raw):
        cap = [e for e in raw if "1100cc" in e["title"]][0]
        text = _claims(cap)
        assert "1077" in text and "1099" in text
        assert re.search(r"bore only|bore-only", text, re.I)
        assert re.search(r"stroke only|stroke-only", text, re.I)

    def test_the_concurrent_sale_trap_is_stated(self, raw):
        cap = [e for e in raw if "1100cc" in e["title"]][0]
        assert re.search(r"same time|concurrent|beside", _claims(cap), re.I)

    def test_cylinder_one_is_the_left_rear_and_banks_alternate(self, raw):
        cyl = [e for e in raw if "left REAR" in e["title"]][0]
        text = _claims(cyl)
        assert re.search(r"1 and 3.{0,30}rear", text, re.I)
        assert re.search(r"2 and 4.{0,30}front", text, re.I)

    def test_the_vee_angle_is_stated_as_65(self, raw):
        blob = json.dumps(raw)
        assert "65-degree" in blob or "65 degree" in blob
        assert re.search(r"never 90|not the 90", blob, re.I)

    def test_the_cam_drive_and_service_positions_are_stated(self, raw):
        cam = [e for e in raw if "cam drive" in e["title"]][0]
        text = _claims(cam)
        assert re.search(r"intake camshaft only|only the intake", text, re.I)
        assert "150" in text and "450" in text
        assert re.search(r"not.{0,30}180|180-degree increments", text, re.I)

    def test_the_three_normal_aprc_behaviours_are_all_present(self, raw):
        aprc = [e for e in raw if "look like faults" in e["title"]][0]
        text = _claims(aprc)
        assert re.search(r"dyno|rear stand|burnout", text, re.I)
        assert re.search(r"pit[- ]lane", text, re.I)
        assert re.search(r"two seconds|two minutes", text, re.I)

    def test_the_generator_families_are_stated_as_indistinguishable(self, raw):
        chg = [e for e in raw if "owner consensus" in e["title"]][0]
        text = _claims(chg)
        assert re.search(r"two.{0,40}generator families|not interchangeable", text, re.I)
        assert re.search(r"generator cover", text, re.I)
        assert re.search(r"not.{0,20}(a )?(recall|campaign)|no free remedy", text, re.I)


class TestDeferralBoundaries:
    def test_no_phase_232_models(self, raw):
        for e in raw:
            assert not re.findall(r"Dorsoduro|Shiver|SR Max", _claims(e)), e["title"]

    def test_no_mv_agusta_content(self, raw):
        for e in raw:
            assert not re.findall(r"MV Agusta|Brutale|Turismo", _claims(e)), e["title"]

    def test_no_tooling_or_code_content(self, raw):
        """235 owns the tools and codes. Checked case-sensitively — an
        earlier version matched brake *pads* against the PADS tool."""
        for e in raw:
            assert not re.findall(r"\bP0\d{3}\b|\bPADS\b", _claims(e)), e["title"]
            assert e["dtc_codes"] == [], e["title"]

    def test_aprilia_and_mv_still_have_no_adapter_rows(self):
        """The gap row 235 owns. Guarded at zero here, as 221 and 226
        guarded theirs, with a counter-assertion that other makes have
        rows so the zero means something."""
        matrix = json.loads(COMPAT.read_text(encoding="utf-8"))
        makes = {r["make"] for r in matrix}
        assert not {"aprilia", "mv", "mv-agusta", "mvagusta"} & makes
        for other in ("bmw", "ducati", "ktm", "triumph"):
            assert other in makes, other


class TestProvenanceAndSearchability:
    def test_every_entry_is_service_manual_sourced(self, raw):
        assert {e["source"] for e in raw} == {"service-manual"}

    def test_every_entry_says_what_it_is_drawn_from(self, raw):
        for e in raw:
            assert re.search(r"[Dd]rawn from", e["description"]), e["title"]

    def test_no_entry_fabricates_a_forum_tip(self, raw):
        for e in raw:
            assert "Forum tip" not in e["fix_procedure"], e["title"]

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
        "is the rsv4 1100 really 1100cc",
        "which cylinder is number 1 on an rsv4",
        "cam timing on an aprilia v4",
        "aprc light on after a dyno run",
        "traction control wrong after new tyres",
        "no recalls found for this aprilia",
        "pads measure fine but brake is poor",
        "which generator does this aprilia have",
    ])
    def test_a_mechanic_query_finds_the_entry(self, db_path, needle):
        assert find_issues_by_symptom(needle, db_path), needle
