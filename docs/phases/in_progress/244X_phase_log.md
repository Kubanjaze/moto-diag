# Phase 244X — 244U's rule reaches the imports it was written for — phase log

**Status:** 🚧 In progress
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
