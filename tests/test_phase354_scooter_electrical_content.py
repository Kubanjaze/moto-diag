"""Phase 354 — scooter electrical: the charging layer Track M left empty.

Before this file, 251–254's four scooter files held zero rows about a stator,
a charging system or a rectifier, and every one of their 53 uses of
"regulator" meant the US regulator. A Ruckus was reached by 19 charging rows
and a Zuma 125 by 12, none about its own machine.

The roadmap row said "stator-to-battery, no FI on older carb scooters, simple
wiring". The service manuals said something else, and the tests below keep
what they said:

* **carburettor versus injection does not predict the charging design** — the
  carburetted CHF50 Metropolitan has a three-phase alternator/starter run by
  an ECM, and the injected Zuma 125 prints "AC magneto";
* **a separate lighting coil is a per-model fact, not a scooter fact** — the
  Kymco Agility 50 has one and the People S 250 in the same maker's range
  does not, and one SYM manual covers both arrangements;
* **one make per row** (F142), each row naming only machines its own
  documents cover, and each machine reaching its row at tier 0.
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
SEED = K / "known_issues_scooter_electrical.json"

#: The rows Phase 354 shipped, by title — the title is part of the row's
#: identity (F129), so a retitled row is a new row and must be named here.
TITLES_354 = {
    "On a Honda PCX150 the alternator is also the starter, and the regulator/rectifier is inside the ECM":
        ("Honda", "PCX150"),
    "Honda's carburetted CHF50 charges through a three-phase alternator/starter that its ECM controls":
        ("Honda", "CHF50"),
    "Two Kymco service manuals, two opposite charging systems: the Agility 50 lights its headlight from its own AC coil":
        ("Kymco", "Agility 50"),
    "One SYM manual gives the Jet 50/100 an illumination coil and the Jet Euro 50/100 an SCR with a Y-Y charging coil":
        ("SYM", "Jet 50"),
    "Piaggio's Fly 50 is single-phase, while the Fly 125, Beverly 125 and MP3 400 charge through a three-phase alternator wired to the battery":
        ("Piaggio", "Fly 125"),
    "Vespa's 50 cc regulator is tested with the lights on and off; the LX 125-150 and GTS 300 use a three-phase alternator wired to the battery through a fuse":
        ("Vespa", "LX 125"),
    "Yamaha's YW125 service manual gives two stator resistances a factor of two apart":
        ("Yamaha", "YW125"),
}

_DOCUMENT = re.compile(r"service manual|workshop manual|owner'?s manual", re.I)
_NUMBER = re.compile(
    r"\b\d+(?:[.,]\d+)?\s?(?:V|A|W|kW|Ah|AH|ohm|rpm|mA)(?!\w)", re.I)


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

    path = str(tmp_path_factory.mktemp("p354") / "p354.db")
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
    def test_the_file_is_exactly_354s_rows(self):
        have = {e["title"] for e in _entries()}
        assert have == set(TITLES_354), sorted(have ^ set(TITLES_354))

    def test_one_make_per_row(self):
        """F142: a multi-make row pairs every model with every make in the
        junction, so a SYM model would be filed under Kymco."""
        for e in _entries():
            assert "," not in e["make"], (e["title"][:50], e["make"])
            assert e["make"] == TITLES_354[e["title"]][0]

    def test_no_row_declares_applicability(self):
        """D2: these claims are about a machine's generator, not its
        transmission; an absent key makes no claim on that axis."""
        for e in _entries():
            assert "applicability" not in e, e["title"][:50]

    def test_every_row_is_labelled_service_manual(self):
        assert {e["source"] for e in _entries()} == {"service-manual"}


# ---------------------------------------------------------------------------
# 2. Anchored
# ---------------------------------------------------------------------------
class TestEveryRowIsAnchored:
    @pytest.mark.parametrize("entry", _entries(), ids=lambda e: e["make"] + ":" + e["title"][:30])
    def test_the_row_names_its_document(self, entry):
        assert _DOCUMENT.search(entry["description"]), entry["title"][:60]

    @pytest.mark.parametrize("entry", _entries(), ids=lambda e: e["make"] + ":" + e["title"][:30])
    def test_the_row_quotes_the_maker(self, entry):
        """Written from quotes: at least two quoted passages per row."""
        assert len(re.findall(r"'[^']{8,}'", entry["description"])) >= 2, entry["title"][:60]

    @pytest.mark.parametrize("entry", _entries(), ids=lambda e: e["make"] + ":" + e["title"][:30])
    def test_the_row_carries_numbers_and_says_where_it_read_them(self, entry):
        assert _NUMBER.search(_text(entry)), entry["title"][:60]
        assert "research library" in entry["description"], entry["title"][:60]

    def test_no_row_claims_a_provenance_it_cannot_show(self):
        """Refuters: 'the same copy Phase 254 cited' was false for the SYM
        Jet, the Beverly and the Vespa S 50. Each row now says only what is
        known — a copy in the research library, not fetched from the maker."""
        for e in _entries():
            assert "the same copy Phase 254 cited" not in e["description"], e["title"][:40]
            assert "third-party mirror" not in e["description"], e["title"][:40]


# ---------------------------------------------------------------------------
# 3. Boundaries: what other phases own
# ---------------------------------------------------------------------------
class TestBoundaries:
    def test_no_row_writes_carburettor_service(self):
        """Row 353. Naming that a machine is carburetted is this phase's
        evidence; servicing the carburettor is not."""
        for e in _entries():
            low = _text(e).lower()
            for owned in ("float bowl", "pilot screw", "main jet", "slow jet", "jetting",
                          "carburettor rebuild", "carburetor rebuild"):
                assert owned not in low, (e["title"][:40], owned)

    def test_no_row_restates_the_kickstart_row(self):
        """254's kickstart row owns starting on a flat battery."""
        for e in _entries():
            for sentence in _sentences(e):
                low = sentence.lower()
                assert not re.search(r"kick[- ]?start", low), (e["title"][:40], sentence[:100])

    def test_no_row_restates_the_ruckus_metropolitan_comparison(self):
        """252 owns carb-versus-injection on the Ruckus and the NCW50
        Metropolitan; 354 names neither machine as its subject."""
        for e in _entries():
            assert "Ruckus" not in _text(e), e["title"][:40]
            assert "NCW50" not in e["model"], e["title"][:40]


