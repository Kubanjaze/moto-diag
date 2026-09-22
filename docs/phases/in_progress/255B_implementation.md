# Phase 255B — Twist-and-go vs manual small bikes

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-22

> **Step 0 below is unchanged from the committed draft** (`b157da2`) and is
> not re-run. The plan begins at "Decisions taken".

---

## S0-1. The subject is genuinely empty — and its vocabulary is not

`twist-and-go` and `twist n go` return **0 rows** across 1,045. The row has
never been written.

But the *nouns* it would use are well populated, and almost none of them is
scoped:

| noun | rows | transmission-scoped | dominant provenance |
|---|---|---|---|
| gear selection / shifting | 21 | **0** | unverified 17 |
| variator / drive belt | 19 | 7 | service-manual 13 |
| transmission / gear oil | 13 | **0** | unverified 7 |
| clutch-less / semi-auto | 9 | 1 | unverified 5 |
| clutch lever / cable | 8 | **0** | unverified 7 |
| engine braking | 6 | **0** | unverified 3 |
| centrifugal clutch | 4 | 3 | service-manual 4 |
| kickstart | 4 | 1 | unverified 3 |
| creep / idle engagement | 3 | 1 | unverified 2 |

**48 manual-side rows are already unscoped and already reaching scooters.**
That reframes the sequencing question below: option (c) would not open a
leak, it would enlarge one.

## S0-2. Sequencing — what option (c) would actually put in front of a PCX

Measured on the live database, a Honda PCX 150 **already** retrieves:

* **3** clutch lever / cable / pack rows — including id 206 *"Clutch cable
  fraying and sudden failure — cable clutch"* and id 258 *"CRF250L/300L
  clutch basket rattle"*
* **2** gearbox / shifting rows
* **13** final-drive-chain rows

A PCX has no clutch cable, no gearbox and no chain.

**Option (c) — manual-side rows ship unscoped — adds to this.** A row
written as *"clutch free play: check at the lever"* would reach the PCX at
`make_wide` and could outrank the CVT content, because `make_wide` beats
`make_other_model` (see S0-4). So (c) does not merely defer a fix; it
**writes new rows into a known defect**, with the phase that documents the
distinction being the one that widens it.

**Option (b) — pull the coverage phase forward — is bigger than it looks.**
The blocker 255 identified is not that manual machines are unclassifiable;
it is that they resolve **`unknown`**, so a `{manual}` row is withheld from
every CBR and Harley not in the lookup. The lookup holds **1** `manual`
entry today (SYM Wolf 150). Coverage is a sourcing phase across the corpus's
manual models, with its own refuter.

**Option (a) is recommended**, with one refinement worth stating: the
comparison can still be written, **from the twist-and-go side**. A row
saying *"a scooter has no clutch lever, so the free-play procedure in a
manual-bike guide does not apply"* is a `{cvt}` row that mentions manual
machines. It ships now. Its mirror — *"what is different about a small
manual bike"* — waits for coverage.

## S0-3. The three debts Phase 256 left

All three confirmed present on the live database:

| row | debt | state |
|---|---|---|
| **4609** | drop `Filly LX 50` from the model column | Filly **is** in the junction (5 entries) |
| **4615** | split the regulator-methodology half | declares `{"transmission": ["cvt"]}`, 11 junction entries |
| **4611** | split the kickstart half | declares `{"transmission": ["cvt"]}`, 29 junction entries |

Each needs its own commit with `KNOWN_SELF_EXCLUDING` in
`tests/test_phase256_chokepoint.py` updated — that pin is permanent and two
of its four entries resolve here.

## S0-4. The PCX question — it is not a reserved slot, it is a tier defect

**Measured.** A PCX 150 retrieves 165 rows, **8 of them transmission-scoped
and applicable**, and **0 reach its twelve**. The twelve are 2 `model`-tier
PCX rows and 10 `make_wide` generic Honda rows. The 8 scoped rows sit at
ranks **58, 66, 77, 83, 114, 116, 138, 141** — all at tier
`make_other_model`, the least specific tier there is.

