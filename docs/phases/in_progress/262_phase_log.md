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

### Round 2 — 2026-09-26: the 48 claims round 1 added, and every sentence it changed

Two fresh-context Opus refuters, given a sentence-level diff of the text
before and after round 1 (`s0/refute/round1_changed_sentences.md`: 40
crash, 44 track, 51 emissions, 5 generic winterization and the W30 item).
Both were cut off once by a network outage (the API host unreachable)
before writing anything; both were resumed with their context and
finished. Verdict files: `s0/refute/r2_*_verdict.md`.

| claim | verdict | quote | source |
|---|---|---|---|
| C32 | kept | "REAR WHEEL INSPECTION Check the wheel rim runout using dial indicators. Actual runout is 1 /2 the total indicator readings. SERVICE LIMITS: Radial: 2 .0 mm (0.08 in) Axial: 2 . 0 mm (0.08 in)" | Honda CHF50/P/S Metropolitan 2002–2006 SM p. 242 |
| C33 | kept (no half-TIR note on this page; see defect 1) | "Measure the rear wheel rim runout. Service Limits: Radial: 2.0mm replace if over A x i a l: 2.0mm replace if over" | Kymco People / People S 250 SM p. 206 |
| C34 | kept | "WHEEL RIM … Actual runout is 1/2 the total indicator reading. SERVICE LIMIT: Axial: 2.0 mm (0.08 in) Radial: 2.0 mm (0.08 in)" | Honda PCX150 2013–2017 SM p. 326 (headed "FRONT WHEEL/SUSPENSION/STEERING") |
| C35 | kept | "FRONT WHEEL … INSPECTION AXLE Place the axle in V-blocks and measure the runout. Actual runout is 1 /2 the total indicator reading. SERVICE LIMIT: 0 . 20 mm" | Honda CHF50/P/S Metropolitan SM p. 218 |
| C36 | kept | "FRONT WHEEL … Remove the front axle to pull out the axle. … INSPECTION AXLE RUNOUT Set the axle in V blocks … The actual runout is ½ of the total indicator reading. Service Limit: 0.2mm replace if over" | Kymco People / People S 250 SM p. 187 |
| C37 | kept | "FRONT WHEEL AND BRAKE DISK … CHECKING THE FRONT WHEEL 1. Check: wheel axle Roll the wheel axle on a flat surface." | Yamaha YW125Y 2009 SM p. 117 |
| C38 | kept | "In accordance with the B&P section 9884.9 and CCR section 3353, provide the customer an estimate for the specific work needed to diagnose and repair the inspection failure." | BAR Smog Check Reference Guide 2025 p. 32 |
| C39 | kept (the insurance words are in the note's heading; the body names only road approval) | "Voiding of the government approval for road use and the insurance coverage  If the ABS is switched off completely, the vehicle's approval for road use is invalidated." | KTM 2019 690 Duke OM p. 54 |
| C40 | kept | "OWNER'S MANUAL2019 690 Duke" | KTM 2019 690 Duke OM p. 1 |
| C41 | kept | "Check the frame for damage, cracks, and deformation. » If the frame shows signs of damage, cracks, or deformation: ‒ Change the frame. Repairs on the frame are not permitted." | KTM 2027 450 SX-F / 450 XC-F OM p. 93 |
| C42 | kept | "‒ Change the frame. Repairs on the frame are not permitted." | KTM 2027 250 XC-W / 300 EXC … OM p. 97 |
| C43 | kept | "‒ Change the frame. Repairs on the frame are not permitted." | KTM 2027 500 EXC-F OM p. 96 |
| C44 | kept | "Surgical Strip —A vehicle completely stripped when recovered from theft. … Owner Declared —A vehicle irreversibly designated by the owner solely as a source of parts or scrap metal." | California DMV VIRPM 19.015 Definitions p. 1 |
| C45 | kept (rendered: the chart headings also carry "(Front and rear tire pressures are normal)"; see defect 5) | "STEERING HANDLEBAR DOES NOT TRACK STRAIGHT … Steering handlebar pulls to one side → ①Misaligned front and rear wheels ②Bent front fork" / "Suspension is too hard → ①Bent fork tube or shock rod" | Kymco People / People S 250 SM p. 35 |
| C46 | kept | "Tampering can void manufacturer warranties and insurance agreements." | EPA fact sheet (aftermarket defeat devices and tampering) p. 2 |
| C47 | kept | "OWNER'S MANUAL2022 250 EXC TPI 250 EXC SIX DAYS TPI 250 XC‑W TPI 300 EXC TPI …" | KTM 2022 250/300 EXC TPI OM p. 1 |
| W31 | kept | "CHARGE THE BATTERY BEFORE USE TO ENSURE OPTIMUM PERFORMANCE. INADEQUATE CHARGING OF THE BATTERY WITH A LOW ELECTROLYTE LEVEL BEFORE IT IS FIRST USED SHORTENS THE LIFE OF THE BATTERY." | Piaggio Beverly 125 service station manual p. 78 |
| W32 | kept (the page is the "Possible Cause / Operation" troubleshooting table) | "If the vehicle is not used for some time (1 month or more) the battery needs to be recharged periodically. The battery runs down completely in the course of 3 months." | Beverly 125 p. 55 |
| crash item 1 instr.: "On the Honda CB500F/FA a banking (lean angle) sensor stops the engine and fuel pump … OFF and back to ON … other machines follow their own manual" | kept | "A banking (lean angle) sensor automatically stops the engine and fuel pump if the motorcycle falls over. To reset the sensor, you must turn the ignition switch to the OFF position and back to the ON position before the engine can be restarted." | Honda CB500F/FA 2018 OM p. 113 |
| crash item 1 diag.: "ride slowly and cautiously; it warns … not immediately apparent, and says to have it thoroughly checked" | kept | "Ride slowly and cautiously. Your motorcycle may have suffered damage that is not immediately apparent. Have your motorcycle thoroughly checked at a qualified service facility as soon as possible." | Honda CB500F/FA 2018 OM p. 9 |
| crash item 2: "the only maker's rule in the library is KTM's, the same in four KTM owner's manuals" | kept | Search `repairs?ontheframe\|framerepair\|repairtheframe\|repairingtheframe\|framemustnotberepaired\|weld…frame`: 4 pages in 4 files, all KTM (22_3214421 p. 94, 27_3240384 p. 93, 27_3240387 p. 97, 27_3240392 p. 96). `changetheframe\|replacetheframe\|framemustbereplaced\|replaceframe` gives the same 4 pages. `straighten…frame` gives 0. Quote: "Repairs on the frame are not permitted." | KTM 2022 EXC TPI OM p. 94 |
| crash item 2 descr.: "KTM 2022 250/300 EXC TPI and XC-W TPI … the same rule for the link fork" | kept | "Change the link fork. Guideline Repairs on the link fork are not permitted." | KTM 2022 EXC TPI OM p. 94 |
| crash item 2: title "KTM's rule is change, not repair" | kept | "Change the frame. Guideline Repairs on the frame are not permitted." | KTM 2022 EXC TPI OM p. 94 |
| crash item 3: title "a bent handlebar is replaced, not straightened" | kept | "A bent handlebar must always be replaced. Never try to straighten the handlebar" | KTM 950 Super Enduro R 2008 OM p. 27 |
| crash item 4 descr.: the Kymco chart rows | kept | "Steering handlebar pulls to one side … ②Bent front fork"; "Suspension is too hard … ①Bent fork tube or shock rod" | Kymco People / People S 250 SM p. 35 |
| crash item 4 diag.: "A bent front fork shows as the handlebar pulling to one side …" | kept, weak (reads cause to symptom, drops the co-cause and the tire-pressure condition; defect 5) | "Steering handlebar pulls to one side → ①Misaligned front and rear wheels ②Bent front fork … (Front and rear tire pressures are normal)" | Kymco People / People S 250 SM p. 35 |
| crash item 5 descr.: the front-axle figures and half TIR (CHF50 0.20, PCX150 0.2, Kymco 0.2) | kept | "Place the axle on V-blocks and measure the runout with a dial indicator. SERVICE LIMIT: 0.2 mm (0.01 in) Actual runout is 1/2 of the total indicator reading." | Honda PCX150 SM p. 326 (CHF50 p. 218 and Kymco p. 187 as in C35 and C36) |
| crash item 5 descr.: "For the front wheel axle the Yamaha YW125Y … 0.25 mm … 'Do not attempt to straighten a bent wheel axle'" | kept | "CHECKING THE FRONT WHEEL … Wheel axle bending limit 0.25mm (0.01in) WARNING Do not attempt to straighten a bent wheel axle." | Yamaha YW125Y 2009 SM p. 117 |
| crash item 5 instr.: "on the Honda and Kymco pages the actual runout is half the total indicator reading" (rim) | **killed** for Kymco: its two rim pages give the limit and no halving. Only its axle page (p. 187) halves | "WHEEL RIM Check the wheel rim runout. Service Limits: Radial: 2.0mm replace if over A x i a l: 2.0mm replace if over" (p. 188); "Measure the rear wheel rim runout. Service Limits: Radial: 2.0mm replace if over" (p. 206) | Kymco People / People S 250 SM pp. 188, 206 |
| crash item 5 instr.: the rim limits and pages (CHF50 219/242, PCX150 326/355, Kymco 188/206, YW125Y front 1.0 mm p. 117) | kept | "Actual runout is 1/2 the total indicator reading. SERVICE LIMITS: Radial: 2 .0 mm (0.08 in) Axial: 2 . 0 mm (0.08 in)" (CHF50 p. 219); "Radial wheel runout limit 1.0mm (0.04in) Lateral wheel runout limit 1.0mm (0.04in)" (YW125Y p. 117) | Honda CHF50 SM p. 219; Yamaha YW125Y SM p. 117 |
| crash item 5 diag.: "replace if over (Kymco … pp. 187–188, 206)" | kept | "Radial: 2.0mm replace if over" | Kymco People / People S 250 SM p. 206 |
| crash item 7 descr.: "The one estimate rule it holds, California BAR's written repair estimate (B&P section 9884.9), is written for Smog Check repairs" | kept, but "written" is not on the page (defect 3) | "In accordance with B&P section 9884.9 and CCR section 3353, prepare an estimate for the specific work needed to bring the vehicle into compliance. … The estimate must include price for labor and parts." | BAR Smog Check Reference Guide 2025 p. 32 |
| crash item 7 diag.: "Where its owner's manuals say 'insurance' they mostly say where to keep the insurance papers" | kept | Search `insurance` in pages.json: 29 pages. 26 are "registration, and insurance information can be stored in the plastic document bag" (Honda) or the Yamaha document-space text. 3 are the KTM ABS note (19_3213917 p. 183; 19_3213923 pp. 54, 110). 1 is EU 168/2013 p. 36 | Honda CB500F/FA 2018 OM p. 113 and others |
| crash item 7 diag.: "the KTM 2019 690 Duke owner's manual: switching the ABS off completely voids the road approval and the insurance coverage (PDF p. 54)" | kept (as C39) | "Voiding of the government approval for road use and the insurance coverage" | KTM 2019 690 Duke OM p. 54 |
| crash item 7 diag.: "Its 'photograph' pages are workshop illustrations or type-approval and recall paperwork" | killed as worded (half-applied fix; defect 4). Search `photograph`: 177 pages. Several are owner's-manual illustrations or manual disclaimers | "The gear positions can be seen in the photograph." (KTM 2022 EXC TPI OM p. 24); "All information, illustrations, photographs and specifications contained in this manual are based on the latest product information" (Kymco People S OM p. 4) | KTM 2022 OM p. 24; Kymco People S OM p. 4 |
| crash item 8 descr.: nonrepairable criteria | kept | "Surgical Strip —A vehicle completely stripped when recovered from theft. Complete Burn —A completely burned vehicle. Owner Declared —A vehicle irreversibly designated by the owner solely as a source of parts or scrap metal." | DMV 19.015 p. 1 |
| crash item 8 exp_fail: "a vehicle declared nonrepairable put back on the road, though it cannot be titled or reregistered" | kept | "Once declared nonrepairable, the vehicle cannot be titled or reregistered." | DMV 19.015 p. 1 |
| generic winterization item 2: "On a four-stroke, change engine oil and filter before storage" | kept as a template step, with a gap: 3 of the 5 four-stroke storage lists checked do it; Honda CB500F/FA p. 117 and Yamaha XVS95CL p. 81 list no oil change (defect 6) | "Before laying the vehicle up out of use, have the engine oil and the oil filter element changed by a specialist workshop" (BMW F800R p. 124); "Change the engine oil and filter, clean the oil screens." (KTM 690 p. 172); "1. Change the engine oil and filter." (Kymco People S p. 60) | BMW F800R RM p. 124; KTM 690 Enduro 2010 OM p. 172; Kymco People S OM p. 60 |
| generic winterization item 2: "some makers change it again after storage (one, if more than a month has passed)" | **killed**: one maker, not "some", and that one is the conditional case. Its after-storage change is the engine oil only, not the filter | "Removal from storage … 2. Change the engine oil if more than 1 month has passed since the start of storage." | Kymco People S OM p. 61 |
| (the count behind the kill) | Of the six storage pages named, only Kymco changes oil after storage. After-storage steps: KTM 2022 p. 155 "Install the 12-V battery … Perform checks …"; KTM 690 p. 173 "Recharge the battery … Refuel …"; BMW F800R p. 124 "Install a charged battery. Before starting: work through the checklist."; Honda CB500F/FA p. 117 "inspect all maintenance items required by the Maintenance Schedule"; Yamaha XVS95CL p. 81 has no after-storage list. The library-wide search `(removalfromstorage\|afterstorage\|restoringtouse\|puttingintooperationafterstorage\|preparingforuseafterstorage\|returningtoservice\|endofstorage\|recommissioning).{0,600}(changetheengineoil\|…oilchange…)` returns 3 pages, all Kymco and all with the same conditional sentence (PeopleS p. 61, Agility 50-125 p. 50, Super 8 50X p. 46). Its positive control is Kymco p. 61, which it found | "Change the engine oil if more than 1 month has passed since the start of storage." | Kymco People S OM p. 61 |
| generic winterization item 2: "A two-stroke's storage list may change the gear oil instead" | kept | "– Change the gear oil. … – Add 2-stroke oil." | KTM 2022 250/300 EXC TPI OM p. 154 |
| generic winterization item 3 exp_pass: "on a charger the machine's maker allows, or removed or disconnected as its manual says and recharged when that manual says" | kept for the six named makers, with a gap: the Vespa and BMW R 850 R connected-battery options are not covered (defect 8) | "If you leave the battery in place, disconnect the negative - terminal to prevent discharge." (Honda); "disconnect the battery or connect a suitable trickle charger" (BMW F800R p. 117) | Honda CB500F/FA 2018 OM p. 117; BMW F800R RM p. 117 |
| winterization item 5 (W30): "a sealed battery's charge checked and, if necessary, recharged every six months while the vehicle is stored in open circuit (PDF pp. 77–78)" | kept | "Sealed battery If the vehicle is provided with a sealed battery, the only maintenance required is the check of its charge and recharging, if necessary." (p. 77) / "These operations should be carried out before delivering the vehicle, and on a six-month basis while the vehicle is stored in open circuit." (p. 78) | Beverly 125 pp. 77–78 |
| winterization item 5 (W30): "in a caution box on the same page, which also warns about a low electrolyte level before first use … 1 month or more … three months (PDF p. 78; the same words are in its troubleshooting table, PDF p. 55)" | kept, verbatim-accurate | "IF THE VEHICLE IS NOT USED FOR SOME TIME (1 MONTH OR MORE) THE BATTERY NEEDS TO BE RECHARGED PERIODICALLY. THE BATTERY RUNS DOWN COMPLETELY IN THE COURSE OF THREE MONTHS." | Beverly 125 p. 78 (and p. 55) |
| winterization item 5 (W30): "The manual gives both figures and does not say which applies to a stored vehicle." | kept, loose (defect 7): the six-month figure does name its condition (open circuit); the caution names none | "on a six-month basis while the vehicle is stored in open circuit" | Beverly 125 p. 78 |
| T25 | kept | "ERS (YZF-R1M)" | Yamaha YZFR1T1/YZFR1MT OM p. 41 |
| T26 | kept | "Adjusting spring preload for front wheel with Dynamic Damping Con- trol OE … Apply the rider's weight to the motorcycle." | BMW S 1000 R RM p. 80 |
| T27 | kept | "Adjusting spring preload for rear wheel … measure distanceD from bottom edge1 of the number-plate carrier to screw2 of the chain guard." | BMW S 1000 R RM p. 78 |
| T28 | kept | "As delivered, KTM offroad motorcycles are adjusted for an average rider's weight (with full protective clothing). Guideline Standard rider weight 75 … 85 kg (165 … 187 lb.)" | KTM 2022 250/300 EXC TPI OM p. 55 |
| T29 | kept | "11.7 Checking the static sag of the shock absorber … Static sag 37 mm (1.46 in)" … "the rider, wear- ing full protective clothing, sits on the seat … Riding sag 110 mm (4.33 in)" | KTM 2022 250/300 EXC TPI OM p. 58 |
| T30 | kept | "YAMAHA MOTOR CORPORATION, U.S.A. 2020 AND LATER MODEL STREET & DUAL- PURPOSE MOTORCYCLE LIMITED WARRANTY … purchased from an authorized Yamaha motorcycle dealer in the continental United States" | Yamaha YZFR1T1/YZFR1MT OM p. 135 |
| T31 | kept | "This vehicle is not suitable for use on race tracks." | KTM 2027 790 DUKE OM p. 10 |
| T32 | kept | "Owner's manual2027 790 DUKE" | KTM 2027 790 DUKE OM p. 1 |
| T33 | kept | "Pro riding modesOE DYNAMIC PRO The DYNAMIC PRO mode can- not be activated unless the cod- ing plug is inserted." | BMW S 1000 R RM p. 107 |
| T34 | kept | "with Dynamic Traction Control (DTC) OE DTC switched off The DTC indicator light lights up. DTC assistance is deactivated." | BMW S 1000 XR RM p. 133 |
| T35 | kept on its page; its use in item 4 is killed as unconditioned (defect 1) | "Note that deactivating the DTC means that the DTC remains switched off even after the ig- nition has been switched off and then on again." (inside "Riding mode DYNAMIC PRO", begun p. 131) vs "DTC is switched on. If the coding plug is not inser- ted, you have the alternative of switching the ignition off and then on again." | BMW S 1000 XR RM p. 132 (p. 62) |
| T36 | kept | "The mode last selected is automatically reactivated after the ignition has been switched off and then on again." | BMW S 1000 R RM p. 106 |
| T37 | kept (qualified: the menu item is the rear-wheel ABS) | "This module allows you to turn the rear wheel ABS (anti-lock braking system) on/off. … WARNING Turn the ABS off only when riding on a closed circuit course." | Yamaha YZFR7T OM p. 71 |
| T38 | kept | "Nut, rear axle M50x1.5 250 Nm … Thread greased/lock locking wire with locking varnish … Mount outside locking wire4. – Mount inside locking wire5. The pins of the locking wires engage in the drilled holes of the wheel axle." (both the R block and the "(SUPER DUKE RR)" block) | KTM 2023 1290 Super Duke R/RR OM p. 129 |
| T39 | kept | "Nor is approval by an official technical inspection authority, or even the granting of a gen- eral operating permit or a certif- icate issued by the tyre manufacturer necessarily a suf- ficient guarantee" (title p. 1: "Maintenance Instructions K 1200 RS") | BMW K 1200 RS Maintenance Instructions p. 4 |
| T40 | kept | "Do not use pure water as only coolant is able to meet the requirements needed in terms of corrosion protec- tion and lubrication properties." | KTM 2022 250/300 EXC TPI OM p. 170 |
| T41 | kept | "10.2 Required work Every 10 operating hours when used for motorsports Every 40 operating hours Every 20 operating hours" | KTM 2022 250/300 EXC TPI OM p. 52 |
| T42 | kept | "Every 40 operating hours when used for motorsports Every 10 operating hours when used for motorsports" | KTM 2022 250/300 EXC TPI OM p. 54 |
| T43 | kept | "Locknut (mirror) to clamping piece Joining compound: Multi-wax spray 20 Nm" | BMW S 1000 R RM p. 85 |
| E34 | kept | "PGA recommends keeping all receipts relating to the maintenance of the motorcycle but may not deny the enforceability of the warranty solely on the basis of the absence of such receipts, nor by invoking the failure to perform all scheduled maintenance work." | Vespa GTS 310 HPE (USA) OM p. 17 |
| E35 | kept | "The vehicle or engine manufacturer, in accordance with this article, shall not be liable for malfunctions of the components covered by the warranty that result from the presence of additional or modified parts." | Vespa GTS 310 HPE (USA) OM p. 19 |
| E36 | kept | "Production vehicles must also be properly labeled and have their emission control systems warranted for their specified useful life." | CARB "ONMC - Executive Order Introduction" p. 1 |
| E37 | kept | "Note that exhaust systems (headers or mufflers) intended for installation on non-catalyst equipped motorcycles are also considered by CARB to be replacement parts provided all emission controls originally connected to the exhaust manifold are reconnected to the exhaust system and are functioning properly." | CARB "Aftermarket Motorcycle Parts" p. 1 |
| E38 | kept | "the CAA prohibits tampering with or defeating emission controls on EPA-certified vehicles." … "As a matter of enforcement discretion, EPA is concerned with the sale and use of aftermarket parts that increase emissions. EPA generally takes no enforcement for the sale and use of aftermarket parts jf the person can demonstrate" | EPA fact sheet, March 2020, p. 1 |
| E39 | kept | "a reasonable basis for knowing that such use will not adversely affect emissions performance. One may prove a reasonable basis in one of the following ways" … "may result in penalties of up to the statutory civil penalties. As of January 13, 2020, the statutory civil penalties are $48, 192 per violative vehicle or engine for manufacturers and dealers and $4,819 per violative vehicle or engine or defeat device for any person other than a manufacturer or dealer." | EPA fact sheet, March 2020, p. 2 |
| E40 | kept (qualified: the page also lists PGM-FI and Ignition Timing Control, defect 7) | "# Secondary Air Injection System … Evaporative Emission Control System 50 STATE (meets California)" | Honda CB500F/FA 2018 OM p. 122 |
| E41 | kept | "The fuel tank, fuel hoses, and fuel vapor charge hoses use fuel permeation control technologies to prevent fuel vapor emissions. Tampering with these components to reduce or defeat the effectiveness of the fuel permeation technologies is prohibited." | Honda CB500F/FA 2018 OM p. 123 |
| E42 | kept | "• Motorcycles. … H&S §§ 44011, 44011(a)(6), VC § 4000.1, CCR §§ 3340.5, 3340.42" | BAR Smog Check Reference Guide 2025 p. 9 |
| E43 | kept | "EVAPORATIVE EMISSION CONTROL SYSTEM (EXCEPT AFTER '13 MODEL CM TYPE) This model complies with CARB evaporative emission requirements." | Honda PCX150 2013–2017 SM p. 42 |
| E44 | kept | "Appendix A 35 … Tampered - Any emission control component which is missing, modified or disconnected." | BAR Smog Check Reference Guide 2025 p. 41 |
| track item 1: "The KTM 2022 250/300 EXC TPI owner's manual, for its EXC models: the derestricted version "must only be operated in closed off areas…"" | kept | "(All EXC models) … This vehicle is only authorized for operation on public roads in the homologated (restricted) version. The derestricted version of this vehicle must only be operated in closed off areas away from public highway traffic." | KTM 2022 250/300 EXC TPI OM p. 9 |
| track item 1: "The KTM 2027 790 DUKE owner's manual, by contrast: "This vehicle is not suitable for use on race tracks"" | kept | "This vehicle is not suitable for use on race tracks." | KTM 2027 790 DUKE OM p. 10 |
| track item 1 + diagnosis: Yamaha Motor Corporation, U.S.A.'s limited warranty, continental U.S., "Competition or racing use" | kept | "GENERAL EXCLUSIONS from this warranty shall include any failures caused by: Competition or racing use." | Yamaha YZFR1T1/YZFR1MT OM p. 135 |
| track item 2: mirror, brake-fluid reservoir, 20 Nm with Multi-wax spray | kept | "When removing the right mirror, make sure that the brake-fluid reservoir remains cor- rectly secured." … "Joining compound: Multi-wax spray 20 Nm" | BMW S 1000 R RM p. 85 |
| track item 2 instruction: reactivate the warning (p. 88); refit marked template's own; plug protected | kept | "before the motorcycle is ridden on public roads the warning has to be reactivated … Protect the plug on the motor- cycle to prevent the ingress of foreign matter." | BMW S 1000 R RM p. 88 |
| track item 3: front preload to rider's weight; negative spring displacement rear p. 78, front p. 80 | kept | "Front spring preload has to be adjusted to suit the rider's weight." (p. 78) … "Measure distanceD between bottom edge1 of the slider tube and front axle2. Apply the rider's weight" (p. 80) | BMW S 1000 R RM pp. 78, 80 |
| track item 3: "on machines with Dynamic Damping Control (optional equipment), 6...10 mm at the front with an 85 kg rider (PDF pp. 80–81)" | kept | "Adjusting spring preload for front wheel with Dynamic Damping Con- trol OE" (p. 80) … "Negative spring displacement of front wheel 6...10 mm (With rider 85 kg)" (p. 81) | BMW S 1000 R RM pp. 80–81 |
| track item 3: KTM rider-weight band, rear shock static 37 / riding 110 mm | kept | "Standard rider weight 75 … 85 kg (165 … 187 lb.)" / "Checking the static sag of the shock absorber" (see T28, T29) | KTM 2022 250/300 EXC TPI OM pp. 55, 58 |
| track item 3: "in its section for the YZF-R1M only … presets ERS mode M-1 for track use with racing slick tires (PDF p. 42)" | kept, incomplete (defect 3) | "M -1 is preset for track use with racing slick tires. M-2 is preset for track use with street tires. M-3 is preset for street use with street tires." | Yamaha YZFR1T1/YZFR1MT OM p. 42 |
| track item 3 instruction: KTM riding sag with full protective clothing; BMW damping to surface and preload | kept | "An increase in spring preload requires firmer damping, a re- duction in spring preload re- quires softer damping." | BMW S 1000 R RM p. 81 |
| track item 4: DYNAMIC PRO (Pro riding modes OE), coding plug, grip "generally encountered only on race tracks", rear lock-up | kept | "riding on surfaces with the high level of grip gen- erally encountered only on race tracks … ABS control is not active at the rear wheel when the footbrake lever is pressed. Under these circumstances, the rear wheel can lock up." | BMW S 1000 R RM p. 107 |
| track item 4: XR DTC (OE) off: drifts, wheelies, flipping over backwards | kept | "Any drifts are possible. … Any wheelies are possible. There is a possibility of the motorcycle flipping over backwards." | BMW S 1000 XR RM p. 133 |
| track item 4: Yamaha R7 launch control "track use on closed circuit race tracks only" | kept | "LC S is intended for track use on closed circuit race tracks only." | Yamaha YZFR7T OM p. 23 |
| track item 4: R7 "Turn the ABS off only when riding on a closed circuit course" | kept (qualified: rear-wheel ABS; defect 6) | "turn the rear wheel ABS (anti-lock braking system) on/off … Turn the ABS off only when riding on a closed circuit course." | Yamaha YZFR7T OM p. 71 |
| track item 4 instruction: "on the BMW S 1000 R the mode last selected returns (PDF p. 106)" | kept | "The mode last selected is automatically reactivated after the ignition has been switched off and then on again" (see T36) | BMW S 1000 R RM p. 106 |
| track item 4 instruction: "on the BMW S 1000 XR a deactivated DTC stays off (PDF p. 132)" | killed as stated (condition dropped; defect 1) | "DTC is switched on. If the coding plug is not inser- ted, you have the alternative of switching the ignition off and then on again." | BMW S 1000 XR RM p. 62 |
| track item 5: KTM required work 10 h (pp. 52–53), recommended 10 h and 40 h (pp. 53–54) | kept | "10.2 Required work Every 10 operating hours when used for motorsports" / "Every 40 operating hours when used for motorsports Every 10 operating hours when used for motorsports" (see T41, T42) | KTM 2022 250/300 EXC TPI OM pp. 52, 54 |
| track item 6 instruction: KTM "Do not use pure water" (p. 170) | kept | "Do not use pure water as only coolant is able to meet the requirements needed in terms of corrosion protec- tion and lubrication" (see T40) | KTM 2022 250/300 EXC TPI OM p. 170 |
| track item 6 diagnosis: KTM 1290 Super Duke R / RR locking wires (p. 129) | kept | "Mount outside locking wire" (see T38) | KTM 2023 1290 Super Duke R/RR OM p. 129 |
| track item 6 diagnosis: "a seat lock cable" | kept, unattributed (defect 8) | "disconnect the seat lock wire" | Kymco Agility 50 SM p. 32 |
| track item 6 diagnosis: "technical inspection" note in the BMW K 1200 RS Maintenance Instructions (p. 4) | kept (the same note is also in a second BMW booklet, R_04… p. 4) | "Nor is approval by an official technical inspection authority" (see T39) | BMW K 1200 RS Maintenance Instructions p. 4 |
| emissions item 1: full citation list, section 1.1.5, p. 9 | kept | "H&S §§ 44011, 44011(a)(6), VC § 4000.1, CCR §§ 3340.5, 3340.42" (see E42) | BAR Smog Check Reference Guide 2025 p. 9 |
| emissions item 2: CARB E.O. for "make, model and model year"; "must also be properly labeled" | kept | "Production vehicles must also be properly labeled and have their emission control systems warranted for their specified useful life" (see E36; "must first issue an Executive Order for the particular make, model, and model year") | CARB "ONMC - Executive Order Introduction" p. 1 |
| emissions item 2: CB500F CARB evaporative requirement "when operated and maintained according to the instructions provided"; label on left of swingarm | kept | "CARB also requires that your motorcycle comply with applicable evaporative emission requirements during its useful life, when operated and maintained according to the instructions provided." … "The Vehicle Emission Control Information label is located on the left side of the swingarm." | Honda CB500F/FA 2018 OM p. 121 |
| emissions item 2 diagnosis: PCX destination code; reading a machine's code is the template's reading | kept | "AC 50 state (meets California)" | Honda PCX150 2013–2017 SM p. 8 |
| emissions item 3: EPA "the Act prohibits tampering … on EPA-certified vehicles" (p. 1) | kept | "As a matter of enforcement discretion, EPA is concerned with the sale and use of aftermarket parts that increase emissions" (see E38) | EPA fact sheet p. 1 |
| emissions item 3: penalties "up to", "as of January 13, 2020", $4,819 / $48,192; warranties and insurance | kept (qualified: $48,192 is "per violative vehicle or engine", no defeat device; defect 9) | "One may prove a reasonable basis in one of the following ways" (see E39; "Tampering can void manufacturer warranties and insurance agreements.") | EPA fact sheet p. 2 |
| emissions item 3: BAR "Tampered" glossary (p. 41), VC 27156 sentence (p. 45) | kept | "One such law is California Vehicle Code Section 27156 which states that no person shall disconnect, modify, or alter any required motor vehicle pollution control device." | BAR Smog Check Reference Guide 2025 pp. 41, 45 |
| emissions item 3 instruction: CB500F system walk "the systems the … manual describes (PDF pp. 122–123)" | kept, incomplete (defect 7) | "# PGM-FI System … # Ignition Timing Control System … # Secondary Air Injection System … # Catalytic Converters" | Honda CB500F/FA 2018 OM p. 122 |
| emissions item 3 instruction: fuel-permeation tampering; noise-control heading, U.S. federal law; presumed acts | kept | "TAMPERING WITH THE NOISE CONTROL SYSTEM IS PROHIBITED: U. S. federal law prohibits" (p. 123) … "Removing or disabling any emissions compliance component, or replacing any compliance component with a noncompliant component." (p. 124) | Honda CB500F/FA 2018 OM pp. 123–124 |
| emissions item 3 expected_fail and item 6 diagnosis: "for a motorcycle, prohibited by VC 27156 as CARB applies it (Aftermarket Motorcycle Parts)" | killed as cited (defect 2) | "prohibits the installation of any add-on or modified emission-related part on any pollution-controlled motorcycles" … "Motorcycles which are manufactured for on-road use have been pollution controlled since the 1979 model year." | CARB "Aftermarket Motorcycle Parts" p. 1 |
| emissions item 4: CARB exhaust note for non-catalyst motorcycles | kept | "exhaust systems (headers or mufflers) intended for installation on non-catalyst equipped motorcycles are also considered by CARB to be replacement parts provided all emission controls originally connected to the exhaust manifold are reconnected to the exhaust system" (see E37) | CARB "Aftermarket Motorcycle Parts" p. 1 |
| emissions item 4 expected_fail: "not a header or muffler on a non-catalyst machine with its emission controls reconnected" | kept, condition half-dropped (defect 5) | "reconnected to the exhaust system and are functioning properly" | CARB "Aftermarket Motorcycle Parts" p. 1 |
| emissions item 4 instruction: EPA enforcement discretion and three ways (p. 1 … p. 2) | kept (page split: "reasonable basis … not adversely affect" is on p. 2; defect 4) | "As a matter of enforcement discretion, EPA is concerned with the sale and use of aftermarket parts that increase emissions" / "One may prove a reasonable basis in one of the following ways" (see E38, E39; "3. By producing an Executive Order from the California Air Resources Board (CARS) that covers the same device on the same vehicle on which the device is installed.") | EPA fact sheet pp. 1–2 |
| emissions item 4 instruction: "verify … that the E.O. covers this part on this make and model" (declined "model year") | kept; decline right | "describing the part or device, and which motorcycle models that it is intended to be used" | CARB "Aftermarket Motorcycle Parts" p. 1 |
| emissions item 4 diagnosis: Vespa exempt part usable, not grounds to reject warranty, "shall not be liable…" | kept | "shall not be liable for malfunctions of the components covered by the warranty that result from the presence of additional or modified parts" (see E35) | Vespa GTS 310 HPE (USA) OM p. 19 |
| emissions item 5: PCX "no adjustment … periodic inspection" is the catalytic converter's | kept | "THREE-WAY CATALYTIC CONVERTER … No adjustment to the system should be made, although periodic inspection of the components is recommended." | Honda PCX150 2013–2017 SM p. 42 |
| emissions item 5 expected_fail: Honda misfire "stop riding and turn off the engine" (p. 125); Vespa MIL "for a long time" (p. 28) | kept | "If your engine is misfiring, backfiring, stalling, or otherwise not running properly, stop riding and turn off the engine." | Honda CB500F/FA 2018 OM p. 125 |
| emissions item 6: PCX evaporative heading | kept | "EVAPORATIVE EMISSION CONTROL SYSTEM (EXCEPT AFTER '13 MODEL CM TYPE)" (see E43) | Honda PCX150 2013–2017 SM p. 42 |
| emissions item 7: CB500F (USA) p. 45 "certified" parts | kept | "USA Maintenance, replacement or repair of the emission control devices and systems may be performed by any motorcycle repair establishment or individual using parts that are "certified" to EPA standards." | Honda CB500F/FA 2018 OM p. 45 |
| emissions item 7: Vespa California warranty, Class III 280 cm³+, 5 yr / 30,000 km, receipts clause | kept (machine is 310 cm³, p. 89: "Engine capacity 18.92 cu.in (310 cm³)", so Class III is its class) | "Class III motorcycles (280 cm³ and above): for a period of use of five (5) years or 30,000 kilometers (18,641 miles), whichever occurs first." | Vespa GTS 310 HPE (USA) OM p. 17 |
| emissions item 7 expected_fail / diagnosis (Yamaha p. 122, Vespa p. 17, Honda p. 128) | kept | "Your warranty coverage is not voided if you perform your own maintenance. However, failures that occur due directly to improper maintenance are not covered by these warranties." | Honda CB500F/FA 2018 OM p. 128 |

**Round 2 result.**
- **Claims:** all 48 round-1 additions kept (C32–C47, T25–T43, E34–E44,
  W31, W32).
- **Changed sentences:** 68 with a factual claim tested; **6 killed as
  written**, and another 11 kept only with a condition or a correction.
  Two of the killed sentences had come from round 1's own proposed
  replacements, so round 1's proposals were checked like the rest.
  - crash item 5: "on the Honda and Kymco pages the actual runout is
    half the total indicator reading" — the Kymco rim pages (pp. 188,
    206) never halve it.
  - generic winterization item 2: "some makers change it again after
    storage (one, …)" — exactly one maker, Kymco, conditionally, and two
    four-stroke storage lists name no oil change at all.
  - crash item 7: the "photograph" sentence was still incomplete
    (owner's-manual illustrations, front-matter disclaimers).
  - track item 4: "on the S 1000 XR a deactivated DTC stays off" — only
    with the coding plug (p. 132 sits in the DYNAMIC PRO section, p. 131);
    without it, the ignition cycle switches DTC back on (p. 62).
  - emissions items 3 and 6: "prohibited by VC 27156 as CARB applies it"
    for a missing or disconnected part — CARB's page speaks only of
    installing unexempted parts, from the 1979 (on-road) and 1997
    (off-road) model years; the disconnect wording is BAR's (p. 45).
- **My round-1 decline was wrong.** I declined the refuter's "M-2 for
  track use with street tires" because the text layer around "T-2" did
  not show it. The rendered p. 42 prints "M-2 is preset for track use with
  street tires". I had read a snippet, not the page. The item now gives
  T-1 and M-1 for slicks and T-2 and M-2 for street tires (pp. 41–42).
- **Fixed:** all of the above, plus the lesser ones — EPA's reasonable
  basis spans pp. 1–2; the CARB exhaust exception keeps "functioning
  properly" in pass and fail; the R7's ABS warning is for its rear-wheel
  ABS; the Honda system list is complete; the lock-wire sentence names the
  Kymco Agility 50 (p. 32) and drops "factory"; "$48,192 per violative
  vehicle or engine"; W30's last sentence says what each Beverly figure is
  conditioned on; BAR's estimate is not "written" on the page; the Kymco
  p. 35 chart read in its own direction, with its tire-pressure condition.
- **The generic starter's oil and battery lines became pure pointers.**
  Each attempt to enumerate the makers in the starter text was wrong once,
  in round 1 and again in round 2. The operator's F161 scope is "remove
  each unsupported figure or replace it with a pointer to the cited
  winterization_v1". The oil line now keeps its original words minus the
  figure and points to `winterization_v1`. The battery pass is "Battery
  kept as the machine's own manual says", with the pointer. The original
  text's remaining universality (the two-stroke, the makers who change no
  oil) is added to F163.
