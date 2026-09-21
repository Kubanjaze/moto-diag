# Phase 252 — Honda's small machines: the four the corpus never named

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-20

---

## Goal

Row 252: "Honda Ruckus / Grom / Metropolitan / PCX — cult-favorite small
Hondas, Grom 125 modding community, Ruckus/Metro 50cc scooters." Written
under the rule Track L kept and Track M opened on: every entry is anchored
to a manufacturer document named in the description, or it is not written;
every number carries its label; one row, one label; a regulator record on
its own row; a community source dated; a mirrored document named as
mirrored.

## Step 0 — findings

Measured against the live database (1006 rows) on 2026-09-20.

**S0-1. The subject is empty — and the obvious check says it is not.** No
row names the Ruckus, the Metropolitan, the PCX, the Monkey, the Super Cub
or the Trail 125. A `LIKE '%Grom%'` search returns **four rows**, and all
four are the word **grommet** — a Honda CBR1000RR stator row, a CBR900RR
fairing row, an all-Honda stator row and a VFR800 windscreen row. The
search that would have reported the Grom as covered is a substring
collision. Nothing mentions the Ruckus or the PCX at all.

**S0-2. Honda is the corpus's third-largest marque and not one of its rows
is anchored.** 142 Honda rows, **all 142 `source: unverified`** — twelve
seed files (`cbr1000rr`, `cbr600f`, `cbr600rr`, `cbr_supersport`,
`cross_model`, `cruisers`, `dualsport`, `electrical`, `rebel`,
`standards`, `v4`, `vintage`), every one of them from the pre-242 legacy
seed. Corpus-wide the split is 660 unverified, 164 service-manual, 149
model-generated, 27 forum, 6 regulation. So 252 writes the **first
anchored Honda content in the corpus**, and it must not lean on the 142
rows beside it for anything, because none of them names a document.

**S0-3. Every small Honda is unresolved today, and the number is
measurable.** Honda's model pool is 27 entries and every one is 250 cm3 or
larger: Africa Twin, CB750, CBR1000RR, GL1800 Gold Wing, Rebel 1100,
Shadow 750, VFR800, VTX1800, XR650L and so on. Through `resolve_vehicle`
against the live database, **Grom, Grom 125, Ruckus, PCX150, PCX 150,
Metropolitan, Monkey 125, Super Cub C125 and Trail 125 all resolve to
`unresolved`** and fall back to 20 make-wide hits, where a CBR1000RR
resolves exact and returns 31. That is the before-state this phase moves.

**S0-4. 250C's control-group pin sits directly in the blast radius.**
`tests/test_phase250C_model_vocabulary.py` holds `UNCHANGED = {"Honda":
27, ...}` and asserts **equality** — Honda, Kawasaki, Suzuki and Yamaha
write one marque per row, so raw-key and marque-key are the same thing for
them, and the test proves the derivation changed nothing it had no
business changing. Adding Honda rows moves that number for a reason that
has nothing to do with the derivation. The pin is updated in the same
commit with the reason written into it, exactly as 250C updated
`test_phase245_damon_absence.py`. `BEFORE` is a `>=` floor and needs no
change. **This is recorded in Step 0 rather than discovered by the
regression**, which is where 250C found its equivalent.

**S0-5. No adapter row, no fault-code file.** `compat_matrix.json` holds
13 Honda entries and every model pattern is `CBR%`, `VFR%`, `shadow%`,
`gold wing`, or a bare `%` — nothing small. `seed/dtc_codes/` holds eight
files (aprilia, bmw, ducati, generic, harley_davidson, ktm, mv_agusta,
triumph) and **no honda.json at all**. Both are absences to record, not to
fill.

**S0-6. The row's boundaries are other rows in this track.** 253 is
"Yamaha Zuma / Vino + Kymco / SYM / Genuine", 254 is "Small-displacement
CVT diagnostics", 256 is "Scooter electrical (12V minimal)", 257 is
"Small-engine carb service". So the generic CVT layer, the generic scooter
electrical layer and carburettor service are **not** 252's, exactly as
they were not 251's. 252 is the machines.

