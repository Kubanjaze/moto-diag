"""Phase 244 — Energica (Ego, Eva/EsseEsse9, Experia).

Written BEFORE the research returned, from the invariants plan v1.0 committed
to. Content-shaped assertions are added afterwards.

This phase opened around two NAMED DOUBTS — unsourced claims about Energica
already shipping in source code. The guards for those are written so they hold
whichever way the research resolves: a claim must be either sourced or gone,
never left standing unattributed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from motodiag.core.database import init_db
from motodiag.knowledge.issues_repo import search_known_issues
from motodiag.knowledge.loader import load_known_issues_file

ROOT = Path(__file__).resolve().parents[1]
K = ROOT / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"
ENERGICA = K / "known_issues_energica.json"
HV = K / "known_issues_electric_hv_safety.json"
FAULT_CODES = ROOT / "src" / "motodiag" / "engine" / "fault_codes.py"
SOUND_SIG = ROOT / "src" / "motodiag" / "media" / "sound_signatures.py"

RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}


@pytest.fixture(scope="module")
def raw():
    return json.loads(ENERGICA.read_text(encoding="utf-8"))


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "en.db")
    init_db(path)
    load_known_issues_file(HV, path)
    load_known_issues_file(ENERGICA, path)
    return path


def _claims(e) -> str:
    """Assertion-bearing fields, newline-joined so a clause regex cannot read
    across a field boundary (the Phase 241 lesson)."""
    return "\n".join([e["title"], e["description"], *e["causes"], e["fix_procedure"]])


# ---------------------------------------------------------------------------
# 1. Reachability
# ---------------------------------------------------------------------------
class TestReachability:
    def test_every_entry_is_make_energica(self, raw):
        for e in raw:
            assert "Energica" in e["make"], e["title"][:60]

    def test_a_query_returns_this_file_and_the_hv_floor(self, db, raw):
        rows = search_known_issues(make="Energica", db_path=db)
        hv = json.loads(HV.read_text(encoding="utf-8"))
        assert len(rows) == len(raw) + len(hv)

    def test_critical_entries_come_first(self, db):
        sevs = [r["severity"] for r in search_known_issues(make="Energica", db_path=db)]
        assert [RANK[s] for s in sevs] == sorted((RANK[s] for s in sevs), reverse=True), sevs


# ---------------------------------------------------------------------------
# 2. Figures carry their document, per source class
# ---------------------------------------------------------------------------
FIGURE = re.compile(
    r"\b\d[\d,.]*\s*(?:V|VDC|kWh|kW|Ah|A|Nm|N·m|ft[- ]?lbs?|qt|L|km|mi|miles|hours?|hrs?"
    r"|minutes?|mins?|Hz|rpm|%|°C|°F|pole pairs?|poles)\b",
    re.I,
)
DOC = re.compile(
    r"(manual|handbook|bulletin|specification|spec sheet|spec table|model page"
    r"|diagnosis (?:sheet|information)|technology page|support|FAQ|press release"
    r"|release notes|owner['’]s|regulator|recall record|complaint database|forum|owners report)",
    re.I,
)  # a manufacturer spec table and a per-model page are documents too — Phase 244


class TestFiguresCarryTheirDocument:
    def test_any_entry_printing_a_figure_names_its_source(self, raw):
        for e in raw:
            figs = [m.group(0) for m in FIGURE.finditer(_claims(e))
                    if not re.fullmatch(r"12\s*(?:volt|V)", m.group(0), re.I)]
            if figs:
                assert DOC.search(e["description"]), (
                    f"{e['title'][:60]}: prints {figs[:3]} but names no source"
                )

    PRICE = re.compile(
        r"(?:[$\u00a3\u20ac]\s?\d|\b(?:USD|EUR|GBP|CHF)\s?\d|\d[\d,.]*\s?(?:dollars|euros|pounds)\b)",
        re.I,
    )

    def test_no_entry_prints_a_price(self, raw):
        """Phase 244 caught this guard vacuous: it matched only currency
        SYMBOLS, and the figures the research actually withheld were written
        "USD 500" and "USD 2,500" — a currency CODE, which sailed straight
        through. Owner-quoted costs from a company that has since changed hands
        are not prices, and a mechanic acts on a price."""
        for e in raw:
            m = self.PRICE.search(_claims(e))
            assert not m, f"{e['title'][:60]}: prints a price {m.group(0)!r}"

    def test_the_price_guard_can_fire(self):
        for s in ("$2,500", "USD 2,500", "EUR 500", "\u00a31,200", "500 dollars"):
            assert self.PRICE.search(s), s
        assert not self.PRICE.search("1200 cycles at 80 percent capacity")

    def test_no_pole_count_is_stated_for_energica(self, raw):
        """GAP 2, caught by mutation: the figure guard above only asks whether
        SOME document is named, so a pole count injected into an entry that
        already cites a manual inherits that entry's provenance and passes.

        This phase's whole finding is that no Energica pole count exists in any
        source. So the corpus must not state one — asserted directly rather
        than inferred from the presence of a citation."""
        for e in raw:
            m = re.search(r"\b\d+\s*pole[- ]?pairs?\b|\b\d+\s*poles\b", _claims(e), re.I)
            assert not m, (
                f"{e['title'][:60]}: states a pole count {m.group(0)!r} — no Energica "
                "source establishes one (Phase 244)"
            )

    def test_the_figure_pattern_can_fire(self):
        assert FIGURE.search("21.5 kWh") and FIGURE.search("8 pole pairs")
        assert not FIGURE.search("the Ego model")


# ---------------------------------------------------------------------------
# 3. Provenance, scope, shape
# ---------------------------------------------------------------------------
class TestProvenanceAndScope:
    def test_sources_are_honest(self, raw):
        assert {e["source"] for e in raw} <= {"service-manual", "forum", "model-generated"}
        assert "unverified" not in {e["source"] for e in raw}

    def test_every_entry_says_what_it_is_drawn_from(self, raw):
        for e in raw:
            assert re.search(r"[Dd]rawn from|[Gg]eneral knowledge|[Oo]wners report", e["description"]), e["title"][:60]

    def test_forum_tip_marker_tracks_the_source(self, raw):
        for e in raw:
            assert ("Forum tip" in e["fix_procedure"]) == (e["source"] == "forum"), e["title"][:60]

    def test_no_campaign_reference_number(self, raw):
        blob = json.dumps(raw)
        assert not re.findall(r"\b\d{2}V\d{3,6}\b|RM/\d{4}/\d+|\bR/\d{4}/\d{3}\b", blob)
        assert not re.search(r"recall (?:no\.?|number|#)\s*\S", blob, re.I)

    def test_every_entry_is_energica_specific(self, raw):
        marker = re.compile(r"Energica|\bEgo\b|\bEva\b|EsseEsse|Experia", re.I)
        for e in raw:
            assert marker.search(_claims(e)), f"{e['title'][:60]}: nothing Energica-specific"

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


# ---------------------------------------------------------------------------
# 4. The two named doubts — resolved either way, never left unsourced
# ---------------------------------------------------------------------------
class TestDoubtA_TheFaultCodeAttribution:
    """`fault_codes.py` recognises ^(HV|MC|BMS|INV|CHG|REG)_ and commented it as
    "Zero/LiveWire/Energica HV battery/motor DTCs". Zero of the 99 seeded DTC
    codes use that format; its only occurrences are Phase 111 test fixtures.

    Phase 242 established Zero publishes a numbered owner's-manual table;
    Phase 243 established LiveWire's codes need Digital Technician II. Neither
    uses an HV_ prefix. So the attribution is wrong for at least two of the
    three makes it names, whatever the research finds for Energica.

    These guards hold either way: the namespace may stay (it is a defensible
    internal convention) but it may not claim manufacturers use it without
    saying what that claim rests on."""

    def test_the_matcher_itself_still_works(self):
        """The regex is exercised by Phase 111 and must keep working — only the
        attribution is in question, never the matcher."""
        from motodiag.engine.fault_codes import CodeFormat, classify_code

        fmt, _desc = classify_code("HV_B001")
        assert fmt == CodeFormat.ELECTRIC_HV

    def test_no_bare_manufacturer_attribution_remains(self):
        """The comment must not assert, unqualified, that these makes use this
        format.

        MENTION VERSUS USE. The correction itself QUOTES the old wrong
        attribution in order to refute it, and a naive line-by-line check flags
        the quotation as though it were the claim — this guard did exactly that
        on its first widening. Comment lines are therefore joined into blocks
        and each occurrence is judged on what PRECEDES it: an attribution
        introduced by "previously read", "was wrong" or similar is being cited,
        not made."""
        text = FAULT_CODES.read_text(encoding="utf-8")
        lines = text.splitlines()

        blocks, cur = [], []
        for ln in lines:
            s = ln.strip()
            if s.startswith("#"):
                cur.append(s.lstrip("#").strip())
            else:
                if cur:
                    blocks.append(" ".join(cur))
                cur = []
        if cur:
            blocks.append(" ".join(cur))

        attribution = re.compile(
            r"(?:used by|for)\s+[^.]{0,60}?(?:Zero|LiveWire|Energica)[^.]{0,80}?"
            r"(?:HV|BMS|DTC|fault code)",
            re.I,
        )
        cited = re.compile(
            r"previously read|used to read|was wrong|incorrectly|before this|"
            r"the error|origin of the error|misattribut",
            re.I,
        )
        for block in blocks:
            for m in attribution.finditer(block):
                preceding = block[:m.start()]
                assert cited.search(preceding), (
                    "fault_codes.py makes an unqualified manufacturer attribution for the "
                    f"HV_ format:\n    ...{block[max(0, m.start() - 60):m.end() + 60]}..."
                )

    def test_the_attribution_guard_can_fire(self):
        """Anti-vacuity, both directions: a bare attribution must trip it, and
        the same words introduced as a quotation must not."""
        attribution = re.compile(
            r"(?:used by|for)\s+[^.]{0,60}?(?:Zero|LiveWire|Energica)[^.]{0,80}?"
            r"(?:HV|BMS|DTC|fault code)",
            re.I,
        )
        bare = "Used by Zero, LiveWire, Energica for HV battery faults"
        quoted = 'This comment previously read "Used by Zero, LiveWire, Energica for HV battery faults"'
        assert attribution.search(bare)
        m = attribution.search(quoted)
        assert m and re.search(r"previously read", quoted[:m.start()], re.I)

    def test_the_correction_is_actually_present(self):
        """A positive assertion, so the guard cannot be satisfied by deleting
        the comment altogether."""
        text = FAULT_CODES.read_text(encoding="utf-8")
        assert re.search(r"Phase 244", text)
        assert re.search(r"internal", text, re.I)
        for make in ("Zero", "LiveWire", "Energica"):
            assert make in text, f"{make}'s actual code format is no longer recorded"


class TestDoubtB_TheMotorSpecification:
    """`sound_signatures.py` asserted "Energica uses an oil-cooled PMSM (8 pole
    pairs)" inside a signature instructing a technician to compute motor whine
    fundamental as motor_RPM x pole_pairs / 60. Nothing consumes the figure,
    but it is written as fact and tells a human to compute with it.

    The guard holds either way: a pole-pair count may stay only if it carries
    an attribution; otherwise it must be gone."""

    POLE = re.compile(r"(\d+)\s*pole\s*pairs?", re.I)

    def test_any_surviving_pole_pair_figure_is_attributed(self):
        text = SOUND_SIG.read_text(encoding="utf-8")
        for m in self.POLE.finditer(text):
            # Phase 244: a +/-400 character window was too generous. The
            # rewritten docstring is full of attribution words, so a figure
            # dropped anywhere inside it inherited them and the guard passed on
            # a mutation it should have caught. Attribution must be in the SAME
            # SENTENCE as the figure.
            start = max(text.rfind(".", 0, m.start()), text.rfind("\n", 0, m.start()))
            end = m.end() + 200
            for stop in (text.find(".", m.end()), text.find("\n", m.end())):
                if stop != -1:
                    end = min(end, stop)
            window = text[start + 1:end]
            attributed = re.search(
                r"manufacturer|manual|specification|datasheet|per Energica|per Zero"
                r"|owners report|not established|unsourced|withdrew|withdrawn|WITHDREW"
                r"|carried no source|typical|caller must",
                window, re.I,
            )
            assert attributed, (
                f"an unattributed pole-pair figure survives: {m.group(0)!r} — "
                "source it or withdraw it, do not leave it standing as fact"
            )

    def test_the_pole_pair_guard_can_fire(self):
        """Anti-vacuity: the pattern must match the shape it polices."""
        assert self.POLE.search("an oil-cooled PMSM (8 pole pairs)")
        assert self.POLE.search("4 pole pairs")
        assert not self.POLE.search("a permanent-magnet synchronous motor")
