# Phase 244E — Retrieval widening — phase log

**Status:** Planned
**Opened:** 2026-09-10

---

## 2026-09-10 — Plan v1.0 written

Opened immediately after Phase 244D's re-seed, which made a latent bug in
Phase 244C visible: `BMW + "R1200GS"` returns **1** row where `BMW` with no
model returns **50**. Resolving the model successfully makes the answer fifty
times worse — a caller who knows less about the machine gets more knowledge
about it.

The cause is in the data, not the filter. Re-seeding revealed that the corpus
holds two populations: the early Japanese/American phases wrote clean model
names, while every Track K and L phase put prose in the `model` column
(`"Liquid-cooled R-series boxers, R1200GS and all LC R models from 2013"`), and
none of those makes has a `model = 'All'` row to fall back on. **30.7% of the
corpus is unreachable by a model-equality filter.**

Ducati and Triumph avoid the bug only because their model strings resolve as
`ambiguous`, so no filter is applied. Correct behaviour arriving through a
failure to resolve is not something to rely on, and it is why the fix is a
property assertion rather than a patch to one example.

**The plan's sharpest constraint is what must NOT change.** Phase 244C's guard
bundles two claims: a CBR600RR issue must not reach an F4i, and a Kawasaki
issue must not reach a Honda. Widening requires relaxing the first. The second
is the one with a mechanic on the other end, and splitting a guard is precisely
how its strict half goes missing — so the cross-make assertion will be restated
in this phase's own guards as well, existing in two files so that editing one
cannot quietly drop it.