**Why they are at that tier is the finding.** Eight of the 254 rows **do**
name the machine: their junction carries `Honda PCX125` and `Honda PCX150`.
But the tier query compares `known_issue_models.model` against the
**resolved** model, and:

* `resolve_vehicle("Honda", "PCX 150")` resolves to **`PCX 150`**
* the junction stores **`Honda PCX150`**

Two mismatches at once — a marque prefix and the spacing. So a row that
names the machine can never reach tier 0 for it.

**This is corpus-wide, not a Phase 254 quirk: 469 of 2,424 junction rows
(19%) begin with a marque name.**

**Simulated, not assumed.** Adding the resolver-normalised form of every
prefixed junction entry (485 aliases) to a copy of the live database:

| | scoped rows in the PCX's twelve | scoped tiers |
|---|---|---|
| as shipped | **0** | `make_other_model` |
| normalised | **6** | `model`, `make_other_model` |

Seven rows enter — 4605, 4606, 4607, 4608, 4610, 4611, 4612 — and seven
generic Honda rows leave: brake fluid (236), coolant hose (233), ground
corrosion (267), HISS immobilizer (262), starter clutch (232), starter
relay (265), tyre age (240).

**That trade needs a decision with numbers, and it is not 255B's.** It is a
244I-family retrieval defect touching 19% of the junction and every machine
in the corpus, not a content question. **No fix proposed here.**

## S0-5. Existing-code overlap — two more corpora with the same defect and no mechanism

The applicability axis fixed `known_issues`. The predictor reads two other
row sets that have **no applicability field at all**:

* **`advanced/wear_patterns.json`** — **24 of 30 patterns apply to every
  machine** (`make: null`, `model_pattern: "%"`), including
  `clutch-cable-stretch`, `clutch-basket-judder`, `chain-stretch-sprocket`
  and `final-drive-splines`.
* **`advanced/data/service_interval_templates.json`** — `chain-clean-lube`
  at `make: "*"`, described as *"Universal chain maintenance"*.

**Demonstrated, not inferred.** Feeding each pattern its own symptom strings:

| pattern | Honda PCX 150 (CVT, no clutch cable, no chain) | Harley Road King (belt drive) |
|---|---|---|
| `clutch-cable-stretch` | **matches** | **matches** |
| `chain-stretch-sprocket` | **matches** | **matches** |
| `clutch-basket-judder` | **matches** | **matches** |
| `final-drive-splines` | **matches** | **matches** |

Read by `advanced/wear.py` and `advanced/schedule_repo.py`, entirely outside
the `known_issues` path and therefore outside the chokepoint.

**The symptom vocabulary shows the same tilt**: 40 symptoms, of which
`Clutch slipping` and `Hard shifting` are manual-machine symptoms, and
**none** of belt, creep or kickstart appears.

So the row this phase would write — *what is different about diagnosing a
twist-and-go* — would document a distinction that **two other corpora
actively violate**, on the same machines, in the same product.

---

# Plan (v1.0)

## Decisions taken

Five questions were put to the operator on 2026-09-21 and answered. They are
recorded here because the plan below is only legible against them.

| # | question | decision |
|---|---|---|
| 1 | sequencing | **(a)** — twist-and-go side only, scoped per row. The manual mirror waits for the sourced coverage phase. |
| 2 | F115, row 4605's make column | **fix in 255B, by enumerating the belt / cam-belt marques** — not by wildcard. |
| 3 | the PCX tier defect | **its own phase.** 255B records the measurement and opens a roadmap row. No fix here. |
| 4 | `wear_patterns.json` and `service_interval_templates.json` | **file as a finding.** No code change here. |
| 5 | the three Phase 256 debts | **all three, in 255B, three commits.** |

**One premise in the brief was corrected by the operator and the correction
is load-bearing.** Dropping `Filly LX 50` from 4609's model column does
**not** restore the Filly's prediction. It removes an over-claim made on a
recycled page header. The Filly stays `unknown`, still does not receive
4609, and the guard entry resolves because *the row no longer names a
machine it excludes* — not because the machine starts receiving it. No
lookup entry, no override. D4.1 below is written to that causality, and so
is the guard prose it replaces.

**Verified on the live database while writing this plan** (`data/motodiag.db`,
`schema_version` 64):

