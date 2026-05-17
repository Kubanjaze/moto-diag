# ROADMAP Authority Boundary

**Status:** Binding contract. Identical copy committed to both `Kubanjaze/moto-diag`
and `Kubanjaze/moto-diag-mobile`. This file is a contract, not project state —
its duplication across both repos is intentional and correct.

**Established:** 2026-05-17
**Reason:** Track I (Phases 185–204) status was being mirrored in two roadmaps
with no sync mechanism, producing recurring drift (the 195/195B miss being the
triggering instance). This contract removes the drift class structurally rather
than relying on hand-sync discipline.

---

## The boundary

MotoDiag spans two repos and one shared phase ledger. Status for any phase lives
in **exactly one** authoritative place:

| Phase range | Track(s) | Status authority | Surfaces that are authoritative |
|-------------|----------|------------------|----------------------------------|
| 01–184 | A–H | **Backend repo** | backend `docs/ROADMAP.md`, backend `phase_log.md`, backend `implementation.md` Phase History table |
| 185–204 | I (Mobile) | **Mobile repo** | mobile `docs/ROADMAP.md`, mobile `implementation.md` Phase History/status table, mobile `phase_log.md` |
| 205–352 | J–T | **Backend repo** | backend `docs/ROADMAP.md`, backend `phase_log.md`, backend `implementation.md` Phase History table |

Track I is the only mobile-owned track. Backend commits that land inside a
Track I phase (e.g., 191B's `efb0b7e`/`32ac5c2`, 195B's Whisper pipeline) are
**contributions to a mobile-owned phase**, not a separate backend track. Their
status is recorded by the mobile repo, not mirrored into a backend Track I table.

## What the backend aggregate surfaces carry for Track I

The backend `docs/ROADMAP.md`, `phase_log.md`, and `implementation.md` Phase
History table **must NOT carry a per-phase Track I table or per-phase Track I
rows.** They carry exactly one Track I pointer entry that defers to the mobile
repo as authority. Backend surfaces may state coarse Track I headline status
(e.g., "195B closed, 195C reserved") in the pointer entry, but the per-phase
detail of 185–204 lives only in the mobile repo.

Historical Track I rows already present in backend `phase_log.md` /
`implementation.md` (191B, 193, etc.) are **frozen as written**. They were
accurate at time of writing. Do not rewrite or delete them — the phase log is
append-only timestamped history per CLAUDE.md. No new Track I rows are added to
backend aggregate surfaces after this contract takes effect.

## Per-phase doc files — unchanged

Per-phase implementation/log files (`NNN_implementation.md`,
`NNN_phase_log.md`) continue to live in the **backend** repo at
`docs/phases/completed/`, sequentially numbered alongside 01–184. This is the
established convention and this contract does NOT change it. Track I phase docs
(`191B_*.md`, `193_*.md`, `195B_*.md`, …) stay in the backend ledger. Mobile
`implementation.md` already documents this and links back. Do not create a
parallel mobile `docs/phases/` tree.

## Mobile phase_log.md — required, authoritative

The mobile repo carries `phase_log.md` at its root per CLAUDE.md product-project
structure (every product project carries one). It is authoritative for Track I
project-level state (architecture changes, package additions, gate status).
Pre-contract Track I per-phase history is referenced from the backend ledger;
this file owns Track I project-level changes going forward.

## Out of scope

Document version strings (`implementation.md` version header,
`pyproject.toml`, `package.json`) are independent per-document release counters
per CLAUDE.md's per-document versioning rule. They are NOT status and are NOT
governed by this contract. Backend `~0.13.x` vs mobile `~0.1.x` is expected and
correct; do not reconcile them.

## Drift-detection

None required. The contract removes the drift class by construction: each
phase's status lives in exactly one authoritative surface. There is no sync
mechanism to maintain because there is nothing to sync.

## Changing this contract

This file is a contract. Amending the ownership boundary requires an explicit
decision recorded in both repos' phase logs and a matched commit to both copies.
Do not edit one copy without the other.
