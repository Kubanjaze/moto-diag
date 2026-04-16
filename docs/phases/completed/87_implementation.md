# MotoDiag Phase 87 — Safety Warnings + Critical Alerts

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build a rule-based safety checker that scans diagnosis text, symptom lists, and repair procedures against predefined safety rules to flag hazardous conditions (brake failure, fuel leaks, fire risk, electrical shorts, crush hazards). Pure logic module — no API calls needed. All alerts are deterministic and instantly available to downstream modules (AI engine, CLI display, repair plan builder).

CLI: `python -m pytest tests/test_phase87_safety.py -v`

Outputs: `src/motodiag/engine/safety.py`, `tests/test_phase87_safety.py` (37 tests)

## Logic
- Define AlertLevel enum: CRITICAL > WARNING > CAUTION > INFO with sort ordering
- Define SafetyAlert Pydantic model with level, title, message, affected_system, immediate_action, optional do_not
- Define SAFETY_RULES: 18 rules with regex patterns covering brakes, fuel, stator fire, stuck throttle, head gasket, overheating, electrical shorts, steering, wheel bearings, chain, tires, oil leak, coolant leak, exhaust leak, valve clearance, air filter, spark plugs, brake fluid
- Define REPAIR_SAFETY_KEYWORDS: 12 keyword-to-alert mappings for repair steps (drain fuel, remove fuel tank, brake fluid, brake caliper, jack, lift, battery, coolant drain, exhaust, chain adjust, spring compress, electrical wiring)
- SafetyChecker class: compile regex patterns once in __init__, then match against text in O(rules * text) time
- check_diagnosis(): scan free-text diagnosis against all compiled rules, deduplicate by title
- check_symptoms(): join symptom list into single string, delegate to check_diagnosis()
- check_repair_procedure(): scan each step against REPAIR_SAFETY_KEYWORDS dict, deduplicate by title
- format_alerts(): sort by AlertLevel priority (CRITICAL first), format with severity icons and DO NOT warnings

## Key Concepts
- AlertLevel enum (str, Enum): 4 levels with explicit sort ordering via _ALERT_ORDER dict
- SafetyAlert Pydantic model: structured output with optional do_not field for negative safety instructions
- SAFETY_RULES: list of dicts with regex pattern lists — multiple patterns per rule for variant matching
- REPAIR_SAFETY_KEYWORDS: dict mapping plain-text keywords to safety alert definitions
- Regex compilation: patterns compiled once in SafetyChecker.__init__() for performance
- Case-insensitive matching: re.IGNORECASE on all patterns
- Deduplication: seen_titles set prevents duplicate alerts when text matches multiple patterns for same rule
- check_symptoms() delegates to check_diagnosis() by joining symptom list with separator
- format_alerts() sorts by _ALERT_ORDER before rendering — CRITICAL always appears first
- No API dependency: entire module is pure Python + Pydantic, zero external calls

## Verification Checklist
- [x] AlertLevel enum has 4 values: critical, warning, caution, info (5 tests)
- [x] SafetyAlert model creates with all fields, do_not is optional (3 tests)
- [x] check_diagnosis(): brake failure/leak = CRITICAL (2 tests)
- [x] check_diagnosis(): fuel leak = CRITICAL (1 test)
- [x] check_diagnosis(): stator connector melting = CRITICAL (1 test)
- [x] check_diagnosis(): head gasket = WARNING (1 test)
- [x] check_diagnosis(): overheating + steam = WARNING (1 test)
- [x] check_diagnosis(): electrical short = WARNING (1 test)
- [x] check_diagnosis(): chain worn = CAUTION (1 test)
- [x] check_diagnosis(): tire worn = CAUTION (1 test)
- [x] check_diagnosis(): oil leak = CAUTION (1 test)
- [x] check_diagnosis(): valve clearance = INFO (1 test)
- [x] check_diagnosis(): unrelated text = no alerts (1 test)
- [x] check_diagnosis(): case insensitive (1 test)
- [x] check_diagnosis(): no duplicates from repeated keywords (1 test)
- [x] check_symptoms(): overheating + steam = WARNING (1 test)
- [x] check_symptoms(): fuel smell = CRITICAL (1 test)
- [x] check_symptoms(): normal symptoms = no critical/warning (1 test)
- [x] check_symptoms(): empty list = no alerts (1 test)
- [x] check_repair_procedure(): drain fuel = fire caution (1 test)
- [x] check_repair_procedure(): brake fluid = paint caution (1 test)
- [x] check_repair_procedure(): jack = crush warning (1 test)
- [x] check_repair_procedure(): lift = warning (1 test)
- [x] check_repair_procedure(): normal step = no alert (1 test)
- [x] check_repair_procedure(): multiple hazards detected (1 test)
- [x] format_alerts(): empty list = empty string (1 test)
- [x] format_alerts(): CRITICAL appears before INFO (1 test)
- [x] format_alerts(): correct ordering all 4 levels (1 test)
- [x] format_alerts(): DO NOT field included when present (1 test)
- [x] format_alerts(): header present (1 test)
- [x] SAFETY_RULES: at least 10 rules defined (1 test)
- [x] REPAIR_SAFETY_KEYWORDS: at least 10 keywords defined (1 test)
- [x] All levels represented in rules (1 test)
- [x] Every rule has required fields (1 test)
- [x] Every repair keyword has required fields (1 test)
- [x] All 37 tests pass

## Risks
- **Pattern coverage**: Regex patterns may miss unusual phrasings — mitigated by providing multiple pattern variants per rule and case-insensitive matching. Additional patterns can be added without changing the architecture.
- **False positives**: Common words like "battery" in repair steps trigger alerts even for benign operations — acceptable trade-off since safety warnings should err on the side of caution.
- **No NLP**: Pure regex means no semantic understanding — "the brakes are fine, no failure" would still match "brake" + "failure". Future phases could add negation detection if needed.

## Deviations from Plan
- Added stuck throttle and strong fuel odor as additional CRITICAL rules beyond the original spec (5 CRITICAL vs 3 planned)
- Added steering, wheel bearing as WARNING rules for completeness
- Added coolant leak and exhaust leak as CAUTION rules
- Added spring compress, electrical wiring, chain adjust, coolant drain, exhaust, remove fuel tank to REPAIR_SAFETY_KEYWORDS (12 total vs implied ~6)
- Total: 18 SAFETY_RULES and 12 REPAIR_SAFETY_KEYWORDS — more comprehensive than the minimum spec

## Results
| Metric | Value |
|--------|-------|
| SAFETY_RULES count | 18 |
| REPAIR_SAFETY_KEYWORDS count | 12 |
| CRITICAL rules | 5 |
| WARNING rules | 5 |
| CAUTION rules | 5 |
| INFO rules | 3 |
| Tests written | 37 |
| Tests passing | 37 |
| API calls | 0 |
| Module size | ~330 lines |

Pure logic safety module with zero API dependency. The rule set covers the most dangerous motorcycle failure modes a mechanic would encounter — brake failure, fuel leaks, fire risk from stator connectors, stuck throttles, and head gasket blowouts get CRITICAL or WARNING level. Repair procedure scanning catches common shop hazards: fuel handling, lifting, brake work, battery service, compressed springs, and hot exhaust.
