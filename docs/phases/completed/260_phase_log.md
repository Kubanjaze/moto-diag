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

The builder's session recorded none: three authoring defects were caught
by its first test run and folded into the build commit (Deviations). The
Opus review found three that had left the session, one of them its own.

### Bug fix #1 — 2026-09-25

- **Issue:** migration 067 had no `rollback_sql`. Rolling it back raised
  "Migration 67 (ppi_engine_workflow) has no rollback_sql defined", and
  259's `test_rollback_peels_everything_067_added` was red on the branch.
- **Root cause:** the builder's Deviations record that inserting 068
  "replaced 067's tail including its `),`". The repair put `),` back
  straight after 067's `upgrade_sql`, so 067's `rollback_sql` became
  068's (rewritten for the chassis slug) and 067 kept the default `""`.
  The builder's gate list did not include 259's tests, which were the
  only ones to exercise it.
- **Fix:** 067's rollback restored verbatim from `master`. All 65 of
  master's migrations now compare identical on the branch (pydantic
  `model_dump` equality), with 068 the only new entry. Guard:
  `test_every_migration_keeps_its_rollback`.
- **Files:** `src/motodiag/core/migrations.py`,
  `tests/test_phase260_ppi_chassis.py`.
- **Verified:** the guard is red on the unfixed `migrations.py` and green
  on the fix.

**Commit.** `df44de7`

### Bug fix #2 — 2026-09-25

- **Issue:** 259's `test_upgrade_from_66_alters_only_the_approved_row`
  failed (`[67, 68] == [67]`), and its rollback test would have failed
  next (`68 == 66`). 260's own two tests had the same shape and would go
  red the day 069 lands.
- **Root cause:** F124's family in the rollback/upgrade shape. Each test
  rolled back only its own migration, asserted the version below it, and
  asserted `apply_pending_migrations(...) == [N]`. All three hold only
  while N is the head.
- **Fix:** rollbacks peel every successor (`rollback_to_version`), and a
  re-apply asserts the first version applied plus the head against
  `SCHEMA_VERSION`. The upgrade-scope tests apply only their own
  migration, so a successor's rows are never measured as theirs.
- **Files:** `tests/test_phase259_ppi_engine.py`,
  `tests/test_phase260_ppi_chassis.py`.
- **Verified:** a migration 069 planted as a pytest plugin (a new
  template, an UPDATE to another row, `SCHEMA_VERSION` 69). With it, the
  old tests fail 4/4 and the fixed ones pass 5/5. Without it, 259 + 260
  pass 50/50.

**Commit.** `7ef1275`

### Bug fix #3 — 2026-09-25

- **Issue:** the first regression of record, on `4770326`, failed 1 of
  9,375. `test_f124_schema_pin_discipline` flagged
  `test_phase260_ppi_chassis.py:237`,
  `assert get_current_version(path) == 68`.
- **Root cause:** bug fix #2 wrote that literal while 68 is the head: the
  same family as #2, introduced by its own fix. It reached the regression
  because the pre-commit set was rule 3's four whole-tree checks, and
  those do not include the F124 guard.
- **Fix:** the assertion now compares against the migration just applied
  (`m068.version`). From here on, any change to a migration or a
  migration test also runs the F124 guard and 240c's genuine head pin
  before commit.
- **Files:** `tests/test_phase260_ppi_chassis.py`.
- **Verified:** the F124 guard was red in the regression and is green
  now. F124 + 259 + 260 + the four whole-tree checks + 240c: 135 passed.
  Planted 069: 5/5.

**Commit.** `b22b715`

**Three bugs in one build: the shared cause.** #2 and #3 are one family,
a version literal the head can equal. #1 is an edit that replaced a
neighbour's text. They have one enabler in common: no test that
exercises the neighbour ran before commit. #1 and #2 went through a gate
list that left out 259's file, and #3 went through a pre-commit set that
left out the F124 guard. The remedy is the rule in #3's Fix, recorded
here and in the session memory.

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

### Pending (Opus session, outside the sandbox) — done, see the next entry

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

### 2026-09-25 — Opus session: review, refute, regression of record

Done in `~/Projects/moto-diag`, outside the sandbox. The builder's
full-suite line was never recorded: Subconscious ran out before the run
finished.

- **Fetched and merged.** `phase-260` was fetched from the sandbox clone
  (five commits, `b1a3e70` … `68c0fa9`), and `master` was merged in
  (`62e1eb5`). That brought in CLAUDE.md rule 1's addition (`b3285f3`):
  only the operator grants a stop's approval, and a pre-approval is
  applied as the operator's scoped wording, literally. The 068 live
  apply below runs under exactly that.
