"""Phase 244L — vision costs reach the ledger.

A shop owner asked what a day of questions costs and there was no way to tell
them. Three reasons, only one of them a missing feature:

  1. `answer_question_about_frames` bound its usage to `_usage` and discarded
     it — Phase 244J shipped an endpoint spending a vision call per request
     that recorded nothing.
  2. `cost_events.kind` carried CHECK (kind IN ('whisper','claude_extraction')),
     so a vision cost could not be recorded even deliberately.
  3. `cost_events` had zero rows.
"""

import sqlite3

import pytest

from support.source_guards import code_of
from motodiag.core.database import init_db, SCHEMA_VERSION
from motodiag.core.migrations import (
    get_migration_by_version,
    rollback_to_version,
)
from motodiag.engine.client import MODEL_ALIASES
from motodiag.engine.models import TokenUsage
from motodiag.media import vision_analysis_pipeline as vap
from motodiag.media.vision_costs import (
    KIND_GUIDANCE,
    KIND_SWEEP,
    cost_usd_to_cents,
    record_vision_cost,
)
from motodiag.shop.cost_repo import aggregate_costs, record_cost_event

USAGE = TokenUsage(
    input_tokens=9000, output_tokens=1200,
    model=MODEL_ALIASES["sonnet"], cost_estimate=0.141099,
)


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "cost.db")
    init_db(path)
    # A real video for video_id=5 to reference. The FK is enforced, which the
    # first version of these tests discovered by failing — and that discovery
    # is why `record_vision_cost` now degrades to an unlinked row instead of
    # losing the charge.
    c = sqlite3.connect(path)
    c.execute("""INSERT INTO diagnostic_sessions (id, vehicle_make, vehicle_model,
                 vehicle_year, status) VALUES (1, 'Honda', 'CBR600F4i', 2001, 'open')""")
    c.execute("""INSERT INTO videos (id, session_id, started_at, duration_ms, width,
                 height, file_size_bytes, file_path, sha256)
                 VALUES (5, 1, '2026-01-01', 1000, 1, 1, 1, '/x', 'h')""")
    c.commit(); c.close()
    return path


def _rows(path):
    c = sqlite3.connect(path); c.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in c.execute("SELECT * FROM cost_events")]
    finally:
        c.close()


class TestTheLedgerAcceptsVision:
    def test_a_guidance_cost_is_recorded(self, db):
        assert record_vision_cost(USAGE, KIND_GUIDANCE, video_id=5, db_path=db)
        rows = _rows(db)
        assert len(rows) == 1
        assert rows[0]["kind"] == "vision_guidance"
        assert rows[0]["video_id"] == 5

    def test_a_sweep_cost_is_recorded(self, db):
        record_vision_cost(USAGE, KIND_SWEEP, video_id=5, db_path=db)
        assert _rows(db)[0]["kind"] == "vision_sweep"

    def test_the_two_kinds_stay_separate(self, db):
        """The question asked was what the QUESTIONS cost. One generic `vision`
        kind would average guidance into sweeps and lose exactly that."""
        record_vision_cost(USAGE, KIND_GUIDANCE, db_path=db)
        record_vision_cost(USAGE, KIND_SWEEP, db_path=db)
        assert {r["kind"] for r in _rows(db)} == {"vision_guidance", "vision_sweep"}

    def test_the_recorded_cents_match_the_usage(self, db):
        record_vision_cost(USAGE, KIND_GUIDANCE, db_path=db)
        assert _rows(db)[0]["cost_usd_cents"] == cost_usd_to_cents(0.141099) == 14

    def test_tokens_are_recorded_in_the_polymorphic_units_pair(self, db):
        record_vision_cost(USAGE, KIND_GUIDANCE, db_path=db)
        row = _rows(db)[0]
        assert row["units_label"] == "tokens"
        assert row["units_value"] == 10200

    def test_the_existing_kinds_still_validate(self, db):
        record_cost_event(kind="whisper", model="whisper-1", cost_usd_cents=3, db_path=db)
        record_cost_event(kind="claude_extraction", model="x", cost_usd_cents=1, db_path=db)
        assert len(_rows(db)) == 2

    def test_an_unknown_kind_is_still_rejected(self, db):
        """Widening the CHECK must not have removed it."""
        c = sqlite3.connect(db)
        with pytest.raises(sqlite3.IntegrityError):
            c.execute("INSERT INTO cost_events (kind, model, cost_usd_cents) "
                      "VALUES ('bogus', 'm', 1)")
        c.close()


