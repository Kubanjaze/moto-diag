# Phase 261 — Track N batch 1: tire, brake, suspension and drivetrain service

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-25 (v1.1: build, two refute rounds, regression, close-out — see Deviations)

**Branch:** `phase-261` (Opus session, main checkout).

**Carries four ROADMAP rows** (the operator's batching, 2026-09-25): 261
tire service, 269 brake service, 270 suspension service, 271 chain / belt
/ shaft service. One Step 0, one migration, one regression, one
close-out, one handoff. The ledger convention is in the phase log: row
261 closes with its CLOSED date and the regression line; rows 269, 270
and 271 close ✅ "folded into 261" with no date of their own; one history
row (261) and one handoff (`2026-09-25_261_closed.md`).

## Goal

Give the shop four service protocols as workflow content on the Phase 114
substrate, one template per row, reachable through the `motodiag
workflow list/show` door 259 built:

| row | slug | category | items (optional) |
|---|---|---|---|
| 261 | `tire_service_v1` | `tire_service` | 7 (TPMS) |
| 269 | `brake_service_v1` | `brake_service` | 7 (caliper and master-cylinder overhaul) |
| 270 | `suspension_service_v1` | `suspension_service` | 7 (fork oil — the CHF50's fork is greased; fork air bleed) |
| 271 | `drivetrain_service_v1` | `drivetrain_service` | 7 (all: a machine has one drive type) |

Every figure an item states names its machine and cites that machine's
document by name and PDF page, in the item's own text. Machines are named
as their documents' title pages name them. Where no document sets a
figure (N1 wear-pattern names, N2 universal-joint inspection, N3 belt
alignment), the item says so and invents none. Steps no document states
are marked as the template's own.

CLI: none new. `motodiag workflow list [--category tire_service|
brake_service|suspension_service|drivetrain_service]` and `motodiag
workflow show <slug>`. Bug fix #1 made `workflow list` print every slug
whole at 80 columns.

Outputs: migration 069 `chassis_drivetrain_service_workflows`
(`src/motodiag/core/migrations.py`, schema 68 → 69); `SCHEMA_VERSION`
68 → 69 (`src/motodiag/core/database.py`); `src/motodiag/cli/workflow.py`
(bug fix #1); `tests/test_phase261_service_workflows.py` (27 tests);
`COLLECTED_TEST_FLOOR` 9388 → 9415; F160 filed.

## Logic

1. **Migration 069.** Four `INSERT OR IGNORE` template rows
   (`["ice","electric","hybrid"]`, tier `individual`, system user 1),
   then 28 items keyed on the slug sub-select, inside the one-shot
   journal. **Inserts only**: no existing row is altered or deleted.
   `rollback_sql` deletes the four templates' items, then the templates.
2. **Items.** Tire: read the old tire (the makers' causes of abnormal
   wear; Kymco's flat spot); damage and age cracking; date code and age;
   TPMS / BMW RDC; fitting (approved tire, tubeless, rotation arrow, rim
   runout); balance; pressure, bead and run-in. Brake: pads; discs;
   caliper overhaul; master cylinder; fluid; bleeding; reassembly and
   bedding-in. Suspension: settings and sag; spring rate for the rider;
   fork oil; seals, wipers and springs; fork air bleed; rear shock;
   damping and preload. Drivetrain: chain slack (each maker's way of
   measuring); chain wear, sprockets and guides; clean and lubricate;
   adjust, align and replace; belt slack and condition; shaft final-drive
   oil; universal joints and swinging-arm bearings.
3. **Data flow.** Migration journal (existing DBs) / `db init` (new DBs)
   → `workflow_templates` + `checklist_items` → the existing accessors →
   the existing click commands → terminal. Nothing computes.

## Key Concepts

- **Content on a door that already opens** (260's shape): one migration
  plus its pins. The only code change is bug fix #1, which the new slugs
  exposed.
- **Claims before text.** The claims list (`s0/claims.py`) was written
  and checked on its pages before the item text, and a cross-check maps
  every "PDF p." in the seeded text back to a claim for the machine
  named before it.
- **Makers' words, then negatives.** Every subject was searched in the
  maker's own vocabulary first. The belt negative died inside Step 0 to
  Yamaha's "drive belt slack", and N1 died in refute to Kymco's "flat
  spots". Each was narrowed to what the evidence supports.
- **Names from title pages.** The Yamaha service manual is the YW125Y's
  ("Zuma" is on none of its 338 pages). The Honda manual covers the
  PCX150. The belt manuals are the XVS95CL and XVS13AF. A test pins it.
- **A figure travels with its method.** KTM's 55–58 mm chain tension, at
  the sliding piece on a lift stand, is not Honda's midway slack, nor
  BMW's deflection on the side stand. The item gives each with its
  method and says they cannot be compared.
- **F158 and F124** as in 259/260: no build references in any text a
  user sees; no literal head pin; migration tests build their own 068
  database and compare against `m.version`.

## Decisions

- **D1: four templates, one per row.** Each row is its own shop job and
  its own enum category.
- **D2: one migration (069)** for all four, the operator's batch shape.
- **D3: drivetrain is one template with optional per-drive items**
  (Step 0 S0-4). Three templates would ship the same items under three
  slugs.
- **D4: all powertrains** (S0-5).
- **D5: scope stops at the rows' subjects.** The scooter CVT belt and a
  scooter's final-reduction gear oil are not the row's "belt" and
  "shaft".
- **D6: the extraction route.** Subconscious returned 403 (account
  suspended; S0-7). Rule 2's fallback route ran the one-turn extraction
  in the same sandbox. Every quote it returned was checked on its page.
- **D7 (refute): the fork-oil item is optional.** A greased fork (the
  CHF50's) has no oil to change.
- **D8 (refute): F160 filed, not fixed.** 260's live `ppi_chassis_v1`
  names the YW125Y manual "Zuma 125". Changing live rows is a rule-1
  stop.

## Non-goals

- No new tables, repo functions, CLI commands, API routes or mobile
  screens.
- No change to existing templates or items. F158's 33 references, F159's
  uncited starter figures and F160's names stay with their own work.
- No CVT belt, winterization, break-in or valve content (batch 2 and
  other rows).

## Claims for the refute pass

Every fact the seeded text states, with its library path and PDF page.
There are 212 claims:
- 154 were refuted in round 1: the 157 original claims less the 3 retired
  after it (T32, B42, S33, whose sentences left the content). B1, S4 and
  S29 are among them, with the records corrected after their kill;
- 53 were added from round 1's findings and refuted in round 2;
- B62, D54 and S51–S53 were added from round 2's findings. They are
  verified mechanically on their pages but were not refuted by a third
  round.

Each claim's verbatim anchors (329) are on the cited page (`s0/claims.py`,
`verify.check`). The per-row verdicts are the phase log's Refuter pass.

**Negatives** (Step 0, whitespace-proof over all 260 PDFs, each with a
control on the exact page):

| # | negative | result |
|---|---|---|
| N1 | No document names cupping, feathering or squaring | Narrowed by refute. As first written ("names wear patterns such as …") it was killed by Kymco's "significant flat spots" (People S 50/125/200 OM p. 27), which the item now cites. Scalloping, sawtooth, heel-and-toe and squared or stepped tire wear: 0 pages. Control: `abnormalwear` hits CB500F OM p. 60 |
| N2 | No document gives a universal-joint inspection procedure or play figure | Kept by both rounds: 5 hits, all a scooter's final-reduction shaft; control `universaljoint` hits R 1100 S p. 81 |
| N3 | No document sets a final-drive belt alignment figure | Kept: 2 hits, the CHF50's CVT belt-case cover; control `drivebeltslack` hits XVS95CL OM p. 66 |

**`tire_service_v1`**

| # | claim as the item states it | document (library path) | PDF p. |
|---|---|---|---|
| T1 | KTM: low tire pressure leads to abnormal wear and overheating | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 116 |
| T2 | Honda CB500F: inspect for abnormal wear on the contact surface | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 60 |
| T3 | KTM: loose spokes form lateral and radial run-out | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 116 |
| T4 | CB500F minimum tread depth front 1.5 mm, rear 2.0 mm | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 134 |
| T5 | PCX150: measure tread at the centre; minimum 1.5 mm front, 2.0 mm rear | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 97 |
| T6 | KTM minimum tread depth ≥ 2 mm | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 115 |
| T7 | F800R: worn when tread reaches the marks, shown by TI, TWI or an arrow | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 100 |
| T8 | CB500F: cuts, slits or cracks exposing fabric or cords; embedded objects | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 60 |
| T9 | Yamaha SR400: tires age even unused; tread and sidewall cracking is evidence of ageing | Yamaha SR400 owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_2RD-28199-13_02.pdf`) | 56 |
| T10 | KTM: DOT last four digits, week then year; change after 5 years at the latest | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 116 |
| T11 | CB500F: TIN date example 22 09 = week 22 of 2009 | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 63 |
| T12 | CB500F: annual inspection from 5 years; remove after 10 years from manufacture | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 62 |
| T13 | F800R RDC: rim label marks sensor position; tell the fitter | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 103 |
| T14 | R 1200 GS RDC: no transmission until above approx. 30 km/h | BMW R 1200 GS rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0A01_RM_0213_R1200GS_01.pdf`) | 100 |
| T15 | F800R RDC: readings temperature-compensated to 20 °C | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 76 |
| T16 | F800R RDC: sensor battery capacity warning | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 39 |
| T17 | R 1200 GS: compare RDC reading with the table value, correct with the air line | BMW R 1200 GS rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0A01_RM_0213_R1200GS_01.pdf`) | 101 |
| T18 | CB500F: recommended tires or same size, construction, speed rating, load range; no tube in a tubeless tire | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 62 |
| T19 | CB500F: same size, construction, speed rating and load range | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 61 |
| T20 | BMW F 800 GS: note direction-of-rotation arrows on tyre or rim | BMW F 800 GS rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0K51_RM_0725_01.pdf`) | 178 |
| T21 | PCX150 rim runout service limit 2.0 mm axial and radial; half the indicator reading | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 326 |
| T22 | Kymco People S 250 rim runout 2.0 mm radial and axial | Kymco People / People S 250 service manual (`pdf/kymco_people_s250_sm.pdf`) | 188 |
| T23 | CB500F: balance with Honda Genuine weights after the tire is installed | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 62 |
| T24 | BMW S 1000 XR: front imbalance max 5 g; weights max 80 g, half each side | BMW S 1000 XR rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_S_0D03_RM_0418_01.pdf`) | 205 |
| T25 | BMW S 1000 XR: rear imbalance max 45 g | BMW S 1000 XR rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_S_0D03_RM_0418_01.pdf`) | 206 |
| T26 | Yamaha XC50J: balance whenever the tire or wheel is changed | Yamaha XC50J owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_1TS-F8199-15_02.pdf`) | 51 |
| T27 | F800R: new tyres smooth; run in at various heel angles | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 67 |
| T28 | R 1200 GS: new tyres do not give full grip straight away | BMW R 1200 GS rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0A01_RM_0213_R1200GS_01.pdf`) | 85 |
| T29 | KTM: only mount tires approved and/or recommended by KTM | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 115 |
| T30 | F800R RDC fault causes: wheels without sensors, failed sensors, radio interference | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 38 |
| T31 | F800R: incorrect tyre-removal procedures can damage the RDC sensors | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 103 |
| T33 | R 1200 GS: wet roads pose a risk with new tyres | BMW R 1200 GS rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0A01_RM_0213_R1200GS_01.pdf`) | 85 |
| T34 | Kymco People S 250 rim runout axial 2.0 mm | Kymco People / People S 250 service manual (`pdf/kymco_people_s250_sm.pdf`) | 188 |
| T35 | Kymco People S 50/125/200: significant flat spots on the tread → replace immediately | Kymco People S 50/125/200 owner's manual (`pdf/PeopleS-50-125-200.pdf`) | 27 |
| T36 | Kymco Like 150i/50i: proper wheel balance avoids uneven tire wear | Kymco Like 150i/50i owner's manual (`pdf/kymco_like_150i_50i_om.pdf`) | 53 |
| T37 | Yamaha SR400: a cracked sidewall → dealer replaces the tire immediately | Yamaha SR400 owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_2RD-28199-13_02.pdf`) | 55 |
| T38 | Yamaha SR400: old and aged tires checked by tire specialists for further use | Yamaha SR400 owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_2RD-28199-13_02.pdf`) | 56 |
| T39 | KTM EXC TPI: cuts, run-in objects or other damage → change the tires | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 115 |
| T40 | R 1200 GS: display shows -- for each tyre until the first signal | BMW R 1200 GS rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0A01_RM_0213_R1200GS_01.pdf`) | 100 |
| T41 | F800R: -- also when the 30 km/h threshold is not yet passed, or a system error | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 37 |
| T42 | F800R: system error as a cause | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 38 |
| T43 | F800R: battery warning — seek a specialist workshop's advice | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 39 |
| T44 | F800R: 2.5 bar front, 2.9 bar rear, tyre cold | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 134 |
| T45 | R 1200 GS: wet roads and extremely sharp inclines | BMW R 1200 GS rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0A01_RM_0213_R1200GS_01.pdf`) | 85 |
| T46 | F 800 GS: the front wheel installed wrong way round | BMW F 800 GS rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0K51_RM_0725_01.pdf`) | 178 |

