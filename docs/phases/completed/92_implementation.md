# MotoDiag Phase 92 — Wiring Diagram Reference

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Provide structured wiring reference data for common motorcycle circuits across all makes. Not actual wiring diagrams (copyrighted) but the diagnostic information mechanics need: wire colors, connector locations, expected voltage/resistance values, test points, common failures, and diagnostic tips. Enables both direct lookup and AI prompt injection for circuit-specific diagnosis.

CLI: `python -m pytest tests/test_phase92_wiring.py -v`

Outputs: `src/motodiag/engine/wiring.py` (5 circuit references + lookup functions), 29 tests

## Key Concepts
- CircuitReference model: circuit name, system, description, applicable makes, wires, test points, failures, tips
- WireReference model: color, function, connector location, expected voltage, expected resistance
- 5 predefined circuit references: charging (stator→battery), starting (battery→motor), fuel injection (pump+injectors), ignition (CDI→coils→plugs), ABS (wheel speed sensors)
- Each circuit covers all 5 makes (Honda, Yamaha, Kawasaki, Suzuki, Harley) with make-specific notes in tips
- Lookup functions: get_circuit_reference() (name match), get_circuits_by_system(), list_all_circuits()
- build_wiring_context(): formats circuit into structured text for AI prompt injection
- Wire color conventions documented (yellow=stator, red=power, green/black=ground)
- Test points include specific voltage/resistance values and what abnormal readings mean
- Common failures list acts as a quick-reference for likely fault locations per circuit
- Diagnostic tips are mechanic-level practical advice (e.g., "tap the relay while pressing start")

## Verification Checklist
- [x] 5 circuit references with complete data (29 tests)
- [x] All circuits cover 3+ makes with real wire colors and test values
- [x] Lookup functions work with partial name matching and case insensitivity
- [x] Context builder produces structured text suitable for AI prompt injection
- [x] All 29 tests pass (0.30s)

## Results
| Metric | Value |
|--------|-------|
| Files created | 1 (wiring.py) |
| Tests | 29/29, 0.30s |
| Circuit references | 5 (charging, starting, FI, ignition, ABS) |
| Total wire entries | 14 across 5 circuits |
| Total test points | 20+ across 5 circuits |
