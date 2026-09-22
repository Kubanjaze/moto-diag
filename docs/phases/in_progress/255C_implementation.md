# Phase 255C — The junction stores names the tier query cannot match

**Version:** DRAFT (Step 0 only — NOT v1.0) | **Tier:** Standard | **Date:** 2026-09-22

> Step 0 findings only. No plan, no decisions, no scope. Committed at this
> stage so the measurements live in the repo rather than in a transcript.

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

## Not decided here

Whether the fix belongs in extraction, in the resolver, or in both; whether
the junction stores one canonical per machine or every alias; what happens
to the two debris strings; and whether the resolver returning two `exact`
canonicals for one machine is 255C's to fix or its own defect. **All of that
is v1.0, and v1.0 is not written until Step 0 is reviewed.**
