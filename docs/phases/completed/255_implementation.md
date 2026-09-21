# Phase 255 — The transmission axis: a machine attribute, a row declaration, and a filter that excludes

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-21

---

## Goal

Row 255 was planned as "Twist-and-go vs manual small bikes — scooter vs small
motorcycle diagnostic differences." Its Step 0 found that the corpus cannot
express that distinction at all, and that Phase 254 shipped a defect because of
it. So 255 becomes the mechanism and **255B becomes the content row**.

Build a transmission axis: a typed machine attribute, a per-row declaration of
which transmissions a row applies to, a resolver that returns a *candidate set*
rather than a guess, and a filter that **excludes** rather than reorders.

## Step 0 — findings

Measured against the live database (1045 rows, schema 62) on 2026-09-21.

**S0-1. Phase 254 shipped a defect, and this phase's first measurement found
it.** Every Honda and every Yamaha retrieves the generic CVT layer, including
machines with no CVT:

| machine | CVT rows retrieved |
|---|---|
| Honda CBR1000RR (6-speed sportbike) | 7 |
| Honda GL1800 Gold Wing | 7 |
| Honda Grom (5-speed, wet multiplate) | 7 |
| Yamaha YZF-R1 | 8 |
| Yamaha XS650 | 8 |
| Honda PCX 150 (scooter — correct target) | 7 |
| **Kawasaki Ninja 400** | **0** |

Kawasaki's zero isolates the cause: the 254 rows carry `make = "Piaggio, Vespa,
Honda, Yamaha, Kymco, SYM, Genuine"`, so any Honda or Yamaha matches at the
make-wide tier. Kawasaki is not in that list. It is the make column doing this,
not the content.

**By the delivery standard this is a validation failure, not a verification
one.** Phase 254 passed 85 tests, 22/22 mutations, a 986-test blast radius and a
7,750-test regression, all green, and still reaches machines it does not
describe. Logged as a dated bug-fix entry against 254 with its own commit.

**S0-2. The corpus cannot express the distinction the original row was about.**
`LIKE '%manual%'` returns **311 rows, of which 300 are the document** — service
manual, owner's manual, workshop manual. Exactly **2** use the word in the
transmission sense. This is the fifth consecutive substring collision found at
Step 0 (grommet, symptom/system/genuine part, controller/kickstand, and now
manual), and the worst ratio of the five. Filed as an F-ticket; not fixed here.

**S0-3. There is no transmission attribute anywhere.** `vehicles` carries
`powertrain`, `engine_type`, `battery_chemistry`, `motor_kw`, `bms_present` —
and nothing for transmission. `known_issues` carries no applicability of any
kind.

**S0-4. A third axis is already visible, and it predates 254.** Measured across
subsystem axes on probe machines — measurement only, nothing fixed:

| machine | axis | rows | verdict |
|---|---|---|---|
| CBR1000RR, Gold Wing, Grom, R1, XS650 | cvt/variator | 7–8 | over-reach, no CVT |
| **Yamaha XS650** | **liquid cooling** | **11** | **over-reach, air-cooled twin** |

74 of 1045 rows name more than one marque. By subsystem: cvt/variator 11 rows (8
multi-make), liquid cooling 67 (11), carburettor 52 (2), chain final drive 8 (0),
clutch pack/lever 15 (0), kickstart 4 (1).

The XS650 cooling over-reach is **not** from 254 — it predates it. Own finding,
own F-ticket, not fixed here.

**S0-5. Mobile writes to this table, so a one-time migration would have been
wrong.** `NewVehicleScreen.tsx:121` calls `api.POST('/v1/vehicles', {body})` into
`create_vehicle_endpoint` and the same `vehicles` table. The body carries `make,
model, year, engine_cc, vin, protocol, powertrain, engine_type,
battery_chemistry, motor_kw, bms_present, mileage, notes` — no transmission, and
none is being added to mobile in this phase. Every mobile-created vehicle will
land with the column NULL. **The backfill must therefore be a resolver applied at
read time, not a migration run once.**

Note that mobile already sends `powertrain` as a first-class field, which gives
the later mobile phase a precedent to copy.

**S0-6. 250B's powertrain filter cannot be mirrored, for two independent
reasons.** Read from the code, not assumed:

```python
if (powertrain or "").lower() == "electric":
    pool = _electric_first(rows, limit)
```

1. **It reorders, it does not exclude.** `_electric_first` returns
   `electric + [everything else]`; nothing is removed. Copying it would put CVT
   rows first for a scooter and leave them in the prompt for a CBR1000RR.
2. **It infers the row's powertrain from the row's marque names**, and
   `is_electric_row` is documented as *"deliberately generous: a row naming four
   marques of which one is electric IS about an electric machine."* That
   generosity is precisely what breaks here, because Honda and Yamaha build both
   scooters and motorcycles.

**255 deliberately diverges on both points**, and the ADR records why.
**250B itself is not touched.**

