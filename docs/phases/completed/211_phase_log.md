# Phase 211 — BMW R-series boxer twin — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-07 | **Completed:** 2026-09-07
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

### 2026-09-07 — Built. Provenance first, then twelve boxer entries.

- **Migration 051** adds `known_issues.source`, CHECK-constrained to
  `unverified · model-generated · forum · service-manual ·
  mechanic-verified`. Verified on a fresh DB and on a DB built to 50
  with a pre-existing row — that row reads `unverified` after, which is
  the true statement about its origin. The CHECK rejects
  `model_generated` with an underscore; a typo cannot become a fourth
  silent category.
- **The CLI says it out loud.** `kb show` prints `Source:` under the
  fix procedure and, for anything short of a manual or a mechanic, a
  one-line warning — captured from a real run, not described. For
  `service-manual` content the warning is absent, which is what makes
  it mean something. `kb list` gains a `Source` column.
- **The F9 lint fired in the direction it was built for.** I typed the
  API field `str`; `--check-pydantic-literal-vs-check` flagged it
  against the migration's CHECK before anything was regenerated.
  Retyped as a `Literal` alias, so OpenAPI emits a strict enum and the
  mobile codegen produced `"unverified" | "model-generated" | …` — the
  F37 discipline enforced *before* the drift, not after.
- **The knowledge-base count guard fired too.** 660 → 672 failed four
  docs that still said 660. That is the guard working; corrected.
- **Twelve entries, each tagged `model-generated` and each admitting
  it in its own description text**, so a reader of the raw JSON with no
  schema in front of them is still told. Entries I could not write
  without inventing a figure — wethead starter sprag, R nineT fork
  specifics — were dropped, and the plan's Logic section was corrected
  to say what was actually built.
- **Regression 4930 / 0. F9 lint clean. Mobile `tsc` clean.**
- **Key finding: the honest label cost one migration, one parameter and
  a render function**, and it is what lets the remaining 29 Track K
  phases proceed without pretending. A mechanic who knows the bike can
  promote an entry to `mechanic-verified` and the warning goes away —
  which is the review loop the table never had.
