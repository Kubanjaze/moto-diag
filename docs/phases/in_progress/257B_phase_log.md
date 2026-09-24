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
