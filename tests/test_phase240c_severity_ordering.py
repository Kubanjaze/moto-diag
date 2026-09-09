"""Phase 240C — severity must sort worst-first on every ordered query.

Six query paths ordered by ``severity DESC`` on a TEXT column. SQLite sorts
that lexicographically, and the four values alphabetise into almost exactly
the wrong order::

    ORDER BY severity DESC  ->  medium, low, high, critical

so ``critical`` came back LAST on all six. It survived for so long because the
output always looked plausibly sorted.

These guards assert the PROPERTY (a worse row precedes a less-bad one) rather
than pinning a row order, and they go through the repository functions the
product actually calls rather than re-implementing the SQL.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from motodiag.core.database import SCHEMA_VERSION, get_connection, init_db
from motodiag.core.severity import (
    SEVERITY_RANK,
    SEVERITY_RANK_SQL,
    severity_rank_sql,
)
from motodiag.knowledge.issues_repo import (
    find_issues_by_dtc,
    find_issues_by_symptom,
    search_known_issues,
)

SRC = Path(__file__).resolve().parents[1] / "src"
ORDER = ["critical", "high", "medium", "low"]


def _rank(row) -> int:
    return SEVERITY_RANK.get((row.get("severity") or "").lower(), 0)


def _is_sorted_worst_first(rows) -> bool:
    ranks = [_rank(r) for r in rows]
    return ranks == sorted(ranks, reverse=True)


@pytest.fixture
def db(tmp_path):
    """One row per severity, sharing a symptom and a DTC so all three
    knowledge paths return the whole set and the ordering is observable.

    Titles are chosen so that alphabetical order does NOT accidentally
    reproduce the correct order -- otherwise the guard could pass on the
    tiebreaker alone.
    """
    path = str(tmp_path / "sev.db")
    init_db(path)
    with get_connection(path) as c:
        for sev, title in zip(ORDER, ["D low-ish name", "C name", "B name", "A name"]):
            c.execute(
                "INSERT INTO known_issues (title, description, make, severity,"
                " symptoms, dtc_codes, fix_procedure) VALUES (?,?,?,?,?,?,?)",
                (title, "d", "TestMake", sev, "shared symptom", "P0999", "f"),
            )
        c.commit()
    return path


class TestTheKnowledgePaths:
    def test_search_known_issues_returns_worst_first(self, db):
        rows = search_known_issues(make="TestMake", db_path=db)
        assert [r["severity"] for r in rows] == ORDER, [r["severity"] for r in rows]

    def test_find_issues_by_symptom_returns_worst_first(self, db):
        rows = find_issues_by_symptom("shared symptom", db_path=db)
        assert _is_sorted_worst_first(rows), [r["severity"] for r in rows]
        assert rows[0]["severity"] == "critical"

    def test_find_issues_by_dtc_returns_worst_first(self, db):
        rows = find_issues_by_dtc("P0999", db_path=db)
        assert _is_sorted_worst_first(rows), [r["severity"] for r in rows]
        assert rows[0]["severity"] == "critical"

    def test_critical_outranks_medium_which_is_the_original_defect(self, db):
        """The exact inversion: lexicographic DESC put `medium` first."""
        rows = search_known_issues(make="TestMake", db_path=db)
        sevs = [r["severity"] for r in rows]
        assert sevs.index("critical") < sevs.index("medium")
        assert sevs.index("high") < sevs.index("medium")
        assert sevs.index("medium") < sevs.index("low")


class TestTheRecallPaths:
    """The recall sites carry the identical defect and the identical
    vocabulary. Phase 240B's audit named only the knowledge paths; the shape
    sweep found these. An open-recall list that puts the critical campaigns
    last is a safety surface."""

    @pytest.fixture
    def recall_db(self, tmp_path):
        path = str(tmp_path / "rec.db")
        init_db(path)
        with get_connection(path) as c:
            for i, sev in enumerate(ORDER):
                c.execute(
                    "INSERT INTO recalls (campaign_number, make, description,"
                    " severity) VALUES (?,?,?,?)",
                    (f"C{9 - i:03}", "TestMake", "d", sev),
                )
            c.commit()
        return path

    def test_advanced_open_recall_list_returns_worst_first(self, tmp_path):
        """The site this phase actually broke.

        The first version of the fix dropped the `ORDER BY` keyword while
        substituting the rank expression, leaving malformed SQL. It did not
        raise: `list_open_for_bike` wraps its query in
        `except sqlite3.OperationalError: return []` to degrade gracefully on
        a pre-migration database, so a syntax error became an empty result.
        Phase 155's own test caught it; this file had a gap, because it
        guarded the inventory lookup and not this one. Closed here."""
        from motodiag.advanced.recall_repo import list_open_for_bike

        path = str(tmp_path / "adv.db")
        init_db(path)
        with get_connection(path) as c:
            c.execute(
                "INSERT INTO vehicles (make, model, year, vin) VALUES (?,?,?,?)",
                ("TestMake", "TestModel", 2020, "VIN240C"),
            )
            vid = c.execute("SELECT id FROM vehicles ORDER BY id DESC LIMIT 1").fetchone()[0]
            for i, sev in enumerate(ORDER):
                c.execute(
                    "INSERT INTO recalls (campaign_number, make, model, year_start,"
                    " year_end, description, severity, open) VALUES (?,?,?,?,?,?,?,1)",
                    (f"A{9 - i:03}", "TestMake", "TestModel", 2019, 2021, "d", sev),
                )
            c.commit()

        rows = list_open_for_bike(vid, db_path=path)
        assert rows, "query returned nothing — malformed SQL is swallowed here"
        assert _is_sorted_worst_first(rows), [r["severity"] for r in rows]
        assert rows[0]["severity"] == "critical"

    def test_inventory_recall_lookup_returns_worst_first(self, recall_db):
        from motodiag.inventory.recall_repo import list_recalls_for_vehicle

        rows = list_recalls_for_vehicle(make="TestMake", db_path=recall_db)
        assert _is_sorted_worst_first(rows), [r["severity"] for r in rows]
        assert rows[0]["severity"] == "critical"


class TestTheCanonicalRank:
    def test_sql_is_built_from_the_dict(self):
        """Not two hand-written copies -- the SQL is derived, so they cannot
        drift."""
        for sev, rank in SEVERITY_RANK.items():
            assert f"WHEN '{sev}' THEN {rank}" in SEVERITY_RANK_SQL

    def test_unknown_and_null_severity_rank_below_low(self):
        assert "ELSE 0" in SEVERITY_RANK_SQL
        assert min(SEVERITY_RANK.values()) > 0

    def test_the_aliased_form_only_rewrites_the_column(self):
        aliased = severity_rank_sql("r.severity")
        assert aliased.startswith("CASE r.severity ")
        assert aliased.count("severity") == SEVERITY_RANK_SQL.count("severity")

    @pytest.mark.parametrize(
        "module,name",
        [
            ("motodiag.advanced.predictor", "SEVERITY_WEIGHT"),
            ("motodiag.advanced.tsb_repo", "_SEVERITY_ORDER"),
        ],
    )
    def test_the_existing_correct_copies_agree(self, module, name):
        """Phase 240C did not rewrite the five already-correct copies of this
        mapping -- touching working code inside a correctness fix is how
        regressions arrive. This asserts they agree with the canonical value
        instead, so they cannot drift while consolidation waits for its own
        phase."""
        import importlib

        other = getattr(importlib.import_module(module), name)
        for sev, rank in SEVERITY_RANK.items():
            assert other.get(sev) == rank, f"{module}.{name}[{sev}]"


class TestTheShapeGuard:
    """Phase 240B's audit named three sites; the defect had six. A name-keyed
    sweep has missed family members three times on this project, so this
    guard is keyed on the SHAPE -- any `ORDER BY ... severity` that is not
    routed through the canonical rank."""

    def test_no_lexicographic_severity_sort_remains(self):
        offenders = []
        for py in SRC.rglob("*.py"):
            if py.name == "severity.py":
                continue  # documents the defect in its own docstring
            if py.name == "migrations.py":
                # DDL history, not a live query path. Migration 049 built the
                # lexicographic index, 053 replaces it, and 053's rollback
                # must rebuild the old one -- that is what rollback means.
                # The live state is asserted by
                # TestTheIndexIsNotSilentlyLost instead, which checks the
                # PLAN rather than the text.
                continue
            for n, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"ORDER BY\s+[\w.]*severity\s+(DESC|ASC)", line, re.I):
                    offenders.append(f"{py.relative_to(SRC)}:{n}: {line.strip()}")
        assert not offenders, (
            "lexicographic severity sort reintroduced -- use "
            "motodiag.core.severity.SEVERITY_RANK_SQL:\n  " + "\n  ".join(offenders)
        )

    def test_the_guard_can_actually_fire(self):
        """Anti-vacuity: the pattern must match the shape it forbids."""
        assert re.search(
            r"ORDER BY\s+[\w.]*severity\s+(DESC|ASC)",
            "sql += ' ORDER BY severity DESC, title'",
            re.I,
        )
        assert re.search(
            r"ORDER BY\s+[\w.]*severity\s+(DESC|ASC)",
            "ORDER BY r.severity DESC, r.nhtsa_id",
            re.I,
        )


class TestTheIndexIsNotSilentlyLost:
    """Migration 206 added `idx_known_issues_sort` because EXPLAIN QUERY PLAN
    showed `SCAN` + `USE TEMP B-TREE FOR ORDER BY`. A CASE expression cannot
    use that index, so fixing the ordering without migration 053 would have
    silently undone that phase's work. This asserts the plan, not the index
    definition -- an index that exists but is not used is worth nothing."""

    def test_the_ordered_query_uses_an_index(self, db):
        with get_connection(db) as c:
            plan = c.execute(
                f"EXPLAIN QUERY PLAN SELECT * FROM known_issues "
                f"ORDER BY {SEVERITY_RANK_SQL} DESC, title"
            ).fetchall()
        detail = " ".join(r[-1] for r in plan)
        assert "USING INDEX idx_known_issues_sort" in detail, detail
        assert "TEMP B-TREE" not in detail, detail

    def test_schema_version_matches_the_migration(self):
        from motodiag.core.migrations import MIGRATIONS

        assert SCHEMA_VERSION == max(m.version for m in MIGRATIONS)

    def test_rollback_then_upgrade_restores_the_expression_index(self, tmp_path):
        """The index is recreated inside two table-rebuild migrations as well
        as by 053. If one of those still built the old form, a
        rollback-then-upgrade cycle would silently restore the lexicographic
        index and the query would lose its plan."""
        from motodiag.core.migrations import MIGRATIONS

        path = str(tmp_path / "roll.db")
        init_db(path)
        mig = next(m for m in MIGRATIONS if m.version == 53)
        with get_connection(path) as c:
            c.executescript(mig.rollback_sql)
            sql_after_rollback = c.execute(
                "SELECT sql FROM sqlite_master WHERE name='idx_known_issues_sort'"
            ).fetchone()[0]
            assert "CASE" not in sql_after_rollback
            c.executescript(mig.upgrade_sql)
            sql_after_upgrade = c.execute(
                "SELECT sql FROM sqlite_master WHERE name='idx_known_issues_sort'"
            ).fetchone()[0]
        assert "CASE" in sql_after_upgrade
        assert "WHEN 'critical' THEN 4" in sql_after_upgrade
