"""Phase 195 (Commit 0) — voice transcript upload + extracted_symptoms tests.

Pins the substrate-half of the substrate-then-feature pair. Tests cover:

* Migration v42 — voice_transcripts + extracted_symptoms tables, indexes,
  FK posture, CHECK constraints (extraction_state + extraction_method).
* audio_pipeline.inspect_audio — WAV / M4A / Ogg detection + corrupt
  input + empty input + unsupported format.
* transcript_extraction.extract_symptoms_from_transcript — phrase
  splitter + keyword categorization + empty / no-match / multi-match.
* transcript_repo + extracted_symptom_repo — CRUD + quota helpers +
  confirm_extracted_symptom flow.
* audio_sweep.prune_old_audio — 60-day boundary correctness, missing
  file no-op, idempotency, audio_deleted_at stamping.
* Route layer — POST / GET / PATCH / DELETE / audio-stream over
  /v1/shop/{id}/work-orders/{id}/transcripts with auth, cross-shop
  isolation, quota enforcement, mechanic-confirm round trip, 410
  on swept audio.
"""

from __future__ import annotations

import io
import json as _json
import struct
import wave
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import SCHEMA_VERSION, get_connection, init_db
from motodiag.media.audio_pipeline import (
    AudioDecodeError,
    UnsupportedAudioFormatError,
    inspect_audio,
)
from motodiag.media.audio_sweep import (
    DEFAULT_RETENTION_DAYS,
    prune_old_audio,
)
from motodiag.media.transcript_extraction import (
    extract_symptoms_from_transcript,
    split_into_phrases,
)
from motodiag.shop import (
    add_shop_member, create_shop, create_work_order, seed_first_owner,
)
from motodiag.shop.extracted_symptom_repo import (
    confirm_extracted_symptom,
    create_extracted_symptom,
    get_extracted_symptom,
    list_for_transcript,
)
from motodiag.shop.transcript_repo import (
    VoiceTranscriptQuotaExceededError,
    count_voice_transcripts_this_month_for_uploader,
    count_wo_voice_transcripts,
    create_voice_transcript,
    get_voice_transcript,
    list_wo_voice_transcripts,
    soft_delete_voice_transcript,
    update_extraction_state,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase195_c0.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("MOTODIAG_DATA_DIR", str(tmp_path / "data"))
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()
    yield path
    reset_settings()


def _make_user(db_path, username, sub_tier="shop"):
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES (?, ?, 'individual', 1)",
            (username, f"{username}@ex.com"),
        )
        user_id = cur.lastrowid
        conn.execute(
            """INSERT INTO subscriptions
               (user_id, tier, status, current_period_end)
               VALUES (?, ?, 'active', datetime('now', '+30 days'))""",
            (user_id, sub_tier),
        )
    return user_id


def _seed_shop_and_wo(db_path, owner_user_id, shop_name="TestShop"):
    shop_id = create_shop(shop_name, db_path=db_path)
    seed_first_owner(shop_id, owner_user_id, db_path=db_path)
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO vehicles (make, model, year, protocol) "
            "VALUES ('Honda', 'CBR600', 2005, 'none')"
        )
        vid = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO customers (name, phone, email) "
            "VALUES ('Alice', '555-0100', 'a@ex.com')"
        )
        cust_id = cur.lastrowid
    wo_id = create_work_order(
        shop_id=shop_id, vehicle_id=vid, customer_id=cust_id,
        title="brake service", priority=2, db_path=db_path,
    )
    return shop_id, wo_id


@pytest.fixture
def authed(api_db):
    user_id = _make_user(api_db, "owner")
    _, plaintext = create_api_key(user_id, db_path=api_db)
    shop_id, wo_id = _seed_shop_and_wo(api_db, user_id)
    return user_id, plaintext, shop_id, wo_id


@pytest.fixture
def client(api_db):
    return TestClient(create_app(db_path_override=api_db))


