"""Phase 244N — stop discarding what already happens.

Three streams of exactly the data this product needs passed through it daily
and were dropped at the end of the request. This file guards the capture of all
three, and one property that outranks the rest:

``TestRecordNeverLabel`` — there is no outcome, verdict, correct or score
column anywhere in this phase, and that is a decision rather than an omission.
A finding nobody acted on is *unresolved*, not *wrong*. A nullable outcome
column invites a default, and a default fabricates negatives that nothing
downstream could later detect. Interpretation belongs to a phase that can be
judged on it, against data this phase keeps honest.

The other property worth reading first is that **capture never costs the thing
being captured**. Every write here is wrapped and swallowed, and every guard
below asserts the request still succeeds when capture raises.
"""

from __future__ import annotations

import json
import sqlite3
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from support.source_guards import code_of

from motodiag.api import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.capture import (
    capture_session_overrides,
    capture_stats,
    current_analysis,
    list_analyses,
    list_interactions,
    record_analysis,
    record_guidance_interaction,
)
from motodiag.capture import analyses as analyses_mod
from motodiag.capture import guidance_log as guidance_mod
from motodiag.capture import overrides as overrides_mod
from motodiag.core.database import SCHEMA_VERSION, get_connection, init_db
from motodiag.core.migrations import get_migration_by_version, rollback_to_version
from motodiag.core.session_repo import create_session_for_owner
from motodiag.core.video_repo import set_analysis_findings
from motodiag.media.vision_types import GuidanceCandidate, GuidanceResponse, Grounding

VEHICLE = 10


def _answer(answered: bool = True) -> GuidanceResponse:
    return GuidanceResponse(
        question_understood_as="Where is the oil coming from?",
        answers_the_question=answered,
        candidates=[
            GuidanceCandidate(
                candidate="Clutch cover gasket",
                why_plausible="Wet film below the cover, dry above",
                how_to_discriminate="Clean and run; refill from the cover seam",
                grounding=Grounding.MACHINE_SPECIFIC,
            ),
            GuidanceCandidate(
                candidate="Stator cover seal",
                why_plausible="Adjacent seam, similar run pattern",
                how_to_discriminate="Check the lower seam after a cold start",
                grounding=Grounding.CROSS_PLATFORM,
            ),
        ],
        what_would_narrow_it=["Clean the area and re-run for five minutes"],
        not_established="Whether the leak is pressurised",
        observation_basis="Frames 4-9 show a wet film on the left case",
    )


@pytest.fixture
def db(tmp_path, monkeypatch):
    """A shop with one machine and one real customer.

    `reset_settings()` is not optional here. `get_settings` is an lru_cache of
    size 1, so without it `create_app()` keeps whatever path a previous test
    cached and the API reads a different database than the fixture wrote --
    which surfaces as "no such table: api_keys" from inside the auth
    middleware, several layers from the cause.
    """
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "capture.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("MOTODIAG_DATA_DIR", str(tmp_path))
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()
    c = sqlite3.connect(path)
    c.execute(
        "INSERT INTO vehicles (id, make, model, year, customer_id) "
        "VALUES (?, 'Honda', 'CBR600F4i', 2001, 1)",
        (VEHICLE,),
    )
    c.execute("INSERT INTO customers (id, name) VALUES (2, 'Dana Reyes')")
    c.commit()
    c.close()
    yield path
    reset_settings()


def _user(db_path, username="tech"):
    with get_connection(db_path) as conn:
        return int(
            conn.execute(
                "INSERT INTO users (username, email, tier, is_active) "
                "VALUES (?, ?, 'shop', 1)",
                (username, f"{username}@example.com"),
            ).lastrowid
        )


def _ai_session(db_path, uid, *, ai=True) -> int:
    sid = create_session_for_owner(
        owner_user_id=uid, vehicle_make="Honda", vehicle_model="CBR600F4i",
        vehicle_year=2001, db_path=db_path,
    )
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE diagnostic_sessions SET vehicle_id = ?, diagnosis = ?, "
            "confidence = ?, severity = ?, ai_model_used = ? WHERE id = ?",
            (VEHICLE, "Cam chain tensioner", 0.8, "high",
             "claude-sonnet" if ai else None, sid),
        )
    return sid


# ---------------------------------------------------------------------------


