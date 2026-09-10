# Phase 244I — The model column, and the models an entry says it does NOT cover

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-10

---

## Goal

Phase 244F gave `make` a derived key. `model` has the same disease and one that
`make` did not: **entries name models in order to exclude them.**

> `390 Adventure, 790 Adventure, 890 Adventure — as distinct from 1290 Super Adventure`
> `Hypermotard 1100 (not EVO)`
> `950 and 990 LC8 on the fiche; 1190/1290 fitment unknown, not excluded`

A junction built by naive extraction would attach these entries to the exact
machines their authors wrote them to rule out. That is worse than the gap it
closes — a mechanic acting on another model's documented fault, delivered with
the confidence of a machine-specific match.

221 of 363 distinct model values carry list or prose structure. Phase 244E
already makes those rows *reachable* (they arrive labelled `make_other_model`),
so this phase is not about reachability. It is about **precision**: an entry
that genuinely covers R1200GS should rank as this model, not as some other one.

## Step 0 findings — two changed the design, one nearly killed the phase

**1. The obvious vocabulary yields almost nothing.** Deriving model names from
clean single-value entries — the shape that worked for marques — made exactly
**4 of ~298 prose rows** gain a precise model. Models are an open vocabulary,
and the ones named in prose mostly appear nowhere as a clean value.

Applying Phase 244F's actual move — augmenting the vocabulary with clean tokens
split *out of* the list values — took it from **4 to 271**. The vocabulary that
fixes the column again comes out of the strings that broke it.

**2. Fourteen values name excluded models**, using `as against`, `as distinct
from`, `versus`, `not established`, `(not EVO)`. Extraction must stop at the
contrast marker and read only what precedes it. Verified: both KTM Adventure
entries extract their covered models and **zero excluded ones**.

**3. Substring dedup drops real models.** `"390 Adventure, 390 Adventure R,
890 Adventure"` lost *390 Adventure* because it is a substring of *390 Adventure
R*. Both are real, distinct machines. Dedup must be **position-aware** — drop a
match only when every one of its occurrences sits inside another match.

**That defect also exists in Phase 244F's `extract_marques`.** It is latent
there because no marque in the 16-value set is a substring of another, so it has
never fired. The corrected helper is shared, and 244F adopts it.

## Non-goals

- **Not editing the corpus.** As with `make`, the column keeps what the author
  wrote and the junction is derived beside it.
- **Not parsing qualifiers.** `built before the mid-2012 change` is a real
  restriction this phase does not model. Rows keep their year columns; nothing
  claims the qualifier has been understood.

## Logic

**Migration 056** adds `known_issue_models (issue_id, model)`, backfilled via the
same `post_apply` hook Phase 244F introduced.

**Vocabulary is per make.** Model names are only meaningful within a marque, and
scoping prevents one make's model matching another's text.

**Extraction order:** scope value (`All`) → no models; a clean value → itself;
otherwise strip from the first contrast marker onward, then whole-word match the
remainder against the make's vocabulary, then position-aware dedup.

**Retrieval uses the junction for the `model` tier.** Phase 244E's tiers,
ordering and monotonicity invariant are unchanged — a row simply has more ways
to qualify as `model` rather than `make_other_model`.

## Key Concepts

- **A corpus that says "not X" must never be indexed as X.** The one failure
  here with a person on the other end.
- **Reachability was already solved; this is precision.** Phase 244E's fallback
  means a bad extraction has no upside to trade against.
- **Position-aware dedup.** Containment is a property of occurrences, not of
  strings.
- **The vocabulary comes from the strings that broke the column** — 4 rows
  versus 271 is the whole difference between the two derivations.

## Verification Checklist

- [x] An entry naming an excluded model does not reach that model
- [x] All fourteen contrast values are checked individually, not sampled
- [x] `390 Adventure` and `390 Adventure R` both survive dedup when both appear
- [x] A model appearing only inside a longer one is dropped
- [x] Vocabulary is per-make; one make's model never matches another's text
- [x] Prose rows gain a precise model where one is genuinely named
- [x] `All` stays a scope and is never a model
- [x] Phase 244E's monotonicity invariant still holds corpus-wide
- [x] Phase 244F adopts the corrected dedup
- [x] Mutation: drop contrast handling → an exclusion guard fails
- [x] Mutation: naive substring dedup → the 390 Adventure guard fails
- [x] Full regression green

