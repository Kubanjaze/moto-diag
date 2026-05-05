"""Phase 191B fix-cycle — `motodiag serve` startup-migration regression guard.

The bug surfaced at the Phase 191B architect-gate: backend code shipped
SCHEMA_VERSION = 39 (videos table migration), but `motodiag serve`
launched against an existing v38 DB stayed at v38 because neither
`serve_cmd` nor `create_app()` was calling `init_db()`. Architect had
to manually run `python -c "from motodiag.core.database import init_db;
init_db()"` to advance the schema before /v1/version reflected v39.

Latent since Phase 175. Surfaced by Phase 191B's deploy path because
this is the first phase to ship a new migration AFTER an architect-gate
emulator session had already initialized + persisted a DB at the previous
schema version. Same failure-family shape as Phase 187 latent + Phase
188 surfaced (Content-Type strip on POST) and Phase 175 latent + Phase
190 surfaced (DTC 404 ProblemDetail shape mismatch): a code path that
"works in tests" because the tests' setup happens to compensate for the
production gap.

Fix lives in `serve_cmd` (not `create_app()`) to preserve Phase 175's
choice that the app factory is side-effect-free for tests.

Tests guard the contract:
  - serve_cmd applies pending migrations by default
  - serve_cmd respects --skip-migrations and warns when DB is out of date
  - the migration apply is idempotent (re-invoking serve_cmd is safe)
"""

from __future__ import annotations

from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

from motodiag.core.database import SCHEMA_VERSION, init_db
from motodiag.core.migrations import get_current_version


@pytest.fixture
def cli_with_serve(tmp_path, monkeypatch):
    """Click group with the serve command registered + DB pointed at tmp."""
    db_path = str(tmp_path / "phase191b_serve.db")
    monkeypatch.setenv("MOTODIAG_DB_PATH", db_path)
    # Reset settings cache so MOTODIAG_DB_PATH takes effect
    from motodiag.core.config import reset_settings
    reset_settings()

    from motodiag.cli.serve import register_serve

    @click.group()
    def root():
        pass

    register_serve(root)
    yield root, db_path
    reset_settings()


def _make_db_at_version(db_path: str, target_version: int) -> None:
    """Initialize a DB and apply migrations up to (and including)
    target_version. Returns silently when already at or beyond target."""
    init_db(db_path, apply_migrations=False)
    from motodiag.core import migrations as migrations_mod
    pending = [
        m for m in migrations_mod.MIGRATIONS
        if m.version <= target_version
    ]
    for m in pending:
        if get_current_version(db_path) < m.version:
            migrations_mod.apply_migration(m, db_path=db_path)
    assert get_current_version(db_path) == target_version


# ---------------------------------------------------------------------
# 1. Migration apply on startup
# ---------------------------------------------------------------------


class TestServeAppliesMigrationsByDefault:
    """The fix-cycle's load-bearing assertion: serve_cmd advances the DB
    schema to match SCHEMA_VERSION before launching uvicorn."""

    def test_serve_applies_pending_migration_to_match_schema_version(
        self, cli_with_serve,
    ):
        """v38 DB + Phase 191B SCHEMA_VERSION=39 → serve advances to 39."""
        root, db_path = cli_with_serve
        _make_db_at_version(db_path, target_version=38)
        assert get_current_version(db_path) == 38

        runner = CliRunner()
        with patch("uvicorn.run") as mock_uvicorn:
            result = runner.invoke(root, ["serve"])

        assert result.exit_code == 0, result.output
        assert get_current_version(db_path) == SCHEMA_VERSION
        assert get_current_version(db_path) == 39  # f9-noqa: ssot-pin fixture-data: literal `39` here is the migration boundary the test exercises (38 → 39 via fix-cycle-1's startup migration apply); paired with the `== SCHEMA_VERSION` assertion above as a "this version IS the version we expect" cross-check. Replacing with SCHEMA_VERSION would lose the test's intent (verify the integer landed at the specific expected number, not just "matches whatever SCHEMA_VERSION currently is").
        # uvicorn was called (we mocked it; it didn't actually launch)
        assert mock_uvicorn.called
        # Output mentions the migration apply
        assert (
            "Applied migrations: schema_version 38 → 39" in result.output
            or "schema_version 38" in result.output
        )

    def test_serve_logs_no_op_when_schema_already_at_target(
        self, cli_with_serve,
    ):
        """DB already at SCHEMA_VERSION → init_db is no-op, log says so."""
        root, db_path = cli_with_serve
        _make_db_at_version(db_path, target_version=SCHEMA_VERSION)

        runner = CliRunner()
        with patch("uvicorn.run") as mock_uvicorn:
            result = runner.invoke(root, ["serve"])

        assert result.exit_code == 0, result.output
        assert get_current_version(db_path) == SCHEMA_VERSION
        assert "DB schema up to date" in result.output
        assert mock_uvicorn.called

    def test_serve_creates_db_when_missing(
        self, cli_with_serve,
    ):
        """No DB on disk → serve creates one + applies all migrations."""
        import os
        root, db_path = cli_with_serve
        # Don't pre-create the DB
        assert not os.path.exists(db_path)

        runner = CliRunner()
        with patch("uvicorn.run") as mock_uvicorn:
            result = runner.invoke(root, ["serve"])

        assert result.exit_code == 0, result.output
        assert os.path.exists(db_path)
        assert get_current_version(db_path) == SCHEMA_VERSION
        assert mock_uvicorn.called

    def test_serve_migration_is_idempotent(self, cli_with_serve):
        """Two consecutive serve invocations both succeed; schema stays
        at SCHEMA_VERSION after both."""
        root, db_path = cli_with_serve
        _make_db_at_version(db_path, target_version=38)

        runner = CliRunner()
        with patch("uvicorn.run"):
            r1 = runner.invoke(root, ["serve"])
            assert r1.exit_code == 0
            v1 = get_current_version(db_path)
            r2 = runner.invoke(root, ["serve"])
            assert r2.exit_code == 0
            v2 = get_current_version(db_path)

        assert v1 == SCHEMA_VERSION
        assert v2 == SCHEMA_VERSION


