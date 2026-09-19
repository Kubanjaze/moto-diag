# Phase 249 — Thermal management: the generic layer, anchored per make

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-18

---

## Goal

Row 249: "Thermal management (battery + motor) — liquid cooling loops
(battery), air cooling (motor), thermal derating curves, ambient temp
effects." The last content row before Gate 13, written under the rule
246 set and 247–248 kept: every entry is what the system does and how each
make shows it, anchored to a manufacturer document for every make named,
or not written; every number labelled; one row, one label; a regulator
record on its own row; a community source dated.

## Step 0 — findings

**S0-1. Most of the row is already written.** The audit found:
- **Battery derating and temperature bands**: 246's row *Thermal derating
  is the BMS refusing charge or discharge at the pack's temperature
  limits* carries Zero's BMS limits and battery-gauge bands (2021 and
  2025), Energica's four battery bands and LIMP triggers, and LiveWire's
  charging limits and RESS over-temperature charge stop.
- **Motor cooling type**: 242's platform row says every Zero motor is
  "passively air-cooled"; 244's motor-generation row says the pre-EMCE
  Energica motor is oil-cooled and the EMCE motor and inverter share a
  liquid loop.
- **LiveWire's coolant loop**: 243 carries the pressurised loop, its
  capacity and antifreeze, no thermostat as a service item, and the one
  dealer coolant change at 50,000 mi.
- **Energica's fluids**: 244's service-interval row says the pre-EMCE
  machine services motor oil, transmission oil and coolant.
- **Motor and controller temperature codes**: 247's fault-surface row
  carries Zero codes 41 and 57, the thermal-strategy indicator (as a
  fault surface, bands deferred here), Energica's P1049, P0298, drive and
  motor coolant sensor codes and the LIMP temperature messages, and
  LiveWire's Temp widget.

The `thermal` DTC category ("Battery/motor thermal management") exists
since migration 004 and is empty, like its five siblings.

**S0-2. What is not written.**
- *The cooling architecture as one map*: which of pack, motor,
  controller/inverter and charger is liquid-, oil- or air-cooled on each
  make, per the makers' own documents. The row's premise — "liquid
  cooling loops (battery)" — is untested: no corpus row says any of the
  three liquid-cools its pack. If none does, that is a correction to the
  row, as 212 and 245 made.