**S0-7. Infrastructure that already exists and will be reused.**
`rollback_to_version(target_version, db_path)` at `core/migrations.py:4447`;
`MIGRATIONS` registry at `core/migrations.py:55`; `SCHEMA_VERSION = 62` in
`core/database.py`; and the enum precedent — `PowertrainType(str, Enum)` in
`core/models.py`, introduced by Phase 110's retrofit "so downstream modules can
gate electric-specific logic without sprinkling make/model checks." That sentence
is this phase's brief, one axis over.

**S0-8. Cub clutch construction — verified first-hand, and my premise was half
wrong.** Documents fetched and checked in the main session, not accepted from a
report. All from **Honda's own servers**.

*Parts catalogue `13K0GK01`, "PARTS CATALOG SUPER CUB C125", © Honda Motor Co.,
Ltd. 2018, `2rom-prd-data.hondamotopub.com` (115 pages).* Every part number and
name below was confirmed present by direct extraction:

| Honda's own name | number | section | friction plates |
|---|---|---|---|
| `DISK, CLUTCH FRICTION` ×3, `DISK COMP., CLUTCH FRICTION` ×1, `PLATE, CLUTCH` ×3, `SPRING, CLUTCH` ×6, `OUTER COMP., CLUTCH` | 22201-KYZ-901, 22208-KYZ-901, 22321-KE8-000, 22401-KYZ-901 | E-8 `CLUTCH` | **yes** |
| `WEIGHT SET, PRIMARY CLUTCH`, `SPRING, PRIMARY CLUTCH`, `OUTER ASSY., PRIMARY CLUTCH` | 22535-K73-T30, 22641-KYZ-901, 22660-K0G-901 | E-7 `ONE WAY CLUTCH` | **no** |
| `STARTING CLUTCH` | — | E-9 | no — this is the **starter motor sprag** |
| `LEVER COMP., CLUTCH`, `BOLT, CLUTCH ADJUSTING` | 22810-KPH-900, 22846-K0G-900 | E-6 R. crankcase cover | actuation, **inside the engine** |

**Three consequences.**

1. **Friction plates are a definite yes, not a "may".** Plate, disc, spring and
   pressure-plate content is live Cub content.
2. **"Lever" is not a usable exclusion signal.** Honda's own part name for the
   internal actuator is `LEVER COMP., CLUTCH`, inside the right crankcase cover.
   Excluding on the word "lever" would have withheld content that applies. The
   authoring discriminator is **handlebar / cable / hydraulic**, not "lever".
3. **The Cub has two clutches with disjoint parts and disjoint symptoms** — a
   centrifugal primary (E-7, no friction plates) and a multiplate change clutch
   released by the gear pedal (E-8). A single "Cub clutch" notion merges them.

**A claim I had to downgrade.** "Clutch free play is a published Cub adjustment"
is **not supported for the C125**. Its owner's manual — `32K0GC20` /
`00X32-K0G-C200`, © Honda Motor Co., Ltd., same host, 140 pages — returns **zero**
hits for `clutch lever`, `clutch cable` and `clutch adjust`, and only three
`clutch` sentences, none about free play. Its 18 `freeplay` hits are all brake
("Freeplay at the tip of the brake pedal"). The parts catalogue proves a
`BOLT, CLUTCH ADJUSTING` exists; **no obtainable Honda document publishes a C125
clutch free-play procedure.** Cub clutch *adjustment* content is therefore
unanchored, which is a reason to withhold it rather than to route it.

**Honda's vocabulary, two traps.** `STARTING CLUTCH` is the **starter motor
sprag**, not the centrifugal drive clutch — Honda's word for that is **primary
clutch**, and my own earlier brief used "start clutch" wrongly. And "basket" is
not Honda's word at all: it is `OUTER COMP., CLUTCH` (E-8) against
`OUTER ASSY., PRIMARY CLUTCH` (E-7), so generic "basket" content maps
ambiguously and must be resolved by reading the row.

"Judder" appears in no document reached. The nearest Honda failure vocabulary is
"Clutch plate uneven" and "Warped clutch disc/plate" (CT90-110 shop manual,
archive.org mirror), both E-8. Mapping judder to E-8 would be **inference, not
citation**, and is therefore not done.

## Decisions

**D1. The axis is transmission mechanism, not rider experience.** Six values,
each defined by mechanism, because the maker's own word is unreliable — Honda
publishes the **Trail 125 as "Semiautomatic; four speeds" in 2022 and "Manual; 4
speeds" in 2026** for an unchanged machine. Classification rule: *which
diagnostic content applies to this machine.*

| value | mechanism |
|---|---|
| `manual` | rider-operated clutch, rider-selected gears |
| `cvt` | continuously variable pulleys and belt, centrifugal clutch, no gear selection |
| `dct` | two clutches, automated engagement, gears automated or rider-commanded |
| `semi_auto_centrifugal` | centrifugal clutch, rider-selected gears, no clutch lever |
| `semi_auto_actuated` | conventional clutch, electronically or hydraulically actuated, rider-selected gears, no clutch lever |
| `direct_drive` | no gearbox and no clutch |

`semi_auto` is split because the two sub-mechanisms differ diagnostically: a
Cub's clutch and a Y-AMT's clutch are not the same object, and collapsing them
would reproduce the over-reach this phase exists to fix, in miniature.

