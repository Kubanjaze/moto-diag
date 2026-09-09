"""Phase 238 — European valve service intervals, compared across makes.

Every interval here carries a manufacturer document, and two independent
refuter passes re-read the schedule tables visually. The phase also
corrects one shipped Phase 225B claim and closes one Phase 234 deferral.
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
K = ROOT / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"
FILE = K / "known_issues_european_intervals.json"
KTM_ADV = K / "known_issues_ktm_adventure.json"


@pytest.fixture(scope="module")
def raw():
    return json.loads(FILE.read_text(encoding="utf-8"))


def _claims(e):
    return " ".join([e["title"], e["description"], e["fix_procedure"]] + e["causes"])


class TestFileShape:
    def test_thirteen_entries(self, raw):
        assert len(raw) == 13

    def test_symptoms_are_short_phrases(self, raw):
        for e in raw:
            for s in e["symptoms"]:
                assert len(s) <= 55 and not s.endswith("."), f"{e['title']}: {s!r}"

    def test_every_entry_says_what_it_is_drawn_from(self, raw):
        for e in raw:
            assert re.search(r"[Dd]rawn\b[\w' ]{0,16}\bfrom", e["description"]), e["title"]

    def test_no_forum_entries_here(self, raw):
        """Every interval rests on a manufacturer document. The one
        owner-report figure (a shim diameter) is labelled inside an
        entry whose own claim is the document's absence."""
        assert {e["source"] for e in raw} <= {"service-manual", "model-generated"}
        # Rule 3 as a biconditional (Phase 240B). These two files hold no
        # `forum` entry, so the negative half alone was correct by accident;
        # keyed off `source` it stays correct if one is ever added.
        for e in raw:
            assert ("Forum tip" in e["fix_procedure"]) == (e["source"] == "forum"), e["title"]

    def test_no_title_collides_corpus_wide(self):
        titles = []
        for f in K.glob("known_issues_*.json"):
            titles += [e["title"] for e in json.loads(f.read_text(encoding="utf-8"))]
        assert len(titles) == len(set(titles))


class TestEveryFigureCarriesItsDocument:
    def test_every_entry_that_prints_an_interval_names_its_document(self, raw):
        """An interval without its document is the failure mode this
        phase exists to avoid. The document is established by the
        entry's opening "Drawn from" sentence for every figure in it, so
        the rule is per entry: any entry printing a km/mile figure must
        name a manual, handbook, sheet, poster, table or page in its
        description. (A first draft checked a ±400-character window per
        figure and failed an entry whose document sat 410 characters
        before the number.)"""
        doc = r"(manual|handbook|sheet|poster|table|page|document|Rider)"
        for e in raw:
            if re.search(r"\d{1,3},\d{3}\s*(km|mi|miles)", _claims(e)):
                assert re.search(doc, e["description"], re.I), f"{e['title']}: prints an interval but names no document"

    def test_unconfirmed_figures_are_labelled(self, raw):
        e = next(x for x in raw if "Aprilia" in x["title"])
        assert re.search(r"unconfirmed|could not be opened|not openable", _claims(e))


class TestTheSiblingTestAndItsException:
    def test_mv_is_named_as_the_documented_exception(self, raw):
        e = raw[0]
        text = _claims(e)
        assert "12,000 km" in text and "30,000 km" in text
        assert re.search(r"same engine, overlapping years", text)
        for model in ("Brutale 800", "Turismo Veloce", "F3"):
            assert model in text, model

    def test_the_other_makes_are_stated_to_agree(self, raw):
        text = _claims(raw[0])
        for pair in ("373cc", "399cc", "890", "Scrambler 800 and Monster 797", "Trident 660"):
            assert pair in text, pair


class TestThe225BCorrection:
    def test_the_correction_is_its_own_entry(self, raw):
        e = next(x for x in raw if "373cc versus 399cc" in x["title"])
        text = _claims(e)
        assert "15,000 km" in text and "20,000 km" in text
        assert re.search(r"corrected here", text)

    def test_the_225b_entry_no_longer_claims_a_shorter_sibling_interval(self):
        raw225b = json.loads(KTM_ADV.read_text(encoding="utf-8"))
        e = next(x for x in raw225b if "service schedule" in x["title"])
        text = " ".join([e["title"], e["description"], e["fix_procedure"]] + e["causes"])
        assert not re.search(r"shorter interval than the 390 Duke", text)
        assert re.search(r"corrected at Phase 238", text)
        assert "share an engine and its valve interval" in e["title"]

    def test_the_225b_entry_keeps_what_was_true(self):
        raw225b = json.loads(KTM_ADV.read_text(encoding="utf-8"))
        e = next(x for x in raw225b if "service schedule" in x["title"])
        text = " ".join([e["description"]] + e["causes"])
        assert "dusty-conditions" in text
        assert "clutch lubrication oil nozzle" in text
        assert "deliberately not reproduced" in e["fix_procedure"]


class TestTheOtherCorrectionsRefutationForced:
    def test_mv_coupon_ladder_has_the_merged_first_cell(self, raw):
        e = next(x for x in raw if "coupon ladder" in x["title"])
        text = _claims(e)
        assert re.search(r"A.{0,60}merged cell", text)
        assert "B 15,000" in text and "H 105,000" in text

    def test_f3_2020_figure_resolves_the_234_deferral(self, raw):
        e = next(x for x in raw if "coupon ladder" in x["title"])
        assert re.search(r"F3 675/800 MY2020.{0,80}30,000 km", _claims(e))

    def test_ducati_oil_service_is_not_quoted_as_one_range(self, raw):
        e = next(x for x in raw if "six-minute units" in x["title"])
        text = _claims(e)
        assert "1 h 12–1 h 36" not in text
        assert re.search(r"Group 3 has no oil-service column", text)

    def test_shim_diameter_stays_unprinted_as_a_spec(self, raw):
        e = next(x for x in raw if "shim diameter" in x["title"])
        text = _claims(e)
        assert "7.48 mm" in text
        assert re.search(r"owner report", text)
        assert re.search(r"no diameter|not a specification", text)

    def test_job_types_carry_their_provenance(self, raw):
        e = next(x for x in raw if "job types" in x["title"])
        text = _claims(e)
        assert re.search(r"by owner report", text)
        assert e["source"] == "model-generated"


class TestBoundaries:
    def test_no_fault_codes(self, raw):
        for e in raw:
            assert e["dtc_codes"] == []

    def test_no_campaign_numbers(self, raw):
        for e in raw:
            assert not re.findall(r"\b\d{2}V\d{6}\b", _claims(e)), e["title"]

    def test_spring_valve_entry_names_both_engines_and_the_error(self, raw):
        e = next(x for x in raw if "spring-valve" in x["title"])
        text = _claims(e)
        assert "60,000 km" in text and "45,000 km" in text
        assert re.search(r"not desmo|not to desmo", text)


class TestSearchability:
    @pytest.mark.parametrize("needle", [
        "mv agusta brutale 800 valve interval",
        "ktm 390 adventure valve clearance km",
        "ducati desmo service hours panigale v4",
        "bmw r1250gs valve check interval",
        "triumph street triple valve adjustment charge",
        "is a valve check due every two years",
    ])
    def test_a_plausible_query_finds_something(self, raw, needle):
        words = [w[:5] for w in re.findall(r"[a-z0-9]+", needle) if len(w) > 3]
        best = max(sum(1 for w in words if w in _claims(e).lower().replace("-", "")) for e in raw)
        assert best >= 3, f"{needle!r} matched only {best} terms"
