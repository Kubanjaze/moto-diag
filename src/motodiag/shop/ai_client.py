"""Shared Anthropic client helpers for Track G AI phases (163, 166, 167).

Phase 162.5 — micro-phase. Three independent Track G AI planners (163,
166, 167) flagged the exact same duplication risk: each would
re-implement Anthropic SDK setup, cost-cents math, prompt-cache
toggling, and JSON-fence extraction. This module is the single
authoritative implementation; subsequent AI phases compose on it.

Public surface
--------------

- :class:`ShopAIClient` — thin wrapper over the Anthropic SDK with
  ephemeral prompt caching, Phase 131 ``ai_response_cache`` integration,
  and TokenUsage / cost-cents tracking.
- :func:`resolve_model` — alias resolver (haiku/sonnet/opus → full ids).
- :func:`calculate_cost` — token usage → integer cents.
- :func:`extract_json_block` — strip markdown fences from model output.
- :func:`get_anthropic_client` — lazy singleton (``functools.lru_cache``).

Track G AI phases import from here; no phase should ``import anthropic``
directly. The grep test in each AI phase enforces this.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Optional

from motodiag.core.config import get_settings


# ---------------------------------------------------------------------------
# Model alias + pricing tables
# ---------------------------------------------------------------------------


MODEL_ALIASES: dict[str, str] = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-7",
}


# Cost per million tokens, in cents. Kept in sync with engine/client.py.
# Tuple is (input_cents_per_mtok, output_cents_per_mtok).
MODEL_PRICING: dict[str, tuple[int, int]] = {
    "claude-haiku-4-5-20251001": (80, 400),
    "claude-sonnet-4-6":         (300, 1500),
    "claude-opus-4-7":           (1500, 7500),
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0


@dataclass(frozen=True)
class AIResponse:
    text: str
    model: str
    usage: TokenUsage
    cost_cents: int
    cache_hit: bool = False


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ShopAIClientError(RuntimeError):
    """Wraps Anthropic SDK errors + setup failures into a stable type."""


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def resolve_model(alias_or_full: str) -> str:
    """Resolve 'haiku'/'sonnet'/'opus' to full model ids; passthrough otherwise.

    Raises :class:`ShopAIClientError` on unknown alias.
    """
    if alias_or_full in MODEL_ALIASES:
        return MODEL_ALIASES[alias_or_full]
    if alias_or_full in MODEL_PRICING:
        return alias_or_full
    raise ShopAIClientError(f"unknown model alias: {alias_or_full!r}")


def calculate_cost(model: str, usage: TokenUsage) -> int:
    """Return AI call cost in integer cents.

    Cache reads are 10% of normal input cost. Cache writes are 125% of
    normal input cost (one-time fee on cache creation; subsequent hits
    pay only the 10% rate).
    """
    if model not in MODEL_PRICING:
        return 0
    in_c, out_c = MODEL_PRICING[model]
    in_cost = (usage.input_tokens * in_c) / 1_000_000
    in_cost += (usage.cache_read_tokens * in_c * 0.1) / 1_000_000
    in_cost += (usage.cache_creation_tokens * in_c * 1.25) / 1_000_000
    out_cost = (usage.output_tokens * out_c) / 1_000_000
    return int(round(in_cost + out_cost))


def extract_json_block(text: str) -> str:
    """Strip ``\\`\\`\\`json ... \\`\\`\\``` or bare ``\\`\\`\\``` fences if present.

    Returns the bare JSON body. If no fences detected, returns input
    stripped of leading/trailing whitespace.
    """
    s = text.strip()
    if s.startswith("```"):
        lines = s.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].rstrip() == "```":
            lines = lines[:-1]
        s = "\n".join(lines)
    return s.strip()


@lru_cache(maxsize=1)
def get_anthropic_client(api_key: Optional[str] = None):
    """Lazy singleton Anthropic client.

    api_key defaults to ``settings.anthropic_api_key``. Raises
    :class:`ShopAIClientError` when SDK is missing or key not configured.

    Cached via ``functools.lru_cache(maxsize=1)`` — call
    ``get_anthropic_client.cache_clear()`` to force a re-init when the
    api_key changes (tests use this).
    """
    try:
        import anthropic  # noqa
    except ImportError as e:
        raise ShopAIClientError("anthropic SDK not installed") from e

    key = api_key or get_settings().anthropic_api_key
    if not key:
        raise ShopAIClientError("ANTHROPIC_API_KEY not configured")
    return anthropic.Anthropic(api_key=key)


