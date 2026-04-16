# MotoDiag Phase 85 — Parts + Tools Recommendation

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build a parts and tools recommendation engine that takes a diagnosis plus vehicle make/model/year and returns structured part recommendations (with part numbers, brands, price ranges, OEM vs aftermarket guidance, and cross-references) alongside tool recommendations (with specifications, essentiality, and alternatives). Uses Claude via DiagnosticClient for intelligent recommendations grounded in real mechanic knowledge.

CLI: `python -m pytest tests/test_phase85_parts.py -v`

Outputs: `src/motodiag/engine/parts.py`, 35 tests

## Logic
1. PartSource enum defines four sourcing categories: OEM, aftermarket, used, generic
2. PartRecommendation Pydantic model captures: part_name, part_number (optional), brand, price_range_low/high, source, notes, cross_references list
3. ToolRecommendation Pydantic model captures: tool_name, specification, price_range string, essential bool, alternative (optional)
4. PARTS_PROMPT system prompt instructs Claude to return JSON with specific part numbers, trusted brand recommendations, price ranges, cross-references, and tool specifications
5. PartsRecommender.__init__ accepts a DiagnosticClient instance
6. recommend() builds a user prompt from diagnosis + vehicle info, calls client.ask() with PARTS_PROMPT as system, parses response
7. _parse_recommendations() extracts JSON (handling code fences), iterates parts/tools arrays, validates each with Pydantic, skips malformed items gracefully
8. Returns tuple of (list[PartRecommendation], list[ToolRecommendation], TokenUsage)

## Key Concepts
- PartSource enum: 4 values (oem, aftermarket, used, generic) as str enum for JSON compatibility
- PartRecommendation: Pydantic model with ge=0.0 validation on price fields, optional part_number and notes
- ToolRecommendation: essential flag distinguishes must-have from nice-to-have tools, alternative field for workarounds
- cross_references: list[str] enables mechanics to find equivalent parts across brands (e.g., NGK = Denso)
- PARTS_PROMPT: mentions 13+ trusted motorcycle parts brands (NGK, DID, EBC, All Balls, Rick's, etc.)
- Prompt requires JSON response format with specific schema for reliable parsing
- _parse_recommendations: per-item try/except allows partial success — good items survive even if others are malformed
- Code fence handling: strips ```json``` wrappers before parsing (same pattern as DiagnosticClient)
- Graceful fallback: returns empty lists on total parse failure rather than raising exceptions
- DiagnosticClient integration: uses ask() with system prompt override, inherits session tracking and cost monitoring

## Verification Checklist
- [x] PartSource enum has 4 values (oem, aftermarket, used, generic)
- [x] PartRecommendation creates with minimal fields (5 tests)
- [x] PartRecommendation with part_number, cross_references, notes
- [x] PartRecommendation rejects negative prices
- [x] ToolRecommendation: essential vs optional, with alternative, consumable, specification
- [x] PARTS_PROMPT mentions NGK, DID, EBC, All Balls, Rick's, OEM, aftermarket, part numbers, cross-references, JSON, price range (10 tests)
- [x] PartsRecommender.recommend() returns structured lists + TokenUsage
- [x] Correct prompt and system prompt passed to client.ask()
- [x] Bad JSON returns empty lists gracefully
- [x] Partial JSON: good items survive, bad items skipped
- [x] Code-fenced JSON parsed correctly
- [x] Empty parts/tools arrays handled
- [x] Cross-references preserved through parsing
- [x] All 35 tests pass

## Risks
- Claude may not always return valid JSON — mitigated by graceful fallback returning empty lists
- Part numbers may be hallucinated — noted in prompt as "where available", mechanic should verify
- Price ranges become stale over time — acceptable for estimates, not for quoting customers
- Prompt brand list needs periodic updates as aftermarket landscape evolves

## Deviations from Plan
None — built as specified.

## Results

| Metric | Value |
|--------|-------|
| Module | `src/motodiag/engine/parts.py` |
| Models | PartSource, PartRecommendation, ToolRecommendation |
| Classes | PartsRecommender |
| Tests | 35 (all mocked, zero API calls) |
| Lines of code | ~175 (parts.py) + ~290 (test) |
| Brands in prompt | 13+ (NGK, Denso, DID, RK, EK, EBC, All Balls, Rick's, Shindy, K&L, Motion Pro, Barnett, Vesrah, Cometic, Moose, Trail Tech) |

Parts recommendation engine provides structured, brand-aware suggestions with cross-references, enabling mechanics to quickly identify what they need and where to source it.
