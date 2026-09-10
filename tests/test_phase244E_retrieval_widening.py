"""Phase 244E — resolving a model must not shrink the answer.

Phase 244D's re-seed exposed a Phase 244C bug: `BMW + "R1200GS"` returned 1 row
where `BMW` with no model returned 50. Succeeding at identification made the
answer fifty times worse.

The cause is in the data. 30% of the corpus — effectively all of Tracks K and L
— carries prose in the `model` column ("Liquid-cooled R-series boxers, R1200GS
and all LC R models from 2013"), and none of those makes has a `model = 'All'`
row to fall back on, so an equality filter reaches almost nothing.

The fix is stated as a property, not patched for one example: **knowing more
must never return less.**
"""

import contextlib
import inspect
import sqlite3

import pytest

from motodiag.knowledge import vehicle_resolver as vr
from motodiag.media.vision_analysis_pipeline import _format_known_issues
from support.source_guards import code_of


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    """Models both populations the real corpus turned out to contain: makes with
    clean model names and an `All` fallback, and makes whose `model` column
    holds prose with no fallback at all."""
    p = tmp_path / "kb.db"
    conn = sqlite3.connect(p)
    conn.execute("""CREATE TABLE known_issues (id INTEGER PRIMARY KEY, make TEXT,
                    model TEXT, title TEXT, description TEXT, severity TEXT)""")
    rows = [
        # clean-model population, with a wildcard fallback
        ("Honda", "CBR600F4i", "Injector fouling", "d", "high"),
        ("Honda", "CBR600F4i", "Float bowl seep", "d", "low"),
        ("Honda", "All", "Cam chain tensioner", "d", "critical"),
        ("Honda", "CBR600RR", "Regulator rectifier", "d", "high"),
        ("Honda", "CB750", "Carb sync", "d", "medium"),
        # prose-model population, no fallback — the Track K shape
        ("BMW", "R1200GS", "Final drive bearing", "d", "critical"),
        ("BMW", "Liquid-cooled R-series boxers, R1200GS and all LC R models from 2013",
         "ELAST belt", "d", "high"),
        ("BMW", "Oilhead R1100/R1150 and R1200 hexhead and camhead boxers",
         "Alternator belt", "d", "medium"),
        ("BMW", "R-series (Paralever)", "Driveshaft splines", "d", "high"),
        # a different make entirely
        ("Kawasaki", "ZX-10R", "Cam chain guide", "d", "high"),
        ("Kawasaki", "All", "Fork seal", "d", "low"),
    ]
    conn.executemany(
        "INSERT INTO known_issues (make, model, title, description, severity) VALUES (?,?,?,?,?)", rows)
    conn.commit(); conn.close()

    @contextlib.contextmanager
    def _conn(path=None):
        c = sqlite3.connect(p); c.row_factory = sqlite3.Row
        try: yield c
        finally: c.close()

    monkeypatch.setattr(vr, "get_connection", _conn)
    return str(p)


class TestKnowingMoreNeverReturnsLess:
    """The invariant the phase exists to establish."""

    def test_the_reported_case_is_fixed(self, corpus):
        _, with_model = vr.known_issues_for_vehicle("BMW", "R1200GS", db_path=corpus, limit=50)
        _, without = vr.known_issues_for_vehicle("BMW", "", db_path=corpus, limit=50)
        assert len(with_model) >= len(without), (
            f"resolving the model shrank the answer: {len(with_model)} < {len(without)}")

    def test_it_holds_for_every_make_and_model_in_the_corpus(self, corpus):
        """Asserted as a property across the whole corpus, because the original
        bug was invisible for Honda and fatal for BMW — one example proves
        nothing here."""
        makes = vr.known_makes(corpus)
        checked = 0
        for make in makes:
            _, baseline = vr.known_issues_for_vehicle(make, "", db_path=corpus, limit=100)
            for model in vr.known_models(make, corpus):
                _, narrowed = vr.known_issues_for_vehicle(make, model, db_path=corpus, limit=100)
                assert len(narrowed) >= len(baseline), (
                    f"{make} + {model!r}: {len(narrowed)} rows vs {len(baseline)} with no model")
                checked += 1
        assert checked > 0, "the property was never exercised"

    def test_a_prose_model_make_is_not_starved(self, corpus):
        """BMW's model column is prose with no `All` row — the shape that broke."""
        _, rows = vr.known_issues_for_vehicle("BMW", "R1200GS", db_path=corpus, limit=50)
        assert len(rows) == 4, f"expected every BMW row, got {len(rows)}"