# ---------------------------------------------------------------------------
# 4. What the documents said, kept as they said it
# ---------------------------------------------------------------------------
class TestWhatTheManualsSaid:
    def test_carburettor_versus_injection_is_not_the_axis(self):
        """S0-10: the carburetted CHF50 is three-phase with an ECM."""
        body = _row("carburetted CHF50")["description"]
        assert "does not predict" in body
        assert "3-phase AC generator" in body
        assert re.search(r"carburetted machine has an ECM", body)

    def test_the_pcx_regulator_is_in_the_ecm(self):
        row = _row("PCX150 the alternator is also the starter")
        assert "'The regulator/rectifier is built into the ECM.'" in row["description"]
        assert "Faulty regulator/rectifier in ECM" in row["description"]
        assert re.search(r"Do not order a separate regulator", row["fix_procedure"])

    def test_the_honda_standard_is_relative_to_the_battery(self):
        for fragment in ("PCX150 the alternator", "carburetted CHF50"):
            body = _row(fragment)["description"]
            assert "15.5 V" in body and "high beam" in body, fragment

    def test_the_agility_lighting_side_is_read_on_the_ac_range(self):
        body = _row("Two Kymco service manuals")["description"]
        assert "'Type Single-phase half-wave SCR'" in body
        assert "AC range" in body

    def test_the_kymco_figures_come_from_pages_headed_agility_50(self):
        """254 found FILLY headers in this manual; the row must say so."""
        body = _row("Two Kymco service manuals")["description"]
        assert "FILLY" in body and "headed AGILITY 50" in body

    def test_the_sym_row_says_the_yellow_wire_depends_on_the_model(self):
        body = _row("One SYM manual")["description"]
        assert re.search(r"yellow is the illumination coil", body)
        assert re.search(r"the yellow pair is the charging coil", body)

    def test_the_zuma_contradiction_ships_both_figures_and_picks_neither(self):
        row = _row("YW125 service manual gives two stator")
        body = row["description"]
        assert "0.56 ~ 0.84" in body and "0.28 ~ 0.42" in body
        assert "does not choose" in body
        assert "0.42 and 0.56" in row["fix_procedure"]