class TestRecordNeverLabel:
    """The property that outranks the rest.

    A finding nobody acted on is unresolved, not wrong -- it may have been
    right and deprioritised, or right and fixed without paperwork. If absence
    of evidence becomes a negative label, every statistic computed on this data
    later rests on invented negatives and nothing can detect it.
    """

    def test_no_outcome_column_exists_in_the_migration(self):
        sql = get_migration_by_version(59).upgrade_sql.lower()
        for banned in ("outcome", "verdict", "correct", "score", "was_right"):
            assert banned not in sql, (
                f"migration 059 declares a `{banned}` column — this phase "
                "records and does not label"
            )

    def test_no_outcome_column_exists_in_the_database(self, db):
        with get_connection(db) as conn:
            for table in ("guidance_interactions", "video_analyses"):
                cols = [
                    r[1] for r in conn.execute(f"PRAGMA table_info({table})")
                ]
                for banned in ("outcome", "verdict", "correct", "score"):
                    assert not any(banned in c.lower() for c in cols), (
                        f"{table}.{banned} exists"
                    )

    @pytest.mark.parametrize(
        "module", [guidance_mod, analyses_mod, overrides_mod]
    )
    def test_no_module_writes_a_judgement(self, module):
        src = code_of(module).lower()
        for banned in ("outcome", "verdict", "is_correct", "was_right"):
            assert banned not in src, f"{banned} in {module.__name__}"


class TestGuidanceInteractionsArePersisted:
    def test_one_call_writes_one_row(self, db):
        rid = record_guidance_interaction(
            "where is the oil coming from?", _answer(),
            video_id=None, vehicle_id=VEHICLE, db_path=db,
        )
        assert rid is not None
        rows = list_interactions(vehicle_id=VEHICLE, db_path=db)
        assert len(rows) == 1

    def test_the_response_round_trips(self, db):
        original = _answer()
        record_guidance_interaction("q", original, vehicle_id=VEHICLE, db_path=db)
        stored = list_interactions(vehicle_id=VEHICLE, db_path=db)[0]["response"]
        assert GuidanceResponse(**stored) == original, (
            "the stored JSON must reconstruct the answer that was given"
        )

    def test_the_candidates_survive_with_their_grounding(self, db):
        record_guidance_interaction("q", _answer(), vehicle_id=VEHICLE, db_path=db)
        stored = list_interactions(vehicle_id=VEHICLE, db_path=db)[0]
        cands = stored["response"]["candidates"]
        assert len(cands) == 2
        assert cands[0]["grounding"] == "machine_specific"
        assert cands[0]["how_to_discriminate"]

    def test_answers_the_question_is_a_column_not_a_json_scan(self, db):
        """'How often can it not answer what was asked' is the most
        interesting question anyone will ask of this table."""
        record_guidance_interaction("a", _answer(True), vehicle_id=VEHICLE, db_path=db)
        record_guidance_interaction("b", _answer(False), vehicle_id=VEHICLE, db_path=db)
        with get_connection(db) as conn:
            unanswered = conn.execute(
                "SELECT COUNT(*) FROM guidance_interactions "
                "WHERE answers_the_question = 0"
            ).fetchone()[0]
        assert unanswered == 1

    def test_the_question_is_stored_verbatim(self, db):
        q = "why is it running lean ONLY above 6k?"
        record_guidance_interaction(q, _answer(), vehicle_id=VEHICLE, db_path=db)
        assert list_interactions(vehicle_id=VEHICLE, db_path=db)[0]["question"] == q

    def test_candidate_count_is_promoted(self, db):
        record_guidance_interaction("q", _answer(), vehicle_id=VEHICLE, db_path=db)
        assert list_interactions(vehicle_id=VEHICLE, db_path=db)[0]["candidate_count"] == 2

    def test_a_plain_dict_is_accepted(self, db):
        assert record_guidance_interaction(
            "q", {"answers_the_question": True, "candidates": []},
            vehicle_id=VEHICLE, db_path=db,
        ) is not None

    def test_a_broken_video_link_does_not_lose_the_interaction(self, db):
        """A dangling FK must not cost the record. Same contract as 244L."""
        rid = record_guidance_interaction(
            "q", _answer(), video_id=99999, vehicle_id=VEHICLE, db_path=db,
        )
        # Either it recorded, or it declined -- but it must never raise, and
        # the caller must never see an exception for a logging concern.
        assert rid is None or isinstance(rid, int)

    def test_an_unserialisable_response_does_not_raise(self, db):
        assert record_guidance_interaction("q", object(), db_path=db) is None

    def test_a_broken_database_does_not_raise(self, tmp_path):
        assert record_guidance_interaction(
            "q", _answer(), db_path=str(tmp_path / "nope.db"),
        ) is None


