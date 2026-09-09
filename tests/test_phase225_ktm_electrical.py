"""Phase 225 — KTM electrical + FI. Closes the KTM block.

The direct analogue of 215 (BMW) and 220 (Ducati), and the first
electrical phase whose external facts were **researched and adversarially
refuted before being written** rather than recalled. Five questions went
to agents with web access; every finding was refuted by two lenses
(source quality; contradiction search). Four survived. The tooling
finding was refuted on its function-list detail only — identity,
coverage and hardware held — and the refuters supplied the corrected
per-model list that the adapter record now carries.

**The cylinder mapping was settled from KTM's own document.** The claim
that cylinder 1 is the rear on the LC8 rested on an unattributed
transcription and a forum post, which is not enough to ship a misfire
row on. The official 950/990 repair manual's error-code table (p. 162)
lists P0201 injector rear / P0202 front, P0351 coil rear / P0352 front,
P0130 lambda rear / P0150 front — every first-indexed code addresses the
rear cylinder. The fifth refuter independently downloaded the same
manual and confirmed it. That is what the P0301/P0302/P0130/P0150 rows
are built on, and the mapping is guarded against contradicting itself
(the 220 regex). For the LC8c parallel twin the side is **unknown**, and
the rows say so rather than guess.

**A refuter caught an overreach in my draft.** I had written the TuneECU
reset sequence as the fix "after throttle-body work". No source ties it
to that; it is documented after a map load, on the 990/RC8 only, and the
CAN-bus 1050–1290 bikes get no adjustments through TuneECU at all. The
rows and the entry were corrected before this test was written.

**Three roadmap corrections in one row.** "Keihin FI" is right for the
LC8, LC4 and EXC-F only — the LC8c and every Bajaj-built bike are Bosch,
the TPI two-strokes Continental, the TBI two-strokes Vitesco. "Tuneboy"
lists KTMs but as a tune editor; TuneECU is the diagnostic tool.
"PowerParts cross-platform" is not a KTM term; it means shared article
numbers across KTM, Husqvarna and GasGas.

**Blink codes are cited, not invented.** Every two-digit blink code
mentioned in the DTC rows is asserted to be in the set the manual's
table actually contains.
"""

from __future__ import annotations

import json
import re

import pytest

from motodiag.core.config import SEED_DATA_DIR
from motodiag.core.database import init_db
from motodiag.knowledge.dtc_repo import get_dtcs
from motodiag.knowledge.issues_repo import (
    count_known_issues,
    find_issues_by_symptom,
    search_known_issues,
)
from motodiag.knowledge.loader import load_dtc_file, load_known_issues_file

D = SEED_DATA_DIR / "dtc_codes"
K = SEED_DATA_DIR / "knowledge"
KTM_DTC = D / "ktm.json"
GEN_DTC = D / "generic.json"
ELEC = K / "known_issues_ktm_electrical.json"
KTM_FILES = sorted(K.glob("known_issues_ktm_*.json"))
COMPAT = SEED_DATA_DIR.parent.parent / "hardware" / "compat_data"
ADAPTERS = COMPAT / "adapters.json"
MATRIX = COMPAT / "compat_matrix.json"
SLUG = "tuneecu-ktm-android"

STD_CODE = re.compile(r"^[PUBC][0-3][0-9A-F]{3}$")
#: The two-digit blink codes on p. 162 of the KTM 950/990 repair manual
#: for the codes this file touches. Any other number cited is invented.
MANUAL_BLINK_CODES = {"06", "17", "18", "24", "25", "33", "34", "37", "38"}


def _claims(e: dict) -> str:
    return " ".join([e["title"], e["description"], e["fix_procedure"]] + e["causes"])


@pytest.fixture
def dtc_db(tmp_path):
    path = str(tmp_path / "d.db")
    init_db(path)
    load_dtc_file(GEN_DTC, path)
    load_dtc_file(KTM_DTC, path)
    return path


@pytest.fixture
def codes():
    return json.loads(KTM_DTC.read_text(encoding="utf-8"))


@pytest.fixture
def issues():
    return json.loads(ELEC.read_text(encoding="utf-8"))


def _first(rows):
    return rows[0] if isinstance(rows, list) else list(rows.values())[0]