## Risks

- **Over-extraction, and it is not symmetric with 244F.** A wrong marque is
  usually obvious to a technician; a wrong *model* of the right marque looks
  entirely plausible and will be acted on. Every rule here is conservative:
  whole-word, make-scoped, contrast-truncated, and silent when unsure.
- **The contrast list is a heuristic.** It covers the fourteen values present
  today. A future phrasing it does not know would extract from text it should
  not, so the guard enumerates all fourteen rather than sampling, and any new
  contrast phrasing added to the corpus should be added here.
- **`not excluded` is a double negative** — `1190/1290 fitment unknown, not
  excluded` means *unknown*, and truncating at `not` correctly yields nothing
  for the tail. Pinned as its own case because a cleverer parser would get it
  wrong.

---

## Deviations from Plan

**The plan's exclusion mechanism was wrong, and this phase's own guard proved
it.** v1.0 specified truncation: cut everything from the first contrast marker
onward. A parametrised guard over every contrast phrasing found the case that
breaks:

```
"390 Adventure; 390 Duke not established"   ->  kept 390 Duke
```

The excluded model **precedes** the marker there, so truncation leaves it
standing. Exclusion is not positional, it is **clause-scoped**: negated
parentheticals are removed, the value is split into clauses, and any clause
carrying a contrast marker is dropped whole. Verified corpus-wide — **zero**
indexed models are absent from the covered part of their source value.

Yield moved 258 → 254 with the stricter rule, which is the right direction: four
rows lost to conservatism against a class of false attribution removed.

**My fixture was unrepresentative, for the second phase running.** Three
mutations escaped — single-character tokens, unbalanced brackets, scope phrases
— because the hand-built fixture lacked shapes the real corpus has: `"... and R"`
splitting to a bare `R` that would match almost any text, and a comma inside
parentheses tearing a year qualifier in half. Adding those shapes caught all
three, and one exposed a defect nothing had flagged: **`2018+` was entering the
vocabulary as a machine.** Bare years and year ranges are now rejected.

Phase 244F had the same problem with Triumph and Moto Guzzi. Worth stating as a
finding in its own right: **a fixture built from imagination tests the corpus you
expected, not the one you have.**

**One guard passed for the wrong reason and was rewritten.** The unbalanced-bracket
mutation survived even after the fixture gained a bracket case, because the
fragment was 30 characters and got rejected on *length* before the bracket check
ran. The fixture value was shortened so the check under test is the one that
fires.

**A latent defect in Phase 244F was fixed here.** Its `extract_marques` used
naive substring dedup, which discards a shorter name whenever a longer one
contains it. Harmless for marques — none in the 16-value set is a substring of
another — and fatal for models, where `390 Adventure` loses to `390 Adventure R`
though both are named and both are distinct machines. The corrected
position-aware helper lives in `marques.py` and both callers use it.

## Results

| Metric | Value |
|--------|-------|
| Prose rows gaining a precise model | **254 of 286** (4 under the naive derivation) |
| Excluded models indexed | **0**, corpus-wide |
| Junction rows | 1,674 across 556 distinct models |
| Vocabulary | derived, per-make, no hard-coded model list |
| `model` column rewrites | **0** |
| Guards | 34 |
| Mutations run / caught | 7 / 7 (three after repairing the fixture) |
| Regression | **6280 passed / 0 failed** (baseline 6246; +34 guards). First run red on one missed schema pin |

**Key finding: a corpus that says "not X" must never be indexed as X, and the
obvious implementation gets that wrong in a way testing at the value level does
not reveal.** Truncation looks correct against the examples anyone would pick —
they all put the exclusion last. It fails on the one phrasing where the excluded
name comes first, and that phrasing is in the corpus. Enumerating every contrast
value rather than sampling is what found it.

## Follow-up recorded

The contrast vocabulary is a closed list covering the fourteen phrasings present
today. A new phrasing would extract from text it should not, so the guard
enumerates all fourteen rather than sampling — a gap shows up as a failure rather
than as a silent mis-index. Any new contrast wording added to the corpus must be
added to `CONTRAST`.
