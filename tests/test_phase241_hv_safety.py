"""Phase 241 — HV safety and lockout/tagout; Track L opens.

The first phase whose content can kill someone if it is wrong. The guards here
are therefore about honesty and reachability more than about coverage:

* every entry must be reachable from an electric make (Phase 240B's S2 —
  a prose `make` like "All European makes" matches nothing);
* no entry may print a pack voltage, a discharge wait or a torque it cannot
  attribute, and every entry must SAY it is withholding them;
* provenance must be honest — nothing here opened a manufacturer manual, so
  nothing here may claim to have;
* `SafetyChecker` has no production caller, and that gap is pinned as a
  tripwire rather than papered over.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from motodiag.core.database import init_db
from motodiag.knowledge.issues_repo import find_issues_by_symptom, search_known_issues
from motodiag.knowledge.loader import load_known_issues_file

K = Path(__file__).resolve().parents[1] / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"
SRC = Path(__file__).resolve().parents[1] / "src"
HV = K / "known_issues_electric_hv_safety.json"

#: The electric makes Track L covers. Every entry's `make` must contain at
#: least one of these verbatim, or `make LIKE '%X%'` cannot return it.
ELECTRIC_MAKES = ("Zero", "LiveWire", "Energica", "Damon")


@pytest.fixture(scope="module")
def raw():
    return json.loads(HV.read_text(encoding="utf-8"))


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "hv.db")
    init_db(path)
    load_known_issues_file(HV, path)
    return path


def _claims(e) -> str:
    """Assertion-bearing fields. `symptoms` are reports, not claims.

    Joined on newlines, not spaces: a cause ending "...the manual specifies"
    followed by a fix_procedure starting "1. Confirm" must not read as
    "the manual specifies 1". Field boundaries are clause boundaries, and
    every clause-scoped regex below excludes the newline."""
    return "\n".join([e["title"], e["description"], *e["causes"], e["fix_procedure"]])


# ---------------------------------------------------------------------------
# 1. Reachability — the S2 lesson, asserted rather than inherited
# ---------------------------------------------------------------------------
class TestEveryEntryIsReachable:
    def test_every_make_field_names_an_electric_make(self, raw):
        for e in raw:
            assert any(m in e["make"] for m in ELECTRIC_MAKES), (
                f"{e['title'][:60]}: make={e['make']!r} contains no electric make token — "
                "a make-filtered lookup cannot return it (Phase 240B, S2)"
            )

    @pytest.mark.parametrize("make", ELECTRIC_MAKES)
    def test_a_make_filtered_lookup_returns_the_whole_file(self, db, raw, make):
        assert len(search_known_issues(make=make, db_path=db)) == len(raw)

    def test_the_symptom_path_reaches_it_too(self, db):
        assert find_issues_by_symptom("service plug removed", db_path=db)

    def test_critical_entries_come_first(self, db):
        """Phase 240C made this ordering real. On a safety file it is the
        difference between the mechanic seeing 'verify absence of voltage'
        first or last."""
        sevs = [r["severity"] for r in search_known_issues(make="Zero", db_path=db)]
        rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        assert [rank[s] for s in sevs] == sorted((rank[s] for s in sevs), reverse=True), sevs


# ---------------------------------------------------------------------------
# 2. Deliberate absence — the figures are withheld, and the entry says so
# ---------------------------------------------------------------------------
class TestNoFigureIsInvented:
    #: A number followed by V, above the 12V/48V auxiliary range, is a pack
    #: voltage. "12V" and "48V" name the low-voltage system and are allowed.
    PACK_VOLTAGE = re.compile(r"\b(?!12V\b)(?!48V\b)\d{2,4}\s*V(?:DC|AC)?\b")
    WAIT = re.compile(r"\b\d+\s*(?:second|sec|minute|min|hour)s?\b", re.I)
    TORQUE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:Nm|N·m|ft[- ]?lbs?|lb[- ]?ft)\b", re.I)

    def test_no_pack_voltage_is_printed(self, raw):
        for e in raw:
            m = self.PACK_VOLTAGE.search(_claims(e))
            assert not m, f"{e['title'][:60]}: prints a pack voltage {m.group(0)!r}"

    def test_no_discharge_wait_is_printed(self, raw):
        for e in raw:
            m = self.WAIT.search(_claims(e))
            assert not m, f"{e['title'][:60]}: prints a wait interval {m.group(0)!r}"

    def test_no_torque_is_printed(self, raw):
        for e in raw:
            m = self.TORQUE.search(_claims(e))
            assert not m, f"{e['title'][:60]}: prints a torque {m.group(0)!r}"

    def test_every_entry_states_that_it_withholds_them(self, raw):
        """The absence is a deliverable only if it is announced. A silent gap
        reads as an oversight; a stated one routes the reader to the manual."""
        for e in raw:
            assert re.search(r"deliberately prints no|does not (?:state|supply|substitute)", e["description"]), (
                e["title"][:60]
            )
            assert "manufacturer" in e["description"].lower(), e["title"][:60]

    def test_the_patterns_can_actually_fire(self):
        """Anti-vacuity: each regex must match the shape it forbids and pass
        the shape it permits."""
        assert self.PACK_VOLTAGE.search("the pack is 116V nominal")
        assert self.PACK_VOLTAGE.search("a 350 VDC bus")
        assert not self.PACK_VOLTAGE.search("remove the 12V supply")
        assert self.WAIT.search("wait 5 minutes before")
        assert self.TORQUE.search("torque to 25 Nm")


# ---------------------------------------------------------------------------
# 3. Provenance — honest about what was and was not opened
# ---------------------------------------------------------------------------
class TestProvenanceIsHonest:
    def test_nothing_claims_a_manual_it_did_not_open(self, raw):
        """No manufacturer HV document was opened for this phase, so
        `service-manual` would be a false label. If a later phase opens
        one, this assertion is the thing to change — deliberately."""
        assert {e["source"] for e in raw} == {"model-generated"}

    def test_every_description_admits_its_origin(self, raw):
        for e in raw:
            assert "general knowledge" in e["description"].lower(), e["title"][:60]

    def test_forum_tip_marker_tracks_the_source(self, raw):
        for e in raw:
            assert ("Forum tip" in e["fix_procedure"]) == (e["source"] == "forum"), e["title"][:60]

    def test_no_entry_reads_as_a_certified_procedure(self, raw):
        """A model-generated entry must not borrow the voice of a document it
        is not: "the manual specifies 25 Nm" asserts a figure on the manual's
        authority. But "the point the manual specifies" — with no figure —
        is deferral, which is exactly what this file is supposed to do.
        Mention versus use, again: the guard fires only when borrowed
        authority is attached to a number within the same clause."""
        forbidden = re.compile(
            r"\b(?:per the manual|the manual (?:specifies|states)|manufacturer-approved|"
            r"rated (?:at|to)|certified (?:to|at))\b[^.;\n]{0,40}?\d", re.I,
        )
        for e in raw:
            m = forbidden.search(_claims(e))
            assert not m, f"{e['title'][:60]}: {m.group(0)!r} attaches borrowed authority to a figure"

    def test_the_certified_procedure_guard_can_fire(self):
        """Anti-vacuity, both directions."""
        forbidden = re.compile(
            r"\b(?:per the manual|the manual (?:specifies|states)|manufacturer-approved|"
            r"rated (?:at|to)|certified (?:to|at))\b[^.;\n]{0,40}?\d", re.I,
        )
        assert forbidden.search("the manual specifies a 5 minute wait")
        assert forbidden.search("gloves rated to 1000 V")
        assert not forbidden.search("at the point the manual specifies. 1. Confirm")
        assert not forbidden.search("in the order the manual specifies.")


# ---------------------------------------------------------------------------
# 4. Severity carries information, and the file is well-formed
# ---------------------------------------------------------------------------
class TestFileShape:
    def test_severity_is_not_uniformly_critical(self, raw):
        """Everything about HV feels critical. If every entry is, the ranking
        Phase 240C fixed carries no information."""
        assert len({e["severity"] for e in raw}) >= 2

    def test_the_lethal_ones_are_critical(self, raw):
        for needle in ("does not make the machine safe", "live-dead-live", "damaged, deformed or submerged",
                       "Do not work alone"):
            e = next(x for x in raw if needle in x["title"])
            assert e["severity"] == "critical", e["title"][:60]

    def test_symptoms_follow_the_house_format(self, raw):
        for e in raw:
            for s in e["symptoms"]:
                assert len(s) <= 55 and not s.endswith("."), (e["title"][:40], s)

    def test_no_title_collides_corpus_wide(self):
        titles = []
        for f in K.glob("known_issues_*.json"):
            titles += [e["title"] for e in json.loads(f.read_text(encoding="utf-8"))]
        assert len(titles) == len(set(titles))

    def test_no_campaign_reference_number(self, raw):
        blob = json.dumps(raw)
        assert not re.findall(r"\b\d{2}V\d{3}\b|RM/\d{4}/\d+", blob)


# ---------------------------------------------------------------------------
# 5. The integration gap, pinned rather than papered over
# ---------------------------------------------------------------------------
class TestTheSafetyCheckerGapIsRecorded:
    """`engine/safety.py` has a 19-rule SAFETY_RULES engine with exactly the
    shape HV rules want. Step 0 found that nothing in production constructs
    `SafetyChecker` — only tests do. HV rules were therefore NOT added there:
    a safety system with no delivery path is the appearance of safety, which
    on high voltage is worse than nothing.

    This pins the current state so the day someone wires the checker in, this
    fails and tells them what else that wiring needs."""

    def test_safety_checker_has_no_production_caller_today(self):
        hits = []
        for py in SRC.rglob("*.py"):
            if py.name in ("safety.py", "__init__.py"):
                continue
            if "SafetyChecker" in py.read_text(encoding="utf-8"):
                hits.append(str(py.relative_to(SRC)))
        assert not hits, (
            f"SafetyChecker is now constructed in production: {hits}. Before this ships, "
            "(1) give it vehicle/powertrain context — it has none, so an HV rule fires on a "
            "carburetted twin; (2) add the HV rules Phase 241 deliberately withheld; "
            "(3) delete this tripwire."
        )

    def test_no_hv_rule_was_added_to_the_unwired_engine(self):
        from motodiag.engine.safety import SAFETY_RULES

        hv = [r for r in SAFETY_RULES if re.search(r"high.?voltage|\bHV\b|traction (?:pack|battery)|service (?:plug|disconnect)",
                                                    json.dumps(r), re.I)]
        assert not hv, "HV rules landed in SAFETY_RULES while it still has no production caller"
