# Phase 260 — Pre-purchase inspection — chassis — phase log

**Status:** ✅ Complete (2026-09-25)
**Branch:** `phase-260` (GLM builder session, sandboxed)

---

### 2026-09-25 — Opened as the operator's third Subconscious run

Taken from `docs/handoffs/2026-09-24_259_closed.md`: row 260, PPI —
chassis, on the substrate 259 gave a door. Read before acting: the 259
handoff; ROADMAP rows around 260 (the status key, the 259 row's
`**CLOSED 2026-09-24.**` shape); `ROADMAP_AUTHORITY.md` (260 is backend,
205+); FOLLOWUPS in full (F158's re-measure names this phase's own
predecessor description as an open miss; F153–F157 remain open);
259's implementation, phase log and Step 0 (the pattern this phase
follows); the closeout and finding skills; the working-rules index.

Branch `phase-260` from `master` at `7709a15` (259 is merged; the
handoff's instruction). **The ROADMAP row flip (260 🔲 → 🚧) is commit
`b1a3e70`, which this session did not author**: it landed on the branch
at 00:59:21, after the branch was created and before Step 0 — the
correct ledger step, in the correct place, written from outside the
session (the operator's side; its message says "opens from the 259
handoff" and it carries the Claude attribution). Recorded here
faithfully rather than claimed: standing rule 5 says another session
on this checkout only reads, so the operator should know a writer
touched the branch. It stayed, verified by `roadmap_check.py` (ok) —
it is exactly the step the rule requires, done before Step 0 as the
rule requires.

**The operator's sandbox differences, acknowledged:** this clone and
the session tmp are writable; everything else is not. Any live step
runs against the 1,060-row snapshot as a dry run. Citations point into
`~/research/motodiag`. The finish line is "ready to merge": no
regression of record, no refute, no merge, no deploy — those are the
Opus session's and are pending below. Every document-sourced claim is
listed with its citation in the implementation doc's claims table
(C1–C18).

**Sandbox measurements, logged per the operator's instruction:**
planted writes to `~/research/motodiag` and to the main checkout fail
with `operation not permitted`, files not created (standing rule 2's
technical boundary). zsh heredocs fail as in 258/259; commit messages go
through `-F` files in the session tmp. `259_step0.md`'s PYTHONPATH
measurement still holds.

### 2026-09-25 — Step 0: extension, no fork

Measurements S0-1..S0-5 are in `260_step0.md`. In short: the substrate's
front door exists (259), so this phase is one content migration plus
tests, and **no new module**; the library supports the row's seven
subjects from five held documents (KTM 250/300 EXC TPI OM pp.
76/94/99/101/115/116/164; Zuma 125 2009 SM pp. 34/55/93–95; CHF50 SM
pp. 12/217/241/243/314/318; Metropolitan 2025 OM pp. 64–66/121; F800R
OM pp. 94–95), and **three negatives** are measured whitespace-proof
with positive controls: no frame-alignment figure, no swingarm play
tolerance, no wheel-bearing play figure — the nearest real play figures
in the whole library are a *crankshaft* bearing's, which is the
positive control for the wheel-bearing search itself. Chassis subjects
are powertrain-agnostic: the template is for all three powertrains,
deliberately unlike 259's ICE-restricted engine protocol. And
`ppi_engine_v1`'s description still ends "the chassis protocol is Phase
260" — measured present in the snapshot; this phase owns the re-point
(D3, the operator-approved option-1 shape from 259's review).

**Decision (logged, not asked): no fork.** The plan follows 259's
substrate pattern with the door already built. **Step 0 committed at
`1baa7fc`, then v1.0 at `6fc0784`** — before any code was written.

### 2026-09-25 — Build: migration 068, 26 tests

Committed at `0bd7836`. What shipped:

- **Migration 068 `ppi_chassis_workflow`** (schema 67 → 68): the
  `ppi_chassis_v1` template (category `ppi`, powertrains
  `["ice","electric","hybrid"]` — all three, S0-4), **7 items** (frame
  and crash evidence; steering head bearings; front fork; swingarm;
  wheel bearings and rims; brakes; tires), every figure cited to a held
  document with its PDF page, and the one-line UPDATE re-pointing
  `ppi_engine_v1`'s description at the new slug by name — removing the
  F158 review miss the 259 deploy recorded. The rollback peels exactly
  that: items cascade, template gone, the seeded description restored
  verbatim.
- **No new module, no CLI, no repo change**: `motodiag workflow
  list/show` (259) renders the new template as soon as the migration
  seeds it. `SCHEMA_VERSION` 67 → 68 in `core/database.py`.
- **`tests/test_phase260_ppi_chassis.py`** — 26 tests: the migration
  (fresh init; the upgrade-from-67 test builds its own 67 baseline,
  never the snapshot; the rollback round trip with the description
  restored), the content pins (every cited figure, **per field**), the
  two no-figure items (frame, swingarm: no mm, no %, no N·m — and both
  say where the figure belongs), the F158 pins (with the pattern seen to
  catch a planted "Phase 999" and to leave a BMW F800R alone), the
  applicability (offered for electric, ice and hybrid; the engine
  protocol still excluded from electric), and the CLI through the real
  registered group.

**Known-bad controls, each planted, seen red, reverted:**

1. a planted "alignment tolerance 0.5 mm" in the frame item fails the
   no-figure pin;
2. a corrupted figure in the brakes item's instruction alone
   ("2.6 mm" for "2.5 mm") fails the per-field pin — the description
   still carries the right figure, which is exactly what the pin exists
   to catch;
3. a planted "Closed at Phase 999" in the new template's description
   fails the F158 pin;
4. the UPDATE disabled (`WHERE … AND 1 = 0`) fails both the re-point
   test and the upgrade-from-67 scope guard ("exactly one existing row
   altered").

**The whole-tree gates** (rule 3 plus 259's list, plus the substrate and
allowlist gates that caught 259's fixes #4/#5): 191C, 244G, 244U, 244V,
244T, 244J, 244Y, 256, 209B, 114, F124, 240c, 191D, roadmap continuity
— **521 passed**; `finding_check.py` exit 0, both variants. The
allowlist did not move: no module was wired or unwired.

**The dry run** (a copy of the snapshot in the session tmp, never the
snapshot itself): schema 67 → 68; 3+16 → 4+23 templates+items;
`ppi_engine_v1`'s description re-pointed; the `known_issues` content
hash `5932cd02c78ae850` identical before and after; `PRAGMA
integrity_check` ok.

`COLLECTED_TEST_FLOOR` raised 9346 → **9372** with the close-out commit:
measured the way the floor test itself measures (`python -m pytest
--collect-only -q`, repo root), **9,372 = 9,346 + 26**. The first
measurement run reported one transient collection error that two
immediate re-runs did not reproduce (the background full suite was
mid-collection at the time); the floor is raised on the clean count,
and the phase log records the anomaly.

**Decision (logged, not asked): the row closes ✅ with the close-out
commit**, as 259 and 258 did on this date. The regression of record,
the refute pass, the merge and the deploy remain pending below; the
handoff says so; `closeout_check` A5 is red by design until Opus records
the regression line.

**Decision (logged, not asked): a finding was filed, not an edit
made.** `generic_ppi_v1`'s starter item 5 carries uncited figures
("Pads >3mm… tires <5 years old") that the library contradicts
(F800R's pad limit is 1.0 mm). Measured in Step 0, filed as **F159** in
`docs/FOLLOWUPS.md`; the item is the substrate's seed, not this phase's
content, and its fix is a sourcing decision plus a migration keyed on
the old text (F129's shape).

### Bug fixes

None. Three authoring defects were caught by the first test run and
folded into the build commit before it landed (a dropped closing
parenthesis for migration 067's tuple, an over-demanding fork pin, CLI
needles that wrapped at the 80-column terminal — Deviations in the
implementation doc); the four known-bad probes were deliberate; the
full suite's only red file is the expected environmental one. A phase
with no bug fixes writes no register (the close-out skill's skip rule,
stated here).

### 2026-09-25 — Close-out

v1.1 with Deviations and Results in the implementation doc; both phase
documents to `docs/phases/completed/`; ROADMAP row 260 ✅ with
**CLOSED 2026-09-25**; root `implementation.md` 0.13.81 → 0.13.82 with
the Phase History row; `COLLECTED_TEST_FLOOR` 9346 → 9372; F159 filed in
`docs/FOLLOWUPS.md`; the handoff
`docs/handoffs/2026-09-25_260_closed.md` in this close-out commit,
before any merge, per rule 4.

**The FULL suite** (instruction 5, the whole point of which is that it
replaces any hand-kept list): run in the sandbox before the close-out;
the only red file expected is `tests/test_phase209_packaging.py` (7
failures, the sandbox's exported PYTHONPATH, environmental — recorded in
259's phase log and expected here). Anything else red is mine to fix
before the close-out commit; the result line is recorded here when the
run completes.

### Pending (Opus session, outside the sandbox)

- **Fetch and review `phase-260`** in `~/Projects/moto-diag`. Five
  commits on the branch at close-out, all named from `git log` (the
  259 lesson: no hash from memory): `b1a3e70` (row 🚧 — external, see
  the log's opening entry) → `1baa7fc` (Step 0) → `6fc0784` (v1.0) →
  `0bd7836` (build: migration 068, 26 tests) → this close-out commit
  (v1.1, the row ✅, the history row, the floor, F159, the handoff).
- **Run the regression of record.** Expect **9,372 passed, 0 failed, 0
  skipped** (the floor is already raised on the branch). Record the
  line with its commit hash and count in this log so `closeout_check`
  A5 goes green. `test_phase209_packaging.py` runs clean outside the
  sandbox (259's measurement).
- **Run the refute pass** over the claims table in
  `260_implementation.md` (C1–C18): open each cited document at its PDF
  page; re-derive the three negatives (C15–C17) with the session tmp's
  `census_negatives.py` or any whitespace-proof scan; reproduce the
  repo measurements (the snapshot at 67 with the F158 phrase; a fresh
  `db init` at 68 with `ppi_chassis_v1` + 7 items; the one-row UPDATE's
  before/after).
- **Backup the live database, then let migration 068 run** on the
  merged deploy (`~/backups/motodiag/`, retain 5, print the before-state,
  dry-run on a copy first). The migration's effect on the live DB is:
  one template + seven items inserted, **one existing row altered** —
  `ppi_engine_v1`'s description, re-pointed from "the chassis protocol
  is Phase 260" to "for the full chassis-side protocol see
  ppi_chassis_v1" (the operator-approved option-1 shape; the dry run
  recorded above shows the exact before/after; if the operator strikes
  this, drop the UPDATE from 068 and its rollback together). Schema 67
  → 68; the 1,060-row corpus is untouched (hash-verified in the dry
  run).
- Then merge to `master`, push, deploy, and add the deploy's outcome to
  the handoff (rule 4).
- Findings: **F159** filed by this phase; F149, F153–F157 remain open
  from earlier phases.
