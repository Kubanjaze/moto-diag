# Phase 379 — Small fixes from the open-findings triage — phase log

**Status:** 🚧 In progress (2026-10-08)
**Branch:** `phase-379` (Opus session, main checkout)

---

### 2026-10-08 — Opened

The operator, in this session: "approved: close the 11 now. 379 = the nine
small fixes. then 380 = F129 + F142, then the content batch. D, E and F stay
as the triage says." Section A was done first, on master (`0220fdf`): 11
closed, with their evidence re-measured, and F198 filed for the Filly,
which F119 still held. The prompt is `docs/prompts/379_small_fixes.txt`.
Row 379 went 🚧 before Step 0; `roadmap_check.py` exit 0.

### 2026-10-08 — Step 0 and v1.0

`379_step0.md`. Every finding re-measures. Three add to the triage:
- F176's delete is blocked by five tables, not two;
- a Fiddle 50 service manual is on disk, its cover rendered with Quick
  Look;
- `VehicleContext` is not in the mobile snapshot, so F144 should need no
  mobile session.

No fork, so no stop. The decisions are in S0-2.

The first fast run before v1.0's commit went red on B2: v1.0 and Step 0
cited F199 before it was filed. F199 was then filed with the finding
skill, before any commit. Rule 6's "file before citing", caught by B2,
which is the check working.
