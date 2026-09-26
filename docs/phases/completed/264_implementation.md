# Phase 264 — Track N batch 2: winterization, de-winterization, engine break-in and valve adjustment

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-26 (v1.1: build, three refute rounds, regression, close-out — see Deviations)

**Branch:** `phase-264` (Opus session, main checkout).

**Carries four ROADMAP rows** (the operator's batching): 264
winterization, 265 de-winterization, 266 engine break-in, 268 valve
adjustment. One Step 0, one migration, one regression, one close-out,
one handoff. The ledger convention is 261's:
- row 264 closes with its CLOSED date and the regression line;
- rows 265, 266 and 268 close ✅ "folded into 264" with no date of their
  own;
- one history row (264) and one handoff.

## Goal

Four shop protocols as workflow content on the Phase 114 substrate, one
template per row, reachable through `motodiag workflow list/show`:

| row | slug | category | powertrains | items (optional) |
|---|---|---|---|---|
| 264 | `winterization_v1` | `winterization` | ice, electric, hybrid | 7 (fuel, carburetor, oil and cylinders, traction battery) |
| 265 | `de_winterization_v1` | `de_winterization` | ice, electric, hybrid | 7 (traction battery, fuel and oil) |
| 266 | `engine_break_in_v1` | `break_in` | ice, hybrid | 6 (cool-down) |
| 268 | `valve_adjustment_v1` | `valve_service` | ice, hybrid | 8 (screw and lock nut, shims, V-twin, the engine types with no figure) |

Every figure an item states names its machine and cites that machine's
document and PDF page, in the item's own text. Machines are named as
their documents' title pages name them. Where the makers disagree
(fuel before storage, cylinder oil, battery intervals, break-in limits,
"cold") the item gives each maker's position beside its machine and says
they cannot be merged. Where no document sets a figure (N1–N7 in
`264_step0.md`) the item says so and invents none. Steps no document
states are marked as the template's own.

**Two live-row changes, in the same migration** (the operator's scope):
1. **F158:** `generic_winterization_v1`'s description loses "Track N
   phase 264 expands." and names `winterization_v1` by slug. Its four
   items are untouched.
2. **F160:** the 8 "Zuma" mentions in 3 live `ppi_chassis_v1` items (ids
   18, 19, 21) become the title page's model code, "YW125Y". F160 says
   nine; the ninth is in migration 068's Python description, which is
   never seeded (S0-6).

CLI: none new.

Outputs:
- migration 070 `seasonal_breakin_valve_workflows` in
  `src/motodiag/core/migrations.py` (schema 69 → 70);
- `SCHEMA_VERSION` 69 → 70 in `src/motodiag/core/database.py`;
- `tests/test_phase264_seasonal_breakin_valve.py`;
- `tests/test_phase260_ppi_chassis.py`: its "Zuma 125" head-state pin
  moves to "YW125Y" with the fix;
- a new finding for the generic winterization items' unsupported figures;
- F160 closed.

## Logic

1. **Migration 070**, inside the one-shot journal:
   - four `INSERT OR IGNORE` template rows (tier `individual`, system user
     1), then 28 items keyed on the slug sub-select;
   - one `UPDATE` of `generic_winterization_v1.description`, keyed on its
     slug and on the old text;
   - one `UPDATE` of `ppi_chassis_v1`'s items: the one unique phrase "The
     Zuma manual's adjustment" first, then "Zuma 125" → "YW125Y", across
     the six text fields.

   `rollback_sql` deletes the four templates' items and the templates,
   reverses the F160 text in the opposite order, and restores the
   generic description verbatim.
2. **Data flow:** migration journal (existing DBs) / `db init` (new DBs) →
   `workflow_templates` + `checklist_items` → the existing accessors →
   the existing click commands → the terminal.

## Key Concepts

- **Content on a door that already opens** (259–261's shape): one
  migration plus its pins.
- **Claims before text** (261): a claims list with verbatim anchors
  checked on their pages, then the text, then a cross-check mapping every
  "PDF p." in the seeded text back to a claim for the machine named
  before it.
- **A figure travels with its method.** "Cold" is three definitions:
  below 35 °C (Honda, Kymco), room temperature (Yamaha), and 20 °C (KTM's
  V-twins). Break-in is limited by engine speed, by throttle opening, or
  by engine performance. Each figure keeps its measure.
- **F158 and F124** as in 259–261.

## Decisions

- **D1: four templates, one per row**, each its own enum category, which
  already exists.
- **D2: one migration (070)** for the four templates and both live
  re-points (the operator's scope).
- **D3: 264 adds `winterization_v1`; the generic stays the quick starter**
  (S0-4). The generic's unsupported figures are filed, not fixed.
- **D4: valve adjustment is one template with optional per-engine-type
  items** (S0-4). Inline-four, boxer and desmodromic engines share one
  item, whose content is the negatives.
- **D5: powertrains** as S0-5.
- **D6: the F160 text is "YW125Y"**, the title page's model code, matching
  069's text. The document is "the Yamaha YW125Y 2009 service manual".
- **D7: route.** Subconscious GLM-5.3 did the first-pass extraction, in
  a proven sandbox (S0-7). Opus chose every figure from its page.

## Non-goals

- No new tables, repo functions, CLI commands, API routes or mobile
  screens.
- The generic winterization items, F158's `known_issues` references and
  F159 stay with their own work.
- No crash, track-day or emissions content (batch 3).

## Claims for the refute pass

Every fact the seeded text states, with its library path and PDF page:
**106 claims** and **285 verbatim anchors**, every anchor on its cited page
(`s0/claims.py`, checked by `s0/verify.py`, which was seen to fail on a wrong
page and a corrupted figure). The cross-check `s0/xcheck.py` maps every
"PDF p." in the seeded text of the four templates back to a claim for the
machine named before it: **242 cited pages, 0 unclaimed**; its control
(withdrawing W23) turned exactly the one citation red.

Rounds: 85 claims (+ F1) refuted in round 1; 10 added from round 1's findings
and refuted in round 2; 9 added from round 2 and refuted in round 3; W30,
added from round 3's own quote, is checked mechanically only. Per-row
verdicts are in the phase log's Refuter pass.

**Negatives** (Step 0, whitespace-proof over all 260 PDFs, each with a
control on its page; widened by the refuters):

| # | negative | result |
|---|---|---|
| N1 | No document covers a desmodromic valve train | Kept: 0 pages; the "desmo" hits are "desmontar" and whitespace-joined words |
| N2 | No document names heat cycles; only Genuine prescribes a cool-down | **Narrowed by refute.** "Heat cycle": 0 pages, kept. "Only Genuine": killed by the Yamaha XC50J owner's manual, "After every hour of operation, stop the engine, and then let it cool for five to ten minutes" (p. 34); the item now names both makers |
| N3 | No service manual gives a break-in after an engine or top-end rebuild | Kept for service manuals; "only Genuine speaks to a rebuild" killed by SYM, "It is better to drive in low speed after replacing the engine" (T2 250i OM p. 17) |
| N4 | No inline-four document gives a valve clearance figure | Kept: 17 documents, 0 pages with a figure; control KTM 690 Enduro OM p. 174 |
| N5 | No boxer document gives a valve clearance figure | Kept: 5 documents, 0 pages; the words occur only as "Check/adjust valve clearances" (R 1100 S p. 7) |
| N6 | No storage procedure names an engine-oil grade | Kept: 211 storage-procedure pages, 0 with a grade token |
| N7 | No document asks for the brakes to be exercised after storage | Kept: 27 + 117 + 176 + 270 candidate pages, none in a storage or return context; control "Check the brakes" (R 850 R / R 1150 R MI p. 59) |

**`winterization_v1`**

| # | claim | document (library path) | PDF p. |
|---|---|---|---|
| W1 | 690 Enduro: check all parts for function and wear; service during storage | KTM 2010 690 Enduro owner's manual (`acquired/KTM/10_3211511_en_OM.pdf`) | 172 |
| W2 | CB500F: wash, wax except matte, chrome rust-inhibiting oil, lubricate chain | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 117 |
| W3 | F800R: lubricate lever and stand pivots; acid-free grease on chrome; oil change before lay-up; no load on either wheel; restoring: wax off, clean, charged battery, checklist | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 124 |
| W4 | XVS95CL long-term (60 days): repairs; fill tank + stabilizer + run 5 min; fuel cock off; carb drain; fogging or teaspoonful; ground electrodes; lubricate cables/stands; pressure then wheels off ground or turn monthly; muffler bag; battery maintenance charger; VRLA; monthly charge 0-30 °C | Yamaha XVS95CL/XVS95CLC owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_BP6-28199-13_02.pdf`) | 81 |
| W5 | XVS95CL: long term storage (60 days or more); tarp over wet machine → rust; damp cellars, stables (ammonia), chemicals; cool dry; engine and exhaust cool before covering; wash tires, brake cleaner or acetone; test braking before higher speeds | Yamaha XVS95CL/XVS95CLC owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_BP6-28199-13_02.pdf`) | 80 |
| W6 | 1290 SDR: fuel additive at last refuel; fill completely, lowest ethanol; short engine runs rust valves and exhaust | KTM 2023 1290 Super Duke R / RR owner's manual (`acquired/KTM/23_3214761_en_OM.pdf`) | 157 |
| W7 | 690 Enduro: tank as empty as possible; oil and filter, clean oil screens; battery 0-35 °C without direct sunshine | KTM 2010 690 Enduro owner's manual (`acquired/KTM/10_3211511_en_OM.pdf`) | 172 |
| W8 | People S: oil and filter step 1; drain carb, empty tank, spray rust-inhibiting oil; outdoors, heat/sparks/flame away; tablespoon 15-20 cc; cap secured away; cloth over hole | Kymco People S 50/125/200 owner's manual (`pdf/PeopleS-50-125-200.pdf`) | 60 |
| W9 | EXC TPI: fuel additive; add 2-stroke oil; gear oil change; lithium-ion 10-20 °C; lift stand; dry place without large temperature fluctuations; air-permeable tarp | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 154 |
| W10 | EXC TPI: non-porous traps humidity → corrosion; short runs condense and rust engine parts and exhaust | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 155 |
| W11 | XV250T1: drain float chambers by drain bolts, deposits, fuel into tank; stabilizer prevents tank rust and fuel deterioration | Yamaha XV250T1/XV250T1C owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_BJP-28199-15_02.pdf`) | 81 |
| W12 | CB500F: maintenance stand + block, both tires off ground; remove battery, charge, shaded ventilated; or disconnect negative; full-body cover, remove after rain | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 117 |
| W13 | PCX150: remove, full charge, charge every two weeks | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 390 |
| W14 | R 850/1150 R: disconnect earth lead; clock drains; warranty not accepted; ~4 months; 2 months if connected; fully recharge before restoring | BMW R 850 R / R 1150 R Maintenance Instructions (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0428_WA_0504_R850-1150R_01.pdf`) | 49 |
| W15 | R 850/1150 R: charger with limit voltage 14.4 V | BMW R 850 R / R 1150 R Maintenance Instructions (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0428_WA_0504_R850-1150R_01.pdf`) | 48 |
| W16 | Beverly: sealed battery six-monthly in open circuit; not used 1 month → periodic recharge; runs down in three months | Piaggio Beverly 125 service station manual (`pdf/beverly125.pdf`) | 78 |
| W17 | F800R: >4 weeks disconnect or trickle charger; BMW float charger | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 117 |
| W18 | Elettrica: prolonged non-use → full traction charge at least every three months; earth + differential breaker; 0 to -10 °C slow partial 6 h to 60 % | Vespa Elettrica service station manual (`elettrica_ws.pdf`) | 9 |
| W19 | Elettrica: sealed battery six-monthly while stored in open circuit | Vespa Elettrica service station manual (`elettrica_ws.pdf`) | 163 |
| W20 | XVS95CL: check and correct tire pressure then lift wheels off ground | Yamaha XVS95CL/XVS95CLC owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_BP6-28199-13_02.pdf`) | 81 |
| W21 | EXC TPI: non-porous covers named | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 155 |
| W22 | XVS95CL: cool dry place, porous cover | Yamaha XVS95CL/XVS95CLC owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_BP6-28199-13_02.pdf`) | 80 |
| W23 | 690 Enduro: short runs rust valves and exhaust (winter item text) | KTM 2010 690 Enduro owner's manual (`acquired/KTM/10_3211511_en_OM.pdf`) | 173 |
| W24 | XV250T1 long-term: turn the fuel cock lever to ON | Yamaha XV250T1/XV250T1C owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_BJP-28199-15_02.pdf`) | 80 |
| W25 | Beverly: sealed battery condition | Piaggio Beverly 125 service station manual (`pdf/beverly125.pdf`) | 77 |
| W26 | People S: maintenance or repairs before storage | Kymco People S 50/125/200 owner's manual (`pdf/PeopleS-50-125-200.pdf`) | 60 |
| W27 | People S: oil change after storage if more than 1 month | Kymco People S 50/125/200 owner's manual (`pdf/PeopleS-50-125-200.pdf`) | 61 |
| W30 | Beverly: not used 1 month or more; runs down in the course of three months | Piaggio Beverly 125 service station manual (`pdf/beverly125.pdf`) | 78 |
| W28 | Elettrica: prolonged exposure 0 to -10 °C | Vespa Elettrica service station manual (`elettrica_ws.pdf`) | 9 |
| W29 | XVS95CL generic carburetor step: clean container, retighten drain bolt | Yamaha XVS95CL/XVS95CLC owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_BP6-28199-13_02.pdf`) | 81 |

**`de_winterization_v1`**

| # | claim | document (library path) | PDF p. |
|---|---|---|---|
| R1 | F800R restoring: remove wax, clean, charged battery, checklist before starting | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 124 |
| R2 | People S removal: uncover/clean; oil if >1 month; charge battery; drain excess rust-inhibiting oil; fresh gasoline; pre-ride; test ride low speeds safe area away from traffic | Kymco People S 50/125/200 owner's manual (`pdf/PeopleS-50-125-200.pdf`) | 61 |
| R3 | EXC TPI: remove from lift stand; checks and maintenance measures; test ride | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 155 |
| R4 | R 850/1150 R restoring: wax off, clean, charged battery, safety checks, check brakes, check tyre pressures | BMW R 850 R / R 1150 R Maintenance Instructions (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0428_WA_0504_R850-1150R_01.pdf`) | 59 |
| R5 | XVS95CL: muffler bag fitted for storage | Yamaha XVS95CL/XVS95CLC owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_BP6-28199-13_02.pdf`) | 81 |
| R6 | Beverly: OCV >12.60 V install; <12.60 renewal recharge; 14.40-14.70 V; 10-12 h, min 6 max 24; Vaseline terminals | Piaggio Beverly 125 service station manual (`pdf/beverly125.pdf`) | 78 |
| R7 | R 1100 S restoring: charged battery, grease battery terminals, check brakes, tyre pressures | BMW R 1100 S Service and Technical Booklet (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0422_ST_1000_R1100S_01.pdf`) | 79 |
| R8 | R 850/1150 R: always fully recharge before restoring to use | BMW R 850 R / R 1150 R Maintenance Instructions (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0428_WA_0504_R850-1150R_01.pdf`) | 49 |
| R9 | 1190 Adventure: set time and date if battery was removed | KTM 2016 1190 Adventure owner's manual (`acquired/KTM/16_3213388_en_OM.pdf`) | 206 |
| R10 | R 850/1150 R: do not jump-start a flat battery; recharge; control units | BMW R 850 R / R 1150 R Maintenance Instructions (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0428_WA_0504_R850-1150R_01.pdf`) | 48 |
| R11 | PCX150: MF battery performance deteriorates after 2-3 years | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 390 |
| R12 | Elettrica: charge to 100 %; normal charge only above 0 °C; ancillary battery may not be full; charged while running | Vespa Elettrica service station manual (`elettrica_ws.pdf`) | 9 |
| R13 | Elettrica: below 10 % speed limited, icon flashes | Vespa Elettrica service station manual (`elettrica_ws.pdf`) | 90 |
| R14 | 690 Enduro: after storage refuel; test ride | KTM 2010 690 Enduro owner's manual (`acquired/KTM/10_3211511_en_OM.pdf`) | 173 |
| R15 | People S pre-ride: engine oil add, leaks; tires; fuel; brakes; steering; instruments; lights and horn; chassis | Kymco People S 50/125/200 owner's manual (`pdf/PeopleS-50-125-200.pdf`) | 25 |
| R16 | EXC TPI before-use list | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 46 |
| R17 | CB500F: after storage inspect all Maintenance Schedule items | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 117 |
| R18 | EXC TPI: level below marking = leaking or linings worn; do not continue riding | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 101 |
| R19 | XVS95CL: tire pressure on cold tires, ambient temperature | Yamaha XVS95CL/XVS95CLC owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_BP6-28199-13_02.pdf`) | 58 |
| R20 | XVS95CL: brake cleaner or acetone; test braking and cornering before higher speeds | Yamaha XVS95CL/XVS95CLC owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_BP6-28199-13_02.pdf`) | 80 |
| R21 | Beverly: do not reverse the connections; constant current mode 1/10 capacity | Piaggio Beverly 125 service station manual (`pdf/beverly125.pdf`) | 78 |
| R22 | Elettrica: prolonged non-use, full charge at least every three months | Vespa Elettrica service station manual (`elettrica_ws.pdf`) | 9 |
| R23 | Beverly: constant current charge time 5 h; really flat below 12.6 V, never exceed 8 h | Piaggio Beverly 125 service station manual (`pdf/beverly125.pdf`) | 78 |

