"""Phase 233 — MV Agusta 3-cylinder (F3, Brutale, Dragster, Turismo Veloce).

**Both refuters caught the same error, and the shipped file exists partly
because of it.** The research reported the Dragster's loose-rear-spoke
recall as UK-only with no US campaign, and advised checking spoke
tension. Both refuters found it in the US database, found it flagged
do-not-ride, and found the published remedy is **replacement of the rear
wheel** — because the spoke nipples' surface treatment is out of
specification, so the tightening torque cannot hold and re-tensioning
does not restore them. Following the original guidance would have left a
defective wheel on a machine under a do-not-ride campaign. The entry now
says the obvious repair is the wrong one.

**The counter-rotating crank entry declines to state the direction.** MV
markets the counter-rotation and the research established it from MV's
own material — but MV's stated direction, clockwise or anticlockwise
viewed from a named side, could not be opened from any manufacturer
document. So the entry says what the mechanic must do (establish it from
the machine's timing marks) rather than inventing the answer, which is
the Phase 224 discipline applied to a rotation instead of a cylinder.

**No campaign numbers appear**, carrying forward the decision taken at
Phase 231 after a cited reference turned out to belong to another
manufacturer entirely.
"""

from __future__ import annotations

import json
import re

import pytest

from motodiag.core.config import SEED_DATA_DIR
from motodiag.core.database import init_db
from motodiag.knowledge.issues_repo import (
    count_known_issues, find_issues_by_symptom, search_known_issues)
from motodiag.knowledge.loader import load_known_issues_file

K = SEED_DATA_DIR / "knowledge"
TRIPLE = K / "known_issues_mv_agusta_triple.json"
COMPAT = SEED_DATA_DIR.parent.parent / "hardware" / "compat_data" / "compat_matrix.json"

DESIGNATIONS = {"F3": r"\bF3\b", "Brutale": r"Brutale", "Dragster": r"Dragster",
                "Turismo Veloce": r"Turismo Veloce", "MV": r"MV Agusta",
                "triple": r"triple", "675": r"\b675\b", "798": r"\b798\b"}
UNAMBIGUOUS = {k: v for k, v in DESIGNATIONS.items()
               if k in ("Brutale", "Dragster", "Turismo Veloce", "MV")}


def _claims(e):
    return " ".join([e["title"], e["description"], e["fix_procedure"]] + e["causes"])


def _named(e, where="both"):
    text = e["title"] if where == "title" else _claims(e)
    return [n for n, p in DESIGNATIONS.items() if re.search(p, text)]


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "m.db"); init_db(path)
    load_known_issues_file(TRIPLE, path); return path


@pytest.fixture
def raw():
    return json.loads(TRIPLE.read_text(encoding="utf-8"))


class TestContent:
    def test_loads_five(self, db_path):
        assert count_known_issues(db_path=db_path) == 5

    def test_all_are_mv_agusta(self, raw, db_path):
        assert {e["make"] for e in raw} == {"MV Agusta"}
        assert len(search_known_issues(make="MV Agusta", db_path=db_path)) == 5

    def test_severity_years_procedures(self, raw):
        for e in raw:
            assert e["severity"] in {"critical", "high", "medium", "low"}
            assert 2012 <= e["year_start"] <= e["year_end"] <= 2026, e["title"]
            assert e["fix_procedure"].strip() and e["estimated_hours"] > 0, e["title"]
            assert e["parts_needed"], e["title"]

    def test_the_do_not_ride_recalls_are_the_critical_entry(self, raw):
        crit = [e for e in raw if e["severity"] == "critical"]
        assert len(crit) == 1
        assert "do-not-ride" in crit[0]["title"]


class TestTheRefutedGuidanceWasReplaced:
    def test_the_spoke_remedy_is_wheel_replacement_not_retensioning(self, raw):
        """Both refuters found the original advice would leave a
        defective wheel in service."""
        rec = [e for e in raw if "do-not-ride" in e["title"]][0]
        text = _claims(rec)
        assert re.search(r"replacement of the rear wheel|replacement wheel", text, re.I)
        assert re.search(r"re-tension\w*\s+(does not|being ineffective)|not\s+re-tension", text, re.I)

    def test_it_says_the_torque_cannot_hold(self, raw):
        """The mechanism is why re-torquing fails, and stating it stops a
        shop from trying anyway."""
        rec = [e for e in raw if "do-not-ride" in e["title"]][0]
        text = _claims(rec)
        assert re.search(r"surface treatment", text, re.I)
        assert re.search(r"cannot hold", text, re.I)

    def test_the_swingarm_bolt_fails_in_service_not_at_assembly(self, raw):
        """Also corrected: the failure is a heat-treatment defect showing
        up in service, not a bolt snapping while being torqued."""
        rec = [e for e in raw if "do-not-ride" in e["title"]][0]
        text = _claims(rec)
        assert re.search(r"heat treatment", text, re.I)
        assert re.search(r"in service", text, re.I)
        # The entry names the wrong description in order to correct it —
        # "not, as is sometimes described, a bolt that breaks while being
        # tightened". A bare pattern match reads that as the claim.
        # Thirteenth mention-versus-use slip.
        for m in re.finditer(r"break\w* (?:while|during) (?:being )?tighten", text, re.I):
            window = text[max(0, m.start() - 90):m.start()]
            assert re.search(r"\bnot\b|rather than|sometimes described", window, re.I), (
                "asserts the wrong failure mode")

    def test_no_campaign_number_appears(self, raw):
        blob = json.dumps(raw)
        assert not re.findall(r"\b\d{2}V\d{3}\b", blob)
        assert not re.findall(r"RM/\d{4}/\d+", blob)


