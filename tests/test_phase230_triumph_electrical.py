"""Phase 230 — Triumph electrical + tooling. Closes the Triumph block.

**The first closing phase to arrive with a written brief from its
predecessors.** Row 230 carried three inheritances, each recorded on it
by an earlier phase, and each was verified here rather than trusted:

- **The adapter gap (226).** Five Triumph rows, none full-access, and no
  row at all for the air-cooled Bonneville that eleven entries describe.
  Filled — and the honest answer turned out to be *two* answers: the
  carburetted 2001–2007 machines have **no engine control module and no
  connector**, so they get an explicit `incompatible` row rather than
  coverage. An absent row implies missing tooling; an incompatible row
  says no tool can exist.
- **The naming question (225 via 226).** For KTM, TuneECU does
  diagnostics and TuneBoy is only an editor. **That does not carry
  across.** On Triumph TuneBoy also ships a diagnostic module — though
  it publishes no function matrix for it, so its per-model diagnostic
  coverage is recorded as unestablished rather than assumed.
- **P0315 (227).** Verified verbatim in Triumph's own bulletins by a
  refuter who re-downloaded them: Euro 5 markets, normally adapted at
  the factory, occasionally needed at PDI, **cannot be cleared with the
  normal erase function**, and needs a full power-down after adaption.
  The inherited claim held completely.

**The cylinder numbering was settled with an exception.** Phase 224
declined to assert KTM's numbering; 225 settled it from KTM's manual.
Here Triumph's own specification tables give "Cylinder Numbering: Left
to Right" for the transverse triples — but the **Rocket 3's longitudinal
triple is "Front to back", "1 at front"**, so a generic misfire row is
actively misleading on that model. All three misfire rows carry the
exception.

**Eleventh phase in which a selector confused mention with use**: a check
for an "official" claim about DealerTool matched the *symptom* "is
dealertool the official triumph tool" — a mechanic's question, not a
claim. Claim checks here run on assertion-bearing fields only.
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
TRI_DTC = D / "triumph.json"
GEN_DTC = D / "generic.json"
ELEC = K / "known_issues_triumph_electrical.json"
TRIUMPH_FILES = sorted(K.glob("known_issues_triumph_*.json"))
COMPAT = SEED_DATA_DIR.parent.parent / "hardware" / "compat_data"
ADAPTERS = COMPAT / "adapters.json"
MATRIX = COMPAT / "compat_matrix.json"
NEW_SLUGS = {"tuneecu-triumph-android", "dealertool-triumph"}

STD_CODE = re.compile(r"^[PUBC][0-3][0-9A-F]{3}$")


def _claims(e: dict) -> str:
    """Assertion-bearing fields only. Symptoms are the mechanic's own
    words — a question like "is dealertool the official triumph tool" is
    a report, not a claim the corpus makes (the Phase 218 lesson,
    rediscovered here as the eleventh mention-versus-use slip)."""
    return " ".join([e["title"], e["description"], e["fix_procedure"]] + e["causes"])


def _first(rows):
    return rows[0] if isinstance(rows, list) else list(rows.values())[0]


@pytest.fixture
def dtc_db(tmp_path):
    path = str(tmp_path / "d.db")
    init_db(path)
    load_dtc_file(GEN_DTC, path)
    load_dtc_file(TRI_DTC, path)
    return path


@pytest.fixture
def codes():
    return json.loads(TRI_DTC.read_text(encoding="utf-8"))


@pytest.fixture
def issues():
    return json.loads(ELEC.read_text(encoding="utf-8"))


class TestNoFabricatedCodes:
    def test_every_code_is_standard_format(self, codes):
        for c in codes:
            assert STD_CODE.match(c["code"]), c["code"]

    def test_no_row_is_a_proprietary_p1_code(self, codes):
        """Triumph genuinely uses a P1xxx block — a workshop manual lists
        28 of them. They are Triumph's numbers to publish, not this
        file's to transcribe."""
        for c in codes:
            assert not c["code"].startswith("P1"), c["code"]

    def test_no_proprietary_chassis_code_is_transcribed(self, codes, issues):
        """Likewise the C1xxx chassis and security series. The knowledge
        entry describes the family; it does not list its numbers."""
        blob = json.dumps(codes) + json.dumps(issues)
        assert not re.search(r"\bC1\d{3}\b", blob)

    def test_no_duplicates_and_all_marked_triumph(self, codes):
        assert len({c["code"] for c in codes}) == len(codes)
        assert {c["make"] for c in codes} == {"Triumph"}

    def test_vocabularies_are_valid(self, codes):
        from motodiag.core.models import Severity, SymptomCategory

        cats = {e.value for e in SymptomCategory}
        sevs = {e.value for e in Severity}
        for c in codes:
            assert c["category"] in cats and c["severity"] in sevs, c["code"]