class TestOverrideCapture:
    """`session_overrides` has stored (field_name, ai_value, override_value)
    since Phase 116 and had no caller, while PATCH overwrote AI-authored
    diagnoses and discarded the prior value."""

    def test_a_correction_is_recorded(self, db):
        uid = _user(db)
        sid = _ai_session(db, uid)
        before = {"diagnosis": "Cam chain tensioner", "ai_model_used": "claude-sonnet"}
        written = capture_session_overrides(
            sid, before, {"diagnosis": "Split intake boot"}, db_path=db,
        )
        assert written == 1

    def test_it_carries_the_prior_value(self, db):
        uid = _user(db)
        sid = _ai_session(db, uid)
        capture_session_overrides(
            sid,
            {"diagnosis": "Cam chain tensioner", "ai_model_used": "claude-sonnet"},
            {"diagnosis": "Split intake boot"},
            db_path=db,
        )
        with get_connection(db) as conn:
            row = conn.execute(
                "SELECT field_name, ai_value, override_value FROM session_overrides"
            ).fetchone()
        assert row[0] == "diagnosis"
        assert row[1] == "Cam chain tensioner", "the AI's value must be preserved"
        assert row[2] == "Split intake boot"

    def test_a_no_op_records_nothing(self, db):
        uid = _user(db)
        sid = _ai_session(db, uid)
        written = capture_session_overrides(
            sid,
            {"diagnosis": "Cam chain tensioner", "ai_model_used": "claude-sonnet"},
            {"diagnosis": "Cam chain tensioner"},
            db_path=db,
        )
        assert written == 0, "sending the same value is not a correction"

    def test_a_numeric_no_op_records_nothing(self, db):
        """SQLite hands back 0.8 or '0.8' depending on affinity."""
        uid = _user(db)
        sid = _ai_session(db, uid)
        written = capture_session_overrides(
            sid, {"confidence": "0.8", "ai_model_used": "m"},
            {"confidence": 0.8}, db_path=db,
        )
        assert written == 0

    def test_a_session_with_no_ai_author_records_nothing(self, db):
        """Recording (NULL -> 'x') as an override would fill the table with
        ordinary data entry and ruin every statistic drawn from it."""
        uid = _user(db)
        sid = _ai_session(db, uid, ai=False)
        written = capture_session_overrides(
            sid, {"diagnosis": "typed by hand", "ai_model_used": None},
            {"diagnosis": "changed by hand"}, db_path=db,
        )
        assert written == 0

    def test_several_fields_record_several_rows(self, db):
        uid = _user(db)
        sid = _ai_session(db, uid)
        written = capture_session_overrides(
            sid,
            {"diagnosis": "a", "confidence": 0.8, "severity": "high",
             "ai_model_used": "m"},
            {"diagnosis": "b", "confidence": 0.4, "severity": "low"},
            db_path=db,
        )
        assert written == 3

    def test_status_is_not_captured(self, db):
        """Open -> closed is workflow, not a correction."""
        uid = _user(db)
        sid = _ai_session(db, uid)
        written = capture_session_overrides(
            sid, {"status": "open", "ai_model_used": "m"},
            {"status": "closed"}, db_path=db,
        )
        assert written == 0

    def test_every_captured_field_is_a_valid_override_field(self):
        from motodiag.feedback.models import OverrideField

        for field in overrides_mod.CAPTURED_FIELDS:
            OverrideField(field)

    def test_a_broken_write_does_not_raise(self, db):
        uid = _user(db)
        sid = _ai_session(db, uid)
        with mock.patch(
            "motodiag.feedback.feedback_repo.record_override",
            side_effect=RuntimeError("boom"),
        ):
            assert capture_session_overrides(
                sid, {"diagnosis": "a", "ai_model_used": "m"},
                {"diagnosis": "b"}, db_path=db,
            ) == 0


