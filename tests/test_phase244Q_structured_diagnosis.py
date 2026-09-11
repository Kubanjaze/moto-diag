"""Phase 244Q — the text diagnosis stops guessing at its own output.

`motodiag diagnose quick` completed after the hotfix earlier the same day and
produced something worse than the crash it replaced: the response came back at
exactly the 2048-token cap, truncated mid-JSON, parsing failed, and the fallback
stored the raw text as the diagnosis with a hardcoded ``confidence=0.5`` and
``severity=medium``. The command reported success.

Two guards here matter more than the rest.

``TestTruncationIsLoud`` — the cap was never the bug. ``stop_reason`` is what
the API uses to say it ran out of room, and nothing in ``client.py`` read it.
Raising the cap makes truncation rarer; reading ``stop_reason`` makes it
visible, and only the second one stops a silent degradation.

``TestTheCacheCannotServeThePreFixBlob`` — ``diagnose()`` hashes only semantic
inputs, not the prompt or the response format, so without a version bump the
truncated row written before this fix would serve that query forever: immune to
the fix, and indistinguishable from a good row. The code predicted this in its
own comment and named the remedy.
"""

from __future__ import annotations

import json
from unittest import mock

import pytest

from support.source_guards import code_of

from motodiag.core.config import Settings
from motodiag.engine import client as client_mod
from motodiag.engine.client import (
    DIAGNOSE_CACHE_KIND,
    MODEL_ALIASES,
    DiagnosticClient,
    ResponseTruncated,
    ToolRefused,
    build_diagnosis_tool,
)
from motodiag.engine.models import DiagnosticResponse

AUTHORED_FIELDS = {
    "vehicle_summary",
    "symptoms_acknowledged",
    "diagnoses",
    "additional_tests",
    "notes",
}


def _tool_use_block(payload: dict):
    b = mock.Mock()
    b.type = "tool_use"
    b.input = payload
    return b


def _api_response(*, blocks, stop_reason="tool_use", out_tokens=500):
    r = mock.Mock()
    r.content = blocks
    r.stop_reason = stop_reason
    r.usage = mock.Mock(input_tokens=400, output_tokens=out_tokens)
    return r


def _good_payload() -> dict:
    return {
        "vehicle_summary": "2001 Honda CBR600F4i",
        "symptoms_acknowledged": ["oil leak left side"],
        "diagnoses": [
            {
                "diagnosis": "Left crankcase cover gasket weeping",
                "confidence": 0.72,
                "severity": "medium",
                "evidence": ["Wet film below the cover, dry above"],
                "repair_steps": ["Drain oil", "Replace cover gasket"],
            }
        ],
        "additional_tests": ["Clean and re-run for five minutes"],
        "notes": "",
    }


@pytest.fixture
def api_client(monkeypatch):
    """A DiagnosticClient whose SDK call is entirely under test control."""
    c = DiagnosticClient(api_key="test-key-not-real")
    fake_sdk = mock.Mock()
    monkeypatch.setattr(c, "_get_client", lambda: fake_sdk)
    return c, fake_sdk


# ---------------------------------------------------------------------------


class TestTruncationIsLoud:
    """The cap was never the bug. Not looking at `stop_reason` was."""

    def test_a_truncated_response_raises(self, api_client):
        c, sdk = api_client
        sdk.messages.create.return_value = _api_response(
            blocks=[_tool_use_block(_good_payload())],
            stop_reason="max_tokens",
        )
        with pytest.raises(ResponseTruncated) as exc:
            c.ask_structured("prompt", build_diagnosis_tool())
        assert "cut off" in str(exc.value)

    def test_it_raises_even_when_the_partial_block_would_parse(self, api_client):
        """A truncated tool_use block can still look plausible, and plausible
        is exactly what must not reach the database."""
        c, sdk = api_client
        sdk.messages.create.return_value = _api_response(
            blocks=[_tool_use_block(_good_payload())],
            stop_reason="max_tokens",
        )
        with pytest.raises(ResponseTruncated):
            c.ask_structured("prompt", build_diagnosis_tool())

    def test_the_exception_carries_the_usage_that_was_paid_for(self, api_client):
        c, sdk = api_client
        sdk.messages.create.return_value = _api_response(
            blocks=[_tool_use_block(_good_payload())],
            stop_reason="max_tokens", out_tokens=4096,
        )
        with pytest.raises(ResponseTruncated) as exc:
            c.ask_structured("prompt", build_diagnosis_tool())
        assert exc.value.usage is not None
        assert exc.value.usage.output_tokens == 4096
        assert exc.value.max_tokens == c.max_tokens

    def test_stop_reason_is_actually_read(self):
        src = code_of(client_mod.DiagnosticClient.ask_structured)
        assert "stop_reason" in src, (
            "the API reports truncation here and the old code never looked"
        )

    def test_diagnose_does_not_swallow_truncation(self):
        """A cut-off diagnosis must reach the caller as an error. The old
        behaviour stored the fragment with a confidence nobody computed."""
        src = code_of(client_mod.DiagnosticClient.diagnose)
        assert "except ResponseTruncated" in src and "raise" in src