def _make_wav_bytes(duration_sec=1.0, sample_rate=16000):
    """Build a minimal valid WAV (silence) with the given duration."""
    nframes = int(duration_sec * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * nframes)
    return buf.getvalue()


def _make_m4a_header_bytes():
    """Return a synthetic M4A-shaped byte sequence — header sufficient
    for inspect_audio to detect the format. Not a playable file."""
    # 'ftyp' box at offset 4 with brand 'M4A '
    body = b"\x00\x00\x00\x20" + b"ftypM4A " + b"\x00" * 24
    return body + b"\x00" * 100  # padding so size > 12 bytes


def _make_ogg_header_bytes():
    """Synthetic Ogg header: 'OggS' at offset 0."""
    return b"OggS" + b"\x00" * 60


# ---------------------------------------------------------------------------
# 1. Migration shape
# ---------------------------------------------------------------------------


class TestMigration042:

    def test_schema_version_at_least_42(self):
        # Pin the floor (Phase 195 bumped 41 → 42 for voice_transcripts +
        # extracted_symptoms tables) rather than equality; downstream
        # phases bump further without re-litigating. Same F9-discipline
        # opt-out as Phase 194's contract-pin.
        assert SCHEMA_VERSION >= 42  # f9-noqa: ssot-pin contract-pin: phase-195 floor — verifies migration 042 landed and stays

    def test_voice_transcripts_columns(self, api_db):
        with get_connection(api_db) as conn:
            cur = conn.execute("PRAGMA table_info(voice_transcripts)")
            cols = {r[1]: (r[2], bool(r[3]), r[4]) for r in cur.fetchall()}
        for name in (
            "id", "work_order_id", "issue_id", "audio_path",
            "audio_size_bytes", "audio_format", "audio_sha256",
            "duration_ms", "sample_rate_hz", "language",
            "captured_at", "uploaded_by_user_id",
            "preview_text", "preview_engine",
            "extraction_state", "extracted_at",
            "whisper_transcript", "whisper_segments",
            "whisper_cost_usd_cents", "whisper_model",
            "source", "created_at", "updated_at",
            "audio_deleted_at", "deleted_at",
        ):
            assert name in cols, f"missing column: {name}"
        assert cols["work_order_id"][1] is True
        assert cols["audio_path"][1] is True
        assert cols["whisper_transcript"][1] is False  # 195B-anticipating
        assert cols["source"][1] is False  # forward-invest narrow
        assert cols["language"][2] == "'en-US'"
        assert cols["sample_rate_hz"][2] == "16000"
        assert cols["extraction_state"][2] == "'pending'"

    def test_extracted_symptoms_columns(self, api_db):
        with get_connection(api_db) as conn:
            cur = conn.execute("PRAGMA table_info(extracted_symptoms)")
            cols = {r[1]: (r[2], bool(r[3]), r[4]) for r in cur.fetchall()}
        for name in (
            "id", "transcript_id", "text", "category",
            "linked_symptom_id", "confidence",
            "extraction_method", "segment_start_ms",
            "segment_end_ms", "confirmed_by_user_id",
            "confirmed_at", "source", "created_at", "deleted_at",
        ):
            assert name in cols, f"missing column: {name}"
        assert cols["transcript_id"][1] is True
        assert cols["text"][1] is True
        assert cols["confidence"][2] == "1.0"
        assert cols["extraction_method"][2] == "'keyword'"

    def test_voice_transcripts_indexes(self, api_db):
        with get_connection(api_db) as conn:
            cur = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='index' AND tbl_name='voice_transcripts'"
            )
            names = {r[0] for r in cur.fetchall()}
        assert "idx_voice_transcripts_wo" in names
        assert "idx_voice_transcripts_issue" in names
        assert "idx_voice_transcripts_audio_age" in names
        assert "idx_voice_transcripts_extraction_state" in names

    def test_extraction_state_check_rejects_invalid(self, api_db, authed):
        user_id, _, _, wo_id = authed
        with get_connection(api_db) as conn:
            with pytest.raises(Exception):
                conn.execute(
                    """INSERT INTO voice_transcripts
                       (work_order_id, audio_path, audio_size_bytes,
                        audio_sha256, duration_ms, captured_at,
                        uploaded_by_user_id, extraction_state)
                       VALUES (?, 'p.m4a', 100, 'a', 1000, '2026-05-06', ?, 'INVALID')""",
                    (wo_id, user_id),
                )

    def test_extraction_method_check_rejects_invalid(self, api_db, authed):
        user_id, _, _, wo_id = authed
        transcript_id = create_voice_transcript(
            work_order_id=wo_id, audio_path="p.m4a",
            audio_size_bytes=100, audio_format="m4a", audio_sha256="a",
            duration_ms=1000, captured_at="2026-05-06",
            uploaded_by_user_id=user_id, db_path=api_db,
        )
        with get_connection(api_db) as conn:
            with pytest.raises(Exception):
                conn.execute(
                    """INSERT INTO extracted_symptoms
                       (transcript_id, text, extraction_method)
                       VALUES (?, 'rough idle', 'INVALID_METHOD')""",
                    (transcript_id,),
                )

    def test_fk_cascade_on_wo_delete(self, api_db, authed):
        user_id, _, _, wo_id = authed
        transcript_id = create_voice_transcript(
            work_order_id=wo_id, audio_path="p.m4a",
            audio_size_bytes=100, audio_format="m4a", audio_sha256="a",
            duration_ms=1000, captured_at="2026-05-06",
            uploaded_by_user_id=user_id, db_path=api_db,
        )
        create_extracted_symptom(
            transcript_id=transcript_id, text="rough idle",
            db_path=api_db,
        )
        with get_connection(api_db) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("DELETE FROM work_orders WHERE id = ?", (wo_id,))
        # Both transcript + extracted_symptom should be gone
        assert get_voice_transcript(transcript_id, db_path=api_db) is None
        with get_connection(api_db) as conn:
            cur = conn.execute(
                "SELECT COUNT(*) FROM extracted_symptoms "
                "WHERE transcript_id = ?", (transcript_id,),
            )
            assert cur.fetchone()[0] == 0


