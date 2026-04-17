"""Phase 127 — Session History Browser tests.

Covers:
- `TestMigration014`: migration 014 definition, SCHEMA_VERSION bump, notes
  column actually created on a fresh init.
- `TestSessionRepoExtensions`: list_sessions new keyword-only filters
  (vehicle_id, search, since, until, limit), reopen_session (happy /
  missing / already-open), append_note (append / preserve prior / missing
  session), get_notes.
- `TestCliList`: --make, --search, --since, --limit, empty-result message.
- `TestCliReopen`: happy path, missing session, already-open warning.
- `TestCliAnnotate`: happy path, missing session, multiple annotations
  accumulate, special-character note text.
- `TestShowIncludesNotes`: terminal rendering includes a Notes panel,
  markdown formatter includes `## Notes` section.

Zero AI calls — all exercises use pure repo + CLI with no `_default_diagnose_fn`
mocking required (we seed sessions directly via `create_session` / `set_diagnosis`).
"""

from __future__ import annotations

import time

import pytest
from click.testing import CliRunner

from motodiag.core.database import (
    SCHEMA_VERSION,
    get_connection,
    init_db,
    get_schema_version,
)
from motodiag.core.migrations import get_migration_by_version
from motodiag.core.session_repo import (
    append_note,
    close_session,
    create_session,
    get_notes,
    get_session,
    list_sessions,
    reopen_session,
    set_diagnosis,
)


# --- Fixtures ---


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase127.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(db, monkeypatch):
    """Point settings at the temp DB; reset config cache after. Mirrors the
    Phase 125 / 126 pattern."""
    from motodiag.core.config import reset_settings
    monkeypatch.setenv("MOTODIAG_DB_PATH", db)
    reset_settings()
    yield db
    reset_settings()


def _seed_diagnosed_session(
    db_path: str,
    make: str = "Harley-Davidson",
    model: str = "Sportster 1200",
    year: int = 2001,
    vehicle_id: int | None = None,
    diagnosis: str = "Stator failure — voltage drops under load.",
    symptoms: list[str] | None = None,
    fault_codes: list[str] | None = None,
    close: bool = True,
    created_at: str | None = None,
) -> int:
    """Create, diagnose, and (optionally) close a session.

    If `created_at` is provided we also back-date the row so date-range
    filter tests have a deterministic spread of timestamps independent of
    wall-clock ordering.
    """
    # If the caller specifies a vehicle_id, make sure a matching row exists
    # (FKs are enforced via PRAGMA foreign_keys=ON in the connection manager).
    if vehicle_id is not None:
        with get_connection(db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO vehicles (id, make, model, year, protocol) "
                "VALUES (?, ?, ?, ?, 'none')",
                (vehicle_id, make, model, year),
            )
    sid = create_session(
        vehicle_make=make,
        vehicle_model=model,
        vehicle_year=year,
        symptoms=symptoms or [],
        fault_codes=fault_codes or [],
        vehicle_id=vehicle_id,
        db_path=db_path,
    )
    set_diagnosis(
        session_id=sid,
        diagnosis=diagnosis,
        confidence=0.85,
        severity="high",
        repair_steps=["Check wiring", "Replace part"],
        db_path=db_path,
    )
    if close:
        close_session(sid, db_path=db_path)
    if created_at is not None:
        with get_connection(db_path) as conn:
            conn.execute(
                "UPDATE diagnostic_sessions SET created_at = ? WHERE id = ?",
                (created_at, sid),
            )
    return sid


# =============================================================================
# TestMigration014 — schema change for `notes` column
# =============================================================================


class TestMigration014:
    def test_migration_014_exists_in_registry(self):
        """Migration 014 is registered with the expected name and SQL."""
        m = get_migration_by_version(14)
        assert m is not None, "Migration 014 must be registered"
        assert m.name == "session_notes_column"
        # Sanity-check the upgrade SQL adds the notes column; we only look
        # for the critical tokens so formatting changes in the migration
        # don't break the test.
        assert "diagnostic_sessions" in m.upgrade_sql
        assert "notes" in m.upgrade_sql
        assert "TEXT" in m.upgrade_sql

    def test_fresh_init_has_notes_column(self, db):
        """After init_db, diagnostic_sessions.notes exists and is NULL by default."""
        with get_connection(db) as conn:
            cursor = conn.execute("PRAGMA table_info(diagnostic_sessions)")
            columns = {row["name"]: row for row in cursor.fetchall()}
        assert "notes" in columns, (
            f"notes column missing; got {sorted(columns)}"
        )

        # New sessions get notes=NULL
        sid = create_session(
            vehicle_make="Honda", vehicle_model="CBR929RR",
            vehicle_year=2000, db_path=db,
        )
        with get_connection(db) as conn:
            row = conn.execute(
                "SELECT notes FROM diagnostic_sessions WHERE id=?", (sid,)
            ).fetchone()
        assert row["notes"] is None

    def test_schema_version_bumped(self, db):
        """SCHEMA_VERSION constant is at least 14 and the DB tracks it."""
        assert SCHEMA_VERSION >= 14
        assert get_schema_version(db) >= 14


