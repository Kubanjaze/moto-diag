# Phase 260 — Pre-purchase inspection — chassis

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-25

**Branch:** `phase-260` (GLM builder session in the sandbox clone; finish
line "ready to merge" — the regression of record, the refute pass, the
merge and the deploy are the Opus session's).

## Goal

Give the shop a pre-purchase **chassis** inspection protocol as persistent
workflow content on the Phase 114 substrate — one template,
`ppi_chassis_v1`, covering the seven subjects the ROADMAP row names
(frame straightness, accident history, fork seals, steering head bearings,
swingarm, wheel bearings, brake/tire condition). The front door already
exists (`motodiag workflow list/show`, built in 259), so this phase adds
content and **no new module** — the existing command renders the new
template the moment the migration seeds it. Every figure in the item text
cites the document it came from (S0-3); where no document sets a figure
(frame alignment, swingarm play, wheel-bearing play — three negatives,
each measured with a whitespace-proof census and a positive control) the
item says where the figure belongs and no number is invented.

The migration also re-points `ppi_engine_v1`'s description — which today
ends "the chassis protocol is Phase 260" — at the new template by name.
That phrase is the F158 review miss recorded in the 2026-09-25 re-measure;
the handoff leaves it "for 260", and the F158 rule forbids build
references in text users see. The change is the same one-row shape the
operator approved for `generic_ppi_v1` in 259's review; the dry run
records its exact effect for the Opus session's live load, and the
rollback restores the old text verbatim.

CLI: none new — `motodiag workflow list`, `motodiag workflow show
ppi_chassis_v1` (259's commands, this phase's content).

Outputs: migration 068 (`src/motodiag/core/migrations.py`, schema 67 →
68), `SCHEMA_VERSION` 67 → 68 in `src/motodiag/core/database.py`,
`tests/test_phase260_ppi_chassis.py`

## Logic

1. **Migration 068 — `ppi_chassis_workflow`.** One `INSERT OR IGNORE` for
   the template (slug `ppi_chassis_v1`, category `ppi`,
   `applicable_powertrains = ["ice","electric","hybrid"]` — **all three**,
   S0-4: chassis subjects are powertrain-agnostic, an electric machine has
   a frame, forks, bearings, brakes and tires — `estimated_duration_minutes`
   80, tier `individual`, system user 1). Seven `INSERT`s for the checklist
   items (`sequence_number` 1–7, keyed on the slug sub-select, inside the
   one-shot migration journal — S0-2). One `UPDATE` replacing
   `ppi_engine_v1`'s description with the same text re-pointed: "…for the
   full chassis-side protocol see ppi_chassis_v1." `rollback_sql` peels
   exactly what 068 added: the new items cascade with the template, the
   template goes, and `ppi_engine_v1`'s description is restored verbatim
   to the text migration 067 seeded.
2. **No CLI, no repo, no API change.** `list_templates`,
   `get_template_by_slug` and `get_checklist_items` render the new
   template through the group 259 registered. The substrate's
   allowlist/classification state does not move (no module is wired or
   unwired by this phase).
3. **Data flow.** migration journal (existing DBs) / `db init` (new DBs) →
   `workflow_templates` + `checklist_items` → the existing accessors →
   the existing click commands → terminal. Nothing computes; this is
   content plus the tests that pin it.

## Key Concepts

- **Content on a door that already opens** (S0-1): 259 built the front
  door because the substrate had none; 260's marginal cost is the content
  migration alone. The wiring rule is satisfied by the migration's rows
  travelling through the door 259 registered — the tests drive `motodiag
  workflow show ppi_chassis_v1` through the real registered group.
- **Provenance on screen** (244V's rule, 259's practice): every figure an
  item states is a cited machine's own, with the document and PDF page in
  the item's own text — worked examples from the Zuma 125 2009 service
  manual, the Honda CHF50 service manual, the Metropolitan 2025 owner's
  manual, the KTM 250/300 EXC TPI owner's manual and the BMW F800R
  owner's manual.
- **Negatives measured, then honoured** (S0-3): no document in the
  library sets a frame-alignment figure, a swingarm/engine-hanger play
  tolerance, or a wheel-bearing play figure. Those three places in the
  content say where the figure belongs instead — the machine's own
  service manual — and the tests pin that the frame and swingarm items
  carry no measurement figure at all.
- **F158 by construction**: the new template's description and every
  item's text name documents and templates by name only — no phase
  numbers, track letters, finding numbers or "this phase". The tests pin
  this for every surface this phase touches, including the re-pointed
  `ppi_engine_v1` description. The known offender
  `generic_winterization_v1` ("Track N phase 264 expands") is F158's,
  not this phase's to fix silently.
- **The floor-pin pattern** (F124): schema assertions use
  `SCHEMA_VERSION >= 68` or literals below the head; the genuine head pin
  stays in `tests/test_phase240c_severity_ordering.py`.

## Decisions

- **D1 — new template `ppi_chassis_v1`, not an edit of `generic_ppi_v1`
  or `ppi_engine_v1`.** The generic stays the 5-item quick check; the
  engine protocol stays engine-side; chassis is the third protocol of the
  set. Editing seeded items in place collides with the item-identity
  problem (S0-2/F129), and the generic's stub items are another phase's
  content.
- **D2 — powertrains all three** (S0-4), by contrast with 259's
  `["ice","hybrid"]`: every chassis subject exists on an electric machine.
  The items' wording never presumes an engine.
- **D3 — migration 068 also re-points `ppi_engine_v1`'s description**
  (the F158 review miss). Logged as a decision rather than asked because
  the 259 handoff names this phrase as 260's ("It is not fixed here, by
  the operator's instruction for 259"), the F158 rule in this session's
  brief forbids exactly it, and the shape is the one the operator
  approved in 259's review (option 1, `669a316`). The migration runs as a
  dry run in this session; the live one-row alteration is the Opus
  session's after the backup, and the handoff states it plainly so the
  operator can strike it from the deploy if they disagree.
- **D4 — seven items**, mapping one-to-one to the row's seven subjects:
  frame straightness + accident history (1, the row's two history-flavoured
  subjects belong to one walk-around), steering head bearings (2), front
  fork seals (3), swingarm (4), wheel bearings (5), brakes (6), tires (7).
  All required — chassis has no "when in doubt" item the way the engine
  protocol's leak-down is conditional.
- **D5 — no CLI or schema surface beyond the content migration.** The
  API stays out of scope, as in 259; the front door exists.

## Non-goals

- No engine, winterization, tire-service (261) or crash-claim (262)
  content beyond the row's subjects.
- No new tables, repo functions, CLI commands, API routes, or models.
- No migration of the live database in this session: migration 068 runs
  as a dry run against a copy of the snapshot; the real load, after a
  backup, is the Opus session's.
- No repair of the 25 pre-existing F158 offenders, including
  `generic_winterization_v1`'s "Track N phase 264 expands" — that is the
  filed repair phase's work.
- No fixing of `generic_ppi_v1`'s uncited starter figures (S0-5 note);
  recorded for a finding, not edited — the rows are another phase's
  content and their identity is prose (F129).
- Mobile: untouched.

## Claims for the Opus refute pass

Every fact below is taken from a document in `~/research/motodiag`
(cited by library-relative path and PDF page, the F152 convention) and
appears in the seeded item text. The refute pass opens each document at
the page and checks the claim against it.

| # | claim as it appears in the content | document | PDF page |
|---|---|---|---|
| C1 | KTM's owner's manual directs: "Check the frame for damage, cracks, and deformation. » If the frame shows signs of damage, cracks, or deformation: — Change the frame. Guideline: Repairs on the frame are not permitted." The same page checks the "link fork" (the rear arm) with the same rule | `acquired/KTM/22_3214421_en_OM.pdf` (2022 250/300 EXC TPI owner's manual) | 94 (printed 92) |
| C2 | The CHF50 service manual lists a bent frame as a cause of "steers to one side or does not track straight" and "front wheel wobbles"-adjacent handling faults; "worn or damaged engine mounting bushings" as another cause; and, in the rear-wheel chapter, "oil leakage from damper unit" as a cause of soft suspension | `honda/chf50_service_mirror.pdf` | 217 (13-5), 241 (14-3), 318 (21-7) |
| C3 | Zuma 125 service manual, checking the steering head: elevate the front wheel, "Grasp the bottom of the front fork legs and gently rock the front fork. Binding/looseness → Adjust the steering head"; the lower ring nut's initial tightening torque 38 N·m, final tightening torque 14 N·m; "Check the steering head for looseness or binding by turning the front fork all the way in both directions." | `pdf/yamaha_zuma125_2009_sm.pdf` | 93, 94 (printed 3-40, 3-41) |
| C4 | KTM owner's manual, checking steering head bearing play: move the fork legs to and fro in the direction of travel — "Play should not be detectable on the steering head bearing"; over the entire steering range "no detectable detent positions"; running with play, "the bearings and the bearing seats in the frame can become damaged over time" | `acquired/KTM/22_3214421_en_OM.pdf` | 76 (printed 74) |
| C5 | Zuma 125 service manual, checking the front fork: inner tube "Damage/scratches → Replace"; oil seal "Oil leakage → Replace"; "Hold the scooter upright and apply the front brake… Push down hard on the handlebar several times and check if the front fork rebounds smoothly. Rough movement → Repair." Its chassis specifications give fork spring free length 252.1 mm standard / 247 mm limit, and inner-tube bending limit 0.2 mm (0.008 in) | `pdf/yamaha_zuma125_2009_sm.pdf` | 95 (3-42), 34 (2-14) |
| C6 | CHF50 service manual, front fork spring free length standard 128.5 mm, service limit 125.9 mm | `honda/chf50_service_mirror.pdf` | 12 |
| C7 | Zuma 125 service manual maintenance table: wheels — "Check runout and for damage. Replace if necessary."; wheel bearings — "Check bearings for smooth operation. Replace if necessary."; steering bearings — "Check bearing assemblies for looseness." | `pdf/yamaha_zuma125_2009_sm.pdf` | 55 (printed 3-2) |
| C8 | CHF50 service manual: raise the front wheel and spin it by hand; the hard-to-turn causes are "Brake dragging / Worn or damaged wheel bearings / Bent axle"; axle runout SERVICE LIMIT 0.20 mm (0.008 in); wheel rim runout SERVICE LIMITS radial 2.0 mm, axial 2.0 mm | `honda/chf50_service_mirror.pdf` | 314, 218 (13-6), 12, 242 (14-4) |
| C9 | CHF50 service manual: front and rear brake drum I.D. standard 95.0 mm, service limit 95.5 mm; lining thickness standard 3.5 mm, service limit 1.0 mm; lever free play 10–20 mm; "Always replace the brake shoes as a set" | `honda/chf50_service_mirror.pdf` | 12, 241 (14-3), 243 (14-5) |
| C10 | BMW F800R owner's manual: brake-pad wear limit front and rear "min 1.0 mm (Friction pad only, without backing plate. The wear indicators (grooves) must be clearly visible.)" | `acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf` | 94, 95 |
| C11 | KTM owner's manual: brake discs — wear limit front 2.5 mm (0.098 in), rear 3.5 mm (0.138 in) (standard XC-W/EXC models); hand brake lever free travel ≥ 3 mm; a brake-fluid level that drops below the marking means "the brake system is leaking or the brake linings are worn down", and "old brake fluid reduces the braking effect" | `acquired/KTM/22_3214421_en_OM.pdf` | 164 (printed 162), 99 (printed 97), 101 (printed 99) |
| C12 | CHF50 service manual: minimum tire tread depth service limit 0.8 mm, cold tire pressures 125 kPa (18 psi) front, 200 kPa (28 psi) rear | `honda/chf50_service_mirror.pdf` | 12 |
| C13 | Metropolitan 2025 owner's manual: tire air pressure front 18 psi (125 kPa), rear 29 psi (200 kPa); tread wear indicators — "If they become visible, replace the tires immediately"; inspect for cuts, slits or cracks that expose fabric or cords, embedded objects, and sidewall bumps or bulges | `honda/metro_2025_31GJB680.pdf` | 121 (printed 117), 65 (printed 61), 64 (printed 60) |
| C14 | KTM owner's manual: minimum tread depth ≥ 2 mm (≥ 0.08 in); "The tire date of manufacture is usually contained in the tire label and is indicated by the last four digits of the DOT number. The first two digits indicate the week of manufacture and the last two digits the year of manufacture. KTM recommends that the tires be changed after 5 years at the latest, regardless of the actual state of wear. » If the tires are more than 5 years old: — Change the tires." | `acquired/KTM/22_3214421_en_OM.pdf` | 115, 116 (printed 113, 114) |
| C15 | **Negative:** no document in the library sets a frame-alignment or straightening figure. Vocabulary `frame` within 30 chars of alignment/tolerance/limit/straighten/gauge (and the reverse), whitespace-proof, scope every `*.pdf` under `~/research/motodiag` minus the venvs (260 files; 16 yield no text — F127's debris and the image-only documents); 13 hits in 7 files, all installation prose or parts-diagram labels, zero figures. Control: `frame` alone finds 1,279 pages in 162 files including C1's page; the figure-regex catches real limit tables where they exist (SYM 7429958 p. 61). `census_negatives.py` in the session tmp | whole library | — |
| C16 | **Negative:** no document in the library sets a swingarm or engine-hanger play tolerance. Vocabulary `swing[- ]?arm`/`engine hanger`/`pivot` within 40 chars of limit/tolerance/play: 6 hits in 3 files, all BMW top-case lid prose ("pivot lever at top limit position"), zero figures. Control: the subject vocabulary finds 448 pages in 78 files | whole library | — |
| C17 | **Negative:** no document in the library sets a wheel-bearing play figure. Vocabulary `wheel bearing` within 40 chars of limit/tolerance/clearance/play, and `bearing…clearance/play…digit`: 29 hits in 16 files, all checklist lines ("check the wheel bearing for play"); the only play figures the search found anywhere are a *crankshaft* bearing's (`pdf/kymco_people_s250_sm.pdf` p. 140, axial 0.20 / radial 0.05 mm) — proof the regex catches figures, none for a wheel. Control: `wheel bearing` finds 340 pages in 95 files | whole library | — |
| C18 | KTM owner's manual: "Different tire tread patterns on the front and rear wheel impair the handling characteristic. Different tire tread patterns can make the vehicle significantly more difficult to control. — Make sure that only tires with a similar tire tread pattern are fitted to the front and rear wheel." | `acquired/KTM/22_3214421_en_OM.pdf` | 39 (printed 37) |

Measurements of this repo the refute pass reproduces (not document
claims): the snapshot stands at schema 67 with 1,060 `known_issues`, 3
templates, 16 items, and `ppi_engine_v1`'s description carrying "the
chassis protocol is Phase 260"; migration 068 raises a fresh `db init`
database to 68 with `ppi_chassis_v1` + 7 items and re-points exactly one
existing row; `motodiag workflow show ppi_chassis_v1` renders every item
through the real registered group.

## Verification Checklist

- [x] Migration 068 applies on a fresh `db init` database;
      `SCHEMA_VERSION >= 68`
- [x] 068's rollback peels it: no `ppi_chassis_v1`, items gone via
      cascade, `ppi_engine_v1`'s description restored verbatim; the
      schema back at 67
- [x] The upgrade-from-67 test builds its own 67 baseline (never
      touching `data/motodiag.db`) and asserts exactly one existing row
      is altered, naming no phase
- [x] Template: category `ppi`, powertrains exactly
      `["ice","electric","hybrid"]`, active, tier `individual`; offered
      under `list_templates(powertrain="electric")` — the deliberate
      difference from 259's engine protocol
- [x] Seven items, `sequence_number` 1–7 contiguous, every item has
      instruction / expected pass / expected fail, all required
- [x] Figures pinned per field: C3/C4 in the steering item, C5/C6 in the
      fork item, C7/C8 in the wheels item, C9/C10/C11 in the brakes item,
      C12/C13/C14/C18 in the tires item — each needle demanded in each
      field that states it (259's bug fix #1 lesson)
- [x] The frame and swingarm items carry no measurement figure (regex for
      mm/%/N·m numbers must miss) and name where the figure belongs
- [x] F158 pin: the new template's description, its items, and the
      re-pointed `ppi_engine_v1` description contain no `Phase N`,
      `Track X`, finding number or "this phase"; the pattern is seen to
      catch a planted "Phase 999"
- [x] `motodiag workflow list` shows all four templates;
      `workflow show ppi_chassis_v1` prints all seven item titles and
      the description with its citations
- [x] Known-bad controls planted, seen red, reverted (four; phase log)
- [x] The whole-tree gates pass (521 across 191C/244G/244U/244V/244T/
      244J/244Y/256/209B/114/F124/240c/191D/roadmap continuity) and
      `finding_check` exit 0 in both variants; the FULL suite green
      except the expected environmental file (the phase log's line)
- [x] The dry run on a copy of the snapshot recorded in the phase log
      (one template + seven items + one description UPDATE; the
      `known_issues` content hash unchanged)

## Deviations from Plan

- **The regression of record, the refute pass, the merge, the deploy and
  the live load did not run** — the operator's standing arrangement for
  this Subconscious session: everything to "ready to merge" commits on
  `phase-260` in this clone; the rest is the Opus session's and is
  pending in the phase log. `closeout_check` A5 is red by design until
  the regression line lands.
- **The claims table grew one row between v1.0 and the build**: the
  tires item cites the KTM manual's mismatched-pattern warning (PDF
  p. 39), which v1.0's C1–C17 did not name. Added as C18 in this v1.1
  so the refute table matches the content that shipped.
- **Three authoring defects were caught by the first test run and folded
  into the build commit, never committed broken** (the 259 precedent
  for first-run catches): the insertion dropped migration 067's closing
  parenthesis (a SyntaxError at collection — the Edit replaced 067's
  tail including its `),`); the fork pin over-demanded its needle,
  asking the instruction to cite PDF p. 34 where the figures it covers
  live in the description and diagnosis; and the CLI pins asserted
  spaced phrases ("for the full chassis-side protocol see
  ppi_chassis_v1") that rich wraps at the 80-column test terminal —
  the needles are now single tokens where the screen is asserted, and
  the DB-level pins carry the exact text.
- **One transient collection error** in the first `--collect-only`
  measurement (9,372 collected, 1 error) that a re-run immediately did
  not reproduce (9,372 collected, clean, twice); the suite was running
  concurrently in the background at the time. The floor was raised on
  the clean count.
- **The ROADMAP row's 🚧 flip is an external commit** (`b1a3e70`,
  00:59:21): this session created the branch and then — before its own
  first commit — someone on the operator's side committed the row
  change onto it, the ledger step this session should have made first.
  It is the correct change in the correct place (`roadmap_check.py` ok),
  so it stays; recorded here and in the phase log because standing rule
  5 says a second session on this checkout only reads, and the operator
  should know a writer touched the branch.
- **A finding was filed rather than an edit made** (F159): the
  substrate's own starter item carries uncited figures. v1.0 planned the
  finding ("recorded for a finding, not edited"); F159 is it.
- **No bug-fix register**: nothing that left this session needed a fix
  in its own commit — the authoring defects above were caught before
  the build commit, the four known-bad controls were probes by design,
  and the full suite's only red file is the expected environmental
  one. A phase with no bug fixes writes no register (the close-out
  skill's skip rule); the reason is stated here.

## Results

| Metric | Value |
|--------|-------|
| Template added | 1 (`ppi_chassis_v1`, 7 items, the row's 7 subjects) |
| Migration | 068, schema 67 → 68; rollback peels it round-trip |
| Production code | `migrations.py` (+123 lines, all migration 068) + 1 line in `database.py` |
| Tests added | 26 (`tests/test_phase260_ppi_chassis.py`) |
| Known-bad controls | 4 planted, seen red, reverted (frame figure; per-field corruption; planted Phase 999; the UPDATE disabled) |
| Bug fixes | 0 — three first-run authoring catches folded into the build commit (Deviations) |
| Whole-tree gates | 521 passed + `finding_check` exit 0, both variants |
| Dry run (snapshot copy) | 67 → 68; 3+16 → 4+23 templates+items; one description updated; `known_issues` hash `5932cd02c78ae850` unchanged; integrity ok |
| Collected count | 9,372 (= floor 9,346 + 26); floor raised with the close-out commit |
| Findings filed | 1 (F159 — the substrate's starter item carries uncited figures) |
| Regression of record | pending — Opus session, outside the sandbox |

Key finding: a content phase on a door that already opens is one
migration and its pins. The 259 pattern held exactly — per-field
figure pins, no-figure negatives with censuses behind them, the journal
seed — and cost no new production surface at all. The step 0 census
also found what the door shows next to the new content: the substrate's
own starter item carries uncited figures on the same screen as a
figure-disciplined protocol (F159), which is the workflow-side shape of
what F149 documented for the corpus.

## Risks

- **Item identity is prose** (S0-2/F129's shape), as in 259: mitigated by
  pinning the content in this phase's tests and keeping the seed inside
  the one-shot journal.
- **The F158 re-point (D3) alters one live row.** The dry run records the
  exact before/after; the rollback restores verbatim; the handoff flags
  it for the operator's eye. If the operator strikes it, the migration's
  UPDATE comes out in one line and the rollback with it.
- **Worked-example figures are the cited machines' own** (Zuma 125,
  CHF50, Metropolitan, KTM EXC, F800R) and the item text says so per
  figure; the refute pass should attack any sentence that implies the
  numbers apply beyond their machine. The tire-age 5-year line is KTM's
  recommendation, quoted as KTM's, not as a universal.
- **The three negatives (C15–C17) are search claims**, and the census's
  counts are what the recorded vocabulary produced; the refute pass
  re-derives them with `census_negatives.py` (session tmp) or its own
  whitespace-proof scan. The parse-count method (partial-text files
  searched over the pages they yield) is stated in the step 0 doc.
- **The generic stub's uncited figures** ("Pads >3mm… tires <5 years
  old") now sit on the same screen as a figure-disciplined protocol;
  filed as a finding rather than edited (D1, F129).
