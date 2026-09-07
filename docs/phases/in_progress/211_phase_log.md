# Phase 211 — BMW R-series boxer twin — Phase Log

**Status:** 🔨 In progress
**Started:** 2026-09-07
**Repos:** `Kubanjaze/moto-diag` + mobile, branch `phase-211-bmw-r-series`

---

### 2026-09-07 — Plan v1.0 + Step 0 audit

- **Track K opens with a decision, not a file.** Thirty phases of
  repair knowledge authored from training data, into a table with no
  provenance column. Raised before writing anything; the user chose to
  add provenance and tag Track K content as model-generated rather than
  proceed as Tracks B did or pause.
- **Step 0 caught a tenfold overstatement first.** The docs claimed
  ~6,600 known issues; a fresh `db init` loads 660. Originated as a
  row-count comment in Phase 206, copied forward by everything that
  cited it. Fixed on `master` with a guard before this branch was cut —
  auditing what exists before adding to it is the only reason it was
  noticed.
- **Greenfield for BMW, reshape for provenance.** No BMW seed file
  exists; three cross-platform entries mention it in passing. The
  `parts` table already has `verified_by`, so the concept has precedent
  in the schema. Every `issues_repo` read is `SELECT *` and the loader
  uses `item.get()`, so the new column reaches the CLI and API without
  touching a query.
- **The content will be tagged for what it is.** Twelve boxer entries,
  each `model-generated`, each written to be checked by someone who
  knows the bike. Figures I am not confident in are left out rather
  than invented.
