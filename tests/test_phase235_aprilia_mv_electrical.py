"""Phase 235 — Aprilia + MV Agusta electrical, fault codes and dealer tools.

This phase owns three surfaces at once, like 225 and 230: knowledge
entries, make-specific DTC rows for two makes that had none, and the
adapter-catalogue gap that Phases 231-234 each guarded at zero.
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "src" / "motodiag" / "knowledge" / "seed"
K = SEED / "knowledge"
FILE = K / "known_issues_aprilia_mv_electrical.json"
APRILIA_DTC = SEED / "dtc_codes" / "aprilia.json"
MV_DTC = SEED / "dtc_codes" / "mv_agusta.json"
HW = ROOT / "src" / "motodiag" / "hardware" / "compat_data"
COMPAT = HW / "compat_matrix.json"
ADAPTERS = HW / "adapters.json"

#: Verified directly against Aprilia's Service Station Manual (B043120,
#: Tuono V4 R) rather than taken from research. Two refuters disagreed —
#: one said 18, one said 19 — so the manual was flattened, de-hyphenated
#: and counted here. The sentence is line-wrapped in the PDF as
#: "in- strument", which is exactly how a naive grep undercounts it.
NEVER_DISPLAYED = {
    "P0110", "P0115", "P0116", "P0130", "P0135", "P0160", "P0163",
    "P0164", "P0169", "P0180", "P0183", "P0184", "P0446", "P0560",
    "P0601", "P0604", "P0605", "P0608", "P0611",
}

NEW_MAKES = {"aprilia", "mv-agusta"}


@pytest.fixture(scope="module")
def raw():
    return json.loads(FILE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ap_dtc():
    return json.loads(APRILIA_DTC.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def mv_dtc():
    return json.loads(MV_DTC.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def matrix():
    return json.loads(COMPAT.read_text(encoding="utf-8"))


def _claims(entry):
    """Assertion-bearing fields only. Symptoms are the rider's own
    words reported back, not claims the file makes — the distinction
    that produced false positives at 218, 230 and 233."""
    return " ".join(
        [entry["title"], entry["description"], entry["fix_procedure"]]
        + entry["causes"]
    )


class TestFileShape:
    def test_eight_entries(self, raw):
        assert len(raw) == 8

    def test_required_keys(self, raw):
        need = {
            "title", "description", "make", "model", "year_start",
            "year_end", "severity", "symptoms", "causes",
            "fix_procedure", "parts_needed", "estimated_hours",
            "dtc_codes", "source",
        }
        for e in raw:
            assert need <= set(e), e["title"]

    def test_symptoms_are_short_phrases(self, raw):
        for e in raw:
            for s in e["symptoms"]:
                assert len(s) <= 55 and not s.endswith("."), f"{e['title']}: {s!r}"

    def test_no_title_collides_corpus_wide(self):
        titles = []
        for f in K.glob("known_issues_*.json"):
            titles += [e["title"] for e in json.loads(f.read_text(encoding="utf-8"))]
        assert len(titles) == len(set(titles))

    def test_severity_and_source_vocabulary(self, raw):
        assert {e["severity"] for e in raw} <= {"low", "medium", "high", "critical"}
        assert {e["source"] for e in raw} <= {"service-manual", "model-generated"}

    def test_no_entry_claims_a_forum_tip(self, raw):
        """Gate 2 requires forum-derived entries to carry a forum tip and
        forbids everyone else from claiming one. Nothing here is
        forum-derived, so nothing here may claim it."""
        for e in raw:
            assert "Forum tip" not in e["fix_procedure"], e["title"]


class TestProvenanceIsHonest:
    def test_service_manual_entries_rest_on_a_primary_document(self, raw):
        """`service-manual` here means a primary official document —
        Aprilia's own manual, or the EU regulation quoted verbatim. The
        provenance vocabulary has no `regulation` value; that gap is
        recorded in the phase plan rather than papered over by
        mislabelling the entry `unverified`, which would additionally
        drag it into Gate 2's forum-tip rule."""
        for e in raw:
            if e["source"] != "service-manual":
                continue
            assert re.search(r"Service Station Manual|Regulation \(EU\)",
                             e["description"]), e["title"]

    def test_vendor_sourced_entries_are_not_dressed_as_manuals(self, raw):
        for e in raw:
            if e["source"] != "model-generated":
                continue
            assert "Service Station Manual" not in e["description"], e["title"]

    def test_every_entry_says_what_it_is_drawn_from(self, raw):
        for e in raw:
            assert re.search(r"[Dd]rawn from", e["description"]), e["title"]