# ---------------------------------------------------------------------------
# 4b. What the four refuters corrected, each kept corrected
# ---------------------------------------------------------------------------
class TestWhatTheRefutersCorrected:
    def test_the_pcx_leakage_limit_is_given_per_edition(self):
        """0.1 mA is the '13 model; after '13 it is 0.4 mA (p. 20-8)."""
        fix = _row("PCX150 the alternator")["fix_procedure"]
        assert "0.4 mA max. after '13" in fix

    def test_the_pcx_stator_check_is_attributed_to_the_starter_chart(self):
        row = _row("PCX150 the alternator")
        assert "charging tree has no stator step" in row["description"]
        assert "starter chart (p. 6-6)" in row["fix_procedure"]

    def test_the_chf50_is_not_called_the_metropolitan(self):
        """The CHF50 manual prints 'Metropolitan' 0 times in 319 pages; the
        name may appear only where the row speaks of the NCW50's manuals."""
        row = _row("carburetted CHF50")
        assert "Metropolitan" not in row["title"]
        for sentence in _sentences(row):
            if "Metropolitan" in sentence:
                assert "NCW50" in sentence, sentence[:100]

    def test_the_agility_ac_test_carries_its_own_page_limit(self):
        fix = _row("Two Kymco service manuals")["fix_procedure"]
        assert "12 - 14 V, 5,000 rpm max, p. 14-4" in fix

    def test_the_kymco_carburettors_are_not_called_one_carburettor(self):
        body = _row("Two Kymco service manuals")["description"]
        assert "share a maker and a carburettor" not in body
        assert "carburetted fuel system" in body

    def test_the_zuma_band_logic_is_the_right_way_round(self):
        """First draft said 0.42-0.56 falls 'between' the figures; it fails
        both. The disagreeing bands are 0.28-0.42 and 0.56-0.84."""
        fix = _row("YW125 service manual")["fix_procedure"]
        assert "A reading between 0.42 and 0.56 ohm fails both" in fix
        assert "passes the troubleshooting page and fails the specification page" in fix

    def test_the_zuma_name_is_attributed_not_asserted(self):
        body = _row("YW125 service manual")["description"]
        assert "the name Zuma appears on none of its 338 pages" in body
        assert "Phase 253's cover-code record" in body

    def test_symply_is_not_named(self):
        """The manual filed as the Symply 125 never names a model beyond
        'MODEL ABA'; no document links the two (F150)."""
        for e in _entries():
            assert "Symply" not in _text(e) and "Symply" not in e["model"], e["title"][:40]

    def test_the_sym_yellow_winding_conflict_ships(self):
        body = _row("One SYM manual")["description"]
        assert "'charging /illumination coil (yellow to ground)'" in body
        assert "12.0~14.0 V / 5000 rpm" in body

    def test_piaggio_pages_are_cited_by_their_printed_folios(self):
        for fragment in ("Piaggio's Fly 50", "Vespa's 50 cc"):
            body = _row(fragment)["description"]
            assert "ELE SYS - " in body, fragment
            assert "print no chapter page numbers" not in body, fragment

    def test_the_idle_quote_is_not_given_to_the_mp3(self):
        body = _row("Piaggio's Fly 50")["description"]
        assert "The MP3 400 manual carries only the first half of that sentence" in body

    def test_the_key_switch_sentence_is_the_lx_manuals_only(self):
        row = _row("Vespa's 50 cc")
        assert "key-switch" not in row["title"] and "key switch" not in row["title"]
        assert "the GTS manual does not say it" in row["description"]

    def test_the_16v_and_15_2v_figures_are_not_compared(self):
        """Refuter: different tests (burnt-bulb regulation check vs battery
        poles with a charged battery). The first draft said a 50 cc Vespa may
        read higher than a 125; that sentence must not come back."""
        row = _row("Vespa's 50 cc")
        assert "allowed to run higher" not in _text(row)
        assert "neither figure stands in for the other" in row["description"]
        assert "they are different measurements" in row["fix_procedure"]


# ---------------------------------------------------------------------------
# 5. Scope: which machines, which years
# ---------------------------------------------------------------------------
class TestScope:
    def test_the_chf50_row_does_not_name_the_current_metropolitan(self):
        """The CHF50 is not the NCW50. Naming 'Metropolitan' in the model
        column would hand a 2020 Metropolitan this row at tier 0."""
        row = _row("carburetted CHF50")
        assert row["model"] == "CHF50"
        assert row["year_start"] == 2002
        assert row.get("year_end") is None, "the manual prints no end year"

    def test_the_pcx_row_is_held_to_the_years_a_document_ties_to_its_manual(self):
        """Refuter: an open end handed this row to the 2018-on PCX150, a
        149 cm3 engine. The 2015 owner's manual's KF18 / 153 cm3 is the last
        year a document ties to this service manual."""
        row = _row("PCX150 the alternator")
        assert (row["year_start"], row["year_end"]) == (2013, 2015)
        assert "149 cm3" in row["description"] and "KF18" in row["description"]
        assert "PCX160" not in row["model"] and "PCX 160" not in row["model"]

    def test_no_other_row_carries_a_year_window(self):
        """255B's F132 rule: a window no cited document supports gates
        retrieval for nothing."""
        for e in _entries():
            if e["make"] == "Honda":
                continue
            assert e.get("year_start") is None and e.get("year_end") is None, e["title"][:40]


