# Phase 247 — Motor controller / inverter faults: the generic layer, anchored per make

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-18

---

## Goal

Row 247: "Motor controller / inverter faults — IGBT failures, phase-loss
detection, overcurrent faults, controller firmware." Phases 242–246 drew the
boundary the same way each time: the make phases own failure patterns, and
246, 247 and 249 own the generic BMS, inverter and thermal layers. 246 set
the rule this row inherits: **every entry is written as what the component
does and how each make shows it, anchored to a manufacturer document for
every make named, or not written**; every number carries its label, and the
label now travels with the number into the prompt. The row's four bullets
are generic power-electronics engineering. Under the corpus's provenance
classes that is `model-generated` unless a maker's own document names it,
so this row writes what Zero, Energica and LiveWire *publish* about their
motor controllers — and, where they publish nothing, says so.

## Step 0 — findings

**S0-1. What exists.** The `dtc_category_meta` table has carried `inverter`
("DC-to-AC inverter faults", critical) and `motor` ("Electric motor
controller faults (IGBT, phase)", critical) since migration 004, alongside
`regen`, `thermal`, `charging_port` and `hv_battery`; **all six are empty**
(0 rows in `dtc_codes`), as 246's close-out established for `hv_battery`.
Sixty corpus rows mention a controller, inverter, VCU, MBB, DC-DC or regen;
the electric-specific ones are 244's Energica motor-generation row and its
110-code row (seven codes named, none inverter-specific), 242's Zero rows
on Cypher II/III, firmware as a service item (firmware page + a 2020
storage-mode bulletin), the app, and the key-switch campaign; 243's
LiveWire rows on the 2020 onboard-charger software campaign that shuts the
powertrain down (NHTSA, 1,012 units; UK 30), the self-displayed trouble
codes (`forum`: odometer trigger + run button; meanings need Digital
Technician II), and the 6-pin CAN connector / TechLink 3; 246's rows name
the MBB, VCU and power controller in passing. **Nothing generic about the
motor controller exists; nothing anywhere names an IGBT failure, a
phase-loss detection or an overcurrent fault.**

**S0-2. Sources, by make.** 246's research fetched and verified the four
owner's manuals (Zero 88-09445-01 and 8811984-AF, Energica ENF003100
Rev. 02, H-D 94000703 and the 94001019 pages on the Service Information
Portal), Zero's firmware release notes, the NHTSA-hosted Zero bulletin
SV-ZMC-020-405 and the LiveWire warranty and EU battery pages. Five of its
refuter-verified survivors were set aside as 247 ground and are reusable
with their quotes: Zero 2025 §4.11's "thermal strategy" solid-red
indicator ("power will be reduced accordingly … does not indicate that
there's anything malfunctioning"); Zero's motor temperature gauge, colour
only, "do not have a numerical value display function"; Energica's LIMP
mode, "implemented automatically by the VCU", with motor and drive
temperature among its triggers; LiveWire's Temp widget showing "RESS
temperature, motor controller temperature and motor temperature"
(94000703 printed p. 99). **Not yet read for this row:** the Zero 2021
§7.6 fault-code table beyond codes 51–56; Energica's code table beyond the
seven codes 244 named (the inverter, motor, drive and VCU rows — the
likeliest place any maker names overcurrent or a phase fault); LiveWire's
Table 37 alerts beyond the RESS balance row; NHTSA recall and complaint
records for loss of propulsion on all three; Zero's firmware page as a
per-platform component list (is there a motor-controller firmware line at
all); Energica's repair-information sheet.

**S0-3. The design question.** "IGBT failures, phase-loss detection,
overcurrent faults" are true of every inverter and published by no
motorcycle maker in engineering terms. The row can be done honestly in
246's shape: what the controller is on each make and where its firmware
lives; how a controller or motor fault reaches the rider (fault codes,
dash messages, LIMP, alerts); what each maker publishes about overcurrent,
phase and power-stage faults (most likely a code name and nothing behind
it); controller firmware as a service item; what reads the controller.
Where a maker publishes nothing, the row says so, with the document read
in full to say it — 241's and 245's precedent, 246's practice.

**S0-4. Substrate — none, and one decision.** No schema change: the
categories exist. The live question is whether 247 seeds Energica's
inverter and motor codes into `dtc_codes` so `--category inverter`
answers — F90's shape. A `dtc_codes` row needs `common_causes` and
`fix_summary`; the manual gives code, description and MIL only, so the
causes and fixes would be model-generated, which is the failure 244Z
fixed. The gate-12 shadow rule adds a second cost: Energica's P0562 ("VCU
MAIN SUPPLY UNDERVOLTAGE") would shadow the generic P0562 and must differ
in causes and fix. **Decision: not in 247.** F90 stays open; the codes go
into `known_issues.dtc_codes` on the 247 rows, where a `code` lookup
reaches them, as 246 did for the BMS channels.

**S0-5. Cadence.** As 246 ran it: a five-lens sweep per make
(manufacturer document, regulator record, owner community, tooling,
platform generation), then **one refuter per cited URL that fetches the
page itself**, then a critic who reads survivors against the pages. No
workflow opt-in was given for this row, so the pass runs through the
Agent tool with the same rules: a page the refuter cannot fetch cannot be
cited; every number quoted verbatim; aggregators banned; the wiki, if
reached, `forum` unless reproducing an official document.

**S0-6. Boundaries.** 246 owns the pack; 248 owns regen behaviour; 249
owns cooling hardware, temperature bands and derate curves. A fault code,
alert or LIMP trigger caused by motor or controller temperature is a
fault surface and belongs here; the temperature tables and the thermal
strategy curve do not, and 247 cross-references them. The onboard charger
is neither the inverter nor 247's (the 2020 campaign is already in the
LiveWire file).

