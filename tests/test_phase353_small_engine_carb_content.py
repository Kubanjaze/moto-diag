"""Phase 353 — small-engine carburettor service: the layer Track M left to it.

Before this file, the five Track M files (251–254, 354) held no carburettor
service at all: ``float bowl``, ``pilot screw``, ``main jet`` and ``jetting``
each read 0, because 254 and 354 forbade those terms so that 353 would own
them. The corpus's only carburettor-service rows were ten unsourced big-bike
rows (F151), so no carburetted scooter reached a row about its own
carburettor.

The roadmap row said "Keihin/Mikuni small-bore carbs, seasonal cleaning,
emission restrictions". The makers' documents said something narrower, and
the tests below keep what they said:

* **Keihin/Mikuni is true for part of the class** — the two-stroke Vespa and
  Typhoon 50s carry Dell'Orto, and the Kymco, SYM and CHF50 manuals name no
  maker at all;
* **"factory pre-set" is not one rule** — the CHF50 resets its pilot screw two
  ways by edition, Piaggio sets the mixture on an exhaust analyser, and only
  one of two Kymco manuals says "factory pre-set";
* **one make per row** (F142), each machine reaching its own row at tier 0.
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
from motodiag.knowledge.retrieval import rows_for_machine
from motodiag.knowledge.vehicle_resolver import known_issues_for_vehicle

ROOT = Path(__file__).resolve().parent.parent
K = ROOT / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"
SEED = K / "known_issues_small_engine_carbs.json"

#: The rows Phase 353 shipped, by title — the title is part of the row's
#: identity (F129), so a retitled row is a new row and must be named here.
TITLES_353 = {
    "Honda's CHF50 carburettor: a factory pre-set pilot screw, reset two different ways by edition, and a high-altitude setting that is not undone by reversing it":
        ("Honda", "CHF50"),
    "Honda Ruckus owner's manuals: idle speed is the only carburettor adjustment the emission section allows, a high-altitude setting must come back out, and methanol was dropped by 2022":
        ("Honda", "Ruckus"),
    "Kymco Agility 50 and People S 250 carburettors: record the pilot screw's turns, test the bystarter hot and cold, and drain the float chamber after a month unused":
        ("Kymco", "Agility 50"),
    "SYM carburetted scooters: the auto by-starter is checked by resistance and by air through its circuit hot and cold, and the pilot screw is set at the factory and trimmed to CO":
        ("SYM", "Joyride 125"),
    "Piaggio's small carburetted scooters: the mixture screw is set on an exhaust analyser, and each automatic starter has its own resistance and time":
        ("Piaggio", "Fly 50"),
    "Vespa's small carburetted scooters: Dell'Orto on the two-stroke 50s, Keihin on the LX 125-150, and an LX 50 manual that gives two idle speeds":
        ("Vespa", "LX 50"),
    "Yamaha's carburetted scooters: owner's manuals leave carburettor adjustment to the dealer, drain the float chamber back into the tank for storage, allow E10 and do not recommend methanol":
        ("Yamaha", "Vino 125"),
}

_DOCUMENT = re.compile(r"service manual|workshop manual|owner'?s manual", re.I)
_NUMBER = re.compile(r"\b\d+(?:[.,]\d+)?\s?(?:ohm|rpm|r/min|mm|%|m|ft|turns?)(?!\w)", re.I)


def _entries() -> list[dict]:
    return json.loads(SEED.read_text(encoding="utf-8"))


def _text(e: dict) -> str:
    return " ".join(str(e.get(k) or "") for k in ("title", "description", "fix_procedure"))


def _row(fragment: str) -> dict:
    hits = [e for e in _entries() if fragment.lower() in e["title"].lower()]
    assert len(hits) == 1, (fragment, [e["title"][:60] for e in hits])
    return hits[0]


def _sentences(e: dict) -> list[str]:
    return re.split(r"(?<=[.;])\s+", _text(e))


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    from motodiag.core.config import reset_settings

    path = str(tmp_path_factory.mktemp("p353") / "p353.db")
    init_db(path)
    for f in sorted(K.glob("known_issues_*.json")):
        load_known_issues_file(f, path)
    rebuild_make_index_at(path)
    rebuild_model_index_at(path)
    reset_settings()
    return path


# ---------------------------------------------------------------------------
# 1. What shipped
# ---------------------------------------------------------------------------
class TestWhatShipped:
    def test_the_file_is_exactly_353s_rows(self):
        have = {e["title"] for e in _entries()}
        assert have == set(TITLES_353), sorted(have ^ set(TITLES_353))

    def test_one_make_per_row(self):
        """F142: a multi-make row pairs every model with every make in the
        junction."""
        for e in _entries():
            assert "," not in e["make"], (e["title"][:50], e["make"])
            assert e["make"] == TITLES_353[e["title"]][0]

    def test_no_row_declares_applicability(self):
        """D2: carburettor service makes no claim on the transmission axis."""
        for e in _entries():
            assert "applicability" not in e, e["title"][:50]

    def test_every_row_is_labelled_service_manual(self):
        """D3: the maker's own document, as 252's and 253's owner's-manual
        rows are labelled; the text says which document it is."""
        assert {e["source"] for e in _entries()} == {"service-manual"}

    def test_only_the_two_honda_rows_carry_a_year_window(self):
        """A window must come from a document (F132): the CHF50 manual's
        cover starts at 2002; the Ruckus editions read span 2012-2025."""
        windows = {e["model"]: (e.get("year_start"), e.get("year_end")) for e in _entries()
                   if e.get("year_start") or e.get("year_end")}
        assert windows == {"CHF50": (2002, None), "Ruckus, NPS50": (2012, 2025)}


# ---------------------------------------------------------------------------
# 2. Anchored
# ---------------------------------------------------------------------------
class TestEveryRowIsAnchored:
    @pytest.mark.parametrize("entry", _entries(), ids=lambda e: e["make"] + ":" + e["title"][:30])
    def test_the_row_names_its_document(self, entry):
        assert _DOCUMENT.search(entry["description"]), entry["title"][:60]

    @pytest.mark.parametrize("entry", _entries(), ids=lambda e: e["make"] + ":" + e["title"][:30])
    def test_the_row_quotes_the_maker(self, entry):
        """Written from quotes: at least four quoted passages per row."""
        assert len(re.findall(r"'[^']{8,}'", entry["description"])) >= 4, entry["title"][:60]

    @pytest.mark.parametrize("entry", _entries(), ids=lambda e: e["make"] + ":" + e["title"][:30])
    def test_the_row_carries_numbers_and_says_where_it_read_them(self, entry):
        assert _NUMBER.search(_text(entry)), entry["title"][:60]
        assert "research library" in entry["description"], entry["title"][:60]

    def test_no_row_claims_a_provenance_it_cannot_show(self):
        for e in _entries():
            assert "third-party mirror" not in e["description"], e["title"][:40]
            assert "the same copy" not in e["description"], e["title"][:40]


# ---------------------------------------------------------------------------
# 3. Boundaries: what other phases own
# ---------------------------------------------------------------------------
class TestBoundaries:
    def test_no_row_restates_the_charging_rows(self):
        """354 owns charging."""
        for e in _entries():
            low = _text(e).lower()
            for owned in ("stator", "rectifier", "charging", "alternator"):
                assert owned not in low, (e["title"][:40], owned)

    def test_no_row_restates_the_kickstart_row(self):
        """254's kickstart row owns starting on a flat battery."""
        for e in _entries():
            assert not re.search(r"kick[- ]?start", _text(e), re.I), e["title"][:40]

    def test_the_ruckus_row_does_not_restate_carb_versus_injection(self):
        """252 owns the Ruckus/Metropolitan comparison."""
        body = _text(_row("Honda Ruckus"))
        assert "Metropolitan" not in body
        assert not re.search(r"inject", body, re.I)

    def test_the_yamaha_row_does_not_restate_the_carburettor_codes(self):
        """253's engines row carries TEIKEI, KEIHIN NCV18 and Mikuni BS26."""
        body = _text(_row("Yamaha's carburetted"))
        for code in ("NCV18", "BS26", "Y14P", "Teikei", "TEIKEI", "Mikuni", "KEIHIN"):
            assert code not in body, code
        assert "not repeated here" in body

    def test_no_row_generalises_keihin_and_mikuni(self):
        """S0-6: the roadmap's 'Keihin/Mikuni' is false for the two-strokes
        and unstated for Kymco, SYM and the CHF50."""
        for e in _entries():
            assert not re.search(r"keihin\s*(/|or|and)\s*mikuni", _text(e), re.I), e["title"][:40]