class TestTheCaptureNeverCostsTheRequest:
    """A capture write that fails a technician's edit has traded the thing
    that matters for the thing that might matter later."""

    def test_a_failing_override_capture_does_not_fail_the_patch(self, db):
        uid = _user(db)
        sid = _ai_session(db, uid)
        _, key = create_api_key(uid, db_path=db)
        client = TestClient(create_app())

        with mock.patch(
            "motodiag.api.routes.sessions.capture_session_overrides",
            side_effect=RuntimeError("capture exploded"),
        ):
            resp = client.patch(
                f"/v1/sessions/{sid}",
                json={"diagnosis": "Split intake boot"},
                headers={"X-API-Key": key},
            )
        assert resp.status_code == 200, (
            "the technician's edit must survive a capture failure"
        )
        with get_connection(db) as conn:
            stored = conn.execute(
                "SELECT diagnosis FROM diagnostic_sessions WHERE id = ?", (sid,)
            ).fetchone()[0]
        assert stored == "Split intake boot", "the edit actually applied"

    def test_a_failing_analysis_history_write_does_not_fail_the_analysis(self, db):
        with get_connection(db) as conn:
            conn.execute(
                "INSERT INTO diagnostic_sessions (id, vehicle_id, vehicle_make, "
                "vehicle_model, vehicle_year, status) "
                "VALUES (1, ?, 'Honda', 'CBR', 2001, 'open')", (VEHICLE,),
            )
            conn.execute(
                "INSERT INTO videos (id, session_id, started_at, duration_ms, "
                "width, height, file_size_bytes, file_path, sha256) "
                "VALUES (1, 1, '2026-01-01', 1, 1, 1, 1, '/x', 'h')"
            )
        with mock.patch(
            "motodiag.capture.analyses.record_analysis",
            side_effect=RuntimeError("boom"),
        ):
            assert set_analysis_findings(
                1, {"findings": []}, db_path=db,
            ) is True, "the analysis still persists"


class TestTheApiRecordsWhatItAnswers:
    def test_patch_through_the_api_writes_an_override(self, db):
        uid = _user(db)
        sid = _ai_session(db, uid)
        _, key = create_api_key(uid, db_path=db)
        client = TestClient(create_app())

        resp = client.patch(
            f"/v1/sessions/{sid}",
            json={"diagnosis": "Split intake boot"},
            headers={"X-API-Key": key},
        )
        assert resp.status_code == 200
        with get_connection(db) as conn:
            rows = conn.execute(
                "SELECT field_name, ai_value, override_value FROM session_overrides"
            ).fetchall()
        assert len(rows) == 1, "the hook fires on the real request path"
        assert rows[0][1] == "Cam chain tensioner"
        assert rows[0][2] == "Split intake boot"

    def test_a_patch_that_changes_nothing_writes_no_override(self, db):
        uid = _user(db)
        sid = _ai_session(db, uid)
        _, key = create_api_key(uid, db_path=db)
        client = TestClient(create_app())
        client.patch(
            f"/v1/sessions/{sid}",
            json={"diagnosis": "Cam chain tensioner"},
            headers={"X-API-Key": key},
        )
        with get_connection(db) as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM session_overrides"
            ).fetchone()[0] == 0

    def test_the_ask_route_resolves_the_vehicle_from_the_session(self, db):
        """`videos` carries session_id and NOT vehicle_id. The first draft read
        row["vehicle_id"] and would have written NULL on every interaction --
        which silently breaks erasure, since that resolves customer ->
        vehicles -> interactions."""
        from motodiag.api.routes.videos import _vehicle_id_for_session

        with get_connection(db) as conn:
            conn.execute(
                "INSERT INTO diagnostic_sessions (id, vehicle_id, vehicle_make, "
                "vehicle_model, vehicle_year, status) "
                "VALUES (7, ?, 'Honda', 'CBR', 2001, 'open')", (VEHICLE,),
            )
        assert _vehicle_id_for_session(7, db) == VEHICLE

    def test_the_ask_route_calls_the_recorder(self):
        from motodiag.api.routes import videos as videos_mod

        src = code_of(videos_mod)
        assert "record_guidance_interaction(" in src, (
            "the /ask endpoint must persist its interaction"
        )


