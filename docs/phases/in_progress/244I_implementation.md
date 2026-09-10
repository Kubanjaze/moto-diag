# Phase 244I — The model column, and the models an entry says it does NOT cover

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-10

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

- [ ] An entry naming an excluded model does not reach that model
- [ ] All fourteen contrast values are checked individually, not sampled
- [ ] `390 Adventure` and `390 Adventure R` both survive dedup when both appear
- [ ] A model appearing only inside a longer one is dropped
- [ ] Vocabulary is per-make; one make's model never matches another's text
- [ ] Prose rows gain a precise model where one is genuinely named
- [ ] `All` stays a scope and is never a model
- [ ] Phase 244E's monotonicity invariant still holds corpus-wide
- [ ] Phase 244F adopts the corrected dedup
- [ ] Mutation: drop contrast handling → an exclusion guard fails
- [ ] Mutation: naive substring dedup → the 390 Adventure guard fails
- [ ] Full regression green

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
