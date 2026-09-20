# Phase 250C — The model-resolution pool is keyed by the raw make column

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-20

---

## Goal

Row 250C, opened by 250B's Step 0 (F100): `vocabulary_from_conn` keys the
per-make model vocabulary by the **raw** `known_issues.make` string, so a
row reading "Zero, Harley-Davidson, LiveWire, Energica" files its models
under that whole string and under no marque. The model tier cannot fire
for what it cannot look up.

This is the defect Phase 244F fixed for makes and 244I fixed for model
*values*, one level down in the *keys*. Key the vocabulary by derived
marque — and attribute each model to the marque it belongs to, which the
raw keying never had to decide.

## Step 0 — findings

Measured on a freshly seeded database (996 rows) on 2026-09-20, and
re-verified from scratch rather than carried over from 250B's plan.

**S0-1. A third of the corpus's models are invisible to the matcher.**
501 models are resolvable against 764 in the junction. LiveWire **0 of
23**, Damon **0 of 10**, Energica 6 of 24, Harley-Davidson 13 of 36, Zero
14 of 32, Moto Guzzi 11 of 32, Aprilia 31 of 61, MV Agusta 30 of 59, BMW
51 of 74, KTM 62 of 85, Ducati 83 of 106, Triumph 82 of 104. Honda,
Kawasaki, Suzuki and Yamaha are complete, because every one of their rows
carries a single marque. Six of the 23 vocabulary keys are not marques at
all; one is a whole prose sentence holding three models.

**S0-2. The junction is not clean ground truth, so "resolve all 764" is
the wrong target.** 95 of the 764 pairs (12%) are **cross-attributed**: a
row naming six marques files every model against all six, so the junction
holds `(Aprilia, "BMW S 1000 R")`, `(Aprilia, "Ducati desmo")`,
`(Aprilia, "Triumph triples")`. MV Agusta carries 14 such, Aprilia 10, KTM
10, Moto Guzzi 10. Keying alone would import all 95 into the resolution
pool, where they would be matched against as though they were that
marque's models.

**S0-3. Attribution costs nothing and removes the noise.** Simulated over
the real corpus:

| Variant | pool | cross-marque tokens in it |
|---|---|---|
| today (keyed by raw make) | 501 | — (they are unreachable instead) |
| keyed by marque | 764 | **95** |
| keyed by marque, attributed | 638 | **1** |

Attribution has two rungs. A token whose marque can be read from a
single-marque row belongs to that marque — this is what catches "Brutale"
and "F4", MV Agusta models that name no marque. A token that *names* a
marque belongs to it — this is what catches "BMW S 1000 R" under Aprilia.

**S0-4. What that does to resolution.** Sweeping every (marque, model)
pair the junction knows: **511 of 764 resolve today (67%)**, and **644
(84%)** with the fix — 133 more. Four pairs stop resolving, and all four
are the cross-marque noise this phase is removing: MV Agusta / "Ducati",
MV Agusta / "KTM", MV Agusta / "against KTM", MV Agusta / "Triumph
siblings that agree".

**S0-5. Three machines still will not resolve, and none of them is this
row's.** Each was checked against today's behaviour before being excluded:

- **Zero SR/F** — fails today and after. The tokenizer splits on `/`, so
  the pool holds `SR` and `F`, never `SR/F`. That is 244I's splitter, not
  the keying.
- **BMW R1250GS** — `ambiguous` today and after: the abbreviation rung
  finds R1150, R1200, R-series and more, and correctly refuses to choose.
- **Harley-Davidson LiveWire** — `unresolved` today, `ambiguous` after.
  The corpus never writes a bare "LiveWire" model; it writes
  "Harley-Davidson LiveWire (ELW)" and "LiveWire ONE (LW1)", so the name
  genuinely covers two machines. Refusing is defensible, and 250B's
  powertrain filter already carries that bike's prompt.

**S0-6. Prose junk is in the pool and stays there.** `known_models("Zero")`
today includes "BMS logs" and "Zero"; Aprilia's includes "CAN
generations" and "shim-under-bucket". These come from 244I's token
splitter on prose model strings, they exist before and after this change,
and cleaning them is a different row. Filed, not fixed.

**S0-7. One domain fact the data cannot supply.** The cross-marque
exclusion must not fire between **Harley-Davidson and LiveWire**: the
model token "LiveWire" names a marque *and* is Harley-Davidson's own
machine, so excluding it would take every LiveWire model out of
Harley-Davidson's pool — the opposite of the fix. Simulated both ways; the
exemption is what keeps Harley-Davidson at 23 models instead of 15.

