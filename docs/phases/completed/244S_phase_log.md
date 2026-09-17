# Phase 244S — The retrieval fixes reach the commands people use — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-17

---

## 2026-09-17 — Plan v1.0 written

Second of the three reachability phases the Track L audit found. Step 0 ran
inside 244R's sweep as a design plus an adversarial check, and **the checker
broke the design**: the two retrieval paths return different row shapes, so
swapping one for the other would have handed callers JSON strings where they
expect lists. Its corrections are the plan.

The measured harm is worse than "specific entries rank badly". A bike entered
as "Homda" returns 0 rows through the LIKE path, `build_knowledge_context([])`
returns "", and the model diagnoses with no corpus while nothing says so —
the exact failure 244C exists to end, still shipping on the primary command.
The resolver returns 143 for the same input.

## 2026-09-17 — Built

The shape contract first, as the checker insisted: `row_to_issue_dict` is
public and both retrieval paths return through it. Then the wiring, and the
measurement that justifies the phase — "Homda"/"cbrf4i" went from 0 rows to
12 on the real corpus, with "make recorded as 'Homda', read as 'Honda'"
printed where a technician sees it.

Two things the work added to the plan. The excluding KTM entry is not dropped
— 244E forbids that — so it arrives ranked last and labelled, which in turn
meant the prompt builder had to learn the tier: an entry about another model
was rendering identically to one written about the machine in front of you.

And a fixture found a latent crash. `build_knowledge_context` called `len()`
on a NULL `fix_procedure`. No shipped row triggers it today; the column is
nullable, so the first entry authored without a procedure would have broken
every diagnosis that retrieved it.

Three of my own test drafts were wrong and said so loudly: the corpus fixture
rebuilt only the model junction, so the resolver could not see rows the make
index had never been told about.

20 tests, 7/7 mutations caught.

## 2026-09-17 18:59 EDT — Complete

Regression **6,856 passed, 0 failed, 26:49**. No schema change.