Placements: **Honda DCT** (Africa Twin, Gold Wing, NC750X) → `dct`. **Honda
E-Clutch** (CB650R/CBR650R 2024+) → `manual`, because the lever is present and
every manual-clutch diagnostic still applies; the actuator is an addition, not a
replacement. **Yamaha Y-AMT** (MT-09, Tracer 9) and **FJR1300 YCC-S** →
`semi_auto_actuated`. **Super Cub C125, Symba, Trail 125** →
`semi_auto_centrifugal`.

**D2. E-Clutch is a known limit, recorded now.** If actuator-specific rows ever
exist they are **model-scoped**, not a seventh enum value.

**D3. Row-side declaration is a SET, assigned per row from what that row
actually says.** Not per category, not per subsystem, and never inferred at
runtime.

**There is no keyword matching anywhere** — not in seed authoring, not at load,
not at read. Every set is declared **by row id, with a written reason.** The
handlebar/cable/hydraulic discriminator from S0-8 is an **authoring guide for
whoever reads the row**, not a classifier; nothing in the code ever looks at row
text.

The standard is the same one the C70/CT90 non-goal applies: a row gets a
transmission value only if **its own content holds for that mechanism**. So a
254 row about a scooter clutch bell's inner-diameter wear limit is `{cvt}`
alone — it does **not** get `semi_auto_centrifugal`, because that limit is a
scooter figure and a Cub's primary clutch is a different assembly with different
parts. **Expect most 254 rows to be `{cvt}` alone.** A row earns a second value
only by being about something that genuinely holds for both.

**D4. The resolver returns a candidate set, never a guess.** `make/model/year`
cannot separate a manual Africa Twin from a DCT Africa Twin — both are sold in
the same model year. So the resolver answers with the set of transmissions the
machine might have.

**Inclusion rule:** a scoped row is included only if **its declared set covers
every candidate.**
- Unknown machine → candidates are all six values → only a row declaring all six
  passes, which is equivalent to unscoped. This is the fail-closed policy.
- Ambiguous Africa Twin → `{manual, dct}` → rows valid for both pass; lever-only
  rows and dct-only rows are withheld.

Never misleading, sometimes missing. That trade is deliberate: a Gold Wing told
about variator rollers is a wrong answer; a PCX missing one row is an incomplete
one.

**D5. Resolver precedence, in order:** explicit column → model lookup →
powertrain inference → unknown. **`electric ⇒ direct_drive` is a default with
model overrides, not a rule** — the Brammo Empulse has a six-speed, Electric
Motion trials machines have a clutch, and the Ninja 7 Hybrid is an automated
manual. Entries that cannot be classified confidently **stay NULL and are never
guessed.**

**D6. The fail-closed cost is measured, not assumed.** A counter logs every
retrieval where scoped rows were withheld, **distinguishing unknown from
ambiguous**, so the cost of the policy is visible rather than argued about.

**D7. Row-side shape takes the next axis without a second migration, and it
carries a contract.** `known_issues.applicability` holds a JSON object keyed by
axis — `{"transmission": ["cvt"]}`. Adding cooling later is a new key, not a
migration. The extra cost over a single `transmission_applicability` column is
small because filtering happens in Python (`prompt_rows.py`), not in SQL.
**Machine-side stays per-axis typed columns**, so `vehicles.transmission` is its
own column with a CHECK constraint, exactly as `powertrain` is.

**The contract, because a JSON column has none by default:**

- A pydantic model with **`Literal` axis keys** and **`Literal` values**.
- **Validated at seed load and again at read.** An unknown key or an unknown
  value is **rejected loudly** — not dropped, not defaulted.
- **Semantics:** an **absent key** means unscoped on that axis. An **empty list
  is a validation error**, never "applies to nothing" and never "applies to
  everything" — an empty list is almost always an authoring mistake and must
  fail rather than silently do one of two opposite things.

**Stated limit:** a JSON column has **no CHECK constraint**, so the Phase 195C
schema lint does not cover it. **The pydantic model is the only guard**, which
makes it load-bearing, so it gets its own test — including a rejected unknown
axis and a rejected unknown value.

**D8. 250B is not touched.** The ADR records the deliberate divergence and notes
that marque inference is a known weaker pattern.

**D9. A known limit, accepted and documented: large maxi-scooters lose
friction-plate content.** The Yamaha TMAX and Suzuki Burgman 650 run a **wet
multiplate clutch alongside a CVT**. Declared `{cvt}`, they will not receive
friction-plate rows that genuinely apply to them. **Missing, not misleading** —
which is the trade D4 already makes — and recorded here so it is a known cost
rather than a surprise. Revisited if a maxi-scooter content row is ever written.

**D10. The general applicability mechanism is a named phase, not "future."** The
ADR names it, because a third axis is already visible (S0-4).

## Scope

1. `VehicleTransmission(str, Enum)` in `core/models.py`, mirroring
   `PowertrainType`, `Literal`-typed at every contract boundary (F9 subtype 3).
2. Migration 063: `vehicles.transmission` with a CHECK constraint;
   `known_issues.applicability`. `SCHEMA_VERSION` 62 → 63. Rollback tested with
   `rollback_to_version`; all schema assertions `>= N`, never `== N`.