# ---------------------------------------------------------------------------
# ShopAIClient
# ---------------------------------------------------------------------------


class ShopAIClient:
    """High-level wrapper for Track G AI phases.

    Usage::

        client = ShopAIClient(model="haiku")
        response = client.ask(
            user_prompt="...",
            system_prompt="...",            # cached via ephemeral cache_control
            cache_kind="priority_score",    # Phase 131 ai_response_cache partition
            cache_payload={...},            # SHA256-keyed dedupe payload
            max_tokens=512,
            temperature=0.2,
        )
        # response.text, response.model, response.usage, response.cost_cents,
        # response.cache_hit
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

        Cache layer (Phase 131 ``ai_response_cache``):
        - If ``cache_kind`` + ``cache_payload`` supplied, checks cache
          first; on hit returns cached text with cost_cents=0,
          cache_hit=True.
        - On miss, calls Claude + persists the result + returns fresh
          response with cache_hit=False.

        System prompt sent with ``cache_control={"type": "ephemeral"}``
        so subsequent calls within the 5-minute window pay only the 10%
        cache-read rate on the cached input tokens.
        """
        # --- Phase 131 cache check ---
        cache_key: Optional[str] = None
        if cache_kind and cache_payload is not None:
            from motodiag.engine.cache import (
                _make_cache_key, get_cached_response,
            )
            cache_key = _make_cache_key(cache_kind, cache_payload)
            cached = get_cached_response(cache_key, db_path=db_path)
            if cached is not None:
                # Cached response_dict shape: {"text": "...",
                # "model": "...", "input_tokens": N, "output_tokens": N}
                resp = cached["response"]
                return AIResponse(
                    text=str(resp.get("text", "")),
                    model=str(resp.get("model", self.model)),
                    usage=TokenUsage(
                        input_tokens=0,
                        output_tokens=0,
                        cache_read_tokens=cached.get("tokens_input", 0) or 0,
                    ),
                    cost_cents=0,
                    cache_hit=True,
                )

        # --- Live call ---
        client = get_anthropic_client(self.api_key)
        system_blocks: list = []
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
                temperature=(
                    temperature if temperature is not None
                    else self.temperature
                ),
                system=system_blocks if system_blocks else None,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except Exception as e:
            raise ShopAIClientError(f"Claude API call failed: {e}") from e

        # Extract text from content blocks
        text_parts: list[str] = []
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                text_parts.append(block.text)
        text = "".join(text_parts)

        usage = TokenUsage(
            input_tokens=getattr(resp.usage, "input_tokens", 0) or 0,
            output_tokens=getattr(resp.usage, "output_tokens", 0) or 0,
            cache_creation_tokens=(
                getattr(resp.usage, "cache_creation_input_tokens", 0) or 0
            ),
            cache_read_tokens=(
                getattr(resp.usage, "cache_read_input_tokens", 0) or 0
            ),
        )
        cost_cents = calculate_cost(self.model, usage)

        # --- Persist to Phase 131 cache (failures must NOT break the call) ---
        if cache_kind and cache_key is not None:
            try:
                from motodiag.engine.cache import set_cached_response
                set_cached_response(
                    cache_key=cache_key,
                    kind=cache_kind,
                    model_used=self.model,
                    response_dict={
                        "text": text,
                        "model": self.model,
                        "input_tokens": usage.input_tokens,
                        "output_tokens": usage.output_tokens,
                    },
                    tokens_input=usage.input_tokens,
                    tokens_output=usage.output_tokens,
                    cost_cents=cost_cents,
                    db_path=db_path,
                )
            except Exception:
                # Cache write errors are silent — never break the call.
                pass

        return AIResponse(
            text=text, model=self.model, usage=usage,
            cost_cents=cost_cents, cache_hit=False,
        )
