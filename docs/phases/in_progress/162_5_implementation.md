# MotoDiag Phase 162.5 — Shared AI Client Helper

**Version:** 1.0 | **Tier:** Micro | **Date:** 2026-04-21

## Goal

Micro-phase inserted between Phase 162 and Phase 163 per consolidation notes. Three Track G AI planners (163, 166, 167) independently flagged code triplication around Anthropic client setup, cost-cents math, prompt caching, and JSON extraction from markdown fences. Extract the shared primitives into `src/motodiag/shop/ai_client.py` BEFORE Phase 163 ships — rule-of-three extract, saves ~250 LoC across the next three AI phases.

No migration. No new CLI. No new subgroup. Pure refactor-in-place creating a new helper module.

Outputs:

- `src/motodiag/shop/ai_client.py` (~180 LoC) — shared helpers.
- `src/motodiag/shop/__init__.py` +10 LoC — re-export `ShopAIClient`, `resolve_model`, `calculate_cost`, `MODEL_PRICING`, `MODEL_ALIASES`.
- `tests/test_phase162_5_ai_client.py` (~15 tests).

## Logic

### `src/motodiag/shop/ai_client.py` contract

```python
"""Shared Anthropic client helpers for Track G AI phases (163, 166, 167).

Extracted from the duplicate patterns three Track G AI planners flagged.
Wraps the Anthropic SDK with:
- Lazy client init (module-level singleton via functools.lru_cache).
- Model alias resolution (haiku/sonnet/opus → full model ids).
- Token → cost-cents calculation (shared MODEL_PRICING table).
- Prompt caching enabled via ephemeral cache_control on system blocks.
- JSON-from-markdown-fence extraction for responses that wrap in ```json ... ```.
- Integration with Phase 131 ai_response_cache for cross-session memoization.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Optional

from motodiag.core.config import get_settings


MODEL_ALIASES: dict[str, str] = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-7",
}


# Cost per million tokens, in cents. Kept in sync with engine/client.py.
MODEL_PRICING: dict[str, tuple[int, int]] = {
    "claude-haiku-4-5-20251001": (80, 400),    # (input_c_per_mtok, output_c_per_mtok)
    "claude-sonnet-4-6":         (300, 1500),
    "claude-opus-4-7":           (1500, 7500),
}


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0


@dataclass(frozen=True)
class AIResponse:
    text: str
    model: str
    usage: TokenUsage
    cost_cents: int
    cache_hit: bool = False


class ShopAIClientError(RuntimeError):
    """Wraps Anthropic SDK errors into a stable exception type."""


def resolve_model(alias_or_full: str) -> str:
    """Resolve 'haiku'/'sonnet'/'opus' to full model ids; passthrough otherwise."""
    if alias_or_full in MODEL_ALIASES:
        return MODEL_ALIASES[alias_or_full]
    if alias_or_full in MODEL_PRICING:
        return alias_or_full
    raise ShopAIClientError(f"unknown model alias: {alias_or_full!r}")


def calculate_cost(model: str, usage: TokenUsage) -> int:
    """Return AI call cost in integer cents. model is a full model id."""
    if model not in MODEL_PRICING:
        return 0
    in_c, out_c = MODEL_PRICING[model]
    # Cache reads are 10% of normal input cost; cache writes are 25% more.
    in_cost = (usage.input_tokens * in_c) / 1_000_000
    in_cost += (usage.cache_read_tokens * in_c * 0.1) / 1_000_000
    in_cost += (usage.cache_creation_tokens * in_c * 1.25) / 1_000_000
    out_cost = (usage.output_tokens * out_c) / 1_000_000
    return int(round(in_cost + out_cost))


@lru_cache(maxsize=1)
def get_anthropic_client(api_key: Optional[str] = None):
    """Lazy singleton Anthropic client. api_key defaults to settings.anthropic_api_key."""
    try:
        import anthropic  # noqa
    except ImportError as e:
        raise ShopAIClientError("anthropic SDK not installed") from e

    key = api_key or get_settings().anthropic_api_key
    if not key:
        raise ShopAIClientError("ANTHROPIC_API_KEY not configured")
    return anthropic.Anthropic(api_key=key)


def extract_json_block(text: str) -> str:
    """Strip ```json ... ``` or ``` ... ``` fences if present. Returns bare body."""
    s = text.strip()
    if s.startswith("```"):
        lines = s.splitlines()
        # Drop leading ```json or ``` and trailing ```
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].rstrip() == "```":
            lines = lines[:-1]
        s = "\n".join(lines)
    return s.strip()


