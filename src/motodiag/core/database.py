"""SQLite database connection and schema management."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from motodiag.core.config import get_settings


SCHEMA_VERSION = 1

SCHEMA_SQL = """
-- Vehicles table
CREATE TABLE IF NOT EXISTS vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    make TEXT NOT NULL,
    model TEXT NOT NULL,
    year INTEGER NOT NULL,
    engine_cc INTEGER,
    vin TEXT,
    protocol TEXT NOT NULL DEFAULT 'none',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_vehicles_make_model ON vehicles(make, model);
CREATE INDEX IF NOT EXISTS idx_vehicles_year ON vehicles(year);

-- DTC codes table
CREATE TABLE IF NOT EXISTS dtc_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'medium',
    make TEXT,
    common_causes TEXT,  -- JSON array
    fix_summary TEXT,
    UNIQUE(code, make)
);

CREATE INDEX IF NOT EXISTS idx_dtc_code ON dtc_codes(code);
CREATE INDEX IF NOT EXISTS idx_dtc_make ON dtc_codes(make);

-- Symptoms table
CREATE TABLE IF NOT EXISTS symptoms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    related_systems TEXT,  -- JSON array
    UNIQUE(name, category)
);

-- Known issues table
CREATE TABLE IF NOT EXISTS known_issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    make TEXT,
    model TEXT,
    year_start INTEGER,
    year_end INTEGER,
    severity TEXT NOT NULL DEFAULT 'medium',
    symptoms TEXT,  -- JSON array
    dtc_codes TEXT,  -- JSON array
    causes TEXT,  -- JSON array
    fix_procedure TEXT,
    parts_needed TEXT,  -- JSON array
    estimated_hours REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_known_issues_make_model ON known_issues(make, model);

-- Diagnostic sessions table
CREATE TABLE IF NOT EXISTS diagnostic_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER,
    vehicle_make TEXT NOT NULL,
    vehicle_model TEXT NOT NULL,
    vehicle_year INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    symptoms TEXT,  -- JSON array
    fault_codes TEXT,  -- JSON array
    diagnosis TEXT,
    repair_steps TEXT,  -- JSON array
    confidence REAL,
    severity TEXT,
    cost_estimate REAL,
    ai_model_used TEXT,
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    closed_at TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
);

CREATE INDEX IF NOT EXISTS idx_sessions_status ON diagnostic_sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_vehicle ON diagnostic_sessions(vehicle_make, vehicle_model);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def get_db_path() -> str:
    """Get database file path from settings."""
    return get_settings().db_path


def init_db(db_path: str | None = None) -> None:
    """Initialize the database with schema tables."""
    path = db_path or get_db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA_SQL)
        # Record schema version if not present
        cursor = conn.execute("SELECT COUNT(*) FROM schema_version")
        if cursor.fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,),
            )
        conn.commit()


@contextmanager
def get_connection(db_path: str | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Get a database connection as a context manager."""
    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_schema_version(db_path: str | None = None) -> int | None:
    """Get current schema version, or None if DB not initialized."""
    path = db_path or get_db_path()
    if not Path(path).exists():
        return None
    with get_connection(path) as conn:
        try:
            cursor = conn.execute(
                "SELECT MAX(version) FROM schema_version"
            )
            row = cursor.fetchone()
            return row[0] if row else None
        except sqlite3.OperationalError:
            return None


def table_exists(table_name: str, db_path: str | None = None) -> bool:
    """Check if a table exists in the database."""
    path = db_path or get_db_path()
    with get_connection(path) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        return cursor.fetchone() is not None
