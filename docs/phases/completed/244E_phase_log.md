# Phase 244E — Retrieval widening — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-10 | **Closed:** 2026-09-10
**Repo:** https://github.com/Kubanjaze/moto-diag

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


---

## 2026-09-10 — Built

Retrieval now tiers rather than filters. Rows are selected for the resolved
make and labelled `model` / `make_wide` / `make_other_model`, ordered
most-specific first and filled to the caller's limit. `BMW + "R1200GS"` goes
from **1 row to 25**, and the exact-model row still ranks first.

**Asserted as a property, not an example.** Across the live corpus — 362
make/model pairs over 26 makes — there are **zero** cases where supplying a
model returns fewer rows than omitting it. That mattered because the original
bug was invisible for Honda and fatal for BMW; a single worked example would
have proved nothing.

**The same defect from Phase 240C, reproduced by me in a new file.** Adding the
severity `ORDER BY` made a 244C guard return `[]`. The fixture lacked a
`severity` column, the query raised, and a blanket `except Exception` turned a
malformed query into "no known issues found" — exactly the
`advanced/recall_repo.py` failure where a dropped `ORDER BY` keyword was
swallowed and a lookup reported empty instead of erroring. Especially pointed
here: Phase 244C exists to make an unmatched name distinguishable from an
undocumented machine, and this made a *broken query* indistinguishable from
both. The catch is now narrow — a missing table is an empty corpus, a missing
column is a bug and raises. `known_makes` and `known_models` got the same
treatment; they had been throwing outright on a fresh database, so best-effort
never reached the case it was written for.

**A bundled guard was split rather than edited.** Phase 244C asserted in one
test that a CBR600RR entry must not reach an F4i and that a Kawasaki entry must
not reach a Honda. Widening relaxes the first; the second is the one that puts
wrong work in a mechanic's hands. It now exists in both files, because splitting
a guard is how its strict half quietly disappears.

**Precision by labelling, not by exclusion.** The formatter tags each entry with
its tier and names the other model when there is one, and the guidance prompt
states that a same-make/different-model entry is `cross_platform` at best.
Verified live on the original recording: the model cited *"Stator failure
diagnosis and replacement — all Honda models [this make, all models]"* and
grounded it as `cross_platform`, not `machine_specific`. The label reaches the
reasoning and constrains the claim.

16 guards, 6/6 mutations caught, F9 lint clean.

**Not fixed, and still the root cause.** `make` and `model` hold prose and
multi-make lists. LiveWire and Damon resolve to nothing at all — all 24 LiveWire
rows are tagged `"Harley-Davidson, LiveWire"`, leaving Phase 243's entire output
unreachable. This phase makes retrieval survive that data; it does not repair it.