class TestAnalysisHistory:
    @pytest.fixture
    def video(self, db):
        with get_connection(db) as conn:
            conn.execute(
                "INSERT INTO diagnostic_sessions (id, vehicle_id, vehicle_make, "
                "vehicle_model, vehicle_year, status) "
                "VALUES (1, ?, 'Honda', 'CBR', 2001, 'open')", (VEHICLE,),
            )
            conn.execute(
                "INSERT INTO videos (id, session_id, started_at, duration_ms, "
                "width, height, file_size_bytes, file_path, sha256) "
                "VALUES (1, 1, '2026-01-01', 1, 1, 1, 1, '/x', 'h')"
            )
        return 1

    def test_re_analysis_preserves_the_prior_sweep(self, db, video):
        """Commit d2c23f8 exists because a sweep had to be rescued into git by
        hand before a re-run. This is that scenario."""
        set_analysis_findings(
            video, {"findings": [{"description": "original leak"}]}, db_path=db,
        )
        set_analysis_findings(
            video, {"findings": [{"description": "re-run"}]}, db_path=db,
        )
        history = list_analyses(video, db_path=db)
        assert len(history) == 2
        old = [a for a in history if a["superseded_at"]]
        assert len(old) == 1
        assert old[0]["findings"]["findings"][0]["description"] == "original leak"

    def test_exactly_one_analysis_is_current(self, db, video):
        for i in range(4):
            set_analysis_findings(
                video, {"findings": [{"description": f"run {i}"}]}, db_path=db,
            )
        history = list_analyses(video, db_path=db)
        assert len(history) == 4
        assert sum(1 for a in history if a["superseded_at"] is None) == 1

    def test_current_analysis_is_the_newest(self, db, video):
        set_analysis_findings(video, {"findings": [{"description": "old"}]}, db_path=db)
        set_analysis_findings(video, {"findings": [{"description": "new"}]}, db_path=db)
        cur = current_analysis(video, db_path=db)
        assert cur["findings"]["findings"][0]["description"] == "new"

    def test_the_videos_column_still_holds_the_current_sweep(self, db, video):
        """244M's compile, the API and the reports all read this column. It
        must keep working in exactly the shape it had."""
        set_analysis_findings(video, {"findings": [{"description": "old"}]}, db_path=db)
        set_analysis_findings(video, {"findings": [{"description": "new"}]}, db_path=db)
        with get_connection(db) as conn:
            blob = conn.execute(
                "SELECT analysis_findings FROM videos WHERE id = ?", (video,)
            ).fetchone()[0]
        assert json.loads(blob)["findings"][0]["description"] == "new"

    def test_deleting_a_video_cascades_its_analyses(self, db, video):
        set_analysis_findings(video, {"findings": []}, db_path=db)
        with get_connection(db) as conn:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("DELETE FROM videos WHERE id = ?", (video,))
        assert list_analyses(video, db_path=db) == []

    def test_record_analysis_on_a_broken_database_does_not_raise(self, tmp_path):
        assert record_analysis(1, "{}", db_path=str(tmp_path / "nope.db")) is None


class TestErasureCoversTheNewStreams:
    def test_forget_erases_guidance_interactions(self, db):
        from motodiag.memory import attach_vehicle, erase_customer

        attach_vehicle(VEHICLE, 2, db_path=db)
        record_guidance_interaction("q", _answer(), vehicle_id=VEHICLE, db_path=db)
        assert erase_customer(2, db_path=db) >= 1
        assert list_interactions(vehicle_id=VEHICLE, db_path=db) == []

    def test_the_dry_run_counts_what_the_delete_removes(self, db):
        """A preview that undercounts is a lie in exactly the situation it
        exists to prevent."""
        from motodiag.memory import attach_vehicle, erase_customer, erase_plan

        attach_vehicle(VEHICLE, 2, db_path=db)
        record_guidance_interaction("q1", _answer(), vehicle_id=VEHICLE, db_path=db)
        record_guidance_interaction("q2", _answer(), vehicle_id=VEHICLE, db_path=db)
        planned = erase_plan(2, db_path=db).fact_count
        assert erase_customer(2, db_path=db) == planned


class TestStats:
    def test_counts_are_real(self, db):
        record_guidance_interaction("a", _answer(True), vehicle_id=VEHICLE, db_path=db)
        record_guidance_interaction("b", _answer(False), vehicle_id=VEHICLE, db_path=db)
        s = capture_stats(db_path=db)
        assert s["guidance_interactions"] == 2
        assert s["guidance_answered"] == 1
        assert s["guidance_unanswered"] == 1

    def test_the_denominators_are_reported(self, db):
        """A capture count alone cannot say whether capture works: 0 overrides
        against 0 AI-authored sessions is nothing to correct, 0 against 40 is a
        broken hook."""
        uid = _user(db)
        _ai_session(db, uid)
        s = capture_stats(db_path=db)
        assert s["sessions_ai_authored"] == 1
        assert s["session_overrides"] == 0