class TestTheNeverDisplayedSet:
    def test_the_entry_lists_all_nineteen(self, raw):
        entry = next(e for e in raw if "Nineteen" in e["title"])
        found = set(re.findall(r"\bP0\d{3}\b", entry["fix_procedure"]))
        assert found == NEVER_DISPLAYED, found ^ NEVER_DISPLAYED

    def test_the_count_word_matches_the_set(self, raw):
        entry = next(e for e in raw if "Nineteen" in e["title"])
        assert len(NEVER_DISPLAYED) == 19
        assert "nineteen" in _claims(entry).lower()

    def test_p0218_is_not_in_the_set(self, raw):
        """The research put P0218 on this list and it is not on it —
        the manual gives P0217 and P0218 identical text and neither
        carries the never-displayed sentence. Pinned because a plausible
        wrong member is how the claim failed the first time."""
        assert "P0218" not in NEVER_DISPLAYED
        entry = next(e for e in raw if "Nineteen" in e["title"])
        assert "P0218" not in entry["fix_procedure"]

    def test_it_extends_phase_232_rather_than_restating_it(self, raw):
        """232 already ships the claim that the ride-by-wire torque
        monitor stores a code the dash never displayed. What is new here
        is the SCOPE — that the set is nineteen codes and includes
        ordinary sensor and emissions circuits, not just the safety
        layer. The entry has to say so, or it is a restatement."""
        entry = next(e for e in raw if "Nineteen" in e["title"])
        text = _claims(entry)
        assert re.search(r"ordinary|routine", text, re.I)
        for ordinary in ("P0130", "P0135", "P0446"):
            assert ordinary in text, ordinary

    def test_att_versus_mem_is_explained_not_assumed(self, raw):
        entry = next(e for e in raw if "Nineteen" in e["title"])
        text = _claims(entry)
        assert "ATT" in text and "MEM" in text
        assert re.search(r"currently present|present now", text, re.I)


class TestApriliaDtcRows:
    def test_seven_rows_all_aprilia(self, ap_dtc):
        assert len(ap_dtc) == 7
        assert {r["make"] for r in ap_dtc} == {"Aprilia"}

    def test_every_row_names_the_sae_divergence(self, ap_dtc):
        """The whole point of an Aprilia row is that the SAE meaning is
        wrong for this make. A row that does not say so has not earned
        its place, because the generic reading is what the mechanic
        already has."""
        for r in ap_dtc:
            body = " ".join(r["common_causes"])
            assert re.search(r"NOT the SAE meaning|SAE ", body), r["code"]

    def test_rows_quote_the_manual_rather_than_paraphrase(self, ap_dtc):
        quoted = [r for r in ap_dtc if "'" in " ".join(r["common_causes"])]
        assert len(quoted) >= 6, [r["code"] for r in quoted]

    def test_severity_and_category_vocabulary(self, ap_dtc):
        assert {r["severity"] for r in ap_dtc} <= {"low", "medium", "high", "critical"}
        assert {r["category"] for r in ap_dtc} <= {
            "cooling", "electrical", "engine", "exhaust", "fuel", "idle"}

    def test_the_never_displayed_rows_say_so(self, ap_dtc):
        for r in ap_dtc:
            if r["code"] not in NEVER_DISPLAYED:
                continue
            body = " ".join(r["common_causes"]) + r["fix_summary"]
            assert re.search(r"does not indicate|never .{0,20}display|no warning light",
                             body, re.I), r["code"]

    def test_p0217_direction_is_not_inverted(self, ap_dtc):
        """A refuter caught the research stating this backwards. The
        manual says the MEASURED pressure is BELOW the estimated one."""
        row = next(r for r in ap_dtc if r["code"] == "P0217")
        body = " ".join(r for r in row["common_causes"])
        assert re.search(r"below the estimated", body)
        assert not re.search(r"above the estimated", body)

    def test_p0608_is_marked_as_a_consequence_not_a_cause(self, ap_dtc):
        row = next(r for r in ap_dtc if r["code"] == "P0608")
        assert re.search(r"consequence rather than a root cause",
                         " ".join(row["common_causes"]))
        assert "Continue fault search" in row["fix_summary"]