**`brake_service_v1`**

| # | claim as the item states it | document (library path) | PDF p. |
|---|---|---|---|
| B1 | KTM EXC TPI: linings minimum thickness ≥ 1 mm | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 102 |
| B2 | KTM: press pistons back; keep fluid from overflowing; always change linings in pairs | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 104 |
| B3 | F800R: pad wear limit min 1.0 mm friction only; grooves clearly visible | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 94 |
| B4 | YW125Y: pad wear limit 0.8 mm | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 134 |
| B5 | Beverly 125: pad minimum 1.5 mm | Piaggio Beverly 125 service manual (`pdf/beverly125.pdf`) | 196 |
| B6 | CB500F: replace both left and right pads at the same time | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 77 |
| B7 | Beverly: fluid on disc or pads — replace the pads and clean the disc | Piaggio Beverly 125 service manual (`pdf/beverly125.pdf`) | 190 |
| B8 | KTM disc wear limits, standard models front 2.5 mm rear 3.5 mm | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 100 |
| B9 | PCX150 disc thickness limit 3.0 mm; warpage 0.30 mm | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 371 |
| B10 | YW125Y disc thickness min 3.5 mm; deflection max 0.15 mm | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 119 |
| B11 | Kymco People S 250 disc 4.0 standard, 3.0 limit; runout 0.30 | Kymco People / People S 250 service manual (`pdf/kymco_people_s250_sm.pdf`) | 184 |
| B12 | YW125Y: whenever a caliper is disassembled replace piston seal and dust seal | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 146 |
| B13 | YW125Y schedule: piston seal every two years; hose every four; fluid every two years | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 146 |
| B14 | YW125Y: never solvents on internal brake components | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 147 |
| B15 | YW125Y: piston seal with brake fluid, dust seal with silicone grease | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 147 |
| B16 | PCX150 caliper cylinder I.D. limits 25.460 / 22.710 mm; piston O.D. 25.31 / 22.56 mm | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 384 |
| B17 | Kymco People S 250 caliper piston O.D. limit 25.30 mm | Kymco People / People S 250 service manual (`pdf/kymco_people_s250_sm.pdf`) | 194 |
| B18 | PCX150 master cylinder I.D. 12.755 mm, piston O.D. 12.645 mm | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 373 |
| B19 | PCX150: piston, cups, spring, snap ring and boot as a set | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 374 |
| B20 | Beverly: all seals replaced every time the pump is serviced | Piaggio Beverly 125 service manual (`pdf/beverly125.pdf`) | 201 |
| B21 | KTM: never DOT 5 (silicone); brake fluid attacks paint | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 102 |
| B22 | KTM: brake fluid DOT 4 / DOT 5.1 | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 170 |
| B23 | CB500F: brake fluid every 2 years | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 49 |
| B24 | CB500F: Honda DOT 4; can damage plastic and painted surfaces | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 57 |
| B25 | PCX150: fresh DOT 3 or DOT 4 from a sealed container; do not mix | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 363 |
| B26 | Beverly: fluid hygroscopic | Piaggio Beverly 125 service manual (`pdf/beverly125.pdf`) | 48 |
| B27 | Beverly: change every 20,000 km or two years | Piaggio Beverly 125 service manual (`pdf/beverly125.pdf`) | 49 |
| B28 | YW125Y: water lowers the boiling point; vapor lock | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 89 |
| B29 | PCX150: bleed once the system has been opened or if the brake feels spongy | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 363 |
| B30 | PCX150: squeeze lever, open bleed valve 1/2 turn, close, release slowly; valve 5.4 N·m | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 367 |
| B31 | YW125Y: if bleeding is difficult let fluid settle a few hours | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 91 |
| B32 | YW125Y bleed screw 6 Nm | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 92 |
| B33 | KTM front caliper screw M8 25 Nm Loctite 243 | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 69 |
| B34 | F800R caliper on fork leg 30 Nm | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 106 |
| B35 | PCX150 caliper mounting bolt 30 N·m, ALOC bolt replaced | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 21 |
| B36 | KTM: operate foot brake lever until linings contact and there is a pressure point | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 109 |
| B37 | F800R: new pads have to bed down; longer stopping distance | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 67 |
| B38 | Kymco People S 250 caliper bolts 29–35 N·m | Kymco People / People S 250 service manual (`pdf/kymco_people_s250_sm.pdf`) | 195 |
| B39 | YW125Y: drain the whole system before disassembling the caliper; compressed air at the hose joint | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 145 |
| B40 | Beverly: all seals and gaskets replaced every time the caliper is serviced | Piaggio Beverly 125 service manual (`pdf/beverly125.pdf`) | 193 |
| B41 | Kymco People S 250 master cylinder I.D. limit 12.75 mm | Kymco People / People S 250 service manual (`pdf/kymco_people_s250_sm.pdf`) | 191 |
| B43 | PCX150: wait, close the valve, release the lever slowly | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 367 |
| B44 | YW125Y: solvents make the piston seal swell and distort | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 147 |
| B45 | KTM: oil seals and brake lines not designed for DOT 5 | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 102 |
| B46 | PCX150: warpage over the limit → check the wheel bearings | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 371 |
| B47 | Beverly: remove the wheel to check axial run-out; clean the disc and its seat on the hub | Piaggio Beverly 125 service manual (`pdf/beverly125.pdf`) | 196 |
| B48 | PCX150 caliper limits labelled upper and centre/lower | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 384 |
| B49 | Beverly: clean reused parts with denatured alcohol; rubber no longer than 20 seconds | Piaggio Beverly 125 service manual (`pdf/beverly125.pdf`) | 190 |
| B50 | Kymco People S 250: silicone grease on the piston and oil seal | Kymco People / People S 250 service manual (`pdf/kymco_people_s250_sm.pdf`) | 194 |
| B51 | YW125Y: caliper cylinder out → replace the caliper assembly | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 146 |
| B52 | Beverly: a scratched cylinder → replace the entire calliper | Piaggio Beverly 125 service manual (`pdf/beverly125.pdf`) | 192 |
| B53 | PCX150 CBS master cylinder I.D. 11.055 mm, piston O.D. 10.945 mm | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 363 |
| B54 | Kymco People S 250: main piston and spring installed as a unit | Kymco People / People S 250 service manual (`pdf/kymco_people_s250_sm.pdf`) | 191 |
| B55 | KTM EXC TPI: clean spilled brake fluid immediately with water | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 102 |
| B56 | Beverly: under normal conditions; more often under intense or harsh use | Piaggio Beverly 125 service manual (`pdf/beverly125.pdf`) | 190 |
| B57 | Beverly: 20,000 km / two years under normal climatic conditions | Piaggio Beverly 125 service manual (`pdf/beverly125.pdf`) | 49 |
| B58 | YW125Y: other fluids may make the rubber seals deteriorate | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 89 |
| B59 | PCX150: no air bubbles in the bleed hose; check the fluid level often | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 367 |
| B60 | Beverly: if air keeps coming, examine fittings, then pump and caliper piston seals | Piaggio Beverly 125 service manual (`pdf/beverly125.pdf`) | 199 |
| B61 | KTM EXC TPI: hand brake lever until pads contact and there is a pressure point | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 104 |
| B62 | Beverly: over the run-out limit → replace the disc and repeat the test; clean disc and hub seat when installing | Piaggio Beverly 125 service manual (`pdf/beverly125.pdf`) | 196 |

