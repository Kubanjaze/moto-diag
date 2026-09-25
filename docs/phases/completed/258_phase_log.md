# Phase 258 — Gate 14 (scooter / small displacement integration) — phase log

**Status:** ✅ Complete (2026-09-24)
**Branch:** `phase-258` (GLM builder session, sandboxed)

---

### 2026-09-24 — Opened as the operator's Subconscious run

Taken from `docs/handoffs/2026-09-24_353_closed.md`: Gate 14 queries a
scooter/small bike and must reach the CVT (254), scooter-electrical (354)
and small-engine-carb (353) workflows. Read before acting: the handoff,
ROADMAP rows 251–258, 353, 354 and their phase docs, `ROADMAP_AUTHORITY.md`
(258 is backend, 205+), FOLLOWUPS F132, F142, F149, F150, F151, F152, and
Gate 13's `250_implementation.md` as the house pattern.

Branch `phase-258` from `master` at `c1b3ed7`, in sync with origin.
`roadmap_check.py` exit 0. ROADMAP row 258 🔲 → 🚧 at `0de3c54` **before
Step 0**, per CLAUDE.md.

**This is the operator's Subconscious run (standing rule 2).** Five
differences from a builder session, given by the operator: write only to
this clone and the session tmp; `data/motodiag.db` (1,060 rows) stands in
for the live database, and any live step against it is a dry run; commits
stay on `phase-258` in this clone for an Opus session to fetch; the finish
line is "ready to merge" (Step 0, v1.0, build, tests, the four whole-tree
checks, close-out documents — no merge, no full regression); refute runs
on Opus, so every document-sourced claim is listed with its citation for
that pass.

**Sandbox measurements, logged per the operator's instruction:** the
sandbox refuses heredoc temp files (`can't create temp file for here
document: operation not permitted`) and `/tmp` writes (`Operation not
permitted`). Working as intended, not worked around: commit messages and
Step 0 scripts go through files in the session tmp via the Write tool.
This is the message-file form of the working rule (commit messages through
a quoted heredoc — a message file cannot execute a backtick either), and
the same form the 353 handoff records for merge messages.

### 2026-09-24 — Step 0: greenfield-shaped gate, no fork