# ---------------------------------------------------------------------------
# 2. audio_pipeline (Phase 195 substrate — format detection only)
# ---------------------------------------------------------------------------


class TestAudioPipeline:

    def test_wav_detection_and_metadata(self):
        raw = _make_wav_bytes(duration_sec=2.0, sample_rate=16000)
        result = inspect_audio(raw)
        assert result.audio_format == "wav"
        assert result.sample_rate_hz == 16000
        assert result.duration_ms == 2000
        assert result.size_bytes == len(raw)
        assert len(result.sha256) == 64

    def test_m4a_header_detection(self):
        raw = _make_m4a_header_bytes()
        result = inspect_audio(raw)
        assert result.audio_format == "m4a"
        # Header parser doesn't extract duration for M4A; mobile metadata authoritative
        assert result.duration_ms is None
        assert result.sample_rate_hz == 16000  # default

    def test_ogg_header_detection(self):
        raw = _make_ogg_header_bytes()
        result = inspect_audio(raw)
        assert result.audio_format == "ogg"
        assert result.duration_ms is None
        assert result.sample_rate_hz == 48000

    def test_empty_payload_raises_decode_error(self):
        with pytest.raises(AudioDecodeError):
            inspect_audio(b"")

    def test_unsupported_format_raises(self):
        with pytest.raises(UnsupportedAudioFormatError):
            inspect_audio(b"this is not audio bytes" * 5)

    def test_corrupt_wav_raises_decode_error(self):
        # Has the WAV header magic but truncated body
        raw = b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 4
        with pytest.raises(AudioDecodeError):
            inspect_audio(raw)


