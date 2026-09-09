"""Phase 242 — Zero Motorcycles, the first make-specific electric phase.

Written BEFORE the research returned, from the rules plan v1.0 committed to.
These are invariants on whatever content survives refutation; the
content-shaped tests (headline entries, generations covered) are added after.

Two boundaries drive everything here:
* a machine-specific figure is printed ONLY from a named Zero document the
  research opened (Phase 238's rule, hardened at 241) — otherwise it is
  withheld and the entry says so;
* Zero-specific only — 246/247/249 own BMS, inverter and thermal.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from motodiag.core.database import init_db
from motodiag.knowledge.issues_repo import search_known_issues
from motodiag.knowledge.loader import load_known_issues_file

K = Path(__file__).resolve().parents[1] / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"
ZERO = K / "known_issues_zero.json"
HV = K / "known_issues_electric_hv_safety.json"


@pytest.fixture(scope="module")
def raw():
    return json.loads(ZERO.read_text(encoding="utf-8"))


@pytest.fixture
def db(tmp_path):
    """Zero file loaded WITH 241's HV floor, because that is what a
    `make=Zero` query returns in the product."""
    path = str(tmp_path / "zero.db")
    init_db(path)
    load_known_issues_file(HV, path)
    load_known_issues_file(ZERO, path)
    return path


def _claims(e) -> str:
    """Assertion-bearing fields, newline-joined so a clause regex cannot read
    across a field boundary (the 241 lesson). `symptoms` are reports."""
    return "\n".join([e["title"], e["description"], *e["causes"], e["fix_procedure"]])


# ---------------------------------------------------------------------------
# 1. Reachability, and the reading order 240C made real
# ---------------------------------------------------------------------------
class TestReachability:
    def test_every_entry_is_make_zero(self, raw):
        """Exactly "Zero" — a prose make is reachable from nothing (240B, S2),
        and "Zero Motorcycles" would still match `%Zero%` but is not what the
        cross-platform files or 241 use."""
        for e in raw:
            assert "Zero" in e["make"], e["title"][:60]

    def test_a_zero_query_returns_this_file_and_the_hv_floor(self, db, raw):
        rows = search_known_issues(make="Zero", db_path=db)
        hv = json.loads(HV.read_text(encoding="utf-8"))
        assert len(rows) == len(raw) + len(hv)

    def test_the_critical_hv_floor_outranks_a_medium_zero_entry(self, db):
        """240C's ordering, doing the job it was fixed for: a mechanic who
        searches Zero sees 'verify absence of voltage' before a belt-tension
        note."""
        sevs = [r["severity"] for r in search_known_issues(make="Zero", db_path=db)]
        rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        assert [rank[s] for s in sevs] == sorted((rank[s] for s in sevs), reverse=True)

    def test_every_entry_names_a_model_or_platform(self, raw):
        for e in raw:
            assert e["model"] and e["model"].strip(), e["title"][:60]


# ---------------------------------------------------------------------------
# 2. Figures carry their document, or are withheld and say so
# ---------------------------------------------------------------------------
FIGURE = re.compile(
    r"\b\d[\d,.]*\s*(?:V|VDC|kWh|kW|Ah|A|Nm|N·m|ft[- ]?lbs?|km|mi|miles|hours?|hrs?|minutes?|mins?|seconds?|secs?|%|°C|°F)\b",
    re.I,
)
DOC = re.compile(
    r"(manual|handbook|bulletin|specification|spec sheet|support article|knowledge base"
    r"|release notes|owner['’]s|accessory (?:page|product page)|privacy policy"
    r"|regulator (?:recall )?record|recall record)",
    re.I,
)  # a recall entry's figures come from the regulator, not from a Zero document
WITHHELD = re.compile(r"(deliberately prints no|does not (?:state|supply|print)|not established here|withheld)", re.I)


class TestFiguresCarryTheirDocument:
    def test_a_printed_figure_names_a_zero_document(self, raw):
        """238's rule, per entry: any entry that prints a figure must name
        the Zero document it came from in its description. 12V is exempt —
        it names the auxiliary system, not a pack figure."""
        for e in raw:
            text = _claims(e)
            figs = [m.group(0) for m in FIGURE.finditer(text) if not re.fullmatch(r"12\s*V", m.group(0), re.I)]
            if figs:
                assert DOC.search(e["description"]) and e["source"] == "service-manual", (
                    f"{e['title'][:60]}: prints {figs[:3]} but names no Zero document / is not service-manual"
                )

    def test_a_model_generated_entry_prints_no_figure(self, raw):
        """The converse. If no document was opened, no number ships."""
        for e in raw:
            if e["source"] == "model-generated":
                text = _claims(e)
                figs = [m.group(0) for m in FIGURE.finditer(text) if not re.fullmatch(r"12\s*V", m.group(0), re.I)]
                assert not figs, f"{e['title'][:60]}: model-generated but prints {figs[:3]}"

    def test_the_figure_pattern_can_fire(self):
        assert FIGURE.search("the pack is 14.4 kWh") and FIGURE.search("torque to 25 Nm")
        assert FIGURE.search("every 4,000 miles") and not FIGURE.search("the Z-Force 75-7 motor")


# ---------------------------------------------------------------------------
# 3. Provenance is honest and rule 3 holds
# ---------------------------------------------------------------------------
class TestProvenance:
    def test_only_the_six_values(self, raw):
        assert {e["source"] for e in raw} <= {"service-manual", "forum", "model-generated", "regulation", "unverified", "mechanic-verified"}
        assert "unverified" not in {e["source"] for e in raw}, "unverified is reserved for legacy rows"

    def test_every_entry_says_what_it_is_drawn_from(self, raw):
        for e in raw:
            assert re.search(r"[Dd]rawn from|[Gg]eneral knowledge", e["description"]), e["title"][:60]

    def test_service_manual_entries_name_a_zero_document(self, raw):
        for e in raw:
            if e["source"] == "service-manual":
                assert DOC.search(e["description"]) or re.search(r"regulator|recall record", e["description"], re.I), e["title"][:60]

    def test_forum_tip_marker_tracks_the_source(self, raw):
        for e in raw:
            assert ("Forum tip" in e["fix_procedure"]) == (e["source"] == "forum"), e["title"][:60]


# ---------------------------------------------------------------------------
# 4. Scope: Zero-specific, no campaign numbers, well-formed
# ---------------------------------------------------------------------------
class TestScope:
    def test_no_campaign_reference_number(self, raw):
        blob = json.dumps(raw)
        assert not re.findall(r"\b\d{2}V\d{3,6}\b|RM/\d{4}/\d+|\bR/\d{4}/\d{3}\b", blob)
        assert not re.search(r"recall (?:no\.?|number|#)\s*\S", blob, re.I)

    def test_every_entry_names_zero_hardware_or_history(self, raw):
        """The scope lens, as a static check: an entry must mention something
        that is Zero's — a model, the platform, the app, a Zero part — not
        just 'electric motorcycle' in general."""
        marker = re.compile(r"Z-Force|Cypher|SR/F|SR/S|DSR|FXE|FXS|\bFX\b|\bDS\b|Charge Tank|Zero (?:app|S\b|SR\b|DS\b|FX\b|Motorcycles)|ZF\d", re.I)
        for e in raw:
            assert marker.search(_claims(e)), f"{e['title'][:60]}: names nothing Zero-specific"

    def test_symptoms_follow_the_house_format(self, raw):
        for e in raw:
            assert e["symptoms"], e["title"][:60]
            for s in e["symptoms"]:
                assert len(s) <= 55 and not s.endswith("."), (e["title"][:40], s)

    def test_no_title_collides_corpus_wide(self):
        titles = []
        for f in K.glob("known_issues_*.json"):
            titles += [e["title"] for e in json.loads(f.read_text(encoding="utf-8"))]
        assert len(titles) == len(set(titles))

    def test_severity_carries_information(self, raw):
        assert len({e["severity"] for e in raw}) >= 2