class TestNoFabricatedCodes:
    def test_every_code_is_standard_format(self, codes):
        for c in codes:
            assert STD_CODE.match(c["code"]), c["code"]

    def test_no_invented_manufacturer_range_code(self, codes):
        """KTM does use P1xxx — P1590 side stand, P1105/P1106 hoses —
        but those are KTM's numbers to publish, not this file's."""
        for c in codes:
            assert not c["code"].startswith("P1"), c["code"]

    def test_no_duplicates_and_all_marked_ktm(self, codes):
        assert len({c["code"] for c in codes}) == len(codes)
        assert {c["make"] for c in codes} == {"KTM"}

    def test_vocabularies_are_valid(self, codes):
        from motodiag.core.models import Severity, SymptomCategory

        cats = {e.value for e in SymptomCategory}
        sevs = {e.value for e in Severity}
        for c in codes:
            assert c["category"] in cats and c["severity"] in sevs, c["code"]

    def test_every_blink_code_cited_is_in_the_manual(self, codes):
        cited = set(re.findall(r"blink code (\d\d)", json.dumps(codes)))
        assert cited, "the blink-code layer is never mentioned"
        assert cited <= MANUAL_BLINK_CODES, cited - MANUAL_BLINK_CODES

    def test_p0560_not_p0562_is_the_ktm_voltage_code(self, codes):
        """The manual's table uses P0560 for control-unit supply
        voltage. A KTM row on P0562 would be shadowing the generic
        entry with a code KTM does not set."""
        by = {c["code"]: c for c in codes}
        assert "P0560" in by and "P0562" not in by


class TestEveryShadowingRowEarnsIt:
    def test_shadowing_rows_exist_and_differ(self, codes):
        generic = {c["code"]: c for c in json.loads(GEN_DTC.read_text(encoding="utf-8"))}
        shadowing = [c for c in codes if c["code"] in generic]
        assert len(shadowing) >= 1, "nothing shadows — no comparison to make"
        for c in shadowing:
            g = generic[c["code"]]
            assert c["common_causes"] != g.get("common_causes"), c["code"]
            assert c["fix_summary"] != g.get("fix_summary"), c["code"]

    def test_a_ktm_gets_the_ktm_row(self, dtc_db):
        assert _first(get_dtcs(["P0301"], make="KTM", db_path=dtc_db))["make"] == "KTM"

    def test_another_make_still_gets_generic(self, dtc_db):
        assert _first(get_dtcs(["P0301"], make="Honda", db_path=dtc_db))["make"] is None


class TestTheCylinderMappingComesFromTheManual:
    def test_first_indexed_codes_address_the_rear(self, codes):
        by = {c["code"]: c for c in codes}
        for code in ("P0301", "P0130"):
            assert re.search(r"\bREAR\b", json.dumps(by[code])), code
        for code in ("P0302", "P0150"):
            assert re.search(r"\bFRONT\b", json.dumps(by[code])), code

    def test_the_mapping_never_contradicts_itself(self, codes):
        """Both misfire rows restate it. Every statement must agree:
        1 is rear, 2 is front (the Phase 220 guard, inverted for KTM)."""
        expected = {"1": "rear", "2": "front"}
        stated = re.findall(
            r"cylinder[- ]?([12])[^.]{0,80}?\b(rear|front)\b", json.dumps(codes), re.I
        )
        assert stated, "the mapping is never stated"
        for num, side in stated:
            assert side.lower() == expected[num], f"cylinder {num} called {side}"

    def test_the_lc8c_side_is_declared_unknown_not_guessed(self, codes):
        by = {c["code"]: c for c in codes}
        for code in ("P0301", "P0302"):
            text = json.dumps(by[code])
            assert "LC8c" in text and "not established" in text, code

    def test_the_aftermarket_colour_trap_is_named(self, codes):
        """Dynojet routes orange to the FRONT injector on the 1290 — the
        opposite of KTM's rear-first numbering. A shop reading harness
        colour as cylinder number works on the wrong cylinder."""
        assert "Dynojet" in json.dumps(codes)


class TestTheDraftOverreachWasCorrected:
    def test_no_row_claims_the_reset_is_for_throttle_body_work(self, codes):
        """A refuter found no source tying the TuneECU sequence to
        throttle-body replacement. The rows now say it is documented
        after a map load and not established after a throttle-body."""
        blob = json.dumps(codes)
        assert "map load" in blob
        assert "not established" in blob
        assert not re.search(r"after throttle-body (or TPS )?work[^.]{0,40}(is usually|are followed by)", blob)

    def test_the_can_bus_bikes_are_stated_to_have_no_tuneecu_adjustments(self, codes, issues):
        blob = json.dumps(codes) + json.dumps(issues)
        assert re.search(r"no (TuneECU )?adjustments", blob, re.I)


