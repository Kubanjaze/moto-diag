# Phase 253 — Yamaha's scooters and the Taiwanese makers

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-21

---

## Goal

Row 253: "Yamaha Zuma / Vino + Kymco / SYM / Genuine — budget scooters,
Taiwanese manufacturers, parts availability." Written under the rule Track
L kept and Track M has followed: every entry anchored to a manufacturer
document named in the description, or not written; every number carries its
label; one row, one label; a regulator record on its own row and as a
floor; a community source dated; a mirrored document named as mirrored.

## Step 0 — findings

Measured against the live database (1019 rows) on 2026-09-20.

**S0-1. The subject is empty, and three separate checks say otherwise.**
Zero rows name the Zuma, the Vino, the BWS, the Roughhouse, the Agility or
Taiwan. But `LIKE '%SYM%'` returns **117 rows** — every one of them
*symptom* or *system* — `LIKE '%Genuine%'` returns **60**, every one of
them *genuine part* or *genuine Honda*, and `LIKE '%Buddy%'` returns five,
none of them the scooter. This is the second phase running where the naive
substring check claims the subject is covered: 252's was *grommet*. Here
there are three of them, and two of the three marque names are ordinary
English words.

**S0-2. Yamaha is the corpus's fifth-largest marque and not one of its rows
is anchored.** 111 rows, **all 111 `source: unverified`**, across ten seed
files (`crossmodel`, `cruisers`, `dualsport`, `electrical`, `fz_mt`, `r1`,
`r6`, `r7_thundercat`, `vintage`, `vmax`). Its model pool is 23 entries and
every one is a motorcycle — Bolt, FZ6, MT-09, RD350, V-Star, VMAX, XS650,
YZF-R1. No scooter of any kind. This is exactly 252's situation one marque
over, and the same decision follows: those 111 rows are not evidence.

**S0-3. Kymco, SYM and Genuine are not marques here.** The junction holds
eighteen marques and none of the three. They would be the first Taiwanese
manufacturers in the corpus, and Genuine the first US assembler-importer.

**S0-4. The marque names are safe — measured on a copy, not assumed.**
Two of the three collide with ordinary corpus prose, so before writing
anything a probe loaded makes literally named `SYM` and `Genuine` into a
copy of the live database. Result: **`resolve_vehicle("system")` and
`resolve_vehicle("symptom")` both stay unresolved** — marque matching is
not substring-based — while `SYM`, `Genuine` and `Kymco` all resolve
exact, their models resolve exact, `pragma integrity_check` returns `ok`,
and no existing retrieval moved except Yamaha's make-wide count rising by
the single probe row that carried its name. The risk this phase was most
exposed to does not materialise, and that is now evidence rather than
hope. One true ambiguity remains and is not a defect: a rider typing
`genuine` as a make gets the Genuine Scooter Company, which is correct.

**S0-5. No adapter, no fault-code file.** `compat_matrix.json` covers
eleven makes and none of these three; `seed/dtc_codes/` holds eight files
and **none for Yamaha at all**. Absences to record, not to fill.

**S0-6. The row's boundaries are three later rows and one that just
closed.** 254 is "Small-displacement CVT diagnostics", 256 "Scooter
electrical (12V minimal)", 257 "Small-engine carb service" — so the generic
layers are not 253's, exactly as they were not 251's or 252's. And **252
closed hours ago on adjacent machines**: the same class, the same
regulator, the same document-access problems. Its rows are referenced and
never restated, which is a heavier burden here than in any previous row of
this track. The same applies to "parts availability", which the roadmap row
names: Track K already wrote the Piaggio Group's shared catalogue and
supersession chain, and KTM's Bajaj sourcing. 253 writes what *these*
makers' documents say, or writes the absence.

