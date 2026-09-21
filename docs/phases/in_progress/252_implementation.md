# Phase 252 — Honda's small machines: the four the corpus never named

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-20

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

## Verification Checklist

- [ ] Every row anchored to a named document, or dropped
- [ ] Every number labelled; no number without a fetched source
- [ ] No row restates a generic layer 254/256/257 will own
- [ ] Ruckus, Grom, Metropolitan and PCX resolve as Honda models after the load
- [ ] The new test file scanned by 244G's raw-source guard
- [ ] Mutations caught
- [ ] Full regression green — 0 failed, 0 skipped
- [ ] Live DB loaded copy-first, before-state printed; count docs moved
- [ ] Roadmap row, `implementation.md` history row, `phase_log.md`