3. `knowledge/transmission.py` — the resolver: candidate sets, the four-rung
   precedence, the model lookup table, and the withheld-rows counter.
4. `prompt_rows.py` — the exclusion filter. Additive parameter; existing callers
   unchanged when it is not passed.
5. Seed declaration of the 254 CVT rows as `{"transmission": ["cvt"]}`, plus any
   other row whose set is unambiguous from what it says.
6. `tests/test_phase255_transmission_axis.py` — the machine-level regression
   guard with negative assertions. **This is the test Phase 254 was missing.**
7. ADR recording D1, D4, D5, D7, D8 and naming the general-applicability phase.

## Non-goals

- **No content row.** The twist-and-go vs manual diagnostic differences are
  **255B**, and 255B selects its rows by the axis rather than by searching for
  the word "manual" — so it does not depend on the substring collision being
  fixed.
- **No mobile garage field.** Mobile keeps writing vehicles without transmission
  and the resolver covers them. A transmission field on the mobile garage form is
  a later phase, named here so it is a decision and not an oversight.
- **No general applicability mechanism** — named in the ADR as the next axis's
  phase, not built here.
- **No fix for the XS650 cooling over-reach** — own F-ticket, predates 254.
- **No fix for substring retrieval** — own F-ticket.
- **No change to 250B.**
- **No guessed resolver entries.**
- **No carrying the C70 / CT90-CT110 clutch service limits to the C125 or
  CT125.** Those figures are real (C70 friction disc 2.3 mm limit; CT90-110 disc
  2.4 mm, plate 1.85 mm) but belong to different part numbers, and **no C125 or
  CT125 service manual is obtainable** — Honda publishes none free, and
  `hondamotopub.com` carries owner's manuals and parts catalogues only.
- **No keyword matching in seed or at runtime** (D3).

## Amendments to v1.0 (same day, before build)

**A1. Sequencing — no `manual` in any set until coverage is sourced.** The NULL
cost only bites when `{manual}` rows are scoped: a clutch-cable row declared
`{manual}` would be withheld from every unlisted CBR and Harley, which is a
worse outcome than today's. **255 therefore ships the mechanism plus `cvt`
scoping only.** Set logic and the ambiguous-candidate rule are exercised with
**synthetic test-only rows** — the Africa Twin fixture uses those, not shipped
content. The sourced manual-coverage list is a **specific later phase**:
workflow plus refuter, source = manufacturer specification pages. **No bulk
inference, ever.**

**A2. The regression that matters is machine-level, not corpus-level.** My
earlier reasoning — "models with no corpus rows can't lose retrieval they never
had" — **was wrong.** Make-wide retrieval keys on the **vehicle's** make, not on
the model having rows; that is the Step 0 defect itself, a Grom receiving seven
rows with no Grom content. So a user's TMAX or NMAX **does** get the CVT layer
today and **would lose it** on deploy. The diff is against machines:

- **(a) Live `vehicles` table, measured.** 10 vehicles, 5 of the seven makes:
  Honda CB500, CBR954RR, cbrf4i; Yamaha MT07, YZF-R1. Each gets 7–8 CVT rows
  today and each correctly loses them — none is a CVT machine. **No live vehicle
  regresses.** The exposure is future machines.
- **(b) Every model from 254's 34 owner's manuals goes in the lookup**, sourced
  to that manual, **whether or not it has corpus rows.**
- **(c) No make-default for scooter marques.** The Vespa PX and older Genuine
  Stella are **manual** — a Vespa-means-CVT default would be wrong on a machine
  Piaggio still sold recently.
- **(d) Residual gap is whatever users add next**, so the **mobile transmission
  field moves up: it is the phase immediately after 255B**, no longer "later".

**A3. XC155 / SMAX — unverified, and the lesson stands anyway.** I could not
source the equivalence: Yamaha's model pages return 200 but are JavaScript
shells, and `model_list` returned HTTP 500. The only first-hand evidence is the
**regulator's**, where the rows read `YAMAHA / XC155` and **no row says SMAX** —
so "(SMAX)" was a sweep's gloss, not a document. **The equivalence is not
asserted.** What does follow, and is the more useful half: **a name search does
not prove absence.** "SMAX returns zero rows" and "XC155 returns two rows" may
well be one machine. **Every lookup entry therefore carries an explicit alias
list — model code and marketing name — and absence is never concluded from one
spelling.**

**A4. Matching rule.** Per entry: an **explicit alias list**; strip the make
prefix; **whole-token match against aliases**, make-scoped. **No fuzzy matching.
No alpha/numeric splitting. No substring matching anywhere.** Every form
currently in the junction is a test case — `PCX150`, `PCX 150`, `PCX125`,
`PCX160`, `Honda PCX150`, `Honda PCX125`, `Zuma`, `Zuma 125`, `Zuma 50`,
`Zuma 50F`, `Yamaha Zuma 125`, `Vino`, `Vino 50`, `Vino 125`, `Vino Classic`,
`Metropolitan`, `Honda Metropolitan`, `Ruckus`, `XMAX`, `Yamaha XMAX`, `XC155`.
A test also feeds a free-text model string chosen to collide — **Like, Fly, Jet,
Kick, Wolf and Buddy are all real model names** and all are ordinary words.
**Junction junk itself stays with F108** and is not cleaned here.

