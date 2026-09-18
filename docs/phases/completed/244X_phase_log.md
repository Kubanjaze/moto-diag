# Phase 244X — 244U's rule reaches the imports it was written for — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-18

---

## 2026-09-18 — Plan v1.0

Split out of 244W, where one of the design prototypes found it: 244U's
regex stops at a newline, so the parenthesised multi-line import that most
packages here use for their re-exports was never blanked, and the rule
"a re-export is not a use" quietly did not apply to them. The fixture I
wrote for 244U used single-line imports and pinned the wrong shape.

Step 0 was mostly inherited and then re-measured on the tree 244W left:
47 → 104 live orphans, +57, 0 stale — the 43 that last time sat inside dead
modules are now absorbed by `MODULE_ISLANDS`, which is what 244W's third
scope item was for. Every one of the 57 has zero code references outside
its own file and is re-exported by exactly one init. Two of them turned out
to be worth a line on their own: `inventory/recall_repo` and
`advanced/recall_repo` write the same table, and only the second has a
command; and `submit_feedback` is genuinely unwired — nothing in the
product writes `diagnostic_feedback`.

## 2026-09-18 — Built

One regex and no surprises, which after 244W is its own kind of result.
The alias group now crosses newlines inside parentheses; seven forms of the
import statement are pinned; 244U's fixture and its ablation helper both use
the multi-line form, and all twelve of 244U's tests pass with their
assertions untouched — the proof was right, it had been running on the one
shape the regex handled.

The 57 entries went in with the same evidence each — zero code references
outside its own file, one init re-exporting it — and a test that every one
names that init. Two carry a classification a list would have flattened:
`inventory/recall_repo` as a Phase 118 duplicate of Phase 155's repo over
the same table, and `submit_feedback` as the only writer of a table nothing
writes. Both pinned by class, not just by presence.

38 tests, 314 across the four gate suites, 5/5 mutations.

## 2026-09-18 — Complete

Regression **7145 passed, 0 failed, 26:33**. No schema change, no source change under `src/`.

One correction before commit: 244Y's Step 0, running alongside, found that
the "duplicate" recall repo is delegated to by the live one for a single
function. The four entries now say so. The instrument work — 209B, 244U,
244W, 244X — is complete; what follows acts on what it reports.
