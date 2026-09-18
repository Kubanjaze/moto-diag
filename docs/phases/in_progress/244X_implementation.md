# Phase 244X — 244U's rule reaches the imports it was written for

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-18

---

## Goal

Phase 244U established that a package-init re-export is not a use, and
implemented it with a regex that stops at a newline. A parenthesised
multi-line `from … import (…)` — the form every package in this tree with more
than a couple of exports uses — was never blanked, so 244U's rule silently did
not apply to `auth`, `inventory`, `billing`, `feedback` and the rest. Found by
one of 244W's design prototypes, verified in 244W's Step 0 (S0-7), and split
out because its finding is its own: 57 names in live modules that only a
package init mentions.

This phase fixes the regex, puts the shape it missed into 244U's own fixture
so the conjunctive proof pins what actually occurs, and classifies the 57.

## Step 0 — findings

**S0-1. The defect, exactly** (from 244W S0-7). `_FROM_IMPORT` is
`(from\s+[\w\.]+\s+import\s*\(?)([^)\n]*\)?)`. The alias group `[^)\n]*`
cannot cross a newline, so:

```
from demo.shelf import ShelfSitter, Other        -> ShelfSitter blanked: True
from demo.shelf import (\n    ShelfSitter,\n)     -> ShelfSitter blanked: False
```

`auth/__init__.py`, `inventory/__init__.py` and `billing/__init__.py` each
carry five imports in the second form, `feedback/__init__.py` two.

**S0-2. Measured on the current loader, after 244W.** With the alias group
allowed to cross newlines inside parentheses, the live orphan count goes
**47 → 104: +57, 0 stale.** Before 244W the same fix surfaced 99, of which 43
sat inside the 19 modules `MODULE_ISLANDS` now holds; those are absorbed by
their module entries, which is the composition 244W's scope item 3 was for.
The 57 that remain are in live modules.

**S0-3. All 57 are what 244U's rule defines.** For every one: zero references
in any non-init module's code other than its own file (after the gate's own
blanking), and exactly one `__init__.py` re-exporting it. By package:
`advanced` 11, `auth` 9, `shop` 8, `accounting` 6, `feedback` 6, `crm` 5,
`inventory` 4, `billing` 3, `memory` 2, `capture` 1, `intake` 1,
`obd_reports` 1. The measurement script printed each name's referrers; there
was nothing to reason about individually, and that is the point — the
re-export was the only thing standing between these and the list.

**S0-4. The ones that look like features, checked at the table.** For each
candidate: the SQL its body runs, and whether any *other* live file writes
those tables.

- **Genuinely unwired.** `feedback_repo::submit_feedback` — nothing else
  writes `diagnostic_feedback`; 244N wired `record_override` (the
  `session_overrides` table), not this. The five read accessors beside it are
  the read side of a table nothing writes. `users_repo::create_user` — no
  other `INSERT INTO users`; users exist only as migration-005 seed data.
  `obd_reports/repo::list_failures` — the route writes `obd_failure_reports`
  through the same file; nothing reads it back. `customer_bikes_repo::
  transfer_ownership` — no route or command transfers a bike.
- **Superseded, and one duplicate implementation.** `inventory/recall_repo`'s
  `add/get/list/delete_recall` write the same `recalls` table as
  `advanced/recall_repo` (Phase 118 vs Phase 155); only the second has a
  command. `memory/compile::compile_vehicle` and `compile_all` are
  one-line wrappers returning `.inserted` of the `_detailed` forms 209C
  wired. `invoice_repo::recalculate_invoice_totals` — `shop/invoicing.py`
  computes its own totals.
- **Helpers beside a live path.** `deactivate_user` wraps the live
  `update_user`; `get_system_user` wraps `get_user`; `get_current_owner`
  wraps `list_customers_for_bike`; `get_unassigned_customer` wraps
  `get_customer`; `deactivate_shop` sits beside two live `UPDATE shops`
  writers. `public-api`, the `_REPO_HELPER` shape, with the wrapped name in
  the reason.
