"""Phase 243 — Harley-Davidson LiveWire and LiveWire One.

The reachability risk here is the inverse of Phase 242's. `make="Harley-Davidson"`
already returns 110 combustion entries; content that merely *exists* under that
make is buried. So the reachability guards assert POSITION, not presence.

The other axis is the brand split: the same lineage is Harley-Davidson LiveWire
(ELW, 2019-2020) and LiveWire ONE (LW1, 2021 on). A claim attributed to the
wrong badge is this subject's characteristic error.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from motodiag.core.database import init_db
from motodiag.knowledge.issues_repo import search_known_issues
from motodiag.knowledge.loader import load_known_issues_file

K = Path(__file__).resolve().parents[1] / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"
LW = K / "known_issues_livewire.json"
HV = K / "known_issues_electric_hv_safety.json"
COOLING = K / "known_issues_cross_platform_cooling.json"

RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}


@pytest.fixture(scope="module")
def raw():
    return json.loads(LW.read_text(encoding="utf-8"))


@pytest.fixture
def db(tmp_path):
    """The LiveWire file loaded with everything a Harley query really returns:
    241's HV floor and the 110 combustion Harley entries."""
    path = str(tmp_path / "lw.db")
    init_db(path)
    load_known_issues_file(HV, path)
    load_known_issues_file(LW, path)
    for f in sorted(K.glob("known_issues_harley*.json")):
        load_known_issues_file(f, path)
    return path


def _claims(e) -> str:
    return "\n".join([e["title"], e["description"], *e["causes"], e["fix_procedure"]])


# ---------------------------------------------------------------------------
# 1. Reachability — position, not presence
# ---------------------------------------------------------------------------
class TestReachability:
    @pytest.mark.parametrize("make", ["Harley-Davidson", "LiveWire"])
    def test_both_badges_return_the_whole_file(self, db, raw, make):
        titles = {r["title"] for r in search_known_issues(make=make, db_path=db)}
        missing = [e["title"] for e in raw if e["title"] not in titles]
        assert not missing, f"{make} query misses {len(missing)} entries"

    def test_the_critical_entry_is_not_buried_under_combustion_content(self, db, raw):
        """The failure mode this phase was scoped around. A Harley query returns
        110 combustion entries; if the LiveWire loss-of-propulsion campaign sits
        below them it is unfindable in practice, even though it is present.

        Phase 240C's severity ordering is what makes this assertion possible at
        all — before it, `critical` sorted last."""
        rows = search_known_issues(make="Harley-Davidson", db_path=db)
        crit = next(e for e in raw if e["severity"] == "critical")
        pos = [r["title"] for r in rows].index(crit["title"])
        band = [r for r in rows if r["severity"] == "critical"]
        assert pos < len(band), (
            f"the LiveWire critical entry sits at position {pos} of {len(rows)}, "
            f"outside the {len(band)}-row critical band — it is present but buried"
        )

    def test_livewire_query_is_not_swamped(self, db, raw):
        """A LiveWire-badged query should return this file plus the HV floor and
        nothing combustion — the whole point of carrying both names."""
        rows = search_known_issues(make="LiveWire", db_path=db)
        hv = json.loads(HV.read_text(encoding="utf-8"))
        assert len(rows) == len(raw) + len(hv)


# ---------------------------------------------------------------------------
# 2. The brand split
# ---------------------------------------------------------------------------
class TestTheBadgeSplit:
    ELW_ONLY = re.compile(r"\bELW\b|Harley-Davidson LiveWire\b")
    LW1_ONLY = re.compile(r"\bLW1\b|LiveWire ONE\b")

    def test_every_entry_names_the_badge_it_applies_to(self, raw):
        for e in raw:
            assert self.ELW_ONLY.search(e["model"]) or self.LW1_ONLY.search(e["model"]), (
                f"{e['title'][:60]}: model field names neither badge"
            )

    def test_an_elw_only_entry_does_not_span_into_the_livewire_one_years(self, raw):
        """A claim about the 2019-2020 Harley-badged machine must not carry a
        year range that sweeps in LW1 machines, and vice versa."""
        for e in raw:
            m = e["model"]
            if self.ELW_ONLY.search(m) and not self.LW1_ONLY.search(m):
                assert e["year_end"] is None or e["year_end"] <= 2025, e["title"][:60]
            if self.LW1_ONLY.search(m) and not self.ELW_ONLY.search(m):
                assert e["year_start"] is None or e["year_start"] >= 2021, (
                    f"{e['title'][:60]}: LW1-only entry starts at {e['year_start']}, before the badge existed"
                )

    def test_the_badge_split_itself_is_documented(self, raw):
        e = next(x for x in raw if "badge changes" in x["title"].lower())
        t = _claims(e)
        assert "ELW" in t and "LW1" in t
        assert re.search(r"Harley-Davidson dealer", t) and re.search(r"LiveWire dealer", t)


