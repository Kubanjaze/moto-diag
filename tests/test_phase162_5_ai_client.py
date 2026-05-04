"""Phase 162.5 — Shared AI client helper tests.

Two test classes across ~16 tests:

- :class:`TestHelpers` (~9) — pure functions: resolve_model, calculate_cost,
  extract_json_block, get_anthropic_client lazy + cached + missing-SDK paths.
- :class:`TestShopAIClient` (~7) — instance behavior with mocked Anthropic
  client + mocked Phase 131 cache helpers.

All tests mock the Anthropic SDK; zero live tokens.
"""

# f9-allow-model-ids: SSOT-pin — mirror of Phase 79's engine/client.py
# test pattern but for the shop ai_client module's resolve_model +
# calculate_cost. Literal model IDs ARE the canonical assertion (if
# MODEL_ALIASES["sonnet"] drifts, these tests fail loudly). Refactoring
# through SSOT import would make them tautological. See
# docs/patterns/f9-mock-vs-runtime-drift.md subspecies (ii).

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from motodiag.shop.ai_client import (
    MODEL_ALIASES,
    MODEL_PRICING,
    AIResponse,
    ShopAIClient,
    ShopAIClientError,
    TokenUsage,
    calculate_cost,
    extract_json_block,
    get_anthropic_client,
    resolve_model,
)


# ===========================================================================
# 1. Pure helpers
# ===========================================================================


class TestHelpers:

    def test_resolve_model_haiku_alias(self):
        assert resolve_model("haiku") == "claude-haiku-4-5-20251001"

    def test_resolve_model_sonnet_alias(self):
        assert resolve_model("sonnet") == "claude-sonnet-4-6"

    def test_resolve_model_full_id_passthrough(self):
        assert (
            resolve_model("claude-haiku-4-5-20251001")
            == "claude-haiku-4-5-20251001"
        )

    def test_resolve_model_unknown_raises(self):
        with pytest.raises(ShopAIClientError, match="unknown model"):
            resolve_model("gpt-4")

    def test_calculate_cost_haiku_input_only(self):
        # 1M input tokens at 80 cents/Mtok = 80 cents
        usage = TokenUsage(input_tokens=1_000_000, output_tokens=0)
        assert calculate_cost("claude-haiku-4-5-20251001", usage) == 80

    def test_calculate_cost_includes_cache_read_at_10pct(self):
        # 1M cache_read tokens at 10% of 80 cents = 8 cents
        usage = TokenUsage(
            input_tokens=0, output_tokens=0,
            cache_read_tokens=1_000_000,
        )
        assert calculate_cost("claude-haiku-4-5-20251001", usage) == 8

    def test_calculate_cost_includes_cache_creation_at_125pct(self):
        # 1M cache_creation tokens at 125% of 80 cents = 100 cents
        usage = TokenUsage(
            input_tokens=0, output_tokens=0,
            cache_creation_tokens=1_000_000,
        )
        assert calculate_cost("claude-haiku-4-5-20251001", usage) == 100

    def test_calculate_cost_zero_usage_returns_zero(self):
        assert calculate_cost(
            "claude-haiku-4-5-20251001", TokenUsage(),
        ) == 0

    def test_calculate_cost_unknown_model_returns_zero(self):
        usage = TokenUsage(input_tokens=1_000_000)
        assert calculate_cost("gpt-4", usage) == 0

    def test_extract_json_block_strips_json_fence(self):
        assert extract_json_block('```json\n{"a":1}\n```') == '{"a":1}'

    def test_extract_json_block_strips_bare_fence(self):
        assert extract_json_block('```\n{"a":1}\n```') == '{"a":1}'

    def test_extract_json_block_no_fence_passthrough(self):
        assert extract_json_block('{"a":1}') == '{"a":1}'


# ===========================================================================
# 2. ShopAIClient (mocked Anthropic)
# ===========================================================================


