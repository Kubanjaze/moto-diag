# Phase 255C — The junction stores names the tier query cannot match

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-22

> **Step 0 below is unchanged from the committed draft** (`0d80bc6`) and is
> not re-run. The plan begins at "Decisions taken".

---

## S0-0. What 244I locks in — audited first, because it constrains the fix

Eight constraints, from `tests/test_phase244I_model_vocabulary.py`. Three of
them rule out approaches that would otherwise look obvious.

| pinned by | constraint | what it means for 255C |
|---|---|---|
| `test_the_model_column_is_never_rewritten` | `known_issues.model` is never rewritten; the junction is **derived** | **A fix may not normalise by editing the column.** It must act at extraction. |
| `TestAnExcludedModelIsNeverIndexed` (6 tests) | entries name models **in order to exclude them**, and the junction is built only from the part that states what IS covered | A normaliser runs on the **covered part, after exclusion parsing** — never on the raw column. Normalising raw text could index a model the row exists to exclude. |
| `test_the_vocabulary_is_scoped_per_make` · `test_a_model_from_another_make_does_not_match` | the vocabulary is per-make | Normalisation must be **per-make**, or two marques' machines can merge. |
| `test_a_rebuild_is_idempotent` | rebuilding the junction twice changes nothing | Any alias the fix adds must **converge**, not accumulate. |
| `test_the_vocabulary_is_derived_not_hardcoded` · `test_known_models_returns_the_vocabulary_not_raw_column_values` | no hardcoded alias list | **No lookup table of spellings.** The normaliser is a function, not data. |
| `test_no_single_character_tokens` · `test_no_bare_year_tokens` · `test_no_unbalanced_bracket_debris` | the vocabulary rejects debris | These filters exist and **two debris strings still get through** — see S0-3. |
| `test_the_migration_backfills_in_its_own_transaction` | migration 056's `post_apply` is `models:rebuild_model_index` | 255C's migration rebuilds the same way, in its own transaction. |
| `test_monotonicity_still_holds` | knowing more must never return less | Satisfied — see S0-4. Nothing is lost; rows change **tier**. |

## S0-1. The roadmap's framing is wrong, and the correct one is worse

The 255B roadmap row — which I wrote — says the junction stores
marque-prefixed model strings the tier query cannot match. **Measured, that
is not the defect.**

The tier query is exact equality:

```sql
WHEN ? IS NOT NULL AND EXISTS (
    SELECT 1 FROM known_issue_models
    WHERE known_issue_models.issue_id = known_issues.id
      AND known_issue_models.model = ?      -- the RESOLVED model
) THEN 0
```

And the resolver returns **two different canonical forms for one machine,
both `exact`, both confidence 1.0**, depending on what the caller typed:

```
typed 'PCX 150'       -> resolved 'PCX 150'        method=exact conf=1.0
typed 'PCX150'        -> resolved 'PCX 150'        method=exact conf=1.0
typed 'Honda PCX150'  -> resolved 'Honda PCX150'   method=exact conf=1.0
typed 'Honda PCX 150' -> resolved 'Honda PCX150'   method=exact conf=1.0
```

The junction holds **seven** strings for the PCX family: `Honda PCX125`,
`Honda PCX150`, `PCX`, `PCX 150`, `PCX125`, `PCX150`, `PCX160`.

**So the defect is bidirectional.** A row indexed as `Honda PCX150` reaches
tier 0 only from a marque-prefixed spelling; a row indexed as `PCX 150` only
from a bare one. One machine, two disjoint tier-0 sets, chosen by how the
caller happened to type the model.

## S0-2. The census — 50 machines are split across spellings

| | |
|---|---|
| junction rows (live, post-255B) | **2,433** |
| distinct model strings | **706** |
| groups that are one machine under several spellings | **50** |
| junction strings inside those groups | **101** |
| of those 50, groups whose spellings resolve to **more than one canonical** | **48** |

The largest splits:

