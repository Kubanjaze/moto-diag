# Phase 262 — Track N batch 3: crash support, track-day preparation, and emissions compliance — phase log

**Status:** 🚧 In progress
**Branch:** `phase-262` (Opus session, main checkout)

---

### 2026-09-26 — Opened: Track N batch 3

The operator's prompt, 2026-09-26: start Phase 262, Track N batch 3 of
3, and run it to its finish line. Batch 3 is rows 262 (crash and
insurance claim support), 263 (track-day and race prep) and 267
(emissions and smog compliance, California first). Then gate 272.

**Ledger convention, 261's and 264's, as the operator restated it.** 262
carries the batch. Rows 263 and 267 close ✅ "folded into 262" with no
CLOSED date. One history row (262) and one handoff.

**Also in scope, in the same migration** (the operator's words):
1. "F161: generic_winterization_v1's four live items carry figures no
   maker's document supports … Remove each unsupported figure or replace
   it with a pointer to the cited winterization_v1."
2. "F162: fix the two further defects the batch-2 reviewers found in
   ppi_chassis_v1."
3. "W30: the one claim added in batch 2's third refute round that has had
   no adversarial read. Give it one, and fix or drop it on the verdict."

**The operator's stop, recorded as given:** "Items 1 and 2 alter
existing live rows, which is a rule-1 stop: back up to ~/backups/motodiag/
first and keep 5; dry-run on a copy; run the F158 census on the copy;
show me every changed row with before and after text, and wait for my
answer before the live apply." No pre-approval of the live apply exists.

**The operator's Step 0 condition:** "If Step 0 finds a row that cannot
be sourced from primary documents, stop and give me the options. Row 262
especially may not be a manual topic."

**Carried forward** (the operator's list): F124, and migration tests that
survive the next migration; no test reads `data/motodiag.db`; no internal
references in any text a user sees (F158); whitespace-proof negatives
with a control on the cited page; names from title pages; the Edit tool
for source edits, and nothing in `/tmp`; and batch 2's lesson: "every
refute round's fixes introduced defects the next round found. After the
last fix round, re-read every claim whose text changed." Regression by
`.claude/skills/closeout/regression.sh`.

Read before acting: CLAUDE.md and the working-rules index; ROADMAP rows
258–272 and the status key; `ROADMAP_AUTHORITY.md`; the newest handoff
(`2026-09-26_264_closed.md`, named by `git log`); F161 and F162 in
`docs/FOLLOWUPS.md`; 264's implementation, phase log and Step 0; F158.

Branch `phase-262` from `master` at `1c836ee`. **Ledger step:** row 262 →
🚧 (65 words by `roadmap_words.py`). The row went in after the first
library census had run, not before it: a lapse against CLAUDE.md's "a
row before its Step 0", recorded here. The census changed nothing on
disk.

### 2026-09-26 — Step 0: the fork the operator anticipated, and the answer

The measurements are in `262_step0.md`. In short:
- **The three categories exist** (`CRASH_SUPPORT`, `TRACK_PREP`,
  `EMISSIONS`); the batch is one content migration (071) plus tests, with
  no new module.
- **Row 262 is partly a manual topic.** Makers cover a post-crash
  inspection, replacing bent parts, and runout limits. No document gives
  photo standards, damage estimation, insurance claims, salvage rules or
  a frame measurement (N8, N9).
- **Row 263's named subjects are mostly the sanctioning body's**: safety
  wire (N10), race coolant (N11), tech inspection and race numbers (N12).
  The makers cover track set-up.
- **No California regulator text was held.**

That is the operator's stop condition. The options went to the operator
with the evidence. **The operator's answers, verbatim:**
- Row 262: "Post-crash + CA salvage law (Recommended)"
- Row 263: "Makers' track prep (Recommended)"
- Row 267: "Fetch official CA + federal text (Recommended)"
- Provenance: "In the text (Recommended)"

**Acquisition (S0-8).** 13 regulator documents were fetched by
`acquire.py`'s own Fetcher and `save()` into
`~/research/motodiag/acquired/Regulation/`, with sidecars. That is 12 in
the first run, EPA's alert refused with a 403, and one DMV page (revived
salvage) in a second run, with its referrer recorded. leginfo's
robots.txt disallows every agent, and the eCFR API is disallowed, so
neither is fetched. Two leginfo sections had been opened by hand with
`curl` before the robots rule was read; nothing from them is saved or
cited.

**Rule 2 ran on its primary route.** The sandbox was proven by planted
writes (repository, library, scratchpad refused; the clone accepted).
Three Subconscious GLM-5.3 calls, one per row:

| packet | pages | facts | quotes on their page | turns | tokens | time |
|---|---|---|---|---|---|---|
| crash (262) | 147 | 122 | 80 | 3 | 417,103 | 177 s |
| track (263) | 256 | 99 | 78 | 5 | 682,063 | 335 s |
| emissions (267) | 286 | 104 | 92 | 4 | 573,777 | 307 s |

**The crash call invented quotes.** All 10 of its KTM 2022 EXC TPI quotes
are on no page. One gives the KTM 950 Super Enduro R's handlebar sentence
(its OM p. 27) to the EXC TPI's p. 63. Nothing from the model is used
unchecked: facts are nominations, and Opus takes every figure from the
page.

**The F158 census on a live copy, before 071:** 79 hits in 47 rows, 0 in
any workflow row. The control, "Phase 999" planted on a copy, was found
exactly once.

### 2026-09-26 — v1.0 committed; build: migration 071, three templates, two fixes, 30 tests

v1.0 committed and pushed as `7b59818`, before any code.

What was built (`940677d`):
- **Migration 071 `crash_track_emissions_workflows`** (schema 70 → 71):
  - `crash_support_v1`: 8 items, all powertrains; items 7 (the claim
    record) and 8 (California) optional;
  - `track_prep_v1`: 6 items, ICE and hybrid; item 4 (rider aids)
    optional;
  - `emissions_v1`: 7 items, ICE and hybrid; item 6 (the evaporative
    system) optional.
- **F161**: three `UPDATE`s on `generic_winterization_v1`'s items 1–3,
  each keyed on its exact old text. "Sta-Bil", "Run engine 5 minutes",
  "(typically 10W-40)" and "(13.2V-13.6V)" become pointers to
  `winterization_v1`. The titles and item 4 are unchanged.
- **F162**: one `UPDATE` on the chassis steering item, keyed on both old
  substrings: "checks the same movement for binding or looseness (PDF
  p. 93)", and "the KTM 2022 250/300 EXC TPI owner's manual (PDF p. 76)".
- The rollback deletes the new rows and restores every changed field
  verbatim, keyed on the new text.
- **Claims before text** (`s0/claims262.py`): 92 claims, 204 verbatim
  anchors, all on their pages. The checker was seen to fail on a wrong
  page and on corrupted figures, on a manual page and on a regulator
  page.