**S0-8. What the tests pin on this module.** `models.py` carries a source
guard: `code_of(models)` must contain the literal
`SELECT make, model FROM known_issues`, so the derivation keeps reading
that query and does its marque work in Python rather than moving to a
junction JOIN. `extract_models` is called with its vocabulary
**positionally as the third argument** in four places, so nothing may be
inserted before it. `SCHEMA_VERSION == 62` is pinned in **twelve** test
files, so this phase adds no migration — the live junction is rebuilt at
close-out instead. And `marques.py` may not contain a marque-name
literal, which decides where S0-7's fact lives.

**S0-9. `All European makes` harvests marque names as models.** Its model
column reads "Aprilia, BMW, Ducati, Gilera, Husqvarna, KTM, Moto Guzzi,
Moto Morini" — a list of marques, tokenised as models. Today they are
quarantined under a key nobody queries; keyed by marque they would land
in each European marque's pool, so `known_models("BMW")` would contain
"BMW", "Ducati" and "Aprilia". Six tokens in the corpus are exactly a
marque name — Aprilia, BMW, Ducati, KTM, Moto Guzzi and Zero — and none
of them is a model. Dropping them costs nothing: the corpus writes no
bare "LiveWire" model, the one case where a marque name is also a
machine.

## Decisions

**D1. Key by derived marque, using the derivation 244F already
established.** `extract_marques` is the corpus's own answer to "which
marques does this string name"; the vocabulary uses it rather than
inventing a second rule.

**D2. Attribute in three rungs, single-marque evidence first.** A model
seen on a single-marque row belongs to that marque. Otherwise a token that
*names* a marque belongs to it. Otherwise the row's marques all take it.
A token that is *exactly* a marque name is not a model and is dropped
(S0-9). The rule is data-driven and its residue is measured, not assumed:
**1** mis-attributed token out of 638.

**D3. The related-marque exemption is a named fact in its own module.**
244F guards `marques.py` and 244C guards `vehicle_resolver.py` against
hard-coded marque names, and rightly — the vocabulary there is derived. A
parent/sub-marque relationship is not derivable from a make column that
never writes it, so it goes in `knowledge/marque_families.py`, declared
and commented, the way 250B's electric-marque fact went in
`knowledge/powertrain.py`.

**D5. The derivation stays connection-scoped.** `marques.py` records why:
deriving by `db_path` where a connection was in hand once let "the write
path and the read path disagree about what a marque is". The marque
vocabulary and the European expansion are computed once per rebuild and
passed down, never re-read per row from the configured database.

**D4. Out of scope, each filed rather than folded in.** The `/` split
(Zero SR/F), the ambiguity rung (BMW R1250GS), and the prose junk tokens.
This row changes the keying and the attribution; those three would each
change what counts as a model, which is a different question.

## Scope

1. `knowledge/models.py` — `vocabulary_from_conn` keys by derived marque
   and attributes per D2; `extract_models` looks up the union of the
   marques a row's make string names, rather than the raw string. Its
   marque vocabulary arrives as a new keyword argument **after**
   `vocabulary`, because four callers pass that one positionally.
2. `knowledge/marque_families.py` — the parent/sub-marque fact.
3. `rebuild_model_index*` re-derives the junction from the new
   vocabulary. No schema change and no migration: 056 already exists and
   its `post_apply` hook is unchanged.
4. Tests: the per-marque pool measurements, the attribution rungs, the
   cross-marque exclusion and its exemption, the four pairs that correctly
   stop resolving, and the three out-of-scope machines pinned as
   unchanged.
5. The live database's junction rebuilt at close-out, copy first, with the
   before-state printed.

## Non-goals

- No schema change, no migration, no corpus edit.
- No change to the resolver's ladder, its fuzzy floor, or its tiering.
- No change to `known_makes`/marque derivation — 244F's work stands.
- No cleaning of prose tokens (S0-6), no `/` handling (S0-5).

## Results (v1.1)

**Shipped:** `knowledge/models.py` keys the vocabulary by derived marque and
attributes each token; `knowledge/marque_families.py` holds the one fact the
data cannot supply; `knowledge/prompt_rows.py` gained a safety floor (see
Deviations); `tests/test_phase250C_model_vocabulary.py` is 48 tests. No
schema change, no migration, no corpus edit.

- 48 new tests; 250B's safety-floor assertion and 245's Damon pin rewritten.
- 9 mutations.
- Full regression **7,403 passed, 0 failed, 25:05**.

### What the matcher can now see

| marque | before | after | | marque | before | after |
|---|---|---|---|---|---|---|
| LiveWire | **0** | 11 | | Aprilia | 31 | 47 |
| Damon | **0** | 4 | | BMW | 51 | 66 |
| Energica | 6 | 17 | | Ducati | 83 | 95 |
| Harley-Davidson | 13 | 24 | | KTM | 62 | 74 |
| Zero | 14 | 25 | | MV Agusta | 30 | 42 |
| Moto Guzzi | 11 | 21 | | Triumph | 82 | 95 |