class TestTheRoadmapCorrections:
    def test_four_suppliers_not_one(self, issues):
        blob = json.dumps(issues)
        for s in ("Keihin", "Bosch", "Continental", "Vitesco"):
            assert s in blob, f"{s} never named"
        supplier = [e for e in issues if "engine-management supplier" in e["title"]][0]
        text = _claims(supplier)
        assert re.search(r"Bosch[^.]{0,80}(790|890|LC8c)", text)
        assert re.search(r"Bosch[^.]{0,120}(125|390|Bajaj)", text)

    def test_tuneboy_is_a_tune_editor_and_tuneecu_the_diagnostic_tool(self, issues):
        tools = [e for e in issues if "TuneECU reaches" in e["title"]][0]
        text = _claims(tools)
        assert "tune-editing" in text or "tune editor" in text
        assert "not a diagnostic tool" in text or "not diagnostics" in text or "not offering diagnostics" in text

    def test_powerparts_cross_platform_is_defined_as_shared_part_numbers(self, issues):
        pp = [e for e in issues if "PowerParts" in e["title"]][0]
        text = _claims(pp)
        assert "Husqvarna" in text and "GasGas" in text
        assert "not a KTM term" in text


class TestNothingIsAssertedThatTheResearchDidNotEstablish:
    def test_no_dealer_tool_brand_name_is_invented(self, issues):
        """No branded KTM dealer-tool name was verified. The entries say
        'the KTM diagnostics tool', which is KTM's own phrase."""
        blob = json.dumps(issues)
        assert "KTM diagnostics tool" in blob
        assert not re.search(r"\bXC[_-]?2\b|Dealer\.?net tool|KTM DT\b", blob)

    def test_the_abs_hex_format_claim_was_not_used(self, issues):
        """A refuter flagged it as having no cited source."""
        assert "hex" not in json.dumps(issues).lower()

    def test_the_single_case_report_is_labelled_as_one(self, issues):
        p1 = [e for e in issues if "P1xxx" in e["title"]][0]
        text = _claims(p1).lower()
        assert "one documented owner report" in text or "a reported case" in text


class TestTheAdapterIsInTheCatalog:
    @pytest.fixture(scope="class")
    def adapters(self):
        return json.loads(ADAPTERS.read_text(encoding="utf-8"))

    @pytest.fixture(scope="class")
    def matrix(self):
        return json.loads(MATRIX.read_text(encoding="utf-8"))

    def test_the_adapter_exists(self, adapters):
        assert SLUG in {a["slug"] for a in adapters}

    def test_it_matches_the_catalog_schema(self, adapters):
        tu = next(a for a in adapters if a["slug"] == SLUG)
        peer = next(a for a in adapters if a["slug"] == "obdlink-mx-plus")
        assert set(tu) == set(peer)

    def test_mode22_is_false(self, adapters):
        """TuneECU speaks KTM's own protocol, not generic Mode 22."""
        assert next(a for a in adapters if a["slug"] == SLUG)["supports_mode22"] is False

    def test_the_price_is_labelled_as_a_conversion(self, adapters):
        """No USD price could be established. The record carries the EUR
        licence converted and says so, rather than a made-up USD figure
        presented as native."""
        tu = next(a for a in adapters if a["slug"] == SLUG)
        assert tu["price_usd_cents"] > 0
        assert "converted" in tu["known_issues"]

    def test_compat_rows_are_ktm_only_with_provenance(self, matrix):
        rows = [r for r in matrix if r["adapter_slug"] == SLUG]
        assert rows
        assert {r["make"] for r in rows} == {"ktm"}
        for r in rows:
            assert r["verified_by"].strip(), r["model_pattern"]
            assert "tuneecu" in r["verified_by"].lower(), r["model_pattern"]

    def test_the_bosch_bikes_are_marked_incompatible_not_omitted(self, matrix):
        """The most useful rows. A shop checking a 790 should be told
        no, not find nothing."""
        rows = {r["model_pattern"]: r for r in matrix if r["adapter_slug"] == SLUG}
        for pat in ("390%", "790%", "890%", "125%", "EXC%", "990 Duke%"):
            assert rows[pat]["status"] == "incompatible", pat

    def test_the_990_lc8_row_cannot_match_the_990_duke(self, matrix):
        """Same displacement, different engine, different supplier. The
        LC8 row is year-bounded so a 2024 990 Duke does not fall into
        the full-access row by pattern."""
        rows = [r for r in matrix if r["adapter_slug"] == SLUG and r["model_pattern"] == "990%"]
        assert rows and all(r["year_max"] <= 2013 for r in rows)

    def test_the_can_rows_are_partial_not_full(self, matrix):
        """No adjustments through TuneECU on these — 'full' would send a
        shop expecting an adaptation reset."""
        rows = {r["model_pattern"]: r for r in matrix if r["adapter_slug"] == SLUG}
        for pat in ("1290%", "1190 Adventure%", "1050%", "1090%"):
            assert rows[pat]["status"] == "partial", pat

    def test_the_gap_221_left_is_closed(self, matrix):
        ktm = [r for r in matrix if r["make"] == "ktm"]
        assert any(r["status"] == "full" for r in ktm)


