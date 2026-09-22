# Applicability axes — what a corpus row is about, and what a machine has

**Status:** accepted · **Phase:** 255 · **Date:** 2026-09-21

## The problem, as measured

Phase 254 wrote twelve rows about small-displacement scooter CVTs. Each row
is anchored to a manufacturer document, each carries one provenance label,
and the file passed 85 of its own tests, 22 of 22 mutations, a 986-test
blast radius and a 7,750-test regression. Nothing about the rows is wrong.

Measured against the live database the day after it merged:

| machine | Phase 254 rows retrieved |
|---|---|
| Honda GL1800 Gold Wing | 9 |
| Honda CBR1000RR | 9 |
| Honda Grom | 9 |
| Yamaha YZF-R1 | 10 |
| Yamaha XS650 | 10 |
| Honda PCX 150 *(the intended target)* | 9 |
| **Kawasaki Ninja 400** | **0** |

Kawasaki's zero isolates the cause. The rows carry `make = "Piaggio, Vespa,
Honda, Yamaha, Kymco, SYM, Genuine"`, so any Honda or Yamaha matches at the
make-wide tier and Kawasaki does not. It is the make column doing this, not
the content. **Every test asked whether the rows were right. None asked
which machines would receive them.**

`known_issues` had no way to say what a row is *about*, and `vehicles` had
no way to say what a machine *has*. This ADR adds both.

## Decision

**A row declares the values it applies to, per axis, by hand.**
`known_issues.applicability` is a JSON object keyed by axis —
`{"transmission": ["cvt"]}`. An absent key means unscoped on that axis,
which is what every row written before Phase 255 is. Adding cooling or
final drive later is a new key, not a migration, and the extra cost over a
`transmission_applicability` column is small because the filtering happens
in Python rather than SQL.

**A machine carries a typed column per axis.** `vehicles.transmission` has
its own CHECK constraint, exactly as `powertrain` does. It is nullable with
no default, and that is a deliberate divergence from `powertrain`, which
defaults to `ice`: a machine whose transmission nobody recorded has an
unknown transmission, and writing `manual` would be a fabrication that
retrieval would then act on.

**The resolver returns a candidate set, not a value.** `make/model/year`
genuinely cannot separate a manual Africa Twin from a DCT Africa Twin —
Honda sells both in the same model year — so a resolver returning one value
would have to invent it. Four rungs, first answer wins: explicit column →
model lookup → powertrain default → unknown. Each answer carries its
provenance: `explicit`, `model-sourced`, `powertrain-default`, `ambiguous`,
`unknown`.

**The inclusion rule is coverage, and it fails closed.** A scoped row is
included only if its declared set covers *every* candidate. An unknown
machine has all six transmissions as candidates, so only a row declaring
all six passes — which is the same as being unscoped.

The consequence is worth stating plainly, because it is the opposite of
what one expects from a lookup table: **the Gold Wing is fixed by the
absence of an entry, not by the presence of one.** The lookup exists to
*preserve* retrieval for the machines that should keep it. Every machine
missing from it loses scoped rows automatically.

**Never misleading, sometimes missing.** A Gold Wing told about variator
rollers is a wrong answer; a PCX missing one row is an incomplete one.
Those are not the same kind of failure, and this axis prefers the second.

## Why this diverges from Phase 250B, which is not touched

250B filters the prompt by powertrain and looks superficially like the
thing to copy. It is not, for two independent reasons, both read from the
code rather than assumed.

**It reorders; it does not exclude.** `_electric_first` returns
`electric + [everything else]` and nothing is removed. That is right for
its problem — an electric machine that also sees a generic row has lost
nothing. It is wrong for this one: moving a variator row to position twelve
does not make it true of a Gold Wing.

**It infers the row's powertrain from the marque names in its `make`
column**, and `is_electric_row` is documented as *"deliberately generous: a
row naming four marques of which one is electric IS about an electric
machine."* That generosity is precisely the mechanism that produced the 254
defect, because Honda and Yamaha build both scooters and motorcycles.

So 255 diverges on both points and **250B itself is unchanged**. Marque
inference is recorded here as a known weaker pattern, not as a precedent to
follow.

## No keyword matching, anywhere

Not in seed authoring, not at load, not at read. Rows are declared by id
with a written reason; machines are classified from a table sourced to
manufacturer documents. Nothing in the code ever looks at row text to
decide applicability.

