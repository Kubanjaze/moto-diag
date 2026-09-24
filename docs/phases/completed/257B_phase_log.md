# Phase 257B — The per-vehicle transmission field — phase log

**Status:** ✅ Complete (2026-09-24)
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

### 2026-09-24 — Mobile build: the vehicle screen

Mobile branch `phase-257B-transmission-field`, `0e1ed53`, pushed. Backend
served on **127.0.0.1:8757** only, against a scratchpad copy of the live
DB, to refresh `api-schema/openapi.json`; the schema diff is the
transmission field and nothing else. `TransmissionLiteral` is derived from
the generated type. `VehicleDetailScreen` shows the value (or "Not sure")
and edits it with the six values plus "Not sure", which sends an explicit
`null`. Tests: `VehicleDetail.transmission.test.tsx` (7, the real screen
with `api` mocked at the network boundary), `vehicleEnums.test.ts` +3.
**Break-it: 6/6 mutations killed**, including the one that matters most:
`transmission ?? undefined`, the idiom the screen uses for its other
nullable field, which would drop the key and never clear. jest **1174
passed / 96 suites**, tsc 0, eslint 0 errors on the changed files (two
pre-existing `no-void` warnings, not in changed lines).

**Decision:** the create screen is not changed (D7); filed as F147.

### 2026-09-24 — Follow-ups filed; F121 closed

`next_f_number.sh` → F145. Filed in the **mobile** file, where the code
is: F145 (the lookup's value as a suggestion; spans both, filed where the
rider-facing part lands), F146 (bulk editing), F147 (the create screen).
Mobile `0a339d1`. F121 closed in this file, remainder pointed at F147.
Filing them flipped which file leads, and the finding contract's pin on
that went red → bug fix #2.

### 2026-09-24 — Regression of record, both repos

`COLLECTED_TEST_FLOOR` 8959 → 8999 first (`d91c243`; +40 reconciled: 25
from this phase's file, +1 from bug fix #2, 14 from
`test_roadmap_continuity.py`, added by `76edc69` and never added to the
floor). 244G scanner over `tests/`: 0. `__pycache__` cleared, `-B`. The
FOLLOWUPS edits for F148 were stashed in both repos for the length of the
run, because the finding contract reads both files: the run saw
`d91c243`'s tree and nothing else.

- **Backend regression of record at `d91c243`: 8999 passed, 0 failed,
  0 skipped, 8 warnings, 48:31** (floor 8999).
- **Mobile regression of record at `0a339d1` (code at `0e1ed53`): jest 1174
  passed / 96 suites; tsc exit 0.**

### 2026-09-24 — F148 filed; Step 0 re-verified; deploy

**F148:** reading A7 to learn what the close-out needs showed its
version-header half is keyed to the history table's first bold row, which
is 244M, so it cannot fire for any other phase. Filed, not fixed.

**Step 0 re-verified on a fresh copy of the live DB:** schema 66, 10
vehicles, 0 transmissions, 1,046 `known_issues`; main file mtime
2026-09-22 16:25, unchanged. A 0-byte `-wal` and a `-shm` carry 12:15
today, the time of my Step 0 read, most likely the failed `sqlite3 -readonly`
open; the WAL is empty, so nothing was written.

**Deploy:** 257B has no migration and writes no database, so, as in 257,
no backup was taken: backing up would have meant deleting the oldest of
the five in `~/backups/motodiag/` for a database this phase does not touch.
No motodiag backend process or launchd job is running; the API change
takes effect at the next `motodiag serve`. Deploy is the merge and push of
both branches.

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

**Commit.** `8e039e7`

### Bug fix #2 — 2026-09-24

- **Issue:** `test_phase255D_finding_contract::…test_both_followups_files_are_read`
  failed, `assert 144 > 147`, once F145–F147 were in the mobile file.
- **Root cause:** the test pinned `max(backend) > max(mobile)`, a snapshot
  of which file was ahead, and asked for the allocation's assumptions to be
  revisited if it flipped. Revisited: `next_f_number.sh` takes the max over
  both files and B1 compares the header with that same global max. Nothing
  depends on which file leads.
- **Fix:** the pin is replaced by `test_the_next_number_clears_both_files`
  (the script's next number is `max(both) + 1`). The findings stay in the
  mobile file; moving them to satisfy the pin would break the contract.
- **Files:** `tests/test_phase255D_finding_contract.py`,
  `.claude/skills/finding/CHANGELOG.md`.
- **Verified:** the new test is red with the script narrowed to one file,
  green restored (script diff empty); gates (191C, 244G, 255D
  finding/closeout/refute contracts, roadmap continuity) **106 passed**;
  `finding_check` exit 0.

**Commit.** `df82a21`