**`engine_break_in_v1`**

| # | claim | document (library path) | PDF p. |
|---|---|---|---|
| E1 | Buddy 125: run-in for new engine or new components; 0-100 miles 1/2 throttle, cool 10 min after every 30 min; first 500 miles avoid WOT / high temperature | Genuine Buddy 125 owner's manual (`manuals/genuine_buddy125.pdf`) | 25 |
| E2 | Buddy 125: 0~95 miles cool 5-10 min per hour; gear oil after 200 miles; problems → dealers | Genuine Buddy 125 owner's manual (`manuals/genuine_buddy125.pdf`) | 27 |
| E3 | SR400: 0-1600 km; parts wear and polish to clearances; 3500 r/min 0-1000; 4200 1000-1600; no prolonged full throttle/overheating; red zone | Yamaha SR400 owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_2RD-28199-13_02.pdf`) | 39 |
| E4 | 690 Enduro: 6,000 rpm first 1,000 km, 7,800 after; avoid fully opening | KTM 2010 690 Enduro owner's manual (`acquired/KTM/10_3211511_en_OM.pdf`) | 46 |
| E5 | 1190 Adventure: 6,500 rpm first 1,000 km, 10,250 after | KTM 2016 1190 Adventure owner's manual (`acquired/KTM/16_3213388_en_OM.pdf`) | 86 |
| E6 | R 1200 GS: vary throttle and rpm; avoid constant rpm; twisting hilly roads; <5000 min-1; check 500-1200 km | BMW R 1200 GS rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0A01_RM_0213_R1200GS_01.pdf`) | 85 |
| E7 | XVS95CL: 1/3 throttle 0-1000 km; 1/2 1000-1600 km; oil and filter after 1000 km | Yamaha XVS95CL/XVS95CLC owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_BP6-28199-13_02.pdf`) | 41 |
| E8 | People S: <1/2 throttle initial 300 miles (600 km); <3/4 to 600 miles (1,000 km); vary; loaded/unloaded/cool; some stress; not excessive drive line load; constant low speed glazing; fasteners tightened, contaminated oil replaced | Kymco People S 50/125/200 owner's manual (`pdf/PeopleS-50-125-200.pdf`) | 23 |
| E9 | EXC TPI: <70 % first 3 operating hours; idle may change; 1,400-1,500 rpm; adjust | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 40 |
| E10 | CB500F: first 300 miles (500 km): full-throttle starts, rapid acceleration, hard braking, rapid down-shifts | Honda CB500F/FA 2018 owner's manual (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 14 |
| E11 | People S: below 25 MPH (40 KPH) first 600 miles (1,000 km) | Kymco People S 50/125/200 owner's manual (`pdf/PeopleS-50-125-200.pdf`) | 40 |
| E12 | F800R: avoid high-speed main roads; exceeding rpm → increased wear; no full-load acceleration | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 66 |
| E13 | F800R: avoid low engine speeds at full load; do not omit first inspection 500-1200 km | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 67 |
| E14 | PCX150: engine oil initial 600 mi (1,000 km) or 1 month | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 77 |
| E15 | PCX150: first scheduled maintenance compensates initial wear of break-in | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 3 |
| E16 | People S: initial service after one month or 200 miles (300 km); most important service | Kymco People S 50/125/200 owner's manual (`pdf/PeopleS-50-125-200.pdf`) | 25 |
| E17 | F800R: running-in check between 500 and 1200 km | BMW F 800 R rider's manual (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_F_0217_RM_0309_F800R_01.pdf`) | 141 |
| E18 | XVS95CL: engine trouble during break-in → Yamaha dealer immediately | Yamaha XVS95CL/XVS95CLC owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_BP6-28199-13_02.pdf`) | 42 |
| E19 | People S: constant low speed can glaze parts | Kymco People S 50/125/200 owner's manual (`pdf/PeopleS-50-125-200.pdf`) | 23 |
| E20 | XC50J: 0-150 km, after every hour stop engine and let it cool 5-10 minutes | Yamaha XC50J owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_1TS-F8199-15_02.pdf`) | 34 |
| E21 | SYM T2 250i: better to drive in low speed after replacing the engine | SYM T2 250i owner's manual (`v2/sympdf/T2_Owner_Manual.pdf`) | 17 |
| E22 | EXC TPI: first 5 operating hours < 100 %; check idle speed regularly | KTM 2022 250/300 EXC TPI owner's manual (`acquired/KTM/22_3214421_en_OM.pdf`) | 40 |
| E23 | Buddy 125: run-in to 620 miles | Genuine Buddy 125 owner's manual (`manuals/genuine_buddy125.pdf`) | 27 |
| E24 | SYM T2 250i: first 1,000 km low speed; oil change after first 300 km | SYM T2 250i owner's manual (`v2/sympdf/T2_Owner_Manual.pdf`) | 17 |