- *The motor and controller side of thermal management*: the motor and
  controller temperature gauges and their bands, and the powertrain
  thermal strategy's behaviour, which 247 deferred here; whether any
  maker publishes a derating curve (the row's bullet).
- *The cooling loop's own fault surface*: coolant-pump alerts and codes,
  coolant-temperature lamps, radiator and fan items, as each make shows
  them — distinct from the pack's temperature faults (246) and the
  controller's (247).
- *Ambient temperature and riding*: what each maker says about riding in
  heat and cold, parking in the sun, and range — the riding side; the
  charging side is 246's.

**S0-3. Design.** Four generic rows at most, each cross-referencing the
rows above instead of restating them: *architecture*, *motor and
controller temperature and derating*, *cooling-loop faults and service*,
*ambient temperature*. A figure already shipped in 242–248 is named by
reference, not copied.

**S0-4. Substrate — none.** The `thermal` category stays empty (F90);
cooling codes a manual publishes ride on the fault row's `dtc_codes`,
named in its text.

**S0-5. Cadence.** 248's: three per-make sweeps, one refuter per document
that fetches the page itself, a critic; through the Agent tool. Sweeps are
told what is already written so they look for the gaps.

## Decisions carried

1. Fetch-and-verify research; no quote, no row.
2. Community sources `forum`, dated; manufacturer web pages labelled as
   such; official documents cited directly.
3. Every number labelled; percentages only with their source in the same
   sentence (248's rule).
4. `thermal` category empty; no seeding here (F90).

## Scope

1. Up to four rows in `known_issues_thermal.json` (above), `make`
   list-valued; regulation or forum rows only if records survive.
2. Tests in 248's shape, with 249's concepts in titles and a boundary test
   that no row restates 246's battery bands or 243's coolant interval.
3. Research record here; README and guide count bump.

## Non-goals

- No battery charge/discharge limits or battery bands (246), no controller
  codes (247), no regen (248), no LiveWire coolant interval (243), no
  Energica service intervals (244).
- No derating curve or threshold from memory. None.
- No schema change; no seeding; no new commands.

## Results (v1.1)

**Built as planned: four rows, and a correction to the row itself.** The
roadmap row's first bullet, "liquid cooling loops (battery)", is not borne
out by any of the three makers' documents. Zero's manuals describe no
coolant at all and call the powertrain "passively air-cooled". Energica's
manual says only that the central battery compartment "allows cooling of
the battery", and its technology page credits "specific ventilation
paths". LiveWire's service manuals route coolant through the on-board
charger, the controller electronics and the motor, and no coolant-flow
step or hose procedure includes the RESS; two S2 steps name a "battery
charger to RESS coolant hose" that nothing else in that manual shows. No
document states how any of the three batteries is cooled. The row now
says so, as rows 212 and 245 were corrected, and a test forbids any row
from asserting a liquid-cooled or an air-cooled pack.

### The content (`known_issues_thermal.json`, four rows)

| Concept | Row | Source | Anchors |
|---|---|---|---|
| Architecture | *Nothing on any make is documented as a liquid-cooled battery — what each maker's documents call air-cooled, liquid-cooled or leave unstated* | service-manual | Zero 8811984-AF §4.11/§6.6/§8.18, 88-09445-01, 2020 service manual heat-sink procedure; Energica ENF003100 Rev. 02 pp.57, 72, 121, technology page captures 2019 and 2021, Experia and Ego pages; H-D LiveWire ONE service manual 94000865 and S2 service manual 94001237 (coolant flow, EVPT table, RESS removal, PEU steps, fans) |
| Motor and controller temperature | *Motor and controller temperature on each make — a gauge with no number behind the red, a thermal strategy with no curve, and no motor gauge at all on some* | service-manual | Zero 8811984-AF §2.2/§3.24/§3.27/§4.11/§4.12/§8.18, 88-09445-01, 88-09447-01 §3.11/§3.14/§4.5/§7.6–7.7, firmware page; Energica pp.27, 33, 63, repair-information sheet; H-D 94000703, 94001019, 94001315 |
| Cooling-loop faults and service | *The cooling loop's own faults and service on each make — pump and fan codes, a coolant lamp whose number is only in the service manual, and Zero with no loop at all* | service-manual | Zero 8811984-AF §6.2–6.5/§6.39, 2020 service manual heat-sink procedure; Energica pp.78–80, 108, 114–116; H-D 94000703 p.89 and Table 37, 94001019 alerts, 94001315 alerts and charging icons, service manuals' General Tables 2–3, Operation pump table, Troubleshooting, Pressure Cap Test; NHTSA regulator sentence |
| Ambient | *Ambient heat and cold on each make — what the manuals say about riding, parking and storing, apart from the battery's own limits* | service-manual | Zero 8811984-AF §3.27/§6.9/§7.8/§7.9; Energica pp.34, 37, 121, repair-information sheet PID 46; H-D 94001315 portable-charger instructions, service manuals' Freeze Point Test and Drain and Fill notice |

**What is new against the rows already shipped.** Zero's motor gauge bands
(White 20–118 °C, Red 118–150 °C) and the manual's own contradiction about
a numeric motor temperature; the Cypher II two-stage yellow indicator and
its motor and board temperature codes; the platform clash on codes 41, 55,
56 and 57; the Cypher II controller heat sink and its thermal-grease
procedure; Energica's water-pump, charger-fan and charger-temperature codes
(nine codes on the fault row's `dtc_codes`), its coolant-level check and
its PIDs 05 and 46; LiveWire's coolant loop as the service manuals draw it,
the coolant lamp's 178 °F (81 °C), the pressure-cap limits, the pump
control table and run-on, the S2 fans, and the cooling alerts per
generation. Everything already shipped — 246's battery bands and limits,
243's coolant loop and interval, 244's fluids and intervals, 247's
temperature codes and Propulsion Limited — is named by reference, never
copied, and the content test enforces it: no sentence about the battery
may repeat one of the ten temperature ranges printed in 246's
thermal-derating row, and no row may carry 243's coolant interval.

**Energica's anchor is the document, not a model year.** A refuter found
that the Eva manual's revision date is February 2018 while its sample
labels read model year 2016, so the 249 rows cite "the Energica Eva
owner's manual, Cod. ENF003100 Rev. 02 (February 2018), which names the
Eva 80 and Eva 107", and a test forbids "2018 Eva". The 246–248 rows use
"the 2018 Eva" 24 times; correcting them is F93, not this phase.

### Deviations

1. **Four rows, all service-manual.** No regulation row: no recall on any
   make concerns cooling; the regulator record is a sentence on the fault
   row, naming Zero's pack campaigns 13V257 and 18V215 and the
   rotor-to-stator campaign 14V119 as what they are. No forum row: the one
   readable forum thread holds no quotable statement.
2. **The row's premise is corrected**, above.
3. **The service manuals were reachable.** The 2021 LiveWire ONE and 2024
   S2 dealer service manuals on Harley-Davidson's Service Information
   Portal were read for the first time in this corpus; 243's caveat that
   no LiveWire service manual could be opened is now stale (F93).
4. **Kills**: 14 claims — pure restatements of 243, 244, 246 and 247
   content, the MotoE race-bike articles (pit equipment on the Ego Corsa,
   not a road model), the marketing lines "no heat throttling" and the
   competitor claim about air-cooled motors, an owner complaint, and the
   refuted recall absence.

### Verification

- 40 tests in `test_phase249_thermal_content.py`; 557 across the 19 suites
  run before the regression (the four content files 246–249, 246's
  label-surface file, 244D, 244F, 244I, 208, 78, 241–244, 244T, 03, 244S,
  244E, 240).
- **8/8 mutations killed**, bytecode cleared and `-B`: strip every
  document name · add an unlabelled 85 °C threshold as `model-generated` ·
  copy a battery range shipped by 246 · copy 243's coolant interval ·
  delete the ambient row · assert a liquid-cooled battery · anchor
  Energica to "2018 Eva" again · list a code the text never names.
- 244G raw-source scan of the new test file: clean. `ruff` clean.
- No schema change; `dtc_codes` seed and `dtc_category_meta` untouched.
- Full regression **7,195 passed, 0 failed, 18:47** — the third run on this tree; the first two finished 7,174 passed, 21 skipped (the packaging suite's wheel build could not install its build requirements mid-run), recorded in the phase log.

### Research record

**Cadence.** Three per-make sweeps, each told what the corpus already
held, produced 75 claims citing 35 URLs; 11 refuter groups fetched every
page themselves (34 served; one portal document answered 403) and judged
75/75 claims, each also flagging whether a claim only restated shipped
content; a critic read the survivors against the verified quotes and the
shipped rows. Tally: 31 survive clean, 43 downgraded, 1 refuted; the
critic killed 14 and trimmed every mixed claim to its new half. Eleven
claims were flagged as restating shipped content — the first phase where
that was the largest single source of cuts.

**The refutation.** The Zero sweep said no Zero recall involves thermal
management; the refuter found 13V257 (2013 FX and XU), whose consequence
is a rapid temperature increase and off-gassing with burn risk, and
18V215, a short with fire risk. Both are pack campaigns; no recall on any
make concerns motor, controller or coolant-loop cooling, and that
narrower sentence is what the row carries.

**Grid.** Architecture and ambient have a manual anchor for every make.
Empty cells, carried as absences: a documented battery cooling method on
all three; a derating curve, percentage or trigger temperature on all
three; any motor or controller temperature display on Energica; any
owner-facing motor or inverter over-temperature alert on LiveWire; any
cooling-loop fault on Zero (it has no loop); every Energica EMCE and
Experia statement beyond web pages.

**Follow-ups (F93).** The Energica anchor wording across 244–248; 243's
stale service-manual caveat; seven battery-side findings for 246 (Cypher
II BMS floors, the 2020 service manual's 55 °C charge figure and
over-temperature procedure, codes 10 and 11, the -35 °C winter floor, a
§5.1 against §7.8 cold cut-off conflict in the 2025 manual, the S2 "RESS
TEMP OUT OF RANGE" icon, the Energica CTO's battery-derate statement);
247's 25V834 bulletin model list; the unread LiveWire emergency-response
guides and parts catalogue; the forum thread and the owner complaints.

## Verification Checklist

- [x] Every row names a manufacturer document for every make it names (test)
- [x] No number without a label (test)
- [x] No row restates the battery bands or the coolant interval already shipped (test)
- [x] No row claims a liquid-cooled or an air-cooled battery (test)
- [x] `kb search cooling` / `"motor temperature"` / `ambient` each return a 249 row (test)
- [x] 246–248 tests still pass
- [x] Mutations: 8/8
- [x] Full regression green — **7,195 passed, 0 failed, 18:47**
