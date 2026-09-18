# Phase 247 — Motor controller / inverter faults: the generic layer, anchored per make

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-18

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

## Verification Checklist

- [ ] Every row names a manufacturer document for every make it names
- [ ] No numeric threshold without a label (test)
- [ ] `kb search inverter` / `"motor controller"` / `firmware` each return a 247 row (test)
- [ ] `dtc_codes` seed untouched; `dtc_category_meta` untouched
- [ ] 246's label-surface tests still pass
- [ ] Mutations: strip a document name; add an unlabelled ampere figure; paste a community number into a manual row; delete a concept row
- [ ] Full regression green
