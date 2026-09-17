"""Phase 244S — the retrieval fixes reach the commands people use.

Phases 244C–244I built typo tolerance, junction-table retrieval and specificity
tiering, and all of it reached exactly one route: the video-question endpoint.
`motodiag diagnose`, the product's primary command, still retrieved with
`make LIKE '%X%'`.

The worst of what that cost, measured on the real corpus: a bike entered as
**"Homda"** returned **0 rows**, `build_knowledge_context([])` returned `""`,
and the model diagnosed with no knowledge base at all while nothing on screen
said so. That is the failure Phase 244C exists to end, still shipping.

These tests go through `_load_known_issues` — the one function behind
`diagnose quick`, `diagnose start`, the `quick` alias and `motodiag code` — and
through the commands themselves.
"""

from __future__ import annotations

import json

import pytest

from motodiag.cli.diagnose import (
    KNOWN_ISSUE_PROMPT_LIMIT,
    _covers_year,
    _load_known_issues,
)
from motodiag.core.database import get_connection, init_db
from motodiag.engine.prompts import build_knowledge_context
from motodiag.knowledge.issues_repo import row_to_issue_dict, search_known_issues
from motodiag.knowledge.vehicle_resolver import known_issues_for_vehicle


def _issue(conn, *, make, model, title, symptoms, year_start=None, year_end=None,
           severity="medium"):
    return conn.execute(
        "INSERT INTO known_issues (make, model, title, description, symptoms, "
        "causes, severity, year_start, year_end, source) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'service-manual')",
        (make, model, title, f"{title} — description", json.dumps(symptoms),
         json.dumps(["a cause"]), severity, year_start, year_end),
    ).lastrowid


@pytest.fixture
def corpus(tmp_path):
    """A small corpus with the three shapes that matter: a model-specific row,
    a make-wide row, and a row about a different model of the same make."""
    db = str(tmp_path / "phase244S.db")
    init_db(db)
    with get_connection(db) as conn:
        _issue(conn, make="Honda", model="CBR600F4i", title="Stator failure",
               symptoms=["battery not charging"], year_start=2001, year_end=2006)
        _issue(conn, make="Honda", model="All", title="Regulator rectifier heat",
               symptoms=["dim lights"])
        _issue(conn, make="Honda", model="Gold Wing GL1800",
               title="Airbag inflator — as distinct from CBR models",
               symptoms=["airbag light"])
        _issue(conn, make="Honda", model="CBR600F4i", title="Old-model carb issue",
               symptoms=["hesitation"], year_start=1987, year_end=1990)
    _reindex(db)
    return db


def _reindex(db: str) -> None:
    """Both junctions. The resolver SELECTs through `known_issue_makes`, so a
    row missing from it is invisible however well the model index knows it —
    which is what made my first draft of the cap test return 3 rows."""
    from motodiag.knowledge.marques import rebuild_make_index_at
    from motodiag.knowledge.models import rebuild_model_index_at

    rebuild_make_index_at(db)
    rebuild_model_index_at(db)


# ---------------------------------------------------------------------------
# 1. One row shape, because two paths now feed one prompt builder
# ---------------------------------------------------------------------------


class TestBothPathsReturnTheSameShape:
    def test_the_like_path_decodes_its_list_columns(self, corpus):
        rows = search_known_issues(make="Honda", db_path=corpus)
        assert rows and isinstance(rows[0]["symptoms"], list)

    def test_the_resolver_path_does_too(self, corpus):
        """It returned bare rows until 244S, where `symptoms` was a JSON
        string — a caller iterating it would have walked characters."""
        _identity, rows = known_issues_for_vehicle("Honda", "CBR600F4i", db_path=corpus)
        assert rows and isinstance(rows[0]["symptoms"], list)

    def test_the_shapes_match_key_for_key(self, corpus):
        like = search_known_issues(make="Honda", model="CBR600F4i", db_path=corpus)
        _identity, resolved = known_issues_for_vehicle(
            "Honda", "CBR600F4i", db_path=corpus,
        )
        common = {"symptoms", "causes", "dtc_codes", "parts_needed"}
        for key in common:
            assert isinstance(like[0][key], list)
            assert isinstance(resolved[0][key], list)

    def test_the_helper_is_public_now(self):
        assert row_to_issue_dict.__doc__ and "244S" in row_to_issue_dict.__doc__


# ---------------------------------------------------------------------------
# 2. A typo no longer empties the corpus
# ---------------------------------------------------------------------------


class TestATypoNoLongerEmptiesTheCorpus:
    def test_the_old_path_returned_nothing(self, corpus):
        """The bug, pinned: this is what `diagnose` used to call."""
        assert search_known_issues(make="Homda", db_path=corpus) == []

    def test_the_command_path_now_finds_the_corpus(self, corpus):
        identity, rows = _load_known_issues("Homda", "CBR600F4i", 2003, db_path=corpus)
        assert rows, "a typo'd make must not silently empty the knowledge base"
        assert identity is not None

    def test_the_correction_is_reported(self, corpus):
        """Silent resolution fixes the prompt and leaves the garage wrong."""
        identity, _rows = _load_known_issues("Homda", "CBR600F4i", 2003, db_path=corpus)
        assert any("Homda" in c and "Honda" in c for c in identity.corrections())

    def test_an_empty_context_is_what_the_model_used_to_get(self):
        assert build_knowledge_context([]) == ""


