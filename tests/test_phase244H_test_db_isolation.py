"""Phase 244H — the test suite writes to the production database.

Twice in one day a regression run applied a schema migration to the operator's
real `data/motodiag.db`. Migration 054 was recorded at 06:44:46 and 055 the same
way later. **Both were correct, which is why nobody noticed** — the dangerous
version is a test exercising a destructive path, and Phase 244D's migration
deleted 5,940 rows.

The mechanism: `get_connection(db_path=None)` resolves through
`get_settings().db_path`, and several CLI command paths call `init_db()` bare.
"""

import os
import sqlite3
from pathlib import Path

import pytest

from conftest import PRODUCTION_DB
from motodiag.core.config import get_settings, reset_settings
from motodiag.core.database import get_db_path, init_db


class TestTheDefaultIsRedirected:
    def test_the_bare_path_is_not_the_production_database(self):
        assert str(Path(get_db_path()).resolve()) != PRODUCTION_DB

    def test_the_environment_override_is_set(self):
        assert os.environ.get("MOTODIAG_DB_PATH"), (
            "conftest must set MOTODIAG_DB_PATH before anything resolves it")

    def test_settings_agree_with_the_override(self):
        assert get_settings().db_path == os.environ["MOTODIAG_DB_PATH"]

    def test_it_happens_at_import_time_not_fixture_time(self):
        """`get_settings` is an lru_cache'd singleton that modules may read while
        being imported, so a session-scoped fixture would run too late for
        anything resolved during collection."""
        from support.source_guards import code_of

        src = code_of(Path(__file__).parent / "conftest.py")
        assign = src.index('os.environ["MOTODIAG_DB_PATH"]')
        first_fixture = src.index("@pytest.fixture")
        assert assign < first_fixture, (
            "the redirect must be at module level, before any fixture")

    def test_an_explicit_override_still_wins(self):
        """Set only when unset, so a developer pointing at their own database is
        not overridden."""
        from support.source_guards import code_of

        src = code_of(Path(__file__).parent / "conftest.py")
        assert 'if not os.environ.get("MOTODIAG_DB_PATH")' in src


class TestABareInitDbDoesNotReachRealData:
    def test_init_db_with_no_arguments_creates_the_temporary_database(self):
        """The exact call shape that migrated the operator's database twice."""
        init_db()
        resolved = Path(get_db_path())
        assert resolved.exists()
        assert str(resolved.resolve()) != PRODUCTION_DB

    def test_a_bare_connection_opens_the_temporary_database(self):
        from motodiag.core.database import get_connection

        init_db()
        with get_connection() as conn:
            db_file = conn.execute("PRAGMA database_list").fetchall()[0][2]
        assert str(Path(db_file).resolve()) != PRODUCTION_DB


class TestTheOperatorsDatabaseIsUntouched:
    """The property actually wanted. Every other assertion here is a proxy."""

    def test_the_production_file_is_not_modified_by_a_bare_write(self):
        prod = Path(PRODUCTION_DB)
        if not prod.exists():
            pytest.skip("no production database on this machine")
        before = (prod.stat().st_mtime_ns, prod.stat().st_size)

        init_db()
        from motodiag.knowledge.issues_repo import add_known_issue

        add_known_issue(title="244H probe", description="d", make="Honda", model="CBR")

        after = (prod.stat().st_mtime_ns, prod.stat().st_size)
        assert before == after, "a bare write changed the operator's database"

    def test_the_probe_landed_somewhere_else(self):
        """Guard against the previous test passing because nothing was written."""
        from motodiag.knowledge.issues_repo import add_known_issue, count_known_issues

        init_db()
        before = count_known_issues()
        add_known_issue(title="244H probe 2", description="d", make="Honda", model="CBR")
        assert count_known_issues() == before + 1


class TestTheTripwireItself:
    def test_the_autouse_tripwire_exists(self):
        from support.source_guards import code_of

        src = code_of(Path(__file__).parent / "conftest.py")
        assert "_never_the_production_database" in src
        assert "autouse=True" in src

    def test_the_tripwire_fires_when_the_default_points_at_production(self, monkeypatch):
        """Simulated rather than asserted structurally: point the setting back at
        production and confirm the condition the fixture tests would fail."""
        monkeypatch.setenv("MOTODIAG_DB_PATH", PRODUCTION_DB)
        reset_settings()
        assert str(Path(get_db_path()).resolve()) == PRODUCTION_DB
        # No manual restore: monkeypatch puts the env var back at teardown, and
        # conftest clears the settings cache after every test. The first version
        # of this guard called `delenv` in a `finally`, which runs BEFORE
        # monkeypatch restores — it wiped the session default for every test
        # that came after and turned four unrelated guards into errors.

    def test_the_tripwire_message_names_the_cause(self):
        from support.source_guards import code_of

        src = code_of(Path(__file__).parent / "conftest.py")
        assert "get_connection(db_path=None)" in src, (
            "the failure message must explain the fall-through, not just report it")


class TestTheSharedRedirectFixture:
    def test_it_redirects_both_read_and_write_paths(self, redirect_default_db):
        """Patching `init_db` alone covered the write path and left the read
        path resolving to the operator's database — several fixtures did exactly
        that, and passed only because production was seeded."""
        from motodiag.core.database import get_connection

        assert get_db_path() == redirect_default_db
        with get_connection() as conn:
            db_file = conn.execute("PRAGMA database_list").fetchall()[0][2]
        assert str(Path(db_file).resolve()) == str(Path(redirect_default_db).resolve())

    def test_it_leaves_a_usable_schema(self, redirect_default_db):
        with sqlite3.connect(redirect_default_db) as conn:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        assert "known_issues" in tables and "dtc_codes" in tables

    def test_it_restores_the_setting_afterwards(self, request):
        """The fixture must not leak its redirect into later tests."""
        before = os.environ.get("MOTODIAG_DB_PATH")
        assert before, "the session default should be in place here"
