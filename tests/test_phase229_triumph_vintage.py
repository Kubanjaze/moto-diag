"""Phase 229 — Triumph vintage (pre-Hinckley Meriden + early Hinckley).

**The most saturated topic in the corpus, and the saturation has a
shape.** Four vintage files hold 40 entries — Honda, Kawasaki, Suzuki,
Yamaha, ten each — plus twenty cross-platform carburettor and ignition
entries. Read their titles together and every make's file covers the
*same ten topics*: cam chain tensioner, charging, carb rebuild, points
ignition, petcock and tank rust, fork seals, brakes, oil leaks, wiring
harness, drive chain. That is a template, and a Triumph file following it
would be the fifth telling. Worse, `cross_platform_ignition` already owns
points-versus-electronic conversion **and names Boyer Bransden for
British twins specifically** — the single most obvious Triumph-vintage
entry was already written, by another file.

**But every British-specific term returned zero.** Whitworth, BSF, Cycle
thread, positive earth, oil-in-frame, Amal, modular, 360-degree crank,
dynamo — none appeared anywhere in 806 entries. So this file is built
entirely on the axis the corpus lacks: not what is old about an old bike,
but what is *British* about it. The bar asserted below is that every
entry names such a term, and the counter-assertion sweeps all six
existing vintage and cross-platform files for zero.

**Refutation removed six claims.** The research said Whitworth
disappeared after 1962 — its own cited source shows Whitworth nuts on
1963–67 unit engines. It inverted the oil-in-frame seat height. It
attributed valve sizes and balancer counts to a source containing
neither. It gave a recall's year range as 1999–2004 when the regulator
lists 1997. It extrapolated hard starting and misfire from a source
saying only that spark is more reliable with correct polarity. And it
framed the five-speed as retro-only when the 1994–95 Speed Triple was
five-speed too — which changes a gearbox quote. None of the six is in the
shipped file, and each is asserted absent.
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
VINTAGE = K / "known_issues_triumph_vintage.json"
TRIUMPH_FILES = sorted(K.glob("known_issues_triumph_*.json"))
COMPAT = SEED_DATA_DIR.parent.parent / "hardware" / "compat_data" / "compat_matrix.json"

#: The five Triumph compat rows that existed before Phase 230 filled the
#: gap. Phases 226-229 each asserted the count was exactly 5 — the right
#: guard while the gap was open, and the wrong shape once it closed. Same
#: "constant standing in for an invariant" bug as the KTM count at 222.
#: These now assert the original rows SURVIVED, which is what they meant.
ORIGINAL_TRIUMPH_ROWS = {
    ("obdlink-mx-plus", "tiger%"),
    ("obdlink-mx-plus", "675"),
    ("obdlink-lx", "bonneville%"),
    ("elm327-generic-bt-clone", "675"),
    ("obdlink-sx", "tiger%"),
}


#: The axis this file exists on. Every entry must name one — it is what
#: forty Japanese-vintage entries cannot say.
BRITISH_SPECIFIC = {
    "Whitworth": r"Whitworth",
    "BSF": r"\bBSF\b",
    "Cycle thread": r"Cycle thread|British Standard Cycle",
    "positive earth": r"positive earth",
    "oil-in-frame": r"oil-in-frame|oil in frame",
    "Amal": r"\bAmal\b",
    "360-degree": r"360-degree",
    "wasted spark": r"wasted spark",
    "sludge trap": r"sludge trap",
    "Meriden": r"Meriden",
    "Hinckley": r"Hinckley",
    "modular": r"modular",
    "T595": r"T595",
    "T509": r"T509",
    "T309": r"T309",
    "Pozidriv": r"Pozidriv",
}

#: The ten topics every existing vintage file already covers. None may be
#: the *subject* of an entry here.
TEMPLATE_TOPICS = (
    r"cam chain tensioner|charging system|carburett?or (rebuild|sync)|"
    r"points ignition|petcock|tank rust|fork seal|brake (master|caliper)|"
    r"wiring harness|drive chain"
)

#: The six claims refutation removed. Each is asserted absent.
REFUTED = {
    "Whitworth ended ~1962": r"Whitworth[^.]{0,60}(1962|disappear)",
    "seat height inverted": r"32\.5[^.]{0,40}(tall|problem|high)",
    "unsourced valve/balancer specs": r"32 ?mm inlet|28 ?mm exhaust|two balancer",
    "recall year range wrong": r"1999[^.]{0,30}2004[^.]{0,60}fuel connector",
    "polarity symptom overreach": r"polarity[^.]{0,60}(hard start|misfire)",
    "five-speed as retro-only": r"five-speed[^.]{0,60}retro[^.]{0,30}only",
}


def _claims(e: dict) -> str:
    return " ".join([e["title"], e["description"], e["fix_procedure"]] + e["causes"])


def _british(e: dict, where: str = "both") -> list[str]:
    text = e["title"] if where == "title" else _claims(e)
    return [n for n, p in BRITISH_SPECIFIC.items() if re.search(p, text)]


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "vintage.db")
    init_db(path)
    load_known_issues_file(VINTAGE, path)
    return path


@pytest.fixture
def raw():
    return json.loads(VINTAGE.read_text(encoding="utf-8"))


class TestContent:
    def test_loads_thirteen(self, db_path):
        assert count_known_issues(db_path=db_path) == 13

    def test_all_are_triumph(self, raw, db_path):
        assert {e["make"] for e in raw} == {"Triumph"}
        assert len(search_known_issues(make="Triumph", db_path=db_path)) == 13

    def test_severity_years_procedures(self, raw):
        for e in raw:
            assert e["severity"] in {"critical", "high", "medium", "low"}
            assert 1950 <= e["year_start"] <= e["year_end"] <= 2004, e["title"]
            assert e["fix_procedure"].strip() and e["estimated_hours"] > 0, e["title"]
            assert e["parts_needed"], e["title"]

    def test_both_eras_are_covered(self, raw):
        meriden = [e for e in raw if e["year_start"] < 1991]
        hinckley = [e for e in raw if e["year_start"] >= 1991]
        assert len(meriden) >= 5 and len(hinckley) >= 5


class TestTheAxisIsBritishnessNotAge:
    def test_every_entry_names_a_british_specific_term(self, raw):
        for e in raw:
            assert _british(e, "title"), f"{e['title']}: title names none"
            assert _british(e, "both"), f"{e['title']}: body names none"

    def test_the_forty_japanese_vintage_entries_score_zero(self):
        """The counter-assertion, and the reason this file is not a
        fifth telling. Swept over all six existing vintage and
        cross-platform files, every entry."""
        terms = {k: v for k, v in BRITISH_SPECIFIC.items()}
        for name in ("honda_vintage", "kawasaki_vintage", "suzuki_vintage",
                     "yamaha_vintage", "cross_platform_carbs",
                     "cross_platform_ignition"):
            f = K / f"known_issues_{name}.json"
            for e in json.loads(f.read_text(encoding="utf-8")):
                hits = [n for n, p in terms.items() if re.search(p, json.dumps(e))]
                assert not hits, f"{name}: {e['title'][:40]} scores {hits}"

    def test_no_entry_takes_a_template_topic_as_its_subject(self, raw):
        """The ten topics every make's vintage file already covers. They
        may be referred to; none may be what an entry is about."""
        for e in raw:
            hits = re.findall(TEMPLATE_TOPICS, e["title"], re.I)
            assert not hits, f"{e['title']}: template topic as subject {hits}"

    def test_the_points_entry_was_not_rewritten(self, raw):
        """`cross_platform_ignition` already owns points-versus-electronic
        conversion and already names Boyer Bransden for British twins.
        This file may cite Boyer for its own claims; it may not make
        points conversion an entry."""
        for e in raw:
            assert "points" not in e["title"].lower(), e["title"]
        generic = json.loads(
            (K / "known_issues_cross_platform_ignition.json").read_text(encoding="utf-8")
        )
        assert any("Points ignition" in x["title"] for x in generic), (
            "the entry this file defers to has gone"
        )


class TestRefutationRemovedSixClaims:
    @pytest.mark.parametrize("label,pattern", sorted(REFUTED.items()))
    def test_the_refuted_claim_is_absent(self, raw, label, pattern):
        hit = re.search(pattern, json.dumps(raw), re.I)
        assert not hit, f"{label}: {hit.group()[:80]!r}"

    def test_whitworth_is_not_bounded_at_the_pre_unit_era(self, raw):
        """The research said Whitworth disappeared after the last
        pre-units; its own source shows Whitworth nuts on 1963-67 unit
        engines. The entry now says the standards are mixed and must be
        gauged."""
        threads = [e for e in raw if "thread standards" in e["title"]][0]
        text = _claims(threads)
        assert re.search(r"gauge", text, re.I), "the entry does not say to gauge"
        assert re.search(r"well after the pre-unit era|mixed standards", text)

    def test_the_five_speed_covers_the_speed_triple_not_only_retros(self, raw):
        """Refuted: the 1994-95 Speed Triple was five-speed too, which
        changes a gearbox quote."""
        five = [e for e in raw if "five-speed" in e["title"]]
        assert five
        text = _claims(five[0])
        assert "Speed Triple" in text
        assert re.search(r"retro", text), "the retro models are no longer mentioned"

    def test_the_recall_entry_does_not_state_a_narrow_year_range(self, raw):
        """The regulator lists 1997 machines in the fuel-connector
        campaign; the research said 1999. The entry gives the range the
        regulator gives."""
        rec = [e for e in raw if "frame headstock weld" in e["title"]][0]
        assert "1997" in _claims(rec) or "1997" in rec["model"]


class TestTheDiagnosticContent:
    def test_the_wasted_spark_deduction_is_stated_both_ways(self, raw):
        """The most useful entry here: one dead cylinder cannot be the
        module; both dead can be. Stating only the first half leaves the
        reader unable to use it."""
        ws = [e for e in raw if "wasted spark" in e["title"]][0]
        text = _claims(ws)
        assert re.search(r"cannot be the ignition unit|cannot be the ignition box", text)
        assert re.search(r"both cylinders are dead|If \*\*both\*\*|if both", text, re.I)

    def test_the_amal_screw_direction_is_stated_explicitly(self, raw):
        """The single most direct trap for a Japanese-trained hand, and
        it must say which way, not merely that it differs."""
        amal = [e for e in raw if "AIR screw" in e["title"]][0]
        text = _claims(amal)
        assert re.search(r"in (is|richens|makes).{0,30}rich", text, re.I)
        assert re.search(r"invert|opposite", text, re.I)

    def test_the_sludge_trap_rebuild_consequence_is_stated(self, raw):
        trap = [e for e in raw if "sludge trap" in e["title"]][0]
        text = _claims(trap)
        assert re.search(r"split", text, re.I)
        assert re.search(r"big end", text, re.I)

    def test_the_oil_in_frame_crack_is_framed_as_structural(self, raw):
        oif = [e for e in raw if "frame is the oil tank" in e["title"]][0]
        assert re.search(r"structural", _claims(oif), re.I)

    def test_the_badge_is_not_the_capacity_gives_both_numbers(self, raw):
        badge = [e for e in raw if "badge is not the capacity" in e["title"]][0]
        text = _claims(badge)
        assert "885" in text and "1180" in text

    def test_the_t_number_entry_gives_the_real_capacities(self, raw):
        t = [e for e in raw if "project code, not a capacity" in e["title"]][0]
        text = _claims(t)
        assert "955" in text and "885" in text
        assert re.search(r"renamed", text), "the strongest evidence is missing"


class TestDeferralBoundaries:
    def test_no_modern_bonneville_content(self, raw):
        forbidden = r"T100|T120 Black|Street Twin|Speedmaster 1200"
        for e in raw:
            assert not re.findall(forbidden, _claims(e)), e["title"]

    def test_no_modern_tiger_content(self, raw):
        forbidden = r"Tiger 800|Tiger 900|Tiger 1200|T-plane"
        for e in raw:
            assert not re.findall(forbidden, _claims(e)), e["title"]

    def test_no_modern_triple_content(self, raw):
        """228 owns the 675/765/1050/1200 machines. The T309 Speed
        Triple here is an 885 from the modular era and is this phase's."""
        forbidden = r"Street Triple|Daytona 675|Daytona Moto2|\b765\b|Speed Triple 1200"
        for e in raw:
            assert not re.findall(forbidden, _claims(e)), e["title"]

    def test_the_early_speed_triple_entry_is_year_bounded(self, raw):
        st = [e for e in raw if "T309" in e["title"]][0]
        assert st["year_end"] <= 1996, "overlaps Phase 228's population"

    def test_no_fault_codes_or_tooling_content(self, raw):
        forbidden = r"\bP0\d{3}\b|\bP1\d{3}\b|TuneECU|TuneBoy|dealer mode"
        for e in raw:
            assert not re.findall(forbidden, _claims(e), re.I), e["title"]
        for e in raw:
            assert e["dtc_codes"] == [], e["title"]

    def test_the_adapter_catalog_is_unchanged(self):
        matrix = json.loads(COMPAT.read_text(encoding="utf-8"))
        rows = {(r["adapter_slug"], r["model_pattern"])
                for r in matrix if r["make"] == "triumph"}
        assert ORIGINAL_TRIUMPH_ROWS <= rows, ORIGINAL_TRIUMPH_ROWS - rows


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

    def test_no_symptom_resolves_to_two_triumph_files(self, raw):
        mine = {s for e in raw for s in e["symptoms"]}
        for f in TRIUMPH_FILES:
            if f == VINTAGE:
                continue
            theirs = {s for e in json.loads(f.read_text(encoding="utf-8"))
                      for s in e["symptoms"]}
            assert not (mine & theirs), f"{f.name}: {mine & theirs}"

    def test_no_title_collides_corpus_wide(self):
        titles = []
        for f in K.glob("known_issues_*.json"):
            titles += [e["title"] for e in json.loads(f.read_text(encoding="utf-8"))]
        assert len(titles) == len(set(titles))

    @pytest.mark.parametrize("needle", [
        "rounded off a fastener on a british bike",
        "is this bike positive earth",
        "oil weeping from the frame",
        "where is the oil filter on a triumph twin",
        "one cylinder has no spark on a triumph twin",
        "amal pilot screw direction",
        "fasteners keep coming loose",
        "is a triumph 900 really 900cc",
        "is the t595 a 595cc bike",
        "is this hinckley triumph carbed or injected",
        "five speed or six speed on a speed triple",
        "cracked headstock on an early hinckley",
        "metric or whitworth on this triumph",
    ])
    def test_a_mechanic_query_finds_the_entry(self, db_path, needle):
        assert find_issues_by_symptom(needle, db_path), needle