class TestEveryShadowingRowEarnsIt:
    def test_shadowing_rows_exist_and_differ(self, codes):
        generic = {c["code"]: c for c in json.loads(GEN_DTC.read_text(encoding="utf-8"))}
        shadowing = [c for c in codes if c["code"] in generic]
        assert len(shadowing) >= 1
        for c in shadowing:
            g = generic[c["code"]]
            assert c["common_causes"] != g.get("common_causes"), c["code"]
            assert c["fix_summary"] != g.get("fix_summary"), c["code"]

    def test_a_triumph_gets_the_triumph_row(self, dtc_db):
        assert _first(get_dtcs(["P0301"], make="Triumph", db_path=dtc_db))["make"] == "Triumph"

    def test_another_make_still_gets_generic(self, dtc_db):
        assert _first(get_dtcs(["P0301"], make="Honda", db_path=dtc_db))["make"] is None


class TestTheCylinderNumberingAndItsException:
    def test_the_transverse_mapping_is_stated(self, codes):
        by = {c["code"]: c for c in codes}
        assert re.search(r"cylinder 1[^.]{0,90}left", json.dumps(by["P0301"]), re.I)
        assert re.search(r"cylinder 2[^.]{0,90}centre", json.dumps(by["P0302"]), re.I)
        assert re.search(r"cylinder 3[^.]{0,90}right", json.dumps(by["P0303"]), re.I)

    def test_every_misfire_row_carries_the_rocket_3_exception(self, codes):
        """The refuter's finding, and the reason a generic row would
        mislead: the Rocket 3's longitudinal triple is numbered front to
        back, so cylinder 1 there is the FRONT cylinder."""
        for code in ("P0301", "P0302", "P0303"):
            c = [x for x in codes if x["code"] == code][0]
            assert "Rocket 3" in json.dumps(c), code
        assert re.search(r"1 at front|front cylinder", json.dumps(codes), re.I)

    def test_the_mapping_never_contradicts_itself(self, codes):
        """Transverse: 1 left, 2 centre, 3 right. Every statement of it
        must agree (the Phase 220 guard)."""
        expected = {"1": "left", "2": "centre", "3": "right"}
        blob = json.dumps(codes)
        for num, side in re.findall(
            r"cylinder (\d)[^.]{0,60}?\b(left|centre|right)\b", blob, re.I
        ):
            assert side.lower() == expected[num], f"cylinder {num} called {side}"

    def test_no_observer_position_is_invented(self, codes):
        """Triumph's tables say 'left to right' without stating from
        where. The rows do not resolve what the source leaves open."""
        blob = json.dumps(codes)
        assert not re.search(r"as seated|viewed from the front|rider's left", blob, re.I)


class TestTheInheritedClaimsWereVerified:
    def test_p0315_is_written_as_the_bulletins_state_it(self, codes):
        """Phase 227 handed this over on one refuter's word. Verified
        here in Triumph's own bulletins before being written."""
        p = [c for c in codes if c["code"] == "P0315"]
        assert p, "the inherited P0315 finding was dropped"
        text = json.dumps(p[0])
        assert "cannot be erased" in text
        assert "Euro 5" in text
        assert re.search(r"pre-delivery|PDI", text)
        assert re.search(r"power down|powered down", text, re.I)

    def test_p0315_is_framed_as_an_unperformed_adaption_first(self, codes):
        """The diagnostically important part: on a Euro 5 machine this
        is usually not a fault, and treating it as a sensor failure
        costs a part that was never wrong."""
        p = [c for c in codes if c["code"] == "P0315"][0]
        assert re.search(r"not a fault|never performed|unperformed", json.dumps(p), re.I)

    def test_the_tuneboy_answer_is_not_carried_over_from_ktm(self, issues):
        """Phase 225 found TuneBoy is only an editor on KTM. On Triumph
        it also ships a diagnostic module — so the entry must not repeat
        the KTM conclusion, and must record that its per-model coverage
        is unestablished."""
        tools = [e for e in issues if "TuneECU, TuneBoy and DealerTool" in e["title"]]
        assert tools, "the tool-landscape entry is missing"
        text = _claims(tools[0])
        assert "not *only* that" in text or "not only" in text.lower()
        assert re.search(r"unestablished|not established|does not publish", text)

    def test_dealertool_is_marked_third_party(self, issues):
        tools = [e for e in issues if "DealerTool" in e["title"]][0]
        text = _claims(tools)
        assert re.search(r"third-party", text)
        assert re.search(r"not Triumph's own|not Triumph's", text)

    def test_the_official_word_is_not_asserted_about_dealertool(self, issues):
        """A refuter found the vendor says 'the ORIGINAL diagnostic
        software', with 'official' appearing only in meta keywords. The
        entry does not put that word in the vendor's mouth — checked on
        claims only, since a symptom phrasing the customer's question is
        a report."""
        for e in issues:
            assert not re.search(r"DealerTool[^.]{0,60}official", _claims(e), re.I), e["title"]