**`valve_adjustment_v1`**

| # | claim | document (library path) | PDF p. |
|---|---|---|---|
| V1 | PCX150: cold below 35 °C; T mark; rocker slack confirms compression TDC; no slack → one full turn; gauge between screw and stem; 0.10 ± 0.02 / 0.24 ± 0.02 | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 82 |
| V2 | CHF50: cold below 35 °C; lobe faces cylinder side; one revolution; gauge between lifter and shim; IN 0.10 ± 0.03 (text layer '+', rendered ±), EX 0.19 ± 0.03 | Honda CHF50 service manual (`honda/chf50_service_mirror.pdf`) | 64 |
| V3 | People S 250: cold below 35 °C; IN 0.1 EX 0.1; check again after lock nut tightened | Kymco People / People S 250 service manual (`pdf/kymco_people_s250_sm.pdf`) | 59 |
| V4 | YW125Y: cold engine room temperature; TDC compression; counterclockwise; punch mark on sprocket; IN 0.10~0.14 EX 0.16~0.20 | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 62 |
| V5 | 1190 Adventure: 2-cylinder 75° V; DOHC 4 valves; at 20 °C exhaust 0.25-0.30, intake 0.10-0.15 | KTM 2016 1190 Adventure owner's manual (`acquired/KTM/16_3213388_en_OM.pdf`) | 209 |
| V6 | XVS95CL: cold; dealer; improper mixture, noise, engine damage | Yamaha XVS95CL/XVS95CLC owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_BP6-28199-13_02.pdf`) | 58 |
| V7 | YW125Y: TDC mark on AC magneto rotor on pointer; locknut; gauge screw/valve tip; 7 Nm; tool 90890-01311 | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 63 |
| V8 | YW125Y: measure again, repeat; breather/covers 7 Nm, plug 13 Nm | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 64 |
| V9 | PCX150: slight drag; oil on lock nut threads and seat; 10 N·m; recheck; duct rubber seal | Honda PCX150 (2013–2017) service manual (`pdf/honda_pcx_2013_2017_sm.pdf`) | 83 |
| V10 | 690 Enduro: valve play cold 0.07-0.13 | KTM 2010 690 Enduro owner's manual (`acquired/KTM/10_3211511_en_OM.pdf`) | 174 |
| V11 | GTS 300: intake 0.10, discharge 0.15 | Vespa GTS Super 300 ie (2008) service station manual (`pdfs/vespa_gts300_shop.pdf`) | 9 |
| V12 | People S 250: low compression — valve clearance too small | Kymco People / People S 250 service manual (`pdf/kymco_people_s250_sm.pdf`) | 60 |
| V13 | People S 250: adjusting nut 8.8 N-m, engine oil to threads | Kymco People / People S 250 service manual (`pdf/kymco_people_s250_sm.pdf`) | 81 |
| V14 | GTS 300: tappet set screw lock nut 6÷8 | Vespa GTS Super 300 ie (2008) service station manual (`pdfs/vespa_gts300_shop.pdf`) | 16 |
| V15 | CHF50 shims: A=(B-C)+D; 69 thicknesses 1.200-2.900 mm 0.025; don't drop; mark; tweezers/magnet; micrometer; reface seat >2.900; rotate several times; recheck | Honda CHF50 service manual (`honda/chf50_service_mirror.pdf`) | 65 |
| V16 | XVS95CL: check and adjust when cold every 16000 mi (25000 km) | Yamaha XVS95CL/XVS95CLC owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_BP6-28199-13_02.pdf`) | 45 |
| V17 | 1290 SDR: at 20 °C intake 0.10-0.15, exhaust 0.25-0.30 | KTM 2023 1290 Super Duke R / RR owner's manual (`acquired/KTM/23_3214761_en_OM.pdf`) | 161 |
| V18 | XVS95CL: V-type, 2-cylinder | Yamaha XVS95CL/XVS95CLC owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_BP6-28199-13_02.pdf`) | 82 |
| V19 | 1190 Adventure: check valve clearance with air filter and spark plugs removed | KTM 2016 1190 Adventure owner's manual (`acquired/KTM/16_3213388_en_OM.pdf`) | 103 |
| V20 | YZFR6L: check and adjust cold every 26600 mi (42000 km) | Yamaha YZFR6L/YZFR6LC owner's manual (`acquired/Yamaha/library_om_contents_pdf_10_BN6-28199-13_02.pdf`) | 60 |
| V21 | K 1200 RS: bucket-type tappets, two chain-driven overhead camshafts | BMW K 1200 RS Maintenance Instructions (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_K_0547_WA_0504_K1200RS_01.pdf`) | 63 |
| V22 | R 1100 S: tappets and short pushrods | BMW R 1100 S Service and Technical Booklet (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0422_ST_1000_R1100S_01.pdf`) | 80 |
| V23 | R 1100 S schedule: Check/adjust valve clearances | BMW R 1100 S Service and Technical Booklet (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0422_ST_1000_R1100S_01.pdf`) | 7 |
| V24 | CHF50: B = recorded valve clearance | Honda CHF50 service manual (`honda/chf50_service_mirror.pdf`) | 65 |
| V25 | YW125Y: valve cover 7 Nm | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 64 |
| V26 | People S 250: loosen the lock nut and adjust by turning the adjusting nut | Kymco People / People S 250 service manual (`pdf/kymco_people_s250_sm.pdf`) | 59 |
| V27 | CHF50: rotate the drive pulley counterclockwise several times | Honda CHF50 service manual (`honda/chf50_service_mirror.pdf`) | 65 |
| V28 | 690 Enduro: one valve play figure | KTM 2010 690 Enduro owner's manual (`acquired/KTM/10_3211511_en_OM.pdf`) | 174 |