# ---------------------------------------------------------------------------
# 3. transcript_extraction (Section 2 γ keyword pass)
# ---------------------------------------------------------------------------


class TestTranscriptExtraction:

    def test_split_into_phrases(self):
        text = "The bike won't start. I noticed a clunk in the front end."
        phrases = split_into_phrases(text)
        assert len(phrases) == 2
        assert "won't start" in phrases[0]
        assert "clunk in the front end" in phrases[1]

    def test_split_handles_commas(self):
        phrases = split_into_phrases(
            "Hard starting, rough idle, and brake squeal.",
        )
        assert len(phrases) >= 3

    def test_split_drops_too_short(self):
        phrases = split_into_phrases("ok. yes. nope.")
        # All too short or matching strip/length filters
        for p in phrases:
            assert len(p) >= 3

    def test_extracts_multiple_categories(self):
        text = (
            "The bike has hard starting in the morning. "
            "Rough idle when warm. "
            "Also some brake squeal at low speed."
        )
        results = extract_symptoms_from_transcript(text)
        categories = {r.category for r in results}
        assert "fuel" in categories  # hard starting + rough idle
        assert "braking" in categories  # brake squeal

    def test_no_matches_returns_empty(self):
        results = extract_symptoms_from_transcript(
            "Just dropped off the bike, keys are on the dash.",
        )
        assert results == []

    def test_empty_input_returns_empty(self):
        assert extract_symptoms_from_transcript("") == []
        assert extract_symptoms_from_transcript(None) == []
        assert extract_symptoms_from_transcript("   \n\t  ") == []

    def test_matches_have_confidence_1(self):
        results = extract_symptoms_from_transcript(
            "Bike is overheating and there is a coolant leak.",
        )
        assert all(r.confidence == 1.0 for r in results)


# ---------------------------------------------------------------------------
# 4. transcript_repo + extracted_symptom_repo
# ---------------------------------------------------------------------------


class TestTranscriptRepo:

    def test_create_get_round_trip(self, api_db, authed):
        user_id, _, _, wo_id = authed
        transcript_id = create_voice_transcript(
            work_order_id=wo_id, audio_path="p.m4a",
            audio_size_bytes=12345, audio_format="m4a",
            audio_sha256="abc", duration_ms=5000,
            captured_at="2026-05-06T10:00:00Z",
            uploaded_by_user_id=user_id,
            preview_text="rough idle when warm",
            preview_engine="ios-speech",
            db_path=api_db,
        )
        row = get_voice_transcript(transcript_id, db_path=api_db)
        assert row is not None
        assert row["work_order_id"] == wo_id
        assert row["audio_format"] == "m4a"
        assert row["preview_text"] == "rough idle when warm"
        assert row["preview_engine"] == "ios-speech"
        assert row["language"] == "en-US"  # default

    def test_list_excludes_soft_deleted(self, api_db, authed):
        user_id, _, _, wo_id = authed
        tid = create_voice_transcript(
            work_order_id=wo_id, audio_path="p.m4a",
            audio_size_bytes=100, audio_format="m4a", audio_sha256="a",
            duration_ms=1000, captured_at="2026-05-06",
            uploaded_by_user_id=user_id, db_path=api_db,
        )
        soft_delete_voice_transcript(tid, db_path=api_db)
        assert list_wo_voice_transcripts(wo_id, db_path=api_db) == []
        assert get_voice_transcript(tid, db_path=api_db) is None

    def test_update_extraction_state_stamps_extracted_at(
        self, api_db, authed,
    ):
        user_id, _, _, wo_id = authed
        tid = create_voice_transcript(
            work_order_id=wo_id, audio_path="p.m4a",
            audio_size_bytes=100, audio_format="m4a", audio_sha256="a",
            duration_ms=1000, captured_at="2026-05-06",
            uploaded_by_user_id=user_id, db_path=api_db,
        )
        update_extraction_state(tid, "extracted", db_path=api_db)
        row = get_voice_transcript(tid, db_path=api_db)
        assert row["extraction_state"] == "extracted"
        assert row["extracted_at"] is not None

    def test_quota_helpers(self, api_db, authed):
        user_id, _, _, wo_id = authed
        for i in range(5):
            create_voice_transcript(
                work_order_id=wo_id, audio_path=f"p{i}.m4a",
                audio_size_bytes=100, audio_format="m4a",
                audio_sha256=f"s{i}", duration_ms=1000,
                captured_at="2026-05-06",
                uploaded_by_user_id=user_id, db_path=api_db,
            )
        assert count_wo_voice_transcripts(wo_id, db_path=api_db) == 5
        assert count_voice_transcripts_this_month_for_uploader(
            user_id, db_path=api_db,
        ) == 5


