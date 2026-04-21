# Track G Research Brief: Mechanic Workflow (Issue Taxonomy + Priority Heuristics)

Research for Phases 162 (issue logging), 163 (AI priority scoring), 165 (parts linkage).
Source: Domain-Researcher agent + mechanic-forum synthesis (HD Forums, ADVrider, r/MotoMechanic, MIC data).

---

## 1. Issue Category Taxonomy (Phase 162)

**Ship with 12 categories** (expand from existing 7 in `core/models.py::SymptomCategory`):

Existing to keep: `engine`, `fuel_system`, `electrical`, `cooling`, `exhaust`, `transmission`, `other`.

REQUIRED new additions:
- **`brakes`** — MANDATORY. Safety tier always elevates for brake complaints. Covers pads, rotors, calipers, master cylinder, lines, ABS sensors, bleeding.
- **`suspension`** — Forks, shocks, linkage, bearings, fork seals. ~20% of sport-bike bench time.
- **`drivetrain`** — Chain+sprockets, belt, driveshaft, u-joints, clutch cable/line. DISTINCT from transmission (transmission = internal gearbox; drivetrain = engine-output to rear-wheel).
- **`tires_wheels`** — Tires + wheel bearings + TPMS + tubes + cush drives. #1 revenue line in independent shops.
- **`accessories`** — Aftermarket installs (bags, windshields, crash bars, heated grips, lighting, ECU flashes). 30-50% of Harley shop revenue.

RECOMMENDED addition:
- **`rider_complaint`** — Subjective intake ("feels wobbly," "weird vibration"). Phase 163 defaults to Tier 3 medium pending diagnostic reassignment.

Deferred to Phase 164:
- `bodywork` — Crash repair + cosmetic. Low frequency, can wait.

**Real shop ticket distribution (baseline to validate against):**
- ~35% engine/fuel/electrical
- ~25% tires/brakes
- ~15% suspension/drivetrain
- ~15% accessories/install work
- ~10% rider-complaint diagnosis

Existing 7 categories misfile ~40-50% of tickets into "other." 12 categories covers ~95%.

---

## 2. Severity Rubric — 4 Tiers (Phase 163)

### Tier 1: CRITICAL
Immediate safety-to-rider risk. Bike must not leave shop in current state. Mechanic may advise tow-in.

Examples: stuck throttle, fuel leak at tank/petcock/injector, brake failure (no pressure / seized caliper), steering head bearing failure (headshake >40mph), frame crack, electrical fire/smoke, wheel bearing collapse, tire cord showing, chain/belt imminent failure, stuck-on cooling fan + overheating.

### Tier 2: HIGH
Ridable only short distance. Customer can ride home carefully but not on a trip.

Examples: soft brake lever, headlight out, failing charging system, loose/dry chain, tire <2/32" tread, weeping oil leak, clutch slip under load, stalls at idle only, turn signal inoperative, coolant weeping at hose clamp, fuel-trim/misfire DTCs, new handlebar vibration.

### Tier 3: MEDIUM
Safely ridable. Fix within normal service interval. No safety/stranding risk.

Examples: intermittent turn signal, rough idle that clears under load, fuel economy drop, stiff clutch lever, horn inoperative, minor valve-cover seepage, slight speedo error, soft suspension out of spec, speed-specific wobble only, accessory malfunction (heated grips out, Bluetooth), fork seal weeping.

### Tier 4: LOW
No functional impact. Pure cosmetic or comfort.

Examples: scuffed tank, stuck mirror adjustment, worn seat foam, paint chip, unused-accessory malfunction, clock issues, loose fairing clip, rider-preferred mods (taller bars, different pegs).

### AI prompt rule
"Default to higher tier when in doubt. If complaint mentions brakes, fuel, steering, tires, or electrical-smoke → Tier 1 pending diagnosis. If complaint is rider-subjective → Tier 3 + flag for diagnostic reassignment."

---

## 3. Priority Scoring Formula (Phase 163)

**No industry standard exists** — moto-diag sets the baseline.

```
priority_score = base_tier_score + wait_age_bonus + customer_history_bonus

base_tier_score:
  Tier 1 (Critical) = 1000
  Tier 2 (High)     = 500
  Tier 3 (Medium)   = 200
  Tier 4 (Low)      = 50

wait_age_bonus = wait_days × tier_aging_rate
  Tier 1 aging = 100/day  (shouldn't matter — Tier 1 flips same-day)
  Tier 2 aging = 50/day   (matures to near-Tier-1 at 10 days)
  Tier 3 aging = 20/day   (matures to near-Tier-2 at 15 days)
  Tier 4 aging = 10/day   (matures to near-Tier-3 at 15 days)

customer_history_bonus (regulars get priority bump):
  0 prior tickets (last 12mo)  = 0
  1-2 prior tickets             = 25
  3-5 prior tickets             = 75
  6+ prior tickets (regular)    = 150

Ceilings/floors:
  Max priority_score = 1500 (aged Tier 4 can't beat fresh Tier 1)
  Tier 1 floors at 1000 regardless of age
  rider_complaint default = 300 until reclassified
```