**`ppi_chassis_v1` (F160)**

| # | claim | document (library path) | PDF p. |
|---|---|---|---|
| F1 | YW125Y SM title page: 2009 MOTORCYCLE SERVICE MANUAL Model : YW125Y | Yamaha YW125Y 2009 service manual (`pdf/yamaha_zuma125_2009_sm.pdf`) | 1 |

## Verification Checklist

- [x] Migration 070 applies on a fresh `init_db` database;
      `SCHEMA_VERSION >= 70`; 070 found by name
- [x] Upgrade 069 → 070 on a self-built 069 database changes exactly the 1
      template description and the 3 chassis items that said "Zuma", and
      adds exactly the four templates and their 28 items
      (`test_upgrade_from_69_changes_exactly_the_scoped_rows`)
- [x] `rollback_to_version(69)` restores every changed row byte-identical
      (bar `updated_at`), removes the new rows with no orphans, and
      re-applies
- [x] Every migration keeps its rollback (and two round trips catch what
      that guard cannot, control 5)
- [x] Each template: category, powertrains, tier, duration; titles and
      sequence; optional items exactly as planned
- [x] Figures pinned per field; every machine-bound figure beside its
      machine; machines named as their documents name them; no "Zuma" in
      any workflow row
- [x] The negatives stated where the items rely on them, as narrowed by
      the refute; the no-figure engine-type item carries no clearance
