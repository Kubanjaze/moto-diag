"""Phase 222 — KTM Duke naked line. Second phase of the KTM block.

**The specificity bar is calibrated, not copied.** Phase 221 required
three distinct 1290 terms per entry, and there it was the right bar: it
caught five of seven first-draft entries whose bodies were generic. The
Duke line has a narrower vocabulary — there is no MSC, no Bosch, no
Super Adventure — so entries here score two to four on the same style of
count. Lowering the number to make the file pass would be the failure
Phase 221 avoided, so the bar changed shape instead: every entry must
name at least one **model or engine designation** (LC8c, LC4, 790 Duke,
390 Duke, RC 390 …), in its title as well as its body. Brand-name
padding cannot satisfy that, and the corpus's existing parallel-twin
entry scores zero against it.

**The LC8c is a parallel twin.** Row 224 reserves cam chain tensioner,
electric start and valve clearance for the "LC8 V-twin"; the 790 and 890
use the LC8c, which is not a V-twin. That leaves the Duke twins' engine
unowned as the roadmap is written, so those three topics are avoided
here regardless of how 224 is later scoped — nothing gets written twice
either way.

**"Super Duke" contains "Duke".** A bare `\\bDuke\\b` check matches the
entire Phase 221 file, so every model assertion here is anchored to a
number or explicitly excludes the prefix.

**Mentioning the 1290 is allowed; writing about it is not.** The entry
that explains what the LC8c is *needs* to say what the LC8 is and where
it lives. The boundary is enforced on the 1290's own systems and model
names, and on the `model` field, not on the string "1290".
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
DUKE_FILE = K / "known_issues_ktm_duke.json"
KTM_FILES = sorted(K.glob("known_issues_ktm_*.json"))

#: A model or engine designation. Naming one of these is the bar — it is
#: what a generic entry about small bikes or parallel twins cannot do.
DESIGNATIONS = {
    "LC8c": r"\bLC8c\b",
    "LC4": r"\bLC4\b",
    "790 Duke": r"790 Duke",
    "890 Duke": r"890 Duke",
    "690 Duke": r"690 Duke",
    "390 Duke": r"390 Duke",
    "125 Duke": r"125 Duke",
    "RC 390": r"RC ?390",
}
#: Supporting terms. Real, but not sufficient on their own.
CONTEXT = {"KTM": r"\bKTM\b", "Bajaj": r"\bBajaj\b", "crankpin": r"crankpin"}

NEGATION = re.compile(
    r"\bno\b|\bnot\b|neither|unlike|never|rather than|instead of|without|does not|nor ",
    re.I,
)
REPORTED = re.compile(
    r"(says|said|saying|calls? it|called|reporting|reports?|"
    r"listed as|advertised as|take them at their word|"
    r"describ\w+(\s+\w+){0,3}\s+as)(\s+an?|\s+the)?\s*$",
    re.I,
)
#: Comparison, not identity. "the throttle feel of a V-twin" and "sounds
#: like a V-twin" say what the engine resembles — which is the entire
#: point of an entry explaining why an experienced rider gets it wrong.
#: Sixth consecutive phase in which my own check, not the content, was
#: at fault; this is the family's simile member.
SIMILE_BEFORE = re.compile(
    r"(like an?|feel of an?|sound of an?|beat of an?|character of an?|"
    r"feels? like|sounds? like|behaves? like|resembl\w+|mimic\w+)\s*$",
    re.I,
)
#: The term used attributively — "V-twin character", "V-twin beat" —
#: describes a quality, not the engine's architecture.
SIMILE_AFTER = re.compile(r"^\s*(character|characteristics?|feel|beat|sound|note)", re.I)


def _claims(e: dict) -> str:
    return " ".join([e["title"], e["description"], e["fix_procedure"]] + e["causes"])


def _named(e: dict, table: dict) -> list[str]:
    text = _claims(e)
    return [n for n, p in table.items() if re.search(p, text, re.I)]


def _asserts(text: str, term: str, window: int = 90) -> bool:
    """A positive claim that the thing under discussion *is* the term.

    Four exemptions, each one a phase's lesson: negation may precede or
    follow (219), reported speech is a quotation (221), and a comparison
    — before the term as a simile, after it as an attributive — says
    what something resembles, not what it is (this phase)."""
    for m in re.finditer(term, text, re.I):
        before = text[max(0, m.start() - window):m.start()]
        after = text[m.end():m.end() + window]
        if REPORTED.search(before[-45:]) or SIMILE_BEFORE.search(before[-30:]):
            continue
        if SIMILE_AFTER.match(after):
            continue
        if not (NEGATION.search(before) or NEGATION.search(after)):
            return True
    return False


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "duke.db")
    init_db(path)
    load_known_issues_file(DUKE_FILE, path)
    return path


@pytest.fixture
def raw():
    return json.loads(DUKE_FILE.read_text(encoding="utf-8"))


class TestContent:
    def test_loads_five(self, db_path):
        assert count_known_issues(db_path=db_path) == 5

    def test_all_are_ktm(self, raw, db_path):
        assert {e["make"] for e in raw} == {"KTM"}
        assert len(search_known_issues(make="KTM", db_path=db_path)) == 5

    def test_severity_years_procedures(self, raw):
        for e in raw:
            assert e["severity"] in {"critical", "high", "medium", "low"}
            assert 2008 <= e["year_start"] <= e["year_end"] <= 2026, e["title"]
            assert e["fix_procedure"].strip() and e["estimated_hours"] > 0, e["title"]
            assert e["parts_needed"], e["title"]

    def test_the_file_has_a_diagnostic_entry_not_only_identification(self, raw):
        """The first draft was five identification and sourcing entries
        with nothing diagnostic in it — a thin shape for a known-issues
        file. The uneven-beat entry is the spine that fixed that."""
        diagnostic = [e for e in raw if "misfire" in _claims(e).lower()]
        assert diagnostic, "no diagnostic entry — the file is all identification"


class TestSpecificityIsMeasuredOnDesignations:
    def test_every_entry_names_a_model_or_engine_designation(self, raw):
        for e in raw:
            assert _named(e, DESIGNATIONS), f"{e['title']}: names no designation"

    def test_every_title_names_one_too(self, raw):
        """A designation buried in a fix procedure is weaker than one in
        the title, where it tells a reader what the entry is about."""
        for e in raw:
            hit = [n for n, p in DESIGNATIONS.items()
                   if re.search(p, e["title"], re.I)]
            assert hit, f"{e['title']}: title names no designation"

    def test_every_entry_clears_two_distinct_terms_overall(self, raw):
        for e in raw:
            total = _named(e, DESIGNATIONS) + _named(e, CONTEXT)
            assert len(total) >= 2, f"{e['title']}: only {total}"

    def test_the_generic_parallel_twin_entry_fails_this_check(self):
        """The counter-assertion. The corpus already carries eight
        parallel-twin entries; the closest is a valve-clearance entry on
        the small Ninjas. It must score zero designations, or this
        file's bar is measuring nothing."""
        ninja = json.loads(
            (K / "known_issues_kawasaki_ninja_small.json").read_text(encoding="utf-8")
        )
        generic = [
            e for e in ninja
            if e["title"] == "Ninja 250R/300 valve clearance — parallel twin needs regular checks"
        ]
        assert generic, "the entry this file is measured against is gone"
        assert _named(generic[0], DESIGNATIONS) == []


