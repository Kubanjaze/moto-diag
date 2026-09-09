"""Phase 236 — European diagnostic tooling, cross-platform comparison.

The row's ground was already covered per make (215, 220, 225, 230, 235),
so this file may only hold what is visible when the makes are compared
side by side. Every entry must name a specific tool AND a specific
make-level behaviour of it; general tooling advice is Phase 235's or
nobody's.
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
K = ROOT / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"
FILE = K / "known_issues_european_tooling.json"
TOOLS = ("TuneECU", "TEXA", "GS-911", "DiagCode", "OBDSTAR")
MAKES = ("BMW", "Ducati", "KTM", "Triumph", "Aprilia", "MV Agusta", "Moto Guzzi")


@pytest.fixture(scope="module")
def raw():
    return json.loads(FILE.read_text(encoding="utf-8"))


def _claims(e):
    return " ".join([e["title"], e["description"], e["fix_procedure"]] + e["causes"])


class TestFileShape:
    def test_thirteen_entries(self, raw):
        assert len(raw) == 13

    def test_required_keys(self, raw):
        need = {"title", "description", "make", "model", "year_start", "year_end",
                "severity", "symptoms", "causes", "fix_procedure", "parts_needed",
                "estimated_hours", "dtc_codes", "source"}
        for e in raw:
            assert need <= set(e), e["title"]

    def test_symptoms_are_short_phrases(self, raw):
        for e in raw:
            for s in e["symptoms"]:
                assert len(s) <= 55 and not s.endswith("."), f"{e['title']}: {s!r}"

    def test_every_entry_says_what_it_is_drawn_from(self, raw):
        for e in raw:
            assert re.search(r"[Dd]rawn\b[\w' ]{0,16}\bfrom", e["description"]), e["title"]

    def test_no_title_collides_corpus_wide(self):
        titles = []
        for f in K.glob("known_issues_*.json"):
            titles += [e["title"] for e in json.loads(f.read_text(encoding="utf-8"))]
        assert len(titles) == len(set(titles))

    def test_no_forum_tips_claimed(self, raw):
        # Rule 3 as a biconditional (Phase 240B). These two files hold no
        # `forum` entry, so the negative half alone was correct by accident;
        # keyed off `source` it stays correct if one is ever added.
        for e in raw:
            assert ("Forum tip" in e["fix_procedure"]) == (e["source"] == "forum"), e["title"]
        assert {e["source"] for e in raw} <= {"service-manual", "model-generated"}


class TestTheGenericnessBar:
    """The refuters flagged two of fifteen proposed entries as writable
    without naming any manufacturer's hardware — both were dropped
    because Phase 235 already holds that ground. The bar is enforced on
    what shipped."""

    def test_every_entry_names_a_tool(self, raw):
        for e in raw:
            assert any(t in _claims(e) for t in TOOLS), e["title"]

    def test_every_entry_names_a_make_or_make_group(self, raw):
        for e in raw:
            text = _claims(e) + " " + e["make"]
            assert any(m in text for m in MAKES + ("Piaggio",)), e["title"]

    def test_no_entry_is_pure_regulatory_theory(self, raw):
        """ISO 19689 clause text and OBD stage I/II were the two flagged
        entries. Both already live in Phase 235's file and catalogue."""
        for e in raw:
            assert "19689" not in _claims(e), e["title"]
            assert "OBD stage" not in _claims(e), e["title"]


class TestTheCorrectionsRefutationForced:
    def test_ktm_loses_both_read_and_write(self, raw):
        """The research's headline said Triumph and KTM degrade identically
        — write survives, read does not. The table says KTM rows are
        diagnostics-only. A refuter read the columns; the finding had
        contradicted itself between its scope and claim fields."""
        e = next(x for x in raw if "degrades differently" in x["title"])
        text = _claims(e)
        assert re.search(r"no read \*and no write\*|neither read nor write", text)
        assert re.search(r"cannot write at all", text)

    def test_triumph_keeps_write_and_loses_read(self, raw):
        e = next(x for x in raw if "degrades differently" in x["title"])
        text = _claims(e)
        assert re.search(r"diagnostics and write but \*\*no read\*\*|write but not read", text)

    def test_the_asymmetry_is_the_point_not_a_footnote(self, raw):
        e = next(x for x in raw if "degrades differently" in x["title"])
        assert re.search(r"assuming it degrades the same way", e["title"])
        assert re.search(r"different conversations|generalises it will be wrong",
                         _claims(e))

    def test_newest_triumphs_are_not_claimed_outside_tuneecu(self, raw):
        """The research said the red-plug Triumphs were absent from the
        table. The table lists Scrambler 1200, Tiger 850/900, Street
        Triple 765 RS from a VIN, Trident 660 and Tiger Sport 660 — and
        the finding's own earlier section had already said so."""
        for e in raw:
            text = _claims(e)
            assert not re.search(r"(Tiger 900|Scrambler 1200|Trident 660).{0,80}not (in|on) the table",
                                 text, re.I), e["title"]

    def test_triumph_transition_year_is_deliberately_absent(self, raw):
        """A refuter found the stated timeline off by three model years.
        Rather than pick a year, the entry says why none is printed."""
        e = next(x for x in raw if "connector outlier" in x["title"])
        assert re.search(r"deliberately not printed", _claims(e))
        assert not re.findall(r"\b20(1\d|2[0-6])\b", e["description"]), \
            "no transition year should appear in the Triumph connector entry"

    def test_no_reseller_part_numbers(self, raw):
        """A refuter found a Ducati tool part number sourced from a
        reseller listing that names a different version. None ship."""
        for e in raw:
            assert not re.findall(r"\b\d{5}\.\d{4}\b", _claims(e)), e["title"]