**`suspension_service_v1`**

| # | claim as the item states it | document (library path) | PDF p. |
|---|---|---|---|
| S1 | KTM EXC: adjust the shock first, then the fork; standard rider weight 75–85 kg; small differences by preload, large by springs | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 55 |
| S2 | KTM EXC: static sag 37 mm; riding sag 110 mm; rider bounces, feet on footrests | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 58 |
| S3 | KTM EXC: sag gauge at the rear axle to the SAG marking | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 57 |
| S4 | KTM 690 Enduro: static sag 25 mm | KTM 690 Enduro 2010 owner's manual (`acquired/KTM/10_3211511_en_OM.pdf`) | 73 |
| S5 | KTM 690 Enduro riding sag 70–80 mm | KTM 690 Enduro 2010 owner's manual (`acquired/KTM/10_3211511_en_OM.pdf`) | 74 |
| S6 | KTM EXC shock spring 57–63 / 60–66 / 63–69 N/mm by rider weight; no exact fork riding sag; bottoming → harder springs; hard fork after long use → bleed | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 60 |
| S7 | KTM EXC fork spring 4.2 / 4.4 / 4.6 N/mm; fork oil 636 ± 10 ml SAE 4 | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 166 |
| S8 | KTM 690 Enduro fork spring 5.2 / 5.4 / 5.6 N/mm; fork oil 620 ml SAE 5 | KTM 690 Enduro 2010 owner's manual (`acquired/KTM/10_3211511_en_OM.pdf`) | 183 |
| S9 | PCX150 fork fluid 122.0 ± 2.5 cm3, level 75 mm | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 335 |
| S10 | YW125Y fork oil 0.104 L per leg, 10W | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 160 |
| S11 | YW125Y: oil levels in both legs equal | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 158 |
| S12 | YW125Y: stroke the outer tube while draining | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 155 |
| S13 | YW125Y: never reuse the oil seal | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 156 |
| S14 | YW125Y: lubricate new seal lips; numbered side up | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 159 |
| S15 | PCX150: fork fluid on the new oil-seal and dust-seal lips; stopper ring | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 334 |
| S16 | KTM EXC: dirt behind the dust boots makes the oil seals leak | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 67 |
| S17 | YW125Y fork spring free length 252.1 mm, limit 247 mm | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 157 |
| S18 | CHF50 fork spring free length service limit 125.9 mm | Honda CHF50 service manual (`honda/chf50_service_mirror.pdf`) | 227 |
| S19 | KTM EXC shock: 10 bar gas pressure; SAE 2.5 fluid | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 167 |
| S20 | KTM EXC: the shock is filled with highly compressed nitrogen | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 55 |
| S21 | Honda XR650L: damper contains high pressure nitrogen; do not disassemble or service | Honda XR650L 2018 owner's manual (`acquired/Honda/om_AHM_XR650L_2018_XR650L_31MGW660_0.pdf`) | 85 |
| S22 | YW125Y: rear shock oil leaks → replace the assembly | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 175 |
| S23 | PCX150: compress the shock several times; check for leaks | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 95 |
| S24 | KTM EXC standard clickers: low-speed compression 15, high-speed 2 turns | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 56 |
| S25 | KTM EXC shock rebound standard 15 clicks | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 57 |
| S26 | KTM EXC shock spring preload 9 mm | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 59 |
| S27 | KTM 690: never change settings at random or by more than ± 40 % | KTM 690 Enduro 2010 owner's manual (`acquired/KTM/10_3211511_en_OM.pdf`) | 64 |
| S28 | CB500F rear preload: 9 positions, standard 4; never 1 to 9 directly | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 92 |
| S29 | YW125Y fork spring rates K1 7.1 N/mm, K2 15.4 N/mm | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 34 |
| S30 | KTM: spring rate shown on the outside of the spring | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 60 |
| S31 | YW125Y fork spring K1/K2 under front suspension; no optional spring | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 34 |
| S32 | KTM 690 Enduro: bleeding the fork legs, lean on the side stand | KTM 690 Enduro 2010 owner's manual (`acquired/KTM/10_3211511_en_OM.pdf`) | 75 |
| S34 | KTM EXC: static sag = A−B, riding sag = A−C; full protective clothing | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 58 |
| S35 | PCX150: new dust seal lip with fork fluid | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 334 |
| S36 | KTM EXC TPI: riding sag adjusted by choosing a suitable spring | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 60 |
| S37 | KTM EXC TPI: static sag off → adjust the shock's spring preload | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 58 |
| S38 | KTM 690 Enduro R: one fork spring 5.2 N/mm for 75–85 kg; 635 ml | KTM 690 Enduro 2010 owner's manual (`acquired/KTM/10_3211511_en_OM.pdf`) | 184 |
| S39 | KTM 690 Enduro (not R) fork table heading | KTM 690 Enduro 2010 owner's manual (`acquired/KTM/10_3211511_en_OM.pdf`) | 183 |
| S40 | CHF50 fork parts greased, 6.5–8 g | Honda CHF50 service manual (`honda/chf50_service_mirror.pdf`) | 227 |
| S41 | PCX150: measure level from the top of the fork pipe, leg fully compressed; SS-8; levels equal | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 335 |
| S42 | YW125Y: uneven oil levels → poor handling and a loss of stability | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 158 |
| S43 | YW125Y: inner tube bends/damage/scratches → replace | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 157 |
| S44 | KTM EXC TPI: bleeding the fork legs on a lift stand; excess pressure escapes | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 66 |
| S45 | KTM 690 Enduro: excess pressure escapes | KTM 690 Enduro 2010 owner's manual (`acquired/KTM/10_3211511_en_OM.pdf`) | 76 |
| S46 | KTM EXC TPI service schedule: perform the shock absorber service | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 53 |
| S47 | KTM EXC TPI: your authorized KTM workshop will be glad to help | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 55 |
| S48 | KTM 690 Enduro: the ±40 % is from the guideline table under the seat | KTM 690 Enduro 2010 owner's manual (`acquired/KTM/10_3211511_en_OM.pdf`) | 64 |
| S49 | CB500F: standard 4 with the index mark at the left end of the lower mounting bolt | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 92 |
| S50 | KTM EXC TPI: clickers counted from fully clockwise | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 56 |
| S51 | YW125Y: inner and outer tube — bends/damage/scratches → replace; never straighten a bent inner tube | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 157 |
| S52 | KTM EXC TPI: before every trip — bleed the fork legs | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 46 |
| S53 | CHF50 fork disassembly: grease in the bottom case, no oil | Honda CHF50 service manual (`honda/chf50_service_mirror.pdf`) | 226 |

