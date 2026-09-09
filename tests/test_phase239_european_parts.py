"""Phase 239 — European parts sourcing, as catalogue rows and documented constraints.

Three surfaces, like 225/230/235: parts rows (Aprilia, MV Agusta and
Moto Guzzi had zero), OEM-to-aftermarket cross-references, and knowledge
entries for constraints that rest on a document. A wrong model_pattern
puts a wrong part on a bike, so the refuters' fitment corrections are
pinned here individually.
"""
import json
import re
import tempfile
from pathlib import Path

import pytest

from motodiag.advanced.parts_loader import load_parts_file, load_parts_xref_file
from motodiag.core.database import get_connection, init_db

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "src" / "motodiag" / "advanced" / "data"
PARTS = DATA / "parts.json"
XREF = DATA / "parts_xref.json"
K = ROOT / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"
FILE = K / "known_issues_european_parts.json"
EURO = {"aprilia", "mv-agusta", "moto-guzzi", "ktm", "bmw", "ducati", "triumph"}

#: The catalogue before this phase, snapshotted from master — asserted to
#: survive, the Phase 230 pattern, rather than pinning a total that the next
#: phase would move. Also the scope for rules that govern only rows added
#: here (cost sourcing), so original rows are not judged by them.
ORIGINAL_SLUGS = frozenset([
    "all-balls-18-3019-brake-caliper-kit",
    "all-balls-22-1019-wheel-bearing",
    "all-balls-23-5001-cush-drive-klr",
    "all-balls-25-1486-final-drive-seal",
    "all-balls-25-5132-water-pump-seal",
    "all-balls-25-6004-water-pump-triumph",
    "ape-tsh301-manual-cct-cbr600rr",
    "ape-tsk160-manual-tensioner-zx6r",
    "barnett-306-90-20131-clutch-plates",
    "barnett-519-90-06028-clutch-springs",
    "bmw-11417722956-oil-filter",
    "bmw-11537726068-coolant-hose",
    "bmw-33117660878-final-drive-seal",
    "cometic-c8560-head-gasket-r6",
    "cycle-electric-ce-4000-stator",
    "dp-dp828-brake-pads",
    "ducati-19020221a-clutch-plates",
    "ducati-44440034a-clutch-spring",
    "eagle-mike-05-dohickey-klr650",
    "ebc-fa380hh-brake-pads-r1",
    "ebc-fa388-hh-brake-pads",
    "feuling-4124-cam-tensioner",
    "hd-26349-99-oem-cam-bearings",
    "hd-26499-08-oem-cam-tensioner",
    "hd-29965-07a-stator",
    "hd-62921-03-fuel-pump",
    "hd-63731-99-oil-filter",
    "hiflo-hf157-oil-filter-ktm",
    "honda-06455-mee-000-brake-pads",
    "honda-14520-kzs-901-cct",
    "honda-15410-mcj-505-oil-filter",
    "honda-17211-mbw-j20-air-filter",
    "honda-44650-mee-j20-front-wheel-bearing",
    "jt-jtf520-15-sprocket-front",
    "kawasaki-13239-1091-doohickey",
    "kawasaki-14044-1284-chain-tensioner",
    "kawasaki-92161-1478-cushion-rubber",
    "kn-ha-6001-air-filter-f4i",
    "kn-kn-138-oil-filter-suzuki",
    "kn-kn-170-oil-filter-hd",
    "kn-kn-204-oil-filter-honda",
    "ktm-60003086000-oil-filter",
    "ktm-75030088000-water-pump-seal",
    "mahle-ox-119d-oil-filter-bmw",
    "ngk-cr9eh-9-spark-plug",
    "ngk-cr9eix-iridium-spark-plug",
    "ngk-cr9ek-spark-plug",
    "purolator-pl14610-oil-filter",
    "quantum-hfp-383-fuel-pump",
    "samco-bmw-112-coolant-hose",
    "sands-33-4220-cam-tensioner",
    "sbs-806hs-brake-pads",
    "sunstar-321-15-sprocket-front",
    "superlite-rs8-525-sprocket-front",
    "suzuki-09482-00413-spark-plug",
    "suzuki-16510-07j00-oil-filter",
    "torrington-b168-cam-bearing",
    "triumph-t1261150-water-pump",
    "triumph-t2017070-sprocket-front",
    "yamaha-2c0-11181-00-head-gasket",
    "yamaha-4xv-w0045-50-brake-pads",
    "yamaha-5vy-2580w-10-brake-caliper-seal"
])