- **The cross-check** (`s0/xcheck262.py`): 104 cited PDF pages and 9
  regulator-page citations in the seeded text, 0 unclaimed. Its
  control, withdrawing C17, turned exactly the two p. 34 citations red.
- **30 tests** in `tests/test_phase262_crash_track_emissions.py`. Three
  failed at first run, all test-authoring or length errors, not content:
  two pin needles carried a parenthesis the combined citations do not
  have. Two titles were long enough that `workflow show` wrapped them at
  80 columns; they were shortened ("The claim record — no photo or claim
  standard in the library"; "Safety wire, coolant, inspection and race
  numbers — the event's rules").
- **Two existing pins moved with the phase's own changes:**
  - `test_phase259_ppi_engine.py::test_workflow_list_empty_category_fails_loudly`
    used `track_prep` as the empty category, which 071 fills. It now
    finds an empty category at run time, so the next content phase cannot
    turn it red.
  - `test_phase264_seasonal_breakin_valve.py::test_chassis_items_name_the_yw125y`
    pinned "the YW125Y service manual calls". It now pins F162's
    sentence.
- **Floor** 9446 → 9476 (+30, this file only; `--collect-only -q -p
  no:xdist` measured 9,476).

**Known-bad controls**, each planted with the Edit tool, run with
`__pycache__` cleared and `-B`, seen red, and reverted:

| # | plant | red tests |
|---|---|---|
| 1 | "frame twist under 2 mm" in the frame item | `test_no_frame_measurement_is_invented` |
| 2 | CHF50 axle 0.20 → 0.25 mm | `test_every_pinned_figure_is_in_its_field`, `test_figures_sit_beside_their_machine` |
| 3 | "(Phase 999)" in the emissions description | `test_all_three_templates_are_clean` |
| 4 | F161's oil `UPDATE` keyed on "10W-30" (a silent no-op) | the upgrade-scope test and both F161 tests |
| 5 | `emissions_v1` dropped from the rollback's template `DELETE` | both round-trip tests; the rollback-presence guard stayed green, as in 261 and 264 |
| 6 | an extra `UPDATE` of a `tire_service_v1` item inside 071 | the upgrade-scope test and the round trip |
| 7 | "coolant drained to water only" in the event-rules item | `test_no_race_rule_is_invented` |

After the reverts, none of the plant strings is in the file, and the
file passes 30/30.

**Whole-tree gates before the build commit:** rule 3's four, plus the
F124 guard, 240c, 209B, 244U, 244Y, 244V, 355, the floor, and the 114,
259, 260, 261, 264 and 262 files: **544 passed** (`-n auto`).
`finding_check` exit 0; `check(phase_docs="docs/phases/in_progress")`
returns [].

## Refuter pass

**Round 1 — 2026-09-26.** Four fresh-context Opus refuters in parallel: one
per template, and one for F161, F162 and W30 (W30's first adversarial
read). Every cited page was opened, and pages with a doubtful text layer
were rendered: BAR pp. 9–10, Kymco p. 35, the KTM EXC TPI service
schedule, BMW S 1000 R pp. 78–82, Beverly pp. 77–79 and the title pages
without a text layer. Full verdict files, with every item-text defect and
its replacement, are in the session scratchpad at `s0/refute/*_verdict.md`;
the claim rows below are as the refuters wrote them.

| claim | verdict | quote | source |
|---|---|---|---|
| C1 | kept | "If you decide to continue riding, first turn the ignition switch to the OFF position, and evaluate the condition of your motorcycle. Inspect for fluid leaks, check the tightness of critical nuts and bolts, and check the handlebar, control levers, brakes, and wheels. Ride slowly and cautiously." | Honda CB500F/FA 2018 owner's manual p. 9 |
| C2 | kept (CB500F/FA only; the template states it for any machine, see defect 2) | "A banking (lean angle) sensor automatically stops the engine and fuel pump if the motorcycle falls over. To reset the sensor, you must turn the ignition switch to the OFF position and back to the ON position before the engine can be restarted." | Honda CB500F/FA 2018 owner's manual p. 113 |
| C3 | kept | "A fall can damage the vehicle more seriously than it may first appear. – Check the vehicle after a fall as you do when preparing for use." | KTM 1290 Super Duke R / RR 2023 owner's manual p. 83 |
| C4 | kept | "OWNER'S MANUAL2023 1290 SUPER DUKE R 1290 SUPER DUKE RR" | KTM 1290 Super Duke R / RR 2023 owner's manual p. 1 |
| C5 | kept | "After a fall, check the vehicle as usual before putting it into operation." | KTM 690 Enduro / Enduro R 2010 owner's manual p. 53 |
| C6 | kept | "A bent handlebar must always be replaced. Never try to straighten the handlebar because this will cause it to lose its stability." | KTM 950 Super Enduro R 2008 owner's manual p. 27 |
| C7 | kept | "950 SUPER ENDURO R" … "OWNER’S MANUAL2008" | KTM 950 Super Enduro R 2008 owner's manual p. 1 |
| C8 | kept | "If the handlebar is bent or straightened, the material becomes fatigued. The handlebar may break as a result. – Change the handlebar if the handlebar is damaged or bent." | KTM 1290 Super Duke R / RR 2023 owner's manual p. 65 |
| C9 | kept | "Bends/cracks/damage J Replace. WARNING Do not attempt to straighten a bent handlebar as this may dangerously weaken it." | Yamaha YW125Y 2009 service manual p. 165 |
| C10 | kept | "Reusing a damaged or abnormally bent or kinked throttle cable can prevent proper throttle valve operation and may lead to a loss of throttle control while riding." | Honda PCX150 2013–2017 service manual p. 78 |
| C11 | kept | "Check the frame for damage, cracks, and deformation. » If the frame shows signs of damage, cracks, or deformation: – Change the frame. Guideline Repairs on the frame are not permitted." | KTM 2022 250/300 EXC TPI (and XC-W TPI) owner's manual p. 94 |
| C12 | kept (cover also lists 250/300 XC-W TPI, Six Days and Erzbergrodeo) | "OWNER'S MANUAL2022 250 EXC TPI 250 EXC SIX DAYS TPI 250 XC‑W TPI 300 EXC TPI" | KTM 2022 250/300 EXC TPI owner's manual p. 1 |
| C13 | kept | "Either wheel wobbles … Bent frame The scooter pulls to one side … Bent fork • Bent axle • Bent frame" | Honda CHF50/P/S Metropolitan 2002–2006 service manual p. 318 |
| C14 | kept (render confirms "Bent frame" sits under this heading) | "Steers to one side or does not track straight • Bent front axle … • Bent fork • Worn or damaged engine mounting bushings • Bent frame" | Honda PCX150 2013–2017 service manual p. 325 |
| C15 | kept | "UNSTABLE HANDLING … Frame 8Bent frame 8Damaged steering head pipe" | Yamaha YW125Y 2009 service manual p. 335 |
| C16 | kept | "inner tube 1 8outer tube 2 Bends/damage/scratches J Replace. WARNING Do not attempt to straighten a bent inner tube as this may dangerously weaken it." | Yamaha YW125Y 2009 service manual p. 157 |
| C17 | kept | "Inner tube bending limit … 0.2mm (0.008in)" | Yamaha YW125Y 2009 service manual p. 34 |
| C18 | kept (chart headings only: on the rendered page the symptom rows are "Steering handlebar pulls to one side" and "Suspension is too hard"; see defect 6) | "Steering handlebar pulls to one side … ②Bent front fork" / "Suspension is too hard … ①Bent fork tube or shock rod" | Kymco People / People S 250 service manual p. 35 |
| C19 | kept (FRONT axle) | "FRONT WHEEL … INSPECTION AXLE Place the axle in V-blocks and measure the runout. Actual runout is 1 /2 the total indicator reading. SERVICE LIMIT: 0 . 20 mm (0.008 in)" | Honda CHF50/P/S Metropolitan 2002–2006 service manual p. 218 |
| C20 | kept (front wheel; halving applies to the rim too) | "Spin the wheel slowly a nd r e ad the r u n o ut u s i ng a dial indicator. Actual runout is 1/2 the total indicator reading. SERVICE LIMITS: Radial: 2 .0 mm (0.08 in) Axial: 2 . 0 mm (0.08 in)" | Honda CHF50/P/S Metropolitan 2002–2006 service manual p. 219 |
| C21 | kept (FRONT axle) | "Place the axle on V-blocks and measure the runout with a dial indicator. SERVICE LIMIT: 0.2 mm (0.01 in) Actual runout is 1/2 of the total indicator reading." | Honda PCX150 2013–2017 service manual p. 326 |
| C22 | kept (rear wheel) | "Check the wheel rim runout using dial indicators. Actual runout is 1/2 the total indicator readings. SERVICE LIMITS: Radial: 2.0 mm (0.08 in) Axial: 2.0 mm (0.08 in)" | Honda PCX150 2013–2017 service manual p. 355 |
| C23 | kept (front wheel) | "Roll the wheel axle on a flat surface. Bends J Replace. Wheel axle bending limit 0.25mm (0.01in) WARNING Do not attempt to straighten a bent wheel axle." … "Radial wheel runout limit 1.0mm (0.04in) Lateral wheel runout limit 1.0mm (0.04in)" | Yamaha YW125Y 2009 service manual p. 117 |
| C24 | kept (FRONT axle) | "Set the axle in V blocks and measure the runout using a dial gauge. The actual runout is ½ of the total indicator reading. Service Limit: 0.2mm replace if over" | Kymco People / People S 250 service manual p. 187 |
| C25 | kept (front wheel) | "WHEEL RIM Check the wheel rim runout. Service Limits: Radial: 2.0mm replace if over A x i a l: 2.0mm replace if over" | Kymco People / People S 250 service manual p. 188 |
| C26 | kept | "Total Loss Salvage Vehicle (VC §544) —A vehicle that has been wrecked, destroyed, or damaged, to the extent that the owner or insurance company considers it uneconomical to repair and, because of this, the vehicle is not repaired for the owner. A salvage certificate is issued instead of an ownership certificate for a total loss salvage vehicle and becomes the ownership document." | California DMV, Vehicle Industry Registration Procedures Manual 19.015 Definitions p. 1 |
| C27 | kept | "Nonrepairable Vehicle (VC §431) —A vehicle that meets one of the following criteria and has no resale value except as a source of parts or scrap metal: Surgical Strip —A vehicle completely stripped when recovered from theft. Complete Burn —A completely burned vehicle. Owner Declared —A vehicle irreversibly designated by the owner solely as a source of parts or scrap metal. Once declared nonrepairable, the vehicle cannot be titled or reregistered." | California DMV, 19.015 Definitions p. 1 |
| C28 | kept | "Owner Retained Total Loss Salvage or Nonrepairable Vehicle (VC §§11515 and 11515.2) —A total loss salvage or nonrepairable vehicle that the owner retains as a portion of the settlement with an insurance company." | California DMV, 19.015 Definitions p. 1 |
| C29 | kept | "19.075 Salvage Certificate (VC §11515) The insurance company or its designee (salvage pool or registration service) or the owner must apply for the salvage certificate within 10 days from the date the insurance company makes a total loss settlement with the owner." | California DMV, 19.075 Salvage Certificate p. 1 |
| C30 | kept | "If you have a total loss salvage vehicle, and you do not receive an insurance settlement, then you (as the vehicle owner) are responsible for getting the certificate." | California DMV, Total Loss Salvage & Non-Repairable Vehicles p. 1 |
| C31 | kept (the three documents are under the Revived Salvage heading, not only the Revived Junk one; the list also has proof of ownership and fees, so "among" is right) | "A Revived Salvage Vehicle is a vehicle previously reported to DMV as a total loss by the owner or insurance company, but has been rebuilt and restored to operational condition. If your total loss/salvage vehicle has been revived, you must register the vehicle again. To register your Revived Salvage Vehicle, you will need: A completed Application for Title or Registration (REG 343) (PDF) form … A Verification of Vehicle (REG 31) (PDF) form or CHP Certificate of Inspection (CHP 97C) form. An electronic Vehicle Safety Systems Inspection (VSSI) certificate." | California DMV, Junk/Revived Salvage Vehicles p. 1 |
| N8 | kept (qualified) | 0 pages for `framedimension`, `framealign`, `framestraight\|straightness`, `measur…frame\|framemeasur`, `chassisdimension\|chassismeasur`, `straighten…frame`; the 9 hits for `frame…(limit\|tolerance\|servicelimit\|specification)` are all Piaggio "Frame and suspensions / Specification" tables that describe the chassis type, e.g. "Type of chassis Welded tubular steel chassis with stamped sheet reinforce-ments." Controls on the same vocabulary: `bentframe` finds 4 pages (CHF50 pp. 217, 318; PCX150 p. 325; YW125Y p. 335); `repairs?ontheframe` finds 4 KTM manuals. Caveat: caster/trail figures appear in spec tables in 64 files (e.g. CB500F/FA p. 133). They are specifications, not a frame check. | whole library (260 files) + 13 regulator pages; control: Honda PCX150 service manual p. 325 |
| N9 | kept (qualified) | Census: `insuranceclaim\|claimform\|fileaclaim\|claimprocedure\|claimsprocess` finds 1 page, a recall warranty "claim procedure" (NHTSA 07V253 remedy p. 10); `photograph…(damage\|vehicle\|document)\|documentthedamage\|takepictures\|takephotos\|recordthedamage\|damagereport\|accidentreport` finds 2 pages, neither a damage-photo standard (NHTSA 14V364 Part 573 p. 2 recall form; fly125 p. 80 workshop step); `damageestimat\|repairestimat\|appraisal\|appraiser\|insuranceadjuster\|claimsadjuster` finds 2 pages, both BAR: "In accordance with B&P section 9884.9 and CCR section 3353, prepare an estimate for the specific work needed to bring the vehicle into compliance." That is a regulator's repair-estimate rule, but it is written for Smog Check repairs, not for damage estimating (see defect 7). Control: `insurance` finds 37 pages. | whole library + regulator pages; BAR Smog Check Reference Guide 2025 p. 32 |
| T1 | kept | "KTM sport motorcycles are designed and constructed to meet the normal demands of regular road and race track operation, but not for use on dirt roads." … "Using the motorcycle in extreme conditions such as racing can lead to above-average wear to components such as the power train or brakes. For this reason, it may be necessary to service or replace worn parts before the limit specified in the service schedule is reached." | KTM 2010 1190 RC8 USA OM p. 10 |
| T2 | kept | "OWNER'S MANUAL 2010 1190 RC8 USA" | KTM 2010 1190 RC8 USA OM p. 1 |
| T3 | kept (qualified: the two anchors come from two different model blocks) | "(All EXC models) … The derestricted version of this vehicle must only be operated in closed off areas away from public highway traffic." / "(All XC‑W models) … This vehicle is not approved for use on public roads." | KTM 2022 250/300 EXC TPI OM p. 9 |
| T4 | kept (qualified: it is the U.S. limited warranty) | "YAMAHA MOTOR CORPORATION, U.S.A. 2020 AND LATER MODEL STREET & DUAL-PURPOSE MOTORCYCLE LIMITED WARRANTY" … "GENERAL EXCLUSIONS from this warranty shall include any failures caused by: Competition or racing use." | Yamaha YZFR1T1/YZFR1MT OM p. 135 |
| T5 | kept | "YZFR1T1/YZFR1T1C YZFR1MT/YZFR1MTC" | Yamaha YZFR1T1/YZFR1MT OM p. 1 |
| T6 | kept | "On the race track … Removing/installing mirrors … Removing and installing number- plate carrier … Removing and installing front turn indicators" | BMW S 1000 R RM p. 65 |
| T7 | kept | "Rider's Manual S 1000 R" | BMW S 1000 R RM p. 1 |
| T8 | kept (qualified: joining compound omitted) | "When removing the right mirror, make sure that the brake-fluid reservoir remains cor- rectly secured." … "Locknut (mirror) to clamping piece Joining compound: Multi-wax spray 20 Nm" | BMW S 1000 R RM p. 85 |
| T9 | kept | "If the number-plate carrier is removed in preparation for a race-track session, the elec- tronics detect a bulb failure and the appropriate warning appears on the display. Activating the EQIPWARNLAMP function in theSETUPMENU suppresses this warning." | BMW S 1000 R RM p. 86 |
| T10 | kept | "before the motorcycle is ridden on public roads the warning has to be reactivated by selecting the EQIPWARNLAMP function in theSETUPMENU" … "Protect the plug on the motor- cycle to prevent the ingress of foreign matter." | BMW S 1000 R RM p. 88 |
| T11 | kept (qualified: the measuring procedure on this page is the REAR wheel's) | "Front spring preload has to be adjusted to suit the rider's weight." … "Adjusting spring preload for rear wheel … measure distance D between points 1 and 2 again and calculate the difference (negative spring displacement) between the two readings." | BMW S 1000 R RM p. 78 |
| T12 | kept (qualified: the front figure sits in the "with Dynamic Damping Control OE" procedure begun on p. 80) | "Negative spring displacement of front wheel 6...10 mm (With rider 85 kg)" … "An increase in spring preload requires firmer damping, a re- duction in spring preload re- quires softer damping." | BMW S 1000 R RM p. 81 (heading "Adjusting spring preload for front wheel – with Dynamic Damping Control OE", p. 80) |
| T13 | kept | "Compression stage, ba- sic setting, front Position 1 (comfortable setting with rider 85 kg) Position 3 (normal setting with rider 85 kg) Position 7 (sports setting with rider 85 kg)" | BMW S 1000 R RM p. 82 |
| T14 | kept (qualified: both figures are the rear shock absorber's) | "11.7 Checking the static sag of the shock absorber … Static sag 37 mm (1.46 in)" … "11.8 Checking the riding sag of the shock absorber … Riding sag 110 mm (4.33 in)" | KTM 2022 250/300 EXC TPI OM p. 58 |
| T15 | kept (qualified: the page gives the weight band) | "As delivered, KTM offroad motorcycles are adjusted for an average rider's weight (with full protective clothing). Guideline Standard rider weight 75 … 85 kg (165 … 187 lb.)" | KTM 2022 250/300 EXC TPI OM p. 55 |
| T16 | killed (as attributed to the YZFR1T1/YZFR1MT manual without variant: ERS is the YZF-R1M's only) | "ERS (YZF-R1M)" (section heading, p. 41) … "M -1 is preset for track use with racing slick tires." (p. 42) | Yamaha YZFR1T1/YZFR1MT OM p. 41–42 |
| T17 | kept (qualified: optional equipment) | "Pro riding modesOE DYNAMIC PRO The DYNAMIC PRO mode can- not be activated unless the cod- ing plug is inserted." … "ABS control is not active at the rear wheel when the footbrake lever is pressed. Under these circumstances, the rear wheel can lock up." | BMW S 1000 R RM p. 107 |
| T18 | kept (qualified: optional equipment) | "with Dynamic Traction Control (DTC) OE DTC switched off … DTC assistance is deactivated. Any drifts are possible. Front-wheel lift detection is deactivated. Any wheelies are possible. There is a possibility of the motorcycle flipping over backwards." | BMW S 1000 XR RM p. 133 |
| T19 | kept | "Rider's Manual S 1000 XR" | BMW S 1000 XR RM p. 1 |
| T20 | kept | "LC S is intended for track use on closed circuit race tracks only." | Yamaha YZFR7T OM p. 23 |
| T21 | kept | "YZFR7T/YZFR7TC (R7)" | Yamaha YZFR7T OM p. 1 |
| T22 | kept | "The regular service intervals as stated apply to motorcycles used on public roads. In the case of motorcycles used for racing, the intervals have to be adap- ted accordingly in line with the increased wear and tear associ- ated with this mode of use." | BMW S 1000 R RM p. 175 |
| T23 | kept | "IF MOTORCYCLE IS USED FOR COMPETITION 7500 KM SERVICE SHOULD BE CARRIED OUT AFTER EVERY RACE!" | KTM 2008 950 Super Enduro R OM p. 30 (repeated p. 31) |
| T24 | kept for the two headers; the anchor "Change the front brake fluid" is killed as a motorsport item | "Every 10 operating hours when used for motorsports" (header of 10.2 Required work, continued on this page, and of 10.3) … "10.3 Recommended work Every 40 operating hours when used for motorsports" … "Change the front brake fluid." (render: its two marks are in the "every 12 months" and "every 48 months" columns, none in either motorsport column) | KTM 2022 250/300 EXC TPI OM p. 53 |
| N10 | kept (qualified: the diagnosis sentence about it is wrong, see defect 11) | "Mount outside locking wire4. – Mount inside locking wire5. The pins of the locking wires engage in the drilled holes of the wheel axle." — a factory axle-nut retainer, not safety-wire/lockwire. Census: `safety-?wire` 0 pages; `lock-?wire` 1 page (control: Kymco Agility 50 p. 32 "disconnect the seat lock wire"); `lockingwire` 4 pages, all KTM 1290 Super Duke R/RR (pp. 127, 128, 129, 174) | KTM 2023 1290 Super Duke R/RR OM p. 129 |
| N11 | kept | No race/track coolant anywhere. Census `(coolant|antifreeze).{0,200}(racing|racetrack|race-track|competition|motorsport|trackuse)` and reverse: 6 pages, none prescribes a coolant for racing (service-table headers and a "Racing Bio" air-filter oil). Control: `coolant` 1,674 pages / 134 files; `purewater|plainwater|glycol-?free|waterwetter…` 15 pages, e.g. "Do not use pure water as only coolant is able to meet the requirements needed in terms of corrosion protec- tion and lubrication properties." | KTM 2022 250/300 EXC TPI OM p. 170 (control) |
| N12 | kept | Census `technicalinspection|techinspection|scrutineer|scrutini[sz]` 2 pages (BMW K 1200 RS and R_0428 warranty booklets p. 4, a parts/accessories-approval note: "Nor is approval by an official technical inspection authority … or a certif- icate issued by the tyre manufacturer necessarily a suf- ficient guarantee"); `racenumber|startnumber|competitionnumber|numberboard|numberplate.{0,60}(race|racing|competition)` 0 pages. Control: `number-?platecarrier` 17 pages / 8 files | BMW K 1200 RS WA p. 4 |
| E1 | kept | "1.1.5 Exempted Vehicles … • Motorcycles. … H&S §§ 44011, 44011(a)(6), VC § 4000.1, CCR §§ 3340.5, 3340.42" | BAR Smog Check Reference Guide 2025 p. 9 |
| E2 | kept (confirmed by render: x in "Smog Check Required None") | "Table 1: Smog Check Requirements by Vehicle Type" / "Motorcycle All All All x N/A N/A N/A" | BAR Smog Check Reference Guide 2025 p. 10 |
| E3 | kept | "Smog Check Reference Guide 2025 11/21/2025" | BAR Smog Check Reference Guide 2025 p. 1 |
| E4 | kept | "In order for an On-Road Motorcycle (ONMC) to be introduced into commerce in California for use on public roads, the California Air Resources Board (CARB) must first issue an Executive Order for the particular make, model, and model year, certifying that it has met the applicable emission standards." | CARB "ONMC - Executive Order Introduction" p. 1 |
| E5 | kept (text drops "when operated and maintained according to the instructions provided", defect 15) | "CARB also requires that your motorcycle comply with applicable evaporative emission requirements during its useful life, when operated and maintained according to the instructions provided." / "The Vehicle Emission Control Information label is located on the left side of the swingarm." | Honda CB500F/FA 2018 OM p. 121 |
| E6 | kept | "50 STATE versions of this motorcycle are equipped with an evaporative emission control system. (P.104)" | Honda XR650L 2018 OM p. 32 |
| E7 | kept | "The Vehicle Emission Control Information label is attached to the rear fender." | Honda XR650L 2018 OM p. 109 |
| E8 | kept (a code table; it does not identify a given machine, defect 5) | "DESTINATION CODE REGION AC 50 state (meets California) CM Canada" | Honda PCX150 2013–2017 SM p. 8 |
| E9 | kept | "Vehicle Code section 27156 (VC 27156) , California's anti-tampering law, prohibits the installation of any add-on or modified emission-related part on any pollution-controlled motorcycles, unless the part has been exempted by CARB." | CARB "Aftermarket Motorcycle Parts" p. 1 |
| E10 | kept (the page's exhaust note for non-catalyst motorcycles is omitted, defect 8) | "Some examples are fuel injection systems, re-jetting of carburetors, aftermarket catalytic converters, performance camshafts, and gear sprockets." | CARB "Aftermarket Motorcycle Parts" p. 1 |
| E11 | kept | "The label should indicate the manufacturer's name, device name and a valid E.O. number assigned by CARB. The format of the E.O. number is D-XXX-XXX" | CARB "Aftermarket Motorcycle Parts" p. 1 |
| E12 | kept (the sentence sits in Appendix D, Engine Change Guidelines) | "One such law is California Vehicle Code Section 27156 which states that no person shall disconnect, modify, or alter any required motor vehicle pollution control device." | BAR Smog Check Reference Guide 2025 p. 45 |
| E13 | kept (a Smog Check program glossary term, Appendix A, defect 10) | "Tampered - Any emission control component which is missing, modified or disconnected." | BAR Smog Check Reference Guide 2025 p. 41 |
| E14 | kept | "Tampering with these components to reduce or defeat the effectiveness of the fuel permeation technologies is prohibited." / "TAMPERING WITH THE NOISE CONTROL SYSTEM IS PROHIBITED: U. S. federal law prohibits" | Honda CB500F/FA 2018 OM p. 123 |
| E33 | kept | "The exhaust system contains one or more catalytic converters." | Honda CB500F/FA 2018 OM p. 122 |
| E15 | kept (the list continues the noise-control heading from p. 123; the text does say "noise-control section") | "AMONG THOSE ACTS PRESUMED TO CONSTITUTE TAMPERING ARE THE FOLLOWING ACTS: ● Removal of, or puncturing the muffler, baffles, header pipes or any other component which conducts exhaust gases. … ● Removing or disabling any emissions compliance component, or replacing any compliance component with a noncompliant component." | Honda CB500F/FA 2018 OM p. 124 |
| E16 | kept (the text drops "up to", "As of January 13, 2020" and "enforcement discretion", defects 2, 3 and 7) | "the statutory civil penalties are $48, 192 per violative vehicle or engine for manufacturers and dealers and $4,819 per violative vehicle or engine or defeat device for any person other than a manufacturer or dealer." | EPA fact sheet, March 2020, p. 2 |
| E17 | kept | "FACT SHEET Clean Air Act Vehicle Aftermarket Defeat Devices and Tampering March 2020 U.S. Environmental Protection Agency" | EPA fact sheet, March 2020, p. 1 |
| E18 | kept (the text drops the paragraph's third sentence, defect 4) | "Any additional or modified component that is deemed exempt from the prohibitions of Section 27156 of the Vehicle Code by the Air Resources Board may be used on a vehicle or engine. Such use, in itself, will not constitute grounds for the rejection of a warranty application" | Vespa GTS 310 HPE (USA) OM p. 19 |
| E19 | kept | "Always use unleaded gasoline. Leaded gasoline will damage the catalytic converter." / "A replacement unit must be an original Honda part or equivalent." | Honda CB500F/FA 2018 OM p. 125 |
| E20 | kept | "Do not let the vehicle run completely out of fuel. This may cause damage to the catalytic converter." | Yamaha XTZ7T (Ténéré 700) OM p. 31 |
| E21 | kept (the title page also covers XTZ7TC) | "XTZ7T (Ténéré 700) XTZ7TC (Ténéré 700) … MOTORCYCLE OWNER'S MANUAL" | Yamaha XTZ7T (Ténéré 700) OM p. 1 |
| E22 | kept | "Use only unleaded gasoline. The use of leaded gasoline will cause unre- pairable damage to the catalytic converter." | Yamaha XC50J OM p. 25 |
| E23 | kept | "FLASHING MIL WARNING LIGHT: USING THE VEHICLE FOR A LONG TIME WITH THE MIL WARNING LIGHT FLASHING MAY DAMAGE THE CATALYST, THE ENGINE OR THE VEHICLE." | Vespa GTS 310 HPE (USA) OM p. 28 |
| E24 | kept | "TAMPERING WITH THE CATALYTIC SILENCER MAY CAUSE SEVERE DAMAGE TO THE ENGINE." | Vespa GTS 310 HPE (USA) OM p. 61 |
| E25 | kept | "Vespa Gts 310 HPE Ed: 02-05_2025 Cod. 1Q001103 (USA)" | Vespa GTS 310 HPE (USA) OM p. 1 |
| E26 | kept (the paragraph sits under "50 STATE (meets California)") | "Evaporative Emission Control System 50 STATE (meets California) An evaporative emissions control system uses a canister filled with charcoal to adsorb fuel vapor from the fuel tank while the engine is off." | Honda CB500F/FA 2018 OM p. 122 |
| E27 | kept | "Canister (for California) … Check each hose connection. … Check each hose and canister for cracks or damage. Replace if damaged. … Make sure that the canister breather is not blocked, and if necessary, clean it." | Yamaha XTZ7T (Ténéré 700) OM p. 79 |
| E28 | kept (the heading carries a condition the text drops, defect 13) | "EVAPORATIVE EMISSION CONTROL SYSTEM (EXCEPT AFTER '13 MODEL CM TYPE) This model complies with CARB evaporative emission requirements." / "No adjustment to the system should be made, although periodic inspection of the components is recommended." | Honda PCX150 2013–2017 SM p. 42 |
| E29 | kept (Yamaha's own warranty terms; the Vespa statement says the opposite, defect 1) | "Copies of work orders and/or receipts for parts purchased and installed on your vehicle will be required to document that maintenance has been completed in accordance with the emissions warranty. The chart below is printed only as a reminder that maintenance work is required. It is not acceptable proof of maintenance work." | Yamaha XTZ7T (Ténéré 700) OM p. 122 |
| E30 | kept | "Your warranty coverage is not voided if you perform your own maintenance. However, failures that occur due directly to improper maintenance are not covered by these warranties." | Honda CB500F/FA 2018 OM p. 128 |
| E31 | kept (marked "USA" on the page; misused as a fail criterion, defect 14) | "USA Maintenance, replacement or repair of the emission control devices and systems may be performed by any motorcycle repair establishment or individual using parts that are "certified" to EPA standards." | Honda CB500F/FA 2018 OM p. 45 |
| E32 | kept | "Class III motorcycles (280 cm³ and above): for a period of use of five (5) years or 30,000 kilometers (18,641 miles), whichever occurs first." | Vespa GTS 310 HPE (USA) OM p. 17 |
| W30 — Beverly: "if the vehicle is not used for some time (1 month or more) the battery needs periodic recharging, and runs down completely in the course of three months (PDF p. 78)" | kept (verbatim and on the page; context needs one clause, see Defect 1) | "IF THE VEHICLE IS NOT USED FOR SOME TIME (1 MONTH OR MORE) THE BATTERY NEEDS TO BE RECHARGED PERIODICALLY. THE BATTERY RUNS DOWN COMPLETELY IN THE COURSE OF THREE MONTHS." | Piaggio Beverly 125 service station manual (pdf/beverly125.pdf) p. 78 |
| W30 context — the section heading | kept: it is under "Sealed battery" (heading at the foot of p. 77; the next heading is "Pump electrics check" on p. 79) | "Sealed battery If the vehicle is provided with a sealed battery, the only maintenance required is the check of its charge and recharging, if necessary." | Beverly 125 p. 77 |
| W30 context — the same CAUTION box speaks of a battery that has an electrolyte level | kept (context; noted: the box is a boilerplate caution, not written for a sealed battery) | "CHARGE THE BATTERY BEFORE USE TO ENSURE OPTIMUM PERFORMANCE. INADEQUATE CHARGING OF THE BATTERY WITH A LOW ELECTROLYTE LEVEL BEFORE IT IS FIRST USED SHORTENS THE LIFE OF THE BATTERY." | Beverly 125 p. 78 |
| W30 context — the same words are generic Piaggio text | kept (context; noted: they are repeated in the troubleshooting table, worded for "a motorcycle") | "If the vehicle is not used for some time (1 month or more) the battery needs to be recharged periodically. The battery runs down completely in the course of 3 months. If the battery is fitted on a motorcycle, be careful not to invert the connections" | Beverly 125 p. 55 |
| W30 context — the Beverly's battery is sealed | kept: the only battery the spec names | "Battery Sealed, 12 V / 10 Ah" | Beverly 125 p. 9 |
| W30 — the six-month interval also cited in item 5 | kept (pp. 77–78 correct) | "These operations should be carried out before delivering the vehicle, and on a six-month basis while the vehicle is stored in open circuit." | Beverly 125 p. 78 |
| F162a — YW125Y "checks the same movement for binding or looseness (PDF p. 93)" | kept | "Grasp the bottom of the front fork legs and gently rock the front fork. Binding/looseness J Adjust the steering head." | Yamaha YW125Y 2009 service manual (pdf/yamaha_zuma125_2009_sm.pdf) p. 93 |
| F162a — YW125Y title | kept | "2009 MOTORCYCLE SERVICE MANUAL Model : YW125Y_" | yamaha_zuma125_2009_sm.pdf p. 1 |
| F162b — "KTM 2022 250/300 EXC TPI owner's manual (PDF p. 76)": "Play should not be detectable on the steering head bearing." | kept | "Play should not be detectable on the steering head bearing." | KTM 2022 OM (acquired/KTM/22_3214421_en_OM.pdf) p. 76 |
| F162b — title page | kept (the title also lists the XC-W TPI variants; "250/300 EXC TPI" is a fair short name) | "OWNER'S MANUAL2022 250 EXC TPI 250 EXC SIX DAYS TPI 250 XC‑W TPI 300 EXC TPI" | 22_3214421_en_OM.pdf p. 1 |
| F162b — the 2027 manual has the same sentence on the same PDF page | kept (context; noted: yes, identical sentence; its title names no "TPI" model, so naming the 2022 manual is what makes the citation unique) | "Play should not be detectable on the steering head bearing." / title "Owner's manual2027 250 XC-W 300 EXC" | acquired/KTM/27_3240387_en_BA.pdf p. 76 and p. 1 |
| F162 — "the KTM manual warns that running with play damages the bearing seats in the frame as well (PDF p. 76)" | kept | "If the vehicle is operated for a lengthy period with play in the steering head bearing, the bearings and the bearing seats in the frame can become damaged over time." | 22_3214421_en_OM.pdf p. 76 |
| F162 — "the KTM manual's standard is that play should not be detectable (PDF p. 76)"; "rock them to and fro in the direction of travel" | kept | "Move the handlebar to the straight-ahead position. Move the fork legs to and fro in the direction of travel." | 22_3214421_en_OM.pdf p. 76 |
| F162 — "they must move easily over the entire range with no detent position" (uncited, but the KTM text) | kept | "It must be possible to move the handlebar easily over the entire steering range. There should be no detectable detent positions." | 22_3214421_en_OM.pdf p. 76 |
| F162 — YW125Y lower ring nut 38 N·m initial, 14 N·m final (PDF p. 94) | kept | "Lower ring nut (initial tightening torque) 38Nm" … "Lower ring nut (final tightening torque) 14Nm" | yamaha_zuma125_2009_sm.pdf p. 94 |
| F162 — "A notch at the straight-ahead position is dented bearing races" / "freshly adjusted but unchanged bearings only hide the notch until the grease settles" | killed: no support; the KTM page adjusts first for a detent, and the "hide the notch" claim is found nowhere. Searched: `brinell` across the library, 0 pages; `(notch\|detent)…(straight\|steering\|bearing)`, 16 pages, all KTM "adjust … then check" text or unrelated | "» If detent positions are detected: – Adjust the steering head bearing play. (p. 74) – Check the steering head bearing and change if necessary." | 22_3214421_en_OM.pdf p. 76 |
| F162 — adjust first, then the bearings (the Yamaha agrees) | kept (context; noted) | "Check the steering head for looseness or binding by turning the front fork all the way in both directions. If any binding is felt, remove the lower bracket and check the upper and lower bearings." | yamaha_zuma125_2009_sm.pdf p. 94 |
| F162 — diagnosis "a notch at straight-ahead is brinelled races from an impact or years of load in one position" | killed: no support (same searches). The nearest support is the Beverly troubleshooting table, which names recessed seats or flattened balls only after the ring-nut adjustment has failed, and gives no cause | "If irregularities in turning the steering continue even after making the above adjustments, check the seats on which the ball bearings rotate: replace them if they are recessed or if the balls are flattened." | Beverly 125 p. 56 |
| F161-fuel — "a full tank with stabilizer and the engine run" | kept | "Fill up the fuel tank, adding fuel stabilizer according to product instructions. Run the engine for 5 minutes to distribute treated fuel through the fuel system." | Yamaha XVS95CL OM (library_om_contents_pdf_10_BP6-28199-13_02.pdf) p. 81 |
| F161-fuel — "a full tank with additive and no run" | kept (the page has no run step and warns against short runs) | "When refueling for the last time before taking the motorcycle out of service, add fuel additive." … "Fill the fuel tank completely as specified" … "Avoid running the engine for a short time only." | KTM 1290 Super Duke R/RR 2023 OM (23_3214761_en_OM.pdf) p. 157 |
| F161-fuel — "an empty tank" | kept | "Make sure the tank is as empty as possible so that you can fill up with fresh fuel when you put the motorcycle back into operation." | KTM 690 Enduro 2010 OM (10_3211511_en_OM.pdf) p. 172 |
| F161-fuel — "an empty tank" (second maker) | kept | "Drain the carburetor (if equipped) and empty the fuel tank into an approved gasoline container" | Kymco People S OM (PeopleS-50-125-200.pdf) p. 60 |
| F161-fuel — item 1 title "Add fuel stabilizer" | killed: an empty-tank maker adds none (Defect 2) | "Make sure the tank is as empty as possible" | KTM 690 Enduro 2010 OM p. 172 |
| F161-oil — "before storage" | kept | "Before laying the vehicle up out of use, have the engine oil and the oil filter element changed by a specialist workshop" | BMW F800R RM p. 124 |
| F161-oil — "before storage" (second maker) | kept | "Change the engine oil and filter, clean the oil screens." | KTM 690 Enduro 2010 OM p. 172 |
| F161-oil — "both" | kept, with a condition | "1. Change the engine oil and filter." (Storage) / "2. Change the engine oil if more than 1 month has passed since the start of storage." (Removal from storage) | Kymco People S OM p. 60 and p. 61 |
| F161-oil — "after it" as a maker's position on its own | killed: no maker checked changes the oil only after storage. winterization_v1 item 4 cites none. Searched: the five named pages, plus every "restoring to use" / "after storage" / "putting into operation after storage" section (`ctx.py`, 152 pages, BMW index and section hits). None has an after-only change | "Install a charged battery. Before starting: work through the checklist." (restoring to use: no oil step) | BMW F800R RM p. 124 |
| F161-oil — "Change engine oil and filter" as a universal step | killed for two-strokes: the KTM 2022 250/300 EXC TPI storage list changes the gear oil and adds 2-stroke oil. The Yamaha XVS95CL storage list names no oil change at all | "Change the gear oil." … "Add 2-stroke oil." | KTM 2022 OM (22_3214421_en_OM.pdf) p. 154 |
| F161-battery — "a charger the machine's maker allows" | kept (no maker in the library forbids a charger the maker approves) | "Confirm that the battery and its charger are compatible. Do not charge a VRLA battery with a conventional charger." | Yamaha XVS95CL OM p. 81 |
| F161-battery — "on a charger the maker allows" (a BMW charges through its socket) | kept | "With the battery connected to the vehicle's on-board electrical system, charge via the power socket." | BMW (manuals_…F_0K11_RM_1119_01.pdf) p. 182 |
| F161-battery — "or removed and recharged at the maker's interval" as the only other passing state | killed (incomplete): two makers leave the battery in place, disconnected, with no charger and no interval | "If you leave the battery in place, disconnect the negative - terminal to prevent discharge." | Honda CB500F 2018 OM (om_AHM_CB500F-FA_2018…pdf) p. 117 |
| F161-battery — second in-place case | killed (same) | "a trickle charger, which can be obtained from your BMW Motorrad dealer, should be connected or the battery disconnected and then recharged before starting riding again." | BMW K1200S RM (manuals_…K_0581_RM_0904_K1200S_01.pdf) p. 160 |
| F161-battery — expected_fail "Battery left disconnected with no maintenance" | killed: this is what the Honda CB500F manual prescribes when the battery stays in | "If you leave the battery in place, disconnect the negative - terminal to prevent discharge." | Honda CB500F 2018 OM p. 117 |
| F161 item 3 instruction (untouched) "Disconnect negative terminal, clean terminals, connect battery tender per manufacturer instructions" | killed: the makers give disconnecting and a charger as alternatives ("or"), not as one combined step, and "clean terminals" is in none of the storage pages checked | "If the motorcycle is to be out of use for more than four weeks, disconnect the battery or connect a suitable trickle charger to the battery." | BMW F800R RM p. 117 |
| F161 item 4 (untouched) "centerstand/jackstand to unload suspension" | killed: every maker checked lifts the machine to take the load off the tires (both wheels), and none mentions the suspension. A centerstand alone does not lift both wheels | "lift the vehicle so that all wheels are off the ground. Otherwise, turn the wheels a little once a month in order to prevent the tires from becoming degraded in one spot." | Yamaha XVS95CL OM p. 81 |
| F161 item 4 — both wheels (second and third makers) | kept (context; noted) | "Stand the motorcycle in a dry room in such a way that there is no load on either wheel." | BMW F800R RM p. 124 |
| F161 item 4 — both wheels (Honda) | kept (context; noted) | "Place your motorcycle on a maintenance stand and position a block so that both tires are off the ground." | Honda CB500F 2018 OM p. 117 |
| F161 item 4 — "cover with breathable cover" | kept | "Cover the motorcycle with a tarp or cover that is permeable to air." … "Do not use non-porous materials since they prevent humidity from escaping, thus causing corrosion." | KTM 1290 Super Duke R/RR 2023 OM p. 157 |
| F161 item 4 — expected_fail "plastic tarp cover" | kept (it is plastic that is excluded, not a tarp: KTM allows an air-permeable tarp) | "Cover the scooter (do not use plastic or other coated materials)" | Kymco People S OM p. 60 |
| F161 item 4 — expected_pass "weight off tires" | kept | "Place the scooter on blocks to raise both tires off the ground." | Kymco People S OM p. 60 |

**Round 1 result.**
- **Claims:** 91 of 92 kept (C1–C31, T1–T24 bar T16, E1–E33, and the
  fixes' rows). **T16 killed:** the Yamaha's ERS mode M-1 is under "ERS
  (YZF-R1M)" (p. 41), so it is the R1M's, not the whole manual's. The
  item now says so.
- **Negatives:** N8–N12 all kept on widened searches. N10's diagnosis
  sentence was false as worded ("its only lock wire is a seat lock
  wire"): the KTM 1290 Super Duke R / RR rear-axle locking wires (p. 129)
  are in the library too. The sentence now names them, as factory
  retainers, not a safety-wire procedure.
- **W30:** kept. The words are verbatim under the Beverly's "Sealed
  battery" heading. But they sit in a boilerplate caution box about a
  low electrolyte level before first use, and they repeat the
  troubleshooting table (p. 55). "The same manual says", placed after the
  six-month rule, made them read as a second interval for the same
  stored battery. **Fixed:** the sentence keeps its words and gains that
  context, and says the manual does not reconcile the two.
- **About 56 item-text defects, all in scope fixed**, each re-anchored
  as a new claim (C32–C47, T25–T43, E34–E44, W31–W32: 48 claims, 70
  anchors, all on their pages). The substantive ones:
  - crash: front-axle conditions and rear rims; the lean-angle sensor
    widened from the CB500F/FA to every machine; "the maker's rule" for a
    KTM-only rule; the Kymco chart's own rows; the surgical-strip
    condition; "a nonrepairable vehicle rebuilt", which the DMV does not
    forbid; the "insurance" negative, which KTM's ABS warning and EPA's
    sentence contradicted as worded;
  - track: T16; BMW's front sag only with Dynamic Damping Control
    (optional equipment); KTM's sag is the rear shock's, for 75 … 85 kg;
    the Yamaha warranty is the U.S. one; KTM's 790 DUKE "not suitable for
    use on race tracks" added; the road-mode step is now the makers' own
    (BMW pp. 106, 132);
  - emissions: EPA's penalty is "up to" and federal; EPA's "reasonable
    basis" is enforcement discretion; Vespa's California warranty may not
    be denied for missing receipts alone, which contradicted the
    Yamaha-derived fail criterion; Vespa's liability limit on exempted
    parts; CARB's exhaust note for non-catalyst machines; the E.O. must
    cover this machine; BAR's "tampered" is the Smog Check glossary's.
- **Declined, with reasons:**
  - the refuter's "M-2 for track use with street tires and M-3 for
    street use": p. 42 names "T-2" for track with street tires, and the
    M-2/M-3 presets are not stated there;
  - naming the CHF50 "CHF50/P/S Metropolitan" in every mention: the first
    mention in each item carries it, later ones say "CHF50", as 260 and
    264 do.

**Outside the scope: F163.** The fixes refuter also found defects in live
text 262 does not touch. They are recorded as F163, not changed: the
operator's scope for F161 is the unsupported figures, and for F162 the
two named defects. The replacements drafted from the pages:
- `generic_winterization_v1` item 1 title → "Fuel for storage".
- item 3 instruction → "Charge the battery fully, then do what the
  machine's own manual says: remove it, disconnect it in place, or keep
  it on a charger the maker allows. winterization_v1 gives each maker's
  step with its document and page."
- item 3 expected_fail → "Battery left connected with no charger, or left
  without the recharge its manual asks for."
- item 4 instruction → "Move to a dry storage place, lift the machine so
  that both wheels are off the ground (a stand, blocks or lifting gear,
  as its manual says; where it cannot be lifted, turn the wheels a little
  once a month), and cover it with a cover that is permeable to air,
  never plastic."
- `ppi_chassis_v1` steering item: the notch sentence → "A detent
  position means adjust the play, then check the bearing and change it
  if necessary (KTM, PDF p. 76)", dropping "only hide the notch until the
  grease settles"; the diagnosis → "a notch that survives adjustment
  means recessed bearing seats or flattened balls, to be replaced (Piaggio
  Beverly 125 service station manual, PDF p. 56)".
