# Phase 249 — Thermal management: the generic layer, anchored per make

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-18

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

## Verification Checklist

- [ ] Every row names a manufacturer document for every make it names (test)
- [ ] No number without a label (test)
- [ ] No row restates the battery bands or the coolant interval already shipped (test)
- [ ] `kb search cooling` / `"motor temperature"` / `ambient` each return a 249 row (test)
- [ ] 246–248 tests still pass
- [ ] Mutations
- [ ] Full regression green
