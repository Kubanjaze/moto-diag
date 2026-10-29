"""Phase 393 — bug fixes #1 and #2.

#1, the PDF escape. `reporting/renderers.py` defined `_escape` for
reportlab's markup, then rebound the name with `from html import escape as
_escape` for the HTML renderer, so every PDF went through `html.escape`.
Measured at Step 0 (S0-7): reportlab renders `&quot;` and `&#x27;`, so
today's PDFs read right; the defect was the wrong function. These tests
read the text back out of a real PDF, and prove which function the PDF
renderer calls.

#2, the erase. `memory/erase.py`'s three handlers, written for "table
absent", caught every exception. An error at the guidance table during a
customer's erase was swallowed, and the erase reported success with the
customer's questions still there. Now only "no such table" is dropped. The
planted error is the one SQLite raises when another connection holds a
table's lock; the control (the tables really absent) must still erase.
"""
from __future__ import annotations

import contextlib
import html
import io
import sqlite3

import pytest

from motodiag.capture.guidance_log import list_interactions, record_guidance_interaction
from motodiag.core.database import get_connection, init_db
from motodiag.media.vision_types import GuidanceCandidate, GuidanceResponse, Grounding
from motodiag.memory import attach_vehicle, erase_customer, erase_plan
from motodiag.memory import erase as erase_mod
from motodiag.memory.facts import MemoryFact, insert_facts
from motodiag.reporting import renderers

pypdf = pytest.importorskip("pypdf")

TRICKY = 'She said "hi" & it\'s <ok> > fine'


# ------------------------------------------------------- #1, the PDF escape
def _pdf_text(doc: dict) -> str:
    body = renderers.PdfReportRenderer().render(doc)
    return "\n".join(p.extract_text() for p in pypdf.PdfReader(io.BytesIO(body)).pages)


class TestThePdfEscape:
    def test_the_five_characters_come_out_of_the_pdf_as_written(self):
        text = _pdf_text({"title": TRICKY, "subtitle": TRICKY, "sections": [
            {"heading": TRICKY, "body": TRICKY, "bullets": [TRICKY]}], "footer": TRICKY})
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        assert lines.count(TRICKY) == 5, text
        for entity in ("&quot;", "&#x27;", "&amp;", "&lt;", "&gt;"):
            assert entity not in text, f"{entity} reached the page"

    def test_the_pdf_renderer_calls_the_markup_escape(self, monkeypatch):
        seen = []
        real = renderers._markup_escape

        def spy(value):
            seen.append(value)
            return real(value)

        monkeypatch.setattr(renderers, "_markup_escape", spy)
        renderers.PdfReportRenderer().render({"title": TRICKY, "sections": []})
        assert TRICKY in seen, "the PDF renderer did not escape its title with _markup_escape"

    def test_the_markup_escape_escapes_markup_and_leaves_quotes(self):
        assert renderers._markup_escape(TRICKY) == (
            'She said "hi" &amp; it\'s &lt;ok&gt; &gt; fine')

    def test_the_html_renderer_still_escapes_quotes(self):
        assert renderers._e('"\'<') == "&quot;&#x27;&lt;"

    def test_one_name_one_function(self):
        """The defect was one name bound twice in one module."""
        assert renderers._markup_escape is not html.escape
        assert renderers._html_escape is html.escape
        assert not hasattr(renderers, "_escape")


# ------------------------------------------------------------- #2, the erase
VEHICLE, CUSTOMER = 10, 2


@pytest.fixture
def db(tmp_path):
    """One real customer, one machine of theirs, one compiled fact."""
    path = str(tmp_path / "erase.db")
    init_db(path)
    c = sqlite3.connect(path)
    c.execute("INSERT INTO vehicles (id, make, model, year, customer_id) "
              "VALUES (?, 'Honda', 'CBR600F4i', 2001, 1)", (VEHICLE,))
    c.execute("INSERT INTO customers (id, name) VALUES (?, 'Dana Reyes')", (CUSTOMER,))
    c.commit()
    c.close()
    attach_vehicle(VEHICLE, CUSTOMER, db_path=path)
    assert insert_facts([MemoryFact(vehicle_id=VEHICLE, fact_kind="repair", subject="clutch",
                                    source="service-record", origin_table="work_orders",
                                    established_at="2026-01-01")], db_path=path) == 1
    return path