class TestTheCodeFormatEntry:
    def test_the_three_code_families_are_described(self, issues):
        fmt = [e for e in issues if "flashing" in e["title"]][0]
        text = _claims(fmt)
        assert "P0" in text and "P1" in text and "C1" in text

    def test_the_flashing_versus_steady_distinction_is_stated(self, issues):
        """The uncommon and genuinely useful part: lamp behaviour is
        specified per code, and flashing means an identity or security
        mismatch."""
        fmt = [e for e in issues if "flashing" in e["title"]][0]
        text = _claims(fmt)
        assert re.search(r"flashing[^.]{0,80}(identity|security|mismatch)", text, re.I)
        assert re.search(r"steady[^.]{0,80}(ordinary|sensor|circuit)", text, re.I)

    def test_the_dash_sequence_is_not_presented_as_procedure(self, issues):
        """Every source for it was blocked. It is recorded as something
        a customer may have done, not as something to recommend."""
        dash = [e for e in issues if "dash diagnostic mode" in e["title"]]
        assert dash
        text = _claims(dash[0])
        assert re.search(r"not (Triumph )?(factory )?procedure|not documented by Triumph", text)

    def test_no_unsourced_standard_number_is_cited(self, issues):
        """A refuter found 'ISO 19689' appears in none of the sources."""
        assert "19689" not in json.dumps(issues)


class TestTheAdapterGapIsFilledHonestly:
    @pytest.fixture(scope="class")
    def adapters(self):
        return json.loads(ADAPTERS.read_text(encoding="utf-8"))

    @pytest.fixture(scope="class")
    def matrix(self):
        return json.loads(MATRIX.read_text(encoding="utf-8"))

    def test_both_adapters_exist(self, adapters):
        assert NEW_SLUGS <= {a["slug"] for a in adapters}

    def test_they_match_the_catalog_schema(self, adapters):
        peer = next(a for a in adapters if a["slug"] == "obdlink-mx-plus")
        for slug in NEW_SLUGS:
            a = next(x for x in adapters if x["slug"] == slug)
            assert set(a) == set(peer), slug

    def test_mode22_is_false_on_both(self, adapters):
        """Triumph's socket is OBD-II shaped and speaks a Triumph K-line
        protocol, not the generic emissions layer."""
        for slug in NEW_SLUGS:
            a = next(x for x in adapters if x["slug"] == slug)
            assert a["supports_mode22"] is False, slug

    def test_prices_are_labelled_indicative(self, adapters):
        """Neither vendor publishes a USD price. Both records say the
        figure is converted and indicative rather than a vendor price."""
        for slug in NEW_SLUGS:
            a = next(x for x in adapters if x["slug"] == slug)
            assert re.search(r"indicative", a["known_issues"]), slug

    def test_compat_rows_are_triumph_only_with_provenance(self, matrix):
        for slug in NEW_SLUGS:
            rows = [r for r in matrix if r["adapter_slug"] == slug]
            assert rows, slug
            assert {r["make"] for r in rows} == {"triumph"}, slug
            for r in rows:
                assert r["verified_by"].strip(), (slug, r["model_pattern"])

    def test_the_air_cooled_bonneville_gap_is_closed(self, matrix):
        """What Phase 226 left. Eleven entries in this corpus describe
        those machines and they had no adapter row at all."""
        rows = [r for r in matrix
                if r["make"] == "triumph"
                and "bonneville" in r["model_pattern"]
                and r["year_min"] < 2016]
        assert rows, "the air-cooled Bonneville still has no coverage"
        assert any(r["status"] == "full" for r in rows)

    def test_the_carburetted_half_is_incompatible_not_absent(self, matrix):
        """The honest half of the answer, and the reason this is two
        rows rather than one: those machines have no engine control
        module, so no tool can exist. An absent row would imply we
        merely lack one."""
        carb = [r for r in matrix
                if r["make"] == "triumph"
                and "bonneville" in r["model_pattern"]
                and r["year_max"] <= 2007]
        assert carb, "the carburetted machines have no row at all"
        assert all(r["status"] == "incompatible" for r in carb)
        assert any(re.search(r"no engine control module|deliberate", r["notes"], re.I)
                   for r in carb)

    def test_the_original_five_rows_survived(self, matrix):
        """Phases 226-229 guarded these. 230 added; it did not rewrite."""
        original = {
            ("obdlink-mx-plus", "tiger%"), ("obdlink-mx-plus", "675"),
            ("obdlink-lx", "bonneville%"), ("elm327-generic-bt-clone", "675"),
            ("obdlink-sx", "tiger%"),
        }
        rows = {(r["adapter_slug"], r["model_pattern"])
                for r in matrix if r["make"] == "triumph"}
        assert original <= rows, original - rows


