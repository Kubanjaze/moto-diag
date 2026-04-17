# MotoDiag Phase 101 — Visual Symptom Analysis (Claude Vision)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build a VisualAnalyzer class that uses Claude Vision API (mocked in tests) to analyze motorcycle images/frames for visual diagnostic symptoms: smoke color/density, fluid leaks by color/location, physical damage, gauge readings, wear indicators (chain, tires, brake pads), and corrosion. Includes built-in smoke color and fluid color diagnostic guides for instant offline lookup without API calls.

CLI: `python -m pytest tests/test_phase101_vision.py -v`

Outputs: `src/motodiag/media/vision_analysis.py` (VisualAnalyzer + models + guides), 34 tests

## Logic
- FindingType enum: smoke, leak, damage, gauge_reading, wear, corrosion, missing_part, modification
- Severity enum: critical, high, medium, low, info
- VisualFinding model: finding_type, description, confidence (0.0-1.0), location_in_image, severity
- VisualAnalysisResult model: findings list, overall_assessment, suggested_diagnostics, image_quality_note. Computed properties: finding_count, critical_findings, high_severity_findings, average_confidence. Method: findings_by_type().
- SMOKE_COLOR_GUIDE: dict mapping white/blue/black/gray to cause, common_sources, severity, notes. White=coolant, blue=oil, black=rich fuel.
- FLUID_COLOR_GUIDE: dict mapping green/orange/red/dark_brown/light_brown/clear to fluid type, severity, action.
- VISION_ANALYSIS_PROMPT: motorcycle-specific system prompt guiding Claude Vision to inspect for 6 categories (smoke, leaks, damage, gauges, wear, corrosion).
- VehicleContext model: make, model, year, mileage, reported_symptoms. to_context_string() formats for prompt injection.
- VisualAnalyzer.analyze_image(): takes image_description + optional VehicleContext, builds prompt, calls client.ask() (mocked), parses JSON response into VisualAnalysisResult. Returns empty result for blank descriptions.
- VisualAnalyzer.analyze_smoke(): offline lookup in SMOKE_COLOR_GUIDE — no API call.
- VisualAnalyzer.analyze_fluid_leak(): offline lookup in FLUID_COLOR_GUIDE — no API call.
- Response parsing: strips markdown code fences, attempts JSON parse, falls back to raw text in overall_assessment.

## Key Concepts
- Claude Vision API integration pattern (simulated via mock client in tests)
- Motorcycle-specific vision prompt covering 6 diagnostic categories
- Offline diagnostic guides (SMOKE_COLOR_GUIDE, FLUID_COLOR_GUIDE) for instant results
- Pydantic models with computed properties and type-based filtering
- JSON response parsing with markdown fence stripping and fallback handling
- VehicleContext for prompt injection (enriches vision analysis with vehicle-specific info)

## Verification Checklist
- [x] VisualFinding: basic fields, defaults, all finding types (3 tests)
- [x] VisualAnalysisResult: empty, finding_count, critical filter, high severity filter, average confidence, findings_by_type (6 tests)
- [x] VehicleContext: full context, empty, partial (3 tests)
- [x] SMOKE_COLOR_GUIDE: white=coolant, blue=oil, black=rich, all have sources (4 tests)
- [x] FLUID_COLOR_GUIDE: green=coolant, red=transmission, all have actions (3 tests)
- [x] analyze_smoke: known color, case insensitive, unknown color (3 tests)
- [x] analyze_fluid_leak: known color, unknown color (2 tests)
- [x] analyze_image: JSON response parsed, empty description, unparseable response, system prompt passed, no vehicle context, whitespace description, markdown-wrapped JSON (7 tests)
- [x] VISION_ANALYSIS_PROMPT: mentions smoke, leak, gauge, wear (4 tests)

## Risks
- Image analysis is text-description-based (simulated) — real Claude Vision requires base64 image data or URL
- Smoke/fluid guides are static knowledge — edge cases (e.g., pink coolant, brown-tinted diesel) may not match
- Response parsing assumes JSON or plain text — complex mixed responses may lose structure

## Results
| Metric | Value |
|--------|-------|
| Files created | 1 (vision_analysis.py) |
| Tests | 34 (fully mocked, no API calls) |
| Models | 5 (FindingType, Severity, VisualFinding, VisualAnalysisResult, VehicleContext) |
| Diagnostic guides | 2 (SMOKE_COLOR_GUIDE: 4 colors, FLUID_COLOR_GUIDE: 6 colors) |
| Analyzer methods | 3 (analyze_image, analyze_smoke, analyze_fluid_leak) |
| External deps | 0 (uses DiagnosticClient but mocked in tests) |

Key finding: The dual-mode design (AI analysis for complex images + instant offline lookup for smoke/fluid colors) gives mechanics fast answers for common symptoms without burning API tokens, while still supporting full image analysis when needed.