def _guidance(db: str) -> None:
    record_guidance_interaction("Where is the oil coming from?", GuidanceResponse(
        question_understood_as="Where is the oil coming from?", answers_the_question=True,
        candidates=[GuidanceCandidate(candidate="Clutch cover gasket",
                                      why_plausible="Wet film below the cover",
                                      how_to_discriminate="Clean and run",
                                      grounding=Grounding.MACHINE_SPECIFIC)],
        what_would_narrow_it=["Clean the area and re-run"], not_established="",
        observation_basis="Frames 4-9"), vehicle_id=VEHICLE, db_path=db)


def _facts(db: str) -> int:
    with get_connection(db) as conn:
        return conn.execute("SELECT COUNT(*) FROM memory_facts").fetchone()[0]


class _Locked:
    """The real connection, except that the statement naming `table` and
    starting with `verb` raises what SQLite raises when another connection
    holds that table's lock."""

    def __init__(self, conn: sqlite3.Connection, table: str, verb: str):
        self._conn, self._table, self._verb = conn, table, verb

    def execute(self, sql: str, *args):
        if self._table in sql and sql.lstrip().upper().startswith(self._verb):
            raise sqlite3.OperationalError(f"database table is locked: {self._table}")
        return self._conn.execute(sql, *args)

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _plant(monkeypatch, table: str, verb: str) -> None:
    real = erase_mod.get_connection

    @contextlib.contextmanager
    def locked(db_path=None):
        with real(db_path) as conn:
            yield _Locked(conn, table, verb)

    monkeypatch.setattr(erase_mod, "get_connection", locked)


#: The three handled statements: the table, the statement's verb, which one.
HANDLED = [
    ("customer_bikes", "SELECT", "the read of the ownership junction"),
    ("guidance_interactions", "SELECT", "erase_plan's count of guidance questions"),
    ("guidance_interactions", "DELETE", "erase_customer's delete of guidance questions"),
]


class TestTheEraseRefusesOnAnErrorItWasNotWrittenFor:
    @pytest.mark.parametrize("table, verb, which", HANDLED, ids=[h[2] for h in HANDLED])
    def test_a_locked_table_makes_the_erase_raise_and_leaves_everything(
            self, db, monkeypatch, table, verb, which):
        _guidance(db)
        _plant(monkeypatch, table, verb)
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            erase_customer(CUSTOMER, db_path=db)
        monkeypatch.undo()
        assert _facts(db) == 1, "the erase raised, so nothing may be gone"
        assert len(list_interactions(vehicle_id=VEHICLE, db_path=db)) == 1

    @pytest.mark.parametrize("table, verb, which", HANDLED[:2], ids=[h[2] for h in HANDLED[:2]])
    def test_the_dry_run_refuses_too(self, db, monkeypatch, table, verb, which):
        _plant(monkeypatch, table, verb)
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            erase_plan(CUSTOMER, db_path=db)


class TestTheControlTablesAbsentStillErase:
    """The exclusion's control: "no such table" is still what the handlers
    drop, so an install without the two tables erases its memory facts."""

    def test_without_customer_bikes_or_guidance_interactions(self, db):
        with get_connection(db) as conn:
            conn.execute("PRAGMA foreign_keys=OFF")
            conn.execute("DROP TABLE guidance_interactions")
            conn.execute("DROP TABLE customer_bikes")
        assert erase_plan(CUSTOMER, db_path=db).fact_count == 1
        assert erase_customer(CUSTOMER, db_path=db) == 1
        assert _facts(db) == 0

    def test_with_both_tables_the_erase_deletes_both(self, db):
        _guidance(db)
        assert erase_customer(CUSTOMER, db_path=db) == 2
        assert _facts(db) == 0 and list_interactions(vehicle_id=VEHICLE, db_path=db) == []