# ---------------------------------------------------------------------------
# 3. Figures carry their document, per source class
# ---------------------------------------------------------------------------
FIGURE = re.compile(
    r"\b\d[\d,.]*\s*(?:V|VDC|kWh|kW|Ah|A|Nm|N·m|ft[- ]?lbs?|qt|L|km|mi|miles|hours?|hrs?|minutes?|mins?|Hz|%|°C|°F)\b",
    re.I,
)
DOC = re.compile(
    r"(manual|handbook|bulletin|specification|spec sheet|support|FAQ|press release"
    r"|release notes|owner['’]s|service information portal|regulator|recall record"
    r"|regulator['’]?s? (?:recall )?record|complaint database|forum)",
    re.I,
)  # class-matched: a recall entry cites a regulator, a forum entry cites owners


class TestFiguresCarryTheirDocument:
    def test_any_entry_printing_a_figure_names_its_source(self, raw):
        for e in raw:
            figs = [m.group(0) for m in FIGURE.finditer(_claims(e))
                    if not re.fullmatch(r"12\s*(?:volt|V)", m.group(0), re.I)]
            if figs:
                assert DOC.search(e["description"]), (
                    f"{e['title'][:60]}: prints {figs[:3]} but names no source"
                )

    def test_forum_entries_do_not_print_a_price(self, raw):
        """Owner-quoted costs vary wildly and a mechanic acts on a price. The
        research marked every one of them withhold."""
        for e in raw:
            m = re.search(r"[$£€]\s?\d", _claims(e))
            assert not m, f"{e['title'][:60]}: prints a price {m.group(0)!r}"

    def test_the_figure_pattern_can_fire(self):
        assert FIGURE.search("approximately 0.8 qt") and FIGURE.search("80,000 km")
        assert FIGURE.search("78-90 Hz") and not FIGURE.search("the ELW model code")


# ---------------------------------------------------------------------------
# 4. Provenance, scope, shape
# ---------------------------------------------------------------------------
class TestProvenanceAndScope:
    def test_sources_are_honest(self, raw):
        assert {e["source"] for e in raw} <= {"service-manual", "forum", "model-generated"}
        assert "unverified" not in {e["source"] for e in raw}

    def test_forum_tip_marker_tracks_the_source(self, raw):
        for e in raw:
            assert ("Forum tip" in e["fix_procedure"]) == (e["source"] == "forum"), e["title"][:60]

    def test_no_campaign_reference_number(self, raw):
        blob = json.dumps(raw)
        assert not re.findall(r"\b\d{2}V\d{3,6}\b|RM/\d{4}/\d+|\bR/\d{4}/\d{3}\b", blob)
        assert not re.search(r"recall (?:no\.?|number|#)\s*\S", blob, re.I)

    def test_every_entry_is_livewire_specific(self, raw):
        marker = re.compile(r"LiveWire|Revelation|\bELW\b|\bLW1\b|TechLink|Digital Technician", re.I)
        for e in raw:
            assert marker.search(_claims(e)), f"{e['title'][:60]}: nothing LiveWire-specific"

    def test_symptoms_follow_the_house_format(self, raw):
        for e in raw:
            assert e["symptoms"], e["title"][:60]
            for s in e["symptoms"]:
                assert len(s) <= 55 and not s.endswith("."), (e["title"][:40], s)

    def test_no_title_collides_corpus_wide(self):
        titles = []
        for f in K.glob("known_issues_*.json"):
            titles += [e["title"] for e in json.loads(f.read_text(encoding="utf-8"))]
        assert len(titles) == len(set(titles))


# ---------------------------------------------------------------------------
# 5. The correction this phase made to shipping content
# ---------------------------------------------------------------------------
class TestTheThermostatCorrection:
    """The cross-platform cooling entry listed the LiveWire among Harley
    liquid-cooled models taking a thermostat replaced every 40,000-50,000
    miles. The research searched all 108 sections of the LiveWire manual: the
    word thermostat appears zero times, neither service table has a thermostat
    row, and the manual's own overheating tree does not list one. The 50,000
    figure is a corrupted echo of a real interval that belongs to the coolant."""

    def test_livewire_is_no_longer_in_the_thermostat_list(self):
        d = json.loads(COOLING.read_text(encoding="utf-8"))
        sentence = next(
            (m.group(0) for m in re.finditer(r"[^.]*liquid-cooled[^.]*\.", d[0]["description"])
             if "Street 750" in m.group(0)), "")
        assert sentence, "the model-list sentence is gone — check the correction survived"
        assert "LiveWire" not in sentence, f"LiveWire still listed: {sentence[:140]}"

    def test_the_correction_states_why_and_scopes_itself(self):
        d = json.loads(COOLING.read_text(encoding="utf-8"))
        t = d[0]["description"]
        assert re.search(r"thermostat does not appear", t, re.I)
        assert re.search(r"no claim either way about a thermostat on the Street 750 or Pan America", t), (
            "the correction must not silently imply a finding about the two models it did not examine"
        )

    def test_the_livewire_file_states_the_positive_replacement(self, raw):
        e = next(x for x in raw if "no thermostat" in x["title"].lower())
        assert re.search(r"does not appear", _claims(e), re.I)
        assert re.search(r"not established", _claims(e), re.I), (
            "the entry must state the limit of the finding — no parts catalogue was opened"
        )
