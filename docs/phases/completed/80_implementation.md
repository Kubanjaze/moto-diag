# MotoDiag Phase 80 — Symptom Analysis Prompt Engineering

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Build the symptom analysis subsystem within the diagnostic engine. This adds structured symptom intake (categorization, severity assessment, onset pattern), a specialized prompt template that guides Claude through differential diagnosis reasoning, and a `SymptomAnalyzer` class that combines symptom context with knowledge base lookups to produce ranked diagnoses. The key innovation is a two-pass approach: first query the knowledge base for relevant known issues, then feed those issues as context to Claude for AI-enhanced reasoning.

CLI: `python -m pytest tests/test_phase80_symptom_analysis.py -v`

Outputs: `src/motodiag/engine/symptoms.py` (SymptomAnalyzer + helpers), updated prompts, 28 tests

## Logic
1. `symptoms.py` — `SymptomAnalyzer` class + helper functions:
   - `categorize_symptoms()`: classifies symptoms into 6 system categories (electrical, fuel, mechanical, cooling, drivetrain, braking) with "other" bucket for unrecognized symptoms
   - `assess_urgency()`: checks symptom combinations against 5 predefined critical/warning patterns — overheating+power loss, fuel smell+no start, brake failure, engine damage, starter damage
   - `build_differential_prompt()`: assembles vehicle context + categorized symptoms + urgency alerts + knowledge context into a comprehensive diagnostic prompt
   - `SymptomAnalyzer.analyze()`: two-pass method that categorizes symptoms, assesses urgency, builds differential prompt, calls Claude with symptom-specific system prompt, parses response, and returns metadata

2. `SYMPTOM_ANALYSIS_PROMPT`: 5-step structured diagnostic prompt:
   - Step 1: Symptom acknowledgement with system categories
   - Step 2: Onset pattern inference (sudden/gradual, constant/intermittent, condition-specific)
   - Step 3: Knowledge base correlation (rank KB matches by relevance)
   - Step 4: Differential diagnosis (ranked by probability with confidence %, evidence, "test to confirm")
   - Step 5: Safety check (flag critical conditions prominently)

## Key Concepts
- Symptom categorization: 6 system buckets with 40+ symptom patterns, substring matching for flexibility
- Safety-critical detection: 5 predefined dangerous combinations (e.g., overheating+steam = possible head gasket)
- Two-pass diagnosis: knowledge base first, then AI reasoning grounded by KB context
- Differential diagnosis ranking: confidence percentages + "test to confirm" for each diagnosis
- Onset pattern analysis: structured in the prompt template for Claude to infer from context
- Metadata return: analyzer returns categorized symptoms, urgency alerts, and KB match count alongside the diagnosis
- All API calls go through DiagnosticClient.ask() — inherits token tracking and session metrics

## Verification Checklist
- [x] Symptom categorization classifies electrical, fuel, mechanical, cooling, drivetrain, braking (8 tests)
- [x] Urgency assessment flags critical combinations: overheating+power loss, fuel+no start, brakes (6 tests)
- [x] Differential prompt includes vehicle context, categories, alerts, KB matches (5 tests)
- [x] SymptomAnalyzer returns response, usage, and metadata with mocked API (4 tests)
- [x] Knowledge base context is passed through to the API call prompt (verified via mock call_args)
- [x] Symptom-specific system prompt used (verified via mock call_args)
- [x] Prompt template has all 5 structured steps (5 template tests)
- [x] All 28 tests pass without live API (fully mocked, 0.08s)

## Results
| Metric | Value |
|--------|-------|
| Files created | 1 (symptoms.py) |
| Tests | 28/28, 0.08s |
| Test coverage | Categorization (8), urgency (6), prompt building (5), mocked analyzer (4), prompt template (5) |
| API calls | 0 (fully mocked) |
| Symptom patterns | 40+ across 6 categories |
| Critical combinations | 5 safety-critical patterns |

Key finding: The two-pass approach (KB lookup → AI reasoning with KB context) is the bridge between Track B's knowledge base and Track C's AI engine. The `SymptomAnalyzer` is the first consumer of this pattern — all downstream diagnostic phases (81-94) will follow the same architecture of querying existing data, building focused context, and letting Claude reason over structured inputs.