**`drivetrain_service_v1`**

| # | claim as the item states it | document (library path) | PDF p. |
|---|---|---|---|
| D1 | KTM EXC chain tension 55–58 mm; repeat at different positions | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 90 |
| D2 | KTM: too tight wears chain, sprockets, transmission, wheel bearings; too loose may fall off | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 89 |
| D3 | CB500F slack 35–45 mm; do not ride over 60 mm; check at several points (kinked links) | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 80 |
| D4 | F800R chain deflection 30–40 mm at the tightest point | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 101 |
| D5 | KTM wear: 18 rollers ≤ 272 mm under 10–15 kg; else change the drivetrain kit | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 92 |
| D6 | CB500F: wear label red zone after adjusting → replace | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 83 |
| D7 | F800R: pull chain at the rear of the sprocket; teeth tips out of the links → specialist | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 102 |
| D8 | KTM: sprockets and chain always replaced together | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 91 |
| D9 | CB500F: new chain on worn sprockets wears rapidly | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 58 |
| D10 | KTM: sliding guard/piece — chain pin lower edge at or below → change | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 92 |
| D11 | KTM: chain guide light part worn → change | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 93 |
| D12 | KTM: rinse, chain cleaner, dry, chain spray | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 89 |
| D13 | CB500F O-ring chain: no steam, pressure washer, wire brush, gasoline | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 59 |
| D14 | F800R: lubricate every 1000 km at the latest | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 100 |
| D15 | KTM: adjuster markings equal relative to the reference marks → wheel aligned | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 91 |
| D16 | CB500F: index marks match; axle nut 88 N·m; lock nuts 21 N·m | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 82 |
| D17 | F800R: scale readings equal left and right | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 101 |
| D18 | F800R: 19 Nm chain tensioner locknut; 100 Nm rear axle | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 102 |
| D19 | CB500F: chain DID520V0, 112 links, 15T/41T | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 134 |
| D20 | KTM: rear sprocket nut 35 Nm Loctite 2701 | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 168 |
| D21 | KTM: engine sprocket screw 60 Nm Loctite 2701 | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 163 |
| D22 | XVS95CL: 45 N on a belt tension gauge at the check hole | Yamaha XVS95CL/XVS95CLC owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_BP6-28199-13_02.pdf`) | 65 |
| D23 | XVS95CL belt slack 6.0–8.0 mm; dealer adjusts | Yamaha XVS95CL/XVS95CLC owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_BP6-28199-13_02.pdf`) | 66 |
| D24 | XVS13AF belt slack 5.0–7.0 mm; check-hole marks 5.0 mm apart | Yamaha XVS13AF/XVS13AFC owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_3D8-28199-18_02.pdf`) | 64 |
| D25 | XVS95CL: belt condition and tension every 2500 mi (4000 km) | Yamaha XVS95CL/XVS95CLC owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_BP6-28199-13_02.pdf`) | 48 |
| D26 | XVS13AF: never oil or wax the belt | Yamaha XVS13AF/XVS13AFC owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_3D8-28199-18_02.pdf`) | 82 |
| D27 | R 1100 S: change rear wheel drive oil at operating temperature | BMW R 1100 S Service and Technical Booklet (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0422_ST_1000_R1100S_01.pdf`) | 6 |
| D28 | R 1100 S: every 40,000 km or at the latest every 2 years | BMW R 1100 S Service and Technical Booklet (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0422_ST_1000_R1100S_01.pdf`) | 8 |
| D29 | R 1100 S: hypoid GL 5; final drive approx. 0.25 l; SAE 90 above 5 °C, SAE 80 below | BMW R 1100 S Service and Technical Booklet (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0422_ST_1000_R1100S_01.pdf`) | 87 |
| D30 | R 850 R / R 1150 R final drive approx. 0.25 l | BMW R 850 R / R 1150 R Maintenance Instructions (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0428_WA_0504_R850-1150R_01.pdf`) | 67 |
| D31 | K 1200 RS final drive 0.25 l | BMW K 1200 RS Maintenance Instructions (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_K_0547_WA_0504_K1200RS_01.pdf`) | 70 |
| D32 | R 1100 S: Paralever shaft with two universal joints | BMW R 1100 S Service and Technical Booklet (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0422_ST_1000_R1100S_01.pdf`) | 81 |
| D33 | R 1100 S schedule: check swinging arm bearings (freedom from play) | BMW R 1100 S Service and Technical Booklet (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0422_ST_1000_R1100S_01.pdf`) | 7 |
| D34 | R 1200 GS: shaft drive with bevel gears | BMW R 1200 GS rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0A01_RM_0213_R1200GS_01.pdf`) | 156 |
| D35 | CB500F: shift to neutral; slack midway between the sprockets | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 80 |
| D36 | CB500F: inspect sprockets for worn or damaged teeth | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 58 |
| D37 | CB500F: cleaner designed for O-ring chains; can damage the rubber seals; keep lubricant off brakes and tires | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 59 |
| D38 | F800R: more often in wet, dusty or dirty conditions; wipe off excess | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 100 |
| D39 | CB500F: turn both adjusting nuts an equal number of turns | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 82 |
| D40 | XVS13AF: on the sidestand | Yamaha XVS13AF/XVS13AFC owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_3D8-28199-18_02.pdf`) | 64 |
| D41 | F800R: teeth tips between links OK; pulled over the teeth → specialist workshop | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 102 |
| D42 | R 850 R / R 1150 R: to bottom edge of filler opening | BMW R 850 R / R 1150 R Maintenance Instructions (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0428_WA_0504_R850-1150R_01.pdf`) | 67 |
| D43 | KTM: sliding piece criterion | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 93 |
| D44 | KTM EXC TPI chain tension: at the end of the chain sliding piece, lower run taut | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 90 |
| D45 | CB500F: side stand, neutral, lower half midway; links may be kinked and binding | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 80 |
| D46 | F800R: no weight applied, supported on its side stand | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 101 |
| D47 | XVS95CL: belt check — condition, replace if damaged | Yamaha XVS95CL/XVS95CLC owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_BP6-28199-13_02.pdf`) | 48 |
| D48 | XVS13AF: dealer adjusts the belt slack | Yamaha XVS13AF/XVS13AFC owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_3D8-28199-18_02.pdf`) | 65 |
| D49 | R 1100 S: alternatively SAE 80 W 90 | BMW R 1100 S Service and Technical Booklet (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0422_ST_1000_R1100S_01.pdf`) | 87 |
| D50 | R 850 R / R 1150 R: EPX 90 alternatively SAE 90 | BMW R 850 R / R 1150 R Maintenance Instructions (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0428_WA_0504_R850-1150R_01.pdf`) | 67 |
| D51 | K 1200 RS: Castrol EPX 90 or SAE 90 | BMW K 1200 RS Maintenance Instructions (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_K_0547_WA_0504_K1200RS_01.pdf`) | 70 |
| D52 | XVS95CL / XVS13AF title-page model names | Yamaha XVS95CL/XVS95CLC owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_BP6-28199-13_02.pdf`) | 1 |
| D53 | XVS13AF title page | Yamaha XVS13AF/XVS13AFC owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_3D8-28199-18_02.pdf`) | 1 |
| D54 | KTM EXC TPI chain tension check: raise the motorcycle with a lift stand | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 89 |

