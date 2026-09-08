"""Phase 234 — MV Agusta 4-cylinder (F4, Brutale 750/910/982/998/1078).

**A refuter caught cross-contamination between this phase and its
sibling.** The research attached the swing-arm screw campaign to the F4;
the regulator scopes it to three-cylinder models only, and a query for
the F4 returns nothing. The irony is that the finding carried its own
warning against cross-contaminating from the triples. It is not in this
file — it is in Phase 233's, where it belongs — and a test asserts the
boundary from this side.

**The shim diameter is deliberately absent.** Sources disagreed and none
was authoritative, so rather than pick one the file tells a shop to
measure an existing shim before ordering. That matters practically: a
workshop's existing Japanese shim kit may not fit, and the mismatch is
otherwise discovered with the camshafts already out.

**"Radial valve" is demystified rather than repeated.** It describes
valve *placement*; the cam lobes are ground at a compensating angle and
act on conventional bucket tappets, and the manufacturer's manual
describes an ordinary shim-under-bucket job. A claim circulating online
that these are shim-over-bucket contradicts MV's own manual, and the
file says so.
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
FOUR = K / "known_issues_mv_agusta_four.json"
TRIPLE = K / "known_issues_mv_agusta_triple.json"
COMPAT = SEED_DATA_DIR.parent.parent / "hardware" / "compat_data" / "compat_matrix.json"

DESIGNATIONS = {"F4": r"\bF4\b", "Brutale": r"Brutale", "MV": r"MV Agusta",
                "four-cylinder": r"four-cylinder", "1078": r"1078", "998": r"\b998\b"}


def _claims(e):
    return " ".join([e["title"], e["description"], e["fix_procedure"]] + e["causes"])


def _named(e, where="both"):
    text = e["title"] if where == "title" else _claims(e)
    return [n for n, p in DESIGNATIONS.items() if re.search(p, text)]


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "f.db"); init_db(path)
    load_known_issues_file(FOUR, path); return path


@pytest.fixture
def raw():
    return json.loads(FOUR.read_text(encoding="utf-8"))


class TestContent:
    def test_loads_five(self, db_path):
        assert count_known_issues(db_path=db_path) == 5

    def test_all_are_mv_agusta(self, raw, db_path):
        assert {e["make"] for e in raw} == {"MV Agusta"}
        assert len(search_known_issues(make="MV Agusta", db_path=db_path)) == 5

    def test_severity_years_procedures(self, raw):
        for e in raw:
            assert e["severity"] in {"critical", "high", "medium", "low"}
            assert 1999 <= e["year_start"] <= e["year_end"] <= 2018, e["title"]
            assert e["fix_procedure"].strip() and e["estimated_hours"] > 0, e["title"]
            assert e["parts_needed"], e["title"]


class TestTheCrossContaminationWasCaught:
    def test_the_swingarm_screw_campaign_is_not_here(self, raw):
        """A refuter found the research had attached a three-cylinder-only
        campaign to the F4; a regulator query for the F4 returns nothing.
        It lives in the Phase 233 file."""
        for e in raw:
            assert not re.search(r"swing ?arm (pin |fixing )?(screw|bolt)", _claims(e), re.I), e["title"]

    def test_it_is_in_the_triple_file_instead(self):
        """Counter-assertion: the campaign was not simply deleted."""
        triple = json.loads(TRIPLE.read_text(encoding="utf-8"))
        assert any(re.search(r"swingarm pin", _claims(e), re.I) for e in triple)

    def test_no_three_cylinder_content_here(self, raw):
        for e in raw:
            assert not re.findall(r"\bF3\b|Dragster|Turismo Veloce|counter-rotat", _claims(e)), e["title"]

    def test_no_symptom_resolves_to_both_mv_files(self, raw):
        mine = {s for e in raw for s in e["symptoms"]}
        theirs = {s for e in json.loads(TRIPLE.read_text(encoding="utf-8"))
                  for s in e["symptoms"]}
        assert not (mine & theirs), mine & theirs


class TestTheRadialValveEntry:
    def test_it_says_placement_not_mechanism(self, raw):
        rv = [e for e in raw if "Radial valve" in e["title"]][0]
        text = _claims(rv)
        assert re.search(r"placement", text, re.I)
        assert re.search(r"bucket tappets", text, re.I)

    def test_it_contradicts_the_shim_over_bucket_claim(self, raw):
        """The online claim is named in order to be corrected, which is
        the only way a reader who has seen it changes course."""
        rv = [e for e in raw if "Radial valve" in e["title"]][0]
        text = _claims(rv)
        assert re.search(r"shim-under-bucket|shim under bucket", text, re.I)
        assert re.search(r"shim-\*\*over\*\*-bucket|shim-over-bucket|over-bucket", text, re.I)
        assert re.search(r"contradicted|should not be acted on", text, re.I)

    def test_it_tells_the_shop_not_to_decline_on_the_name(self, raw):
        rv = [e for e in raw if "Radial valve" in e["title"]][0]
        assert re.search(r"do not decline|not decline the work", _claims(rv), re.I)


class TestTheShimDiameterIsDeliberatelyAbsent:
    def test_no_diameter_figure_appears(self, raw):
        """Sources disagreed and none was authoritative, so the file
        states none — and says to measure instead."""
        for e in raw:
            assert not re.search(r"\d+\.\d+\s*mm\s*(shim|diameter)", _claims(e), re.I), e["title"]
            assert not re.search(r"(shim|diameter)[^.]{0,30}\d+\.\d+\s*mm", _claims(e), re.I), e["title"]

    def test_the_entry_says_to_measure_first(self, raw):
        sh = [e for e in raw if "shim before ordering a kit" in e["title"]][0]
        text = _claims(sh)
        assert re.search(r"measure an existing shim", text, re.I)
        assert re.search(r"could not be established|not established", text, re.I)

    def test_it_warns_against_the_shelf_kit(self, raw):
        sh = [e for e in raw if "shim before ordering a kit" in e["title"]][0]
        assert re.search(r"Japanese", _claims(sh))


class TestTheBadgesAreWrongBothWays:
    def test_both_directions_are_stated(self, raw):
        b = [e for e in raw if "wrong in both directions" in e["title"]][0]
        text = _claims(b)
        assert re.search(r"1078 really is|1078 is", text, re.I)
        assert re.search(r"990[^.]{0,40}998", text)
        assert re.search(r"989[^.]{0,40}982", text)

    def test_the_two_998_engines_are_named_as_the_worst_trap(self, raw):
        b = [e for e in raw if "wrong in both directions" in e["title"]][0]
        text = _claims(b)
        assert re.search(r"two different 998", text, re.I)
        assert re.search(r"does not identify a piston", text, re.I)

    def test_the_impossible_figure_is_flagged_not_repeated(self, raw):
        """One circulating capacity does not survive the arithmetic for
        its own stated bore and stroke. It is described, not printed."""
        b = [e for e in raw if "wrong in both directions" in e["title"]][0]
        assert re.search(r"arithmetically impossible", _claims(b), re.I)
        assert "1098" not in json.dumps(raw)


class TestTheIndependentShopEntry:
    def test_it_separates_the_mechanical_from_the_parts_question(self, raw):
        ind = [e for e in raw if "independent shop" in e["title"]][0]
        text = _claims(ind)
        assert re.search(r"documented", text, re.I)
        assert re.search(r"parts", text, re.I)
        assert re.search(r"special tools", text, re.I)

    def test_it_refuses_both_the_easy_answers(self, raw):
        """Neither 'dealer only' nor 'anyone can do it' — the entry says
        what is doable and what sets the timescale."""
        ind = [e for e in raw if "independent shop" in e["title"]][0]
        assert re.search(r"declining the machine on reputation|accepting it on optimism",
                         _claims(ind), re.I)

    def test_the_brake_campaign_is_routed_by_frame_number(self, raw):
        ind = [e for e in raw if "independent shop" in e["title"]][0]
        text = _claims(ind)
        assert re.search(r"master cylinder", text, re.I)
        assert re.search(r"frame number", text, re.I)


class TestBoundariesAndSearchability:
    def test_no_campaign_number_appears(self, raw):
        blob = json.dumps(raw)
        assert not re.findall(r"\b\d{2}V\d{3}\b", blob)
        assert not re.findall(r"RM/\d{4}/\d+", blob)

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

    def test_every_entry_names_a_designation_in_title_and_body(self, raw):
        for e in raw:
            assert _named(e, "title"), f"{e['title']}: title names none"
            assert _named(e, "both"), f"{e['title']}: body names none"

    def test_provenance_and_symptom_format(self, raw):
        assert {e["source"] for e in raw} == {"service-manual"}
        for e in raw:
            assert re.search(r"[Dd]rawn from", e["description"]), e["title"]
            assert "Forum tip" not in e["fix_procedure"], e["title"]
            for s in e["symptoms"]:
                assert len(s) <= 55 and not s.endswith("."), f"{e['title']}: {s!r}"

    def test_no_title_collides_corpus_wide(self):
        titles = []
        for f in K.glob("known_issues_*.json"):
            titles += [e["title"] for e in json.loads(f.read_text(encoding="utf-8"))]
        assert len(titles) == len(set(titles))

    @pytest.mark.parametrize("needle", [
        "radial valve head on an f4",
        "what size shims does an f4 take",
        "is the brutale 990 really 990cc",
        "valve interval on an f4",
        "can an independent work on an mv agusta",
    ])
    def test_a_mechanic_query_finds_the_entry(self, db_path, needle):
        assert find_issues_by_symptom(needle, db_path), needle
