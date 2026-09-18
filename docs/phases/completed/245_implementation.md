# Phase 245 — Damon HyperSport / HyperFighter: nothing to write yet, and that is recorded

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-18

---

## Goal

Row 245 as written cannot be done honestly. Damon has delivered no customer
motorcycle, published no owner's manual or service documentation, has no
vehicle on NHTSA's record, and has no owner community — and the only "owner
problems" on the web are fabricated. The 242–244 per-make cadence ships
sourced claims; there are none to ship. Phase 241's precedent applies: on a
file where the content cannot be sourced, *the deliberate absence is the
content.* This phase corrects the row's premise, pauses it with an explicit
trigger, pins the absence with a tripwire so it is revisited on purpose, and
records the trap the next researcher would otherwise walk into.

## Step 0 — findings

**S0-1. The repo is greenfield for Damon.** Zero make-specific rows in
`known_issues`, `dtc_codes`, parts, workflow templates, recalls or intervals.
The only mentions are `core/models.py:68` (the `ELECTRIC` powertrain
comment), `knowledge/marques.py` and `vehicle_resolver.py:162` (244F: Damon
surfaces only through the union of list-valued `make` fields), and Phase
241's shared HV floor — 10 rows whose `make` is *"Zero, Harley-Davidson,
LiveWire, Energica, Damon"*, model *"Electric motorcycles — … Damon
HyperSport"*, years 2010–2026, `source = model-generated`. Those are the
cross-make safety floor, not Damon content. The resolver on the marque:
`resolve_vehicle('Damon', 'HyperSport')` -> VehicleIdentity(make=Resolution(field_name='make', given='Damon', resolved='Damon', method='exact', confidence=1.0, alternatives=[]), model=Resolution(field_name='model', given='', resolved=None, method='unresolved', con.

**S0-2. No customer unit has been delivered.** Damon's own investor-relations
release of 2025-05-28 lays out a twelve-phase plan whose *prototype
production* is Q1 2026 and battery validation Q2 2026, says "initial product
is expected to remain on schedule for 2026", and mentions no customer
deliveries. Damon's help-centre delivery-date article returns 404;
`damon.com` returned 522 at research time. Independent press through March
2025 asks whether Damon will ever deliver and records the co-founder's
departure; the company had been taking pre-orders since the CES 2020 unveiling.

**S0-3. There is no manufacturer documentation to source from.** No owner's
manual, service manual, bulletin or published fault-code table exists. What
Damon has published is a *prototype's* feature set, via its CES 2020 demo and
press coverage of it: **Shift** moves the windscreen, footpegs, handlebars
and seat between a sport and a commuter position on a button, while riding —
it is *ergonomics*, not suspension; **CoPilot** is 77 GHz radar and 1080p
cameras feeding a neural net that warns through LEDs on the windscreen's
trailing edge and haptics in the bars, and also reads the rider's grip and
posture. **Row 245's "Shift smart suspension" is wrong** — the same
wrong-premise shape as row 212's chain final drive.

**S0-4. NHTSA has no Damon vehicle on record.** The products endpoint for
`make=damon`, model year 2026, returns Count 0: no model, therefore no
recall campaign. The recalls-by-vehicle endpoint answers 400 for the make.

**S0-5. The trap: fabricated owner content exists for a bike with no owners.**
`ev.care` states the HyperSport "launched in Canada/US in 2024" and lists
"regen tuning abrupt in the first 1,000 km", "throttle map firmware updates
after service" and "connector waterproofing degrading during prolonged
monsoon parking", attributed to "earlier production batches … addressed by
OTA updates". No owner, date, region or source is named, and it contradicts
the manufacturer's own May 2025 schedule. `ridereview.com` and a
`bikenrider.com` "reaches its first customers" post are the same shape. Under
the 242 cadence every one of these dies at the refuter; the danger is a later
researcher, or an AI, ingesting them as forum tips. The tripwire records the
trap.

**S0-6. Cadence.** 242–244 ran the sweep and refute as an orchestrated
six-agent workflow; this phase ran the same five lenses solo — manufacturer
document, regulator record, owner community, tooling, platform generation —
because three primary sources settled it and the orchestrated run was neither
opted into nor needed. The research record is this section.

## Scope

1. **Row 245 corrected and paused.** The description states what Shift and
   CoPilot are; status ⏸️ with the trigger: *revisit when Damon ships
   customer units and publishes an owner's manual — and see S0-5 before
   trusting any "owner report".*
2. **A tripwire, `tests/test_phase245_damon_absence.py`**: Damon has zero
   make-specific `known_issues` rows; the shared HV floor still names it;
   every row naming Damon is `model-generated` (so an ingested "forum" or
   "owner" entry fails here first); the marque resolves. Its docstring is
   the trigger and the trap.
3. **No content authored, no schema change, no generic EV content** —
   246/247/249 own BMS, inverter and thermal.
4. Close-out rows; the row is not ✅.

## Non-goals

- No Damon `known_issues`, DTCs, parts or intervals. Nothing sourced exists.
- No change to the 241 HV floor.
- No research workflow; see S0-6.

## Verification Checklist

- [x] Row 245 no longer says "smart suspension"; it is ⏸️ with the trigger
- [x] The tripwire passes today and its docstring names the trigger and the trap
- [x] The tripwire fails if a `make = "Damon"` row is inserted with any source other than `model-generated` (mutation)
- [x] The tripwire fails if the shared HV row stops naming Damon (mutation)
- [x] Full regression green — **6,977 passed, 0 failed, 19:48**

---

## Results (v1.1)

**Built as planned. Nothing authored. No deviations.**

Row 245 is rewritten: Shift and CoPilot described from press coverage of the
CES 2020 prototype, the delivery status from Damon's own 2025-05-28 release,
the NHTSA result, and the trigger — *customer units shipped and an owner's
manual published* — with the fabricated-review trap named in the row so
nobody has to open this doc to be warned. Status ⏸️, not ✅: the row was not
done, it was found undoable, and that is a different thing.

`tests/test_phase245_damon_absence.py` pins the absence on a fixture seeded
from the 241 HV file — the only seed file that names Damon, which the
fixture proves by loading only it: no make-specific row; no Damon seed file;
the HV floor still names Damon (10 rows); every row naming Damon is
`model-generated`, so a "forum" or "owner" entry fails there first; the
marque resolves exactly and the model resolves to nothing, which is correct
today. The docstring is the trigger and the trap. Scanned with 244G's
raw-source guard before it was installed: clean.

### Verification

- 5 tests; 216 across the phase suite and the gate suites.
- **2/2 mutations killed**: a fabricated `forum` row for Damon appended to
  the HV seed (`test_every_row_naming_damon_is_model_generated` and the
  make-specific check fail); "Damon" removed from the shared make string
  (`test_the_hv_floor_still_names_damon` fails). Run with bytecode cleared.
- No source change under `src/`; no schema change; nothing reachable that
  was not.
- Full regression **6,977 passed, 0 failed, 19:48**.

### Research record

Solo, through the 242 sweep's five lenses. **Manufacturer document:** none
exists; the IR release of 2025-05-28 is the primary status source. **Regulator
record:** NHTSA products endpoint, `make=damon`, model year 2026, Count 0.
**Owner community:** `myevdiscussion` and `motorcycleforum` threads are
pre-order holders and press-ride impressions of prototypes. **Tooling:**
none published. **Platform generation:** HyperSport HS / Premier / SX / SE
and HyperFighter are announced trims of a prototype. **Rejected:** `ev.care`
("launched in Canada/US in 2024"; regen, throttle-map and "monsoon parking"
connector problems "fixed by OTA") — no owner, date, region or source, and
contradicts the manufacturer's schedule; `ridereview.com` and
`bikenrider.com` ("reaches its first customers") — same shape. Damon's
delivery-date help article returned 404 and `damon.com` 522 on two attempts
two minutes apart; recorded, not interpreted.