### Worked examples

- New customer, Tier 3, waited 10 days: 200 + (10×20) + 0 = **400**
- Walk-in Tier 2 soft-brake, 1 prior ticket: 500 + 0 + 25 = **525** (correctly ahead of aged T3)
- Same T3 after 25 more days: 200 + (25×20) + 0 = **700** (now beats fresh T2 — correct, customer is furious)

### Shop-triage empirical norms
- Tier 1 → same-day / next-day
- Tier 2 → same-week (3-5 business days)
- Tier 3 → FIFO within 2-week window
- Tier 4 → FIFO within 4-week window
- "Bench rot" (>14 days on T3, >21 days on T4) triggers customer call to schedule or release bike — #1 customer-satisfaction complaint per MIC survey

---

## 4. Failure-Mode → Parts Clusters (Phase 165 seed data)

Top 5 failure modes per system, with parts clusters Phase 165 should pre-aggregate.

### Engine (category: engine)
1. **Won't start / cranks no fire** → spark plugs, ignition coils, plug wires, CKP/CMP sensors, kill switch, battery load test
2. **Misfire / rough running** → spark plugs, coils, injectors (FI), carb jets+floats (carb), compression test gauge
3. **Oil leak** → valve cover gasket, base gasket, cam chain tensioner seal, oil pan gasket, crankshaft seals, oil filter
4. **Overheating (air-cooled)** → oil cooler, cooling fin cleaning, correct-weight oil, thermostat (if oil-cooled)
5. **Top-end noise** → valve shims / screw-adjust tappets, cam chain tensioner, valve lash gauge kit

### Fuel system
1. **Stalls at idle, runs fine above** → pilot jet (carb), IAC valve (FI), vacuum leak check, throttle body sync
2. **Hesitation / bog under acceleration** → accelerator pump, fuel pump pressure test, fuel filter, injector clean
3. **Fuel leak** → tank petcock, fuel line, fuel pump gasket, injector O-rings, carb float bowl gasket
4. **Hard starting when hot** → fuel pump, vapor lock (tank vent), ethanol-degraded rubber lines, FPR
5. **Running rich/lean** → O2 sensor, MAP sensor, air filter, TPS, ECU flash

### Electrical
1. **Battery dies overnight** → parasitic draw test, battery load test, battery replace, stator + R/R output test
2. **Charging fault** → stator, R/R, main harness (stator plug corrosion), battery
3. **Starter won't engage** → starter relay, brushes, solenoid, side-stand switch, clutch safety switch
4. **Intermittent electrical** → ignition switch, main harness (corroded connectors), terminal corrosion, frame ground
5. **ABS / traction fault** → wheel speed sensors, tone rings, ABS module, related fuse

### Brakes (new category)
1. **Soft/spongy lever** → brake fluid flush, bleed kit, master cylinder rebuild kit, SS brake lines, caliper seals
2. **Pulsation / warping** → rotors (measure thickness + runout), pads, caliper pins
3. **Pads metal-on-metal** → pads (OE or upgrade), rotors if scored, caliper clean+lube kit
4. **ABS fault** → wheel speed sensor, tone ring, ABS module, wiring harness at fork
5. **Dragging caliper** → caliper seals, pistons (corrosion), slide pins, brake fluid flush

### Cooling (liquid-cooled)
1. **Overheating idle-only, fine moving** → radiator fan, fan relay, fan temp sensor, coolant level
2. **Coolant leak** → water pump seal, hose clamps, radiator, thermostat housing gasket, head gasket (worst case)
3. **Runs cold / slow warmup** → thermostat stuck open, temp sensor
4. **Coolant in oil / oil in coolant** → head gasket, cylinder head crack, water pump seal (internal)
5. **Pressure loss at cap** → radiator cap, overflow bottle+hose, pressure test kit

### Cross-system quick notes
- Drivetrain → chain, sprockets F+R, master link, belt, tensioner, drive pulley
- Tires → tire (size-matched), tube if required, valve stem, wheel weights, cush drives
- Suspension seals → fork seal kit, fork oil, dust seal, slider bushings, shock linkage bearings

Parts clusters should be seeded from JSON rubric Phase 165 ships with, keyed by (category, top_complaint_keyword). Phase 177-180 analytics can learn actual parts-usage patterns per issue over time.
