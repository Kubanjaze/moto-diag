# MotoDiag Phase 84 — Repair Procedure Generator

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Build a repair procedure generator that takes a diagnosis and vehicle context, sends it to Claude via the existing DiagnosticClient, and returns a structured RepairProcedure with numbered mechanic-friendly steps, tools, parts, time estimates, skill level, and safety warnings. This bridges the diagnostic engine output to actionable repair instructions.

CLI: `python -m pytest tests/test_phase84_repair.py -v`

Outputs: `src/motodiag/engine/repair.py`, `tests/test_phase84_repair.py`, 41 tests

## Logic
- RepairStep Pydantic model holds a single numbered instruction with optional tip and warning
- RepairProcedure model aggregates steps with tools_needed, parts_needed, estimated_hours, skill_level (enum), safety_warnings, and optional notes
- SkillLevel enum: BEGINNER, INTERMEDIATE, ADVANCED
- assess_skill_level() standalone function: keyword-based classification — checks advanced keywords first (engine rebuild, transmission, crankshaft), then intermediate (electrical, stator, fork seal, valve adjustment), then beginner (oil change, spark plug, chain lube). Defaults to intermediate if no match.
- RepairProcedureGenerator class: takes a DiagnosticClient, exposes generate() method
- generate() builds a user prompt with vehicle context (year/make/model + diagnosis), calls client.ask() with REPAIR_PROMPT as system prompt, parses JSON response into RepairProcedure
- JSON parsing: strips markdown code fences, falls back to a minimal single-step procedure if parsing fails (preserves raw text in step 1 instruction)
- REPAIR_PROMPT: system prompt requiring torque specs, safety warnings for fuel/brake/electrical/lifting, specific tool names, part quantities, honest time estimates, skill level, and DIY vs shop alternative approaches

## Key Concepts
- RepairStep model: step_number (ge=1), instruction, optional tip, optional warning
- RepairProcedure model: title, description, steps[], tools_needed[], parts_needed[], estimated_hours, skill_level (enum), safety_warnings[], optional notes
- SkillLevel enum with string values for JSON serialization ("beginner"/"intermediate"/"advanced")
- Keyword-based skill assessment with priority ordering (advanced > intermediate > beginner)
- REPAIR_PROMPT emphasizes torque specs, safety warnings (fuel/brake/electrical/lifting), specific tooling, OEM vs aftermarket parts
- JSON parsing with markdown code fence stripping (same pattern as DiagnosticClient._parse_diagnostic_response)
- Graceful fallback: bad JSON produces minimal procedure with raw text preserved and warning notes
- Uses existing DiagnosticClient.ask() for API calls — no new API surface
- assess_skill_level() is standalone (usable without API) for fallback and offline classification
- All tests fully mocked via MagicMock — zero API calls

## Verification Checklist
- [x] RepairStep creation: basic, with tip, with warning, with both, step_number validation (5 tests)
- [x] RepairProcedure creation: minimal, full, advanced skill, beginner skill (4 tests)
- [x] SkillLevel enum: values, string construction (2 tests)
- [x] assess_skill_level: beginner (4), intermediate (5), advanced (5), default, case insensitive (16 tests)
- [x] REPAIR_PROMPT validation: not empty, torque, safety, JSON, skill levels, fuel, brake, electrical, alternatives (9 tests)
- [x] RepairProcedureGenerator mocked: structured response, code fence, bad JSON fallback, prompt validation, empty response (5 tests)
- [x] All 41 tests pass
- [x] Zero API calls in test suite

## Risks
- Keyword-based skill assessment is a heuristic — edge cases may misclassify (mitigated: defaults to intermediate, which is the safest middle ground)
- Claude may not always return valid JSON — mitigated by fallback that preserves raw text
- REPAIR_PROMPT is long — token cost per call is higher than diagnostic prompt (acceptable: repair procedures are less frequent than diagnoses)

## Deviations from Plan
None — built as specified.

## Results
| Metric | Value |
|--------|-------|
| Files created | 2 (repair.py, test_phase84_repair.py) |
| Tests | 41 (5 step + 4 procedure + 2 enum + 16 skill + 9 prompt + 5 generator) |
| Skill keywords | 15 advanced, 14 intermediate, 15 beginner |
| API calls | 0 (all mocked) |

Repair procedure generator provides the bridge from diagnostic output to actionable mechanic instructions, with safety-first design and graceful degradation when AI responses are malformed.