Model matching is make-scoped, normalised, and whole-token against an
**explicit alias list**. No fuzzy matching, no alpha/numeric splitting, no
substring matching. The reason is concrete: **Like, Fly, Jet, Kick, Wolf
and Buddy are all real model names and all are ordinary words.** Substring
matching would make every one of them a hazard.

## Two things the documents taught us

**A name search does not prove absence.** Phase 254 concluded that no
corpus row says "SMAX" and treated `XC155` as a separate matter. They may
well be one machine; the equivalence could not be sourced and is not
asserted. What follows instead is structural: every lookup entry carries an
explicit alias list pairing model code with marketing name, sourced where
possible — the Yamaha Zuma 125 service manual cover reads `Model : YW125Y`,
and that is where its alias comes from.

**A manufacturer uses one of this enum's value names to mean something
else.** The Vespa Primavera/S 150 owner's manual states *"The vehicle is
fitted with direct drive automatic transmission"* — a CVT scooter, where
Piaggio's "direct drive" means no intermediate gearbox, not this axis's
`direct_drive` value of "no gearbox and no clutch". The same manual
contains zero occurrences of "variator". This is a documentation hazard and
not a runtime one, precisely because nothing in the code reads document
text; it is recorded so the next author does not resolve it the wrong way.

## The limit this carries, stated rather than discovered later

A JSON column has **no CHECK constraint**, so the Phase 195C schema lint
does not cover `applicability` the way it covers `known_issues.source`. The
pydantic model in `knowledge/applicability.py` is the only guard there is,
which makes it load-bearing. It uses `Literal` axis keys and `Literal`
values, forbids unknown keys, validates at seed load and again at read, and
rejects an unknown key or value loudly rather than dropping either — a typo
like `{"transmision": ["cvt"]}` must not load as unscoped and quietly
reintroduce the 254 defect. An empty list is a validation error, never
"applies to nothing" and never "applies to everything", because a slip that
could silently mean either of two opposite things must fail.

**What "loudly" costs, measured rather than assumed.** Validating at read
means one corrupt value raises out of `_load_known_issues`, which serves
both `motodiag diagnose` and `motodiag code` — so a single bad row stops
diagnosis. The trade is kept: dropping the row silently would load a typo
as unscoped and put it straight back in front of every Gold Wing, which is
this ADR's whole subject. The error names the offending row by id and
title, and the behaviour is pinned by a test rather than left implicit.

## Sequencing

**Phase 255 ships the mechanism plus `cvt` scoping only.** No shipped row
declares `manual`, and a test enforces it across every seed file. The
reason is measured rather than stylistic: a clutch-cable row declared
`{manual}` would be withheld from every CBR and Harley absent from the
lookup, which is a worse outcome than today's, not a better one. Set logic
and the ambiguous-candidate rule are exercised with synthetic test-only
rows, so every value is proven without shipping any.

Sourced manual-transmission coverage of the corpus's models is a **specific
later phase** — workflow plus refuter, source = manufacturer specification
pages. No bulk inference, ever.

## Named phases that follow

1. **255B** — the content row the transmission axis was built for
   (twist-and-go versus manual small bikes), selecting rows by the axis
   rather than by searching for the word "manual".
2. **The mobile transmission field** — the phase immediately after 255B.
   Mobile already sends `powertrain` as a first-class field, so the
   precedent exists. Until it lands, every mobile-created vehicle arrives
   with the column NULL and the resolver is what covers it; the residual
   gap is whatever machines users add next.
3. **Sourced manual coverage** — as above.
4. **The general applicability mechanism** — a third and fourth axis are
   already visible and measured. A Yamaha XS650, an air-cooled twin,
   retrieves 11 liquid-cooling rows, and that one predates 254. A Honda PCX
   retrieves 8 final-drive-chain rows; a belt-drive Harley and a
   shaft-drive Gold Wing should not get those either, which makes final
   drive its own axis and **not** something to solve with `{manual}` sets.

---

## The chokepoint (added Phase 256)

The ADR above described *what* a row declares and *how* a machine is
classified. It did not say **where the decision is made**, and that gap had
a measurable shape: by the time Phase 256 opened there were **four** code
paths retrieving `known_issues` for a specific machine, and only one of
them applied the filter.

They were found one at a time, each by somebody noticing — never by a
mechanism:

| door | how it was found |
|---|---|
| `_load_known_issues` (diagnose, code) | built with the filter, Phase 255 |
| video `/ask` | asked late in 255 "which other callers exist?" |
| `predict_failures` | same question, same afternoon; filed as F123 |
| `shop/priority_scorer` | Phase 256's Step 0, by a raw-SQL sweep — **dead since it was written**, F126 |

**The rule: one function decides, every door calls it.**
`knowledge/retrieval.py::rows_for_machine` resolves the machine, applies
the filter, and records what it withheld. `purpose` is **required with no
default**, because a default is how the fourth door came to exist without
anyone deciding what it was.

A structural guard fails the build if any module outside the repo layer
names `known_issues` in SQL, and it plants a bypass against itself on every
run — a guard never observed to fail is not a guard.

### What the chokepoint changed about the F122 decision

Phase 255 made an unreadable `applicability` **raise** at read time, having
weighed only two options: raise, or load it as unscoped. The second would
put a mistyped row in front of every machine, so it chose the first — and
the cost shipped, one bad row stopping diagnosis for every machine.

The third option follows from this axis's own principle and was missed:
**exclude the row.** Never unscoped, so a typo cannot reintroduce the 254
defect. Never fatal, so one row cannot take down the product. The id is
logged and the count persisted.

**Loud rejection stays at write time**, and the asymmetry is deliberate: at
write time nothing is lost by refusing; at read time refusing costs the
technician an answer they could have had.

### The cost is a table now, not a number in memory

Phase 255 counted withheld rows in process memory. Every CLI command is a
fresh process, so the aggregate was always zero by the time anyone could
read it — Phase 209B's orphan guard caught the accessors and said *"retire
these or wire that route."* Migration 064 adds `retrieval_withheld` and
`motodiag kb withheld` reads it.

**One correction worth carrying**, because the obvious reading is wrong:
`rows_withheld` is **the cost of not knowing, not what sourcing recovers.**
A Grom resolving `unknown` records 8 withheld rows, and sourcing it
correctly as `manual` withholds the same 8 — those rows are `{cvt}` and a
manual Grom may not have them either way. Sourcing the Grom recovers
**zero**. The table is ordered by *retrievals* for that reason.

### A row naming a machine is a claim, not authority

Four rows name a model in their junction that their own `applicability`
then excludes — a Kymco row names the Filly LX 50 and is withheld from it,
costing that machine its rank-1 critical prediction.

**No override rule was added.** Letting an explicit model match beat the
axis filter would make a row's `model` string authoritative over a sourced
lookup, which is string-naming as authority — the pattern this whole axis
exists to replace. The row that named the Filly did so on a **recycled
page header** that Phase 254 had already examined and rejected.

A permanent guard pins the four with their resolutions and fails on a
fifth. It exists because every other guard here asks whether a machine
receives rows it may not have; only a refuter thought to ask whether a
machine misses rows written for it.

---

## `source` means "manufacturer document", not "service manual" (added Phase 255B)

A refuter auditing Phase 255B's rows reported, repeatedly and across several
rows, that `source: service-manual` was wrong wherever the row's evidence was
an **owner's** manual. The question is settled here rather than row by row,
because the answer is already in the corpus.

**Measured across all 107 seed files: 192 rows carry `source:
service-manual`, and 75 of them — 39% — cite an owner's manual in their own
description.** That is not a labelling error repeated 75 times. It is what the
label has always meant.

**The decision: `service-manual` means the row's evidence is a manufacturer
document.** Owner's manual, service manual, workshop manual, service station
manual, parts catalogue — all of them. It is the provenance *class*, which is
the axis the `source` vocabulary discriminates on:

| label | what it means |
|---|---|
| `service-manual` | a manufacturer document |
| `regulation` | primary legal or regulator text |
| `mechanic-verified` | a person confirmed it on a machine |
| `forum` | community-derived, provenance surfaced at display |
| `unverified` · `model-generated` | neither, and not shippable content |

**No new enum value was added**, deliberately. A separate `owners-manual`
value would split one provenance class across two labels, make every existing
query wrong, and answer a question nobody asks: what a reader needs to know is
whether a claim rests on a document the maker published, and it does.

**What the row must still do** is name its document *type* accurately in its
own prose. `test_a_service_manual_row_names_its_document` enforces that a
document is named at all; naming it as a service manual when it is an owner's
manual is a defect in the sentence, not in the label. Phase 255B fixed two
such sentences and dropped the rows that had more.