class TestRoundingIsHalfUpBecauseItIsMoney:
    @pytest.mark.parametrize("usd,cents", [
        (0.141099, 14), (0.0, 0), (0.004, 0), (0.005, 1),
        (0.015, 2), (0.025, 3), (0.994, 99), (1.0, 100),
    ])
    def test_half_up(self, usd, cents):
        # 0.015 and 0.025 are the cases that separate half-up from Python's
        # builtin banker's rounding, which gave 2c for BOTH. Written with
        # round() first; the docstring said half-up while the code did
        # something else — an unexplainable few cents in a monthly report.
        assert cost_usd_to_cents(usd) == cents

    def test_a_negative_cost_is_zero_not_a_credit(self):
        assert cost_usd_to_cents(-1.0) == 0

    def test_it_does_not_use_the_builtin_round(self):
        src = code_of(cost_usd_to_cents)
        assert "ROUND_HALF_UP" in src
        assert "round(" not in src.replace("ROUND_HALF_UP", "")


class TestRecordingNeverCostsTheAnswer:
    """The money is spent before the ledger is touched. A bookkeeping failure
    must not lose a technician their answer."""

    def test_a_failed_write_returns_none_rather_than_raising(self, tmp_path):
        missing = str(tmp_path / "no_such_schema.db")
        sqlite3.connect(missing).close()  # exists, but has no cost_events
        assert record_vision_cost(USAGE, KIND_GUIDANCE, db_path=missing) is None

    def test_a_broken_video_link_still_records_the_charge(self, db):
        """The money was spent. A ledger that drops charges because a link
        broke is worse than one with a null link — found by these tests
        failing on the FK before the fallback existed."""
        assert record_vision_cost(USAGE, KIND_GUIDANCE, video_id=99999, db_path=db)
        rows = _rows(db)
        assert len(rows) == 1
        assert rows[0]["video_id"] is None
        assert rows[0]["cost_usd_cents"] == 14

    def test_no_usage_records_nothing_and_does_not_raise(self, db):
        assert record_vision_cost(None, KIND_GUIDANCE, db_path=db) is None
        assert _rows(db) == []


class TestBothVisionPathsRecord:
    def test_the_guidance_path_no_longer_discards_its_usage(self):
        """`_usage` is how the cost vanished: no warning, no lint, nothing."""
        src = code_of(vap.VisionAnalyzer.answer_question_about_frames)
        assert "_usage" not in src, "the usage is being discarded again"
        assert "record_vision_cost" in src

    def test_the_sweep_path_records_too(self):
        src = code_of(vap.VisionAnalyzer.analyze_video_frames)
        assert "record_vision_cost" in src

    def test_both_paths_share_one_choke_point(self):
        """Two call sites each remembering to record are two chances to
        forget, and forgetting is exactly what happened."""
        guidance = code_of(vap.VisionAnalyzer.answer_question_about_frames)
        sweep = code_of(vap.VisionAnalyzer.analyze_video_frames)
        for src in (guidance, sweep):
            assert "record_vision_cost" in src
            assert "INSERT INTO cost_events" not in src, "bypassed the helper"

    def test_they_record_under_different_kinds(self):
        assert "KIND_GUIDANCE" in code_of(vap.VisionAnalyzer.answer_question_about_frames)
        assert "KIND_SWEEP" in code_of(vap.VisionAnalyzer.analyze_video_frames)


class TestTheReportNeedsNoChanges:
    def test_aggregate_rolls_up_vision_kinds(self, db):
        for _ in range(3):
            record_vision_cost(USAGE, KIND_GUIDANCE, db_path=db)
        record_vision_cost(USAGE, KIND_SWEEP, db_path=db)
        roll = aggregate_costs(db_path=db)
        by_kind = getattr(roll, "by_kind", None) or roll.model_dump().get("by_kind", {})
        assert by_kind.get("vision_guidance") == 42
        assert by_kind.get("vision_sweep") == 14

    def test_guidance_spend_is_answerable_on_its_own(self, db):
        """The operator's actual question: what do the QUESTIONS cost."""
        for _ in range(5):
            record_vision_cost(USAGE, KIND_GUIDANCE, db_path=db)
        record_vision_cost(USAGE, KIND_SWEEP, db_path=db)
        roll = aggregate_costs(db_path=db)
        by_kind = getattr(roll, "by_kind", None) or roll.model_dump().get("by_kind", {})
        assert by_kind["vision_guidance"] == 70