class TestTheWholeKtmBlockCoheres:
    def test_the_whole_ktm_block_loads_together(self, tmp_path):
        path = str(tmp_path / "ktm.db")
        init_db(path)
        expected = 0
        for f in KTM_FILES:
            load_known_issues_file(f, path)
            expected += len(json.loads(f.read_text(encoding="utf-8")))
        assert count_known_issues(db_path=path) == expected
        # Phase 240B: `expected` is the sum of file lengths, which equals the
        # make-filtered count only while every entry in these files carries
        # the make verbatim -- `make LIKE '%X%'` is a substring match. The
        # Aprilia block already breaks that (compound "Aprilia and MV Agusta"
        # makes), so count the filtered number rather than assuming it.
        entries = [e for f in KTM_FILES for e in json.loads(f.read_text(encoding="utf-8"))]
        assert len(search_known_issues(make="KTM", db_path=path)) == sum(
            1 for e in entries if "ktm" in e["make"].lower()
        )
        assert len(json.loads(ELEC.read_text(encoding="utf-8"))) == 7

    def test_no_title_collides(self):
        titles = []
        for f in KTM_FILES:
            titles += [e["title"] for e in json.loads(f.read_text(encoding="utf-8"))]
        assert len(titles) == len(set(titles))

    def test_no_symptom_resolves_to_two_ktm_files(self, issues):
        mine = {s for e in issues for s in e["symptoms"]}
        for f in KTM_FILES:
            if f == ELEC:
                continue
            theirs = {s for e in json.loads(f.read_text(encoding="utf-8")) for s in e["symptoms"]}
            assert not (mine & theirs), f"{f.name}: {mine & theirs}"

    def test_the_1290_read_access_point_is_not_restated(self, issues):
        """The 1290 file already says an emissions-level scan will not
        see MSC faults. This file's job is the tool landscape."""
        for e in issues:
            assert "no codes from that tool is not evidence" not in e["description"]


class TestProvenanceAndSearchability:
    @pytest.fixture
    def issue_db(self, tmp_path):
        path = str(tmp_path / "e.db")
        init_db(path)
        load_known_issues_file(ELEC, path)
        return path

    def test_every_entry_is_tagged(self, issue_db, issues):
        rows = search_known_issues(make="KTM", db_path=issue_db)
        assert {r["source"] for r in rows} == {"model-generated"}
        assert all(e.get("source") == "model-generated" for e in issues)

    def test_every_description_admits_its_origin(self, issues):
        for e in issues:
            assert "general knowledge" in e["description"].lower(), e["title"]

    def test_prose_entries_cite_no_codes(self, issues):
        for e in issues:
            assert e["dtc_codes"] == [], e["title"]

    def test_symptoms_are_short_phrases(self, issues):
        for e in issues:
            for s in e["symptoms"]:
                assert len(s) <= 55 and not s.endswith("."), f"{e['title']}: {s!r}"

    @pytest.mark.parametrize("needle", [
        "tuneecu will not connect to a 790",
        "fi light flashing on a ktm in neutral",
        "scanner says idle air control on a ktm",
        "immobiliser antenna failure on the dash",
        "idles badly after a map load",
        "engine light after an akrapovic",
        "tool will not connect to this ktm",
    ])
    def test_a_mechanic_query_finds_the_entry(self, issue_db, needle):
        assert find_issues_by_symptom(needle, issue_db), needle