Measurements S0-1..S0-11 are in `258_step0.md`; the scripts live in the
builder session tmp (regenerable; the load-bearing figures are re-derived
by the gate's tests). In short: **the path carries the track's content** —
all three layers reach the 12-row prompt for the machines that cover all
three, composition (250B) visibly answering the symptom, the axis (255)
withholding scoped CVT rows from the Grom, and the chokepoint (256) at
every door. Two exceptions carry the gate's findings: the SYM overlap
machines reach CVT content only at tier 2 — the CVT rows pair SYM under
`Jet 50`/`Joyride`/`Symply 125` while 353/354 pair the same machines under
`Jet Euro 50`/`Joyride 125`/`Fiddle 50` — and the Fiddle 50 resolves
transmission `unknown` (the lookup has no "fiddle 50" spelling) so the 8
scoped CVT rows are withheld from it entirely.

**Decision (logged, not asked): no fork.** Gate 13's pattern decides every
question: zero production code, gaps pinned as executable documentation
and filed as findings (F153–F157), repairs left to their own rows. The
finish line is the operator's "ready to merge"; merge, deploy, regression
of record and refute are marked pending for Opus and are not attempted
here. v1.0 committed before any test code was written.

### 2026-09-24 — Build: the gate file, 125 tests, zero production code

Committed at `f08640a` (with the corrections below folded in), then
close-out. `tests/test_phase258_gate14.py`: nine classes, 125 tests —
every scooter make answers through the real CLI root; the three layers
reachable by the vocabulary their phases pinned (254's `weight roller`,
not `roller weight`); the diagnostic path walked through real
`diagnose quick` with the AI call replaced, its 12-row census pinned per
machine for all sixteen; the SYM exception and the Fiddle 50's unknown
resolution pinned to fail when F153/F154 close; the handoff's predicted
gaps stated rather than found; cross-surface agreement; the honest gaps;
Track M's invariants re-run against the seed; Gate 13 re-run as a
subprocess and `SCHEMA_VERSION` pinned at 66.

Findings F153–F157 filed at `608d783` after Step 0, per the finding
skill (next number from both files: `next_f_number.sh` → F153).

**Mutations 11/11**, each applied, caught, reverted, tree verified clean:
an SYM junction pair added to a CVT row; `fiddle 50` added to
`TRANSMISSION_LOOKUP`; a Kymco compat row; a `kymco.json` DTC file;
F149's reg/rec row scoped to Shadow; Kymco added to a cross-platform
carburettor row's make; the Ruckus carburettor window opened to 2008;
Metropolitan added to the CHF50 carburettor row's models; plural stemming
in `relevance_tokens`; the transmission scope removed from the
roller-wear row; the prompt cap raised 12 → 16. The first harness run
also taught the harness its own lesson: its revert step parsed
`git status` and would have checked out real work alongside the mutation
— the error that stopped it is why the harness now reverts only the
mutation's known paths, and why the build was committed before any
mutation ran.

**The four whole-tree checks** on the close-out tree: 191C F9 lint +
244G guard shapes + roadmap continuity **58 passed**;
`finding_check.py` exit 0 — both variants, including
`phase_docs="docs/phases/in_progress"`.

`COLLECTED_TEST_FLOOR` raised 9188 → **9321** with the close-out commit
(collected count, gate file present; raised before the regression of
record, the floor's own rule).

**Decision (logged, not asked): the row closes ✅ with the close-out
commit.** CLAUDE.md's own order puts the handoff in the close-out commit
"before the merge" — 353 and 354 closed this way on this date. The
merge, the regression of record, the refute pass and the deploy remain
pending below, and the handoff says so.

### Bug fix #1 — 2026-09-24

- **Issue:** `TestEveryScooterMakeAnswersThroughTheCli::…make_s_own_electrical_and_carburettor_rows_list[Genuine]`
  failed: 353 and 354 wrote no Genuine row.
- **Root cause:** the test asserted a per-make universal over makes the
  two content phases never read manuals for. Genuine is Track M's Damon
  shape — a make the cross-make phases cover.
- **Fix:** the assertion narrowed to the four makes with their own rows,
  and a new test records the honest gap: Genuine's answer is 253's rows
  and the multi-make CVT rows, nothing of its own.
- **Files:** `tests/test_phase258_gate14.py`.
- **Verified:** the new test green; mutations 11/11.

**Commit.** `f08640a`

### Bug fix #2 — 2026-09-24

- **Issue:** `TestTheSymException::…fiddles_prompt_holds_only_the_two_unscoped_cvt_rows`
  failed on the naming row's title.
- **Root cause:** F9, again: the title was recalled from the Step 0
  printout ("returns the wrong part") instead of copied from the seed
  ("returns the other two").
- **Fix:** titles copied from the files; three assertions corrected.
- **Files:** `tests/test_phase258_gate14.py`.
- **Verified:** the three corrected tests green; mutations 11/11.

**Commit.** `f08640a`

### Bug fix #3 — 2026-09-24

- **Issue:** `TestTheSymException::…tier0_pair_counts` failed:
  `(Honda, PCX150): 0 pairs, pinned 12`.
- **Root cause:** the junction's canonical spelling is `PCX 150` (with a
  space) — the machine's own rows print "Honda PCX150", and 255C's
  canonicalisation differs. The pin used the model column's spelling, not
  the junction's.
- **Fix:** the pin keyed on the junction spelling, which is what tier 0
  matches. **This is the third bug of the build, so the build stopped and
  found the shared cause** (below, after #4).
- **Files:** `tests/test_phase258_gate14.py`.
- **Verified:** the pin green; the machine's prompt census unchanged
  (the garage query `PCX150` still resolves and reaches the pinned rows).

**Commit.** `f08640a`

### Bug fix #4 — 2026-09-24

- **Issue:** two Step 0 claims were false as written: "no scooter row
  carries a DTC code" (252's GROM125 row carries eleven Honda blink
  codes) and "No compat entries known" for every scooter machine
  (measured against a database whose adapter catalogue was never
  seeded).
- **Root cause:** the shared cause of #1–#4, measured not assumed:
  **Step 0 wrote universals and negatives from ad-hoc queries that had no
  positive control** — a `dtc_codes != ''` filter that passes `'[]'`, a
  harness DB built without `seed_all`, a make list asserted over makes
  never read, titles recalled rather than copied. The first `pytest` run
  was the control those claims never had. That is the F9 family
  (assumption vs reality) wearing the "negative claims need a positive
  control" rule's own clothes.
- **Fix:** everything the failures touched was re-measured before any fix
  was written: the catalogue seeded and the compat answers re-taken
  (Honda scooters inherit the make-level dev/test mock — F157 restated
  with the corrected measurement), the blink-code row found and given its
  positive control (`kb by-code 9-1` reaches it), the negatives narrowed
  to what is true (no SAE OBD code on any Track M row). `258_step0.md`
  S0-9 corrected in the same commit.
- **Files:** `tests/test_phase258_gate14.py`,
  `docs/phases/in_progress/258_step0.md`, `docs/FOLLOWUPS.md`.
- **Verified:** the re-measured tests green; `finding_check` exit 0 after
  the F157 restatement; mutations 11/11.

**Commit.** `f08640a`

### Bug fix #5 — 2026-09-24

- **Issue:** the regression of record on `b10f6f9` failed at 0%. F124's
  guard (`test_no_test_pins_the_head_with_a_literal`) named
  `test_phase258_gate14.py:898`, which asserted `SCHEMA_VERSION == 66`.
- **Root cause:** a head pin by a literal, the kind F124 retired in favour
  of the one canonical pin (`test_phase240c_severity_ordering.py`) and
  floor pins. The sandbox run checked the four whole-tree tests that
  CLAUDE.md's rule 3 lists. F124's guard is a fifth that the list does not
  name, so the first run to meet it was the full regression. Found by the
  Opus session, outside the sandbox.
- **Fix:** the assertion is a floor, `SCHEMA_VERSION >= 66`. The test is
  renamed `test_the_schema_is_at_least_the_one_the_gate_ran_on`, and its
  docstring says what it asserts and why. The gate still collects 125
  tests, so the floor stays 9321.
- **Files:** `tests/test_phase258_gate14.py`.
- **Verified:** F124's guard, the floor test, the F9 lint and 244G: 48
  passed. All 13 tests that scan the whole tree, run on the tree before the
  fix: 1 failed (this one), 338 passed. This was the only whole-tree miss.

**Commit.** `0533038`

### 2026-09-24 — Close-out

v1.1, Deviations and Results in the implementation doc; both phase
documents to `docs/phases/completed/`; ROADMAP row 258 ✅ with
**CLOSED 2026-09-24**; root `implementation.md` 0.13.79 → 0.13.80 with
the Phase History row; `COLLECTED_TEST_FLOOR` 9188 → 9321; the handoff
`docs/handoffs/2026-09-24_258_closed.md` in this close-out commit, before
any merge, per rule 4. `closeout_check` run: **A1–A4, A6, A7 pass; A5
(regression line) red by design** until the Opus session records the
regression of record.

### Pending (Opus session, outside the sandbox)

- Regression of record (full suite; expect 9321 passed; record the line
  with its commit hash and count so `closeout_check` A5 passes).
- Refute pass over the gate's pinned truths: (a) each pin matches the
  seed, (b) each honest-gap test fails when filled — the 11-mutation list
  in the implementation doc is the script, (c) the S0 measurements
  reproduce on a fresh seed. The gate states no new document claims; the
  corpus rows it walks carry citations in the 251–254/353/354 phase docs.
- Merge `phase-258` to `master`, push, deploy; add the deploy's outcome
  to the handoff.
- Backup of the live database before any load (none is expected — this
  gate writes no content; confirm and record).
- Refile or close findings as decided: F153–F157 are all open.