**S0-7. The count moves.** README, the quickstart, the install guide and
the launch checklist all state 1006 and move together (Phase 208's guard).

**S0-8. Schema version is 62 and stays there.** No migration, no new
table, no new column.

## Decisions

**D1. Anchored or not written.** Every statement names the document it came
from — owner's manual with its Honda part number, service manual, a
service bulletin, a parts catalogue, or a regulator record with its
campaign number. A claim whose page the refuter cannot fetch is not
`service-manual`; it is downgraded or dropped.

**D2. One row, one label**, and a forum row names its site and the page's
own date. 246's rule, kept.

**D3. The four named machines are the row; the miniMOTO siblings ride only
where a document carries them together.** The roadmap names the Ruckus,
the Grom, the Metropolitan and the PCX. The Monkey 125, Super Cub C125 and
Trail 125 share the Grom's engine family, and Honda's own service
literature sometimes covers them in one book. Where a fetched document
covers them together, the row says so and names the document; where it
does not, they are not written. **No sibling is added because it is
plausible that it shares.**

**D4. Honda's 142 unverified rows are not evidence.** Nothing in this
phase may cite, restate or lean on an existing Honda row. If an anchored
document contradicts one, that is a finding to file, not a row to rewrite
here.

**D5. What the machines do not have is content.** If Honda publishes no
valve-clearance figure, no belt-width limit or no fault-code list for a
model, the row says so rather than borrowing one from a forum and
labelling it manual.

**D6. A mirrored document is named as mirrored.** Honda's owner's manual
channel and Helm's service-manual channel may both refuse non-browser
clients. Phase 246's rule stands: a `service-manual` row names the
document by its Honda part number **and** says it was read from a mirror
copy. What a row may never do is imply the statement came off a Honda
server.

**D7. The regulator record is a floor, not a census.** F103, filed by 251:
`api.nhtsa.gov` 403s a default User-Agent, and a client that maps a 4xx to
an empty result cannot tell "no recalls" from "I was blocked". Any
regulation row here states the campaigns it names as a floor, and its test
forbids a completeness claim. The repo's `recalls.json` is a 30-row static
fixture, not a source.

**D8. The modding community is a documented subject, not a licence.** The
roadmap row names the Grom's modding community. A community claim is a
`forum` row with a site and a page date, or it is not written — and the
distinction the machines actually turn on is what Honda's own documents
say about a modified machine, which is anchored.

## Scope

1. `known_issues_honda_small.json` — the machines: what distinguishes each
   model generation, what Honda publishes for service, how the machine is
   read by a tool if it is, the regulator record, and a dated community row
   only where a community number is the only number.
2. A content test in 251's shape: every row anchored, every number
   labelled, no restatement of the generic layers 254/256/257 will own, and
   the four machines reachable through the model junction after the load.
3. `tests/test_phase250C_model_vocabulary.py` — the `UNCHANGED` Honda pin,
   moved with its reason (S0-4).
4. The four user-facing docs' count, moved together.

## Non-goals

- **No generic CVT, scooter-electrical or carburettor layer** — rows 254,
  256, 257.
- **No other make** — row 253 has Yamaha, Kymco, SYM and Genuine.
- No `dtc_codes` seeding, no adapter compatibility rows (S0-5).
- No schema change, no migration.
- No rewrite of Honda's 142 unverified rows (D4).
- Nothing from memory: no interval, torque or capacity that a fetched page
  does not state.

## Results (v1.1)

**Shipped:** `known_issues_honda_small.json`, thirteen rows — nine
`service-manual`, four `regulation`, none `model-generated` and none
`unverified`. Corpus 1006 → 1019. Honda's model pool **27 → 46**.

- 93 tests, 15 mutations.
- Full regression **7,560 passed, 0 failed, 31:28**.

### The rows

Three carry what the corpus had no equivalent of. **Honda's two 50 cm3
scooters are opposite machines**: the Ruckus is still carburetted for model
year 2025 — "no adjustment should be made except idle speed adjustment"
(31GJP610 p.85), with a "High Altitude Carburetor Adjustment" section at
p.89, and PGM-FI and fuel injection returning zero hits across all four
Ruckus manuals — while the Metropolitan is injected, with a malfunction
indicator lamp in all five of its manuals and zero hits for carburetor.
They share no plug, no JASO oil grade, no tyre pressure, no fuse and no
battery. **In model year 2022 the Grom and the Trail 125 ran different
engines**, 50.0 x 63.1 mm at 10.0:1 against 52.4 x 57.9 mm at 9.3:1, and
the only obtainable service manual describes the pre-2022 four-speed Grom,
so no figure inherits forward. And **a Grom fault above 1800 rpm shows as a
steady lamp rather than a blink code**, with a 0.3-second pre-flash marking
a stored code — so a technician revving the engine while watching the lamp
concludes there is none.

Honda's GROM125 fault-code index holds **exactly eleven codes**, and prints
one pair — 9-1 and 9-2 — inverted against every other pair in the table.
The page was rendered at seven and fourteen times magnification to settle
it: the words are unambiguous, so it is Honda's erratum and not a reading
artifact, and the row ships it as such.

The regulation rows carry the Grom fuel-pump supersession as the thing that
distinguishes it from the corpus's two existing repeat-campaign rows — not
a remedy that failed in service, and not a second defect found later, but a
first remedy only partly effective, so that **a completed recall is not
proof of a repaired machine**; the Metropolitan transmission campaign with
the rider-facing sentence that exists only in the manufacturer's filing;
the reflector campaign as an FMVSS 108 compliance failure whose model-year
coverage is not uniform; and the record itself as a floor.

### What the refuters changed — an inference, not a figure

Three sweeps, working independently, all concluded that the regulator's
per-vehicle lookup returns HTTP 400 when it does not recognise a model
string. It is a tidy explanation, it fits every observation, and it is
wrong. The refuter ran the control none of the three had run — one model
string across several model years:

| query | status |
|---|---|
| `GROM125` 2014 / 2015 / 2020 | 200, real campaigns |
| `GROM125` 2013 / 2016 / 2019 / 2021 / 2023 | **400**, empty |
| `grom` (a name it cannot resolve) 2020 | **400**, empty |

**A 400 means zero results.** A wrong model name and a genuine no-recall
year are identical at every layer, so nothing in the response validates a
model string. Two further claims fell with it: the endpoint that looked
like a recall index takes an **inert parameter** — a garbage value returns
byte-identical lists — and the "hidden Ruckus recall" that had blocked the
Ruckus rows was a **complaint**, ODI 10883289. The blocker dissolved.

The rest of the layer behaved as it has since 246:

| The sentence | Why it died |
|---|---|
| the Ruckus primary reduction is printed two ways, "2.8:1 ~" and "2.85:1 -" | the hyphen form is the **Metropolitan's**; all four Ruckus manuals use the tilde. The real disagreement is 2.8 against 2.85 |
| the oil spec changed once, SG to SJ | two changes — "or resource conserving" arrived in 2022, SJ in 2024 |
| the Ruckus gives no coolant calendar interval | it gives two years, in footnote 4, against the Metropolitan's three |
| the CHF50 manual's filename contradicts its edition line | "2002-2006" is printed on Honda's own cover; a 2007 issue date is an ordinary reprint |
| the Grom service manual names itself nowhere | it names itself once — "the service procedures for the GROM125" — and says MSX nowhere in 266 pages |
| the PCX plug changed from CPR7EA-9 to LMAR8L-9 | there is a third, MR8K-9 for 2020; the two-way version mis-serves every 2020–2021 machine |
| the reflector campaign covers 2020–2021 | not uniform: a Grom is covered for 2020 only |
| the transmission-oil row and the campaign | a documented sequence of dates; no document states a connection and none is asserted |

### Side finding — the machines were never uncovered

`known_issues` id 261 is `unverified`, its model column is the wildcard, and
it therefore reaches every Honda from 2001 to 2025 with a ten-entry blink-code
table. Honda's own GROM125 index contradicts it on four codes — 7 is engine
oil temperature not TPS, 8 is throttle position not intake air, 9 is intake
air not coolant, 33 is EEPROM not fuel pump — and three more of its codes do
not exist on the machine at all. Its clearing procedure is not Honda's, and
its `fix_procedure` contains a sentence beginning "Forum tip:". Filed as F106.

### Deviations

**D3 was exercised, and the siblings earned less than expected.** The plan
said the miniMOTO siblings ride only where a fetched document covers them
with the Grom. No service document does: the only cross-model statement
obtained is a Honda press release about the Monkey's engine. So the
siblings appear in the model columns and in the engine-comparison row, and
carry no service figures of their own.

**A row was nearly dropped, and D8 caught it.** The first draft had no
modification row, which would have silently narrowed the roadmap row's own
scope. The anchored material exists — four acts named under the noise
emission control system — and it is written, scoped as the refuter
corrected it rather than as the sweep reported it.

### Verification

- Thirteen rows, every one anchored to a document named in its description;
  mirror provenance stated for the GROM125 manual and the CHF50 manual, and
  Honda's own CDN named where the document came off it.
- All fourteen machines resolve exact — Ruckus, NPS50, Metropolitan, NCW50,
  Giorno, CHF50, Grom, GROM125, PCX, PCX150, Monkey 125, Super Cub C125,
  Trail 125, CT125 — where before the phase every one of them resolved to
  nothing.
- The 250C control-group pin moved 27 → 46 with its reason written in, as
  Step 0 said it would (S0-4).
- 15 mutations, all caught. Two guards were too blunt on their first run —
  one banned a phrase that appears inside its own prohibition, the other
  selected rows on a string that also matches a regulator component field —
  and both were rewritten to test the property.

## Verification Checklist

- [x] Every row anchored to a named document, or dropped
- [x] Every number labelled; no number without a fetched source
- [x] No row restates a generic layer 254/256/257 will own
- [x] Ruckus, Grom, Metropolitan and PCX resolve as Honda models after the load
- [x] The new test file scanned by 244G's raw-source guard
- [x] Mutations caught — 15/15
- [x] Full regression green — **7,560 passed, 0 failed, 31:28**, 0 skipped
- [x] Live DB loaded copy-first, before-state printed; count docs moved
- [x] Roadmap row, `implementation.md` history row, `phase_log.md`
