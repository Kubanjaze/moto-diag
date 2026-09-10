"""Phase 244B — guidance mode on the media path.

Written against the failure the user actually reported: shown a bike and asked
where a leak was most likely coming from, the product returned plenty of
information that drifted from the question.

Step 0 found three structural causes, and these guards pin each one closed:
the question is now an input; the answer shape can be guidance rather than a
forced sweep; and every candidate carries what it rests on.

The hardest thing to assert is RELEVANCE — "answered the question" is not a
regex. What is testable is the structure that made drift inevitable, so these
guards target that: the question reaches the model, the contract cannot express
a diagnosis, and an ungrounded candidate must say so.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from motodiag.media import analysis_worker as vap_worker
from motodiag.media import vision_analysis_pipeline as vap
from motodiag.media.vision_types import (
    GUIDANCE_PROMPT,
    Grounding,
    GuidanceCandidate,
    GuidanceResponse,
    VehicleContext,
    VisualAnalysisResult,
)
from support.source_guards import code_of

LEAK_Q = "Where is this leak most likely coming from?"
VC = VehicleContext(make="Honda", model="CBR600RR", year=2008)


# ---------------------------------------------------------------------------
# 1. Cause one: the question is now an input
# ---------------------------------------------------------------------------
class TestTheQuestionReachesTheModel:
    def test_the_prompt_builder_accepts_a_question(self):
        """Before Phase 244B this took (vehicle_context, frame_count) only, so
        a technician's question could not reach the model at any point. That is
        why the reported answer 'drifted' — it was never an input."""
        params = inspect.signature(vap._build_user_prompt).parameters
        assert "question" in params

    def test_the_question_appears_in_the_built_prompt(self):
        prompt = vap._build_user_prompt(VC, 6, question=LEAK_Q)
        assert LEAK_Q in prompt

    def test_the_prompt_tells_the_model_to_answer_only_that(self):
        prompt = vap._build_user_prompt(VC, 6, question=LEAK_Q)
        assert "answer this, and only this" in prompt.lower()

    def test_without_a_question_the_sweep_prompt_is_unchanged(self):
        """The sweep is correct for a sweep request. This phase adds a path; it
        does not alter the existing one."""
        prompt = vap._build_user_prompt(VC, 6)
        assert "report_video_findings" in prompt
        assert "TECHNICIAN'S QUESTION" not in prompt


# ---------------------------------------------------------------------------
# 2. Cause two and three: the answer shape is no longer forced to be a sweep
# ---------------------------------------------------------------------------
class TestTheAnswerShapeCanBeGuidance:
    def test_a_separate_guidance_tool_exists(self):
        assert vap._build_guidance_tool()["name"] == "provide_guidance"

    def test_the_sweep_tool_still_exists(self):
        assert vap._build_findings_tool()["name"] == "report_video_findings"

    def test_the_guidance_contract_cannot_express_a_diagnosis(self):
        """The text path's fourth cause, kept out of this contract by design:
        `DiagnosisItem.diagnosis` is a REQUIRED field described as 'specific
        root cause', so a narrow question still yields a verdict and a system
        with no evidence must still name one. Guidance must be able to answer
        without concluding."""
        for banned in ("diagnosis", "root_cause", "repair_steps", "parts_needed", "estimated_cost"):
            assert banned not in GuidanceResponse.model_fields, banned
            assert banned not in GuidanceCandidate.model_fields, banned

    def test_the_discriminator_is_required_of_every_candidate(self):
        """The value of a guidance answer is what tells the candidates apart.
        A candidate without it is a guess in a list."""
        assert GuidanceCandidate.model_fields["how_to_discriminate"].is_required()

    def test_an_answer_can_decline_to_answer(self):
        r = GuidanceResponse(
            question_understood_as=LEAK_Q,
            answers_the_question=False,
            not_established="No frame shows the underside; the origin cannot be narrowed from this capture.",
        )
        assert r.answers_the_question is False and r.candidates == []


# ---------------------------------------------------------------------------
# 3. Grounding — the Track K discipline applied to generated reasoning
# ---------------------------------------------------------------------------
class TestGroundingIsCarriedPerCandidate:
    def test_every_candidate_must_declare_its_grounding(self):
        assert GuidanceCandidate.model_fields["grounding"].is_required()

    def test_the_grounding_vocabulary_distinguishes_corpus_from_reasoning(self):
        vals = {g.value for g in Grounding}
        assert {"machine_specific", "cross_platform", "general_reasoning", "not_established"} == vals

    def test_a_candidate_cannot_be_built_without_saying_what_it_rests_on(self):
        with pytest.raises(Exception):
            GuidanceCandidate(
                candidate="Countershaft seal",
                why_plausible="Oil near the front sprocket",
                how_to_discriminate="Clean and re-run; oil returning behind the sprocket cover points here",
            )

    def test_the_prompt_forbids_dressing_reasoning_as_documentation(self):
        assert "do not present reasoning as documentation" in (
            vap._build_user_prompt(VC, 6, question=LEAK_Q, corpus_context="- Entry: x").lower()
        )

    def test_with_no_corpus_the_model_is_told_to_say_so(self):
        """An ungrounded guidance surface would undo the corpus discipline in
        one feature. With nothing to ground on, the model must say that rather
        than sound authoritative."""
        prompt = vap._build_user_prompt(VC, 6, question=LEAK_Q, corpus_context="")
        assert "NO CORPUS ENTRIES" in prompt
        assert "general_reasoning at best" in prompt

    def test_corpus_rows_are_rendered_for_citation(self):
        out = vap._format_known_issues(
            [{"title": "Countershaft seal weep", "description": "Oil at the front sprocket cover."}]
        )
        assert "Countershaft seal weep" in out


# ---------------------------------------------------------------------------
# 4. The system prompt targets the reported failure directly
# ---------------------------------------------------------------------------
class TestTheGuidancePromptTargetsTheReportedFailure:
    def test_it_names_completeness_as_the_failure_mode(self):
        """The reported failure was volume, not inaccuracy: 'plenty of
        information' that 'drifted from the purpose'. The prompt has to say
        that a complete survey is a failure, because completeness is what the
        sweep prompt rewards."""
        p = GUIDANCE_PROMPT.lower()
        assert "is a failure" in p and "survey" in p

    def test_it_forbids_diagnosing(self):
        p = GUIDANCE_PROMPT.lower()
        assert "do not diagnose" in p and "do not name a root cause" in p

    def test_it_uses_the_leak_case_to_show_the_distinction(self):
        """The reported question was about a leak, and the existing sweep
        prompt's leak guidance is about identifying the FLUID by colour, which
        is a different question from where it comes from."""
        p = GUIDANCE_PROMPT.lower()
        assert "leak" in p and "origins" in p

    def test_it_requires_saying_what_cannot_be_established(self):
        assert "cannot establish" in GUIDANCE_PROMPT.lower()


# ---------------------------------------------------------------------------
# 5. Wiring, end to end, without a live model
# ---------------------------------------------------------------------------
class _Block:
    type = "tool_use"

    def __init__(self, payload):
        self.input = payload


class _Resp:
    def __init__(self, payload):
        self.content = [_Block(payload)]


class _FakeClient:
    """Captures what the pipeline actually sent."""

    def __init__(self, payload):
        self.payload = payload
        self.seen = {}

    def ask_with_images(self, **kw):
        self.seen = kw
        return _Resp(self.payload), None


@pytest.fixture
def payload():
    return {
        "question_understood_as": LEAK_Q,
        "answers_the_question": True,
        "candidates": [
            {
                "candidate": "Countershaft output seal",
                "why_plausible": "Oil film spreading back from the front sprocket area",
                "how_to_discriminate": "Clean the area, run briefly, and look for oil returning from behind the sprocket cover rather than above it",
                "grounding": "general_reasoning",
                "grounding_detail": "No corpus entry for this machine supports this; offered as reasoning.",
                "check_order_rationale": "Cheapest to inspect — cover off in minutes",
            }
        ],
        "what_would_narrow_it": ["A frame of the underside with the machine on a stand"],
        "not_established": "",
        "observation_basis": "Oil sheen visible low on the left case in two frames",
    }


class TestEndToEndWiring:
    def test_the_question_and_guidance_tool_are_sent(self, tmp_path, payload, monkeypatch):
        frame = tmp_path / "f.jpg"
        frame.write_bytes(b"x")
        analyzer = vap.VisionAnalyzer()
        fake = _FakeClient(payload)
        monkeypatch.setattr(analyzer, "_get_client", lambda: fake)

        result = analyzer.answer_question_about_frames([frame], question=LEAK_Q, vehicle_context=VC)

        assert isinstance(result, GuidanceResponse)
        assert LEAK_Q in fake.seen["prompt"]
        assert fake.seen["tool_choice"]["name"] == "provide_guidance"
        assert fake.seen["system"] is GUIDANCE_PROMPT
        assert result.candidates[0].grounding == Grounding.GENERAL_REASONING

    def test_a_blank_question_is_refused(self, tmp_path, payload, monkeypatch):
        frame = tmp_path / "f.jpg"
        frame.write_bytes(b"x")
        analyzer = vap.VisionAnalyzer()
        monkeypatch.setattr(analyzer, "_get_client", lambda: _FakeClient(payload))
        with pytest.raises(ValueError, match="question is required"):
            analyzer.answer_question_about_frames([frame], question="   ")

    def test_corpus_rows_reach_the_prompt_for_citation(self, tmp_path, payload, monkeypatch):
        frame = tmp_path / "f.jpg"
        frame.write_bytes(b"x")
        analyzer = vap.VisionAnalyzer()
        fake = _FakeClient(payload)
        monkeypatch.setattr(analyzer, "_get_client", lambda: fake)
        analyzer.answer_question_about_frames(
            [frame],
            question=LEAK_Q,
            vehicle_context=VC,
            known_issues=[{"title": "Countershaft seal weep", "description": "Oil at the sprocket cover."}],
        )
        assert "Countershaft seal weep" in fake.seen["prompt"]

    def test_the_sweep_path_is_untouched(self):
        """The regression that would matter most: guidance must not have
        changed how a sweep request behaves."""
        src = code_of(vap.VisionAnalyzer.analyze_video_frames)
        assert 'tool_choice = {"type": "tool", "name": "report_video_findings"}' in src
        assert "question" not in inspect.signature(vap.VisionAnalyzer.analyze_video_frames).parameters


# ---------------------------------------------------------------------------
# 6. Cause four: known facts must reach the model, not be re-guessed
# ---------------------------------------------------------------------------
class TestTheSessionsVehicleReachesTheModel:
    """Reported by the user: the analysis guessed make and model instead of
    pulling details the session already held.

    The cause was not the prompt. `_build_vehicle_context` was a stub returning
    an empty VehicleContext, with a docstring deferring the real join to a
    later commit that never landed. Because `to_context_string()` renders an
    empty context as the literal "No vehicle context provided.", the model was
    told on every analysis that nothing was known about the machine, and then
    shown pixels. Guessing was the only move left.

    Same family as SafetyChecker at Phase 241: stubbed, deferred, never wired,
    and silent about it."""

    def test_an_empty_context_still_renders_the_no_context_string(self):
        """Pinned because it is the mechanism: an empty context does not
        degrade quietly, it actively tells the model nothing is known."""
        assert VehicleContext().to_context_string() == "No vehicle context provided."

    def test_a_populated_context_names_the_machine(self):
        s = VehicleContext(make="Honda", model="CBR600RR", year=2008, mileage=31450).to_context_string()
        assert "2008 Honda CBR600RR" in s and "31,450" in s

    def test_the_builder_is_no_longer_a_stub(self):
        src = code_of(vap_worker._build_vehicle_context)
        assert "return VehicleContext()" in src, "the best-effort fallback must remain"
        assert "get_session" in src, "the session join never landed — this is the Phase 244B fix"

    def test_it_pulls_make_model_year_from_the_session(self, tmp_path, monkeypatch):
        session = {
            "vehicle_make": "Honda",
            "vehicle_model": "CBR600RR",
            "vehicle_year": 2008,
            "vehicle_id": None,
            "symptoms": ["oil spot under the bike"],
        }
        monkeypatch.setattr(vap_worker, "get_session", lambda *a, **k: session, raising=False)
        import motodiag.core.session_repo as sr
        monkeypatch.setattr(sr, "get_session", lambda *a, **k: session)
        vc = vap_worker._build_vehicle_context({"session_id": 7})
        assert (vc.make, vc.model, vc.year) == ("Honda", "CBR600RR", 2008)
        assert "oil spot under the bike" in vc.reported_symptoms
        assert "2008 Honda CBR600RR" in vc.to_context_string()

    def test_symptoms_stored_as_json_text_are_decoded(self):
        """Sessions store symptoms as a JSON string; a raw string would reach
        the prompt as a list of characters."""
        import motodiag.core.session_repo as sr
        session = {"vehicle_make": "Zero", "vehicle_model": "SR/F", "vehicle_year": 2022,
                   "vehicle_id": None, "symptoms": json.dumps(["will not charge"])}
        orig = sr.get_session
        sr.get_session = lambda *a, **k: session
        try:
            vc = vap_worker._build_vehicle_context({"session_id": 3})
        finally:
            sr.get_session = orig
        assert vc.reported_symptoms == ["will not charge"]

    def test_a_missing_session_does_not_break_the_analysis(self):
        """Best-effort is still the contract: no session, no context, analysis
        proceeds."""
        assert vap_worker._build_vehicle_context({}).to_context_string() == "No vehicle context provided."

    def test_a_failing_lookup_does_not_break_the_analysis(self):
        import motodiag.core.session_repo as sr
        orig = sr.get_session

        def boom(*a, **k):
            raise RuntimeError("db gone")

        sr.get_session = boom
        try:
            vc = vap_worker._build_vehicle_context({"session_id": 1})
        finally:
            sr.get_session = orig
        assert vc.make == ""


class TestTheSessionIsNotTheSourceOfTruthForTheMachine:
    """Two defects the user found by re-running a real recording, both in the
    same family as the stub: information the session already held never
    reached the model.

    1. The session's free-text `notes` field was read by nothing. In the
       reported case it was the ONLY place the actual complaint was written
       down — "Leaking oil on left side" — while `symptoms` was empty.
    2. `diagnostic_sessions` denormalizes make/model/year at creation AND
       keeps a `vehicle_id`. Nothing re-syncs them. The user corrected
       "Homda" to "Honda" in the garage and the session kept reporting the
       typo, so the analysis would have gone on naming the wrong marque
       forever after the data was fixed."""

    def test_session_notes_reach_the_prompt(self):
        s = VehicleContext(
            make="Honda", model="CBR600F4i", year=2001,
            notes="[2026-09-09T19:54] Leaking oil on left side",
        ).to_context_string()
        assert "Leaking oil on left side" in s, (
            "the technician's own account of the fault must reach the model"
        )

    def test_blank_notes_add_no_line(self):
        s = VehicleContext(make="Honda", model="CBR600RR", year=2008, notes="   ").to_context_string()
        assert "Technician notes" not in s

    def test_notes_alone_are_enough_to_avoid_the_no_context_string(self):
        """The failure mode being guarded is the literal 'nothing is known'
        sentence, so any real content must displace it."""
        assert VehicleContext(notes="weeping at the stator cover").to_context_string() \
            != "No vehicle context provided."

    def test_the_live_vehicle_row_wins_over_a_stale_session_snapshot(self, tmp_path):
        """The exact bug the user reported: fixed in the garage, stale in the
        session."""
        import sqlite3
        from motodiag.core import database as db_mod
        import motodiag.core.session_repo as sr

        p = tmp_path / "t.db"
        conn = sqlite3.connect(p)
        conn.execute("CREATE TABLE vehicles (id INTEGER PRIMARY KEY, make TEXT, model TEXT, year INTEGER, mileage INTEGER)")
        conn.execute("INSERT INTO vehicles VALUES (10, 'Honda', 'CBR600F4i', 2001, 18200)")
        conn.commit(); conn.close()

        session = {"vehicle_make": "Homda", "vehicle_model": "cbrf4i", "vehicle_year": 2001,
                   "vehicle_id": 10, "symptoms": [], "notes": "Leaking oil on left side"}
        orig_sess, orig_conn = sr.get_session, db_mod.get_connection

        def _conn(path=None):
            import contextlib
            @contextlib.contextmanager
            def _cm():
                c = sqlite3.connect(p); c.row_factory = sqlite3.Row
                try: yield c
                finally: c.close()
            return _cm()

        sr.get_session = lambda *a, **k: session
        db_mod.get_connection = _conn
        try:
            vc = vap_worker._build_vehicle_context({"session_id": 6}, db_path=str(p))
        finally:
            sr.get_session, db_mod.get_connection = orig_sess, orig_conn

        assert vc.make == "Honda", "the garage correction must win over the session's snapshot"
        assert vc.model == "CBR600F4i"
        assert vc.mileage == 18200
        assert "Homda" not in vc.to_context_string()
        assert "Leaking oil on left side" in vc.to_context_string()

    def test_a_blank_live_field_does_not_erase_the_snapshot(self, tmp_path):
        """Preferring the live row must not become 'trust an empty garage
        field over a populated session'."""
        import sqlite3, contextlib
        from motodiag.core import database as db_mod
        import motodiag.core.session_repo as sr

        p = tmp_path / "t2.db"
        conn = sqlite3.connect(p)
        conn.execute("CREATE TABLE vehicles (id INTEGER PRIMARY KEY, make TEXT, model TEXT, year INTEGER, mileage INTEGER)")
        conn.execute("INSERT INTO vehicles VALUES (11, '', NULL, NULL, NULL)")
        conn.commit(); conn.close()

        session = {"vehicle_make": "Honda", "vehicle_model": "CBR600RR", "vehicle_year": 2008,
                   "vehicle_id": 11, "symptoms": [], "notes": ""}
        orig_sess, orig_conn = sr.get_session, db_mod.get_connection

        def _conn(path=None):
            @contextlib.contextmanager
            def _cm():
                c = sqlite3.connect(p); c.row_factory = sqlite3.Row
                try: yield c
                finally: c.close()
            return _cm()

        sr.get_session = lambda *a, **k: session
        db_mod.get_connection = _conn
        try:
            vc = vap_worker._build_vehicle_context({"session_id": 9}, db_path=str(p))
        finally:
            sr.get_session, db_mod.get_connection = orig_sess, orig_conn

        assert (vc.make, vc.model, vc.year) == ("Honda", "CBR600RR", 2008)