```
['Honda PCX150', 'PCX 150', 'PCX150']      ['1290 Super Duke R', 'KTM 1290 Super Duke R']
['250', 'KTM 250']                          ['390 Duke', 'KTM 390 Duke']
['790 Duke', 'KTM 790 Duke']                ['946', 'Vespa 946']
['Agility', 'Kymco Agility']                ['Agility 125', 'Kymco Agility 125']
['Agility 50', 'Kymco Agility 50']          ['Aprilia RSV4', 'RSV4']
```

## S0-3. Stripping the marque prefix is the WRONG fix, and the numbers say so

The obvious repair — strip the marque and re-index — would break 98 rows to
fix none.

Of the **100 distinct marque-prefixed junction strings**, resolved against
their own marque:

| | |
|---|---|
| **98** | the stored, prefixed form **IS** the resolver's canonical. Stripping breaks them. |
| **0** | stripping yields the canonical. |
| **2** | neither — prose debris: `'Piaggio Group marques only'`, `'Triumph siblings that agree'` |

The resolver actively **adds** the marque for some models — `SR Max` →
`Aprilia SR Max`, `Shiver 750` → `Aprilia Shiver 750`, method `abbreviation`.
For those, the prefixed junction entry is correct and the bare one is the
anomaly. The prefix is not a defect; **the inconsistency is.**

The two debris strings are a separate, smaller finding: they pass 244I's
single-character, bare-year and bracket filters, and they are not models.

## S0-4. The trade, measured — and nothing is lost

Simulated on a copy of the live database by unifying all 50 split groups
(**516 junction rows added**, 2,433 → 2,949):

| Honda PCX 150 | live | unified |
|---|---|---|
| rows retrieved | 166 | 166 |
| rows surviving the filter | 166 | 166 |
| at tier `model` | **2** | **11** |
| at tier `make_wide` | 20 | 20 |
| at tier `make_other_model` | **144** | **135** |

**Nine rows move up a tier. No row is added or removed.** The seven-in /
seven-out in the prompt is the 244S cap of twelve re-cutting a re-ranked
list, not the filter excluding anything — which is why 244I's monotonicity
pin is satisfied: knowing the model returns *more* at tier 0, never fewer
rows overall.

**In** (7): the scooter-CVT rows — drive-belt vocabulary, roller wear limit,
clutch side, belt width, CVT symptom vocabulary, fault codes, kickstart.
**Out** (7): generic Honda rows — brake fluid, coolant hose, ground
corrosion, HISS immobilizer, starter clutch, starter relay, tyre age.

## S0-5. The normaliser — positive control in both directions, zero collisions

A per-make key of `lower(remove spaces(strip own marque))`:

**Must merge, and does:**

```
'Honda PCX150'     vs 'PCX 150'      -> merged
'Kymco Agility 50' vs 'Agility 50'   -> merged
'Vespa 946'        vs '946'          -> merged
```

**Must NOT merge, and does not:**

```
'PCX 150'    vs 'PCX 125'       -> kept apart      'PCX'      vs 'PCX 150'   -> kept apart
'Agility 50' vs 'Agility 125'   -> kept apart      'Buddy 125' vs 'Buddy 170i' -> kept apart
'390 Duke'   vs '390 Adventure' -> kept apart      'LX 50'    vs 'LX 125'    -> kept apart
```

**Cross-marque collisions: 0.** No normalised key carries two different
explicit marques — checked across all 706 strings. (An earlier run of this
check reported 39 of 50 "collisions"; it was reading each issue's own
**make column**, which is many-valued on a cross-make row, rather than the
marque named by the model string. The corrected test is the one above.)

---

# Plan (v1.0)

## Decisions taken

Seven, from the operator on 2026-09-22, after Step 0 was reviewed.

| # | decision |
|---|---|
| 1 | **The resolver is the fix.** One canonical identity per machine regardless of input spelling. Extraction calls the resolver and has **no normaliser of its own**. Canonicalisation runs **after** 244I's exclusion parsing, never on raw text. No alias table. |
| 2 | **The junction stores one canonical per row.** Never every alias. |
| 3 | **Canonical is a `(make, model)` PAIR.** The model never carries the marque; the tier query matches on both. |
| 4 | The two debris strings are a **244I extraction-filter leak**, fixed at extraction with a planted-prose positive control, own commit. No hand edits to the junction. |
| 5 | Enumerate every consumer of canonical strings before v1.0, with a positive control, and report which break. |
| 6 | Junction rebuild by migration with rollback; a before/after tier table per fixture machine; a guard on canonical consistency. |
| 7 | Commit messages via quoted heredoc. Added to `CLAUDE.md`. |

