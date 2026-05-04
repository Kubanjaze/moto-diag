"""Diagnostic engine client — wraps Anthropic SDK for motorcycle diagnostics."""

import json
import logging
import os
import time
from typing import Optional
from datetime import datetime, timezone

from motodiag.core.config import get_settings
from motodiag.engine.cache import (
    _make_cache_key,
    cost_dollars_to_cents,
    get_cached_response,
    set_cached_response,
)
from motodiag.engine.models import (
    DiagnosticResponse,
    DiagnosisItem,
    DiagnosticSeverity,
    TokenUsage,
    SessionMetrics,
)
from motodiag.engine.prompts import (
    DIAGNOSTIC_SYSTEM_PROMPT,
    build_vehicle_context,
    build_symptom_context,
    build_knowledge_context,
    build_full_prompt,
)

_log = logging.getLogger(__name__)

# Model pricing per million tokens (USD) as of 2026-05.
#
# Phase 191B fix-cycle-4 (2026-05-04): the prior "sonnet" entry pointed
# at "claude-sonnet-4-5-20241022" which was a fabricated/unreleased
# model ID — Anthropic's Sonnet 4 family went 4.0 -> 4.6 with no 4.5
# release. Architect-gate caught the bug at re-smoke step 7: the live
# Anthropic API returned 404 not_found_error every Vision call. Latent
# since the engine module was first written; surfaced by Phase 191B's
# Commit 2 because that's the first phase to do REAL Anthropic API
# calls instead of mocked-only test paths. Sixth instance of the F9
# "snapshot/assumption doesn't match runtime" failure family.
#
# When Anthropic releases a new generation, update BOTH the alias map
# AND this pricing dict in lockstep. F15 (filed at fix-cycle-4) wires
# a regression test that asserts the resolved model ID is in a known-
# good set so this drift is caught at pytest-time instead of
# 404-from-live-API time.
MODEL_PRICING = {
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
}

# Default model alias mapping. Aliases insulate callers from full model
# ID changes — bump the value here when Anthropic ships a new generation;
# call sites that pass "sonnet" / "haiku" pick up the new model
# automatically.
MODEL_ALIASES = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
}


