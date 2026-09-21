# Phase 256 — The retrieval chokepoint — phase log

**Status:** 🚧 In progress
**Opened:** 2026-09-21

---

## 2026-09-21 — Step 0 (draft, `471f123`)

Three enumerations over `src/motodiag`: raw SQL, AST call-sites, and every
file naming the table classified by hand. The method's limit was recorded at
the time and matters: **the three known doors were not rediscovered blind** —
I knew them from Phase 255, so two of the three sweeps were confirmations.
Only the raw-SQL sweep could find something unregistered, and it is the one
that found door 4.

Door 4 — `shop/priority_scorer` — turned out to be **dead since it was
written**. It selected a column named `fix`; the column is `fix_procedure`
and `fix` has never existed in any schema. Every call raised, a bare
`except Exception` returned `[]`, and the AI work-order scorer was told the
knowledge base had nothing on the machine, for every work order, always.
Seven of ten of the operator's vehicles would have matched. No test ever
called the function.

## 2026-09-21 — Build

**F126 was fixed on master before the phase opened**, on the operator's
instruction that two of its three defects were bugs rather than findings.
That turned out to matter for a reason nobody predicted: it gave door 4 a
**real** before-number instead of a row of zeros.

**The first check of the day was whether that fix reopened the Phase 254
leak.** It did not, and the reason is uncomfortable: door 4 matches
`LOWER(make) = ?`, exact equality, and nine of the eleven scoped rows carry
a seven-marque make string that is never equal to `"yamaha"`. **The
244C–244I defect this phase exists to fix was acting as accidental
protection** — so the *rewire* is what creates the exposure, and the filter
had to land in the same commit. Verified without the `LIMIT`, because "5 of
5" can hide a sixth: an R1 matches 33 rows unlimited, none scoped.

**The tripwire built to enforce that did not work the first time.** It
capped and filtered in one expression, so it read the five rows the scorer
receives — and with the filter removed, a Gold Wing's scoped rows sit at
resolver positions 56, 64, 75, 81, 113 and 115. Every one hidden by the
cap. The guard passed on leaking code, an hour after I had caught the
identical masking in the old `LIMIT 5`. Fixed structurally: the filtered set
is returned entire and the cap applies after. **A cap must never be what
makes a correctness property hold**, because a cap is a presentation
decision and someone will raise it.

**Then the same mistake in a third shape.** `GUARD_FETCH = 400` was safe by
arithmetic until the corpus grew. Measured before removing it: worst match
count 165 rows (16% of corpus), and unlimited costs **17.6 ms against 17.6
ms**. The caps were doing no work. All three production candidate stages —
200, 200 and 25 — are now the corpus count. Door 2 improves as a result:
`/ask` filters the full set and caps at twenty-five *after*, so the vision
model receives up to twenty-five rows that **apply**.

**And a fourth shape: my door-3 fixture was decorative.** It rebuilt the
candidate pool in the test and called the filter itself, so bypassing the
filter *inside* `predict_failures` left all 60 assertions green.

Four variations of one error in a single day — a guard that cannot observe
the thing it claims to guard. Each was caught by a positive control, and
none by reading the code.

## 2026-09-21 — The refuter

Four findings, each verified before acting on it, and the sharpest was one
this suite could never have produced: **rows that name a machine and are
then withheld from it.** Every guard here asks whether a machine receives
rows it may not have; none asked whether a machine misses rows written for
it. Four cases, and the Kymco Filly loses its rank-1 critical,
3,000-miles-overdue prediction to a row that names it.

It also disproved a docstring I had written with some confidence:
`rows_withheld` is **not** "what a sourced lookup entry would have saved".
A Grom records 8 and sourcing it as `manual` withholds the same 8 —
sourcing the Grom recovers **zero**.

And it caught that `predict_failures` now writes to the database while its
docstring called the pipeline side-effect free.

## 2026-09-21 — Step 0 corrected

Step 0 said there was one dynamic table-name query. **There are four.** Its
search looked for `FROM` followed by `{`, and in an f-string `{table}` is a
FormattedValue that never appears in the literal text — the literal ends
with `"SELECT * FROM "`. It was scanning for a character the target cannot
contain, so its eleven hits were prose and its one real find was luck. The
guard written to replace it repeated the mistake exactly before
over-correcting to thirteen. All four are safe, verified by reading every
literal passed as the table argument.
