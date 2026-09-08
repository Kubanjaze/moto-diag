"""Phase 218 — Ducati Multistrada.

**The cam-drive guardrail becomes conditional here.** Phase 216 denied
cam chains on the Monster line (belt engines). Phase 217 denied cam
belts on the Panigale (chain engines). Both rules were correct per file.
The Multistrada breaks that pattern: the 1200, 1260 and V2 are belt
driven, the V4's Granturismo is chain driven, and they share a model
name. So the assertion below resolves belt-versus-chain **from each
entry's own model string** before judging its claims — the first
guardrail in the project that is conditional rather than flipped.

**The Granturismo also breaks Phase 219's premise.** Row 219 is
"Ducati desmodromic valve service"; the Multistrada V4 has conventional
spring valves and a far longer interval, so 219 does not apply to it.
That exclusion is asserted here and annotated on the roadmap.

Claim checks run on title, description, causes and fix_procedure and
never on `symptoms` — the Phase 217 lesson, where a symptom recording a
mistaken belief ("quoted for cam belts on a panigale") was wrongly
flagged as a claim.
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
MS_FILE = K / "known_issues_ducati_multistrada.json"
MON_FILE = K / "known_issues_ducati_monster.json"
PAN_FILE = K / "known_issues_ducati_panigale.json"
DUCATI_FILES = (MON_FILE, PAN_FILE, MS_FILE)

NEGATION = re.compile(
    r"\bno\b|\bnot\b|unlike|never|rather than|instead of|without|does not|nor ", re.I
)


def _claims(e: dict) -> str:
    """Assertion-bearing fields only; `symptoms` are reports."""
    return " ".join([e["title"], e["description"], e["fix_procedure"]] + e["causes"])


def _asserts(text: str, term: str) -> bool:
    for m in re.finditer(re.escape(term), text, re.I):
        if not NEGATION.search(text[max(0, m.start() - 80):m.start()]):
            return True
    return False


def _drive_for(model: str) -> str:
    """Which timing drive this entry's bike actually has."""
    v4 = bool(re.search(r"V4", model))
    twin = bool(re.search(r"1200|1260|V2\b", model))
    if v4 and not twin:
        return "chain"
    if twin and not v4:
        return "belt"
    return "both"


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "ms.db")
    init_db(path)
    load_known_issues_file(MS_FILE, path)
    return path


@pytest.fixture
def raw():
    return json.loads(MS_FILE.read_text(encoding="utf-8"))


class TestContent:
    def test_loads_eight(self, db_path):
        assert count_known_issues(db_path=db_path) == 8

    def test_all_are_ducati_multistrada(self, raw):
        for e in raw:
            assert e["make"] == "Ducati"
            assert "Multistrada" in e["model"], e["title"]

    def test_generations_are_covered(self, raw):
        models = " ".join(e["model"] for e in raw)
        for gen in ("1200", "1260", "V4"):
            assert gen in models, f"no entry naming {gen}"

    def test_severity_years_procedures(self, raw):
        for e in raw:
            assert e["severity"] in {"critical", "high", "medium", "low"}
            assert 2010 <= e["year_start"] <= e["year_end"] <= 2026, e["title"]
            assert e["fix_procedure"].strip() and e["estimated_hours"] > 0, e["title"]
            assert e["parts_needed"], e["title"]


class TestTheCamDriveRuleIsConditional:
    """Not one rule per file, as in 216 and 217 — one rule per entry,
    resolved from the bike it is about."""

    def test_no_belt_claimed_on_a_v4_only_entry(self, raw):
        for e in raw:
            if _drive_for(e["model"]) == "chain":
                assert not _asserts(_claims(e), "cam belt"), (
                    f"{e['title']}: claims a belt on a chain-driven V4"
                )

    def test_no_chain_claimed_on_a_belt_engine_entry(self, raw):
        for e in raw:
            if _drive_for(e["model"]) == "belt":
                assert not _asserts(_claims(e), "cam chain"), (
                    f"{e['title']}: claims a chain on a belt-driven Testastretta"
                )

    def test_the_split_itself_is_documented(self, raw):
        """An entry must actually explain that one model name covers two
        timing drives, or the conditional rule has nothing to stand on."""
        blob = json.dumps(raw).lower()
        assert "belt" in blob and "chain" in blob
        assert any("cam drive splits" in e["title"].lower() for e in raw)

    def test_both_sibling_files_still_hold_their_own_rules(self):
        """Counter-assertion: 216 and 217 remain correct for their own
        bikes. This phase is an exception, not a repeal."""
        assert "cam belt" in MON_FILE.read_text(encoding="utf-8").lower()
        assert "chain" in PAN_FILE.read_text(encoding="utf-8").lower()


class TestTheGranturismoExclusion:
    """Phase 219 is desmodromic valve service. The Multistrada V4 has
    spring valves, so 219 does not cover it."""

    def test_the_spring_valve_exception_is_stated(self, raw):
        blob = json.dumps(raw).lower()
        assert "spring" in blob and "desmodromic" in blob

    def test_it_does_not_write_the_desmo_procedure(self, raw):
        """Stating that desmo is absent is this phase's job; the desmo
        procedure itself belongs to 219."""
        for e in raw:
            t = e["title"].lower()
            assert "valve clearance" not in t and "shim" not in t, e["title"]
            assert "desmo service" not in t, e["title"]


class TestSpecificityAgainstASaturatedCorpus:
    """Five electronic-suspension entries and three adventure-touring
    files already exist. A sixth 'the unit failed' or a fourth 'loaded
    bike sags' adds nothing."""

    def test_any_skyhook_entry_is_about_load_not_failure(self, raw):
        sky = [e for e in raw if "skyhook" in json.dumps(e).lower()]
        for e in sky:
            blob = _claims(e).lower()
            assert "load" in blob or "preload" in blob, (
                f"{e['title']}: a sixth electronic-suspension failure entry"
            )

    def test_every_entry_names_multistrada_hardware(self, raw):
        marks = ("granturismo", "dvt", "skyhook", "radar", "multistrada",
                 "testastretta", "rally", "1260", "spring valve")
        for e in raw:
            blob = _claims(e).lower()
            assert any(m in blob for m in marks), e["title"]

    def test_no_title_collides_across_the_ducati_files(self):
        titles = []
        for f in DUCATI_FILES:
            titles += [e["title"] for e in json.loads(f.read_text(encoding="utf-8"))]
        assert len(titles) == len(set(titles))


class TestDeferralsAndProvenance:
    def test_no_fault_codes(self, raw):
        for e in raw:
            assert e["dtc_codes"] == [], e["title"]

    def test_no_ecu_or_tool_content(self, raw):
        blob = json.dumps(raw).lower()
        for term in ("marelli", "dda+", "dds tool"):
            assert term not in blob, term

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
        "quoted desmo service on a v4",
        "belt service overdue by age",
        "wallows when loaded with luggage",
    ])
    def test_a_mechanic_query_finds_the_entry(self, db_path, needle):
        assert find_issues_by_symptom(needle, db_path), needle


class TestAllThreeDucatiFilesCoexist:
    def test_they_load_together(self, tmp_path):
        path = str(tmp_path / "duc.db")
        init_db(path)
        for f in DUCATI_FILES:
            load_known_issues_file(f, path)
        assert count_known_issues(db_path=path) == 30
        assert len(search_known_issues(make="Ducati", db_path=path)) == 30