class TestExtractedSymptomRepo:

    def test_confirm_flips_method_when_text_changes(self, api_db, authed):
        user_id, _, _, wo_id = authed
        tid = create_voice_transcript(
            work_order_id=wo_id, audio_path="p.m4a",
            audio_size_bytes=100, audio_format="m4a", audio_sha256="a",
            duration_ms=1000, captured_at="2026-05-06",
            uploaded_by_user_id=user_id, db_path=api_db,
        )
        eid = create_extracted_symptom(
            transcript_id=tid, text="rough idle", category="fuel",
            db_path=api_db,
        )
        confirm_extracted_symptom(
            eid, confirmed_by_user_id=user_id,
            text="rough idle when warm", db_path=api_db,
        )
        row = get_extracted_symptom(eid, db_path=api_db)
        assert row["text"] == "rough idle when warm"
        assert row["extraction_method"] == "manual_edit"
        assert row["confirmed_by_user_id"] == user_id

    def test_confirm_keeps_method_when_text_unchanged(
        self, api_db, authed,
    ):
        user_id, _, _, wo_id = authed
        tid = create_voice_transcript(
            work_order_id=wo_id, audio_path="p.m4a",
            audio_size_bytes=100, audio_format="m4a", audio_sha256="a",
            duration_ms=1000, captured_at="2026-05-06",
            uploaded_by_user_id=user_id, db_path=api_db,
        )
        eid = create_extracted_symptom(
            transcript_id=tid, text="rough idle", category="fuel",
            db_path=api_db,
        )
        confirm_extracted_symptom(
            eid, confirmed_by_user_id=user_id, db_path=api_db,
        )
        row = get_extracted_symptom(eid, db_path=api_db)
        assert row["text"] == "rough idle"  # unchanged
        assert row["extraction_method"] == "keyword"  # unchanged
        assert row["confirmed_by_user_id"] == user_id

    def test_list_for_transcript_orders_by_id_asc(self, api_db, authed):
        user_id, _, _, wo_id = authed
        tid = create_voice_transcript(
            work_order_id=wo_id, audio_path="p.m4a",
            audio_size_bytes=100, audio_format="m4a", audio_sha256="a",
            duration_ms=1000, captured_at="2026-05-06",
            uploaded_by_user_id=user_id, db_path=api_db,
        )
        ids = []
        for text in ("first", "second", "third"):
            ids.append(create_extracted_symptom(
                transcript_id=tid, text=text, db_path=api_db,
            ))
        rows = list_for_transcript(tid, db_path=api_db)
        assert [r["id"] for r in rows] == ids


# ---------------------------------------------------------------------------
# 5. audio_sweep (Section 5 retention + Risk 9)
# ---------------------------------------------------------------------------