class TestMvDtcRows:
    def test_six_rows_all_mv(self, mv_dtc):
        assert len(mv_dtc) == 6
        assert {r["make"] for r in mv_dtc} == {"MV Agusta"}

    def test_every_row_carries_its_provenance(self, mv_dtc):
        """No MV primary document could be opened. Every row says so in
        its own body, because a reader meets one row, not the file."""
        for r in mv_dtc:
            assert "PROVENANCE" in " ".join(r["common_causes"]), r["code"]
            assert re.search(r"third-party", " ".join(r["common_causes"]), re.I)

    def test_no_p1xxx_row_is_shipped(self, mv_dtc):
        """MV's manufacturer block is real and this project cannot
        decode it. Shipping a guessed meaning would reproduce exactly
        the Aprilia failure the phase documents — a confident wrong
        answer. The block is named in a knowledge entry instead."""
        for r in mv_dtc:
            assert not re.match(r"P1\d{3}$", r["code"]), r["code"]

    def test_the_cylinder_count_boundary_is_asserted(self, mv_dtc):
        row = next(r for r in mv_dtc if r["code"] == "P0328")
        text = " ".join(row["common_causes"]) + row["fix_summary"]
        assert re.search(r"cannot legitimately occur|only on the four", text, re.I)

    def test_the_known_caption_error_is_flagged(self, mv_dtc):
        row = next(r for r in mv_dtc if r["code"] == "P0208")
        assert "CAPTION IS WRONG" in " ".join(row["common_causes"]).upper()


class TestTheOppositeTrapsFinding:
    def test_the_key_entry_names_both_directions(self, raw):
        entry = raw[0]
        text = _claims(entry)
        assert "P1" in text
        assert re.search(r"no manufacturer P1xxx block", text)
        assert re.search(r"silence is safer|failure is loud", text, re.I)

    def test_it_names_concrete_false_friends(self, raw):
        entry = raw[0]
        for code in ("P0510", "P0462", "P0217"):
            assert code in _claims(entry), code

    def test_the_false_friends_are_backed_by_real_rows(self, raw, ap_dtc):
        """Every code the headline entry cites as a false friend must
        actually exist in the Aprilia table, or the entry is describing
        a fix the product does not ship."""
        shipped = {r["code"] for r in ap_dtc}
        for code in re.findall(r"\bP0\d{3}\b", _claims(raw[0])):
            assert code in shipped, code


class TestCrossMakeEntriesResolveUnderBothMakes:
    def test_combined_make_values_are_substring_addressable(self, raw):
        """`issues_repo` filters with `make LIKE '%value%'`, so a
        combined make resolves under either name. Asserted rather than
        assumed, because the whole point of a shared entry is that a
        shop looking up one make finds it."""
        combined = [e for e in raw if e["make"] == "Aprilia and MV Agusta"]
        assert combined, "expected genuinely cross-make entries"
        for e in combined:
            assert "Aprilia" in e["make"] and "MV Agusta" in e["make"]

    def test_every_make_value_is_one_of_the_three_forms(self, raw):
        assert {e["make"] for e in raw} == {
            "Aprilia", "MV Agusta", "Aprilia and MV Agusta"}


class TestTheEuro4Correction:
    def test_the_entitlement_entry_exists_and_quotes_the_regulation(self, raw):
        entry = next(e for e in raw if "locked door" in e["title"])
        text = entry["description"]
        assert "2018/295" in text or "44/2014" in text
        assert "free of charge" in text
        assert "alternative connection interface" in text

    def test_it_scopes_the_entitlement_honestly(self, raw):
        """The access is real and narrow. An entry that promised full
        diagnosis from a generic tool would be worse than none."""
        entry = next(e for e in raw if "locked door" in e["title"])
        fix = entry["fix_procedure"]
        assert re.search(r"narrow", fix, re.I)
        for excluded in ("ABS", "immobiliser", "coding"):
            assert excluded in fix, excluded

    def test_it_distinguishes_type_approval_from_bench_verification(self, raw):
        entry = next(e for e in raw if "locked door" in e["title"])
        assert re.search(r"type approval requires, not a bench-verified",
                         entry["fix_procedure"])

    def test_euro4_rows_are_read_only_not_incompatible(self, matrix):
        """The correction that reshaped this phase. The research swept
        the whole Euro 4 generation into `incompatible`; L3e vehicles
        became OBD stage I from 2016, so those years are `read-only`."""
        for make in NEW_MAKES:
            euro4 = [
                r for r in matrix
                if r["make"] == make
                and r["adapter_slug"].startswith("elm327")
                and r["year_min"] == 2016
            ]
            assert len(euro4) == 1, make
            assert euro4[0]["status"] == "read-only", make

    def test_pre_euro4_rows_remain_incompatible(self, matrix):
        for make in NEW_MAKES:
            pre = [
                r for r in matrix
                if r["make"] == make
                and r["adapter_slug"].startswith("elm327")
                and r["year_max"] == 2015
            ]
            assert len(pre) == 1 and pre[0]["status"] == "incompatible", make

    def test_no_generic_row_claims_full_or_partial(self, matrix):
        for r in matrix:
            if r["make"] in NEW_MAKES and r["adapter_slug"].startswith("elm327"):
                assert r["status"] in {"read-only", "incompatible"}, r