class TestTheCacheCannotServeThePreFixBlob:
    def test_the_kind_is_versioned(self):
        assert DIAGNOSE_CACHE_KIND == "diagnose-v2"  # f9-noqa: ssot-pin contract-pin: Phase 244Q cache-format pin. The literal is the point — this phase changes what a stored diagnose response IS, and diagnose() hashes only semantic inputs, so an unversioned key would let the pre-fix truncated row serve that query forever. Bumping requires deciding that stored responses from the prior format must stop matching.

    def test_a_v1_row_never_serves_a_v2_lookup(self):
        from motodiag.engine.cache import _make_cache_key

        payload = {"make": "Honda", "model_name": "CBR600F4i", "year": 2001}
        assert _make_cache_key("diagnose", payload) != _make_cache_key(
            DIAGNOSE_CACHE_KIND, payload
        ), "the pre-fix blob must be unreachable"

    def test_diagnose_uses_the_versioned_kind_on_both_read_and_write(self):
        src = code_of(client_mod.DiagnosticClient.diagnose)
        assert src.count("DIAGNOSE_CACHE_KIND") == 2, (
            "both the lookup and the store must use the versioned kind, or "
            "reads and writes disagree"
        )
        assert '"diagnose"' not in src, "a literal v1 kind is still in use"


class TestTheToolForcesStructure:
    def test_the_tool_choice_is_forced(self, api_client):
        c, sdk = api_client
        sdk.messages.create.return_value = _api_response(
            blocks=[_tool_use_block(_good_payload())]
        )
        c.ask_structured("prompt", build_diagnosis_tool())
        kwargs = sdk.messages.create.call_args.kwargs
        assert kwargs["tool_choice"] == {
            "type": "tool", "name": "report_diagnosis",
        }, "an unforced tool_choice lets the model answer in prose again"

    def test_the_schema_carries_exactly_the_authored_fields(self):
        props = set(build_diagnosis_tool()["input_schema"]["properties"])
        assert props == AUTHORED_FIELDS

    def test_the_schema_keeps_its_defs(self):
        """`DiagnosisItem` and `DiagnosticSeverity` are referenced by $ref, so
        a stripped schema would be unresolvable."""
        schema = build_diagnosis_tool()["input_schema"]
        assert "$defs" in schema
        assert {"DiagnosisItem", "DiagnosticSeverity"} <= set(schema["$defs"])

    def test_the_tool_input_becomes_a_real_response_with_no_text_parsing(
        self, api_client
    ):
        c, sdk = api_client
        sdk.messages.create.return_value = _api_response(
            blocks=[_tool_use_block(_good_payload())]
        )
        payload, usage = c.ask_structured("prompt", build_diagnosis_tool())
        parsed = DiagnosticResponse(**payload)
        assert parsed.diagnoses[0].confidence == 0.72
        assert parsed.diagnoses[0].repair_steps == ["Drain oil",
                                                    "Replace cover gasket"]
        assert usage.output_tokens == 500

    def test_no_tool_use_block_raises_rather_than_guessing(self, api_client):
        c, sdk = api_client
        text_block = mock.Mock(spec=["text"])
        text_block.text = "prose instead of a tool call"
        sdk.messages.create.return_value = _api_response(blocks=[text_block])
        with pytest.raises(ToolRefused, match="no tool_use"):
            c.ask_structured("prompt", build_diagnosis_tool())


