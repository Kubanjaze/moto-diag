# Phase 361 — F178 hybrid values, and F177 engine type — phase log

**Status:** 🚧 In progress
**Branch:** `phase-361` (Opus session, main checkout, the only writer)

---

### 2026-09-29 — Opened

The prompt is `docs/prompts/361_hybrid_values_and_engine_type.txt` (merged
in `af0d392`). The operator's decision (2026-09-29), verbatim:

> 361 with F177, write the prompts

It answered the recommendation of a small phase before Track O batch 1, run
the two-session way 360 was: the safety checker first, then the API's
powertrain values, then a mobile session for the snapshot.

Read first: the 360 handoff (`docs/handoffs/2026-09-29_360_closed.md`),
F177 and F178, the mobile repo's F179, 360's documents in `completed/`
(the migration 074 rebuild and the gate 11 stop), and the deploy skill.

- 361 is the next free number: the highest row was 360, and no phase
  document, handoff or ROADMAP line names 361.
- Row 361 🚧: `5fb84a8`, pushed. `roadmap_check.py` green; the row is 71
  words. `wholetree.sh` before the commit: 1480 passed.

### 2026-09-29 — Step 0

`361_step0.md`. What it found beyond the prompt:
- **The safety hole is wider than F178 says.** Any string outside
  `("ice", "hybrid")` other than `None` hides the seven rules: an empty
  string and `ICE` in capitals do too, not only the two hybrid variants.
- **The engine type has F178's shape exactly.** The API's literal holds
  `rotary`, `diesel`, `none`; the enum holds `electric_motor`, `hybrid`,
  `desmodromic`. Create refuses the first three with 400, an update stores
  them, and the API cannot record an electric motor. Nothing reads the
  engine type to hide anything.
- **Migration 074's own rebuild** carries `engine_type TEXT DEFAULT
  'four_stroke'`, so that is the live column's default.
- **Parts sourcing prints `engine_type: None`** for a NULL, 250B's trap.
- **No CLI command can correct an engine type.**
- Live: 10 bikes, all `ice` and `four_stroke`, schema 74. No value
  outside either enum, so part 2 changes no live row.

The per-option test counts were measured in four scratch worktrees, with
the mobile repo linked beside each so gate 11 ran against the real
snapshot. F178 alone breaks only gate 11's snapshot test and its three
reruns: the planned stop. F177: (a) 120, (b) 3, (c) 93.

**Stopped for the operator's pick (rule 1: a real fork).**