# =============================================================================
# TestSessionRepoExtensions — new list_sessions filters + notes functions
# =============================================================================


class TestSessionRepoExtensions:
    def test_list_sessions_vehicle_id_filter(self, db):
        sid1 = _seed_diagnosed_session(db, vehicle_id=10)
        sid2 = _seed_diagnosed_session(db, vehicle_id=20, make="Honda", model="CBR")
        results = list_sessions(vehicle_id=10, db_path=db)
        ids = [r["id"] for r in results]
        assert sid1 in ids and sid2 not in ids

    def test_list_sessions_search_is_case_insensitive(self, db):
        sid_stator = _seed_diagnosed_session(
            db, diagnosis="Stator failure — voltage drops under load."
        )
        sid_reg = _seed_diagnosed_session(
            db, make="Honda", model="CBR929RR", year=2000,
            diagnosis="Regulator/rectifier burnout on highway."
        )
        # Lowercase search must still match 'Stator' (capitalized in the data)
        results = list_sessions(search="stator", db_path=db)
        ids = [r["id"] for r in results]
        assert sid_stator in ids
        assert sid_reg not in ids

    def test_list_sessions_since_filter(self, db):
        old = _seed_diagnosed_session(
            db, created_at="2026-03-01T10:00:00", make="Yamaha"
        )
        new = _seed_diagnosed_session(
            db, created_at="2026-04-15T10:00:00", make="Kawasaki"
        )
        results = list_sessions(since="2026-04-01", db_path=db)
        ids = [r["id"] for r in results]
        assert new in ids and old not in ids

    def test_list_sessions_until_filter(self, db):
        old = _seed_diagnosed_session(
            db, created_at="2026-03-01T10:00:00", make="Yamaha"
        )
        new = _seed_diagnosed_session(
            db, created_at="2026-04-15T10:00:00", make="Kawasaki"
        )
        # Pure lexicographic compare: '2026-04-01' < '2026-04-15T10:00:00' but
        # > '2026-03-01T10:00:00' so only `old` stays
        results = list_sessions(until="2026-04-01", db_path=db)
        ids = [r["id"] for r in results]
        assert old in ids and new not in ids

    def test_list_sessions_limit_caps_results(self, db):
        # Seed 5 sessions; limit=2 returns exactly 2
        for i in range(5):
            _seed_diagnosed_session(db, make=f"Brand{i}")
        results = list_sessions(limit=2, db_path=db)
        assert len(results) == 2

    def test_reopen_session_happy_path(self, db):
        sid = _seed_diagnosed_session(db, close=True)
        # Pre-state: closed
        pre = get_session(sid, db_path=db)
        assert pre["status"] == "closed"
        assert pre["closed_at"] is not None

        ok = reopen_session(sid, db_path=db)
        assert ok is True
        post = get_session(sid, db_path=db)
        assert post["status"] == "open"
        assert post["closed_at"] is None
        # Diagnosis preserved
        assert post["diagnosis"] == pre["diagnosis"]
        assert post["confidence"] == pre["confidence"]

    def test_reopen_session_missing_returns_false(self, db):
        assert reopen_session(99999, db_path=db) is False

    def test_reopen_session_already_open_is_noop(self, db):
        # Create without closing; status starts as 'open' after create then
        # 'diagnosed' after set_diagnosis. We'll create without diagnosing
        # to leave status='open'.
        sid = create_session(
            vehicle_make="Suzuki", vehicle_model="GSXR",
            vehicle_year=2005, db_path=db,
        )
        pre = get_session(sid, db_path=db)
        assert pre["status"] == "open"
        # reopen returns True because the UPDATE matches a row (idempotent)
        ok = reopen_session(sid, db_path=db)
        assert ok is True
        post = get_session(sid, db_path=db)
        assert post["status"] == "open"

    def test_append_note_adds_timestamp_prefix(self, db):
        sid = _seed_diagnosed_session(db)
        ok = append_note(sid, "Follow-up: verified regulator fault", db_path=db)
        assert ok is True
        notes = get_notes(sid, db_path=db)
        assert notes is not None
        # Prefix '[YYYY-MM-DDTHH:MM] ' — validate shape rather than exact time
        assert notes.startswith("[")
        # ISO date separator 'T' and minute granularity (HH:MM) in the stamp
        assert "T" in notes.split("]")[0]
        assert "Follow-up: verified regulator fault" in notes

    def test_append_note_preserves_prior(self, db):
        sid = _seed_diagnosed_session(db)
        append_note(sid, "First note", db_path=db)
        # Sleep a hair so timestamps can differ at minute resolution — but
        # even if they don't, the append logic just concatenates both
        # entries so the test still asserts the double-entry structure.
        time.sleep(0.01)
        append_note(sid, "Second note", db_path=db)

        notes = get_notes(sid, db_path=db)
        assert notes is not None
        assert "First note" in notes
        assert "Second note" in notes
        # Blank-line separator between entries
        assert "\n\n" in notes
        # First note appears before second note
        assert notes.index("First note") < notes.index("Second note")

    def test_append_note_missing_session_returns_false(self, db):
        ok = append_note(99999, "text", db_path=db)
        assert ok is False


