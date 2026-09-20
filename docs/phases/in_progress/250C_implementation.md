# Phase 250C — The model-resolution pool is keyed by the raw make column

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-20

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

## Verification Checklist

- [ ] Per-marque pools measured before and after, all sixteen
- [ ] The four pairs that stop resolving are the cross-marque noise, named
- [ ] Honda, Kawasaki, Suzuki and Yamaha unchanged — they were complete
- [ ] 244I, 244C, 244F and 244E green, source guards included
- [ ] 250B and Gate 13 green — the electric prompts must not move
- [ ] The new test file scanned by 244G's raw-source guard
- [ ] Mutations caught
- [ ] Full regression green, 0 failed and 0 skipped
- [ ] Live junction rebuilt copy-first, before-state printed
- [ ] Roadmap row, `implementation.md` history row, `phase_log.md`
