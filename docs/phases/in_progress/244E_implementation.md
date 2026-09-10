# Phase 244E — Resolving a model must not shrink the answer

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-10

---

## Goal

Phase 244C's `known_issues_for_vehicle` filters to
`model = X OR model = 'All'` whenever the model resolves. Re-seeding the corpus
at Phase 244D made the consequence visible and it is backwards:

```
BMW + "R1200GS"   model resolves exactly  ->   1 row
BMW + ""          model unresolved        ->  50 rows
```

**Succeeding at identification makes the answer fifty times worse.** A caller
who knows *less* about the machine gets *more* knowledge about it.

## Why the data does this

Re-seeding exposed that the corpus has two populations. The early
Japanese/American phases wrote clean model names. Every Track K and L phase put
prose in the `model` column — `"Liquid-cooled R-series boxers, R1200GS and all
LC R models from 2013"` — and none of those makes has a single `model = 'All'`
row to fall back on:

| make | rows | prose models | `All` rows |
|---|---|---|---|
| Honda | 142 | 0 | 20 |
| Kawasaki | 140 | 0 | 0 |
| BMW | 54 | **44** | **0** |
| Ducati | 46 | **46** | **0** |
| Triumph | 55 | **55** | **0** |
| Zero | 17 | **17** | **0** |

**30.7% of the corpus cannot be reached by a model-equality filter.** For those
makes the filter matches the one row whose model happens to be a bare name, and
the `'All'` escape hatch that rescues Honda does not exist.

Ducati and Triumph escape the bug **by accident**: their model strings resolve
as `ambiguous`, so no filter is applied at all. Correct behaviour arrived
through a failure to resolve, which is not a property to rely on.

## Non-goals

- **Not fixing the vocabulary.** `make` and `model` holding prose is the root
  cause and needs its own phase with a data migration. This phase makes
  retrieval survive the data as it is.
- **Not re-ranking by relevance.** Ordering is tier then severity; no scoring.

## Logic

**Tiers, not a filter.** Rows are selected for the resolved make and labelled
with how specifically they match, then ordered most-specific first and filled
up to `limit`:

| `match_tier` | meaning |
|---|---|
| `model` | the resolved model, exactly |
| `make_wide` | `model = 'All'` — the make's own general entries |
| `make_other_model` | same make, some other model |

**Never fewer than the make-level query would return.** That is the invariant
this phase exists to establish, and it is asserted directly rather than
inferred from row counts in one example.

**Cross-make leakage stays absolutely forbidden.** Phase 244C's guard bundles
two claims — that a CBR600RR issue must not reach an F4i, and that a Kawasaki
issue must not reach a Honda. The first must now change; **the second must
not**, and it is the one with a mechanic on the other end. The guard is split
so the cross-make half stays absolute and cannot be relaxed by accident.

**Labelled, not laundered.** `_format_known_issues` renders the tier alongside
each entry, and the guidance prompt states that a `make_other_model` row
describes a *different machine of the same make*. A near-neighbour row must be
able to inform an answer without being mistaken for machine-specific evidence —
that is exactly the distinction `Grounding.CROSS_PLATFORM` already exists to
carry.

**Ordering reuses the Phase 240C severity SSOT.** Within a tier, rows order by
`SEVERITY_RANK_SQL` from `core/severity.py` — the same expression migration
053's index serves, so the ordering is index-backed rather than a sort of the
whole table, and the constant is not written twice.

## Key Concepts

- **Knowing more must never return less.** A monotonicity property, and the
  cleanest statement of the bug.
- **Precision by labelling beats precision by exclusion** when the data cannot
  support exclusion. Dropping 53 relevant rows to avoid 3 imprecise ones is a
  bad trade; declaring which is which is not.
- **Accidentally-correct is not correct.** Ducati works today only because its
  model fails to resolve.
- **A guard that bundles two claims will eventually block one of them wrongly.**

## Verification Checklist

- [ ] `BMW + R1200GS` returns no fewer rows than `BMW` alone
- [ ] The monotonicity property holds for every make in the corpus, not one example
- [ ] Exact-model rows still rank ahead of make-wide and other-model rows
- [ ] A different make's rows never appear, at any tier
- [ ] Every returned row carries a `match_tier`
- [ ] The formatter labels non-specific rows so they cannot read as machine-specific
- [ ] Within a tier, ordering is by severity rank and uses the 240C SSOT
- [ ] Phase 244C's cross-make guard still passes unmodified in substance
- [ ] Mutation: drop the tier fill → the monotonicity guard fails
- [ ] Mutation: allow cross-make rows → the leakage guard fails
- [ ] Full regression green

## Risks

- **Dilution.** Filling to `limit` with other-model rows could push a
  genuinely-specific entry out of the formatter's 12-row window. Ordering is
  most-specific-first precisely so the fill only ever occupies the tail.
- **Relaxing a leakage guard is where this goes wrong.** The 244C guard is
  being split, and splitting a guard is exactly how its strict half gets lost.
  The cross-make assertion is restated in this phase's own file too, so it
  exists in two places and cannot be dropped by editing one.
- **Silent misrepresentation.** A near-neighbour row that reaches the model
  unlabelled is worse than no row: it would license a machine-specific claim on
  another machine's evidence. The formatter change is not cosmetic and is
  guarded.
- **No production caller yet.** The guidance surface is not wired to a route,
  so this is verified by guards and a live re-run rather than in situ.