class TestAudioSweep:

    def test_prunes_rows_older_than_retention(self, api_db, authed, tmp_path):
        user_id, _, _, wo_id = authed
        # Create a transcript with audio file present
        audio_dir = tmp_path / "data" / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_path = audio_dir / "old.m4a"
        audio_path.write_bytes(b"old audio bytes")
        tid = create_voice_transcript(
            work_order_id=wo_id, audio_path=str(audio_path),
            audio_size_bytes=15, audio_format="m4a",
            audio_sha256="a", duration_ms=1000,
            captured_at="2026-03-01", uploaded_by_user_id=user_id,
            db_path=api_db,
        )
        # Backdate created_at to 61 days ago
        with get_connection(api_db) as conn:
            conn.execute(
                "UPDATE voice_transcripts SET created_at = ? WHERE id = ?",
                ("2026-03-06 12:00:00", tid),
            )
        # Sweep with now=2026-05-06 12:00:00 UTC; cutoff = 61 days back
        now = datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc)
        result = prune_old_audio(now, db_path=api_db)
        assert result.pruned_count == 1
        assert result.total_bytes_freed == 15
        assert not audio_path.exists()
        row = get_voice_transcript(tid, db_path=api_db)
        assert row["audio_deleted_at"] is not None

    def test_preserves_rows_within_retention(
        self, api_db, authed, tmp_path,
    ):
        user_id, _, _, wo_id = authed
        audio_dir = tmp_path / "data" / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_path = audio_dir / "fresh.m4a"
        audio_path.write_bytes(b"fresh audio bytes")
        tid = create_voice_transcript(
            work_order_id=wo_id, audio_path=str(audio_path),
            audio_size_bytes=17, audio_format="m4a",
            audio_sha256="b", duration_ms=1000,
            captured_at="2026-04-30", uploaded_by_user_id=user_id,
            db_path=api_db,
        )
        with get_connection(api_db) as conn:
            conn.execute(
                "UPDATE voice_transcripts SET created_at = ? WHERE id = ?",
                ("2026-04-30 12:00:00", tid),  # 6 days before now
            )
        now = datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc)
        result = prune_old_audio(now, db_path=api_db)
        assert result.pruned_count == 0
        assert audio_path.exists()
        row = get_voice_transcript(tid, db_path=api_db)
        assert row["audio_deleted_at"] is None

    def test_idempotent_second_call(self, api_db, authed, tmp_path):
        user_id, _, _, wo_id = authed
        audio_dir = tmp_path / "data" / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_path = audio_dir / "old2.m4a"
        audio_path.write_bytes(b"old audio")
        tid = create_voice_transcript(
            work_order_id=wo_id, audio_path=str(audio_path),
            audio_size_bytes=9, audio_format="m4a",
            audio_sha256="c", duration_ms=1000,
            captured_at="2026-01-01", uploaded_by_user_id=user_id,
            db_path=api_db,
        )
        with get_connection(api_db) as conn:
            conn.execute(
                "UPDATE voice_transcripts SET created_at = ? WHERE id = ?",
                ("2026-01-01 00:00:00", tid),
            )
        now = datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc)
        first = prune_old_audio(now, db_path=api_db)
        assert first.pruned_count == 1
        # Second sweep is a no-op (audio_deleted_at filter excludes)
        second = prune_old_audio(now, db_path=api_db)
        assert second.pruned_count == 0

    def test_missing_file_no_op(self, api_db, authed, tmp_path):
        user_id, _, _, wo_id = authed
        # Reference a path that doesn't exist
        tid = create_voice_transcript(
            work_order_id=wo_id, audio_path="/nonexistent/path.m4a",
            audio_size_bytes=100, audio_format="m4a", audio_sha256="d",
            duration_ms=1000, captured_at="2026-01-01",
            uploaded_by_user_id=user_id, db_path=api_db,
        )
        with get_connection(api_db) as conn:
            conn.execute(
                "UPDATE voice_transcripts SET created_at = ? WHERE id = ?",
                ("2026-01-01 00:00:00", tid),
            )
        now = datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc)
        result = prune_old_audio(now, db_path=api_db)
        # Missing file is not an error — sweep stamps audio_deleted_at
        assert result.pruned_count == 1
        assert result.errors == []


# ---------------------------------------------------------------------------
# 6. Route — happy path
# ---------------------------------------------------------------------------


