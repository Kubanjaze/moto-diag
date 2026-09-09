"""Phase 225B — KTM mid-size Adventure line (390 / 790 / 890 Adventure).

Closes the open item the KTM block carried from Phase 225 through ten
phases. The axis is deliberate: Phase 222 owns the Duke naked models and
Phase 224 owns the LC8c engine family, so engine-internal content here
would shadow both. What this phase owns is everything around the engine.
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
K = ROOT / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"
FILE = K / "known_issues_ktm_adventure.json"
KTM_FILES = sorted(K.glob("known_issues_ktm_*.json"))


@pytest.fixture(scope="module")
def raw():
    return json.loads(FILE.read_text(encoding="utf-8"))


def _claims(e):
    """Assertion-bearing fields only — symptoms are the rider's words
    reported back, not claims the file makes (218 / 230 / 233)."""
    return " ".join(
        [e["title"], e["description"], e["fix_procedure"]] + e["causes"])


class TestFileShape:
    def test_ten_entries(self, raw):
        assert len(raw) == 10

    def test_required_keys(self, raw):
        need = {"title", "description", "make", "model", "year_start",
                "year_end", "severity", "symptoms", "causes",
                "fix_procedure", "parts_needed", "estimated_hours",
                "dtc_codes", "source"}
        for e in raw:
            assert need <= set(e), e["title"]

    def test_every_entry_is_ktm(self, raw):
        assert {e["make"] for e in raw} == {"KTM"}

    def test_symptoms_are_short_phrases(self, raw):
        for e in raw:
            for s in e["symptoms"]:
                assert len(s) <= 55 and not s.endswith("."), f"{e['title']}: {s!r}"

    def test_every_entry_says_what_it_is_drawn_from(self, raw):
        for e in raw:
            assert re.search(r"[Dd]rawn\b[\w ]{0,12}\bfrom", e["description"]), e["title"]

    def test_no_title_collides_corpus_wide(self):
        titles = []
        for f in K.glob("known_issues_*.json"):
            titles += [e["title"] for e in json.loads(f.read_text(encoding="utf-8"))]
        assert len(titles) == len(set(titles))

    def test_forum_entries_carry_a_forum_tip(self, raw):
        """Gate 2's rule, asserted locally so it fails here rather than
        in the gate."""
        for e in raw:
            if e["source"] == "forum":
                assert "Forum tip" in e["fix_procedure"], e["title"]

    def test_non_forum_entries_do_not_claim_one(self, raw):
        for e in raw:
            if e["source"] != "forum":
                assert "Forum tip" not in e["fix_procedure"], e["title"]


class TestTheGapThisPhaseCloses:
    def test_the_mid_size_adventure_models_are_now_covered(self):
        """Before this phase these three strings appeared zero times in
        the whole corpus while `Super Adventure` appeared twenty-five
        times — all of it the 1290, which Phase 221 owns."""
        body = "\n".join(
            f.read_text(encoding="utf-8") for f in K.glob("known_issues_*.json"))
        for model in ("390 Adventure", "790 Adventure", "890 Adventure"):
            assert model in body, model

    def test_this_file_is_where_they_live(self, raw):
        text = json.dumps(raw)
        for model in ("390 Adventure", "790 Adventure", "890 Adventure"):
            assert model in text, model

    def test_the_naming_trap_is_an_entry_in_its_own_right(self, raw):
        """The gap survived ten phases because a corpus search for
        `Adventure` returns the 1290 confidently. That is worth saying
        out loud rather than only fixing."""
        entry = raw[0]
        text = _claims(entry)
        assert "Super Adventure" in text
        assert re.search(r"differ by (a |one )?single word|differ by one word", text)


class TestBoundariesWithTheRestOfTheKtmBlock:
    def test_no_engine_internal_content(self, raw):
        """222 owns the Duke twins and 224 the LC8c family. Writing
        engine internals here would shadow both."""
        forbidden = r"\bcrankshaft\b|\bcamshaft\b|\bpiston ring|\bconnecting rod\b|\bbalancer shaft\b"
        for e in raw:
            hits = re.findall(forbidden, _claims(e), re.I)
            assert not hits, f"{e['title']}: {hits} belongs to Phase 222/224"

    def test_no_1290_content_is_claimed_here(self, raw):
        """`Super Adventure` may appear — the first entry exists to
        distinguish the two. What is forbidden is writing the 1290's
        own content, so the mentions must be contrastive."""
        for e in raw:
            for m in re.finditer(r"Super Adventure", _claims(e)):
                window = _claims(e)[max(0, m.start() - 200):m.end() + 200]
                assert re.search(
                    r"different|distinct|not|as against|rather than|unrelated|"
                    r"does not|inapplicable|larger", window, re.I), e["title"]

    def test_no_fault_codes(self, raw):
        """The KTM block defers codes to Phase 225."""
        for e in raw:
            assert e["dtc_codes"] == [], e["title"]
            assert not re.findall(r"\bP0\d{3}\b", _claims(e)), e["title"]

    def test_no_ecu_or_tuning_content(self, raw):
        """Phase 225 owns engine management and tuning."""
        forbidden = r"\bTuneECU\b|\bremap\b|\bflash the ECU\b|\bKeihin\b|\bVitesco\b"
        for e in raw:
            hits = re.findall(forbidden, _claims(e), re.I)
            assert not hits, f"{e['title']}: {hits} belongs to Phase 225"

    def test_it_does_not_take_phase_238_ground(self, raw):
        """238 owns European valve service intervals across makes. This
        phase owns one narrower claim — that the Adventure and its Duke
        sibling differ — and deliberately prints no interval figures.

        Scoped to mileages used AS an interval. An owner reporting the
        mileage at which a part failed is a data point, not a schedule,
        and forbidding every number would have deleted that — the
        mention-versus-use distinction, again."""
        interval_words = r"(valve|service|interval|schedule|due|change at|every)"
        for e in raw:
            text = _claims(e)
            for m in re.finditer(r"\d{1,3},\d{3}\s*(km|miles)", text):
                window = text[max(0, m.start() - 90):m.end() + 90]
                assert not re.search(interval_words, window, re.I), \
                    f"{e['title']}: {m.group(0)} reads as an interval"
        entry = next(e for e in raw if "service schedule" in e["title"])
        assert re.search(r"deliberately not reproduced", entry["fix_procedure"])


class TestTheCorrectionsRefutationForced:
    def test_the_subframe_entry_refuses_the_950_990_reputation(self, raw):
        """The research's own trap: the KTM subframe-cracking story
        belongs to an earlier generation, and carrying it across is the
        cross-contamination error this project keeps catching."""
        entry = next(e for e in raw if "subframe" in e["title"].lower())
        text = _claims(entry)
        assert "950" in text and "990" in text
        assert re.search(r"does not belong|do not repeat|not.{0,30}support", text, re.I)

    def test_the_tyre_campaign_is_scoped_to_the_front(self, raw):
        """A refuter found the manufacturer's own notification limits
        this to the front tyre on these models, and to machines still
        on the originally fitted tyres. Quoting a pair is a real cost
        error."""
        entry = next(e for e in raw if "recalls" in e["title"])
        text = _claims(entry)
        assert re.search(r"\*\*front\*\*|front.{0,20}tyre", text, re.I)
        assert re.search(r"originally fitted|original tyres", text, re.I)

    def test_no_campaign_reference_numbers_appear(self, raw):
        """Carried forward from the Phase 231 decision, after a cited
        campaign number turned out to belong to another manufacturer."""
        for e in raw:
            assert not re.findall(r"\b\d{2}V\d{6}\b|\bRecall \d{6,7}\b", _claims(e)), \
                e["title"]

    def test_recall_check_is_by_frame_number_and_multi_database(self, raw):
        entry = next(e for e in raw if "recalls" in e["title"])
        text = _claims(entry)
        assert re.search(r"frame number", text, re.I)
        assert re.search(r"clean result in one is not a clean result", text, re.I)

    def test_the_unestablished_build_location_stays_unestablished(self, raw):
        """A refuter caught the research citing a press release that
        contains none of the claim attached to it. The honest state is
        'not established', and it has to survive into the content."""
        entry = next(e for e in raw if "built" in e["title"])
        text = _claims(entry)
        assert re.search(r"could not be established|unestablished", text, re.I)
        assert re.search(r"2025", text)


class TestTheFuelSystemContent:
    def test_one_pump_and_one_sender_on_opposite_sides(self, raw):
        entry = next(e for e in raw if "runs dry" in e["title"])
        text = _claims(entry)
        assert re.search(r"\*\*one\*\* fuel pump|one fuel pump", text, re.I)
        assert re.search(r"opposite sides", text, re.I)

    def test_both_starvation_causes_are_given_with_a_test(self, raw):
        entry = next(e for e in raw if "runs dry" in e["title"])
        text = _claims(entry)
        assert re.search(r"cock", text, re.I) and re.search(r"vacuum", text, re.I)
        assert re.search(r"open the filler cap", text, re.I)

    def test_the_gauge_entry_separates_design_from_fault(self, raw):
        entry = next(e for e in raw if "fuel gauge" in e["title"])
        text = _claims(entry)
        assert re.search(r"half", text, re.I)
        assert re.search(r"flash", text, re.I)

    def test_the_abs_location_changes_the_quote(self, raw):
        entry = next(e for e in raw if "ABS module" in e["title"])
        text = _claims(entry)
        assert re.search(r"under the fuel tank", text, re.I)
        assert re.search(r"before the customer approves|add tank removal", text, re.I)


class TestSearchability:
    @pytest.mark.parametrize("needle", [
        "ktm adventure runs out of fuel with fuel showing",
        "ktm adventure fuel gauge stuck on full",
        "ktm 890 adventure abs module location",
        "ktm adventure tubeless spoke wheel slow leak",
        "ktm 790 adventure subframe cracking",
        "where is my ktm 390 adventure built",
    ])
    def test_a_plausible_query_finds_something(self, raw, needle):
        # Prefix match rather than exact substring: a mechanic typing
        # "location" should reach an entry that says "located".
        words = [w[:5] for w in re.findall(r"[a-z0-9]+", needle) if len(w) > 3]
        best = max(
            sum(1 for w in words if w in _claims(e).lower()) for e in raw)
        assert best >= 3, f"{needle!r} matched only {best} terms"
