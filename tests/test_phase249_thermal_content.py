"""Phase 249 — thermal management: the generic layer, anchored per make.

Every entry in `known_issues_thermal.json` is one of four concepts — the
cooling architecture, motor and controller temperature, the cooling loop's
own faults, ambient temperature — written as *what the thermal system does*
and *how each make shows it*, anchored to a manufacturer document for every
make named, or not written. 246–248's rules carry over. 249's boundary is
sharper than any earlier row's, because most of the row was already
written: no 249 sentence about the battery may repeat a temperature range
from 246's thermal-derating row, and no 249 row may repeat 243's coolant
interval. A 249 row names those by reference.
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
THM = K / "known_issues_thermal.json"
BMS = K / "known_issues_bms.json"

#: One row per concept, named in the *title* (246's lesson: word-bounded, titles
#: only — a loose needle once matched "moderate" and hid a deleted row).
CONCEPTS = {
    "architecture": r"\b(?:liquid|air|oil)[- ]cooled\b",
    "motor temperature": r"\bmotor\b.*\btemperature\b|\bthermal strategy\b",
    "cooling faults": r"\b(?:cooling|coolant)\b.*\bfault|\bpump\b",
    "ambient": r"\bambient\b|\bheat and cold\b|\bhot and cold\b",
}
_OTHER_ROWS = re.compile(
    r"cell balancing|state of health|voltage curve|cycle count|thermal derating is"
    r"|motor controller is|inverter faults|controller firmware|\bregen\b", re.I
)
_RANGE = re.compile(r"-?\d+\s?(?:-|to)\s?-?\d+\s?°C")


def _shipped_battery_ranges() -> set[str]:
    """Every temperature range 246's thermal-derating row prints, normalised."""
    rows = json.loads(BMS.read_text(encoding="utf-8"))
    row = next(r for r in rows if r["title"].startswith("Thermal derating is the BMS"))
    return {re.sub(r"\s+", "", m) for m in _RANGE.findall(row["description"])}
#: 249's units are temperatures, capacities and intervals, plus everything 246–248 caught.
#: The trailing guard is a lookahead, not \b: a word boundary never follows '%',
#: so '40%' was invisible to this rule until Phase 248's mutation 2 caught it.
_NUMBER = re.compile(
    r"\b\d+(?:[.,]\d+)?\s?(?:mV|V|A|amps?|°C|°F|%|percent|cycles?|Ah|kWh|kW|hp|rpm|N·m|ft-lbs|kph|km/h|mph|km|mi|qt|L|min|minutes|hours)(?!\w)",
    re.I,
)
_DOCUMENT = re.compile(
    r"(owner'?s manual|service manual|service bulletin|release notes"
    r"|support (?:article|knowledge base)|spec(?:ification)? sheet|Rev\.|Cod\.)",
    re.I,
)


def _entries() -> list[dict]:
    d = json.loads(THM.read_text(encoding="utf-8"))
    return d if isinstance(d, list) else next(v for v in d.values() if isinstance(v, list))


def _ident(e: dict) -> str:
    return e["title"][:40]


def _text(e: dict) -> str:
    return " ".join(str(e.get(k) or "") for k in ("title", "description", "fix_procedure"))


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase249.db")
    init_db(path)
    load_known_issues_file(THM, path)
    return path


# ---------------------------------------------------------------------------
# 1. The entries exist and cover the row
# ---------------------------------------------------------------------------