def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD for a given model and token counts."""
    pricing = MODEL_PRICING.get(model, {"input": 1.0, "output": 5.0})
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


def _resolve_model(model: str) -> str:
    """Resolve model alias to full model ID."""
    return MODEL_ALIASES.get(model, model)


class DiagnosticClient:
    """Claude API client for motorcycle diagnostic reasoning.

    Wraps the Anthropic SDK with motorcycle-specific configuration:
    - Model selection (haiku for speed/cost, sonnet for complex reasoning)
    - Token tracking and cost monitoring
    - Structured diagnostic response parsing
    - Knowledge base context injection (Track B → Track C bridge)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "haiku",
        max_tokens: int = 2048,
        temperature: float = 0.3,
    ):
        """Initialize the diagnostic client.

        Args:
            api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var,
                     then to settings.anthropic_api_key.
            model: Model alias ("haiku", "sonnet") or full model ID.
            max_tokens: Maximum response tokens.
            temperature: Response temperature (0.0-1.0). Low = consistent diagnostics.
        """
        # Resolve API key: explicit > env var > settings
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not self._api_key:
            settings = get_settings()
            self._api_key = settings.anthropic_api_key

        self.model = _resolve_model(model)
        self.max_tokens = max_tokens
        self.temperature = temperature

        # Session metrics
        self.session = SessionMetrics(
            session_id=f"diag-{int(time.time())}",
            started_at=datetime.now(timezone.utc),
        )

        # Lazy client initialization (don't import anthropic until needed)
        self._client = None

    @property
    def is_configured(self) -> bool:
        """Check if the client has a valid API key configured."""
        return bool(self._api_key and len(self._api_key) > 10)

    def _get_client(self):
        """Lazy-initialize the Anthropic client."""
        if self._client is None:
            if not self.is_configured:
                raise RuntimeError(
                    "Anthropic API key not configured. Set ANTHROPIC_API_KEY environment "
                    "variable or MOTODIAG_ANTHROPIC_API_KEY in .env file."
                )
            import anthropic
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def ask(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> tuple[str, TokenUsage]:
        """Send a raw prompt to Claude and return the response text + token usage.

        This is the low-level method that all higher-level methods build on.

        Args:
            prompt: The user message content.
            system: System prompt override (defaults to DIAGNOSTIC_SYSTEM_PROMPT).
            model: Model override for this call.
            max_tokens: Max tokens override for this call.
            temperature: Temperature override for this call.

        Returns:
            Tuple of (response_text, token_usage).
        """
        client = self._get_client()
        resolved_model = _resolve_model(model) if model else self.model
        resolved_max = max_tokens or self.max_tokens
        resolved_temp = temperature if temperature is not None else self.temperature
        resolved_system = system or DIAGNOSTIC_SYSTEM_PROMPT

        start_ms = int(time.time() * 1000)

        response = client.messages.create(
            model=resolved_model,
            max_tokens=resolved_max,
            temperature=resolved_temp,
            system=resolved_system,
            messages=[{"role": "user", "content": prompt}],
        )

        end_ms = int(time.time() * 1000)
        latency = end_ms - start_ms

        # Extract text from response
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text

        # Build token usage
        usage = TokenUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=resolved_model,
            cost_estimate=_calculate_cost(
                resolved_model,
                response.usage.input_tokens,
                response.usage.output_tokens,
            ),
            latency_ms=latency,
        )

        # Track in session
        self.session.add_usage(usage)

        return text, usage

    def ask_with_images(
        self,
        prompt: str,
        images: list,
        system: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[dict] = None,
    ) -> tuple[object, TokenUsage]:
        """Send a prompt with image content blocks (Claude Vision).

        Phase 191B addition. Builds a multi-content-block messages
        payload from the given image file paths + the text prompt,
        threads through the existing cost / token-usage / session-
        metric tracking, and returns the raw Anthropic ``Message``
        object so callers can inspect ``tool_use`` blocks for
        structured output.

        The cache layer is intentionally NOT used here — the existing
        cache keys hash the prompt string, but image-cache keys would
        need to also hash each image's bytes (potentially expensive
        for 60-frame batches). Image-response caching is a Commit 2
        concern at the earliest, and may not be high-value at all
        given the diagnostic uniqueness of each video. Critically,
        this method does not break the existing ``ask()`` cache path
        — it's a sibling method, not a replacement.

        Args:
            prompt: User text prompt (joined to image blocks as the
                    final ``text`` content block).
            images: Iterable of file paths (``pathlib.Path`` or strings)
                    pointing at JPEG/PNG images. Encoded as base64
                    content blocks in the messages payload.
            system: System prompt override.
            model: Model alias or full model ID override.
            max_tokens: Max tokens override.
            temperature: Temperature override.
            tools: Optional tool definitions for structured output via
                   the Anthropic tool-use trick. When provided the
                   model can (and with ``tool_choice`` must) emit a
                   ``tool_use`` block instead of plain text.
            tool_choice: Optional tool-selection directive. Pass
                   ``{"type": "tool", "name": "..."}`` to force a
                   specific tool call.

        Returns:
            Tuple of ``(raw Message, TokenUsage)``. The raw Message
            lets callers extract ``tool_use`` blocks for structured
            output via something like
            ``next(b for b in resp.content if b.type == "tool_use")``.
        """
        import base64
        from pathlib import Path as _Path

        client = self._get_client()
        resolved_model = (
            _resolve_model(model) if model else self.model
        )
        resolved_max = max_tokens or self.max_tokens
        resolved_temp = (
            temperature if temperature is not None else self.temperature
        )
        resolved_system = system or DIAGNOSTIC_SYSTEM_PROMPT

        # Build image content blocks (base64-encoded). Assume JPEG by
        # default — the upload pipeline only ever produces JPEGs from
        # ffmpeg's frame extractor. PNG/other-format detection via
        # magic bytes is a future enhancement if Vision returns an
        # unsupported-media-type error in practice.
        content_blocks: list[dict] = []
        for img in images:
            img_path = _Path(img)
            img_bytes = img_path.read_bytes()
            content_blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64.b64encode(img_bytes).decode(),
                },
            })
        # Final content block is the user text prompt.
        content_blocks.append({"type": "text", "text": prompt})

        start_ms = int(time.time() * 1000)

        # Only thread tools/tool_choice into the SDK call when the
        # caller actually provided them — passing ``tools=None``
        # explicitly would change the SDK's behavior.
        kwargs: dict = {
            "model": resolved_model,
            "max_tokens": resolved_max,
            "temperature": resolved_temp,
            "system": resolved_system,
            "messages": [
                {"role": "user", "content": content_blocks}
            ],
        }
        if tools is not None:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice

        response = client.messages.create(**kwargs)

        end_ms = int(time.time() * 1000)
        latency = end_ms - start_ms

        usage = TokenUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=resolved_model,
            cost_estimate=_calculate_cost(
                resolved_model,
                response.usage.input_tokens,
                response.usage.output_tokens,
            ),
            latency_ms=latency,
        )
        self.session.add_usage(usage)

        return response, usage

    def diagnose(
        self,
        make: str,
        model_name: str,
        year: int,
        symptoms: list[str],
        description: Optional[str] = None,
        mileage: Optional[int] = None,
        engine_type: Optional[str] = None,
        modifications: Optional[list[str]] = None,
        known_issues: Optional[list[dict]] = None,
        ai_model: Optional[str] = None,
        use_cache: bool = True,
        offline: bool = False,
    ) -> tuple[DiagnosticResponse, TokenUsage]:
        """Run a full diagnostic analysis on a vehicle with symptoms.

        This is the primary entry point for the diagnostic engine.
        It builds context from vehicle info, symptoms, and knowledge base results,
        sends it to Claude, and parses the structured response.

        Args:
            make: Vehicle manufacturer (e.g., "Honda").
            model_name: Vehicle model (e.g., "CBR600RR").
            year: Model year.
            symptoms: List of reported symptoms.
            description: Optional freeform description from the mechanic.
            mileage: Optional current mileage.
            engine_type: Optional engine description.
            modifications: Optional list of known modifications.
            known_issues: Optional list of relevant known issues from knowledge base.
            ai_model: Optional model override for this diagnosis.
            use_cache: When True (default), look up + store AI response in the
                cache. Set False to bypass the cache entirely (e.g., when
                running comparison experiments that need fresh live output).
            offline: When True, cache lookup is mandatory — a cache miss
                raises ``RuntimeError`` rather than calling the API. Use for
                on-the-road workflows where the mechanic has no internet
                but needs to re-render a previously-cached diagnosis.

        Returns:
            Tuple of (DiagnosticResponse, TokenUsage). On a cache hit,
            ``TokenUsage.input_tokens`` and ``output_tokens`` are 0 and
            ``cost_estimate`` is 0.0.

        Raises:
            RuntimeError: when ``offline=True`` and the cache has no entry
                for the current input fingerprint.
        """
        # --- Cache key construction (independent of the prompt string) ---
        # Only input data that affects the AI's answer is hashed, not the
        # assembled prompt text — so if the prompt template changes but the
        # semantic inputs don't, stale cache entries still serve. (Track R
        # phase 321+ can version-prefix the cache key if a prompt change
        # ever breaks response compatibility.)
        resolved_model = _resolve_model(ai_model) if ai_model else self.model
        cache_payload = {
            "make": make,
            "model_name": model_name,
            "year": year,
            "symptoms": list(symptoms or []),
            "description": description,
            "mileage": mileage,
            "engine_type": engine_type,
            "modifications": list(modifications) if modifications else [],
            "ai_model": resolved_model,
        }

        cache_key = None
        if use_cache:
            try:
                cache_key = _make_cache_key("diagnose", cache_payload)
                cached = get_cached_response(cache_key)
            except Exception as exc:
                # Cache is an optimization, not a dependency — log and
                # continue as if cache was unavailable.
                _log.warning("Cache lookup failed: %s", exc)
                cached = None

            if cached is not None:
                try:
                    diagnostic = DiagnosticResponse(**cached["response"])
                except Exception as exc:
                    _log.warning(
                        "Cached response could not be reconstructed "
                        "(%s) — refreshing from API.", exc,
                    )
                    diagnostic = None
                if diagnostic is not None:
                    # Zero-token usage reflects that nothing was billed.
                    cached_usage = TokenUsage(
                        input_tokens=0,
                        output_tokens=0,
                        model=cached.get("model_used") or resolved_model,
                        cost_estimate=0.0,
                        latency_ms=None,
                    )
                    # Track the cache hit on session metrics too so the
                    # session summary reflects the actual (free) call.
                    self.session.add_usage(cached_usage)
                    return diagnostic, cached_usage

        # Cache miss — honor offline flag before hitting the API.
        if offline:
            raise RuntimeError(
                "Offline mode: no cached response for this query. "
                "Either remove --offline or prime the cache with an "
                "online run."
            )

        # Build context blocks
        vehicle_ctx = build_vehicle_context(
            make=make,
            model=model_name,
            year=year,
            mileage=mileage,
            engine_type=engine_type,
            modifications=modifications,
        )
        symptom_ctx = build_symptom_context(symptoms, description)
        knowledge_ctx = build_knowledge_context(known_issues or [])

        # Assemble full prompt
        full_prompt = build_full_prompt(vehicle_ctx, symptom_ctx, knowledge_ctx)

        # Call the API
        response_text, usage = self.ask(
            prompt=full_prompt,
            model=ai_model,
        )

        # Parse structured response
        diagnostic = self._parse_diagnostic_response(response_text, make, model_name, year, symptoms)

        # Store in cache (best-effort — never break the live call).
        # `mode="json"` serializes enums to their string values so the
        # round-trip through `json.dumps` + `DiagnosticResponse(**data)`
        # reconstructs cleanly (a plain `str(DiagnosticSeverity.HIGH)`
        # can yield 'DiagnosticSeverity.HIGH' depending on Python version,
        # which Pydantic can't re-validate back into the enum).
        if use_cache and cache_key is not None:
            try:
                set_cached_response(
                    cache_key=cache_key,
                    kind="diagnose",
                    model_used=usage.model or resolved_model,
                    response_dict=diagnostic.model_dump(mode="json"),
                    tokens_input=usage.input_tokens,
                    tokens_output=usage.output_tokens,
                    cost_cents=cost_dollars_to_cents(usage.cost_estimate),
                )
            except Exception as exc:
                _log.warning("Cache store failed: %s", exc)

        return diagnostic, usage

    def _parse_diagnostic_response(
        self,
        response_text: str,
        make: str,
        model_name: str,
        year: int,
        symptoms: list[str],
    ) -> DiagnosticResponse:
        """Parse AI response text into a structured DiagnosticResponse.

        Attempts JSON parsing first, falls back to constructing a basic response
        from the raw text if JSON parsing fails.
        """
        # Try to extract JSON from response
        try:
            # Find JSON block in response (may be wrapped in markdown code fences)
            text = response_text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            data = json.loads(text)
            return DiagnosticResponse(**data)
        except (json.JSONDecodeError, KeyError, ValueError, IndexError):
            # Fallback: construct basic response from raw text
            return DiagnosticResponse(
                vehicle_summary=f"{year} {make} {model_name}",
                symptoms_acknowledged=symptoms,
                diagnoses=[
                    DiagnosisItem(
                        diagnosis=response_text[:500],
                        confidence=0.5,
                        severity=DiagnosticSeverity.MEDIUM,
                        evidence=["AI response could not be parsed as structured JSON"],
                        repair_steps=["Review raw AI response for diagnostic details"],
                    )
                ],
                notes="Response was not in structured JSON format — raw text preserved in first diagnosis.",
            )

    def get_session_summary(self) -> dict:
        """Return a summary of the current diagnostic session."""
        return {
            "session_id": self.session.session_id,
            "call_count": self.session.call_count,
            "total_tokens": self.session.total_tokens,
            "total_cost_usd": f"${self.session.total_cost:.4f}",
            "models_used": self.session.models_used,
            "avg_latency_ms": (
                f"{self.session.avg_latency_ms:.0f}" if self.session.avg_latency_ms else "N/A"
            ),
        }