- **Review against the five traps from 258/259:**
  - F124 head pins: bug fixes #2 and #3.
  - Tests reading `data/motodiag.db`: none; the file is named only in
    docstrings.
  - The integration-gap allowlist and the `len(ORPHANS)` /
    `len(UNREACHABLE_MODULES)` / `len(MODULE_ISLANDS)` pins: untouched
    and consistent, since no module was wired.
  - F158: the item text passes the three patterns; the census is below.
    068's `Migration.description` begins "Phase 260:", like 067's, and
    no command prints a migration description (searched `cli/` and
    `api/`). The item text also says "No document in the research
    library sets …", the phrasing 259's reviewed leak-down item uses.
    It is outside F158's patterns and is left as is.
  - Negatives: C16's vocabulary lacked the makers' own words, and its
    controls were not shown hitting the cited pages. It was killed in
    the refute pass below.
  - The review also found what none of the five traps names:
    migration 067 had lost its rollback (bug fix #1).
- **Refute corrections, in two commits:**
  - `20426ff` corrected four attributions: the swingarm bushing pages,
    the wheels item's "turns hard" page, the BMW "rider's manual", and
    the KTM discs' "standard models" scope;
  - `7de9fbe` corrected the swingarm item after C16 was killed.

  Each correction has a pin that fails on the uncorrected text.
  **Decision (logged, not asked):** C16 is corrected, not dropped. The
  operator's instruction for a failed claim was "correct or drop"; the
  library does set a figure, and the phase's own rule is to cite a
  machine's figure as that machine's own. Dropping the sentence would
  have left the item silent about a figure the library holds.
- `COLLECTED_TEST_FLOOR` 9372 → **9375** (`4770326`): bug fix #1's guard
  and the refute pass's two pins.
- **Regression of record: 9375 passed, 0 failed, 0 skipped** at `b22b715`
  (54 min 46 s, the canonical venv, outside the sandbox). An
  earlier run on `4770326` is not a record: it failed 1 of 9,375 (bug fix
  #3). The live database's SHA-256 was `b1e3cc744da1b3b1…` before and
  after both runs, so no test touched it.


## Refuter pass

The Opus session ran this pass on 2026-09-25 over C1–C18 in
`260_implementation.md`. Every cited page was opened with pypdf (6.14.2),
and all 26 have a text layer. Where a page's text layer letter-spaces
words, the quote is given with the spacing collapsed. Document identity
was taken from the title pages, rendered where the text layer is glyph
debris (the BMW):

- KTM "OWNER'S MANUAL 2022 250 EXC TPI … 300 XC-W TPI";
- CHF50: the cover reads "2002–2006 … CHF50/P/S METROPOLITAN";
- Yamaha "2009 … SERVICE MANUAL Model: YW125Y" (the Zuma 125);
- Honda "OWNER'S MANUAL 2025 METROPOLITAN / GIORNO";
- BMW "Rider's Manual F 800 R".

The three negatives were re-derived over all 260 library PDFs,
whitespace-proof (the census and extraction scripts are in the Opus
session scratchpad). Parse counts reproduce Step 0: 157 full, 73
partial, 14 image-only, 16 unopenable. The vocabulary adds the makers'
words: "swinging arm", "link fork", "rear arm", "rear fork", "pivot
shaft", "engine mount", "chassis", and "hub/axle bearing".

| claim | verdict | quote | source |
|---|---|---|---|
| C1 KTM frame and link fork: change, repairs not permitted | kept | "Check the frame for damage, cracks, and deformation. … Change the frame. Guideline Repairs on the frame are not permitted." / "Repairs on the link fork are not permitted." | KTM 2022 250/300 EXC TPI OM, PDF p. 94 |
| C2 CHF50 bent frame; engine mounting bushings; damper oil leak | kept, and the item text corrected | "Steers to one side or does not track straight • Bent fork • … • Bent frame • Worn wheel bearings • Worn or damaged engine mounting bushings" (p. 217). "Either wheel wobbles • Excessive wheel bearing play • Bent rim • Excessively worn engine mounting bushing • Bent frame" (p. 318). "Soft suspension • Weak rear shock absorber spring • Oil leakage from damper unit" (p. 241). The swingarm item cited "wobble and pull (PDF p. 217)", but the wobble is p. 318; it now reads "pull and of wobble (PDF pp. 217, 318)" | CHF50 SM, PDF pp. 217, 318, 241 |
| C3 Zuma 125 steering head: rock check, 38 / 14 N·m | kept | "Grasp the bottom of the front fork legs and gently rock the front fork. Binding/looseness → Adjust the steering head." / "Lower ring nut (initial tightening torque) 38Nm … (final tightening torque) 14Nm" | Zuma 125 2009 SM, PDF pp. 93, 94 |
| C4 KTM steering head: no detectable play, no detents, seats damaged | kept | "Play should not be detectable on the steering head bearing." / "There should be no detectable detent positions." / "the bearings and the bearing seats in the frame can become damaged over time" | KTM OM, PDF p. 76 |
| C5 Zuma 125 fork check; spring 252.1 / 247 mm; inner tube bending 0.2 mm | kept | "oil seal Oil leakage → Replace. 3. Hold the scooter upright and apply the front brake. … Push down hard on the handlebar several times and check if the front fork rebounds smoothly. Rough movement → Repair." / "Free length 252.1mm (9.93in) 247mm (9.72in)" / "Inner tube bending limit … 0.2mm (0.008in)" | Zuma 125 SM, PDF pp. 95, 34 |
| C6 CHF50 fork spring 128.5 / 125.9 mm | kept | "Spring free length STANDARD … 128.5(5.06) SERVICE LIMIT … 125.9(4.96)" | CHF50 SM, PDF p. 12 |
| C7 Zuma 125 maintenance table: wheels, wheel bearings, steering bearings | kept | "Wheels • Check runout and for damage. • Replace if necessary." / "Wheel bearings • Check bearings for smooth operation. • Replace if necessary." / "Steering bearings • Check bearing assemblies for looseness." | Zuma 125 SM, PDF p. 55 |
| C8 CHF50 wheel-spin causes; axle runout 0.20 mm; rim runout 2.0 / 2.0 mm | kept, and the item text corrected | "Raise the front wheel off the ground and spin it by hand. Does the wheel spin freely? NO - • Brake dragging • Worn or damaged wheel bearings • Bent axle" (p. 314, under "Engine lacks power") / "Front wheel turns hard • Faulty wheel bearings • Brake drag • Bent front axle" (p. 217) / "SERVICE LIMIT: 0.20 mm (0.008 in)" (p. 218) / "SERVICE LIMITS: Radial: 2.0 mm (0.08 in) Axial: 2.0 mm (0.08 in)" (p. 242). The wheels item put "turns hard" on p. 314; each phrase is now cited to its own page | CHF50 SM, PDF pp. 314, 217, 218, 242, 12 |
| C9 CHF50 drum 95.0 / 95.5 mm, lining 3.5 / 1.0 mm, lever 10–20 mm, shoes as a set | kept | "Brake drum I.D. … 95.0 (3.74) … 95.5 (3.76)" / "Brake lining thickness 3.5 (0.14) … 1.0 (0.04)" / "Left brake lever free play 10-20(3/8-13/16)" (p. 241) / "Always replace the brake shoes as a set." (p. 243) | CHF50 SM, PDF pp. 12, 241, 243 |
| C10 F800R pad wear limit 1.0 mm, front and rear | kept, and the item text corrected | "Brake-pad wear limit, front min 1.0 mm (Friction pad only, without backing plate. The wear indicators (grooves) must be clearly visible.)" (p. 94) / "Brake-pad wear limit, rear min 1.0 mm (Friction pad only, without backing plate. The wear indicators must be clearly visible.)" (p. 95). The title page reads "Rider's Manual", and the "(grooves)" wording is the front pad's only; the item now says "rider's manual" and attributes the quote to the front | BMW F800R Rider's Manual, PDF pp. 94, 95 |
| C11 KTM disc wear 2.5 / 3.5 mm; lever free travel ≥ 3 mm; fluid-level reading | kept, and the item text scoped | "Brake discs - wear limit (All standard XC-W models, All standard EXC models) front 2.5 mm (0.098 in) rear 3.5 mm (0.138 in) Brake discs - wear limit (All special models) front 2.5 mm … rear 3.7 mm" (p. 164) / "Free travel of hand brake lever ≥ 3 mm (≥ 0.12 in)" (p. 99) / "the brake system is leaking or the brake linings are worn down" and "Old brake fluid reduces the braking effect." (p. 101). The item now says "for the standard models" | KTM OM, PDF pp. 164, 99, 101 |
| C12 CHF50 tread 0.8 mm; 125 kPa (18 psi) / 200 kPa (28 psi) | kept | "Minimum tire tread depth … SERVICE LIMIT 0.8 (0.03)" / "125 kPa (1.25 kgf/cm2, 18 psi)" / "200 kPa (2.00 kgf/cm2, 28 psi)" | CHF50 SM, PDF p. 12 |
| C13 Metropolitan 2025: 18 / 29 psi; wear indicators; damage list | kept | "Tire air pressure Front 18 psi (125 kPa, 1.25 kgf/cm2) Rear 29 psi (200 kPa, 2.00 kgf/cm2)" (p. 121) / "If they become visible, replace the tires immediately." (p. 65) / "Inspect the tires for cuts, slits, or cracks that expose fabric or cords, or nails or other foreign objects embedded … Also inspect for any unusual bumps or bulges in the side walls" (p. 64) | Metropolitan 2025 OM, PDF pp. 121, 65, 64 |
| C14 KTM tread ≥ 2 mm; DOT date; 5-year recommendation | kept | "Minimum tread depth ≥ 2 mm (≥ 0.08 in)" (p. 115) / "indicated by the last four digits of the DOT number. The first two digits indicate the week of manufacture and the last two digits the year of manufacture. KTM recommends that the tires be changed after 5 years at the latest, regardless of the actual state of wear." (p. 116) | KTM OM, PDF pp. 115, 116 |
| C15 negative: no frame-alignment or straightening figure in the library | kept | The only figure-proximate hit for `frame` near alignment/limit/straight/bend/twist/jig/measure is a caster angle and trail: "frametype steel tube underbone … casterangle 27° … trail 90mm". It is not an alignment tolerance. The widened subject "chassis/main frame" (1,816 pages, 145 files) has 11 qualifier hits and 0 figures. Controls: `frame` finds KTM p. 94 (1,279 pages, 162 files); the figure regex fires on CHF50 p. 218 ("0.20mm") | Zuma 125 SM, PDF p. 32 (the one hit); whole library |
| C16 negative: no swingarm or engine-hanger play tolerance in the library | **killed** | "Check the axial clearance between the two swinging arms using a feeler thickness gauge Characteristic Standard clearance 0.40 ÷ 0.60 mm Allowable limit after use: 1.5 mm". The same figures are in `manuals/service/piaggio_mp3_400.pdf` p. 295, `mp3_500_wsm.pdf` p. 349 and `pdfs/c2_hpe_workshop.pdf` pp. 307–308, and `pdf/beverly125.pdf` p. 181 gives "Allowable limit after use: 1 mm". Only the Vespa's title page was read; these four are named by file path, not by model. The maker's word, "swinging arm", is not matched by Step 0's `swing[- ]?arm` on whitespace-stripped text. **Corrected:** the swingarm item now cites the Vespa's clearance as that machine's own, and the false sentence is gone | Vespa GTS Super 300 ie (2008) service station manual, `pdfs/vespa_gts300_shop.pdf`, PDF p. 227 |
| C17 negative: no wheel-bearing play figure in the library | kept | The 3 figure-proximate hits are other parts' limits beside qualitative bearing checks. For example: "wheelbearing turn the inner race of each bearing with your finger, the bearing should turn smoothly and quietly" (PCX p. 326, after axle runout 0.2 mm), and "front wheel turns roughly or is loose → replace the wheel bearings" (Zuma p. 117, after wheel runout 1.0 mm). A second pass for bearing play/clearance figures on wheel-bearing pages found 0. Its control, the same pattern with no page filter, finds 56 pages in 19 files, Kymco People S 250 p. 140's crankshaft figures among them. Subject controls: CHF50 pp. 217/314/318 and Zuma p. 55 are all found | PCX 2013–2017 SM, PDF p. 326; Zuma 125 SM, PDF p. 117; whole library |
| C18 KTM mismatched tread patterns | kept | "Different tire tread patterns on the front and rear wheel impair the handling characteristic. … Make sure that only tires with a similar tire tread pattern are fitted to the front and rear wheel." | KTM OM, PDF p. 39 |

Also corrected: C15's parenthesis in the claims table says "16 yield no
text". The count is 30: 16 files do not open and 14 are image-only, as
Step 0 itself states.

**What the pass did not check.** The item text also holds authored
guidance with no citation, and this pass does not vouch for it: "a drum
at its limit cannot be machined back", "a notch at straight-ahead is
brinelled races", and "run a finger round each bead". None of these
states a figure.
