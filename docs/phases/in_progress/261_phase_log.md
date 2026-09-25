# Phase 261 — Track N batch 1: tire, brake, suspension and drivetrain service — phase log

**Status:** 🚧 In progress
**Branch:** `phase-261` (Opus session, main checkout)

---

### 2026-09-25 — Opened: Track N batch 1

The operator's prompt, 2026-09-25: start Phase 261, Track N batch 1 of
3, and run it to its finish line. On 2026-09-25 the operator approved
doing Track N's eleven remaining rows in three batches instead of eleven
phases. Batch 1 is rows 261 (tire service), 269 (brake service), 270
(suspension service) and 271 (chain, belt and shaft service).

Read before acting: CLAUDE.md and the working-rules index; the ROADMAP's
Track N rows and the status key; `ROADMAP_AUTHORITY.md` (205+ is this
repo's); the newest handoffs (`2026-09-25_355_closed.md`, then
`2026-09-25_260_closed.md`); 260's implementation, phase log and Step 0
(the pattern this batch follows); migration 068 and its tests;
`roadmap_check.py` (R1–R6); the closeout and refute skills.

**Ledger convention, the operator's words, recorded as given.** Phase
261 carries the batch. Row 261 closes with **CLOSED date** and the
regression line. Rows 269, 270 and 271 close ✅ "folded into 261" with
no CLOSED date of their own. `implementation.md` gets one history row,
261, and the close-out writes one handoff,
`docs/handoffs/<date>_261_closed.md`. This keeps `roadmap_check` R6
asking for exactly one handoff per close-out. Measured before relying
on it: R6 sees a close only in a ✅ row carrying `CLOSED YYYY-MM-DD`, or
in an `implementation.md` history row (`closes()`), so ✅ rows 269–271
without a date, and without documents of their own, raise neither R3
nor R6.

Branch `phase-261` from `master` at `a547958`. **Ledger step before Step
0:** rows 261, 269, 270 and 271 → 🚧, commit `4609c26`;
`roadmap_check.py` ok.

### 2026-09-25 — Step 0: an extension, four checklists, no fork

The measurements are in `261_step0.md`. In short:

- The four workflow categories have existed in the enum since Phase 114,
  and none has a template. The `workflow` door renders whatever is
  seeded, so the batch is **one content migration (069) plus tests, with
  no new module**.
- The library supports every subject of every row in the makers' own
  words. The one negative that looked certain, a final-drive belt, died
  inside Step 0 to Yamaha's "drive belt slack" (XVS950 and XVS1300
  owner's manuals). Three negatives stand, each with a control on the
  exact page: N1 (no wear-pattern names), N2 (no u-joint inspection), N3
  (no belt alignment figure).
- **No fork.** Every row is a checklist (S0-4). The drivetrain row's
  three drive types are one template with optional per-drive items.
  Decided, not asked, because three templates would ship the same items
  under three slugs.

**Subconscious was down (S0-7).** The sandbox proof passed: planted
writes into the repository and the library failed with `Operation not
permitted`, and the in-box control succeeded. Subconscious then
answered **403, "organization access is suspended; the entitlement must
be restored"**. The extraction ran on rule 2's fallback,
`--source-route anthropic` (`claude-opus-5-5@medium`), in the same
sandbox, one no-tools turn per row: 259 facts, 353,345 tokens, **every
quote verified against its page (259/259)** by a checker seen to fail
on a corrupted figure and on a wrong page. Run directory:
`~/.cache/motodiag/source-runs/261_step0/`. The operator should know the
Subconscious account needs its entitlement restored.
