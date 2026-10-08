# Phase 380 — Row identity, the junction per make, then the content batch — phase log

**Status:** 🚧 Step 0, stopped for the operator (2026-10-08)
**Branch:** `phase-380` (Opus session, main checkout)

---

### 2026-10-08 — Opened, Step 0, and the stop

The operator: "then 380 = F129 + F142, then the content batch." The
prompt is `docs/prompts/380_row_identity_and_content.txt`. Row 380 went 🚧
before Step 0.

`380_step0.md`:
- **F129:** live and seed match one to one on `(make, model, title)`, 1060
  each.
- **F142:** of 125 models in multi-make rows, 90 have their own make on
  disk and 35 do not; assigning the 90 removes 104 junction rows.

Q1 (F129's key) and Q3 (F142's unassigned models) are real forks: each
option ships different behaviour. Q2 decides whether content edits stay
reviewed migrations. Stopped for the operator, with recommendations 1A,
2A, 3A.