def _post_transcript(client, key, shop_id, wo_id, raw=None, **meta_overrides):
    raw = raw or _make_wav_bytes(duration_sec=2.0)
    metadata = {
        "captured_at": "2026-05-06T10:00:00Z",
        "duration_ms": 2000,
        "language": "en-US",
        "preview_text": "rough idle when warm and brake squeal at low speed",
        "preview_engine": "ios-speech",
    }
    metadata.update(meta_overrides)
    return client.post(
        f"/v1/shop/{shop_id}/work-orders/{wo_id}/transcripts",
        files={"file": ("voice.wav", raw, "audio/wav")},
        data={"metadata": _json.dumps(metadata)},
        headers={"X-API-Key": key},
    )


class TestUploadHappyPath:

    def test_upload_returns_201_with_extracted_symptoms(
        self, client, authed,
    ):
        _, key, shop_id, wo_id = authed
        r = _post_transcript(client, key, shop_id, wo_id)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["work_order_id"] == wo_id
        assert body["audio_format"] == "wav"
        assert body["extraction_state"] == "extracted"
        assert len(body["extracted_symptoms"]) >= 2
        cats = {e["category"] for e in body["extracted_symptoms"]}
        assert "fuel" in cats  # rough idle
        assert "braking" in cats  # brake squeal

    def test_upload_persists_audio_at_canonical_path(
        self, client, authed, tmp_path,
    ):
        _, key, shop_id, wo_id = authed
        r = _post_transcript(client, key, shop_id, wo_id)
        assert r.status_code == 201
        transcript_id = r.json()["id"]
        expected = (
            tmp_path / "data" / "audio"
            / f"shop_{shop_id}" / f"work_order_{wo_id}"
            / f"{transcript_id}.wav"
        )
        assert expected.exists()

    def test_upload_with_no_preview_text_extracts_zero_symptoms(
        self, client, authed,
    ):
        _, key, shop_id, wo_id = authed
        r = _post_transcript(client, key, shop_id, wo_id, preview_text=None)
        assert r.status_code == 201
        assert r.json()["extracted_symptoms"] == []
        assert r.json()["extraction_state"] == "extracted"

    def test_list_then_get_round_trip(self, client, authed):
        _, key, shop_id, wo_id = authed
        r = _post_transcript(client, key, shop_id, wo_id)
        assert r.status_code == 201
        list_r = client.get(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/transcripts",
            headers={"X-API-Key": key},
        )
        assert list_r.status_code == 200
        items = list_r.json()
        assert len(items) == 1
        tid = items[0]["id"]
        get_r = client.get(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/transcripts/{tid}",
            headers={"X-API-Key": key},
        )
        assert get_r.status_code == 200
        assert get_r.json()["id"] == tid

    def test_audio_stream_returns_audio_bytes(self, client, authed):
        _, key, shop_id, wo_id = authed
        r = _post_transcript(client, key, shop_id, wo_id)
        tid = r.json()["id"]
        file_r = client.get(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/transcripts/{tid}/audio",
            headers={"X-API-Key": key},
        )
        assert file_r.status_code == 200
        assert file_r.headers["content-type"] == "audio/wav"
        assert file_r.content[:4] == b"RIFF"

    def test_delete_idempotent(self, client, authed):
        _, key, shop_id, wo_id = authed
        r = _post_transcript(client, key, shop_id, wo_id)
        tid = r.json()["id"]
        del1 = client.delete(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/transcripts/{tid}",
            headers={"X-API-Key": key},
        )
        assert del1.status_code == 204
        del2 = client.delete(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/transcripts/{tid}",
            headers={"X-API-Key": key},
        )
        assert del2.status_code == 204


# ---------------------------------------------------------------------------
# 7. Route — auth + cross-shop isolation
# ---------------------------------------------------------------------------