**A5. Resolver returns value plus provenance**, one of `explicit`,
`model-sourced`, `powertrain-default`, `ambiguous`, `unknown`. **The
withheld-rows counter breaks down by provenance**, so the fail-closed cost is
attributable rather than a single number.

**A6. Final drive is a fourth axis, not a transmission problem.** Measured: a
PCX 150 retrieves **8** final-drive-chain rows, 3 clutch-lever/cable/pack rows
and 1 gearbox row; a Zuma 125, 4/1/2. **A belt-drive Harley and a shaft-drive
Gold Wing should not get chain rows either**, which is why this is its own axis
and **must not be solved with `{manual}` sets.** Added to the
general-mechanism F-ticket as the fourth axis.

**A7. Row 4605 is unreachable to the owners it was written for.** Its make
column is `Piaggio, Vespa, Honda, Yamaha, Kymco, SYM, Genuine`, so a
Harley-Davidson Road King and a BMW R1200GS both reach it: **False**. The row
explaining that a Harley final-drive belt is not a CVT belt cannot be retrieved
by a Harley owner. **Own finding, not fixed here.**

**A8. The set counts, corrected.** Twelve rows: **nine plain `{cvt}`**, **two
flagged `{cvt}`** (4611 kickstart, 4615 regulator methodology — both carry a
general half that belongs to a machine class wider than CVT), and **one
unscoped** (4605). **Eleven rows carry `{cvt}`; one carries no transmission
key.** 4611 and 4615 are recorded as known limits and named in the 255B plan for
splitting.

## Verification Checklist

- [ ] `VehicleTransmission` enum, six values, each defined by mechanism
- [ ] `Literal` types at every contract boundary that carries a transmission
- [ ] Migration 063 applies, and `rollback_to_version` peels it cleanly
- [ ] Every schema assertion uses `>=`, none uses `==`
- [ ] Resolver returns candidate sets; ambiguous models return more than one
- [ ] Unclassifiable models stay NULL; a test asserts coverage `>= N` of the
      corpus's models
- [ ] Withheld-rows counter distinguishes unknown from ambiguous
- [ ] Machine-level regression guard with **negative** assertions, including an
      ambiguous Africa Twin fixture with the column NULL
- [ ] 254's CVT rows reach a PCX and a Kymco Agility, and reach **none** of
      CBR1000RR, Gold Wing DCT, Grom, R1, XS650, Zero
- [ ] No shipped row declares a set containing `manual` (A1)
- [ ] Synthetic test-only rows exercise set logic and the ambiguous rule (A1)
- [ ] Every junction model form matches; a colliding free-text string does not (A4)
- [ ] Resolver returns provenance; counter breaks down by it (A5)
- [ ] Mutations caught
- [ ] Full regression green — 0 failed, 0 skipped
- [ ] 254 bug-fix entry logged with its own commit
- [ ] ADR written; F-tickets filed
- [ ] Roadmap row, `implementation.md` history row, `phase_log.md`

## Definition of done (delivery standard)

| # | item | artifact |
|---|---|---|
| 1 | Verified | regression summary with matching `collected N`; mutations `N/N` |
| 2 | **Validated** | the machine-level guard, which is the artifact 254 lacked — before/after retrieval counts per fixture |
| 3 | Traceable | the Cub clutch verification with its citation; the resolver's model table with its source per entry |
| 4 | Recorded | v1.1 + phase_log + roadmap + history + the 254 bug-fix entry |
| 5 | Reviewed | hash, diff stat, a line of v1.1 read |
| 6 | No new shadowed constant | `check_f9_patterns.py --check-ssot-constants` clean |
| 7 | Shipped data reusable | n/a — no dataset shipped this phase |

---

## Results (v1.1)

### What shipped

| piece | where |
|---|---|
| `VehicleTransmission(str, Enum)`, six values by mechanism | `core/models.py` |
| `vehicles.transmission` — typed, CHECK-constrained, **nullable with no default** | migration 063 |
| `known_issues.applicability` — JSON keyed by axis | migration 063 |
| The applicability contract — pydantic, `Literal` keys and values | `knowledge/applicability.py` |
| The resolver — candidate sets, four-rung precedence, provenance, counter | `knowledge/transmission.py` |
| The filter that **excludes** | `knowledge/prompt_rows.py` |
| 11 of 12 Phase 254 rows declared `{"transmission": ["cvt"]}` | `known_issues_cvt.json` |
| The backfill for rows already in the operator's database | `loader.backfill_row_applicability` |
| ADR | `docs/architecture/applicability-axes.md` |

`SCHEMA_VERSION` 62 → 63. 130 tests, 26 of 26 mutations, F9 lint clean.
Regression **7,882 passed, 0 failed, 0 skipped, 25:43** (baseline 7,750; +132). The
783-test blast radius ran red on three hard-coded `== 62` schema pins — as
designed — but three was not the whole set. **Twelve pins had to be touched
and it took five passes to find them all**; the account is below, because
the way they were missed is more useful than the number.

