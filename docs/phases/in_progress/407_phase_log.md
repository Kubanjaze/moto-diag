# Phase 407 — phase log

**Status:** In progress

## 2026-11-20 — Step 0 and v1.0

The operator, 2026-11-20 (K96): "do that and let me know where issues
stand", answering the advisor's proposal for F285.

Master `3908d99` holds K96, row 407 (🚧), the prompt
(`docs/prompts/407_the_operators_decision_asked_first.txt`) and the plan of
record's entry. This branch is `phase-407-the-operators-decision-asked-first`,
from `3908d99`.

Step 0 (`407_step0.md`): the scout stage labels `step0:done` whatever the
report says, the plan writer runs on that label, and P4 refuses a reshape
only after two calls; `escalate` already carries `needs-admiral` for ten
other stops. Classification: extension.

v1.0 (`407_implementation.md`): one helper, `Fleet.ask_reshape`, called by
the scout stage after its report and by the plan writer's stage before any
model call; five tests; six mutations. Committed and pushed before any
code.