- **Everything else** is a `count_*` / `list_*` / `get_*_by_*` / `delete_*`
  repository helper, a data model or enum (`Fleet`, `CustomerBike`,
  `UserRole`, `RoleName`, `PermissionName`, `RolePermission`,
  `IntakeUsageEntry`, `BayScheduleSlot`), or an exception type
  (`ServiceEventNotFoundError`, `BatchTimeoutError`,
  `PriorityCostCapExceeded`) — `public-api`. `load_recalls_from_json` is
  `test-infra`: F86 pins that nothing in `src/` may call it, and its tests do.

**S0-5. 244U's proof pins the wrong shape, twice over.** Its fixture
(`test_phase244U_gate_blind_spot.py::tree`) writes single-line imports, and
its conjunctive helper `_orphans_with` (lines 97-102) carries a private copy
of the same `[^)\n]*` regex to ablate the two halves. Fixing the gate alone
leaves the proof green on a form the tree barely uses. Both change here: the
fixture's re-export becomes parenthesised and multi-line, and the helper's
copy matches the fix, so "both halves are required" is demonstrated on the
form that occurs.

**S0-6. Why 104 entries is not the rubber stamp S0-5 of 244W warns about.**
Every one of the 57 carries the same evidence — the re-export that masked it,
verified by the measurement — and a classification from the allowlist's
existing categories. What the warning forbids is entries nobody reasoned
about; the reasoning here is that a name a package exports and nothing uses
is either a library helper kept on purpose, a data model or exception type
exported for callers that never came, or a feature with no caller — and each
entry says which, with a phase or a sibling to check it against.

## Scope

1. **Fix `_FROM_IMPORT`** so the alias group of a parenthesised import may
   cross newlines: one regex, both forms, applied to package inits as
   before. The module path stays intact (the import walk reads it).
2. **244U's fixture and helper pin the multi-line form** (S0-5).
3. **The 57 join `ORPHANS`**, each with its classification and the init that
   re-exports it; 244U's running-count pin moves 47 → 104 with its history.
4. **Tests through the gate**: `blank_exports` on the single-line,
   parenthesised single-line, parenthesised multi-line, trailing-comma,
   `as`-alias and comment-inside-parentheses forms; the real tree by name
   for a handful of the 57 that this repo has already pinned as callerless
   elsewhere (`submit_feedback`, `load_recalls_from_json`); the new/stale
   directions unchanged and green.

## Non-goals

- **No deletion and no wiring.** The list grows; the decisions stay where
  they are, now with evidence.
- **No change to `find_module_islands`** or to what 244W landed.
- **No AST rewrite of `blank_exports`.** Two of 244W's design prototypes
  suggested it; a regex that crosses newlines is the whole defect, and the
  tokenizer-based passes beside it already handle the cases where a regex
  would be wrong (strings, comments).

## Verification Checklist

- [ ] `blank_exports` blanks a parenthesised multi-line alias list in a package init
- [ ] Single-line, parenthesised single-line, trailing comma, `as` alias, and a comment inside the parentheses all blank correctly
- [ ] A non-init module's imports are untouched, as before (244U's `test_a_non_init_module_keeps_its_imports`)
- [ ] The module path in the `from` clause survives (the import walk needs it)
- [ ] 244U's conjunctive test passes on a multi-line fixture, and each half alone still fails to reveal the name
- [ ] The real tree reports exactly the 57, both directions clean against `ORPHANS`
- [ ] `submit_feedback` and `load_recalls_from_json` are reported by name
- [ ] Every new entry: classification in `CLASSIFICATIONS`, reason ≥ 20 chars, names the re-exporting init
- [ ] Mutations: revert the regex; blank only the first line; drop the `__all__` half; treat a non-init like an init — each caught
- [ ] Full regression green