class TestTheCounterRotationEntry:
    def test_it_states_what_does_not_change(self, raw):
        """The useful half: nothing internal is reversed, so there is
        nothing to re-clock and no reason to suspect the timing."""
        cr = [e for e in raw if "turns backwards" in e["title"]][0]
        text = _claims(cr)
        assert re.search(r"nothing to re-clock|no correction to apply", text, re.I)
        assert re.search(r"cam timing|firing order", text, re.I)

    def test_it_declines_to_state_the_direction(self, raw):
        """MV's own wording could not be opened. The entry says to get it
        from the machine rather than inventing it — the Phase 224
        discipline applied to a rotation."""
        cr = [e for e in raw if "turns backwards" in e["title"]][0]
        text = _claims(cr)
        assert re.search(r"could not be established|not established here", text, re.I)
        assert re.search(r"timing marks", text, re.I)
        assert not re.search(r"\b(clockwise|anticlockwise|counter-?clockwise)\b", text, re.I)

    def test_it_names_the_consequence_of_turning_it_wrong(self, raw):
        cr = [e for e in raw if "turns backwards" in e["title"]][0]
        text = _claims(cr)
        assert re.search(r"cam[- ]chain tensioner", text, re.I)
        assert re.search(r"back[- ]driv", text, re.I)

    def test_the_sprag_entry_is_marked_forum_sourced(self, raw):
        """It rests on owner reports, and the entry says so because there
        is no campaign and no free remedy to imply."""
        sprag = [e for e in raw if "starter clutch" in e["title"]][0]
        assert sprag["source"] == "forum"
        assert re.search(r"owner[- ]forum|owner report|commonly reported|not.{0,20}campaign",
                         _claims(sprag), re.I)


class TestTheScopeEntry:
    def test_the_national_versus_global_distinction_is_drawn(self, raw):
        scope = [e for e in raw if "understates" in e["title"]][0]
        text = _claims(scope)
        assert re.search(r"grey import|imported", text, re.I)
        assert re.search(r"build (date|window)", text, re.I)
        assert re.search(r"clean.{0,40}check", text, re.I)

    def test_neither_document_is_called_wrong(self, raw):
        """The point is that both are correct and answer different
        questions — saying one is wrong would be the easy error."""
        scope = [e for e in raw if "understates" in e["title"]][0]
        assert re.search(r"neither is wrong|both.{0,20}genuine", _claims(scope), re.I)


class TestIntervalsAreDeferred:
    def test_the_unconfirmed_figure_is_not_repeated(self, raw):
        """The widely quoted F3 interval could not be verified against
        MV's own table, so the file does not print it."""
        # Claims only. A symptom is the mechanic's own words — "quoted
        # 12000 km for the valves" is the question they arrive with, not
        # a figure the corpus states.
        for e in raw:
            assert not re.search(r"12,?000\s*km", _claims(e)), e["title"]
        iv = [e for e in raw if "service intervals" in e["title"]][0]
        assert re.search(r"could not be confirmed|not repeated here", _claims(iv), re.I)

    def test_no_clearance_specification_is_stated(self, raw):
        """Sources disagreed and none was authoritative."""
        for e in raw:
            assert not re.search(r"0\.\d{2}\s*[-–]\s*0\.\d{2}\s*mm", _claims(e)), e["title"]


class TestDeferralBoundaries:
    def test_no_four_cylinder_content(self, raw):
        """234 owns the F4 and the four-cylinder Brutales."""
        for e in raw:
            assert not re.findall(r"\bF4\b|radial valve|1078|990R", _claims(e)), e["title"]

    def test_no_aprilia_content(self, raw):
        for e in raw:
            assert not re.findall(r"Aprilia|RSV4|Tuono|Dorsoduro|Shiver", _claims(e)), e["title"]

    def test_no_tooling_or_code_content(self, raw):
        for e in raw:
            assert not re.findall(r"\bP0\d{3}\b|\bPADS\b", _claims(e)), e["title"]
            assert e["dtc_codes"] == [], e["title"]

    def test_mv_still_has_no_adapter_rows(self):
        matrix = json.loads(COMPAT.read_text(encoding="utf-8"))
        makes = {r["make"] for r in matrix}
        assert not {"mv", "mv-agusta", "mvagusta", "aprilia"} & makes
        assert "triumph" in makes


class TestTheDesignationBarAndSearchability:
    def test_every_entry_names_a_designation_in_title_and_body(self, raw):
        for e in raw:
            assert _named(e, "title"), f"{e['title']}: title names none"
            assert _named(e, "both"), f"{e['title']}: body names none"

    def test_no_other_makes_entry_scores(self):
        for f in K.glob("known_issues_*.json"):
            if "mv_agusta" in f.name:
                continue
            for e in json.loads(f.read_text(encoding="utf-8")):
                hits = [n for n, p in UNAMBIGUOUS.items() if re.search(p, json.dumps(e))]
                assert not hits, f"{f.name}: {e['title'][:40]} scores {hits}"

    def test_provenance_is_recorded_per_entry(self, raw):
        assert {e["source"] for e in raw} <= {"service-manual", "forum"}
        for e in raw:
            assert re.search(r"[Dd]rawn from", e["description"]), e["title"]
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
        "which way does an mv triple turn",
        "starter spins but engine does not turn",
        "loose rear spokes on a dragster",
        "recall check clean but bike was imported",
        "valve interval on an f3 675",
    ])
    def test_a_mechanic_query_finds_the_entry(self, db_path, needle):
        assert find_issues_by_symptom(needle, db_path), needle