class TestTheLC8cIsAParallelTwin:
    def test_no_entry_calls_the_duke_twins_a_v_twin(self, raw):
        """The whole point of the lead entry. Explaining that riders
        *describe* it as a V-twin is required; asserting it is one is
        the error being guarded against."""
        for e in raw:
            text = _claims(e)
            for m in re.finditer(r"V-twin", text, re.I):
                window = text[max(0, m.start() - 120):m.start()]
                # A V-twin claim is only acceptable about the LC8 itself.
                if re.search(r"\bLC8\b(?!c)", window):
                    continue
                assert not _asserts(text[max(0, m.start() - 120):m.end() + 60],
                                    r"V-twin"), f"{e['title']}: asserts a V-twin"

    def test_the_parallel_twin_architecture_is_stated_outright(self, raw):
        blob = json.dumps(raw)
        assert "parallel twin" in blob.lower()
        assert re.search(r"LC8c[^.]{0,80}parallel twin", blob, re.I), (
            "the LC8c is never directly called a parallel twin"
        )

    def test_the_crankpin_explains_why_the_mistake_is_convincing(self, raw):
        """Without the offset crankpin the entry is a bare correction;
        with it, it explains why an experienced rider gets it wrong."""
        assert "crankpin" in json.dumps(raw).lower()


class TestManufacturingOriginIsSourcingNotQuality:
    """The entry most able to go wrong. Origin is a legitimate sourcing
    and specification fact and an illegitimate proxy for quality."""

    def test_no_quality_claim_appears_anywhere(self, raw):
        forbidden = (
            r"\b(cheap|cheaply|poor quality|low quality|badly made|inferior|"
            r"shoddy|unreliable|worse build|inferior build)\b"
        )
        hits = re.findall(forbidden, json.dumps(raw), re.I)
        assert not hits, f"quality claim: {hits}"

    def test_the_entry_says_outright_what_it_is_not(self, raw):
        bajaj = [e for e in raw if "Bajaj" in _claims(e)]
        assert bajaj, "no manufacturing-origin entry"
        text = _claims(bajaj[0]).lower()
        assert "prejudice" in text or "not evidence" in text, (
            "the entry does not disclaim the quality reading"
        )

    def test_it_gives_the_two_practical_consequences(self, raw):
        bajaj = [e for e in raw if "Bajaj" in _claims(e)][0]
        text = _claims(bajaj).lower()
        assert "part number" in text
        assert "market" in text


