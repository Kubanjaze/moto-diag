# MotoDiag Phase 81 — Fault Code Interpretation Prompts

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Build the fault code interpretation subsystem. Takes a DTC code + vehicle context, classifies the code format (OBD-II P-codes, Kawasaki dealer mode, Suzuki C-codes, Honda blink codes, Harley/Yamaha), correlates with local code databases, and produces AI-enhanced root cause analysis with "check before replacing" diagnostic steps.

CLI: `python -m pytest tests/test_phase81_fault_codes.py -v`

Outputs: `src/motodiag/engine/fault_codes.py` (FaultCodeInterpreter + classify_code + code databases), 36 tests

## Logic
1. `fault_codes.py` — `FaultCodeInterpreter` class + code classification:
   - `classify_code()`: regex-based classifier for 8 DTC formats — OBD-II generic (P0xxx/P2xxx), OBD-II manufacturer (P1xxx), Kawasaki 2-digit dealer mode, Suzuki C-mode (C00-C49), Honda blink codes (1-9), Harley B/U codes, Yamaha diagnostics, unknown
   - `FaultCodeResult` Pydantic model: code, format, description, system, possible_causes, tests_to_confirm, related_symptoms, repair_steps, cost, safety_critical flag
   - `FaultCodeInterpreter.interpret()`: two-pass — classify code + local lookup → Claude analysis with DTC-specific prompt
   - `FaultCodeInterpreter.quick_lookup()`: fast local-only lookup without AI (code format + description)
   - `DTC_INTERPRETATION_PROMPT`: 5-step structured prompt emphasizing "code is a SYMPTOM, not the diagnosis"

2. Local code databases (dictionaries):
   - `KAWASAKI_CODE_MAP`: 24 codes covering ECU, ISC, TPS, IAP, ECT, O2, speed, gear, shift, bank angle, battery, FI relay, fuel pump, SET, PAIR, KTRC, KIBS, IMU, cruise, KIPASS
   - `SUZUKI_CODE_MAP`: 20 codes covering C00-C49 (TPS, IAP, ECT, MAP, speed, fuel pump, STPS, gear, exhaust valve, camshaft, wheel speed sensors)
   - `OBD2_SYSTEM_MAP`: 7 system categories (fuel, ignition, emissions, speed/idle, computer, transmission)

## Key Concepts
- Make-specific DTC format classification via regex patterns — 8 distinct formats recognized
- Root cause vs symptom distinction: the DTC is never the diagnosis, always a symptom
- "Check before replacing" philosophy embedded in the prompt template — test the circuit first
- Local code databases provide instant lookup without AI for common codes
- Two-pass approach: local classification/lookup → AI root cause analysis with vehicle context
- FaultCodeResult includes safety_critical flag for brake/ABS/fuel codes
- quick_lookup() enables instant UI display while AI analysis runs in background
- Graceful JSON parse fallback preserves raw AI text when structured parsing fails

## Verification Checklist
- [x] Code classification handles all 8 formats: OBD-II generic, manufacturer, Kawasaki, Suzuki, Honda blink, Harley B/U, Yamaha, unknown (17 tests)
- [x] FaultCodeResult model creates and validates correctly (3 tests)
- [x] Code databases have adequate coverage: Kawasaki 24+, Suzuki 20+, OBD-II 7 systems (3 tests)
- [x] DTC prompt has 5 structured steps and emphasizes testing first (3 tests)
- [x] FaultCodeInterpreter returns structured results with mocked API (7 tests)
- [x] Quick lookup works without AI call (3 tests)
- [x] All 36 tests pass without live API (fully mocked, 0.13s)

## Results
| Metric | Value |
|--------|-------|
| Files created | 1 (fault_codes.py) |
| Tests | 36/36, 0.13s |
| Test coverage | Classification (17), model (3), databases (3), prompt (3), mocked interpreter (7), quick lookup (3) |
| API calls | 0 (fully mocked) |
| Code formats recognized | 8 (OBD-II generic/mfr, Kawasaki, Suzuki, Honda, Harley, Yamaha, unknown) |
| Local code entries | 51 (Kawasaki 24 + Suzuki 20 + OBD-II 7 systems) |

Key finding: The fault code interpreter is the second major consumer of the two-pass architecture (after SymptomAnalyzer). The quick_lookup() method provides a fast local path for UI display, while the full interpret() method adds AI reasoning. The 51 locally-stored code descriptions cover the most common DTCs across Japanese and Harley motorcycles, and the AI fills in for any code not in the local database.