class TestTheSiblingRule:
    """`ask()` has five callers outside the diagnosis path. The codebase wrote
    the rule down in `ask_with_images`: a sibling method, not a replacement."""

    def test_ask_still_returns_text_and_forces_no_tool(self, api_client):
        c, sdk = api_client
        block = mock.Mock()
        block.text = "plain prose"
        sdk.messages.create.return_value = _api_response(blocks=[block])
        text, usage = c.ask("prompt")
        assert text == "plain prose"
        kwargs = sdk.messages.create.call_args.kwargs
        assert "tool_choice" not in kwargs, "ask() must stay free-text"
        assert "tools" not in kwargs

    def test_ask_is_untouched_by_this_phase(self):
        src = code_of(client_mod.DiagnosticClient.ask)
        for forbidden in ("tool_choice", "ResponseTruncated", "stop_reason"):
            assert forbidden not in src, (
                f"{forbidden} leaked into ask(), which five shop callers rely on"
            )

    def test_the_shop_callers_still_exist_and_use_ask(self):
        """Named so the blast radius is pinned rather than remembered."""
        import pathlib

        callers = [
            "src/motodiag/shop/parts_sourcing.py",
            "src/motodiag/shop/labor_estimator.py",
            "src/motodiag/shop/ai_client.py",
            "src/motodiag/shop/priority_scorer.py",
        ]
        for path in callers:
            src = pathlib.Path(path).read_text(encoding="utf-8")
            assert ".ask(" in src, f"{path} no longer calls ask()"


class TestTheCap:
    def test_the_default_is_raised(self):
        assert Settings().max_tokens == 4096  # f9-noqa: ssot-pin contract-pin: Phase 244Q cap pin. The literal is the point — 2048 truncated a structured diagnosis mid-JSON and the failure was silent. Raising this is a cost decision, so a change should be deliberate and reviewed, not incidental.

    def test_it_is_inside_the_validator_range(self):
        Settings(max_tokens=4096)
        with pytest.raises(ValueError):
            Settings(max_tokens=8193)

    def test_the_cap_alone_is_not_treated_as_the_fix(self):
        """Raising the cap makes truncation rarer. Reading stop_reason makes
        it visible. Only the second one is a fix, and both must be present."""
        src = code_of(client_mod.DiagnosticClient.ask_structured)
        assert "stop_reason" in src
        assert "ResponseTruncated" in src


class TestTheFallbackStaysHonest:
    def test_a_refused_tool_costs_exactly_one_api_call(self, api_client):
        """The invariant that matters, and the one the first version broke.

        A refusal used to call `ask()` again — a **second paid call** on every
        structured failure. The cache integration tests caught it as
        `call_count == 2` in the full regression, not here, because these
        guards mocked at the wrong level to see it. Now the refusal carries the
        prose it already paid for.

        Written first as two source-text assertions, the second ending
        `or True` and therefore passing unconditionally. Replaced twice: once
        for vacuity, once for testing the wrong thing.
        """
        c, sdk = api_client
        prose = mock.Mock(spec=["text"])
        prose.text = "Probably the clutch cover gasket."
        sdk.messages.create.return_value = _api_response(blocks=[prose])

        result, usage = c.diagnose(
            make="Honda", model_name="CBR600F4i", year=2001,
            symptoms=["oil leak"], use_cache=False,
        )
        assert sdk.messages.create.call_count == 1, (
            "a refusal must not trigger a second paid call"
        )
        assert "clutch cover gasket" in result.diagnoses[0].diagnosis
        assert usage.output_tokens == 500, "the paid-for usage is reused"

    def test_the_refusal_carries_the_text_it_already_paid_for(self, api_client):
        c, sdk = api_client
        prose = mock.Mock(spec=["text"])
        prose.text = "some prose"
        sdk.messages.create.return_value = _api_response(blocks=[prose])
        with pytest.raises(ToolRefused) as exc:
            c.ask_structured("prompt", build_diagnosis_tool())
        assert exc.value.text == "some prose"
        assert exc.value.usage is not None

    def test_diagnose_never_calls_ask_on_the_fallback_path(self):
        src = code_of(client_mod.DiagnosticClient.diagnose)
        assert "self.ask(" not in src, (
            "calling ask() in the fallback is what doubled the cost of every "
            "refusal; the prose comes back on the ToolRefused instead"
        )

    def test_a_truncation_is_NOT_treated_as_a_refusal(self, api_client, monkeypatch):
        """The fallback must not rescue a truncation — that is precisely how a
        cut-off response became a stored diagnosis with an invented confidence."""
        c, _sdk = api_client
        monkeypatch.setattr(
            c, "ask_structured",
            mock.Mock(side_effect=ResponseTruncated("cut off", max_tokens=4096)),
        )
        fallback = mock.Mock()
        monkeypatch.setattr(c, "ask", fallback)
        with pytest.raises(ResponseTruncated):
            c.diagnose(
                make="Honda", model_name="CBR600F4i", year=2001,
                symptoms=["oil leak"], use_cache=False,
            )
        assert not fallback.called, "truncation must surface, not degrade"

    def test_the_fallback_is_reached_only_after_the_tool_path_fails(self):
        src = code_of(client_mod.DiagnosticClient.diagnose)
        tool_at = src.index("ask_structured")
        fallback_at = src.index("_parse_diagnostic_response")
        assert tool_at < fallback_at, (
            "the structured path must be tried first, not second"
        )