### The defect, before and after — on the diagnose path, measured by row id

Row counts below are the `_load_known_issues` path. The other two doors are
accounted for separately under "`compose_prompt_rows` was not the only
door".

Row ids 4604–4615 are Phase 254's. Eleven declare `{cvt}`; 4605 is
deliberately unscoped, which is why every "after" column reads 1 rather
than 0.

| machine | what it is | before | after | provenance |
|---|---|---|---|---|
| Honda GL1800 Gold Wing | six-speed or DCT tourer | 9 | **1** | ambiguous |
| Honda CBR1000RR | six-speed sportbike | 9 | **1** | unknown |
| Honda Grom | five-speed minibike | 9 | **1** | unknown |
| Yamaha YZF-R1 | six-speed sportbike | 10 | **1** | unknown |
| Yamaha XS650 | five-speed twin | 10 | **1** | unknown |
| Honda CB500 | **live vehicle** | 9 | **1** | unknown |
| Honda CBR954RR | **live vehicle** | 9 | **1** | unknown |
| Honda cbrf4i | **live vehicle** | 9 | **1** | unknown |
| Yamaha MT07 | **live vehicle** | 10 | **1** | unknown |
| SYM Symba | Cub clone, centrifugal | 9 | **1** | model-sourced |
| SYM Wolf 150 | manual motorcycle | 9 | **1** | model-sourced |
| Kawasaki Ninja 400 | the control | 0 | 0 | unknown |
| **Honda PCX 150** | CVT scooter | 9 | **9** | model-sourced |
| **Yamaha Zuma 125** | CVT scooter | 10 | **10** | model-sourced |
| **Kymco Agility 50** | CVT scooter | 10 | **10** | model-sourced |
| **Genuine Buddy 125** | CVT scooter | 9 | **9** | model-sourced |
| **Vespa Primavera** | CVT scooter | 10 | **10** | model-sourced |
| **Piaggio Fly 125** | CVT scooter | 10 | **10** | model-sourced |
| **SYM Symply 125** | CVT scooter | 9 | **9** | model-sourced |

**SYM is the row that proves the mechanism.** One maker, three machines,
three answers, all from that maker's own manuals: the Symply is a CVT and
keeps everything, the Symba is a Cub and loses it, the Wolf is a motorcycle
and loses it. No marque-wide inference could produce that.

**The Gold Wing is fixed by the absence of an entry, not the presence of
one.** That is worth stating because it is the opposite of how a lookup
table usually works. Fail-closed means every unlisted machine loses scoped
rows automatically; the lookup exists to **preserve** retrieval for the
machines that should keep it.

### The lookup, and what it cost to source it

**43 entries across 8 marques, every one re-read first-hand in this
session** — not accepted from a sweep's report. The evidence is tiered and
each entry quotes its document:

* **A type statement.** Genuine's twelve books all print "Transmission
  Type — Continuously Variable (CVT) · Clutch — Dry, Centrifugal"; Kymco's
  print "Transmission … Automatic CVT"; Piaggio's service manuals print
  "automatic expandable pulley variator, torque server, V-belt, automatic
  clutch"; Yamaha's Zuma 125 service manual prints "Transmission type
  V-belt automatic".
* **Variator-specific parts, where no type statement exists.** Honda's
  European books say "the drive belt **and weight rollers**". A final-drive
  belt has no weight rollers, which is what makes this evidence rather than
  a guess.
* **Rejected.** A bare "Drive Belt" line in a maintenance schedule was
  **not** accepted as evidence — it is exactly the ambiguity Phase 254's
  own row 4605 documents, where three unrelated components share the name.
  That decision alone excluded fifteen budget-marque manuals (Lance ×8,
  Roketa ×5, Tank, GTR 50), eleven of which are OCR'd image-only scans.

### The fail-closed cost, measured rather than argued about

Of the **53 model spellings** the Phase 254 rows reach through the model
junction, **40 resolved from a document at merge** and 13 did not. Ten of
those 13 have since been closed — see Deviations — leaving **50 of 53**. The
list as it stood at merge:

> Filly LX 50 · Honda CHF50 · Honda Metropolitan · Piaggio Beverly 250 · Piaggio Beverly Tourer 125 · Piaggio Fly 50 · SYM JET 100 · SYM JET 50 · SYM Joyride · Vespa 946 · Vespa Sprint · XC155 · Zuma 50

Several of those are genuinely CVT machines that will lose the layer. That
is the accepted cost of never guessing, it is attributed by the
withheld-rows counter rather than invisible, and the sourced-coverage phase
is what closes it.

**No live vehicle regresses.** The operator's `vehicles` table holds **10
machines across 6 makes**. **Five** of them are Honda or Yamaha — CB500,
CBR954RR, cbrf4i, MT07, YZF-R1 — and those are the only five that ever
retrieved the CVT layer, because those are the only two of the seven marques
named in the Phase 254 rows. Each of the five correctly *loses* rows it
should never have had. The other five — a Harley-Davidson Road King, a KTM
390, a Kawasaki Ninja ZX-10R and two Suzukis — never retrieved them at all,
for the same reason the Ninja 400 control returns zero.