class TestTheComparisonOnlyFindings:
    def test_bmw_is_one_enduro_single(self, raw):
        e = next(x for x in raw if "449cc" in x["title"])
        assert "G450 X" in _claims(e)
        assert re.search(r"No boxer, no K, no S, no F and no R", _claims(e))

    def test_ducati_is_scoped_by_ecu_not_year(self, raw):
        e = next(x for x in raw if "ECU part number" in x["title"])
        assert re.search(r"the only make", _claims(e))
        assert "EVO" in _claims(e)

    def test_texa_is_named_as_oem_for_exactly_two_makes(self, raw):
        e = next(x for x in raw if "no dealer-tool lockout" in x["title"])
        text = _claims(e)
        assert "Ducati and MV Agusta" in text
        for other in ("BMW", "KTM", "Triumph", "Aprilia", "Moto Guzzi"):
            assert other in text, other
        assert re.search(r"\*\*not\*\* on that list|are not on that list", text)

    def test_the_basic_tier_trap_names_both_tiers(self, raw):
        e = next(x for x in raw if "IDC5 BASIC" in x["title"])
        assert "IDC5 PLUS" in _claims(e)

    def test_the_gs911_cap_is_a_number_not_an_adjective(self, raw):
        e = next(x for x in raw if "GS-911" in x["title"])
        assert re.search(r"ten vehicle|10-vehicle", _claims(e))

    def test_the_negative_statement_entry_explains_why_it_matters(self, raw):
        e = next(x for x in raw if "not compatible" in x["title"])
        assert re.search(r"converts every absence", _claims(e))


class TestBoundaryWithPhase235:
    """235 owns Aprilia/MV tooling in depth. This file may compare, not
    restate — so the 235 specifics stay there."""

    def test_no_pads_detail_restated(self, raw):
        text = " ".join(_claims(e) for e in raw)
        assert "Piaggio Advanced Diagnostic System" not in text

    def test_no_aprilia_connector_pin_counts_restated(self, raw):
        for e in raw:
            assert not re.search(r"\b6-pin Sagem|\b3-pin plug on RSV4", _claims(e)), e["title"]

    def test_the_never_displayed_codes_are_not_here(self, raw):
        for e in raw:
            assert not re.findall(r"\bP0\d{3}\b", _claims(e)), e["title"]
            assert e["dtc_codes"] == []


class TestSearchability:
    @pytest.mark.parametrize("needle", [
        "does tuneecu work on bmw",
        "tuneecu ducati which models",
        "can i read the map on a ktm 1290 with tuneecu",
        "texa idc5 ducati official tool",
        "gs-911 enthusiast vs professional",
        "obdstar iscan covers which bikes",
    ])
    def test_a_plausible_query_finds_something(self, raw, needle):
        words = [w[:5] for w in re.findall(r"[a-z0-9-]+", needle) if len(w) > 3]
        best = max(sum(1 for w in words if w in _claims(e).lower()) for e in raw)
        assert best >= 2, f"{needle!r} matched only {best} terms"


class TestTheProvenanceRule:
    """Phase 240B decided the rule the track had been applying unevenly, and
    enforces it in the file that broke it.

    THE RULE — an entry's `source` names the weakest link in the evidence
    chain its load-bearing claim rests on:

      regulation      the entry quotes legal text and the claim IS the
                      requirement
      service-manual  a primary official document STATES the claim. A
                      documented absence counts ("the manual has no such
                      row" is what the document yielded)
      model-generated vendor or third-party published material, or an
                      inference drawn across sources
      forum           owner reporting or marque-community consensus
      unverified      legacy rows only — origin never recorded. Never
                      assigned to Track K content.

    This file carried the same evidence class under two labels: TuneECU's own
    compatibility table was `service-manual` in four entries and
    `model-generated` in two. The direction was not a coin flip — Phase 235
    had already recorded and tested it one phase earlier ("vendor-documentation
    entries are model-generated"), so the eight vendor entries were DEMOTED
    rather than the two promoted. Promoting would have put this file in direct
    conflict with a passing Phase 235 test and would have silenced the CLI's
    provenance caution across a file where nothing rests on a manufacturer
    document.

    Asserted as a rule rather than a count so the next cross-make phase
    inherits it instead of re-deciding it."""

    VENDORS = ("TuneECU", "TEXA", "HEX", "OBDSTAR", "DiagCode", "IDC5", "GS-911")

    def test_no_vendor_sourced_entry_claims_a_manufacturer_document(self, raw):
        for e in raw:
            if e["source"] != "service-manual":
                continue
            named = [v for v in self.VENDORS if v.lower() in e["description"].lower()]
            assert not named, (
                f"{e['title']}: rests on {named[0]}'s own published material but is "
                "labelled service-manual. Vendor documentation is model-generated — "
                "see Phase 235's TestProvenanceIsHonest."
            )

    def test_every_entry_still_says_what_it_is_drawn_from(self, raw):
        """The demotion must not cost the file its provenance prose."""
        for e in raw:
            assert re.search(r"[Dd]rawn from", e["description"]), e["title"]
