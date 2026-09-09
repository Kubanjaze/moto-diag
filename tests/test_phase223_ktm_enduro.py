"""Phase 223 — KTM enduro (EXC / EXC-F / 690 Enduro R).

**The first phase in the KTM block whose gaps are large rather than
narrow.** 221 and 222 both fought duplication. Here the searches came
back empty: across 756 entries, `TPI`, `transfer port`, `engine hour`,
`hour meter`, `competition` and `piston replacement` each had **zero**
hits, and the only genuine two-stroke service content was three
RD350/400 entries in `yamaha_vintage` — 1970s road bikes.

**But the off-road topic is well covered, so the backwards genericness
test still applies.** Four dual-sport files hold 40 entries between them:
DR650, KLR, XR, WR. Those are trail machines meant to last. What they
cannot describe is a **competition** machine meant to be rebuilt, and
that distinction is what this file is built on — service in engine hours,
top-end work as maintenance, a fuel-injected two-stroke.

**Interval figures are deferred by test**, as in Phase 219, and it
matters more here: a missed top end on a competition two-stroke is an
engine, not a wrong quote.

**Quotation marks are the seventh exemption.** The check flagged
`A request for a top end on a "450 EXC"` as calling a four-stroke a
plain EXC — a sentence whose entire job is to name the error, and which
already marks it as a citation with quote marks. Text inside quotation
marks is cited, not asserted. That joins negation (216/219), reported
speech (221) and comparison (222).
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
ENDURO_FILE = K / "known_issues_ktm_enduro.json"
KTM_FILES = sorted(K.glob("known_issues_ktm_*.json"))

#: An enduro designation. Naming one is the bar — it is what the 40
#: existing trail and dual-sport entries cannot do.
DESIGNATIONS = {
    "EXC-F": r"EXC-F",
    "EXC": r"\bEXC\b",
    "TPI": r"\bTPI\b",
    "LC4": r"\bLC4\b",
    "690 Enduro R": r"690 Enduro R",
    "transfer port": r"transfer port",
}

NEGATION = re.compile(
    r"\bno\b|\bnot\b|neither|unlike|never|rather than|instead of|without|does not|nor ",
    re.I,
)
REPORTED = re.compile(
    r"(says|said|saying|calls? it|called|reporting|reports?|listed as|"
    r"advertised as|request for|describ\w+(\s+\w+){0,3}\s+as)(\s+an?|\s+the)?\s*$",
    re.I,
)
SIMILE_BEFORE = re.compile(
    r"(like an?|feel of an?|sound of an?|beat of an?|character of an?|"
    r"feels? like|sounds? like|behaves? like|resembl\w+|mimic\w+)\s*$",
    re.I,
)


def _claims(e: dict) -> str:
    return " ".join([e["title"], e["description"], e["fix_procedure"]] + e["causes"])


def _quoted_spans(text: str) -> list[tuple[int, int]]:
    """Ranges inside paired double quotes. Text a writer put in quotes is
    being cited — naming an error is not committing it."""
    return [(m.start(), m.end()) for m in re.finditer(r"\"[^\"]{1,120}\"", text)]


def _asserts(text: str, term: str, window: int = 90) -> bool:
    """A positive claim the corpus makes.

    Exemptions, each one a phase's lesson: negation before or after
    (216/219), reported speech (221), comparison (222), and quotation
    (this phase)."""
    quoted = _quoted_spans(text)
    for m in re.finditer(term, text, re.I):
        if any(a <= m.start() and m.end() <= b for a, b in quoted):
            continue
        before = text[max(0, m.start() - window):m.start()]
        after = text[m.end():m.end() + window]
        if REPORTED.search(before[-45:]) or SIMILE_BEFORE.search(before[-30:]):
            continue
        if not (NEGATION.search(before) or NEGATION.search(after)):
            return True
    return False


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "enduro.db")
    init_db(path)
    load_known_issues_file(ENDURO_FILE, path)
    return path


@pytest.fixture
def raw():
    return json.loads(ENDURO_FILE.read_text(encoding="utf-8"))


class TestContent:
    def test_loads_six(self, db_path):
        assert count_known_issues(db_path=db_path) == 6

    def test_all_are_ktm(self, raw, db_path):
        assert {e["make"] for e in raw} == {"KTM"}
        assert len(search_known_issues(make="KTM", db_path=db_path)) == 6

    def test_severity_years_procedures(self, raw):
        for e in raw:
            assert e["severity"] in {"critical", "high", "medium", "low"}
            assert 2008 <= e["year_start"] <= e["year_end"] <= 2026, e["title"]
            assert e["fix_procedure"].strip() and e["estimated_hours"] > 0, e["title"]
            assert e["parts_needed"], e["title"]

    def test_the_oiling_entry_is_the_critical_one(self, raw):
        """If any entry here rates critical it is the one where the
        engine is destroyed by putting the wrong thing in the tank —
        in either direction."""
        tpi = [e for e in raw if "TPI two-stroke" in e["title"]]
        assert tpi and tpi[0]["severity"] == "critical"


class TestCompetitionNotTrail:
    """40 dual-sport entries already exist. Avoiding their topic is not
    enough — an entry must name an enduro designation."""

    def test_every_entry_names_a_designation_in_body_and_title(self, raw):
        for e in raw:
            assert [n for n, p in DESIGNATIONS.items() if re.search(p, _claims(e))], (
                f"{e['title']}: names no designation"
            )
            assert [n for n, p in DESIGNATIONS.items() if re.search(p, e["title"])], (
                f"{e['title']}: title names no designation"
            )

    def test_an_existing_dual_sport_entry_fails_this_check(self):
        """The counter-assertion. The corpus's off-road entries describe
        trail machines; if one scored a designation the bar would be
        measuring nothing."""
        for f in ("known_issues_honda_dualsport.json",
                  "known_issues_suzuki_dual_sport.json"):
            for e in json.loads((K / f).read_text(encoding="utf-8")):
                hits = [n for n, p in DESIGNATIONS.items()
                        if re.search(p, _claims(e))]
                assert not hits, f"{f}: {e['title']} scores {hits}"

    def test_the_competition_distinction_is_actually_drawn(self, raw):
        blob = json.dumps(raw).lower()
        assert "competition" in blob
        assert "engine hours" in blob


class TestIntervalsAreDeferredNotQuoted:
    """Phase 219's discipline, and it matters more here — a missed top
    end on a competition two-stroke is an engine, not a wrong quote."""

    def test_no_entry_states_a_service_interval_as_fact(self, raw):
        for e in raw:
            hits = re.findall(
                r"\b\d{1,3},?\d{0,3}\s*(?:hours?|hrs?|mi|miles?|km)\b",
                _claims(e), re.I,
            )
            assert not hits, f"{e['title']}: states an interval {hits}"

    def test_the_hours_entry_defers_to_the_manual(self, raw):
        hours = [e for e in raw if "engine hours" in e["title"]]
        assert hours, "no engine-hours entry"
        assert "manual" in _claims(hours[0]).lower()

    def test_every_entry_that_mentions_an_interval_points_at_the_manual(self, raw):
        for e in raw:
            text = _claims(e).lower()
            if "interval" in text:
                assert "manual" in text, f"{e['title']}: interval with no manual"


class TestTheTpiOilingDistinction:
    def test_no_entry_says_a_tpi_model_takes_premix(self, raw):
        """The claim that destroys engines. Explaining that riders mix by
        habit is required; asserting the bike takes premix is not.

        Phase 240B widened the search. The original pattern was the exact
        two-word form `takes premix|takes premixed`, taken verbatim from the
        entry's own symptom string -- a deliberate choice, since `_claims`
        excludes `symptoms`. But that form appears nowhere in the assertion
        fields, so the loop never entered and the guard was inert: coverage
        showed the assert line unreached, and "requires premix", "needs
        premix" and "runs on premix" all passed unchallenged.

        The bare stem is what the corpus actually authors -- the live match
        is "does not take premixed fuel", which `_asserts` correctly exempts
        by negation, so the body now executes and still passes. The original
        literal is kept so the symptom wording stays barred from claim
        fields."""
        PREMIX = r"\b(?:takes?|needs?|requires?|runs? on|uses?)\s+premix|takes premixed"
        tpi = [e for e in raw if "TPI" in _claims(e)]
        assert tpi, "no TPI entry — the filter selects nothing and the guard is inert"
        for e in tpi:
            text = _claims(e)
            for m in re.finditer(PREMIX, text, re.I):
                seg = text[max(0, m.start() - 110):m.end() + 40]
                assert not _asserts(seg, PREMIX), e["title"]

    def test_the_oil_pump_and_tank_are_stated(self, raw):
        tpi = [e for e in raw if "TPI" in _claims(e)][0]
        text = _claims(tpi).lower()
        assert "oil pump" in text or "pump" in text
        assert "oil tank" in text

    def test_both_directions_of_the_error_are_covered(self, raw):
        """Mixing oil that should not be mixed, and never filling the
        tank that must be. Only covering one leaves half the engines."""
        tpi = [e for e in raw if "TPI" in _claims(e)][0]
        text = _claims(tpi).lower()
        assert "mix" in text
        assert "never fill" in text or "kept filled" in text or "run low" in text


class TestTheExcSuffix:
    def test_no_four_stroke_is_called_a_plain_exc(self, raw):
        """350/450/500 are EXC-F models. Citing the error in quotes is
        the point of the naming entry; committing it is not."""
        for e in raw:
            assert not _asserts(_claims(e), r"\b(350|450|500)\s*EXC\b(?!-F)"), (
                f"{e['title']}: calls a four-stroke a plain EXC"
            )

    def test_the_error_is_named_rather_than_silently_avoided(self, raw):
        """A mechanic who hears "450 EXC" from a customer needs to be
        told what is wrong with it."""
        assert re.search(r"450 EXC", json.dumps(raw)), "the error is never shown"

    def test_the_distinction_is_stated_both_ways(self, raw):
        blob = json.dumps(raw)
        assert re.search(r"EXC[^-][^.]{0,60}two-stroke", blob, re.I)
        assert re.search(r"EXC-F[^.]{0,60}four-stroke", blob, re.I)


class TestDeferralBoundaries:
    def test_no_221_or_222_content(self, raw):
        forbidden = (
            r"\b1290\b|Super Duke|Super Adventure|\bMSC\b|\bMTC\b|"
            r"\bLC8c\b|Bajaj|790 Duke|890 Duke|390 Duke|125 Duke|RC ?390"
        )
        for e in raw:
            hits = re.findall(forbidden, _claims(e), re.I)
            assert not hits, f"{e['title']}: {hits} belongs to Phase 221/222"

    def test_no_lc8_v_twin_content(self, raw):
        """Row 224 owns the V-twin. The LC4 is a single and neither an
        LC8 nor an LC8c, so it is this phase's — but the V-twin is not."""
        for e in raw:
            hits = re.findall(r"\bLC8\b(?!c)|V-twin", _claims(e), re.I)
            assert not hits, f"{e['title']}: {hits} belongs to Phase 224"

    def test_no_phase_225_ecu_or_tuning_content(self, raw):
        forbidden = r"\bECU\b|Keihin|TuneECU|Tuneboy|remap|reflash|\bP0\d{3}\b"
        for e in raw:
            hits = re.findall(forbidden, _claims(e), re.I)
            assert not hits, f"{e['title']}: {hits} belongs to Phase 225"

    def test_the_mid_size_adventure_gap_is_recorded_not_taken(self, raw):
        """Row 223 is titled "enduro / adventure" but names only enduro
        singles, and the 390/790/890 Adventure appear in no row at all.
        Putting a parallel-twin tourer in with competition two-strokes
        would be incoherent, so the gap went on the roadmap instead."""
        for e in raw:
            hits = re.findall(r"390 Adventure|790 Adventure|890 Adventure",
                              _claims(e), re.I)
            assert not hits, f"{e['title']}: took the Adventure gap"

    def test_no_fault_codes(self, raw):
        for e in raw:
            assert e["dtc_codes"] == [], e["title"]