# ---------------------------------------------------------------------------
# 4. What the documents said, kept as they said it
# ---------------------------------------------------------------------------
class TestWhatTheManualsSaid:
    def test_the_two_strokes_carry_dellorto(self):
        assert "DELL'ORTO PHVA 17.5" in _row("Vespa's small")["description"]
        assert "DELL'ORTO PHVA 17.5" in _row("Piaggio's small")["description"]

    def test_kymco_sym_and_the_chf50_name_no_maker(self):
        assert "neither names its maker" in _row("Kymco Agility")["description"]
        assert "none names the carburettor's maker" in _row("SYM carburetted")["description"]
        assert "It names no carburettor maker" in _row("CHF50 carburettor")["description"]

    def test_the_chf50_high_altitude_setting_is_not_undone_by_reversing_it(self):
        """p. 5-20 goes up 1/2 turn in; p. 5-21 comes down 1/4 turn out.
        Recorded as printed, not corrected."""
        body = _row("CHF50 carburettor")["description"]
        assert "1/2 turn in from the factory preset position" in body
        assert "Turn the pilot screw out 1/4 turn from the high altitude setting" in body

    def test_the_ruckus_methanol_rule_changed(self):
        body = _row("Honda Ruckus")["description"]
        assert "Methanol (methyl alcohol) 5% by volume (max)" in body
        assert "Do not use gasoline containing methanol (methyl alcohol)" in body

    def test_the_kymco_bystarter_test_keeps_its_direction(self):
        """Blocked when powered is normal; air passing when cold is normal."""
        body = _row("Kymco Agility")["description"]
        assert "'If the passage is blocked, the auto bystarter is normal'" in body
        assert "'If air can be blown into the hose, the auto bystarter is normal'" in body

    def test_the_piaggio_mixture_is_set_on_an_analyser(self):
        body = _row("Piaggio's small")["description"]
        assert "The screw final position should be determined by an exhaust fume analysis" in body

    def test_the_fly_125_blanks_are_reported_as_printed(self):
        assert "blanks, printed so on the page" in _row("Piaggio's small")["description"]

    def test_the_storage_rules_disagree_by_maker(self):
        """S0-8: Kymco drains after a month and empties the tank; Yamaha
        drains before several months and pours the fuel back in."""
        assert "not used for over one month" in _row("Kymco Agility")["description"]
        assert "empty the fuel tank" in _row("Kymco Agility")["description"]
        assert "Pour the drained fuel into the fuel tank" in _row("Yamaha's carburetted")["description"]


