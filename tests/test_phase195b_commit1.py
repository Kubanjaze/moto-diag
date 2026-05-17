# f9-allow-model-ids: fixture-data — the model-ID literal here is
# extract_symptoms test fixture data (the Haiku model arg), not
# production model selection; SSOT is src/motodiag/engine/client.py:MODEL_ALIASES.
"""Phase 195B (Commit 1) — Claude extraction + threshold + async pipeline.

Covers:
* `transcript_extraction` — keyword_coverage + should_run_claude_fallback
  threshold gate (the calibrated 0.5 coverage threshold).
* `DiagnosticClient.extract_symptoms` — tool-use structured output
  (mocked Anthropic client; no live call) + malformed-output →
  ClaudeExtractionMalformedError.
* `extracted_symptom_repo.finalize_extraction` — the Backend Commit 1
  ACCEPTANCE CRITERION: row-writes + extraction_state flip are a
  single atomic transaction. Includes the rollback-on-failure test
  that proves a refetch can never see a torn (rows-without-flip /
  flip-without-rows) state.
* `transcript_pipeline.run_extraction_pipeline` — end-to-end async
  orchestration: Whisper-degrade path, keyword-only path,
  Claude-fallback path, malformed-Claude → extraction_failed.
"""

from __future__ import annotations

import sqlite3

import pytest

