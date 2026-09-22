# Phase 255B — Twist-and-go vs manual small bikes

**Version:** DRAFT (Step 0 only — NOT v1.0) | **Tier:** Standard | **Date:** 2026-09-21

> Step 0 findings only. No plan, no decisions, no scope. Committed at this
> stage so the measurements live in the repo rather than in a transcript.

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

## Not decided here

Scope, row count, which side ships, whether F115 is fixed here, and what to
do about S0-4 and S0-5. **All of that is v1.0, and v1.0 is not written
until Step 0 is reviewed.**