- [x] F158 pins over the four templates and the re-pointed generic
      description
- [x] `workflow list --category <each>` and `workflow show <slug>` for
      all four
- [x] Known-bad controls planted, seen red, reverted: six (phase log)
- [x] Rule 3's four whole-tree checks, plus the F124 guard and the
      related suites, before every commit that touched the migration:
      514 passed at the last; `finding_check` exit 0 in both variants
- [x] Regression of record by `regression.sh`: **9446 passed, 0 failed, 0 skipped, 0 errors** at `717dc47` (34 min 41 s wall, `python -m pytest -n auto --dist load`, exit 0)
- [x] Refute pass over every claim, three rounds, `refute_check` exit 0
      (and seen to fail on a planted bad block)
- [x] Backup, a dry run on a copy of live, the scope check (seen to fail
      on a planted out-of-scope change), and the diff with before and
      after text for every changed row, prepared for the operator. **The
      live apply and the merge wait for the operator's answer** (rule 1;
      the phase log's Deploy section)

## Deviations from Plan

- **Three refute rounds, not one.** Round 1's corrections added 10
  claims and rewrote text in every template, so a second fresh refuter
  read them. Its corrections added 9 more and rewrote 17 sentences, so a
  third read those. W30, from round 3's own quote, is mechanically
  verified only.