## Decisions carried from 246

1. Research as a fetch-and-verify pass; the refuter fetches every page.
2. Community sources are `forum`; official documents are cited directly.
3. A forum-cited number ships only with its label wherever displayed —
   enforced by 246's tests, which stay in force; one row carries one label.
4. `battery` category: exists and is empty (246's correction); `inverter`
   and `motor` are the same shape; no seeding here (S0-4, F90).

## Scope

1. **Up to five generic rows** in `known_issues_inverter.json`, each
   anchored per make or not written: *identity* (what the motor controller
   / inverter is on each make and where its firmware lives); *fault
   surface* (how a controller or motor fault shows: Zero fault codes,
   Energica codes, MIL and LIMP triggers, LiveWire instrument alerts);
   *overcurrent, phase and IGBT* (what is published — probably code names
   — and what is not); *controller firmware as a service item* (versions,
   campaigns, what an update does and risks); *tooling* (what reads the
   controller). `make` list-valued; Energica codes in `dtc_codes`.
2. **Tests** in 246's shape on the new file: every service-manual row
   names its document; no number unlabelled; one row, one label; a forum
   row names its site and page date; each concept named in a title; every
   named make resolves through 244F's junction; `kb search inverter`,
   `"motor controller"`, `firmware` each return a 247 row with its label;
   no aggregator, no wiki; plus a boundary test — no 247 row carries a
   temperature-band table or a 246 concept in its title.
3. **Research record** in this doc: survivors by class, rejected claims
   with reasons, the absences.
4. README, quickstart, install guide, launch checklist: count bump.

## Non-goals

- No `dtc_codes` seeding (F90); no schema change; no new commands.
- No regen (248), no cooling hardware or temperature bands (249), no pack
  content (246).
- No engineering explanation of IGBTs, phase-loss detection or overcurrent
  limits from memory. None.

## Results (v1.1)

**Built in 246's shape, with eight rows where the plan said up to five.**
Five service-manual concept rows carry the generic layer; two `regulation`
rows carry the controller recalls, because a regulator record is its own
label and a row carries one; one `forum` row carries the community
log-analyser's account, dated. The row's bullets — IGBT failures,
phase-loss detection, overcurrent faults — are recorded as what no maker
publishes, with the documents read in full to say so.

### The content (`known_issues_inverter.json`, eight rows)

| Concept | Row | Source | Anchors |
|---|---|---|---|
| Identity | *What the motor controller is on each make — a name and a current rating in the owner's manual, a supplier only in a service manual or a recall* | service-manual | Zero 88-09445-01 §3.7/§8.2/§1.2, 8811984-AF §3.7 + spec tables, 88-09447-01 §3.7, 2020 service manual (Sevcon Gen 4.5 Size 4/6); Energica ENF003100 fuse key p.70, p.63, p.72 + model web pages; H-D 94000703 Table 15/Table 10, 94001019 Table 5, 94001315 Table 5 + acronyms; livewire.com Arrow page |
| Fault surface | *How a motor-controller fault reaches the rider on each make — one code, one alert or one LIMP message, and no published cause behind any of them* | service-manual | Zero 88-09445-01 §7.2/§7.4–7.6/§1.2/§3.24, 8811984-AF §7.3–7.7/§4.11/§3.24, 88-09447-01 §7.2–7.7/§3.13, 2020 service manual DTC List-MBB; Energica code table pp.78–83, messages p.75, LIMP p.38, FAULT p.28, MIL p.29; H-D 94000703 Table 37, p.88, p.99, pp.85–86, 94001019 Widgets Table 1, 94001315 Instrument Alerts |
| Overcurrent / phase / IGBT | *No electric motorcycle maker publishes an overcurrent, phase-loss or IGBT diagnostic — the word inverter appears once or twice per manual and nothing sits behind it* | service-manual | Zero 8811984-AF full text, 88-09445-01 full text, 2020 service manual; Energica code table (129 rows) and full text; H-D 94000703 full text, 94001019, 94001315; cross-references to the recall rows |
| Firmware | *Controller firmware is a service item on every make, and none of the three versions the motor controller's firmware for owners* | service-manual | Zero firmware page (updated 2026-08-12), bulletin SV-ZMC-020-405, 8811984-AF §4.3; Energica RMI sheet Rev. 15/05/2018, ENF003100 p.46/p.6/pp.105–109, archived charging page (2023-12-04) and warranty page (2023-12-28); H-D 94000703 p.81/p.175/p.169, 94001019 Updating Software, 94001315 FOTA, livewire.com Del Mar and FAQ pages |
| Tooling | *What reads the motor controller on each make — Zero's dealer laptop, Energica's own dash and OBD modes, LiveWire's Digital Technician II* | service-manual | Zero bulletins SV-ZMC-020-405 and SV-ZMC-020-423, 2020 service manual ZDU sections, 8811984-AF §4.3; Energica ENF003100 p.77/p.46/p.48, RMI sheet p.3, archived 2017 news; H-D M1519, L1015, M1490 (2020, 2022), M1502, 94000703 p.149, 94001315 Bike Status |
| Recalls (Zero) | *Zero's two 2025 controller recalls: a motor controller replaced for busbar fasteners with no warning, and a firmware limp mode for key-switch signal loss* | regulation | NHTSA Part 573 reports 25V834 and 25V587; recalls API records |
| Recalls (LiveWire) | *LiveWire's powertrain-shutdown recalls are software in the on-board charger and the vehicle supervisory controller, reflashed by the dealer on the 2020 bike and over the air on the S2* | regulation | NHTSA campaign 20V624 API record, dealer notice of 2020-10-15 and bulletin M1519; Part 573 report 24V149 and dealer notice of 2024-02-29 |
| Logs (community) | *What a Zero's own logs hold about the motor controller, per the community log-analyser — motor channels on the older platform, none on the newer one, and fault names that are not log strings* | forum | zerologs.bike 'How Zero Logs Work', error-codes and log-generations pages, 'Last updated: July 30, 2026' |

Every row is written as *what the component does* and *how each make
shows it*; every service-manual row names its documents by code inside
the description (244's convention) and says which were read from mirror
copies; web pages are named as web pages with their page or capture
date; every number is the document's own, quoted after the refuters
re-read the page; nothing is `model-generated`. The five concept rows
carry `make` = `Zero, Harley-Davidson, LiveWire, Energica` and resolve to
all four marques through 244F's junction (tested). The Energica fault
channels the manual publishes for the drive, throttle, VCU supply,
contactors and low-level safety — forty codes — ride on the fault-surface
row's `dtc_codes` list, each named character for character in the text
(tested). Verified at close-out on a copy of the live database: the row
is reached through `kb by-code` (`find_issues_by_dtc`, a `LIKE` over the
column), and **not** through the `code` command, which resolves the DTC
table and loads known issues for its `--explain` context by vehicle, not
by code — so a technician typing `code U0110` still sees a heuristic
"No DB entry" until the codes themselves are seeded (F90). 246's results
said its BMS-channel codes were reachable by "a `code` lookup"; the same
correction applies there. `dtc_category_meta` and the `dtc_codes` seed
are untouched (Decision 4; F90).

### A correction to a shipped row

The Energica code-table refuter counted the 2018 Eva manual's diagnostic
table row by row on rendered pages: **129 rows, 128 distinct labels, 127
distinct codes** (U0182 appears twice; one row carries P2158 + P0500),
against the 110 that Phase 244's row *Energica publishes 110 fault codes
in standard SAE format* states in its title, description and fix. The
per-letter split is 82 P, 17 C, 15 B, 13 U — 244's chassis, body and
network counts were right and its powertrain count (65) was not. The row
is corrected in this phase (title now *127 fault codes*, description and
fix updated, with the earlier count and the correction named inside the
description). Because the corpus's identity index is (make, model,
title), the close-out updates the live row by its old title — on a copy
first, before-state printed — rather than letting a re-seed insert a
second row. F90's text in `moto-diag-mobile/docs/FOLLOWUPS.md` is
corrected too.

### Deviations

1. **Eight rows, not five.** Two regulation rows and one forum row, for
   the one-row-one-label rule 246 set. The 247 content test admits
   `regulation` alongside `service-manual` and `forum` for a row that
   carries a number (246's test admitted only two), and requires a
   regulation row to name its NHTSA campaign number.
2. **The critic's rule "never mix web-page facts onto a manual row" was
   not adopted.** Both are the manufacturer's own publications and carry
   the same label; the plan's design is one row per concept with per-make
   provenance inside it, as 246 shipped. Each web-page statement names
   the page and its date or archive capture in the description instead.
3. **The sweep found more than Step 0 expected**: 88 claims over 47 pages,
   including Zero's own 2014–2020 service manuals on an archived dealer
   site (which name the Sevcon Gen 4 and Gen 4.5 controllers and the
   ZDU's Motor Controller Interface), two 2025 Zero recall filings that
   name a Dana TM4 controller and describe a controller hardware failure
   with no warning, and Harley-Davidson's Digital Technician II release
   notes, the only documents that name a LiveWire Motor Control Module.
4. **No community source for Energica or LiveWire.** zeromanual.com is
   still behind an expired certificate; electricmotorcycleforum.com
   serves a database error; the LiveWire forums answer a JavaScript
   challenge. The one forum row is zerologs.bike, confirmed independent
   by the operator during 246.
5. **Three claims were refuted and dropped as written**: that the 2021
   SR/F manual never expands "MSC" (its introduction defines Bosch
   motorcycle stability control — the rows re-entered through the
   refuter's corrected text); that the Sevcon era has no controller
   campaign (NHTSA holds 12V455000 and 13V635000, which the sweep never
   read — filed as a follow-up, not written); that the S2 acronym table
   is the only owner-document place naming the PEU (it is also on the
   charging pages).
6. **Owner complaints are not content.** Two NHTSA complaints (a 2023 Eva
   Ribelle power cut when steering right; a 2024 Del Mar "turtle icon"
   limp) were verified as records and are not written as statements.

### Verification

- 63 tests in `test_phase247_inverter_content.py`; 453 across the 17
  suites run before the regression: the 247 file, both 246 files, 244D
  (dedup — every row inserts; the corrected 244 title still unique),
  244F (marques), 244I (models), 208 (docs counts), 78 (gate 2, forum-tip
  ratio), 241–244 (the EV files), 244T, 03, 244S, 244E, 240 (gate 12 —
  the six-value provenance vocabulary and the README count).
- **8/8 mutations killed**, bytecode cleared and `-B`: strip every
  document name from a service-manual row · add an unlabelled 600 A
  threshold as `model-generated` · paste a community statement into a
  service-manual row · drop the page date from the forum row · delete the
  firmware row · paste a temperature band table into a row · strip the
  campaign numbers from a regulation row · list a code the description
  never names. The second survived its first run — the number rule was
  246's, pack units only, and "600 A" was not a number to it — so the
  rule now covers amps, rpm, kW, hp, torque and speed.
- 244G raw-source scan of the new test file: clean. `ruff` clean.
- No schema change; `dtc_codes` seed and `dtc_category_meta` untouched;
  no new commands; 246's label-surface tests pass unchanged.
- Full regression **7,091 passed, 0 failed, 27:53**.

### Research record

**Cadence.** Three per-make sweep agents (five lenses each) produced 88
claims citing 47 URLs; **21 refuter agents, one per document or
document group, fetched every page themselves** (47/47 fetched; the only
non-200 was NHTSA's API answering an empty query with 400 and `Count 0`,
which the refuter proved is its no-match response) and judged 88/88
claims; a critic read the survivors against the refuters' verified
quotes. Tally: 34 survive clean, 51 survive downgraded, 3 refuted; the
critic killed or reassigned 7 more (two owner complaints, a 246-owned
interlock, a 246-owned fuse recall, and the three refutations). Class
balance of the survivors: 69 service-manual (eleven of them manufacturer
web pages, marked as such), 15 regulation, 4 forum. The pass was real:
three refutations, 51 rewrites, two locator errors, three number errors,
one corpus correction (the Energica count), two missed recalls, one false
"byte-identical edition" claim, one page the sweep quoted from a fetch
summary rather than the page (rewritten from the page).

**Documents.** Zero: 2021 SR/F owner's manual 88-09445-01 (5 claims),
2025 S/SR/SR-F/SR-S owner's manual 8811984-AF (6), 2021 S/SR/DS/DSR
owner's manual 88-09447-01 (2), 2020 S/SR/DS/DSR service manual v1 on an
archived dealer site (3; identity confirmed by its Zero copyright,
service-portal link and Zero e-mail), firmware release notes (3), bulletins
SV-ZMC-020-405 and SV-ZMC-020-423 via NHTSA (3), Part 573 reports 25V834
and 25V587 and API records (6). Energica: Eva owner's manual ENF003100
Rev. 02 (17), the repair-information sheet Rev. 15/05/2018 (2), three
archived energicamotor.com pages (3), two live model pages (2), a dealer
page (1), NHTSA API and FEMA's RAPEX compilation (3). LiveWire: 2020
owner's manual 94000703 (8), 2023 LiveWire ONE manual 94001019 on the
Service Information Portal (3), 2025 S2 manual 94001315 (5, with the 2024
edition compared), livewire.com pages (2), NHTSA records and letters for
20V624, 24V149 and 24V601 (6), bulletins M1519, L1015, M1490 (2020 and
2022) and M1502 (5).

**Grid.** Identity, fault surface, firmware and tooling each have a
service-manual anchor for every make. Empty cells, carried as absences:
overcurrent, phase loss and IGBT for all three makes; a versioned
controller firmware on Zero (its page versions MBB, BMU and BMS only);
a dealer diagnostic tool named by Energica (none, anywhere); Energica's
current-generation identity beyond web specification pages; S2 inverter
hardware (no spec row; the PEU named in acronyms, charging pages and
recall filings); any LiveWire code list (the only code number in any
document read is "VSC P1100000" in a tool release note).

**Numbers.** Every figure in a row was re-read on its page by a refuter:
controller ratings (550/600/665/775/785/900 amp), LiveWire motor figures,
Energica fuse ratings, ZDU version 33 and 33.9, Build 246 / Revision 9,
MBB V46/BMU V22/BMS V28 and V38/V45, V43/V18, V42, 40 kph (verbatim
"After decelerating to 40 kph", never "below"), 7 and 319 units, 1,012
units, VSC 7.1.17.2 → 7.4.28.2, 13.3.16.2 / 13.1.8.2, part 73100005,
FOTA "up to 40 minutes" and "Wait 5 minutes", the FAQ's 5 to 60 minutes,
tool numbers HD-48650 and HD-48650-TL3, HD-50390-9, HD-52742, 16101029,
85-05665, 12-08081, 30-08089. Not written: the 2012–13 Zero campaigns
12V455000 and 13V635000 (refuter-found, never read by the sweep); the
L1010 bulletin's 13.1.16.2 (contradicts the notice's 13.3.16.2); the 2014
manual's 660/420 amp; part 60-07009 (a dealer listing); MBB V44/V19,
V26/V21/V23 and MBB_V55 (notes only); the 2024 S2 spec figures; the
RESS "15.4 kW (20.6 hp)" unit error; zerologs' code counts; the 2025
manual's §3.43 warranty sentence (notes only); every owner-complaint ODI
number.

**Wording rules applied from the critic.** "Cypher II" and "Cypher III"
are this corpus's platform names and are marked so wherever they sit
beside a document that does not use them (the 2021 S/SR/DS/DSR manual,
the 2020 service manual, the 2020 bulletin, both recall reports). The
BMS throttle-disable interlock is 246's and is not restated. The thermal
strategy indicator is written as the manual's "powertrain components",
never "motor or controller", and the bands are 249's. "Drive (Power
Train Controller)" is Energica's term; "inverter" is not. The 2020
bulletin's "Main Brain Board" and the 2019 bulletin's "main bike board"
are both quoted, not harmonised. The 2020 LiveWire manual's reversed
table columns and the bulletins' space-less text layers are noted on the
rows that quote them.

**Follow-ups filed (F91), not written:** the 2012–13 Zero
controller-software campaigns; the L1010 version discrepancy; the 2025
DSR/X owner's manual, never fetched; the 2013–2019 Zero owner's manuals,
unreachable on Zero's host; zerologs' "Cypher III (proprietary)" against
Zero's Dana TM4 filing; and NHTSA's model list naming recalls for four
Zero model-years that its by-vehicle endpoint does not return.

## Verification Checklist

- [x] Every row names a manufacturer document for every make it names (test)
- [x] No numeric threshold without a label (test; controller units)
- [x] `kb search inverter` / `"motor controller"` / `firmware` each return a 247 row with its label (test)
- [x] `dtc_codes` seed untouched; `dtc_category_meta` untouched; listed codes reachable through `kb by-code` (verified on a copy), not through `code`
- [x] 246's label-surface tests still pass
- [x] Mutations: 8/8
- [x] Full regression green — **7,091 passed, 0 failed, 27:53**