class TestTheKtmFilesCoexist:
    def test_they_load_together(self, tmp_path):
        """Counted against the files on disk, not a constant.

        Phase 222 fixed a Phase 221 guard that could not survive the KTM
        block growing — and then wrote this one, which globbed the KTM
        files but hardcoded their total. Phase 223 duly broke it. The
        encoding that survives is the invariant: loading every KTM file
        yields exactly the sum of their entries, with none lost to a
        title collision, and this file contributes 6."""
        path = str(tmp_path / "ktm.db")
        init_db(path)
        expected = 0
        for f in KTM_FILES:
            load_known_issues_file(f, path)
            expected += len(json.loads(f.read_text(encoding="utf-8")))
        assert count_known_issues(db_path=path) == expected
        assert len(search_known_issues(make="KTM", db_path=path)) == expected
        assert len(json.loads(ENDURO_FILE.read_text(encoding="utf-8"))) == 6

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
        "unsure if this two stroke takes premix",
        "booking says 450 exc",
        "low mileage but engine sounds tired",
        "owner alarmed by a top end quote",
        "two stroke feels flat in the midrange",
        "bike used off road but serviced as a road bike",
    ])
    def test_a_mechanic_query_finds_the_entry(self, db_path, needle):
        assert find_issues_by_symptom(needle, db_path), needle


class TestTheDiscriminatorItself:
    """Phase 240B. `_asserts` is the mention-versus-use predicate every guard
    in this file is built on, and its `return True` branch was never reached
    by any test in the suite. Proved by mutation: replacing `_asserts` with
    `lambda *a, **k: False` across the seven files that define it left 180 of
    181 tests passing -- only Phase 221 noticed, and it noticed through a
    real-data positive assertion rather than a probe.

    So every guard here would have behaved identically if the predicate had
    been stubbed out. The dangerous regression is an exemption regex that
    over-matches: that turns `_asserts` permanently False, silently disarming
    every guard built on it while the suite stays green.

    The probe uses a regex term because this file's `_asserts` calls
    re.finditer(term, ...) -- the two implementations in the tree differ, and a probe
    written with the wrong kind returns False for the wrong reason and
    asserts exactly the deadness it is meant to detect."""

    def test_a_plain_assertion_registers(self):
        assert _asserts("The engine is a V-twin.", '\\bV-twin\\b') is True

    def test_a_negated_assertion_does_not(self):
        assert _asserts("The engine is not a V-twin.", '\\bV-twin\\b') is False

    def test_an_absent_term_does_not(self):
        assert _asserts("The engine is a parallel twin.", '\\bV-twin\\b') is False