*(Both "five" and "ten" appear in earlier write-ups of this phase without
saying which is which. Ten is the table; five is the affected subset.)* The exposure is entirely future: whatever a user adds next,
which is why the mobile transmission field moved up to the phase
immediately after 255B.

### Mutations — 26 of 26, after two survivors were fixed

The first run caught 22. Both survivors were real gaps and both are worth
recording, because each was a test that looked like it was checking
something and was not:

* **Alpha/numeric splitting survived.** The test asserted that
  `XMAX250TECHMAX` resolves unknown — true both with and without splitting,
  so it could not tell the two implementations apart. Replaced with two
  discriminating cases (`Sprint49`, `Primavera150`) whose *split* forms are
  real aliases while the concatenations are not, plus an assertion that the
  split form really is an alias, so the test fails loudly if that ever
  stops being true.
* **Removing the migration's backfill survived.** The fixture database is
  built by loading the seed files, and the loader writes `applicability` on
  the way in — so the `post_apply` hook never had to do anything and the
  test was reading the loader's work. Replaced with a test that walks the
  operator's actual path: rows present, column absent, migration applied.
  **This is the piece that repairs the live database, and it was
  untested.**

### Schema pins, and how many it actually took to find them all

**Twelve** pins had to be touched — eleven bumped to 63, one relaxed — and
finding them took five passes. The count matters less than the sequence,
because **every pass looked complete at the time**:

1. The **subsystem-scoped blast radius** found **three**.
2. Running a neighbouring test file found a **fourth**, in a file the blast
   radius had no reason to include.
3. A `grep` found **four more**, one carrying a "NOTE FOR THE NEXT SCHEMA
   BUMP" written after the same pin was missed at Phase 244M.
4. A **ninth** was reachable only because `gate12` runs `gate11` in a
   **subprocess**, so it never appeared in the parent's own failure output.
5. The last **three** came from re-running that grep and **counting its
   hits instead of reading its first screenful** — the first pass had been
   piped through `head` and the truncated list was treated as the whole
   set. That is this phase's own subject, repeated at the end of it: a
   measurement that looks complete because nothing says it isn't.

Phase 244R's pin was the one exception: relaxed from `== 62` to `>= 62`
rather than bumped, because its equality asserted two things at once — that
244R's bump happened, and that nothing had happened since — and only the
first was ever its claim.

### `compose_prompt_rows` was not the only door

Asked late, and it should have been asked first: **which callers retrieve
corpus rows for a specific machine?** That is the question Phase 254 never
asked about its own rows, and asking it here found three doors, not one.

| door | what it does | before | after |
|---|---|---|---|
| `_load_known_issues` — `diagnose`, `code` | composes and caps at 12 | leaking | **filtered** |
| video `/ask` endpoint | hands 25 rows straight to a vision model, no composition at all | leaking | **filtered** |
| `predict_failures` | its own `search_known_issues` retrieval, 50 scored predictions | leaking | **still leaking — F123** |

**The `/ask` leak, measured before it was closed:** a Yamaha MT07 and an
XS650 each received rows **4614** (a CVT recall) and **4606** (variator
roller wear limits). The Hondas missed them at `limit=25` only because
their own rows filled the 25 first — ranking luck, not correctness. Closed
here, because it is the same shape as the diagnose path: rows handed to a
model as context about one machine.

**The predictor leak, measured and left:** a Yamaha MT07 gets **5** of the
254 rows behind its maintenance predictions and a Gold Wing **2**. It is
not fixed in this phase — it is a scored fifty-prediction pipeline with
drift bonuses and its own retrieval, and changing it late, without a plan
and without its own refuter, is how Phase 254's defect got shipped in the
first place. Filed as **F123** with the numbers.

`drop_inapplicable` is public rather than private precisely because of
this: one filter, more than one door.

### The cost of "rejected loudly", found by testing it

The contract says an invalid declaration is rejected loudly at seed load
**and at read**. Implementing that and then exercising it showed what loudly
costs: a single bad value in `known_issues.applicability` raises out of
`_load_known_issues`, which is the retrieval path for the primary diagnose
command *and* for `motodiag code` — three call sites. **One corrupt row stops
diagnosis.**

The trade is kept, because the alternative is worse in the specific way this
phase exists to prevent: dropping the row silently would load
`{"transmision": ["cvt"]}` as unscoped and put it back in front of every Gold
Wing. A typo must not be able to reintroduce the defect.

Two things were changed rather than left: the error now **names the offending
row** by id and title, because a loud failure nobody can act on is not much
better than a quiet one; and the behaviour is **pinned by a test and two
mutations** so it reads as a decision rather than an accident. Filed as
**F122** so the operator can revisit the trade rather than discover it.

### The orphan guard caught three things this phase built and never wired

The full regression's only failure was Phase 209B's integration-gap guard —
F9 subtype 2, and exactly the right guard for a phase about things that do
not reach where they should:

* **`applicability.scoped_rows` was dead**, and its docstring said "Used by
  the counter", which was never true. **Deleted**, rather than allowlisted:
  a helper nobody calls, describing a caller that does not exist, is not a
  gap to record.
* **`withheld_snapshot` and `reset_withheld` have no in-tree caller**, and
  there is a concrete reason they cannot: **the counters live in process
  memory and every CLI command is a fresh process**, so a
  `motodiag … stats` command would print zeros every time. Recorded in the
  209B allowlist as `test-infra` with that reason and a wire-or-retire
  note — the honest caller is an API route on the running server, which is
  a decision this phase did not make.

**So D6 needs stating more precisely than the plan stated it.** The
withheld-rows cost is visible **in the logs** — `record_withheld` fires on
every retrieval that withholds a row and names the provenance. The
**aggregate is not surfaced anywhere a user can see it.** The measurements
in this document were taken by calling the snapshot from a script, which is
exactly what the guard was pointing at.

### Deviations

**There was no section by this name until it was asked for**, which is part of
what it records. The v1.1 had "Non-goals held" — planned exclusions that held —
and nothing recording where the phase departed from what was agreed. Those are
different things, so this section was added and "Non-goals held" left as it is.

**D1. An operator constraint was overridden, and the override shipped.**

The constraint, given during planning: *no current CVT machine loses its rows.*

What shipped does not meet it. Of the 53 model spellings the Phase 254 rows
reach, **13 resolved to unknown at merge** and therefore lost the CVT layer —
including the Ruckus and the Metropolitan, both genuinely CVT machines. The
fail-closed policy was agreed; **this consequence of it was not flagged as
breaking the constraint at the time**, it was written up under "the fail-closed
cost, measured" as though a measured cost were the same as an accepted one. It
is recorded here as a deviation, not only as F119.

**Repaired after merge, and the repair changed the reason.** Almost none of
the 13 were actually unsourceable. **Ten were unsourced because the search was
wrong, not because the documents were silent:**

* Honda prints **"Primary reduction V-matic (2.85:1 ~ 0.86:1)"** in the Ruckus
  and Metropolitan specification tables. The first sweep searched for *belt*,
  *drive belt*, *weight roller*, *CVT* and *transmission* — never for Honda's
  own word. That closed Ruckus, Metropolitan, CHF50, and with the same
  corrected vocabulary, Piaggio Fly 50 and Beverly Tourer 125.
* Five more were **alias gaps against documents already on disk**: SYM JET
  50/100 (service manual 7326249), SYM Joyride (7429958), Vespa Sprint — whose
  aliases this phase *removed* as unsourced without reading the Primavera
  manual's cover, which names it — and Zuma 50 (four Yamaha owner's manuals).

**Three remain**, and they are now honestly characterised rather than lumped
together: **Piaggio Beverly 250** and **Vespa 946** have no document at all,
and **Filly LX 50** has a document whose attribution Phase 254 showed to be
unestablished.

**Coverage: 50 of 53 spellings resolve, up from 40 at merge.**

The deviation still stands, and is worth stating exactly: **the phase traded
coverage for correctness without saying it was trading against a stated
constraint** — and most of what it traded away it did not have to, because the
coverage was there to be found and the search was at fault. A fail-closed
policy is only honest about its cost if the cost has actually been measured
against the evidence available, not against the evidence that one query
happened to reach.

**D2. Scope grew during the build, once.** The video `/ask` endpoint fix was
not in the plan. It was the right fix — the same defect on another door — but
it entered as part of the build commit rather than as a scoped change with its
own commit, and it is recorded as Bug fix #1 in the phase log after the fact.

### Known limits, accepted and recorded

1. **Large maxi-scooters lose friction-plate content.** The Yamaha TMAX and
   Suzuki Burgman 650 run a wet multiplate clutch *alongside* a CVT.
   Declared `{cvt}`, they will not receive friction-plate rows that
   genuinely apply. Missing, not misleading — the trade D4 already makes.
2. **Rows 4611 and 4615 ship as `{cvt}`** although each carries a general
   half wider than CVT (kickstart backup; the regulator-index methodology).
   Splitting them belongs to 255B and is named in its plan.
3. **Honda E-Clutch is `manual`**, and actuator-specific rows, if ever
   written, are model-scoped rather than a seventh enum value.
4. **XC155 / SMAX is not asserted.** What is sourced is the negative:
   Yamaha's XMAX codes are YP125RA, CZD250-A and CZD300-A, read off three
   owner's-manual covers, so XC155 is **not** an XMAX. Whether it is the
   SMAX remains unsourced.
5. **Piaggio calls a CVT "direct drive."** The Primavera/S 150 owner's
   manual reads "fitted with direct drive automatic transmission" and
   contains zero occurrences of "variator". A documentation hazard, not a
   runtime one, because nothing in the code reads document text.

### Non-goals held

No content row (255B). No mobile field (the phase after 255B). No general
applicability mechanism. No fix for the XS650 cooling over-reach, the
`manual` substring collision, or row 4605's make column — each has its own
finding. **No change to 250B**, pinned by a test. No row declares `manual`,
pinned by a test across every seed file. No keyword matching in seed or at
runtime.
