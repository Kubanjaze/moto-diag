"""The sizes of the three tables in `integration_gaps_allowlist.py`, pinned
ONCE (Phase 358, K2).

Each count was pinned as a literal in more than one test: unreachable modules
twice, module islands three times, orphans once. Wiring a listed module means
editing the allowlist, and a builder who found one pin missed the next — Phase
259 paid a second red regression for it. Now each literal lives here, one
assertion per count sits in a file the whole-tree command's fast mode runs,
and every other test imports the constant.
`tests/test_phase358_one_pin_per_count.py` fails on any literal pin of these
sizes anywhere else in `tests/`.

The number is not what holds the tree to the list; the new/stale tests in
`test_phase209B_integration_gaps.py` and `test_phase244W_module_islands.py`
do. A pin makes a change to the size a deliberate edit someone has to
explain, and the explanation is the history below. Append to it.
"""

from __future__ import annotations

#: `len(UNREACHABLE_MODULES)`. Asserted in test_phase209B_integration_gaps.py.
#: 38 of 256 modules unreachable from any entry point on 2026-09-17 (Phase
#: 209B's finding) → 37 at Phase 244Y (cli/registry deleted) → 34 at Phase
#: 259 (motodiag.workflows wired: three modules) → 32 at Phase 274 (`shop
#: labor-rate` reaches motodiag.pricing and pricing.labor_rates) → 29 at Phase
#: 275 (`shop appointment` and `shop calendar` reach motodiag.scheduling and
#: its appointment_repo and models).
UNREACHABLE_COUNT = 29

#: `len(MODULE_ISLANDS)`. Asserted in test_phase244W_module_islands.py.
#: 19 modules / 4,270 lines invisible to the gate on 2026-09-17 (Phase 244W's
#: finding, converged on by four independent designs) → 13 at Phase 244Y (six
#: superseded modules deleted) → 14 (244Y: inventory/models surfaced as a
#: third-order island once its last live import went; substrate). Unchanged by
#: Phase 244Z, on purpose: content fixed, reachability untouched. → 13 at
#: Phase 356 (`workflow run` reaches motodiag.engine.workflows). → 9 at Phase
#: 274 (`shop inventory` and `shop warranty` reach inventory's models,
#: item_repo, vendor_repo and warranty_repo).
MODULE_ISLAND_COUNT = 9

#: `len(ORPHANS)`. Asserted in test_phase244U_gate_blind_spot.py.
#: The running count of live orphans: 46 (pre-244U) → 66 (244U opened the
#: blind spot) → 58 (244V wired eight reference lookups) → 47 (244W: 13
#: reclassified as dead modules, +2 seen through prose strings) → 104 (244X:
#: 244U's rule reached multi-line re-exports, +57) → 98 (Phase 255 added the
#: transmission counter's two accessors as test-infra; a third orphan from the
#: same phase, applicability.scoped_rows, was DELETED rather than listed,
#: because it had no caller and a docstring naming one) → 96 (244Y deleted nine
#: superseded defs and the gate then surfaced Permission, a model whose only
#: constructor had gone) → 102 (Phase 259 fix #4: wiring the workflows
#: substrate's read side made its six write functions live orphans, listed as
#: substrate awaiting Phase 316) → 106 (Phase 356: wiring engine.workflows
#: made its three predefined scripts and generate_next_step live orphans,
#: listed as unwired-feature) → 105 (Phase 274: `shop customer transfer-bike`
#: calls crm transfer_ownership) → 111 (Phase 274: wiring inventory's repos
#: made five helpers and the Recall model live orphans) → 112 (Phase 274:
#: `shop labor-rate` left pricing/labor_rates' file loader a live orphan) →
#: 118 (Phase 275: wiring scheduling made six appointment_repo CRUD helpers
#: live orphans; booking has its own guarded status moves).
ORPHAN_COUNT = 118
