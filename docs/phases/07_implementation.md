# MotoDiag Phase 07 — Diagnostic Session Model

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-15

## Goal
Build the diagnostic session lifecycle — the core workflow that ties a vehicle, symptoms, fault codes, and diagnosis together. A session tracks the entire troubleshooting journey from "bike won't start" to "replaced stator, problem solved." This is the backbone that the AI engine, CLI, and shop management all build on.

CLI: No new CLI command yet — sessions are created/managed programmatically.

Outputs: `core/session_repo.py` (9 functions — full lifecycle CRUD), 16 tests

## Logic
1. Created `core/session_repo.py` with 9 functions + 1 helper:
   - `create_session(vehicle_make, model, year, symptoms?, fault_codes?, vehicle_id?)` → session ID
   - `get_session(session_id)` → full session dict with parsed JSON arrays
   - `update_session(session_id, updates)` → whitelisted field updates
   - `add_symptom_to_session(session_id, symptom)` → append without duplicates
   - `add_fault_code_to_session(session_id, code)` → append without duplicates
   - `set_diagnosis(session_id, diagnosis, confidence?, severity?, repair_steps?)` → sets diagnosis + status to "diagnosed"
   - `close_session(session_id)` → sets status to "closed" + closed_at timestamp
   - `list_sessions(status?, vehicle_make?, vehicle_model?)` → filtered list, newest first
   - `count_sessions(status?)` → count by optional status filter
   - `_row_to_dict(row)` → parses JSON for symptoms, fault_codes, repair_steps
2. Session lifecycle: OPEN → IN_PROGRESS → DIAGNOSED → RESOLVED → CLOSED
3. Symptom/fault code accumulation: read-modify-write with duplicate prevention
4. Diagnosis includes confidence (0-1 float), severity enum, and repair step list
5. Timestamps: created_at on create, updated_at on any change, closed_at on close

## Key Concepts
- Session is the canonical diagnostic workflow unit — everything traces to a session ID
- Status transitions via specific functions: `set_diagnosis()` → "diagnosed", `close_session()` → "closed"
- JSON arrays stored as TEXT, parsed on read — symptoms, fault_codes, repair_steps
- Accumulation pattern: `add_symptom_to_session()` reads current list, appends if not duplicate, writes back
- Whitelisted update fields prevent arbitrary column modification
- `ORDER BY created_at DESC` — most recent sessions first in listings

## Verification Checklist
- [x] `create_session()` returns auto-increment session ID
- [x] Initial status is "open"
- [x] Symptoms and fault codes stored as JSON arrays from creation
- [x] `add_symptom_to_session()` appends without overwriting existing
- [x] Duplicate symptoms ignored (not added twice)
- [x] `add_fault_code_to_session()` appends correctly
- [x] `set_diagnosis()` updates diagnosis, confidence, severity, repair_steps, and status
- [x] `close_session()` sets closed_at timestamp
- [x] `list_sessions(status="open")` filters correctly
- [x] `list_sessions(vehicle_make="Harley")` uses LIKE matching
- [x] `count_sessions()` with and without status filter
- [x] Non-existent session returns None
- [x] Invalid update fields rejected
- [x] 16 tests pass in 0.97s

## Risks
- ~~Concurrent session updates~~ — SQLite WAL mode handles at our scale (single-user CLI tool)
- ~~JSON array read-modify-write race~~ — not a concern for session-frequency operations

## Results
| Metric | Value |
|--------|-------|
| Functions | 9 (create, get, update, add_symptom, add_fault_code, set_diagnosis, close, list, count) |
| Status states | 5 (open, in_progress, diagnosed, resolved, closed) |
| Tests | 16 |
| Test time | 0.97s |

Diagnostic session lifecycle is complete. Every troubleshooting journey — from initial complaint through diagnosis to resolution — is now tracked, searchable, and persistent.
