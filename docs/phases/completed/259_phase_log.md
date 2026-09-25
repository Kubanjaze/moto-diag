# Phase 259 — Pre-purchase inspection (PPI) — engine — phase log

**Status:** ✅ Complete (2026-09-24)
**Branch:** `phase-259` (GLM builder session, sandboxed)

---

### 2026-09-24 — Opened as the operator's second Subconscious run

Taken from `docs/handoffs/2026-09-24_258_closed.md`: row 259 is the Track
N opener, PPI — engine. Read before acting: the handoff, ROADMAP rows
around 259, `ROADMAP_AUTHORITY.md` (259 is backend, 205+), FOLLOWUPS
(F149, F153–F157 open; the whole file), 258's implementation and phase
log (the close-out shape this phase follows), Phase 114's implementation
doc (the substrate this phase extends), and the workspace working-rules
index.

Branch `phase-259` from **`3528e90`** (HEAD of `phase-258` as the Opus
session reviewed it — the handoff's instruction, not `master`, which
moves tonight when 258 merges). ROADMAP row 259 🔲 → 🚧 **before
Step 0** at `08228dd`, per CLAUDE.md.

**The operator's eight sandbox differences, acknowledged:** this clone and
the session tmp are writable; everything else is not. Any live step runs
against the 1,060-row snapshot as a dry run. Citations point into
`~/research/motodiag`. The finish line is "ready to merge": no regression
of record, no refute, no merge, no deploy — those are the Opus session's
and are pending below. Every document-sourced claim is listed with its
citation in the implementation doc for that pass.