```
resolve_transmission("Kymco", "Filly LX 50")
  -> candidates = all six, provenance = 'unknown', entry = None
```

Fail-closed, therefore 4609 (`{"transmission": ["cvt"]}`) is withheld from
the Filly **before and after** this phase. That is the number the commit
message carries.

## Goal

Write the twist-and-go side of the twist-and-go/manual comparison — the
content Phase 255 built the axis for — and clear the three debts Phase 256
left, without any row declaring a set containing `manual`.

---

## D1. Applicability sets — which set, and the rule that picks it

The lookup as it stands, counted (`TRANSMISSION_LOOKUP`, 50 entries):

| value | entries | which |
|---|---|---|
| `cvt` | 46 | the scooter corpus |
| `semi_auto_centrifugal` | 3 | Honda Super Cub C125, Honda CT125 Hunter Cub, SYM Symba 100 |
| `manual` | 1 | SYM Wolf 150 |

**The rule, stated once and applied by row id:**

* A claim that turns on **there being no hand clutch lever** →
  `{cvt, semi_auto_centrifugal}`. The Super Cub, the Hunter Cub and the
  Symba have no clutch lever either; a row that excluded them would be
  wrong about them.
* A claim that turns on **there being no gear selection at all** → `{cvt}`
  alone. Those three machines *do* have a foot gear lever and four speeds;
  including them would be the 254 error in miniature.

No row declares a set containing `manual`. Each row's set is declared by
row id with a one-line reason, per the Phase 255 rule — never inferred from
marque or keyword.

## D2. The rows — subjects and sets, text not yet written

Six subjects. **Row text is deliberately not drafted in v1.0**: under the
content rules an entry is anchored to a document named in its own
description, so the text is written at build time from quotes, and a
subject that yields no quote does not ship as a row. The count below is
therefore a ceiling, not a promise.

| # | subject | set | why that set |
|---|---|---|---|
| R1 | No clutch lever — the free-play and cable-adjust procedures in this corpus have no referent | `{cvt, semi_auto_centrifugal}` | turns on the absent lever, which all four classes of these machines share |
| R2 | No gear selection — what "hard shifting" and "will not go into gear" mean on a machine with no gears, and what the CVT symptom is instead | `{cvt}` | the semi-auto machines shift; excluding them is the point |
| R3 | No final-drive chain — chain adjust/lube intervals do not apply, and the CVT belt is a replace-on-interval item that is **not** tensioned | `{cvt}` | the Super Cub and Symba are chain-driven |
| R4 | Engine braking — the clutch disengages below engagement speed, so a closed throttle does not retard the machine the way a manual bike's does | `{cvt, semi_auto_centrifugal}` | centrifugal disengagement is shared |
| R5 | "Transmission oil" names two different things — a scooter's final-drive gear oil is not a gearbox oil, and the intervals and quantities differ | `{cvt}` | the semi-auto machines have a gearbox |
| R6 | Creep at idle — a correctly set-up twist-and-go does not creep, and creep is a clutch-shoe symptom rather than an adjustment | `{cvt, semi_auto_centrifugal}` | centrifugal clutch behaviour is shared |

**Selection is by the transmission axis, not by searching for the word
`manual`** — so 255B does not depend on F116 (the `manual` substring
collision, 311 rows / 300 of them the document) being fixed first.

**Evidence.** On-disk first. The research library is re-derived and present:
`/private/tmp/claude-501/-Users-lilquant-Projects-moto-diag/c1e7849e-3adc-4dbf-b76d-26d54a43b93b/scratchpad`,
**263 PDFs** (the earlier session id in the brief is dead; this one is live).
A subject that cannot be sourced from the library goes to a research
workflow with a refuter whose brief is to argue the row is unsafe and which
fetches every cited page itself. No numeric threshold without a cited
manufacturer page. One provenance label per row.

## D3. F115 — 4605's make column