# ---------------------------------------------------------------------------
# 6. Reachable — the entry point every diagnosis door uses
# ---------------------------------------------------------------------------
_MACHINES = [
    ("Honda", "PCX150", "PCX150 the alternator"),
    ("Honda", "CHF50", "carburetted CHF50"),
    ("Kymco", "Agility 50", "Two Kymco service manuals"),
    ("Kymco", "People S 250", "Two Kymco service manuals"),
    ("SYM", "Fiddle 50", "One SYM manual"),
    ("SYM", "Jet Euro 50", "One SYM manual"),
    ("SYM", "Joyride 125", "One SYM manual"),
    ("Piaggio", "Fly 50", "Piaggio's Fly 50"),
    ("Piaggio", "MP3 400", "Piaggio's Fly 50"),
    ("Vespa", "LX 50", "Vespa's 50 cc"),
    ("Vespa", "GTS 300", "Vespa's 50 cc"),
    ("Yamaha", "Zuma 125", "YW125 service manual"),
    ("Yamaha", "YW125", "YW125 service manual"),
]


class TestReachable:
    @pytest.mark.parametrize("make,model,fragment", _MACHINES)
    def test_the_machine_gets_its_row_at_tier_0(self, db, make, model, fragment):
        _, rows = known_issues_for_vehicle(make, model, db_path=db, limit=2000)
        mine = [r for r in rows if fragment.lower() in r["title"].lower()]
        assert mine and mine[0]["match_tier"] == "model", (make, model, [r["match_tier"] for r in mine])

    @pytest.mark.parametrize("make,model,fragment", _MACHINES)
    def test_the_chokepoint_keeps_it(self, db, make, model, fragment):
        """Unscoped rows survive rows_for_machine whatever the transmission
        resolves to."""
        _, rows = known_issues_for_vehicle(make, model, db_path=db, limit=2000)
        kept = rows_for_machine(rows, make=make, model=model, purpose="prompt",
                                db_path=db, record=False).rows
        assert any(fragment.lower() in r["title"].lower() for r in kept), (make, model)

    def test_the_pcx_row_outranks_the_make_wide_honda_charging_rows(self, db):
        """S0-5: three unverified Honda model=All rows reach every Honda
        scooter at tier 1. The PCX's own row must come first."""
        _, rows = known_issues_for_vehicle("Honda", "PCX150", db_path=db, limit=2000)
        titles = [r["title"] for r in rows]
        mine = next(i for i, t in enumerate(titles) if "PCX150 the alternator" in t)
        wide = [i for i, r in enumerate(rows) if r["match_tier"] == "make_wide"
                and re.search(r"stator|regulator/rectifier|charging", r["title"], re.I)]
        assert wide, "positive control: the make-wide charging rows must still be there"
        assert mine < min(wide)

    def test_a_gold_wing_does_not_get_them_above_tier_2(self, db):
        _, rows = known_issues_for_vehicle("Honda", "Gold Wing", db_path=db, limit=2000)
        for r in rows:
            if r["title"] in TITLES_354:
                assert r["match_tier"] == "make_other_model", r["title"][:50]

    def test_a_current_metropolitan_does_not_get_the_chf50_row_at_tier_0(self, db):
        _, rows = known_issues_for_vehicle("Honda", "Metropolitan", db_path=db, limit=2000)
        chf = [r for r in rows if "carburetted CHF50" in r["title"]]
        assert chf, "positive control: the row still reaches the make"
        assert chf[0]["match_tier"] == "make_other_model"

    @pytest.mark.parametrize("query,fragment", [
        ("regulator/rectifier", "PCX150 the alternator"),
        ("illumination coil", "One SYM manual"),
        ("lighting coil", "Two Kymco service manuals"),
        ("stator coil resistance", "YW125 service manual"),
    ])
    def test_search_finds_the_rows(self, db, query, fragment):
        rows = search_known_issues(query=query, db_path=db, limit=200)
        assert any(fragment.lower() in r["title"].lower() for r in rows), query