- **Two Step 0 negatives were narrowed by the refute:**
  - N2 ("only Genuine prescribes a cool-down"): the Yamaha XC50J does too;
  - N3 as worded in the item ("only Genuine speaks to a rebuild"): SYM
    speaks to a replaced engine.

  Both items now carry the new makers, with citations.
- **Two existing pins moved with the phase's own changes:**
  - 260's `test_figures_name_their_machines` pinned "Zuma 125" on a
    fresh database. It now pins "YW125Y" and no "Zuma".
  - 114's `test_list_by_powertrain` pinned "no winterization for
    electric". It is now scoped to the generic slug, with the positive
    for `winterization_v1`.
- **F160 counted 8 live mentions, not 9.** The ninth is migration 068's
  Python description, never seeded. That code is history and is left as
  written.
- **F161 filed:** the generic winterization items' unsupported figures.
  A first draft called 13.2–13.6 V "a charging-system figure". A check of
  the 19 pages before the commit found it is a fully charged battery's
  resting voltage, and the finding and Step 0 were corrected.
- **The merge waits with the live apply.** `init_db` applies pending
  migrations, so a merged 070 could reach the live rows through any
  command run against `data/motodiag.db` before the operator answers.
  The close-out commit, the dry run and the diff are on `phase-264`.