# ---------------------------------------------------------------------------
# 3. Rows arrive tiered, and the prompt says which is which
# ---------------------------------------------------------------------------


class TestTheOtherModelEntry:
    def test_it_is_ranked_below_the_model_specific_rows(self, corpus):
        _identity, rows = _load_known_issues("Honda", "CBR600F4i", 2003, db_path=corpus)
        tiers = [r["match_tier"] for r in rows]
        assert tiers[0] == "model"
        assert tiers == sorted(
            tiers, key=lambda t: ["model", "make_wide", "make_other_model"].index(t)
        )

    def test_it_is_not_dropped_either(self, corpus):
        """244E's rule: knowing more must never return less. The Gold Wing row
        stays, ranked and labelled — it is not filtered out."""
        _identity, rows = _load_known_issues("Honda", "CBR600F4i", 2003, db_path=corpus)
        assert any("Airbag inflator" in r["title"] for r in rows)

    def test_the_prompt_says_a_different_model_is_a_different_model(self, corpus):
        _identity, rows = _load_known_issues("Honda", "CBR600F4i", 2003, db_path=corpus)
        context = build_knowledge_context(rows)
        assert "scope: this model" in context
        assert "same make, DIFFERENT model" in context

    def test_a_row_with_no_fix_procedure_does_not_crash_the_prompt(self):
        """`.get("fix_procedure", "")` returns None for a NULL column, and the
        builder called len() on it. No shipped row triggers this; the column is
        nullable, so one new entry would have."""
        context = build_knowledge_context([
            {"title": "No procedure yet", "severity": "low", "symptoms": ["x"],
             "causes": [], "fix_procedure": None},
        ])
        assert "No procedure yet" in context

    def test_a_row_without_a_tier_renders_as_before(self):
        context = build_knowledge_context([
            {"title": "Legacy", "severity": "low", "symptoms": [], "causes": []},
        ])
        assert "--- Issue 1: Legacy (severity: low) ---" in context


# ---------------------------------------------------------------------------
# 4. The year filter, and the cap
# ---------------------------------------------------------------------------


class TestTheYearFilterAndTheCap:
    def test_an_out_of_range_entry_is_excluded(self, corpus):
        _identity, rows = _load_known_issues("Honda", "CBR600F4i", 2003, db_path=corpus)
        assert not any("Old-model carb" in r["title"] for r in rows), (
            "the 1987-1990 entry does not describe a 2003 machine"
        )

    def test_the_same_entry_returns_for_a_year_it_covers(self, corpus):
        _identity, rows = _load_known_issues("Honda", "CBR600F4i", 1988, db_path=corpus)
        assert any("Old-model carb" in r["title"] for r in rows)

    def test_the_window_matches_the_repos_own(self):
        assert _covers_year({"year_start": 2001, "year_end": 2006}, 2003)
        assert not _covers_year({"year_start": 2001, "year_end": 2006}, 2007)
        assert not _covers_year({"year_start": 2001, "year_end": 2006}, 2000)
        assert _covers_year({"year_start": None, "year_end": None}, 2003)
        assert _covers_year({"year_start": 2001, "year_end": 2006}, None)

    def test_the_prompt_is_bounded(self, corpus):
        with get_connection(corpus) as conn:
            for i in range(40):
                _issue(conn, make="Honda", model="CBR600F4i",
                       title=f"Filler issue {i}", symptoms=["x"])
        _reindex(corpus)
        _identity, rows = _load_known_issues("Honda", "CBR600F4i", 2003, db_path=corpus)
        assert len(rows) == KNOWN_ISSUE_PROMPT_LIMIT

    def test_the_filter_runs_before_the_cap(self, corpus):
        """Filtering after the cap would let out-of-range rows consume the
        budget and starve the result."""
        with get_connection(corpus) as conn:
            for i in range(30):
                _issue(conn, make="Honda", model="CBR600F4i",
                       title=f"Ancient issue {i}", symptoms=["x"],
                       year_start=1980, year_end=1985)
        _reindex(corpus)
        _identity, rows = _load_known_issues("Honda", "CBR600F4i", 2003, db_path=corpus)
        assert rows, "the 2003-relevant rows must survive 30 irrelevant ones"
        assert not any("Ancient" in r["title"] for r in rows)


# ---------------------------------------------------------------------------
# 5. Failure stays quiet in the right way
# ---------------------------------------------------------------------------


class TestWhenRetrievalCannotAnswer:
    def test_an_unknown_make_returns_no_rows_and_an_identity(self, corpus):
        identity, rows = _load_known_issues(
            "Bugatti", "Veyron", 2010, db_path=corpus,
        )
        assert rows == []
        assert identity is not None, (
            "the caller needs to be able to say WHY it is empty"
        )

    def test_a_broken_database_does_not_take_down_the_command(self, tmp_path):
        """No rows and no exception. The identity may still come back — the
        resolver answers what it can about the name before it touches the
        corpus — and the caller renders nothing when there is nothing to
        correct."""
        identity, rows = _load_known_issues(
            "Honda", "CBR600F4i", 2003, db_path=str(tmp_path / "nope.db"),
        )
        assert rows == []
        assert identity is None or identity.corrections() == []