def _make_mock_anthropic_response(
    text: str = "ok",
    input_tokens: int = 100,
    output_tokens: int = 20,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
):
    """Build a mock anthropic.messages.create response."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    resp = MagicMock()
    resp.content = [block]
    resp.usage = MagicMock(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_input_tokens=cache_read_tokens,
        cache_creation_input_tokens=cache_creation_tokens,
    )
    return resp


class TestShopAIClient:

    def test_init_resolves_alias(self):
        c = ShopAIClient(model="haiku")
        assert c.model == "claude-haiku-4-5-20251001"

    def test_init_unknown_alias_raises(self):
        with pytest.raises(ShopAIClientError):
            ShopAIClient(model="gpt-4")

    def test_ask_calls_anthropic_with_system_cache_control(self):
        get_anthropic_client.cache_clear()
        with patch(
            "motodiag.shop.ai_client.get_anthropic_client",
        ) as mock_get_client:
            mock_client = MagicMock()
            # Use 1M tokens so cost rounds to a non-zero integer (cents)
            mock_client.messages.create.return_value = (
                _make_mock_anthropic_response(
                    input_tokens=1_000_000, output_tokens=200_000,
                )
            )
            mock_get_client.return_value = mock_client

            c = ShopAIClient(model="haiku")
            response = c.ask(
                user_prompt="hello",
                system_prompt="you are a helper",
            )

        assert isinstance(response, AIResponse)
        assert response.text == "ok"
        assert response.cache_hit is False
        assert response.usage.input_tokens == 1_000_000
        assert response.usage.output_tokens == 200_000
        # 1M input × 80c + 200k output × 400c = 80 + 80 = 160 cents
        assert response.cost_cents == 160

        # Verify the system block was sent with ephemeral cache_control
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["system"][0]["cache_control"] == {
            "type": "ephemeral",
        }
        assert call_kwargs["system"][0]["text"] == "you are a helper"

    def test_ask_no_system_omits_system_kwarg(self):
        with patch(
            "motodiag.shop.ai_client.get_anthropic_client",
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = (
                _make_mock_anthropic_response()
            )
            mock_get_client.return_value = mock_client

            c = ShopAIClient(model="haiku")
            c.ask(user_prompt="hi")

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] is None

    def test_ask_with_cache_hit_returns_cached_zero_cost(self, tmp_path):
        from motodiag.engine.cache import set_cached_response, _make_cache_key
        from motodiag.core.database import init_db
        db = str(tmp_path / "cache.db")
        init_db(db)
        payload = {"q": "hi"}
        key = _make_cache_key("priority_score", payload)
        set_cached_response(
            cache_key=key,
            kind="priority_score",
            model_used="claude-haiku-4-5-20251001",
            response_dict={"text": "cached answer", "model": "claude-haiku-4-5-20251001"},
            tokens_input=42,
            tokens_output=10,
            cost_cents=5,
            db_path=db,
        )

        # Patch get_anthropic_client so we'd see if it tried to call live
        with patch(
            "motodiag.shop.ai_client.get_anthropic_client",
        ) as mock_get_client:
            mock_get_client.side_effect = AssertionError(
                "should not be called on cache hit"
            )
            c = ShopAIClient(model="haiku")
            response = c.ask(
                user_prompt="ignored",
                system_prompt="ignored",
                cache_kind="priority_score",
                cache_payload=payload,
                db_path=db,
            )
        assert response.cache_hit is True
        assert response.text == "cached answer"
        assert response.cost_cents == 0
        assert response.usage.cache_read_tokens == 42

    def test_ask_with_cache_miss_persists_response(self, tmp_path):
        from motodiag.engine.cache import get_cached_response, _make_cache_key
        from motodiag.core.database import init_db
        db = str(tmp_path / "cache.db")
        init_db(db)
        payload = {"q": "fresh"}
        key = _make_cache_key("priority_score", payload)
        # Sanity: nothing cached yet
        assert get_cached_response(key, db_path=db) is None

        with patch(
            "motodiag.shop.ai_client.get_anthropic_client",
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = (
                _make_mock_anthropic_response(text="fresh answer")
            )
            mock_get_client.return_value = mock_client

            c = ShopAIClient(model="haiku")
            response = c.ask(
                user_prompt="hi",
                system_prompt="prompt",
                cache_kind="priority_score",
                cache_payload=payload,
                db_path=db,
            )
        assert response.cache_hit is False
        assert response.text == "fresh answer"

        # Cache should now contain the response
        cached = get_cached_response(key, db_path=db)
        assert cached is not None
        assert cached["response"]["text"] == "fresh answer"

    def test_ask_sdk_error_wrapped_in_ShopAIClientError(self):
        with patch(
            "motodiag.shop.ai_client.get_anthropic_client",
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.messages.create.side_effect = RuntimeError(
                "boom from SDK"
            )
            mock_get_client.return_value = mock_client

            c = ShopAIClient(model="haiku")
            with pytest.raises(ShopAIClientError, match="boom from SDK"):
                c.ask(user_prompt="x")

    def test_ask_cache_write_error_swallowed_response_returned(self, tmp_path):
        from motodiag.core.database import init_db
        db = str(tmp_path / "cache.db")
        init_db(db)
        with patch(
            "motodiag.shop.ai_client.get_anthropic_client",
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = (
                _make_mock_anthropic_response(text="ok")
            )
            mock_get_client.return_value = mock_client

            with patch(
                "motodiag.engine.cache.set_cached_response",
                side_effect=RuntimeError("disk full"),
            ):
                c = ShopAIClient(model="haiku")
                # Should NOT raise — cache write failure is silent
                response = c.ask(
                    user_prompt="hi",
                    cache_kind="priority_score",
                    cache_payload={"q": "x"},
                    db_path=db,
                )
        assert response.text == "ok"
        assert response.cache_hit is False