# =============================================================================
# TestCliList — new filter options on `diagnose list`
# =============================================================================


class TestCliList:
    def test_list_make_filter(self, cli_db):
        _seed_diagnosed_session(cli_db, make="Harley-Davidson", model="Sportster 1200")
        _seed_diagnosed_session(cli_db, make="Honda", model="CBR929RR", year=2000)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["diagnose", "list", "--make", "Honda"])
        assert r.exit_code == 0, r.output
        assert "Honda" in r.output
        # The Harley row must not appear
        assert "Harley-Davidson" not in r.output
        assert "Sportster" not in r.output

    def test_list_search_filter(self, cli_db):
        _seed_diagnosed_session(
            cli_db, diagnosis="Stator failure — voltage drops under load."
        )
        _seed_diagnosed_session(
            cli_db, make="Honda", model="CBR",
            diagnosis="Regulator/rectifier burnout on highway."
        )
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["diagnose", "list", "--search", "stator"])
        assert r.exit_code == 0, r.output
        # At least the Stator row appears; the regulator row's diagnosis text
        # does not contain 'stator'.
        assert "Stator" in r.output or "stator" in r.output.lower()
        assert "Regulator" not in r.output

    def test_list_since_filter(self, cli_db):
        _seed_diagnosed_session(
            cli_db, created_at="2026-03-01T10:00:00", make="Yamaha",
            diagnosis="OLD — clutch wear.",
        )
        _seed_diagnosed_session(
            cli_db, created_at="2026-04-15T10:00:00", make="Kawasaki",
            diagnosis="NEW — chain stretch.",
        )
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["diagnose", "list", "--since", "2026-04-01"])
        assert r.exit_code == 0, r.output
        # The newer (Kawasaki) session should appear, the older (Yamaha) should not
        assert "Kawasaki" in r.output
        assert "Yamaha" not in r.output

    def test_list_limit_caps_rows(self, cli_db):
        # Seed 5 sessions; --limit 2 should only show 2.
        for i in range(5):
            _seed_diagnosed_session(
                cli_db, make=f"Brand{i}", diagnosis=f"Diag number {i} here."
            )
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["diagnose", "list", "--limit", "2"])
        assert r.exit_code == 0, r.output
        # Count how many of our seeded brand names are in the output. With
        # --limit 2, only 2 brands should appear.
        brand_hits = sum(f"Brand{i}" in r.output for i in range(5))
        assert brand_hits == 2, (
            f"Expected exactly 2 brand rows with --limit 2, got {brand_hits}. "
            f"Output: {r.output}"
        )

    def test_list_empty_result_message(self, cli_db):
        _seed_diagnosed_session(cli_db, make="Harley-Davidson")
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["diagnose", "list", "--make", "Ducati"])
        assert r.exit_code == 0, r.output
        assert "no sessions match" in r.output.lower()


# =============================================================================
# TestCliReopen — `diagnose reopen <id>`
# =============================================================================


