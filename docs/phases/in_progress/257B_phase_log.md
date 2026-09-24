# Phase 257B — The per-vehicle transmission field — phase log

**Status:** 🚧 In progress
**Opened:** 2026-09-24

---

### 2026-09-24 — Opened under the amended authority contract

First phase under the 2026-09-24 `ROADMAP_AUTHORITY.md` amendment: the
backend range is open-ended (205+), matched in both repos — moto-diag
`76edc69`, mobile `10a660f`. The contract asks for an amendment to be
recorded in both repos' phase logs; no phase was open when it was made, so
it is cited here, as the next phase's log. 257B is backend-owned (not in
185–204); its mobile commits are contributions to a backend phase.

Read before acting: ROADMAP (257 row and neighbours), the authority
contract, handoff `2026-09-23_257_after_yamaha.md`, FOLLOWUPS (F121, F143),
`257_implementation.md` v1.2. ROADMAP row added as 🚧 before Step 0:
`2c30ecd`, pushed. Gates before that commit: 191C F9 lint, 244G, finding
contract, roadmap continuity — 60 passed; `finding_check.py` exit 0.

### 2026-09-24 — Step 0: extension, no fork

The column exists (migration 063), live DB is schema 66 with 10 vehicles
and 0 transmissions, and the resolver's `explicit` rung exists. What is
missing is every writer (registry inserts, update whitelist, API schemas,
PATCH clear) and one reader: **`/ask` passes `getattr(context,
"transmission", None)` on a `VehicleContext` with no such field**, so the
API's only retrieval door never saw a vehicle's own value. Measurements
S0-1..S0-11 in the implementation doc.

**Decision (logged, not asked):** no fork by the operator's own criteria —
the field's home is settled, and the backend change is smaller than a
column. Straight on to v1.0.

**Decision:** `powertrain` stays unwired in `/ask` (D5). Wiring it would
change the answer for an unset electric vehicle, which item 2 of the
finish line forbids. To be filed.

### 2026-09-24 — v1.0 committed before any code

`f4889a9`, pushed on `phase-257B-transmission-field`. F144 allocated with
`next_f_number.sh` (both files: moto-diag F143, mobile F115) and filed
before the code comment that cites it.

### 2026-09-24 — Backend build: the API writes it, `/ask` reads it

`70c3f23`. Registry inserts and the update whitelist; `TransmissionLiteral`
on create, update and response; PATCH honours an explicit `null` for
transmission only; `VehicleContext.transmission` filled from the live row
and passed by `/ask`. `tests/test_phase257B_transmission_field.py`, 24
tests, including the E2E (set → `/ask` explicit → clear → `/ask`
model-sourced) and the CLI diagnose wiring test.

**Decision:** dropped the enum-to-value conversion I had added to
`update_vehicle` for `transmission`. Measured: sqlite binds the `str` enum
member as `'cvt'` unaided, so the line did nothing and no mutation of it
could go red (S9). The existing four conversions are untouched.

**Break-it:** 10 mutations, one per new line of code, each against the 257B
file with `-B` and `__pycache__` cleared: **10/10 killed**.

**Related suites + gates** (26 files: everything touching the vehicle API,
`VehicleContext`, `_build_vehicle_context`, `update_vehicle`,
`rows_for_machine`, plus 255*, 256*, 191C, 244G, roadmap continuity):
1 failed, 1032 passed → bug fix #1.

## Bug-fix register

### Bug fix #1 — 2026-09-24

- **Issue:** `test_phase244B_guidance::…live_vehicle_row_wins_over_a_stale_session_snapshot`
  failed: make stayed `'Homda'`.
- **Root cause:** `70c3f23` widened `_build_vehicle_context`'s live-row
  SELECT to include `transmission`. On a `vehicles` table without the
  column the SELECT raised, and its except clause dropped make, model and
  mileage with it: a best-effort read turned all-or-nothing.
- **Fix:** the original SELECT restored verbatim; `transmission` read by a
  separate best-effort query.
- **Files:** `src/motodiag/media/analysis_worker.py`,
  `tests/test_phase257B_transmission_field.py`.
- **Verified:** new guard red without the fix, green with it; mutations
  10/10; related suites + gates **1034 passed**; 244G tree 0 hits;
  `finding_check` exit 0.
- **Commit:** `8e039e7`