# ---------------------------------------------------------------------
# 2. --skip-migrations escape hatch
# ---------------------------------------------------------------------


class TestSkipMigrationsFlag:
    """--skip-migrations preserves the old (buggy) behavior for deploy
    pipelines that run migrations out-of-band."""

    def test_skip_migrations_does_not_advance_schema(self, cli_with_serve):
        """v38 DB + --skip-migrations → still v38 after serve."""
        root, db_path = cli_with_serve
        _make_db_at_version(db_path, target_version=38)

        runner = CliRunner()
        with patch("uvicorn.run") as mock_uvicorn:
            result = runner.invoke(root, ["serve", "--skip-migrations"])

        assert result.exit_code == 0, result.output
        assert get_current_version(db_path) == 38
        assert "Skipping migration apply" in result.output
        assert mock_uvicorn.called

    def test_skip_migrations_warns_when_schema_out_of_date(
        self, cli_with_serve,
    ):
        """--skip-migrations + schema mismatch → stderr warning."""
        root, db_path = cli_with_serve
        _make_db_at_version(db_path, target_version=38)

        runner = CliRunner()
        with patch("uvicorn.run"):
            result = runner.invoke(root, ["serve", "--skip-migrations"])

        assert result.exit_code == 0
        assert "WARNING" in result.stderr
        assert "does not match" in result.stderr

    def test_skip_migrations_no_warning_when_schema_matches(
        self, cli_with_serve,
    ):
        """--skip-migrations + already at SCHEMA_VERSION → no stderr warning."""
        root, db_path = cli_with_serve
        _make_db_at_version(db_path, target_version=SCHEMA_VERSION)

        runner = CliRunner()
        with patch("uvicorn.run"):
            result = runner.invoke(root, ["serve", "--skip-migrations"])

        assert result.exit_code == 0
        assert "WARNING" not in (result.stderr or "")


# ---------------------------------------------------------------------
# 3. uvicorn launch surface (defensive — confirm the fix doesn't break
# the existing serve invocation pattern)
# ---------------------------------------------------------------------


class TestUvicornLaunchSurface:

    def test_serve_invokes_uvicorn_with_factory_pattern(self, cli_with_serve):
        """Phase 175's contract: serve uses factory=True against
        motodiag.api:create_app."""
        root, db_path = cli_with_serve
        _make_db_at_version(db_path, target_version=SCHEMA_VERSION)

        runner = CliRunner()
        with patch("uvicorn.run") as mock_uvicorn:
            result = runner.invoke(root, ["serve"])

        assert result.exit_code == 0, result.output
        assert mock_uvicorn.called
        args, kwargs = mock_uvicorn.call_args
        # First positional arg or 'app' kwarg is the import string
        assert args[0] == "motodiag.api:create_app"
        assert kwargs.get("factory") is True
