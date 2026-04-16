# MotoDiag Phase 79 — Claude API Integration + Base Client

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Build the foundational Claude API client for the diagnostic engine. This module wraps the Anthropic SDK with motorcycle-diagnostic-specific configuration: model selection (Haiku for speed/cost, Sonnet for complex reasoning), token tracking for cost monitoring, structured output parsing, .env auto-loading, and a clean interface that all downstream diagnostic phases will use.

CLI: `python -m pytest tests/test_phase79_engine_client.py -v`

Outputs: `src/motodiag/engine/client.py` (API client), `src/motodiag/engine/models.py` (response models), `src/motodiag/engine/prompts.py` (system prompt templates), 32 tests

## Logic
1. `client.py` — `DiagnosticClient` class wrapping `anthropic.Anthropic`:
   - API key resolution: explicit > env var `ANTHROPIC_API_KEY` > settings `MOTODIAG_ANTHROPIC_API_KEY`
   - Model selection via alias ("haiku", "sonnet") or full model ID, resolved at call time
   - `diagnose()` method: takes vehicle context + symptoms + knowledge base → returns `DiagnosticResponse` + `TokenUsage`
   - `ask()` method: raw prompt with system context → response text + usage (low-level, used by all higher methods)
   - Token tracking: per-call `TokenUsage` and cumulative `SessionMetrics` with running averages
   - Cost calculation: model-specific pricing (Haiku $0.80/$4.00, Sonnet $3.00/$15.00 per MTok)
   - JSON response parsing with graceful fallback for non-JSON AI responses
   - Lazy Anthropic client initialization (doesn't import SDK until first call)

2. `models.py` — Pydantic response models:
   - `DiagnosisItem`: diagnosis, confidence (0.0-1.0), severity, evidence, repair_steps, cost, parts, safety_warning
   - `DiagnosticResponse`: vehicle_summary, symptoms_acknowledged, ranked diagnoses, additional_tests, notes
   - `TokenUsage`: per-call input/output tokens, model, cost_estimate, latency_ms
   - `SessionMetrics`: cumulative tracking with `add_usage()` method, running average latency

3. `prompts.py` — System prompt templates:
   - `DIAGNOSTIC_SYSTEM_PROMPT`: motorcycle diagnostic expert identity, 7-point approach, structured JSON output requirement
   - `build_vehicle_context()`: make/model/year/mileage/engine/modifications → formatted string
   - `build_symptom_context()`: symptoms list + optional freeform description → formatted string
   - `build_knowledge_context()`: known issues from Track B → truncated context for RAG-style injection
   - `build_full_prompt()`: assembles vehicle + symptom + knowledge contexts + response format instruction

## Key Concepts
- Anthropic SDK `messages.create()` with system prompt as separate parameter
- Model alias resolution: "haiku" → "claude-haiku-4-5-20251001", "sonnet" → "claude-sonnet-4-5-20241022"
- Pydantic v2 models with Field descriptions for self-documenting schema
- Token counting via `response.usage.input_tokens` / `response.usage.output_tokens`
- Cost tracking per model tier with `MODEL_PRICING` dict
- Knowledge base context injection: Track B known issues formatted into user prompt for RAG-style grounding
- Temperature 0.3 for diagnostic consistency (low creativity, high accuracy)
- Graceful JSON parse fallback: if AI doesn't return valid JSON, construct a basic DiagnosticResponse from raw text
- Mock-friendly design: `_get_client()` lazy init enables complete test isolation without live API
- `SessionMetrics.add_usage()` maintains running averages across multiple diagnostic calls

## Verification Checklist
- [x] `DiagnosticClient` initializes with API key from env (4 init tests pass)
- [x] Model selection works — haiku default, sonnet override, full ID passthrough (4 resolution tests)
- [x] Token tracking counts correctly — per-call and cumulative session (2 metrics tests)
- [x] Cost calculation matches model pricing — Haiku vs Sonnet, zero tokens, fallback (4 cost tests)
- [x] Response models validate correctly — all Pydantic models (5 model tests)
- [x] System prompts build with vehicle/symptom/knowledge context (8 prompt builder tests)
- [x] Knowledge context injection verified in mocked diagnose call
- [x] JSON parse fallback works for non-structured AI responses
- [x] All 32 tests pass without hitting the live API (fully mocked, 0.09s)

## Risks
- API key not configured — handled with clear RuntimeError message listing both env var options
- SDK version: anthropic 0.96.0 installed and verified, response object structure confirmed
- Token counting accuracy: depends on SDK response.usage object — verified in mocked tests
- JSON parsing: AI may not always return valid JSON — fallback handler preserves raw text in response
- Cost pricing: hardcoded MODEL_PRICING dict needs updating when Anthropic changes prices

## Results
| Metric | Value |
|--------|-------|
| Files created | 3 (client.py, models.py, prompts.py) + __init__.py updated |
| Tests | 32/32, 0.09s |
| Test coverage | Model resolution (4), cost calc (4), response models (5), prompts (8), client init (5), mocked API (5), session tracking (1) |
| API calls | 0 (fully mocked) |
| Anthropic SDK | 0.96.0 |

Key finding: The engine module provides a clean interface for all downstream phases. The `diagnose()` method bridges Track B (knowledge base) to Track C (AI reasoning) via the knowledge context injection in prompts.py. All 16 remaining Track C phases will build on this foundation.
