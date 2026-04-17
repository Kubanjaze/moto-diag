"""Schema migration framework for MotoDiag.

Phase 110: Reusable forward-only migration system with rollback support.
All subsequent retrofit phases (111-120) and future expansion tracks append
to MIGRATIONS. Each migration runs in a transaction; on failure the schema
version is not bumped.

Design:
- Forward-only in production (new DB gets all migrations, existing DB
  applies only missing ones)
- Rollback supported for testing and emergency recovery
- Each migration has a unique integer version matching schema_version table
- Migration 001 corresponds to initial schema (tracked in database.py)
- Migration 002 corresponds to pricing tables added later
- Migration 003+ are retrofit-era additions
"""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from motodiag.core.config import get_settings
from motodiag.core.database import get_connection


class Migration(BaseModel):
    """A single schema migration.

    upgrade_sql runs when applying the migration (forward).
    rollback_sql runs when reverting (used for testing, emergency recovery).
    Both should be idempotent where possible.
    """
    version: int = Field(..., description="Unique monotonic version number matching schema_version table")
    name: str = Field(..., description="Short slug describing the migration")
    description: str = Field(..., description="Human-readable explanation of what this migrates")
    upgrade_sql: str = Field(..., description="SQL to apply the migration")
    rollback_sql: str = Field(default="", description="SQL to revert the migration (optional but recommended)")


# --- Migration registry ---
# Retrofit phases append entries here. Do NOT delete or reorder — migrations
# are applied in version order, and existing DBs rely on consistent history.

MIGRATIONS: list[Migration] = [
    # Migration 003 — Phase 110: vehicle registry expansion
    Migration(
        version=3,
        name="vehicle_powertrain_expansion",
        description=(
            "Phase 110: Add powertrain (ICE/electric/hybrid), engine_type "
            "(4-stroke/2-stroke/electric/hybrid/desmo), battery_chemistry, "
            "motor_kw, and bms_present columns to vehicles table. Existing "
            "rows get ICE/4-stroke defaults."
        ),
        upgrade_sql="""
            ALTER TABLE vehicles ADD COLUMN powertrain TEXT DEFAULT 'ice';
            ALTER TABLE vehicles ADD COLUMN engine_type TEXT DEFAULT 'four_stroke';
            ALTER TABLE vehicles ADD COLUMN battery_chemistry TEXT;
            ALTER TABLE vehicles ADD COLUMN motor_kw REAL;
            ALTER TABLE vehicles ADD COLUMN bms_present INTEGER DEFAULT 0;
        """,
        rollback_sql="""
            -- SQLite does not support DROP COLUMN directly pre-3.35.
            -- Use CREATE-COPY-DROP-RENAME pattern. For rollback testing only.
            CREATE TABLE vehicles_rollback AS
                SELECT id, make, model, year, engine_cc, vin, protocol, notes
                FROM vehicles;
            DROP TABLE vehicles;
            ALTER TABLE vehicles_rollback RENAME TO vehicles;
        """,
    ),
]


def get_current_version(db_path: Optional[str] = None) -> int:
    """Return the highest applied schema version, or 0 if the DB is fresh."""
    path = db_path or get_settings().db_path
    if not Path(path).exists():
        return 0

    with get_connection(path) as conn:
        try:
            cursor = conn.execute("SELECT MAX(version) FROM schema_version")
            row = cursor.fetchone()
            if row and row[0] is not None:
                return int(row[0])
        except Exception:
            # schema_version table may not exist on a very fresh DB
            return 0
    return 0


def get_applied_migrations(db_path: Optional[str] = None) -> list[int]:
    """Return a sorted list of all applied schema version numbers."""
    path = db_path or get_settings().db_path
    if not Path(path).exists():
        return []

    with get_connection(path) as conn:
        try:
            cursor = conn.execute("SELECT version FROM schema_version ORDER BY version")
            return [int(row[0]) for row in cursor.fetchall()]
        except Exception:
            return []


def get_pending_migrations(db_path: Optional[str] = None) -> list[Migration]:
    """Return migrations with a version higher than the current applied max."""
    current = get_current_version(db_path)
    return [m for m in MIGRATIONS if m.version > current]


def apply_migration(migration: Migration, db_path: Optional[str] = None) -> None:
    """Apply a single migration transactionally.

    On failure, the transaction rolls back and schema_version is not updated.
    """
    path = db_path or get_settings().db_path

    with get_connection(path) as conn:
        # Execute the upgrade SQL (may be multi-statement)
        conn.executescript(migration.upgrade_sql)

        # Record the migration in schema_version
        conn.execute(
            "INSERT INTO schema_version (version) VALUES (?)",
            (migration.version,),
        )


def apply_pending_migrations(db_path: Optional[str] = None) -> list[int]:
    """Apply all pending migrations in version order. Returns applied versions."""
    pending = get_pending_migrations(db_path)
    applied: list[int] = []

    for migration in sorted(pending, key=lambda m: m.version):
        apply_migration(migration, db_path)
        applied.append(migration.version)

    return applied


def rollback_migration(migration: Migration, db_path: Optional[str] = None) -> None:
    """Roll back a single migration using its rollback_sql.

    Mainly for testing and emergency recovery. Not used in normal operation.
    """
    if not migration.rollback_sql.strip():
        raise ValueError(
            f"Migration {migration.version} ({migration.name}) has no rollback_sql defined"
        )

    path = db_path or get_settings().db_path

    with get_connection(path) as conn:
        conn.executescript(migration.rollback_sql)
        # Remove from schema_version
        conn.execute(
            "DELETE FROM schema_version WHERE version = ?",
            (migration.version,),
        )


def rollback_to_version(target_version: int, db_path: Optional[str] = None) -> list[int]:
    """Roll back migrations until the DB is at target_version.

    Rolls back in reverse version order. For testing and recovery.
    """
    applied = get_applied_migrations(db_path)
    to_rollback = sorted([v for v in applied if v > target_version], reverse=True)

    rolled_back: list[int] = []
    for version in to_rollback:
        migration = next((m for m in MIGRATIONS if m.version == version), None)
        if migration is None:
            raise ValueError(f"No migration definition found for version {version}")
        rollback_migration(migration, db_path)
        rolled_back.append(version)

    return rolled_back


def get_migration_by_version(version: int) -> Optional[Migration]:
    """Look up a migration by version number."""
    return next((m for m in MIGRATIONS if m.version == version), None)