**501 → 639.** Honda 27, Kawasaki 39, Suzuki 29 and Yamaha 23 did not move,
which is the control: every one of their rows names a single marque, so
raw-key and marque-key are the same thing for them, and a change there would
have meant the derivation touched something it had no business touching.

**Resolution: 511 of 764 pairs (67%) → 648 of 743 (87%).** The junction grew
1,839 → 1,897 rows. It lost 42 pairs and gained 21: every one of the 42 is
the junk this phase set out to remove — `(Aprilia, "BMW")`, `(BMW, "BMW")`,
`(Ducati, "Ducati")`, `(Ducati, "18 poster")` — and the 21 gained are the
compound designations below.

### Deviations

**1. The slash split was folded in, at the operator's request.** S0-5 filed
`Zero SR/F` as out of scope and D4 said so; mid-build the operator asked for
it, and since it lives in the same function this phase was rewriting, it was
done here rather than in another row.

The corpus uses `/` for two different jobs, and the split has to keep both.
It separates two machines in "R1200/R1250", "F650/F700", "450/500 EXC-F",
"Ego/Eva", "K1200S/K1200R" and "Zero S/DS"; it is part of the name in Zero's
own SR/F, SR/S, SR/FX and DSR/X. They separate on the corpus's own evidence:
in every enumeration the right-hand fragment is a full designation of three
characters or more, and in every compound name it is one or two. The
left-hand side must be at least two characters, which is what keeps "S/DS" —
Zero S and Zero DS — a list. `SR/F`, `SR/S` and `DSR/X` now resolve
**exact**, and the enumerations still split.

**2. A safety floor, because this phase swept one away.** Making model
resolution work has a consequence nobody had measured: on a Zero SR/F the
prompt became twelve tier-0 rows, all specific to that model, and **not one
critical row survived** — 241's high-voltage rules are `make_wide`, so a
better model match outranked every one of them. A technician opening a pack
would have lost "do not work alone on a live HV system" and "removing the
service disconnect does not de-energise the motor" to a more specific prompt.

`prompt_rows.py` now holds `SAFETY_RESERVE = 3` rows for the most severe
content the machine has, swapped in over the lowest-ranked rows already
chosen. After: Zero 3 critical, Energica 3, LiveWire ONE 5, Harley-Davidson
LiveWire 6 — and the Zero and Energica prompts now carry **all four** generic
layers, which they did not before. 250B's assertion moved from "at least five
critical rows" — a snapshot of a prompt whose model never resolved — to the
declared floor plus the named rules themselves.

**3. What the attribution does not fix, measured.** 30 pool entries are held
by two or more unrelated marques. Most are genuinely shared fragments — 1000,
1200, 750, 900, 998 — which belong in each marque's pool. The rest are the
prose tokens S0-6 already filed ("2020 service manual", "CAN generations")
and tokens from multi-marque rows that no single-marque row owns, so
"Alpinista" sits in four electric marques' pools instead of LiveWire's alone.
The rungs cannot separate those without evidence the corpus does not carry.

**4. Phase 245's Damon pin needed updating, and it is the phase in one
sentence.** That file asserted the model "cannot resolve, because no row
carries one, and that is correct today". A row did carry one: 241's
high-voltage file names "Damon HyperSport" in its model column, and the raw
keying filed it under "Zero, Harley-Davidson, LiveWire, Energica, Damon" and
under no marque. The name was in the corpus and unreachable. It now resolves,
so a Damon HyperSport reaches the HV rules — and the assertion that the
absence is real (no seed file, no row of its own, every row model-generated
and list-valued) is untouched, with `corpus_hits == 0` added so a resolved
model can never be read as Damon content.

The full regression is how this was found: the suites in the blast radius
were all green, and 245 is not one anybody would have listed.

### Verification

- Pools measured for all sixteen marques, before and after, with the four
  already-complete marques pinned as unmoved.
- 382 tests green across the fourteen suites in the blast radius, including
  244C, 244E, 244F, 244I and their source guards, 244S's four pins, Gate 13
  and 250B.
- The three machines S0-5 ruled out were re-checked: `BMW R1250GS` still
  refuses as `ambiguous`, `Harley-Davidson LiveWire` still refuses, and
  `Zero SR/F` now resolves because Deviation 1 brought it into scope.

## Verification Checklist

- [x] Per-marque pools measured before and after, all sixteen
- [x] The four pairs that stop resolving are the cross-marque noise, named
- [x] Honda, Kawasaki, Suzuki and Yamaha unchanged — they were complete
- [x] 244I, 244C, 244F and 244E green, source guards included
- [x] 250B and Gate 13 green — the electric prompts must not move
- [x] The new test file scanned by 244G's raw-source guard
- [x] Mutations caught — 9/9
- [x] Full regression green — **7,403 passed, 0 failed, 25:05**, 0 skipped
- [x] Live junction rebuilt copy-first, before-state printed
- [x] Roadmap row, `implementation.md` history row, `phase_log.md`
