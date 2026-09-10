# Phase 244F — Marque vocabulary + make junction — phase log

**Status:** Planned
**Opened:** 2026-09-10

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