class ShopAIClient:
    """High-level wrapper for Track G AI phases.

    Usage:
        client = ShopAIClient(model="haiku")
        response = client.ask(
            user_prompt="...",
            system_prompt="...",           # cached via ephemeral cache_control
            cache_kind="priority_score",   # Phase 131 ai_response_cache partition
            cache_payload={...},           # SHA256-keyed dedupe payload
            max_tokens=512,
            temperature=0.2,
        )
        # response.text, response.model, response.usage, response.cost_cents, response.cache_hit
    """

    def __init__(
        self,
        model: str = "haiku",
        api_key: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ):
        self.model = resolve_model(model)
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.temperature = temperature

    def ask(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        *,
        cache_kind: Optional[str] = None,
        cache_payload: Optional[dict] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        db_path: Optional[str] = None,
    ) -> AIResponse:
        """Send a prompt. Returns AIResponse with text + usage + cost.

        If cache_kind + cache_payload are supplied, checks Phase 131
        ai_response_cache first; on miss, calls Claude + caches the result.
        System prompt is sent with cache_control={"type": "ephemeral"}.
        """
        # --- Phase 131 cache layer ---
        if cache_kind and cache_payload:
            from motodiag.engine.cache import (
                _make_cache_key, get_cached_response, set_cached_response,
            )
            cache_key = _make_cache_key(cache_kind, cache_payload)
            cached = get_cached_response(cache_key, db_path=db_path)
            if cached is not None:
                return AIResponse(
                    text=cached["response_text"],
                    model=cached.get("ai_model", self.model),
                    usage=TokenUsage(
                        input_tokens=0, output_tokens=0,
                        cache_read_tokens=cached.get("tokens_input", 0),
                    ),
                    cost_cents=0,
                    cache_hit=True,
                )

        client = get_anthropic_client(self.api_key)
        system_blocks = []
        if system_prompt:
            system_blocks = [{
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }]
        try:
            resp = client.messages.create(
                model=self.model,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature or self.temperature,
                system=system_blocks if system_blocks else None,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except Exception as e:
            raise ShopAIClientError(f"Claude API call failed: {e}") from e

        # Extract text (SDK returns a list of content blocks)
        text_parts = []
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                text_parts.append(block.text)
        text = "".join(text_parts)

        usage = TokenUsage(
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            cache_creation_tokens=getattr(resp.usage, "cache_creation_input_tokens", 0) or 0,
            cache_read_tokens=getattr(resp.usage, "cache_read_input_tokens", 0) or 0,
        )
        cost_cents = calculate_cost(self.model, usage)

        # Persist to Phase 131 cache if requested
        if cache_kind and cache_payload:
            try:
                from motodiag.engine.cache import (
                    _make_cache_key, set_cached_response,
                )
                cache_key = _make_cache_key(cache_kind, cache_payload)
                set_cached_response(
                    cache_key, cache_kind, text,
                    tokens_input=usage.input_tokens,
                    tokens_output=usage.output_tokens,
                    cost_cents=cost_cents,
                    ai_model=self.model,
                    db_path=db_path,
                )
            except Exception:
                # Cache errors must not break the call.
                pass

        return AIResponse(
            text=text, model=self.model, usage=usage,
            cost_cents=cost_cents, cache_hit=False,
        )
```

### `shop/__init__.py` additions

```python
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
```

### Test plan — `tests/test_phase162_5_ai_client.py` (~15 tests, 2 classes)

**`TestHelpers` (~8):**
- `test_resolve_model_aliases` — haiku/sonnet/opus → full ids
- `test_resolve_model_passthrough_full_id` — already-full id returns itself
- `test_resolve_model_unknown_raises`
- `test_calculate_cost_haiku_math` — known tokens × pricing = expected cents
- `test_calculate_cost_includes_cache_discounts` — cache_read @ 10%, cache_creation @ 125%
- `test_calculate_cost_zero_usage_returns_zero`
- `test_extract_json_block_strips_json_fence`
- `test_extract_json_block_strips_bare_fence`
- `test_extract_json_block_no_fence_passthrough`

**`TestShopAIClient` (~7):**
- `test_init_resolves_model_alias`
- `test_ask_without_cache_calls_anthropic_and_returns_AIResponse` — mock `anthropic.Anthropic.messages.create`
- `test_ask_with_cache_hit_returns_cached_AIResponse` — mock Phase 131 cache hit
- `test_ask_with_cache_miss_calls_anthropic_then_persists` — mock cache miss + set_cached_response
- `test_ask_system_prompt_sent_with_ephemeral_cache_control` — verify kwargs
- `test_ask_sdk_error_wrapped_in_ShopAIClientError`
- `test_ask_cache_write_error_swallowed_response_still_returned`

All tests mock `anthropic.Anthropic` + `motodiag.engine.cache.get_cached_response` / `set_cached_response`. Zero live tokens.

## Key Concepts

- **Rule-of-three extract.** Three independent Track G AI planners (163, 166, 167) flagged the exact same duplication. Extracting now saves ~250 LoC across the three subsequent phases and makes future prompt-cache tuning a one-file change.
- **Prompt caching is always-on.** System prompts are sent with `cache_control={"type":"ephemeral"}` by default. Track G AI phases with stable system prompts (priority rubric, sourcing rules, labor norms) all benefit without opting in per-call.
- **Phase 131 cache integration.** SHA256-keyed dedupe via `kind="xxx"` partition. ShopAIClient transparently checks before calling and persists after. Cache failures silently degrade (call still completes).
- **Lazy singleton client via `@lru_cache(maxsize=1)`.** One Anthropic() instance per process; subsequent calls reuse it.
- **MODEL_PRICING authoritative for Track G.** Kept in sync with `engine/client.py`. A future "billing" phase can unify both into a single canonical table; for now, duplication is tolerable and documented.
- **No CLI. No migration. No new state.** Pure helper module. Micro-phase scope.

## Verification Checklist

- [ ] `from motodiag.shop.ai_client import ShopAIClient, resolve_model, calculate_cost, MODEL_PRICING, MODEL_ALIASES` imports clean.
- [ ] `resolve_model("haiku")` → `"claude-haiku-4-5-20251001"`.
- [ ] `resolve_model("claude-haiku-4-5-20251001")` → passthrough.
- [ ] `resolve_model("gpt-4")` raises `ShopAIClientError`.
- [ ] `calculate_cost("claude-haiku-4-5-20251001", TokenUsage(1_000_000, 0))` returns 80.
- [ ] `calculate_cost` cache_read tokens at 10% of input price.
- [ ] `calculate_cost` cache_creation tokens at 125% of input price.
- [ ] `extract_json_block('```json\n{"a":1}\n```')` returns `'{"a":1}'`.
- [ ] `extract_json_block('{"a":1}')` returns unchanged.
- [ ] `ShopAIClient(model="haiku")` resolves `self.model` to full id.
- [ ] `.ask(user_prompt, system_prompt)` with mocked Anthropic returns `AIResponse(text=..., cost_cents>0, cache_hit=False)`.
- [ ] `.ask` with cache_kind + cache_payload and cached response returns `cache_hit=True`, `cost_cents=0`.
- [ ] `.ask` sends system block with `cache_control={"type":"ephemeral"}` (verified via mock assertion).
- [ ] SDK error wrapped in `ShopAIClientError`.
- [ ] All Phase 160/161/162 tests still GREEN (additive only; no regressions).
- [ ] Full regression GREEN.
- [ ] Zero live API tokens.

## Risks

- **MODEL_PRICING drift vs engine/client.py.** Two copies of the pricing table. Mitigation: documented "update both when Anthropic changes prices"; a future billing phase unifies into one canonical source.
- **Phase 131 cache table migration lag.** If a future migration renames cache columns, both engine/client.py and shop/ai_client.py need updates. Mitigation: shop/ai_client.py uses the public helpers `get_cached_response` / `set_cached_response` from `engine.cache` — those functions own the column names; only one surface to update.
- **`lru_cache(maxsize=1)` + changing api_key.** If the api_key changes mid-session, the cached client still uses the old key. Mitigation: production use is one key per process; tests that need to swap keys call `get_anthropic_client.cache_clear()`.
- **SDK version drift.** Anthropic SDK may evolve the `cache_control` shape. Mitigation: tests verify the shape explicitly; breaking SDK updates surface as test failures, not silent regressions.