class TestTheWholeTriumphBlockCoheres:
    def test_the_whole_triumph_block_loads_together(self, tmp_path):
        path = str(tmp_path / "tri.db")
        init_db(path)
        expected = 0
        for f in TRIUMPH_FILES:
            load_known_issues_file(f, path)
            expected += len(json.loads(f.read_text(encoding="utf-8")))
        assert count_known_issues(db_path=path) == expected
        # Phase 240B: `expected` is the sum of file lengths, which equals the
        # make-filtered count only while every entry in these files carries
        # the make verbatim -- `make LIKE '%X%'` is a substring match. The
        # Aprilia block already breaks that (compound "Aprilia and MV Agusta"
        # makes), so count the filtered number rather than assuming it.
        entries = [e for f in TRIUMPH_FILES for e in json.loads(f.read_text(encoding="utf-8"))]
        assert len(search_known_issues(make="Triumph", db_path=path)) == sum(
            1 for e in entries if "triumph" in e["make"].lower()
        )
        assert len(json.loads(ELEC.read_text(encoding="utf-8"))) == 5

    def test_no_title_collides(self):
        titles = []
        for f in TRIUMPH_FILES:
            titles += [e["title"] for e in json.loads(f.read_text(encoding="utf-8"))]
        assert len(titles) == len(set(titles))

    def test_no_symptom_resolves_to_two_triumph_files(self, issues):
        mine = {s for e in issues for s in e["symptoms"]}
        for f in TRIUMPH_FILES:
            if f == ELEC:
                continue
            theirs = {s for e in json.loads(f.read_text(encoding="utf-8"))
                      for s in e["symptoms"]}
            assert not (mine & theirs), f"{f.name}: {mine & theirs}"

    def test_the_earlier_phases_kept_their_dtc_boundary(self):
        """226-229 all carry `dtc_codes: []` because this phase owned
        the code surface. That is still true."""
        for f in TRIUMPH_FILES:
            if f == ELEC:
                continue
            for e in json.loads(f.read_text(encoding="utf-8")):
                assert e["dtc_codes"] == [], f"{f.name}: {e['title']}"


class TestProvenanceAndSearchability:
    @pytest.fixture
    def issue_db(self, tmp_path):
        path = str(tmp_path / "e.db")
        init_db(path)
        load_known_issues_file(ELEC, path)
        return path

    def test_every_entry_is_service_manual_sourced(self, issue_db, issues):
        rows = search_known_issues(make="Triumph", db_path=issue_db)
        assert {r["source"] for r in rows} == {"service-manual"}
        assert {e["source"] for e in issues} == {"service-manual"}

    def test_every_entry_says_what_it_is_drawn_from(self, issues):
        for e in issues:
            assert re.search(r"[Dd]rawn from", e["description"]), e["title"]

    def test_prose_entries_cite_no_codes(self, issues):
        for e in issues:
            assert e["dtc_codes"] == [], e["title"]

    def test_symptoms_are_short_phrases(self, issues):
        for e in issues:
            for s in e["symptoms"]:
                assert len(s) <= 55 and not s.endswith("."), f"{e['title']}: {s!r}"

    @pytest.mark.parametrize("needle", [
        "warning lamp flashing on a triumph",
        "generic obd reader will not connect to a triumph",
        "cannot find a diagnostic socket on a bonneville",
        "is dealertool the official triumph tool",
        "hidden diagnostic menu on a triumph",
    ])
    def test_a_mechanic_query_finds_the_entry(self, issue_db, needle):
        assert find_issues_by_symptom(needle, issue_db), needle