from motodiag.core.config import reset_settings
from motodiag.core.database import get_connection, init_db
from motodiag.engine.client import (
    ClaudeExtractionMalformedError,
    DiagnosticClient,
)
from motodiag.media.transcript_extraction import (
    CLAUDE_FALLBACK_COVERAGE_THRESHOLD,
    extract_symptoms_from_transcript,
    keyword_coverage,
    should_run_claude_fallback,
    split_into_phrases,
)
from motodiag.shop.extracted_symptom_repo import (
    finalize_extraction,
    list_for_transcript,
)
from motodiag.shop.transcript_repo import get_voice_transcript


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = str(tmp_path / "phase195b_c1.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    reset_settings()
    yield path
    reset_settings()


def _make_transcript(
    db, *, preview_text="hard starting in the morning",
    state="extracting",
):
    """Insert a voice_transcripts row directly (raw connection — the
    row's own FKs point at parent rows this minimal DB lacks)."""
    raw = sqlite3.connect(db)
    cur = raw.execute(
        """INSERT INTO voice_transcripts
           (work_order_id, audio_path, audio_size_bytes, audio_format,
            audio_sha256, duration_ms, captured_at,
            uploaded_by_user_id, preview_text, extraction_state)
           VALUES (1, ?, 100, 'm4a', 'sha', 5000, '2026-05-16', 1,
                   ?, ?)""",
        (f"{tmp_audio()}", preview_text, state),
    )
    tid = cur.lastrowid
    raw.commit()
    raw.close()
    return tid


def tmp_audio() -> str:
    return "/tmp/fake-audio.m4a"


# ---------------------------------------------------------------------------
# 1. Threshold gate
# ---------------------------------------------------------------------------


class TestThresholdGate:

    def test_threshold_calibrated_at_0_5(self):
        assert CLAUDE_FALLBACK_COVERAGE_THRESHOLD == 0.5

    def test_coverage_all_matched(self):
        txt = "hard starting in the morning. rough idle when warm."
        phrases = split_into_phrases(txt)
        ex = extract_symptoms_from_transcript(txt)
        assert keyword_coverage(phrases, ex) == 1.0

    def test_coverage_partial(self):
        txt = "hard starting in the morning. blah blah nonsense filler."
        phrases = split_into_phrases(txt)
        ex = extract_symptoms_from_transcript(txt)
        cov = keyword_coverage(phrases, ex)
        assert 0.0 < cov < 1.0

    def test_coverage_empty_phrases_is_zero(self):
        assert keyword_coverage([], []) == 0.0

    def test_should_run_claude_empty_transcript_false(self):
        assert should_run_claude_fallback("", []) is False
        assert should_run_claude_fallback(None, []) is False
        assert should_run_claude_fallback("   ", []) is False

    def test_should_run_claude_zero_match_nonempty_true(self):
        # Non-empty transcript, keyword found nothing → Claude fires.
        assert should_run_claude_fallback(
            "xyzzy plugh frobnitz quux", [],
        ) is True

    def test_should_run_claude_high_coverage_false(self):
        txt = "hard starting in the morning. rough idle when warm."
        ex = extract_symptoms_from_transcript(txt)
        # coverage 1.0 ≥ 0.5 → keyword sufficient.
        assert should_run_claude_fallback(txt, ex) is False

    def test_should_run_claude_low_coverage_true(self):
        # 1 match in 4 phrases → coverage 0.25 < 0.5 → Claude fires.
        txt = (
            "hard starting in the morning. some filler here. "
            "more unrelated chatter. and yet more nonsense words."
        )
        ex = extract_symptoms_from_transcript(txt)
        cov = keyword_coverage(split_into_phrases(txt), ex)
        assert cov < CLAUDE_FALLBACK_COVERAGE_THRESHOLD
        assert should_run_claude_fallback(txt, ex) is True


# ---------------------------------------------------------------------------
# 2. DiagnosticClient.extract_symptoms (mocked Anthropic client)
# ---------------------------------------------------------------------------


class _FakeBlock:
    def __init__(self, type_, **kw):
        self.type = type_
        for k, v in kw.items():
            setattr(self, k, v)


class _FakeUsage:
    input_tokens = 120
    output_tokens = 40


class _FakeResponse:
    def __init__(self, content):
        self.content = content
        self.usage = _FakeUsage()


class _FakeMessages:
    def __init__(self, response):
        self._response = response

    def create(self, **kwargs):
        return self._response


class _FakeClient:
    def __init__(self, response):
        self.messages = _FakeMessages(response)


def _client_with_response(monkeypatch, response):
    client = DiagnosticClient(api_key="sk-test-fake-key-1234567890")
    monkeypatch.setattr(
        client, "_get_client", lambda: _FakeClient(response),
    )
    return client


class TestExtractSymptoms:

    def test_extract_symptoms_parses_tool_use(self, monkeypatch):
        resp = _FakeResponse([
            _FakeBlock(
                "tool_use",
                input={
                    "symptoms": [
                        {"text": "rough idle when warm", "category": "fuel"},
                        {"text": "front brake squeal", "category": "braking"},
                    ],
                },
            ),
        ])
        client = _client_with_response(monkeypatch, resp)
        symptoms, usage = client.extract_symptoms(
            "the bike has rough idle and brake squeal",
            categories=["fuel", "braking", "electrical"],
        )
        assert len(symptoms) == 2
        assert symptoms[0] == {
            "text": "rough idle when warm", "category": "fuel",
        }
        assert usage.input_tokens == 120
        assert usage.output_tokens == 40

    def test_extract_symptoms_empty_list(self, monkeypatch):
        resp = _FakeResponse([
            _FakeBlock("tool_use", input={"symptoms": []}),
        ])
        client = _client_with_response(monkeypatch, resp)
        symptoms, _ = client.extract_symptoms(
            "just dropped the bike off", categories=["fuel"],
        )
        assert symptoms == []

    def test_extract_symptoms_no_tool_block_raises(self, monkeypatch):
        resp = _FakeResponse([_FakeBlock("text", text="I think...")])
        client = _client_with_response(monkeypatch, resp)
        with pytest.raises(ClaudeExtractionMalformedError):
            client.extract_symptoms("...", categories=["fuel"])

    def test_extract_symptoms_malformed_input_raises(self, monkeypatch):
        resp = _FakeResponse([
            _FakeBlock("tool_use", input={"wrong_key": []}),
        ])
        client = _client_with_response(monkeypatch, resp)
        with pytest.raises(ClaudeExtractionMalformedError):
            client.extract_symptoms("...", categories=["fuel"])

    def test_extract_symptoms_drops_incomplete_items(self, monkeypatch):
        resp = _FakeResponse([
            _FakeBlock(
                "tool_use",
                input={
                    "symptoms": [
                        {"text": "rough idle", "category": "fuel"},
                        {"text": "", "category": "fuel"},        # no text
                        {"text": "no category here"},            # no cat
                    ],
                },
            ),
        ])
        client = _client_with_response(monkeypatch, resp)
        symptoms, _ = client.extract_symptoms(
            "...", categories=["fuel"],
        )
        assert len(symptoms) == 1


# ---------------------------------------------------------------------------
# 3. finalize_extraction — ATOMIC TRANSACTION ACCEPTANCE CRITERION
# ---------------------------------------------------------------------------


class TestFinalizeExtractionAtomicity:
    """Backend Commit 1 acceptance criterion (architect-elevated):
    the extracted_symptoms row-writes + the extraction_state flip
    MUST be a single atomic transaction. A mobile refetch must see
    EITHER (extracting, no rows) OR (extracted, all rows) — never a
    torn state."""

    def test_happy_path_rows_and_state_commit_together(self, db):
        tid = _make_transcript(db, state="extracting")
        inserted = finalize_extraction(
            tid,
            [
                {"text": "rough idle", "category": "fuel",
                 "extraction_method": "keyword"},
                {"text": "brake squeal", "category": "braking",
                 "extraction_method": "claude"},
            ],
            "extracted",
            db_path=db,
        )
        assert inserted == 2
        # A reader (separate connection) sees the consistent post-state:
        # state flipped AND all rows present.
        row = get_voice_transcript(tid, db_path=db)
        assert row["extraction_state"] == "extracted"
        assert row["extracted_at"] is not None
        symptoms = list_for_transcript(tid, db_path=db)
        assert len(symptoms) == 2

    def test_pre_finalize_state_is_extracting_with_no_rows(self, db):
        # The "before" half of the atomicity contract — a refetch
        # landing before finalize sees (extracting, 0 rows).
        tid = _make_transcript(db, state="extracting")
        row = get_voice_transcript(tid, db_path=db)
        assert row["extraction_state"] == "extracting"
        assert list_for_transcript(tid, db_path=db) == []

    def test_rollback_on_mid_write_failure_leaves_no_torn_state(self, db):
        # THE interleaving guarantee. finalize_extraction inserts
        # symptom rows then flips state, all in one transaction. If a
        # row INSERT fails partway (here: an invalid extraction_method
        # violates the migration-042 CHECK constraint), get_connection
        # rolls the WHOLE transaction back. Result: NO rows written +
        # state NOT flipped — exactly the "never torn" guarantee. A
        # refetch at any instant sees (extracting, 0 rows), never a
        # partial write.
        tid = _make_transcript(db, state="extracting")
        with pytest.raises(sqlite3.IntegrityError):
            finalize_extraction(
                tid,
                [
                    {"text": "row one ok", "category": "fuel",
                     "extraction_method": "keyword"},
                    # 2nd row violates the extraction_method CHECK —
                    # the INSERT raises AFTER row one already inserted.
                    {"text": "row two bad", "category": "fuel",
                     "extraction_method": "NOT_A_VALID_METHOD"},
                ],
                "extracted",
                db_path=db,
            )
        # Atomic rollback: row one is GONE (not just row two), and the
        # state did NOT flip. No torn state.
        row = get_voice_transcript(tid, db_path=db)
        assert row["extraction_state"] == "extracting"
        assert list_for_transcript(tid, db_path=db) == []

    def test_replace_existing_supersedes_prior_rows(self, db):
        # The async pipeline re-extracts from the Whisper-canonical
        # transcript + supersedes the sync keyword pass via
        # replace_existing=True — also inside the one transaction.
        tid = _make_transcript(db, state="extracting")
        finalize_extraction(
            tid,
            [{"text": "old keyword row", "category": "fuel"}],
            "extracting",  # interim — not really used this way, but
            db_path=db,    # exercises a first write
        )
        assert len(list_for_transcript(tid, db_path=db)) == 1
        finalize_extraction(
            tid,
            [
                {"text": "new row a", "category": "fuel"},
                {"text": "new row b", "category": "braking"},
            ],
            "extracted",
            replace_existing=True,
            db_path=db,
        )
        live = list_for_transcript(tid, db_path=db)
        assert len(live) == 2
        assert {s["text"] for s in live} == {"new row a", "new row b"}

    def test_extraction_failed_state_no_extracted_at(self, db):
        tid = _make_transcript(db, state="extracting")
        finalize_extraction(
            tid,
            [{"text": "keyword survivor", "category": "fuel"}],
            "extraction_failed",
            db_path=db,
        )
        row = get_voice_transcript(tid, db_path=db)
        assert row["extraction_state"] == "extraction_failed"
        # extracted_at is only stamped on the 'extracted' state.
        assert row["extracted_at"] is None
        # Keyword rows survive — graceful degradation per plan §2.
        assert len(list_for_transcript(tid, db_path=db)) == 1


# ---------------------------------------------------------------------------
# 4. transcript_pipeline — end-to-end async orchestration
# ---------------------------------------------------------------------------


class TestExtractionPipeline:

    def test_pipeline_whisper_unavailable_degrades_to_preview(
        self, db, monkeypatch,
    ):
        # No OpenAI key → Whisper unavailable. Pipeline degrades to
        # preview_text, runs keyword extraction, finalizes 'extracted'.
        monkeypatch.setenv("MOTODIAG_OPENAI_API_KEY", "")
        reset_settings()
        tid = _make_transcript(
            db,
            preview_text="hard starting in the morning. rough idle when warm.",
            state="extracting",
        )
        from motodiag.media.transcript_pipeline import run_extraction_pipeline
        run_extraction_pipeline(tid, shop_id=1, db_path=db)

        row = get_voice_transcript(tid, db_path=db)
        assert row["extraction_state"] == "extracted"
        assert row["whisper_transcript"] is None  # whisper never ran
        symptoms = list_for_transcript(tid, db_path=db)
        assert len(symptoms) >= 1
        assert all(s["extraction_method"] == "keyword" for s in symptoms)

    def test_pipeline_never_leaves_transcript_stuck_in_extracting(
        self, db, monkeypatch,
    ):
        # Even a transcript with no preview_text + no whisper must
        # finalize OUT of 'extracting' (zero rows, state 'extracted').
        monkeypatch.setenv("MOTODIAG_OPENAI_API_KEY", "")
        reset_settings()
        tid = _make_transcript(db, preview_text=None, state="extracting")
        from motodiag.media.transcript_pipeline import run_extraction_pipeline
        run_extraction_pipeline(tid, shop_id=1, db_path=db)
        row = get_voice_transcript(tid, db_path=db)
        assert row["extraction_state"] in ("extracted", "extraction_failed")

    def test_pipeline_claude_fallback_path(self, db, monkeypatch):
        # Low keyword coverage → Claude fires. Mock the Claude client
        # to return a structured symptom; assert a 'claude'-method row
        # lands + a cost_events claude row is recorded.
        monkeypatch.setenv("MOTODIAG_OPENAI_API_KEY", "")  # whisper off
        reset_settings()
        tid = _make_transcript(
            db,
            preview_text="xyzzy plugh frobnitz totally unmatched chatter",
            state="extracting",
        )

        # Patch DiagnosticClient.extract_symptoms at the pipeline's
        # import site.
        import motodiag.media.transcript_pipeline as pipe

        class _StubUsage:
            model = "claude-haiku-4-5-20251001"
            input_tokens = 100
            output_tokens = 30
            cost_estimate = 0.0012  # USD

        class _StubClient:
            def __init__(self, *a, **kw):
                pass

            def extract_symptoms(self, text, categories, model=None):
                return (
                    [{"text": "intermittent stall", "category": "fuel"}],
                    _StubUsage(),
                )

        monkeypatch.setattr(
            "motodiag.engine.client.DiagnosticClient", _StubClient,
        )
        pipe.run_extraction_pipeline(tid, shop_id=7, db_path=db)

        row = get_voice_transcript(tid, db_path=db)
        assert row["extraction_state"] == "extracted"
        symptoms = list_for_transcript(tid, db_path=db)
        methods = {s["extraction_method"] for s in symptoms}
        assert "claude" in methods
        # cost_events recorded the claude call.
        with get_connection(db) as conn:
            n = conn.execute(
                "SELECT COUNT(*) FROM cost_events "
                "WHERE kind='claude_extraction'"
            ).fetchone()[0]
        assert n == 1

    def test_pipeline_malformed_claude_degrades_to_extraction_failed(
        self, db, monkeypatch,
    ):
        monkeypatch.setenv("MOTODIAG_OPENAI_API_KEY", "")
        reset_settings()
        tid = _make_transcript(
            db,
            preview_text="xyzzy plugh frobnitz totally unmatched chatter",
            state="extracting",
        )

        class _BadClient:
            def __init__(self, *a, **kw):
                pass

            def extract_symptoms(self, text, categories, model=None):
                raise ClaudeExtractionMalformedError("malformed")

        monkeypatch.setattr(
            "motodiag.engine.client.DiagnosticClient", _BadClient,
        )
        import motodiag.media.transcript_pipeline as pipe
        pipe.run_extraction_pipeline(tid, shop_id=1, db_path=db)

        row = get_voice_transcript(tid, db_path=db)
        # Claude failed → state 'extraction_failed', keyword rows kept
        # (zero here since the text is all-nonsense, but the contract
        # is the state flag — never stuck in 'extracting').
        assert row["extraction_state"] == "extraction_failed"