class TestSpecificityIsRankedNotFiltered:
    def test_the_exact_model_ranks_first(self, corpus):
        _, rows = vr.known_issues_for_vehicle("BMW", "R1200GS", db_path=corpus, limit=50)
        assert rows[0]["match_tier"] == "model"
        assert rows[0]["title"] == "Final drive bearing"

    def test_tiers_are_ordered_most_specific_first(self, corpus):
        _, rows = vr.known_issues_for_vehicle("Honda", "CBR600F4i", db_path=corpus, limit=50)
        order = {"model": 0, "make_wide": 1, "make_other_model": 2}
        seq = [order[r["match_tier"]] for r in rows]
        assert seq == sorted(seq), f"tiers out of order: {[r['match_tier'] for r in rows]}"

    def test_every_row_carries_a_tier(self, corpus):
        _, rows = vr.known_issues_for_vehicle("Honda", "CBR600F4i", db_path=corpus, limit=50)
        assert all(r.get("match_tier") in {"model", "make_wide", "make_other_model"} for r in rows)

    def test_severity_orders_within_a_tier_via_the_ssot(self, corpus):
        """Reuses Phase 240C's SEVERITY_RANK_SQL so the expression index serves
        the ordering and the constant is not written twice."""
        src = code_of(vr.known_issues_for_vehicle)
        assert "SEVERITY_RANK_SQL" in src
        assert "CASE severity WHEN" not in src, "severity rank inlined instead of imported"
        _, rows = vr.known_issues_for_vehicle("BMW", "", db_path=corpus, limit=50)
        sev = [r["severity"] for r in rows]
        rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        assert [rank[s] for s in sev] == sorted([rank[s] for s in sev], reverse=True)


class TestTheMakeBoundaryIsAbsolute:
    """Duplicated from Phase 244C on purpose. Widening relaxed the same-make
    half of a bundled guard; splitting a guard is how its strict half goes
    missing, so this assertion now lives in two files."""

    def test_another_makes_rows_never_appear(self, corpus):
        for make, model in [("Honda", "CBR600F4i"), ("Honda", ""), ("BMW", "R1200GS"), ("BMW", "")]:
            _, rows = vr.known_issues_for_vehicle(make, model, db_path=corpus, limit=100)
            assert {r["make"] for r in rows} <= {make}, (
                f"{make} query returned rows from {{r['make'] for r in rows}}")

    def test_a_kawasaki_issue_never_reaches_a_honda(self, corpus):
        _, rows = vr.known_issues_for_vehicle("Honda", "CBR600F4i", db_path=corpus, limit=100)
        assert "Cam chain guide" not in {r["title"] for r in rows}

    def test_widening_never_crosses_a_make_even_when_starved(self, corpus):
        """A make with few rows must come back short rather than borrow."""
        _, rows = vr.known_issues_for_vehicle("Kawasaki", "ZX-10R", db_path=corpus, limit=100)
        assert {r["make"] for r in rows} == {"Kawasaki"}
        assert len(rows) == 2


class TestNearNeighboursAreLabelledNotLaundered:
    def test_the_formatter_marks_another_models_entry(self):
        out = _format_known_issues([
            {"title": "Injector fouling", "description": "d", "model": "CBR600F4i", "match_tier": "model"},
            {"title": "Regulator rectifier", "description": "d", "model": "CBR600RR", "match_tier": "make_other_model"},
        ])
        assert "[this model] Injector fouling" in out
        assert "SAME MAKE, DIFFERENT MODEL" in out
        assert "not established for this machine" in out

    def test_the_other_model_is_named(self):
        """A technician must be able to see WHICH machine the evidence is from."""
        out = _format_known_issues([
            {"title": "Regulator rectifier", "description": "d", "model": "CBR600RR", "match_tier": "make_other_model"},
        ])
        assert "CBR600RR" in out

    def test_an_untagged_row_is_treated_as_the_least_specific(self):
        """Fail safe: a row arriving without a tier must not be presented as
        machine-specific."""
        out = _format_known_issues([{"title": "T", "description": "d", "model": "X"}])
        assert "SAME MAKE, DIFFERENT MODEL" in out

    def test_the_prompt_explains_what_the_tag_means(self):
        from motodiag.media.vision_types import GUIDANCE_PROMPT
        assert "SAME MAKE, DIFFERENT MODEL" in GUIDANCE_PROMPT
        assert "cross_platform at best" in GUIDANCE_PROMPT


class TestABrokenQueryIsNotAnEmptyCorpus:
    """Phase 240C shipped this defect in `advanced/recall_repo.py` — a dropped
    ORDER BY keyword swallowed by a blanket except, so a lookup returned empty
    instead of raising. This phase reproduced it with a new ORDER BY against a
    fixture missing the column."""

    def test_a_malformed_query_raises_rather_than_returning_empty(self, tmp_path, monkeypatch):
        p = tmp_path / "bad.db"
        c = sqlite3.connect(p)
        c.execute("CREATE TABLE known_issues (id INTEGER PRIMARY KEY, make TEXT, model TEXT, title TEXT)")
        c.execute("INSERT INTO known_issues (make, model, title) VALUES ('Honda','CBR','T')")
        c.commit(); c.close()

        @contextlib.contextmanager
        def _conn(path=None):
            cc = sqlite3.connect(p); cc.row_factory = sqlite3.Row
            try: yield cc
            finally: cc.close()

        monkeypatch.setattr(vr, "get_connection", _conn)
        with pytest.raises(sqlite3.OperationalError):
            vr.known_issues_for_vehicle("Honda", "CBR", db_path=str(p))

    def test_a_missing_table_is_still_an_empty_corpus(self, tmp_path, monkeypatch):
        """Best-effort survives for the case that genuinely means 'nothing here'."""
        p = tmp_path / "empty.db"
        sqlite3.connect(p).close()

        @contextlib.contextmanager
        def _conn(path=None):
            cc = sqlite3.connect(p); cc.row_factory = sqlite3.Row
            try: yield cc
            finally: cc.close()

        monkeypatch.setattr(vr, "get_connection", _conn)
        identity, rows = vr.known_issues_for_vehicle("Honda", "CBR", db_path=str(p))
        assert rows == []