class TestTheSchemaContract:
    def test_schema_version_is_current(self):
        assert SCHEMA_VERSION == 59  # f9-noqa: ssot-pin contract-pin: Phase 244N schema-bump pin. The literal is the point — importing the constant would make this assert x == x. Bumped 58→59 by migration 059 (guidance_interactions + video_analyses). NOTE: tests/test_phase191b_serve_migrations.py pins this as `get_current_version(db_path) == N`, NOT `SCHEMA_VERSION == N`, so grepping for this form alone MISSES it — that is exactly how it was missed at 244M.

    def test_the_migration_declares_every_index(self, db):
        with get_connection(db) as conn:
            idx = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' "
                    "AND tbl_name IN ('guidance_interactions','video_analyses') "
                    "AND name NOT LIKE 'sqlite_%'"
                )
            }
        assert idx == {
            "idx_guidance_interactions_vehicle",
            "idx_guidance_interactions_video",
            "idx_guidance_interactions_created",
            "idx_guidance_interactions_answered",
            "idx_video_analyses_video",
            "idx_video_analyses_current",
        }

    def test_the_migration_backfills_existing_sweeps(self, db):
        """Adding a table whose purpose is to stop dropping sweeps, while
        dropping the sweeps already recorded, would be its own joke."""
        with get_connection(db) as conn:
            conn.execute(
                "INSERT INTO diagnostic_sessions (id, vehicle_id, vehicle_make, "
                "vehicle_model, vehicle_year, status) "
                "VALUES (1, ?, 'Honda', 'CBR', 2001, 'open')", (VEHICLE,),
            )
            conn.execute(
                "INSERT INTO videos (id, session_id, started_at, duration_ms, "
                "width, height, file_size_bytes, file_path, sha256, "
                "analysis_findings, analyzed_at) "
                "VALUES (1, 1, '2026-01-01', 1, 1, 1, 1, '/x', 'h', ?, '2026-01-02')",
                (json.dumps({"findings": [{"description": "pre-existing"}]}),),
            )
        # Roll 059 back properly rather than deleting its version row: the
        # first draft did the latter and re-applying hit "table already
        # exists", which is the migration machinery correctly objecting to
        # being lied to about what had been applied.
        rollback_to_version(58, db_path=db)
        init_db(db)  # re-applies 059, backfilling from the videos column
        history = list_analyses(1, db_path=db)
        assert len(history) == 1
        assert history[0]["findings"]["findings"][0]["description"] == "pre-existing"

    def test_rolling_back_059_destroys_nothing_it_did_not_create(self, db):
        record_guidance_interaction("q", _answer(), vehicle_id=VEHICLE, db_path=db)
        rollback_to_version(58, db_path=db)
        with get_connection(db) as conn:
            names = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        assert "guidance_interactions" not in names
        assert "video_analyses" not in names
        for survivor in (
            "videos", "vehicles", "customers", "diagnostic_sessions",
            "session_overrides", "diagnostic_feedback", "memory_facts",
            "cost_events",
        ):
            assert survivor in names, f"{survivor} must survive a 059 rollback"

    def test_the_videos_column_survives_the_rollback(self, db):
        with get_connection(db) as conn:
            conn.execute(
                "INSERT INTO diagnostic_sessions (id, vehicle_id, vehicle_make, "
                "vehicle_model, vehicle_year, status) "
                "VALUES (1, ?, 'Honda', 'CBR', 2001, 'open')", (VEHICLE,),
            )
            conn.execute(
                "INSERT INTO videos (id, session_id, started_at, duration_ms, "
                "width, height, file_size_bytes, file_path, sha256) "
                "VALUES (1, 1, '2026-01-01', 1, 1, 1, 1, '/x', 'h')"
            )
        set_analysis_findings(1, {"findings": [{"description": "kept"}]}, db_path=db)
        rollback_to_version(58, db_path=db)
        with get_connection(db) as conn:
            blob = conn.execute(
                "SELECT analysis_findings FROM videos WHERE id = 1"
            ).fetchone()[0]
        assert json.loads(blob)["findings"][0]["description"] == "kept", (
            "the column is not this migration's to destroy"
        )


class TestPassiveMeansNoNewSurface:
    def test_there_is_no_capture_record_command(self):
        """If a human has to run something, the capture was not passive — and
        a capture that is not passive is the one that sat at zero rows for
        nine phases."""
        from motodiag.cli.capture import capture as group

        assert set(group.commands) == {
            "stats", "interactions", "overrides", "analyses",
        }, "capture is read-only; recording happens as a byproduct"