**S0-7. The count moves.** README, the quickstart, the install guide and
the launch checklist all state 1019 and move together (Phase 208's guard).

**S0-8. Schema version is 62 and stays there.** No migration, no new table,
no new column.

**S0-9. Side finding, found while probing — the model vocabulary holds 32
entries that are not models.** `resolve_vehicle("SYM", "Mio")` came back
`ambiguous` against alternatives including `2017 campaign population`,
`cast-aluminium Front Frame` and `maxi-scooter`. Measured across the
vocabulary: **21 descriptive phrases** (`one per make`, `approximately 2016
to 2020`, `as this corpus names them`, `S 1000 RR by type code`,
`Piaggio Group marques only`) and **11 components or traits** (`wet slipper
clutch`, `nylon fuel tank`, `in-tank pump flange`, `camhead boxers`,
`air-cooled 2V Desmodue`) are resolvable as models, because some rows use
the model column as a description field. Filed, not fixed here — 253 is a
content row.

## Decisions

**D1. Anchored or not written.** Every statement names the document it came
from. A claim whose page the refuter cannot fetch is not `service-manual`;
it is downgraded or dropped.

**D2. One row, one label**, and a forum row names its site and the page's
own date. 246's rule, kept.

**D3. The make column names the marque plainly.** 250C keys the model
vocabulary by derived marque, so three new marques resolve their models the
day the rows land — provided the make column says `Kymco`, `SYM` or
`Genuine` and not a sentence.

**D4. Yamaha's 111 unverified rows are not evidence.** Nothing here may
cite, restate or lean on them. A contradiction is a finding to file, not a
row to rewrite.

**D5. What these machines do not have is content**, stated against named
documents rather than as a general negative.

**D6. A mirrored document is named as mirrored**, by its own edition line
or part number where it prints one, and by what it self-declares where it
does not — the provenance question 252 had to settle for the GROM125 book.

**D7. Parts availability is written from documents or not written.** The
roadmap row names it and it is the subject most likely to attract folklore:
what a dealer network stocks, what is rebadged from whom, what is still
supported. A claim about rebadging needs a document that says so, not a
resemblance.

**D8. 252 is referenced, never restated.** Its Honda rows, its regulator
findings and its access notes are shipped content. A 253 row that needs one
names it and points.

**D9. The regulator record is a floor.** And the reading 252 corrected
binds here: an HTTP 400 from the per-vehicle lookup means zero results, not
an unrecognised model string, so nothing in a response validates a name.

## Scope

1. `known_issues_yamaha_kymco_sym_genuine.json` — the machines: what
   Yamaha publishes for the Zuma and Vino, what Kymco, SYM and Genuine
   publish for theirs, who actually builds what, the regulator record, and
   parts availability where a document speaks to it.
2. A content test in 252's shape: every row anchored, every number
   labelled, no restatement of 252 or of the generic layers, and the three
   new marques reachable through the junction 250C keys by marque.
3. The four user-facing docs' count, moved together.

## Non-goals

- **No generic CVT, scooter-electrical or carburettor layer** — 254, 256, 257.
- **No restatement of Phase 252's Honda rows** or of Track K's parts rows.
- No `dtc_codes` seeding, no adapter compatibility rows (S0-5).
- No schema change, no migration.
- No rewrite of Yamaha's 111 unverified rows (D4).
- **No fix for S0-9's vocabulary junk** — filed, and out of scope for a
  content row.
- Nothing from memory: no interval, torque or capacity that a fetched page
  does not state.

## Results (v1.1)

**Shipped:** `known_issues_yamaha_kymco_sym_genuine.json`, fourteen rows —
nine `service-manual`, five `regulation`, none `model-generated` and none
`unverified`. Corpus 1019 → 1033. **Three new marques**, and Yamaha's model
pool **23 → 46**.

- 105 tests, 20 mutations.
- Full regression **7,665 passed, 0 failed, 36:56**.

### The rows

Three carry what the corpus had no equivalent of. **One nameplate covers
three engines**: the Zuma 50 is an air-cooled two-stroke with autolube and
no sump to drain through model year 2011, the Zuma 50F a liquid-cooled
injected four-stroke from 2012, and the Zuma 125 air-cooled through 2021
then liquid-cooled with variable valve actuation — while the **Vino splits
the other way**, its 50 liquid-cooled and carburetted where its 125 of the
same era is air-cooled. The figure that does damage is the spark-plug
torque: **20 N·m on the two-stroke against 13 N·m on the four-stroke**.

**Yamaha prints one interval three ways.** The same 18,000 km Zuma 125
V-belt replacement appears as "Every 1200 mi", "Every 18000 km (12000 mi)"
and "Every 11000 mi" across three documents — the 2009 owner's manual short
by roughly a factor of nine, and the same misprint in the Vino 125 book.
Beneath it sits a wider defect: a 4,000 mile interval given as 7,000 km and
then 6,000 km in one sentence, in **twelve of fifteen manuals spanning 2006
to 2022**. That is a house style, not a slip.

**Who builds a Genuine scooter is a chain, not a sentence.** A VIN prefix
registered to a Taiwanese manufacturer trading as PGO, a regulator
manufacturer record carrying both names, and unerased "SHOULD BE DONE BY
YOUR PGO DEALER" text in three current manuals — reported as a chain,
because no reachable document contains the declaration, and shipped with
the three counterweights that cut against it.

### What the refuters changed — one headline per sweep

| The sentence | Why it died |
|---|---|
| "Zuma and BWS appear in none of the fourteen documents" | *Zuma* is on two covers, and the sweep had cited one of those documents under its own belt claim. Naming is **year-dependent**, not absent |
| "XC50 is the Vino 50 is unanchored folklore" | the 2007 Vino 50 manual carries `XC50W` on its cover and `VINO` on page 5 — **the campaign's own model year** |
| "SYM's entire Honda statement is one clause, no dates, no models" | SYM's **US** host gives 1962, "joint venture", and two named cars. The sweep scoped to the corporate parent |
| "no fault codes across 21 Kymco and SYM manuals" | they exist under the makers' own words — *Fi error code indicator*, *Engine Warning Indicator*, *EFi Trouble Indicator*, *Fault indicator light* |
| that scoped zero | one of the 21 files has **no text on 47 of its 57 pages**; its zeros were never evidence |
| "JASO appears nowhere" | Kymco-only; it appears once, in SYM's Wolf CR300i |
| "the Rattler 50 takes a wider plug gap than the Buddy 50" | the Rattler's own manual prints both gaps — a defect, not a difference |
| "campaign 04V381000 covers the Super-9" | it covers the **Vitality** too, in both years |
| "one of the two NIU campaigns is a do-not-ride" | **both** are; only one also lacks a remedy |
| "the Super 8 50 name collision is a site-labelling defect" | Kymco's site labels the 50X and 50R correctly; the collision is inside the documents |
| "the People S manual describes no injection" | it describes **secondary air** injection; only fuel injection is absent |

Each is a test and a mutation.

### The safety question Step 0 asked first

Two of the three new marque names are ordinary English words — `SYM` sits
inside 397 corpus rows as *symptom* or *system*, `Genuine` inside 60 as
*genuine part*. Before any row was written, a probe loaded makes literally
named `SYM` and `Genuine` into a copy of the live database:
`resolve_vehicle("system")` and `("symptom")` both stayed **unresolved**,
marque matching is not substring-based, all three resolved exact,
`integrity_check` returned `ok`, and no existing retrieval moved except
Yamaha's make-wide count rising by the one probe row carrying its name.
The same check now runs against the shipped rows.

### Deviations

**The roadmap row's "parts availability" got a thinner answer than hoped,
and that is the answer.** Kymco makes quantified claims — parts stocked in
US warehouses, over 500 dealers — but states no support duration for a
discontinued model. SYM makes no parts claim at all; its discontinued-models
page lists eleven machines and says nothing about parts for any of them.
Genuine gates parts manuals behind a dealer login. The row records what each
maker does and does not commit to, rather than inventing a comparison.

**Two guards were too blunt on their first run, and one contradicted a
sibling test twelve lines away.** Both were rewritten to test the claim,
scoped to a sentence. This is the third consecutive phase in which a
token-ban guard fired on the honest row that names an error in order to
disclaim it, so it is now written down as a memory rather than relearned.

### Verification

- Fourteen rows, every one anchored to a document named in its description;
  Yamaha's own library named where the document came off it, mirrors named
  where they did not.
- All sixteen machines resolve exact — Zuma, Zuma 125, Vino, Vino 50, XC50A,
  GQX125N, Agility, Like 150i, Vitality, Symba, Mio 50, Wolf CR300i, Buddy,
  Buddy Kick, Roughhouse 50, Stella.
- `system`, `symptom` and `genuine part` still resolve to nothing after the
  load.
- The 250C control-group pin moved 23 → 46 for Yamaha with its reason, as
  Step 0 said it would.
- 20 mutations, all caught.

## Verification Checklist

- [x] Every row anchored to a named document, or dropped
- [x] Every number labelled; no number without a fetched source
- [x] No row restates Phase 252 or a generic layer 254/256/257 will own
- [x] Kymco, SYM and Genuine resolve as marques, with their models, after the load
- [x] Zuma, Vino and BWS resolve as Yamaha models
- [x] The new test file scanned by 244G's raw-source guard
- [x] Mutations caught — 20/20
- [x] Full regression green — **7,665 passed, 0 failed, 36:56**, 0 skipped
- [x] Live DB loaded copy-first, before-state printed; count docs moved
- [x] Roadmap row, `implementation.md` history row, `phase_log.md`