**The collision set, measured rather than asserted.** Vocabulary
`drive belt` — the maker's own phrase — over `title || description ||
symptoms`, whole corpus, 1,045 rows, **count 13** (not the first
screenful). Positive control: 4605 itself is in the set, at its own id.

Of the 13, the members carrying a **non-CVT** meaning of the phrase are:

| id | make | meaning |
|---|---|---|
| 188 | Harley-Davidson | final drive — *"Drive belt tensioner bearing failure"* |
| 579 | Yamaha | final drive — belt-drive cruiser inspection |
| 715 | BMW | alternator — belt-driven alternator, oilhead/hexhead/R nineT |
| 870 | BMW | alternator — two incompatible belt types |
| 1312 | Harley-Davidson, LiveWire | final drive — belt with its own tension gauge |

So the enumeration is **Harley-Davidson, BMW, LiveWire** — three marques,
each anchored to a named row in this corpus, which is what 4605's own
description already cites when it speaks of a Harley drive belt tensioner
bearing, a LiveWire tension gauge and BMW boxers with two incompatible
types. **Yamaha is already in 4605's make column**, so the Bolt owner
reached by 579 already reaches it; no gap there.

**Makes only, not models.** `make_wide` is the tier that carries this, and
naming a model the documents do not establish is precisely the 4609 mistake
being repaired one commit away.

**4605 stays unscoped, and this is the part that matters.** Measured:

```
Harley-Davidson Road King -> provenance 'unknown', entry None
BMW R1200GS               -> provenance 'unknown', entry None
LiveWire ONE              -> provenance 'unknown', entry None
```

The filter is fail-closed. Declaring **any** transmission set on 4605 would
withhold it from all three again — F115 re-created by another route, in the
same commit that claims to fix it. A test asserts 4605's `applicability`
stays NULL, and that test is broken first to see it fail.

## D4. The three Phase 256 debts — three commits

`KNOWN_SELF_EXCLUDING` in `tests/test_phase256_chokepoint.py` is a
**permanent** pin, not phase-scoped. The guard asserts
`found == set(KNOWN_SELF_EXCLUDING)`, so a key whose condition no longer
holds must be **removed**, not re-worded. Two of the four resolve here;
`Piaggio Beverly 250` and `Vespa 946` stay (F119, closed-unobtainable).

### D4.1 — commit 1: 4609 drops the Filly

Remove `Filly LX 50` from 4609's `model` column and from
`known_issue_models` (5 entries today → 4). Remove the
`(_KEY_KYMCO, "Filly LX 50")` key from `KNOWN_SELF_EXCLUDING`.

The prose in that key currently reads *"Until then the Filly loses its
rank-1 critical prediction"*, which implies the fix returns it. It does
not. The key is deleted, so the prose goes with it — but the phase log and
the commit message state the correct causality: **the over-claim is
withdrawn, the retrieval is unchanged, and the guard resolves because the
row stops naming a machine it excludes.** Measured before and after.

### D4.2 — commit 2: 4615 splits

| half | applicability | content | campaigns named |
|---|---|---|---|
| CVT | stays `{cvt}` | one campaign touches a scooter CVT component; across the small-scooter makes, no belt/pulley/sheave/variator campaign | 21V251000 |
| general | **unscoped** | the two regulator index endpoints contradict each other bidirectionally (25 of 102); an empty per-vehicle response is indistinguishable from a wrong model string; query by campaign number | 26V302000, 14V364000 |

`SYM Symba` goes with the general half, per the operator. The
`(_KEY_REGULATOR, "SYM Symba")` key is removed: the general half is
unscoped, so naming the Symba is no longer a contradiction, and the CVT
half no longer names it. Both halves keep `source: regulation` and each
names its campaigns — the regulation content rule holds on both.

### D4.3 — commit 3: 4611 splits

| half | applicability | content |
|---|---|---|
| CVT | stays `{cvt}` | which machines in this class have a kickstart; carburetted machines have one and injected ones do not; the Buddy Kick is injected and the word `kick` in its manual is only the model's name |
| general | **unscoped** | a kickstart is a start path that does not need the battery, so a machine that kick-starts but will not start electrically points at the brake-lever switch or the starter circuit — the kickstart as a **diagnostic**, not only a fallback |

**4611 has no `KNOWN_SELF_EXCLUDING` entry today and will have none after** —
its junction (29 models) contains no Symba and no machine it excludes. The
brief's "each its own commit with `KNOWN_SELF_EXCLUDING` updated" holds for
commits 1 and 2; this commit touches the guard only if the split creates a
new naming, which it does not. Stated rather than glossed.

### D4.4 — id and title discipline

`backfill_row_applicability` matches on `(title, make)` and applies an
`UPDATE`, so `known_issues.id` never changes. To keep that true:

* **The half that keeps the original id keeps the original title verbatim.**
  For both 4611 and 4615 that is the **CVT** half. The general half is a new
  row with a new id (1046+, after the D2 rows).
* Consequence to flag: 4615's title ends *"and two indexes that disagree
  with each other and with the data"* — a clause that now describes the new
  row. Trimming it is a title change, which re-points the backfill matcher
  and needs migration 065's hook to update `title` by id. **Recommendation:
  leave the title verbatim this phase** and let the new row carry the index
  subject in its own title. Operator's call at review.

## D5. Migration and counts

* `SCHEMA_VERSION` 64 → **65**; migration **065**, following 063's shape
  (column work plus a `post_apply` hook), because the loader only reaches a
  database someone re-seeds and the operator's live database is already
  populated.
* The hook must also rebuild the junctions — 4605's makes and 4609's models
  change, and `known_issue_makes` / `known_issue_models` are derived. 063's
  chain used `rebuild_make_index` / `rebuild_model_index`; `post_apply` takes
  one target, so 065 gets a single hook that calls what it needs.
* Seed file: `src/motodiag/knowledge/seed/knowledge/known_issues_cvt.json`
  (12 entries today). It and the live database must agree; a test asserts
  that for every row this phase touches.
* `known_issues` 1,045 → **up to 1,053** (6 new content rows + 2 split
  halves), and the phase log states the number actually reached, not this
  ceiling.

## D6. The PCX tier defect — a phase, not a fix

255B ships **no code** for S0-4. It opens a ROADMAP row carrying S0-4's
measurements: 469 of 2,424 junction rows (19%) marque-prefixed; the PCX
going 0 → 6 scoped rows in its twelve on a copy with 485 normalised
aliases; the seven in (4605, 4606, 4607, 4608, 4610, 4611, 4612) and the
seven out (236, 233, 267, 262, 232, 265, 240).

**Number to confirm at review: `244AA`.** It belongs to the 244I family —
244I is the phase that built the model column and the exclusion semantics —
but **244A through 244Z are all taken**, so the family needs a two-letter
suffix or the phase goes elsewhere. Alternative: `255C`. Not chosen
unilaterally.

**255B must also correct the existing 255B roadmap row at close-out.** It
currently frames the PCX as *"whether a generic layer needs a reserved slot
the way `SAFETY_RESERVE` gets one"*. Step 0 refuted that: it is not a
capping or reserved-slot question, it is a string-matching defect in the
tier query. Leaving the old framing on the roadmap would send the next
phase after the wrong thing. The rewritten row is capped at 120 words plus
a link.

## D7. The two other corpora — F129

Next F-number, counted across **both** files per `ROADMAP_AUTHORITY.md`:
backend `docs/FOLLOWUPS.md` holds F115–F128 (14); `moto-diag-mobile`'s holds
F1–F115 plus cross-references to F123 and F128. Max across both = **F128**,
so this is **F129**, filed in the backend repo because the code is
`src/motodiag/advanced/`.

One finding covering both files, carrying S0-5's demonstration: the four
patterns that match both a Honda PCX 150 and a belt-drive Harley Road King,
the 24-of-30 census, `chain-clean-lube` at `make: "*"`, and the two readers
(`advanced/wear.py`, `advanced/schedule_repo.py`) that sit outside the Phase
256 chokepoint. No fix proposed.

---

## Scope

1. Up to six twist-and-go content rows, each scoped by row id with a reason (D1, D2).
2. 4605's make column gains Harley-Davidson, BMW, LiveWire; stays unscoped (D3).
3. Three commits for the Phase 256 debts (D4).
4. Migration 065, schema 64 → 65 (D5).
5. A ROADMAP row for the PCX tier phase, and a correction to the existing 255B row (D6).
6. F129 filed (D7).

## Non-goals

* **No row declares a set containing `manual`.** The mirror waits.
* **No fix for the PCX tier defect.** Measurement and a roadmap row only.
* **No applicability field on `wear_patterns.json` or
  `service_interval_templates.json`,** and no change to their readers.
* **No new lookup entries** — in particular none for the Filly. The 4609 fix
  withdraws a claim; it does not manufacture coverage.
* **No loosening of the applicability filter** and no special-casing of the
  244S cap.
* F116, F117, F118 untouched.

## Risks

| risk | mitigation |
|---|---|
| A D2 subject turns out to be unsourceable and the row ships anyway on plausibility | No quote, no row. The six are a ceiling; the phase log states what actually shipped and what was dropped. |
| 4605 gets scoped by a later hand and F115 silently returns | A test pins `applicability IS NULL` on 4605 with the reason in its message, broken first to see it fail. |
| Splitting 4611/4615 churns ids and breaks the backfill matcher | D4.4 — the retained half keeps id **and** title verbatim; the new half is a new row. |
| The migration's junction rebuild is skipped and the make/model columns disagree with the junctions | A test asserts column-vs-junction agreement for every row this phase touches, in both directions. |
| The engine-braking and creep rows (R4, R6) over-claim about the three `semi_auto_centrifugal` machines | Each of those rows must cite a document for the semi-auto machine specifically, not only for a scooter, or it drops to `{cvt}`. |

## Results (v1.1)

### What shipped, and what did not

**Zero twist-and-go content rows.** The phase is named for a comparison it
did not write. Seven content subjects were drafted; **seven died to the
documents** across two adversarial cycles, and an eighth — a row already
committed — died in audit.

What did ship is the mechanism repair around it:

| | |
|---|---|
| rows added | **1** (4615's general half) |
| rows repaired | **3** (4609, 4615, 4605) |
| rows restored | **1** (4611 — a split made and backed out) |
| corpus | 1,045 → **1,046** |
| schema | 64 → **65** (migration 065) |
| findings filed | F129, F130, F131 |
| findings resolved | **F115** |
| live defects fixed | **F132** |
| `KNOWN_SELF_EXCLUDING` | 4 entries → **2** |

### Deviations — every content subject, and the document that killed it

**R1 — no clutch lever.** Shipped nothing. Honda's PCX150 owner's manual:
*"operating the rear brake lever applies the rear brake and a portion of the
front brake."* The left lever is a linked-brake lever on four machines the
row named. The rewrite then died on attribution: the passage is verbatim
only in the 2015 edition, and the 2022/2023 editions gate it *"Except ABS
type"*.

**R2 — no gear to select.** Shipped nothing. Killed on its own cited page:
Piaggio's MP3 400 workshop manual gives the drive after the variator as
*"Final reduction Gear reduction unit in oil bath"*, while the row's fix
step forbade quoting "an oil for a gearbox". The rewrite kept the same
clause and died on it again.

**R3 — no chain.** Shipped nothing. The Kymco Agility 50 service manual's
own periodic maintenance table lists *"Drive chain I I I I"*. Two of the
four positive controls, the Honda C70 and CT110, have **no PDF in the
library at all** — only OCR'd text and an archive landing page. The rewrite
inverted to that schedule line being the defect and died because it cited
the wrong table: the manual's real schedule is clean and the line sits in an
unheaded appendix.

**R4 — engine braking.** Never written. Both halves of its premise were
contradicted before a row existed. Honda's PCX owner's manual warns of *"the
rear wheel from skidding due to engine braking"* on a CVT scooter; Honda's
Super Cub C125 owner's manual instructs *"Engine braking helps slow your
vehicle down when you release the throttle"*, and the SYM Symba manual heads
a section *"Engine Brake"*. This is the citation rule working at the
cheapest possible point.

**R5 — "transmission oil" names two things.** Shipped nothing. The thesis
was inverted by the documents it cited: Honda's PCX owner's manual prints
*"Transmission oil capacity After draining 0.13 US qt (0.12 L)"* in the same
booklet whose schedule says "Final Drive Oil"; Kymco's Super 8 50X prints
*"Gear oil"* in its maintenance table and *"Transmission oil … 0.19 qt"* in
its capacities table. The rewrite inverted to the collision and still died:
*"on the Yamaha it is not the term at all"* is false — the Zuma 125 service
manual heads its procedure **"CHANGING THE TRANSMISSION OIL"** — and *"a
fifth of a litre or less"* is false, the GTS 300 printing 250 cm³ and the
Primavera 270 cm³.

**R6 — creep at idle.** Shipped nothing. Five Piaggio-group service manuals
carry *"REAR WHEEL ROTATES WITH ENGINE AT IDLE — Idling rpm too high →
Adjust the engine idle speed"* as the **first** cause, so the row's claim
that the makers name the clutch rather than the idle screw was false. The
rewrite inverted to "the makers disagree on order" and died too: Piaggio's
50cc books list three and four causes, and Kymco and Honda publish exactly
one cause with **no ordering at all**, so there is no opposite order.

**R7 — the Kymco Like clutch-lever step.** Shipped nothing, and this is the
one whose *substance* survived both cycles. The defect is real and verbatim
at page index 48. It died on the documentary record instead: *"two
editions"* was three paths holding one byte-identical PDF, and the corrected
row died on scope — the manual's own specification tables put **ABS on the
150i and drum on the 50i**, so a drum-model defect was being declared for
the ABS machine and withheld from the drum machine.

### The F132 table — the evidence the year-window change shipped on

Rows entering / leaving per machine per model year, nulling the unevidenced
windows:

```
machine                      class        2001   2003   2005   2013   2019   2022   2026   2027
------------------------------------------------------------------------------------------------
Honda PCX 150                cvt            +8   same   same   same   same   same   same     +8
Kymco Agility 50             cvt            +9     +1   same     +1     +1     +1     +1     +9
Vespa LX 50                  cvt            +9     +1   same   same   same     +1     +1     +9
Yamaha Zuma 125              cvt            +8   same   same   same   same   same   same     +8
Genuine Buddy 125            cvt            +8   same   same   same   same   same   same     +8
Kymco People S 250           cvt            +9     +1   same     +1     +1     +1     +1     +9
Honda GL1800 Gold Wing       NOT cvt        +1   same   same   same   same   same   same     +1
Yamaha YZF-R1                NOT cvt        +1   same   same   same   same   same   same     +1
Honda Grom                   NOT cvt        +1   same   same   same   same   same   same     +1
Kawasaki Ninja 400           NOT cvt      same   same   same   same   same   same   same   same
SYM Symba 100                semi-auto      +1   same   same   same   same   same   same     +1
------------------------------------------------------------------------------------------------
TOTAL entering: 123    TOTAL leaving: 0
```

Nothing ever leaves — a null bound removes a gate. The prediction that
non-CVT machines would show **zero** change did not hold, and the table is
what showed it. The one row they gain is 4605, unscoped by design, whose
reach this phase deliberately widened when it closed F115.

## Verification checklist

* [ ] `tests/test_phase244G_guard_shapes.py::scan_for_raw_source_assertions` run over the **whole** `tests/` tree, before the regression. Source assertions use `from support.source_guards import code_of`, never raw `read_text`.
* [ ] `scripts/check_f9_patterns.py --all` clean.
* [ ] Every guard broken once and seen to fail. A cap is never what makes a correctness property hold.
* [ ] Mutation run: clear `__pycache__`, `python -B`, restore after.
* [ ] Every negative claim states its search vocabulary **including the maker's own word**, the scope, the **count** (never piped through `head`), and passes a positive control on a known-present case.
* [ ] Regression states **commit hash and collected count**. Gate on failures **and** skips — a skip stops the close-out.
* [ ] Seed file and live database agree for every touched row.
* [ ] `KNOWN_SELF_EXCLUDING` down to two entries, and the guard still fails when a row is made to name a machine it excludes.
* [ ] Deploy: backups to `~/backups/motodiag/`, retain last 5, never `/tmp`. Print the before-state, migrate a copy first, then live.
* [ ] Close-out order: v1.1 Results → phase log → roadmap row (≤120 words + link) → `implementation.md` history row → merge → push → deploy → file F129.
