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

---

## Inventories are not status (added 2026-09-02, F54)

The boundary above governs **phase status**. It does NOT exempt the backend's
architecture inventories from staying accurate.

The backend `implementation.md` **Package Inventory**, **Database Tables**, **CLI
Commands** and **Dependencies** sections describe what the backend IS, not how far
a track has got. A Track I phase that adds a backend package, table, migration or
route MUST update them in the same close-out, even though its status row lives in
the mobile repo.

**Why this line exists:** between Phases 194 and 200 the backend gained the
`reporting` and `push` packages and five tables while `implementation.md` still
described `api` as "empty, awaiting Phase 175". Every one of those phases was
Track I, and each close-out correctly skipped the backend status surfaces — and
then skipped the inventories with them. Repaired under F54; this rule is the
structural fix so the same drift cannot recur by the same reasoning.

---

## Findings are governed too (added 2026-09-21)

The boundary above governs **phase status**, and since F54 the backend's
architecture **inventories**. It said nothing about findings, and the gap had a
measurable effect: nine consecutive backend findings (F115–F123, moto-diag
Phase 255 — retrieval paths, corpus rows, manufacturer documents) were filed in
the **mobile** repo, because that is where the follow-ups file happened to
start and the practice lived in an agent's memory rather than in this contract.

**The rule, which is now part of this contract:**

1. **A finding lives in the repo whose code it is about.** Backend findings in
   `moto-diag/docs/FOLLOWUPS.md`; mobile findings in
   `moto-diag-mobile/docs/FOLLOWUPS.md`. A finding that spans both is filed
   once, in the repo where the fix lands, and referenced from the other.
2. **F-numbers are ONE global sequence across both files.** The next number is
   `max(F across BOTH files) + 1`, never the max of one. A number is never
   reused, and a finding that moves repos **keeps its number**.
3. **Each file's header states both rules and points at the other file.** The
   rule lives in the documents, not in memory.

**Migration, 2026-09-21:** F115–F123 moved from the mobile file to the new
backend file, keeping their numbers, with a one-line pointer left behind.
**Nothing older moved** — entries below F115 predate the rule and stay where
they are, including several about backend code. Renumbering history would break
every reference to them in phase docs and roadmap rows, which is a worse defect
than an inconsistent archive.

This is consistent with the boundary above rather than an exception to it:
per-phase docs follow the *phase*, and findings follow the *code*. Those differ
only for Track I, where a mobile-owned phase may produce a backend finding —
which rule 1 resolves by asking where the fix lands.

---

## Evidence lives outside the repos, at one durable path (added 2026-09-21, F127-adjacent)

The 263 source documents every Phase 250–256 citation rests on lived at
`/private/tmp/claude-501/<session-id>/scratchpad`. That path is
**session-specific and not durable**: the session id recorded in Phase 255B's
own handoff was already dead when 255B opened, and `/private/tmp` is cleared
by the OS without notice. It is the same mistake this contract's deploy rule
already forbids for backups, made with irreplaceable evidence instead of a
database copy.

**The rule, which is now part of this contract:**

1. **The canonical evidence path is `~/research/motodiag/`.** Every citation
   path — in a phase doc, a row description, a finding, or a commit message —
   points there.
2. **Never `/private/tmp`, never a session scratchpad.** A scratchpad holds
   intermediates that can be regenerated. A source document cannot.
3. **A phase that acquires a document files it under the canonical path before
   citing it,** not after. A citation to a path that does not exist is a
   citation to nothing.
4. **Citations name the file relative to that root** — `manuals/genuine/…`,
   not an absolute path that encodes someone's home directory.

**State recorded at the move, 2026-09-21.** 9,624 files, 2.7 GB, verified
**byte-identical by an md5 manifest across all 9,624 files** before the source
was removed. Counts match on both sides: 9,624 files, 263 `.pdf`, 2,878,775,081
bytes.

**Two counts that do not reconcile with F127, recorded rather than resolved.**
Of the 263 files carrying a `.pdf` extension, **247 are PDFs by magic bytes**
and **16 are download debris** — 12 HTML documents, 2 short ASCII files, 1 XML
stub, 1 empty file. F127 records **32** debris files. Neither number should be
trusted until F127's own phase re-derives it against this tree.

**Build debris was moved intact, not pruned.** The tree carries two throwaway
virtualenvs (`grom/venv`, `honda/venv` — 5,242 files) and 235 MB of pip logs.
A durability fix does not authorise deciding what counts as evidence; pruning
is a separate decision.
