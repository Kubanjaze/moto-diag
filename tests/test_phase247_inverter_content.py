"""Phase 247 — motor controller / inverter faults: the generic layer, anchored per make.

Every entry in `known_issues_inverter.json` is one of five concepts — the
controller's identity, its fault surface, overcurrent/phase/IGBT, controller
firmware, tooling — written as *what the controller does* and *how each make
shows it*, anchored to a manufacturer document for every make named, or not
written. 246's rules carry over unchanged: the document named in the
description (no citation column exists), every number labelled, one row one
label, a forum row dated. 247 adds a boundary: nothing here restates 246's
pack content or 249's temperature tables.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from motodiag.core.database import init_db
from motodiag.knowledge.issues_repo import search_known_issues
from motodiag.knowledge.loader import load_known_issues_file

ROOT = Path(__file__).resolve().parent.parent
K = ROOT / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"
INV = K / "known_issues_inverter.json"

#: One row per concept, named in the *title* (246's lesson: word-bounded, titles
#: only — a loose needle once matched "moderate" and hid a deleted row).
CONCEPTS = {
    "identity": r"\bmotor controller\b.*\bis\b|\binverter\b.*\bis\b",
    "fault surface": r"\bfault\b|\balert",
    "overcurrent phase igbt": r"overcurrent|phase|IGBT",
    "firmware": r"\bfirmware\b",
    "tooling": r"\btool\b|\breads\b",
}
_BAND_TABLE = re.compile(
    r"\bblue\b.*\bwhite\b.*\bred\b|\bblue\b.*\bgreen\b.*\byellow\b", re.I | re.S
)
_246_TITLES = re.compile(
    r"cell balancing|state of health|voltage curve|cycle count|thermal derating", re.I
)
#: 247's units are the controller's: amps, rpm, kW, torque, speed. A first draft
#: inherited 246's pack units and let a 600 A model-generated row through (mutation 2).
_NUMBER = re.compile(
    r"\b\d+(?:[.,]\d+)?\s?(?:mV|V|A|amps?|°C|°F|%|cycles?|Ah|kWh|kW|hp|rpm|N·m|ft-lbs|kph|km|mi)\b",
    re.I,
)
_DOCUMENT = re.compile(
    r"(owner'?s manual|service manual|service bulletin|release notes"
    r"|support (?:article|knowledge base)|spec(?:ification)? sheet|Rev\.|Cod\.)",
    re.I,
)


def _entries() -> list[dict]:
    d = json.loads(INV.read_text(encoding="utf-8"))
    return d if isinstance(d, list) else next(v for v in d.values() if isinstance(v, list))


def _ident(e: dict) -> str:
    return e["title"][:40]


def _text(e: dict) -> str:
    return " ".join(str(e.get(k) or "") for k in ("title", "description", "fix_procedure"))


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase247.db")
    init_db(path)
    load_known_issues_file(INV, path)
    return path


# ---------------------------------------------------------------------------
# 1. The entries exist and cover the row
# ---------------------------------------------------------------------------


class TestTheFiveConcepts:
    def test_the_seed_file_exists_and_loads(self, db):
        assert search_known_issues(db_path=db), "known_issues_inverter.json loaded nothing"

    def test_no_row_restates_246_or_249(self):
        """246 owns the pack, 249 owns the temperature tables. A 247 row may
        name a temperature-triggered fault; it may not carry the band table."""
        for e in _entries():
            assert not _246_TITLES.search(e["title"]), e["title"]
            assert not _BAND_TABLE.search(e["description"]), (e["title"][:40], "band table")

    @pytest.mark.parametrize("concept", sorted(CONCEPTS))
    def test_each_concept_has_an_entry(self, concept):
        pattern = re.compile(CONCEPTS[concept], re.I)
        assert any(pattern.search(e["title"]) for e in _entries()), concept

    def test_symptoms_follow_the_house_format(self):
        """`find_issues_by_symptom` is a LIKE match; the make phases hold
        symptoms to short phrases with no trailing period."""
        for e in _entries():
            assert e["symptoms"], e["title"]
            for s in e["symptoms"]:
                assert len(s) <= 55 and not s.endswith("."), (e["title"][:40], s)

    def test_every_entry_reaches_every_make_its_string_names(self, db):
        """Generic layer, anchored per make: a row's make string names the
        makes its anchors cover, and the junction 244F derives from it must
        carry every one of them — a LiveWire technician filtering by make
        has to reach the LiveWire half of each entry. The vocabulary is a
        function of the corpus in *this* database, so the index is rebuilt
        here rather than read from whatever the previous test configured."""
        import sqlite3

        from motodiag.knowledge import marques as mq

        mq.rebuild_make_index_at(db)
        c = sqlite3.connect(db)
        try:
            for e in _entries():
                got = {r[0] for r in c.execute(
                    "SELECT j.make FROM known_issue_makes j JOIN known_issues k "
                    "ON k.id = j.issue_id WHERE k.title = ?", (e["title"],))}
                named = {m.strip() for m in e["make"].split(",")}
                assert got == named, (e["title"][:40], got, named)
        finally:
            c.close()

    def test_no_entry_is_a_make_specific_failure_pattern(self):
        """242-244 own those. A 246 entry is the generic layer: it names what
        the BMS does and how a make exposes it, and its make is list-valued
        across the makes its anchor covers, or names the one make anchored."""
        for e in _entries():
            text = _text(e).lower()
            assert "how" in text or "shows" in text or "exposes" in text, e["title"]


# ---------------------------------------------------------------------------
# 2. Every entry is anchored, every number is labelled
# ---------------------------------------------------------------------------


class TestEveryEntryIsAnchored:
    @pytest.mark.parametrize("entry", _entries() if INV.exists() else [], ids=_ident)
    def test_a_service_manual_entry_names_its_document(self, entry):
        """No citation column exists; 244's convention is the document named
        in the description. `service-manual` without a named document is a
        label, not a source."""
        if entry["source"] == "service-manual":
            assert _DOCUMENT.search(entry["description"]), entry["title"]

    @pytest.mark.parametrize("entry", _entries() if INV.exists() else [], ids=_ident)
    def test_a_number_is_never_unlabelled(self, entry):
        """The operator's rule. A threshold is `service-manual` (document
        named) or `forum` — never `model-generated`, never `unverified`."""
        if _NUMBER.search(_text(entry)):
            assert entry["source"] in {"service-manual", "regulation", "forum"}, (
                f"{entry['title']}: a numeric threshold with source {entry['source']!r}"
            )

    @pytest.mark.parametrize("entry", _entries() if INV.exists() else [], ids=_ident)
    def test_a_regulation_entry_names_its_campaign(self, entry):
        """A regulator record is anchored by its campaign number, the way a
        manual row is anchored by its document code."""
        if entry["source"] == "regulation":
            assert re.search(r"\b\d{2}V\d{3}\b", entry["description"]), entry["title"]
            assert "NHTSA" in entry["description"], entry["title"]

    @pytest.mark.parametrize("entry", _entries() if INV.exists() else [], ids=_ident)
    def test_every_listed_code_is_named_in_the_text(self, entry):
        """`dtc_codes` is what a `code` lookup joins on; a code listed there
        must be the one the description names, character for character."""
        for code in entry["dtc_codes"]:
            assert code in entry["description"], (entry["title"][:40], code)

    @pytest.mark.parametrize("entry", _entries() if INV.exists() else [], ids=_ident)
    def test_a_forum_entry_names_where_it_came_from(self, entry):
        """The research reached one community source: zerologs.bike, an
        independent log-analyser site (its footer: "Made for Zero Motorcycles
        owners"). The Unofficial Zero Manual was again unreachable (expired
        TLS), so nothing may cite it. A forum entry names its site and the
        page's "Last updated" date."""
        if entry["source"] == "forum":
            assert re.search(
                r"(zerologs\.bike|forum|owner.community|thread)", entry["description"], re.I
            ), entry["title"]
            assert re.search(r"last updated:?\s+\w+ \d{1,2}, \d{4}", entry["description"], re.I), (
                f"{entry['title']}: a community page's figures need the page date beside them"
            )
            assert "zeromanual" not in _text(entry).lower(), (
                "the wiki was never fetched; it cannot be cited"
            )

    @pytest.mark.parametrize("entry", _entries() if INV.exists() else [], ids=_ident)
    def test_a_forum_number_never_shares_a_row_with_manual_content(self, entry):
        """One row carries one label. A community threshold inside a
        `service-manual` row would be displayed under the manual's label,
        which is the exact failure the operator's rule exists to prevent."""
        if entry["source"] == "service-manual":
            assert "zerologs" not in _text(entry).lower(), entry["title"]

    def test_nothing_is_model_generated(self):
        """246's practice: an entry that could not be anchored was not written."""
        assert all(e["source"] != "model-generated" for e in _entries())

    def test_no_entry_cites_a_fabricated_or_aggregator_source(self):
        bad = ("ev.care", "ridereview", "bikenrider", "wikipedia", "voltagebasics",
               "batterystoragehq", "tycorun")
        for e in _entries():
            assert not any(b in _text(e).lower() for b in bad), e["title"]


# ---------------------------------------------------------------------------
# 3. Reachable through the commands people use
# ---------------------------------------------------------------------------


class TestReachable:
    @pytest.fixture(autouse=True)
    def _wide(self, monkeypatch):
        monkeypatch.setenv("COLUMNS", "220")

    @pytest.mark.parametrize("term", ["inverter", "motor controller", "firmware"])
    def test_kb_search_finds_the_layer(self, db, monkeypatch, term):
        from motodiag.cli.main import cli
        from motodiag.core.config import reset_settings

        monkeypatch.setenv("MOTODIAG_DB_PATH", db)
        reset_settings()
        try:
            out = CliRunner().invoke(cli, ["kb", "search", term]).output
        finally:
            reset_settings()
        assert term.split()[0] in out.lower(), out
        assert ("service-manual" in out) or ("forum" in out), "the label must show by the result"
