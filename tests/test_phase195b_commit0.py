"""Phase 195B (Commit 0) — Whisper client + cost ledger + F44 fold-in.

Covers:
* Migration 043 — `cost_events` table shape + indexes + `kind` CHECK
  enum + `transcript_id` FK ON DELETE SET NULL.
* `shop/cost_repo.py` — record + aggregate + per-shop monthly rollup.
* `media/whisper_client.py` — cost math, availability gate, typed
  errors (no live API call; the SDK call path is gated behind an
  API key the test environment doesn't set).
* `motodiag costs report` CLI.
* F44 fold-in — `api_port` default moved 8080 → 8000.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from motodiag.core.config import Settings, reset_settings
from motodiag.core.database import SCHEMA_VERSION, get_connection, init_db
from motodiag.media.whisper_client import (
    WHISPER_USD_CENTS_PER_MINUTE,
    WhisperTranscriptionError,
    WhisperUnavailableError,
    estimate_cost_usd_cents,
    transcribe,
    whisper_available,
)
from motodiag.shop.cost_repo import (
    aggregate_costs,
    record_cost_event,
    shop_cost_this_month,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = str(tmp_path / "phase195b_c0.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    reset_settings()
    yield path
    reset_settings()


# ---------------------------------------------------------------------------
# 1. Migration 043
# ---------------------------------------------------------------------------


class TestMigration043:

    def test_schema_version_at_least_43(self):
        # F9-SSOT discipline: floor not equality (phase-194 precedent).
        assert SCHEMA_VERSION >= 43  # f9-noqa: ssot-pin contract-pin: phase-195B floor — verifies migration 043 landed

    def test_cost_events_table_shape(self, db):
        with get_connection(db) as conn:
            cols = {
                r[1]: (r[2], bool(r[3]))
                for r in conn.execute("PRAGMA table_info(cost_events)")
            }
        for name in (
            "id", "kind", "model", "transcript_id", "shop_id",
            "units_label", "units_value", "cost_usd_cents", "created_at",
        ):
            assert name in cols, f"missing column: {name}"
        assert cols["kind"][1] is True          # NOT NULL
        assert cols["model"][1] is True
        assert cols["cost_usd_cents"][1] is True

    def test_cost_events_indexes(self, db):
        with get_connection(db) as conn:
            names = {
                r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' "
                    "AND tbl_name='cost_events'"
                )
            }
        assert "idx_cost_events_created" in names
        assert "idx_cost_events_shop" in names
        assert "idx_cost_events_kind" in names

    def test_kind_check_constraint_rejects_invalid(self, db):
        with get_connection(db) as conn:
            with pytest.raises(Exception):  # IntegrityError
                conn.execute(
                    "INSERT INTO cost_events (kind, model, cost_usd_cents) "
                    "VALUES ('INVALID', 'whisper-1', 1)"
                )

    def test_kind_check_accepts_both_enum_values(self, db):
        with get_connection(db) as conn:
            for kind in ("whisper", "claude_extraction"):
                conn.execute(
                    "INSERT INTO cost_events (kind, model, cost_usd_cents) "
                    "VALUES (?, ?, 1)",
                    (kind, "m"),
                )


# ---------------------------------------------------------------------------
# 2. cost_repo
# ---------------------------------------------------------------------------


class TestCostRepo:

    def test_record_then_aggregate_round_trip(self, db):
        record_cost_event(
            "whisper", "whisper-1", 6,
            shop_id=1, units_label="duration_ms", units_value=600_000,
            db_path=db,
        )
        record_cost_event(
            "claude_extraction", "claude-haiku-4-5", 3,
            shop_id=1, units_label="tokens", units_value=700,
            db_path=db,
        )
        rollup = aggregate_costs(db_path=db)
        assert rollup.total_usd_cents == 9
        assert rollup.event_count == 2
        assert rollup.by_kind == {"whisper": 6, "claude_extraction": 3}
        assert rollup.by_model == {"whisper-1": 6, "claude-haiku-4-5": 3}

    def test_aggregate_filters_by_shop(self, db):
        record_cost_event("whisper", "whisper-1", 10, shop_id=1, db_path=db)
        record_cost_event("whisper", "whisper-1", 20, shop_id=2, db_path=db)
        assert aggregate_costs(shop_id=1, db_path=db).total_usd_cents == 10
        assert aggregate_costs(shop_id=2, db_path=db).total_usd_cents == 20
        assert aggregate_costs(db_path=db).total_usd_cents == 30

    def test_aggregate_filters_by_since(self, db):
        record_cost_event("whisper", "whisper-1", 5, db_path=db)
        # An all-time query sees it; a far-future `since` excludes it.
        assert aggregate_costs(db_path=db).event_count == 1
        assert aggregate_costs(
            since="2099-01-01 00:00:00", db_path=db,
        ).event_count == 0

    def test_shop_cost_this_month(self, db):
        record_cost_event("whisper", "whisper-1", 7, shop_id=42, db_path=db)
        record_cost_event(
            "claude_extraction", "claude-haiku-4-5", 4,
            shop_id=42, db_path=db,
        )
        assert shop_cost_this_month(42, db_path=db) == 11
        assert shop_cost_this_month(99, db_path=db) == 0

    def test_transcript_id_fk_set_null_on_transcript_delete(self, db):
        # Bill a cost_events row against a transcript, hard-delete the
        # transcript — the cost row survives with transcript_id NULL
        # (ON DELETE SET NULL). The voice_transcripts row's OWN FKs
        # (work_order_id, uploaded_by_user_id) point at parent rows
        # this minimal test DB doesn't have, so the fixture insert
        # uses a raw connection with foreign_keys OFF; the cost_events
        # FK — the actual subject — is then exercised via
        # get_connection (foreign_keys ON).
        import sqlite3
        raw = sqlite3.connect(db)
        cur = raw.execute(
            """INSERT INTO voice_transcripts
               (work_order_id, audio_path, audio_size_bytes,
                audio_format, audio_sha256, duration_ms,
                captured_at, uploaded_by_user_id)
               VALUES (1, 'a.m4a', 100, 'm4a', 'sha', 5000,
                       '2026-05-16', 1)"""
        )
        tid = cur.lastrowid
        raw.commit()
        raw.close()

        eid = record_cost_event(
            "whisper", "whisper-1", 1, transcript_id=tid, db_path=db,
        )
        with get_connection(db) as conn:
            conn.execute(
                "DELETE FROM voice_transcripts WHERE id = ?", (tid,),
            )
        with get_connection(db) as conn:
            row = conn.execute(
                "SELECT transcript_id FROM cost_events WHERE id = ?",
                (eid,),
            ).fetchone()
        assert row["transcript_id"] is None


# ---------------------------------------------------------------------------
# 3. whisper_client
# ---------------------------------------------------------------------------


class TestWhisperClient:

    def test_cost_math_rounds_up(self):
        assert estimate_cost_usd_cents(30_000) == 1    # 0.5min × 0.6 → ceil
        assert estimate_cost_usd_cents(90_000) == 1    # 1.5min × 0.6 → ceil
        assert estimate_cost_usd_cents(600_000) == 6   # 10min × 0.6
        assert estimate_cost_usd_cents(0) == 0

    def test_cost_rate_constant(self):
        assert WHISPER_USD_CENTS_PER_MINUTE == 0.6

    def test_whisper_unavailable_without_key(self, db, monkeypatch):
        monkeypatch.setenv("MOTODIAG_OPENAI_API_KEY", "")
        reset_settings()
        assert whisper_available() is False

    def test_whisper_available_with_key(self, db, monkeypatch):
        monkeypatch.setenv("MOTODIAG_OPENAI_API_KEY", "sk-test-fake")
        reset_settings()
        assert whisper_available() is True
        reset_settings()

    def test_transcribe_raises_unavailable_without_key(self, db, monkeypatch):
        monkeypatch.setenv("MOTODIAG_OPENAI_API_KEY", "")
        reset_settings()
        with pytest.raises(WhisperUnavailableError):
            transcribe("/nonexistent.m4a")

    def test_transcribe_raises_transcription_error_on_missing_file(
        self, db, monkeypatch,
    ):
        # With a key set, the missing-file check fires before any API
        # call — surfaces as WhisperTranscriptionError.
        monkeypatch.setenv("MOTODIAG_OPENAI_API_KEY", "sk-test-fake")
        reset_settings()
        with pytest.raises(WhisperTranscriptionError):
            transcribe("/definitely/not/here.m4a")
        reset_settings()


# ---------------------------------------------------------------------------
# 4. costs report CLI
# ---------------------------------------------------------------------------


class TestCostsReportCLI:

    def test_costs_report_empty(self, db):
        from motodiag.cli.main import cli
        result = CliRunner().invoke(cli, ["costs", "report"])
        assert result.exit_code == 0
        assert "all-time" in result.output
        assert "0 call" in result.output

    def test_costs_report_with_events(self, db):
        record_cost_event("whisper", "whisper-1", 12, shop_id=1, db_path=db)
        record_cost_event(
            "claude_extraction", "claude-haiku-4-5", 8, shop_id=1,
            db_path=db,
        )
        from motodiag.cli.main import cli
        result = CliRunner().invoke(cli, ["costs", "report"])
        assert result.exit_code == 0
        assert "$0.20" in result.output       # 12 + 8 cents
        assert "whisper" in result.output
        assert "claude_extraction" in result.output

    def test_costs_report_bad_since_rejected(self, db):
        from motodiag.cli.main import cli
        result = CliRunner().invoke(
            cli, ["costs", "report", "--since", "not-a-date"],
        )
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# 5. F44 fold-in — port default moved 8080 → 8000
# ---------------------------------------------------------------------------


class TestF44PortFoldIn:

    def test_api_port_default_is_8000(self):
        assert Settings().api_port == 8000

    def test_api_servers_default_is_8000(self):
        servers = Settings().api_servers_list
        assert servers == [
            {"url": "http://localhost:8000", "description": "Local dev"},
        ]
