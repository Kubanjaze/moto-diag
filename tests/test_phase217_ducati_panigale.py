"""Phase 217 — Ducati Panigale, Streetfighter V4/V2.

**The guardrail inverts inside its own block.** Phase 216 asserted that
Ducatis are belt driven and denied "cam chain" on every Monster entry.
That is true of the Desmodue, Desmoquattro and Testastretta engines in
that file and **false here**: the Superquadro drives its cams by a chain
to a gear train between the camshafts, and the V4 Desmosedici Stradale
is chain driven too. Phase 216's assertion was scoped to its own file so
nothing broke, but its comment stated a false generalisation and was
corrected during this audit.

So this file asserts the *opposite* of its predecessor — no entry may
claim a cam belt on a Panigale — and keeps a counter-assertion that the
Monster file still legitimately owns belts.

**Claims versus reports.** The check runs on title, description, causes
and fix_procedure. It deliberately does **not** run on `symptoms`,
because a symptom records what a person reports, including a mistaken
belief: "quoted for cam belts on a panigale" is a correct symptom of
this exact problem, not a claim the bike has belts. A first-pass
validator flagged it — the third time in three phases that my own check,
not the content, was the thing at fault.
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

P_FILE = SEED_DATA_DIR / "knowledge" / "known_issues_ducati_panigale.json"
M_FILE = SEED_DATA_DIR / "knowledge" / "known_issues_ducati_monster.json"

NEGATION = re.compile(r"\bno\b|\bnot\b|unlike|never|rather than|instead of|without", re.I)


def _claims(entry: dict) -> str:
    """The assertion-bearing fields. `symptoms` are excluded on purpose —
    they record reported complaints, including mistaken ones."""
    return " ".join(
        [entry["title"], entry["description"], entry["fix_procedure"]]
        + entry["causes"]
    )


def _asserts(text: str, term: str) -> bool:
    for m in re.finditer(re.escape(term), text, re.I):
        if not NEGATION.search(text[max(0, m.start() - 70):m.start()]):
            return True
    return False


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "pani.db")
    init_db(path)
    load_known_issues_file(P_FILE, path)
    return path


@pytest.fixture
def raw():
    return json.loads(P_FILE.read_text(encoding="utf-8"))


class TestContent:
    def test_loads_ten(self, db_path):
        assert count_known_issues(db_path=db_path) == 10

    def test_all_are_ducati(self, db_path):
        assert len(search_known_issues(make="Ducati", db_path=db_path)) == 10

    def test_the_line_is_covered(self, raw):
        models = " ".join(e["model"] for e in raw)
        for m in ("1199", "959", "Panigale V4", "Streetfighter V4"):
            assert m in models, f"no entry naming {m}"

    def test_severity_years_and_procedures(self, raw):
        for e in raw:
            assert e["severity"] in {"critical", "high", "medium", "low"}
            assert 2012 <= e["year_start"] <= e["year_end"] <= 2026, e["title"]
            assert e["fix_procedure"].strip() and e["estimated_hours"] > 0, e["title"]
            assert e["parts_needed"], e["title"]


class TestTheCamDriveGuardrailInverts:
    """Phase 216 denies cam chains; this phase denies cam belts. Same
    make, opposite rule, because they are different engine families."""

    def test_no_entry_claims_a_cam_belt(self, raw):
        for e in raw:
            for term in ("cam belt", "timing belt"):
                assert not _asserts(_claims(e), term), (
                    f"{e['title']}: claims a {term} on a Panigale"
                )

    def test_a_symptom_may_still_report_a_mistaken_belt_quote(self, raw):
        """The distinction this file turns on: reporting that someone
        wrongly quoted belts is correct content."""
        symptoms = [s for e in raw for s in e["symptoms"]]
        assert any("belt" in s.lower() for s in symptoms)

    def test_the_chain_and_gear_drive_is_actually_stated(self, raw):
        blob = json.dumps(raw).lower()
        assert "chain" in blob and "gear" in blob

    def test_the_monster_file_still_owns_belts(self):
        """Counter-assertion — belts are real on the Monster line, so
        the rule above is a scope boundary, not a claim about Ducati."""
        assert "cam belt" in M_FILE.read_text(encoding="utf-8").lower()


class TestPanigaleSpecificity:
    """Six litre-class superbikes are already in the corpus. An entry
    that would read the same on a ZX-10R adds nothing."""

    def test_every_entry_names_panigale_hardware(self, raw):
        marks = ("superquadro", "desmosedici", "monocoque", "smart ec",
                 "counter-rotating", "panigale", "streetfighter v4",
                 "rear-bank", "rear bank")
        for e in raw:
            blob = _claims(e).lower()
            assert any(m in blob for m in marks), e["title"]

    def test_no_title_collides_with_the_monster_file(self, raw):
        monster = {e["title"] for e in json.loads(M_FILE.read_text(encoding="utf-8"))}
        assert not {e["title"] for e in raw} & monster


class TestDeferrals:
    def test_no_fault_codes(self, raw):
        for e in raw:
            assert e["dtc_codes"] == [], e["title"]

    def test_no_valve_service_content(self, raw):
        """Desmo intervals, shims and clearances belong to Phase 219 —
        including the 15,000 mile figure surfaced during the audit."""
        for e in raw:
            t = e["title"].lower()
            assert "valve clearance" not in t and "shim" not in t, e["title"]
            assert "desmo service" not in t, e["title"]

    def test_no_ecu_or_tool_content(self, raw):
        blob = json.dumps(raw).lower()
        for term in ("marelli", "dda+", "dds tool"):
            assert term not in blob, term


class TestProvenanceAndSearchability:
    def test_every_entry_is_tagged(self, db_path, raw):
        rows = search_known_issues(make="Ducati", db_path=db_path)
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
        "quoted for cam belts on a panigale",
        "misfire at idle only",
        "coolant level slowly dropping",
    ])
    def test_a_mechanic_query_finds_the_entry(self, db_path, needle):
        """Needles quoted from the shipped data — invented ones missed
        in Phases 214 and 216."""
        assert find_issues_by_symptom(needle, db_path), needle


class TestBothDucatiFilesCoexist:
    def test_they_load_together(self, tmp_path):
        path = str(tmp_path / "duc.db")
        init_db(path)
        for f in (M_FILE, P_FILE):
            load_known_issues_file(f, path)
        FILES = (M_FILE, P_FILE)
        # Phase 240B: was a hardcoded total. A count derived from the same
        # JSON the test loads survives corpus growth; a literal has to be
        # hand-edited by every later phase that adds an entry. The make
        # filter is a substring match (`make LIKE '%X%'`), so the
        # make-filtered number is counted the same way rather than assumed
        # equal to the file total -- they diverge the moment a compound or
        # cross-make entry lands in a make-prefixed file.
        entries = [e for f in FILES for e in json.loads(f.read_text(encoding="utf-8"))]
        assert count_known_issues(db_path=path) == len(entries)
        assert len(search_known_issues(make="Ducati", db_path=path)) == sum(
            1 for e in entries if "ducati" in e["make"].lower()
        )


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

    The probe uses a literal term because this file's `_asserts` calls
    re.finditer(re.escape(term), ...) -- the two implementations in the tree differ, and a probe
    written with the wrong kind returns False for the wrong reason and
    asserts exactly the deadness it is meant to detect."""

    def test_a_plain_assertion_registers(self):
        assert _asserts("The engine is a V-twin.", 'V-twin') is True

    def test_a_negated_assertion_does_not(self):
        assert _asserts("The engine is not a V-twin.", 'V-twin') is False

    def test_an_absent_term_does_not(self):
        assert _asserts("The engine is a parallel twin.", 'V-twin') is False
