"""Diagnostic engine client — wraps Anthropic SDK for motorcycle diagnostics."""

import json
import os
import time
from typing import Optional
from datetime import datetime, timezone

from motodiag.core.config import get_settings
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

# Model pricing per million tokens (USD) as of 2026-04
MODEL_PRICING = {
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-sonnet-4-5-20241022": {"input": 3.00, "output": 15.00},
}

# Default model alias mapping
MODEL_ALIASES = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-5-20241022",
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

        Returns:
            Tuple of (DiagnosticResponse, TokenUsage).
        """
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
