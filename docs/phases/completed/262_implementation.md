# Phase 262 — Track N batch 3: crash support, track-day preparation, and emissions compliance (California first)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-26 (v1.1: build, five refute rounds, regression, close-out — see Deviations)

**Branch:** `phase-262` (Opus session, main checkout).

**Carries three ROADMAP rows** (the operator's batching): 262 crash and
insurance claim support, 263 track-day and race prep, 267 emissions and
smog compliance. One Step 0, one migration, one regression, one
close-out, one handoff. The ledger convention is 261's and 264's:
- row 262 closes with its CLOSED date and the regression line;
- rows 263 and 267 close ✅ "folded into 262" with no date of their own;
- one history row (262) and one handoff.

## Goal

Three shop protocols as workflow content on the Phase 114 substrate, one
template per row, reachable through `motodiag workflow list/show`, plus
three fixes to live rows in the same migration:

| row | slug | category | powertrains | items (optional) |
|---|---|---|---|---|
| 262 | `crash_support_v1` | `crash_support` | ice, electric, hybrid | 8 (the claim record; both California items) |
| 263 | `track_prep_v1` | `track_prep` | ice, hybrid | 6 (rider aids) |
| 267 | `emissions_v1` | `emissions` | ice, hybrid | 7 (the evaporative system) |

Scope is the operator's answer to Step 0's fork (`262_step0.md`, S0-4):
- **262:** the makers' post-crash inspection, plus California's salvage
  and total-loss rules from the DMV's own text. Photo documentation,
  damage estimation and insurance claims are stated as unsourced (N9).
- **263:** the makers' track preparation. Safety wire, race coolant,
  tech inspection and number plates are stated as the sanctioning
  body's rules; no maker's document in the library gives them (N10–N12).
- **267:** the makers' emission pages plus the regulators' own text
  (BAR, CARB, DMV, EPA), acquired by script (S0-8).
- **Provenance:** named in the text ("California DMV, Vehicle Industry
  Registration Procedures Manual, 19.015"); the claims table records
  provenance `regulation` or `maker` per claim. No schema change.

Every figure an item states names its machine and cites that machine's
document and PDF page. Every rule from a regulator names the regulator
and the document (a web page is cited by its section title, as it has no
pages). Machines and documents are named from their title pages.

**Three live-row fixes, in the same migration** (the operator's scope):
1. **F161:** `generic_winterization_v1`'s unsupported figures go:
   - item 6's "Run engine 5 minutes to circulate", stated as universal,
     and its expected_fail;
   - item 7's "recommended winter weight (typically 10W-40)";
   - item 8's expected_pass "reading float voltage (13.2V-13.6V)".

   Each becomes a pointer to `winterization_v1`, which gives each maker's
   own figure with its page. The brand "Sta-Bil" in item 6's sentence goes
   with the figure (no maker's document names a product). Item 9 carries
   no figure and is not changed.
2. **F162:** `ppi_chassis_v1` item 18:
   - "the YW125Y service manual calls the same movement binding or
     looseness (PDF p. 93)" becomes "checks the same movement for binding
     or looseness";
   - "the KTM 250/300 EXC owner's manual (PDF p. 76)" in its description
     names the manual 260 cited: "the KTM 2022 250/300 EXC TPI owner's
     manual".
3. **W30:** `winterization_v1` item 56's Beverly sentence gets its first
   adversarial read in refute round 1. It is kept, fixed or dropped on
   the verdict. (v1.1: kept on its words; fixed on its context, a first-use
   caution box beside the six-month rule.)

CLI: none new.

Outputs:
- migration 071 `crash_track_emissions_workflows` in
  `src/motodiag/core/migrations.py` (schema 70 → 71);
- `SCHEMA_VERSION` 70 → 71 in `src/motodiag/core/database.py`;
- `tests/test_phase262_crash_track_emissions.py`;
- `tests/test_phase264_seasonal_breakin_valve.py`: its F162 head-state
  pin moves with the fix (and item 5's pins, if W30 changes);
- F161 and F162 closed at the live apply.

## Logic

1. **Migration 071**, inside the one-shot journal:
   - three `INSERT OR IGNORE` template rows (tier `individual`, system
     user 1), then 21 items keyed on the slug sub-select;
   - F161: three `UPDATE`s on `generic_winterization_v1`'s items, each
     keyed on the template's slug, the item's sequence number and the
     item's exact old text;
   - F162: one `UPDATE` on `ppi_chassis_v1`'s steering item, keyed on
     its exact old text;
   - W30: on the verdict.

   `rollback_sql` deletes the three templates' items and the templates,
   and restores every changed field verbatim, keyed on its new text.
2. **Data flow:** migration journal (existing DBs) / `db init` (new DBs) →
   `workflow_templates` + `checklist_items` → the existing accessors →
   the existing click commands → the terminal.

## Key Concepts

- **Content on a door that already opens** (259–264's shape).
- **Claims before text** (261): a claims list with verbatim anchors
  checked on their pages (`s0/claims262.py`, `s0/verify262.py`), then the
  text, then a cross-check that maps every "PDF p." and every regulator
  citation in the seeded text back to a claim (`s0/xcheck262.py`).
- **Regulator text is not a manual.** It is authoritative on what the
  law requires and says nothing about how a given machine behaves; the
  items keep the two apart and name which is which.
- **A negative is part of the content** where the row asks for something
  no document gives (photo standards, safety wire).
- **F158 and F124** as in 259–264.

## Decisions

- **D1: three templates, one per row**, each in its own existing enum
  category.
- **D2: one migration (071)** for the templates and the three fixes (the
  operator's scope).
- **D3: the regulators' text is acquired by script** (`acquire.py`'s
  Fetcher and `save()`), never by a model (F141), and only from hosts whose
  robots.txt permits it. leginfo and the eCFR API are excluded (S0-8).
- **D4: provenance in the text**, per the operator (S0-4).
- **D5: powertrains.** `crash_support_v1` all three. `track_prep_v1`
  and `emissions_v1` ICE and hybrid: every track document in the library
  is an ICE machine's, and an electric machine has no exhaust or
  evaporative emissions. S0-5 proposed all three for track prep. Measured
  against the documents, none speaks for an electric machine on a track.
- **D6: California first, and only California,** for the salvage and
  smog items. Other states' rules are not in the library.
- **D7: route.** Subconscious GLM-5.3 did the first-pass extraction in a
  proven sandbox (S0-7). Its quotes were checked on their pages: 250 of
  325 were there. Opus chooses every figure from the page itself.

## Non-goals

- No new tables, columns, repo functions, CLI commands, API routes or
  mobile screens.
- No state other than California for the salvage or smog items.
- No photo, estimating or insurance-claim standard is invented (N9).
- No race-organiser rules are invented (N10–N12).
- F158's `known_issues` references and F159 stay with their own work.

## Planned items

**`crash_support_v1`** — 1 safety, the law and the first look; 2 frame
(check, and change rather than repair); 3 handlebar and controls (replace,
never straighten); 4 front fork; 5 axles and wheels (runout against the
machine's limit); 6 hidden damage and the qualified check; 7 the claim
record (optional; N9); 8 California: total loss, salvage certificate, and
registering a repaired total loss (optional).

**`track_prep_v1`** — 1 intended use and warranty; 2 road equipment off
(mirrors, number-plate carrier, turn indicators) and back on for the
road; 3 suspension for the rider and the track; 4 rider aids on a closed
track; 5 service intervals when raced; 6 what the sanctioning body sets
(safety wire, coolant, tech inspection, number plates: N10–N12).

**`emissions_v1`** — 1 California Smog Check and motorcycles; 2 what
standard it was built to (the label, the California model, CARB's
Executive Order); 3 tampering: what counts and what the law says;
4 aftermarket parts and the CARB Executive Order label; 5 the catalytic
converter; 6 the evaporative system (optional); 7 emission maintenance,
records and the warranty.

## Claims for the refute pass

Every fact the seeded text states, with its library path and PDF page
(a regulator web page is page 1), and its provenance: **155 claims** (126
`maker`, 29 `regulation`) and **294 verbatim anchors**, every anchor on its
cited page (`s0/claims262.py`, checked by `s0/verify262.py`, which was seen
to fail on a wrong page and on corrupted figures, on a manual page and on a
regulator page). The cross-check `s0/xcheck262.py` maps every "PDF p."
and every regulator page named in the seeded text back to a claim for the
document named before it: **135 cited pages and 12 regulator citations, 0
unclaimed**; its control (withdrawing C17, and later C32) turned exactly
that citation red. C39, C40, C46, C49 and C50 were checked but are cited by
no shipped sentence since round 5's drop (F164). Per-round verdicts are in
the phase log's Refuter pass.

**Negatives** (Step 0, whitespace-proof over the library and the
regulator pages, each with a control on its page; widened by the
refuters):

| # | negative | result |
|---|---|---|
| N8 | No document gives a frame measurement to check a frame against | Kept: every "frame … dimension" hit is overall vehicle size; control YW125Y SM p. 34 |
| N9 | No photo, damage-estimating or insurance-claim standard | Kept; BAR's written estimate (p. 27, 32) is the Automotive Repair Act's, applied to Smog Check work, and the item says so |
| N10 | No safety-wire or lockwire procedure | Kept; the "lock wire" hits are a Kymco Agility 50 seat lock wire (p. 32) and the KTM 1290 Super Duke R / RR rear axle nut's locking wires (p. 129) |
| N11 | No coolant for track or race use | Kept; KTM says "Do not use pure water" (EXC TPI p. 170), now cited beside the event's rule |
| N12 | No tech-inspection or race-number rule | Kept; "technical inspection" is a parts-and-accessories note in two BMW booklets (p. 4 of each) |

| # | template | claim | document (library path) | page | provenance |
|---|---|---|---|---|---|
| C1 | crash_support_v1 | Honda's crash paragraph | Honda CB500F/FA 2018 OM (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 9 | maker |
| C2 | crash_support_v1 | lean-angle sensor reset | Honda CB500F/FA 2018 OM (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 113 | maker |
| C3 | crash_support_v1 | KTM after a fall | KTM 2023 1290 Super Duke R / RR OM (`acquired/KTM/23_3214761_en_OM.pdf`) | 83 | maker |
| C4 | crash_support_v1 | title page | KTM 2023 1290 Super Duke R / RR OM (`acquired/KTM/23_3214761_en_OM.pdf`) | 1 | maker |
| C5 | crash_support_v1 | KTM 690 after a fall | KTM 2010 690 Enduro OM (`acquired/KTM/10_3211511_en_OM.pdf`) | 53 | maker |
| C6 | crash_support_v1 | KTM 950 SE handlebar | KTM 2008 950 Super Enduro R OM (`acquired/KTM/08_3211240_OM_EN.pdf`) | 27 | maker |
| C7 | crash_support_v1 | title page | KTM 2008 950 Super Enduro R OM (`acquired/KTM/08_3211240_OM_EN.pdf`) | 1 | maker |
| C8 | crash_support_v1 | KTM 1290 handlebar | KTM 2023 1290 Super Duke R / RR OM (`acquired/KTM/23_3214761_en_OM.pdf`) | 65 | maker |
| C9 | crash_support_v1 | YW125Y handlebar | Yamaha YW125Y 2009 SM (`pdf/yamaha_zuma125_2009_sm.pdf`) | 165 | maker |
| C10 | crash_support_v1 | throttle cable | Honda PCX150 (2013–2017) SM (`pdf/honda_pcx_2013_2017_sm.pdf`) | 78 | maker |
| C11 | crash_support_v1 | KTM frame | KTM 2022 250/300 EXC TPI OM (`acquired/KTM/22_3214421_en_OM.pdf`) | 94 | maker |
| C12 | crash_support_v1 | title page | KTM 2022 250/300 EXC TPI OM (`acquired/KTM/22_3214421_en_OM.pdf`) | 1 | maker |
| C13 | crash_support_v1 | CHF50 bent frame | Honda CHF50/P/S Metropolitan (2002–2006) SM (`honda/chf50_service_mirror.pdf`) | 318 | maker |
| C14 | crash_support_v1 | PCX150 bent frame | Honda PCX150 (2013–2017) SM (`pdf/honda_pcx_2013_2017_sm.pdf`) | 325 | maker |
| C15 | crash_support_v1 | YW125Y bent frame | Yamaha YW125Y 2009 SM (`pdf/yamaha_zuma125_2009_sm.pdf`) | 335 | maker |
| C16 | crash_support_v1 | YW125Y inner tube | Yamaha YW125Y 2009 SM (`pdf/yamaha_zuma125_2009_sm.pdf`) | 157 | maker |
| C17 | crash_support_v1 | YW125Y inner tube limit | Yamaha YW125Y 2009 SM (`pdf/yamaha_zuma125_2009_sm.pdf`) | 34 | maker |
| C18 | crash_support_v1 | People S 250 fork | Kymco People / People S 250 SM (`pdf/kymco_people_s250_sm.pdf`) | 35 | maker |
| C19 | crash_support_v1 | CHF50 axle | Honda CHF50/P/S Metropolitan (2002–2006) SM (`honda/chf50_service_mirror.pdf`) | 218 | maker |
| C20 | crash_support_v1 | CHF50 rim | Honda CHF50/P/S Metropolitan (2002–2006) SM (`honda/chf50_service_mirror.pdf`) | 219 | maker |
| C21 | crash_support_v1 | PCX150 axle | Honda PCX150 (2013–2017) SM (`pdf/honda_pcx_2013_2017_sm.pdf`) | 326 | maker |
| C22 | crash_support_v1 | PCX150 rear rim | Honda PCX150 (2013–2017) SM (`pdf/honda_pcx_2013_2017_sm.pdf`) | 355 | maker |
| C23 | crash_support_v1 | YW125Y axle and wheel | Yamaha YW125Y 2009 SM (`pdf/yamaha_zuma125_2009_sm.pdf`) | 117 | maker |
| C24 | crash_support_v1 | People S 250 axle | Kymco People / People S 250 SM (`pdf/kymco_people_s250_sm.pdf`) | 187 | maker |
| C25 | crash_support_v1 | People S 250 rim | Kymco People / People S 250 SM (`pdf/kymco_people_s250_sm.pdf`) | 188 | maker |
| C26 | crash_support_v1 | DMV total loss definition | DMV VIRPM 19.015 Definitions (web) (`acquired/Regulation/portal_handbook_vehicle-industry-registration-procedures-manual-2_salvage-nonrepairable-junk-vehicles_definitions.html`) | 1 | regulation |
| C27 | crash_support_v1 | DMV nonrepairable | DMV VIRPM 19.015 Definitions (web) (`acquired/Regulation/portal_handbook_vehicle-industry-registration-procedures-manual-2_salvage-nonrepairable-junk-vehicles_definitions.html`) | 1 | regulation |
| C28 | crash_support_v1 | DMV owner retained | DMV VIRPM 19.015 Definitions (web) (`acquired/Regulation/portal_handbook_vehicle-industry-registration-procedures-manual-2_salvage-nonrepairable-junk-vehicles_definitions.html`) | 1 | regulation |
| C29 | crash_support_v1 | DMV 10 days | DMV VIRPM 19.075 Salvage Certificate (web) (`acquired/Regulation/ortal_handbook_vehicle-industry-registration-procedures-manual-2_salvage-nonrepairable-junk-vehicles_salvage-certificate.html`) | 1 | regulation |
| C30 | crash_support_v1 | owner applies without a settlement | DMV, Total Loss Salvage & Non-Repairable Vehicles (web) (`acquired/Regulation/portal_vehicle-registration_new-registration_total-loss-salvage-non-repairable-vehicles.html`) | 1 | regulation |
| C31 | crash_support_v1 | revived salvage registration | DMV, Junk/Revived Salvage Vehicles (web) (`acquired/Regulation/portal_vehicle-registration_new-registration_junk-revived-salvage-vehicles.html`) | 1 | regulation |
| T1 | track_prep_v1 | RC8 intended use | KTM 2010 1190 RC8 USA OM (`acquired/KTM/10_3211524_en_OM.pdf`) | 10 | maker |
| T2 | track_prep_v1 | title page | KTM 2010 1190 RC8 USA OM (`acquired/KTM/10_3211524_en_OM.pdf`) | 1 | maker |
| T3 | track_prep_v1 | EXC TPI closed areas (EXC block) | KTM 2022 250/300 EXC TPI OM (`acquired/KTM/22_3214421_en_OM.pdf`) | 9 | maker |
| T4 | track_prep_v1 | YZF-R1 warranty | Yamaha YZFR1T1/YZFR1MT OM (`acquired/Yamaha/library_om_contents_pdf_10_D45-28199-11_02.pdf`) | 135 | maker |
| T5 | track_prep_v1 | title page | Yamaha YZFR1T1/YZFR1MT OM (`acquired/Yamaha/library_om_contents_pdf_10_D45-28199-11_02.pdf`) | 1 | maker |
| T6 | track_prep_v1 | S 1000 R chapter | BMW S 1000 R RM (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_S_0D02_RM_0913_S1000R_01.pdf`) | 65 | maker |
| T7 | track_prep_v1 | title page | BMW S 1000 R RM (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_S_0D02_RM_0913_S1000R_01.pdf`) | 1 | maker |
| T8 | track_prep_v1 | S 1000 R mirror | BMW S 1000 R RM (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_S_0D02_RM_0913_S1000R_01.pdf`) | 85 | maker |
| T9 | track_prep_v1 | S 1000 R plate carrier | BMW S 1000 R RM (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_S_0D02_RM_0913_S1000R_01.pdf`) | 86 | maker |
| T10 | track_prep_v1 | S 1000 R warning back on | BMW S 1000 R RM (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_S_0D02_RM_0913_S1000R_01.pdf`) | 88 | maker |
| T11 | track_prep_v1 | S 1000 R preload method | BMW S 1000 R RM (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_S_0D02_RM_0913_S1000R_01.pdf`) | 78 | maker |
| T12 | track_prep_v1 | S 1000 R front sag and damping | BMW S 1000 R RM (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_S_0D02_RM_0913_S1000R_01.pdf`) | 81 | maker |
| T13 | track_prep_v1 | S 1000 R compression positions | BMW S 1000 R RM (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_S_0D02_RM_0913_S1000R_01.pdf`) | 82 | maker |
| T14 | track_prep_v1 | EXC TPI sag | KTM 2022 250/300 EXC TPI OM (`acquired/KTM/22_3214421_en_OM.pdf`) | 58 | maker |
| T15 | track_prep_v1 | EXC TPI rider weight | KTM 2022 250/300 EXC TPI OM (`acquired/KTM/22_3214421_en_OM.pdf`) | 55 | maker |
| T16 | track_prep_v1 | YZF-R1 ERS M-1 | Yamaha YZFR1T1/YZFR1MT OM (`acquired/Yamaha/library_om_contents_pdf_10_D45-28199-11_02.pdf`) | 42 | maker |
| T17 | track_prep_v1 | S 1000 R DYNAMIC PRO | BMW S 1000 R RM (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_S_0D02_RM_0913_S1000R_01.pdf`) | 107 | maker |
| T18 | track_prep_v1 | S 1000 XR DTC off | BMW S 1000 XR RM (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_S_0D03_RM_0418_01.pdf`) | 133 | maker |
| T19 | track_prep_v1 | title page | BMW S 1000 XR RM (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_S_0D03_RM_0418_01.pdf`) | 1 | maker |
| T20 | track_prep_v1 | YZF-R7 LCS | Yamaha YZFR7T OM (`acquired/Yamaha/library_om_contents_pdf_10_D42-28199-10_02.pdf`) | 23 | maker |
| T21 | track_prep_v1 | title page | Yamaha YZFR7T OM (`acquired/Yamaha/library_om_contents_pdf_10_D42-28199-10_02.pdf`) | 1 | maker |
| T22 | track_prep_v1 | S 1000 R racing intervals | BMW S 1000 R RM (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_S_0D02_RM_0913_S1000R_01.pdf`) | 175 | maker |
| T23 | track_prep_v1 | 950 SE after every race | KTM 2008 950 Super Enduro R OM (`acquired/KTM/08_3211240_OM_EN.pdf`) | 30 | maker |
| T24 | track_prep_v1 | EXC TPI motorsport columns | KTM 2022 250/300 EXC TPI OM (`acquired/KTM/22_3214421_en_OM.pdf`) | 53 | maker |
| E1 | emissions_v1 | BAR exempted vehicles | BAR, Smog Check Reference Guide 2025 (`acquired/Regulation/pdf_smog-check-reference-guide.pdf`) | 9 | regulation |
| E2 | emissions_v1 | BAR table 1 | BAR, Smog Check Reference Guide 2025 (`acquired/Regulation/pdf_smog-check-reference-guide.pdf`) | 10 | regulation |
| E3 | emissions_v1 | title page | BAR, Smog Check Reference Guide 2025 (`acquired/Regulation/pdf_smog-check-reference-guide.pdf`) | 1 | regulation |
| E4 | emissions_v1 | CARB certification EO | CARB, ONMC - Executive Order Introduction (web) (`acquired/Regulation/our-work_programs_road-motorcycles_onmc-executive-order-introduction.html`) | 1 | regulation |
| E5 | emissions_v1 | CB500F label and CARB evap | Honda CB500F/FA 2018 OM (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 121 | maker |
| E6 | emissions_v1 | XR650L 50-state | Honda XR650L 2018 OM (`acquired/Honda/om_AHM_XR650L_2018_XR650L_31MGW660_0.pdf`) | 32 | maker |
| E7 | emissions_v1 | XR650L label | Honda XR650L 2018 OM (`acquired/Honda/om_AHM_XR650L_2018_XR650L_31MGW660_0.pdf`) | 109 | maker |
| E8 | emissions_v1 | PCX150 destination code | Honda PCX150 (2013–2017) SM (`pdf/honda_pcx_2013_2017_sm.pdf`) | 8 | maker |
| E9 | emissions_v1 | CARB VC 27156 | CARB, Aftermarket Motorcycle Parts (web) (`acquired/Regulation/aftermarket-motorcycle-parts.html`) | 1 | regulation |
| E10 | emissions_v1 | CARB which parts | CARB, Aftermarket Motorcycle Parts (web) (`acquired/Regulation/aftermarket-motorcycle-parts.html`) | 1 | regulation |
| E11 | emissions_v1 | CARB EO label | CARB, Aftermarket Motorcycle Parts (web) (`acquired/Regulation/aftermarket-motorcycle-parts.html`) | 1 | regulation |
| E12 | emissions_v1 | BAR VC 27156 | BAR, Smog Check Reference Guide 2025 (`acquired/Regulation/pdf_smog-check-reference-guide.pdf`) | 45 | regulation |
| E13 | emissions_v1 | BAR tampered definition | BAR, Smog Check Reference Guide 2025 (`acquired/Regulation/pdf_smog-check-reference-guide.pdf`) | 41 | regulation |
| E14 | emissions_v1 | CB500F permeation and noise | Honda CB500F/FA 2018 OM (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 123 | maker |
| E33 | emissions_v1 | CB500F catalytic converter in the exhaust | Honda CB500F/FA 2018 OM (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 122 | maker |
| E15 | emissions_v1 | CB500F noise tampering acts | Honda CB500F/FA 2018 OM (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 124 | maker |
| E16 | emissions_v1 | EPA reasonable basis and penalties | EPA fact sheet, March 2020 (`acquired/Regulation/system_files_documents_2021-11_epafactsheetreaftermarketddsandtampering.pdf`) | 2 | regulation |
| E17 | emissions_v1 | title page | EPA fact sheet, March 2020 (`acquired/Regulation/system_files_documents_2021-11_epafactsheetreaftermarketddsandtampering.pdf`) | 1 | regulation |
| E18 | emissions_v1 | GTS 310 HPE exempt parts | Vespa GTS 310 HPE (USA) OM (`gts310_usa_om.pdf`) | 19 | maker |
| E19 | emissions_v1 | CB500F catalytic converter | Honda CB500F/FA 2018 OM (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 125 | maker |
| E20 | emissions_v1 | Tenere 700 fuel out | Yamaha XTZ7T (Ténéré 700) OM (`acquired/Yamaha/library_om_contents_pdf_10_BRL-28199-11_02.pdf`) | 31 | maker |
| E21 | emissions_v1 | title page | Yamaha XTZ7T (Ténéré 700) OM (`acquired/Yamaha/library_om_contents_pdf_10_BRL-28199-11_02.pdf`) | 1 | maker |
| E22 | emissions_v1 | XC50J leaded | Yamaha XC50J OM (`acquired/Yamaha/library_om_contents_pdf_10_1TS-F8199-15_02.pdf`) | 25 | maker |
| E23 | emissions_v1 | GTS 310 HPE MIL | Vespa GTS 310 HPE (USA) OM (`gts310_usa_om.pdf`) | 28 | maker |
| E24 | emissions_v1 | GTS 310 HPE catalytic silencer | Vespa GTS 310 HPE (USA) OM (`gts310_usa_om.pdf`) | 61 | maker |
| E25 | emissions_v1 | title page | Vespa GTS 310 HPE (USA) OM (`gts310_usa_om.pdf`) | 1 | maker |
| E26 | emissions_v1 | CB500F canister | Honda CB500F/FA 2018 OM (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 122 | maker |
| E27 | emissions_v1 | Tenere 700 canister check | Yamaha XTZ7T (Ténéré 700) OM (`acquired/Yamaha/library_om_contents_pdf_10_BRL-28199-11_02.pdf`) | 79 | maker |
| E28 | emissions_v1 | PCX150 evap and catalyst | Honda PCX150 (2013–2017) SM (`pdf/honda_pcx_2013_2017_sm.pdf`) | 42 | maker |
| E29 | emissions_v1 | Tenere 700 records | Yamaha XTZ7T (Ténéré 700) OM (`acquired/Yamaha/library_om_contents_pdf_10_BRL-28199-11_02.pdf`) | 122 | maker |
| E30 | emissions_v1 | CB500F own maintenance | Honda CB500F/FA 2018 OM (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 128 | maker |
| E31 | emissions_v1 | CB500F certified parts | Honda CB500F/FA 2018 OM (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 45 | maker |
| E32 | emissions_v1 | GTS 310 HPE CA warranty | Vespa GTS 310 HPE (USA) OM (`gts310_usa_om.pdf`) | 17 | maker |
| F1 | ppi_chassis_v1 | F162: p. 93 names the fault the check finds | Yamaha YW125Y 2009 SM (`pdf/yamaha_zuma125_2009_sm.pdf`) | 93 | maker |
| F2 | ppi_chassis_v1 | F162: the 2022 EXC TPI's p. 76 | KTM 2022 250/300 EXC TPI OM (`acquired/KTM/22_3214421_en_OM.pdf`) | 76 | maker |
| F3 | ppi_chassis_v1 | F162: the same sentence in the 2027 manual, which is why the name is needed | KTM 2027 250 XC-W / 300 EXC OM (`acquired/KTM/27_3240387_en_BA.pdf`) | 76 | maker |
| C32 | crash_support_v1 | CHF50 rear rim | Honda CHF50/P/S Metropolitan (2002–2006) SM (`honda/chf50_service_mirror.pdf`) | 242 | maker |
| C33 | crash_support_v1 | People S 250 rear rim | Kymco People / People S 250 SM (`pdf/kymco_people_s250_sm.pdf`) | 206 | maker |
| C34 | crash_support_v1 | PCX150 front rim; front-wheel page | Honda PCX150 (2013–2017) SM (`pdf/honda_pcx_2013_2017_sm.pdf`) | 326 | maker |
| C35 | crash_support_v1 | CHF50 axle page is the front wheel's | Honda CHF50/P/S Metropolitan (2002–2006) SM (`honda/chf50_service_mirror.pdf`) | 218 | maker |
| C36 | crash_support_v1 | People S 250 axle page is the front axle's | Kymco People / People S 250 SM (`pdf/kymco_people_s250_sm.pdf`) | 187 | maker |
| C37 | crash_support_v1 | YW125Y p. 117 is the front wheel's | Yamaha YW125Y 2009 SM (`pdf/yamaha_zuma125_2009_sm.pdf`) | 117 | maker |
| C38 | crash_support_v1 | BAR estimate rule, Smog Check repairs | BAR, Smog Check Reference Guide 2025 (`acquired/Regulation/pdf_smog-check-reference-guide.pdf`) | 32 | regulation |
| C39 | crash_support_v1 | 690 Duke ABS off | KTM 2019 690 Duke OM (`acquired/KTM/19_3213923_en_OM.pdf`) | 54 | maker |
| C40 | crash_support_v1 | title page | KTM 2019 690 Duke OM (`acquired/KTM/19_3213923_en_OM.pdf`) | 1 | maker |
| C41 | crash_support_v1 | KTM frame rule, 2nd manual | KTM 2027 450 SX-F / XC-F OM (`acquired/KTM/27_3240384_en_BA.pdf`) | 93 | maker |
| C42 | crash_support_v1 | KTM frame rule, 3rd manual | KTM 2027 250 XC-W / 300 EXC OM (`acquired/KTM/27_3240387_en_BA.pdf`) | 97 | maker |
| C43 | crash_support_v1 | KTM frame rule, 4th manual | KTM 2027 500 EXC-F OM (`acquired/KTM/27_3240392_en_BA.pdf`) | 96 | maker |
| C44 | crash_support_v1 | DMV nonrepairable criteria in full | DMV VIRPM 19.015 Definitions (web) (`acquired/Regulation/portal_handbook_vehicle-industry-registration-procedures-manual-2_salvage-nonrepairable-junk-vehicles_definitions.html`) | 1 | regulation |
| C45 | crash_support_v1 | People S 250 chart rows (rendered) | Kymco People / People S 250 SM (`pdf/kymco_people_s250_sm.pdf`) | 35 | maker |
| C46 | crash_support_v1 | EPA insurance | EPA fact sheet, March 2020 (`acquired/Regulation/system_files_documents_2021-11_epafactsheetreaftermarketddsandtampering.pdf`) | 2 | regulation |
| C47 | crash_support_v1 | title page lists XC-W TPI too | KTM 2022 250/300 EXC TPI OM (`acquired/KTM/22_3214421_en_OM.pdf`) | 1 | maker |
| T25 | track_prep_v1 | ERS is the R1M's | Yamaha YZFR1T1/YZFR1MT OM (`acquired/Yamaha/library_om_contents_pdf_10_D45-28199-11_02.pdf`) | 41 | maker |
| T26 | track_prep_v1 | S 1000 R front preload is the DDC OE procedure | BMW S 1000 R RM (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_S_0D02_RM_0913_S1000R_01.pdf`) | 80 | maker |
| T27 | track_prep_v1 | p. 78 is the rear wheel's | BMW S 1000 R RM (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_S_0D02_RM_0913_S1000R_01.pdf`) | 78 | maker |
| T28 | track_prep_v1 | EXC TPI rider weight band | KTM 2022 250/300 EXC TPI OM (`acquired/KTM/22_3214421_en_OM.pdf`) | 55 | maker |
| T29 | track_prep_v1 | EXC TPI rear shock sag | KTM 2022 250/300 EXC TPI OM (`acquired/KTM/22_3214421_en_OM.pdf`) | 58 | maker |
| T30 | track_prep_v1 | US limited warranty | Yamaha YZFR1T1/YZFR1MT OM (`acquired/Yamaha/library_om_contents_pdf_10_D45-28199-11_02.pdf`) | 135 | maker |
| T31 | track_prep_v1 | 790 Duke not for race tracks | KTM 2027 790 DUKE OM (`acquired/KTM/27_3240428_en_BA.pdf`) | 10 | maker |
| T32 | track_prep_v1 | title page | KTM 2027 790 DUKE OM (`acquired/KTM/27_3240428_en_BA.pdf`) | 1 | maker |
| T33 | track_prep_v1 | DYNAMIC PRO is optional equipment | BMW S 1000 R RM (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_S_0D02_RM_0913_S1000R_01.pdf`) | 107 | maker |
| T34 | track_prep_v1 | DTC is optional equipment | BMW S 1000 XR RM (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_S_0D03_RM_0418_01.pdf`) | 133 | maker |
| T35 | track_prep_v1 | S 1000 XR DTC stays off | BMW S 1000 XR RM (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_S_0D03_RM_0418_01.pdf`) | 132 | maker |
| T36 | track_prep_v1 | S 1000 R last mode returns | BMW S 1000 R RM (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_S_0D02_RM_0913_S1000R_01.pdf`) | 106 | maker |
| T37 | track_prep_v1 | YZF-R7 ABS off | Yamaha YZFR7T OM (`acquired/Yamaha/library_om_contents_pdf_10_D42-28199-10_02.pdf`) | 71 | maker |
| T38 | track_prep_v1 | KTM 1290 rear axle locking wires | KTM 2023 1290 Super Duke R / RR OM (`acquired/KTM/23_3214761_en_OM.pdf`) | 129 | maker |
| T39 | track_prep_v1 | K 1200 RS parts-and-accessories note | BMW K 1200 RS MI (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_K_0547_WA_0504_K1200RS_01.pdf`) | 4 | maker |
| T40 | track_prep_v1 | EXC TPI coolant | KTM 2022 250/300 EXC TPI OM (`acquired/KTM/22_3214421_en_OM.pdf`) | 170 | maker |
| T41 | track_prep_v1 | EXC TPI required work, motorsport column | KTM 2022 250/300 EXC TPI OM (`acquired/KTM/22_3214421_en_OM.pdf`) | 52 | maker |
| T42 | track_prep_v1 | EXC TPI recommended work, both motorsport columns | KTM 2022 250/300 EXC TPI OM (`acquired/KTM/22_3214421_en_OM.pdf`) | 54 | maker |
| T43 | track_prep_v1 | mirror locknut compound | BMW S 1000 R RM (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_S_0D02_RM_0913_S1000R_01.pdf`) | 85 | maker |
| E34 | emissions_v1 | Vespa CA receipts clause | Vespa GTS 310 HPE (USA) OM (`gts310_usa_om.pdf`) | 17 | maker |
| E35 | emissions_v1 | Vespa liability limit | Vespa GTS 310 HPE (USA) OM (`gts310_usa_om.pdf`) | 19 | maker |
| E36 | emissions_v1 | CARB labelling | CARB, ONMC - Executive Order Introduction (web) (`acquired/Regulation/our-work_programs_road-motorcycles_onmc-executive-order-introduction.html`) | 1 | regulation |
| E37 | emissions_v1 | CARB exhaust note | CARB, Aftermarket Motorcycle Parts (web) (`acquired/Regulation/aftermarket-motorcycle-parts.html`) | 1 | regulation |
| E38 | emissions_v1 | EPA discretion | EPA fact sheet, March 2020 (`acquired/Regulation/system_files_documents_2021-11_epafactsheetreaftermarketddsandtampering.pdf`) | 1 | regulation |
| E39 | emissions_v1 | EPA up-to wording | EPA fact sheet, March 2020 (`acquired/Regulation/system_files_documents_2021-11_epafactsheetreaftermarketddsandtampering.pdf`) | 2 | regulation |
| E40 | emissions_v1 | CB500F system list | Honda CB500F/FA 2018 OM (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 122 | maker |
| E41 | emissions_v1 | CB500F permeation | Honda CB500F/FA 2018 OM (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 123 | maker |
| E42 | emissions_v1 | BAR full citation | BAR, Smog Check Reference Guide 2025 (`acquired/Regulation/pdf_smog-check-reference-guide.pdf`) | 9 | regulation |
| E43 | emissions_v1 | PCX150 evap heading | Honda PCX150 (2013–2017) SM (`pdf/honda_pcx_2013_2017_sm.pdf`) | 42 | maker |
| E44 | emissions_v1 | BAR p. 41 is the program glossary | BAR, Smog Check Reference Guide 2025 (`acquired/Regulation/pdf_smog-check-reference-guide.pdf`) | 41 | regulation |
| W31 | winterization_v1 | W30 context: the caution box | Piaggio Beverly 125 SSM (`pdf/beverly125.pdf`) | 78 | maker |
| W32 | winterization_v1 | W30 context: troubleshooting table | Piaggio Beverly 125 SSM (`pdf/beverly125.pdf`) | 55 | maker |
| T44 | track_prep_v1 | R1M T-1 slicks | Yamaha YZFR1T1/YZFR1MT OM (`acquired/Yamaha/library_om_contents_pdf_10_D45-28199-11_02.pdf`) | 41 | maker |
| T45 | track_prep_v1 | R1M street-tyre presets | Yamaha YZFR1T1/YZFR1MT OM (`acquired/Yamaha/library_om_contents_pdf_10_D45-28199-11_02.pdf`) | 42 | maker |
| T46 | track_prep_v1 | S 1000 XR DTC back on without coding plug | BMW S 1000 XR RM (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_S_0D03_RM_0418_01.pdf`) | 62 | maker |
| T47 | track_prep_v1 | p. 132 note is in the DYNAMIC PRO section | BMW S 1000 XR RM (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_S_0D03_RM_0418_01.pdf`) | 131 | maker |
| T48 | track_prep_v1 | YZF-R7 rear-wheel ABS switch | Yamaha YZFR7T OM (`acquired/Yamaha/library_om_contents_pdf_10_D42-28199-10_02.pdf`) | 71 | maker |
| T49 | track_prep_v1 | Agility 50 seat lock wire | Kymco Agility 50 SM (`pdfs/kymco_agility50_sm.pdf`) | 32 | maker |
| T50 | track_prep_v1 | title page | Kymco Agility 50 SM (`pdfs/kymco_agility50_sm.pdf`) | 1 | maker |
| E45 | emissions_v1 | CB500F systems, the rest of the list | Honda CB500F/FA 2018 OM (`acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`) | 122 | maker |
| E46 | emissions_v1 | EPA reasonable basis continues on p. 2 | EPA fact sheet, March 2020 (`acquired/Regulation/system_files_documents_2021-11_epafactsheetreaftermarketddsandtampering.pdf`) | 2 | regulation |
| E47 | emissions_v1 | BAR VC 27156 wording | BAR, Smog Check Reference Guide 2025 (`acquired/Regulation/pdf_smog-check-reference-guide.pdf`) | 45 | regulation |
| C48 | crash_support_v1 | BAR: written estimate under the Act | BAR, Smog Check Reference Guide 2025 (`acquired/Regulation/pdf_smog-check-reference-guide.pdf`) | 27 | regulation |
| T51 | track_prep_v1 | S 1000 XR DTC returns above 10 km/h | BMW S 1000 XR RM (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_S_0D03_RM_0418_01.pdf`) | 126 | maker |
| T52 | track_prep_v1 | second BMW booklet with the note | BMW R 850 R / R 1150 R MI (`acquired/BMW/manuals_BA-Extern_IN_BA-INTERNET-COM_PDF_R_0428_WA_0504_R850-1150R_01.pdf`) | 4 | maker |
| C49 | crash_support_v1 | 1090 Adventure R ABS off, the same warning | KTM 2019 1090 Adventure R OM (`acquired/KTM/19_3213917_en_OM.pdf`) | 183 | maker |
| C50 | crash_support_v1 | title page | KTM 2019 1090 Adventure R OM (`acquired/KTM/19_3213917_en_OM.pdf`) | 1 | maker |
| W30 | winterization_v1 | W30, for its adversarial read | Piaggio Beverly 125 SSM (`pdf/beverly125.pdf`) | 78 | maker |


## Verification Checklist

- [x] Migration 071 applies on a fresh `init_db` database;
      `SCHEMA_VERSION >= 71`; 071 found by name
- [x] Upgrade 070 → 071 on a self-built 070 database changes exactly the
      scoped item rows (F161's three, F162's one, W30's one), each only in
      its named fields, and adds exactly the three templates and their 21
      items (`test_upgrade_from_70_changes_exactly_the_scoped_rows`,
      `test_upgrade_changes_only_the_named_fields`)
- [x] `rollback_to_version(70)` restores every changed row byte-identical,
      removes the new rows with no orphans, and re-applies
- [x] Every migration keeps its rollback (and two round trips catch what
      that guard cannot, control 5)
- [x] Each template: category, powertrains, tier, duration; titles and
      sequence; optional items exactly as planned
- [x] Figures pinned per field; every machine-bound figure beside its
      machine (`MACHINE_OF`); every regulator rule beside its regulator
      (`REGULATOR_OF`)
- [x] The negatives stated where the items rely on them; no frame
      measurement and no race rule invented (tests)
- [x] F161: no "10W-40", "13.2", "5 minutes" or "Sta-Bil" in the generic
      items, and each changed field a pointer; F162: the two sentences as
      planned; W30: its context stated
- [x] F158 pins over the three templates and the fixed rows
- [x] `workflow list --category <each>` and `workflow show <slug>` for
      all three
- [x] Known-bad controls planted, seen red, reverted: seven (phase log)
- [x] Rule 3's four whole-tree checks, plus the F124 guard and the related
      suites, before every commit that touched the migration: 546 passed at
      the last; `finding_check` exit 0 in both variants
- [x] Regression of record by `regression.sh`: **9478 passed, 0 failed, 0 skipped, 0 errors** at `8d65a3e` (13 min 53 s wall, `python -m pytest -n auto --dist load`, exit 0)
- [x] Refute pass over every claim and W30, five rounds; after each fix
      round every changed sentence was re-read by the next round, and the
      loop closed under the operator's stopping rule; `refute_check` exit 0
- [x] Backup, a dry run on a copy of live, the F158 census on the copy
      (and its control), and the diff with before and after text for every
      changed row, prepared for the operator. **The live apply and the merge
      wait for the operator's answer** (rule 1; the phase log's Deploy
      section)

## Deviations from Plan

- **Five refute rounds, closed by the operator's stopping rule.** Each
  fix round introduced defects the next found, including in the
  refuters' own proposed replacements (round 2 killed two of round 1's; round 3
  and round 4 one each of their predecessor's). Mid-loop the operator
  set the rule: after round 3's factual defects, one more round on only
  the changed sentences, then at most one more; anything unresolved is
  dropped and filed. Round 5 left one sentence unresolved (crash item 7's
  account of where "insurance" appears besides the papers); it was
  dropped from 071 and filed as **F164**.
- **The generic starter's pointers were rewritten three times** before
  they claimed only what they point at. Each attempt to describe the
  makers inside the starter text was refuted once, so the final wording
  states no maker's step: "winterization_v1 gives the fuel / oil steps of
  the makers it cites" and "compares several makers' battery steps".
- **W30 changed a fifth live row** (winterization_v1 item 5's
  description), inside the operator's words "fix or drop it on the
  verdict". The deploy scope check includes it, field by field.
- **The refuters found defects in live text outside F161's and F162's
  scope** (the generic items' untouched title, steps and pass/fail; three
  unsupported steering-bearing sentences in chassis item 18). They are
  **F163**, with drafted replacements in the phase log, not changed.
- **`track_prep_v1` item 4 (rider aids) is optional** (v1.0 planned none):
  not every machine has them.
- **I declined a round-1 fix on a text-layer snippet, and was wrong.** The
  rendered Yamaha p. 42 prints the R1M's M-2 street-tyre preset that I
  said was not there. Round 2 caught it. A page whose layout matters is
  rendered before a fix is declined.
- **Two round-2 refuters were cut off by a network outage** (API host
  unreachable) before writing anything, and were resumed with their
  context.
- **The row went in after the first census** (a lapse against CLAUDE.md,
  recorded in the phase log; the census wrote nothing to the repository).
- **Tests moved beyond the plan:** 259's empty-category probe now finds an
  empty category at run time (071 filled `track_prep`), and 264's W30 pins
  moved with the W30 fix.
- **The Subconscious run directory** sits under `264_step0/`: the copied
  script kept 264's root path. The sandbox proof is unaffected.

## Results

| Metric | Value |
|---|---|
| Templates added | 3 (`crash_support_v1` 8 items, `track_prep_v1` 6, `emissions_v1` 7), 21 items, 4 optional |
| Live rows changed | 5 checklist items: generic winterization items 6, 7, 8 (F161, pointers), chassis item 18 (F162), winterization_v1 item 56 (W30); no template row |
| Migration | 071, schema 70 → 71; rollback round-trips byte-identical |
| Production code | `migrations.py` (migration 071), 1 line in `database.py` |
| Tests | 32 added (`tests/test_phase262_crash_track_emissions.py`); 259's and 264's pins moved |
| Known-bad controls | 7 planted, seen red, reverted; plus the anchor, cross-check, census and scope-check controls |
| Regulator documents | 13 acquired by script with sidecars (BAR, CARB ×5, DMV ×6, EPA) |
| Claims | 155 (126 maker, 29 regulation), 294 anchors on their pages; 135 cited pages + 12 regulator citations, 0 unclaimed |
| Refute | Round 1: 91/92 kept (T16 killed), ~56 text fixes. Round 2: 48/48 kept, 6 sentences killed. Round 3: 10/10 kept, 4 killed. Round 4: 3/3 kept, 2 killed. Round 5: 11 kept, 1 killed → dropped (F164) |
| Bug fixes | none |
| Findings | F163 and F164 filed; F161 and F162 fixed by 071 (closed at the live apply) |
| Floor | 9446 → 9478 |
| Regression of record | **9478 passed, 0 failed, 0 skipped, 0 errors** at `8d65a3e` (13 min 53 s wall, `python -m pytest -n auto --dist load`, exit 0) |

Key finding: **text that describes other text is the hardest to get
right.** The pointers in the generic starter ("winterization_v1 gives
each maker's …") were refuted three times: each version described
winterization_v1 a little more broadly than its items hold. A pointer
that makes no claim about its target's coverage survived. The same held
for counts ("two documents", "mostly as a warning"): a count needs the
same census as a negative, over every page set the library holds,
regulator pages included.

## Risks

- **Regulator pages change.** A web page is not a fixed edition. Each is
  kept with its sha256 and fetch time (2026-09-26), and the items name the
  page as fetched.
- **A rule read as a machine fact, or the reverse.** Mitigated by naming
  the regulator beside every rule (`REGULATOR_OF`) and the machine beside
  every figure (`MACHINE_OF`).
- **The generic starter still carries defects outside the scope** (F163),
  and item 7 of `crash_support_v1` ships without its insurance sentence
  (F164).
- **Item identity is prose** (F129's shape): the content is pinned in
  tests and seeded only inside the journal.