@pytest.fixture(scope="module")
def parts():
    return json.loads(PARTS.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def xref():
    return json.loads(XREF.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def raw():
    return json.loads(FILE.read_text(encoding="utf-8"))


def _by(parts, pn):
    return [r for r in parts if r["oem_part_number"] == pn]


class TestTheGapIsFilled:
    def test_the_three_zero_makes_now_have_rows(self, parts):
        makes = {r["make"] for r in parts}
        assert {"aprilia", "mv-agusta", "moto-guzzi"} <= makes

    def test_original_rows_survive(self, parts):
        assert ORIGINAL_SLUGS <= {r["slug"] for r in parts}

    def test_slugs_are_unique(self, parts):
        slugs = [r["slug"] for r in parts]
        assert len(slugs) == len(set(slugs))

    def test_every_xref_resolves_both_sides(self, parts, xref):
        slugs = {r["slug"] for r in parts}
        for x in xref:
            assert x["oem_slug"] in slugs, x["oem_slug"]
            assert x["aftermarket_slug"] in slugs, x["aftermarket_slug"]

    def test_the_loader_accepts_everything_end_to_end(self, parts, xref):
        with tempfile.TemporaryDirectory() as d:
            db = f"{d}/t.db"
            init_db(db)
            load_parts_file(PARTS, db)
            load_parts_xref_file(XREF, db)
            with get_connection(db) as c:
                assert c.execute("SELECT count(*) FROM parts").fetchone()[0] == len(parts)
                # Distinct pairs, not rows: the original Phase 153 seed carries
                # one duplicated pair (ducati-19020221a-clutch-plates ->
                # barnett-519-90-06028-clutch-springs, indexes 41 and 67) that
                # INSERT OR IGNORE has silently swallowed since. Left in place
                # as pre-existing data; detected here rather than papered over.
                pairs = {(x["oem_slug"], x["aftermarket_slug"]) for x in xref}
                assert c.execute("SELECT count(*) FROM parts_xref").fetchone()[0] == len(pairs)
                assert len(xref) - len(pairs) == 1, "expected exactly the one known original duplicate"


class TestCostHonesty:
    def test_no_cost_is_none(self, parts):
        assert all(isinstance(r["typical_cost_cents"], int) for r in parts)

    def test_zero_cost_rows_say_why(self, parts):
        """0 is the repo's own unpriced sentinel (add_part defaults to
        it; cost queries filter > 0). A row using it must say so, or a
        reader takes it for a price."""
        for r in parts:
            if r["typical_cost_cents"] == 0:
                assert re.search(r"unpriced sentinel|not priced|GBP|EUR", r["notes"]), r["slug"]

    def test_no_converted_currencies(self, parts):
        """Fiche prices are GBP/EUR and stay in notes. A refuter caught
        an NZD figure rendered as USD in the sibling phase."""
        for r in parts:
            if r["slug"] in ORIGINAL_SLUGS:
                continue
            if r["make"] in EURO and r["typical_cost_cents"] > 0:
                assert "USD" in r["notes"] or r["verified_by"] == "forum", r["slug"]


class TestTheFitmentCorrections:
    def test_ktm_19_inch_band_uses_exact_patterns(self, parts):
        """'1_90%Adventure%' would have matched the R variants, which take
        the 21-inch band. Exact model names, no wildcard, no R."""
        for r in _by(parts, "60309173100"):
            assert "%" not in r["model_pattern"], r["model_pattern"]
            assert not r["model_pattern"].endswith(" R"), r["model_pattern"]

    def test_hiflo_hf138_starts_2009(self, parts):
        r = next(x for x in _by(parts, "HF138") if x["make"] == "aprilia")
        assert r["year_min"] == 2009
        assert "does NOT list" not in r["notes"]

    def test_bmw_belt_xref_pairs_the_corrected_way_round(self, parts, xref):
        slugs = {r["slug"]: r for r in parts}
        pair = {(slugs[x["oem_slug"]]["oem_part_number"], slugs[x["aftermarket_slug"]]["oem_part_number"])
                for x in xref if slugs[x["oem_slug"]]["make"] == "bmw"
                and slugs[x["aftermarket_slug"]]["brand"] == "Contitech"}
        assert ("11318528385", "4PK592 (582) ELAST") in pair
        assert ("12317681841", "4PK611 (592) ELAST") in pair
        assert ("11318528385", "4PK611 (592) ELAST") not in pair

    def test_ina_bearing_has_no_bmw_number_and_no_xref(self, parts, xref):
        r = next(x for x in parts if x["oem_part_number"] == "F-237895")
        assert "NOT confirmed" in r["description"]
        assert not any(x["aftermarket_slug"] == r["slug"] or x["oem_slug"] == r["slug"] for x in xref)

    def test_ducati_scrambler_current_belt_starts_2019(self, parts):
        r = next(x for x in _by(parts, "73740241B") if x["model_pattern"].startswith("Scrambler"))
        assert r["year_min"] == 2019

    def test_early_scramblers_are_on_the_281a_belt(self, parts):
        r = next(x for x in _by(parts, "73740281A") if x["model_pattern"].startswith("Scrambler"))
        assert (r["year_min"], r["year_max"]) == (2015, 2018)

    def test_ktm_truncated_fiche_is_not_read_as_exclusion(self, parts):
        for pn in ("0760122050", "60040020000"):
            r = _by(parts, pn)[0]
            assert re.search(r"truncated|not shown", r["notes"]), pn
            assert "only" not in r["description"].lower()

    def test_supersessions_are_rated_five(self, xref):
        """Scoped to rows that say they are supersessions — an original
        Ducati clutch-plates-to-springs pair is same-brand and rated 4,
        correctly, because it is a companion part."""
        for x in xref:
            if "supersession" in x["notes"].lower():
                assert x["equivalence_rating"] == 5, x

    def test_approximate_rows_are_rated_two(self, xref):
        for x in xref:
            if "pproximate" in x["notes"]:
                assert x["equivalence_rating"] <= 2, x["notes"]


class TestKnowledgeFile:
    def test_eleven_entries(self, raw):
        assert len(raw) == 11

    def test_symptoms_are_short_phrases(self, raw):
        for e in raw:
            for s in e["symptoms"]:
                assert len(s) <= 55 and not s.endswith("."), f"{e['title']}: {s!r}"

    def test_every_entry_says_what_it_is_drawn_from(self, raw):
        for e in raw:
            assert re.search(r"[Dd]rawn\b[\w' ]{0,16}\bfrom", e["description"]), e["title"]

    def test_forum_tips_only_on_forum_entries(self, raw):
        for e in raw:
            assert ("Forum tip" in e["fix_procedure"]) == (e["source"] == "forum"), e["title"]

    def test_no_title_collides_corpus_wide(self):
        titles = []
        for f in K.glob("known_issues_*.json"):
            titles += [e["title"] for e in json.loads(f.read_text(encoding="utf-8"))]
        assert len(titles) == len(set(titles))

    def test_no_campaign_numbers_and_no_currency_figures(self, raw):
        for e in raw:
            text = " ".join([e["description"], e["fix_procedure"]] + e["causes"])
            assert not re.findall(r"\b\d{2}V\d{6}\b", text), e["title"]
            assert not re.search(r"\$\s?\d|USD \d|NZD|EUR \d|GBP \d", text), e["title"]

    def test_the_negative_findings_stay_negative(self, raw):
        fd = next(e for e in raw if "complete unit" in e["title"])
        assert "not established" in fd["title"]
        mv = next(e for e in raw if "rim band" in e["title"])
        assert "could be established" in mv["title"]

    def test_the_generic_mv_distribution_entries_were_dropped(self, raw):
        text = " ".join(e["title"] for e in raw)
        for phrase in ("DHL", "KTM North America", "Pierer"):
            assert phrase not in text, phrase

    def test_no_entry_restates_a_237_differential(self, raw):
        d237 = json.loads((K / "known_issues_european_differentials.json").read_text(encoding="utf-8"))
        stems = {" ".join(e["title"].split()[:6]).lower() for e in d237}
        for e in raw:
            assert " ".join(e["title"].split()[:6]).lower() not in stems, e["title"]