**Sandbox measurements, logged per the operator's instruction:** planted
writes to `~/research/motodiag` and to the main checkout fail with
`operation not permitted` (files not created — the boundary is technical,
standing rule 2, not an instruction). zsh heredocs fail as in 258;
commit messages go through `-F` files in the session tmp. Details and
one more (the session's exported `PYTHONPATH`) in `259_step0.md`.

### 2026-09-24 — Step 0: extension, no fork

Measurements S0-1..S0-5 are in `259_step0.md`. In short: the Phase 114
substrate carries the PPI category, the tables, the models and the CRUD —
and **no consumer at all**: nothing in `cli/` or `api/` imports a line of
it, and no PPI content exists beyond `generic_ppi_v1`'s 5 starter items.
The library supports four of the six subjects from held documents (CHF50
SM pp. 11, 13, 79; Metropolitan 2025 OM pp. 17, 62); **leak-down is a
negative claim** — 260 PDFs searched, 0 hits, control "compression" finds
178 — so that item ships with no figure. `checklist_items` has no unique
constraint, so the seed lives in the one-shot migration journal.

**Decision (logged, not asked): no fork.** The plan follows 114's own
forward pointer (content on the substrate), 244V's precedent for the
front door (a reference with no entry point is dead weight the day it
ships), and 244Z's rule for figures (invent nothing; cite or defer). A
new template `ppi_engine_v1` rather than editing `generic_ppi_v1`
(identity: the generic stays the quick check, 260 owns chassis); the
generic's stale forward pointer re-pointed by the same migration. **Step
0 committed at `ce2adb9`, then v1.0 at `7cd0737`** — before any code was
written. (The first draft of this log and the handoff wrote a hash from
memory, `0342ba2`, that resolves to nothing; corrected in the docs-fix
commit after the close-out — the S8 lesson, relearned by this phase
itself.)

### 2026-09-24 — Build: migration 067, the CLI front door, 23 tests

Committed at `9f80234` (with bug fix #1 folded in), then fix #2 at
`f47cc81`, then close-out. What shipped:

- **Migration 067 `ppi_engine_workflow`** (schema 66 → 67): the
  `ppi_engine_v1` template (category `ppi`, powertrains
  `["ice","hybrid"]` — electric excluded, S0-4), **7 items** mapping to
  the row's six subjects (static visual; battery/charging;
  starter/cold start/running; compression; leak-down; oil; fuel), and
  the one-line UPDATE re-pointing `generic_ppi_v1`'s description. The
  rollback peels exactly that: items cascade, template gone, old
  description restored.
- **`src/motodiag/cli/workflow.py`** — the substrate's first front door:
  `motodiag workflow list [--category]` and `motodiag workflow show
  <slug>`, printing the full item text with its citations. Registered
  from `cli/main.py`. ~95 lines, the `reference.py` pattern (the module
  244V built for exactly this unreachable-reference shape).
- **`tests/test_phase259_ppi_engine.py`** — 23 tests: the migration
  (fresh init, the snapshot dry run 66 → 67 with the 1,060 rows
  untouched, the rollback round trip), the content pins (every cited
  figure, per field; the leak-down no-figure regex), the applicability
  (electric excluded through the substrate's own filter), and the CLI
  through the real registered group.

**Known-bad controls, each planted, seen red, reverted:** a leak-down
percentage fails the no-figure pin; removing the registration fails all
six CLI tests; a changed "202 psi" caught the first content pin's
defect — bug fix #1 below.

**The whole-tree checks** (rule 3 plus the sandbox list, instruction 6):
191C, 244G, roadmap continuity, F124, F86, 191D, 240c, 241, 244J, 244T,
244V, 256 — **306 passed**; `finding_check.py` exit 0, both variants.
`test_phase209_packaging.py`: **26 passed, 7 failed — identical at the
base commit**, measured in a worktree at `3528e90` under the same
invocation: the session's exported `PYTHONPATH=<clone>/src` leaks into
the file's clean venv (pip sees the package "already installed" via the
source tree and installs no `motodiag` script), so the clean-venv tests
cannot be clean in this sandbox under any env shape — with `PYTHONPATH`
unset, the clone's own venv leaks the *main checkout* onto `sys.path`
and one test imports the wrong tree. Environmental, not the branch's
diff; the Opus regression of record (no sandbox, no `PYTHONPATH`) is
expected to run 209 green.

`COLLECTED_TEST_FLOOR` raised 9321 → **9344** with the close-out commit:
collected count measured the way the floor test itself measures
(`python -m pytest --collect-only -q`, repo root), **9,344 = 9,321 + 23**;
raised before the regression of record, the floor's own rule.

**Decision (logged, not asked): the row closes ✅ with the close-out
commit**, as 258 did on this date. The regression of record, the refute
pass, the merge and the deploy remain pending below; the handoff says
so; `closeout_check` A5 is red by design until Opus records the
regression line.

### Bug fix #1 — 2026-09-24

- **Issue:** the known-bad probe "corrupt a cited figure" did **not**
  fail the compression pin: planting "210 psi" in the item's description
  passed, because the pin joined description + instruction +
  diagnosis into one string and the instruction still said "202 psi".
- **Root cause:** the pin asserted "the figure appears somewhere in the
  item" instead of "the figure appears in each field that states it" —
  a weakened form of the exact thing F124 is about, written into a test
  whose purpose was to catch figure corruption. A control that survives
  the planted defect it exists for is S4.
- **Fix:** the compression and battery pins now demand their needles in
  **each** field that states them (`description` and `instruction_text`
  separately). Re-planted the "210 psi" probe: the pin fails naming the
  field. Reverted; 23 passed.
- **Files:** `tests/test_phase259_ppi_engine.py`.
- **Verified:** the failing re-plant output (assertion names
  `description`), then green on the reverted tree.

**Commit.** `9f80234`

### Bug fix #2 — 2026-09-24

- **Issue:** `test_f124_schema_pin_discipline.py::…test_no_test_pins_the_head_with_a_literal`
  failed on the first whole-tree run, naming
  `test_phase259_ppi_engine.py:150` — `get_current_version(path) == 67`
  in the rollback test (and `max(MIGRATIONS) == 67` in the migration
  test, same shape).
- **Root cause:** F124 again — an equality against a literal equal to
  the current head is a copy every future migration must edit. Unlike
  258's fix #5, this was caught **inside** the sandbox, because the
  operator's instruction 6 named F124's guard in the run list this
  time.
- **Fix:** at-head asserted against `SCHEMA_VERSION` (the constant, not
  a literal); the `max(MIGRATIONS) == 67` head-ness check dropped
  entirely — that is the genuine pin's job in 240c — and replaced by
  "migration 067 exists by name, `SCHEMA_VERSION >= 67`".
- **Files:** `tests/test_phase259_ppi_engine.py`.
- **Verified:** F124's guard, 240c, 191C, 191D and the full 259 file:
  82 passed.

**Commit.** `f47cc81`

### Bug fix #3 — 2026-09-24

- **Issue:** outside the sandbox,
  `test_upgrade_dry_run_on_a_copy_of_the_live_snapshot` failed in the
  Opus review's worktree (`assert 0 == 66`). It copied
  `data/motodiag.db`, which a fresh checkout does not have.
- **Root cause:** the test read the live database's state, schema 66 and
  1,060 rows. It passed in the sandbox clone only because that clone
  held a snapshot. It would also have failed the first regression after
  this phase's own deploy moved the live database to 67.
- **Fix:** `test_upgrade_from_66_alters_only_the_approved_row` builds its
  own 66 database by applying migrations up to 66, never 067. It then
  asserts the change the operator approved:
  - one template and seven items are added;
  - exactly one existing row, `generic_ppi_v1`, is altered;
  - that row's description names no phase.

  A first rewrite built the baseline by rolling 067 back. It passed a
  mutation that widened the UPDATE to every generic template, because
  the rollback does not undo the extra row. The baseline built up from 66
  catches it.
- **Files:** `tests/test_phase259_ppi_engine.py`.
- **Verified:** 23 passed. Mutations: phase numbers restored to the
  text, red; UPDATE widened to `generic_%`, red. Both reverted.

**Commit.** `7dab6d3`

### Bug fix #4 — 2026-09-24

- **Issue:** the regression of record on `f6bf40b` failed 2 of 9,344, both
  in `test_phase209B_integration_gaps.py`:
  - `motodiag.workflows`, `.models` and `.template_repo` are now
    reachable, so their `UNREACHABLE_MODULES` entries are stale;
  - six public write functions in `workflows/template_repo.py` are live
    orphans.
- **Root cause:** 259's `motodiag workflow` command imports the Phase 114
  substrate, and the substrate classification is built to fail when a
  phase wires it. The sandbox run did not include this gate.
  **Shared cause with #2:** the whole-tree gates a builder must run are a
  hand-kept list. CLAUDE.md names four, and the Opus prompt named 13. This
  gate walks `src/` by import graph and matched neither list. Two of this
  build's four fixes trace to that list being incomplete.
- **Fix:**
  - the three module entries are removed;
  - the six functions are listed as substrate orphans awaiting Phase 316
    (259 wired only list/show);
  - `test_the_known_scale` goes 37 → 34, with the reason in its waiver;
  - `COLLECTED_TEST_FLOOR` goes 9344 → 9346 (the gate's per-entry tests,
    +6 −3 −1).
- **Files:** `tests/support/integration_gaps_allowlist.py`,
  `tests/test_phase209B_integration_gaps.py`,
  `tests/test_phase255B_collected_test_floor.py`.
- **Verified:** the 13 whole-tree tests, this gate, 259's tests and the
  floor: 521 passed. The F9 and SSOT lints accept the updated waiver.

**Commit.** `bd19fa5`

### 2026-09-24 — Close-out

v1.1, Deviations and Results in the implementation doc; both phase
documents to `docs/phases/completed/`; ROADMAP row 259 ✅ with
**CLOSED 2026-09-24**; root `implementation.md` 0.13.80 → 0.13.81 with
the Phase History row; `COLLECTED_TEST_FLOOR` 9321 → 9344; the handoff
`docs/handoffs/2026-09-24_259_closed.md` in this close-out commit, before
any merge, per rule 4. `closeout_check` run: **A1–A4, A6, A7 pass; A5
(regression line) red by design** until the Opus session records the
regression of record.

### Pending (Opus session, outside the sandbox)

- Regression of record (full suite; expect **9,344 passed**,
  0 failed, 0 skipped — the floor is already raised; record the line
  with its commit hash and count so `closeout_check` A5 passes). Note:
  `test_phase209_packaging.py` runs clean outside the sandbox where no
  `PYTHONPATH` pins the source tree; its 7 sandbox failures are
  recorded above and reproduce at the base commit.
- Refute pass over the claims table in `259_implementation.md`
  (C1–C7): open each cited document at its page and check the claim;
  the negative C7's census is `census_leakdown.py` in the builder
  session tmp, regenerable in a minute.
- Merge `phase-259` to `master` (after 258's merge tonight), push,
  deploy; add the deploy's outcome to the handoff.
- Backup of the live database before the load: migration 067 runs
  against the live DB (`~/backups/motodiag/`, retain 5, print the
  before-state). It adds one template + seven items and updates one
  description; the corpus is untouched — but back up and record, per
  the rule.
- Findings: none filed by this phase; F149, F153–F157 remain open from
  earlier phases.

### 2026-09-24 22:21 — Opus session: review and refute

- **Operator decision (option 1).** 067's re-pointed description names
  no phases; it ends "For the full engine-side protocol see
  ppi_engine_v1." (`669a316`). The operator approved the alteration of
  that one live row.
- **Refute of C1–C7.** These are the claims table in the implementation
  doc. Each cited page was opened with `pypdf`.
  - **C1–C6 are confirmed** at the cited PDF pages, with the figures and
    quotes as written.
  - **Identity.** The Metropolitan manual's cover text reads "OWNER'S
    MANUAL 2025 METROPOLITAN / GIORNO". The CHF50 service manual's cover
    has no text layer; 353 rendered it as "CHF50/P/S METROPOLITAN
    2002–2006" (F152).
  - **C7: the conclusion is confirmed and the control is corrected.** The
    re-run removed the whitespace from each page's text, so letter-spaced
    OCR cannot hide a hit:
    - 260 files, 16 of them unparseable;
    - 0 describe a cylinder leak-down test. The only matches for the
      wider vocabulary are six battery "current leakage test" pages.

    The claims table states the control wrongly. The plain `compression`
    search finds 178 files and does **not** find C1's page, whose text
    layer spaces the word out. The whitespace-proof control finds 181
    files, C1's page among them. Item 5's "finds 178" stays as written,
    because it is true of the plain search it describes.
- **Operator census, F158.** Option 1 prompted it. It is filed on master
  (`632497a`) and not fixed here.