class TestWhatTheRefutersCorrected:
    """Four refuters, 178 claims, 32 killed. Each correction pinned."""

    def test_both_chf50_editions_are_factory_pre_set_and_reset_differently(self):
        body = _row("CHF50 carburettor")["description"]
        assert "Both editions say 'The pilot screw is factory pre-set" in body
        assert "obtain the highest engine speed" in body
        assert "until the engine speed drops by 50 rpm" in body

    def test_the_chf50_replacement_procedure_gives_the_initial_opening(self):
        fix = _row("CHF50 carburettor")["fix_procedure"]
        assert "back out 2-1/4 turns" in fix
        assert "back out 2-3/4 turns (P type 2-1/8)" in fix

    def test_the_chf50_cover_names_the_metropolitan(self):
        """The image-only cover prints CHF50/P/S METROPOLITAN (F152); the
        row still reaches only the CHF50 at tier 0 (see TestReachable)."""
        body = _row("CHF50 carburettor")["description"]
        assert "cover, an image with no text layer, reads CHF50/P/S METROPOLITAN" in body
        assert _row("CHF50 carburettor")["model"] == "CHF50"

    def test_the_ruckus_owner_idle_procedure_is_2012_only(self):
        body = _row("Honda Ruckus")["description"]
        assert "Only the 2012 edition gives the owner an idle procedure" in body
        assert "not the owner's only" not in body

    def test_the_ruckus_change_is_not_dated_past_what_was_read(self):
        body = _row("Honda Ruckus")["description"]
        assert "dated only to 2022 or earlier" in body
        assert "after 2012" not in _row("Honda Ruckus")["title"]

    def test_factory_pre_set_is_the_agility_manuals_claim_only(self):
        for s in _sentences(_row("Kymco Agility")):
            if "factory pre-set" in s:
                assert "Agility 50 manual" in s, s
                assert "Both" not in s, s

    def test_the_sym_star_note_is_epas_and_only_two_manuals_explain_it(self):
        body = _row("SYM carburetted")["description"] + _row("SYM carburetted")["fix_procedure"]
        assert "SYM prohibits" not in body
        assert "the Jet and Fiddle 50 schedules print the stars without that note" in body

    def test_the_xa05w_manual_is_not_called_the_fiddle_iii(self):
        """It prints only 'MODEL XA05W-6'; the name comes from a file name."""
        row = _row("SYM carburetted")
        assert "Fiddle III" not in row["model"]
        assert "'MODEL XA05W-6'" in row["description"]

    def test_the_fly_50_starter_is_its_own(self):
        body = _row("Piaggio's small")["description"]
        assert "'Automatic starter resistance 6 ohm +/- 5 %'" in body
        assert "'max. time 15 min'" in body

    def test_no_walbro_figures_reach_the_beverly(self):
        """The B 125-250 manual (618162) is tied to no model in the column:
        its 125 chassis prefix differs from the Beverly 125's."""
        body = _text(_row("Piaggio's small"))
        assert "Walbro" not in body and "WALBRO" not in body
        assert "618162" not in body

    def test_the_lx_50_idle_figures_are_not_explained_away(self):
        body = _row("Vespa's small")["description"]
        assert "two procedures" not in body
        assert "The S 50 manual prints no CO figure" in body

    def test_yamaha_does_not_recommend_methanol_rather_than_forbid_it(self):
        row = _row("Yamaha's carburetted")
        assert "do not recommend methanol" in row["title"]
        assert "if available" in row["fix_procedure"]
        assert "1600 - 1700 r/min on the YJ125Y" in row["description"]

    def test_zuma_is_bridged_not_asserted(self):
        body = _row("Yamaha's carburetted")["description"]
        assert "None prints 'Zuma'" in body