- 10 new claims anchor the round-2 wording (T44–T50, E45–E47): 150
  claims, 288 anchors, all on their pages. The cross-check reads 134
  cited pages and 12 regulator citations, 0 unclaimed.

### Round 3 — 2026-09-26: the 10 claims round 2 added, and every sentence it changed

One fresh-context Opus refuter, given the sentence-level diff of round 2
(`s0/refute/round2_changed_sentences.md`, 32 sentences). It rendered the
pages whose layout mattered (Yamaha R1 pp. 41–42, Kymco pp. 188, 206).

| claim | verdict | quote | source |
|---|---|---|---|
| T44 | kept (rendered: TIP inside "ERS (YZF-R1M)") | "T -1 is preset for track use with rac- ing slick tires." | Yamaha YZFR1T1/YZFR1MT OM p. 41 |
| T45 | kept (rendered) | "T -2 is preset for track use with street tires. … M-2 is preset for track use with street tires. M-3 is preset for street use with street tires." | Yamaha YZFR1T1/YZFR1MT OM p. 42 |
| T46 | kept | "DTC is switched on. If the coding plug is not inser- ted, you have the alternative of switching the ignition off and then on again." | BMW S 1000 XR RM p. 62 |
| T47 | kept | "Riding mode DYNAMIC PRO with riding modes ProOE … TheDYNAMIC PRO mode cannot be activated unless the coding plug is inserted." | BMW S 1000 XR RM p. 131 |
| T48 | kept | "This module a llows you to turn the rear wheel ABS (anti-lock braking system) on/off. … WARNING Turn the A BS off only when riding on a closed circuit course." | Yamaha YZFR7T OM p. 71 |
| T49 | kept (census `lock-?wire`: 1 page in all of pages.json) | "AGILITY 50 Discornnect the seat lock wire." | Kymco Agility 50 SM p. 32 |
| T50 | kept | "This Service Manual describes the technical features and servicing procedures for the KYMCO AGILITY 50" | Kymco Agility 50 SM p. 1 |
| E45 | kept | "# PGM-FI System … # Ignition Timing Control System The ignition timing control system adjusts the ignition timing to reduce the amount of HC, CO, and NOx produced." | Honda CB500F/FA 2018 OM p. 122 |
| E46 | kept | "a reasonable basis for knowing that such use will not adversely affect emissions performance." | EPA fact sheet (March 2020) p. 2 |
| E47 | kept | "One such law is California Vehicle Code Section 27156 which states that no person shall disconnect, modify, or alter any required motor vehicle pollution control device." | BAR Smog Check Reference Guide 2025 p. 45 |
| crash item 4 diag.: "With tire pressures normal, the Kymco chart lists a bent front fork, beside misaligned front and rear wheels, as a cause of the handlebar pulling to one side, and a bent fork tube or shock rod as the cause of suspension that is too hard" | kept (rendered: the tyre-pressure condition heads both charts; "Suspension is too hard" has one cause) | "(Front and rear tire pressures are normal) … Steering handlebar pulls to one side ①Misaligned front and rear wheels ②Bent front fork … Suspension is too hard ①Bent fork tube or shock rod" | Kymco People / People S 250 SM p. 35 |
| crash item 5 instr.: "on the Honda pages the actual runout is half the total indicator reading" | kept (CHF50 pp. 219, 242; PCX150 pp. 326, 355) | "Check the wheel rim runout using dial indicators. Actual runout is 1/2 the total indicator readings. SERVICE LIMITS: Radial: 2.0 mm (0.08 in) Axial: 2.0 mm (0.08 in)" | Honda PCX150 2013–2017 SM p. 355 |
| crash item 5 instr.: "the Kymco rim pages give their limit without saying how the reading is taken" | kept, loose. The text does not say, but each page's drawing shows two dial indicators on the rim. What neither page says is whether the limit is the full reading or half of it (defect 5) | "WHEEL RIM Check the wheel rim runout. Service Limits: Radial: 2.0mm replace if over Axial: 2.0mm replace if over" (p. 188); "Measure the rear wheel rim runout." (p. 206) | Kymco People / People S 250 SM pp. 188, 206 |
| crash item 7 descr.: "California BAR's repair estimate (B&P section 9884.9 and CCR section 3353), is written for Smog Check repairs" | **killed**. The guide itself says the estimate is required by the Automotive Repair Act. The guide applies it to Smog Check work; the rule is not written for Smog Check (defect 1) | "A written estimate must be provided in accordance with the Automotive Repair Act before the inspection and/or repair can be conducted. … B&P § 9884.9, H&S § 44033(c), CCR § 3353" | BAR Smog Check Reference Guide 2025 p. 27 (and p. 32) |
| crash item 7 descr.: "The one estimate rule it holds" | kept. A search for `(repair\|damage\|written) estimate\|estimate (for\|of) …` over pages.json and pages_reg.json finds only BAR guide pages (5 = table of contents, 27, 32). The `9884\|3353` hits outside the guide are Honda parts-list numbers | "In accordance with B&P section 9884.9 and CCR section 3353, prepare an estimate for the specific work needed to bring the vehicle into compliance." | BAR Smog Check Reference Guide 2025 p. 32 |
| crash item 7 diag.: "Where its owner's manuals say 'insurance' they mostly say where to keep the insurance papers" | kept. `insurance` over pages.json: 29 pages. 25 are the document-bag or document-storage text, 3 are the KTM ABS note and 1 is EU 168/2013 | "The owner's manual, registration, and insurance information can be stored in the plastic document bag located underside of the front seat." | Honda CB500F/FA 2018 OM p. 113 |
| crash item 7 diag.: "elsewhere it appears mostly as a warning" | **killed**. Round 2's count omitted the regulator pages. With them, "elsewhere" is 12 pages: KTM ABS note (3 pages, 2 manuals), EPA (1), EU 168 liability insurance (1), BAR "Insurance Code (IC)" (1), and 6 California DMV pages on the insurance company's part in a total loss (the pages item 8 cites). Warnings are 4 of the 12 (defect 2) | "The insurance company or its designee (salvage pool or registration service) or the owner must apply for the salvage certificate within 10 days from the date the insurance company makes a total loss settlement with the owner." | California DMV VIRPM 19.075 Salvage Certificate p. 1 |
| crash item 7 diag.: "the KTM 2019 690 Duke owner's manual: switching the ABS off completely voids the road approval and the insurance coverage (PDF p. 54)" | kept (as C39: the insurance words are in the note's heading) | "Voiding of the government approval for road use and the insurance coverage If the ABS is switched off completely, the vehicle's approval for road use is invalidated." | KTM 2019 690 Duke OM p. 54 |
| crash item 7 diag.: "Its 'photograph' pages are workshop and owner's-manual illustrations, manual front-matter disclaimers, or type-approval and recall paperwork" | kept. `photograph` over pages.json gives 177 pages and 137 distinct contexts. All are workshop "as shown in the photograph" steps (Piaggio, Vespa, Beverly, Fly, MP3, Typhoon, Gilera), KTM "The gear positions can be seen in the photograph", Vespa OM p. 60, Kymco "illustrations, photographs and specifications" front matter, PGO SM p. 2 front matter, EU 168/2013 p. 20 (type approval) and NHTSA 14V364 Part 573 p. 2 (recall). The 4 pages_reg.json hits are "Press Photographer License Plates" in the DMV site navigation: "photographer", not the word "photograph", so no defect | "All information, illustrations, photographs and specifications contained in this manual are based on the latest product information" | Kymco People S 50/125/200 OM p. 4 |
| emissions item 3 descr.: "violations may bring civil penalties of up to the statutory amount, which as of January 13, 2020 was $4,819 per violative vehicle, engine or defeat device for any person other than a manufacturer or dealer ($48,192 per violative vehicle or engine for manufacturers and dealers)" | kept | "Violation of the anti-tampering and defeat device provisions of the CAA may result in penalties of up to the statutory civil penalties. As of January 13, 2020, the statutory civil penalties are $48, 192 per violative vehicle or engine for manufacturers and dealers and $4,819 per violative vehicle or engine or defeat device for any person other than a manufacturer or dealer." | EPA fact sheet p. 2 |
| emissions item 3 descr.: "Tampering can void manufacturer warranties and insurance agreements" (PDF p. 2) | kept | "WARRANTY ISSUES Tampering can void manufacturer warranties and insurance agreements." | EPA fact sheet p. 2 |
| emissions item 3 instr.: PGM-FI and ignition timing, exhaust and catalytic converter, secondary air, canister on 50-state models, closed crankcase, fuel tank / fuel hoses / vapor charge hoses — "the systems the … manual describes (PDF pp. 122–123)" | kept. All seven are on pp. 122–123. The noise emission control system (p. 123) is covered by the next sentences | "Evaporative Emission Control System 50 STATE (meets California)" (p. 122); "Crankcase Emissions Control System The engine is equipped with a closed crankcase system" (p. 123) | Honda CB500F/FA 2018 OM pp. 122–123 |
| emissions item 3 exp_fail and item 6 diag.: "On a pollution-controlled motorcycle (on-road from the 1979 model year, off-road from 1997: CARB, Aftermarket Motorcycle Parts), VC 27156 bars disconnecting, modifying or altering a required pollution control device (BAR …, PDF p. 45)" | kept. The model-year scope is CARB's, and BAR's wording is BAR's. They fit together because BAR's wording covers only a "required" device. The page (p. 45) is right | "Motorcycles which are manufactured for on-road use have been pollution controlled since the 1979 model year. … motorcycles which are manufactured for off-road use have been pollution controlled since 1997 model year and are subject to the prohibitions in VC 27156." | CARB "Aftermarket Motorcycle Parts" p. 1 (with BAR p. 45, E47) |
| emissions item 3 exp_fail: "and installing an unexempted add-on or modified emission-related part (CARB, Aftermarket Motorcycle Parts)" | kept | "prohibits the installation of any add-on or modified emission-related part on any pollution-controlled motorcycles, unless the part has been exempted by CARB." | CARB "Aftermarket Motorcycle Parts" p. 1 |
| emissions item 3 exp_fail / item 6 diag.: "BAR's Smog Check glossary calls such a component 'tampered' (PDF p. 41)" | kept. The appendix is headed "Definitions and Abbreviations List"; "glossary" describes it fairly | "Tampered - Any emission control component which is missing, modified or disconnected." | BAR Smog Check Reference Guide 2025 p. 41 (Appendix A) |
| emissions item 4 instr.: "EPA generally takes no enforcement where a person can show a reasonable basis that the part will not adversely affect emissions (PDF pp. 1–2)" | kept | "EPA generally takes no enforcement for the sale and use of aftermarket parts jf the person can demonstrate" (p. 1) / "a reasonable basis for knowing that such use will not adversely affect emissions performance." (p. 2) | EPA fact sheet pp. 1–2 |
| emissions item 4 instr.: "the part is identical in design and function to the one it replaces; the vehicle as modified meets emission standards on the original manufacturer's certification tests; or a CARB Executive Order covers the same device on the same vehicle (PDF p. 2)" | kept | "1. The aftermarket part is identical in design and function to the part it is replacing. 2. The vehicle, as modified, meets emissions standards when tested on the same tests as the original vehicle manufacturer used to certify the vehicle with EPA. 3. By producing an Executive Order from the California Air Resources Board (CARS) that covers the same device on the same vehicle" | EPA fact sheet p. 2 |
| emissions item 4 exp_pass / exp_fail: "a header or muffler on a non-catalyst machine with its original emission controls reconnected and functioning (properly)" | kept. CARB's condition covers the controls "originally connected to the exhaust manifold", and the text asks for no less | "exhaust systems (headers or mufflers) intended for installation on non-catalyst equipped motorcycles are also considered by CARB to be replacement parts provided all emission controls originally connected to the exhaust manifold are reconnected to the exhaust system and are functioning properly." | CARB "Aftermarket Motorcycle Parts" p. 1 |
| emissions item 6 diag.: "A missing or disconnected canister is a missing or disconnected emission control component." | kept | "Evaporative Emission Control System 50 STATE (meets California) An evaporative emissions control system uses a canister filled with charcoal" | Honda CB500F/FA 2018 OM p. 122 |
| generic winterization item 2 instr.: "Change engine oil and filter with the oil the machine's own manual specifies." | **killed**. This is universal again, and it now covers two-strokes too (round 2 had "On a four-stroke"). Two four-stroke storage lists name no oil change, and the KTM two-stroke changes gear oil. It also contradicts the item's own next sentence (defect 3) | "Clean the motorcycle. … – Change the gear oil. … – Add 2-stroke oil." (KTM p. 154); Honda's storage list is wash, chain, stand, dry, battery: "Remove the battery … to prevent discharge. … After removing your motorcycle from storage, inspect all maintenance items" (p. 117) | KTM 2022 250/300 EXC TPI OM p. 154; Honda CB500F/FA 2018 OM p. 117 |
| generic winterization item 2 instr.: "Which makers change the oil for storage, and when, differs: winterization_v1 gives each maker's step with its document and page." | kept. winterization_v1 item 4 cites KTM 690 p. 172, BMW F800R p. 124, Kymco People S pp. 60–61 (including the after-storage change) and KTM EXC TPI p. 154 (gear oil) | "2. Change the engine oil if more than 1 month has passed since the start of storage." | Kymco People S 50/125/200 OM p. 61 |
| generic winterization item 3 exp_pass: "winterization_v1 gives each maker's charger, connection and interval with its document and page" | **killed as worded**. winterization_v1 item 5 names a charger only for BMW (R 850 R p. 48; F800R p. 117) and Yamaha (XVS95CL p. 81). It names none for Honda or KTM, and none for Piaggio, although the Beverly page it cites does name one. It gives no recharge interval for either KTM (defect 4) | "Normal bench charging must be carried out using the specific battery charger 020333Y (single) or 020334 (multiple)" | Piaggio Beverly 125 service station manual p. 78 |
| winterization item 5 descr.: "The manual gives both figures and does not reconcile them: the six-month check is for a vehicle stored in open circuit, and the caution does not say whether the battery is connected." | kept. The caution's next sentence speaks of refitting the battery "if it is necessary", which names no stored state | "on a six-month basis while the vehicle is stored in open circuit." … "IF THE VEHICLE IS NOT USED FOR SOME TIME (1 MONTH OR MORE) THE BATTERY NEEDS TO BE RECHARGED PERIODICALLY. THE BATTERY RUNS DOWN COMPLETELY IN THE COURSE OF THREE MONTHS. IF IT IS NECESSARY TO REFIT THE BATTERY IN THE VEHICLE, BE CAREFUL NOT TO REVERSE THE CONNECTIONS" | Piaggio Beverly 125 p. 78 |
| track item 3 descr.: "in its section for the YZF-R1M only ('ERS (YZF-R1M)', PDF p. 41), presets automatic mode T-1 and manual mode M-1 for track use with racing slick tires, and T-2 and M-2 for track use with street tires (PDF pp. 41–42)" | kept (rendered). The automatic and manual labels are the page's own | "The ERS consists of three semi-active automatic modes (T-1, T-2, and R-1) and three manual setting modes (M-1, M-2, and M-3)." | Yamaha YZFR1T1/YZFR1MT OM p. 41 |
| track item 4 descr.: "for its rear-wheel ABS switch, 'Turn the ABS off only when riding on a closed circuit course' (PDF p. 71)" | kept | "This module a llows you to turn the rear wheel ABS (anti-lock braking system) on/off. … Turn the A BS off only when riding on a closed circuit course." | Yamaha YZFR7T OM p. 71 |
| track item 4 descr.: launch control "is intended for track use on closed circuit race tracks only" (PDF p. 23) | kept | "LC S is intended for track use on closed circuit race tracks only." | Yamaha YZFR7T OM p. 23 |
| track item 4 instr.: "on the BMW S 1000 XR, with the coding plug inserted, a deactivated DTC stays off after the ignition is switched off and on (PDF p. 132" | kept. The p. 132 note sits in the DYNAMIC PRO section (T47). pp. 62 and 126 make the ignition reset apply only "if the coding plug is not inserted", so "with the coding plug inserted" is the right condition | "Note that deactivating the DTC means that the DTC remains switched off even after the ig- nition has been switched off and then on again." | BMW S 1000 XR RM p. 132 |
| track item 4 instr.: "without the coding plug, switching the ignition off and on switches DTC back on, PDF p. 62" | kept, loose. p. 126 adds a condition: DTC comes back only once the motorcycle passes 10 km/h after the ignition is cycled (defect 6) | "If the encoding plug for the DYNAMIC PROriding mode is not inserted, accelerating the motorcycle to a defined minimum speed after switching the ignition off and then on again reactivates the DTC. Minimum speed for ac- tivation of DTC min 10 km/h" | BMW S 1000 XR RM p. 126 (and p. 62) |
| track item 6 diag.: "its 'lock wire' hits are a seat lock wire (Kymco Agility 50 service manual, PDF p. 32)" | kept (T49, T50) | "Discornnect the seat lock wire." | Kymco Agility 50 SM p. 32 |
| track item 6 diag.: "the locking wires that secure the KTM 1290 Super Duke R / RR rear axle nut (PDF p. 129)" | kept. `locking-?wires?`: 4 pages, all in this manual (pp. 127, 128 remove; p. 129 mount; p. 174 spec), for both the R and the RR | "Nut, rear axle M50x1.5 250 Nm … Thread greased/lock locking wire with locking varnish – Mount outside locking wire4. – Mount inside locking wire5. The pins of the locking wires engage in the drilled holes of the wheel axle." | KTM 2023 1290 Super Duke R/RR OM p. 129 |
| track item 6 diag.: "its 'technical inspection' is a parts-and-accessories approval note in the BMW K 1200 RS Maintenance Instructions (PDF p. 4)" (left from round 2 defect 8; not changed) | kept, incomplete. `technicalinspection`: 2 pages, the K 1200 RS and the R 850 R / R 1150 R Maintenance Instructions, p. 4 of each (defect 7) | "Nor is approval by an official technical inspection authority, or even the granting of a gen- eral operating permit necessar- ily a sufficient guarantee" | BMW R 850 R / R 1150 R Maintenance Instructions p. 4 |

**Round 3 result.** All 10 new claims kept. 32 changed sentences tested:
25 kept, 3 kept loose, **4 killed** — again including round 2's own
replacements.
- crash item 7: BAR's estimate is "written for Smog Check repairs" — the
  guide says the written estimate is the Automotive Repair Act's (p. 27),
  applied to Smog Check work. Rewritten to say so.
- crash item 7: "elsewhere it appears mostly as a warning" — round 2's
  census missed the regulator pages; with them, 4 of 12 are warnings and
  6 are the DMV's total-loss pages. Rewritten: a warning in two documents,
  and the insurance company's part in the DMV pages item 8 cites.
- generic winterization items 2 and 3: the pointer sentences still
  described winterization_v1 ("each maker's charger, connection and
  interval"), and it does not hold all of that. **Every generic pointer now
  claims only what it points at** — "winterization_v1 gives the fuel /
  oil / battery steps of the makers it cites, each with its document and
  page" — and the oil line no longer states a universal change.
- Loose, fixed: the Kymco rim pages draw two dial indicators but do not
  say full or half reading; DTC returns without the coding plug only
  above 10 km/h (S 1000 XR p. 126); the "technical inspection" note is
  in two BMW booklets.
- Not applied: its knock-on rewrite of generic item 2's untouched
  expected_pass and expected_fail (F163's scope; the finding lists them).

3 claims anchor the new wording (C48, T51, T52): 153 claims, 292
anchors, all on their pages. Cross-check: 136 cited pages and 12
regulator citations, 0 unclaimed.

**The operator's stopping rule for the refute loop, 2026-09-26, recorded
as given:** "Carry on to the dry run once round 3 is clean. Stopping rule
for the refute loop: if round 3 finds only wording defects, fix them,
re-read just those sentences once, and move on. If it finds a factual
defect (wrong figure, page, name or source), fix it and run one more
round on only the changed sentences. No more than one round after that:
any claim still unresolved gets dropped from the migration and filed as
a finding, not shipped. Then stop at the live apply with the F161/F162
diff, as planned."

Applied literally: round 3 found factual defects (a misattributed source
— the estimate rule is the Automotive Repair Act's — and an incomplete
count), so round 4 runs on only round 3's changed sentences and new
claims. If round 4 finds defects, they are fixed and round 5, the last,
reads only those sentences; anything still unresolved after round 5 is
dropped from migration 071 and filed as a finding.

### Round 4 — 2026-09-26: round 3's changed sentences and its 3 claims (the operator's "one more round")

One fresh-context Opus refuter over `s0/refute/round3_changed_sentences.md`
and C48, T51, T52.

| claim | verdict | quote | source |
|---|---|---|---|
| C48 | kept | "A written estimate must be provided in accordance with the Automotive Repair Act before the inspection and/or repair can be conducted." | BAR Smog Check Reference Guide 2025 p. 27 |
| T51 | kept | "If the encoding plug for the DYNAMIC PROriding mode is not inserted, accelerating the motorcycle to a defined minimum speed after switching the ignition off and then on again reactivates the DTC. Minimum speed for ac- tivation of DTC min 10 km/h" | BMW S 1000 XR RM p. 126 |
| T52 | kept (K 1200 RS title page rendered: "…enance Instructions … 0 RS") | "Nor is approval by an official technical inspection authority, or even the granting of a gen- eral operating permit necessar- ily a sufficient guarantee, since these test procedures are not always adequate." | BMW R 850 R / R 1150 R Maintenance Instructions p. 4 |
| crash item 5 instr.: "on the Honda pages the actual runout is half the total indicator reading" | kept (CHF50 pp. 219, 242; PCX150 pp. 326, 355 all say so) | "Check the wheel rim runout using dial indicators. Actual runout is 1 /2 the total indicator readings. SERVICE LIMITS: Radial: 2 .0 mm (0.08 in) Axial: 2 . 0 mm (0.08 in)" | Honda CHF50 SM p. 242 |
| crash item 5 instr.: "the Kymco rim pages draw two dial indicators on the rim but do not say whether their limit is on the full indicator reading or half of it" | kept (rendered; the text on both pages has no "1/2" and no "total indicator") | "WHEEL RIM Check the wheel rim runout. Service Limits: Radial: 2.0mm replace if over Axial: 2.0mm replace if over" (p. 188); "INSPECTION Measure the rear wheel rim runout." (p. 206) | Kymco People / People S 250 SM pp. 188, 206 |
| crash item 7 descr.: "The one estimate rule it holds is in BAR's Smog Check Reference Guide 2025, which for Smog Check inspections and repairs requires a written estimate in accordance with the Automotive Repair Act (B&P section 9884.9 and CCR section 3353) (PDF pp. 27, 32)" | kept. p. 27 covers "the inspection and/or repair" and p. 32 the repair estimate, so both statutes are cited on the pages | "In accordance with B&P section 9884.9 and CCR section 3353, prepare an estimate for the specific work needed to bring the vehicle into compliance." | BAR Smog Check Reference Guide 2025 p. 32 (and p. 27) |
| crash item 7 diag.: "elsewhere it appears as a warning in two documents — the KTM 2019 690 Duke owner's manual … (PDF p. 54); EPA's fact sheet …" | **killed**. The KTM warning is also in a second KTM manual, the 2019 1090 Adventure R (rendered p. 183), so the warning is in three documents, not two (defect 1) | "Voiding of the government approval for road use and the insurance coverage If the ABS is switched off completely, the vehicle's approval for road use is invalidated." | KTM 2019 1090 Adventure R OM p. 183 |
| crash item 7 diag.: "the KTM 2019 690 Duke owner's manual: switching the ABS off completely voids the road approval and the insurance coverage (PDF p. 54)" | kept | "Note Voiding of the government approval for road use and the insurance coverage If the ABS is switched off completely, the vehicle's approval for road use is invalidated." | KTM 2019 690 Duke OM p. 54 |
| crash item 7 diag.: "and in the California DMV pages item 8 cites, as the insurance company's part in a total loss" | kept, incomplete. It is true of all four pages item 8 cites (19.015, 19.075, Total Loss, Junk/Revived). Two further DMV pages (19.040, notice of retention) and, in passing, EU 168/2013 p. 36 and BAR p. 8 go unmentioned; they are folded into defect 1 | "19.075 Salvage Certificate (VC §11515) The insurance company or its designee (salvage pool or registration service) or the owner must apply for the salvage certificate within 10 da[ys]" | California DMV VIRPM 19.075 Salvage Certificate p. 1 |
| generic winterization item 1 instr.: "winterization_v1 gives the fuel steps of the makers it cites, each with its document and page" | kept. winterization_v1 item 2 cites Yamaha XVS95CL p. 81, KTM 1290 p. 157, KTM 690 p. 172, KTM EXC TPI p. 154 and Kymco People S p. 60. The cited Honda CB500F p. 117 and BMW F800R p. 124 storage lists have no fuel step | "Make sure the tank is as empty as possible so that you can fill up with fresh fuel when you put the motorcycle back into operation." | KTM 690 Enduro 2010 OM p. 172 |
| generic winterization item 2 instr.: "Change the oil for storage as the machine's own manual lists it, with the oil it specifies; the makers differ on whether and when." | kept. The machine's own manual governs, and the sentence admits there may be no oil change | "– Clean the motorcycle. ( p. 150) – Change the gear oil. ( p. 148)" | KTM 2022 250/300 EXC TPI OM p. 154 |
| generic winterization item 2 instr.: "winterization_v1 gives the oil steps of the makers it cites, each with its document and page" | kept at the maker level. winterization_v1 item 4 gives KTM (690 p. 172; EXC TPI gear oil p. 154), BMW (F800R p. 124), Kymco (pp. 60–61) and the Yamaha fogging oil (p. 81). The BMW R 850 R step on p. 58 is the same as the F800R step | "Before laying the vehicle up out of use, have the en- gine oil and the oil filter element changed by a specialist work- shop" | BMW F800R RM p. 124 |
| generic winterization item 3 exp_pass: "winterization_v1 gives the battery steps of the makers it cites, each with its document and page" | **killed**. winterization_v1 cites the Kymco People S 50/125/200 OM on p. 60 four times (fuel, carburetor, oil, cylinder). Its battery step on that same page (remove, store frost- and sun-free, slow-charge monthly) is in no winterization_v1 item. Also not given with a page: the BMW F800R "Remove the battery" (p. 124, a cited page), the KTM 690 "Remove the battery / Recharge the battery" (p. 172, cited only for its temperature) and the Piaggio charger (p. 78, a cited page) (defect 2) | "4. Remove the battery. Store it in an area protected from freez- ing temperatures and direct sunlight. Slow charge the bat- tery once a month (use a quality charger designed for use on a maintenance-free type battery)." | Kymco People S 50/125/200 OM p. 60 |
| track item 4 instr.: "without the coding plug, switching the ignition off and on switches DTC back on once the motorcycle passes 10 km/h, PDF pp. 62, 126" | kept (T51). p. 62 agrees: "in excess of the minimum" | "DTC is switched on. If the coding plug is not inser- ted, you have the alternative of switching the ignition off and then on again." | BMW S 1000 XR RM p. 62 (and p. 126) |
| track item 6 diag.: "a parts-and-accessories approval note in two BMW booklets (the K 1200 RS and the R 850 R / R 1150 R Maintenance Instructions, PDF p. 4 of each)" | kept (census `technicalinspection`: exactly these 2 pages) | "Nor is approval by an official technical inspection authority, or even the granting of a gen- eral operating permit or a certif- icate issued by the tyre manufacturer necessarily a suf- ficient guarantee" | BMW K 1200 RS Maintenance Instructions p. 4 |

**Round 4 result.** 3 of 3 new claims kept; 12 changed sentences with a
factual claim tested, **2 killed**, both factual and both introduced by
round 3's rewrite:
- crash item 7: "a warning in two documents" — the same KTM ABS warning
  is also in the KTM 2019 1090 Adventure R owner's manual (p. 183). Now
  "in warnings — among them" both KTM manuals and EPA, with no count.
- generic winterization item 3, expected_pass: "winterization_v1 gives
  the battery steps of the makers it cites" — it does not give every
  cited page's battery step (Kymco p. 60, BMW F 800 R p. 124, KTM 690
  p. 172). Now "winterization_v1 compares several makers' battery steps,
  with their pages", which its item 5 does (five makers, 17 citations).
- Carried over, not changed: generic items 2 and 3's untouched
  expected_pass, expected_fail and instruction — F163.

C49 and C50 anchor the 1090 Adventure R page: 155 claims, 294 anchors,
all on their pages. Cross-check: 137 cited pages and 12 regulator
citations, 0 unclaimed. Under the operator's rule, round 5 is the last:
it reads only these two sentences and C49, C50.

### Round 5 — 2026-09-26: the last round under the operator's rule

One fresh-context Opus refuter over round 4's two rewritten sentences and
C49, C50.

| claim | verdict | quote | source |
|---|---|---|---|
| C49: 1090 Adventure R, the ABS-off note about insurance | kept | "Voiding of the government approval for road use and the insurance coverage  If the ABS is switched off completely, the vehicle's approval for road use is invalidated." | KTM 2019 1090 Adventure R owner's manual (19_3213917_en_OM.pdf) p. 183 (printed 181). on_page True, and False on p. 182 |
| C50: title page of 19_3213917 | kept | "OWNER'S MANUAL2019 1090 Adventure R Art. no. 3213917en" (the render shows the same) | 19_3213917_en_OM.pdf p. 1 |
| S1a: 690 Duke, PDF p. 54 | kept | "7.16 "TC/ABS" … Note Voiding of the government approval for road use and the insurance coverage  If the ABS is switched off completely, the vehicle's approval for road use is invalidated." | KTM 2019 690 Duke owner's manual (19_3213923_en_OM.pdf) p. 54 |
| S1b: title page of 19_3213923 is the 2019 690 Duke | kept | "OWNER'S MANUAL2019 690 Duke Art. no. 3213923en" (the render shows the same) | 19_3213923_en_OM.pdf p. 1 |
| S1c: "switching the ABS off completely voids the road approval and the insurance coverage" | kept, see defect 1 | "Voiding of the government approval for road use and the insurance coverage  If the ABS is switched off completely…". The word "insurance" appears only in the note's bold heading. The body sentence names only road approval. | 19_3213917_en_OM.pdf p. 183; 19_3213923_en_OM.pdf p. 54 |
| S1d: the KTM passages are "warnings" | killed | "Note Voiding of the government approval … insurance coverage". The rendered p. 183 shows this as a plain "Note". Directly below it on the same page is a separate grey "Warning" box ("Danger of accidents  Driving aids can only prevent a rollover…") that does not mention insurance. KTM's own key keeps the two apart: "Warning Identifies a danger that is likely to lead to fatal or serious injury…", "Note Identifies a danger that will lead to considerable machine and material damage…" | 19_3213917_en_OM.pdf p. 183 (render) and p. 15 (2.4 Degrees of risk and symbols) |
| S1e: EPA quote and page | kept | "WARRANTY ISSUES Tampering can void manufacturer warranties and insurance agreements." It sits under a "WARRANTY ISSUES" heading; the fact sheet does not call it a warning. | EPA Fact Sheet "Defeat Device and Tampering", March 2020 (system_files_documents_2021-11_epafactsheetreaftermarketddsandtampering.pdf) p. 2 |
| S1f: the DMV pages item 8 cites describe the insurance company's part in a total loss | kept | "The insurance company or its designee (salvage pool or registration service) or the owner must apply for the salvage certificate within 10 days from the date the insurance company makes a total loss settlement with the owner." Also on the other cited pages: "considers it uneconomical to repair" (19.015); "If you receive a settlement from your insurance company, then the insurance company is responsible for getting the certificate within 10 days" (Total Loss page); "previously reported to DMV as a total loss by the owner or insurance company" (Junk/Revived page) | California DMV VIRP manual 19.075 Salvage Certificate (HTML) p. 1; 19.015 Definitions p. 1; Total Loss Salvage & Non-Repairable Vehicles p. 1; Junk/Revived Salvage Vehicles p. 1 |
| S1g: "mostly" for owner's manuals | kept | "The owner's manual, registration, and insurance information can be stored in the plastic document bag". The census (libcensus.hits('insurance'), whitespace-stripped and case-insensitive over pages.json) found 29 pages in 28 files. One is not an owner's manual (eu168.pdf p. 36, the EU regulation). That leaves 28 owner's-manual pages: 24 Honda document-bag pages, 1 Yamaha page ("When storing the owner's manual or vehicle registration and insurance documents in the document storage space…", D45-28199-11 p. 62), and 3 KTM ABS notes (690 Duke pp. 54 and 110, 1090 Adventure R p. 183). So 25 of 28 are about where to keep the papers, and 24 of those use the document-bag sentence. | Honda CB500F owner's manual (om_AHM_CB500F-FA_2018) p. 113, and 23 more pages |
| S2a: winterization_v1 compares several makers' battery steps | kept | "The makers agree on a full charge and disagree on how often." Item 5 covers five makers: Honda (CB500F, PCX150), Yamaha (XVS95CL), BMW (R 850 R / R 1150 R, F800R), Piaggio (Beverly 125) and KTM (690 Enduro, 2022 250/300 EXC TPI). | smoke71.db winterization_v1 item 5, description; its citations include Piaggio Beverly 125 SSM p. 78 |
| S2b: "with their pages" | kept | "a removed battery once a month in the Yamaha XVS95CL owner's manual (PDF p. 81)". Every maker step in item 5 carries a PDF page, and item 6 (Vespa Elettrica, PDF p. 9) does too. | smoke71.db winterization_v1 items 5 and 6; its citations include Piaggio Beverly 125 SSM p. 78 |
| S2c: "Battery kept as the machine's own manual says" | kept | "Charge the battery fully, then do what the machine's own manual says". This is consistent with winterization_v1 item 5; the expected_pass makes no claim about any one maker. | smoke71.db winterization_v1 item 5, instruction_text; its citations include Piaggio Beverly 125 SSM p. 78 |
**Round 5 result.** C49, C50 kept; the generic battery pointer kept
("compares several makers' battery steps, with their pages": five makers
in winterization_v1 item 5, each with a PDF page); "mostly" kept (25 of
28 owner's-manual "insurance" pages are about keeping the papers).
**Killed: calling KTM's ABS passages "warnings"** — KTM prints them as a
"Note", a category its own key (p. 15) defines apart from a Warning, and
a separate Warning box follows on p. 183; EPA's line is under "WARRANTY
ISSUES".

**Applied under the operator's rule:** the claim is unresolved after the
last round, so it is **dropped from migration 071 and filed as F164**,
not shipped. Item 7's diagnosis now ends at the parts round 5 kept:
"Where its owner's manuals say "insurance" they mostly say where to
keep the insurance papers. Its "photograph" pages are …" (the photograph
sentence was kept in round 4). A deletion adds no claim. A guard test
pins that the dropped words do not return. The refuter's last proposed
wording, unread by any refuter, recorded for F164:

> elsewhere it appears where cover can be lost — among them the KTM 2019
> 690 Duke owner's manual (PDF p. 54) and the KTM 2019 1090 Adventure R
> owner's manual (PDF p. 183), in a note on switching the ABS off
> completely headed "Voiding of the government approval for road use and
> the insurance coverage", and EPA's fact sheet, under "WARRANTY ISSUES":
> "Tampering can void manufacturer warranties and insurance agreements"
> (PDF p. 2) — and in regulator pages,

Claims C39, C40, C46, C49 and C50 stay in the claims table as checked,
but no shipped sentence cites them now. The cross-check reads 135 cited
pages and 12 regulator citations, 0 unclaimed.

**The refute loop is closed.** Across five rounds: 155 claims, one killed
(T16) and corrected; one sentence dropped (F164); every other sentence
changed in a fix round was re-read by the next round, and round 5's
sentences were either kept or dropped.