class TestTheFiveConcepts:
    def test_the_seed_file_exists_and_loads(self, db):
        assert search_known_issues(db_path=db), "known_issues_thermal.json loaded nothing"

    def test_no_row_claims_a_liquid_cooled_battery(self):
        """Row 249's own premise ('liquid cooling loops (battery)') is not borne
        out by any maker's documents. A row may say that no document describes
        one; it may not assert either a liquid-cooled or an air-cooled pack."""
        claim = re.compile(
            r"(?:battery|pack|RESS) is (?:liquid|air)[- ]cooled"
            r"|(?:liquid|air)[- ]cooled (?:battery|pack|RESS)\b(?! on any)", re.I
        )
        for e in _entries():
            for field in ("description", "fix_procedure"):
                found = claim.search(e.get(field) or "")
                assert not found, (e["title"][:40], found and found.group(0))

    def test_energica_is_anchored_to_the_document_not_a_model_year(self):
        """The Eva manual's revision date is February 2018 and its sample labels
        read model year 2016, so '2018 Eva' asserts a year the document does
        not state; 249 anchors to the document code and revision."""
        for e in _entries():
            if "Energica" in e["make"]:
                assert "2018 Eva" not in e["description"], e["title"][:40]
                assert "ENF003100 Rev. 02" in e["description"], e["title"][:40]

    def test_no_row_restates_what_is_already_shipped(self):
        """Most of row 249 was written before it opened. A 249 row may name
        246's battery bands, 243's coolant interval and the 247/248 rows; it
        may not copy them, or a correction to one would leave a stale twin."""
        shipped = _shipped_battery_ranges()
        assert shipped, "246's thermal-derating row no longer prints a range"
        for e in _entries():
            assert not _OTHER_ROWS.search(e["title"]), e["title"]
            for field in ("description", "fix_procedure"):
                text = e.get(field) or ""
                assert "50,000 mi" not in text and "80,000 km" not in text, (
                    e["title"][:40], "243's coolant interval, copied"
                )
                for sentence in re.split(r"(?<=[.!?])\s+", text):
                    if "battery" in sentence.lower() or "pack" in sentence.lower():
                        found = {re.sub(r"\s+", "", m) for m in _RANGE.findall(sentence)}
                        assert not (found & shipped), (e["title"][:40], sorted(found & shipped))

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
    @pytest.mark.parametrize("entry", _entries() if THM.exists() else [], ids=_ident)
    def test_a_service_manual_entry_names_its_document(self, entry):
        """No citation column exists; 244's convention is the document named
        in the description. `service-manual` without a named document is a
        label, not a source."""
        if entry["source"] == "service-manual":
            assert _DOCUMENT.search(entry["description"]), entry["title"]

    @pytest.mark.parametrize("entry", _entries() if THM.exists() else [], ids=_ident)
    def test_a_number_is_never_unlabelled(self, entry):
        """The operator's rule. A threshold is `service-manual` (document
        named) or `forum` — never `model-generated`, never `unverified`."""
        if _NUMBER.search(_text(entry)):
            assert entry["source"] in {"service-manual", "regulation", "forum"}, (
                f"{entry['title']}: a numeric threshold with source {entry['source']!r}"
            )

    @pytest.mark.parametrize("entry", _entries() if THM.exists() else [], ids=_ident)
    def test_a_regulation_entry_names_its_campaign(self, entry):
        """A regulator record is anchored by its campaign number, the way a
        manual row is anchored by its document code."""
        if entry["source"] == "regulation":
            assert re.search(r"\b\d{2}V\d{3}\b", entry["description"]), entry["title"]
            assert "NHTSA" in entry["description"], entry["title"]

    @pytest.mark.parametrize("entry", _entries() if THM.exists() else [], ids=_ident)
    def test_every_listed_code_is_named_in_the_text(self, entry):
        """`dtc_codes` is what a `code` lookup joins on; a code listed there
        must be the one the description names, character for character."""
        for code in entry["dtc_codes"]:
            assert code in entry["description"], (entry["title"][:40], code)

    @pytest.mark.parametrize("entry", _entries() if THM.exists() else [], ids=_ident)
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

    @pytest.mark.parametrize("entry", _entries() if THM.exists() else [], ids=_ident)
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

    @pytest.mark.parametrize("term", ["cooling", "motor temperature", "ambient"])
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