## Verification Checklist

- [x] Migration 069 applies on a fresh `init_db` database;
      `SCHEMA_VERSION >= 69`; 069 found by name
- [x] Upgrade 068 → 069 on a self-built 068 database changes no existing
      template or item row and adds exactly the four templates and 28
      items (`test_upgrade_from_68_inserts_only`)
- [x] `rollback_to_version(68)` removes all four templates and their
      items with no orphans; re-applying restores them
- [x] Every migration keeps its rollback (260's guard, green with 069)
- [x] Each template: category, powertrains, tier, active, duration; 7
      items each in contiguous sequence; the optional items exactly the
      planned ones (fork oil added by the refute)
- [x] Figures pinned per field; every machine-bound figure sits beside
      its machine; machines named as their documents name them
- [x] N1 (narrowed), N2, N3 stated; the u-joint item carries no
      measurement
- [x] F158 pins over all four templates, with the pattern seen to catch
      a planted reference
- [x] `workflow list` shows every slug whole at 80 columns (bug fix #1);
      `list --category <each>` and `workflow show <slug>` for all four
- [x] Known-bad controls planted, seen red, reverted: six (phase log)
- [x] Rule 3's four whole-tree checks, plus the F124 guard, 240c, 209B,
      244U, 244Y, 244V, 191D and 355, before every commit that touched
      the migration: 500 passed at the last; `finding_check` exit 0 in
      both variants
- [x] Regression of record by `regression.sh`: **9415 passed, 0 failed, 0 skipped, 0 errors** at `87566dd` (15 min 11 s wall, `python -m pytest -n auto --dist load`, exit 0)
- [x] Refute pass over every claim, in two rounds, with the `## Refuter
      pass` block in the phase log (`refute_check` exit 0)
- [x] Dry run on a copy of the live database, then the live apply after
      a backup (the phase log's Deploy section)

## Deviations from Plan

- **The extraction ran on the fallback route.** Rule 2 sends first-pass
  extraction to Subconscious. The sandbox proof passed (planted writes
  outside the box refused, the control inside succeeded), then
  Subconscious answered 403, "organization access is suspended". The
  same one-turn, no-tools call ran on `claude-opus-5-5@medium` in the
  same sandbox: 4 calls, 353,345 tokens, 259 facts, 259/259 quotes on
  their pages.
- **Two refute rounds, not one.** Round 1's corrections added 53 claims
  and rewrote text in every item, so a second fresh refuter read the new
  claims and the corrected text: 53 kept, 8 wording defects, all fixed.
  Five claims added after round 2 (B62, D54, S51–S53) are mechanically
  verified but have had no third round.
- **The refute changed more than v1.0 planned:**
  - N1 narrowed;
  - the fork-oil item made optional;
  - document names corrected throughout to their title pages;
  - "the makers disagree" on shocks replaced by each maker's actual
    position;
  - authored steps marked as the template's own.

  Titles are unchanged from the build. The suspension template's last
  planned item ("road check") never shipped: no document supported one,
  and the fork air bleed took its place.
- **Bug fix #1 touched code** (`cli/workflow.py`). v1.0 said no code
  change; the new slugs were the first longer than rich's elided column.
- **F160 filed.** 260's live chassis text names the YW125Y manual
  "Zuma 125". It is a live-row change, so it is not fixed here.
- **A working-rules slip:** two scripted edits (`sed -i` on one line of
  `database.py`; a count-asserted replace for three test fixes), both
  exact and read back. The phase log records it.
- **One scratch file went to `/tmp`** (`m069.txt`, a copy of migration
  069's text for a grep) instead of the scratchpad; removed at once.

## Results

| Metric | Value |
|---|---|
| Templates added | 4 (`tire_service_v1`, `brake_service_v1`, `suspension_service_v1`, `drivetrain_service_v1`), 28 items, 12 optional |
| Migration | 069, schema 68 → 69, inserts only; rollback peels it round trip |
| Production code | `migrations.py` (migration 069), 1 line in `database.py`, `cli/workflow.py` (bug fix #1: +8 / −4 lines, four of them a comment) |
| Tests added | 27 (`tests/test_phase261_service_workflows.py`) |
| Known-bad controls | 6 planted, seen red, reverted |
| Claims | 212, 329 verbatim anchors on their pages; 358 cited pages, 0 unclaimed |
| Refute | Round 1: 160 rows, 156 kept, 4 killed (N1 narrowed; B1, S4, S29 claim records). Round 2: 53 kept, 0 killed. About 58 item-text defects fixed across both |
| Bug fixes | 1 (`workflow list` elided slugs at 80 columns) |
| Findings filed | F160 |
| Floor | 9388 → 9415 |
| Regression of record | **9415 passed, 0 failed, 0 skipped, 0 errors** at `87566dd` (15 min 11 s wall, `python -m pytest -n auto --dist load`, exit 0) |

Key finding: the refute pass earns its cost on content that has already
passed every mechanical check. All 329 anchors were on their pages and
every citation resolved, yet round 1 still found about 50 places where the
text said more than, or other than, its page. Five of them would have
given a mechanic a wrong verdict:
- an unlabelled caliper bore;
- a chain-slack figure compared across methods;
- a disc "cleaned" instead of replaced;
- an owner's warning read as a workshop ban;
- a model name its document does not carry.

## Risks

- **Figures quoted from one machine read as universal.** Mitigated by
  naming the machine beside every figure, pinned by a test.
- **Item identity is prose** (F129's shape): the content is pinned in
  tests and seeded only inside the journal.
- **Five claims have had one mechanical check and no adversarial read**
  (B62, D54, S51–S53).
- **The Kymco Like 150i/50i owner's manual has no cover page.** Its name
  rests on its own p. 2 and p. 5 text, and its PDF metadata title is a
  leftover ("DOWNTOWN 125i").