class TestTheSchemaContract:
    def test_schema_version_is_current(self):
        assert SCHEMA_VERSION == 58  # f9-noqa: ssot-pin contract-pin: Phase 244L schema-bump pin. The literal is the point — importing the constant alone would make this assert x == x. Bumped 56→57 by migration 057 (cost_events accepts vision_sweep and vision_guidance). Bumping requires a corresponding new migration in src/motodiag/core/migrations.py. Bumped 57→58 at Phase 244M (migration 058 adds memory_facts, the per-machine compiled memory: keyed on vehicle_id and deliberately NOT on customer_id, because `customers` row 1 is the `Unassigned` sentinel that every vehicle row carries by DEFAULT, so a customer key would compile one memory holding every bike in the shop -- the exact cross-contamination the feature exists to prevent; fact_key is a UNIQUE hash that COALESCEs its nullable origin_id, because SQLite treats NULLs as DISTINCT and the naive form would let every re-compile duplicate).

    def test_the_rebuild_redeclares_every_index(self):
        """Phase 244D's lesson on this codebase's table rebuilds."""
        sql = get_migration_by_version(57).upgrade_sql
        for idx in ("idx_cost_events_created", "idx_cost_events_shop",
                    "idx_cost_events_kind"):
            assert f"CREATE INDEX {idx}" in sql, f"{idx} not recreated"

    def test_a_fresh_database_has_all_four_kinds(self, db):
        c = sqlite3.connect(db)
        sql = c.execute("SELECT sql FROM sqlite_master WHERE name='cost_events'").fetchone()[0]
        c.close()
        for kind in ("whisper", "claude_extraction", "vision_sweep", "vision_guidance"):
            assert kind in sql

    def test_a_ledger_row_survives_its_video_being_deleted(self, db):
        """ON DELETE SET NULL, matching how transcript_id already behaves —
        a financial record must outlive the thing it refers to."""
        # The fixture already seeded session 1 / video 5; this needs its own
        # video to delete without disturbing the others.
        c = sqlite3.connect(db)
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("""INSERT INTO videos (id, session_id, started_at, duration_ms, width,
                     height, file_size_bytes, file_path, sha256)
                     VALUES (7, 1, '2026-01-01', 1000, 1, 1, 1, '/x7', 'h7')""")
        c.commit(); c.close()

        record_vision_cost(USAGE, KIND_GUIDANCE, video_id=7, db_path=db)
        c = sqlite3.connect(db); c.execute("PRAGMA foreign_keys=ON")
        c.execute("DELETE FROM videos WHERE id = 7"); c.commit(); c.close()

        rows = _rows(db)
        assert len(rows) == 1, "the ledger row was deleted with the video"
        assert rows[0]["video_id"] is None
        assert rows[0]["cost_usd_cents"] == 14


class TestTheRollbackDoesNotDestroyTheLedger:
    """The first draft of 057's rollback was migration 043's, copied verbatim.

    043 CREATED `cost_events`, so dropping the table is the correct way to
    undo it. 057 only widened a CHECK -- dropping the table there destroys
    the whisper ledger 043 created and this migration merely edited. It was
    not caught by review: the two blocks are byte-identical, and a text
    search for the destructive statement returns two hits, only one of them
    a defect. It was caught by Phase 235B's fixture, which rolls back to 51
    and then found no table to read.
    """

    def test_rolling_back_preserves_rows_this_migration_did_not_create(self, db):
        c = sqlite3.connect(db)
        c.execute(
            "INSERT INTO cost_events (kind, model, cost_usd_cents) "
            "VALUES ('whisper', 'whisper-1', 42)"
        )
        c.commit(); c.close()

        record_vision_cost(USAGE, KIND_GUIDANCE, db_path=db)
        rollback_to_version(51, db_path=db)

        rows = _rows(db)
        assert [r["kind"] for r in rows] == ["whisper"], (
            "the pre-existing ledger must survive a rollback of a migration "
            "that only widened a CHECK"
        )
        assert rows[0]["cost_usd_cents"] == 42

    def test_rolling_back_narrows_the_check_again(self, db):
        rollback_to_version(51, db_path=db)
        c = sqlite3.connect(db)
        try:
            with pytest.raises(sqlite3.IntegrityError):
                c.execute(
                    "INSERT INTO cost_events (kind, model, cost_usd_cents) "
                    "VALUES ('vision_sweep', 'x', 1)"
                )
        finally:
            c.close()

    def test_rolling_back_drops_the_column_it_added(self, db):
        rollback_to_version(51, db_path=db)
        c = sqlite3.connect(db)
        cols = [r[1] for r in c.execute("PRAGMA table_info(cost_events)")]
        c.close()
        # `cols` is EMPTY for a dropped table, which made the absence check
        # below pass against the destructive rollback. Assert the table is
        # there first, or this guard tests nothing.
        assert cols, "cost_events does not exist after rollback"
        assert "video_id" not in cols

    def test_the_rollback_redeclares_every_index_too(self, db):
        """The upgrade guard checked `upgrade_sql` only, so a rollback that
        rebuilt the table without its indexes would have passed it."""
        rollback_to_version(51, db_path=db)
        c = sqlite3.connect(db)
        idx = {
            r[0]
            for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='index' "
                "AND tbl_name='cost_events' AND name NOT LIKE 'sqlite_%'"
            )
        }
        c.close()
        assert idx == {
            "idx_cost_events_created",
            "idx_cost_events_shop",
            "idx_cost_events_kind",
        }

    def test_the_rollback_is_not_migration_043s(self):
        """Pins the distinction rather than the text: 043 may drop the table
        because it created it; 057 may not, because it did not."""
        assert "DROP TABLE IF EXISTS cost_events" in get_migration_by_version(43).rollback_sql
        assert "DROP TABLE IF EXISTS cost_events" not in get_migration_by_version(57).rollback_sql
