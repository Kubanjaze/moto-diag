# Phase 253 — Yamaha's scooters and the Taiwanese makers

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-20

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

## Verification Checklist

- [ ] Every row anchored to a named document, or dropped
- [ ] Every number labelled; no number without a fetched source
- [ ] No row restates Phase 252 or a generic layer 254/256/257 will own
- [ ] Kymco, SYM and Genuine resolve as marques, with their models, after the load
- [ ] Zuma, Vino and BWS resolve as Yamaha models
- [ ] The new test file scanned by 244G's raw-source guard
- [ ] Mutations caught
- [ ] Full regression green — 0 failed, 0 skipped
- [ ] Live DB loaded copy-first, before-state printed; count docs moved
- [ ] Roadmap row, `implementation.md` history row, `phase_log.md`