## D0. Why the resolver embeds the marque in some canonicals — answered

**It does not, by design. It has no rule about marques at all.**

`vehicle_resolver.known_models()` returns `models.model_vocabulary()`, which
244I derives from the corpus's own `model` column. The resolver's canonical
set **is** that vocabulary. So:

```
Aprilia vocabulary:  ['Aprilia SR Max', 'Aprilia Shiver 750', 'SRV', 'SRV 850',
                      'Shiver', 'Shiver 900']
Honda vocabulary:    ['Honda PCX125', 'Honda PCX150', 'PCX', 'PCX 150',
                      'PCX125', 'PCX150', 'PCX160']
```

`Aprilia SR Max` is canonical because a row author typed the marque into the
model column; `Shiver 900` is canonical because another did not. **Same make,
both conventions, no rule distinguishing them.** There is nothing to
preserve — the inconsistency is the whole of the phenomenon.

**The counter-case, checked as the operator asked.** Only **2** of 706
junction strings lead with a marque that is not among their row's makes, and
both are the known debris: `'Piaggio Group marques only'` and
`'Triumph siblings that agree'`. `LiveWire One` leads with `LiveWire`, and
LiveWire **is** one of its row's makes. **So the `(make, model)` pair form
is safe, and no case blocks it.**

## D1. The mechanism 250C already built, and 255C carries through

`known_issue_models` is `(issue_id, model)` — **no make column.** But
`models.vocabulary_from_conn` already attributes every model token to a
marque, in three documented rungs, and explicitly handles the case where a
marque is also a model line:

> *"A token that **names** a marque belongs to it, unless the two marques are
> the same family (`marque_families`): 'LiveWire' is a marque and a
> Harley-Davidson machine."*

**That attribution is computed and then discarded when the junction is
written.** 255C does not invent a normaliser. It carries 250C's existing
attribution into the junction and into the tier query.

## D2. What changes

1. **`known_issue_models` gains a `make` column**, so a junction row is a
   `(issue_id, make, model)` triple. The make is 250C's attribution, not the
   row's make column.
2. **The model side of the vocabulary drops the marque prefix**, so a
   machine has one canonical model string per make. `Aprilia SR Max` becomes
   `(Aprilia, SR Max)`; `Honda PCX150` and `PCX 150` both become
   `(Honda, PCX 150)`.
3. **The tier query matches the pair:**

```sql
WHEN ? IS NOT NULL AND EXISTS (
    SELECT 1 FROM known_issue_models
    WHERE known_issue_models.issue_id = known_issues.id
      AND known_issue_models.make  = ?
      AND known_issue_models.model = ?
) THEN 0
```

4. **Extraction calls the resolver**, and has no normaliser of its own
   (decision 1). Canonicalisation happens on the **covered part**, after
   244I's exclusion parsing.

## D3. The 244I constraints, and how each is met

| constraint | how D2 meets it |
|---|---|
| the model column is never rewritten | Nothing writes `known_issues.model`. The junction is derived, as it already is. |
| an excluded model is never indexed | Canonicalisation runs on the covered part only, **after** exclusion parsing. A test plants `"X as distinct from Y"` and asserts Y is absent under the pair form too. |
| the vocabulary is scoped per make | The pair form makes this structural rather than conventional. |
| a rebuild is idempotent | One canonical per row means the rebuild converges by construction. Pinned. |
| the vocabulary is derived, not hardcoded | No alias table (decision 1). The canonical is a function of the corpus. |
| debris filters | Replaced by a **positive gate** at extraction (D5 amended). The blacklists are the defect, not an incomplete list. |
| the migration backfills in its own transaction | 255C's migration does the same, `post_apply` → `rebuild_model_index`. |
| monotonicity: knowing more never returns less | Measured in Step 0 — retrieved and kept both unchanged at 166; nine rows move **up** a tier. Pinned as a tier table (D6). |