class TestCliReopen:
    def test_reopen_happy_path(self, cli_db):
        sid = _seed_diagnosed_session(cli_db, close=True)
        # Confirm pre-state
        assert get_session(sid, db_path=cli_db)["status"] == "closed"
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["diagnose", "reopen", str(sid)])
        assert r.exit_code == 0, r.output
        assert f"#{sid}" in r.output
        assert "reopened" in r.output.lower()
        # Post-state: open
        assert get_session(sid, db_path=cli_db)["status"] == "open"

    def test_reopen_missing_session_errors(self, cli_db):
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["diagnose", "reopen", "99999"])
        assert r.exit_code != 0
        assert "not found" in r.output.lower()

    def test_reopen_already_open_warns(self, cli_db):
        # create_session leaves status='open' (no set_diagnosis / close_session)
        sid = create_session(
            vehicle_make="Suzuki", vehicle_model="GSXR",
            vehicle_year=2005, db_path=cli_db,
        )
        assert get_session(sid, db_path=cli_db)["status"] == "open"
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["diagnose", "reopen", str(sid)])
        # Exit code is 0 (not an error) but the output warns.
        assert r.exit_code == 0, r.output
        assert "already open" in r.output.lower()


# =============================================================================
# TestCliAnnotate — `diagnose annotate <id> <text>`
# =============================================================================


class TestCliAnnotate:
    def test_annotate_happy_path_prints_notes(self, cli_db):
        sid = _seed_diagnosed_session(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, [
            "diagnose", "annotate", str(sid),
            "Verified regulator fault on dyno",
        ])
        assert r.exit_code == 0, r.output
        assert "note added" in r.output.lower()
        assert "Verified regulator fault on dyno" in r.output

        # The notes column was updated in the DB
        notes = get_notes(sid, db_path=cli_db)
        assert notes is not None
        assert "Verified regulator fault on dyno" in notes

    def test_annotate_missing_session_errors(self, cli_db):
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["diagnose", "annotate", "99999", "text"])
        assert r.exit_code != 0
        assert "not found" in r.output.lower()

    def test_annotate_multiple_accumulate(self, cli_db):
        sid = _seed_diagnosed_session(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r1 = runner.invoke(cli, [
            "diagnose", "annotate", str(sid), "First observation",
        ])
        assert r1.exit_code == 0, r1.output
        r2 = runner.invoke(cli, [
            "diagnose", "annotate", str(sid), "Follow-up after dyno test",
        ])
        assert r2.exit_code == 0, r2.output

        notes = get_notes(sid, db_path=cli_db)
        assert "First observation" in notes
        assert "Follow-up after dyno test" in notes
        assert notes.index("First observation") < notes.index(
            "Follow-up after dyno test"
        )
        # Blank-line separator between annotations
        assert "\n\n" in notes

    def test_annotate_special_characters(self, cli_db):
        sid = _seed_diagnosed_session(cli_db)
        from motodiag.cli.main import cli

        # Exercise Unicode (Ω Greek Omega, em-dash) + CLI-special characters
        # (semicolon, @) so a future CLI-arg escaping change does not silently
        # drop them. SQLite stores UTF-8 by default, so the full string should
        # survive the round-trip into the notes column.
        special = 'Replaced stator — 0.2Ω reading; customer @ 5pm!'
        runner = CliRunner()
        r = runner.invoke(cli, ["diagnose", "annotate", str(sid), special])
        assert r.exit_code == 0, r.output
        notes = get_notes(sid, db_path=cli_db)
        assert notes is not None
        # All special tokens survive into the persisted notes
        assert "Ω" in notes
        assert "—" in notes
        assert "customer @ 5pm" in notes
        assert ";" in notes


# =============================================================================
# TestShowIncludesNotes — formatter + terminal rendering integration
# =============================================================================


class TestShowIncludesNotes:
    def test_terminal_show_includes_notes_panel(self, cli_db):
        sid = _seed_diagnosed_session(cli_db)
        # Add a note directly via append_note so the terminal path reads it
        append_note(sid, "Customer confirmed intermittent stall", db_path=cli_db)

        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["diagnose", "show", str(sid)])
        assert r.exit_code == 0, r.output
        # Rich Panel title "Notes" surfaces in the captured output.
        assert "Notes" in r.output
        assert "Customer confirmed intermittent stall" in r.output

    def test_md_format_includes_notes_section(self, cli_db):
        sid = _seed_diagnosed_session(cli_db)
        append_note(sid, "Pulled service bulletin for this VIN range", db_path=cli_db)

        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, [
            "diagnose", "show", str(sid), "--format", "md",
        ])
        assert r.exit_code == 0, r.output
        assert "## Notes" in r.output
        assert "Pulled service bulletin for this VIN range" in r.output