# ---------------------------------------------------------------------------
# 5. Reachable
# ---------------------------------------------------------------------------
_MACHINES = [
    ("Honda", "CHF50", "CHF50 carburettor"),
    ("Honda", "Ruckus", "Honda Ruckus"),
    ("Honda", "NPS50", "Honda Ruckus"),
    ("Kymco", "Agility 50", "Kymco Agility"),
    ("Kymco", "People S 250", "Kymco Agility"),
    ("Kymco", "People 250", "Kymco Agility"),
    ("SYM", "Joyride 125", "SYM carburetted"),
    ("SYM", "Jet Euro 50", "SYM carburetted"),
    ("SYM", "Fiddle 50", "SYM carburetted"),
    ("Piaggio", "Fly 50", "Piaggio's small"),
    ("Piaggio", "Fly 125", "Piaggio's small"),
    ("Piaggio", "Beverly 125", "Piaggio's small"),
    ("Piaggio", "Typhoon 50", "Piaggio's small"),
    ("Vespa", "LX 50", "Vespa's small"),
    ("Vespa", "S 50", "Vespa's small"),
    ("Vespa", "LX 150", "Vespa's small"),
    ("Yamaha", "Vino 50", "Yamaha's carburetted"),
    ("Yamaha", "Vino 125", "Yamaha's carburetted"),
    ("Yamaha", "Zuma 50", "Yamaha's carburetted"),
]


class TestReachable:
    @pytest.mark.parametrize("make,model,fragment", _MACHINES)
    def test_the_machine_gets_its_row_at_tier_0(self, db, make, model, fragment):
        _, rows = known_issues_for_vehicle(make, model, db_path=db, limit=2000)
        mine = [r for r in rows if fragment.lower() in r["title"].lower()]
        assert mine and mine[0]["match_tier"] == "model", (make, model, [r["match_tier"] for r in mine])

    @pytest.mark.parametrize("make,model,fragment", _MACHINES)
    def test_the_chokepoint_keeps_it(self, db, make, model, fragment):
        _, rows = known_issues_for_vehicle(make, model, db_path=db, limit=2000)
        kept = rows_for_machine(rows, make=make, model=model, purpose="prompt",
                                db_path=db, record=False).rows
        assert any(fragment.lower() in r["title"].lower() for r in kept), (make, model)

    def test_the_ruckus_row_outranks_the_big_bike_carb_rows(self, db):
        """S0-3: before 353 a Ruckus's first carburettor row was a CBR600F4i
        float bowl at make_other_model (F151)."""
        _, rows = known_issues_for_vehicle("Honda", "Ruckus", db_path=db, limit=2000)
        titles = [r["title"] for r in rows]
        mine = next(i for i, t in enumerate(titles) if t.startswith("Honda Ruckus owner's manuals"))
        bowl = next(i for i, t in enumerate(titles) if t.startswith("Float bowl overflow"))
        assert mine < bowl

    def test_a_gold_wing_does_not_get_them_above_tier_2(self, db):
        _, rows = known_issues_for_vehicle("Honda", "Gold Wing", db_path=db, limit=2000)
        ours = [r for r in rows if r["title"] in TITLES_353]
        assert ours, "positive control: the Honda rows still reach the make"
        for r in ours:
            assert r["match_tier"] == "make_other_model", r["title"][:50]

    def test_a_current_metropolitan_does_not_get_the_chf50_row_at_tier_0(self, db):
        _, rows = known_issues_for_vehicle("Honda", "Metropolitan", db_path=db, limit=2000)
        chf = [r for r in rows if r["title"].startswith("Honda's CHF50 carburettor")]
        assert chf, "positive control: the row still reaches the make"
        assert chf[0]["match_tier"] == "make_other_model"

    @pytest.mark.parametrize("query,fragment", [
        ("pilot screw", "CHF50 carburettor"),
        ("auto bystarter", "Kymco Agility"),
        ("by-starter", "SYM carburetted"),
        ("exhaust fume analysis", "Piaggio's small"),
        ("fuel stabilizer", "Yamaha's carburetted"),
    ])
    def test_search_finds_the_rows(self, db, query, fragment):
        rows = search_known_issues(query=query, db_path=db, limit=200)
        assert any(fragment.lower() in r["title"].lower() for r in rows), query
