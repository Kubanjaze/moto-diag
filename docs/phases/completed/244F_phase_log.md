# Phase 244F — Marque vocabulary + make junction — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-10 | **Closed:** 2026-09-10
**Repo:** https://github.com/Kubanjaze/moto-diag

---

## 2026-09-10 — Plan v1.0 written

Third phase in a chain that started with a technician asking where a leak was
coming from. `known_issues.make` is one free-text column doing four jobs: a
marque, a list of marques, a scope phrase, and in one row a full sentence of
findings — `"BMW and Ducati have listed adjustments; KTM, Triumph, Aprilia,
Moto Guzzi have none"`.

**The cost is specific: LiveWire and Damon are not queryable makes at all.** All
24 LiveWire rows sit inside `"Harley-Davidson, LiveWire"` and all 10 Damon rows
inside a five-marque string, so `make = 'LiveWire'` returns nothing while the
corpus documents the machine. Phase 243 researched and wrote that content and
none of it can be retrieved.

**Step 0 found the whole problem is 12 strings over 38 entries** — small enough
to read individually, which was worth doing: three of them are not lists at all.
`All makes` and `All European makes` are genuine scope statements about vendor
tooling and valve-train work, and the sentence is a finding summary that
happened to be pasted into the make column. Treating any of the three as a
delimiter-separated list would have produced nonsense.

**The vocabulary is derivable, which is the finding that makes the phase
tractable.** Splitting the list-valued strings on `,` and ` and ` yields clean
tokens; unioned with the single-marque values they give 16 marques — *including
LiveWire and Damon, which appear nowhere else in the corpus*. So the pool that
lets LiveWire resolve is built out of the very strings that were hiding it. No
marque list is written by hand, for the same reason Phase 244C reads its
vocabulary from the data: a hard-coded list is wrong the next time a phase adds
a make.

The European set is derivable too — seed files named `known_issues_european_*`
contain exactly seven marques, and that is what `All European makes` expands to.
Energica falls outside it, being in its own file; the two affected entries
concern valve-train work and ICE tooling so the exclusion is defensible, but it
is an artefact of the derivation rather than a judgment, and the plan records it
rather than quietly absorbing it.

**The column is not being corrected, only indexed.** Rewriting 970 entries by
script is a larger risk than the defect, and what the author wrote should
survive. A junction table beside it is what queries will use.


---

## 2026-09-10 — Built

Migration 055 adds `known_issue_makes` and backfills it in its own transaction.
**LiveWire goes from 0 to 24 entries, Damon from 0 to 10** — Phase 243's output
is retrievable for the first time. Zero 17→27, Energica 12→22, Triumph 55→62,
Ducati 46→55. No issue is orphaned, and **not one `make` value was rewritten**.

**The build reintroduced the disease it was curing.** Joining the junction made
eleven existing tests go silently empty: a database below schema 55 has no
junction, so the join returned nothing — indistinguishable from a corpus with
nothing to say about the machine. That is the same failure as `make = 'Homda'`
returning zero rows, which is what opened this whole chain at Phase 244C. The
cure was built and the bug rebuilt one layer down, and only the regression
caught it. A missing junction now falls back to column matching, guarded to
still refuse cross-make results and still tier.

**The vocabulary was being derived from the wrong database.** Indexing derived
its marque list by `db_path`, defaulting to the configured production database,
so writing to any other database indexed it against production's vocabulary —
the write path and read path could disagree about what a marque is. Deriving
from the connection in hand makes that impossible rather than merely unlikely.

**A derived vocabulary is only correct over a complete corpus.** A row inserted
before the entry that establishes a marque cannot index against it; a rebuild
after seeding produced more rows than the inserts had. `rebuild_make_index` is
now authoritative and `db init` runs it once loading finishes. Worth stating
plainly: nothing about the incremental path *looks* wrong while it is being
wrong.

**One guard could not be written honestly.** The fallback is scoped to junction
errors, but that scoping is not behaviourally testable — the junction query and
the fallback depend on the same columns, so any error one hits the other hits
too. Mutation testing showed the first version passed with the condition
deleted. It is now a source assertion whose docstring says the behaviour is
unreachable and that structure is what is pinned. **A guard that admits its
reach is worth more than one implying a check it does not perform.**

**A fixture of mine was unrepresentative and the code was right.** Triumph and
Moto Guzzi appeared only inside the prose sentence, so the extractor declined to
treat them as marques — correct, and conservative in the right direction: the
vocabulary is what the corpus establishes, not what a sentence mentions. Kept as
a guard.

34 guards, 7/7 mutations caught, F9 lint clean, regression **6212 passed / 0
failed**.