class TestTheTextPathReachesTheLedger:
    """Folded in after the operator's point: everything else in this phase
    tuned a path that wrote nothing to the cost ledger.

    `cost_events.kind` took whisper, claude_extraction and the two vision
    kinds. Phase 244L widened it for vision; text diagnosis was never in it.
    So `max_tokens` was raised against spend nobody could measure.
    """

    @pytest.fixture
    def ledger_db(self, tmp_path, monkeypatch):
        from motodiag.core.database import init_db

        path = str(tmp_path / "ledger.db")
        init_db(path)
        return path

    def _rows(self, path):
        from motodiag.core.database import get_connection

        with get_connection(path) as conn:
            return [
                dict(zip(
                    ["kind", "model", "cents", "units_label", "units_value"], r
                ))
                for r in conn.execute(
                    "SELECT kind, model, cost_usd_cents, units_label, "
                    "units_value FROM cost_events"
                )
            ]

    def test_the_kind_is_accepted_by_the_database(self, ledger_db):
        from motodiag.shop.cost_repo import record_cost_event

        record_cost_event(
            kind="text_diagnosis", model="haiku", cost_usd_cents=3,
            units_label="tokens", units_value=1200, db_path=ledger_db,
        )
        assert self._rows(ledger_db)[0]["kind"] == "text_diagnosis"

    def test_a_completed_diagnosis_writes_one_row(self, ledger_db):
        from motodiag.engine.models import TokenUsage
        from motodiag.engine.client import record_diagnosis_cost

        record_diagnosis_cost(
            TokenUsage(input_tokens=400, output_tokens=1200,
                       model=MODEL_ALIASES["haiku"], cost_estimate=0.03),
            db_path=ledger_db,
        )
        rows = self._rows(ledger_db)
        assert len(rows) == 1
        assert rows[0]["kind"] == "text_diagnosis"

    def test_it_records_the_completion_length(self, ledger_db):
        """The distribution this accumulates is what should set max_tokens
        later — from a p95, not from doubling 2048 on one observation."""
        from motodiag.engine.models import TokenUsage
        from motodiag.engine.client import record_diagnosis_cost

        record_diagnosis_cost(
            TokenUsage(input_tokens=400, output_tokens=1873,
                       model="haiku", cost_estimate=0.03),
            db_path=ledger_db,
        )
        row = self._rows(ledger_db)[0]
        assert row["units_label"] == "tokens"
        assert row["units_value"] == 1873

    def test_a_truncated_call_is_recorded_because_it_is_pure_waste(
        self, api_client, ledger_db, monkeypatch
    ):
        """Paid in full, unusable output. If waste is invisible in the ledger
        then the most expensive failure mode is the one nobody can see."""
        import motodiag.engine.client as cm

        c, sdk = api_client
        sdk.messages.create.return_value = _api_response(
            blocks=[_tool_use_block(_good_payload())],
            stop_reason="max_tokens", out_tokens=4096,
        )
        recorded = []
        monkeypatch.setattr(
            cm, "record_diagnosis_cost",
            lambda usage, **kw: recorded.append(usage),
        )
        with pytest.raises(ResponseTruncated):
            c.ask_structured("prompt", build_diagnosis_tool())
        assert len(recorded) == 1, "a truncated call must still reach the ledger"
        assert recorded[0].output_tokens == 4096

    def test_a_zero_cost_call_records_nothing(self, ledger_db):
        """A cache hit spends nothing and `ai_response_cache.hit_count`
        already counts the saving; a zero row would dilute the averages."""
        from motodiag.engine.models import TokenUsage
        from motodiag.engine.client import record_diagnosis_cost

        record_diagnosis_cost(
            TokenUsage(input_tokens=0, output_tokens=0, model="haiku",
                       cost_estimate=0.0),
            db_path=ledger_db,
        )
        assert self._rows(ledger_db) == []

    def test_no_usage_records_nothing_and_does_not_raise(self, ledger_db):
        from motodiag.engine.client import record_diagnosis_cost

        record_diagnosis_cost(None, db_path=ledger_db)
        assert self._rows(ledger_db) == []

    def test_a_failing_ledger_write_never_costs_the_diagnosis(self, tmp_path):
        """The call is paid for and the answer is in hand. Phase 244L's
        contract, for the same reason."""
        from motodiag.engine.models import TokenUsage
        from motodiag.engine.client import record_diagnosis_cost

        record_diagnosis_cost(
            TokenUsage(input_tokens=1, output_tokens=1, model="haiku",
                       cost_estimate=0.05),
            db_path=str(tmp_path / "does-not-exist.db"),
        )  # must not raise

    def test_the_report_renders_the_new_kind_with_no_code_change(self, ledger_db):
        from motodiag.shop.cost_repo import aggregate_costs, record_cost_event

        record_cost_event(
            kind="text_diagnosis", model="haiku", cost_usd_cents=7,
            units_label="tokens", units_value=900, db_path=ledger_db,
        )
        roll = aggregate_costs(db_path=ledger_db)
        by_kind = getattr(roll, "by_kind", None) or roll.model_dump()["by_kind"]
        assert by_kind["text_diagnosis"] == 7

    def test_rolling_back_060_rebuilds_rather_than_drops(self, ledger_db):
        """Phase 244L shipped a rollback copied from the migration that
        CREATED this table. 043 may drop it; a CHECK widening may not."""
        from motodiag.core.database import get_connection
        from motodiag.core.migrations import rollback_to_version
        from motodiag.shop.cost_repo import record_cost_event

        record_cost_event(kind="whisper", model="whisper-1",
                          cost_usd_cents=42, db_path=ledger_db)
        record_cost_event(kind="text_diagnosis", model="haiku",
                          cost_usd_cents=7, db_path=ledger_db)

        rollback_to_version(59, db_path=ledger_db)

        rows = self._rows(ledger_db)
        assert [r["kind"] for r in rows] == ["whisper"], (
            "the pre-060 ledger must survive; only rows the narrowed CHECK "
            "cannot hold are discarded"
        )
        with get_connection(ledger_db) as conn:
            idx = {
                r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' "
                    "AND tbl_name='cost_events' AND name NOT LIKE 'sqlite_%'"
                )
            }
        assert idx == {"idx_cost_events_created", "idx_cost_events_shop",
                       "idx_cost_events_kind"}

    def test_a_REAL_diagnose_call_writes_a_ledger_row(
        self, api_client, tmp_path, monkeypatch
    ):
        """The wiring, not the recorder.

        Every other guard in this class calls `record_diagnosis_cost` directly,
        which verifies the function and says nothing about whether `diagnose()`
        ever calls it. Deleting the call site left all of them green — the same
        wrong-layer mistake that let a double API call reach the full
        regression earlier in this phase. This drives `diagnose()` and looks in
        the table.
        """
        from motodiag.core.config import reset_settings
        from motodiag.core.database import get_connection, init_db

        db = str(tmp_path / "wired.db")
        init_db(db)
        monkeypatch.setenv("MOTODIAG_DB_PATH", db)
        reset_settings()
        try:
            c, sdk = api_client
            sdk.messages.create.return_value = _api_response(
                blocks=[_tool_use_block(_good_payload())], out_tokens=1873,
            )
            c.diagnose(
                make="Honda", model_name="CBR600F4i", year=2001,
                symptoms=["oil leak"], use_cache=False,
            )
            with get_connection(db) as conn:
                rows = conn.execute(
                    "SELECT kind, units_label, units_value FROM cost_events"
                ).fetchall()
            assert len(rows) == 1, "diagnose() must reach the ledger"
            assert rows[0][0] == "text_diagnosis"
            assert rows[0][1] == "tokens"
            assert rows[0][2] == 1873
        finally:
            reset_settings()