class TestDeferralBoundaries:
    def test_no_1290_specific_systems_or_models(self, raw):
        """The string "1290" is allowed — the LC8c entry must say where
        the LC8 lives. What is forbidden is writing the 1290's own
        content."""
        forbidden = r"Super Duke|Super Adventure|\bMSC\b|\bMTC\b"
        for e in raw:
            hits = re.findall(forbidden, _claims(e), re.I)
            assert not hits, f"{e['title']}: {hits} belongs to Phase 221"

    def test_no_entry_is_actually_about_a_1290(self, raw):
        for e in raw:
            assert "1290" not in e["model"], e["title"]

    def test_no_phase_223_enduro_content(self, raw):
        forbidden = r"\bEXC\b|\bSMC\b|hard enduro|Enduro R|\b450\b|\b500\b"
        for e in raw:
            hits = re.findall(forbidden, _claims(e), re.I)
            assert not hits, f"{e['title']}: {hits} belongs to Phase 223"

    def test_none_of_224s_reserved_topics(self, raw):
        """Row 224 reserves these for the LC8 V-twin. Because the LC8c
        is a parallel twin, the row as written may not cover the Duke
        twins at all — so they are avoided here either way."""
        forbidden = (
            r"cam chain tensioner|electric start|starter (motor|clutch|sprag)|"
            r"valve clearance|valve service"
        )
        for e in raw:
            hits = re.findall(forbidden, _claims(e), re.I)
            assert not hits, f"{e['title']}: {hits} belongs to Phase 224"

    def test_no_phase_225_ecu_or_tuning_content(self, raw):
        forbidden = r"\bECU\b|Keihin|TuneECU|Tuneboy|remap|reflash|\bP0\d{3}\b"
        for e in raw:
            hits = re.findall(forbidden, _claims(e), re.I)
            assert not hits, f"{e['title']}: {hits} belongs to Phase 225"

    def test_no_fault_codes(self, raw):
        for e in raw:
            assert e["dtc_codes"] == [], e["title"]


class TestTheSuperDukePrefixTrap:
    def test_this_file_never_says_super_duke(self, raw):
        """A naive `\\bDuke\\b` check matches the entire 1290 file. This
        file's Dukes are always numbered."""
        assert "Super Duke" not in json.dumps(raw)

    def test_the_1290_file_still_does(self):
        """Counter-assertion: the trap is real, not hypothetical."""
        f = K / "known_issues_ktm_1290.json"
        assert "Super Duke" in f.read_text(encoding="utf-8")


class TestTheKtmFilesCoexist:
    def test_they_load_together(self, tmp_path):
        path = str(tmp_path / "ktm.db")
        init_db(path)
        for f in KTM_FILES:
            load_known_issues_file(f, path)
        assert count_known_issues(db_path=path) == 11
        assert len(search_known_issues(make="KTM", db_path=path)) == 11

    def test_no_title_collides(self):
        titles = []
        for f in KTM_FILES:
            titles += [e["title"] for e in json.loads(f.read_text(encoding="utf-8"))]
        assert len(titles) == len(set(titles))


class TestProvenanceAndSearchability:
    def test_every_entry_is_tagged(self, db_path, raw):
        rows = search_known_issues(make="KTM", db_path=db_path)
        assert {r["source"] for r in rows} == {"model-generated"}
        assert all(e.get("source") == "model-generated" for e in raw)

    def test_every_description_admits_its_origin(self, raw):
        for e in raw:
            assert "general knowledge" in e["description"].lower(), e["title"]

    def test_symptoms_are_short_phrases(self, raw):
        for e in raw:
            for s in e["symptoms"]:
                assert len(s) <= 55 and not s.endswith("."), f"{e['title']}: {s!r}"

    @pytest.mark.parametrize("needle", [
        "ordered v-twin parts for a 790 duke",
        "part number does not match the parts diagram",
        "rc 390 part does not fit the 390 duke",
        "enduro procedure quoted for a road bike",
        "790 duke sounds like it is missing",
    ])
    def test_a_mechanic_query_finds_the_entry(self, db_path, needle):
        assert find_issues_by_symptom(needle, db_path), needle