class TestAdapterCatalogue:
    def test_both_makes_now_have_rows(self, matrix):
        assert NEW_MAKES <= {r["make"] for r in matrix}

    def test_the_make_slug_is_hyphenated(self, matrix):
        assert not {"mv", "mvagusta", "mv agusta"} & {r["make"] for r in matrix}

    def test_every_row_points_at_an_adapter_that_exists(self, matrix):
        slugs = {a["slug"] for a in json.loads(ADAPTERS.read_text(encoding="utf-8"))}
        for r in matrix:
            assert r["adapter_slug"] in slugs, r["adapter_slug"]

    def test_adapter_slugs_are_unique(self):
        slugs = [a["slug"] for a in json.loads(ADAPTERS.read_text(encoding="utf-8"))]
        assert len(slugs) == len(set(slugs))

    def test_row_status_vocabulary(self, matrix):
        assert {r["status"] for r in matrix} <= {
            "full", "partial", "read-only", "incompatible"}

    def test_tuneecu_is_deliberately_incompatible_with_mv(self, matrix):
        """A deliberate negative row, as Phase 230 shipped for the
        carburetted Bonnevilles. TuneECU is the usual recommendation for
        Italian machines and it does not cover MV at any age."""
        row = next(r for r in matrix
                   if r["adapter_slug"] == "tuneecu-aprilia"
                   and r["make"] == "mv-agusta")
        assert row["status"] == "incompatible"
        assert row["year_min"] <= 1997 and row["year_max"] >= 2026

    def test_mv_official_tool_is_marked_full(self, matrix):
        row = next(r for r in matrix
                   if r["adapter_slug"] == "texa-idc5-bike"
                   and r["make"] == "mv-agusta")
        assert row["status"] == "full"
        assert "OFFICIAL" in row["notes"]

    def test_unsourced_year_ranges_are_labelled(self, matrix):
        """Only a few year ranges in this phase are genuinely
        source-stated. Every other new row must say its range is an
        estimate, so a later reader does not mistake it for coverage.

        `incompatible` rows are exempt because they claim the opposite
        of coverage: "this tool does not cover this make at any age" is
        not a range a reader can over-trust. The rule is about coverage
        claims, and scoping it that way is why the exemption is here
        rather than the assertion being loosened."""
        for r in matrix:
            if r["make"] not in NEW_MAKES or r["status"] == "incompatible":
                continue
            notes = r["notes"]
            assert ("SOURCE-STATED" in notes
                    or "era estimate" in notes
                    or "OBD stage" in notes
                    or "ISO 19689" in notes), r["adapter_slug"] + " " + r["make"]

    def test_the_three_source_stated_ranges_are_marked(self, matrix):
        stated = [r for r in matrix
                  if r["make"] in NEW_MAKES and "SOURCE-STATED" in r["notes"]]
        assert len(stated) == 4, [r["model_pattern"] for r in stated]

    def test_coverage_uncertainty_is_recorded_not_hidden(self, matrix):
        """No source consulted confirms MV three- vs four-cylinder tool
        parity. The catalogue has to say so rather than imply parity by
        shipping a clean make-level row."""
        mv_rows = [r for r in matrix if r["make"] == "mv-agusta"]
        assert any("NOT confirmed" in r["notes"] or "not confirmed" in r["notes"]
                   for r in mv_rows)


class TestDeferralBoundariesStillHold:
    def test_phase_231_file_still_has_no_tool_or_code_content(self):
        """231 deferred these strings here. This phase must not have
        leaked back into that file."""
        raw231 = json.loads(
            (K / "known_issues_aprilia_rsv4.json").read_text(encoding="utf-8"))
        for e in raw231:
            body = " ".join([e["title"], e["description"], e["fix_procedure"]]
                            + e["causes"])
            assert not re.findall(r"\bP0\d{3}\b|\bPADS\b", body), e["title"]

    def test_this_file_owns_the_tooling_vocabulary(self, raw):
        text = " ".join(_claims(e) for e in raw)
        assert "PADS" in text or "Piaggio Advanced Diagnostic System" in text

    def test_no_model_specific_content_belonging_to_231_to_234(self, raw):
        """Valve intervals, capacities and campaigns belong to the model
        phases. This one is electrical, codes and tools."""
        for e in raw:
            body = _claims(e)
            assert not re.search(r"valve clearance|shim|recall campaign", body, re.I), \
                e["title"]