- **Subconscious took 3–5 turns per call where 2 is the measured norm,
  and one call looped.** Its `machine` field also reintroduced "Zuma".
  Nothing from the model was used unchecked.
- **The Read tool could not render PDFs in this session** (no poppler).
  Pages were cut out with pypdf and rendered with `sips`.
- **Scripted edits:** the header line of `docs/FOLLOWUPS.md` and the
  scratchpad scripts were written by script. Every edit to source and
  tests went through the Edit tool.

## Results

| Metric | Value |
|---|---|
| Templates added | 4 (`winterization_v1` 7 items, `de_winterization_v1` 7, `engine_break_in_v1` 6, `valve_adjustment_v1` 8), 28 items, 11 optional |
| Live rows changed | 1 template description (F158), 3 chassis items (F160: 8 mentions → YW125Y) |
| Migration | 070, schema 69 → 70; rollback round-trips byte-identical (bar `updated_at`) |
| Production code | `migrations.py` (migration 070), 1 line in `database.py` |
| Tests | 31 added (`tests/test_phase264_seasonal_breakin_valve.py`); 2 existing pins moved (114, 260) |
| Known-bad controls | 6 planted, seen red, reverted; plus the cross-check, anchor, scope-check and refute-check controls |
| Claims | 106, 285 verbatim anchors on their pages; 242 cited pages, 0 unclaimed |
| Refute | Round 1: 93 rows, 84/85 claims kept (W16 page-only kill), N2 and N3 narrowed, about 50 text defects fixed. Round 2: 10 kept, 17 fixed. Round 3: 9 kept, 4 fixed |
| Bug fixes | none |
| Findings | F161 and F162 filed; F160 fixed by 070 (closed at the live apply) |
| Floor | 9415 → 9446 |
| Regression of record | **9446 passed, 0 failed, 0 skipped, 0 errors** at `717dc47` (34 min 41 s wall, `python -m pytest -n auto --dist load`, exit 0) |

Key finding: **each refute round found defects that the round before had
put in.** Round 1's fixes left two conditions dropped and one maker
contradicted, which round 2 found. Round 2's fixes dropped four more
qualifiers, which round 3 found. A corrected sentence is new content. It
needs the same read as the first draft, and "the fix landed" is itself a
claim to check.

## Risks

- **Figures read as universal.** Mitigated by naming the machine beside
  every figure, pinned by `MACHINE_OF`.
- **W30 has had one mechanical check and no adversarial read.**
- **260's live chassis text still carries two defects** the valve
  refuter found outside F160's scope (the name-only change): "calls the
  same movement binding or looseness" (p. 93 names the fault found), and
  an EXC p. 76 citation that could be either KTM EXC manual. Filed as
  F162, not changed.
- **Item identity is prose** (F129's shape): the content is pinned in
  tests and seeded only inside the journal.
