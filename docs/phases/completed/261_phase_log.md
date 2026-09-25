# Phase 261 — Track N batch 1: tire, brake, suspension and drivetrain service — phase log

**Status:** ✅ Complete (2026-09-25)
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

### 2026-09-25 — Build: migration 069, four templates, 26 tests

Committed at `8842f4a`, after bug fix #1 at `6b98b4c`. What shipped:

- **Migration 069 `chassis_drivetrain_service_workflows`** (schema 68 →
  69). Four templates, all three powertrains, 7 items each:
  `tire_service_v1` (the TPMS item optional), `brake_service_v1` (the
  caliper and master-cylinder overhauls optional), `suspension_service_v1`
  (the fork air bleed optional), `drivetrain_service_v1` (every item
  optional: a machine has one drive type). **Inserts only**; the rollback
  deletes the four templates' items, then the templates.
- **The claims were written before the text.** `s0/claims.py` (session
  scratchpad) holds 157 claims with 250 verbatim anchors, all 250 found on
  their cited page by the Step 0 checker. The text was then written from
  that list, and `s0/xcheck.py` mapped every "PDF p." in the seeded text
  (294 cited pages) back to a claim for its template, attributing each
  citation to the nearest machine named before it: 0 unclaimed. Its
  control: withdrawing T11, the only claim on CB500F OM p. 63, turned it
  red on two citations. (A first control, withdrawing T10, stayed green,
  because KTM p. 116 is also claimed by T1 and T3. It proved nothing and
  was replaced. A same-length edit then served a stale `.pyc`: the
  re-run after restoring still read red until `__pycache__` was cleared
  and `-B` used, the trap in the operator's memory notes.)
- **Corrected before any test ran, by reading the pages:**
  - the Zuma 125's K1/K2 spring rates (7.1 / 15.4 N/mm) are its **front
    fork** spring, listed under "Front suspension" with "Optional spring
    available: No" (SM p. 34). The draft called them rear spring rates;
  - four sentences said more than their page ("pistons caught in a rag",
    "not more damping", "in pairs" for fork springs, "with the fork cold");
    they were cut;
  - four attributions named "Honda" or two BMWs where the reader could
    not tell which manual. Each now names the machine.
- **26 tests** in `tests/test_phase261_service_workflows.py`: fresh init;
  upgrade from a self-built 068 (inserts only: every row present at 068
  byte-identical after it); `rollback_to_version(68)` and re-apply; the
  optional items exactly as planned; per-field figure pins; every
  machine-bound figure beside its machine; the Zuma fork-spring and the
  PCX millimetres-only pins; N1–N3 stated; the u-joint item with no
  measurement; F158 pins with the planted-reference control; applicability
  for every powertrain; the CLI (the full-slug list, each category, show
  for all four).
- **Floor** 9388 → 9414 (+26, this file only; `--collect-only -q -p
  no:xdist` measured 9,414).

**Known-bad controls**, each planted with the Edit tool, seen red on
exactly its own test, and reverted (`__pycache__` cleared, `-B`, before
each run):

| # | plant | red test |
|---|---|---|
| 1 | "over 0.2 mm" in the u-joint item | `test_universal_joint_item_carries_no_measurement` |
| 2 | 272 → 274 mm in the chain-wear instruction only | `test_every_pinned_figure_is_in_its_field` |
| 3 | "(expanded in Phase 999)" in the brake description | `test_all_four_templates_are_clean` |
| 4 | an `UPDATE` of `generic_ppi_v1`'s "Frame inspection" row inside 069 | `test_upgrade_from_68_inserts_only` |
| 5 | `drivetrain_service_v1` dropped from the rollback's template `DELETE` | `test_rollback_peels_everything_069_added` |

Control 5 is worth its line: `test_every_migration_keeps_its_rollback`
stayed green, because the slug still appears in the items `DELETE`. Only
the round trip caught it. After the reverts: `grep` finds none of the
four planted strings, 26 passed, and `xcheck.py` still reads 0 unclaimed.

**Whole-tree gates before the build commit:** rule 3's four, plus the
F124 guard, 240c, 209B, 244U, 244Y, 244V, 191D, 355, and the 114, 259,
260 and 261 files: **497 passed** (`-n auto`), `finding_check` exit 0.

**A working-rules slip, recorded:** two edits used a script instead of the
Edit tool: `sed -i` for the one `SCHEMA_VERSION` line in `database.py`,
and a count-asserted Python `str.replace` for three test-authoring fixes
in the new test file. Both were exact, single-match replacements, and
both regions were read back afterwards (`git diff`, `grep -n`). Every edit
since is by the Edit tool.

## Bug fixes

### Bug fix #1 — 2026-09-25 — `workflow list` elided slugs at 80 columns

- **Issue:** at an 80-column terminal `motodiag workflow list` printed
  `suspension_se…`, `drivetrain_se…` and `tire_service_…`. The slug is
  what `workflow show` takes and the category is what `--category` takes,
  so a user could not read either for this batch's templates, the first
  slugs longer than 16 characters.
- **Root cause:** the Slug and Category columns used rich's default
  overflow (ellipsis) and could shrink to fit the table.
- **Fix:** Slug and Category are `no_wrap`, so they never shrink; Name and
  Powertrains fold instead of eliding, so no text on the screen is lost.
- **Files:** `src/motodiag/cli/workflow.py`.
- **Verified:** `test_workflow_list_shows_every_slug_in_full` and
  `test_list_by_each_new_category`, red on the old code (both seen) and
  green after; the first also asserts no "…" anywhere on the screen, which
  caught a first cut that stopped eliding slugs but elided "Powertr…".

**Commit.** `6b98b4c`

## Deploy preparation — 2026-09-25: the scope check, controlled before the merge

`s0/deploy261.py` (session scratchpad) takes the before-state, backs up
with SQLite's backup API (retain 5), dry-runs on a copy of the backup, and
diffs every table by rowid. It refuses the live apply unless the only
changes are `workflow_templates` +4, `checklist_items` +28 and
`schema_version` +1, with nothing changed or removed anywhere. Control, on
scratch copies taken from live with the backup API (live only read): the
real migration gave no problems; a copy with one existing
`checklist_items` row changed gave "checklist_items: 1 changed". Live
read before and after: schema 68, 1,060 `known_issues`, 4 templates,
23 items, integrity ok, `known_issues` sha256 prefix `dfae941ba742d03f`.

## Refuter pass

Four fresh-context Opus refuters, one per template, 2026-09-25; every cited page opened, every document's identity read from its own title page (rendered as an image where the text layer was empty). Full verdict files, with the item-text defects and the search counts behind each negative: session scratchpad `s0/refute/*_verdict.md`. Rows as the refuters wrote them.

| claim | verdict | quote | source |
|---|---|---|---|
| T1 | kept | "Low tire pressure leads to abnormal wear and overheating of the tire. Correct tire pressure ensures optimal riding comfort and maximum tire service life." | KTM Owner's Manual 2022 250/300 EXC TPI (and XC-W TPI), PDF p. 116 |
| T2 | kept | "Inspect the tires for signs of abnormal wear on the contact surface." | Honda CB500F/FA Owner's Manual, PDF p. 60 |
| T3 | kept | "If the tension in the spokes is too low, then lateral and radial run-out will form in the wheel. Other spokes will become looser as a result." | KTM Owner's Manual 2022 250/300 EXC TPI, PDF p. 116 |
| T4 | kept | "Minimum tread depth Front 0.06 in (1.5 mm) Rear 0.08 in (2.0 mm)" | Honda CB500F/FA Owner's Manual, PDF p. 134 |
| T5 | kept | "Measure the tread depth at the center of the tires. … MINIMUM TIRE TREAD DEPTH: FRONT: 1.5 mm (0.06 in) REAR: 2.0 mm (0.08 in)" | Honda 2013-2017 Service Manual PCX150, PDF p. 97 |
| T6 | kept | "Adhere to the legally required minimum tread depth. Minimum tread depth ≥ 2 mm (≥ 0.08 in)" | KTM Owner's Manual 2022 250/300 EXC TPI, PDF p. 115 |
| T7 | kept | "The tyre is worn out when the tyre tread has worn down to the level of the marks. The locations of the marks are indicated on the edge of the tyre, e.g. by the letters TI, TWI or by an arrow." | BMW Rider's Manual F800R, PDF p. 100 |
| T8 | kept | "Inspect the tires for cuts, slits, or cracks that exposes fabric or cords, or nails or other foreign objects embedded in the side of the tire or the tread." | Honda CB500F/FA Owner's Manual, PDF p. 60 |
| T9 | kept | "Tires age, even if they have not been used or have only been used occasion- ally. Cracking of the tread and sidewall rubber, sometimes accompanied by carcass deformation, is an evidence of ageing." | Yamaha SR400 (SR400J/SR400JC) Owner's Manual, PDF p. 56 |
| T10 | kept | "indicated by the last four digits of the DOT number. The first two digits indicate the week of manufacture and the last two digits the year of manu- facture. KTM recommends that the tires be changed after 5 years at the latest, regardless of the actual state of wear." | KTM Owner's Manual 2022 250/300 EXC TPI, PDF p. 116 |
| T11 | kept | "22 09: Date of manufacture (week & year). Example: week 22 in year 09." | Honda CB500F/FA Owner's Manual, PDF p. 63 |
| T12 | kept | "it is recommended that you have annual inspections performed once the tires reach 5 years old. It is also recommended that all tires be removed from service after 10 years from the date of manufacture, regardless of their condition or state of wear." | Honda CB500F/FA Owner's Manual, PDF p. 62 |
| T13 | kept | "If the motorcycle is equipped with RDC, each wheel rim bears an adhesive label indicating the position of the RDC sensor." | BMW Rider's Manual F800R, PDF p. 103 |
| T14 | kept | "does not enable transmission of the meas- ured values until the motorcycle has accelerated to above approx- imately 30 km/h for the first time. The display shows -- for each tyre until the tyre-pressure signal is received for the first time." | BMW Rider's Manual R 1200 GS, PDF p. 100 |
| T15 | kept | "The tyre-pressure readings shown by the multifunction display are temperature- compensated; the reference tyre temperature for these readings is always 20 °C." | BMW Rider's Manual F800R, PDF p. 76 |
| T16 | kept | "The integral battery in the tyre- pressure sensor has lost a sig- nificant proportion of its original capacity. There is no assurance of how long the tyre pressure control system can remain opera- tional." | BMW Rider's Manual F800R, PDF p. 39 |
| T17 | kept | "Compare the RDC readings on the multifunction display with the value in the table on the inside cover of the Rider's Manual. Then use the air line to compensate for the difference between the RDC reading and the value in the table." | BMW Rider's Manual R 1200 GS, PDF p. 101 |
| T18 | kept | "Do not install a tube inside a tubeless tire on this motorcycle. Excessive heat build-up can cause the tube to burst." | Honda CB500F/FA Owner's Manual, PDF p. 62. The claim label also names "same size, construction…", which is on p. 61 (T19), not p. 62. The item text cites p. 61 for it correctly, so only the claim label is loose. |
| T19 | kept | "Use the recommended tires or equivalents of the same size, construction, speed rating, and load range." | Honda CB500F/FA Owner's Manual, PDF p. 61 |
| T20 | kept | "ATTENTION Front wheel installed wrong way round Risk of accident Note direction-of-rotation arrows on tyre or rim." | BMW Rider's Manual F 800 GS, PDF p. 178 |
| T21 | kept | "Actual runout is 1/2 the total indicator reading. SERVICE LIMIT: Axial: 2.0 mm (0.08 in) Radial: 2.0 mm (0.08 in)" | Honda 2013-2017 Service Manual PCX150, PDF p. 326. The rear wheel is the same, at PDF p. 355. |
| T22 | kept | "WHEEL RIM Check the wheel rim runout. Service Limits: Radial: 2.0mm replace if over" | Kymco PEOPLE/PEOPLE S 250 service manual, PDF p. 188. The rear is the same, at PDF p. 206. |
| T23 | kept | "Have the wheel balanced with Honda Genuine balance weights or equivalent after the tire is installed." | Honda CB500F/FA Owner's Manual, PDF p. 62 |
| T24 | kept | "Permissible front-wheel imbalance max 5 g Balance weight for front wheel (One half of the weights must be attached to the left and the other half to the right of the wheel rim) max 80 g" | BMW Rider's Manual S 1000 XR, PDF p. 205 |
| T25 | kept | "Permissible rear-wheel imbalance max 45 g" | BMW Rider's Manual S 1000 XR, PDF p. 206 |
| T26 | kept | "The wheel should be balanced whenever either the tire or wheel has been changed or replaced." | Yamaha XC50J Owner's Manual, PDF p. 51. The passage sits under the heading "Cast wheels". |
| T27 | kept | "New tyres have a smooth sur- face. This must be roughened by riding in a restrained manner at various heel angles until the tyres are run in." | BMW Rider's Manual F800R, PDF p. 67 |
| T28 | kept | "New tyres do not provide full grip straight away." | BMW Rider's Manual R 1200 GS, PDF p. 85 |
| T29 | kept | "Only mount tires approved and/or recommended by KTM. Other tires could have a negative effect on handling characteristics." | KTM Owner's Manual 2022 250/300 EXC TPI, PDF p. 115 |
| T30 | kept | "Possible cause: Motorcycle is fitted with wheels not equipped with RDC sensors. … Possible cause: One or two RDC sensors have failed." | BMW Rider's Manual F800R, PDF p. 38. The page also has "radio- communication systems operat- ing in the vicinity". |
| T31 | kept | "Incorrect tyre-removal pro- cedures can result in dam- age to the RDC sensors." | BMW Rider's Manual F800R, PDF p. 103 |
| T32 | kept | "Tyre pressure, front 2.5 bar Tyre pressure, rear 2.9 bar" | BMW Rider's Manual S 1000 XR, PDF p. 206. No "cold" condition is stated here or on PDF p. 145; see the defect under item 7. |
| T33 | kept | "New tyres do not provide full grip straight away. Wet roads and extremely sharp in- clines pose a risk of accident." | BMW Rider's Manual R 1200 GS, PDF p. 85 |
| T34 | kept | "A x i a l: 2.0mm replace if over" | Kymco PEOPLE/PEOPLE S 250 service manual, PDF p. 188 |
| N1 | killed | "Check for damage (blisters or cuts) in the side wall, or for significant flat spots on the tires' tread. Replace the tire immediately if any damage of this type is present." | KYMCO People S 50 & 125 & 200 Owner's Manual, PDF p. 27. The same sentence is in KYMCO Agility 50/125 Owner's Manual (pdfs/kymco_agility50-125.pdf), PDF p. 23, and in v2/pdf/Super-8-50X-Owners-Manual.pdf, PDF p. 20. |
| B1 | killed | "Check the brake linings for minimum thicknessA. Minimum thicknessA ≥ 1 mm (≥ 0.04 in)" — the 1 mm half holds, but the claim's "change in pairs" is not on p. 102. That sentence is on p. 104 ("Always change the brake linings in pairs"), which B2 already carries. Fix the claim record: drop "change in pairs" from B1. The item text already cites pairs to p. 104 and needs no change. | KTM 2022 250/300 EXC TPI / XC-W TPI Owner's Manual, PDF p. 102 |
| B2 | kept | "Manually press the brake caliper toward the brake disc to push back the brake pistons. Ensure that brake fluid does not flow out of the brake fluid reservoir, extract some if necessary." … "Always change the brake linings in pairs." | KTM 2022 250/300 EXC TPI / XC-W TPI Owner's Manual, PDF p. 104 |
| B3 | kept | "Brake-pad wear limit, front min 1.0 mm (Friction pad only, without backing plate. The wear indicators (grooves) must be clearly visible.)" (the rear is also min 1.0 mm, p. 95) | BMW F800R Rider's Manual, PDF p. 94 |
| B4 | kept | "Measure: brake pad wear limit a Out of specification J Replace the brake pads as a set. Brake pad wear limit 0.8mm (0.03in)" (front disc; this model's rear brake is a drum, p. 128) | Yamaha YW125Y 2009 Service Manual, PDF p. 134 |
| B5 | kept | "Front brake pads … Check the thickness of the pads. Characteristic Minimum value 1.5 mm" (the rear is the same 1.5 mm, p. 197) | Beverly 125 Service Station Manual, PDF p. 196 |
| B6 | kept | "If necessary have the pads replaced by your dealer. Always replace both left and right brake pads at the same time." | Honda CB500F/FA Owner's Manual, PDF p. 77 |
| B7 | kept | "THE PRESENCE OF BRAKE FLUID ON THE DISC OR BRAKE PADS REDUCES BRAKING EFFICIENCY. IN THIS CASE, REPLACE THE PADS AND CLEAN THE DISC WITH A HIGH-QUALITY SOLVENT." | Beverly 125 Service Station Manual, PDF p. 190 |
| B8 | kept | "Brake discs - wear limit (All standard XC-W models, All stan- dard EXC models) front 2.5 mm (0.098 in) rear 3.5 mm (0.138 in) Brake discs - wear limit (All special models) front 2.5 mm (0.098 in) rear 3.7 mm (0.146 in)" | KTM 2022 250/300 EXC TPI / XC-W TPI Owner's Manual, PDF p. 100 |
| B9 | kept | "Measure the brake disc thickness at several points. SERVICE LIMIT: 3.0 mm (0.12 in) Check the brake disc for warpage. SERVICE LIMIT: 0.30 mm (0.001 in)" (the inch figure is the manual's misprint; the item cites mm only, correctly) | Honda 2013–2017 PCX150 Service Manual, PDF p. 371 |
| B10 | kept | "Brake disc deflection limit (maxi- mum) 0.15mm (0.006in)" … "Brake disc thickness limit (mini- mum) 3.5mm (0.14in)" | Yamaha YW125Y 2009 Service Manual, PDF p. 119 |
| B11 | kept | "Brake disk thickness 4.0 3.0 Brake disk runout ⎯ 0.30" (under "Standard (mm) Service Limit (mm)", front-brake chapter 14) | Kymco People/People S 250 Service Manual, PDF p. 184 |
| B12 | kept | "WARNING Whenever a brake caliper is disassembled, replace the piston seal and dust seal." | Yamaha YW125Y 2009 Service Manual, PDF p. 146 |
| B13 | kept | "Recommended brake component replacement schedule Brake pads Piston seal Brake hose Brake fluid If necessary Every two years Every four years Every two years and whenever the brake is disassembled" | Yamaha YW125Y 2009 Service Manual, PDF p. 146 |
| B14 | kept | "Never use solvents on internal brake components as they will cause the pis- ton seal to swell and distort." | Yamaha YW125Y 2009 Service Manual, PDF p. 147 |
| B15 | kept | "Recommended lubricant Brake caliper piston seal Brake fluid Brake caliper dust seal Silicone grease" | Yamaha YW125Y 2009 Service Manual, PDF p. 147 |
| B16 | kept | "Measure the caliper cylinder I.D. SERVICE LIMIT: Upper: Center/lower: 25.460 mm (1.0024 in) 22.710 mm (0.8941 in) … Measure the caliper piston O.D. SERVICE LIMIT: Upper: Center/lower: 25.31 mm (0.996 in) 22.56 mm (0.8888 in)" (the figures hold; the item drops the Upper / Center-lower labels, see defect 3a) | Honda 2013–2017 PCX150 Service Manual, PDF p. 384 |
| B17 | kept | "Measure the piston O.D. with a micrometer gauge. Service Limit: 25.30mm" | Kymco People/People S 250 Service Manual, PDF p. 194 |
| B18 | kept | "Measure the master cylinder I.D. SERVICE LIMIT: 12.755 mm (0.5022 in) Measure the master piston O.D. SERVICE LIMIT: 12.645 mm (0.4978 in)" (front brake master cylinder; see defect 4a) | Honda 2013–2017 PCX150 Service Manual, PDF p. 373 |
| B19 | kept | "Keep the piston, cups, spring, snap ring and boot as a set; do not substitute individual parts." | Honda 2013–2017 PCX150 Service Manual, PDF p. 374 |
| B20 | kept | "CAUTION ALL THE SEALS AND GASKETS MUST BE REPLACED EVERY TIME THE PUMP IS SERVICED." | Beverly 125 Service Station Manual, PDF p. 201 |
| B21 | kept | "Never use DOT 5 brake fluid. It is silicone-based and purple in color. … Avoid contact between brake fluid and painted parts. Brake fluid attacks paint." | KTM 2022 250/300 EXC TPI / XC-W TPI Owner's Manual, PDF p. 102 |
| B22 | kept | "Brake fluid DOT 4 / DOT 5.1 Standard/classification – DOT" | KTM 2022 250/300 EXC TPI / XC-W TPI Owner's Manual, PDF p. 170 |
| B23 | kept | "Brake Fluid *5 2 Years" (with "*5 : Replacement requires mechanical skill.") | Honda CB500F/FA Owner's Manual, PDF p. 49 |
| B24 | kept | "NOTICE Brake fluid can damage plastic and painted surfaces. Wipe up spills immediately and wash thoroughly. Recommended brake fluid: Honda DOT 4 Brake Fluid or equivalent" | Honda CB500F/FA Owner's Manual, PDF p. 57 |
| B25 | kept | "Always use fresh DOT 3 or DOT 4 brake fluid from a sealed container when servicing the system. Do not mix different types of fluid, they may not be compatible." | Honda 2013–2017 PCX150 Service Manual, PDF p. 363 |
| B26 | kept | "THE BRAKE FLUID IS HYGROSCOPIC, IN OTHER WORDS, IT ABSORBS MOISTURE FROM THE SURROUNDING AIR." | Beverly 125 Service Station Manual, PDF p. 48 |
| B27 | kept | "UNDER NORMAL CLIMATIC CONDITIONS, THE FLUID MUST BE CHANGED EVERY 20,000 KM OR ANYWAY EV- ERY TWO YEARS." (the item drops the "normal conditions" qualifier, see defect 5b) | Beverly 125 Service Station Manual, PDF p. 49 |
| B28 | kept | "When refilling, be careful that water does not enter the brake fluid reservoir. Wa- ter will significantly lower the boiling point of the brake fluid and could cause vapor lock." | Yamaha YW125Y 2009 Service Manual, PDF p. 89 |
| B29 | kept | "Once the hydraulic system has been opened, or if the brake feels spongy, the system must be bled." | Honda 2013–2017 PCX150 Service Manual, PDF p. 363 |
| B30 | kept | "1. Squeeze the brake lever all the way and loosen the bleed valve 1/2 of a turn. … After bleeding the system completely, tighten the bleed valve to the specified torque. TORQUE: 5.4 N·m (0.55 kgf·m, 4.4 lbMt)" | Honda 2013–2017 PCX150 Service Manual, PDF p. 367 |
| B31 | kept | "If bleeding is difficult, it may be necessary to let the brake fluid settle for a few hours. Repeat the bleeding procedure when the tiny bubbles in the hose have disappeared." | Yamaha YW125Y 2009 Service Manual, PDF p. 91 |
| B32 | kept | "j. Tighten the bleed screw to specification. Bleed screw 6Nm (0.6m kgf, 4.3ft lbf)" | Yamaha YW125Y 2009 Service Manual, PDF p. 92 |
| B33 | kept | "Position the brake caliper, and mount and tighten screws4. Guideline Screw, front brake caliper M8 25 Nm (18.4 lbf ft) Loctite®243™" (the same figure appears on pp. 73, 75 and in the p. 168 torque table; no counter-figure) | KTM 2022 250/300 EXC TPI / XC-W TPI Owner's Manual, PDF p. 69 |
| B34 | kept | "Tighten screws 1 of the brake calipers on left and right to the specified torque. Brake caliper on fork leg 30 Nm" | BMW F800R Rider's Manual, PDF p. 106 |
| B35 | kept | "Brake caliper mounting bolt 2 8 30 (3.1, 22) ALOC bolt: replace with new ones." (p. 386 confirms it is the front caliper: "Install the new front brake caliper mounting bolts … TORQUE:30 N·m") | Honda 2013–2017 PCX150 Service Manual, PDF p. 21 |
| B36 | kept | "Operate the foot brake lever repeatedly until the brake lin- ings are in contact with the brake disc and there is a pressure point." (the hand-lever twin is on p. 104) | KTM 2022 250/300 EXC TPI / XC-W TPI Owner's Manual, PDF p. 109 |
| B37 | kept | "New brake pads have to bed down before they can achieve their optimum friction levels. … New brake pads can ex- tend stopping distance by a significant margin." | BMW F800R Rider's Manual, PDF p. 67 |
| B38 | kept | "Install the brake caliper to the shock absorber and tighten the two bolts. Torque: 29～35N-m" (the rear caliper is also 29～35 N-m, p. 205) | Kymco People/People S 250 Service Manual, PDF p. 195 |
| B39 | kept | "Before disassembling the brake caliper, drain the brake fluid from the entire brake system. … a. Blow compressed air into the brake hose joint opening a to force out the pistons from the brake caliper." | Yamaha YW125Y 2009 Service Manual, PDF p. 145 |
| B40 | kept | "CAUTION ALL THE SEALS AND GASKETS MUST BE REPLACED EV- ERY TIME THE CALLIPER IS SERVICED." | Beverly 125 Service Station Manual, PDF p. 193 |
| B41 | kept | "Measure the brake master cylinder I.D. Inspect the master cylinder for scratches or cracks. Service Limit: 12.75mm" | Kymco People/People S 250 Service Manual, PDF p. 191 |
| B42 | kept | "Actuate the tool at the bleed fitting, at the same time constantly topping up the brake system tank to prevent air being drawn into the system" (said of the MityVac vacuum-pump bleed, see defect 6b) | Beverly 125 Service Station Manual, PDF p. 199 |
| B43 | kept | "Wait several seconds and then close the bleed valve. 2. Release the brake lever slowly and wait several seconds after it reaches the end of its travel." | Honda 2013–2017 PCX150 Service Manual, PDF p. 367 |
| B44 | kept | "Never use solvents on internal brake components as they will cause the pis- ton seal to swell and distort." | Yamaha YW125Y 2009 Service Manual, PDF p. 147 |
| B45 | kept | "Oil seals and brake lines are not designed for DOT 5 brake fluid." | KTM 2022 250/300 EXC TPI / XC-W TPI Owner's Manual, PDF p. 102 |
| S1 | kept | "When adjusting the basic chassis setting, first adjust the shock absorber and then the fork. … Standard rider weight 75 … 85 kg (165 … 187 lb.) … Small weight differences can be compensated by adjusting the spring preload, but in the case of large weight differences, the springs must be replaced." | KTM Owner's Manual 2022 250/300 EXC TPI, EXC Six Days, XC‑W TPI (Art. no. 3214421en), PDF p. 55 |
| S2 | kept | "Static sag 37 mm (1.46 in)" … "the rider, wear- ing full protective clothing, sits on the seat in a normal sitting position (feet on footrests) and bounces up and down a few times" … "Riding sag 110 mm (4.33 in)" | KTM Owner's Manual 2022 250/300 EXC TPI etc. (3214421en), PDF p. 58 |
| S3 | kept | "Position the sag gage in the rear axle and measure the distance to markingSAG on the rear fender." | KTM Owner's Manual 2022 250/300 EXC TPI etc. (3214421en), PDF p. 57 |
| S4 | killed | "(690 Enduro) Static sag 25 mm (0.98 in) (690 Enduro R) Static sag 25 mm (0.98 in)". The static-sag half holds. The claim also puts "riding sag 70–80 mm" on p. 73, but that figure is on p. 74 (S5). Trim S4 to static sag only. The item text already cites pp. 73–74 correctly. | KTM Owner's Manual 2010 690 Enduro / 690 Enduro R (3211511en), PDF p. 73 |
| S5 | kept | "(690 Enduro) Riding sag 70… 80 mm (2.76… 3.15 in) (690 Enduro R) Riding sag 70… 80 mm (2.76… 3.15 in)" | KTM Owner's Manual 2010 690 Enduro / 690 Enduro R (3211511en), PDF p. 74 |
| S6 | kept | "Weight of rider: 65 … 75 kg (143 … 165 lb.) 57 … 63 N/mm … For various reasons, no exact riding sag can be determined for the fork. … if the fork frequently bottoms out (hard end stop on compression), harder springs must be fitted … If the fork feels unusually hard after extended periods of oper- ation, the fork legs need to be bled." The rates on this page are the shock spring's (section 11.10, "Remove the shock absorber"). | KTM Owner's Manual 2022 250/300 EXC TPI etc. (3214421en), PDF p. 60 |
| S7 | kept | "23.7 Fork … Weight of rider: 65 … 75 kg (143 … 165 lb.) 4.2 N/mm (24 lb/in) … 4.4 N/mm (25.1 lb/in) … 4.6 N/mm (26.3 lb/in) … Fork oil per fork leg 636 ± 10 ml (21.5 ± 0.34 fl. oz.) Fork oil (SAE 4)" | KTM Owner's Manual 2022 250/300 EXC TPI etc. (3214421en), PDF p. 166 |
| S8 | kept | "18.1690 Enduro … 5.2 N/mm (29.7 lb/in) … 5.4 N/mm (30.8 lb/in) … 5.6 N/mm (32 lb/in) … Fork oil per fork leg 620 ml (20.96 fl. oz.) Fork oil (SAE 5)". This is the 690 Enduro only. The Enduro R, on PDF p. 184, lists a single fork spring of "5.2 N/mm", for 75… 85 kg riders only, and "635 ml". | KTM Owner's Manual 2010 690 Enduro / 690 Enduro R (3211511en), PDF p. 183 |
| S9 | kept | "FORK FLUID CAPACITY: 122.0 ± 2.5 cm3 … Pump the fork pipe several times to remove trapped air … Compress the fork leg fully and measure the fluid level from the top of the fork pipe. FORK FLUID LEVEL: 75 mm (2.95 in)" | Honda PCX150 Service Manual, PDF p. 335 |
| S10 | kept | "Quantity (each front fork leg) 0.104L (0.11 US qt, 0.09 Imp. qt) Recommended oil Fork oil 10W or equivalent" | Yamaha 2009 Service Manual, Model YW125Y, PDF p. 160 |
| S11 | kept | "Make sure the oil levels in both front fork legs are equal. … Uneven oil levels can result in poor han- dling and a loss of stability." | Yamaha 2009 Service Manual, Model YW125Y, PDF p. 158 |
| S12 | kept | "Stoke the outer tube several times while drain- ing the fork oil." | Yamaha 2009 Service Manual, Model YW125Y, PDF p. 155 |
| S13 | kept | "Never reuse the oil seal." | Yamaha 2009 Service Manual, Model YW125Y, PDF p. 156 |
| S14 | kept | "Make sure the numbered side of the oil seal faces up. … Before installing the oil seal, lubricate its lips with lithium soap base grease." | Yamaha 2009 Service Manual, Model YW125Y, PDF p. 159 |
| S15 | kept | "Apply fork fluid to the lip of a new oil seal … Install the oil seal stopper ring [1] into the stopper ring groove on the fork slider." | Honda PCX150 Service Manual, PDF p. 334 |
| S16 | kept | "Over time, dirt can accumu- late behind the dust boots. If this dirt is not removed, the oil seals behind can start to leak." | KTM Owner's Manual 2022 250/300 EXC TPI etc. (3214421en), PDF p. 67 |
| S17 | kept | "Spring free length 252.1mm (9.93in) <Limit> :247mm (9.72in)" | Yamaha 2009 Service Manual, Model YW125Y, PDF p. 157 |
| S18 | kept | "Measure th e for k sprin g fre e length . SERVICE LIMIT: 1 2 5 .9 mm (4.96 in)" | Honda CHF50 Service Manual, PDF p. 227 |
| S19 | kept | "Gas pressure 10 bar (145 psi) … Shock absorber fluid ( p. 169) SAE 2.5" | KTM Owner's Manual 2022 250/300 EXC TPI etc. (3214421en), PDF p. 167 |
| S20 | kept | "The shock absorber is filled with highly compressed nitrogen." | KTM Owner's Manual 2022 250/300 EXC TPI etc. (3214421en), PDF p. 55 |
| S21 | kept | "The rear shock absorber damper unit contains high pressure nitrogen gas. Do not attempt to disassemble, service, or improperly dispose of the damper. See your dealer." | Honda 2018 XR650L Owner's Manual (31MGW660), PDF p. 85 |
| S22 | kept | "rear shock absorber Oil leaks J Replace the rear shock ab- sorber assembly." | Yamaha 2009 Service Manual, Model YW125Y, PDF p. 175 |
| S23 | kept | "Check the action of the shock absorber by compressing it several times. Check the entire shock absorber ·assembly for signs of leaks, damage or loose fasteners." | Honda PCX150 Service Manual, PDF p. 95 |
| S24 | kept | "Turn adjusting screw1 clockwise with a screwdriver as far as the last perceptible click. … Low-speed compression damping Comfort 18 clicks Standard 15 clicks … High-speed compression damping Comfort 2.5 turns Standard 2 turns". Both counts start from fully clockwise. | KTM Owner's Manual 2022 250/300 EXC TPI etc. (3214421en), PDF p. 56 |
| S25 | kept | "Rebound damping Comfort 18 clicks Standard 15 clicks Sport 12 clicks" | KTM Owner's Manual 2022 250/300 EXC TPI etc. (3214421en), PDF p. 57 |
| S26 | kept | "Spring preload 9 mm (0.35 in)" | KTM Owner's Manual 2022 250/300 EXC TPI etc. (3214421en), PDF p. 59 |
| S27 | kept | "These adjustments should be understood as a guideline … Do not change the adjustments at random or by more than ± 40%, since otherwise the riding characteristics could deteriorate, particularly at high speeds." | KTM Owner's Manual 2010 690 Enduro / 690 Enduro R (3211511en), PDF p. 64 |
| S28 | kept | "The preload adjuster has 9 positions. The standard position is 4 when the index mark on the adjuster is aligned with the left end of the rear shock absorber lower mounting bolt. … Attempting to adjust directly from 1 to 9 or 9 to 1 may damage the shock absorber." | Honda 2018 CB500F/CB500FA Owner's Manual (31MJWB20), PDF p. 92 |
| S29 | killed | "Front suspension … Spring rate (K1) 7.1N/mm … Spring rate (K2) 15.4N/mm". These are the front fork spring rates. The rear rates on the same page are "Spring rate (K1) 9.3N/mm … (K2) 13.15N/mm … (K3) 19.23N/mm". The claim text's "rear" is wrong. The item text correctly calls these the fork spring, so the item has no defect here. | Yamaha 2009 Service Manual, Model YW125Y, PDF p. 34 |
| S30 | kept | "The spring rate is shown on the outside of the spring." This is in section 11.10, the shock spring. | KTM Owner's Manual 2022 250/300 EXC TPI etc. (3214421en), PDF p. 60 |
| S31 | kept | "Front suspension … Spring rate (K1) 7.1N/mm … Spring rate (K2) 15.4N/mm … Optional spring available No" | Yamaha 2009 Service Manual, Model YW125Y, PDF p. 34 |
| S32 | kept | "9.14Bleeding the fork legs – Lean the motorcycle on the side stand." The procedure continues on p. 76: "Remove bleeder screws briefly. Any excess pressure escapes from the interior of the fork." | KTM Owner's Manual 2010 690 Enduro / 690 Enduro R (3211511en), PDF p. 75 |
| S33 | kept | "12.8 Installing the fork legs … Position the fork legs. Bleeder screws1 are positioned toward the front." The page is true, but it is fork-leg installation, not bleeding (see Item 5 below). | KTM Owner's Manual 2022 250/300 EXC TPI etc. (3214421en), PDF p. 69 |
| S34 | kept | "The static sag is the difference between measurementsA andB. … the rider, wear- ing full protective clothing … The riding sag is the difference between measurementsA andC." | KTM Owner's Manual 2022 250/300 EXC TPI etc. (3214421en), PDF p. 58 |
| S35 | kept | "Apply fork fluid to a new dust seal [2] lip." | Honda PCX150 Service Manual, PDF p. 334 |
| D1 | kept | "Chain wear is not always even, so you should repeat this measurement at different chain positions. Chain tension 55 … 58 mm (2.17 … 2.28 in)" | KTM Owner's Manual 2022 250/300 EXC TPI (Art. no. 3214421en), PDF p. 90 |
| D2 | kept | "If the chain is tensioned too much, the chain, engine sprocket, rear sprocket, transmission and rear wheel bearings wear more quickly. … If the chain is too loose, the chain may fall off the engine sprocket or the rear sprocket." | KTM Owner's Manual 2022 250/300 EXC TPI, PDF p. 89 |
| D3 | kept | "If the slack is not constant at all points, some links may be kinked and binding. … Drive chain slack: 1 3/8 - 1 3/4 in (35 - 45 mm) u Do not ride your motorcycle if the slack exceeds 2 3/8 in (60 mm)." | Honda CB500F/CB500FA Owner's Manual (2018, USA), PDF p. 80 |
| D4 | kept | "Turn the rear wheel until it reaches the position with the lowest amount of chain sag. Use a screwdriver to push the chain up and down and measure difference a. Chain deflection 30...40 mm (Motorcycle with no weight applied, supported on its side stand)" | BMW F 800 R Rider's Manual, PDF p. 101 |
| D5 | kept | "Weight, chain wear measurement 10 … 15 kg (22 … 33 lb.) – Measure distanceB of 18 chain rollers in the lower chain section. … Maximum distanceB from 18 chain rollers at the longest chain section 272 mm (10.71 in) » If distanceB is greater than the specified measurement: – Change the drivetrain kit." | KTM Owner's Manual 2022 250/300 EXC TPI, PDF p. 92 |
| D6 | kept | "If the index mark on the washer enters the red zone on the label after the chain has been adjusted to the proper slack, the chain is excessively worn and must be replaced." | Honda CB500F/CB500FA Owner's Manual, PDF p. 83 |
| D7 | kept | "Pull the chain back at the rear- most point of the sprocket." | BMW F 800 R Rider's Manual, PDF p. 102 |
| D8 | kept | "The engine sprocket, rear sprocket, and chain should always be replaced together." | KTM Owner's Manual 2022 250/300 EXC TPI, PDF p. 91 |
| D9 | kept | "Use of a new chain with worn sprockets will cause rapid chain wear." | Honda CB500F/CB500FA Owner's Manual, PDF p. 58 |
| D10 | kept | "If the lower edge of the chain pins is in line with, or below, the chain sliding guard: – Change the chain sliding guard." | KTM Owner's Manual 2022 250/300 EXC TPI, PDF p. 92 |
| D11 | kept | "If the light part of the chain guide is worn: – Change the chain guide." | KTM Owner's Manual 2022 250/300 EXC TPI, PDF p. 93 |
| D12 | kept | "Rinse off loose dirt with a soft jet of water. – Remove old grease residue with chain cleaner. … – After drying, apply chain spray." | KTM Owner's Manual 2022 250/300 EXC TPI, PDF p. 89 |
| D13 | kept | "Do not use a steam cleaner, a high pressure cleaner, a wire brush, volatile solvent such as gasoline and benzene, abrasive cleaner, chain cleaner or lubricant NOT designed specifically for O-ring chains as these can damage the rubber O-ring seals." | Honda CB500F/CB500FA Owner's Manual, PDF p. 59 |
| D14 | kept | "Lubricate the drive chain every 1000 km at the latest." | BMW F 800 R Rider's Manual, PDF p. 100 |
| D15 | kept | "Turn adjusting screws3 on the left and right so that the markings on the left and right chain adjusters are in the same position relative to reference marksA. The rear wheel is then correctly aligned. … Nut, rear wheel spin- dle M20x1.5 80 Nm (59 lbf ft)" | KTM Owner's Manual 2022 250/300 EXC TPI, PDF p. 91 |
| D16 | kept | "Tighten the rear axle nut. Torque: 65 lbf·ft (88 N·m, 9.0 kgf·m) … hold the adjusting nuts and tighten the lock nuts. Torque: 15 lbf·ft (21 N·m, 2.1 kgf·m)" | Honda CB500F/CB500FA Owner's Manual, PDF p. 82 |
| D17 | kept | "Make sure that scale read- ings 4 are the same on left and right." | BMW F 800 R Rider's Manual, PDF p. 101 |
| D18 | kept | "Locknut of the final-drive chain tensioning screw 19 Nm … Rear quick-release axle in swinging arm 100 Nm" | BMW F 800 R Rider's Manual, PDF p. 102 |
| D19 | kept | "Standard drive chain DID520V0 No. of links 112 Standard sprocket size Drive sprocket 15T Driven sprocket 41T" | Honda CB500F/CB500FA Owner's Manual, PDF p. 134 |
| D20 | kept | "Nut, rear sprocket screw M8 35 Nm (25.8 lbf ft) Loctite®2701™" | KTM Owner's Manual 2022 250/300 EXC TPI, PDF p. 168 |
| D21 | kept | "Screw, drive chain engine sprocket M10 60 Nm (44.3 lbf ft) Loctite®2701™" | KTM Owner's Manual 2022 250/300 EXC TPI, PDF p. 163 |
| D22 | kept | "Note the position of the drive belt with a force of 45 N (4.5 kgf, 10 lbf) applied to the belt with a belt ten- sion gauge as shown." | Yamaha XVS95CL/XVS95CLC Owner's Manual (BP6-28199-13), PDF p. 65 |
| D23 | kept | "If the drive belt slack is incorrect, have a Yamaha dealer adjust it. … Drive belt slack: 6.0–8.0 mm (0.24–0.31 in)" | Yamaha XVS95CL/XVS95CLC Owner's Manual (BP6-28199-13), PDF p. 66 |
| D24 | kept | "The marks near the drive belt check hole are 5.0 mm (0.2 in) apart. … Drive belt slack: 5.0–7.0 mm (0.20–0.28 in)" | Yamaha XVS13AF/XVS13AFC Owner's Manual (3D8-28199-18), PDF p. 64 |
| D25 | kept | "Drive belt • Check belt condition. • Replace if damaged. • Check belt tension. • Adjust if necessary. √ Every 2500 mi (4000 km)" | Yamaha XVS95CL/XVS95CLC Owner's Manual (BP6-28199-13), PDF p. 48 |
| D26 | kept | "Never apply oil or wax to the drive belt." | Yamaha XVS13AF/XVS13AFC Owner's Manual (3D8-28199-18), PDF p. 82 |
| D27 | kept | "Change the oil in the rear wheel drive while at regular operating temperature 3) *)" | BMW Service and Technical Booklet R 1100 S, PDF p. 6 |
| D28 | kept | "3) Every 40, 000 km (24, 000 miles) or at the latest every 2y e a r s" | BMW Service and Technical Booklet R 1100 S, PDF p. 8 |
| D29 | kept | "Gearbox oil Brand-name hypoid gear oil, API class GL 5 … Final drive approx. 0.25 l (0.44 Imp.pint) (to bottom edge of filler screw) Viscosity class at outside temperature: above 5 °C SAE 90 below 5 °C SAE 80 alternatively SAE 80 W 90" | BMW Service and Technical Booklet R 1100 S, PDF p. 87 |
| D30 | kept | "Final drive approx. 0.25 l (to bottom edge of filler opening)" | BMW Maintenance Instructions R 1150 R / R 850 R, PDF p. 67 |
| D31 | kept | "Final drive 0.25 l (to bottom edge of filler opening)" | BMW Maintenance Instructions K 1200 RS, PDF p. 70 |
| D32 | kept | "By shaft protected within hollow swinging arm of Paralever rear suspension, with integral torsional vibration damper and two universal joints." | BMW Service and Technical Booklet R 1100 S, PDF p. 81 |
| D33 | kept | "Check swinging arm bearings (freedom from play), adjust if necessary* )" | BMW Service and Technical Booklet R 1100 S, PDF p. 7 |
| D34 | kept | "Type of final drive Shaft drive with bevel gears" | BMW Rider's Manual R 1200 GS, PDF p. 156 |
| D35 | kept | "Shift the transmission to Neutral. … Check the slack in the lower half of the drive chain midway between the sprockets." | Honda CB500F/CB500FA Owner's Manual, PDF p. 80 |
| D36 | kept | "Also inspect the drive sprocket and driven sprocket. If either has worn or damaged teeth, have the sprocket replaced by your dealer." | Honda CB500F/CB500FA Owner's Manual, PDF p. 58 |
| D37 | kept | "as these can damage the rubber O-ring seals. Avoid getting lubricant on the brakes or tires." | Honda CB500F/CB500FA Owner's Manual, PDF p. 59 |
| D38 | kept | "Lubric- ate the chain more frequently if the motorcycle is ridden in wet, dusty or dirty conditions. … Wipe off excess lubricant." | BMW F 800 R Rider's Manual, PDF p. 100 |
| D39 | kept | "Turn both adjusting nuts an equal number of turns until the correct drive chain slack is obtained." | Honda CB500F/CB500FA Owner's Manual, PDF p. 82 |
| D40 | kept | "Place the vehicle on the side- stand." | Yamaha XVS13AF/XVS13AFC Owner's Manual (3D8-28199-18), PDF p. 64 |
| D41 | kept | "The top of the teeth are still between the chain links ( a): the chain is OK. The chain is being pulled out over the top of the teeth ( b): contact a specialist workshop" | BMW F 800 R Rider's Manual, PDF p. 102 |
| D42 | kept | "Gearbox approx. 0.80 l (to bottom edge of filler opening) Final drive approx. 0.25 l (to bottom edge of filler opening)" | BMW Maintenance Instructions R 1150 R / R 850 R, PDF p. 67 |
| D43 | kept | "If the lower edge of the chain pins is in line with or below the chain sliding piece: – Change the chain sliding piece." | KTM Owner's Manual 2022 250/300 EXC TPI, PDF p. 93 |
| N2 | kept | "with integral torsional vibration damper and two universal joints." (positive control: the only drive-line universal-joint mentions in the library are descriptive technical data, with no inspection step or play figure) | BMW Service and Technical Booklet R 1100 S, PDF p. 81 (the same sentence appears in K 1200 RS Maintenance Instructions p. 64 and R 1150 R / R 850 R Maintenance Instructions p. 61) |
| N3 | kept | "Check belt condition. • Replace if damaged. • Check belt tension. • Adjust if necessary." (positive control: the only final-drive belt schedule in the library; no alignment step or figure) | Yamaha XVS95CL/XVS95CLC Owner's Manual (BP6-28199-13), PDF p. 48 (the same row is in XVS13AF/XVS13AFC p. 47) |

**Round 1 result: 156 of 160 rows kept; 4 killed.**
- **N1 is killed as first written.** Kymco's People S 50/125/200 owner's
  manual names a tread shape: "significant flat spots on the tires'
  tread. Replace the tire immediately" (PDF p. 27). The narrower claim
  survives: no document names cupping, feathering, scalloping, sawtooth,
  heel-and-toe, or squared or stepped wear. The item now names the flat
  spot, with its citation, and states the narrowed negative.
- **B1, S4 and S29 were wrong claim records, not wrong content.** B1 put
  "change in pairs" on p. 102; it is on p. 104. S4 put the 690's riding
  sag on p. 73; it is on p. 74. S29 labelled the YW125Y's K1/K2 rates
  "rear"; they are the fork's. The item text already had all three
  right.

**The item-text defects, about 50 across the 28 items, were all
corrected** before round 2. Grouped:
- **Machine names, from the title pages:** KTM 2022 250/300 EXC TPI;
  Honda PCX150 (2013–2017); Yamaha YW125Y ("Zuma" is on none of its
  pages, F160 for 260's text); Kymco People / People S 250; 2010 KTM 690
  Enduro, not the Enduro R; Yamaha XVS95CL and XVS13AF, not XVS950 and
  XVS1300.
- **Scope:**
  - figures with their conditions: the PCX150 caliper's upper and
    centre/lower bores; its front and CBS master cylinders; the fork
    level's datum;
  - each chain-slack figure with its own way of measuring. KTM's 55–58 mm
    at the sliding piece is not Honda's midway slack, and comparing them
    gives a wrong verdict;
  - the BMW final-drive viscosity per model, and the Beverly fluid
    interval's "normal conditions".
- **Makers' positions:** the XR650L notice is the owner's manual speaking
  to the owner ("See your dealer"), not a workshop ban. "The makers
  disagree" became "service policy differs by shock". KTM's shock service
  is cited to its schedule (p. 53).
- **Wrong pages:** the EXC fork bleed is p. 66 on a lift stand, not
  p. 69. The fork spring table is p. 166 only.
- **Steps no document states** are now marked as the template's own: the
  drive-line lash check, the drain-plug inspection and the sealing
  washer, and the "dark, milky oil" reading.
- **The fork-oil item became optional:** the Honda CHF50's fork is
  greased, with no oil to change (SM p. 227).

The corrections added 53 claims (T35–T46, B46–B61, S36–S50, D44–D53,
drawn from the refuters' own quotes) and retired 3 (T32, B42, S33) whose
sentences left the content. All 320 anchors are on their pages. The
cross-check reads 353 cited pages with 0 unclaimed, and a new test pins
the title-page names; its control, a planted "Zuma", went red.

### Round 2 — 2026-09-25: the 53 claims round 1's corrections added, and the corrected text

One fresh-context Opus refuter. Identity of the two documents new in this round from their own pages: the rendered cover of `pdf/PeopleS-50-125-200.pdf` reads "KYMCO PEOPLE S 50 & 125 & 200 OWNER'S MANUAL"; `pdf/kymco_like_150i_50i_om.pdf` has no cover (its PDF metadata title is a leftover, "DOWNTOWN 125i"), and its pp. 2 and 5 name the KYMCO LIKE 150i/50i.

| claim | verdict | quote | source |
|---|---|---|---|
| T35 | kept | "Check for damage (blisters or cuts) in the side wall, or for significant flat spots on the tires' tread. Replace the tire immediately if any damage of this type is present." | Kymco People S 50 & 125 & 200 Owner's Manual, PDF p. 27 |
| T36 | kept | "Proper wheel balance is important to avoid variable contact between tire and ground, and to avoid uneven tire wear." | KYMCO LIKE 150i/50i Owner's Manual (no cover; name from p. 2), PDF p. 53 |
| T37 | kept | "if the sidewall is cracked, have a Yamaha dealer replace the tire immediately" | Yamaha SR400 (SR400J/SR400JC) Owner's Manual, PDF p. 55 |
| T38 | kept | "Old and aged tires shall be checked by tire specialists to ascertain their suitability for further use." | Yamaha SR400 (SR400J/SR400JC) Owner's Manual, PDF p. 56 |
| T39 | kept | "If the tires have cuts, run-in objects, or other damage: – Change the tires." | KTM Owner's Manual 2022 250/300 EXC TPI (3214421en), PDF p. 115 |
| T40 | kept | "The display shows -- for each tyre until the tyre-pressure signal is received for the first time." | BMW Rider's Manual R 1200 GS, PDF p. 100 |
| T41 | kept | "The motorcycle has not yet ac- celerated past the threshold of approximately 30 km/h." | BMW Rider's Manual F800R, PDF p. 37 |
| T42 | kept | "Possible cause: A system error has occurred." | BMW Rider's Manual F800R, PDF p. 38 |
| T43 | kept | "The integral battery in the tyre- pressure sensor has lost a sig- nificant proportion of its original capacity. … Seek the advice of a specialist workshop" | BMW Rider's Manual F800R, PDF p. 39 |
| T44 | kept | "Tyre pressure, front 2.5 bar, Tyre cold Tyre pressure, rear 2.9 bar, Tyre cold" | BMW Rider's Manual F800R, PDF p. 134 |
| T45 | kept | "New tyres do not provide full grip straight away. Wet roads and extremely sharp in- clines pose a risk of accident." (the item's paraphrase of this line is defect 8) | BMW Rider's Manual R 1200 GS, PDF p. 85 |
| T46 | kept | "ATTENTION Front wheel installed wrong way round Risk of accident Note direction-of-rotation arrows on tyre or rim." | BMW Rider's Manual F 800 GS, PDF p. 178 |
| B46 | kept | "If the warpage exceeds the service limit, check the wheel bearings for excessive play." | Honda 2013–2017 PCX150 Service Manual, PDF p. 371 |
| B47 | kept | "Remove the wheel and check using the appro- priate tools that the axial run-out of the brake surface is within the prescribed limits. … WHEN INSTALLING, THOROUGHLY CLEAN THE DISC AND ITS SEAT ON THE HUB." (the item's use of this line is defect 1) | Piaggio Beverly 125 Service Station Manual, PDF p. 196 |
| B48 | kept | "Measure the caliper cylinder I.D. SERVICE LIMIT: Upper: Center/lower: 25.460 mm (1.0024 in) 22.710 mm (0.8941 in) … Measure the caliper piston O.D. SERVICE LIMIT: Upper: Center/lower: 25.31 mm (0.996 in) 22.56 mm" | Honda 2013–2017 PCX150 Service Manual, PDF p. 384 |
| B49 | kept | "IT IS THEREFORE NECESSARY TO CLEAN THEM THOROUGH WITH DENATURED ALCOHOL. … RUBBER PARTS SHOULD NEVER BE LEFT IN ALCOHOL LONGER THAN 20 SECONDS." | Piaggio Beverly 125 Service Station Manual, PDF p. 190 |
| B50 | kept | "Apply silicon grease to the piston and oil seal." | Kymco People / People S 250 Service Manual, PDF p. 194 |
| B51 | kept | "brake caliper cylinder 2 Scratches/wear J Replace the brake caliper assembly." | Yamaha 2009 Service Manual, Model YW125Y, PDF p. 146 |
| B52 | kept | "that the cylinder and the floating body of the cal- liper do not show signs of scratches or erosion, otherwise replace the entire calliper" | Piaggio Beverly 125 Service Station Manual, PDF p. 192 |
| B53 | kept | "CBS master Cylinder I.D. 11.000 - 11.043 (0.4331 - 0.4348) 11.055 (0.4352) cylinder Piston O.D. 10.957 - 10.984 (0.4314 - 0.4324) 10.945 (0.4309)" | Honda 2013–2017 PCX150 Service Manual, PDF p. 363 |
| B54 | kept | "During assembly, the main piston and spring must be installed as a unit without exchange." | Kymco People / People S 250 Service Manual, PDF p. 191 |
| B55 | kept | "Immediately clean up any brake fluid that has over- flowed or spilled using water." | KTM Owner's Manual 2022 250/300 EXC TPI (3214421en), PDF p. 102 |
| B56 | kept | "UNDER NORMAL DRIVING AND CLIMATIC CONDITIONS YOU SHOULD CHANGE THE FLUID EVERY TWO YEARS. IF BRAKES ARE USED INTENSELY AND/OR IN HARSH CON- DITIONS, CHANGE THE FLUID MORE FREQUENTLY." | Piaggio Beverly 125 Service Station Manual, PDF p. 190 |
| B57 | kept | "UNDER NORMAL CLIMATIC CONDITIONS, THE FLUID MUST BE CHANGED EVERY 20,000 KM OR ANYWAY EV- ERY TWO YEARS." | Piaggio Beverly 125 Service Station Manual, PDF p. 49 |
| B58 | kept | "Use only the designated brake fluid. Other brake fluids may cause the rub- ber seals to deteriorate, causing leakage and poor brake performance." | Yamaha 2009 Service Manual, Model YW125Y, PDF p. 89 |
| B59 | kept | "Check the fluid level often while bleeding the brake to prevent air from being pumped into the system. … Repeat the steps 1 and 2 until there are no air bubbles in the bleed hose." | Honda 2013–2017 PCX150 Service Manual, PDF p. 367 |
| B60 | kept | "IF AIR CONTINUES TO COME OUT DURING THE BLEED OPERATION, EXAMINE ALL THE FITTINGS. IF SAID FIT- TINGS DO NOT SHOW SIGNS OF BEING FAULTY, LOOK FOR THE AIR INPUT AMONG THE VARIOUS SEALS ON THE PUMP AND CALLIPER PISTONS." | Piaggio Beverly 125 Service Station Manual, PDF p. 199 |
| B61 | kept | "Operate the hand brake lever repeatedly until the brake lin- ings are in contact with the brake disc and there is a pressure point." | KTM Owner's Manual 2022 250/300 EXC TPI (3214421en), PDF p. 104 |
| S36 | kept | "11.10 Adjusting the riding sag … – Choose and mount a suitable spring." | KTM Owner's Manual 2022 250/300 EXC TPI (3214421en), PDF p. 60 |
| S37 | kept | "» If the static sag is less or more than the specified value: – Adjust the spring preload of the shock absorber." | KTM Owner's Manual 2022 250/300 EXC TPI (3214421en), PDF p. 58 |
| S38 | kept | "18.2690 Enduro R … Spring rate Weight of rider: 75… 85 kg (165… 187 lb.) 5.2 N/mm (29.7 lb/in) … Fork oil per fork leg 635 ml (21.47 fl. oz.)" | KTM Owner's Manual 2010 690 Enduro / 690 Enduro R (3211511en), PDF p. 184 |
| S39 | kept | "18.1690 Enduro … Weight of rider: 65… 75 kg (143… 165 lb.) 5.2 N/mm … 75… 85 kg … 5.4 N/mm … 85… 95 kg … 5.6 N/mm … Fork oil per fork leg 620 ml" | KTM Owner's Manual 2010 690 Enduro / 690 Enduro R (3211511en), PDF p. 183 |
| S40 | kept | "Appl y 6 .5 - 8 g of greas e to th e followin g p a r t s. - r e b o u nd s p r i ng - g u i d e bushin g inne r s u r f a ce - f o r k sprin g tightl y woun d e nd" (the item's citation for "no oil" is defect 7) | Honda CHF50 Service Manual, PDF p. 227 |
| S41 | kept | "Pro Honda Suspension Fluid SS-8 (1 OW) or equivalent FORK FLUID CAPACITY: 122.0 ± 2.5 cm3 … Compress the fork leg fully and measure the fluid level … from the top of the fork pipe. FORK FLUID LEVEL: 75 mm … Be sure the oil level … is same in the both forks." | Honda 2013–2017 PCX150 Service Manual, PDF p. 335 |
| S42 | kept | "Make sure the oil levels in both front fork legs are equal. … Uneven oil levels can result in poor han- dling and a loss of stability." | Yamaha 2009 Service Manual, Model YW125Y, PDF p. 158 |
| S43 | kept | "inner tube 1 8outer tube 2 Bends/damage/scratches J Replace. WARNING Do not attempt to straighten a bent inner tube" (the item's narrowing of this is defect 5) | Yamaha 2009 Service Manual, Model YW125Y, PDF p. 157 |
| S44 | kept | "12.3 Bleeding the fork legs Preparatory work – Raise the motorcycle with a lift stand. … – Release bleeder screws1. Any excess pressure escapes from the interior of the fork." ("Neither wheel is in contact with the ground." is on the same page, §12.1) | KTM Owner's Manual 2022 250/300 EXC TPI (3214421en), PDF p. 66 |
| S45 | kept | "(690 Enduro) – Remove bleeder screws briefly. Any excess pressure escapes from the interior of the fork." | KTM Owner's Manual 2010 690 Enduro / 690 Enduro R (3211511en), PDF p. 76 |
| S46 | kept | "Perform the shock absorber service." | KTM Owner's Manual 2022 250/300 EXC TPI (3214421en), PDF p. 53 |
| S47 | kept | "The shock absorber is filled with highly compressed nitrogen. – Please follow the description provided. (Your authorized KTM workshop will be glad to help.)" | KTM Owner's Manual 2022 250/300 EXC TPI (3214421en), PDF p. 55 |
| S48 | kept | "You can find the table on the underside of the seat. These adjustments should be understood as a guideline … Do not change the adjustments at random or by more than ± 40%" | KTM Owner's Manual 2010 690 Enduro / 690 Enduro R (3211511en), PDF p. 64 |
| S49 | kept | "The preload adjuster has 9 positions. The standard position is 4 when the index mark on the adjuster is aligned with the left end of the rear shock absorber lower mounting bolt." | Honda CB500F/CB500FA Owner's Manual, PDF p. 92 |
| S50 | kept | "Turn adjusting screw1 clockwise with a screwdriver as far as the last perceptible click. … – Turn counterclockwise by the number of clicks" | KTM Owner's Manual 2022 250/300 EXC TPI (3214421en), PDF p. 56 |
| D44 | kept | "Pull the chain at the end of the chain sliding piece upward to measure chain tensionA. Info Lower chain section1 must be taut." (the item leaves out this page's lift-stand condition: defect 3) | KTM Owner's Manual 2022 250/300 EXC TPI (3214421en), PDF p. 90 |
| D45 | kept | "If the slack is not constant at all points, some links may be kinked and binding. … 2. Place your motorcycle on its side stand … 3. Check the slack in the lower half of the drive chain midway between the sprockets." | Honda CB500F/CB500FA Owner's Manual, PDF p. 80 |
| D46 | kept | "Chain deflection 30...40 mm (Motorcycle with no weight applied, supported on its side stand)" (the item's "once" is defect 4) | BMW Rider's Manual F800R, PDF p. 101 |
| D47 | kept | "Drive belt • Check belt condition. • Replace if damaged. • Check belt tension. • Adjust if necessary. √ Every 2500 mi (4000 km)" (rendered: √ at the initial 600 mi, then every 2500 mi) | Yamaha XVS95CL/XVS95CLC Owner's Manual, PDF p. 48 |
| D48 | kept | "5. If the drive belt slack is incorrect, have a Yamaha dealer adjust it." | Yamaha XVS13AF/XVS13AFC Owner's Manual, PDF p. 65 |
| D49 | kept | "Viscosity class at outside temperature: above 5 °C SAE 90 below 5 °C SAE 80 alternatively SAE 80 W 90" | BMW Service and Technical Booklet R 1100 S, PDF p. 87 |
| D50 | kept | "Final drive approx. 0.25 l (to bottom edge of filler opening) Viscosity class EPX 90 alternatively SAE 90" | BMW Maintenance Instructions R 1150 R / R 850 R, PDF p. 67 |
| D51 | kept | "Final drive 0.25 l (to bottom edge of filler opening) Viscosity class Castrol EPX 90 or SAE 90" | BMW Maintenance Instructions K 1200 RS, PDF p. 70 |
| D52 | kept | "BP6-28199-13 XVS95CL XVS95CLC OWNER'S MANUAL" | Yamaha XVS95CL/XVS95CLC Owner's Manual, PDF p. 1 |
| D53 | kept | "3D8-28199-18 XVS13AF XVS13AFC OWNER'S MANUAL" | Yamaha XVS13AF/XVS13AFC Owner's Manual, PDF p. 1 |

**Round 2 result: 53 kept, 0 killed.** Every round-1 fix held. It found 8 wording defects in the corrected text, all fixed in `87566dd`. One was substantive: the brake item's diagnosis had the hub seat cleaned "before condemning the disc", but the Beverly replaces a disc over its run-out limit and repeats the test, and cleans the seat only when installing (PDF p. 196). The other seven:
- "not honing" removed;
- the KTM chain check's lift stand added (p. 89), and "neutral" scoped to the Honda;
- "once" removed from the F800R's check;
- the tube check widened to both tubes anywhere, never straightened (YW125Y p. 157);
- the KTM fork bleed cited to its before-every-trip list (p. 46);
- the CHF50's greased fork cited to pp. 226–227;
- the R 1200 GS quoted as written.

Five claims came from round 2's own quotes and are mechanically verified only: B62, D54, S51, S52, S53.

## Regression of record

Regression of record: 9415 passed, 0 failed, 0 skipped, 0 errors at `87566dd` (15 min 11 s wall, `python -m pytest -n auto --dist load`, exit 0)

The tree was clean at `87566dd`. The floor is 9415, and 9,415 were collected. The log is `~/.cache/motodiag/regressions/87566dd_parallel_20260925_142827.log`.