## D4. Consumers — enumerated, with a positive control

AST sweep over **569 Python files** for every producer/consumer of a
canonical model string and the three tables that store one. **Positive
control:** a planted `resolve_vehicle` caller was found, then removed.

**Unaffected — and the first one is the important negative result:**

* **The Phase 255 transmission lookup does not consume canonical strings.**
  It never calls `resolve_vehicle` or `known_models`; it matches its own
  `canonical` + `aliases` against raw input via `_alias_match`. **Zero of its
  50 entries have a marque-prefixed canonical.** The resolver change does not
  reach it.
* **Mobile is a producer of raw input, not a consumer.**
  `NewVehicleScreen.tsx:107` sends `model: model.trim()`. No canonicalisation
  exists on the mobile side.
* **The four retrieval doors need no change.** `predictor`, `videos`,
  `diagnose` and `priority_scorer` all pass what they hold into
  `rows_for_machine`; the pairing happens inside `known_issues_for_vehicle`.

**Affected:**

* **16 of the 100 marque-prefixed canonicals are pinned as literals** — two
  in source (`models.py` / `marque_families.py` pin `BMW S 1000 R`;
  `migrations.py` pins `SYM Symba` in Phase 255B's rollback SQL) and the rest
  across eleven test files, concentrated in `test_phase255_transmission_axis`,
  `test_phase255B_twist_and_go`, `test_phase250C_model_vocabulary` and
  `test_phase256_chokepoint`. Each is updated to the pair form in the commit
  that changes the vocabulary, not before and not after.
* **`retrieval_withheld`** is keyed on `(make, model, provenance, purpose)`
  and records the string the door passed, so rows accumulated under an old
  canonical stop accumulating under the new one. **Live impact is 10 rows,
  all `unknown` provenance.** It re-accumulates. Recorded, not migrated —
  the table is diagnostics, and migrating a counter would assert a continuity
  the counter does not have.

## D5 (amended 2026-09-22). A positive gate at extraction — and three wrong counts on the way to it

**The original D5 said "the two debris strings". The number was wrong three
times, each time from an under-scoped search, and each time it moved the
same direction.**

| count | how it was reached | why it was wrong |
|---|---|---|
| **2** | Step 0 searched for junction strings whose **leading marque** was not their row's make | Seven of the next nine do not lead with a marque at all. Same family as the V-matic miss: the search could not find what it was looking for. |
| **9** | shape heuristics over a hand-picked pattern list | Found what I thought to look for. A pattern list is a blacklist by another name. |
| **85** | the gate run over **all 706** junction strings — the whole-corpus negative control the operator required | This is the first count defined by a **rule** rather than by a search, which is why it is the first one that holds. |

**The lesson is the method, not the number.** Two searches and a heuristic
each returned a subset and each read as complete. Defining the set by a rule
and running it over the whole corpus is what ended it — and that is the same
correction the evidence-discipline rule already demands for negative claims,
arrived at from the other direction.

### Why the decision-6 guard cannot close this class

The guard as specified — *every junction string resolves to its own
machine's canonical* — fires on **0 of the debris strings**, and it is
circular. 244I derives `model_vocabulary` **from the model column**;
extraction wrote `'000 km'` into the junction, so the vocabulary contains it,
so `resolve_vehicle('Ducati', '000 km')` returns `'000 km'` by exact match.
**Debris defines its own canonical.** A check satisfied by construction on
exactly the strings it was written for.

Guard 2 — *no two junction strings for one machine* — fires on 52 groups
covering 105 strings and catches **0** debris, because each debris string
appears once. **The two guards close one class between them: spelling-split.
They are kept for that, and they do not close debris.**

The common cause, and the reason the four blacklist fixes were dropped:
**extraction has no positive gate.** `CONTRAST`, `_PROSE_WORD`,
`_NEGATED_PAREN` and `is_scope` are all blacklists, and every root cause
found was a gap in one. A fifth gap lands silently.

### The gate

**Rule: a token is rejected when it contains a bare lowercase word and
carries no code token.** A bare lowercase word is one that does not begin
with a capital or a digit and is not alphanumeric-mixed; parentheticals are
stripped first, so `'R-series (airhead)'` is judged on `'R-series'`. A code
token is `[A-Z]{1,4}\d{2,4}`, a bare 3–4 digit number, `nV`, or `Vn`.

*(The operator's phrasing was "no code token, no capitalised proper noun".
The rule above is what produces exactly the set below — `'Electric
motorcycles'` carries a capital and is still debris — so the rule is stated
here as implemented rather than as described.)*

**What it admits:** every model designation the corpus uses — `PCX 150`,
`F-series`, `R-series (airhead)`, `250`, `125`, `Brutale 800`,
`Super Cub C125`, `390 Adventure R`, `XC155 / SMAX`, `S 1000 RR by type
code` — and every group (B) string.

**Scope: group (A) only — 57 strings, 105 junction rows.** Strings with no
code token and no designation: `'Electric motorcycles'` (10 rows), `'as this
corpus names them'` (5), `'Desmosedici Stradale engines'` (5), `'BMS logs'`
(4), down to `'year'`, `'location'`, `'related'`, `'independent'`,
`'per handbook'`.

**Negative control is the whole corpus:** run over all 706 junction strings,
the gate rejects **exactly** those 57 and admits the other 649, group (B)
included. The 57 are pinned as a set; a fifty-eighth fails the suite naming
the string, in `KNOWN_SELF_EXCLUDING` style.

**Loud means a failing test, not a seed-load crash.** A gate cannot know
whether a rejection is legitimate, so it never crashes the loader —
operator's correction, 2026-09-22.

### Group (B) is not 255C's

28 strings carrying a code token but reading as prose. **No shape rule
separates them**, and the pair that shows why is `'R1200 hexhead'` — an
engine-family designation 244I's vocabulary is built to carry — against
`'2020 service manual'` — debris. Both are "number plus lowercase words".

Telling them apart is a question about **what the corpus means by a model**,
which is 244I semantics, not spelling identity. **Filed on the
general-applicability ticket with that pair as the example. Group (B)
strings stay exactly as they are today.**

## D6. Verification

* **The tier table, per fixture machine, before and after.** Step 0's
  measurement becomes the pinned shape: a PCX 150 goes `model` 2 → 11,
  `make_other_model` 144 → 135, **retrieved and kept unchanged at 166**. A
  machine per marque family, plus a non-CVT control.
* **Guard 1 — no junction string resolves to a different canonical than its
  own machine.** For every `(issue_id, make, model)`, resolving that pair
  returns that pair.
* **Guard 2 — no two junction strings for one machine.** The 50 split groups
  become 50 single entries; a fifty-first split fails the suite.
* Both guards broken on purpose and seen to fail.
* `COLLECTED_TEST_FLOOR` raised in the commit that adds the tests.

## Scope

1. `known_issue_models` gains `make`; the tier query matches the pair (D2).
2. Extraction calls the resolver; the model vocabulary drops the marque (D1, D2).
3. The two debris strings, own commit, planted-prose control (D5).
4. Migration with rollback; junction rebuilt by `post_apply` (D3).
5. The 16 pinned literals updated with the vocabulary change (D4).
6. Two guards, a tier table, a raised test floor (D6).

## Non-goals

* **No alias table.** The canonical is a function of the corpus, not data.
* **No change to the transmission lookup.** It does not consume canonicals (D4).
* **No migration of `retrieval_withheld`.** 10 rows of diagnostics; it re-accumulates.
* **No hand edits to the junction.** Everything through extraction and rebuild.
* **No change to `known_issues.model`.** 244I pins that it is never rewritten.
* **No mobile change.** Mobile sends raw text and always has.

## Risks

| risk | mitigation |
|---|---|
| Canonicalising before exclusion parsing indexes a model the row exists to exclude | D3 — it runs on the covered part only, with a planted `as distinct from` fixture asserting the excluded model stays absent |
| Dropping the marque merges two marques' machines | Step 0 measured **zero** cross-marque collisions across all 706 strings; the pair form makes the make structural, and Guard 1 pins it |
| A pinned literal is missed and a test asserts an old canonical | D4's enumeration is AST-based with a positive control; the 16 are named and change in one commit |
| The tier change is read as rows being lost | Retrieved and kept are unchanged at 166 and the tier table shows it; the twelve-row prompt change is the 244S cap re-cutting a re-ranked list |

## D7 (2026-09-22). The fork on single-token models, and the measurement that invented it

Building D2 surfaced a case the plan had not decided: **a model name that is a
single token also present as a marque or a common word.** `ONE` is the
specimen — LiveWire's model, and an English word.

Two branches were drafted. Both were rejected by the operator, and correctly:
each kept or reintroduced the marque inside the model string, which
**decision 3 forbids** — the model never carries its marque. The fork was
then reframed as an *extraction* problem rather than a canonical-form one,
and a mechanism was tried: admit a single-token model only when it appears
**adjacent to its marque** in the source string.

It was measured before committing, as instructed. **It lost 457 legitimate
rows across 108 models.** Named, not summarised: `SR` 33 → 1, `DS` 28 → 1,
`Experia` 26 → 0, `DSR` 26 → 2, `FX` 20 → 1, `Alpinista` and `Mulholland`
16 → 0 each, and `Grom`, `Thruxton` and `Speedmaster` among the rest. The
operator's standing instruction — *name it and stop, don't reach for a list*
— was followed, and adjacency was stripped out.

### The measurement that invented the problem

Adjacency was a remedy for a defect that did not exist. The "32 false `One`
rows" that motivated it came from **reading the row TITLES instead of the
model columns that produced them.** Forty-two model columns literally contain
the string `LiveWire ONE`. A bare `One` in the junction was the correct
canonical on all forty-two.

This is the same class as every census error of the week — the 2 → 9 → 85
debris counts, the 247-files-quoted-as-172-documents, the F132 table read off
a corrupted database. The rule it yields is **check what produced the
number, not what the number sits next to**, and it is on the CLAUDE.md
instance list under that name.

### Resolution

Decision 3's plain rule stands with nothing added. `One` stays bare and is
right on all 42 rows; `Zuma` collapses against `Zuma 125` by containment.
`_stands_alone` and `_is_single_token` are gone. The **per-marque dedupe
restructuring is kept** regardless: under the pair form `dedupe_contained`
must compare within one make, which is correct whether or not a cross-make
collision exists in today's corpus. The identity-key fallback was not needed.

### The junction, decomposed

| quantity | rows |
|---|---|
| OLD `(issue, model)`, pre-255C | 2,433 |
| NEW distinct `(issue, model)` | **2,397** — below the ~2,412 ceiling set for the fork |
| NEW total `(issue, make, model)` | **2,795** — +398 is the marque dimension, structural, not growth |

Both figures moved by +4 after bug fix #5 below, which was found by the full
regression after the first commit landed at 2,393 / 2,791. The ceiling still
holds.

## Bug fixes found while building

Each is a real defect in shipped code, found by a test that was written to
fail first.

* **#1 — a comma inside a thousands separator split a figure in half.**
  `_model_tokens` split on `,` before protecting `1,200`. Own commit
  (`8fd680f`), dated entry, planted control.
* **#2 — migration 065's `post_apply` wrote the 3-column junction at v65.**
  `rebuild_model_index` writes the pair form, but 065 runs while the table is
  still 2-column, so **any database at 64 or 65 could not migrate.** Fixed by
  reading `PRAGMA table_info(known_issue_models)` and writing 2 or 3 columns
  to suit the shape in front of it.
* **#3 — the schema-56 degradation path crashed on placeholder count.**
  The tier query gained a binding for the pair, but the make-only fallback
  still passed six parameters into five placeholders: *"Incorrect number of
  bindings"*. Fixed with a separate `make_only_params`. The path is reachable
  on any database that has not taken migration 057, which is why it is a
  crash and not a cosmetic mismatch.
* **#4 — migration 065's rollback restored a junction string no rebuild
  produces.** Its `INSERT OR IGNORE` carried the literal `'SYM Symba'`, the
  form the *model column* spells. 255C canonicalises the junction, where that
  machine is `'Symba'`. The round trip landed one row short — 2,385 → 2,384,
  `(164, 'Symba')` lost and `'SYM Symba'` left behind — and the baseline was
  itself inflated by the same spurious insert. Fixed to the canonical form,
  with the reasoning in the SQL comment so the next canonicalisation finds
  it. **Junction literals are written in the form the extractor produces,
  never the form the column spells.**
* **#5 — the plain-model early accept bypassed canonicalisation entirely, and
  indexed three rows as nothing.** Found by the **full regression**, after the
  four-file run and the first commit were both green — two failures the
  narrow run could not have produced. 244I short-circuits a delimiter-free
  value straight into the index, skipping `covered_part` *and* the
  vocabulary, so the raw column text became the junction entry. Under 255C
  that is the defect itself. Worse, the pair form's version of the accept
  tested **exact** membership, and `Energica Experia` is not in a pool that
  now holds `Experia` — so rows 868, 1290 and 1307 were indexed as
  **nothing at all**, and an Experia could never reach tier 0 on the row that
  names it. Decision 1 says extraction has no normaliser of its own; an
  accept that returns the input unchanged is a second normaliser, and the
  worst kind. Removed. Measured over the corpus: **985 rows unchanged, 18
  changed, none lost** — three rescued from total loss, fifteen trading a raw
  string for the canonical (`S1000XR (2015-2019)` → `S 1000 XR`,
  `Road King (FLHR)` → `Road King`, and `R1150/R1200 (Integral ABS)` → both
  `R1150` **and** `R1200`, one row reaching two machines it always named).
  The gate stays at vocabulary construction, where a name is first admitted.
* **#6 — `extract_models` was left orphaned, still emitting the old defect.**
  209B's orphan pin caught it: the pair form superseded its one `src/`
  caller, leaving a public function referenced by nothing but its own tests.
  It was **deleted, not allowlisted** — its plain-model branch returned the
  raw value, so it disagreed with the pair form on exactly the three rows
  above, and every disagreement was a marque-prefixed string. A superseded
  function that still emits the defect its replacement removes is a loaded
  gun for the next caller. 244I's four assertions are about exclusion
  parsing, so they project the pair form and test the same thing.

## Deviations from plan

Added at close-out of Phase 255D, whose `closeout` check found this section
missing. It is written from what the phase log records, not reconstructed
from memory.

1. **The single-token fork was not anticipated by v1.0.** `ONE` is
   LiveWire's model and an English word, and v1.0 had no rule for it. Two
   drafted branches were rejected, a marque-adjacency mechanism was built,
   measured at **457 legitimate rows lost across 108 models**, and stripped
   out. Decision 3's plain rule stood with nothing added. See D7.
2. **Three bug fixes (#5, #6, #7) were found after the plan's scope was
   written**, two of them by the full regression after a narrow run and a
   commit were both green, and #7 by the operator's terminal check.
   `extract_models` was **deleted** — a public function removal that v1.0
   did not scope.
3. **The first three commits were made on `master`**, against the
   phase-branch convention every prior phase follows. Corrected mid-phase:
   the branch was created at the tip and local `master` rewound to the
   pushed v1.0. Nothing pushed was discarded.
4. **D4's "every consumer" enumeration was scoped to `src/`** and missed a
   canonical pinned in a test — a seventeenth where sixteen were named.
   Filed as **F136**.
5. **The plan claimed group (B) was "filed on the general-applicability
   ticket" and it was not.** The claim was written; the entry never existed.
   Found at close-out and filed properly as **F135**.
6. **The first deploy verification table was not like-for-like.** Its
   "before" column ran 255C's code against the pre-255C schema — the
   degradation path. Re-measured from a worktree at `3a5fbdb` against the
   pre-deploy backup, which changed the story: Grom and Damon HyperSport
   were **flat**, not gains, and Energica Experia was **26 → 27**, not
   0 → 27.