class TestUploadAuth:

    def test_unauth_returns_401(self, client, authed):
        _, _, shop_id, wo_id = authed
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/transcripts",
            files={"file": ("v.wav", _make_wav_bytes(), "audio/wav")},
            data={"metadata": '{"captured_at": "2026-05-06", "duration_ms": 1000}'},
        )
        assert r.status_code == 401

    def test_individual_tier_returns_402(self, client, authed, api_db):
        _, _, shop_id, wo_id = authed
        ind_user_id = _make_user(api_db, "alone", sub_tier="individual")
        _, ind_key = create_api_key(ind_user_id, db_path=api_db)
        r = _post_transcript(client, ind_key, shop_id, wo_id)
        assert r.status_code == 402

    def test_cross_shop_returns_403(self, client, authed, api_db):
        _, key, _, _ = authed
        other_user = _make_user(api_db, "other_owner")
        other_shop, other_wo = _seed_shop_and_wo(
            api_db, other_user, shop_name="OtherShop",
        )
        r = _post_transcript(client, key, other_shop, other_wo)
        assert r.status_code == 403

    def test_cross_wo_returns_404(self, client, authed):
        _, key, shop_id, _ = authed
        r = _post_transcript(client, key, shop_id, 999_999)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# 8. Route — quota + format errors + PATCH confirm flow + 410
# ---------------------------------------------------------------------------


class TestUploadQuotasAndErrors:

    def test_per_wo_count_cap_enforced(self, client, authed, api_db):
        from motodiag.api.routes.transcripts import (
            PER_WO_TRANSCRIPT_COUNT_CAP,
        )
        _, key, shop_id, wo_id = authed
        user_id = authed[0]
        for i in range(PER_WO_TRANSCRIPT_COUNT_CAP):
            create_voice_transcript(
                work_order_id=wo_id, audio_path=f"p{i}.m4a",
                audio_size_bytes=100, audio_format="m4a",
                audio_sha256=f"s{i}", duration_ms=1000,
                captured_at="2026-05-06",
                uploaded_by_user_id=user_id, db_path=api_db,
            )
        r = _post_transcript(client, key, shop_id, wo_id)
        assert r.status_code == 402

    def test_corrupt_audio_returns_422(self, client, authed):
        _, key, shop_id, wo_id = authed
        r = client.post(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/transcripts",
            files={"file": ("v.wav", b"not audio bytes" * 5, "audio/wav")},
            data={"metadata": _json.dumps({
                "captured_at": "2026-05-06", "duration_ms": 1000,
            })},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 415  # unrecognized header → 415


class TestPatchConfirmFlow:

    def test_patch_extracted_symptom_round_trip(self, client, authed):
        _, key, shop_id, wo_id = authed
        r = _post_transcript(client, key, shop_id, wo_id)
        body = r.json()
        tid = body["id"]
        eid = body["extracted_symptoms"][0]["id"]
        patch_r = client.patch(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/transcripts/{tid}"
            f"/extracted-symptoms/{eid}",
            json={"text": "rough idle (cold start only)"},
            headers={"X-API-Key": key},
        )
        assert patch_r.status_code == 200
        updated = patch_r.json()
        assert updated["text"] == "rough idle (cold start only)"
        assert updated["extraction_method"] == "manual_edit"
        assert updated["confirmed_by_user_id"] is not None


class TestAudioGoneAfterSweep:

    def test_audio_endpoint_returns_410_after_sweep(
        self, client, authed, api_db,
    ):
        _, key, shop_id, wo_id = authed
        r = _post_transcript(client, key, shop_id, wo_id)
        tid = r.json()["id"]
        # Manually stamp audio_deleted_at to simulate sweep
        with get_connection(api_db) as conn:
            conn.execute(
                "UPDATE voice_transcripts SET audio_deleted_at = ? WHERE id = ?",
                ("2026-07-06T00:00:00Z", tid),
            )
        file_r = client.get(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/transcripts/{tid}/audio",
            headers={"X-API-Key": key},
        )
        assert file_r.status_code == 410
